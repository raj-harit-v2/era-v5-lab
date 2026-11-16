#!/usr/bin/env python3
"""convert_frozen.py injects the frozen tokenizer into the converter output and refuses a wrong one (G12 week 3, task 2).

    python test_convert_frozen.py <llama.cpp b11669 checkout>
    LLAMA_CPP=<checkout> python -m pytest test_convert_frozen.py

A tiny "checkpoint" ships tokenizer A; tokenizer B (another training text, same vocabulary size) is the "frozen" one.
Checks: a wrong sha256 is refused before anything is converted; with the right one the GGUF cuts the test lines into B's ids
(and A's differ, so the test would notice an injection that did nothing). Sentences are the ones of
test_gguf_roundtrip_normalizer.py, written for the tests, not from any benchmark.
"""
from __future__ import annotations

import json, os, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import convert_frozen as cf  # noqa: E402
import gguf_roundtrip as rt  # noqa: E402
import test_gguf_roundtrip_normalizer as nt  # noqa: E402


def run(llama_cpp: Path, work: Path) -> list[str]:
    from llama_cpp import Llama
    from tokenizers import Tokenizer
    a, b = work / "a.json", work / "b.json"
    full = nt.RAW_LINES
    nt.RAW_LINES = full[:5]; nt.build_tokenizer(a)   # the checkpoint's own tokenizer
    nt.RAW_LINES = full; nt.build_tokenizer(b)       # the frozen one
    ckpt = work / "ckpt"
    rt.make_tiny_model(a, ckpt, "<|begin_of_text|>", "<|end_of_text|>")
    bad = []
    if json.loads((ckpt / "config.json").read_text())["vocab_size"] < 700:   # table smaller than B's vocabulary: refused
        try:
            cf.convert_frozen(ckpt, b, rt.sha256(b), llama_cpp, work / "small.gguf", work / "w0")
            bad.append("a checkpoint with a too small embedding table was accepted")
        except SystemExit as e:
            bad += [] if "embedding table" in str(e) else [f"too small table: unexpected result {e}"]
    try:
        cf.convert_frozen(ckpt, b, "0" * 64, llama_cpp, work / "no.gguf", work / "w1")
        bad.append("a wrong sha256 was accepted")
    except SystemExit as e:
        if "refusing" not in str(e) or (work / "no.gguf").exists():
            bad.append(f"wrong sha256: unexpected result {e}")
    cfg = json.loads((ckpt / "config.json").read_text()); cfg["vocab_size"] = 700   # room for B (the embedding is not read)
    (ckpt / "config.json").write_text(json.dumps(cfg))
    out = cf.convert_frozen(ckpt, b, rt.sha256(b), llama_cpp, work / "ok.gguf", work / "w2")
    llm = Llama(model_path=str(out), vocab_only=True, verbose=False)
    if llm.metadata.get("tokenizer.ggml.pre") != cf.PRE:
        bad.append(f"pre-tokenizer is {llm.metadata.get('tokenizer.ggml.pre')}")
    ta, tb = Tokenizer.from_file(str(a)), Tokenizer.from_file(str(b))
    lines = [tb.normalizer.normalize_str(x) for x in nt.RAW_LINES + nt.LATIN_CODE]
    tb.normalizer = ta.normalizer = None
    same_b = [llm.tokenize(x.encode(), add_bos=False, special=True) == tb.encode(x, add_special_tokens=False).ids for x in lines]
    diff_a = [ta.encode(x, add_special_tokens=False).ids != tb.encode(x, add_special_tokens=False).ids for x in lines]
    if not all(same_b):
        bad.append(f"{same_b.count(False)} of {len(lines)} lines tokenize differently from the frozen tokenizer")
    if not any(diff_a):
        bad.append("tokenizers A and B cut every line the same: the test cannot tell which one was injected")
    return bad


def test_convert_frozen():   # pytest entry point
    import pytest
    if not os.environ.get("LLAMA_CPP") or not (HERE.parents[1] / "03-tokenizer" / "v1").is_dir():
        pytest.skip("set LLAMA_CPP to a llama.cpp b11669 checkout, run inside the lab repo")
    with tempfile.TemporaryDirectory() as t:
        bad = run(Path(os.environ["LLAMA_CPP"]), Path(t))
    assert not bad, bad


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with tempfile.TemporaryDirectory() as t:
        problems = run(Path(sys.argv[1]), Path(t))
    for p in problems:
        print("FAIL", p)
    print("PASS: wrong sha256 refused; the converter output carries the frozen tokenizer, pre = " + cf.PRE
          if not problems else f"{len(problems)} check(s) failed")
    sys.exit(1 if problems else 0)
