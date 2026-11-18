# Code verifier and RL data v1 note, 15 Nov 2026

Three findings about the stdio code reward and the RL data v1 code_contests tasks. The reward audit uses completions
of a public surrogate model (Qwen2.5-Coder-7B-Instruct), one sampling seed; the statement check is a property of the
data file and uses no model. Nothing here changes the reward function or the data build; it is evidence for a
decision. No task ids, statements, tests or completions are in this report or its evidence files.

## 1. Scoring speed with identical rewards (R1)

603.5 s to 36.3 s on the same 1,536 completions with byte-identical reward vectors (early exit at the first wrong
answer in the local runner, plus a pool of small scorer processes started before the models load). The matched table,
command and limits are in `code_rl_e1_20261115.md` section 1. Rewards are byte-stable; the failure reason (error vs
timeout) is not, for one or two programs per run.

## 2. Independent audit of the reward with tests it never used (R5)

RL data v1 keeps the first 20 tests of each code_contests problem; the pinned source rows hold more (median 101).
`rl-loop/pilots/fable_e1_20261115/modal_audit.py` fetched the pinned parquet shards of `deepmind/code_contests` @
`802411c3` (31 files, every sha256 equal to the task's recorded hash, every kept-20 prefix equal to the task's tests),
took up to 80 unused tests per task and ran every reward-1 completion of the E1 screen on them.

- Command: `G10_E1_WORK=<private folder> modal run modal_audit.py::audit --run-id e1a` (from the pilot folder).
- Hardware: Modal CPU, 4 cores for the fetch, 32 cores for the run step (network blocked), 32-process scorer pool.
- Evidence: `fable_20261115_evidence/reward_audit_e1a.json`.

| | Count |
|---|---:|
| Reward-1 completions audited | 162 (56 tasks, 4,480 unused tests) |
| Pass every unused test | 157 |
| Fail an unused test | **5 (3.1%)**: 3 runtime errors, 2 wrong answers; no time-limit failures |
| Tasks where every rewarded completion fails the unused tests | 3 of 56 |
| Tasks where some do | 2 of 56 |

*Surrogate completions (base model, before training), one sampling seed.*

Final useful output:

```
"fetch": {"tasks_with_a_pass": 56, "files": 31, "kept_prefix_mismatch": 0, "no_hidden_tests": 0, "hidden_tests": 4480, "file_sha_mismatch": 0}
"verdict_on_hidden_tests": {"pass": 157, "runtime_error": 3, "wrong_answer": 2}, "false_positive_share": 0.0309
```

On this cohort the 20-test reward is mostly sound: about 3% of the rewards it pays are for programs that are wrong on
tests it did not look at, and three cohort prompts are "mixed" only because of such false positives. After 60 steps of
RL the false-positive share of rewarded completions rose from 1.2% to 3.0% on fresh samples
(`code_rl_e1_20261115.md` section 4). The unused tests never enter training.

Cost: $0.04 (ledger estimate).

## 3. 116 code tasks have no problem description (R6)

`rl-data/statement_check.py` (new; test in `rl-data/test_rl_data.py`) measures the text before the first
"Example" / "Sample Input" / "Input" heading and flags fewer than 40 characters. Re-run on the PR tree on 15 Nov:

```bash
python rl-data/statement_check.py <RL data v1 cc.jsonl, sha256 91ee9951...9be0> --ids-out <private file>
# {"tasks": 3723, "flagged": 116, "min_chars": 40, "by_judge": {"aizu": {"tasks": 1970, "flagged": 102}, "atcoder": {"tasks": 208, "flagged": 3}, "codechef": {"tasks": 489, "flagged": 1}, "hackerearth": {"tasks": 1056, "flagged": 10}}}
```

Apple M1 Pro CPU, under one second. 116 of 3,723 tasks are flagged (3.1%): 102 Aizu (5.2% of Aizu), 10 HackerEarth,
3 AtCoder, 1 CodeChef; the flagged statements are typically about 50 characters long. The builder only checks that the
source `description` field is non-empty. Five of them were in the E1 screen and all five were all-fail: they cannot be
solved as posed and waste rollouts. A regex is not a ruling: the list should get a human look, then be dropped or
flagged. The ids are not published here.

## Not measured

- The false-positive rate for other task families, or on the run's own final training completions.
- Whether scoring evaluations on kept plus unused tests by default changes any conclusion (it would make the reward
  stricter; cost is cents per run on CPU).
- A human review of the 116 flagged statements.
- Docker-mode scoring speed (early exit applies to the local runner only).
