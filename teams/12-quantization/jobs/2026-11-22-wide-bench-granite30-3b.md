# Wide benchmark pass on Granite 3.0 3B-A800M (MoE): bf16 against Q8_0, Q4_K_M and Q3_K_M (Gate 4 evidence)

REQUEST FOR TSAI REVIEW. No approval and no run result is claimed. The author is the G12 owner below. SreekanthZipsy, the lead, approves; TSAI runs it. I need the result for Gate 4 evidence, due Fri 27 Nov, 11:59 PM IST.

The MoE half of the wide pass. The Indic half is [2026-11-22-wide-bench-sarvam1.md](2026-11-22-wide-bench-sarvam1.md); scripts, staging, backend and reporting are the same and are described there.

```text
Team:            12-quantization
Owner:           Soma Korada (SomaKorada07)
Lead approval:   SreekanthZipsy
Question:        On full MMLU and ARC-Challenge, how many points do the Q8_0, Q4_K_M and Q3_K_M GGUF files of the Granite 3.0 3B-A800M MoE model lose against its bf16 file on the same items?
Script:          teams/12-quantization/eval_wide/run_job.py (runs llama.cpp's converter, llama-quantize, eval_mini/test_llamacpp_lm.py, eval_wide/run_wide_gguf.py and eval_wide/paired.py)
Command:         python teams/12-quantization/eval_wide/run_job.py --model-dir ./inputs/granite-3.0-3b-a800m-base --hf-home ./inputs/hf_home --llama-dir ./work/llama.cpp-b11669 --convert-python ./work/.venv-convert/bin/python --formats bf16 Q8_0 Q4_K_M Q3_K_M --tasks mmlu arc_challenge --work ./work --out ./out/wide-granite30-3b --model ibm-granite/granite-3.0-3b-a800m-base --revision 142d2c8e3f7fb8844011cfa5565f0e520f0824b9
Config:          none. Every setting is on the command line or is a default of the scripts.
Inputs:          ibm-granite/granite-3.0-3b-a800m-base at 142d2c8e3f7f (Apache-2.0, not gated); lm_eval's MMLU and ai2_arc datasets. Staged once with network by eval_wide/prepare_inputs.py --tasks mmlu arc_challenge; no token needed.
Hardware:        1 GPU (16 GB or more; the bf16 file is about 6.6 GB)
Max time:        360 minutes (ESTIMATE from a T4, see "What I ran before filing")
Precision:       bf16 baseline; Q8_0, Q4_K_M and Q3_K_M weights, router (ffn_gate_inp) F32, output layer Q8_0
Measures:        Per format and task: accuracy (MMLU acc, ARC-C acc_norm), item count, seconds per item, requests truncated at 4,096 tokens. Per quantized format and task, against bf16 on the same items: difference in points, 95% CI, McNemar exact p. Per format: GGUF size and sha256, guard test PASS/FAIL.
Expected result: Guard test PASS on all four files. bf16 near 48% on MMLU (timing run: 47.7% on 1,140 items). Q8_0 within ±1 point of bf16. Q4_K_M 1 to 4 points down: in week 3 the 1B sibling drifted more than OLMoE at Q4_K_M (KL 0.065 against 0.023). Q3_K_M 3 to 8 points down.
Outputs:         ./out/wide-granite30-3b/{job.json, paired.md, runs/<format>/summary.json, runs/<format>/<task>.samples.jsonl, logs/*.log}, about 6 MB in total. No item text (Team 9's firewall). GGUF files go to ./work/; each quantized file is deleted after its format.
Test log:        teams/12-quantization/jobs/evidence/2026-11-22-wide-bench-granite30-3b/ (Kaggle T4 x2: timing run and a smoke of this command)
```

## One run

| Model | Formats | Tasks (items) | Output directory |
|---|---|---|---|
| ibm-granite/granite-3.0-3b-a800m-base @ 142d2c8e3f7f | bf16, Q8_0, Q4_K_M, Q3_K_M | MMLU (14,042), ARC-C (1,172) | ./out/wide-granite30-3b/ |

## Why this model and these tasks

- **An MoE in the family our export targets.** `GraniteMoeForCausalLM` (llama.cpp `granitemoe`): 32 layers, 40 experts with top-8 (about 800 M active of 3.3 B), tied embeddings, 4,096-token context. G12's export of the G5 checkpoint is a Granite MoE Shared model, and week 3 showed the 1B-A400M sibling drifts more than OLMoE at Q4_K_M.
- **Not the 1B-A400M of #643.** In our timing run it scored 27.1% on MMLU (1,140 items, bf16), 2 points above the 25% chance line. Items then flip between formats at random, so a paired test measures noise, not damage. The 3B-A800M scored 47.7% on the same items.
- **English tasks only.** Granite 3.0 is not trained on Indic languages, so MILU would sit near chance for the same reason. sarvam-1's request covers Indic.
- **Items.** Full MMLU is enough to see a 1-point drop, and full ARC-C a 2-point drop (`docs/wide_benchmark_scope.md`).

## Source and staging

As in [the sarvam-1 request](2026-11-22-wide-bench-sarvam1.md#source-and-staging), with this staging command (no `HF_TOKEN`: nothing gated):

`python teams/12-quantization/eval_wide/prepare_inputs.py --tasks mmlu arc_challenge --hf-home ./inputs/hf_home --model-dir ./inputs/granite-3.0-3b-a800m-base --model ibm-granite/granite-3.0-3b-a800m-base --revision 142d2c8e3f7fb8844011cfa5565f0e520f0824b9`

If both jobs run on one machine, `./inputs/hf_home` can be shared: the sarvam-1 staging already holds MMLU and ARC-C.

## What I ran before filing

**Timing run**, Kaggle 2 × Tesla T4, 22 Nov, `eval_wide.ipynb` (same `run_wide_gguf.py`), bf16, 20 items per task (MMLU 20 per subject), MILU left out. Guard test PASS.

| Task | Items | Score | Seconds per item |
|---|---:|---:|---:|
| MMLU | 1,140 | 47.7 | 0.361 |
| ARC-C | 20 | 35.0 | 0.810 |

Full splits from these times: bf16 about 1.7 h on a T4. Using sarvam-1's eval-time ratios for the quantized files (Q8_0 0.67×, Q4_K_M 0.53×, Q3_K_M 0.56×; not measured on this model), about 4.6 h for the four formats, plus about 15 minutes to convert and quantize. 360 minutes leaves about 25% margin.

Files: [timing/](evidence/2026-11-22-wide-bench-granite30-3b/timing/) (`environment.json`, `summary.json`, `scores_long.csv`, and the run, guard-test and convert logs, cut to this model's run: the session ran sarvam-1 and Granite 1B first).

**Guard test change.** Granite's tokenizer splits " Paris" into " Par" + "is", so `test_llamacpp_lm.py` now checks the first token of the answer under the model's own tokenizer. For OLMoE and sarvam-1 " Paris" is one token, so their check is unchanged. Granite 3B, PASS: log p(' Par') −0.930 in scoring, −0.938 in generation, off-by-one value −13.59.

**Prefix cache on this MoE.** The guard's check 3 (scoring with the prefix cache against scoring from scratch) moved a score by 0.043 nats on Granite 3B, close to its 0.05 limit; sarvam-1 (dense) moved 0.0001. A plausible cause is the MoE router: a different batch shape changes the GPU arithmetic slightly, and a near-tie between experts can flip. Scores are computed in the same order for every format, so the paired comparison is like for like, but a quantized file could cross 0.05 and stop the job at its guard test. In the smoke below the guard passed on Q4_K_M as well.

**Smoke of this command** (`--formats bf16 Q4_K_M --cap 2 --tasks mmlu arc_challenge`, offline, empty work folder): PASS, every step exit 0 in 7 minutes, the convert step included (110.7 s) and Q4_K_M quantized in 156.9 s. Details: [smoke_run_job.md](evidence/2026-11-22-wide-bench-granite30-3b/smoke_run_job.md).

## Open items for TSAI

1. **Time.** 360 minutes is a T4 estimate; a faster GPU should need less.
2. **Tools and work folder:** as in the sarvam-1 request (items 3 and 4 there).
