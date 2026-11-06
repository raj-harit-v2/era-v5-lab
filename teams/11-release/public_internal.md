# What is public and what is internal

G11 Release writes the public text of the lab. This file says what may go into public text and what stays
inside the lab. Nothing is public without TSAI approval.

## Rule 1: ask TSAI before you publish any number

A number is any count, size, score, cost, speed, percentage, rank or future date. Ask even if the number is in
a slide, a chat message or this repository. The date of an update and the week number need no approval.

## Rule 2: if you are not sure, it is internal

Treat the item as internal. Ask in the G11 group. G11 asks TSAI.

## Rule 3: name teams, not people

Public text names teams only. It names no person, not even by a first name or a GitHub handle. This applies to the
weekly updates, the dashboard text, the run report, the model card and the launch announcement.

## Public, after TSAI approves the text

| Topic | What we may say |
|---|---|
| The lab | What the lab does, in plain words, as TSAI describes it. |
| Teams | The names of the teams and what each team works on this week, at the level of the weekly update. |
| Data | The names of public data sources, and the kinds of problems we found in them. Short examples only if TSAI approves them and they hold no personal data. |
| Benchmarks | The names of the benchmarks that G9 Evaluation gives us. Scores only after TSAI approves them. |
| Methods | Methods that others have already published, described in general terms. |
| Links | Links to the public lab repository. |

## Internal, unless TSAI approves it in writing

| Topic | Examples |
|---|---|
| Numbers | Model size, token count, compute, cost, speed, scores and dates that TSAI has not approved. |
| Open decisions | Plans that are not final, such as the model size, the token budget and the training dates. |
| Results | Results of experiments and evaluations before TSAI approves them. |
| Unpublished work | Techniques, tricks and results that TSAI plans to publish later, for example in a paper. TSAI keeps the list of these topics. It is not in this public repository. |
| Teaching material | Slides, worked examples, session recordings and chat messages, unless TSAI shares them publicly. |
| Personal data | Names, emails, phone numbers and addresses of anyone. Public text names teams only (Rule 3). |
| Pack contents | Personal data or secrets found in the data packs. Never copy them anywhere. |
| Secrets | Keys, tokens, passwords, internal links and machine names. |
| Students | Grades, removals, the waitlist and the problems of any one person. |

## How we keep this

1. Every public text goes through the steps in `style/style_guide.md`.
2. A draft in a pull request is public, because the repository is public. It holds only facts that are already
   public, and `[number: waiting for TSAI]` for a number that TSAI has not approved.
3. The pull request records the lead OKs and the TSAI approval. It links only to public pull requests, never to
   the CAP chat. TSAI approves before the G11 lead merges.
4. If something internal becomes public by mistake, tell the G11 lead and TSAI at once. Do not repeat the item
   in the chat while you report it.
