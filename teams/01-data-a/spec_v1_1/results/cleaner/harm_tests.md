# clean() harm tests: spec v1.1

`spec_v1_1/clean.py` (sha256 `6a57276c0e83…`, built from `sheets/specv1_1.md`) on TSAI's 500-doc sample packs, one for each pack it has rules for, 17 Nov 2026. It was run on the samples only, not on the full packs.
- **The tool:** `spec_v1/validate/make_harm_tests.py`, run through `use_clean.py`, with `harmtest/harm_test.py` run as it is. On each pack it runs:
  - `clean()` on the gold docs;
  - each rule alone on the gold docs;
  - every rule that doesn't cover the pack, on all 500 docs of the sample pack, which must change nothing.
- **The gold:** Data A's (`teams/01-data-a/gold/`) for 13 packs, and Data B's (`teams/02-data-b/gold/`) for 18 Indic packs. Each pack is tested on its own gold set. The limit is `max(1, floor(1% of gold))`.
- **The packs:** TSAI's sample packs, 500 docs each, the same files as in #244 (sha256 checked).

From `teams/01-data-a`, where `<checkout>` is a copy of the repository whose `teams/01-data-a/gold/` also holds Data B's Indic gold files (the harness reads gold from there):

```
python3 -I spec_v1_1/use_clean.py spec_v1/validate/make_harm_tests.py <checkout> <packs folder> --out <out>/harm_tests.md --results <out>
```

Last lines (1 min 34 s; exit 1 because of the gold contradictions):

```
ind-te-fw2 PASS gold 0 0 | not passing: [] | out of scope acting: []
ind-te-sangraha-s PASS gold 0 0 | not passing: [] | out of scope acting: []
ind-te-sangraha-v FAIL gold 2 0 | not passing: [('DB-C6-001', 'FAIL'), ('C6', 'FAIL')] | out of scope acting: []
wrote <out>/harm_tests.md | not run: []
```

| pack | gold docs (limit) | `clean()`: changed + dropped | result | without the gold contradictions |
|---|---|---|---|---|
| code-cpp, code-go, code-java, code-js-ts, code-python, code-rust | 122, 163, 116, 204, 141, 234 | 0 each | PASS | — |
| en-dclm, en-fineweb-edu, en-nemotroncc-synth | 62, 158, 326 | 0 each | PASS | — |
| en-nemotroncc | 129 (1) | 2: `056cc9bc44c927e2` (`DA-A8-003`), `fd16036899796ca4` (`DA-A8-004`) | **FAIL** | 0/127 PASS |
| math-finemath | 86 (1) | 2: `2d328b828fa97706` (`DA-A8-001`), `0f119a596e8b7f63` dropped (`DA-C9-003`) | **FAIL** | 0/84 PASS |
| math-megamath | 26 (1) | 0 | PASS | — |
| sci-finepdfs | 202 (2) | 5: `920855df51f37db8` (`DA-A7-001`); `4b958ac1f45443b5`, `d0a0a41263e845f5`, `eb6ad9726f2d7ddd` (`DA-C7-004`); `b6fd81dbf90b0d17` dropped (`DA-C7-005`, a false positive) | **FAIL** | 1/198 PASS |
| ind-te-sangraha-v | 80 (1) | 2: `01418489e7410bdf`, `85644a4840025b6f` (`DB-C6-001`) | **FAIL** | 0/78 PASS |
| ind-bn-fw2, ind-hi-fw2, ind-hi-indiccorp | 227 (2), 218 (2), 425 (4) | 2 each (1 changed, 1 dropped) | PASS | — |
| ind-hi-sangraha-v | 219 (2) | 2 | PASS | — |
| ind-bn-sangraha-v, ind-kn-fw2, ind-mr-fw2, ind-sa-fw2, ind-ta-sangraha-v | 137, 115, 158, 71, 141 | 1 each | PASS | — |
| ind-gu-fw2, ind-hi-hplt, ind-hi-sangraha-s, ind-kn-sangraha-s, ind-kn-sangraha-v, ind-mr-sangraha-v, ind-te-fw2, ind-te-sangraha-s | 80, 37, 24, 22, 99, 99, 17, 24 | 0 each | PASS | — |

**Why 4 packs FAIL.** A pack fails when `clean()` changes or drops more of its gold docs than the limit. On these 4 packs, the docs over the limit are the 11 that spec v1.1's rules touch:

| pack | gold doc | rule | what the doc holds |
|---|---|---|---|
| en-nemotroncc | `056cc9bc44c927e2` | `DA-A8-003` | two sentences run together, with no space after the full stop |
| en-nemotroncc | `fd16036899796ca4` | `DA-A8-004` | a quote run into the speaker's name |
| math-finemath | `2d328b828fa97706` | `DA-A8-001` | two sentences run together, with no space after the full stop |
| math-finemath | `0f119a596e8b7f63`, dropped | `DA-C9-003` | a converter template page |
| sci-finepdfs | `920855df51f37db8` | `DA-A7-001` | a word split in extraction |
| sci-finepdfs | `4b958ac1f45443b5`, `d0a0a41263e845f5`, `eb6ad9726f2d7ddd` | `DA-C7-004` | empty image links |
| sci-finepdfs | `b6fd81dbf90b0d17`, dropped | `DA-C7-005` | a complete certificate of 220 characters, under the rule's 250 |
| ind-te-sangraha-v | `01418489e7410bdf`, `85644a4840025b6f` | `DB-C6-001` | a bare `..`, which the pack's reader labelled C6 in other docs |

- **10 are gold contradictions:** the gold marks the doc clean, but it holds the disease its rule targets.
- **1 is a false positive:** `DA-C7-005` drops `b6fd81dbf90b0d17`, a complete short doc. That is within the rule's own limit (1 of 202).
- **Without the 10 gold contradictions, all 4 packs pass:** en-nemotroncc 0/127, math-finemath 0/84, sci-finepdfs 1/198 and ind-te-sangraha-v 0/78. As `sheets/NEW_DISEASES.md` records (section "Open"), gold contradictions are left out of the count for their rule only, and re-read at the next gold refresh.
- **None of these rules is quarantined or turned off.** Like every rule of `sheets/specv1_1.md`, they are candidates and run in `clean.py`. The re-read of these gold docs at the next gold refresh is a release gate.
- **Spec v1.1 adds only these 11 gold docs.**
- **The other Indic gold docs** are changed by spec v1's own rules, exactly as spec v1's `clean.py` on TSAI main changes them, all within the limit. On ind-kn-fw2 and ind-ta-sangraha-v, that rule is the shared F1 (`f1_rule.py`).
- **Scope holds:** on all 31 sample packs, no rule that doesn't cover the pack changed a doc.
- **Not tested:**
  - cadj-commits: `clean()` has no rules for it and keeps every doc (`tests/test_clean.py`);
  - no gold set, so NOT TESTABLE: cadj-notebooks, cadj-stackexchange, ind-ml-fw2, ind-or-fw2, ind-ta-fw2 and ind-ta-sangraha-s.
