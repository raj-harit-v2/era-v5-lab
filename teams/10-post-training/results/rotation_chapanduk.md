# Week-3 rotation (Team 10): SWE environment end to end in Docker

Rotation member chapanduk (Shivam Kumar). One environment; R1 is the run in Docker and R2 is the verifier result. Besides the gold patch and a no-fix patch (as in `rotation_asraj.md`), the environment gets two harder negative controls: a plausible partial fix, and the real fix plus a new test file (a reward-hacking attempt). Patches and raw outputs are in `rotation_chapanduk_evidence/`.

## python-humanize__humanize-41
Environment: `python-humanize__humanize-41` (python-humanize/humanize, MIT, language python), upstream PR https://github.com/python-humanize/humanize/pull/41, base commit `5dc4b8270d4a`.

- Lab commit: `ff0f656ebfdb7d6c0b80dc2c33f1f0b1e789d9f9` (tip of `g10-week3-post-training`)
- Docker: 28.3.3 linux/arm64
- Test command: `python -m pytest -p no:cacheprovider -o addopts= -q tests/test_number.py`
- FAIL_TO_PASS: 5 tests, PASS_TO_PASS: 135 tests
- Wall time: 52 s for the gold check (includes the first image build), about 2 s for the four patch runs

### R1: end to end in Docker

Commands, from the repo root (`swe-envs/verify.py`, locked-down runs: `--network=none --memory=2g --cpus=2 --pids-limit=256 --cap-drop=ALL --security-opt=no-new-privileges`, non-root):

```
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/python-humanize__humanize-41 --check --runs 5
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/python-humanize__humanize-41 --patch teams/10-post-training/swe-envs/python-humanize__humanize-41/gold.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/python-humanize__humanize-41 --patch teams/10-post-training/results/rotation_chapanduk_evidence/python-humanize__humanize-41_wrong.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/python-humanize__humanize-41 --patch teams/10-post-training/results/rotation_chapanduk_evidence/python-humanize__humanize-41_partial.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/python-humanize__humanize-41 --patch teams/10-post-training/results/rotation_chapanduk_evidence/python-humanize__humanize-41_tamper.patch
```

Gold check (the hidden tests fail on the base commit and pass after the gold patch, every run, with the report-integrity sentinel):

```json
{
 "instance_id": "python-humanize__humanize-41",
 "repo": "python-humanize/humanize",
 "f2p": 5,
 "p2p": 135,
 "image_id": "sha256:c9edec8f5a0f",
 "runs": 5,
 "problems": [],
 "fails_before": "5/5",
 "passes_after": "5/5",
 "seconds": 0.5,
 "ok": true
}
```

### R2: verifier result

| Candidate patch | Expected reward | Reward | Failed tests / reason |
|---|---|---|---|
| gold.patch (upstream fix) | 1 | 1 | none |
| wrong.patch (adds a note file, no fix) | 0 | 0 | 5 failed |
| partial.patch (strips the minus sign but never puts it back (`-1000000` gives `1.0 million`)) | 0 | 0 | 6 failed |
| tamper.patch (gold fix plus a new `tests/conftest.py`) | 0 | 0 | rejected before tests run: patch edits test files: ['tests/conftest.py'] |

It fails all 5 FAIL_TO_PASS tests and also breaks the PASS_TO_PASS case `-100`, which the base code already handled. The tamper patch carries the real fix, so a verifier that only ran the tests would give it 1; this one gives 0 because the patch touches a test path.

**Result: PASS.** The gold check exit code is 0; the verifier gives 1 only to the real fix, and 0 to the no-fix, partial and test-tampering patches.

Full verifier outputs:

```json
{
 "gold": {
  "instance_id": "python-humanize__humanize-41",
  "reward": 1,
  "failed": [],
  "n_failed": 0,
  "seconds": 0.6
 },
 "wrong": {
  "instance_id": "python-humanize__humanize-41",
  "reward": 0,
  "failed": [
   "tests.test_number::test_intword[test_args12--1.0 billion]",
   "tests.test_number::test_intword[test_args17--6.0 trillion]",
   "tests.test_number::test_intword[test_args21--1.3 quadrillion]",
   "tests.test_number::test_intword[test_args24--8.1 decillion]",
   "tests.test_number::test_intword[test_args7--1.0 million]"
  ],
  "n_failed": 5,
  "seconds": 0.5
 },
 "partial": {
  "instance_id": "python-humanize__humanize-41",
  "reward": 0,
  "failed": [
   "tests.test_number::test_intword[test_args12--1.0 billion]",
   "tests.test_number::test_intword[test_args17--6.0 trillion]",
   "tests.test_number::test_intword[test_args21--1.3 quadrillion]",
   "tests.test_number::test_intword[test_args24--8.1 decillion]",
   "tests.test_number::test_intword[test_args7--1.0 million]",
   "tests.test_number::test_intword[test_args2--100]"
  ],
  "n_failed": 6,
  "seconds": 0.4
 },
 "tamper": {
  "instance_id": "python-humanize__humanize-41",
  "reward": 0,
  "reason": "patch edits test files: ['tests/conftest.py']"
 }
}
```

## Summary

| Environment | Gold check (5 runs) | gold | wrong | partial | tamper |
|---|---|---|---|---|---|
| `python-humanize__humanize-41` | fails before 5/5, passes after 5/5, ok | 1 | 0 | 0 | 0 |

The environment is deterministic over 5 runs and the verifier separates the real fix from all three wrong patches. No problems found; no change to the environments is needed.
