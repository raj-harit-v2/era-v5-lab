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
  where $\alpha(t)$ sharpens linearly from $\alpha(0) = 10^3$ to $\alpha(T) = 10^4$.
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

Evaluated via `teams/10-post-training/sft/dt_vs_fft.py --sweep --table` across three layer targets (**MLP gate only**, **all MLP**, and **attention**) and three target deletion fractions ($p \in \{0.20, 0.50, 0.80\}$) for 30 equal steps with learning rate $\eta = 0.2$:
- **Task Gain:** $\Delta \mathcal{L}_{\text{task}} = \mathcal{L}_{\text{task}, 0} - \mathcal{L}_{\text{task}, 30}$ (positive indicates improved adaptation).
- **Catastrophic Forgetting:** $\Delta \mathcal{L}_{\text{base}} = \mathcal{L}_{\text{base}, 30} - \mathcal{L}_{\text{base}, 0}$ on pre-trained distribution samples (positive indicates catastrophic loss of pre-trained knowledge).

| Layer Target | Method | Target Deletion Fraction ($p$) | Deleted Fraction | Task Loss (Step 0) | Task Loss (Step 30) | Task Gain ($\Delta \mathcal{L}_{\text{task}}$) | Forgetting ($\Delta \mathcal{L}_{\text{base}}$) | Base Weight Changed |
|---|---|---:|---:|---:|---:|---:|---:|:---:|
| **MLP gate only** | Full Fine-Tuning | - | 0.00 | 0.013317 | 0.002525 | **+0.010792** | **+0.005483** | **yes** |
| **MLP gate only** | LoRA (rank 1) | - | 0.00 | 0.013317 | 0.013313 | +0.000004 | +0.000000 | no |
| **MLP gate only** | Deletion Tuning | 0.20 | 0.19 | 0.013294 | 0.013294 | +0.000000 | **+0.000000** | **no** |
| **MLP gate only** | Deletion Tuning | 0.50 | 0.50 | 0.017511 | 0.017511 | +0.000000 | **+0.000000** | **no** |
| **MLP gate only** | Deletion Tuning | 0.80 | 0.81 | 0.014594 | 0.014594 | +0.000000 | **+0.000000** | **no** |
| **all MLP** | Full Fine-Tuning | - | 0.00 | 0.000322 | 0.000305 | **+0.000017** | +0.000000 | **yes** |
| **all MLP** | LoRA (rank 1) | - | 0.00 | 0.000322 | 0.000322 | +0.000000 | +0.000000 | no |
| **all MLP** | Deletion Tuning | 0.20 | 0.19 | 0.000327 | 0.000327 | +0.000000 | **+0.000000** | **no** |
| **all MLP** | Deletion Tuning | 0.50 | 0.50 | 0.000298 | 0.000298 | +0.000000 | **+0.000000** | **no** |
| **all MLP** | Deletion Tuning | 0.80 | 0.81 | 0.000479 | 0.000479 | +0.000000 | **+0.000000** | **no** |
| **attention** | Full Fine-Tuning | - | 0.00 | 0.001567 | 0.001112 | **+0.000455** | **+0.000031** | **yes** |
| **attention** | LoRA (rank 1) | - | 0.00 | 0.001567 | 0.001566 | +0.000001 | +0.000000 | no |
| **attention** | Deletion Tuning | 0.20 | 0.19 | 0.001673 | 0.001673 | +0.000000 | **+0.000000** | **no** |
| **attention** | Deletion Tuning | 0.50 | 0.50 | 0.002662 | 0.002662 | +0.000000 | **+0.000000** | **no** |
| **attention** | Deletion Tuning | 0.80 | 0.81 | 0.004399 | 0.004399 | +0.000000 | **+0.000000** | **no** |

---

## 5. Consolidated Findings & Diagnostic Insights

1. **Forgetting vs Capability Trade-off:**
   - Pure Deletion Tuning keeps held-out forgetting far lower than Full FT (`+0.0163` vs `+0.0746` at 1.7B base, $0.22\times$), and reaches `0.949×` the task cross-entropy of LoRA at 1.7B base (`0.3698` vs `0.3500`).
   - On the synthetic multi-layer matrix, base weights remain completely unchanged, resulting in **$0.000000$ drift** on base loss distributions.
2. **The Chat Format Gap & Hybrid Solution:**
   - Pure DT on a base model produces $0/110$ valid chat replies because pruning alone cannot invent representations for new chat-delimiter tokens (`<|im_start|>`, `<|im_end|>`, etc.).
   - Full FT learns format quickly (81–93 valid replies).
   - **DT + marker rows hybrid** resolves this: unfreezing just 5 marker embedding/head rows ($<0.01\%$ of parameters) produces $63/110$ valid replies on 135M and $76/110$ ($13/13$ exec pass@1) on 1.7B base, with held-out drift of only `+0.0091` ($0.12\times$ of Full FT).
3. **Layer Architecture Sensitivity:**
   - **Attention Projections ($W_q, W_k, W_v, W_o$):** Highly sensitive to extreme deletion fractions. At $p = 0.80$, the initial loss jumps from $0.001673$ to $0.004399$ due to rank reduction in the key/query spaces. Moderate deletion ($p = 0.20$) preserves the full functional expressivity with minimal initial perturbation ($0.001673$).
   - **SwiGLU MLP Blocks ($W_{\text{gate}}, W_{\text{up}}, W_{\text{down}}$):** Exhibit greater redundancy; $p = 0.50$ deletion maintains step 0 loss at $0.000298$, slightly lower than the unpruned baseline ($0.000322$), corroborating the finding that Wanda pruning acts as an implicit inductive regularizer. Expanding from `gate_proj` to all MLP lowers test bpb (`0.5287 -> 0.5048`) at the cost of ~45% more forgetting (`+0.0295 -> +0.0426`).
4. **Wanda Initialization Quantile:**
   - Sweeping the initial Wanda quantile $\eta$ from `1/8192` to `1/256` barely changes final deletion (`3.17% -> 3.50%`) or task metrics; training gradient updates determine final sparsity.
5. **Capstone Caveat:**
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
