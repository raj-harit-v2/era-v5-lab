# Tool-result verifier set (`toolresult_verifier.py`, `tasks/`)

A binary reward for one agent skill: **report a tool's output exactly**. Each task is a chat-format v0 transcript that
ends with a tool result. The model must answer the user from that result, without rounding, retyping, dropping a
joiner, changing a unit or calling the tool again. No candidate code runs, so there is no sandbox or container.

The Python and Go verifiers check code, and the Indic verifier checks a short answer in `<answer>` tags. This one
checks a normal reply for the tool's exact values.

```text
rl/toolresult/
  README.md                     this file
  toolresult_verifier.py        reward(), score(), prompt_text(), check_task(), the command line
  test_toolresult_verifier.py   correct and wrong reply for every task, the cheating cases, the whole-value rule, the lint
  tasks/<task_id>/              task.json, messages.json, hidden/expected.json
```

The two tests the week-3 brief asks for (one correct completion scores 1.0, one wrong answer that ignores the tool
result scores 0.0), plus hallucinated, rounded, unclosed-marker and extra-turn completions, are also in the shared
`../test_verifier.py` (section "tool-result exact verifier"), so `pytest teams/10-post-training/rl/test_verifier.py`
covers this set through `reward.py`.

```bash
python teams/10-post-training/rl/toolresult/toolresult_verifier.py --check-all                       # lint every task
python teams/10-post-training/rl/toolresult/toolresult_verifier.py --prompt teams/10-post-training/rl/toolresult/tasks/<task_id>
python teams/10-post-training/rl/toolresult/toolresult_verifier.py --reward teams/10-post-training/rl/toolresult/tasks/<task_id> completion.txt
python teams/10-post-training/rl/reward.py --check-all --type toolresult                             # through the one entry point
python -m pytest teams/10-post-training/rl/toolresult/test_toolresult_verifier.py -q -p no:cacheprovider
```

From the trainer, use the shared entry point: `reward.reward("toolresult/<task_id>", completion)` returns
`(score, info)`. Give the model `prompt_text(task_dir)`; the completion is what it writes after
`<|im_start|>assistant\n`. Only `reward` is for training; `reason` is for logs and never holds the expected value.

## How a completion is scored

It scores 1 only if all of these hold:

0. **Readable text.** The completion is a string of valid Unicode with no control character other than tab and
   newline. Bytes, `None`, a lone surrogate, NUL or an ANSI colour code score 0, with a reason; they never crash.
1. **One assistant turn.** The completion is read with `chat-format/render.py` `parse()`, as in `sft/tests/scorers.py`.
   It must be exactly one valid assistant turn. A reply that runs on into a made-up `tool` or `user` turn, uses
   look-alike markers (`<tool_call>`, `<think>`, `<｜think｜>`) or leaves `<|think|>` open scores 0. The closing
   `<|im_end|>` and `<|endoftext|>` are optional.
2. **No new tool call.** The answer is already in the transcript.
3. **A short visible reply.** The think span is not read. The reply must not be empty and has at most 1,000
   characters.
4. **Every `required` value** of `hidden/expected.json` appears in the reply as a whole value.
5. **No `wrong` value** of `hidden/expected.json` appears in the reply as a whole value.

`hidden/expected.json` is the ground truth. The model never sees it: the prompt is rendered from `messages.json` only
(`test_the_ground_truth_is_never_in_the_prompt`).

**Exact text.** Letter case, digits, units and spelling must match the tool. Only these are evened out, on both sides:
- Unicode NFC: two encodings of one Indic letter agree. Never NFKC.
- Invisible characters that never change a value are removed: U+200B and U+FEFF (the G10 text rule in
  `swe-task/hindi_text_prep.py`), and every other format character (soft hyphen, word joiner, direction marks and
  isolates), variation selectors and the combining grapheme joiner. Without this, `3<word joiner>2` would hide the
  wrong value `32` from the reader's eyes but not from the check.
- **ZWJ and ZWNJ** are kept inside an Indic word, where they change the spelling (`कर्<ZWJ>हाड`). After a digit, a
  Latin letter, a space or punctuation they join nothing, so they are removed (`3<ZWJ>1` is `31`).
- Runs of whitespace read as one space.

**A whole value** is not part of a longer word or number:

| Value | Found in | Not found in |
|---|---|---|
| `31.6` | `It is 31.6 °C.`, `(31.6)` | `131.6`, `31.65`, `-31.6` |
| `31` | | `31.6` |
| `1,250.00` | `₹1,250.00.` | |
| `test_leap_year` | `tests/test_dates.py::test_leap_year failed` | `test_leap_years` |
| `क्ष` | | `क्षि` (a vowel sign follows) |
| `क्<ZWNJ>ष` | `क्<ZWNJ>ष` | `क्ष` (ZWNJ dropped), `क्<ZWJ>ष` (the other joiner) |

A reply may quote other values of the tool result ("31.6 °C, feels like 34.2 °C" scores 1).

**Cut-off replies.** A reply cut off by the length limit is scored on what it holds. Cut inside a value ("It is
31."), inside the think span or inside a tool call, it scores 0. Cut after the full value ("It is 31.6 °C and"), it
scores 1: the RL reward view drops `<|im_end|>` (`rl-loop/team5_adapter.py`, `keep_stop=False`), so a finished reply
and a cut one look the same to the verifier. The trainer knows which replies hit the length limit.

## Writing a task

A task is a folder `tasks/<task_id>/`, where the folder name equals `id`.

| File | Content |
|---|---|
| `task.json` | `id`, `title`, `difficulty` (easy, medium, hard), `effort` (`1k`, `4k`, `16k`, `64k`), `source` (starts with `original`, says who wrote it and when), `author` (GitHub handle), `eligibility` (`eval` or `train`), `tags`, optional `note` |
| `messages.json` | the transcript in `render.py`'s message format: a system turn, the user's question, then one or more assistant tool calls each followed by a `tool` turn. It ends with a `tool` turn |
| `hidden/expected.json` | `{"required": [...], "wrong": [...]}`. `required`: values copied from the tool result, all of which the reply must hold. `wrong`: altered copies (rounded, retyped, a joiner dropped, a unit changed) that must score 0. They must never appear in the tool result |

`--check-task` checks all of this:
- the fields and their values, and that the id matches the folder;
- the transcript renders, ends with a tool turn and has an assistant tool call;
- every required value is in a tool result, and none is in the system or user text, so it can only come from the tool;
- no wrong value is in a tool result, and no value is both required and wrong;
- a reply quoting the required values scores 1, and a reply quoting each wrong value scores 0.

Then add the task's correct and wrong reply to `CASES` in `test_toolresult_verifier.py`. A test fails when a task has
no entry there.

**A broken task stops the run.** When scoring, a `hidden/expected.json` that is not JSON, has a duplicate key, has an
empty or non-list `required` or `wrong`, a value that is not a non-empty string, or a value that is both required and
wrong raises `ValueError`; a missing one raises `FileNotFoundError`. It is never scored as the model's mistake (an
empty `required` list would otherwise give 1 to every reply). `--check-task` reports the same problems as a list.

**Who may write a training task.** TSAI's data rule of 3 Nov (`../../rl-data/README.md`): training problems are written
by people. A task with `"eligibility": "train"` fails the lint if its `source` names a model. The twelve tasks here were
written by Claude (AI assistant) for naveen333nav (ten on 16 Nov, two on 23 Nov). Each `task.json` says so, and each
is `"eligibility": "eval"`. They test the verifier and can be used for evaluation.

## Tasks so far (12)

| Task | What a wrong reply does | Required | Wrong |
|---|---|---|---|
| `weather_decimal` | rounds a decimal | `31.6` | `31`, `32`, `31.0` |
| `order_total_field` | takes the subtotal instead of the total | `1,250.00` | `1,205.00`, `1,150.00` |
| `handbook_file_list` | drops a file or flattens a path | 3 paths | `handbook/vpn-setup.md`, `handbook/leave_policy.md` |
| `pytest_failed_test` | says all tests passed | `test_leap_year`, `1 failed`, `11 passed` | `12 passed`, `0 failed` |
| `shell_exit_code` | says the command worked | `1`, `ModuleNotFoundError: No module named 'yaml'` | `0`, the error with `yml` |
| `parcel_city_joiner` | drops the ZWJ of a Marathi name (eyelash RA) | `कर्‍हाड` | `कर्हाड`, `करहाड` |
| `currency_no_recompute` | recomputes the amount instead of quoting the tool | `21033.13` | `21033.125`, `21033`, `21000` |
| `event_id_case` | changes the letter case of an ID | `evt_7Hq2Lx` | `evt_7hq2lx`, `evt_7Hq2Ix`, `EVT_7HQ2LX` |
| `queue_retry_latest` | reports the first, failed call instead of the retry | `4318` | `4381`, `4,381` |
| `disk_usage_unit` | changes GiB to GB | `3.7 GiB` | `3.7 GB`, `3.97 GB`, `4 GiB` |
| `file_list_truncated` | the tool output is cut off (5 names of 1342); the reply counts the names shown | `1342` | `1340`, `1300`, `1,342` |
| `rate_api_error_page` | the tool returns an nginx HTML error page instead of JSON; the reply invents a rate | `502 Bad Gateway` | `502 Bad Request`, `503 Service Unavailable`, `504 Gateway Timeout` |

The Marathi spelling in `parcel_city_joiner` still has to be confirmed by a native reader (its `task.json` `note`).

## Limits

- **It checks values, not meaning.** "It is not 31.6 °C" scores 1. `test_meaning_is_not_judged` keeps this limit
  visible. Judging meaning needs a judge model.
- **Hedging between two real values passes.** "31.6 or 34.2" scores 1, because both are in the tool result. Only listed
  wrong values are refused.
- **Exact means exact.** `1,250` for `1,250.00`, `21,033.13` for `21033.13` or `3.7GiB` for `3.7 GiB` score 0. The system
  turn of every task asks the model to copy values exactly as the tool wrote them.
- **One spelling, one encoding.** Marathi also writes the eyelash RA as `ऱ्` (U+0931 + virama). NFC keeps it apart
  from the tool's `र्<ZWJ>`, so `कऱ्हाड` scores 0 on `parcel_city_joiner`
  (`test_the_other_encoding_of_eyelash_ra_is_a_different_spelling`). A native reader should say whether both should
  pass.
- **Look-alike letters are not mapped.** A Cyrillic `Е` inside a wrong value hides it from the wrong-value check, as
  NFKC is not used. The required value must still be there in the tool's own letters.
- **An invented value next to a reported error passes.** In `rate_api_error_page` a reply that reports
  `502 Bad Gateway` and also guesses a rate scores 1. Only listed wrong values are refused.
- **The tasks are hand-written and few.** They show that the verifier works; they are not a training set.

## Decontamination

Run on 23 Nov 2026 for all 12 tasks with `teams/09-evaluation/decontam/decontam_check.py` and `canary_scan.py` from
course `main` at `e554432`, fingerprints v2 full set (`set_sha256`
`2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`), on 24 documents: the rendered prompt
(`prompt_text()`) and `hidden/expected.json` of each task, one JSONL line each (`doc_id`, `text`). Result: **0
flagged, 0 canary hits** (canaries era-v5-lab, gpqa_diamond, hle, terminal_bench_2). Input file sha256:
`861a01cf652b9d91429b886ef8df4e43f7aeb512d564515497cae124f30dea9e`, written outside the repository. To repeat it, write
the same lines (`doc_id` `toolresult/<task_id>/prompt` and `.../expected`) and run both scripts on them. The first ten
tasks were also checked on 17 Nov 2026 (`main` at `5aed520`, 20 documents, 0 flagged, 0 hits).
