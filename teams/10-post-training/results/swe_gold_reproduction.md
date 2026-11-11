# Existing SWE gold-set reproduction

Independent reproduction on 5 Nov 2026 (IST) using the existing
human-sourced environment `python-validators__validators-191`.

No new issue, buggy repository, test patch or gold patch is introduced by
this change. The environment provenance remains the upstream human-filed
issue and merged pull request recorded in its `env.json`. This note is
verification documentation only; it is not task or training content.

## Harness tests

Command:

```sh
python -m pytest teams/10-post-training/swe-envs/test_verify.py -q
```

Result:

```text
58 passed in 0.08s
```

## Docker gold check

The image was rebuilt from scratch immediately before the check. BuildKit's
output confirmed that the application and dependency layers ran again; the
only cached layer was the pinned base-image download.

Build command:

```sh
docker build --no-cache --pull \
  -t g10-swe/python-validators__validators-191:v1 \
  teams/10-post-training/swe-envs/python-validators__validators-191
```

Gold-check command:

```sh
python3 teams/10-post-training/swe-envs/verify.py \
  teams/10-post-training/swe-envs/python-validators__validators-191 \
  --check --runs 1
```

Environment:

- Docker Engine 29.9.2
- Architecture: `aarch64`
- Runtime network disabled by the verifier

Result:

| Field | Value |
|---|---|
| Instance | `python-validators__validators-191` |
| Repository | `python-validators/validators` |
| Fresh build | `--no-cache --pull` |
| Image | `sha256:7ca9a8c1181a` |
| FAIL_TO_PASS | 1 |
| PASS_TO_PASS | 7 |
| Fails before gold patch | 1/1 |
| Passes after gold patch | 1/1 |
| Problems | none |
| Result | **PASS** |

The check reproduced the required behaviour: the regression test failed on
the fixed historical base commit and all selected tests passed after applying
the existing upstream gold patch.
