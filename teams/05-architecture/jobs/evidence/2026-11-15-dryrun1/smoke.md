# Dry run 1: end-to-end smoke of the command

This is a test log. It is not a bits-per-byte result and it is not a speed measurement.

## What was run

- Source: `train_week2.py` at [71bc0fb](https://github.com/theschoolofai/era-v5-lab/commit/71bc0fbb99fbe5e90d8a09055b7622010e8ab23f) with the C3 scoring patch from #474 applied (head `f9fd0df`, patch sha256 `a35945f709116e4150c5edb98c19762ef3bc9438cb8619e8c500e8a3437756d7`). The patch applied clean.
- Not in this smoke: TSAI's Gate 2 speed fixes, `runtime_fast.yaml` and the `t2m1` resolution. These three are staged by TSAI and are not in the repository. The smoke used the checked-in `runtime.yaml` and the loop path.
- Machine: Apple laptop, CPU only, 8 GB memory, Python 3.13, PyTorch 2.13.0, fp32.
- Arm: `exp2_muon.yaml`, the same file the job names. The model is the full T2 size (237,052,416 parameters). Only the context (32), the batch (2) and the step count (3) are small.
- Tokenizer: frozen C3, sha256 `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3`. The file is not in this pull request.
- Byte table: built here with `python teams/04-ke2/src/build_tables.py --tokenizer ./inputs/tokenizer_c3.json --pos-dims 32 --out ./out/c3-tables`. Raw P32 content sha256 `fc5e5f8ffacbe93ecdedc276661edfd43ed9a13621eb4a68166ef80e24e88f9b`, file sha256 `dfbb3207bba13cb46899afc7aad06e876a84961f6a4e206980cd39071f2926d3`. The content sha256 is the one `frozen_tok.md` in #474 lists. The file sha256 is not the one listed there (`f775213c…`). The trainer checks the content sha256 and the tokenizer sha256 stored inside the table. The table has 131,072 rows, none truncated, none empty.
- Training text: `teams/05-architecture/jobs/fixtures/exp1_smoke_train.jsonl` from main (2 documents).
- Held-out text: 15 real documents of `heldout_v1`, one per slice. The ids are in [heldout_subset_ids.txt](heldout_subset_ids.txt). To rebuild the two files, keep the rows of `heldout_v1.jsonl` and `heldout_v1_sources.jsonl` whose id is in that list, in file order. The sha256 values are `c8a2edf8…04f17` and `c9c8b7a7…fb77c`, as the manifest records them.
- `G5_DOCUMENT_CACHE_DIR` was not set.

## Command

Run from the repository root. The local paths are written here as `./inputs` and `./out`. Nothing else is changed.

```bash
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_muon.yaml --runtime teams/05-architecture/configs/runtime.yaml --tokenizer-release frozen-c3 --tokenizer ./inputs/tokenizer_c3.json --byte-table ./inputs/raw_table_c3_P32.npz --train-data teams/05-architecture/jobs/fixtures/exp1_smoke_train.jsonl --heldout-data ./inputs/heldout_subset.jsonl --heldout-sources ./inputs/heldout_subset_sources.jsonl --device cpu --seed 1236 --smoke --smoke-steps 3 --smoke-seq-len 32 --smoke-batch-size 2 --no-checkpoint --out ./out/dryrun1-smoke
```

Exit code 0. The trainer prints nothing to the terminal. It writes its output to files. `summary.json`, complete:

```text
{
  "status": "SMOKE",
  "steps": 3,
  "wall_seconds": 850.7738585416228,
  "timed_out": false,
  "first_ce": 12.154038429260254,
  "last_ce": 6.291483402252197,
  "final_model_sha256": "bb2d2092371d6061bc6c82be58ceca3ebb91eae932d4285ae4d7950d795bd4c1",
  "eligible_for_quality_comparison": false
}
```

The other output files are beside this page: [manifest.json](manifest.json), [metrics.jsonl](metrics.jsonl), [losses.txt](losses.txt), [total_losses.txt](total_losses.txt).

## What the smoke shows

1. The command form of the job runs end to end with the frozen C3 tokenizer and its matching table: load, step-0 held-out pass, three Muon steps, final held-out pass, output files.
2. The loss and the gradient norm are finite at every step. Training loss went 12.154, 8.844, 6.291. Gradient norm before clipping was 12.78, 10.09, 9.18.
3. The manifest records `optimizer.name: muon`, `optimizer.muon_lr: 0.01`, `optimizer.adamw_lr: 0.001`, and `bpb_policy: original UTF-8 bytes, with C3 tokenizer normalization`.
4. The held-out score divides by the original bytes. The 15 documents have 15,999 original UTF-8 bytes and 15,939 bytes after the C3 normalizer. `val/utf8_bytes` is 15999 and `val/encoded_utf8_bytes` is 15939. The three slices that the normalizer changes keep their original counts in `val/slices/*/utf8_bytes`:

| Slice | Document | Original bytes | Bytes after C3 normalizer | `utf8_bytes` in metrics |
|---|---|---:|---:|---:|
| as | `fw2-as-test-000012` | 2069 | 2036 | 2069 |
| bn | `fw2-bn-test-000001` | 1428 | 1410 | 1428 |
| pa | `fw2-pa-test-000023` | 1356 | 1347 | 1356 |

The other 12 documents do not change under the normalizer.

## Wall time

- Trainer wall time: 850.8 seconds. Whole process: 856.0 seconds.
- Step time: 282.0, 277.8 and 284.2 seconds for the three steps. Almost all of the wall time is in these three steps.
- This is the loop path on a laptop CPU with 8 GB of memory and a 237 M parameter model. It says nothing about the GPU run. On the same machine the same arm with tokenizer v0 and without the C3 patch took 275.8 to 372.0 seconds per step, so the patch does not add the time.
- I have no GPU on this machine. The step time of the real run comes from TSAI's speed-fix source. #474 has a CUDA smoke of the same command form: 5.98 seconds for three steps on an RTX 3070 laptop GPU.

## Unit tests

Run from the repository root, at 71bc0fb with the patch applied:

```bash
python -m unittest discover -s teams/05-architecture/tests -p 'test_week2*.py'
```

```text
Ran 114 tests in 4.097s

FAILED (failures=2, skipped=1)
```

The two failures are `test_muon_not_silently_adamw` and `test_muon_rate_and_comparison_remain_pending` in `test_week2_model.py`. Both also fail at 71bc0fb without the patch (113 tests, 2 failures, 1 skipped). Both read `exp2_muon.yaml` and were written when the Muon arm had no rate: one expects `muon_lr` to be unset, the other expects a Muon validation error. The file now has `muon_lr: 0.01`. Neither test touches the training step or the scoring.

```bash
python -m unittest discover -s teams/05-architecture/tests -p test_week2_scoring.py -k test_frozen_c3_bpb_uses_original_bytes -v
```

```text
test_frozen_c3_bpb_uses_original_bytes (test_week2_scoring.SliceTests.test_frozen_c3_bpb_uses_original_bytes) ... ok

Ran 1 test in 0.047s

OK
```

## Not checked here

- The full T2 shape: context 2,048 and batch 8.
- bf16 and CUDA.
- TSAI's speed fixes, `runtime_fast.yaml` and the `t2m1` resolution.
- The staged `train.jsonl`. I do not have this file.
- The full `heldout_v1` under frozen C3 on this machine. #474 reports that all 1,059 documents load with the patch.
