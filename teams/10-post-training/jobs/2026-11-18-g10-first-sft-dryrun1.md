# Job request: G10 first SFT on the dry run 1 checkpoint, 2,048-token code slice, traces vs short answers

**Run after #565 and #564.** This job reads two outputs TSAI stores from those merged requests: the firewalled OCR-2
pack shards 0-3 (#565) and the RL data v1 `cc.jsonl` (#564). If either file is missing or is not the pinned bytes, the
job stops in its first step, before any row is built, and names the missing input and the job that makes it.

Every setting is fixed below with its evidence. The day-one probe (#558) has not returned yet; nothing here waits for
it. "If the #558 result shows otherwise" names the only values that would change and to what.

Why: the probe tells us whether dry run 1 can be fine-tuned at all (which method closes a chat turn, at what forgetting
cost, how fast the native sampler is). This job is the first SFT on that checkpoint with the data it would really get:
OCR-2 code rows, the SFT data v1 code set. Dry run 1 has a 2,048-token context and most OCR-2 rows are longer
(measured on the four shards used here: 4,050 of 30,615 rows fit, 13.2%; the whole-pack length table
`sft/results/sft_v1_lengths_p1536/sft-code-opencodereasoning-2.json` gives 18.5%), so the job trains on the rows that fit,
dropped and counted, never cut. G10's small-model study E9 (`results/e9_sft_before_rl.md`, SmolLM2 135M and 360M, one
seed) found that long reasoning traces make a weak model run out of token budget before it writes code, while the same
rows with the reasoning deleted give closed turns with running programs. That is a small-model finding; this job checks
it on our own architecture as the second arm.

```
Team:            10-post-training
Owner:           f20201351h-maker
Lead approval:   saitej123 (asked TSAI in the G10 group on 17 Nov to approve and process this request)
Question:        On the dry-run-1 checkpoint, which shape of the same OCR-2 SFT rows (those that fit 2,048 tokens) gives more RL-usable output on the easiest RL prompts, full reasoning traces (A2) or the same rows with the reasoning deleted (A4), and does either stay within +0.05 bits per byte of forgetting?
Script:          teams/10-post-training/capstone/sft_job_v1.py at this PR's head commit; it calls capstone/sft_slice_v1.py, sft_g5.py, day_one_probe.py (pins, arm cleanup, RL screen), rl-loop/team5_adapter.py and rl-data/stdio_check.py from the same commit
Command:         G10_STDIO_RUNNER=docker python teams/10-post-training/capstone/sft_job_v1.py --g5-root <G5> --run-folder <RUN> --tokenizer <TOKENIZER> --byte-table <TABLE> --heldout <HELDOUT> --heldout-sources <HELDOUT_SOURCES> --packs <PACK>/shard-00000/pack.firewalled.jsonl <PACK>/shard-00001/pack.firewalled.jsonl <PACK>/shard-00002/pack.firewalled.jsonl <PACK>/shard-00003/pack.firewalled.jsonl --rl-tasks <POOL>/out/v1/cc.jsonl --rl-ids teams/10-post-training/capstone/probe_rl_easy_ids.txt --rl-limit 48 --rl-seconds 420 --rl-max-new 1536 --method full --lr 1e-4 --steps 243 --batch 16 --max-train-seconds 1500 --deadline-minutes 85 --gen-limit 8 --gen-seconds 90 --gen-max-new 1536 --seed 1 --device cuda --out out/
Config:          none: every setting is on the command line above
Seed:            1 (row order, sampling, LoRA init); the run folder's own seed 1234 is not used
Inputs:          see "Inputs and pins" (public, TSAI-staged, or stored by an earlier G10 job; sha256 for each)
Packages:        Python 3.12, torch (CUDA build), numpy, tokenizers, pyyaml, safetensors; Docker for the code verifier. CPU log used torch 2.14.1, numpy 2.5.4, tokenizers 0.23.3, pyyaml 6.0.3, safetensors 0.8.0
Hardware:        1 GPU
Max time:        90 minutes (the T2 cap). The script stops itself at 85 minutes (--deadline-minutes 85: an arm still running is killed, its weights removed, summary.json names it); the runner's own limit is the backstop. Estimate 60-80 minutes, an estimate; basis under "Time"
Precision:       weights as stored (fp32), AdamW state fp32; the step-1 writeback check reports what bf16 storage would have kept
Measures:        pins (tokenizer and table against the run manifest; every input present; run block size 2,048; RL pool sha256); slice: rows read, dropped by reason, kept per length bucket and effort tier, sha256 of each built file; per arm: dev NLL, forgetting (held-out bpb before and after, per group), greedy format screen on 16 dev prompts (closed turn, validity, hit budget), RL screen on the easy prompts (k 8, temperature 1, 420 s budget per screen: code-fence share, programs that run, pass rate, mixed groups, reasons, prompts reached), step-1 writeback, frozen-weight and reload checks, steps done and training seconds; compare.json with the decision rule applied
Expected result: pins match; slice exactly as in the table below (3,903 train rows, 147 dev rows); base: no closed turns, RL pass 0; A2: closes some turns, many samples hit the 1,536-token budget, few programs run; A4: most samples close with a code fence and more programs run than A2, pass near 0; forgetting within +0.05 for A2, A4 unsure (E9 135M: +0.070 with repeated short rows; here A4 sees each row as often as A2); mixed groups 0-2 in both arms (E9: 0-3% below 1B parameters); A2 stops at the 1,500 s training cap after about 40-175 of its 243 steps; total 60-80 min, an estimate (basis under "Time"); the script's own 85-minute deadline caps it
Outputs:         out/*.json, out/sft_a2/sft_report.json, out/sft_a4/sft_report.json, out/adapter.yaml (paths and hashes); no rows, generations or weights on ordinary exit; under 2 MB
Test log:        teams/10-post-training/jobs/2026-11-18-g10-first-sft-dryrun1.log (CPU, same script from a clean git archive of commit e113f299, context-2,048 stand-in trained on p1536, the same four pack shards, reduced steps and budgets)
```

## Design (one question, one change between arms)

- **Rows.** The firewalled OCR-2 pack v1 (p1536), shards 0-3: SFT data v1 code rows after the eval firewall (no problem
  used to evaluate RL or effort is in them). Rows longer than the model's block size are dropped and counted. Each kept
  row is re-tokenised with the run's own tokenizer and table and must give exactly the pack's ids and loss mask.
- **The one change.** A2 trains on the rows as they are (reasoning trace, then the code). A4 trains on the same rows,
  same order, with the `<|think|>` ... `<|/think|>` block deleted; nothing is written, only admitted text is removed (the
  E9 A4 rule). A row without a reasoning block or without code after it is dropped from both arms (none on these four
  shards). A4 runs exactly the optimizer steps A2 completed, so a training-time cap cannot make the arms unequal; A4
  therefore sees fewer tokens per step. Same method, learning rate, batch, seed and evaluation for both.
- **Length buckets.** The slice keeps the pack's own length mix inside the limit and reports it per bucket; it is not
  resampled. Here 84% of training rows are 1,025-2,048 tokens long, so the arms train mostly on the longest rows that fit.
- **Dev split.** 5% of problems by a salted hash of the user turn (the system turn names the effort tier, which differs
  between completions of one problem, so it is left out); every completion of a problem is on one side. The pack's own
  held-out split (`heldout_eval_v1`) is not read.
- **Head rows.** Dry run 1's input side has no per-token embedding rows (KE2 maps each token's byte code through one
  shared projection, `teams/05-architecture/harness/week2/model.py`), and its output head is untied (#556: config v1
  leaves `ke2_output_dim` empty). So the nine chat-marker tokens have trainable rows only in `head.weight`. With
  `--method full` the whole head trains; with `--method lora_markers` LoRA adapters plus those nine head rows train
  (`--marker-rows`, weight decay 0). This job uses `full` (see "Settings and why").
- **Evaluation (eval_v1, code part).** Forgetting: Team 5's own `evaluate()` on the held-out file dry run 1 scored
  (G5 protocol). Format validity: `chat-format/render.py` parse of greedy generations on dev prompts. Execution: the RL
  reward's sandboxed verifier (`rl-data/stdio_check.py`) on the 48 easiest RL prompts of the probe
  (`capstone/probe_rl_easy_ids.txt`), the same ids the probe screens on the base model. Not covered here: the bench's
  sealed test split and eval-mini (Team 9), and the tool-call, Indic and safety sets (chat data, not code).
- **Decision rule (applied in `compare.json`).** Among arms within +0.05 bpb forgetting, the arm with more mixed groups,
  then more running programs, becomes the default SFT row shape for the next SFT job on a TSAI checkpoint. "RL signal"
  needs at least 2 mixed groups. Each screen walks the ids in the file's fixed order and starts no new prompt after its
  time budget, so A2 and A4 are compared on the prompts both screens reached (`compare.json` `compared_on`), and the
  base on the same ids. If neither arm has it, RL on this checkpoint size waits; the SFT recipe still
  takes the winning shape. One seed and at most 48 prompts: a difference of one or two mixed groups is within noise
  and is reported as such.
- **What does not transfer.** Dry run 1 is a T2 checkpoint (8 layers, width 512, 16+1 experts, 1,221 steps). A
  verdict here is about a weak checkpoint at a 2,048 context; the capstone model will be larger, trained longer and may
  have a longer context, so the short-vs-long answer must be re-measured on it. SFT data v1 Dolly and Indic rows are not
  in this job (one change per comparison).

## Settings and why

| Setting | Value | Evidence |
| :--- | :--- | :--- |
| Method, learning rate | `full`, `1e-4` (AdamW 0.9/0.95, the `sft_g5.py` defaults) | G10's SmolLM2 bench on code rows with reasoning blocks (`results/small_sft.md`): full FT at 1e-4 closed 74-79% of turns over 3 seeds with forgetting +0.0503 to +0.0515 bpb; LoRA r=4 at 1e-3 forgot only +0.0384 but closed 0 of 110 turns (it emitted `<|im_end|>` first). An arm that closes no turn gives the RL screen nothing to score, so full FT is the method that can answer the question; its forgetting is reported against the +0.05 limit, not assumed. E9 used the same 1e-4. The probe's own full arm uses 3e-4 on short Dolly rows; these rows are about six times longer per step, so the bench value is kept (one change at a time). |
| Optimizer | AdamW, not Muon | TSAI's Gate 3 learning-rate recheck (muon_lr 0.005 with lr 0.001 beat dry run 1's 0.01 on seeds 1234 and 1235) is about pre-training from scratch. Fine-tuning a trained checkpoint with Muon is not tested anywhere in G10 or G5, and the bench, E9 and the probe all use AdamW; changing the optimizer would add a second change to a one-question job. |
| Precision | fp32 weights and AdamW state | step-1 writeback on the CPU log: bf16 storage would keep about 8% of the first update, fp32 keeps all of it |
| Steps, training cap | `--steps 243` (one pass over the 3,903 rows, no row twice), `--max-train-seconds 1500` | E9: repeating short rows made A4 forget more (+0.070), so no row repeats. The cap is expected to stop A2 first, after about 40-175 steps (Time); A4 then runs exactly A2's completed steps |
| RL screen | 48 easy ids (the probe's), k 8, up to 1,536 new tokens, `--rl-seconds 420` per screen | 1,536 new tokens is what a 2,048 context leaves after the prompt, and running out of budget is the effect under test (E9), so it is not shortened. The Mac GPU decodes the dry-run-1 shape at 98 ms per step (Time), about 150 s per prompt when every sample runs to the budget, so the screen is budgeted instead of counted |
| Format screen | 8 dev prompts, greedy, up to 1,536 tokens, `--gen-seconds 90` | secondary to the RL screen; budgeted for the same reason |
| Block size | 2,048 | dry run 1's config (`exp2_muon.yaml` inherits `t2.yaml`, `block_size: 2048`; #475). The job now checks the run folder's own `manifest.json` and stops if it differs |
| Pack, pool | #565 `out/firewalled/shard-0000{0..3}`, #564 `out/run/out/v1/cc.jsonl` | sha256 below; any other bytes stop the job in `pins` |

## If the #558 result shows otherwise

- `sft_full` forgets more than +0.05 bpb on dry run 1 **and** `sft_lora_markers` closes at least half as many turns as
  `sft_full` within +0.05: change `--method full --lr 1e-4` to `--method lora_markers --lr 1e-3` (marker rows at the
  default `--marker-lr 1e-3`). If neither closes turns, keep `full`.
- `sampling.json` (KV path) or `forgetting.json` is much slower than the basis below: lower `--max-train-seconds` so
  that 3 x the probe's forgetting seconds x 1.4 (the dev rows) + 1,500 s of training + A4 + 3 x 510 s of screens stays
  under 85 minutes. Faster needs no change: the budgets only cap.
- `adapter.json` `model_spec.block_size` is not 2,048: the job stops in `pins` by itself; the slice table would then be
  rebuilt locally with `capstone/sft_slice_v1.py --max-tokens <block size>` and the hashes below replaced.
- No path changes: the placeholders are the ones the probe used.

## Inputs and pins

`<G5>`, `<RUN>`, `<TOKENIZER>`, `<TABLE>`, `<HELDOUT>`, `<HELDOUT_SOURCES>` are the same TSAI-side paths the probe
(#558) used: `<G5>` the lab checkout dry run 1 ran from, `<RUN>` its run folder (`manifest.json`, `checkpoint.pt`,
`summary.json`), the p1536 tokenizer and table it trained with, and the original heldout_v1 bytes and source map it
scored. Only TSAI knows these paths. `<PACK>` is where TSAI stores #565's `out/firewalled`; `<POOL>` is where it stores
#564's `out/run`. The job stops at once, before any row is built, with the reason in `out/pins.json`, when the
tokenizer or table is not the one the run manifest records, when the run folder has no checkpoint or manifest or a block
size other than 2,048, when any pack shard or `cc.jsonl` is missing (the message names #565 or #564), or when
`cc.jsonl` is not the pinned file. The adapter then refuses a run folder whose source hashes differ from `<G5>`.

| Input | Where TSAI gets it | Pin |
| :--- | :--- | :--- |
| Run folder, tokenizer, table, held-out | as for the probe (#558) | tokenizer `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`; table content `21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a` |
| OCR-2 pack, shards 0-3 (`<PACK>`) | `out/firewalled/shard-0000N/pack.firewalled.jsonl` of the OCR-2 pack job (#565), stored by TSAI | the firewalled sha256 in `sft/results/ocr2_eval_firewall_v1.json` (`applied_locally`), listed in the next table; any other file is refused before it is read |
| RL tasks (`<POOL>`) | `out/run/out/v1/cc.jsonl` of the RL data v1 pool job (#564, `jobs/2026-11-18-rl-data-v1-pool.md`) | sha256 `91ee99512f0411aea2de4ca5eaf10b87b2d8f785ca73747bf8deb45dd6ea9be0` |
| RL ids | in the repo: `capstone/probe_rl_easy_ids.txt`, 48 ids (the probe's) | sha256 `452178c10e7325bc1cea62b0ad567a68dc32f6596f273b97dc8a36728f985c6f` |

| Pack shard | Bytes | sha256 (firewalled) |
| :--- | ---: | :--- |
| 0 | 608,603,588 | `227d97e37ede3b203b8f07a4d5e247c83ab1f1f202b1376ba755d435f2a25c06` |
| 1 | 604,823,777 | `8a5c19ac8c6793ee701c983ff76a93b14d75073267d6ce8269d2ffe398aa312f` |
| 2 | 594,146,724 | `0143f11095ac75a103f2c5d752baf758dcdcee7f275eaecc6e845dca086b698b` |
| 3 | 605,885,024 | `c2b530f12a166cc28f35e45ddb30c36c3bf14f56d35f413ab02850dd5f738e2c` |

The slice is built inside the job (step `inputs`); with the p1536 tokenizer, the committed table and these four
shards, at a block size of 2,048, it must give (measured on the CPU log, `out/inputs.json` records the same fields):

| Built file | Rows | Tokens | Trained tokens | sha256 |
| :--- | ---: | ---: | ---: | :--- |
| `a2_train.jsonl` | 3,903 | 5,686,666 | 4,582,876 | `19ac5d12d8bd79665c4d8bee2d76a42ad4d112af0cbca0fe1e3815a333669a17` |
| `a4_train.jsonl` | 3,903 | 1,377,452 | 273,662 | `c39626735fe7c25f28821a6252e65df394201396d713460f781e4685f0e9b3e5` |
| `dev.jsonl` | 147 | 217,560 | 168,892 | `29f69de4c467c27a80126b373c9820c6d7d40210225efe932a0406f7c7888538` |

Training rows by length: 15 up to 512 tokens, 615 from 513 to 1,024, 3,273 from 1,025 to 2,048; effort tiers 1k 1,576
and 4k 2,327 (no 16k or longer row fits). Token counts p50/p90/p99: A2 1,507/1,946/2,033, A4 333/527/722. The rows live
in `out/_inputs/` during the run and are deleted at exit, on success and on failure.

**Data route and what it costs.** The job reads the stored pack (#565) and pool (#564) and needs nothing handed over by G10. Building the slice
inside the job from the public sources instead was weighed and not taken: it would run `sft/run_ocr2.py` (join, decontam,
render, pack) on four shards first, about 40 CPU-minutes per shard with one worker (median 2,374 s per shard, the
p1536 build record `sft/results/ocr2_pack_v1_p1536.md`), and it would still need the private evaluation-firewall family
list handed over, the same file the pack job needs. If #565 is not run when this job is approved, the cheapest route is
for TSAI to run #565's own two commands with `--shards 0:4` first (same code, same pins, CPU only, about 40 minutes with
four workers); this job then reads those four files unchanged and checks them by sha256. #564's `cc.jsonl` does not
need the two private id lists (#564 says the same for the probe's copy).

## Time

Measured on the CPU log (attached, clean export, Apple M1 Pro, context-2,048 stand-in with 10,611,008 parameters,
reduced settings): all 5 steps ok in 289 s wall. Pins 0.1 s, slice 21.3 s, A2 203.5 s (10 steps of 16 rows: 76.9 s training, the rest evaluation, generation, forgetting and two RL screens), A4 64.4 s (the same 10 steps: 6.2 s training; no base evaluation), compare 0.0 s; each RL screen stopped at its 3 s budget after 3 of 6 prompts, as set. These show the steps run on rows of the real length; they are not T2 timings.

No timing of this script on dry run 1 exists, so the estimate is built from three measurements, each labelled:

1. **Training rate, TSAI's GPU (measured by TSAI, pre-training shape).** Team 7's restore drill on dry run 1 (#573,
   job B): load, steps 611 to 1,221 and the save took about 30 min 39 s on one GPU, so at most 3.0 s per step of
   8 x 2,048 = 16,384 tokens, at least 5,440 tokens/s in bf16 with Muon. Dry run 1 itself (1,221 steps inside its
   90-minute cap, #475) gives at least 3,705 tokens/s. The first T2 run, before TSAI's speed fixes, measured 12.7 s per
   step (the Instructor's message to Team 5 in the G5 group): 1,290 tokens/s, the slow end. These are pre-training
   steps: batch 8 full 2,048-token windows, bf16, Muon. This job's steps are 16 rows of 1,457 tokens on average, fp32,
   AdamW, through G10's SFT loop. Assumption, not measured: fp32 halves the rate, giving 645 to 2,720 tokens/s for a
   training step and about three times that for forward-only evaluation.
2. **Decode rate, the dry-run-1 shape on a Mac GPU (measured here).** A stand-in with dry run 1's config (8 layers,
   width 512, 8 heads, 2 KV heads, 16+1 experts top-2, expert FFN 768, context 2,048; 237,052,416 parameters, a
   2.16 GB checkpoint against dry run 1's "about 2.2 GB"; random weights) through `capstone/bench_sampling_g5.py --paths
   kv --k 8 --prompt-len 256 --max-new 256 --device mps`: 25.2 s, 81.4 new tokens/s, 98 ms per step for 8 samples.
   This Mac GPU is taken as slower than TSAI's; no CUDA decode figure exists. Full fine-tuning at this size does not fit
   in the Mac's 16 GB (MPS out of memory), so the training rate comes from item 1.
3. **Token counts (measured here).** A2: 16 rows x 1,457 mean = about 23,300 tokens per step; A4 about 5,650. One
   evaluation reads the 147 dev rows (217,560 tokens) and heldout_v1 (3,775,551 bytes, about 543,000 tokens at the 6.95
   bytes per token of our heldout_v1 sample), about 760,000 tokens.

| Part | Bound | Basis |
| :--- | :--- | :--- |
| Pins and slice | under 1 min | CPU log: slice 20-23 s for 2.4 GB of packs |
| Loading, reload checks | about 3 min | two model loads and two save/reload parity checks of a ~1 GB model |
| Three evaluations (base, after A2, after A4) | 5-20 min | 3 x 760,000 tokens at 1,935-8,160 tokens/s (item 1) |
| A2 training | 25 min (cap) | 8.6-36 s per step: 41-174 of 243 steps fit in 1,500 s; the cap is checked between steps |
| A4 training | under 7 min | A2's steps at a quarter of the tokens per step |
| Six screens (RL 420 s and format 90 s, x 3) | 25.5 min | the budgets; a screen finishes the prompt it is on, which adds at most one prompt each (about 2.5 min per RL prompt at the Mac rate of item 2, less on a faster GPU) |
| Total | about 60-80 min (estimate) | the script stops itself at 85 min; Max time 90 |

What the budgets mean for the result: at the Mac decode rate an RL screen reaches only about three prompts when every
sample runs to 1,536 tokens, and more when samples close early (A4) or the GPU is faster. `compare.json` records how
many prompts both arms reached, and the decision rule needs two mixed groups among them; a comparison on very few
prompts reads "no RL signal" and says so.

Max time does not rest on this estimate: the script ends itself at 85 minutes (`--deadline-minutes 85`). An arm still
running then is killed, its weights are removed, and `summary.json` names it. The step files already written are valid;
A2 runs first, so a deadline loses A4 and the comparison, not A2. A verifier container started just before the kill
ends at its own per-test timeout.

## Saving and resuming

The job saves no resumable state. TSAI asked that pre-training runs save through Team 7's Checkpointer (G7 restore drill,
#573, merged: restore A and B pass on dry run 1); the job request form (`JOB_REQUEST.md`) does not ask for it. This job is one GPU, at most 90
minutes, returns reports only (each arm's weights are deleted after the reload check, as in the probe), so a kill costs
at most one re-run of the job. A later SFT job whose weights are kept for RL or Team 9 evaluation should save through
`teams/07-infrastructure/ckpt` (`Checkpointer.save`, then `export_safetensors()`); that is not this job.

## Execution limits and failure reporting

The `--max-train-seconds` cap covers A2's training loop only, checked between optimizer steps; A4 runs A2's completed
step count. Loading, evaluation, generation and verification add time; the whole job is bounded by `--deadline-minutes 85`,
which kills an arm still running at that time; TSAI's `Max time` on the process group is the backstop. Each RL and format screen starts no new prompt after its budget (`--rl-seconds`,
`--gen-seconds`). On ordinary success or failure each arm removes its weights
and generations and the job removes `out/_inputs/`; an abrupt kill needs the runner's cleanup of `out/_inputs/` and
`out/sft_*/model.safetensors`. If `pins` fails nothing else runs (exit 1): a tokenizer or table the run did not train
with, a run folder without `checkpoint.pt` or `manifest.json` or with a block size other than 2,048, a missing pack
shard or `cc.jsonl`, or a `cc.jsonl` that is not the pinned file. If `inputs` fails (a pack whose sha256 is not in the
firewall record) nothing else runs. If A2 fails, A4 runs
with its own base evaluation and `compare` reports the failure.

The verifier runs each sample in a temporary directory inside Docker; `G10_STDIO_RUNNER=local` (uid-isolated, needs
root) is the fallback. No CUDA or full-width performance claim is made from CPU evidence.

## Run-gate evidence (speed and executability)

- Runs end to end: the attached CPU log of commit e113f299 from a clean `git archive`: exit 0, `{"ok": true, "steps": 5, "failed_steps": []}`, `pins` passed with the new input and block-size checks (block_size 2048, RL pool sha256 the pinned file), built files with exactly the sha256 above, A4 ran A2's 10 steps, mask checks and reload parity pass in both arms, each RL screen stopped at its budget and `compare.json` compared the arms on the 3 prompts both reached, 52 KB of output with rows and weights removed. Tests: `pytest rl-loop/test_sft_job_v1.py rl-loop/test_day_one_probe.py`: 29 passed, 1 skipped (a tokenizer test that needs a local file); they cover a missing pack, a missing pool, a wrong block size and a wrong pool hash each stopping before any row is built, the screen budget, the common-prompt comparison, and an arm killed at the job deadline with its weights removed.
- Hot path added by this job: the slice builder. Counting ids from the raw line and parsing only the rows that fit
  (about one in seven) instead of parsing every 600 MB shard: 23.05 s before, 3.94 s after (3.96 s on a repeat) over the
  same four shards on the Mac CPU, the same 4,050 rows kept (row-id list sha256 `97655a80...`), identical output files
  (sha256 above).
- Step-1 writeback on the CPU log: at the first warmup learning rate (1e-5) fp32 storage kept every update to the
  watched tensor, bf16 storage would have kept about 8% (0.082 in A2, 0.079 in A4); the job keeps fp32 weights and optimizer state for that reason.
- Training, evaluation and the RL screen are the existing `sft_g5.py` and `day_one_probe.py` paths (no new per-token or
  per-expert Python loops). Changes to them are opt-in and off by default, so the merged probe (#558) runs unchanged:
  `sft_g5.py --no-before`, `--rl-seconds`, `--gen-seconds`; `day_one_probe.rl_screen_bundle(seconds=0)` and per-prompt
  counts (task id, passes, programs that ran, samples with a code fence; no text).
- What the CPU log does not prove: any timing, memory or learning on dry run 1, and the quality of either arm. Memory
  (estimate, not measured): fp32 AdamW full fine-tuning of 237M parameters is about 3.8 GB plus one 2,048-token
  microbatch with 32,768-entry logits, within one 24 GB GPU.

## Update 18 Nov: what `<G5>` must be, and a wrong one now stops in seconds

- `<G5>` must be a lab checkout whose four Team 5 files (`harness/train_week2.py`, `week2/model.py`, `week2/config.py`,
  `week2/artifacts.py`) have the same sha256 as the `sources` recorded in `<RUN>/manifest.json`. The adapter has always
  refused any other pair; before this update that showed up only after the slice was built (about 48 s on the CPU
  stand-in, minutes at full size) and the message named no remedy.
- The same comparison now also runs in the `pins` step. A mismatched pair stops the job in about 5 s, before any row is
  built, with exit 1, `failed_steps ["pins"]`, each differing file listed with the run manifest's hash and the `<G5>`
  hash, and the remedy (point `--g5-root` at a checkout with the manifest's hashes). A manifest with no `sources` is
  refused the same way. Nothing is relaxed: a matching pair runs as before, and the adapter's own check still runs later.
- Ask for TSAI: please pass as `--g5-root` the same harness tree you used for G7's restore jobs A and B (#573). Its
  result note (`teams/07-infrastructure/results/restore_dryrun1.md`, section 5) says you ran both on the real dry run 1
  checkpoint on 17 Nov, "the same setup as #475", exit 0 with no identity error, `final_model_sha256` equal to dry run 1;
  section 2 says `train_week2.py`'s `--resume` refuses a checkpoint whose identity hash differs from the current run. So a
  tree that matches the real checkpoint exists on your side. With any other tree this job now stops in seconds and prints
  both hashes. Current `main` drifts further from that tree (open G5 drafts #606 and #607 change `train_week2.py` and
  `week2/model.py` again), which is why the early stop matters.
- What we cannot see: the real run's `manifest.json["sources"]` is not in the repo (the committed dry run 1 manifest under
  `teams/05-architecture/jobs/evidence/2026-11-15-dryrun1/` is G5's CPU smoke, whose `train_week2.py`, `artifacts.py`,
  `evaluation.py` and `data.py` hashes match no committed blob), and the G7 job outputs were not added to the repository.
  So we do not know which commit that tree is; the sha256 of the four files in the real manifest would let us name it.
