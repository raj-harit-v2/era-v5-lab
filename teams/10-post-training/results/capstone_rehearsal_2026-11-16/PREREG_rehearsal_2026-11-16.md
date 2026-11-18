> Local `private/`, `logs/` and script paths below refer to the original experiment workspace; public validation is attached under `teams/10-post-training/jobs/evidence/2026-11-16-g10-capstone-rehearsal/`.

> Publication update, 16 November 2026: the instructor now reports #475 completed with p1536 and a final checkpoint at TSAI. The local findings below describe harness `ae4c03d`; the actual probe must use the source checkout and artifacts recorded by #475. CUDA/T2 and vLLM remain unmeasured by G10. No checkpoint access is assumed.

# Preregistration: capstone-family rehearsal measurements (16 Nov 2026, written 05:26 IST)

Written before any Phase 3–5 measurement on stand-in B. Seen so far: mechanics smoke runs on the tiny stand-in A
(d64, 40 pre-training steps; SFT 3–6 steps per method), which only show that the code paths execute, and B's
pre-training curve to step 150 (held-out code-slice bpb 4.28 → 3.04). Every number below comes from a model of ~22M
parameters (mostly the 131,072-row head) trained for under two hours on ~4–6M tokens on an M1 Pro. **None of it
transfers to the dry-run-1 model as a quality number** (T2: d512, 8 layers, 16+1 experts, ctx 2048, ~20M tokens, bpb
~1.66 by the Gate 2 table). What should transfer: whether code runs, which checks fire, relative cost of the parts of a
step, and whether a method's mechanism engages on G5's module layout.

## P3. SFT methods on Team 5's model (full, LoRA, DT, markers control)

Question: does each method train on G5's layout (KE2 input, untied head, per-expert `nn.Linear` in a `ModuleList`),
and does format learning (closing `<|im_end|>`) need the output-head marker rows here as R8 found on SmolLM2?

Competing explanations and predictions
- H-a "format is in the head rows": markers-only control raises `closed_im_end` above base; DT and LoRA without head
  rows stay near base on `closed_im_end` even if their eval NLL falls; LoRA+markers ≈ full on `closed_im_end`.
- H-b "the body can carry it": LoRA alone reaches ≥ half of full's `closed_im_end`, markers-only does not move it.
- H-c "the model is too weak for any format": every arm, full included, stays at `closed_im_end` < 0.1. Then the
  comparison says nothing about methods; report it as a capability floor of this stand-in, not a method result.

Endpoint: on 64 held-out Dolly SFT-half eval prompts (unfiltered, greedy, 48 new tokens): `closed_im_end` and
`format_validity` (render.py parse), with the failure-reason table; secondary: masked eval NLL per target; forgetting
= pre-training held-out bpb (Team 5's evaluate) before vs after, code and en slices. Same rows, steps (300), batch
(16 rows), seed (1), warmup and schedule for every arm; lr 3e-4 full, 1e-3 LoRA (r16), DT per official schedule
(alpha 100→1000, lambda 1e-5, eta 0.05) on `g5_mlp`, markers lr 1e-3. One seed: differences under ~0.1 in a rate over
64 prompts are noise (binomial SE ≈ 0.06 at p = 0.5).

Decision it changes: whether DT / LoRA can be considered for capstone SFT without explicitly trainable head rows, and
what the day-one SFT recipe must include. Not changed by it: which method is best at full width.

Stop conditions: any arm with a non-finite loss, a failed writeback / frozen-weight / reload check, or a mask-check
failure is reported as a defect and not compared.

## P4. RL loop on Team 5's model

Q4a (mechanics): does `rl-loop/train.py` with objective_v1 run end to end with the adapter's native sampler, save,
resume bit-exactly after a kill, and pass the CLAUDE.md GRPO review (constant / singleton / mixed groups through the
real advantage function, dropped-group invariance of the update, all-dropped batch skips the optimizer)? Pass/fail per
check; any fail is a defect to fix in G10 code.

Q4b (stalled learning): a trainable weight before vs after one real step in its storage dtype, FP32 vs BF16 storage.
Prediction from the A-model SFT writeback (BF16 would keep 43% of a 1e-4 AdamW step on a d64 q-matrix): at RL learning
rates (1e-5 to 1e-6) BF16 storage would drop most of the update. Endpoint: fraction of entries moved, FP32 vs BF16.

Q4c (numerics-only trust-region firing): same weights, one prompt alone vs inside a batch of k, FP32 vs BF16 compute.
Explanations: (i) G5's router is computed in FP32 with autocast disabled (model.py), so BF16 near-tie flips (R2b on
OLMoE) should mostly vanish and the mask should fire on ≪ 0.1% of tokens; (ii) the rest of the block in BF16 still
moves router inputs enough to flip top-2 choices and the mask fires in the 0.1–2% range like OLMoE. Endpoint: share
of sampled tokens with |log ratio| outside [log 0.8, log 1.2] and share of (token, layer) expert sets that differ,
batch-1 vs batch-k and fp32 vs bf16 autocast (CPU bf16 autocast if MPS lacks it; label the device). Decision: whether
the capstone RL run needs fp32 routing, routing replay, or nothing (WORKING_PLAN section 6 thresholds: < 0.1% nothing).
Does not transfer: absolute rates at d512 with 16 experts and trained weights; re-measure on the real checkpoint.

Q4d (where time goes): profile one RL step (sampling, scoring, forward/backward) and sampling tokens/s with and without
a KV cache. `LanguageModel` has no cache in Team 5's code; a G10-side cached decode would be new code and is only
built if sampling is the dominant cost.

## P5. What a model at this capability can learn from

Re-analysis of saved private screens (no new sampling first): pass rate and share of mixed-reward groups by
difficulty field, judge and statement length for the 7B and 1.5B screens. Explanations for why groups carry no
gradient: (i) all-fail because tasks are too hard for the model (predicts: mixed share rises steeply as model size
grows and as difficulty falls); (ii) all-fail because of format / parse failures (predicts: failure reasons dominated
by no-code / parse errors, not wrong answers). Endpoint: mixed-group share by rung; estimated fraction of RL data v1
with ≥ 1 success at k = 8 per capability level. Then a screen of stand-in B on the easiest rung (expected: 0 passes;
the interesting quantity is the failure-reason mix, i.e. whether the model even emits a code block).

Decision it changes: the order of SFT vs RL work for the capstone and which RL data to build first.
Does not transfer: absolute pass rates of a from-scratch capstone model at 20M+ tokens; only the shape of the
dependency (format first, then attainable tasks).

Cost cap: local CPU/MPS only, $0. No paid compute. Stop if the machine's swap is exhausted (it was 97% used at 05:12).
