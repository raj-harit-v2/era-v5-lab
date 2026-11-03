# Held-out set v1 (G5)

**Owner:** Deepjyoti Saha (G5). **Reviewers:** Shivanshu Thapliyal (G5 lead), TSAI.

This folder holds G5's held-out set, the fixed text on which models are scored in bits per byte
([`experiments/plan_v1.md`](https://github.com/theschoolofai/era-v5-lab/blob/main/teams/05-architecture/experiments/plan_v1.md)).
The held-out text is **one file, `data/heldout_v1.jsonl`**, with 15 slices one after the other.
This is the **full set**, built on 2 Nov 2026. [`results/heldout_v1.sha256`](../results/heldout_v1.sha256) names it.
It replaces the 300-document sample that this pull request first carried for harness testing.

## Purpose

- **Score the week-2 experiments.** Every arm of plan v1 (EXP-1 to EXP-3, the Muon screen, the attention arms, the T3 confirms) is scored
  on exactly the same text, so the winner rule compares like with like.
- **Score the final V5 model** (and the dry-run checkpoints) on the same text, with the same metric.
- **Check that the experiments were a faithful small-scale copy of the real thing.** The week-2 choices are made on small
  test models (T1 to T3) and a small training stream. Scoring the final model on the same held-out text shows whether
  those choices still hold at full size, on the real data mix. Bits per byte makes this possible: it does not depend on
  the model size or on the tokenizer.
- **Give the lab one fixed, reproducible, benchmark-free text** for any team that needs a perplexity check.

Because of the second and third points, the set is **permanent**: its bytes are frozen once the full set is built, and it
must never be trained on.

## Rules every source follows

1. A split its makers set aside (validation or test), so no one's *train* split contains it.
2. An accepted licence: [ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/) or [MIT](https://opensource.org/license/mit).
3. Not a benchmark: Team 9's fingerprint check
   ([`teams/09-evaluation/decontam/`](https://github.com/theschoolofai/era-v5-lab/blob/main/teams/09-evaluation/decontam/README.md)) flags 0 documents.
4. Not Team 1 or Team 2 data: their data is V5's own training data.
5. Matches the kinds of text in the lab's sample packs (the diagnosis packs listed below), so the score covers
   the same ground. The V5 training mix itself is not set; the pack names show how this set was put together.

## Layout

| Path | What |
|---|---|
| `data/heldout_v1.jsonl` | The held-out text: one file, 15 slices; each id starts with its slice |
| `data/heldout_v1_sources.jsonl` | **Source tracking**: where each document came from (see below) |
| `data/SHA256SUMS` | Checksums of both JSONL files (see "Checksums" below) |
| `data/heldout_manifest.json` | Selection rule, pinned dataset revisions, excluded documents with the reason, the file's documents, text bytes and sha256; per slice: dataset, part, id prefix, documents, text bytes, documents skipped for personal data |
| `heldout_decontam_v1.txt` | Output of Team 9's check on the file |
| `heldout_report.json` | The same result in the form the G5 harness (PR #190) requires for `--heldout-report`: the file's sha256, the fingerprint set id, `scope: full`, `matches: 0`, `docs_checked` |
| `build_heldout.py` | Rebuilds `data/` byte for byte |
| `.gitattributes` | Keeps the data files byte for byte on every operating system, so the sha256 values stay valid |

## Composition

| Slice | Id prefix | Dataset | Part | Docs | Text bytes |
|---|---|---|---|---|---|
| English web | `c4-val` | [allenai/c4](https://huggingface.co/datasets/allenai/c4) | en/c4-validation.00000-of-00008.json.gz | 140 | 247,056 |
| Indic: Hindi | `fw2-hi-test` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | hin_Deva test | 34 | 255,134 |
| Indic: Bengali | `fw2-bn-test` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | ben_Beng test | 27 | 265,042 |
| Indic: Tamil | `fw2-ta-test` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | tam_Taml test | 37 | 256,545 |
| Indic: Telugu | `fw2-te-test` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | tel_Telu test | 21 | 255,189 |
| Indic: Kannada | `fw2-kn-test` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | kan_Knda test | 38 | 250,459 |
| Indic: Malayalam | `fw2-ml-test` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | mal_Mlym test | 30 | 251,018 |
| Indic: Marathi | `fw2-mr-test` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | mar_Deva test | 38 | 250,524 |
| Indic: Gujarati | `fw2-gu-test` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | guj_Gujr test | 31 | 250,826 |
| Indic: Punjabi | `fw2-pa-test` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | pan_Guru test | 27 | 254,686 |
| Indic: Odia | `fw2-or-test` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | ory_Orya test | 53 | 225,421 |
| Indic: Assamese | `fw2-as-test` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | asm_Beng test | 20 | 253,230 |
| Math | `owm-test` | [EleutherAI/proof-pile-2](https://huggingface.co/datasets/EleutherAI/proof-pile-2) | open-web-math/test/test.jsonl.zst | 55 | 259,449 |
| Science | `pes2o-val` | [allenai/peS2o](https://huggingface.co/datasets/allenai/peS2o) | data/v2/validation-00000-of-00002.json.gz | 170 | 250,710 |
| Code (Python, C++, Go, Java, JavaScript, Rust) | `vault-<lang>-test` | [Fsoft-AIC/the-vault-function](https://huggingface.co/datasets/Fsoft-AIC/the-vault-function) | data/test/{python,cpp,go,java,javascript,rust} | 338 | 250,262 |
| **`data/heldout_v1.jsonl`** | | | | **1059** | **3,775,551** |

Text bytes = the sum of `len(text.encode("utf-8"))`, the denominator of bits per byte. The JSON quotes and line breaks
are not counted. Each slice takes documents in source order until about 0.25 MB of text is reached, so the last
document of a slice can take it slightly over.
To score a single slice, keep the lines whose id starts with its prefix.

### Why these sources

The last column names the lab's sample packs each source matches, for transparency. These are the diagnosis
packs, not a decided training mix: the V5 training mix is not set.

| Slice | Source | Why |
|---|---|---|
| English | [C4](https://huggingface.co/datasets/allenai/c4) `en`, validation | A released split of a cleaned web crawl; one of the most-reported language-model evaluation texts. Matches the English sample packs `en-dclm`, `en-fineweb-edu`, `en-nemotroncc`. |
| Indic (11 languages) | [FineWeb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2), test | A released test split of a large multilingual web crawl, set aside by its makers. It covers all 11 G3 languages. Matches the Indic sample packs `ind-*-fw2` (FineWeb-2). |
| Math | [OpenWebMath](https://huggingface.co/datasets/open-web-math/open-web-math) (in [Proof-Pile-2](https://huggingface.co/datasets/EleutherAI/proof-pile-2)), test | Web pages with mathematical content. ODC-By 1.0. Matches the math sample packs `math-finemath`, `math-megamath`. |
| Science | [peS2o](https://huggingface.co/datasets/allenai/peS2o) v2, validation | Academic papers. Matches the science sample pack `sci-finepdfs`. |
| Code | [The Vault](https://huggingface.co/datasets/Fsoft-AIC/the-vault-function) (function level), test | Built from permissively licensed GitHub code ([The Stack](https://huggingface.co/datasets/bigcode/the-stack)). Its test split covers Python, C++, Go, Java, JavaScript and Rust, the languages of the code sample packs `code-python`, `code-cpp`, `code-go`, `code-java`, `code-js-ts`, `code-rust`. Only functions whose repo licences are all permissive are kept. |

Not used, with the reason: Team 1/2 data (it is V5's training data); benchmarks such as FLORES, IN22, MILU, MMLU,
GSM8K, HumanEval and MBPP (lab rule); our own carve-out of FineWeb (not a released split); mC4 validation (no Odia
or Assamese); Sangraha, HPLT and CulturaX (no held-out split, and likely training sources); arXiv (licences vary per paper);
codeparrot-clean (unstated licences); CodeSearchNet (licence "other", widely used as a benchmark); The Stack v2 (gated, no
split); [Paloma](https://huggingface.co/datasets/allenai/paloma) (gated, mixed licences; a possible later slice to compare with outside models).

## How documents are chosen

Rows in the order the source stores them (code: the six languages in turn); text stripped; empty texts skipped; code only when every repo licence is permissive; a document with an email address, a phone number or a secret-looking string is skipped (no personal data in the repo, and pr-guard rejects emails); documents found in review are dropped by id (DROPPED_IN_REVIEW) and still count toward the size budget; stop at --docs documents or once --mb megabytes of text are reached. No shuffling, no other filtering.

Dataset revisions are pinned, so a rebuild gives the same bytes:

- [`EleutherAI/proof-pile-2`](https://huggingface.co/datasets/EleutherAI/proof-pile-2/tree/901a9273a770e9d4138c5ddd91802f9c5c6cdc4b) at `901a9273a770e9d4138c5ddd91802f9c5c6cdc4b`
- [`Fsoft-AIC/the-vault-function`](https://huggingface.co/datasets/Fsoft-AIC/the-vault-function/tree/505c679056e49a2a269b64777ee7c496d22e1440) at `505c679056e49a2a269b64777ee7c496d22e1440`
- [`HuggingFaceFW/fineweb-2`](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/tree/af9c13333eb981300149d5ca60a8e9d659b276b9) at `af9c13333eb981300149d5ca60a8e9d659b276b9`
- [`allenai/c4`](https://huggingface.co/datasets/allenai/c4/tree/1588ec454efa1a09f29cd18ddd04fe05fc8653a2) at `1588ec454efa1a09f29cd18ddd04fe05fc8653a2`
- [`allenai/peS2o`](https://huggingface.co/datasets/allenai/peS2o/tree/636a503e44a3ca1b58e01fb61eab0825cd574de0) at `636a503e44a3ca1b58e01fb61eab0825cd574de0`

Documents dropped after Team 9's check, with the reason (also in the manifest):

- `owm-test-000011`: shares 13-word runs with LiveCodeBench release_v6 items (coverage 1%); fingerprints v1, 1 Nov 2026

Documents dropped in the G5 lead's review (2 Nov), because they hold a phone number or an email address that the
filter did not catch (US-style numbers, a number written in Odia digits, and the `email@example.com` placeholder that
FineWeb puts where it removed an email). They still count toward their slice's size budget, so every other document
stays where it was (also in the manifest and the script):

- `c4-val-000018`: phone number (US format), lead review of PR #191, 2 Nov 2026
- `c4-val-000030`: phone numbers (US format), lead review of PR #191, 2 Nov 2026
- `c4-val-000059`: phone number (US format, dots), lead review of PR #191, 2 Nov 2026
- `c4-val-000094`: phone number (US format), lead review of PR #191, 2 Nov 2026
- `fw2-or-test-000030`: email address (email@example.com placeholder), lead review of PR #191, 2 Nov 2026
- `fw2-or-test-000046`: phone number written in Odia digits, lead review of PR #191, 2 Nov 2026

So English ends at about 247 KB and Odia at about 225 KB, a little under 0.25 MB. Bits per byte is a rate and the
winner rule averages each Indic slice as its own number, so the smaller slices keep the same weight; only their
estimate is slightly less precise.

**Known limit of the filter.** It removes emails, Indian mobile numbers, `+` international numbers and secret-like
strings. It does not yet catch US-style numbers, numbers written in Indic digits or the `email@example.com`
placeholder; v1 handles those by the id list above, and a scan of the final file with wider patterns finds none left.
Widen the filter before building any new set (v2 or a cleaned copy); changing it here would change v1's bytes.
It does not remove names or street addresses, as is usual for public web text.

## Format

One JSON object per line, UTF-8: `{"id": "...", "text": "..."}`. Ids are unique and say where the text came from:
`c4-val-000000`, `fw2-hi-test-000000`, `owm-test-000000`, `pes2o-val-000000`, `vault-py-test-000000`.

## Source tracking

`data/heldout_v1_sources.jsonl` has one line per document, in the same order and with the same `id` as
`heldout_v1.jsonl`, so any document can be traced back to its source, attributed, or removed:

| Field | Meaning | Example |
|---|---|---|
| `id` | joins to `heldout_v1.jsonl` | `fw2-hi-test-000003` |
| `slice` | the slice | `hi` |
| `dataset`, `revision` | Hugging Face dataset and pinned revision | `HuggingFaceFW/fineweb-2`, `af9c1333…` |
| `file`, `row` | the file in that dataset, and the row number in it (counting rows that were skipped) | `data/hin_Deva/test`, `3` |
| `source_id` | the source's own key where it has one: FineWeb-2 and peS2o `id`; for code `path@hexsha` | |
| `url` | the page URL (C4, FineWeb-2, OpenWebMath); for code, the GitHub repository | |
| `licence` | ODC-By-1.0, or for code the repository's licences (all permissive) | `Apache-2.0` |
| `text_sha256` | sha256 of the document's text, so anyone can check it was not changed | |

It is also the list the Data teams and Team 9 can use to keep these documents out of training: by URL and source id,
not only by our id. Documents whose URL or source id contains an email address or phone number are skipped like the
text itself.

## Checksums

- `results/heldout_v1.sha256` names the scored file, as plan v1 requires.
- `data/SHA256SUMS` holds the sha256 of both files:

  ```
  21c6e4b2df8dae9d69e254f4a00fc934d2a3c70f0675065a03724299d94312bb  heldout_v1.jsonl
  95585a25bdccb077130432d49b6427c5ff5f756d5b43b9c7033803326f65e0d6  heldout_v1_sources.jsonl
  ```

  Check it from `data/` with `sha256sum -c SHA256SUMS` (Linux, macOS, Git Bash), or in PowerShell with
  `Get-FileHash heldout_v1.jsonl -Algorithm SHA256`.

## Rebuild it

From the repo root (needs `pip install datasets zstandard`, and network access to Hugging Face):

```
python teams/05-architecture/heldout_v1/build_heldout.py --out teams/05-architecture/heldout_v1/data --mb 0.25
```

A rebuild into an empty folder gave the same `heldout_v1.jsonl`, `heldout_v1_sources.jsonl`, manifest and `SHA256SUMS`, byte for byte. TSAI jobs run without
network ([`JOB_REQUEST.md`](https://github.com/theschoolofai/era-v5-lab/blob/main/JOB_REQUEST.md)), so they read the committed files, not the script.

## Benchmark check (Team 9)

`heldout_decontam_v1.txt` is the output of Team 9's
[`decontam_check.py`](https://github.com/theschoolofai/era-v5-lab/blob/main/teams/09-evaluation/decontam/decontam_check.py) on `data/heldout_v1.jsonl`, full fingerprint set:

```
fingerprints v1 set_sha256 11e290a44d1467875fdf8bebc55eab21f0a6367f411aab98a4a027a546fd372e (full set)
docs 1059 flagged 0 (0.00%) by benchmark {}
```

It is repeated on fingerprints v2 (due Wed 4 Nov). TSAI decided (2 Nov) that Team 9 adds held-out v1 to fingerprints v2
as a protected set. That re-check must therefore leave out the held-out set's own fingerprints, or every document
would match itself; only the benchmark sets count.

`heldout_report.json` carries the same result for the harness, which refuses a quality run unless the report's
`heldout_sha256` equals the held-out file's sha256, `matches` is 0, `scope` is `full`, a `fingerprint_set_id` is given
and `docs_checked` equals the number of documents it reads. Checked with the harness's own reader from PR #190:
1059 documents read, the same 3,775,551 bytes, report accepted.

```
python teams/05-architecture/harness/train_week2.py ... --heldout-data teams/05-architecture/heldout_v1/data/heldout_v1.jsonl --heldout-report teams/05-architecture/heldout_v1/heldout_report.json
```

## What comes next

| When | What | Who |
|---|---|---|
| 2 Nov | **Delivered**: the full set, Team 9's check (0 matches), `heldout_report.json`, `results/heldout_v1.sha256` | Deepjyoti |
| From EXP-1 on | Every arm scored on it, with the plan v1 winner rule (below); every slice reported (lines selected by id prefix) | harness, arm owners |
| Wed 4 Nov | Re-check on Team 9's **fingerprints v2** (new cleaning rule `spec-v1`, plus Terminal-Bench 2 and BFCL v3); its `set_sha256` added next to v1's | Deepjyoti, Team 9 |
| Wed 4 Nov (TSAI, 2 Nov) | **Protection**: Team 9 adds held-out v1 to fingerprints v2 as a protected set, so the decontamination of the training shards also removes these pages; `heldout_v1_sources.jsonl` gives the URLs and source ids | Team 9 |
| When spec v1 code lands | **Cleaned copy** (`heldout_v1_clean`): Team 1 and Team 2's final cleaning run on the set, then Team 9's check. A separate file, reported as its own column; v1 stays raw | Deepjyoti |
| Later (v1.1, separate slices) | A whole-file code slice; possibly a Paloma slice to compare with outside models; possibly a "temporal" slice (text newer than any training crawl) | to be decided |

The v1 bytes never change once the full set is built. Anything new is a separate, named slice or file.

## Decisions for v1 (confirmed in the TSAI review, 2 Nov)

1. **Sources (frozen for v1):** C4 `en` validation; FineWeb-2 test (11 languages); OpenWebMath test; peS2o validation;
   The Vault test. A later change is a new, named set (v2), not an edit to v1's bytes.
2. **Size:** about 0.25 MB of text per slice, 15 slices, about 3.75 MB in all: "enough for the small arms and fast to
   score" (TSAI).
3. **Score (plan v1, TSAI 2 Nov):** every slice is reported. An arm wins on the mean bits per byte of three groups:
   English, code, and the mean of the 11 Indic slices. It must not be worse than the runner-up on code or on the Indic
   mean by more than the seed spread (seeds 1234 to 1236). Math and science are reported beside it.
4. **Permanent and kept out of training:** yes (TSAI). C4 validation and the FineWeb-2 test split come from the same web
   crawl as some training sources, so Team 9 adds held-out v1 to fingerprints v2 as a protected set.
5. **Raw for ever:** v1 stays raw, so every score compares the same text. A cleaned copy would be `heldout_v1_clean`,
   reported as its own column.
6. **Code** is function level in v1 (The Vault gives single functions with their docstrings).

## Licences and attribution

[C4](https://huggingface.co/datasets/allenai/c4), [FineWeb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2),
[OpenWebMath](https://huggingface.co/datasets/open-web-math/open-web-math) (via [Proof-Pile-2](https://huggingface.co/datasets/EleutherAI/proof-pile-2)) and
[peS2o](https://huggingface.co/datasets/allenai/peS2o) are under [ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/); users should also
follow the [Common Crawl terms of use](https://commoncrawl.org/terms-of-use). [The Vault](https://huggingface.co/datasets/Fsoft-AIC/the-vault-function)
is under [MIT](https://opensource.org/license/mit) and is built from permissively licensed code.
No text was changed except for stripping leading and trailing white space.
