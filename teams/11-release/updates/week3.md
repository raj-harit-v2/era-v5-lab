# ERA V5 Lab: week 3 update

**Date:** 19 Nov 2026
**Period:** 15 Nov to 19 Nov 2026

The lab ran its first dry run with the frozen tokenizer. A dry run is a short test of the whole training setup before the main training run.

## The teams

- **Tokenizer:** The Tokenizer team froze and published the final tokenizer, measured its encoding speed, and checked chat format markers with partner teams.
- **Architecture:** The Architecture team merged the week 3 model settings, the dry run, and the seed-repeat jobs. The run-evidence check is approved.
- **Infrastructure:** The Infrastructure team stopped and restored the first dry run, and the loss matched at every step. It wrote the checkpoint interval and failure runbook.
- **Monitoring:** Monitoring checked the dry run logs for missing steps and alarms, added reinforcement learning and token records, and updated the public dashboard.
- **Evaluation:** The Evaluation team built the checkpoint scorer, found zero benchmark hits in the first training shards, and wrote the evaluation schedule.
- **Release:** Release wrote the dashboard text, a glossary, the launch announcement draft and the gate update.

## Next week

Next week, the teams prepare the second dry run and the public dashboard.

---

## Review record (remove this section before publishing)

This record is public, like the rest of the pull request. Put only public facts in it: yes or no, and links to
public pull requests. Never link to the CAP chat. Chat links are internal.

How to fill it:

1. Collect the text for each team.
   - Week 1: one sentence from each lead. Ask the leads in the CAP chat, and give the due day.
   - From week 2: one short paragraph for each team, from the rotating student of that team or from the lead.
2. Paste each text above. Edit it only for style, and send the edit back to the writer.
3. Mark "Lead OK" when the lead of that team says OK to the final text.
4. Give the source of each fact: a public pull request or a file in this repository. Gate 4 needs a source for
   each fact.
5. Write `[number: waiting for TSAI]` for any number that TSAI has not approved yet.
6. Run `python teams/11-release/style/check_style.py <this file> --numbers` and clear every error.

| Team | Text received | Lead OK | Source |
|---|---|---|---|
| Data A | no | no (line left out this week) | |
| Data B | no | no (line left out this week) | |
| Tokenizer | Yes | Yes | [#465](https://github.com/theschoolofai/era-v5-lab/pull/465), [#504](https://github.com/theschoolofai/era-v5-lab/pull/504), [#488](https://github.com/theschoolofai/era-v5-lab/pull/488), [#505](https://github.com/theschoolofai/era-v5-lab/pull/505), [#516](https://github.com/theschoolofai/era-v5-lab/pull/516), [#561](https://github.com/theschoolofai/era-v5-lab/pull/561), [#642](https://github.com/theschoolofai/era-v5-lab/pull/642) |
| KE2 | no | no (line left out this week) | |
| Architecture | Yes | Yes | [#556](https://github.com/theschoolofai/era-v5-lab/pull/556), [#475](https://github.com/theschoolofai/era-v5-lab/pull/475), [#620](https://github.com/theschoolofai/era-v5-lab/pull/620), [#462](https://github.com/theschoolofai/era-v5-lab/pull/462), [#466](https://github.com/theschoolofai/era-v5-lab/pull/466), [#487](https://github.com/theschoolofai/era-v5-lab/pull/487), [#574](https://github.com/theschoolofai/era-v5-lab/pull/574), [#605](https://github.com/theschoolofai/era-v5-lab/pull/605) |
| Performance | no | no (line left out this week) | |
| Infrastructure | Yes | Yes | [#491](https://github.com/theschoolofai/era-v5-lab/pull/491), [#573](https://github.com/theschoolofai/era-v5-lab/pull/573), [#586](https://github.com/theschoolofai/era-v5-lab/pull/586), [#633](https://github.com/theschoolofai/era-v5-lab/pull/633), [#463](https://github.com/theschoolofai/era-v5-lab/pull/463), [#510](https://github.com/theschoolofai/era-v5-lab/pull/510) |
| Monitoring | Yes | Yes | [#494](https://github.com/theschoolofai/era-v5-lab/pull/494), [#464](https://github.com/theschoolofai/era-v5-lab/pull/464), [#512](https://github.com/theschoolofai/era-v5-lab/pull/512), [#518](https://github.com/theschoolofai/era-v5-lab/pull/518), [#575](https://github.com/theschoolofai/era-v5-lab/pull/575), [#493](https://github.com/theschoolofai/era-v5-lab/pull/493), [#551](https://github.com/theschoolofai/era-v5-lab/pull/551), [#495](https://github.com/theschoolofai/era-v5-lab/pull/495), [#629](https://github.com/theschoolofai/era-v5-lab/pull/629) |
| Evaluation | Yes | Yes | [#549](https://github.com/theschoolofai/era-v5-lab/pull/549), [#641](https://github.com/theschoolofai/era-v5-lab/pull/641), [#627](https://github.com/theschoolofai/era-v5-lab/pull/627), [#648](https://github.com/theschoolofai/era-v5-lab/pull/648), [#662](https://github.com/theschoolofai/era-v5-lab/pull/662) |
| Post-training | no | no (line left out this week) | |
| Release | Yes | Yes | [#598](https://github.com/theschoolofai/era-v5-lab/pull/598), [#497](https://github.com/theschoolofai/era-v5-lab/pull/497), [#578](https://github.com/theschoolofai/era-v5-lab/pull/578), [#600](https://github.com/theschoolofai/era-v5-lab/pull/600), [#603](https://github.com/theschoolofai/era-v5-lab/pull/603), [#443](https://github.com/theschoolofai/era-v5-lab/pull/443), [#460](https://github.com/theschoolofai/era-v5-lab/pull/460) |
| Quantization | no | no (line left out this week) | |

- [x] `check_style.py` gives 0 errors
- [ ] Every number in the text has TSAI approval
- [ ] The text names teams only, and no person
- [ ] Nothing from the internal list in `public_internal.md`
- [ ] No `[number: waiting for TSAI]` left in the text
- [ ] The G11 lead reviewed the pull request (a pull request from the lead: a team member commented)
- [ ] Sent to TSAI on: <DD Mon YYYY>
- [ ] TSAI approved on: <DD Mon YYYY>
- [ ] Merged after TSAI approved
