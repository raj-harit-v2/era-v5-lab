# Router comparison: CPU smoke of both commands

This is a test log. It is not a bits-per-byte result, not a comparison of the two arms, and not a speed measurement.

## What was run

- Source: `train_week2.py` on branch `g5-w4-optimizer-split` at `803ccbf` (lab main `baa8d17` plus #706, which adds `optim.router_on_muon`).
- Machine: Windows laptop, CPU only, Python 3.12.10, PyTorch 2.13.0+cpu, fp32.
- Arms: `configs/arms/router/router_muon.yaml` and `router_adamw.yaml`, full T2 size (237,052,416 parameters); only the context (160), batch (1) and steps (6) are small.
- Inputs: tokenizer v0 and the matching P32 raw table, with synthetic text, from `jobs/evidence/2026-11-15-rotation-attn4-seed1239/inputs/` (the same files as the earlier rotation smokes; not re-committed). The real job uses frozen p1536 (see the request).
- `check_week2.py` on both arms: "Runtime specification valid".

## Command (run from the repository root)

```text
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/router/router_muon.yaml --runtime teams/05-architecture/configs/runtime.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/synthetic_train.jsonl --heldout-data ./inputs/synthetic_heldout.jsonl --device cpu --seed 1234 --smoke --smoke-steps 6 --smoke-seq-len 160 --smoke-batch-size 1 --no-checkpoint --out ./out/router-muon
```

The same with `router_adamw.yaml` and `--out ./out/router-adamw`, run twice.

## Results

| | router_muon | router_adamw (run 1) | router_adamw (run 2) |
|---|---|---|---|
| Exit code, status | 0, SMOKE | 0, SMOKE | 0, SMOKE |
| Training wall seconds | 43.3 | 41.4 | 41.7 |
| manifest `router_on_muon` | true | false | false |
| manifest `muon_parameters` | 165,740,544 | 165,675,008 | 165,675,008 |
| manifest `adamw_parameters` | 71,311,872 | 71,377,408 | 71,377,408 |
| Train CE, steps 1 to 6 | 12.185, 11.544, 10.662, 9.878, 8.932, 8.174 | 12.185, 11.545, 10.652, 9.862, 8.921, 8.209 | identical to run 1 |
| Synthetic held-out BPB, step 0 → 6 | 2.7657 → 1.7997 | 2.7657 → 1.7963 | identical to run 1 |
| `final_model_sha256` | `f92eb3f4…` | `770a940f…` | `770a940f…` |

- The switch does what it says: the Muon count differs by 65,536, the router weights at T2 (8 layers × 16 experts × 512), the same number as Team 7's updated layout pin in #706.
- Same seed and same command give the same model: `router_adamw` twice, byte-identical `losses.txt`, same `final_model_sha256`.
- All losses finite. Step 1 is identical in both arms (same initial weights); they part from step 2 on, as expected once the router is updated differently.
- `manifest.json`, `summary.json` and `losses.txt` of `router_muon` and of `router_adamw` run 1 are in the two subfolders.
