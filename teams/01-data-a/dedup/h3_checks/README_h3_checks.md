# H3 checks before h3.py: known pairs and the encoder (dedup v2 proposal, H3-e and H3-i)

Two scripts, measurement only: nothing is removed. Document text stays in `out/`, outside the repo.

## 1. `build_known_pairs.py` (done, 15 Nov)

Splits raw `ind-sa-fw2` documents (week-1 pack: 5,963 documents) into their Sanskrit lines and the lines Data B's
`DB-H3-001` calls translations (Hindi by function words, or Latin script without IAST marks).

```bash
P=/d/TheSchoolofAI/Capstone/Cap1-packs/Cap1-packs/ind-sa-fw2
python build_known_pairs.py --parts $P/Part_1/part-00000.parquet $P/Heldout/part-00000.parquet --out out
```

Result: 433 documents with at least 3 lines and 200 characters on each side (343 with an English half, 90 Hindi).

**Finding: these are mostly not translations.** Read by hand, most are a Sanskrit news story (`sanskritvarta.in`) with
an embedded English or Hindi tweet on the same event, a Sanskrit story with an English blurb, or Hindi commentary.
Even the "interleaved" ones (each translation line right after a Sanskrit line: 138 documents, 697 line pairs) are
mostly news paragraphs alternating with tweets; a few are real translations (a stava with its English rendering,
greetings with their meaning). So `DB-H3-001` removes embedded foreign-language text more than translations, and this
pack cannot supply reliable translation positives. The 433 pairs are kept as **same-topic hard negatives**: the case
H3 must keep (E5a: "a same-topic page is kept").

## 2. `labse_check.py` (to run on your machine: it needs Hugging Face)

Measures the encoder on
- **A, B: FLORES-200 devtest**, the same 1,012 sentences translated into English, Hindi, Sanskrit and Odia: true
  translations at sentence level, and as 8-sentence pseudo-documents scored with H3's coverage rule;
- **C: the 433 `ind-sa-fw2` pairs**: how many H3 would wrongly match, at each sentence threshold.

FLORES is an evaluation benchmark (G9 decontaminates against it): it is read here to test the encoder, never added to
training data.

```bash
pip install sentence-transformers datasets pyarrow numpy
hf auth login            # then accept the terms once at https://huggingface.co/datasets/openlanguagedata/flores_plus
cd /d/TheSchoolofAI/Capstone/Wk2/h3
python labse_check.py --pairs out/known_pairs.parquet --out out/labse
```

The model (about 1.9 GB) downloads on first use; CPU is fine (about 20k sentences, minutes). Output:
`out/labse/summary.json` (numbers and doc_ids only) and `out/labse/pair_scores.csv` (doc_ids and scores).

What to read in `summary.json`:
- `flores.<lang>-eng_Latn.p_at_1`: does the encoder find the right translation? Low for Sanskrit or Odia means the
  encoder is weak there (H3-i).
- `flores.<lang>-eng_Latn.true_pair_cosine` and `true_pairs_at_or_above`: where true pairs sit against the 0.7
  sentence threshold (H3-h).
- `pseudo_documents.true_qualifying_at_rule` vs `other_qualifying_at_rule`: at which sentence threshold true
  translations pass the 0.6 coverage rule and other blocks do not.
- `ind_sa_fw2_same_document_pairs.*.qualifying_at_rule`: the false-match rate on real same-topic pages.
- `highest_coverage_at_0.7`: 15 doc_ids to read by hand; real translations among them are the pack's true positives.

A different encoder (for example BGE-M3 or multilingual-e5) can be compared with `--model <name>`.
