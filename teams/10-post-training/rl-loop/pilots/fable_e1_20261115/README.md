# Code-RL and Deletion-Tuning-RL drivers, 15 Nov 2026

These are the executed Modal drivers and configurations behind `../../../results/code_rl_e1_20261115.md`,
`../../../results/dt_rl_e4_20261115.md` and `../../../results/verifier_data_note_20261115.md`, copied without runtime
changes. They are an execution snapshot with external input requirements, not a self-contained rebuild kit. Data,
answers, completions, logs, model weights and run states are not in Git. Surrogate evidence (public Qwen model,
one seed); nothing here is a capstone result.

## Entry points

`modal_app.py` (app and volume `g10-fable-e1-2026-11-15`; A100-80GB, H200 for Deletion Tuning, CPU for scoring):

| Entry point | What it does |
|---|---|
| `::weights` | Downloads Qwen2.5-Coder-7B-Instruct @ `c03e6d35` to the volume and records the safetensors sha256. |
| `::check` | CPU preflight with the network blocked: sandbox isolation probes (`isolation_probe.py`), then the task construction the GPU job will do. |
| `::e1 --run-id ID --steps N --budget-s S --max-calls C` | The code-RL run (`cfg_e1.yaml`): screen, objective_v1 on attention weights, held-out and train-cohort evaluations, durable state. Runs as budgeted calls: each call pauses at its deadline and the next continues from the saved state. |
| `::e4 --run-id ID --steps N --config cfg_e4_dt.yaml --train-ids-file F` | Deletion Tuning as the RL method on a fixed cohort (no screen), H200. `cfg_e4b_dt.yaml` is the 10x mask-lr variant. |
| `::rescore --run-id ID --limit 1536` | Matched scoring benchmark: the screen's saved completions scored four ways (8 threads with and without early exit, 32 threads, 32-process `score_pool`). |
| `::sample --run-id ID` | Fresh samples from the base model and from the run's latest state (`rl-loop/sample_from_state.py`), held-out and cohort. |
| `::dryrun --config CFG` | Only the CPU dry run of a config in the job image. |

`::e1` and `::e4` call a CPU dry run in the same image (`smoke`) before every GPU call and refuse to start the GPU
call if it fails: every module the config imports must be in the image, and the trainer's state, pause/resume and
Deletion Tuning branches must run on a tiny random model. It was added after two E4 launches failed within two
minutes each (a file missing from the image; a log line in a sampler-only branch that no CPU test had run).

`modal_audit.py` (app `g10-fable-audit-2026-11-15`, CPU only):

| Entry point | What it does |
|---|---|
| `::audit --run-id ID` | Fetches the pinned `deepmind/code_contests` parquet shards (revision `802411c3`), checks each shard's sha256 and that the kept 20 tests equal the task's tests, then runs every reward-1 screen completion on up to 80 source tests the reward never used (network blocked for the run step). Prints counts only. |
| `::audit_trained --run-id ID` | The same audit on the completions written by `modal_app.py::sample`. |

`stage_e1.py <cc.jsonl> <tokenizer.json> <out dir>` writes the deterministic 192 train / 96 held-out split from the
RL data v1 code_contests file (source sha256 checked), using the same hash rule as `../wp5_20261115/stage_pilot.py`.
Its outputs contain task records with tests: keep them out of the repository.

`isolation_probe.py` is the same probe as in `../wp5_20261115/` (byte-identical).

## External inputs

- `G10_E1_WORK`: an absolute path to a private work folder outside Git. The drivers read
  `$G10_E1_WORK/e1/data/{tasks.jsonl,train_ids.txt,heldout_ids.txt}` (from `stage_e1.py`), read
  `$G10_E1_WORK/e1/private/cohort_ids_<run>.txt` for `::sample` (and pass it to `::e4` via `--train-ids-file`), append
  every call's estimated cost to `$G10_E1_WORK/SPEND.jsonl`, and write result JSON under `$G10_E1_WORK/e1/`.
- `G10_E1_CAP_USD` (default 14): a call is refused when the ledger plus the call's worst case (function timeout x
  rate) would pass this cap. The ledger is an estimate from client wall time, not the billing page. Do not reset it
  to get past the guard.
- RL data v1 code_contests (`cc.jsonl`, sha256 `91ee9951…9be0`) and the pinned Qwen tokenizer, for staging.
- A Modal account; rates in the code are `modal billing rates` as read on 15 Nov 2026.

## Historical commands (from this folder)

```bash
G10_E1_WORK=<private folder> modal run modal_app.py::weights
G10_E1_WORK=<private folder> modal run modal_app.py::check
G10_E1_WORK=<private folder> G10_E1_CAP_USD=22 modal run --detach modal_app.py::e1 --run-id e1a --steps 60 --budget-s 3000 --grace-s 600 --max-calls 2
G10_E1_WORK=<private folder> modal run modal_app.py::rescore --run-id e1a --limit 1536
G10_E1_WORK=<private folder> modal run modal_audit.py::audit --run-id e1a
G10_E1_WORK=<private folder> modal run modal_app.py::sample --run-id e1a
G10_E1_WORK=<private folder> modal run modal_audit.py::audit_trained --run-id e1a
G10_E1_WORK=<private folder> G10_E1_CAP_USD=<cap> modal run --detach modal_app.py::e4 --run-id e4a --steps 30 --budget-s 3600 --grace-s 600 --max-calls 1 --train-ids-file <private folder>/e1/private/cohort_ids_e1a.txt
G10_E1_WORK=<private folder> G10_E1_CAP_USD=<cap> modal run --detach modal_app.py::e4 --run-id e4a --steps 60 --budget-s 2400 --grace-s 600 --max-calls 1 --train-ids-file <private folder>/e1/private/cohort_ids_e1a.txt
G10_E1_WORK=<private folder> G10_E1_CAP_USD=<cap> modal run --detach modal_app.py::e4 --run-id e4b --steps 20 --budget-s 1500 --grace-s 300 --max-calls 1 --config cfg_e4b_dt.yaml --train-ids-file <private folder>/e1/private/cohort_ids_e1a.txt
```

`e4a` ran as a 30-step call and was then extended to 60 steps by resume (second line). `G10_E1_CAP_USD` was the session guard:
22 for the E1 calls, raised step by step to 29.5 for the E4 calls as the ledger grew (the account held $30). The reports give the whole call history, including failed launches. The run IDs identify preserved evidence on the volume; reusing one would resume or refuse that
run, not start a new one. No run is requested by this snapshot.

## Not in this folder

The drivers for the DT marker-control, untied-head and sweep arms (`modal_e2.py`), the MoE mismatch probe
(`modal_e3.py`) and the run watchdog (`watch_run.py`) stayed local: they mount the experimental worktree by an absolute
path. They call only in-repo entry points (`sft/bench/train.py`, `sft/bench/evaluate.py`, `rl-loop/mismatch_probe.py`);
the reports give the exact arguments.
