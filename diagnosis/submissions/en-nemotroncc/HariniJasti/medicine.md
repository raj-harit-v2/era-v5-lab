# Medicine sheet: en-nemotroncc (HariniJasti)

Counts come from my labels for all 500 documents of the pack. Eleven diseases appear more than five times. Each medicine is a short Python function `text -> (new_text, action)`; the key regex is shown in each section.

**Harm test status.** The real harm test needs the English gold set from the Data A / Data B teams:
Running the medicines on the gold set gives changed / dropped / % / PASS-FAIL per medicine.
Until the gold set is available I ran a **proxy harm test** on the 138 documents I labelled `clean` (1% of 138 ≈ 1.4 documents). I'll replace the proxy column with gold numbers when I have it.

| # | Disease | Count (of 500) | Action | Proxy: clean docs changed | Proxy: dropped | Proxy % | Catches (of my labelled cases) |
|---|---|---|---|---|---|---|---|
| M1 | C5 SEO / essay-mill snippet page | 102 | drop | 0 | 0 | 0.0% PASS | 19 / 102 |
| M2 | C4 teaser / archive page | 102 | drop | 0 | 0 | 0.0% PASS | 3 / 102 |
| M3 | C1 boilerplate lines | 176 | fix | 0 | 0 | 0.0% PASS | 20 / 176 |
| M4 | C2 repeated lines | 85 | fix | 0 | 0 | 0.0% PASS | 22 / 85 |
| M5 | C3 truncated text | 200 | fix / drop | 0 | 0 | 0.0% PASS | 18 / 200 |
| M6 | F1 personal email / phone | 12 | fix (mask) | 2 | 0 | 1.45% FAIL | 4 / 12 |
| M7 | A1 invisible characters | 14 | fix | 0 | 0 | 0.0% PASS | 14 / 14 |
| M8 | B4 template junk | 28 | fix | 0 | 0 | 0.0% PASS | 5 / 28 |
| M9 | D3 foreign-script lines | 15 | fix / drop | 0 | 0 | 0.0% PASS | 3 / 15 |
| M10 | D4 spun text | 28 | drop | 0 | 0 | 0.0% PASS | 1 / 28 |
| M11 | B5 sentences glued after a full stop | 56 | fix | 0 | 0 | 0.0% PASS | 16 / 56 |

The medicines are tuned for precision, not recall: a medicine that misses some sick docs is safe, while one that damages good docs fails.

---

## Medicine 1 — C5 SEO / essay-mill snippet pages

1. **Disease:** C5, 102 docs. Examples:
   - `45cc4aca83036255` — `An analysis of realism in both great expectations and frankenstein` (title repeated), `realism which is .`
   - `3e4ee522b5c267be` — `Essayzoo: cheap pre written essays for sale`, `a trip to the zoo is.`
   - `bf58bb70fdc4a7fe` — `students essays sample topics narrative persuasive`, `cover many.`
2. **Medicine:** these pages are search snippets stitched together; each snippet is cut off as `<function word> .`. Count those cuts (plus `Mon DD, YYYY .` dates); drop if ≥ 4, or ≥ 2 and the title repeats.
   ```python
   CUT_SNIPPET = re.compile(r"\b(the|and|of|in|a|to|for|as|by|with|an|that|from|on|or|is|be|was|which)\s?\.(\s|$)", re.I)
   ```
3. **Action:** drop.
4. **Harm test:** proxy 0 changed, 0 dropped of 138 (0%). Gold: ___ / ___.
5. **Side effects:** text quoting truncated lists or code like `a .` could be hit. Misses doorway pages without the ` .` cuts (keyword titles + shuffled sentences).

## Medicine 2 — C4 teaser / archive pages

1. **Disease:** C4, 102 docs. Examples:
   - `eb8eab5f88e01414` — `brings … More No Lesson Plan is the Best Lesson Plan`
   - `48541ab5ac386c19` — `mandated taking out […]`
   - `962bc6e4f3744dd1` — `has greatly expanded today.……`
2. **Medicine:** two or more post-teaser markers (`… More Title`, `[…]`) mean the doc is a list of cut-off posts glued together.
   ```python
   TEASER = re.compile(r"(…|\.\.\.)\s*More\s+[A-Z]|\[…\]|\[\.\.\.\]")   # drop if >= 2 hits
   ```
3. **Action:** drop.
4. **Harm test:** proxy 0 / 0 of 138 (0%). Gold: ___ / ___.
5. **Side effects:** an essay that quotes with `[…]` twice would be dropped. Misses joined docs with no marker (most C4 cases, e.g. `adbab34e5ae0df37` `promised to keep aThe play`).

## Medicine 3 — C1 boilerplate lines

1. **Disease:** C1, 176 docs. Examples:
   - `17f4af14c04c9fde` — `Primary tabs`
   - `b787548f4655559b` — `Search for:`
   - `ca32200e3729539d` — `Click to expand...`
2. **Medicine:** delete whole lines that are only a known UI string (Read More, Continue reading, Click to expand..., Primary tabs, Search for:, Share, Comments N, N thoughts on …, Related posts, Posted in …, Leave a reply, Skip to content, Home / …, RSS header - this is hidden, Quantity, Store Information, External links, Follow). The regex matches only a whole line (`^…$`), never inside a sentence.
3. **Action:** fix (remove the line).
4. **Harm test:** proxy 0 / 0 of 138 (0%). I removed `Contents` from the list because it hit a clean doc (`024cf48bc1be034f`). Gold: ___ / ___.
5. **Side effects:** a real one-word heading such as "Share" or "Follow" in an article would be removed. Misses site-specific footers (e.g. `Our Guide to Vaping` in `d09dc244c45fc2bf`).

## Medicine 4 — C2 repeated lines

1. **Disease:** C2, 85 docs. Examples:
   - `351055b1795d8f3b` — `This is Sonya54's TrustRating` / `This is Giavani123's TrustRating` (same widget repeated)
   - `45cc4aca83036255` — title line at offsets 0 and 3207
   - `b53192f0d3a3dbfc` — `A look at the moral development of filipino youth` at offsets 0 and 3208
2. **Medicine:** keep the first copy of any line of ≥ 40 characters, delete later exact copies.
   ```python
   if len(key) >= 40 and key in seen: continue   # drop the repeat
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 / 0 of 138 (0%). A 25-character minimum also hit repeated sub-headings and captions in clean pages, so the minimum is 40. Gold: ___ / ___.
5. **Side effects:** poems or song-like text with a real refrain, and legal text that repeats a clause on purpose. Misses near-duplicates (the TrustRating lines differ by username).

## Medicine 5 — C3 truncated text

1. **Disease:** C3, 200 docs (most common). Examples:
   - `0c69e2d3936a37a9` — ends `(e.g., lumpy snowflake`
   - `cf9ffce5fa114b16` — ends `interstitium. It`
   - `e18d8d5057e2aea8` — `so that the situation can be…`
2. **Medicine:** only fire when the last word cannot end an English sentence (the, a, of, and, It, …) or the doc ends in `…` / `[…]`. Then trim back to the last full sentence; if less than 200 characters remain, drop.
   ```python
   CUT_END = re.compile(r"(\b(the|a|an|of|and|or|to|in|on|for|with|by|from|that|which|is|are|was|were|be|It|its|their|his|her|as|at|but|so|such|than)|…|\[…\])\s*$", re.I)
   ```
3. **Action:** fix (trim), or drop if almost nothing is left.
4. **Harm test:** proxy 0 / 0 of 138 (0%). The first version also matched a plain `...` ending and hit a clean forum post (`d57d424ce49c5526`), so `...` was removed. Gold: ___ / ___.
5. **Side effects:** a doc that ends on a title like "The Lord of the" in a list would be trimmed. Misses truncations that end on a noun (`using the following link:`).

## Medicine 6 — F1 personal email / phone

1. **Disease:** F1, 12 docs. Examples (values not copied):
   - `17f4af14c04c9fde` — phone number at offset 824
   - `fab230d1a3b03a77` — phone number at offset 5203, email at offset 5221
   - `a3727c426e649c64` — phone number at offset 278 (repeated 9×)
2. **Medicine:** replace personal emails with `<EMAIL>` and phone numbers with `<PHONE>`. Role / placeholder addresses (info@, sales@, support@, you@, example.com …) are kept, and so are phone numbers that follow a business word in the same line (call, contact, office, agency, service, hall, department, company …), because they are not personal data.
   ```python
   EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")
   PHONE = re.compile(r"(?<!\d)(\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.‐-]\d{3}[\s.‐-]\d{4}(?!\d)")
   ```
3. **Action:** fix (mask).
4. **Harm test:** proxy 2 changed / 0 dropped of 138 (1.45%, FAIL). Both hits are organisation addresses that are not on the role list (`45b126bd3b538779`, `48cb07c100d0d901`). A longer role list, or masking only when a person's name is next to the address, would fix it. Gold: ___ / ___.
5. **Side effects:** business emails and office phones get masked unless their name is on the role list; numbers formatted like phones (product codes, IDs) can be masked. Names, home addresses and dates of birth are not caught (e.g. `48541ab5ac386c19` reader name and city).

## Medicine 7 — A1 invisible characters

1. **Disease:** A1, 14 docs. Examples:
   - `bbe410dfbf6e94fe` — U+200B at offset 111 (~40 in total)
   - `c9e6d6b160ed24cb` — U+00AD at offset 1012
   - `3d2f892c9543b193` — U+00AD at offset 365
2. **Medicine:** delete ZWSP, BOM, soft hyphen, LRM/RLM, bidi embeddings/isolates and word joiner. ZWJ (U+200D) and ZWNJ (U+200C) are kept because they are needed in emoji and Indic text.
   ```python
   INVISIBLE = re.compile("[​﻿­‎‏‪-‮⁠⁦-⁩]")
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 / 0 of 138 (0%). Gold: ___ / ___.
5. **Side effects:** a soft hyphen in a long German/Dutch word only marks a hyphenation point, so removing it changes no visible text. Right-to-left text that needs bidi marks (Arabic/Hebrew quotes) could display wrongly.

## Medicine 8 — B4 template junk

1. **Disease:** B4, 28 docs. Examples:
   - `ae8a5a4fdf8d3351` — `[email protected]` (Cloudflare email placeholder)
   - `96b00cc286431230` — `[[i]]`
   - `cf2892092e61e1aa` — `salty foods1`, `hyponatremic3What` (footnote numbers glued)
2. **Medicine:** delete fixed template tokens: Cloudflare `[email protected]`, `[[x]]` markers, `{{var}}`, `…show more content…`, whole `Loading...` lines and `Dive into the research topics of …` lines.
   ```python
   JUNK = re.compile(r"\[email\xa0protected\]|\[email protected\]|\[\[[a-z0-9]{1,3}\]\]|\{\{[^{}\n]{1,40}\}\}|…show more content…|^\s*Loading\.\.\.\s*$|^\s*Dive into the research topics of .*$", re.M)
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 / 0 of 138 (0%). Gold: ___ / ___.
5. **Side effects:** wiki or template documentation that explains `{{var}}` syntax would lose its examples. Glued footnote numbers (`foods1`) are not fixed, because a rule for them also breaks words like `MP3`.

## Medicine 9 — D3 foreign-script lines in English docs

1. **Disease:** D3, 15 docs. Examples:
   - `29160f1b6b0823cf` — `解说语言`
   - `4e3b0960daa6743d` — `как раз об том же самом вчера у Шмальгаузена`
   - `f6d54677432cce21` — `Контрольная работа 8 класс модуль 2 Spotlight`
2. **Medicine:** remove lines where more than half the letters are Cyrillic, Arabic, CJK, kana or Hangul. If more than 30% of the lines are like that, drop the doc.
3. **Action:** fix, or drop.
4. **Harm test:** proxy 0 / 0 of 138 (0%). Gold: ___ / ___.
5. **Side effects:** language-learning pages and articles that quote a line in Russian/Chinese lose the quote. Misses mixed Latin-script languages (Spanish/French in `3da0a9bbeeac1a6a`, `37a68ee0535aea68`).

## Medicine 10 — D4 spun / synonym-swapped text

1. **Disease:** D4, 28 docs. Examples:
   - `bd708a0acc1ee841` — `Research Old fashioned paper`, `PhD Amount Cases`
   - `3da0a9bbeeac1a6a` — `The solución has the problematic of the room`
   - `83fecaa73a44ab3b` — `mugshot incidents very eminently`
2. **Medicine:** article spinners replace fixed phrases with fixed "synonyms" (research paper → old fashioned paper, big data → huge information, parents → dad and mom). Drop the doc if two or more different spin phrases appear (a fixed list of known spin phrases).
3. **Action:** drop.
4. **Harm test:** proxy 0 / 0 of 138 (0%). Gold: ___ / ___.
5. **Side effects:** very low recall (1 of 28): each spinner uses different swaps, so a phrase list only catches the ones I have seen. A better medicine is a small language-model perplexity filter, which needs its own harm test.

## Medicine 11 — B5 sentences glued after a full stop

1. **Disease:** B5, 56 docs. Examples:
   - `008661b46ac2a3c5` — `children's books.Her love`, `and digitally.She also`
   - `212ba0fac2722e6c` — `purchasing their practice.Also keep in mind`
   - `425c5c97438f1383` — `on the matter.She said`
2. **Medicine:** B5 has several shapes; only one has a safe rule. When a lowercase word, a full stop and a capitalised word are glued (`books.Her`), insert a space. File extensions and domains (`Node.Js`, `ASP.Net`) are skipped.
   ```python
   GLUED_STOP = re.compile(r"\b([a-z]{3,})\.([A-Z][a-z]{2,})\b")
   ```
3. **Action:** fix.
4. **Harm test:** proxy 0 / 0 of 138 (0%). Gold: ___ / ___.
5. **Side effects:** identifiers like `object.Method` in code and some brand names would get a space. Other B5 shapes are not fixed: words glued without a full stop (`creamthe`, `MahSouth`), code with lost indentation, and flattened lists.

---

## Medicine I tried and rejected

**Split glued words** (`[a-z]{2,}[A-Z][a-z]{2,}` → insert a space, for `promised to keep aThe play`). On a proxy of 96 clean docs it changed 3 (3.1%, FAIL): `fd16036899796ca4`, `acfaa05dfcc54537`, `5224d2b4ead317b0`. CamelCase brand and product names that are not on a whitelist get split too. Not proposed.
