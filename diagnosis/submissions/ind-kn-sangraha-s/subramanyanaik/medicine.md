# Medicine sheet: ind-kn-sangraha-s (subramanyanaik)

Pack: 500 Kannada documents, `ai4bharat/sangraha` synthetic (English Wikipedia machine-translated into Kannada).
The pack labels are in `labels.csv` next to this file. This sheet has one medicine for each disease found in more
than five documents: G4, D4, C3, B3, A6 and B2. A3 is in exactly 5 docs, but its fix is mechanical and safe, so it
gets a medicine too (Medicine 7). B4 (5), G1 (3), C1 (3) and C2 (1) are not above five, so they get no medicine.

## How the harm test was run

- **Gold set.** The Data B interim gold set for this pack, `teams/02-data-b/gold/ind-kn-sangraha-s_gold.csv`:
  **11 docs** that two readers both read in full and marked `clean`. The test was run with Data B's own tool,
  `teams/02-data-b/tools/harm_test_indic.py` (this sheet's sections and code blocks are in its format):
  ```
  python harm_test_indic.py --medicine medicine.md --pack ind-kn-sangraha-s.parquet --gold-dir teams/02-data-b/gold
  ```
  A rule may change or drop at most 1% of the gold set or 1 doc, whichever is more (here 1 of 11). The tool also
  fails a rule that changes a ZWJ/ZWNJ count, breaks NFC or removes a compatibility character.
  - As a second check, the same medicines ran on the **27 docs I read in full and labelled `clean`** (the 11 gold
    docs are among them), with my own harm test.
  - To show that the tool really ran each rule, I also ran it with all 500 docs as the "gold" set: it gives the
    same changed and dropped counts as the pack table below, with 0 joiner or normal-form problems.
- **Does it touch other docs?** Each medicine also ran on all 500 docs and was compared with my labels:
  - *off-target*: the medicine changes a doc that is not labelled with its disease;
  - *missed*: the doc is labelled with the disease, but the medicine does not touch it.
- **Does it touch other text?** On every doc, these checks ran:
  - ZWJ U+200D and ZWNJ U+200C counts never change;
  - digits never change (except where B3 or C3 remove a whole span);
  - text that was NFC stays NFC;
  - edits never overlap;
  - running a medicine a second time changes nothing (idempotent);
  - each edit only does its own job: G4 changes only ಃ into `:`, the bracket medicine never removes a letter or
    digit, the tail trim is at most 400 characters, A3 removes only a stray `Â` (with its spaces, or its quotes and
    comma), and A6 only turns one Latin initial into its Kannada letter name.
- **Hand-written cases.** 39 cases were checked:
  - legitimate text that must not change: Sanskrit visarga words, a word-internal visarga, real colons, `main()`,
    `(p <0.05)`, `a < b > c`, a real `ಐ. ಡಿ. ಕಾರ್ಡ್`, verbless sentences, a value line, `Âge` and `Côte`,
    `Ph.ಡಿ.`, Roman numerals, units and maths variables, a broken URL;
  - damage that must be fixed.
- Every medicine only edits spans it matched. Nothing else in the document can change.
- **Pipeline order:**
  1. B3 placeholders
  2. B2 tags
  3. A3 stray `Â`
  4. D4 empty brackets
  5. G4 colon
  6. C3 tail
  7. A6 Latin initials (fix) and other mixed script (flag)

  Placeholders, tags and the stray `Â` go first because removing them can leave empty brackets or empty last lines,
  which the later steps clean up. For example `(<unk> Â, ಅಹಿರು …)` becomes `(ಅಹಿರು …)` after B3, A3 and D4.

**Summary of results:**

| # | Disease | Medicine | Action | Docs with disease | Gold changed (of 11) | Gold dropped | Gold verdict | Pack: changed / dropped | Off-target | Missed |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | G4 visarga for colon | `visarga_to_colon` | fix | 167 | 0 | 0 | PASS | 167 / 0 (396 edits) | 0 | 0 |
| 2 | D4 empty brackets (mechanical part of D4) | `strip_empty_brackets` | fix | 48 of 463 D4 | 0 | 0 | PASS | 49 / 0 (68 edits) | 1 | 0 |
| 3 | C3 dangling tail | `trim_dangling_tail` | fix | 69 | 0 | 0 | PASS | 59 / 0 | 4 | 17 |
| 4 | B3 MT placeholders | `strip_mt_placeholders` | fix, or drop if more than 3 | 38 | 0 | 0 | PASS | 32 / 6 (49 edits) | 0 | 0 |
| 5 | A6 mixed script | `fix_mixed_script` | fix Latin initials, flag the rest | 26 | 0 | 0 | PASS | 12 / 0 (14 edits); 25 docs touched | 0 | 1 |
| 6 | B2 tags as text | `strip_tag_text` | fix | 14 | 0 | 0 | PASS | 13 / 0 (20 edits) | 0 | 1 |
| 7 | A3 mojibake (stray `Â`) | `strip_stray_a_circumflex` | fix | 5 | 0 | 0 | PASS | 4 / 0 (4 edits) | 0 | 1 (left to B2) |
| | All seven in order | pipeline | | | 0 | 0 | PASS | 233 / 6 | | |

**All seven in order** (Data B `harm_test_indic.py`, ALL IN ORDER): gold set of 11 documents (ind-kn-sangraha-s 11), medicine.md sha256 dc9084016893; rule: changed or dropped at most 1% or 1 document, whichever is more.
- Changed 0 of 11 (0.00%). Dropped 0 of 11 (0.00%). **PASS**
- ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
- Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

The sha256 above is of this sheet just before these result lines were pasted in; the code blocks did not change.

On the safety checks, all medicines had **0 problems**, and the pipeline is idempotent. All 39 hand-written cases pass.

---

## Medicine 1: G4, a visarga written for a colon

1. **Disease:** G4 is in 167 docs, with 396 damaged characters.
   - The MT model wrote the colon `:` as the Kannada visarga ಃ U+0C83 at the end of a word. This happens almost
     always before a list or a quote.
   - Examples:
     - `80cfb7382898fb9c`: `ಸಹೋದರನಿದ್ದಾನೆಃ` at offset 389;
     - `6334e341b04a84bc`: `ವಿವರಿಸಲಾಗಿದೆಃ` at offset 2492;
     - `dc78cbb98b87ca59`: `ಸೂಚನೆಗಳುಃ` at offset 2066.
   - Real visarga is kept: Sanskrit-origin words such as ಮೂಲತಃ, ಭಾಗಶಃ and ನಮಃ, and visarga inside a word such
     as ದುಃಖ.
2. **Medicine:** A ಃ at the end of a Kannada word becomes `:`. Two kinds of words are left alone:
   - a whitelist of Sanskrit words;
   - Sanskrit adverbs in -ತಃ/-ಶಃ with an inherent *a* (ವ್ಯಕ್ತಿಗತಃ).

   A double visarga keeps its first one (ಸ್ವತಃಃ → ಸ್ವತಃ:).
   ```python
   KN = "ಀ-೿"
   SANSKRIT_VISARGA = {"ಮೂಲತಃ","ಸ್ವತಃ","ಪುನಃ","ಬಹುಶಃ","ಭಾಗಶಃ","ಪ್ರಾಯಶಃ","ಕ್ರಮಶಃ","ಅಕ್ಷರಶಃ","ಸಾಮಾನ್ಯತಃ",
       "ವಸ್ತುತಃ","ಮುಖ್ಯತಃ","ಸಂಪೂರ್ಣತಃ","ಪ್ರಧಾನತಃ","ಸ್ವಭಾವತಃ","ಸಂಭವತಃ","ಅಂತಃ","ಛಂದಃ","ನಮಃ","ಮನಃ",
       "ಸಾಧಾರಣತಃ","ತತಃ","ಅತಃ","ದುಃ","ನಿಃ","ಪ್ರಾತಃ","ಶನೈಃ","ಇತಃ","ಸರ್ವತಃ","ಉಭಯತಃ","ಪರತಃ","ಆದಿತಃ",
       "ಶತಶಃ","ಸಹಸ್ರಶಃ","ಏಕಶಃ"}
   VISARGA_WORD = re.compile(rf"[{KN}]*ಃ(?![{KN}])")                       # word-final only
   SANSKRIT_ADVERB = re.compile(r"[ಅ-ಹೞೠೡ][ತಶ]ಃ$")

   def visarga_to_colon(text):
       def sub(m):
           w = m.group()
           return w if w in SANSKRIT_VISARGA or SANSKRIT_ADVERB.search(w) else w[:-1] + ":"
       return VISARGA_WORD.sub(sub, text)
   ```
3. **Action:** Fix the text. Only the one character changes, and the doc is kept.
4. **Harm test:**
   - **Gold** (Data B `harm_test_indic.py`, pasted from its `--md-out` block): gold set of 11 documents (ind-kn-sangraha-s 11), medicine.md sha256 dc9084016893; rule: changed or dropped at most 1% or 1 document, whichever is more.
     - Changed 0 of 11 (0.00%). Dropped 0 of 11 (0.00%). **PASS**
     - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
     - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - **Second check** (my own harm test, 27 docs I labelled `clean`): 0 changed and 0 dropped.
   - **Pack:** it changes exactly the 167 docs labelled G4, with 0 off-target and 0 missed. Every edit is one
     ಃ → `:`.
5. **Side effects:**
   - A Sanskrit word that ends in visarga and is not on the list would get a wrong colon, for example a rare
     -ಃ noun in a quoted shloka. None occurs in this pack, but the list should be reviewed for religious or
     classical texts.
   - A visarga that is wrong but not a colon (one the MT added for no reason) also becomes `:`. I did not see
     this case.

## Medicine 2: D4, empty brackets left by bad machine translation

1. **Disease:** D4 (bad machine translation) is in 463 of 500 docs, with 1,583 findings. Most of it is wrong
   meaning: literal translations of names, a reversed sense, dropped values. **No regex can fix that.** The part a
   script can fix is the empty brackets the MT leaves where it dropped foreign-script text (48 docs).
   - Examples:
     - `9e20e8d482b36907`: `ಪ್ಯಾಂಟೇಜ್ ಪ್ಲೇಹೌಸ್ ಥಿಯೇಟರ್ ()` at offset 29;
     - `9c8c88baf0ae132b`: `()` at offset 31;
     - `c3db2fd821c28710`: `(, ಕೆಲವೊಮ್ಮೆ` at offset 89 (the first item was dropped).
2. **Medicine:** It removes two things:
   - a bracket pair that holds only spaces or `,;:`, when it comes after a space or at a line start, so `f()` in
     code is never touched;
   - the stray separator in a bracket that lost only its first item.
   ```python
   EMPTY_BRACKETS = re.compile(r"[ \t]*(?<![^\s])\((?:[ \t,;:]|&nbsp;)*\)")
   LEADING_COMMA = re.compile(r"(?<=\()[ \t]*[,;]+[ \t]*(?=[^\s,;)])")

   def strip_empty_brackets(text):
       return LEADING_COMMA.sub("", EMPTY_BRACKETS.sub("", text))
   ```
3. **Action:** Fix the text by removing the empty brackets. The doc is kept.
   - The rest of D4 needs a decision on the whole pack, not a regex; see Q39 to TSAI (is a D4-only doc `fix` or
     `drop`?).
   - My proposal is to score each doc against its English source with a cross-lingual quality-estimation model,
     because this pack is synthetic and the English source exists. I have not run it, since it needs a model
     download.
4. **Harm test:**
   - **Gold** (Data B `harm_test_indic.py`, pasted from its `--md-out` block): gold set of 11 documents (ind-kn-sangraha-s 11), medicine.md sha256 dc9084016893; rule: changed or dropped at most 1% or 1 document, whichever is more.
     - Changed 0 of 11 (0.00%). Dropped 0 of 11 (0.00%). **PASS**
     - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
     - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - **Second check** (my own harm test, 27 docs I labelled `clean`): 0 changed and 0 dropped.
   - **Pack:** it touches 49 docs, all 48 labelled ones plus 1 off-target, and misses 0. It never removes a letter
     or a digit.
5. **Side effects:**
   - The off-target doc is `b6fa26245e5bbee0`. It is pseudocode where `ಖಾಲಿ ಪಟ್ಟಿ ()` means "the empty list ()",
     so the medicine removes a meaningful `()`. Code-like text should skip this medicine.
   - It cannot restore the dropped name. It only removes the visible hole.

## Medicine 3: C3, the document ends on a dangling tail

1. **Disease:** C3 is in 69 docs. The doc ends on a part with nothing after it: an empty section heading, the
   lead-in of a list or table the cleaning dropped, or a short cut fragment.
   - Examples:
     - `3a69a945a1b7aeaa`: ends `…ಈ ಕೆಳಗಿನ 20 … ತಂಡಗಳನ್ನು ಆಯ್ಕೆ ಮಾಡಲಾಯಿತುಃ` / `ಬಾಹ್ಯ ಸಂಪರ್ಕಗಳು.` at offset 451;
     - `bd7252ce7767cbad`: ends on five empty headings `ಸಿಬ್ಬಂದಿ.` … `ಉತ್ಪಾದನೆ` at offset 1183;
     - `418db7f8ae6fded8`: ends `34 ಸಹಃ` at offset 1390.
2. **Medicine:** Look at the last line, trim it if it is one of the kinds below, and repeat:
   - a known empty heading (ಉಲ್ಲೇಖಗಳು, ಟಿಪ್ಪಣಿಗಳು, ಮೂಲಗಳು, ಗ್ರಂಥಸೂಚಿ, ಬಾಹ್ಯ ಸಂಪರ್ಕಗಳು …);
   - a lead-in sentence that ends in `:` or ಃ, or that says "the following / as follows" (ಈ ಕೆಳಗಿನ, ಹೀಗಿವೆ);
   - a line of at most 4 words with no closing punctuation;
   - a heading of 1–2 words whose last word is not a finite verb.

   It never trims the title line, never trims a line that ends in a digit (table or score values), and makes no
   change if the trim would be longer than 400 characters.
   ```python
   TAIL_HEADINGS = {"ಉಲ್ಲೇಖಗಳು","ಟಿಪ್ಪಣಿಗಳು","ಮೂಲಗಳು","ಮೂಲ","ಗ್ರಂಥಸೂಚಿ","ಬಾಹ್ಯ ಕೊಂಡಿಗಳು",
                    "ಬಾಹ್ಯ ಸಂಪರ್ಕಗಳು","ಇದನ್ನೂ ನೋಡಿ","ಹೆಚ್ಚಿನ ಓದುವಿಕೆ","ಎರಕಹೊಯ್ದ","ಪಾತ್ರವರ್ಗ"}
   END_OK = tuple(".!?\"'”’)]।")
   LEAD_IN = re.compile(r"(?:ಈ ಕೆಳಗಿನ|ಕೆಳಗಿನಂತೆ|ಹೀಗಿವೆ|ಹೀಗಿದೆ|ಇಂತಿವೆ|ಇಂತಿದೆ)[^.]*\.?$")
   VERB_END = re.compile(r"(?:ರು|ದೆ|ತೆ|ರೆ|ವೆ|ತು|ದು|ನು|ಳು|ವು|ಲ್ಲ|ಬೇಕು|ಇದೆ)\W*$")

   def _last_sentence_start(line):
       body = line.rstrip()[:-1]
       cut = max(body.rfind(". "), body.rfind("? "), body.rfind("! "))
       return 0 if cut < 0 else cut + 2

   def _dangling(core):                       # core = last line, stripped
       bare = core.rstrip(".:ಃ ").strip()
       if bare in TAIL_HEADINGS: return "line"
       if core.endswith((":", "ಃ")): return "sentence"
       if core.endswith(".") and LEAD_IN.search(core[_last_sentence_start(core):]): return "sentence"
       if core[-1].isdigit(): return None
       if not core.endswith(END_OK) and len(core.split()) <= 4: return "line"
       if core.endswith(".") and len(core.split()) <= 2 and len(core) <= 30 \
               and not VERB_END.search(core[:-1]): return "line"
       return None

   def trim_dangling_tail(text, max_trim=400):
       first = text.lstrip()
       title_end = len(text) - len(first) + (first.find("\n") if "\n" in first else len(first))
       end = start = len(text.rstrip())
       while start > title_end:
           ls = text.rfind("\n", 0, start) + 1
           line = text[ls:start]
           how = _dangling(line.strip()) if line.strip() else None
           if how is None: break
           new = ls if how == "line" else ls + _last_sentence_start(line)
           if new <= title_end: break
           start = new
           while start > title_end and text[start - 1] in " \t\n": start -= 1
       if start == end or end - start > max_trim: return text
       return text[:start] + text[end:]
   ```
3. **Action:** Fix the text by trimming the dangling tail. The trailing newline is kept and the doc is never
   dropped. Docs that were labelled `drop` because almost nothing is left are dropped by the reader's verdict, not
   by this rule.
4. **Harm test:**
   - **Gold** (Data B `harm_test_indic.py`, pasted from its `--md-out` block): gold set of 11 documents (ind-kn-sangraha-s 11), medicine.md sha256 dc9084016893; rule: changed or dropped at most 1% or 1 document, whichever is more.
     - Changed 0 of 11 (0.00%). Dropped 0 of 11 (0.00%). **PASS**
     - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
     - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - **Second check** (my own harm test, 27 docs I labelled `clean`): 0 changed and 0 dropped.
   - **Pack:** it changes 59 docs, 55 of them on target and 4 off-target, and misses 17.
   - The largest trim is 232 characters over 5 lines (a proof whose formulas were dropped, leaving four ಃ lead-ins).
     The median trim is 39 characters.
5. **Side effects:**
   - **The 4 off-target trims** remove link residue or stray fragments. No prose sentence is lost:
     - an `ಬಾಹ್ಯ ಸಂಪರ್ಕಗಳು.` (External links) heading with its link title (`a06d1a685aa9f218`, `a567d25bdf9307a8`);
     - a see-also item `ತಿಹೈ` (`b09132dc931f8d94`);
     - a stray caption `(ಮೆಸ್ಟಿಜೋ).` (`865bb4af9d177158`).
   - **The 17 misses** are mostly cases a tail rule cannot see:
     - a table dropped in the middle of the doc;
     - a doc that ends on a complete sentence which mentions a list that is gone (`7f3e663054c591ed`);
     - a bibliography cut at `pp. 1-15`;
     - a list of years.
   - A lead-in that also carries facts loses those facts. For example `0b958053024326fd` ends "the following
     musicians played on songs X, Y, Z", and the song names go with it.
   - The 4-word rule would trim a real short last line that has no full stop. None of the gold docs ends like that.

## Medicine 4: B3, MT placeholders left in the text

1. **Disease:** B3 is in 38 docs, with 61 findings. In place of a number, year or code it could not translate, the
   MT model left a placeholder:
   - `<ಐ. ಡಿ. 1>`, `ಐ. ಡಿ. 1`, `ಐಡಿ1` (transliterated "ID1");
   - or `<unk>`.

   The value is lost. Examples:
   - `455c1baea7ecaeb4`: `ಐಡಿ1` at offset 340;
   - `652430783641cf74`: `<ಐ. ಡಿ. 2>` at offset 163;
   - `c3db2fd821c28710`: `ಐ. ಡಿ. 1ರಲ್ಲಿ` at offset 37841.
2. **Medicine:** It removes the placeholder, together with a Kannada case suffix attached to it or written as the
   next word (`ಐಡಿ1 ನಲ್ಲಿ`), so the sentence still reads as Kannada. It also takes:
   - the quotes around a quoted placeholder;
   - a comma that would otherwise start the line.

   It drops the doc when it has more than 3 placeholders.
   ```python
   KN = "ಀ-೿"
   CASE_SUFFIX = r"(?:ನಲ್ಲಿ|ರಲ್ಲಿ|ರಂದು|ರಿಂದ|ನಿಂದ|ರವರೆಗೆ|ರ|ನೇ|ಕ್ಕೆ|ಗೆ|ರಷ್ಟು|ರಂತೆ)"
   PLACEHOLDER = re.compile(
       r"[ \t]*(?:<unk>"
       r"|<\s*ಐ\.\s*ಡಿ\.\s*\d+\s*>"
       rf"|ಐ\.\s*ಡಿ\.\s*\d+(?:\.\d+)?(?:{CASE_SUFFIX}(?![{KN}]))?"
       rf"|ಐಡಿ\d+(?:{CASE_SUFFIX}(?![{KN}]))?)"
       rf"(?:[ \t]+{CASE_SUFFIX}(?![{KN}]))?")

   def strip_mt_placeholders(text, max_placeholders=3):
       hits = list(PLACEHOLDER.finditer(text))
       if len(hits) > max_placeholders:
           return True                                        # drop
       for m in reversed(hits):
           s, e = m.start(), m.end()
           if s and e < len(text) and text[s-1] == text[e] and text[e] in "\"'“”":
               s, e = s - 1, e + 1                            # "<ಐ. ಡಿ. 1>" -> nothing
               while s and text[s-1] in " \t": s -= 1
           if (s == 0 or text[s-1] == "\n") and text[e:e+1] in (",", ";"):
               e += 1                                         # no comma left leading the line
               while e < len(text) and text[e] in " \t": e += 1
           text = text[:s] + text[e:]
       return text
   ```
   Example: `ಇದು ಕಾರ್ಯಾಚರಣೆಯನ್ನು ಐಡಿ1 ನಲ್ಲಿ ಖರೀದಿಸಿತು.` → `ಇದು ಕಾರ್ಯಾಚರಣೆಯನ್ನು ಖರೀದಿಸಿತು.`
   The real `ಐ. ಡಿ. ಕಾರ್ಡ್` (ID card) is not touched, because a placeholder needs a digit.
3. **Action:** Fix the text when the doc has 1–3 placeholders. Drop the doc when it has more than 3, because too
   many values are gone. Six docs are dropped: `b78645d9990988c3` (5 placeholders), `7212610f297cbe1b` (15),
   `61ac039ff7e47d50` (11), `0d7f88244748a4e1` (4), `a84cbd8f664d1816` (11) and `5477f4457221c30c` (11).
   My labels say `fix` for these six because the rest of their text reads well. The threshold of 3 is a proposal
   (asked to TSAI).
4. **Harm test:**
   - **Gold** (Data B `harm_test_indic.py`, pasted from its `--md-out` block): gold set of 11 documents (ind-kn-sangraha-s 11), medicine.md sha256 dc9084016893; rule: changed or dropped at most 1% or 1 document, whichever is more.
     - Changed 0 of 11 (0.00%). Dropped 0 of 11 (0.00%). **PASS**
     - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
     - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - **Second check** (my own harm test, 27 docs I labelled `clean`): 0 changed and 0 dropped.
   - **Pack:** it touches exactly the 38 labelled docs (32 fixed, 6 dropped), with 0 off-target and 0 missed.
5. **Side effects:**
   - The sentence still lacks the value. "…in males <ಐ. ಡಿ. 2> mm…" becomes "…in males mm…", so a unit can be left
     with no number.
   - A real "ID" written as ಐ. ಡಿ. followed by a number (an ID number in prose) would be removed. None occurs in
     this pack.

## Medicine 5: A6, wrong or mixed script

1. **Disease:** A6 is in 26 docs, with 28 findings:
   - foreign names written in a mix of Cyrillic, Greek and Latin;
   - Latin letters glued to Kannada letters inside one abbreviation;
   - Cyrillic or Arabic words the MT did not transliterate.

   Examples:
   - `b1b67391f8db03cb`: `сереf meselesi` at offset 903 (U+0441 U+0435 U+0440 U+0435 with Latin f);
   - `54f770edbfb0f27e`: `i.ಇ.ಪಳೆಯುಳಿಕೆ` at offset 491 (Latin i in "i.e.");
   - `cff540231e8e8ed1`: `гнеzdо` at offset 59 (Latin z inside Cyrillic).
2. **Medicine:** Two parts.
   - **Fix: Latin initials in a Kannada abbreviation.** The MT translated an abbreviation but left its first
     letter in English: `i.ಇ.` (i.e., 10 times), `e.ಜಿ.` (e.g.), `a.ಕೆ.ಎ.` (a.k.a.), `f.ಸಿ.` (F.C., twice). The
     Latin letter becomes its Kannada letter name, as the pack writes these elsewhere (`ಎಫ್.ಸಿ.` 26 times, `ಐ.ಇ.`
     once): `i.ಇ.` → `ಐ.ಇ.`, `f.ಸಿ.` → `ಎಫ್.ಸಿ.`. It fires only on a single Latin letter (no letter, digit or dot
     before it) followed at once by a dot, a Kannada letter name and another dot. Deleting the Latin letter
     instead would leave `.ಇ.`, which is still broken.
     ```python
     LETTER_NAME = {"a": "ಎ", "b": "ಬಿ", "c": "ಸಿ", "d": "ಡಿ", "e": "ಇ", "f": "ಎಫ್", "g": "ಜಿ", "h": "ಎಚ್",
                    "i": "ಐ", "j": "ಜೆ", "k": "ಕೆ", "l": "ಎಲ್", "m": "ಎಂ", "n": "ಎನ್", "o": "ಒ", "p": "ಪಿ",
                    "q": "ಕ್ಯೂ", "r": "ಆರ್", "s": "ಎಸ್", "t": "ಟಿ", "u": "ಯು", "v": "ವಿ", "w": "ಡಬ್ಲ್ಯೂ",
                    "x": "ಎಕ್ಸ್", "y": "ವೈ", "z": "ಝಡ್"}
     NAMES = "|".join(sorted(set(LETTER_NAME.values()), key=len, reverse=True))
     LATIN_INITIAL = re.compile(rf"(?<![A-Za-z0-9.])[A-Za-z](?=\.(?:{NAMES})\.)")

     def fix_latin_initials(text):
         return LATIN_INITIAL.sub(lambda m: LETTER_NAME[m.group().lower()], text)
     ```
   - **Flag: every other mixed-script token.** It flags a token (text between spaces, brackets, quotes, `/` or
     `-`) that has either:
     - letters from two scripts out of Latin, Greek, Cyrillic, Arabic and Kannada;
     - or any Cyrillic or Arabic letter (the source is English Wikipedia).

     It does not flag Latin or digits joined to a Kannada case suffix (`49ersನ`, `GMTಯ`, `IIIಯ`), because that is
     normal here.
   ```python
   SCRIPTS = {"Latin": r"A-Za-zÀ-ɏ", "Greek": r"Ͱ-Ͽ", "Cyrillic": r"Ѐ-ӿ",
              "Arabic": r"؀-ۿ", "Kannada": r"ಀ-೿"}
   TOKEN = re.compile(r"[^\s()\"'“”‘’,;:!?\[\]{}<>/\-]+")
   LATIN_PLUS_SUFFIX = re.compile(r"[A-Za-z0-9]+[ಀ-೿]+|[ಀ-೿]+[A-Za-z0-9]+")

   def _flag_mixed_script(text):
       out = []
       for m in TOKEN.finditer(text):
           found = {n for n, r in SCRIPTS.items() if re.search(f"[{r}]", m.group())}
           mixed = len(found) >= 2 and not (found == {"Latin", "Kannada"} and LATIN_PLUS_SUFFIX.fullmatch(m.group()))
           if mixed or found & {"Cyrillic", "Arabic"}:
               out.append((m.start(), m.group()))
       return out
   ```
3. **Action:** Fix the Latin initials; flag the rest without changing the text. The flagged docs go to a reader
   or are scored.
   - The rest has no safe automatic fix. Removing the Latin letters leaves a broken word (`сереf` → `сере`), and
     the right letters are not knowable from the text: `сереf` should be the Turkish *Şeref*, and a homoglyph map
     would give a wrong *ceref*. In `αo` (a physics symbol, a₀) removing the `o` changes the formula.
   - What stays flagged: Cyrillic, Greek and Arabic names in their own script (often garbled, such as
     `гнеzdо`), a broken URL whose site name was translated (`W.ವಿಹಂಗಮ.ಕಾಮ್` in `15871320cdf79aa0`) and a place
     name `Åಗೋರ್ನಲ್ಲಿ` (`25874ea69e8cd152`).
   - The other option would be to drop every flagged doc. That loses docs whose other text is usable, so I do
     not propose it.
4. **Harm test:**
   - **Gold** (Data B `harm_test_indic.py`, pasted from its `--md-out` block): gold set of 11 documents (ind-kn-sangraha-s 11), medicine.md sha256 dc9084016893; rule: changed or dropped at most 1% or 1 document, whichever is more.
     - Changed 0 of 11 (0.00%). Dropped 0 of 11 (0.00%). **PASS**
     - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
     - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - **Second check** (my own harm test, 27 docs I labelled `clean`): 0 changed or flagged.
   - **Pack:** the fix changes 12 docs (14 initials), all labelled A6, for example `54f770edbfb0f27e`
     (`i.ಇ.ಪಳೆಯುಳಿಕೆ` → `ಐ.ಇ.ಪಳೆಯುಳಿಕೆ` at offset 491), `605c195dc5422a06` (`(i.ಇ. ಪೋಪ್)` at offset 70565) and
     `b497ade9ed6f64c3` (`f.ಸಿ.` at offset 28). Fix and flag together touch 25 docs, all labelled A6, with 0
     off-target. After the whole pipeline, 13 docs are still flagged (25 before the fix). It misses 1,
     `309c6300b2a22783`: a garbled word in pure Greek (`αλεσιρεσι`), which looks like a real Greek quote.
   - It does not touch `Ph.ಡಿ.` (a Latin letter comes before the initial), Roman numerals, units or maths
     variables.
5. **Side effects:**
   - The fixed abbreviation is consistent Kannada, but still a letter-by-letter transliteration of the English
     one; a reader may prefer the Kannada word (ಅಂದರೆ for i.e., ಉದಾಹರಣೆಗೆ for e.g.). Choosing words needs a
     reader, so the medicine only makes the script consistent.
   - A real Cyrillic or Arabic quote, such as a Russian name given in its own script, gets flagged. This costs a
     reader's time but changes no text.

## Medicine 6: B2, HTML tags written as text

1. **Disease:** B2 is in 14 docs, with 15 findings:
   - literal tags such as `<br>`;
   - tags the MT transliterated: `<ಬಿ. ಆರ್.>` = "<br>", `<ಬಿಆರ್>`, and `<ರಿಫರ್ ಹೆಸರು = "…"> </ರಿಫರ್>` =
     `<ref name="…"></ref>`;
   - empty table-cell residue `<> </Â>`.

   Examples:
   - `3a69a945a1b7aeaa`: `<ಬಿ. ಆರ್.>` at offset 573;
   - `de997c2e752683e0`: `<ರಿಫರ್ ಹೆಸರು =` at offset 643;
   - `4c6c7ddb7fca4227`: `<ಬಿಆರ್>` at offset 1551.
2. **Medicine:** It removes these tags, and the line break too when the tag was the whole line.
   ```python
   TAG = re.compile(
       r"[ \t]*(?:<\s*/?\s*(?:br|ಬಿ\.?\s*ಆರ್\.?|ಬಿಆರ್)\s*/?\s*>"
       r"|<\s*/?\s*ರಿಫರ್(?:\s[^<>\n]{0,80})?>"
       r"|<>\s*</Â>)")

   def strip_tag_text(text):
       def sub(m):
           s, e = m.span()
           whole_line = (s == 0 or text[s-1] == "\n") and text[e:e+1] == "\n"
           return "" if not whole_line else "\0"            # marker: also eat the newline
       return TAG.sub(sub, text).replace("\0\n", "")
   ```
3. **Action:** Fix the text by removing the tags. The doc is kept.
4. **Harm test:**
   - **Gold** (Data B `harm_test_indic.py`, pasted from its `--md-out` block): gold set of 11 documents (ind-kn-sangraha-s 11), medicine.md sha256 dc9084016893; rule: changed or dropped at most 1% or 1 document, whichever is more.
     - Changed 0 of 11 (0.00%). Dropped 0 of 11 (0.00%). **PASS**
     - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
     - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - **Second check** (my own harm test, 27 docs I labelled `clean`): 0 changed and 0 dropped.
   - **Pack:** it changes 13 docs, all labelled B2, with 0 off-target. It misses 1, `f1161ea20322b1f3`, where
     `<ವೀಸಾ` is a broken tag with no closing `>` that runs into prose; it is left for a reader.
   - Maths such as `a < b > c` and `(p <0.05)` is not touched.
5. **Side effects:**
   - A `<br>` in the middle of a line is removed without putting in a line break, so two sentences can end up
     joined by a space.
   - The `ref` name text inside `<ರಿಫರ್ …>` is lost. It was citation markup, not prose.

## Medicine 7: A3, a stray `Â` left by double decoding

1. **Disease:** A3 is in 5 docs, with 11 findings, and every one is a stray `Â` (U+00C2). It is what is left of a
   UTF-8 sequence that starts with byte C2 (for example a non-breaking space, C2 A0) after the text was decoded as
   Latin-1 once and the second byte was lost. Five docs is not above the threshold, but the fix is mechanical.
   Examples:
   - `1e1de41eb43d681d`: `Â 1910ರಲ್ಲಿ` at offset 640 (start of a line);
   - `3da04151703f4541`: `"Â",` at offset 17186 (a quoted kanji that was lost, leaving only `Â`);
   - `b6fa26245e5bbee0`: `s Â ಮೊದಲ (p, c)` at offset 4291 (pseudocode; the `Â` stood for an arrow).
2. **Medicine:** It removes an `Â` that is not part of a Latin word (`Âge` and `Côte` stay), together with:
   - the spaces before it, or the spaces after it when it starts a line;
   - the quotes around it and the comma after it, when it was the whole quoted item.

   It skips `</Â>`, the table-cell residue `<> </Â>` that Medicine 6 (B2) removes as a whole.
   ```python
   LATIN = "A-Za-zÀ-ɏ"
   STRAY_A = re.compile(rf"\"Â\"(?:,[ \t]*)?|[ \t]*(?<![{LATIN}/])Â(?![{LATIN}>])")

   def strip_stray_a_circumflex(text):
       for m in reversed(list(STRAY_A.finditer(text))):
           s, e = m.start(), m.end()
           if s == 0 or text[s-1] == "\n":                    # line start: take the spaces after it
               while e < len(text) and text[e] in " \t": e += 1
           text = text[:s] + text[e:]
       return text
   ```
3. **Action:** Fix the text. Only the `Â` and the spaces or quotes around it are removed; the doc is kept.
4. **Harm test:**
   - **Gold** (Data B `harm_test_indic.py`, pasted from its `--md-out` block): gold set of 11 documents (ind-kn-sangraha-s 11), medicine.md sha256 dc9084016893; rule: changed or dropped at most 1% or 1 document, whichever is more.
     - Changed 0 of 11 (0.00%). Dropped 0 of 11 (0.00%). **PASS**
     - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
     - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - **Second check** (my own harm test, 27 docs I labelled `clean`): 0 changed and 0 dropped. No gold doc has an `Â`.
   - **Pack:** it changes 4 docs (4 edits), all labelled A3, with 0 off-target. The fifth A3 doc,
     `5f6f044745aeb4f4`, has its 7 `Â` only inside `<> </Â>`, which B2 removes earlier in the pipeline.
   - In `a84cbd8f664d1816`, `(<unk> Â, ಅಹಿರು ಅಕ್ಷರಗಳು)` becomes `(ಅಹಿರು ಅಕ್ಷರಗಳು)` after B3, A3 and D4.
5. **Side effects:**
   - The lost character is not restored: in `b6fa26245e5bbee0` the pseudocode arrow is gone (`s ಮೊದಲ (p, c)`),
     and in `3da04151703f4541` the kanji is gone, so the sentence lists one item fewer.
   - A text that really uses `Â` on its own (a single-letter label) would lose it. None occurs in this pack.

## Observations

- **F2 benchmark leak: none found.** G9's `teams/09-evaluation/decontam/decontam_check.py` on all 500 docs with the
  full fingerprint set v1 (set_sha256 `11e290a44d1467875fdf8bebc55eab21f0a6367f411aab98a4a027a546fd372e`; it covers
  FLORES-200, IN22-Gen, IN22-Conv, MILU and the English, code and maths benchmarks): **0 of 500 docs flagged**.
  So no doc is labelled F2, and F2 needs no medicine.
