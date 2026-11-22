# Job request: E9 at SmolLM2-1.7B base, does RL have a signal after SFT

```
Team:            10-post-training
Owner:           f20201351h-maker
Lead approval:   saitej123 (confirmed, 21 Nov 2026; merged via #681)
Question:        At 1.7B, after full SFT on execution-verified code (short code-only answers vs full reasoning traces), does the share of easiest-rung RL prompts with a mixed (gradient-carrying) group of 8 samples reach 10%? (It did not at 135M and 360M: 3.1% and 6.3%.)
Script:          teams/10-post-training/rl-loop/pilots/recipe_e9_20261116/recipe_job.py at this PR's head; it calls sft/bench/train.py, rl_screen.py and evaluate.py, rl-loop/score_pool.py, rl-data/stdio_check.py and rl/verifier.py from the same commit (all in this PR or on main)
Command:         python teams/10-post-training/rl-loop/pilots/recipe_e9_20261116/recipe_job.py --config teams/10-post-training/rl-loop/pilots/recipe_e9_20261116/cfg_e9_17b.yaml
Config:          teams/10-post-training/rl-loop/pilots/recipe_e9_20261116/cfg_e9_17b.yaml
Seed:            1 (sampling and SFT row order)
Inputs:          pinned by sha256 in the table below, placed under ./inputs/ by TSAI: HuggingFaceTB/SmolLM2-1.7B @ effd688a12921b4cc83e3312b6feb579f70f9c71 (Apache-2.0) as inputs/SmolLM2-1.7B-effd688a, and inputs/g10-e9/ (five files, 92.5 MB)
Packages:        Python 3.12, torch (CUDA build), transformers, tokenizers, numpy, pyyaml, safetensors; Docker for the code verifier (or Linux root with `stdio_runner: local`). CPU log used the versions of the Mac environment named in the log header
Hardware:        1 GPU, A100 or H100 with 40 GB or more (full fine-tune of 1.7B with fp32 AdamW state needs ~27 GB + activations)
Max time:        150 minutes, enforced by TSAI's job runner (estimate below: about 95 min; the A4 arm runs first, so a timeout still returns a finished result)
Precision:       training fp32 weights / gradients / AdamW state with bf16 autocast; sampling bf16 on the A100 (fp32 on every smaller run; fp16 is not used: it produced non-finite probabilities on the 360M checkpoint)
Measures:        per arm: closed-turn, code-block, parses, runs, pass shares with 95% intervals over problems; failure reasons; mixed-group share; pass@8; forgetting bpb on G5 held-out v1; step time; peak memory
Expected result: A2v2 mixed share 10-25%, pass 3-8%; A4 mixed share at least A2v2's with far fewer tokens; A4 forgetting above 0.05 (135M and 360M values are in `results/e9_sft_before_rl.md` of PR saitej123/era-v5-lab#107)
Outputs:         out/e9/e9_summary.json (rewritten after every finished arm: a partial report after a timeout holds the finished arms) and, per arm in out/e9/{A4,A2v2}/: train_report.json, screen/screen_report.json, forget.json; writes only under out/; under 50 MB without screen/generations.jsonl (model text, keep private) and the saved model folders (about 3.4 GB per arm: delete them, they are not results)
Test log:        teams/10-post-training/jobs/2026-11-17-e9-sft-before-rl-1.7b.log (CPU, same script and config shape from a clean git archive of commit 0a0e0c93, which holds every script and test of this PR; the PR's later commit adds only this request and the log)
```

Why 1.7B (results so far, SmolLM2 base, rung 1, 128 problems x 8 samples, one seed):

| size, code SFT | new tokens | code block | program runs | pass | mixed groups |
|---|---|---|---|---|---|
| 135M full traces | 1,024 | 8.6% | 1.9% | 0 | 0/128 |
| 135M full traces | 2,048 (60 problems) | 55% | 10.8% | 0.2% | 1/60 |
| 135M short answers | 1,024 | 99% | 35% | 0.4% | 4/128 = 3.1% |
| 360M full traces, full FT | 2,048 | 62% | 28% | 1.0% (strict 9/10) | 8/128 = 6.3% [2.3, 10.9] |
| 360M full traces, LoRA r4 + marker rows | 2,048 | 54% | 18% | 0.6% | 4/128 = 3.1% |

The mixed share grows with size and has not crossed 10% at 360M. 1.7B is the first size where it plausibly does, and it is
too large for full fine-tuning on our free hardware (2x T4). Passes were re-checked on 80 unused source tests ("strict").

Time estimate (an estimate; every rate below is measured on a Kaggle T4, none on an A100). The 360M screen first took 15,690 s
(106.8 tokens/s). The cause was the decode attention of grouped-query models (K and V repeated three times per step, a step costing
about 7 ms per row at a 1,500-token context in fp32 and fp16 alike). With a grouped decode attention and a loop that drops finished
rows (`rl_screen.py`, own sampler that draws random numbers over all rows, so its sampled texts equal HF `generate`'s: 256 of 256
rows identical on the same 32 prompts x 8, seed 1) the same screen runs at 415.6 tokens/s (3.9x), 1,036 s against 4,006 s for the
32 prompts; full tables and paired intervals in draft PR saitej123/era-v5-lab#107 (`results/e9_sft_before_rl.md`). SmolLM2-1.7B has 32 KV heads (no grouping), so the grouped attention does
not apply and the job keeps stock attention with the own loop. Measured directly on one T4 (SmolLM2-1.7B base, fp16, own loop,
8 prompts x 8 samples, KV 8 GB, 16 rows per batch): 81,352 tokens in 476 s = 170.9 tokens/s, peak 7.9 GB.
Screen size: 160 prompts (128 rung-1 + 32 rest) x 8 samples x about 1,636 new tokens (the 360M measured mean; the 1.7B SFT model's
length is an assumption) = about 2.09 M tokens for A2v2; A4 about 1/15 of that (mean 93 vs 1,636 tokens per sample on 135M and 360M).
On a T4 the A2v2 screen would take 2.09 M / 171 = about 12,200 s (3.4 h). On one A100 the rate is not measured: taking 3x the T4 rate
(conservative: the T4-to-A100 bandwidth ratio is 6x, but a decode step also has a launch floor) gives 4,070 s = 68 min; 6x gives 34 min.
Training: 135M took 14 s per update on an M1 Pro (fp32 MPS); 1.7B has 12.6x the FLOPs and an A100 with bf16 autocast is about 60x the
M1's throughput: about 3 s per update, about 8 min per arm for 150 updates (scaled from the Mac, not measured on a GPU). Forgetting
about 3 min per arm. Order: A4 first (8 + 5 + 3 = about 16 min), then A2v2 (8 + 68 + 3 = about 79 min): about 95 min in all, Max time 150.

If the time limit hits: `out/e9/e9_summary.json` is rewritten after each finished arm (`complete: false`, `arms_requested`). A partial
report therefore holds A4 complete (train_report.json, screen/screen_report.json with the ladder, mixed-group share and failure reasons,
forget.json) and, for A2v2, whatever it had reached: the training log and the resumable state (saved every 10 updates), or, if training
was done, `screen/generations.jsonl` with the batches already generated (a rerun with the same command resumes per batch; the screen
report is written only when the screen finishes). Arms not reached have no folder. A rerun in the same `out/` continues from the
done-markers.

## Pinned inputs

TSAI places these files under `./inputs/` (the way the other teams' job files stage their inputs by sha256); the model is public
(Apache-2.0) and is fetched at the pinned revision. The data files hold task text and tokenized training rows from admitted sources
(OCR-2 execution-verified solutions, RL data v1 code tasks) and stay out of the repository: they go to TSAI as a private bundle
(a private Kaggle dataset shared with TSAI's account, or a file link, whichever TSAI prefers). Check with `shasum -a 256`.

| Path under `./inputs/` | What | bytes | sha256 |
|---|---|---|---|
| `g10-e9/ocr2_clean_v2.tok.jsonl` | arm A2v2 rows: 1,501 OCR-2 slice rows with the 72 family-overlap rows removed | 26,777,167 | `fbebcaac612e9831a183a828a0741e0e39cb563167c5c6a3603feba0aa867d3c` |
| `g10-e9/ocr2_short_v2.tok.jsonl` | arm A4 rows: the same 1,501 with the reasoning block removed | 9,593,065 | `f9eaa57038285ef0b856cd931ee05829fdb312f281cba2aae2532e46760a0cbe` |
| `g10-e9/cc.jsonl` | RL data v1 code records, restricted to the 882 tasks the screens use | 56,119,180 | `fde089d6265bccc83c895e6a3e399ad43dd6b83825c01c02e0260d6dfe9014ba` |
| `g10-e9/rung1_s128_ids.txt` | the 128 rung-1 screen ids | 3,750 | `37fcc2fe84d3a70afdac6c549db93c8f7ba713c91bc40487a7687254ac805557` |
| `g10-e9/rest_s32_ids.txt` | the 32 rest-sample ids | 997 | `1db0465c075a67f25364ca53ba0c57faa6b671d460b05221435016f7c10a90d1` |
| `SmolLM2-1.7B-effd688a/model.safetensors` | HuggingFaceTB/SmolLM2-1.7B @ effd688a | 3,422,777,952 | `1193528982f4ac0c0b707ce36fd7dc03a0ef6f3e1a432deb886dce2e90c300c0` |
| `SmolLM2-1.7B-effd688a/tokenizer.json` | same revision | 2,104,556 | `9ca9acddb6525a194ec8ac7a87f24fbba7232a9a15ffa1af0c1224fcd888e47c` |
| `SmolLM2-1.7B-effd688a/config.json` | same revision | 635 | `33397f6af8090f7290f27ce6fb1cd23a95fd0915a5c648dfd10b6002aaf7fc48` |
| `SmolLM2-1.7B-effd688a/generation_config.json` | same revision | 111 | `2056c988e990b0d13670f63f2f3b87b3b6d07edaf7a3416998ba27dab2d8a059` |
| `SmolLM2-1.7B-effd688a/vocab.json` | same revision | 800,662 | `82b84012e3add4d01d12ba14442026e49b8cbbaead1f79ecf3d919784f82dc79` |
| `SmolLM2-1.7B-effd688a/merges.txt` | same revision | 466,391 | `0b54e8aa4e53d5383e2e4bc635a56b43f9647f7b13832d5d9ecd8f82dac4f510` |
| `SmolLM2-1.7B-effd688a/special_tokens_map.json` | same revision | 831 | `e786b595b9a23148bf1630df78d9037a048ea671e48bfd3549a1e3c233742bb3` |
| `SmolLM2-1.7B-effd688a/tokenizer_config.json` | same revision | 3,658 | `4bb9af56a342753d39374f4016a16574cab299fe088e896f425ce3c433f61424` |

The forgetting metric reads the held-out file that is already in the repository (`teams/05-architecture/heldout_v1`).

The script runs offline (model and data staged as inputs) and writes only to `out/`. Programs run in Docker
(`stdio_runner: docker`) or, without Docker on Linux as root, with `stdio_runner: local`; the expected outputs never reach
the program. Training state is saved every 10 updates (`--save-every`), so a killed job resumes with the same command.
Test log: the same script and config shape on a Mac CPU with `dry_run: true` (SmolLM2-135M, tiny sizes, arms A4 then A2v2, fp32), 52 s, exit 0.
It proves the commands, the files, the arm order and the summary written after each arm. It does not prove the 1.7B numbers (time, memory,
the bf16 autocast path or the A100 sampling rate), the forgetting step (`forget` is off in a dry run) or the pass shares: only the T4
measurements above and TSAI's run can. Tests of the touched code: `python -m pytest teams/10-post-training/sft/bench/tests` (35 passed, 2 skipped).
