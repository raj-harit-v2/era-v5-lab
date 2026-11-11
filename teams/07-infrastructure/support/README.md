# Support (optional): the evidence behind the submission

**Not needed to read, use or review the design.** The submission is the topic folders next to this one ([`../README.md`](../README.md)).
This folder holds what we used to **prove** it: tests, a Docker copy of the Slurm cluster with drills, a tiny
test trainer, GPU checks for Kaggle, the cost model, and generated reports.

| Folder | What | Needs |
|---|---|---|
| `tests/` | unit tests for checkpoint (T1–T13), queue, health, cost and monitoring, with their fixtures | Docker (or Python with torch) |
| `simulation/` | the Docker Slurm cluster, the drill script (`run_sim.py`), the test trainer, the architecture team's `config_v0.yaml`, and the latest results; see [simulation/README.md](simulation/README.md) | Docker, ~25 min |
| `kaggle/` | GPU checks on Kaggle's free 2 GPUs (real `nvidia-smi`, NCCL all-reduce and timeout, checkpoint tests on CUDA, save speed); see [kaggle/README.md](kaggle/README.md) | a Kaggle account |
| `cost/` | cost model (Young's interval, spot vs on-demand, hot spare), its report, and the "instances outside Slurm" check | Python |
| `tools/` | `bench_save.py`: the real checkpoint stall on a GPU | a GPU |
| `docs/` | [review_week1.md](docs/review_week1.md) (results, instructor questions, status), [sim_results.md](docs/sim_results.md), [metrics_catalog.md](docs/metrics_catalog.md), [codes_and_actions.md](docs/codes_and_actions.md), [deepspeed_impact.md](docs/deepspeed_impact.md) (proposal: what changes in each ADR if we train with DeepSpeed), [team08_contract_notes.md](docs/team08_contract_notes.md) (Team 08's health JSON contract: what we changed, what we suggest) | — |

## Run the evidence

From `teams/07-infrastructure`, with Docker Desktop running. Nothing needs the cloud.

```bash
docker compose -f support/simulation/slurm-docker/docker-compose.yml build slurmdbd   # once, ~5 min

# 1. unit tests (~1 min)
docker run --rm -v "$PWD":/opt/v5:ro --entrypoint bash v5-slurm-sim:1 \
  -c 'cd /opt/v5 && python -m pytest -q -p no:cacheprovider -W ignore support/tests'

# 2. the checkpoint tests against S3 (the moto emulator, the real boto3 code path)
docker run --rm -v "$PWD":/opt/v5:ro --entrypoint bash v5-slurm-sim:1 -c '
  cd /opt/v5; moto_server -p 9000 >/dev/null 2>&1 & sleep 3
  export V5_S3_ENDPOINT=http://127.0.0.1:9000 V5_S3_ACCESS_KEY=test V5_S3_SECRET_KEY=test
  python -c "import boto3; boto3.client(\"s3\", endpoint_url=\"http://127.0.0.1:9000\").create_bucket(Bucket=\"v5-test\")"
  V5_TEST_REMOTE=s3://v5-test/ckpt python -m pytest -q -p no:cacheprovider -W ignore support/tests/test_ckpt.py'

# 3. the full Docker Slurm simulation, every drill (~25 min); ends with "N/N drills passed"
python3 support/simulation/run_sim.py      # results in support/simulation/results/, summary in support/docs/sim_results.md

# 4. cost model (results in node-hours; no price in the repo)
docker run --rm -v "$PWD":/opt/v5 --entrypoint bash v5-slurm-sim:1 \
  -c 'cd /opt/v5 && python support/cost/cost_model.py --measured support/simulation/results/metrics.json'

# after editing metrics/catalog.yaml or common/reasons.py, regenerate the pages
docker run --rm -v "$PWD":/opt/v5 --entrypoint bash v5-slurm-sim:1 -c 'cd /opt/v5 &&
  python metrics/evaluate.py --render-md ../support/docs/metrics_catalog.md &&
  python metrics/explain.py --all ../support/docs/codes_and_actions.md'
```

What "pass" looks like: all unit tests pass in steps 1 and 2; step 3 ends with `N/N drills passed`.

The tests also guard the layout: `tests/test_queue.py` fails if any `/opt/v5/...` path in the Slurm files, the
job scripts or the Docker files points to a file that does not exist, and `tests/test_monitoring.py` fails if
the code can report a cause that has no plain-words explanation.

## Review checklist (for the lead)

- [ ] Every decision in ADR 0001–0004 has an "In simple words" box a non-infra student can follow.
- [ ] Each item in `docs/review_week1.md` is marked fixed / tested / open, with a reason.
- [ ] Unit tests pass (steps 1–2); the simulation passes if you run it (step 3).
- [ ] Every HIGH alert and every exit-78 cause says what to do (`metrics/README.md`, `docs/codes_and_actions.md`).
- [ ] the price of a node-hour is given at run time (`--price-per-node-h`) when a money figure is needed; the repo holds none.
- [ ] Open points in each ADR have an owner and a date.
