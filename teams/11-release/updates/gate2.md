# ERA V5 Lab: Gate 2 update

**Date:** 14 Nov 2026
**Period:** 1 Nov to 14 Nov 2026

At this gate, TSAI reviewed the proposals from the teams below. Each decision uses the words that TSAI approved.

## Decisions

| Decision | Team that proposed it | Decision text |
|---|---|---|
| Freeze the tokenizer | Tokenizer | Freeze C3 (sample v0). eos is id 130822 ([#407](https://github.com/theschoolofai/era-v5-lab/pull/407)). After the freeze, token IDs stay fixed. TSAI approves each later fix. |
| KE2 | KE2 | Accept the KE2 validation of C3 ([#372](https://github.com/theschoolofai/era-v5-lab/pull/372)). Align the KE2 special-token map to eos id 130822. |
| First model configuration: attention type, number of experts, optimizer and learning rate | Architecture | Muon optimizer. Keep the v0 attention. 16 routed experts plus 1 shared expert, top-2. Learning rate 1e-3 stays provisional. |
| Share of Indic text in its own script, and the limit on Indic text in Latin script | Data B | Rerun [#400](https://github.com/theschoolofai/era-v5-lab/pull/400) with C3 this week. TSAI sets the share from that table. |
| Duplicate removal, source priority list and the updated data spec | Data A | One spec v1.1. Cleaner [#244](https://github.com/theschoolofai/era-v5-lab/pull/244) is merged and ran on sample v0. Run the [#255](https://github.com/theschoolofai/era-v5-lab/pull/255) dedup design on the cleaned sample. |
| Data mix for supervised fine-tuning | Post-training | [#391](https://github.com/theschoolofai/era-v5-lab/pull/391) is SFT mix v1. Week 3 adds strong SFT tests. Deletion Tuning (potential candidate). The Post-training team first reads the method, writes the code and tests it against full fine-tuning. TSAI decides after that. |
| Bit widths for the smaller versions of the model | Quantization | No evidence yet. This decision moves to Gate 3. |

Short forms: C3 is the name of the chosen tokenizer candidate. eos is the token that marks the end of a document. KE2 is the lab team that tests its embedding method on the lab's tokenizer. SFT means supervised fine-tuning. Dedup means duplicate removal. Top-2 means that each token goes to two of the routed experts.

## Next

Next, the lab runs the first dry run and prepares the first data shards, and Release writes the public text for the dashboard.

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
6. TSAI approves this pull request before the G11 lead merges it.

| Team | Proposal pull request | Lead OK |
|---|---|---|
| Tokenizer | [#340](https://github.com/theschoolofai/era-v5-lab/pull/340) | yes |
| KE2 | [#349](https://github.com/theschoolofai/era-v5-lab/pull/349) | yes |
| Architecture | [#374](https://github.com/theschoolofai/era-v5-lab/pull/374) | yes |
| Data B | [#327](https://github.com/theschoolofai/era-v5-lab/pull/327), [#383](https://github.com/theschoolofai/era-v5-lab/pull/383), [#400](https://github.com/theschoolofai/era-v5-lab/pull/400) | yes |
| Data A | [#255](https://github.com/theschoolofai/era-v5-lab/pull/255), [#365](https://github.com/theschoolofai/era-v5-lab/pull/365) | yes |
| Post-training | [#312](https://github.com/theschoolofai/era-v5-lab/pull/312), [#391](https://github.com/theschoolofai/era-v5-lab/pull/391) | yes |
| Quantization | [#221](https://github.com/theschoolofai/era-v5-lab/pull/221) | yes |

- [x] `check_style.py` gives 0 errors
- [x] Every number in the text has TSAI approval
- [x] The text names teams only, and no person
- [x] Nothing from the internal list in `public_internal.md`
- [x] No `[waiting for TSAI]` left in the text
- [x] A team member commented on this pull request
- [x] TSAI approved on: 15 Nov 2026
- [ ] Merged after TSAI approved
