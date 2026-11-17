#!/usr/bin/env python3
"""Convert a checkpoint to GGUF carrying the frozen tokenizer, then run the round trip on the result (G12 week 3, task 2).

    python tokenizer/convert_frozen.py --checkpoint <hf dir> --tokenizer <tokenizer.json> --tokenizer-sha256 <64 hex> \\
        --llama-cpp <b11669 checkout> --work <scratch> --out <report dir> [--outtype bf16] [--eos "<|endoftext|>"] \\
        [--convert-python <python of the converter venv>] [--llama-tokenize <bin>]

1. Refuses (exit 1) if tokenizer.json does not have the SHA-256 asked for, or its vocabulary is bigger than the
   checkpoint's embedding table.
2. Stages the checkpoint (symlinks) with the checkpoint's own tokenizer files replaced by the frozen tokenizer.json, and runs
   llama.cpp's convert_hf_to_gguf.py with the pre-tokenizer forced to `granite-embed-multi-97m` (the only built-in pattern
   that matches; the stock converter stops with "BPE pre-tokenizer was not recognized").
3. Runs gguf_roundtrip.py --gguf on the output, with --normalize-first. Exit code is that script's: 0 same ids everywhere,
   2 only the dropped normalizer explains the differences (known limit), 1 anything else. Held-out text only, reports hold
   ids, counts and hashes.

quantize_eval.py can import convert_frozen() for step 2 alone. tokenizer.json is an input and is never copied into the repo.
"""
from __future__ import annotations

import argparse, json, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gguf_roundtrip as rt  # noqa: E402

PRE = "granite-embed-multi-97m"
TOKENIZER_FILES = ("tokenizer.json", "tokenizer_config.json", "tokenizer.model", "special_tokens_map.json",
                   "vocab.json", "merges.txt", "added_tokens.json", "chat_template.jinja", "chat_template.json")


def stage(checkpoint: Path, tokenizer_json: Path, out: Path, bos: str, eos: str) -> None:
    """`out` = the checkpoint's files (symlinks) minus its tokenizer, plus the frozen one."""
    shutil.rmtree(out, ignore_errors=True)   # a reused --work must not keep another checkpoint's symlinks
    out.mkdir(parents=True)
    for f in checkpoint.iterdir():
        if f.name not in TOKENIZER_FILES:
            (out / f.name).symlink_to(f.resolve())
    (out / "tokenizer.json").write_bytes(tokenizer_json.read_bytes())
    (out / "tokenizer_config.json").write_text(json.dumps(
        {"tokenizer_class": "PreTrainedTokenizerFast", "bos_token": bos, "eos_token": eos}), encoding="utf-8")


def convert_frozen(checkpoint: Path, tokenizer_json: Path, sha256: str, llama_cpp: Path, outfile: Path, work: Path,
                   outtype: str = "bf16", bos: str = "<|begin_of_text|>", eos: str = "<|endoftext|>", python=None) -> Path:
    """The converter step. SystemExit with a message if the tokenizer is not the one asked for or does not fit."""
    got = rt.sha256(tokenizer_json)
    if got != sha256.lower():
        sys.exit(f"refusing: {tokenizer_json} has sha256 {got}, asked for {sha256}")
    t = json.loads(tokenizer_json.read_text(encoding="utf-8"))
    n_vocab = 1 + max(max(t["model"]["vocab"].values(), default=-1), max((a["id"] for a in t["added_tokens"]), default=-1))
    known = set(t["model"]["vocab"]) | {a["content"] for a in t["added_tokens"]}
    for role, tok in (("bos", bos), ("eos", eos)):
        if tok not in known:
            sys.exit(f"refusing: {role} token {tok!r} is not in {tokenizer_json.name}; pass --{role} with a token it has")
    cfg_vocab = json.loads((checkpoint / "config.json").read_text(encoding="utf-8")).get("vocab_size", 0)
    if cfg_vocab < n_vocab:
        sys.exit(f"refusing: the tokenizer has {n_vocab:,} ids, the checkpoint's embedding table {cfg_vocab:,}")
    staged = work / "staged_checkpoint"
    stage(checkpoint, tokenizer_json, staged, bos, eos)
    rt.convert(llama_cpp, staged, PRE, outfile, outtype, python)
    return outfile


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--checkpoint", type=Path, required=True, help="HF checkpoint folder (config.json, safetensors)")
    ap.add_argument("--tokenizer", type=Path, required=True, help="the frozen tokenizer.json")
    ap.add_argument("--tokenizer-sha256", required=True, help="SHA-256 the tokenizer.json must have")
    ap.add_argument("--llama-cpp", type=Path, required=True, help="llama.cpp b11669 checkout")
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="folder for the round-trip report")
    ap.add_argument("--outtype", default="bf16")
    ap.add_argument("--bos", default="<|begin_of_text|>")
    ap.add_argument("--eos", default="<|endoftext|>", help="the frozen tokenizer's eos (id 130822)")
    ap.add_argument("--convert-python", type=Path, help="python of the converter's venv (default: this one)")
    ap.add_argument("--llama-tokenize", type=Path)
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    gguf = convert_frozen(a.checkpoint, a.tokenizer, a.tokenizer_sha256, a.llama_cpp, a.work / "frozen.gguf", a.work,
                          a.outtype, a.bos, a.eos, a.convert_python)
    cmd = [sys.executable, str(HERE / "gguf_roundtrip.py"), "--tokenizer", str(a.tokenizer), "--name", "converted",
           "--gguf", str(gguf), "--normalize-first", "--llama-cpp", str(a.llama_cpp), "--work", str(a.work),
           "--out", str(a.out), "--pre", PRE, "--bos", a.bos, "--eos", a.eos]
    if a.llama_tokenize:
        cmd += ["--llama-tokenize", str(a.llama_tokenize)]
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
