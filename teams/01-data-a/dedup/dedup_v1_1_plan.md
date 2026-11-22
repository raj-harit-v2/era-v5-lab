# Dedup plan for Weeks 3 and 4 (15–28 Nov 2026): v1 at scale, then the data card

**Lead:** Vijay Patil (Data A). **Owners:** Kunal Sinha and Aneesha Das (Data A dedup). **Status:** in progress; updated at most once a day, when a row changes.
**Follows the lab schedule:** Week 3 (15–21 Nov) is cleaning, dedup, decontamination and tokenizing at scale, with
Gate 3 on Sat 21 Nov (the first training shards pass the audit and match their manifests). Week 4 (22–28 Nov) is the
training-week shards, dry run 2 (24 Nov), `data_card_v1.md` and TSAI's data go or no-go on Sat 28 Nov.
**Week-4 work order (TSAI, 21 Nov):** the merged pipeline runs on **corpus-v1**, the real training data, not sample-v0,
and dry run 2 trains on its output. Everything validated so far ran on the sample.
**So dedup runs v1's rules, frozen** (as proposed on #255). `dedup_design_v2_proposal.md` is the backlog for after
training starts; nothing in it changes this run.

> **What this plan asks for:** nothing beyond the lab schedule. Weeks 3–4 are the scheduled dedup work (the run at
> scale, the audit, the data card). The v2 backlog and the TSAI jobs forecast are for information: each later job comes
> as its own request, and the team or TSAI can drop any of them. The only decision needed this week is item 6 (licences
> and pack order for Thursday's packs).

## Week 3 (15–21 Nov): dedup v1 at scale · Gate 3, Sat 21 Nov

| When | Work (proposal item) | Done when |
|---|---|---|
| Mon 16 | **Dedup job request on #255** (rebased; local run on TSAI's rerun files: 1,345 removed, 64 by rule 0, 0 held-out; pinned at `6cfc24a`) | Done. Approved by Vijay Patil (16 Nov); TSAI's run returned 17 Nov (#547): 1,345 removed, 64 by rule 0, 0 held-out, as expected; #255 merged 17 Nov |
| Tue 17 | **Item 16:** answers to Sourav's 7 open items; the dedup job as a runner `run.json` (adopt the cleaning job's folder, `to: dedup`) | `run_pipeline.py --plan` passes on it |
| Before the Thu 19 job | **Item 6:** every pack of the job's input manifest in `dedup.json` (`licence_usable`, `default_licence_usable: false`) and in `pack_order` (G10's table covers the 38 sample packs) | `licence_default_used_for` is empty in the summary. Rehearsed on the 38 sample packs (#599); for corpus-v1, see Week 4 |
| Thu 19 | **The combined Data A job** (TSAI, 17 Nov: spec v1.1 cleaning, then shards). #547's list fits only the #244 cleaning, so overlap and dedup must run again on this job's cleaned output, through the runner (clean → overlap → dedup → apply → F2 → shards); asked Vijay on 18 Nov | Rehearsed as TSAI's 38-pack run (#599, merged): 86 parts, 74/74 pipeline checks, 9/9 inventory checks, 48 train shards |
| After TSAI's dedup run | **Item 5:** `code_sha256` and git commit in `overlap_summary.json` and `dedup_summary.json`; part SHA-256s carried from overlap to dedup. After the run, so its `6cfc24a` pin holds. When the runner runs dedup itself (run mode), it records the script's SHA-256, which covers #503 for that job | Tests pass; outputs otherwise byte-identical to v1; Sourav's `cleaning_pipeline.json` gets the code hashes |
| Wed 18 | **H3:** #610 merged (`h3.py` and the report-only H3 step in `dedup.py`); E5c job request #625 (report-only measurement, 1 GPU) | Approved by Vijay Patil (18 Nov); TSAI's go-ahead (19 Nov); TSAI's run |
| Thu 19 | **H3: TSAI's ruling** (#625): rule 0 removal once E5c and the harm check pass; direct edges only, fixed in #663; four follow-up questions asked on #625. The H3 harm test on the diagnosis packs (Aneesha Das), since sample v0 has no gold | #663 merged (19 Nov). Harm test: pass, 0 of 1,308 gold removed, but 0 H3 removals. TSAI's answers still open |
| Fri 20 | **H3:** #625 (E5c) and #666 (BGE-M3 on E5c's Sanskrit pairs) merged; LaBSE pinned at `836121a`; G10 signs off both encoders (#634) | TSAI's runs |
| When the run's outputs are back | **Dedup audit** (checks on dedup's own numbers; no document reading): see below | Five lines in Vijay's daily audit pack; any failure filed as an issue |

**The dedup audit.** The schedule's general Week 3 audit (reading cleaned documents, comparing before and after
cleaning, decoding shards) is the whole team's, planned by Vijay Patil, and is not repeated here. These five checks are
dedup's own:

| Check | What it means | Where | Pass |
|---|---|---|---|
| No held-out removed | Dedup never deletes a held-out document (G3 uses them) | `heldout_removed`, `dedup_summary.json` | 0 |
| Harm check | No gold (reviewed clean) document is removed | `harm_check.status`, `dedup_summary.json` | `pass` |
| Apply matches the list | `apply_dedup.py` removed exactly the listed rows | `removed` in `apply_dedup_summary.json` vs rows of `remove_list.csv` | Equal |
| Survivor loss | Groups whose kept copy F2 then removed (accepted by TSAI, 12 Nov) | `survivor_loss_summary.json` | Counted and listed |
| Removals per pack | Each pack's removals against the 5 Nov run; a jump points to a problem | `by_pack`, `dedup_summary.json`, vs `results_v1.md` | Close to 5 Nov (about 0.1% overall) |

## Week 4 (22–28 Nov): corpus-v1 and dry run 2 · Gate 4, Sat 28 Nov

From TSAI's week-4 work order (21 Nov). Dedup's part of the lead's corpus-v1 run (task 1) and week-4 task 3 (H3):

| When | Work | Done when |
|---|---|---|
| Sun 22 – Mon 23 | **Dedup and overlap ready for corpus-v1:** every pack of corpus-v1 in `pack_order`, `licence_usable` and overlap's `expected_packs` (a pack missing from any of them stops the run); overlap's memory and time checked against corpus-v1's row count (all-pairs took 56 min and 9.6 GiB on 1.4 M documents). H3 in the run: report-only, E5c's settings (sentence 0.55 for Sanskrit, E5c's packs, `device: cuda`) | Corpus-v1's pack list and row count from Vijay Patil; the configs match it |
| Tue 24 (D3) | **Corpus-v1 run** (task 1, lead with Sourav Dhar); dry run 2 starts | Dedup and overlap stages complete in the run |
| Wed 25 (D4) | **Week-4 task 3:** H3 rule with TSAI, per #625: `h3_design_v1.md` (with this PR). Team 2: H3's Indic pairs and scope | TSAI confirms or corrects the proposed reading in "Decisions" |
| Thu 26 | **Dedup audit** of the corpus-v1 run (the five checks in Week 3) | Five lines in the daily audit pack |
| By Fri 27, 23:59 IST | Gate 4 evidence: everything on `main` or in a PR linked in the team group. **Dedup section of `data_card_v1.md`** (method, survivor rules, counts per pack, held-out handling, harm check, known limits: H3 report-only; Indic minimum under review (E4); truncated copies under 80%) | Reviewed by Vijay |
| Sat 28 | Go or no-go on the main run | Dedup part of the data report sent |

## After training starts: the v2 backlog

All 16 items of `dedup_design_v2_proposal.md` stay in the backlog; none is dropped. Items 5, 6 and 16 are done in
Week 3 because the run at scale needs them (item 5 just after TSAI's dedup run). The rest start after launch, in this order:

| # | Item | Waits on |
|---|---|---|
| 1, 2 | Same-URL rule; math numbers on the body (behind switches, off = v1) | The first overlap rerun after launch |
| 4 | Code threshold hand review | The run's pairs |
| 3, 9 | Indic length minimum; Indic shingles if needed. Kannada done 18 Nov (#393): 20/20 template, the 50-word minimum stays | E4 readers' labels for Telugu (#394) and Tamil (#395) |
| 7a | H3 encoder comparison on Sanskrit: `labse_check.py --model BAAI/bge-m3` (or a multilingual-e5 model), and a margin score in place of the plain cosine (H3-h, H3-i); measurement only, nothing removed. **BGE-M3 done 16 Nov** (`h3_bge_m3_check_results_v1.md`: 82–95% of Sanskrit blocks at 0.7, 8 times slower); margin score open | Nothing; can run any time, and is evidence for TSAI's ruling |
| 7b | H3: `h3.py` and the dedup side, report-only. **Merged 18 Nov (#610)**; E5c measurement job #625 | Ruled 19 Nov (#625): removal once E5c and the harm check pass, direct edges only (#663); E5d readers for the Sanskrit threshold |
| 8, 10, 11 | Containment; "changed least" survivor rule; MinHash + LSH test | The run's outputs; full-data size |
| 12 | Training ablation of the cross-pack pass | A pack's cross-pack removals reaching 1% |
| 13, 14, 15 | New sources from #461: pack order, non-document packs, licences | #461's packs joining; G10 |

## TSAI jobs after launch

A forecast for TSAI's planning: the jobs the backlog needs on TSAI's machines. Each comes as its own job request with a
local test log. Items 3, 4, 9, 13–15 and E5d need no job of their own (readers, hand reviews, local experiments,
decisions, configs); a rule they change goes into job 2 or 3. The H3 harm test runs locally on the diagnosis packs.

| # | Job | Items | Hardware, rough time | When | Depends on |
|---|---|---|---|---|---|
| 1 | H3 E5c measurement (#625), report-only | 7 | 1 GPU, ≤ 120 min | Merged 20 Nov | TSAI's run |
| 1b | H3 second encoder: BGE-M3 on E5c's Sanskrit pairs (#666), report-only | 7 | 1 GPU, ≤ 180 min | Merged 20 Nov | TSAI's run |
| 2 | Overlap v1.1 rerun: same URL, math body, Indic minimum, code threshold; containment pairs written too | 1–4, 8 | CPU, about 80–90 min (the rerun took 77) | First week after launch | The team's call on items 1–2; E4 labels for item 3 |
| 3 | Dedup v1.1 on that rerun | 1–4, 6 | CPU, minutes | Right after job 2 | Job 2 |
| 4 | H3 removal run (`dedup.py` with `h3.remove: true`), in v1 | 7 | CPU, minutes | After E5c and the H3 harm test pass | TSAI's ruling (19 Nov); #663 merged; E5d for the Sanskrit threshold |
| 5 | "Changed least" survivor test (raw and cleaned text) | 10 | CPU, under an hour | After job 3 | Job 3's groups |
| 6 | MinHash + LSH agreement test on the sample | 11 | CPU, about 1–2 h | When the full-data size is known or #461's packs join | Full-data size |
| 7 | Training ablation of the cross-pack pass | 12 | GPU training | Only if a pack's cross-pack removals reach 1% | Counts with new packs |

## Requirements for the run at scale

Status: **Met** (with evidence), **This week** (with the day), **Waiting** (on whom).

### Functional

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| FR1 | Find exact (H1) and near (H2) duplicates within and across all 38 packs, with v1's family rules | Met (v1) | `dedup_design_v1.md`; TSAI's overlap run of 5 Nov |
| FR2 | Choose survivors in rule order: held-out, licence, URL, length, pack order | Met (v1) | `source_priority_v1.md`; `tests/test_dedup.py` |
| FR3 | Never remove a held-out document; report held-out ↔ held-out pairs | Met (v1) | `heldout_removed: 0`; `apply_dedup.py` also rejects held-out rows |
| FR4 | A copy from an unusable pack never survives; every pack of the run listed explicitly | Met for the 38 sample packs (#630, rehearsal #599); waiting: corpus-v1's pack list | G10 lists all 38 sample packs in Stage 0 (16 Nov); new sources need G10 rows |
| FR5 | `remove_list.csv` has exactly `pack_id, split, part, row_in_part, doc_id`, each row once | Met (v1) | `apply_dedup.py` checks |
| FR6 | `dedup_groups.csv` lists every group's survivors and removed copies, for F2's survivor count | Met (12 Nov) | `survivor_loss.py` reads it |
| FR7 | Empty documents are listed, never matched, never removed | Met (10 Nov) | `empty_documents.csv` |

### Non-functional

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| NFR1 | Reproducible: same inputs and config give byte-identical outputs and group IDs | Met (v1) | Windows rerun: same `remove_list.csv` (`913e66a6…`) |
| NFR2 | Backward compatible: item 5's change leaves every other output byte-identical | This week: after TSAI's run | Same check as for H3 on 15 Nov |
| NFR3 | Traceable: summaries record input SHA-256s, the code SHA-256 and the git commit | This week: after TSAI's run (the job request records the commit meanwhile) | `cleaning_pipeline.json` `code_sha256` not null |
| NFR4 | Reversible: dedup never rewrites data; every removal is logged | Met (v1) | `dedup_log.jsonl`; `apply_dedup.py` writes new parts |
| NFR5 | Safe: stops on mismatched inputs | Met (v1) | `check_results()`, `read_urls()`; tests |
| NFR6 | No harm: zero gold documents removed | Met on 4 diagnosis packs; recheck in the run | Harm check in `dedup_summary.json` |
| NFR7 | No document text in any output | Met (v1) | Output review |
| NFR8 | Fast enough for the full sample | Met | `benchmarks/2026-11-14-dedup-speed/` |
| NFR9 | Runs offline within the job's limits | Met | `JOB_REQUEST.md` rules |
| NFR10 | Tested; each job request carries a fresh test log | Ongoing | `pytest` log with the dedup job request |

## Dependencies

| What | Who | Needed for |
|---|---|---|
| Corpus-v1's pack list and row count | Vijay Patil, TSAI | FR4, `pack_order`, `expected_packs`, overlap sizing |
| TSAI's E5c and BGE-M3 runs (#625, #666, merged) | TSAI | H3 counts; E5d |
| Answers to the four H3 questions (#625, 19 Nov) | TSAI | Week-4 task 3; the H3 removal run (job 4) |
| G10's licence table on `main` | Sai Teja (G10) | Done for the 38 packs (#524) and the H3 encoders (#634); new packs need rows |
| Answers on item 16 | Sourav Dhar, Vijay Patil | Tue's `run.json` |

## Log

| Date | Change |
|---|---|
| 16 Nov | Plan written; then aligned to the lab schedule (Weeks 3 and 4): v1 frozen for the run at scale, v2 work after launch |
| 16 Nov | Aneesha Das added as co-owner; Vijay Patil named as lead |
| 16 Nov | General Week 3 audit left to Vijay's plan; the five dedup checks kept here |
| 16 Nov | G10: `en-dclm` stays In (research line read as a disclaimer, noted for TSAI's Gate 3); FR4 waits on G10's PR merging |
| 16 Nov | Backlog item 7 split: 7a encoder comparison on Sanskrit (BGE-M3 or e5, margin score; any time), 7b dedup side (waits on `h3.py` format and TSAI) |
| 16 Nov | Item 5 moved after TSAI's dedup run (keeps the `6cfc24a` pin); the dedup job request on #255 is ready; 7a: BGE-M3 measured |
| 16 Nov | Dedup job on #255 approved by the lead; with TSAI |
| 17 Nov | TSAI's dedup run returned (#547), as expected; #255 merged |
| 18 Nov | #610 merged (H3, report-only); E5c job request #625; Thu 19 combined job: overlap and dedup must rerun on its cleaning (asked Vijay); item 6 now waits on that job's pack list; TSAI jobs forecast added |
| 18 Nov | "What this plan asks for" note added: the backlog and the forecast are for information, not requests |
| 19 Nov | E4 Kannada scored (#393): 20/20 template, so item 3 keeps v1's minimum for Kannada; Telugu and Tamil still with readers |
| 19 Nov | TSAI ruled on H3 (#625): rule 0 removal in v1 once E5c and the harm check pass, direct edges only; #663 fixes `h3_join.py`; harm test on the diagnosis packs (Aneesha); job 4 moves to after E5c and the harm test |
| 20 Nov | #625 and #666 merged; LaBSE pinned at `836121a`; G10 signs off the H3 encoders (#634); TSAI's 38-pack rehearsal (#599) merged |
| 21 Nov | Week-4 work order: corpus-v1 run (D3), H3 rule as week-4 task 3 (D4, `h3_design_v1.md`); Week 4 section rewritten for it |
