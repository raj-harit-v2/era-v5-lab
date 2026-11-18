# Rotation R1: Sigmoid Gate on Attention Output (`attn-4`), Seed 1239

**Author:** `@thinktinkergreen`  
**Team:** `05-architecture`  
**Arm:** Sigmoid gate on attention (`attn-4`, `teams/05-architecture/configs/arms/attn4_gate.yaml`)  
**Assigned Seed:** `1239` (repeating the T2 evaluation arm against baseline seeds 1234, 1235, 1236)  
**Run Due Date:** Wednesday, 18 Nov 2026  
**Replication Verdict Due Date:** Thursday, 19 Nov 2026  
**Configuration Invariant:** This rotation run strictly evaluates the existing architecture arm and **does not modify `config_v1.yaml`**.

---

## 1. Executive Summary & Assigned Task

As part of the Week 3 rotation into Team 05 (Architecture), Member `@thinktinkergreen` is assigned to repeat one existing T2 attention alternative at a new random seed:
- **Design:** Sigmoid gate on attention output (`attn-4`).
- **Seed:** `1239`.
- **Training Setup:** Identical T2 budget:
  - 1,221 training steps
  - Batch size 8, sequence length 2,048 (16,384 tokens/step, ~20.0M tokens total)
  - Micro-batch size 1 (peak VRAM ~10.3 GB, zero OOM risk)
  - Optimizer: AdamW (`--lr 0.001`)
  - Target Evaluation: `heldout_v1` (three-group BPB, English, Code, Indic splits).
- **Core Question:** Does `attn4_gate` maintain its held-out bits-per-byte advantage and stability when evaluated at a fresh seed (`1239`), confirming that earlier T2 gains were structural rather than seed-lucky artifacts?

---

## 2. Job Request & Verification Evidence

The formal TSAI job submission request is committed and tracked at:
- **Job Request File:** [`teams/05-architecture/jobs/2026-11-15-rotation-attn4-seed1239.md`](../jobs/2026-11-15-rotation-attn4-seed1239.md)
- **Execution Evidence Directory:** [`teams/05-architecture/jobs/evidence/2026-11-15-rotation-attn4-seed1239/`](../jobs/evidence/2026-11-15-rotation-attn4-seed1239/)

### Pre-Submission Verification Summary

Prior to filing the job request, local preflight validation was completed and certified:
1. **Tokenizer & Raw Byte Table Hash Lock:**
   - Tokenizer v0 SHA-256: `2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5`
   - P32 Raw Byte Table SHA-256: `47d411a9c6cae6fa2075935567243e51f4efbc377ccef3eef42c32fce66f869f`
   - Re-verified via `teams/04-ke2/src/build_tables.py` against `v0_tokenizer.json`.
2. **Specification & Configuration Audit:**
   - Ran `teams/05-architecture/harness/check_week2.py` against `attn4_gate.yaml`: Reported **0 errors**, valid runtime and model specification.
   - All 17 unit tests in `teams/05-architecture/tests/test_week2_attention.py` passed with 100% success rate.
3. **Execution Smoke Test:**
   - Executed a 6-step local smoke run (`--smoke`, seed 1239, batch size 1, context length 160) using `teams/05-architecture/harness/train_week2.py`.
   - Run completed with exit code 0 in 24.8 seconds.
   - Training cross-entropy decreased smoothly from 11.964 to 6.878 with zero NaN/inf values.
   - Verified that artifact outputs strictly adhered to standard filenames (`manifest.json`, `metrics.jsonl`, `summary.json`, `losses.txt`, `total_losses.txt`).

---

## 3. Replication Results Table

*(Pending TSAI Queue Execution — Due Wednesday, 18 Nov 2026)*

The returned metrics from `./out/attn4-gate-1239/` will be ingested upon receipt:

| Arm | Seed | Steps | Aggregate BPB | Three-Group BPB | English BPB | Code BPB | Indic Mean BPB | Step Time (ms) | Tokens / Sec | Run Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **attn-0 (Ref)** | 1234 | 1,221 | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | Completed |
| **attn-0 (Ref)** | 1235 | 1,221 | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | Completed |
| **attn-0 (Ref)** | 1236 | 1,221 | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | Completed |
| **attn-4 (Gate)** | 1234 | 1,221 | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | Completed |
| **attn-4 (Gate)** | 1235 | 1,221 | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | Completed |
| **attn-4 (Gate)** | 1236 | 1,221 | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | *TSAI* | Completed |
| **attn-4 (Gate)** | **1239** | **1,221** | *Pending* | *Pending* | *Pending* | *Pending* | *Pending* | *Pending* | *Pending* | *Scheduled* |

---

## 4. Replication Decision Rules & Verdict Protocol

*(Verdict to be declared by Thursday, 19 Nov 2026)*

To evaluate whether the result holds, the following preregistered decision criteria are enforced:

### Criterion 1: Seed Spread Compliance
- Let $\mu_{\text{prior}}$ and $\sigma_{\text{prior}}$ be the mean and standard deviation of `attn-4` across seeds 1234, 1235, 1236.
- Let $\Delta_{\text{spread}} = \max(\text{bpb}_{1234..1236}) - \min(\text{bpb}_{1234..1236})$.
- **Pass Rule:** The seed-1239 three-group BPB must fall within $[\min(\text{bpb}) - 0.5 \Delta_{\text{spread}}, \max(\text{bpb}) + 0.5 \Delta_{\text{spread}}]$.
- Any deviation $> 2\sigma$ without hardware fault constitutes a seed-spread anomaly.

### Criterion 2: Structural Superiority Over Baseline (`attn-0`)
- **Pass Rule:** The seed-1239 run must preserve a lower three-group BPB than the mean of the reference baseline `attn-0`:
  $$\text{BPB}_{\text{attn-4, 1239}} < \overline{\text{BPB}}_{\text{attn-0}}$$
- Furthermore, neither the Code BPB nor the Indic Mean BPB may regress by more than $+0.02$ BPB compared to the reference baseline.

### Criterion 3: Numerical Stability & Monotonicity
- **Pass Rule:** Zero NaN, zero Inf, gradient norms strictly bounded within $[0.1, 5.0]$, and final step count equal to exactly 1,221.

---

## 5. Timeline & Next Steps

1. **15 Nov 2026:** Pre-flight smoke validation complete; job request PR filed with evidence.
2. **18 Nov 2026:** TSAI queue executes `attn-4` (seed 1239) and posts `./out/attn4-gate-1239/` metrics.
3. **19 Nov 2026:** Ingest final metrics into Section 3, evaluate Criteria 1–3, and declare final replication verdict.
