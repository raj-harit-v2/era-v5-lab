# RL code tasks and verifier

`verifier.py` turns a model completion into a binary reward for a task in `tasks/<task_id>/`. The design and the cheating cases are in `design_note.md`.

## Use

```bash
python teams/10-post-training/rl/verifier.py --check-task teams/10-post-training/rl/tasks/<task_id>               # lint, and the reference must score 1
python teams/10-post-training/rl/verifier.py --reward teams/10-post-training/rl/tasks/<task_id> completion.txt    # {"reward": 0|1, ...}
python teams/10-post-training/rl/verifier.py --reward teams/10-post-training/rl/tasks/<task_id> completion.txt --sandbox docker   # for training
python -m pytest teams/10-post-training/rl/test_verifier.py -q -p no:cacheprovider
```

The reply holds counts for humans and logs. The training loop must use only the `reward` value. The reply holds counts for humans and logs; the training loop must use only the `reward` value. Docker mode needs the image `python:3.12-slim` (or set `G10_RL_IMAGE`). The docker tests are skipped when docker or the image is missing.

## Writing a task

A task is a folder `tasks/<task_id>/` (the folder name equals `id`):

| File | Content |
|---|---|
| `task.json` | `id`, `title`, `entry_point`, `time_limit_s`, `difficulty` (easy, medium, hard), `source` (starts with `original`, then the author and date), `tags` |
| `prompt.md` | the problem, the exact signature, 2-3 examples. Never a hidden input |
| `visible_tests.json` | 2-3 cases, the same ones the prompt shows |
| `hidden_tests.json` | 10 or more cases: edge cases, other sizes, other kinds of input |
| `reference.py` | your own solution to the task |

A case is `{"args": [...], "kwargs": {...}, "expected": <json value>}`, or `{"args": [...], "raises": "ValueError"}` when the function must raise. Expected values are plain JSON; a returned tuple is compared as a list.

Rules for the dataset: tasks must be original (not taken from HumanEval, MBPP or any benchmark), the reference solution must score 1, and the hidden tests must not appear in the prompt. Run the repository's decontamination check on the prompts before merging.

## One reward entry point and the warm pool (`reward.py`, `pool.py`)

TSAI (5 Nov, on PR #30): one wrapper `reward(env_id, output)` that returns a score and an info dict, with each environment registered under its env_id, and a warm container pool with one worker per CPU core.

```python
import importlib.util
spec = importlib.util.spec_from_file_location("reward", "teams/10-post-training/rl/reward.py")
reward = importlib.util.module_from_spec(spec); spec.loader.exec_module(reward)

score, info = reward.reward("code/parse_duration", completion)       # rl/tasks/<task_id>, this verifier
score, info = reward.reward("swe/pallets__click-1934", patch_text)   # swe-envs/<instance_id>, swe-envs/verify.py

with reward._pool().CodePool(workers=8) as cp:                        # warm pool for code tasks
    reward.configure(code_runner=cp.runner)
    ...
```

- `register("<type>", checker)` adds an environment type. An unknown or unsafe env_id raises `KeyError`. It never scores 0 silently, because a silent 0 looks like a real failure to the trainer.
- **Code pool:** one long-lived container per worker, with the same limits as the `docker` sandbox, reused for a batch of rollouts. After every rollout the pool:
  - empties `/tmp` and the work folder;
  - kills every process the candidate left behind (PID 1 is a small reaper, so killed processes cannot linger as zombies);
  - recycles the container after a timeout, a failed cleanup or 200 uses.

  The expected answers still never enter the container.
- **SWE envs are not pooled.** Their tests write into the repository, so a reused container could carry a planted change into the next rollout. Pre-started single-use containers measured slower than plain parallel `docker run --rm` (see the bench). So each SWE rollout gets a fresh container, and the trainer runs them in parallel. `swe-envs/verify.py` accepts an `executor`, so a safe reusable design can plug in later.
- Throughput: `results/reward_pool_bench.md` (`python rl/bench_pool.py --write results/reward_pool_bench.md`).
- Every reference solution and gold patch scores 1, and every wrong answer scores 0: `python rl/reward.py --check-all [--pool]`.

## Session 18 objective (`objective_v1.py`)

`objective_v1.md` is the v1 rule. Group advantage is the reward minus the group mean, with no division by the standard deviation. Groups whose rewards are all equal are dropped. A token whose importance ratio is outside `[1 - 0.2, 1 + 0.2]` is masked out of the sum. The trainer minimizes the returned loss and skips the step when every group was dropped.

```bash
python -m pytest teams/10-post-training/rl/test_objective_v1.py -q -p no:cacheprovider
```

## Go tasks

The Go verifier, its runner, the Docker image and the Go tasks are in [`go/`](go/README.md). They use `verifier.py` from this folder. `reward.py` registers them as `go/<task_id>` with the docker sandbox by default (the `process` sandbox is for unit tests), and `python rl/reward.py --check-all --type go` checks them (needs the `g10-go-rl:1` image).

## Indic tasks

Indic short-answer tasks are in [`indic/`](indic/README.md): an Indic prompt, and one checkable answer in `<answer>...</answer>` (an integer in any script's digits, a word in the task's script, or a choice label). `indic/indic_verifier.py` checks the answer exactly after normalising it. It runs no code, so it needs no container. `reward.py` registers it as `indic/<task_id>`, and `python rl/reward.py --check-all --type indic` runs without docker.

Agentic tasks (one pytest command or one patch, run in a SWE env image) are in [`agentic/`](agentic/README.md). `reward.py` registers them as `agentic/<task_id>`; `python rl/reward.py --check-all --type agentic` needs docker.

Math tasks (an exact boxed answer from the RL data v1 math pool, pinned by SHA-256) are in [`math_pool/`](math_pool/README.md). `reward.py` registers them as `math_pool/<task_id>`; they need the pool (`G10_MATH_POOL`) and `math-verify==0.9.0`. TSAI has not ruled on MATH for RL.

There are two math env types on purpose: `math_pool` (this set) checks one boxed answer against a record pinned in the RL data v1 pool, so it scales to thousands of problems but needs the pool; `math` (the owner's `rl/math`, a separate PR) holds small self-contained tasks with their answers in the repository and an `<answer>` tag.

JavaScript and TypeScript tasks (Exercism exercises, hidden jest tests, docker image `g10-jsts-rl:1`) are in [`jsts/`](jsts/README.md). `reward.py` registers them as `js/<task_id>` and `ts/<task_id>`; `python rl/reward.py --check-all --type js` (or `ts`) needs docker and the image.

## Tool-result tasks

Tool-result tasks are in [`toolresult/`](toolresult/README.md): a transcript that ends with a tool result, and a reply that must report the tool's values exactly (no rounding, retyping or new tool call). `toolresult/toolresult_verifier.py` checks the reply for the required values as whole values and refuses listed wrong values. It runs no code, so it needs no container. `reward.py` registers it as `toolresult/<task_id>`, and `python rl/reward.py --check-all --type toolresult` runs without docker.

## JavaScript tasks

The JavaScript verifier, its runner, the Docker image and the JavaScript tasks are in [`js/`](js/README.md). They use `verifier.py` from this folder via `js_verifier.py`. `reward.py` registers them as `js/<task_id>` with the docker sandbox by default (the `process` sandbox is for unit tests), and `python rl/reward.py --check-all --type js` checks them (needs the `g10-js-rl:1` image). Node.js 26 or later is required.

## Files in this folder

| File | What it is |
|---|---|
| `verifier.py`, `_sandbox_child.py`, `test_verifier.py` | The verifier: binary reward for one task, expected answers kept outside the sandbox. |
| `tasks/` | The original coding tasks (see "Writing a task"). |
| `reward.py`, `test_reward.py` | The one `reward(env_id, output)` entry point for code, SWE, Indic and Go environments. |
| `jsts/` | The JavaScript and TypeScript verifier set: hidden jest tests in a docker image, Exercism tasks, tests. |
| `math_pool/` | The pool-pinned math verifier set: boxed exact answer, pins into the RL data v1 math pool, tests. |
| `agentic/` | The agentic verifier set: command and patch checks, its tasks and tests. |
| `indic/` | The Indic verifier set: exact-answer reward, its tasks and tests, and the template generator. |
| `toolresult/` | The tool-result verifier set: exact tool-result text in the reply, its ten tasks and tests. |
| `js/` | The JavaScript verifier set: Node.js 26, sandboxed execution, its tasks and tests. |
| `indic_prompts_v0.md` | Indic prompt families with checkable answers, who writes them, the Team 2 check and the status. |
| `objective_v1.py`, `objective_v1.md`, `test_objective_v1.py` | Session 18 objective: group advantage, equal-reward drop, trust-region mask. |
| `small_rl.py`, `test_small_rl.py` | Local RL loop on one code task. The result is `results/small_rl.md`. |
| `pool.py`, `bench_pool.py` | The warm container pool for code tasks, and the rollouts-per-second benchmark. |
| `design_note.md` | Design, the cheating cases and open questions. |
| `decontam_report.md` | Benchmark-overlap check of the RL sets (see below). |

## Decontamination of the RL sets

`decontam_report.md` is the result of checking the RL sets TSAI allowed on 6 Nov against Team 9's benchmark fingerprints v2 (full set, with a canary scan). It lists, per set, the rows in, flagged and kept, the benchmarks hit, the benchmark items with the largest overlap and the input file hashes. Section 6 gives the commands to reproduce a run, and section 8 says what the check does not cover.

The report is written by the SFT tools, not by hand: `sft/decontam_run.py` checks one set and `sft/decontam_report.py` builds the report (`--title "RL decontamination report"`). How to run them is in `sft/README.md`. Do not put benchmark text in this file or in the run records: only set names, counts, document ids, benchmark item ids, offsets and sha256 values.
