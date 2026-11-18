# RL data v1: rebuild check, verifier answers and manifests (15 Nov)

RL data v1 was built on 11 Nov from pinned bytes. That build was never committed. On 15 Nov it was rebuilt from the
same pins with the current week-3 builders and compared with the recorded hashes. The data files stay local; this
branch holds metadata only. Apple M1 Pro, CPU, Docker 29.9.2.

## Rebuild

At the rebuild stage, the week-3 versions of `rl-data/{build,build_math,stdio_check,math_check,survey,filter}.py` and
`sft/decontam_run.py` were byte-identical to the PR #54 versions used on 11 Nov. The final branch subsequently
hardens the local runner in `stdio_check.py`; it does not change the data builders or their rebuilt output. Command:
`work/wp4-rl-integration-2026-11-15/rldata_rebuild/run_rebuild.sh` (pins, build, decontam x2, MATH-500 guard,
assemble). It took 63 s. This is a local execution record: the wrapper scripts and raw inputs are not included in
this metadata-only submission. A fresh rebuild also needs the pinned source files and Team 9 fingerprints v2;
the manifests do not constitute a self-contained rebuild kit.

| File | sha256 (rebuild = 11 Nov record) | Rows |
|---|---|---:|
| code_contests v1 `cc.jsonl` | `91ee99512f0411aea2de4ca5eaf10b87b2d8f785ca73747bf8deb45dd6ea9be0` | 3,723 |
| MATH train v1 `math.jsonl` | `630c6dae44cd60ce8a35a6ce66ee391843a964e0dac8fab3b3e7eb5c7489a65c` | 7,234 |

Every intermediate file also matched: task files, decontam inputs, and both decontam clean files (`84b0a645…`,
`ca1073f2…`). Both decontam records are equal to the 11 Nov records except for the `run_at` timestamp. Canaries: 0
in both sets. All 39 code_contests and 7 MATH parquets matched their pins.

Funnel: code_contests train 13,328 → minus 7,819 Codeforces-sourced and 417 with fewer than 3 tests → 5,092 →
minus 1,369 flagged by fingerprints v2 → 3,723. By judge: aizu 1,970, hackerearth 1,056, codechef 489, atcoder 208.
MATH train 7,500 → minus 2 without `\boxed{}` → 7,498 → minus 175 v2-flagged and 91 sharing a 13-word run with
MATH-500 (2 in both) → 7,234.

## Verifier answers, human references only

| Family | Correct answer | Wrong answer | Where |
|---|---|---|---|
| stdio, per judge (aizu, atcoder, codechef, hackerearth) | the row's human solution from the pinned parquet scores 1. codechef and hackerearth have only Python 2 references, converted with lib2to3. | same program plus `print(0)` scores 0 | `rl-data/check_v1_human_references.py` (new) |
| math | `\boxed{reference answer}` scores 1 | `\boxed{answer+1}` scores 0 (5 tasks) | same file |
| SWE | gold patch scores 1 | no-op scores 0, through `rl/reward.py` | existing `rl/test_reward.py::test_swe_env_scores_gold_one_and_noop_zero_from_parallel_workers` (not duplicated) |
| Go | | | `rl/go` (another member's work). Its tasks were written by an AI assistant and are evaluation-only by their own README. Not RL data. |

The new check needs local data and Docker. It runs only when the file is named, so
`pytest teams/10-post-training/rl-data` does not collect it. A missing input fails the check and names the input:
without `G10_RL_V1_DIR` and `G10_CC_SOURCE_DIR`, both checks fail in 0.01 s. Docker must be running.

```bash
G10_RL_V1_DIR=<rebuild>/out/v1 G10_CC_SOURCE_DIR=<code_contests@802411c3>/data \
  python -m pytest teams/10-post-training/rl-data/check_v1_human_references.py -q -p no:cacheprovider
# 2 passed in 10.29s
python -m pytest teams/10-post-training/rl-data teams/10-post-training/rl/test_verifier.py teams/10-post-training/rl/test_reward.py -q -p no:cacheprovider -rs
# 88 passed, 2 skipped in 50.75s before the rename (the 2 skips were this check without inputs);
# after the rename: rl-data alone 25 passed in 6.59s, the check is not collected
```

Final verification used the existing environment with math-verify installed: the human-reference check plus
`rl-data/test_survey_math.py` passed all 15 tests in 13.26 s. The separate trainer math-task integration passed in
1.53 s. These supplement the base-environment test run recorded in `objective_v1_trainer.md`; they do not erase
its explicitly reported missing-input skips.

## Manifests

`rl-data/manifests/rl-code-code-contests-noncf.v1.json` and `rl-math-hendrycks-math-train.v1.json` record the
source repo, revision, each input file's sha256, the output sha256 and row count, the decontam record hash and the
rebuild command, with no rows. They also record the held-out boundaries:

- code_contests: train split only. Codeforces rows are out.
- MATH: train files only. MATH-500 is read only by the overlap guard.

They also record the id+text prompt pool for Team 9's `decontam_check.py --id-field id`:

| Pool | Rows | sha256 |
|---|---:|---|
| code_contests | 3,723 | `84b0a645…` |
| MATH | 7,234 | `5148ce7a…` |

The pool files are local, for the lead to hand on.

## Open gates (not closed here)

- Licences: `licences/licence_table.md` (line 141, summary line 287) marks `rl-code-code-contests` **allowed** after
  TSAI's 6 Nov answer, train splits only. That matches this build: train split only, Codeforces rows out.
  Hendrycks MATH has **no row**, so MATH is not approved for RL until a row and a decision exist.
- Python 2 references: the codechef and hackerearth tasks (489 + 1,056 in v1) have only Python 2 human
  references. The correct-answer check converts them with lib2to3. The lead decides whether to keep or drop them.
- Pass-rate filtering on the real starting model was not done. It needs the checkpoint (TSAI: use it when the
  checkpoint lands).
- No TACO rows are in RL data v1. The earlier TACO expected-output disagreements from the DT study do not affect
  these sets.
