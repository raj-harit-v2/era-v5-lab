#!/usr/bin/env python3
"""
run_harness.py
==============

One benchmark for every tokenizer the team compares. It measures:

  flores  FLORES-200 dev+devtest fertility (tokens / whitespace word) on the 11
          Brahmic languages and English. Same method as the reference script
          BrahmicTokenizer-131K/evaluate_fertility_flores.py, so the numbers
          diff 1:1 against reference_outputs/evaluate_fertility_flores.json.
  code    tokens / char on HumanEval (prompt + canonical_solution), MBPP-sanitized
          test (code) and GSM8K train (question + "\\n" + answer). Same corpora as
          BrahmicTokenizer-131K/evaluate_code_math.py.

  in22    IN22-Gen fertility (tokens / whitespace word), same method as flores and as
          BrahmicTokenizer-131K/evaluate_fertility_in22.py. Needs the gated
          ai4bharat/IN22-Gen parquet (--in22-parquet, or the Hugging Face cache).
  heldout fertility on the held-out text of the tokenizer sample, one row per pack
          (tokens / char and tokens / word). Needs --heldout-dir.
  roundtrip  decode(encode(text)) must equal the tokenizer's own normalisation of
          the text, on up to N documents per pack (default 1,000) of the held-out
          text. Local tokenizer.json files only (the baseline and --candidate).

Pass bar (Week plan): a candidate beats BrahmicTokenizer-131K on mean Indic
fertility and is at most 2% worse on English fertility, HumanEval and MBPP.
The in22, heldout and roundtrip suites are reported next to it; they do not change it.

Usage
-----
    # Gate 1: the baseline matches the committed reference within 0.001
    python run_harness.py --tokenizers BrahmicTokenizer-131K \\
        --brahmic-dir /path/to/BrahmicTokenizer-131K --check-reference

    # Full comparator table
    python run_harness.py --tokenizers all --suites flores,code --out results.json --md results.md

    # A candidate from train_bpe.py, judged against the pass bar
    python run_harness.py --tokenizers BrahmicTokenizer-131K,o200k_base \\
        --candidate mine=/path/to/tokenizer.json --suites flores,code

    # Held-out text and the round-trip check on a candidate
    python run_harness.py --tokenizers BrahmicTokenizer-131K --candidate c3=/path/to/tokenizer.json \\
        --suites heldout,roundtrip --heldout-dir /path/to/sample/heldout

Data: FLORES-200 under --flores-dir (see baseline/reproduce.md for the
download). The code suite downloads public datasets through `datasets`.
The held-out text is lab data: keep it on your machine, never on a public site.
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

LANGS = [
    ("eng_Latn", "En"), ("hin_Deva", "Hi"), ("ben_Beng", "Bn"), ("tam_Taml", "Ta"),
    ("tel_Telu", "Te"), ("kan_Knda", "Kn"), ("mal_Mlym", "Ml"), ("mar_Deva", "Mr"),
    ("guj_Gujr", "Gu"), ("pan_Guru", "Pa"), ("ory_Orya", "Or"), ("asm_Beng", "As"),
]
INDIC = [lbl for _, lbl in LANGS if lbl != "En"]
CODE_CORPORA = ["HumanEval", "MBPP", "GSM8K"]

BASELINE = "BrahmicTokenizer-131K"
PASS_MARGIN = 0.02                       # at most 2% worse
GUARDED = [("flores", "En"), ("code", "HumanEval"), ("code", "MBPP")]
REFERENCE_TOL = 0.001

# name -> (kind, source, pinned revision). Revisions pinned 27 Oct 2026 so a
# re-run months later measures the same tokenizer files.
REGISTRY = {
    BASELINE:          ("brahmic",  "tokenizer.json", None),
    "o200k_base":      ("tiktoken", "o200k_base", None),
    "Gemma-4":         ("hf", "google/gemma-4-E4B",                 "411aa17b749aa952df1359d2dcea73917a544d9a"),
    "Qwen3.8":         ("hf", "Qwen/Qwen3.8-27B",                   "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"),
    "Qwen3-8B":        ("hf", "Qwen/Qwen3-8B",                      "b968826d9c46dd6066d109eabc6255188de91218"),
    "DeepSeek-V4":     ("hf", "deepseek-ai/DeepSeek-V4-Flash-Base", "8855555deef230a27a21a8d6f294b7b7497759b6"),
    "Sarvam-30B":      ("hf", "sarvamai/sarvam-30b",                "071ae95e933605ca1104a6b4524a36a98488efa4"),
    "Sarvam-m":        ("hf", "sarvamai/sarvam-m",                  "01534a53c46f2788e392dbb3d994e0fa8f04d3fd"),
    "Sarvam-1":        ("hf", "sarvamai/sarvam-1",                  "e9607337286ddf496d4a2562b194e489dcf3feea"),
}


def make_encoder(kind, src, rev):
    if kind == "local":
        from tokenizers import Tokenizer
        t = Tokenizer.from_file(src)
        return lambda s: t.encode(s).ids
    if kind == "tiktoken":
        import tiktoken
        e = tiktoken.get_encoding(src)
        return lambda s: e.encode(s, disallowed_special=())
    if kind == "hf":
        from transformers import AutoTokenizer
        # trust_remote_code stays off: every registry entry loads without it.
        t = AutoTokenizer.from_pretrained(src, revision=rev, trust_remote_code=False)
        return lambda s: t.encode(s, add_special_tokens=False)
    raise ValueError(kind)


def load_flores(flores_dir):
    root = Path(flores_dir)
    if not (root / "dev").is_dir() or not (root / "devtest").is_dir():
        sys.exit(f"ERROR: {root}/dev and {root}/devtest must exist. See baseline/reproduce.md.")
    texts = {}
    for code, lbl in LANGS:
        lines = ((root / "dev" / f"{code}.dev").read_text(encoding="utf-8").splitlines()
                 + (root / "devtest" / f"{code}.devtest").read_text(encoding="utf-8").splitlines())
        texts[lbl] = [line for line in lines if line.strip()]
    return texts


def load_code():
    from datasets import load_dataset
    he = load_dataset("openai/openai_humaneval", split="test")
    mbpp = load_dataset("google-research-datasets/mbpp", "sanitized", split="test")
    gsm = load_dataset("openai/gsm8k", "main", split="train")
    return {
        "HumanEval": [r["prompt"] + r["canonical_solution"] for r in he],
        "MBPP": [r["code"] for r in mbpp if r["code"]],
        "GSM8K": [r["question"] + "\n" + r["answer"] for r in gsm],
    }


def run_flores(enc, texts):
    row = {}
    for lbl, lines in texts.items():
        tok = sum(len(enc(line)) for line in lines)
        words = sum(len(line.split()) for line in lines)
        row[lbl] = round(tok / max(words, 1), 4)
    have = [lbl for lbl in INDIC if lbl in row]          # a suite may lack a language (IN22)
    row["Mean"] = round(sum(row[lbl] for lbl in have) / len(have), 4)
    return row


def find_in22_parquet():
    hits = sorted(glob.glob(os.path.expanduser(
        "~/.cache/huggingface/hub/datasets--ai4bharat--IN22-Gen/snapshots/*/data/*.parquet")))
    if not hits:
        sys.exit("ERROR: IN22-Gen is gated on Hugging Face and is not cached. Accept the terms at "
                 "https://huggingface.co/datasets/ai4bharat/IN22-Gen, log in, and load it once, "
                 "or pass --in22-parquet PATH.")
    return hits[0]


def load_in22(path):
    """IN22-Gen is one wide parquet: one column per FLORES language code, one row per sentence."""
    import pyarrow.parquet as pq
    table = pq.read_table(path or find_in22_parquet())
    texts = {}
    for code, lbl in LANGS:
        if code in table.column_names:
            texts[lbl] = [s for s in table[code].to_pylist() if isinstance(s, str) and s.strip()]
        else:
            print(f"  IN22: {lbl} ({code}) is missing, skipped", flush=True)
    if not texts:
        sys.exit("ERROR: no FLORES language columns found in the IN22 parquet.")
    return texts


def load_heldout(root):
    """Held-out parquet files of the tokenizer sample -> {pack: [(doc_id, text), ...]}.

    Columns used: text (required), doc_id and pack_id (optional; the pack falls back
    to the name of the parent folder).
    """
    import pyarrow.parquet as pq
    files = sorted(glob.glob(str(Path(root) / "**" / "*.parquet"), recursive=True))
    if not files:
        sys.exit(f"ERROR: no .parquet files under {root}. Pass --heldout-dir (the sample's heldout/ folder).")
    packs = {}
    for f in files:
        t = pq.read_table(f)
        if "text" not in t.column_names:
            sys.exit(f"ERROR: {f} has no 'text' column (columns: {t.column_names}).")
        texts = t["text"].to_pylist()
        ids = t["doc_id"].to_pylist() if "doc_id" in t.column_names else [f"{Path(f).name}:{i}" for i in range(len(texts))]
        pk = t["pack_id"].to_pylist() if "pack_id" in t.column_names else [Path(f).parent.name] * len(texts)
        for d, p, x in zip(ids, pk, texts):
            if isinstance(x, str) and x.strip():
                packs.setdefault(p, []).append((d, x))
    return packs


def run_heldout(enc, packs):
    row = {}
    for pack, docs in sorted(packs.items()):
        tok = sum(len(enc(x)) for _, x in docs)
        chars = sum(len(x) for _, x in docs)
        words = sum(len(x.split()) for _, x in docs)
        row[pack] = {"docs": len(docs), "tok_per_char": round(tok / max(chars, 1), 4),
                     "tok_per_word": round(tok / max(words, 1), 4)}
    return row


def sample_docs(docs, n):
    """The first n documents by sha256(doc_id): the same documents on every run and machine."""
    return sorted(docs, key=lambda d: hashlib.sha256(str(d[0]).encode()).hexdigest())[:n]


def run_roundtrip(path, packs, n):
    """decode(encode(text)) must equal the tokenizer's own normalisation of the text.

    A candidate with a normalizer (v1: NFC + chillu + nukta re-join) changes some texts on
    purpose, so the expected string is normalizer(text), not text. `normalised` counts
    how many documents the normalizer changed. Only offsets are reported for a failure,
    never the text: the held-out text is lab data.
    """
    from tokenizers import Tokenizer
    t = Tokenizer.from_file(path)
    norm = t.normalizer.normalize_str if t.normalizer is not None else (lambda s: s)
    out = {}
    for pack, docs in sorted(packs.items()):
        sample = sample_docs(docs, n)
        fails, changed = [], 0
        for doc_id, text in sample:
            expect = norm(text)
            changed += expect != text
            got = t.decode(t.encode(text, add_special_tokens=False).ids, skip_special_tokens=False)
            if got != expect:
                pos = next((i for i, (a, b) in enumerate(zip(got, expect)) if a != b), min(len(got), len(expect)))
                fails.append({"doc_id": doc_id, "offset": pos})
        out[pack] = {"docs": len(sample), "failures": len(fails), "normalised": changed,
                     "first_failures": fails[:5]}
    return out


def run_code(enc, corpora):
    row = {}
    for name, texts in corpora.items():
        tok = sum(len(enc(s)) for s in texts)
        chars = sum(len(s) for s in texts)
        row[name] = round(tok / max(chars, 1), 4)
    return row


def check_reference(results, reference_path):
    """Gate 1: every FLORES column of the baseline within REFERENCE_TOL of the reference."""
    ref = json.loads(Path(reference_path).read_text())[BASELINE]
    got = results[BASELINE]["flores"]
    worst = 0.0
    print(f"\nReference check vs {reference_path} (tolerance {REFERENCE_TOL})")
    for k in [lbl for _, lbl in LANGS] + ["Mean"]:
        d = abs(got[k] - ref[k])
        worst = max(worst, d)
        print(f"  {k:<4} got={got[k]:.4f} ref={ref[k]:.4f} |d|={d:.4f}")
    ok = worst <= REFERENCE_TOL
    print(f"  max |d| = {worst:.4f} -> {'PASS' if ok else 'FAIL'}")
    return ok


def pass_bar(results, name):
    """Candidate vs baseline: lower mean Indic, and <=2% worse on En / HumanEval / MBPP."""
    base, cand = results[BASELINE], results[name]
    checks = [("Indic mean fertility", cand["flores"]["Mean"], base["flores"]["Mean"],
               cand["flores"]["Mean"] < base["flores"]["Mean"])]
    for suite, key in GUARDED:
        if suite in cand and suite in base:
            limit = base[suite][key] * (1 + PASS_MARGIN)
            checks.append((f"{key} ({suite})", cand[suite][key], base[suite][key], cand[suite][key] <= limit))
    print(f"\nPass bar: {name} vs {BASELINE}")
    for label, c, b, ok in checks:
        print(f"  {label:<22} {c:.4f} vs {b:.4f} ({(c / b - 1) * 100:+.2f}%)  {'PASS' if ok else 'FAIL'}")
    ok = all(c[3] for c in checks)
    print(f"  -> {'PASS' if ok else 'FAIL'}")
    return ok


def to_markdown(results):
    out = []
    names = list(results)
    if any("flores" in r for r in results.values()):
        cols = [lbl for _, lbl in LANGS] + ["Mean"]
        out += ["## FLORES-200 fertility (tokens / word, lower is better; Mean = 11 Indic)", "",
                "| Tokenizer | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
        for n in names:
            if "flores" in results[n]:
                out.append(f"| {n} | " + " | ".join(f"{results[n]['flores'][c]:.4f}" for c in cols) + " |")
        out.append("")
    if any("in22" in r for r in results.values()):
        cols = [lbl for _, lbl in LANGS] + ["Mean"]
        out += ["## IN22-Gen fertility (tokens / word, lower is better; Mean = Indic languages present)", "",
                "| Tokenizer | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
        for n in names:
            if "in22" in results[n]:
                out.append(f"| {n} | " + " | ".join(f"{results[n]['in22'].get(c, float('nan')):.4f}" for c in cols) + " |")
        out.append("")
    if any("heldout" in r for r in results.values()):
        packs = sorted({p for r in results.values() for p in r.get("heldout", {})})
        out += ["## Held-out text (tokens / char, lower is better; docs in brackets)", "",
                "| Pack | docs | " + " | ".join(n for n in names if "heldout" in results[n]) + " |",
                "|---" * (2 + sum("heldout" in results[n] for n in names)) + "|"]
        for p in packs:
            cells = [f"{results[n]['heldout'][p]['tok_per_char']:.4f}" if p in results[n].get("heldout", {}) else "-"
                     for n in names if "heldout" in results[n]]
            docs = next(results[n]["heldout"][p]["docs"] for n in names if p in results[n].get("heldout", {}))
            out.append(f"| {p} | {docs} | " + " | ".join(cells) + " |")
        out.append("")
    if any("roundtrip" in r for r in results.values()):
        out += ["## Round trip: decode(encode(text)) == normalizer(text)", "",
                "| Tokenizer | packs | docs checked | failures | docs changed by the normalizer |", "|---|---|---|---|---|"]
        for n in names:
            if "roundtrip" in results[n]:
                rt = results[n]["roundtrip"]
                out.append(f"| {n} | {len(rt)} | {sum(v['docs'] for v in rt.values())} | "
                           f"{sum(v['failures'] for v in rt.values())} | {sum(v['normalised'] for v in rt.values())} |")
        out.append("")
    if any("code" in r for r in results.values()):
        out += ["## Code and math (tokens / char, lower is better)", "",
                "| Tokenizer | " + " | ".join(CODE_CORPORA) + " |", "|---" * (len(CODE_CORPORA) + 1) + "|"]
        for n in names:
            if "code" in results[n]:
                out.append(f"| {n} | " + " | ".join(f"{results[n]['code'][c]:.4f}" for c in CODE_CORPORA) + " |")
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tokenizers", default="all", help=f'"all" or comma list of {list(REGISTRY)}')
    ap.add_argument("--candidate", action="append", default=[], metavar="NAME=PATH",
                    help="a local tokenizer.json to evaluate and judge against the pass bar (repeatable)")
    ap.add_argument("--suites", default="flores", help='comma list of "flores", "code", "in22", "heldout", "roundtrip"')
    ap.add_argument("--in22-parquet", help="IN22-Gen parquet (default: the Hugging Face cache)")
    ap.add_argument("--heldout-dir", help="folder with the held-out parquet files of the tokenizer sample")
    ap.add_argument("--roundtrip-docs", type=int, default=1000, help="documents per pack for the round trip (default 1000)")
    ap.add_argument("--brahmic-dir", default="../BrahmicTokenizer-131K",
                    help="clone of github.com/theschoolofai/BrahmicTokenizer-131K")
    ap.add_argument("--flores-dir", default="/tmp/flores200_dataset")
    ap.add_argument("--check-reference", action="store_true",
                    help=f"exit 1 unless {BASELINE} FLORES fertility is within {REFERENCE_TOL} of the reference")
    ap.add_argument("--out", help="write results JSON here")
    ap.add_argument("--md", help="write a markdown table here")
    args = ap.parse_args()

    brahmic_dir = Path(args.brahmic_dir)
    names = list(REGISTRY) if args.tokenizers == "all" else [s.strip() for s in args.tokenizers.split(",") if s.strip()]
    bad = [n for n in names if n not in REGISTRY]
    if bad:
        sys.exit(f"ERROR: unknown tokenizers {bad}. Available: {list(REGISTRY)}")
    jobs = []
    for n in names:
        kind, src, rev = REGISTRY[n]
        if kind == "brahmic":
            kind, src = "local", str(brahmic_dir / src)
        jobs.append((n, kind, src, rev))
    candidates = []
    for spec in args.candidate:
        n, _, p = spec.partition("=")
        if not p:
            sys.exit(f"ERROR: --candidate expects NAME=PATH, got {spec!r}")
        jobs.append((n, "local", p, None))
        candidates.append(n)
    if (args.check_reference or candidates) and BASELINE not in names:
        sys.exit(f"ERROR: --check-reference and --candidate need {BASELINE} in --tokenizers.")

    suites = [s.strip() for s in args.suites.split(",")]
    data = {}
    if "flores" in suites:
        data["flores"] = load_flores(args.flores_dir)
    if "code" in suites:
        data["code"] = load_code()
    if "in22" in suites:
        data["in22"] = load_in22(args.in22_parquet)
    if {"heldout", "roundtrip"} & set(suites):
        if not args.heldout_dir:
            sys.exit("ERROR: the heldout and roundtrip suites need --heldout-dir.")
        data["packs"] = load_heldout(args.heldout_dir)
    unknown = set(suites) - {"flores", "code", "in22", "heldout", "roundtrip"}
    if unknown:
        sys.exit(f"ERROR: unknown suites {sorted(unknown)}.")

    results = {}
    for n, kind, src, rev in jobs:
        t0 = time.time()
        try:
            enc = make_encoder(kind, src, rev)
        except Exception as e:  # one gated or missing tokenizer must not stop the table
            print(f"=== {n}: LOAD FAIL {type(e).__name__}: {e}", flush=True)
            continue
        r = {"source": src, "revision": rev}
        if "flores" in data:
            r["flores"] = run_flores(enc, data["flores"])
        if "code" in data:
            r["code"] = run_code(enc, data["code"])
        if "in22" in data:
            r["in22"] = run_flores(enc, data["in22"])
        if "heldout" in suites:
            r["heldout"] = run_heldout(enc, data["packs"])
        if "roundtrip" in suites:
            if kind == "local":
                r["roundtrip"] = run_roundtrip(src, data["packs"], args.roundtrip_docs)
            else:
                print(f"    {n}: roundtrip skipped (local tokenizer.json files only)", flush=True)
        results[n] = r
        summary = []
        if "flores" in r:
            summary.append(f"Indic mean={r['flores']['Mean']:.4f} En={r['flores']['En']:.4f}")
        if "code" in r:
            summary.append(" ".join(f"{k}={v:.4f}" for k, v in r["code"].items()))
        if "in22" in r:
            summary.append(f"IN22 Indic mean={r['in22']['Mean']:.4f}")
        if "heldout" in r:
            summary.append(f"heldout packs={len(r['heldout'])}")
        if "roundtrip" in r:
            rt = r["roundtrip"]
            summary.append(f"roundtrip docs={sum(v['docs'] for v in rt.values())} "
                           f"failures={sum(v['failures'] for v in rt.values())}")
        print(f"=== {n}: {'  '.join(summary)}  ({time.time() - t0:.1f}s)", flush=True)

    ok = True
    if args.check_reference:
        ok &= check_reference(results, brahmic_dir / "reference_outputs" / "evaluate_fertility_flores.json")
    for n in candidates:
        if n in results and "flores" in results[n] and "flores" in results.get(BASELINE, {}):
            ok &= pass_bar(results, n)
        elif n in results:
            print(f"\nPass bar for {n}: skipped (needs the flores suite on {BASELINE} and on {n})")
    for n, r in results.items():
        if "roundtrip" in r:
            bad_packs = {p: v for p, v in r["roundtrip"].items() if v["failures"]}
            print(f"\nRound trip {n}: {sum(v['docs'] for v in r['roundtrip'].values())} docs in "
                  f"{len(r['roundtrip'])} packs, {sum(v['failures'] for v in bad_packs.values())} failures "
                  f"-> {'FAIL' if bad_packs else 'PASS'}")
            for p, v in bad_packs.items():
                print(f"  {p}: {v['failures']} of {v['docs']}; first {v['first_failures']}")
            ok &= not bad_packs

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2, ensure_ascii=False))
        print(f"wrote {args.out}")
    if args.md:
        Path(args.md).write_text(to_markdown(results))
        print(f"wrote {args.md}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
