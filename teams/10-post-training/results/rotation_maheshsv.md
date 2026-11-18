# Week-3 rotation (Team 10): SWE environment end to end in Docker

Rotation member maheshsv (Mahesh Sv), from Team 9. One environment; R1 is the run in Docker and R2 is the verifier result. Besides the gold patch and a no-fix patch (as in `rotation_asraj.md`), the environment gets three more controls (as in `rotation_chapanduk.md`): a correct fix written differently from the gold patch, a plausible partial fix, and the real fix plus a new test file (a reward-hacking attempt). R3 is one finding about the issue text. Patches and raw outputs are in `rotation_maheshsv_evidence/`.

## pallets__jinja-1204
Environment: `pallets__jinja-1204` (pallets/jinja, BSD-3-Clause, language python), upstream PR https://github.com/pallets/jinja/pull/1204, base commit `fd001b216a80`.

- Lab commit: `fb7d5e6a2a6a72042b6baa527190d6e1b8ee67fa` (tip of `g10-week3-post-training`)
- Docker: 29.8.2 linux/arm64 (Apple M2 Pro, runs are native to the arm64 VM; linux/amd64 was not run)
- Host Python for `verify.py`: 3.13.14
- Test command: `python -m pytest -p no:cacheprovider -o addopts= -q tests/test_api.py`
- FAIL_TO_PASS: 1 test, PASS_TO_PASS: 32 tests
- Wall time: 39 s for the gold check (includes the first image build), under 1 s for each patch run

### R1: end to end in Docker

Commands, from the repo root (`swe-envs/verify.py`, locked-down runs: `--network=none --memory=2g --cpus=2 --pids-limit=256 --cap-drop=ALL --security-opt=no-new-privileges`, non-root):

```
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/pallets__jinja-1204 --check --runs 5
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/pallets__jinja-1204 --patch teams/10-post-training/swe-envs/pallets__jinja-1204/gold.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/pallets__jinja-1204 --patch teams/10-post-training/results/rotation_maheshsv_evidence/pallets__jinja-1204_wrong.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/pallets__jinja-1204 --patch teams/10-post-training/results/rotation_maheshsv_evidence/pallets__jinja-1204_alt_fix.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/pallets__jinja-1204 --patch teams/10-post-training/results/rotation_maheshsv_evidence/pallets__jinja-1204_partial.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/pallets__jinja-1204 --patch teams/10-post-training/results/rotation_maheshsv_evidence/pallets__jinja-1204_tamper.patch
```

The image built from the committed `Dockerfile` with no change to any environment file. Gold check (the hidden test fails on the base commit and passes after the gold patch, every run, with the report-integrity sentinel):

```json
{
 "instance_id": "pallets__jinja-1204",
 "repo": "pallets/jinja",
 "f2p": 1,
 "p2p": 32,
 "image_id": "sha256:f4f31226fbbd",
 "runs": 5,
 "problems": [],
 "fails_before": "5/5",
 "passes_after": "5/5",
 "seconds": 0.5,
 "ok": true
}
```

The counts and the 5/5 results match row 9 of `swe_gold_check.md`. The image id differs from the one recorded there (`sha256:855f6b973d2c`); this is a new build on another machine, and no claim is made that the builds are bit-identical.

### R2: verifier result

| Candidate patch | Expected reward | Reward | Failed tests / reason |
|---|---|---|---|
| gold.patch (upstream fix) | 1 | 1 | none |
| wrong.patch (adds a note file, no fix) | 0 | 0 | 1 failed (the FAIL_TO_PASS test) |
| alt_fix.patch (a separate `__contains__` method on `Undefined` that raises `UndefinedError`; no `CHANGES.rst` edit) | 1 | 1 | none |
| partial.patch (`Undefined.__contains__` returns `False`, so `in` no longer reaches `__iter__` but still does not raise) | 0 | 0 | 1 failed (the FAIL_TO_PASS test) |
| tamper.patch (gold code fix plus a new `tests/test_rotation_extra.py`) | 0 | 0 | rejected before tests run: patch edits test files: ['tests/test_rotation_extra.py'] |

The verifier accepts a correct fix that is not textually the gold patch, so the reward follows behaviour and not the diff. The tamper patch carries the real fix, so a verifier that only ran the tests would give it 1; this one gives 0 because the patch touches a test path.

**Result: PASS.** The gold check exit code is 0; the verifier gives 1 to both correct fixes, and 0 to the no-fix, partial and test-tampering patches.

Full verifier outputs (also in `rotation_maheshsv_evidence/pallets__jinja-1204_results.json`):

```json
{
 "gold": {
  "instance_id": "pallets__jinja-1204",
  "reward": 1,
  "failed": [],
  "n_failed": 0,
  "seconds": 0.6
 },
 "wrong": {
  "instance_id": "pallets__jinja-1204",
  "reward": 0,
  "failed": [
   "tests.test_api.TestUndefined::test_default_undefined"
  ],
  "n_failed": 1,
  "seconds": 0.5
 },
 "alt_fix": {
  "instance_id": "pallets__jinja-1204",
  "reward": 1,
  "failed": [],
  "n_failed": 0,
  "seconds": 0.5
 },
 "partial": {
  "instance_id": "pallets__jinja-1204",
  "reward": 0,
  "failed": [
   "tests.test_api.TestUndefined::test_default_undefined"
  ],
  "n_failed": 1,
  "seconds": 0.5
 },
 "tamper": {
  "instance_id": "pallets__jinja-1204",
  "reward": 0,
  "reason": "patch edits test files: ['tests/test_rotation_extra.py']"
 }
}
```

### R3: finding, the issue text does not reproduce on the base commit

`issue.md` reports a `TypeError` from `'value' in data['missing_key']` under `StrictUndefined` (Jinja 2.11.2, Python 3.6) and expects an `UndefinedError`. I ran the issue's two templates, and the hidden test's template `{{ 'foo' in missing }}`, in the environment image with each `Undefined` class, on the base commit and again after the gold patch (`pallets__jinja-1204_issue_repro.py`, output in `pallets__jinja-1204_issue_repro.log`, both runs with `--network=none`).

| Undefined class | Template | Base commit | Base + gold.patch |
|---|---|---|---|
| `StrictUndefined` (the issue's case) | `{{ 'value' in data['missing_key'] }}` | raises `UndefinedError` | raises `UndefinedError` |
| `StrictUndefined` (the issue's case) | `{% if 'value' in data['missing_key'] %}{% endif %}` | raises `UndefinedError` | raises `UndefinedError` |
| `Undefined` (the hidden test's case) | `{{ 'foo' in missing }}` | renders `False` | raises `UndefinedError` |

- On the base commit (Jinja 3.0.0a1, Python 3.9) the issue's own example already gives the behaviour the issue asks for, with the exact message it expects (`'dict object' has no attribute 'missing_key'`). No `TypeError` appears for any of the four classes.
- The hidden test checks a different case: `in` on the default `Undefined`, which returns `False` before the fix. The issue text names only `StrictUndefined` and never says the default `Undefined` should raise.
- So a solver that reads only `issue.md` and runs its example sees nothing to fix, and a no-change patch satisfies the issue as written but gets reward 0 (the `wrong.patch` row above).
- `swe_env_review.md` marks this environment `keep` with the note that the expected error for `in` on `Undefined` is explicit. On this evidence the tests ask for more than the issue states, which is the `keep-flagged` case described in `swe-envs/README.md`. I suggest the team re-review the verdict. I did not change `env.json` or any other environment file.

What this does not show: why the `TypeError` appeared on Jinja 2.11.2 with Python 3.6 (that version was not run), and whether the same holds on linux/amd64.

## Summary

| Environment | Gold check (5 runs) | gold | wrong | alt_fix | partial | tamper |
|---|---|---|---|---|---|---|
| `pallets__jinja-1204` | fails before 5/5, passes after 5/5, ok | 1 | 0 | 1 | 0 | 0 |

The environment builds, is deterministic over 5 runs, and the verifier separates the two correct fixes from the three wrong patches. No problem found in the image or the verifier. One open point for the team: the issue text does not reproduce on the base commit and does not describe the behaviour the hidden test checks (R3), so the `keep` verdict may need to become `keep-flagged`.
