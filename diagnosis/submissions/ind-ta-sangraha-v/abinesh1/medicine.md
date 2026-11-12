# Medicine sheet: ind-ta-sangraha-v (abinesh1)

Pack: 500 Tamil documents, all labelled (296 fix, 153 clean, 51 drop). One section per disease found more than five times.

The rules run in the order of this sheet. C1 runs first, so the other medicines do not spend changes on lines that C1 removes.

**Gold harm test: PASS.** Gold set `teams/02-data-b/gold/ind-ta-sangraha-v_gold.csv` on main: 41 documents, so the limit
is max(1, 1% of 41) = 1 document. All 41 are also labelled `clean` in my labels.csv. Data A's `harm_test.py` (#140) ran
each of the 8 rules alone and all 8 in file order: 0 gold documents changed and 0 dropped
(code sha256 `6b248eec3cff4fd958d62873325bcb594be3e9ccc41ef46289561720a0873f56`).

```
python -I teams/01-data-a/tools/harm_test.py --pack ind-ta-sangraha-v.parquet --gold teams/02-data-b/gold/ind-ta-sangraha-v_gold.csv --rules diagnosis/submissions/ind-ta-sangraha-v/abinesh1/medicine.md --rule all
```

The table also gives a pack check: the same rules on all 500 pack documents, counted against my labels.

| Medicine | Action | Pack docs changed | Labelled docs treated | Pack docs labelled `clean` that it changes | Gold changed | Gold dropped |
|---|---|---|---|---|---|---|
| C1 boilerplate lines | fix | 50 | 50 of 163 | 0 of 153 | 0 | 0 |
| A6 ஃ for a lost colon | fix | 135 | 125 of 136 | 0 of 153 | 0 | 0 |
| G1 legacy-font glyphs | fix | 25 | 24 of 35 | 0 of 153 | 0 | 0 |
| G4 split decimals and URLs | fix | 65 | 43 of 44 | 0 of 153 | 0 | 0 |
| B4 literal `\n` | fix | 22 | 22 of 23 | 0 of 153 | 0 | 0 |
| C3 unfinished last sentence | fix | 22 | 16 of 24 | 0 of 153 | 0 | 0 |
| C5 headline lists | drop | 3 dropped | 3 of 23 | 0 of 153 | 0 | 0 |
| C2 long repeated paragraph | fix | 3 | 3 of 8 | 0 of 153 | 0 | 0 |
| G3 text lost | flag only | 0 | – | – | 0 | 0 |
| C4 two documents joined | flag only | 0 | – | – | 0 | 0 |
| D4 bad machine translation | flag only | 0 | – | – | 0 | 0 |
| D3 mixed language | keep | 0 | – | – | 0 | 0 |

## Medicine 1: C1 boilerplate

1. **Disease:** C1, 163 documents (157 fix, 6 drop). Examples:
   - `b696ac9e380537d5`: News18 footer line `நியூஸ்18 தமிழ்நாடு தொலைக்காட்சியை, ARASU CABLE - 46, …`
   - `28e55a22748757af`: last line `Sign up to receive our newsletter in your inbox every day!`
   - `086f4273ad802fea`: oneindia block `Don't Miss!` followed by ticker lines such as `- Finance ஈஷா அம்பானி-க்கு புதிய பதவி. .`
2. **Medicine:** delete whole lines that match known site templates: the newsletter line, the `Don't Miss!` block and its
   ticker lines (`- <section> …` or `- <n> hrs ago …`), the two News18 footer lines, and read-also lines
   (`Also Read:`, `Also see:`, `இதையும் படிங்க`, `இதையும் பாருங்க`). A line is removed only when it starts with a template;
   text inside a line is never touched.
   ```python
   import re

   _TICKER = "Finance|Travel|Education|Technology|News|Automobiles|Movies|Lifestyle|Sports"  # oneindia "Don't Miss!" block
   _C1_LINE = re.compile(r"(?m)^[ \t]*(?:Sign up to receive our newsletter in your inbox every day!|Don't Miss!"
                         rf"|- (?:\d+ (?:mins?|hrs?) ago|{_TICKER}) .*"
                         r"|உலகம் முதல் உள்ளூர் வரை இன்றைய முக்கிய செய்திகள்.*|நியூஸ்18 தமிழ்நாடு தொலைக்காட்சியை.*"
                         r"|(?:Also Read|Also see)\s*:.*|இதையும் (?:படிங்க|பாருங்க).*)[ \t]*(?:\n|$)")

   def medicine_c1(text):
       return _C1_LINE.sub("", text)
   ```
3. **Action:** fix (remove the lines).
4. **Harm test:** `harm_test.py --rule C1` on this pack's gold set, `teams/02-data-b/gold/ind-ta-sangraha-v_gold.csv` on
   main (41 documents, limit 1): 0 documents changed, 0 dropped, 0.00%, result PASS. Pack check: changes 50 documents, all
   labelled C1; none of the 153 `clean` documents.
5. **Side effects:**
   - The rule treats only 50 of the 163 C1 documents. The other 113 have site-specific boilerplate (breadcrumbs, related
     headlines mixed into the article, captions, share widgets) that a general rule cannot remove safely. They stay as they are.
   - An article whose own sentence starts with `- Sports ` or `Also Read:` would lose that line. No such case in the pack.

## Medicine 2: A6 ஃ (aytham) for a lost colon

1. **Disease:** A6, 136 documents (120 fix, 16 drop). A legacy font maps the colon to ஃ. Examples:
   - `ba0521a76a80c6ba`: `அவரது அறிக்கைஃ` at the end of a line (should be `அறிக்கை:`)
   - `b314ba477f78d672`: dateline `பொள்ளாச்சிஃ பொள்ளாச்சி மற்றும்`
   - `2bd051878060e7e3`: dateline `சென்னைஃ சென்னை ஐஐடி`
2. **Medicine:** ஃ that is not followed by a consonant becomes a colon. A real aytham always comes before a consonant
   (`அஃது`, `எஃகு`, `ஃப` in loan words), so it stays.
   ```python
   import re

   def medicine_a6(text):
       return re.sub("ஃ(?![க-ஹ])", ":", text)  # aytham before a space or line end is a lost colon
   ```
3. **Action:** fix.
4. **Harm test:** gold set: 0 of 41 changed, 0 dropped, PASS. Pack check: changes 135 documents, none labelled `clean`. 8 of the 10 changed documents
   without an A6 label have a real lost colon inside a headline line that was labelled C1 only.
5. **Side effects:**
   - **Sanskrit visarga in Tamil script** is also written ஃ and is turned into a colon: `ஹரஃ` (`42686daa22d0e057`),
     `பக்திதஃ` (`2172fbfc8ec32092`), `ப்ரபஞ்சஃ` (`b2f3b49721ef4f89`). Devotional texts with Sanskrit verses are most at risk in the gold set.
   - A letter list in a grammar text: `ஙஞணநமனவயலளஃ என்னும்` (`bbbf6b441072c407`) loses its real aytham.
   - Missed: ஃ glued to the next word (`திருப்பூர்ஃதிருப்பூர்`, `85ded505f55ead28`) looks like a real aytham, and Tamil
     numerals that OCR read as letters need a reader. 11 of the 136 documents are missed.

## Medicine 3: G1 legacy-font glyphs

1. **Disease:** G1, 35 documents (30 fix, 5 drop). Text typed in a legacy font and converted glyph by glyph. Examples:
   - `c7e4a7ea75c2044e`: `கல்லுாரி` (ு+ா for ூ; should be `கல்லூரி`)
   - `8b6b217ae67c4717`: `வருகின்றனா்` (ா் for ர்; should be `வருகின்றனர்`)
   - `61957b6260e7f6a8`: `ெதருவில்` (vowel sign typed before the consonant; should be `தெருவில்`)
2. **Medicine:** three rules. `ா்` becomes `ர்`; `ுா` becomes `ூ`; a sign ெ, ே or ை that does not follow a consonant moves
   after the next consonant, and with a following ா it becomes ொ or ோ. Each of these sequences is invalid in Unicode Tamil.
   ```python
   import re

   _LEGACY = {("ெ", "ா"): "ொ", ("ே", "ா"): "ோ"}  # sign typed before the consonant, then ா: one two-part vowel sign

   def medicine_g1(text):
       text = text.replace("ா்", "ர்").replace("ுா", "ூ")
       return re.sub("(?<![க-ஹ])([ெேை])([க-ஹ])(ா?)",
                     lambda m: m[2] + _LEGACY.get((m[1], m[3]), m[1] + m[3]), text)
   ```
3. **Action:** fix.
4. **Harm test:** gold set: 0 of 41 changed, 0 dropped, PASS. Pack check: changes 25 documents, none labelled `clean`. The one changed document
   without a G1 label has `இளைஞா்கள்` in a headline line labelled C1.
5. **Side effects:**
   - After an OCR error the sign can move to the wrong letter: `தஸ்ைஸை` becomes `தஸ்ஸைை` (`504b1a8292fbe9d2`, already a drop).
   - Missed: ௗ typed for ள (`வௌ்ளி`), ஒ+ள for ஔ, and a consonant lost before its sign (`ிஜய்`). 11 of the 35 documents are missed.

## Medicine 4: G4 split decimals, dates and URLs

1. **Disease:** G4, 44 documents (43 fix, 1 drop). A space was added after every full stop, which splits numbers and
   web addresses. Examples:
   - `89879512ea611689`: film title `படம் 2. 0` (should be `2.0`)
   - `78a681d105a4a147`: `ரூபாய் 9. 46 லட்சத்தில்` (should be `9.46`)
   - `2bd051878060e7e3`: `https://study. iitm. ac. in/es/`
2. **Medicine:** remove the space in `<digit>. <digit>`, and in a run of Latin words joined by `. ` that ends in a
   common domain (`com`, `in`, `org`, `net`, `lk`, `info`). Tamil initials (`எம். எல். ஏ.`) are not touched.
   ```python
   import re

   def medicine_g4(text):
       text = re.sub(r"(?<=\d)\. (?=\d)", ".", text)  # 28. 17 -> 28.17
       return re.sub(r"\b[A-Za-z0-9-]+(?:\. [A-Za-z0-9-]+)*\. (?:com|in|org|net|lk|info)\b",
                     lambda m: m[0].replace(". ", "."), text)
   ```
3. **Action:** fix.
4. **Harm test:** gold set: 0 of 41 changed, 0 dropped, PASS. Pack check: changes 65 documents, none labelled `clean`. The 22 changed documents
   without a G4 label are real splits inside lines labelled C1 (`News18Tamil. com` in the footer, `ரூ. 1. 03 லட்சத்தில்`
   in the ticker).
5. **Side effects:**
   - A sentence that ends in a number, followed by one that starts with a number (`… 2019. 20 பேர் …`), would be
     joined into `2019.20`. No such case in the pack, but it can happen in the gold set.
   - An English sentence that ends in a word and is followed by `in` (`… done. in …`) would be joined. No such case in the pack.
   - Missed: the other G4 form, a superscript flattened by NFKC: `k3 ஆக இருக்கும்` for k³ (`78a416ddb22e0850`).

## Medicine 5: B4 literal `\n`

1. **Disease:** B4, 23 documents (19 fix, 4 drop). The two characters backslash and `n` appear in place of a line break.
   Examples:
   - `7cce84d0d76b0c30`: `NDTV Sports\n"உலகக் கோப்பையின்` (16 times)
   - `00b0ea09f19c54e1`: `ஊர்வசி\n[Tuesday, 2012-07-10` (7 times)
   - `caf1190306aaaad1`: `| TamilSpy\nத.தே.கூ அலுவலகம்` (23 times)
2. **Medicine:** a literal `\n` becomes a line break.
   ```python
   def medicine_b4(text):
       return text.replace("\\n", "\n")  # the two characters backslash and n become a line break
   ```
3. **Action:** fix.
4. **Harm test:** gold set: 0 of 41 changed, 0 dropped, PASS. Pack check: changes 22 documents, all labelled B4.
5. **Side effects:**
   - A tutorial that shows `\n` in code (`printf("…\n")`) would get a real line break inside the code. No such case in the pack.
   - Missed: the other B4 form, the placeholder `XNUMX` (`b16791a5741328a2`, already a drop).

## Medicine 6: C3 unfinished last sentence

1. **Disease:** C3, 24 documents (22 fix, 2 drop). The text stops in the middle of a sentence. Examples:
   - `65126393f0ef52c9`: ends `… திருமணம் கைகூடும் பிரார்த்தனை தலமாகவும்`
   - `368e7b6a663593c7`: ends `… என்னும் முடுக்கத்தைக் கொடுப்பதாகவும்,`
   - `00035542745535c7`: ends `… அவரும் பயந்துபோய் தீர்வை முழுவதையும் தள்ளு`
2. **Medicine:** when the last line is at least 80 characters long and ends in a letter or a comma (not in `.` `!` `?` `…`,
   a closing quote or a bracket), cut that line back to its last sentence end. A last line with no sentence end goes.
   Short last lines (bylines, titles, signatures) are not touched.
   ```python
   import re

   def _cut_sentence(line):
       e = max(line.rfind(c) for c in ".!?…")
       return line[:e + 1]  # e = -1: no sentence end, so the whole line goes

   def medicine_c3(text):
       return re.sub(r"(?m)^[^\n]{80,}(?<=[\u0B80-\u0BFFA-Za-z,])\s*\Z", lambda m: _cut_sentence(m[0].rstrip()), text)
   ```
3. **Action:** fix (remove the unfinished sentence).
4. **Harm test:** gold set: 0 of 41 changed, 0 dropped, PASS. Pack check: changes 22 documents, none labelled `clean`. Of the 6 changed documents
   without a C3 label, 3 end in the junk `.�,` after the last full stop (A4), and the cut removes it; 1 ends in a
   related-tags line (C1); 1 ends in an OCR'd verse number (below); 1 is a drop.
5. **Side effects:**
   - The cut can stop at a Tamil initial, so the sentence is still unfinished: `… மைக்கேல் ஆர்.` (`f2cd43ce576f5a6a`).
   - A cut inside quoted speech leaves the quote open (`00035542745535c7`).
   - A verse number that OCR read as Tamil letters is cut: `கெட்டேனே. கூஉ` loses `கூஉ` (`9c360e8b7a812610`). A last line
     that ends in a digit is not touched, so verse numbers in digits stay.
   - A poem or verse whose long last line has no full stop would lose that line. This is the main risk in the gold set.
   - Missed: 5 documents that stop right after a full stop, and 3 whose last line is under 80 characters. 8 of the 24 are missed.

## Medicine 7: C5 headline lists

1. **Disease:** C5, 23 documents (21 drop, 2 fix). The document is only a list of unrelated headlines or one-line items.
   Examples:
   - `3ec2b85b9976a2dd`: six film headlines and nothing else, from `புதிதாக கட்டப்படும் நடிகர் சங்க கட்டிடத்திற்கு விஜயகாந்த் பெயர்! பிரபல நடிகர் கோரிக்கை!`
   - `581feefe2ea19ac5`: four Chennai headlines, from `முதல்வரின் பாராட்டைப் பெற்ற சென்னை ஐ. டி இளைஞர்; அப்படி என்ன செய்தார்?`
   - `60d23b63db1f5dfe`: four clickbait headlines about sex, each ending in `!` or `?`, with no article
2. **Medicine:** drop a document that has at least four lines, where every line is at most 150 characters and ends in
   `!` or `?`. This is the clickbait form; an article has at least one line that ends in a full stop.
   ```python
   import re

   def medicine_c5(text):
       """True: drop the document."""
       return re.search(r"\A(?:[ \t]*[^\n]{1,150}?[!?][ \t]*\n+){3,}[ \t]*[^\n]{1,150}?[!?][ \t]*\n*\Z", text) is not None
   ```
3. **Action:** drop.
4. **Harm test:** gold set: 0 of 41 changed, 0 dropped, PASS. Pack check: drops 3 documents, all labelled C5; none labelled `clean`.
5. **Side effects:**
   - A gold document made only of short questions or exclamations would be dropped: a quiz, a list of FAQ headings, slogans,
     or a poem whose every line ends in `!` or `?`. A page of jokes in quotes ends each line in `"`, so it stays.
   - Missed: 20 of the 23. Most are lists of one-line news items that end in a full stop. By shape they look like a short
     article; telling them apart needs a topic-change model. Others start with a site menu (`Sort By :`, `Results For`).

## Medicine 8: C2 long repeated paragraph

1. **Disease:** C2, 8 documents (7 fix, 1 drop). Examples:
   - `5dc80d9d825fa6cc`: a 641-character paragraph printed twice, from `இது சிறு மளிகை மற்றும் பெட்டிக்கடை வியாபாரிகளை பெரிதும் பாதிக்கும்`
   - `8fb37ca66fe1e1f7`: the lead `வீட்டிற்குள் புகுந்த மர்ம நபர்கள், அங்கே உணவு சமைத்து வைக்கப்பட்டிருப்பதை கண்டுள்ளனர்.` is repeated inside a later paragraph
   - `b54a137e794fc027`: an English reader comment posted twice on a blog page
2. **Medicine:** when a line of at least 180 characters appears again later in the text, whole or inside another line,
   delete the later copy. Titles repeated as the first line are shorter, so they stay.
   ```python
   import re

   def medicine_c2(text):
       return re.sub(r"(?ms)^([ \t]*([^\n]{180,}?)[ \t]*$.*?)\2", r"\1", text)  # a later copy of a long line goes
   ```
3. **Action:** fix.
4. **Harm test:** gold set: 0 of 41 changed, 0 dropped, PASS. Pack check: changes 3 documents, all labelled C2; none labelled `clean`.
5. **Side effects:**
   - A pack document labelled `clean` repeats its 176-character lead as the title (`b726c7682a75ed9f`). The 180 limit leaves it
     alone, but a gold document with a longer repeated lead would be changed.
   - A song with a long refrain, or a legal text that repeats a clause word for word, would lose the later copies.
   - When the copy sat inside a line, a double space is left where it was.
   - Missed: 5 of the 8. Short teaser lines repeated three times (`24ec1b20186fa9ea`), a pull quote glued to the first
     sentence (`be834cefcc145f72`), and repeats under 180 characters.

## Medicine 9: G3 text lost (flag only)

1. **Disease:** G3, 60 documents (57 fix, 3 drop). Lines, list items or the opening of a quote were removed by an earlier
   filter. Examples:
   - `a48cbb35f5ab2603`: `அதற்கு 3 ஆவணங்கள் தேவை.` then only two documents are listed
   - `492ec7b8ce35e05d`: the quote has no opening: `ஆனால்அதிலிருந்து மீண்டு வர இஸ்லாம் எனக்கு பெரிதும் உதவியது" என்று`
   - `bb1f46dbc57d0c5f`: the list of guests is cut and resumes mid-list at `ஜிப்ரி(LLB),மற்றும்`
2. **Medicine:** none. Lost text cannot be restored from the document, and a rule that guesses where text is missing
   would hit good documents.
3. **Action:** keep the documents; flag the doc_ids from labels.csv for the team that owns the earlier filter, so it can be
   checked against Tamil text at the source.
4. **Harm test:** no rule runs, so 0 gold documents changed and 0 dropped.
5. **Side effects:** none from a rule. The cost is that the gaps stay in the training data.

## Medicine 10: C4 two documents joined (flag only)

1. **Disease:** C4, 22 documents (19 fix, 3 drop). Examples:
   - `81e45dba89f683a1`: a text on fasting, then unrelated local news from `மடிப்பாக்கம் : மடிப்பாக்கம் பகுதியில்`
   - `0144a10753d9b239`: an MP's thank-you note, then an unrelated spiritual quote `அமைதியை ஆயுதமாக கொண்டு அன்பு என்னும்`
   - `a433e6b081fd240c`: about 11 district news items joined, each with two summary bullets such as
     `- சிவகங்கையில் கோலப்போட்டி பரிசளிப்பு விழா நடந்தது.`
2. **Medicine:** none. The joins have no common marker: a regex that splits on summary bullets would also split good
   articles that use bullet lists.
3. **Action:** keep; flag the doc_ids. A split at the boundaries needs a topic-change model, which is outside this sheet.
4. **Harm test:** no rule runs, so 0 gold documents changed and 0 dropped.
5. **Side effects:** none from a rule. The joined documents stay joined.

## Medicine 11: D4 bad machine translation (flag only)

1. **Disease:** D4, 17 documents, all drop. Machine translations of Turkish and Russian sites. Examples:
   - `07595651f9328e9f`: Turkish number format left in: `பயணிகளுக்கு% 60 தள்ளுபடி`
   - `5ec82c27d7df0286`: `ரஷ்யாவில் மிக அழகான இடங்களில் ஒரு பெரிய எண் இல்லை` (word-for-word, no meaning)
   - `37c9a1205b3bb933`: `இது இடையகமாக இருந்தால், அவுட் என்றால் சமமாக உள்ளது`
2. **Medicine:** none. Bad translation is a matter of meaning; no regex finds it without also hitting good text.
   The `% 60` pattern finds only one document.
3. **Action:** drop the 17 labelled documents by doc_id. Finding the rest at scale needs a translation-quality score.
4. **Harm test:** no rule runs, so 0 gold documents changed and 0 dropped.
5. **Side effects:** none from a rule. Unlabelled machine translations stay in the data.

## Medicine 12: D3 mixed language (keep)

1. **Disease:** D3, 7 documents (6 fix, 1 drop). Examples:
   - `5eff05f90deef5c7`: English product terms throughout: `Super AMOLED Plus Infinity-O Displayவை`
   - `1b2275c971396534`: embedded English tweets: `Social Media is a breeding ground`
   - `b2f3b49721ef4f89`: a Sanskrit stotra in Tamil script with Tamil commentary: `ஸ்மராரே : ஸ்படிகமணி`
2. **Medicine:** none. DISEASES.md says to label mixed language, not judge it; English words in Tamil writing are natural.
   A clean row has no codes, so 3 clean documents with natural English in them say so in the note instead of D3.
3. **Action:** keep. The one D3 drop is dropped for its other diseases.
4. **Harm test:** no rule runs, so 0 gold documents changed and 0 dropped.
5. **Side effects:** none.
