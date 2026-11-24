# Rotation R1 and R2: Telugu shard `ind-te-sangraha-v` — auditor varshith2000

Closes #533. R1 and R2 complete: the code-point checks and the full 50-document reader pass are
done; findings and final summary below. Codes from `diagnosis/DISEASES.md`.

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
| `ab9fe3bc8182b406` | A6 | 896 | `U+0C4D U+0020 U+0028 U+0045 U+0056 U+004D U+0C32` | Latin letters inside a Telugu word |
| `49c6df1e08705feb` | G1 | 3024 | `U+0C30 U+0C3E U+003E U+0C4D U+0C2F U+0C2A U+0C4D` | virama right after `>`; **source, not cleaning** — identical in the raw sample v0 part (reviewer-checked) |
| `84626d9f75147b0d` | G1 | 1534 | `U+0C41 U+0020 U+0027 U+0C4D U+0C2D U+0C37 U+0C23` | virama right after an apostrophe; **source, not cleaning** — identical in the raw sample v0 part (reviewer-checked) |

### From the reader pass

| doc_id | code | offset | hex dump | note |
| --- | --- | --- | --- | --- |
| `0cce98c8136212f3` | G1 | 97 | `U+0C4D U+0C2F U+0C3E U+0020 U+0C2F U+0C2E U+0C41` | space inside a word, right after a vowel sign — the word reads split in two; 6–8 further instances of the same signature in this document; **source, not cleaning** — all 71 "vowel sign, space, letter" places in this document are in the raw sample v0 part too (reviewer-checked) |
| `85c371eab86e00d1` | D3 | 1021 | `U+000A U+0020 U+0905 U+092F U+094B U+0927 U+094D` | Devanagari (Hindi) run start; mixed language, labelled not judged (DISEASES.md D3) |
| `85c371eab86e00d1` | D3 | 1075 | `U+0061 U+0020 U+0915 U+0947 U+0020 U+0938 U+094D` | same pattern |
| `85c371eab86e00d1` | D3 | 1146 | `U+0069 U+0020 U+0915 U+0940 U+0020 U+0924 U+093E` | same pattern |
| `85c371eab86e00d1` | D3 | 1189 | `U+0050 U+0020 U+0915 U+093E U+0930 U+094D U+092F` | same pattern |
| `85c371eab86e00d1` | D3 | 1258 | `U+000A U+0020 U+092F U+094B U+0917 U+0940 U+0020` | same pattern; the five runs are ~15% of the document; the pipeline `lang_label` for this document is `te` (relevant to #531) |
| `b23ac5e37e0db14b` | D3 | 0 | `U+0044 U+006F U+006E U+0027 U+0074 U+0020` | Latin (English) run at document start; 7 runs total, ~5% of the document (76.7% Telugu); mixed language, labelled not judged |
| `b23ac5e37e0db14b` | D3 | 191 | `U+002D U+0020 U+0041 U+0075 U+0074 U+006F U+006D U+006F` | Latin run, 4 words |
| `b23ac5e37e0db14b` | D3 | 286 | `U+002D U+0020 U+0046 U+0069 U+006E U+0061 U+006E U+0063` | Latin run, 3 words |
| `b23ac5e37e0db14b` | D3 | 371 | `U+002E U+000A U+004E U+0069 U+0068 U+0061 U+0072 U+0069` | Latin run, 3 words (romanised-looking names) |
| `b23ac5e37e0db14b` | D3 | 468 | `U+0021 U+000A U+0052 U+0061 U+0074 U+0068 U+0069 U+006B` | Latin run, 2 words (romanised-looking name) |
| `b23ac5e37e0db14b` | D3 | 1410 | `U+0035 U+0020 U+0044 U+0061 U+0079 U+0073 U+0020 U+0043` | Latin run, 2 words |
| `b23ac5e37e0db14b` | D3 | 1910 | `U+0036 U+0020 U+0044 U+0061 U+0079 U+0073 U+0020 U+0043` | Latin run, 2 words |

## Summary — final

- Documents checked by code points: 50 of 50. Documents read: 50 of 50; the remaining 25 documents
  produced no further recorded findings.
- Findings: G1 3 rows + 6–8 same-signature instances (1 document); A6 1; D3 12 (2 documents:
  Hindi runs ×5, Latin/English runs ×7); G2 0; A1 0; A4 0.
- Dominant reader pattern: `U+0020` inserted inside words after a matra — invisible to the
  code-point checks (a matra followed by a space is also every legitimate word boundary), which is
  why the reader pass carries it.
- Joiners: no ZWJ/ZWNJ damage observed (G2 = 0), consistent with #523 for this pack.
- Per the PR review (19 Nov): the three G1 documents above were checked against the raw sample v0
  part and are identical there — **source damage, not cleaning** — so they are kept out of the
  Gate 3 count of cleaning damage.

## Status

Complete. R1 (50-document reader pass, code-point checks) and R2 (findings with document IDs,
offsets and hex dumps, final summary) are done. The dominant word-split pattern is source-side;
no cleaning damage attributable to clean.py or p1536 was observed in this sample.
