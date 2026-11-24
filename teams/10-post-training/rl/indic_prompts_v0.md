# Indic prompts with checkable answers, v0

Week 3 and 4, member E (gmrammohan15). Status on 24 Nov: the families and the generator are ready, and 6 person-written templates are in (4 Hindi, 2 Tamil). All are `eligibility: eval` until a Team 2 reader signs off (section 5).

## 1. What this is

RL needs prompts whose answers a program can check. For Indic languages, this file lists:
- the prompt families we use;
- how each family's answer is checked;
- who writes the prompts and who confirms them;
- what is ready and what is still open.

Every prompt is scored by `rl/indic/indic_verifier.py`, registered as `indic/<task_id>` in `rl/reward.py`. The model replies in the language and gives its final answer in one `<answer>...</answer>`. The verifier normalises that answer and checks it exactly.

Normalisation follows the G10 text rule: strip U+200B and U+FEFF, keep ZWJ and ZWNJ, NFC and not NFKC, and strip end marks such as `।`. An integer answer is written in ASCII digits or the task's own script's digits, with no leading zero: on a Hindi task `४०` equals `40`, while `৪০` (Bengali digits) and `040` score 0. A text answer must be in the task's script. Details are in `rl/indic/README.md`.

## 2. Who writes the prompts (TSAI data rule, 3 Nov)

RL training text is written by people, never by a model. So there are two kinds of Indic prompts:

| Kind | Written by | Use | Where |
|---|---|---|---|
| Seed tasks (6) | Claude (AI assistant) for gmrammohan15, and each `task.json` says so | testing the verifier, and evaluation | `rl/indic/tasks/`, `"eligibility": "eval"` |
| Templates | a person on the team, checked by a Team 2 reader of that language | training, after the check | `rl/indic/templates/indic_templates.yaml` |

`rl/indic/generate.py` turns one template into many prompts. It draws the values, computes the answer from the template's expression, and keeps an item only if:
- its answer scores 1;
- each listed wrong answer scores 0;
- its prompt does not give the answer away.

The lint blocks the two ways round the rule:
- A template or task marked `train` fails if its `source` names a model.
- It also fails if it has no `team2_reviewer` other than the author.

## 3. Families

Each family has one answer that the verifier can check exactly. "Templates" counts the person-written templates in `indic_templates.yaml`; each stays `eval` until its Team 2 sign-off.

| # | Family | `answer_type` | How the answer is checked | Languages to start | Seed task (eval) | Templates |
|---|---|---|---|---|---|---|
| F1 | Arithmetic word problems (two or three steps, everyday objects, rupees and paise) | integer | the value; ASCII or the task's own digits | hi, ta, te, bn, kn | `hi_mango_count`, `ta_class_present` | 4 (`hi_f1_left`, `hi_f1_change`, `ta_appalam_sub`, `ta_pen_mult`) |
| F2 | Number written in words to digits, with lakh and crore (`तीन लाख पाँच हज़ार बयालीस`) | integer | the value; Indian or Western grouping | hi, bn, mr | `hi_number_words` | 0 |
| F3 | Calendar: weekday or month a number of days or months from a given one | text | the word in a closed list (7 weekdays, 12 months), in the task's script | hi, ta, te | `hi_weekday_after` | 1 (`hi_f3_weekday`) |
| F4 | Numbers written in Indic digits: compare, order, add (`৪৮৯` against `৫০২`) | integer or choice | the value, or the option label | bn, hi, ta | `bn_largest_choice` | 0 |
| F5 | A name, number or place from a short passage written by the template author | text (`answer_in_prompt`) | the span, with listed variants such as case endings (`సీత`, `సీతతో`) | te, hi, kn | `te_passage_who` | 0 |
| F6 | Time and units: hours and minutes, metres and centimetres, rupees and paise | integer | the value in the asked unit | hi, ta | none yet | 1 (`hi_f6_minutes`) |

Kept out of v0, because one exact answer is not possible or not safe:

| Out | Why |
|---|---|
| Translation, summaries, free answers | many right answers. They need a judge model, not an exact check (Session 18: use a test where one exists, a judge only where none does) |
| Number to words (digits to `पैंतालीस`) | spellings vary (chandrabindu or anusvara, `हज़ार` or `हजार`). It can come back when Team 2 lists the accepted spellings for each number word |
| Transliteration between scripts | several valid spellings for one name |
| Akshara or letter counts | readers disagree on what one akshara is. The code task `rl/tasks/indic_cluster_count` already covers a fixed rule |
| Facts and general knowledge | answers change over time, and such questions are close to benchmark items |

## 4. Answer format and the checks, per family

- Every prompt ends with the instruction, in the language, to put the final answer in `<answer>...</answer>`. It shows the format with a word, never with a number or the answer (`<answer>संख्या</answer>`, `<answer>எண்</answer>`).
- F1, F2, F4 and F6: the template gives one or two wrong answers from common slips (adding instead of subtracting, one step missed, the lakh place shifted). The generator keeps a draw only if every wrong answer differs from the right one, and drops a draw that writes the answer in the prompt.
- F3 and F5: `also_accept` lists the other right forms (for example a case ending). A text answer in another script scores 0: `Shanivar` on a Devanagari task.
- Difficulty: F1 and F6 vary the number of steps and the size of the numbers. The RL filter (`rl-data/filter.py`) then keeps only the items the starting model sometimes solves, as for the code tasks.

## 5. Status and what is open

| Item | Status |
|---|---|
| Verifier, 6 seed tasks, tests, `indic/<task_id>` in `reward.py` | done: PR #88 (correct = 1 and wrong = 0 for every task; 59 tests) |
| Generator and template lint | done: PR #89 (41 tests; about 50,000 checked items per second on one CPU core) |
| Templates written by people | **in progress**. Hindi, gmrammohan15 (24 Nov): `hi_f1_left`, `hi_f1_change`, `hi_f6_minutes`, `hi_f3_weekday`. Tamil, ranjani-cse (#149): `ta_appalam_sub`, `ta_pen_mult`. Telugu: a Telugu-speaking author is asked for 2 templates (the mechanics of `te_f1_change` and `te_f6_minutes` are ready). All pass `generate.py --check` |
| Team 2 check | **open**. Batch 1 (the 4 Hindi templates, 5 items each) goes to Data B through the G10 lead; shankarpandala assigns a native reader within a day (21 Nov). Request to Team 2 (Data B) readers, by language, from `teams/02-data-b/readers.md`: Hindi mittalutkarsh; Tamil truesrini; Telugu shankarpandala; Bengali aneeshads; Kannada keshavamurali. Each reader checks the wording of the seed task in their language and of each template, and five generated items. When they agree, their handle goes in `team2_reviewer` and the link to their reply goes here |
| Decontamination of the training prompts | runs on each template's generated file before it is used (section 6) |

Team 2 replies (handle, language, what was checked, link) will be listed here as they come in.

## 6. Decontamination

- **Seed tasks (15 Nov).** The 6 prompts and their answers (12 documents) were checked with `teams/09-evaluation/decontam/decontam_check.py` (fingerprints v2, full set, `set_sha256` `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`) and `canary_scan.py`, on lab main `17fa3c69`. The result was 0 flagged and 0 canary hits.
- **Generated items.** The generator's output file works with the Team 9 tools as written. Run `decontam_check.py <items.jsonl> --id-field id --text-field prompt` with the full set, and `canary_scan.py` with the same fields. A trial on 600 items from the test fixture templates (not training templates) gave 0 flagged and 0 canary hits. Every template's output is checked the same way before training, and the counts and the input sha256 are added here. No prompt text goes into the repository, only ids, counts and hashes.
- **Hindi templates, batch 1 (24 Nov).** 200 items from each of `hi_f1_left`, `hi_f1_change`, `hi_f6_minutes` and `hi_f3_weekday` (`--per-template 200 --seed 1234`, 800 items, input sha256 `b1540f8bc3e0d2ed98b6621505b8091b412ddccb5d23172e950e2d9592444510`), checked with `decontam_check.py` and `canary_scan.py` as on lab main `5b07c354` (fingerprints v2, full set, the same `set_sha256`): 0 flagged, 0 canary hits (4 canaries).

## 7. Questions for TSAI and the lead

1. **Is a person-written template whose values are drawn by a program allowed as training text?** The easy rung (`rl-data/easy_rung.py`) asked the same question for code.
   - *TSAI ruling (21 Nov 2026):* **Proceed** with programmatic value fills on human-written templates (same pattern as the rest of the lab's data rule), **conditional on Team 2's reader sign-off actually completing before admission**. AI-written seed tasks remain `eligibility: eval` only.
2. **Should the Indic share of RL data v1 be fixed per language, or follow the native Indic share in `teams/02-data-b/native_indic_share_v1.md`?**
   - *Team 10 lead recommendation (20 Nov 2026, `saitej123`):* **Follow Team 2's `native_indic_share_v1.md` proportions** with a small per-language floor so every covered language has verifiable RL signal. Awaits TSAI confirmation at Gate 3.
3. **Current template status (24 Nov 2026):** `rl/indic/templates/indic_templates.yaml` holds 6 person-written templates (4 Hindi, 2 Tamil) and 0 Team 2 reader sign-offs, so 0 are training-eligible yet. Per TSAI's 3 Nov data rule, training templates are not model-generated and await Team 2 review before entering RL training.
