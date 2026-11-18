# Rotation review: model card, Tokenizer row

**Date:** 17 Nov 2026

Week 3 rotation in the Release team. The Release lead wrote this review as cover, because no rotation pull request came for this row. This file reviews the Tokenizer row of `model_card_outline.md` (R1) and marks each claim that has no evidence (R2).

Checked against main at commit `8732384`.

The Tokenizer section has no text yet, so this review covers the current outline row and its evidence.

## R1: review of the Tokenizer row

The row says: "How the model splits text into pieces."
The owner team is Tokenizer. The status is empty. The Lead OK cell records an OK from the Tokenizer lead.

### What the evidence supports

- The frozen tokenizer is p1536, not C3. The Tokenizer lead confirmed these words in a [comment on #460](https://github.com/theschoolofai/era-v5-lab/pull/460#issuecomment-6945257605). The release is in `teams/03-tokenizer/release/README.md` ([#504](https://github.com/theschoolofai/era-v5-lab/pull/504)).
- TSAI used the same words in a [comment on #460](https://github.com/theschoolofai/era-v5-lab/pull/460#issuecomment-6909024067): the first shards use the frozen tokenizer p1536, not C3.
- TSAI approved one tokenizer number for public text: the eos ID, the token that marks the end of a document (`gate2.md`, [#443](https://github.com/theschoolofai/era-v5-lab/pull/443)). p1536 keeps the same eos ID ([#504](https://github.com/theschoolofai/era-v5-lab/pull/504), `release/README.md`).
- The release folder explains how to download the tokenizer and check it with `verify_release.py`.
- The Tokenizer lead confirmed the row in a [comment on #384](https://github.com/theschoolofai/era-v5-lab/pull/384#issuecomment-6829903858).
- The status "empty" is correct. No Tokenizer section text is in `teams/11-release/model_card/`.

### What the evidence does not support yet

- **Token IDs.** `TOKENIZER_CARD.md` says the token IDs are identical to C3, on lines 3 and 180. The release README says every C3 ID keeps its token, except a set of IDs that now hold new Indic merges ([#414](https://github.com/theschoolofai/era-v5-lab/pull/414)). [#504](https://github.com/theschoolofai/era-v5-lab/pull/504) explains "identical" as the special tokens being byte-for-byte the same as in C3. So the card most likely means the special-token IDs.
- **Freeze date.** `TOKENIZER_CARD.md` says TSAI froze p1536 on 15 Nov 2026. [#481](https://github.com/theschoolofai/era-v5-lab/pull/481), which Data B opened on 15 Nov 2026, also names a TSAI notice of that day. The release README says 16 Nov 2026, the day of the release in [#504](https://github.com/theschoolofai/era-v5-lab/pull/504). So the README may give the release date, not the freeze date. The Tokenizer team confirms.
- **Scores per language.** The scores in section 5 of `TOKENIZER_CARD.md` are for C3, and its model-side scores are still marked TODO. The p1536 scores in the release README have no TSAI approval for public text.
- **Other numbers.** The vocabulary size, the merges and the count of special tokens have no TSAI approval for public text.

### Suggestions for the owner team

1. Write the section from the release README, not from the C3 parts of the card.
2. Fix the mismatches in `TOKENIZER_CARD.md`. For the token IDs on lines 3 and 180, the likely fix is "the special-token IDs are identical". For the freeze date, confirm the date, and fix the card or the release README. Also check line 5, which still names the Gate 2 freeze of C3. The file size on line 11 also differs from the release README.
3. Write `[number: waiting for TSAI]` for every number that TSAI has not approved. The eos ID is approved.
4. Agree with Data A and Data B on the Languages row, which Tokenizer also owns, so that no fact appears in two sections.

## R2: claims and evidence

| # | Claim | Evidence | Result |
|---|---|---|---|
| 1 | The owner team is Tokenizer | `model_card_outline.md` on main | has evidence |
| 2 | The status is empty | No Tokenizer section text is on main | has evidence |
| 3 | The Tokenizer lead confirmed the row | [Comment on #384](https://github.com/theschoolofai/era-v5-lab/pull/384#issuecomment-6829903858) | has evidence |
| 4 | The frozen tokenizer is p1536, not C3 | [#504](https://github.com/theschoolofai/era-v5-lab/pull/504), `release/README.md`, [TSAI comment on #460](https://github.com/theschoolofai/era-v5-lab/pull/460#issuecomment-6909024067), [Tokenizer lead comment on #460](https://github.com/theschoolofai/era-v5-lab/pull/460#issuecomment-6945257605) | has evidence |
| 5 | Each token ID is the same as in C3 | The card (lines 3 and 180) and [#504](https://github.com/theschoolofai/era-v5-lab/pull/504) say yes, and #504 means the special tokens. The release README says a set of IDs changed ([#414](https://github.com/theschoolofai/era-v5-lab/pull/414)) | evidence conflicts |
| 6 | TSAI froze p1536 on a known date | The card and [#481](https://github.com/theschoolofai/era-v5-lab/pull/481) point to 15 Nov 2026. The release README gives 16 Nov 2026, the day of #504 | evidence conflicts |
| 7 | Scores per language for p1536 | The release README cites [#436](https://github.com/theschoolofai/era-v5-lab/pull/436). TSAI has not approved them for public text | no evidence for public text |
| 8 | TSAI approved the eos ID for public text, and p1536 keeps it | `gate2.md` ([#443](https://github.com/theschoolofai/era-v5-lab/pull/443)), [#504](https://github.com/theschoolofai/era-v5-lab/pull/504), `release/README.md` | has evidence |
| 9 | Any other number about the tokenizer | TSAI has approved none for public text | no evidence. Write `[number: waiting for TSAI]` |

## No evidence

- Claims 5 and 6: the Tokenizer team fixes the card or the release README, or confirms the right text.
- Claim 7: evidence comes when TSAI approves the scores.
- Claim 9: evidence comes when TSAI approves each number.
