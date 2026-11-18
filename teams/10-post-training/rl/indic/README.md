# Indic verifier set (`indic_verifier.py`, `tasks/`)

A binary reward for Indic tasks with one checkable answer. The prompt is in an Indic language. The model replies in that language and puts its final answer in `<answer>...</answer>`. The verifier normalises the answer and compares it exactly with the accepted answers. No candidate code runs, so there is no sandbox or container, and one core scores about 500,000 completions per second.

The Python and Go verifiers check code. This one checks a short answer: a number, a word or name in the task's script, or a multiple-choice label.

```text
rl/indic/
  README.md               this file
  indic_verifier.py       reward(), score(), prepare(), check_task(), the command line and --bench
  test_indic_verifier.py  correct and wrong answer for every task, the cheating cases, normalisation, the lint
  tasks/<task_id>/        task.json, prompt.md, answer.json
  generate.py             many checked items from one person-written template (output to out/, never committed)
  test_generate.py        template lint, safe expressions, item self-checks, determinism, the command line
  templates/indic_templates.yaml   the training templates, written by people (empty until they are)
```

The prompt families, who writes them, and the Team 2 check are in [`../indic_prompts_v0.md`](../indic_prompts_v0.md).

```bash
python teams/10-post-training/rl/indic/indic_verifier.py --check-all                                   # lint every task
python teams/10-post-training/rl/indic/indic_verifier.py --check-task teams/10-post-training/rl/indic/tasks/<task_id>
python teams/10-post-training/rl/indic/indic_verifier.py --reward teams/10-post-training/rl/indic/tasks/<task_id> completion.txt
python teams/10-post-training/rl/indic/indic_verifier.py --bench
python teams/10-post-training/rl/reward.py --check-all --type indic                                     # through the one entry point
python -m pytest teams/10-post-training/rl/indic/test_indic_verifier.py -q -p no:cacheprovider
```

From the trainer, use the shared entry point: `reward.reward("indic/<task_id>", completion)` returns `(score, info)`. Generated items that have no folder are scored with `score(prepare(meta, accepted), completion)`. Only `reward` is for training; `reason` is for logs.

## How a completion is scored

1. **Visible reply only.** Everything up to the last `<|/think|>` is dropped. If a `<|think|>` is still open after that, the completion has no answer. Only the last 20,000 characters are read.
2. **Answer tags.** Every `<answer>...</answer>` in the visible reply is read. No tag, an empty tag, or a tag longer than 200 characters scores 0. Two different answers score 0. The same answer repeated (`40` and `४०`) is one answer.
3. **Normalisation**, on the answer and on every accepted answer:
   - remove U+200B and U+FEFF only, and keep ZWJ and ZWNJ (the G10 text rule in `swe-task/hindi_text_prep.py`);
   - case folding, then NFC (not NFKC);
   - one space for each run of whitespace;
   - strip quotes, brackets and `. , ; : ! ? । ॥` at the ends.
4. **Compare by `answer_type`:**

| `answer_type` | Scores 1 when | Scores 0, for example |
|---|---|---|
| `integer` | the value is accepted. Digits are ASCII or the task's own script's (`40` or `४०` on a Hindi task, `36` or `௩௬` on a Tamil task), optionally grouped `3,05,042` or `305,042`, with an optional minus sign | `40 आम`, `चालीस`, `4०` (two scripts), `৪০` or `٤٠` on a Hindi task (another script), `040` (leading zero), `30,50,42` |
| `text` | the answer equals an accepted variant, and every letter and mark is in the task's `script` | `Shanivar` for a Devanagari task, a different word |
| `choice` | the answer is the accepted option label from `choices` | another label, or the option's text instead of its label |

The reply dict never holds the expected answer.

## Writing a task

A task is a folder `tasks/<task_id>/`. The folder name equals `id`, and the name starts with the language code (`hi_`, `ta_`, ...).

| File | Content |
|---|---|
| `task.json` | `id`, `title`, `language` (ISO 639-1), `script` (ISO 15924: `Deva`, `Beng`, `Guru`, `Gujr`, `Orya`, `Taml`, `Telu`, `Knda`, `Mlym`, `Latn`), `answer_type`, `difficulty`, `source` (starts with `original`, says who wrote it and when), `author` and `team2_reviewer` (GitHub handles), `eligibility` (`eval` or `train`), `tags`. A `choice` task adds `choices`. A task whose answer is a span of the prompt adds `"answer_in_prompt": true` |
| `prompt.md` | the question in the language, and the instruction to put the final answer in `<answer>...</answer>`. Show the format with a word, never with the answer (`<answer>संख्या</answer>`) |
| `answer.json` | `{"accepted": [...], "wrong": [...]}`. `accepted` holds every form that must score 1. `wrong` holds plausible wrong answers that must score 0. Integers for `integer` tasks, strings otherwise |

`--check-task` checks all of this:
- the fields and their values, and that the id matches the folder;
- every accepted answer scores 1, and every wrong answer scores 0;
- no answer is both accepted and wrong;
- accepted text answers are in the task's script, and a choice answer is one of the choices;
- the prompt asks for `<answer>` and does not contain the answer (any number in the prompt equal to an accepted integer counts, in any script and with leading zeros).

Then add the task's correct and wrong completion to `CASES` in `test_indic_verifier.py`. A test fails when a task has no entry there.

**Who may write a training task.** TSAI's data rule of 3 Nov (`../../rl-data/README.md`): training problems are written by people. A task with `"eligibility": "train"` fails the lint if its `source` names a model, or if it has no `team2_reviewer` other than the author. The six tasks here were written by Claude (AI assistant) for gmrammohan15. Each `task.json` says so, and each is `"eligibility": "eval"`. They test the verifier and can be used for evaluation. A Team 2 reader still has to confirm each answer and the wording; the reader's handle then goes in `team2_reviewer`.

## Templates and the generator (`generate.py`)

A template is a prompt with `{placeholders}`, the parameter ranges, and the answer and one or two wrong answers as small expressions. The format is in the docstring of `generate.py` and in the comments of `templates/indic_templates.yaml`.

```bash
python teams/10-post-training/rl/indic/generate.py --templates teams/10-post-training/rl/indic/templates/indic_templates.yaml --check
python teams/10-post-training/rl/indic/generate.py --templates teams/10-post-training/rl/indic/templates/indic_templates.yaml --per-template 200 --seed 1234 --out out/indic_items.jsonl
python -m pytest teams/10-post-training/rl/indic/test_generate.py -q -p no:cacheprovider
```

- **Expressions** may use only integers, strings, the template's names, `+ - * // %`, comparisons, `and or not`, `x if c else y`, indexing, and `min max abs len digits`. A placeholder must be a plain name. Anything else is rejected when the template is read, so a template cannot run code. `*` works on integers only, with the product at most 10^30, and no computed value may be longer than 10,000 characters, so a template cannot use up memory either (`'ab' * 10**12` is refused at once).
- **Every item is checked before it is written**: its answer scores 1 with `indic_verifier`, each wrong answer scores 0, and its prompt does not give the answer away. A draw that fails, or repeats a prompt, is drawn again. A template that cannot give the asked number of distinct items stops with an error after 5,000 draws in a row with no new item. It never loops.
- **Same seed, same items**: each template has its own random stream (`seed:template_id`), so adding a template does not change the items of the others.
- **Speed**: about 50,000 checked items per second on one laptop CPU core (20,000 items from one template in about 0.4 s; five runs on 15 Nov: 46,829 to 51,808 per second).
- The trainer scores an item with `indic_verifier.score(indic_verifier.prepare(item, item["accepted"]), completion)`.

## Tasks so far (6)

| Task | Language | Type | What it checks |
|---|---|---|---|
| `hi_mango_count` | Hindi | integer | a two-step word problem |
| `hi_number_words` | Hindi | integer | a number written in words (lakh, hazaar) as digits |
| `hi_weekday_after` | Hindi | text | the weekday a number of days from today |
| `ta_class_present` | Tamil | integer | a two-step word problem |
| `bn_largest_choice` | Bengali | choice | the largest of four numbers in Bengali digits |
| `te_passage_who` | Telugu | text (span) | a name from a short passage |

## Speed

`--bench` scores 200,000 completions of about 1,600 characters each, with a think span, half of them correct and half wrong. On one laptop CPU core it takes about 0.4 s, which is about 500,000 completions per second (three runs on 15 Nov: 499,741, 507,459 and 510,044 per second). Task folders are read once and cached until `task.json` or `answer.json` changes. Regexes and script tables are built at import. A reward therefore costs nothing next to generating the completion.

## Decontamination (15 Nov)

The prompt and the accepted answers of each of the 6 tasks (12 documents) were checked with `teams/09-evaluation/decontam/decontam_check.py` (fingerprints v2, full set, `set_sha256` `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`) and `canary_scan.py`, on lab main `17fa3c69`. The result was 0 flagged and 0 canary hits. Input file sha256: `521e3a3b4f8bda68ec5200dd4f265fc1f19ef08fac7a6be5aeb1b1065723cb9b`, one JSONL line per prompt and per answer (`doc_id`, `text`), written outside the repository. To repeat it, write the same lines and run both scripts on them.
