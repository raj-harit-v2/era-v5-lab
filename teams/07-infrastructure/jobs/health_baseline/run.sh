#!/usr/bin/env bash
# run.sh - the one start command of the health baseline job (ADR 0003 "baseline method").
#
#   bash teams/07-infrastructure/jobs/health_baseline/run.sh [--runs N] [--gpus N] [--out DIR]
#
# In simple words: on a node that we believe is healthy, run the full health check five times, run the Xid scan
# and the collective (all-reduce, reduce-scatter, all-gather, all-to-all) test once on their own, ask Team 08's
# validator whether every report follows v5-health/1, and write down what we measured. No network, no keys.
# It reads the node and writes only to ./out/ (job rules, JOB_REQUEST.md).
#
#   --runs N    how many full health runs (default 5, as in ADR 0003)
#   --gpus N    how many GPUs the node must show (default: what nvidia-smi lists; 0 if none). With 0 it is a CPU
#               smoke test (gloo, proves the pipeline only); with 1 there are no collectives; with 2+ NCCL.
#   --out DIR   output folder (default ./out)
# Environment: PYTHON (default python3), V5_EXPECT_GPUS (same as --gpus), V5_COLL_MAX_MB (largest message, MB;
#              default 1024 on GPUs, 16 on CPU).
#
# Exit code: 0 when every expectation in expected_results.json is met and Team 08's validator passed, else 1.
# Needs: python3 with pyyaml; torch for 0 or 2+ GPUs (a CUDA build for 2+).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEAM_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"                       # teams/07-infrastructure
HEALTH="$TEAM_DIR/health"
VALIDATOR="$TEAM_DIR/../08-monitoring/health-check/health_check.py"   # Team 08's v5-health/1 validator
PYTHON="${PYTHON:-python3}"
export PYTHON
export PYTHONDONTWRITEBYTECODE=1        # job rule: write only to ./out/

RUNS=5
OUT="out"
GPUS="${V5_EXPECT_GPUS:-}"

while [ $# -gt 0 ]; do
    case "$1" in
        --runs) RUNS="${2:?--runs needs a value}"; shift 2 ;;
        --gpus) GPUS="${2:?--gpus needs a value}"; shift 2 ;;
        --out)  OUT="${2:?--out needs a value}"; shift 2 ;;
        -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^#\( \|$\)//'; exit 0 ;;
        *) echo "run.sh: unknown argument: $1" >&2; exit 64 ;;
    esac
done
case "$RUNS" in ''|*[!0-9]*|0) echo "run.sh: --runs must be a positive number" >&2; exit 64 ;; esac

if [ -z "$GPUS" ]; then
    if command -v nvidia-smi >/dev/null 2>&1; then
        GPUS="$(nvidia-smi -L 2>/dev/null | grep -c '^GPU' || true)"
    else
        GPUS=0
    fi
    GPUS="${GPUS:-0}"
    GPU_SOURCE="detected with nvidia-smi -L"
else
    GPU_SOURCE="given"
fi
case "$GPUS" in ''|*[!0-9]*) echo "run.sh: GPU count must be a number, got '$GPUS'" >&2; exit 64 ;; esac

# 0 GPUs: CPU smoke test.  1 GPU: no collective is possible.  2+ GPUs: the real baseline.
if [ "$GPUS" -eq 1 ]; then MODE=prolog; else MODE=full; fi
if [ "$GPUS" -eq 0 ]; then COLL_RANKS=2; COLL_MB="${V5_COLL_MAX_MB:-16}"; else COLL_RANKS="$GPUS"; COLL_MB="${V5_COLL_MAX_MB:-1024}"; fi

mkdir -p "$OUT" || exit 1
OUT="$(cd "$OUT" && pwd)"
LOG="$OUT/run.log"
rm -f "$OUT"/health_run*.json "$OUT"/xid_scan.json "$OUT"/allreduce.json "$OUT"/node_health.jsonl \
      "$OUT"/baseline_summary.json "$OUT"/results_check.txt "$OUT"/validation.txt "$OUT"/clickhouse_rows.jsonl \
      "$OUT"/exit_codes.txt "$LOG"
rm -rf "$OUT/state" "$OUT/events"
mkdir -p "$OUT/state" "$OUT/events"

# health_check.py writes its state and events to /var/... by default: move both under ./out/
export V5_EXPECT_GPUS="$GPUS"
export V5_HEALTH_STATE="$OUT/state"
export V5_EVENTS_DIR="$OUT/events"

# CPU profile (--gpus 0): hide any real GPUs so torch.cuda.is_available() is False in the children.
# Otherwise allreduce_test.py picks CUDA whenever a GPU exists and starts 2 ranks on 1 GPU, and rank 1
# dies with "CUDA error: invalid device ordinal". Empty = no device visible, so the collectives use gloo.
[ "$GPUS" -eq 0 ] && export CUDA_VISIBLE_DEVICES=

say() { echo "[health_baseline] $*" | tee -a "$LOG"; }
with_timeout() { local s="$1"; shift; if command -v timeout >/dev/null 2>&1; then timeout "$s" "$@"; else "$@"; fi; }

say "start $(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) gpus=$GPUS ($GPU_SOURCE) mode=$MODE runs=$RUNS out=$OUT"

# ---- preflight: fail early with the reason, not halfway through
if ! "$PYTHON" -c "import yaml" 2>>"$LOG"; then
    say "ERROR: $PYTHON cannot import yaml. Install it: $PYTHON -m pip install pyyaml"; exit 1
fi
if [ "$GPUS" -ne 1 ]; then
    if ! "$PYTHON" -c "
import sys, torch
n = torch.cuda.device_count()
want = $GPUS
if want and (not torch.cuda.is_available() or n < want):
    sys.exit(f'torch sees {n} CUDA device(s), the node must show {want}. Install a CUDA build of torch that matches the driver.')
" 2>>"$LOG"; then
        say "ERROR: torch is missing or does not see $GPUS GPU(s) (details in $LOG)"; tail -n 3 "$LOG" >&2; exit 1
    fi
fi
if [ ! -f "$VALIDATOR" ]; then
    say "ERROR: Team 08's validator not found at $VALIDATOR (copy teams/08-monitoring/health-check/ next to teams/07-infrastructure/)"; exit 1
fi

# ---- what machine was this (for reading the numbers later)
{
    echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "host: $(hostname)"; echo "kernel: $(uname -sr)"
    echo "python: $("$PYTHON" -c 'import sys; print(sys.version.split()[0])')"
    "$PYTHON" -c "import torch; print('torch:', torch.__version__); print('cuda_devices:', torch.cuda.device_count()); print('nccl:', torch.cuda.nccl.version() if torch.cuda.is_available() else 'n/a')" 2>/dev/null
    echo "dcgmi: $(command -v dcgmi || echo 'not installed')"
    if command -v nvidia-smi >/dev/null 2>&1; then
        echo "--- nvidia-smi -L"; nvidia-smi -L 2>&1
        echo "--- driver / link"; nvidia-smi --query-gpu=index,driver_version,pcie.link.gen.max,pcie.link.width.max --format=csv 2>&1
        echo "--- topology (NV# = NVLink, PHB/PIX/SYS = PCIe)"; nvidia-smi topo -m 2>&1
    fi
} > "$OUT/env.txt" 2>&1

# ---- 1. the full health check, N times (state is fresh, so run 1 sees every Xid of this boot, later runs only new ones)
: > "$OUT/exit_codes.txt"
for i in $(seq 1 "$RUNS"); do
    say "health run $i/$RUNS (mode $MODE)"
    with_timeout 1800 "$HEALTH/gpu_health.sh" --mode "$MODE" --out "$OUT/health_run$i.json" >/dev/null 2>>"$LOG"
    rc=$?
    echo "health_run$i exit=$rc" >> "$OUT/exit_codes.txt"
    [ -f "$OUT/health_run$i.json" ] || say "WARNING: run $i wrote no report (exit $rc)"
done

# ---- 2. Xid scan on its own (its own state file, so it also sees every Xid of this boot)
say "xid_scan.py"
"$PYTHON" -I -B "$HEALTH/xid_scan.py" --state "$OUT/state/xid_standalone.json" > "$OUT/xid_scan.json" 2>>"$LOG"
echo "xid_scan exit=$?" >> "$OUT/exit_codes.txt"

# ---- 3. collectives on their own (needs 2 ranks; with 1 GPU there is nothing to test)
if [ "$GPUS" -ne 1 ]; then
    say "allreduce_test.py: $COLL_RANKS ranks, largest message ${COLL_MB} MB"
    with_timeout 900 "$PYTHON" -B -m torch.distributed.run --standalone --nproc_per_node="$COLL_RANKS" \
        "$HEALTH/allreduce_test.py" --max-mb "$COLL_MB" --out "$OUT/allreduce.json" >/dev/null 2>>"$LOG"
    echo "allreduce_test exit=$?" >> "$OUT/exit_codes.txt"
else
    say "allreduce_test.py skipped: 1 GPU cannot run a collective"
fi

# ---- 4. join the reports, check the expectations, compute the baseline numbers
say "summarize_baseline.py"
"$PYTHON" -B "$SCRIPT_DIR/summarize_baseline.py" --out "$OUT" 2>>"$LOG"
RC_SUM=$?

# ---- 5. Team 08's validator: does every report follow v5-health/1, and does it map to one ClickHouse row?
RC_VAL=1
if [ -f "$OUT/node_health.jsonl" ]; then
    say "Team 08 validator"
    "$PYTHON" -I -B "$VALIDATOR" --validate "$OUT/node_health.jsonl" > "$OUT/validation.txt" 2>&1
    RC_VAL=$?
    "$PYTHON" -I -B "$VALIDATOR" --validate "$OUT/xid_scan.json" >> "$OUT/validation.txt" 2>&1 || RC_VAL=1
    "$PYTHON" -I -B "$VALIDATOR" --clickhouse-jsonl "$OUT/node_health.jsonl" > "$OUT/clickhouse_rows.jsonl" 2>>"$LOG" || RC_VAL=1
    cat "$OUT/validation.txt"
fi

if [ "$RC_SUM" -eq 0 ] && [ "$RC_VAL" -eq 0 ]; then
    say "DONE: all expectations met, validator PASS. Results in $OUT"
    exit 0
fi
say "DONE: NOT OK (summary exit $RC_SUM, validator exit $RC_VAL). Read $OUT/results_check.txt and $OUT/validation.txt"
exit 1
