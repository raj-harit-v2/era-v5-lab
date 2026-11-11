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
