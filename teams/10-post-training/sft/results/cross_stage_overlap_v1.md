# Cross-stage overlap: SFT data v1 (OCR-2 pack) against the RL side

Record `cross_stage_overlap_v1.json`, built by `cross_stage_overlap.py`. Counts and hashes only: no statement text,
problem id or key is in this file. The key lists are private. Nothing in the pack or the RL pool was changed;
this record is the flags a later ruling can apply.

The unit is the distinct problem. The pack has 418,496 training rows over 15,341 distinct problems (70 shards; tokens 2,661,573,319, p1536 token counts from the build's per-row stats).

## Result

| RL-side set | RL problems | Found in the pack (confirmed) | key / norm / shingle | Also `possible` only | Distinct pack problems | Pack rows | Pack tokens |
|---|---:|---:|---|---:|---:|---:|---:|
| (a) RL data v1 code pool | 3,577 | 2,791 (78%) | 2708 / 36 / 47 | 30 | 2,958 | 76,949 | 434,334,903 |
| (b1) RL held-out, 15 Nov runs (E1; includes the pilot's 48) | 96 | 78 (81%) | 74 / 1 / 3 | 0 | 81 | 2,259 | 12,225,172 |
| (b2) RL held-out, E10 plan | 160 | 133 (83%) | 131 / 2 / 0 | 3 | 142 | 4,875 | 20,893,440 |
| (c) effort suite, code slots | 30 | 26 (87%) | 26 / 0 / 0 | 0 | 26 | 827 | 4,529,215 |

The sets overlap: (b1) and (b2) are drawn from the pool, the effort suite is not in the pool (the close flag removes it). No RL held-out set is defined in RL data v1 itself (`rl_data_v1_close.json` has no held-out flag); (b1) and (b2) are the lists the 15 Nov experiments and the E10 plan used.

Route into the pack (confirmed matches). A match by dataset id alone would find only the code_contests route.

| Set | Through code_contests rows | Only through TACO or APPS rows | Also through TACO or APPS rows |
|---|---:|---:|---:|
| (a) RL data v1 code pool | 243 | 2,548 | 2,661 |
| (b1) RL held-out, 15 Nov runs (E1; includes the pilot's 48) | 7 | 71 | 74 |
| (b2) RL held-out, E10 plan | 14 | 119 | 125 |
| (c) effort suite, code slots | 7 | 19 | 19 |

Per shard: the JSON holds rows and tokens for all 70 shards for each set. Pool overlap per shard ranges 0 to 3,703 rows.

Against the 4-shard count of 16 Nov (the G10 recipe session's measurement: 2,384 of 3,577 with a statement in shards 0-3, first rule): the same four shards under this rule give 2,362 confirmed and 2,384 confirmed or possible, 14,531 pack rows. The old count was over the rendered user turn of each row and the old rule counted siblings; this one is over distinct problems.

## Validation (read on 16 Nov, private)

- First rule (13-word shingles, at least 20% of the RL statement, whole pool): 77 non-exact pairs read: 55 the same problem, 22 a sibling problem of the same series (precision 71%). Band 0.20 to 0.65: 8 of 30 the same. Band 0.65 and above: 47 of 47 the same (the differences were exponent and ordinal formatting). Highest sibling coverage 0.615.
- Normalised-text tier: 12 of 12 read are the same problem (markup differences only).
- Exact-key tier: identical text by construction; 14 shortest RL statements read for stub collisions: 2 are example-only stubs, the rest are full short problems.
- Near misses just under the first rule (coverage 0.09 to 0.20): 27 read, 26 different problems, 1 same task in other wording (not counted), 0 the same statement. No missed copy was found there; this says nothing about copies whose text was rewritten more.
- Change made once, after reading: confirm level raised from 0.20 to 0.65; 0.20-0.65 is kept as the separate `possible` tier. The 0.65 level was chosen after reading these pairs, so the precision at 0.65 is in-sample; the margin to the nearest sibling (0.615) is thin.

## Sizing the choices (no choice is made here)

| Choice | Pack problems | Pack rows | Pack tokens | Share of pack rows | Share of pack tokens | Share of v1 admitted tokens |
|---|---:|---:|---:|---:|---:|---:|
| (i) SFT drops every problem found in the RL pool | 2,958 | 76,949 | 434,334,903 | 18.4% | 16.3% | 16.3% |
| minimum: SFT drops problems of (b1), (b2), (c) only | 247 | 7,877 | 37,254,643 | 1.9% | 1.4% | 1.4% |
| minimum, counting the `possible` tier too (upper bound) | 250 | 7,958 | 37,717,518 | 1.9% | 1.4% | 1.4% |
| minimum, narrower: (b1) and (c) only | 106 | 3,048 | 16,702,769 | 0.7% | 0.6% | 0.6% |
| minimum, narrower, counting the `possible` tier too (upper bound) | 106 | 3,048 | 16,702,769 | 0.7% | 0.6% | 0.6% |
| (i) plus the minimum | 2,986 | 77,788 | 439,005,916 | 18.6% | 16.5% | 16.5% |
| (i) counting the `possible` tier too (upper bound) | 2,965 | 77,169 | 435,497,462 | 18.4% | 16.4% | 16.3% |

Shares are of the pack's rows and of the pack's tokens (two different columns: a problem's rows are not all the same length, so the two shares differ).

## Sensitivity to the confirm level

The confirm level (0.65) was set after reading pairs. How many problems sit within 0.05 of it (only problems that rest on shingle coverage; key and norm matches do not depend on it):

| RL-side set | `possible` with best coverage just below the level (would be confirmed at level - band) | confirmed with best coverage just above it (would drop at level + band) |
|---|---:|---:|
| (a) RL data v1 code pool | 2 | 1 |
| (b1) RL held-out, 15 Nov runs (E1; includes the pilot's 48) | 0 | 0 |
| (b2) RL held-out, E10 plan | 0 | 0 |
| (c) effort suite, code slots | 0 | 0 |


The other direction: the OCR-2 held-out eval split (8,507 rows, 317 problems) against the RL pool: 73 pool problems (2%) are in it, 73 held-out problems, 1,948 held-out rows (66 key / 1 norm / 6 shingle). Keeping the held-out split out of the RL training pool would drop these pool problems.

(ii) RL drops every pool problem found in the pack: 2,791 of 3,577 go, 786 stay; of the 754 easiest-rung problems 663 go and 91 stay.

Mix areas: the pack is the whole code area and 99.8% of the admitted v1 tokens, so its share of lost tokens is also the code area's share lost. The other areas hold almost nothing admitted (`sft_data_v1.md`, area budget); a budget anchored on the code area shrinks every area's need with it.

`Distinct pack problems` counts family keys: one RL problem can match two (the same text under TACO and under APPS), so it can exceed the number of RL problems found.

## Rule and inputs

Rule: key (same family_sha256), norm (same lower-cased [a-z0-9] words), shingle (RL coverage >= confirm); possible (coverage in [possible, confirm)) is reported apart and never counted as a match. Shingles: 13 words, confirm at 0.65, possible from 0.2.

| Input | sha256 or size |
|---|---|
| rl_cc_sha256 | `91ee99512f0411aea2de4ca5eaf10b87b2d8f785ca73747bf8deb45dd6ea9be0` |
| effort_manifest_sha256 | `fb8c09a4940b800c50de5ea7eaf51eb40afd62740a1919b08282f72910e97f8b` |
| source_index_sha256 | `285aa87484c1269f5da9c62cd031e06b19158c760f4cc8720a1d3df3e0f535bf` |
| rowstats_sha256 | `ba824f617c7ebfdb6b867f35cf7efd0594516ba9ed297c23f012d2520d6c4d55` |
| pack_manifest_sha256 | `fab395750fad3329c6b612493641f37c42792e46219a521fca74c30e21b7783b` |
| rung_ids_sha256 | `95692a349358609ca52436532cd384f020dc7060ba3292a4bb7d8971ad2360e4` |
| sft_manifest_sha256 | `ec335ce64b07e701f1e6ba857a977ec194450c1dd3f7ca183fe8ba6a902e2d07` |
| id list rl_code_pool (3577) | `4ad35ee70378729e5a979e33efac537a41cf35e535c29ee3da620565c5abb2fe` |
| id list heldout_e1_15nov (96) | `e05053a048c76ef87f6c55022a9211405d043bdfab386bf2bfe76cd8c7522a26` |
| id list heldout_e10_planned (160) | `8d3a794e4b5606f73467d2924689c66687a0e71e5a995671ade65f1516042752` |
| id list effort_suite_code (30) | `f2cd483a5357e5c9ea86dec9c93ee0ba33e96a0d4109b093b15c35f94db78360` |
| row-stat files | 70 |
