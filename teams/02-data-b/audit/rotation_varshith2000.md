# Rotation R1 and R2: Telugu shard `ind-te-sangraha-v` — auditor varshith2000

Closes #533. R1 in progress: the 50-document read continues through 19 Nov; findings so far are
recorded below and this file will be updated with the remaining rows and the final summary by
Fri 20 Nov. Codes from `diagnosis/DISEASES.md`.

## Method

- Shard: `shards/ind-te-sangraha-v/train/ind-te-sangraha-v-train-000000` — 8,593 documents,
  matching the kept count in #523. Index/data consistency checked (last offset × uint32 = exact
  `.bin` size).
- Tokenizer: frozen p1536, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`,
  verified before use.
- Draw: the issue #533 snippet, `DAY = 4`, 50 documents written to `read_D4/` (kept out of git).
  Reproducible: `random.Random(4).sample(range(8593), 50)` over the shard's document order.
- Code-point checks: one batched regex pass per code over the 50 cleaned texts (G1, G2, A1, A4,
  A6); no Python loop over tokens. A6 matches letters only (danda U+0964/U+0965 excluded as
  punctuation). Reader pass over the drawn documents for damage the code points cannot show.

Command and output (TSAI speed rule):

```
python check_r1.py read_D4
documents checked: 50 (read_D4)
G1: 2
G2: 0
A1: 0
A4: 0
A6: 1
total findings: 3 -> read_D4_findings.tsv
wall time: 0.34 s
```

## Findings

IDs, codes, offsets and hex dumps only (the finding and two or three code points each side).

### From the code-point scan

| doc_id | code | offset | hex dump | note |
| --- | --- | --- | --- | --- |
| `ab9fe3bc8182b406` | A6 | 896 | `U+0C4D U+0020 U+0028 U+0045 U+0056 U+004D U+0C32` | Latin letters inside a Telugu word (reader confirmation pending) |
| `49c6df1e08705feb` | G1 | 3024 | `U+0C30 U+0C3E U+003E U+0C4D U+0C2F U+0C2A U+0C4D` | virama right after `>` — a stripped markup artifact suspected |
| `84626d9f75147b0d` | G1 | 1534 | `U+0C41 U+0020 U+0027 U+0C4D U+0C2D U+0C37 U+0C23` | virama right after an apostrophe — consonant before it suspected lost |

### From the reader pass (in progress)

| doc_id | code | offset | hex dump | note |
| --- | --- | --- | --- | --- |
| `0cce98c8136212f3` | G1 | 97 | `U+0C4D U+0C2F U+0C3E U+0020 U+0C2F U+0C2E U+0C41` | space inside a word, right after a vowel sign — the word reads split in two; 6–8 further instances of the same signature in this document, offsets to follow in the next update |
| `85c371eab86e00d1` | D3 | 1021 | `U+000A U+0020 U+0905 U+092F U+094B U+0927 U+094D` | Devanagari (Hindi) run start; mixed language, labelled not judged (DISEASES.md D3) |
| `85c371eab86e00d1` | D3 | 1075 | `U+0061 U+0020 U+0915 U+0947 U+0020 U+0938 U+094D` | same pattern |
| `85c371eab86e00d1` | D3 | 1146 | `U+0069 U+0020 U+0915 U+0940 U+0020 U+0924 U+093E` | same pattern |
| `85c371eab86e00d1` | D3 | 1189 | `U+0050 U+0020 U+0915 U+093E U+0930 U+094D U+092F` | same pattern |
| `85c371eab86e00d1` | D3 | 1258 | `U+000A U+0020 U+092F U+094B U+0917 U+0940 U+0020` | same pattern; the five runs are ~15% of the document; the pipeline `lang_label` for this document is `te` (relevant to #531) |

## Summary — to date (R1 reading continues)

- Documents checked by code points: 50 of 50. Documents read so far: 25 of 50 (continuing
  19–20 Nov); no further findings recorded from the documents read so far beyond those below.
- Findings so far: G1 3 rows + 6–8 same-signature instances pending offsets (1 document); A6 1;
  D3 5 (1 document); G2 0; A1 0; A4 0.
- Dominant reader pattern so far: `U+0020` inserted inside words after a matra — invisible to the
  code-point checks (a matra followed by a space is also every legitimate word boundary), which is
  why the reader pass carries it.
- Joiners: no ZWJ/ZWNJ damage observed (G2 = 0), consistent with #523 for this pack.

## Status

R1 reading halfway (25 of 50). To come by Fri 20 Nov: the remaining 25 documents' rows, the
pending offsets for `0cce98c8136212f3`, reader confirmation of the three scan rows, and the final
summary.
