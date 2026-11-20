# ERA V5 Lab: Gate 3 update

**Date:** 21 Nov 2026
**Period:** 15 Nov to 21 Nov 2026

At this gate, TSAI reviewed the first dry run, the first data shards and the public text for the dashboard. Each
decision uses the words that TSAI approved.

## The first dry run

A dry run is a short test of the whole training setup before the main training run.

TSAI ran the first dry run with the training setup from Architecture and the frozen tokenizer p1536
([#475](https://github.com/theschoolofai/era-v5-lab/pull/475)). The run finished every planned training step. The loss
had no invalid values, and the run saved a final checkpoint. Scores: [number: waiting for TSAI]

## The first data shards

Shards are files that store token IDs, preserve whole documents and mark each document's end. Each shard has a
manifest and a quality report. Data A defined the shard format and tested it on a sample shard
([#358](https://github.com/theschoolofai/era-v5-lab/pull/358), [#373](https://github.com/theschoolofai/era-v5-lab/pull/373)).
The lab produced the first 41 shards from a sample of the lab's data, using the frozen tokenizer p1536, not C3.

## Decisions

| Decision | Team that proposed it | Decision text |
|---|---|---|
| The tokenizer for training | Tokenizer | The frozen tokenizer is p1536, not C3. |
| Bit widths for the smaller versions of the model | Quantization | [waiting for TSAI] |
| Share of Indic text in its own script, and the limit on Indic text in Latin script | Data B | The Indic share in its own script is 8% of every batch. The limit on romanised Indic text is 1% of tokens per language (a ceiling). |
| The data mix for the first training weeks, and the translated languages in it | Data B | [waiting for TSAI] |
| The learning rate schedule and the context length for each phase | Architecture | [waiting for TSAI] |
| The parallel layout for the training run, and the kernel changes for dry run 2 | Infrastructure, Performance | [waiting for TSAI] |
| The evaluation schedule for the training run | Evaluation | [waiting for TSAI] |
| SFT data v1 and RL data v1 | Post-training | [waiting for TSAI] |
| The public dashboard panels and their text | Monitoring, Release | [waiting for TSAI] |
| The serving stack for the public demo | Quantization | [waiting for TSAI] |

Short forms: p1536 and C3 are names of tokenizer candidates. Romanised Indic text is Indic text written in Latin script. SFT means supervised fine-tuning. RL means reinforcement learning.

## Next

Next, the lab prepares the second dry run, and Monitoring publishes the dashboard with the text that TSAI approves.

---

## Review record (remove this section before publishing)

This record is public, like the rest of the pull request. Put only public facts in it: yes or no, and links to
public pull requests. Never link to the CAP chat. Chat links are internal.

How to fill it:

1. Infrastructure sends the summary of the first dry run. Data A sends the text about the first shards.
2. Paste each text above. Edit it only for style, and send the edit back to the writer.
3. After TSAI decides, write each decision in the words that TSAI approves. Remove a row if TSAI does not decide it
   at this gate, and add a row for each other decision that TSAI makes.
4. The lead of each team gives an OK on the text about their team.
5. Write `[number: waiting for TSAI]` for any number that TSAI has not approved yet.
6. Run `python teams/11-release/style/check_style.py <this file> --numbers` and clear every error.
7. TSAI approves this pull request before the G11 lead merges it.

| Part | Team | Source | Text received | Lead OK |
|---|---|---|---|---|
| The first dry run | Architecture | [#475](https://github.com/theschoolofai/era-v5-lab/pull/475) and the TSAI comment on it (Infrastructure: no separate summary needed) | draft by Release from #475, confirmed by Architecture | yes |
| The first data shards | Data A | [#358](https://github.com/theschoolofai/era-v5-lab/pull/358), [#373](https://github.com/theschoolofai/era-v5-lab/pull/373), first 41 shards: TSAI comment on this pull request | text by Data A on this pull request, style edits confirmed by Data A | yes |
| Tokenizer for training (p1536 in place of C3) | Tokenizer | [#504](https://github.com/theschoolofai/era-v5-lab/pull/504) | TSAI words on this pull request, confirmed by Tokenizer | yes |
| Bit widths (moved from Gate 2) | Quantization | [#221](https://github.com/theschoolofai/era-v5-lab/pull/221) | no | no |
| Indic share (from Gate 2) | Data B | [#400](https://github.com/theschoolofai/era-v5-lab/pull/400), split by language in [#522](https://github.com/theschoolofai/era-v5-lab/pull/522) | TSAI numbers on this pull request | yes |
| Data mix and translated languages | Data B | | no | no |
| Learning rate schedule and context length | Architecture | | no | no |
| Parallel layout and kernel changes | Infrastructure, Performance | | no | no |
| Evaluation schedule | Evaluation | | no | no |
| SFT data v1 and RL data v1 | Post-training | [#524](https://github.com/theschoolofai/era-v5-lab/pull/524) | no | no |
| Public dashboard panels and text | Monitoring, Release | Panels: [#495](https://github.com/theschoolofai/era-v5-lab/pull/495). Text: [#598](https://github.com/theschoolofai/era-v5-lab/pull/598). Monitoring applied the text, merged: [#629](https://github.com/theschoolofai/era-v5-lab/pull/629) | text by Release, merged by TSAI in #598 | Monitoring: yes, [approval on #629](https://github.com/theschoolofai/era-v5-lab/pull/629#pullrequestreview-5967977324) |
| Serving stack for the public demo | Quantization | | no | no |

- [ ] `check_style.py` gives 0 errors
- [ ] Every number in the text has TSAI approval
- [ ] The text names teams only, and no person
- [ ] Nothing from the internal list in `public_internal.md`
- [ ] No `[waiting for TSAI]` left in the text
- [x] A team member commented on this pull request
- [ ] TSAI approved on: [DD Mon YYYY]
- [ ] Merged after TSAI approved
