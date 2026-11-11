#!/bin/bash
# Start the V5 production stack in order, checking each step before the next (ADRs 0001-0004).
#
# In simple words: a cluster has a strict start order. Logins (munge) first, then the accounting database,
# then the controllers, then the accounts, then the GPU nodes. Then we prove the nodes are healthy and the
# checkpoint store is safe BEFORE we spend GPU hours, and only then submit the main run. Each step waits until
# its check passes, and stops the whole launch on the first failure, saying which step and why. Every step is
# safe to run twice, so after a fix you continue with `--from <step>`.
#
#   launch.sh                    run every step
#   launch.sh --dry-run          print what would run, change nothing
#   launch.sh --from slurmd      start at a step (after fixing a failure)
#   launch.sh --only health      one step
#   launch.sh --list             the steps, in order
#
# Settings come from /etc/v5/cluster.env (or $V5_CLUSTER_ENV); see cluster.env.example next to this file.
# Commands reach each host through $V5_EXEC, "%h" is the host: `ssh -o BatchMode=yes %h` on cloud nodes (default),
# `docker exec slurm-docker-%h-1` against the Docker test cluster (support/simulation).
set -uo pipefail

STEPS=(preflight munge slurmdbd dbbackup slurmctld accounts slurmd health services store submit status)
why() {  # one line per step: what it proves (bash 3.2 has no associative arrays: macOS operator laptops)
  case "$1" in
    preflight) echo "settings complete, every host reachable, code and config pinned" ;;
    munge) echo "munged runs everywhere and every host accepts the controller's credential (same key)" ;;
    slurmdbd) echo "accounting database daemon up and answering" ;;
    dbbackup) echo "a backup of the accounting DB exists and restores (counts only after a test restore)" ;;
    slurmctld) echo "primary and backup controller up; scontrol ping shows both" ;;
    accounts) echo "accounts, QOS and limits loaded (setup_accounts.sh, safe twice)" ;;
    slurmd) echo "every GPU node registered and idle" ;;
    health) echo "full health check on every GPU node (GPUs, ECC, NVLink, Xid, NVMe, 4 collectives); a failing node is drained" ;;
    services) echo "hot-spare timer and alert watcher on the controller, spot watcher on every node" ;;
    store) echo "checkpoint store: write, read, and a stale write refused (fencing depends on it)" ;;
    submit) echo "main run submitted (unless already queued), RUNNING, claimed its epoch, restored and started" ;;
    status) echo "jobs and nodes in plain words" ;;
  esac
}

DRY=0; FROM=""; ONLY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --from) FROM="$2"; shift ;;
    --only) ONLY="$2"; shift ;;
    --list) for s in "${STEPS[@]}"; do printf '%-10s %s\n' "$s" "$(why "$s")"; done; exit 0 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

ENV_FILE="${V5_CLUSTER_ENV:-/etc/v5/cluster.env}"
# shellcheck disable=SC1090
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"
V5_EXEC="${V5_EXEC:-ssh -o BatchMode=yes -o ConnectTimeout=10 %h}"
V5_REPO="${V5_REPO:-/opt/v5}"
V5_PY="${V5_PY:-/opt/venv/bin/python}"
V5_SUBMIT_USER="${V5_SUBMIT_USER:-svc}"
V5_EVENTS_DIR="${V5_EVENTS_DIR:-/var/log/v5/events}"
V5_REMOTE_ROOT="${V5_REMOTE_ROOT:-}"         # required: preflight stops if it is empty
V5_DBD_HOST="${V5_DBD_HOST:-}"; V5_MIN_NODES="${V5_MIN_NODES:-}"
RUN_ID="${RUN_ID:-v5main}"
V5_MAIN_ARGS="${V5_MAIN_ARGS:-}"            # extra sbatch args (the Docker test: smaller nodes)
V5_MAIN_ENV="${V5_MAIN_ENV:-}"              # extra --export pairs, comma separated
V5_WAIT_S="${V5_WAIT_S:-300}"
V5_SKIP="${V5_SKIP:-}"                      # steps that do not apply (the Docker test has no systemd: services)
CTLD=(${V5_CTLD_HOSTS:-})
NODES=(${V5_NODES:-})
CTL="${CTLD[0]:-}"
SUB="$V5_REPO"                # the team folder: adr/ ckpt/ queue/ slurm/ health/ metrics/ common/ launch/
LOG="${V5_LAUNCH_LOG:-./launch-$(date -u +%Y%m%dT%H%M%SZ).log}"

say()  { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$LOG" >&2; }
fail() { say "FAIL [$STEP]: $*"; say "fix it, then: $0 --from $STEP"; exit 1; }

# on <host> <command>: run a command on a host through $V5_EXEC. Dry run: print it only.
on() {
  local h="$1"; shift
  local cmd="${V5_EXEC//%h/$h} bash -lc $(printf '%q' "$*")"
  if [[ $DRY == 1 ]]; then echo "  would run on $h: $*" >&2; return 0; fi
  eval "$cmd"
}

# wait_until <seconds> <what> <command...>: poll every 3 s until the command succeeds.
wait_until() {
  local t="$1" what="$2"; shift 2
  [[ $DRY == 1 ]] && { echo "  would wait up to ${t}s for: $what" >&2; return 0; }
  local end=$((SECONDS + t))
  until "$@" >/dev/null 2>&1; do
    (( SECONDS > end )) && fail "timed out after ${t}s waiting for: $what"
    sleep 3
  done
}

# daemon <host> <process> <systemd unit>: start it unless it already runs, then require that it runs.
daemon() {
  local h="$1" proc="$2" unit="$3"
  if [[ $DRY == 0 ]] && on "$h" "pgrep -x $proc" >/dev/null 2>&1; then
    say "  $h: $proc already running"; return 0
  fi
  on "$h" "systemctl start $unit" || fail "$h: systemctl start $unit failed"
  wait_until 60 "$proc on $h" on "$h" "pgrep -x $proc"
  say "  $h: $proc started"
}

ctl() { on "$CTL" "$*"; }

# ------------------------------------------------------------------------------------------------- steps

step_preflight() {
  local miss=()
  for v in V5_DBD_HOST V5_CTLD_HOSTS V5_NODES V5_REMOTE_ROOT V5_MIN_NODES; do [[ -n "${!v:-}" ]] || miss+=("$v"); done
  [[ ${#miss[@]} -eq 0 ]] || fail "missing in $ENV_FILE: ${miss[*]}"
  [[ ${#NODES[@]} -ge $V5_MIN_NODES ]] || fail "V5_NODES has ${#NODES[@]} hosts, V5_MIN_NODES is $V5_MIN_NODES"
  for h in "$V5_DBD_HOST" "${CTLD[@]}" "${NODES[@]}"; do
    on "$h" "test -x $V5_PY && test -f $SUB/slurm/mainrun.sbatch" >/dev/null 2>&1 || [[ $DRY == 1 ]] \
      || fail "$h: not reachable, or $V5_PY / $SUB missing"
  done
  # One code version everywhere: the git sha and the config sha go into every checkpoint manifest, and a
  # restore refuses a different one (ADR 0001 §1). Different code on two nodes would hold the run later.
  if [[ $DRY == 0 ]]; then
    local shas
    shas=$(for h in "${CTLD[@]}" "${NODES[@]}"; do on "$h" "sha256sum $SUB/ckpt/ckpt.py $SUB/slurm/mainrun.sbatch | sha256sum | cut -c1-16"; done | sort -u)
    [[ $(wc -l <<<"$shas") -eq 1 ]] || fail "hosts run different code: $(tr '\n' ' ' <<<"$shas")"
    say "  code fingerprint on every host: $shas"
  fi
}

step_munge() {
  for h in "$V5_DBD_HOST" "${CTLD[@]}" "${NODES[@]}"; do daemon "$h" munged munge; done
  # A credential made on the controller must decode on every host: proves one shared key, and clocks in step.
  [[ $DRY == 1 ]] && return 0
  local cred; cred=$(ctl "munge -n") || fail "munge -n failed on $CTL"
  for h in "$V5_DBD_HOST" "${CTLD[@]}" "${NODES[@]}"; do
    on "$h" "unmunge" <<<"$cred" >/dev/null 2>&1 || fail "$h does not accept $CTL's munge credential (key or clock)"
  done
  say "  every host accepts the same munge key"
}

step_slurmdbd() {
  daemon "$V5_DBD_HOST" slurmdbd slurmdbd
  wait_until 120 "slurmdbd answering" ctl "sacctmgr -n show cluster"
}

step_dbbackup() {
  # Before anything writes new accounting rows: today's dump, then a test restore (ADR 0002 §1).
  # /etc/v5/db.env holds DB_ROOT_PASSWORD, written at boot from the cloud secrets store (never in the repo).
  on "$V5_DBD_HOST" "set -a; source /etc/v5/db.env; set +a; bash $SUB/slurm/backup_db.sh ${V5_BACKUP_DIR:-/var/backups/slurm} && \
    bash $SUB/slurm/backup_db.sh --verify-latest ${V5_BACKUP_DIR:-/var/backups/slurm}" >>"$LOG" 2>&1 \
    || fail "accounting DB backup or its test restore failed (see $LOG)"
}

step_slurmctld() {
  for h in "${CTLD[@]}"; do
    daemon "$h" slurmctld slurmctld
    [[ "$h" == "$CTL" ]] && wait_until 120 "primary controller answering" ctl "scontrol ping | grep -q 'is UP'"
  done
  [[ $DRY == 1 ]] && return 0
  local up; up=$(ctl "scontrol ping" | grep -c 'is UP')
  [[ $up -ge ${#CTLD[@]} ]] || fail "scontrol ping: $up of ${#CTLD[@]} controllers UP"
  say "  $up controllers UP"
}

step_accounts() {
  ctl "bash $SUB/slurm/setup_accounts.sh" >>"$LOG" 2>&1 || fail "setup_accounts.sh failed (see $LOG)"
  [[ $DRY == 1 ]] && return 0
  ctl "sacctmgr -n show assoc where account=mainrun user=$V5_SUBMIT_USER format=qos" | grep -q mainrun \
    || fail "user $V5_SUBMIT_USER has no mainrun association"
}

nodes_registered() {
  # registered = answering slurmctld: idle, allocated, mixed, or drained on purpose (not down, not unknown)
  local n; n=$(ctl "sinfo -h -N -n $1 -t idle,alloc,mix,drain -o %N | sort -u | wc -l")
  [[ ${n:-0} -ge $2 ]]
}

step_slurmd() {
  for h in "${NODES[@]}"; do daemon "$h" slurmd slurmd; done
  local list; list=$(IFS=,; echo "${NODES[*]}")
  # A node that was drained on purpose stays drained: launch never resumes it (an operator decides that).
  wait_until "$V5_WAIT_S" "every node registered" nodes_registered "$list" "${#NODES[@]}"
  [[ $DRY == 1 ]] || say "  $(ctl "sinfo -h -N -n $list -o '%N %t'" | tr '\n' ' ')"
}

step_health() {
  # Every node at once (the deep check takes minutes). health_check.py exits 0 pass, 3 warn, 4 fail. Full mode
  # does not drain by itself (only the periodic check does), so a failed node is drained here, with the
  # failed checks as the reason: the main run must never land on it.
  local pids=() h rc
  mkdir -p "$(dirname "$LOG")"
  for h in "${NODES[@]}"; do
    on "$h" "source /etc/v5/node.env 2>/dev/null; V5_EVENTS_DIR=$V5_EVENTS_DIR $V5_PY $SUB/health/health_check.py --mode full" \
      >"$LOG.health.$h.json" 2>&1 &
    pids+=($!)
  done
  local ok=0 bad=() warn=()
  for i in "${!NODES[@]}"; do
    h=${NODES[$i]}
    wait "${pids[$i]}"; rc=$?
    if [[ $rc == 0 || $rc == 3 ]]; then
      ok=$((ok + 1)); [[ $rc == 3 ]] && warn+=("$h")
    else
      bad+=("$h")
      [[ $DRY == 1 ]] && continue
      local why
      why=$(sed -n 's/.*"drain_reason": "\([^"]*\)".*/\1/p' "$LOG.health.$h.json" | head -1)
      ctl "scontrol update nodename=$h state=drain reason='health: ${why:-full check exit $rc}'" \
        || fail "could not drain $h"
    fi
  done
  [[ $DRY == 1 ]] && return 0
  say "  healthy: $ok of ${#NODES[@]}${warn:+ (warnings: ${warn[*]})}${bad:+; drained: ${bad[*]} (reports: $LOG.health.<node>.json)}"
  [[ $ok -ge $V5_MIN_NODES ]] || fail "only $ok healthy nodes, the main run needs $V5_MIN_NODES"
}

step_services() {
  for h in "${CTLD[@]}"; do
    on "$h" "systemctl enable --now v5-keep-spare.timer v5-watch.service" || fail "$h: controller services"
  done
  for h in "${NODES[@]}"; do
    on "$h" "systemctl enable --now v5-spot-watch.service" || fail "$h: spot watcher"
  done
}

step_store() {
  # Fencing (ADR 0001 §3) needs a store that refuses a stale write; an endpoint that ignores If-Match would
  # let two attempts both commit. Checked here, before any GPU hour is spent.
  local out
  out=$(ctl "source /etc/v5/node.env 2>/dev/null; $V5_PY $SUB/ckpt/ckpt.py probe-store --run $V5_REMOTE_ROOT/$RUN_ID") \
    || fail "checkpoint store probe failed: $out"
  say "  $out"
  [[ $DRY == 1 ]] && return 0
  local n; n=$(ctl "source /etc/v5/node.env 2>/dev/null; $V5_PY $SUB/ckpt/ckpt.py list --run $V5_REMOTE_ROOT/$RUN_ID" | wc -l)
  say "  run $RUN_ID: $n committed checkpoints ($([[ $n -gt 0 ]] && echo 'the run resumes from latest.json' || echo 'fresh start'))"
}

step_submit() {
  local q t0
  t0=$(date -u +%Y-%m-%dT%H:%M:%S)
  if [[ $DRY == 0 ]]; then
    q=$(ctl "squeue -h -n v5-mainrun -o '%A %T'")
    # already queued: the attempt that runs now may have started long ago, so accept its events of any time
    if [[ -n "$q" ]]; then say "  main run already queued: $q (not submitted again)"; t0=""; fi
  fi
  if [[ -z "${q:-}" ]]; then
    local exp="ALL,RUN_ID=$RUN_ID${V5_MAIN_ENV:+,$V5_MAIN_ENV}"
    q=$(ctl "cd /tmp && runuser -u $V5_SUBMIT_USER -- sbatch --parsable --export=$exp $V5_MAIN_ARGS $SUB/slurm/mainrun.sbatch") \
      || fail "sbatch refused the main run: $q"
    say "  submitted job ${q%%;*}"
  fi
  [[ $DRY == 1 ]] && return 0
  # Proof it runs, not only that Slurm started it: this attempt claimed the run (fencing) and restored, after
  # which the trainer logs train.started. (A run that already reached its last step restores and exits 0
  # without a training step, so we wait for train.started, not train.step.)
  local ev="cat $V5_EVENTS_DIR/*.jsonl 2>/dev/null | grep '\"run_id\": \"$RUN_ID\"'"
  local since="awk -F'\"time\": \"' '{ if (substr(\$2,1,19) >= \"$t0\") print }'"
  wait_until "$V5_WAIT_S" "train.started of this attempt" ctl "$ev | $since | grep -q '\"event\": \"train.started\"'"
  say "  $(ctl "$ev | $since | grep -E '\"event\": \"(checkpoint.claimed|train.started)\"' | cut -c1-200")"
  q=$(ctl "squeue -h -n v5-mainrun -o '%A %T'")
  if [[ -n "$q" ]]; then say "  main run: $q"
  else say "  main run is not queued any more (finished or held): $(ctl "sacct -X -n -n --name v5-mainrun -o jobid,state,exitcode | tail -1")"; fi
}

step_status() {
  ctl "$V5_PY $SUB/queue/job_queue.py status" | tee -a "$LOG" >&2
}

# ------------------------------------------------------------------------------------------------- run

started=0; [[ -z "$FROM" ]] && started=1
[[ -n "$FROM$ONLY" ]] && ! printf '%s\n' "${STEPS[@]}" | grep -qx "${FROM:-$ONLY}" && { echo "no step '${FROM:-$ONLY}' (see --list)" >&2; exit 2; }
say "V5 launch: run $RUN_ID, controller ${CTL:-?}, ${#NODES[@]} nodes, store ${V5_REMOTE_ROOT:-?}$([[ $DRY == 1 ]] && echo ', DRY RUN')"
for STEP in "${STEPS[@]}"; do
  [[ "$STEP" == "$FROM" ]] && started=1
  [[ $started == 1 ]] || continue
  [[ -n "$ONLY" && "$STEP" != "$ONLY" ]] && continue
  if [[ " $V5_SKIP " == *" $STEP "* ]]; then say "== $STEP: SKIPPED (V5_SKIP)"; continue; fi
  say "== $STEP: $(why "$STEP")"
  t=$SECONDS
  "step_$STEP"
  say "   ok ($((SECONDS - t)) s)"
done
say "launch complete (log: $LOG)"
