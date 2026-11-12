# Medicine sheet: ind-kn-sangraha-s (millermuttu)

Pack: 500 documents, Kannada, source sangraha-synthetic (Wikipedia pages machine-translated into Kannada).
Labels: 359 clean, 141 fix, 0 drop.

Diseases found more than five times: B2 (43), C3 (30), A6 (30), C1 (24), D3 (16), B3 (7). D4 and G1 (5 each) and
C2, C4, B4, A3 are at or below five, so they get no medicine.

All the code is in this file: the `python` blocks, read from top to bottom, make one script. The blocks are the
import below and the six medicines. The harm test is Data B's tool; it runs this file as it is:

```
python3 teams/02-data-b/tools/harm_test_indic.py --medicine medicine.md --pack ind-kn-sangraha-s.parquet \
    --gold-dir teams/02-data-b/gold
```

```python
import re
```

## The harm test, in one table

Gold set: the gold set of this pack, `teams/02-data-b/gold/ind-kn-sangraha-s_gold.csv` (Data B gold sets rebuilt
31 Oct, PR #161): 27 documents, each marked clean by two readers. All 27 are in this pack. A rule fails if it changes
or drops more than 1% of the gold set or more than 1 document, whichever is more (DISEASES.md section 4 and the
TSAI rule for small gold sets): here at most 1 of 27.

Data B's tool (`harm_test_indic.py`) on this file:

```
gold set: 27 documents in 1 pack(s) (ind-kn-sangraha-s 27)
a rule may change or drop at most 1 of 27 documents (1% or 1, whichever is more)
rule           changed dropped  percent  joiners  form   result
B2                   0       0    0.00%  ok      ok     PASS
B3                   0       0    0.00%  ok      ok     PASS
A6                   0       0    0.00%  ok      ok     PASS
C1                   0       0    0.00%  ok      ok     PASS
C3                   0       0    0.00%  ok      ok     PASS
D3                   0       0    0.00%  ok      ok     PASS
ALL IN ORDER         0       0    0.00%  ok      ok     PASS
result: PASS
```

As a second, wider check, I also ran each medicine on my own 359 clean rows. That set has one reader only, so it is a
proxy and not gold.

| Medicine | Disease | Gold changed | Gold dropped | Result | My clean rows changed | Labelled docs it fixes | Pack docs it touches |
|---|---|---|---|---|---|---|---|
| M1 | B2 | 0 / 27 | 0 | PASS | 0 / 359 | 43 / 43 | 46 |
| M2 | B3 | 0 / 27 | 0 | PASS | 0 / 359 | 3 / 7 | 3 |
| M3 | A6 | 0 / 27 | 0 | PASS | 0 / 359 | 9 / 30 | 9 |
| M4 | C1 | 0 / 27 | 0 | PASS | 5 / 359 | 7 / 24 | 22 |
| M5 | C3 | 0 / 27 | 0 | PASS | 3 / 359 | 18 / 30 | 26 |
| M6 | D3 | 0 / 27 | 0 | PASS (no text change) | 0 / 359 | n/a | 0 |

I read each of the 8 changes in my clean rows (see the side effects of M4 and M5). Each one removes text that I should
have labelled C1 or C3. They are misses in my label sheet, not harm.

## Medicine 1: translated HTML tags (B2)

1. **Disease:** B2, 43 documents. The translation step turned the tags into Kannada letters.
   - `ff6d56a4f0b67604`: `<ಐ. ಡಿ. 1>` at offset 626 (this was `<ID 1>`)
   - `3a69a945a1b7aeaa`: `<ಬಿ. ಆರ್.>` at offset 573 (this was `<br>`)
   - `5f6f044745aeb4f4`: `<>` and `</Â>` at offset 219 and 222 (7 times each)
   - Also without brackets: `2d9a373d2ef00c46`: `ಐ. ಡಿ. 1` at offset 5796.
2. **Medicine:** replace a translated or real `<br>` with a newline. Delete `<ID n>` in its Kannada form, with or
   without brackets, and the space before it. Delete any other tag that starts with a Latin letter, the translated
   `<ರಿಫರ್ ...>` reference tag, and `<>`.
   ```python
   TAG_ID = re.compile(r" ?<?ಐ\. ಡಿ\. \d+>?")
   TAG_BR = re.compile(r"<ಬಿ\.? ?ಆರ್\.?>|<br\s*/?>", re.I)
   TAG_ANY = re.compile(r"</?(?:[A-Za-zÀ-ÿ][^<>\n]{0,40}|ರಿಫರ್[^<>\n]{0,80})>|<>")
   def m1_tags(s):
       s = TAG_BR.sub("\n", s)
       return TAG_ANY.sub("", TAG_ID.sub("", s))
   ```
3. **Action:** fix the text.
4. **Harm test:** gold 0 changed, 0 dropped of 27. PASS. My clean rows: 0 of 359.
5. **Side effects:** `<ಐ. ಡಿ. 1>` stood for a name or a number that the source hid. Deleting it can leave a sentence
   with a gap ("... was born in ."). The medicine also deletes `<unk>` (that is M2's job too, so no harm). A real
   Kannada text that writes `ಐ. ಡಿ. 2` for "ID 2" (an ID card number) would lose it; I saw no such case.

## Medicine 2: ghost tokens (B3)

1. **Disease:** B3, 7 documents labelled. Only 3 have a real ghost token, `<unk>`:
   - `a84cbd8f664d1816`: `<unk>` 11 times, first at offset 753
   - `76ff156acd160ee4`: `<unk>` at offset 217 and 1074
   - `d5133441c9d74b4f`: `<unk>` at offset 37 and 58

   The other 4 rows (`f1161ea20322b1f3` `<`, `2b65959fd113626f` `?`, `652430783641cf74` `? =`, `145f7cfbe62c98c6` `!`)
   are stray punctuation, not chat markers. They are under the limit of five, so they get no medicine here.
2. **Medicine:** delete the unknown token and the usual chat-template markers.
   ```python
   GHOST = re.compile(r"<unk>|<\|[a-z_]+\|>|\[/?INST\]|</?s>|</?think>")
   def m2_ghost(s):
       return GHOST.sub("", s)
   ```
3. **Action:** fix the text. `<unk>` replaced a character that the tokenizer of the translation model did not know,
   so the word around it stays damaged.
4. **Harm test:** gold 0 changed, 0 dropped of 27. PASS. My clean rows: 0 of 359.
5. **Side effects:** a text about HTML or about language models that quotes `<s>` or `<|endoftext|>` loses the quote.

## Medicine 3: "i.e." and "e.g." half translated (A6)

1. **Disease:** A6, 30 documents. Latin letters glued to Kannada letters in one word. There are three kinds:
   - half-translated abbreviations: `54f770edbfb0f27e`: `(i.ಇ.ಪಳೆಯುಳಿಕೆ)` at offset 490; `7213ef84e617ab3c`:
     `(e.ಜಿ.` at offset 876; `4fde496efbb5da8b`: `(i.ಇ.,` at offset 316
   - Roman numerals or acronyms with a Kannada case ending: `0e72261397f357cd`: `xiiಗೆ` at offset 115;
     `572e66f3cdcbcedf`: `GMTಯಲ್ಲಿ` at offset 501
   - Latin technical names with a Kannada word: `bddb7db5986a353f`: `dbus-ಜಾವಾ` at offset 708
2. **Medicine:** only the first kind is damage. Replace the half-translated `i.e.` with `ಅಂದರೆ` and `e.g.` with `ಉದಾ.`.
   The second and third kinds are how Kannada writers add a case ending to a foreign name. Leave them.
   ```python
   HALF_IE = re.compile(r"\bi\.\s?ಇ\.")
   HALF_EG = re.compile(r"\be\.\s?ಜಿ\.")
   def m3_half_translated(s):
       return HALF_EG.sub("ಉದಾ.", HALF_IE.sub("ಅಂದರೆ", s))
   ```
3. **Action:** fix the text.
4. **Harm test:** gold 0 changed, 0 dropped of 27. PASS. My clean rows: 0 of 359. It fixes 9 of the 30 A6 documents.
5. **Side effects:** a list item `i.` followed by a sentence that begins with `ಇ.` would change; I saw none. Other
   half-translated initials (`f.ಸಿ.` for "F.C." in `b497ade9ed6f64c3`) are not fixed, because the right Kannada form
   depends on the name.

## Medicine 4: reference footer and advertisement lines (C1)

1. **Disease:** C1, 24 documents.
   - `248d753341105364`: `ಉಲ್ಲೇಖಗಳು.\nಉಲ್ಲೇಖಗಳು\nಮೂಲಗಳು` (References, References, Sources) at offset 565
   - `2237fbd5cc07cfb8`: `ಉಲ್ಲೇಖಗಳು.\nಉಲ್ಲೇಖಗಳು\nಗ್ರಂಥಸೂಚಿ` (References, Bibliography) at offset 6479
   - `795cf2909be9d1f6`: `ಜಾಹೀರಾತು` (Advertisement) as its own line at offset 4668, 4708, 4749
2. **Medicine:** find the first line that is only a footer heading: References, Sources, Notes, Bibliography,
   External links, See also. If it is in the second half of the document, cut the document there. Delete every line
   that is only `ಜಾಹೀರಾತು`.
   ```python
   FOOTER = re.compile(r"^(?:ಉಲ್ಲೇಖಗಳು|ಮೂಲಗಳು|ಟಿಪ್ಪಣಿಗಳು|ಗ್ರಂಥಸೂಚಿ|ಬಾಹ್ಯ ಸಂಪರ್ಕಗಳು|ಇದನ್ನೂ ನೋಡಿ)\.?[ \t]*$", re.M)
   AD_LINE = re.compile(r"^[ \t]*ಜಾಹೀರಾತು[ \t]*\n?", re.M)
   def m4_footer(s):
       m = FOOTER.search(s)
       if m and m.start() > len(s) // 2:
           s = s[: m.start()].rstrip()
       return AD_LINE.sub("", s)
   ```
3. **Action:** fix the text.
4. **Harm test:** gold 0 changed, 0 dropped of 27. PASS. My clean rows: 5 of 359 changed. I read all 5. Two
   (`7316a3d779366b1a`, `8772f7c961f3c48f`) end in an empty `ಉಲ್ಲೇಖಗಳು.` heading, `ed7cfe412cf5a9bb` ends in
   "translated from the German Wikipedia", `7696c91439e39dd0` and `ea7e1afd07060b11` end in a link or reference list.
   All 5 are footers that I missed when labelling.
5. **Side effects:** it fixes only 7 of the 24 C1 documents. The other 17 end in lists with a content heading
   (Honours `ಗೌರವಗಳು.`, track lists, cast lists). Those lists are content of the page, so the medicine keeps them. A
   footer in the first half of a short document stays; a "Notes" section that holds real text is cut.

## Medicine 5: dangling list intro at the end (C3)

1. **Disease:** C3, 30 documents. Most truncated documents end with a sentence that announces a list, and the list is
   missing. The translation wrote the colon as the visarga `ಃ`.
   - `1428f9e8314543c8`: `ಪುಸ್ತಕಗಳು ಮತ್ತು ಪ್ರಬಂಧಗಳು ಹೀಗಿವೆಃ` ("his books and essays are as follows:") at offset 560
   - `ee2758858961a338`: `ಜನರು ಅದರ ಮೇಯರ್ ಆಗಿದ್ದರುಃ` at offset 9312
   - `378c502cc7ad043b`: `ಈ ಕೆಳಗಿನವುಗಳನ್ನು ಒಳಗೊಂಡಿವೆಃ` at offset 406
2. **Medicine:** if the document ends with `ಃ` or `:`, cut its last sentence (back to the last newline or the last
   `. `). If nothing is left, drop the document.
   ```python
   def m5_dangling_intro(s):
       body = s.rstrip()
       if not body.endswith(("ಃ", ":")):
           return s
       cut = max(body.rfind("\n"), body.rfind(". ") + 1)
       return body[:cut].rstrip() + "\n" if cut > 0 else True
   ```
3. **Action:** fix the text (drop only a document that is one dangling sentence).
4. **Harm test:** gold 0 changed, 0 dropped of 27. PASS. My clean rows: 3 of 359 changed (`523fee1068dc3fa9`,
   `5182f57e468c0d70`, `db80897e2760a8ad`). All 3 end with a list intro and no list: C3 that I missed.
5. **Side effects:** it fixes 18 of the 30 C3 documents. The other 12 stop in the middle of a word or a list item
   (`2ffa1db3ff911b53`, `6a8a83b833862e25`); no safe rule finds the end of the text there. The visarga `ಃ` is also a
   real Kannada letter (`ದುಃಖ`, `ಅಂತಃ`). A document that really ends with such a word would lose its last sentence. In
   this pack no document does.

## Medicine 6: mixed language (D3)

1. **Disease:** D3, 16 documents. Foreign words inside Kannada text.
   - `cff540231e8e8ed1`: Russian `орлиное гнеzdо` at offset 51
   - `309c6300b2a22783`: Greek `αλεσιρεσι αρεσιρεσι` at offset 4207
   - `a0ee8f67d70aa82b`: Japanese romanisation `ōzeki` at offset 975
2. **Medicine:** no text change. DISEASES.md says: label mixed language, do not judge it. The foreign words are names
   and titles that the page quotes. The function measures the share of letters that are neither Kannada nor Latin,
   so the mixture team can see it.
   ```python
   LETTER = re.compile(r"[^\W\d_]", re.U)
   NOT_KN_LATIN = re.compile(r"[^\W\d_a-zA-Zಀ-೿]", re.U)
   def m6_foreign_ratio(s):
       n = len(LETTER.findall(s))
       return len(NOT_KN_LATIN.findall(s)) / n if n else 0.0
   def medicine_d3(s):
       return s  # keep the text; m6_foreign_ratio is the measure
   ```
   In the 16 D3 documents the share is at most 0.054 (5.4%). No document is mostly foreign.
3. **Action:** keep the text. Record the ratio.
4. **Harm test:** gold 0 changed, 0 dropped of 27. PASS (the rule keeps every text).
5. **Side effects:** none on the text. The ratio does not see Latin words (English, German) because Latin is normal in
   this pack (names, units, acronyms).
