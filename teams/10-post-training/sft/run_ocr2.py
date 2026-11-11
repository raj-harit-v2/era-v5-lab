"""Bounded, resumable shard runner for the OpenCodeReasoning-2 join (G10).

    python run_ocr2.py --manifest source_manifest.json --policy ocr2_policy.json \
        --shards 0:70 --workers 1 --out-dir RUN [--resume] [--mode diagnostic|admission]

Per shard it runs five stages and reuses the existing tools unchanged:

    joined      prepare_ocr2.py   question join from the pinned original splits, sidecar, exclusions
    rendered    convert.py        --set sft-code-opencodereasoning-2 --input joined.jsonl --index-base B --tokenizer T
    screened    decontam_run.py   Team 9 full set + canary scan, clean file, second pass over the clean file
    rechecked   (this file)       the second pass has zero hits; every retained id maps to its original row
    pack        pack_admission.py report in a diagnostic run; the admitted pack in an admission run

and one run-wide stage, `indexed` (source_index.py). Paths, hashes and ids come from the source manifest
(`conversion.tokenizer`, `screening.tools_dir`, `screening.set_sha256`); an unset one stops the run. No
benchmark or tag filter, no --no-recheck, no --drop-clean and no empty expected hash is ever passed.

A stage writes into `<stage>.tmp/`, syncs it, renames it, and only then publishes
`state/<stage>.complete.json` (also by rename). An exit code is not a completion marker. On --resume a
stage is skipped only if its marker matches the code/policy/tokenizer/fingerprint tuple and every recorded
input and output still has its sha256. Anything else is moved to `quarantine/` and that one stage runs
again; a stage whose inputs then differ runs again too. The deterministic hash of a stage leaves out run
times (and the scan record's `run_at`), so two runs and any --workers count can be compared exactly.

A shard with no pinned local input is listed as `not_available_locally`: it is accounted for, not
scanned. A diagnostic run folder never resumes into an admission run. A canary stops the shard and
leaves a private incident record (ids, offsets, canary label; no text). Exit code: 0 every requested
shard with a local input is complete and reconciled, 1 a shard failed or stopped, 2 bad input, 3 refused
by policy (or, in admission mode, a pack was refused).

Everything under --out-dir is private: statements, completions and document ids. Keep it out of Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import convert as g10  # noqa: E402
import decontam_run  # noqa: E402
import pack_admission  # noqa: E402
import prepare_ocr2 as join  # noqa: E402
import source_index as si  # noqa: E402

SET_ID = join.SET_ID
STAGE_SCHEMA = "g10-ocr2-stage/1"
STAGES = ("joined", "rendered", "screened", "rechecked", "pack")
STAGE_DIR = {"joined": "join", "rendered": "rendered", "screened": "screen", "rechecked": "recheck", "pack": "pack"}
VOLATILE = {"screened": (f"{SET_ID}.record.json",)}  # the record carries run_at
CODE_FILES = ("sft/run_ocr2.py", "sft/prepare_ocr2.py", "sft/source_index.py", "sft/pack_admission.py",
              "sft/convert.py", "sft/decontam_run.py", "chat-format/render.py")
FAULT_POINTS = ("before_publish", "before_marker")


class RunError(Exception):
    """Bad input, an unset path, or a tool that could not run (exit code 2)."""


class CanaryStop(Exception):
    """A canary was found: the shard stops, an incident record is written."""


class Fault(RuntimeError):
    """Test only: stands in for a process that is killed at a chosen point."""


# --- files -------------------------------------------------------------------------------------

def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_tree(folder: Path) -> None:
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            with open(path, "rb") as stream:
                os.fsync(stream.fileno())
    _fsync_dir(folder)


def _write_json_atomic(path: Path, value) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=1, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def _tree_hashes(folder: Path) -> dict:
    return {p.relative_to(folder).as_posix(): si.sha256_file(p) for p in sorted(folder.rglob("*")) if p.is_file()}


def _tree_bytes(folder: Path) -> int:
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def _peak_rss_mb() -> dict:
    scale = 1 if sys.platform == "darwin" else 1024  # ru_maxrss: bytes on macOS, KiB on Linux
    return {who: round(resource.getrusage(flag).ru_maxrss * scale / 1e6, 1)
            for who, flag in (("self", resource.RUSAGE_SELF), ("children_so_far", resource.RUSAGE_CHILDREN))}


def _quarantine(root: Path, victims: list[Path]) -> list[str]:
    """Move partial or stale files aside. Nothing is deleted and nothing is reused."""
    moved = []
    for victim in victims:
        if victim.exists():
            pen = root / "quarantine"
            pen.mkdir(exist_ok=True)
            n = 0
            while (pen / f"{victim.name}.{n}").exists():
                n += 1
            os.rename(victim, pen / f"{victim.name}.{n}")
            moved.append(f"{victim.name}.{n}")
    return moved


# --- configuration -----------------------------------------------------------------------------

def load_config(manifest_path, policy_path, out_dir, mode: str) -> dict:
    """Resolve every path and hash of a run from the manifest and the policy. Unset means stop."""
    manifest_path, policy_path, out_dir = Path(manifest_path).resolve(), Path(policy_path).resolve(), Path(out_dir).resolve()
    manifest, manifest_sha, base = si.load_manifest(manifest_path)
    policy, policy_sha = join.load_policy(policy_path)
    licence = g10.licence_row(SET_ID)
    join.gate(policy, mode, licence["decision"])
    fixture = manifest.get("test_fixture") is True

    def at(value):
        return Path(value) if Path(value).is_absolute() else base / value

    tokenizer = (manifest.get("conversion") or {}).get("tokenizer") or {}
    if not isinstance(tokenizer.get("path"), str) or not isinstance(tokenizer.get("sha256"), str):
        raise RunError("conversion.tokenizer {path, sha256} is unset in the source manifest")
    tokenizer_path = at(tokenizer["path"])
    if not tokenizer_path.is_file() or si.sha256_file(tokenizer_path) != tokenizer["sha256"]:
        raise RunError(f"{tokenizer_path} is missing or is not the pinned tokenizer {tokenizer['sha256'][:12]}...")
    limit = (manifest.get("conversion") or {}).get("max_sequence_tokens")

    screening = manifest.get("screening") or {}
    if not isinstance(screening.get("tools_dir"), str):
        raise RunError("screening.tools_dir is unset in the source manifest")
    tools = at(screening["tools_dir"])
    if not all((tools / name).is_file() for name in ("decontam_check.py", "canary_scan.py")):
        raise RunError(f"{tools} is not Team 9's decontam folder")
    expect = screening.get("set_sha256")
    if not isinstance(expect, str) or len(expect) != 64:
        raise RunError("screening.set_sha256 is unset in the source manifest: an empty expected hash is never used")
    fingerprints = screening.get("fingerprints_test_only")
    if fingerprints is not None and not fixture:
        raise RunError("screening.fingerprints_test_only is for test fixtures; a real run uses the set next to the tools")
    if not fixture and expect not in (policy.get("pack") or {}).get("approved_fingerprint_set_sha256", []):
        raise RunError(f"screening.set_sha256 {expect[:12]}... is not an approved fingerprint set in the policy")
    tool_hashes = decontam_run.tool_info(tools)["files"]
    declared = screening.get("tool_sha256")
    if declared is not None and declared != tool_hashes:
        raise RunError("Team 9's tool files are not the ones pinned in screening.tool_sha256")

    tuple_ = {
        "mode": mode, "test_fixture": fixture, "policy_sha256": policy_sha, "source_manifest_sha256": manifest_sha,
        "tokenizer_sha256": tokenizer["sha256"], "max_sequence_tokens": limit, "fingerprint_set_sha256": expect,
        "tools_sha256": tool_hashes, "licence_row_sha256": si.sha256_json(licence),
        "code_sha256": {name: si.sha256_file(g10.TEAM / name) for name in CODE_FILES},
    }
    config_sha = si.sha256_json(tuple_)
    return {
        "mode": mode, "test_fixture": fixture, "tuple": tuple_, "config_sha256": config_sha,
        "run_id": f"{mode}-{config_sha[:12]}", "manifest_path": str(manifest_path), "policy_path": str(policy_path),
        "out_dir": str(out_dir), "index_path": str(out_dir / "index" / "source_index.sqlite"),
        "tokenizer_path": str(tokenizer_path), "tools": str(tools), "expect_sha": expect,
        "fingerprints": str(at(fingerprints)) if fingerprints else None, "max_sequence_tokens": limit,
        "manifest_sha256": manifest_sha, "fault": None,
    }


# --- the run-wide index ------------------------------------------------------------------------

def ensure_index(cfg: dict) -> dict:
    out = Path(cfg["out_dir"])
    index, marker_path = Path(cfg["index_path"]), out / "state" / "indexed.complete.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if (marker["manifest_sha256"] == cfg["manifest_sha256"] and index.is_file()
                and si.sha256_file(index) == marker["index_sha256"]):
            return {**marker, "resumed": True}
    except (OSError, ValueError, KeyError):
        pass
    moved = _quarantine(out, [index, index.with_name(index.name + ".tmp"), marker_path])
    started = time.monotonic()
    meta = si.build(cfg["manifest_path"], index)
    marker = {"schema": STAGE_SCHEMA, "stage": "indexed", "state": "indexed", "manifest_sha256": cfg["manifest_sha256"],
              "content_sha256": meta["content_sha256"], "index_sha256": si.sha256_file(index), "sources": meta["sources"],
              "exec": {"seconds": round(time.monotonic() - started, 3), "index_bytes": index.stat().st_size, "quarantined": moved}}
    _write_json_atomic(marker_path, marker)
    return marker


# --- one stage ---------------------------------------------------------------------------------

def _tool(cmd: list, what: str, ok=(0,)) -> subprocess.CompletedProcess:
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", cwd=str(HERE))
    if proc.returncode not in ok:
        tail = (proc.stderr.strip().splitlines() or proc.stdout.strip().splitlines() or [""])[-1]
        raise RunError(f"{what} exited {proc.returncode}: {tail}")
    return proc


def _sidecar(path: Path) -> dict:
    with open(path, encoding="utf-8") as stream:
        return {entry["rendered_id"]: entry for entry in map(json.loads, stream)}


def _ids(path: Path, sidecar: dict, what: str) -> list[str]:
    """The ids of a rendered or retained file, each checked against the sidecar's original row."""
    ids = []
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            entry = sidecar.get(row["id"])
            if entry is None or row.get("source_id") != entry["ocr_id"]:
                raise RunError(f"{what}: {row['id']} does not map to its original OCR row through the sidecar")
            ids.append(row["id"])
    if len(set(ids)) != len(ids):
        raise RunError(f"{what}: an id appears twice")
    return ids


def _ids_sha(ids) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def _work_joined(cfg, shard_id, shard_dir, tmp, entry_path, done):
    result = join.prepare(cfg["manifest_path"], cfg["policy_path"], entry_path, shard_id, tmp, cfg["mode"], cfg["index_path"])
    return {"raw_rows": result["raw_rows"], **result["groups"], "outcomes": result["outcomes"], "by_source": result["by_source"],
            "families": result["families"], "tags": result["tags"], "index_base": result["index_base"],
            "input_coverage": result["input"]["coverage"]}


def _work_rendered(cfg, shard_id, shard_dir, tmp, entry_path, done):
    joined = shard_dir / "join" / "joined.jsonl"
    out = tmp / "rendered.jsonl"
    _tool([sys.executable, HERE / "convert.py", "--set", SET_ID, "--input", joined, "--index-base",
           done["joined"]["counts"]["index_base"], "--tokenizer", cfg["tokenizer_path"], "--out", out], "convert.py")
    manifest = json.loads(Path(f"{out}.manifest.json").read_text(encoding="utf-8"))
    eligible = done["joined"]["counts"]["eligible_joined"]
    ids = _ids(out, _sidecar(shard_dir / "join" / "joined.sidecar.jsonl"), "rendered file")
    skipped = sum(manifest["skipped"].values())
    if manifest["rows_in"] != eligible or manifest["rows"] != len(ids) or len(ids) + skipped != eligible:
        raise RunError("convert.py counts do not reconcile with the join")
    return {"joined_in": eligible, "rendered": len(ids), "converter_rejected": skipped, "skipped": manifest["skipped"],
            "effort": manifest["effort"], "tokens": manifest.get("tokens"), "trained_tokens": manifest.get("trained_tokens"),
            "rendered_ids_sha256": _ids_sha(ids)}


def _work_screened(cfg, shard_id, shard_dir, tmp, entry_path, done):
    rendered = shard_dir / "rendered" / "rendered.jsonl"
    rows = done["rendered"]["counts"]["rendered"]
    if rows == 0:  # nothing to scan is not a clean scan: no scan credit, and it is said so
        scan = {"scan": "not_run", "reason": "no rendered rows", "scan_credit": False, "rows_in": 0,
                "rows_flagged": 0, "rows_canary": 0, "rows_removed": 0, "rows_kept": 0}
        _write_json_atomic(tmp / "scan.json", scan)
        return scan
    cmd = [sys.executable, HERE / "decontam_run.py", "--set", SET_ID, "--input", rendered, "--out-dir", tmp,
           "--tools", cfg["tools"], "--expect-sha", cfg["expect_sha"]]
    if cfg["fingerprints"]:
        cmd += ["--fingerprints", cfg["fingerprints"]]
    proc = _tool(cmd, "decontam_run.py", ok=(0, 1))
    record = json.loads((tmp / f"{SET_ID}.record.json").read_text(encoding="utf-8"))
    if record["rows_canary"]:
        incident = Path(cfg["out_dir"]) / "incidents" / f"shard-{shard_id:05d}-canary.json"
        incident.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(incident, {"shard_id": shard_id, "set": SET_ID, "set_sha256": record["set_sha256"],
                                      "hits": record["canary"]["hits"], "note": "ids, offsets and canary labels only"})
        raise CanaryStop(str(incident))
    bad = [name for name, ok in record["checks"].items() if not ok]
    if proc.returncode != 0 or not record["ok"] or bad:
        raise RunError("decontam_run.py reconciliation failed: " + ", ".join(bad or ["record not ok"]))
    if (record["scope"] != "full set" or record["set_sha256"] != cfg["expect_sha"] or record["rows_in"] != rows
            or record["rows_in"] != record["rows_kept"] + record["rows_removed"]
            or record["inputs"][0]["sha256"] != si.sha256_file(rendered) or record.get("clean_files_deleted")):
        raise RunError("the scan record is not a full-set scan of this exact render")
    scan = {"scan": "full_set", "scan_credit": True, "fingerprints": record["fingerprints"], "set_sha256": record["set_sha256"],
            "rows_in": record["rows_in"], "rows_flagged": record["rows_flagged"], "rows_canary": record["rows_canary"],
            "rows_removed": record["rows_removed"], "rows_kept": record["rows_kept"],
            "by_benchmark": {k: v for k, v in sorted(record["by_benchmark"].items()) if v},
            "flagged_ids_sha256": _ids_sha(sorted(record["flagged"])), "clean_sha256": record["clean"][0]["sha256"]}
    _write_json_atomic(tmp / "scan.json", scan)
    return scan


def _work_rechecked(cfg, shard_id, shard_dir, tmp, entry_path, done):
    scan = done["screened"]["counts"]
    if not scan["scan_credit"]:
        result = {"recheck": "not_run", "reason": "no scan", "retained": 0, "removed": 0}
        _write_json_atomic(tmp / "recheck.json", result)
        return result
    screen = shard_dir / "screen"
    record = json.loads((screen / f"{SET_ID}.record.json").read_text(encoding="utf-8"))
    clean = screen / f"{SET_ID}.clean.jsonl"
    second = record.get("recheck_on_clean") or {}
    if second.get("flagged") != 0 or second.get("docs") != record["rows_kept"] or second.get("set_sha256") != cfg["expect_sha"]:
        raise RunError("the second pass over the retained file is missing or has hits")
    if si.sha256_file(clean) != record["clean"][0]["sha256"]:
        raise RunError("the retained file is not the one the scan record names")
    sidecar = _sidecar(shard_dir / "join" / "joined.sidecar.jsonl")
    rendered = _ids(shard_dir / "rendered" / "rendered.jsonl", sidecar, "rendered file")
    retained = _ids(clean, sidecar, "retained file")
    removed = set(rendered) - set(retained)
    if (not set(retained) <= set(rendered) or len(retained) != record["rows_kept"] or len(removed) != record["rows_removed"]
            or removed != set(record["flagged"])):
        raise RunError("retained and removed rows do not reconcile with the render and the scan record")
    with open(tmp / "retained.sidecar.jsonl", "w", encoding="utf-8") as stream:
        for rid in retained:  # the sidecar lines of the retained rows, in retained order
            stream.write(json.dumps(sidecar[rid], ensure_ascii=True) + "\n")
    result = {"recheck": "second_full_pass_zero_hits", "docs": second["docs"], "flagged": 0, "retained": len(retained),
              "removed": len(removed), "retained_ids_sha256": _ids_sha(retained)}
    _write_json_atomic(tmp / "recheck.json", result)
    return result


def _work_pack(cfg, shard_id, shard_dir, tmp, entry_path, done):
    scanned = done["screened"]["counts"]["scan_credit"]
    pack = {"schema": pack_admission.PACK_SCHEMA, "set": SET_ID, "test_fixture": cfg["test_fixture"],
            "policy": cfg["policy_path"], "source_manifest": cfg["manifest_path"],
            "join_manifest": "../join/join_manifest.json", "sidecar": "../join/joined.sidecar.jsonl",
            "rendered": "../rendered/rendered.jsonl",
            "retained": f"../screen/{SET_ID}.clean.jsonl" if scanned else None,
            "decontam_record": f"../screen/{SET_ID}.record.json" if scanned else None,
            "tokenizer": cfg["tokenizer_path"], "max_sequence_tokens": cfg["max_sequence_tokens"]}
    _write_json_atomic(tmp / "pack_manifest.json", pack)
    training = cfg["mode"] == "admission"
    report = pack_admission.evaluate(tmp / "pack_manifest.json", "training" if training else "report",
                                     tmp / "pack.jsonl" if training else None)
    _write_json_atomic(tmp / "pack_report.json", report)
    return {"attempted": report["attempted"], "row_checks_passed": report["row_checks_passed"],
            "pack_rejected": report["pack_rejected"], "admitted": report["admitted"], "emitted": report["emitted"],
            "training_admissible": report["training_admissible"], "blockers": report["blockers"],
            "row_outcomes": report["row_outcomes"], "passed_rows": report["passed_rows"]}


WORK = {"joined": _work_joined, "rendered": _work_rendered, "screened": _work_screened,
        "rechecked": _work_rechecked, "pack": _work_pack}


def _inputs(cfg: dict, shard_dir: Path, stage: str, entry_path: Path) -> dict:
    j, r, s = shard_dir / "join", shard_dir / "rendered", shard_dir / "screen"
    clean, record = s / f"{SET_ID}.clean.jsonl", s / f"{SET_ID}.record.json"
    return {
        "joined": {"ocr_input": entry_path, "policy": Path(cfg["policy_path"]), "source_manifest": Path(cfg["manifest_path"]),
                   "source_index": Path(cfg["index_path"])},
        "rendered": {"joined": j / "joined.jsonl", "sidecar": j / "joined.sidecar.jsonl", "tokenizer": Path(cfg["tokenizer_path"])},
        "screened": {"rendered": r / "rendered.jsonl"},
        "rechecked": {"rendered": r / "rendered.jsonl", "sidecar": j / "joined.sidecar.jsonl", "scan": s / "scan.json",
                      "clean": clean, "record": record},
        "pack": {"join_manifest": j / "join_manifest.json", "sidecar": j / "joined.sidecar.jsonl", "rendered": r / "rendered.jsonl",
                 "scan": s / "scan.json", "clean": clean, "record": record, "recheck": shard_dir / "recheck" / "recheck.json",
                 "policy": Path(cfg["policy_path"]), "tokenizer": Path(cfg["tokenizer_path"])},
    }[stage]


def _hash_inputs(inputs: dict) -> dict:
    return {label: (si.sha256_file(path) if path.is_file() else None) for label, path in sorted(inputs.items())}


def _state_label(cfg: dict, stage: str, counts: dict) -> str:
    if stage != "pack":
        return stage
    if cfg["mode"] != "admission":
        return "pack_report"
    return "pack_validated" if counts["training_admissible"] else "pack_refused"


def _stage(cfg: dict, shard_id: int, shard_dir: Path, stage: str, entry_path: Path, done: dict) -> dict:
    marker_path = shard_dir / "state" / f"{stage}.complete.json"
    final, tmp = shard_dir / STAGE_DIR[stage], shard_dir / (STAGE_DIR[stage] + ".tmp")
    input_hashes = _hash_inputs(_inputs(cfg, shard_dir, stage, entry_path))
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if (marker["stage"] == stage and marker["shard_id"] == shard_id and marker["mode"] == cfg["mode"]
                and marker["config_sha256"] == cfg["config_sha256"] and marker["inputs"] == input_hashes
                and final.is_dir() and _tree_hashes(final) == marker["outputs"]):
            return {**marker, "resumed": True}
    except (OSError, ValueError, KeyError):
        pass
    moved = _quarantine(shard_dir, [final, tmp, marker_path, marker_path.with_name(marker_path.name + ".tmp")])
    tmp.mkdir()
    started = time.monotonic()
    counts = WORK[stage](cfg, shard_id, shard_dir, tmp, entry_path, done)
    _fsync_tree(tmp)
    if cfg["fault"] == [stage, "before_publish"]:
        raise Fault(f"{stage}: stopped before the stage folder was published")
    os.rename(tmp, final)
    _fsync_dir(shard_dir)
    if cfg["fault"] == [stage, "before_marker"]:
        raise Fault(f"{stage}: stopped before the completion marker was published")
    outputs = _tree_hashes(final)
    stable = {name: sha for name, sha in outputs.items() if name not in VOLATILE.get(stage, ())}
    marker = {
        "schema": STAGE_SCHEMA, "stage": stage, "state": _state_label(cfg, stage, counts), "shard_id": shard_id,
        "run_id": cfg["run_id"], "mode": cfg["mode"], "test_fixture": cfg["test_fixture"], "config_sha256": cfg["config_sha256"],
        "inputs": input_hashes, "outputs": outputs, "counts": counts,
        "deterministic_sha256": si.sha256_json({"stage": stage, "shard_id": shard_id, "mode": cfg["mode"],
                                                "config_sha256": cfg["config_sha256"], "outputs": stable, "counts": counts}),
        "exec": {"seconds": round(time.monotonic() - started, 3), "output_bytes": _tree_bytes(final), "peak_rss_mb": _peak_rss_mb(),
                 "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "quarantined": moved},
    }
    _write_json_atomic(marker_path, marker)
    return {**marker, "resumed": False}


def reconcile(counts: dict) -> list[str]:
    """The four conservation equations of one shard. Returns the ones that do not hold."""
    j, r, s, p = counts["joined"], counts["rendered"], counts["screened"], counts["pack"]
    checks = {
        "raw = policy excluded + malformed or unresolved + eligible joined":
            j["raw_rows"] == j["policy_excluded"] + j["malformed_or_unresolved"] + j["eligible_joined"],
        "eligible joined = converter rejected + rendered": j["eligible_joined"] == r["converter_rejected"] + r["rendered"],
        "rendered = removed + clean": r["rendered"] == s["rows_removed"] + s["rows_kept"] and s["rows_in"] == r["rendered"],
        "clean = pack rejected + pack row checks passed": s["rows_kept"] == p["pack_rejected"] + p["row_checks_passed"] == p["attempted"],
    }
    return [name for name, ok in checks.items() if not ok]


def run_shard(cfg: dict, shard_id: int) -> dict:
    manifest, _, base = si.load_manifest(cfg["manifest_path"])
    shard = manifest["ocr2"]["shards"][shard_id]
    summary = {"shard_id": shard_id, "path": shard["path"]}
    entry = next((e for e in manifest["ocr2"].get("inputs", []) if e["shard_id"] == shard_id), None)
    if entry is None:
        return {**summary, "state": "not_available_locally", "note": "no pinned local input in the source manifest: not scanned"}
    entry_path = Path(entry["path"]) if Path(entry["path"]).is_absolute() else base / entry["path"]
    shard_dir = Path(cfg["out_dir"]) / "shards" / f"shard-{shard_id:05d}"
    (shard_dir / "state").mkdir(parents=True, exist_ok=True)
    summary.update(input_coverage=entry["coverage"], input_rows=entry["rows"])
    done: dict = {}
    try:
        for stage in STAGES:
            done[stage] = _stage(cfg, shard_id, shard_dir, stage, entry_path, done)
    except CanaryStop as stop:
        return {**summary, "state": "stopped_canary", "incident": str(stop), "stages_complete": list(done)}
    except (RunError, si.SourceIndexError, pack_admission.PackError, OSError, ValueError) as exc:
        return {**summary, "state": "failed", "error": f"{type(exc).__name__}: {exc}", "stages_complete": list(done)}
    counts = {stage: done[stage]["counts"] for stage in STAGES}
    broken = reconcile(counts)
    stage_hashes = {stage: done[stage]["deterministic_sha256"] for stage in STAGES}
    return {**summary, "state": "failed" if broken else "complete", "not_reconciled": broken,
            "final_state": done["pack"]["state"], "counts": counts, "stage_sha256": stage_hashes,
            "deterministic_sha256": si.sha256_json(stage_hashes),
            "exec": {stage: {"resumed": done[stage]["resumed"], **done[stage]["exec"]} for stage in STAGES}}


# --- the run -----------------------------------------------------------------------------------

def parse_shards(spec: str, total: int) -> list[int]:
    try:
        first, _, last = spec.partition(":")
        ids = list(range(int(first), int(last))) if last else [int(first)]
    except ValueError:
        raise RunError(f"--shards {spec!r}: use A:B (B not included) or one id") from None
    if not ids or ids[0] < 0 or ids[-1] >= total:
        raise RunError(f"--shards {spec!r} is outside the {total} shards of the source manifest")
    return ids


def run(manifest_path, policy_path, shards: str, workers: int, out_dir, resume: bool = False, mode: str = "diagnostic",
        fault=None) -> dict:
    out = Path(out_dir).resolve()
    cfg = load_config(manifest_path, policy_path, out, mode)
    if fault is not None:
        if not cfg["test_fixture"] or list(fault)[1] not in FAULT_POINTS:
            raise RunError("fault injection is for test fixtures only")
        cfg["fault"] = list(fault)
    manifest, _, _ = si.load_manifest(manifest_path)
    ids = parse_shards(shards, len(manifest["ocr2"]["shards"]))
    out.mkdir(parents=True, exist_ok=True)
    run_file = out / "run.json"
    history = []
    if run_file.is_file():
        previous = json.loads(run_file.read_text(encoding="utf-8"))
        if previous["mode"] != mode:
            raise RunError(f"{out} holds a {previous['mode']} run: a {previous['mode']} folder never resumes into "
                           f"{mode}; use a new --out-dir")
        if not resume:
            raise RunError(f"{out} already holds run {previous['run_id']}: pass --resume, or use a new --out-dir")
        history = previous.get("history", []) + ([previous["run_id"]] if previous["run_id"] != cfg["run_id"] else [])
    elif any(out.iterdir()):
        raise RunError(f"{out} is not empty and is not a run folder")
    _write_json_atomic(run_file, {"schema": "g10-ocr2-run/1", "run_id": cfg["run_id"], "mode": mode,
                                  "test_fixture": cfg["test_fixture"], "config_sha256": cfg["config_sha256"],
                                  "config": cfg["tuple"], "history": history})
    started = time.monotonic()
    indexed = ensure_index(cfg)
    if workers <= 1:
        results = [run_shard(cfg, shard_id) for shard_id in ids]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(partial(run_shard, cfg), ids))  # map keeps the shard order
    execs = {str(r["shard_id"]): r.pop("exec", None) for r in results}
    states = [r["state"] for r in results]
    complete = [r for r in results if r["state"] == "complete"]
    totals: dict = {}
    for r in complete:
        for stage, keys in (("joined", ("raw_rows", "policy_excluded", "malformed_or_unresolved", "eligible_joined")),
                            ("rendered", ("converter_rejected", "rendered")),
                            ("screened", ("rows_flagged", "rows_canary", "rows_removed", "rows_kept")),
                            ("pack", ("attempted", "row_checks_passed", "pack_rejected", "admitted", "emitted"))):
            for key in keys:
                totals[f"{stage}.{key}"] = totals.get(f"{stage}.{key}", 0) + r["counts"][stage][key]
    expected = len(manifest["ocr2"]["shards"])
    full = sum(1 for r in complete if r["input_coverage"] == "full")
    coverage = {
        "schema": "g10-ocr2-coverage/1", "set": SET_ID, "run_id": cfg["run_id"], "mode": mode, "test_fixture": cfg["test_fixture"],
        "config_sha256": cfg["config_sha256"], "ocr_revision": manifest["ocr2"]["revision"],
        "index_content_sha256": indexed["content_sha256"],
        "accounting": {"expected_shards": expected, "requested": len(ids), "not_requested": expected - len(ids),
                       "complete_full_shard": full, "complete_row_prefix_only": len(complete) - full,
                       "not_available_locally": states.count("not_available_locally"),
                       "stopped_canary": states.count("stopped_canary"), "failed": states.count("failed")},
        "full_dataset": full == expected,
        "totals_over_complete_shards": totals, "shards": results,
    }
    coverage["deterministic_sha256"] = si.sha256_json(coverage)
    _write_json_atomic(out / "coverage.json", coverage)
    _write_json_atomic(out / "coverage.exec.json", {
        "run_id": cfg["run_id"], "wall_seconds": round(time.monotonic() - started, 3), "workers": workers,
        "indexed": {"resumed": indexed.get("resumed", False), **indexed["exec"]}, "shards": execs,
        "peak_rss_mb": _peak_rss_mb(), "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    return coverage


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, required=True, help="source manifest (also names tokenizer, tools and set hash)")
    ap.add_argument("--policy", type=Path, required=True)
    ap.add_argument("--shards", required=True, help="A:B (B not included) or one shard id")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out-dir", type=Path, required=True, help="private run folder; keep it out of Git")
    ap.add_argument("--resume", action="store_true", help="continue a run folder: verified stages are kept, the rest rerun")
    ap.add_argument("--mode", choices=join.MODES, default="diagnostic")
    args = ap.parse_args(argv)
    try:
        coverage = run(args.manifest, args.policy, args.shards, args.workers, args.out_dir, args.resume, args.mode)
    except join.Refusal as exc:
        print(f"run_ocr2: REFUSED: {exc}", file=sys.stderr)
        return 3
    except (RunError, si.SourceIndexError, OSError, ValueError) as exc:
        print(f"run_ocr2: {exc}", file=sys.stderr)
        return 2
    for shard in coverage["shards"]:
        line = f"shard {shard['shard_id']:>2} {shard['state']}"
        if shard["state"] == "complete":
            c = shard["counts"]
            line += (f" [{shard['input_coverage']}] raw {c['joined']['raw_rows']} eligible {c['joined']['eligible_joined']}"
                     f" rendered {c['rendered']['rendered']} flagged {c['screened']['rows_flagged']}"
                     f" canary {c['screened']['rows_canary']} kept {c['screened']['rows_kept']}"
                     f" admitted {c['pack']['admitted']} ({shard['final_state']})")
        elif shard["state"] != "not_available_locally":
            line += f": {shard.get('error') or shard.get('incident')}"
        print(line)
    print(json.dumps({"run_id": coverage["run_id"], "accounting": coverage["accounting"],
                      "full_dataset": coverage["full_dataset"], "deterministic_sha256": coverage["deterministic_sha256"]}))
    acc = coverage["accounting"]
    if acc["failed"] or acc["stopped_canary"]:
        return 1
    if mode_refused(coverage):
        return 3
    return 0


def mode_refused(coverage: dict) -> bool:
    return coverage["mode"] == "admission" and any(s.get("final_state") == "pack_refused" for s in coverage["shards"])


if __name__ == "__main__":
    sys.exit(main())
