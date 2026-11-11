#!/usr/bin/env bash
# Re-run every test of the OCR-2 join, admission and resume work (G10). Exits non-zero if any test fails,
# errors or is SKIPPED, or if no test ran. No network, CPU only.
#
#   G10_DECONTAM_TOOLS=<lab main>/teams/09-evaluation/decontam PYTHON=<python 3.11+> bash verify.sh
#
# The tools must be Team 9's decontam folder from lab main (the one that carries fingerprints v2):
# the folder on the G10 branch is older and cannot build the toy fingerprint set the tests use.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"
: "${G10_DECONTAM_TOOLS:?set G10_DECONTAM_TOOLS to the Team 9 decontam folder from lab main}"  # no apostrophe here: bash 3.2
export G10_DECONTAM_TOOLS PYTHONDONTWRITEBYTECODE=1

for need in decontam_check.py canary_scan.py fpset.py registry.py; do
  test -f "$G10_DECONTAM_TOOLS/$need" || { echo "verify: $G10_DECONTAM_TOOLS/$need not found" >&2; exit 2; }
done
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "verify: Python 3.11+ is needed")'
"$PY" -c 'import pyarrow, tokenizers, pytest'

LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

run() {  # label, then the test files
  local label="$1"; shift
  echo "== $label"
  "$PY" -m pytest "$@" -q -rs -p no:cacheprovider 2>&1 | tee "$LOG"
  if grep -Eq '(^|[ ,])[0-9]+ (skipped|xfailed|xpassed|deselected)' "$LOG"; then
    echo "verify: a test was skipped or deselected; that counts as a failure here" >&2
    exit 1
  fi
  grep -Eq '(^|[ ,])[0-9]+ passed' "$LOG" || { echo "verify: no test passed" >&2; exit 1; }
}

run "new: source index and join"      "$HERE/test_prepare_ocr2.py"
run "new: pack admission"             "$HERE/test_pack_admission.py"
run "new: shard runner and resume"    "$HERE/test_ocr2_resume.py"
run "reused tools still pass"         "$HERE/test_convert.py" "$HERE/test_decontam_run.py"
echo "verify: OK"
