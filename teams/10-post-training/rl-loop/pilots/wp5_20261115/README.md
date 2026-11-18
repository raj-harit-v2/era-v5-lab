# WP5 execution snapshot, 15 Nov 2026

These are the executed deployment/staging scripts and configurations, copied without runtime changes. They are an execution snapshot with external input requirements, not a self-contained data download/rebuild kit. See `../../../results/wp5_code_rl_pilot.md` and its JSON evidence.

- `stage_pilot.py` runs from a staging directory containing `rldata_rebuild/out/v1/cc.jsonl`, `qwen_tok/tokenizer.json` and an existing `wp5/` directory. It checks the RL v1 source SHA, writes the deterministic 64/48 split under `wp5/data/`, and records file hashes. Use the pinned Qwen2.5-Coder-1.5B-Instruct tokenizer recorded in the report. The source file and tokenizer are external inputs.
- Supply the resulting three data files under this snapshot's `data/` before invoking the Modal driver. Data, answers, logs and model files are excluded from Git. Expected data hashes are in the pilot JSON evidence.
- Set `G10_TEAM_DIR` to the absolute `teams/10-post-training` directory. The unmodified driver's default path is the original controller workspace layout; the explicit override makes the snapshot location usable. The driver uploads only `rl/verifier.py`, `rl-data` and `rl-loop`; it does not upload `rl/tasks` or `rl/go` as RL tasks.
- `isolation_probe.py` is the original Modal probe. The public asserting CLI is `rl-data/check_local_isolation.py`; its Docker command is in the trainer report.
- `spend.jsonl` retains all observed task costs. Its total is estimated, not dashboard billing. Do not reset it to bypass the task's $2.90 total/$2.55 scheduling guard. The recorded 30-minute run is now refused by the remaining guard. No run is requested by this snapshot.

Historical command, from the repository root, with the documented input files present:

```bash
G10_TEAM_DIR="$PWD/teams/10-post-training" modal run teams/10-post-training/rl-loop/pilots/wp5_20261115/modal_app.py::pilot \
  --config teams/10-post-training/rl-loop/pilots/wp5_20261115/cfg_7b.yaml \
  --run-id p7b --timeout-s 1800 --gpu A100-80GB --model-key 7b
# p7b: killed: max_seconds reached; 1800.8 function seconds; estimated function cost $1.5664
```

The historical run ID identifies preserved evidence; reuse would overwrite that run directory. Any separately authorized future run needs a distinct ID and a reconciled budget. The four-step state was not checkpointed, so it cannot be resumed from these files.
