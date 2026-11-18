# Job request: G10 day-one probe of the dry-run-1 run folder

TSAI agreed on 16 Nov to run this probe on the dry run 1 checkpoint (#475). It reads the #475 run folder in place: no
checkpoint leaves TSAI's machine, nothing is written outside `out/`, and every input is public or already staged by
TSAI. Nothing private has to be handed over.

Dry run 1 was trained with the frozen p1536 tokenizer (TSAI's result comment on #475, 16 Nov: "tokenizer p1536 (sha256
e6b93a93...a64b)"), although the #475 job file asked for C3. This request uses p1536 and its matching KE2 byte table,
and the probe refuses to start if they are not the ones the run folder's own manifest records.

```
Team:            10-post-training
Owner:           f20201351h-maker
Lead approval:   saitej123 (requested on this PR)
Question:        On the dry-run-1 checkpoint, which SFT setup makes the base model close a chat turn (full, LoRA, LoRA + marker head rows, Deletion Tuning, marker rows only), and does the base or SFT'd model get any RL signal on the easiest RL prompts?
Script:          teams/10-post-training/capstone/day_one_probe.py at this PR's head commit (base: main 5aed520); it calls capstone/probe_inputs.py, sft_g5.py, bench_sampling_g5.py, mismatch_g5.py, rl-loop/team5_adapter.py and rl-data/stdio_check.py from the same commit
Command:         G10_STDIO_RUNNER=docker python teams/10-post-training/capstone/day_one_probe.py --g5-root <G5> --run-folder <RUN> --tokenizer <TOKENIZER> --byte-table <TABLE> --heldout <HELDOUT> --heldout-sources <HELDOUT_SOURCES> --sft-dolly <DATA>/databricks-dolly-15k.jsonl --rl-tasks <POOL>/out/v1/cc.jsonl --rl-ids teams/10-post-training/capstone/probe_rl_easy_ids.txt --rl-limit 48 --rl-max-new 512 --sft-steps 300 --sft-max-train-seconds 480 --device cuda --out out/
Config:          none: every setting is on the command line above
Seed:            1 (sampling and SFT); the run folder's own seed 1234 is not used
Inputs:          see "Inputs and pins" below (all public or TSAI-staged; sha256 for each)
Packages:        Python 3.12, torch (CUDA build), numpy, tokenizers, pyyaml, safetensors; Docker for the code verifier. CPU log used torch 2.14.1, numpy 2.5.4, tokenizers 0.23.3, pyyaml 6.0.3, safetensors 0.8.0
Hardware:        1 GPU
Max time:        60 minutes, enforced by TSAI's job runner on the whole process group (partial reports are valid on timeout)
Precision:       weights as stored (fp32); the mismatch step also measures bf16 autocast
Measures:        pins (tokenizer and table content hash against the run manifest, checked first); adapter status and hashes; held-out bpb per slice; native sampler tokens/s (last-position head vs KV cache, identical tokens); share of tokens outside objective_v1's trust region from numerics alone and expert-set flips (1 row vs 8, fp32 vs bf16) on CUDA; base format screen (64 prompts); RL screen (48 prompts x 8 samples: pass rate, mixed groups, failure reasons); per SFT arm: closed <|im_end|> on 64 eval prompts, eval NLL, forgetting (held-out bpb before/after), step-1 writeback (fp32 vs what bf16 storage would keep), frozen-weight and reload checks, RL screen after full and LoRA + markers
Expected result: pins: both hashes match the run manifest; inputs: 5,255 train / 589 eval rows with the sha256 below; base: 0 closed turns, RL pass 0 with "no code block"; full and LoRA + marker rows close most turns, LoRA and DT alone close none (seen on the d128 stand-in, 2 seeds); RL screen after SFT still 0 (Dolly has no code); mismatch below 0.5% (stand-in: 0.11-0.17% bf16 vs fp32 on MPS/CPU); total 30-55 min (ESTIMATE, basis under "Time")
Outputs:         out/*.json, out/sft_*/sft_report.json, out/adapter.yaml (paths and hashes); no rows, generations or weights on ordinary exit; under 2 MB
Test log:        teams/10-post-training/jobs/2026-11-17-g10-dryrun1-probe.log (CPU, same script from a clean git archive of commit 82c4bc5, d128 stand-in trained on p1536, reduced steps)
```

## Inputs and pins

The placeholders are TSAI-side paths. `<G5>` is the lab checkout TSAI ran dry run 1 from and `<RUN>` its run folder
(`manifest.json`, `checkpoint.pt`, `summary.json`). #475's result comment does not name the code revision or where
the p1536 inputs were staged, so this request does not assume them: the adapter refuses a run folder whose manifest
source hashes differ from `<G5>`'s harness, and the `pins` step refuses a tokenizer or table the manifest does not
record. `<HELDOUT>` and `<HELDOUT_SOURCES>` are the original heldout_v1 bytes and source map dry run 1 scored.

| Input | Where TSAI gets it | Pin |
| :--- | :--- | :--- |
| Run folder | #475 output, kept by TSAI | `manifest.json`, `checkpoint.pt`, `summary.json`; the adapter checks `model_hash` against `summary.json` |
| Tokenizer | the p1536 `tokenizer.json` TSAI used for dry run 1 (Team 3 release, `teams/03-tokenizer/release/SHA256SUMS` on main) | sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` |
| Byte table | the raw P32 table TSAI used for dry run 1. The committed Team 4 p1536 table is `teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz` (#498). #475's result comment does not state the table hash, so `pins` checks the content hash against the run's `manifest.json` | committed table: file `e19a6cae8a6e9e5f74c47748f459df4b156bb61b8cec2af485b439c7132a39b0`, content `21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a` |
| Held-out | the heldout_v1 file and source map #475 scored | as recorded in #475's `manifest.json` |
| Dolly-15k | public: `databricks/databricks-dolly-15k` @ `bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a`, file `databricks-dolly-15k.jsonl` (CC-BY-SA-3.0, human-written) | sha256 `2df9083338b4abd6bceb5635764dab5d833b393b55759dffb0959b6fcbf794ec`, 13,085,339 bytes |
| RL tasks | `out/run/out/v1/cc.jsonl` of the RL data v1 pool job (`jobs/2026-11-18-rl-data-v1-pool.md`) | sha256 `91ee99512f0411aea2de4ca5eaf10b87b2d8f785ca73747bf8deb45dd6ea9be0` (the `expected` value in `rl-data/rebuild_v1/pins_v1.json`) |
| RL ids | in this PR: `capstone/probe_rl_easy_ids.txt`, 48 ids | sha256 `452178c10e7325bc1cea62b0ad567a68dc32f6596f273b97dc8a36728f985c6f` |

The SFT rows are built inside the job (step `inputs`, `capstone/probe_inputs.py`): row i of the Dolly file becomes
`sft-dolly-15k/i`, is rendered by `sft/convert.py` in G10 chat format v0 (assistant body plus `<|im_end|>` trained),
re-tokenised with the run's own tokenizer and checked byte for byte against the table; the pre-training half of Dolly
is refused by id hash and rows over 256 tokens are dropped, not cut. With the p1536 tokenizer and the committed table
above the job must report:

| Built file | Rows | Bytes | sha256 |
| :--- | ---: | ---: | :--- |
| `sft_train.jsonl` | 5,255 | 5,825,858 | `c273a4d7a7b6fb9a0520829a8c15a1feb00899e4fa0f0deb60931de39b7cbd62` |
| `sft_eval.jsonl` | 589 | 652,769 | `f77fc96c15be384e5634124f4655f43ee2513857547f0b3cc3992fdb984a556e` |

`out/inputs.json` records these values; a different sha256 means a different Dolly file, tokenizer or table. The rows
live in `out/_inputs/` during the run and are deleted at exit, on success and on failure.

Why the rows are built in the job: the ids then always come from the tokenizer TSAI stages for the run, and nothing
private is sent. These are the same bytes as the G10 rehearsal's p1536 files, which checks that it is the same
pipeline. An earlier version of this request pinned C3, read from #475's job file; TSAI's result comment shows the run
used p1536, and C3 ids differ on 102 of the 5,255 train rows, so that version would have fed the checkpoint partly
wrong tokens. The `pins` step now catches that before any model work.

The RL ids are RL data v1 code_contests problems (codechef/hackerearth, statement up to 310 p1536 tokens), a random 48
of 754 with seed 20261116. Under p1536 the statements fit the 2,048-token context with room for 512 new tokens; any
that does not is counted as `skipped_too_long`, not dropped silently.

## Time

Measured (CPU log attached, clean export of commit 82c4bc5, Apple M1 Pro, d128 stand-in with 24.7M parameters
trained on p1536, reduced settings): all 13 steps ok in 771 s wall. Pins 0.0 s, inputs 4.0 s, adapter 1.8 s,
forgetting 24.7 s, sampling 20.6 s, mismatch 108.1 s, format 19.2 s, RL screen 7.6 s (4 prompts), SFT arms
105.0-131.6 s each (30 steps), most of it evaluation, generation, forgetting and the reload check. These are CPU
times on a 24.7M stand-in; they show the steps run, not how long they take on the T2 checkpoint.

Estimated for the job (not measured; no GPU run of this script on the T2 checkpoint exists):

| Part | Bound | Basis |
| :--- | :--- | :--- |
| Five SFT arms, training | at most 40 min (5 x 480 s cap) | 300 steps of 16 rows of at most 256 tokens is about a quarter of a T2 pre-training step's tokens per step; the cap stops an arm that is slower |
| Evaluation, generation, forgetting, three RL screens, mismatch | about 10-15 min | three screens of 48 prompts x 8 samples x up to 512 new tokens with the KV-cache sampler; the base and Dolly-trained models are expected to write no code block, so the verifier mostly returns at once |
| Pins, loading, inputs, adapter | under 1 min | 5.8 s on the CPU log; the pins step only hashes two files |

So 30-55 minutes, inside the 60-minute limit even if every arm hits its cap. If the runner stops the job at 60
minutes, the step files already written are valid and `summary.json` is missing; the arms run in the order full,
markers, LoRA, LoRA + markers, DT, so the most important comparison finishes first.

## Execution limits and failure reporting

The five 480-second limits cover training loops only, checked between optimizer steps. Loading, calibration,
evaluation, generation and verification add time. The Python entry point does not enforce a 60-minute global deadline:
TSAI must enforce `Max time` on the whole process group. A deadline can leave some steps unfinished; the completed
step JSON files stay valid. On ordinary success or failure each arm removes its weights and generations, and the probe
removes `out/_inputs/`; an abrupt process kill needs the job runner's cleanup of `out/_inputs/` and
`out/sft_*/model.safetensors` before results are returned. The script continues independent checks after an ordinary
step failure, writes `summary.json`, and exits nonzero if any step failed. If the `pins` step fails (a tokenizer or
table content hash differs from the run manifest; both values are printed and saved in `pins.json`), nothing else
runs and the exit code is 1. If the `inputs` step fails, nothing else runs (every later step reads its rows).

The code verifier runs each sample in a Python temporary directory (removed after each check) inside Docker. If
Docker is not available, `G10_STDIO_RUNNER=local` (uid-isolated, needs root); if neither is allowed, drop
`--rl-tasks/--rl-ids` and the job still answers the SFT half of the question. If the pool job's `cc.jsonl` is not in
TSAI storage yet, drop the same two flags.

DT is an exploratory diagnostic arm. Calibration can miss experts and initialize more deletion than the intended prior;
the report records uncovered layers and deletion at initialization. It is not an endorsed training recipe. No CUDA or
full-width performance claim is made from CPU evidence.
