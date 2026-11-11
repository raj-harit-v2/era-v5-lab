# Launch (`launch/`): starting the whole stack, in order

Plain-words overview and the reasons behind it: [team briefing §3.7](../TEAM_BRIEFING.md#37-starting-the-cluster-operations).
Full step table: [team README](../README.md#starting-production-opslaunchsh).

| File | What |
|---|---|
| `launch.sh` | starts and checks everything in order; stops at the first failure; safe to run twice |
| `cluster.env.example` | what `launch.sh` needs: hosts, minimum healthy nodes, checkpoint store, run id (no secrets) |

## How it works, step by step

```text
cp launch/cluster.env.example /etc/v5/cluster.env   (edit hosts, store, run id)
launch/launch.sh            every step: do it (only if not already done) → check it → next, or STOP with the reason

 1 preflight   settings complete · every host reachable · the same code on every host
 2 munge       munged on every host · a credential from the controller decodes everywhere (one key, clocks ok)
 3 slurmdbd    accounting daemon up and answering
 4 dbbackup    dump the accounting database AND restore it into a scratch copy (a backup counts only then)
 5 slurmctld   primary and backup controller up (scontrol ping)
 6 accounts    slurm/setup_accounts.sh (QOS, team accounts, GPU shares, budgets) · main run may preempt
 7 slurmd      every GPU node registered (a node drained on purpose stays drained)
 8 health      health_check.py --mode full on every node at once · a failing node is drained ·
               fewer healthy nodes than V5_MIN_NODES → STOP
 9 services    alert watcher + hot-spare timer (controller) · spot watcher (every node)
10 store       ckpt.py probe-store: write, read, and a stale write refused (fencing needs it)
11 submit      main run submitted unless already queued · it claimed its epoch, restored and started
12 status      job_queue.py status
```

```bash
launch/launch.sh --list          # the steps
launch/launch.sh --dry-run       # what would run where; nothing changes
launch/launch.sh --from health   # continue after fixing a failed step
launch/launch.sh --only store    # one step
```

Hosts are reached through `V5_EXEC` (`ssh -o BatchMode=yes %h` by default; the Docker test uses
`docker exec -i slurm-docker-%h-1`). Secrets never sit in `cluster.env`: the database password is read on its host
from `/etc/v5/db.env`.
