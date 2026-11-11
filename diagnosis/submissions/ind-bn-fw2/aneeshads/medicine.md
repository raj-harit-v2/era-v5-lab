# Medicine sheet: ind-bn-fw2 (aneeshads)

Counts are from my label sheet `labels.csv` (4 November): 100 documents read in full (my assigned IDs), 83 `clean`
and 17 `fix`, 4 codes found. A count is the number of evidence items, followed by the number of documents. A disease
gets a section when it is found more than five times: C1 (14 times, in 14 documents) and D3 (7 times, in 7
documents). F1 (1 time, 1 document) and C2 (1 time, 1 document) are below the threshold.

**Harm test.** The gold set is `teams/02-data-b/gold/ind-bn-fw2_gold.csv` on `main` (rebuilt 2 November): 244
documents of this pack that two readers (aditeyaaitronics and sohamniyogi) kept. The tool is Data B's, which runs
the code in this file as it is:

```
python3 teams/02-data-b/tools/harm_test_indic.py --medicine medicine.md \
    --pack ind-bn-fw2.parquet --gold-dir teams/02-data-b/gold
```

A rule may change or drop at most 1% of the gold set or 1 document, whichever is more: on 244 documents that is
**2 documents**. No changed document may lose or gain a ZWJ/ZWNJ or leave NFC (the tool's two audits). Part 4 of
each medicine is the tool's own text (run of 4 November, `--rule all`). All rules run in order change 2 of 244
(0.82%, **PASS**).

**All 100 of my documents are in that gold set**, among them the 17 that I marked `fix`. So a medicine that cures
more than 2 of my sick documents fails the harm test by construction: the gold readers kept these documents. This
decides the sheet: C1 gets a narrow medicine that passes, and the full C1 rule is reported as a candidate that fails.

| # | Code | Count (documents) | Action | Gold changed | Gold dropped | Gold share | Result | Labelled documents treated | fw2 pack changed (500) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | C1 | 14 (14) | fix | 2 | 0 | 0.82% | **pass** | 2 of 14 | 2 |
| 1a | C1 (candidate, full rule) | | fix | 46 ¹ | 0 | 15.97% ¹ | **fail** | 11 of 14 | 95 |
| 2 | D3 | 7 (7) | none (candidate: fix) | – | – | – | no rule in code | 1 of 7 | 41 |

¹ From my run of 3 November on the gold set of that day (238 fw2 documents and 50 sangraha documents, 288 in all).

## Medicine 1

1. **Disease:** C1, boilerplate of Bangladeshi news sites: photo and agency credits, source lines, desk slugs and
   datelines. Count 14, in 14 documents.
   - `656e1a989097ab40`, offset 0: `সংগৃহীত ছবি।`, a photo credit on its own line ("collected photo").
   - `642e2d510bf80d87`, offset 565: `—ইউএনবি`, the agency credit (UNB) after a dash at the end of the story.
   - `16b0ef19cedf0abb`, offset 1059: `বিডি প্রতিদিন/এমআই`, the desk slug of Bangladesh Pratidin (paper/editor's
     initials) at the end of the story.
2. **Medicine:** remove a line that is only a photo credit (`সংগৃহীত ছবি`, `ছবি: সংগৃহীত`, `ফাইল ছবি`), and remove an
   agency credit after a dash at the end of a line (`—ইউএনবি`, `—বাসস`, `—এএফপি`, `—রয়টার্স`, `—বিবিসি`).
   ```python
   import re

   _PHOTO_CREDIT = re.compile(r"^[ \t]*(?:সংগৃহীত ছবি|ছবি[ \t]*[:ঃ][ \t]*সংগৃহীত|ফাইল ছবি)[।.]?[ \t]*(?:\n|$)", re.M)
   _AGENCY_AFTER_DASH = re.compile(r"[ \t]*[—–][ \t]*(?:ইউএনবি|বাসস|এএফপি|রয়টার্স|বিবিসি)[ \t]*$", re.M)


   def medicine_c1(text):
       text = _PHOTO_CREDIT.sub("", text)            # a photo credit on its own line: সংগৃহীত ছবি।
       return _AGENCY_AFTER_DASH.sub("", text)       # an agency credit after a dash at the end of a line: —ইউএনবি
   ```

   The candidate I tested is the full rule, which also removes the other forms of C1 in my labels: a source line
   (`সূত্র: বিবিসি`), a desk slug at the end of a paragraph (`বিডি প্রতিদিন/এমআই`, `ভোরের আকাশ/নি`), and a dateline
   at the start (`নিজস্ব প্রতিবেদক, নাটোর :`). Its name starts with `_`, so the harm-test tool does not run it as the
   C1 rule.
   ```python
   import re

   _SOURCE_LINE = re.compile(r"^[ \t]*সূত্র[ \t]*[:ঃ][^\n]{0,80}(?:\n|$)", re.M)
   _DESK_SLUG = re.compile(r"(?:^|(?<=[।.!?]))[ \t]*[^\s/।]+(?:[ \t][^\s/।]+){0,2}"
                           r"(?:[ \t]*/[ \t]*[^\s/।]+(?:[ \t][^\s/।]+){0,2})+[ \t]*$", re.M)
   _DATELINE = re.compile(r"\A[ \t]*(?:নিজস্ব প্রতিবেদক|অনলাইন ডেস্ক|[^\n,।]{2,30}প্রতিনিধি)[^\n:ঃ।]{0,30}[:ঃ।]+[ \t]*")


   def _candidate_c1(text):
       text = medicine_c1(text)                      # the passing part first
       text = _SOURCE_LINE.sub("", text)             # সূত্র: বিবিসি
       text = _DESK_SLUG.sub("", text)               # বিডি প্রতিদিন/এমআই at the end of a paragraph
       return _DATELINE.sub("", text)                # নিজস্ব প্রতিবেদক, নাটোর : at the start
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 244 documents (ind-bn-fw2 244), medicine.md sha256 16279cf5d3db; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 2 of 244 (0.82%). Dropped 0 of 244 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   The two changed gold documents are my own `642e2d510bf80d87` (`—ইউএনবি`) and `656e1a989097ab40` (`সংগৃহীত ছবি।`),
   the two C1 documents that this medicine treats.

   The full candidate changed 46 of the 288 gold documents of 3 November and dropped 0: 15.97%. **Fail.** It treats
   11 of my 14 C1 documents. 19 of the 46 are my own documents, and 8 of those I marked `clean` myself although they
   carry the same boilerplate: for example `চাঁদপুর প্রতিনিধি:` at offset 0 of `44b419b70b6d9c1a` and
   `বাংলাপোস্ট২৪/নাছির` at offset 523 of `241485aee4d1a252`. So my labels do not treat datelines and slugs in one way
   either. fw2 pack: 95 documents changed.
5. **Side effects:**
   - Of `medicine_c1`: a line `ফাইল ছবি` that is a real caption, or a sentence that ends with a quoted agency name
     after a dash, would be removed. It leaves 12 of my 14 C1 documents as they are.
   - Of the candidate:
     - The dateline gives the place of the story (`নাটোর`, `চাঁদপুর`); removing it loses a fact that the first sentence
       often does not repeat.
     - The slug pattern also removes a short last line with a slash that is content, such as a date `১২/০৩` or a
       ratio, when it stands alone after a full stop.
     - It still misses a byline that is only a name (`বিল্লাল হোসেন প্রান্তঃ` in `04e967f91a68f9d2`), a source in the
       middle of a line, and a desk name without a slash (`অনলাইন ডেস্ক।।` after the first line in `4b0b3423594d7d68`).
   - To cure the rest of C1, the gold readers and I need to agree first whether credits, slugs and datelines are
     boilerplate. Until then the gold set treats them as clean text.

## Medicine 2

1. **Disease:** D3, mixed language. Count 7, in 7 documents. 5 of the 7 are `clean` documents, because DISEASES.md
   says to label D3 but not judge it.
   - `39a83529d646f458`, offset 352: `left handed`, an English gloss in brackets after the Bengali `বাঁহাতি`; the same
     page has `অমিতাভ বচ্চন (Amitabh Bachchan)`.
   - `448d894cd2d20ced`, offset 1190: `জি-মেইল সাইন-ইন`, English words written in Bengali letters.
   - `0d0cf7fcbba3fef6`, offset 659: `https://toffeelive.com/`, an English URL in Bengali prose.
2. **Medicine:** none. The candidate I tested removes an English gloss in brackets after a Bengali word. Its name
   starts with `_`, so the harm-test tool does not run it as a D3 rule.
   ```python
   import re

   _GLOSS = re.compile(r"\s?\(\s*[A-Za-z][A-Za-z0-9 .,&'’-]*\)")


   def _candidate_d3(text):
       return _GLOSS.sub("", text)                   # রোহিত শর্মা (Rohit Sharma) -> রোহিত শর্মা
   ```
3. **Action:** keep the documents as they are. The candidate's action would be to fix the text.
4. **Harm test:** gold set of 244 documents (ind-bn-fw2 244), medicine.md sha256 16279cf5d3db: the tool reports "D3
   has no rule in code, so nothing to test". Nothing changes: 0 changed, 0 dropped of 244.
5. **Side effects:**
   - The candidate would remove good text: English names and terms that help a model link the two scripts.
   - It misses most D3: English words in Bengali letters (`ওয়ারড্রোব` at offset 643 of `3c0e338578d39683`,
     `জি-মেইল সাইন-ইন`, `ষ্টাফ` at offset 1082 of `65d53111eecdb10d`) and URLs; these are natural Bengali and need no
     medicine.

## Codes below the threshold

| Code | Disease | Count (documents) | Example |
|---|---|---|---|
| F1 | personal data | 1 (1) | `138b777477338cb0`, offset 633: an address (the value is not given here) |
| C2 | repeated lines | 1 (1) | `529567589848cc21`, offset 2980: `শহীদ মিনার` |

## A6 in this pack (not in my labels)

A6, the Assamese RA U+09F0 `ৰ` in place of the Bengali RA U+09B0 `র`, is not in my labels for this pack. The A6
medicine of my ind-bn-sangraha-v sheet (replace `ৰ` with `র` only when a document has more than 6 `ৰ` and fewer `ৰ`
than `র`, the TSAI decision of 4 November) was checked on this pack on 4 November:

- **Gold:** on the 244 gold documents of ind-bn-fw2 it changes 0 and drops 0 (0.00%, limit 2). ZWJ/ZWNJ and
  normal-form audits pass. **PASS**
- **Pack (500 documents):** 3 documents have a `ৰ`, one each (`3d1bc6eb238cbbb1`, `bd59fdf51e29e37b`,
  `7806d286fa99b29e`), among 548 to 2,630 `র`. All three have 6 or fewer `ৰ`, so the medicine changes none of them:
  0% of the `ৰ` changed, 100% (3 of 3) unchanged.

So in this pack the filtered A6 is safe but has nothing to treat. It is not added as a medicine of this sheet.
