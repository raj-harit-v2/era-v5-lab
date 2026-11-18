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
