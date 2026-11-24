# ERA V5 Lab: launch announcement

**Date:** [date: waiting for TSAI]

The ERA V5 lab of The School of AI (TSAI) builds and trains its own language model. Students of the lab work in
teams, and each team owns one part of the work. The work is in a public repository, so anyone can follow it.

## What the lab does

The lab cleans public text and builds a tokenizer that splits the text into pieces. Then it trains the model on
that text. It tests the model on public benchmarks, tunes it to chat, and makes smaller versions of it for
serving. TSAI approves each decision before the lab acts on it.

## The teams

- **Data A** cleans the training text, removes duplicates and packs the text into files for training.
- **Data B** reads Indian-language and code-adjacent text with native readers, and proposes how much of each kind
  goes into training.
- **Tokenizer** builds the tokenizer, which splits text into the pieces that the model reads.
- **KE2** tests its embedding method on the lab's tokenizer. The model uses the KE2 output head, the last part of
  the model, which scores each token as the next token.
- **Architecture** sets the shape of the model and its training settings.
- **Performance** makes each training step faster, and tests that each fast part matches a high-precision
  reference.
- **Infrastructure** runs the training jobs, checks the health of the machines, and saves the work so that a run
  can restart after a crash.
- **Monitoring** watches the training run, raises alarms and builds the public dashboard.
- **Evaluation** tests the model on public benchmarks and keeps benchmark items out of the training text.
- **Post-training** tunes the model after its main training, for example to chat in the lab's chat format.
- **Quantization** makes smaller versions of the model for serving, and checks them against the full model.
- **Release** writes the public text of the lab: the weekly updates, the dashboard text, the model card and the
  run report.

## Follow the work

- The public dashboard shows the training run: [dashboard link: waiting for Monitoring]
- The public lab repository holds the work of every team: https://github.com/theschoolofai/era-v5-lab

---

## Review record (remove this section before publishing)

This record is public, like the rest of the pull request. Put only public facts in it: yes or no, and links to
public pull requests. Never link to the CAP chat. Chat links are internal.

How to fill it:

1. Each team lead gives an OK on the line about their team in a pull request comment (`OK @handle`), or sends a
   new line.
2. Edit each new line only for style, and send the edit back to the writer.
3. Monitoring sends the dashboard link after TSAI approves the dashboard.
4. TSAI sets the date and confirms the goal of the lab in its own words.
5. Write `[number: waiting for TSAI]` for any number that TSAI has not approved yet.
6. Run `python teams/11-release/style/check_style.py <this file> --numbers` and clear every error.
7. TSAI approves this pull request before the G11 lead merges it.

| Part | Source | Lead OK |
|---|---|---|
| Goal of the lab, and what the lab does | `updates/2026-10-31_week1.md`, `model_card/model_card_outline.md`, `report/report_outline.md` | TSAI: no |
| Data A | `updates/2026-10-31_week1.md`, `updates/week2.md`, `updates/gate2.md`. Files for training (shards): [#358](https://github.com/theschoolofai/era-v5-lab/pull/358), [#373](https://github.com/theschoolofai/era-v5-lab/pull/373), and the Data A text on [#460](https://github.com/theschoolofai/era-v5-lab/pull/460#issuecomment-6962086936) | no |
| Data B | `updates/2026-10-31_week1.md`, `updates/gate2.md`, `updates/gate3.md` (data mix and Indic share: checked, the line does not change) | no |
| Tokenizer | `model_card/model_card_outline.md` (Tokenizer row), `updates/gate3.md` (the frozen tokenizer p1536: checked, the line does not change) | no |
| KE2 | `updates/gate2.md` (short forms), `updates/gate3.md` (the output head), [#704](https://github.com/theschoolofai/era-v5-lab/pull/704) | no |
| Architecture | `updates/2026-10-31_week1.md`, `model_card/model_card_outline.md`, `updates/gate3.md` (checked, the line does not change) | yes ([comment on #753](https://github.com/theschoolofai/era-v5-lab/pull/753#issuecomment-7109891336)) |
| The KE2 output head is in the training code | Architecture confirms this before the text is published. The Gate 3 update says that Architecture adds the head to the training code. Not yet: [#717](https://github.com/theschoolofai/era-v5-lab/pull/717) has not merged ([comment on #753](https://github.com/theschoolofai/era-v5-lab/pull/753#issuecomment-7109891336)) | no |
| Performance | `updates/2026-10-31_week1.md` | no |
| Infrastructure | `updates/2026-10-31_week1.md`, `model_card/model_card_outline.md`, `updates/gate3.md` (the first dry run: checked, the line does not change) | no |
| Monitoring | `updates/2026-10-31_week1.md`, `updates/week2.md`, `dashboard/dashboard_text.md` ([#598](https://github.com/theschoolofai/era-v5-lab/pull/598)), public panels with the approved text ([#629](https://github.com/theschoolofai/era-v5-lab/pull/629)) | no |
| Evaluation | `updates/2026-10-31_week1.md` | no |
| Post-training | `updates/2026-10-31_week1.md`, `updates/week2.md` | yes ([comment on #753](https://github.com/theschoolofai/era-v5-lab/pull/753#issuecomment-7107195973)) |
| Quantization | `updates/2026-10-31_week1.md`, `model_card/model_card_outline.md` (Serving row) | no |
| Release | `public_internal.md` (Rule 3) | yes (the Release lead wrote this draft) |
| Dashboard link | Monitoring, after TSAI approves the dashboard | no |

- [ ] `check_style.py` gives 0 errors
- [ ] Every number in the text has TSAI approval
- [ ] The text names teams only, and no person
- [ ] Nothing from the internal list in `public_internal.md`
- [ ] No `waiting for` placeholder left in the text
- [ ] A team member commented on this pull request
- [ ] TSAI approved on: [DD Mon YYYY]
- [ ] Merged after TSAI approved
