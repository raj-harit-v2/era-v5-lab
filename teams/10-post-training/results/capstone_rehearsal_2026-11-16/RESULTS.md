> Local `private/`, `logs/` and script paths below refer to the original experiment workspace; public validation is attached under `teams/10-post-training/jobs/evidence/2026-11-16-g10-capstone-rehearsal/`.

> Publication update, 16 November 2026: the instructor now reports #475 completed with p1536 and a final checkpoint at TSAI. The local findings below describe harness `ae4c03d`; the actual probe must use the source checkout and artifacts recorded by #475. CUDA/T2 and vLLM remain unmeasured by G10. No checkpoint access is assumed.

# Capstone rehearsal: G10 post-training on Team 5's model family (16 Nov 2026)

**Scope label for every number here.** Stand-ins A and B are capstone-family models we trained on an M1 Pro with Team
5's own trainer: same code path (KE2 byte-code input, GQA + RoPE, SwiGLU MoE with a shared expert and top-2 loop
dispatch, dense untied 131,072-row head, Muon), far smaller and far less trained than dry run 1. Numbers from them
are **mechanics, costs and relative comparisons, never quality claims**. One pre-training seed; SFT comparison repeated with two seeds. Preregistration:
`PREREG_rehearsal_2026-11-16.md` (written 05:26, before any B measurement).

| | A (tiny) | B (small) | dry run 1 (T2, from the chats) |
|---|---|---|---|
| d_model / layers / heads / KV heads | 64 / 2 / 4 / 2 | 128 / 4 / 4 / 2 | 512 / 8 / 8 / 2 |
| experts (routed + shared, top-k) / expert FFN | 4+1, top-2 / 128 | 16+1, top-2 / 256 | 16+1, top-2 / 768 |
| context | 128 | 256 | 2,048 |
| parameters | 9.18M (8.4M head) | 24.7M (16.8M head) | ~233M |
| optimizer | Muon 0.01 / AdamW 1e-3 (T2's) | same | same |
| tokens seen | 40 steps x 1k | 4.1M scored (1,141 steps x 16 x 256) | ~20M (1,221 x 8 x 2,048) |
| data | local permissive Python + Dolly pre-training half | same | TSAI-staged bundle |
| precision / device | fp32, MPS | fp32, MPS | bf16 autocast, GPU |

Distance from dry run 1: about 10x fewer parameters, 8x shorter context, a few times fewer tokens, different data,
no Indic text (so B's Indic slices get worse with training). What is the same: every line of model, loader,
optimizer and evaluation code (Team 5's, unmodified, at lab main `ae4c03d`).

---

## Phase 1: our own capstone-family run folders

What ran
- p1536 KE2 raw table built with Team 4's `src/build_tables.py`: format v2, P32, 131,072 unique rows, 0 truncated,
  content sha256 `21072027b19e…`. Team 5's `Artifacts` accepts it once its tokenizer pin is overridden.
- Pre-training text `private/pretrain/train_v1.jsonl` (sha256 `88aea0f2…`): 3,540 permissively licensed `.py` files
  (41.9 MB, licences checked per distribution) and 7,609 Dolly rows (6.0 MB, only the pre-training half by id hash;
  the other half is SFT data). 5 of 11,151 documents needed handling for exact byte round-trip (3 NFC, 2 dropped).
- Held-out: Team 5's heldout_v1, a 255-document subset with all 15 slices (`artifacts/heldout_v1_bal60k.jsonl`).
- Launcher `capstone/g5_launch.py` runs Team 5's unmodified `train_week2.py` with exactly these recorded patches
  (`G10_LAUNCH.json` in each run folder): tokenizer-identity default → p1536; `mps` added to the device choices;
  float64 copies of MPS tensors made on CPU (exact); deterministic algorithms `warn_only` on MPS (no deterministic
  MPS kernel for the KE2 backward, so MPS runs are not bit-reproducible). Config overlay (`g5_overlay/`): Team 5's
  `runtime.yaml`, `t2.yaml`, `exp2_muon.yaml`, `plan_v1.md` copied unchanged + our size-only arms.
- A: 40 steps, CE 11.97 → 8.97, 73 s (MPS). B: 1,141 steps in 105 min (time cap; mean 5.3 s/step on a loaded
  machine), train CE 11.94 → 3.53, checkpoint sha256 `68ab2426…`, final model hash `30e536be…`, status SMOKE.

B held-out bpb curve (Team 5's evaluate, every 50 steps; code/en/math slices; aggregate rises because Indic slices,
absent from the training text, get worse):

| step | all | code | en | math | sci | hi |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2.479 | 4.280 | 3.765 | 4.646 | 3.356 | 1.965 |
| 100 | 2.196 | 3.039 | 2.666 | 3.154 | 2.413 | 1.984 |
| 500 | 2.270 | 2.791 | 2.364 | 2.819 | 2.155 | 2.195 |
| 1,000 | 2.184 | 2.712 | 2.271 | 2.710 | 2.085 | 2.117 |
| 1,100 | 2.340 | 2.746 | 2.258 | 2.701 | 2.093 | 2.369 |

"Clearly non-trivial" here means the code slice fell from 4.28 to 2.71 bits per byte and English from 3.77 to 2.26;
dry run 1 is reported at 1.66 aggregate (T2, Gate 2 table), so B is far weaker.

What broke
1. **Team 5's trainer refuses the frozen tokenizer**: `artifacts.py` pins tokenizer v0 (`2de039f2…`) by default.
2. **heldout_v1 does not load under the frozen tokenizer**: all 74 bn/pa/as documents fail Team 5's exact byte
   check under C3 and p1536 (the normaliser composes nukta forms, e.g. য + ় → য়). Our subset carries the 18 affected
   documents in normalised form, recorded in `heldout_v1_bal60k.note.json`.
3. Team 5's trainer is CUDA/CPU only; MPS needed the three launcher patches above. Not a defect for TSAI GPUs.
4. Throughput on this machine: d128 SFT/pre-training ~2,300 tok/s on MPS with micro-batch 8; T1/T2 shapes swap on
   16 GB unified memory (T2-like at T=512: 58 tok/s), so the largest useful laptop stand-in is d128.

Also produced: `capstone/kaggle_t4.py` (2x T4: T2 dims at the dry-run-1 token budget in fp32 + T1, then two SFT arms
with RL screens), `make_kaggle_bundle.sh`, job-request drafts in `jobs_draft/`. The whole Kaggle pipeline ran as a
CPU dry run at tiny size (`logs/kaggle_dry4.log`); the Hugging Face streaming step did not run here (it downloads).

## Phase 2: the adapter

- New `run_folder` mode in `rl-loop/team5_adapter.py`: builds the bundle from what `train_week2.py` wrote. Checks:
  manifest/checkpoint hashes, the manifest's source hashes equal the pinned import, G5 `validate()` on the manifest's
  config, tokenizer and KE2 content equal the manifest's, checkpoint identity equals the manifest's, and G5's
  `model_hash` of the loaded weights equals `summary.json`. Origin `g10_rehearsal` → `REHEARSAL_READY` (never a
  learning report); `g5_delivery` needs a non-smoke manifest and a probe NLL → `READY`. Also a no-git hash pin for
  bundles (every harness file hashed).
- The "about 25 skipped Team 5 tests" were skipped for two missing inputs that were on disk all along (the baseline
  tokenizer `01d968a7…` and the 25 MB OLMoE shape checkpoint `0bd7ae87…`). With them set: **27 passed, 1 skipped**
  (math_verify not installed) before today's additions; one of them had gone stale unnoticed (durable trainer state
  added `evals.jsonl`; fixed).
- Real run folders A and B build `REHEARSAL_READY`; G5's model hash equals `summary.json` (A `326f0721…`).

## Phase 3: SFT on Team 5's model

Mechanics (A, then B): `capstone/sft_rows.py` re-tokenises G10 chat-format rows with p1536 and the converter's own
`token_mask` rule; `capstone/sft_g5.py` trains full / LoRA / DT / markers through a thin wrapper so the bench's loss
contract, LoRA module, DT module, writeback check and schedule run unchanged.

Checks on real rows (all passed on A and B): labels equal the mask shifted by one; the loss equals the masked sum of
per-position NLL from full logits; noise added to logits at masked positions leaves the loss bit-identical; the
assistant header is never supervised; `<|im_end|>` targets are supervised. Step-1 writeback: FP32 storage moves 100%
of entries; **BF16 storage would have kept 43% of the update** (A, q-matrix, lr 1e-4). Frozen-weight hash unchanged
for every non-full method; reload of the saved G5 state dict reproduces logits exactly.

What did not hold on G5 and was ported
- DT's target sets (`gate_proj` substrings) match nothing in G5, and a substring `o` matches everything; anchored
  `g5_gate / g5_mlp / g5_attn` sets added to `dt/mask.py`.
- DT's Wanda calibration crashed on G5 experts: routed experts receive gathered `[routed tokens, d]` rows and shared
  experts receive all flattened `[B*T, d]` rows (padding included, zeroed afterwards). The hook now drops padding
  for `[B,T,d]` and `[B*T,d]` inputs and uses gathered rows as they are; a test checks a padded batch gives the same
  Wanda norms as the rows calibrated separately.
- There are no per-token input embedding rows in KE2 (one shared projection of each token's byte code), so the
  marker control can only train **output-head** rows. On this architecture the R8 finding (output-side rows matter)
  is not a choice but the only option; the input side of a marker is fixed by its bytes `<|im_end|>`.
- G5's experts are per-expert `nn.Linear` in a `ModuleList` (loop dispatch), so DT and LoRA wrap them as is. If the
  capstone moves to G6's packed `[E, …]` expert tensors, both need a 3-D variant (gap, not built).

Data lengths that matter for capstone SFT: under p1536, **13.9% of OCR-2 rows fit 2,048 tokens** (16,054 rows from
shards 0-1; median 5,506; p90 13,084), Dolly 99.8%.

B comparison (P3, preregistered):

300 steps x 16 Dolly SFT-half rows, seed 1, same rows and schedule for every arm, CPU (MPS rebuilds kernels for
every new batch shape: 85 s for SFT step 1 on MPS vs 1.0 s on CPU). 64 unfiltered eval prompts, greedy, 48 new tokens.
"Closed" = the reply ends with `<|im_end|>` and render.py parses the transcript.

| arm (trainable) | eval NLL/target, seed 1 / 2 | closed turns, seed 1 / 2 | held-out bpb code / en, seed 1 (base 2.738 / 2.248) | BF16 would keep of step-1 update | checks (both seeds) |
|---|---|---|---|---:|---|
| base (no training) | 6.835 | 0 / 64 | 2.738 / 2.248 | - | - |
| full (24.7M) | 6.232 / 6.231 | **53 / 46** | 2.725 / 2.199 | 17% | mask, writeback, reload |
| markers only (9 head rows) | 6.623 / 6.623 | 11 / 11 | 2.738 / 2.253 | 22-23% | + frozen hash |
| LoRA r16 (1.31M) | 6.449 / 6.450 | **0 / 0** | 2.752 / 2.222 | 100% (adapter) | + frozen hash |
| LoRA r16 + markers | 6.326 / 6.327 | **57 / 52** | 2.761 / 2.221 | 100% (adapter) | + frozen hash |
| DT on every expert's gate/up/down (6.7M gate logits) | 6.475 / 6.476 | **0 / 0** | 2.734 / 2.226 | 65% (gate logits) | + frozen hash, 5.5% deleted |

Seed 2 (16 Nov midday, same rows, steps and settings, different batch order; `private/sft_b_seed2/`) changes no
ordering: arms without head rows close no turn in either seed; LoRA + head rows is at or above full fine-tune in both.
Held-out bpb for seed 2 is within 0.003 of seed 1 for every arm.

Reading (two seeds; a difference of ~8 of 64 is inside binomial noise):
- Preregistered H-a holds: the turn-closing marker is learned through the output-head rows. LoRA and DT lower the
  eval NLL more than the markers control does, yet close no turn; adding the nine head rows to LoRA closes 57 of 64.
  Teacher-forced loss would have ranked LoRA above markers-only, the opposite of generation (the R3 lesson, again).
- No arm forgets: code and English held-out bpb move by at most 0.03 (full improves English by 0.05).
- What "closed" does not mean: full FT's replies are degenerate ("The following are the most popular of the world."
  is 16 of the 64 replies). A constant string ending in `<|im_end|>` would score 100% on this check. It measures that
  the chat structure is learnable on this model class, not answer quality.
- DT on MoE: 30 of 204 masked expert layers saw no calibration token, so they start without a Wanda prior and their
  random gate logits delete ~half their weights under the hard mask (deletion at init 11.7% vs the 5% prior). A
  per-expert calibration floor (or prior = keep for unseen experts) is needed before DT is used on the capstone.
- The RL screen after full SFT (24 easiest-rung prompts x 8): still 0 passes, 0 code fences: Dolly teaches no code.

## Phase 4: RL on Team 5's model

- **GRPO review, literally, on G5** (`test_team5_adapter.py`, real run folder → adapter policy → `train.train`):
  constant and singleton groups return `None` from the real advantage function; a mixed group gives [-0.5, 0.5,
  -0.5, 0.5]; constant groups never reach the backward or the token denominator; adding a dropped group leaves the
  loss, weights and AdamW moments of the mixed groups unchanged; an all-dropped batch (constant, then singleton)
  never steps the optimizer and creates no state. All pass.
- **Stalled learning**: at lr 1e-6 a bf16-stored G5 model loses the update (stored change < 1% of entries with a
  nonzero gradient; the trainer raises "lost update"); with FP32 masters the update is kept. At 1e-9 even FP32
  cannot hold the step for head rows of magnitude ~0.25 (ulp ~1.5e-8).
- Fixed on the way: (1) `Team5Policy.sample` ran outside the trainer's autocast (sampler and trainer in different
  precisions; a bf16 G5 model crashed while sampling); (2) a G5 checkpoint is fp32, so `fp32_master` converts nothing
  and the trainer ran G5 entirely in fp32: new `train.autocast: bf16`; (3) bf16-stored G5 weights only run under
  autocast (KE2 returns fp32 by design).
- **Sampler**: `LanguageModel` has no KV cache. `Bundle.sample` also projected every position through the 131,072-row
  head on every step; it now projects the last position only. New `rl-loop/g5_decode.py`: KV-cached decoding from
  Team 5's own modules (only the attention arithmetic re-implemented; local/sink/gate layers refused); per-position
  logits within 1e-4 of Team 5's forward; greedy and temperature-1 samples identical to the re-forward path (CPU).
  Before/after on A (CPU, k=8, prompt 64, 64 new, greedy, identical tokens): 42.1 → 102.0 (head) → 682.8 (KV) new
  tokens/s. On B (k=8, prompt 128, 128 new, greedy; identical tokens on every path):

| device | before (full head each step) | last-position head | KV cache |
|---|---:|---:|---:|
| MPS | 8.7 | 163.8 (18.8x) | 258.6 (29.6x) |
| CPU | 38.9 | 108.4 (2.8x) | 947.6 (24.3x) |

On MPS the old loop's cost was mostly the [8, L, 131,072] logits written at every step; on CPU the quadratic
re-forward dominates. At T2 width and 1,024-token completions the gap grows (re-forward is quadratic in length).
- **Save, kill, resume** (A, toy task, KV sampler, 8 steps, state every step): SIGKILL after step 3's state, resume
  → with one thread, bit-identical to the uninterrupted run (and two uninterrupted runs are bit-identical); with
  default threads two uninterrupted runs already differ by ~1e-7 relative in loss from step 2, and the resumed run
  sits inside that floor (same samples and rewards at every step).
- **Numerics-only trust-region firing** (`capstone/mismatch_g5.py`, real G5 routing read by recomputing G5's own rule
  on each MoE's input). B, 24 Dolly eval prompts x 8 samples x 96 new tokens = 18,432 sampled tokens, same weights,
share of tokens with ratio outside [0.8, 1.2] / share of (token, layer) pairs whose top-2 expert set differs:

| pair | MPS | CPU |
|---|---|---|
| fp32, 8 rows in one forward vs 1 row | 0 / 0 | 0 / 0 |
| bf16 autocast vs fp32, 1 row | **0.109% / 0.225%** | 0.174% / 0.263% |
| bf16, 8 rows vs 1 row | 0.005% / 0.010% | 0 / 0 |
| same forward twice | 0 / 0 | 0 / 0 |

On OLMoE (R2) the same probe gave 2.04% outside and 44.8% expert-set flips (8 rows vs 1). On G5 the batch-shape
effect almost vanishes, consistent with G5 computing the router in fp32 with autocast off (model.py). The precision
effect (a bf16 sampler against an fp32 trainer, or the reverse) is ~0.1-0.2%: at the threshold where WORKING_PLAN
section 6 says act. Flips grow with depth (MPS: 19, 56, 97, 78 per layer). With the native sampler this is moot (the
trainer recomputes sampler log-probs itself, ratio exactly 1 at epoch 1); it matters only for a vLLM sampler in bf16
against an fp32 or differently-batched trainer. CUDA kernels were not measured.
- **One step, profiled**: two runs on B, CPU, objective_v1, 8 prompts x k 8, KV sampler, 4 steps each (`rl/b_*_cpu`):

| run | step time | sampling | scoring | old log-probs | backward + update | optimizer stepped |
|---|---:|---:|---:|---:|---:|---|
| stdio, easiest rung (prompt <= ~180, 72 new) | 13.5 s | 13.5 s (100%) | 0.003 s | - | - | never (8/8 groups all-zero, 4 steps) |
| toy parity (prompt 128, 96 new) | 24-26 s | 16 s (64%) | ~0 | 2 s (8%) | 6-7 s (27%) | every step; stored-update share ~0.95 |

  Sampling is the limiting part even with the KV cache (at 340-390 sampled tokens/s here). Scoring cost was not
  measured: no completion contained a code block, so stdio_check returned before running anything; on the 15 Nov
  surrogate runs scoring was the bottleneck once programs ran (R1). The stdio run is also the end-to-end check that
  the verifier path, codec and docker sandbox work on G5 output (and that a model with no signal never steps).
- vLLM: G12's `export_hf.py` (Granite MoE Shared, PR #14 on `SreekanthZipsy/era-v5-lab` branch `G12-Week3`) is the
  only route; tested by G12 on a random checkpoint only. Not reachable from here today.

## Phase 5: what such a model can learn from

Re-analysis of saved screens (`capstone/screen_ladder.py` → `phase5_ladder.json`; counts only), RL data v1 code pool
(3,577 prompts), k = 8:

| model (screen) | prompts | pass rate | mixed groups | pool-reweighted mixed share |
|---|---:|---:|---:|---:|
| OLMoE-1B-7B-0924-Instruct (12 Nov survey) | 32 | 4.7% | 12.5% | 7.4% |
| Qwen2.5-Coder-1.5B-Instruct (WP5) | 64 | 2.5% | 10.9% | 10.2% |
| Qwen2.5-Coder-7B-Instruct (WP5) | 64 | 11.3% | 34.4% | 30.9% |
| Qwen2.5-Coder-7B-Instruct (E1) | 192 | 10.6% | 29.2% | 24.4% |
| Qwen3.6-35B-A3B-FP8 (12 Nov survey) | 32 | 40.6% | 34.4% | 38.5% |

- The `difficulty` field does not stratify: 87% of the pool is difficulty 0.
- Statement length does. For the weak models every gradient-carrying group was in the shortest third (≤ 310
  statement tokens): 1.5B short 25% mixed, mid and long 0%; OLMoE short 25%, mid/long 0%; 7B short 51-64%, long 5-7%.
- Judge: aizu (52% of the pool) gives the weak models almost nothing (1.5B: 0 of 31); codechef/hackerearth carry most
  of the signal.
- A from-scratch capstone at dry-run-1 scale (233M, ~20M tokens) sits far below the 1.5B coder (trained on trillions
  of tokens, then instruction-tuned), which itself gets gradient on ~10% of the pool. Prediction: ~0% on RL data v1.
- Easiest rung built only from admitted fields: pool ∩ {codechef, hackerearth} ∩ statement ≤ 310 tokens = 754
  prompts (95 of them ≤ 160 prompt tokens fit B's context).
- **B on the easiest rung** (95 prompts that fit B's context, k = 8, 96 new tokens, temperature 1, docker-isolated
  stdio_check): 0 of 760 samples pass; every failure is "no code block" (7 samples contain a code fence, none a
  parseable Python block). The base model also closes 0 of 64 chat turns with `<|im_end|>` (greedy, 64 tokens).
  So the binding constraint is format, not problem-solving: nothing the RL objective does can start until the model
  emits a closed turn with a code block.

What this implies for the order of work: see the dated section in WORKING_PLAN.md.

## What could not be tested here, and the cheapest way to test it

| Not tested | Why | Cheapest test |
|---|---|---|
| Anything at dry-run-1 width, context 2,048, bf16 on GPU | no GPU, 16 GB RAM | `capstone/kaggle_t4.py` on Kaggle 2x T4 (free), or the TSAI probe job |
| Batch-shape numerics on CUDA kernels (R2's main effect on OLMoE) | CPU/MPS kernels differ | day-one probe `mismatch` step on the real checkpoint |
| Hub streaming in the Kaggle script | would download data here | first cell on Kaggle |
| vLLM sampling of the G5 model | needs G12's export on a trained checkpoint | G12 ask (DEFECTS item 7) |
| SFT on code rows | no OCR-2 row fits B's 256 context | Kaggle T2 OCR-2 arm (in the script) |
| RL learning on real prompts | B solves nothing; the real model probably won't either before SFT | Kaggle after the OCR-2 SFT arm, then the TSAI job |

## Publication review, 16 November 2026
The probe now writes a terminal summary and exits nonzero after any failed step, while continuing independent checks. SFT-arm model files and generations are removed on ordinary failure as well as success. TSAI must enforce the 60-minute global deadline; the per-arm limits are not total-job limits. New failure-path tests and an end-to-end reduced CPU run are attached under `jobs/evidence/2026-11-16-g10-capstone-rehearsal/`. DT unseen-expert initialization remains an explicit limitation, not fixed by this PR.
