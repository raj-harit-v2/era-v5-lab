# SWE environments (G10 week 2, tasks D/E/F)

Each folder `swe-envs/<instance_id>/` is one SWE environment built from **one merged upstream GitHub PR**:
a fixed commit, a failing test and a gold patch, in Docker. `results/swe_gold_check.md` shows that each one
passes the gold check: the test fails before the patch and passes after it.

## What is in an environment

| File | What | Where it comes from |
|---|---|---|
| `env.json` | `instance_id`, `repo`, `base_commit`, `FAIL_TO_PASS`, `PASS_TO_PASS` (same names as SWE-bench), plus `licence`, `pr_url`, `issue_urls`, `merged_at`, `provenance`, `base_image`, `image`, `test_files`, `test_cmd`, `timeout_s`, `quality_verdict` | `make_env.py`; `quality_verdict` from `results/swe_env_review.md` |
| `issue.md` | the problem statement | the linked GitHub issue, text unchanged, with its URL |
| `gold.patch` | the fix | the non-test files of the upstream PR |
| `test.patch` | the hidden tests | the test files of the upstream PR |
| `Dockerfile` | repo at `base_commit`, **no git history**, base image pinned by digest, runs as a non-root user | `make_env.py` |
| `requirements.lock` | exact dependency versions, resolved as of the PR merge date | `make_env.py` (`uv pip install --exclude-newer <merge date>`) |

## Rules every environment follows

- **Human content only (TSAI 3 Nov rule).** The issue, fix and tests are all upstream, written by people. We use PRs merged **before 2023** that close a human-filed issue. `make_env.py` refuses a PR whose body, commits or issue mention an AI coding tool. No model writes any environment content; the scripts here only cut the PR apart, pin the environment and measure the tests.
- **Permissive repos only** (MIT, BSD, Apache-2.0 ...), recorded in `env.json.licence`.
- **Not a benchmark repo.** No repo from SWE-bench (incl. Lite and Verified), SWE-bench Multimodal, SWE-bench Live or SWE-bench Pro (`benchmark_repos.txt`).
- **No leaks.** The image has the repo at the base commit only, with a fresh one-commit git history, so the fix cannot be read from `.git`.
- **Locked-down runs.** Every test run uses `--network=none --memory=2g --cpus=2 --pids-limit=256 --cap-drop=ALL --security-opt=no-new-privileges`, as a non-root user, under a timeout.
- **Hidden tests win.** `verify.py` refuses a candidate patch that touches a test file (`tests/`, `test_*.py`, `conftest.py`, `tox.ini` ...), including paths git writes in quoted form (non-ASCII names), and any patch that adds a symlink, a submodule or a binary file. It then restores the test files and applies `test.patch` after the candidate.
- **Report integrity.** After the hidden tests, `verify.py` adds a sentinel test that always fails. For Python it is made to look like one more hidden test: its name is the first FAIL_TO_PASS test's name plus two words, its body is a small assertion with random ints, and it is appended to the file of that test, which the test command already runs (job W, 18 Nov 2026: the earlier `test_<12 hex>` sentinel in its own untracked file was found and spared by a patch that rewrote pytest's reports). A run counts only if the sentinel is reported as failed, the test command exits with code 1, and (pytest) the junit report shows no more passed tests than pytest's own summary line. A test reported both passed and failed counts as failed. The hidden `test.patch` and the script reach the container on stdin / inside the script, not as a mount or a `bash -c` argument, so the candidate cannot read the clean upstream patch from disk or the sentinel from `/proc/1/cmdline`; the test command reads `/dev/null`. A patch that adds a top-level path that would shadow the runner (`pytest.py`, `_pytest/`, `pluggy/`, `py.py`, `sitecustomize.py`, `usercustomize.py`, a `*.pth`, or a module named like a standard-library module) scores 0 before any run. This file is shared with `rl/agentic` and the `swe/<id>` envs.

## Commands

```bash
# reward for a candidate patch (RL): prints {"reward": 0|1, ...}
python swe-envs/verify.py swe-envs/<instance_id> --patch candidate.patch

# gold check: one env, or all of them (writes the results table)
python swe-envs/verify.py swe-envs/<instance_id> --check --runs 5
python swe-envs/verify.py --check-all --runs 5 --write results/swe_gold_check.md
python swe-envs/verify.py --check-all --runs 5 --platform linux/amd64 --write results/swe_gold_check_amd64.md

# build a new env from an upstream PR (needs `gh` logged in, Docker, network)
python swe-envs/make_env.py --repo pallets/click --pr 1934

# list more candidates from an open pool (default nebius/SWE-rebench, read at a pinned Hub commit) with the same filters
python swe-envs/import_pool.py --out pool_manifest.json [--revision SHA] [--local-dir DIR]

# SWE-rebench pilot: admission checks and evidence (rebench-pilot/<id>/admission.json, results/swe_rebench_pilot.md)
python swe-envs/make_env.py --repo keis/base58 --pr 46 --out-dir swe-envs/rebench-pilot
python swe-envs/rebench_pilot.py --source-dir DIR --runs 5 --platforms native linux/amd64

# harness tests (offline, no Docker)
python -m pytest swe-envs/test_verify.py -q
```

## How FAIL_TO_PASS and PASS_TO_PASS are chosen

`make_env.py` runs the test files from `test.patch` twice on the base commit and twice after the gold patch:

- **FAIL_TO_PASS:** passes after every time, and fails (or does not exist) before every time.
- **PASS_TO_PASS:** passes on both sides every time.
- **Dropped and recorded in `build_notes`:** any test that changes between runs.

`verify.py --check` then runs both sides 5 times. Every run must agree, or the env fails.

## Dependencies

- Runtime and test dependencies are resolved as of the merge date and frozen in `requirements.lock`.
- Build tools (setuptools, wheel) may be newer, up to 2025-06-01, because setuptools before 64 cannot do editable installs.
- The Python version follows the merge year: 3.8 up to 2020, 3.9 in 2021, 3.10 in 2022.
- Base images are multi-arch (`python:3.x-slim`) and pinned by manifest digest, so the same Dockerfile builds on arm64 and amd64.

## Using these in an RL loop

- The shared fields use SWE-bench names, so SWE-bench-style loaders can read `env.json` with little glue. The env format for a specific RL framework (verifiers, OpenEnv, Harbor, slime) is a week 3-4 task, once the team picks the framework.
- `quality_verdict` is `keep` (16 envs) or `keep-flagged` (5 envs: the tests are stricter than the issue, so a correct fix that reads the issue differently can fail). Filter or down-weight on it. `quality_note` says why. The review is model-assisted metadata, not training data.

## Scaling with SWE-rebench (TSAI, 4 Nov)

TSAI allows pre-2023 rows from `nebius/SWE-rebench` (CC-BY-4.0) on two conditions: use only the human parts (issue, patch, tests), and rebuild and gold-check every env ourselves. The Qwen2.5-72B install recipes and quality labels are not used, because that model's licence is outside the generator rule. `import_pool.py` lists candidates; `make_env.py` rebuilds each one from the upstream PR; `verify.py --check` decides. The attribution is in `licences/licence_table.md`.

## SWE-rebench pilot (11 Nov): 5 environments in `rebench-pilot/`

The first five SWE-rebench environments, kept apart from the 21 above (`verify.py --check-all` does not read
`rebench-pilot/`). Results: `../results/swe_rebench_pilot.md`. Evidence per env: `rebench-pilot/<id>/admission.json`.

- **Pinned source.** `nebius/SWE-rebench` at Hub commit `89cdfbab4ab1bd8f5a658bb212d1b63624f4f881`, split `test`,
  both parquet files checked against the sha256 the Hub records (`rebench-pilot/source_manifest.json`).
  `import_pool.py` now refuses an unpinned revision, a file whose hash differs, and a row whose date is missing or
  unreadable. Its output is a discovery list only.
- **Dates.** SWE-rebench's `created_at` is the PR's date. `make_env.py` now also checks the linked issue's own
  creation date and the merge date from GitHub, and refuses a missing, unreadable or 2023+ date.
- **Human parts only.** Issue text, fix and tests come from GitHub (the upstream issue and PR), not from the
  release. The release's install recipes, `requirements`, `environment` and quality labels are not read. From the
  row we read only the id, repo, dates, licence name, base commit and test lists, to compare with the rebuild.
- **Protected sets.** Every repo named in G9's fingerprints v2 for SWE-bench Verified, Live and Pro (181 repos) is
  in `benchmark_repos.txt`; no pilot repo is. Issue, test and fix text of all five passed G9's
  `decontam_check.py` and `canary_scan.py` on the full v2 set (`set_sha256 2826a3b8…`): 15 documents, 0 flagged,
  0 canaries (`rebench-pilot/decontam_record.json`). The gold patch stays a private verifier reference; it is
  never put in a prompt.
- **Admission** (`rebench_pilot.py`): per platform, 5 runs with no patch (every FAIL_TO_PASS test reported and
  failing) and 5 with the gold patch (every listed test reported and passing), each in a fresh container with no
  network; no collection errors; verify.py's report-integrity checks; a comment-only negative control gets reward
  0 and the gold patch reward 1; an isolation probe (only `lo` up, no route, TCP and DNS fail, one commit,
  non-root); no container left behind.
- **Platforms.** This Mac's Docker runs a linux/arm64 VM: arm64 runs are native to that VM; linux/amd64 runs are
  emulated. A native linux/amd64 host has not run these yet.
- **Rejected candidates** and why: `source_manifest.json` (`rejected`) and the results file.

## Known limits

- **The candidate's code runs in the same process as the tests.** It can try to rewrite the report (for example from an `atexit` hook, or by wrapping pytest's `TestReport`, attack P1 of the independent attack test of 18 Nov 2026: reward 1 on the earlier sentinel, now 0, as are P1b, P1c; the fixtures are in `rl/agentic/attack_fixtures/`). No in-process check is sound for Python; the defence is that the sentinel looks like the hidden failing tests and that the channels that reveal it are closed (see above). The integrity checks catch a rewritten report that drops the sentinel, flips it, changes the exit code or disagrees with pytest's summary line. **Residual:** a patch that reads the test source at run time can still look for the sentinel's body shape (`expected = <int>` then `assert <int> == expected`). If RL ever finds that, the next step is K sentinels made as mutated copies of real hidden tests. For RL, log every patch that imports `atexit`, calls `os._exit` or opens files under `/tmp`; `reward()` returns a `flags` list for patches that mention `_pytest`, `TestReport`, `pluggy`, `sys.modules`, `gc.get_objects`, `inspect`, `/proc/`, `atexit` or `os._exit` (recorded, not refused): read a sample of high-reward flagged patches each run. The executor passed to `reward()` must run the script with `bash -s` on stdin; a pooled executor (none exists yet, see `rl/pool.py`) must use `docker exec -i ... bash -s`.
- **Go reports** come from `go test -json`, which reads the test binary's own output; a printed `--- PASS` line cannot hide a real `--- FAIL` (fail wins), and the sentinel and exit code checks apply as for Python.
- The root filesystem is not read-only, because the tests write into the repo; the container is thrown away after each run.
