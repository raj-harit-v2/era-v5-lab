# Medicine sheet: ind-kn-fw2 (keshavamurali)

Pack: `ind-kn-fw2` (Kannada, 500 documents). Counts come from `labels.csv` (500 labelled rows).

**Gold set used for the harm test:** `teams/02-data-b/gold/ind-kn-fw2_gold.csv` as rebuilt on 2 Nov, the 114
documents of this pack that two readers marked clean (built by `teams/02-data-b/tools/gold_indic.py`).

The harm numbers below come from `teams/02-data-b/tools/harm_test_indic.py` run on these 114 documents. A rule may
change or drop at most 1% of the gold set or 1 document, whichever is more, so at most 1 of the 114. The sha256 in
each harm line is that of this file when the test ran; only the text around the code changed after that.

**How the code is laid out:**
- Each section's code runs on its own, as the harm tool runs it. Shared helpers are repeated in each section.
- Each rule takes the document text and returns the new text, or `True` to drop the document.
- The sections are in the order the medicines run: C2, C5, C1, G1. C5 runs before C1 because C1 removes the
  `N days ago` / `Read more` lines that C5 uses as signals.
- **Never removed:** a line with a ZWJ or ZWNJ, or with a compatibility character (`…`, `½`, full-width letters).
  The harm tool counts such a removal as damage.
- **Built for a larger corpus too:** C2, C5 and G1 look at one document at a time. C1's site templates are counted
  per website with an 8-byte hash per line (Medicine 3).
- The C1 section also holds the code that finds a pack's site templates (`_find_templates`), so the template list
  in the rule can be rebuilt from the pack.

## Medicine 1

1. **Disease:** C2 (repeated lines), 28 documents.
   - `17e5d6b10dc06231` (row 111): the dateline and lead `ಕಲಬುರಗಿ,ಏ.5:ಈಶಾನ್ಯ ಕರ್ನಾಟಕದ ಪ್ರವಾಸೋದ್ಯಮದ ಅಭಿವೃದ್ಧಿಗೆ …` (188 characters) twice, as the title and again as the first line of the body
   - `76fdbcb28c49fc27` (row 51): `ಸುದ್ದಿದಿನ.ಕಾಂ|ವಾಟ್ಸಾಪ್|<phone>` four times (site contact line; number not copied)
   - `0bc105464a1dbdf3` (row 369): `ಫೋಟೋ: ಪೋಲಿನಾ ಇನೊಜೆಮ್ಟ್ಸೆವಾ, ಚಾಂಪಿಯನ್ಶಿಪ್` eight times
2. **Medicine:** if a line of **30 or more characters** appears **2 or more times** in one document, keep only its
   first copy.
   - Short lines are never touched, so repeated words, answers (`ಹೌದು`), dialogue tags and quiz options stay.
   - Documents that look like verse are skipped entirely: 6 or more lines, more than half of them short (under 60 characters) and without a sentence end. Refrains are the writing style there, and a refrain can be longer than 30 characters (`ಇವನಾರವ ಇವನಾರವ ಇವನಾರವನೆಂದೆನಿಸದಿರಯ್ಯಾ` is 40).
   ```python
   import unicodedata
   from collections import Counter

   ZWJ, ZWNJ = chr(0x200D), chr(0x200C)
   END = re.compile(r'[.?!।॥"”\')]\s*$')   # a line that ends a sentence

   def _protected(line):
       return ZWJ in line or ZWNJ in line or any(unicodedata.decomposition(c).startswith('<') for c in line)

   def _short(l):
       return 0 < len(l) < 60 and not END.search(l)

   def _verse(t):
       ls = [l.strip() for l in t.split('\n') if l.strip()]
       return len(ls) >= 6 and sum(map(_short, ls)) / len(ls) > 0.5

   def medicine_c2(text, min_chars=30, times=2):
       if _verse(text):
           return text
       c = Counter(l.strip() for l in text.split('\n') if len(l.strip()) >= min_chars)
       rep = {l for l, n in c.items() if n >= times}
       seen, out = set(), []
       for l in text.split('\n'):
           s = l.strip()
           if s in rep and not _protected(s):
               if s in seen:
                   continue
               seen.add(s)
           out.append(l)
       return '\n'.join(out)
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 114 documents (ind-kn-fw2 114), medicine.md sha256 6662c45c666a; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 114 (0.00%). Dropped 0 of 114 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - Short repeated junk is not removed: `ಖರೀದಿಸಿ.` six times (row 369) and `ಚಿತ್ರಕೃಪೆ: rajkumar1220` five
     times (row 476). Medicine 3 catches such lines only when they repeat across a site's pages.
   - A long line that is repeated on purpose in prose, such as a quoted sentence or a question restated in an FAQ, loses its second copy.
   - Verse with long lines (6 or more lines that are mostly 60 characters or longer) is not seen as verse, so a long refrain there is thinned.
   - The 30-character limit counts code points, which suits Kannada (about 3 to 4 words). It is a parameter, to be set again for other scripts.

## Medicine 2

1. **Disease:** C5 (lists of keywords or links, teaser pages), 80 documents.
   - `dbbd14b33cfb0729` (row 37): `Display85`, `CPU43`, `GPU28` (spec widget and shop links)
   - `c472a3db00395ba6` (row 33): `ದಿನದ ಸುದ್ದಿ5 days ago` (related-headline teasers)
   - `bf21eb9f2a9511b6` (row 58): `Title`, `ಚಿತ್ರದುರ್ಗ | ನೀರಾವರಿ ಸಮಿತಿ ಅಧ್ಯಕ್ಷರ ಆಯ್ಕೆ ಪ್ರಕ್ರಿಯೆ ಸರಿಯಿಲ್ಲ : …` (headline list)
2. **Medicine:** short lines on their own are not a disease; poems, news highlights and credit blocks are short too.
   - **Block:** 3 or more consecutive short lines (under 60 characters, no sentence end), of which at least 2 carry a link or teaser signal: `N days ago`, `ಇನ್ನಷ್ಟು`, `Read more`, `Tag results`, a URL or `.com`, or `|`.
   - **Drop:** the whole document is dropped when more than 60% of its lines are short and at least 30% carry a signal.
   ```python
   import unicodedata

   ZWJ, ZWNJ = chr(0x200D), chr(0x200C)
   END = re.compile(r'[.?!।॥"”\')]\s*$')   # a line that ends a sentence
   SIGNAL = re.compile(r'\d+\s*(days?|hours?|minutes?|mins?) ago|ಇನ್ನಷ್ಟು|Read more|Tag results'
                       r'|https?://|www\.|\.com\b|\|', re.I)

   def _protected(line):
       return ZWJ in line or ZWNJ in line or any(unicodedata.decomposition(c).startswith('<') for c in line)

   def _short(l):
       return 0 < len(l) < 60 and not END.search(l)

   def medicine_c5(text):
       lines = text.split('\n')
       idx = [i for i, l in enumerate(lines) if l.strip()]      # non-empty lines, original positions
       ls = [lines[i].strip() for i in idx]
       sig = [bool(SIGNAL.search(l)) for l in ls]
       if len(ls) >= 5 and sum(map(_short, ls)) / len(ls) > 0.6 and sum(sig) / len(ls) >= 0.3:
           return True
       drop, run = set(), []
       for k in range(len(ls) + 1):
           if k < len(ls) and (_short(ls[k]) or sig[k]):
               run.append(k)
           else:
               if len(run) >= 3 and sum(sig[j] for j in run) >= 2:
                   drop.update(idx[j] for j in run if not _protected(ls[j]))
               run = []
       return '\n'.join(l for i, l in enumerate(lines) if i not in drop)
   ```
3. **Action:** fix the text (remove the block); drop the document when it is mostly a list.
4. **Harm test:** gold set of 114 documents (ind-kn-fw2 114), medicine.md sha256 6662c45c666a; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 114 (0.00%). Dropped 0 of 114 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - `|` is a signal, and Kannada verse uses `|` and `||` as line ends. Song lines in `634f9d4743893171` (row 31), such as `ಯಾರೇನೆಂದರು ನಿನಗೆ ಸದ್ಗುರು ದೇವ ||`, are removed with the headline block next to them.
   - A real list of links, for example a reference list at the end of an article, is removed.
   - Teaser lines that hold `…` stay, because of the never-removed rule (2 documents in this pack).
   - Most C5 pages without these signals are not caught.

## Medicine 3

1. **Disease:** C1 (boilerplate), 212 documents.
   - `5eaafa2efe204fb3` (row 8): `- Tag results for Subramanian Swamy`
   - `95fcd3a60a26a368` (row 19): `- Just In`, `- Don't Miss!`, `- News ಕರ್ನಾಟಕದಲ್ಲಿ 573 ಕೊರೊನಾ ಸೋಂಕಿತರು ಪತ್ತೆ`
   - `bfe4d0c9f43dc03b` (row 14): `‘ವಾರ್ತಾ ಭಾರತಿ’ ನಿಮಗೆ ಆಪ್ತವೇ ? …` and `ಬೆಂಬಲಿಸಲು ಇಲ್ಲಿ ಕ್ಲಿಕ್ ಮಾಡಿ` (the site's donation appeal, on all 7 of its pages)
2. **Medicine:** remove a line in any of these four cases:
   - (a) **site template:** the line is on 5 or more pages of the same website (host of the `url` column), and on
     at least 10% of that site's pages. A line that many different sites share, such as `ಧನ್ಯವಾದಗಳು` or a
     proverb, is never a template by this count.
   - (b) it matches a short list of boilerplate phrases;
   - (c) it starts with a dash or bullet followed by an English word. Tag pages, related-news links and ads use this format: `- Tag results for …`, `- Education …`, `- News …`;
   - (d) it is a bare dash followed by a `<category> N days ago` line, a teaser card.

   Finding the templates needs the URLs and the whole pack, but the harm tool passes the rule only the text. So the
   templates are found first with `_find_templates` (the second code block below), and the rule carries the 15
   template lines of this pack as 8-byte hashes. A hash also keeps the site's phone number out of this file.
   Examples of template lines: `Don't Miss!` (all 34 `kannada.filmibeat.com` pages), `Source link` (all 8
   `savikannada.in` pages), `ಟಾಪ್ ನ್ಯೂಸ್` (11 of 25 `udayavani.com` pages). On a whole pack, each site's own
   templates should be applied to that site only: `medicine_c1(text, templates=found[host])`.
   ```python
   import hashlib
   import unicodedata

   ZWJ, ZWNJ = chr(0x200D), chr(0x200C)
   BOILER = re.compile(r'Share on WhatsApp|Copyright|©|Leave a Reply|Team Udayavani|ಟಾಪ್ ನ್ಯೂಸ್'
                       r'|\d+\s*(days?|hours?|minutes?) ago|Read more|ಇನ್ನಷ್ಟು (ಓದಿ|ಸುದ್ದಿ)', re.I)
   DASH_EN = re.compile(r'^[ \t]*[-–•][ \t]+[A-Za-z].*$', re.M)
   DASH_BARE = re.compile(r'^[ \t]*[-–•][ \t]*\n[^\n]*\d+\s*days? ago[^\n]*$', re.M)
   TEMPLATES = frozenset({          # site-template lines of ind-kn-fw2, found by _find_templates below
       '0c61b19cfb72c68a', '1523d8487cd4c792', '33f8a3e8d468bc8a', '4c304be013888589',
       '54181b210567e69b', '714f62bb0822152b', '86796ef8093339d7', '9236d07688fe64f6',
       '9c5d9390e0604341', 'b3f8b6881e5db8b7', 'bbce4efb0877577a', 'be298df70325f3f8',
       'cd54a6b665b3a745', 'e73bc5bae38473b3', 'ff2cc858983d961c',
   })

   def _protected(line):
       return ZWJ in line or ZWNJ in line or any(unicodedata.decomposition(c).startswith('<') for c in line)

   def _key(line):
       return hashlib.blake2b(line.encode('utf-8'), digest_size=8).hexdigest()

   def medicine_c1(text, templates=TEMPLATES):
       def cut(m):
           return m.group() if _protected(m.group()) else ''
       t = DASH_BARE.sub(cut, text)
       t = DASH_EN.sub(cut, t)

       def boiler(l):
           s = l.strip()
           return not _protected(s) and ((len(s) >= 3 and _key(s) in templates) or BOILER.search(s))
       return '\n'.join(l for l in t.split('\n') if not boiler(l))
   ```
   Finding the site templates of a pack: pass the `url` and `text` columns as pairs. For this pack,
   `frozenset().union(*_find_templates(pairs).values())` gives the 15 hashes above.
   ```python
   from collections import Counter
   from urllib.parse import urlparse

   def _host_of(url):
       h = urlparse(url or '').netloc.lower()
       return h[4:] if h.startswith('www.') else h

   def _find_templates(docs, min_docs=5, min_share=0.1):
       """docs: (url, text) pairs of one pack. Returns {host: frozenset of template line hashes}.
       A line is a template of a site when it is on min_docs or more of the site's pages and on at least
       min_share of them. Counting per site keeps a line that many sites share from being a template."""
       f, per_host = Counter(), Counter()
       for url, text in docs:
           h = _host_of(url)
           if not h:
               continue
           per_host[h] += 1
           f.update((h, _key(l)) for l in {l.strip() for l in text.split('\n') if len(l.strip()) >= 3})
       out = {}
       for (h, k), n in f.items():
           if n >= max(min_docs, min_share * per_host[h]):
               out.setdefault(h, set()).add(k)
       return {h: frozenset(v) for h, v in out.items()}
   ```
3. **Action:** fix the text (remove the lines).
4. **Harm test:** gold set of 114 documents (ind-kn-fw2 114), medicine.md sha256 6662c45c666a; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 114 (0.00%). Dropped 0 of 114 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - A real Kannada bullet list that starts with an English word, such as `- WhatsApp ಮೂಲಕ…`, loses those lines.
   - A sentence that one site puts in many of its articles on purpose, such as a standard disclaimer, is removed.
   - Template lines on a site with fewer than 5 pages in the corpus are not found. A small pack finds less boilerplate than a large corpus.
   - Template lines that change from day to day, such as a "trending" headline box, can stay under the 10% share on a large site.
   - The hash list in this file belongs to this pack. For another pack or a larger corpus, find the templates again.
   - It catches only about half of the C1 documents. Menus and footers that are not repeated across a site's pages remain.

## Medicine 4

1. **Disease:** G1 (word cut at the vowel sign), 28 documents.
   - Only 2 documents in the pack have the exact pattern that this medicine fixes, so there are 2 examples:
     - `634f9d4743893171` (row 31): `ವಣ ್ಸುವಾಗ` (space before the virama)
     - `2914f93d5aa778b8` (row 253): `ವಸಡಿನ ೊಂದನ್ನು` (space before a vowel sign)
   - Most G1 damage in this pack is another kind:
     - a split between two full letters (`ಕರ್ನಾ ಟಕದ`, `e427affbdf302a39`, row 48);
     - legacy-font damage (`ಸಾಂಸ್ಕøತಿಕ`).
   - This regex cannot fix those.
2. **Medicine:** a Kannada dependent sign (vowel sign, virama, anusvara, visarga) can never start a word. Remove the
   space in front of it. Then normalise to NFC: a two-part vowel that was split (`ೆ` + space + `ೂ`) is not NFC once
   joined, and NFC composes it (`ೊ`).
   ```python
   import unicodedata

   G1 = re.compile(r'([\u0C80-\u0CFF]) ([\u0CBE-\u0CCD\u0CD5\u0CD6\u0C82\u0C83])')

   def medicine_g1(text):
       out = G1.sub(r'\1\2', text)
       return unicodedata.normalize('NFC', out) if out != text else text
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 114 documents (ind-kn-fw2 114), medicine.md sha256 6662c45c666a; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 114 (0.00%). Dropped 0 of 114 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - The join restores valid bytes but not lost letters. If a letter was dropped together with the space, the joined word is still wrong.
   - Text that shows a sign on its own on purpose, such as a grammar lesson that writes `ಾ`, is joined to the word before it.
   - A changed document is also normalised to NFC as a whole.

## All four in order

4. **Harm test:** gold set of 114 documents (ind-kn-fw2 114), medicine.md sha256 6662c45c666a; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 114 (0.00%). Dropped 0 of 114 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**



## C4: no rule needed

**C4 (two documents joined), 15 documents.** Examples: `d0a0a33b2b7ed888` (row 196), two separate news items;
`a701f2b6d7e7c7bd` (row 396), a legal news roundup with the headings stripped; `bafe29d8add27a01` (row 416), a news
piece followed by an advert.

- **Why there is no rule:** a disjoint document cannot be found by a rule on the text. A join has no fixed marker.
  Whether two paragraphs belong to one story depends on what they mean: an article that moves to a related point, a
  roundup of short items, or an op-ed that quotes other reports looks the same to a regex as two unrelated stories.
  Telling them apart needs topic segmentation by a model, or a reader.
- **What is already treated:** in this pack, most joins come from site pages that show several articles separated by
  a related-headline list, a "Trending" box or the site's contact line. Medicines 1 to 3 remove those blocks in 9 of
  the 15 C4 documents (for example rows 31, 33, 51, 58, 433). The articles on both sides of a removed block stay in
  one document.
- **Harm test:** no rule in code, so nothing to test: 0 of 114 gold documents changed or dropped.

## Diseases without a medicine

These diseases were found more than five times, but no rule is used on them as a medicine. Each entry gives the
reason: the rule fails the harm test (C3, G2), it can find the disease but not fix it (A6), the disease is labelled
rather than judged (D3), the rule catches too little or flags too many documents (D4, F3), or no rule is possible (D5).

Each candidate below was written as a rule and run on its own with `harm_test_indic.py` on the same gold set of 114
documents (ind-kn-fw2 114), each in its own section of a separate file. The code is shown as text so that the harm
tool does not run it with the medicines above. Each candidate returns `True` (drop, or flag for review) or `False`.

- **A6 (wrong or mixed script), 32 documents. Kept as a flag, not a medicine.**
  - **Rule:** flag Latin or legacy-font letters joined to a Kannada letter. A single `s` that ends a Kannada word is allowed, because it is valid dialect: `ಒಂದs`, `ತಾನs` in `92305d5a724c194a` (row 73).
    ```text
    MIXED = re.compile(r'[\u0C80-\u0CFF][A-Za-zøÆæ¸¹²³]+|[A-Za-zøÆæ¸¹²³][\u0C80-\u0CFF]')

    def medicine_a6(text):
        return any(not re.fullmatch(r'[\u0C80-\u0CFF]s', m.group()) for m in MIXED.finditer(text))
    ```
  - **Harm test:** changed 0 of 114 (0.00%), dropped 1 of 114 (0.88%). **PASS** (within the 1-document limit). ZWJ/ZWNJ audit and normal-form audit: **PASS.**
  - The one gold document it flags is `41932ab38a6fafb6` (row 172), where `ka.gov.inಗೆ` is a URL with a normal Kannada case suffix: a false alarm.
  - **Why not a medicine:** it flags 14 documents, only 7 of them labelled A6 (7 of 32 caught). Scripts cannot be fixed without a font map, so this is at most a flag.
- **C3 (truncated document), 14 documents. Fails.**
  - **Rule:** the last line, after credit lines (`ಚಿತ್ರ ಕೃಪೆ:`, `ವರದಿ:` …), has no sentence end.
    ```text
    END = re.compile(r'[.?!।॥"”\')]\s*$')
    CREDIT = re.compile(r'^(ಚಿತ್ರ ಕೃಪೆ|ಕೃಪೆ|ವರದಿ|ಹೇಳಿದವರು|ಲೇಖಕರು|ಲೇಖನ|Photo|Image|Source)\s*[:：]', re.I)

    def medicine_c3(text):
        ls = [l.strip() for l in text.split('\n') if l.strip()]
        while ls and CREDIT.search(ls[-1]):
            ls.pop()
        return bool(ls) and not END.search(ls[-1])
    ```
  - **Harm test:** changed 0 of 114 (0.00%), dropped 6 of 114 (5.26%). **FAIL.** ZWJ/ZWNJ audit and normal-form audit: **PASS.**
    The 6 gold documents: `942c1fdddfb8931c` (row 1, ends with `,`); `1db7c578463eb78c` (row 45),
    `51e9a734efdfb853` (row 144) and `8c692ecce3a2f2a1` (row 289), complete sentences with no full stop;
    `2a971489e8068e9c` (row 373) and `780c2ea64fce09d2` (row 462), which end with a narrator or author name on its
    own line.
  - It also flags 108 documents in the pack, only 7 of them labelled C3. A regex cannot tell a real cut from a
    closing comma, an author name, a poem or a sentence without a full stop. C3 is labelled by hand only.
- **D3 (mixed language), 92 documents. No medicine.**
  - **Rule:** Latin letters are 15% or more of all letters.
    ```text
    def medicine_d3(text, share=0.15):
        kn = len(re.findall(r'[\u0C80-\u0CFF]', text))
        la = len(re.findall(r'[A-Za-z]', text))
        return kn + la > 0 and la / (kn + la) >= share
    ```
  - **Harm test:** changed 0 of 114 (0.00%), dropped 0 of 114 (0.00%). **PASS.** ZWJ/ZWNJ audit and normal-form audit: **PASS.**
  - **Why not a medicine:** mixing Kannada and English can be natural, so D3 is labelled, not judged. The rule also
    catches only 12 of the 92 D3 documents (15 flagged).
- **D4 (bad machine translation), 33 documents. No medicine.**
  - **Rule:** 3 or more English words left untranslated between Kannada words.
    ```text
    LEFT_IN_ENGLISH = re.compile(r'[\u0C80-\u0CFF]+ [A-Za-z]{3,} [\u0C80-\u0CFF]+')

    def medicine_d4(text, times=3):
        return len(LEFT_IN_ENGLISH.findall(text)) >= times
    ```
  - **Harm test:** changed 0 of 114 (0.00%), dropped 0 of 114 (0.00%). **PASS.** ZWJ/ZWNJ audit and normal-form audit: **PASS.**
  - **Why not a medicine:** it catches only 4 of the 33 D4 documents (4 flagged, all labelled D4). Most D4 damage is
    wrong meaning, broken grammar or wrong gender and case, which needs a reader or a model, not a regex.
- **D5 (translationese), 8 documents. No medicine.**
  - **Rule:** none. Text that is grammatical but that no native speaker would write has no surface pattern.
  - **Harm test:** no rule in code, so nothing to test: 0 of 114 gold documents changed or dropped.
- **F3 (harmful content), 9 documents. Kept as a flag for review.**
  - **Rule:** spam keywords in English and Kannada.
    ```text
    SPAM = re.compile(r'dating|ಡೇಟಿಂಗ್|\bHGH\b|sex stor|ಸೆಕ್ಸ್|escort|casino|betting|ಬೆಟ್ಟಿಂಗ್|viagra|porn', re.I)

    def medicine_f3(text):
        return bool(SPAM.search(text))
    ```
  - **Harm test:** changed 0 of 114 (0.00%), dropped 0 of 114 (0.00%). **PASS.** ZWJ/ZWNJ audit and normal-form audit: **PASS.**
  - **Why not an automatic drop:** it catches only 4 of the 9 F3 documents and flags 8 documents without an F3 label,
    such as news that reports on these topics.
- **G2 (lost ZWJ or ZWNJ), 266 documents. Fails; no medicine.**
  - **Rule:** a Kannada conjunct (virama followed by a consonant) in a document that has no ZWJ or ZWNJ anywhere.
    ```text
    ZWJ, ZWNJ = chr(0x200D), chr(0x200C)
    CONJUNCT = re.compile(r'[\u0C80-\u0CFF]\u0CCD[\u0C80-\u0CFF]')

    def medicine_g2(text):
        return bool(CONJUNCT.search(text)) and ZWJ not in text and ZWNJ not in text
    ```
  - **Harm test:** changed 0 of 114 (0.00%), dropped 114 of 114 (100.00%). **FAIL.** ZWJ/ZWNJ audit and normal-form audit: **PASS.**
  - **Why:** the pack has no ZWNJ or ZWJ at all, so this is a pack-wide loss from upstream cleaning, and any rule that
    looks for it flags every document. A lost joiner looks the same as a normal conjunct, and restoring it needs a
    word list. It is reported upstream instead.
