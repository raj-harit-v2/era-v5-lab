# Public dashboard text: the new panels

**Date:** 23 Nov 2026

Monitoring plans new panels for the public dashboard. Its list is in
`teams/08-monitoring/docs/dashboard_content_decisions_w4.md` ([#732](https://github.com/theschoolofai/era-v5-lab/pull/732)).
This file has one plain sentence for each new panel, and the text for the panel that explains the dashboard. The
words follow the public glossary in `glossary.md`. Benchmark scores follow `score_text_format.md`.

## Why this is a separate file

Monitoring's test, `teams/08-monitoring/grafana/test_public_dashboard.py`, checks that each row of
`dashboard_text.md` matches a panel on the public dashboard. These panels are not public yet, so their rows wait in
this file. When Monitoring adds a panel to `public_v1.json`, the same pull request moves its row into
`dashboard_text.md`. The panel names are the working names from Monitoring's list. Monitoring sets the final titles.

## One sentence for each panel

| Panel | Sentence |
|---|---|
| Dataset and Shard Composition | This panel shows each pack of text by subject and language, with its token count and the share of its documents that cleaning removed. |
| Eval-Mini Scores Alongside Training Loss | This panel shows the model's scores on a small set of benchmark questions at each checkpoint, next to the training loss. |
| Training Pace | This panel shows how many tokens the run processes each second and how long each training step takes. |
| Open Infrastructure Health | This panel counts the restarts of the training run, the alarms that fired and the checkpoints that the run saved. |
| What This Shows and What It Doesn't | This panel explains what the dashboard shows and what it does not show. |

## Text for the panel "What This Shows and What It Doesn't"

**What this dashboard shows**

This dashboard shows one training run of the ERA V5 lab as it happens. The run on the dashboard now is
[run: waiting for TSAI, the kind of run and its name]. The panels show how well the model predicts text, its
benchmark scores, how fast the run goes and which text it trains on. They also count every restart and every alarm.
All times are in IST (India Standard Time).

**What this dashboard does not show**

The loss curves do not show how good the final model will be. The scores come from a small set of benchmark
questions, not from the full benchmarks. The dashboard does not show the cost of the run or the machines that it
runs on.

## New terms for the glossary

This pull request also adds these terms to `glossary.md`: pack, checkpoint, benchmark, restart and alarm.

---

## Review record (remove this section before publishing)

This record is public, like the rest of the pull request. Put only public facts in it: yes or no, and links to
public pull requests. Never link to the CAP chat. Chat links are internal.

How to fill it:

1. The lead of each team in the Source column gives an OK on the sentences in a pull request comment
   (`OK @handle`), or sends a new sentence.
2. Edit each new sentence only for style, and send the edit back to the writer.
3. TSAI names the run for the explaining panel and says what kind of run it is. For example: "the second dry run,
   a short test of the whole training setup before the main training run".
4. If Monitoring builds one of these panels as several panels, write one `This panel ...` sentence for each panel
   title.
5. If a final panel title uses a term that is not in `glossary.md`, such as Eval-Mini, add the term to the glossary.
6. Run `python teams/11-release/style/check_style.py <this file> --numbers` and clear every error.
7. TSAI approves this pull request before the G11 lead merges it.

| Panel | Source | Lead OK |
|---|---|---|
| Dataset and Shard Composition | Monitoring list, section 2.3 (Data A) | Monitoring: no; Data A: no |
| Eval-Mini Scores Alongside Training Loss | Monitoring list, section 2.4 (Evaluation) | Monitoring: no; Evaluation: no |
| Training Pace | Monitoring list, sections 2.1 and 2.2 (Architecture, Performance). Architecture sent this sentence: the run does not log context length ([comment on #760](https://github.com/theschoolofai/era-v5-lab/pull/760#issuecomment-7109890552)) | Monitoring: no; Architecture: yes; Performance: no |
| Open Infrastructure Health | Monitoring list, section 3 | Monitoring: no |
| What This Shows and What It Doesn't | Monitoring list, section 3 | Monitoring: no; TSAI: no |
| New glossary terms | `glossary.md` | Monitoring: no |

- [ ] `check_style.py` gives 0 errors
- [ ] No number in the text
- [ ] The text names teams only, and no person
- [ ] Nothing from the internal list in `public_internal.md`
- [ ] No `waiting for` placeholder left in the text
- [ ] A team member commented on this pull request
- [ ] TSAI approved on: [DD Mon YYYY]
- [ ] Merged after TSAI approved
