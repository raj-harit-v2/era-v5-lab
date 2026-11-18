# SFT bench (G10, WP3)

One small, tested harness that runs SFT on an SFT-v1 slice and reports task gain and forgetting the same way for every
method and model. First surrogate: `HuggingFaceTB/SmolLM2-135M` @ `93efa2f097d58c2a74874c7e644dbc9b0cee75a2` (Apache-2.0).
Results: [`../../results/small_sft.md`](../../results/small_sft.md). Scorers: [`../eval_v1.md`](../eval_v1.md).

| File | What |
|---|---|
| `slice.py` | Builds train/dev/test from admitted OCR-2 pack rows. Split unit = near-duplicate cluster of the problem family key (never a row, never the completion id). Drops rows whose cluster touches a WP1 held-out family. Writes ids, counts and sha256 in `manifest.json`. |
| `retok.py` | Maps G10 markers to existing surrogate special tokens (no new embedding rows), re-tokenises in one batch, rebuilds the mask with `convert.train_spans` + `convert.token_mask`. |
| `train.py` | AdamW, FP32 master weights, loss contract of `train_probe.py` (imported), methods `full`, `lora` (r=4 on q/k/v/o/gate/up/down), `dt` (Deletion Tuning from `../../dt/mask.py`: gate_proj mask logits, hard mask baked for evaluation; `--train-marker-rows` adds the labelled marker-row hybrid, wd must be 0). Step-1 stored-weight writeback check; save + reload parity check. |
| `evaluate.py` | Separate process. Target bits per byte, format validity, execution pass@1 (Docker, `rl-data/stdio_check.py`), forgetting bpb on G5 held-out v1 (G5 `scoring.py`), Team 9 eval-mini (black box). |
| `exec_tasks.py` | stdin/stdout tests for dev/test problems from the pinned human-written sources, accepted only if the statement's family hash matches. |
| `tests/test_bench.py` | 19 tests: marker ids, mask parity with `convert.py` (fixtures, and 50 real rows when `G10_BENCH_SLICE` is set), zero split overlap, held-out guard, eval firewall, loss and gradient equal to `train_probe`, zero-target rejection, target bytes counted once under byte-fallback tokens, writeback check, CPU determinism of two seeded runs, LoRA trains adapters only, DT end-to-end (logits only, base-or-zero weights, mask artefact), marker hybrid moves only marker rows, format judge. |

## Marker table (SmolLM2-135M)

| G10 marker | surrogate surface | id |
|---|---|---|
| `<\|endoftext\|>` | `<\|endoftext\|>` | 0 |
| `<\|im_start\|>` | `<\|im_start\|>` | 1 |
| `<\|im_end\|>` | `<\|im_end\|>` | 2 |
| `<\|think\|>` | `<jupyter_script>` | 15 |
| `<\|/think\|>` | `<empty_output>` | 16 |
| tool markers (4) | not mapped; rows with them are rejected | - |

Ids 15 and 16 are existing specials whose embedding rows have the same norm (3.308) as the other untrained-looking
specials (1, 2, 5, 7-16); ids 0, 3, 4, 6 differ. A row whose content already contains any surrogate special surface is
rejected, so every special id in a sequence is a G10 marker. The final `<|endoftext|>` is never a target (the G10 mask policy).

## Commands

```
B=teams/10-post-training/sft/bench
python $B/slice.py --shard-dir <run>/shards/shard-00000 ... --clusters family_clusters.json \
    --heldout-ids heldout_eval_v1_ids.PRIVATE.jsonl --tokenizer <smollm2>/tokenizer.json --out-dir <slice> --fractions 0.70,0.10,0.20
python $B/exec_tasks.py --split-file <slice>/test.tok.jsonl --sources-root <root with sources/> --out <slice>/test.exec.jsonl
python $B/train.py --train <slice>/train.tok.jsonl --model <base dir> --revision none --method full --steps 400 \
    --lr 1e-4 --seed 1 --device cuda --autocast bf16 --micro-tokens 8192 --out <run>
python $B/evaluate.py --model <run>/model --split-file <slice>/test.tok.jsonl --metrics bpb,format,forget \
    --gen-batch 56 --token-budget 16384 --generations-out <gens> --out <report>
python $B/evaluate.py --score-exec --generations <gens> --exec-tasks <slice>/test.exec.jsonl --out <exec report>
python $B/evaluate.py --eval-mini --model <run>/model --eval-mini-python <team9 venv>/bin/python --device cpu --out <report>
G10_BENCH_SLICE=<slice> python -m pytest $B/tests -q
```

On Apple MPS use `--device mps --micro-tokens 2048 --grad-checkpointing` and set `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7
PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5`; it trains in FP32 at about 15 s per update on an M1 Pro 16 GB (measured over 6 steps).
Slices, generations, checkpoints and exec tasks hold training or evaluation data: keep them out of Git.
