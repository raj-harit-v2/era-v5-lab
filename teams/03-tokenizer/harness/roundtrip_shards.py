"""Round trip on the token shards (G3 week 3, Task 4).

    python teams/03-tokenizer/harness/roundtrip_shards.py <shard folder> --tokenizer <p1536>/tokenizer.json \
        --out teams/03-tokenizer/results/roundtrip_shards.md

Reads Data A's shards (teams/01-data-a/shards/shard_format_v1.md): <shard_id>.json, .bin, .idx.npy, .docs.parquet.
Groups them by the manifest's `domain`, draws up to --per-domain documents per domain (seeded, across all the shards of
that domain) and checks each drawn document:

  eos       the document ends with EOS 130822, and no other special id is inside it;
  ids       encode(decode(ids)) == ids: the shard ids are exactly what p1536 gives for the text they decode to;
  normal    normalizer(decode(ids)) == decode(ids): the decoded text is already in normal form (NFC, chillu, nukta);
  source    (only with --clean <dir>) decode(ids) == normalizer(source text), the source row being the docs.parquet
            input_part / input_row in that folder's run_clean.py output.

Before any document is read, each shard is checked against its manifest: tokenizer_sha256 is p1536, eos_token_id 130822,
the .bin header (magic 20261025, version 2, token count), size 1,024 + 4 x token_count, payload sha256, index sha256, and
the index (int64, starts at 0, rises, ends at token_count, doc_count + 1 entries). A shard that fails is reported and
skipped.

The report gives only IDs, counts, hashes and token positions: never document text. Needs numpy, pyarrow, tokenizers.
"""

import argparse
import hashlib
import json
import platform
import random
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import tokenizers
from tokenizers import Tokenizer

P1536_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
VOCAB = 131_072
EOS_ID = 130_822
SPECIAL_FROM = 130_725
MAGIC, VERSION, HEADER_BYTES = 20261025, 2, 1024
BATCH = 256


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_tokenizer(path, any_tokenizer):
    got = sha256(path)
    if got != P1536_SHA256 and not any_tokenizer:
        sys.exit(f"{path}: sha256 {got}, not the frozen p1536 {P1536_SHA256}")
    tok = Tokenizer.from_file(str(path))
    if not any_tokenizer:
        if tok.get_vocab_size(with_added_tokens=True) != VOCAB:
            sys.exit(f"{path}: vocab {tok.get_vocab_size(with_added_tokens=True)}, not {VOCAB}")
        if tok.id_to_token(EOS_ID) != "<|endoftext|>":
            sys.exit(f"{path}: id {EOS_ID} is {repr(tok.id_to_token(EOS_ID))}, not <|endoftext|>")
    specials = {i for i, t in tok.get_added_tokens_decoder().items() if t.special}
    specials |= set(range(SPECIAL_FROM, VOCAB))
    norm = tok.normalizer.normalize_str if tok.normalizer is not None else (lambda t: t)
    return tok, got, specials, norm


def open_shard(manifest_path, tok_sha, check_sha):
    """(shard dict, None) or (None, reason)."""
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    if m.get("schema_version") != "shard-v1":
        return None, None  # not a shard manifest
    d = manifest_path.parent
    sid = m["shard_id"]
    bin_p = d / Path(m["payload_uri"]).name
    idx_p = d / Path(m["index_uri"]).name
    docs_p = d / Path(m.get("sample_metadata_uri", f"{sid}.docs.parquet")).name
    qr_p = d / Path(m.get("quality_report_uri", f"{sid}.quality_report.json")).name
    for p in (bin_p, idx_p):
        if not p.exists():
            return None, f"{p.name} missing"
    if m.get("tokenizer_sha256") != tok_sha:
        return None, f"tokenizer_sha256 {m.get('tokenizer_sha256')} is not the tokenizer given"
    if m.get("eos_token_id") != EOS_ID:
        return None, f"eos_token_id {m.get('eos_token_id')}"
    n = int(m["token_count"])
    if bin_p.stat().st_size != HEADER_BYTES + 4 * n or m.get("payload_bytes") != HEADER_BYTES + 4 * n:
        return None, "payload size does not match 1,024 + 4 x token_count"
    header = np.fromfile(bin_p, dtype="<i4", count=3)
    if header.tolist() != [MAGIC, VERSION, n]:
        return None, f"header {header.tolist()}"
    if check_sha:
        if sha256(bin_p) != m["payload_sha256"]:
            return None, "payload sha256 does not match the manifest"
        if sha256(idx_p) != m["index_sha256"]:
            return None, "index sha256 does not match the manifest"
    idx = np.load(idx_p)
    if idx.dtype != np.int64 or idx[0] != 0 or idx[-1] != n or len(idx) != m["doc_count"] + 1 or (np.diff(idx) <= 0).any():
        return None, "index is not int64 0 .. token_count, rising, doc_count + 1 entries"
    tokens = np.memmap(bin_p, dtype="<u4", mode="r", offset=HEADER_BYTES, shape=(n,))
    meta = None
    if docs_p.exists():
        cols = [c for c in ("doc_id", "input_part", "input_row") if c in pq.read_schema(docs_p).names]
        meta = pq.read_table(docs_p, columns=cols).to_pydict()
        if len(meta["doc_id"]) != m["doc_count"]:
            return None, "docs.parquet rows != doc_count"
    writer_dropped = None
    if qr_p.exists():
        qr = json.loads(qr_p.read_text(encoding="utf-8"))
        writer_dropped = {"roundtrip": qr.get("left_out", {}).get("roundtrip"), "rows_read": qr.get("rows_read")}
    return {"id": sid, "m": m, "tokens": tokens, "idx": idx, "meta": meta, "writer": writer_dropped,
            "payload_sha256": m["payload_sha256"], "domain": m.get("domain", "?")}, None


def first_diff(a, b):
    for k, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return k
    return min(len(a), len(b))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shards", type=Path, help="folder with the shards (searched recursively for *.json manifests)")
    ap.add_argument("--tokenizer", type=Path, required=True, help="the frozen p1536 tokenizer.json")
    ap.add_argument("--per-domain", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=4)
    ap.add_argument("--clean", type=Path, help="folder with the run_clean.py *_clean.parquet the shards were written from")
    ap.add_argument("--no-sha", action="store_true", help="skip the payload and index sha256 (faster; not for the report)")
    ap.add_argument("--any-tokenizer", action="store_true", help="tests only")
    ap.add_argument("--out", type=Path, help="write the Markdown report here (and a .json next to it)")
    a = ap.parse_args(argv)

    t0 = time.time()
    tok, tok_sha, specials, norm = load_tokenizer(a.tokenizer, a.any_tokenizer)
    shards, bad = [], []
    for mp in sorted(a.shards.rglob("*.json")):
        if mp.name.endswith(".quality_report.json") or mp.name == "cleaning_pipeline.json":
            continue
        try:
            s, why = open_shard(mp, tok_sha, not a.no_sha)
        except (KeyError, ValueError, OSError) as e:
            s, why = None, f"{type(e).__name__}: {e}"
        if s:
            shards.append(s)
        elif why:
            bad.append((mp.stem, why))
    if not shards:
        sys.exit(f"no readable shard in {a.shards}" + "".join(f"\n  {i}: {w}" for i, w in bad))

    clean_cache = {}

    def source_text(s, j):
        part, row = s["meta"]["input_part"][j], s["meta"]["input_row"][j]
        if part not in clean_cache:
            hits = list(a.clean.rglob(part))
            clean_cache[part] = pq.read_table(hits[0], columns=["text"]).column("text").to_pylist() if hits else None
        col = clean_cache[part]
        return col[row] if col is not None and 0 <= row < len(col) else None

    by_domain = defaultdict(list)
    for s in shards:
        by_domain[s["domain"]].append(s)

    rng = random.Random(a.seed)
    domains, failures, per_shard = {}, [], defaultdict(lambda: {"sampled": 0, "fail": 0})
    for dom in sorted(by_domain):
        pool = [(s, j) for s in by_domain[dom] for j in range(len(s["idx"]) - 1)]
        draw = sorted(rng.sample(range(len(pool)), min(a.per_domain, len(pool))))
        stats = {"shards": len(by_domain[dom]), "docs": len(pool), "sampled": len(draw), "tokens": 0,
                 "eos": 0, "ids": 0, "normal": 0, "source": 0, "source_missing": 0, "fffd_docs": 0}
        for b in range(0, len(draw), BATCH):
            items = [pool[k] for k in draw[b:b + BATCH]]
            docs = [s["tokens"][s["idx"][j]:s["idx"][j + 1]].tolist() for s, j in items]
            inner = [d[:-1] for d in docs]
            texts = tok.decode_batch(inner, skip_special_tokens=False)
            re_ids = [e.ids for e in tok.encode_batch(texts, add_special_tokens=False)]
            for (s, j), d, ids, text, again in zip(items, docs, inner, texts, re_ids):
                doc_id = s["meta"]["doc_id"][j] if s["meta"] else f"#{j}"
                per_shard[s["id"]]["sampled"] += 1
                stats["tokens"] += len(d)
                why = []
                if d[-1] == EOS_ID and not (set(ids) & specials):
                    stats["eos"] += 1
                else:
                    why.append("eos/special")
                if again == ids:
                    stats["ids"] += 1
                else:
                    why.append(f"ids differ at token {first_diff(ids, again)} ({len(ids)} vs {len(again)})")
                if norm(text) == text:
                    stats["normal"] += 1
                else:
                    why.append("decoded text not in normal form")
                if "�" in text:
                    stats["fffd_docs"] += 1
                if a.clean and s["meta"] and "input_row" in s["meta"]:
                    src = source_text(s, j)
                    if src is None:
                        stats["source_missing"] += 1
                    elif norm(src) == text:
                        stats["source"] += 1
                    else:
                        why.append(f"source differs at char {first_diff(norm(src), text)}")
                if why:
                    per_shard[s["id"]]["fail"] += 1
                    failures.append({"domain": dom, "shard_id": s["id"], "doc": j, "doc_id": doc_id, "why": "; ".join(why)})
        domains[dom] = stats

    wall = time.time() - t0
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parent).stdout.strip() or "?"
    total = sum(d["sampled"] for d in domains.values())
    result = "PASS" if not failures and not bad else "FAIL"
    summary = {"result": result, "tokenizer_sha256": tok_sha, "tokenizers": tokenizers.__version__,
               "python": platform.python_version(), "platform": platform.platform(), "commit": commit,
               "seed": a.seed, "per_domain": a.per_domain, "source_check": bool(a.clean), "wall_s": round(wall, 1),
               "domains": domains, "shards": [{"shard_id": s["id"], "domain": s["domain"],
                                                "payload_sha256": s["payload_sha256"], "doc_count": len(s["idx"]) - 1,
                                                "token_count": int(s["idx"][-1]), **per_shard[s["id"]],
                                                "writer_left_out_roundtrip": (s["writer"] or {}).get("roundtrip"),
                                                "writer_rows_read": (s["writer"] or {}).get("rows_read")}
                                               for s in shards],
               "skipped_shards": [{"shard": i, "why": w} for i, w in bad], "failures": failures}

    print(f"RESULT: {result}  {total:,} documents, {len(domains)} domains, {len(shards)} shards, "
          f"{len(failures)} failures, {len(bad)} shards skipped, {wall:.1f} s")
    for dom, st in domains.items():
        print(f"  {dom:10s} sampled {st['sampled']:>5,}  eos {st['eos']:>5,}  ids {st['ids']:>5,}  normal {st['normal']:>5,}"
              + (f"  source {st['source']:>5,}" if a.clean else ""))
    for f in failures[:20]:
        print(f"  FAIL {f['shard_id']} doc {f['doc']} ({f['doc_id']}): {f['why']}")
    for i, w in bad:
        print(f"  SKIPPED {i}: {w}")

    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        a.out.write_text(report(summary, a), encoding="utf-8")
        print(f"wrote {a.out} and {a.out.with_suffix('.json').name}")
    return 0 if result == "PASS" else 1


def report(S, a):
    src = S["source_check"]
    total = sum(d["sampled"] for d in S["domains"].values())
    ok = lambda n, of: f"{n:,} / {of:,}"
    L = ["# Round trip on the p1536 token shards (week 3, Task 4)\n\n",
         f"**Result: {S['result']}.** {total:,} documents drawn from {len(S['shards'])} shards in {len(S['domains'])} "
         f"domains (up to {S['per_domain']:,} per domain, seed {S['seed']}); {len(S['failures'])} failures.\n\n",
         "| Field | Value |\n|---|---|\n",
         f"| Tokenizer | p1536 `tokenizer.json`, sha256 `{S['tokenizer_sha256']}` |\n",
         f"| Shards | TSAI's p1536 sample-v0 bundle (16 Nov), `dataset_version: sample` |\n",
         f"| Script | `teams/03-tokenizer/harness/roundtrip_shards.py` at `{S['commit'][:12]}` |\n",
         f"| Environment | Python {S['python']}, tokenizers {S['tokenizers']}, {S['platform']} |\n",
         f"| Wall time | {S['wall_s']} s, including sha256 of every shard |\n\n",
         "## Checks per document\n\n",
         "| Check | Rule |\n|---|---|\n",
         "| eos | ends with EOS `<\\|endoftext\\|>` 130822; no other special id inside |\n",
         "| ids | `encode(decode(ids)) == ids` (ids without the final EOS, `add_special_tokens=False`) |\n",
         "| normal | `normalizer(decode(ids)) == decode(ids)`: decoded text is already NFC + chillu + nukta form |\n",
         "| source | `decode(ids) == normalizer(source text)`, source row from `docs.parquet` `input_part` / `input_row` |\n\n",
         "Each shard was first checked against its manifest: tokenizer sha256, EOS id, `.bin` header and size, "
         "payload and index sha256, and the document index.\n\n",
         "## By domain\n\n",
         "| Domain | Shards | Docs in shards | Drawn | eos | ids | normal | source | Tokens drawn |\n",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"]
    for dom, d in S["domains"].items():
        s_col = ok(d["source"], d["sampled"]) if src else "not run"
        L.append(f"| {dom} | {d['shards']} | {d['docs']:,} | {d['sampled']:,} | {ok(d['eos'], d['sampled'])} | "
                 f"{ok(d['ids'], d['sampled'])} | {ok(d['normal'], d['sampled'])} | {s_col} | {d['tokens']:,} |\n")
    L += ["\n## By shard\n\n",
          "Writer drops: documents `shard_writer.py` already left out because `decode(encode(x)) != normalizer(x)` "
          "(from each shard's `quality_report.json`), of rows read.\n\n",
          "| Shard | Domain | payload sha256 | Docs | Tokens | Drawn | Failures | Writer drops |\n",
          "|---|---|---|---:|---:|---:|---:|---:|\n"]
    for s in S["shards"]:
        wd = (f"{s['writer_left_out_roundtrip']:,} / {s['writer_rows_read']:,}"
              if s["writer_left_out_roundtrip"] is not None and s["writer_rows_read"] else "n/a")
        L.append(f"| `{s['shard_id']}` | {s['domain']} | `{s['payload_sha256'][:12]}…` | {s['doc_count']:,} | "
                 f"{s['token_count']:,} | {s['sampled']:,} | {s['fail']} | {wd} |\n")
    L.append("\n## Failures\n\n")
    if S["failures"]:
        L.append("| Shard | Doc | doc_id | What |\n|---|---:|---|---|\n")
        L += [f"| `{f['shard_id']}` | {f['doc']} | `{f['doc_id']}` | {f['why']} |\n" for f in S["failures"][:200]]
    else:
        L.append("None.\n")
    if S["skipped_shards"]:
        L.append("\n## Shards skipped\n\n| Shard | Why |\n|---|---|\n")
        L += [f"| `{x['shard']}` | {x['why']} |\n" for x in S["skipped_shards"]]
    L += ["\n## Notes\n\n",
          "- The round trip is against the normalized text, as the tokenizer card says (section 2): Bn/Pa nukta and Ml old "
          "chillu come back in normal form, so `decode(encode(x))` can differ from the raw `x`.\n",
          "- " + ("The source check ran against the cleaned parts the shards were written from.\n" if src else
                  "The source check (`--clean`) did not run: the cleaned parts were not available. `ids` and `normal` "
                  "together show the shard ids are p1536's own encoding of text already in normal form, and the writer "
                  "had already checked decode against the normalized source for every kept document.\n"),
          "- No document text is in this file: only IDs, counts, hashes and token positions.\n",
          "\n## Command\n\n```\n",
          f"python teams/03-tokenizer/harness/roundtrip_shards.py <shards> --tokenizer <p1536>/tokenizer.json "
          f"--per-domain {S['per_domain']} --seed {S['seed']}" + (" --clean <clean parts>" if src else "") +
          " --out teams/03-tokenizer/results/roundtrip_shards.md\n```\n"]
    return "".join(L)


if __name__ == "__main__":
    sys.exit(main())
