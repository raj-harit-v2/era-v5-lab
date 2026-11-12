# Medicine sheet: en-nemotroncc-synth (maheshsv)

## Pack and method

- Pack: `en-nemotroncc-synth`, 500 English documents from nvidia/Nemotron-CC v1, synthetic split (an LLM rewrote
  Common Crawl pages). Five rewrite kinds, 100 documents each: `distill`, `diverse_qa_pairs`, `extract_knowledge`,
  `knowledge_list`, `wrap_medium`. Columns: `doc_id, pack_id, source, lang_label, url, text, meta`.
- Every document was read in full against a written reading rubric (`read=full` on all 500 rows). A script then
  verified that each quoted evidence string exists verbatim in its document and computed the character offsets, and
  it scanned all 500 documents for the mechanical diseases (A1 to A5, B1 to B3, C2, E3, emails) and for the two
  pack-wide generation artefacts of medicines 3 and 4, so that those are labelled the same way in every row. Two
  checks followed: an independent review re-read 48 documents and the code, and a **blind second reading of all 500
  documents** by a second reader who had not seen these labels. The agreement figures are in the next section; every
  disagreement was adjudicated one by one, and 47 rows changed as a result of the two checks.
- Verdicts: **339 clean, 145 fix, 16 drop.**
- Disease counts (documents): B4 36, B5 12, C1 76, C2 1, C3 47, C4 9, C5 7, D3 1, D4 2, F1 2, F2 1, F3 1.
- Character diseases (A group), HTML entities (B1), ghost chat markers (B3) and exact or near duplicates (H1, H2)
  were all **absent**: zero hits in 500 documents (maximum word 5-gram Jaccard between any two documents
  0.035, two SEO lists from the same page). Non-ASCII characters are typographic (em dash, degree sign,
  accented letters) plus a few Greek and Arabic letters quoted as glosses.
- **Gold set caveat.** The English gold set of Team 1 (Data A) is not published yet. Every harm test below runs on
  a proxy: the 339 documents of this pack marked `clean`. Three limits of this proxy: it is single-reader
  (the lab's gold set needs two readers who agree); the constants and regular expressions below were tuned on these
  same 500 documents, so the 0% figures are optimistic; and for medicines 3 and 4 the test is **circular**, see
  there. I will re-run the rules on the official gold set as soon as Team 1 publishes it; the code is below.

## Second-reader agreement

The lab measures agreement between two readers on 10% of the rows. I measured it on all 500 before submitting:

| Measure | Before adjudication | After adjudication |
|---|---|---|
| Verdict agreement (clean / fix / drop) | 89.6% | 92.2% |
| Cohen's kappa, three verdicts | 0.74 | 0.82 |
| Clean versus not-clean agreement | 90.2% | 92.6% |
| Rows with any difference in codes | 70 | 52 |

28 of the 52 remaining differences are one convention: the second reader noted the
generation artefacts of medicines 3 and 4 (missing spaces, rewriter meta-comments) but, like the disease list, gave
them no code; this sheet codes them B4. Without those rows the verdict agreement is 96.4%. The other
conventions a second reader may apply differently, all stated where they are used: a chunk that ends on a bare
heading whose body is in the next chunk is C3 here; an advertising or contact sentence woven into prose is C1 here;
a one-word foreign gloss is not D3 here.

## Medicine 1: C3 truncated document (47 documents)

1. **Disease:** C3, 47 documents. 61 documents of this pack are consecutive chunks of one OCR'd book
   (Upton's *Nibelungs*, one URL); the chunking cut the passage mid-sentence and the rewriter then appended
   `Question: … Answer: …` pairs after the cut, so the fragment sits at the end of the passage, not at the end of the
   document. Where the cut sits in the 47 documents: 18 start mid-sentence, 24 end
   the passage with a fragment (several of them a short line: an orphan heading such as `The Festival`, a line of
   verse), 5 are cut inside the passage (page turns, a dropped line of speech). Examples (exact trailing
   characters of the passage):
   - `d896f8ca6a2beae1`: `…company. Leading e-commerce platforms in 2020`
   - `fdd2b470571c5e4d`: `…ly with all leading business systems such as:`
   - `593cf027a182e228`: `…ed. Other useful information about this game:`
2. **Medicine:** take the passage before the first `Question:` line. (a) If its last line is a prose line (20
   characters or more, not a bullet, not a `Key: value` line, not an `Answer:` line) and does not end with sentence
   punctuation or a closing bracket, cut that line back to its last sentence end, or remove the line if it has
   none. (b) If its first line starts with a lower-case letter and is 40 characters or more, cut it up to its first
   sentence end. Keep the QA block.
```python
def _split_qa(text: str) -> tuple[str, str]:
    m = QA_START.search(text)
    return (text[: m.start()], text[m.start():]) if m else (text, "")

def _finish(lines: list[str], tail: str) -> tuple[str | None, bool]:
    new_body = "\n".join(lines).rstrip()
    if len(new_body) < MIN_KEEP_CHARS:
        return None, True
    return (new_body + ("\n\n" + tail.strip() if tail.strip() else "")), True

def trim_truncation(text: str) -> tuple[str | None, bool]:
    """Cut a sentence fragment at the end of the passage (before any Question/Answer block). Drop if little is left.
    A trailing line that ends in sentence punctuation, a closing bracket or quote, a bullet, a `Key: value` line or an
    Answer line is left alone."""
    body, tail = _split_qa(text)
    lines = body.rstrip().split("\n")
    last = lines[-1].strip()
    if not (len(last) >= MIN_PROSE_LINE and not LIST_MARK.match(last) and not KEY_VALUE_LINE.match(last)
            and not ANSWER_LINE.search(last) and not TERMINAL.search(last)):
        return text, False
    ends = list(SENTENCE_END.finditer(last + " "))
    lines[-1] = last[: ends[-1].end()].rstrip() if ends else ""
    return _finish(lines, tail)

def trim_leading_fragment(text: str) -> tuple[str | None, bool]:
    """Cut a leading fragment: a long first prose line that starts with a lower-case letter and does not look like code."""
    body, tail = _split_qa(text)
    lines = body.lstrip().split("\n")
    first = lines[0].strip()
    if not (first and first[0].islower() and len(first) >= MIN_LEAD_LINE and not CODE_LIKE.search(first)):
        return text, False
    e = SENTENCE_END.search(first + " ")
    lines[0] = first[e.end():].lstrip() if e else ""
    return _finish(lines, tail)

def trim_truncation_both_ends(text: str) -> tuple[str | None, bool]:
    new, ch1 = trim_truncation(text)
    if new is None:
        return None, True
    new2, ch2 = trim_leading_fragment(new)
    return new2, ch1 or ch2
```
   with `MIN_PROSE_LINE = 20`, `MIN_LEAD_LINE = 40`, `MIN_KEEP_CHARS = 200` and the patterns
   `QA_START = '^\\s*Question:'` (multiline), `TERMINAL = '[.!?…]+[\\"\'”’)\\]]*$|[)\\]]$|[\\"”’]$'`,
   `LIST_MARK = '^(?:[-*•–—]|\\d+[.)]|[a-z][.)])\\s'`, `KEY_VALUE_LINE = '^[^:\\n]{1,60}:\\s'`,
   `ANSWER_LINE = '^(?:Answer|A)\\s*[:.]|\\bAnswer:\\s'`, `SENTENCE_END = '[.!?…][\\"\'”’)\\]]*\\s'`,
   `CODE_LIKE = '[$/\\\\=(){}<>|]|--|\\bnpm\\b|\\bpip\\b|\\bgit\\b'`.
3. **Action:** fix (trim the fragment). Drop the document if fewer than 200 characters remain.
4. **Harm test:** Run on the proxy gold set (339 documents of this pack marked `clean`): **0 changed, 0 dropped (0.0%)**. Passes the 1% rule. On the whole pack the rule touches 26 of 500 documents, 24 of the 47 documents labelled C3. This test is not circular: the C3 labels come from reading, not from this rule.
5. **Side effects:** 23 of the 47 labelled documents are out
   of reach: cuts inside the passage and the shortest orphan lines (`The Festival`, 12 characters) need a
   rejoin of consecutive chunks from the same URL, not a trim. Convention: a chunk that ends on a bare heading whose
   body sits in the next chunk is labelled C3 (orphan heading); the blind second reader called those complete, so
   expect disagreement on exactly those rows. False positives, constructed and confirmed: a first line that starts
   with a lower-case brand name (`iPhone …`, `eBay …`) and runs 40 characters or more loses its first sentence; a
   complete last line of 20 characters or more without a full stop (a line of verse, a slogan, a heading such as
   `Frequently Asked Questions About Taxes`, a line ending in an emoji) is removed, which for a heading is the intended
   orphan-heading behaviour; a roman-numeral or abbreviated item (`ii. Keep the soil moist`, `Dr.`, `e.g.`) can be cut
   back to the abbreviation because `SENTENCE_END` treats it as a sentence end. False negatives: a fragment on a
   `Key: value` line (`Note: the company said that it would`), a capitalised start fragment, a fragment that happens
   to end with a full stop. Lines ending in a closing quote or bracket and en-dash bullets are now accepted as
   complete, and a code-like first line (`npm install …`) is never trimmed; an earlier version trimmed a complete
   parenthetical (`35ebd1eaea214130`). None of the false positives occurred in the proxy gold set.

## Medicine 2: C1 boilerplate (76 documents)

1. **Disease:** C1, 76 documents. Two shapes. (a) Whole boilerplate lines left by the scraper:
   - `d7ece2193f620b9b`: `[Share on other sites]` (three times)
   - `7e33ae5e96e36516`: `Word Count: 2498`
   - `b61d4ab44f34bce1`: `RELATED STORIES` followed by `6 mins read`
   (b) Advertising or call-to-action sentences that the rewriter wove into the prose, for example a closing
   "consider contacting <vendor> on <number> for further information" (`922e32f45f63d013`), a law firm's "How We
   Can Help" section (`fa6afecb771ef379`), a download-button instruction (`d4700fb9b804516b`), a treatment centre's
   closing paragraph (`2819f558ee6c1e7e`). Contact lines are labelled C1 whether or not a person is named; business
   and institution phone numbers are not F1.
2. **Medicine (shape a only):** delete a line when the whole line, trimmed, matches a navigation, sharing, metadata
   or footer pattern.
```python
def strip_boilerplate_lines(text: str) -> tuple[str | None, bool]:
    kept = [ln for ln in text.split("\n") if not BOILERPLATE_LINE.match(ln.strip())]
    changed = len(kept) != text.count("\n") + 1
    new = "\n".join(kept).strip()
    if changed and len(new) < MIN_KEEP_CHARS:
        return None, True
    return (new if changed else text), changed
```
   `BOILERPLATE_LINE` (case-insensitive, applied to the trimmed line) matches whole lines such as `Share …`,
   `Read more …`, `Related posts …`, `Posted by …`, `Word Count: 2498`, `Tags: …`, `3 Comments`, `Subscribe …`,
   `© …`, `Previous`, `Next`, `Home`, `Menu`, `Search`:
```
^(?![^\n]*[^\s.][.!?]$)(?:\[?(?:share (?:on|this|via)\b|share:|tweet(?: this)?\b|pin it\b|email this\b|print this\b)[^\n]{0,40}\]?|(?:read|learn|see|view) more\b[^\n]{0,30}|related (?:posts?|stories|articles|questions|links|content)\b[^\n]{0,40}|(?:posted|published|updated|last updated|written) (?:by|on)\b[^\n]{0,50}|(?:posted|published|updated|last updated):[^\n]{0,40}|word count:?\s*\d+\s*|tags?:[^\n]{0,200}|(?:\d+ )?comments?(?: \(\d+\))?:?|leave a (?:comment|reply)\b[^\n]{0,30}|(?:subscribe|sign up|log ?in|register)(?: now| here| today| to our newsletter| for (?:free|updates))?\s*[»›>]?|click here\b[^\n]{0,40}|(?:©|copyright ©?\s*(?:19|20)\d\d|all rights reserved\b)[^\n]{0,80}|(?:previous|next)(?: (?:post|article|page))?\s*[»›>]?|[«‹<]?\s*(?:previous|next)(?: (?:post|article|page))?|home|menu|search|skip to (?:main )?content)$
```
3. **Action:** fix (delete the line). Drop if fewer than 200 characters remain.
4. **Harm test:** Run on the proxy gold set (339 documents of this pack marked `clean`): **0 changed, 0 dropped (0.0%)**. Passes the 1% rule. On the whole pack the rule touches 5 of 500 documents, 4 of the 76 documents labelled C1. Not circular: the regular expression was not used in labelling.
5. **Side effects:** the line rule is safe but weak: 72 of the
   76 C1 documents are shape (b), in-prose advertising, which no regular expression can remove without
   damaging real sentences. For spec v1 I propose: treat shape (b) by document-level verdict (the labelled
   `doc_id`s are the fix/drop list for this pack) and ask for a classifier rule trained on these labels.
   Constructed ordinary sentences that an earlier version deleted and this version keeps (the rule now refuses any
   line that ends like a sentence, and the `share`, `login`, `register`, `published` and `copyright` branches are
   anchored to their boilerplate forms): `Share prices fell 5% today after the earnings report.`; `Login to the server using SSH with the command below:`; `Register your vehicle within 30 days of moving.`; `Published by Penguin in 1999, it became a bestseller.`; `Written by Shakespeare around 1600.`; `See more examples in the next section.`; `Copyright infringement occurs when a work is used without th`
   (0 of 7 still deleted). What still goes: any line that starts
   with `Tags:` and has no sentence punctuation, a bare `Search` or `Home` line, a `Register` line of up to a few
   words. The proxy gold set contains almost no legal, finance or tutorial prose of the kind at risk, and every
   whole-line boilerplate the reader saw is already outside it, so the 0% says little about those genres.

## Medicine 3: B4 rewriter meta-comments (8 documents)

1. **Disease:** B4 (closest code: junk from the generation pipeline in prose; the list has no code for rewriter
   artefacts). The rewriting model leaked its instruction context into the output: it tells the reader what the
   source page did *not* say.
   - `47f4f5107ac9aece`: `The provided text also discusses` ("The provided text also discusses …")
   - `6a2017ab99292d5b`: `Not specified in the given text` as a whole bullet
   - `d896f8ca6a2beae1`: `The text does not provide` as a QA answer
   8 documents, 5 of them `knowledge_list`. Plain "The text discusses …" openers of
   `distill` summaries are not counted: they are the summary frame, not a failed extraction.
2. **Medicine:** match the negated phrase (`not … in the (given|provided) text/passage/document`, `the text does
   not provide/mention/…`) or `the given/provided text`. Delete the bullet, `Key: value` line or QA pair that
   carries it; in running prose delete only the sentence.
```python
def remove_meta_comments(text: str) -> tuple[str | None, bool]:
    """Delete the bullet, `Key: value` line or Question/Answer pair that carries a rewriter meta-comment; in running
    prose delete only the sentence."""
    if not META.search(text):
        return text, False
    lines = text.split("\n")
    drop = set()
    for i, ln in enumerate(lines):
        if not META.search(ln):
            continue
        s = ln.strip()
        if s.startswith("Question:") or ANSWER_LINE.match(s):
            drop.add(i)                                   # drop the whole QA pair, whichever line carries it
            if s.startswith("Question:") and i + 1 < len(lines) and ANSWER_LINE.match(lines[i + 1].strip()):
                drop.add(i + 1)
            if ANSWER_LINE.match(s) and not s.startswith("Question:") and i > 0 and lines[i - 1].strip().startswith("Question:"):
                drop.add(i - 1)
        elif LIST_MARK.match(s) or KEY_VALUE_LINE.match(s):
            drop.add(i)
        else:
            sentences = re.split(r"(?<=[.!?])\s+", ln)
            lines[i] = " ".join(x for x in sentences if not META.search(x))
    new = "\n".join(ln for i, ln in enumerate(lines) if i not in drop)
    new = re.sub(r"\n{3,}", "\n\n", new).strip()
    if len(new) < MIN_KEEP_CHARS:
        return None, True
    return new, True
```
   `META` (case-insensitive):
```
(?i)\bnot (?:explicitly |specifically |directly )?(?:provided|stated|mentioned|specified|given|available|included|present|disclosed|named) in the (?:given |provided |original |above |source )?(?:text|passage|article|document|excerpt|content|context)|\bthe (?:text|passage|article|document) does not (?:explicitly |specifically )?(?:provide|mention|specify|state|say|give|include|indicate|name)\b|\bthe (?:given|provided) (?:text|passage) (?:also )?(?:discusses|mentions|describes|states|says|provides|refers|covers|explains|includes|lists|notes)\b
```
3. **Action:** fix. Drop if fewer than 200 characters remain (`4fc487e14eab5961` is a 458-character list in which
   the country and the coup are never named; it drops).
4. **Harm test:** Run on the proxy gold set (339 documents of this pack marked `clean`): **0 changed, 0 dropped (0.0%)**. Passes the 1% rule. On the whole pack the rule touches 8 of 500 documents, 8 of the 36 documents labelled B4. **This test is circular:** the label sheet applied this same regular expression when
   labelling, so every matching document is already `fix`, never `clean`, and the 0 cannot fail. What the data does
   show: all 8 hits were inspected individually and every one is a genuine artefact
   (precision 8/8). The real harm test needs the independent gold set.
5. **Side effects:** the pattern deliberately does **not** match plain "in the text" (QA questions such as "Who is
   the main character in this text?" are the normal format of `diverse_qa_pairs`), nor "The text discusses …" and
   "The text mentions that …" (the summary frame of `distill` and `knowledge_list` rewrites, present in several
   clean rows), nor "the original text", which two `wrap_medium` documents use legitimately as product copy about
   paraphrasing tools. Constructed sentences such as `Read the given passage carefully and answer the questions that follow.`; `Applicants must sign the provided document before the deadline.` are
   no longer matched, because the `given/provided text`
   branch now requires a reporting verb. A Question line that carries the phrase takes its Answer line with it and
   vice versa, so no orphan line is left. A genuine essay that writes "the provided text also discusses" would lose
   that sentence.

## Medicine 4: B4 detokenisation glitch, missing space before an opening quote (18 documents)

1. **Disease:** B4 (closest code). A systematic generation artefact: the space before an opening single quote is
   missing, so the quote glues to the previous word.
   - `536547e07d7d65ca`: `n. The'resources(-Count)' re`
   - `c1a354c76d5c4586`: `ds for'remember' and 'forget` (five times in one document)
   - `7e2cbd39bf39635f`: `called'silth/seeth'. Upon re`
   18 documents, 23 occurrences, in all five rewrite kinds. A sibling variant, the
   missing space before a dot-extension (`e.g.,.tar`, `like.yaml or.txt` in `03ad0f392751ba37`), is labelled B4
   but not fixed by this rule.
2. **Medicine:** when a letter is directly followed by `'`, the quote opens a word that starts with `s`, `r` or
   `m`, and the phrase is closed by another `'` on the same line, insert a space before the quote. The `s/r/m`
   restriction comes from the data: every one of the 23 glitches opens such a word, which fits a detokeniser that
   treated the quote as the start of a contraction (`'s`, `'re`, `'m`) and glued it to the previous word.
   Contractions, possessives and poetic elisions (`it's`, `don't`, `we're`, `o'clock`, `y'all`, `rock'n'roll`,
   `ne'er`) are excluded by the look-ahead; Python string prefixes (`f'…'`, `r'…'`, `b'…'`, `rb'…'`) by the
   look-behind.
```python
def fix_detok_quotes(text: str) -> tuple[str | None, bool]:
    new = DETOK.sub(" '", text)
    return new, new != text
```
   `DETOK` (compiled with `re.M`):
```
(?<=[A-Za-z])(?<![^A-Za-z][frbuFRBU])(?<![^A-Za-z][rR][bB])(?<![^A-Za-z][bB][rR])'(?!s\b|t\b|re\b|ll\b|ve\b|d\b|m\b|em\b|n'|er\b|clock\b|all\b|am\b)(?=[srmSRM][A-Za-z][^'\n]{0,40}'(?:[\s,.;:)!?]|$))
```
3. **Action:** fix (insert one space).
4. **Harm test:** Run on the proxy gold set (339 documents of this pack marked `clean`): **0 changed, 0 dropped (0.0%)**. Passes the 1% rule. On the whole pack the rule touches 18 of 500 documents, 17 of the 36 documents labelled B4. **This test is circular** in the same way as medicine 3: the labelling applied the
   same expression. All 18 hits were inspected individually and every one is a genuine glitch
   (precision 18/18); one of them carries the instance under B5 (`6c9e38f009ea3806`), hence
   17 of 18 are labelled B4.
5. **Side effects:** a possessive directly followed by a quoted phrase that closes on the same line (`the boys'bikes'`)
   would get a spurious space; not seen in 500 documents. Constructed code and verse inputs (`print(f'hello world')`; `pattern = re.compile(r'sample')`; `payload = b'raw'`; `I ne'er saw such a thing,' she said`; `the boys' bikes were new`)
   are left alone. False negatives: a
   quoted phrase longer than 40 characters, a glitch with no closing quote on the line, the sibling variant with a
   dot-extension (`e.g.,.tar`, `like.yaml`, `the.NET`: 2 documents, labelled B4, not fixed by this rule). Curly quotes (’) are
   not handled; none occur in this pack.

The B4 total (36 documents) is larger than the two rules together because B4 was also used, as the
closest code, for other pipeline junk in 11 documents: `d2fb665c40af5edb` (`-DATE-` placeholder left in a bill description); `ea0ecda1c2f25dd1` (OCR glyph junk `e~ \` inside prose); `6011e88c8cc9c77d` (missing space before dot-extensions (`in.jpg,.png`)); `12693fe362d15d0d` (Cloudflare `[email protected]` placeholder); `373e0f0dd5699ac0` (e-learning template demo content under a real course title, dropped); `57922931d471745c` (epoch-bug date `January 17, 1970` and midnight time copied from the CMS); `0c03a4c096276336` (forum thread recast as an AI/user exchange); `d4f559ee86104b5b` (missing space before `.NET`); `68924f97019edabb` (`https://www.example.com/…` placeholder link); `e472a2fcc0df3984` (SEO-writing prompt leaked into the prose, dropped); `03ad0f392751ba37` (missing space before dot-extensions (`e.g.,.tar`)).
The most training-relevant of these is the leaked SEO-writing prompt in `e472a2fcc0df3984` ("vary your verbs …"),
dropped, and the chat-role recasting in `0c03a4c096276336` ("The AI advises the user …"), which teaches the
assistant/user frame as plain text and sits next to B3 in danger.

## Medicine 5: C4 two documents joined (9 documents)

1. **Disease:** C4, 9 documents: SEO aggregator or "people also ask" pages whose unrelated snippets the
   rewriter stitched into one text. Examples: `7b8ffe6ce68a4411` (Chicago housing market interleaved with RESPA
   kickback law), `650be7c8d64f5efd` (five unrelated essay snippets plus a dangling graded outline),
   `a14eaa5e58baf3c3` (Q&A aggregator). Verdicts: 5 drop, 4 fix
   (fix where the joined part is a short tail that can be cut: a reader comment, appended related-post teasers, a
   second forum question).
2. **Medicine:** the obvious lexical rule, as code, so that its failure is on record:
```python
def flag_topic_shift(text: str) -> tuple[str, bool]:
    """Flag a document of four or more paragraphs in which two adjacent paragraphs share no content words."""
    paras = [p for p in re.split(r"\n\s*\n|\n", text) if len(p.split()) >= MIN_PARA_WORDS]
    if len(paras) < MIN_PARAS:
        return text, False
    words = [{w for w in WORD_RE.findall(p.lower()) if w not in STOP} for p in paras]
    return text, any(not (a & b) for a, b in zip(words, words[1:]))
```
   with `MIN_PARAS = 4`, `MIN_PARA_WORDS = 25`. The boundary is semantic; an
   embedding-based topic-shift score may work but needs the gold set to set its threshold. For this pack the
   medicine is the list of labelled `doc_id`s.
3. **Action:** drop; fix where the joined part is a short tail that can be cut.
4. **Harm test:** Run on the proxy gold set (339 documents of this pack marked `clean`): **57 changed, 0 dropped (16.81%)**. Fails the 1% rule. On the whole pack the rule touches 109 of 500 documents, 5 of the 9 documents labelled C4. **Fails**: forum threads, tag archives, course grids and knowledge lists are
   legitimately multi-topic. The drop list by construction touches 0 of 339 proxy gold documents. No
   automatic rule is proposed for spec v1.
5. **Side effects:** any automatic rule will also flag legitimate multi-topic pages that the label sheet
   deliberately kept as page structure; the threshold must be set on those.

## Medicine 6: B5 broken Markdown in code (12 documents)

1. **Disease:** B5, 12 documents. The rewriter emitted identifiers inside code as Markdown, and the
   underscores were eaten as italics markers (`add_filter` became `addfilter`, `load_word2vec_format` became
   `loadword2vecformat`); in other documents the announced code examples were dropped and only the prose around
   them survived, or a LaTeX formula lost its subscripts. Examples:
   - `42d8419d13115795`: `addfilter('intermediateimagesizesadvanced','myintermediateimage_sizes');`
   - `ac2d7bac43b4a937`: `setllCUSTNO ORDHDRL1;` (space eaten between RPG opcode and operand)
   - `b63a5e89acfb14e3`: `$\sigmax\sigmap \geq \frac{h}{4\pi}$`
2. **Medicine:** no safe automatic fix: restoring an eaten underscore needs knowledge of the API (`add_filter`
   versus `addfilter`), and a dropped code example cannot be recovered. A detector is possible and is tested here:
```python
def flag_eaten_identifiers(text: str) -> tuple[str, bool]:
    """Flag code (fenced or backticked) that contains a lower-case identifier of 12+ letters, no underscore, that is
    not a dictionary word: the signature of `add_filter` -> `addfilter` damage."""
    words = _dictionary()
    for span in CODE_SPAN.findall(text):
        for tok in LONG_LOWER.findall(span):
            if tok not in words:
                return text, True
    return text, False
```
   using the system word list (`/usr/share/dict/words`) to exclude real words.
3. **Action:** route flagged documents to a manual fix. Fix by hand where the identifier is known
   (`42d8419d13115795`, `f160996522775c21`, `ac2d7bac43b4a937`, `713e88c96cefef1a`, `6c9e38f009ea3806`,
   `6df80446baf7b672`); where an announced code example is simply gone (`03ad0f392751ba37`, `7ee6cdea68d597b0`,
   `52731a50fbea41cb`, `f5d81aaad46e50f8`) keep the prose; `wrap_medium` and `extract_knowledge` rewrites that
   contain code fences should not feed the code mix.
4. **Harm test (detector):** Run on the proxy gold set (339 documents of this pack marked `clean`): **0 changed, 0 dropped (0.0%)**. Passes the 1% rule. On the whole pack the rule touches 3 of 500 documents, 3 of the 12 documents labelled B5. The detector cannot see dropped examples, mangled spaces in RPG
   (`setllCUSTNO`) or a broken formula, hence the partial recall.
5. **Side effects:** a legitimate long lower-case identifier that is not an English word (`stringbuilder`,
   `getelementbyid` written in lower case) would be flagged for review; the action is a review, not a change.

## Medicine 7: C5 lists of titles or links (7 documents)

1. **Disease:** C5, 7 documents: pages that are mostly a list of teaser titles, related-story headlines
   or a series table of contents, with little or no prose. Examples: `affc40538cb81c3e` (a series table of contents
   of about 30 question titles), `beb73cd7cb9e50fd` (a list of related magazine stories), `f27860217811cf33` (an SEO
   aggregator's list of essay topics).
2. **Medicine:** none that passes a test yet. I tried "flag a document in which at least half of the non-QA lines are
   short title-case lines without sentence punctuation, with at least eight such lines": at thresholds that keep the
   harm under 1% it catches 0 of the 7 documents, because the rewriter turned most of these lists into
   run-on lines or glued titles together. For this pack the medicine is the list of labelled `doc_id`s.
3. **Action:** drop when the list is the whole document; fix (cut the list) when it is a tail after a real article
   (`b61d4ab44f34bce1`).
4. **Harm test:** the drop list by construction touches 0 of 339 proxy gold documents. No automatic rule is
   proposed.
5. **Side effects:** none for a manual list.

## Diseases below the five-document threshold (no medicine required)

| Code | Docs | Note |
|---|---|---|
| F1 | 2 | Two documents with email addresses, three addresses in all (one personal blog contact, one named employee's work address). Policy proposed for spec v1: mask every email with `[EMAIL]`, because an email is a directly harvestable identifier whatever its owner; business and institution phone numbers are public contact points and are not F1. Values never copied; offsets only. Named-person profiles without contact data (`aeec9af96e03401d`, a child record holder; `36109ec5880f6cf2`) are marked clean with a note and flagged for the second reader. |
| F2 | 1 | `701cacaccdb06931`: three USMLE-style multiple-choice stems with options stripped (MedQA-type items); drop, and check against fingerprints v1. |
| F3 | 1 | `06cfe5719541e863`: torture and sexual-violence "punishment" list; drop. |
| C2 | 1 | Repeated forum footer line. |
| B2 | 0 | No leftover markup. Two literal tag names (`<ul>` in `d096a0402bb49b08`, `<listbox>` in `a9c8f8d69278c340`) are deliberate mentions in UI bug reports and are marked clean with a note; a tag-stripping rule must exempt tag names quoted in prose. |
| D3, D4 | 1, 2 | A German SEO backlink inside English text (D3); mistranslations on a machine-translated Russian gardening site, two documents (D4). Greek and Arabic single words quoted as glosses are not D3. No D5: the only candidate was re-coded D4 after the second reading. |

## Observations without a disease code

- **Source concentration.** 61 documents (12% of the pack) are consecutive chunks of one book from one URL, and
  170 documents in total share their source page with at least one other document (44 pages). There are no exact or
  near duplicates (maximum word 5-gram Jaccard 0.035), so H codes do not apply, but a per-source cap in the data
  mix would stop one book from dominating a shard.
- **OCR noise** in the book chunks (`hound` for `bound`, `cloth` for `doth`, hard line wraps inside sentences,
  missing opening quotation marks) is noted in the `note` column of the affected rows, including rows marked
  `clean`; no code covers OCR noise, so `clean` there means "no listed disease".
- **Wrong generated answers.** Several `diverse_qa_pairs` answers contradict their own passage (noted per row). The
  evaluation team should treat synthetic QA as unverified.
- The flowery `wrap_medium` style was not labelled as a disease; it is the declared nature of the split.
