# Task 11 handoff validation

Anirudh Narla ran the CPU experiments in [the report](../dt_then_rl.md). The handoff audit checked the committed analysis summaries against the per-step metrics and reran the affected test suites on the Week 3 branch with the handoff changes applied.

- There are 540 unique condition, arm, seed, and step records. The DT subset contains six runs with 30 optimizer updates each. Every DT step records zero deleted weights becoming nonzero.
- Both DT summaries record 348,469 initial deletions and 348,469 deleted weights still zero at the end of the recorded mask summary. Their three per-seed changes are positive, and the mean per-seed change agrees with the recorded aggregate to the precision stored.
- The three-seed all-trainable mean is 0.4268 to 0.6383 (reported paired change +0.2116). The experts-only mean is 0.4268 to 0.5013 (+0.0745). The underlying per-prompt evaluation scores and checkpoint were private inputs, so the audit did not recompute confidence intervals or rerun the original experiment.
- The canary configuration parses and uses the Team 5 adapter, stdio scoring, the saved DT SFT state and keep mask, and three `objective_v1` steps. A run on the delivered checkpoint is pending the staged inputs.

Local CPU regression, Python 3.12.14 and PyTorch 2.14.1, from the repository root:

```text
$ PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 python -m pytest teams/10-post-training/rl-loop teams/10-post-training/dt/tests teams/10-post-training/sft/bench/tests teams/10-post-training/chat-format -q -p no:cacheprovider
145 passed, 44 skipped in 146.32s
```

The nine tests in `rl-loop/test_keep_zero.py` also passed in a separate run (30.76 s).

## Review follow-up

- A Docker fixture run exercised the strict verifier preflight and threaded scoring. The same program scored `1.0` and `0.0` against two separate expected outputs. A regression test simulates Docker startup failure and checks that the preflight and pooled scoring raise an error.
- The resume tests reject a changed SFT checkpoint, binary mask, mask metadata, enforcement mode, and restored weights that violate the mask. A separate test checks that vLLM with `model.init_state` fails before the engines load.
- The paired-analysis tests cover aligned inputs and reject mismatched prompt sets, order, score counts, evaluation endpoints, and historical rows without a prompt fingerprint.

The same affected-area CPU command passed again after the fixes: `153 passed, 44 skipped in 153.94s`.

Reviewer follow-up on scan timing and mask storage. The keep-zero integration test checks the per-step timing field and the persistent tensor byte count.

```text
$ PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 python -m pytest teams/10-post-training/rl-loop/test_keep_zero.py teams/10-post-training/rl-loop/test_resume_state.py -q -p no:cacheprovider
18 passed in 19.56s
```
