#!/usr/bin/env python3
"""Serving with token ids: the GGUF round trip for tokenizer p1536 when the app tokenizes (G12 week 3, Gate 3).

results/gguf_roundtrip_p1536.md fails for two reasons that live in llama.cpp's own tokenizer: the GGUF cannot carry
p1536's normalizer (3,074 Indic test lines), and llama.cpp's built-in split pattern tells capitals from lower case with
ASCII ranges only (1 Russian test line, 6 vocabulary tokens). A serving app can skip llama.cpp's tokenizer: it tokenizes
with the frozen tokenizer.json (normalizer and split pattern exactly as in training) and sends token ids. llama-server's
/completion takes `prompt` as a list of ids, and /detokenize turns ids into text. This script checks that path on the
same test lines as gguf_roundtrip.py, and measures what the other path (plain text into llama.cpp, as Ollama does)
costs on our own data.

  1. ids in, text out, on every test line: tokenizer.json's ids are what the model gets, by construction. Check that
     llama.cpp's detokenize(ids) is the text tokenizer.json's decode(ids) gives, and that the model runs on the ids.
  2. the whole vocabulary: llama.cpp's text for every id equals tokenizer.json's bytes.
  3. --server: the same through a running llama-server (/detokenize of 20 lines per set; /completion with an id prompt).
  4. --sample-dir: plain text into llama.cpp, on the raw sample v0 parts. Per pack: the documents the normalizer changes;
     in a seeded sample of 300 documents, those whose llama.cpp ids differ from tokenizer.json's; and the documents where
     the two split patterns cut differently (only a document with a non-ASCII capital can differ, so only those are run).

Speed: encode and decode are batched (Rust); detokenize and tokenize are one C call per line or document; the split
patterns run inside the regex engine (a substitution that marks every cut), so no Python loop visits tokens or words.
The reports hold counts, line indices, ids and hashes only, never text.

    python tokenizer/serving_ids_check.py --tokenizer <p1536 tokenizer.json> --gguf <GGUF with this tokenizer> \
        --llama-cpp <llama.cpp b11669> --work <gguf_roundtrip.py's --work> --out results \
        [--server http://127.0.0.1:8091] [--sample-dir <raw sample v0 train folder, one folder per pack>]
Writes <out>/gguf_serving_ids_p1536.md and .json. Exit 0 when checks 1 to 3 pass on every line and id; 1 otherwise.
"""
from __future__ import annotations

import argparse, json, os, platform, random, sys, time, urllib.request
from pathlib import Path

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gguf_roundtrip import byte_map, load_sets, sha256  # noqa: E402  (the same test lines and byte map)

SAMPLE_DOCS, SERVER_LINES = 300, 20
# a non-ASCII capital (Latin-1, Latin Extended-A, Greek, Cyrillic, Latin Extended Additional): the pre-filter of check 4
NON_ASCII_CAPS = r"[\x{00C0}-\x{00DE}\x{0100}-\x{017F}\x{0370}-\x{03FF}\x{0400}-\x{04FF}\x{1E00}-\x{1EFF}]"


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def ids_path(hf, llm, gen, sets):
    """Check 1: per set, the lines whose llama.cpp detokenize(ids) differs from tokenizer.json's decode(ids). The model
    runs on the first line of each set, with its ids (60 at most) as the prompt."""
    out = {}
    for name, s in sets.items():
        ids = [e.ids for e in hf.encode_batch(s["lines"], add_special_tokens=False)]
        want = hf.decode_batch(ids, skip_special_tokens=False)
        bad = [k for k, (x, w) in enumerate(zip(ids, want)) if llm.detokenize(x, special=True) != w.encode("utf-8")]
        gen.reset()
        r = gen.create_completion(prompt=ids[0][:60], max_tokens=2, temperature=0)
        out[name] = {"lines": len(ids), "tokens": sum(map(len, ids)), "text_differs": bad,
                     "model_ran_on_ids": r["usage"]["prompt_tokens"] == len(ids[0][:60])}
    return out


def vocab_pieces(llm, tok):
    """Check 2: every id's text in llama.cpp equals tokenizer.json's bytes."""
    bm, special = byte_map(), {a["id"]: a["content"] for a in tok["added_tokens"] if a["special"]}
    bad = [i for t, i in tok["model"]["vocab"].items()
           if llm.detokenize([i], special=True) != (special[i].encode() if i in special else bytes(bm[c] for c in t))]
    return {"ids": len(tok["model"]["vocab"]), "bad": bad}


def server_check(url, hf, sets):
    """Check 3: llama-server's /detokenize on tokenizer.json's ids, and /completion with an id prompt."""
    out = {"lines": 0, "text_differs": 0}
    for s in sets.values():
        ids = [e.ids for e in hf.encode_batch(s["lines"][:SERVER_LINES], add_special_tokens=False)]
        for x, w in zip(ids, hf.decode_batch(ids, skip_special_tokens=False)):
            out["lines"] += 1
            out["text_differs"] += post(url + "/detokenize", {"tokens": x})["content"] != w
    ids = hf.encode(sets["tel_Telu"]["lines"][0], add_special_tokens=False).ids[:60]
    r = post(url + "/completion", {"prompt": ids, "n_predict": 2, "temperature": 0, "cache_prompt": False})
    n = r.get("tokens_evaluated")
    out.update(prompt_ids=len(ids), tokens_evaluated=n, completion_ok=n in (len(ids), len(ids) + 1))  # +1: a BOS in front
    return out


def plain_text_cost(sample_dir, hf, llm, hf_pat, llama_pat):
    """Check 4: plain text into llama.cpp, per pack of the raw sample v0 (counts only)."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    import regex
    norm, rx_hf, rx_ll = hf.normalizer.normalize_str, regex.compile(hf_pat), regex.compile(llama_pat)
    rows = {}
    for pack_dir in sorted(p for p in Path(sample_dir).iterdir() if p.is_dir()):
        texts = pq.read_table(sorted(pack_dir.glob("*.parquet"))[0], columns=["text"]).column("text").combine_chunks()
        docs = texts.to_pylist()
        changed = sum(norm(t) != t for t in docs)                      # one Rust call per document
        pick = [docs[i] for i in random.Random(0).sample(range(len(docs)), min(SAMPLE_DOCS, len(docs)))]
        h = [e.ids for e in hf.encode_batch(pick, add_special_tokens=False)]
        g = [llm.tokenize(t.encode("utf-8"), add_bos=False, special=True) for t in pick]
        caps = pc.filter(texts, pc.match_substring_regex(texts, NON_ASCII_CAPS)).to_pylist()
        cut = lambda rx, t: rx.sub("\x00\\g<0>", t)                    # every cut marked, inside the regex engine
        rows[pack_dir.name] = {
            "docs": len(docs), "normalizer_changes": changed, "sample": len(pick),
            "sample_ids_differ": sum(a != b for a, b in zip(g, h)),
            "sample_tokens_hf": sum(map(len, h)), "sample_tokens_llama": sum(map(len, g)),
            "docs_with_non_ascii_capital": len(caps), "split_differs": sum(cut(rx_hf, t) != cut(rx_ll, t) for t in caps)}
    return rows


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "–"


def report(res, args) -> str:
    i, ip = res["info"], res["ids_path"]
    n_lines, differ = sum(s["lines"] for s in ip.values()), sum(len(s["text_differs"]) for s in ip.values())
    L = ["# GGUF round trip, serving with token ids: tokenizer p1536", "",
         f"Generated by `tokenizer/serving_ids_check.py` on {i['date']} ({i['machine']}). Do not edit by hand; rerun the "
         "script.", "",
         "**Question.** `gguf_roundtrip_p1536.md` fails because llama.cpp's own tokenizer differs from tokenizer.json: the "
         "GGUF cannot carry p1536's normalizer, and llama.cpp's split pattern tells capitals from lower case with ASCII "
         "ranges only. Does the round trip pass when the serving app tokenizes with tokenizer.json and sends llama.cpp "
         "token ids (llama-server `/completion` with `prompt` as a list of ids, `/detokenize` for the text)? vLLM reads "
         "tokenizer.json itself, so it is on this path already.", "",
         "## Result", "",
         f"- **Ids in, text out: {differ:,} of {n_lines:,} test lines differ**; the model ran on the ids in every set: "
         f"{'yes' if all(s['model_ran_on_ids'] for s in ip.values()) else 'NO'}. "
         f"Same {len(ip)} sets and lines as `gguf_roundtrip_p1536.md`.",
         f"- **Whole vocabulary: {len(res['vocab']['bad']):,} of {res['vocab']['ids']:,} ids** have a different text in "
         "llama.cpp."]
    if "server" in res:
        s = res["server"]
        L.append(f"- **llama-server** (same GGUF): `/detokenize` differs on {s['text_differs']} of {s['lines']} lines; "
                 f"`/completion` with a {s['prompt_ids']}-id prompt evaluated {s['tokens_evaluated']} tokens: "
                 f"{'OK' if s['completion_ok'] else 'NOT OK'}.")
    L += ["", f"**Verdict: {'PASS' if i['pass'] else 'FAIL'}.** "
          + ("A serving app that tokenizes with tokenizer.json and sends ids gets exactly the training ids on every test "
             "line, and llama.cpp gives back the same text for every id. The normalizer and the split pattern stay in "
             "tokenizer.json, where they are exact." if i["pass"] else "See the tables."), ""]
    if "plain_text" in res:
        pt = res["plain_text"]
        L += ["## What plain text into llama.cpp costs (Ollama, llama-server `/completion` with a text prompt)", "",
              "On the raw sample v0 parts (the text the p1536 shards were made from). *Normalizer changes*: documents whose "
              "text the normalizer changes, so llama.cpp sees other text than training did. *Sample ids differ*: of "
              f"{SAMPLE_DOCS} documents drawn with seed 0, those whose llama.cpp ids differ from tokenizer.json's. "
              "*Split pattern differs*: documents whose cuts differ between tokenizer.json's pattern and llama.cpp's, both "
              "run with the `regex` package as in `gguf_roundtrip.py` (an estimate; only documents with a non-ASCII capital "
              "can differ, so only those are run). The *sample ids differ* column is llama.cpp's own tokenizer.", "",
              "| Pack | Documents | Normalizer changes | Sample ids differ | Tokens tokenizer.json / llama.cpp (sample) "
              "| Documents with a non-ASCII capital | Split pattern differs |", "|---|---:|---:|---:|---:|---:|---:|"]
        for pack, r in pt.items():
            L.append(f"| `{pack}` | {r['docs']:,} | {r['normalizer_changes']:,} ({pct(r['normalizer_changes'], r['docs'])}) "
                     f"| {r['sample_ids_differ']} of {r['sample']} | {r['sample_tokens_hf']:,} / {r['sample_tokens_llama']:,} "
                     f"| {r['docs_with_non_ascii_capital']:,} | {r['split_differs']:,} ({pct(r['split_differs'], r['docs'])}) |")
        L += ["", "**What it means.** The normalizer cost is not spread evenly. Where a pack's text uses the characters "
              "the normalizer rewrites, most documents reach llama.cpp in a form the model never saw in training; elsewhere "
              "almost none do. The split-pattern cost is small in every pack and comes from Latin, Greek or Cyrillic words "
              "with a non-ASCII capital. A plain-text client (Ollama, or llama-server with a text prompt) therefore needs "
              "the app to normalize first, and still keeps the split-pattern difference; a client that sends tokenizer.json's "
              "ids has neither.", ""]
    L += ["## Per set (ids in, text out)", "", "| Set | Lines | Tokens | Text differs | Model ran on ids |", "|---|---:|---:|---:|---|"]
    L += [f"| {n} | {s['lines']:,} | {s['tokens']:,} | {len(s['text_differs'])} | {'yes' if s['model_ran_on_ids'] else 'NO'} |"
          for n, s in ip.items()]
    L += ["", "## Inputs and versions", "", "| What | Value |", "|---|---|",
          f"| tokenizer.json sha256 | `{i['tokenizer_sha256']}` |", f"| GGUF sha256 (not committed) | `{i['gguf_sha256']}` |",
          f"| llama.cpp pre-tokenizer type | `{i['pre']}` |", f"| Machine | {i['machine']} |",
          f"| Versions | Python {i['python']}, llama-cpp-python {i['llama_cpp_python']}, tokenizers {i['tokenizers']}, "
          f"llama-server {i.get('server_build', 'not run')} |", f"| Wall time | {i['seconds']} s |", "",
          "Rerun: `python tokenizer/serving_ids_check.py --tokenizer <tokenizer.json> --gguf <tiny p1536 GGUF from "
          "gguf_roundtrip.py --work> --llama-cpp <llama.cpp b11669> --work <its --work> --out results --server <llama-server "
          "URL> --sample-dir <raw sample v0 train folder>`", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--gguf", type=Path, required=True)
    ap.add_argument("--llama-cpp", type=Path, required=True, help="llama.cpp checkout: its split pattern for check 4")
    ap.add_argument("--work", type=Path, required=True, help="gguf_roundtrip.py's --work (cached test lines)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--server", help="URL of a llama-server running the same GGUF (check 3)")
    ap.add_argument("--sample-dir", type=Path, help="raw sample v0 parts, one folder per pack (check 4)")
    ap.add_argument("--pre", default="granite-embed-multi-97m")
    a = ap.parse_args()
    t0 = time.time()
    import llama_cpp, tokenizers
    from llama_cpp import Llama
    from tokenizers import Tokenizer
    tok = json.loads(a.tokenizer.read_text(encoding="utf-8"))
    hf = Tokenizer.from_file(str(a.tokenizer))
    sets = load_sets(a.work)
    llm = Llama(model_path=str(a.gguf), vocab_only=True, verbose=False)
    gen = Llama(model_path=str(a.gguf), n_ctx=128, n_gpu_layers=0, verbose=False)
    res = {"ids_path": ids_path(hf, llm, gen, sets), "vocab": vocab_pieces(llm, tok)}
    del gen
    info = {"date": time.strftime("%Y-%m-%d"), "machine": f"{platform.machine()} {platform.system()}", "pre": a.pre,
            "tokenizer_sha256": sha256(a.tokenizer), "gguf_sha256": sha256(a.gguf), "python": platform.python_version(),
            "llama_cpp_python": llama_cpp.__version__, "tokenizers": tokenizers.__version__}
    if a.server:
        res["server"] = server_check(a.server.rstrip("/"), hf, sets)
        with urllib.request.urlopen(a.server.rstrip("/") + "/props", timeout=30) as r:
            info["server_build"] = json.loads(r.read()).get("build_info", "?")
    if a.sample_dir:
        src = (a.llama_cpp / "src" / "llama-vocab.cpp").read_text(encoding="utf-8")
        block = src[src.index("case LLAMA_VOCAB_PRE_TYPE_GRANITE_EMB_MULTI"):][:1500]
        llama_pat = json.loads(next(l.strip().rstrip(",") for l in block.splitlines() if l.strip().startswith('"[^')))
        res["plain_text"] = plain_text_cost(a.sample_dir, hf, llm, tok["pre_tokenizer"]["pretokenizers"][0]["pattern"]["Regex"],
                                            llama_pat)
    differ = sum(len(s["text_differs"]) for s in res["ids_path"].values())
    ok = (differ == 0 and all(s["model_ran_on_ids"] for s in res["ids_path"].values()) and not res["vocab"]["bad"]
          and (not a.server or (res["server"]["text_differs"] == 0 and res["server"]["completion_ok"])))
    info.update(seconds=round(time.time() - t0, 1), **{"pass": ok})
    res["info"] = info
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "gguf_serving_ids_p1536.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (a.out / "gguf_serving_ids_p1536.md").write_text(report(res, a), encoding="utf-8")
    n_lines = sum(s["lines"] for s in res["ids_path"].values())
    print(f"ids path: {differ} of {n_lines} lines differ; vocabulary: {len(res['vocab']['bad'])} bad of {res['vocab']['ids']}"
          + (f"; server: {res['server']['text_differs']} of {res['server']['lines']} differ, completion "
             f"{'ok' if res['server']['completion_ok'] else 'NOT ok'}" if a.server else "")
          + f"; {'PASS' if ok else 'FAIL'}; wall time {info['seconds']} s")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
