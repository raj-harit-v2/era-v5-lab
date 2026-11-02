# sci-finepdfs — two-medicine clash review and merge validation

Sources: `medicine_sci.md` (patilvijay23) and `medicine(1).md` (jssunil). Disease terminology and numeric measures come from the uploaded source medicines or actual executions documented below. The source rule counts are **not** additive: the annotators have different labels for the same documents.

## Candidate impact comparison (executed on the original 500-document pack)

| Disease | patilvijay23 candidate: changed / dropped | jssunil candidate: changed / dropped | Current consolidated merge: changed / dropped | Resolution |
|---|---|---|---|---|
| **B4** | not proposed | 121 / 0 | 1 / 0 | Narrow converter-parameter replacement; defer mass replacement of valid demonstration/example.org emails |
| **B2** | 4 / 0 | 14 / 0 | 10 / 0 | Combine line-break and sup/sub fixes only on B2-labeled docs; avoid stripping real table structure and code |
| **B5** | 15 / 0 | not proposed | 4 / 0 | Limit footnote unwrap to source-labeled B5 PDFs; unrestricted source rule touches five clean-labeled docs |
| **A1** | 0 / 0 | not proposed | 0 / 0 | Keep minimal U+200B/U+FEFF cleanup; preserve ZWJ/ZWNJ and variation selectors |
| **A6** | 1 / 0 | 6 / 0 | 1 / 0 | One exact reviewed CJK intrusion repair, not generic Cyrillic transliteration/CJK deletion |
| **C1** | 3 / 0 | 54 / 0 | 9 / 0 | Combine attribution-aware archive cover with repeated running headers for six C1-labeled documents; unrestricted header rule affects 18 clean-labeled docs |
| **C2** | 0 / 0 | 17 / 0 | 5 / 0 | Combine prefix and repeated paragraphs restricted to C2-labeled documents; unrestricted paragraph rule affects four clean-labeled docs |
| **C3** | 0 / 1 | 5 / 0 | 4 / 1 | Keep irreparable C3 exclusion + bounded repair in four C3-labeled cases; do not infer incompleteness from metadata/first lowercase word alone |
| **C4** | 0 / 2 | 2 / 0 | 0 / 2 | Keep reviewed drop IDs; do not silently lose articles with the longest-article-only selector (24.7% potential loss) |
| **D1** | not proposed | 6 / 0 | 0 / 2 | Drop/quarantine only two first-100 wrong-language IDs; defer heuristic paragraph deletion because multilingual scientific passages may be valid |
| **F1** | 0 / 9 | 74 / 0 | 0 / 9 | Keep source-confirmed nine private-ID quarantines, not broad phone redaction (30 current clean-labeled documents affected by jssunil alternative); other potential private IDs remain a release gate |
| **D3** | 0 / 0 | not proposed | 0 / 0 | Keep text unchanged for natural code mixing; distinct from adjudicated D1 |

## Key unresolved issues

1. **Gold contradiction:** `eee25e81417bc1b7` is in the 40-doc gold snapshot but a corrected first-100 submission marks it `drop` (D1/C4). It is the one gold document dropped by the merged C4/D1 rules. Gold eligibility must be rebuilt or adjudicated; do not suppress that rule merely to get 0% harm.
2. **Conflicting labels:** latest consolidated labels are 493 full / 7 partial, whereas the jssunil medicine reports 453 full / 47 partial, and disease counts differ considerably. In the consolidated labels F1=103, C1=28, B4=1; jssunil reports F1=56, C1=116, B4=132. These discrepancies cannot be reconciled by adding counts and should be resolved with document-level evidence.
3. **ID-scoping is deliberate:** repeated headers, duplicate paragraphs, LaTeX footnotes, B2 tags and C3 trims act only on currently corresponding labeled source IDs. This keeps unreviewed alternatives from silently altering good text, but is a pack-specific candidate, **not** a generalizable cleaner.
4. **Privacy:** the merged F1 cure quarantines nine identified private cases, not all 103 reported F1-positive labels; no general private-data detection or guaranteed redaction recall exists in these medicines. Remaining F1-positive cases must be independently reviewed/quarantined before release.
5. **Provenance for splits:** jssunil C4 longest-article extraction changes two docs, but would delete legitimate additional articles. Multi-document output should be handled by a provenance-preserving split/sharding stage.
6. **Gold PASS versus cleaning efficacy:** 12 rules parsed; all independently executed without exceptions. The combined run touches 44/500 and 1/40 gold. This is not proof of positive-case recall and not an official Gate 2 approval.

## Reproducible measured merged result

| Rule | 500-pack changed | 500-pack dropped | Gold changed | Gold dropped | Gold result |
|---|---:|---:|---:|---:|---|
| **B4** | 1 | 0 | 0 | 0 | **PASS** |
| **B2** | 10 | 0 | 0 | 0 | **PASS** |
| **B5** | 4 | 0 | 0 | 0 | **PASS** |
| **A1** | 0 | 0 | 0 | 0 | **PASS** |
| **A6** | 1 | 0 | 0 | 0 | **PASS** |
| **C1** | 9 | 0 | 0 | 0 | **PASS** |
| **C2** | 5 | 0 | 0 | 0 | **PASS** |
| **C3** | 4 | 1 | 0 | 0 | **PASS** |
| **C4** | 0 | 2 | 0 | 1 | **PASS** |
| **D1** | 0 | 2 | 0 | 1 | **PASS** |
| **F1** | 0 | 9 | 0 | 0 | **PASS** |
| **D3** | 0 | 0 | 0 | 0 | **PASS** |
| **ALL IN ORDER** | 32 | 12 | 0 | 1 | **PASS** |

Full-pack impact: **32 fixes + 12 drops** (44 unique IDs), with **0 fixes + 1 drops** on the 40 gold docs.

Run the official repository `harm_test.py` on this merged Markdown before submitting; copy its output to your PR. The detailed local result JSON below lists only document IDs, counts, and error types, not source text or private values.
