#!/usr/bin/env python3
"""GGUF round trip for a tokenizer (G12 week 2, tasks 6 and 9).

Builds a tiny random Llama that carries the tokenizer, converts it to GGUF with llama.cpp's converter, then checks
that llama.cpp tokenizes every test line to the SAME TOKEN IDS as the Hugging Face tokenizer, and decodes them back
to the same text. Gate 2 bar (TSAI, 2 Nov): same ids on every line; a pre-tokenizer that only gives the same decoded
text is not accepted.

    python gguf_roundtrip.py --tokenizer v0/tokenizer.json --name v0 \
        --llama-cpp /path/to/llama.cpp-b11669 --work /tmp/rt --out ../results

Writes <out>/gguf_roundtrip_<name>.md (report) and .json (per-line mismatch indices). The reports hold counts, line
indices, token ids and hashes only, never line text.

Test text (TSAI, 10 Nov: no benchmark text): Team 3's held-out sources, streamed from Hugging Face at pinned dataset
commits into --work (about 2 minutes, 10-20 MB; needs network and the `datasets` package): the FineWeb-2 `test` split of
12 languages and 5 others, FineWeb for English, codeparrot-clean-valid for Python. Derived from it: lines with ZWNJ / ZWJ
inserted, NFD lines, Malayalam old-style chillu. Delete --work afterwards to remove all of it. A second run with the same
--work reads the cache.

Exit code (decided by the first --pre type): 0 = same ids on every line; 1 = anything else; 2 = only with
--normalize-first, see below.

--normalize-first is for a tokenizer.json that has a normalizer (tokenizer v1 idea 2: NFC, Malayalam chillu, Bengali /
Punjabi nukta). The GGUF format has no normalizer, so llama.cpp tokenizes the text as it is. Two passes are run:
  raw         text as it is; HF applies its normalizer, llama.cpp does not. Lines the normalizer changes may differ.
  normalized  llama.cpp on normalizer(text) against HF on the SAME normalized text (HF without its normalizer). This
              must match on every line; if it does, the dropped normalizer is the only cause of the raw differences.
It also checks that normalize-then-tokenize equals HF's own pipeline on every line. Exit 2 = the raw pass has
differences, all on lines the normalizer changes, and the normalized pass is clean: the serving app must normalize
before llama.cpp. Without a normalizer the two passes are identical (the script measures this, it does not assume it).

Why the pre-tokenizer is chosen by hand: llama.cpp does not read the split regex from tokenizer.json. Its converter
hashes the ids of a fixed test string and maps known hashes to built-in regexes; our tokenizer is not in that list,
so conversion stops ("BPE pre-tokenizer was not recognized"). This script sets the type by name (--pre) instead.
`gpt-4o` has our regex but llama.cpp's version leaves out \\p{M}, so Indic vowel signs split off;
`granite-embed-multi-97m` keeps \\p{M} (see docs/unsupported_parts.md, section 4a).

Tokenizer v0 is not in the repo (7.7 MB); build it with teams/03-tokenizer/v0/build_v0.py and check SHA256SUMS.

Versions used: Python 3.12, llama.cpp b11669 (converter + gguf-py), llama-cpp-python 0.3.36, tokenizers 0.22.2,
transformers 4.57.6, torch 2.11.0 (CPU), numpy 2.2.6, sentencepiece 0.2.2, protobuf 4.25.9, gguf 0.19.0, datasets 4.8.5,
regex 2026.11.9 (optional, for the cause analysis)
(llama.cpp's gguf-py). Optional --llama-tokenize: the llama-tokenize binary of the same llama.cpp build.
"""
from __future__ import annotations

import argparse, hashlib, json, os, platform, subprocess, sys, time, unicodedata
from pathlib import Path

# Test text: Team 3's held-out sources (teams/03-tokenizer/train/fetch_heldout.py), not benchmark data. Pinned by the
# dataset repository's commit; streamed in order, so the same commit gives the same lines.
FW2 = ("HuggingFaceFW/fineweb-2", "af9c13333eb981300149d5ca60a8e9d659b276b9")                  # per-language `test` split
FW = ("HuggingFaceFW/fineweb", "9bb295ddab0e05d785b879661af7260fed5140fc")                     # English, sample-10BT
CODE = ("codeparrot/codeparrot-clean-valid", "4db92d2ec0c1b4c41eeb439cfae16854511d9dcd")      # Python files

# Team 3's languages (harness/run_harness.py): English + every Brahmic script the tokenizer covers
INDIC = ["hin_Deva", "mar_Deva", "ben_Beng", "asm_Beng", "tam_Taml", "tel_Telu", "kan_Knda", "mal_Mlym", "guj_Gujr",
         "pan_Guru", "ory_Orya"]
# not asked for; Latin with diacritics, Greek and Cyrillic test the regex's case classes
EXTRA = ["fra_Latn", "deu_Latn", "vie_Latn", "ell_Grek", "rus_Cyrl"]
N = 1000          # lines per language and for code
N_DERIVED = 100   # lines per Indic language in the derived sets
N_FILES, MAX_FILE = 100, 20_000   # whole Python files, at most this many characters each
VIRAMAS = "\u094d\u09cd\u0a4d\u0acd\u0b4d\u0bcd\u0c4d\u0ccd\u0d4d"
ZWNJ, ZWJ = "\u200c", "\u200d"
# Malayalam atomic chillu -> consonant + virama + ZWJ (the old spelling); Team 3's normalizer joins them back
OLD_CHILLU = {0x0D7A: "\u0d23\u0d4d\u200d", 0x0D7B: "\u0d28\u0d4d\u200d", 0x0D7C: "\u0d30\u0d4d\u200d",
              0x0D7D: "\u0d32\u0d4d\u200d", 0x0D7E: "\u0d33\u0d4d\u200d", 0x0D7F: "\u0d15\u0d4d\u200d"}
DEFAULT_PRE = ["granite-embed-multi-97m", "gpt-4o"]


def sha256(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_lines(lines: list[str]) -> str:
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def insert_zw(line: str) -> str:
    """ZWNJ after every 3rd virama starting with the 1st, ZWJ after every 3rd starting with the 2nd (deterministic)."""
    out, k = [], 0
    for ch in line:
        out.append(ch)
        if ch in VIRAMAS:
            k += 1
            if k % 3 == 1:
                out.append(ZWNJ)
            elif k % 3 == 2:
                out.append(ZWJ)
    return "".join(out)


def stream_docs(repo, config, split, field):
    from datasets import load_dataset
    for row in load_dataset(repo[0], name=config, split=split, streaming=True, revision=repo[1]):
        if row[field].strip():
            yield row[field]


def first_lines(docs, n: int) -> list[str]:
    out = []
    for doc in docs:
        out += [ln for ln in doc.split("\n") if ln.strip()]
        if len(out) >= n:
            break
    return out[:n]


def fetch_heldout(work: Path) -> dict[str, list[str]]:
    """The first N non-blank lines of each held-out stream, and the first whole Python files; cached in work/heldout/."""
    pins = {"fineweb-2": FW2[1], "fineweb": FW[1], "codeparrot-clean-valid": CODE[1], "n": N, "files": [N_FILES, MAX_FILE]}
    cache = work / "heldout" / "lines.json"
    if cache.exists() and json.loads(cache.read_text(encoding="utf-8"))["pins"] == pins:
        return json.loads(cache.read_text(encoding="utf-8"))["lines"]
    os.environ.setdefault("HF_HOME", str(work / "hf"))   # every download stays under --work
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    raw = {lang: first_lines(stream_docs(FW2, lang, "test", "text"), N) for lang in INDIC + EXTRA}
    raw["eng_Latn"] = first_lines(stream_docs(FW, "sample-10BT", "train", "text"), N)
    lines, files = [], []
    for doc in stream_docs(CODE, None, "train", "content"):
        if len(lines) < N:
            lines += [ln for ln in doc.split("\n") if ln.strip()]
        if len(files) < N_FILES and len(doc) <= MAX_FILE:
            files.append(doc)
        if len(lines) >= N and len(files) >= N_FILES:
            break
    raw["code_py_lines"], raw["code_py_files"] = lines[:N], files
    short = {k: len(v) for k, v in raw.items() if len(v) < (N_FILES if k == "code_py_files" else N)}
    if short:
        sys.exit(f"held-out stream too short: {short}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"pins": pins, "lines": raw}, ensure_ascii=False), encoding="utf-8")
    return raw


def load_sets(work: Path) -> dict[str, dict]:
    """name -> {lines, kind, source}. Text from Team 3's held-out sources; the ZWJ/ZWNJ, old-chillu and NFD sets are
    derived from it, because the natural text has no ZWJ or ZWNJ at all."""
    raw = fetch_heldout(work)
    fw2 = lambda lang: f"{FW2[0]} {lang} test @{FW2[1][:8]}, first {N} non-blank lines"
    sets = {"eng_Latn": {"lines": raw["eng_Latn"], "kind": "script",
                         "source": f"{FW[0]} sample-10BT @{FW[1][:8]}, first {N} non-blank lines"}}
    for lang in INDIC:
        sets[lang] = {"lines": raw[lang], "kind": "script", "source": fw2(lang)}
    for lang in EXTRA:
        sets[lang] = {"lines": raw[lang], "kind": "extra", "source": fw2(lang)}
    with_virama = {lang: [x for x in raw[lang] if any(v in x for v in VIRAMAS)][:N_DERIVED] for lang in INDIC}
    sets["zwj_zwnj"] = {"lines": [insert_zw(x) for xs in with_virama.values() for x in xs], "kind": "script",
                        "source": f"first {N_DERIVED} lines with a virama of each Indic language above, with ZWNJ and ZWJ "
                                  "inserted after viramas (the natural text has none)"}
    sets["nfd_indic"] = {"lines": [unicodedata.normalize("NFD", x) for lang in INDIC for x in raw[lang][:N_DERIVED]],
                         "kind": "extra", "source": f"first {N_DERIVED} lines of each Indic language above, NFD-decomposed"}
    chillu = [x for x in raw["mal_Mlym"] if any(chr(c) in x for c in OLD_CHILLU)][:N_DERIVED]
    sets["old_chillu_ml"] = {"lines": [x.translate(OLD_CHILLU) for x in chillu], "kind": "extra",
                             "source": f"mal_Mlym lines with a chillu, spelled consonant+virama+ZWJ ({len(chillu)} lines)"}
    sets["code_py_lines"] = {"lines": raw["code_py_lines"], "kind": "code",
                             "source": f"{CODE[0]} @{CODE[1][:8]}, first {N} non-blank lines (indentation kept)"}
    sets["code_py_files"] = {"lines": raw["code_py_files"], "kind": "code",
                             "source": f"{CODE[0]} @{CODE[1][:8]}, first {len(raw['code_py_files'])} whole files up to "
                                       f"{MAX_FILE:,} characters (newlines and indentation runs)"}
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


def convert(llama_cpp: Path, model_dir: Path, pre: str, outfile: Path, outtype: str = "f16", python=None):
    """Run llama.cpp's converter in a child process (`python`, default this one) with get_vocab_base_pre forced to `pre`."""
    code = ("import sys, runpy; L = sys.argv[1]; sys.path[:0] = [L, L + '/gguf-py']\n"
            "import conversion.base as b; pre = sys.argv[2]\n"
            "b.TextModel.get_vocab_base_pre = lambda self, tokenizer: pre\n"
            "sys.argv = [L + '/convert_hf_to_gguf.py'] + sys.argv[3:]\n"
            "runpy.run_path(sys.argv[0], run_name='__main__')")
    r = subprocess.run([str(python or sys.executable), "-c", code, str(llama_cpp), pre, str(model_dir),
                        "--outfile", str(outfile), "--outtype", outtype], capture_output=True, text=True)
    if r.returncode or not outfile.exists():
        sys.exit(f"conversion with pre={pre} failed:\n{r.stderr[-3000:]}")


def stock_convert_error(llama_cpp: Path, model_dir: Path, work: Path) -> str:
    """What the unmodified converter says about this tokenizer (expected: pre-tokenizer not recognized)."""
    r = subprocess.run([sys.executable, str(llama_cpp / "convert_hf_to_gguf.py"), str(model_dir), "--vocab-only",
                        "--outfile", str(work / "stock.gguf")], capture_output=True, text=True)
    if r.returncode == 0:
        return "converted without error (the tokenizer's hash is in this llama.cpp's list)"
    return r.stderr.strip().splitlines()[-1]


def cli_check(binary: Path, gguf: Path, enc, lines_by_set: dict, work: Path) -> dict:
    """The llama.cpp build's own llama-tokenize on each set joined into one text: same ids as `enc` (an HF tokenizer)?
    llama-cpp-python ships its own copy of llama.cpp, so this checks that the result holds for the converter's build."""
    out = {}
    for name, lines in lines_by_set.items():
        text = "\n".join(lines)
        f = work / f"cli_{name}.txt"
        f.write_bytes(text.encode("utf-8"))
        r = subprocess.run([str(binary), "-m", str(gguf), "-f", str(f), "--ids", "--no-bos", "--no-escape",
                            "--log-disable"], capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"llama-tokenize failed on {name}:\n{r.stderr[-2000:]}")
        out[name] = json.loads(r.stdout.strip().splitlines()[-1]) == enc.encode(text, add_special_tokens=False).ids
    return out


def first_diff(g: list, h: list, k: int) -> dict:
    """Where two id lists first differ, as ids; line text never goes into a report."""
    j = next(i for i, (a, b) in enumerate(zip(g + [-1], h + [-1])) if a != b)
    lo = max(0, j - 2)
    return {"line": k, "at_token": j, "hf_ids": h[lo:j + 4], "gguf_ids": g[lo:j + 4]}


def byte_map() -> dict:
    """GPT-2's byte-level alphabet: the character that stands for each byte, inverted (character -> byte)."""
    bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    cs, n = bs[:], 0
    for b in range(256):
        if b not in bs:
            bs.append(b); cs.append(256 + n); n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


def all_tokens(llm, plain, tok: dict) -> dict:
    """Every vocabulary id: (1) llama.cpp's text for the id equals tokenizer.json's bytes; (2) tokenizing that text gives
    the same ids in llama.cpp and HF (tokens that are whole UTF-8 text; special tokens are checked separately)."""
    bm = byte_map()
    special = {a["id"]: a["content"] for a in tok["added_tokens"] if a["special"]}
    res = {"ids": 0, "piece_bad": [], "text_ids": 0, "tok_bad": []}
    for text, i in tok["model"]["vocab"].items():
        want = special[i].encode("utf-8") if i in special else bytes(bm[c] for c in text)
        res["ids"] += 1
        if llm.detokenize([i], special=True) != want:
            res["piece_bad"].append(i)
            continue
        if i in special:
            continue
        try:
            s = want.decode("utf-8")
        except UnicodeDecodeError:
            continue   # part of a character: no text to tokenize
        res["text_ids"] += 1
        if llm.tokenize(want, add_bos=False, special=True) != plain.encode(s, add_special_tokens=False).ids:
            res["tok_bad"].append(i)
    return res


PRE_TYPES = {"granite-embed-multi-97m": "LLAMA_VOCAB_PRE_TYPE_GRANITE_EMB_MULTI"}   # llama.cpp's name for the type


def explain_pretok(r: dict, tok: dict, sets: dict, norm_sets: dict, llama_cpp: Path, pre: str, nf: bool) -> dict:
    """Why do lines or tokens differ for a reason other than the normalizer? Counts only, no text. For the lines that
    differ off the normalizer's account (the normalized pass with --normalize-first, else the raw pass on lines it does not
    change) and for the vocabulary tokens that tokenize differently: how many have a different cut in the pre-tokenizer
    regex of tokenizer.json and in the pattern llama.cpp uses for this type (read from its source, run with the `regex`
    package), and how many tokens are all-capital words with an accented capital that end in an ASCII capital."""
    import string
    out = {"lines": 0, "lines_by_set": {}, "lines_cut_differs": None, "tokens": len(r["all_tokens"]["tok_bad"]), "shape": 0,
           "tokens_cut_differs": None}
    todo = []   # (text, "line" or "token")
    for name, st in r["sets"].items():
        ids = st["normalized"]["id_mismatch"] if nf else [k for k in st["id_mismatch"] if k not in set(st["changed"])]
        if ids:
            out["lines_by_set"][name] = len(ids)
            todo += [(norm_sets[name][k] if nf else sets[name]["lines"][k], "line") for k in ids]
    out["lines"] = len(todo)
    bm, inv = byte_map(), {v: k for k, v in tok["model"]["vocab"].items()}
    for i in r["all_tokens"]["tok_bad"]:
        t = bytes(bm[c] for c in inv[i]).decode("utf-8")
        letters = [c for c in t if unicodedata.category(c).startswith("L")]
        out["shape"] += bool(letters and all(unicodedata.category(c) == "Lu" for c in letters)
                             and any(ord(c) > 127 for c in letters) and t[-1] in string.ascii_uppercase)
        todo.append((t, "token"))
    try:
        import regex
        src = (llama_cpp / "src" / "llama-vocab.cpp").read_text(encoding="utf-8")
        block = src[src.index("case " + PRE_TYPES[pre]):][:1500]
        llama_pat = json.loads(next(l.strip().rstrip(",") for l in block.splitlines() if l.strip().startswith('"[^')))
        hf_pat = tok["pre_tokenizer"]["pretokenizers"][0]["pattern"]["Regex"]
        cuts = lambda pat, t: {m.end() for m in regex.finditer(pat, t)}
        diff = {"line": 0, "token": 0}
        for t, kind in todo:
            diff[kind] += cuts(hf_pat, t) != cuts(llama_pat, t)
        out["lines_cut_differs"], out["tokens_cut_differs"] = diff["line"], diff["token"]
    except (ImportError, KeyError, ValueError, StopIteration, OSError):
        pass   # no `regex` package, or a pre-tokenizer type this script has no source mapping for
    return out


def check(gguf: Path, hf, plain, tok: dict, sets: dict, norm_sets: dict, normalize_first: bool = False) -> dict:
    """hf: the tokenizer as trained (with its normalizer); plain: the same without the normalizer; norm_sets:
    each set's lines after the normalizer (the same lines when there is none)."""
    from llama_cpp import Llama
    m = Llama(model_path=str(gguf), n_ctx=64, n_gpu_layers=0, verbose=False)   # the converted model runs
    generated = m.create_completion("भारत एक देश है", max_tokens=2, temperature=0)
    del m
    llm = Llama(model_path=str(gguf), vocab_only=True, verbose=False)
    res = {"pre": llm.metadata.get("tokenizer.ggml.pre"), "n_vocab": llm.n_vocab(),
           "bos": llm.token_bos(), "eos": llm.token_eos(), "generates": bool(generated["choices"]), "sets": {}}
    for name, s in sets.items():
        t0, r = time.time(), {"lines": len(s["lines"]), "id_mismatch": [], "gguf_text_err": [], "hf_text_err": [],
                              "tok_hf": 0, "tok_gguf": 0, "examples": [], "changed": [], "mismatch_changed": 0,
                              "mismatch_unchanged": 0}
        n = {"id_mismatch": [], "gguf_text_err": [], "hf_pipeline_diff": [], "tok_hf": 0, "tok_gguf": 0, "examples": []}
        for k, x in enumerate(s["lines"]):
            nx = norm_sets[name][k]
            # special=True on both sides: HF always parses special-token strings inside text
            g = llm.tokenize(x.encode("utf-8"), add_bos=False, special=True)
            h = hf.encode(x, add_special_tokens=False).ids
            r["tok_hf"] += len(h); r["tok_gguf"] += len(g)
            if nx != x:
                r["changed"].append(k)
            if llm.detokenize(g, special=True) != x.encode("utf-8"):
                r["gguf_text_err"].append(k)
            if hf.decode(h, skip_special_tokens=False) != nx:   # HF decodes to the normalized text
                r["hf_text_err"].append(k)
            if g != h:
                r["id_mismatch"].append(k)
                r["mismatch_changed" if nx != x else "mismatch_unchanged"] += 1
                if len(r["examples"]) < 2:
                    r["examples"].append(first_diff(g, h, k))
            if normalize_first:
                gn = llm.tokenize(nx.encode("utf-8"), add_bos=False, special=True)
                hn = plain.encode(nx, add_special_tokens=False).ids
                n["tok_hf"] += len(hn); n["tok_gguf"] += len(gn)
                if llm.detokenize(gn, special=True) != nx.encode("utf-8"):
                    n["gguf_text_err"].append(k)
                if hn != h:   # normalize, then plain tokenization, must be what HF does on the raw line
                    n["hf_pipeline_diff"].append(k)
                if gn != hn:
                    n["id_mismatch"].append(k)
                    if len(n["examples"]) < 2:
                        n["examples"].append(first_diff(gn, hn, k))
        r["seconds"] = round(time.time() - t0, 2)
        if normalize_first:
            r["normalized"] = n
        res["sets"][name] = r
    bad = []
    for a in tok["added_tokens"]:
        g = llm.tokenize(a["content"].encode("utf-8"), add_bos=False, special=True)
        if g != [a["id"]] or llm.detokenize(g, special=True) != a["content"].encode("utf-8"):
            bad.append({"id": a["id"], "content": a["content"], "gguf": g})
    res["specials"] = {"n": len(tok["added_tokens"]), "bad": bad}
    res["all_tokens"] = all_tokens(llm, plain, tok)
    return res


def vocab_bad(r: dict) -> bool:
    return bool(r["all_tokens"]["piece_bad"] or r["all_tokens"]["tok_bad"])


def verdict(r: dict, normalize_first: bool = False) -> int:
    """Exit code. 0 = same ids on every line and every vocabulary id checks out; 2 = raw pass differs only on lines the
    normalizer changes, the normalized pass is clean and the vocabulary checks out (needs --normalize-first);
    1 = anything else."""
    return 1 if vocab_bad(r) else line_verdict(r, normalize_first)


def line_verdict(r: dict, normalize_first: bool = False) -> int:
    """The same, for the test lines, the specials and the converted model only (not the whole-vocabulary check)."""
    base = not r["specials"]["bad"] and r["generates"]
    sets = r["sets"].values()
    if base and all(r["cli"].values()) and all(not s["id_mismatch"] and not s["gguf_text_err"] for s in sets):
        return 0
    if normalize_first and base and all(r["cli_norm"].values()) and all(
            not s["gguf_text_err"] and not s["mismatch_unchanged"] and not s["normalized"]["id_mismatch"]
            and not s["normalized"]["gguf_text_err"] and not s["normalized"]["hf_pipeline_diff"] for s in sets):
        return 2
    return 1


def report(args, info, sets, results) -> str:
    nf, hasn = args.normalize_first, info["normalizer"] != "none"
    L = [f"# GGUF round trip: tokenizer {args.name}", "",
         f"Generated by `tokenizer/gguf_roundtrip.py` on {info['date']} ({info['machine']}). Do not edit by hand; rerun the script.", "",
         "**Question.** Does llama.cpp, after GGUF conversion, cut text into the **same token ids** as the Hugging Face "
         "tokenizer the model is trained with? Gate 2 bar (TSAI, 2 Nov): same ids on every line; same decoded text alone "
         "is not enough.", "",
         "**Pass per line:** (1) GGUF ids == HF `tokenizers` ids; (2) GGUF detokenize(ids) == the original bytes. "
         "Special-token strings are parsed on both sides, as HF does by default. Checked with llama-cpp-python, line by line. "
         "The `llama-tokenize` column repeats the check with the llama.cpp build's own binary, on each set joined into "
         "one text with newlines.", ""]
    if hasn:
        L += [f"**Normalizer.** This tokenizer.json has a normalizer ({info['normalizer']}). The GGUF format has none, so "
              "llama.cpp tokenizes the text as it is while HF normalizes it first. " + (
              "The **raw** pass compares them as they are; the **normalized** pass applies the normalizer first and compares "
              "llama.cpp on that text with HF on the same text (HF without its normalizer), so the dropped normalizer is "
              "the only difference left. Normalize-then-tokenize is also checked against HF's own pipeline on every line."
              if nf else "Rerun with `--normalize-first` to separate that cause from any other."), ""]
    if info["longest_token_bytes"] > 32:
        L += [f"**Warning.** The longest token is {info['longest_token_bytes']} bytes. llama-cpp-python's detokenize holds one "
              "token's text in 32 bytes, so the decode column below can fail for that reason alone; the ids are not affected.", ""]
    L += ["## Result", ""]
    labels = {0: " **PASS**", 1: " **FAIL**", 2: " **KNOWN LIMIT: llama.cpp drops the normalizer**"}
    for pre in args.pre:
        r = results[pre]
        tot = lambda key: sum(len(s[key]) for s in r["sets"].values())
        n = sum(s["lines"] for s in r["sets"].values())
        line = (f"- **`{pre}`**: {tot('id_mismatch'):,} of {n:,} lines with different ids"
                + (f" ({sum(s['mismatch_changed'] for s in r['sets'].values()):,} on lines the normalizer changes, "
                   f"{sum(s['mismatch_unchanged'] for s in r['sets'].values()):,} on lines it does not)" if hasn else "")
                + f", {tot('gguf_text_err'):,} decode errors; "
                f"specials {r['specials']['n'] - len(r['specials']['bad'])}/{r['specials']['n']} exact; "
                f"{len(r['all_tokens']['piece_bad']) + len(r['all_tokens']['tok_bad'])} bad ids of {r['all_tokens']['ids']:,} "
                "in the whole-vocabulary check.")
        if nf:
            line += (f" Normalized pass: {sum(len(s['normalized']['id_mismatch']) for s in r['sets'].values()):,} of {n:,} "
                     f"lines differ, {sum(len(s['normalized']['hf_pipeline_diff']) for s in r['sets'].values()):,} differ "
                     "from HF's own pipeline.")
        v, lv = verdict(r, nf), line_verdict(r, nf)
        L.append(line + (" **LINES " + ("PASS" if lv == 0 else "KNOWN LIMIT (normalizer)") + ", WHOLE-VOCABULARY CHECK FAILS**"
                         if v == 1 and lv in (0, 2) else labels[v]))
    L += ["", f"The stock converter (no `--pre` override) says: `{info['stock_error']}`", ""]
    def unexplained(r):   # lines (raw pass off the normalizer's account, or normalized pass) + vocabulary tokens
        lines = sum(len(st["normalized"]["id_mismatch"]) if nf else st["mismatch_unchanged"] for st in r["sets"].values())
        return lines + len(r["all_tokens"]["tok_bad"]) + len(r["all_tokens"]["piece_bad"])
    ok = [p for p in args.pre if verdict(results[p], nf) in (0, 2)]
    best = ok[0] if ok else min(args.pre, key=lambda p: unexplained(results[p]))
    rb = results[best]
    trap = [p for p in args.pre if p != best and not any(st["gguf_text_err"] for st in results[p]["sets"].values())]
    if ok:
        L.append(f"**What it means.** Convert models that use this tokenizer with pre-tokenizer `{best}`; until llama.cpp knows "
                 "this tokenizer's hash, the converter must be told the type, as this script does.")
    else:
        pt = rb["pretok"]
        L.append("**What it means.** **No tested llama.cpp pre-tokenizer gives the same ids on every line and every vocabulary "
                 f"token: blocker for G3 and G12.** The closest is `{best}`: apart from the lines the normalizer changes, "
                 f"{unexplained(rb) - len(rb['all_tokens']['tok_bad']) - len(rb['all_tokens']['piece_bad']):,} test line(s) and "
                 f"{len(rb['all_tokens']['tok_bad']) + len(rb['all_tokens']['piece_bad']):,} vocabulary token(s) differ.")
    if trap:
        L.append(" ".join(f"`{p}` decodes every line back to the same text, but cuts "
                          f"{sum(len(st['id_mismatch']) for st in results[p]['sets'].values()):,} lines into different tokens."
                          for p in trap) + " A check of decoded text alone would pass it; the model would see ids it was not "
                 "trained on.")
    if nf and any(st["mismatch_changed"] for st in rb["sets"].values()):
        ch = sum(len(st["changed"]) for st in rb["sets"].values()); mm = sum(st["mismatch_changed"] for st in rb["sets"].values())
        n = sum(st["lines"] for st in rb["sets"].values())
        L += ["", f"**Normalizer.** llama.cpp alone does not reproduce the training ids on the {mm:,} lines whose text the "
              f"normalizer changes ({ch:,} of {n:,} lines are changed). With the normalizer applied first those lines match "
              "(see the normalized pass). A serving app that uses llama.cpp must run the normalizer on the text before "
              "tokenizing; the GGUF cannot carry it."]
    if not ok:
        pt = rb["pretok"]
        by = ", ".join(f"{k} {v}" for k, v in pt["lines_by_set"].items()) or "none"
        L += ["", "**Pre-tokenizer.** What differs besides the normalizer: "
              f"{pt['lines']:,} test line(s) (by set: {by}) and {pt['tokens']:,} vocabulary token(s) "
              f"({pt['shape']:,} of the tokens are all-capital words with an accented capital that end in an ASCII capital). "
              "The pattern llama.cpp uses for this type (`src/llama-vocab.cpp`) tells upper from lower case with the ASCII "
              "ranges `[^a-z]` and `[^A-Z]`, while tokenizer.json's regex uses `\\p{Lu}` and `\\p{Ll}`. For cased letters "
              "outside ASCII (accented Latin, Cyrillic, Greek) the two cut words differently where the case changes, for "
              "example a word in CamelCase or an all-capital word with an accented capital."
              + (f" Running both regexes with the `regex` package gives a different cut for {pt['lines_cut_differs']:,} of "
                 f"{pt['lines']:,} lines and {pt['tokens_cut_differs']:,} of {pt['tokens']:,} tokens."
                 if pt["lines_cut_differs"] is not None else "")
              + " Scripts without case (every Indic script and the code sets here) are not affected: none of their "
              "test lines differs for this reason. Text with such words (all-capital headings, CamelCase in Cyrillic or Greek) "
              "gets different ids from llama.cpp; the line numbers and token ids are in the .json."]
    L.append("")
    for pre in args.pre:
        r = results[pre]
        L += [f"## Per set, pre-tokenizer `{pre}`", "",
              f"GGUF metadata: `tokenizer.ggml.pre` = `{r['pre']}`, n_vocab {r['n_vocab']:,}, bos {r['bos']}, eos {r['eos']}. "
              f"The full GGUF loads and generates: {'yes' if r['generates'] else 'NO'}.", "",
              f"**Whole vocabulary.** All {r['all_tokens']['ids']:,} ids: llama.cpp's text equals tokenizer.json's for "
              f"{r['all_tokens']['ids'] - len(r['all_tokens']['piece_bad']):,}; tokenizing a token's own text gives the same "
              f"ids as HF for {r['all_tokens']['text_ids'] - len(r['all_tokens']['tok_bad']):,} of {r['all_tokens']['text_ids']:,} "
              "tokens that are whole text (the rest are parts of a character, or special tokens, checked on their own).", ""]
        if nf:
            L += ["**Raw pass** (text as it is):", ""]
        cols = (["Set", "Kind", "Lines"] + (["Changed by normalizer"] if hasn else []) + ["Different ids"]
                + (["of which on changed lines"] if hasn else [])
                + ["GGUF decode errors", "HF decode errors", "Tokens HF", "Tokens GGUF", "Δ tokens", "llama-tokenize"])
        L += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for name, s in r["sets"].items():
            d = (s["tok_gguf"] / s["tok_hf"] - 1) * 100 if s["tok_hf"] else 0
            cells = ([name, sets[name]["kind"], f"{s['lines']:,}"] + ([f"{len(s['changed']):,}"] if hasn else [])
                     + [f"{len(s['id_mismatch']):,}"] + ([f"{s['mismatch_changed']:,}"] if hasn else [])
                     + [f"{len(s['gguf_text_err']):,}", f"{len(s['hf_text_err']):,}", f"{s['tok_hf']:,}", f"{s['tok_gguf']:,}",
                        f"{d:+.1f}%", {True: "same", False: "**differs**", None: "not run"}[r["cli"].get(name)]])
            L.append("| " + " | ".join(cells) + " |")
        ex_rows = [(n, "raw" if nf else "", e) for n, s in r["sets"].items() for e in s["examples"][:1]]
        if nf:
            L += ["", "**Normalized pass** (llama.cpp on normalizer(text) against HF on the same text, no normalizer):", "",
                  "| Set | Lines | Different ids | GGUF decode errors | Differs from HF's own pipeline | Tokens HF | Tokens GGUF | llama-tokenize |",
                  "|---|---|---|---|---|---|---|---|"]
            for name, s in r["sets"].items():
                q = s["normalized"]
                L.append(f"| {name} | {s['lines']:,} | {len(q['id_mismatch']):,} | {len(q['gguf_text_err']):,} | "
                         f"{len(q['hf_pipeline_diff']):,} | {q['tok_hf']:,} | {q['tok_gguf']:,} | "
                         f"{ {True: 'same', False: '**differs**', None: 'not run'}[r['cli_norm'].get(name)] } |")
            ex_rows += [(n, "normalized", e) for n, s in r["sets"].items() for e in s["normalized"]["examples"][:1]]
        if ex_rows:
            L += ["", "First differing tokens (token ids around the first difference, one line per set; the lines are not "
                  "printed, look them up by index in the source):", "",
                  "| Set | Pass | Line | HF ids | GGUF ids |", "|---|---|---|---|---|"]
            L += [f"| {n} | {ps or 'raw'} | {e['line']} | {e['hf_ids']} | {e['gguf_ids']} |" for n, ps, e in ex_rows]
        if r["specials"]["bad"]:
            L += ["", f"Specials that fail: {json.dumps(r['specials']['bad'][:10], ensure_ascii=False)}"]
        L.append("")
    L += ["## Sets", "", "| Set | Source |", "|---|---|"]
    L += [f"| {n} | {s['source']} |" for n, s in sets.items()]
    L += ["", "Kinds: `script` = what the task asks (each script the tokenizer covers, and code); `extra` = harder input "
          "outside the task (other Latin, Greek, Cyrillic, NFD). The text is web text from Team 3's held-out sources (FineWeb, "
          "FineWeb-2, codeparrot-clean-valid), not benchmark data; each source is pinned by its dataset commit below, and "
          "each set by the sha256 of its lines. Team 3's own held-out files cannot be rebuilt without their training corpus "
          "(they drop overlapping documents), so this run reads the same sources directly and its hashes differ from "
          "theirs. This file and the .json hold counts, line indices, token ids and hashes only, never line text.", "",
          "## Inputs and outputs (sha256)", "", "| What | sha256 |", "|---|---|"]
    L += [f"| {k} | `{v}` |" for k, v in info["sha256"].items()]
    L += ["", f"Longest token: {info['longest_token_bytes']} bytes. Normalizer in tokenizer.json: {info['normalizer']}.", "",
          "Versions: " + ", ".join(f"{k} {v}" for k, v in info["versions"].items()) + ".", "",
          "Rerun: `python tokenizer/gguf_roundtrip.py --tokenizer <tokenizer.json> --name " + args.name +
          (" --normalize-first" if nf else "") + (f' --eos "{args.eos}"' if args.eos != "<|end_of_text|>" else "") +
          " --llama-cpp <llama.cpp b11669> --llama-tokenize <its llama-tokenize> --work <tmp> --out results`", ""]
    return "\n".join(L)


def _version(package: str) -> str | None:
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tokenizer", type=Path, required=True, help="tokenizer.json")
    ap.add_argument("--name", required=True, help="label for the report, e.g. v0 or frozen")
    ap.add_argument("--llama-cpp", type=Path, required=True, help="llama.cpp checkout (b11669): converter + gguf-py")
    ap.add_argument("--work", type=Path, required=True, help="scratch folder: data, tiny model, GGUF files")
    ap.add_argument("--out", type=Path, required=True, help="folder for the .md and .json report")
    ap.add_argument("--pre", action="append", help=f"llama.cpp pre-tokenizer type(s); the first decides the exit code "
                    f"(default: {' '.join(DEFAULT_PRE)})")
    ap.add_argument("--normalize-first", action="store_true",
                    help="also run llama.cpp on normalizer(text) against HF on the same text (for a tokenizer with a normalizer)")
    ap.add_argument("--gguf", type=Path, help="check this converted GGUF (from tokenizer/convert_frozen.py) instead of converting a tiny model; its tokenizer.ggml.pre must equal the first --pre")
    ap.add_argument("--llama-tokenize", type=Path, help="llama-tokenize binary of the same llama.cpp build (optional)")
    ap.add_argument("--bos", default="<|begin_of_text|>")
    ap.add_argument("--eos", default="<|end_of_text|>")
    args = ap.parse_args()
    args.pre = args.pre or DEFAULT_PRE
    if args.gguf:   # one given file, one pre-tokenizer
        args.pre = args.pre[:1]
    args.work.mkdir(parents=True, exist_ok=True); args.out.mkdir(parents=True, exist_ok=True)

    import llama_cpp, tokenizers, torch, transformers
    from tokenizers import Tokenizer
    sets = load_sets(args.work)
    model_dir = args.work / f"tiny_{args.name}"
    n_vocab = make_tiny_model(args.tokenizer, model_dir, args.bos, args.eos) if not args.gguf else None
    tok = json.loads(args.tokenizer.read_text(encoding="utf-8"))
    nj = tok.get("normalizer")
    info = {"date": time.strftime("%Y-%m-%d"), "machine": f"{platform.machine()} {platform.system()}, CPU",
            "stock_error": stock_convert_error(args.llama_cpp, model_dir, args.work) if not args.gguf
            else "not run: this GGUF was made by convert_frozen.py with the pre-tokenizer set by name",
            "normalizer": "none" if nj is None else nj["type"] + (f", {len(nj['normalizers'])} steps" if nj.get("normalizers") else ""),
            "sha256": {f"tokenizer.json ({args.name})": sha256(args.tokenizer),
                       "fineweb-2 dataset commit": FW2[1], "fineweb dataset commit": FW[1],
                       "codeparrot-clean-valid dataset commit": CODE[1],
                       "llama.cpp convert_hf_to_gguf.py": sha256(args.llama_cpp / "convert_hf_to_gguf.py"),
                       "llama.cpp conversion/base.py": sha256(args.llama_cpp / "conversion" / "base.py")},
            "versions": {"Python": platform.python_version(), "llama-cpp-python": llama_cpp.__version__,
                         "tokenizers": tokenizers.__version__, "transformers": transformers.__version__,
                         "torch": torch.__version__, **{m: v for m in ("datasets", "regex") if (v := _version(m))}},
            "tiny_model": f"Llama, 1 layer, hidden 64, vocab {n_vocab:,}, random weights (seed 0), f16 GGUF" if not args.gguf
            else "none: the GGUF checked is the converter's output for a real checkpoint"}
    # byte-level vocab: one character per byte. llama-cpp-python's detokenize holds one token's text in 32 bytes, so a
    # longer token makes the GGUF decode check fail on its own, with the ids still right (BrahmicTokenizer's rule: <= 32)
    info["longest_token_bytes"] = max(len(t) for t in tok["model"]["vocab"])
    if nj is not None:
        info["sha256"]["normalizer (canonical json, 16 hex)"] = hashlib.sha256(
            json.dumps(nj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    for n, st in sets.items():
        info["sha256"][f"lines of {n}, joined with newlines (text not committed)"] = sha256_lines(st["lines"])
    hf = Tokenizer.from_file(str(args.tokenizer))
    plain = Tokenizer.from_str(hf.to_str()); plain.normalizer = None
    norm_sets = {n: [hf.normalizer.normalize_str(x) for x in s["lines"]] if hf.normalizer is not None else s["lines"]
                 for n, s in sets.items()}
    results = {}
    for pre in args.pre:
        gguf = args.gguf or args.work / f"tiny_{args.name}_{pre}.gguf"
        if not args.gguf:
            convert(args.llama_cpp, model_dir, pre, gguf)
        info["sha256"][f"GGUF ({pre}), not committed"] = sha256(gguf)
        results[pre] = r = check(gguf, hf, plain, tok, sets, norm_sets, args.normalize_first)
        if args.gguf and r["pre"] != pre:
            sys.exit(f"{gguf} has tokenizer.ggml.pre = {r['pre']!r}, not {pre!r}: converted without the forced pre-tokenizer")
        r["cli"] = cli_check(args.llama_tokenize, gguf, hf, {n: s["lines"] for n, s in sets.items()}, args.work) \
            if args.llama_tokenize else {}
        r["cli_norm"] = cli_check(args.llama_tokenize, gguf, plain, norm_sets, args.work) \
            if args.llama_tokenize and args.normalize_first else {}
        r["pretok"] = explain_pretok(r, tok, sets, norm_sets, args.llama_cpp, pre, args.normalize_first)
        print(f"{pre}: {sum(len(s['id_mismatch']) for s in r['sets'].values())} lines with different ids, "
              f"{sum(len(s['gguf_text_err']) for s in r['sets'].values())} decode errors, "
              f"{len(r['specials']['bad'])} bad specials, {len(r['all_tokens']['piece_bad'])}+{len(r['all_tokens']['tok_bad'])} bad ids"
              + (f"; normalized pass: {sum(len(s['normalized']['id_mismatch']) for s in r['sets'].values())} different, "
                 f"{sum(len(s['changed']) for s in r['sets'].values())} lines changed by the normalizer"
                 if args.normalize_first else "") + f"; verdict {verdict(r, args.normalize_first)}")
    md = args.out / f"gguf_roundtrip_{args.name}.md"
    md.write_text(report(args, info, sets, results), encoding="utf-8")
    drop = ("examples", "seconds")
    slim = {pre: {k: v for k, v in r.items() if k != "sets"} | {"sets": {
        n: {k: ({kk: vv for kk, vv in v.items() if kk != "examples"} if k == "normalized" else v)
            for k, v in s.items() if k not in drop} for n, s in r["sets"].items()}} for pre, r in results.items()}
    (args.out / f"gguf_roundtrip_{args.name}.json").write_text(
        json.dumps({"info": info, "results": slim}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {md}")
    sys.exit(verdict(results[args.pre[0]], args.normalize_first))


if __name__ == "__main__":
    main()
