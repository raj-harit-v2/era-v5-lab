# Medicine sheet: en-dclm (shekar-maker)

Pack: `en-dclm`, 500 English documents from DCLM-baseline 1.0 (filtered). All 500 rows are labelled
(65 clean / 349 fix / 86 drop). Counts below are from `labels.csv`.

Diseases found more than five times: C1 (386), C3 (98), C5 (61), C2 (30), D3 (24), B4 (23), D4 (18), C4 (16),
A1 (12), F1 (8), H3 (7), A3 (7). Eight have a regex medicine below; D3, D4, C4 and H3 have none and are
explained in the last section. Found five times or fewer (no medicine required): F3 3, B5 3, A6 3, A2 3,
B2 2, F2 1, D5 1, A4 1, B1 1.

**Harm test status.** Every medicine was run on the real gold set of this pack,
`teams/01-data-a/gold/en-dclm_gold.csv` (62 documents that two readers marked `clean`), with the Data A tool:

```
python -I teams/01-data-a/tools/harm_test.py --pack en-dclm.parquet \
  --gold teams/01-data-a/gold/en-dclm_gold.csv \
  --rules diagnosis/submissions/en-dclm/shekar-maker/medicine.md --rule all
```

The limit is 1 document changed or dropped (`max(1, 1% of 62)`). All eight medicines pass with 0 changed and
0 dropped, alone and run together in file order. These numbers replace the earlier *proxy* numbers (the proxy
was the 65 documents of this pack that I marked `clean`). All 62 gold documents are among those 65, so the gold
run confirms the proxy result; it is not a new, independent sample. The gold set is below its target (62 of
200), so the test is weak evidence for rare side effects.

Medicines are given as Python. Each takes the document text and returns the new text, or `("drop", "")` to
drop the document. Each block runs on its own (`re` is imported by the tool). Medicine 2 needs `pip install ftfy`.

---

## Medicine 1: A1 invisible junk characters

1. **Disease:** A1, 12 documents. Examples: `4a22b0cbca7869fc` BOM `U+FEFF` at offset 0; `9f004914c20a592b` three
   BOMs `U+FEFF U+FEFF U+FEFF` at offset 0; `855032b92c2b8d25` soft hyphens `U+00AD` at offsets 161, 185, 527, 550
   (`ge­sprochen`); `f4e27249dc2787fc` LRE `U+202A` at offset 90; `11c3cd0e50856c3e` ZWSP `U+200B` at offset 0.
2. **Medicine:** delete ZWSP, BOM, soft hyphen and the bidi embedding/isolate marks. Keep ZWJ/ZWNJ.
   ```python
   A1_RE = re.compile("[​﻿­‪-‮⁦-⁩]")
   def medicine_a1(text): return A1_RE.sub("", text)
   ```
3. **Action:** fix.
4. **Harm test:** gold set 0/62 changed, 0 dropped: PASS. Whole pack: 10 changed, 0 dropped.
5. **Side effects:** a soft hyphen that a typesetter placed on purpose is deleted too, which joins the word
   correctly (`never­ending` → `neverending`), so no damage. Bidi marks in genuinely mixed-direction text (Arabic
   or Hebrew quotes inside English) would be lost; none in this pack. The medicine does not touch U+200C/U+200D.

## Medicine 2: A3 mojibake

1. **Disease:** A3, 7 documents. Examples: `7b1d879aa4e04769` `â€”` for an em dash at offset 554 (52 hits, with
   `U+009D` controls); `94f537dcf85f69f8` `â€œ`-style quotes from offset 2494 to the end (57 C1-control bytes);
   `816e5ec1fb368590` `NoÂ waste` (`U+00C2 U+00A0`) at offset 596 and `Ã…` for `Å` at 3092; `5d1fd12b101321f0`
   `artistÂ\x92s` at 12598.
2. **Medicine:** detect the double-decoding signatures, repair with `ftfy.fix_text`, and drop the document only
   if the signature is still dense after repair (the bytes are gone, not just mis-decoded).
   ```python
   import ftfy
   A3_RE = re.compile(r"â€[\x80-\xbf‘-™]?|Ã[\x80-\xbf\u0080-ÿ]|Â[\xa0-\xbf]|[\x80-\x9f]")
   def medicine_a3(text):
       if not A3_RE.search(text): return text
       new = ftfy.fix_text(text)
       return ("drop", "") if len(A3_RE.findall(new)) * 1000 / max(len(new), 1) > 1.0 else new
   ```
3. **Action:** fix; drop when unrepairable.
4. **Harm test:** gold set 0/62 changed, 0 dropped: PASS. Whole pack: 4 changed, 0 dropped.
5. **Side effects:** the signature regex misses mojibake that went through a non-UTF-8 round trip, for example
   Cyrillic `й` standing in for `é` (`Pokйmon` in `68575a61a90990d5`, `Diffйrents` in `467b5c0aa1d13de8`) and
   symbol-font gibberish (`3dc93ffbd87ba839`): 3 of the 7 labelled documents are not touched. `ftfy` can in rare
   cases "repair" legitimate text that happens to look like mojibake (`Ã` followed by a letter in Portuguese); it
   does not happen in the 62 gold documents.

## Medicine 3: B4 template and code junk in prose

1. **Disease:** B4, 23 documents. Examples: `e3fba14beec00b2b` tracking JS `fbq('track', 'ViewContent');` at offset
   0; `6da64e1f3aa0f61c` image alt residue `dougball.gif - 0.95 K` 18 times from offset 40315; `b0b8c0fe32cb4bee`
   filename `bigstock--191940913.jpg` glued to the first word at offset 126; `6d42edb6050b961a` template bug
   `WRITTEN BY Home Upgrades That Can Save You Money` at offset 39.
2. **Medicine:** delete the residue tokens, not the document.
   ```python
   B4_RES = [re.compile(r"\b[\w-]+\.(?:jpe?g|png|gif|webp)(?:\s*-\s*[\d.]+\s*K)?\b", re.I),
             re.compile(r"\bfbq\([^)]*\);?|\bgtag\([^)]*\);?|\bga\('send'[^)]*\);?"),
             re.compile(r"\{\{\s*[\w.]+\s*\}\}|\$\{[^}]{1,40}\}"),
             re.compile(r"^(?:undefined|NaN|null)\s*$", re.M)]
   def medicine_b4(text):
       new = text
       for rx in B4_RES: new = rx.sub("", new)
       return re.sub(r"[ \t]{2,}", " ", new) if new != text else text
   ```
3. **Action:** fix.
4. **Harm test:** gold set 0/62 changed, 0 dropped: PASS. Whole pack: 8 changed, 0 dropped.
5. **Side effects:** recall is low (2 of 23 labelled documents): most B4 in this pack is placeholder text glued
   into words (`holder maleChase`, `Lance-Earl-Ladn-C-trucsLance`) or an unrendered theme string, which no regex can
   separate from prose. A tutorial that legitimately names `image.png` loses that filename.

## Medicine 4: C1 boilerplate

1. **Disease:** C1, 386 documents (the most common disease: 77% of the pack). Examples: `a6673336e37d2ca9`
   breadcrumb `You are here: Home >` at offset 0 and `Related Links:` at 10208; `0864734353e1b73e` `YOU ARE HERE:
   LAT HomeCollections` at 0 and `Los Angeles Times Articles` at 4980; `80c9139ec8b57301` `Post a Comment` 9 times
   and `No comments :` 6 times; `401400b4e5ef2ee8` `Skip to: Site Menu | Main content` at 63.
2. **Medicine:** remove a line when it is short (8 words or fewer) and starts with a site-chrome phrase.
   ```python
   C1_RE = re.compile(r"^(?:share (?:on|this|via)|tweet|follow (?:us|me|@)|like us|related (?:posts?|articles?|links?|games?)"
       r"|read more|click (?:here|to)|leave a (?:comment|reply)|post(?:ed)? (?:a )?comment|no comments?|\d+ comments?"
       r"|posted (?:by|on|in)|filed under|tags?:|categor(?:y|ies):?|labels?:|skip to|you are here|home\s*[>»|]"
       r"|log ?in|sign (?:in|up)|register|subscribe|newsletter|all rights reserved|copyright|©|privacy policy"
       r"|terms of (?:use|service)|powered by|back to top|print this|email this|previous post|next post|older post"
       r"|newer post|view (?:all|profile)|contact us|advertisement|sponsored|links to this post|<< home)", re.I)
   def medicine_c1(text):
       lines = text.split("\n")
       keep = [ln for ln in lines if not (ln.strip() and len(ln.split()) <= 8 and C1_RE.search(ln.strip()))]
       return re.sub(r"\n{3,}", "\n\n", "\n".join(keep)) if len(keep) != len(lines) else text
   ```
3. **Action:** fix.
4. **Harm test:** gold set 0/62 changed, 0 dropped: PASS. Whole pack: 117 changed, 0 dropped.
5. **Side effects:** the rule only matches a line that *starts* with a chrome phrase, so it reaches 117 of the 386
   labelled documents; the rest are repeated titles, nav bars like `Contents | < Browse | Browse >`, forum
   headers `Author Topic: ... (Read 289 times)` and comment chrome glued to prose with NBSP. A line of real prose
   that starts with "Register" or "Subscribe" (an instruction in an article) is deleted. A sentence that happens to
   start with "Copyright" in a legal article is deleted. Neither case occurs in the 62 gold documents.

## Medicine 5: C2 repeated lines

1. **Disease:** C2, 30 documents. Examples: `50d363e8b8340b11` `never quiet, never soft.....` 21 times from offset
   2715; `8fa9168e8da3a2d4` `Individual Eyelashes Extensions` as a line 4 times at 180; `a874cd0a1d145148` title
   `Maintenance Bond` 3 times at 14/141/194; `e2f62269aa2a0900` caption `borrowed with permission from ...` 3 times.
2. **Medicine:** a line of 20+ characters that appears 3 or more times is kept once; if the repeated lines are more
   than 30% of the non-empty lines the document is dropped.
   ```python
   from collections import Counter
   def medicine_c2(text, min_len=20, min_rep=3, drop_ratio=0.3):
       lines = text.split("\n")
       counts = Counter(ln.strip() for ln in lines if len(ln.strip()) >= min_len)
       rep = {ln for ln, c in counts.items() if c >= min_rep}
       if not rep: return text
       if sum(counts[ln] for ln in rep) / max(sum(1 for ln in lines if ln.strip()), 1) > drop_ratio: return ("drop", "")
       seen, out = set(), []
       for ln in lines:
           s = ln.strip()
           if s in rep:
               if s in seen: continue
               seen.add(s)
           out.append(ln)
       return "\n".join(out)
   ```
3. **Action:** fix; drop when the document is mostly repetition.
4. **Harm test:** gold set 0/62 changed, 0 dropped: PASS. Whole pack: 8 changed, 0 dropped.
5. **Side effects:** a refrain in a poem or song, a repeated stage direction in a play, or a repeated table header
   is collapsed to one copy. Short repeated lines (under 20 characters, e.g. `Post a Comment`) are left to Medicine 4.

## Medicine 6: C3 truncated document

1. **Disease:** C3, 98 documents. Examples: `cd0ef2540a4ee803` teaser cut with `...` at offset 317; `8b697f9f7d91de38`
   ends mid-sentence `I think that you will be` at 2680; `a1b97fd910707a8d` sentence cut where link text was stripped
   `I can't even find a link from` at 4095; `089fde49e557cc5d` ends with the heading `Female Problems` and no body.
2. **Medicine:** only the *stub* form is treated. A document of at most 600 characters whose last word is one no
   sentence ends on (`from`, `the`, `and`, ...) or that ends with a teaser `...` is dropped (the dangling-word test only applies when the text has no
   terminal punctuation).
   ```python
   DANGLING = set("a an the and or but of to in on at by for from with as that which who will would can could is are was were be been being has have had this these those its their his her my our your".split())
   def medicine_c3(text, max_len=600):
       body = text.rstrip()
       if not body: return ("drop", "")
       if len(body) > max_len: return text
       last = (re.findall(r"[A-Za-z']+", body) or [""])[-1].lower()
       teaser = body.endswith(("...", "…", "[...]", "[…]", "(more)", "Read more"))
       unfinished = body[-1] not in ".!?\"')]}»”’:;" and last in DANGLING
       return ("drop", "") if teaser or unfinished else text
   ```
3. **Action:** drop (stubs only); longer truncated documents are labelled, not cut.
4. **Harm test:** gold set 0/62 changed, 0 dropped: PASS. Whole pack: 0 changed, 1 dropped.
5. **Side effects:** my first version trimmed any last line without terminal punctuation; it changed 5 of the 28
   documents then in the proxy set (complete sentences that simply lack a full stop), so it was withdrawn. The
   stub rule's dangling-word test then dropped a clean 560-character document ending `...what research impact is.`,
   which failed the 1% limit on the 65-document proxy; it now applies only when the text has no terminal
   punctuation. The rule catches 1 of the 98 labelled documents, because in this pack C3 is mostly mid-text gaps
   where a link, a citation, a quote or an image was stripped by an earlier cleaner (the readers' notes say most C3 rows are of this kind, not end-of-document cuts).
   There is no safe regex for that; it is the main finding of this slice for the pipeline team: the
   HTML-to-text step drops anchor text and embedded content.

## Medicine 7: C5 keyword lists and SEO spam

1. **Disease:** C5, 61 documents. Examples: `c64a732a64b1ce8b` `teknik forex tf h1` injected
   at offsets 44, 6858 and throughout random textbook sentences; `d7d9f2c89773b700` Korean casino keywords
   `온라인카지노` injected mid-sentence at 2801, 5424, 8201; `a381d9217f39570e` `cheap michael kors handbags` at 93;
   `ba893cf355e53633` spun word salad `be sure to seems to cost` from offset 147.
2. **Medicine:** drop when (a) a 4-word phrase made of 3+ content words repeats 6+ times at a density of at least
   8 per 1000 words, or (b) a CJK/Hangul/Cyrillic run sits between Latin words on the same line at least twice.
   ```python
   from collections import Counter
   STOP = set("the a an of and or to in on for with at by from is are was were be as it this that these those its".split())
   FOREIGN = "가-힯一-鿿぀-ヿЀ-ӿ"
   INJECT_RE = re.compile(rf"[A-Za-z]{{3,}}[ ,.]+[{FOREIGN}]{{2,}}[ ,.]+[A-Za-z]{{3,}}")
   def medicine_c5(text, min_rep=6, min_density=0.008):
       words = re.findall(r"[a-z0-9']+", text.lower())
       if len(words) < 60: return text
       grams = Counter(" ".join(words[i:i+4]) for i in range(len(words) - 3))
       phrase, n = max(grams.items(), key=lambda kv: kv[1])
       content = [w for w in phrase.split() if w not in STOP]
       spam = n >= min_rep and len(content) >= 3 and n / len(words) >= min_density
       return ("drop", "") if spam or len(INJECT_RE.findall(text)) >= 2 else text
   ```
3. **Action:** drop.
4. **Harm test:** gold set 0/62 changed, 0 dropped: PASS. Whole pack: 0 changed, 8 dropped.
5. **Side effects:** precision was bought with recall. A looser version (4 repeats, 2 content words, any
   non-Latin share under 5%) dropped 44 documents in the pack but also a clean student-union article (`a U-Pass
   program` 5 times) and a legitimate bilingual Chinese-English dictionary page, so it was tightened. The tight
   rule catches 7 of the 61 labelled documents: most C5 here is *spun* English (`be sure to seems to cost`) or
   glued textbook sentences, which read as ordinary words to a regex. Those need a language-model perplexity or
   a repetition-of-rare-n-grams filter at the pipeline level, not a line rule. A product review that names the
   product in four content words six or more times (`sony alpha 7 iii`) would be dropped.

## Medicine 8: F1 personal data

1. **Disease:** F1, 8 documents. Examples (type and position only): `71f25549c2c4200d` email at offset 2436;
   `416e12ac72df0b07` emails at offsets 669, 964, 2192; `e5d949484740fff3` PO box at 8031, email at 8120, phone at
   8155; `c3ff48f35f98745c` phone at offset 8567.
2. **Medicine:** replace with a placeholder. An email is redacted when its shape is personal (first.last, digits,
   a long local part, or a webmail domain); a single-word mailbox at an organisation's own domain is kept. Phone
   numbers in national or international format are always redacted.
   ```python
   EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
   PHONE_RE = re.compile(r"(?<![\d\w-])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}(?![\d\w-])")
   WEBMAIL_RE = re.compile(r"@(?:gmail|googlemail|yahoo|ymail|hotmail|outlook|live|msn|aol|icloud|me|protonmail|proton|rediffmail|zoho|gmx|yandex|mail)\.", re.I)
   PERSONAL_LOCAL_RE = re.compile(r"[._\-]|\d|^.{13,}$")
   def _private(addr): return bool(WEBMAIL_RE.search(addr) or PERSONAL_LOCAL_RE.search(addr.split("@", 1)[0]))
   def medicine_f1(text):
       new = EMAIL_RE.sub(lambda m: "[EMAIL]" if _private(m.group()) else m.group(), text)
       return PHONE_RE.sub("[PHONE]", new)
   ```
3. **Action:** fix (redact in place).
4. **Harm test:** gold set 0/62 changed, 0 dropped: PASS. Whole pack: 13 changed, 0 dropped.
5. **Side effects:** the shape rule is a guess about who is private: a person with a one-word mailbox at their own
   domain is not redacted, and a company address like `sales.team@...` is. Business phone numbers (restaurants,
   banks, a shop) are redacted although they are public; the readers chose not to label those F1. The phone
   regex matches 10-digit groups only; UK/EU formats and numbers written without separators pass through. Postal
   addresses and PO boxes are not handled.

## No medicine: D3 (24), D4 (18), C4 (16), H3 (7)

- **D3 mixed language (24):** labelled, not judged (DISEASES.md, group D). The Urdu, Hindi, German, Spanish and
  Portuguese code-switching and bilingual page shells in this pack are mostly natural, so there is no medicine.
- **D4 bad machine translation (18):** nearly all are *spun* text (`suches as`, `they can cost not cheap`,
  `alcoholic beverages alcoholic beverage`, e.g. `e1d3971ca464902c`, `a85d5ac50a23111d`). There is no regex for
  grammar damage; a language-model perplexity filter would catch it, and most of these are also C5 so Medicine 7
  or that filter removes them.
- **C4 two documents joined (16):** no safe regex; a topic boundary is invisible to a pattern. Most C4 documents are
  also C5 spam.
- **H3 same content elsewhere (7):** Wikipedia reposts and wire stories (e.g. `e22858e9e5d594cd`, a Wikipedia
  biography; `c84f362725cdf249`, an AP story). Detecting them needs the other sources (a Wikipedia dump, a news
  corpus) to hash against; one pack cannot do it, so this is a cross-source dedup job for the pipeline.

---

## Harm test summary

Gold = `teams/01-data-a/gold/en-dclm_gold.csv`, 62 documents. Limit = 1 document changed or dropped
(`max(1, 1% of 62)`). Output of `harm_test.py --rule all`; the last row runs the eight medicines in file order.

| Medicine | Pack: changed | Pack: dropped | Gold: changed | Gold: dropped | Result |
|---|---|---|---|---|---|
| A1 invisible characters | 10 | 0 | 0 | 0 | PASS |
| A3 mojibake | 4 | 0 | 0 | 0 | PASS |
| B4 template residue | 8 | 0 | 0 | 0 | PASS |
| C1 boilerplate lines | 117 | 0 | 0 | 0 | PASS |
| C2 repeated lines | 8 | 0 | 0 | 0 | PASS |
| C3 truncated stubs | 0 | 1 | 0 | 0 | PASS |
| C5 keyword spam | 0 | 8 | 0 | 0 | PASS |
| F1 personal data | 13 | 0 | 0 | 0 | PASS |
| All eight in order | | | 0 | 0 | PASS |

Recall against my own labels (of the documents I labelled with the code, how many the medicine touches):
A1 10/12, F1 6/8, A3 4/7, C1 117/386, C2 7/30, C5 7/61, B4 2/23, C3 1/98. The low numbers are deliberate: each
rule was tightened until it left the clean documents alone, and what it then misses (spun prose, stripped link
text, placeholder text glued into words) is not a regex problem.
