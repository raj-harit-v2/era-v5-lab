# ERA V5 Lab: Gate 2 update (draft)

**Date:** 14 Nov 2026
**Period:** 1 Nov to 14 Nov 2026

[A short text about the lab at this gate. Release writes it after TSAI decides.]

## Decisions

| Decision | Team that proposed it | Decision text |
|---|---|---|
| Freeze the tokenizer | Tokenizer | [waiting for TSAI] |
| KE2 | KE2 | [waiting for TSAI] |
| First model configuration: attention type, number of experts and optimizer | Architecture | [waiting for TSAI] |
| Share of Indic text in its own script, and the limit on Indic text in Latin script | Data B | [waiting for TSAI] |
| Duplicate removal, source priority list and the updated data spec | Data A | [waiting for TSAI] |
| Data mix for supervised fine-tuning | Post-training | [waiting for TSAI] |
| Bit widths for the smaller versions of the model | Quantization | [waiting for TSAI] |

## Next

[One sentence about the next steps. No dates or results without TSAI approval.]

---

## Review record (remove this section before publishing)

This record is public, like the rest of the pull request. Put only public facts in it: yes or no, and links to
public pull requests. Never link to the CAP chat. Chat links are internal.

How to fill it:

1. Each team sends its proposal by the time TSAI set. Add the public pull request of the proposal below.
2. After TSAI decides, write each decision in the words that TSAI approves.
3. The lead of each team gives an OK on the text about their decision.
4. Write `[number: waiting for TSAI]` for any number that TSAI has not approved yet.
5. Run `python teams/11-release/style/check_style.py <this file> --numbers` and clear every error.
6. Release then copies the approved text to `updates/gate2.md`.

| Team | Proposal pull request | Lead OK |
|---|---|---|
| Tokenizer | | no |
| KE2 | | no |
| Architecture | | no |
| Data B | | no |
| Data A | | no |
| Post-training | | no |
| Quantization | | no |

- [x] `check_style.py` gives 0 errors
- [ ] Every number in the text has TSAI approval
- [ ] The text names teams only, and no person
- [ ] Nothing from the internal list in `public_internal.md`
- [ ] No `[waiting for TSAI]` left in the text
- [ ] A team member commented on this pull request
- [ ] TSAI approved on: [DD Mon YYYY]
- [ ] Merged after TSAI approved
