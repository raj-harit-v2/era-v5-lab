# Medicine sheet: sci-finepdfs (aneeshads)

> Written by `make_medicines_md.py` from `labels.csv` on 2026-10-28 23:18. Rows labelled: 100 of 500 (all read in full). The code of every medicine is in `medicines_sci.py`; each `cure_<code>(text)` returns the new text, or `("drop", "")`. **Harm test:** each medicine runs on the Data A gold set for sci-finepdfs (`teams/01-data-a/gold/sci-finepdfs_gold.csv`, 26 documents that two readers marked clean). A medicine fails when it changes or drops more than 1% of the gold set; with 26 documents, **one changed document is already 3.8%**, so a medicine passes only if it changes and drops nothing.

A disease gets a section when it is found in more than 5 documents (C2, F1, B5, C1, A6, D3). A1 and B2 are in 5 or fewer documents but more than 5 times, so they get a section too, at the end.

## Medicine 1: C2, repeated lines

1. **Disease:** C2 (repeated lines), found in 39 documents (2643 times) in the 100 labelled rows. Three examples:
   - `8c1aed2f8a439b91` @3029: `MIT Introduction to Deep Learning` (8 copies; the medicine keeps the first and removes 7)
   - `6324a2bb8fae9275` @34824: `Disulfide minimization` (4 copies; the medicine keeps the first and removes 3)
   - `135ae306b27ebd17` @4491: `**Power Dissipation (Note 2)**` (6 copies; the medicine keeps the first and removes 5)
2. **Medicine:** A line of 15 characters or more, with at least two words, that appears 4 or more times in one document is a running page header or footer: keep the first copy and remove the later copies. Lines with a LaTeX backslash and Markdown table rows are never touched, because `\begin{cases}` and table separators repeat on purpose. A line that appears 2 or 3 times is kept: the gold set has real text repeated 2 and 3 times (a title, a reference, a caption).

   ```python
   import re
   from collections import Counter

   C2_MIN_LEN = 15

   C2_MIN_COPIES = 4

   C2_WORD = re.compile(r"[A-Za-z]{2,}")

   def c2_is_header(line):
       s = line.strip()
       return (len(s) >= C2_MIN_LEN
               and len(C2_WORD.findall(s)) >= 2      # words, not a rule of underscores or a number row
               and "\\" not in s                     # LaTeX: \begin{cases} ... repeats on purpose
               and not s.startswith("|"))

   def cure_c2(text):
       lines = text.split("\n")
       counts = Counter(l.strip() for l in lines)
       headers = {s for s, n in counts.items() if n >= C2_MIN_COPIES and c2_is_header(s)}
       if not headers:
           return text
       seen, out = set(), []
       for line in lines:
           s = line.strip()
           if s in headers:
               if s in seen:
                   continue
               seen.add(s)
           out.append(line)
       return "\n".join(out)
   ```

3. **Action:** Fix the text.
4. **Harm test:** on the gold set (26 documents) it changes 0 and drops 0: 0 of 26 = 0.00%, **pass**.
   On the 39 labelled documents with C2 it acts on 23 (it misses `f94ced321243b853`, `ec7cb30bfd82a1f0`, `5a17c561359e5ad0`, `b64c51d59247a36c`, `63e0a8b8fa721ac1` and 11 more). On the whole pack (500 documents) it changes 94 and drops 0.
5. **Side effects:**
   - Real content that is repeated 4 or more times is removed: a roll-call vote line (`Approved: DeForest, Grandy, …` 29 times in `50cc681aabd3d82b`), the role line under each signature (`Member of Congress` 243 times in `507d7cf0978d22e4`), and form fields with the same value (`Not Sustained: 0` in `39857b0ef2904033`).
   - A table footnote repeated under each table (`* Relative standard error of more than 30%` in `7700a268afd083e8`) is kept only under the first table.
   - Repeats of 2 or 3 copies stay, and a header that the PDF tool changed slightly on each page (a page number inside it) is not found.
   - Seen on documents that I labelled `clean` (each is either a side effect or a document that is not really clean):
     - `d1b2e193abc4a5f3` @341: `Harrisburg, PA  17120` (4 copies; the medicine keeps the first and removes 3)
     - `39857b0ef2904033` @3096: `Not Sustained: 0` (4 copies; the medicine keeps the first and removes 3)
     - `7700a268afd083e8` @49342: `* Relative standard error of more than 30%` (5 copies; the medicine keeps the first and removes 4)
     - `5cd969382b955d84` @19909: `The Continental Insurance Company` (6 copies; the medicine keeps the first and removes 5)

## Medicine 2: F1, personal data

1. **Disease:** F1 (personal data), found in 23 documents (171 times) in the 100 labelled rows. Three examples:
   - `0d51f1448091e52b`: phone number at offset 588; the medicine masks it as `<PHONE>`
   - `ec7cb30bfd82a1f0`: phone number at offset 11649; the medicine masks it as `<PHONE>`
   - `89810040c152f744`: phone number at offset 4439; the medicine masks it as `<PHONE>`
2. **Medicine:** Mask a phone or fax number with `<PHONE>` when a phone word (tel, tél, telephone, phone, ph, fax, cell, mobile, call) comes at most 25 characters before it, on the same line or at the end of the line above. The number has 7 to 15 digits written in groups. A number that ends like an amount (`1.23 4567.89`) is not masked. E-mail addresses are already replaced upstream by FinePDFs (`firstname.lastname@example.org`), so the medicine leaves them.

   ```python
   import re

   F1_PHONE = re.compile(
       r"(?P<key>\b(?:tel|t[ée]l[ée]phone|telephone|phone|ph|fax|cell|mobile|call)\b[^\d\n]{0,25}?\n?)"
       r"(?P<num>\+?\(?\d[\d().\s-]{5,22}\d)", re.I)

   def f1_is_phone(num):
       digits = re.sub(r"\D", "", num)
       return (7 <= len(digits) <= 15
               and re.search(r"[\s.()-]", num)               # written in groups
               and not re.search(r"\d\.\d{2}$", num))

   def cure_f1(text):
       def mask(m):
           return m.group("key") + "<PHONE>" if f1_is_phone(m.group("num")) else m.group(0)
       return F1_PHONE.sub(mask, text)
   ```

3. **Action:** Fix the text (mask the number, keep the document).
4. **Harm test:** on the gold set (26 documents) it changes 0 and drops 0: 0 of 26 = 0.00%, **pass**.
   On the 23 labelled documents with F1 it acts on 21 (it misses `eb1ad9ea3743f0ec`, `0178465b09de61b6`). On the whole pack (500 documents) it changes 81 and drops 0.
5. **Side effects:**
   - Office, switchboard and helpline numbers of organisations are masked too; they are not personal data. This costs little text.
   - A number with no phone word near it (`For more information: 555 …`, a number in a table column headed Phone) is not masked.
   - A labelled `phone number` that is not one (a budget line `Phone` + an amount in `0178465b09de61b6`, a `dial …` step in a cognitive-science example in `031d526e862d6f22`) is rightly kept.
   - Seen on documents that I labelled `clean` (each is either a side effect or a document that is not really clean):
     - `5cd969382b955d84`: phone number at offset 309; the medicine masks it as `<PHONE>`

## Medicine 3: B5, broken Markdown or LaTeX

1. **Disease:** B5 (broken Markdown or LaTeX), found in 18 documents (402 times) in the 100 labelled rows. Three examples:
   - `80c340aef304a24c` @21835: `\footnote{“...considerable royalties amounting to many thousands of dollars were…` → ` (“...considerable royalties amounting to many thousands of dollars were accumul…`
   - `d7a3e129dcd9c041` @2392: `\footnote{The penalties set forth in the Secretary’s Petition for Assessment of …` → ` (The penalties set forth in the Secretary’s Petition for Assessment of Penalty …`
   - `ae0c958288200e55` @4087: `\footnote{See Appendix 7: EC Common Position 2004/694/CFSP, 11 October 2004; and…` → ` (See Appendix 7: EC Common Position 2004/694/CFSP, 11 October 2004; and Appendi…`
2. **Medicine:** A LaTeX `\footnote{…}` command that the PDF tool left in the prose becomes the footnote text in brackets: `…dollars.\footnote{The penalties…}` → `…dollars. (The penalties…)`. Nested braces are counted; an unclosed `\footnote{` loses only the command. Inline math (`$x$`, `\( r \)`), footnote markers `\(^1\)` and `\textsuperscript{1}` are left alone: the gold set has them in 6 of 26 documents, so a medicine that rewrites them fails the harm test.

   ```python
   def cure_b5(text):
       out, i = [], 0
       while True:
           j = text.find("\\footnote{", i)
           if j < 0:
               out.append(text[i:])
               return "".join(out)
           out.append(text[i:j])
           k, depth = j + len("\\footnote{"), 1
           while k < len(text) and depth:
               depth += {"{": 1, "}": -1}.get(text[k], 0) if text[k - 1] != "\\" else 0
               k += 1
           if depth:                                    # never closed: keep the words, drop the command
               out.append(" ")
               i = j + len("\\footnote{")
           else:                                        # \footnote{X} -> " (X)"
               out.append(" (" + text[j + len("\\footnote{"):k - 1].strip() + ")")
               i = k
   ```

3. **Action:** Fix the text.
4. **Harm test:** on the gold set (26 documents) it changes 0 and drops 0: 0 of 26 = 0.00%, **pass**.
   On the 18 labelled documents with B5 it acts on 4 (it misses `6324a2bb8fae9275`, `9c8350f1f10c7755`, `cb2103a228e1c9e0`, `135ae306b27ebd17`, `6bbcabe06c799acf` and 9 more). On the whole pack (500 documents) it changes 15 and drops 0.
5. **Side effects:**
   - A footnote in brackets breaks the sentence it was attached to when it is long.
   - Most labelled B5 evidence is `\(^2\)` markers and `$…$` math, which the gold readers accepted as clean; the medicine does not touch them, so it misses those documents on purpose.
   - A `\footnote` in a real LaTeX listing (a tutorial about LaTeX) would also be rewritten.

## Medicine 4: C1, boilerplate

1. **Disease:** C1 (boilerplate), found in 12 documents (66 times) in the 100 labelled rows. Three examples:
   - `6bbcabe06c799acf` @2514: `Copyright, 1935, by the American College of Dentists` (the medicine removes the line)
   - `6dc622390a3f7207` @239706: `© 1988-2015 ACORD CORPORATION. All rights reserved.` (the medicine removes the line)
   - `b01bfbf64f278c75` @76520: `COPYRIGHT © 2017` (the medicine removes the line)
2. **Medicine:** Remove a line of 200 characters or less that starts with `Copyright` (or `©Copyright`), or that contains `All rights reserved`, or the page navigation `First page Prev. page`. A line that only starts with `©` is kept: the gold set has image credits (`© Ympäristöhallinto`) and a publisher line (`© 2000 Paperi ja Puu Oy`).

   ```python
   import re

   C1_LINE = re.compile(r"^\W{0,3}(?:©\s*)?copyright\b|all rights reserved|first page\s+prev\.? page", re.I)

   C1_MAX_LINE = 200

   def cure_c1(text):
       lines = text.split("\n")
       return "\n".join(l for l in lines if len(l) > C1_MAX_LINE or not C1_LINE.search(l))
   ```

3. **Action:** Fix the text.
4. **Harm test:** on the gold set (26 documents) it changes 0 and drops 0: 0 of 26 = 0.00%, **pass**.
   On the 12 labelled documents with C1 it acts on 5 (it misses `1c686de5116ab261`, `b64c51d59247a36c`, `12379eff30e2aa1c`, `031d526e862d6f22`, `d6dcd8fca4d05d49` and 2 more). On the whole pack (500 documents) it changes 27 and drops 0.
5. **Side effects:**
   - A licence line that the reader needs (`© Creative Commons License` and the licence name) is kept when it has no `Copyright` word, and removed when it has one.
   - Product promos, brand names and URL lists (most of the labelled C1 evidence that the medicine misses) need a per-site list; one pattern list cannot find them without hitting the gold set.
   - A short line in a legal text that starts with the word Copyright (`Copyright infringement is …`) is removed.

## Medicine 5: A6, wrong or mixed script

1. **Disease:** A6 (wrong or mixed script), found in 9 documents (121 times) in the 100 labelled rows. Three examples:
   - `f5faeb5d20b73087` @11498: `raise立ts` (U+7ACB) → `raisets`
   - `12e943fb710cab5b` @882: `smooth抽吸` (U+62BD U+5438) → `smooth`
   - `6324a2bb8fae9275`: labelled `A6 L31 @7557: Latin word contains Greek letter Greek Small Letter Alpha (U+03B1), which lo…`; the medicine keeps it
2. **Medicine:** (1) In a word that mixes Latin and Cyrillic letters, write the word in the script of most of its letters: Cyrillic letters become Latin with the Serbian/Macedonian transliteration (`vrтoglavo` → `vrtoglavo`), and a Latin look-alike in a Cyrillic word becomes Cyrillic (`подготовкa` → `подготовка`). (2) A Chinese, Japanese or Korean character glued to a Latin word is removed when such characters are 1% or less of the letters (`smooth抽吸` → `smooth`). Greek letters inside Latin words (`μg`, `Cα`, `PGF2α`, `Aβ42`) are correct scientific notation and are never changed; the gold set has them.

   ```python
   import regex

   A6_WORD = regex.compile(r"[\p{L}\p{M}]+")

   A6_CJK = regex.compile(r"[\p{sc=Han}\p{sc=Hiragana}\p{sc=Katakana}\p{sc=Hangul}]+")

   A6_CJK_SHARE = 0.01

   A6_LAT_TO_CYR = dict(zip(map(ord, "aceopxyjsABCEHKMOPTX"), "асеорхујѕАВСЕНКМОРТХ"))

   A6_CYR_TO_LAT = dict(zip(map(ord, "абвгдђежзијклљмнњопрстћуфхцчџшАБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШіІѕЅ"),
                            ["a", "b", "v", "g", "d", "đ", "e", "ž", "z", "i", "j", "k", "l", "lj", "m", "n", "nj",
                             "o", "p", "r", "s", "t", "ć", "u", "f", "h", "c", "č", "dž", "š",
                             "A", "B", "V", "G", "D", "Đ", "E", "Ž", "Z", "I", "J", "K", "L", "Lj", "M", "N", "Nj",
                             "O", "P", "R", "S", "T", "Ć", "U", "F", "H", "C", "Č", "Dž", "Š", "i", "I", "s", "S"]))

   def a6_fix_word(m):
       w = m.group()
       lat = len(regex.findall(r"\p{sc=Latin}", w))
       cyr = len(regex.findall(r"\p{sc=Cyrillic}", w))
       if not lat or not cyr or lat == cyr:
           return w
       if cyr > lat:
           fixed = regex.sub(r"\p{sc=Latin}", lambda c: c.group().translate(A6_LAT_TO_CYR), w)
           if not regex.search(r"\p{sc=Latin}", fixed):
               return fixed                              # подготовкa -> подготовка
       return w.translate(A6_CYR_TO_LAT)

   def cure_a6(text):
       if regex.search(r"\p{sc=Cyrillic}", text):
           text = A6_WORD.sub(a6_fix_word, text)
       cjk = sum(len(r) for r in A6_CJK.findall(text))
       if cjk and cjk / max(1, len(regex.findall(r"\p{L}", text))) <= A6_CJK_SHARE:
           text = regex.sub(r"(?<=\p{sc=Latin})" + A6_CJK.pattern + r"|" + A6_CJK.pattern + r"(?=\p{sc=Latin})",
                            "", text)                    # raise立ts -> raisets, smooth抽吸 -> smooth
       return text
   ```

3. **Action:** Fix the text.
4. **Harm test:** on the gold set (26 documents) it changes 0 and drops 0: 0 of 26 = 0.00%, **pass**.
   On the 9 labelled documents with A6 it acts on 2 (it misses `6324a2bb8fae9275`, `cb2103a228e1c9e0`, `135ae306b27ebd17`, `2934f10a13faaf17`, `aa241f145eca058d` and 2 more). On the whole pack (500 documents) it changes 6 and drops 0.
5. **Side effects:**
   - Removing the glued character leaves a broken word when it stood for letters (`raise立ts` → `raisets`; the source probably had `plants`).
   - Macedonian `и` in a Latin-majority word becomes `i`, which is right for Serbian Latin and wrong for a Macedonian name.
   - Most labelled A6 rows are Greek letters in units and gene names (`100 μA`, `IL-1β`); the medicine keeps them on purpose, so those rows count as misses.

## Medicine 6: D3, mixed language

1. **Disease:** D3 (mixed language), found in 8 documents (59 times) in the 100 labelled rows. Three examples:
   - `28bb6f385b19eda4`: 64% of the letters are not English, starting `Yrittäjälähtöisiä parkkiruutuja Helsinkiin!⏎⏎San Franciscoss…`; the medicine drops it
   - `f26a6a8bd745c1a2`: labelled `D3: "(Asociación Costarricense para el Estudio e Intervención en Drogas, ACEID)" at offset…`; the medicine keeps it
   - `12e943fb710cab5b`: labelled `D3: "抽吸" at offset 882`; the medicine keeps it
2. **Medicine:** D3 is natural in science PDFs (an organisation's Spanish name, a Chinese table header), so the medicine keeps mixed text. It drops a document only when more than 50% of its letters are in paragraphs that are not English: a paragraph is not English when most of its letters are not Latin script, or when it has at least 2 function words of another language (de, fr, es, it, fi, lt, lv, sr/hr, sv, nl) and more than twice as many as English function words.

   ```python
   import re
   import regex

   D3_EN = set("the of and to in is that for on with as by are be this it from or at an was which not have has "
               "were their its can will these but been more also all would there they".split())

   D3_OTHER = set(("der die das und ist nicht mit von zu den ein eine dem auf für sich auch "
                   "le la les des est une dans pour pas que qui du au sur avec sont "
                   "el los las es una por para con del se como más su "
                   "il di che della per non sono gli nel alla "
                   "ja on ei että ovat oli kanssa myös tai kuin sekä "
                   "ir yra kad su iš ar buvo nuo bei "
                   "un ar uz par kas tiek "
                   "je na za od da su kao ili ali biti "
                   "och att det som är för med på av inte "
                   "het een van zijn niet voor met ook").split())

   D3_DROP_SHARE = 0.5

   def d3_foreign_share(text):
       total = foreign = 0
       for para in re.split(r"\n\s*\n", text):
           letters = regex.findall(r"\p{L}", para)
           if not letters:
               continue
           non_latin = sum(1 for c in letters if not regex.match(r"\p{sc=Latin}", c))
           words = [w.lower() for w in regex.findall(r"\p{L}+", para)]
           en = sum(w in D3_EN for w in words)
           other = sum(w in D3_OTHER for w in words)
           total += len(letters)
           if non_latin / len(letters) > 0.5 or (other >= 2 and other > 2 * en):
               foreign += len(letters)
       return foreign / max(1, total)

   def cure_d3(text):
       return ("drop", "") if d3_foreign_share(text) > D3_DROP_SHARE else text
   ```

3. **Action:** Drop the document (when more than half of it is not English); otherwise keep it.
4. **Harm test:** on the gold set (26 documents) it changes 0 and drops 0: 0 of 26 = 0.00%, **pass**.
   On the 8 labelled documents with D3 it acts on 1 (it misses `f26a6a8bd745c1a2`, `12e943fb710cab5b`, `7c48e04e2f71eefa`, `d46a15944a70f6bb`, `f78ccc8f92e4c6dc` and 2 more). On the whole pack (500 documents) it changes 0 and drops 2.
5. **Side effects:**
   - A short page in English with long foreign quotations can cross 50% and be dropped.
   - A foreign language that is not in the function-word list (Portuguese, Polish, Czech) in Latin script is counted as English, so the page is kept.
   - A bilingual document that is half English (an English report with a French annex) is kept; the labeller dropped `ae0c958288200e55` for this, and the medicine does not.

---

The next two diseases are in 5 or fewer documents, but more than 5 times.

## Medicine 7: A1, invisible characters

1. **Disease:** A1 (invisible characters), found in 5 documents (34 times) in the 100 labelled rows. Three examples:
   - `b64c51d59247a36c` @92911: `WE❤⟦U+FE0F⟧TALK.` (U+FE0F) → `WE❤TALK.`
   - `d5f88477e272bd7c` @1606: `☑⟦U+FE0F⟧` (U+FE0F) → `☑`
   - `78687cb0dc7a4f80` @398301: `⬆⟦U+FE0F⟧⬆⟦U+FE0F⟧ | ⬆⟦U+FE0F⟧⬆⟦U+FE0F⟧ …` (U+FE0F) → `⬆⬆ | ⬆⬆ | ⬆⬆ | ⬆⬆ | ⬆⬆ | ⬆⬆ | ⬇⬇ | ⬇⬇ | …`
2. **Medicine:** Remove invisible characters: the emoji variation selectors U+FE0E and U+FE0F, zero-width space U+200B, BOM U+FEFF, soft hyphen U+00AD and the bidi controls U+202A–U+202E and U+2066–U+2069.

   ```python
   import re

   A1_JUNK = re.compile("[\uFE0E\uFE0F\u200B\uFEFF\u00AD\u202A-\u202E\u2066-\u2069]")

   def cure_a1(text):
       return A1_JUNK.sub("", text)
   ```

3. **Action:** Fix the text.
4. **Harm test:** on the gold set (26 documents) it changes 0 and drops 0: 0 of 26 = 0.00%, **pass**.
   On the 5 labelled documents with A1 it acts on 4 (it misses `f5faeb5d20b73087`). On the whole pack (500 documents) it changes 5 and drops 0.
5. **Side effects:**
   - An emoji that needs U+FE0F to show in colour (`❤️`) shows as a plain symbol (`❤`); the meaning is kept.
   - The `立` labelled A1 in `f5faeb5d20b73087` is not invisible; the A6 medicine handles it.

## Medicine 8: B2, HTML tags

1. **Disease:** B2 (HTML tags), found in 4 documents (47 times) in the 100 labelled rows. Three examples:
   - `8854bf31b8eea361` @6674: `<sup>a</sup>` → `^a`
   - `aa241f145eca058d` @39648: `<sup>c</sup>` → `^c`
   - `2b60daba400d7754` @27164: `<br>Max. Temperature: 1800°C; Working Temperature: 1700°C;<br>Heating Element: M…` → `; Max. Temperature: 1800°C; Working Temperature: 1700°C; Heating Element: Molybd…`
2. **Medicine:** Rewrite the HTML that the PDF-to-Markdown step left in tables: `<sup>x</sup>` → `^x`, `<sub>x</sub>` → `_x`, `<br>` → `; ` (a Markdown table cell cannot hold a newline), and remove `<b>`, `<i>`, `<u>`, `<em>`, `<strong>`, `<span>`, `<div>`, `<p>`, `<font>` tags (a tag with attributes only when they have `=`, so `a <b and c> d` in math is safe).

   ```python
   import re

   B2_SUP = re.compile(r"<sup>(.*?)</sup>", re.I)

   B2_SUB = re.compile(r"<sub>(.*?)</sub>", re.I)

   B2_BR = re.compile(r"\s*<br\s*/?>\s*", re.I)

   B2_TAG = re.compile(r"</?(?:b|i|u|em|strong|span|div|p|font)(?:\s+[a-z-]+=[^<>\n]{0,80})?\s*/?>", re.I)

   def cure_b2(text):
       text = B2_SUP.sub(r"^\1", text)       # 6<sup>a</sup> -> 6^a
       text = B2_SUB.sub(r"_\1", text)       # H<sub>2</sub>O -> H_2O
       text = B2_BR.sub(lambda m: " " if text[m.start() - 1:m.start()] in ";,.:" else "; ", text)  # in a table cell
       return B2_TAG.sub("", text)
   ```

3. **Action:** Fix the text.
4. **Harm test:** on the gold set (26 documents) it changes 0 and drops 0: 0 of 26 = 0.00%, **pass**.
   On the 4 labelled documents with B2 it acts on 4. On the whole pack (500 documents) it changes 14 and drops 0.
5. **Side effects:**
   - `^G12D/+` is less clear than a real superscript for a long gene label.
   - A `<br>` that separated two list items becomes `; `, which joins them into one line.
   - A document that teaches HTML (a code listing with `<p>`) loses its example tags.

## Summary

| Medicine | Code | Action | Gold changed | Gold dropped | Gold harm | Result | Labelled docs fixed | Pack changed | Pack dropped |
|---|---|---|---|---|---|---|---|---|---|
| 1 | C2 | fix | 0 | 0 | 0.00% | pass | 23 of 39 | 94 | 0 |
| 2 | F1 | fix | 0 | 0 | 0.00% | pass | 21 of 23 | 81 | 0 |
| 3 | B5 | fix | 0 | 0 | 0.00% | pass | 4 of 18 | 15 | 0 |
| 4 | C1 | fix | 0 | 0 | 0.00% | pass | 5 of 12 | 27 | 0 |
| 5 | A6 | fix | 0 | 0 | 0.00% | pass | 2 of 9 | 6 | 0 |
| 6 | D3 | drop | 0 | 0 | 0.00% | pass | 1 of 8 | 0 | 2 |
| 7 | A1 | fix | 0 | 0 | 0.00% | pass | 4 of 5 | 5 | 0 |
| 8 | B2 | fix | 0 | 0 | 0.00% | pass | 4 of 4 | 14 | 0 |

Other codes, with no medicine yet (one document each):

| Code | Disease | Documents | Times |
|---|---|---|---|
| B3 | ghost chat markers | 1 | 14 |
| B4 | template and code junk | 1 | 4 |
| A3 | mojibake | 1 | 2 |
