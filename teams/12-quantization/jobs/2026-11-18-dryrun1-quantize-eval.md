# Dry run 1 checkpoint: quantize, score and 100 fixed prompts (Gate 3 evidence)

REQUEST FOR TSAI REVIEW. No approval and no run result is claimed. The authors are the G12 owners below. SreekanthZipsy, the lead, approves; TSAI runs it. I need the run for Gate 3 evidence, due Fri 20 Nov.

```text
Team:            12-quantization
Owner:           therahulbhati, s9k96
Lead approval:   SreekanthZipsy
Question:        Does the G12 flow take the dry run 1 checkpoint to bf16, Q8_0 and Q4_K_M GGUF files with no manual step, and how far do Q8_0 and Q4_K_M move from bf16 in score and on 100 fixed prompts?
Script:          teams/12-quantization/scripts/run_flow.py (it runs quantize_eval.py, then flow_fixed_prompts.py), with export_hf.py, check_gguf_logits.py, tokenizer/convert_frozen.py and Team 10's eval/effort_suite.py
Command:         python teams/12-quantization/scripts/run_flow.py --checkpoint ./out/dryrun1-1234 --tokenizer ./inputs/tokenizer.json --eval teams/12-quantization/prompts/eval_own_20.json --work ./work --out ./out/dryrun1-g12 --manifest teams/10-post-training/eval/effort_manifest.json --source-dir code_contests=./inputs/code_contests --source-dir hendrycks_math=./inputs/hendrycks_math
Config:          none. Every setting is on the command line or is a default of the scripts.
Inputs:          the dry run 1 run folder, the frozen p1536 tokenizer (sha256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b), the two Team 10 parquet sets, and a prepared work folder. See "Source and staging".
Hardware:        1 GPU
Max time:        60 minutes (ESTIMATE, see "What I ran before filing")
Precision:       bf16 baseline; Q8_0 and Q4_K_M weights, router F32, output layer Q8_0
Measures:        Export test A1 (exported model against G5's model) and test A3 (llama.cpp against G5's model). Per format: size, bits per weight, score on 20 items, eval time, tokens per second. On the 100 prompts per format: finish reasons, tokens per second, outputs identical to bf16 and mean shared prefix with bf16, reported separately for Team 10's 55 slots and our 45 fill slots.
Expected result: A1 and A3 PASS. Q8_0 close to bf16 on the prompts and the score. Q4_K_M further away. No score level is assumed: the model has 1,221 steps of training and the 20 items are easy.
Outputs:         ./out/dryrun1-g12/{runs.csv,scores.json,manifest_<date>.json,prompts/summary.json,prompts/prompts_<format>.jsonl}, 50 MB or less (the smoke wrote 0.7 MB). GGUF files are deleted at the end.
Test log:        teams/12-quantization/jobs/evidence/2026-11-18-dryrun1-quantize-eval/smoke.md
```

## One run

| Model | Formats | Prompts | Output directory |
|---|---|---:|---|
| dry run 1, exp2_muon, frozen p1536, seed 1234 | bf16, Q8_0, Q4_K_M | 100 | ./out/dryrun1-g12/ |

One job, one command. There is no shell pipe. `run_flow.py` runs `quantize_eval.py` and then `flow_fixed_prompts.py` and stops at the first non-zero exit code.

## Where each setting comes from

| Setting | Value in this job | Source |
|---|---|---|
| Checkpoint | `./out/dryrun1-1234/` | The dry run 1 run folder (#475, finished 16 Nov, TSAI's result comment). ASSUMPTION, see below. |
| Model settings | read from the run folder's `manifest.json` (`config.model`) | `export_hf.py`. No `--spec` is needed. |
| Tokenizer | frozen p1536, `./inputs/tokenizer.json` | `teams/03-tokenizer/release/SHA256SUMS`. The command's default sha256 is this one, and the script refuses any other file. |
| llama.cpp | b11669 binaries and checkout | #467. The converter needs a forced pre-tokenizer (`granite-embed-multi-97m`); the stock converter stops on this vocabulary. |
| Formats | bf16, Q8_0, Q4_K_M | G12 choice: the bf16 baseline and the two formats the question names. |
| Router and output layer | router F32, output layer Q8_0 | `quantize_eval.py` defaults. |
| Items for the score | `prompts/eval_own_20.json`, sha256 `5d4fec16221c3d2dd1aa2695f6f6ded97d5a493afd460bf7f927e19e36fbb069` | G12 choice, see "How the run is scored". |
| 100 prompts | Team 10's `eval/effort_manifest.json` (30 code and 25 math slots) plus 45 of ours | Team 10 (answer in the G12 channel): the 45 unresolved slots stay unresolved, we fill them from `prompts/fixed_100.jsonl` and report the two groups separately. |
| Decoding | greedy (temperature 0, top_k 1), seed 0, 128 new tokens, context 2,048 | `flow_fixed_prompts.py` defaults. |

## Source and staging

- Start from `theschoolofai/era-v5-lab` main with the PR that carries this file merged. `run_flow.py`, `prompts/eval_own_20.json` and the offline change to `quantize_eval.py` are in it.
- Run folder: `./out/dryrun1-1234/` with `checkpoint.pt` (about 2.2 GB with the optimizer state), `manifest.json` and `summary.json`. TSAI keeps it. Check `final_model_sha256` in its `summary.json`; the script records the sha256 of `checkpoint.pt` in `scores.json`.
- Tokenizer: stage the frozen p1536 tokenizer as `./inputs/tokenizer.json`, as `teams/03-tokenizer/release/README.md` describes, and check it against `release/SHA256SUMS`. The file is not in the repository.
- Python (3.12 or later) that runs `run_flow.py`: `llama-cpp-python==0.3.36` and `pyarrow`. Nothing else outside the work folder.
- llama.cpp binaries `llama-quantize` and `llama-server` at b11669 on the PATH (the script checks the build number).
- Work folder `./work/`, prepared once with network, then used offline. It must contain:
  - `llama.cpp-b11669/`, a checkout of tag b11669 (`git clone --depth 1 --branch b11669 https://github.com/ggml-org/llama.cpp`);
  - `.venv-convert/`, a Python 3.12 venv with `llama.cpp-b11669/requirements/requirements-convert_hf_to_gguf.txt`, `llama.cpp-b11669/gguf-py` and `pyarrow<19` installed (this venv also runs the export, so it needs torch and transformers, which the requirements file brings).
  - Nothing else: the export, the GGUF files and the test A3 file are written there by the run.
- Team 10's parquet files, only if TSAI can stage them: `./inputs/code_contests/` (`deepmind/code_contests` at `802411c3010c`, the 24 `train-*.parquet` files the manifest names, about 4.6 GB) and `./inputs/hendrycks_math/` (`EleutherAI/hendrycks_math` at `21a5633873b6`, the 7 `<subject>/train-*.parquet` files, 3 MB). `effort_suite.py` checks each file against the sha256 in the manifest. Without them, drop `--manifest` and both `--source-dir` options; the run then uses our own 100 prompts.

With these in place the run makes no network call: no `git ls-remote`, no clone, no package install, no download. I ran the smoke with `git ls-remote`, `clone`, `fetch` and `pull` blocked and it passed. The tokenizer round trip (`--roundtrip`) is not in this command: it needs held-out text from the Hub, and it tests the tokenizer and the converter, which the weights do not change. Its result for p1536 is in #467's report.

## How the run is scored and reported

- Scores: 20 items, 10 multiple-choice and 10 arithmetic, written by G12 for the flow test (`prompts/eval_own_20.json`, no benchmark text). Each format is scored with `llama-server` on the same items. This is a check that the files work and move little from bf16, not a benchmark. Week 2's eval-mini cannot be passed as items: `teams/12-quantization/eval_mini` runs through lm-evaluation-harness and downloads its datasets, and G9's built item file is gitignored.
- Prompts: Team 10's 55 slots and our 45 fill slots (20 tool, 15 Indic, 10 general) are reported separately in `prompts/summary.json` as `g10_55` and `g12_fill_45`. There is no pooled number.
- For Team 10's slots the run writes no prompt text, no output text and no output token ids, only the slot, token counts, a sha256 of the text, a sha256 of the output ids, the finish reason and the speed. Output ids and text are written for our 45 prompts only.
- One checkpoint, one seed, greedy decoding. No winner is named and no setting is changed.

## What I ran before filing

A smoke of the same command form (no `--manifest`, because the parquet files are not on my machine) on an Apple M5, 16 GB, Metal, llama.cpp b11669, with a random-weight model in the shape of dry run 1: the `manifest.json` of TSAI's full run folder (`teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/`), 237 million parameters in the trainer's layout, in a `checkpoint.pt` with optimizer, stream and RNG entries like the trainer writes. Exit 0 in 1 min 54 s with a warm work folder. A1 PASS (max logit difference 8.1e-06, same top-1 on 4,096 of 4,096 positions), A3 PASS (same top-1 on 16 of 16 prompts, max log-probability difference 0.0372, limit 0.05). The three files are 0.61, 0.32 and 0.22 GB. The `--manifest` path ran with synthetic text for the 55 slots: 55 rows without text or ids, 45 with, summary split into `g10_55` and `g12_fill_45`. The commands, the logs and the unit tests (29 tests in four files) are in [smoke.md](evidence/2026-11-18-dryrun1-quantize-eval/smoke.md).

The smoke is not a result: random weights, so scores and agreement with bf16 mean nothing. I could not test the trained checkpoint, a GPU, the real parquet files, or a machine without network (I blocked the git calls but the machine had network).

## Open items for TSAI

1. **Tools.** Are llama.cpp b11669 (`llama-quantize`, `llama-server`) and a Python with `llama-cpp-python==0.3.36` and `pyarrow` installed on the job machine, and can the work folder above be prepared with network once? The GPU build of llama.cpp and of llama-cpp-python is optional: the flow also runs on CPU, slower.
2. **Team 10 parquet files.** Can `code_contests` (about 4.6 GB) and `hendrycks_math` be staged? If not, the run uses only our own 100 prompts and the Team 10 split is empty.
3. **Network.** Is no network at run time acceptable with the prepared work folder? Nothing in the command needs it then. If the job must fetch the pinned pieces, the first run needs git and PyPI.
4. **Where the work folder lives.** The rule is that a job writes only to `./out/`. The work folder (llama.cpp checkout, converter venv, the exported model of about 0.6 GB) is far over 50 MB, so I put it at `./work/`, outside `./out/`. If it must be under `./out/`, tell me where it may be deleted from the 50 MB count.
5. **Run folder.** Is `./out/dryrun1-1234/` the folder TSAI kept, with `checkpoint.pt` and `manifest.json`? If its path or layout differs, I change `--checkpoint`.
6. **Export risk.** `export_hf.py` was written against the checkpoint of `make_random_checkpoint.py`. I checked it on a random model with the dry run 1 shape and the full trainer layout (`model`, `optimizer`, `stream`, RNG entries, `step`) and the manifest of TSAI's full run: A1 PASS. I have not seen the real `checkpoint.pt`. If the export stops on it, the first line of the error says which tensor or setting it did not expect.
7. **Time.** 60 minutes is an estimate. The M5 smoke took under 2 minutes for a model of the same size, but the 55 Team 10 prompts are longer than ours and a GPU build is not tested.
