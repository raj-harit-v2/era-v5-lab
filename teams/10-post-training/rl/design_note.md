# RL code tasks and verifier: design note

Code is in `rl/` (the verifier and its tests pass). This note explains the design and the open questions.

## Goal

A set of original Python coding tasks with hidden tests, and a verifier that gives a binary reward (1 or 0) for a model's completion. This is the verifiable reward for the RL loop. A policy trained against a weak verifier learns to fool it, so the verifier is the main design problem.

## The key decision: expected answers never enter the sandbox

A common design runs the candidate's code and the test reporter in the same process and reads the result from a file that process can write. We reproduced the consequence on such a verifier: a patch that appends an `atexit` hook forges an all-pass report and gets reward 1.

Here the sandboxed process receives only inputs:
- `cases.json`: a list of `{args, kwargs}`, visible and hidden cases mixed in one unlabeled list.
- `solution.py`: the candidate's code.

The child process calls the function on each input and writes the outputs. The verifier (the parent) compares the outputs with the expected values, which stay in the parent and are never written to the sandbox folder. To forge a pass the candidate would have to know the answers to hidden inputs, which means solving the task. `sys.exit(0)`, printing the expected text, a forged results file and a patched harness have nothing to forge.

Limit: this works for tasks that call a function and compare the JSON result. Tasks that need a custom check (any valid answer accepted) are out of scope for v1.

## Task folder layout

```
rl/
  README.md
  verifier.py            reward(task_dir, completion, sandbox) -> {"reward": 0|1, "reason": ..., "passed", "total"}
  _sandbox_child.py      runs inside the sandbox: imports solution.py, calls the entry point on the inputs
  test_verifier.py       pytest: correct and wrong answer, plus the cheating cases
  tests/fixtures/        a test-only fixture task (not part of the dataset)
  tasks/<task_id>/
    task.json            id, title, entry_point, time_limit_s, difficulty, source, tags
    prompt.md            what the model sees: problem text, signature, 3 examples
    visible_tests.json   the 2-3 cases shown in the prompt
    hidden_tests.json    10 or more cases, never shown
    reference.py         reference solution (proves the tests are satisfiable)
```

A case is `{"args": [...], "kwargs": {...}, "expected": <json>}` or `{"args": [...], "raises": "ValueError"}`. Values are plain JSON (tuples become lists; bool is not an int; an int is accepted where a float is expected but a float is not accepted where an int is expected; floats compare with a tolerance of 1e-9). A `raises` case accepts the named exception or any subclass of it. `python teams/10-post-training/rl/verifier.py --check-task teams/10-post-training/rl/tasks/<id>` lints a task (files present, 2-3 visible and 10+ hidden cases, no repeated inputs, no hidden call copied into the prompt (in Python or JSON syntax), the prompt names the function, source starts with "original") and runs the reference solution through the verifier, which must score 1. It also checks that a stub returning `None` does not score 1.

## How a completion is parsed

1. Fences are read line by line and paired in order. The last block labelled `python`, `python3`, `py` or with no label is used. Blocks in other languages (output, bash, text) are ignored and cannot shift the pairing. No usable block, or a block that is never closed (a cut-off answer): reward 0.
2. Reject it if it is longer than 20,000 characters, empty, or contains a NUL byte.
3. The entry point must exist when `solution.py` is imported. Otherwise every case fails.

## Sandbox

Two modes, same protocol:
- `process`: child process with resource limits (memory 512 MB, file size 10 MB, no fork or threads, no core files), clean environment, `python -B -s` with a fixed `PYTHONHASHSEED` (so set order does not make rewards flaky), its own process group killed on timeout, output discarded. For unit tests. It does not hide the task folder or block the network (a test documents this).
- `docker`: `--network=none --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 32 --memory 512m --memory-swap 512m --cpus 1 --ulimit fsize=10000000 --ulimit core=0`, a 16 MB `/tmp` tmpfs, non-root user, and only the work folder mounted. The file-size limit stops a candidate from filling the host disk through the mounted folder. The task folder is not in the container. Use this for training.

Timeouts: 2 s per case, `time_limit_s` plus 3 s for the whole run.

## Reward rule

Reward is 1 only if the child finished, the result file has exactly one well-formed entry per case, and every visible and hidden case matches. Otherwise 0. No partial credit in v1. The result is never taken from stdout or the exit code.

The reply to the caller contains counts (passed and total), never which hidden case failed or what it expected. The training loop must feed back only the `reward` value, never the whole reply: the counts are for humans and logs, and a policy that saw them could learn the hidden tests one at a time.

## Cheating cases (each is a test in `test_verifier.py`, all score 0)

| Case | Defence |
|---|---|
| `sys.exit(0)` or `os._exit(0)` at import, `sys.exit` inside the function | no result file, or the case is recorded as an error |
| Print the expected output or "PASSED" | stdout is discarded |
| Hard-code the visible examples | hidden cases are mixed in and must pass |
| Forge `results.json` (at import and from `atexit`) | the forger does not know the expected values |
| Patch `json.dumps`, `print`, builtins | same: no knowledge of the answers |
| Infinite loop in the function, at import, or `time.sleep(60)` | per-case alarm and wall-clock kill of the process group |
| Memory bomb, writing a 50 MB file | address-space and file-size limits |
| Fork bomb | process limit (process mode), pids-limit (docker) |
| Flood stdout | output discarded |
| Return a set or other non-JSON value, `True` for `1`, a wrong exception type | strict comparison |
| Read the hidden tests from disk | not mounted in docker (tested); open in process mode (documented) |
| Reach the network, write to `/etc` | `--network=none`, `--read-only` (tested in docker) |

## The ten tasks

| Task | Difficulty | Topic |
|---|---|---|
| `indic_cluster_count` | hard | user-perceived characters in Indic text (marks, virama, ZWJ/ZWNJ) |
| `topo_order` | hard | smallest dependency order, cycle detection |
| `normalize_phone_in` | medium | Indian mobile numbers, any Unicode digits |
| `parse_duration` | medium | `"1h30m"` to seconds, strict validation |
| `session_split` | medium | split event times into sessions |
| `ring_sums` | medium | sum of each concentric ring of a grid |
| `wrap_text` | medium | word wrap with long-word splitting |
| `next_business_day` | easy | next weekday that is not a holiday, strict date format |
| `transliterate_digits` | easy | digits between ASCII, Devanagari, Bengali, Tamil |
| `weighted_median` | easy | weighted median with error cases |

Each reference solution scores 1 in both sandboxes, and simple wrong answers score 0. Expected values were produced by the reference solutions, so the tests were also checked in three other ways: a second implementation of each task, written from the prompt alone, agrees with the reference on all test inputs and on about 4,000 random inputs per task; mutation testing (flipped comparisons, shifted constants, swapped `and`/`or`) leaves only mutants that cannot change an output; and the prompts were re-read for ambiguity.

## Originality and decontamination

Tasks are original: not taken from HumanEval, MBPP or any benchmark. `source` in `task.json` records this. Run the repository's decontamination check on the prompts before merging.

## Decisions (TSAI answers of 5 Nov) and what was built

1. **Entry point.** One wrapper `reward(env_id, output)` returns a score and an info dict. Each environment registers its own checker under its `env_id`. Built in `rl/reward.py` (PR #33); the ten code tasks register through `rl/verifier.py`.
2. **Custom checkers.** Not in v1. Every case in the ten tasks has exactly one expected value or one expected exception, so one exact check is enough. A hook can be added later, with its own tests, only when a real task needs several valid answers.
3. **Cost per call.** A Docker call is about 0.23 s (0.04 s in process mode). `rl/pool.py` keeps a warm container per worker (one worker per CPU core), reuses it for a batch of rollouts and cleans it after each one. Measured in `results/reward_pool_bench.md` (8 CPUs, Docker Desktop): code tasks 21.42 rollouts/s with the pool, 12.45 in parallel and 4.38 serial. SWE environments are not pooled, because a reused container with a writable repository is unsafe; 4 parallel workers give 2.15 rollouts/s.

## Out of scope

Model training, repository-patch environments, SFT data.
