# Medicine sheet: math-finemath (SomaKorada07)

Pack: 500 documents, `HuggingFaceTB/finemath | finemath-4plus`, all labelled `en`, every document read in full.
Labels: 322 fix, 101 clean, 77 drop. Every medicine below is a complete Python function (`medicine_<code>(text)`, stdlib
only) that returns the new text, or `("drop", text)` to drop the document. Each one gives the same output as my
`medicines.py` on all 500 pack documents.

**Harm test.** Gold: `teams/01-data-a/gold/math-finemath_gold.csv` (30 documents, all labelled `clean` in my `labels.csv`),
run with `harm_test.py` from `g1-harm-test`, limit `max(1, 1% of 30)` = 1 document:

```
python -I teams/01-data-a/tools/harm_test.py --pack math-finemath.parquet \
  --gold teams/01-data-a/gold/math-finemath_gold.csv \
  --rules diagnosis/submissions/math-finemath/SomaKorada07/medicine.md --rule all
```

"Caught" is how many of the documents labelled with that disease the medicine actually changes (its recall on this
pack). The proxy column is the 101 pack documents I labelled `clean`.

| # | Disease | Labelled docs | Action | Caught | Pack: changed / dropped | Proxy clean (101): changed / dropped | Gold (30): changed / dropped |
|---|---|---|---|---|---|---|---|
| 1 | C1 boilerplate | 328 | fix | 109 | 109 / 0 | 0 / 0 | 0 / 0 PASS |
| 2 | C2 repeated lines / passages | 187 | fix | 40 | 57 / 0 | 0 / 0 | 0 / 0 PASS |
| 3 | C5 keyword / link lists | 50 | fix (drop via verdict when the page is mostly spam) | 5 | 5 / 0 | 0 / 0 | 0 / 0 PASS |
| 4 | C3 truncated | 49 | drop previews, trim teaser cuts | 15 | 5 / 12 | 0 / 0 | 0 / 0 PASS |
| 5 | A1 invisible characters | 15 | fix | 14 | 14 / 0 | 0 / 0 | 0 / 0 PASS |
| 6 | B4 template junk | 18 | fix | 9 | 9 / 0 | 0 / 0 | 0 / 0 PASS |
| 7 | B5 broken LaTeX / markdown | 28 | fix | 5 | 7 / 0 | 0 / 0 | 0 / 0 PASS |
| 8 | A3 mojibake | 11 | fix | 10 | 10 / 0 | 0 / 0 | 0 / 0 PASS |
| 9 | B2 HTML tags | 8 | fix | 3 | 3 / 0 | 0 / 0 | 0 / 0 PASS |
| 10 | A6 symbol-font / look-alike glyphs | 9 | fix | 5 | 5 / 0 | 0 / 0 | 0 / 0 PASS |
| 11 | D3 mixed-in foreign script | 10 | fix (drop if >30% foreign) | 5 | 7 / 1 | 0 / 0 | 0 / 0 PASS |
| 12 | C4 two documents joined | 7 | drop (manual) | – | no automatic medicine | – | – |
| 13 | D4 machine-translated / spun text | 22 | drop (manual) | – | no automatic medicine | – | – |
| 14 | A5 compatibility forms | 6 | fix | 6 | 6 / 0 | 0 / 0 | 0 / 0 PASS |
| 15 | F1 personal data | 7 | fix | 2 | 8 / 0 | 1 / 0 | 0 / 0 PASS |

All 13 medicines pass on the gold set, one by one and all together in file order (0 / 30 changed or dropped).
As a check that the rules do run, on the whole 500-document pack they give the "Pack" counts above. C4 and D4 have
no function, so the test lists them as warnings. patilvijay23/era-v5-lab#19 rewrote 10 of these in the team
rule form; its C1 has a shorter phrase list (47 caught instead of 109). The function here is the full one.

---

## Medicine 1: C1 boilerplate
1. **Disease:** C1, 328 documents (most web pages keep some site chrome). `72f073c36305b095` "posted by gamer chick" @13; `de1b08a158de9ae9` "This preview shows page" @95; `92bef36fe0c0fc40` "Replies / Views" related-thread blocks @9487.
2. **Medicine:** delete a line that is a known chrome phrase (`C1`), or that contains a site-chrome phrase (`C1_SITE`, ~70 phrases seen in this pack: GMAT Club headers, "View Full Document", OEIS footer, "My Personal Notes arrow_drop_up", …) and is at most 120 characters; delete `Replies\n<n>\nViews\n<n>` blocks.
   ```python
   import re

   # a whole line that is generic site chrome
   C1_LINE = re.compile(
       r"(?i)\s*(?:More Similar Questions|Similar Questions|Related (?:Questions|Posts|Articles)|Share (?:this|on \w+)|"
       r"Sign ?up|Log ?in|Subscribe|Cookie|Accept (?:all )?cookies|Privacy Policy|Terms of (?:Use|Service)|"
       r"All rights reserved|©.*|&copy;.*|Follow us|Skip to (?:main )?content|Show Tags|Replies|Views|"
       r"Contact - Home.*|Report (?:abuse|post)|Upvote|Downvote|Like this:|Loading\.\.\.|Previous Post|Next Post|"
       r"Recommended|Back to top|Quick Reply|Click here.*|Leave a (?:Reply|Comment)|Your email address will not be published.*|"
       r"Posted by.*|Tags?:.*|Categories?:.*|Hide Tags|Join (?:now|us)|Download (?:the )?App.*|Course Hero.*)\s*")
   # site chrome seen in this pack (forums, homework sites, document hosts, OEIS, GMAT Club ...); only on lines <= 120 chars
   C1_SITE = re.compile(
       r"(?i)Check GMAT Club Decision Tracker|It is currently \d+ \w+ \d{4}|GMAT Club Daily Prep|Display posts from previous|"
       r"GMAT® test is a registered trademark|\[#permalink\]|Kudos \[\?\]|This preview shows page|Sign up to view the full|"
       r"View Full Document|Ask a homework question|intentionally blurred sections|My Personal Notes arrow_drop_up|"
       r"^Open in App$|^Last Updated :|All times are GMT|The time now is \d{1,2}:\d{2}|Privacy Statement|"
       r"Remember Me\? Password|having trouble loading external resources|analy[sz]e our traffic|Want to see this answer and more|"
       r"^See Solution$|^Subscribe now$|Upcoming SlideShare|Are you sure you want to|Report Content as Inappropriate|"
       r"Open this post in threaded view|^Loading content$|The OEIS Community \| Maintained by|supported by donations|"
       r"You are Here: Home|Registered Office:|CYBER MONDAY|^Wiki User$|^Buscar$|^Uncategorized$|Created with Sketch|"
       r"best freelance writing portal|Comment sent successfully|Choose the classification system|Read More »|"
       r"TUTORIALS HOME|Top of Page|Our sister site|Everything was clear\?|Hello Guest!|Free\s+Algebra Tutorials!|"
       r"Teach yourself statistics|^Home >>|‎ > ‎|claim an answer you’ll have 24 hours|Search Our Content Library|"
       r"filtered results|^Sort by$|tutors are online|snackBarMessage|Go To Main Page|^Show/hide solution$|"
       r"Correct! Wrong!|Tutorial is loading|^Filed Under:|^Exam Prep:|^Asked in:|Verified Answer \| Published|"
       r"^Guided Lessons$|^Course Content$|Doorsteptutor|Mark Forums Read|^Recommended$|DocShare\.tips|^Hide$|"
       r"Not now$|Write an Interview Experience|Your message has been successfully submitted|has the best spam protection|"
       r"posting guide http|Questions are from the workbook|^Share$|^Children$|Go back to editing|try BYJU|We‘ve got your back")
   # phpBB "Replies / <n> / Views / <n>" block, one value per line
   C1_REPLIES = re.compile(r"(?m)^Replies\n\d+\nViews\n[\d.]+K?\n?")

   def medicine_c1(text):
       keep = [l for l in text.split("\n")
               if not (C1_LINE.fullmatch(l) or (C1_SITE.search(l) and len(l) <= 120))]
       return C1_REPLIES.sub("", "\n".join(keep))
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 changed / 0 dropped. Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** recall is only 109 / 328: the phrase list is fitted to sites seen here, so new sites' menus and footers are missed. A forum title ending in `[#permalink]` is removed (the question usually repeats in the post). A real line that is only "Share", "Views" or "Tags:" would be removed. Found and fixed while testing: "The time now is" deleted the problem statement "If the time now is 9 o'clock" (now needs hh:mm).

## Medicine 2: C2 repeated lines and passages
1. **Disease:** C2, 187 documents. `92bef36fe0c0fc40` "• Introductory Physics Homework Help" @9487 (x10); `98e5be6db6c1c81e` "Mathematical Practice 3: Construct viable…" @2979 (x2); `e9bc93d8821adcec` the same reading passage before each question (x4–5).
2. **Medicine:** (a) a non-code line of 15+ characters that appears 5+ times keeps only its first copy; (b) a passage (blank-line block, 150+ characters, not a bullet list, not answer options, not code) that appears more than once keeps only its first copy (ruling 13).
   ```python
   import re

   C2_CODE = re.compile(r"[;{}]\s*$|^\s*(?:for|if|while|return|def|class)\b")
   C2_PARA_SPLIT = re.compile(r"(\n\s*\n)")
   C2_OPTION = re.compile(r"\s*(?:[A-E1-5][.)]|\(?[a-e]\))\s")

   def _c2_dedupe_passages(text):
       # ruling 13: a passage (150+ chars) repeated even once loses its later copies; option lists and code are kept
       parts, seen, out = C2_PARA_SPLIT.split(text), set(), []
       for k, part in enumerate(parts):
           q = part.strip()
           if k % 2 == 0 and len(q) >= 150 and not re.match(r"\s*[•*-] ", q):
               ql = [x for x in q.splitlines() if x.strip()]
               options = sum(bool(C2_OPTION.match(x)) for x in ql) >= max(2, len(ql) // 2)
               code = sum(bool(re.search(r"[;{}]\s*$", x)) for x in ql) >= max(1, len(ql) // 3)
               if not options and not code:
                   if q in seen:
                       if out and k > 0:
                           out.pop()          # drop the blank-line separator before the copy
                       continue
                   seen.add(q)
           out.append(part)
       return "".join(out)

   def medicine_c2(text):
       lines = text.split("\n")
       counts = {}
       for l in lines:
           counts[l.strip()] = counts.get(l.strip(), 0) + 1
       seen, out = set(), []
       for l in lines:
           s = l.strip()
           if len(s) >= 15 and counts[s] >= 5 and not C2_CODE.search(s):
               if s in seen:
                   continue
               seen.add(s)
           out.append(l)
       return _c2_dedupe_passages("\n".join(out))
   ```
3. **Action:** fix.
4. **Harm test:** proxy 1 changed / 0 dropped (0.85%). Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** the proxy change is natural restatement: an author repeats a sentence on purpose (`5ee756dbf1307a6f`) and the copy is lost. Repeated per-question passages (`e9bc93d8821adcec`) lose their later copies, so later questions lose their context. Recall 40 / 187: short repeated titles and quoted questions under 150 characters are kept.

## Medicine 3: C5 keyword / link lists
1. **Disease:** C5, 50 documents. `25901665fc855b35` "See more: What Did Greg Giraldo…" @3568; `b124803aff87e2d9` "Domain And Range Notes Teachers Pay Teachers…" @5708; `1eff00a48b3b10a0` SEO FAQ farm.
2. **Medicine:** delete lines starting `See more:` and lines made of 5+ comma-separated Title-Case phrases of 2–8 words.
   ```python
   import re

   C5_SEO = re.compile(r"(?m)^(?:See more: .*|(?:[A-Z][\w’'&.-]*(?: [\w’'&.-]+){1,7}, ){5,}.*)$")

   def medicine_c5(text):
       return C5_SEO.sub("", text)
   ```
3. **Action:** fix; a page that is mostly SEO is dropped by its verdict (most of the 46 are `drop`).
4. **Harm test:** proxy 0 / 0. Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** recall is 5 / 50: most C5 here is whole spun/SEO pages, which only a drop decision handles. A real comma list of Title-Case names (bibliography, theorem names) would be deleted.

## Medicine 4: C3 truncated documents
1. **Disease:** C3, 49 documents. `de1b08a158de9ae9` Course Hero preview cut at "s[R2(Cgs" @3238; `9d26c83f14d2087f` "We hav" @772 (paywall); `4e1e6a7902a4435e` teaser ending "deeper unders..." @6566.
2. **Medicine:** drop a document that carries a preview/paywall banner (`This preview shows|Sign up to view the full|View Full Document|intentionally blurred sections`); if a document ends in a teaser cut (`word...` or `word…`), trim back to the last full sentence.
   ```python
   import re

   C3_PREVIEW = re.compile(r"This preview shows|Sign up to view the full|View Full Document|intentionally blurred sections")
   C3_TEASER = re.compile(r"\w(?:\.\.\.|…)$")

   def medicine_c3(text):
       if C3_PREVIEW.search(text):                     # paywall / preview page: cut by design
           return ("drop", text)
       s = text.rstrip()
       if C3_TEASER.search(s):                         # teaser cut: "...deeper unders..."
           last_stop = max(s.rfind(". ", 0, len(s) - 3), s.rfind(".\n", 0, len(s) - 3))
           return s[:last_stop + 1] if last_stop > 0 else text
       return text
   ```
3. **Action:** drop (previews) / fix (teasers).
4. **Harm test:** proxy 0 / 0. Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** a good document that merely quotes "View Full Document" would be dropped. Recall 15 / 49: a document that stops mid-solution with no marker (`b6a1ee1fa12a6d5e` code cut at @4908) cannot be detected by a rule. A first version that trimmed every last line without end punctuation changed 6 of 117 clean documents (headings, signatures, answer lists) and was replaced.

## Medicine 5: A1 invisible characters
1. **Disease:** A1, 15 documents. `064d8dd19536d1d8` U+200E LRM @9 (x2); `8f09ea36d06abaef` U+00AD soft hyphen @3180 (x4); `263a5308b96d2e4a` U+200B @6754.
2. **Medicine:** delete U+200B, U+FEFF, U+00AD, U+200E, U+200F, U+2060, U+202A–U+202E, U+2066–U+2069. ZWJ/ZWNJ are never touched (ruling 12).
   ```python
   import re

   # ZWJ U+200D / ZWNJ U+200C are left alone on purpose (they are script, not junk)
   A1_RX = re.compile("[​﻿­‎‏⁠‪-‮⁦-⁩]")

   def medicine_a1(text):
       return A1_RX.sub("", text)
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 / 0. Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** a ZWSP used as the only word separator joins two words. LRM/RLM matter in RTL text (safe in this English pack; do not run on RTL packs). U+2062 INVISIBLE TIMES in MathML text (1 document) is not removed.

## Medicine 6: B4 template junk
1. **Disease:** B4, 18 documents. `2d9c3add6852f806` "{{ 'ml-label-loading-course' | message }}" @0 (x14); `56027551326bb040` "{[ snackBarMessage ]}" @1482; `e967e3352605755f` "[TheoryMissing]" @102.
2. **Medicine:** delete `{[ name ]}`, `{{ name.attr | filter }}` (spaces inside, so LaTeX `{{x}}` is not hit), `{% … %}`, `[TheoryMissing]`, `document.write(…)`.
   ```python
   import re

   B4_RX = re.compile(r"\{\[\s*\w+\s*\]\}|\{\{\s+['\w][\w'.| :-]*\s+\}\}|\{%.*?%\}|\[TheoryMissing\]|"
                      r"document\.write\([^)]*\);?|^\s*\"?\s*%\}\s*$", re.M)

   def medicine_b4(text):
       out = B4_RX.sub("", text)
       return re.sub(r"\n{3,}", "\n\n", out) if out != text else text
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 / 0. Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** a tutorial that teaches Angular/Jinja templates would lose its examples. Recall 9 / 18: AsciiMath leftovers such as `color(blue)(` are not covered.

## Medicine 7: B5 broken LaTeX / markdown
1. **Disease:** B5, 28 documents. `e73db44e20a89b36` "$$$where" @241 (x4); `951a4c150e019bd5` "[itex]" @23031; `3a2ccc88dfcd67c9` unclosed ``` fence @12634.
2. **Medicine:** exactly `$$$` → `$$`; forum BBCode `[itex] [/itex] [tex] [/tex] [math]` → `$`; an odd number of ``` fences gets a closing fence at the end.
   ```python
   import re

   B5_TRIPLE = re.compile(r"(?<!\$)\${3}(?!\$)")                  # exactly $$$ ($$$$ is two blocks, valid)
   B5_BBCODE = re.compile(r"\[/?(?:itex|tex|math)\]", re.I)       # forum BBCode math

   def medicine_b5(text):
       out = B5_BBCODE.sub("$", B5_TRIPLE.sub("$$", text))
       if out.count("```") % 2:                                    # unclosed code fence at the end
           out = out.rstrip() + "\n```"
       return out
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 / 0. Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** found while testing: `$$$$` is two adjacent display blocks and is valid (`3e136806c369dfbc`), so only exactly three dollars are changed. A literal `[math]` in prose becomes `$`. Recall 5 / 28: stray `$$` inside inline math (`3f15fccd9f76020b`) and LaTeX with stripped backslashes (`$mathbb`) cannot be repaired by rule.

## Medicine 8: A3 mojibake
1. **Disease:** A3, 11 documents. `c9e5d27233084b62` "â€™" @178 (x24; U+00E2 U+20AC U+2122); `ab295000bded241a` "ðŸ˜€" @118; `f79e6aeb5ebb6a5c` "тАЩ" @4628 (UTF-8 read as cp866).
2. **Medicine:** a short run starting with a UTF-8 lead byte seen as cp1252 (`Â Ã â ð Ð Ñ à á ä`) is re-encoded as cp1252 and decoded as UTF-8; kept only if that succeeds and is shorter. Same for cp866 `т[АБ].`.
   ```python
   import re

   # cp1252 characters for the bytes 0x80-0x9F
   A3_CP1252_EXTRA = "€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ"
   # lead chars are the usual UTF-8 lead bytes seen as cp1252; not U+00D7 (x + no-break space is real maths)
   A3_MOJI = re.compile("[ÂÃâðÐÑàáä][\u0080-¿ -¿" + A3_CP1252_EXTRA + "]{1,3}")
   A3_CP866 = re.compile("т[АБ][Ѐ-ӿ]")    # UTF-8 read as cp866: "тАЩ" is a right quote

   def _a3_undo(m, enc):
       s = m.group()
       try:
           out = s.encode(enc).decode("utf-8")
       except (UnicodeEncodeError, UnicodeDecodeError):
           return s
       return out if len(out) < len(s) else s

   def medicine_a3(text):
       t = A3_MOJI.sub(lambda m: _a3_undo(m, "cp1252"), text)
       return A3_CP866.sub(lambda m: _a3_undo(m, "cp866"), t)
   ```
3. **Action:** fix. All 10 repairs checked by hand (`Ben’s`, `statistics…`, `plano–convex`, `Here’s`, 😀).
4. **Harm test:** proxy 0 / 0. Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** the first version accepted any Latin-1 lead and turned `×`+NBSP into Hebrew `נ` in 2 clean documents; the lead set is now restricted. Real Latin-1 text could still be "repaired" when the run happens to decode as UTF-8 (rare).

## Medicine 9: B2 HTML tags
1. **Disease:** B2, 8 documents. `bf73e54bda1aabdb` "<br />" @367 (x18); `addb07a0a886743c` "<ul>" @6030; `951a4c150e019bd5` "</Math>" @22663.
2. **Medicine:** `<br>` → newline; remove simple formatting tags (`p div span a ul ol li sup sub strong em font b i center`); skip documents with a code fence or `<script>`.
   ```python
   import re

   B2_BR = re.compile(r"<br\s*/?>", re.I)
   B2_TAG = re.compile(r"</?(?:div|span|p|a|ul|ol|li|sup|sub|strong|em|font|b|i|center)"
                       r"(?:\s+[\w-]+=(?:\"[^\"]*\"|'[^']*'|[^\s>]+))*\s*/?>", re.I)

   def medicine_b2(text):
       if "```" in text or "<script" in text.lower():      # tags inside code are content
           return text
       return B2_TAG.sub("", B2_BR.sub("\n", text))
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 / 0. Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** `x<sup>2</sup>` becomes `x2`. Recall 3 / 8: tags inside documents that also contain code, and broken fragments like `strong> Option`, are left.

## Medicine 10: A6 symbol-font private-use glyphs and look-alikes
1. **Disease:** A6, 9 documents. `9be631b8d8a8b294` U+F0C5 @6107 (should be ⊕); `c46f9ecdfac73e93` U+F0D8 @875 (x9); `f2746fa01fbc3cf4` "fɑstidious" @4992 (U+0251 U+0455 U+0461).
2. **Medicine:** map U+F000+code to the Symbol-font character for 46 codes (`(`, `)`, `=`, `⊕`, `∂`, Greek, brackets, …); leave other private-use characters.
   ```python
   # PDFs set in the Symbol font leak U+F0xx = U+F000 + Symbol code. Map the ones seen in the pack; leave the rest.
   A6_SYMBOL = {0x28: "(", 0x29: ")", 0x2B: "+", 0x2D: "−", 0x3D: "=", 0x44: "Δ", 0x53: "Σ", 0x57: "Ω",
                0x61: "α", 0x62: "β", 0x64: "δ", 0x67: "γ", 0x6C: "λ", 0x6D: "μ", 0x70: "π",
                0x71: "θ", 0x72: "ρ", 0x77: "ω", 0xA3: "≤", 0xA5: "∞", 0xA8: "♦", 0xAE: "→",
                0xB1: "±", 0xB3: "≥", 0xB4: "×", 0xB6: "∂", 0xB7: "•", 0xB9: "≠", 0xBB: "≈",
                0xC5: "⊕", 0xC7: "∩", 0xC8: "∪", 0xCE: "∈", 0xD6: "√", 0xD8: "¬", 0xDE: "⇒",
                0xE5: "∑", 0xE6: "⎛", 0xE7: "⎜", 0xE8: "⎝", 0xF2: "∫", 0xF6: "⎞", 0xF7: "⎟",
                0xF8: "⎠"}
   A6_PUA_MAP = {0xF000 + k: v for k, v in A6_SYMBOL.items()}

   def medicine_a6(text):
       return text.translate(A6_PUA_MAP)
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 / 0. Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** Wingdings uses the same code points: U+F0D8 as an arrow bullet becomes `¬`. Look-alike letters in spam (`fɑstidious`) and the Armenian apostrophe in `Math՚s` are not fixed (recall 5 / 9).

## Medicine 11: D3 mixed-in foreign script
1. **Disease:** D3, 10 documents. `b605c8aa5c37f266` Japanese title "ベクトル…" @23; `f2746fa01fbc3cf4` Ukrainian ad lines "Дивитися фільми…" @10238 (x4); `8210e5fa65c2f665` Marathi intro "पाईये" @144.
2. **Medicine:** delete a line when more than half of its letters are Cyrillic, Indic, CJK, kana, Hangul or Arabic; if such lines hold more than 30% of the document's letters, drop the document (that is D1).
   ```python
   import re

   # Cyrillic, Indic, kana, CJK, Hangul, Arabic (Greek is left out: Greek letters are maths)
   D3_FOREIGN = re.compile("[Ѐ-ӿऀ-෿぀-ヿ一-鿿가-힯؀-ۿ]")

   def medicine_d3(text):
       out, foreign = [], 0
       for l in text.split("\n"):
           letters = sum(c.isalpha() for c in l)
           f = len(D3_FOREIGN.findall(l))
           if letters and f / letters > 0.5:      # a line that is mostly foreign script is removed
               foreign += f
               continue
           out.append(l)
       total = sum(c.isalpha() for c in text)
       if total and foreign / total > 0.3:        # mostly not English: that is D1, drop
           return ("drop", text)
       return "\n".join(out)
   ```
3. **Action:** fix (drop when mostly foreign).
4. **Harm test:** proxy 0 / 0. Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** a legitimate quotation or title in another language is removed (DISEASES.md says D3 can be natural). Greek is excluded on purpose, since Greek letters are maths.

## Medicine 12: C4 two documents joined
1. **Disease:** C4, 7 documents. `dcaa196cc9b2af15` "A COVID-19 Prophecy" headline inside a units page @2843; `4d57615e33e7997e` "What mammal most abhors physical violence?" @573; `e68f196ec97b88a5` "What is Kanka?" @1865.
2. **Medicine:** none that is safe. A tested rule (cut a trailing block with no maths after a maths document) caught 0 of the labelled cases and changed 2 clean documents, so it is not proposed.
3. **Action:** drop by verdict. 4 of the 7 are also spam pages (C5) and are already `drop`; `e68f196ec97b88a5`, `c55fa2fcaeafd041` and `f6c1776061f622c6` (19 exam papers joined into one document) need the parts split or cut by hand or by a better splitter.
4. **Harm test:** not applicable (no automatic rule).
5. **Side effects:** none from automation; the cost is that C4 stays in documents nobody reviews.

## Medicine 13: D4 machine-translated or machine-spun text
1. **Disease:** D4, 22 documents. Most are SEO pages rewritten by a paraphrasing tool ("spun"): `4bbc06d580844d70` "optimistic integers that are only separating" @367 (for "positive integers that are only divisible"); `d3dc5a9f14a9a35a` "sine regulation" @658 (for "sine rule"); `a5d6914aacebfa97` "6 inches equals 3 thumbs up" @4121. A few are machine translations: `2b0dcb71433030d5` (German Wikipedia, LaTeX broken by the translator), `7fec63b917700801` "Because the byte unit inside the computer to represent the number are fixed-length" @478.
2. **Medicine:** no safe rule. Spun text is grammatical word by word; the signal is synonyms that make no sense in maths ("sine regulation", "optimistic integers"). A rule-based detector cannot see that without a language model. Proposed for later (not built, not tested): score each document with a small reference LM and a list of known spin substitutions ("sine regulation", "thumbs up" for inches, "optimistic" for positive), and send high scores to review.
3. **Action:** drop by verdict. 16 of the 22 are already `drop` (whole pages of spun SEO text); the 6 `fix` rows have one spun or translated paragraph inside an otherwise good page and need that paragraph cut by hand.
4. **Harm test:** not applicable (no automatic rule).
5. **Side effects:** none from automation. Ruling 11: ordinary spelling and grammar mistakes by people are not D4, so a future LM detector must be tuned not to flag forum posts by non-native writers.

## Medicine 14: A5 compatibility forms (PDF ligatures, fullwidth punctuation)
1. **Disease:** A5, 6 documents. `c16db13d63739369` "ﬀ" @313 (x91 ligatures: ﬀ ﬁ ﬂ ﬃ, U+FB00 U+FB01 U+FB02 U+FB03); `ce9b0d519779eba2` "ﬀ" @68 (x17); `addb07a0a886743c` fullwidth comma "，" @2666 (x2, U+FF0C) in English text translated from Chinese.
2. **Medicine:** replace the ligatures U+FB00–U+FB06 by their NFKC letters (ﬁ → fi, ﬀ → ff); replace fullwidth ASCII punctuation U+FF01–U+FF5E by the ASCII character, but only in documents where CJK characters are under 1% of the letters (real Chinese/Japanese text keeps its punctuation).
   ```python
   import re
   import unicodedata

   A5_LIG = re.compile("[ﬀ-ﬆ]")
   A5_FULLWIDTH = re.compile("[！-～]")
   A5_CJK = re.compile("[぀-ヿ一-鿿가-힯]")

   def medicine_a5(text):
       out = A5_LIG.sub(lambda m: unicodedata.normalize("NFKC", m.group()), text)      # ligature to letters
       letters = sum(c.isalpha() for c in out) or 1
       if len(A5_CJK.findall(out)) / letters < 0.01:                                    # leave real CJK text alone
           out = A5_FULLWIDTH.sub(lambda m: chr(ord(m.group()) - 0xFEE0), out)          # fullwidth to ASCII
       return out
   ```
3. **Action:** fix.
4. **Harm test:** see the table (proxy and gold columns). Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** a document that quotes a ligature as a character (a typography page) would lose it. Fullwidth digits in English text become ASCII digits, which is wanted here. Full NFKC is not applied: it would also change superscripts (x² → x2) and other maths symbols.

## Medicine 15: F1 personal data
1. **Disease:** F1, 7 documents (values never copied). `02c235b035b38798` email at offset 82 (x2); `ace41f52d349ca6b` email at offset 1447 (x2); `4477acbfa8e1a6da` phone number at offset 2074. Company numbers and business emails are not F1 (ruling 6).
2. **Medicine:** emails → `[email removed]`; NNN-NNN-NNNN phone numbers → `[phone removed]` when no digit is within 3 characters (skips number tables).
   ```python
   import re

   F1_EMAIL = re.compile(r"[\w.+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}")
   F1_PHONE = re.compile(r"(?<![\d.])(?:\+\d{1,3}[ -])?\(?\d{3}\)?[ -]\d{3}[ -]\d{4}(?![\d.])")

   def medicine_f1(text):
       t = F1_EMAIL.sub("[email removed]", text)
       def _f1_phone(m):
           around = t[max(0, m.start() - 3):m.start()] + t[m.end():m.end() + 3]
           return m.group() if re.search(r"\d", around) else "[phone removed]"   # skip number tables
       return F1_PHONE.sub(_f1_phone, t)
   ```
3. **Action:** fix.
4. **Harm test:** proxy 1 changed (0.85%). Gold: 0 / 30 changed, 0 dropped (PASS).
5. **Side effects:** business contacts are masked too (harmless for privacy; that is the proxy change). Recall 2 / 7: IP addresses (`0306000512344150`), obfuscated emails and messenger IDs are not matched.

---

### Found five times or fewer (no medicine required)
E1 code collapsed into one line by extraction, or generated code (5, `af9d1316d085d805` MATLAB program on one 3712-char line), E2 hash blobs and data arrays (5), B1 entities (4, `ab0dcfdea8b8f728` "&#40;1-2x&#41;"), D2 romanised Hindi (2, `c5b36a86af256f62` "Apne doubts clear karein"), A4 U+FFFD (3, `7c6df0c4a23c902b` "M�bius"), A2 control characters (3, `c16db13d63739369` U+0004), F2 competition problems from known contests (4: `296ba0775d5f6cca` IMO 2009 Q5, `b65447202cb074c9` AMC 8 2012, `8f09ea36d06abaef` IMO 1959 problem, `b22b5d72708d7f26` IMO 1964 problem), H2 (2), D1 (1, `ce878294b69f1b20` Chinese). No F3, E3, B3 or G-group cases.

### Not in the disease list
25 documents lost their formulas when the page was extracted (e.g. `161a7643db59ce25`, `8e9e5b4d6166454e`): the text says "the slope of the line tangent to the graph of at the point is". This is recorded in `note` only; it may deserve its own code.
