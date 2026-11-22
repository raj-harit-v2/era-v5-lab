# Licence status of the 38 sample packs, before cleaning at scale

**Status:** draft for the team, 15 Nov 2026 (Kunal Sinha, Data A dedup). Nothing here is a licence decision: G10 owns those, and TSAI rules on anything G10 leaves open. A licence tag is not legal clearance.
**Update, 15 Nov (G10's reply to Data A):** G10 has added explicit Stage 0 rows for **all 38 sample packs**, each `TSAI reserves`, on `saitej123:g10-week3-post-training` (`teams/10-post-training/licences/licence_table.md`; checked on that branch: 38 pack rows plus `chandassu`, none missing). It landed on `main` with G10's PR (#524, 17 Nov). What that settles and what is left:
- **Settled:** the 19 packs covered at source level (Sangraha verified and synthetic, FineWeb-2, starcoderdata) and the 10 packs from new sources (`cadj-*`, `en-dclm`, `en-fineweb-edu`, `en-nemotroncc`, `en-nemotroncc-synth`, `math-finemath`, `math-megamath` as `megamath-web`, `sci-finepdfs`). `code-js-ts` no longer carries the "training-use rights require further verification" note.
- **DCLM, resolved (16 Nov):** G10 updated the `en-dclm` row (card revision `817d675276`). The licence is CC-BY-4.0 in both the card's tag and its description; the "research purposes only" wording sits under Uses and Limitations as a fitness disclaimer, not a licence term (as G10 read Dolci), and the data has no model-written text. `en-dclm` stays `TSAI reserves` (In, with attribution under CC-BY-4.0 and Common Crawl terms); the disclaimer is noted in the row for TSAI's Gate 3 sign-off. No effect on dedup.
- **Still open:** `ind-hi-hplt` keeps "web terms", for TSAI, who reserves every decision.
- **New for attribution:** `en-nemotroncc-synth`'s Wikipedia rewrites inherit CC-BY-SA.
- **H3 encoders (20 Nov):** G10 signed off LaBSE (Apache-2.0) and BGE-M3 (MIT) as models of the data pipeline, not training data (#634).
- **For dedup:** done in #630 (18 Nov): `dedup.json` lists all 38 packs in `licence_usable` (true unless TSAI rules otherwise) with `default_licence_usable: false`. Steps 2 to 5 below (pin subsets, keep Out packs out at the input, attribution IDs for `cadj-*`) still apply.

The rest of this note is the state before G10's reply, kept as the record.

**Why now:** dedup v1 treats all 38 packs as usable **for this experiment only** (TSAI, 12 Nov): `licence_usable` is empty and `default_licence_usable` is `true` in `dedup/dedup.json`. A cleaning run at scale is not that experiment, so every pack needs a recorded decision first.

## What the licence decision controls, and where

| Where | What a licence decision does | What it cannot do |
|---|---|---|
| **Which packs enter the run** (the sample manifest, `stages.clean` in the pipeline config) | Keeps an Out source out of training altogether | — |
| **Dedup rule 1** (`source_priority_v1.md`, `decide()` in `dedup.py`) | Inside a duplicate group, a copy from an unusable pack never survives; if no train copy is usable, all train copies go | It never touches a document that has no duplicate. Dedup is not a licence filter |
| **Attribution** (model card, data sheet) | CC-BY, CC-BY-SA and ODC-By sources need credit | — |

So an Out pack must be left out **before cleaning**, not removed by dedup.

## The rule applied (TSAI, as recorded in G10's table and in #461)

- **In:** permissive licences (MIT, Apache-2.0, BSD, CC0, CC-BY, ODC-By) and CC-BY-SA (with attribution); text made by open-weight models under permissive licences (gpt-oss, and others G10 has allowed, such as DeepSeek-R1 and Qwen3).
- **Out:** non-commercial (NC), no-derivatives (ND), no stated licence; text made by closed OpenAI, Anthropic or Google models, or by Llama models; output of models whose licence carries use restrictions into a model trained on it (OpenRAIL-M, TSAI 3 Nov).

## Status per source (15 sources, 38 packs)

"G10" is the decision in `teams/10-post-training/licences/licence_table.md` on `main` (Stage 0 unless noted). "Reading" is this note's reading under the rule, for G10 to confirm.

| Source | Packs | Licence (card) | Generator | G10 | Reading | Open point |
|---|---|---|---|---|---|---|
| `bigcode/starcoderdata` | `code-cpp`, `code-go`, `code-java`, `code-js-ts`, `code-python`, `code-rust` | `other`: each file keeps its upstream licence; attribution required | none | TSAI reserves for go, js-ts, python, rust; **no row for cpp, java** | In, with per-file attribution | `code-js-ts`: G10 says training-use rights need verification. cpp and java need rows |
| `bigcode/commitpackft` | `cadj-commits` | MIT tag | none (human commits) | TSAI reserves, **as SFT set** (`sft-code-commitpackft`) | In | No Stage 0 (pretraining) row. Sample has no `url` |
| `HuggingFaceTB/issues-kaggle-notebooks` (Kaggle part) | `cadj-notebooks` | Kaggle part from Meta Kaggle Code, Apache-2.0 per the card; no Hub licence tag seen | none | **no row** | In, if the pack is the Kaggle part only (week-1 diagnosis: "500 Kaggle notebooks") | Confirm the config (`kaggle`, not `issues`). Sample has no `url` |
| `bigcode/starcoder2data-extras` (`stackoverflow`) | `cadj-stackexchange` | Stack Exchange dump: CC-BY-SA (version by post date) | none | **no row** | In, with attribution (CC-BY-SA) | Attribution needs post IDs or URLs; sample has no `url` |
| `mlfoundations/dclm-baseline-1.0` | `en-dclm` | CC-BY-4.0 tag; the card also says it is designed for research purposes only | none | **no row** | Unclear: the licence is In, the card's research-only statement may not be a licence term (G10 treated a similar statement on Dolci as intent, not a term) | G10 or TSAI ruling |
| `HuggingFaceFW/fineweb-edu` | `en-fineweb-edu` | ODC-By 1.0 (web text under Common Crawl terms) | none (an edu classifier selects; it writes nothing) | **no row** | In, with attribution | Row needed |
| `nvidia/Nemotron-CC` v1 (Common Crawl contrib) | `en-nemotroncc`, `en-nemotroncc-synth` | Released under the Common Crawl Terms of Use, not a standard licence | `-synth`: rewritten by Mistral NeMo 12B Instruct (open weights, Apache-2.0); real part: none | **no row** | The generator passes the rule (open weights, permissive licence). The terms are non-standard, like HPLT's "web terms" | G10 or TSAI ruling on the Common Crawl Terms of Use |
| `HuggingFaceTB/finemath` | `math-finemath` | ODC-By | none | **no row** | In, with attribution | Row needed |
| `LLM360/MegaMath` | `math-megamath` | ODC-By | Web subset: none. Its synthetic subsets are model-written; folders are named after their models, including `llama-3.3` and `qwen-2.5` | **no row** | In for the **web** subset only. Every one of the 17,647 sample-v0 train documents has a source URL, which points to the web subset (an inference, not a recorded fact) | Record the subset in the manifest; keep the synthetic subsets out (Llama output is Out) |
| `HuggingFaceFW/finepdfs` | `sci-finepdfs` | ODC-By 1.0 | none | **no row** | In, with attribution | Row needed |
| `HuggingFaceFW/fineweb-2` | 10 `ind-*-fw2` packs | ODC-By 1.0 | none | TSAI reserves for mr, kn only | In, with attribution | Rows for bn, gu, hi, ml, or, sa, ta, te (one source row would do) |
| `ai4bharat/sangraha` verified | 6 `ind-*-sangraha-v` packs | CC-BY-4.0 | none | TSAI reserves for ta only | In, with attribution | Rows for bn, hi, kn, mr, te |
| `ai4bharat/sangraha` synthetic | 4 `ind-*-sangraha-s` packs | CC-BY-4.0 | IndicTrans2 translation of English Wikipedia (MIT) | **no row** | In by licence and generator. G2's proposal has 0% translated text until TSAI decides at Gate 3 (#440), and it measured 4.7% clean | Likely out for quality reasons, not licence |
| `ai4bharat/IndicCorpV2` | `ind-hi-indiccorp` | CC-BY-4.0 (G10) / CC0 (card) | none | TSAI reserves | In | — |
| HPLT 3.0 | `ind-hi-hplt` | CC0 for the packaging only; the text keeps its web terms | none | TSAI reserves, **not verified** | Treat like other web crawl: keep URLs, honour opt-outs and takedowns | G10 left it open |

**Count:** G10's Stage 0 table covers 9 of the 38 packs (`code-go`, `code-js-ts`, `code-python`, `code-rust`, `ind-mr-fw2`, `ind-kn-fw2`, `ind-ta-sangraha-v`, `ind-hi-indiccorp`, `ind-hi-hplt`; its tenth row, `chandassu`, is not a sample pack). **29 packs have no pretraining decision recorded**, and two of the 9 (`code-js-ts`, `ind-hi-hplt`) are not verified.

## What G10's file already settles at source level

Besides the Stage 0 table, `licence_table.md` has a "Strategy v0" section and a "Hand-off to Team 11" (4 Nov) that work per **source**:

- **Sangraha and IndicCorpV2** are listed by source under CC-BY-4.0 in the hand-off, though the Stage 0 table names only `ind-ta-sangraha-v` and `ind-hi-indiccorp`. If G10 confirms the source-level entry covers every Sangraha pack, the 9 other Sangraha packs (5 verified, 4 synthetic) are settled.
- **FineWeb-2** is listed for `ind-mr-fw2` and `ind-kn-fw2` only, and **starcoderdata** for the Go, Python and Rust "permissive subsets; copyleft and non-commercial files filtered out". The same wording would extend to the 8 other FineWeb-2 packs and to C++ and Java; it needs saying.
- **Strategy v0, "commercial-use data only":** a dataset whose licence is missing or restricts commercial use is excluded. This is the rule that decides `en-dclm`, unless G10 reads its "research purposes only" line as a statement of intent (as it did for Dolci).
- **Approved generators (TSAI, 3 Nov):** open-weight models under MIT or Apache-2.0 that allow training on their output. Mistral NeMo 12B (Apache-2.0, `en-nemotroncc-synth`) fits the rule though it is not on the list by name; IndicTrans2 (MIT, `sangraha-s`) is already accepted for `indic-align`'s translated subsets.
- **Takedown:** web crawls keep source URL manifests for robots.txt, DMCA and GDPR requests. The empty `url` of the `cadj-*` packs matters for this, not only for attribution.

So the ask to G10 is smaller than 29 new rows: confirm the source-level coverage (Sangraha, FineWeb-2, starcoderdata), confirm that this covers 19 of the 29 (8 FineWeb-2, 9 Sangraha, 2 starcoderdata), add rows for the other 10 packs, which come from 9 sources G10 has not looked at (commitpackft as pretraining, the notebooks, Stack Exchange, DCLM, FineWeb-Edu, Nemotron-CC with 2 packs, FineMath, MegaMath, FinePDFs), and rule on DCLM and Nemotron-CC.

## What has to happen before cleaning at scale

1. **A decision for every pack.** G10 adds Stage 0 rows for the 29 packs, one row per source where the licence is the same across languages. The five that need a ruling, not just a row: `en-dclm` (research-only statement), `en-nemotroncc` and `en-nemotroncc-synth` (Common Crawl Terms of Use), `code-js-ts` (training-use rights), `ind-hi-hplt` (web terms).
2. **Pin the subset of every pack**, not only the dataset, in the sample manifest: MegaMath `web`, Nemotron-CC v1 (real or synthetic, and which synthetic kinds), `starcoder2data-extras` `stackoverflow`, `issues-kaggle-notebooks` `kaggle`. Licence and generator differ between subsets of one dataset, so the dataset name alone is not enough.
3. **Leave Out packs out at the input**, in the manifest or the pipeline's `stages.clean`, before the clean job. Dedup's rule 1 only decides which copy of a duplicate survives.
4. **Fill `dedup.json` explicitly** for the scale run: every pack listed in `licence_usable`, and `default_licence_usable: false`, so a pack nobody decided can never be the surviving copy. Better still, the pipeline's preflight refuses a run in which a pack of the manifest is missing from `licence_usable` (a check for Sourav's runner, next to its other stop-before-write checks).
5. **Keep what attribution and takedown need.** CC-BY, CC-BY-SA and ODC-By need credit, and web text needs its URL so a takedown request can be honoured. The sample's `url` is empty for all three `cadj-*` packs: check that the full data carries a repository, commit, notebook or post ID for them, and keep it through cleaning and shards.
6. **New sources (#461) follow the same steps** before they join: Aksharantar, MADLAD-400 and BPCC's mined part already need G10's ruling.
7. **Tools are a separate question.** Model weights used in the pipeline (LaBSE for H3, IndicTrans2 if used) need G10's clearance as tools; that does not change any pack's status.

## Questions

- **G10:** Stage 0 rows for the 29 packs; rulings on `en-dclm`, the two Nemotron-CC packs, `code-js-ts` and `ind-hi-hplt`.
- **TSAI:** is `default_licence_usable: false` with an explicit list the right default for the scale run? Does the experiment-only ruling of 12 Nov end with the scale run?
- **Data A (sampling):** which subset or config each pack was drawn from, recorded in the manifest.
- **Pipeline (Sourav):** a preflight check that every pack in the manifest has a licence decision.

## Sources

- G10 licence table: `teams/10-post-training/licences/licence_table.md` (main).
- Sample manifest: `teams/01-data-a/jobs/2026-11-02-tokenizer-sample-v0-clean/tokenizer_sample_v0_manifest.json` (main).
- Dataset cards: [DCLM-baseline](https://huggingface.co/datasets/mlfoundations/dclm-baseline-1.0), [MegaMath](https://huggingface.co/datasets/LLM360/MegaMath), [issues-kaggle-notebooks](https://huggingface.co/datasets/HuggingFaceTB/issues-kaggle-notebooks), [starcoder2data-extras](https://huggingface.co/datasets/bigcode/starcoder2data-extras).
- Nemotron-CC v1 terms and generator: Su et al., "Nemotron-CC", ACL 2025 ([paper](https://aclanthology.org/2025.acl-long.123)); Mistral NeMo's licence: [Mistral AI](https://mistral.ai/news/mistral-nemo/).
