# Week-3 rotation (Team 10): SWE environment end to end in Docker

Rotation member vpw (Vardhan Walavalkar, Team 05-architecture). Assigned environment:
`python-validators__validators-191`, due Thu 19 Nov. R1 is the run in Docker; R2 is the verifier result. Beyond
the gold patch and a no-fix patch (as in `rotation_asraj.md`), this also covers a plausible-but-overly-strict
partial fix and a reward-hacking attempt (real fix plus a test-file edit), as in `rotation_chapanduk.md`. Patches
and raw outputs are in `rotation_vpw_evidence/`.

## python-validators__validators-191

Environment: `python-validators__validators-191` (python-validators/validators, MIT, language python), upstream
PR https://github.com/python-validators/validators/pull/191, base commit `95e5f001c2a9`.

- Lab commit: `5aed520fd4a4707b64795ed2e722eba368477978` (`upstream/main`)
- Docker: 29.1.3 linux/amd64
- Test command: `python -m pytest -p no:cacheprovider -o addopts= -q tests/test_ipv4.py`
- FAIL_TO_PASS: 1 test, PASS_TO_PASS: 7 tests
- Wall time: about 1.4 s per patch run, after the image build

**Host note.** This box's own user is uid 1001; the image's non-root `runner` user is uid 1000.
`verify.py`'s `tempfile.TemporaryDirectory()` for `/patches` defaults to mode 0700, so the bind mount was not
readable inside the container (`git apply`: "Permission denied") until the host directory was chmod'd 0755 before
the mount. This is a local host workaround (not a change to `swe-envs/verify.py` or any committed file) -- a
one-line `os.chmod` wrapper run outside the repo. The gold check, patches and rewards below are otherwise exactly
`verify.py`'s own output.

### R1: end to end in Docker

Commands, from the repo root (`swe-envs/verify.py`, locked-down runs: `--network=none --memory=2g --cpus=2
--pids-limit=256 --cap-drop=ALL --security-opt=no-new-privileges`, non-root):

```
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/python-validators__validators-191 --check --runs 5
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/python-validators__validators-191 --patch teams/10-post-training/swe-envs/python-validators__validators-191/gold.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/python-validators__validators-191 --patch teams/10-post-training/results/rotation_vpw_evidence/python-validators__validators-191_wrong.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/python-validators__validators-191 --patch teams/10-post-training/results/rotation_vpw_evidence/python-validators__validators-191_partial.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/python-validators__validators-191 --patch teams/10-post-training/results/rotation_vpw_evidence/python-validators__validators-191_tamper.patch
```

Gold check (the hidden test fails on the base commit and passes after the gold patch, every run, with the
report-integrity sentinel):

```json
{
 "instance_id": "python-validators__validators-191",
 "repo": "python-validators/validators",
 "f2p": 1,
 "p2p": 7,
 "image_id": "sha256:0a3d7fef7971",
 "runs": 5,
 "problems": [],
 "fails_before": "5/5",
 "passes_after": "5/5",
 "seconds": 1.3,
 "ok": true
}
```

### R2: verifier result

The upstream issue: the `ipv4` validator only checked each dot-separated group was all-digit and in `0..255`, so
any number of leading zeros passed (`"0127.0.0.1"` validated as `True`). The gold fix adds a length cap
(`len(x) > 3` rejects) on top of the existing checks.

| Candidate patch | Expected reward | Reward | Failed tests / reason |
|---|---|---|---|
| `gold.patch` (upstream fix) | 1 | 1 | none |
| `wrong.patch` (adds `ROTATION_NOTE.md`, no fix) | 0 | 0 | 1 failed (the target FAIL_TO_PASS case) |
| `partial.patch` (caps length with `>= 3` instead of `> 3`: fixes the target case but is overly strict) | 0 | 0 | 2 failed |
| `tamper.patch` (gold fix plus a comment added to `tests/test_ipv4.py`) | 0 | 0 | rejected before tests run: patch edits test files: `['tests/test_ipv4.py']` |

`partial.patch` is the interesting case: it correctly rejects `"0127.0.0.1"` (so the target FAIL_TO_PASS test
passes), but its off-by-one (`>= 3` rather than `> 3`) also rejects every 3-digit group, breaking two
PASS_TO_PASS cases that must stay valid: `"123.5.77.88"` (group `"123"`) and `"127.0.0.1"` (group `"127"`). A
verifier that checked only the target test would reward this candidate; this one correctly gives it 0 because it
checks every PASS_TO_PASS case too. `tamper.patch` carries the real fix, so a verifier that only ran the tests
would give it 1; this one gives 0 because the patch touches a test path before any test runs.

**Result: PASS.** The gold check exit code is 0 (5/5 both sides); the verifier gives 1 only to the real fix, and 0
to the no-fix, overly-strict, and test-tampering patches, with the correct reason in each case.

Full verifier outputs:

```json
{
 "gold": {
  "instance_id": "python-validators__validators-191",
  "reward": 1,
  "failed": [],
  "n_failed": 0,
  "seconds": 1.4
 },
 "wrong": {
  "instance_id": "python-validators__validators-191",
  "reward": 0,
  "failed": [
   "tests.test_ipv4::test_returns_failed_validation_on_invalid_ipv4_address[0127.0.0.1]"
  ],
  "n_failed": 1,
  "seconds": 1.3
 },
 "partial": {
  "instance_id": "python-validators__validators-191",
  "reward": 0,
  "failed": [
   "tests.test_ipv4::test_returns_true_on_valid_ipv4_address[123.5.77.88]",
   "tests.test_ipv4::test_returns_true_on_valid_ipv4_address[127.0.0.1]"
  ],
  "n_failed": 2,
  "seconds": 1.3
 },
 "tamper": {
  "instance_id": "python-validators__validators-191",
  "reward": 0,
  "reason": "patch edits test files: ['tests/test_ipv4.py']"
 }
}
```
