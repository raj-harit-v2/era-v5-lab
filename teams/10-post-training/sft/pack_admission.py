"""Strict admission boundary between a scanned OCR-2 render and a training pack (G10).

    python pack_admission.py --manifest pack_manifest.json --mode report --out pack_report.json
    python pack_admission.py --manifest pack_manifest.json --mode training --out pack.jsonl

`convert.py` lets a `TSAI reserves` set through so that it can be scanned. That is a diagnostic permission.
A training pack needs more, and this is the one place that checks all of it:

run level (any one of these is a blocker; `--mode training` then writes nothing and exits 3)
    the set is `allowed` in the policy AND in licences/licence_table.md; the join ran in admission mode;
    policy, source manifest, sidecar and render are the exact files the join and the scan were bound to;
    the teacher is known and approved; every source that supplied a row is approved for training, has an
    identity level the policy accepts (`pack.accepted_identity_levels`, default verified only; diagnostic
    never) and has known statement terms and attribution; the tokenizer and the fingerprint
    set are the approved ones; the scan was the full set with zero canaries and a zero-hit second pass
    over the retained file; a context limit is set; the run is not a test fixture.

row level (a failing row is rejected and counted; the others still pass)
    the retained id maps through the sidecar to its original OCR row and carries that row's own id;
    the upstream split is a train split; the row is tokenized with this tokenizer and its ids, spans and
    mask recompute exactly; at least one shifted assistant target exists (loss_mask[1:]); the sequence
    fits the context limit.

held-out split (only when the policy has `pack.heldout_eval_v1`)
    a row that passed every row check goes to the held-out file instead of the pack when the salted
    sha256 of its problem family key falls under `fraction`. The unit is the problem family (exact
    statement identity across sources), so a held-out problem has no completion in the pack. In training
    mode the held-out rows are written to `<out stem>.heldout_eval_v1<suffix>` with their own sha256.
    Nothing is deleted: setting the fraction to 0 folds them back.

`--mode report` runs the same checks, never writes rows and exits 0: it says what would block a pack.
`clean rows = pack rejected + row checks passed` and `row checks passed = train rows + held-out rows`
always hold. The pack manifest is a small JSON written by
`run_ocr2.py` (paths relative to its own folder). Keep packs and reports with ids out of Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import convert as g10  # noqa: E402
import prepare_ocr2 as join  # noqa: E402
import source_index as si  # noqa: E402

PACK_SCHEMA = "g10-ocr2-pack/1"
REPORT_SCHEMA = "g10-ocr2-pack-report/1"
MODES = ("report", "training")
ROW_OUTCOMES = (
    "rejected_duplicate_id", "rejected_unmapped_id", "rejected_identity_mismatch", "rejected_protected_split",
    "rejected_no_target_span", "rejected_not_tokenized", "rejected_mask_mismatch", "rejected_empty_shifted_target",
    "rejected_context_overflow", "passed_row_checks",
)


ENCODE_CHUNK = 256  # rows per tokenizer.encode_batch call in the row check; 1 reproduces the per-row path


class PackError(Exception):
    """An input of the admission check cannot be read (exit code 2)."""


def _load_json(path: Path, what: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PackError(f"cannot read {what} {path}: {exc}") from exc


def load_pack_manifest(path) -> tuple[dict, Path]:
    path = Path(path)
    pack = _load_json(path, "pack manifest")
    if pack.get("schema") != PACK_SCHEMA or pack.get("set") != join.SET_ID:
        raise PackError(f"{path.name}: not a {PACK_SCHEMA} manifest for {join.SET_ID}")
    for field in ("policy", "source_manifest", "join_manifest", "sidecar", "rendered"):
        if not isinstance(pack.get(field), str):
            raise PackError(f"{path.name}: {field} is missing")
    return pack, path.resolve().parent


def _percentile(sorted_values: list[int], q: float) -> int | None:
    if not sorted_values:
        return None
    return sorted_values[min(len(sorted_values) - 1, int(q * len(sorted_values)))]


def heldout_selector(policy: dict):
    """The policy's held-out rule as a function of a problem family key, or None when there is no hold-out."""
    spec = (policy.get("pack") or {}).get("heldout_eval_v1")
    if not spec or spec.get("fraction", 0) == 0:
        return None
    threshold, salt = int(spec["fraction"] * 2**64), spec["salt"]

    def held(family: str) -> bool:
        digest = hashlib.sha256(f"{salt}\n{family}".encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") < threshold
    return held


def heldout_path(out_path: Path) -> Path:
    return out_path.with_name(f"{out_path.stem}.heldout_eval_v1{out_path.suffix}")


def row_outcome(row: dict, entry: dict | None, policy: dict, tok, limit: int | None, enc=None) -> tuple[str, int, int]:
    """(outcome, tokens, shifted targets) of one retained row. `entry` is its sidecar line.

    `enc` is the row text already encoded by `tok` (a batched caller passes it); None encodes here."""
    if entry is None:
        return "rejected_unmapped_id", 0, 0
    if row.get("set") != join.SET_ID or row.get("source_id") != entry["ocr_id"]:
        return "rejected_identity_mismatch", 0, 0
    dataset = entry["source_row_key"][2]
    if entry["split_membership"] not in policy["sources"].get(dataset, {}).get("train_splits", []):
        return "rejected_protected_split", 0, 0
    text = row.get("text")
    spans = g10.train_spans(text) if isinstance(text, str) else []
    if not spans or row.get("train_spans") != [list(s) for s in spans]:
        return "rejected_no_target_span", 0, 0
    ids, mask = row.get("input_ids"), row.get("loss_mask")
    if tok is None or not isinstance(ids, list) or not isinstance(mask, list):
        return "rejected_not_tokenized", 0, 0
    if enc is None:
        enc = tok.encode(text, add_special_tokens=False)
    if len(ids) != len(mask) or enc.ids != ids or g10.token_mask(spans, enc.offsets) != mask:
        return "rejected_mask_mismatch", len(ids), 0
    targets = sum(mask[1:])  # position 0 is never predicted: a next-token target starts at index 1
    if targets == 0:
        return "rejected_empty_shifted_target", len(ids), 0
    if limit is not None and len(ids) > limit:
        return "rejected_context_overflow", len(ids), targets
    return "passed_row_checks", len(ids), targets


def _encode_chunk(tok, rows: list) -> list:
    """Encodings of the chunk's row texts in one batch call; None where there is nothing to encode."""
    at = [i for i, row in enumerate(rows) if isinstance(row, dict) and isinstance(row.get("text"), str)]
    out = [None] * len(rows)
    if tok is not None and at:
        for i, enc in zip(at, tok.encode_batch([rows[i]["text"] for i in at], add_special_tokens=False)):
            out[i] = enc
    return out


def evaluate(pack_manifest_path, mode: str, out_path=None, encode_chunk: int = ENCODE_CHUNK) -> dict:
    """Run every check. In training mode with no blocker the admitted rows are written to `out_path`."""
    if mode not in MODES:
        raise PackError(f"unknown mode {mode!r}")
    pack, base = load_pack_manifest(pack_manifest_path)

    def at(field):
        value = pack.get(field)
        return None if value is None else (Path(value) if Path(value).is_absolute() else base / value)

    try:
        policy, policy_sha = join.load_policy(at("policy"))
        _, manifest_sha, _ = si.load_manifest(at("source_manifest"))
    except si.SourceIndexError as exc:
        raise PackError(str(exc)) from exc
    join_manifest = _load_json(at("join_manifest"), "join manifest")
    blockers: list[str] = []

    def block(cond, code):
        if cond and code not in blockers:
            blockers.append(code)

    table_decision = g10.licence_row(join.SET_ID)["decision"]
    block(pack.get("test_fixture") is not False, "test_fixture_run")
    block(not policy["set_decision"].startswith("allowed"), "set_not_allowed_in_policy")
    block(not table_decision.startswith("allowed"), "set_not_allowed_in_licence_table")
    block(policy["set_decision"] != table_decision, "policy_and_licence_table_disagree")
    block(join_manifest.get("mode") != "admission", "join_not_in_admission_mode")
    block(join_manifest.get("policy_sha256") != policy_sha, "policy_changed_since_join")
    block(join_manifest.get("source_manifest_sha256") != manifest_sha, "source_manifest_changed_since_join")
    teacher = policy["teacher"]
    block(not (teacher["approved"] and teacher["model"] and teacher["licence"]), "teacher_unknown_or_not_approved")
    block(not policy["ocr2"]["distribution_licence"], "ocr2_distribution_licence_unknown")

    accepted_levels = join.accepted_identity_levels(policy)
    held = heldout_selector(policy)
    sidecar_path = at("sidecar")
    block(si.sha256_file(sidecar_path) != (join_manifest.get("outputs") or {}).get("joined.sidecar.jsonl"), "sidecar_not_the_joined_one")
    sidecar: dict[str, dict] = {}
    with open(sidecar_path, encoding="utf-8") as stream:
        for line in stream:
            entry = json.loads(line)
            if entry["rendered_id"] in sidecar:
                raise PackError("the sidecar names one rendered id twice")
            sidecar[entry["rendered_id"]] = entry
    block(len(sidecar) != join_manifest.get("groups", {}).get("eligible_joined"), "sidecar_row_count_differs_from_join")
    for entry in sidecar.values():
        dataset = entry["source_row_key"][2]
        src = policy["sources"].get(dataset, {})
        block(not src.get("training_approved"), f"source_not_approved_for_training:{dataset}")
        block(entry.get("source_identity_level") not in accepted_levels,
              f"source_identity_level_not_accepted:{dataset}/{entry['split_membership']}")
        block(not (src.get("statement_licence") and src.get("attribution")), f"source_terms_or_attribution_unknown:{dataset}")
        block(not entry["licence"].get("row_tag"), "row_licence_unknown")

    pack_policy = policy.get("pack") or {}
    tokenizer_path, tok, tokenizer_sha = at("tokenizer"), None, None
    if tokenizer_path is None or not tokenizer_path.is_file():
        block(True, "tokenizer_missing")
    else:
        from tokenizers import Tokenizer

        tokenizer_sha = si.sha256_file(tokenizer_path)
        tok = Tokenizer.from_file(str(tokenizer_path))
        block(tokenizer_sha not in pack_policy.get("approved_tokenizer_sha256", []), "tokenizer_not_approved")
    limit = pack.get("max_sequence_tokens")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        limit = None
        block(True, "context_limit_not_set")

    rendered_path, retained_path, record_path = at("rendered"), at("retained"), at("decontam_record")
    rendered_sha = si.sha256_file(rendered_path)
    record = None
    if record_path is None or retained_path is None:
        block(True, "scan_record_missing")
    else:
        record = _load_json(record_path, "decontam record")
        recheck = record.get("recheck_on_clean") or {}
        clean = record.get("clean") or []
        block(not record.get("ok") or not all((record.get("checks") or {"": False}).values()), "scan_not_ok")
        block(record.get("scope") != "full set", "scan_scope_not_full_set")
        block(record.get("set_sha256") not in pack_policy.get("approved_fingerprint_set_sha256", []), "fingerprint_set_not_approved")
        block(record.get("rows_canary") != 0 or (record.get("canary") or {}).get("files_skipped") != 0, "canary_found_or_scan_incomplete")
        block(recheck.get("flagged") != 0 or recheck.get("docs") != record.get("rows_kept"), "second_pass_missing_or_has_hits")
        block(record.get("clean_files_deleted") is True, "clean_file_was_dropped")
        block(len(record.get("inputs") or []) != 1 or record["inputs"][0].get("sha256") != rendered_sha, "scan_ran_on_another_render")
        block(len(clean) != 1 or clean[0].get("sha256") != si.sha256_file(retained_path), "retained_file_not_the_scanned_clean_file")

    writing = mode == "training" and out_path is not None
    out_path = Path(out_path) if out_path is not None else None
    held_out_path = heldout_path(out_path) if writing else None
    tmp = out_path.with_name(out_path.name + ".tmp") if writing else None
    held_tmp = held_out_path.with_name(held_out_path.name + ".tmp") if writing else None
    outcomes: Counter = Counter()
    lengths: list[int] = []
    tokens = targets = retained_rows = 0
    by_source: Counter = Counter()
    families: set = set()
    seen: set = set()
    digest, held_digest = hashlib.sha256(), hashlib.sha256()
    held_stats = {"rows": 0, "tokens": 0, "shifted_assistant_targets": 0, "length_max": None}
    held_by_source: Counter = Counter()
    held_families: set = set()
    train_families: set = set()
    sink = open(tmp, "wb") if writing else None
    held_sink = open(held_tmp, "wb") if writing else None

    def check(chunk: list) -> None:
        nonlocal tokens, targets
        encodings = _encode_chunk(tok, [row for _, row in chunk]) if encode_chunk > 1 else [None] * len(chunk)
        for (line, row), enc in zip(chunk, encodings):
            rid = row.get("id")
            if rid in seen:
                outcome, n, t = "rejected_duplicate_id", 0, 0
            else:
                seen.add(rid)
                outcome, n, t = row_outcome(row, sidecar.get(rid), policy, tok, limit, enc)
            outcomes[outcome] += 1
            if outcome != "passed_row_checks":
                continue
            entry = sidecar[rid]
            lengths.append(n)
            tokens += n
            targets += t
            source = f"{entry['source_row_key'][2]}/{entry['split_membership']}"
            by_source[source] += 1
            families.add(entry["problem_family_key"])
            data = line if line.endswith(b"\n") else line + b"\n"
            if held is not None and held(entry["problem_family_key"]):
                held_stats["rows"] += 1
                held_stats["tokens"] += n
                held_stats["shifted_assistant_targets"] += t
                held_stats["length_max"] = max(held_stats["length_max"] or 0, n)
                held_by_source[source] += 1
                held_families.add(entry["problem_family_key"])
                if held_sink is not None:
                    held_sink.write(data)
                    held_digest.update(data)
            else:
                train_families.add(entry["problem_family_key"])
                if sink is not None:
                    sink.write(data)
                    digest.update(data)

    try:
        if retained_path is not None:
            chunk: list = []
            with open(retained_path, "rb") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    retained_rows += 1
                    chunk.append((line, json.loads(line)))
                    if len(chunk) >= max(1, encode_chunk):
                        check(chunk)
                        chunk = []
            if chunk:
                check(chunk)
        if record is not None:
            block(record.get("rows_kept") != retained_rows, "retained_row_count_differs_from_scan_record")
        for stream in (sink, held_sink):
            if stream is not None:
                stream.flush()
                os.fsync(stream.fileno())
    finally:
        for stream in (sink, held_sink):
            if stream is not None:
                stream.close()

    passed = outcomes["passed_row_checks"]
    train_rows = passed - held_stats["rows"]
    admitted = train_rows if (mode == "training" and not blockers) else 0
    if writing:
        if blockers:
            tmp.unlink(missing_ok=True)
            held_tmp.unlink(missing_ok=True)
        else:
            os.replace(tmp, out_path)
            if held is not None:
                os.replace(held_tmp, held_out_path)
            else:
                held_tmp.unlink(missing_ok=True)
    lengths.sort()
    spec = (policy.get("pack") or {}).get("heldout_eval_v1") or {}
    report = {
        "schema": REPORT_SCHEMA, "set": join.SET_ID, "mode": mode,
        "training_admissible": not blockers, "blockers": sorted(blockers),
        "attempted": retained_rows, "row_checks_passed": passed, "pack_rejected": retained_rows - passed,
        "train_rows": train_rows, "heldout_rows": held_stats["rows"],
        "admitted": admitted, "emitted": admitted if writing else 0,
        "row_outcomes": {o: outcomes[o] for o in ROW_OUTCOMES if outcomes[o]},
        "passed_rows": {"tokens": tokens, "shifted_assistant_targets": targets, "unique_families": len(families),
                        "by_source": dict(sorted(by_source.items())),
                        "length_p50": _percentile(lengths, 0.50), "length_p95": _percentile(lengths, 0.95),
                        "length_max": lengths[-1] if lengths else None},
        "train_pack": {"rows": train_rows, "tokens": tokens - held_stats["tokens"],
                       "shifted_assistant_targets": targets - held_stats["shifted_assistant_targets"],
                       "unique_families": len(train_families)},
        "heldout_eval_v1": {**held_stats, "unique_families": len(held_families), "by_source": dict(sorted(held_by_source.items())),
                            "fraction": spec.get("fraction", 0), "salt": spec.get("salt"), "unit": "problem_family_key",
                            "sha256": held_digest.hexdigest() if (writing and not blockers and held is not None) else None},
        "context_limit": limit, "tokenizer_sha256": tokenizer_sha,
        "bound_to": {"policy_sha256": policy_sha, "source_manifest_sha256": manifest_sha, "rendered_sha256": rendered_sha,
                     "join_mode": join_manifest.get("mode"),
                     "fingerprint_set_sha256": record.get("set_sha256") if record else None},
        "pack_sha256": digest.hexdigest() if (writing and not blockers) else None,
    }
    if retained_rows != report["pack_rejected"] + passed or passed != train_rows + held_stats["rows"]:
        raise AssertionError("pack counts do not reconcile")
    if held_families & train_families:
        raise AssertionError("a problem family is on both sides of the held-out split")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, required=True, help="pack manifest written by run_ocr2.py")
    ap.add_argument("--mode", choices=MODES, required=True)
    ap.add_argument("--out", type=Path, required=True, help="report JSON (report mode) or the pack JSONL (training mode)")
    args = ap.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.mode, args.out if args.mode == "training" else None)
    except (PackError, OSError, ValueError) as exc:
        print(f"pack_admission: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(report, indent=1, sort_keys=True) + "\n"
    if args.mode == "report":
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    elif report["training_admissible"]:
        Path(f"{args.out}.admission.json").write_text(text, encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("mode", "training_admissible", "attempted", "row_checks_passed", "admitted", "emitted")}))
    if args.mode == "training" and not report["training_admissible"]:
        print("pack_admission: REFUSED: " + ", ".join(report["blockers"]), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
