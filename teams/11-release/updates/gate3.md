# ERA V5 Lab: Gate 3 update

**Date:** 21 Nov 2026
**Period:** 15 Nov to 21 Nov 2026

At this gate, TSAI reviewed the first dry run, the first data shards and the public text for the dashboard. Each
decision uses the words that TSAI approved.

## The first dry run

A dry run is a short test of the whole training setup before the main training run.

TSAI ran the first dry run with the training setup from Architecture and the frozen tokenizer p1536
([#475](https://github.com/theschoolofai/era-v5-lab/pull/475)). The run finished every planned training step. The loss
had no invalid values, and the run saved a final checkpoint.

## The first data shards

Shards are files that store token IDs, preserve whole documents and mark each document's end. Each shard has a
manifest and a quality report. Data A defined the shard format and tested it on a sample shard
([#358](https://github.com/theschoolofai/era-v5-lab/pull/358), [#373](https://github.com/theschoolofai/era-v5-lab/pull/373)).
The lab produced the first 41 shards from a sample of the lab's data, using the frozen tokenizer p1536, not C3.

## Decisions

| Decision | Team that proposed it | Decision text |
|---|---|---|
| The first dry run | Architecture, Infrastructure | Go. The full run finished, the checkpoint is good, and a restore from the checkpoint matched bit for bit. |
| The tokenizer for training | Tokenizer | The frozen tokenizer is p1536, not C3. |
| Data mix and Indic share | Data A, Data B | The Indic share in its own script is fixed at 8% of every batch. The limit on romanised Indic text is 1% of tokens per language (a ceiling). |
| The learning rate | Architecture | The learning rate of 1e-3 is now final. The learning rate for the Muon optimizer is [number: waiting for TSAI]. |
| Model layout and size | Architecture | Architecture sets the exact model size once the lab knows the real token count of its first full corpus. |
| Attention and experts | Architecture | Keep the v0 attention, and 16 routed experts plus 1 shared expert, top-2. A test with more experts did worse. |
| The output head | KE2 | The model uses the KE2 output head, not the dense untied head that the first dry run used. This replaces the earlier choice of the dense untied head. |
| Public dashboard panels and monitoring | Monitoring | TSAI accepted the public dashboard panels and the monitoring. |

Short forms: p1536 and C3 are names of tokenizer candidates. Romanised Indic text is Indic text written in Latin script.
KE2 is the lab team that tests its embedding method on the lab's tokenizer. The output head is the last part of the
model, which scores each token as the next token. A dense untied head is the standard output head.

## Next

Next, the lab prepares the second dry run, and Architecture adds the KE2 output head to the training code. TSAI decides the evaluation schedule, the tuning method after the main
training, and serving and quantization at a later gate.

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
| The first dry run (text) | Architecture | [#475](https://github.com/theschoolofai/era-v5-lab/pull/475) and the TSAI comment on it (Infrastructure: no separate summary needed) | draft by Release from #475, confirmed by Architecture | yes |
| The first data shards | Data A | [#358](https://github.com/theschoolofai/era-v5-lab/pull/358), [#373](https://github.com/theschoolofai/era-v5-lab/pull/373), first 41 shards: TSAI comment on [#460](https://github.com/theschoolofai/era-v5-lab/pull/460) | text by Data A on #460, style edits confirmed by Data A | yes |
| Decision: the first dry run (go) | Architecture, Infrastructure | [#475](https://github.com/theschoolofai/era-v5-lab/pull/475), full run: [#620](https://github.com/theschoolofai/era-v5-lab/pull/620), restore drill: [#573](https://github.com/theschoolofai/era-v5-lab/pull/573), [#633](https://github.com/theschoolofai/era-v5-lab/pull/633) | TSAI decision at Gate 3 | no |
| Decision: tokenizer for training | Tokenizer | [#504](https://github.com/theschoolofai/era-v5-lab/pull/504) | TSAI words on #460, confirmed by Tokenizer | yes |
| Decision: data mix and Indic share | Data A, Data B | [#400](https://github.com/theschoolofai/era-v5-lab/pull/400), split by language in [#522](https://github.com/theschoolofai/era-v5-lab/pull/522) | TSAI numbers on #460, decided again at Gate 3 | yes (Data B) |
| Decision: learning rate | Architecture | [#447](https://github.com/theschoolofai/era-v5-lab/pull/447), Gate 2 update [#443](https://github.com/theschoolofai/era-v5-lab/pull/443) | TSAI decision at Gate 3 | no |
| Decision: model layout and size | Architecture | | TSAI decision at Gate 3 | no |
| Decision: attention and experts | Architecture | [#447](https://github.com/theschoolofai/era-v5-lab/pull/447), Gate 2 update [#443](https://github.com/theschoolofai/era-v5-lab/pull/443), test with more experts: [#659](https://github.com/theschoolofai/era-v5-lab/pull/659), [#668](https://github.com/theschoolofai/era-v5-lab/pull/668) | TSAI decision at Gate 3 | no |
| Decision: output head | KE2, Architecture | TSAI decision in `teams/04-ke2/gate3.md`, merged with the handoff to Architecture in [#694](https://github.com/theschoolofai/era-v5-lab/pull/694) | TSAI decision, 21 Nov | no |
| Decision: public dashboard panels and monitoring | Monitoring, Release | Panels: [#495](https://github.com/theschoolofai/era-v5-lab/pull/495). Text: [#598](https://github.com/theschoolofai/era-v5-lab/pull/598). Monitoring applied the text, merged: [#629](https://github.com/theschoolofai/era-v5-lab/pull/629) | text by Release, merged by TSAI in #598 | Monitoring: yes, [approval on #629](https://github.com/theschoolofai/era-v5-lab/pull/629#pullrequestreview-5967977324) |

Open at Gate 3, for the next gate update: evaluation schedule ([#662](https://github.com/theschoolofai/era-v5-lab/pull/662)), tuning method after the main training
([#524](https://github.com/theschoolofai/era-v5-lab/pull/524), [#593](https://github.com/theschoolofai/era-v5-lab/pull/593), [#634](https://github.com/theschoolofai/era-v5-lab/pull/634)), serving and quantization ([#538](https://github.com/theschoolofai/era-v5-lab/pull/538)).

- [x] `check_style.py` gives 0 errors
- [x] Every number in the text has TSAI approval
- [x] The text names teams only, and no person
- [x] Nothing from the internal list in `public_internal.md`
- [ ] No `[waiting for TSAI]` left in the text
- [x] A team member commented on this pull request
- [x] TSAI approved on: 19 Nov 2026
- [x] Merged after TSAI approved
