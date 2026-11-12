# Medicine sheet: ind-mr-sangraha-v (patilvijay23)

**Source:** `labels.csv` (final reviewed Marathi pack, rows 1–500), **500 distinct documents; all 500 marked `full`**. Verdicts: **125 `clean`, 336 `fix`, 39 `drop`**. This supersedes the earlier medicine sheet based on 252 documents. Disease counts are *distinct document counts*, not the number of occurrences; documents can have multiple diseases. A medicine section is included for every disease present in **more than five** reviewed documents.

**Status:** Label review complete; **latest supplied harm-test report passes all 11 executable candidates plus the combined run on 99 gold documents**. Gold safety does not establish general disease detection or full repair coverage.

## Data B Indic gold-set harm test — latest reported results

**Reproduce** with the Data B harness and inputs available locally (Python requires `pyarrow`; adjust paths for another checkout):

```bash
python -I teams/02-data-b/tools/harm_test_indic.py \
  --medicine diagnosis/submissions/ind-mr-sangraha-v/patilvijay23/medicine.md \
  --pack /path/to/packs/ind-mr-sangraha-v.parquet \
  --gold-dir teams/02-data-b/gold \
  --rule all --show 10 \
  --md-out ind_mr_harm_results.md
```

**Latest result source:** `ind_mr_harm_results.md` reports **99 gold documents** from `ind-mr-sangraha-v`, with tested medicine SHA-256 prefix **`f51c4fc18992`**. All 11 rules and `ALL IN ORDER` report **0 changed, 0 dropped (0.00%), PASS**, with both Indic audits passing. The nonempty-gold allowance is **1 affected document**. The report does not record the run date, input paths or full input digests; the command above is a reproduction template. No new test execution is claimed for this documentation update. Recording these results changes the medicine Markdown hash without changing rule code.

**Input provenance:**

- Previously recorded harness SHA-256: `af3fe73b5b3433d97c4f63065dad970ef02bd4be776fc2e00d2e613825c1163e`.
- Previously recorded pack SHA-256: `ad598b6ac2330c00b423b26f826f6d120d8940f0eb7f5412fca2fcd045b4ef30`.
- The previous 88-document gold CSV had SHA-256 `7771ac3d97e311c8e7a499c57e0ce906d34f857b65ccd7c77a00a8d660c2ec2e`; this does not identify the latest 99-document gold input. Its digest must be recorded from the run inputs.
- Current labels (500 documents, including the 26 D3-only verdict updates): `85c2dafd4ceb532982685017d1b059a0d4956662e6506fb6937f2d5bfcb6574d`. The harm report does not record a labels digest.

| Rule | Changed | Dropped | Percent | ZWJ/ZWNJ audit | Normal-form audit | Result |
| --- | ---: | ---: | ---: | --- | --- | --- |
| A5 | 0 | 0 | 0.00% | PASS | PASS | **PASS** |
| D3 | 0 | 0 | 0.00% | PASS | PASS | **PASS** |
| C1 | 0 | 0 | 0.00% | PASS | PASS | **PASS** |
| C2 | 0 | 0 | 0.00% | PASS | PASS | **PASS** |
| A6 | 0 | 0 | 0.00% | PASS | PASS | **PASS** |
| B4 | 0 | 0 | 0.00% | PASS | PASS | **PASS** |
| C3 | 0 | 0 | 0.00% | PASS | PASS | **PASS** |
| D4 | 0 | 0 | 0.00% | PASS | PASS | **PASS** |
| F1 | 0 | 0 | 0.00% | PASS | PASS | **PASS** |
| C4 | 0 | 0 | 0.00% | PASS | PASS | **PASS** |
| C5 | 0 | 0 | 0.00% | PASS | PASS | **PASS** |
| ALL IN ORDER | 0 | 0 | 0.00% | PASS | PASS | **PASS** |

**Previously reported positive-case validation (not rerun in the latest harm report):** Independently running each new rule over all 500 records excluded exactly the reviewed target IDs: C3 **2**, C4 **4**, D4 **20**, F1 **12**, with **0 text changes, 0 non-target exclusions and 0 errors** for each. Combined file-order execution changed **263** documents and excluded exactly the same **38 unique target records**, with **0 errors**. All **12 long-context candidates** survived. Empty text and synthetic Marathi/code-mixed/joiner-containing non-target text stayed unchanged under each new rule.

**Limits:** The remaining **11 C3 fixes, 7 C4 fixes and 1 D4 fix** still require verified contextual intervention. F1 quarantine intentionally withholds all 12 reviewed private records, including 11 labelled `fix`, until complete redaction is verified; labels remain unchanged. Zero gold changes means the Indic audits do not exercise changed outputs. These results establish bounded exclusion behavior and gold safety. F1 redaction is verified only on synthetic supported fields; the helper changed none of the 12 reviewed F1 records. Unseen-record recall, real-data redaction effectiveness and release approval remain unresolved.

## Disease coverage in the final 500 labels

| Disease | Documents | `fix` | `drop` | Proposed handling |
| --- | ---: | ---: | ---: | --- |
| A5 | 221 | 208 | 13 | Executable NFC normalization candidate |
| D3 | 148 | 103 | 19 | Preserve natural code-mixing; explicit no-op |
| C2 | 100 | 95 | 5 | Conservative exact repeated-prefix removal |
| C1 | 97 | 84 | 13 | Narrow publisher/related-content boilerplate removal |
| A6 | 45 | 42 | 3 | Automate mixed-script numeric tokens only; contextual handling for other A6 forms |
| C5 | 23 | 13 | 10 | Remove high-confidence standalone tag-list lines; separately handle headline-only documents |
| D4 | 21 | 1 | 20 | Executable reviewed exclusions: 20 drop; 1 targeted fix pending |
| B4 | 19 | 19 | 0 | Convert literal `\n` sequences in prose (narrow gate) |
| C3 | 13 | 11 | 2 | Executable exclusion of 2 reviewed drops; 11 contextual fixes pending |
| F1 | 12 | 11 | 1 | Executable quarantine of all 12; verified redaction pending |
| C4 | 11 | 7 | 4 | Executable exclusion of 4 reviewed drops; 7 verified splits/fixes pending |

D3 also occurs in **26 `clean` documents** retained as natural code-mixing; disease tags are preserved as descriptive annotations.

**Below medicine threshold:** G1 (**4 documents**; detached Indic combining marks, context-specific repair only) and B5 (**1 document**; broken markup marker). These five diagnoses are fully labelled, but no generic executable medicine is justified by their limited evidence.

**Suggested cleaning order:** B4 → A5 → narrowly scoped A6 → C1 → C5 → C2. D3 is an explicit no-op; C3, C4, D4 and F1 now have bounded executable exclusion/quarantine manifests, with contextual repairs still pending. The fresh Data B `--rule all` Indic run reported a **PASS** for the existing file-order `ALL IN ORDER` sequence, including both Indic-specific audits. The suggested cleaning order here is descriptive and may differ from the sequence actually run by the harness. Verify positive-document effectiveness and combined-rule interactions before deployment.

**Long-context preservation:** **12 documents** are tagged `Long-context candidate — use for long context` in the reviewed labels' `note` column, including both clean documents and documents with fixable defects. Do not impose a blanket short-length cap or drop them merely because they are long; preserve the coherent long-form text after authorized fixes. No long-context candidate has a `drop` verdict.

---

## Medicine 1 — A5: wrong Unicode normal form

1. **Disease:** A5, **221 documents**. Decomposed Devanagari forms whose NFC normalization changes the code-point sequence. Examples from the labels:
   - `4884f7c293a7beab`: `ऱ` at offset 2437 → NFC `ऱ`.
   - `47594b68339a08b9`: `ऴ` → NFC `ऴ`.
   - `038ffeeda8d9dca7`: `ऱ` at offset 68 (5 occurrences) → NFC `ऱ`.
   - **Additional reviewed example (rows 351–500 unless noted):** `2fcf621e5200ec99`: non-NFC `ऱ` at offset 171.

2. **Medicine:** Normalize the text to NFC. Do **not** use NFKC or change Indic digits, ZWJ or ZWNJ.

   ```python
   import unicodedata

   def cure_a5(text):
       return unicodedata.normalize("NFC", text)
   ```

3. **Action:** Fix by NFC normalization only; it does not override a document-level `drop` decision for other diseases.

4. **Harm test (Data B Indic `harm_test_indic.py`): PASS** — **0 changed, 0 dropped / 99 gold documents (0.00%)**; gold limit: 1 changed/dropped document. **ZWJ/ZWNJ audit: PASS** (0 affected documents with changed joiner counts). **Normal-form audit: PASS** (0 affected documents left NFC or lost a compatibility character). This demonstrates no measured gold harm; it does not establish NFC-repair effectiveness on A5-positive documents.

5. **Side effects:** NFC changes code-point sequences and may invalidate offsets; NFC does **not** reconnect a detached matra/virama, repair OCR errors, or fix severe structural corruption. Count actual changes in the harm test rather than presuming they are harmless.

## Medicine 2 — D3: natural mixed-language content

1. **Disease:** D3, **148 documents**. Natural Marathi mixed with English names, titles, technical words, or Sanskrit quotations. Examples:
   - `870f3c12624cc486`: `UPSC` near offset 1172.
   - `31e2deeb3fd7a6f3`: `Karjat Nagar Panchayat Election` near offset 200.
   - `8344f9091076fadd`: English phrase `The question is will he get` near offset 866.
   - **Additional reviewed example (rows 351–500 unless noted):** `bfd0e9032a359e9b`: natural Marathi–English code-mixing near offset 0; co-occurring C1/C2 require separate attention.

2. **Medicine:** Preserve the text. Mixed language alone is **not** evidence that the document is damaged.

   ```python
   def cure_d3(text):
       return text
   ```

3. **Action:** Keep unchanged for D3. Apply separate, independently tested medicines if the same document also has another disease. Of the 28 previously `fix` D3-only documents, **26 are now `clean`** because their notes call for retaining natural mixing. **Two remain `fix`** (`273f333736ce4524` and `8344f9091076fadd`) because their notes say `remove non-indic content`; these require contextual review, and the D3 no-op does not implement that removal. Any separate transformation must be justified by another disease or a specifically documented operation.

4. **Harm test (Data B Indic `harm_test_indic.py`): PASS** — **0 changed, 0 dropped / 99 gold documents (0.00%)**; gold limit: 1 changed/dropped document. **ZWJ/ZWNJ audit: PASS** (0 affected documents with changed joiner counts). **Normal-form audit: PASS** (0 affected documents left NFC or lost a compatibility character). Because this is an intentional no-op, its PASS does not show that the two remaining D3-only `fix` records were corrected.

5. **Side effects:** No direct mutation. The risk is *over-cleaning by other medicines*: an English name, English headline, or Sanskrit quotation is not necessarily C1/C5 boilerplate or A6 corruption.

## Medicine 3 — C1: publisher/navigation boilerplate

1. **Disease:** C1, **97 documents**. Publisher promotions, unrelated navigation, login/footer prompts and related-story notices. Examples:
   - `2c66d24bfd6db2ef`: related-story marker `हे ही वाचाः` near offset 1082.
   - `e14f9a0e6e8d1d9b`: English publisher promotion near offset 741 and Marathi follow prompt near offset 972.
   - `038ffeeda8d9dca7`: social-media/source navigation near offset 1312 (`साम आता सर्व सोशल मीडिया`).
   - **Additional reviewed example (rows 351–500 unless noted):** `983103a12fa7a78f`: publisher/navigation boilerplate near offset 1926.

2. **Medicine:** Remove only full lines starting with clearly identified navigation/related-story/promo phrases; do not delete text just because it is in English. Keep line endings stable and avoid deleting partial sentence matches.

   ```python
   import re

   _C1_LINE = re.compile(
       r"^\s*(?:"
       r"हे\s*ही\s*वाचा\s*[:ः]?.*"
       r"|हेही\s*वाचा\s*[:ः]?.*"
       r"|हे\s*देखील\s*वाचा\s*[:ः]?.*"
       r"|Read\s+Also\s*[:\-]?.*"
       r"|Keep\s+Reading\s*[:\-]?.*"
       r"|Forgot\s+your\s+password\??\s*.*"
       r"|Home\s*/\s*Marathi\s*"
       r"|Get\s+Latest\s+Marathi\s+News.*"
       r"|साम\s+आता\s+सर्व\s+सोशल\s+मीडिया.*"
       r")\s*$",
       flags=re.IGNORECASE,
   )

   def cure_c1(text):
       lines = text.splitlines(keepends=True)
       return "".join(
           line for line in lines
           if not _C1_LINE.fullmatch(line.rstrip("\r\n"))
       )
   ```

3. **Action:** Fix only matching boilerplate lines. A `drop` verdict remains if no coherent article survives.

4. **Harm test (Data B Indic `harm_test_indic.py`): PASS** — **0 changed, 0 dropped / 99 gold documents (0.00%)**; gold limit: 1 changed/dropped document. **ZWJ/ZWNJ audit: PASS** (0 affected documents with changed joiner counts). **Normal-form audit: PASS** (0 affected documents left NFC or lost a compatibility character). Verify independently that the narrow matcher removes actual C1 boilerplate without deleting article content.

5. **Side effects:** Some genuine article text could begin with one of the listed phrases, and boilerplate embedded mid-paragraph is intentionally not removed. This rule is conservative; context-specific cleanup is needed for more complex cases.

## Medicine 4 — C2: exact repeated lead/content

1. **Disease:** C2, **100 documents**. Duplicate titles, lead paragraphs, or repeated article snippets. Examples:
   - `4884f7c293a7beab`: opening paragraph repeats at offsets 0 and 316.
   - `948113e0495d4af9`: opening text repeats at offsets 0 and 122.
   - `9532c5c8c0d27ac4`: lead/title repeats at offsets 0 and 114.
   - **Additional reviewed example (rows 351–500 unless noted):** `f8666e415e416667`: repeated lead/text near offsets 104 and 344.

2. **Medicine:** Remove only a **long, exact** second copy of the document's opening content if it occurs near the beginning; do not perform global line deduplication, fuzzy matching, or removal of legitimate refrains.

   ```python
   def cure_c2(text):
       seed_len, min_repeat, search_limit = 48, 80, 1600
       if len(text) < min_repeat * 2:
           return text
       seed = text[:seed_len]
       second = text.find(seed, seed_len, min(len(text), search_limit))
       if second < 0:
           return text
       matched = 0
       max_match = min(second, len(text) - second)
       while matched < max_match and text[matched] == text[second + matched]:
           matched += 1
       if matched < min_repeat:
           return text
       return text[:second] + text[second + matched:]
   ```

3. **Action:** Fix only verified exact repeated prefixes, keeping the first occurrence. Review other C2 variants manually.

4. **Harm test (Data B Indic `harm_test_indic.py`): PASS** — **0 changed, 0 dropped / 99 gold documents (0.00%)**; gold limit: 1 changed/dropped document. **ZWJ/ZWNJ audit: PASS** (0 affected documents with changed joiner counts). **Normal-form audit: PASS** (0 affected documents left NFC or lost a compatibility character). Verify on C2-positive documents that intended duplicates are removed with valid joins.

5. **Side effects:** Repeated opening text may be intentional (poetry, quotations, structured articles). The strict rule misses shorter duplicates and OCR-altered copies, which is preferable to deleting uncertain content. Check the resulting join around the removed span.

## Medicine 5 — A6: wrong or mixed script

1. **Disease:** A6, **45 documents**. A heterogeneous collection including corrupted mixed digits, hyphenated Marathi words, intruding Latin characters, and a stray non-Devanagari symbol. Examples:
   - `4884f7c293a7beab`: mixed digits `१0७`, `१0`, `३0` (ASCII zero positions recorded at offsets 1901, 1910 and 1952 in the final labels).
   - `e71787a3124f9007`: Marathi word fragments `चेह-याच्या` and `ब-याच` (hyphen positions at offsets 509 and 834 in the final labels).
   - `208b033cb8584898`: stray `U+00BA` inside a Marathi word near offset 787 (2 occurrences).
   - **Additional reviewed example (rows 351–500 unless noted):** `7d5867bf37cf6900`: stray `U+00BA` in a word near offset 885 (also F1; handle privacy separately).

2. **Medicine:** **Automate only one narrow subtype:** replace ASCII digits inside a contiguous token containing both ASCII and Devanagari digits. Hyphen, stray `U+00BA`, Latin-character intrusion, standalone ASCII digits, and other A6 cases need separate context-aware decisions.

   ```python
   import re

   _A6_MIXED_DIGITS = re.compile(r"[०-९0-9]+")
   _A6_DIGIT_MAP = str.maketrans("0123456789", "०१२३४५६७८९")

   def cure_a6(text):
       def convert(match):
           token = match.group()
           if re.search(r"[०-९]", token) and re.search(r"[0-9]", token):
               return token.translate(_A6_DIGIT_MAP)
           return token
       return _A6_MIXED_DIGITS.sub(convert, text)
   ```

3. **Action:** Fix the mixed-digit subtype only; handle remaining A6 occurrences through verified context-specific repairs or separately tested medicines; do not pretend that the mixed-digit rule covers all 45 A6 documents.

4. **Harm test (Data B Indic `harm_test_indic.py`): PASS** — **0 changed, 0 dropped / 99 gold documents (0.00%)**; gold limit: 1 changed/dropped document. **ZWJ/ZWNJ audit: PASS** (0 affected documents with changed joiner counts). **Normal-form audit: PASS** (0 affected documents left NFC or lost a compatibility character). Only mixed-digit conversion is covered; other A6 subtypes require separate source-aware tests.

5. **Side effects:** Even mixed-script digits can occasionally be deliberate; global Latin removal, blanket hyphen replacement, or indiscriminate `U+00BA` substitution would risk damaging legitimate names and D3 code-mixing.

## Medicine 6 — B4: literal escaped newline in prose

1. **Disease:** B4, **19 documents**. A literal backslash followed by `n` occurs where a line boundary is intended. Examples:
   - `5cd1cc2146075a9f`: literal `\n` near offset 81 (3 occurrences).
   - `09f78635c7686fd8`: literal `\n` near offset 14 (11 occurrences).
   - `8f3c76c4c4ad8584`: literal `\n` near offset 109 (13 occurrences).
   - **Additional reviewed example (rows 351–500 unless noted):** `3561e05403291f93`: literal `\n` near offset 42 (99 occurrences).

2. **Medicine:** Convert the literal two-character sequence `\n` to a newline **only for this identified prose subtype**. Run before line-based C1/C5/C2 cleaning.

   ```python
   def cure_b4(text):
       # Conservative gate for recurring escaped newlines in the Marathi prose pack.
       if text.count("\\n") < 3:
           return text
       return text.replace("\\n", "\n")
   ```

3. **Action:** Fix escaped newlines when they recur as prose formatting artifacts.

4. **Harm test (Data B Indic `harm_test_indic.py`): PASS** — **0 changed, 0 dropped / 99 gold documents (0.00%)**; gold limit: 1 changed/dropped document. **ZWJ/ZWNJ audit: PASS** (0 affected documents with changed joiner counts). **Normal-form audit: PASS** (0 affected documents left NFC or lost a compatibility character). Check B4-positive prose separately so valid technical escape sequences remain intact.

5. **Side effects:** Technical quotations can legitimately include `\n`. The recurrence threshold reduces but does not eliminate that risk. Other escaped control sequences are left untouched.

## Medicine 7 — C3: incomplete or truncated document

1. **Disease:** C3, **13 documents**. Text starts or stops mid-sentence, or page-continuation artifacts interrupt it. Examples:
   - `7ac16bc32542abcd`: incomplete ending near offset 1203.
   - `8acc240b173977d0`: incomplete beginning at offset 0 and page-continuation artifacts.
   - `177179a646864418`: incomplete ending near offset 824 (`चांगले निर्णय`).
   - `31dcd9c6ce0f3808`: incomplete document boundary near offset 31221

2. **Medicine:** **Context-specific operation; not an unreviewed label.** Verify the source boundary and either restore the missing text, trim the demonstrably incomplete fragment while preserving a coherent document, or exclude the document. A universal regex cannot reliably infer the original sentence or detect all truncated Marathi prose. **The executable candidate below excludes only reviewed drop records; contextual repairs remain pending.**


   ```python
   import hashlib

   # Reviewed Marathi pack records only: original and file-order pre-rule text.
   # SHA-256 avoids embedding private values and supports the text-only harness.
   _EXCLUDED_SHA256 = frozenset({
       # 0ad004d5deb1e7fe
       "0ad004d5deb1e7fece97aa9806c12904aa8f3443a9784e6ad8192fe37ccdc50a",
       # 10cfc7c874a1bb29
       "10cfc7c874a1bb29938183dcf35cdeb6b9bd36cb47b721b46cea9429e60552c9",
       "395b9f4527f05f508da2f9ea26395d99bec57bd7a46934165c4dad8eb2e04ce3",
   })

   def cure_c3(text):
       if hashlib.sha256(text.encode("utf-8")).hexdigest() in _EXCLUDED_SHA256:
           return True  # Exclude/quarantine; retain provenance outside public output.
       return text
   ```

3. **Action:** Fix only with verified source/boundary; **drop** when no coherent content remains (as in `0ad004d5deb1e7fe`, labelled `drop`).

4. **Harm test (Data B Indic `harm_test_indic.py`): PASS — 0 changed, 0 dropped / 99 gold documents (0.00%); ZWJ/ZWNJ audit PASS; normal-form audit PASS.** See the fresh results above. Positive-case scope: **2 reviewed records excluded individually**; all other records stay unchanged for this rule. Contextual repairs are not covered.

5. **Side effects:** Trimming near punctuation can remove legitimate text; generating a missing ending would invent content. Some incomplete-looking passages are intentional excerpts.

**Executable scope:** Exact fingerprints are a finite reviewed exclusion manifest, not a general disease detector. Modified or unseen text requires renewed review. Fingerprints include original text and text after preceding text rules in file order, so tested combined execution still recognizes these records. Keep original metadata and exclusion reasons in restricted provenance.

## Medicine 8 — D4: severely unnatural machine translation

1. **Disease:** D4, **21 documents**. Broken literal translation, unnatural Marathi grammar, or extensive semantically corrupted wording. Examples:
   - `61b2c25e9513730b`: broken translated phrasing near offset 2793 (`काय माजी कर्मचारी किराणा दुकान...`).
   - `866b1853d8a9d95a`: severely unnatural text from offset 0.
   - `43785419033933e9`: severely unnatural translated phrasing from offset 0.
   - **Additional example from reviewed row 291:** `cc36761de1d96f0f`: localized awkward translated wording near offset 981, labelled `fix` rather than `drop`.
   - **New example from rows 351–500:** `816e770dc45f85c5`: pervasive machine-translation grammar corruption from offset 0; labelled `drop`.

2. **Medicine:** **Source-aware intervention only.** Of the 21 reviewed D4 documents, **20 carry `drop` and 1 carries `fix`** (`cc36761de1d96f0f`, a localized wording defect). Do not attempt word-by-word regex "repair" or machine-generate a replacement training document. The single `fix` case needs an evidence-preserving local correction, not a global language rewrite. **The executable candidate below excludes only reviewed drop records; contextual repairs remain pending.**


   ```python
   import hashlib

   # Reviewed Marathi pack records only: original and file-order pre-rule text.
   # SHA-256 avoids embedding private values and supports the text-only harness.
   _EXCLUDED_SHA256 = frozenset({
       # 43785419033933e9
       "43785419033933e9f960794254f99a82f58573597bb458a1ff6ece908ff5615e",
       # 4c7b3c1a1061d97f
       "4c7b3c1a1061d97f22cd98fc25efcc5121806199350f56eac5c3ab2ade99929f",
       # 61b2c25e9513730b
       "4d59a3a5a9bc1ec25f9d8534d1fc6be16eed665184b870b6781e3cfeeddccb80",
       "61b2c25e9513730b3f652488ad8f9f111f4181f78ec62bf01f78f5465e4effb6",
       # 6684bd791d877bc0
       "6684bd791d877bc04352f9688f6b82fb85fdf236095eb2fe2f7f45080382a626",
       # 787dd37a24269172
       "787dd37a2426917285649b89c3498c782ddff3c729e902df662fe61cb5916f0e",
       # 78d17bae5d29f865
       "78d17bae5d29f8654e70637ce32536f3fbf90f78c484cbe5bb4a2a9bf6f05646",
       # 7f79826d091b1834
       "7f79826d091b1834136bae3b13e8a9bcf5eb91fb7048454d58f860588f60c175",
       # 816e770dc45f85c5
       "816e770dc45f85c5b503878ef07c45ffe8403a0794e2955f0648ab7e003b49ee",
       "933d30ff5e07e29a42f4090600f9a6c9347c967931bdb7ce35ec2130dec0f97e",
       # 866b1853d8a9d95a
       "866b1853d8a9d95a9f3e5cfe1f57484891f138bcce185c57a6dc0aaa123117de",
       # 915caa7e4b7ded75
       "915caa7e4b7ded751b5e54860a842ff604380c51daaa9207c3f747d3251a2090",
       # 994056d70dd415f8
       "994056d70dd415f803bd61335fda5f6cb17b299070077e9e416d51b04d3ad016",
       # 9e41a5d56ac92089
       "9e41a5d56ac92089dae7eef899dd02ffa4d7290237855b1d112d85e74fe8c222",
       # 9ed1317a6abd1ce0
       "9ed1317a6abd1ce0aeb0579c3b451808e64bdf6a394289523c6b656e70b644dd",
       # a07ef1c92c0cceb3
       "a07ef1c92c0cceb3008efdbca6f2decde997fca77ee73c9d7f2394e83d735307",
       # a274c193c5e5f3ee
       "a274c193c5e5f3ee72858a9143927532090eb3469df2f5928bc12450eefa06a9",
       # c4cbdc3ab951c6b8
       "c4cbdc3ab951c6b8d78efc1e373e81c0e88b0abc159de384ee6209ef469ec12e",
       "d4baa996ec32d3d7b3427ce972d20a6a907e06a5a2975ea5cea7296a40119b77",
       # d0b76c2968e55e7d
       "741fb8dc1ff20269175f0bbc71a9dbd7eeea4208719bf6c0dabc728b54fb2b4c",
       "d0b76c2968e55e7dbd55218dfef5454a46e4071cf2f6016999489ae67049ea2b",
       # e977e6e5b6339831
       "a681d885fe07f9f18dcf20d1964de4615ad1c26a51522c6337ed9436fd54aa5c",
       "e977e6e5b63398319f54fe9da7cb72a0ea031b9bfd9cfb688efa69ecb965c315",
       # f0b421e314af77d6
       "f0b421e314af77d6649909e8ccf3db245e49bdc7a1f60665b202c20102e697b7",
       # f94044ff48697280
       "a9f684f8e34573b1abe36123e1831416e6fbf2d22124c63219b716b3019201bf",
       "f94044ff486972805edce8c630c643bb02ef18aa13e58f62a0af3947baa3498e",
   })

   def cure_d4(text):
       if hashlib.sha256(text.encode("utf-8")).hexdigest() in _EXCLUDED_SHA256:
           return True  # Exclude/quarantine; retain provenance outside public output.
       return text
   ```

3. **Action:** **Drop the 20 documents marked `drop`**, including `9e41a5d56ac92089` and `f94044ff48697280` (both now labelled `full`); retain the single `fix` document for a limited, source-faithful wording repair. All 21 diagnoses are final reviewed labels.

4. **Harm test (Data B Indic `harm_test_indic.py`): PASS — 0 changed, 0 dropped / 99 gold documents (0.00%); ZWJ/ZWNJ audit PASS; normal-form audit PASS.** See the fresh results above. Positive-case scope: **20 reviewed records excluded individually**; all other records stay unchanged for this rule. Contextual repairs are not covered.

5. **Side effects:** Unusual idioms, literary style and natural code-mixing could be mistaken for bad translation. Avoid applying a broad language-quality classifier without validation.

**Executable scope:** Exact fingerprints are a finite reviewed exclusion manifest, not a general disease detector. Modified or unseen text requires renewed review. Fingerprints include original text and text after preceding text rules in file order, so tested combined execution still recognizes these records. Keep original metadata and exclusion reasons in restricted provenance.

## Medicine 9 — F1: private-person information

1. **Disease:** F1, **12 documents**. Private residential locations, personally linked addresses or contact details. Examples **without revealing any private values**:
   - `fab4928039a870ab`: private-person-linked street-level location near offset 9.
   - `727a8a3d9a6f4fd4`: phone number near offset 2095.
   - `d2dbdd1f87b6a3e1`: private residential location near offset 278.
   - `b5776aacf45b7cac`: private-person identity/location at offset 256 (private values intentionally omitted).

2. **Medicine:** **Context-specific privacy gate.** Identify and redact the exact private span with surrounding context, or exclude the document if the sensitive material cannot be safely removed. Names of public figures and public institutions are not automatically private data. **Do not embed any private values in rule code, examples, logs, PRs or JSON reports. The executable candidate first quarantines all 12 reviewed F1 records pending verified full-span redaction, then applies a bounded Marathi-aware redactor to other text. It uses `<PHONE>`, `<EMAIL>` and `<ADDRESS>` placeholders only with explicit private context; it preserves recognised organisation contacts, role mailboxes and example/government email domains.**


   ```python
   import hashlib

   # Reviewed Marathi pack records only: original and file-order pre-rule text.
   # SHA-256 avoids embedding private values and supports the text-only harness.
   _EXCLUDED_SHA256 = frozenset({
       # 001bc250879bd0f7
       "001bc250879bd0f702986535ee3252eee6e1a7c48cdee7f2890a890fd6d50583",
       # 404f212106f160c8
       "404f212106f160c83000ac10881284d088304b030173cbd48fbe99d83c42f743",
       # 50bf742434fe8393
       "50bf742434fe8393f951f369fee4030e82089b9f4ae1fc64cf130eaf3c7b8844",
       # 6402789257fa2f5a
       "011dd7d4bd18b4f776adc7618c36a81e30ae22fdcdde3a446d068968f1519296",
       "6402789257fa2f5a997646dca7c843b74d4dece07a4c7419fd92684c46b213cd",
       # 66ebbb3c7f89fc6e
       "66ebbb3c7f89fc6e9d0fd41720240f166e6a72ebe5fbca7e9d9c76ee8f47de44",
       # 727a8a3d9a6f4fd4
       "25a62eaac83c681739b5550c373f1f6fe1f8cf79ab5f63455d12b131659cc873",
       "727a8a3d9a6f4fd42343d464e0f3b36a153a29ef3c1a91bb9b3635aaf4b65be8",
       # 7d5867bf37cf6900
       "7d5867bf37cf6900af52d058752e3dfc761949319080591871e7c6bb5b0d3e2d",
       # 8924481cb3403322
       "8924481cb3403322ef651e1327e34417558683c9b6c7033dbc81111afd507873",
       # b5776aacf45b7cac
       "b5776aacf45b7cac904ffedd0da2f4fe8e5b08ea0732bc03684d66a93349ae1e",
       # d2dbdd1f87b6a3e1
       "d2dbdd1f87b6a3e1dda084663699ee354eca663094d25b6aa4ef48e373fa07af",
       # fab4928039a870ab
       "fab4928039a870ab3506e01b8a5a910ee799e3662c2a85cb8c3454c092364e50",
       # fedd23c56d6850a6
       "392115d2af134133091b7c8e672863133bea34461b3d8d352e3f6cdd5af5b0b3",
       "fedd23c56d6850a6fcdd4911a9b268d1f00d30a2b1c96e9b59bc8c05335e9936",
   })

   # Adapted from g1-specv1/tools/f1_rule.py: explicit private context,
   # typed placeholders and organisation/role safeguards. Marathi prose only.
   import re

   _F1_ORG = re.compile(
       r"(?:महानगरपालिका|नगरपालिका|ग्रामपंचायत|शासकीय|सरकारी|कार्यालय|"
       r"विद्यापीठ|महाविद्यालय|विद्यालय|रुग्णालय|पोलीस|पोलिस|हेल्पलाइन|"
       r"कंपनी|बँक|बँकेचा|संस्था|सार्वजनिक|टोल[ -]?फ्री|"
       r"\b(?:government|office|university|hospital|company|helpline|bank)\b)", re.I)
   _F1_PERSONAL = re.compile(
       r"(?:वैयक्तिक|खाजगी|खासगी|घरचा|घरचा संपर्क|घरचा पत्ता|घरचा फोन|"
       r"घरचा ईमेल|राहत्या घराचा|निवासी पत्ता|माझा|माझी|माझे|"
       r"\b(?:personal|private|home|residential|my)\b)", re.I)
   _F1_EMAIL = re.compile(
       r"(?<![\w.+%-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])")
   _F1_ROLE = re.compile(
       r"^(?:info|contact|support|help|admin|office|sales|press|media|"
       r"noreply|no-reply|editor|news|helpline|hr|jobs)$", re.I)
   _F1_SAFE_DOMAIN = re.compile(
       r"(?:^|\.)(?:example\.(?:com|org|net)|invalid|test|localhost|"
       r"users\.noreply\.github\.com|gov\.in|nic\.in)$", re.I)
   # Indian mobiles, ASCII or Devanagari digits; no digit normalization.
   _F1_PHONE = re.compile(
       r"(?<![\w+])(?:\+[9९][1१][ -]?)?[6-9६-९][0-9०-९]{4}[ -]?[0-9०-९]{5}(?![\w-])")
   # Only a labelled personal address field, never an inferred place/name span.
   _F1_ADDRESS = re.compile(
       r"(?P<label>(?:(?:वैयक्तिक|खाजगी|खासगी|निवासी)\s+पत्ता|"
       r"(?:घरचा|राहत्या घराचा)\s+पत्ता|(?:home|private|residential)\s+address)"
       r"\s*[:：]\s*)(?P<value>[^\r\n]+)", re.I)

   def _f1_private_context(text, start, end):
       # Stay within the line; the preceding line can identify an organisation.
       lo = text.rfind("\n", 0, start) + 1
       hi = text.find("\n", end)
       hi = len(text) if hi < 0 else hi
       previous = text.rfind("\n", 0, max(0, lo - 1)) + 1
       context = text[previous:hi]
       return not _F1_ORG.search(context) and bool(_F1_PERSONAL.search(text[lo:start]))

   def _redact_f1_mr(text):
       """Bounded candidate, not proof of complete privacy removal.
       Unlabelled details, names, landlines and narrative addresses need review.
       """
       def email(match):
           local, domain = match.group().rsplit("@", 1)
           if _F1_ROLE.fullmatch(local) or _F1_SAFE_DOMAIN.search(domain):
               return match.group()
           return "<EMAIL>" if _f1_private_context(match.string, match.start(), match.end()) else match.group()

       def phone(match):
           return "<PHONE>" if _f1_private_context(match.string, match.start(), match.end()) else match.group()

       def address(match):
           if not _f1_private_context(match.string, match.start("value"), match.end("value")):
               return match.group()
           # Multi-field lines need separate span review; do not erase other fields.
           value = match.group("value")
           if "<ADDRESS>" in value or re.search(r"[;|]|<(?:PHONE|EMAIL)>", value):
               return match.group()
           return match.group("label") + "<ADDRESS>"

       out = _F1_EMAIL.sub(email, text)
       out = _F1_PHONE.sub(phone, out)
       return _F1_ADDRESS.sub(address, out)

   def cure_f1(text):
       # Quarantine takes precedence: partial redaction never releases these records.
       if hashlib.sha256(text.encode("utf-8")).hexdigest() in _EXCLUDED_SHA256:
           return True
       return _redact_f1_mr(text)
   ```

3. **Action:** Fix by verified, privacy-preserving redaction; otherwise **drop**. Do not release an unredacted F1 record.

4. **Harm test (Data B Indic `harm_test_indic.py`): PASS — 0 changed, 0 dropped / 99 gold documents (0.00%); ZWJ/ZWNJ audit PASS; normal-form audit PASS.** See the fresh results above. Positive-case scope: **12 reviewed records excluded individually**; no other pack records changed. The redaction helper alone changed **0/12** reviewed F1 records, so it has no demonstrated repair coverage on those cases. Synthetic checks cover supported fields; they do not establish real-data recall.

5. **Side effects:** A broad name/address detector can erase legitimate public references; a narrow detector can miss sensitive data. The label's `hex` and evidence should never reproduce private values.

**Executable scope and provenance:** Adapted from the shared [g1-specv1 F1 rule](https://github.com/patilvijay23/era-v5-lab/blob/g1-specv1/teams/01-data-a/spec_v1/tools/f1_rule.py), using explicit private context, typed placeholders and public-contact safeguards. This is a self-contained Marathi prose adaptation; it does not import the original code-family dispatch or tree-sitter path. Apply only to trusted Marathi pack provenance. The exact-fingerprint quarantine takes precedence over redaction and recognises original and tested file-order pre-rule text. Edited/unseen records cannot be assumed private-data-free.

**Supported redactions:** Private-labelled email fields; Indian mobile numbers starting with 6–9, optionally prefixed by +91, using ASCII or Devanagari digits; single-line explicitly labelled residential-address fields. Organisation cues on the current or immediately preceding line suppress redaction. Address lines containing multiple fields require separate review. Names, unlabelled details, narrative locations, landlines, obfuscated contacts and unrecognised organisation cues remain limitations. Redaction can remove meaningful characters, including joiners inside a sensitive span; gold audits with zero changes do not validate such cases. No blanket digit normalization or name/place deletion is performed.

**Validation:** The latest supplied report shows individual and combined Indic harm tests passed with 0 changed / 0 dropped of 99 gold records and both audits PASS. Previously reported full-pack behavior was 263 changed / 38 excluded combined, including all 12 F1 quarantines; no errors and all 12 long-context candidates survive. Synthetic-only tests verify supported redaction, idempotence, public-contact preservation, number boundaries and unrelated Indic text preservation:

```bash
python3 -m unittest discover -s teams/02-data-b/medicine-tests
```

## Medicine 10 — C4: unrelated documents joined

1. **Disease:** C4, **11 documents**. Two unrelated articles or passages concatenated without a reliable document boundary. Examples:
   - `eca53051bfdab52d`: a new document begins near offset 1975.
   - `815eb112e94faf6e`: unrelated second text begins near offset 115.
   - `f2b8c25ffbcc196c`: unrelated standalone passage begins near offset 555 (`रशियातल्या फिफा`).
   - **Additional reviewed example (rows 351–500 unless noted):** `f1b6e560a1351d1c`: unrelated joined passage starts near offset 1716.

2. **Medicine:** **Context-specific operation; not an unreviewed label.** Inspect the boundary and split into separately traceable documents, or retain just the verified coherent span if provenance permits. Do not create duplicate `doc_id`s or guess split locations from language switches alone. **The executable candidate below excludes only reviewed drop records; contextual repairs remain pending.**


   ```python
   import hashlib

   # Reviewed Marathi pack records only: original and file-order pre-rule text.
   # SHA-256 avoids embedding private values and supports the text-only harness.
   _EXCLUDED_SHA256 = frozenset({
       # 802ea4e0038fae55
       "802ea4e0038fae55fba668aca47d3f7c546b15564d109bc8afb500c5ad78fd02",
       # 9910e11f3461f5d0
       "9910e11f3461f5d09f7abfb46cfca489b7bb5209d507d963dab976ff55e3b112",
       "e5d935b539d7724761ec3e96fbfe365fece60f1423ef62aee339f1a913889716",
       # a3a467b4dcb9c51b
       "a3a467b4dcb9c51b0a2112852ad9b31a8b9f895f21d207c9a3dac6114617ca02",
       "dbc9e19bc50ab161305d9e57e012f471e5250092c7dc4eef472245eb3ecb86e8",
       # d89a364142de1d38
       "c71c2ca6277898aaf1416e32d9f280c46f4a98293b21601bf23103e5f0536aa9",
       "d89a364142de1d38711026940c0f096e45d2276cb062773651c866d4998228d7",
   })

   def cure_c4(text):
       if hashlib.sha256(text.encode("utf-8")).hexdigest() in _EXCLUDED_SHA256:
           return True  # Exclude/quarantine; retain provenance outside public output.
       return text
   ```

3. **Action:** Fix by a provenance-preserving split/removal when possible; **drop** when the surviving text is not coherent (`d89a364142de1d38` and `9910e11f3461f5d0` are labelled `drop`).

4. **Harm test (Data B Indic `harm_test_indic.py`): PASS — 0 changed, 0 dropped / 99 gold documents (0.00%); ZWJ/ZWNJ audit PASS; normal-form audit PASS.** See the fresh results above. Positive-case scope: **4 reviewed records excluded individually**; all other records stay unchanged for this rule. Contextual repairs are not covered.

5. **Side effects:** Legitimate bilingual quotations, interviews, and multi-section articles may look like joined documents; blind splitting can corrupt source context.

**Executable scope:** Exact fingerprints are a finite reviewed exclusion manifest, not a general disease detector. Modified or unseen text requires renewed review. Fingerprints include original text and text after preceding text rules in file order, so tested combined execution still recognizes these records. Keep original metadata and exclusion reasons in restricted provenance.

## Medicine 11 — C5: tag/keyword/headline-list contamination

1. **Disease:** C5, **23 documents**. Navigation headlines, SEO tags, related-article lists, and keyword blocks mixed with prose. Examples:
   - `4dea645e7a66adbb`: headline/keyword list begins near offset 2520.
   - `5c0626f06c750fcf`: navigation headline/tag-list starts at offset 0 (`लाईव्ह न्यूज`); the record is labelled `drop`.
   - `9532c5c8c0d27ac4`: standalone `Tags: Sleeping habits` near offset 320.
   - **Additional reviewed example (rows 351–500 unless noted):** `0c7931b66f6e2ea5`: unrelated headline/link list near offset 4702 (also C1/B4).

2. **Medicine:** Remove only clearly standalone tag/keyword lines, not legitimate lists that are part of article content. Whole navigation-only documents retain their reviewed `drop` action; generic text segmentation is not safe here.

   ```python
   import re

   _C5_TAG_LINE = re.compile(
       r"^\s*(?:Tags?|Keywords?|कीवर्ड)\s*[:：]\s*\S.*$",
       flags=re.IGNORECASE,
   )

   def cure_c5(text):
       return "".join(
           line for line in text.splitlines(keepends=True)
           if not _C5_TAG_LINE.fullmatch(line.rstrip("\r\n"))
       )
   ```

3. **Action:** Fix standalone matched tag lines; remove other verified contamination with a context-specific operation. **Drop** documents composed almost entirely of navigation/headline lists (e.g., `5c0626f06c750fcf`), consistent with their labels.

4. **Harm test (Data B Indic `harm_test_indic.py`): PASS** — **0 changed, 0 dropped / 99 gold documents (0.00%)**; gold limit: 1 changed/dropped document. **ZWJ/ZWNJ audit: PASS** (0 affected documents with changed joiner counts). **Normal-form audit: PASS** (0 affected documents left NFC or lost a compatibility character). The narrow tag-line rule does not cover every C5 headline-list subtype; test positive-case coverage separately.

5. **Side effects:** Metadata examples and instructional prose can contain genuine `Tags:` or `Keywords:` lines. Broadly deleting any list or headline would destroy real content. Some C5 overlaps C1, so combined-rule effects must be assessed separately.

---

## Review and release checklist

- **Reviewed label input:** All **500** source records are `full`. Current verdicts are **125 clean / 336 fix / 39 drop**, following the 26 D3-only verdict updates. Reviewed evidence/offsets and the 12 long-context tags are unchanged. No 252-row totals or `partial`-read labels remain.
- **D3 semantics:** **26 D3-only documents are now `clean`** because their notes preserve natural mixing. **Two remain `fix`** because their notes request removal of non-Indic content; contextual review is pending. D3 remains a no-op, so no text-cleaning change is claimed.
- **D4 outcomes:** Apply the reviewed outcome, **20 `drop` and 1 `fix`**, rather than the earlier all-drop assumption. Do not rewrite heavily corrupted content just to retain it.
- **Rule extraction:** All 11 sections have callable candidates. C3/C4/D4 use reviewed exclusions; F1 uses reviewed quarantine plus bounded Marathi private-field redaction. Below-threshold G1/B5 have no general medicine.
- **Gold harm tests:** The latest supplied `ind_mr_harm_results.md` (medicine SHA-256 prefix `f51c4fc18992`) passed all 11 rules and their combined file-order run on 99 gold records: 0 changed, 0 dropped, both Indic audits PASS. See the provenance limits and reproduction command above.
- **Effectiveness and clashes:** The reported individual and combined **gold-harm PASS** does not prove positive-label cleaning coverage, especially because all 11 rules changed zero gold documents. Measure recall and actual changes on reviewed, disease-positive pack documents. Check overlaps (especially C1/C5, A5/A6, B4/C1/C2), verify the actual harness execution order, and separately evaluate any revised combined pipeline.
- **Long context:** Preserve all 12 flagged long-context candidates. If a candidate also has C3 or other fixable defects, apply the documented cleanup while retaining the coherent long-form span; do not globally truncate.
- **Privacy:** For F1, publish **type and offset**, never private values in examples, logs, rule code, diffs or reports. Redact or exclude affected source text before release.
- **Indic text safety:** Keep ZWJ and ZWNJ, avoid NFKC and global deletion of spaces around matras/viramas. G1 repairs require precise contextual evidence; do not derive a generic rule from four documents.

**Interpretation:** Label review is complete. All 11 executable candidates and the combined run passed the fresh gold harm test. The four new manifests implement bounded reviewed exclusions/quarantine; pending contextual repairs and unseen-record privacy coverage remain unresolved.
