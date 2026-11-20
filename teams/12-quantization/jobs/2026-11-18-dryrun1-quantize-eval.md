# Dry run 1 checkpoint: quantize, score and 100 fixed prompts (Gate 3 evidence)

DRAFT, to be sent on Wed 18 Nov. The checkpoint is the dry run 1 run folder that TSAI kept (#475, `./out/dryrun1-1234`:
`checkpoint.pt`, `manifest.json`, `summary.json`). It was trained with the frozen p1536 tokenizer (TSAI's result comment
on #475, 16 Nov). The export reads the model settings from the run folder's `manifest.json`, so no `--spec` is needed.

```
Team:            12-quantization
Owner:           Rahul Bhati (therahulbhati), Shubham Saxena (s9k96)
Lead approval:   SreekanthZipsy
Question:        Does the G12 flow take the dry run 1 checkpoint to bf16, Q8_0 and Q4_K_M GGUF files with no manual step, and how far do Q8_0 and Q4_K_M move from bf16 in score and on 100 fixed prompts?
Script:          teams/12-quantization/scripts/quantize_eval.py, then teams/12-quantization/scripts/flow_fixed_prompts.py (with export_hf.py, check_gguf_logits.py, tokenizer/gguf_roundtrip.py and Team 10's eval/effort_suite.py)
Command:         python teams/12-quantization/scripts/quantize_eval.py --checkpoint inputs/dryrun1-1234 --tokenizer inputs/tokenizer.json --tokenizer-sha256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b --formats bf16,Q8_0,Q4_K_M --roundtrip --work out/work --runs-csv out/runs.csv --scores-out out/scores.json && python teams/12-quantization/scripts/flow_fixed_prompts.py --gguf-dir out/work --formats Q8_0,Q4_K_M --manifest teams/10-post-training/eval/effort_manifest.json --source-dir code_contests=inputs/code_contests --source-dir hendrycks_math=inputs/hendrycks_math --scores out/scores.json --out out/prompts --delete-ggufs
Config:          none (every setting is on the command line)
Inputs:          see "Inputs and pins" below
Hardware:        1 GPU
Max time:        60 minutes (ESTIMATE: the random 10M-parameter test took 6.5 min on an Apple M1, most of it package installs; dry run 1 is about 300M parameters)
Precision:       bf16 (baseline), Q8_0 and Q4_K_M weights; router F32, output Q8_0
Measures:        A1 (export logits vs G5's model), A3 (llama.cpp vs G5), round-trip exit code; per format: size, bpw, router/output type, score, eval time, tok/s; on the 100 prompts per format: finish reasons, tok/s, outputs identical to bf16, mean shared prefix with bf16
Expected result: A1 and A3 PASS; round trip exit 1 or 2 (known limits of the GGUF tokenizer, #467); Q8_0 within noise of bf16 and close to bf16 on the prompts; Q4_K_M within about 2 points. No score level is assumed for a 1,221-step model.
Outputs:         out/runs.csv, out/scores.json, out/work/*-roundtrip/*.md, out/work/*.json, out/prompts/summary.json, out/prompts/prompts_<format>.jsonl (ids and sha256s; output token ids and text only for our own prompts), logs. GGUF files deleted at the end.
Test log:        teams/12-quantization/jobs/2026-11-15-flow-random-checkpoint.log (own machine, random G5 checkpoint, public BrahmicTokenizer-131K)
```

## Inputs and pins

| Input | Where TSAI gets it | Pin |
|---|---|---|
| Run folder `inputs/dryrun1-1234/` | #475 output, kept by TSAI | `summary.json` `final_model_sha256` |
| Tokenizer `inputs/tokenizer.json` | p1536, the one dry run 1 used (`teams/03-tokenizer/release/`) | sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` |
| `inputs/code_contests/` | `deepmind/code_contests` @ `802411c3010c`, the 24 `train-*.parquet` files the manifest names (about 4.6 GB) | each file's sha256 in `effort_manifest.json`, checked by `effort_suite.py` |
| `inputs/hendrycks_math/` | `EleutherAI/hendrycks_math` @ `21a5633873b6`, the 7 `<subject>/train-*.parquet` files (3 MB) | as above |
| 100 prompts | Team 10's `eval/effort_manifest.json` (in the repo): 30 code and 25 math slots from the files above; its 45 unavailable slots (20 tool, 15 Indic, 10 general) filled from our `prompts/fixed_100.jsonl` | manifest `d6190b2d…`, `fixed_100.sha256` |
| llama.cpp | b11669 binaries (`llama-quantize`, `llama-server`) | build number checked by the script |

Team 10's prompt texts and the model's answers to them (as text or token ids) are not written to `out/`, only ids and sha256s.

## Test run (15 Nov, Apple M1 8 GB, Metal, llama.cpp b11669)

Random G5 checkpoint from `scripts/make_random_checkpoint.py` (2 layers, width 64, 16 + 1 experts, 131,072 ids,
9.8M parameters), public BrahmicTokenizer-131K (`01d968a7…`), stand-in eval limited to 20 items. Exit 0.

| Step | Result |
|---|---|
| A1 export | max logit difference 1.67e-06, same top-1 on 4,096 of 4,096 positions: PASS |
| A3 llama.cpp vs G5 | same top-1 on 16 of 16 prompts, max log-probability difference 0.0076: PASS |
| Round trip | 0 lines with different ids; 16 single tokens wrong in the whole-vocabulary check: exit 1 |
| bf16 / Q8_0 / Q4_K_M | built, router F32 and output Q8_0 checked, scored (score 0: random weights) |

## Open before sending

1. **No network in a job (JOB_REQUEST.md rule 1).** `quantize_eval.py` downloads at run time: the llama.cpp checkout,
   the converter venv (`uv pip install`), llama-cpp-python and `datasets` for the round trip, the held-out text for the
   round trip and the stand-in eval. Either TSAI's machine has these, or `inputs/` carries them (a prepared `--work`
   folder with `llama.cpp-b11669/`, `heldout/lines.json` and the eval file). The work folder also holds the converter
   venv and the exported model, so it should not count toward the 50 MB of `out/`. To agree with TSAI.
2. **Eval set for the scores.** `quantize_eval.py` scores its own items file (default: the 25 Oct stand-in). Decide
   whether to pass G9's eval-mini items with `--eval` instead, so the numbers can be compared with week 2.
