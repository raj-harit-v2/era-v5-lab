# Medicine sheet: code-rust (ranjanguddu)

Pack: `code-rust`, 500 documents, 2.32 M characters. 234 documents are `fix`, 13 are `drop`
(all 13 for `C2`, see Medicine 3), 253 are `clean`.

Codes found in the pack: `B3` 225, `B4` 25, `C2` 13, `F2` 4, `B2` 4, `B1` 3, `E2` 2, `A1` 1.
Three codes appear more than five times, so this sheet has three medicines.

## A note on the harm test

The official gold set is now in the repository: `teams/01-data-a/gold/code-rust_gold.csv`,
**234 documents** (`doc_id`, `reader_1`, `reader_2` — two independent readers). Every number
below is measured on it with `teams/01-data-a/tools/harm_test.py`. The limit for this gold set
is `max(1, floor(1% of 234))` = **2 documents** changed or dropped per rule.

Command (from the repo root), once per rule code:

```
python -I teams/01-data-a/tools/harm_test.py --pack code-rust.parquet \
  --gold teams/01-data-a/gold/code-rust_gold.csv \
  --rules diagnosis/submissions/code-rust/ranjanguddu/medicine.md --rule B3
```

| rule | changed | dropped | percent | limit | result |
|---|---|---|---|---|---|
| `B3` | 0 | 0 | 0.00% | 2 | **PASS** |
| `B4` | 0 | 0 | 0.00% | 2 | **PASS** |
| `C2` | 0 | 0 | 0.00% | 2 | **PASS** |

## Medicine 1

1. **Disease:** `B3` Ghost chat markers — **225 of 500 documents (45%)**.

   Every one of these documents starts with a wrapper line that the pack builder added, not
   the author. The line is `<reponame>NAME`, `<filename>PATH` or `<gh_stars>RANGE`, always at
   offset 0, and the code begins on the next line. Three examples:

   | `doc_id` | exact characters | offset |
   |---|---|---|
   | `e016447055203614` | `<gh_stars>1-10` | 0 |
   | `d1e5237063713aba` | `<filename>server/src/room/dto/response/join_room.dto.rs` | 0 |
   | `1b399017559a1439` | `<gh_stars>1000+` | 0 |

2. **Medicine:** drop the leading wrapper lines. Only lines **at the very start** of the
   document are removed, so the same words inside a string or a comment later in the file are
   left alone.

   ```python
   import re

   WRAPPER_LINE = re.compile(r"^[ \t]*<(?:reponame|filename|gh_stars)>[^\n]*\r?\n")

   def medicine_b3(text: str) -> str:
       """Remove the StarCoder wrapper lines at the top of the document."""
       lines = text.split("\n")
       i = 0
       while i < len(lines) and WRAPPER_LINE.match(lines[i] + "\n"):
           i += 1
       return "\n".join(lines[i:]) if i else text
   ```

3. **Action:** **fix**. The wrapper is a line the builder added; the document underneath is
   real Rust code and is worth keeping.

4. **Harm test:** on the official gold set (`code-rust_gold.csv`, 234 documents) the medicine
   **changes 0 documents and drops 0 documents = 0.00%**, limit 2 → **PASS**. The same 0.00%
   was measured earlier on my local 253-document clean set.

   Recall on my own labels: it changes **225 of 225** documents that I marked `B3`.

5. **Side effects:** the rule looks only at the first lines, so its only failure mode is a
   document that legitimately begins with a line like `<filename>...`. No document in my pack
   does (0 of 253 clean). A file that *documents* the wrapper format — for example a tokenizer
   that lists these markers — would be stripped if the marker happens to be the first line;
   the fix is to read the document before applying the medicine, which the label sheet does.

## Medicine 2

1. **Disease:** `B4` Unfilled placeholders — **25 of 500 documents (5%)**.

   The text still carries the tokens that an earlier anonymising pass left behind, or that a
   template left unfilled. The vocabulary is open-ended: `<NAME>`, `<EMAIL>`, `<PASSWORD>`,
   `<QUERY>`, `<EXPRESSION>`, `<FILE>`, `<GPIO>`, `<D3DLOCKED_RECT>`. Three examples:

   | `doc_id` | exact characters | offset |
   |---|---|---|
   | `7dcf53c66a82f309` | `<NAME>` | 22 |
   | `920d344679eb3387` | `<EMAIL>` | 182 |
   | `874d33cfab182d2e` | `<PASSWORD>` | 11779 |

2. **Medicine:** replace a bracketed all-capitals token with neutral text. The negative
   lookbehind is the important part: it skips a token that follows an identifier, which is
   where a Rust type argument sits (`Option<JSON>`), and keeps a token that stands on its own,
   which is where a placeholder sits.

   ```python
   import re

   PLACEHOLDER = re.compile(r"(?<![A-Za-z0-9_])<\s*[A-Z][A-Z0-9_]{1,30}\s*>")
   NEUTRAL = {"<NAME>": "Author", "<EMAIL>": "email@example.com", "<KEY>": "REDACTED",
              "<PASSWORD>": "REDACTED", "<TOKEN>": "REDACTED"}

   def medicine_b4(text: str) -> str:
       """Replace unfilled placeholders with neutral text."""
       return PLACEHOLDER.sub(
           lambda m: NEUTRAL.get(m.group(0).replace(" ", ""), "REDACTED"), text)
   ```

   The replacements are deliberately neutral: `email@example.com` is a reserved documentation
   domain, so the medicine never invents a real person's data.

3. **Action:** **fix**. The surrounding code is good; only the token is wrong.

4. **Harm test:** on the official gold set (`code-rust_gold.csv`, 234 documents) the medicine
   **changes 0 documents and drops 0 documents = 0.00%**, limit 2 → **PASS**.

   Recall on my own labels: it changes **22 of 25** documents that I marked `B4`.

   Without the lookbehind the same rule changes 1 of 253 gold documents (0.40%): `89e3fae6360038e6`
   contains `-> Option<JSON>`, a Rust type name and not a placeholder. The lookbehind removes
   that damage, which is why it is in the rule.

5. **Side effects:** three known failures.
   - The 3 documents the rule does not catch use template syntax instead of a bracketed token:
     `{{ name }}`, `{{ property }}`, `{{REPLACE}}` (`5dc99bbc98f31f6f`, `016bc22f87c65d9a`,
     `bdbb96ab384d09e0`). A rule for `{{ ... }}` would be a different medicine, and for a
     template engine such as `temply` that syntax is the language the crate implements, not a
     defect — those rows deserve a second look.
   - A placeholder used as a type argument (`Vec<NAME>`) is skipped by the lookbehind.
   - The replacement text is invented. It removes the token but does not restore the value
     that was removed, so the document stays unusable as an example of real code.

## Medicine 3

1. **Disease:** `C2` Repeated lines — **13 of 500 documents (2.6%)**.

   In this pack the repeated line is **structural Rust**, not spam. Three examples:

   | `doc_id` | the repeated line | count / lines |
   |---|---|---|
   | `f86e2e854b4328d0` | `#[allow(unused_mut)]` | 376 / 2555 |
   | `9773497d0c18080b` | `#[allow(unused_mut)]` | 153 / 1270 |
   | `856747c12b100481` | `register: ::vcell::VolatileCell<u32>,` | 23 / 207 |

2. **Medicine:** a detector, not a text edit.

   ```python
   from collections import Counter

   def c2_repeated_line(text: str, min_repeat: int = 20, min_share: float = 0.10) -> bool:
       """True if the document is dominated by one repeated line, else False."""
       lines = text.split("\n")
       counts = Counter(line.strip() for line in lines if len(line.strip()) >= 8)
       if not counts:
           return False
       line, count = counts.most_common(1)[0]
       if count >= min_repeat and count / max(1, len(lines)) >= min_share:
           return True
       return False
   ```

3. **Action:** **drop**, not fix. There is no safe line-level repair here: `#[allow(unused_mut)]`
   before each function is per-item, `unsafe {` and `register: ...` are structure. Deleting the
   repeats changes what the program means, and deleting all but one can stop it compiling. The
   honest action for a file whose bulk is one repeated structural line is to drop the file.
   The 13 rows for this code in `labels.csv` therefore carry `verdict=drop`. This costs 13 of
   500 documents (2.6%) of the pack.

4. **Harm test:** on the official gold set (`code-rust_gold.csv`, 234 documents) the medicine
   **changes 0 documents and drops 0 documents = 0.00%**, limit 2 → **PASS**. The only change
   made for the test is the return value: the detector returns `True` (drop) or `False` (keep)
   now, because `harm_test.py` rejects a tuple or `None` with `TypeError`. The detection and the
   thresholds (`min_repeat=20, min_share=0.10`) are unchanged. The table below was measured
   earlier on my local 253-document clean set, before the official gold set existed:

   | threshold | changes on gold set (253) | passes 1%? | catches my 13 `C2` rows |
   |---|---|---|---|
   | `min_repeat=10, min_share=0.03` | 7 = **2.77%** | **no** | 11 of 13 |
   | `min_repeat=10, min_share=0.05` | 1 = 0.40% | yes | 8 of 13 |
   | `min_repeat=20, min_share=0.10` | 0 = 0.00% | yes | 4 of 13 |
   | `min_repeat=20, min_share=0.20` | 0 = 0.00% | yes | 0 of 13 |

   The loose threshold that finds most of the documents fails the harm test (2.77%), because
   the clean documents it damages repeat lines for exactly the same structural reason. The
   threshold that passes finds only 4 of 13. I propose `min_repeat=20, min_share=0.10`: it
   drops 0 of 253 gold documents, and the documents it misses are the ones a reader must judge
   anyway.

5. **Side effects:** this medicine is the weakest of the three and it is worth saying why.
   "Repeated lines" separates good from bad badly in a code pack: `#[derive(Clone)]`,
   `#[inline(always)]`, `unsafe {`, `#[macro_export]` and `let mut cpu = get_cpu();` repeat in
   code that no one would call diseased, and `0, 0, 0, ...` in a numeric table
   (`df290f4014eeef57`, 12 of 85 lines) is closer to `E2` than to `C2`. The threshold above
   only drops the extreme tail. If a better rule is wanted, the signal is not the count of a
   repeated line but whether the repeated line carries information at all.
