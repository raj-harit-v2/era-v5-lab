# Medicine sheet: ind-ta-fw2 (truesrini)

Pack: 500 documents from FineWeb-2 Tamil, all read in full. My labels (`labels.csv`): 281 clean, 217 fix, 2 drop.
This is web crawl: news sites, blogs, novels, shop pages and some machine-translated content farms, so most
diseases are page furniture (footers, related links, tag pages) and machine translation.

Codes found more than five times: C1 (141), C3 (67), D4 (35), C2 (20), C5 (13), A6 (12), D3 (9), D1 (8), G3 (6),
A3 (6). Each has a section below; D3 and G3 have no rule in code, and the section says why.

Every medicine is a Python function `medicine_<code>`. It returns the new text (fix), the same text (no change), or
`True` (drop). Two rules (D4 and C5) need the page URL, so they take `doc` (a dict with `text` and `url`): Data A's
`harm_test.py` runs those, and `harm_test_indic.py` runs the text rules with the ZWJ/ZWNJ and NFC audits. The
sections are in run order: the drop rules first (D4, C5, C3, D1), then the fixes.

**Harm test (DISEASES.md section 4).** A rule passes when it changes or drops at most max(1, 1%) of the gold set.

- **Official gold set: pending.** `teams/02-data-b/gold/gold_coverage.csv` lists 0 gold documents for `ind-ta-fw2`.
  The gold set is the documents that both readers marked `clean`, and my labels were not in the repo yet.
- **Provisional gold, done.** The pack has two readers, Dharshanthaigu (PR #169) and me. We both marked 218
  documents `clean`, which is how the lab builds gold. Limit: max(1, floor(1% of 218)) = 2 documents. Every rule
  changed 0 and dropped 0 of them: `teams/01-data-a/harmtest/harm_test.py` for all eight rules, and
  `teams/02-data-b/tools/harm_test_indic.py` for the six text rules (ZWJ/ZWNJ and NFC audits ok).
- **Stand-in on my own 281 clean documents** (limit 2): every rule passes (C5 drops 1, the others change 0).

Commands, run from the repo root with a gold file `ind-ta-fw2_gold.csv` (columns doc_id,reader_1,reader_2):

```
python -I teams/01-data-a/harmtest/harm_test.py --pack ind-ta-fw2.parquet --gold ind-ta-fw2_gold.csv --rules medicine.md --rule C1 --show 10
python teams/02-data-b/tools/harm_test_indic.py --medicine medicine.md --pack ind-ta-fw2.parquet --gold-dir <folder of the gold file> --rule C1
```

**Speed.** The code is written for large data: every regex is compiled once, each rule first runs a cheap substring
or URL test and returns the text unchanged when it cannot apply, and C1 skips lines over 300 characters (the
paragraphs) without running its regex. On this machine (one core, Python 3.10) all eight rules together run over 20,000 documents (the pack 40 times, 58 M characters) in 3.0 s, about 6,576 documents a second; the first version took 17.8 s. Per rule: D4 0.02 s (was 0.12 s), C5 0.12 s (was 0.28 s), C3 0.34 s (was 1.64 s), D1 0.73 s (was 8.00 s), C1 0.72 s (was 1.10 s), C2 0.16 s (was 0.23 s), A3 0.55 s (was 4.80 s), A6 0.40 s (was 1.68 s).

"Treated" means the number of documents with that label that the rule changes or drops.

---

## Medicine 1: drop machine-translated mirror sites (D4)

1. **Disease:** D4, bad machine translation. Count in my pack: 35.
   - `c55beca33971ccca`: `சிஇஆர்டி உள்ளது Cநோய் எதிர்ப்பு சக்தி, Eநிச்சயதார்த்தம்` at 10701 (the acronym CERT spelled out as "C-immunity, E-engagement")
   - `89ff87a801db05db`: `பலர் ஏற்கனவே பாலூட்டிவிட்டனர்` at 3976 ("weaned off" rendered as "breast-fed")
   - `d71255737d1e08ee`: `அது யாருக்குத் தெரியும் மேற்கு உலகம் ஒரு நாள் நிஜமாகுமா? சரி, ஒரு வகையான.` at 86 (the title Westworld translated)
2. **Medicine:** the page URL decides. A `ta.` sub-domain of a foreign site, or a `/ta/` language path, is an
   automatic translation of an English or Russian site. Wikimedia and Vikaspedia (`ta.` sub-domains) and Vatican
   News and Cochrane (`/ta/` paths) publish human work there, so they are allowed.

   ```python
   import re
   from urllib.parse import urlsplit

   # D4: pages from machine-translated mirror sites. A "ta." sub-domain of a foreign site is an automatic
   # translation of an English or Russian site; Wikimedia and the government Vikaspedia are written by people.
   # A "/ta/" language path is the same kind of mirror, except on Vatican News and Cochrane (human translations).
   TA_HOST_OK = ("wikipedia.org", "wikisource.org", "wiktionary.org", "wikibooks.org", "vikaspedia.in")
   TA_PATH_OK = ("vaticannews.va", "cochrane.org")


   def d4_mt_mirror(t, url=""):
       if "ta." not in url and "/ta/" not in url:  # fast path: most URLs never get to urlsplit
           return t
       p = urlsplit(url)
       host = p.netloc.lower()
       if host.startswith("ta.") and not host.endswith(TA_HOST_OK):
           return None
       if p.path.startswith("/ta/") and not host.endswith(TA_PATH_OK):
           return None
       return t


   def medicine_d4(doc):
       out = d4_mt_mirror(doc["text"], doc.get("url") or "")
       return True if out is None else out  # None from the rule means drop
   ```

3. **Action:** drop. The meaning is wrong sentence by sentence, so there is nothing safe to fix.
4. **Harm test:**
   - Gold (provisional: the 218 documents both readers marked clean, limit 2): 0 changed, 0 dropped. **PASS**
   - Stand-in (my 281 clean documents, limit 2): 0 changed, 0 dropped, PASS.
   - Pack: drops 21 of the 35 D4 documents. Outside the label it drops 3 more: two content-farm pages I labelled C5
     and A6 (`ta.drjuventude.eu`, `lifepo4golfcartbattery.com/ta/`) and a porn page (F3).
5. **Side effects:**
   - It misses machine translation on normal Tamil news domains (14 documents, for example `வழக்குகள்`, court cases,
     for covid "cases", and the abbreviation splits such as `எஸ்.எஸ்.`). Those need a text model, not a URL rule.
   - A future site that publishes human Tamil translations under `/ta/` would be dropped until it is added to the allow list.

## Medicine 2: drop tag and section pages (C5)

1. **Disease:** C5, lists of keywords or links. Count in my pack: 13.
   - `432dd606f22c5ebc`: `பாம்பு ஒருவரை கடிக்கும் முன் எப்படி எச்சரிக்கும்?...` at 0, the first of 30 health headlines and travel ads (`/news_list/`)
   - `a12723436a0a5a31`: `பள்ளி மாணவர் தற்கொலை செய்துகொண்ட சம்பவத்தில்...` at 137, one of 10 teasers on a district section page
   - `103c0fc9df35b01e`: `- சென்னை மாநகராட்சி ஆணையருக்கு டெங்கு காய்ச்சல்` at 0, the first of 16 city headlines and job teasers
2. **Medicine:** drop the document when its URL is a listing URL (`/tag/`, `/tags/`, `/topic/`, `/category/`,
   `/entitysearch`, `/news_list`, a district edition page) and no line is long enough (250 characters) to be a paragraph.

   ```python
   import re
   from urllib.parse import urlsplit

   # C5: tag, topic, search and section pages: a listing URL and no line long enough to be a paragraph
   LIST_PATH = re.compile(r"/(?:tag|tags|topic|category|entitysearch|news_list)(?:/|\?|$)|/all-editions/[^/]+/[^/]+/?$")
   LONG_LINE = re.compile(r"[^\n]{250}")


   def c5_list_page(t, url=""):
       if not LIST_PATH.search(urlsplit(url).path):
           return t
       if t.count("\n") >= 3 and not LONG_LINE.search(t):
           return None
       return t


   def medicine_c5(doc):
       out = c5_list_page(doc["text"], doc.get("url") or "")
       return True if out is None else out  # None from the rule means drop
   ```

3. **Action:** drop.
4. **Harm test:**
   - Gold (provisional: the 218 documents both readers marked clean, limit 2): 0 changed, 0 dropped. **PASS**
   - Stand-in (my 281 clean documents, limit 2): 1 dropped (`80f59ddb40131238`, 20 unrelated Chennai headlines from `/entitysearch/`, labelled clean), PASS.
   - Pack: drops 2 of the 13 C5 documents. Outside the label it also drops `80f59ddb40131238` (labelled clean),
     `f8b9215dbe90215c` (`/topic/CSK`, labelled D1) and `8048597ad756a8bf` (`/topic/Ayalaan`, labelled C1): all three are teaser pages.
5. **Side effects:**
   - Keyword lists inside a normal article (SEO tag lines, `Stephan Hawkings / Stefan Howking`, "Tablet Uses in Tamil"
     link lists) and listing pages on ordinary URLs are not caught (11 documents).
   - A first version that dropped any page made only of short lines dropped 14 clean documents (dialogue-heavy
     novels, short news), so the URL is needed.

## Medicine 3: drop pages that show only the start (C3)

1. **Disease:** C3, truncated document. Count in my pack: 67.
   - `aebffbe78a715708`: `Page 1 of 9` at 0; the text stops at `அதிலும் மடத்து நிலங்கள். எல்லாம்`
   - `bb2b71743bc56c9b`: `இன்றைய இந்தக் கட்டுரையை தொடர்ந்துப் படிக்க, மெட்ராஸ் பேப்பருக்கு சந்தா எடுக்கவும்!` at 765 (paywall)
   - `56e2d441dc41ded6`: `… Continue reading` in a WordPress embed card
   - Most of the 67 end on a footer or widget line (`Last Updated 15, Nov 2018, 1:11 PM`, `Next Story`,
     `Advertisement`) rather than mid-sentence; the scanner reads that as a cut ending.
2. **Medicine:** drop the document when it carries a cut marker: `… Continue reading`, `Page 1 of N` on its own
   line, or a Tamil paywall line. A page that only ends on a footer is not dropped: Medicine 5 (C1) removes the footer.

   ```python
   import re

   # C3: the page shows only the start of the article (embed card, pager, paywall)
   CUT_MARK = re.compile(r"… Continue reading|^Page 1 of \d+$|தொடர்ந்துப் படிக்க, .{0,40}சந்தா|ப்ரீமியம் கட்டுரை இது", re.M)
   CUT_HINTS = ("Continue reading", "Page 1 of", "சந்தா", "ப்ரீமியம்")


   def c3_cut_page(t, url=""):
       if not any(h in t for h in CUT_HINTS):  # fast path: plain substring tests before the regex
           return t
       return None if CUT_MARK.search(t) else t


   def medicine_c3(text):
       out = c3_cut_page(text)
       return True if out is None else out  # None from the rule means drop
   ```

3. **Action:** drop. The rest of the article is not in the crawl.
4. **Harm test:**
   - Gold (provisional: the 218 documents both readers marked clean, limit 2): 0 changed, 0 dropped. **PASS**
   - Stand-in (my 281 clean documents, limit 2): 0 changed, 0 dropped, PASS.
   - Pack: drops 5 of the 67 C3 documents, and Medicine 5 (C1) fixes the ending of 30 more. Nothing outside the label is touched.
5. **Side effects:**
   - Pages that simply stop mid-sentence with no marker (a Wikisource page end, a Q&A farm) are not caught (32 documents).
   - A complete article that quotes the words "Continue reading" would be dropped. None in this pack.

## Medicine 4: drop pages that are mostly not Tamil (D1)

1. **Disease:** D1, wrong language label. Count in my pack: 8.
   - `b8e129dc12b2885a`: `The search feature allows you to easily find people on your Workplace.` at 108 (a help page, 43% Tamil letters)
   - `5ca9f296cba469ed`: `These are Makara Sankaranthi - Pongal celebration photos.` at 0 (a bilingual blog, 43% Tamil letters)
   - `22e396281a59eeb4`: `We’re back baby!` and `— Anirudh Ravichander (@anirudhofficial) February 12, 2020` at 1148 (an English tweet quoted in a Tamil article)
2. **Medicine:** drop the document when fewer than 60% of its letters are Tamil. The lowest real Tamil page in this
   pack is at 72%, so 60% leaves a margin.

   ```python
   import re
   TA = "஀-௿"

   # D1: wrong language label. Fewer than 60% of the letters are Tamil: the page is mostly English.
   # The lowest real Tamil page in this pack is at 72%.
   TA_LETTER = re.compile(f"[{TA}]")
   LATIN_LETTER = re.compile(r"[A-Za-z]")


   def d1_not_tamil(t, url=""):
       la = len(LATIN_LETTER.findall(t))
       if la * 10 < len(t):  # fast path: under 10% Latin characters; a drop would need over 83% non-letters
           return t
       ta = len(TA_LETTER.findall(t))
       return None if ta + la and ta / (ta + la) < 0.6 else t


   def medicine_d1(text):
       out = d1_not_tamil(text)
       return True if out is None else out  # None from the rule means drop
   ```

3. **Action:** drop.
4. **Harm test:**
   - Gold (provisional: the 218 documents both readers marked clean, limit 2): 0 changed, 0 dropped; ZWJ/ZWNJ and NFC audits ok. **PASS**
   - Stand-in (my 281 clean documents, limit 2): 0 changed, 0 dropped, PASS.
   - Pack: drops 2 of the 8 D1 documents (the two mostly-English pages) and touches nothing outside the label.
5. **Side effects:**
   - The other six D1 documents are Tamil articles with English inside: a quoted tweet, an English headline or URL
     slug (`sawreb netravelker - india america captan`). That English is part of the content, so it is kept: no
     rule removes it, and C1 leaves it alone on purpose.
   - A Tamil page that quotes long English passages (a bilingual lesson) would be dropped. None in this pack.

## Medicine 5: remove boilerplate lines (C1)

1. **Disease:** C1, boilerplate. Count in my pack: 141.
   - `9e5239c638f4e5ed`: `Sign up to receive our newsletter in your inbox every day!` at 2197 (the last line)
   - `ea25ede399f43283`: `Edited by Mahendran` at 818 (the last line)
   - `073e5fef33d63579`: `Latest Photos:` at 1295 (a gallery label as the last line)
2. **Medicine:** delete a whole line when it is a known site widget (newsletter, "Advertisement", "Next Story",
   "View this post on Instagram", "Latest Photos:", embed instructions, "Page 1 of 9", "Last Updated"), a Tamil
   "read this too" line (`இதையும் படியுங்கள்...`), a follow-us or share line, or a bare site name; and trim a share
   phrase glued to the last sentence. Other English lines (tweets, headlines, URL slugs) are not touched: they are
   content, labelled D1 where they matter.

   ```python
   import re

   # C1: boilerplate lines. A line is removed only when the whole line is a known widget. Every widget is under
   # 300 characters, so longer lines (the paragraphs, most of the text) are skipped without running the regex.
   # English lines that are not widgets (tweets, slugs, headlines) are left: they are content or a language issue
   # (D1), not boilerplate.
   _C1_LINE = re.compile(
       r"[ \t]*(?:"
       r"Sign up to receive our newsletter in your inbox every day!"
       r"|Read Exclusive COVID-19 Coronavirus News updates, at Asianet News Tamil\."
       r"|Advertisement|Don't Miss!|Trending|Latest|Breaking News|Next Story|Related Tags ?:?|Related posts:"
       r"|View this post on Instagram|Copy and paste this (?:URL|code) into your (?:WordPress )?site to embed"
       r"|English Summary|Description|Latest Photos:|Read More:|Comments|Post a Comment"
       r"|Web Title:.*|Edited by [A-Za-z .]+|Page \d+ of \d+|Developed by - .*|Disclaimer: .*"
       r"|Top posting users this month|Permissions in this forum:.*|Win Big, Make Your Cricket Tales Now"
       r"|Last (?:Updated|Modified)[ \t]*:?.*"
       r"|\(?(?:இதையும்|மேலும்|இன்னும்) (?:படி|பாரு|பார்)[^\n]{0,150}"            # "read this too" links
       r"|.{0,30}(?:டெலிக்ராம்|டெலிகிராம்|இன்ஸ்டாகிராம்)[ \t]*:.{0,60}"            # follow-us lines
       r"|.{0,60}(?:டெலிகிராம் ஆப்பில் பெற|கூகுள் செய்திகள் பக்கத்தில்).{0,80}"
       r"|.{0,40}(?:நண்பர்களுடன் பகிர்ந்து கொள்ளுங்கள்|இந்த காலவரிசையைப் பகிரவும்).{0,20}"  # share lines
       r"|[a-z0-9.-]+\.(?:in|com|lk|net|org)"                                     # a bare site name ("newstm.in")
       r")[ \t]*"
   )
   _SHARE_TAIL = re.compile(r"இந்த காலவரிசையைப் பகிரவும்[ \t\n]*$")  # a share button glued to the last sentence


   def c1_boilerplate(t, url=""):
       lines = t.split("\n")
       keep = [ln for ln in lines if len(ln) > 300 or not _C1_LINE.fullmatch(ln)]
       out = "\n".join(keep) if len(keep) < len(lines) else t
       if "பகிரவும்" in out:
           out = _SHARE_TAIL.sub("", out)
       if out is t:
           return t
       out = out.rstrip("\n ")  # only newlines and spaces: a no-break space must survive
       if out == t.rstrip("\n "):
           return t
       return out if len(out) >= 150 else None


   def medicine_c1(text):
       out = c1_boilerplate(text)
       return True if out is None else out  # None from the rule means drop
   ```

3. **Action:** fix. Drop only if less than 150 characters are left.
4. **Harm test:**
   - Gold (provisional: the 218 documents both readers marked clean, limit 2): 0 changed, 0 dropped; ZWJ/ZWNJ and NFC audits ok. **PASS**
   - Stand-in (my 281 clean documents, limit 2): 0 changed, 0 dropped, PASS.
   - Pack: treats 80 of the 141 C1 documents. Outside the label it changes 2 documents labelled D1, where it removes
     only an `Advertisement` line and keeps the English content.
   - An earlier version also removed pasted tweets and English lines at the very start or end of a page. It changed 3
     of my clean documents. Two of them (`22e396281a59eeb4`, `4ce70e36e83b8691`) hold English that is content, so I
     relabelled them D1 and took those two parts out of the rule; the third (`073e5fef33d63579`) is real
     boilerplate and is now labelled C1.
5. **Side effects:**
   - Unrelated "related story" headlines in the middle of an article are plain Tamil sentences, and English slugs or
     tweets are now kept as content, so the rule does not treat them (most of the 61 untreated documents).
   - A byline under the headline (`By Aruvi | Galatta | Sep 05, 2020, 08:44 pm`) is not removed.

## Medicine 6: remove the repeated headline line (C2)

1. **Disease:** C2, repeated lines. Count in my pack: 20.
   - `1764f27a3eea3f9f`: `படையப்பா படத்தில் முதலில் நடிக்கவிருந்தது இந்த பிரபலமா?...` at 0 and again at 95 (the headline twice)
   - `a30ed1434333cc5c`: `தேசியவாத காங்கிரஸ், திரிணமூல் காங்கிரஸ், சி.பி.ஐ ஆகிய கட்சிகளை...` at 0, repeated as the last line
   - `64d8aac92c8d369f`: `Villupuram court acquitted first two accused in srimathi death case` at 85, repeated after "English Summary"
2. **Medicine:** delete a later copy of a line only when the first copy is one of the first three lines
   (headline, summary, slug) and is longer than 20 characters.

   ```python
   import re

   # C2: a line printed twice by the page template. Only a later copy of one of the first three lines (the
   # headline, the summary, a slug) is removed, so a refrain or a repeated heading in the body stays.
   def c2_repeats(t, url=""):
       head = t.split("\n", 3)[:3]
       cands = {ln.strip() for ln in head if len(ln.strip()) > 20}
       if not any(t.count(c) > 1 for c in cands):  # fast path: no head line occurs twice
           return t
       seen, out = set(), []
       for line in t.split("\n"):
           key = line.strip()
           if key in cands and key in seen:
               continue
           seen.add(key)
           out.append(line)
       return "\n".join(out)


   def medicine_c2(text):
       out = c2_repeats(text)
       return True if out is None else out  # None from the rule means drop
   ```

3. **Action:** fix.
4. **Harm test:**
   - Gold (provisional: the 218 documents both readers marked clean, limit 2): 0 changed, 0 dropped; ZWJ/ZWNJ and NFC audits ok. **PASS**
   - Stand-in (my 281 clean documents, limit 2): 0 changed, 0 dropped, PASS.
   - Pack: treats 16 of the 20 C2 documents and touches nothing outside the label.
5. **Side effects:**
   - Repeats that start in the body, and a headline and summary that are near (not exact) repeats, are left (4 documents).
   - A first version that removed every repeated line changed 2 clean documents (a song refrain, a repeated heading).

## Medicine 7: undo legacy-font leftovers (A3)

1. **Disease:** A3, mojibake from a legacy Tamil font (Bamini style). Count in my pack: 6.
   - `817263226f2d16db`: `இருந்தார்;;;;;;;.` (26 U+003B SEMICOLON, 31 times in the document)
   - `03f21bf2abdef067`: `ஏற்படுத்துகிறதுஇ அத்துடன்` (1551 U+0B87 TAMIL LETTER I, expected U+002C COMMA)
   - `d642024607c9d273`: `போலீஸôரும்` (709 U+00F4 LATIN SMALL LETTER O WITH CIRCUMFLEX, expected U+0BBE TAMIL VOWEL SIGN AA)
2. **Medicine:** three narrow repairs: remove `;;` runs or `;.` after a pulli or vowel sign, turn a word-final
   `இ` before a space into a comma, and turn `ô` after a Tamil consonant into `ா`.

   ```python
   import re

   # A3: legacy-font (Bamini-style) conversion leftovers
   PULLI_SEMI = re.compile(r"(?<=[ா-்])(?:;{2,}|;(?=\.))")  # ';;' or ';.' after a pulli or vowel sign
   I_COMMA = re.compile(r"(?<=[க-ஹா-ௌ])இ(?= )")             # a word ending in the letter இ was a comma
   O_CIRC = re.compile(r"(?<=[க-ஹ])ô")                       # ô after a consonant was the vowel sign ா


   def a3_legacy_font(t, url=""):
       if ";" in t:
           t = PULLI_SEMI.sub("", t)
       if "இ " in t:
           t = I_COMMA.sub(",", t)
       if "ô" in t:
           t = O_CIRC.sub("ா", t)
       return t


   def medicine_a3(text):
       out = a3_legacy_font(text)
       return True if out is None else out  # None from the rule means drop
   ```

3. **Action:** fix.
4. **Harm test:**
   - Gold (provisional: the 218 documents both readers marked clean, limit 2): 0 changed, 0 dropped; ZWJ/ZWNJ and NFC audits ok. **PASS**
   - Stand-in (my 281 clean documents, limit 2): 0 changed, 0 dropped, PASS.
   - Pack: treats 3 of the 6 A3 documents. Outside the label it changes 1 document (`ஆனார்;.`, a real stray semicolon).
5. **Side effects:**
   - Single leftover semicolons (`பதவிக்கும்; அரசியலமைப்பு`) are left, because a single `;` is also normal Tamil
     punctuation; a first version that removed them changed 13 clean documents.
   - English words or URLs typed through a Tamil font (`தீதீதீ` for "www") cannot be undone by a rule.

## Medicine 8: remove a stray Latin letter after a Tamil word (A6)

1. **Disease:** A6, wrong or mixed script. Count in my pack: 12.
   - `f33fb2b187960fd7`: `ஜெயிலில் அடைப்புd` (58 U+0064 LATIN SMALL LETTER D)
   - `940d6d6ecd23174f`: `நேரடியாf வளர்ந்திருக்கும்` (4720 U+0066 LATIN SMALL LETTER F, expected U+0B95 TAMIL LETTER KA)
   - `315294ec820a9d4e`: `வெள்ளத்த்pல்` (4438 U+0070 LATIN SMALL LETTER P, expected U+0BBF TAMIL VOWEL SIGN I)
2. **Medicine:** remove one lowercase Latin letter that sits between a Tamil character and a space or a punctuation mark.

   ```python
   import re
   TA = "஀-௿"

   # A6: one stray Latin letter glued to the end of a Tamil word ("அடைப்புd", "நேரடியாf")
   # the letter is matched first and the Tamil character checked behind it: about 4x faster than a leading lookbehind
   STRAY_LATIN = re.compile(rf"[a-z](?<=[{TA}][a-z])(?=[\s.,!?]|$)")


   def a6_stray_latin(t, url=""):
       return STRAY_LATIN.sub("", t)


   def medicine_a6(text):
       out = a6_stray_latin(text)
       return True if out is None else out  # None from the rule means drop
   ```

3. **Action:** fix.
4. **Harm test:**
   - Gold (provisional: the 218 documents both readers marked clean, limit 2): 0 changed, 0 dropped; ZWJ/ZWNJ and NFC audits ok. **PASS**
   - Stand-in (my 281 clean documents, limit 2): 0 changed, 0 dropped, PASS.
   - Pack: treats 2 of the 12 A6 documents. Outside the label it changes 1 document (a legacy-font page labelled A3, where the letter was also stray).
5. **Side effects:**
   - Six of the 12 are a whole English word between Tamil words (`simian`, `aka`, `shpae`). That is mixed language,
     not a broken letter, so the rule leaves them on purpose.
   - Latin letters inside a word (`வெள்ளத்த்pல்`), a capital before Tamil (`Aஅவர்`) and Latin look-alikes (`செய்தõன்`) are not caught.

## Medicine 9: none for natural code-mixing (D3)

1. **Disease:** D3, mixed language. Count in my pack: 9.
   - `ed5f1dd9278d0f2a`: `Oracle Engineered Systems Database Administrator பணிக்கென` at 188
   - `264798d24ec2bd8a`: `Ingredients for ரசகுல்லா` at 470
   - `87eac8d1e10f2eda`: `பின் Edit மெனு சென்று Paste Special பிரிவில் கிளிக் செய்திடு` at 920
2. **Medicine:** none, so there is no code block. DISEASES.md says D3 can be natural: label it, do not judge it.
3. **Action:** keep, no change.
4. **Harm test:** nothing changes, so 0 changed and 0 dropped on any set.
5. **Side effects:** none. Machine translation that leaves English words untranslated is D4, not D3.

## Medicine 10: none for a dropped lead paragraph (G3)

1. **Disease:** G3, content removed by an earlier step. Count in my pack: 6.
   - `e1d78d71db89ef2c`: `அவற்றை, எதிர்வரும் நவம்பர் மாதம் 15 ஆம் திகதிக்கும்...` at 0 (starts with "them")
   - `90fc2ac18d4ca2df`: `அதாவது அதானி குழுமம் குறித்து கடந்த வாரம்...` at 0 (starts with "that is")
   - `3d85708af56e6599`: `அதன்படி, சிபிஎஸ்இ 12ஆம் வகுப்பு பொதுத்தேர்வு...` at 36 ("accordingly", after a subheading)
2. **Medicine:** none that fixes the text, so there is no code block. The lead paragraph is not in the crawl, and a
   drop rule on such opening words would also drop complete articles that start with `இந்த நிலையில்` after a dateline.
3. **Action:** keep, no change. Report the count to the extraction team.
4. **Harm test:** nothing changes: 0 changed and 0 dropped.
5. **Side effects:** none from the medicine. Six documents keep a missing first paragraph.
