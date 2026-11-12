# Medicine sheet: ind-te-fw2 (sandeepkunkunuru)

Pack: 500 Telugu documents from FineWeb-2 (`tel_Telu`). All 500 read in full. Verdicts: 176 clean, 221 fix, 103 drop.

**Harm test set.** Every rule below is tested with `teams/02-data-b/tools/harm_test_indic.py` on the **own-pack real gold set (`ind-te-fw2_gold.csv`: 18 two-reader clean documents)**, the **verified sibling pack gold set (`ind-te-sangraha-v_gold.csv`: 18 documents on `main` `ea7b533`, 27 on 2 Nov, 23 on 31 Oct)**, and the **Telugu real gold set (`teams/02-data-b/gold/telugu_gold.csv`: 50 documents on 2 Nov and 46 documents on 31 Oct; 60 documents on 3 Nov `ea7b533` across `ind-te-fw2` 18, `ind-te-sangraha-s` 24, and `ind-te-sangraha-v` 18)**. Under the TSAI rule (`CAP 31 Oct: per pack, never pooled`, `max(1%, 1 document)`), a rule passes when it changes or drops at most 1 gold document in its pack and passes both the ZWJ/ZWNJ joiner audit and the NFC/compatibility-character normal-form audit. I also report results on the 176 documents of `ind-te-fw2` that I labelled `clean`.

Columns used below: *recall* = labelled documents in `ind-te-fw2` that the medicine changes or drops; *fires on unlabelled* = documents in `ind-te-fw2` without that label that the medicine changes or drops.

## Summary

| Code | Count | Action | Own-pack gold (`ind-te-fw2`, 18) | `ind-te-sangraha-v` gold (18 / 27) | Telugu gold (50) | Gold % | Joiner / Form audit | Result | Clean-slice (176) | Recall | Fires on unlabelled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 250 | fix | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** | 0/176 (0.0%) | 122/250 | 1 |
| D4 | 87 | drop | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** | 0/176 (0.0%) | 71/87 (60/87 text-only) | 6 (2 are D5) |
| D3 | 83 | none (no-op) | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** (no medicine) | 0/176 (0.0%) | 0/83 | 0 |
| C2 | 41 | fix | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** | 0/176 (0.0%) | 17/41 | 13 |
| C5 | 14 | drop | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** (rejected for pipeline: side effects on fix slice) | 1/176 (0.6%) | 2/14 | 21 |
| C3 | 9 | fix | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** (v1 `..`/`…` failed at 1.20%; v2 `[…]` passes at 0.00%) | 0/176 (0.0%) | 1/9 | 1 |
| B2 | 8 | fix | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** | 0/176 (0.0%) | 6/8 | 0 |
| F3 | 8 | drop | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** | 0/176 (0.0%) | 7/8 | 0 |
| C4 | 8 | drop | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** | 0/176 (0.0%) | 1/8 | 1 |
| D5 | 8 | drop (by the D4 rule) | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** | 0/176 (0.0%) | 2/8 | – |
| A6 | 8 | fix | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** | 0/176 (0.0%) | 3/8 | 3 |
| F1 | 6 | fix | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** | 1/176 (0.6%) | 6/6 | 7 |
| G1 | 4 | fix | 0/18 (0.00%) | 0/18 (0.00%) | 0/50 (0.00%) | 0.00% | ok / ok | **PASS** | 0/176 (0.0%) | 4/4 | 0 |
| **ALL IN ORDER** | – | pipeline | **0/18 (0.00%)** | **0/18 (0.00%)** | **0/50 (0.00%)** | **0.00%** | **ok / ok** | **PASS** | 1/176 (0.6%) | – | – |

All medicines together (`ALL IN ORDER` in `harm_test_indic.py`): **0 changed and 0 dropped out of 18 own-pack gold documents (`ind-te-fw2`, 0.00%, PASS), 0 changed and 0 dropped out of 18 `ind-te-sangraha-v` gold documents (`main` `ea7b533`, 0.00%, PASS; also 0/27 on 2 Nov and 0/23 on 31 Oct), and 0 changed and 0 dropped out of 50 real Telugu gold documents (`telugu_gold.csv`, 0.00%, PASS; ZWJ/ZWNJ audit PASS; normal-form audit PASS)**, and 1 changed out of 176 `ind-te-fw2` clean-slice documents (0.6%, the F1 helpline number below). The drop rules remove 72 of the 87 D4 documents, 2 of the 8 D5 documents and all 8 F3 documents.

## Medicine 1: C1 boilerplate

1. **Disease:** C1, 250 documents. Examples: `8d59bc181e2d8446` menu line `- వార్తలు - సినిమా - స్పోర్ట్స్` at offset 0;
   `ab4df107c4d439c6` `- మరింత చదవండి: IO నుండి` at offset 869; `58a735e896dd47e5` tweet embed URL at offset 1710.
   The most common markers are "ఇది కూడా చదవండి"/"Also read", "తాజా వార్తలు (Latest News)", "Don't Miss!", "Just In",
   News18 bylines, "First Publish Date", the Eenadu footer "గమనిక: ఈనాడు.నెట్‌లో కనిపించే…", and `pic.twitter.com` lines.
2. **Medicine:** delete a whole line when it matches a known furniture pattern (anchored at the line start, or the whole
   line for short words such as `మరిన్ని` and `ప్రకటన`).
   ```python
   C1_LINE = re.compile(r"""^\s*(?:
       (?:Also\s+[Rr]ead|Read\s+[Mm]ore|Don'?t\s+Miss!?|Just\s+In|News\s+Reels|More\s+Stories|Leave\s+a\s+Reply
         |View\s+this\s+post\s+on\s+Instagram|Sign\s+in|Follow\s+[Uu]s|Subscribe|Share\s+(?:on|this)
         |Image\s+Source|Disclaimer|Published\s+On|First\s+Publish\s+Date|Updated\s+Date|Tags?|TAGS)\b.*
     | (?:ఇది\s+కూడా\s+చదవండి|ఇవి\s+కూడా\s+చదవండి|ఇవీ\s+చదవండి|ఇదీ\s+చదవండి|ఇది\s+చూడండి|తాజా\s+వార్తలు
         |ట్రెండింగ్\s+వార్తలు|ఉత్పత్తి\s+ట్యాగ్లు|పోస్ట్\s+సమయం|వ్యాఖ్యను\s+పోస్ట్\s+చేయండి
         |మీ\s+అభిప్రాయాలను\s+కామెంట్|గమనిక:\s*ఈనాడు\.నెట్|\[\[సంబంధిత\s+కథనం\]\]).*
     | (?:మరిన్ని|ప్రకటన|g-ప్రకటన)(?:\s*-\s*[\w\s]{0,30})?
     | .*(?:Empowering\s+140\+\s+Indians|India\s+Herald\s+Group\s+of\s+Publishers|pic\.twitter\.com/|t\.co/\w).*
     | -?\s*\d{1,2}\s+\w{3}\s+\d{4}\s+\d{1,2}:\d{2}\s+[AP]M(?:\s+GMT)?.*
     | \w[\w\s.]{0,40},\s*News18,\s*\w+.*
   )\s*$""", re.X)
   def c1_boilerplate(t, url=None):
       return "\n".join(l for l in t.split("\n") if not C1_LINE.match(l))
   ```
3. **Action:** fix (delete the line).
4. **Harm test:** real Telugu gold set (`telugu_gold.csv`, 46 documents across `ind-te-fw2` 18, `ind-te-sangraha-s` 5, `ind-te-sangraha-v` 23):
   - Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Note: omitting `.strip()` on the joined lines avoids stripping trailing spaces/newlines on clean `ind-te-sangraha-v` documents when no line matches `C1_LINE`. Clean slice (`ind-te-fw2`, 176 docs): 0 changed, 0 dropped (0.0%).
5. **Side effects:** recall is 122/250. Boilerplate that is glued into a paragraph, or that uses a phrase per site
   (headline lists, breadcrumb runs), is missed. A real sentence that starts with "Tags" or "Subscribe" would be deleted.
   I saw none in the pack.

## Medicine 2: D4 machine translation (also covers D5 translationese)

1. **Disease:** D4, 87 documents. D5, 8 documents. Examples: `ab4df107c4d439c6` `మీకు పని చేస్తుంది. గాలిలో మీటర్లు`
   at offset 500 (an auto-translated Fortnite guide); `0085c49fc57558bf` `తెల్లటి శ్రేణి చలనచిత్రాలు` at offset 880;
   `7ef5b7ab6df65268` `పొడవైన పొడవాటి తోక కీలకపదాలను` at offset 5630 ("long tail keywords", word for word).
2. **Medicine:** two signals, and either one drops the document.
   - The host starts with `te.` on a non-Telugu site (`te.task1.info`, `te.aesbuc.pt`, …). These are auto-translation
     proxies of English or European sites. Wikimedia `te.` hosts and `te.vikaspedia.in` are excluded.
   - Calque density: more than 30 per 1,000 words of (`మరియు` "and" + `యొక్క` "of"), with at least 6 total calque tokens (`marks >= 6 and rate > 30`). Native Telugu joins clauses with suffixes
     and the genitive case, and rarely writes `యొక్క` ("of"). Machine translation writes one for each English "and"
     and "of".
   ```python
   from urllib.parse import urlparse
   WIKI = re.compile(r"^te\.(?:(?:m\.)?wiki(?:pedia|source|books|quote|tionary|news)\.org|vikaspedia\.in)$")
   def d4_machine_translation(t, url=None):
       host = urlparse(url or "").netloc.lower()
       if host.startswith("te.") and not WIKI.match(host):
           return True
       marks = t.count("మరియు") + t.count("యొక్క")
       rate = 1000 * marks / max(1, len(re.findall(r"\S+", t)))
       return True if (marks >= 6 and rate > 30) else False
   ```
   Measured rate per 1,000 words (p10 / p50 / p90): D4+D5 documents 18.1 / 38.5 / 59.5; clean documents 0.0 / 0.0 / 0.8.
   40 of 95 D4+D5 documents have a `te.` host; 0 of 176 clean documents do.
3. **Action:** drop.
4. **Harm test:** own-pack real gold set (`ind-te-fw2_gold.csv`, 18 documents), verified sibling pack gold set (`ind-te-sangraha-v_gold.csv`, 18 documents on `main` `ea7b533`, 27 on 2 Nov, 23 on 31 Oct), and Telugu real gold set (`telugu_gold.csv`, 50 documents on 2 Nov and 46 documents on 31 Oct):
   - Own-pack gold (`ind-te-fw2`, 18 docs): Changed 0 of 18 (0.00%). Dropped 0 of 18 (0.00%). **PASS**
   - Verified sibling pack gold (`ind-te-sangraha-v`, 18 docs on `ea7b533` / 27 on 2 Nov / 23 on 31 Oct): Changed 0 (0.00%). Dropped 0 (0.00%). **PASS**
   - Full Telugu gold (`telugu_gold.csv`, 50 docs on 2 Nov / 46 docs on 31 Oct): Changed 0 (0.00%). Dropped 0 (0.00%). **PASS** (Note: on the 3 Nov expanded 24-doc synthetic translated pack `ind-te-sangraha-s_gold.csv`, 3 short synthetic items of 88–124 words have calque rates of 65.2–72.6 per 1,000 words; `ind-te-sangraha-s` uses its own rule `DB-D4-012`.)
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Clean slice (`ind-te-fw2`, 176 docs): 0 changed, 0 dropped (0.0%).
   - **Week-2 tokenizer sample audit (`DB-D4-011` on `train/ind-te-fw2/part-00000.parquet` and `train/ind-te-sangraha-v/part-00000.parquet`):**
     - The v1 threshold (`(marks >= 6 or (marks >= 3 and "యొక్క" in t)) and rate > 15`) dropped 792 of 5,997 documents in `ind-te-fw2` (text-only) and 493 of 8,609 in `ind-te-sangraha-v`. Reading 20 dropped documents from each pack confirmed that `rate > 15` (and `3 <= marks < 6` with `యొక్క`) caught short native Telugu news articles (`4ed2e3cf7adb1775` on `telugu.latestly.com` with 3 marks at rate 24.4 from a trailing disclaimer, `22816de24fcb1e99` and `514b36f500507f3f` on `telugu.drivespark.com` at rates 22.7 and 17.2, `f04faca3308a1b04` on `telugu.samayam.com` at rate 18.0, `70cb7aa9df299796` Toyota press release at rate 23.6, `a2a089536f6dc7e6`, `a2c0be4957dce9b1`, `28d36038f58c44aa`), classical literary/philosophical prose with `యొక్క` (`0da6cd97a63f7645` at rate 15.7, `0942d09d44e37136` at rate 16.6), a named human translation of the Quran (`55835a003c67b0a5` at rate 26.6), and 3 Telugu Wikipedia pages (`60f3675bfbe8b45b`, `00f40cc34648f10f`, `888e8269907e36c9`) when `clean.py` invoked the rule without `url`.
     - Narrowing to `WIKI` (Wikimedia `te.*` + `te.vikaspedia.in`) and `marks >= 6 and rate > 30` reduces drops on `ind-te-fw2` from 792 to **629** (with `url`; **558** text-only) and keeps **5 of the 6** good Telugu documents in the 20-doc sample (plus all 24 Telugu Wikipedia pages), and reduces drops on `ind-te-sangraha-v` from 493 to **370**, keeping **6 of the 7** good Telugu documents while still dropping **all 13 of 13** machine-translated documents (`75ea6c5607880a13`, `8f3326d950b224df`, `ad90db53f6a10d60`, `39d0649ecb9f6cfd`, `2d51003f0275bc0a`, `5a55ae5a2b0ffd8f`, `0cf72889874b7039`, `311a2fd7627e1466`, `9e7fbbf7bd183e85`, `a2f94cfc107f219d`, `1ef1e43a15a83bec`, `564a7303c2a65481`, `000079226d796e6c`).
5. **Side effects:** on the 500-document diagnosis pack, D4 recall is 71/87 with `url` (60/87 text-only), clean-slice drops are 0/176 (0.0%), and unlabelled D4 drops fall from 18 down to 6 (2 of which are D5). Native or translated prose with heavy conjunction/genitive lists above 30 per 1,000 words (such as `3f60723fa29917ca` at 46.4 and `29fe193635c628cb` at 36.2) can still cross the threshold.

## Medicine 3: C2 repeated lines

1. **Disease:** C2, 41 documents. Examples: `6faa50209f00b4cf` the line `————` 5 times from offset 1386;
   `5c570eaba09f22b5` the paragraph `గోదారమ్మ మరోసారి ఉగ్రరూపం దాలుస్తోంది` repeated from offset 266;
   `7a37badd365e0f53` `‘‘అధికారమే మాకు అండగా ఉంది` repeated at offset 333.
2. **Medicine:** keep the first copy of each line (15 characters or more after strip) that occurs 2 or more times, and
   delete the later copies.
   ```python
   from collections import Counter
   def c2_repeats(t, url=None):
       lines = t.split("\n"); n = Counter(l.strip() for l in lines if len(l.strip()) >= 15)
       seen, out = set(), []
       for l in lines:
           s = l.strip()
           if n.get(s, 0) >= 2:
               if s in seen: continue
               seen.add(s)
           out.append(l)
       return "\n".join(out)
   ```
3. **Action:** fix.
4. **Harm test:** real Telugu gold set (`telugu_gold.csv`, 46 documents across `ind-te-fw2` 18, `ind-te-sangraha-s` 5, `ind-te-sangraha-v` 23):
   - Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Clean slice (`ind-te-fw2`, 176 docs): 0 changed, 0 dropped (0.0%). I also tested a threshold of 3 copies: recall fell from 17/41 to 10/41.
5. **Side effects:** recall 17/41. Readers also labelled repeats inside a line (a title repeated in the first sentence)
   and short repeated lines, and this rule cannot see those. A poem or song with a refrain would lose the refrain.

## Medicine 4: C5 keyword and link lists (rejected)

1. **Disease:** C5, 14 documents. Examples: `6faa50209f00b4cf` `ప్రైజ్ బాండ్ ప్రైమ్ ఫోటో స్టేట్ గెస్ పేపర్స్` at
   offset 1336 (keyword stuffing); `7ad93bc101c3a384` a list of adult video titles at offset 97; `ba133083568cfeae` a
   list of unrelated article teasers at offset 0.
2. **Medicine tested:** after the C1 deletion, drop the document when at least 14 non-empty lines are short (under 60
   characters) and have no end punctuation, and they make up more than 50% of the lines.
   ```python
   _C5_C1_LINE = re.compile(r"""^\s*(?:
       (?:Also\s+[Rr]ead|Read\s+[Mm]ore|Don'?t\s+Miss!?|Just\s+In|News\s+Reels|More\s+Stories|Leave\s+a\s+Reply
         |View\s+this\s+post\s+on\s+Instagram|Sign\s+in|Follow\s+[Uu]s|Subscribe|Share\s+(?:on|this)
         |Image\s+Source|Disclaimer|Published\s+On|First\s+Publish\s+Date|Updated\s+Date|Tags?|TAGS)\b.*
     | (?:ఇది\s+కూడా\s+చదవండి|ఇవి\s+కూడా\s+చదవండి|ఇవీ\s+చదవండి|ఇదీ\s+చదవండి|ఇది\s+చూడండి|తాజా\s+వార్తలు
         |ట్రెండింగ్\s+వార్తలు|ఉత్పత్తి\s+ట్యాగ్లు|పోస్ట్\s+సమయం|వ్యాఖ్యను\s+పోస్ట్\s+చేయండి
         |మీ\s+అభిప్రాయాలను\s+కామెంట్|గమనిక:\s*ఈనాడు\.నెట్|\[\[సంబంధిత\s+కథనం\]\]).*
     | (?:మరిన్ని|ప్రకటన|g-ప్రకటన)(?:\s*-\s*[\w\s]{0,30})?
     | .*(?:Empowering\s+140\+\s+Indians|India\s+Herald\s+Group\s+of\s+Publishers|pic\.twitter\.com/|t\.co/\w).*
     | -?\s*\d{1,2}\s+\w{3}\s+\d{4}\s+\d{1,2}:\d{2}\s+[AP]M(?:\s+GMT)?.*
     | \w[\w\s.]{0,40},\s*News18,\s*\w+.*
   )\s*$""", re.X)
   def medicine_c5(t, url=None):
       cleaned = "\n".join(l for l in t.split("\n") if not _C5_C1_LINE.match(l))
       lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
       if not lines:
           return False
       short_no_punct = sum(1 for l in lines if len(l) < 60 and not re.search(r"[.!?:;।…\"'”’)\]]$", l))
       return True if (short_no_punct >= 14 and short_no_punct / len(lines) > 0.5) else False
   ```
3. **Action:** drop.
4. **Harm test:** own-pack real gold set (`ind-te-fw2_gold.csv`, 18 documents) and full Telugu real gold set (`telugu_gold.csv`, 50 documents across `ind-te-fw2` 18, `ind-te-sangraha-s` 5, `ind-te-sangraha-v` 27; 46 documents in the 31 Oct snapshot):
   - Own-pack gold (`ind-te-fw2`, 18 docs): Changed 0 of 18 (0.00%). Dropped 0 of 18 (0.00%). **PASS**
   - Full Telugu gold (`telugu_gold.csv`, 50 docs): Changed 0 of 50 (0.00%). Dropped 0 of 50 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Clean slice (`ind-te-fw2`, 176 docs): 0 changed, 1 dropped (0.6%, `2acf40242963f9fd` film crew credits).
5. **Side effects. Rejected:** it drops 16 documents that readers labelled `fix` (news pages with captions, sub-heads
   and menus that C1 misses) plus 1 clean film-credits press release, and it catches only 2 of the 14 C5 documents. Line shape does not separate list pages from
   articles in this pack. The medicine is **not** recommended for `spec_v1`. In the pipeline, D4 (10) and F3 (4) together drop
   11 of the 14 C5 documents, because SEO list pages here are almost always machine-translated or adult. A real C5 medicine needs a
   link and teaser signal from the HTML, which this text-only pack does not have.

## Medicine 5: G1 orphan vowel signs

1. **Disease:** G1, 4 documents (plus 4 G2 documents with broken conjuncts). Examples: `a472cbb07057854e` a virama after a space, `్జకాగా`, at offset 4003
   (hex U+0020 U+0C4D U+0C1C); `b1fc122a01e457a3` `ిిచేదు` at offset 2047 (U+0020 U+0C3F U+0C3F);
   `19499950e087f669` `ంంంంచి` at offset 1704 (U+0020 U+0C02).
2. **Medicine:** delete a run of dependent vowel signs, virama or anusvara that follows whitespace or a line start. A
   dependent sign must follow a consonant.
   ```python
   G1_RX = re.compile(r"(?m)(^|\s)[ా-ౖఁ-ఃౢౣ]+")
   def g1_orphan_signs(t, url=None):
       return G1_RX.sub(r"\1", t)
   ```
3. **Action:** fix.
4. **Harm test:** real Telugu gold set (`telugu_gold.csv`, 46 documents across `ind-te-fw2` 18, `ind-te-sangraha-s` 5, `ind-te-sangraha-v` 23):
   - Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Clean slice (`ind-te-fw2`, 176 docs): 0 changed, 0 dropped (0.0%).
5. **Side effects:** recall 4/4 on orphan matras/viramas. A space put *inside* a word before a consonant (`అం దిస్తారు`, `ఉద్య మం`) or a legacy-font conjunct substitution (`నేనేనువ్ఞ్వ`, G2) is not detectable by a whitespace-matra rule without a dictionary, so it stays. Deleting the orphan sign leaves the word
   misspelt. It does not restore the word. Re-attaching the sign to the previous consonant would be riskier.

## Medicine 6: B2 HTML tags

1. **Disease:** B2, 8 documents. Examples: `7ef5b7ab6df65268` `<span style="font-family: Mandali;">` at offset 2497;
   `41c998453152115f` `<a href="https://www.siasat.com/Telangan…` at offset 1268; `b59cc78294a8662b`
   `width="1600" height="1600" class="size-full` at offset 60.
2. **Medicine:**
   ```python
   B2_RX = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^<>]{0,300})?/?>|<>|\b(?:width|height|class|style)=\"[^\"]*\"")
   def b2_html(t, url=None):
       return B2_RX.sub("", t)
   ```
3. **Action:** fix.
4. **Harm test:** real Telugu gold set (`telugu_gold.csv`, 46 documents across `ind-te-fw2` 18, `ind-te-sangraha-s` 5, `ind-te-sangraha-v` 23):
   - Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Clean slice (`ind-te-fw2`, 176 docs): 0 changed, 0 dropped (0.0%).
5. **Side effects:** text that discusses HTML (a tutorial that shows `<div>`) would lose its examples. Broken tag
   fragments with no `<` (`- 24>`) are missed.

## Medicine 7: F3 harmful content

1. **Disease:** F3, 8 documents. Examples: `7ad93bc101c3a384` adult video title list from offset 0;
   `0642038506ef1eee` stalkerware guide "how to read someone's texts without them knowing" at offset 7245;
   `6faa50209f00b4cf` prize-bond gambling guess papers from offset 0.
2. **Medicine:** drop when the URL names adult, gambling or spyware content, or when the text has 3 or more adult or
   betting terms.
   ```python
   F3_URL = re.compile(r"sex-?stor|(?<![a-z])sex(?![a-z])|porn|xxx|erotic|erotyczn|adult|phone-spy|spy-on|prize-?bond"
                       r"|satta|casino|betting", re.I)
   F3_RX = re.compile(r"sex\s*stor|porn|xxx|\bnude\b|దెంగ|పూకు|మొడ్డ|బూతు\s*కథ|సెక్స్\s*కథ|prize\s*bond|satta\s*matka"
                      r"|betting\s*tips", re.I)
   def f3_harmful(t, url=None):
       return True if (F3_URL.search(url or "") or len(F3_RX.findall(t)) >= 3) else False
   ```
3. **Action:** drop.
4. **Harm test:** real Telugu gold set (`telugu_gold.csv`, 46 documents across `ind-te-fw2` 18, `ind-te-sangraha-s` 5, `ind-te-sangraha-v` 23):
   - Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Clean slice (`ind-te-fw2`, 176 docs): 0 changed, 0 dropped (0.0%).
5. **Side effects:** recall 7/8. It misses `te.hunterschool.org` (a manipulative dating guide with no keyword). The
   first version of the URL pattern matched "Sus**sex**" in a cricket story. The `(?<![a-z])` guard fixes that, but
   other substrings can still collide. A news report *about* betting or pornography laws would be dropped if its URL
   has the word.

## Medicine 8: C4 two documents joined (news-feed dumps)

1. **Disease:** C4, 8 documents. Examples: `be0a3e30ba42803f` about 40 unrelated dated news items from offset 15;
   `5fcc07384b87d161` three unrelated stories at offsets 0, 1030 and 2135; `7e2931c2867a729f` an English press release
   followed by its Telugu version at offset 2144.
2. **Medicine:** drop when 3 or more time stamps (`23 min ago`, `30 Mar 2023`) appear, because each item of a feed
   carries its own stamp.
   ```python
   C4_RX = re.compile(r"(?m)(?:\d+\s+(?:min|mins|hours?)\s+ago|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct"
                      r"|Nov|Dec)\w*\s+\d{4})")
   def c4_feed(t, url=None):
       return True if len(C4_RX.findall(t)) >= 3 else False
   ```
3. **Action:** drop.
4. **Harm test:** real Telugu gold set (`telugu_gold.csv`, 46 documents across `ind-te-fw2` 18, `ind-te-sangraha-s` 5, `ind-te-sangraha-v` 23):
   - Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Clean slice (`ind-te-fw2`, 176 docs): 0 changed, 0 dropped (0.0%).
5. **Side effects:** recall 1/8 alone, 3/8 in the pipeline. Most joins have no marker at all: two stories run on with
   no boundary. Finding them needs a topic-shift model, not a rule. A timeline article with many dates would be dropped.

## Medicine 9: C3 truncated teaser

1. **Disease:** C3, 9 documents. Examples: `8c5a7540bec0d441` `పాకిస్థాన్ క్రికెట్ […]` at offset 540;
   `232615716ef393f4` `ఈ మద్య సం` stops mid-word at offset 875; `2311ca6e49dffc35` `వేసుక..` at offset 300.
2. **Medicine:** when the last paragraph ends in `[…]` or `[...]`, delete that paragraph.
   ```python
   def c3_teaser(t, url=None):
       paras = t.rstrip().split("\n")
       if len(paras) > 1 and re.search(r"\[(?:…|\.\.\.)\]\s*$", paras[-1]):
           return "\n".join(paras[:-1]).rstrip()
       return t
   ```
3. **Action:** fix.
4. **Harm test:** real Telugu gold set (`telugu_gold.csv`, 46 documents across `ind-te-fw2` 18, `ind-te-sangraha-s` 5, `ind-te-sangraha-v` 23):
   - Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Clean slice (`ind-te-fw2`, 176 docs): 0 changed, 0 dropped (0.0%). The first version also cut paragraphs that end in `..`
   or `…`. It changed 2 clean-slice documents (1.2%) and **failed**: Telugu writers end sentences with `..` and `…` as a style
   (`తో పాటు..`, `కొట్లాడతాం…`).
5. **Side effects:** recall 1/9. A cut in the middle of a word or sentence with no marker is not detectable by a rule.
   The automatic scan flagged 115 documents for "no end punctuation", and reading confirmed 9.

## Medicine 10: F1 personal data

1. **Disease:** F1, 6 documents. Examples: `b6ddb1f2f2e4456f` phone number at offset 2432; `b84adcd535648e79` phone
   number at offset 5462; `ed4dc90ebfde2f56` phone number at offset 8072 (values not copied).
2. **Medicine:** delete Indian mobile numbers and e-mail addresses.
   ```python
   F1_RX = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+|(?<!\d)(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
   def f1_pii(t, url=None):
       return F1_RX.sub("", t)
   ```
3. **Action:** fix (delete the value, keep the document). I delete rather than write a placeholder token, so that no
   new marker string enters the training text.
4. **Harm test:** real Telugu gold set (`telugu_gold.csv`, 46 documents across `ind-te-fw2` 18, `ind-te-sangraha-s` 5, `ind-te-sangraha-v` 23):
   - Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Clean slice (`ind-te-fw2`, 176 docs): 1 changed (`c5a74a6de69221b8`, a public helpline number), 0 dropped (0.6%).
5. **Side effects:** it also deletes public numbers (helplines, offices) and company e-mail addresses, 7 documents in
   the pack. That cost is accepted for privacy. It misses landlines, addresses and ID numbers.

## Medicine 11: A6 look-alike anusvara

1. **Disease:** A6, 8 documents. Examples: `d5308e76e13e8058` `వ్యక్తిత్వo` with Latin `o` (U+006F) for anusvara at
   offset 2910; `64e785802da2651a` `శoఖం` at offset 3160; `f7dafcbdfdb85610` `స౦గతి` with Telugu digit zero (U+0C66)
   at offset 70.
2. **Medicine:** a Latin `o` or Telugu digit zero that follows a Telugu consonant or vowel sign, and is followed by a
   consonant, a space or punctuation, becomes anusvara U+0C02.
   ```python
   A6_RX = re.compile(r"(?<=[క-హా-ౌ])[o౦](?=[క-హ]|\s|[.,!?]|$)")
   def a6_lookalike(t, url=None):
       return A6_RX.sub("ం", t)
   ```
3. **Action:** fix.
4. **Harm test:** real Telugu gold set (`telugu_gold.csv`, 46 documents across `ind-te-fw2` 18, `ind-te-sangraha-s` 5, `ind-te-sangraha-v` 23):
   - Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Clean slice (`ind-te-fw2`, 176 docs): 0 changed, 0 dropped (0.0%).
5. **Side effects:** recall 3/8. Other stray Latin letters (`చేయవచ్చుn`, `తయారుచేయగలిగేS`) or embedded Devanagari (`।`, Hindi tweet) are not look-alike anusvaras. A Telugu number written right after a word (`క౦` meaning "ka 0") would be changed. I saw none.

## Medicine 12: D3 mixed language (no-op; clean + D3 is clean)

1. **Disease:** D3, 83 documents (for example `ab4df107c4d439c6` `Fortnite చాప్టర్ 3` at offset 188). Telugu news writes English
   names, brands and terms in Latin script, often with a Telugu suffix (`YouTubeలో`).
2. **Medicine:** no-op (`DISEASES.md`: "label it, do not judge it"; `clean + D3` is clean for gold voting).
   ```python
   def medicine_d3(t, url=None):
       return t
   ```
3. **Action:** none (keep text unchanged). 12 documents where D3 is the only label have verdict `clean`.
4. **Harm test:** own-pack real gold set (`ind-te-fw2_gold.csv`, 18 documents) and full Telugu real gold set (`telugu_gold.csv`, 50 documents across `ind-te-fw2` 18, `ind-te-sangraha-s` 5, `ind-te-sangraha-v` 27; 46 documents in the 31 Oct snapshot):
   - Own-pack gold (`ind-te-fw2`, 18 docs): Changed 0 of 18 (0.00%). Dropped 0 of 18 (0.00%). **PASS**
   - Full Telugu gold (`telugu_gold.csv`, 50 docs): Changed 0 of 50 (0.00%). Dropped 0 of 50 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Clean slice (`ind-te-fw2`, 176 docs): 0 changed, 0 dropped (0.0%).
5. **Side effects:** none.

## Method

- An automatic scan ran first on every document (detectors for A1–A6, B1–B5, C2, C3, D1, D3, E3, F1, G1, H1, H2). Then
  every line of every document was read, with hidden characters shown and each line marked with its character offset.
  Every scan hit was confirmed or rejected by reading. For example, 115 C3 hits came down to 9; most were trailing
  bylines (C1).
- The D4 and D5 labels are a reading judgement. Rows with D4 or D5 have `read=full`.
