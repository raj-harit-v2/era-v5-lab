"""Group-relative policy-gradient losses. The algorithm is a config choice, because TSAI picks it at Gate 4.

For one prompt with k sampled completions and rewards r_1..r_k:

    algo       advantage A_i                         ratio                         reduction over tokens
    grpo       (r_i - mean) / (std + eps)            per token                     mean per sequence, then mean
    dr_grpo    r_i - mean                            per token                     sum / max_new  (no length bias)
    rloo       r_i - mean of the other k-1 rewards   per token                     sum / max_new
    gspo       (r_i - mean) / (std + eps)            per sequence: exp(mean token  one term per sequence
                                                     log-ratio), proposed for MoE

std is the population std (divide by k). A group whose rewards are all equal has no signal: advantages() returns
None and the trainer drops it (DAPO's dynamic sampling, arXiv 2503.14476). The surrogate is PPO-clipped:
min(ratio * A, clip(ratio, 1 - eps, 1 + eps) * A). The optional KL to a reference policy uses the k3 estimator
exp(ref - new) - (ref - new) - 1 per token.

Sources: GRPO (DeepSeekMath, arXiv 2402.03300), Dr. GRPO (arXiv 2503.20783), RLOO (arXiv 2402.14740),
GSPO (arXiv 2507.18071).
"""
from __future__ import annotations

import torch

ALGOS = ("grpo", "dr_grpo", "rloo", "gspo")
OBJECTIVE_V1 = "objective_v1"  # the lead's Session 18 contract (rl/objective_v1.md, commit ff19ce2); see below
ALL_ALGOS = ALGOS + (OBJECTIVE_V1,)


def advantages(rewards: torch.Tensor, algo: str, eps: float = 1e-4) -> torch.Tensor | None:
    if algo not in ALL_ALGOS:
        raise ValueError(f"unknown algo {algo!r}; choose from {ALL_ALGOS}")
    r = rewards.float()
    if r.numel() < 2 or torch.all(r == r[0]):
        return None
    if algo == OBJECTIVE_V1:  # r_i - mean(r), no std division; mean in float64 like the reference
        r64 = rewards.double()
        return (r64 - r64.mean()).float()
    mean = r.mean()
    if algo in ("grpo", "gspo"):
        return (r - mean) / (r.std(correction=0) + eps)
    if algo == "dr_grpo":
        return r - mean
    k = r.numel()
    return (r - mean) * k / (k - 1)  # r_i - mean of the others


def tis_weights(old_lp: torch.Tensor, rollout_lp: torch.Tensor, mask: torch.Tensor, algo: str,
                clip_max: float) -> torch.Tensor:
    """Truncated importance weights for the sampler/trainer gap (TIS; Yao et al. 2025, research/g10_gpu/q3).

    The completions were sampled by vLLM (rollout_lp) but the PPO ratio uses the trainer's own logprobs (old_lp),
    so each term is re-weighted by pi_train_old / pi_rollout, truncated at clip_max so one token can't dominate.
    Token level for grpo, dr_grpo and rloo ([k, T]); sequence level for gspo ([k], geometric mean over tokens),
    to match its sequence ratio. Detached: the weights scale the gradient, they don't receive one.
    """
    m = mask.float()
    d = (old_lp - rollout_lp).detach() * m
    if algo == "gspo":
        return torch.exp(d.sum(-1) / m.sum(-1).clamp_min(1)).clamp(max=clip_max)
    return torch.exp(d).clamp(max=clip_max) * m


def mismatch(old_lp: torch.Tensor, rollout_lp: torch.Tensor, mask: torch.Tensor) -> dict:
    """How far the sampler is from the trainer on the sampled tokens: mean |log ratio| and the K3 estimate of
    KL(sampler || trainer), exp(r) - 1 - r with r = log pi_train - log pi_rollout."""
    m = mask.float()
    r = (old_lp - rollout_lp).detach() * m
    n = m.sum().clamp_min(1)
    return {"abs_logratio": float((r.abs()).sum() / n), "k3": float(((torch.exp(r) - 1 - r) * m).sum() / n)}


def policy_loss(new_lp: torch.Tensor, old_lp: torch.Tensor, adv: torch.Tensor, mask: torch.Tensor, algo: str,
                clip_eps: float = 0.2, ref_lp: torch.Tensor | None = None, kl_coef: float = 0.0,
                is_weight: torch.Tensor | None = None) -> tuple[torch.Tensor, dict]:
    """new_lp, old_lp, ref_lp, mask: [k, T]; adv: [k]; is_weight: tis_weights() or None. Returns (loss, stats)."""
    m = mask.float()
    n_tok = m.sum(-1).clamp_min(1)
    log_ratio = (new_lp - old_lp) * m
    if algo == "gspo":
        seq_ratio = torch.exp(log_ratio.sum(-1) / n_tok)
        surr = torch.minimum(seq_ratio * adv, seq_ratio.clamp(1 - clip_eps, 1 + clip_eps) * adv)
        if is_weight is not None:
            surr = surr * is_weight
        loss = -surr.mean()
        clipped = ((seq_ratio - 1).abs() > clip_eps).float().mean()
        ratio_mean = seq_ratio.mean()
    else:
        ratio = torch.exp(log_ratio)
        a = adv[:, None]
        surr = torch.minimum(ratio * a, ratio.clamp(1 - clip_eps, 1 + clip_eps) * a) * m
        if is_weight is not None:
            surr = surr * is_weight
        if algo == "grpo":
            loss = -(surr.sum(-1) / n_tok).mean()
        else:  # dr_grpo, rloo: constant normaliser, no per-sequence length division
            loss = -surr.sum() / (m.shape[0] * m.shape[1])
        clipped = ((((ratio - 1).abs() > clip_eps).float() * m).sum() / m.sum().clamp_min(1))
        ratio_mean = (ratio * m).sum() / m.sum().clamp_min(1)
    kl = torch.zeros((), device=new_lp.device)
    if ref_lp is not None and kl_coef > 0:
        d = (ref_lp - new_lp) * m
        kl = ((torch.exp(d) - d - 1) * m).sum() / m.sum().clamp_min(1)
        loss = loss + kl_coef * kl
    return loss, {"clip_frac": float(clipped.detach()), "ratio_mean": float(ratio_mean.detach()), "kl": float(kl.detach())}


# --- objective_v1: the lead's Session 18 objective in the batched trainer ---------------------------------------
#
# Contract (rl/objective_v1.md and objective_v1.py at ff19ce2, owned by the lead; reproduced here, not changed):
#   A_i     = r_i - mean(r) for a group whose rewards are not all equal; equal-reward and singleton groups are dropped
#             (absent from the numerator AND the denominator)
#   rho_it  = pi_theta(y_it) / pi_sampler(y_it), the importance ratio against the policy that sampled the token
#   m_it    = 1 when 1 - eps <= rho_it <= 1 + eps (closed bounds), else 0; eps = 0.2
#   L       = - sum_{kept groups, i, t} m_it * A_i * log pi_theta(y_it) / T
#   T       = number of real (unpadded) completion tokens in kept groups; a masked token adds 0 and still counts
#   T == 0 or no kept group -> no loss, the trainer skips the optimizer step
# The loss is plain -A * log pi: no ratio weighting, no PPO clipping, no reference KL, no entropy term. The mask is
# computed from detached values, so it selects tokens and never receives a gradient. T is batch-global (all kept groups
# of the step), so objective_v1_terms() returns the un-normalised numerator and the caller divides by T once.

TR_EPSILON = 0.2


def trust_region_mask(ratio: torch.Tensor, eps: float = TR_EPSILON) -> torch.Tensor:
    """Bool mask, True inside the closed region [1 - eps, 1 + eps] (same comparisons as the reference)."""
    if not (eps >= 0 and eps < float("inf")):
        raise ValueError("eps must be finite and >= 0")
    return (ratio >= 1.0 - eps) & (ratio <= 1.0 + eps)


def objective_v1_terms(new_lp: torch.Tensor, sampler_lp: torch.Tensor, adv: torch.Tensor, cmask: torch.Tensor,
                       eps: float = TR_EPSILON) -> tuple[torch.Tensor, dict]:
    """new_lp (differentiable), sampler_lp, cmask: [k, T]; adv: [k] (one kept group or a row chunk of it).

    Returns (numerator, stats): numerator = -sum(m * A * new_lp) over real tokens (divide by the batch T), and
    device tensors (no host sync) tokens, inside, masked_pos, masked_neg, tokens_pos, tokens_neg, nonfinite.
    `nonfinite` counts REAL tokens whose current/sampler log-probability or computed ratio is NaN/inf; the reference rejects those
    inputs, so callers must raise when it is nonzero (train.py checks it once per epoch, before the optimizer step).
    Padding values are never inspected.
    The ratio is evaluated in float64 from detached log-probabilities so that a ratio at a boundary is compared
    the way the reference compares Python floats. Padding never enters the ratio (it is set to 0 before exp).
    """
    real = cmask.bool()
    diff = torch.where(real, new_lp.detach().double() - sampler_lp.detach().double(), 0.0)
    ratio = torch.exp(diff)
    inside = trust_region_mask(ratio, eps) & real
    a = adv.to(new_lp.dtype)[:, None]
    num = -(torch.where(inside, new_lp, 0.0) * a).sum()
    pos, neg = (adv > 0)[:, None] & real, (adv < 0)[:, None] & real
    out = ~inside & real
    bad = (~torch.isfinite(new_lp.detach()) | ~torch.isfinite(sampler_lp.detach()) | ~torch.isfinite(ratio)) & real
    stats = {"tokens": real.sum(), "inside": inside.sum(), "masked_pos": (out & pos).sum(),
             "masked_neg": (out & neg).sum(), "tokens_pos": pos.sum(), "tokens_neg": neg.sum(), "nonfinite": bad.sum()}
    return num, stats


def objective_v1_loss(new_lp: torch.Tensor, sampler_lp: torch.Tensor, adv: torch.Tensor, cmask: torch.Tensor,
                      eps: float = TR_EPSILON) -> tuple[torch.Tensor, dict]:
    """Single-group convenience (benchmarks, tests): numerator / T for this group alone. The trainer divides by the
    batch-global T instead (train.backward_objective_v1)."""
    num, st = objective_v1_terms(new_lp, sampler_lp, adv, cmask, eps)
    if int(st["nonfinite"]):  # one host sync; this helper is for tests and benchmarks
        raise ValueError("non-finite log-probability or ratio on a real token (objective_v1 contract)")
    return num / st["tokens"].clamp_min(1), st
