# Medicine sheet: ind-bn-sangraha-v (pratik-2025)

Harm tests were run on the Bengali gold set `teams/02-data-b/gold/ind-bn-sangraha-v_gold.csv`:
50 documents from this pack, read as clean by two readers (aneeshads, pratik-2025).
A medicine fails if it changes or drops more than 1% of the gold set. With 50 documents,
one document is 2%, so a medicine passes only if it touches no gold document.

| Code | Action | Gold changed | Gold dropped | Result |
|---|---|---|---|---|
| D4 | drop | - | - | not testable (no automatic rule) |
| D3 | drop | 0 | 0 | PASS |
| C5 | drop | 0 | 0 | PASS |
| C3 | fix (v2) | 1 | 0 | FAIL (2%) |
| C1 | fix | 0 | 0 | PASS |
| G2 | fix (v2) | 0 | 0 | PASS (v1 failed: 23 changed) |
| C4 | drop | - | - | not testable (no automatic rule) |
| A3 | fix | 0 | 0 | PASS |
| C2 | fix | 0 | 0 | PASS |
| G1 | fix | 0 | 0 | PASS |
| D5 | keep | - | - | not testable (no automatic rule) |
| A2 | fix | 0 | 0 | PASS |
| D2 | drop | 0 | 0 | PASS |

## D4 — Bad machine translation
- Count: 189. Examples: 0ca18aa03db2ef77, 54442e06493e7751, 87c77e18093a596b
- Medicine: no regex can detect this. Score each document with a Bengali language-model fluency score (perplexity); flag documents above a threshold set on the gold set.
- Action: drop (only above the threshold)
- Harm test: not testable — no automatic rule yet.
- Side effects: formal, technical or old-style Bengali can score badly and be dropped wrongly.

## D3 — Mixed language
- Count: 109. Examples: 0ca18aa03db2ef77, 54442e06493e7751, 87c77e18093a596b
- Medicine: measure the share of Latin letters: `len(re.findall(r'[A-Za-z]', t)) / max(1, len(re.findall(r'[A-Za-zঀ-৿]', t)))`
- Action: keep (natural code-mixing); drop only if Latin share > 0.5
- Harm test: gold set 50 documents; changed 0, dropped 0 (0.0%) — PASS
- Side effects: news with many English names or terms may cross the threshold.

## C5 — Lists of keywords or links
- Count: 46. Examples: 017b4f09daad47e4, 0f79a07b7f39f669, 14c39215a007bbe9
- Medicine: drop if more than 60% of lines are short (< 4 words) and contain no sentence end (`।` `.` `?` `!`).
- Action: drop
- Harm test: gold set 50 documents; changed 0, dropped 0 (0.0%) — PASS
- Side effects: poems and real lists (recipes, ingredients) may be dropped.

## C3 — Truncated document
- Count: 41. Examples: f4b1f41a0f6d3a9e, b3f021daf03eebe5, eb3dc547426a3951
- Medicine (v2): flag only if the last line has 8 or more words and the text does not end with `।` `.` `?` `!` `"` or `)`; remove the incomplete last sentence.
- Action: fix
- Harm test: v1 (any ending without an end mark) changed 2 of 50 gold documents (4%) — FAIL. v2 changed 1 of 50 (2%; gold doc 6fb6f2b0a3cec116) — FAIL. Needs a narrower rule.
- Side effects: a long final line that is a heading, caption or list item without punctuation.

## C1 — Boilerplate
- Count: 39. Examples: 7035900113f62f27, 017b4f09daad47e4, 5c35ce7401e2ddd5
- Medicine: remove whole lines matching share/menu phrases, e.g. `^(শেয়ার করুন|Share|আরও পড়ুন|Read more|Follow us).*$`
- Action: fix
- Harm test: gold set 50 documents; changed 0, dropped 0 (0.0%) — PASS
- Side effects: a real sentence that starts with one of these phrases.

## G2 — Lost ZWJ or ZWNJ
- Count: 31. Examples: 4620e19b5836f03f, 8a252dfddf006bf5, f83b0bf24e9d2963
- Medicine (v2): at the start of a word only, `র্যা` → `র‍্যা` (ZWJ restored), as in র‍্যাব, র‍্যালি: `re.sub(r"(?<![ঀ-৿])র্যা", "র‍্যা", t)`
- Action: fix
- Harm test: v1 (every র্য) changed 23 of 50 gold documents (46%) — FAIL, because mid-word র্য (সূর্য, কার্য, কার্যালয়) is correct spelling. v2 changed 0, dropped 0 (0.0%) — PASS
- Side effects: a borrowed word that needs ZWJ mid-word is missed.

## C4 — Two documents joined
- Count: 15. Examples: f0e9d668c4268ff2, 7160f28b914f8629, f4b1f41a0f6d3a9e
- Medicine: no reliable rule; flag documents with a sharp topic change (low similarity between halves) for review.
- Action: drop (flagged only)
- Harm test: not testable — no automatic rule yet.
- Side effects: long articles that change topic naturally.

## A3 — Mojibake
- Count: 14. Examples: 5584556a2ea2dcfd, 975e9170d8259094, 1530194906022e0e
- Medicine: detect `à¦|à§|Ã|â€`; try `t.encode('latin-1').decode('utf-8')` on the broken span.
- Action: fix if the repair succeeds, else drop
- Harm test: gold set 50 documents; changed 0, dropped 0 (0.0%) — PASS
- Side effects: real text containing accented Latin letters.

## C2 — Repeated lines
- Count: 10. Examples: 44f51067574b2556, b0d8affd2329469d, 1da19ac48860fb47
- Medicine: keep only the first copy of any line (longer than 20 characters) that appears 3 or more times.
- Action: fix
- Harm test: gold set 50 documents; changed 0, dropped 0 (0.0%) — PASS
- Side effects: songs and poems with a repeated chorus.

## G1 — Cut at the vowel sign
- Count: 9. Examples: 251870ed41c8f19c, 32029c674c355e1b, 53ad1531ea630e8c
- Medicine: remove a space before a Bengali vowel sign or virama: `re.sub(r' ([া-্ৗ])', r'\1', t)`
- Action: fix
- Harm test: gold set 50 documents; changed 0, dropped 0 (0.0%) — PASS
- Side effects: very rare; a deliberately spaced sign in teaching text.

## D5 — Translationese
- Count: 8. Examples: b0c095487dd72b87, 22a785c77561bc0e, 63a1a908974b93be
- Medicine: no rule; same fluency score as D4.
- Action: keep (low harm)
- Harm test: not testable — no automatic rule yet.
- Side effects: same as D4.

## A2 — Control characters
- Count: 8. Examples: f4b1f41a0f6d3a9e, 2d21cfd2fc5a133f, 4620e19b5836f03f
- Medicine: `re.sub(r'[\x00-\x08\x0B-\x1F\x7F-\x9F]', '', t)` (removes carriage return \r and other control characters; keeps tab and newline)
- Action: fix
- Harm test: gold set 50 documents; changed 0, dropped 0 (0.0%) — PASS
- Side effects: none expected for prose.

## D2 — Romanised Bengali
- Count: 6. Examples: aecb9893b814c81f, a3a0a3d543d77afe, cbe94742890797f9
- Medicine: drop if Bengali-script share < 20% and a romanised-Bengali word list matches (e.g. ami, tumi, kemon, achhe).
- Action: drop
- Harm test: gold set 50 documents; changed 0, dropped 0 (0.0%) — PASS
- Side effects: English documents that happen to contain those words.
