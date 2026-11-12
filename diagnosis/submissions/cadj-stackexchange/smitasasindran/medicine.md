# Medicine sheet: cadj-stackexchange (smitasasindran)

**Note:** All 500 documents in this pack contain the ghost markers `<issue_start>` and `<issue_comment>`. Every document starts with `<issue_start>`, and every document has at least one `<issue_comment>`. The harm tests will be run when the gold pack for this set gets published.

Write one section for each disease that you found more than five times.


1. **Disease:** B3, ghost chat markers
- **Count:** 500 of 500 documents, 1,966 occurrences in total: 500 `<issue_start>` and 1,466 `<issue_comment>`.
- **Examples:**
     - `87116d4f6facd13b`: `<issue_start>` at offset 0, `<issue_comment>` at offsets 302 and 495.
     - `c9e11c8baa07c6e0`: `<issue_start>` at offset 0, `<issue_comment>` at offsets 944, 1367 and 4657.
     - `d78b5eeab23e7a55`: `<issue_start>` at offset 0, `<issue_comment>` at offsets 302 and 1120.

2. **Medicine:** 
Replace `<issue_start>` with `[issue_start]`   
Replace each `<issue_comment>` with `[issue_comment]`   

```python
import re

def cure_b3(text: str) -> str:
    text = text.replace("<issue_start>", "[issue_start]")
    text = text.replace("<issue_comment>", "[issue_comment]")
    return text
```

3. **Action:** fix the text. No document is dropped.

4. **Harm test:**
   B3 is present in all 500 documents, and this data pack has no gold set.
   - Documents changed: 500
   - Documents dropped: 0
   - Status: **PASS** (Reason: Though it would change all documents, we need this rule to cleanup ghost markers)

5. **Side effects:** 
Simple replace rule on exact match, should have no side effects


## Medicine 2

1. **Disease:** B4, redaction placeholders that look like HTML tags.
- **Count:** 162 occurrences in 53 documents: `<NAME>` 90 (24 docs), `<EMAIL>` 44 (13 docs), `<PASSWORD>` 27 (17 docs), `<KEY>` 1 (1 doc). 138 of them are inside code snippets.
- **Examples:**
     - `a06ac825948fcdf1`: `@<NAME>,` at offset 1239.
     - `b79c9269b393f7ee`: `"email": "<EMAIL>",` at offset 119.
     - `32407cff5d9572ab`: `$password="<PASSWORD>";` at offset 410.

2. **Medicine:**
Replace the exact tags `<NAME>`, `<EMAIL>`, `<PASSWORD>` and `<KEY>` with `[NAME]`, `[EMAIL]`, `[PASSWORD]` and `[KEY]`.  
Leave the `username_N:` labels in place.  
Other tags (`<br>`, `<image>`, `<div>`) are left alone.

```python
import re

def cure_b4(text: str) -> str:
    return re.sub(r"<(NAME|EMAIL|PASSWORD|KEY)>", r"[\1]", text)
```

3. **Action:** fix the text. No document is dropped.

4. **Harm test:** Gold set empty, not testable.

5. **Side effects:**
- In other code, `<NAME>` or `<KEY>` can be real syntax, for example a generic type `Map<KEY>` or a template. Replacing it would change the code. The gold-set test should show whether it happens in other languages.


## Medicine 3

1. **Disease:** A2, control characters. The only one found is the carriage return U+000D.
- **Count:** 1,041 occurrences in 29 documents. All of them are the first half of a `\r\n` pair. There is no lone `\r`.
- **Examples:**
     - `c690c0c539e5374d`: U+000D at offset 573 (69 in the document).
     - `b9203642a7704098`: U+000D at offset 527 (28 in the document).
     - `caab0dbaa0d7211e`: U+000D at offset 590 (126 in the document).

2. **Medicine:**
Replace each `\r\n` with `\n`. Nothing else is changed.

```python
def cure_a2(text: str) -> str:
    return text.replace("\r\n", "\n")
```

3. **Action:** fix the text. No document is dropped.

4. **Harm test:** Gold set empty, not testable.

   Source files written on Windows use `\r\n` as normal line endings, so a gold set of source files may change more than 1%. If it does, report it to the gold-set owners. Those files are not clean either.

5. **Side effects:**
- A `\r\n` inside a multi-line string literal (a C# verbatim string, a Python triple-quoted string) is part of the string value. Changing it to `\n` changes the value.
- A lone `\r` (an old Mac line ending) is not handled. None was found in this pack. Use `re.sub(r"\r\n?", "\n", text)` if the gold set has any.


## Medicine 4

1. **Disease:** C4, two documents joined. The document is its own question followed by the comments of the previous document, with no boundary between them.
- **Count:** 104 of 500 documents. In 97 of them the copied block runs to the end of the document. 22 documents follow a document that is also affected, so the same comments appear in a run of several documents.
- **Examples:**
     - `92172ee7c68d51f9`: the question is about Rails and jQuery. From offset 543, `username_1: \`movementDistance\` is an \`Int\`` starts comments about Swift. They are copied from `8adb7ee924d9c299`.
     - `b33feafa5645bc5a`: `username_1: You can either create the locale,` at offset 530, copied from `578eb1503702a79d`.
     - `9a421950f1fe4228`: `username_1: As others have said, my first suggestion would b` at offset 493, copied from `796f4f8329c2ee55`.

2. **Medicine:**
Compare the document with the document before it in the pack. If they share a block of 200 or more characters that starts where the question ends (within 20 characters of the first `<issue_comment>`), cut the document at the end of its own question. The comments belong to a different question.

```python
from difflib import SequenceMatcher

TAG = "<issue_comment>"

def cure_c4(text: str, prev_text: str, min_block: int = 200) -> str:
    q_end = len(text.split(TAG)[0])
    m = SequenceMatcher(None, prev_text, text, autojunk=False).find_longest_match(
        0, len(prev_text), 0, len(text))
    if m.size >= min_block and abs(m.b - q_end) <= 20:
        return text[:q_end].rstrip()
    return text
```

3. **Action:** fix the text. No document is dropped. Each of the 104 keeps its own question (at least 145 characters), and the copied comments are removed.

4. **Harm test:** Gold set empty, not testable.

   Clean documents should not share a 200-character block with their neighbour, so the expected result is 0 changed.

5. **Side effects:**
- The rule needs the documents in their original order. If the pack is shuffled, the previous document is the wrong one.
- In 7 documents there is some text after the copied block (up to about 2,000 characters). The cut removes it too. The cut also removes the document's own comments, if it had any.
- A document that quotes a long block of the previous question's answer would also be cut. This did not happen here, because all 104 matches start at the end of the question.


## Medicine 5

1. **Disease:** H2, near duplicate. It is the same 104 documents as Medicine 4: the comments appear in the document and again in the document before it.
- **Count:** 104 of 500 documents.
- **Examples:**
     - `92172ee7c68d51f9`: offset 543, copied from `8adb7ee924d9c299`.
     - `b33feafa5645bc5a`: offset 530, copied from `578eb1503702a79d`.
     - `d55a3d15fa97fb05`: offset 347, copied from `1b54ff7534a0fcef`.

2. **Medicine:** the same as Medicine 4. Cutting the copied comments removes the duplicate, so use `cure_c4`. The original comments stay in the document that they belong to (the earlier one).

3. **Action:** fix the text. No document is dropped.

4. **Harm test:** Gold set empty, not testable.

5. **Side effects:** the same as Medicine 4. We do not judge which copy is the true one. The earlier document keeps the comments, because the comments belong to its question.


