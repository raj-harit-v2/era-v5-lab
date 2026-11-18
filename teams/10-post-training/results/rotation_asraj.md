# Week-3 rotation (Team 10): SWE environments end to end in Docker

Rotation member from Team 5. One section per environment, each with R1 (the run in Docker) and R2 (the verifier result).

## pallets__click-1934
Environment: `pallets__click-1934` (pallets/click, BSD-3-Clause), upstream PR https://github.com/pallets/click/pull/1934, base commit `da2b658e6185`.

- Lab commit: `6728a7a02f13fd7e0d2d230241407d9059ffff36`
- Docker: 29.2.0 linux/arm64
- Test command: `python -m pytest -p no:cacheprovider -o addopts= -q tests/test_options.py`
- FAIL_TO_PASS: 3 tests, PASS_TO_PASS: 88 tests
- Wall time for all three steps: 32 s

### R1: end to end in Docker

Commands, from the repo root (`swe-envs/verify.py`, locked-down runs: `--network=none --memory=2g --cpus=2 --pids-limit=256 --cap-drop=ALL --security-opt=no-new-privileges`, non-root):

```
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/pallets__click-1934 --check --runs 5
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/pallets__click-1934 --patch teams/10-post-training/swe-envs/pallets__click-1934/gold.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/pallets__click-1934 --patch wrong.patch
```

Gold check (the hidden tests fail on the base commit and pass after the gold patch, every run, with the report-integrity sentinel):

```json
{
 "instance_id": "pallets__click-1934",
 "repo": "pallets/click",
 "f2p": 3,
 "p2p": 88,
 "image_id": "sha256:d935cff8782a",
 "runs": 5,
 "problems": [],
 "fails_before": "5/5",
 "passes_after": "5/5",
 "seconds": 0.8,
 "ok": true
}
```

### R2: verifier result

| Candidate patch | Expected reward | Reward |
|---|---|---|
| gold.patch (upstream fix) | 1 | 1 |
| wrong.patch (adds a note file, no fix) | 0 | 0 |

**Result: PASS.** The gold check exit code is 0; the verifier gives 1 to the real fix and 0 to a patch that does not fix the issue.

Full verifier outputs:

```json
{
 "gold": {
  "instance_id": "pallets__click-1934",
  "reward": 1,
  "failed": [],
  "n_failed": 0,
  "seconds": 0.6
 },
 "wrong": {
  "instance_id": "pallets__click-1934",
  "reward": 0,
  "failed": [
   "tests.test_options::test_is_bool_flag_is_correctly_set[bool non-flag [False]]",
   "tests.test_options::test_is_bool_flag_is_correctly_set[bool non-flag [None]]",
   "tests.test_options::test_is_bool_flag_is_correctly_set[bool non-flag [True]]"
  ],
  "n_failed": 3,
  "seconds": 0.6
 }
}
```

## masterminds__semver-134

Environment: `masterminds__semver-134` (Masterminds/semver, MIT, language go), upstream PR https://github.com/Masterminds/semver/pull/134, base commit `fe7c21038085`.

- Lab commit: `5b22eb2db480e6dd1262bb07aa7bf4946a8e5266`
- Docker: 29.2.0 linux/arm64
- Test command: `go test -json -count=1 ./`
- FAIL_TO_PASS: 1 tests, PASS_TO_PASS: 25 tests
- Wall time for all three steps: 72 s

### R1: end to end in Docker

Commands, from the repo root (`swe-envs/verify.py`, locked-down runs: `--network=none --memory=2g --cpus=2 --pids-limit=256 --cap-drop=ALL --security-opt=no-new-privileges`, non-root):

```
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/masterminds__semver-134 --check --runs 5
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/masterminds__semver-134 --patch teams/10-post-training/swe-envs/masterminds__semver-134/gold.patch
python3 teams/10-post-training/swe-envs/verify.py teams/10-post-training/swe-envs/masterminds__semver-134 --patch wrong.patch
```

Gold check (the hidden tests fail on the base commit and pass after the gold patch, every run, with the report-integrity sentinel):

```json
{
 "instance_id": "masterminds__semver-134",
 "repo": "Masterminds/semver",
 "f2p": 1,
 "p2p": 25,
 "image_id": "sha256:0198d4df7d6d",
 "runs": 5,
 "problems": [],
 "fails_before": "5/5",
 "passes_after": "5/5",
 "seconds": 6.4,
 "ok": true
}
```

### R2: verifier result

| Candidate patch | Expected reward | Reward |
|---|---|---|
| gold.patch (upstream fix) | 1 | 1 |
| wrong.patch (adds a note file, no fix) | 0 | 0 |

**Result: PASS.** The gold check exit code is 0; the verifier gives 1 to the real fix and 0 to a patch that does not fix the issue.

Full verifier outputs:

```json
{
 "gold": {
  "instance_id": "masterminds__semver-134",
  "reward": 1,
  "failed": [],
  "n_failed": 0,
  "seconds": 6.3
 },
 "wrong": {
  "instance_id": "masterminds__semver-134",
  "reward": 0,
  "failed": [
   "github.com/Masterminds/semver/v3::TestConstraintCheck"
  ],
  "n_failed": 1,
  "seconds": 6.2
 }
}
```
