# harness_lab: score a lab checkpoint, write eval-mini v1

`run_lab_ckpt.py` takes the folder of a run in the checkpoint store and writes one eval-mini v1 file
(`../results/eval_mini_v1_schema.md`, section 6).

Steps it does: read `latest.json` (or the `commits.jsonl` line of `--step`) -> read `MANIFEST.json` ->
`export_safetensors()` (Team 7; checks sha256 of every file and the probe-loss bits) -> score -> build the v1 records ->
`check(doc, 0)` from `results/convert_v0_to_v1.py` -> write the file (byte-identical on a rerun).

```bash
python teams/07-infrastructure/jobs/restore_test/restore_test.py          # makes the CPU test store
python teams/09-evaluation/harness_lab/run_lab_ckpt.py \
    --run-dir teams/07-infrastructure/jobs/restore_test/out/ckpt_store/restore-b
```

CPU log: `logs/cpu_test.log`. Needs torch >= 2.14.1, safetensors, and the pinned `kronecker-embeddings`
(`teams/04-ke2/src/requirements.txt`).

## What is and is not done

| | State |
|---|---|
| Pointer, manifest, `model_revision`, `checkpoint` block, export, `check(doc, 0)` | Done, tested on the tiny MoE on CPU |
| `--scorer smoke` (next-token accuracy on Team 5's seeded stream) | Done. It tests the pipeline. It is not an eval-mini task and says nothing about quality |
| lm-eval tasks on a real lab model | **Not wired.** The tokenizer (BrahmicTokenizer-131K) and Team 5's model (`week2/model.py`) exist; an lm-eval wrapper that loads them does not. `--scorer <module>:<function>` is reserved for it |
| Team 5 `checkpoint.pt` + `manifest.json` layout (section 6, last paragraph) | Not done |
| `--run-name` for queue jobs (`<job_run_id>/<arm>`) | Done, not tested on a real queue job |

## Schema point to confirm

Section 6 says `checkpoint.epoch` is the `<E>` in the folder name, and also that it comes from `latest.json`. After a restore,
`latest.json` holds epoch + 1 (the restore claims it) while the folder is still `-e1`. The script takes the folder name.
