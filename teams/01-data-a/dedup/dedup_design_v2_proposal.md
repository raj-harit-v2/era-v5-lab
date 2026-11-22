# Dedup v2 proposal: what v1 left open

**Lead:** Vijay Patil (Data A). **Owners:** Kunal Sinha and Aneesha Das (Data A dedup).

**Now (Weeks 3 and 4, 15–28 Nov):** dedup runs v1's rules, frozen, at scale; only items 5, 6 and 16 are done now, because the run needs them (item 5 just after TSAI's dedup run, so the job's pin holds). TSAI's v1 dedup run is done (#547, 17 Nov: 1,345 of 1,414,996 removed, 64 by rule 0, 0 held-out, as expected) and #255 is merged. H3's code is merged too (#610, 18 Nov), report-only; its first measurement job is #625, approved by Vijay Patil (18 Nov) and given TSAI's go-ahead with its ruling on H3 (19 Nov: rule 0 removal in v1 once E5c and the harm check pass; only direct edges remove, fixed in #663). #625 and the second-encoder job #666 were merged on 20 Nov and wait for TSAI's runs. **Week 4 (22–28 Nov)** runs the merged pipeline on **corpus-v1**, the real training data, for dry run 2; H3 stays report-only in that run, because E5c has not run yet (`h3_design_v1.md`, "Decisions"). Plan and requirements: `dedup_v1_1_plan.md`. Everything else in this file is the backlog for after training starts.

**Status:** final draft for team review, 15 Nov 2026 (first draft 13 Nov); updated 15 Nov for the new Indic sources (#461, with Shankar Pandala's review), Aneesha Das's H3 draft (#44 on Vijay's fork) and G2's note that it has no translated-pair work; updated 16 Nov for G10's licence rulings (all 38 packs), the BGE-M3 encoder check (H3-h, H3-i), a first containment count on the rerun (item 8) and item 5 moving after TSAI's dedup run; updated 18 Nov for H3 v1.1 merged (#610), the end-to-end check of `h3.py` → `dedup.py`, the E5c job request (#625) and the forecast of TSAI jobs; updated 19 Nov for the licence map (#630), E4's Kannada labels (item 3), TSAI's H3 ruling on #625 and the direct-edge fix (#663); updated 21 Nov for #625 and #666 merged, G10's sign-off on the H3 encoders (#634), the LaBSE pin, the H3 harm test's result, the CUDA timing from the 38-pack rehearsal and the week-4 work order (H3 is week-4 task 3, in `h3_design_v1.md`) (Kunal Sinha and Aneesha Das, Data A dedup). Nothing here changes v1, its job request or PR #255. v1 runs as agreed; each item below starts only after its own review.
**Builds on:** `dedup_design_v1.md` (how duplicates are found), `source_priority_v1.md` (which copy survives), `results_v1.md` (the numbers) and Sourav Dhar's pipeline (`teams/01-data-a/pipeline/`, which applies the remove list with `apply_dedup.py`). H3 has its own design, `h3_design_v1.md` (Aneesha Das, draft); this file only adds to it.

Every v1 number quoted here comes from TSAI's 5 Nov run or the local runs in `results_v1.md`. The 5 Nov run is superseded by the rerun on the #244 cleaning, so each number is checked again on the rerun before any item below is decided.

## Summary

Items are split by what they need. **v1.1** items change a rule or a setting of the existing method; each needs evidence and one overlap run, nothing new to build. **v2** items add a new method or a new rule and need their own experiment first.

| # | Item | Release | Why (v1 evidence) | Needs |
|---|---|---|---|---|
| 1 | Same-URL pairs count as H2 at ≥ 0.80 | v1.1 | A same-URL math copy scored 0.894 and was missed; two true math copies sharing a URL were rejected by the numbers rule | Team decision, overlap run |
| 2 | Math numbers rule on the body only | v1.1 | The rule rejected true copies whose only numeric difference was a date line or a number in the title | Team decision, overlap run |
| 3 | Indic length minimum | v1.1 | The 50-word minimum rejects 135 near-identical Indic pairs (69 documents); 19.9% of Indic documents are under 50 words. Kannada (18 Nov): 20/20 template, so the minimum stays there | E4 reader labels (Telugu, Tamil), overlap run |
| 4 | Code threshold (0.85 on tokens) | v1.1 | "Under review" in v1; `code-rust` has 530 qualifying token pairs but only 3 word pairs ≥ 0.80 | Hand review of code pairs |
| 5 | Summaries record code SHA-256, git commit and part hashes; `remove_list.csv` keeps its five columns | v1.1 | Sourav's runner adopts overlap and dedup but cannot record their code (`code_sha256` stays null); `apply_dedup.py` accepts only the exact five-column header | Code change, tests |
| 6 | Config-only updates: licence map, Data B pack order | v1.1 | G10's table on `main` (#524, 17 Nov) lists all 38 packs in Stage 0, `TSAI reserves`; the licence map is filled in #630 (18 Nov), outputs unchanged | #630 merged; a G10 row and a `pack_order` place for any pack beyond the 38 |
| 7 | **H3: translations across languages** | v1.1 in `h3_design_v1.md` (Aneesha); recheck in v2.0 | Out of scope in v1 (TSAI, 5 Nov); Sanskrit packs are known to carry translations | H3-a to H3-e merged (#610); H3-f ruled by TSAI (#625, 19 Nov); H3-g to H3-m after E5 |
| 8 | Containment for truncated copies | v2 | E3 limit: a copy keeping 85 of 100 words is caught, 80 of 100 is missed | Experiment on the overlap outputs |
| 9 | Indic-aware shingles | v2, only if 3 is not enough | Word 5-grams were set on English (Risk 2) | Experiment on Indic packs |
| 10 | Survivor rule: the copy cleaning changed least | v2 | Dropped from v1: no per-document record of fixes | Experiment on the rerun's groups |
| 11 | Scale to the full data: MinHash + LSH agreement test | v2, sooner if #461's sources join | Exact all-pairs took 56 min on 1.4 M documents; the full data is larger, and #461 adds more Common Crawl | Agreement test on the sample |
| 12 | Training ablation of the cross-pack pass | v2, conditional; likely triggered by #461 | Only worth running where cross-pack removes ≥ 1% of a pack; on the sample none does, but MADLAD-400, IndicCorp and Sangraha unverified overlap fw2 | Counts with the new packs |
| 13 | **Pack order for new packs:** a rule, not a hand-made list | Before any new pack joins | v1 ranks only the 38 sample packs; #461 proposes 15 new sources | Team decision; Data B's clean shares |
| 14 | **Packs that are not documents** (word pairs, lexicons, single sentences, speech transcripts) | Before those packs join | #461: Aksharantar, Dakshina, BPCC, Shrutilipi, IndicVoices | A decision per pack |
| 15 | **Licence map for the new sources** | Before those packs join | #461: card text and tag disagree for Aksharantar and MADLAD-400; BPCC's mined part repackages NC data | G10's rulings |
| 16 | **Pipeline contract** with Sourav's runner: remove-list checks, summaries, the dedup job as a `run.json` | Now, for every release | `apply_dedup.py` stops on a list that breaks its checks; `pipeline/open-items.md` lists 7 dedup items | Code and docs; answers to Sourav |

**Not dedup, handed on:**
- Empty documents (7 in v1) are a spec v1.1 cleaning rule.
- Template pages that pass the thresholds (slideserve.com, name/date templates) are a quality-filter problem.
- Benchmark contamination belongs to F2 (G9's fingerprints).

## v1.1: rule and setting changes

All of v1.1 goes into **one** overlap run, after TSAI's v1 dedup job, so that v1's remove list stays the record for the experiment and v1.1's effect can be reported as a difference: documents removed or kept, per pack and per item.

### 1. Same URL

**Change:** a pair whose documents have the same non-empty `url` counts as an H2 duplicate at Jaccard ≥ 0.80, in every family. This overrides the math numbers rule and the 0.90 math threshold for that pair only.
**Evidence:** reference.com's "examples of quadrilaterals" is in `math-finemath` train and `math-megamath` held-out with the identical URL, at 0.894. Two true math copies were rejected by the numbers rule; both share their URL.
**Check before deciding:** list every same-URL pair at 0.50–0.90 on the rerun and read them. A site that serves different content at one URL (a feed, a search page) would make this rule wrong for that site.

### 2. Math numbers rule on the body

**Change:** compare the multisets of numbers in the body only, ignoring the title and first line.
**Evidence:** the two rejected copies differed only in a date line or a number in the title.
**Check:** the worked-example pairs that the rule correctly keeps apart (math E1) must still be kept apart.

### 3. Indic length minimum

**Change:** a lower minimum for `ind-*` packs, or a minimum in shingles instead of words, set from E4's labels.
**Evidence:** across all `ind-*` packs the 50-word minimum rejects 135 near-identical pairs (69 documents); the three `sangraha-s` packs lose almost all their pairs (106 pairs, 35 documents, 4 clusters, each pair differing by 1–5 words per side).
**Needs:** the native readers' labels (issues #392–#395) on sheets rebuilt from the rerun. If they label the pairs as copies, lower the minimum. If they label them as templates, v1's minimum stays.
**Bound:** whatever the labels, the change affects at most 69 Indic documents on the sample.
**Kannada, 18 Nov (#393, Ravi Naik):** all 20 `ind-kn-sangraha-s` pairs labelled **template** ("different headword; same
dictionary-notice body"): 10 documents of 17–41 words, Jaccard 0.82–0.94, 19 of the 20 pairs in one cluster. A 30-word
minimum would have made 19 of them H2 duplicates, so for Kannada v1's 50-word minimum stays. Telugu (32 pairs, #394)
and Tamil (54 pairs, #395) are still with readers.

### 4. Code threshold

**Change:** keep, raise or lower 0.85, from a hand review of about 20 code pairs on each side of the threshold, as was done for math. Include a sample of `cadj-commits`, the pack with the most duplicates.

### 5. Summaries and the remove list

The remove list is applied by Sourav Dhar's `apply_dedup.py` (`teams/01-data-a/pipeline/`, #37 and #46 on Vijay's fork). Its checks set this item:
- **`remove_list.csv` keeps exactly its five columns** (`pack_id, split, part, row_in_part, doc_id`). `apply_dedup.py` stops on any other header, so no `reason` or `stage` column is added. The rule that removed each document is already in `dedup_log.jsonl` (`rule`, `stage`, `priority_rule`), and H3 removals are logged there too.
- **`overlap_summary.json` and `dedup_summary.json` record `code_sha256` and the git commit** of the script that wrote them. The runner adopts the overlap and dedup jobs as TSAI ran them, and without these fields its `cleaning_pipeline.json` has `code_sha256: null` for both (Sourav's open items).
- **`overlap_summary.json` records the SHA-256 of every input part** (today `checksum_verification: deferred`), and `dedup_summary.json` carries them on. `apply_dedup.py` checks the `doc_id` and `pack_id` of every listed row, which catches a list made from other parts; the hashes also catch a part whose unlisted rows changed.

### 6. Config-only updates

G10's table on `main` (#524, 17 Nov) has a Stage 0 row for every sample pack, all `TSAI reserves` (`en-dclm` stays In, its "research purposes only" line read as a disclaimer and noted for TSAI's Gate 3). **Done in #630 (18 Nov):** `dedup.json` lists all 38 packs in `licence_usable` with `default_licence_usable: false`; on the rerun's files every output is byte-identical, and a new test checks that every pack in `pack_order` has a licence entry (`jobs/logs/2026-11-18-dedup-licence-check.txt`). If TSAI excludes a pack later, set it to `false`. If the Data B lead asks for another order of their 25 packs, change the list in `dedup.json` and `source_priority_v1.md`. Neither needs an overlap run: rerun `dedup.py`, and its tests, on the same overlap outputs.

## v2: new methods

### 7. H3: translations across languages

H3 has its own design: `h3_design_v1.md` (Aneesha Das, draft; #44 on Vijay's fork), for dedup v1.1. It finds candidates with LaBSE and URL keys and decides by sentence coverage (aligned sentences ÷ sentences of the shorter document). That replaces the chunk-embedding sketch this file had on 13 Nov.

The points below split into what Aneesha's v1.1 design should take up before its first TSAI run, and what is rechecked in v2.0 once E5's measurements exist.

**For H3 v1.1 (owner: Aneesha Das, in `h3_design_v1.md`; raised on #44).** H3-a to H3-e are implemented and merged in #610 (18 Nov, `85fa92e`): `h3.py` reads all documents and removes nothing, its `h3_matches.csv` header is exactly `h3_join.py`'s, parallel packs are handled in `h3_join.py`, and the FLORES checks are in `h3_checks/`. H3-f was asked on #610 (18 Nov) and ruled by TSAI on #625 (19 Nov): see "TSAI's ruling" below.

| # | Rule | Why |
|---|---|---|
| H3-a | **Keep H3 out of the survivor rules.** Form the H1/H2 groups first. An H3 edge may only remove a train copy of a held-out document (rule 0), and only the train document H3 itself matched with the held-out document: no removal through an H1/H2 group (TSAI, 19 Nov; fixed in #663). Every other H3 pair is reported, not removed | Otherwise rules 1–4 remove one language's copy, and rule 3 ("longer") does not compare across scripts |
| H3-b | **One `dedup.py` run.** `h3.py` reads all documents of its packs (no `exclude`); `overlap.py` and `h3.py` are independent; one `dedup.py` run reads both match files and writes one remove list | Sourav Dhar's pipeline ask; excluding H1/H2 removals needs a second `dedup.py` run and saves little (0.095% removed on 5 Nov) |
| H3-c | **Keys.** `h3_matches.csv` carries `(pack_id, split, part, row_in_part, doc_id)` | No join on `h3_docs.parquet` rows; matches the remove list's key |
| H3-d | **Parallel packs are not H3 duplicates.** No H3 edge between two documents of the same parallel pack (Pralekha, BPCC human parts); pairs with other packs are reported as usual | They are translations on purpose (#461) |
| H3-e | **Real known pairs.** Positives from FLORES-200 devtest (the same sentences in English, Hindi, Sanskrit and Odia; an evaluation set, read to test the encoder, never trained on). Hard negatives from `ind-sa-fw2`: its documents split by `DB-H3-001` into Sanskrit and "translation" lines are mostly a Sanskrit story with an embedded English or Hindi tweet on the same event (433 pairs, checked by hand on 15 Nov), the same-topic case H3 must keep. Scripts: `h3_checks/build_known_pairs.py`, `labse_check.py` (how it was run: below) | E5a uses a fake encoder; `DB-H3-001` removes embedded foreign-language text more than translations, so it cannot supply positives |
| H3-f | **Settled by TSAI (#625, 19 Nov).** Rule 0 removal is on for v1 (`h3.remove: true`) once E5c and the harm check both pass; until then H3 is report-only. Scope: Indic–English and Sanskrit–Hindi, prose packs only; Data A ↔ Data B stays out of v1. Only direct edges remove. Sanskrit's encoder and threshold wait on E5a′ (a second encoder) and E5d. Pralekha-type multi-language packs are designed later. LaBSE's licence sign-off (G10) is pending but not blocking | Asked on #610 (18 Nov), with Shankar Pandala's note (15 Nov) that keep-or-remove was not ruled. G2 has no pair finder, no LaBSE/IndicTrans2 runs and no H3 review pack, so H3 is Data A's alone; G2's translation work rates quality (#440), and its proposal has 0% translated text until TSAI decides at Gate 3 |

**Rechecked in v2.0 (after E5c and E5d)**

| # | Question | Evidence it needs |
|---|---|---|
| H3-g | Is anything removed beyond rule 0, for example machine-translated copies (D4/D5)? Which copy survives? | E5d labels by pair type; a TSAI decision |
| H3-h | Thresholds per language pair (coverage 0.6, sentence cosine 0.7, `doc_floor` 0.5 are provisional). **Measured 15 Nov** (`h3_labse_check_results_v1.md`, run steps below): at 0.7, LaBSE finds 100% of Hindi and Odia FLORES translations but only 29% of Sanskrit–English and 19% of Sanskrit–Hindi; at 0.5 Sanskrit rises to 96% / 89%, but 3 of the 7 real-page matches are not translations. **BGE-M3, 16 Nov** (`h3_bge_m3_check_results_v1.md`): at 0.7 it finds 82% of Sanskrit–English and 95% of Sanskrit–Hindi blocks, Hindi and Odia stay at 100%, and 6 of its 8 real-page matches are translations, so one threshold fits every pair | E5d's sweep and hand review, per pair; a margin score with LaBSE |
| H3-i | The encoder: LaBSE or an alternative, per language. **Measured 15 Nov:** Odia and Hindi fine (P@1 1.0 against English); Sanskrit found (P@1 0.95–0.98) but with low cosines (median 0.69). **BGE-M3, 16 Nov:** Sanskrit P@1 0.99, true-pair median 0.74–0.78; but unrelated text also scores higher (best wrong match median 0.57 against LaBSE's 0.41), so `doc_floor` needs retuning (about 0.6), and it is about 8 times slower on CPU (7,255 s against 863 s) | A Sanskrit reader's labels on BGE-M3's 16–27 candidates at 0.5–0.6; its cost on TSAI's GPU |
| H3-j | Head-only retrieval (first 4 sentences, mutual top 3): does it miss pairs on sites whose pages share their opening lines? | The share of URL-found pairs that retrieval also finds (E5b) |
| H3-k | Coverage over at most 16 sentences: is that enough for long documents? | Coverage on long known pairs |
| H3-l | Second opinion: translate-then-embed on a sample, rather than translate-then-H2. It beat a multilingual encoder in Pasch, Petridis and Cutura (arXiv 2406.13695), 82% against 60% F1 | Agreement with sentence coverage on the E5d sample |
| H3-m | Wider scope: Data A ↔ Data B pairs (out of v1, TSAI, 19 Nov), more language pairs, Pralekha-type packs and #461's new packs | v1.1's counts and cost per pair |

**H3 encoder check, 15 Nov (measurement only; results in `h3_labse_check_results_v1.md`)**

What was run, and how to repeat it. Scripts and README: `h3_checks/` (`build_known_pairs.py`, `labse_check.py`,
`README_h3_checks.md`). Document text stays in a local `out/` folder outside the repo; only numbers and doc_ids are
reported.

1. **Same-page pairs from `ind-sa-fw2`** (no model needed; 7 s):
   `python build_known_pairs.py --parts <raw ind-sa-fw2 parts> --out out`. It splits each raw document (week-1 pack,
   5,963 documents) into its Sanskrit lines and the lines `DB-H3-001` calls translations. Result: 433 pairs (343 with
   an English half, 90 Hindi). Read by hand, most are not translations (a Sanskrit news story with an embedded tweet on
   the same event), so they serve as same-topic hard negatives; `DB-H3-001` cannot supply positives.
2. **The encoder on Hugging Face models and data** (laptop CPU, 863 s; needs internet access to Hugging Face):
   - Prerequisites, once: in a Python venv, `pip install sentence-transformers datasets pyarrow numpy`; `hf auth login`
     with a read token; accept the terms on the gated dataset page
     `https://huggingface.co/datasets/openlanguagedata/flores_plus`.
   - Run: `python labse_check.py --pairs out/known_pairs.parquet --out out/labse`. The model
     (`sentence-transformers/LaBSE`, about 1.9 GB) downloads on first use into the Hugging Face cache.
   - If it stops with `DatasetNotFoundError: ... is a gated dataset`, the terms were not accepted (or the token is for
     another account). On Windows, a warning about symlinks is harmless.
   - Positives: FLORES-200 devtest, 1,012 sentences in English, Hindi, Sanskrit and Odia (an evaluation set, read to
     test the encoder and never used as training data), as sentences and as 8-sentence pseudo-documents. Negatives:
     other FLORES blocks, and the 433 same-page pairs. H3's own settings throughout (mutual best match, sentence
     threshold swept 0.5 to 0.9, coverage rule 0.6).
3. **Result in one line:** Hindi and Odia are fine at the draft's 0.7 (100% of translated blocks qualify, 0% of other
   blocks); Sanskrit is found (P@1 0.95 to 0.98) but at 0.7 only 29% of Sanskrit-English and 19% of Sanskrit-Hindi
   blocks qualify, and at 0.5 3 of the 7 real-page matches are not translations (H3-h, H3-i).
4. **BGE-M3, 16 Nov** (`h3_bge_m3_check_results_v1.md`): the same command with `--model BAAI/bge-m3` (7,255 s). At 0.7
   it finds 82% of Sanskrit-English and 95% of Sanskrit-Hindi blocks (Hindi and Odia 100%, other blocks 0%); 6 of its 8
   real-page matches are translations. Its cosines run higher for unrelated text too, and it is about 8 times slower.
5. **Next:** a margin score in place of the plain cosine, with LaBSE (`--progress` prints stage times).

**End-to-end check, 17 Nov** (local, `h3_e2e`): Aneesha's `h3.py` on two 5 Nov cleaned parts (5,639 Sanskrit train documents
against 130 Hindi held-out), then `dedup.py` with the `h3` key on the 5 Nov overlap outputs. 128 pairs were verified and
none qualified, even with the thresholds lowered to 0.5 and 0.4 (best coverage 0.357). `dedup.py` accepted the file
(header, keys), reported `h3: 0 matches`, and `remove_list.csv` stayed byte-identical to the 5 Nov list (`913e66a6…`).
The same run with pairs is still to do.

**E5c, 18 Nov** (#625): the measurement job request: `h3.py` at `85fa92e` on the #244 cleaned sample, report-only, sa–en,
sa–hi, hi–en and or–en on prose packs (about 348,000 comparable documents), sentence threshold 0.7 and 0.55 for the
Sanskrit pairs (provisional), 1 GPU, at most 120 minutes. A local smoke run of the same config passed (200 documents per
pack, 0 qualifying, 81 tests); on a laptop CPU the full scope would take about 30 hours.

**TSAI's ruling, 19 Nov** (#625; H3-f). Vijay Patil approved E5c on 18 Nov; TSAI gave the go-ahead with this ruling:
- **Removal:** rule 0 removal for v1 once E5c and the harm check both pass; report-only until then. Tonight's first
  training job stays report-only.
- **Scope:** Indic–English and Sanskrit–Hindi, prose packs only (#625's scope). No Data A ↔ Data B in v1 (H3-m).
- **Direct edges only:** no transitive removal. `h3_join.py` on `main` removed every train survivor of the matched
  document's H1/H2 group; #663 (19 Nov) removes only the matched train document, if H1/H2 kept it. Two new outcomes:
  `already_removed` (H1/H2 had removed it) and `reported_indirect` (a train ↔ train match where a side's group holds a
  held-out copy). `dedup_summary.json` gains `h3.train_docs_targeted`, the same in report-only and remove mode.
- **Sanskrit:** encoder and threshold not decided; E5a′ is BGE-M3 (16 Nov, H3-h, H3-i), then E5d's readers. BGE-M3 on
  E5c's Sanskrit pairs on the real sample is job #666 (merged 20 Nov, revision `5617a9f`, report-only).
- **Later:** Pralekha-type packs.
- **Licence:** G10 signed off LaBSE (Apache-2.0) and BGE-M3 (MIT) as models of the data pipeline (#634, 20 Nov).
- **LaBSE pin:** jobs stage revision `836121a` (`model.safetensors` `77d8e1…`), not a `SentenceTransformer.save()` copy
  (the 17 Nov local run's `deaceb…`: the same 199 weight tensors). Agreed on #625, 20 Nov.
- **CUDA timing:** in TSAI's 38-pack rehearsal (#599) `h3.py` read all 91,559 documents of `ind-sa-fw2`, `ind-hi-fw2`
  and `en-fineweb-edu` in 205.7 s on CUDA (fp16), 0 qualifying at 0.7 (`jobs/logs/2026-11-19-first-training-rehearsal-38packs/`).

**The harm check for H3** (Aneesha Das, 19 Nov): on sample v0 it can only be `not_testable` (no gold document is in the
sample; her 12-pack run gives `gold_ids_in_input: 0`), so E5c cannot pass it. Proposed: a separate H3 harm test on the
diagnosis packs with the gold on `main` (`teams/01-data-a/gold` for English, `teams/02-data-b/gold` for Hindi and
Sanskrit), `h3.py` then `dedup.py` with `h3.remove: true` in the ruled scope, run on #663. It reports H3's removals
next to the status, since a pass with no H3 removal tests nothing. `ind-or-fw2` has no gold set. Turning removal on
later touches `pipeline/stage_args.py` (hard-codes `remove: False`), `run_pipeline.py`'s check that H3 is report-only,
the `h3` section of `dedup.json` and the first-training job request, in their own PR.

**Result, 19 Nov** (`jobs/logs/2026-11-19-h3-harm-diag-local.txt`, on #663): pass with each language held out in turn,
0 of 1,308 gold documents removed. No pair reached coverage 0.6 (highest 0.188; highest with a gold document 0.143), so
`h3.train_docs_targeted` is 0 and H3 removal itself was not tested. A looser stress run (coverage about 0.18 and 0.12)
would make H3 remove some documents on the gold packs.

**Asked of TSAI on #625, 19 Nov** (no answer by 21 Nov; `h3_design_v1.md` records our proposed reading of each):
1. Direct edge: H3 itself matching a held-out document with a train document (#663's reading); a match to a train copy
   of a held-out document is reported, not removed. Right?
2. Does the separate harm test on the diagnosis packs count as "the harm check passes"?
3. Odia has no gold set: does or ↔ en stay report-only when removal turns on?
4. Should E5d label candidates from both encoders (LaBSE and BGE-M3)?

### 8. Containment for truncated copies

**Problem.** Jaccard compares two documents as wholes, so a truncated copy is missed once it keeps less than about 80% of the text (E3: on a 100-word text, keeping 85 words scores 0.84 and is caught, keeping 80 scores 0.79 and is missed).

**Change.** Score pairs also by containment: shared shingles ÷ shingles of the shorter document. `overlap.py` already computes the shared count of every pair and the shingle count of every document, so containment costs no new pass. Two things do change:
- **The pair floor.** `overlap.py` keeps only pairs at Jaccard ≥ 0.50. A copy that keeps 40% of the text has a Jaccard near 0.40 and is dropped before any rule sees it, so containment pairs need their own floor.
- **A guard against short texts inside long ones.** A quote, a licence block or a boilerplate paragraph is fully contained in many long documents and is not a copy of them. The guard is a minimum length for the shorter document, plus the family's existing rules.

The survivor is unchanged: rule 3 already keeps the longer copy.

**First count, 16 Nov** (TSAI's rerun on the #244 cleaning, `overlap_pairs.csv`): pairs whose containment is at least 0.90 but which v1 does not match.

| Family | Pairs | Shorter document about 50 words or more |
|---|---:|---:|
| Code | 916 | 891 |
| Indic | 321 | 113 |
| Math | 302 | 299 |
| Prose | 19 | 14 |
| Across families | 5 | 5 |

At least 1,563 pairs, mostly code and math; prose hardly changes, and most short Indic pairs belong to item 3. It is a lower bound: `overlap_pairs.csv` keeps only pairs at Jaccard ≥ 0.50, so copies truncated to less than about half are not in it. None has been read yet.

**Experiment.** On the rerun's outputs:
- Count pairs at containment ≥ 0.90 that Jaccard misses, per family.
- Read 20 of them.
- Add known pairs to `tests/test_known_pairs.py`: truncated copies at 70%, 50% and 30%, which must be caught, and a quoted paragraph inside a long page, which must be kept.

### 9. Indic-aware shingles (only if item 3 is not enough)

Whitespace word 5-grams were set on English. If E4's readers find copies that a lower word minimum still misses, or false matches from long agglutinative words, try shingles that do not depend on word boundaries: character n-grams of the H1 key, or 5-grams of a tokenizer's subwords such as G3's. Compare the two on the E4 pairs and on Indic gold. The harm check must stay at zero gold removed.

### 10. Survivor rule: the copy cleaning changed least

From `source_priority_v1.md`, "Not used in v1".
- **Rule:** among copies that tie on rules 0–3, prefer the one whose cleaned text differs least from its raw text, for example 1 − `difflib` ratio, measured only for the pairs dedup finds.
- **Why it's feasible:** raw and cleaned text share a `doc_id`, so no change to the cleaning tools is needed.
- **Placement:** after rule 3 (completeness) and before rule 4 (pack order), so it can only change survivors that pack order decides today.
- **Experiment:** count how many of the rerun's groups it would decide differently, and read those.

### 11. Scale: MinHash + LSH agreement test

Exact all-pairs scoring ran in 56 minutes and 9.6 GiB on 1.4 M documents. v1 keeps MinHash + LSH as the fallback for a run that does not fit. Before it is ever needed, measure on the sample how many of the exact method's qualifying pairs MinHash + LSH finds at a given number of permutations and bands, and at what cost. Then the switch is a measured choice, not a guess. Exact scoring stays the default while it fits.

### 12. Training ablation (conditional)

Unchanged from v1. Train small proxy models with and without the cross-pack pass only where cross-pack removes at least 1% of a pack. Recheck this on the full data's counts.

## New sources (#461): what dedup needs before they join

PR #461 (Srinivasan Govindaraj, Data B, `teams/02-data-b/indic_sources_v1.md`) lists 9 new Indic datasets (N1–N9) and 6 extensions of sources the lab already has (its E1–E6). v1 is unaffected: it covers only the 38 sample packs. Before any of these packs joins, dedup needs the following.

### 13. Pack order for new packs (rule 4)

**Problem.** Rule 4 is a hand-made list of the 38 sample packs: Data A in `clean.py` order, then Data B in alphabetical order. A new pack has no place in it, and a hand-placed list will not scale to 50+ packs. Alphabetical order also decides today that an `fw2` copy beats a `sangraha-v` copy of the same page, with no reason behind it.

**Proposal.** Replace the list with a rule. Rank packs by their measured clean share (Data B measures it per pack in `native_indic_share_v1.md`. On the rebuilt gold, #439: 85.0% for `ind-hi-indiccorp`, 25.3% for `fw2`, 4.7% for `sangraha-s`, 7.4% for `ind-hi-hplt`. The rule must read the current version of that file, since the numbers moved when the gold was rebuilt; #461's figures came from the 2 Nov gold). Packs without a measurement go after measured ones, in a fixed fallback order: curated sources (Wikipedia, Wikisource, IndicCorp, Sangraha verified) before raw crawl (`fw2`, MADLAD-400, Sangraha unverified). Ties keep v1's order. The ranking is computed once per run and written into `dedup.json`, so a run stays reproducible.

**Check.** On the rerun's groups, count how many survivors the new order would change, and read a sample of them: the surviving copy should look cleaner.

### 14. Packs that are not documents

**Problem.** v1's family rules assume documents: prose needs 50 words for H2, and shorter documents get H1 only. Several #461 sources are not documents:
- Aksharantar: native/romanised word pairs.
- Dakshina: a lexicon and short hand-romanised sentences.
- BPCC: single translated sentences.
- Shrutilipi and IndicVoices: speech transcripts, often short.

**Proposal.** A decision per pack, recorded in `dedup.json`:
- **Excluded from dedup:** Aksharantar and Dakshina's lexicon. They are for romanisation (D2) work, not pretraining text, and exact repeats of a word pair carry no harm.
- **H1 only:** BPCC sentences, Dakshina sentences and the speech transcripts. Exact repeats are removed; near-duplicate scoring of single sentences would mostly match common phrasing.
- **Normal rules:** every document-level source (Wikipedia, Wikisource, Pralekha, MADLAD-400, IndicCorp, FinePDFs, Sangraha).

Parallel packs (Pralekha, BPCC) are also exempt from H3 within the pack (H3-d, item 7).

### 15. Licence map for the new sources (rule 1)

Rule 1 already treats permissive and CC-BY-SA licences as usable, so most of #461's In list needs no change. Three need G10's ruling before they go into `licence_usable`:
- **Aksharantar:** the tag says only "cc"; the card text says CC-BY (manual part) and CC0 (mined and existing parts).
- **MADLAD-400:** ODC-By tag, but the card text says CC-BY-4.0.
- **BPCC's mined part:** tagged CC0, but it repackages Samanantar, which is CC-BY-NC-4.0. #461 does not propose it.

### Effect on items 11 and 12

MADLAD-400, IndicCorp and Sangraha unverified are Common Crawl again and overlap `fw2` (#461 expects most of MADLAD-400 to dedup against `fw2`). Two v1 conclusions therefore need checking again:
- **Cross-pack scope (item 12).** v1 applied the cross-pack pass without a training ablation because only 50 of 2,711 qualifying pairs were cross-pack. With these packs, cross-pack removals may pass 1% of a pack. Where they do, the ablation runs before the cross-pack pass is applied to that pack (Risk 1: text repeated across sources tends to be good text).
- **Scale (item 11).** More packs bring the MinHash + LSH agreement test forward.

Also from #461:
- **Held-out overlap.** Its FineWeb-2 extension adds Punjabi and Assamese train data, and `heldout_v1` holds FineWeb-2's test splits for both. Rule 0 handles any overlap; the first run reports pa/as train ↔ held-out pairs separately.
- **Naming.** #461's extensions are numbered E1–E6, the same names as dedup's experiments E1–E5. Renaming them (e.g. X1–X6) avoids mixing them up.

## Pipeline prerequisites (Sourav's runner and `apply_dedup.py`)

### 16. What the pipeline needs from dedup

Sourav Dhar's runner (`run_pipeline.py`) runs clean → overlap → dedup → apply → F2 → survivor loss → shards. Overlap and dedup are TSAI jobs that it adopts; `apply_dedup.py` applies `remove_list.csv`; `survivor_loss.py` reads `dedup_groups.csv`. Its checks make the following a contract for every dedup release, v1.1 and v2 included.

**`remove_list.csv`, as `apply_dedup.py` checks it (any failure stops the run before anything is written):**

| Check | What dedup must guarantee |
|---|---|
| Header | Exactly `pack_id, split, part, row_in_part, doc_id`. No new column (item 5) |
| Keys | No `(split, part, row_in_part)` listed twice; `row_in_part` a whole number ≥ 0 |
| Held-out | No held-out row. Rule 0, enforced again at apply: one held-out row means the list is broken. H3-a relies on this |
| Part and row | `part` is the path relative to the split folder, with `/` (`code-go/part-00000.parquet`); `row_in_part` is the 0-based row in file order, as `overlap.py` numbers them |
| Same cleaning run | The `doc_id` and `pack_id` at each listed row match the list. A list made from another cleaning run than the parts stops the run |
| Pack column | No empty `pack_id` in any part |

**Other outputs:**
- `dedup_groups.csv` is read by `survivor_loss.py`, and the runner checks that its group count matches. Its format is part of the contract.
- `dedup_summary.json`: the runner checks status, counts, the overlap hashes and **held-out removed = 0**.

**Sourav's open items for the dedup side** (`pipeline/open-items.md`, 14 Nov):
1. `code_sha256` and the git commit in `overlap_summary.json` and `dedup_summary.json` (item 5).
2. Do `overlap_summary.versions` or `block` change what counts as a duplicate? (He assumes no.) Is `gold_dirs` used only by the harm check?
3. Are `inputs`, `out` and `results` safe to override per run (the runner generates them)? Once the scripts take `--input` and `--out` flags, the runner's generated configs can go.
4. The dedup job after the #244 cleaning: a `jobs/<date>-dedup/run.json` that adopts job 244's clean folder, with `to: dedup`, and a request whose `Command:` is `python teams/01-data-a/pipeline/run_pipeline.py --config <run.json>`. The test log is `--plan` plus a small trial with `stages.clean.only`.
5. PR order: the runner's default `pipeline.json` points at `teams/01-data-a/dedup/*.json`, which reach `main` only with #255.
6. Delete the untracked placeholders in `teams/01-data-a/dedup/` once dedup merges.
7. Licence (`licence_status_before_scale_v1.md`): a preflight check that every pack of the manifest is listed in `licence_usable`.

**What this means for H3:** H3 adds no second remove list. Under H3-b, one `dedup.py` run writes one `remove_list.csv` with the same five columns, so `apply_dedup.py` needs no change; H3 removals (rule 0 only, H3-a) are told apart in `dedup_log.jsonl`. `dedup_groups.csv` keeps the H1/H2 groups only; a survivor removed by H3 is written as `removed`, so its group has no survivor. Checked against Sourav's `survivor_loss.py` (16 Nov): such a group is counted as `without_survivor`, as a no-licence group is, never as lost to F2, so no change is needed there. The H3 cases are told apart in `dedup_log.jsonl` (`rule: H3`) and `h3_pairs.csv`.

## Order of work

1. **Now, in parallel with v1:**
   - Item 16: the answers to Sourav's open items; the dedup job as a runner `run.json` if his runner still needs one.
   - H3 v1.1: H3-a to H3-e done and merged (#610); E5c job request (#625), approved; H3-f ruled by TSAI (#625, 19 Nov);
     direct-edge fix (#663); the H3 harm test on the diagnosis packs (Aneesha Das, passed 19 Nov with 0 H3 removals);
     the BGE-M3 job (#666); week-4 task 3, the ruling in `h3_design_v1.md` (due Wed 25 Nov).
   - Decisions on items 13–15, so new packs can join with a rule ready.
2. **After TSAI's v1 dedup job:**
   - Item 5: summaries with code SHA-256, commit and part hashes (after the job, so its `6cfc24a` pin holds).
   - Items 1–4 and 6 together in one v1.1 overlap run.
   - The containment experiment (item 8) on the same outputs.
3. **After the v1.1 run:**
   - Item 10 on its groups.
   - Item 9 if E4 calls for it.
   - H3-g to H3-m, once E5c and E5d have run.
4. **When new packs join (#461) or the full-data size is known:** items 11 and 12.

The TSAI jobs this order needs (at most seven, most of them short CPU jobs) are listed in `dedup_v1_1_plan.md`,
"TSAI jobs after launch".

## Questions for review

The team reviews first; only the questions that are TSAI's go to TSAI, in one short note, after the team agrees.

**For the team** (Vijay Patil approves as lead):
- Items 1 (same URL) and 2 (math body) for v1.1: turn their switches on for the overlap rerun, or keep v1's rules?
- The two-week scope in `dedup_v1_1_plan.md`.
- Items 13 and 14 (rule 4 by measured clean share; non-document packs), when #461's packs are about to join.

**For TSAI** (after the team agrees):
- H3: ruled on #625 (19 Nov, H3-f). Four follow-up questions asked there the same day (direct edge, the harm test on the diagnosis packs, Odia without gold, E5d with both encoders); see "TSAI's ruling" in item 7.
- The overlap rerun carries items 1 and 2 if the team turns them on, and v1.1's effect is reported as a difference from v1. Acceptable?
- Later, only when #461's packs join: rule 4 by measured clean share (item 13), since TSAI approved v1's pack order.

**For other teams:**
- Sourav Dhar: whether the runner's preflight can check the licence map (item 16).
- G10: Aksharantar, MADLAD-400 and BPCC's mined part (item 15). The H3 model weights are signed off (#634); any further encoder chosen after E5d needs its own row.
- Data B (G2): clean-share measurements for each new pack (item 13). G2 has no H3 work (15 Nov), so readers for Sanskrit–Hindi and Sanskrit–English pairs have to be found elsewhere.

**Settled:** licence decisions for all 38 sample packs (G10, 16 Nov); how `survivor_loss.py` counts H3-emptied groups (checked, item 16); `h3_matches.csv` keyed by document, and H3-a to H3-e in `h3.py` (#610, 18 Nov); H3 removal, scope and direct edges only (TSAI, #625, 19 Nov); the H3 encoders' licences, LaBSE and BGE-M3 (G10, #634, 20 Nov).

## References

- Pasch, Petridis and Cutura, "Multilingual De-Duplication Strategies: Applying scalable similarity search with monolingual & multilingual embedding models", arXiv 2406.13695.
- Feng et al., "Language-agnostic BERT Sentence Embedding" (LaBSE), arXiv 2007.01852.
- Gala et al., "IndicTrans2: Towards High-Quality and Accessible Machine Translation Models for all 22 Scheduled Indian Languages", arXiv 2305.16307.
- Aneesha Das, `h3_design_v1.md` (draft), PR #44 on patilvijay23/era-v5-lab.
- Srinivasan Govindaraj, `teams/02-data-b/indic_sources_v1.md`, PR #461.
- Read, not used: Messmer, Sabolčec and Jaggi, "Enhancing Multilingual LLM Pretraining with Model-Based Data Selection", arXiv 2502.10361. It covers quality selection, not dedup; its decontamination (13-gram match, drop the whole document) is relevant to F2.
