# ERA V5 Lab: week 2 update

**Date:** 4 Nov 2026
**Period:** 1 Nov to 4 Nov 2026

The teams of the ERA V5 lab built on their first week of work and started new tasks.

## The teams

- **Data A:** Data A added rules for Indian languages to the cleaner and fixed the masking of personal data. TSAI ran the cleaner on the tokenizer sample.
- **Tokenizer:** Tokenizer trained several candidate tokenizers on the tokenizer sample, and TSAI rebuilt one of them and got the same result.
- **Performance:** Performance compared ways to run the mixture-of-experts layer, put together its speed evidence, and recorded the result of its baseline timing job.
- **Monitoring:** Monitoring built a metric store, a dashboard for the training run and checkpoint alarms, and a node health check with Infrastructure.
- **Evaluation:** Evaluation added lab canary strings and a canary scanner to its test files. It prepared new agent benchmarks for fingerprinting and fixed how Indic scores are averaged.
- **Post-training:** Post-training mapped chat markers to tokenizer slots, built a chat-format converter with loss masks, audited dataset licences, and proposed a fine-tuning mix.
- **Release:** Release merged the first weekly update after TSAI approved it, wrote the model card outline, and drafted the report outline.
- **Quantization:** Quantization recorded a checksum for each output file and checked a round trip of tokenizer v0 through the GGUF file format. It also supported the Indic evaluation and ran it on different formats.

## Next week

Next week the lab takes a break, and then each team prepares its proposals for the next set of lab decisions.

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
| Data A | Yes | Yes | [#244](https://github.com/theschoolofai/era-v5-lab/pull/244) (open), [#194](https://github.com/theschoolofai/era-v5-lab/pull/194) |
| Data B | no | no (line left out this week) | |
| Tokenizer | Yes | Yes | [#183](https://github.com/theschoolofai/era-v5-lab/pull/183), [#187](https://github.com/theschoolofai/era-v5-lab/pull/187), [#195](https://github.com/theschoolofai/era-v5-lab/pull/195), [#218](https://github.com/theschoolofai/era-v5-lab/pull/218) |
| KE2 | no | no (line left out this week) | |
| Architecture | Yes | no (line left out this week) | [#180](https://github.com/theschoolofai/era-v5-lab/pull/180), [#197](https://github.com/theschoolofai/era-v5-lab/pull/197) |
| Performance | Yes | Yes | [fork #41](https://github.com/vaibh27/era-v5-lab/pull/41), [fork #53](https://github.com/vaibh27/era-v5-lab/pull/53), [fork #54](https://github.com/vaibh27/era-v5-lab/pull/54), [fork #55](https://github.com/vaibh27/era-v5-lab/pull/55), [#239](https://github.com/theschoolofai/era-v5-lab/pull/239) (open) |
| Infrastructure | no | no (line left out this week) | |
| Monitoring | Yes | Yes | [#119](https://github.com/theschoolofai/era-v5-lab/pull/119), [#250](https://github.com/theschoolofai/era-v5-lab/pull/250), [#247](https://github.com/theschoolofai/era-v5-lab/pull/247), [#282](https://github.com/theschoolofai/era-v5-lab/pull/282), [#287](https://github.com/theschoolofai/era-v5-lab/pull/287), [#260](https://github.com/theschoolofai/era-v5-lab/pull/260), [#248](https://github.com/theschoolofai/era-v5-lab/pull/248), [#262](https://github.com/theschoolofai/era-v5-lab/pull/262), [#266](https://github.com/theschoolofai/era-v5-lab/pull/266), [#278](https://github.com/theschoolofai/era-v5-lab/pull/278), [#299](https://github.com/theschoolofai/era-v5-lab/pull/299), [#301](https://github.com/theschoolofai/era-v5-lab/pull/301), [#302](https://github.com/theschoolofai/era-v5-lab/pull/302), [#136](https://github.com/theschoolofai/era-v5-lab/pull/136) (open), [#125](https://github.com/theschoolofai/era-v5-lab/pull/125) (open) |
| Evaluation | Yes | no (waiting for OK on the new wording) | [#193](https://github.com/theschoolofai/era-v5-lab/pull/193), [#184](https://github.com/theschoolofai/era-v5-lab/pull/184), [#280](https://github.com/theschoolofai/era-v5-lab/pull/280), [#192](https://github.com/theschoolofai/era-v5-lab/pull/192), [#300](https://github.com/theschoolofai/era-v5-lab/pull/300) |
| Post-training | Yes | Yes | [#178](https://github.com/theschoolofai/era-v5-lab/pull/178), [#173](https://github.com/theschoolofai/era-v5-lab/pull/173) |
| Release | Yes | Yes | [#142](https://github.com/theschoolofai/era-v5-lab/pull/142), [#152](https://github.com/theschoolofai/era-v5-lab/pull/152), [#234](https://github.com/theschoolofai/era-v5-lab/pull/234), [#237](https://github.com/theschoolofai/era-v5-lab/pull/237), [#264](https://github.com/theschoolofai/era-v5-lab/pull/264), [#281](https://github.com/theschoolofai/era-v5-lab/pull/281), [#283](https://github.com/theschoolofai/era-v5-lab/pull/283) |
| Quantization | Yes | Yes | [#221](https://github.com/theschoolofai/era-v5-lab/pull/221) (open), [#220](https://github.com/theschoolofai/era-v5-lab/pull/220), [#219](https://github.com/theschoolofai/era-v5-lab/pull/219) |

- [x] `check_style.py` gives 0 errors
- [ ] Every number in the text has TSAI approval
- [ ] Every person named has signed the consent form
- [ ] Nothing from the internal list in `public_internal.md`
- [ ] No `[number: waiting for TSAI]` left in the text
- [ ] The G11 lead reviewed the pull request (a pull request from the lead: a team member commented)
- [ ] Sent to TSAI on: <DD Mon YYYY>
- [ ] TSAI approved on: <DD Mon YYYY>
- [ ] Merged after TSAI approved
