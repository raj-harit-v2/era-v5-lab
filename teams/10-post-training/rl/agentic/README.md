# Agentic tasks for RL data v1 (`agentic_verifier.py`, `tasks/`)

Gate 3 deliverable "one agentic verifier set: one exact command or patch check, one correct answer, one wrong answer"
(work order, 14 Nov). Registered as `agentic/<task_id>` in `../reward.py`.

```text
rl/agentic/
  README.md                   this file
  agentic_verifier.py         reward(), check_task() and the command line
  build_tasks.py              builds a task folder from an existing swe-envs/<instance_id>
  test_agentic_verifier.py    correct and wrong answers, malformed and cheating cases, lint
  tasks/<task_id>/            task.json, prompt.md (the model sees this), hidden/expected.json (never shown)
```

## What it adds to `swe/<id>`

`swe/<id>` scores one thing: a unified diff, applied to the base commit, then the hidden tests. An agentic trajectory
starts with a different action: a shell command (find the tests for this issue and run them). `swe` cannot score a
command. This set can.

- **command mode (new signal).** The model answers with one line in one ```` ```bash ```` block. The line is parsed and never given to a shell:
  `pytest` or `python -m pytest`, a short flag allowlist, relative paths; pipes, `;`, `&&`, quotes, `$`, `cd`, `-k`,
  `-x`, `-p`, `-c`, `--junitxml`, `..` and absolute paths all score 0. A valid command runs in the env's image
  (network off, the Docker limits of `swe-envs/verify.py`) with the hidden test patch applied. Reward 1 only if the
  set of tests it ran equals the set the repo's recorded test command runs, and every FAIL_TO_PASS test fails (the
  command reproduces the bug). The whole suite, a subset, the wrong file and a command that runs nothing all score 0;
  `pytest tests/x.py`, `python -m pytest -q tests/x.py` and `-v` all score 1 (a behavioural check, not string equality).
- **patch mode (a thin wrapper, no new signal).** One ```` ```diff ```` block, scored by `swe-envs/verify.py` `reward()`.
  It only adds the one-block output rule and the action-type check. Command mode also gets the hidden test patch inside its script (stdin), like patch mode. `task.json` carries `pool_overlap: swe/<id>`:
  do not put a patch task and its `swe/<id>` twin into one RL pool.

Output rules (both modes): text up to the last `<|/think|>` is ignored, an unclosed `<|think|>` has no answer, and the
reply may hold exactly one fenced block of the asked kind and none of another kind.

## Commands

```bash
python teams/10-post-training/rl/agentic/agentic_verifier.py --check-all        # recorded answer 1, wrong answer 0
python teams/10-post-training/rl/agentic/agentic_verifier.py --reward teams/10-post-training/rl/agentic/tasks/<task_id> completion.txt
python teams/10-post-training/rl/reward.py --check-all --type agentic
python -m pytest teams/10-post-training/rl/agentic/test_agentic_verifier.py -q -p no:cacheprovider
python teams/10-post-training/rl/agentic/build_tasks.py command <instance_id>    # a new command task from a swe env
```

Needs Docker; an env image that is absent is built from its Dockerfile (network needed once). The parser tests run
without Docker.

## Where the data comes from

- Issue text: the upstream GitHub issue, unchanged (`swe-envs/<id>/issue.md`). Tests, test command, FAIL_TO_PASS and
  PASS_TO_PASS: the upstream repository and the execution-verified record of `swe-envs/<id>/env.json`. Generator: none.
- The expected test set in `hidden/expected.json` is measured by running the recorded command through the verifier.
- `prompt.md` also lists the test files of the checkout (`git ls-files` in the env image) and starts with a fixed
  output-format header. **The header is harness text, not taken from a source** (the output protocol, no task content). It is
  the same kind of text as the output-format line of any prompt, but TSAI has not ruled on it; if it must be
  taken from a human-written source, replace `COMMAND_HEADER` and `PATCH_HEADER` in `build_tasks.py` and rebuild.
- The wrong patches in `test_agentic_verifier.py` are fixtures derived from a human gold patch, kept out of any pool.

## Chance level, and what the tasks are for

Each command task is in effect a choice among the test files in its prompt. `task.json` records
`candidate_test_files` and `chance_level` (1 divided by the number of `test_*.py` files listed; for example 0.25
for `humanize-26` with 4 files and 0.034 for `boltons-302` with 29). Read a pass rate against that number: a 25% pass
rate on `humanize-26` is chance, not skill. The five tasks (four command, one patch) demonstrate the verifier and are not an
RL pool; a pool needs many more tasks built with `build_tasks.py`.

## Limits

- Patch mode runs the candidate's code in pytest's process. The earlier claim that beating the report checks needs faked terminal output was wrong: attacks P1 and P1b rewrote `TestReport` and scored 1 (independent attack test, 18 Nov 2026). They now score 0 (`attack_fixtures/`, `test_agentic_verifier.py`), see `swe-envs/README.md`, "Known limits", for the residual and the shared-file change.
- A policy can score by matching words of the issue to a file name in the listing; that is the intended skill, but an
  easy issue can be solved by lexical overlap alone. Tasks are few (4 command, 1 patch).
- One test command family (pytest) and Python envs only.
