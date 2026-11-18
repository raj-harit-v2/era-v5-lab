#!/usr/bin/env python3
"""Token records for one SFT set with a pinned frozen tokenizer (p1536 by default, C3 for the earlier records): run `convert.py`, check the output, write a record (WP14).

    python sft_v1_records.py run --set sft-dolly-15k --rows 1000 --tokenizer tokenizer.json \
        --revisions-json hf_pins.json --out-dir private/p1 --record-dir records
    python sft_v1_records.py full --set sft-dolly-15k --tokenizer tokenizer.json --revisions-json hf_pins.json \
        --out-dir private/full --record-dir records [--budget-gb 30]
    python sft_v1_records.py check --jsonl out.jsonl [--jsonl out2.jsonl ...] --tokenizer tokenizer.json

`run` converts the first `--rows` selected rows of the set (source order), reruns the same command for a second
`content_sha256`, then checks every written row:

  * `render.parse(text)` reads the row back, the effort equals the row's `effort`, and `render.render` of the
    parsed messages gives `text` byte for byte;
  * `input_ids` equal a fresh encode of `text`, decode back to `text`, and `loss_mask` has the same length;
  * no trained token lies outside a train span; each span starts after `<|im_start|>assistant\\n`, ends with
    `<|im_end|>` and holds no `<|im_start|>`; there is one span per assistant turn;
  * no token inside a `<|tool_result|>` block is trained, and every `<|tool_call|>` block lies inside a span;
  * the row ends with `<|endoftext|>`, which is not trained; ids are unique; ids stay below the vocabulary size.

`full` converts the whole set by streaming the pinned Hub files (no source copy is kept), writes rolling parts, gzips
each finished part and checks that it decompresses to the same bytes, runs the same checks on every row, and reruns the
first rows from the pinned source to compare their hash with the first lines of the full output. It stops the run if
the output passes a size budget. Full output is a conversion, not a pack: decontamination and held-out exclusion are
recorded as not done unless a record exists.

The record holds counts, hashes and timings only, never row text. Checks run in batches (`encode_batch`, numpy
offset arithmetic); there is no Python loop over tokens.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import resource
import subprocess
import sys
import time
from array import array
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent
MAX_LEN = 32768  # max_sequence_tokens, provisional for SFT data v1 (TSAI 14 Nov 2026)
C3_SHA256 = "15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3"  # C3 sample-v0 tokenizer.json (14 Nov)
P1536_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"  # p1536, TSAI Gate 3 notice (15 Nov)
# Frozen tokenizers by label. p1536 is the one for new work; C3 stays only to reproduce the C3 records.
FROZEN_TOKENIZERS = {"p1536": P1536_SHA256, "c3": C3_SHA256}
DEFAULT_TOKENIZER = "p1536"


def require_tokenizer(path: str, label: str = DEFAULT_TOKENIZER, allow_other: bool = False) -> str:
    """Refuse a tokenizer file whose sha256 is not the pinned one for `label` (a record from another tokenizer
    would be mislabelled). Returns the label written into the record's scope."""
    if label not in FROZEN_TOKENIZERS:
        raise SystemExit(f"unknown tokenizer label {label!r}; known: {sorted(FROZEN_TOKENIZERS)}")
    if allow_other:
        return label
    got, want = sha256_file(Path(path)), FROZEN_TOKENIZERS[label]
    if got != want:
        raise SystemExit(f"{path} has sha256 {got}, not the pinned {label} tokenizer {want}")
    return label


def require_c3(path: str, allow_other: bool = False) -> None:
    """The C3 pin (kept for the C3 records of 14-16 Nov)."""
    require_tokenizer(path, "c3", allow_other)


def _tok_label(a) -> str:
    """Check `--tokenizer` against `--tokenizer-label`'s pin; the name used in record scopes ("p1536" or "C3")."""
    label = require_tokenizer(a.tokenizer, getattr(a, "tokenizer_label", DEFAULT_TOKENIZER), a.allow_other_tokenizer)
    return "C3" if label == "c3" else label


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


render = _load("g10_render_rec", TEAM / "chat-format" / "render.py")
T = render.T


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def percentile(sorted_vals: np.ndarray, q: float) -> int | None:
    """Same rule as mix_inventory.percentile: the value at index int(q * n), clipped."""
    n = len(sorted_vals)
    return int(sorted_vals[min(n - 1, int(q * n))]) if n else None


def _ranges(text: str, open_tag: str, close_tag: str) -> list[tuple[int, int]]:
    out, pos = [], 0
    while (a := text.find(open_tag, pos)) >= 0:
        b = text.index(close_tag, a) + len(close_tag)
        out.append((a, b))
        pos = b
    return out


def _inside(starts: np.ndarray, ends: np.ndarray, ranges: list[tuple[int, int]]) -> np.ndarray:
    """Per token: True if (start, end) lies fully inside one of the sorted, non-overlapping ranges."""
    if not ranges:
        return np.zeros(len(starts), dtype=bool)
    rs = np.fromiter((a for a, _ in ranges), dtype=np.int64)
    re_ = np.fromiter((b for _, b in ranges), dtype=np.int64)
    i = np.searchsorted(rs, starts, side="right") - 1
    return (i >= 0) & (ends <= re_[np.clip(i, 0, None)])


def _overlaps(starts: np.ndarray, ends: np.ndarray, ranges: list[tuple[int, int]]) -> np.ndarray:
    """Per token: True if the token overlaps any range at all."""
    if not ranges:
        return np.zeros(len(starts), dtype=bool)
    rs = np.fromiter((a for a, _ in ranges), dtype=np.int64)
    re_ = np.fromiter((b for _, b in ranges), dtype=np.int64)
    i = np.searchsorted(rs, ends, side="left") - 1  # last range starting before the token ends
    return (i >= 0) & (re_[np.clip(i, 0, None)] > starts) & (starts < ends)


def load_tok(tokenizer_path: str):
    from tokenizers import Tokenizer

    return Tokenizer.from_file(tokenizer_path)


def checker_version() -> str:
    """Bind stored checks to their logic, renderer/marker state and relevant runtime dependencies."""
    import inspect
    import tokenizers

    src = "".join(inspect.getsource(f) for f in (_ranges, _inside, _overlaps, check_part))
    context = {
        "schema": 2,
        "row_checks_source_sha256": hashlib.sha256(src.encode("utf-8")).hexdigest(),
        "renderer_source_sha256": sha256_file(Path(render.__file__)),
        "effective_marker_assignments": render.ASSIGNED_SURFACES,
        "effective_surfaces": T,
        "max_len": MAX_LEN,
        "runtime": {"numpy": np.__version__, "tokenizers": tokenizers.__version__,
                    "python": list(sys.version_info[:3])},
    }
    return hashlib.sha256(json.dumps(context, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def check_part(path: Path, tok, tokenizer_sha256: str, batch: int = 64) -> dict:
    """Run every row check on one file (.jsonl or .jsonl.gz) and return mergeable counters.

    Besides the checks it hashes the decompressed bytes of the file (the same lines `convert.py` hashed) and records
    the compressed file's sha256, so the result is bound to those exact bytes. No row text is kept."""
    vocab = tok.get_vocab_size(with_added_tokens=True)
    eos_id = tok.token_to_id(T["endoftext"])
    norm = tok.normalizer
    fail: Counter = Counter()
    info: Counter = Counter()  # facts that are not failures
    lengths = array("I")
    efforts: Counter = Counter()
    ids_seen: set[str] = set()
    ids_in_order: list[str] = []
    n = tokens = trained = shifted = spans_n = calls_n = results_n = tool_rows = 0
    trained_excluded_boundary = 0

    def flush(rows: list[dict]) -> None:
        nonlocal n, tokens, trained, shifted, spans_n, calls_n, results_n, tool_rows, trained_excluded_boundary
        enc = tok.encode_batch([r["text"] for r in rows], add_special_tokens=False)
        dec = tok.decode_batch([r["input_ids"] for r in rows], skip_special_tokens=False)
        for r, e, d in zip(rows, enc, dec):
            text, ids, mask = r["text"], r["input_ids"], r["loss_mask"]
            n += 1
            efforts[r["effort"]] += 1
            lengths.append(len(ids))
            tokens += len(ids)
            if r["id"] in ids_seen:
                fail["duplicate_id"] += 1
            ids_seen.add(r["id"])
            ids_in_order.append(r["id"])
            try:
                parsed = render.parse(text)
                if parsed["effort"] != r["effort"]:
                    fail["parse_effort_differs"] += 1
                if render.render(parsed["messages"], parsed["effort"]) != text:
                    fail["render_parse_roundtrip_differs"] += 1
                n_assistant = sum(m["role"] == "assistant" for m in parsed["messages"])
            except render.RenderError:
                fail["parse_error"] += 1
                continue
            if ids != e.ids:
                fail["input_ids_differ_from_fresh_encode"] += 1
            if d != text:
                # the tokenizer's own normaliser (NFC for this tokenizer) rewrites some inputs; ids then decode to the
                # normalised text. That is a property of the tokenizer, not of the records, and is counted separately.
                if norm is not None and d == norm.normalize_str(text):
                    info["decode_equals_normalised_text_only"] += 1
                else:
                    fail["decode_differs_from_text"] += 1
            if len(mask) != len(ids):
                fail["mask_length_differs"] += 1
                continue
            if max(ids) >= vocab:
                fail["id_out_of_vocab"] += 1
            if ids[-1] != eos_id or mask[-1] != 0:
                fail["eos_missing_or_trained"] += 1
            m = np.asarray(mask, dtype=bool)
            trained += int(m.sum())
            shifted += int(m[1:].sum())  # labels are input_ids[1:], masked by loss_mask[1:]
            offsets = np.asarray(e.offsets, dtype=np.int64).reshape(-1, 2)
            starts, ends = offsets[:, 0], offsets[:, 1]
            spans = [tuple(s) for s in r["train_spans"]]
            spans_n += len(spans)
            if len(spans) != n_assistant:
                fail["spans_not_one_per_assistant_turn"] += 1
            head = f"{T['im_start']}assistant\n"
            for a, b in spans:
                if text[a - len(head):a] != head or not text[:b].endswith(T["im_end"]) or T["im_start"] in text[a:b]:
                    fail["span_boundary_wrong"] += 1
                    break
            if (m & ~_inside(starts, ends, spans)).any():
                fail["trained_token_outside_span"] += 1
            results = _ranges(text, T["tool_result"], T["tool_result_end"])
            calls = _ranges(text, T["tool_call"], T["tool_call_end"])
            results_n += len(results)
            calls_n += len(calls)
            tool_rows += bool(results or calls)
            if (m & _overlaps(starts, ends, results)).any():
                fail["tool_result_token_trained"] += 1
            if calls and not all(any(a <= ca and cb <= b for a, b in spans) for ca, cb in calls):
                fail["tool_call_outside_span"] += 1
            # a tool call's own tokens must be trained, except a token that straddles the block edge
            if calls:
                inside_call = _inside(starts, ends, calls)
                trained_excluded_boundary += int((inside_call & ~m).sum())

    plain_h, plain_bytes = hashlib.sha256(), 0
    rows: list[dict] = []
    with (gzip.open(path, "rb") if path.suffix == ".gz" else open(path, "rb")) as f:  # gzip checks the CRC at end of stream
        for line in f:
            plain_h.update(line)
            plain_bytes += len(line)
            rows.append(json.loads(line))
            if len(rows) >= batch:
                flush(rows)
                rows = []
    if rows:
        flush(rows)
    return {"checker_version": checker_version(), "tokenizer_sha256": tokenizer_sha256,
            "file": {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)},
            "plain_sha256": plain_h.hexdigest(), "plain_bytes": plain_bytes, "rows": n, "fail": dict(fail), "info": dict(info),
            "efforts": dict(efforts), "tokens": tokens, "trained": trained, "shifted": shifted, "spans": spans_n,
            "calls": calls_n, "results": results_n, "tool_rows": tool_rows, "untrained_in_calls": trained_excluded_boundary,
            "lengths": lengths.tolist(), "ids": ids_in_order}


def merge_parts(parts: list[dict]) -> dict:
    """Combine per-part results, in file order, into the result `check_files` has always returned.

    `duplicate_id` is recomputed on the union of ids, so a repeat across two parts is counted exactly as a single pass would."""
    fail: Counter = Counter()
    info: Counter = Counter()
    efforts: Counter = Counter()
    for p in parts:
        fail.update(p["fail"])
        info.update(p["info"])
        efforts.update(p["efforts"])
    n = sum(p["rows"] for p in parts)
    union: set[str] = set()
    for p in parts:
        union.update(p["ids"])
    dup = n - len(union)
    if dup:
        fail["duplicate_id"] = dup
    else:
        fail.pop("duplicate_id", None)
    untrained_calls = sum(p["untrained_in_calls"] for p in parts)
    if untrained_calls:
        fail["tool_call_token_untrained"] = untrained_calls
    tokens, trained = sum(p["tokens"] for p in parts), sum(p["trained"] for p in parts)
    arr = np.sort(np.concatenate([np.asarray(p["lengths"], dtype=np.uint32) for p in parts])) if n else np.zeros(0, dtype=np.uint32)
    return {
        "rows": n, "files": [p["file"] for p in parts], "checks_failed": dict(fail), "checks_ok": not fail, "info": dict(info),
        "tokens": tokens, "trained_tokens": trained, "trained_share": round(trained / tokens, 6) if tokens else None,
        "shifted_supervised_targets": sum(p["shifted"] for p in parts),
        "length": {"p50": percentile(arr, 0.5), "p95": percentile(arr, 0.95), "max": int(arr[-1]) if n else None, "min": int(arr[0]) if n else None},
        "rows_over_max_len": int((arr > MAX_LEN).sum()), "max_len": MAX_LEN,
        "effort_rows": {k: efforts.get(k, 0) for k in ("1k", "4k", "16k", "64k")},
        "train_spans": sum(p["spans"] for p in parts), "tool_call_blocks": sum(p["calls"] for p in parts),
        "tool_result_blocks": sum(p["results"] for p in parts), "rows_with_tool_blocks": sum(p["tool_rows"] for p in parts),
        "tool_call_tokens_untrained": untrained_calls,
        "unique_ids": len(union) == n,
    }


def check_files(paths: list[Path], tokenizer_path: str, batch: int = 64) -> dict:
    tok, sha = load_tok(tokenizer_path), sha256_file(Path(tokenizer_path))
    return merge_parts([check_part(Path(p), tok, sha, batch) for p in paths])


def run_convert(a, out: Path, progress: Path) -> dict:
    if getattr(a, "source_rows", None):  # a set whose reader splits `n` over its parts (aya_collection: n // len(AYA_COLLECTION_SUBSETS) per subset)
        reading = ["--hf-file", str(a.source_rows)]
    else:
        reading = ["--hf-file", str(10**9), "--limit", str(a.rows)]
    cmd = [sys.executable, str(HERE / "convert.py"), "--set", a.set, *reading,
           "--tokenizer", a.tokenizer, "--out", str(out), "--progress", str(progress)]
    if a.revisions_json:
        cmd += ["--revisions-json", str(a.revisions_json)]
    if a.file_spec:
        cmd += ["--file-spec", a.file_spec]
    env = dict(os.environ, G10_MAX_HUB_BYTES=str(int(a.max_hub_gb * 1e9)))
    if getattr(a, "local_root", None):
        env["G10_LOCAL_ROOT"] = str(a.local_root)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.monotonic()
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    wall = time.monotonic() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    if proc.returncode:
        raise SystemExit(f"convert.py failed ({proc.returncode}): {proc.stderr[-800:]}")
    manifest = json.loads(Path(f"{out}.manifest.json").read_text(encoding="utf-8"))
    bytes_read = json.loads(progress.read_text(encoding="utf-8")).get("bytes_read")
    return {"manifest": manifest, "wall_s": round(wall, 3), "cpu_user_s": round(after.ru_utime - before.ru_utime, 3),
            "cpu_sys_s": round(after.ru_stime - before.ru_stime, 3), "max_rss_mb": round(after.ru_maxrss / 2**20, 1),
            "hub_bytes_read": bytes_read}


def cmd_run(a) -> int:
    os.environ.setdefault("RAYON_NUM_THREADS", "2")  # the check pass runs in this process; keep it off the other slot's cores
    label = _tok_label(a)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{a.set}.first{a.rows}.jsonl"
    first = run_convert(a, out, out_dir / f"{a.set}.progress.json")
    again = out_dir / f"{a.set}.rerun.jsonl"
    second = run_convert(a, again, out_dir / f"{a.set}.progress2.json")
    man = first["manifest"]
    t0 = time.monotonic()
    checks = check_files([out], a.tokenizer)
    check_s = time.monotonic() - t0
    record = {
        "set": a.set, "scope": (f"first {a.source_rows} source rows (an equal share of each subset), {label}" if getattr(a, "source_rows", None)
                  else f"first {a.rows} selected rows, source order, {label}"), "tokenizer_sha256": sha256_file(Path(a.tokenizer)),
        "decision": man["decision"], "generator_model": man["generator_model"], "licence": man["licence"], "source": man["source"],
        "hub_revision": man.get("hub_revision"), "input": man["input"], "selection": man["selection"],
        "rows_scanned": man["rows_scanned"], "rows_in": man["rows_in"], "rows_out": man["rows"], "skipped": man["skipped"],
        "effort_manifest": man["effort"], "content_sha256": man["content_sha256"], "rerun_content_sha256": second["manifest"]["content_sha256"],
        "deterministic_rerun": man["content_sha256"] == second["manifest"]["content_sha256"],
        "file_sha256": checks["files"][0]["sha256"], "file_bytes": checks["files"][0]["bytes"],
        "checks": checks, "checks_wall_s": round(check_s, 2),
        "convert": {k: first[k] for k in ("wall_s", "cpu_user_s", "cpu_sys_s", "max_rss_mb", "hub_bytes_read")},
        "rows_per_s_convert": round(man["rows_scanned"] / first["wall_s"], 2) if first["wall_s"] else None,
        "tokens_per_s_convert": round(checks["tokens"] / first["wall_s"]) if first["wall_s"] else None,
        "rerun_wall_s": second["wall_s"],
    }
    # mix_inventory token-record keys
    record["token_record"] = {"set_id": a.set, "rows": man["rows"], "sequence_tokens": checks["tokens"],
                              "shifted_supervised_targets": checks["shifted_supervised_targets"],
                              "tokenizer_sha256": record["tokenizer_sha256"], "length": checks["length"], "effort": man["effort"],
                              "basis": record["scope"] + "; not the admissible kept rows"}
    again.unlink(missing_ok=True)
    Path(f"{again}.manifest.json").unlink(missing_ok=True)
    rd = Path(a.record_dir)
    rd.mkdir(parents=True, exist_ok=True)
    (rd / f"{a.set}.record.json").write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"set": a.set, "rows_out": record["rows_out"], "tokens": checks["tokens"], "share": checks["trained_share"],
                      "over": checks["rows_over_max_len"], "ok": checks["checks_ok"] and record["deterministic_rerun"],
                      "failed": checks["checks_failed"], "rows_per_s": record["rows_per_s_convert"], "wall_s": first["wall_s"]}))
    return 0 if checks["checks_ok"] and record["deterministic_rerun"] else 1


def compress_part(part: Path, running: "hashlib._Hash") -> dict:
    """gzip one finished part, check that it decompresses to the same bytes, delete the plain file.

    `running` accumulates the sha256 of the plain parts in order, which must equal convert.py's content_sha256."""
    gz = Path(f"{part}.gz")
    plain_h = hashlib.sha256()
    size = 0
    with open(part, "rb") as src, gzip.open(gz, "wb", compresslevel=6) as dst:
        for block in iter(lambda: src.read(1 << 22), b""):
            plain_h.update(block)
            running.update(block)
            dst.write(block)
            size += len(block)
    back_h = hashlib.sha256()
    with gzip.open(gz, "rb") as f:  # read the compressed file back: this is the verified copy
        for block in iter(lambda: f.read(1 << 22), b""):
            back_h.update(block)
    if back_h.hexdigest() != plain_h.hexdigest():
        raise SystemExit(f"{gz.name}: decompressed bytes differ from the written part")
    part.unlink()
    return {"name": gz.name, "plain_bytes": size, "plain_sha256": plain_h.hexdigest(), "gz_bytes": gz.stat().st_size,
            "gz_sha256": sha256_file(gz)}


def first_lines_sha256(gz_parts: list[Path], n: int) -> str:
    h, left = hashlib.sha256(), n
    for p in gz_parts:
        with gzip.open(p, "rb") as f:
            for line in f:
                if left <= 0:
                    return h.hexdigest()
                h.update(line)
                left -= 1
    return h.hexdigest()


def cmd_full(a) -> int:
    import shutil

    os.environ.setdefault("RAYON_NUM_THREADS", str(a.threads))  # the check pass runs in this process
    label = _tok_label(a)

    out_dir = Path(a.out_dir) / a.set
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / a.set
    budget = int(a.budget_gb * 2**30)
    global_budget = int(a.global_budget_gb * 2**30)
    already = sum(f.stat().st_size for f in Path(a.out_dir).rglob("*") if f.is_file())
    if already + budget > global_budget:
        raise SystemExit(f"{already / 2**30:.1f} GiB already under {a.out_dir} plus this set's {a.budget_gb} GiB budget is over "
                         f"the {a.global_budget_gb} GiB global budget")
    free0 = shutil.disk_usage(out_dir).free
    if free0 < budget + (20 << 30):
        raise SystemExit(f"free disk {free0 / 2**30:.0f} GiB is below budget + 20 GiB reserve")
    cmd = [sys.executable, str(HERE / "convert.py"), "--set", a.set, "--hf-file", str(10**12), "--tokenizer", a.tokenizer,
           "--out", str(prefix), "--roll-mb", str(a.roll_mb), "--progress", str(out_dir / "progress.json")]
    if a.revisions_json:
        cmd += ["--revisions-json", str(a.revisions_json)]
    if a.max_rows:
        cmd += ["--limit", str(a.max_rows)]
    env = dict(os.environ, G10_MAX_HUB_BYTES=str(int(a.max_hub_gb * 1e9)), RAYON_NUM_THREADS=str(a.threads))
    if a.local_root:  # a staged copy of the Hub repo at the pinned revision: <root>/<dataset id>/<file>; no network is used
        env["G10_LOCAL_ROOT"] = str(a.local_root)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.monotonic()
    log = open(out_dir / "convert.log", "w", encoding="utf-8")  # a file, not a pipe: nothing can fill and block the run
    proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
    running, parts, done_names = hashlib.sha256(), [], set()
    aborted = None
    while True:
        finished = proc.poll() is not None
        for part in sorted(out_dir.glob(f"{a.set}.part*.jsonl")):
            if part.name not in done_names:
                done_names.add(part.name)
                parts.append(compress_part(part, running))
        used = sum(f.stat().st_size for f in out_dir.iterdir() if f.is_file())
        total = sum(f.stat().st_size for f in Path(a.out_dir).rglob("*") if f.is_file())  # every full run under --out-dir
        if (used > budget or total > global_budget) and not finished:
            proc.kill()
            aborted = (f"output reached {used / 2**30:.1f} GiB, over the {a.budget_gb} GiB per-set budget" if used > budget else
                       f"all outputs under {a.out_dir} reached {total / 2**30:.1f} GiB, over the {a.global_budget_gb} GiB global budget")
            break
        if finished:
            break
        time.sleep(3)
    proc.wait()
    log.close()
    wall = time.monotonic() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    if aborted or proc.returncode:
        raise SystemExit(aborted or f"convert.py failed ({proc.returncode}): {(out_dir / 'convert.log').read_text(encoding='utf-8')[-800:]}")
    manifest = json.loads(Path(f"{prefix}.manifest.json").read_text(encoding="utf-8"))
    if running.hexdigest() != manifest["content_sha256"]:
        raise SystemExit("sha256 of the plain parts differs from convert.py's content_sha256")
    gz_paths = [out_dir / p["name"] for p in parts]
    t1 = time.monotonic()
    checks = check_files(gz_paths, a.tokenizer)
    check_s = time.monotonic() - t1
    # determinism: rerun the first rows from the same pinned source and compare with the first lines of the full output
    rerun_hash = rerun_rows = None
    if a.rerun_rows:
        again = out_dir / "rerun.jsonl"
        sub = argparse.Namespace(set=a.set, rows=a.rerun_rows, tokenizer=a.tokenizer, revisions_json=a.revisions_json,
                                 file_spec=None, max_hub_gb=a.max_hub_gb, local_root=a.local_root)
        second = run_convert(sub, again, out_dir / "progress2.json")
        rerun_rows, rerun_hash = second["manifest"]["rows"], second["manifest"]["content_sha256"]
        again.unlink(missing_ok=True)
        Path(f"{again}.manifest.json").unlink(missing_ok=True)
        deterministic = first_lines_sha256(gz_paths, rerun_rows) == rerun_hash
    else:
        deterministic = None
    plain = sum(p["plain_bytes"] for p in parts)
    gz = sum(p["gz_bytes"] for p in parts)
    record = {
        "set": a.set, "scope": f"full set as selected by the adapter, source order, {label}", "status": a.status,
        "tokenizer_sha256": sha256_file(Path(a.tokenizer)), "decision": manifest["decision"], "generator_model": manifest["generator_model"],
        "licence": manifest["licence"], "source": manifest["source"], "hub_revision": manifest.get("hub_revision"),
        "input": manifest["input"], "selection": manifest["selection"], "rows_scanned": manifest["rows_scanned"],
        "rows_in": manifest["rows_in"], "rows_out": manifest["rows"], "skipped": manifest["skipped"], "effort_manifest": manifest["effort"],
        "content_sha256": manifest["content_sha256"], "rerun_rows": rerun_rows, "rerun_content_sha256": rerun_hash,
        "deterministic_rerun": deterministic, "parts": parts, "plain_bytes": plain, "gz_bytes": gz,
        "gz_ratio": round(plain / gz, 2) if gz else None, "checks": checks, "checks_wall_s": round(check_s, 1),
        "convert": {"wall_s": round(wall, 1), "cpu_user_s": round(after.ru_utime - before.ru_utime, 1),
                    "cpu_sys_s": round(after.ru_stime - before.ru_stime, 1), "max_rss_mb": round(after.ru_maxrss / 2**20, 1),
                    "threads": a.threads, "hub_bytes_read": json.loads((out_dir / "progress.json").read_text(encoding="utf-8")).get("bytes_read")},
        "rows_per_s_convert": round(manifest["rows_scanned"] / wall, 2), "tokens_per_s_convert": round(checks["tokens"] / wall),
        "decontam": "not run on this output: no kept-row record exists for this set; converted, not decontaminated",
        "heldout_ids_excluded": 0, "heldout_note": "no held-out id list exists for this set at run time (WP15 lists cover OCR-2 shards only)",
    }
    record["token_record"] = {"set_id": a.set, "rows": manifest["rows"], "sequence_tokens": checks["tokens"],
                              "shifted_supervised_targets": checks["shifted_supervised_targets"],
                              "tokenizer_sha256": record["tokenizer_sha256"], "length": checks["length"], "effort": manifest["effort"],
                              "basis": record["scope"] + "; converted, not decontaminated"}
    rd = Path(a.record_dir)
    rd.mkdir(parents=True, exist_ok=True)
    (rd / f"{a.set}.full.record.json").write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    ok = checks["checks_ok"] and deterministic is not False
    print(json.dumps({"set": a.set, "rows_out": record["rows_out"], "tokens": checks["tokens"], "share": checks["trained_share"],
                      "over": checks["rows_over_max_len"], "gz_GiB": round(gz / 2**30, 2), "ok": ok, "failed": checks["checks_failed"],
                      "rows_per_s": record["rows_per_s_convert"], "wall_s": record["convert"]["wall_s"], "deterministic": deterministic}))
    return 0 if ok else 1


def write_json_atomic(path: Path, obj, *, overwrite: bool = False) -> None:
    """Write JSON to a temporary file in the same folder, then rename. Refuses to replace an existing file unless told to."""
    path = Path(path)
    if path.exists() and not overwrite:
        raise SystemExit(f"{path} already exists; not overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Two check-parts workers may meet at the same part. Each writer needs its own
    # temporary file; a shared .tmp path lets one rename the other writer's file.
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
        tmp = Path(handle.name)
        json.dump(obj, handle, indent=1, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    try:
        if overwrite:
            tmp.replace(path)
        else:
            # Atomic no-replace publication, including when two finalizers race.
            # The temporary file and destination are on the same filesystem.
            try:
                os.link(tmp, path)
            except FileExistsError:
                raise SystemExit(f"{path} already exists; not overwritten") from None
    finally:
        tmp.unlink(missing_ok=True)


def complete_gz_parts(set_dir: Path, set_id: str) -> list[Path]:
    """Finished parts of a running `full` conversion: `<set>.partNNNN.jsonl.gz` whose plain `.jsonl` has been removed.

    The driver gzips a finished part, reads the .gz back against the plain bytes and only then deletes the plain file,
    so a .gz that still has its plain sibling may be mid-write and is skipped."""
    out = []
    for gz in sorted(set_dir.glob(f"{set_id}.part*.jsonl.gz")):
        if not Path(str(gz)[: -len(".gz")]).exists():
            out.append(gz)
    return out


def partial_path(partials_dir: Path, gz: Path) -> Path:
    return Path(partials_dir) / f"{gz.name}.check.json"


def load_valid_partial(partials_dir: Path, gz: Path, tokenizer_sha256: str) -> dict | None:
    """A stored per-part result, only if it was made by this checker version, with this tokenizer, on these exact gz bytes."""
    path = partial_path(partials_dir, gz)
    if not path.is_file():
        return None
    try:
        part = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    ok = (part.get("checker_version") == checker_version() and part.get("tokenizer_sha256") == tokenizer_sha256
          and part["file"]["name"] == gz.name and part["file"]["bytes"] == gz.stat().st_size
          and part["file"]["sha256"] == sha256_file(gz))
    return part if ok else None


def cmd_check_parts(a) -> int:
    """Check the finished parts of a running conversion, one part at a time, and store each result next to its gz sha256.

    Run it while `full` is still converting; `finalize` reuses every stored result that is still valid and checks the rest."""
    _tok_label(a)
    set_dir = Path(a.out_dir) / a.set
    tok, tsha = load_tok(a.tokenizer), sha256_file(Path(a.tokenizer))
    deadline = time.monotonic() + a.max_seconds if a.max_seconds else None
    done = skipped = 0
    todo = complete_gz_parts(set_dir, a.set)
    for gz in (todo[::-1] if a.reverse else todo):  # two processes, one with --reverse, meet in the middle
        if load_valid_partial(a.partials_dir, gz, tsha) is not None:
            skipped += 1
            continue
        t0 = time.monotonic()
        part = check_part(gz, tok, tsha)
        part["check_wall_s"] = round(time.monotonic() - t0, 2)
        write_json_atomic(partial_path(a.partials_dir, gz), part, overwrite=True)
        done += 1
        print(json.dumps({"part": gz.name, "rows": part["rows"], "tokens": part["tokens"], "fail": part["fail"],
                          "wall_s": part["check_wall_s"]}), flush=True)
        if deadline and time.monotonic() > deadline:
            break
    print(json.dumps({"checked_now": done, "already_valid": skipped, "complete_parts": len(complete_gz_parts(set_dir, a.set))}))
    return 0


def cmd_finalize(a) -> int:
    """Finish a conversion from its finished files, without converting again, and write the full record.

    Every check `full` makes is made here, from the files on disk:
      * the manifest exists, names exactly the parts on disk (no extra, partial or uncompressed part), and its Hub revision,
        tokenizer hash and decision agree with the pin file, the pinned tokenizer hash and the licence table;
      * each part decompresses to the end (gzip CRC) and its plain bytes are hashed; the hash of all plain bytes in order
        equals the manifest's `content_sha256`; the line count equals the manifest's row count;
      * every row check of `check_files` (parse round trip, ids, decode, masks, spans, tool blocks, EOS, length, unique ids),
        taken from valid stored per-part results where there are any, and run here for the others;
      * the first rows are converted again from the pinned source and their hash equals the first lines of the output.
    What the original run measured and this one cannot (convert wall time, CPU time, peak RSS, rows per second, Hub bytes)
    is written as null with the reason. The record is written once, atomically, after every check has passed."""
    label = _tok_label(a)
    os.environ.setdefault("RAYON_NUM_THREADS", str(a.threads))
    out_dir = Path(a.out_dir) / a.set
    prefix = out_dir / a.set
    rec_path = Path(a.record_dir) / f"{a.set}.full.record.json"
    if rec_path.exists():
        raise SystemExit(f"{rec_path} already exists; not overwritten")
    manifest_path = Path(f"{prefix}.manifest.json")
    if not manifest_path.is_file():
        raise SystemExit(f"{manifest_path} is missing: the converter has not finished")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    # --- layout ----------------------------------------------------------------------------------
    want = [f"{name}.gz" for name in manifest.get("parts", [])]
    on_disk = sorted(p.name for p in out_dir.glob(f"{a.set}.part*"))
    if not want:
        problems.append("manifest lists no parts")
    if on_disk != sorted(want):
        problems.append(f"parts on disk differ from the manifest: missing {sorted(set(want) - set(on_disk))[:3]}, extra {sorted(set(on_disk) - set(want))[:3]}")
    if want != sorted(want) or [int(w.split(".part")[1][:4]) for w in want] != list(range(len(want))):
        problems.append("part numbers are not 0..N-1 in order")
    pins = json.loads(Path(a.revisions_json).read_text(encoding="utf-8"))["datasets"]
    meta = _load("g10_convert_fin", HERE / "convert.py").licence_row(a.set)
    tsha = sha256_file(Path(a.tokenizer))
    if manifest.get("hub_revision") != pins.get(meta["source"], {}).get("sha"):
        problems.append(f"manifest hub_revision {manifest.get('hub_revision')} is not the pinned {pins.get(meta['source'], {}).get('sha')}")
    if f"tokenizer sha256 {tsha}" != manifest.get("effort_counter"):
        problems.append(f"manifest effort_counter does not name the {label} tokenizer hash")
    for key in ("decision", "generator_model", "licence", "source"):
        if manifest.get(key) != meta[key]:
            problems.append(f"manifest {key} differs from the licence table now")
    if problems:
        raise SystemExit("cannot finalize: " + "; ".join(problems))
    gz_paths = [out_dir / w for w in want]
    # --- integrity: every part to the end of its stream, hash of all plain bytes in order -----------------
    t0 = time.monotonic()
    running, parts, lines_total = hashlib.sha256(), [], 0
    for gz in gz_paths:
        plain_h, size, lines = hashlib.sha256(), 0, 0
        with gzip.open(gz, "rb") as f:
            for block in iter(lambda: f.read(1 << 22), b""):
                plain_h.update(block)
                running.update(block)
                size += len(block)
                lines += block.count(b"\n")
        lines_total += lines
        parts.append({"name": gz.name, "plain_bytes": size, "plain_sha256": plain_h.hexdigest(), "gz_bytes": gz.stat().st_size,
                      "gz_sha256": sha256_file(gz), "rows": lines})
    integrity_s = time.monotonic() - t0
    if running.hexdigest() != manifest["content_sha256"]:
        raise SystemExit("sha256 of the decompressed parts in order differs from the manifest content_sha256")
    if lines_total != manifest["rows"]:
        raise SystemExit(f"{lines_total} lines in the parts, manifest says {manifest['rows']} rows")
    # --- row checks: reuse valid stored results, run the rest -------------------------------------------
    tok = load_tok(a.tokenizer)
    results, reused, ran_here = [], 0, 0
    t1 = time.monotonic()
    for gz, info in zip(gz_paths, parts):
        part = None if a.no_reuse else load_valid_partial(a.partials_dir, gz, tsha) if a.partials_dir else None
        if part is not None and part["plain_sha256"] == info["plain_sha256"] and part["plain_bytes"] == info["plain_bytes"] and part["rows"] == info["rows"]:
            reused += 1
        else:
            part = check_part(gz, tok, tsha)
            ran_here += 1
            if (part["plain_sha256"], part["rows"]) != (info["plain_sha256"], info["rows"]):
                raise SystemExit(f"{gz.name}: the check read different bytes from the integrity pass")
        results.append(part)
    checks = merge_parts(results)
    check_s = time.monotonic() - t1
    if checks["rows"] != manifest["rows"]:
        raise SystemExit(f"checks saw {checks['rows']} rows, manifest says {manifest['rows']}")
    # --- determinism: the first rows converted again from the pinned source --------------------------------
    rerun_hash = rerun_rows = None
    deterministic = None
    if a.rerun_rows:
        again = out_dir / "rerun.jsonl"
        sub = argparse.Namespace(set=a.set, rows=a.rerun_rows, tokenizer=a.tokenizer, revisions_json=a.revisions_json,
                                 file_spec=None, max_hub_gb=a.max_hub_gb, local_root=a.local_root)
        second = run_convert(sub, again, out_dir / "progress2.json")
        rerun_rows, rerun_hash = second["manifest"]["rows"], second["manifest"]["content_sha256"]
        again.unlink(missing_ok=True)
        Path(f"{again}.manifest.json").unlink(missing_ok=True)
        deterministic = first_lines_sha256(gz_paths, rerun_rows) == rerun_hash
    plain, gz_total = sum(p["plain_bytes"] for p in parts), sum(p["gz_bytes"] for p in parts)
    unknown = "unknown: the converter was not run by this command, and the original driver did not record it"
    record = {
        "set": a.set, "scope": f"full set as selected by the adapter, source order, {label}", "status": a.status,
        "tokenizer_sha256": tsha, "decision": manifest["decision"], "generator_model": manifest["generator_model"],
        "licence": manifest["licence"], "source": manifest["source"], "hub_revision": manifest.get("hub_revision"),
        "input": manifest["input"], "selection": manifest["selection"], "rows_scanned": manifest["rows_scanned"],
        "rows_in": manifest["rows_in"], "rows_out": manifest["rows"], "skipped": manifest["skipped"], "effort_manifest": manifest["effort"],
        "content_sha256": manifest["content_sha256"], "rerun_rows": rerun_rows, "rerun_content_sha256": rerun_hash,
        "deterministic_rerun": deterministic,
        "parts": [{k: p[k] for k in ("name", "plain_bytes", "plain_sha256", "gz_bytes", "gz_sha256")} for p in parts],
        "plain_bytes": plain, "gz_bytes": gz_total, "gz_ratio": round(plain / gz_total, 2) if gz_total else None,
        "checks": checks, "checks_wall_s": round(check_s, 1),
        "convert": {"wall_s": None, "cpu_user_s": None, "cpu_sys_s": None, "max_rss_mb": None, "threads": None, "hub_bytes_read": None,
                    "unknown": unknown},
        "rows_per_s_convert": None, "tokens_per_s_convert": None,
        "finalized": {"by": "sft_v1_records.py finalize", "integrity_pass_wall_s": round(integrity_s, 1), "parts_reused_from_stored_checks": reused,
                      "parts_checked_here": ran_here, "check_threads": int(os.environ["RAYON_NUM_THREADS"]),
                      "checker_version": checker_version(), "convert_py_sha256": sha256_file(HERE / "convert.py")},
        "decontam": "not run on this output: no kept-row record exists for this set; converted, not decontaminated",
        "heldout_ids_excluded": 0, "heldout_note": "no held-out id list exists for this set at run time (WP15 lists cover OCR-2 shards only)",
    }
    record["token_record"] = {"set_id": a.set, "rows": manifest["rows"], "sequence_tokens": checks["tokens"],
                              "shifted_supervised_targets": checks["shifted_supervised_targets"], "tokenizer_sha256": tsha,
                              "length": checks["length"], "effort": manifest["effort"],
                              "basis": record["scope"] + "; converted, not decontaminated"}
    ok = checks["checks_ok"] and deterministic is not False
    if not ok:
        print(json.dumps({"set": a.set, "ok": False, "failed": checks["checks_failed"], "deterministic": deterministic}))
        return 1
    write_json_atomic(rec_path, record)
    print(json.dumps({"set": a.set, "rows_out": record["rows_out"], "tokens": checks["tokens"], "share": checks["trained_share"],
                      "over": checks["rows_over_max_len"], "gz_GiB": round(gz_total / 2**30, 2), "ok": True, "failed": checks["checks_failed"],
                      "deterministic": deterministic, "reused_parts": reused, "checked_here": ran_here,
                      "integrity_s": round(integrity_s, 1), "check_s": round(check_s, 1)}))
    return 0


def cmd_verify_local(a) -> int:
    """Check a staged copy of a Hub repo (`<root>/<dataset id>/<file>`) against the pinned LFS sha256 of every file the set reads."""
    convert = _load("g10_convert_vl", HERE / "convert.py")
    pins = json.loads(Path(a.revisions_json).read_text(encoding="utf-8"))["datasets"]
    repo = convert.licence_row(a.set)["source"]
    os.environ["G10_LOCAL_ROOT"] = str(a.root)
    if repo not in pins:
        raise SystemExit(f"{repo} is not in {a.revisions_json}")
    spec = convert.ADAPTERS[a.set][2][1]
    if a.set == "sft-indic-aya-collection":
        names = list(convert.AYA_COLLECTION_SUBSETS)
    else:
        names = convert.expand_paths(repo, spec)
    bad = 0
    for name in names:
        pin = pins[repo]["files"].get(name)
        path = Path(a.root) / repo / name
        if pin is None or not path.is_file():
            print(f"MISSING {name}")
            bad += 1
            continue
        want = pin.get("lfs_sha256")
        got = sha256_file(path) if want else None
        ok = path.stat().st_size == pin["size"] and (want is None or got == want)
        print(("ok     " if ok else "DIFFER ") + name)
        bad += not ok
    print(json.dumps({"set": a.set, "revision": pins[repo]["sha"], "files": len(names), "bad": bad}))
    return 1 if bad else 0


def cmd_check(a) -> int:
    res = check_files([Path(p) for p in a.jsonl], a.tokenizer)
    print(json.dumps(res, indent=1))
    return 0 if res["checks_ok"] else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--set", required=True)
    r.add_argument("--rows", type=int, default=1000)
    r.add_argument("--tokenizer", required=True)
    r.add_argument("--tokenizer-label", choices=sorted(FROZEN_TOKENIZERS), default=DEFAULT_TOKENIZER,
                    help="which pinned tokenizer --tokenizer must be (default p1536, frozen 15 Nov 2026)")
    r.add_argument("--allow-other-tokenizer", action="store_true", help="skip the pinned-tokenizer sha256 check (tests only)")
    r.add_argument("--revisions-json")
    r.add_argument("--file-spec")
    r.add_argument("--source-rows", type=int, help="read exactly this many source rows instead of --rows selected rows")
    r.add_argument("--out-dir", required=True)
    r.add_argument("--record-dir", required=True)
    r.add_argument("--max-hub-gb", type=float, default=2.0, help="stop the convert run after this many GB from the Hub")
    r.set_defaults(fn=cmd_run)
    f = sub.add_parser("full")
    f.add_argument("--set", required=True)
    f.add_argument("--tokenizer", required=True)
    f.add_argument("--tokenizer-label", choices=sorted(FROZEN_TOKENIZERS), default=DEFAULT_TOKENIZER,
                    help="which pinned tokenizer --tokenizer must be (default p1536, frozen 15 Nov 2026)")
    f.add_argument("--allow-other-tokenizer", action="store_true", help="skip the pinned-tokenizer sha256 check (tests only)")
    f.add_argument("--revisions-json")
    f.add_argument("--out-dir", required=True)
    f.add_argument("--record-dir", required=True)
    f.add_argument("--roll-mb", type=float, default=400)
    f.add_argument("--budget-gb", type=float, default=30, help="kill the run if its (compressed) output passes this many GiB")
    f.add_argument("--global-budget-gb", type=float, default=80,
                   help="refuse to start, or kill the run, if all outputs under --out-dir (every set) would pass this many GiB")
    f.add_argument("--max-hub-gb", type=float, default=60, help="stop the convert run after this many GB from the Hub")
    f.add_argument("--threads", type=int, default=4, help="RAYON_NUM_THREADS for the convert run")
    f.add_argument("--rerun-rows", type=int, default=2000)
    f.add_argument("--max-rows", type=int, help="stop after this many selected rows (a test-log run of the full command)")
    f.add_argument("--local-root", help="read a staged copy of the Hub repo under <local-root>/<dataset id>/ instead of the Hub")
    f.add_argument("--status", default="converted, not decontaminated; not a pack")
    f.set_defaults(fn=cmd_full)
    cp = sub.add_parser("check-parts", help="check the finished parts of a running conversion and store each result")
    cp.add_argument("--set", required=True)
    cp.add_argument("--tokenizer", required=True)
    cp.add_argument("--tokenizer-label", choices=sorted(FROZEN_TOKENIZERS), default=DEFAULT_TOKENIZER,
                    help="which pinned tokenizer --tokenizer must be (default p1536, frozen 15 Nov 2026)")
    cp.add_argument("--out-dir", required=True)
    cp.add_argument("--partials-dir", required=True, type=Path)
    cp.add_argument("--max-seconds", type=float, help="stop starting new parts after this long")
    cp.add_argument("--reverse", action="store_true", help="take parts from the last one backwards")
    cp.add_argument("--allow-other-tokenizer", action="store_true")
    cp.set_defaults(fn=cmd_check_parts)
    fz = sub.add_parser("finalize", help="finish a conversion from its files on disk and write the full record")
    fz.add_argument("--set", required=True)
    fz.add_argument("--tokenizer", required=True)
    fz.add_argument("--tokenizer-label", choices=sorted(FROZEN_TOKENIZERS), default=DEFAULT_TOKENIZER,
                    help="which pinned tokenizer --tokenizer must be (default p1536, frozen 15 Nov 2026)")
    fz.add_argument("--revisions-json", required=True)
    fz.add_argument("--out-dir", required=True)
    fz.add_argument("--record-dir", required=True)
    fz.add_argument("--partials-dir", type=Path, help="stored per-part checks to reuse where still valid")
    fz.add_argument("--no-reuse", action="store_true", help="run every row check here, ignoring stored results")
    fz.add_argument("--rerun-rows", type=int, default=2000)
    fz.add_argument("--threads", type=int, default=4)
    fz.add_argument("--max-hub-gb", type=float, default=2.0)
    fz.add_argument("--local-root")
    fz.add_argument("--status", default="converted, not decontaminated; not a pack")
    fz.add_argument("--allow-other-tokenizer", action="store_true")
    fz.set_defaults(fn=cmd_finalize)
    v = sub.add_parser("verify-local")
    v.add_argument("--set", required=True)
    v.add_argument("--root", required=True)
    v.add_argument("--revisions-json", required=True)
    v.set_defaults(fn=cmd_verify_local)
    c = sub.add_parser("check")
    c.add_argument("--jsonl", action="append", required=True)
    c.add_argument("--tokenizer", required=True)
    c.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
