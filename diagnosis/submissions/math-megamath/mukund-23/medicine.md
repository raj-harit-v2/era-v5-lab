# Medicine sheet: math-megamath (mukund-23)

Each medicine is a Python function that takes the document text and returns the new text and the action ('keep', 'fix' or 'drop'). Shared imports and helper used by several of them:

~~~python
import re, unicodedata

FENCE = re.compile(r'```.*?```', re.S)

def _outside_code(text, fn):
    """Apply fn only to the parts of text outside ``` fences."""
    out, last = [], 0
    for m in FENCE.finditer(text):
        out.append(fn(text[last:m.start()])); out.append(m.group()); last = m.end()
    out.append(fn(text[last:]))
    return ''.join(out)
~~~

## Medicine 1

1. **Disease:** C1 (Boilerplate), found in 360 documents. Examples:
   - `e6a35e0a1697811c`: `Ads by Google` at offset 0
   - `d492cffdecdbee5e`: `## Answer This Question` at offset 536
   - `264f83c578759870`: `Reply Link.` at offset 2654
2. **Medicine:** Remove every line that consists only of a known piece of site chrome: share and comment widgets, sales buttons, Q&A templates, video-site boilerplate, chart download links, citation boxes, browser warnings, forum quote and member furniture, copyright and ad lines. Lines inside triple-backtick code fences are not touched. Only whole lines are removed, so a phrase inside a sentence is kept.

   ~~~python
   # C1 Boilerplate: remove whole lines that are known site chrome.
   C1_LINE = re.compile(r'''^\s*(?:
       Skip\ to\ content | Leave\ a\ (?:Reply|comment) | \#*\s*Leave\ a\ Reply | Share\ this:? | Like\ this:? | Like\ Loading\.\.\.
     | LikeLike | Reply(?:Delete)? | Reply\ Link\. | Subscribe\ to:? | Posts\ \(Atom\) | Print\ Page | Toggle\ navigation
     | Get\ Price | Get\ Best\ Quote | chat\ online | Read\ More | Learn\ More | More\ coming\ soon!
     | Study\ guides | Write\ your\ answer\.\.\. | Submit | Related\ questions
     | Want\ Lecture\ Notes\? | Please\ support\ me\ on\ Patreon!? | Download\ this\ (?:chart|table).* | Image\ \.csv\ \.xls
     | \*\*How\ to\ Cite\ This\ Entry:\*\* | You\ are\ using\ an\ out\ of\ date\ browser\..* | You\ should\ upgrade\ or\ use\ an\ alternative\ browser\.
     | Comments\ are\ no\ longer\ being\ accepted\. | Show\ Abstract | Quote: | Originally\ Posted\ by.* | Last\ edited.*
     | Join\ Date:.* | Posts:\ [\d,]+ | Thread\ Tools | Display\ Modes | Report\ Share | Share:
     | Copyright\ ©.* | ©\ .*\d{4}.* | All\ Rights\ Reserved\.? | Ads\ by\ Google | Advertisement
   )\s*$''', re.X | re.M | re.I)

   def c1_boilerplate(t):
       new = _outside_code(t, lambda s: C1_LINE.sub('', s))
       new = re.sub(r'\n{3,}', '\n\n', new)
       return (new, 'fix') if new != t else (t, 'keep')
   ~~~

3. **Action:** Fix (remove the matching lines).
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** It removes a line that is real content but happens to equal a chrome phrase, for example a forum post whose whole text is "Submit" or a lesson line "Read More". It misses chrome that is not on the list (most of the 360 rows have site-specific chrome), so it is a partial cure.

## Medicine 2

1. **Disease:** B5 (Markdown or LaTeX that is broken), found in 168 documents. Examples:
   - `fe174b7a4eefbe48`: `where .` at offset 72
   - `cb8eb128eb9a4068`: `equal to the .` at offset 1615
   - `30d58e04b952cb9e`: `defined for and conjectured that for all .` at offset 30
2. **Medicine:** When formulas are stripped, a function word is left directly before punctuation ("where .", "equal to the .", "If , then") or an empty "( )" remains. Count these gaps outside code fences. A document with 3 or more gaps is too damaged to read.

   ~~~python
   # B5 Broken markdown/LaTeX: stripped formulas leave a function word followed directly by
   # punctuation ("where .", "equal to the .", "If , then") or an empty "( )". Drop when 3+ gaps.
   B5_GAP = re.compile(r'\b(?:where|is|are|be|by|as|that|of|to|the|and|then|if|If|so|gives|becomes|equals|let|Let|for)\s+[.,;](?=\s|$)'
                       r'|\(\s*\)')

   def b5_stripped_formulas(t):
       gaps = len(B5_GAP.findall(FENCE.sub('', t)))
       return (t, 'drop') if gaps >= 3 else (t, 'keep')
   ~~~

3. **Action:** Drop the document.
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** It misses documents where the stripped formula leaves no function-word gap (a lead-in colon followed by the next paragraph). It can drop a good document that happens to contain three such patterns. It does not repair the other B5 forms (split bold markers, broken tables, escaped dollars).

## Medicine 3

1. **Disease:** C5 (Lists of keywords or links), found in 144 documents. Examples:
   - `50bbff56e6b37a90`: `Related questions` at offset 81
   - `014111869f4df84f`: `Displaying all worksheets` at offset 3259
   - `264f83c578759870`: `Pleonaste Sodalite` at offset 160
2. **Medicine:** A document of at least 15 non-empty lines (outside code) in which 70% or more of the lines are short fragments: 8 words or fewer, no sentence punctuation at the end, and no digits or math symbols.

   ~~~python
   # C5 Lists of keywords or links: at least 15 lines, and 70%+ of them are short fragments
   # (8 words or fewer, no sentence punctuation at the end, no digits or math symbols).
   C5_MATH = re.compile(r'[$=\\^_{}|]|\d')

   def c5_link_lists(t):
       lines = [l.strip() for l in FENCE.sub('', t).split('\n') if l.strip()]
       if len(lines) < 15: return t, 'keep'
       frag = [l for l in lines if len(l.split()) <= 8 and not re.search(r'[.?!:;]$', l) and not C5_MATH.search(l)]
       return (t, 'drop') if len(frag) / len(lines) >= 0.7 else (t, 'keep')
   ~~~

3. **Action:** Drop the document.
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** It drops a page that is a list but useful, for example a glossary of terms with no definitions on the same line. It misses lists that live inside a longer page (a "Related questions" block under a good answer), which is most of the 144 rows; those are left to C1.

## Medicine 4

1. **Disease:** C2 (Repeated lines), found in 105 documents. Examples:
   - `d5065048d4363e87`: `The irrationality of e can be proved` at offset 0 (twice)
   - `e2f7723d7ea2f3dc`: `Datasheet Format In Exel` at offset 1025 (3 times)
   - `264f83c578759870`: `Hundreds of mines are located` at offset 3881 (twice)
2. **Medicine:** Remove every later copy of a line of 40 or more characters that already appeared earlier in the document. Lines inside triple-backtick code fences are not touched.

   ~~~python
   # C2 Repeated lines: remove every later copy of a line of 40+ characters (outside code).
   def c2_dedupe(t):
       def dd(s):
           seen, out = set(), []
           for line in s.split('\n'):
               k = line.strip()
               if len(k) >= 40 and k in seen: continue
               if len(k) >= 40: seen.add(k)
               out.append(line)
           return '\n'.join(out)
       new = _outside_code(t, dd)
       return (new, 'fix') if new != t else (t, 'keep')
   ~~~

3. **Action:** Fix (keep the first copy of each line).
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** Some repeats are real content: two tables with the same header row, a textbook glossary that repeats a phrase, an exercise statement repeated in its solution, a definition shared by two terms. The rule removes those too. Code that is not fenced loses its repeated lines.

## Medicine 5

1. **Disease:** B2 (HTML or XML tags), found in 77 documents. Examples:
   - `1631de9c56cd0b38`: `<br>` at offset 353
   - `fac3fa734ed04785`: `<a href=` at offset 2971
   - `487387f6895a6833`: `<![CDATA[` at offset 0
2. **Medicine:** Outside code fences, replace `<br>` with a newline, remove common HTML tags (div, span, p, a, img, table cells, lists, headings, font, b, i, em, strong, sup, sub, code, pre) and remove CDATA wrappers.

   ~~~python
   # B2 HTML or XML tags: <br> becomes a newline, other known tags are removed (outside code).
   B2_BR = re.compile(r'<br\s*/?>', re.I)
   B2_TAG = re.compile(r'</?(?:div|span|p|a|img|table|tr|td|th|ul|ol|li|h[1-6]|font|b|i|em|strong|sup|sub|code|pre)\b[^<>]{0,200}/?>', re.I)
   B2_CDATA = re.compile(r'<!\[CDATA\[|\]\]>')

   def b2_tags(t):
       new = _outside_code(t, lambda s: B2_CDATA.sub('', B2_TAG.sub('', B2_BR.sub('\n', s))))
       return (new, 'fix') if new != t else (t, 'keep')
   ~~~

3. **Action:** Fix (remove the tags).
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** Text that discusses HTML outside a code fence loses its tags. Removing `<sup>` turns 10<sup>31</sup> into 1031, so a document with sup or sub tags needs the exponent kept by hand. It does not repair the larger part of B2 in this pack: words glued together where tags were already stripped ("applythe", "Losses1u").

## Medicine 6

1. **Disease:** G4 (Over-normalised), found in 56 documents. Examples:
   - `c39b918eca3d96f8`: `20080429` at offset 56
   - `fbc7c56923efc029`: `massspring` at offset 1458
   - `607211d7cc2611f7`: `twentyseven` at offset 242
2. **Medicine:** Restore hyphens in two safe patterns only: English number words ("twentyseven" becomes "twenty-seven") and 8-digit dates that are valid calendar dates and stand alone ("20080429" becomes "2008-04-29"). Dates inside URLs, paths, version stamps or longer numbers are not touched.

   ~~~python
   # G4 Over-normalised (deleted hyphens): restore two safe patterns only.
   NUM = r'(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)'
   UNIT = r'(?:one|two|three|four|five|six|seven|eight|nine)'
   G4_NUMWORD = re.compile(rf'\b({NUM})({UNIT})\b', re.I)
   G4_DATE = re.compile(r'(?<![\w/:.-])((?:19|20)\d\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?![\w/:.-])')

   def g4_hyphens(t):
       new = G4_NUMWORD.sub(r'\1-\2', t)
       new = G4_DATE.sub(r'\1-\2-\3', new)
       return (new, 'fix') if new != t else (t, 'keep')
   ~~~

3. **Action:** Fix.
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** An 8-digit number that is not a date but looks like one (a product code 20080429) gets hyphens. Deleted minus signs inside formulas cannot be restored by rule, because the original sign is unknown; documents where they change the mathematics should be dropped by a reader, as in our labels.

## Medicine 7

1. **Disease:** C3 (Truncated document), found in 45 documents. Examples:
   - `3a89917cc2de5d18`: `… Expand` at offset 789
   - `af0da3e1a9aa821e`: `forâ€¦` at offset 278
   - `d5065048d4363e87`: `Assume that e is` at offset 75 (text stops after this sentence)
2. **Medicine:** If the last non-empty line of the document ends in a cut-off marker ("...", "…", or "… Expand"), remove that line. If nothing is left, drop the document.

   ~~~python
   # C3 Truncated document: the last non-empty line ends in a cut-off marker ("...", "…", "… Expand").
   # Remove that last line; drop the document if nothing is left.
   C3_END = re.compile(r'(?:\.\.\.|…)(?:\s*Expand)?\s*$')

   def c3_truncated(t):
       body = t.rstrip()
       if not C3_END.search(body): return t, 'keep'
       rest = body.rsplit('\n', 1)[0].rstrip() if '\n' in body else ''
       return (rest + '\n', 'fix') if rest else (t, 'drop')
   ~~~

3. **Action:** Fix (remove the cut line), or drop if the document was only that line.
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** A post that really ends with an ellipsis ("thanks in advance...") loses its last line. It misses truncation without a marker, where the text simply stops mid-sentence.

## Medicine 8

1. **Disease:** C4 (Two documents joined), found in 36 documents. Examples:
   - `e2f7723d7ea2f3dc`: `AMIT 135` at offset 2981 (training notes inside a crusher SEO page)
   - `014111869f4df84f`: `LESSON 16:` at offset 2630 (lesson plan inside a slope SEO page)
   - `587de6ce9cffe118`: `They are distributed` at offset 0 (unrelated forum excerpts)
2. **Medicine:** Most joined documents in this pack are SEO pages that stitch search snippets together, each snippet with a sales or teaser button. Count these prompts ("Get Price", "Get Best Quote", "chat online", "Learn More", "Read More", "More###", "Continue Reading"). Three or more means a stitched page.

   ~~~python
   # C4 Two documents joined: SEO scrape pages that stitch search snippets together are marked by
   # repeated sales/teaser prompts. Drop when 3 or more such prompts appear.
   C4_PROMPT = re.compile(r'Get Price|Get Best Quote|chat online|Learn More|Read More|More###|Oline Chat|Continue Reading', re.I)

   def c4_joined(t):
       return (t, 'drop') if len(C4_PROMPT.findall(t)) >= 3 else (t, 'keep')
   ~~~

3. **Action:** Drop the document.
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** A good blog index page with three "Read More" links is dropped. Joined documents without such prompts (forum excerpt lists, merged threads) are missed.

## Medicine 9

1. **Disease:** F1 (Personal data), found in 36 documents. Examples:
   - `95627c7c24b4d18e`: personal email at offset 215
   - `8270757b82f6649c`: personal email written with " at " at offset 57
   - `3f2cae8c98fa6e7d`: personal email written with " at " at offset 65
2. **Medicine:** Mask email addresses, including the " at " spelling, with `<EMAIL>`. Do not mask Usenet message IDs (after Message-ID, References or news:), mailing-list and role addresses (info, support, sales, owner-..., ...-list, ...-discuss and similar), or strings whose domain part has no letters.

   ~~~python
   # F1 Personal data: mask email addresses, including ' at ' obfuscation. Not masked: message IDs
   # (inside <...> after Message-ID/References/news:), and list or role addresses.
   F1_EMAIL = re.compile(r'(?<![\w.+-])[\w.+-]+(?:@| at | AT )[A-Za-z][\w-]*(?:\.[A-Za-z][\w-]*)*\.[A-Za-z]{2,}\b')
   F1_ROLE = re.compile(r'^(?:info|support|sales|contact|admin|help|office|webmaster|customer|owner-[\w-]+|[\w-]*(?:list|-l|group|bounces|discuss|users|announce))(?:@| at )', re.I)

   def f1_mask(t):
       def rep(m):
           s, before = m.group(), t[max(0, m.start() - 30):m.start()]
           if F1_ROLE.match(s) or re.search(r'(?:Message-ID:|References\*?:|news:)\s*<?$', before, re.I) \
              or re.search(r'\$\d', s) or (before.endswith('<') and re.match(r'[\w.$%-]*\d[\w.$%-]*@', s)):
               return s
           return '<EMAIL>'
       new = F1_EMAIL.sub(rep, t)
       return (new, 'fix') if new != t else (t, 'keep')
   ~~~

3. **Action:** Fix (mask).
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** A phrase like "available at site.org" is masked as if it were an email. A personal address that looks like a role or list address (for example a local part ending in "-users" or "-group") is not masked. Names, phone numbers and street addresses are not covered.

## Medicine 10

1. **Disease:** A3 (Mojibake), found in 35 documents. Examples:
   - `6134c52da8a58271`: `algÃ¨bres` at offset 1058
   - `9a93353b16444362`: `Iâ€™ve` at offset 502
   - `af0da3e1a9aa821e`: `â€¦` at offset 281
2. **Medicine:** Find runs that look like UTF-8 read as Windows-1252 (a character such as Ã, Â or â followed by 1 to 3 characters from the Windows-1252 range). Encode each run back to Windows-1252 and decode it as UTF-8. If that fails, leave the run unchanged.

   ~~~python
   # A3 Mojibake: UTF-8 text decoded as Windows-1252. Re-encode each damaged run and decode it again.
   A3_RUN = re.compile(r'(?:[ÂÃÅÆâ][\u0080-¿ŒœŠšŸŽžƒˆ˜–-™]{1,3})+')

   def a3_mojibake(t):
       def rep(m):
           s = m.group()
           try: return s.encode('cp1252').decode('utf-8')
           except (UnicodeEncodeError, UnicodeDecodeError): return s
       new = A3_RUN.sub(rep, t)
       return (new, 'fix') if new != t else (t, 'keep')
   ~~~

3. **Action:** Fix.
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** It does not repair other damage that we also coded A3: Windows-1250 mojibake ("BirkhĂ¤user"), symbols replaced by "?" or letters, shifted font encodings. A real Ã followed by a symbol in Portuguese or French text could be changed, although the decode step fails safely in most such cases.

## Medicine 11

1. **Disease:** B4 (Template and code junk in prose), found in 15 documents. Examples:
   - `d77b6dc0ed5c0b90`: `[latex]` at offset 325 (440 times)
   - `d77b6dc0ed5c0b90`: `[hidden-answer a=` at offset 6682 (57 times)
   - `7471b9a550060215`: `=3DIF` at offset 11462
2. **Medicine:** Turn WordPress LaTeX shortcodes `[latex]x[/latex]` into `$x$`, and remove the `[hidden-answer ...]` and `[reveal-answer ...]` shortcodes and their closing tags.

   ~~~python
   # B4 Template and code junk: WordPress shortcodes. [latex]x[/latex] becomes $x$; answer shortcodes are removed.
   B4_LATEX = re.compile(r'\[latex\](.*?)\[/latex\]', re.S)
   B4_SHORT = re.compile(r'\[/?(?:hidden-answer|reveal-answer)[^\]]*\]')

   def b4_shortcodes(t):
       new = B4_SHORT.sub('', B4_LATEX.sub(r'$\1$', t))
       return (new, 'fix') if new != t else (t, 'keep')
   ~~~

3. **Action:** Fix.
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** A document that explains these shortcodes loses its examples. It covers only the shortcode form; quoted-printable residue (=3D), escape codes and template placeholders still need a reader.

## Medicine 12

1. **Disease:** D3 (Mixed language), found in 13 documents. Examples:
   - `3d76e832a73ee7ce`: `Wille, Würfel und Wahrscheinlichkeit` at offset 106
   - `fd8aa6b1dd4bb3a3`: `ulamki_porownanie` at offset 3288
   - `25d526a09832efea`: `गुणनखण्ड` at offset 44
2. **Medicine:** In this English pack, remove lines shorter than 40 characters that contain no ASCII characters and at least two letters in another script (language links, navigation and tag lines). Words in another language inside an English sentence are kept, because DISEASES.md says mixed language can be natural.

   ~~~python
   # D3 Mixed language: in an English pack, remove short lines (under 40 chars) that are only in a
   # non-Latin script (navigation, tags, language links). Inline words in English sentences are kept.
   D3_LINE = re.compile(r'^[^\x00-\x7FÀ-ɏ\n]{1,39}$', re.M)

   def d3_foreign_lines(t):
       def only_foreign(m):
           s = m.group()
           return '' if sum(ch.isalpha() for ch in s) >= 2 else s
       new = D3_LINE.sub(only_foreign, t)
       return (new, 'fix') if new != t else (t, 'keep')
   ~~~

3. **Action:** Fix (remove the line).
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** A short content line written in another script (a heading in Hindi on a bilingual textbook page) is removed. Mixed language in Latin script (German, French or Polish words) is not touched, so most of the 13 rows are not changed by this rule.

## Medicine 13

1. **Disease:** A5 (Wrong normal form), found in 10 documents. Examples:
   - `bfb8e74c830beb7a`: `beneﬁts` at offset 4378
   - `eb7319d7034a8a14`: `ﬂuid` at offset 2001
   - `2a420404633d31fd`: `ﬁeld` at offset 11638
2. **Medicine:** Replace the Latin ligature characters U+FB00 to U+FB06 (ﬀ, ﬁ, ﬂ, ﬃ, ﬄ, ﬅ, ﬆ) with their letter pairs, using NFKC on those characters only.

   ~~~python
   # A5 Wrong normal form: expand the Latin ligature characters U+FB00..U+FB06 (ﬁ, ﬂ, ﬀ, ...).
   def a5_ligatures(t):
       new = ''.join(unicodedata.normalize('NFKC', c) if 0xFB00 <= ord(c) <= 0xFB06 else c for c in t)
       return (new, 'fix') if new != t else (t, 'keep')
   ~~~

3. **Action:** Fix.
4. **Harm test:** gold set empty, not testable. The Data A gold set for this pack is not published yet. The test will run when it exists. Pass rule for the interim small gold sets: the medicine changes or drops at most 1 document or 1% of the gold set, whichever is larger.
5. **Side effects:** A text about typography that shows the ligature characters on purpose loses them. Other A5 damage, such as accents written as separate characters ("M´ethodes"), is not repaired.
