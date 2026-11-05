# Romanised Indic (D2): share and detector, v1

Issue #213, part 1. How much of each Indic language in the `ind-*` packs is written in Latin letters (D2 in
`diagnosis/DISEASES.md`, for example Hindi as "aap kaise ho"), measured with a small detector that was tested on
100 documents readers had already labelled. Part 2, the cap proposal, will be `romanised_policy_v1.md`.

## Result

`romanised_share_v1.csv`: share of documents the detector flags, per language, on the full packs (500 documents per pack).

| lang | packs | docs | flagged | share |
|---|---|---|---|---|
| hi | 5 | 2500 | 17 | 0.68% |
| sa | 1 | 500 | 4 | 0.80% |
| gu | 1 | 500 | 3 | 0.60% |
| bn | 2 | 1000 | 2 | 0.20% |
| ta | 3 | 1500 | 3 | 0.20% |
| te | 3 | 1500 | 2 | 0.13% |
| kn | 3 | 1500 | 1 | 0.07% |
| ml, mr, or | 1, 2, 1 | 500, 1000, 500 | 0 | 0% |
| all | 22 | 11000 | 32 | 0.29% |

These shares are a lower bound: the detector finds 42% (readers' labels) to 64% (checked labels) of the D2 documents,
so the real share could be about 1.5 to 2.4 times the flagged one, roughly 0.45-0.7% overall instead of 0.29%
(for Hindi, about 1.1-1.6% instead of 0.68%).

Per pack (`romanised_share_by_pack_v1.csv`): ind-hi-fw2 1.4%, ind-hi-hplt 1.2%, every other pack 0.8% or less.

What this means:
- Romanised Indic is rare: about 3 documents in 1000 overall, and about 1 in 100 in the Hindi web packs (fw2, hplt).
- A flagged document is rarely romanised from start to end. Most are Devanagari (or other script) articles with
  romanised SEO headings ("Photo Se Background Kaise Hataye", "Aaj Ka Love Rashifal"), a reader comment, or a tweet.
  Longer romanised passages are in a Bengali tech forum thread, a Telugu story site, a Kannada phrasebook, a Tamil
  drug page, and Sanskrit verses in IAST (three ind-sa-fw2 pages and a Gita page in ind-gu-fw2).
- Most of the D2 documents the detector misses have only one or two romanised words (an SEO title, a short
  comment), so they add little romanised text even though they raise the document share.
- Counts per language are small (0 to 17 documents), so differences between languages below 1% are noise.

## The detector (`detector.py`)

1. Take the words in Latin letters, without URLs, emails, @handles, #hashtags and all-capital acronyms (ANI, AAP, EMI).
2. Count the ones on a short list of common romanised Indic words: hai, nahi, kaise, kya, aur, ke, ki, ko, se ... for
   Hindi, and a few for bn, mr, ta, te, kn, ml, gu. Words that are also English (in, to, me, is, na ...) are not on it.
3. Count the letters with IAST diacritics (ā ī ū ṛ ṃ ṇ ś ṣ ḥ ...), the usual romanisation of Sanskrit.
4. Flag the document when it has at least 3 list words, 2 of them different, or at least 5 IAST letters.

No model and no training data; `python3 detector.py "aap kaise ho, sab theek hai?"` shows what it matched.

## The test (`build_testset.py`, `eval_detector.py`, `eval_v1.md`)

`testset_100.csv`: all 52 documents that any reader marked D2 (76 D2 rows in 48 sheets of 22 packs, 37 of them in
ind-hi-hplt), plus 48 documents no reader marked D2: 24 drawn among documents with at least 10% Latin letters
(English text, names, URLs, so the detector meets hard cases) and 24 drawn from all others. Seed 0, and the draw does
not use the detector.

Ground truth is the readers' labels: a document is D2 when at least one reader marked it D2. Next to them are the
checked labels: 19 of the 52 reader D2 marks hold no romanised Indic phrase when read again (English text, or a proper
name only such as a newspaper, scheme or film title, romanised Arabic, or a table of accented letters), and
`checked_labels.csv` gives the reason for each. No negative was changed.

| labels | D2 docs | flagged | true pos | false pos | missed | precision | recall |
|---|---|---|---|---|---|---|---|
| readers' labels (ground truth) | 52 | 22 | 22 | 0 | 30 | 100% | 42% |
| checked labels | 33 | 22 | 21 | 1 | 12 | 95% | 64% |

Gold check: on all 1,957 gold documents in `teams/02-data-b/gold/` (17 packs; two readers marked each one clean, so
none is D2) the detector flags 0. Gold cannot measure recall, but it shows the detector does not fire on clean text.

- Missed (30 with readers' labels): 18 are reader D2 marks that point at English text or a proper name (for example
  ind-mr-fw2 rows 146 and 231); the other 12 are SEO titles or comments with one or two romanised words
  ("Vish Ke Dant", "Sariya Cement Ka Rate", "Shiksha k Odisha kya hai") or words not on the list ("1 no pic madhe").
  Every miss is listed in `eval_v1.md`.
- False alarms: none with readers' labels; one with checked labels (romanised Arabic with IAST-style accents, which a
  reader marked D2).
- Thresholds: 2 words instead of 3 raises recall to 48% (readers) / 70% (checked), still flags 0 gold documents, and
  flags 7 more documents on the full packs; 3 words was kept. The full table is in `eval_v1.md`.
- Precision on a test set that is half D2 is easier than on real packs, where D2 is rare (about 0.3%).

## Reproduce

```bash
cd teams/02-data-b/romanised
# packs/<pack_id>.parquet: the 22 ind-* sample packs; sheets/: readers' labels.csv
python3 ../tools/fetch_sheets.py --packs ind-hi-hplt ind-hi-fw2 ... --out sheets
uv run --with pyarrow python build_testset.py      # testset_100.csv
uv run --with pyarrow python eval_detector.py      # eval_v1.md
uv run --with pyarrow python share.py              # romanised_share_v1.csv, romanised_share_by_pack_v1.csv
```

`packs/` and `sheets/` are not committed (`.gitignore`): the packs are large and the sheets are other readers' files.
`fetch_sheets.py` refuses one sheet (PR #43, ind-mr-fw2/vpw): a note in it holds a stray terminal escape character,
and gh will not print it. That sheet was taken from the pull request's commit with git instead:
`git fetch https://github.com/theschoolofai/era-v5-lab.git pull/43/head` and
`git show FETCH_HEAD:diagnosis/submissions/ind-mr-fw2/vpw/labels.csv > sheets/ind-mr-fw2/vpw.csv`.
