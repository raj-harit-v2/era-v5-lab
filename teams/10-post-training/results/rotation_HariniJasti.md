# Week-3 rotation (Team 10): SWE environment end to end in Docker

Rotation member HariniJasti (Harini Jasti). One environment. R1 is the run in Docker and R2 is the verifier result. Besides the gold patch, the verifier gets a plausible partial fix that handles only half of the issue. Patch and raw outputs are in `rotation_HariniJasti_evidence/`.

## mahmoud__boltons-302

Environment: `mahmoud__boltons-302` (mahmoud/boltons, BSD-3-Clause), upstream PR https://github.com/mahmoud/boltons/pull/302 (issue https://github.com/mahmoud/boltons/issues/297), base commit `9420cfeb3b1e`.

Issue: `daterange(start, stop, inclusive=True)` returns an infinite iterator when `start == stop`; expected to get `start` exactly once. The gold patch changes `elif start < stop:` to `elif start <= stop:` in `boltons/timeutils.py`.

- Lab commit: `b6fcd5603a0680cdc55ea35bfdd3531e0c9d6488`
- Docker: 29.9.3 linux/amd64 (Docker Desktop 4.99.0 on Windows, WSL 2 backend)
- Test command: `python -m pytest -p no:cacheprovider -o addopts= -q tests/test_timeutils.py`
- FAIL_TO_PASS: 1 test, PASS_TO_PASS: 4 tests
- Wall time for all three steps: about 5 s (image already built)

### R1: end to end in Docker

Commands, from the repo root (`swe-envs/verify.py`, locked-down runs: `--network=none --memory=2g --cpus=2 --pids-limit=256 --cap-drop=ALL --security-opt=no-new-privileges`, non-root):

```
python teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/mahmoud__boltons-302 --check --runs 5
python teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/mahmoud__boltons-302 --patch teams/10-post-training/swe-envs/mahmoud__boltons-302/gold.patch
python teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/mahmoud__boltons-302 --patch teams/10-post-training/results/rotation_HariniJasti_evidence/mahmoud__boltons-302_partial.patch
```

Gold check (the hidden test fails on the base commit and passes after the gold patch, every run, with the report-integrity sentinel):

```json
{
 "instance_id": "mahmoud__boltons-302",
 "repo": "mahmoud/boltons",
 "f2p": 1,
 "p2p": 4,
 "image_id": "sha256:aa4972a4b64d",
 "runs": 5,
 "problems": [],
 "fails_before": "5/5",
 "passes_after": "5/5",
 "seconds": 2.0,
 "ok": true
}
```

### R2: verifier result

| Candidate patch | Expected reward | Reward |
|---|---|---|
| gold.patch (upstream fix) | 1 | 1 |
| partial.patch (returns early when `start == stop`: right for `inclusive=False`, yields nothing for `inclusive=True`) | 0 | 0 |

**Result: PASS.** The gold check exit code is 0; the verifier gives 1 to the real fix and 0 to a plausible partial fix. The partial patch applies cleanly and the 4 PASS_TO_PASS tests still pass, so the 0 comes only from the hidden FAIL_TO_PASS test catching the missed `inclusive=True` case.

Full verifier outputs:

```json
{
 "gold": {
  "instance_id": "mahmoud__boltons-302",
  "reward": 1,
  "failed": [],
  "n_failed": 0,
  "seconds": 1.3
 },
 "partial": {
  "instance_id": "mahmoud__boltons-302",
  "reward": 0,
  "failed": [
   "tests.test_timeutils::test_daterange_with_same_start_stop"
  ],
  "n_failed": 1,
  "seconds": 2.1
 }
}
```

### Notes from running on Windows

- With `core.autocrlf=true`, the checkout gives the env files (`gold.patch`, `test.patch`, `Dockerfile`, ...) CRLF line endings, which can stop the patches from applying in the Linux container. I converted `swe-envs/mahmoud__boltons-302/` back to LF before running (local only, not committed). A `.gitattributes` rule such as `teams/10-post-training/swe-envs/** text eol=lf` would avoid this for other Windows users.
- On the first run (image build), `verify.py` printed a `UnicodeDecodeError` from a subprocess reader thread: Windows Python decoded the `docker build` log as cp1252. The build and the check still succeeded. Setting `PYTHONUTF8=1` removes the warning; the outputs above are from a rerun with it set.
