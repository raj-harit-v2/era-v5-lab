# Questions for TSAI: the Indic filters (issue #214, part of #217)

From the Data B filters group. We built D1 (script share), A1 (invisible characters) and G1 (broken vowel sign) in
`teams/02-data-b/filters/medicine.md`. Four things need your answer. Each has our recommendation, so a short "yes" or a
change is enough. Nothing here holds document text.

## 1. Which invisible characters should A1 remove?

**What A1 removes now (12 characters, the list in `DISEASES.md`):** U+200B zero-width space, U+FEFF byte-order mark,
U+00AD soft hyphen, U+202A to U+202E bidi embedding and override marks, U+2066 to U+2069 bidi isolate marks.
**Never removed:** U+200D ZWJ and U+200C ZWNJ. They are part of Indic spelling.

**What the packs we hold contain.** We scanned 5,000 documents in 10 packs (bn-fw2, bn-sangraha-v, hi-sangraha-s,
kn-fw2, kn-sangraha-s, ml-fw2, or-fw2, ta-fw2, ta-sangraha-s, te-sangraha-s) for every invisible, format, control, odd-space,
private-use and unassigned character. Only three kinds occur:

| Character | Count | Where |
|---|---|---|
| U+FE0F variation selector-16 | 9 characters in 3 documents | bn-fw2 1, ml-fw2 7, ta-fw2 1 |
| U+200C ZWNJ | 2 in 1 document | or-fw2 |
| U+0C49 (unassigned Telugu code point) | 2 in 1 document | te-sangraha-s |

None of the 12 A1 characters occur, and neither do U+200E, U+200F, U+00A0 or any other space variant. There is also no
ZWJ in any pack. These packs look cleaned already. Zero ZWJ in 5,000 Indic documents may mean joiners were lost earlier
(disease G2); that is outside the v1 filters, but you may want to know.

**Design consideration for LLM training.** Remove a character only if it means nothing in a left-to-right Indic script
and only adds noise tokens. Keep anything that changes how a word looks or what it means. Every removal is final, so we
ask before we add to the list.

### Tier 2: we recommend adding these (please confirm)

| Code point | Name | Why |
|---|---|---|
| U+200E, U+200F | Left-to-right mark, right-to-left mark | No effect in left-to-right text; copy-paste junk. All our scripts are left-to-right |
| U+061C | Arabic letter mark | The same kind of direction mark |
| U+2060 | Word joiner | Invisible no-break; junk in Indic prose |
| U+2061 to U+2064 | Invisible math operators | Junk outside maths |
| U+206A to U+206F | Deprecated format controls | Deprecated by Unicode |
| U+FFF9 to U+FFFB | Interlinear annotation marks | Junk |
| U+FFFC | Object replacement character | Marks a lost embedded object |
| U+E0000 to U+E007F | Tag characters | Invisible. They can hide instructions inside text, so this is also a safety point (class F) |
| U+180E | Mongolian vowel separator | Invisible, not used in Indic |

### Tier 3: TSAI's decision

| Code point | Name | Question |
|---|---|---|
| U+034F | Combining grapheme joiner | Sometimes used to order combining marks. Keep? |
| U+FE00 to U+FE0F | Variation selectors | U+FE0F follows emoji and changes how they look. Keep, or drop in Indic text only? (9 occur in our packs) |
| U+00A0, U+2000 to U+200A, U+202F, U+205F, U+3000, U+1680 | Non-breaking and special spaces | Turn into a plain space? That is not NFKC. It would be a separate rule, not A1 |
| U+2028, U+2029 | Line and paragraph separators | Turn into a newline? Also a separate rule |
| U+3164, U+FFA0, U+115F, U+1160, U+2800 | Blank-looking filler characters | Not Indic. Remove? |
| U+E000 to U+F8FF | Private use | Old Indic fonts map letters here. That is mojibake (A3 or A6), so we would not delete it blindly |
| U+200B | Zero-width space (already removed) | Where it is the only gap between two words, removing it glues them. Should it become a space when it sits between two letters? |

**Q1.** Add the Tier 2 characters to A1? **Q2.** What do you decide on each Tier 3 row?

## 2. Our understanding of "use the author's code": is it right?

What we found, and where:

- #211: "Keep each author's code as they wrote it, and mark anything you add to make it fit."
- `indic_rules/README.md` (PR #240) repeats it: the author's code unchanged; what Data B changes is marked in the code and listed.
- #240 accepts a same-language borrowed rule for a pack that has none of its own (Pritish52718, 3 Nov).
- Your visarga rulings (#240, 5 Nov): a visarga used as a colon is clean, also with a space before it, so it stays.

Everything we did with other authors' code is marked in `medicine.md`. Please check these six choices:

| # | What we did | Why |
|---|---|---|
| a | **A1:** two authors wrote it, #109 (SreekanthZipsy) and #114 (adinathauti). We use #114. | Same 12 characters (tested against both authors' own text, and on 20,000 random strings with no difference). #114 is one regex call, about 20 times faster. Is "same output, so pick the faster" fine? |
| b | In #114's code we wrote the 12 characters as `\u` escapes and added `medicine_a1`. | The author typed the invisible characters themselves, which is easy to damage in an editor. The harm tool looks for the name `medicine_<code>`. Are escapes and a rename allowed as marked changes? |
| c | **G1:** one `medicine_g1` that picks the script of the document and runs that script's author: Kannada #47, Devanagari #50, Malayalam #116, Tamil #169, Odia #86. Each function is renamed and otherwise unchanged, apart from your visarga rulings. | The harm tool allows one function per disease code, and the issue asks for G1 "for any script". Is a dispatcher over several authors' functions fine? |
| d | **G1 for Bengali, Gurmukhi, Gujarati, Telugu** has no author's code in this file. We wrote a small fallback of our own, marked as ours: remove a space between a consonant and a following vowel sign or virama, nothing else. | Spec v1 has per-pack G1 rules for those scripts, but they are tied to their packs. OK to ship ours, or should we reuse a spec v1 rule instead? |
| e | We left out #116's second function, `drop_stacked_sign`. | It drops a whole document, and we think G1 should only fix. Agree? |
| f | #116, #169 and #86 are not on `main` yet. We copied their code from the open PRs, by script. | Is citing the PR and commit enough until they merge? |

**Q3.** Is each of a to f right? If not, say which rule applies.

## 3. D1 and Devanagari: fix it, or leave it?

D1 counts letters by script and drops a document when another script dominates. Hindi, Marathi and Sanskrit all use
Devanagari, so a Hindi page in a Marathi pack has a 100% Devanagari share and is **kept**. The issue says so itself:
script share alone cannot catch it.

I could not run how many of the 38 D1 marks (te-sangraha-v 12, sa-fw2 6, hi-hplt 4 and others) are this same-script case,
because the Hindi, Marathi and Sanskrit packs are among the files I missed to download by Nov 6th.

Options:

- **A. Leave it for v1 (our recommendation).** D1 stays "script share" only. A Hindi page in a Marathi pack needs a
  language-ID check, which is a different tool (the `romanised/` folder already has IndicLID code). We say so in the README.
- **B. Add a Devanagari check inside D1.** For example marker words and letters that separate Marathi from Hindi
  (such as the letter ळ), flag only. It could wrongly flag Hindi that quotes Marathi, and we cannot measure it on gold yet.
- **C. Both:** A for the release, B once we have the packs.

**Q4.** A, B or C? If B, should it flag only, or also drop?

## 4. The pack files we are missing: please share the links again

The harm test needs `<pack_id>.parquet` for each pack. The links ended on 6 Nov and I misread the instruction and downloaded only the gold set csv files and did not download the packs I needed. 
I hold the 10 packs listed in section 1. **Please can you share links for these 12:**

| Pack | Needed for |
|---|---|
| ind-te-fw2 | harm test (gold exists) |
| ind-te-sangraha-v | harm test; holds D1 marks (12) and an A1 rule (DB-A1-002) |
| ind-kn-sangraha-v | harm test |
| ind-ta-sangraha-v | harm test |
| ind-hi-fw2 | harm test |
| ind-hi-hplt | harm test; D1 marks (4) |
| ind-hi-indiccorp | harm test |
| ind-mr-fw2 | harm test; the Devanagari G1 rule's author tested it only here; holds an A1 rule (DB-A1-001) |
| ind-mr-sangraha-v | harm test; G1 target |
| ind-gu-fw2 | harm test |
| ind-sa-fw2 | harm test; D1 marks (6) |
| ind-hi-sangraha-v | harm test (it has a gold set of 219 documents now) |

**Q5.** Where can we download these, and until when will the links work?

## Current state, so you know what the answers change

- 49 unit tests pass (made-up text only). The harm test passes (D1, A1, G1 and all in order) on the 6 packs that have both a
  pack file and a gold set: bn-fw2, bn-sangraha-v, hi-sangraha-s, kn-fw2, kn-sangraha-s, te-sangraha-s. Each result file also shows the
  ZWJ and ZWNJ counts before and after.
- ta-fw2, ta-sangraha-s, ml-fw2, or-fw2 have a pack file but no gold set yet: "gold set empty, not testable".
- NFC only, never NFKC. ZWJ and ZWNJ are never removed or added.
