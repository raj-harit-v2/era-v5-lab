#!/usr/bin/env bash
# The one TSAI job for dry run 2's DT vs LoRA vs Full FT comparison, started from where Team 5's run leaves its weights.
#
# Team 5's owner (Capstone Session General, 23 Nov): the checkpoint stays on the job machine, in the store
# /shared/ckpt under run id dryrun2-1234; a later job reads it by passing that store and run id. So this chain:
#   1. run folder: Team 5's out/dryrun2-1234 as it is when it still has checkpoint.pt; otherwise rebuild it from the
#      Team 7 store (capstone/run_folder_from_store.py: Team 7 export, strict keys, probe bits, model hash == summary.json)
#   2. probe file (capstone/make_probe_file.py, Team 5's loader and loss) that origin g5_delivery requires
#   3. router bias reach (capstone/router_bias_reach.py), a report for Team 9 and the lead; a failure here never stops the job
#   4. the lead's wrapper capstone/dryrun2_dt_compare.py, unchanged, with every argument after `--` passed through
# Steps 1 and 2 run on the GPU (--device cuda) so Team 7 compares the probe bits on the device class that saved them.
#
#   G5=<lab checkout> T5_OUT=<Team 5's out/dryrun2-1234> STORE=/shared/ckpt TOKENIZER=<tokenizer_p1536.json> \
#   TABLE=<raw_table_P32.npz> HELDOUT=<heldout jsonl of the run> HELDOUT_SOURCES=<its sources jsonl> WORK=<scratch dir> \
#   bash teams/10-post-training/capstone/dryrun2_job_chain.sh -- <dryrun2_dt_compare.py arguments without
#   --g5-root/--run-folder/--tokenizer/--byte-table/--probe-file/--origin>
set -euo pipefail
: "${G5:?}" "${T5_OUT:?}" "${TOKENIZER:?}" "${TABLE:?}" "${HELDOUT:?}" "${HELDOUT_SOURCES:?}" "${WORK:?}"
STORE="${STORE:-/shared/ckpt}"; DEVICE="${DEVICE:-cuda}"; PY="${PY:-python}"
[ "${1:-}" = "--" ] && shift
C="$G5/teams/10-post-training/capstone"
export PYTHONPATH="$G5/teams/07-infrastructure${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p "$WORK"
log() { echo "[dryrun2_job_chain $(date -u +%H:%M:%SZ)] $*"; }

if [ -f "$T5_OUT/checkpoint.pt" ]; then
  RF="$T5_OUT"; log "run folder: $RF (Team 5's own checkpoint.pt)"
else
  RF="$WORK/dr2_run"
  if [ -f "$RF/G10_FROM_STORE.json" ]; then
    log "run folder: $RF (rebuilt earlier, reused)"
  else
    log "rebuild from store $STORE (run id from $T5_OUT/manifest.json)"
    "$PY" "$C/run_folder_from_store.py" --g5-root "$G5" --run-folder "$T5_OUT" --store "$STORE" --tokenizer "$TOKENIZER" \
      --byte-table "$TABLE" --heldout-data "$HELDOUT" --heldout-sources "$HELDOUT_SOURCES" --device "$DEVICE" --out "$RF"
  fi
fi
PF="$WORK/probe.json"
[ -f "$PF" ] || "$PY" "$C/make_probe_file.py" --g5-root "$G5" --run "$RF" --tokenizer "$TOKENIZER" --byte-table "$TABLE" \
  --device "$DEVICE" --out "$PF"
"$PY" "$C/router_bias_reach.py" --g5-root "$G5" --run-folder "$RF" --tokenizer "$TOKENIZER" --byte-table "$TABLE" \
  --heldout "$HELDOUT" --windows 8 --device "$DEVICE" --out "$WORK/router_bias_reach.json" \
  || log "router_bias_reach failed (report only; the job continues)"
log "wrapper: dryrun2_dt_compare.py --run-folder $RF --probe-file $PF --origin g5_delivery $*"
set +e
"$PY" "$C/dryrun2_dt_compare.py" --g5-root "$G5" --run-folder "$RF" --tokenizer "$TOKENIZER" --byte-table "$TABLE" \
  --probe-file "$PF" --origin g5_delivery "$@"
RC=$?
set -e
OUT=""; prev=""; for x in "$@"; do [ "$prev" = "--out" ] && OUT="$x"; prev="$x"; done
# 5. every arm's own report: the router bias stayed as delivered, and im_end at turn ends and mid-reply (job ADP)
"$PY" - "$OUT" "$WORK/arm_checks.json" <<'PYEOF' || RC=${RC/#0/5}
import json, sys
from pathlib import Path
out, dest = Path(sys.argv[1]), Path(sys.argv[2])
arms, bad = {}, []
for rep in sorted(out.glob("sft_*/sft_report.json")):
    r = json.loads(rep.read_text())
    rb, im = r.get("router_bias_unchanged") or {}, r.get("im_end_at_targets") or {}
    arms[rep.parent.name] = {"router_bias_unchanged": rb.get("pass"), "im_end_at_targets": im}
    if rb.get("pass") is not True:
        bad.append(rep.parent.name)
dest.write_text(json.dumps({"arms": arms, "router_bias_failed": bad}, indent=1))
print(json.dumps({"arm_checks": {a: {"router_bias_unchanged": v["router_bias_unchanged"],
                  "im_end_end_mid": [(v["im_end_at_targets"].get(k) or {}).get(f) for k in ("before", "after")
                                     for f in ("mean_logprob", "mid_logprob")]} for a, v in arms.items()}}))
sys.exit(1 if bad or not arms else 0)
PYEOF
log "done: wrapper exit $RC, arm checks in $WORK/arm_checks.json"
exit $RC
