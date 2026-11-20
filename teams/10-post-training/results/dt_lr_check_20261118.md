# DT learning rate check: official 5e-4 against our 2e-3 (`SmolLM2-135M`, 18 Nov 2026)

**Verdict (one seed): at the official lr 5e-4, DT has lower raw drift than full fine-tuning (+0.0207 against +0.0508) but also fits the task less (test bpb 0.5484 against 0.4836), and is worse than LoRA and full FT on task bpb. These rows are not at equal fit; for the equal-fit comparison see section 7 of `dt_vs_fft.md`, which finds that DT does not forget less than full FT.**

Question from the 17 Nov port check: SFT DT used lr 2e-3, the official `deleting-weights` script uses 5e-4 (constant lr, AdamW, 400 steps, alpha 100 to 1000, lambda 1e-5). Does the lr change the DT row of section 1?

## Setup
`SmolLM2-135M`, OCR-2 `slice-v1` (train 2,509 rows; test 300 rows / 110 clusters), seed 1, 400 steps x 8 rows, `gate_proj` masks only, alpha 100->1000, `eta=1/2048`, lambda 1e-5 decaying, warmup 20 + cosine to 0.1x, AdamW 0.9/0.95, clip 1, `--grad-checkpointing`. Only lr differs between arms.
Both arms trained on a Mac (Apple M1 Pro, MPS, fp32, `--micro-tokens 4096` instead of the A10 runs' 8192 to avoid memory swap; same update, different accumulation chunks). Both evaluated on CPU fp32 with the unchanged `sft/bench/evaluate.py` (`--metrics bpb,forget --token-budget 16384 --device cpu`), together with the saved A10 2e-3 model as a control for the evaluator.
Command shape: `python sft/bench/train.py --method dt --steps 400 --lr <lr> --seed 1 --device mps --micro-tokens 4096 --grad-checkpointing ...`, then `python sft/bench/evaluate.py --model <model> --split-file test.tok.jsonl --metrics bpb,forget --token-budget 16384 --device cpu`.

## Result (test split; drift = held-out v1 bpb minus base 1.0981)
| Row | lr | Test target bpb | Held-out drift | Deleted share, gate weights (end) |
| --- | ---: | ---: | ---: | ---: |
| DT, Mac-trained | 5e-4 (official) | 0.5484 | +0.0207 | 2.019% |
| DT, Mac-trained | 2e-3 (ours) | 0.5323 | +0.0287 | 3.214% |
| DT, saved A10 model, evaluated here | 2e-3 | 0.5321 | +0.0279 | 3.22% |
| Full FT (section 1, 3 seeds) | 1e-4 | 0.4836 | +0.0508 | - |
| LoRA r=4 (section 1) | 1e-3 | 0.5283 | +0.0384 | - |
Dev bpb is the earlier A10 sweep (not re-measured): 3e-4 0.5728, 5e-4 0.5545, 1e-3 0.5413, 2e-3 0.5386 (full FT 0.4913, LoRA 0.5355).

- Raw drift at 5e-4 is 0.030 below full FT's (not at equal fit); test bpb at 5e-4 is 0.020 above LoRA's and 0.065 above full FT's.
- 5e-4 against 2e-3 on the same machine: test bpb 0.0161 worse, drift 0.0080 smaller, 1.2 points less of the gate weights deleted: a trade-off along lr, not a change of ordering.

## Checks
- Mac-trained 2e-3 against the saved A10 2e-3 run: test bpb 0.5323 against 0.5321, drift +0.0287 against +0.0279, deleted share 3.214% against 3.22%, final training loss 1.1989 against 1.1989. The 5e-4 arm matches its A10 run likewise (final loss 1.2308 against 1.2314, deleted 2.019% against 2.02%). Hardware, fp32 and chunking moved the run by about 0.001 bpb.
- The saved A10 2e-3 model scored by this CPU evaluator reproduces its section 1 numbers (0.5321, +0.0279).
- MPS evaluation was discarded: its forgetting path crashes (float64) and its dev bpb was wrong on a model whose A10 score is known (0.91 against 0.5386).

## Not measured, and what does not transfer
One seed (differences under about 0.003 are not separated; the ones above are larger). Generation format (0/110 for pure DT) and exec pass rate were not re-run. 135M dense, one code slice, AdamW, fp32: this says what lr does to the surrogate's DT row, not what it does on the capstone MoE with Muon.
