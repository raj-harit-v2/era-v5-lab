r"""E4 of dedup_design_v1.md: rebuild the rejected near-identical pairs of the Indic sangraha-s packs from the raw text,
and prepare them for a human reader. It labels nothing.

TSAI's overlap run rejected 106 pairs inside ind-kn-, ind-te- and ind-ta-sangraha-s that score word Jaccard >= 0.80,
each because a document has fewer than 50 words (results_v1.md, section 3). Whether they are true copies needs a reader
of the language. This script:

  1. Takes those pairs from TSAI's outputs: overlap_pairs.csv (score >= 0.80, both documents in the same pack) minus
     the pairs in overlap_matches.csv, with each document's split, part, row and word count from overlap_docs.parquet.
  2. Finds each document's text in the raw sample-v0 parts by split and doc_id (cleaning keeps doc_id) and rebuilds its
     H1 key and word 5-grams as overlap.py does. TSAI scored the cleaned parts; cleaning may have changed some of them
     (Team 9 report that ind-kn- and ind-te-sangraha-s were not passed through unchanged). So the script checks, for
     every document of these packs, whether the raw text gives TSAI's word and 5-gram counts, and for every pair whether
     the raw text gives TSAI's score (to the 6 decimals TSAI wrote). A pair without that was read from text that
     differs from what TSAI scored.
  3. Counts, from TSAI's outputs alone, how many of these pairs, and how many prose pairs >= 0.80 with an ind-* side
     across all packs, would qualify with a lower word minimum (40, 30, 20, 10).
  4. Writes a blind review sheet per pack: the two texts of each pair side by side, in a shuffled order, with no score,
     no length and no label, and a labels CSV for the reader to fill in. A key file, not for the reader, maps each
     pair ID to its rows, IDs, scores and counts.

Everything is written under out/e4/, which is git-ignored. The review sheets hold document text and must stay out of
the repo; only counts from e4_summary.json go into the docs.

HOW TO RUN IT
=============
From the repository root, with pyarrow:

    python3 -B teams/01-data-a/dedup/e4_review.py

Options (paths relative to the repository root): --tsai (TSAI's overlap outputs, default out/overlap_tsai), --raw (raw
sample-v0 packs, each with Part_* and Heldout, default inputs/sample_v0/packs), --out (inside out/, default out/e4),
--packs (default the three sangraha-s packs), --seed (order of the pairs on the sheets, default 2026).

WHAT IT WRITES (in --out)
=========================
  e4_summary.json             counts only: per pack, the documents checked against TSAI's counts, the pairs, how many
                              have TSAI's score from the raw text, clusters, and the counts at lower word minimums;
                              across all ind-* prose pairs, the same counts
  e4_pairs.csv                the key: pair ID -> rows, doc_ids, splits, TSAI's and the raw score, word counts, H1 key
                              characters, words that differ, cluster. IDs, scores and counts only; not for the reader
  review/<pack>/reading.html  the pairs to read, blind: text A and text B side by side, words found in only one of
                              them highlighted. Holds document text
  review/<pack>/labels.csv    pair_id, label, note: for the reader to fill in (copy, template, different or unsure)
"""
import sys
sys.dont_write_bytecode = True   # write only to ./out/: no __pycache__ beside the scripts

import argparse, csv, hashlib, html, json, random, re  # noqa: E402
from collections import Counter, defaultdict, namedtuple  # noqa: E402
from difflib import SequenceMatcher  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from h1_sha256 import h1_key, pack_folders, read_file, write_csv  # noqa: E402
from jaccard_matrix import MIN_WORDS, shingles  # noqa: E402
from overlap_rules import THRESHOLDS, domain  # noqa: E402

REPO = Path(__file__).resolve().parents[3]   # teams/01-data-a/dedup/e4_review.py -> the repository root
PACKS = ["ind-kn-sangraha-s", "ind-te-sangraha-s", "ind-ta-sangraha-s"]
LANGUAGES = {"bn": "Bengali", "gu": "Gujarati", "hi": "Hindi", "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi",
             "or": "Odia", "sa": "Sanskrit", "ta": "Tamil", "te": "Telugu"}
LOWER = (40, 30, 20, 10)                     # word minimums to count, below the design's 50
WORD = re.compile(r"\S+")

Raw = namedtuple("Raw", "text key grams words status same_counts")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_raw(raw, pack):
    """(split, doc_id) -> [(file name, row, text)] for every document of one raw pack, and the files read."""
    folders = pack_folders(raw / pack)
    if not folders:
        sys.exit(f"ERROR: no Part_* or Heldout folder in {raw / pack}")
    index, files = defaultdict(list), []
    for d in folders:
        split = "heldout" if d.name.lower() == "heldout" else "train"
        for f in sorted(d.rglob("*.parquet")):
            files.append(f)
            for row, doc_id, text in read_file(f):
                index[split, doc_id].append((f.name, row, text or ""))
    return index, files


def find_text(index, doc):
    """The raw text of one TSAI document, by split and doc_id; the part and row settle a repeated doc_id."""
    found = index.get((doc["split"], doc["doc_id"]), [])
    if not found:
        return None, "missing"
    same = [c for c in found if c[0] == Path(doc["part"]).name and c[1] == doc["row_in_part"]]
    if len(found) == 1 or same or len({c[2] for c in found}) == 1:
        return (same or found)[0][2], "found"
    return found[0][2], "ambiguous"


def profile(text, doc):
    """The raw text's H1 key, set of word 5-gram digests and word count, as overlap.py builds them."""
    key = h1_key(text)
    blob, words = shingles(key, 5)
    grams = {blob[i:i + 8] for i in range(0, len(blob), 8)}
    return key, grams, words, words == doc["words"] and len(grams) == doc["shingles"]


def jaccard(a, b):
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def differing(key_a, key_b):
    """Words of each H1 key outside the longest matching runs of the two."""
    wa, wb = key_a.split(), key_b.split()
    na = nb = 0
    for op, i1, i2, j1, j2 in SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
        if op != "equal":
            na, nb = na + i2 - i1, nb + j2 - j1
    return na, nb


def highlight(text_a, text_b):
    """Both raw texts as HTML, with the words found in only one of them (after aligning the two) marked."""
    spans = [list(WORD.finditer(t)) for t in (text_a, text_b)]
    tokens = [[m.group().casefold() for m in s] for s in spans]
    marked = (set(), set())
    for op, i1, i2, j1, j2 in SequenceMatcher(None, *tokens, autojunk=False).get_opcodes():
        if op != "equal":
            marked[0].update(range(i1, i2))
            marked[1].update(range(j1, j2))
    out = []
    for text, sp, mk in zip((text_a, text_b), spans, marked):
        parts, pos = [], 0
        for k, m in enumerate(sp):
            if k in mk:
                parts += [html.escape(text[pos:m.start()]), "<mark>", html.escape(m.group()), "</mark>"]
                pos = m.end()
        parts.append(html.escape(text[pos:]))
        out.append("".join(parts))
    return out


PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>E4 pairs: {language}</title>
<style>
  :root {{ color-scheme: light dark; --line: #8886; --mark: #f5c54270; }}
  body {{ font: 16px/1.6 system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 16px; }}
  .pair {{ border-top: 2px solid var(--line); padding: 12px 0 24px; }}
  .texts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 700px) {{ .texts {{ grid-template-columns: 1fr; }} }}
  .text {{ white-space: pre-wrap; overflow-wrap: anywhere; font-size: 18px; padding: 8px 10px;
           border: 1px solid var(--line); border-radius: 6px; }}
  mark {{ background: var(--mark); color: inherit; }}
  h2 {{ font-size: 18px; margin: 0 0 8px; }}
  h3 {{ font-size: 14px; margin: 0 0 4px; }}
</style>
</head>
<body>
<h1>{language}: {n} pairs to read</h1>
<p>Each block shows two documents from the {language} part of the sangraha-s sample. For each pair, write one label
in <code>labels.csv</code>, on the row with the pair's ID:</p>
<ul>
  <li><b>copy</b>: the same text. One may have a few words added, removed or changed, or be cut shorter.</li>
  <li><b>template</b>: the same frame or fixed wording (a site header, a form, a standard notice) with different
      content: different names, dates, numbers, places or message.</li>
  <li><b>different</b>: different texts that share some phrases.</li>
  <li><b>unsure</b>: you cannot tell. Please say why in the note.</li>
</ul>
<p>Words found in only one of the two texts are highlighted. That is only a reading aid: it does not suggest an
answer. The pairs are in random order. Please label every pair on your own before comparing notes with anyone.
The text is the raw sample-v0 text.</p>
{pairs}
</body>
</html>
"""
BLOCK = """<section class="pair">
<h2>{pid}</h2>
<div class="texts">
<div><h3>A</h3><div class="text" dir="auto">{a}</div></div>
<div><h3>B</h3><div class="text" dir="auto">{b}</div></div>
</div>
</section>"""


def clusters(pairs):
    """Connected groups of the pairs' documents: row -> (cluster number, cluster size), and the groups."""
    parent = {}
    def root(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b, _ in pairs:
        parent[root(a)] = root(b)
    groups = defaultdict(list)
    for x in list(parent):
        groups[root(x)].append(x)
    ordered = sorted(groups.values(), key=min)
    return {x: (k, len(g)) for k, g in enumerate(ordered, 1) for x in g}, ordered


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tsai", default="out/overlap_tsai", help="TSAI's overlap outputs")
    ap.add_argument("--raw", default="inputs/sample_v0/packs", help="raw sample-v0 packs, each with Part_* and Heldout")
    ap.add_argument("--out", default="out/e4", help="output folder, inside out/")
    ap.add_argument("--packs", nargs="+", default=PACKS, help="ind-* packs whose rejected pairs to rebuild")
    ap.add_argument("--seed", type=int, default=2026, help="seed for the order of the pairs on the review sheets")
    args = ap.parse_args(argv)
    tsai, raw, out = REPO / args.tsai, REPO / args.raw, REPO / args.out
    if not out.resolve().is_relative_to((REPO / "out").resolve()):
        sys.exit(f"ERROR: --out must be inside out/ in the repository root, not {args.out}")
    for p in args.packs:
        if not p.startswith("ind-") or domain(p) != "prose":
            sys.exit(f"ERROR: {p} is not an ind-* pack")
    try:
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
    except ImportError:
        sys.exit("ERROR: needs pyarrow: python3 -m pip install pyarrow")

    # 1. TSAI's outputs: every document's pack and word count, the qualifying pairs, the pairs >= 0.80.
    table = pq.read_table(tsai / "overlap_docs.parquet",
                          columns=["row", "doc_id", "pack", "split", "part", "row_in_part", "words", "shingles"])
    if table.column("row").to_pylist() != list(range(table.num_rows)):
        sys.exit("ERROR: overlap_docs.parquet rows are not 0, 1, 2, ... in order")
    pack_of, words = table.column("pack").to_pylist(), table.column("words").to_pylist()
    docs = {d["row"]: d for d in table.filter(pc.is_in(table.column("pack"), value_set=pa.array(args.packs))).to_pylist()}
    absent = sorted(set(args.packs) - {d["pack"] for d in docs.values()})
    if absent:
        sys.exit(f"ERROR: no documents of {absent} in {tsai / 'overlap_docs.parquet'}")
    with (tsai / "overlap_matches.csv").open(newline="", encoding="utf-8") as f:
        matched = {tuple(sorted((int(m["row_a"]), int(m["row_b"])))) for m in csv.DictReader(f)}
    threshold = THRESHOLDS["prose"]
    qualify, rejected, indic = Counter(), defaultdict(list), defaultdict(list)
    with (tsai / "overlap_pairs.csv").open(newline="", encoding="utf-8") as f:
        for p in csv.DictReader(f):
            if float(p["jaccard"]) < threshold:
                continue
            a, b = sorted((int(p["row_a"]), int(p["row_b"])))
            pa_, pb_ = pack_of[a], pack_of[b]
            ok = (a, b) in matched
            if pa_ == pb_ and pa_ in args.packs:
                if ok:
                    qualify[pa_] += 1
                else:
                    rejected[pa_].append((a, b, p["jaccard"]))
            if not ok and domain(pa_) == domain(pb_) == "prose" and "ind-" in (pa_[:4], pb_[:4]):
                indic[" x ".join(sorted((pa_, pb_)))].append((a, b))

    # 2-4, pack by pack: the raw text, the checks, the counts, the blind sheet.
    summary_packs, key_rows, raw_files = {}, [], {}
    for pack in args.packs:
        index, files = read_raw(raw, pack)
        raw_files.update({str(f.relative_to(raw)): sha256_file(f) for f in files})
        found = {}
        status = Counter()
        for r, d in docs.items():
            if d["pack"] != pack:
                continue
            text, st = find_text(index, d)
            status[st] += 1
            if text is not None:
                key, grams, n, same_counts = profile(text, d)
                found[r] = Raw(text, key, grams, n, st, same_counts)
        pairs = sorted(rejected[pack])
        cluster_of, groups = clusters(pairs)
        lang = pack.split("-")[1]
        order = list(range(len(pairs)))
        random.Random(f"{args.seed}:{pack}").shuffle(order)
        blocks, labels, same_score = [], [], 0
        for n, i in enumerate(order, 1):
            a, b, score = pairs[i]
            pid = f"{lang}-{n:02d}"
            ra, rb = found.get(a), found.get(b)
            raw_score = jaccard(ra.grams, rb.grams) if ra and rb else None
            same = raw_score is not None and abs(raw_score - float(score)) <= 1e-6
            same_score += same
            da, db = differing(ra.key, rb.key) if ra and rb else ("", "")
            key_rows.append([pid, pack, a, b, docs[a]["doc_id"], docs[b]["doc_id"], docs[a]["split"], docs[b]["split"],
                             score, "" if raw_score is None else f"{raw_score:.6f}", same,
                             docs[a]["words"], docs[b]["words"], ra.words if ra else "", rb.words if rb else "",
                             len(ra.key) if ra else "", len(rb.key) if rb else "", da, db,
                             ra.status if ra else "missing", rb.status if rb else "missing",
                             ra.same_counts if ra else "", rb.same_counts if rb else "", *cluster_of[a]])
            if ra and rb:
                ha, hb = highlight(ra.text, rb.text)
            else:
                ha, hb = (html.escape(x.text) if x else "<em>text not found in the raw parts</em>" for x in (ra, rb))
            blocks.append(BLOCK.format(pid=pid, a=ha, b=hb))
            labels.append([pid, "", ""])
        sheet = out / "review" / pack
        sheet.mkdir(parents=True, exist_ok=True)
        language = LANGUAGES.get(lang, lang)
        (sheet / "reading.html").write_text(PAGE.format(lang=lang, language=language, n=len(pairs),
                                                         pairs="\n".join(blocks)), encoding="utf-8")
        with open(sheet / "labels.csv", "w", newline="", encoding="utf-8-sig") as fh:   # BOM: opens in Excel
            csv.writer(fh).writerows([["pair_id", "label", "note"], *labels])

        shorter = [min(docs[a]["words"], docs[b]["words"]) for a, b, _ in pairs]
        raw_split = Counter()
        for (split, _doc_id), copies in index.items():
            raw_split[split] += len(copies)
        summary_packs[pack] = {
            "documents_tsai": dict(sorted(Counter(d["split"] for d in docs.values() if d["pack"] == pack).items())),
            "documents_raw": dict(sorted(raw_split.items())),
            "tsai_documents_found_in_raw": status["found"],
            "tsai_documents_ambiguous_in_raw": status["ambiguous"],
            "tsai_documents_missing_from_raw": status["missing"],
            "tsai_documents_with_tsai_counts_from_raw": sum(x.same_counts for x in found.values()),
            "pairs_at_or_above_0.80": qualify[pack] + len(pairs),
            "qualify": qualify[pack],
            "rejected": len(pairs),
            "rejected_by_50_word_minimum": sum(s < MIN_WORDS for s in shorter),
            "rejected_other": sum(s >= MIN_WORDS for s in shorter),
            "rejected_pairs_with_tsai_score_from_raw": same_score,
            "documents_in_rejected_pairs": len(cluster_of),
            "clusters": len(groups),
            "cluster_sizes": {str(k): v for k, v in sorted(Counter(len(g) for g in groups).items())},
            "rejected_pairs_by_shorter_document_words": {f"{lo}-{lo + 9}": sum(lo <= s <= lo + 9 for s in shorter)
                                                          for lo in range(0, MIN_WORDS, 10)},
            "rejected_pairs_qualifying_with_minimum": {str(m): sum(s >= m for s in shorter) for m in LOWER},
        }

    # 3, across all packs: prose pairs >= 0.80 with an ind-* side that the 50-word minimum rejected.
    indic_out, all_pairs = {}, []
    for name, prs in sorted(indic.items()):
        shorter = [min(words[a], words[b]) for a, b in prs]
        all_pairs += zip(prs, shorter)
        indic_out[name] = {"pairs": len(prs), "rejected_other": sum(s >= MIN_WORDS for s in shorter),
                           "qualifying_with_minimum": {str(m): sum(s >= m for s in shorter) for m in LOWER}}
    indic_total = {
        "pairs": len(all_pairs),
        "rejected_other": sum(s >= MIN_WORDS for _, s in all_pairs),
        "documents": len({x for p, _ in all_pairs for x in p}),
        "qualifying_with_minimum": {str(m): sum(s >= m for _, s in all_pairs) for m in LOWER},
        "documents_in_qualifying_pairs": {str(m): len({x for p, s in all_pairs if s >= m for x in p}) for m in LOWER},
    }

    write_csv(out / "e4_pairs.csv",
              ["pair_id", "pack", "row_a", "row_b", "doc_id_a", "doc_id_b", "split_a", "split_b", "tsai_jaccard",
               "raw_jaccard", "tsai_score_from_raw", "words_a", "words_b", "raw_words_a", "raw_words_b",
               "raw_key_chars_a", "raw_key_chars_b", "differing_words_a", "differing_words_b", "raw_text_a",
               "raw_text_b", "tsai_counts_from_raw_a", "tsai_counts_from_raw_b", "cluster", "cluster_size"], key_rows)
    summary = {
        "what": "E4: near-identical pairs (word Jaccard >= 0.80) inside each pack that the 50-word minimum rejected, "
                "rebuilt from the raw sample-v0 text. No labels: the reading is a human reader's.",
        "inputs": {"tsai": args.tsai,
                   "tsai_files": {f: sha256_file(tsai / f)
                                  for f in ("overlap_docs.parquet", "overlap_matches.csv", "overlap_pairs.csv")},
                   "raw": args.raw, "raw_files": raw_files},
        "checks": {"tsai_counts_from_raw": "the raw text gives the word and 5-gram counts TSAI recorded for the document",
                   "tsai_score_from_raw": "the raw text of both documents gives TSAI's word Jaccard, to 1e-6"},
        "seed": args.seed,
        "packs": summary_packs,
        "ind_prose_pairs_rejected_by_length": {"by_pack_pair": indic_out, "all": indic_total},
    }
    (out / "e4_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"packs": summary_packs, "ind_prose_pairs_rejected_by_length": indic_total}, indent=2))
    print(f"\nWrote e4_summary.json, e4_pairs.csv and review/<pack>/reading.html, labels.csv to {args.out}. "
          f"The review sheets hold document text: keep them out of the repo.")


if __name__ == "__main__":
    sys.exit(main())
