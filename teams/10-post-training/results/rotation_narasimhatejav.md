# Week-3 rotation (Team 10): SWE environment end to end in Docker

Rotation member narasimhatejav (Narasimha Teja). One environment. R1 is the run in Docker and R2 is the verifier result. Besides the gold patch and a no-fix patch, the environment gets four harder negative controls: a plausible partial fix, two test-path tampering attempts, and a report-forging patch that touches no test path. Patches and raw outputs are in `rotation_narasimhatejav_evidence/`.

## pallets__click-1990
Environment: `pallets__click-1990` (pallets/click, BSD-3-Clause, language python), upstream PR https://github.com/pallets/click/pull/1990 (issue https://github.com/pallets/click/issues/1978), base commit `422cb2064eed`.

The bug: a flag option with `required=True` (for example `--on/--off`) is never reported as missing, because click gives every flag an implicit `False` default. The gold fix skips that default when the option is required (one line in `src/click/core.py`).

- Lab commit: `fb7d5e6a2a6a72042b6baa527190d6e1b8ee67fa` (tip of `g10-week3-post-training`)
- Docker: 28.4.0 linux/arm64
- Test command: `python -m pytest -p no:cacheprovider -o addopts= -q tests/test_options.py`
- FAIL_TO_PASS: 1 test (`test_missing_required_flag`), PASS_TO_PASS: 108 tests
- Wall time: 82 s for the image build, 7 s for the 5-run gold check, about 1 s for each patch run

### Build note (network, not the environment)

On my network, plain-HTTP requests to `deb.debian.org` get `403 Forbidden` (HTTPS gets 200, checked from the host and from inside the base image), so the Dockerfile's `apt-get update` step failed. I built the image from a copy of the Dockerfile with one extra line before `apt-get update`, which moves apt to the HTTPS mirror:

```
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources
```

The base image digest, click commit, pinned `requirements.lock` and install steps are unchanged; that line is the only difference. The image is tagged `g10-swe/pallets__click-1990:v1`, so `verify.py` uses it as-is. The environment files on the branch are not changed. Anyone whose network allows HTTP to the Debian mirror can build with the committed Dockerfile.

### R1: end to end in Docker

Commands, from the repo root (`swe-envs/verify.py`, locked-down runs: `--network=none --memory=2g --cpus=2 --pids-limit=256 --cap-drop=ALL --security-opt=no-new-privileges`, non-root):

```
E=teams/10-post-training/swe-envs/pallets__click-1990
V=teams/10-post-training/swe-envs/verify.py
R=teams/10-post-training/results/rotation_narasimhatejav_evidence
python3 $V $E --check --runs 5
python3 $V $E --patch $E/gold.patch
python3 $V $E --patch $R/pallets__click-1990_wrong.patch
python3 $V $E --patch $R/pallets__click-1990_partial.patch
python3 $V $E --patch $R/pallets__click-1990_tamper.patch
python3 $V $E --patch $R/pallets__click-1990_rootconftest.patch
python3 $V $E --patch $R/pallets__click-1990_srchack.patch
```

Gold check. On every run the hidden test fails on the base commit and passes after the gold patch, and the report-integrity sentinel holds:

```json
{
 "instance_id": "pallets__click-1990",
 "repo": "pallets/click",
 "f2p": 1,
 "p2p": 108,
 "image_id": "sha256:d1119edee903",
 "runs": 5,
 "problems": [],
 "fails_before": "5/5",
 "passes_after": "5/5",
 "seconds": 0.9,
 "ok": true
}
```

### R2: verifier result

| Candidate patch | What it does | Expected reward | Reward | Failed tests / reason |
|---|---|---|---|---|
| gold.patch | upstream fix | 1 | 1 | none |
| wrong.patch | adds `NOTES.md`, no code change | 0 | 0 | `test_missing_required_flag` |
| partial.patch | removes the implicit `False` default for every flag, not only required ones | 0 | 0 | `test_winstyle_options` (PASS_TO_PASS) |
| tamper.patch | gold fix plus a force-pass hook appended to `tests/conftest.py` | 0 | 0 | rejected before tests run: `patch edits test files: ['tests/conftest.py']` |
| rootconftest.patch | the same force-pass hook in a new root-level `conftest.py`, no fix | 0 | 0 | rejected before tests run: `patch edits test files: ['conftest.py']` |
| srchack.patch | no fix; `src/click/__init__.py` patches pytest's `TestReport` so every failure is reported as passed | 0 | 0 | `report integrity: the sentinel test is reported as passed` |

Notes on the controls:

- **partial** fixes the target test (a required flag now has no default, so it is reported as missing). It also changes behaviour that already worked: an unset optional flag now gives `None` instead of `False`, which `test_winstyle_options` checks (`assert result.output == "False\n"`). The PASS_TO_PASS list catches it.
- **tamper** and **rootconftest** carry a hook that rewrites every failed test report to passed. The verifier treats any `conftest.py` as a test file, wherever it sits, so both are rejected before the tests run.
- **srchack** touches no test path, so the test-file rule cannot see it. With this patch and no fix, a plain `pytest` run inside the image prints `109 passed` and exits 0, so a grader that trusted pytest's output or the junit file would give it 1. In the verifier's run the sentinel test (always fails) is reported as passed, so the report is rejected and the reward is 0. This control exercises the report-integrity check, which the other patches never reach.

**Result: PASS.** The gold check exit code is 0. The verifier gives 1 only to the real fix, and 0 to the no-fix, partial, two test-tampering and report-forging patches.

Full verifier outputs (also in `rotation_narasimhatejav_evidence/pallets__click-1990_results.json`):

```json
{
 "gold": {"instance_id": "pallets__click-1990", "reward": 1, "failed": [], "n_failed": 0, "seconds": 0.6},
 "wrong": {"instance_id": "pallets__click-1990", "reward": 0, "failed": ["tests.test_options::test_missing_required_flag"], "n_failed": 1, "seconds": 0.6},
 "partial": {"instance_id": "pallets__click-1990", "reward": 0, "failed": ["tests.test_options::test_winstyle_options"], "n_failed": 1, "seconds": 0.6},
 "tamper": {"instance_id": "pallets__click-1990", "reward": 0, "reason": "patch edits test files: ['tests/conftest.py']"},
 "rootconftest": {"instance_id": "pallets__click-1990", "reward": 0, "reason": "patch edits test files: ['conftest.py']"},
 "srchack": {"instance_id": "pallets__click-1990", "reward": 0, "reason": "report integrity: the sentinel test is reported as passed"}
}
```

## Summary

| Environment | Gold check (5 runs) | gold | wrong | partial | tamper | rootconftest | srchack |
|---|---|---|---|---|---|---|---|
| `pallets__click-1990` | fails before 5/5, passes after 5/5, ok | 1 | 0 | 0 | 0 | 0 | 0 |

The environment is deterministic over 5 runs, and the verifier separates the real fix from all five wrong patches, including one that forges the test report without touching a test file. No problems found in the environment. The only issue was the plain-HTTP Debian mirror being blocked on my network at build time. It is not a defect in the environment, but other rotators on restricted networks may hit it too.
