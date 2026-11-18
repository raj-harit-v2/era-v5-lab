# Deletion Tuning vs LoRA vs full fine-tuning on the SFT bench (WP2 draft, 14 Nov 2026)

**Evidence level: surrogate, exploratory.** Dense SmolLM2 (Apache-2.0), AdamW, one OCR-2 code slice. Nothing here measures
the capstone MoE, Muon or KE2. **Data provenance is conditional** on WP1 (draft #79: the 14 WP11 source spot checks
remain open; TSAI has now confirmed keeping the 2% held-out split). The main table uses the bench `slice-v1` test split. It was already scored in WP3, so every
number on it is **exploratory**. A small fresh supplement (91 rows, 22 problem clusters, below) gives limited
independent corroboration. It is not a confirmatory or official result. Settings were chosen on the dev split only. The
preregistration and its three amendments were written and hashed before the corresponding scores existed.

## What was compared

| Item | Value |
|---|---|
| Models | SmolLM2-135M @ `93efa2f0`, SmolLM2-1.7B @ `effd688a`, SmolLM2-1.7B-Instruct @ `31b70e2e` (same tokenizer, sha256 `9ca9acdd…`). 360M was not run |
| Data | bench slice-v1: train 2,509 rows / 531 clusters; dev 300 rows / 78 clusters; test 300 rows / 110 clusters. Rows ≤ 2,048 tokens, split by near-duplicate problem cluster |
| Steps | 400 optimizer steps × 8 rows for every arm; same order, loss (global-count mean over masked targets), warmup 20 + cosine, AdamW (0.9, 0.95), wd 0, clip 1 |
| Precision | FP32 master weights, BF16 autocast for training (CUDA), FP32 evaluation with TF32 off |
| full FT | every weight, LR 1e-4 |
| LoRA | r 4, alpha 8, q k v o gate up down; LR 1e-3 selected by our WP3 dev sweep |
| DT (pure) | one FP32 logit per `gate_proj` weight; W·sigmoid(αG) in training, W·1[G>0] (baked) for every evaluation; α 100→1000; Wanda prior η = 1/2048 on 64 train rows; λ 1e-5 decaying to 0; bias kept. LR 2e-3. Port of the official code (`dt/mask.py`) |
| DT+m (**hybrid**) | DT plus the 5 embedding rows of the mapped chat markers (ids 0, 1, 2, 15, 16; tied with the LM head) trained at LR 1e-4. Not pure DT: it writes 5 × hidden float values |
| LR choice | dev target bpb at 135M, seed 1, then frozen for every size. full {3e-6, 1e-5, 3e-5, 1e-4}, LoRA {1e-4, 3e-4, 1e-3} (WP3). DT {3e-4: 0.5728, 5e-4: 0.5545, 1e-3: 0.5413, 2e-3: **0.5386**}. All three winners are the largest value tried, so the optimum may be higher |
| Seeds | 135M full FT 3 seeds; every other arm 1 seed (seed 1) |
| Hardware | 135M train and test eval: Modal A10. 1.7B: Modal L40S. Supplement: L40S (1.7B), Mac M1 Pro CPU (135M) |

## Results on the slice-v1 test split (exploratory)

Format = greedy reply on 110 prompts (one per cluster) that closes with `<|im_end|>` and parses as one assistant turn.
Exec = pass@1 on the first 100 prompts; "validated" counts only the 69 of those whose own reference solution passes all of
its tests in the sandbox (decided from the data before any WP2 model generated). Forgetting = bits per byte on G5 held-out v1.

| size | start | arm | test bpb | format valid (95% CI) | exec all / validated | held-out v1 bpb (Δ vs base) | DT deleted (gate / all weights) |
|---|---|---|---|---|---|---|---|
| 135M | base | untrained | 0.8148 | 0/110 | 0/100 / 0/69 | 1.0981 | |
| 135M | base | full FT (3 seeds) | 0.4836 (0.4835-0.4837) | 81-87/110 (mean 76.7%) | 1-2/100 | 1.1489 (+0.0508) | |
| 135M | base | LoRA | 0.5283 | 0/110 | 0/100 | 1.1365 (+0.0384) | |
| 135M | base | DT | 0.5321 | 0/110 | 0/100 | 1.1260 (+0.0279) | 3.22% / 0.63% |
| 135M | base | DT+m (hybrid) | 0.5287 | 63/110 (48-66%) | 1/100 / 1/69 | 1.1276 (+0.0295) | 3.21% / 0.63% |
| 1.7B | base | untrained | 1.0490 | 0/110 | 0/100 | 0.8434 | |
| 1.7B | base | full FT | 0.3332 | 93/110 (77-90%) | 21/100 / 20/69 | 0.9180 (+0.0746) | |
| 1.7B | base | LoRA | 0.3500 | 84/110 (68-83%) | 18/100 / 17/69 | 0.9121 (+0.0687) | |
| 1.7B | base | DT | 0.3698 | 0/110 | 0/100 | 0.8597 (+0.0163) | 1.32% / 0.31% |
| 1.7B | base | DT+m (hybrid) | 0.3633 | 76/110 (60-77%) | 13/100 / 13/69 | 0.8525 (+0.0091) | 1.25% / 0.29% |
| 1.7B | instruct | untrained | 0.5815 | 107/110 (92-99%) | 13/100 / 13/69 | 0.9061 | |
| 1.7B | instruct | full FT | 0.3284 | 91/110 (75-89%) | 22/100 / 22/69 | 0.9463 (+0.0402) | |
| 1.7B | instruct | LoRA | 0.3409 | 8/110 (4-14%) | 0/100 | 0.9251 (+0.0190) | |
| 1.7B | instruct | DT | 0.3556 | 0/110 | 0/100 | 0.9115 (+0.0054) | 1.22% / 0.29% |
| 1.7B | instruct | DT+m (hybrid) | not run (budget) | | | | |

Ratios against full FT of the same size and start (gain = untrained bpb − arm bpb). Format p values: exact paired
McNemar against full FT seed 1 on the same 110 prompts.

| size | start | arm | bpb-gain ratio | format ratio | Δforgetting ratio | rule 1 "viable" (format ≥ 0.9×, gain ≥ 0.8×) |
|---|---|---|---|---|---|---|
| 135M | base | LoRA | 0.865 | 0.00 | 0.76 | no |
| 135M | base | DT | 0.854 | 0.00 | 0.55 | no |
| 135M | base | DT+m (hybrid) | 0.864 | 0.75 (13 vs 35 discordant, p = 0.002) | 0.58 | no |
| 1.7B | base | LoRA | 0.976 | 0.90 (6 vs 15, p = 0.078) | 0.92 | yes, barely (one seed) |
| 1.7B | base | DT | 0.949 | 0.00 | 0.22 | no |
| 1.7B | base | DT+m (hybrid) | 0.958 | 0.82 (7 vs 24, p = 0.003) | 0.12 | no |
| 1.7B | instruct | LoRA | 0.951 | 0.09 | 0.47 | no |
| 1.7B | instruct | DT | 0.893 | 0.00 | 0.13 | no |

Format failure modes (counts of 110): pure DT 135M: 110 run to the 2,048-token budget; pure DT 1.7B base: 65 emit a
foreign special token, 37 run to the budget, 8 miss the think-close marker; pure DT 1.7B-Instruct: 87 foreign special
token, 23 budget; LoRA 1.7B-Instruct: 82 foreign special token; LoRA 135M (WP3): `<|im_end|>` as the first token on all 110.

## Fresh supplement `heldout-sup-v1` (evaluation only; 22 clusters)

91 rows from the WP1 proposed `heldout_eval_v1` rows of pack shards 0-3: 22 families = 22 near-duplicate clusters,
0 overlap with slice-v1 at cluster, family, question hash and OCR question id, and 0 families shared with the shards 0-3
training packs. Never trained on and never used for any choice. 22 prompts, 22 exec tasks (13 validated: the reference
passes). With 22 clusters a difference of a few prompts is not interpretable.

| size | start | arm | bpb | format | exec all / validated |
|---|---|---|---|---|---|
| 135M | base | untrained | 0.8296 | 0/22 | 0/22 / 0/13 |
| 135M | base | full FT s1 / s2 / s3 | 0.4853 / 0.4855 / 0.4858 | 17 / 13 / 17 of 22 | 1 / 2 / 1 of 22 |
| 135M | base | LoRA | 0.5289 | 0/22 | 0/22 |
| 135M | base | DT | 0.5328 | 0/22 | 0/22 |
| 135M | base | DT+m (hybrid) | 0.5291 | 9/22 | 0/22 |
| 1.7B | base | untrained | 1.0604 | 0/22 | 0/22 |
| 1.7B | base | full FT | 0.3360 | 16/22 | 3/22 / 3/13 |
| 1.7B | base | LoRA | 0.3493 | 12/22 | 2/22 / 2/13 |
| 1.7B | base | DT | 0.3691 | 0/22 | 0/22 |
| 1.7B | base | DT+m (hybrid) | 0.3615 | 14/22 | 2/22 / 2/13 |
| 1.7B | instruct | untrained | 0.5903 | 18/22 | 1/22 / 1/13 |
| 1.7B | instruct | full FT | 0.3329 | 12/22 | 3/22 / 3/13 |
| 1.7B | instruct | LoRA | 0.3427 | 1/22 | 0/22 |
| 1.7B | instruct | DT | 0.3572 | 0/22 | 0/22 |

The supplement agrees with the test table in every direction that the test table shows clearly (bpb order, pure DT
format 0, LoRA-Instruct collapse, DT+m recovering most of the format). It is too small to say anything about the smaller
differences (for example LoRA vs DT+m at 1.7B base).

Cluster bootstrap of paired bpb differences on the supplement (135M only; 10,000 resamples of the 22 clusters, seed 0;
per-row NLL recomputed on the Mac CPU with the evaluator's loss, totals equal to the table): DT − full FT s1 +0.0475
[+0.0417, +0.0527]; DT+m − DT −0.0036 [−0.0041, −0.0032]; LoRA − DT −0.0039 [−0.0060, −0.0015]; DT+m − LoRA +0.0003
[−0.0021, +0.0022] (not resolved); full FT s2 − s1 +0.0001 [−0.0011, +0.0012]. The additional collection below supplies the corresponding 1.7B intervals.

## Hypotheses (preregistered; one seed at 1.7B, so none of these is settled)

- **H1 (stage), not supported.** Pure DT's bpb-gain ratio is 0.949 from base and 0.893 from Instruct, so DT recovers a
  *smaller* share from Instruct, the opposite of H1's direction. On format pure DT is 0 from both starts. One seed each.
- **H2 (scale), consistent but weak.** Pure DT's bpb-gain ratio rises from 0.854 (135M) to 0.949 (1.7B base). Two sizes,
  one 1.7B seed, 360M missing.
- **H3 (forgetting), observed threshold met at 1.7B, not at 135M.** DT's Δ held-out v1 bpb is 0.22× (base) and 0.13× (Instruct) of
  full FT's at 1.7B; 0.55× at 135M (the threshold is ≤ 0.5×). Low forgetting does not rescue a method that fails format.

## Decision rule (PLAN WP2, applied literally, separately for pure and hybrid)

**Pure DT:** rule 1 fails at every size and both starts (format validity 0 versus 81-93 valid replies out of 110 across full-FT arms/seeds). The bpb condition of
rule 2 is met (ratio ≥ 0.8 and rising, 0.85 → 0.95), but rule 2 presupposes a viable method, and a method that produces
no valid reply is not one. Rule 3 does not apply (base ratio is not < 0.5). **Verdict: evidence is split** (near-parity
target bpb and much less forgetting; total format failure). Pure DT as specified here (frozen embeddings, think markers on
untrained special ids) is **not** recommended for base→chat SFT on this evidence.

**Hybrid DT+m:** rule 1 fails at 135M (format 0.75×) and at 1.7B base (0.82×; bpb 0.96×; forgetting 0.12×). Instruct was
not run. **Verdict: split; promising but not viable by the preregistered bar**, and it is a hybrid, not pure DT.

**Next test named by the rule:** the capstone-family check (WP8) with the actual checkpoint and a development-validated marker protocol, or
the 3B point of PLAN §6 only if the stage question still needs it. A second seed at 1.7B for full FT, LoRA and DT+m
would show whether 76 vs 93 and 84 vs 93 are stable.

## What the format failure is (mechanism; development data)

- Measured: in SmolLM2-135M the embedding rows of ids 1, 2, 5, 7-16 are nearly parallel (|w15 − w2| = 0.047, norm 3.31);
  in 360M rows 15 and 16 are bit-identical; in 1.7B and 1.7B-Instruct row 15 is a trained token but row 16 (think-close)
  lies within 0.011 of untrained ids 5, 7, 10 and 12. The embeddings are tied, so these rows are also the output rows.
- Dev prompts (135M): every training reply starts with id 15. Pure DT puts p ≈ 0.035-0.038 on each of im_end, think and
  think-close (0.146 on specials in total) and the argmax goes to an ordinary token; DT+m picks think on 78/78 (p 0.97)
  after its marker rows separate (|w15 − w2| 0.047 → 0.358). Full FT behaves like DT+m.
- The matched marker-row intervention supports frozen marker/output-head adaptation as a limitation at 135M.
  Initial near-collinearity is a plausible contributor; this study did not isolate it from other benefits of training
  the marker rows, so it is not established as the sole cause. It is **not** the whole story at 1.7B: LoRA, which also freezes the embeddings, formats 84/110 from the
  base checkpoint but only 8/110 from Instruct (82 foreign special tokens). The token ids emitted were not recorded.
- Capstone follow-up: verify that the actual checkpoint can distinguish and generate the required markers, with a
  development control using a supported native format or distinct marker mapping. Tokenizers assign IDs; model weights
  learn representations. The surrogate five-row hybrid has not been tested on the capstone. The latest TSAI ruling
  in CAP, checked in the 15 Nov export, keeps the dry-run-1 output head dense untied and makes the KE2 cosine decoder
  evaluation-only. This study uses SmolLM2's tied embeddings/output head, so its marker-row intervention does not
  establish how the actual dry-run-1 head will behave.

## Code and checks

- `dt/mask.py` ports `agentic-learning-ai-lab/deleting-weights` @ `94f0340e` (MIT): soft mask in training, hard mask baked
  into plain `nn.Linear` for every evaluation, Wanda prior, linear α schedule, λ regulariser decaying to 0. Differences on
  purpose: bias kept, Wanda norms skip padding, masks packed with zlib instead of zstd.
- Tests (`dt/tests`, 12; bench tests 19; 31 pass on CPU): all-keep mask gives bitwise-equal logits (soft and hard) for
  gate, all-MLP and attention targets; bias preserved; hard and soft agree within 1e-5 at α = 1000; only mask logits get
  gradients; base weights bitwise unchanged after training; α schedule; regulariser sign; Wanda init rate matches the
  paper's ηΦ(3) + (1−η)Φ(−3); deletion fraction over targeted and all weights; bake = hard mask and survives save/reload;
  mask pack/unpack round trip; end-to-end DT and marker-hybrid runs; `--train-marker-rows` refuses full FT and wd ≠ 0.
- Every run: step-1 stored-weight writeback PASS; frozen-weight sha256 equal before/after (LoRA, DT, DT+m); bake parity
  0.0; save → fresh reload bit-identical (full, DT) or ≤ 3e-4 logits (LoRA merged). Real checkpoints rechecked offline:
  pure DT 135M changes only the 30 `gate_proj` tensors, every value is the base value or 0, and the 854,071 new zeros
  equal the reported deletions; DT+m additionally changes exactly embedding rows 0, 1, 2, 15, 16.

## Speed, memory, cost (measured)

| arm (1.7B, L40S, bf16 autocast, grad checkpointing, ≤ 8,192 tokens per micro-batch, 8 rows per step) | 400 steps | s/step | peak CUDA allocated |
|---|---|---|---|
| full FT | 848-853 s | 2.12 | 34.4 GB |
| LoRA r4 | 778-875 s | 1.95-2.19 | 12.3 GB |
| DT (402.7M mask logits) | 734 s | 1.83 | 18.3 GB |
| DT+m | 749 s | 1.87 | 19.5 GB |

The DT number is measured, not inferred: the hard mask uses dense matmuls with zeros, so no inference speedup is established or claimed. DT training state is larger than LoRA's (one FP32 logit plus two Adam moments per targeted weight).
The saved pure-DT delta is a 1-bit mask (requires the exact original checkpoint; the hybrid additionally needs its changed marker rows): 6.4-6.8 MB (zlib) at 1.7B versus a 6.8 GB FP32 full-FT checkpoint. 135M on A10:
DT ≈ 1.03 s/step, 5.4 GB. 1.7B evaluation per checkpoint (L40S): test bpb ~65 s, 110 generations 350-500 s, held-out v1
~305 s. Modal spend for WP2: **≈ $11.7 estimated** (original ledger $11.501 plus $0.1935 for the forward-only uncertainty collection;
20 GPU function jobs in total and one CPU model-download app). This is not dashboard billing; startup/storage and
other non-function charges are not fully reconciled.

## Not done / limits

- 360M, DT+m from Instruct, LoRA+m, the layer and η sweeps, T = 1,600, second and third seeds at 1.7B: not run ($12 cap).
- No fresh large confirmatory endpoint: a fresh grouped slice from shards 4-5 yielded 2 rows (OCR-2 spreads a problem's
  completions across shards). The test split is exploratory; the 22-cluster supplement is small.
- LRs were chosen at 135M and not re-tuned at 1.7B; full FT at 1e-4 may forget more than a tuned 1.7B LR would.
- Exec counts are low and partly limited by the data: in 23 of 110 test tasks (7 of 22 supplement tasks) the OCR-2
  reference and up to three human solutions print identical outputs that differ from the stored expected output (possible
  causes include multiple valid answers, unsupported checking contracts, or incorrect expected outputs); 10 more test tasks (2 supplement)
  are unresolved. All are TACO; code_contests and APPS references pass. "Validated" columns exclude them. The same
  pattern explains the 7/24 dev reference failures reported by WP3 (dev: 11 disagree, 7 unresolved, of 76).
- The 1.7B intervals below cover evaluation-cluster uncertainty for fixed checkpoints, not training-seed variation.
  The 135M full-FT seed spread on the test split is 0.0002 bpb.

## Additional preregistered uncertainty collection (controller)

Per-row NLL for all nine saved 1.7B checkpoints was collected in a single L40S FP32/TF32-off forward-only job after
settings and checkpoints were frozen. No training, model selection, generation or metric-definition change. Each
collection has the same 91 row IDs, 22 cluster IDs and byte denominators; summed bpb agrees with the earlier batched
score within 1e-5. Function time 302.7 s, estimated cost $0.1935. The collector CLI smoke also matched the existing 135M
per-row result. `dt/analysis.py` exposes this same loss helper and the paired cluster bootstrap.

Paired differences on the fresh supplement, 10,000 cluster resamples, seed 0; positive means higher (worse) target bpb:

| Comparison | Difference | 95% cluster-bootstrap interval |
|---|---:|---:|
| 1.7B base DT − full FT | +0.03310 | [+0.02520, +0.04037] |
| 1.7B base DT+m − full FT | +0.02553 | [+0.01732, +0.03328] |
| 1.7B base LoRA − full FT | +0.01332 | [+0.00686, +0.01963] |
| 1.7B Instruct DT − full FT | +0.02438 | [+0.01679, +0.03166] |
| 1.7B Instruct LoRA − full FT | +0.00980 | [+0.00420, +0.01528] |
| 1.7B base DT+m − DT | −0.00757 | [−0.00926, −0.00589] |

These intervals describe this small evaluation population for the fixed saved checkpoints. They do not cover seed,
architecture, optimizer or admission uncertainty, and they do not make code-pass or capstone-performance claims.
Aggregate results and parity metadata: `results/dt_bpb_uncertainty.json`. Raw per-row records stay private.

Example reproduction (inputs/checkpoints must be staged; no private items are committed):

```bash
python dt/analysis.py collect --model "$MODEL" --split-file "$SUPPLEMENT" --device cuda --out "$OUT/arm.json"
python dt/analysis.py bootstrap --arm "dt=$OUT/dt.json" --arm "full=$OUT/full.json" --pair dt:full --out "$OUT/bootstrap.json"
```

## Addendum, 15 Nov 2026: marker controls, untied head, deletion/layer sweep (one seed each)

**Surrogate, exploratory, one seed per arm.** Added after the sections above, which are unchanged. Same slice-v1 data,
400 steps x 8 rows, seed 1, evaluation commands and integrity checks (writeback, frozen-weight hash, reload parity: all
pass on every arm) as the 14 Nov study. Rows marked "ref" are the 14 Nov measurements, not rerun. Preregistrations are
local files, not in the repository. Evidence (aggregate reports, no generations): `fable_20261115_evidence/`
(`mk17b-s1.json`, `mk17b-lr1e-3-s1.json`, `loram17b-s1.json`, `mcnemar.json`, `dtm135-*.json`).

The Modal driver (`modal_e2.py`) stayed local. Each arm ran these in-repo commands (from `teams/10-post-training`):

```bash
python sft/bench/train.py --train <slice-v1>/train.tok.jsonl --model <weights> --revision none --tokenizer-dir <weights> \
  --steps 400 --seed 1 --device cuda --autocast bf16 --micro-tokens 8192 --grad-checkpointing --log-every 50 --out <run> <ARM ARGS>
python sft/bench/evaluate.py --model <run>/model --split-file <slice-v1>/test.tok.jsonl --metrics bpb,format,forget \
  --gen-limit 200 --gen-batch <37 at 1.7B, 56 at 135M> --token-budget 16384 --device cuda --generations-out <private> --out <test.json>
python sft/bench/evaluate.py --model <run>/model --split-file <heldout-sup-v1>/test.tok.jsonl --metrics bpb,format \
  --gen-limit 200 --gen-batch <same> --token-budget 16384 --device cuda --generations-out <private> --out <sup.json>
```

New bench options used here (this PR): `--method markers` (every weight frozen, only the marker rows train),
`--untie-head` and `--marker-scope {both,input,output}`. Tests: `sft/bench/tests/test_bench.py`.

### R3. Marker controls on SmolLM2-1.7B base (NVIDIA L40S)

Arm args: markers `--method markers --lr 1e-4 --train-marker-rows --marker-lr 1e-4` (and `1e-3` for both LRs);
LoRA+markers `--method lora --lr 0.001 --train-marker-rows --marker-lr 1e-4`.

| Arm | Trains | Test bpb | Valid replies / 110 | Supplement valid / 22 | Held-out v1 bpb (change vs base 0.8434) |
|---|---|---:|---:|---:|---:|
| untrained (ref) | nothing | 1.0490 | 0 | 0 | 0.8434 |
| markers only, LR 1e-4 | 5 marker rows | 0.5871 | 3 | 0 | 0.8417 (-0.0017) |
| markers only, LR 1e-3 | 5 marker rows | 0.5112 | 1 | 1 | 0.8543 (+0.0109) |
| pure DT (ref) | gate masks | 0.3698 | 0 | 0 | 0.8597 (+0.0163) |
| DT + markers (ref) | gate masks + 5 rows | 0.3633 | 76 | 14 | 0.8525 (+0.0091) |
| LoRA + markers | LoRA r4 + 5 rows | 0.3483 | 81 | 17 | 0.8815 (+0.0381) |
| LoRA (ref) | LoRA r4 | 0.3500 | 84 | 12 | 0.9121 (+0.0687) |
| full FT (ref) | everything | 0.3332 | 93 | 16 | 0.9180 (+0.0746) |

*Surrogate model, one seed per arm.*

Execution pass@1 on the first 100 test prompts (all / the 69 with a validated reference), scored locally in Docker with
the 14 Nov script: LoRA + markers 15 / 14; reference rows LoRA 18 / 17, DT + markers 13 / 13, full FT 21 / 20.
Markers-only arms were not scored (1 and 3 valid replies). The execution scorer's caveat in `small_sft.md` applies (the
17/24 dev reference-control check does not establish a scorer ceiling).

Paired exact McNemar on the 110 format prompts (`mcnemar.json`): LoRA+markers vs DT+markers 81 vs 76, discordant
19/14, p = 0.49; LoRA+markers vs LoRA 81 vs 84, p = 0.72; LoRA+markers vs full FT 81 vs 93, p = 0.029.

- **Marker rows alone do not produce the format** (3/110 and 1/110; "never closes the turn" in 102 and 108 of 110).
  Pure DT alone does not either (0/110). Together they give 76/110: the hybrid's repair is an interaction. The
  preregistered reading "format needs body adaptation too" held; "markers are sufficient" is rejected at both LRs.
- **Teacher-forced bpb overstates adaptation.** Training five rows moves bpb from 1.049 to 0.511, 75% of full
  fine-tuning's bpb gain, while producing one valid reply in 110. The 14 Nov "bpb-gain ratio 0.95 for pure DT" should
  be read with this in mind.
- With the same marker freedom, DT and LoRA are not distinguishable on format (76 vs 81, p = 0.49) or execution (13 vs
  15 of 100). DT+markers has the higher bpb (0.363 vs 0.348) and the smaller held-out drift (+0.009 vs +0.038). Marker
  rows did not change LoRA's format (81 vs 84). Differences of a few prompts are not interpretable at one seed.
- Cost $3.46 for the three arms (ledger estimate).

### R8. Untied head at 135M: the output-side marker rows carry the repair (NVIDIA A10)

SmolLM2-135M, head untied before training, DT on gate_proj plus five marker rows, arm args
`--method dt --lr 0.002 --train-marker-rows --marker-lr 1e-4 --untie-head --marker-scope {both,input,output}`.

| Marker rows trained | Valid replies / 110 | Supplement / 22 | Test bpb |
|---|---:|---:|---:|
| output head only | 60 | 8 | 0.5287 |
| both sides | 57 | 9 | 0.5286 |
| input embeddings only | **0** | 0 | 0.5321 |
| tied, 14 Nov (ref, not rerun) | 63 | | 0.5287 |

*Surrogate model, one seed per arm.*

Output-only equals both; input-only is exactly as bad as pure DT (0/110, and the same bpb as pure DT, 0.5321). The
prediction "output rows carry it" held. The untied head here starts as a copy of the embeddings, which the capstone's
dense untied head (dry-run-1 ruling) will not. Cost $1.11 (ledger estimate).

### R10. Deletion-fraction and target-layer sweep at 135M (NVIDIA A10)

SmolLM2-135M, tied head, five marker rows trainable in every arm, base held-out v1 bpb 1.0981. Arm args: the R8 DT
args without `--untie-head`, plus `--dt-eta 0.0001220703125` (1/8192), `--dt-eta 0.00390625` (1/256),
`--dt-targets mlp` or `--dt-targets attn`.

| Target layers | Init quantile (knob) | Deleted at init, of targeted | Deleted at end, of targeted / of all weights | Test bpb | Valid / 110 | Supplement / 22 | Held-out v1 bpb change |
|---|---|---:|---:|---:|---:|---:|---:|
| MLP gate | 1/8192 | 0.15% | 3.17% / 0.63% | 0.5288 | 62 | 13 | +0.0295 |
| MLP gate (14 Nov, ref) | 1/2048 | 0.18% | 3.21% / 0.63% | 0.5287 | 63 | 9 | +0.0295 |
| MLP gate | 1/256 | 0.52% | 3.50% / 0.69% | 0.5286 | 59 | 12 | +0.0276 |
| all MLP (gate, up, down) | 1/2048 | 0.18% | 1.55% / 0.92% | **0.5048** | 71 | 12 | +0.0426 |
| attention (q, k, v, o) | 1/2048 | 0.18% | 2.65% / 0.52% | 0.5303 | 71 | 11 | +0.0471 |

*Surrogate model, one seed per arm; every arm is the DT+markers hybrid, not pure DT.*

- **The init quantile hardly matters.** A 32-fold change moves the realised deletion from 3.17% to 3.50% of the
  targeted weights and leaves bpb, format and forgetting unchanged. Training decides what is deleted; at this scale the
  deletion fraction is an outcome, not a control.
- **The target layers matter more.** All three MLP matrices lower bpb (0.505 vs 0.529) and give 71 valid replies, at
  about 45% more held-out drift than gate-only. Attention masks give the same 71 with gate-level bpb and the largest
  drift.
- With one seed, 59 to 71 valid replies is inside the spread seen between full-FT seeds at this size (81 to 87), so
  the format column does not rank the arms; bpb and drift differences are the readable part.
- Cost $1.50 (ledger estimate).

Still not done after this addendum: second seeds at 1.7B, the capstone model, and DT-then-RL. DT as the RL method
itself (no SFT stage) is in `dt_rl_e4_20261115.md`.
