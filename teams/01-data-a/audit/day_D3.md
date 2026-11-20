# Cap1 audit: issues to fix

This file lists the problems found while auditing the Cap1 packs, as of 2026-11-17.

For each pack, about 10 docs were read side by side: the text before cleaning (`Cap1-packs/`) and after cleaning (`tokenizer_sample_v0_clean/train/`). Each doc was labelled in `audit_labels/<pack>_<part>.csv` as `clean` (no problem) or `fix` (something is wrong), with a disease code and a note where one was given. Disease codes follow `era-v5-lab/diagnosis/DISEASES.md`.

Docs labelled `clean` are left out. What remains is every doc that needs attention: 71 docs from 29 label files. All 71 are marked `fix`.

The issues fall into three groups. Two are real damage or leftovers in the text (visarga, licence headers). The third is docs that cleaning removed, where the label does not yet say whether removing them was right.

## Summary

| Issue | Docs |
|---|---:|
| Visarga ః replaced with `:` (G4) | 6 |
| Licence header at the top (E4) | 9 |
| Dropped by cleaning (no cleaned version) | 56 |
| **Total** | **71** |

Most of the list (56 of 71) is dropped docs. The visarga issue is the smallest group in the sample, but it is the most serious, because the same change hits thousands of docs across the full pack (see below).

## Visarga ః replaced with `:` (G4) (6)

**What it is.** In Telugu text, cleaning replaced the visarga ః (U+0C03) with an ASCII colon `:` (U+003A). The visarga is part of the word, not punctuation, so the word changes. A tokenizer trained on this text learns the colon as part of Telugu words. This is damage from cleaning: G4, over-normalised.

**How big it is.** All 6 docs are in ind-te-sangraha-s. Checking that whole pack found 3,464 visargas swapped for a colon, and 15,098 left alone, so the swap only happens in some contexts. Smaller numbers of the same swap appear in ind-te-sangraha-v (16) and the Hindi packs ind-hi-fw2, ind-hi-hplt and ind-hi-indiccorp (73 together).

**What to do.** The current `spec_v1/clean.py` excludes every visarga/colon conversion (TSAI ruling, 5 November), so the cleaned output was probably made with an earlier version. Re-cleaning these packs with the current `clean.py` should fix it. Check that the visarga count in each doc stays the same before and after cleaning.

| Pack | doc_id | Verdict |
|---|---|---|
| ind-te-sangraha-s / Part_1 | `f4fbbfb4fced3fd3` | fix |
| ind-te-sangraha-s / Part_1 | `7a7f76d343369290` | fix |
| ind-te-sangraha-s / Part_1 | `63c9fc20d6b0eb40` | fix |
| ind-te-sangraha-s / Part_1 | `af19aa1a64c71111` | fix |
| ind-te-sangraha-s / Part_1 | `27e1bff4db96d0b2` | fix |
| ind-te-sangraha-s / Part_1 | `3ec84d7adeaf07a9` | fix |

## Licence header at the top (E4) (9)

**What it is.** The source file still starts with a licence block after cleaning. The same licence text repeats across thousands of files, so the model spends training on boilerplate instead of code. This is disease E4, repeated licence headers.

**Where.** Code packs only: cpp, java, js-ts, python and rust. `clean.py` has E4 rules for these packs, but these headers got through. Either the header format is not one the rules match, or the output was made with an earlier version.

**What to do.** Compare the header in these docs with the patterns of the E4 rules in `clean.py` and widen the rule where it misses. Two of these rows have no E4 code in the label file; add it.

| Pack | doc_id | Verdict |
|---|---|---|
| code-cpp / Part_1 | `c5d0947a47aa6f3c` | fix |
| code-cpp / Part_1 | `5a1aafe479d99e5b` | fix |
| code-cpp / Part_1 | `38783d4714af32a5` | fix |
| code-cpp / Part_2 | `4a7dd5edbbd424b3` | fix |
| code-java / Part_1 | `be6d4be4e458d124` | fix |
| code-js-ts / Part_1 | `3a8f6f9b6b188062` | fix |
| code-python / Part_2 | `b51ea6bccd71d209` | fix |
| code-rust / Part_1 | `f3550045b5e8d207` | fix |
| code-rust / Part_1 | `56fa57d7083be296` | fix |

## Dropped by cleaning (no cleaned version) (56)

**What it is.** Cleaning removed these docs completely, so the viewer has nothing to show next to the original. That is why their notes say "No Matching doc_id". They are marked `fix`, but no reason is written down. So it is not yet recorded whether dropping them was right or wrong.

**Where.** Across code, English, Indic and math packs. The biggest groups are en-nemotroncc (11), code-go (10), ind-te-fw2 (6) and ind-te-sangraha-v (6).

**What to do.** Decide what `fix` means for a dropped doc and apply it to every row in this table.
- If the drop was wrong (a good doc was removed), keep `fix` and add a note on what was good about it. For Indic docs this is G3, Indic dropped by an English rule.
- If the drop was right, change the verdict to `drop`.

To find out which rule removed a doc, run the current `clean.py` on it. Rules that drop on short lines or line length (C5 headline lists, E1 generated code) are the first to check.

| Pack | doc_id | Verdict |
|---|---|---|
| code-cpp / Part_1 | `40456bdc4432955e` | fix |
| code-go / Part_1 | `9c743b93f0458461` | fix |
| code-go / Part_1 | `545a867b548509dc` | fix |
| code-go / Part_1 | `764578ceac3deba5` | fix |
| code-go / Part_1 | `bcc67b626494a02c` | fix |
| code-go / Part_2 | `c85c2a285dfc8ab0` | fix |
| code-go / Part_2 | `f2b67dcbdaf9237c` | fix |
| code-go / Part_2 | `1662f27536504ddd` | fix |
| code-go / Part_2 | `b663ea600ebd6009` | fix |
| code-go / Part_2 | `aeb863ba677348d2` | fix |
| code-go / Part_2 | `3dde1872c474745d` | fix |
| code-js-ts / Part_1 | `76601a86cf8accee` | fix |
| code-js-ts / Part_2 | `be0eb84a4e965db7` | fix |
| code-python / Part_1 | `72a5a69f8d64fd2a` | fix |
| code-python / Part_1 | `879901159d451bb2` | fix |
| code-python / Part_2 | `e30aafe28b1c5ed9` | fix |
| code-python / Part_2 | `0d24d161fdea1c27` | fix |
| code-python / Part_2 | `f006685e9f42ea08` | fix |
| code-rust / Part_1 | `b8fdde6f382aaafd` | fix |
| en-dclm / Part_1 | `d7818c10380a5026` | fix |
| en-dclm / Part_1 | `fadea98410fa8ca2` | fix |
| en-dclm / Part_1 | `b86c2383830279bb` | fix |
| en-dclm / Part_2 | `6939b53dba7b7954` | fix |
| en-fineweb-edu / Part_1 | `e45798a41ffbc9a2` | fix |
| en-fineweb-edu / Part_1 | `0e8ffd1fb8fb0ad7` | fix |
| en-fineweb-edu / Part_1 | `dec9f5f7041b27f3` | fix |
| en-fineweb-edu / Part_1 | `3ad0b20895d54344` | fix |
| en-fineweb-edu / Part_2 | `7bd3c06c9f78ad8a` | fix |
| en-fineweb-edu / Part_2 | `e53209fdeb4c5c16` | fix |
| en-nemotroncc-synth / Part_1 | `4874a9c840d47276` | fix |
| en-nemotroncc / Part_1 | `5fc6ebc3d8c98c45` | fix |
| en-nemotroncc / Part_1 | `89a7e46458683bc7` | fix |
| en-nemotroncc / Part_1 | `d27f5ef67c8b49fb` | fix |
| en-nemotroncc / Part_1 | `bcebaea7f66d1ea8` | fix |
| en-nemotroncc / Part_1 | `d711896d88e00074` | fix |
| en-nemotroncc / Part_1 | `cb464155e945f3e5` | fix |
| en-nemotroncc / Part_2 | `c64a8520993b7e63` | fix |
| en-nemotroncc / Part_2 | `54d0a4af6ccec85f` | fix |
| en-nemotroncc / Part_2 | `8902bb932d2904e4` | fix |
| en-nemotroncc / Part_2 | `cad4428b2b048d40` | fix |
| en-nemotroncc / Part_2 | `b3bf0af5595be04d` | fix |
| ind-hi-indiccorp / Part_1 | `e20f601e84248141` | fix |
| ind-hi-indiccorp / Part_1 | `07ba8d9f599c324d` | fix |
| ind-te-fw2 / Part_1 | `1e9a487e649bb5a0` | fix |
| ind-te-fw2 / Part_1 | `485b12ad43a958fe` | fix |
| ind-te-fw2 / Part_1 | `0464c3de3f87e31f` | fix |
| ind-te-fw2 / Part_1 | `0a1f54bde5070d5e` | fix |
| ind-te-fw2 / Part_1 | `a96399aa4ef3b802` | fix |
| ind-te-sangraha-s / Part_1 | `ccbf820e232eaa69` | fix |
| ind-te-sangraha-v / Part_1 | `969c8ca6ebc8a573` | fix |
| ind-te-sangraha-v / Part_1 | `ca949d32f7bc33dd` | fix |
| ind-te-sangraha-v / Part_1 | `f0d9b745d8e4a6f3` | fix |
| ind-te-sangraha-v / Part_1 | `222b20d27357942b` | fix |
| ind-te-sangraha-v / Part_1 | `40df311496a357ed` | fix |
| ind-te-sangraha-v / Part_1 | `57ca091d4d08cebc` | fix |
| math-finemath / Part_1 | `3a8ffc03c53f9182` | fix |

---

## Supplement: Gujarati FW2 and Marathi Sangraha-v

Week 3, D3 (17 Nov 2026). Reviewer: `patilvijay23`.

This supplements the earlier audit above with the reviewer's manual findings for two packs previously awaiting language review. It records 10 documents per pack. Marathi FW2 is outside this report and remains pending.

### Inputs and method

- Raw input: the local tokenizer sample supplied for this audit.
- Output under review: decoded text from the corresponding frozen-p1536 tokenizer_samplev0 shards, compared with raw text by `doc_id` in the side-by-side viewer.
- Shards: `ind-gu-fw2-train-000000` and `ind-mr-sangraha-v-train-000000`.
- Disease definitions: [DISEASES.md](../../../diagnosis/DISEASES.md).

The tables transcribe the reviewer's observations. This report does not claim an independent rerun of decoding, hashes or cleaner rules. Input file hashes, decoded-output paths, viewer revision and sample-selection method were not recorded in the supplied notes and should accompany the final audit evidence. Offsets and occurrence counts are as reported in the viewer; their coordinate basis has not been independently checked.

The older `tokenizer_sample_v0_clean` copy must not be substituted for shard-decoded output: [#576](https://github.com/theschoolofai/era-v5-lab/pull/576) found visarga damage in that older copy which was absent from the p1536 shards.

### Summary

| Pack | Reviewed | Unchanged | Valid changes | Residual issues | No issue reported |
|---|---:|---:|---:|---:|---:|
| `ind-gu-fw2` | 10 | 10 | 0 | 5 | 5 |
| `ind-mr-sangraha-v` | 10 | 5 | 5 | 2 | 8 |
| **Total** | **20** | **15** | **5** | **7** | **13** |

No harmful transformation was reported in these 20 documents. This is a small manual sample, not a whole-pack quality estimate or a spec v1.1 acceptance test.

| Residual disease | Affected documents | Interpretation |
|---|---:|---|
| A6: wrong or mixed script | 4 | Reviewer-reported character issues; exact characters/code points still need to be attached. |
| C1: boilerplate | 3 | Two Gujarati documents and one Marathi document retain boilerplate. |
| C5: keyword lists / SEO spam | 1 | One Gujarati document is dominated by keyword and promotional material. |

Disease counts overlap: `94ecf8811dedff0b` has A6 and C1; `588e25b8563af4bc` has C5 and C1. There are seven distinct affected documents.

### Gujarati: `ind-gu-fw2`

All 10 reviewed documents were unchanged. Five have residual issues. `fix` below means the retained output needs attention; the proposed remedy for the SEO-dominated document is a drop, subject to rule review.

| doc_id | Observed output | Audit verdict | Diseases | Evidence / note |
|---|---|---|---|---|
| `94ecf8811dedff0b` | Unchanged | fix | A6;C1 | A6 at offset 4381, 4 occurrences; C1 at offset 4312. Exact character and boilerplate evidence pending. |
| `c9ef612450630b40` | Unchanged | No issue reported | — | No residual issue reported. |
| `674541ca413a06f3` | Unchanged | No issue reported | — | No residual issue reported. |
| `ae2dbded43e8fc7c` | Unchanged | fix | C1 | Boilerplate at offset 87; exact evidence pending. |
| `875e98e15c7a6db0` | Unchanged | fix | A6 | Character issue at offset 298; exact character/code point pending. |
| `a1ffd8e51cf1f02a` | Unchanged | fix | A6 | Character issue at offset 364, 5 occurrences; exact character/code point pending. |
| `c533c8a92da1f0ae` | Unchanged | No issue reported | — | No residual issue reported. |
| `588e25b8563af4bc` | Unchanged | fix; recommend drop | C5;C1 | Repeated VIP full-form search phrases, a tag list and website/social promotion dominate the document. |
| `815625e34d4899a8` | Unchanged | No issue reported | — | No residual issue reported. |
| `c52f5264a10f060e` | Unchanged | No issue reported | — | No residual issue reported. |

#### SEO-dominated document: `588e25b8563af4bc`

- **C5:** the section headed “Tags for VIP Full Form” repeats variants of the same search query rather than adding substantive content.
- **C1:** the website-description section and “Also Visit our Socials” are promotional boilerplate.
- **Proposed action:** drop if a reviewed document-quality rule supports it. There is a short meaningful definition of VIP, but the reviewer judges the document's overall value too low relative to its SEO and promotional content. Removing boilerplate and retaining that definition is an alternative to assess during rule review.
- **Not established:** A6. Ordinary English words and the acronym VIP alongside Gujarati are not sufficient evidence of wrong-script characters.

### Marathi: `ind-mr-sangraha-v`

Five documents changed and the reviewer judged all five changes correct. Of the five unchanged documents, two retain issues.

| doc_id | Observed output | Audit verdict | Diseases | Evidence / note |
|---|---|---|---|---|
| `44d74a34615c8985` | Unchanged | No issue reported | — | No residual issue reported. |
| `6b962bed444a10cb` | Unchanged | fix | C1 | Offset 1319: `टॅग्स :प्रीती झिंटाPreity Zintaशेअर :`; retained tag/share boilerplate. |
| `81e9021dbd5618f9` | Unchanged | No issue reported | — | No residual issue reported. |
| `a793b8e393ed7376` | Changed correctly | Acceptable change | — | `करणाºया` → `करणाऱ्या`. |
| `04c57e4e65e9e936` | Changed correctly | Acceptable changes | — | Two variations of the preceding character correction; exact pairs not supplied. |
| `54600ee0f4bd755f` | Unchanged | fix | A6 | Character issue at offset 222, 16 occurrences; exact character/code point pending. |
| `9d32f5191f18cdbd` | Changed correctly | Acceptable change | — | `प्रमाणीकरण ासह` → `प्रमाणीकरणासह`. |
| `165d1cfbae9b6acb` | Changed correctly | Acceptable change | — | `येणाºया` → `येणाऱ्या`. |
| `a5db82fda38c6c8c` | Unchanged | No issue reported | — | No residual issue reported. |
| `9782478013baa7a1` | Changed correctly | Acceptable change | — | `दुसºयाच` → `दुसऱ्याच`. |

These are observations of the final decoded text. Without intermediate evidence, the report does not attribute each valid transformation specifically to cleaning or tokenizer normalization.

### Follow-up

1. Attach the input identities and viewer revision, confirm the displayed output is the decoded p1536 shard text, and export the corresponding label CSVs for consolidation with Narasimha. Do not overwrite existing labels.
2. For the four reported A6 documents, record the exact characters, code points/hex and context. Confirm each is a wrong-script character rather than legitimate mixed-language content before proposing a replacement.
3. For C1, attach the Gujarati snippets and confirm the Marathi tag/share block boundaries. Propose narrowly scoped removal that preserves article text.
4. Review the C5/C1 document's drop recommendation against the frozen spec. A sample-v0 residual finding alone does not prove a spec v1.1 implementation defect or authorize a new rule.
5. Reproduce confirmed findings with the current cleaner and map them to an existing rule or a proposed future-spec change. Any new medicine needs the language gold-set harm test before adoption; no medicine or harm test is supplied here.
6. Complete the separate 10-document `ind-mr-fw2` audit and arrange the required second-reader review of 10% of the documents (2 of these 20).

This report includes no document payloads, signed download links or local decoded artifacts. The short snippets above provide evidence for the reported findings.
