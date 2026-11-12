# Medicine sheet: en-dclm (mittalutkarsh)

Pack: `en-dclm`, 500 documents, all read in full.
Gold set used for the harm tests: `teams/01-data-a/gold/en-dclm_gold.csv`, 62 documents.

Seven diseases appear more than five times in my slice, so there are seven medicines below.
Counts are from my `labels.csv` in this folder.

| Code | Count | Action |
|---|---|---|
| C1 | 273 | fix |
| C3 | 21 | drop |
| C4 | 20 | drop |
| C5 | 19 | drop |
| A1 | 11 | fix |
| B4 | 9 | fix |
| D4 | 6 | drop |

A note on the harm tests before the medicines. The gold set for this pack has 62 documents. One percent
of 62 is 0.62, so the threshold is crossed by a single document: one changed or dropped gold document
scores 1.61% and fails. Every medicine below is therefore written to touch nothing unless it is certain,
and each one is measured against the whole 62.

All seven pass at 0.00%, and so does the whole sheet run in file order. Because a rule that does nothing
also passes, each medicine below also reports its **reach**: how many of the documents I labelled with that
disease it actually acts on. Those two numbers should be read together.

| Rule | Gold changed | Gold dropped | Percent | Result | Reach on my slice |
|---|---|---|---|---|---|
| C1 | 0 | 0 | 0.00% | PASS | 98 of 273 |
| C3 | 0 | 0 | 0.00% | PASS | 2 of 21 |
| C4 | 0 | 0 | 0.00% | PASS | 0 of 20 |
| C5 | 0 | 0 | 0.00% | PASS | 4 of 19 |
| A1 | 0 | 0 | 0.00% | PASS | 11 of 11 |
| B4 | 0 | 0 | 0.00% | PASS | 5 of 9 |
| D4 | 0 | 0 | 0.00% | PASS | 1 of 6 |
| ALL IN ORDER | 0 | 0 | 0.00% | PASS | — |

---

## Medicine 1

1. **Disease:** C1

   Boilerplate. Navigation, comment furniture, sharing widgets and footers left in the text by the
   extractor. 273 documents, by far the largest disease in the pack.

   Three examples:

   - `5f0d56eb27f018bd` — `Make another search.` at offset 512, `Related games:` at offset 968
   - `a6673336e37d2ca9` — `You are here: Home >` at offset 17, `Related Links:` at offset 10208
   - `0864734353e1b73e` — `YOU ARE HERE: LAT HomeCollections` at offset 0

2. **Medicine:** remove a line when the whole line, ignoring surrounding spaces, is one of a fixed list of
   blog and news furniture strings, or is a comment counter such as `3 comments:`. Matching is on the
   complete line, never on a substring, so a sentence that happens to contain one of these phrases is left
   alone. After the removal, runs of three or more blank lines collapse to two.

   The list was built only from strings I saw in this pack. I did not add phrases I expected to find.

   ```python
   import re

   _LINES = frozenset(
       s.lower()
       for s in (
           "No comments:",
           "Leave a Reply",
           "Post a Comment",
           "Add a New Comment",
           "Comments are closed.",
           "Anonymous said...",
           "Popular Posts",
           "Recent Posts",
           "Blog Archive",
           "Follow by Email",
           "Related Links:",
           "Related Posts Plugin for WordPress, Blogger...",
           "No related post!",
           "Stumble it Reddit this share on Facebook",
           "Los Angeles Times Articles",
           "YOU ARE HERE: LAT HomeCollections",
           "The story is too old to be commented.",
           "Read the rest of this entry",
           "Creative Commons License",
           "Click to read more ...",
           "clipped from",
           "go to Top",
       )
   )

   # "1 comment:", "12 comments", "No comments" with or without the colon; "0 votes"
   _COUNTER = re.compile(r"^(?:(?:\d{1,4}|no)\s+comments?:?|\d{1,4}\s+votes?)$", re.I)
   _BLANKS = re.compile(r"\n{3,}")

   def _is_furniture(line):
       bare = line.strip()
       if not bare:
           return False
       return bare.lower() in _LINES or bool(_COUNTER.match(bare))

   def medicine_c1(text):
       lines = text.split("\n")
       kept = [ln for ln in lines if not _is_furniture(ln)]
       if len(kept) == len(lines):
           return text          # nothing removed, so do not touch the spacing either
       return _BLANKS.sub("\n\n", "\n".join(kept))
   ```

3. **Action:** fix. The article itself is good in nearly all of these documents; only the furniture goes.

4. **Harm test:** 0 of 62 gold documents changed, 0 dropped, 0.00%. PASS.

   Reach on my own slice: it acts on 1 of the 6 documents I labelled D4.

   Reach on my own slice: it acts on 5 of the 9 documents I labelled B4.

   Reach on my own slice: it acts on 11 of the 11 documents I labelled A1.

   Reach on my own slice: it acts on 4 of the 19 documents I labelled C5.

   Reach on my own slice: it acts on 0 of the 20 documents I labelled C4.

   Reach on my own slice: it acts on 2 of the 21 documents I labelled C3.

   Reach on my own slice: it acts on 98 of the 273 documents I labelled C1.

5. **Side effects:** the rule is deliberately literal, so it removes only the furniture I actually saw. A
   page whose menu reads `Latest Posts` instead of `Recent Posts` keeps its menu. It also cannot help where
   the extractor glued the furniture onto the end of a real sentence with no line break, which happened in
   `cb2bdc3224b4c92f`. A document that is nothing but furniture is left as an empty document rather than
   dropped; C5 and C3 catch most of those separately.

---

## Medicine 2

1. **Disease:** C3

   Truncated document. The text stops in the middle of a sentence, or the page is a list of excerpts that
   were each cut short. 21 documents.

   Three examples:

   - `cd0ef2540a4ee803` — excerpt cut at `and...` at offset 334
   - `52422fff81211f50` — excerpt cut with `[…]` at offset 395
   - `8b697f9f7d91de38` — news teasers cut mid-sentence, `Because` at offset 429

2. **Medicine:** drop the document when it ends in an excerpt marker, or when the last word is a function
   word that cannot end an English sentence. Truncation cannot be repaired, and the tail is the only place
   it can be detected without guessing.

   ```python
   import re

   # Only the bracketed excerpt marker. A bare "..." is ordinary English punctuation.
   _MARKER = re.compile(r"\[\s*(?:…|\.\.\.)\s*\]$")
   _DANGLING = frozenset(
       "a an the and or but of to in on at for with from by as is are was were "
       "that this these those which who because however".split()
   )
   _LAST_TOKEN = re.compile(r"([A-Za-z0-9']+)[^A-Za-z0-9']*$")

   def medicine_c3(text):
       tail = text.rstrip()
       if not tail:
           return text
       if _MARKER.search(tail):
           return ("drop", "")
       if tail.endswith((".", "!", "?", '"', "'", ")", ":", "…")):
           return text
       token = _LAST_TOKEN.search(tail)
       if token and token.group(1).lower() in _DANGLING:
           return ("drop", "")
       return text
   ```

3. **Action:** drop. A document that stops mid-sentence teaches the model to stop mid-sentence.

4. **Harm test:** 0 of 62 gold documents changed, 0 dropped, 0.00%. PASS.

5. **Side effects:** it reads only the end of the document, so it misses truncation in the middle, which is
   where I found it in `a1b97fd910707a8d` and `5a6856a5e9397412` — there the extractor dropped link and
   image text and left the sentence around it standing. Those need a different medicine, and I have not
   written one. A document that genuinely ends on an ellipsis for effect would be dropped wrongly; I saw
   none in this pack, but it is the obvious failure.

---

## Medicine 3

1. **Disease:** C4

   Two documents joined. Two unrelated texts with no boundary, usually a tag or archive page glued to an
   article, or scraped sentences concatenated. 20 documents.

   Three examples:

   - `d5d5ef995a71816e` — unrelated sentences joined from offset 0
   - `2cc8913710272e6b` — scrambled forum text joined at offset 32
   - `d7d9f2c89773b700` — Korean casino tag page, then `Actor Joel Brooks` at offset 36

2. **Medicine:** drop the document when an archive or tag header — the kind of line that can only begin a
   page — appears somewhere other than the start. A second page header inside the body means a second page
   was appended.

   ```python
   import re

   _HEADER = re.compile(
       r"^\s*(?:archivo de la etiqueta|archive for|archives for|tag archives?|"
       r"category archives?|posts tagged|browsing category|browsing tag)\b[:\s]",
       re.I,
   )

   def medicine_c4(text):
       lines = text.split("\n")
       for i, line in enumerate(lines):
           if i and _HEADER.match(line) and "".join(lines[:i]).strip():
               return ("drop", "")
       return text
   ```

3. **Action:** drop. The boundary is not marked, so the two halves cannot be separated reliably.

4. **Harm test:** 0 of 62 gold documents changed, 0 dropped, 0.00%. PASS.

5. **Side effects:** this is the weakest medicine of the seven and I want to say so plainly. **Its reach on
   my own slice is zero**: none of the 20 C4 documents kept a page header, so the rule fires on nothing. It
   passes the harm test only because it does nothing, and on the evidence here it should be marked DROP in
   the rule report rather than kept.

   I tried to replace it with a measurable signal before settling for this. Sentence-salad documents look
   as though they should have a high share of sentences beginning with a lower-case word or a digit, from
   fragments spliced together. They do not: across the 18 C4 documents long enough to measure, the median
   is 0.03 and the maximum 0.22, while the gold set reaches 0.12 and my own clean rows reach 0.80. There is
   no threshold that separates them, so I did not ship a rule based on it.

   The honest conclusion is that C4 in this pack is not reachable by a pattern. Telling two unrelated topics
   apart needs a model that scores coherence, and that belongs in the pipeline, not in a medicine sheet.
   `e6bdda6c700ff3ba` and `db1c016b4526af57` are the clearest examples of what a regular expression cannot
   see. In practice C5 and D4 drop several of these documents for other reasons, which is luck, not cover.

---

## Medicine 4

1. **Disease:** C5

   Lists of keywords and links. SEO spam, injected product keywords and tag clouds. 19 documents.

   Three examples:

   - `1ec7fa64b9476242` — `Cheap NFL Jerseys` injected at offset 532
   - `a381d9217f39570e` — `cheap michael kors` keywords from offset 93
   - `0b139d9931d96986` — keyword link list, `Free AUTO INSURANCE Quotes` at offset 0

2. **Medicine:** drop the document when at least two different injected-keyword markers appear, or when a
   single line is a run of five or more short pipe-separated phrases. Two markers rather than one, because
   a page may mention a brand once for an honest reason.

   ```python
   import re

   _SPAM = tuple(
       re.compile(p, re.I)
       for p in (
           r"\bcheap\s+(?:nfl|nba|mlb|nhl)\b",
           r"\bcheap\s+(?:michael\s+kors|oakley|ray\s*bans?|jerseys)\b",
           r"\bray\s*bans?\s+(?:sunglasses|outlet)\b",
           r"\b(?:auto|car)\s+insur\w*\s+(?:quotes?|qiotes?|rates?)\b",
           r"\bfree\s+auto\s+insurance\s+quotes\b",
           r"\bsex\s+dating\s+in\b",
           r"\bwrite\s+my\s+essay\b",
           r"\b(?:카지노|바카라|룰렛)\b",
           r"\bpigmentación\s+capilar\b",
       )
   )
   # Seven or more pipe-separated fragments, and not a bulleted list: a tag cloud, not prose.
   _KEYWORD_LINE = re.compile(r"^(?![ \t]*[•·*\-])(?:[^|\n]{2,40}\|){6,}[^|\n]{2,40}[ \t]*$", re.M)

   def medicine_c5(text):
       hits = sum(1 for p in _SPAM if p.search(text))
       if hits >= 2 or _KEYWORD_LINE.search(text):
           return ("drop", "")
       return text
   ```

3. **Action:** drop. In every one of these documents the spam is the reason the page exists; there is no
   good article underneath to save.

4. **Harm test:** 0 of 62 gold documents changed, 0 dropped, 0.00%. PASS.

5. **Side effects:** the marker list is drawn from one pack of 500 English documents, so it will age badly —
   next year's spam sells something else. A genuine article about car insurance that quotes a spam phrase
   twice would be dropped. The pipe-separated test would also catch an honest table that survived
   extraction as a single line, though I saw none in this pack.

---

## Medicine 5

1. **Disease:** A1

   Invisible junk characters. Byte order marks, zero-width spaces, soft hyphens and bidi controls left in
   the text. 11 documents.

   Three examples:

   - `4a22b0cbca7869fc` — BOM at offset 0
   - `11c3cd0e50856c3e` — zero width space at offset 0, second at offset 318
   - `10355b4f94c87a2c` — soft hyphen inside `never­ending` at offset 40

2. **Medicine:** delete the invisible characters named in the disease list. ZWJ (U+200D) and ZWNJ (U+200C)
   are **not** removed: they are part of Indic script and are not a disease. This pack is English, but the
   rule is written so it stays correct if it is ever reused on an Indic pack.

   ```python
   import re

   # U+FEFF BOM, U+200B ZWSP, U+00AD soft hyphen, U+200E/200F LRM/RLM,
   # U+202A-U+202E and U+2066-U+2069 bidi controls. U+200C and U+200D are left alone.
   _INVISIBLE = re.compile("[﻿​­‎‏‪-‮⁦-⁩]")

   def medicine_a1(text):
       return _INVISIBLE.sub("", text)
   ```

3. **Action:** fix. The text around these characters is fine; only the characters go.

4. **Harm test:** 0 of 62 gold documents changed, 0 dropped, 0.00%. PASS.

5. **Side effects:** removing a soft hyphen joins the two halves of a word, which is right for
   `never­ending` but wrong if a document ever used it as a real hyphen. Stripping bidi controls from a
   document that genuinely mixes right-to-left and left-to-right text would change how that text renders;
   there is no such document in this pack, but there would be in an Arabic or Hebrew one, and this medicine
   should not be reused there without a second look.

---

## Medicine 6

1. **Disease:** B4

   Template and code junk in prose. Tracking scripts, server-side include errors, ad placeholders and
   paragraph markers from the extractor. 9 documents.

   Three examples:

   - `e3fba14beec00b2b` — `fbq('track', 'ViewContent');` at offset 0
   - `90c2a9476f8445ad` — `{/PARAGRAPH}` at offset 10736
   - `b612431bc1ffadd2` — `[an error occurred while processing this directive]` at offset 0

2. **Medicine:** remove the junk tokens where they stand, and delete the line when the whole line is a
   tracking call or an ad placeholder. Each pattern is a literal artefact, not a guess.

   ```python
   import re

   _TOKENS = tuple(
       re.compile(p, re.I)
       for p in (
           r"\{/?PARAGRAPH\}",
           r"\[an error occurred while processing this directive\]",
           r"\{\{\s*[A-Za-z_][\w.]*\s*\}\}",
       )
   )
   _JUNK_LINE = re.compile(
       r"^[ \t]*(?:fbq\(.*?\);?|ga\(.*?\);?|_gaq\.push\(.*?\);?|"
       r"google adsense here|advertisement)[ \t]*$",
       re.I | re.M,
   )
   _BLANKS = re.compile(r"\n{3,}")

   def medicine_b4(text):
       out = _JUNK_LINE.sub("", text)
       for pattern in _TOKENS:
           out = pattern.sub("", out)
       if out == text:
           return text          # nothing removed, so do not touch the spacing either
       return _BLANKS.sub("\n\n", out)
   ```

3. **Action:** fix. In seven of the nine documents the prose around the junk is worth keeping.

4. **Harm test:** 0 of 62 gold documents changed, 0 dropped, 0.00%. PASS.

5. **Side effects:** a page that is *about* web analytics and quotes `fbq('track', ...)` on a line of its
   own would lose the line it is discussing. Removing `{/PARAGRAPH}` in place can leave two words joined
   with no space where the extractor used the marker as the only separator, which is what happened in
   `f819811b670939d0`; the text is still readable but one word boundary is lost.

---

## Medicine 7

1. **Disease:** D4

   Bad machine translation and synonym-spun text. Grammatical shape with the words swapped for thesaurus
   entries, so the meaning is gone. 6 documents.

   Three examples:

   - `cf633c0a1623318a` — `demigod askew cheese bisected cloister` at offset 377
   - `3dce67ac37d56429` — spun text from offset 31
   - `0a28e7f42a4bba02` — `Write My Essay!` at offset 0, spun text from offset 72

2. **Medicine:** drop the document when the mechanical residue of a spinner is still in the text: unused
   spintax alternatives in braces, or an essay-mill banner. I am not trying to detect spun prose itself.

   ```python
   import re

   _SPINTAX = re.compile(r"\{[^{}\n]{2,60}\|[^{}\n]{2,60}\}")
   _MILL = re.compile(r"\b(?:write my essay|essay writing service|buy essays? online)\b", re.I)

   def medicine_d4(text):
       if _SPINTAX.search(text) or _MILL.search(text):
           return ("drop", "")
       return text
   ```

3. **Action:** drop. Spun text has no recoverable meaning, so there is nothing to fix.

4. **Harm test:** 0 of 62 gold documents changed, 0 dropped, 0.00%. PASS.

5. **Side effects:** this reaches only the documents where the spinner left its syntax behind. Finished spun
   text, which is most of what I labelled D4, reads as ordinary English to a regular expression and passes
   straight through — `3dce67ac37d56429` and `a55992c7a90ce4f4` are both missed. Detecting it properly needs
   a language model scoring word collocations, which is beyond a medicine of this kind. The spintax pattern
   would also fire on a document that legitimately shows spintax syntax, such as a page explaining how
   article spinners work.

---

## What I did not write a medicine for

F1 (5), C2 (5) and A3 (5) are below the threshold of more than five, so they have no section here. A3
(mojibake) is the one I would write next if the bar moved, because it is mechanical and a fix exists.

For F1 I followed the rule in `DISEASES.md`: the evidence column in `labels.csv` gives only the type and the
offset, never the value, and the `hex` column is empty for those rows.

## Three things worth raising with the team

**The gold set is too small for the 1% rule to mean anything.** `en-dclm` gold holds 62 documents, so the
budget is 0.62 of a document: one changed document is 1.61% and fails, and there is no difference between a
rule that touches one document and a rule that touches six. The coverage table puts the pack at 62 against a
target of 200, with 108 disputed candidates — that dispute count, not the reading, is what keeps the set
small. Until it grows, every annotator on this pack is really being tested against zero tolerance, which
pushes all of us towards rules so narrow that they barely act. My C1 rule reaches 98 of 273 documents for
exactly that reason; I could reach far more and still do no real harm, but not and stay under 0.62.

**Two of my rules passed for the wrong reason at first.** Before I fixed them, C1 and B4 each changed 16 of
the 62 gold documents without removing a single line. Both ended by collapsing runs of blank lines, so any
document that happened to contain three consecutive newlines came back different and counted as harmed. The
fix was to return the text untouched when nothing was removed. It is worth other people checking their own
sheets for this: a tidy-up step at the end of a medicine is invisible in the rule but shows up as harm, and
the harm test cannot tell the two apart.

**Nine documents I marked `clean` contain a C1 furniture line.** `77b614ea3de96a3c`, `6aa2b1b15014b8c1`,
`0b6d3f138a3faac0`, `d9f493749079bf86`, `5d51c4fa93622d1b`, `4d2bbc4507af6cbe`, `2f4e718a130571c8`,
`8a7b6e90a1b41eb8` and `325f79f5f47bfaa0`. None is in the gold set, so no harm number moves, but my label and
my own rule disagree on them and one of the two is wrong. I would re-read these nine before they are
considered for gold.

## Harm test command

```
python -I teams/01-data-a/tools/harm_test.py \
  --pack en-dclm.parquet \
  --gold teams/01-data-a/gold/en-dclm_gold.csv \
  --rules diagnosis/submissions/en-dclm/mittalutkarsh/medicine.md \
  --rule all
```

The numbers in this sheet were produced by applying each section's function to the 62 gold documents of
`en-dclm` and counting the documents that came back changed or dropped, which is what the command above
measures. Rerun it after the gold set grows: every number here is tied to a 62-document set.
