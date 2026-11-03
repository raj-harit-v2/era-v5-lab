#!/usr/bin/env python3
"""GGUF round trip for a tokenizer (G12 week 2, tasks 6 and 9).

Builds a tiny random Llama that carries the tokenizer, converts it to GGUF with llama.cpp's converter, then checks
that llama.cpp tokenizes every test line to the SAME TOKEN IDS as the Hugging Face tokenizer, and decodes them back
to the same text. Gate 2 bar (TSAI, 2 Nov): same ids on every line; a pre-tokenizer that only gives the same decoded
text is not accepted.

    python gguf_roundtrip.py --tokenizer v0/tokenizer.json --name v0 \
        --llama-cpp /path/to/llama.cpp-b11669 --work /tmp/rt --out ../results

Writes <out>/gguf_roundtrip_<name>.md (report) and .json (per-line mismatch indices). Exits 1 if the first --pre
type has any id mismatch or decode error. Downloads its data into --work (~26 MB) and checks every file's sha256.

Why the pre-tokenizer is chosen by hand: llama.cpp does not read the split regex from tokenizer.json. Its converter
hashes the ids of a fixed test string and maps known hashes to built-in regexes; our tokenizer is not in that list,
so conversion stops ("BPE pre-tokenizer was not recognized"). This script sets the type by name (--pre) instead.
`gpt-4o` has our regex but llama.cpp's version leaves out \\p{M}, so Indic vowel signs split off;
`granite-embed-multi-97m` keeps \\p{M} (see docs/unsupported_parts.md, section 4a).

Tokenizer v0 is not in the repo (7.7 MB); build it with teams/03-tokenizer/v0/build_v0.py and check SHA256SUMS.

Versions used: Python 3.12, llama.cpp b11669 (converter + gguf-py), llama-cpp-python 0.3.36, tokenizers 0.22.2,
transformers 4.57.6, torch 2.11.0 (CPU), numpy 2.2.6, sentencepiece 0.2.2, protobuf 4.25.9, gguf 0.19.0
(llama.cpp's gguf-py). Optional --llama-tokenize: the llama-tokenize binary of the same llama.cpp build.
"""
from __future__ import annotations

import argparse, gzip, hashlib, json, os, platform, subprocess, sys, tarfile, time, unicodedata, urllib.request
from pathlib import Path

FLORES = ("https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz",
          "b8b0b76783024b85797e5cc75064eb83fc5288b41e9654dabc7be6ae944011f6")
HUMANEVAL = ("https://raw.githubusercontent.com/openai/human-eval/b9453e8f1865df0a0057a1383767caa400acfbcf/data/HumanEval.jsonl.gz",
             "b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef")
MBPP = ("https://raw.githubusercontent.com/google-research/google-research/83f1e7b59e762648c953de751d31f75720683622/mbpp/sanitized-mbpp.json",
        "ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9")

# Team 3's 12 languages (harness/run_harness.py): every Brahmic script the tokenizer covers, plus English
LANGS = ["eng_Latn", "hin_Deva", "mar_Deva", "ben_Beng", "asm_Beng", "tam_Taml", "tel_Telu", "kan_Knda",
         "mal_Mlym", "guj_Gujr", "pan_Guru", "ory_Orya"]
# not asked for; Latin with diacritics, Greek and Cyrillic test llama.cpp's approximation of the regex's case classes
EXTRA = ["fra_Latn", "deu_Latn", "vie_Latn", "ell_Grek", "rus_Cyrl"]
N = 1000
ZW = ("‌", "‍")   # ZWNJ, ZWJ
DEFAULT_PRE = ["granite-embed-multi-97m", "gpt-4o"]


def sha256(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch(url_sha, work: Path) -> Path:
    url, want = url_sha
    p = work / url.rsplit("/", 1)[1]
    if not p.exists():
        urllib.request.urlretrieve(url, p)
    if sha256(p) != want:
        sys.exit(f"{p}: sha256 {sha256(p)} != pinned {want}")
    return p


def load_sets(work: Path) -> dict[str, dict]:
    """name -> {lines, kind, source}. FLORES: first 1,000 of dev+devtest (2,009). Code: first 1,000 non-blank lines."""
    tar = fetch(FLORES, work)
    root = work / "flores200_dataset"
    if not root.exists():
        with tarfile.open(tar) as t:
            t.extractall(work, members=[m for m in t.getmembers() if m.name.split("/")[-1].split(".")[0] in LANGS + EXTRA],
                         filter="data")

    def flores(lang):
        return [s for sp in ("dev", "devtest")
                for s in (root / sp / f"{lang}.{sp}").read_text(encoding="utf-8").splitlines()]

    sets = {}
    for lang in LANGS + EXTRA:
        sets[lang] = {"lines": flores(lang)[:N], "kind": "extra" if lang in EXTRA else "script",
                      "source": "FLORES-200 dev+devtest, first 1,000"}
    zw = [s for lang in LANGS for s in flores(lang) if any(c in s for c in ZW)]
    sets["zwj_zwnj"] = {"lines": zw, "kind": "script", "source": "every FLORES line (all 2,009, 12 languages) with ZWJ or ZWNJ"}
    sets["nfd_indic"] = {"lines": [unicodedata.normalize("NFD", s) for lang in LANGS[1:] for s in flores(lang)[:100]],
                         "kind": "extra", "source": "first 100 lines of each Indic language, NFD-decomposed"}

    he = [json.loads(l) for l in gzip.open(fetch(HUMANEVAL, work), "rt", encoding="utf-8")]
    mb = json.loads(fetch(MBPP, work).read_text(encoding="utf-8"))
    he_docs = [r["prompt"] + r["canonical_solution"] for r in he]
    sets["code_humaneval"] = {"lines": [s for d in he_docs for s in d.splitlines() if s.strip()][:N], "kind": "code",
                              "source": "HumanEval prompt + solution, first 1,000 non-blank lines (indentation kept)"}
    sets["code_mbpp"] = {"lines": [s for r in mb for s in r["code"].splitlines() if s.strip()][:N], "kind": "code",
                         "source": "MBPP sanitized code, first 1,000 non-blank lines"}
    sets["code_files"] = {"lines": he_docs, "kind": "code",
                          "source": "all 164 HumanEval problems as whole multi-line strings (newlines, indentation runs)"}
    return sets


def make_tiny_model(tok_json: Path, out: Path, bos: str, eos: str) -> int:
    """A 1-layer random Llama whose vocab is the tokenizer's; tokenizer.json is copied byte for byte."""
    import shutil, torch
    from transformers import LlamaConfig, LlamaForCausalLM, PreTrainedTokenizerFast
    t = json.loads(tok_json.read_text(encoding="utf-8"))
    n_vocab = 1 + max(max(t["model"]["vocab"].values()), max(a["id"] for a in t["added_tokens"]))
    tok = PreTrainedTokenizerFast(tokenizer_file=str(tok_json), bos_token=bos, eos_token=eos)
    cfg = LlamaConfig(vocab_size=n_vocab, hidden_size=64, intermediate_size=128, num_hidden_layers=1,
                      num_attention_heads=2, num_key_value_heads=2, max_position_embeddings=2048,
                      bos_token_id=tok.bos_token_id, eos_token_id=tok.eos_token_id)
    torch.manual_seed(0)
    LlamaForCausalLM(cfg).to(torch.bfloat16).save_pretrained(out)
    tok.save_pretrained(out)
    shutil.copyfile(tok_json, out / "tokenizer.json")
    return n_vocab


def convert(llama_cpp: Path, model_dir: Path, pre: str, outfile: Path):
    """Run llama.cpp's converter in a child process with get_vocab_base_pre forced to `pre`."""
    code = ("import sys, runpy; L = sys.argv[1]; sys.path[:0] = [L, L + '/gguf-py']\n"
            "import conversion.base as b; pre = sys.argv[2]\n"
            "b.TextModel.get_vocab_base_pre = lambda self, tokenizer: pre\n"
            "sys.argv = [L + '/convert_hf_to_gguf.py'] + sys.argv[3:]\n"
            "runpy.run_path(sys.argv[0], run_name='__main__')")
    r = subprocess.run([sys.executable, "-c", code, str(llama_cpp), pre, str(model_dir),
                        "--outfile", str(outfile), "--outtype", "f16"], capture_output=True, text=True)
    if r.returncode or not outfile.exists():
        sys.exit(f"conversion with pre={pre} failed:\n{r.stderr[-3000:]}")


def stock_convert_error(llama_cpp: Path, model_dir: Path, work: Path) -> str:
    """What the unmodified converter says about this tokenizer (expected: pre-tokenizer not recognized)."""
    r = subprocess.run([sys.executable, str(llama_cpp / "convert_hf_to_gguf.py"), str(model_dir), "--vocab-only",
                        "--outfile", str(work / "stock.gguf")], capture_output=True, text=True)
    if r.returncode == 0:
        return "converted without error (the tokenizer's hash is in this llama.cpp's list)"
    return r.stderr.strip().splitlines()[-1]


def piece(llm, hf, i, side):
    return (llm.detokenize([i], special=True) if side == "gguf" else hf.decode([i], skip_special_tokens=False).encode()
            ).decode("utf-8", "backslashreplace")


def cli_check(binary: Path, gguf: Path, hf, sets: dict, work: Path) -> dict:
    """The llama.cpp build's own llama-tokenize on each set joined into one text: same ids as HF?
    llama-cpp-python ships its own copy of llama.cpp, so this checks that the result holds for the converter's build."""
    out = {}
    for name, s in sets.items():
        text = "\n".join(s["lines"])
        f = work / f"cli_{name}.txt"
        f.write_bytes(text.encode("utf-8"))
        r = subprocess.run([str(binary), "-m", str(gguf), "-f", str(f), "--ids", "--no-bos", "--no-escape",
                            "--log-disable"], capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"llama-tokenize failed on {name}:\n{r.stderr[-2000:]}")
        out[name] = json.loads(r.stdout.strip().splitlines()[-1]) == hf.encode(text, add_special_tokens=False).ids
    return out


def check(gguf: Path, hf, tok: dict, sets: dict) -> dict:
    from llama_cpp import Llama
    m = Llama(model_path=str(gguf), n_ctx=64, n_gpu_layers=0, verbose=False)   # the converted model runs
    generated = m.create_completion("भारत एक देश है", max_tokens=2, temperature=0)
    del m
    llm = Llama(model_path=str(gguf), vocab_only=True, verbose=False)
    res = {"pre": llm.metadata.get("tokenizer.ggml.pre"), "n_vocab": llm.n_vocab(),
           "bos": llm.token_bos(), "eos": llm.token_eos(), "generates": bool(generated["choices"]), "sets": {}}
    for name, s in sets.items():
        t0, r = time.time(), {"lines": len(s["lines"]), "id_mismatch": [], "gguf_text_err": [], "hf_text_err": [],
                              "tok_hf": 0, "tok_gguf": 0, "examples": []}
        for k, x in enumerate(s["lines"]):
            # special=True on both sides: HF always parses special-token strings inside text
            g = llm.tokenize(x.encode("utf-8"), add_bos=False, special=True)
            h = hf.encode(x, add_special_tokens=False).ids
            r["tok_hf"] += len(h); r["tok_gguf"] += len(g)
            if llm.detokenize(g, special=True) != x.encode("utf-8"):
                r["gguf_text_err"].append(k)
            if hf.decode(h, skip_special_tokens=False) != x:
                r["hf_text_err"].append(k)
            if g != h:
                r["id_mismatch"].append(k)
                if len(r["examples"]) < 2:
                    j = next(i for i, (a, b) in enumerate(zip(g + [-1], h + [-1])) if a != b)
                    lo = max(0, j - 2)
                    r["examples"].append({"line": k, "at_token": j,
                                          "hf": [piece(llm, hf, i, "hf") for i in h[lo:j + 4]],
                                          "gguf": [piece(llm, hf, i, "gguf") for i in g[lo:j + 4]]})
        r["seconds"] = round(time.time() - t0, 2)
        res["sets"][name] = r
    bad = []
    for a in tok["added_tokens"]:
        g = llm.tokenize(a["content"].encode("utf-8"), add_bos=False, special=True)
        if g != [a["id"]] or llm.detokenize(g, special=True) != a["content"].encode("utf-8"):
            bad.append({"id": a["id"], "content": a["content"], "gguf": g})
    res["specials"] = {"n": len(tok["added_tokens"]), "bad": bad}
    return res


def report(args, info, sets, results) -> str:
    first = results[args.pre[0]]
    L = [f"# GGUF round trip: tokenizer {args.name}", "",
         f"Generated by `tokenizer/gguf_roundtrip.py` on {info['date']} ({info['machine']}). Do not edit by hand; rerun the script.", "",
         "**Question.** Does llama.cpp, after GGUF conversion, cut text into the **same token ids** as the Hugging Face "
         "tokenizer the model is trained with? Gate 2 bar (TSAI, 2 Nov): same ids on every line; same decoded text alone "
         "is not enough.", "",
         "**Pass per line:** (1) GGUF ids == HF `tokenizers` ids; (2) GGUF detokenize(ids) == the original bytes. "
         "Special-token strings are parsed on both sides, as HF does by default. Checked with llama-cpp-python, line by line. "
         "The `llama-tokenize` column repeats the check with the llama.cpp build's own binary, on each set joined into "
         "one text with newlines.", "",
         "## Result", ""]
    for pre in args.pre:
        r = results[pre]
        ids = sum(len(s["id_mismatch"]) for s in r["sets"].values())
        txt = sum(len(s["gguf_text_err"]) for s in r["sets"].values())
        n = sum(s["lines"] for s in r["sets"].values())
        L.append(f"- **`{pre}`**: {ids:,} of {n:,} lines with different ids, {txt:,} decode errors; "
                 f"specials {r['specials']['n'] - len(r['specials']['bad'])}/{r['specials']['n']} exact."
                 + (" **PASS**" if ids == txt == 0 and not r["specials"]["bad"] else " **FAIL**"))
    L += ["", f"The stock converter (no `--pre` override) says: `{info['stock_error']}`", ""]
    ok = [p for p in args.pre if not any(s["id_mismatch"] or s["gguf_text_err"] for s in results[p]["sets"].values())
          and not results[p]["specials"]["bad"]]
    trap = [p for p in args.pre if p not in ok and not any(s["gguf_text_err"] for s in results[p]["sets"].values())]
    L.append("**What it means.** " + (
        f"Convert models that use this tokenizer with pre-tokenizer `{ok[0]}`; until llama.cpp knows this tokenizer's "
        f"hash, the converter must be told the type, as this script does. " if ok else
        "**No tested llama.cpp pre-tokenizer gives the same ids: blocker for G3 and G12** (mismatches per language "
        "below). ") + (
        " ".join(f"`{p}` decodes every line back to the same text, but cuts "
                 f"{sum(len(s['id_mismatch']) for s in results[p]['sets'].values()):,} lines into different tokens."
                 for p in trap) + " A check of decoded text alone would pass it; the model would see ids it was not "
        "trained on." if trap else ""))
    L.append("")
    for pre in args.pre:
        r = results[pre]
        L += [f"## Per set, pre-tokenizer `{pre}`", "",
              f"GGUF metadata: `tokenizer.ggml.pre` = `{r['pre']}`, n_vocab {r['n_vocab']:,}, bos {r['bos']}, eos {r['eos']}. "
              f"The full GGUF loads and generates: {'yes' if r['generates'] else 'NO'}.", "",
              "| Set | Kind | Lines | Different ids | GGUF decode errors | HF decode errors | Tokens HF | Tokens GGUF | Δ tokens | llama-tokenize |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for name, s in r["sets"].items():
            d = (s["tok_gguf"] / s["tok_hf"] - 1) * 100 if s["tok_hf"] else 0
            L.append(f"| {name} | {sets[name]['kind']} | {s['lines']:,} | {len(s['id_mismatch']):,} | {len(s['gguf_text_err']):,} | "
                     f"{len(s['hf_text_err']):,} | {s['tok_hf']:,} | {s['tok_gguf']:,} | {d:+.1f}% | "
                     f"{ {True: 'same', False: '**differs**', None: 'not run'}[r['cli'].get(name)] } |")
        ex = [(n, e) for n, s in r["sets"].items() for e in s["examples"][:1]]
        if ex:
            L += ["", "First differing tokens (pieces around the first difference, one line per set):", "",
                  "| Set | Line | HF pieces | GGUF pieces |", "|---|---|---|---|"]
            for n, e in ex:
                f = lambda ps: " · ".join(f"`{p}`" for p in ps).replace("|", "\\|")
                L.append(f"| {n} | {e['line']} | {f(e['hf'])} | {f(e['gguf'])} |")
        if r["specials"]["bad"]:
            L += ["", f"Specials that fail: {json.dumps(r['specials']['bad'][:10], ensure_ascii=False)}"]
        L.append("")
    L += ["## Sets", "", "| Set | Source |", "|---|---|"]
    L += [f"| {n} | {s['source']} |" for n, s in sets.items()]
    L += ["", "Kinds: `script` = what the task asks (each script the tokenizer covers, and code); `extra` = harder input "
          "outside the task (other Latin, Greek, Cyrillic, NFD). Text is not committed; the sources below are pinned by "
          "sha256. FLORES-200 is CC-BY-SA 4.0 (NLLB Team et al., 2022).", "",
          "## Inputs and outputs (sha256)", "", "| What | sha256 |", "|---|---|"]
    L += [f"| {k} | `{v}` |" for k, v in info["sha256"].items()]
    L += ["", "Versions: " + ", ".join(f"{k} {v}" for k, v in info["versions"].items()) + ".", "",
          "Rerun: `python tokenizer/gguf_roundtrip.py --tokenizer <tokenizer.json> --name " + args.name +
          " --llama-cpp <llama.cpp b11669> --llama-tokenize <its llama-tokenize> --work <tmp> --out results`", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tokenizer", type=Path, required=True, help="tokenizer.json")
    ap.add_argument("--name", required=True, help="label for the report, e.g. v0 or frozen")
    ap.add_argument("--llama-cpp", type=Path, required=True, help="llama.cpp checkout (b11669): converter + gguf-py")
    ap.add_argument("--work", type=Path, required=True, help="scratch folder: data, tiny model, GGUF files")
    ap.add_argument("--out", type=Path, required=True, help="folder for the .md and .json report")
    ap.add_argument("--pre", action="append", help=f"llama.cpp pre-tokenizer type(s); the first decides the exit code "
                    f"(default: {' '.join(DEFAULT_PRE)})")
    ap.add_argument("--llama-tokenize", type=Path, help="llama-tokenize binary of the same llama.cpp build (optional)")
    ap.add_argument("--bos", default="<|begin_of_text|>")
    ap.add_argument("--eos", default="<|end_of_text|>")
    args = ap.parse_args()
    args.pre = args.pre or DEFAULT_PRE
    args.work.mkdir(parents=True, exist_ok=True); args.out.mkdir(parents=True, exist_ok=True)

    import llama_cpp, tokenizers, torch, transformers
    from tokenizers import Tokenizer
    sets = load_sets(args.work)
    model_dir = args.work / f"tiny_{args.name}"
    n_vocab = make_tiny_model(args.tokenizer, model_dir, args.bos, args.eos)
    info = {"date": time.strftime("%Y-%m-%d"), "machine": f"{platform.machine()} {platform.system()}, CPU",
            "stock_error": stock_convert_error(args.llama_cpp, model_dir, args.work),
            "sha256": {f"tokenizer.json ({args.name})": sha256(args.tokenizer),
                       "FLORES-200 tarball": FLORES[1], "HumanEval.jsonl.gz": HUMANEVAL[1], "sanitized-mbpp.json": MBPP[1],
                       "llama.cpp convert_hf_to_gguf.py": sha256(args.llama_cpp / "convert_hf_to_gguf.py"),
                       "llama.cpp conversion/base.py": sha256(args.llama_cpp / "conversion" / "base.py")},
            "versions": {"Python": platform.python_version(), "llama-cpp-python": llama_cpp.__version__,
                         "tokenizers": tokenizers.__version__, "transformers": transformers.__version__,
                         "torch": torch.__version__},
            "tiny_model": f"Llama, 1 layer, hidden 64, vocab {n_vocab:,}, random weights (seed 0), f16 GGUF"}
    tok = json.loads(args.tokenizer.read_text(encoding="utf-8"))
    hf = Tokenizer.from_file(str(args.tokenizer))
    results = {}
    for pre in args.pre:
        gguf = args.work / f"tiny_{args.name}_{pre}.gguf"
        convert(args.llama_cpp, model_dir, pre, gguf)
        info["sha256"][f"GGUF ({pre}), not committed"] = sha256(gguf)
        results[pre] = r = check(gguf, hf, tok, sets)
        r["cli"] = cli_check(args.llama_tokenize, gguf, hf, sets, args.work) if args.llama_tokenize else {}
        print(f"{pre}: {sum(len(s['id_mismatch']) for s in r['sets'].values())} lines with different ids, "
              f"{sum(len(s['gguf_text_err']) for s in r['sets'].values())} decode errors, "
              f"{len(r['specials']['bad'])} bad specials")
    md = args.out / f"gguf_roundtrip_{args.name}.md"
    md.write_text(report(args, info, sets, results), encoding="utf-8")
    slim = {pre: {k: v for k, v in r.items() if k != "sets"} | {"sets": {n: {k: s[k] for k in
            ("lines", "id_mismatch", "gguf_text_err", "hf_text_err", "tok_hf", "tok_gguf")} for n, s in r["sets"].items()}}
            for pre, r in results.items()}
    (args.out / f"gguf_roundtrip_{args.name}.json").write_text(
        json.dumps({"info": info, "results": slim}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {md}")
    r = results[args.pre[0]]
    ok = (not r["specials"]["bad"] and r["generates"] and all(r["cli"].values())
          and all(not s["id_mismatch"] and not s["gguf_text_err"] for s in r["sets"].values()))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
