# Medicine sheet: math-finemath (uz9ai)

Count: 500 documents
Pack: `HuggingFaceTB/finemath`, all labelled `en`, all read in full.
Verdicts in `labels.csv`: 347 clean, 147 fix, 6 drop.
Six codes were found more than five times: F1 (78 documents), C1 (38), A1 (15), A3 (11), A6 (9), A5 (6). Each has one medicine below.

**Everything needed to reproduce the numbers is in this file.** Each Medicine section contains the full code of its medicine with all
constants (phrase lists, tables). To run them, put this at the top of one Python file, paste the code blocks of Medicines 1 to 6 below it,
then paste the harness block from the last section:
```python
import csv, re, sys, unicodedata
```


All six together change 15 of 347 proxy documents (4.3%), and every one of the 15 is an F1 or C1 hit. On the gold set (86 documents, limit 1) every medicine and all six together change 0 documents.

Rule of the lab repository: no personal values are copied here. F1 evidence gives the type and the offset only.

---

## Medicine 1: F1 personal data
1. **Disease:** F1, 78 documents (77 fix, 1 drop). Types by document: person name 74, e-mail 4, phone 3, postal address 1 (a document can have several types). Examples (type and offset, no values): `02c235b035b38798` name @72 and e-mail @82; `4dd5d3e3c89b86ae` phone number @20; `216144050512d475` name @107 (answerer's name under a question).
2. **Medicine:** the names sit in a few layouts, so the rule is a list of anchored patterns, each replacing only the name with `[name removed]`: "Asked by NAME |", "asked by NAME on", "edited by NAME", "Date: ...⏎From: NAME⏎Subject:", "Author: NAME", "NAME says:", "NAME said...", a line `-NAME` (signature), a line `by NAME` with two or three words, and `NAME  Mon D, YYYY` (forum post header). The Q&A comment header `– NAME Mon D 'YY at HH:MM` is no longer a pattern: on the gold set it changed 4 clean documents (see the harm test below). E-mail addresses become `[email removed]` unless the local part is a role (`info`, `support`, `contact`, `sales`, `admin`, ...). A phone number after a label (`WhatsApp`, `Toll free no`, `Tel`, `Phone`, `Call`) or in the form `NNN-NNN-NNNN` / `NNNN-NNN-NNNN` becomes `[phone removed]`.
   ```python
   # Only high-precision patterns: bylines and comment headers, personal e-mails, phone numbers after a label.
   NAME = r"[A-Z][a-z]+(?:\.? [A-Z][a-z]+){0,2}"
   GENERIC = r"(?:info|support|contact|discounts?|admin|sales|help|webmaster|feedback|office|team|hello|enquiries)"
   F1_RULES = [
       (re.compile(r'(?m)^(Asked by )' + NAME + r'(?= \|)'), r'\1[name removed]'),
       (re.compile(r'(?m)^(asked by )' + NAME + r'(?= on )'), r'\1[name removed]'),
       (re.compile(r'(?m)^(edited by )' + NAME + r'(?= )'), r'\1[name removed]'),
       (re.compile(r'(?m)^(Date: [^\n]+\nFrom: )' + NAME + r'(?=\nSubject:)'), r'\1[name removed]'),
       (re.compile(r'(?m)^(Author\n\n### )' + NAME + r'$'), r'\1[name removed]'),
       (re.compile(r'(?m)^(Author: )' + NAME + r'$'), r'\1[name removed]'),
       (re.compile(r'(?m)^(\d+\. )?' + NAME + r'(?= says:$)'), r'\1[name removed]'),
       (re.compile(r'(?m)^' + NAME + r'(?= said\.\.\.$)'), r'[name removed]'),
       (re.compile(r'(?m)^(-)' + NAME + r'$'), r'\1[name removed]'),
       (re.compile(r'(?m)^(by )' + NAME.replace('{0,2}', '{1,2}') + r'$'), r'\1[name removed]'),
       (re.compile(r'(?m)^' + NAME + r'(?=\s\u00a0[A-Z][a-z]{2} \d{1,2}, \d{4}$)'), r'[name removed]'),
       (re.compile(r'(?<![\w.-])(?!' + GENERIC + r'@)[\w.+-]+@[\w-]+(?:\.[\w-]+)+'), '[email removed]'),
       (re.compile(r'(?i)\b(whatsapp(?: chat)?|toll free no|tel|phone|call)\b(:?\s*)\+?[\d][\d\s-]{8,}\d'), r'\1\2[phone removed]'),
       (re.compile(r'(?<![\d.-])\(?\d{3,4}\)?[ -]\d{3}-\d{4}(?![\d-])'), '[phone removed]'),
   ]
   def med_F1(t):
       for rx, rep in F1_RULES:
           t = rx.sub(rep, t)
       return t
   ```
3. **Action:** fix.
4. **Harm test:** proxy 3 changed / 0 dropped of 347 (0.9%; these 3 are among the 7 documents that I had checked earlier and found to hold real personal data although I had labelled them clean). Gold (86 documents, limit 1): 0 changed / 0 dropped, PASS. A first version with a Q&A comment-header pattern (`– NAME Mon D 'YY at HH:MM`) changed 4 gold documents (4.65%, FAIL); the pattern also matched short user handles, so it was removed.
5. **Side effects:** recall is only 20 of 78 (it was 26 of 78 with the comment-header pattern, so names in StackExchange comment headers are no longer found): names in running text ("thanks, Priya"), in lists of users, in a signature block under a title, and postal addresses are not found, because a rule cannot tell a person's name from a topic word. It also masks user names that are handles (`whuber`, `talmid`), and names of public authors in a byline (an author's attribution is lost). A role e-mail not in the short list would be masked too. A business phone number is masked as well (I treat it as F1 in my labels). A real line `-Name` that is a minus sign before a capitalised word would be changed.

## Medicine 2: C1 boilerplate
1. **Disease:** C1, 38 documents (36 fix, 2 drop). `ff84a3381e5cc70f` Khan Academy "If you're seeing this message, it means we're having trouble loading external resources..." @0; `43fe6906818d0a26` "Powered by phpBB © phpBB Group ... GMAT® test is a registered trademark..." @1745; `3298ace879873aa7` "This preview shows document pages 1 - 2. Sign up to view the full document." @1584.
2. **Medicine:** (a) delete a line of at most 200 characters that starts with a known site-chrome phrase (`C1_PHRASES` below, 46 phrases seen in this pack); (b) delete a line that is a navigation bar (6 or more short items separated by ` | `) or a tag cloud (8 or more comma-separated Title-Case phrases); (c) from a footer phrase (`Powered by php...`, `We use cookies to personalise content`, `Kindly note that the GMAT`, `Sign up for free to access`, `Thread Tools Display Modes`) delete to the end of the line; (d) delete the forum counter block `Replies⏎9⏎Views⏎1K` and runs of 3 or more lines that hold only an arrow.
   ```python
   C1_PHRASES = [
       r'Powered by php\w*', r'Kindly note that the GMAT', r'We use cookies to personali[sz]e content',
       r'(?:Open in App|Not now|Scroll to Top|Related Articles)\W*$', r'My Personal Notes arrow_drop_up',
       r"If you're seeing this message, it means we're having trouble loading external resources",
       r"If you're behind a web filter, please make sure that the domains",
       r'Created with Sketch', r'You visited us \d+ times', r'Unlock Full Access',
       r'Sign up for free to access', r'\u2190 Previous', r'Post Go back to editing',
       r'Explore Courses for', r'Watch in App', r"Join BYJU'S Learning Program", r'Courses for Kids',
       r'Free study material', r'Offline Centres', r'Or use your account on', r'Upcoming SlideShare',
       r'Go To Main page', r'We are the best freelance writing portal', r'To read offline at any time',
       r'Website Maintained by', r'CYBER MONDAY OFFER', r'Related Introductory Physics Homework Help',
       r'Introductory Physics Homework Help', r'You are Here: Home', r'Home\s*>>',
       r'new topic post reply', r'\(Running on oeis\d\.\)', r'Replies\s*Views',
       r'Ask a homework question', r'Share this great discussion', r'This preview shows document pages',
       r'Sign up to view the full document', r'View Full Document', r'You are on page \d+\s*of \d+',
   ]
   C1_RX = re.compile(r'(?i)^\W*(?:' + '|'.join(C1_PHRASES) + r')')   # a line that STARTS with a chrome phrase
   _TITLE_LIST = re.compile(r"^(?:[A-Z][\w'&.\-]*(?: [\w'&.\-]+){0,6}, ){7,}")
   _NAV_BAR = re.compile(r'^(?:[^|\n]{1,25} \| ){5,}')                      # "Lookup | Welcome | Wiki | ..."
   # phrases that start a footer: delete from the phrase to the end of its line
   _TAIL = re.compile(r'(?i)(?:Powered by php\w*|We use cookies to personali[sz]e content|Kindly note that the GMAT'
                      r'|Sign up for free to access|_{10,} \[hidden email\] mailing list|\| Top of Page \||'
                      r'Thread Tools Display Modes|Similar Threads Thread).*$')
   def med_C1(t):
       t0 = t
       t = re.sub(r'(?m)^Replies\n[\d.,K]+\nViews\n[\d.,K]+\n?', '', t)   # forum thread counters
       t = re.sub(r'(?m)(?:^[\u2192\u2190]\n){3,}', '', t)                    # runs of lone arrows
       keep = []
       for line in t.split('\n'):
           s = line.strip()
           if s and len(s) <= 200 and C1_RX.match(s):
               continue
           if _TITLE_LIST.match(s) or _NAV_BAR.match(s):                # SEO tag cloud, nav bar
               continue
           line = _TAIL.sub('', line)
           keep.append(line)
       out = '\n'.join(keep)
       return re.sub(r'\n{3,}', '\n\n', out) if out != t0 else t0
   ```
3. **Action:** fix. After the fix, a document that keeps fewer than about 200 characters should be dropped (for example `db5a45c39b512a02`, where only the first line is real text); this length check is not in the code.
4. **Harm test:** proxy 12 changed / 0 dropped of 347 (3.5%). All 12 contain chrome of the same kind as the labelled C1 documents (a cookie or app banner, a course menu, a breadcrumb, a forum footer, the OEIS menu bar, "View Full Document" preview pages), so I believe they are missing C1 labels (list above). Gold (86 documents, limit 1): 0 changed / 0 dropped, PASS.
5. **Side effects:** the phrase list is fitted to the sites in this pack, so menus and footers from other sites are missed. Recall is 36 of 38 here, but that is partly because the phrases were taken from those same documents, so expect a lower number on new data. The rule removes a legitimate line that starts with one of the phrases (a lesson that really is titled "Related Articles", or a line "Home >> ..." inside a tutorial). Removing "View Full Document" and the preview banner leaves a cut-off page body: such pages are better dropped (C3). Missed here: `98e5be6db6c1c81e` (a metadata block `Author:⏎Subject:⏎...`) and `57e62d62ad273696` (a block of forum link lines).

## Medicine 3: A1 invisible characters
1. **Disease:** A1, 15 documents, 49 characters. `064d8dd19536d1d8` U+200E LEFT-TO-RIGHT MARK @9 (x2); `8f09ea36d06abaef` U+00AD SOFT HYPHEN @3180 (x4, inside LaTeX `\\\xad(`); `263a5308b96d2e4a` U+200B ZERO WIDTH SPACE @6754. Also U+FEFF at offset 0 in `00ac15aab828f732` and `4e95ecbf4dc047ff`, and six U+2062 INVISIBLE TIMES in `4e8b452ef39ff8b6` @289.
2. **Medicine:** delete U+200B, U+FEFF, U+00AD, U+200E, U+200F, U+2060 to U+2064, U+202A to U+202E, U+2066 to U+2069. U+200C and U+200D (ZWNJ, ZWJ) are never touched.
   ```python
   A1_RX = re.compile('[\u200b\ufeff\u00ad\u200e\u200f\u2060-\u2064\u202a-\u202e\u2066-\u2069]')
   def med_A1(t):
       return A1_RX.sub('', t)
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 changed / 0 dropped of 347. Gold (86 documents, limit 1): 0 changed / 0 dropped, PASS.
5. **Side effects:** if a ZWSP is the only separator between two words, they are joined. A soft hyphen that was already followed by a space leaves the split word (`stud ies` in `4d57615e33e7997e`); the rule cannot re-join it. LRM and RLM carry meaning in right-to-left text, so this medicine must not run on Arabic or Hebrew packs. U+2062 is removed from MathML text, where it only marks an invisible multiplication.

## Medicine 4: A3 mojibake
1. **Disease:** A3, 11 documents. `f5f0ba81109f9e43` "â€™" @5192 (U+00E2 U+20AC U+2122, a right quote); `ab295000bded241a` "ðŸ˜€" @118 (U+00F0 U+0178 U+02DC U+20AC, an emoji); `f79e6aeb5ebb6a5c` "тАЩ" @4628 (U+0442 U+0410 U+0429, the same quote read as code page 866). Others: `4477acbfa8e1a6da` "Ă©" (code page 1250), `8d3cd2aa796817be` "¡Ý" (a GBK `≥` read as Latin-1), `c9e5d27233084b62` (several different sequences).
2. **Medicine:** find a short run that starts with a UTF-8 lead byte shown as a Windows-1252 or 1250 character (`Â Ã â ð Ă`) and followed by continuation bytes. Encode the run back to bytes (Windows-1252, then 1250; undefined bytes such as U+0081 pass through), decode as UTF-8, and keep the result only if it is shorter and falls in Latin, punctuation, currency, arrows, maths or emoji. Two narrow extra rules: `т[АБ]x` (cp866) and `¡Ý` / `¡Ü` style GBK pairs, accepted only when the result is a maths sign.
   ```python
   _OK = (  # ranges the repaired text may fall in (Latin, punctuation, maths, arrows, emoji)
       (0x00A0, 0x024F), (0x2000, 0x206F), (0x20A0, 0x20CF), (0x2190, 0x21FF),
       (0x2200, 0x22FF), (0x1F000, 0x1FAFF))
   def _ok(s):
       return all(any(a <= ord(c) <= b for a, b in _OK) or c in '\n' for c in s)

   # a run that starts with a UTF-8 lead byte (C2 C3 E2 F0) shown in cp1252 / cp1250
   _RUN = re.compile('[\u00c2\u00c3\u00e2\u00f0\u0102][\u0080-\u00ff\u0100-\u017f\u0192\u02c6\u02dc\u2013-\u203a\u20ac\u2122]{1,3}')
   _CP866 = re.compile('\u0442[\u0410\u0411][\u0400-\u04ff]')
   _GBK_MATH = {'\u2265', '\u2264', '\u2260', '\u2248', '\u00b1', '\u00d7', '\u00f7', '\u221e', '\u2220', '\u2208'}
   _GBK = re.compile('\u00a1[\u00a1-\u00ff]')

   def _try(run, codec):
       try:
           b = bytearray()
           for ch in run:
               try:
                   b += ch.encode(codec)
               except UnicodeEncodeError:
                   if '\u0080' <= ch <= '\u009f':   # undefined cp1252 byte shown as a C1 control
                       b.append(ord(ch))
                   else:
                       raise
           s = bytes(b).decode('utf-8')
       except (UnicodeEncodeError, UnicodeDecodeError):
           return None
       return s if len(s) < len(run) and _ok(s) else None

   def _fix_run(m):
       run = m.group()
       # the regex may take one char too many: try the full run, then shorter ones
       for n in range(len(run), 1, -1):
           for codec in ('cp1252', 'cp1250'):
               s = _try(run[:n], codec)
               if s:
                   return s + run[n:]
       return run

   def _fix_cp866(m):
       try:
           s = m.group().encode('cp866').decode('utf-8')
       except (UnicodeEncodeError, UnicodeDecodeError):
           return m.group()
       return s if _ok(s) else m.group()

   def _fix_gbk(m):
       try:
           s = m.group().encode('cp1252').decode('gbk')
       except (UnicodeEncodeError, UnicodeDecodeError):
           return m.group()
       return s if s in _GBK_MATH else m.group()

   def med_A3(t):
       t = _RUN.sub(_fix_run, t)
       t = _CP866.sub(_fix_cp866, t)
       return _GBK.sub(_fix_gbk, t)
   ```
3. **Action:** fix. The repairs in the 11 documents were checked on screen: `’`, `–`, `…`, `é`, `😀`, `≥`, `Â`+NBSP to NBSP.
4. **Harm test:** proxy 0 changed / 0 dropped of 347. Gold (86 documents, limit 1): 0 changed / 0 dropped, PASS.
5. **Side effects:** a real text that happens to contain `Ã` or `â` followed by symbols that decode as valid UTF-8 would be "repaired" (rare in English maths text; the result must be Latin, punctuation or maths, which blocks Hebrew or Arabic false repairs such as `×`+NBSP). Only the code pages seen in this pack are covered (1252, 1250, 866, GBK maths signs). A document with a lone `Â` before a normal character, or a double-encoded string, is not repaired.

## Medicine 5: A6 symbol-font private-use glyphs and look-alikes
1. **Disease:** A6, 9 documents. `9be631b8d8a8b294` U+F0C5 @6107 (a circle-plus sign between two variables in a logic formula, should be ⊕); `c46f9ecdfac73e93` U+F0D8 @875 (slide bullet); `f2746fa01fbc3cf4` "fɑstidious", "discusѕion", "ѡeblog" (U+0251 @4992, U+0455 @5008, U+0461 @5058). Others: `8e9e5b4d6166454e` (a PDF equation, many U+F0xx), `c55fa2fcaeafd041` "DСВ" with Cyrillic U+0421 U+0412 @457, `c4c6e583f8989cd3` "Math՚s" with Armenian U+055A @21.
2. **Medicine:** (a) U+F0xx from the Symbol font: bullet codes (`B7 A8 D8 A7`) become `•`; a table of maths codes becomes the real sign (`F03D` `=`, `F028` `(`, `F029` `)`, `F02B` `+`, `F0B6` `∂`, `F0C5` `⊕`, `F0D7` `⋅`, Greek letters); the tall-bracket pieces (`F0E6` to `F0FE`) are deleted; other private-use characters stay. (b) U+055A between letters becomes `'`. (c) in a word that has an ASCII letter and a look-alike letter (Cyrillic `С В Е Н К М О Р Т Х А а е о р с х у і ѕ ѡ`, Latin alpha `ɑ`), the look-alike is replaced by the ASCII letter.
   ```python
   _BULLET = {'\uf0b7', '\uf0a8', '\uf0d8', '\uf0a7'}          # Wingdings / Symbol bullets
   _SYMBOL = {  # U+F000 + Symbol-font code -> Unicode
       0x28: '(', 0x29: ')', 0x2b: '+', 0x2d: '\u2212', 0x3d: '=', 0x3c: '<', 0x3e: '>',
       0x68: '\u03b7', 0x72: '\u03c1', 0x78: '\u03be', 0x7a: '\u03b6', 0x61: '\u03b1', 0x62: '\u03b2',
       0x67: '\u03b3', 0x64: '\u03b4', 0x6c: '\u03bb', 0x6d: '\u03bc', 0x70: '\u03c0', 0x73: '\u03c3',
       0x74: '\u03c4', 0x77: '\u03c9', 0xb1: '\u00b1', 0xb2: '\u2033', 0xb4: '\u00d7', 0xb6: '\u2202',
       0xb9: '\u2260', 0xba: '\u2261', 0xbb: '\u2248', 0xc5: '\u2295', 0xc4: '\u2297', 0xd7: '\u22c5',
       0xa3: '\u2264', 0xb3: '\u2265', 0xa5: '\u221e', 0xd1: '\u2207', 0xe5: '\u2211', 0xf2: '\u222b',
   }
   _BRACKET_PIECES = set(range(0xe6, 0xff)) - {0xf2}           # tall-bracket drawing pieces
   _PUA_RX = re.compile('[\uf020-\uf0ff]')
   def _sym(m):
       c = m.group()
       if c in _BULLET:
           return '\u2022'
       code = ord(c) - 0xF000
       if code in _SYMBOL:
           return _SYMBOL[code]
       if code in _BRACKET_PIECES:
           return ''
       return c

   _HOMO = {  # Cyrillic / Latin-extended letters that look like ASCII letters
       '\u0421': 'C', '\u0412': 'B', '\u0415': 'E', '\u041d': 'H', '\u041a': 'K', '\u041c': 'M',
       '\u041e': 'O', '\u0420': 'P', '\u0422': 'T', '\u0425': 'X', '\u0410': 'A',
       '\u0430': 'a', '\u0435': 'e', '\u043e': 'o', '\u0440': 'p', '\u0441': 'c', '\u0445': 'x',
       '\u0443': 'y', '\u0456': 'i', '\u0455': 's', '\u0461': 'w', '\u0251': 'a',
   }
   _TOKEN = re.compile(r'\w+')
   def _homo(m):
       w = m.group()
       if re.search('[A-Za-z]', w) and any(c in _HOMO for c in w):
           return ''.join(_HOMO.get(c, c) for c in w)
       return w

   def med_A6(t):
       t = _PUA_RX.sub(_sym, t)
       t = re.sub(r'(?<=[A-Za-z])\u055a', "'", t)               # Armenian apostrophe inside a word
       t = _TOKEN.sub(_homo, t)
       return t
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 changed / 0 dropped of 347. Gold (86 documents, limit 1): 0 changed / 0 dropped, PASS.
5. **Side effects:** Symbol and Wingdings share the code points: a Wingdings arrow at `F0D8` becomes a plain bullet, and a Symbol `F0D8` (`¬`) would also become a bullet. Deleting the bracket pieces turns a matrix into loose numbers. The look-alike rule needs a Latin letter in the same word, so a word fully in Cyrillic is not touched. Missed: `f6c1776061f622c6`, where U+0404 `Є` stands alone for `∈` (`f, g Є R`). Recall 8 of 9.

## Medicine 6: A5 ligatures and full-width forms
1. **Disease:** A5, 6 documents. `ce9b0d519779eba2` "ﬀ" U+FB00 @68, then U+FB01 @187, U+FB02 @1110, U+FB03 @2443 (PDF ligatures in "Diﬀerential", "ﬁrst", "reﬂection", "coeﬃcients"); `6dbea1b7e4a63a28` "ﬁ" U+FB01 @1229; `addb07a0a886743c` "，" U+FF0C FULLWIDTH COMMA @2666 in English text. Also `c16db13d63739369` (x4 ligature kinds), `a96d6c140245cd16`, `2c59f0ca117f6bdf`.
2. **Medicine:** replace U+FB00 to U+FB06 by their NFKC letters (`ﬁ` to `fi`, `ﬀ` to `ff`). Replace full-width ASCII forms U+FF01 to U+FF5E by the ASCII character, adding a space after `， ： ； ？ ！` when a non-space follows, but only when CJK characters are under 1% of the letters. Full NFKC is not used: it would change `x²` to `x2`.
   ```python
   LIG_RX = re.compile('[\ufb00-\ufb06]')
   FW_RX = re.compile('[\uff01-\uff5e]')
   CJK_RX = re.compile('[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]')
   _FW_SPACE = set('\uff0c\uff1a\uff1b\uff1f\uff01')  # become ", " ": " "; " "? " "! "

   def _fw(m):
       a = chr(ord(m.group()) - 0xFEE0)
       nxt = m.string[m.end():m.end() + 1]
       return a + ' ' if m.group() in _FW_SPACE and nxt and not nxt.isspace() else a

   def med_A5(t):
       t = LIG_RX.sub(lambda m: unicodedata.normalize('NFKC', m.group()), t)
       letters = sum(c.isalpha() for c in t) or 1
       if len(CJK_RX.findall(t)) / letters < 0.01:
           t = FW_RX.sub(_fw, t)
       return t
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 changed / 0 dropped of 347. Gold (86 documents, limit 1): 0 changed / 0 dropped, PASS.
5. **Side effects:** a typography page that shows a ligature as an example loses it. In `2c59f0ca117f6bdf` the ligature is inside OCR garbage; the fix is harmless but the text stays garbage. A full-width character inside a short English quote from a Chinese text is converted too, because the 1% rule looks at the whole document.

---

## Harness (harm test and recall)
Paste after the code of Medicines 1 to 6. It prints, for each medicine, how many labelled documents it changes, how many `clean` documents
it changes (the proxy harm test), and, if a gold parquet with a `text` column is given, the gold numbers.
```text
MEDS = {'C1': med_C1, 'A1': med_A1, 'A3': med_A3, 'A5': med_A5, 'A6': med_A6, 'F1': med_F1}

def run(labels, parquet):
    import pandas as pd
    df = pd.read_parquet(parquet).set_index('doc_id')
    rows = list(csv.DictReader(open(labels, encoding='utf-8', newline='')))
    clean = [r['doc_id'] for r in rows if r['verdict'] == 'clean']
    print(f'clean proxy: {len(clean)} documents; 1% = {len(clean) / 100:.2f}')
    for code, f in MEDS.items():
        lab = [r['doc_id'] for r in rows if code in r['diseases'].split(';')]
        caught = [d for d in lab if f(df.loc[d, 'text']) != df.loc[d, 'text']]
        harm = [d for d in clean if f(df.loc[d, 'text']) != df.loc[d, 'text']]
        print(f'{code}: labelled {len(lab)}, caught {len(caught)}, clean changed {len(harm)} {harm[:6]}')
    # all medicines in sequence
    def chain(t):
        for f in (med_A3, med_A1, med_A5, med_A6, med_C1, med_F1):
            t = f(t)
        return t
    harm = [d for d in clean if chain(df.loc[d, 'text']) != df.loc[d, 'text']]
    print(f'all medicines together: clean changed {len(harm)} of {len(clean)} {harm}')
    if len(sys.argv) > 3:                                  # real harm test on the gold set
        g = pd.read_parquet(sys.argv[3])
        for code, f in MEDS.items():
            n = sum(f(t) != t for t in g['text'])
            print(f'GOLD {code}: changed {n} of {len(g)} ({100 * n / len(g):.2f}%)')

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
```

### Found five times or fewer (no medicine required)
D3 mixed-in foreign script (3: `7de899c48fa1cb6b` Arabic @16467, `ce878294b69f1b20` Chinese @0, `ca3cb26190545cf7` Turkish @7), A4 replacement character U+FFFD (3: `dcaa196cc9b2af15` @1261, `e8c2f5d56d924698` @7988, `7c6df0c4a23c902b` @1957), A2 control characters (3: `ca992a9ad3ec9ab5` U+000F U+000E @833, `4fe1c2fcbad20d13` U+0081 @817, `c16db13d63739369` U+0004 @52), H2 near duplicate (1: `3d55caf668a9200b`, same as `db5a45c39b512a02`), B2 HTML tags (1: `ee971e5cfb53453e` `</p>` @6121), D1 wrong language (1: `e9d9f54a1a782960` Chinese @2).
