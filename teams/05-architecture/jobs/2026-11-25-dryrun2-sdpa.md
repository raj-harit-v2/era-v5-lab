# Dry run 2 SDPA arm: loss + held-out bpb A/B beside eager (#720)

REQUEST FOR TSAI REVIEW. Tip [#97](https://github.com/vaibh27/era-v5-lab/pull/97) MERGED. Class twin lands opt-in `dryrun2_sdpa.yaml`. This is **not** a re-queue of #720 (`dryrun2-1234` / eager).

```text
Team:            05-architecture / 06-performance (G6 WO2)
Owner:           Raj H (raj-harit-v2)
Lead approval:   raj-harit-v2
Question:        Beside eager dryrun2-1234 (#720), does dryrun2_sdpa.yaml finish 1,221 steps with finite loss, and how do training loss and held-out val/bpb compare to the eager arm (G5 A/B for a possible main-run SDPA default)?
Script:          teams/05-architecture/harness/train_week2.py (same as #720). Requires class land of tip #97 (opt-in SDPA + dryrun2_sdpa.yaml) on lab main first.
Command:         PYTHONPATH=teams/07-infrastructure python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/dryrun2_sdpa.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer-release frozen-p1536 --tokenizer ./inputs/tokenizer_p1536.json --byte-table teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout_v1.jsonl --heldout-sources ./inputs/heldout_v1_sources.jsonl --heldout-sha256 ./inputs/heldout_v1.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --seed 1234 --run-id dryrun2-sdpa-1234 --checkpoint-store /shared/ckpt --checkpoint-interval-s 600 --checkpoint-at-start --expert-load-every 50 --out ./out/dryrun2-sdpa-1234
Config:          teams/05-architecture/configs/arms/dryrun2_sdpa.yaml (inherits dryrun2.yaml + model.attn_impl: sdpa). Eager dryrun2.yaml is unchanged.
Inputs:          Same staged inputs as #720 / 2026-11-22-dryrun2.md. This request does not rename shards.
Hardware:        1 GPU with native bf16 support
Max time:        90 minutes (T2 cap in runtime.yaml)
Precision:       bf16
Measures:        Training loss and grad norm each step; step time and tokens/s; held-out val/bpb (and related held-out metrics) at each eval step; MoE expert_load every 50 steps; completed steps; wall time; final_model_sha256. Compare loss + held-out val/bpb to eager #720 when that result exists.
Expected result: 1,221 completed steps with no NaN and no inf. No bits-per-byte value is assumed. Fewer than 1,221 steps is INCOMPLETE_NOT_A_RESULT. A NaN or an inf voids the run.
Outputs:         ./out/dryrun2-sdpa-1234/{manifest.json,summary.json,metrics.jsonl,losses.txt,total_losses.txt}, 50 MB or less in total. Checkpoint stays on the job machine.
Test log:        none. No smoke result is claimed.
```

## One run

| Arm | Config | Seed | Steps | Output directory |
|---|---|---:|---:|---|
| dryrun2-sdpa | dryrun2_sdpa.yaml | 1234 | 1,221 | ./out/dryrun2-sdpa-1234/ |

One job, one command. Not a flip of `dryrun2.yaml`. G5 ACK: DR2 stays eager; SDPA stays opt-in until loss + held-out bpb A/B is within noise (band TBD after this run).

## Pins

| Item | Value |
| :--- | :--- |
| Tip | [#97](https://github.com/vaibh27/era-v5-lab/pull/97) MERGED (`a1d364dc`) |
| Eager reference job | class [#720](https://github.com/theschoolofai/era-v5-lab/pull/720) / run id `dryrun2-1234` |
| Modal speed-only (not this job) | tip `speed_dryrun2.md` ~1.049× / −1.5 GB |

## Notes

- Do **not** re-queue #720 for SDPA. New run id `dryrun2-sdpa-1234`.
- Queue only after the class opt-in PR that adds `dryrun2_sdpa.yaml` is on `main`.
- Ask G5 for a “within noise” band only after this A/B returns (main-run default decision).
