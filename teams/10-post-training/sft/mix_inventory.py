#!/usr/bin/env python3
"""Eligibility ledger and mixture feasibility check for the G10 SFT mixture (Package D3).

    python mix_inventory.py build --out-jsonl results/eligibility_ledger.jsonl --out-md ../docs/eligibility_ledger.md \
        [--ocr2-runs <folder with report_0-69.json and its shard records>] [--token-records <jsonl>] \
        [--c3-records <jsonl>] [--verify]

What it does
    1. Reads the four documents on the branch: licences/licence_table.md (Stage 1), sft/decontam_report.md,
       sft/decontam_kept_rows.md and sft/sft_mix_proposal.md, plus the OCR-2 full-run record
       (sft/results/ocr2_full_run.json). With --ocr2-runs it also reads the 70 per-shard records, which hold one
       line per rendered row, so it can recompute the kept-row statistics instead of trusting the aggregate.
    2. Writes one ledger line per set (and one per OCR-2 source), with approval state, coverage class, row
       counts by stage, source hashes and, **only where a run record holds them**, unique families, sequence
       tokens, shifted supervised targets and length percentiles. A field no record holds is null and labelled
       `not_measured`. Nothing is estimated and nothing is carried over from memory.
    3. Computes, for illustrative budgets, requested_tokens(area) = budget x area_share and
       minimum_exposure(group) = assigned_tokens / unique_eligible_token_supply, then repeat exposure at 1x, 2x
       and 4x. A verdict is `INFEASIBLE` with the reason, `FEASIBLE` (supply fully measured), `FEASIBLE_ON_MEASURED`
       (the measured part alone already covers the request), or `UNMEASURED`. An unmeasured source is never
       assumed large enough and never filled by an excluded source or by hidden oversampling.

Budget unit (proposal, not a decision): total processed non-padding tokens (`tokens`, the length of the whole
rendered sample), with the supervised share (`shifted_supervised_targets`, the loss-masked assistant tokens
after the one-token shift) reported next to it. TSAI/Sai choose the unit; see docs/eligibility_ledger.md.

Everything is deterministic: the same inputs give the same bytes, and the ledger holds no timestamps.
Only the standard library is used. No dataset rows or text are read; the shard records hold counts and hashes.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

SCHEMA = "g10-eligibility-ledger/1"
AREAS = ("code", "agentic", "tool_use", "indic", "general", "safety")
EFFORTS = ("1k", "4k", "16k", "64k")
# sft_mix_proposal.md section 4. They apply across the whole mix, not per area and not in addition to it.
EFFORT_SHARES = {"1k": 0.30, "4k": 0.35, "16k": 0.25, "64k": 0.10}
BUDGETS = (10_000_000, 100_000_000, 1_000_000_000)   # illustrative planning scenarios, not approved sizes
REPEAT_CAPS = (1, 2, 4)
COVERAGE = ("full", "partial", "text-only", "excluded", "held")
CANDIDATE_CAPS = (1024, 4096, 8192, 16384, 32768, 65536)
SHARE_TOLERANCE = 1e-9
LENS_ALLOWED = "allowed"
LENS_RESERVED = "allowed+reserved"
LENSES = (LENS_ALLOWED, LENS_RESERVED)

# Fixed scenario of docs/G10_DATA.md section 5 (35 / 25 / 15 / 15 / 10 / 0, pending TSAI). The proposal table
# scenario is parsed from sft_mix_proposal.md section 2 so the two can be compared.
PLAN_SCENARIO = {"code": 0.35, "agentic": 0.25, "tool_use": 0.15, "indic": 0.15, "general": 0.10, "safety": 0.0}

# Composition inside each area, from sft_mix_proposal.md section 3 (fractions are of the area, not of the mix).
# A set that the proposal does not place in a group gets no assigned tokens here: it is listed as unassigned supply.
# Inside a group the rule is "equal exposure": assigned tokens are proportional to eligible supply. That is the rule
# with the lowest possible maximum repeat; it is a planning convention, not something the proposal states.
COMPOSITION = {
    "code": [
        ("long-cot competitive code", 25 / 35, ["sft-code-opencodereasoning", "sft-code-opencodereasoning-2",
                                                "sft-code-codeforces-cots"]),
        ("real commit diffs", 10 / 35, ["sft-code-commitpackft"]),
    ],
    "agentic": [
        ("SWE issue resolution", 15 / 25, ["sft-code-swe-rebench-openhands", "sft-code-nemotron-cascade-swe"]),
        ("terminal and CLI agents", 10 / 25, ["sft-code-nemotron-terminal"]),
    ],
    "tool_use": [
        ("execution-verified multi-tool calls", 8 / 15, ["sft-salesforce-xlam-60k"]),
        ("interactive multi-turn tool agents", 7 / 15, ["sft-agentic-nemotron-agentic-v1",
                                                         "sft-agentic-nemotron-sft-agentic-v2-tool-calling"]),
    ],
    "indic": [
        ("human-written Indic instructions", 10 / 15, ["sft-indic-aya-dataset"]),
        ("templated Indic task data", 5 / 15, ["sft-indic-aya-collection"]),
    ],
    "general": [
        ("math, science and STEM CoT", 4.9 / 7, ["sft-stem-code-openthoughts3", "sft-rl-math-openmathreasoning",
                                                 "sft-math-openr1-math", "sft-bespoke-stratos-17k",
                                                 "sft-science-nemotron-science", "sft-math-nemotron-math-v2",
                                                 "sft-math-nemotron-proofs", "sft-science-nemotron-science-v2",
                                                 "sft-science-glm51-phd"]),
        ("concise general instructions", 2.1 / 7, ["sft-dolly-15k", "sft-chat-nemotron-if-v1",
                                                   "sft-chat-nemotron-if-v2", "sft-oasst2"]),
    ],
    "safety": [
        ("safety supervision", 1.0, ["sft-safety-indicguard", "sft-safety-nemotron-guard-v3", "sft-safety-aegis-v1",
                                     "sft-safety-wildjailbreak", "sft-safety-nemotron-sft-v2"]),
    ],
}

# Sets that were run but are not named in the area table of proposal section 2. Their area is inferred from the set
# name and marked `inferred`; they sit in no composition group (no assigned tokens).
INFERRED_AREA = {
    "sft-code-nemotron-cuda": "code", "sft-code-nemotron-opencode": "code", "sft-code-swe-zero-openhands": "agentic",
    "sft-indic-indic-align-oasst-t": "indic", "sft-indic-indic-align-dolly-t": "indic",
    "sft-math-nemotron-sft-math-v4": "general", "sft-math-nemotron-proofs-v3-sft": "general",
    "sft-math-openr1-math-raw": "general",
}

AREA_NAMES = {"code": "code", "agentic": "agentic", "tool use": "tool_use", "indic": "indic", "general": "general",
              "safety": "safety"}


# --- small helpers ------------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def to_int(text: str) -> int:
    return int(re.sub(r"[^\d]", "", text))


def percentile(sorted_values: list[int], q: float) -> int | None:
    """Same rule as pack_admission._percentile: the value at index int(q * n), clipped."""
    if not sorted_values:
        return None
    return sorted_values[min(len(sorted_values) - 1, int(q * len(sorted_values)))]


def length_stats(values: list[int]) -> dict | None:
    if not values:
        return None
    v = sorted(values)
    return {"n": len(v), "min": v[0], "p50": percentile(v, 0.50), "p90": percentile(v, 0.90),
            "p95": percentile(v, 0.95), "p99": percentile(v, 0.99), "max": v[-1],
            "mean": round(sum(v) / len(v), 1)}


def split_cells(line: str) -> list[str]:
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|") and not inner.endswith("\\|"):
        inner = inner[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", inner)]


def table_rows(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        if not line.lstrip().startswith("|"):
            continue
        cells = split_cells(line)
        if all(re.fullmatch(r":?-{2,}:?", c) or c == "" for c in cells):
            continue
        rows.append(cells)
    return rows


def section(text: str, start: str, end: str | None) -> list[str]:
    """Lines from the heading that starts with `start` up to (not including) the next heading starting with `end`."""
    lines = text.split("\n")
    begin = next((i for i, ln in enumerate(lines) if ln.startswith(start)), None)
    if begin is None:
        raise ValueError(f"heading not found: {start!r}")
    stop = len(lines)
    if end is not None:
        for j in range(begin + 1, len(lines)):
            if lines[j].startswith(end):
                stop = j
                break
    return lines[begin + 1:stop]


def unbacktick(cell: str) -> str:
    return cell.strip().strip("`").strip()


# --- parsers for the branch documents ---------------------------------------------------------------

def normalise_decision(raw: str) -> str:
    low = raw.strip().lower()
    if low.startswith("excluded"):
        return "excluded"
    if low.startswith("tsai reserves"):
        return "tsai_reserves"
    if low.startswith("allowed"):
        return "allowed"
    return "other:" + raw.strip()


def parse_licence_stage1(text: str) -> dict[str, dict]:
    """Stage 1 table of licence_table.md: set id -> source, language, generator, licence, decision."""
    out: dict[str, dict] = {}
    rows = table_rows(section(text, "### Stage 1", "### Stage 2"))
    for cells in rows[1:]:
        if len(cells) != 6:
            raise ValueError(f"Stage 1 row has {len(cells)} cells, not 6: {cells[:1]}")
        set_id = unbacktick(cells[0])
        if set_id in out:
            raise ValueError(f"duplicate Stage 1 set: {set_id}")
        out[set_id] = {"set_id": set_id, "source": cells[1], "language": cells[2], "generator": cells[3],
                       "licence": cells[4], "decision_raw": cells[5], "decision": normalise_decision(cells[5])}
    return out


def parse_decontam_results(text: str) -> tuple[list[dict], dict]:
    """Section 1 of decontam_report.md. Returns the per-set rows and the header facts."""
    rows = []
    for cells in table_rows(section(text, "## 1. Result per set", "## 2.")):
        if cells[0] == "Set" or cells[0].startswith("**Total"):
            continue
        if len(cells) != 8:
            raise ValueError(f"result row has {len(cells)} cells: {cells[:1]}")
        run_on = cells[1]
        src = re.search(r"of ([\d,]+) source rows", run_on)
        rows.append({"set_id": unbacktick(cells[0]), "run_on": run_on, "rows_in": to_int(cells[2]),
                     "flagged": to_int(cells[3]), "canary": to_int(cells[4]),
                     "removed": to_int(re.match(r"[\d,]+", cells[5]).group(0)), "kept": to_int(cells[6]),
                     "clean_sha256_prefixes": re.findall(r"`([0-9a-f]{8,})…?`", cells[7]),
                     "source_rows_stated": to_int(src.group(1)) if src else None})
    head = {}
    m = re.search(r"\*\*set_sha256:\*\*\s*`([0-9a-f]{64})`", text)
    head["set_sha256"] = m.group(1) if m else None
    m = re.search(r"\*\*Sets run:\*\*\s*([\d,]+)\.\s*\*\*Rows in:\*\*\s*([\d,]+)\.\s*\*\*Removed[^:]*:\*\*\s*([\d,]+)"
                  r"[^*]*\*\*Kept:\*\*\s*([\d,]+)", text)
    if not m:
        raise ValueError("decontam_report.md header line (Sets run / Rows in / Removed / Kept) not found")
    head.update(sets_run=to_int(m.group(1)), rows_in=to_int(m.group(2)), removed=to_int(m.group(3)),
                kept=to_int(m.group(4)))
    return rows, head


def parse_decontam_inputs(text: str) -> dict[str, list[dict]]:
    """Section 6: set id -> list of {file, bytes, sha256}."""
    out: dict[str, list[dict]] = defaultdict(list)
    for cells in table_rows(section(text, "## 6. Inputs", "## 7.")):
        if cells[0] == "Set" or len(cells) != 4:
            continue
        out[unbacktick(cells[0])].append({"file": unbacktick(cells[1]), "bytes": to_int(cells[2]),
                                          "sha256": unbacktick(cells[3])})
    return dict(out)


def parse_kept_rows(text: str) -> tuple[dict[str, dict], dict]:
    rows = {}
    total = {}
    for cells in table_rows(text.split("\n")):
        if cells[0] == "Set" or len(cells) != 5:
            continue
        if cells[0].startswith("**"):
            total = {"rows_in": to_int(cells[1]), "removed": to_int(cells[2]), "kept": to_int(cells[4])}
            continue
        rows[unbacktick(cells[0])] = {"rows_in": to_int(cells[1]), "removed": to_int(cells[2]),
                                      "kept": to_int(cells[4])}
    return rows, total


def parse_proposal(text: str) -> dict:
    """Area shares and named sets from the table of section 2, and per-language rows from section 7."""
    areas: dict[str, dict] = {}
    for cells in table_rows(section(text, "## 2.", "## 3.")):
        if len(cells) != 4 or not re.match(r"\*\*\d\.", cells[0]):
            continue
        name = re.sub(r"^\*\*\d\.\s*", "", cells[0]).split("**")[0].strip().lower()
        key = AREA_NAMES[name]
        share = re.search(r"([\d.]+)%", cells[1])
        areas[key] = {"share": float(share.group(1)) / 100.0, "share_text": cells[1].replace("*", ""),
                      "sets": sorted(set(re.findall(r"`(sft-[A-Za-z0-9._-]+)`", cells[3])))}
    languages: dict[str, int] = {}
    for cells in table_rows(section(text, "## 7.", "## 8.")):
        if cells and unbacktick(cells[0]) == "sft-indic-aya-dataset" and len(cells) >= 3:
            note = cells[2].replace("*", "").split("Single turn")[0]
            for name, count in re.findall(r"([A-Z][a-z]+) ([\d,]+)", note):
                languages[name] = to_int(count)
    return {"areas": areas, "aya_dataset_language_rows": languages,
            "table_total_percent": round(sum(a["share"] for a in areas.values()) * 100, 6)}


# --- OCR-2 records -------------------------------------------------------------------------------------

def ocr2_from_report(report: dict) -> dict:
    """Numbers the aggregate full-run record states (counts, token totals, families). Nothing is recomputed."""
    counts, dedup = report["counts"], report["dedup"]
    t = counts["totals"]
    kept_dedup = dedup["kept"]
    return {
        "raw": t["joined.raw_rows"], "policy_excluded": t["joined.policy_excluded"],
        "held": t["joined.malformed_or_unresolved"], "joined": t["joined.eligible_joined"],
        "converter_rejected": t["rendered.converter_rejected"], "rendered": t["rendered.rendered"],
        "removed": t["screened.rows_removed"], "canary": t["screened.rows_canary"], "kept": t["screened.rows_kept"],
        "admitted": t["pack.admitted"], "pack_attempted": t["pack.attempted"],
        "outcomes": counts["outcomes"], "by_source": counts["by_source"], "codeforces_train": counts["codeforces_train"],
        "rendered_tokens": counts["tokens"]["rendered_tokens"],
        "rendered_trained_tokens": counts["tokens"]["rendered_trained_tokens"],
        "kept_tokens": dedup["tokens"]["kept_tokens"], "kept_trained_tokens": dedup["tokens"]["kept_trained_tokens"],
        "kept_positions": dedup["tokens"]["kept_positions"],
        "kept_content_clusters_c08": dedup["tokens"]["kept_content_clusters_C08"],
        "kept_by_source_positions": kept_dedup["P"]["by_source_positions"],
        "shards": len(report["shards_loaded"]), "states": counts["states"],
        "identities": counts["total_identities"],
    }


def ocr2_from_shards(run_dir: Path, report: dict) -> dict:
    """Recompute kept-row statistics from the per-shard records named in the report's `sources`.

    Each record is a gzip JSON whose `summary` holds `rows_schema` and one list per rendered row
    (`dataset`, `kept`, `tokens`, `trained_tokens`, `family_sha256`, ...). Rows carry hashes and counts, no text.
    """
    kept_tokens: list[int] = []
    per_source = defaultdict(lambda: {"rows": 0, "tokens": 0, "trained": 0, "families": set()})
    rendered = {"rows": 0, "tokens": 0, "trained": 0}
    rendered_effort = {e: 0 for e in EFFORTS}
    families: set[str] = set()
    seen_ids: set[str] = set()
    pack_len_max = 0
    run_ids: set = set()
    blockers_by_shard: list[tuple] = []
    shard_sha = {}
    shard_records = 0
    for sid in sorted(report["sources"], key=int):
        record = json.loads(gzip.open(run_dir / report["sources"][sid], "rt", encoding="utf-8").read())
        summary = record.get("summary", record)
        ix = {k: i for i, k in enumerate(summary["rows_schema"])}
        shard_records += 1
        run_ids.add(summary.get("run_id"))
        dl = record.get("download") or {}
        shard_sha[int(sid)] = {"sha256": dl.get("sha256"), "bytes": dl.get("bytes"),
                               "sig_sha256": summary.get("sig_sha256"), "run_id": summary.get("run_id"),
                               "config_sha256": summary.get("config_sha256")}
        for e, n in summary["shard"]["counts"]["rendered"]["effort"].items():
            rendered_effort[e] += n
        for r in summary["rows"]:
            oid = r[ix["ocr_id"]]
            if oid in seen_ids:
                raise ValueError(f"duplicate ocr_id {oid} across shard records")
            seen_ids.add(oid)
            if r[ix["rendered"]]:
                rendered["rows"] += 1
                rendered["tokens"] += r[ix["tokens"]]
                rendered["trained"] += r[ix["trained_tokens"]]
            if r[ix["kept"]]:
                ds = r[ix["dataset"]]
                kept_tokens.append(r[ix["tokens"]])
                ps = per_source[ds]
                ps["rows"] += 1
                ps["tokens"] += r[ix["tokens"]]
                ps["trained"] += r[ix["trained_tokens"]]
                ps["families"].add(r[ix["family_sha256"]])
                families.add(r[ix["family_sha256"]])
        pack_counts = summary["shard"]["counts"]["pack"]
        blockers_by_shard.append(tuple(pack_counts.get("blockers", [])))
        pack_len_max = max(pack_len_max, pack_counts["passed_rows"].get("length_max") or 0)
    caps = {}
    sorted_len = sorted(kept_tokens)
    for cap in CANDIDATE_CAPS:
        under = [t for t in sorted_len if t <= cap]
        caps[str(cap)] = {"rows": len(under), "tokens": sum(under)}
    return {
        "shard_records_read": shard_records, "shard_sha": shard_sha, "rendered": rendered,
        "rendered_effort": rendered_effort, "kept_rows": len(kept_tokens), "kept_tokens": sum(kept_tokens),
        "kept_trained_tokens": sum(p["trained"] for p in per_source.values()),
        "kept_length": length_stats(kept_tokens), "kept_families_by_position": len(families),
        "kept_caps": caps, "pack_blockers": sorted(set().union(*blockers_by_shard)) if blockers_by_shard else [],
        "pack_blockers_identical_in_every_shard": len(set(blockers_by_shard)) <= 1, "run_ids": sorted(x for x in run_ids if x), "pack_length_max_over_shards": pack_len_max,
        "per_source": {ds: {"rows": p["rows"], "tokens": p["tokens"], "trained": p["trained"],
                            "families": len(p["families"])} for ds, p in sorted(per_source.items())},
        "family_union_equals_sum": len(families) == sum(len(p["families"]) for p in per_source.values()),
    }


def ocr2_hashes(full_run_path: Path, run_dir: Path | None) -> dict:
    """Source and run hashes for OCR-2. Without the run folder only the aggregate record's hash is known."""
    out = {"ocr2_full_run_sha256": sha256_file(full_run_path), "tokenizer_sha256": None, "source_manifest_sha256": {},
           "run_id": None, "revision": None, "shard_sha256": None}
    if run_dir is None:
        return out
    manifest_path = run_dir / "manifest/source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out["source_manifest_sha256"]["shards_3_69"] = sha256_file(manifest_path)
    early = run_dir.parent / "shard0-2/source_manifest.json"
    if early.is_file():
        out["source_manifest_sha256"]["shards_0_2"] = sha256_file(early)
    out["tokenizer_sha256"] = manifest["conversion"]["tokenizer"]["sha256"]
    out["tokenizer_label"] = manifest["conversion"]["tokenizer"]["label"]
    out["max_sequence_tokens"] = manifest["conversion"]["max_sequence_tokens"]
    out["revision"] = manifest["ocr2"]["revision"]
    shards = sorted(manifest["ocr2"]["shards"], key=lambda x: x["shard_id"])
    out["shard_sha256"] = [x["sha256"] for x in shards]
    out["shard_rows"] = sum(x["rows"] for x in shards)
    out["shard_bytes"] = sum(x["bytes"] for x in shards)
    out["pins"] = {k: v.get("revision") for k, v in sorted(manifest["pins"].items()) if isinstance(v, dict)}
    out["report_0_69_sha256"] = sha256_file(run_dir / "report_0-69.json")
    return out


def read_token_records(path: Path) -> dict[str, dict]:
    """Optional measured token records, one JSON object per line, for sets whose admissible rows were tokenized.

    Required keys: set_id, rows (must equal the decontam kept rows), sequence_tokens, shifted_supervised_targets,
    tokenizer_sha256. Optional: length (as length_stats), unique_families, effort (counts by tier), basis.
    """
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["set_id"]] = rec
    return out


C3_REQUIRED = ("set_id", "scope", "rows", "sequence_tokens", "shifted_supervised_targets", "tokenizer_sha256", "content_sha256")


def read_c3_records(path: Path) -> list[dict]:
    """Optional C3 token records (WP14), one JSON object per line, one per set and scope.

    Unlike `--token-records` they need not cover the decontamination-kept rows: each states its own scope (for
    example "first 1,000 rows" or "full set, converted, not decontaminated") and is reported as that, never as a
    pack or as the kept-row supply. Required keys: set_id, scope, rows, sequence_tokens, shifted_supervised_targets,
    tokenizer_sha256, content_sha256. Optional: status, trained_tokens, length, effort, rows_over_max_len, max_len,
    skipped, rows_in, hub_revision, admission, decontam, checks_ok, rows_per_s, track.
    """
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            missing = [k for k in C3_REQUIRED if k not in rec]
            if missing:
                raise ValueError(f"c3 record for {rec.get('set_id')!r} lacks {missing}")
            out.append(rec)
    return sorted(out, key=lambda r: (r["set_id"], r["scope"]))


# --- unit records -----------------------------------------------------------------------------------------

def empty_tokens() -> dict:
    return {"status": "not_measured", "sequence_tokens": None, "shifted_supervised_targets": None,
            "tokenizer_sha256": None, "basis": "no run record holds a token count for this set"}


def approval_state(decision: str | None) -> str:
    return {"excluded": "excluded", "tsai_reserves": "tsai_reserves", "allowed": "allowed",
            None: "not_in_licence_table"}.get(decision, decision)


def eligible(unit: dict, lens: str) -> bool:
    """A set can supply training tokens if its licence state passes the lens and its coverage holds assistant rows."""
    states = ("allowed",) if lens == LENS_ALLOWED else ("allowed", "tsai_reserves")
    return unit["approval_state"] in states and unit["coverage_class"] in ("full", "partial") and not unit["problems"]


def build_units(licence: dict, results: list[dict], inputs: dict, kept_rows: dict, proposal: dict,
                ocr2_report: dict | None, ocr2_rows: dict | None, token_records: dict,
                input_hashes: dict) -> tuple[list[dict], list[dict]]:
    """One record per Stage 1 set (plus one per OCR-2 source). Returns (units, contradictions)."""
    contradictions: list[dict] = []

    def contradiction(kind: str, detail: str, subject: str = "") -> None:
        contradictions.append({"kind": kind, "subject": subject, "detail": detail})

    by_run = {r["set_id"]: r for r in results}
    area_of, basis_of, group_of = {}, {}, {}
    for area, info in sorted(proposal["areas"].items()):
        for s in info["sets"]:
            area_of[s], basis_of[s] = area, "proposal_section_2"
    for area, groups in COMPOSITION.items():
        for name, _, members in groups:
            for s in members:
                group_of[s] = name
                if s not in area_of:
                    contradiction("composition_set_not_in_proposal_table", f"{s} is in the section 3 composition of "
                                  f"{area} but not in the section 2 table", s)
                elif area_of[s] != area:
                    contradiction("composition_area_mismatch", f"{s} is in {area} composition, {area_of[s]} table", s)
    for s, area in INFERRED_AREA.items():
        if s not in area_of:
            area_of[s], basis_of[s] = area, "inferred_from_set_name"

    units: list[dict] = []
    for set_id in sorted(licence):
        lic = licence[set_id]
        run = by_run.get(set_id)
        files = inputs.get(set_id, [])
        unit = {
            "type": "set", "set_id": set_id, "source": lic["source"], "language": lic["language"],
            "area": area_of.get(set_id), "area_basis": basis_of.get(set_id, "unassigned"),
            "group": group_of.get(set_id),
            "licence": {"decision": lic["decision_raw"], "generator": lic["generator"], "licence": lic["licence"]},
            "approval_state": approval_state(lic["decision"]),
            "pack": {"admitted_rows": None, "basis": "no pack admission report exists for this set"},
            "coverage_class": None, "coverage_basis": None,
            "hashes": {"input_files": len(files), "input_bytes": sum(f["bytes"] for f in files),
                       "input_files_sha256": [f["sha256"] for f in files],
                       "clean_sha256_prefixes": run["clean_sha256_prefixes"] if run else [],
                       "fingerprint_set_sha256": input_hashes["fingerprint_set_sha256"] if run else None},
            "rows": {"stages": {}}, "families": {"unique": None, "basis": "not_recorded"},
            "tokens": empty_tokens(), "length": None, "effort": {"counts": None, "basis": "not_recorded"},
            "context": {"limit": None, "status": "not_set",
                        "basis": "configs/config_v0.yaml data.seq_len is null (open); the OCR-2 manifest has "
                                 "max_sequence_tokens null"},
            "problems": [], "unproven": [],
        }
        if run is None:
            if unit["approval_state"] == "excluded":
                unit["coverage_class"], unit["coverage_basis"] = "excluded", "licence decision excluded; not run"
            else:
                unit["coverage_class"] = "held"
                unit["coverage_basis"] = "licence decision is not excluded but no converter or decontam record exists"
        else:
            kept_row = kept_rows.get(set_id)
            stages = {"converted": run["rows_in"], "flagged": run["flagged"], "canary": run["canary"],
                      "removed": run["removed"], "kept": run["kept"]}
            unit["rows"]["stages"] = stages
            if run["rows_in"] != run["removed"] + run["kept"]:
                contradiction("rows_do_not_balance", f"rows in {run['rows_in']} != removed {run['removed']} + kept "
                              f"{run['kept']}", set_id)
            if kept_row is None:
                if set_id != "sft-safety-aegis-v1":
                    contradiction("missing_in_kept_rows_table", "decontam_report.md runs it, decontam_kept_rows.md "
                                  "does not list it", set_id)
            elif (kept_row["rows_in"], kept_row["removed"], kept_row["kept"]) != (run["rows_in"], run["removed"],
                                                                                 run["kept"]):
                contradiction("kept_rows_table_differs", f"decontam_kept_rows.md {kept_row} vs decontam_report.md "
                              f"{ {k: run[k] for k in ('rows_in', 'removed', 'kept')} }", set_id)
            if unit["approval_state"] == "excluded":
                contradiction("excluded_set_has_run_record", "licence decision is excluded but it was run", set_id)
            if set_id == "sft-safety-aegis-v1":
                unit["coverage_class"] = "text-only"
                unit["coverage_basis"] = "the stored text column was scanned; the set has no assistant turn"
                unit["tokens"] = dict(empty_tokens(), shifted_supervised_targets=0, status="not_measured",
                                      basis="no assistant turn: 0 supervised targets by construction (text-only)")
            elif run["source_rows_stated"] is not None and run["source_rows_stated"] != run["rows_in"]:
                unit["coverage_class"] = "partial"
                unit["coverage_basis"] = (f"{run['rows_in']:,} of {run['source_rows_stated']:,} source rows were "
                                          "converted; the rest are over the 64k effort budget and were not scanned")
            elif run["run_on"].startswith("all 70 python shards"):
                unit["coverage_class"] = "partial"
                unit["coverage_basis"] = "all shards ran, but only joined rows reach the scan; some rows are held"
            else:
                unit["coverage_class"] = "full"
                unit["coverage_basis"] = "every row the converter produced from the selected source was scanned"
        units.append(unit)
    for s in sorted(set(by_run) - set(licence)):
        contradiction("run_set_not_in_licence_table", f"{s} has a decontam record but no Stage 1 row", s)

    by_id = {u["set_id"]: u for u in units}
    # OCR-2: the only set with token records.
    ocr = by_id.get("sft-code-opencodereasoning-2")
    if ocr is not None and ocr2_report is not None:
        fill_ocr2(ocr, ocr2_report, ocr2_rows, by_run.get(ocr["set_id"]), contradiction, input_hashes)
    # Optional measured records for other sets.
    for set_id, rec in sorted(token_records.items()):
        unit = by_id.get(set_id)
        if unit is None or set_id == "sft-code-opencodereasoning-2":
            contradiction("token_record_ignored", "no such set, or the set already has an OCR-2 record", set_id)
            continue
        kept = unit["rows"]["stages"].get("kept")
        if rec.get("rows") != kept:
            contradiction("token_record_rows_differ", f"token record rows {rec.get('rows')} != kept rows {kept}", set_id)
            continue
        unit["tokens"] = {"status": "measured", "sequence_tokens": rec["sequence_tokens"],
                          "shifted_supervised_targets": rec["shifted_supervised_targets"],
                          "tokenizer_sha256": rec.get("tokenizer_sha256"),
                          "basis": rec.get("basis", "token record on the admissible (kept) rows")}
        unit["length"] = rec.get("length")
        if rec.get("unique_families") is not None:
            unit["families"] = {"unique": rec["unique_families"], "basis": "token record"}
        if rec.get("effort"):
            unit["effort"] = {"counts": rec["effort"], "basis": "token record"}

    for unit in units:
        unit["problems"] = check_unit(unit)
        unit["unproven"] = unproven_notes(unit)
    return units, contradictions


def fill_ocr2(unit: dict, rep: dict, rows: dict | None, run_row: dict | None, contradiction, input_hashes: dict) -> None:
    agg = ocr2_from_report(rep)
    unit["rows"] = {"stages": {
        "raw": agg["raw"], "policy_excluded": agg["policy_excluded"], "held": agg["held"], "joined": agg["joined"],
        "converter_rejected": agg["converter_rejected"], "converted": agg["rendered"], "flagged": agg["removed"],
        "canary": agg["canary"], "removed": agg["removed"], "kept": agg["kept"], "pack_attempted": agg["pack_attempted"],
        "pack_admitted": agg["admitted"]},
        "outcomes_before_scan": dict(sorted(agg["outcomes"].items()))}
    unit["pack"] = {"admitted_rows": agg["admitted"], "basis": "pack_report totals of the 70 shard records "
                    "(blockers: no tokenizer approved, no context limit, set not allowed, source identity "
                    "not verified)"}
    unit["hashes"].update(input_hashes["ocr2"])
    unit["coverage_basis"] = (f"all {agg['shards']} shards ran; only the {agg['joined']:,} joined rows reach the scan and "
                              f"{agg['held']:,} open-r1/codeforces train rows are held (producer revision not established)")
    tokens = {"status": "measured", "sequence_tokens": agg["kept_tokens"],
              "shifted_supervised_targets": agg["kept_trained_tokens"],
              "tokenizer_sha256": input_hashes["ocr2"]["tokenizer_sha256"],
              "basis": "sum over the 427,152 kept (admissible) rows, tokenizer v0.1 development fixture, not the "
                       "frozen tokenizer"}
    unit["tokens"] = tokens
    unit["families"] = {"unique": agg["kept_positions"], "unique_by_content_jaccard_0_8": agg["kept_content_clusters_c08"],
                        "basis": "problem positions over kept rows; content clusters at estimated Jaccard 0.8 "
                                 "(MinHash, exact-duplicate rows 0)"}
    unit["effort"] = {"counts": None, "basis": "tier counts exist for the 542,219 rendered rows only, not for kept rows"}
    if run_row and (run_row["rows_in"], run_row["removed"], run_row["kept"]) != (agg["rendered"], agg["removed"],
                                                                                  agg["kept"]):
        contradiction("ocr2_report_vs_decontam", f"ocr2_full_run.json {agg['rendered']}/{agg['removed']}/"
                      f"{agg['kept']} vs decontam_report.md {run_row['rows_in']}/{run_row['removed']}/{run_row['kept']}",
                      unit["set_id"])
    if agg["raw"] != agg["policy_excluded"] + agg["held"] + agg["joined"]:
        contradiction("ocr2_stage_identity", "raw != policy excluded + held + joined", unit["set_id"])
    if rows is not None:
        unit["length"] = rows["kept_length"]
        unit["effort"] = {"counts": rows["rendered_effort"], "basis": "rendered rows (542,219), kept rows not split"}
        unit["context"].update(rows_fitting_whole_sample=rows["kept_caps"],
                               fit_basis="kept rows whose whole rendered sample has tokens <= cap; whole rows dropped, "
                                         "no truncation; counts from the per-shard records")
        unit["hashes"]["shard_records_read"] = rows["shard_records_read"]
        unit["pack"]["blockers"] = rows["pack_blockers"]
        unit["pack"]["blockers_identical_in_every_shard"] = rows["pack_blockers_identical_in_every_shard"]
        checks = [("kept rows", rows["kept_rows"], agg["kept"]), ("kept tokens", rows["kept_tokens"], agg["kept_tokens"]),
                  ("kept trained tokens", rows["kept_trained_tokens"], agg["kept_trained_tokens"]),
                  ("rendered rows", rows["rendered"]["rows"], agg["rendered"]),
                  ("rendered tokens", rows["rendered"]["tokens"], agg["rendered_tokens"]),
                  ("rendered trained tokens", rows["rendered"]["trained"], agg["rendered_trained_tokens"]),
                  ("kept problem positions", rows["kept_families_by_position"], agg["kept_positions"])]
        for name, got, stated in checks:
            if got != stated:
                contradiction("ocr2_recompute_mismatch", f"{name}: recomputed from shard records {got:,}, stated "
                              f"{stated:,}", unit["set_id"])
        for ds, stated in agg["kept_by_source_positions"].items():
            got = rows["per_source"].get(ds, {}).get("families")
            if got != stated:
                contradiction("ocr2_recompute_mismatch", f"{ds} kept positions: recomputed {got}, stated {stated}",
                              unit["set_id"])


def ocr2_subsets(rep: dict, rows: dict | None) -> list[dict]:
    """One line per OCR-2 source split: rows by stage (from the aggregate) and kept statistics (from shard records)."""
    agg = ocr2_from_report(rep)
    out = []
    for split, outcomes in sorted(agg["by_source"].items()):
        total = sum(outcomes.values())
        ds = split.split("/")[0]
        kept = rows["per_source"].get(ds) if rows and split.endswith("/train") else None
        held = outcomes.get("held_source_unavailable", 0)
        protected = outcomes.get("policy_protected_split", 0)
        if held:
            cov = "held"
        elif protected and not outcomes.get("eligible_joined"):
            cov = "excluded"
        else:
            cov = "partial"
        entry = {"type": "subset", "parent": "sft-code-opencodereasoning-2", "subset": split, "coverage_class": cov,
                 "rows_raw": total, "rows_by_outcome": dict(sorted(outcomes.items()))}
        if cov == "excluded":
            entry["basis"] = "upstream test or validation split: never joined, hashes only (policy_protected_split)"
        if cov == "held":
            left_out = total - held
            entry["basis"] = (f"open-r1/codeforces train: the producer revision is not established, so {held:,} rows are "
                              f"held and {left_out:,} were left out earlier on the quality proposal")
        if kept and not cov == "held":
            entry.update(kept_rows=kept["rows"], kept_tokens=kept["tokens"], kept_shifted_supervised_targets=kept["trained"],
                         kept_unique_families_by_position=kept["families"])
        out.append(entry)
    return out


# --- checks on one record ----------------------------------------------------------------------------------

def check_unit(unit: dict) -> list[str]:
    """Reasons a record cannot be trusted as supply. An empty list means none found; it is not a proof."""
    problems = []
    tok, stages = unit["tokens"], unit["rows"]["stages"]
    kept = stages.get("kept")
    if tok["status"] == "measured":
        seq, tgt = tok["sequence_tokens"], tok["shifted_supervised_targets"]
        if not tok.get("tokenizer_sha256"):
            problems.append("tokens_without_tokenizer_hash")
        if kept is not None and kept > 0 and (seq is None or seq < kept):
            problems.append("rows_tokens_mismatch")          # every rendered row has at least one token
        if kept == 0 and seq:
            problems.append("rows_tokens_mismatch")
        if seq is not None and tgt is not None and tgt > seq:
            problems.append("targets_exceed_tokens")
        if kept and tgt == 0:
            problems.append("zero_assistant_targets")
        ln = unit.get("length")
        if ln and kept is not None and ln.get("n") != kept:
            problems.append("length_rows_mismatch")
        if ln and seq is not None and abs(ln["mean"] * ln["n"] - seq) > 0.5 * ln["n"]:
            problems.append("length_mean_vs_tokens_mismatch")
    if tok.get("shifted_supervised_targets") == 0 and unit["coverage_class"] == "text-only":
        problems.append("zero_assistant_targets")
    st = stages
    if "converted" in st and "removed" in st and "kept" in st and st["converted"] != st["removed"] + st["kept"]:
        problems.append("rows_do_not_balance")
    fam = unit["families"].get("unique")
    if fam is not None and kept is not None and fam > kept:
        problems.append("families_exceed_rows")
    return sorted(set(problems))


def unproven_notes(unit: dict) -> list[str]:
    notes = []
    if unit["tokens"]["status"] != "measured" and unit["coverage_class"] in ("full", "partial"):
        notes.append("token supply not measured: no run record holds sequence or supervised token counts")
    if unit["families"].get("unique") is None and unit["coverage_class"] in ("full", "partial"):
        notes.append("unique problem families not recorded")
    if unit["tokens"]["status"] == "measured":
        notes.append("tokens use the v0.1 development tokenizer; the frozen tokenizer is not yet applied")
    if unit["area_basis"] == "inferred_from_set_name":
        notes.append("area inferred from the set name; the proposal's area table does not list this set")
    if unit["area"] is None and unit["coverage_class"] != "excluded":
        notes.append("area not assigned by the proposal")
    if unit["approval_state"] == "tsai_reserves":
        notes.append("licence decision is TSAI reserves: not approved for training")
    if unit["context"]["status"] == "not_set":
        notes.append("model context limit not set")
    return notes


def family_overlap(family_sets: dict[str, set]) -> dict:
    """Duplicate problem families across sources. A family that appears in two sources is one family for diversity."""
    seen: dict[str, list[str]] = defaultdict(list)
    for src in sorted(family_sets):
        for fam in family_sets[src]:
            seen[fam].append(src)
    union = len(seen)
    total = sum(len(v) for v in family_sets.values())
    pairs: dict[str, int] = defaultdict(int)
    for srcs in seen.values():
        if len(srcs) > 1:
            pairs["+".join(srcs)] += 1
    return {"sum_of_sources": total, "unique_families": union, "duplicated": total - union, "pairs": dict(sorted(pairs.items()))}


# --- mixture arithmetic ------------------------------------------------------------------------------------

def requested_tokens(budget: int, share: float) -> float:
    return budget * share


def minimum_exposure(assigned_tokens: float, supply_tokens: int) -> float | None:
    """assigned tokens / unique eligible token supply; None when the supply is zero or unknown."""
    if not supply_tokens:
        return None
    return assigned_tokens / supply_tokens


def check_shares(shares: dict[str, float], groups: dict | None = None) -> list[str]:
    problems = []
    unknown = sorted(set(shares) - set(AREAS))
    if unknown:
        problems.append(f"unknown_area:{','.join(unknown)}")
    if any(v < 0 for v in shares.values()):
        problems.append("negative_share")
    total = sum(shares.values())
    if abs(total - 1.0) > SHARE_TOLERANCE:
        problems.append(f"shares_sum_{total:.6f}_not_1")
    if groups is not None:
        for area, share in sorted(shares.items()):
            if share > 0:
                g = groups.get(area)
                if not g:
                    problems.append(f"{area}_has_share_but_no_composition_group")
                elif abs(sum(f for _, f, _ in g) - 1.0) > 1e-9:
                    problems.append(f"{area}_group_fractions_not_1")
    return problems


def group_capacity(group: tuple, area_request: float, units_by_id: dict[str, dict], lens: str) -> dict:
    name, fraction, member_ids = group
    request = area_request * fraction
    members = [units_by_id[s] for s in member_ids if s in units_by_id]
    missing = [s for s in member_ids if s not in units_by_id]
    counted = [u for u in members if eligible(u, lens)]
    reasons = []
    for u in members:
        if not eligible(u, lens):
            why = ("excluded" if u["approval_state"] == "excluded" else
                   "text-only (0 assistant targets)" if u["coverage_class"] == "text-only" else
                   "held (no record)" if u["coverage_class"] == "held" else
                   "licence state not in lens" if u["approval_state"] not in (("allowed",) if lens == LENS_ALLOWED
                                                                                 else ("allowed", "tsai_reserves"))
                   else "record problems: " + ",".join(u["problems"]))
            reasons.append(f"{u['set_id']}: {why}")
    measured = [u for u in counted if u["tokens"]["status"] == "measured"]
    unmeasured = [u for u in counted if u["tokens"]["status"] != "measured"]
    supply = sum(u["tokens"]["sequence_tokens"] for u in measured)
    supervised = sum(u["tokens"]["shifted_supervised_targets"] for u in measured)
    complete = bool(counted) and not unmeasured
    status = {}
    for cap in REPEAT_CAPS:
        if request <= 0:
            status[f"{cap}x"] = "NO_REQUEST"
        elif not counted:
            status[f"{cap}x"] = "INFEASIBLE: no eligible source (" + "; ".join(reasons or ["no member"]) + ")"
        elif supply and request <= cap * supply:
            status[f"{cap}x"] = "FEASIBLE" if complete else "FEASIBLE_ON_MEASURED"
        elif complete:
            status[f"{cap}x"] = f"INFEASIBLE: exposure {request / supply:.3f}x exceeds {cap}x" if supply else \
                "INFEASIBLE: eligible supply is 0 tokens"
        else:
            status[f"{cap}x"] = "UNMEASURED"
    return {"group": name, "fraction_of_area": round(fraction, 9), "requested_tokens": request,
            "eligible_sets": [u["set_id"] for u in counted], "ineligible": reasons, "missing_from_ledger": missing,
            "measured_sets": [u["set_id"] for u in measured], "unmeasured_sets": [u["set_id"] for u in unmeasured],
            "supply_tokens_measured": supply, "supervised_targets_measured": supervised,
            "supply_complete": complete, "minimum_exposure": minimum_exposure(request, supply),
            "exposure_note": (None if complete else "upper bound on exposure: unmeasured members only add supply"
                              if supply else "no measured supply"),
            "status": status}


def capacity_records(units: list[dict], scenarios: dict[str, dict[str, float]]) -> list[dict]:
    by_id = {u["set_id"]: u for u in units if u["type"] == "set"}
    out = []
    for sname, shares in sorted(scenarios.items()):
        problems = check_shares(shares, COMPOSITION)
        for budget in BUDGETS:
            for lens in LENSES:
                maxima = {f"{c}x": [] for c in REPEAT_CAPS}
                recs = []
                for area in AREAS:
                    share = shares.get(area, 0.0)
                    area_request = requested_tokens(budget, share)
                    for g in COMPOSITION.get(area, []):
                        rec = group_capacity(g, area_request, by_id, lens)
                        rec.update(type="capacity", scenario=sname, lens=lens, budget_tokens=budget, area=area,
                                   area_share=share)
                        recs.append(rec)
                        if share > 0 and g[1] > 0:
                            for c in REPEAT_CAPS:
                                maxima[f"{c}x"].append((c * rec["supply_tokens_measured"] / (share * g[1]),
                                                        rec["supply_complete"], area, g[0]))
                out.extend(recs)
                total = {"type": "capacity_total", "scenario": sname, "lens": lens, "budget_tokens": budget,
                         "share_problems": problems, "max_total_tokens": {}}
                for c in REPEAT_CAPS:
                    vals = maxima[f"{c}x"]
                    if not vals:
                        total["max_total_tokens"][f"{c}x"] = None
                        continue
                    low = min(vals)
                    total["max_total_tokens"][f"{c}x"] = {
                        "value": int(low[0]), "exact": all(v[1] for v in vals),
                        "binding": f"{low[2]}: {low[3]}",
                        "note": "exact" if all(v[1] for v in vals) else
                        "lower bound at best: unmeasured sources only add supply; 0 here means no measured supply"}
                out.append(total)
    return out


def effort_cell_check(requests: dict, supply: dict, cap: int) -> list[dict]:
    """Per (area, effort) cell: INFEASIBLE if tokens are requested from a cell with no supply, or more than cap x supply."""
    out = []
    for cell in sorted(requests):
        req, sup = requests[cell], supply.get(cell, 0)
        if req <= 0:
            continue
        if sup <= 0:
            out.append({"cell": list(cell), "verdict": "INFEASIBLE", "reason": "impossible cell: requested tokens, "
                        "no supply"})
        elif req > cap * sup:
            out.append({"cell": list(cell), "verdict": "INFEASIBLE",
                        "reason": f"exposure {req / sup:.3f}x exceeds {cap}x"})
    return out


# --- ledger and report -------------------------------------------------------------------------------------

def indic_language_cells(languages: dict[str, int]) -> list[dict]:
    total = sum(languages.values())
    return [{"type": "language_cell", "set_id": "sft-indic-aya-dataset", "language": lang, "rows": n,
             "share_of_set": round(n / total, 6) if total else None,
             "flag": "zero rows" if n == 0 else "under 1,000 rows" if n < 1000 else None}
            for lang, n in sorted(languages.items(), key=lambda kv: (-kv[1], kv[0]))]


def collect(repo_team: Path, ocr2_runs: Path | None, token_records_path: Path | None,
            c3_records_path: Path | None = None) -> list[dict]:
    paths = {"licence": repo_team / "licences/licence_table.md", "decontam": repo_team / "sft/decontam_report.md",
             "kept_rows": repo_team / "sft/decontam_kept_rows.md", "proposal": repo_team / "sft/sft_mix_proposal.md",
             "ocr2_full_run": repo_team / "sft/results/ocr2_full_run.json"}
    for name, p in paths.items():
        if not p.is_file():
            raise FileNotFoundError(f"{name}: {p} not found")
    texts = {k: p.read_text(encoding="utf-8") for k, p in paths.items() if k != "ocr2_full_run"}
    report = json.loads(paths["ocr2_full_run"].read_text(encoding="utf-8"))
    licence = parse_licence_stage1(texts["licence"])
    results, head = parse_decontam_results(texts["decontam"])
    inputs = parse_decontam_inputs(texts["decontam"])
    kept_rows, kept_total = parse_kept_rows(texts["kept_rows"])
    proposal = parse_proposal(texts["proposal"])
    rows = None
    if ocr2_runs is not None:
        rep_file = ocr2_runs / "report_0-69.json"
        if sha256_file(rep_file) != sha256_file(paths["ocr2_full_run"]):
            raise ValueError("report_0-69.json differs from sft/results/ocr2_full_run.json")
        rows = ocr2_from_shards(ocr2_runs, report)
    tok_records = read_token_records(token_records_path) if token_records_path else {}

    input_hashes = {"fingerprint_set_sha256": head["set_sha256"],
                    "ocr2": ocr2_hashes(paths["ocr2_full_run"], ocr2_runs)}
    units, contradictions = build_units(licence, results, inputs, kept_rows, proposal, report, rows, tok_records,
                                        input_hashes)
    # Section-level reconciliation of the two documents.
    if head.get("sets_run") != len(results):
        contradictions.append({"kind": "decontam_header", "subject": "decontam_report.md",
                               "detail": f"header says {head.get('sets_run')} sets, section 1 has {len(results)}"})
    for key, calc in (("rows_in", sum(r["rows_in"] for r in results)), ("removed", sum(r["removed"] for r in results)),
                      ("kept", sum(r["kept"] for r in results))):
        if head.get(key) != calc:
            contradictions.append({"kind": "decontam_header", "subject": "decontam_report.md",
                                   "detail": f"header {key} {head.get(key):,} vs sum of rows {calc:,}"})
    kept_calc = {k: sum(v[k] for v in kept_rows.values()) for k in ("rows_in", "removed", "kept")}
    if kept_total and kept_total != kept_calc:
        contradictions.append({"kind": "kept_rows_total", "subject": "decontam_kept_rows.md",
                               "detail": f"total row {kept_total} vs sum {kept_calc}"})
    aegis = next((r for r in results if r["set_id"] == "sft-safety-aegis-v1"), None)
    if aegis and head.get("rows_in") is not None and kept_total:
        if kept_total["rows_in"] + aegis["rows_in"] != head["rows_in"]:
            contradictions.append({"kind": "kept_rows_total", "subject": "decontam_kept_rows.md",
                                   "detail": "33-set total plus the aegis text column does not equal the 34-set total"})
    for area, info in sorted(proposal["areas"].items()):
        for s in info["sets"]:
            u = next((x for x in units if x["set_id"] == s), None)
            if u is None:
                contradictions.append({"kind": "proposal_set_not_in_licence_table", "subject": s,
                                       "detail": f"named in the {area} row of the proposal table"})
            elif u["approval_state"] == "excluded":
                contradictions.append({"kind": "proposal_table_names_excluded_set", "subject": s,
                                       "detail": f"named in the active {area} row of the proposal table; the licence "
                                                 "table says excluded"})
    scenarios = {"proposal_table": {a: i["share"] for a, i in proposal["areas"].items()},
                 "plan_d3": dict(PLAN_SCENARIO)}
    for name, sh in sorted(scenarios.items()):
        for p in check_shares(sh):
            contradictions.append({"kind": "share_scenario", "subject": name, "detail": p})

    sets = [u for u in units]
    sub = ocr2_subsets(report, rows)
    extra = []
    if rows is not None:
        extra.append({"type": "note", "id": "ocr2_family_positions",
                      "per_source_kept_positions": {k: v["families"] for k, v in rows["per_source"].items()},
                      "union_equals_sum_of_sources": rows["family_union_equals_sum"]})
    cap = capacity_records(sets, scenarios)
    langs = indic_language_cells(proposal["aya_dataset_language_rows"])

    meta = {"type": "meta", "schema": SCHEMA, "budget_unit": "total processed non-padding tokens (proposal; "
            "supervised-target share reported beside it)", "budgets_illustrative": list(BUDGETS),
            "repeat_caps": list(REPEAT_CAPS), "effort_shares_proposal": EFFORT_SHARES,
            "scenarios": scenarios, "inputs_sha256": {
                k: sha256_file(p) for k, p in sorted(paths.items())},
            "ocr2_row_level_recompute": rows is not None,
            "counts": {
                "scanned_entries_in_decontam_report": len(results),
                "stage1_sets": len(licence),
                "coverage": {c: sum(1 for u in sets if u["coverage_class"] == c) for c in COVERAGE},
                "approved_complete_training_packs": 0,
                "approved_complete_training_packs_basis": "no pack admission report exists for any set other than "
                                                          "OCR-2, whose pack report shows 0 admitted rows",
                "sets_with_measured_tokens": sum(1 for u in sets if u["tokens"]["status"] == "measured"),
                "sets_with_record_problems": sum(1 for u in sets if u["problems"])}}
    c3 = []
    if c3_records_path is not None:
        known = {u["set_id"]: u for u in units}
        for rec in read_c3_records(c3_records_path):
            if rec["set_id"] not in known:
                contradictions.append({"kind": "c3_record_set_not_in_licence_table", "subject": rec["set_id"],
                                       "detail": "a C3 token record names a set the licence table does not list"})
                continue
            c3.append({"type": "c3_token_record", **rec, "licence_decision": known[rec["set_id"]]["approval_state"]})
        meta["counts"]["sets_with_c3_records"] = len({r["set_id"] for r in c3})
        meta["counts"]["c3_records"] = len(c3)
    lines = [meta] + sets + sub + langs + cap + extra + c3 + \
        [dict(type="contradiction", **c) for c in sorted(contradictions, key=lambda c: (c["kind"], c["subject"], c["detail"]))]
    return lines


def dump_jsonl(records: list[dict]) -> str:
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n" for r in records)


def fmt(n) -> str:
    return "n/a" if n is None else f"{int(n):,}"


def render_markdown(records: list[dict]) -> str:
    meta = records[0]
    sets = [r for r in records if r["type"] == "set"]
    cap = [r for r in records if r["type"] == "capacity"]
    tot = [r for r in records if r["type"] == "capacity_total"]
    contr = [r for r in records if r["type"] == "contradiction"]
    langs = [r for r in records if r["type"] == "language_cell"]
    subs = [r for r in records if r["type"] == "subset"]
    c = meta["counts"]
    ocr = next(s for s in sets if s["set_id"] == "sft-code-opencodereasoning-2")
    L: list[str] = []
    w = L.append
    w("# Eligibility ledger and mixture capacity (G10 SFT, Package D3)")
    w("")
    w("Generated by `sft/mix_inventory.py` from the documents on this branch. Every number below is read from a "
      "record or computed from one. Rebuild with `python sft/mix_inventory.py build --ocr2-runs <folder> --verify`; "
      "the folder (`report_0-69.json` and its 70 shard records) is a private run folder that is not on the branch, so "
      "without it the OCR-2 row-level lines (length percentiles, per-source tokens, context fit) are not recomputed. "
      "The machine-readable ledger is `sft/results/eligibility_ledger.jsonl` (one JSON object per line: `meta`, `set`, "
      "`subset`, `language_cell`, `capacity`, `capacity_total`, `note`, `contradiction`).")
    w("")
    w("Inputs (sha256): " + "; ".join(f"`{k}` `{v[:12]}…`" for k, v in meta["inputs_sha256"].items()) + ".")
    w("")
    w("**Status words.** *Measured* = a run record holds the number. *Not measured* = no record holds it; the field is "
      "null and nothing is estimated. *Unproven* = a statement no record supports. Nothing here is a training "
      "approval: scanned, eligible-retained, approved-pack and trained-result are four different milestones.")
    w("")
    w("## 1. What the ledger holds")
    w("")
    w(f"- **Scanned entries:** {c['scanned_entries_in_decontam_report']} in `decontam_report.md` (this counts partial "
      "subsets and the Aegis text column). **Approved complete training packs:** "
      f"{c['approved_complete_training_packs']} ({c['approved_complete_training_packs_basis']}). These are separate numbers.")
    w(f"- **Stage 1 sets in the licence table:** {c['stage1_sets']}. Coverage class: " +
      ", ".join(f"{k} {v}" for k, v in c["coverage"].items()) + ".")
    w(f"- **Sets with a measured token count:** {c['sets_with_measured_tokens']} of {c['stage1_sets']} "
      "(OCR-2 only). The decontamination runs recorded rows, not tokens, for the other scanned sets. "
      "This is the main gap: see section 5.")
    w(f"- **Sets whose record fails an internal check:** {c['sets_with_record_problems']}.")
    w("- **Model context limit:** not set (`configs/config_v0.yaml` `data.seq_len` is null; the OCR-2 manifest has "
      "`max_sequence_tokens` null). Any statement that a row \"fits\" is therefore unproven; section 3 shows "
      "how many OCR-2 rows fit each candidate length.")
    w("")
    w("## 2. Supply per set (scanned sets)")
    w("")
    w("`kept` = rows after Team 9 fingerprints v2 removal. `tokens` = whole rendered sample (tokenizer v0.1, "
      "development fixture); `targets` = loss-masked assistant tokens after the one-token shift. Area `*` = inferred "
      "from the set name (not in the proposal's area table). `approval` is the licence-table decision, not a pack admission.")
    w("")
    w("| Set | Area | Approval | Coverage | Rows in | Kept | Tokens | Targets | Families |")
    w("|---|---|---|---|---:|---:|---:|---:|---:|")
    for s in sets:
        if s["coverage_class"] in ("excluded", "held") and not s["rows"]["stages"]:
            continue
        st = s["rows"]["stages"]
        area = (s["area"] or "-") + ("*" if s["area_basis"] == "inferred_from_set_name" else "")
        tk = s["tokens"]
        w(f"| `{s['set_id']}` | {area} | {s['approval_state']} | {s['coverage_class']} | {fmt(st.get('converted'))} | "
          f"{fmt(st.get('kept'))} | {fmt(tk['sequence_tokens'])} | {fmt(tk['shifted_supervised_targets'])} | "
          f"{fmt(s['families']['unique'])} |")
    w("")
    held = [s["set_id"] for s in sets if s["coverage_class"] == "held"]
    excl = [s["set_id"] for s in sets if s["coverage_class"] == "excluded"]
    w(f"Not in the table above: **held** (licence not excluded, no converter or decontam record), {len(held)}: "
      + ", ".join(f"`{x}`" for x in held) + f". **Excluded** by the licence table, {len(excl)}: "
      + ", ".join(f"`{x}`" for x in excl) + ".")
    w("")
    w("### OCR-2 (`sft-code-opencodereasoning-2`), the one set with token records")
    w("")
    stg = ocr["rows"]["stages"]
    w(f"Rows by stage: raw {fmt(stg['raw'])}; policy-excluded {fmt(stg['policy_excluded'])}; held {fmt(stg['held'])}; "
      f"joined {fmt(stg['joined'])}; converter-rejected {fmt(stg['converter_rejected'])}; rendered {fmt(stg['converted'])}; "
      f"removed by the scan {fmt(stg['removed'])}; **kept {fmt(stg['kept'])}**; admitted {fmt(stg['pack_admitted'])}.")
    w("")
    ln = ocr["length"]
    if ln:
        w(f"Kept-row sequence length (tokens, recomputed from the 70 shard records): min {fmt(ln['min'])}, p50 {fmt(ln['p50'])}, "
          f"p90 {fmt(ln['p90'])}, p95 {fmt(ln['p95'])}, p99 {fmt(ln['p99'])}, max {fmt(ln['max'])}, mean {ln['mean']:,}.")
        w("")
    w(f"Supply: **{fmt(ocr['tokens']['sequence_tokens'])} sequence tokens**, **{fmt(ocr['tokens']['shifted_supervised_targets'])} "
      f"supervised targets** ({ocr['tokens']['shifted_supervised_targets'] / ocr['tokens']['sequence_tokens']:.1%} of tokens), over "
      f"{fmt(ocr['families']['unique'])} problems by position ({fmt(ocr['families']['unique_by_content_jaccard_0_8'])} by content at "
      "estimated Jaccard 0.8). Completions repeat problems: they are distinct tokens but one family each.")
    w("")
    w("| OCR-2 source split | Coverage | Raw rows | Kept rows | Kept tokens | Kept targets | Kept problems |")
    w("|---|---|---:|---:|---:|---:|---:|")
    for sb in subs:
        w(f"| `{sb['subset']}` | {sb['coverage_class']} | {fmt(sb['rows_raw'])} | {fmt(sb.get('kept_rows'))} | "
          f"{fmt(sb.get('kept_tokens'))} | {fmt(sb.get('kept_shifted_supervised_targets'))} | "
          f"{fmt(sb.get('kept_unique_families_by_position'))} |")
    w("")
    if ocr["context"].get("rows_fitting_whole_sample"):
        w("## 3. OCR-2 kept rows against candidate context lengths")
        w("")
        w("No context length is set, so none is assumed. Rows are dropped whole (no truncation).")
        w("")
        w("| Cap (tokens) | Kept rows that fit | Tokens in those rows |")
        w("|---:|---:|---:|")
        for cap_len, v in ocr["context"]["rows_fitting_whole_sample"].items():
            w(f"| {int(cap_len):,} | {fmt(v['rows'])} | {fmt(v['tokens'])} |")
        w("")
    w("## 4. Capacity table")
    w("")
    w("`requested = budget x area share x group fraction`. Supply counts only sets with a measured token count on "
      "admissible rows whose licence state is allowed or `TSAI reserves` (none of them is approved for training). "
      "Inside a group tokens are assigned in proportion to supply (equal exposure), a planning convention. Budgets of "
      "10M, 100M and 1B total tokens are **illustrative planning scenarios, not approved training sizes**. "
      "Verdict codes: `F` FEASIBLE (supply fully measured), `F*` FEASIBLE_ON_MEASURED (the measured part alone covers "
      "it; the group still has unmeasured members), `?` UNMEASURED (the records cannot decide), `INF` INFEASIBLE "
      "(reason listed under the table). Each cell reads 1x/2x/4x repeat caps.")
    w("")
    code = {"FEASIBLE": "F", "FEASIBLE_ON_MEASURED": "F*", "UNMEASURED": "?", "NO_REQUEST": "-"}

    def short(v: str) -> str:
        return code.get(v.split(":")[0].split(" (")[0], "INF")

    for scen in sorted({r["scenario"] for r in cap}):
        shares = meta["scenarios"][scen]
        w(f"### Scenario `{scen}`: " + " / ".join(f"{a_} {shares.get(a_, 0):.0%}" for a_ in AREAS))
        w("")
        rows_ = [r for r in cap if r["scenario"] == scen and r["lens"] == LENS_RESERVED]
        by_group = defaultdict(dict)
        for r in rows_:
            by_group[(r["area"], r["group"])][r["budget_tokens"]] = r
        allowed_rows = {(r["area"], r["group"]): r for r in cap if r["scenario"] == scen and r["lens"] == LENS_ALLOWED
                        and r["budget_tokens"] == BUDGETS[0]}
        w("| Group | Eligible sets (TSAI-allowed / allowed or reserved) | Measured supply (tokens) | Requested at 10M / 100M / 1B | "
          "Exposure at 10M / 100M / 1B | Verdict at 10M | at 100M | at 1B |")
        w("|---|---|---:|---|---|---|---|---|")
        for (area, grp), per in by_group.items():
            if per[BUDGETS[0]]["area_share"] <= 0:
                continue
            r0 = per[BUDGETS[0]]
            al = allowed_rows[(area, grp)]
            exp = " / ".join("n/a" if per[b]["minimum_exposure"] is None else f"{per[b]['minimum_exposure']:.3f}x"
                             for b in BUDGETS)
            if exp != "n/a / n/a / n/a" and not r0["supply_complete"]:
                exp += " (upper bound)"
            w(f"| {area}: {grp} | {len(al['eligible_sets'])} / {len(r0['eligible_sets'])} | "
              f"{fmt(r0['supply_tokens_measured'])} | " + " / ".join(fmt(per[b]["requested_tokens"]) for b in BUDGETS)
              + f" | {exp} | " + " | ".join("/".join(short(per[b]["status"][f"{c_}x"]) for c_ in REPEAT_CAPS)
                                           for b in BUDGETS) + " |")
        w("")
        bad = [(r["area"], r["group"], r["status"]["1x"]) for r in rows_ if r["budget_tokens"] == BUDGETS[0]
               and r["status"]["1x"].startswith("INFEASIBLE")]
        for area, grp, why in bad:
            w(f"- **{area}: {grp}** is {why}.")
        if bad:
            w("")
        problems = next(t for t in tot if t["scenario"] == scen)["share_problems"]
        w("Share self-consistency: " + ("sums to 1 and every share has a composition group." if not problems
                                        else "; ".join(problems)))
        w("")
        w("Total budget a group alone could support, at repeat caps 1x / 2x / 4x (lower bound: unmeasured members only "
          "add supply):")
        w("")
        w("| Group | 1x | 2x | 4x |")
        w("|---|---:|---:|---:|")
        none_measured = []
        for (area, grp), per in by_group.items():
            r0 = per[BUDGETS[0]]
            if r0["area_share"] <= 0:
                continue
            sup = r0["supply_tokens_measured"]
            if not sup:
                none_measured.append(f"{area}: {grp}")
                continue
            den = r0["area_share"] * r0["fraction_of_area"]
            w(f"| {area}: {grp} | " + " | ".join(f"{int(c_ * sup / den):,}" for c_ in REPEAT_CAPS) + " |")
        w("")
        w(f"No measured supply, so no bound: {len(none_measured)} groups (" + "; ".join(none_measured) + ").")
        w("")
        w("**Maximum feasible total for the whole mix:** not stated. It is the smallest of the group totals above, "
          f"and {len(none_measured)} of {sum(1 for per in by_group.values() if per[BUDGETS[0]]['area_share'] > 0)} groups "
          "have no measured supply, so the records cannot give it; it is not filled by estimation.")
        w("")
    w("### Indic language cells (rows only; tokens not measured)")
    w("")
    w("From `sft_mix_proposal.md` section 7 (Hugging Face datasets-server statistics, not a run of ours): the "
      "`sft-indic-aya-dataset` rows by language. Kannada and Odia are the deficient cells; Odia has none.")
    w("")
    w("| Language | Rows | Share of set | Flag |")
    w("|---|---:|---:|---|")
    for lg in langs:
        w(f"| {lg['language']} | {fmt(lg['rows'])} | {lg['share_of_set']:.1%} | {lg['flag'] or ''} |")
    w("")
    w("## 5. What the records contradict or cannot decide")
    w("")
    if contr:
        w("| Kind | Subject | Detail |")
        w("|---|---|---|")
        for c_ in contr:
            w(f"| {c_['kind']} | `{c_['subject']}` | {c_['detail']} |")
    else:
        w("No contradiction found among the inputs.")
    w("")
    w("## 6. Decisions for Sai and TSAI")
    w("")
    w("Each item is something the records cannot settle. The final shares and the budget unit are theirs.")
    w("")
    measured = [x for x in sets if x["tokens"]["status"] == "measured"]
    scanned = [x for x in sets if x["rows"]["stages"] and x["coverage_class"] in ("full", "partial")]
    fit = ocr["context"].get("rows_fitting_whole_sample", {})
    d: list[str] = []
    d.append("**Budget unit.** The proposal says \"token/trajectory\". This ledger uses total processed non-padding "
             "tokens (`tokens`) for the budget and reports supervised targets beside it. For OCR-2 the targets are "
             f"{ocr['tokens']['shifted_supervised_targets'] / ocr['tokens']['sequence_tokens']:.1%} of tokens; for an "
             "agent set with long tool results the share is lower (the 1,000-row test in `convert_report.md` "
             "shows 28.3% for SWE-rebench, 93.2% for codeforces-cots, prefix samples only). Choose the unit; a "
             "supervised-token budget and a total-token budget give different supply.")
    d.append("**Safety share.** The active table in `sft_mix_proposal.md` section 2 says 7 General / 3 Safety, while "
             "sections 6 and 8 say to use 0 Safety / 10 General until TSAI names an allowed safety set with chat rows. "
             "All five safety sets are excluded, or text-only with no assistant turn (Aegis). Scenario "
             "`proposal_table` therefore requests 3% from sources that cannot supply it (INFEASIBLE above). Pick "
             "`plan_d3` (0 / 10) or name an allowed set. The table still names four excluded safety sets (section 5).")
    d.append("**Model context length.** Not set, and it is a blocker named by the OCR-2 pack check "
             "(`context_limit_not_set`). " + (f"OCR-2 kept rows that fit whole: {fmt(fit['16384']['rows'])} of "
             f"{fmt(ocr['rows']['stages']['kept'])} at 16,384 tokens and all at 32,768 (section 3)." if fit else ""))
    d.append("**Token counts for the other scanned sets.** "
             f"{len(scanned) - len(measured)} scanned sets have row counts but no token record. Their supply, the "
             "shifted-target share, length percentiles and effort mix cannot be filled by estimation. The next step is "
             "one tokenizing pass over each set's clean file (`convert.py --tokenizer`, then `--token-records`). "
             "The clean files are local outputs of the decontamination runs and are not on the branch. The frozen "
             "tokenizer arrives on 14 Nov, so a pass now would need a rerun.")
    c3 = [r for r in records if r["type"] == "c3_token_record"]
    if c3:
        d.append("**C3 token records (WP14).** "
                 f"{c['sets_with_c3_records']} sets have C3 token records at the scope each states (section 8). Those "
                 "records are first-rows samples or full conversions that were not decontaminated; none is a kept-row "
                 "record, so the supply columns above still hold the scanned counts and the measured-token count of "
                 "section 1 is unchanged.")
    blockers = ocr["pack"].get("blockers")
    d.append("**OCR-2 admission.** 0 rows are admitted. " + (
        "Blockers in the pack report (union over the 70 shards): " + ", ".join(f"`{b}`" for b in blockers) + ". "
        if blockers else "The pack blockers are not recorded (run with --ocr2-runs). ") +
        f"{fmt(ocr['rows']['stages']['held'])} `open-r1/codeforces` train rows are held until the producer revision is "
        "established.")
    d.append("**Overlap between sets.** Family hashes exist only for OCR-2, so duplication of problems between "
             "`sft-code-opencodereasoning`, `sft-code-opencodereasoning-2` and `sft-code-codeforces-cots` is not "
             "measured. Do not sum their families as if they were disjoint until it is.")
    d.append("**Indic.** Odia has no rows in `aya_dataset` and Kannada 334; the Indic area has no token record at all. "
             "The proposal asks for a per-subset cap on `aya_collection` (\"a few thousand rows\") without a number, "
             "so no capped scenario is computed. Section 3 of the proposal gives a 10 / 5 split between "
             "`aya_dataset` and `aya_collection`; section 7 proposes a different composition without shares. Say which.")
    d.append("**Partial and held coverage.** `sft-math-nemotron-proofs-v3-sft` converted 293,648 of 414,890 source "
             f"rows. {len([x for x in sets if x['coverage_class'] == 'held'])} sets in the licence table are not excluded "
             "yet have no converter or decontam record (the held list in section 2). Run them or drop them.")
    d.append("**What to call what.** " f"{c['scanned_entries_in_decontam_report']} scanned entries, "
             f"{c['approved_complete_training_packs']} approved complete training packs. Diagnostic scan, eligible "
             "retained subset, approved pack and trained result are four milestones; only the first exists.")
    for i, item in enumerate(d, 1):
        w(f"{i}. {item}")
    w("")
    w("## 7. Not covered here")
    w("")
    w("This ledger does not change `sft_mix_proposal.md`, `decontam_report.md` or the licence table. It also does "
      "not audit CommitPackFT row or repository licences, add the MATH-train licence row to the RL handoff, or "
      "recount section subtotals in those documents; those are separate edits.")
    w("")
    if c3:
        w("## 8. C3 token records (WP14), by scope")
        w("")
        w("Tokenizer: C3 (`tokenizer_sha256` in each record), rendered with `chat-format/render.py`, masks per "
          "`convert_report.md`. Each row states its own scope. `first N` rows are the first N selected rows of the set in "
          "source order, not a sample of the whole set and not the decontamination-kept rows. `full` rows are every row the "
          "adapter produced from the pinned source; none of them has been through the decontamination run, so they are "
          "converted, not decontaminated, and none is a pack. A licence state of `tsai_reserves` is not an admission. "
          "`targets` = loss-masked assistant tokens after the one-token shift; `over` = rows longer than `max_len` tokens. "
          "OCR-2 is not in this section. Its rows, lengths and counts elsewhere in this document are computed from the legacy "
          "`ocr2_full_run.json` inputs (tokenizer v0.1, no context limit, 0 admitted) and are not the current C3 pack "
          "state, which is recorded in its own pack manifest.")
        w("")
        w("| Set | Licence state | Scope | Rows in | Rows out | Tokens | Targets | Target share | p50 / p95 / max | Over max_len | Checks |")
        w("|---|---|---|---:|---:|---:|---:|---:|---|---:|---|")
        for r in c3:
            ln = r.get("length") or {}
            share = r["shifted_supervised_targets"] / r["sequence_tokens"] if r["sequence_tokens"] else None
            w(f"| `{r['set_id']}` | {r['licence_decision']} | {r['scope']} | {fmt(r.get('rows_in'))} | {fmt(r['rows'])} | "
              f"{fmt(r['sequence_tokens'])} | {fmt(r['shifted_supervised_targets'])} | "
              f"{'n/a' if share is None else format(share, '.1%')} | "
              f"{fmt(ln.get('p50'))} / {fmt(ln.get('p95'))} / {fmt(ln.get('max'))} | {fmt(r.get('rows_over_max_len'))} | "
              f"{'pass' if r.get('checks_ok') else 'not recorded' if r.get('checks_ok') is None else 'FAIL'} |")
        w("")
    w("")
    return ("\n".join(L).rstrip() if c3 else "\n".join(L)) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=["build"])
    here = Path(__file__).resolve().parent
    ap.add_argument("--team-dir", type=Path, default=here.parent, help="teams/10-post-training")
    ap.add_argument("--ocr2-runs", type=Path, help="folder holding report_0-69.json and its results/ shard records")
    ap.add_argument("--token-records", type=Path, help="JSONL of measured token records for other sets")
    ap.add_argument("--c3-records", type=Path, help="JSONL of C3 token records with an explicit scope (see read_c3_records)")
    ap.add_argument("--out-jsonl", type=Path, default=here / "results/eligibility_ledger.jsonl")
    ap.add_argument("--out-md", type=Path, default=here.parent / "docs/eligibility_ledger.md")
    ap.add_argument("--verify", action="store_true", help="do not write; fail if the files differ from a fresh build")
    a = ap.parse_args(argv)
    records = collect(a.team_dir, a.ocr2_runs, a.token_records, a.c3_records)
    jsonl, md = dump_jsonl(records), render_markdown(records)
    if a.verify:
        ok = a.out_jsonl.read_text(encoding="utf-8") == jsonl and a.out_md.read_text(encoding="utf-8") == md
        print("verify:", "identical" if ok else "DIFFERENT")
        return 0 if ok else 1
    a.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    a.out_md.parent.mkdir(parents=True, exist_ok=True)
    a.out_jsonl.write_text(jsonl, encoding="utf-8")
    a.out_md.write_text(md, encoding="utf-8")
    print(f"wrote {a.out_jsonl} ({len(records)} lines) and {a.out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
