"""Source-aware question join for one OpenCodeReasoning-2 shard (G10).

    python prepare_ocr2.py --source-manifest source_manifest.json --policy ocr2_policy.json \
        --input train-00000-of-00070.parquet --shard-id 0 --out-dir run/join [--mode diagnostic|admission]

The Hub shard stores every question as "-". This step rebuilds the question from the pinned original
split (`source_index.py`) and writes a source-shaped JSONL that `convert.py --set
sft-code-opencodereasoning-2 --input` reads unchanged. Nothing is paraphrased, repaired or generated:
a row either gets the exact statement of its original row, or it is left out and counted.

Every input row gets exactly one primary outcome, checked in this order:

    malformed_row, duplicate_row_id, unknown_dataset,
    policy_protected_split, policy_split_not_allowed, policy_row_licence,
    quality_critique_wrong, quality_judgement_unknown, quality_execution_failed, quality_execution_missing,
    invalid_index, held_source_unavailable, held_source_not_approved, held_identity_unverified,
    index_out_of_bounds, source_question_unusable, question_mismatch, policy_protected_family,
    eligible_joined

so that `raw rows = policy excluded + malformed or unresolved + eligible joined` holds exactly. The outer
`train/python` path of a shard authorises nothing: the row's own upstream split decides.

Outputs in --out-dir (all private, never in Git):
    joined.jsonl           eligible rows only, the source columns with the question filled in
    joined.sidecar.jsonl   one line per joined row: rendered id -> OCR row key -> original source row
    exclusions.jsonl       one line per other row: OCR row key, outcome, dataset, split (no text)
    join_manifest.json     counts, hashes and the binding to policy, mode and source manifest; written last

`convert.py` names a rendered row `<set>/<index base + position in joined.jsonl>` and leaves a hole for
a row it skips. The sidecar fixes that position before conversion, so a hole never shifts the mapping.

Modes. `diagnostic` runs under a `TSAI reserves` ruling and with sources whose identity is only
`diagnostic`; its output is for scanning and review. `admission` refuses the whole run unless the set is
`allowed` and the teacher is approved, and holds every row whose source is not approved for training or
not identity-verified. Exit code: 0 done, 2 bad input or manifest, 3 refused by policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import convert as g10  # noqa: E402
import source_index as si  # noqa: E402

SET_ID = "sft-code-opencodereasoning-2"
POLICY_SCHEMA = "g10-ocr2-policy/1"
JOIN_SCHEMA = "g10-ocr2-join/1"
MODES = ("diagnostic", "admission")
PLACEHOLDERS = ("", "-")
POLICY_EXCLUDED = (
    "policy_protected_split", "policy_split_not_allowed", "policy_row_licence", "quality_critique_wrong",
    "quality_judgement_unknown", "quality_execution_failed", "quality_execution_missing",
    "held_source_not_approved", "policy_protected_family",
)
UNRESOLVED = (
    "malformed_row", "duplicate_row_id", "unknown_dataset", "invalid_index", "held_source_unavailable",
    "held_identity_unverified", "index_out_of_bounds", "source_question_unusable", "question_mismatch",
)
ELIGIBLE = "eligible_joined"
OUTCOMES = POLICY_EXCLUDED + UNRESOLVED + (ELIGIBLE,)
STRING_FIELDS = ("id", "dataset", "split", "question", "r1_generation", "judgement", "license")


class Refusal(Exception):
    """The policy does not permit this run (exit code 3). Nothing is written."""


# --- policy ------------------------------------------------------------------------------------

def load_policy(path) -> tuple[dict, str]:
    """Read and validate a policy file. Returns (policy, sha256 of the file)."""
    path = Path(path)
    try:
        raw = path.read_bytes()
        policy = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise si.SourceIndexError(f"cannot read policy {path}: {exc}") from exc

    def need(cond, message):
        if not cond:
            raise si.SourceIndexError(f"policy {path.name}: {message}")

    need(isinstance(policy, dict) and policy.get("schema") == POLICY_SCHEMA, f"schema is not {POLICY_SCHEMA}")
    need(policy.get("set") == SET_ID, f"set is not {SET_ID}")
    need(isinstance(policy.get("set_decision"), str) and policy["set_decision"], "set_decision is missing")
    teacher = policy.get("teacher")
    need(isinstance(teacher, dict) and isinstance(teacher.get("approved"), bool), "teacher.approved must be true or false")
    for field in ("field", "model", "licence"):
        need(isinstance(teacher.get(field), str), f"teacher.{field} is missing (use \"\" for unknown)")
    need(isinstance(policy.get("ocr2"), dict) and isinstance(policy["ocr2"].get("distribution_licence"), str),
         "ocr2.distribution_licence is missing")
    allowed = policy.get("row_licences_allowed")
    need(isinstance(allowed, list) and all(isinstance(x, str) for x in allowed), "row_licences_allowed must be a list")
    quality = policy.get("target_quality")
    need(isinstance(quality, dict), "target_quality is missing")
    need(isinstance(quality.get("admit_judgements"), list) and quality["admit_judgements"], "target_quality.admit_judgements is missing")
    rate = quality.get("min_pass_rate")
    need(isinstance(rate, (int, float)) and not isinstance(rate, bool) and 0 <= rate <= 1, "target_quality.min_pass_rate must be in [0, 1]")
    need(quality.get("missing_execution_evidence") in ("admit_tagged", "exclude"),
         "target_quality.missing_execution_evidence must be admit_tagged or exclude")
    sources = policy.get("sources")
    need(isinstance(sources, dict) and sources, "sources is missing")
    for name, src in sources.items():
        for field in ("train_splits", "protected_splits"):
            need(isinstance(src.get(field), list), f"sources.{name}.{field} must be a list")
        need(not set(src["train_splits"]) & set(src["protected_splits"]), f"sources.{name}: a split is both train and protected")
        need(isinstance(src.get("training_approved"), bool), f"sources.{name}.training_approved must be true or false")
        for field in ("repo", "statement_licence", "attribution"):
            need(isinstance(src.get(field), str), f"sources.{name}.{field} is missing (use \"\" for unknown)")
    need(isinstance(policy.get("protected_family_keys", []), list), "protected_family_keys must be a list")
    return policy, hashlib.sha256(raw).hexdigest()


def gate(policy: dict, mode: str, table_decision: str | None = None) -> None:
    """Set-level admission of a run. Raises Refusal; a diagnostic run never becomes an admission run."""
    if mode not in MODES:
        raise Refusal(f"unknown mode {mode!r}")
    decision = policy["set_decision"]
    if table_decision is not None and table_decision != decision:
        raise Refusal(f"policy says {decision!r} but licences/licence_table.md says {table_decision!r}: the table decides")
    if mode == "diagnostic":
        if not decision.startswith(("TSAI reserves", "allowed")):
            raise Refusal(f"{SET_ID} has decision {decision!r}: not even a diagnostic run is permitted")
        return
    reasons = []
    if not decision.startswith("allowed"):
        reasons.append(f"set decision is {decision!r}, not allowed")
    teacher = policy["teacher"]
    if not (teacher["approved"] and teacher["model"] and teacher["licence"]):
        reasons.append("teacher model or its licence is unknown or not approved")
    if not policy["ocr2"]["distribution_licence"]:
        reasons.append("OCR-2 distribution licence is unknown")
    if reasons:
        raise Refusal("admission mode refused: " + "; ".join(reasons))


# --- small helpers -----------------------------------------------------------------------------

def equivalent(a: str, b: str) -> bool:
    """The documented non-destructive rule for a question that is already present in an OCR-2 row:
    equal after normalising line endings to \\n and ignoring whitespace at the two ends. Nothing else."""
    def norm(text):
        return text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return norm(a) == norm(b)


def pass_rate(value) -> float | None:
    """The publisher's pass_rate as a float, -1.0 for 'no execution evidence', None when unreadable."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(rate) or not (rate == -1.0 or 0.0 <= rate <= 1.0):
        return None
    return rate


def _write_atomic(path: Path, data: bytes) -> str:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    return hashlib.sha256(data).hexdigest()


class _Sink:
    """A JSONL file written under a .tmp name, hashed as it is written, published by rename."""

    def __init__(self, path: Path):
        self.path, self.tmp = path, path.with_name(path.name + ".tmp")
        self.stream, self.digest, self.rows = open(self.tmp, "wb"), hashlib.sha256(), 0

    def write(self, obj: dict) -> None:
        data = (json.dumps(obj, ensure_ascii=True) + "\n").encode("ascii")  # ASCII escapes: any str survives
        self.stream.write(data)
        self.digest.update(data)
        self.rows += 1

    def publish(self) -> str:
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()
        os.replace(self.tmp, self.path)
        return self.digest.hexdigest()

    def abort(self) -> None:
        self.stream.close()
        self.tmp.unlink(missing_ok=True)


def code_hashes() -> dict:
    return {name: si.sha256_file(HERE / name) for name in ("prepare_ocr2.py", "source_index.py")}


def input_entry(manifest: dict, shard_id: int) -> dict:
    for entry in manifest["ocr2"].get("inputs", []):
        if entry["shard_id"] == shard_id:
            return entry
    raise si.SourceIndexError(f"shard {shard_id} has no pinned local input in the source manifest (ocr2.inputs)")


# --- the join ----------------------------------------------------------------------------------

def classify(row, ordinal_seen: set, policy: dict, index: si.SourceIndex, mode: str) -> tuple[str, dict]:
    """One row -> (primary outcome, facts). Facts of an eligible row include the resolved source row."""
    if not isinstance(row, dict) or any(not isinstance(row.get(f), str) for f in STRING_FIELDS) or "index" not in row:
        return "malformed_row", {}
    rate = pass_rate(row.get("pass_rate"))
    if rate is None:
        return "malformed_row", {}
    facts = {"dataset": row["dataset"], "split": row["split"]}
    if row["id"] in ordinal_seen:
        return "duplicate_row_id", facts
    ordinal_seen.add(row["id"])
    src_policy = policy["sources"].get(row["dataset"])
    if src_policy is None:
        return "unknown_dataset", facts
    if row["split"] in src_policy["protected_splits"]:
        return "policy_protected_split", facts
    if row["split"] not in src_policy["train_splits"]:
        return "policy_split_not_allowed", facts
    if row["license"].strip().lower() not in {x.lower() for x in policy["row_licences_allowed"]}:
        return "policy_row_licence", facts
    quality = policy["target_quality"]
    if row["judgement"] not in quality["admit_judgements"]:
        return ("quality_critique_wrong" if row["judgement"] == "wrong" else "quality_judgement_unknown"), facts
    if rate == -1.0:
        if quality["missing_execution_evidence"] == "exclude":
            return "quality_execution_missing", facts
        facts["exec_status"] = "missing"
    elif rate < quality["min_pass_rate"]:
        return "quality_execution_failed", facts
    else:
        facts["exec_status"] = "pass" if rate == 1.0 else "partial"
    try:
        ordinal = si.parse_ordinal(row["index"])
    except si.BadOrdinal:
        return "invalid_index", facts
    source = index.source(row["dataset"], row["split"])
    if source is None:
        return "held_source_unavailable", facts
    if source["protected"]:  # the manifest and the policy disagree: never read a protected split as train
        return "policy_protected_split", facts
    if mode == "admission":
        if not src_policy["training_approved"]:
            return "held_source_not_approved", facts
        if source["identity_level"] != "verified":
            return "held_identity_unverified", facts
    try:
        resolved = index.resolve(row["dataset"], row["split"], ordinal)
    except si.OutOfBounds:
        return "index_out_of_bounds", facts
    if resolved["question"] is None:
        return "source_question_unusable", facts
    facts["question_verified_against_row"] = False
    if row["question"].strip() not in PLACEHOLDERS:
        if not equivalent(row["question"], resolved["question"]):
            return "question_mismatch", facts
        facts["question_verified_against_row"] = True
    family = "sha256:" + resolved["family_sha256"]
    members = index.family_members(resolved["family_sha256"])
    if family in policy.get("protected_family_keys", []) or any(protected for _, _, protected in members):
        return "policy_protected_family", facts
    facts.update(resolved=resolved, family=family, family_sources=sorted({f"{d}/{s}" for d, s, _ in members}),
                 pass_rate=rate)
    return ELIGIBLE, facts


def prepare(source_manifest, policy_path, input_path, shard_id: int, out_dir, mode: str = "diagnostic", index_path=None) -> dict:
    """Join one shard. Returns the join manifest (also written last, as join_manifest.json)."""
    manifest, manifest_sha, _ = si.load_manifest(source_manifest)
    policy, policy_sha = load_policy(policy_path)
    gate(policy, mode, g10.licence_row(SET_ID)["decision"])
    input_path, out_dir = Path(input_path), Path(out_dir)
    entry = input_entry(manifest, shard_id)
    shard = manifest["ocr2"]["shards"][shard_id]
    input_sha = si.sha256_file(input_path)
    if input_sha != entry["sha256"]:
        raise si.SourceIndexError(f"{input_path.name} has sha256 {input_sha}, the manifest pins {entry['sha256']} for shard {shard_id}")
    index = si.open_or_build(source_manifest, index_path or Path(f"{source_manifest}.index.sqlite"))
    for (dataset, split), src in index._sources.items():
        declared = policy["sources"].get(dataset)
        if declared and split in declared["train_splits"] and src["protected"]:
            raise Refusal(f"{dataset}/{split} is a train split in the policy but protected in the source manifest")
        if declared and split in declared["protected_splits"] and not src["protected"]:
            raise Refusal(f"{dataset}/{split} is protected in the policy but its text is indexed as train: rebuild the index")
    row_offset = entry.get("row_offset", 0)
    index_base = si.shard_index_base(manifest, shard_id)
    revision = manifest["ocr2"]["revision"]

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "join_manifest.json").unlink(missing_ok=True)  # the completion marker of this step goes first
    joined, sidecar, excluded = (_Sink(out_dir / n) for n in ("joined.jsonl", "joined.sidecar.jsonl", "exclusions.jsonl"))
    outcomes: Counter = Counter()
    by_source: dict[str, Counter] = {}
    tags: Counter = Counter()
    families: Counter = Counter()
    cross_source: set = set()
    seen: set = set()
    raw = 0
    try:
        for position, row in enumerate(g10.read_rows(input_path)):
            raw += 1
            row_ordinal = row_offset + position
            outcome, facts = classify(row, seen, policy, index, mode)
            outcomes[outcome] += 1
            key = f"{facts['dataset']}/{facts['split']}" if facts else "(malformed)"
            by_source.setdefault(key, Counter())[outcome] += 1
            ocr_key = [revision, shard["path"], row_ordinal]
            if outcome != ELIGIBLE:
                excluded.write({"ocr_row_key": ocr_key, "ocr_id": row.get("id") if isinstance(row, dict) else None,
                                "outcome": outcome, "dataset": facts.get("dataset"), "split": facts.get("split")})
                continue
            resolved = facts["resolved"]
            src_policy = policy["sources"][row["dataset"]]
            tags["exec_" + facts["exec_status"]] += 1
            tags["question_verified_against_row"] += int(facts["question_verified_against_row"])
            families[facts["family"]] += 1
            if len(facts["family_sources"]) > 1:
                cross_source.add(facts["family"])
            sidecar.write({
                "joined_ordinal": joined.rows,
                "rendered_id": f"{SET_ID}/{index_base + joined.rows}",
                "ocr_row_key": ocr_key,
                "ocr_id": row["id"],
                "ocr_question_id": row.get("question_id"),
                "source_row_key": [resolved["repo"], resolved["revision"], row["dataset"], row["split"], resolved["ordinal"]],
                "source_file": resolved["file"],
                "source_local_ordinal": resolved["local_ordinal"],
                "source_problem_id": resolved["problem_id"],
                "source_identity_level": resolved["identity_level"],
                "question_sha256": resolved["question_sha256"],
                "problem_family_key": facts["family"],
                "family_sources": facts["family_sources"],
                "split_membership": row["split"],
                "licence": {"ocr2_distribution": policy["ocr2"]["distribution_licence"], "row_tag": row["license"],
                            "source_statement": src_policy["statement_licence"], "attribution": src_policy["attribution"]},
                "teacher": {"model": policy["teacher"]["model"], "licence": policy["teacher"]["licence"]},
                "quality": {"judgement": row["judgement"], "pass_rate": facts["pass_rate"], "exec_status": facts["exec_status"]},
            })
            joined.write({**row, "question": resolved["question"]})
    except BaseException:
        for sink in (joined, sidecar, excluded):
            sink.abort()
        raise
    finally:
        index.close()
    if raw != entry["rows"]:
        for sink in (joined, sidecar, excluded):
            sink.abort()
        raise si.SourceIndexError(f"{input_path.name} has {raw} rows, the manifest says {entry['rows']} for shard {shard_id}")

    groups = {"policy_excluded": sum(outcomes[o] for o in POLICY_EXCLUDED),
              "malformed_or_unresolved": sum(outcomes[o] for o in UNRESOLVED),
              "eligible_joined": outcomes[ELIGIBLE]}
    if sum(groups.values()) != raw or joined.rows != outcomes[ELIGIBLE] or sidecar.rows != joined.rows \
            or excluded.rows != raw - joined.rows:
        raise AssertionError("join counts do not reconcile")
    shard_rows = shard.get("rows")
    span = shard_rows if shard_rows is not None else row_offset + raw
    outputs = {"joined.jsonl": joined.publish(), "joined.sidecar.jsonl": sidecar.publish(), "exclusions.jsonl": excluded.publish()}
    result = {
        "schema": JOIN_SCHEMA, "set": SET_ID, "mode": mode,
        "shard_id": shard_id, "shard_path": shard["path"], "ocr_revision": revision,
        "input": {"name": input_path.name, "sha256": input_sha, "rows": raw, "row_offset": row_offset, "coverage": entry["coverage"]},
        "index_base": index_base, "id_range": [index_base, index_base + span],
        "policy_sha256": policy_sha, "source_manifest_sha256": manifest_sha,
        "index_content_sha256": index.meta["content_sha256"], "code_sha256": code_hashes(),
        "raw_rows": raw, "groups": groups,
        "outcomes": {o: outcomes[o] for o in OUTCOMES if outcomes[o]},
        "by_source": {k: dict(sorted(v.items())) for k, v in sorted(by_source.items())},
        "tags": dict(sorted(tags.items())),
        "families": {"unique": len(families), "with_several_solutions": sum(1 for n in families.values() if n > 1),
                     "max_solutions": max(families.values(), default=0), "also_in_another_source": len(cross_source)},
        "outputs": outputs,
    }
    _write_atomic(out_dir / "join_manifest.json", (json.dumps(result, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source-manifest", type=Path, required=True)
    ap.add_argument("--policy", type=Path, required=True)
    ap.add_argument("--input", type=Path, required=True, help="the pinned OCR-2 shard (.parquet) or pinned row prefix (.jsonl)")
    ap.add_argument("--shard-id", type=int, required=True)
    ap.add_argument("--out-dir", type=Path, required=True, help="private folder; keep it out of Git")
    ap.add_argument("--mode", choices=MODES, default="diagnostic")
    ap.add_argument("--index", type=Path, help="built source index (default: <source manifest>.index.sqlite, built if absent)")
    args = ap.parse_args(argv)
    try:
        result = prepare(args.source_manifest, args.policy, args.input, args.shard_id, args.out_dir, args.mode, args.index)
    except Refusal as exc:
        print(f"prepare_ocr2: REFUSED: {exc}", file=sys.stderr)
        return 3
    except (si.SourceIndexError, OSError, ValueError) as exc:
        print(f"prepare_ocr2: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: result[k] for k in ("set", "mode", "shard_id", "raw_rows", "groups", "outcomes")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
