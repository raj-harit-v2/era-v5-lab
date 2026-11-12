# Profile — dry run 1

**Status:** stub — awaiting TSAI full-width (or small-width) job logs.  
**Owners:** torch.profiler → Varshith · Nsight → Shashank · Lead review → Raj  
**Rule:** every number cites **GPU name + git SHA**. No invented ms. Traces → gist / `~/.cache/era-perf/traces/` (not under `results/`).

| Field | Value |
| :--- | :--- |
| GPU | _awaiting_ |
| Commit | _awaiting_ |
| Config | _G5 v1 or base — pin when known_ |
| Job PR / tag | `dryrun1_prof` |
| `mfu_method` | `g6-v1` until CAP flips |

## Method

1. Class JOB: `python -m perfkit.bench --config <cfg> --modes clean,layer,trace --level 3 --tag dryrun1_prof --out out` (add `--synthetic` if needed).  
2. Open part traces in [Perfetto](https://ui.perfetto.dev) / Chrome tracing; gist `runs/<tag>_parts/` if needed.  
3. **Nsight:** record findings from TSAI-returned artifacts (link gist; do not commit large binaries here).

## Top ops (torch.profiler)

| rank | op / part | self ms | note |
| ---: | :--- | ---: | :--- |
| 1 | _awaiting_ | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

## Slowest parts (layer + part traces)

| part | ms | gist / Perfetto |
| :--- | ---: | :--- |
| _awaiting_ | | |

## Nsight notes

_Awaiting TSAI node time. Summarize kernels / occupancy / mem that explain profiler hot list._

## Repeat / trust

If dual run: gated parts within **≤5%**. Warm then measure.
