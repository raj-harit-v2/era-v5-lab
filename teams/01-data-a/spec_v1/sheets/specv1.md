# Medicine sheet: Data A — consolidated spec v1 (contributors retained per rule)

Status: **DRAFT / CANDIDATE**. Consolidates the four local medicine sheets; no rule is approved by this document. Follows [medicine_TEMPLATE.md](../../../diagnosis/templates/medicine_TEMPLATE.md): each medicine retains disease/count/examples, words and Python, action, harm evidence, and side effects. Compiler identity is not inferred from contributor handles.

## Scope, dispatch and executable contract

The 13 packs are partitioned into code (six), English prose (four), math (two), and science (one). `pack_id` is required and must come from trusted pack provenance; language alone cannot distinguish English prose, math and scientific PDFs. Missing or unknown pack IDs pass unchanged for inspection and are **not eligible for release**. Preserve original source metadata, text and licensing separately for audit.

Each Python fence is one independent rule module. Load with `teams/01-data-a/tools/harm_test.py`, which isolates sheet blocks. Concatenating fences into one Python namespace or using `medicine_extract.py` on this compiled sheet is unsupported: shared names (`medicine`, `_std`, `LANGS`, helpers) have different meanings. All IDs in this document are unique; renamed IDs are provisional local aliases, require registry reconciliation, and preserve `SOURCE_RULE_ID`. No existing registry is changed.

Run in medicine-section order, route to exactly one family, carry each fixed text into the next rule, and stop on the first drop. Code, English and math retain their source order; science retains its separately measured source order. A drop means exclude/quarantine the complete record and retain audit provenance. Do not serialize dropped private text into public reports. A rule exception or timeout is ERROR, never keep/PASS.

## Binding clash resolutions

| Clash | Resolution in this spec |
|---|---|
| Gold-control minimum-one exception | The repository harm policy controls: `changed + dropped <= max(1, floor(gold_count / 100))`, per rule and combined pipeline **per pack**, at the default 1% limit. At least one affected document is allowed for a nonempty gold set. |
| Same language across families | Outer pack guard on every rule; retain source language and math pack checks. English rules never reach math/science/code. |
| Repeated rule IDs and Python bindings | Unique provisional IDs mapped below; isolated block namespaces. Source bodies otherwise retained, with dispatch adapters. |
| A1/A2 differ across families | Keep family-specific handling: code retains form feed; prose may remove it. Preserve ZWJ/ZWNJ; do not apply prose bidi stripping to unrelated scripts. |
| A3 mojibake / A5 normalization | Retain distinct scoped repairs; no global NFKC. Math superscripts and operators must survive. Source order remains unchanged pending interaction evidence. |
| B2 tag stripping versus scientific/math semantics | No cross-family tag stripper. Science uses reviewed sup/sub conversion and code-fence protection. Math B2 can turn `x<sup>2</sup>` into `x2`: retain only as an unapproved candidate; independent semantic review is a release gate. |
| B4 placeholders versus valid examples | Keep family-specific literal patterns; science retains sample emails. No blanket replacement of template syntax in arbitrary code or math. |
| C1/C2 versus licences, headers and repeated equations | Keep scoped rules and science ID gates. Preserve licence/attribution in provenance before deleting notices. Gold preservation alone cannot approve deletion of meaningful repetition. |
| Code E1/E2/C3/C4 drops versus E4 stripping | Drops first, then strips, as the code source requires. Keep overlapping E4 and E3 rules in source order; distinct detectors are not merged by disease code. |
| C3/C4 repair versus deletion | Preserve each family decision. Science uses reviewed exclusions and bounded repairs; reject longest-article-only extraction. Any split must emit all articles with parent provenance. |
| D1 versus D3 | Science keeps natural multilingual passages; only reviewed wrong-language IDs are quarantined. English D3 deletion remains English-only and requires review of legitimate quotations before approval. |
| F1 privacy differs by family | English keeps its final typed-placeholder rule; science quarantines nine reviewed IDs and gates remaining F1 labels. Code/math sheets do not provide complete F1 coverage. Shared `../tools/f1_rule.py` (TSAI, 1 Nov) runs last on the code, math and science packs through `clean.py`'s `SCOPE`, after `DA-F1-006` on science, and never on English; it is not a sheet block. Gold harm 0 on math and science (`results/cleaner/harm_tests_f1_math_sci.md`); its known misses keep full privacy coverage a release gate. |
| Counts, examples and qualification | Do not add overlapping diagnosis counts. Counts of five or fewer are supplementary coverage, not evidence of the template's >5 criterion. Keep them visibly for provenance and safety coverage. Missing exact examples block template completion. |
| Source medicine versus action prose | Runnable callable determines measured behavior. Some math C3 wrapper paths keep tuple/drop outcomes despite descriptive drop wording; preserve implementation, disclose the discrepancy, and require adjudication before approval. |

## Harm acceptance and evidence gaps

Acceptance uses the updated `harm_test.py` gold-control policy: no errors and at most `max(1, floor(1% × n))` affected documents for each nonempty gold set, per rule and combined pipeline. For example, 1/40 passes (one-document allowance), 2/40 fails, and 2/204 passes. Empty gold sets remain untestable.

A gold document is changed only if a surviving output differs from original text; a dropped document is counted separately, once. Combined impact counts unique affected IDs, never the sum of independent rule counts. Zero gold rows, missing gold IDs, errors or timeouts make the test untestable/error. Run positive-case checks separately: low harm does not establish recall, semantic correctness or privacy coverage.

The four source sheets do not consistently contain three exact `(doc_id, characters)` quotations per medicine. Math cards generally contain no document examples; many code/English cards list IDs only; science uses descriptions and intentionally withholds private values. **Fresh exact-character execution excerpts are added per card below; cards with fewer than three publishable examples remain incomplete.** Do not fabricate snippets, and do not publish private spans to satisfy the template. Supply reviewed non-private exact characters or an access-controlled privacy evidence record before freeze. The historical science sources disagree on labels and the old 40-document gold snapshot (`eee25e81417bc1b7`). The supplied latest science gold has 198 rows and zero measured harm; its digest is recorded below. Inherited science measurements describe the old snapshot; 1/40 (2.50%) passes under the minimum-one exception, while gold eligibility remains a separate review issue. Gold must be adjudicated independently, never edited merely to pass a test.

Source code remains CANDIDATE even after a measured pass. Semantic side effects, reviewer approval, missing examples, F1 coverage and provisional registry IDs remain release gates. Rules for <=5 observations and preservation-only science D3 are supplementary cards.

## Source snapshots

| Source | SHA-256 |
|---|---|
| [medicine_code.md](medicine_code.md) | `e096bea29f0634a76ae99600753527aa266a1d69ed06c4fd88e800b42c8bf13b` |
| [medicine_english.md](medicine_english.md) | `904c63b621515fc07bdd07cfff3553b6cff49504c89f41c2ec1fce2d27b0652c` |
| [medicine_math.md](medicine_math.md) | `d80f46be988242e92774802497e2d78360295e3c57c7e1a0a1a88f5c914a6224` |
| [medicine_sci.md](medicine_sci.md) | `5f1e743253062fee2b91d3e04f13b2c302eddae4a9c02b0f54144d2252e1c411` |

## Identity mapping

| Medicine | Family | Disease | Source identity | Consolidated identity |
|---|---|---|---|---|
| 1 | code | A1 | `DA-A1-001` | `DA-A1-001` |
| 2 | code | A2 | `DA-A2-007` | `DA-A2-007` |
| 3 | code | A6 | `DA-A6-001` | `DA-A6-001` |
| 4 | code | A4 | `DA-A4-002` | `DA-A4-002` |
| 5 | code | A4 | `DA-A4-003` | `DA-A4-003` |
| 6 | code | B3 | `DA-B3-001` | `DA-B3-001` |
| 7 | code | E1 | `DA-E1-001` | `DA-E1-001` |
| 8 | code | E1 | `DA-E1-004` | `DA-E1-004` |
| 9 | code | E1 | `DA-E1-008` | `DA-E1-008` |
| 10 | code | E1 | `DA-E1-006` | `DA-E1-006` |
| 11 | code | E1 | `DA-E1-005` | `DA-E1-005` |
| 12 | code | E1 | `DA-E1-007` | `DA-E1-007` |
| 13 | code | E2 | `DA-E2-001` | `DA-E2-001` |
| 14 | code | C3 | `DA-C3-002` | `DA-C3-002` |
| 15 | code | C4 | `DA-C4-002` | `DA-C4-002` |
| 16 | code | E4 | `DA-E4-005` | `DA-E4-005` |
| 17 | code | E4 | `DA-E4-010` | `DA-E4-010` |
| 18 | code | E4 | `DA-E4-009` | `DA-E4-009` |
| 19 | code | E4 | `DA-E4-007` | `DA-E4-007` |
| 20 | code | C1 | `DA-C1-004` | `DA-C1-004` |
| 21 | code | C1 | `DA-C1-005` | `DA-C1-005` |
| 22 | code | B4 | `DA-B4-009` | `DA-B4-009` |
| 23 | code | E3 | `DA-E3-003` | `DA-E3-003` |
| 24 | code | E3 | `DA-E3-004` | `DA-E3-004` |
| 25 | english | A1 | `DA-A1-004` | `DA-A1-004` |
| 26 | english | A2 | `DA-A2-008` | `DA-A2-008` |
| 27 | english | A5 | `DA-A5-001` | `DA-A5-001` |
| 28 | english | A3 | `DA-A3-002` | `DA-A3-002` |
| 29 | english | B1 | `DA-B1-002` | `DA-B1-002` |
| 30 | english | B2 | `DA-B2-002` | `DA-B2-002` |
| 31 | english | C3 | `DA-C3-001` | `DA-C3-001` |
| 32 | english | C3 | `DA-C3-002` | `DA-C3-003` |
| 33 | english | C5 | `DA-C5-002` | `DA-C5-002` |
| 34 | english | D4 | `DA-D4-001` | `DA-D4-001` |
| 35 | english | C1 | `DA-C1-006` | `DA-C1-006` |
| 36 | english | C2 | `DA-C2-003` | `DA-C2-003` |
| 37 | english | C5 | `DA-C5-005` | `DA-C5-005` |
| 38 | english | D3 | `DA-D3-003` | `DA-D3-003` |
| 39 | english | B4 | `DA-B4-007` | `DA-B4-007` |
| 40 | english | B4 | `DA-B4-008` | `DA-B4-008` |
| 41 | english | B4 | `DA-B4-009` | `DA-B4-012` |
| 42 | english | B4 | `DA-B4-010` | `DA-B4-010` |
| 43 | english | B4 | `DA-B4-011` | `DA-B4-011` |
| 44 | english | F1 | `DA-F1-005` | `DA-F1-005` |
| 45 | math | A3 | `DA-A3-001` | `DA-A3-001` |
| 46 | math | A1 | `DA-A1-001` | `DA-A1-005` |
| 47 | math | A6 | `DA-A6-001` | `DA-A6-003` |
| 48 | math | A5 | `DA-A5-001` | `DA-A5-002` |
| 49 | math | B2 | `DA-B2-001` | `DA-B2-001` |
| 50 | math | B4 | `DA-B4-001` | `DA-B4-001` |
| 51 | math | B5 | `DA-B5-001` | `DA-B5-001` |
| 52 | math | C5 | `DA-C5-001` | `DA-C5-001` |
| 53 | math | D3 | `DA-D3-001` | `DA-D3-005` |
| 54 | math | C3 | `DA-C3-001` | `DA-C3-004` |
| 55 | math | C1 | `DA-C1-001` | `DA-C1-001` |
| 56 | math | C2 | `DA-C2-001` | `DA-C2-001` |
| 57 | math | C5 | `DA-C5-002` | `DA-C5-006` |
| 58 | math | C3 | `DA-C3-002` | `DA-C3-005` |
| 59 | sci | B4 | `cure_b4` | `DA-B4-013` |
| 60 | sci | B2 | `cure_b2` | `DA-B2-003` |
| 61 | sci | B5 | `cure_b5` | `DA-B5-002` |
| 62 | sci | A1 | `cure_a1` | `DA-A1-006` |
| 63 | sci | A6 | `cure_a6` | `DA-A6-002` |
| 64 | sci | C1 | `cure_c1` | `DA-C1-007` |
| 65 | sci | C2 | `cure_c2` | `DA-C2-004` |
| 66 | sci | C3 | `cure_c3` | `DA-C3-006` |
| 67 | sci | C4 | `cure_c4` | `DA-C4-003` |
| 68 | sci | D1 | `cure_d1` | `DA-D1-001` |
| 69 | sci | F1 | `cure_f1` | `DA-F1-006` |
| 70 | sci | D3 | `cure_d3` | `DA-D3-004` |

## Fresh validation

<!-- VALIDATION -->

Fresh local execution using the repository loader, mutation checks, timeouts and pipeline runner; verdicts use the repository policy: at most `max(1, floor(gold_count / 100))` changed-or-dropped gold documents per rule and combined pipeline, per pack. Reports contain IDs and digests only. `pack_id` is supplied from each validated pack filename when absent in Parquet.

| Pack | Gold n | Gold changed / dropped | Result | Full pack fixed / dropped | Errors (gold / pack) |
|---|---:|---:|---|---:|---:|
| code-cpp | 122 | 0 / 0 | PASS | 343 / 10 | 0 / 0 |
| code-go | 163 | 0 / 0 | PASS | 265 / 44 | 0 / 0 |
| code-java | 116 | 0 / 0 | PASS | 350 / 11 | 0 / 0 |
| code-js-ts | 204 | 0 / 0 | PASS | 264 / 22 | 0 / 0 |
| code-python | 142 | 0 / 0 | PASS | 325 / 16 | 0 / 0 |
| code-rust | 234 | 0 / 0 | PASS | 238 / 17 | 0 / 0 |
| en-dclm | 62 | 0 / 0 | PASS | 54 / 9 | 0 / 0 |
| en-fineweb-edu | 158 | 0 / 0 | PASS | 12 / 1 | 0 / 0 |
| en-nemotroncc | 34 | 0 / 0 | PASS | 62 / 17 | 0 / 0 |
| en-nemotroncc-synth | 326 | 0 / 0 | PASS | 32 / 1 | 0 / 0 |
| math-finemath | 86 | 0 / 0 | PASS | 176 / 13 | 0 / 0 |
| math-megamath | 26 | 0 / 0 | PASS | 37 / 10 | 0 / 0 |
| sci-finepdfs | 198 | 0 / 0 | PASS | 32 / 12 | 0 / 0 |

Independent gold rules failing the repository minimum-one limit: none.

All other independently tested in-scope rules passed. Every out-of-pack guard passed on all source documents. Results apply to the snapshots recorded in [results/specv1_validation.json](results/specv1_validation.json). A failed candidate is retained for review and blocks release; it is not silently disabled to improve harm numbers.

Reproduce from the repository root (Python requires `pyarrow` and `ftfy`):

```bash
python3 teams/01-data-a/spec_v1/scripts/validate_specv1.py \
  --packs /home/vijay/projects/erav5/erav5-lab-other-files/packs \
  --gold /home/vijay/projects/erav5/era-v5-lab-second-clone/teams/01-data-a/gold
```


## Medicine 1 — code / A1 / `DA-A1-001`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-A1-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A1 invisible junk characters. Labelled rows: go 0, rust 1, js-ts 1, java 1, cpp 12, python 0. Examples: `2faccaa1d7a77d70`, `91cf7be64838e0d0`, `beae2c42d8a34ccc`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `782bc9665f0acdf7` (code-cpp), original offset 0: `"\ufeff/* <NAME>, \u041a\u041d, 50\u0411, 146"` (fix).
- `de12a2fd152768d6` (code-cpp), original offset 0: `"\ufeff#include \"stdafx.h\"\n#in"` (fix).
- `6cdc9866d4264258` (code-cpp), original offset 0: `"\ufeff#include \"NeuralStructu"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Delete U+FEFF (BOM).

```python
RULE_ID = "DA-A1-001"
SOURCE_RULE_ID = "DA-A1-001"
CODE = "A1"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-cpp"  # pack whose medicine this came from
AUTHOR = "TharunSivamani"
import re

def remove_bom_characters(text: str) -> str:
    return text.replace("\ufeff", "")


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(remove_bom_characters(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 0, rust 1, js-ts 1, java 1, cpp 12, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Only the BOM: other invisible characters of A1 (U+200B, bidi marks, soft hyphen) are not treated, and no labelled row needs it.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-cpp sheet, PR 9. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 2 — code / A2 / `DA-A2-007`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-A2-007`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A2 control characters. Labelled rows: go 1, rust 6, js-ts 17, java 44, cpp 47, python 2. Examples: `34133f5414afff81`, `182c2cf59a3fa4f1`, `2f34546793ed7faf`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `09b5f5db05cc311d` (code-cpp), original offset 53: `"tdafx.h\"\r\n#include \"PlaceholderU"` (fix).
- `d5e1b337f212f4e2` (code-cpp), original offset 97: `"////////\r\n * File:        winstl"` (fix).
- `11edb16ce89987d8` (code-cpp), original offset 24: `"_tree.h\"\r\n#include <assert.h>\r\nu"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** CRLF and lone CR become LF; delete the other C0 control characters and DEL. Tab, newline and form feed stay.

```python
RULE_ID = "DA-A2-007"
SOURCE_RULE_ID = "DA-A2-007"
CODE = "A2"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

CTRL = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f]")

def medicine_a2(doc):
    t = CTRL.sub("", doc["text"].replace("\r\n", "\n").replace("\r", "\n"))
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_a2(doc), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 1, rust 6, js-ts 17, java 44, cpp 47, python 17.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Keeps form feed, which the A2 definition lists, because source code uses it as whitespace. U+0080 to U+009F are not treated.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 3 — code / A6 / `DA-A6-001`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-A6-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A6 mixed script (look-alike letters). Labelled rows: go 2, rust 0, js-ts 0, java 0, cpp 0, python 0. Examples: `48b3b124a7aaa5fc`, `64ed179e7e5c3d21`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `782bc9665f0acdf7` (code-cpp), original offset 390: `"\t\t// \u0446\u0438\u0444\u0440a \u043d\u0430 \u0447\u0438\u0441\u043b\u043e 1 \u0438 2\n\tdoubl"` (fix).
- `64ed179e7e5c3d21` (code-go), original offset 1319: `"and(\"int\u0441\", \"Interrupt Client\")\n"` (fix).
- `48b3b124a7aaa5fc` (code-go), original offset 53: `"<evorui \u0430t gm\u0430il d\u03bft c\u03bfm>, All r"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Cyrillic look-alike letters inside words that also have Latin letters become Latin.

```python
RULE_ID = "DA-A6-001"
SOURCE_RULE_ID = "DA-A6-001"
CODE = "A6"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

HOMO = str.maketrans("аеорсухіјѕАВЕКМНОРСТХІЈЅ", "aeopcyxijsABEKMHOPCTXIJS")

MIXED = re.compile(r"\b(?=\w*[A-Za-z])(?=\w*[Ѐ-ӿ])\w+\b")

def medicine_a6(doc):
    t = MIXED.sub(lambda m: m.group().translate(HOMO), doc["text"])
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_a6(doc), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 2, rust 0, js-ts 0, java 0, cpp 1, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Can turn an obfuscated e-mail address back into plain text, so the data-safety stage runs after it.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 4 — code / A4 / `DA-A4-002`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-A4-002`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A4 replacement characters. Labelled rows: go 1, rust 0, js-ts 0, java 2, cpp 0, python 0. Examples: `2a92a9a8489c5ea2`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `2a92a9a8489c5ea2` (code-go), original offset 17244: `"= \"E\"){\n\t\t\t// \ufffd\ufffd\u0238\n\t\t\thistorydata"` (fix).

**Example gap:** 1/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Delete a `//` comment that holds U+FFFD and no ASCII letter or digit. An author-quoted U+FFFD stays (ruling 7).

```python
RULE_ID = "DA-A4-002"
SOURCE_RULE_ID = "DA-A4-002"
CODE = "A4"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

LOST = re.compile(r"[ \t]*//[^\n\w]*�[^\nA-Za-z0-9]*$", re.M)

def medicine_a4(doc):
    t = LOST.sub("", doc["text"])
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_a4(doc), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 1, rust 0, js-ts 0, java 0, cpp 0, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** U+FFFD in a string, or in a comment with words, stays.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 5 — code / A4 / `DA-A4-003`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-A4-003`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A4 replacement characters. Labelled rows: go 1, rust 0, js-ts 0, java 2, cpp 0, python 0. Examples: `912c53fa71c7d9ad`, `9b95cf192922d106`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `912c53fa71c7d9ad` (code-java), original offset 2833: `" car apr\ufffds s'\ufffdtre arr\ufffdt\ufffd le robo"` (fix).
- `9b95cf192922d106` (code-java), original offset 136: `"ime 2017\ufffd\ufffd3\ufffd\ufffd13\ufffd\ufffd \ufffd\ufffd\ufffd\ufffd9:59:26\n *"` (fix).

**Example gap:** 2/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** In comment lines, U+FFFD between letters becomes a space and other U+FFFD is deleted.

```python
RULE_ID = "DA-A4-003"
SOURCE_RULE_ID = "DA-A4-003"
CODE = "A4"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'java'}
ORIGIN = "code-java"  # packs it runs on
SOURCE = "code-java"  # pack whose medicine this came from
AUTHOR = "vaibh27"
import re

COMMENT_LINE = re.compile(r"(?m)^[ \t]*(?://|/?\*).*$")

def m8_clean_replacement_chars(t: str) -> str:
    def fix(m):
        return re.sub("\ufffd+", "", re.sub(r"(?<=[^\s\ufffd])\ufffd+(?=[^\s\ufffd])", " ", m.group()))
    return COMMENT_LINE.sub(lambda m: fix(m) if "\ufffd" in m.group() else m.group(), t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m8_clean_replacement_chars(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** java. **Docs it touches:** java 2.
4. **Harm test:** java 0.00% (0/116) PASS.
5. **Side effects:** Java only: on go it also changes the author-quoted U+FFFD that ruling 7 keeps.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-java sheet, PR 48. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 6 — code / B3 / `DA-B3-001`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-B3-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B3 ghost markers. Labelled rows: go 247, rust 225, js-ts 262, java 250, cpp 245, python 284. Examples: `01180a3ddf4dfc23`, `03d9fb46f54cf391`, `03e1fbfd3629a84a`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `83dc5d60eaef6288` (code-cpp), original offset 0: `"<reponame>maidiHaitai/ha"` (fix).
- `3a7b03b626595019` (code-cpp), original offset 0: `"<filename>leetcode/power"` (fix).
- `a800be93ce443cb5` (code-cpp), original offset 0: `"<gh_stars>0\n//\n// Create"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Delete the first line when it starts with `<reponame>`, `<filename>` or `<gh_stars>`.

```python
RULE_ID = "DA-B3-001"
SOURCE_RULE_ID = "DA-B3-001"
CODE = "B3"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-cpp"  # pack whose medicine this came from
AUTHOR = "TharunSivamani"
import re

METADATA_PREFIX = re.compile(
    r"\A<(?:reponame|filename|gh_stars)>[^\r\n]*(?:\r?\n|\Z)",
    re.IGNORECASE,
)

def remove_metadata_prefix(text: str) -> str:
    return METADATA_PREFIX.sub("", text, count=1)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(remove_metadata_prefix(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 247, rust 225, js-ts 245, java 250, cpp 245, python 272.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** A marker in the middle of a file is not touched, and none was seen.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-cpp sheet, PR 9. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 7 — code / E1 / `DA-E1-001`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E1-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `023d4d7c1524277f`, `0bbbdad3593bc36f`, `0e5b75717c831da2`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `f08e1abfa9c2ebdc` (code-go), original offset 0: `"\n/*\n * The Jira Cloud platform REST API\n *\n * Jira Cloud platfor"` (drop).
- `3dc96675632ddcff` (code-go), original offset 0: `"//go:build go1.18\n// +build go1.18\n\n// Copyright (c) Microsoft C"` (drop).
- `3c4db0c3d41b7673` (code-go), original offset 0: `"// Code generated by MockGen. DO NOT EDIT.\n// Source: ./gke/gke."` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Generator marker before or just after the `package` clause, or a Kiota or goformation fingerprint.

```python
RULE_ID = "DA-E1-001"
SOURCE_RULE_ID = "DA-E1-001"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'go'}
ORIGIN = "code-go"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "RaviNaik"
import re

_GEN = re.compile(
    r"(?im)^\s*(?://|/\*|\*)?\s*(?:"
    r"code generated\b|"
    r"auto-?generated|"
    r"由\w*自动生成|"
    r"\(re-\)?generated by\b.*|"
    r"generated by:?\s*(?:swagger|go-swagger|protoc|mockgen|microsoft|openapi)|"
    r"do not (?:edit|change) this file|"
    r"(?:\*{3}\s*warning:\s*)?this file (?:was|is|has been) (?:automatically |auto-?)?(?:generated|autogenerated)\b|"
    r"(?:this file )?(?:was )?automatically generated\b|"
    r"this file was generated by\b)"
)

_GEN_FINGERPRINT = re.compile(
    r"(?m)^\s*i[0-9a-f]{40,}\s+\"github\.com/microsoft/kiota|"
    r"AWSCloudFormationSpecificationVersion returns the AWS Specification Version that this resource was generated from"
)

_PKG = re.compile(r"(?m)^package\s+\w+")

def drop_generated(text: str):
    """Drop the file if a generated-code marker sits in the header (before `package`
    or within the first 40 lines). Markers inside string literals further down do not count."""
    m = _PKG.search(text)
    head = text[: m.end()] if m else text[:2000]
    head = "\n".join(head.split("\n")[:40]) if len(head) > 4000 else head
    # also allow the Go convention of the marker directly after the package clause (go-swagger)
    tail_probe = text[m.end(): m.end() + 1500] if m else ""
    if _GEN.search(head) or _GEN.search(tail_probe) or _GEN_FINGERPRINT.search(text[:3000]):
        return "drop", text
    return "keep", text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(drop_generated(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** go. **Docs it touches:** go 42.
4. **Harm test:** go 0.00% (0/163) PASS.
5. **Side effects:** Generated code with no marker is missed: 1 labelled go row.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, PR 36. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 8 — code / E1 / `DA-E1-004`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E1-004`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `00a6ea4358544d22`, `0316bfaac536f88b`, `1aa2bcd706be1e4b`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `6359488cb66a0aa6` (code-python), original offset 0: `"<filename>sdk/python/pulumi_ovh/iploadbalancing_http_farm_server"` (drop).
- `ba0e6a6503f190e9` (code-python), original offset 0: `"#!/usr/bin/env python\n\"\"\"fuzza autogenerated.\"\"\"\n\nfrom __future_"` (drop).
- `ca3630b84be3762a` (code-python), original offset 0: `"<filename>testcases/fspresetReload.py\n#!/usr/bin/env python2\n# I"` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Generator banner in the first 15 lines, or 20 or more `#[doc = "..."]` lines.

```python
RULE_ID = "DA-E1-004"
SOURCE_RULE_ID = "DA-E1-004"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'python', 'rust'}
ORIGIN = "code-rust, code-python"  # packs it runs on
SOURCE = "code-rust"  # pack whose medicine this came from
AUTHOR = "amukka"
import re

MARKER_LINE = re.compile(r"^(?:<(?:reponame|filename|gh_stars)>[^\n]*)\n?")

GENERATED = re.compile(
    r"(?i)(auto-?generated|automatically generated|code generated|generated by|@generated"
    r"|do not (?:directly )?edit|this file is generated)"
)

def _strip_marker(text: str) -> str:
    return MARKER_LINE.sub("", text, count=1)

def e1_generated(text: str):
    """E1: drop when a generated banner is in the first 15 lines, or 20+ #[doc = "..."] lines."""
    body = _strip_marker(text).split("\n")
    head = "\n".join(body[:15])
    if GENERATED.search(head) or sum('#[doc = "' in l for l in body) >= 20:
        return "drop", ""
    return "keep", text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(e1_generated(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** rust, python. **Docs it touches:** rust 17, python 16.
4. **Harm test:** rust 0.00% (0/78) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** A hand-written file whose header says "generated" is dropped. On python it touches 16 docs, 10 labelled E1 and 1 labelled clean.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-rust sheet, PR 52. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 9 — code / E1 / `DA-E1-008`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E1-008`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `0c10e83429b075c5`, `0f34612ed9c80d78`, `2bae666c99ad51ed`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `0f34612ed9c80d78` (code-js-ts), original offset 0: `"import { purry } from './purry';\nexport function omitProp() {\n  "` (drop).
- `82661aa7e8fdfc1f` (code-js-ts), original offset 0: `"<filename>website/static/source/html/search/files_f.js\nvar searc"` (drop).
- `e8483df9bbdbd7f3` (code-js-ts), original offset 0: `"import*as THREE from\"three\";class MultiPageShaderMaterialParamet"` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** A build folder in the path (`node_modules/`, `dist/`, `build/`, `bundles/`, `vendor/`, `generated/`) or `.min.js`, except `.d.ts`; a `sourceMappingURL` line; compiled-module output; a generator word in the header comment; a minified line; a line over 1,000 characters; three or more `.html#` links; or `var searchData =`.

```python
RULE_ID = "DA-E1-008"
SOURCE_RULE_ID = "DA-E1-008"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'javascript', 'typescript'}
ORIGIN = "code-js-ts"  # packs it runs on
SOURCE = "code-js-ts"  # pack whose medicine this came from
AUTHOR = "Sagar063"
import re

_BUILD_PATH = re.compile(r"(^|/)(node_modules|dist|build|bundles?|vendor|generated)/|\.min\.js$")

_GENERATED = re.compile(r"auto-?generated|do not edit|generated by", re.I)

_COMPILED = re.compile(r"Object\.defineProperty\(exports,\s*[\"']__esModule[\"']|\bjsx_runtime_\d+\.jsx\(")

_TAGS = re.compile(r"<(filename|gh_stars|reponame)>")

def _header_comment(text):
    """The comment lines at the very top of the file, after an optional StarCoder line."""
    lines, out = text.split("\n"), []
    if lines and _TAGS.match(lines[0]):
        lines = lines[1:]
    for line in lines:
        s = line.strip()
        if s == "" or s.startswith(("//", "/*", "*", "*/")):
            out.append(line)
        else:
            break
    return "\n".join(out)

def _minified(text):
    return any(len(line) > 300 and line.count(" ") / len(line) < 0.05 for line in text.split("\n"))

def medicine_e1(doc):
    """Drop build output and generated files. doc has 'text' and 'url'."""
    text, path = doc["text"], doc.get("url") or ""
    built = bool(_BUILD_PATH.search(path)) and not path.endswith(".d.ts")
    generated = bool(
        re.search(r"^\s*//# sourceMappingURL=", text, re.M)
        or _COMPILED.search(text)
        or _GENERATED.search(_header_comment(text))
        or _minified(text)
        or max(len(line) for line in text.split("\n")) > 1000
        or text.count(".html#") >= 3
        or re.search(r"var searchData\s*=", text)
    )
    return ("drop", "") if (built or generated) else text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e1(doc), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** js-ts. **Docs it touches:** js-ts 22.
4. **Harm test:** js-ts 0.00% (0/204) PASS.
5. **Side effects:** A hand-written file in such a folder, or with one line over 1,000 characters, is dropped. **3 js-ts docs go on the path alone** (`node_modules`, `build`, `generated`). The 30 Oct ruling says a vendored copy is not a disease by itself, so the reviewer should decide whether `node_modules` and `vendor` stay in the path check. Touches 6 js-ts docs that a reader labelled clean.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-js-ts sheet, PR 115. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 10 — code / E1 / `DA-E1-006`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E1-006`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `138cac43be0730ea`, `2111dfa57dfd75e8`, `3cba9087383097dd`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `c6016e9ce2c607c5` (code-java), original offset 0: `"<gh_stars>10-100\n/*-\n * Copyright (C) 2015 <NAME>\n *\n * This pro"` (drop).
- `73e175e90e6e37da` (code-java), original offset 0: `"// Copyright (c) Microsoft Corporation. All rights reserved.\n// "` (drop).
- `896c9a4f9693205f` (code-java), original offset 0: `"/*\n * XML Type:  CT_TblGridChange\n * Namespace: http://schemas.o"` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Decompiler or generator marker in the text (Jad, Procyon, "AUTO-GENERATED FILE", "This class was generated by", swagger).

```python
RULE_ID = "DA-E1-006"
SOURCE_RULE_ID = "DA-E1-006"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'java'}
ORIGIN = "code-java"  # packs it runs on
SOURCE = "code-java"  # pack whose medicine this came from
AUTHOR = "riyaagrahari"
import re

GEN = re.compile(r'Decompiled by (Jad|Procyon)|Code generated by [^\n]{0,60}Generator|AUTO-GENERATED FILE'
                 r'|generated by a tool and any changes will be overwritten|Automatically generated - do not modify'
                 r'|This class was (automatically )?generated by|auto generated by the swagger'
                 r'|This is a generated file\. Not intended for manual editing')

def drop_e1(text): return bool(GEN.search(text))


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(drop_e1(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** java. **Docs it touches:** java 10.
4. **Harm test:** java 0.00% (0/116) PASS.
5. **Side effects:** Stub files and jadx output with no marker are missed: 4 labelled java rows. Touches 1 doc labelled clean.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-java sheet, PR 123. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 11 — code / E1 / `DA-E1-005`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E1-005`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `4b53d240dabec20a`, `737965d79cc94955`, `83b3083721ee5df9`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `a3256b38a3e5a8d1` (code-cpp), original offset 0: `"#include \"CAM_RowNand.h\"\r\n#include \"RowDecoder.h\"\r\n#include \"for"` (drop).
- `deccbc12f9921ae8` (code-cpp), original offset 0: `"<filename>doc/quickbook/oglplus/quickref/enums/tess_gen_primitiv"` (drop).
- `b5da9ac1658db525` (code-cpp), original offset 0: `"<reponame>StardustXR/libstardustxr<gh_stars>1-10\n// automaticall"` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Generator note in a comment line of the first 1500 characters, or a Kiota or goformation fingerprint.

```python
RULE_ID = "DA-E1-005"
SOURCE_RULE_ID = "DA-E1-005"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'cpp'}
ORIGIN = "code-cpp"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

GENERATED = re.compile(r"^[ \t]*(?://|/\*|\*)[^\n]*?(?:Code generated|generated by|auto-?generated|"
                       r"automatically generated|AutoRest Code Generator|自动生成)", re.I | re.M)

FINGERPRINT = re.compile(r"(?m)^\s*i[0-9a-f]{40,}\s+\"github\.com/microsoft/kiota|"
                         r"Specification Version that this resource was generated from")

def medicine_e1(doc):
    t = doc["text"]
    return ("drop" if GENERATED.search(t[:1500]) or FINGERPRINT.search(t[:3000]) else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e1(doc), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** cpp. **Docs it touches:** cpp 8.
4. **Harm test:** cpp 0.00% (0/120) PASS.
5. **Side effects:** A comment such as "the ID generated by the server" near the top would match.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 12 — code / E1 / `DA-E1-007`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E1-007`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `3c67c435782c8a77`, `9c1d218d257a6176`, `b5da9ac1658db525`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `deccbc12f9921ae8` (code-cpp), original offset 0: `"<filename>doc/quickbook/oglplus/quickref/enums/tess_gen_primitiv"` (drop).
- `b5da9ac1658db525` (code-cpp), original offset 0: `"<reponame>StardustXR/libstardustxr<gh_stars>1-10\n// automaticall"` (drop).
- `c990295fa1578b72` (code-cpp), original offset 0: `"<gh_stars>10-100\n//\n// StatementImpl.cpp\n//\n// $Id: //poco/1.4/D"` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Generator marker in a comment line, or any line longer than 1000 characters.

```python
RULE_ID = "DA-E1-007"
SOURCE_RULE_ID = "DA-E1-007"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'cpp'}
ORIGIN = "code-cpp"  # packs it runs on
SOURCE = "code-java"  # pack whose medicine this came from
AUTHOR = "vaibh27"
import re

GENERATED = re.compile(r"(?im)^[ \t]*(?://|/?\*)[^\n]*(?:auto-generated file|do not (?:edit|modify)\b|decompiled (?:by|with)|"
                       r"code generated by|(?:file|class|code) (?:was|is|has been) (?:auto(?:matically)?[- ]?)?generated|"
                       r"generated by a tool)")

def m7_drop_generated(t: str):
    if GENERATED.search(t) or any(len(line) > 1000 for line in t.split("\n")):
        return None
    return t


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m7_drop_generated(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** cpp. **Docs it touches:** cpp 5.
4. **Harm test:** cpp 0.00% (0/120) PASS.
5. **Side effects:** A hand-written file with one very long line, such as a data table, is dropped.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-java sheet, PR 48. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 13 — code / E2 / `DA-E2-001`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E2-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E2 data blobs. Labelled rows: go 7, rust 2, js-ts 1, java 1, cpp 1, python 1. Examples: `023d4d7c1524277f`, `637118880fa53f2f`, `8c1931d1524ec642`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `8b23faa736d88ac9` (code-cpp), original offset 0: `"/***************************************************************"` (drop).
- `637118880fa53f2f` (code-go), original offset 0: `"<reponame>VJftw/docker-registry-proxy\n// Code generated by proto"` (drop).
- `91bf17319ac11223` (code-go), original offset 0: `"<gh_stars>0\n// Code generated by protoc-gen-go. DO NOT EDIT.\n// "` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Byte-array literals cover 10% or more of the file, or base64 runs 40% or more.

```python
RULE_ID = "DA-E2-001"
SOURCE_RULE_ID = "DA-E2-001"
CODE = "E2"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "RaviNaik"
import re

_BYTES = re.compile(r"(?:0x[0-9a-fA-F]{2},\s*){24,}(?:0x[0-9a-fA-F]{2},?)?")

_B64 = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")

def drop_blob(text: str, share: float = 0.10, b64_share: float = 0.4):
    """Drop the file when byte-array literals cover at least `share` of it, or when base64-looking
    runs cover at least `b64_share`. Removing the array would break the Go code, so there is no fix."""
    if not text:
        return "keep", text
    n = len(text)
    if sum(len(m.group()) for m in _BYTES.finditer(text)) / n >= share:
        return "drop", text
    if sum(len(m.group()) for m in _B64.finditer(text)) / n >= b64_share:
        return "drop", text
    return "keep", text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(drop_blob(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 7, rust 0, js-ts 0, java 0, cpp 1, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Smaller blobs stay: the labelled E2 rows of rust (2), js-ts (1), java (1) and python (1) are not caught.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, PR 36. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 14 — code / C3 / `DA-C3-002`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-C3-002`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C3 truncated or broken document. Labelled rows: go 1, rust 0, js-ts 0, java 0, cpp 0, python 0. Examples: `a27e1273db746e7d`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `a27e1273db746e7d` (code-go), original offset 0: `"package raft\n\nimport (\n\t\"encoding/json\"\n\t\"errors\"\n\t\"fmt\"\n\t\"math/"` (drop).

**Example gap:** 1/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Go lexical check fails: unclosed string, rune or block comment, or unbalanced brackets.

```python
RULE_ID = "DA-C3-002"
SOURCE_RULE_ID = "DA-C3-002"
CODE = "C3"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'go'}
ORIGIN = "code-go"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

def _go_lexes(t):
    i, n, depth = 0, len(t), 0
    while i < n:
        c = t[i]
        if t.startswith("//", i):
            j = t.find("\n", i)
            i = n if j < 0 else j
        elif t.startswith("/*", i):
            j = t.find("*/", i + 2)
            if j < 0:
                return False
            i = j + 2
        elif c in "\"'":
            i += 1
            while i < n and t[i] != c:
                if t[i] == "\n":
                    return False
                i += 2 if t[i] == "\\" else 1
            if i >= n:
                return False
            i += 1
        elif c == "`":
            j = t.find("`", i + 1)
            if j < 0:
                return False
            i = j + 1
        else:
            depth += (c in "{([") - (c in "})]")
            if depth < 0:
                return False
            i += 1
    return depth == 0

def medicine_c3(doc):
    return ("keep" if _go_lexes(doc["text"]) else "drop", doc["text"])


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_c3(doc), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** go. **Docs it touches:** go 1.
4. **Harm test:** go 0.00% (0/163) PASS.
5. **Side effects:** Go only: it reads Rust lifetimes (`'a`) as unclosed runes. It is not a full parser.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 15 — code / C4 / `DA-C4-002`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-C4-002`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C4 two documents joined. Labelled rows: go 0, rust 0, js-ts 0, java 1, cpp 1, python 0. Examples: `1227540794647c4d`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `1227540794647c4d` (code-java), original offset 0: `"<reponame>rakhi2001/ecom7\n______________________________________"` (drop).

**Example gap:** 1/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** A separator line (20 or more `_` or `=`) or a "sample 12 ms submission" caption outside a comment.

```python
RULE_ID = "DA-C4-002"
SOURCE_RULE_ID = "DA-C4-002"
CODE = "C4"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'java'}
ORIGIN = "code-java"  # packs it runs on
SOURCE = "code-java"  # pack whose medicine this came from
AUTHOR = "vaibh27"
import re

JOINED = re.compile(r"(?mi)^[ \t]*(?:_{20,}|={20,}|sample \d+ (?:ms|kb) submission)[ \t]*$")

def m9_drop_joined(t: str):
    return None if JOINED.search(t) else t


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m9_drop_joined(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** java. **Docs it touches:** java 1.
4. **Harm test:** java 0.00% (0/116) PASS.
5. **Side effects:** Java only: in python such a line can be a docstring heading.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-java sheet, PR 48. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 16 — code / E4 / `DA-E4-005`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E4-005`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E4 repeated licence headers. Labelled rows: go 76, rust 22, js-ts 9, java 103, cpp 176, python 70. Examples: `01180a3ddf4dfc23`, `0a0303df2fa01ea8`, `0c16883f44febd4f`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `2bdf36ae14fd90fa` (code-go), original offset 73: `"ge cmd\n\n// Copyright 2018 Blink "` (fix).
- `3dc96675632ddcff` (code-go), original offset 28: `"go1.18\n\n// Copyright (c) Microso"` (fix).
- `83381a2f882bdce3` (code-go), original offset 0: `"// MIT License\n//\n// (C) "` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Drop on a restrictive licence phrase in the first 60 lines. Else delete a licence comment block of 4 or more lines in the Go header, a boxed header, or a block at the end. Build tags and package docs stay.

```python
RULE_ID = "DA-E4-005"
SOURCE_RULE_ID = "DA-E4-005"
CODE = "E4"
ACTION = "fix+drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'go'}
ORIGIN = "code-go"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

LICENCE = re.compile(r"Licensed under|Licensed to the Apache|Permission is hereby granted|Redistribution and use|"
                     r"Use of this source code is governed by|This source code is licensed under|"
                     r"released under the \w+ licen[cs]e|General Public License|Mozilla Public License", re.I)

RESTRICTIVE = re.compile(r"(?i)free for personal use|commercial use requires|non-?commercial use only|"
                         r"commons clause|not for commercial use|for evaluation purposes only")

BLOCK = re.compile(r"(?:[ \t]*/\*[^\n]*\*/[ \t]*\n){2,}|/\*.*?\*/[ \t]*\n?|(?://[^\n]*\n)+", re.S)

TAIL = re.compile(r"\n((?:[ \t]*/\*[^\n]*\*/[ \t]*\n?){2,}|/\*(?:(?!\*/).)*\*/|(?://[^\n]*(?:\n|\Z))+)\s*\Z", re.S)

def _is_licence(block):
    return bool(LICENCE.search(block)) and block.count("\n") >= 4

def medicine_e4(doc):
    t = doc["text"]
    if RESTRICTIVE.search("\n".join(t.split("\n")[:60])):
        return ("drop", t)  # a restrictive licence: stripping the header would not make the code free to use
    body = re.search(r"^(?:import|func|type|var|const)\b", t, re.M)
    end = body.start() if body else len(t)
    head = BLOCK.sub(lambda m: "" if _is_licence(m.group()) else m.group(), t[:end])
    if head != t[:end]:
        head = head.lstrip("\n")
    new = head + t[end:]
    tail = TAIL.search(new)
    if body and tail and tail.start() > len(head) and _is_licence(tail.group(1)):
        new = new[:tail.start()] + "\n"
    return ("keep", t) if new == t else ("fix", new)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e4(doc), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix+drop. **Runs on:** go. **Docs it touches:** go 56.
4. **Harm test:** go 0.00% (0/163) PASS.
5. **Side effects:** A licence block touching the package doc comment takes the doc with it. Removes the notice the licence asks to keep: record the licence in metadata first.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 17 — code / E4 / `DA-E4-010`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E4-010`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E4 repeated licence headers. Labelled rows: go 76, rust 22, js-ts 9, java 103, cpp 176, python 70. Examples: `01180a3ddf4dfc23`, `0a0303df2fa01ea8`, `0c16883f44febd4f`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `9f6e4e65e41f69c4` (code-cpp), original offset 0: `"/* MIT License\n* \n* Copyri"` (fix).
- `0797d20110e8ab9b` (code-cpp), original offset 61: `"rs>1-10\n// Copyright (c) 2010 Th"` (fix).
- `4ac6624748e7453d` (code-cpp), original offset 38: `"der.cxx\n/**\n * PANDA 3D SOFTWARE"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Delete a leading comment block of 5 or more lines that is at least 40% licence text. `#` lines count as comments on python only. Shebang, encoding and Go build lines stay. Repeats until nothing changes, for stacked headers.

```python
RULE_ID = "DA-E4-010"
SOURCE_RULE_ID = "DA-E4-010"
CODE = "E4"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'python', 'rust'}
ORIGIN = "code-go, code-rust, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-rust"  # pack whose medicine this came from
AUTHOR = "amukka"
import re

MARKER_LINE = re.compile(r"^(?:<(?:reponame|filename|gh_stars)>[^\n]*)\n?")

LICENCE = re.compile(
    r"(?i)(licensed under|permission is hereby granted|redistribution and use|public domain"
    r"|this source code form|all rights reserved|without warranties|general public license"
    r"|affero|mit license|apache license|free software|copyright|warranty|spdx|redistribute"
    r"|the software|the terms|permitted|liability|licen[cs]e|apache|distributed|rights|dedicated"
    r"|modified, or|you may not use)"
)

COMMENT_LINE = re.compile(r"^\s*(//(?![!/])|/\*(?![!*])|\*|\*/|#)")

def _strip_marker(text: str) -> str:
    return MARKER_LINE.sub("", text, count=1)

def _licence_density(block: str) -> bool:
    """3+ licence lines and at least 40% of the non-blank lines are licence text."""
    lines = [l for l in block.split("\n") if l.strip(" /*#\t")]
    hits = sum(bool(LICENCE.search(l)) for l in lines)
    return hits >= 3 and hits * 10 >= len(lines) * 4

def e4_licence_header(text: str, comment_line=COMMENT_LINE):
    """E4: remove a leading comment block of 5+ lines that holds licence text.

    The block is either one /* ... */ comment or a run of // lines (single blank lines allowed
    inside). //! and /// doc comments are never part of it.
    """
    body = _strip_marker(text)
    prefix = text[: len(text) - len(body)]
    if body.lstrip().startswith("/*"):
        end = body.find("*/")
        block, rest = (body[: end + 2], body[end + 2 :]) if end != -1 else ("", body)
        n = block.count("\n") + 1
    else:
        lines = body.split("\n")
        n = 0
        i = 0
        while i < len(lines):
            if comment_line.match(lines[i]):
                n = i + 1
                i += 1
            elif not lines[i].strip() and i + 1 < len(lines) and comment_line.match(lines[i + 1]):
                i += 1
            else:
                break
        block, rest = "\n".join(lines[:n]), "\n".join(lines[n:])
    if n >= 5 and _licence_density(block):
        return "fix", prefix + rest.lstrip("\n")
    return "keep", text

NO_HASH = re.compile(r"^\s*(//(?![!/])|/\*(?![!*])|\*|\*/)")

KEEP_LINE = re.compile(r"^(#!|#.*coding[:=]|\s*//\s*(go:|\+build))")

def medicine_e4_fixed(doc):
    text = doc["text"]
    comment = COMMENT_LINE if doc.get("lang_label") == "python" else NO_HASH
    new = text
    while True:  # two stacked licence blocks: apply(apply(doc)) == apply(doc)
        action, out = e4_licence_header(new, comment)
        if action != "fix" or out == new:
            break
        new = out
    if new == text:
        return ("keep", text)
    now = set(new.split("\n"))
    kept = [l for l in text.split("\n")[:60] if KEEP_LINE.match(l) and l not in now]
    return ("fix", "\n".join(kept + [new]) if kept else new)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e4_fixed(doc), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** go, rust, java, cpp, python. **Docs it touches:** go 51, rust 22, java 81, cpp 95, python 60.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Short 2 to 4 line notes stay. Removes the notice the licence asks to keep: record the licence in metadata first. **Changed from `DA-E4-004`:** see the decisions file.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-rust sheet, PR 52. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 18 — code / E4 / `DA-E4-009`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E4-009`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E4 repeated licence headers. Labelled rows: go 76, rust 22, js-ts 9, java 103, cpp 176, python 70. Examples: `0796334a27ed6607`, `0dd7bdea9580fa25`, `1a1a1d7ab0bf9188`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `5655154f71365c63` (code-java), original offset 0: `"/*\n *  Licensed to the A"` (fix).
- `86534a30f79557fb` (code-java), original offset 0: `"/*\n * Licensed under the"` (fix).
- `c70422358a640e42` (code-java), original offset 4: `"stars>0\n/*\n *  Licensed to the A"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Drop on a restrictive licence phrase. Else delete the first licence comment block of 7 or more lines in the first 60 lines, or one at the end.

```python
RULE_ID = "DA-E4-009"
SOURCE_RULE_ID = "DA-E4-009"
CODE = "E4"
ACTION = "fix+drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'java'}
ORIGIN = "code-java"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "RaviNaik"
import re

_LIC_WORDS = re.compile(
    r"(?i)licensed under|permission is hereby granted|without warranty|"
    r"you may not use this file|redistribut|general public license|all rights reserved|"
    r"warranties of|distributed under the licen"
)

_RESTRICTIVE = re.compile(
    r"(?i)free for personal use|commercial use requires|non-?commercial use only|commons clause|"
    r"not for commercial use|for evaluation purposes only"
)

def _comment_runs(lines, limit=60, tail=False):
    """Yield (start, end) of contiguous // runs, /* */ blocks and runs of one-line /* ... */ comments."""
    n = len(lines)
    rng = range(max(0, n - 40), n) if tail else range(0, min(n, limit))
    lo, hi = rng.start, rng.stop
    i = lo
    while i < hi:
        s = lines[i].strip()
        if s.startswith("/*") and s.endswith("*/") and len(s) > 4:
            j = i
            while j < n and lines[j].strip().startswith("/*") and lines[j].strip().endswith("*/"):
                j += 1
            yield i, j
            i = j
        elif s.startswith("/*"):
            j = i
            while j < n and "*/" not in lines[j]:
                j += 1
            yield i, j + 1
            i = j + 1
        elif s.startswith("//") and not s.startswith(("//go:", "// +build", "//+build")):
            j = i
            while j < n and lines[j].strip().startswith("//"):
                j += 1
            yield i, j
            i = j
        else:
            i += 1

def strip_licence_header(text: str, min_lines: int = 7):
    """Drop files whose header carries a restrictive licence. Otherwise remove the first
    comment block in the first 60 lines (or the last 40 lines) that has >= min_lines lines and
    licence grant text. Run this AFTER fix_b3 so the file starts at the real first line."""
    lines = text.split("\n")
    head = "\n".join(lines[:60])
    if _RESTRICTIVE.search(head):
        return "drop", text
    for tail in (False, True):
        for a, b in _comment_runs(lines, tail=tail):
            block = lines[a:b]
            if len(block) >= min_lines and sum(1 for x in block if _LIC_WORDS.search(x)) >= 2:
                kept = lines[:a] + lines[b:]
                return "fix", "\n".join(kept).strip("\n") + ("\n" if text.endswith("\n") else "")
    return "keep", text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(strip_licence_header(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix+drop. **Runs on:** java. **Docs it touches:** java 82.
4. **Harm test:** java 0.00% (0/116) PASS.
5. **Side effects:** Short headers stay.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, PR 36. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 19 — code / E4 / `DA-E4-007`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E4-007`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E4 repeated licence headers. Labelled rows: go 76, rust 22, js-ts 9, java 103, cpp 176, python 70. Examples: `1e918efcbd1c6f4b`, `4aa682fef3c7ba0d`, `67c9226601f26da9`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `ac23df9698407bac` (code-js-ts), original offset 0: `"/**\n *\n *    Copyright ("` (fix).
- `1e918efcbd1c6f4b` (code-js-ts), original offset 24: `"sorolla\n/**\n * Copyright 2015-20"` (fix).
- `877058bd3cb250e3` (code-js-ts), original offset 27: `"torbook\n/**\n * Package that cont"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Delete the first comment at the top when it is 10 or more lines and names Apache, MIT, GPL or "Permission is hereby granted".

```python
RULE_ID = "DA-E4-007"
SOURCE_RULE_ID = "DA-E4-007"
CODE = "E4"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'javascript', 'typescript'}
ORIGIN = "code-js-ts"  # packs it runs on
SOURCE = "code-js-ts"  # pack whose medicine this came from
AUTHOR = "Sagar063"
import re

_LICENCE = re.compile(r"Licensed under the Apache License|Permission is hereby granted|"
                      r"GNU (Lesser |Affero )?General Public License|MIT License", re.I)

_TOP_COMMENT = re.compile(r"\A((?:<(?:reponame|filename|gh_stars)>[^<\n]*)+\n)?\s*"
                          r"(/\*.*?\*/[ \t]*\n?|(?:[ \t]*//[^\n]*\n)+)", re.S)

def medicine_e4(text):
    """Remove a licence comment of 10 or more lines at the top of the file."""
    m = _TOP_COMMENT.match(text)
    if m:
        block = m.group(2).rstrip("\n")
        if _LICENCE.search(block) and block.count("\n") + 1 >= 10:
            return (m.group(1) or "") + text[m.end():].lstrip("\n")
    return text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e4(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** js-ts. **Docs it touches:** js-ts 6.
4. **Harm test:** js-ts 0.49% (1/204) PASS.
5. **Side effects:** Short notices stay. **Changes 1 js-ts gold doc** (`67c9226601f26da9`, a 21-line licence header the gold readers kept). That is within the limit of 2 and it is what the rule is for; the readers disagree on whether a real header is E4. Removes the notice the licence asks to keep: record the licence in metadata first.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-js-ts sheet, PR 115. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 20 — code / C1 / `DA-C1-004`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-C1-004`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C1 boilerplate. Labelled rows: go 1, rust 0, js-ts 0, java 80, cpp 2, python 0. Examples: `45ac5026eac81b39`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `45ac5026eac81b39` (code-go), original offset 617: `"/v1\"\n)\n\n// EDIT THIS FILE!  THIS"` (fix).
- `fd10104d4b8b5721` (code-go), original offset 653: `"/v1\"\n)\n\n// NOTE: json tags are r"` (fix).

**Example gap:** 2/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Delete kubebuilder and operator-sdk scaffold notes ("EDIT THIS FILE!", "NOTE: json tags are required").

```python
RULE_ID = "DA-C1-004"
SOURCE_RULE_ID = "DA-C1-004"
CODE = "C1"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'go'}
ORIGIN = "code-go"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

SCAFFOLD = re.compile(r'^[ \t]*//[ \t]*(?:EDIT THIS FILE!.*|NOTE: json tags are required\..*|'
                      r'Important: Run "make" to regenerate code after modifying this file.*|'
                      r'INSERT ADDITIONAL (?:SPEC|STATUS) FIELDS?.*)\n', re.M)

def medicine_c1(doc):
    t = SCAFFOLD.sub("", doc["text"])
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_c1(doc), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** go. **Docs it touches:** go 2.
4. **Harm test:** go 0.00% (0/163) PASS.
5. **Side effects:** Other generators' scaffold notes are not covered.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 21 — code / C1 / `DA-C1-005`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-C1-005`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C1 boilerplate. Labelled rows: go 1, rust 0, js-ts 0, java 80, cpp 2, python 0. Examples: `077f2bc49b1bb6db`, `0b893004aea9459b`, `1397a887d14c0fae`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `e0ebe203093970dc` (code-java), original offset 100: `"Map;\r\n\r\n/**\r\n * Created by sherx"` (fix).
- `c9eb2d8e4f9cacde` (code-java), original offset 429: `"nUtil;\n\n/**\n * Created by hzliux"` (fix).
- `50e06974390e57ea` (code-java), original offset 0: `"/*\n * To change this lic"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Delete IDE template lines and the template part of a header comment ("To change this template", "Created by ... on").

```python
RULE_ID = "DA-C1-005"
SOURCE_RULE_ID = "DA-C1-005"
CODE = "C1"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'java'}
ORIGIN = "code-java"  # packs it runs on
SOURCE = "code-java"  # pack whose medicine this came from
AUTHOR = "vaibh27"
import re

LIC_WORDS = re.compile(r"licen[cs]e|permission is hereby granted|redistribution and use", re.I)

NOT_LICENCE = re.compile(r"to change this licen[cs]e header|choose licen[cs]e headers", re.I)

IDE_LINE = re.compile(r"(?im)^[ \t]*//[ \t]*TODO Auto-generated (?:method|constructor|catch block|stub)[^\n]*\n")

BLOCK = re.compile(r"[ \t]*/\*.*?\*/[ \t]*\n?", re.S)

IDE_MARK = re.compile(r"(?im)TODO Auto-generated|To change this (?:licen[cs]e header|template)|choose Tools \| Templates|"
                      r"Created (?:by|with) IntelliJ IDEA|Created by [^\n]{1,80}? on \d|File \| Settings \| File Templates|"
                      r"^\s*\*?\s*User\s*:.*\n\s*\*?\s*Date\s*:|^\s*\*?\s*@(?:project|package)\s*[:：]|\$\{[\w.]{1,40}\}|"
                      r"^\s*\*?\s*<p>\s*Title\s*[:：]")

EMPTY_DESC = re.compile(r"(?im)^\s*\*?\s*@?desc(?:ription)?\s*[:：]*\s*(?:TODO)?\s*$")

AUTHOR_DATE = re.compile(r"(?im)^\s*\*?\s*@?(?:author|user)\b(?:.*\n)*?\s*\*?\s*@?(?:date|create|created)\s*[:：]")

TEMPLATE_LINE = re.compile(r"(?i)^\s*(?:/\*+|\*+)?\s*(?:<p>\s*)?(?:@?(?:author|user|date|time|class|project|package|create|created|"
                           r"version|since|title)\b\s*[:：]?.*|desc(?:ription)?\s*[:：]?\s*(?:TODO)?\s*(?:</p>)?|Created (?:by|with) .*|"
                           r"To change this .*|choose .*Templates.*|and open the template.*|TODO Auto-generated.*|"
                           r"(?:copyright|e-?mail|blog|company)\b.*)\s*$")

AUTHOR_ONLY = re.compile(r"/\*\*(?:\s*\*)*\s*@author\b[^\n]*(?:\s*\*)*\s*/")

def _clean_ide_block(block: str) -> str:
    if LIC_WORDS.search(block) and not NOT_LICENCE.search(block):
        return block  # a licence goes with M4
    if AUTHOR_ONLY.fullmatch(block.strip()):  # empty Javadoc with one @author line (labelled B4 only for <NAME>)
        return ""
    if not (IDE_MARK.search(block) or (EMPTY_DESC.search(block) and AUTHOR_DATE.search(block))):
        return block
    body = block.rstrip("\n")
    lines, end = body.split("\n"), block[len(body):]  # end: the newline after */
    inner = [l for l in lines[1:-1] if not TEMPLATE_LINE.match(l) and l.strip(" \t*")]
    if len(lines) < 3 or not inner:
        return ""  # nothing but the template
    return "\n".join([lines[0]] + [l for l in lines[1:-1] if not TEMPLATE_LINE.match(l)] + [lines[-1]]) + end

def m6_strip_ide_templates(t: str) -> str:
    t = IDE_LINE.sub("", t)
    return BLOCK.sub(lambda m: _clean_ide_block(m.group()), t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m6_strip_ide_templates(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** java. **Docs it touches:** java 79.
4. **Harm test:** java 0.00% (0/116) PASS.
5. **Side effects:** Only one java reader labels these; the other two mark 23 of the touched docs clean. It only touches comments.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-java sheet, PR 48. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 22 — code / B4 / `DA-B4-009`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-B4-009`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B4 template junk / PII placeholders. Labelled rows: go 45, rust 18, js-ts 25, java 83, cpp 122, python 27. Examples: `0f4121b3b47fc3e0`, `1398b525d923d644`, `14a63d176ed55369`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `9f6e4e65e41f69c4` (code-cpp), original offset 31: `"c) 2018 <NAME>\n* \n* Permission i"` (fix).
- `ab726af7ee73aa3b` (code-cpp), original offset 17: `"C) 2015 <NAME>\n * All rights res"` (fix).
- `a800be93ce443cb5` (code-cpp), original offset 21: `"ated by <NAME> on 2021/5/13.\n//\n"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** `<NAME>` -> `AUTHOR`, `<EMAIL>` -> `user@example.com`, `<KEY>` -> `EXAMPLE_KEY`, `<PASSWORD>` -> `EXAMPLE_PASSWORD`.

```python
RULE_ID = "DA-B4-009"
SOURCE_RULE_ID = "DA-B4-009"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

NEUTRAL = {"<NAME>": "AUTHOR", "<EMAIL>": "user@example.com", "<KEY>": "EXAMPLE_KEY", "<PASSWORD>": "EXAMPLE_PASSWORD"}

PLACEHOLDER = re.compile("|".join(map(re.escape, NEUTRAL)))

def medicine_b4(doc):
    t = PLACEHOLDER.sub(lambda m: NEUTRAL[m.group()], doc["text"])
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_b4(doc), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 43, rust 18, js-ts 30, java 82, cpp 121, python 83.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Cannot repair code that the redaction cut (C3 drops that file). A neutral word is still not the true author.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 23 — code / E3 / `DA-E3-003`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E3-003`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E3 secrets. Labelled rows: go 1, rust 1, js-ts 9, java 1, cpp 0, python 0. Examples: `98e4c493f32c8bfa`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).


**Example gap:** 0/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Known key formats (AWS, GitHub, `sk-`, Slack, PEM) and base32 seeds assigned to secret, seed or otp names become `EXAMPLE_SECRET`.

```python
RULE_ID = "DA-E3-003"
SOURCE_RULE_ID = "DA-E3-003"
CODE = "E3"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

KEYS = [re.compile(p) for p in (r"AKIA[0-9A-Z]{16}", r"gh[pousr]_[A-Za-z0-9]{30,}", r"\bsk-[A-Za-z0-9_-]{20,}",
        r"xox[baprs]-[A-Za-z0-9-]{10,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")]

SEED = re.compile(r'(?i)((?:secret|seed|totp|otp)\w*\s*:?=\s*")[A-Z2-7]{16,}(")')

def medicine_e3(doc):
    t = doc["text"]
    for rx in KEYS:
        t = rx.sub("EXAMPLE_SECRET", t)
    t = SEED.sub(r"\1EXAMPLE_SECRET\2", t)
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e3(doc), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 1, rust 0, js-ts 0, java 0, cpp 0, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Secrets with no known format and no telling name are missed. A public test vector is replaced too.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 24 — code / E3 / `DA-E3-004`

**Consolidation:** Source [medicine_code.md](medicine_code.md); original identity `DA-E3-004`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** E3 secrets. Labelled rows: go 1, rust 1, js-ts 9, java 1, cpp 0, python 0. Examples: `85fa4d03a2a63982`, `0d3bff117f465b99`, `8302c459b07901ca`.
<!-- CARD EVIDENCE -->
**Current gold harm:** code-cpp: 0 changed / 0 dropped of 122 (PASS); code-go: 0 changed / 0 dropped of 163 (PASS); code-java: 0 changed / 0 dropped of 116 (PASS); code-js-ts: 0 changed / 0 dropped of 204 (PASS); code-python: 0 changed / 0 dropped of 142 (PASS); code-rust: 0 changed / 0 dropped of 234 (PASS).


**Example gap:** 0/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Replace a secret with `EXAMPLE_SECRET` and keep the file. Two kinds: known formats (Google, AWS, GitHub, Stripe, SendGrid, Slack, JWT, PEM), and a quoted value of 16 or more characters assigned to a secret-like name or passed to `new Pusher(`. The value must look random: mixed letters and digits, at least 15% digits, no dots, no dummy words such as `test` or `example`.

```python
RULE_ID = "DA-E3-004"
SOURCE_RULE_ID = "DA-E3-004"
CODE = "E3"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "new rule, written for this sheet"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import math
import re

PLACEHOLDER = "EXAMPLE_SECRET"

KNOWN = [re.compile(p) for p in (
    r"\bAIza[0-9A-Za-z_\-]{35}\b",                                   # Google API key
    r"\bAKIA[0-9A-Z]{16}\b",                                         # AWS access key
    r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",                               # GitHub token
    r"\bgithub_pat_[A-Za-z0-9_]{40,}\b",                             # GitHub fine-grained token
    r"\bsk-[A-Za-z0-9_\-]{20,}\b",                                   # sk- API key
    r"\b[rs]k_live_[0-9A-Za-z]{16,}\b",                              # Stripe live key
    r"\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}\b",             # SendGrid key
    r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b",                            # Slack token
    r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b",  # JWT
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
)]

ASSIGNED = re.compile(
    r"""(?ix)
    (?P<head>
      \b[\w\-]*(?:secret|token|api[_\-]?key|app[_\-]?key|auth[_\-]?key|access[_\-]?key|client[_\-]?key|private[_\-]?key|passw(?:or)?d|pwd|\bkey)[\w\-]*
      ["']?
      (?:\s*:\s*&?(?:'\w+\s+)?[\w<>\[\]]{1,20})?   # Rust and TypeScript types: SECRET: &'static str = "..."
      \s*(?::=|=>|=|:)\s*
      (?P<quote>["'`])
    )
    (?P<value>[^"'`\s\\]{16,200})
    (?P=quote)
    """)

SDK_KEY = re.compile(r"""(?P<head>\bnew\s+Pusher\(\s*(?P<quote>["'`]))[0-9a-fA-F]{16,}(?P=quote)""")

DUMMY = re.compile(r"(?i)example|sample|dummy|test|fake|mock|placeholder|changeme|change_me|your|xxxx|0000|1234|abcd|secret|password|token|<|>|\$\{|\{\{|%s")

def _entropy(v):
    n = len(v)
    return -sum(c / n * math.log2(c / n) for c in (v.count(ch) for ch in set(v)))

def _looks_random(v):
    """A real key is a run of mixed letters and digits, not a word, an identifier, a path, a version or a dummy."""
    if DUMMY.search(v) or "." in v or v.count("/") > 2:
        return False
    if not (re.search(r"[0-9]", v) and re.search(r"[A-Za-z]", v)):  # enum names and plain words have no digits
        return False
    if sum(ch.isdigit() for ch in v) < 0.15 * len(v):                # user_profile_settings_v2
        return False
    return _entropy(v) >= 3.0

def medicine_e3(text):
    new = text
    for rx in KNOWN:
        new = rx.sub(PLACEHOLDER, new)
    new = SDK_KEY.sub(lambda m: m.group("head") + PLACEHOLDER + m.group("quote"), new)
    new = ASSIGNED.sub(lambda m: m.group("head") + PLACEHOLDER + m.group("quote") if _looks_random(m.group("value")) else m.group(0), new)
    return new


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e3(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'code-cpp', 'code-java', 'code-rust', 'code-go', 'code-python', 'code-js-ts'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 0, rust 1, js-ts 2, java 1, cpp 0, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** A key with no digits, or under 16 characters, or under a neutral variable name is missed. A random-looking ID stored under a name like `key` is replaced too; it only changes a string, so the code still parses. Not a full scanner: gitleaks or trufflehog would catch more.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 25 — english / A1 / `DA-A1-004`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-A1-004`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A1 invisible junk characters. Labelled rows: dclm 12, fineweb-edu 1, nemotroncc 14, synth 0. Examples it treats: `10355b4f94c87a2c` (dclm), `11c3cd0e50856c3e` (dclm), `094e33117f3c3cd2` (nemotroncc).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `4a22b0cbca7869fc` (en-dclm), original offset 0: `"\ufeff German Genealogy -- Ce"` (fix).
- `855032b92c2b8d25` (en-dclm), original offset 153: `"davon ge\u00adsprochen, unser Denkver"` (fix).
- `122504afaec49b2d` (en-dclm), original offset 0: `"\ufeff \u82f1\u6587\u5b57\u5178\u4e2d\u6587\u5b57\u5178\n\n\n\u63a8\u5230 Twitter!"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Delete the invisible characters named in the disease list. ZWJ (U+200D) and ZWNJ (U+200C) are **not** removed: they are part of Indic script and are not a disease. This pack is English, but the rule is written so it stays correct if it is ever reused on an Indic pack.

```python
RULE_ID = "DA-A1-004"
SOURCE_RULE_ID = "DA-A1-004"
CODE = "A1"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "mittalutkarsh"  # extractor
import re

_INVISIBLE = re.compile("[﻿​­‎‏‪-‮⁦-⁩]")

def medicine_a1(text):
    return _INVISIBLE.sub("", text)


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_a1(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 11 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 14 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** Removing a soft hyphen joins the two halves of a word, which is right for `never­ending` but wrong if a document ever used it as a real hyphen. Stripping bidi controls from a document that genuinely mixes right-to-left and left-to-right text would change how that text renders; there is no such document in this pack, but there would be in an Arabic or Hebrew one, and this medicine should not be reused there without a second look. ---
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 26 — english / A2 / `DA-A2-008`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-A2-008`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A2 control characters. Labelled rows: dclm 3, fineweb-edu 0, nemotroncc 0, synth 0. Examples it treats: `5d1fd12b101321f0` (dclm), `7b1d879aa4e04769` (dclm).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `94f537dcf85f69f8` (en-dclm), original offset 2486: `"called \u00e2\u0080\u009cThe Mystery of Half Mo"` (fix).
- `5d1fd12b101321f0` (en-dclm), original offset 12597: `" artist\u00c2\u0092s movements, from hand "` (fix).
- `7b1d879aa4e04769` (en-dclm), original offset 1645: `"varies\u00e2\u20ac\u009d, perhaps we should ste"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Remove the control characters U+0000 to U+001F (except tab and newline) and U+007F to U+009F. A carriage return is a control character too: CRLF and a lone CR become a newline.

```python
RULE_ID = "DA-A2-008"
SOURCE_RULE_ID = "DA-A2-008"
CODE = "A2"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new in the 29 Oct sheet as DA-A2-007
import re

A2_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def medicine_a2(text):
    new = A2_CONTROL.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return medicine_a2(doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 3 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A form feed used as a page break is removed, so the two pages run together. Every document with Windows line endings counts as changed.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule, 29 Oct sheet (was DA-A2-007). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 27 — english / A5 / `DA-A5-001`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-A5-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A5 wrong normal form. Labelled rows: dclm 3, fineweb-edu 0, nemotroncc 0, synth 0. Examples it treats: `10355b4f94c87a2c` (dclm), `68575a61a90990d5` (dclm).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `c64a732a64b1ce8b` (en-dclm), original offset 5005: `"o the nai\u0308ve realist is to quest"` (fix).
- `10355b4f94c87a2c` (en-dclm), original offset 642: `"ith Josue\u0301 Me\u0301ndez\u2019\u00a0Days of Sant"` (fix).
- `68575a61a90990d5` (en-dclm), original offset 984: `"\u0301\u00c6\u00b0\u00b1\u00ada\u00b7 O\u0303-A\u0300A\u0303\u00d7- I\u0308U\u0302E\u0308 fl \u00a5\u00b7 \u0308"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Normalise the text to NFC, the form the lab uses.

```python
RULE_ID = "DA-A5-001"
SOURCE_RULE_ID = "DA-A5-001"
CODE = "A5"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new in the 29 Oct sheet as DA-A5-001
import re

import unicodedata


def medicine_a5(text):
    new = unicodedata.normalize("NFC", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return medicine_a5(doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 3 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The bytes of decomposed text change, not its look. A text about Unicode normalisation loses the difference between its examples.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule, 29 Oct sheet (was DA-A5-001). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 28 — english / A3 / `DA-A3-002`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-A3-002`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A3 mojibake. Labelled rows: dclm 7, fineweb-edu 4, nemotroncc 4, synth 0. Examples it treats: `5d1fd12b101321f0` (dclm), `7b1d879aa4e04769` (dclm), `53dadf5fc6ee123a` (fineweb-edu).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `816e5ec1fb368590` (en-dclm), original offset 590: `".\n  \u2022 No\u00c2\u00a0waste products: Since "` (fix).
- `94f537dcf85f69f8` (en-dclm), original offset 140: `" called \u201cThe Mystery of Half Moo"` (fix).
- `5d1fd12b101321f0` (en-dclm), original offset 12596: `"e artist\u00c2\u0092s movements, from hand"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Detect the double-decoding signatures, repair with `ftfy.fix_text`, and drop the document only if the signature is still dense after repair (the bytes are gone, not just mis-decoded).

```python
RULE_ID = "DA-A3-002"
SOURCE_RULE_ID = "DA-A3-002"
CODE = "A3"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "shekar-maker"  # extractor; adapter for (text, flag)
import re
import ftfy  # added by Data A: used, never imported (pip install ftfy)

A3_RE = re.compile(r"â€[\x80-\xbf‘-™]?|Ã[\x80-\xbf\u0080-ÿ]|Â[\xa0-\xbf]|[\x80-\x9f]")

def m_a3(text):
    if not A3_RE.search(text): return text, False
    new = ftfy.fix_text(text)
    return new, len(A3_RE.findall(new)) * 1000 / max(len(new), 1) > 1.0


def _std(out, text):  # added by Data A
    # the author's result (new_text, flag) in the shared form: flag -> drop (their sheet: "flag for drop"),
    # else fix/keep by the text
    new, flag = out
    if flag: return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m_a3(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 4 fixed, 0 dropped, fineweb-edu 1 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The signature regex misses mojibake that went through a non-UTF-8 round trip, for example Cyrillic `й` standing in for `é` (`Pokйmon` in `68575a61a90990d5`, `Diffйrents` in `467b5c0aa1d13de8`) and symbol-font gibberish (`3dc93ffbd87ba839`): 3 of the 7 labelled documents are not touched. `ftfy` can in rare cases "repair" legitimate text that happens to look like mojibake (`Ã` followed by a letter in Portuguese); the gold run will show whether that happens in English.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for (text, flag). Added: ftfy. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 29 — english / B1 / `DA-B1-002`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-B1-002`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B1 HTML entities. Labelled rows: dclm 1, fineweb-edu 0, nemotroncc 3, synth 0. Examples it treats: `1992526bd6e98869` (dclm).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `1992526bd6e98869` (en-dclm), original offset 1492: `"s and GW&#39;s vehicles that wer"` (fix).

**Example gap:** 1/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Decode the common HTML entities (`&amp;`, `&nbsp;`, `&quot;`, `&lt;`, `&gt;`, dashes, quotes, `&#NNN;`, `&#xHH;`). `&nbsp;` becomes a plain space.

```python
RULE_ID = "DA-B1-002"
SOURCE_RULE_ID = "DA-B1-002"
CODE = "B1"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new in the 29 Oct sheet as DA-B1-002
import re

import html
import re

B1_ENTITY = re.compile(r"&(?:amp|nbsp|quot|apos|lt|gt|mdash|ndash|hellip|rsquo|lsquo|rdquo|ldquo|copy|reg|trade"
                       r"|#\d{2,6}|#x[0-9a-fA-F]{2,5});")


def medicine_b1(text):
    new = B1_ENTITY.sub(lambda m: html.unescape(m.group()).replace("\xa0", " "), text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return medicine_b1(doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 1 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A text that shows entities on purpose (an HTML tutorial) is changed. An entity that is not on the list stays.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule, 29 Oct sheet (was DA-B1-002). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 30 — english / B2 / `DA-B2-002`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-B2-002`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B2 HTML or XML tags. Labelled rows: dclm 3, fineweb-edu 1, nemotroncc 1, synth 0. Examples it treats: `6d1051dc3ca46585` (dclm), `a845e6c52e035cbb` (fineweb-edu).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `6d1051dc3ca46585` (en-dclm), original offset 2383: `"ock! --><div style=\"width:100%;h"` (fix).
- `a845e6c52e035cbb` (en-fineweb-edu), original offset 248: `"mework.\n<p>A Christmas murder my"` (fix).

**Example gap:** 2/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Remove common HTML tags (`<div>`, `<p>`, `<br/>`, `<span ...>`, `<li>`, `<strong>`, ...) when the text has at least two of them and is not about HTML (no code fence, `class=`, `<!DOCTYPE`, or the words html, tag, element). A single tag is often a mention, not markup.

```python
RULE_ID = "DA-B2-002"
SOURCE_RULE_ID = "DA-B2-002"
CODE = "B2"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new in the 29 Oct sheet as DA-B2-002
import re

B2_TAG = re.compile(r"</?(?:div|span|p|br|li|ul|ol|img|table|tr|td|th|tbody|thead|strong|em|font|iframe|script|style|center|hr)"
                    r"(?:\s[^<>]{0,200})?\s*/?>", re.I)
B2_ABOUT_HTML = re.compile(r"```|\bclass\s*=|<!DOCTYPE|\bhtml\b|\btag\b|\belement\b", re.I)


def medicine_b2(text):
    if B2_ABOUT_HTML.search(text) or len(B2_TAG.findall(text)) < 2:
        return ("keep", text)
    new = re.sub(r"[ \t]{2,}", " ", B2_TAG.sub(" ", text))
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return medicine_b2(doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 1 fixed, 0 dropped, fineweb-edu 1 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A text that quotes tags as examples without those words loses them. `<br>` and `<p>` become a space, not a line break, so lines can run together.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule, 29 Oct sheet (was DA-B2-002). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 31 — english / C3 / `DA-C3-001`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-C3-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C3 truncated document. Labelled rows: dclm 103, fineweb-edu 35, nemotroncc 101, synth 50. Examples it treats: `52422fff81211f50` (dclm), `4f2fc39dee7af855` (nemotroncc), `5ef3f9c12c7a2608` (nemotroncc).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `52422fff81211f50` (en-dclm), original offset 0: `"Tag: University of Southampton\n\nSolving a piece of the DFTD puzz"` (drop).
- `c1792de8d0f91aa8` (en-nemotroncc), original offset 0: `"Syria: Govt. forces demine Palmyra after retaking ancient city f"` (drop).
- `71a349332d2a5bc2` (en-nemotroncc), original offset 0: `"Where technology, community and commerce converge MWC Barcelona "` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Only the *stub* form is treated. A document of at most 600 characters whose last word is one no sentence ends on (`from`, `the`, `and`, ...) or that ends with a teaser `...` is dropped (the dangling-word test only applies when the text has no terminal punctuation).

```python
RULE_ID = "DA-C3-001"
SOURCE_RULE_ID = "DA-C3-001"
CODE = "C3"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "shekar-maker"  # extractor; adapter for (text, flag)
import re

DANGLING = set("a an the and or but of to in on at by for from with as that which who will would can could is are was were be been being has have had this these those its their his her my our your".split())

def m_c3(text, max_len=600):
    body = text.rstrip()
    if len(body) > max_len: return text, False
    last = (re.findall(r"[A-Za-z']+", body) or [""])[-1].lower()
    teaser = body.endswith(("...", "…", "[...]", "[…]", "(more)", "Read more"))
    unfinished = body[-1] not in ".!?\"')]}»”’:;" and last in DANGLING
    return text, bool(teaser or unfinished)


def _std(out, text):  # added by Data A
    # the author's result (new_text, flag) in the shared form: flag -> drop (their sheet: "flag for drop"),
    # else fix/keep by the text
    new, flag = out
    if flag: return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m_c3(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 1 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 5 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** My first version trimmed any last line without terminal punctuation; it changed 5 of the 28 documents then in the proxy set (complete sentences that simply lack a full stop), so it was withdrawn. The stub rule's dangling-word test then dropped a clean 560-character document ending `...what research impact is.`, which failed the 1% limit on the 65-document proxy; it now applies only when the text has no terminal punctuation. The rule catches 1 of the 98 labelled documents, because in this pack C3 is mostly mid-text gaps where a link, a citation, a quote or an image was stripped by an earlier cleaner (the readers' notes say most C3 rows are of this kind, not end-of-document cuts). There is no safe regex for that; it is the main finding of this slice for the pipeline team: the HTML-to-text step drops anchor text and embedded content.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for (text, flag). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 32 — english / C3 / `DA-C3-003`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-C3-002`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C3 truncated document. Labelled rows: dclm 103, fineweb-edu 35, nemotroncc 101, synth 50. Examples it treats: `484c668df3c40868` (dclm), `52422fff81211f50` (dclm), `8262087c39b0c8c5` (fineweb-edu).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `52422fff81211f50` (en-dclm), original offset 0: `"Tag: University of Southampton\n\nSolving a piece of the DFTD puzz"` (drop).
- `484c668df3c40868` (en-dclm), original offset 0: `"University of Minnesota\nSchool of Physics & Astronomy\n\n\nNew phys"` (drop).
- `8262087c39b0c8c5` (en-fineweb-edu), original offset 0: `"The Truth About\nNikola Tesla became aware early in the 20th cent"` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Drop the document when it ends in an excerpt marker, or when the last word is a function word that cannot end an English sentence. Truncation cannot be repaired, and the tail is the only place it can be detected without guessing.

```python
RULE_ID = "DA-C3-003"
SOURCE_RULE_ID = "DA-C3-002"
CODE = "C3"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "mittalutkarsh"  # extractor
import re

_MARKER = re.compile(r"\[\s*(?:…|\.\.\.)\s*\]$")

_DANGLING = frozenset(
    "a an the and or but of to in on at for with from by as is are was were "
    "that this these those which who because however".split()
)

_LAST_TOKEN = re.compile(r"([A-Za-z0-9']+)[^A-Za-z0-9']*$")

def medicine_c3(text):
    tail = text.rstrip()
    if not tail:
        return text
    if _MARKER.search(tail):
        return ("drop", "")
    if tail.endswith((".", "!", "?", '"', "'", ")", ":", "…")):
        return text
    token = _LAST_TOKEN.search(tail)
    if token and token.group(1).lower() in _DANGLING:
        return ("drop", "")
    return text


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_c3(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 3 dropped, fineweb-edu 0 fixed, 1 dropped, nemotroncc 0 fixed, 14 dropped, synth 0 fixed, 1 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** It reads only the end of the document, so it misses truncation in the middle, which is where I found it in `a1b97fd910707a8d` and `5a6856a5e9397412` — there the extractor dropped link and image text and left the sentence around it standing. Those need a different medicine, and I have not written one. A document that genuinely ends on an ellipsis for effect would be dropped wrongly; I saw none in this pack, but it is the obvious failure. ---
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 33 — english / C5 / `DA-C5-002`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-C5-002`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C5 lists of keywords or links. Labelled rows: dclm 61, fineweb-edu 30, nemotroncc 71, synth 7. Examples it treats: `0b139d9931d96986` (dclm), `1ec7fa64b9476242` (dclm).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `3dc93ffbd87ba839` (en-dclm), original offset 0: `"Corporate, Political, Government Corruption News in Pakistan\n\nPr"` (drop).
- `0b139d9931d96986` (en-dclm), original offset 0: `"Free AUTO INSURANCE Quotes For Your State\n\nGet a list of the lea"` (drop).
- `1ec7fa64b9476242` (en-dclm), original offset 0: `"\u8fd4\u56de\u5217\u8868 \u56de\u5fa9 \u767c\u5e16\n\nCheap Jerseys From China3t\n\ncheap jerseys\n\u00a0\u00a0dollars)"` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Drop the document when at least two different injected-keyword markers appear, or when a single line is a run of five or more short pipe-separated phrases. Two markers rather than one, because a page may mention a brand once for an honest reason.

```python
RULE_ID = "DA-C5-002"
SOURCE_RULE_ID = "DA-C5-002"
CODE = "C5"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "mittalutkarsh"  # extractor
import re

_SPAM = tuple(
    re.compile(p, re.I)
    for p in (
        r"\bcheap\s+(?:nfl|nba|mlb|nhl)\b",
        r"\bcheap\s+(?:michael\s+kors|oakley|ray\s*bans?|jerseys)\b",
        r"\bray\s*bans?\s+(?:sunglasses|outlet)\b",
        r"\b(?:auto|car)\s+insur\w*\s+(?:quotes?|qiotes?|rates?)\b",
        r"\bfree\s+auto\s+insurance\s+quotes\b",
        r"\bsex\s+dating\s+in\b",
        r"\bwrite\s+my\s+essay\b",
        r"\b(?:카지노|바카라|룰렛)\b",
        r"\bpigmentación\s+capilar\b",
    )
)

_KEYWORD_LINE = re.compile(r"^(?![ \t]*[•·*\-])(?:[^|\n]{2,40}\|){6,}[^|\n]{2,40}[ \t]*$", re.M)

def medicine_c5(text):
    hits = sum(1 for p in _SPAM if p.search(text))
    if hits >= 2 or _KEYWORD_LINE.search(text):
        return ("drop", "")
    return text


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_c5(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 4 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The marker list is drawn from one pack of 500 English documents, so it will age badly — next year's spam sells something else. A genuine article about car insurance that quotes a spam phrase twice would be dropped. The pipe-separated test would also catch an honest table that survived extraction as a single line, though I saw none in this pack. ---
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 34 — english / D4 / `DA-D4-001`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-D4-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** D4 bad machine translation. Labelled rows: dclm 21, fineweb-edu 3, nemotroncc 17, synth 2. Examples it treats: `0a28e7f42a4bba02` (dclm).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `0a28e7f42a4bba02` (en-dclm), original offset 0: `"Write My Essay!\nArun Kolatkar An Old Woman\n\nArun Kolatkar An Old"` (drop).

**Example gap:** 1/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Drop the document when the mechanical residue of a spinner is still in the text: unused spintax alternatives in braces, or an essay-mill banner. I am not trying to detect spun prose itself.

```python
RULE_ID = "DA-D4-001"
SOURCE_RULE_ID = "DA-D4-001"
CODE = "D4"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "mittalutkarsh"  # extractor
import re

_SPINTAX = re.compile(r"\{[^{}\n]{2,60}\|[^{}\n]{2,60}\}")

_MILL = re.compile(r"\b(?:write my essay|essay writing service|buy essays? online)\b", re.I)

def medicine_d4(text):
    if _SPINTAX.search(text) or _MILL.search(text):
        return ("drop", "")
    return text


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_d4(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 1 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** This reaches only the documents where the spinner left its syntax behind. Finished spun text, which is most of what I labelled D4, reads as ordinary English to a regular expression and passes straight through — `3dce67ac37d56429` and `a55992c7a90ce4f4` are both missed. Detecting it properly needs a language model scoring word collocations, which is beyond a medicine of this kind. The spintax pattern would also fire on a document that legitimately shows spintax syntax, such as a page explaining how article spinners work. ---
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 35 — english / C1 / `DA-C1-006`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-C1-006`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C1 boilerplate. Labelled rows: dclm 389, fineweb-edu 308, nemotroncc 161, synth 76. Examples it treats: `13b37bf5acff4d16` (dclm), `319afcfc2bbab65b` (dclm), `96dfcd8dcd7a0cff` (fineweb-edu).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `3f9cf2259ef9ba72` (en-dclm), original offset 0: `"Skip to main content\n\nPO"` (fix).
- `b9ad87575375859e` (en-dclm), original offset 99: `"\n\n\n\n\n\n\n\nRelated Posts:\n\n\n  1. Jo"` (fix).
- `8193a0622521740a` (en-dclm), original offset 3273: `"erstock\n\nRead More >"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Delete every line that is only a known widget or menu label (`Primary tabs`, `Search for:`, `Related posts`, `Share this:`, `Read more`, `Link copied`, `Quantity`, and a few more). A whole-line match is required, so a sentence that contains these words is never touched.

```python
RULE_ID = "DA-C1-006"
SOURCE_RULE_ID = "DA-C1-006"
CODE = "C1"
ACTION = "fix"
STAGE = "35"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-nemotroncc"  # pack whose medicine this came from
AUTHOR = "s9k96"  # extractor; None means drop
import re

WIDGET = re.compile(r"(?i)(?:primary tabs|search for:?|related (?:documents|posts|articles):?|click to expand\W*|read more\W*|\[?read more\W*\]?|share this:?|share on (?:other sites|[a-z ]+)|previous|next|menu|contents|advertisement|loading\W*|link copied|the link has been copied!?|post navigation|quantity|breadcrumb|logged|registered|banned|show more|you may also like[a-z ]*|subscribe to [a-z ]+|skip to (?:main )?content|back to top)")

def c1(t):
    """Delete lines that consist only of a known widget or menu label ('Primary tabs', 'Search for:', 'Related posts', 'Share this:' ...)."""
    return "\n".join(l for l in t.split("\n") if not WIDGET.fullmatch(l.strip()))


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(c1(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 6 fixed, 0 dropped, fineweb-edu 2 fixed, 0 dropped, nemotroncc 27 fixed, 0 dropped, synth 1 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** Most reviewed C1 lines are not on the label list. Examples are `Store Information`, `Featured Manchester Subdivision Real Estate Properties`, `Posted by ... October 2, 2013` and `source: easemytrip`, which are site-specific. The list needs more labels as more packs are read. A real section titled `Contents` or `Next` on its own line would lose that line.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; None means drop. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 36 — english / C2 / `DA-C2-003`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-C2-003`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C2 repeated lines. Labelled rows: dclm 38, fineweb-edu 6, nemotroncc 39, synth 1. Examples it treats: `1e13b455581e96ca` (dclm), `28bd69b4ed987643` (dclm), `b888d78a21618c96` (fineweb-edu).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `50d363e8b8340b11` (en-dclm), original offset 1648: `" thing.\ncheck the teleport:\n\na f"` (fix).
- `6c6a180069b69bdb` (en-dclm), original offset 34274: `"equal.\n\n        1. Ally Fogg\n\n  "` (fix).
- `c64a732a64b1ce8b` (en-dclm), original offset 36: `" tf h1\n\nTeknik forex tf h1\n\n\n\n\n\n"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Remove the later copies of a line that appears 3 or more times in the same document (lines of at least 10 characters, compared without extra spaces); the first copy is kept. Shorter lines ("*", "Answer") are left alone. In code (the function the medicine runs; the patterns, weights and helpers it uses are in Appendix B, the full runnable file):

```python
RULE_ID = "DA-C2-003"
SOURCE_RULE_ID = "DA-C2-003"
CODE = "C2"
ACTION = "fix"
STAGE = "35"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-fineweb-edu"  # pack whose medicine this came from
AUTHOR = "deepjyotisaha"  # extractor; adapter for spans
import re

def _merge(spans):
    """Overlapping spans joined into one, keeping the rule of the first."""
    out = []
    for s, e, rule in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(e, out[-1][1]), out[-1][2])
        else:
            out.append((s, e, rule))
    return out

C2_MIN_REPEAT, C2_MIN_CHARS = 3, 10

def c2_spans(text):
    """C2: later copies of a line repeated C2_MIN_REPEAT or more times in the document."""
    seen, lines, pos = {}, [], 0
    for line in text.split("\n"):
        key = " ".join(line.split())
        if len(key) >= C2_MIN_CHARS:
            lines.append((pos, pos + len(line), key))
            seen[key] = seen.get(key, 0) + 1
        pos += len(line) + 1
    out, first = [], set()
    for s, e, key in lines:
        if seen[key] >= C2_MIN_REPEAT:
            if key in first:
                out.append((s, e, "C2-repeated-line"))
            first.add(key)
    return out


def _std(out, text):  # added by Data A
    # the author's result (spans to remove) in the shared form, as their clean() reads it: (spans, True) from
    # c1_spans -> drop; a whole-document "B4-mostly-code" or "C5-list-page" span -> drop; else the spans go
    if isinstance(out, tuple):
        out, flagged = out
        if flagged: return ("drop", text)
    if out and out[0][2] in ("B4-mostly-code", "C5-list-page"): return ("drop", text)
    new = text
    for s, e, _ in reversed(_merge(out)):
        new = new[:s] + new[e:]
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(c2_spans(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 20 fixed, 0 dropped, fineweb-edu 4 fixed, 0 dropped, nemotroncc 19 fixed, 0 dropped, synth 2 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 1/170; fineweb-edu 1/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The medicine finds 6 of the 8 labelled cases. On the whole pack it changes 4 documents: besides the labelled repeats it removes repeated section headings that were labelled C1 and repeated table headers, which belong to their tables. It misses a passage printed twice when the copies are not identical line by line (document 53). --- The appendices below support the medicines above; they are not medicines themselves. ### Appendix A: test on unseen documents On 2026-10-25, before documents 151–500 were labelled, the medicines' predictions for them were saved (`frozen_predictions.json`; C1 scorer trained on the first 150 documents, threshold 0.97). Comparing them with the labels made afterwards (`frozen_test.py`): - **C1 caught:** 174 of 454 labelled C1 lines (38.3%). - **C1 precision:** 169 of the 178 lines it removed were labelled C1 (94.9%). - **Clean documents changed:** 1 of 143 (0.7%): documents 457. - **C3:** found in 0 of the 7 documents labelled C3. - **Blind documents** (every 10th, labelled without seeing any suggestion; the fully independent test): 17 of 47 C1 lines caught (36.2%), 17 of 20 removed lines labelled C1 (85.0%), 0 of 17 clean documents changed. In the other documents the reader saw the predictions as suggestions while labelling, so agreement there is partly their influence. The medicine above was retrained on all labelled documents after this test. ### Appendix B: runnable code All the medicines in one self-contained Python file: copy it into `medicine_standalone.py` and it runs with the standard library alone (no numpy, no other files). It is generated from the code and the trained weights that were tested above, and it gives the same result as that code on all 500 documents of the pack (0 differences, checked by `standalone.py`), when it is given the pack's line-repetition counts (below). Without them, C1 gives a different result on 7 of the 500 documents, because it cannot tell which lines repeat across the pack. How to use it:
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for spans. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 37 — english / C5 / `DA-C5-005`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-C5-005`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C5 lists of keywords or links. Labelled rows: dclm 61, fineweb-edu 30, nemotroncc 71, synth 7. Examples it treats: `4604f40da35906cc` (fineweb-edu), `58b9213cca24ff17` (fineweb-edu), `d49190f1c5ef2a70` (nemotroncc).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `b0b8c0fe32cb4bee` (en-dclm), original offset 3467: `"fitness!\n\nTopics: stretches, wor"` (fix).
- `943b00214cee55c2` (en-dclm), original offset 0: `"Tag: app store duopoly\n\nT"` (fix).
- `52422fff81211f50` (en-dclm), original offset 0: `"Tag: University of South"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Remove a line that is a tag list: it starts with `Tags:`, `Tag:`, `Keywords:`, `Tagged with:`, `Topics:` or `Filed under:`. Lists of commas or pipes without such a word are left alone: in clean documents they are stat lines, ingredient lists and genre lists.

```python
RULE_ID = "DA-C5-005"
SOURCE_RULE_ID = "DA-C5-005"
CODE = "C5"
ACTION = "fix"
STAGE = "35"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new in the 29 Oct sheet as DA-C5-002
import re

C5_PREFIX = re.compile(r"^(?:tags?|keywords?|tagged(?: with| in)?|topics?|filed under)\s*:", re.I)


def medicine_c5(text):
    lines = text.split("\n")
    keep = [ln for ln in lines if not C5_PREFIX.search(ln.strip())]
    if len(keep) == len(lines):
        return ("keep", text)
    new = "\n".join(keep).strip("\n")
    return ("drop", text) if not new.strip() else ("fix", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return medicine_c5(doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 4 fixed, 1 dropped, fineweb-edu 2 fixed, 0 dropped, nemotroncc 4 fixed, 0 dropped, synth 1 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A real heading such as `Topics:` before a list in an article is removed. Keyword spam without the prefix is missed.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule, 29 Oct sheet (was DA-C5-002). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 38 — english / D3 / `DA-D3-003`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-D3-003`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** D3 mixed language. Labelled rows: dclm 24, fineweb-edu 5, nemotroncc 6, synth 1. Examples it treats: `122504afaec49b2d` (dclm), `1ec7fa64b9476242` (dclm), `95e8df7138976c19` (fineweb-edu).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `1ec7fa64b9476242` (en-dclm), original offset 0: `"\u8fd4\u56de\u5217\u8868 \u56de\u5fa9 \u767c\u5e16\n\nCheap Jersey"` (fix).
- `e53279211deae6a8` (en-dclm), original offset 103: `"eeting\n\n\u0443\u0437\u043d\u0430\u0442\u044c \u0431\u043e\u043b\u044c\u0448\u0435\nThe US Sec"` (fix).
- `122504afaec49b2d` (en-dclm), original offset 0: `"\ufeff \u82f1\u6587\u5b57\u5178\u4e2d\u6587\u5b57\u5178\n\n\n\u63a8\u5230 Twitter!"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Do not fix real code-switching. The rule deletes only whole lines in which more than half of the letters are not Latin, in an English pack. A foreign word inside an English sentence stays.

```python
RULE_ID = "DA-D3-003"
SOURCE_RULE_ID = "DA-D3-003"
CODE = "D3"
ACTION = "fix"
STAGE = "35"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-nemotroncc"  # pack whose medicine this came from
AUTHOR = "s9k96"  # extractor; None means drop
import re

def d3(t):
    """Delete lines whose letters are mostly non-Latin (CJK, Cyrillic, Hangul, Devanagari ...) in an English document."""
    import unicodedata
    def foreign(l):
        letters = [c for c in l if c.isalpha()]
        return len(letters) >= 3 and sum(unicodedata.name(c, "").split(" ")[0] != "LATIN" for c in letters) / len(letters) > 0.5
    return "\n".join(l for l in t.split("\n") if not foreign(l))


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(d3(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 4 fixed, 0 dropped, fineweb-edu 1 fixed, 0 dropped, nemotroncc 4 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A quoted line in another language, or a bilingual example, is deleted from a good document. Mixed sentences such as `3da0a9bbeeac1a6a` (Spanish and English in one sentence) are not fixed; they need a human decision.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; None means drop. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 39 — english / B4 / `DA-B4-007`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-B4-007`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B4 template and code junk. Labelled rows: dclm 25, fineweb-edu 8, nemotroncc 15, synth 36. Examples it treats: `281de2e3af773d76` (synth), `47f4f5107ac9aece` (synth).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `47f4f5107ac9aece` (en-nemotroncc-synth), original offset 850: `" safety.\n\nThe provided text also"` (fix).
- `d896f8ca6a2beae1` (en-nemotroncc-synth), original offset 3236: `"tion: Which are the leading e-co"` (fix).
- `b876745af3ee971b` (en-nemotroncc-synth), original offset 2476: `"tion: Who were the three beautif"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Match the negated phrase (`not … in the (given|provided) text/passage/document`, `the text does not provide/mention/…`) or `the given/provided text`. Delete the bullet, `Key: value` line or QA pair that carries it; in running prose delete only the sentence.

```python
RULE_ID = "DA-B4-007"
SOURCE_RULE_ID = "DA-B4-007"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "maheshsv"  # extractor; adapter for (text or None, changed)
import re
ANSWER_LINE = re.compile('^(?:Answer|A)\\s*[:.]|\\bAnswer:\\s')  # added by Data A: from maheshsv's medicine.md
KEY_VALUE_LINE = re.compile('^[^:\\n]{1,60}:\\s')  # added by Data A: from maheshsv's medicine.md
LIST_MARK = re.compile('^(?:[-*•–—]|\\d+[.)]|[a-z][.)])\\s')  # added by Data A: from maheshsv's medicine.md
META = re.compile('(?i)\\bnot (?:explicitly |specifically |directly )?(?:provided|stated|mentioned|specified|given|available|included|present|disclosed|named) in the (?:given |provided |original |above |source )?(?:text|passage|article|document|excerpt|content|context)|\\bthe (?:text|passage|article|document) does not (?:explicitly |specifically )?(?:provide|mention|specify|state|say|give|include|indicate|name)\\b|\\bthe (?:given|provided) (?:text|passage) (?:also )?(?:discusses|mentions|describes|states|says|provides|refers|covers|explains|includes|lists|notes)\\b')  # added by Data A: from maheshsv's medicine.md
MIN_KEEP_CHARS = 200  # added by Data A: from maheshsv's medicine.md

def remove_meta_comments(text: str) -> tuple[str | None, bool]:
    """Delete the bullet, `Key: value` line or Question/Answer pair that carries a rewriter meta-comment; in running
    prose delete only the sentence."""
    if not META.search(text):
        return text, False
    lines = text.split("\n")
    drop = set()
    for i, ln in enumerate(lines):
        if not META.search(ln):
            continue
        s = ln.strip()
        if s.startswith("Question:") or ANSWER_LINE.match(s):
            drop.add(i)                                   # drop the whole QA pair, whichever line carries it
            if s.startswith("Question:") and i + 1 < len(lines) and ANSWER_LINE.match(lines[i + 1].strip()):
                drop.add(i + 1)
            if ANSWER_LINE.match(s) and not s.startswith("Question:") and i > 0 and lines[i - 1].strip().startswith("Question:"):
                drop.add(i - 1)
        elif LIST_MARK.match(s) or KEY_VALUE_LINE.match(s):
            drop.add(i)
        else:
            sentences = re.split(r"(?<=[.!?])\s+", ln)
            lines[i] = " ".join(x for x in sentences if not META.search(x))
    new = "\n".join(ln for i, ln in enumerate(lines) if i not in drop)
    new = re.sub(r"\n{3,}", "\n\n", new).strip()
    if len(new) < MIN_KEEP_CHARS:
        return None, True
    return new, True


def _std(out, text):  # added by Data A
    # the author's result (new_text or None, changed) in the shared form: None -> drop, else fix/keep by the text
    new, _ = out
    if new is None: return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(remove_meta_comments(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 8 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The pattern deliberately does **not** match plain "in the text" (QA questions such as "Who is the main character in this text?" are the normal format of `diverse_qa_pairs`), nor "The text discusses …" and "The text mentions that …" (the summary frame of `distill` and `knowledge_list` rewrites, present in several clean rows), nor "the original text", which two `wrap_medium` documents use legitimately as product copy about paraphrasing tools. Constructed sentences such as `Read the given passage carefully and answer the questions that follow.`; `Applicants must sign the provided document before the deadline.` are no longer matched, because the `given/provided text` branch now requires a reporting verb. A Question line that carries the phrase takes its Answer line with it and vice versa, so no orphan line is left. A genuine essay that writes "the provided text also discusses" would lose that sentence.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for (text or None, changed). Added: ANSWER_LINE, KEY_VALUE_LINE, LIST_MARK, META, MIN_KEEP_CHARS. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 40 — english / B4 / `DA-B4-008`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-B4-008`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B4 template and code junk. Labelled rows: dclm 25, fineweb-edu 8, nemotroncc 15, synth 36. Examples it treats: `0b500dc5f31c1afc` (synth), `1f21b7ad88d0ec88` (synth).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `cab2dbea05fa92b7` (en-dclm), original offset 17454: `"e out wi'me, or somethin'?\"\n\nUnf"` (fix).
- `dede015abe25b6a1` (en-dclm), original offset 365: `"whilst I'se a-ponderin' 'pon it."` (fix).
- `536547e07d7d65ca` (en-nemotroncc-synth), original offset 286: `"ion. The'resources(-Count)' repr"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** When a letter is directly followed by `'`, the quote opens a word that starts with `s`, `r` or `m`, and the phrase is closed by another `'` on the same line, insert a space before the quote. The `s/r/m` restriction comes from the data: every one of the 23 glitches opens such a word, which fits a detokeniser that treated the quote as the start of a contraction (`'s`, `'re`, `'m`) and glued it to the previous word. Contractions, possessives and poetic elisions (`it's`, `don't`, `we're`, `o'clock`, `y'all`, `rock'n'roll`, `ne'er`) are excluded by the look-ahead; Python string prefixes (`f'…'`, `r'…'`, `b'…'`, `rb'…'`) by the look-behind.

```python
RULE_ID = "DA-B4-008"
SOURCE_RULE_ID = "DA-B4-008"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "maheshsv"  # extractor; adapter for (text or None, changed)
import re
DETOK = re.compile("(?<=[A-Za-z])(?<![^A-Za-z][frbuFRBU])(?<![^A-Za-z][rR][bB])(?<![^A-Za-z][bB][rR])'(?!s\\b|t\\b|re\\b|ll\\b|ve\\b|d\\b|m\\b|em\\b|n'|er\\b|clock\\b|all\\b|am\\b)(?=[srmSRM][A-Za-z][^'\\n]{0,40}'(?:[\\s,.;:)!?]|$))", re.M)  # added by Data A: from maheshsv's medicine.md

def fix_detok_quotes(text: str) -> tuple[str | None, bool]:
    new = DETOK.sub(" '", text)
    return new, new != text


def _std(out, text):  # added by Data A
    # the author's result (new_text or None, changed) in the shared form: None -> drop, else fix/keep by the text
    new, _ = out
    if new is None: return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(fix_detok_quotes(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 2 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 18 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A possessive directly followed by a quoted phrase that closes on the same line (`the boys'bikes'`) would get a spurious space; not seen in 500 documents. Constructed code and verse inputs (`print(f'hello world')`; `pattern = re.compile(r'sample')`; `payload = b'raw'`; `I ne'er saw such a thing,' she said`; `the boys' bikes were new`) are left alone. False negatives: a quoted phrase longer than 40 characters, a glitch with no closing quote on the line, the sibling variant with a dot-extension (`e.g.,.tar`, `like.yaml`, `the.NET`: 2 documents, labelled B4, not fixed by this rule). Curly quotes (’) are not handled; none occur in this pack. The B4 total (36 documents) is larger than the two rules together because B4 was also used, as the closest code, for other pipeline junk in 11 documents: `d2fb665c40af5edb` (`-DATE-` placeholder left in a bill description); `ea0ecda1c2f25dd1` (OCR glyph junk `e~ \` inside prose); `6011e88c8cc9c77d` (missing space before dot-extensions (`in.jpg,.png`)); `12693fe362d15d0d` (Cloudflare `[email protected]` placeholder); `373e0f0dd5699ac0` (e-learning template demo content under a real course title, dropped); `57922931d471745c` (epoch-bug date `January 17, 1970` and midnight time copied from the CMS); `0c03a4c096276336` (forum thread recast as an AI/user exchange); `d4f559ee86104b5b` (missing space before `.NET`); `68924f97019edabb` (`https://www.example.com/…` placeholder link); `e472a2fcc0df3984` (SEO-writing prompt leaked into the prose, dropped); `03ad0f392751ba37` (missing space before dot-extensions (`e.g.,.tar`)). The most training-relevant of these is the leaked SEO-writing prompt in `e472a2fcc0df3984` ("vary your verbs …"), dropped, and the chat-role recasting in `0c03a4c096276336` ("The AI advises the user …"), which teaches the assistant/user frame as plain text and sits next to B3 in danger.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for (text or None, changed). Added: DETOK. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 41 — english / B4 / `DA-B4-012`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-B4-009`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B4 template and code junk. Labelled rows: dclm 25, fineweb-edu 8, nemotroncc 15, synth 36. Examples it treats: `7ecdf57b3e06fd56` (dclm), `90c2a9476f8445ad` (dclm).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `e3fba14beec00b2b` (en-dclm), original offset 0: `"fbq('track', 'ViewConten"` (fix).
- `7ecdf57b3e06fd56` (en-dclm), original offset 15: `" Boots\n\nGoogle Adsense Here\n\nWol"` (fix).
- `b612431bc1ffadd2` (en-dclm), original offset 0: `"[an error occurred while"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Remove the junk tokens where they stand, and delete the line when the whole line is a tracking call or an ad placeholder. Each pattern is a literal artefact, not a guess.

```python
RULE_ID = "DA-B4-012"
SOURCE_RULE_ID = "DA-B4-009"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "mittalutkarsh"  # extractor
import re

_TOKENS = tuple(
    re.compile(p, re.I)
    for p in (
        r"\{/?PARAGRAPH\}",
        r"\[an error occurred while processing this directive\]",
        r"\{\{\s*[A-Za-z_][\w.]*\s*\}\}",
    )
)

_JUNK_LINE = re.compile(
    r"^[ \t]*(?:fbq\(.*?\);?|ga\(.*?\);?|_gaq\.push\(.*?\);?|"
    r"google adsense here|advertisement)[ \t]*$",
    re.I | re.M,
)

_BLANKS = re.compile(r"\n{3,}")

def medicine_b4(text):
    out = _JUNK_LINE.sub("", text)
    for pattern in _TOKENS:
        out = pattern.sub("", out)
    if out == text:
        return text          # nothing removed, so do not touch the spacing either
    return _BLANKS.sub("\n\n", out)


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_b4(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 5 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 1 fixed, 0 dropped, synth 1 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A page that is *about* web analytics and quotes `fbq('track', ...)` on a line of its own would lose the line it is discussing. Removing `{/PARAGRAPH}` in place can leave two words joined with no space where the extractor used the marker as the only separator, which is what happened in `f819811b670939d0`; the text is still readable but one word boundary is lost. ---
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 42 — english / B4 / `DA-B4-010`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-B4-010`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B4 template and code junk. Labelled rows: dclm 25, fineweb-edu 8, nemotroncc 15, synth 36. Examples it treats: `3e44df6a7ddb0098` (fineweb-edu).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `3e44df6a7ddb0098` (en-fineweb-edu), original offset 0: `"\u0060page.data.shortTitle ||"` (fix).

**Example gap:** 1/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Two parts. - template junk (fix): remove what a web page left unfilled: "{{ title }}", "{% if … %}", "${name}", a code expression in backticks such as "`page.data.shortTitle || page.data.title`", "NaN" or "undefined" right after ":", "=" or "$", and a line that is only "undefined", "NaN" or "null"; - mostly code (drop): a line is a code line when it has at least two code tokens ("::", "->", "==", "&&", "{", "}", a line ending in ";", a line starting with "import", "def", "return", "public", "$ ", "Sub", …) and at least one for every six words; a table row "|cell||cell|" is never a code line. A document whose code lines hold more than half of its characters is dropped; - code snippets inside an article are kept on purpose (decided 27 Oct): tutorials and manual pages with a few lines of code are good training text, and cutting them risks removing real content. In code (the function the medicine runs; the patterns, weights and helpers it uses are in Appendix B, the full runnable file):

```python
RULE_ID = "DA-B4-010"
SOURCE_RULE_ID = "DA-B4-010"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-fineweb-edu"  # pack whose medicine this came from
AUTHOR = "deepjyotisaha"  # extractor; adapter for spans
import re

def _merge(spans):
    """Overlapping spans joined into one, keeping the rule of the first."""
    out = []
    for s, e, rule in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(e, out[-1][1]), out[-1][2])
        else:
            out.append((s, e, rule))
    return out

B4_TEMPLATE = re.compile(
    r"\{\{[^{}\n]{0,80}\}\}"                          # {{ title }}
    r"|\{%[^\n]{0,80}?%\}"                            # {% if x %}
    r"|\$\{[^{}\n]{0,80}\}"                           # ${name}
    r"|`[\w.]+(?:\s*(?:\|\||&&)\s*[\w.]+)+`"          # `page.data.shortTitle || page.data.title`
    r"|(?<=[:=$])\s*(?:undefined|NaN)\b"              # Price: NaN, name=undefined
    r"|^[ \t]*(?:undefined|NaN|null)[ \t]*$", re.M)

B4_CODE_TOKENS = re.compile(
    r"::|->|=>|==|!=|<=|>=|&&|\|\||\+\+|\+=|-=|\);|\)\s*\{|[{};]\s*$|\}"
    r"|^\s*(?:#include|import\s|from\s+\S+\s+import|def\s|class\s|public\s|private\s|static\s|void\s|return\b"
    r"|require\s|var\s|let\s|const\s|function\b|Sub\s|End Sub|Dim\s|\$\s|>>>\s|>\s)"
    r"|\b(?:End Sub|ByVal|As Integer|System\.out|printf|println)\b", re.M)

B4_MIN_TOKENS, B4_WORDS_PER_TOKEN, B4_SHARE = 2, 6, 0.5

TABLE_ROW = re.compile(r"^\s*\|.*\|\|")

def b4_code_lines(text):
    """(start, end) of every line that looks like code."""
    out, pos = [], 0
    for line in text.split("\n"):
        tokens = len(B4_CODE_TOKENS.findall(line))
        words = len(line.split())
        if tokens >= B4_MIN_TOKENS and tokens * B4_WORDS_PER_TOKEN >= words and not TABLE_ROW.match(line):
            out.append((pos, pos + len(line)))
        pos += len(line) + 1
    return out

def b4_spans(text):
    """B4: the document is dropped if it is mostly code; otherwise template expressions are removed."""
    code = sum(e - s for s, e in b4_code_lines(text))
    if text.strip() and code > B4_SHARE * len(text.strip()):
        return [(0, len(text), "B4-mostly-code")]
    return [(m.start(), m.end(), "B4-template") for m in B4_TEMPLATE.finditer(text)]


def _std(out, text):  # added by Data A
    # the author's result (spans to remove) in the shared form, as their clean() reads it: (spans, True) from
    # c1_spans -> drop; a whole-document "B4-mostly-code" or "C5-list-page" span -> drop; else the spans go
    if isinstance(out, tuple):
        out, flagged = out
        if flagged: return ("drop", text)
    if out and out[0][2] in ("B4-mostly-code", "C5-list-page"): return ("drop", text)
    new = text
    for s, e, _ in reversed(_merge(out)):
        new = new[:s] + new[e:]
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(b4_spans(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 0 dropped, fineweb-edu 1 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The medicine finds 1 of the 16 labelled cases. On the whole pack it changes 1 document. The mostly-code part drops no document of this pack: the most code-like one (document 10) has code in only 3% of its text. The other B4 documents are articles with a code snippet (a Visual Basic or Java listing, a Ruby example, a command manual page, a Haskell mailing-list post), kept on purpose; the readers' labels remain the record of them. Code flattened into a prose line by the original crawl is hard to tell from prose with symbols, which is why the drop needs more than half of the document to be code.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for spans. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 43 — english / B4 / `DA-B4-011`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-B4-011`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B4 template and code junk. Labelled rows: dclm 25, fineweb-edu 8, nemotroncc 15, synth 36. Examples it treats: `d2fb665c40af5edb` (synth).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `d2fb665c40af5edb` (en-nemotroncc-synth), original offset 318: `"e After -DATE-: The amount you o"` (fix).

**Example gap:** 1/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Replace the exact heading `Total Due After -DATE-:` with `Total Due After the Due Date:` only when it occurs exactly once. Leave all other text unchanged. The function accepts a text string and returns a text string; it has no document-ID filter, so the same rule can be evaluated on unseen gold documents. It requires only the Python standard library and installs no tools.

```python
RULE_ID = "DA-B4-011"
SOURCE_RULE_ID = "DA-B4-011"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "AJJAPUSIVA"  # extractor
import re

def medicine_b4(text):
    """Return text with one exact billing-heading placeholder repaired."""
    old = "Total Due After -DATE-:"
    new = "Total Due After the Due Date:"
    if text.count(old) != 1:
        return text
    return text.replace(old, new, 1)


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_b4(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 1 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The literal heading might be intentional quoted text, documentation of a template, or an actual bill that requires a specific date. The rule cannot distinguish these contexts and may change valid text. Repeated occurrences are deliberately left unchanged for review. A gold-set pass alone does not establish effectiveness on the full dataset.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 44 — english / F1 / `DA-F1-005`

**Consolidation:** Source [medicine_english.md](medicine_english.md); original identity `DA-F1-005`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** F1 personal data. Labelled rows: dclm 13, fineweb-edu 12, nemotroncc 13, synth 2. Examples it treats: `416e12ac72df0b07` (dclm), `71f25549c2c4200d` (dclm), `fab230d1a3b03a77` (nemotroncc).
<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: 0 changed / 0 dropped of 62 (PASS); en-fineweb-edu: 0 changed / 0 dropped of 158 (PASS); en-nemotroncc: 0 changed / 0 dropped of 34 (PASS); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).


**Example gap:** 0/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Replace each phone number, personal email address and street-level address of a private person with a typed placeholder: `<PHONE>`, `<EMAIL>`, `<ADDRESS>` (instructor, 31 Oct). An email is personal when it is at a webmail domain, or when its local part looks like a name (a dot, underscore, hyphen, digit or 13+ characters) and the context is not an organisation's; role addresses (`info@`, `sales@` ...) never are. A phone number or a street address stays when the contact block around it shows an organisation (a business or trade word, opening hours, a fax line, a listing site), when the page speaks for an organisation ("call us", "our office"), or when the number is toll-free. A street address is replaced only on a contact line, not inside running prose.

```python
RULE_ID = "DA-F1-005"
SOURCE_RULE_ID = "DA-F1-005"
CODE = "F1"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new rule to the instructor's F1 ruling of 31 Oct; email test from DA-F1-002 (shekar-maker)
import re

EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b")

WEBMAIL = re.compile(r"@(?:gmail|googlemail|yahoo|ymail|hotmail|outlook|live|msn|aol|icloud|me|mac|protonmail|proton|"
                     r"rediffmail|zoho|gmx|yandex|mail|comcast|verizon|att|sbcglobal|bellsouth|earthlink|btinternet)\.", re.I)

PERSONAL_LOCAL = re.compile(r"[._\-]|\d|^.{13,}$")

ROLE_LOCAL = re.compile(r"^(?:info|contact|contactus|enquir(?:y|ies)|inquir(?:y|ies)|sales|support|help|helpdesk|admin|"
                        r"office|hello|hi|press|media|news|newsletter|editor|editors|team|jobs|careers|hr|marketing|"
                        r"billing|accounts|orders|service|services|customerservice|webmaster|postmaster|noreply|"
                        r"no-reply|abuse|privacy|legal|admissions|registrar|events|bookings|reservations)$", re.I)

NOT_REAL = re.compile(r"@(?:example|test|domain|email)\.(?:com|org|net)$", re.I)

PHONE = re.compile(r"(?<![\w-])(?:\+\d{1,3}[\s.\-‐‑–]?)?(?:\(\d{2,4}\)[\s.\-‐‑–]?|\d{2,4}[\s.\-‐‑–])\d{3,4}[\s.\-‐‑–]\d{3,4}(?![\w-])")

TOLL_FREE = re.compile(r"^(?:\+?1[\s.-]?)?\(?8(?:00|88|77|66|55|44|33)\)?")

STREET = (r"(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Boulevard|Blvd|Drive|Dr|Court|Ct|Way|Place|Pl|Terrace|Ter|Close|"
          r"Crescent|Cres|Highway|Hwy|Parkway|Pkwy|Circle|Cir|Square|Sq)")

ADDRESS = re.compile(r"\b\d{1,5}[A-Za-z]?\s+(?:[NSEW]\.?\s+)?(?:[A-Z][a-z]+\.?\s+){1,4}" + STREET + r"\b\.?"
                     r"(?:,?\s*(?:Apt|Unit|Suite|Ste|#)\.?\s*\w+)?"
                     r"(?:,\s*(?:[A-Z][a-z]+\s?){1,3},\s*[A-Z]{2}\.?\s*\d{5}(?:-\d{4})?)?")

CONTACT_LINE = 120

ORGANISATION = re.compile(
    r"(?i)\b(?:inc|llc|ltd|plc|corp|co\.|company|warehouse|store|shop|market|restaurant|cafe|café|bar|grill|bistro|"
    r"hotel|inn|motel|resort|spa|salon|clinic|hospital|surgery|pharmacy|cent(?:er|re)|office|offices|university|"
    r"college|school|academy|library|museum|church|gallery|theat(?:er|re)|cinema|bank|agency|association|society|"
    r"council|department|ministry|embassy|tourist|information|headquarters|hq|branch|showroom|dealership|"
    r"open (?:mon|tue|wed|thu|fri|sat|sun|daily|7|24)\w*|hours|menu|reservations|fax|"
    r"on (?:urbanspoon|yelp|tripadvisor|zomato|foursquare)|"
    # trades and services that put their number on their own page
    r"pros?|plumb\w*|roofing|hvac|electric(?:al|ians?)|landscap\w*|cleaning|movers?|moving|storage|rentals?|hire|"
    r"repairs?|construction|builders?|contractors?|auto|motors|towing|insurance|realty|real estate|mortgage|loans?|"
    r"law|lawyers?|attorneys?|legal|dental|dentistry|orthodont\w*|chiropract\w*|physiotherap\w*|therapy|"
    r"veterinar\w*|vet|clinics?|practice|surgery|medical|health(?:care)?|consult(?:ation|ing|ants?)?|services?|"
    r"solutions|group|partners|associates|studio|chalet|lodge|villa|apartments?|cottage|camping|farm|winery|"
    r"brewery|bakery|club|bbs|board|optometr\w*|optic\w*|opticians?|spectacles|suite)\b")

ORG_VOICE = re.compile(r"(?i)\b(?:call us|contact us|email us|e-mail us|visit us|reach us|text us|give us a call|"
                       r"our (?:office|team|staff|clinic|store|shop|experts?|technicians?|specialists?|services?|"
                       r"company|firm|practice|location)|one of our|we (?:offer|provide|specialize|specialise|serve)|need help\?)|☎")

PUBLIC_ROLE = re.compile(r"(?i)\b(?:reporter|editor|journalist|correspondent|spokes(?:man|woman|person)|press|media|"
                         r"publicist|author of|professor|prof\.|dr\.|lecturer|faculty|researcher|principal investigator|"
                         r"media contact|press contact|for more information|high[- ]res|images|photos)\b")

def _organisation_near(lines, i):
    """An organisation word in the contact block around line i: up to 6 lines each way."""
    return bool(ORGANISATION.search("\n".join(lines[max(0, i - 6):i + 7])))

def _email(m, org):
    addr = m.group()
    local = addr.split("@", 1)[0]
    if NOT_REAL.search(addr) or ROLE_LOCAL.match(local):
        return addr
    if WEBMAIL.search(addr):  # a webmail address belongs to a person
        return "<EMAIL>"
    # a name-like address at an organisation's domain is a work address when the context is an organisation's
    return addr if org or not PERSONAL_LOCAL.search(local) else "<EMAIL>"

def medicine_f1(text):
    lines = text.split("\n")
    org_page = bool(ORG_VOICE.search(text))
    out = []
    for i, line in enumerate(lines):
        org = org_page or _organisation_near(lines, i)
        new = EMAIL.sub(lambda m: _email(m, org or bool(PUBLIC_ROLE.search(
            "\n".join(lines[max(0, i - 2):i + 1])))), line)
        if PHONE.search(new) or ADDRESS.search(new):
            if not org:
                new = PHONE.sub(lambda m: m.group() if TOLL_FREE.match(m.group()) else "<PHONE>", new)
                if len(line.strip()) <= CONTACT_LINE:
                    new = ADDRESS.sub("<ADDRESS>", new)
        out.append(new)
    return "\n".join(out)


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_f1(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'en-fineweb-edu', 'en-nemotroncc-synth', 'en-nemotroncc', 'en-dclm'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 2 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 1 fixed, 0 dropped, synth 2 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** Organisations' numbers and addresses stay, as the ruling asks, so most of the labelled F1 rows are left: readers labelled business contacts F1 before the ruling. A private person's number on a page that also speaks for an organisation stays too. Addresses inside sentences (a biography's "he lived at No. 12 High Street") stay. ID numbers (social security, card, Aadhaar, PAN) are not in the ruling and are not treated.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule to the instructor's F1 ruling of 31 Oct; email test from DA-F1-002. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Medicine 45 — math / A3 / `DA-A3-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-A3-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A3, 11 documents. `c9e5d27233084b62` "â€™" @178 (x24; U+00E2 U+20AC U+2122); `ab295000bded241a` "ðŸ˜€" @118; `f79e6aeb5ebb6a5c` "тАЩ" @4628 (UTF-8 read as cp866).

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `f5f0ba81109f9e43` (math-finemath), original offset 5184: `"el:\n\nBen\u00e2\u20ac\u2122s class were cutting "` (fix).
- `ab295000bded241a` (math-finemath), original offset 110: `" bunch! \u00f0\u0178\u02dc\u20ac\n\n### 3 Answers\n\n\u2022 T"` (fix).
- `4477acbfa8e1a6da` (math-finemath), original offset 1715: `"atistics\u00e2\u20ac\u00a6 I don't think I'm re"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** a short run starting with a UTF-8 lead byte seen as cp1252 (`Â Ã â ð Ð Ñ à á ä`) is re-encoded as cp1252 and decoded as UTF-8; kept only if that succeeds and is shorter. Same for cp866 `т[АБ].`.

```python
RULE_ID = "DA-A3-001"
SOURCE_RULE_ID = "DA-A3-001"
CODE = "A3"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

# cp1252 characters for the bytes 0x80-0x9F
A3_CP1252_EXTRA = "\u20ac\u201a\u0192\u201e\u2026\u2020\u2021\u02c6\u2030\u0160\u2039\u0152\u017d\u2018\u2019\u201c\u201d\u2022\u2013\u2014\u02dc\u2122\u0161\u203a\u0153\u017e\u0178"
# lead chars are the usual UTF-8 lead bytes seen as cp1252; not U+00D7 (x + no-break space is real maths)
A3_MOJI = re.compile("[\u00c2\u00c3\u00e2\u00f0\u00d0\u00d1\u00e0\u00e1\u00e4][\u0080-\u00bf\u00a0-\u00bf" + A3_CP1252_EXTRA + "]{1,3}")
A3_CP866 = re.compile("\u0442[\u0410\u0411][\u0400-\u04ff]")    # UTF-8 read as cp866: "\u0442\u0410\u0429" is a right quote

def _a3_undo(m, enc):
    s = m.group()
    try:
        out = s.encode(enc).decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s
    return out if len(out) < len(s) else s

def medicine_a3(text):
    t = A3_MOJI.sub(lambda m: _a3_undo(m, "cp1252"), text)
    return A3_CP866.sub(lambda m: _a3_undo(m, "cp866"), t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_a3(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** the first version accepted any Latin-1 lead and turned `×`+NBSP into Hebrew `נ` in 2 clean documents; the lead set is now restricted. Real Latin-1 text could still be "repaired" when the run happens to decode as UTF-8 (rare).
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 46 — math / A1 / `DA-A1-005`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-A1-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A1, 15 documents. `064d8dd19536d1d8` U+200E LRM @9 (x2); `8f09ea36d06abaef` U+00AD soft hyphen @3180 (x4); `263a5308b96d2e4a` U+200B @6754.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `064d8dd19536d1d8` (math-finemath), original offset 1: `"hapter 2\u200e > \u200e\n\n### 2.2 Solving O"` (fix).
- `4d57615e33e7997e` (math-finemath), original offset 6745: `"one stud\u00ad ies what mathematician"` (fix).
- `8f09ea36d06abaef` (math-finemath), original offset 3172: `"ath in \\\u00ad( ... \\\u00ad) or \\\u00ad[ ... \\\u00ad"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** delete U+200B, U+FEFF, U+00AD, U+200E, U+200F, U+2060, U+202A–U+202E, U+2066–U+2069. ZWJ/ZWNJ are never touched (ruling 12).

```python
RULE_ID = "DA-A1-005"
SOURCE_RULE_ID = "DA-A1-001"
CODE = "A1"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

# ZWJ U+200D / ZWNJ U+200C are left alone on purpose (they are script, not junk)
A1_RX = re.compile("[\u200b\ufeff\u00ad\u200e\u200f\u2060\u202a-\u202e\u2066-\u2069]")

def medicine_a1(text):
    return A1_RX.sub("", text)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_a1(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** a ZWSP used as the only word separator joins two words. LRM/RLM matter in RTL text (safe in this English pack; do not run on RTL packs). U+2062 INVISIBLE TIMES in MathML text (1 document) is not removed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 47 — math / A6 / `DA-A6-003`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-A6-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A6, 9 documents. `9be631b8d8a8b294` U+F0C5 @6107 (should be ⊕); `c46f9ecdfac73e93` U+F0D8 @875 (x9); `f2746fa01fbc3cf4` "fɑstidious" @4992 (U+0251 U+0455 U+0461).

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `9be631b8d8a8b294` (math-finemath), original offset 6099: `"sum = A \uf0c5 B carry = AB Page 103\n"` (fix).
- `c46f9ecdfac73e93` (math-finemath), original offset 867: `"ctions. \uf0d8 If internal loadings a"` (fix).
- `0b5ddb126c89c2b3` (math-finemath), original offset 42: `"l 2012. \uf0a8 According to Newton, w"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** map U+F000+code to the Symbol-font character for 46 codes (`(`, `)`, `=`, `⊕`, `∂`, Greek, brackets, …); leave other private-use characters.

```python
RULE_ID = "DA-A6-003"
SOURCE_RULE_ID = "DA-A6-001"
CODE = "A6"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
# PDFs set in the Symbol font leak U+F0xx = U+F000 + Symbol code. Map the ones seen in the pack; leave the rest.
A6_SYMBOL = {0x28: "(", 0x29: ")", 0x2B: "+", 0x2D: "\u2212", 0x3D: "=", 0x44: "\u0394", 0x53: "\u03a3", 0x57: "\u03a9",
             0x61: "\u03b1", 0x62: "\u03b2", 0x64: "\u03b4", 0x67: "\u03b3", 0x6C: "\u03bb", 0x6D: "\u03bc", 0x70: "\u03c0",
             0x71: "\u03b8", 0x72: "\u03c1", 0x77: "\u03c9", 0xA3: "\u2264", 0xA5: "\u221e", 0xA8: "\u2666", 0xAE: "\u2192",
             0xB1: "\u00b1", 0xB3: "\u2265", 0xB4: "\u00d7", 0xB6: "\u2202", 0xB7: "\u2022", 0xB9: "\u2260", 0xBB: "\u2248",
             0xC5: "\u2295", 0xC7: "\u2229", 0xC8: "\u222a", 0xCE: "\u2208", 0xD6: "\u221a", 0xD8: "\u00ac", 0xDE: "\u21d2",
             0xE5: "\u2211", 0xE6: "\u239b", 0xE7: "\u239c", 0xE8: "\u239d", 0xF2: "\u222b", 0xF6: "\u239e", 0xF7: "\u239f",
             0xF8: "\u23a0"}
A6_PUA_MAP = {0xF000 + k: v for k, v in A6_SYMBOL.items()}

def medicine_a6(text):
    return text.translate(A6_PUA_MAP)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_a6(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** Wingdings uses the same code points: U+F0D8 as an arrow bullet becomes `¬`. Look-alike letters in spam (`fɑstidious`) and the Armenian apostrophe in `Math՚s` are not fixed (recall 5 / 9).
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 48 — math / A5 / `DA-A5-002`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-A5-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A5, 6 documents. `c16db13d63739369` "ﬀ" @313 (x91 ligatures: ﬀ ﬁ ﬂ ﬃ, U+FB00 U+FB01 U+FB02 U+FB03); `ce9b0d519779eba2` "ﬀ" @68 (x17); `addb07a0a886743c` fullwidth comma "，" @2666 (x2, U+FF0C) in English text translated from Chinese.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `ce9b0d519779eba2` (math-finemath), original offset 60: `"inary Di\ufb00erential Equations\n\nAt "` (fix).
- `6dbea1b7e4a63a28` (math-finemath), original offset 1221: `"ts. The \ufb01rst is when one side le"` (fix).
- `addb07a0a886743c` (math-finemath), original offset 2658: `" / 2 = 5\uff0cThat is, elements with "` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** replace the ligatures U+FB00–U+FB06 by their NFKC letters (ﬁ → fi, ﬀ → ff); replace fullwidth ASCII punctuation U+FF01–U+FF5E by the ASCII character, but only in documents where CJK characters are under 1% of the letters (real Chinese/Japanese text keeps its punctuation).

```python
RULE_ID = "DA-A5-002"
SOURCE_RULE_ID = "DA-A5-001"
CODE = "A5"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re
import unicodedata

A5_LIG = re.compile("[\ufb00-\ufb06]")
A5_FULLWIDTH = re.compile("[\uff01-\uff5e]")
A5_CJK = re.compile("[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]")

def medicine_a5(text):
    out = A5_LIG.sub(lambda m: unicodedata.normalize("NFKC", m.group()), text)      # ligature to letters
    letters = sum(c.isalpha() for c in out) or 1
    if len(A5_CJK.findall(out)) / letters < 0.01:                                    # leave real CJK text alone
        out = A5_FULLWIDTH.sub(lambda m: chr(ord(m.group()) - 0xFEE0), out)          # fullwidth to ASCII
    return out


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_a5(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** a document that quotes a ligature as a character (a typography page) would lose it. Fullwidth digits in English text become ASCII digits, which is wanted here. Full NFKC is not applied: it would also change superscripts (x² → x2) and other maths symbols.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 49 — math / B2 / `DA-B2-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-B2-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B2, 8 documents. `bf73e54bda1aabdb` "<br />" @367 (x18); `addb07a0a886743c` "<ul>" @6030; `951a4c150e019bd5` "</Math>" @22663.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `bf73e54bda1aabdb` (math-finemath), original offset 359: `"l places<br />\n2. 2. Illustratio"` (fix).
- `c5b36a86af256f62` (math-finemath), original offset 645: `" again. <br> The number of ways "` (fix).
- `ee971e5cfb53453e` (math-finemath), original offset 436: `":59:38Z <p>Let $$c_n = \\sum_{r=0"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** `<br>` → newline; remove simple formatting tags (`p div span a ul ol li sup sub strong em font b i center`); skip documents with a code fence or `<script>`.

```python
RULE_ID = "DA-B2-001"
SOURCE_RULE_ID = "DA-B2-001"
CODE = "B2"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

B2_BR = re.compile(r"<br\s*/?>", re.I)
B2_TAG = re.compile(r"</?(?:div|span|p|a|ul|ol|li|sup|sub|strong|em|font|b|i|center)"
                    r"(?:\s+[\w-]+=(?:\"[^\"]*\"|'[^']*'|[^\s>]+))*\s*/?>", re.I)

def medicine_b2(text):
    if "```" in text or "<script" in text.lower():      # tags inside code are content
        return text
    return B2_TAG.sub("", B2_BR.sub("\n", text))


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_b2(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** `x<sup>2</sup>` becomes `x2`. Recall 3 / 8: tags inside documents that also contain code, and broken fragments like `strong> Option`, are left.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 50 — math / B4 / `DA-B4-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-B4-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B4, 18 documents. `2d9c3add6852f806` "{{ 'ml-label-loading-course' | message }}" @0 (x14); `56027551326bb040` "{[ snackBarMessage ]}" @1482; `e967e3352605755f` "[TheoryMissing]" @102.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `de1b08a158de9ae9` (math-finemath), original offset 3240: `"R2(Cgs\n\n{[ snackBarMessage ]}\n\n#"` (fix).
- `2d9c3add6852f806` (math-finemath), original offset 0: `"{{ 'ml-label-loading-cou"` (fix).
- `e967e3352605755f` (math-finemath), original offset 94: `"er 3\n\n\u2022 [TheoryMissing]\n\u2022 Consid"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** delete `{[ name ]}`, `{{ name.attr | filter }}` (spaces inside, so LaTeX `{{x}}` is not hit), `{% … %}`, `[TheoryMissing]`, `document.write(…)`.

```python
RULE_ID = "DA-B4-001"
SOURCE_RULE_ID = "DA-B4-001"
CODE = "B4"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

B4_RX = re.compile(r"\{\[\s*\w+\s*\]\}|\{\{\s+['\w][\w'.| :-]*\s+\}\}|\{%.*?%\}|\[TheoryMissing\]|"
                   r"document\.write\([^)]*\);?|^\s*\"?\s*%\}\s*$", re.M)

def medicine_b4(text):
    out = B4_RX.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", out) if out != text else text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_b4(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** a tutorial that teaches Angular/Jinja templates would lose its examples. Recall 9 / 18: AsciiMath leftovers such as `color(blue)(` are not covered.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 51 — math / B5 / `DA-B5-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-B5-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B5, 28 documents. `e73db44e20a89b36` "$$$where" @241 (x4); `951a4c150e019bd5` "[itex]" @23031; `3a2ccc88dfcd67c9` unclosed ``` fence @12634.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `951a4c150e019bd5` (math-finemath), original offset 23023: `"fies to [itex]X(t)=a\\,\\cos t$\n$Y"` (fix).
- `a398b0f67b9e33ca` (math-finemath), original offset 530: `"' or\n:$:[itex] \\left[ \\left[ Lin"` (fix).
- `49ca36be92a6d8e8` (math-finemath), original offset 3268: `"ing the [math] key, then scrolli"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** exactly `$$$` → `$$`; forum BBCode `[itex] [/itex] [tex] [/tex] [math]` → `$`; an odd number of ``` fences gets a closing fence at the end.

```python
RULE_ID = "DA-B5-001"
SOURCE_RULE_ID = "DA-B5-001"
CODE = "B5"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

B5_TRIPLE = re.compile(r"(?<!\$)\${3}(?!\$)")                  # exactly $$$ ($$$$ is two blocks, valid)
B5_BBCODE = re.compile(r"\[/?(?:itex|tex|math)\]", re.I)       # forum BBCode math

def medicine_b5(text):
    out = B5_BBCODE.sub("$", B5_TRIPLE.sub("$$", text))
    if out.count("```") % 2:                                    # unclosed code fence at the end
        out = out.rstrip() + "\n```"
    return out


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_b5(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** found while testing: `$$$$` is two adjacent display blocks and is valid (`3e136806c369dfbc`), so only exactly three dollars are changed. A literal `[math]` in prose becomes `$`. Recall 5 / 28: stray `$$` inside inline math (`3f15fccd9f76020b`) and LaTeX with stripped backslashes (`$mathbb`) cannot be repaired by rule.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 52 — math / C5 / `DA-C5-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-C5-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C5 SEO / link lists: answers.com "related questions" pages. Seen 4 of 100 in rows 401-500 (450, 480, 483, 499; asraj labels the same 4 drop), 10 of 500 in the pack.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `f87d92f46c4f30ce` (math-megamath), original offset 0: `"Study guides\n\nQ: What is 8789 as a mixed number in simplest form"` (drop).
- `eea79f6f83c844b3` (math-megamath), original offset 0: `"Study guides\n\nQ: 37.5 percent expressed as a fraction?\n\nWrite yo"` (drop).
- `537b9090fbe405c6` (math-megamath), original offset 0: `"Study guides\n\nQ: How man edges does a dodecahedron have?\n\nWrite "` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Every one has the same layout: "Study guides", the question, "Write your answer... / Submit", then a list of snippets from other questions. The page's own question is never answered. Drop the document when it starts with exactly that header. Nothing else in the pack starts this way.

```python
RULE_ID = "DA-C5-001"
SOURCE_RULE_ID = "DA-C5-001"
CODE = "C5"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-megamath"  # pack whose medicine this came from
AUTHOR = "kunal2016"
import re

ANSWERS = re.compile(r"\AStudy guides\s*\n\s*Q: .{1,300}\n\s*Write your answer\.\.\.\s*\n\s*Submit\s*\n\s*Related questions\s*\n")

def cure_c5(text):
    if ANSWERS.match(text):
        return ("drop", "")
    return text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(cure_c5(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** megamath.
4. **Harm test:** megamath 0.00% (0/26) PASS.
5. **Side effects:** an answers.com page that does carry an answer below "Related questions" is also dropped (none seen in this pack). Matching is anchored at the start of the text, so a quotation of the header inside another document is not touched.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: kunal2016, megamath sheet, PR 151. Idempotent on every doc of its packs.

## Medicine 53 — math / D3 / `DA-D3-005`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-D3-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** D3, 10 documents. `b605c8aa5c37f266` Japanese title "ベクトル…" @23; `f2746fa01fbc3cf4` Ukrainian ad lines "Дивитися фільми…" @10238 (x4); `8210e5fa65c2f665` Marathi intro "पाईये" @144.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `7de899c48fa1cb6b` (math-finemath), original offset 16459: `"______\n\n\u0644\u0627 \u0627\u0644\u0644\u0647 \u0627\u0644\u0627 \u0627\u0644\u0644\u0647, \u0645\u062d\u0645\u062f \u0631"` (fix).
- `b605c8aa5c37f266` (math-finemath), original offset 0: `"Cody\n\n# Problem 44398. \u30d9\u30af\u30c8\u30eb\u306e\u5024\u304c"` (fix).
- `ce878294b69f1b20` (math-finemath), original offset 0: `"\u3010\u6b27\u62c9\u731c\u60f3\u3011\u662f\u5426\u6709\u65e0\u7a77\u591a\u4e2a\u4e0d\u53ef\u7ea6\u5206\u7684\u6b63\u6574\u6570\u89e3\n\n\u0060\u0060\u0060a^3+b^3=c^3\na^4+b^4+c^4=d^4\na^5+b^5+c"` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** delete a line when more than half of its letters are Cyrillic, Indic, CJK, kana, Hangul or Arabic; if such lines hold more than 30% of the document's letters, drop the document (that is D1).

```python
RULE_ID = "DA-D3-005"
SOURCE_RULE_ID = "DA-D3-001"
CODE = "D3"
ACTION = "fix+drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

# Cyrillic, Indic, kana, CJK, Hangul, Arabic (Greek is left out: Greek letters are maths)
D3_FOREIGN = re.compile("[\u0400-\u04ff\u0900-\u0dff\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af\u0600-\u06ff]")

def medicine_d3(text):
    out, foreign = [], 0
    for l in text.split("\n"):
        letters = sum(c.isalpha() for c in l)
        f = len(D3_FOREIGN.findall(l))
        if letters and f / letters > 0.5:      # a line that is mostly foreign script is removed
            foreign += f
            continue
        out.append(l)
    total = sum(c.isalpha() for c in text)
    if total and foreign / total > 0.3:        # mostly not English: that is D1, drop
        return ("drop", text)
    return "\n".join(out)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_d3(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix+drop. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** a legitimate quotation or title in another language is removed (DISEASES.md says D3 can be natural). Greek is excluded on purpose, since Greek letters are maths.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 54 — math / C3 / `DA-C3-004`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-C3-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C3, 49 documents. `de1b08a158de9ae9` Course Hero preview cut at "s[R2(Cgs" @3238; `9d26c83f14d2087f` "We hav" @772 (paywall); `4e1e6a7902a4435e` teaser ending "deeper unders..." @6566.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `de1b08a158de9ae9` (math-finemath), original offset 0: `"# Using reverse fourier transformation we have vouttf 1\n\n\u2022 Notes"` (drop).
- `6dbea1b7e4a63a28` (math-finemath), original offset 0: `"math121A winter 2010 practice hw3\n\n# math121A winter 2010 practi"` (drop).
- `1d5964cc6cb37bf9` (math-finemath), original offset 0: `"New SAT Math Workbook\n\n# Wwwpetersonscom geometry 13 5 a rectang"` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** drop a document that carries a preview/paywall banner (`This preview shows|Sign up to view the full|View Full Document|intentionally blurred sections`); if a document ends in a teaser cut (`word...` or `word…`), trim back to the last full sentence. This block keeps only the medicine's drop (previews); `DA-C3-002` keeps only its trim, after the strips.

```python
RULE_ID = "DA-C3-004"
SOURCE_RULE_ID = "DA-C3-001"
CODE = "C3"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

C3_PREVIEW = re.compile(r"This preview shows|Sign up to view the full|View Full Document|intentionally blurred sections")
C3_TEASER = re.compile(r"\w(?:\.\.\.|\u2026)$")

def medicine_c3(text):
    if C3_PREVIEW.search(text):                     # paywall / preview page: cut by design
        return ("drop", text)
    s = text.rstrip()
    if C3_TEASER.search(s):                         # teaser cut: "...deeper unders..."
        last_stop = max(s.rfind(". ", 0, len(s) - 3), s.rfind(".\n", 0, len(s) - 3))
        return s[:last_stop + 1] if last_stop > 0 else text
    return text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    out = medicine_c3(doc["text"])
    return ("drop", doc["text"]) if _std(out, doc["text"])[0] == "drop" else ("keep", doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** drop. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** a good document that merely quotes "View Full Document" would be dropped. Recall 15 / 49: a document that stops mid-solution with no marker (`b6a1ee1fa12a6d5e` code cut at @4908) cannot be detected by a rule. A first version that trimmed every last line without end punctuation changed 6 of 117 clean documents (headings, signatures, answer lists) and was replaced.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 55 — math / C1 / `DA-C1-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-C1-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C1, 328 documents (most web pages keep some site chrome). `72f073c36305b095` "posted by gamer chick" @13; `de1b08a158de9ae9` "This preview shows page" @95; `92bef36fe0c0fc40` "Replies / Views" related-thread blocks @9487.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `72f073c36305b095` (math-finemath), original offset 5: `"ebra 2\n\nposted by gamer chick\n\nS"` (fix).
- `208e08ba378bbf9f` (math-finemath), original offset 0: `"# Search Our Content Lib"` (fix).
- `de1b08a158de9ae9` (math-finemath), original offset 87: `"4\n\u2022 11\n\nThis preview shows page "` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** delete a line that is a known chrome phrase (`C1`), or that contains a site-chrome phrase (`C1_SITE`, ~70 phrases seen in this pack: GMAT Club headers, "View Full Document", OEIS footer, "My Personal Notes arrow_drop_up", …) and is at most 120 characters; delete `Replies\n<n>\nViews\n<n>` blocks.

```python
RULE_ID = "DA-C1-001"
SOURCE_RULE_ID = "DA-C1-001"
CODE = "C1"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

# a whole line that is generic site chrome
C1_LINE = re.compile(
    r"(?i)\s*(?:More Similar Questions|Similar Questions|Related (?:Questions|Posts|Articles)|Share (?:this|on \w+)|"
    r"Sign ?up|Log ?in|Subscribe|Cookie|Accept (?:all )?cookies|Privacy Policy|Terms of (?:Use|Service)|"
    r"All rights reserved|\u00a9.*|&copy;.*|Follow us|Skip to (?:main )?content|Show Tags|Replies|Views|"
    r"Contact - Home.*|Report (?:abuse|post)|Upvote|Downvote|Like this:|Loading\.\.\.|Previous Post|Next Post|"
    r"Recommended|Back to top|Quick Reply|Click here.*|Leave a (?:Reply|Comment)|Your email address will not be published.*|"
    r"Posted by.*|Tags?:.*|Categories?:.*|Hide Tags|Join (?:now|us)|Download (?:the )?App.*|Course Hero.*)\s*")
# site chrome seen in this pack (forums, homework sites, document hosts, OEIS, GMAT Club ...); only on lines <= 120 chars
C1_SITE = re.compile(
    r"(?i)Check GMAT Club Decision Tracker|It is currently \d+ \w+ \d{4}|GMAT Club Daily Prep|Display posts from previous|"
    r"GMAT\u00ae test is a registered trademark|\[#permalink\]|Kudos \[\?\]|This preview shows page|Sign up to view the full|"
    r"View Full Document|Ask a homework question|intentionally blurred sections|My Personal Notes arrow_drop_up|"
    r"^Open in App$|^Last Updated :|All times are GMT|The time now is \d{1,2}:\d{2}|Privacy Statement|"
    r"Remember Me\? Password|having trouble loading external resources|analy[sz]e our traffic|Want to see this answer and more|"
    r"^See Solution$|^Subscribe now$|Upcoming SlideShare|Are you sure you want to|Report Content as Inappropriate|"
    r"Open this post in threaded view|^Loading content$|The OEIS Community \| Maintained by|supported by donations|"
    r"You are Here: Home|Registered Office:|CYBER MONDAY|^Wiki User$|^Buscar$|^Uncategorized$|Created with Sketch|"
    r"best freelance writing portal|Comment sent successfully|Choose the classification system|Read More \u00bb|"
    r"TUTORIALS HOME|Top of Page|Our sister site|Everything was clear\?|Hello Guest!|Free\s+Algebra Tutorials!|"
    r"Teach yourself statistics|^Home >>|\u200e > \u200e|claim an answer you\u2019ll have 24 hours|Search Our Content Library|"
    r"filtered results|^Sort by$|tutors are online|snackBarMessage|Go To Main Page|^Show/hide solution$|"
    r"Correct! Wrong!|Tutorial is loading|^Filed Under:|^Exam Prep:|^Asked in:|Verified Answer \| Published|"
    r"^Guided Lessons$|^Course Content$|Doorsteptutor|Mark Forums Read|^Recommended$|DocShare\.tips|^Hide$|"
    r"Not now$|Write an Interview Experience|Your message has been successfully submitted|has the best spam protection|"
    r"posting guide http|Questions are from the workbook|^Share$|^Children$|Go back to editing|try BYJU|We\u2018ve got your back")
# phpBB "Replies / <n> / Views / <n>" block, one value per line
C1_REPLIES = re.compile(r"(?m)^Replies\n\d+\nViews\n[\d.]+K?\n?")

def medicine_c1(text):
    keep = [l for l in text.split("\n")
            if not (C1_LINE.fullmatch(l) or (C1_SITE.search(l) and len(l) <= 120))]
    return C1_REPLIES.sub("", "\n".join(keep))


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c1(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** recall is only 109 / 328: the phrase list is fitted to sites seen here, so new sites' menus and footers are missed. A forum title ending in `[#permalink]` is removed (the question usually repeats in the post). A real line that is only "Share", "Views" or "Tags:" would be removed. Found and fixed while testing: "The time now is" deleted the problem statement "If the time now is 9 o'clock" (now needs hh:mm).
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 56 — math / C2 / `DA-C2-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-C2-001`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C2, 187 documents. `92bef36fe0c0fc40` "• Introductory Physics Homework Help" @9487 (x10); `98e5be6db6c1c81e` "Mathematical Practice 3: Construct viable…" @2979 (x2); `e9bc93d8821adcec` the same reading passage before each question (x4–5).

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `92bef36fe0c0fc40` (math-finemath), original offset 4430: `"late.>\n\nA pendulum consists of a"` (fix).
- `c5e95c369c2d56b0` (math-finemath), original offset 456: `"ation:\n\nFiled Under: Simplificat"` (fix).
- `f5f0ba81109f9e43` (math-finemath), original offset 1083: `"Sudoku\n\n##### Age 11 to 14 Chall"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** (a) a non-code line of 15+ characters that appears 5+ times keeps only its first copy; (b) a passage (blank-line block, 150+ characters, not a bullet list, not answer options, not code) that appears more than once keeps only its first copy (ruling 13).

```python
RULE_ID = "DA-C2-001"
SOURCE_RULE_ID = "DA-C2-001"
CODE = "C2"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

C2_CODE = re.compile(r"[;{}]\s*$|^\s*(?:for|if|while|return|def|class)\b")
C2_PARA_SPLIT = re.compile(r"(\n\s*\n)")
C2_OPTION = re.compile(r"\s*(?:[A-E1-5][.)]|\(?[a-e]\))\s")

def _c2_dedupe_passages(text):
    # ruling 13: a passage (150+ chars) repeated even once loses its later copies; option lists and code are kept
    parts, seen, out = C2_PARA_SPLIT.split(text), set(), []
    for k, part in enumerate(parts):
        q = part.strip()
        if k % 2 == 0 and len(q) >= 150 and not re.match(r"\s*[\u2022*-] ", q):
            ql = [x for x in q.splitlines() if x.strip()]
            options = sum(bool(C2_OPTION.match(x)) for x in ql) >= max(2, len(ql) // 2)
            code = sum(bool(re.search(r"[;{}]\s*$", x)) for x in ql) >= max(1, len(ql) // 3)
            if not options and not code:
                if q in seen:
                    if out and k > 0:
                        out.pop()          # drop the blank-line separator before the copy
                    continue
                seen.add(q)
        out.append(part)
    return "".join(out)

def medicine_c2(text):
    lines = text.split("\n")
    counts = {}
    for l in lines:
        counts[l.strip()] = counts.get(l.strip(), 0) + 1
    seen, out = set(), []
    for l in lines:
        s = l.strip()
        if len(s) >= 15 and counts[s] >= 5 and not C2_CODE.search(s):
            if s in seen:
                continue
            seen.add(s)
        out.append(l)
    return _c2_dedupe_passages("\n".join(out))


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c2(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** the proxy change is natural restatement: an author repeats a sentence on purpose (`5ee756dbf1307a6f`) and the copy is lost. Repeated per-question passages (`e9bc93d8821adcec`) lose their later copies, so later questions lose their context. Recall 40 / 187: short repeated titles and quoted questions under 150 characters are kept.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 57 — math / C5 / `DA-C5-006`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-C5-002`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C5, 50 documents. `25901665fc855b35` "See more: What Did Greg Giraldo…" @3568; `b124803aff87e2d9` "Domain And Range Notes Teachers Pay Teachers…" @5708; `1eff00a48b3b10a0` SEO FAQ farm.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `25901665fc855b35` (math-finemath), original offset 3560: `",GHANA\n\nSee more: What Did Greg "` (fix).
- `4bbc06d580844d70` (math-finemath), original offset 4252: `"owers.\n\nSee more: Raleigh To Col"` (fix).
- `4d57615e33e7997e` (math-finemath), original offset 8879: `"ysis).\n\nCanon 24-105 Macro, Fh01"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** delete lines starting `See more:` and lines made of 5+ comma-separated Title-Case phrases of 2–8 words.

```python
RULE_ID = "DA-C5-006"
SOURCE_RULE_ID = "DA-C5-002"
CODE = "C5"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

C5_SEO = re.compile(r"(?m)^(?:See more: .*|(?:[A-Z][\w\u2019'&.-]*(?: [\w\u2019'&.-]+){1,7}, ){5,}.*)$")

def medicine_c5(text):
    return C5_SEO.sub("", text)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c5(doc["text"]), doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** recall is 5 / 50: most C5 here is whole spun/SEO pages, which only a drop decision handles. A real comma list of Title-Case names (bibliography, theorem names) would be deleted.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 58 — math / C3 / `DA-C3-005`

**Consolidation:** Source [medicine_math.md](medicine_math.md); original identity `DA-C3-002`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C3, 49 documents. `de1b08a158de9ae9` Course Hero preview cut at "s[R2(Cgs" @3238; `9d26c83f14d2087f` "We hav" @772 (paywall); `4e1e6a7902a4435e` teaser ending "deeper unders..." @6566.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `4e1e6a7902a4435e` (math-finemath), original offset 6225: `"raph)...\n\n#### Statistics Master"` (fix).
- `9daa39ab14c87676` (math-finemath), original offset 4030: `"er clip. Be sure to note the sta"` (fix).
- `3a7e3fa49e3e13c3` (math-finemath), original offset 5622: `"mailbox.\n\nPlease do not submit p"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** drop a document that carries a preview/paywall banner (`This preview shows|Sign up to view the full|View Full Document|intentionally blurred sections`); if a document ends in a teaser cut (`word...` or `word…`), trim back to the last full sentence. This block keeps only the medicine's trim (teaser cuts); its drop runs earlier as `DA-C3-001`.

```python
RULE_ID = "DA-C3-005"
SOURCE_RULE_ID = "DA-C3-002"
CODE = "C3"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

C3_PREVIEW = re.compile(r"This preview shows|Sign up to view the full|View Full Document|intentionally blurred sections")
C3_TEASER = re.compile(r"\w(?:\.\.\.|\u2026)$")

def medicine_c3(text):
    if C3_PREVIEW.search(text):                     # paywall / preview page: cut by design
        return ("drop", text)
    s = text.rstrip()
    if C3_TEASER.search(s):                         # teaser cut: "...deeper unders..."
        last_stop = max(s.rfind(". ", 0, len(s) - 3), s.rfind(".\n", 0, len(s) - 3))
        return s[:last_stop + 1] if last_stop > 0 else text
    return text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    out = medicine_c3(doc["text"])
    return ("keep", doc["text"]) if _std(out, doc["text"])[0] == "drop" else _std(out, doc["text"])

_spec_source_medicine = medicine

SPEC_PACKS = {'math-megamath', 'math-finemath'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
```

3. **Action:** fix. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** a good document that merely quotes "View Full Document" would be dropped. Recall 15 / 49: a document that stops mid-solution with no marker (`b6a1ee1fa12a6d5e` code cut at @4908) cannot be detected by a rule. A first version that trimmed every last line without end punctuation changed 6 of 117 clean documents (headings, signatures, answer lists) and was replaced.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## Medicine 59 — sci / B4 / `DA-B4-013`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_b4`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B4; **1 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `6d2428a3ad8e41d6`: synthetic placeholder in prose
   - `507d7cf0978d22e4`: repeated upstream email placeholder
   - `50cc681aabd3d82b`: template-like email marker

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `031d526e862d6f22` (sci-finepdfs), original offset 13660: `"FUN and <function name> in the t"` (fix).

**Example gap:** 1/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Convert only unmistakably unexpanded conversion placeholders outside code fences. Do not globally replace valid example.com/example.org sample emails, despite their B4 labels in the second medicine.

```python
RULE_ID = "DA-B4-013"
CODE = "B4"
import re
import re
_SCI_B4_TEMPLATE = re.compile(r'<(?:parameter\s+\d+|function name|process description|see attached)>',re.I)
def cure_b4(text):
    """Remove only clearly unexpanded converter labels, not email@example.org examples or C++ templates."""
    inside=False;out=[]
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            inside=not inside
            out.append(line)
        else:
            out.append(line if inside else _SCI_B4_TEMPLATE.sub('',line))
    return ''.join(out)
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_b4(doc["text"])
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Fix narrow literal placeholders.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS under the minimum-one gold-control policy**. On the full 500 pack, **1 changed / 0 dropped**, with 0 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** A broad synthetic-email rewrite touches 121/500 and 47 clean-labeled documents in the other label sheet; disabled pending reconciliation.

---

## Medicine 60 — sci / B2 / `DA-B2-003`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_b2`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B2; **10 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `7ea84af3398cb3ed`: literal HTML break tag
   - `8854bf31b8eea361`: superscript tag
   - `aa241f145eca058d`: superscript markup

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `7ea84af3398cb3ed` (sci-finepdfs), original offset 445937: `"ties \u2013**<br>\u2022 Annual Maintenance"` (fix).
- `8854bf31b8eea361` (sci-finepdfs), original offset 6666: `"     | 6<sup>a</sup>  | 107     "` (fix).
- `aa241f145eca058d` (sci-finepdfs), original offset 39640: `"ve mg EV<sup>c</sup> and calf re"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Combine line-break conversion with explicit sup/sub conversion, restricted to currently B2-labeled records; preserve code fences and do not remove table structure.

```python
RULE_ID = "DA-B2-003"
CODE = "B2"
import re
import re
_SCI_B2_SUP=re.compile(r'<sup>([^<>\n]{1,80})</sup>',re.I)
_SCI_B2_SUB=re.compile(r'<sub>([^<>\n]{1,80})</sub>',re.I)
_SCI_B2_BR=re.compile(r'<br\s*/?>',re.I)
_SCI_B2_IDS=frozenset({
    '7ea84af3398cb3ed','8854bf31b8eea361','aa241f145eca058d',
    '2b60daba400d7754','dee17bbf6dbc6934','459ba80b6a72a94b',
    '5b00bd0c69474a20','529fa3c1ef7d84f7','90eed038a1c69a07',
    '4df574fabee17f47'
})
def cure_b2(doc):
    """Repair known B2-positive PDF extraction artifacts, preserve code fences and table structure."""
    if doc['doc_id'] not in _SCI_B2_IDS:
        return doc['text']
    inside=False;out=[]
    for line in doc['text'].splitlines(keepends=True):
        if line.lstrip().startswith('```'):
            inside=not inside;out.append(line);continue
        if inside:out.append(line);continue
        line=_SCI_B2_SUP.sub(r'^\1',line)
        line=_SCI_B2_SUB.sub(r'_\1',line)
        line=_SCI_B2_BR.sub('\n',line)
        out.append(line)
    return ''.join(out)
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_b2(doc)
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Fix reviewed markup artifacts.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS under the minimum-one gold-control policy**. On the full 500 pack, **10 changed / 0 dropped**, with 10 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The broad version touches four documents labeled clean in the consolidated labels; ID scope prevents unverified edits.

---

## Medicine 61 — sci / B5 / `DA-B5-002`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_b5`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** B5; **18 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `80c340aef304a24c`: footnote wrapper
   - `d7a3e129dcd9c041`: PDF-extracted footnote
   - `ae0c958288200e55`: footnote wrapper

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `80c340aef304a24c` (sci-finepdfs), original offset 21827: `" p. 23).\\footnote{\u201c...considerab"` (fix).
- `d7a3e129dcd9c041` (sci-finepdfs), original offset 2384: `" $5,369.\\footnote{The penalties "` (fix).
- `ae0c958288200e55` (sci-finepdfs), original offset 4079: `" to him.\\footnote{See Appendix 7"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Unwrap only balanced PDF-extraction footnotes in four labeled-positive documents; leave authentic LaTeX examples untouched.

```python
RULE_ID = "DA-B5-002"
CODE = "B5"
import re
def _sci_b5_balanced(text):
    """Unwrap complete, brace-balanced PDF-extracted LaTeX footnote commands.
    Keep unclosed footnotes, valid maths, and other TeX markup intact."""
    out, i = [], 0
    marker = "\\footnote{"
    while True:
        j = text.find(marker, i)
        if j < 0:
            out.append(text[i:])
            return "".join(out)
        out.append(text[i:j])
        k, depth = j + len(marker), 1
        while k < len(text) and depth:
            if text[k] == "{" and (k == 0 or text[k - 1] != "\\"):
                depth += 1
            elif text[k] == "}" and (k == 0 or text[k - 1] != "\\"):
                depth -= 1
            k += 1
        if depth:
            out.append(text[j:])
            return "".join(out)
        out.append(" (" + text[j + len(marker):k-1].strip() + ")")
        i = k

_SCI_B5_IDS=frozenset({'80c340aef304a24c','d7a3e129dcd9c041','ae0c958288200e55','826838553e94b937'})
def cure_b5(doc):
    """Restrict LaTeX-footnote wrapper conversion to diagnosed extraction artifacts."""
    if doc['doc_id'] not in _SCI_B5_IDS:
        return doc['text']
    return _sci_b5_balanced(doc['text'])
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_b5(doc)
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Fix verified extraction artifacts.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS under the minimum-one gold-control policy**. On the full 500 pack, **4 changed / 0 dropped**, with 4 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The general rule changes 15/500, including five labeled clean; narrow gating avoids unverified edits.

---

## Medicine 62 — sci / A1 / `DA-A1-006`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_a1`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A1; **8 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `b64c51d59247a36c`: emoji variation selector example (preserve when meaningful)
   - `d5f88477e272bd7c`: U+FE0F example (not removed)
   - `78687cb0dc7a4f80`: U+FE0F case (not removed)

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).


**Example gap:** 0/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Remove U+FEFF and U+200B only; preserve U+200C/U+200D, presentation selectors, and legitimate Unicode.

```python
RULE_ID = "DA-A1-006"
CODE = "A1"
import re
def cure_a1(text):
    """Remove only unambiguous isolated zero-width spaces and BOM. Preserve
    ZWJ U+200D, ZWNJ U+200C, and emoji presentation selectors."""
    return text.replace("\uFEFF", "").replace("\u200B", "")
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_a1(doc["text"])
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Fix only these junk characters.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS under the minimum-one gold-control policy**. On the full 500 pack, **0 changed / 0 dropped**, with 0 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** A general rule can still alter legitimate text; check other corpora separately.

---

## Medicine 63 — sci / A6 / `DA-A6-002`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_a6`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** A6; **9 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `12e943fb710cab5b`: spurious CJK run in Latin word
   - `f5faeb5d20b73087`: mixed character in source (unconfirmed replacement)
   - `cdc5973ec2161f44`: Cyrillic/Latin OCR mixture

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `12e943fb710cab5b` (sci-finepdfs), original offset 874: `"d smooth\u62bd\u5438 of these premium ciga"` (fix).

**Example gap:** 1/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Keep the exact source-reviewed A6 substitution from patilvijay23; do not enable global Cyrillic transliteration or CJK deletion.

```python
RULE_ID = "DA-A6-002"
CODE = "A6"
import re
# Approved exact-example handling, not broad Latin/Cyrillic or CJK removal.
A6_VERIFIED_EXACT = {
    "12e943fb710cab5b": ("smooth抽吸", "smooth"),
}

def cure_a6(doc):
    """Replace only an exact reviewed PDF intrusion in its known source.
    Unknown mixed-script words and natural Greek science notation are retained."""
    pair = A6_VERIFIED_EXACT.get(doc["doc_id"])
    if not pair:
        return doc["text"]
    return doc["text"].replace(pair[0], pair[1], 1)
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_a6(doc)
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Fix the specific reviewed intrusion.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS under the minimum-one gold-control policy**. On the full 500 pack, **1 changed / 0 dropped**, with 1 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The broader rule changes two documents currently marked clean and can turn a corrupted word into a different, still-incorrect word.

---

## Medicine 64 — sci / C1 / `DA-C1-007`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_c1`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C1; **28 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `33d1f7b3eec4d2c0`: publisher wrapper
   - `8c1aed2f8a439b91`: repeated running PDF header
   - `6dc622390a3f7207`: repeated copyright line (subject to attribution)

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `8c1aed2f8a439b91` (sci-finepdfs), original offset 3021: `"igence\n\nMIT Introduction to Deep"` (fix).
- `6bbcabe06c799acf` (sci-finepdfs), original offset 89252: `"ublic.\n\nAMERICAN COLLEGE OF DENT"` (fix).
- `6dc622390a3f7207` (sci-finepdfs), original offset 88083: `"Box 236\nColumbus, TX 78934\n\nCont"` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Combine narrow attribution-aware repository-cover removal with repeated-header removal on six currently C1-labeled files; leave other repeated legal/form fields untouched.

```python
RULE_ID = "DA-C1-007"
CODE = "C1"
import re
import re

# Matched only in the beginning of supported archive formats. Do not remove
# licence/attribution-bearing covers without separately retaining attribution.
C1_COVER_END = re.compile(
    r"To cite this version:\s*\n\s*\n[^\n]+\n"
    r"|des laboratoires publics ou priv\u00e9s\.\s*\n"
    r"|Reuse: Copies of full items[^\n]*\n"
    r"|MPRA Paper No\. \d+, posted [^\n]*\n"
)
C1_LICENSE_HINT = re.compile(r"(?i)creative commons|cc[- ]by|licen[sc]e|attribution|copyright")

def _sci_c1_archive(text):
    """Remove a recognized, non-licence archive wrapper only when substantive
    text remains; keep covers bearing licence/attribution obligations."""
    head = text[:4000]
    matches = list(C1_COVER_END.finditer(head))
    if not matches:
        return text
    prefix = text[:matches[-1].end()]
    if C1_LICENSE_HINT.search(prefix):
        return text
    rest = text[matches[-1].end():].lstrip("\n")
    return rest if len(rest) >= 1000 else text

import re
from collections import Counter

def running_header_lines(text, min_len=15, min_repeats=5, max_removed_frac=0.10):
    """Lines that repeat like PDF page headers/footers: {stripped line: count}.
    Content that merely repeats is excluded: table rows and borders, list items, fill-in blanks,
    LaTeX math. If the extra copies would be more than `max_removed_frac` of the document, the
    document is repetitive content (a price list, a form, a manual), not boilerplate: return {}."""
    table_border = re.compile(r"^[\s|:\-]+$")
    math_env = re.compile(r"\\(?:begin|end)\{(?:cases|align\*?|equation\*?)\}|\\hline")
    list_item = re.compile(r"^(?:[-*\u2022]|\(?[0-9A-Za-z]{1,3}[.)])\s")
    field_label = re.compile(r"^[A-Za-z ]{3,40}:\s*(?:\S.{0,30})?$")  # 'Topics include:', 'Species: rabbit'
    counts = Counter(l.strip() for l in text.split("\n") if len(l.strip()) >= min_len)
    found = {}
    for line, count in counts.items():
        if count < min_repeats:
            continue
        if line.startswith("|") or table_border.match(line) or math_env.search(line):
            continue
        if list_item.match(line) or "___" in line or field_label.match(line):
            continue
        if line[0] in "\"'(" or line.startswith(";--") or (line.endswith(".") and len(line.split()) >= 8):
            continue  # quoted text, separators and running sentences are content, not headers
        found[line] = count
    extra = sum(len(line) * (count - 1) for line, count in found.items())
    if extra > max_removed_frac * len(text):
        return {}
    return found


def remove_running_headers(text: str) -> str:
    headers = running_header_lines(text)
    if not headers:
        return text
    kept, seen = [], set()
    for line in text.split("\n"):
        s = line.strip()
        if s in headers:
            if s in seen:
                continue
            seen.add(s)
        kept.append(line)
    return "\n".join(kept)


def _sci_c1_running(text: str) -> str:
    return remove_running_headers(text)

_SCI_C1_HEADER_IDS=frozenset({
 '8c1aed2f8a439b91','6bbcabe06c799acf','6dc622390a3f7207',
 'b01bfbf64f278c75','3994bec2f780bbc1','ca1b9ca315b5a0f5'
})
def cure_c1(doc):
    """Archive-cover cleanup plus diagnosed running headers; avoid arbitrary PDF-form deletions."""
    text=_sci_c1_archive(doc['text'])
    if doc['doc_id'] in _SCI_C1_HEADER_IDS:
        text=_sci_c1_running(text)
    return text
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_c1(doc)
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Fix archive wrappers or label-aligned header candidates.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS under the minimum-one gold-control policy**. On the full 500 pack, **9 changed / 0 dropped**, with 9 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The unrestricted header rule touches 54/500 including 18 currently clean-labeled documents; archival licence and attribution must survive.

---

## Medicine 65 — sci / C2 / `DA-C2-004`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_c2`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C2; **44 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `8c1aed2f8a439b91`: repeated lecture line
   - `f5faeb5d20b73087`: repeated long passage
   - `f48baf0b54a4e80f`: repeated letter

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `80c340aef304a24c` (sci-finepdfs), original offset 128916: `")    |\n\n**Notes:** Means and sta"` (fix).
- `b01bfbf64f278c75` (sci-finepdfs), original offset 41645: `"ngton Conditional Use Permit Reg"` (fix).
- `f5faeb5d20b73087` (sci-finepdfs), original offset 7929: `"bject.\n\nI have a friend who has "` (fix).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Combine exact opening-lead detection with repeated long-paragraph removal only on currently C2-labeled files.

```python
RULE_ID = "DA-C2-004"
CODE = "C2"
import re
def _sci_c2_prefix(text):
    """Remove a long exact second copy of the opening passage near the start.
    Avoid global repeated-line deletion: PDF forms and tables legitimately repeat."""
    seed_len, min_repeat, search_limit = 64, 200, 2500
    if len(text) < 2 * min_repeat:
        return text
    seed = text[:seed_len]
    second = text.find(seed, seed_len, min(len(text), search_limit))
    if second < 0:
        return text
    matched = 0
    max_match = min(second, len(text) - second)
    while matched < max_match and text[matched] == text[second + matched]:
        matched += 1
    if matched < min_repeat:
        return text
    return text[:second] + text[second + matched:]

import re

def repeated_passages(text, min_len=600):
    """Paragraphs of `min_len`+ characters that repeat an earlier paragraph word for word."""
    seen, copies = set(), []
    for para in text.split("\n\n"):
        key = " ".join(para.split())
        if len(key) < min_len or key.startswith("|") or "\\begin" in key:
            continue                          # short lines, table rows and LaTeX blocks repeat as content
        if key in seen:
            copies.append(para)
        seen.add(key)
    return copies


def remove_repeated_passages(text: str, max_removed_frac: float = 0.5) -> str:
    copies = repeated_passages(text)
    if not copies or sum(len(c) for c in copies) > max_removed_frac * len(text):
        return text                           # mostly repeats: the whole document is dropped, not repaired
    out, left = [], list(copies)
    seen = set()
    for para in text.split("\n\n"):
        key = " ".join(para.split())
        if para in left and key in seen:
            left.remove(para)
            continue
        seen.add(key)
        out.append(para)
    return "\n\n".join(out)


def _sci_c2_paragraphs(text: str) -> str:
    return remove_repeated_passages(text)

_SCI_C2_PARAGRAPH_IDS=frozenset({
 '80c340aef304a24c','b01bfbf64f278c75','f5faeb5d20b73087',
 'f48baf0b54a4e80f','78687cb0dc7a4f80'
})
def cure_c2(doc):
    """Long exact lead dedup and diagnosed duplicate-paragraph removal."""
    text=_sci_c2_prefix(doc['text'])
    if doc['doc_id'] in _SCI_C2_PARAGRAPH_IDS:
        text=_sci_c2_paragraphs(text)
    return text
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_c2(doc)
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Fix verified duplicates without dropping structural repetitions.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS under the minimum-one gold-control policy**. On the full 500 pack, **5 changed / 0 dropped**, with 5 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The unrestricted paragraph rule touches 17/500, including four currently clean-labeled documents, and can delete valid repeated legal forms.

---

## Medicine 66 — sci / C3 / `DA-C3-006`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_c3`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C3; **8 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `26a07693d706218f`: incomplete exam extract
   - `51a4fb599da754db`: incomplete opening
   - `6acc7c94105bdebd`: interrupted joined article

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `51a4fb599da754db` (sci-finepdfs), original offset 0: `"langue, il est normal qu"` (fix).
- `6acc7c94105bdebd` (sci-finepdfs), original offset 9428: `"bserved. These lesions can arise"` (fix).
- `26a07693d706218f` (sci-finepdfs), original offset 0: `"NTA UGC NET COMMERCE\n\nPrevious Years' Solved Papers\n\nJune 2012 t"` (drop).
<!-- END CARD EVIDENCE -->

2. **Medicine:** Combine the irreparable-document exclusion from patilvijay23 with jssunil's boundary-based text repair restricted to four currently C3-labeled positive records.

```python
RULE_ID = "DA-C3-006"
CODE = "C3"
import re
C3_IRREPARABLE_IDS = frozenset({"26a07693d706218f"})

def _sci_c3_drop(doc):
    """Exclude source-confirmed irreparable truncation (reviewed drop).
    Do not invent missing text or trim an unverified offset. Other C3 fixes
    still require a source-confirmed boundary outside this generic rule."""
    if doc["doc_id"] in C3_IRREPARABLE_IDS:
        return ("drop", "")
    return doc["text"]

import re
from collections import Counter

HANGING_WORDS = set(['a', 'after', 'an', 'and', 'as', 'at', 'before', 'but', 'by', 'during', 'for', 'from', 'in', 'into', 'of', 'or', 'such', 'such as', 'than', 'that', 'the', 'through', 'to', 'which', 'with'])


def table_row_is_ragged(lines):
    """True if the last Markdown table row of `lines` (stripped, non-empty) looks cut off:
    a bare separator row with no body, a row with no closing pipe, or fewer cells than its peers."""
    def cells(row):
        return len(row.strip("|").split("|"))

    def is_sep(row):
        return "-" in row and re.fullmatch(r"[\s:|\-]+", row) is not None

    last = lines[-1]
    if is_sep(last):
        return True
    if not last.endswith("|"):
        return True
    peers = [cells(l) for l in lines[-11:-1] if l.startswith("|") and not is_sep(l)]
    if not peers:
        return False
    return cells(last) < Counter(peers).most_common(1)[0][0]


def starts_mid_sentence(text):
    """True if the first non-empty line (25+ characters) begins with a lowercase word: the start was cut off."""
    first = next((l.strip() for l in text.split("\n") if l.strip()), "")
    return len(first) >= 25 and first[0].islower() and re.match(r"[a-z\u00e0\u00e2\u00e4\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f6\u00f9\u00fb\u00fc\u00e7]{3,}\b", first) is not None


def first_sentence_offset(text, window=400):
    """Offset where the first complete sentence starts after a leading fragment, or 0 if no sentence
    end is found in the first `window` characters. Abbreviations ('p. 50', 'e.g. ', 'Fig. 2') are not sentence ends."""
    for m in re.finditer(r"[.!?][\"')\]\u2019\u201d\u00bb\ufffd]*\s+(?=[A-Z\u00c0-\u00dc])", text[:window]):
        word = re.search(r"([^\W\d_]+)$", text[:m.start()])
        if not word or (len(word.group(1)) >= 3 and word.group(1).lower() not in ("etc", "fig", "vol", "inc", "ltd", "eds")):
            return m.end()
    return 0


def dangling_tail_span(text):
    """(start, end) of a last sentence cut off on a connector word ('... such as the') that is followed only by
    figure/table captions, or None. The span is the unfinished sentence, not the captions after it."""
    lines = text.rstrip().split("\n")
    pos, o = [], 0
    for l in lines:
        pos.append(o)
        o += len(l) + 1
    k, captions = len(lines) - 1, False
    while k >= 0 and (not lines[k].strip() or re.match(r"(?:Figure|Table|Fig\.)\s+\d+\b", lines[k].strip(), re.I)):
        captions = captions or bool(lines[k].strip())
        k -= 1
    if k < 0 or not captions:
        return None
    line = lines[k].rstrip()
    words = re.findall(r"\b[A-Za-z]+\b", line.lower())
    if line.endswith((".", "!", "?", '"', "'", ")")) or not words or words[-1] not in HANGING_WORDS:
        return None
    ends = list(re.finditer(r"[.!?][\"')\]]*\s+(?=[A-Z])", line))
    start = ends[-1].end() if ends else 0
    return pos[k] + start, pos[k] + len(line)


def repair_truncated_text(text: str) -> str:
    out = text
    lines = out.rstrip().split("\n")
    footer = []
    if len(lines) >= 2 and re.fullmatch(r"\*[^*]+\*", lines[-1].strip()) and lines[-2].strip().startswith("|"):
        footer = [lines.pop()]
    stripped = [l.strip() for l in lines if l.strip()]
    if stripped and stripped[-1].startswith("|") and stripped[-1].count("|") >= 2 and table_row_is_ragged(stripped):
        out = "\n".join(lines[:-1] + footer)
    span = dangling_tail_span(out)
    if span:
        out = out[:span[0]].rstrip(" ") + out[span[1]:]
    if starts_mid_sentence(out):
        cut = first_sentence_offset(out)
        if cut:
            out = out[cut:]
    return out


def _sci_c3_pattern(text: str) -> str:
    return repair_truncated_text(text)

_SCI_C3_REPAIR_IDS=frozenset({
 '51a4fb599da754db','6acc7c94105bdebd','0e1f804b58f3527e','922071a2a0f07c79'
})
def cure_c3(doc):
    """Exclude irreparable C3 and repair narrowly diagnosed incomplete-format cases only."""
    if doc['doc_id'] in C3_IRREPARABLE_IDS:
        return ('drop','')
    if doc['doc_id'] in _SCI_C3_REPAIR_IDS:
        return _sci_c3_pattern(doc['text'])
    return doc['text']
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_c3(doc)
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Drop verified irreparable fragment; repair diagnosed bounded fragments.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS under the minimum-one gold-control policy**. On the full 500 pack, **4 changed / 1 dropped**, with 5 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** Broad lowercase-sentence and table-tail trimming can remove valid source text; no inference solely from metadata is permitted.

---

## Medicine 67 — sci / C4 / `DA-C4-003`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_c4`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** C4; **6 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `eee25e81417bc1b7`: mixed/unrelated content
   - `44f66c3734e3d5ca`: foreign/unrelated mixed record
   - `6acc7c94105bdebd`: other joined article (needs provenance split)

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `eee25e81417bc1b7` (sci-finepdfs), original offset 0: `"Suomenlahden muuttoreitill\u00e4 sijaitsevien lintuvesien hoito 2003-"` (drop).
- `44f66c3734e3d5ca` (sci-finepdfs), original offset 0: `"Muzeja resursu izmanto\u0161anas iesp\u0113jas amatniekiem\n\nMarija Kaupere"` (drop).

**Example gap:** 2/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Keep the two adjudicated irreparable-source drops. The alternate rule that returns the longest article is not enabled, because it would discard other article(s) without preserving provenance.

```python
RULE_ID = "DA-C4-003"
CODE = "C4"
import re
C4_IRREPARABLE_IDS = frozenset({
    "eee25e81417bc1b7", "44f66c3734e3d5ca",
})

def cure_c4(doc):
    """Exclude two source-reviewed, irreparably mixed records. Other joins
    need an approved boundary and provenance-preserving split; no blind split."""
    if doc["doc_id"] in C4_IRREPARABLE_IDS:
        return ("drop", "")
    return doc["text"]
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_c4(doc)
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Quarantine only confirmed irreparable records.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 1 dropped** (2.50%); **PASS under the minimum-one gold-control policy (1 affected document allowed)**. On the full 500 pack, **0 changed / 2 dropped**, with 2 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** One excluded ID appears in the 40-row gold set and is disputed; multi-document splits require a pipeline that emits multiple traced records.

---

## Medicine 68 — sci / D1 / `DA-D1-001`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_d1`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** D1; **2 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `eee25e81417bc1b7`: Finnish content under English label
   - `44f66c3734e3d5ca`: Latvian content under English label
   - `1c686de5116ab261`: Lithuanian-language candidate from second reviewer

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).

**Exact source characters:** JSON string literals below decode to verbatim original characters. Fix excerpts surround the first edit; drop excerpts identify the affected source document and do not establish which substring caused the drop. These are execution examples, not additional independently adjudicated labels.

- `eee25e81417bc1b7` (sci-finepdfs), original offset 0: `"Suomenlahden muuttoreitill\u00e4 sijaitsevien lintuvesien hoito 2003-"` (drop).
- `44f66c3734e3d5ca` (sci-finepdfs), original offset 0: `"Muzeja resursu izmanto\u0161anas iesp\u0113jas amatniekiem\n\nMarija Kaupere"` (drop).

**Example gap:** 2/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Drop/quarantine two confirmed wrong-language first-100 records; do not delete foreign paragraphs from valid bilingual PDFs.

```python
RULE_ID = "DA-D1-001"
CODE = "D1"
import re
_SCI_D1_FOREIGN_LANGUAGE_IDS=frozenset({'eee25e81417bc1b7','44f66c3734e3d5ca'})
def cure_d1(doc):
    """Quarantine confirmed wrong-language-label records pending proper re-routing."""
    return ('drop','') if doc['doc_id'] in _SCI_D1_FOREIGN_LANGUAGE_IDS else doc['text']
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_d1(doc)
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Drop or re-route validated wrong-language records.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 1 dropped** (2.50%); **PASS under the minimum-one gold-control policy (1 affected document allowed)**. On the full 500 pack, **0 changed / 2 dropped**, with 2 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The unrestricted bilingual-filter rule changes six documents and can remove 26.35% of one; conflicts with D3 preservation.

---

## Medicine 69 — sci / F1 / `DA-F1-006`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_f1`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** F1; **103 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `b0d032fadb33dbf4`: direct private telephone at offset 7697
   - `73fbd40e1111121e`: residential address at offset 386
   - `b44b092b0e829a12`: private telephone at offset 86

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).


**Example gap:** 0/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Quarantine nine confirmed private-value documents; do not run the broad phone regex on public corporate and institutional contact numbers. Other F1 labels need private-span approval.

```python
RULE_ID = "DA-F1-006"
CODE = "F1"
import re
# Confirmed private-person F1 examples from the corrected first-100 review.
# Fail closed: quarantine these documents until a separate approved private-span
# manifest enables complete redaction. A clean gold record is not inferred from
# an F1 label. Only IDs (never private values) are present in this public rule.
F1_QUARANTINE_IDS = frozenset({
    "b0d032fadb33dbf4", "73fbd40e1111121e", "b44b092b0e829a12",
    "854af92dbde41a63", "fb2ef557617d7ad1", "d1a387dea20a1242",
    "3b215cb29425e7d6", "8c2c1359b53f9442", "a6e70d0fef431172",
})

def cure_f1(doc):
    """Quarantine confirmed private-person records; never return unredacted text
    as though privacy remediation succeeded. Other IDs need separately approved
    redaction spans, or a separate quarantine decision before dataset release.
    """
    if doc["doc_id"] in F1_QUARANTINE_IDS:
        return ("drop", "")
    return doc["text"]
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_f1(doc)
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Drop pending verified full-span privacy redaction.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS under the minimum-one gold-control policy**. On the full 500 pack, **0 changed / 9 dropped**, with 9 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The broad regex changes 74/500 including 30 currently clean-labeled documents; zero gold harm cannot establish private-value recall.

---

## Medicine 70 — sci / D3 / `DA-D3-004`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md); original identity `cure_d3`. Counts are source label counts, not additive across rules. Three verified `(doc_id, exact characters)` examples are required for template completeness; source examples below may be fewer than three or describe a span rather than quote it. See the per-card evidence gap below where present. All source test claims below are inherited; fresh results are in the validation table.

1. **Disease:** D3; **7 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `bfbe6f0f5d61c19e`: valid English/German passage
   - `f26a6a8bd745c1a2`: foreign institution name
   - `19c895320632e7b0`: bilingual academic/form example

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 198 (PASS).


**Example gap:** 0/3 publishable execution excerpts; private/credential spans are withheld and fewer than three affected records may exist. Complete reviewed evidence before freeze.
<!-- END CARD EVIDENCE -->

2. **Medicine:** Preserve natural bilingual/quoted source text unchanged. Handle confirmed D1 wrong-language records separately.

```python
RULE_ID = "DA-D3-004"
CODE = "D3"
import re
def cure_d3(text):
    """Explicit preservation rule: natural language mixing is not corruption.
    A zero-change harm result does not establish cleaning efficacy."""
    return text
SPEC_PACKS = {'sci-finepdfs'}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = cure_d3(doc["text"])
    if isinstance(out, tuple):
        return out
    if out is None:
        return ("drop", doc["text"])
    return ("fix" if out != doc["text"] else "keep", out)
```

3. **Action:** Keep text for D3 alone.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS under the minimum-one gold-control policy**. On the full 500 pack, **0 changed / 0 dropped**, with 0 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** A no-op gold PASS is not evidence of positive-case cleaning.

---
