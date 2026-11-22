#!/usr/bin/env python3
"""The flow on one checkpoint, then 100 fixed prompts (G12 week 3, core task 5). No network, no keys, writes only to --out.

    python scripts/flow_fixed_prompts.py --checkpoint <hf dir> --tokenizer <tokenizer.json> --tokenizer-sha256 <64 hex> \\
        --llama-cpp <b11669 checkout> --llama-quantize <bin> [--formats Q4_K_M,Q8_0] [--out out] [--eos "<|endoftext|>"]
    python scripts/flow_fixed_prompts.py --gguf-dir <quantize_eval.py --work> --formats Q8_0,Q4_K_M \\
        --manifest teams/10-post-training/eval/effort_manifest.json \\
        --source-dir code_contests=<dir> --source-dir hendrycks_math=<dir> [--out out]

--gguf-dir skips steps 2 and 3: it runs the prompts on the GGUFs that quantize_eval.py already built in its --work folder
(<name>-bf16.gguf and <name>-<format>.gguf), so the checkpoint is converted and quantized once. --delete-ggufs removes
those files at the end, after their sha256s are recorded.
summary.json records the tokenizer sha256 that quantize_eval.py wrote to its scores.json: the one *-scores.json in --gguf-dir,
or --scores (quantize_eval.py's --scores-out, if that is not in its --work folder). If none is found it is null, with a note.

--manifest takes the 100 prompts from Team 10's effort manifest (the fixed prompts the lead chose). Its resolved slots
(30 code, 25 math) are read from the pinned parquet files under --source-dir and checked against the manifest's sha256s by
Team 10's own effort_suite.py. Its unavailable slots (20 tool_agentic, 15 indic, 10 general) are filled from --prompts in id
order: tool_agentic from tool_call then reasoning, indic one language at a time, general from english. For Team 10 items
neither the prompt nor the generated text nor its token ids are written, only ids and sha256s (output_ids_sha256 in place of
output_ids), so no benchmark text or answer reaches the repo. The comparison with bf16 uses the ids in memory.

1. checks prompts/fixed_100.jsonl against prompts/fixed_100.sha256 (100 prompts, fixed ids and order);
2. tokenizer/convert_frozen.py: checkpoint + frozen tokenizer -> bf16 GGUF (refuses a tokenizer with another sha256);
3. llama-quantize each format (output layer Q8_0, as quantize_eval.py);
4. runs every prompt on bf16 and on each format: greedy (temperature 0), seed 0, same max tokens, token ids kept.

Writes out/prompts_<format>.jsonl (per prompt: id, output token ids, sha256 of the text, the text, finish reason, tokens/s)
and out/summary.json (finish reasons, mean tokens/s, agreement with bf16: identical outputs and mean shared prefix, with
--manifest reported separately for Team 10's 55 slots (g10_55) and our 45 fill slots (g12_fill_45), GGUF
sha256s, versions, wall time). The prompts are our own, not from a benchmark. The GGUF files go to out/_work and are removed
at the end (--keep to keep them), so out/ stays small. The tokenizer round trip on held-out text needs the network and is
tokenizer/convert_frozen.py's own run (#467); it is not repeated here.
"""
from __future__ import annotations

import argparse, hashlib, importlib.util, json, platform, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tokenizer"))
import convert_frozen as cf  # noqa: E402
import gguf_roundtrip as rt  # noqa: E402


def load_prompts(path: Path) -> list[dict]:
    want = path.with_suffix(".sha256").read_text().split()[0]
    if rt.sha256(path) != want:
        sys.exit(f"refusing: {path} does not have the sha256 in {path.with_suffix('.sha256').name}")
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 100 and len({r["id"] for r in rows}) == 100, "expected 100 prompts with unique ids"
    return rows


FILL = {"tool_agentic": ("tool_call", "reasoning"), "indic": ("indic",), "general": ("english",)}


def fill_order(rows: list[dict], cats: tuple[str, ...]) -> list[dict]:
    """Our prompts for one manifest category, in id order; indic goes one language at a time (round robin)."""
    picked = [r for c in cats for r in sorted((r for r in rows if r["category"] == c), key=lambda r: r["id"])]
    if cats != ("indic",):
        return picked
    langs: dict[str, list[dict]] = {}
    for r in picked:
        langs.setdefault(r["lang"], []).append(r)
    return [q for i in range(max(map(len, langs.values()))) for q in (v[i] for v in langs.values() if i < len(v))]


def manifest_prompts(manifest: Path, source_dirs: dict[str, Path], ours: list[dict]) -> tuple[list[dict], dict]:
    """Team 10's 100 slots: resolved ones from their pinned files, unavailable ones from our prompts (FILL)."""
    path = HERE.parents[1] / "10-post-training" / "eval" / "effort_suite.py"
    spec = importlib.util.spec_from_file_location("g10_effort_suite", path)
    es = importlib.util.module_from_spec(spec); sys.modules[spec.name] = es; spec.loader.exec_module(es)
    m = es.load_manifest(manifest)
    resolved = es.resolve_prompts(m, source_dirs)
    pools = {k: fill_order(ours, v) for k, v in FILL.items()}
    rows, used = [], {k: 0 for k in FILL}
    for s in m["slots"]:
        if s["slot"] in resolved:
            p = resolved[s["slot"]]
            rows.append({"id": s["slot"], "source": "g10", "task_id": p.task_id, "prompt": p.text, "private": True})
        elif s["category"] in pools and used[s["category"]] < len(pools[s["category"]]):
            q = pools[s["category"]][used[s["category"]]]; used[s["category"]] += 1
            rows.append({"id": s["slot"], "source": "g12", "task_id": q["id"], "prompt": q["prompt"], "private": False})
        else:
            sys.exit(f"refusing: slot {s['slot']} ({s['category']}) is unavailable and --prompts has nothing left to fill it")
    info = {"manifest_sha256": m["manifest_sha256"], "suite": m["suite"], "from_g10": len(resolved),
            "filled_from_prompts": {k: v for k, v in used.items() if v}}
    return rows, info


def tokenizer_sha_from_scores(gguf_dir: Path, scores: Path | None) -> tuple[str | None, str | None]:
    """(sha256, None) of the tokenizer quantize_eval.py put into the GGUFs, read from its scores.json; (None, why) if not found.
    --scores, else the one *-scores.json in the --gguf-dir (quantize_eval.py's default place for --scores-out)."""
    if scores is None:
        found = sorted(gguf_dir.glob("*-scores.json"))
        if len(found) != 1:
            return None, (f"no *-scores.json in {gguf_dir}" if not found else f"{len(found)} *-scores.json in {gguf_dir}") + "; pass --scores"
        scores = found[0]
    sha = json.loads(scores.read_text(encoding="utf-8")).get("tokenizer_sha256")
    if not (isinstance(sha, str) and len(sha) == 64):
        return None, f"{scores.name} has no tokenizer_sha256 (a run without --tokenizer)"
    return sha, None


def find_ggufs(work: Path, formats: list[str]) -> dict[str, Path]:
    """quantize_eval.py's files in its --work folder: exactly one <name>-bf16.gguf, then <name>-<format>.gguf."""
    bf16 = sorted(work.glob("*-bf16.gguf"))
    if len(bf16) != 1:
        sys.exit(f"refusing: expected one *-bf16.gguf in {work}, found {len(bf16)}")
    name = bf16[0].name[: -len("-bf16.gguf")]
    ggufs = {"bf16": bf16[0], **{f: work / f"{name}-{f}.gguf" for f in formats}}
    missing = [str(g) for g in ggufs.values() if not g.is_file()]
    if missing:
        sys.exit(f"refusing: missing {', '.join(missing)}")
    return ggufs


def public_row(r: dict) -> dict:
    """What is written for one prompt: a Team 10 row keeps only a sha256 of its output ids, never the ids themselves."""
    r = dict(r)
    if not r.pop("private"):
        return r
    ids = r.pop("output_ids")
    return r | {"output_ids_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest()}


def generate(gguf: Path, prompts: list[dict], max_tokens: int, n_ctx: int, ngl: int, out: Path) -> dict:
    from llama_cpp import Llama
    m = Llama(model_path=str(gguf), n_ctx=n_ctx, n_gpu_layers=ngl, seed=0, verbose=False)
    eos, rows, t_all = m.token_eos(), [], time.time()
    for p in prompts:
        ids_in = m.tokenize(p["prompt"].encode("utf-8"), add_bos=True, special=True)
        ids, finish, t0 = [], "length", time.time()
        for t in m.generate(ids_in, top_k=1, top_p=1.0, temp=0.0, repeat_penalty=1.0, reset=True):
            if t == eos:
                finish = "stop"; break
            ids.append(t)
            if len(ids) >= max_tokens or len(ids_in) + len(ids) >= n_ctx:
                break
        dt = time.time() - t0
        text = m.detokenize(ids).decode("utf-8", errors="replace")
        rows.append({"id": p["id"], **({"source": p["source"], "task_id": p["task_id"]} if "source" in p else {}),
                     "private": bool(p.get("private")),
                     "n_prompt_tokens": len(ids_in), "output_ids": ids, "n_output_tokens": len(ids),
                     "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
                     **({} if p.get("private") else {"text": text}),
                     "finish_reason": finish, "tokens_per_s": round(len(ids) / dt, 2) if dt > 0 else None})
    out.write_text("".join(json.dumps(public_row(r), ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    del m
    fin = {k: sum(r["finish_reason"] == k for r in rows) for k in ("stop", "length")}
    return {"rows": rows, "finish": fin, "wall_s": round(time.time() - t_all, 1),
            "mean_tokens_per_s": round(sum(r["tokens_per_s"] or 0 for r in rows) / len(rows), 2)}


def agreement(base: list[dict], other: list[dict]) -> dict:
    same, prefix = 0, 0.0
    for a, b in zip(base, other):
        x, y = a["output_ids"], b["output_ids"]
        k = next((i for i, (u, v) in enumerate(zip(x, y)) if u != v), min(len(x), len(y)))
        same += x == y
        prefix += k / max(len(x), len(y), 1)
    return {"identical_outputs": same, "of": len(base), "mean_shared_prefix_fraction": round(prefix / len(base), 4)}


def agreement_by_source(base: list[dict], other: list[dict]) -> dict:
    """agreement() as is for a plain run. With --manifest: one entry per source, Team 10's slots ("g10_55") and our fill
    ("g12_fill_45") reported separately, never pooled."""
    if not any("source" in r for r in base):
        return agreement(base, other)
    out = {}
    for src, name in (("g10", "g10_{}"), ("g12", "g12_fill_{}")):
        pairs = [(a, b) for a, b in zip(base, other) if a.get("source") == src]
        if pairs:
            out[name.format(len(pairs))] = agreement([a for a, _ in pairs], [b for _, b in pairs])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--checkpoint", type=Path)
    ap.add_argument("--tokenizer", type=Path)
    ap.add_argument("--tokenizer-sha256")
    ap.add_argument("--llama-cpp", type=Path, help="llama.cpp b11669 checkout (converter + gguf-py)")
    ap.add_argument("--llama-quantize", type=Path)
    ap.add_argument("--gguf-dir", type=Path, help="quantize_eval.py's --work: use its GGUFs instead of converting again")
    ap.add_argument("--scores", type=Path, help="with --gguf-dir: quantize_eval.py's --scores-out, for the tokenizer sha256 in "
                    "the summary (default: the *-scores.json in --gguf-dir)")
    ap.add_argument("--delete-ggufs", action="store_true", help="with --gguf-dir: delete the GGUF files at the end")
    ap.add_argument("--manifest", type=Path, help="Team 10's effort_manifest.json: its 100 slots replace --prompts")
    ap.add_argument("--source-dir", action="append", default=[], metavar="KEY=DIR",
                    help="local copy of a manifest source (code_contests, hendrycks_math), repeatable")
    ap.add_argument("--convert-python", type=Path, help="python of the converter's venv (default: this one)")
    ap.add_argument("--formats", default="Q4_K_M", help="comma list of llama-quantize types; bf16 is always run")
    ap.add_argument("--prompts", type=Path, default=HERE.parent / "prompts" / "fixed_100.jsonl")
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--max-tokens", type=int, default=128)
    ap.add_argument("--n-ctx", type=int, default=2048)
    ap.add_argument("--ngl", type=int, default=99, help="layers on the GPU (ignored by a CPU build)")
    ap.add_argument("--bos", default="<|begin_of_text|>")
    ap.add_argument("--eos", default="<|endoftext|>", help="the frozen tokenizer's eos (id 130822)")
    ap.add_argument("--keep", action="store_true", help="keep the GGUF files in out/_work")
    a = ap.parse_args()
    formats = [f for f in a.formats.split(",") if f and f != "bf16"]
    if not a.gguf_dir and not all((a.checkpoint, a.tokenizer, a.tokenizer_sha256, a.llama_cpp, a.llama_quantize)):
        ap.error("without --gguf-dir: --checkpoint, --tokenizer, --tokenizer-sha256, --llama-cpp and --llama-quantize are required")

    t0, prompts = time.time(), load_prompts(a.prompts)
    summary = {"prompts_sha256": rt.sha256(a.prompts)}
    if a.manifest:
        dirs = dict(x.split("=", 1) for x in a.source_dir)
        prompts, summary["manifest"] = manifest_prompts(a.manifest, {k: Path(v) for k, v in dirs.items()}, prompts)
    summary |= {"max_tokens": a.max_tokens, "n_ctx": a.n_ctx, "decoding": "greedy (temperature 0, top_k 1), seed 0", "formats": {}}
    work = a.out / "_work"
    if a.gguf_dir:
        ggufs = find_ggufs(a.gguf_dir, formats)
        summary["gguf_dir"] = "given (quantize_eval.py --work); converted and quantized there"
        sha, why = tokenizer_sha_from_scores(a.gguf_dir, a.scores)
        summary["tokenizer_sha256"] = sha
        if why:
            summary["tokenizer_sha256_note"] = why
            print(f"warning: tokenizer sha256 not recorded: {why}", file=sys.stderr)
        summary["formats"] = {f: {} for f in ggufs}
    else:
        work.mkdir(parents=True, exist_ok=True)
        bf16 = work / "model-bf16.gguf"
        t = time.time()
        cf.convert_frozen(a.checkpoint, a.tokenizer, a.tokenizer_sha256, a.llama_cpp, bf16, work, "bf16", a.bos, a.eos, a.convert_python)
        summary |= {"tokenizer_sha256": rt.sha256(a.tokenizer), "pre_tokenizer": cf.PRE, "convert_s": round(time.time() - t, 1),
                    "llama_convert_sha256": rt.sha256(a.llama_cpp / "convert_hf_to_gguf.py")}
        ggufs = {"bf16": bf16}
        for fmt in formats:
            t = time.time(); ggufs[fmt] = work / f"model-{fmt}.gguf"
            subprocess.run([str(a.llama_quantize), *([] if fmt == "Q8_0" else ["--output-tensor-type", "q8_0"]),
                            str(bf16), str(ggufs[fmt]), fmt], check=True, capture_output=True)
            summary["formats"][fmt] = {"quantize_s": round(time.time() - t, 1)}
        summary["formats"]["bf16"] = {}
    runs = {}
    a.out.mkdir(parents=True, exist_ok=True)
    for fmt, g in sorted(ggufs.items(), key=lambda kv: kv[0] != "bf16"):
        runs[fmt] = generate(g, prompts, a.max_tokens, a.n_ctx, a.ngl, a.out / f"prompts_{fmt}.jsonl")
        summary["formats"][fmt] |= {"gguf_sha256": rt.sha256(g), "size_bytes": g.stat().st_size,
                                    **{k: runs[fmt][k] for k in ("finish", "mean_tokens_per_s", "wall_s")}}
        if fmt != "bf16":
            summary["formats"][fmt]["agreement_with_bf16"] = agreement_by_source(runs["bf16"]["rows"], runs[fmt]["rows"])
    import llama_cpp
    summary |= {"total_s": round(time.time() - t0, 1), "machine": f"{platform.machine()} {platform.system()}",
                "versions": {"Python": platform.python_version(), "llama-cpp-python": llama_cpp.__version__}}
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    if not a.keep and not a.gguf_dir:
        shutil.rmtree(work)
    if a.gguf_dir and a.delete_ggufs:
        for g in ggufs.values():
            g.unlink()
    print(json.dumps({k: v for k, v in summary.items() if k != "versions"}, indent=1))


if __name__ == "__main__":
    main()
