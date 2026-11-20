# Small SFT on the bench: SmolLM2-135M, OCR-2 slice (14 Nov 2026; forgetting verdict and data status updated 16 Nov; verdict re-run with `forgetting.py` 18 Nov)

**Evidence level: surrogate.** This tests the harness and shows what a small dense model does on this slice. The numbers do
not transfer to the capstone model. **Data provenance:** rows come from the OCR-2 pack v1 built with the C3 tokenizer (PR #79,
merged as the C3 record). Since 16 Nov the lead has confirmed the 2% `heldout_eval_v1` split and the conservative pack that
leaves out 14 unclear-source rows (`jobs/2026-11-16-ocr2-pack-v1.md`). TSAI froze the **p1536** tokenizer (sha256 `e6b93a93...`)
and G10 rebuilds SFT data v1 with it (PR #103, `jobs/2026-11-17-ocr2-pack-v1-p1536.md`). **The slice below was built from the C3
shards 0-3 and was not rebuilt with p1536**; the pack sha256 values in the Setup table are the C3 ones. Whether a p1536 rebuild
changes which rows fit 2,048 tokens or the split was not checked. Only the training pack was read. The WP1 held-out rows were
never opened. The bench drops every row whose near-duplicate cluster touches a WP1 held-out family.

## Setup

| Item | Value |
|---|---|
| Model | `HuggingFaceTB/SmolLM2-135M` @ `93efa2f097d58c2a74874c7e644dbc9b0cee75a2`, Apache-2.0, LlamaForCausalLM, 30 layers, hidden 576, tied embeddings; `model.safetensors` sha256 `80521b40…5da1` |
| Data | OCR-2 pack shards 0-3 (pack sha256 `90233af7…`, `33cdf2e3…`, `82ef539e…`, `2f3c16af…`; 32,082 rows) → rows ≤ 2,048 SmolLM2 tokens: 3,536 |
| Split | near-duplicate cluster (10 Nov MinHash, Jaccard ≥ 0.8) of the problem family key; fractions 0.70/0.10/0.20; caps 4000/300/300 |
| Rows (clusters) | train 2,509 (531), dev 300 (78), test 300 (110); overlap 0 at cluster, family, question-hash and OCR question-id level |
| Slice files | train.tok sha256 `93c4712d…11db`, dev.tok `a0b1458c…e536`, test.tok `8d123382…677d` (private, not in Git) |
| Objective | `train_probe.py` contract: shifted targets from `loss_mask`, global-count mean over the 8-row update, zero-target rows rejected; 80.3% of train tokens are targets |
| Optimiser | AdamW (0.9, 0.95), wd 0, clip 1.0, 20 warmup steps then cosine to 10%; 400 steps × 8 rows (1.275 epochs) |
| Precision | FP32 weights, gradients and AdamW state. CUDA training compute: BF16 autocast. Evaluation: FP32, TF32 off |
| Hardware | Modal NVIDIA A10 (one dev run on A10G), 2 CPU cores, 8 GiB. Eval-mini on the Mac CPU (Apple M1 Pro). Exec in Docker `python:3.12-slim` on the Mac |

Why the split deviates from the plan's 90/5/5 with 4000/300/300: only 3,536 rows in shards 0-3 fit 2,048 tokens, from 747
problem families. At 5%, test would hold 42 problems, too few for the 200-generation format check. I used 70/10/20 to get
110 test problems. The train split is therefore 2,509 rows, not 4,000.

LR was chosen on **dev** target bpb with seed 1 (rule fixed before any test number): full FT {3e-6, 1e-5, 3e-5} + one extension
1e-4; LoRA r=4 {1e-4, 3e-4} + one extension 1e-3. Both winners are the largest value tested, so the best LR may be higher (not tested).

| dev target bpb (base 0.82387) | 3e-6 | 1e-5 | 3e-5 | 1e-4 | | LoRA 1e-4 | 3e-4 | 1e-3 |
|---|---|---|---|---|---|---|---|---|
| full FT | 0.66301 | 0.57919 | 0.52915 | **0.49125** | | 0.63888 | 0.57582 | **0.53553** |

## Results on the test split (frozen config; base on the same table)

**Byte-count correction (14 Nov evening, metadata only).** The first version of `retok.py` charged each trained token the
UTF-8 bytes under its offsets. Byte-fallback tokens of one non-ASCII character share that character's offsets, so those bytes
were counted more than once (train 87/2,509 rows, dev 12/300, test 7/300; test denominator 1,166,384 → 1,166,330 bytes,
−0.0046%). Token ids, masks, gradients, weights, format and exec scores are unaffected: training never reads the byte field,
and re-running the repaired retokenizer gives identical ids, masks and prompt lengths on all 3,109 rows. All bpb values here
are **derived** from each run's recorded NLL sum divided by the corrected byte count (`work/.../correct_bpb.py` →
`corrected_target_bpb.json`); the original eval reports and frozen slice files are unchanged. Each value moved by ≤ 0.00008;
no ranking changed. A corrected rebuild of the slice would change the `.tok.jsonl` sha256 (byte metadata only); the hashes
above are the files the runs actually used.

| Model | target bpb ↓ | format validity ↑ | exec pass@1 | forgetting: held-out v1 bpb (Δ vs base) | 3-group bpb | ARC-C acc_norm | HellaSwag acc_norm |
|---|---|---|---|---|---|---|---|
| base (untrained) | 0.81480 | 0/110 (0.0%) | 0/100 | 1.0981 | 0.9773 | 0.272 | 0.4325 |
| full FT 1e-4, seed 1 | 0.48373 | 85/110 (77.3%) | 2/100 | 1.1484 (+0.0503) | 1.0361 | 0.284 | 0.445 |
| full FT 1e-4, seed 2 | 0.48351 | 87/110 (79.1%) | 2/100 | 1.1496 (+0.0515) | 1.0363 | 0.284 | 0.445 |
| full FT 1e-4, seed 3 | 0.48372 | 81/110 (73.6%) | 1/100 | 1.1488 (+0.0507) | 1.0364 | 0.284 | 0.435 |
| full FT mean (3 seeds) | 0.48365 (spread 0.00022) | 76.7% (spread 5.5 pp) | 1.7% | +0.0508 | 1.0363 | 0.284 | 0.442 |
| LoRA r=4 1e-3, seed 1 | 0.52827 | 0/110 (0.0%) | 0/100 | 1.1365 (+0.0384) | 1.0191 | 0.274 | 0.4375 |

Eval-mini: Team 9 `run_eval_mini.py --profile mini` (ARC-Challenge 500 items, HellaSwag 400 items, 0-shot). It ran as a black
box that returns scores only. Standard errors are about 0.020 and 0.025, so the observed eval-mini differences are small relative to the reported per-score standard errors. A paired significance test was not performed; these results do not establish a general capability improvement. Seeds differ only in data order, from the same base weights. Exec pass@1 uses greedy
decoding on 100 of the 110 test problems. The dev reference-control check through the same sandbox passed 17/24. This does not establish a scorer ceiling: the seven failures remain unexplained (possible strict-output, source/test or unverified-reference issues). Treat execution pass counts as provisional until those failures are diagnosed.

### Forgetting verdict (limits confirmed 16 Nov: bits per byte +0.05, at-limit mark within 0.01)

Rules are those of `sft/eval_v1.md` and `sft/tests/forgetting.py`: forgetting if held-out bits per byte rise by more than 0.05
over the base, or a benchmark falls by more than 2 x its combined stderr and by at least 0.01. A result within 0.01 of its
limit, on either side, is "at the limit". The limits set the verdict only; the numbers above are all reported.

| Run | bits per byte change | vs limit 0.05 | ARC-C change | HellaSwag change | Verdict |
|---|---|---|---|---|---|
| full FT 1e-4, seed 1 | +0.0503 | over by 0.0003, **at the limit** | +0.012 | +0.0125 | **FORGETTING** (bits per byte) |
| full FT 1e-4, seed 2 | +0.0515 | over by 0.0015, **at the limit** | +0.012 | +0.0125 | **FORGETTING** (bits per byte) |
| full FT 1e-4, seed 3 | +0.0507 | over by 0.0007, **at the limit** | +0.012 | +0.0025 | **FORGETTING** (bits per byte) |
| LoRA r=4 1e-3, seed 1 | +0.0384 | under by 0.0116, not at the limit | +0.002 | +0.005 | No forgetting |

- **Benchmarks:** none fell, so neither benchmark counts as forgotten for any run. The drop bar for each is the larger of 0.01
  and 2 x the combined stderr, which `forgetting.py` reads from the reports: 0.0284 for ARC-C (bar 0.057) and 0.0351 for
  HellaSwag (bar 0.070); every change is a rise. No benchmark is marked "at the limit" either.
- **Full FT is a close call.** All three seeds exceed the limit by 0.0003-0.0015, a spread smaller than the seed-to-seed
  spread of the change (0.0012). Read it as "about at the limit", not as a clear breach. The bits-per-byte rise is in every
  group (English, code, Indic).
- **How this was computed.** The verdicts were first written by hand from the table's rounded values (PR #105). On 18 Nov
  `forgetting.py` was run on the original `bench/evaluate.py` reports (schema `g10-bench-eval/1`, merged to the Week 3 branch in
  PR #117, `results/small_sft_evidence/`). It gives the same verdict for all four runs, and its bits-per-byte changes round to
  the table values: +0.0503, +0.0515, +0.0507 and +0.0384 (exact: +0.050315, +0.051493, +0.050677, +0.038351). Its output files
  are in `results/small_sft_evidence/forgetting_check/` (one `.md` and one `.json` per run). The script exits 1 for the three
  full FT runs (verdict "forgetting") and 0 for LoRA. Command, from the repository root, with the `-test.json` file first on
  both sides so that the merged `device` matches (see the evidence README):

  ```
  E=teams/10-post-training/results/small_sft_evidence
  python3 teams/10-post-training/sft/tests/forgetting.py \
    --before $E/base-test.json $E/base-evalmini.json \
    --after  $E/<run>-test.json $E/<run>-evalmini.json \
    --out <run>.md --out-json <run>.json          # <run>: full-lr1e-4-s1, -s2, -s3, lora-lr1e-3-s1
  ```

  The three full FT runs are over the limit by only 0.0003, 0.0015 and 0.0007, so a re-run on a different held-out file or tokenizer
  (for example after a p1536 rebuild of the slice) could change the verdict. All reports record the same held-out sha256
  (`21c6e4b2...`) and tokenizer sha256 (`9ca9acdd...`); `forgetting.py` refuses to compare reports that differ in either.

**What held:** test target bpb fell from 0.815 to 0.484 in all three seeds. Format validity rose from 0% to 74-79%. Every
valid reply has a think block and a fenced code block. The other 21-27% ran to the 2,048-token budget without closing the
turn. **What did not:** execution pass counts are low (1-2/100), with unresolved reference-control failures; the cause cannot be attributed to model size from this experiment. Forgetting bpb on G5 held-out v1 rose by
0.051 for full FT and by 0.038 for LoRA, in every slice group (English, code, Indic).

### LoRA format failure (observed; explanation tentative)
**Observed:** LoRA (r=4, lr 1e-3, seed 1) emits `<|im_end|>` as its first generated token on all 110 test prompts, so its
format validity is 0 although its target bpb improved (0.528 vs base 0.815). Full FT does not do this.

**Tentative explanation, not tested by a control:** in the base checkpoint the embedding rows of `<|im_start|>` (1),
`<|im_end|>` (2), 5 and 7-16 have pairwise cosine ≈ 1.000. The think markers are mapped to 15 and 16 (cosine 0.9999 to id 2).
Embeddings are tied and LoRA leaves them frozen, so the output logits of those ids may stay too close for greedy decoding to
separate, while full FT can move the rows. This geometry is measured. That it *causes* the failure is not shown: no run varied
the mapping, the embedding trainability or the LoRA rank/LR. Other candidates (too few steps for LoRA, the LR grid edge, the
greedy tie-break) are open. The mapping was not changed after this surfaced on a test metric.

**For WP2 (open question, not a conclusion):** a method that keeps embedding rows frozen, as DT does by design, may hit the
same effect on this base checkpoint. That needs a control before any DT conclusion: e.g. LoRA with the marker rows trainable,
or the same arm on SmolLM2-135M-Instruct, whose chat markers are trained.

## Checks (every run)
- Step-1 stored-weight writeback on `model.layers.0.self_attn.q_proj.weight` (full FT) / `q_proj.lora_B` (LoRA): PASS in all
  9 runs. Every entry is within 2 ULP + 1e-4·|update| of an FP64 replay of the AdamW step. 99.9% of entries moved in FP32
  storage. For full FT, quantizing the before/after FP32 tensor to BF16 changed only 0.03-1.1% of entries at step 1 (LR 1.5e-7 to 5e-6). This is an endpoint-quantization counterfactual, not a separately trained BF16-storage arm. LoRA's B starts at zero.
- Save → fresh reload: full FT tensors bit-identical, logits max |diff| 0.0. LoRA: merged weights reloaded bit-identically.
  Logits versus the unmerged in-memory model differ by at most 1.8e-4 (tolerance 1e-3).
- Checkpoint sha256 of the evaluated files equals the files downloaded for eval-mini (e.g. full FT s1 `392fdcf1…`).

## Loss curve (mean training loss per 50 steps)
| steps | 1-50 | 51-100 | 101-150 | 151-200 | 201-250 | 251-300 | 301-350 | 351-400 |
|---|---|---|---|---|---|---|---|---|
| full FT s1 | 1.444 | 1.181 | 1.118 | 1.081 | 1.074 | 1.030 | 0.983 | 0.956 |
| full FT s2 | 1.456 | 1.174 | 1.117 | 1.067 | 1.063 | 1.052 | 0.989 | 0.963 |
| full FT s3 | 1.453 | 1.191 | 1.108 | 1.089 | 1.054 | 1.034 | 0.985 | 0.972 |
| LoRA 1e-3 | 1.564 | 1.304 | 1.246 | 1.212 | 1.209 | 1.164 | 1.148 | 1.129 |

## Speed and memory
| Path | Hardware | Setting | Measured |
|---|---|---|---|
| train, full FT | Modal A10 | BF16 autocast, FP32 master, micro-batch ≤ 8,192 tokens, 8 rows/update (~12k tokens) | 90-92 s per 100 steps; 400 steps 361-368 s; peak CUDA allocated 14.6 GB |
| train, LoRA r=4 | Modal A10 | same | 101-103 s per 100 steps; peak 12.0 GB; 1,221,120 trainable params |
| train, full FT | Apple M1 Pro 16 GB, MPS | FP32, gradient checkpointing, one row per micro-batch | ~15 s per update over 6 steps (≈ 1,500 s per 100 steps, est.); 3.9-7.2 GB MPS driver memory. Without checkpointing: OOM, or swap thrash |
| eval: test target bpb (300 rows, 445k tokens) | Modal A10 | FP32 | 25 s |
| eval: 110 greedy generations ≤ 2,048 tokens | Modal A10 | FP32, batch 56 | 321-335 s for trained/base (LoRA 1.6 s: one token each) |
| eval: forgetting (1,059 docs, windows of 2,048) | Modal A10 | FP32 | 86-111 s |
| eval-mini | Mac CPU | FP32, batch 8 | 108-117 s per model (MPS segfaults in the Team 9 venv at weight load) |
| exec | Mac Docker | 4 workers | 11-16 s per 100 problems |

Modal spend for WP3: about **$2.21 estimated** (6,295 container-seconds at list price: A10 $0.000306/s + 2 cores + 8 GiB),
not read from billing.

## Not measured / gaps
- The Mac did not complete 400 steps. The 400-step runs are on Modal A10 (controller-authorised change). There is no matched
  MPS-versus-CUDA comparison, and no claim of cross-device bit identity.
- Only one LoRA seed, and no control for the LoRA format failure. The DT arm and the marker controls are in `results/dt_sft_surrogate.md` (WP2).
- Bench tests: 18 pass on CPU. Existing `sft/verify.sh` completed with `verify: OK`; its final reused-tools suite reports 104 passes (not the combined total). The bench tests are not yet wired into `verify.sh`.
- Format validity uses one greedy sample per problem, n=110. A 95% interval for 77% is about ±8 pp.
- LR optimum may lie above 1e-4 (full) and 1e-3 (LoRA).
- The forgetting verdict is a `forgetting.py` output (18 Nov), but of one LoRA seed and three full FT seeds on a slice built from the C3 pack; it was not re-run on a p1536 rebuild.
- The slice is from the C3 pack. The lead's decisions on the held-out split and the 14 unclear-source rows are now confirmed, but the p1536
  rebuild (PR #103) has not been compared with this slice; if the rebuilt pack changes the rows that fit 2,048 tokens, rebuild the slice.
