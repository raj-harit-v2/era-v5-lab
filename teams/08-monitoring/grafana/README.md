# Team 08 private Grafana dashboard (`private_v1.json`)

A private dashboard that reads training metrics from ClickHouse. Panels:

- Training, per step from `metrics_raw`: next-token loss, MTP loss, learning rate, tokens/s, GPU memory, MFU.
- Validation loss (panel 20, `metrics_raw`): `validation_loss` as points at each validation run, with the training `loss_ntp` as a thin line on the same axis (both nats per token). Worked out by `metrics_logger/metrics_writer.py` from G5's `val/nll_nats` / `val/scored_tokens`; for G5's own `metrics.jsonl` (no `validation_loss` field) the query works it out from those two rows.
- Rollups from `metrics_rollup_<N>`: mean loss per 10 / 100 / 1000 / 10000 step bucket (pick with the `bucket` variable).
- GPU telemetry from `gpu_telemetry_1s`: power and temperature.
- GPU temperature and thermal throttle per step (panel 22, `metrics_raw`): `gpu_temp_c` with green / yellow / red at 75 C and 85 C, and `gpu_thermal_throttle` (0/1) on the right axis. Written by `metrics_logger/gpu_thermal.py`.
- Gradient norm per step (panel 17, `metrics_raw`): `gradient_norm`, the norm before clipping, with a dashed red line at `run.grad_clip` = 1.0. Written by `teams/05-architecture/harness/train.py`.
- Gradient clipping rate (panel 19, `metrics_raw`): share of steps with `gradient_clipping_applied` = 1 per `bucket`-step bucket (yellow from 0.5). Worked out by `metrics_logger/metrics_writer.py` from `gradient_norm` and `grad_clip`, or written by G5's `train_week2.py` as true / false.

MFU and GPU panels stay empty until a run that logs those metrics is loaded.

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
