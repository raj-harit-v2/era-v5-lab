# Team 08 private Grafana dashboard (`private_v1.json`)

A private dashboard that reads training metrics from ClickHouse. Panels:

- Training, per step from `metrics_raw`: next-token loss, MTP loss, learning rate, tokens/s, GPU memory, MFU.
- Validation loss (panel 20, `metrics_raw`): `validation_loss` as points at each validation run, with the training `loss_ntp` as a thin line on the same axis (both nats per token). Worked out by `metrics_logger/metrics_writer.py` from G5's `val/nll_nats` / `val/scored_tokens`; for G5's own `metrics.jsonl` (no `validation_loss` field) the query works it out from those two rows.
- Validation bits per byte (panel 25, `metrics_raw`): `validation_bpb`, held-out bits per UTF-8 byte (G5's `val/bpb`), as points at each validation run, one series per run. It counts bytes, not tokens, so runs with different G3 tokenizers can be compared here; `validation_loss` (panel 20) only between runs with the same tokenizer. Worked out by `metrics_logger/metrics_writer.py` as `val/nll_nats / (ln(2) * val/utf8_bytes)`. For G5's own `metrics.jsonl` the query takes `val/bpb`, or works it out from `val/nll_nats` and `val/utf8_bytes`; one value per run and step.
- Rollups from `metrics_rollup_<N>`: mean loss per 10 / 100 / 1000 / 10000 step bucket (pick with the `bucket` variable).
- GPU telemetry from `gpu_telemetry_1s`: power and temperature.
- GPU memory used (panel 26, `gpu_telemetry_1s`): `gpu_memory_used`, the memory nvidia-smi reports in use on the whole GPU (all processes), in bytes, shown as GiB. One line per run and GPU, the largest value in each 10-second window. Readings arrive in MiB (`mem_used_mib`); `clickhouse/load_jsonl.py` and `metrics_logger/metrics_writer.py` (`gpu_memory_used`) multiply them by 1,048,576. It is higher than `gpu_alloc_gib` (panel 6), which counts only PyTorch's allocations.
- GPU temperature and thermal throttle per step (panel 22, `metrics_raw`): `gpu_temp_c` with green / yellow / red at 75 C and 85 C, and `gpu_thermal_throttle` (0/1) on the right axis. Written by `metrics_logger/gpu_thermal.py`.
- Gradient norm per step (panel 17, `metrics_raw`): `gradient_norm`, the norm before clipping, with a dashed red line at `run.grad_clip` = 1.0. Written by `teams/05-architecture/harness/train.py`.
- Gradient clipping rate (panel 19, `metrics_raw`): share of steps with `gradient_clipping_applied` = 1 per `bucket`-step bucket (yellow from 0.5). Worked out by `metrics_logger/metrics_writer.py` from `gradient_norm` and `grad_clip`, or written by G5's `train_week2.py` as true / false.
- MoE expert load imbalance (panel 27, `metrics_raw`), next to Router MaxVio (panel 21): `expert_load_imbalance`, busiest expert / average expert (`max(shares) * num_experts`) in the worst MoE layer, per step and run. 1.0 is perfectly balanced; orange from 1.5, red from 2.0 (the busiest expert gets twice the average share). It equals `router_max_vio` + 1. Worked out by `metrics_logger/metrics_writer.py` `expert_load_imbalance` from `expert_load`.
- Update-to-weight ratio (panel 24, `metrics_raw`): `update_weight_ratio`, global L2 `||lr * update|| / ||W||` (default every 10 steps). Worked out by `metrics_logger/metrics_writer.py` `compute_update_weight_ratio`.

- Eval-mini score per checkpoint (panel 28, `eval_mini`): Team 9's eval-mini score of each lab checkpoint, filled by Team 9's `eval_watcher.py`. x is `checkpoint_step`, y the task's primary metric in percent (`primary = 1`, `teams/09-evaluation/results/eval_mini_v1_schema.md`), one line per run and task. Rows with no checkpoint step (the Hugging Face reference models) are left out. When one checkpoint has more than one row (scored again, or the same step after a restart, also across loader `run_id`s), the query keeps the row with the highest `checkpoint_epoch`, then the latest `loaded_at`. Pick runs and tasks with the `eval_run` and `eval_task` variables.

MFU, GPU and eval panels stay empty until a run that logs those metrics is loaded.

## 1. Start ClickHouse and load the data

Follow `../clickhouse/README.md`: start the container, apply `schema_v1.sql` and `rollups_v1.sql`, then load runs with `load_jsonl.py`.

## 2. Start Grafana in Docker

Save this as `datasource.yaml` in a folder, for example `./provisioning/datasources/`:

```yaml
apiVersion: 1
datasources:
  - name: ClickHouse
    uid: era-v5-clickhouse
    type: grafana-clickhouse-datasource
    isDefault: true
    jsonData:
      host: host.docker.internal
      port: 9000
      protocol: native
      username: default
      defaultDatabase: default
```

Then run Grafana. Anonymous admin access is only for a local machine. Do not expose this port.

```bash
docker run -d --name era-v5-grafana -p 127.0.0.1:3000:3000 \
  -e GF_INSTALL_PLUGINS=grafana-clickhouse-datasource \
  -e GF_AUTH_ANONYMOUS_ENABLED=true -e GF_AUTH_ANONYMOUS_ORG_ROLE=Admin \
  -v "$PWD/provisioning/datasources:/etc/grafana/provisioning/datasources" \
  grafana/grafana:latest
```

On Linux, add `--add-host=host.docker.internal:host-gateway` to the command.

Check that the datasource works:

```bash
curl -s localhost:3000/api/datasources/uid/era-v5-clickhouse/health
# {"message":"Data source is working","status":"OK"}
```

## 3. Import the dashboard

In Grafana: Dashboards > New > Import > upload `private_v1.json`. Or with the API:

```bash
python3 -c "import json;print(json.dumps({'dashboard': json.load(open('private_v1.json')), 'overwrite': True}))" \
  | curl -s -X POST localhost:3000/api/dashboards/db -H 'Content-Type: application/json' -d @-
```

Open http://localhost:3000/d/era-v5-private-v1. Choose a ClickHouse datasource in the `ClickHouse` variable if the picker is empty, then pick `run_id`.

## 4. Export after changes

Save changes in Grafana, then export the dashboard JSON (Dashboard > Export > Save to file). Remove the numeric `id` field before committing so the file imports cleanly.

## Adding a panel

Open a separate small pull request that edits only your panel in `private_v1.json`. Use a unique panel `id`. Query `metrics_raw` for per-step values or `metrics_rollup_<N>` for buckets, and filter with `run_id IN ($run)`.
