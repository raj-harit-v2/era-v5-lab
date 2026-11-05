#!/usr/bin/env bash
# gpu_health.sh - the v5-health/1 node health producer named in Team 08's contract
# (teams/08-monitoring/health-check/README.md).
#
# In simple words: this is the script Slurm and Team 08 expect to call on a node. It does not
# re-implement the GPU checks in bash; it is a thin wrapper over health/health_check.py, which
# already emits a v5-health/1 JSON report. One JSON object is written to stdout (the contract:
# "one JSON object to stdout, one line when appended to a .jsonl node log"). Team 08's validator
# (teams/08-monitoring/health-check/health_check.py --validate -) accepts that stdout unchanged.
#
# Usage:
#   health/gpu_health.sh [--mode prolog|periodic|full] [--out FILE] [--report-only]
#                        [--kernel-log FILE] [--nvidia-smi-fixture FILE] [--nvlink-fixture FILE]
#
#   --mode          prolog  (default) before a job starts; DCGM diag level 1; GPUs idle
#                   periodic every 30 s while a node runs; DCGM health watches only
#                   full    before dry runs / after a repair; adds DCGM diag 2 + collective sweep
#   --out FILE      also write the JSON report to FILE (in addition to stdout)
#   --report-only   never drain the node or signal jobs (default here: a producer run is read-only)
#   --kernel-log / --nvidia-smi-fixture / --nvlink-fixture
#                   read these files instead of the live tools (reproducible samples and tests)
#
# Environment:
#   V5_EXPECT_GPUS  expected GPU count (default: expect_gpus in thresholds.yaml; 0 on CPU hosts)
#   PYTHON          python interpreter to use (default: python3)
#
# Exit codes follow health_check.py: 0 pass, 3 warn, 4 fail. In prolog mode a warn exits 0 so Slurm
# does not drain a node for a warning.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

mode="prolog"
report_only="--report-only"   # a producer run never drains a node as a side effect
passthrough=()
out=""

usage() {
    sed -n '2,31p' "${BASH_SOURCE[0]}" | sed 's/^#\( \|$\)//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        --mode)
            mode="${2:?--mode needs a value}"; shift 2 ;;
        --mode=*)
            mode="${1#*=}"; shift ;;
        --out)
            out="${2:?--out needs a value}"; shift 2 ;;
        --out=*)
            out="${1#*=}"; shift ;;
        --report-only)
            report_only="--report-only"; shift ;;
        --act)
            # opt back in to the drain/signal side effects of periodic mode
            report_only=""; shift ;;
        --kernel-log|--nvidia-smi-fixture|--nvlink-fixture)
            passthrough+=("$1" "${2:?$1 needs a value}"); shift 2 ;;
        --kernel-log=*|--nvidia-smi-fixture=*|--nvlink-fixture=*)
            passthrough+=("${1%%=*}" "${1#*=}"); shift ;;
        -h|--help)
            usage; exit 0 ;;
        *)
            echo "gpu_health.sh: unknown argument: $1" >&2
            usage >&2
            exit 64 ;;
    esac
done

case "$mode" in
    prolog|periodic|full) ;;
    *) echo "gpu_health.sh: --mode must be prolog, periodic or full (got '$mode')" >&2; exit 64 ;;
esac

cmd=("$PYTHON" -I -B "$SCRIPT_DIR/health_check.py" --mode "$mode")   # -B: no __pycache__ (job packages write only to ./out/)
[ -n "$report_only" ] && cmd+=("$report_only")
[ -n "$out" ] && cmd+=(--out "$out")
cmd+=("${passthrough[@]}")

# health_check.py writes the v5-health/1 JSON to stdout (and to --out when given) and returns the
# health exit code; pass both straight through.
exec "${cmd[@]}"
