## Combined validation (15 Nov 2026)

**Harm test of this sheet on every pack with a gold set.** `teams/01-data-a/harmtest/harm_test.py`, run as it is, once per pack with `--rules spec_v1_1/sheets/specv1_1.md --rule all`: each of the 364 rules alone, then all of them in sheet order. Each rule's `pack_id` check keeps it to its own packs.
- **The gold:** Data A's (`teams/01-data-a/gold/`) for the 13 code, English, math and science packs; Data B's (`teams/02-data-b/gold/`) for the 18 Indic packs and cadj-commits. 32 packs in all.
- **The packs:** TSAI's sample packs, 500 docs each: the same files as in the spec v1.1 harm runs and #244 (sha256 checked).
- **Not in this test:** the shared F1 (`f1_rule.py`), which is not a card in the sheet.

| pack | gold docs (limit) | all rules in order: changed + dropped | result | without the gold contradictions |
|---|---|---|---|---|
| code-cpp, code-go, code-java, code-js-ts, code-python, code-rust | 122, 163, 116, 204, 141, 234 | 0 each | PASS | — |
| en-dclm, en-fineweb-edu, en-nemotroncc-synth | 62, 158, 326 | 0 each | PASS | — |
| en-nemotroncc | 129 (1) | 2: `056cc9bc44c927e2` (`DA-A8-003`), `fd16036899796ca4` (`DA-A8-004`) | **FAIL** | 0/127 PASS |
| math-finemath | 86 (1) | 2: `2d328b828fa97706` (`DA-A8-001`), `0f119a596e8b7f63` dropped (`DA-C9-003`) | **FAIL** | 0/84 PASS |
| math-megamath | 26 (1) | 0 | PASS | — |
| sci-finepdfs | 202 (2) | 5: `920855df51f37db8` (`DA-A7-001`); `4b958ac1f45443b5`, `d0a0a41263e845f5`, `eb6ad9726f2d7ddd` (`DA-C7-004`); `b6fd81dbf90b0d17` dropped (`DA-C7-005`, a false positive) | **FAIL** | 1/198 PASS |
| ind-te-sangraha-v | 80 (1) | 2: `01418489e7410bdf`, `85644a4840025b6f` (`DB-C6-001`) | **FAIL** | 0/78 PASS |
| the other 17 Indic packs | 2,113 in all | ind-bn-fw2 2/227, ind-hi-fw2 2/218, ind-hi-indiccorp 2/425, ind-hi-sangraha-v 2/219, ind-bn-sangraha-v 1/137, ind-mr-fw2 1/158, ind-sa-fw2 1/71; 0 on the other 10 | PASS each | — |
| cadj-commits | 413 (4) | 0: no rule runs on a cadj pack | PASS | — |

- **Spec v1.1 adds only its own 11 gold docs**, the ones in the table above. On the other 17 Indic packs, the gold docs changed are exactly those spec v1's own Data B rules change (`DB-A6-017`, `DB-G4-007` …), all within the limit: no v1.1 rule runs there.
- **Every v1.1 gold doc touched is a gold contradiction or a recorded false positive.** Vijay agreed to marking gold contradictions: they are left out of the count for their rule, and re-read at the next gold refresh.
- **Rules that fail on their own:** only `DA-C7-004` (3/202) and `DB-C6-001` (2/80), both on gold contradictions.
- **Scope holds:** on every pack, only the rules that cover it changed a gold doc.
- **No gold set, so NOT TESTABLE:** cadj-notebooks, cadj-stackexchange, ind-ml-fw2, ind-or-fw2, ind-ta-fw2 and ind-ta-sangraha-s.

**Speed (14 Nov).** `spec_v1/run_clean.py` timed the whole `clean()` built from this sheet, shared F1 included, on 500 docs a pack: Apple M4, one core, Python 3.12.10, the best of 3 runs, 0 errors. Spec v1 is as on TSAI main.

| pack | spec v1 → combined, docs/s |
|---|---|
| code-cpp, code-go, code-java, code-js-ts, code-python, code-rust | 500, 556, 625, 1,000, 455, 714 → the same |
| en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth | 455, 625, 714, 1,667 → 455, 625, 556, 1,667 |
| math-finemath, math-megamath | 167, 417 → **122, 227** |
| sci-finepdfs | 125 → **70** |
| ind-te-sangraha-v | 625 → 625 |

On math and science the v1.1 rules add about 1 s and 3 s per 500 docs, after two speed passes (`spec_v1_1/results/sheets/harm_tests.md`, "Speed"). No v1.1 rule loops over tokens. The one loop over characters is `DA-A7-003`'s `str.islower` on non-ASCII lines.
