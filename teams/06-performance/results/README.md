# Results

| File | What | GPU | Commit |
|---|---|---|---|
| `baseline_v0.md` | Gate 1 baseline: two runs within 5%, normal and MTP pairs | A100-SXM4-40GB | `f1ed7f2` |
| `slowest5_v0.md` | The five slowest parts of the step, each with a trace and a week-2 idea | A100-SXM4-40GB | `f1ed7f2` |
| `repeat_check_v1.md` | The 5% repeat check on hosts other than Colab (week 2) | several, named per section | named per section |
| `speed_v1.md` | Gate 2 evidence: baseline, CE A/B, MoE dispatch | named per row | named per row |
| `gate2_proposal.md` | Gate 2 Week-2 handout: Sat-14 ask + evidence pointers | n/a (points at pack rows) | tip `g6/dev` after #68 |
| `headloss_fwd_t4.md` | Part 6 (`fwd:head+loss`) profile, torch vs chunked CE | Tesla T4 | `7bc8bee` |
| `profile_dryrun1.md` | Week-3 Gate 3: full-width dry run 1 profiler + Nsight | _awaiting TSAI_ | stub on `g6/dev` |
| `speed_dryrun1.md` | Week-3: MoE dispatch / a2a / ckpt + per-rank / slow ranks | _awaiting TSAI_ | stub on `g6/dev` |
| `kernels_dryrun2.md` | Week-3: proposed dry-run-2 kernels, each with a test | n/a until pairs PASS | stub on `g6/dev` |

The v0 pairs are `baseline_v0` + `baseline_v0-run2` and `mtp_v0` + `mtp_v0-run2` (`model.mtp=true`). Their run JSONs,
JSONL sidecars, part traces and logs are in the gist https://gist.github.com/vaibh27/574990425455e4a9cb64822f14e3d85b.

## `runs/`

Where bench writes each run: `<tag>.json` + `<tag>.md`, the live `<tag>.jsonl` sidecar (`gpu_sample` and
`step_timing` events, for G8; `docs/METRICS.md`) and `<tag>_parts/`, one small Chrome trace per slowest part (open it
in https://ui.perfetto.dev or `chrome://tracing`).

Do not commit `runs/` by default; share run files as a gist. The exception is the run files a result page links to
(today the `t4_headloss*` files for `headloss_fwd_t4.md`). Each must be plain JSON or Markdown under 5 MB (pr-guard
refuses `.gz` files and files over 5 MB).

Full profiler traces go to `~/.cache/era-perf/traces/`, outside the repo. Never write them under `results/`.

Every result names its GPU and commit. A number without both does not count.
