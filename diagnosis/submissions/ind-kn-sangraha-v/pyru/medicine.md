# Medicine sheet: ind-kn-sangraha-v (pyru)

**How these labels were made.** Claude (Anthropic's AI model, used in Claude Code) labelled 497 of the 500 rows at
my request. It read every document in full and wrote the evidence and the notes. I labelled 3 rows myself:
`5f35a70c444aa76f`, `dfca849b43c8a487` and `e7b4e0ef6f12fe8a`. Later, at my request, Claude added C2 to
`dfca849b43c8a487` and C1 to `e7b4e0ef6f12fe8a`, so that they follow the same rules as the other rows. After the lab
ruling of 25 Oct on repeated passages, Claude also changed `5f35a70c444aa76f` from clean to fix (C2). The note on each
of these three rows says so. Claude also wrote the medicine code in this sheet and ran the checks on the pack. Where
this sheet says "my labels", it means all 500 rows.

One section for each disease that my labels show more than five times. Each section has the tested code, and each code block runs on its own: the helper functions it needs are copied into it. Only Python's `re` module is needed.

The rule of each section is `medicine_<code>(text)`, the name that Data A's `harm_test.py --rules medicine.md` looks for. A fix rule returns the fixed text; a drop rule returns True when the document is dropped. `clean(text)` below runs all of them and returns the fixed text, or None when the document is dropped. The sections are in the run order of `clean()`, so a test that runs the rules one after another in file order runs them as `clean()` does.

**Harm tests.** The gold set is Data B's interim Kannada gold set, as rebuilt on 31 Oct (#161, commit a8ae686). It has 175 documents: 103 from this pack, 45 from ind-kn-fw2 and 27 from ind-kn-sangraha-s. The 103 from this pack are the documents that `Anusha-raju` and I both read in full and marked clean, with no codes. I ran Data A's `harm_test.py --rules medicine.md --rule all` (PR #140, commit 00a556c) on them with this sheet, with the per-document time limit on. As TSAI said in CAP, each medicine is tested on the gold set of its own pack, so the results below are for the 103 documents of this pack. All the medicines in order change 0 and drop 0 of the 103 gold documents (0.0%): pass. Each section gives its medicine alone.

Run order on one document: B4 first, because it restores the real line breaks that the line rules need; then the drop rules; then the other fixes. C3 comes last, after the boilerplate at the end is gone. Counts and offsets below are on the text after the B4 fix (the same as the pack except in the 15 documents with a literal backslash-n).

```python
def clean(t):
    """Apply the medicines in order. Return None when the document is dropped."""
    t = fix_literal_newline(t)
    if has_legacy(t) or heavy_broken_signs(t) or headline_list(t) or mt_traces(t):
        return None
    t = fix_over_normalised(t)
    t = fix_lookalikes(t)
    t = strip_boilerplate(t)
    t = dedupe_lines(t)
    t = cut_english_tail(t)
    t = cut_unfinished_end(t)
    return t
```

## Medicine 1: B4, a literal backslash-n in the text

1. **Disease:** B4. My labels: 19 of 500 labelled documents. In the whole pack the rule finds 15 of 500 documents (309 backslash-n); 15 of them are documents that I labelled B4. The two characters '\' and 'n' stand where a line break should be. The text was escaped twice.
   Three examples:
   - `3db23e9e76ca858e` at 81: `ಕನ್ನಡ ನ್ಯೂಸ್\nಮೈಸೂರುಃ ಚಾಮು` (the two characters 005C 006E)
   - `cac1e9c1e7750da3` at 108: `anet Kannada\nಮುಖಪುಟ » ಸ್ಥ` (the two characters 005C 006E)
   - `76ab2e51b2167698` at 66: `ಗಳು | AASraw\n/ಬ್ಲಾಗ್/ಗ್ಯಾ` (the two characters 005C 006E)

2. **Medicine:** Replace every backslash-n (two characters) with a real line break.

   ```python
   BS = chr(92)


   def fix_literal_newline(t):
       """B4: a literal backslash-n (two characters) becomes a real newline."""
       return t.replace(BS + "n", "\n")


   def medicine_b4(text):
       """The B4 rule, under the name that the harm tests look for: returns the fixed text."""
       return fix_literal_newline(text)
   ```

3. **Action:** Fix.

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).

5. **Side effects:**
   - A text about programming that shows \n on purpose would change.
   - A literal \t or \r is not handled.

## Medicine 2: A3, leftover characters of an old Kannada font

1. **Disease:** A3. My labels: 10 of 500 labelled documents. In the whole pack the rule finds 6 of 500 documents; 6 of them are documents that I labelled A3. Some pages were typed in an ASCII font (Nudi or Baraha) and converted to Unicode only in part. Latin letters such as ø, ä, Ç and É are left inside Kannada words.
   Three examples:
   - `f1ee75f8842c24c6` at 527: `ಸ್ಕೊ$್ವಟ್ರ್ಸೊವ್` (residue 0024 '$')
   - `7a99953536fb30ba` at 1051: `ಸಾಂಸ್ಕøತಿಕ` (residue 00F8 'ø')
   - `c84d7b1e2256670e` at 1064: `ನಿಟ್ಟಿನÇÉೇ` (residue 00C7 'Ç')

2. **Medicine:** Drop a document when a Kannada word holds a Latin-1 or Latin Extended letter, or a '$' directly before a Kannada vowel sign or virama. IAST letters (ā, ṇ, ś) do not count, and neither do '$100ರಷ್ಟು' or '30°ಸೆ'.

   ```python
   import re

   IAST = set("āīūṛṝḷṅñṇṭḍśṣḥṁĀĪŪṚṄÑṆṬḌŚṢḤṀ")              # romanised Indic, not legacy-font residue


   def is_kn(c):
       return 0x0C80 <= ord(c) <= 0x0CFF


   def legacy_residue(t):
       """A3: offsets of legacy-font (Nudi/Baraha) residue inside Kannada words.

       Residue is a Latin-1 or Latin Extended letter inside a word that also holds Kannada (ಸಂಸ್ಕøತಿ), or a '$'
       directly before a Kannada vowel sign or virama (ಸ್ಕೊ$್ವ). A '$' before a digit ($100ರಷ್ಟು), a degree
       sign (30°ಸೆ) and IAST letters are not residue.
       """
       out = []
       for m in re.finditer(r"\S+", t):
           w = m.group()
           if not any(is_kn(c) for c in w):
               continue
           for k, c in enumerate(w):
               nxt = w[k + 1] if k + 1 < len(w) else " "
               if c.isalpha() and 0xC0 <= ord(c) <= 0x24F and c not in IAST:
                   out.append(m.start() + k)
               elif c == "$" and is_kn(nxt) and not nxt.isalpha():
                   out.append(m.start() + k)
       return out


   def has_legacy(t):
       """A3: drop a document with legacy-font (Nudi/Baraha) residue inside Kannada words."""
       return bool(legacy_residue(t))


   def medicine_a3(text):
       """The A3 rule, under the name that the harm tests look for: True drops the document."""
       return has_legacy(text)
   ```

3. **Action:** Drop. The way back from these fonts depends on the font, so a safe fix is not possible.

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).

5. **Side effects:**
   - A good document with a single leftover letter is lost.
   - A foreign name with an accent glued to a Kannada suffix (Peléಗೆ) drops the document.

## Medicine 3: G1, vowel signs cut off from their letter

1. **Disease:** G1. My labels: 32 of 500 labelled documents. In the whole pack the rule finds 3 of 500 documents; 3 of them are documents that I labelled G1. In some documents a vowel sign or virama stands with no letter before it: a reph in the wrong place, or a letter lost when the text was taken out of a PDF.
   Three examples:
   - `c245d243cb8e3428` at 20: `ಾಯಾಗ್ರಹಣ` (0079 0020 0CBE)
   - `c84d7b1e2256670e` at 1066: `ನಿಟ್ಟಿನÇÉೇ` (00C7 00C9 0CC7)
   - `9f746e71dabdd692` at 1561: `ವಿಶೇಷವಾದರ್ಷಾಾಂ` (0CB7 0CBE 0CBE)

2. **Medicine:** Count the vowel signs, viramas, nuktas, anusvaras and visargas that have no letter to sit on. ಆ್ಯ, the standard spelling of the English 'a' sound (ಆ್ಯಪ್), does not count. Drop a document with 3 or more.

   ```python
   KN_CONS = set(range(0x0C95, 0x0CBA)) | {0x0CDE}         # consonants
   KN_MATRA = set(range(0x0CBE, 0x0CCD))                   # dependent vowel signs
   VIRAMA_CP, NUKTA_CP, ANUSVARA_CP, VISARGA_CP = 0x0CCD, 0x0CBC, 0x0C82, 0x0C83   # code points, not characters
   LEN_MARKS = {0x0CD5, 0x0CD6}
   VOWELS_BEFORE_YA = {0x0C85, 0x0C86, 0x0C8E}             # ಅ ಆ ಎ, as in ಆ್ಯಪ್
   YA = 0x0CAF


   def is_kn(c):
       return 0x0C80 <= ord(c) <= 0x0CFF


   def broken_signs(t):
       """G1: offsets of a vowel sign, virama, nukta, anusvara or visarga that has no letter to sit on.

       ಆ್ಯ (vowel + virama + ಯ) is the standard spelling of the English "a" sound (ಆ್ಯಪ್) and is not counted.
       A visarga after a virama is a colon turned into a visarga (G4), not a broken sign.
       """
       out = []
       for i, ch in enumerate(t):
           o = ord(ch)
           p = ord(t[i - 1]) if i else 0
           nx = ord(t[i + 1]) if i + 1 < len(t) else 0
           if o == VIRAMA_CP and p in VOWELS_BEFORE_YA and nx == YA:
               continue
           if o in KN_MATRA or o == VIRAMA_CP or o == NUKTA_CP:
               if p not in KN_CONS and p != NUKTA_CP:
                   out.append(i)
           elif o == ANUSVARA_CP:
               if not (i and is_kn(t[i - 1])) or p == VIRAMA_CP:
                   out.append(i)
           elif o == VISARGA_CP:
               if not (i and is_kn(t[i - 1])):
                   out.append(i)
           elif o in LEN_MARKS:
               if p not in (0x0CBF, 0x0CC6, 0x0CCA):
                   out.append(i)
       return out


   def heavy_broken_signs(t, min_count=3):
       """G1: drop a document with min_count or more vowel signs or viramas that have no letter to sit on."""
       return len(broken_signs(t)) >= min_count


   def medicine_g1(text):
       """The G1 rule, under the name that the harm tests look for: True drops the document."""
       return heavy_broken_signs(text)
   ```

3. **Action:** Drop. A document with one or two such signs is kept.

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).

5. **Side effects:**
   - Documents with one or two broken signs keep them. My labels show G1 in 32 documents; most are a misplaced reph (ಜಾಜ್ರ್ for ಜಾರ್ಜ್, ಮಾಚ್ರ್ for ಮಾರ್ಚ್) or a few lost vowel signs in PDF text, which I marked fix, not drop. The rule drops the 3 documents where the damage is dense.
   - A text about Kannada spelling that shows a vowel sign on its own (ಾ) would count it.

## Medicine 4: C5, lists of headlines, links or keywords

1. **Disease:** C5. My labels: 10 of 500 labelled documents. In the whole pack the rule finds 3 of 500 documents; 3 of them are documents that I labelled C5. Some documents are not text but a list: related headlines, trending topics or a keyword list.
   Three examples:
   - `3af42c530ed0274e` at 0: 15 lines, the first `2020ರ ಒಲಿಂಪಿಕ್ಸ್ಗೆ ಕುಸ್ತಿಪಟು ಸುಶೀಲ್ ಅನುಮಾನ!`
   - `62fe00fa46296335` at 0: 10 lines, the first `Welcome!`
   - `abe132cfa2a7e98a` at 0: 26 lines, the first `- ದಿನದಿಂದ ದಿನಕ್ಕೆ ಕುಸಿದ ಕಲೆಕ್ಷನ್; 410 ಕೋಟಿ ಬಜ ...`

2. **Medicine:** Drop a document with 8 or more lines when at least 80% of its text is in short lines (100 characters or less) that do not end with a full stop.

   ```python
   def headline_list(t, min_lines=8, share=0.8):
       """C5: drop a document that is only a list: min_lines or more lines, and at least share of the text in short
       lines (100 characters or less) that do not end with a full stop, as in a list of headlines."""
       lines = [l.strip() for l in t.split("\n") if l.strip()]
       if len(lines) < min_lines:
           return False
       short = [l for l in lines if len(l) <= 100 and not l.endswith(".")]
       return sum(map(len, short)) >= share * sum(map(len, lines))


   def medicine_c5(text):
       """The C5 rule, under the name that the harm tests look for: True drops the document."""
       return headline_list(text)
   ```

3. **Action:** Drop.

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).

5. **Side effects:**
   - A poem, a song or a short list-style notice with 8 or more lines would be dropped. Kannada verse lines have no full stop, so verse is the main risk; in this pack the rule drops no verse.
   - A list with a few long lines, a list inside an article, or a keyword line at the end ('Key words: ...') is not caught. My labels show C5 in 10 documents and the rule finds 3 of them.

## Medicine 5: D4, bad machine translation

1. **Disease:** D4. My labels: 30 of 500 labelled documents. In the whole pack the rule finds 1 of 500 documents; 1 of them is a document that I labelled D4. Pages machine-translated into Kannada, mostly from Russian and English company, how-to and product pages: wrong word senses (ceiling fans as admirers, LED as 'led'), broken clauses, transliterated Russian words, and number placeholders of the translation engine.
   Three examples:
   - `76ab2e51b2167698` at 1205: `ಎಮ್ಎಮ್ಎನ್ಎಕ್ಸ್`
   - `de969a2be049f10a` at 1953: 'ಸಂಪೂರ್ಣ ಕೋಪವನ್ನು ಹೊಂದಿದ್ದೇವೆ' (from my labels; the rule does not find it)
   - `263dcb1b5bef1054` at 559: 'ಇದು ಮ್ಯಾಟರ್ ಕ್ಲಾಯ್ಡೆಲ್ ರಾಜ್ಯವಾಗಿದೆ' (from my labels; the rule does not find it)

2. **Medicine:** Drop a document with the number placeholder of a known translation engine (XNUMX, NUMX, or the same written in Kannada letters, such as ಎಕ್ಸ್ಎನ್ಎಕ್ಸ್ or ಎಮ್ಎಮ್ಎನ್ಎಕ್ಸ್), or with two or more English function words (is, the, of, and, to, ...) standing alone between Kannada words.

   ```python
   import re

   NUM_PLACEHOLDER = re.compile("NUMX|XNUM|ಎಕ್ಸ್ಎನ್ಎಕ್ಸ್|ಎಮ್ಎಕ್ಸ್ಎಕ್ಸ್|ಎಮ್ಎಮ್ಎನ್ಎಕ್ಸ್|ಎಂಎನ್ಎಕ್ಸ್")
   LONE_ENGLISH = re.compile("[ಀ-೿]+ (?:is|the|of|and|to|in|for|with|on|a|an|are|was) [ಀ-೿]+")


   def mt_traces(t):
       """D4: drop a document with traces of a translation engine: the number placeholder of a known engine
       (XNUMX, written in Kannada letters as ಎಕ್ಸ್ಎನ್ಎಕ್ಸ್ or ಎಮ್ಎಮ್ಎನ್ಎಕ್ಸ್), or two or more English function words
       left alone between Kannada words."""
       return bool(NUM_PLACEHOLDER.search(t)) or len(LONE_ENGLISH.findall(t)) >= 2


   def medicine_d4(text):
       """The D4 rule, under the name that the harm tests look for: True drops the document."""
       return mt_traces(text)
   ```

3. **Action:** Drop.

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).

5. **Side effects:**
   - The rule is weak: my labels show D4 in 30 documents and it finds 1 of them. Most bad translation shows only in the meaning. A scale filter needs a model, for example the perplexity of a Kannada language model or a round-trip translation score; I give the rule as a safe first step.
   - A Kannada text that quotes an English title with 'of' or 'the' in two places would be dropped.

## Medicine 6: G4, visarga written for a colon, and the split dot

1. **Disease:** G4. My labels: 270 of 500 labelled documents. In the whole pack the rule finds 267 of 500 documents (620 visargas and dots); 266 of them are documents that I labelled G4. An earlier cleaning step turned ':' after a Kannada letter into the visarga 'ಃ' (for example the Indic NLP normaliser, correct_visarga), and put a space after the dot inside numbers and web addresses (3. 3 ಬಿಲಿಯನ್, 10. 20ಕ್ಕೆ, newskadaba. com). I file both under G4, damage from earlier cleaning.
   In this pack a colon never follows a Kannada letter directly (0 times), a colon after a space or a digit appears 182 times, and a visarga follows a virama 33 times, which Kannada spelling never does.
   Three examples:
   - `dfca849b43c8a487` at 7: `ಮಂಗಳೂರುಃ` → `ಮಂಗಳೂರು:` (0CC1 0C83 → 0CC1 003A)
   - `7db0b44ffea9a442` at 21: `ಟುಃ` → `ಟು:` (0CC1 0C83 → 0CC1 003A)
   - `08a0c3ac46989162` at 965: `ನಿರ್ಮಿಸುತ್ತಾರೆಃ` → `ನಿರ್ಮಿಸುತ್ತಾರೆ:` (0CC6 0C83 → 0CC6 003A)

2. **Medicine:** Two steps. First, turn a visarga back into ':' when it stands for a colon.
   - A visarga right after a virama (್ಃ) is always a colon. Kannada spelling never puts it there.
   - A visarga at the end of a word is a colon, unless the word is a real visarga word: Sanskrit adverbs in -ತಃ and -ಶಃ (ಸ್ವತಃ, ಬಹುಶಃ), a short list (ಪುನಃ, ನಮಃ, ಮನಃ, ಅಂತಃ and others), or the start of a compound (ದುಃಖ, ನಿಃಸಂಶಯ, ಅಂತಃಕರಣ).
   - A visarga inside a word is a colon only when the part before it has three or more letters (a dateline glued to the next word).
   - Sanskrit verse is left alone: a line with a danda (। ॥); a line with two or more candidates that is short (160 characters or less) or whose candidates end like Sanskrit nominatives; and, in a document with a danda anywhere, every candidate except ್ಃ and the end of the first word of a line.
   - PDF verse often writes the danda as '|' or '||'. In a document where a visarga is followed by '|', or where two or more lines end in '|', every line with a '|' is left alone.
   Second, join a dot that has a space after it inside a decimal or a clock time (3. 3 → 3.3; not at the start of a line, where '1. 5' can be a list item) or inside a web address (www. , . com, . in, . gov and the like).

   ```python
   """Find visarga (U+0C83) that stands for a colon.

   The Indic NLP normaliser (correct_visarga) rewrites ':' after an Indic letter as visarga, so a dateline
   'ಬೆಂಗಳೂರು:' becomes 'ಬೆಂಗಳೂರುಃ'. Real visarga words are a small closed set: Sanskrit adverbs in -ತಃ / -ಶಃ,
   a few words (ಪುನಃ, ನಮಃ, ...) and compound prefixes (ದುಃಖ, ನಿಃಸಂಶಯ, ಅಂತಃಕರಣ). Lines with a danda (। ॥) are
   treated as Sanskrit verse and left alone. PDF verse often writes the danda as '|' or '||': in a document where a
   visarga is followed by '|', or where two or more lines end in '|', every line with a '|' is left alone too.
   """
   import re

   VIS, VIRAMA, AA_SIGN = chr(0x0C83), chr(0x0CCD), chr(0x0CBE)
   KN_BLOCK = chr(0x0C80) + "-" + chr(0x0CFF)                  # the Kannada block, for character classes
   JOINERS = chr(0x200C) + chr(0x200D)                          # ZWNJ, ZWJ
   KN = re.compile("[" + KN_BLOCK + "]")
   WORD_END = re.compile("[" + KN_BLOCK + JOINERS + "]+$")
   GENUINE_END = re.compile(r"(ತಃ|ಶಃ)$")
   GENUINE = {"ಪುನಃ", "ನಮಃ", "ಮನಃ", "ಅಂತಃ", "ಯಶಃ", "ತೇಜಃ", "ಶಿರಃ", "ಪ್ರಾತಃ", "ಉರಃ", "ಛಂದಃ", "ತಪಃ", "ಪಯಃ",
              "ವಯಃ", "ನಭಃ", "ಅಧಃ", "ಪುರಃ", "ಬಹಿಃ", "ದುಃ", "ನಿಃ", "ಮುಹುಃ", "ಚಕ್ಷುಃ", "ಆಯುಃ", "ಧನುಃ", "ವಪುಃ",
              "ಹವಿಃ", "ಜ್ಯೋತಿಃ", "ಶ್ರೇಯಃ", "ಮನಸಃ", "ರಜಃ", "ತಮಃ", "ಸ್ವಾಹಾಃ", "ಓಂನಮಃ", "ಸ್ವತಹಃ"}
   PIPE_AFTER_VIS = re.compile(VIS + r"[ \t]*\|")
   PREFIX = {"ದು", "ನಿ", "ಅಂತ", "ಮನ", "ತೇಜ", "ಪ್ರಾತ", "ಬಹಿ", "ಪುನ", "ಛಂದ", "ತಪ", "ಯಶ", "ಅಧ", "ಶಿರ", "ಸುದು",
             "ಸರ್ವದು", "ಸುಖದು", "ಮನಸ್ತಾಪದು"}

   def colon_visargas(t, verse_min=2, verse_len=160):
       """Return the offsets of every visarga in t that stands for a colon.

       A line with verse_min or more candidates is taken as Sanskrit verse and skipped when it is short
       (verse_len characters or less) or when most candidates end like a Sanskrit nominative (-aH after a
       bare consonant, or -AH). Kannada prose with several colons ends them on vowel signs (ಹೇಳುತ್ತಾರೆಃ).
       """
       verse_doc = "।" in t or "॥" in t
       by_line = {}
       for i in _candidates(t):
           start = t.rfind("\n", 0, i) + 1
           if verse_doc and t[i - 1] != VIRAMA and " " in t[start:i].strip():
               continue                                    # a document with verse: only first words and ್ಃ
           by_line.setdefault(start, []).append(i)
       out = []
       for start, offs in by_line.items():
           end = t.find("\n", start); end = len(t) if end < 0 else end
           if len(offs) >= verse_min:
               sanskrit = sum(1 for i in offs if t[i - 1] == AA_SIGN or 0x0C95 <= ord(t[i - 1]) <= 0x0CB9)
               if end - start <= verse_len or sanskrit / len(offs) >= 0.75:
                   continue
           out.extend(offs)
       return out

   def _candidates(t):
       out = []
       pipe_verse = bool(PIPE_AFTER_VIS.search(t)) or sum(1 for l in t.split("\n") if l.rstrip().endswith("|")) >= 2
       for m in re.finditer(VIS, t):
           i = m.start()
           line_start = t.rfind("\n", 0, i) + 1
           line_end = t.find("\n", i); line_end = len(t) if line_end < 0 else line_end
           if "।" in t[line_start:line_end] or "॥" in t[line_start:line_end]:
               continue
           if pipe_verse and "|" in t[line_start:line_end]:
               continue                                    # verse with '|' as danda
           p = t[i - 1] if i else " "
           if p == VIRAMA:
               out.append(i); continue
           if not KN.match(p):
               continue                                    # orphan visarga: G1, not a colon
           w = WORD_END.search(t[:i]).group()
           nx = t[i + 1] if i + 1 < len(t) else " "
           if KN.match(nx):                                # visarga inside a word
               if w in PREFIX or w.endswith(("ದು", "ನಿ")) or len(w) < 3:
                   continue
               out.append(i); continue
           if GENUINE_END.search(w + VIS) or (w + VIS) in GENUINE:
               continue
           out.append(i)
       return out

   def fix(t):
       """Medicine: turn colon-visarga back into ':'."""
       pos = set(colon_visargas(t))
       return "".join(":" if i in pos else c for i, c in enumerate(t))


   fix_visarga = fix
   DEC_SPLIT = re.compile(r"(?<=[^\d\n.])(\d{1,3})\. (\d{1,3})(?![\d.])")
   DOMAIN_SPLIT = re.compile(r"\b([A-Za-z0-9-]+)\. (com|in|org|net|gov|co|info|edu)\b")
   WWW_SPLIT = re.compile(r"\bwww\. (?=[A-Za-z0-9])")


   def fix_dot_split(t):
       """G4: join a dot split by an inserted space inside a decimal, a clock time or a web address (3. 3, 10. 20,
       newskadaba. com, www. vknews. in). A number at the start of a line (a list item '1. 5 ...') is left alone."""
       t = WWW_SPLIT.sub("www.", t)
       for _ in range(3):                                  # karnataka. gov. in needs two passes
           t = DOMAIN_SPLIT.sub(r"\1.\2", t)
       return DEC_SPLIT.sub(r"\1.\2", t)


   def fix_over_normalised(t):
       """G4: undo the two marks of the earlier normaliser: visarga for a colon, then the dot split."""
       return fix_dot_split(fix_visarga(t))


   def medicine_g4(text):
       """The G4 rule, under the name that the harm tests look for: returns the fixed text."""
       return fix_over_normalised(text)
   ```

3. **Action:** Fix: replace each such visarga with ':' and remove the space after each such dot.

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).
   Note: here it changes nothing, because my labels mark no document with a colon-visarga as clean, so no such document is clean for both readers. This medicine is written and tested for this pack. In other Kannada packs the readers may have marked such text clean, so there it can change more gold documents. In week 2, Data A and Data B test the shared medicines on every gold set.

5. **Side effects:**
   - Sanskrit verse quoted without a danda, with one visarga word in a line (ಮತ್ಸರಃ, ಶಂಭೋಃ), is still changed to ':'. In this pack that happens in one document (cda8a7fb4c34da99, 2 visargas).
   - Some colons are missed: words in -ಶಃ or -ತಃ that were colons (ಸಾರಾಂಶಃ, ಮಧ್ಯಪ್ರದೇಶಃ), a short line with two colons (ದಿನಾಂಕಃ ... ಸ್ಥಳಃ ...), later colons in a document that also has verse, and a colon on a line with '||' in a document with '|' verse (2eafc60ffe50cd62).
   - A text that uses ಃ as a colon on purpose would be changed.
   - The dot rule would also join two sentences when one ends in a number and the next starts with a number on the same line ('... 2019ರಲ್ಲಿ 10. 20 ಜನ'). I did not see this in the pack.

## Medicine 7: A6, look-alike characters for Kannada signs

1. **Disease:** A6. My labels: 19 of 500 labelled documents. In the whole pack the rule finds 15 of 500 documents (37 characters); 15 of them are documents that I labelled A6. Text typed or converted from PDF uses a look-alike character for a Kannada sign: the Kannada digit zero ೦ (U+0CE6) or the ASCII digit 0 for the anusvara ಂ (U+0C82), as in ಇ೦ಥಾ and ಸಂಭ0ದ, and the Latin letter s for the avagraha ಽ (U+0CBD) in Sanskrit, as in ತಮೋsಧ್ಯಾಯಃ.
   Three examples:
   - `0fddd312da4d1f53` at 702: `ಸಂಭ0ದದಲ್ಲಿ` → `ಸಂಭಂದದಲ್ಲಿ` (0030 → 0C82)
   - `af897fd315bd2a8b` at 1150: `ಬ೦ದ` → `ಬಂದ` (0CE6 → 0C82)
   - `9f746e71dabdd692` at 385: `ತದ್ಧರ್ಮ೦` → `ತದ್ಧರ್ಮಂ` (0CE6 → 0C82)

2. **Medicine:** Replace a Kannada digit zero that comes right after a Kannada letter or vowel sign, and is not followed by another Kannada digit, with the anusvara. Replace an ASCII 0 that sits between a Kannada letter or vowel sign and a Kannada consonant with the anusvara. Replace a Latin s between two Kannada characters with the avagraha.

   ```python
   import re

   KN_SIGNED = "ಅ-ಹಾ-ೌ"                 # Kannada vowels, consonants and vowel signs
   ZERO_KN = re.compile(f"(?<=[{KN_SIGNED}])೦(?![೦-೯])")
   ZERO_ASCII = re.compile(f"(?<=[{KN_SIGNED}])0(?=[ಕ-ಹ])")
   LATIN_S = re.compile("(?<=[ಀ-೿])s(?=[ಀ-೿])")


   def fix_lookalikes(t):
       """A6: a Kannada digit zero (೦) or an ASCII 0 right after a Kannada letter is the anusvara (ಂ); a Latin s
       between Kannada letters is the avagraha (ಽ)."""
       t = ZERO_KN.sub("ಂ", t)
       t = ZERO_ASCII.sub("ಂ", t)
       return LATIN_S.sub("ಽ", t)


   def medicine_a6(text):
       """The A6 rule, under the name that the harm tests look for: returns the fixed text."""
       return fix_lookalikes(text)
   ```

3. **Action:** Fix.

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).

5. **Side effects:**
   - A number written in Kannada digits right after a word with no space (ಪುಟ೦) would change; I did not see this in the pack.
   - Other look-alikes are not handled: a Latin l or a digit 1 in place of a letter in OCR text (lಳಿಸುತ್ತಾ), and English fragments left by a translation engine.

## Medicine 8: C1, boilerplate lines

1. **Disease:** C1. My labels: 197 of 500 labelled documents. In the whole pack the rule finds 97 of 500 documents (257 lines); 97 of them are documents that I labelled C1. News and blog pages left their page furniture in the text: the Oneindia link block ('Don't Miss!', '- News ...', '- 2 hrs ago ...', '- #tag ...'), 'ಇದನ್ನೂ ಓದಿ:' (also read) lines, the Prajavani 'follow us on Facebook' line, share and like prompts, desk lines, comment policies, breadcrumbs, bylines and Instagram embed lines.
   Three examples:
   - `46e7b0e4e20a9f23` at 0: line `Don't Miss!` removed
   - `59482dca295d8d6a` at 1176: line `Thanks For Reading!` removed
   - `6648d8d9f388650e` at 3239: line `The views expressed in comments published on www. varthabhar ...` removed

2. **Medicine:** Remove a whole line when it matches one of these forms:
   - 'Don't Miss!'; a line that starts with '- News', '- Sports', '- Movies', '- Technology', '- Finance', '- Education', '- Lifestyle', '- Automobiles' or '- Travel'; '- <n> min ago ...' or '- <n> hrs ago ...'; '- #...';
   - 'ಇದನ್ನೂ ಓದಿ:' (also 'ಇದನ್ನೂ ಓದಿಃ' before the G4 fix); 'A post shared by ...';
   - 'ಪ್ರಜಾವಾಣಿ ಫೇಸ್ಬುಕ್ ಪುಟವನ್ನು ಫಾಲೋ ಮಾಡಿ', 'Oneindia ಬ್ರೇಕಿಂಗ್ ನ್ಯೂಸ್ ...', 'ಹೊಸದಿಗಂತ ಡಿಜಿಟಲ್ ಡೆಸ್ಕ್';
   - 'The views expressed in comments published ...', 'Thanks For Reading!', 'Like this:', 'Forgot your password?', 'To Start receiving timely alerts ...', 'Trending Topics';
   - a breadcrumb that starts with 'Home ›' or 'ಮುಖಪುಟ »'; 'Posted on <Month> <d>, <yyyy> by ...';
   - a short line (120 characters or less) that ends with 'ಶೇರ್ ಮಾಡಿ' or 'ಲೈಕ್ ಮಾಡಿ' (share, like).

   ```python
   import re

   C1_LINE = re.compile(
       r"^\s*(?:Don't Miss!?|-\s*(?:News|Sports|Movies|Technology|Finance|Education|Lifestyle|Automobiles|Travel)\s.*"
       r"|-\s*\d+\s*(?:min|mins|hr|hrs)\s+ago\s.*|-\s*#\S.*"
       r"|ಇದನ್ನೂ ಓದಿ\s*[:ಃ].*|A post shared by .*"
       r"|ಪ್ರಜಾವಾಣಿ ಫೇಸ್‌?ಬುಕ್ ಪುಟವನ್ನು\s*ಫಾಲೋ ಮಾಡಿ.*|Oneindia ಬ್ರೇಕಿಂಗ್ ನ್ಯೂಸ್.*|ಹೊಸದಿಗಂತ ಡಿಜಿಟಲ್ ಡೆಸ್ಕ್"
       r"|The views expressed in comments published .*|Thanks For Reading!?|Like this:|Forgot your password\?"
       r"|To Start receiving timely alerts.*|Trending Topics\s*:?|(?:Home|ಮುಖಪುಟ)\s*[›»].*"
       r"|Posted on \w+ \d{1,2}, \d{4} by .*|(?=.{0,120}$).*(?:ಶೇರ್|ಲೈಕ್) ಮಾಡಿ[.!]?)\s*$")


   def strip_boilerplate(t):
       """C1: remove whole boilerplate lines: Oneindia link blocks ('Don't Miss!', '- News ...', '- 2 hrs ago ...',
       '- #tag ...'), 'ಇದನ್ನೂ ಓದಿ:' (also read), follow/share/like prompts, desk lines, comment policies, breadcrumbs
       and embed lines."""
       return "\n".join(l for l in t.split("\n") if not C1_LINE.match(l))


   def medicine_c1(text):
       """The C1 rule, under the name that the harm tests look for: returns the fixed text."""
       return strip_boilerplate(text)
   ```

3. **Action:** Fix: remove those lines.

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).

5. **Side effects:**
   - A real list item that starts with '- News', '- Sports' or '- #' would be removed.
   - A short line of an article that ends with 'ಶೇರ್ ಮಾಡಿ' (an instruction in a how-to) would be removed.
   - Boilerplate inside a line is not touched: a site name after the title ('... | Udayavani - ಉದಯವಾಣಿ', '- ಸವಿ ಕನ್ನಡ ನ್ಯೂಸ್'), a site name in the dateline ('ಧಾರವಾಡ prajakiran. com :'), PDF running headers and page footers. My labels show C1 in about twice as many documents as the rule finds; the rest needs site-by-site rules.
   - An article about Instagram that quotes 'A post shared by' would lose that line.

## Medicine 9: C2, the same line twice in one document

1. **Disease:** C2. My labels: 34 of 500 labelled documents. In the whole pack the rule finds 11 of 500 documents (23 lines); 10 of them are documents that I labelled C2. News pages often repeat the opening paragraph at the end, or a heading twice.
   Three examples:
   - `dfca849b43c8a487` at 1411: line `ಮಂಗಳೂರುಃ ಕರ್ನಾಟಕದಲ್ಲಿ ತೌಕ್ತೆ ಚಂಡಮಾರುತದಿಂದ ಸಂಭವಿಸಿದ ಹಾನಿಗೆ ರಾ ...` comes back at 1411
   - `f8849202ab1a46be` at 1860: line `ಬೋಗಿಗಳುಃ ಎಸಿ-2 ಟೈರ್ ಬೋಗಿ ಒಂದು, ಎಸಿ-3 ಟೈರ್ ಬೋಗಿ ಮೂರು, 8 ಸ್ಲೀಪ ...` comes back at 1860
   - `1a60d090264d7942` at 1002: line `ಕಾರವಾರಃ ರಾಜೀವ್ ಗಾಂಧಿ ಆರೋಗ್ಯ ವಿಜ್ಞಾನಗಳ ವಿಶ್ವವಿದ್ಯಾಲಯ (ಆರ್ಜಿಯು ...` comes back at 1002

2. **Medicine:** Keep the first copy of a line that comes back word for word in the same document. Only lines of 30 characters or more count.

   ```python
   def dedupe_lines(t, min_len=30):
       """C2: keep the first copy of a line that is repeated word for word (lines of min_len characters or more)."""
       seen, out = set(), []
       for l in t.split("\n"):
           k = l.strip()
           if len(k) >= min_len and k in seen:
               continue
           seen.add(k); out.append(l)
       return "\n".join(out)


   def medicine_c2(text):
       """The C2 rule, under the name that the harm tests look for: returns the fixed text."""
       return dedupe_lines(text)
   ```

3. **Action:** Fix: remove the repeats.

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).

5. **Side effects:**
   - Song refrains, poems and lists that repeat a line on purpose lose the repeats. In this pack: the coach list of two trains that have the same coaches (f8849202ab1a46be).
   - A repeat with a small change (for example a dateline in front) is not caught, nor a repeated sentence inside a longer line. My labels show C2 in about three times as many documents.

## Medicine 10: C4, two texts joined

1. **Disease:** C4. My labels: 20 of 500 labelled documents. In the whole pack the rule finds 6 of 500 documents (6 documents); 6 of them are documents that I labelled C4. Two unrelated texts stand in one document with no boundary. In this pack: news roundups and tag pages with many unrelated teasers, two blog posts joined, and an English source story or summary joined to the end of the Kannada story. I count the English block as a joined text even when it covers the same story: it is a second text in another language with no boundary.
   Three examples:
   - `c254933676831bf1` at 1624: English block removed: `NEW DELHI: It has now become easier to transfer money t ...`
   - `a31dbea5a0d6b216` at 2351: English block removed: `Citizens of Bengaluru have opposed new property guidanc ...`
   - `539c9547508b5f0f` at 1569: English block removed: `A Supreme Court Lawyer Rajeev Kumar Ranjan has filed a  ...`

2. **Medicine:** Only the last form has a safe rule. Remove an English block at the end of the document (200 characters or more, every line over 90% Latin letters) when the text before it is Kannada (under 30% Latin letters, 200 characters or more).

   ```python
   def latin_share(s):
       k = sum(1 for c in s if "ಀ" <= c <= "೿")
       a = sum(1 for c in s if c.isascii() and c.isalpha())
       return a / (k + a) if k + a else 0.0


   def cut_english_tail(t, min_chars=200):
       """C4: remove an English block (min_chars or more, lines over 90% Latin letters) joined to the end of a
       Kannada text, such as the English source story."""
       lines = t.split("\n")
       i = len(lines)
       while i > 0 and (not lines[i - 1].strip() or latin_share(lines[i - 1]) > 0.9):
           i -= 1
       head, tail = "\n".join(lines[:i]), "\n".join(lines[i:])
       if len(tail.strip()) >= min_chars and len(head.strip()) >= 200 and latin_share(head) < 0.3:
           return head.rstrip()
       return t


   def medicine_c4(text):
       """The C4 rule, under the name that the harm tests look for: returns the fixed text."""
       return cut_english_tail(text)
   ```

3. **Action:** Fix: remove the English block.

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).

5. **Side effects:**
   - An English footer or disclaimer at the end is also removed. That is boilerplate (C1), so the change is still right, but it is not C4 (three documents in this pack).
   - Roundups and tag pages of unrelated Kannada stories are not caught. My labels show C4 in 17 documents and the rule finds 3 of them; the rest needs a reader or a topic-shift model.
   - A Kannada article that ends with a long English quote would lose the quote.

## Medicine 11: C3, the text stops in the middle of a sentence

1. **Disease:** C3. My labels: 32 of 500 labelled documents. In the whole pack the rule finds 22 of 500 documents (22 documents); 20 of them are documents that I labelled C3. The document was cut: the last line is prose that stops without a sentence end.
   Three examples:
   - `9044eb5731ca5bbb` at 568: the last line stops at `... ಪ್ತ ವಿದ್ವತ್ತನ್ನು ವರ್ಣಿಸಿದುದರ ಫಲವೇ ಅದೆಂದೂ`; the rule removes `⏎ಪುರುಷೋತ್ತಮನು ಆ ವರ್ಷ ಆ ತರಗತಿಯಿಂದ ತೇರ್ಗಡೆ ...`
   - `911d5a63a36beb09` at 1231: the last line stops at `... ಿರಲುತತ್ಪಾದಸೇವಿತರಾದಶಿ ವತ್ಸಗೋತ್ರದಆಪಸ್ತಂಭಸೂ`; the rule removes `⏎ವಿಜಯಾಭ್ಯುದಯ ಶಾಲಿವಾಹನಶಕವ ರ್ಷಂಗಳು ೧೬೦ ರಮೇ ...`
   - `7f58502a21c86228` at 6727: the last line stops at `... ಂಗಳಿನೋಡಿ ಮರಣಭಯಗ್ರಸ್ತನಾಗಿ ಕಂಸನು ಚಿಂತೆಯಿಂದ`; the rule removes `⏎ರು |೨೫| ಕಂಸನು ರಾಮಕೃಷ್ಣರಿಂದ ಮಾಡಲ್ಪಟ್ಟ ರಾ ...`

2. **Medicine:** When the text does not end with a sentence end (. ? ! । ॥ | a closing quote or bracket, ':', a digit), and its last line has 40 characters or more, cut the last line back to its last full stop. When that line has no full stop, remove the line.

   ```python
   SENTENCE_END = set(".?!।॥|\"'”’)»…:ಃ")


   def cut_unfinished_end(t, min_line=40):
       """C3: when the last line is prose (min_line characters or more) that stops without a sentence end, cut it
       back to its last full stop, or remove the line when it has none."""
       s = t.rstrip()
       if not s or s[-1] in SENTENCE_END or s[-1].isdigit():
           return t
       last = s.split("\n")[-1]
       if len(last) < min_line:
           return t
       cut = max(last.rfind(c) for c in ".?!।")
       return (s[: len(s) - len(last)] + (last[: cut + 1] if cut >= 0 else "")).rstrip()


   def medicine_c3(text):
       """The C3 rule, under the name that the harm tests look for: returns the fixed text."""
       return cut_unfinished_end(text)
   ```

3. **Action:** Fix: remove the unfinished sentence.

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).

5. **Side effects:**
   - A last line that is a list or an address with no full stop is cut (a press-office address in c713689df252717f; a keyword list in 7b1751ffb7f20ff0).
   - A cut that ends on a full stop by chance, a dangling heading, or a short last line is not caught.
   - A text that starts in the middle of a sentence is not touched.

## Medicine 12: D3, Kannada and another language mixed

1. **Disease:** D3. My labels: 23 of 500 labelled documents. The rule changes nothing. English phrases or sentences inside Kannada sentences, and quoted Sanskrit or Arabic. This is how people write; the brief says label it, do not judge it.
   Three examples from my labels:
   - `5162614ed46214d1` at 1199: 'CBSE Class 10 Board Exam 2021 ಅನ್ನು'
   - `c7dec812322736d6` at 6735: 'وما أرسلناك'
   - `cd57b4f99f029161` at 875: 'Ecstatic to announce the arrival of our Angelic Baby Girl'

2. **Medicine:** No medicine. The document is kept as it is.

   ```python
   def keep_mixed(t):
       """D3: no medicine. Kannada-English mixing is natural; the brief says label it, do not judge it."""
       return t


   def medicine_d3(text):
       """The D3 rule, under the name that the harm tests look for: returns the text unchanged."""
       return keep_mixed(text)
   ```

3. **Action:** Keep (no change).

4. **Harm test:** on the gold set (103 documents) it changes 0 and drops 0: 0.0%. Pass (at most 1 document or 1%, whichever is larger).

5. **Side effects:**
   - None: the rule changes nothing. A mixed document that also has another disease is handled by the medicine for that disease.
