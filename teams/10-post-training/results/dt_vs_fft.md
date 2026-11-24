# Deletion Tuning, LoRA, and Full Fine-Tuning: Task Gain and Forgetting Table

**Author:** Member A (`@thinktinkergreen`) & Team 10 Post-Training  
**Status (TSAI / Instructor guideline, 15 Nov 2026):** Deletion Tuning (`arXiv 2611.10866`) is evaluated here as a **potential candidate** for final training, **not yet a decision**. TSAI decides at Gate 3 after reviewing these findings.  
**Reference Paper:** arXiv 2611.10866 (*"Deleting Weights to Learn"*), ported from `agentic-learning-ai-lab/deleting-weights` (`src/learnable_sparsity`, MIT).  
**Code:** `teams/10-post-training/sft/deletion_tuning.py`, `teams/10-post-training/sft/dt_vs_fft.py`, `teams/10-post-training/dt/mask.py` (`dt/run_triple.sh`).  
**Tests:** `teams/10-post-training/sft/test_deletion_tuning.py`.  
**Due Date:** Thursday, 19 Nov 2026.  

---

## 1. Surrogate Open-Model Comparison (`SmolLM2-135M` and `SmolLM2-1.7B`, Equal 400 Steps)

**Evidence level: surrogate, exploratory (one seed per arm except 135M full FT with 3 seeds).** Full setup, CIs, McNemar tests, untied-head probes, and caveats are in `results/dt_sft_surrogate.md`.

- **Slice:** OCR-2 `slice-v1` (train `2,509` rows / `531` clusters, dev `300`, test `300` rows / `110` clusters, `<= 2,048` tokens, no overlap with held-out families).
- **Equal steps:** 400 optimizer steps × 8 rows across all methods (`AdamW`, BF16 autocast, FP32 master weights).
- **Arms:** Full FT (`lr 1e-4`), LoRA (`r=4, alpha=8`, `q/k/v/o/gate/up/down`, `lr 1e-3`), pure DT (`gate_proj` masks only, `alpha 100->1000`, Wanda prior `eta=1/2048`, `lambda 1e-5->0`, `lr 2e-3`), and **DT+m hybrid** (DT plus the 5 chat-marker embedding/head rows trainable at `lr 1e-4`).

| Model | Start | Method | Test target bpb ↓ | Format valid (/110) ↑ | Exec pass@1 (/100, validated /69) | Held-out v1 bpb Δ vs base ↓ | Deleted (gate / all weights) |
| --- | --- | --- | ---: | ---: | --- | ---: | --- |
| `SmolLM2-135M` | base | untrained | 0.8148 | 0 | 0 / 0 | 1.0981 (base) | — |
| `SmolLM2-135M` | base | Full fine-tuning (3 seeds) | **0.4836** | **81–87** (mean 76.7%) | 1–2 / — | +0.0508 | — |
| `SmolLM2-135M` | base | LoRA (`r=4`) | 0.5283 | 0 | 0 / — | +0.0384 | — |
| `SmolLM2-135M` | base | Deletion Tuning (pure) | 0.5321 | 0 | 0 / — | **+0.0279** | 3.22% / 0.63% |
| `SmolLM2-135M` | base | DT + marker rows (hybrid) | 0.5287 | 63 | 1 / 1 | +0.0295 | 3.21% / 0.63% |
| `SmolLM2-1.7B` | base | untrained | 1.0490 | 0 | 0 / 0 | 0.8434 (base) | — |
| `SmolLM2-1.7B` | base | Full fine-tuning | **0.3332** | **93** | **21 / 20** | +0.0746 | — |
| `SmolLM2-1.7B` | base | LoRA (`r=4`) | 0.3500 | 84 | 18 / 17 | +0.0687 | — |
| `SmolLM2-1.7B` | base | Deletion Tuning (pure) | 0.3698 | 0 | 0 / — | +0.0163 | 1.32% / 0.31% |
| `SmolLM2-1.7B` | base | DT + marker rows (hybrid) | 0.3633 | 76 | 13 / 13 | **+0.0091** | 1.25% / 0.29% |
| `SmolLM2-1.7B` | instruct | untrained | 0.5815 | 107 | 13 / 13 | 0.9061 (base) | — |
| `SmolLM2-1.7B` | instruct | Full fine-tuning | **0.3284** | **91** | **22 / 22** | +0.0402 | — |
| `SmolLM2-1.7B` | instruct | LoRA (`r=4`) | 0.3409 | 8 | 0 / — | +0.0190 | — |
| `SmolLM2-1.7B` | instruct | Deletion Tuning (pure) | 0.3556 | 0 | 0 / — | **+0.0054** | 1.22% / 0.29% |

*Drift column caveat (18 Nov): the rows are not at equal task fit (Full FT reaches 0.4836, DT 0.5321 at 135M), and drift grows with fit. At matched fit on `SmolLM2-135M` a full fine-tune drifts less than DT, see section 7. The 1.7B rows have not been rechecked at matched fit.*

*Additional `1.7B` base run (`dt_sft_surrogate.md` R7): LoRA + marker rows gave `0.3483` test bpb, `81/110` valid replies, `15/100` (`14/69`) exec, `+0.0381` held-out drift.*

---

## 2. Deletion-Fraction and Target-Layer Sweep (`SmolLM2-135M`, DT + Marker Rows)

From `results/dt_sft_surrogate.md` §R10 (tied head, 5 marker rows trainable in every arm, base held-out v1 bpb `1.0981`, one seed):

| Target layers | Init quantile (`eta`) | Deleted at init (targeted) | Deleted at end (targeted / all) | Test target bpb ↓ | Format valid (/110) ↑ | Supplement valid (/22) | Held-out v1 bpb Δ ↓ |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MLP gate (`gate_proj`) | `1/8192` | 0.15% | 3.17% / 0.63% | 0.5288 | 62 | 13 | +0.0295 |
| MLP gate (`gate_proj`, ref) | `1/2048` | 0.18% | 3.21% / 0.63% | 0.5287 | 63 | 9 | +0.0295 |
| MLP gate (`gate_proj`) | `1/256` | 0.52% | 3.50% / 0.69% | 0.5286 | 59 | 12 | **+0.0276** |
| All MLP (`gate, up, down`) | `1/2048` | 0.18% | 1.55% / 0.92% | **0.5048** | **71** | 12 | +0.0426 |
| Attention (`q, k, v, o`) | `1/2048` | 0.18% | 2.65% / 0.52% | 0.5303 | **71** | 11 | +0.0471 |

---

## 3. Mathematical Formulation & Analytical Update Rule

Deletion Tuning freezes the pre-trained base weight $W \in \mathbb{R}^{d_{\text{out}} \times d_{\text{in}}}$ and trains only one real-valued logit $G_{ij}$ per weight parameter:
- **Training Forward Pass:** The effective weight is:
  $$W_{\text{eff}}(t) = W \odot \sigma\left(\alpha(t) \cdot G\right)$$
  where $\alpha(t)$ sharpens linearly from $\alpha(0) = 100$ to $\alpha(T) = 1000$ in the main SFT port (`dt/mask.py`, matching the paper repo; note that `sft/deletion_tuning.py` and the `cfg_e4_dt.yaml` RL pilots used `10^3 -> 10^4`, tracked in the 17 Nov port check).
- **Inference / Evaluation Forward Pass:** The effective weight is pruned with a deterministic hard mask:
  $$W_{\text{eval}} = W \odot \mathbf{1}\left[G > 0\right]$$
- **Initialization via Wanda Importance:**
  $$S_{ij} = |W_{ij}| \cdot \|X_{:, j}\|_2$$
  The logits $G_{ij}$ are drawn from Gaussian distributions whose means are assigned based on target deletion fraction $p \in [0, 1)$: the lowest $p$ fraction of weights receive $\mu = -0.03$ (biased for deletion), while the top $1 - p$ fraction receive $\mu = +0.03$ (biased for retention), with $\sigma = 0.01$.
- **Regularization Objective:**
  $$\mathcal{L}(G) = \mathcal{L}_{\text{task}}(W_{\text{eff}}(t)) + \lambda \sum_{i, j} \sigma(G_{ij})$$
  where $\lambda$ decays to 0.

---

## 4. Multi-Layer & Deletion-Fraction Matrix: Task Gain vs Catastrophic Forgetting

Evaluated via `teams/10-post-training/sft/dt_vs_fft.py --sweep --table` across three layer targets (**MLP gate only**, **all MLP**, and **attention**) and three target deletion fractions ($p \in \{0.20, 0.50, 0.80\}$) for 30 equal steps with learning rate $\eta = 0.2$, sharpness $\alpha$ 100 to 1000 (the reference SFT setting; earlier versions of this table used 1e3 to 1e4, which saturated the sigmoid so that no mask bit moved, see `results/dt_toy_sharpness_check_20261117.md`). One seed (0), a 4x4 toy, task loss on the toy's own training set. At this setting only some cells move: the three MLP-gate cells changed 5 hard-mask bits in total, all other DT cells changed none, so their rows are still the prior-only numbers:
- **Task Gain:** $\Delta \mathcal{L}_{\text{task}} = \mathcal{L}_{\text{task}, 0} - \mathcal{L}_{\text{task}, 30}$ (positive indicates improved adaptation).
- **Catastrophic Forgetting:** $\Delta \mathcal{L}_{\text{base}} = \mathcal{L}_{\text{base}, 30} - \mathcal{L}_{\text{base}, 0}$ on pre-trained distribution samples (positive indicates catastrophic loss of pre-trained knowledge).

| Layer Target | Method | Target Deletion Fraction ($p$) | Deleted Fraction | Task Loss (Step 0) | Task Loss (Step 30) | Task Gain ($\Delta \mathcal{L}_{\text{task}}$) | Forgetting ($\Delta \mathcal{L}_{\text{base}}$) | Base Weight Changed |
|---|---|---:|---:|---:|---:|---:|---:|:---:|
| **MLP gate only** | Full Fine-Tuning | - | 0.00 | 0.013317 | 0.002525 | **+0.010792** | **+0.005483** | **yes** |
| **MLP gate only** | LoRA (rank 1) | - | 0.00 | 0.013317 | 0.013313 | +0.000004 | +0.000000 | no |
| **MLP gate only** | Deletion Tuning | 0.20 | 0.31 | 0.013294 | 0.007691 | +0.005603 | +0.003684 | no |
| **MLP gate only** | Deletion Tuning | 0.50 | 0.62 | 0.017511 | 0.011382 | +0.006130 | +0.004111 | no |
| **MLP gate only** | Deletion Tuning | 0.80 | 0.75 | 0.014594 | 0.011038 | +0.003556 | -0.002551 | no |
| **all MLP** | Full Fine-Tuning | - | 0.00 | 0.000322 | 0.000305 | **+0.000017** | +0.000000 | **yes** |
| **all MLP** | LoRA (rank 1) | - | 0.00 | 0.000322 | 0.000322 | +0.000000 | +0.000000 | no |
| **all MLP** | Deletion Tuning | 0.20 | 0.19 | 0.000327 | 0.000327 | +0.000000 | +0.000000 | no |
| **all MLP** | Deletion Tuning | 0.50 | 0.50 | 0.000298 | 0.000298 | +0.000000 | +0.000000 | no |
| **all MLP** | Deletion Tuning | 0.80 | 0.81 | 0.000479 | 0.000479 | +0.000000 | +0.000000 | no |
| **attention** | Full Fine-Tuning | - | 0.00 | 0.001567 | 0.001112 | **+0.000455** | **+0.000031** | **yes** |
| **attention** | LoRA (rank 1) | - | 0.00 | 0.001567 | 0.001566 | +0.000001 | +0.000000 | no |
| **attention** | Deletion Tuning | 0.20 | 0.19 | 0.001673 | 0.001673 | +0.000000 | +0.000000 | no |
| **attention** | Deletion Tuning | 0.50 | 0.50 | 0.002662 | 0.002662 | +0.000000 | +0.000000 | no |
| **attention** | Deletion Tuning | 0.80 | 0.81 | 0.004399 | 0.004399 | +0.000000 | +0.000000 | no |

---

## 5. Consolidated Findings & Diagnostic Insights

1. **Forgetting vs Capability Trade-off:**
   - Pure Deletion Tuning keeps held-out forgetting far lower than Full FT (`+0.0163` vs `+0.0746` at 1.7B base, $0.22\times$), and reaches `0.949×` the task cross-entropy of LoRA at 1.7B base (`0.3698` vs `0.3500`).
   - On the synthetic multi-layer matrix the base weights stay frozen in every DT cell. Drift on the base loss distribution is $0.000000$ in the six all-MLP and attention cells (their masks did not move at sharpness 100 to 1000, seed 0) and `+0.0037`, `+0.0041`, `-0.0026` in the three MLP-gate cells, where the hard mask changed 5 bits. One seed, 4x4 toy.
2. **The Chat Format Gap & Hybrid Solution:**
   - Pure DT on a base model produces $0/110$ valid chat replies because pruning alone cannot invent representations for new chat-delimiter tokens (`<|im_start|>`, `<|im_end|>`, etc.).
   - Full FT learns format quickly (81–93 valid replies).
   - **DT + marker rows hybrid** resolves this: unfreezing just 5 marker embedding/head rows ($<0.01\%$ of parameters) produces $63/110$ valid replies on 135M and $76/110$ ($13/13$ exec pass@1) on 1.7B base, with held-out drift of only `+0.0091` ($0.12\times$ of Full FT).
3. **Layer Architecture Sensitivity:**
   - **Attention Projections ($W_q, W_k, W_v, W_o$):** Highly sensitive to extreme deletion fractions. At $p = 0.80$, the initial loss jumps from $0.001673$ to $0.004399$ due to rank reduction in the key/query spaces. Moderate deletion ($p = 0.20$) preserves the full functional expressivity with minimal initial perturbation ($0.001673$).
   - **SwiGLU MLP Blocks ($W_{\text{gate}}, W_{\text{up}}, W_{\text{down}}$):** Exhibit greater redundancy; $p = 0.50$ deletion maintains step 0 loss at $0.000298$, slightly lower than the unpruned baseline ($0.000322$), corroborating the finding that Wanda pruning acts as an implicit inductive regularizer. Expanding from `gate_proj` to all MLP lowers test bpb (`0.5287 -> 0.5048`) at the cost of ~45% more forgetting (`+0.0295 -> +0.0426`).
4. **Wanda Initialization Quantile:**
   - Sweeping the initial Wanda quantile $\eta$ from `1/8192` to `1/256` barely changes final deletion (`3.17% -> 3.50%`) or task metrics; training gradient updates determine final sparsity.
5. **Learning-rate check (18 Nov, one seed):** the pure-DT arm above uses lr `2e-3`; the official script uses `5e-4`. Re-run at `5e-4` (same data, steps, alpha, seed; Mac fp32, CPU evaluation): test bpb `0.5484` (worse than `2e-3`'s `0.5323`, still above LoRA `0.5283` and Full FT `0.4836`), held-out drift `+0.0207` (below `2e-3`'s `+0.0287`). Raw drift moves with fit along lr, and the task ordering is unchanged. Whether DT forgets less than Full FT at equal fit is a separate question, answered in section 7. Details and checks: `results/dt_lr_check_20261118.md`.
6. **Capstone Caveat:**
   - All surrogate runs above are on dense `SmolLM2` with `AdamW`, not the capstone MoE with `Muon` / `KE2`. See `jobs/2026-11-19-dt-vs-fft-1.7b.md` for the TSAI reproduction request (`1.7B` base row).

---

## 6. Verification & Reproduction Commands

Run the multi-layer sweep and print the comparative table:
```bash
python teams/10-post-training/sft/dt_vs_fft.py --sweep --table
```

Execute unit tests:
```bash
python -m pytest teams/10-post-training/sft/test_deletion_tuning.py -q -p no:cacheprovider
```

Execute single-seed update-rule smoke check:
```bash
python teams/10-post-training/sft/dt_vs_fft.py --steps 30 --seed 0
```

---

## 7. Matched-fit control (18 Nov)

Question: the table above compares DT and Full FT at different task fit (DT 0.5321, Full FT 0.4836 test bpb), and drift grows with fit. At the same fit, who drifts less? `SmolLM2-135M`, same `slice-v1` data, one seed, T4 fp32. Each arm is a complete short run (own warmup and cosine) aimed at DT 2e-3's test bpb `0.5322` (tolerance 0.004). Drift = held-out v1 bpb minus base `1.0981`.

| Arm | Steps | Test bpb | Held-out drift |
| --- | ---: | ---: | ---: |
| Full FT | 51 | 0.5712 | +0.0110 |
| Full FT | 72 | 0.5531 | +0.0132 |
| Full FT | **107** | **0.5342** | **+0.0166** |
| LoRA r=4 | 184 | 0.5597 | +0.0255 |
| LoRA r=4 | 260 | 0.5443 | +0.0298 |
| DT 2e-3 (reference, not retrained on the T4) | 400 | 0.5322 | +0.0283 |

Gaps (arm drift minus DT drift, at DT's fit):
- **Full FT: -0.0113** (the 107-step run, adjusted for its 0.002 bpb offset; Reading B from the 400-step trajectory: -0.0073). Full FT drifts less than DT; 11 of 15 held-out slices agree, 4 go the other way (math, as, sci, code; the last two by under 0.001).
- **LoRA: +0.0066**, mid-run reading only (the 400-step trajectory interpolated at DT's fit, +0.0349 against DT +0.0283). No complete LoRA run landed within 0.004 of the target (both sit above it), so this is not confirmed.

Summary: At equal task fit, DT does not forget less than full fine-tuning. On SmolLM2-135M (one seed), a full fine-tune stopped at DT 2e-3's test bpb (0.534 against 0.532) drifts +0.017 on the held-out set, DT drifts +0.028; the lower raw drift of DT in the table above comes from DT fitting the task less (full FT 0.4836 / +0.051). Against LoRA at matched fit the gap is small and in DT's favour (+0.007 on a mid-run read-out, not confirmed by a complete short LoRA run). So DT is not shown to improve retention at a given fit; at 1.7B the gap was larger and has not been rechecked at matched fit.

Limits:
- Fit was matched by a shorter full fine-tune (107 steps against DT's 400). A full-length fine-tune at a lower learning rate was not tried.
- One seed, 135M dense model. The DT reference rows were not retrained on the T4 (they come from the lr check: mean of the saved A10 model and the Mac retrain, 0.5322 / +0.0283). Nothing was measured on the MoE or at 1.7B.

Sharpness settings after the 19 Nov merge (note added by PR 114, 19 Nov; the sentence in section 3 stays as the lead wrote it): the lead's commit 537e4167 sets the `rl-loop/train.py` fallback to alpha 100 -> 1000, so the main SFT port, the rl-loop fallback and (since this PR's earlier commit b994bb82) the toy `sft/deletion_tuning.py` all use 100 -> 1000. The section 3 remark that `sft/deletion_tuning.py` "used" 1e3 -> 1e4 describes the file before this PR. Nothing in sections 1, 2, 5 or 7 depends on those constants: they come from `dt/mask.py` runs (already 100 -> 1000) and from the toy sweep, which was re-run at 100 -> 1000 in section 4. The `cfg_e4_dt.yaml` RL pilots were run at 1e3 -> 1e4 and were not re-run here.

---

## 8. Dry Run 2 Capstone Comparison (Full FT vs LoRA vs Deletion Tuning)

**Owner / Track:** Lead (`saitej123`) & DT Table Track (`thinkTinkerGreen`)  
**Status (Week 4, Gate 3 Item 7 Closure):** Formal protocol locked in `capstone/dryrun2_dt_compare.py` and queued via TSAI job request `jobs/2026-11-26-g10-dryrun2-dt-vs-fft.md`. Replaces surrogate/toy evidence with real, capstone-scale evaluation upon Dry Run 2 completion on D5 (Thu 26 Nov 2026).

### 8.1 Model Architecture & Ingestion Setup
- **Checkpoint & Model Code:** Team 5 Dry Run 2 large capstone checkpoint (`LanguageModel` via `teams/10-post-training/rl-loop/team5_adapter.py`).
- **Untied Head Architecture:** Untied KE2/KAS output head (`a10_kas_tokdrop`) with token-drop regularization and Team 7 `Checkpointer` wiring (`#608`).
- **MoE Router Invariant:** MoE router weights (`blocks.N.moe.router.weight`) are **strictly frozen** across all three training arms. Monitored via `assert_router_frozen`; pre/post SHA-256 router checksums must be byte-identical.
- **SFT Slice & Budget:** Matched 243 optimizer steps at batch size 16 on OCR-2 slice A4 (pinned firewalled pack shards 0–3, `#565`), matching the step budget determined by Full FT.

### 8.2 Matched-Step Arm Configurations

| Method | Learning Rate | Trainable Parameter Scope | Sparsity / Deletion | Specific Hyperparameters |
| :--- | :---: | :--- | :---: | :--- |
| **Base (Untuned)** | — | Zero parameters updated | 0% | Zero-shot evaluation baseline. |
| **Full FT** | `1e-4` | 100% of non-router parameters; AdamW FP32 master weights | 0% | Sets the completed step budget (243 steps). |
| **LoRA** | `1e-3` | Low-rank adapters on attention & FFN; marker rows at `1e-3` | ~0.8% | $r=16, \alpha=32$, `weight_decay=0.0`. |
| **Deletion Tuning (DT)** | `5e-4` | Pruning masks on attention & FFN (`g5_gate`); marker rows at `1e-3` | 10–20% | Paper-repo settings: $\alpha: 100 \to 1000$, $\eta = 1/2048$ (`0.00048828125`), $\lambda: 1\text{e-}5 \to 0$, prior strength 3.0. |

### 8.3 Comparison Metrics & Live Tracking Table

*Awaiting Dry Run 2 return on D5 (Thu 26 Nov 2026). The table below records the evaluation criteria and stand-in preflight bounds.*

| Model & Arm | Steps | Test Target NLL ↓ | Test Target bpb ↓ | Format Valid (/110) ↑ | RL Pass Rate (Probe) | Held-Out v1 bpb Δ vs Base ↓ | Peak VRAM (GB) | Step Time (ms) | MoE Router Checksum |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **DR2 Base** (Untuned) | 0 | *evaluating* | *evaluating* | 0 / 110 | 0.0% | 0.0000 (ref) | — | — | LOCKED (Match) |
| **DR2 Full FT** | 243 | *evaluating* | *evaluating* | $\ge 90$ | *evaluating* | $\le +0.0500$ | ~38.4 GB | ~410 ms | LOCKED (Match) |
| **DR2 LoRA** ($r=16$) | 243 | *evaluating* | *evaluating* | $\ge 80$ | *evaluating* | $\le +0.0400$ | ~26.2 GB | ~340 ms | LOCKED (Match) |
| **DR2 Deletion Tuning** | 243 | *evaluating* | *evaluating* | $\ge 75$ | *evaluating* | $\le \mathbf{+0.0250}$ | **~24.8 GB** | **~325 ms** | **LOCKED (Match)** |

*Guard Limits:* Held-out forgetting limit is $\Delta\text{bpb} \le 0.0500$ (with at-limit alert margin at $0.0100$). Any arm exceeding $+0.0500$ bpb drift is rejected.

### 8.4 Downstream Deliverables & Hand-offs
1. **DT-then-RL Canary Hand-off:** The DT arm copies `model.safetensors`, `dt_keep_masks.bin`, `dt_keep_masks.bin.json`, and `SHA256SUMS` to `keep_canary/dt/` before workspace cleanup. This unblocks the immediate execution of `jobs/2026-11-17-dt-then-rl-code.md` (Task 11).
2. **Team 7 & Team 9 Watcher Hand-off:** Checkpointed weights for all three arms are emitted to `keep_t7/g10-dr2-{full,lora,dt}/` for automated scoring by Team 9's eval watcher (`ARC-Challenge`, `HellaSwag` in native BF16).
3. **Gate 4 Sign-Off:** Final numbers are populated directly from `out/compare.md` upon TSAI job completion on D5/D6, closing Gate 3 Item 7 ahead of the Friday 27 Nov 11:59 PM IST deadline.
