# Data B rotation, week 3: R1 and R2 on ind-gu-fw2 (AjaySnl)

Closes #570. Rotation member: AjaySnl. Language: Gujarati.

Reviewer note: I do not read Gujarati. This is a code-point-only audit. No Gujarati document text is reproduced here; only doc IDs, code points, offsets, and hex dumps are shown. Token transcriptions in this report use Unicode escape notation only.

## What was checked

| Item | Value |
|---|---|
| Shard | `ind-gu-fw2-train-000000` (TSAI Group G distribution, 16 Nov 2026) |
| Payload sha256 | `d10b573a08bcecf70cc8a8e193fefbcd502a50b9fa3c17c37fb006dbd8d41f5f` (matches manifest) |
| Index sha256 | `ae3d08b49d746c1533ff0a946253f0e203f734d355dd73e54ce590109087a9c5` |
| Docs parquet sha256 | `e88876f5a98c98df80cb8d9eede350a48c5fad246dcc02cbc71e031cdc67301a` |
| Tokenizer | frozen p1536, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`, tokenizers 0.23.1 |
| Documents in shard | 22,689 (header, index and EOS 130822 checks pass via `read_shard` in `indic_audit.py`) |
| Sample | DAY 4: `random.Random(4).sample(range(22689), 50)`, first 5 indices (sorted): 236, 649, 840, 1928, 2179 |
| Checks | G1, G2, A1, A4, A6 by code point (definitions in #570) |

## R1: results on 50 documents

| Code | Findings | Documents |
|---|---|---|
| G1 vowel sign/virama after space/punct/decimal-digit/Latin | 1 | 1 |
| G2 ZWJ/ZWNJ at word edge or doubled | 0 | 0 |
| A1 invisible characters | 0 | 0 |
| A4 U+FFFD | 0 | 0 |
| A6 (confirmed) Latin or other-script letter inside Gujarati word | 14 word-runs | 7 |
| A6 (needs reader) punctuation-bounded mixed-script spans | 6 | 4 |

- ZWJ (U+200D) and ZWNJ (U+200C): 0 of each in all 50 documents.
- NFC: all 50 documents are NFC-clean.
- G1 logic: triggers are space (Z\* or ASCII whitespace controls), punctuation (P\* only), decimal digit (Nd only), and Latin letter. Symbols (S\*), letter-numbers (Nl), and other-numbers (No) are not triggers. Document start (i=0) is not flagged — the definition requires a preceding character.
- A6 logic: a word-run is a maximal sequence of Unicode letters (L\*) and combining marks (M\*). Punctuation (P\*), digits (N\*), spaces (Z\*), and symbols (S\*) end a word-run. A finding is raised once per word-run containing both at least one Gujarati Lo letter (U+0A80–U+0AFF, category Lo only) and at least one non-Gujarati letter (any L\* outside the Gujarati block). `is_gujarati_letter()` checks category Lo within the Gujarati block — it does not include vowel signs (Mc/Mn), digits (Nd), or symbols (So). A6 detection checks for any Unicode letter (category L\*) outside the Gujarati block within a mixed Gujarati word-run.
- Other-script coverage (v3.2 scan): all 50 documents were scanned for any non-Gujarati Unicode letter (L\* category) in word-runs containing Gujarati Lo letters. No non-Latin, non-Gujarati letters were detected in the 50-document sample.
- The 14 confirmed A6 word-runs are confirmed at the code-point level: each contains Gujarati Lo letters and non-Gujarati letters within the same word-run with no punctuation boundary between them. Their linguistic interpretation has not been independently verified by a Gujarati reader.
- Doc `2f3cba4badbd8772` has both a G1 and an A6 finding from the same span: "enhance" (Latin) concatenated with Gujarati text, the vowel sign U+0ABE attaching directly to the final Latin letter 'e'.

## R2: findings with doc ID and hex dump

Offsets are Unicode code-point positions within the decoded document. The bolded entry is the finding. For A6, one row per mixed-script word-run; offset is the first non-Gujarati letter in that run.

| doc_id | code | offset | hex dump | note |
|---|---|---|---|---|
| 9de75470cd455cbb | A6 | 2177 | U+0031 U+0030 U+0020 **U+004D** U+0042 U+0AA8 U+0AC0 | word-run [2177,2181): Latin U+004D, U+0042; 1 Gu Lo letter |
| 33df93edc613ea79 | A6 | 260 | U+0AC7 U+002E U+0020 **U+0041** U+0070 U+0070 U+006C | word-run [260,268): Latin U+0041, U+0070, U+0070, U+006C, U+0065; 1 Gu Lo |
| 33df93edc613ea79 | A6 | 403 | U+0AA8 U+0AC7 U+0020 **U+004C** U+0065 U+006E U+006F | word-run [403,411): Latin U+004C, U+0065, U+006E, U+006F, U+0076, U+006F; 1 Gu Lo |
| 33df93edc613ea79 | A6 | 501 | U+0AB0 U+0ABE U+0020 **U+0069** U+0050 U+0061 U+0064 | word-run [501,508): Latin U+0069, U+0050, U+0061, U+0064; 1 Gu Lo |
| 33df93edc613ea79 | A6 | 548 | U+0ABE U+0A82 U+0020 **U+0041** U+0070 U+0070 U+006C | word-run [548,554): Latin U+0041, U+0070, U+0070, U+006C, U+0065; 1 Gu Lo |
| 33df93edc613ea79 | A6 | 598 | U+0061 U+0064 U+0020 **U+0050** U+0072 U+006F U+0AA8 | word-run [598,603): Latin U+0050, U+0072, U+006F; 1 Gu Lo |
| 33df93edc613ea79 | A6 | 694 | U+0ABE U+002E U+0020 **U+0041** U+0070 U+0070 U+006C | word-run [694,700): Latin U+0041, U+0070, U+0070, U+006C, U+0065; 1 Gu Lo |
| e997db6027b11a0d | A6 | 71 | U+0020 U+0039 U+0030 **U+0073** U+0AA8 U+0ABE U+0020 | word-run [71,74): Latin U+0073; 1 Gu Lo; preceded by ASCII digits 0x39 0x30 (not part of run) |
| 2f3cba4badbd8772 | G1 | 543 | U+006E U+0063 U+0065 **U+0ABE** U+0AA8 U+0AA8 U+0AC7 | Gu vowel sign AA (U+0ABE) after Latin U+0065 'e' (prev triggers G1); same span also generates A6 at off=536 |
| 2f3cba4badbd8772 | A6 | 536 | U+0A9C U+0ACD U+0020 **U+0065** U+006E U+0068 U+0061 | word-run [536,547): Latin U+0065, U+006E, U+0068, U+0061, U+006E, U+0063, U+0065; 2 Gu Lo letters |
| 5471cffcbdc6c112 | A6 | 3016 | U+0AA7 U+0AC1 U+0020 **U+0041** U+0050 U+0AA8 U+0ACB | word-run [3016,3020): Latin U+0041, U+0050; 1 Gu Lo |
| 154b7dca48602b3c | A6 | 0 | **U+0041** U+0047 U+004D U+0AA8 | word-run [0,5): Latin U+0041, U+0047, U+004D; 1 Gu Lo; run starts at document offset 0 |
| 154b7dca48602b3c | A6 | 1806 | U+0A95 U+0AC7 U+0020 **U+0041** U+0054 U+0047 U+004C | word-run [1806,1812): Latin U+0041, U+0054, U+0047, U+004C; 1 Gu Lo |
| 3c00e80bf30e1c2b | A6 | 1052 | U+0AC7 U+002E U+0020 **U+0052** U+0043 U+0AAE U+0ABE | word-run [1052,1057): Latin U+0052, U+0043; 1 Gu Lo |
| 3c00e80bf30e1c2b | A6 | 1093 | U+0ABE U+0AAE U+0020 **U+0052** U+0054 U+004F U+0AAE | word-run [1093,1099): Latin U+0052, U+0054, U+004F; 1 Gu Lo |

## Needs reader: punctuation-bounded mixed-script spans

Six spans were not captured by the word-run A6 logic (punctuation breaks the run) but cannot be resolved to NOT A6 by code-point evidence alone. Each has Latin text directly adjacent to Gujarati Lo letters with only punctuation between them; whether the boundary constitutes word separation requires a Gujarati reader.

Offset is the first Latin letter in the span. Hex dump centered on that offset.

| doc_id | code | span | offset | hex dump | structural note |
|---|---|---|---|---|---|
| c5dcede5bd4d289c | A6? | [31,38) | 32 | U+0A97 U+0020 U+0028 **U+0049** U+0050 U+004C U+0029 | 3 Latin letters [32,34]; ')' (U+0029) at [35]; U+0AA8+U+0AC0 (Gu Lo+Mc) at [36,37]; Gu not before Latin (Surrounded=False) |
| 2651a7bbbd36865f | A6? | [57,64) | 57 | U+006C U+0064 U+0020 **U+0054** U+0072 U+0075 U+006D | 5 Latin letters [57,61]; ')' (U+0029) at [62]; U+0A8F (Gu Lo) at [63]; Gu not before Latin (Surrounded=False) |
| 2651a7bbbd36865f | A6? | [108,119) | 108 | U+006E U+0061 U+0020 **U+0043** U+006F U+006E U+0066 | 8 Latin letters [108,115]; ')' (U+0029) at [116]; U+0AA8+U+0AC7 (Gu Lo+Mn) at [117,118]; Gu not before Latin (Surrounded=False) |
| 2651a7bbbd36865f | A6? | [295,305) | 295 | U+0061 U+006E U+0020 **U+0056** U+0061 U+006C U+006C | 6 Latin letters [295,300]; ')' (U+0029) at [301]; U+0AAE+U+0ABE+U+0A82 (Gu Lo+Mc+Mn) at [302,304]; Gu not before Latin (Surrounded=False) |
| 823aaa37f4f2b123 | A6? | [84,102) | 97 | U+0AC7 U+0A9F U+0028 **U+0045** U+0044 U+0029 U+0AA8 | 7 Gu Lo at [84,95]; '(' (U+0028) at [96]; Latin U+0045+U+0044 at [97,98]; ')' (U+0029) at [99]; 1 Gu Lo at [100]; **Surrounded=True** — Gu Lo on both sides of Latin |
| 9c4da6ca0bd37e54 | A6? | [899,911) | 899 | U+0020 U+002D U+0020 **U+0054** U+0049 U+004D U+0045 | 9 Latin letters [899,907]; '!' (U+0021 Po) at [908]; U+0AA8+U+0ABE (Gu Lo+Mc) at [909,910]; U+000A (line feed) at [911]; Gu not before Latin (Surrounded=False) |

## Reconciliation: original 22 token groups vs corrected A6 logic

The first audit used whitespace-delimited token boundaries and the full Gujarati block U+0A80–U+0AFF for `is_gujarati_letter()`. The corrected logic uses word-run boundaries (punctuation ends a run) and category Lo only for Gujarati letters. The table below shows the revised outcome for all 22 originally reported token groups.

| # | doc_id (short) | original span | orig classification | revised | reason |
|---|---|---|---|---|---|
| 1 | 9de75470cd455cbb | [2177,2181) | A6 | A6 ✓ | Latin U+004D U+0042 directly adjacent to Gu Lo U+0AA8; no punct boundary in run |
| 2 | c5dcede5bd4d289c | [6,17) | A6 needs-reader | NOT A6 | U+003A ':' (Po) ends run after Latin letters; Latin and Gu letters are in separate word-runs |
| 3 | c5dcede5bd4d289c | [31,38) | A6 needs-reader | needs reader | ')' (U+0029) at [35] between Latin and Gu; U+0AA8+U+0AC0 (Gu Lo+Mc) at [36,37] immediately follow ')'; cannot rule out Gu case suffix by code points alone |
| 4 | 2651a7bbbd36865f | [57,64) | A6 needs-reader | needs reader | ')' (U+0029) at [62]; U+0A8F (Gu Lo, 1 char) at [63] immediately follows ')'; cannot rule out Gu case element by code points alone |
| 5 | 2651a7bbbd36865f | [108,119) | A6 needs-reader | needs reader | ')' (U+0029) at [116]; U+0AA8+U+0AC7 (Gu Lo+Mn) at [117,118] immediately follow ')'; cannot rule out Gu case suffix by code points alone |
| 6 | 2651a7bbbd36865f | [295,305) | A6 needs-reader | needs reader | ')' (U+0029) at [301]; U+0AAE+U+0ABE+U+0A82 (Gu Lo+Mc+Mn) at [302,304] immediately follow ')'; cannot rule out Gu case suffix by code points alone |
| 7 | 823aaa37f4f2b123 | [84,102) | A6 needs-reader | needs reader | 7 Gu Lo at [84,95] precede '(' (U+0028) at [96]; Latin U+0045+U+0044 at [97,98]; ')' (U+0029) at [99]; 1 Gu Lo at [100]; Surrounded=True — Gu Lo on both sides of Latin; strongest structural candidate |
| 8 | 33df93edc613ea79 | [260,268) | A6 | A6 ✓ | Latin U+0041..U+0065 directly adjacent to Gu Lo U+0AA8; word-run [260,268) |
| 9 | 33df93edc613ea79 | [403,411) | A6 | A6 ✓ | Latin U+004C..U+006F directly adjacent to Gu Lo; word-run [403,411) |
| 10 | 33df93edc613ea79 | [501,508) | A6 | A6 ✓ | Latin U+0069..U+0064 directly adjacent to Gu Lo; word-run [501,508) |
| 11 | 33df93edc613ea79 | [548,554) | A6 | A6 ✓ | Latin U+0041..U+0065 directly adjacent to Gu Lo; word-run [548,554) |
| 12 | 33df93edc613ea79 | [598,603) | A6 | A6 ✓ | Latin U+0050..U+006F directly adjacent to Gu Lo; word-run [598,603) |
| 13 | 33df93edc613ea79 | [694,700) | A6 | A6 ✓ | Latin U+0041..U+0065 directly adjacent to Gu Lo; word-run [694,700) |
| 14 | e997db6027b11a0d | [69,74) | A6 | A6 ✓ | Latin U+0073 's' in same word-run as Gu Lo U+0AA8; digits U+0039 U+0030 precede run but are not part of it |
| 15 | 9c4da6ca0bd37e54 | [899,911) | A6 | needs reader | '!' (U+0021 Po) at [908] between Latin and Gu; U+0AA8+U+0ABE (Gu Lo+Mc) at [909,910] immediately follow '!'; cannot rule out Gu case suffix by code points alone |
| 16 | 2f3cba4badbd8772 | [536,547) | A6 | A6 ✓ | Latin U+0065..U+0065 ('enhance') in same word-run as Gu Lo U+0AA8; Gu mark U+0ABE at [543] is M\* and does not break the run |
| 17 | 5471cffcbdc6c112 | [3016,3020) | A6 | A6 ✓ | Latin U+0041 U+0050 directly adjacent to Gu Lo U+0AA8; word-run [3016,3020) |
| 18 | 154b7dca48602b3c | [0,5) | A6 | A6 ✓ | Latin U+0041 U+0047 U+004D directly adjacent to Gu Lo U+0AA8; word-run [0,5) starts at doc offset 0 |
| 19 | 154b7dca48602b3c | [1806,1812) | A6 | A6 ✓ | Latin U+0041 U+0054 U+0047 U+004C directly adjacent to Gu Lo; word-run [1806,1812) |
| 20 | 3c00e80bf30e1c2b | [292,296) | A6 | NOT A6 | Gu characters in span are U+0AE8 U+0AEB (Nd, Gujarati digits), not Lo; no Gu Lo letter in token — not a Gujarati word |
| 21 | 3c00e80bf30e1c2b | [1052,1057) | A6 | A6 ✓ | Latin U+0052 U+0043 directly adjacent to Gu Lo U+0AAE; word-run [1052,1057) |
| 22 | 3c00e80bf30e1c2b | [1093,1099) | A6 | A6 ✓ | Latin U+0052 U+0054 U+004F directly adjacent to Gu Lo U+0AAE; word-run [1093,1099) |

Token #2 (LSG:ní) is NOT A6: U+003A ':' (Po) terminates the Latin word-run; the Gujarati letters that follow form a separate code-point run containing no Latin letter. Token #20 (FY25) is NOT A6: U+0AE8 and U+0AEB are Gujarati digits (Nd), not Gujarati letters (Lo); no Gu Lo letter exists in that span. Tokens #3–7 and #15 are `needs reader`: each has 1–8 Gu Lo letters directly adjacent to Latin text with only punctuation between them; code-point position alone is insufficient to determine whether the Gujarati characters constitute a case suffix or the Latin is an inline expansion. Token #7 is the strongest structural candidate (Surrounded=True: Gu Lo on both sides of Latin).

## Summary

Documents checked: 50 (DAY 4, `random.Random(4).sample(range(22689), 50)`). Findings: G1 1 in 1 doc, G2 0, A1 0, A4 0, A6 14 confirmed word-runs in 7 docs + 6 needs-reader spans in 4 docs. 0 ZWJ, 0 ZWNJ, 0 replacement characters, 0 invisible characters. All 50 documents are NFC-clean. No non-Latin, non-Gujarati letters were detected in the 50-document sample. The 14 confirmed A6 word-runs are confirmed at the code-point level only; their linguistic interpretation has not been independently verified by a Gujarati reader.

Comparison vs first-pass audit: A6 count reduced from 90 code-point instances (22 token groups, 11 docs) to 14 confirmed word-runs (7 docs) + 6 needs-reader spans (4 docs) after: (a) changing `is_gujarati_letter()` to check Lo category only instead of the full Gujarati block U+0A80–U+0AFF, and (b) using letter+mark (L\*/M\*) word-run boundaries instead of whitespace tokens. Of the 8 tokens originally excluded on punctuation grounds: 2 are confirmed NOT A6 (#2 LSG: — U+003A ':' terminates the Latin run; Gujarati letters form a separate word-run; #20 FY25 — Gu digits only); 6 remain needs reader (#3–7, #15 — 1–8 Gu Lo letters directly adjacent to Latin text with only punctuation between them). G1 result is unchanged.

## Cross-reference: PR #523 Gujarati pack-level joiner evidence

**Source:** `teams/02-data-b/audit/audit_v1.csv`, row `ind-gu-fw2`, merged in PR #523. Column definitions from the CSV header: `pack_id,lang,shards,docs_raw,docs_kept,docs_dropped,zwj_raw,zwj_shard,zwnj_raw,zwnj_shard,docs_joiners_changed,docs_joiners_changed_in_kept_text,drop_rate`.

| Column | Value |
|---|---|
| pack_id | `ind-gu-fw2` |
| lang | `gu` |
| docs_raw | 23,118 |
| docs_kept | 22,689 |
| docs_dropped | 429 |
| zwj_raw (ZWJ before cleaning) | 0 |
| zwj_shard (ZWJ after cleaning) | 0 |
| zwnj_raw (ZWNJ before cleaning) | 0 |
| zwnj_shard (ZWNJ after cleaning) | 0 |
| docs_joiners_changed | 0 |
| docs_joiners_changed_in_kept_text | 0 |
| drop_rate | 1.86% |

`docs_kept` (22,689) matches the shard document count checked in this rotation audit.

**Interpretation:** The raw `ind-gu-fw2` pack contained no ZWJ (U+200D) and no ZWNJ (U+200C) in any document before cleaning. The shard likewise contains none after cleaning. Zero `docs_joiners_changed` confirms that no document had its joiner count altered by the cleaning step. G2 is not a concern at the pack level for `ind-gu-fw2`.

**Foundation:** `teams/02-data-b/audit/indic_audit.py`, which provides the `read_shard()` utility used in this rotation audit, was introduced in the same PR #523.

### Evidence levels: pack-level vs sample-level

| Level | Scope | G2 result |
|---|---|---|
| PR #523 (`audit_v1.csv`) | All 23,118 raw and 22,689 kept documents; before/after cleaning comparison | ZWJ: 0 raw, 0 shard; ZWNJ: 0 raw, 0 shard; 0 documents changed |
| This rotation audit (v3.2) | Deterministic 50-document sample (`random.Random(4).sample(range(22689), 50)`) of the decoded cleaned shard text | 0 ZWJ, 0 ZWNJ found |

The two checks are complementary, not interchangeable. PR #523 covers all documents and establishes the before/after cleaning transition for the full pack. This rotation audit adds evidence about the decoded cleaned text for a reproducible 50-document sample. Neither result substitutes for the other: the pack audit cannot distinguish which sampled documents are clean; the sample audit cannot reconstruct what was present before cleaning.

## Disease-code reference and operational scope

The five checks (G1, G2, A1, A4, A6) were assigned for this rotation by Shankar. The canonical disease definitions are in `diagnosis/DISEASES.md` in the repository. The table below records what the canonical definitions say and how the rotation-specific code-point checks relate to them.

| Code | Canonical definition (`diagnosis/DISEASES.md`) | Operational check applied in this rotation |
|---|---|---|
| G1 | "Cut at the vowel sign — a word split before a matra or virama" (§G: Damage from earlier cleaning) | Gujarati vowel sign (U+0ABE–U+0ACC, excluding unassigned U+0AC6/U+0ACA) or virama (U+0ACD) immediately preceded by a space separator, ASCII whitespace control, punctuation (P\*), decimal digit (Nd), or Latin-script letter. Document offset 0 excluded (no preceding character). |
| G2 | "Lost ZWJ or ZWNJ — a conjunct that renders wrong" (§G) | ZWJ (U+200D) or ZWNJ (U+200C) in the decoded shard text at a word boundary or doubled. Zero instances were found in the 50-document sample. |
| A1 | "Invisible junk characters — U+200B, U+FEFF, bidi marks U+202A–U+202E, U+2066–U+2069, U+00AD" (§A). The canonical definition explicitly notes: "ZWJ U+200D and ZWNJ U+200C are NOT diseases in Indic text." | Exactly the character set named in the canonical definition: U+200B, U+FEFF, U+00AD, U+202A–U+202E, U+2066–U+2069. ZWJ and ZWNJ are excluded, consistent with the canonical note. Zero instances in the 50-document sample. |
| A4 | "Replacement characters — U+FFFD — Bytes lost before release. Count them." (§A) | Scan for U+FFFD in each decoded document. Zero instances in the 50-document sample. |
| A6 | "Wrong or mixed script — Hindi text with Latin look-alike letters; a Bengali word in Assamese letters" (§A) | A word-run (maximal L\*/M\* sequence) containing both at least one Gujarati Lo letter (U+0A80–U+0AFF, category Lo) and at least one non-Gujarati Unicode letter (category L\* outside the Gujarati block). Latin-script letters identified via `regex.match(r'\p{Script=Latin}', ...)`. |

### G1 — scope note

The canonical description covers the class of "word split before a matra or virama" defects. The rotation check applies a specific set of preceding-character triggers: space separators and ASCII controls, punctuation (P\*), decimal digits (Nd), and Latin-script letters. Other preceding characters that could indicate a G1 defect in other contexts (non-Latin letters, Indic digits, symbols) are outside the scope of this rotation's trigger list. A zero count on the implemented triggers does not exclude G1 defects triggered by other preceding characters.

### G2 — scope note

The canonical description covers "lost ZWJ or ZWNJ" defects. This check examines the decoded shard text for ZWJ/ZWNJ at word edges or doubled. Finding zero instances in the 50-document sample means no such patterns remain in the cleaned text; it does not independently establish whether joiners were removed during cleaning. The before/after counts and cleaning evidence in PR #523 are complementary evidence for the full G2 picture.

## Command

```
python -I C:\Users\I763241\Downloads\audit_gu_v3.py
# Key output (v3.2):
# Sample: 50 unique indices, seed=4, first 5 (sorted): [236, 649, 840, 1928, 2179]
# Latin detection: regex.Script=Latin  (regex 2026.6.28, Unicode 15.0.0)
# G1_TARGETS validation: 14 targets, all assigned Gujarati vowel signs or virama
# docs audited:   50
# nfc_bad:        0
# ZWJ in sample:  0
# ZWNJ in sample: 0
# G1:             1 findings
# G2:             0 findings
# A1:             0 findings
# A4:             0 findings
# A6:             14 findings  (confirmed word-runs; 6 needs-reader spans from candidate inspection)
# total findings: 15
# docs with any:  7
# other_script_letter_instances: 0
```
