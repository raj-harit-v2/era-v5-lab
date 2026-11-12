# Medicine sheet: ind-bn-fw2 (sohamniyogi)

Pack: 500 documents, `HuggingFaceFW/fineweb-2 | ben_Beng`, 1.34 M characters. Labels: 314 clean, 148 fix, 38 drop.

## What this pack has and does not have

- **No** ZWSP, BOM, bidi marks, soft hyphens (A1), control characters (A2), U+FFFD (A4), HTML entities or tags (B1, B2),
  or ghost chat markers (B3) anywhere in the pack. I checked all 1.34 M characters, not only the documents I read.
- **The pack is fully NFC.** All 22,571 য় and 3,601 ড় are in decomposed form (base + nukta U+09BC), which is
  the NFC form, because U+09DC/U+09DD/U+09DF are composition exclusions. So A5 is not about NFC here. It is only
  about two-part vowels written in reverse order (Medicine 9).
- **ZWJ and ZWNJ count: 0 in the whole pack.** Real Bengali web text always has some, so they were stripped before
  release. The visible damage from this is G2 (Medicine 2).
- Emails are already masked by FineWeb-2 (`email@example.com`, `firstname.lastname@example.org`). Phone numbers are
  not masked. F1 occurs only 2 times, so it gets no medicine, but both rows are labelled with type and offset.

## About the harm tests below

**Official gold set: all 12 rules PASS, 0 of 238 gold documents changed or dropped.** The gold set is
`teams/02-data-b/gold/ind-bn-fw2_gold.csv` (#161): 238 documents of this pack that both readers (aditeyaaitronics and I)
labelled clean, with 0 disputed. A rule fails when it changes or drops more than 1 % of the gold set (at least 1
document is always allowed), so at most 2 of 238 here.

Each section below holds its rule as a ```` ```python ```` block with a function `medicine_<code>`. A rule takes the
text and returns the new text, or `True` to drop the document. `medicine_d4` takes `doc` because it reads the URL.
This is the format of the team harm tools, so they run the rules straight from this file:

```
# Data B tool (Indic; also checks ZWJ/ZWNJ counts and NFC): every rule except D4
python3 -I teams/02-data-b/tools/harm_test_indic.py --medicine medicine.md \
    --pack ind-bn-fw2.parquet --gold-dir teams/02-data-b/gold --rule C1        # C1, G2, A6, C5, F3, A3, C2, A5, C3, G1, D3
# Data A tool: D4 (it needs doc["url"]) and all rules in file order
python -I teams/01-data-a/tools/harm_test.py --pack ind-bn-fw2.parquet \
    --gold teams/02-data-b/gold/ind-bn-fw2_gold.csv --rules medicine.md --rule all
```

Results on 1 Nov: the Data B tool gives PASS for all 11 text rules, each 0 changed and 0 dropped, with joiners and
normal form "ok". D4 and the run of all rules in file order were run with the same section reading and Data A's
rules (a `doc` argument with `doc_id`, `text`, `url`, `lang_label`; limit max(1, floor(1 %))): 0 changed, 0 dropped,
PASS.

Because I am one of the two gold readers, the gold set is a subset of my own 314 clean rows. A second reader agreed
on each document, so this is a real test, but not a fully independent one. This matters most for M2 (see its warning).
The proxy result (the 314 rows I labelled clean) is kept in the table for comparison. For the character medicines (M2,
M4, M7, M9) I used the same detector to label, so 0 % on the proxy is true by construction.

| Medicine | Disease | Docs in pack | Action | Fires on pack (agrees with my labels) | Proxy changed / dropped (of 314) | **Gold changed / dropped (of 238)** | Result on gold |
|---|---|---|---|---|---|---|---|
| M1 | C1 boilerplate lines | 95 | fix | 44 (42) | 0 / 0 | 0 / 0 | PASS |
| M2 | G2 lost ZWJ in র‍্যা | 50 | fix | 50 (50) | 0 / 0 | 0 / 0 | PASS, see the warning |
| M3 | D4 MT spam sites | 36 | drop | 26 (26) | 0 / 0 | 0 / 0 | PASS |
| M4 | A6 look-alike danda U+09F7 | 17 | fix | 11 (11) | 0 / 0 | 0 / 0 | PASS |
| M5 | C5 keyword-stuffed lines | 11 | fix | 1 (1) | 0 / 0 | 0 / 0 | PASS, low recall |
| M6 | F3 porn / gambling promotion | 8 | drop | 5 (5) | 0 / 0 | 0 / 0 | PASS |
| M7 | A3 legacy-font leftovers | 7 | fix | 7 (7) | 0 / 0 | 0 / 0 | PASS |
| M8 | C2 repeated lines | 9 | fix | 8 (7) | 1 / 0 | 0 / 0 | PASS |
| M9 | A5 two-part vowel reversed | 7 | fix | 7 (7) | 0 / 0 | 0 / 0 | PASS |
| M10 | C3 truncated tail | 7 | fix | 5 (3) | 0 / 0 | 0 / 0 | PASS |
| M11 | G1 detached virama | 6 | fix | 2 (2) | 0 / 0 | 0 / 0 | PASS, low recall |
| M12 | D3 language mixing | 10 | keep (label only) | 0 (rule changes nothing) | 0 / 0 | 0 / 0 | PASS |

D3 (10 documents) gets a keep-only rule, Medicine 12. The mixing is natural, and DISEASES.md says to label it, not
judge it. Two more documents are only an Arabic Qur'an or hadith quotation; they are labelled clean with a note.
D5 (5) and B4 (5) are not more than five, so they get no medicine.

---

## Medicine 1: C1 boilerplate lines

1. **Disease:** C1, 95 documents. Examples: `6ffbbf510a981e67` "এ বিভাগের সর্বাধিক পঠিত" and "প্রিন্ট" at the end;
   `25ce3d7ca0f24773` "For all the latest Sports News Click Here"; `a04341dee190908a` (and all bn.topwar.ru pages)
   "সাবস্ক্রাইব করুন এবং সর্বশেষ খবর এবং দিনের সবচেয়ে গুরুত্বপূর্ণ ইভেন্টগুলির সাথে আপ টু ডেট থাকুন।";
   `ab306b59d8e205f6` "…'হোয়াটসঅ্যাপে ফলো করুন এই সময়কে।"
2. **Medicine:** delete a line only if the *whole line* matches a known furniture pattern (`_C1_LINE` in the code:
   "আরও পড়ুন: …", "শেয়ার করুন", "মন্তব্য করুন", "বিজ্ঞাপন", "প্রিন্ট সংস্করণ", "সর্বশেষ", "সর্বাধিক পঠিত",
   "View this post on Instagram", "Read More", "N total views, M views today", "[hupso]", a lone "#", …) **and** the
   line is among the first 3 or last 6 lines of the document.

   ```python
   import re

   _C1_LINE = re.compile(
       r"^\s*(?:"
       r"(?:আরও|আরো) (?:পড়ুন|পড়তে পারেন)\s*[:ঃ]?.{0,80}|শেয়ার করুন\s*[:ঃ]?|মন্তব্য করুন|বিজ্ঞাপন|"
       r"(?:প্রতিনিধি )?প্রিন্ট সংস্করণ|সর্বশেষ|সর্বাধিক পঠিত|শীর্ষ সংবাদ\s*[:ঃ]?|সম্পর্কিত (?:নিউজ|খবর)|"
       r"সাবস্ক্রাইব করুন এবং সর্বশেষ খবর.*|আমাদের নিউজ চ্যানেল|.*ইউটিউব চ্যানেলে সাবস্ক্রাইব করুন|"
       r".*হোয়াটসঅ্যাপে ফলো করুন.*|এ বিভাগের সর্বাধিক পঠিত|বিস্তারিত (?:ভিডিওতে দেখুন|আরোও জানতে ক্লিক করুন)\s*[:ঃ]?|"
       r"View this post on Instagram|Read (?:More|Entire Article).{0,3}|Continue Reading.{0,3}|Highlights|"
       r"Powered by Froala Editor|For all the latest .* Click Here|[\d,]+ total views, \d+ views today|"
       r"- More Stories On :|\[hupso\]|#"
       r")\s*$", re.I)


   def medicine_c1(text):
       """Delete whole furniture lines among the first 3 or last 6 lines."""
       lines = text.split("\n")
       n = len(lines)
       return "\n".join(l for k, l in enumerate(lines) if not ((k < 3 or k >= n - 6) and _C1_LINE.match(l)))
   ```
3. **Action:** fix (delete the line).
4. **Harm test:** official gold 0 / 238 (0 %), PASS. Proxy gold 0 changed, 0 dropped of 314 (0 %). PASS.
5. **Side effects:** a real headline that is exactly "সর্বশেষ" or "বিজ্ঞাপন" in the last 6 lines is deleted. The
   medicine does not catch furniture glued to prose ("শিরোনামOther", "সিলেট সদর Read More"), desk/initials lines
   ("জিএমএম/এএটি"), related-headline lists, or share requests written as a full sentence. Those need a list model. It
   fires on 44 of the 95 C1 documents.

## Medicine 2: G2 lost ZWJ in the loanword form র‍্যা

1. **Disease:** G2, 50 documents, 136 occurrences. The pack has 0 ZWJ, so every র‍্যা (RAB, rally, brand, track)
   became র্যা, which renders as ya-phala with reph (r-ya), not as ra with ya-phala. Examples: `3024066d06a72875` "র্যাব"
   at 105 (hex `E0 A6 B0 E0 A7 8D E0 A6 AF E0 A6 BE`); `cce9dc39b1581ffb` "ব্র্যান্ডিং" x40 from offset 25;
   `61e81566d086ef88` "র্যালী" at 36.
2. **Medicine:** `র্যা` at a word start or right after a virama becomes `র + ZWJ + ্যা`. The rule needs the following া. Without it, native words like দারিদ্র্য and বৈচিত্র্য would also match, and they
   must not change. Words like কার্যালয় do not match because the র follows া, not a word start or a virama.

   ```python
   import re

   _G2_RX = re.compile("(?:^|(?<=[^ঀ-৿])|(?<=্))র্যা", re.M)


   def medicine_g2(text):
       """র্যা at a word start or after a virama -> র + ZWJ + ্যা (the loanword form)."""
       return _G2_RX.sub("র‍্যা", text)
   ```
3. **Action:** fix.
4. **Harm test:** official gold 0 / 238 (0 %), PASS. Proxy 0 / 314 (circular, see above). **Warning:** a gold set built from the same FineWeb-2 dump
   will have the same ZWJ loss. In this pack, 10 % of documents contain the pattern. A medicine that *correctly* changes
   10 % of the gold set fails the 1 % rule as written. I recommend restoring ZWJ/ZWNJ upstream (re-extracting from the
   source HTML) and not patching documents. If it must be a medicine, the gold set must be checked for the same loss
   first. The official gold set confirms this: it has 0 ZWJ too. Its 0 % only shows that no gold document has the
   loanword form M2 targets (র্যা at a word start or after a virama). 55 gold documents have র্যা inside native words
   such as কার্যালয়, and M2 correctly leaves them alone. Every document with the loanword form was labelled G2, so it
   could not be in the gold set.
5. **Side effects:** a transliterated name that really is written র্যা without ZWJ (rare) gets a ZWJ. The medicine does
   not fix lost ZWNJ, which has no reliable surface pattern.

## Medicine 3: D4 machine-translated spam sites (drop)

1. **Disease:** D4, 36 documents. Examples: `6a18f8751bb83059` bn.horoskopdnevni.com "বৃহস্পতি বিপরীতমুখীটি যখন
   অষ্টাদশীতে"; `3092e9bd6566d7fc` bn.utaheconomicandenergysummit.com "মানুষ এটি লাঠি" (English "stick it");
   `a04341dee190908a` and 8 other bn.topwar.ru pages (machine-translated Russian news).
2. **Medicine:** drop the document if the URL host starts with `bn.` and is not in a short allow-list of real Bengali
   editions (`bn.mtnews24.com`, `bn.globalvoices.org`, `bn.wikipedia.org`, `bn.m.wikipedia.org`,
   `bn.ekusherbangladesh.com.bd`, …). These `bn.` subdomains of foreign sites are auto-translation farms.

   ```python
   from urllib.parse import urlparse

   _BN_OK = {"bn.mtnews24.com", "bn.globalvoices.org", "bn.m.wikipedia.org", "bn.wikipedia.org",
             "bn.ekusherbangladesh.com.bd", "bn.jwtrubber.com", "bn.bettingonlinebd.net"}


   def medicine_d4(doc):
       """Drop (True) a document whose URL host is a bn.* subdomain of a non-Bengali site."""
       host = urlparse(doc.get("url") or "").netloc.lower()
       return host.startswith("bn.") and host not in _BN_OK
   ```
3. **Action:** drop.
4. **Harm test:** official gold 0 / 238 (0 %), PASS. Proxy 0 / 314. PASS.
5. **Side effects:** a new real Bengali edition on a `bn.` host is dropped until it is added to the allow-list. It does
   not catch MT on normal hosts (enigmasoftware.com, actualidadgadget.com, drcockatiel.com). It fires on 26 of 36.

## Medicine 4: A6 look-alike danda U+09F7

1. **Disease:** A6, 17 documents: 13 with U+09F7, 3 with Assamese ৰ U+09F0 (one also has U+09F7), 1 with
   U+2019 inside words ("ঘনি’ষ্ঠ", clickbait filter evasion), 1 with a Devanagari headline. U+09F7 BENGALI CURRENCY NUMERATOR FOUR
   looks exactly like the danda but is a different code point, so the tokenizer splits sentences wrong. Examples:
   `fb97c8e54faa6ea5` "গ্রামে৷" at 176 (hex `E0 A7 B7`); `740b87d9773606f0` x27; `8d8e16b8a976243b` "উত্তর।৷" at 130.
2. **Medicine:** U+09F7 right after a Bengali character or a space becomes the danda U+0964.

   ```python
   import re


   def medicine_a6(text):
       """U+09F7 after a Bengali character or a space -> danda U+0964."""
       return re.sub("(?<=[ঀ-৿\\s])৷", "।", text)
   ```
3. **Action:** fix.
4. **Harm test:** official gold 0 / 238 (0 %), PASS. Proxy 0 / 314. PASS.
5. **Side effects:** a real currency numerator in old-style money notation (I found none in the pack) becomes a danda.
   U+09F7 after a digit, Latin letter or । ("BDT৷", "উত্তর।৷") is not changed. That is why it fires on 11 of
   the 13 U+09F7 documents. Assamese ৰ inside Bengali words ("গ্ৰন্থ", "চাইৰে") is
   not fixed: ৰ→র is safe in "গ্ৰন্থ" but wrong in "চাইৰে" (a typo for চাইবে), so I leave those 3 to a human.

## Medicine 5: C5 keyword-stuffed lines

1. **Disease:** C5, 11 documents. Examples: `01d455bebba21ef1` "Tag: সূরা লাহাবের শানে নুজুল, সুরা লাহাব এর শানে নুযুল,
   …"; `e4aa2126d8505b14` a keyword list at the end; `a315585629ebfd19` a name-meaning SEO page.
2. **Medicine:** delete a line with 6 or more comma pieces, an average of 6 words or fewer per piece, and one two-word
   phrase in at least half of the pieces (`_c5_stuffed` in the code).

   ```python
   import re
   from collections import Counter


   def _c5_stuffed(line):
       parts = [p.strip() for p in re.split(r"[,،]", line) if p.strip()]
       if len(parts) < 6 or sum(len(p.split()) for p in parts) > 6 * len(parts):
           return False
       c = Counter(b for p in parts for b in {" ".join(x) for x in zip(p.split(), p.split()[1:])})
       return bool(c) and c.most_common(1)[0][1] >= 0.5 * len(parts)


   def medicine_c5(text):
       """Delete lines of >= 6 short comma pieces where one two-word phrase is in >= half of them."""
       return "\n".join(l for l in text.split("\n") if not _c5_stuffed(l))
   ```
3. **Action:** fix (delete the line).
4. **Harm test:** official gold 0 / 238 (0 %), PASS. Proxy 0 / 314. PASS. **The 5.10 % is not this rule:** an earlier
   draft (one shared *word* in 60 % of the pieces) changed 16 / 314 = 5.10 % of the proxy and failed. It hit lists of
   names ("মোঃ …, মোঃ …") and enumerations, so I replaced it before submission with the rule above (one shared *two-word
   phrase* in half of the pieces), which changes 0 of the 238 gold documents.
5. **Side effects:** recall is low (1 of 11). Whole SEO pages and spec tables are not caught. Use M3 or a classifier
   for those.

## Medicine 6: F3 porn and gambling promotion (drop)

1. **Disease:** F3, 8 documents. Examples: `43804ba72410d8ff` and `f043584d6c27e3d7` porn-tube pages;
   `80d6bada82e5ff0b` bn.bettingonlinebd.net 888starz review; `95261ddc152835cc` betting promo with "Mostbet BD"
   injected into the middle of the word অনলাইন.
2. **Medicine:** drop if the text has at least 4 matches of
   `পর্ন|চোদা|ক্যাসিনো|বেটিং|বাজি ধর|জুয়া খেল|casino|betting|porn|xxx|sex video` **and** at least 1 match per 600
   characters.

   ```python
   import re

   _F3_RX = re.compile(r"পর্ন|চোদা|ক্যাসিনো|বেটিং|বাজি ধর|জুয়া খেল|casino|betting|porn|xxx|sex video", re.I)


   def medicine_f3(text):
       """Drop (True) when there are >= 4 hits and >= 1 hit per 600 characters."""
       n = len(_F3_RX.findall(text))
       return n >= 4 and n * 600 >= len(text)
   ```
3. **Action:** drop.
4. **Harm test:** official gold 0 / 238 (0 %), PASS. Proxy 0 / 314. PASS. The density rule keeps news about casino raids: `ce8a91b51a89e51a` has 2 hits in
   2,641 chars and is kept.
5. **Side effects:** a long news feature about the casino crackdown with many mentions could be dropped. It does not
   catch spam appended in English to a clean article (`a041c47c2735d3f0`, cialis) or sexual-health product spam.
   Those are caught by M3 or not at all.

## Medicine 7: A3 legacy-font (Bijoy/ANSI) leftovers

1. **Disease:** A3, 7 documents. Text typed in the old Bijoy font and badly converted to Unicode. Examples:
   `874ac01ed8db4951` "দ্রæত" at 571 (æ for ু, hex `C3 A6`); `0cc55d56de34d944` "স¦াক্ষর" at 457 (¦ for ্ব, hex
   `C2 A6`); `4daaf2d1c7aea69f` "বøুপ" at 1232 (ø for ্ল); `71bb93238817a1c8` "সহÑসভাপতি" (Ñ for a dash).
2. **Medicine:** only when the character touches a Bengali letter: æ→ু, ø→্ল, ¦→্ব, Ñ→–, Í→-.

   ```python
   import re

   _A3_MAP = {"æ": "ু", "ø": "্ল", "¦": "্ব", "Ñ": "–", "Í": "-"}


   def medicine_a3(text):
       """Bijoy leftovers next to a Bengali letter -> the intended character."""
       return re.sub("(?<=[ঀ-৿])[æø¦ÑÍ]|[æø¦ÑÍ](?=[ঀ-৿])", lambda m: _A3_MAP[m.group()], text)
   ```
3. **Action:** fix.
4. **Harm test:** official gold 0 / 238 (0 %), PASS. Proxy 0 / 314. PASS.
5. **Side effects:** a real Latin-1 letter right next to Bengali text (a Danish or Spanish name with no space) would be
   changed. None in the pack. Other Bijoy damage (reph in the wrong place "র্ধষণ", "রির্পোটার") is not fixed.

## Medicine 8: C2 repeated lines

1. **Disease:** C2, 9 documents. Examples: `0ca0ac43cc9f2526` "Department of Textile Engineering" x3;
   `7bbe5a23532255c3` "— ANI (@ANI) July 8, 2023" x3; `bd59fdf51e29e37b` a question heading x5.
2. **Medicine:** keep the first two copies of a line longer than 8 characters and delete the third and later copies.

   ```python
   from collections import Counter


   def medicine_c2(text):
       """Keep the first two copies of a line longer than 8 characters; delete later copies."""
       seen, out = Counter(), []
       for l in text.split("\n"):
           k = l.strip()
           seen[k] += 1
           if len(k) > 8 and seen[k] > 2:
               continue
           out.append(l)
       return "\n".join(out)
   ```
3. **Action:** fix.
4. **Harm test:** official gold 0 / 238 (0 %), PASS. Proxy 1 changed, 0 dropped of 314 (0.32 %). PASS.
5. **Side effects:** the one proxy change is `fb25628d14ed717a`, a poem whose refrain "পিতার আশীর্বাদ।" repeats 3
   times. The medicine cuts a real refrain. Song lyrics and poems are at risk.

## Medicine 9: A5 two-part vowel written in reverse order

1. **Disease:** A5, 7 documents. The vowel ো must be stored as ে + া (or U+09CB). These documents store া + ে, which
   NFC does not fix, so the same word exists in two byte forms. Examples: `1c748f4d41f5cb07` "ভালাে" x16 from 594 (hex
   `E0 A6 BE E0 A7 87`); `4c3a514616f31a33` "চৈাধুরী" (ৈ + া for ৌ) at 57; `bfb033a731f20dc9` "বিক্ষােভ" at 593.
2. **Medicine:** া + ে becomes ো, and ৈ + া becomes ৌ.

   ```python
   def medicine_a5(text):
       """া + ে -> ো, ৈ + া -> ৌ (two-part vowels stored in reverse order)."""
       return text.replace("াে", "ো").replace("ৈা", "ৌ")
   ```
3. **Action:** fix.
4. **Harm test:** official gold 0 / 238 (0 %), PASS. Proxy 0 / 314. PASS.
5. **Side effects:** none found. The sequence া + ে has no correct use in Bengali.

## Medicine 10: C3 truncated tail

1. **Disease:** C3, 7 documents. Examples: `a03da238fe5d7dcd` ends "…সহযোগী সংগঠনের সভা"; `39feeae74731a5f8` ends
   "…অপহরন করে নিয়ে যায়" with no danda; `740b87d9773606f0` ends "…মিল রয়েছে, কখনও কখনও".
2. **Medicine:** if the text ends in a Bengali letter, the last line is longer than 60 characters, and the last 40
   characters contain no `: ঃ / - – —` (credit lines such as "সূত্র: বিবিসি" or "শিশির/এনাম/আকাশ"), cut the text after the
   last `। ? ! ৷`.

   ```python
   import re


   def medicine_c3(text):
       """Cut a broken last sentence back to the last । ? ! ৷ (credit lines are left alone)."""
       s = text.rstrip()
       if not s:
           return text
       last = s.split("\n")[-1]
       if not re.match("[ঀ-৿]", s[-1]) or len(last) <= 60 or re.search(r"[:ঃ/\-–—]", last[-40:]):
           return text
       cut = max(s.rfind(c) for c in "।?!৷")
       return s[:cut + 1] if cut > 0 else text
   ```
3. **Action:** fix (trim the broken sentence; keep the document).
4. **Harm test:** official gold 0 / 238 (0 %), PASS. Proxy 0 / 314. PASS.
5. **Side effects:** a last sentence that is complete but has no danda is cut (all 3 labelled cases it fires on are real
   cuts, but the same shape could be complete). It misses "[…]" endings and lists that stop without "প্রমুখ". It also trims keyword lists at the end (`7b65bbecd0338588`, `e4aa2126d8505b14`),
   which is a useful side effect.

## Medicine 11: G1 detached virama

1. **Disease:** G1, 6 documents. Examples: `bb4a327ce2e54290` "সম ্প্রদায়" at 5977 (hex `20 E0 A7 8D`);
   `ce8a91b51a89e51a` "মু্িক্তযোদ্ধা" at 30; `f31201dc061fecbc` "\nিশক্ষা" at 265 (pre-base ি placed before the
   consonant, Bijoy conversion).
2. **Medicine:** remove a space between a consonant and a following virama + consonant.

   ```python
   import re


   def medicine_g1(text):
       """Remove a space between a consonant and a following virama + consonant."""
       return re.sub("(?<=[ক-হ]) (?=্[ক-হ])", "", text)
   ```
3. **Action:** fix.
4. **Harm test:** official gold 0 / 238 (0 %), PASS. Proxy 0 / 314. PASS.
5. **Side effects:** low recall (2 of 6). Virama + vowel ("্ি") and ি moved before its consonant need reordering, not
   joining, and a wrong join makes it worse ("ধর্মের ্র" would become "ধর্মের্র"), so those cases stay for a human.

## Medicine 12: D3 language mixing (keep, label only)

1. **Disease:** D3, 10 documents. Examples: `61dc0261aeb4ced0` English glosses in brackets "(FIFA World Cup 2022)" at
   47; `0ca0ac43cc9f2526` English course and batch lines "(Batch-40)" at 6655; `b9c8f89ff096bcd9` an Arabic Qur'an
   quotation (324 characters) at 119.
2. **Medicine:** none. The mixing is natural Bengali usage (English terms and names, quoted Arabic scripture), and
   DISEASES.md says to label D3, not to judge it. Removing the English or Arabic would damage good text. The rule
   keeps every document as it is, so that the harm test can run on it like every other rule.

   ```python
   def medicine_d3(text):
       """Keep the document unchanged: D3 is labelled, not cleaned."""
       return text
   ```
3. **Action:** keep (no fix, no drop).
4. **Harm test:** official gold 0 / 238 (0 %), PASS. The rule changes no document by construction.
5. **Side effects:** none from the rule. The D3 documents stay in the data with their mixed-language spans. If a later
   stage wants Bengali-only text, it should use the D3 labels and the offsets in `labels.csv`, not a text rule.
