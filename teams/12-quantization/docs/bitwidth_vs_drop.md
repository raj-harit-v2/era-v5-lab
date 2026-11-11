# Bit width against quality drop (G12)

**Model.** `allenai/OLMoE-1B-7B-0924` @ `6d84c48581ec`. Seven llama.cpp formats, bf16 plus Q8_0 down to Q2_K. Every quantized file keeps `output.weight` at Q8_0 and the router (`ffn_gate_inp`) at F32, so bits per weight is the file average, not the name of the format.

**Demo format: Q4_K_M.** It is the smallest format with no significant task loss, at 4.90 bits per weight and 4.24 GB (3.3× smaller than bf16). The next step, Q3_K_M, is where the paired tests first fail.

## One row per format

Task drops are points versus bf16 on the same questions (format minus bf16), from [`eval_mini/results/RESULTS.md`](../eval_mini/results/RESULTS.md). **Bold** is a paired difference the team treats as a real loss (McNemar p < 0.01, except Q2_K GSM8K at p 0.052). Perplexity ratio is full WikiText-2 test PPL divided by bf16's 7.993 ([`perplexity/runs_ppl.csv`](../perplexity/runs_ppl.csv)). KL is the mean KL from bf16 on 16,384 WikiText-2 tokens ([`quality/kl.csv`](../quality/kl.csv)). Eval time is the eval_mini scoring run. Generation speed is a different machine; see the notes under the table.

| Format | bpw | Size | ARC-C | HellaSwag | MMLU | GSM8K | TruthfulQA-mc2 | PPL ratio | KL | Eval time | Gen |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bf16 | 16.0 | 13.84 GB | | | | | | 1 | | 2695 s | 138 tok/s |
| Q8_0 | 8.51 | 7.36 GB | −0.4 | −0.2 | −0.4 | +2.0 | −0.3 | 1.000 | 0.0013 | 888 s | 207 tok/s |
| Q6_K | 6.60 | 5.71 GB | +0.8 | +0.8 | 0.0 | 0.0 | +0.1 | 1.002 | 0.0038 | 892 s | 179 tok/s |
| Q5_K_M | 5.72 | 4.95 GB | −0.4 | +0.2 | +0.9 | +2.5 | +0.4 | 1.006 | 0.0081 | 1042 s | 49 tok/s |
| Q4_K_M | 4.90 | 4.24 GB | +0.2 | −0.2 | −1.9 | +1.0 | −0.5 | 1.023 | 0.0233 | 986 s | 175 tok/s |
| Q3_K_M | 3.89 | 3.37 GB | −0.2 | −1.2 | **−4.2** | −1.5 | −0.6 | 1.065 | 0.0576 | 954 s | 178 tok/s |
| Q2_K | 2.99 | 2.59 GB | **−7.6** | **−4.5** | **−10.4** | **−5.5** | +1.5 | 1.314 | 0.2336 | 904 s | 195 tok/s |

**Time and machine.**

- **Eval time:** Kaggle 2× Tesla T4, all layers on GPU, 28–29 Oct. llama-cpp-python 0.3.36, GGUFs from llama.cpp b11669. 1,870 questions per format. Source: `eval_time_s` in [`runs/runs.csv`](../runs/runs.csv), which matches `wall_clock_s` in the eval_mini `environment.json` files.
- **Gen:** Apple M3 Max 64GB, Metal, 25 Oct, llama.cpp b10050. This is generation speed, not the scoring time. Q5_K_M's 49 tok/s is machine load that day (its eval took 198 s against 44–66 s for the other formats). A 29 Oct rerun of the same file was 223 tok/s, with Q6_K at 240 and Q4_K_M at 261. Do not rank formats by the 49.
- **PPL ratio** was measured on Kaggle 2×T4, llama.cpp v0.7.0, 25 Oct (bf16 468 s, the quants 125–141 s). bf16 is slower there because the T4 has no native bf16. The same ordering on 16,384 tokens (Apple M5 16GB, 26 Oct) is Q8_0 1.001, Q6_K 1.004, Q5_K_M 1.006, Q4_K_M 1.018, Q3_K_M 1.058, Q2_K 1.285.
- **KL** is the M5 run above, about 23–29 s per quantized format. bf16 was the reference pass and its time was not recorded.

Quantize time is not in the table. On the M3 Max it was Q8_0 11 s, Q6_K 25 s, Q5_K_M 58 s, Q4_K_M 50 s, Q3_K_M 25 s, Q2_K 28 s. On the Kaggle perplexity machine (4 CPUs) the same formats took 78–340 s. Either way it is a one-time cost, not a reason to pick a format for the demo.

## Why Q4_K_M

Q8_0 through Q5_K_M match bf16 on every eval_mini task. Q4_K_M does too: its largest drop is MMLU −1.9 (p 0.13), and the confidence interval still includes zero. Q3_K_M is the first format with a measured loss, MMLU −4.2 (p 0.004). Q2_K loses ARC-C, HellaSwag, MMLU and GSM8K. TruthfulQA-mc2 does not pick a format; its largest move is +1.5 at Q2_K.

Perplexity and KL, which can see gaps the benchmarks cannot, put Q4_K_M on the near side of the knee. The ratio goes 1.006 → 1.023 → 1.065 from Q5_K_M to Q4_K_M to Q3_K_M, and KL goes 0.008 → 0.023 → 0.058. Q2_K is a different regime (ratio 1.31, KL 0.23, same top-1 only 76%).

Q5_K_M is the closer match to bf16, and the benchmarks cannot separate it from Q4_K_M. It costs 4.95 GB instead of 4.24 GB. For a demo that has to ship one file, that extra 0.7 GB does not buy a task the audience can see.

The code + Indic run (1 Nov, same Kaggle 2×T4, four formats only) agrees. Q4_K_M has no significant paired change. Q3_K_M loses HumanEval+ by −3.7 points (p 0.031): bf16 solved 6 problems that Q3_K_M failed, and Q3_K_M solved none the other way. Indic scores sit near chance for this English-heavy model, so they are not used to choose.

| Format | MMLU-Pro | GSM8K | HumanEval+ | MBPP+ | Eval time | Machine |
|---|---|---|---|---|---|---|
| bf16 | | | | | 5211 s | Kaggle 2×T4 |
| Q8_0 | −0.3 | 0.0 | 0.0 | +0.3 | 2123 s | Kaggle 2×T4 |
| Q4_K_M | −1.0 | −3.0 | −1.8 | −0.5 | 1957 s | Kaggle 2×T4 |
| Q3_K_M | −0.7 | −4.0 | **−3.7** | −1.6 | 1822 s | Kaggle 2×T4 |

Q6_K, Q5_K_M and Q2_K were not run on this set. Drops are points versus bf16. Source: [`eval_code_indic/results/RESULTS.md`](../eval_code_indic/results/RESULTS.md) and the 1 Nov rows of [`runs/runs.csv`](../runs/runs.csv).

**Not the demo format.** Q8_0 is the same quality at 7.36 GB. Q3_K_M and Q2_K are smaller and are the formats that lose tasks.
