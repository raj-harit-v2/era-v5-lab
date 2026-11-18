# Source priority v1: Which copy survives

**Status:** v1. Who agreed each rule, and when, is in the decision log at the end of `dedup_design_v1.md`.

When dedup (`dedup_design_v1.md`) finds a group of duplicates, the rules below choose the survivor. They are applied **in order**: each rule only breaks the ties left by the one above. `dedup_log.jsonl` records the rule that decided (`priority_rule`).

| Order | Rule | The copy that survives |
|---:|---|---|
| 0 | Held-out first | Every held-out copy. Dedup never removes a held-out document |
| 1 | Licence | A copy whose pack has a usable licence |
| 2 | Provenance | A copy with a source URL |
| 3 | Completeness | The longer copy |
| 4 | Pack order | The copy in the pack ranked first, then the lowest `(split, part, doc_id)` |

## Rule 0: held-out first

The sample splits every pack into `train/` and `heldout/`. G3 (tokenizer) uses the held-out documents to choose and check the tokenizer, not to train it (`teams/03-tokenizer/COMPARE.md`), so removing one would change G3's results.

| Pair | What happens |
|---|---|
| train ↔ train | Rules 1–4 choose the survivor |
| train ↔ held-out | The held-out copy survives and the train copy is removed, which also removes the leak |
| held-out ↔ held-out | Nothing is removed; the pair is reported to G3 |

Rule 0 overrides rule 1: a held-out document is kept even if its pack's licence would rule it out, and is reported instead. Dedup never shrinks the held-out set.

## Rule 1: licence

- **Usable:** permissive licences (e.g. MIT, Apache-2.0, BSD, CC-BY, CC0, public domain) and CC-BY-SA.
- **Not usable:** any NC (non-commercial), any ND (no derivatives), and unstated licences. A copy with an unusable licence never survives.
- If no copy in a group has a usable licence, every train copy is removed.
- **Applied per pack.** The sample has no per-document licence column, so a pack's licence applies to all its documents. `dedup.json` holds the map (`licence_usable`, with `default_licence_usable` for packs not listed).
- **For this experiment only, all 38 sample-v0 packs are treated as usable** (TSAI, 12 Nov). TSAI approved every pack into sample v0, and G10's licence table on `main` (`teams/10-post-training/licences/licence_table.md`, "Stage 0: Foundation data") excludes none of them: it lists 8 of the 38 (`code-python`, `code-go`, `code-js-ts`, `ind-mr-fw2`, `ind-kn-fw2`, `ind-ta-sangraha-v`, `ind-hi-indiccorp`, `ind-hi-hplt`), all with the decision "TSAI reserves", and does not list the other 30. So `licence_usable` stays empty and every pack uses `default_licence_usable: true`; `dedup.json` is unchanged. **G10 owns the final licence decision.**
- **Not verified: `code-js-ts` and `ind-hi-hplt`.** G10's table leaves both open: `code-js-ts` ("training-use rights require further verification") and `ind-hi-hplt` (CC0 for the packaging only; web terms for the text). On the 5 Nov run neither changed the remove list: `code-js-ts`'s only cross-pack matches were the empty documents, which are set aside, and `ind-hi-hplt` had no qualifying duplicates. This is checked again on the rerun. If G10 excludes a pack, set it to `false` in `licence_usable` and rerun `dedup.py` (seconds).

## Rule 2: provenance

Prefer the copy with a non-empty `url`. Dataset and licence are known from the pack for every document, so the URL is the only part of provenance that differs between copies. The survivor keeps its provenance record; the removed copies stay traceable through the log.

## Rule 3: completeness

Prefer the copy with the longer normalised text, so a complete copy beats a truncated one.

## Rule 4: pack order

The spec defines no pack order, so v1 uses the order in which `clean.py` lists the packs. `clean.py` lists only the 13 Data A packs (its `_FAMILY` map); the 25 Data B packs have no list in either team's code, so they follow in alphabetical order of `pack_id`. This list is the authority, even if `clean.py` is later reordered, and `dedup.json` holds the same list.

1–13, Data A, in `clean.py` order: `code-go`, `code-js-ts`, `code-java`, `code-cpp`, `code-rust`, `code-python`, `en-fineweb-edu`, `en-dclm`, `en-nemotroncc-synth`, `en-nemotroncc`, `math-megamath`, `math-finemath`, `sci-finepdfs`.

14–38, Data B, alphabetical: `cadj-commits`, `cadj-notebooks`, `cadj-stackexchange`, `ind-bn-fw2`, `ind-bn-sangraha-v`, `ind-gu-fw2`, `ind-hi-fw2`, `ind-hi-hplt`, `ind-hi-indiccorp`, `ind-hi-sangraha-s`, `ind-hi-sangraha-v`, `ind-kn-fw2`, `ind-kn-sangraha-s`, `ind-kn-sangraha-v`, `ind-ml-fw2`, `ind-mr-fw2`, `ind-mr-sangraha-v`, `ind-or-fw2`, `ind-sa-fw2`, `ind-ta-fw2`, `ind-ta-sangraha-s`, `ind-ta-sangraha-v`, `ind-te-fw2`, `ind-te-sangraha-s`, `ind-te-sangraha-v`.

Within one pack, the lowest `(split, part, doc_id)` wins.

**Effect on the sample:** the order of the Data B packs matters only for cross-pack pairs with a Data B pack on at least one side: 23 of the 50 cross-pack qualifying pairs in TSAI's overlap rerun on the #244 cleaning (14 between two Data B packs, 9 between a Data A and a Data B pack; the same counts as on 5 Nov), out of 1,414,996 documents. Most are the same Indic text in a FineWeb-2 (`fw2`) pack and a Sangraha (`sangraha-v`) pack; with this order the `fw2` copy survives. The Data B lead may ask for a different order, with a reason, by Fri 13 Nov 2026.

## Example

Three copies of the same article:

| Copy | Pack, split | Pack licence | `url` | Result |
|---|---|---|---|---|
| A | science, train | CC-BY-NC | yes | Removed at rule 1 (NC) |
| B | science, train | CC-BY | empty | Removed at rule 2 |
| C | math, train | CC-BY-SA | yes | **Survives** (decided by rule 2) |

If B were in `heldout/`, B would survive at rule 0, and A and C would be removed.

## After dedup: F2

The pipeline order is **Clean, then Dedup, then F2** (TSAI, 12 Nov). F2 (benchmark contamination, matched against G9's fingerprints) runs on the deduplicated data, so among the copies of a group it sees only the survivors.

- If F2 removes the survivor of a duplicate group, the removal stands. **No other copy of the group is promoted** in its place, so the group can end with no copy in the data.
- These groups are **counted and listed in the report**: for each, the survivor F2 removed, as `(pack_id, split, part, doc_id)`, and the group's size.
- A group can have more than one survivor, because every held-out copy survives (rule 0). Reading used here: such a group counts as soon as F2 removes any one of its survivors.

## Not used in v1: fewer fixes

Preferring the copy that cleaning changed least was considered and dropped, because no per-document record of fixes exists: `clean.py` returns only the action and the new text, `run_clean.py` records only dropped and failed IDs, and `run_tokenizer_sample.py` counts rules per part, not per document. The v2 candidate needs no change to the cleaning tools: raw and cleaned text share a `doc_id`, so dedup can measure how much each copy changed (e.g. `1 − difflib` ratio) for the pairs it finds and keep the copy that changed least.

## Open items

- G10: the final licence decision, including `code-js-ts` and `ind-hi-hplt` (not verified; treated as usable for this experiment only).
- Data B lead: any objection to the alphabetical order of their 25 packs, with a reason, by Fri 13 Nov 2026.
