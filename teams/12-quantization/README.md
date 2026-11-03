# Team 12-quantization

Put your work in a **topic folder**: `teams/12-quantization/<topic>/<file>`, for example `teams/12-quantization/harness/run.py`.
Team documents named in the week plan (for example `benchmarks_v1.md`) may sit directly in the team folder. The team lead decides the topic names. Do not make personal folders. Do not make new folders under `teams/`.
Open a pull request; the lead reviews and merges it. The pr-guard check must pass.

## Week 1: OLMoE-1B-7B in six llama.cpp formats

`allenai/OLMoE-1B-7B-0924` @ `6d84c48581ec`, converted to a bf16 GGUF and quantized from Q8_0 down to Q2_K. Every
quantized format keeps `output.weight` at Q8_0, and the router (`ffn_gate_inp`) stays F32. Each format was measured in
three ways:

| Format | Size | ARC-C | HellaSwag | MMLU | GSM8K | TruthfulQA-mc2 | WikiText-2 PPL | KL vs bf16 | Same top-1 |
|---|---|---|---|---|---|---|---|---|---|
| bf16 | 13.84 GB | 46.8 | 66.0 | 53.7 | 10.5 | 37.3 | 7.993 | | |
| Q8_0 | 7.36 GB | 46.4 | 65.8 | 53.3 | 12.5 | 37.0 | 7.994 | 0.0013 | 98.3% |
| Q6_K | 5.71 GB | 47.6 | 66.8 | 53.7 | 10.5 | 37.4 | 8.012 | 0.0038 | 96.8% |
| Q5_K_M | 4.95 GB | 46.4 | 66.2 | 54.6 | 13.0 | 37.7 | 8.039 | 0.0081 | 95.3% |
| Q4_K_M | 4.24 GB | 47.0 | 65.8 | 51.8 | 11.5 | 36.9 | 8.179 | 0.0233 | 92.1% |
| Q3_K_M | 3.37 GB | 46.6 | 64.8 | **49.5** | 9.0 | 36.7 | 8.516 | 0.0576 | 87.9% |
| Q2_K | 2.59 GB | **39.2** | **61.5** | **43.3** | **5.0** | 38.9 | 10.500 | 0.2336 | 76.2% |

Benchmark scores are % correct on G9's eval_mini profile (1,870 questions, about ±2–3 points of standard error each).
**Bold** marks a significant drop compared with bf16 on the same questions: McNemar p < 0.01, except Q2_K GSM8K
(p 0.052). Perplexity is on the full WikiText-2 test set. KL is the mean KL divergence from bf16's next-token
distribution on 16,384 WikiText-2 tokens.

**What it says.** The benchmarks show no measurable loss from Q8_0 to Q4_K_M. The first real drop is Q3_K_M on MMLU
(−4.2 points), and Q2_K breaks broadly. Perplexity and KL rise steadily at every step, so they separate formats that
the benchmarks cannot. Q4_K_M is the smallest format with no significant benchmark loss (3.3× smaller than bf16).

| Folder | What | Detail |
|---|---|---|
| [`eval_mini/`](eval_mini/) | G9's eval_mini on every format, scored in-process with llama-cpp-python; paired comparison with bf16 | [`results/RESULTS.md`](eval_mini/results/RESULTS.md) |
| [`perplexity/`](perplexity/) | WikiText-2 perplexity, llama.cpp v0.7.0 on Kaggle | [`README.md`](perplexity/README.md) |
| [`quality/`](quality/) | KL divergence and same-top-1 against bf16 (`llama-perplexity --kl-divergence`) | [`README.md`](quality/README.md) |
| [`runs/runs.csv`](runs/runs.csv) | one row per format: size, bits per weight, quantize time, generation speed, eval_mini score | notes column |
| [`scripts/quantize_eval.py`](scripts/quantize_eval.py) | makes the GGUFs (output tensor Q8_0) and measures size, quantize time and speed; its own eval is the 25 Oct stand-in, whose scores in runs.csv were replaced by eval_mini | script docstring |
| [`quantize/quantize_olmoe.sh`](quantize/quantize_olmoe.sh) | an alternative recipe (output BF16, down to Q3_K_M); **not** the one measured here | script header |
| [`tools/tools.md`](tools/tools.md) | survey of quantization and serving tools: licences, MoE support | |
| [`tokenizer/gguf_roundtrip.py`](tokenizer/gguf_roundtrip.py) | week 2: does llama.cpp give the same token ids as the HF tokenizer after GGUF conversion? Tokenizer v0: yes with pre-tokenizer `granite-embed-multi-97m` (0 of 22,033 lines differ); `gpt-4o` differs on 14,517 | [`results/gguf_roundtrip_v0.md`](results/gguf_roundtrip_v0.md) |

**Rerun.**
- **Benchmarks:** import `eval_mini/eval_mini.ipynb` into Kaggle (GPU T4 x2, Internet on), set `FORMATS`, then
  Save & Run All. It builds llama.cpp b11669 and llama-cpp-python 0.3.36, converts, quantizes, runs the logprob test,
  then scores.
- **Combine:** `python eval_mini/combine.py eval_mini/results/raw/* --out <dir>` rebuilds the tables from the
  committed per-question rows.
- **Perplexity and KL:** the commands are in each folder's README.

Versions:
- llama.cpp b11669 (= v0.7.0) for conversion and quantizing;
- llama-cpp-python 0.3.36, lm_eval 0.4.13, datasets 5.1.0 and Python 3.13 for eval_mini;
- G9's `run_eval_mini.py` from lab `main`, fixed by its sha256 in every summary.
