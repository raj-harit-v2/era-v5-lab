# Spec v1 harm tests

DRAFT. Made by `spec_v1/tools/make_harm_tests.py` on 02 Nov 2026 from `clean.py` (built by `spec_v1/tools/build_clean.py` from `specv1.md`) with the team's `harm_test.py`, run as it is. Each cell: gold docs changed + dropped. Limit: `max(1, floor(1% of gold))`, that is `max(1 document, 1%)` (TSAI decision), each pack on its own gold set, never pooled. An empty gold set is NOT TESTABLE and an error is never a PASS; a result other than PASS is shown after the count.

A rule is tested only on the gold sets of the packs it applies to: its entry in `SCOPE`, the table at the top of `clean.py`. `·` means the rule does not apply to that pack, so it was not run there.

## 1. clean(), the whole cleaner, on each pack

| pack | family | gold docs (limit) | gold changed + dropped | result | whole pack fixed / dropped | rules that do not apply, acting on the whole pack | gold result as `results/cleaner/specv1_validation.json` |
|---|---|---:|---:|---|---:|---|---|
| code-cpp | code | 122 (1) | 0 | PASS | 340 / 10 | none | yes |
| code-go | code | 163 (1) | 0 | PASS | 260 / 44 | none | yes |
| code-java | code | 116 (1) | 0 | PASS | 349 / 11 | none | yes |
| code-js-ts | code | 204 (2) | 0 | PASS | 260 / 22 | none | yes |
| code-python | code | 141 (1) | 0 | PASS | 319 / 16 | none | other snapshot |
| code-rust | code | 234 (2) | 0 | PASS | 236 / 17 | none | yes |
| en-dclm | english | 62 (1) | 0 | PASS | 54 / 9 | none | yes |
| en-fineweb-edu | english | 158 (1) | 0 | PASS | 12 / 1 | none | yes |
| en-nemotroncc | english | 129 (1) | 0 | PASS | 62 / 17 | none | other snapshot |
| en-nemotroncc-synth | english | 326 (3) | 0 | PASS | 32 / 1 | none | yes |
| math-finemath | math | 86 (1) | 0 | PASS | 177 / 13 | none | yes |
| math-megamath | math | 26 (1) | 0 | PASS | 62 / 10 | none | yes |
| sci-finepdfs | sci | 202 (2) | 0 | PASS | 45 / 13 | none | other snapshot |

On the code, math and science packs `clean()` also runs the shared F1 (`spec_v1/tools/f1_rule.py`) last, and `DA-B4-009` leaves `<EMAIL>`: `specv1_validation.json` ran the sheet without them, so these packs may differ from it.

## 2. Each rule alone, on the gold sets of its packs only

### code

| rule | cpp | go | java | js-ts | python | rust | result |
|---|---:|---:|---:|---:|---:|---:|---|
| A1 `DA-A1-001` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| A2 `DA-A2-007` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| A6 `DA-A6-001` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| A4 `DA-A4-002` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| A4 `DA-A4-003` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| B3 `DA-B3-001` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E1 `DA-E1-001` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E1 `DA-E1-004` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E1 `DA-E1-008` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E1 `DA-E1-006` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E1 `DA-E1-005` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E1 `DA-E1-007` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E2 `DA-E2-001` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| C3 `DA-C3-002` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| C4 `DA-C4-002` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E4 `DA-E4-005` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E4 `DA-E4-010` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E4 `DA-E4-009` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E4 `DA-E4-007` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| C1 `DA-C1-004` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| C1 `DA-C1-005` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| B4 `DA-B4-009` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E3 `DA-E3-003` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| E3 `DA-E3-004` | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| F1 `f1_rule.py` | 0 | 0 | 0 | 0 | 0 | 0 | PASS (not run on math-finemath, math-megamath, sci-finepdfs) |

### english

| rule | dclm | fineweb-edu | nemotroncc | nemotroncc-synth | result |
|---|---:|---:|---:|---:|---|
| A1 `DA-A1-004` | 0 | 0 | 0 | 0 | PASS |
| A2 `DA-A2-008` | 0 | 0 | 0 | 0 | PASS |
| A5 `DA-A5-001` | 0 | 0 | 0 | 0 | PASS |
| A3 `DA-A3-002` | 0 | 0 | 0 | 0 | PASS |
| B1 `DA-B1-002` | 0 | 0 | 0 | 0 | PASS |
| B2 `DA-B2-002` | 0 | 0 | 0 | 0 | PASS |
| C3 `DA-C3-001` | 0 | 0 | 0 | 0 | PASS |
| C3 `DA-C3-003` | 0 | 0 | 0 | 0 | PASS |
| C5 `DA-C5-002` | 0 | 0 | 0 | 0 | PASS |
| D4 `DA-D4-001` | 0 | 0 | 0 | 0 | PASS |
| C1 `DA-C1-006` | 0 | 0 | 0 | 0 | PASS |
| C2 `DA-C2-003` | 0 | 0 | 0 | 0 | PASS |
| C5 `DA-C5-005` | 0 | 0 | 0 | 0 | PASS |
| D3 `DA-D3-003` | 0 | 0 | 0 | 0 | PASS |
| B4 `DA-B4-007` | 0 | 0 | 0 | 0 | PASS |
| B4 `DA-B4-008` | 0 | 0 | 0 | 0 | PASS |
| B4 `DA-B4-012` | 0 | 0 | 0 | 0 | PASS |
| B4 `DA-B4-010` | 0 | 0 | 0 | 0 | PASS |
| B4 `DA-B4-011` | 0 | 0 | 0 | 0 | PASS |
| F1 `DA-F1-005` | 0 | 0 | 0 | 0 | PASS |

### math

| rule | finemath | megamath | result |
|---|---:|---:|---|
| A3 `DA-A3-001` | 0 | 0 | PASS |
| A1 `DA-A1-005` | 0 | · | PASS |
| A6 `DA-A6-003` | 0 | · | PASS |
| A5 `DA-A5-002` | 0 | 0 | PASS |
| B2 `DA-B2-001` | 0 | 0 | PASS |
| B4 `DA-B4-001` | 0 | 0 | PASS |
| B5 `DA-B5-001` | 0 | 0 | PASS |
| C5 `DA-C5-001` | · | 0 | PASS |
| D3 `DA-D3-005` | 0 | 0 | PASS |
| C3 `DA-C3-004` | 0 | · | PASS |
| C1 `DA-C1-001` | 0 | · | PASS |
| C2 `DA-C2-001` | 0 | · | PASS |
| C5 `DA-C5-006` | 0 | 0 | PASS |
| C3 `DA-C3-005` | 0 | · | PASS |
| F1 `f1_rule.py` | 0 | 0 | PASS (not run on code-cpp, code-go, code-java, code-js-ts, code-python, code-rust, sci-finepdfs) |

### sci

| rule | finepdfs | result |
|---|---:|---|
| B4 `DA-B4-013` | 0 | PASS |
| B2 `DA-B2-003` | 0 | PASS |
| B5 `DA-B5-002` | 0 | PASS |
| A1 `DA-A1-006` | 0 | PASS |
| A6 `DA-A6-002` | 0 | PASS |
| C1 `DA-C1-007` | 0 | PASS |
| C2 `DA-C2-004` | 0 | PASS |
| C3 `DA-C3-006` | 0 | PASS |
| C4 `DA-C4-003` | 0 | PASS |
| D1 `DA-D1-001` | 0 | PASS |
| F1 `DA-F1-006` | 0 | PASS |
| D3 `DA-D3-004` | 0 | PASS |
| F1 `f1_rule.py` | 0 | PASS (not run on code-cpp, code-go, code-java, code-js-ts, code-python, code-rust, math-finemath, math-megamath) |

## 3. Each disease-code function, on the packs where one of its rules applies

| function | cpp | go | java | js-ts | python | rust | dclm | fineweb-edu | nemotroncc | nemotroncc-synth | finemath | megamath | finepdfs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | · | 0 |
| A2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | · | · | · |
| A6 | 0 | 0 | 0 | 0 | 0 | 0 | · | · | · | · | 0 | · | 0 |
| A4 | 0 | 0 | 0 | 0 | 0 | 0 | · | · | · | · | · | · | · |
| A5 | · | · | · | · | · | · | 0 | 0 | 0 | 0 | 0 | 0 | · |
| A3 | · | · | · | · | · | · | 0 | 0 | 0 | 0 | 0 | 0 | · |
| B1 | · | · | · | · | · | · | 0 | 0 | 0 | 0 | · | · | · |
| B2 | · | · | · | · | · | · | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| B5 | · | · | · | · | · | · | · | · | · | · | 0 | 0 | 0 |
| B3 | 0 | 0 | 0 | 0 | 0 | 0 | · | · | · | · | · | · | · |
| E1 | 0 | 0 | 0 | 0 | 0 | 0 | · | · | · | · | · | · | · |
| E2 | 0 | 0 | 0 | 0 | 0 | 0 | · | · | · | · | · | · | · |
| C3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | · | 0 |
| C4 | 0 | 0 | 0 | 0 | 0 | 0 | · | · | · | · | · | · | 0 |
| C5 | · | · | · | · | · | · | 0 | 0 | 0 | 0 | 0 | 0 | · |
| D4 | · | · | · | · | · | · | 0 | 0 | 0 | 0 | · | · | · |
| E4 | 0 | 0 | 0 | 0 | 0 | 0 | · | · | · | · | · | · | · |
| C1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | · | 0 |
| C2 | · | · | · | · | · | · | 0 | 0 | 0 | 0 | 0 | · | 0 |
| D1 | · | · | · | · | · | · | · | · | · | · | · | · | 0 |
| D3 | · | · | · | · | · | · | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| B4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| E3 | 0 | 0 | 0 | 0 | 0 | 0 | · | · | · | · | · | · | · |
| F1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Affected gold IDs are in `results/cleaner/specv1_<pack>_harm.json`. No document text is kept.

## Not run

| family | pack | why |
|---|---|---|
