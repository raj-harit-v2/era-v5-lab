"""Equal-step comparison of Deletion Tuning, LoRA, and full fine-tuning.

The local run uses synthetic slices so the update rules, layer targets
(MLP gate only, all MLP, attention), and deletion fractions (0.20, 0.50, 0.80)
can be checked without a GPU. The open-model run is the job request. This
script does not download a model and does not read benchmark items.

Usage:
    python teams/10-post-training/sft/dt_vs_fft.py --steps 30 --seed 0
    python teams/10-post-training/sft/dt_vs_fft.py --sweep --steps 30 --seed 0
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _dt():
    spec = importlib.util.spec_from_file_location("g10_deletion_tuning", HERE / "deletion_tuning.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DT = _dt()


def _copy(weight):
    return [row[:] for row in weight]


def _copy_weights(w_dict):
    return {k: [row[:] for row in v] for k, v in w_dict.items()}


def _flatten(weight):
    return [value for row in weight for value in row]


def _unflatten(values, rows, cols):
    return [values[row * cols:(row + 1) * cols] for row in range(rows)]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _matvec(M, v):
    return [_dot(row, v) for row in M]


def _softmax(vec):
    m = max(vec)
    exps = [math.exp(x - m) for x in vec]
    s = sum(exps)
    return [x / s for x in exps]


def _forward(weight, inputs):
    preds = []
    for sample in inputs:
        preds.append([math.tanh(sum(value * feature for value, feature in zip(row, sample))) for row in weight])
    return preds


def _task_loss(weight, inputs, targets):
    preds = _forward(weight, inputs)
    total = 0.0
    count = 0
    for pred, target in zip(preds, targets):
        for left, right in zip(pred, target):
            total += (left - right) * (left - right)
            count += 1
    return total / count


def _column_norms(inputs, cols):
    norms = []
    for col in range(cols):
        norms.append(math.sqrt(sum(sample[col] * sample[col] for sample in inputs)))
    return norms


def _synthetic_slice(rng, rows, cols, samples):
    base = [[rng.uniform(-0.3, 0.3) for _ in range(cols)] for _ in range(rows)]
    teacher = [[value + rng.uniform(-0.2, 0.2) for value in row] for row in base]
    inputs = [[rng.uniform(-1.0, 1.0) for _ in range(cols)] for _ in range(samples)]
    targets = _forward(teacher, inputs)
    return base, inputs, targets


def _effective(method, base, state, step, total_steps):
    rows = len(base)
    cols = len(base[0])
    if method == "fft":
        return state["weight"]
    if method == "lora":
        return [
            [base[row][col] + state["b"][row] * state["a"][col] for col in range(cols)]
            for row in range(rows)
        ]
    alpha = DT.sharpness(step, total_steps)
    masked = DT.apply_mask(base, DT.soft_mask(state["logits"], alpha))
    return masked


def _pack_grad(method, grad_weight, state):
    rows = len(grad_weight)
    cols = len(grad_weight[0])
    if method == "fft":
        return _flatten(grad_weight)
    if method == "lora":
        grad_a = [0.0] * cols
        grad_b = [0.0] * rows
        for row in range(rows):
            for col in range(cols):
                grad_a[col] += grad_weight[row][col] * state["b"][row]
                grad_b[row] += grad_weight[row][col] * state["a"][col]
        return grad_a + grad_b
    alpha = state["alpha"]
    mask = DT.soft_mask(state["logits"], alpha)
    flat_base = _flatten(state["base"])
    flat_grad = _flatten(grad_weight)
    grad_logits = []
    for base_value, grad_value, bit in zip(flat_base, flat_grad, mask):
        grad_logits.append(grad_value * base_value * alpha * bit * (1.0 - bit))
    return grad_logits


def _task_grad(weight, inputs, targets):
    rows = len(weight)
    cols = len(weight[0])
    grad = [[0.0] * cols for _ in range(rows)]
    preds = _forward(weight, inputs)
    scale = 2.0 / (len(inputs) * rows)
    for sample, pred, target in zip(inputs, preds, targets):
        for row in range(rows):
            residual = pred[row] - target[row]
            slope = 1.0 - pred[row] * pred[row]
            for col in range(cols):
                grad[row][col] += scale * residual * slope * sample[col]
    return grad


def _params(method, state):
    if method == "fft":
        return _flatten(state["weight"])
    if method == "lora":
        return state["a"] + state["b"]
    return state["logits"]


def _set_params(method, state, values):
    rows = len(state["base"])
    cols = len(state["base"][0])
    if method == "fft":
        state["weight"] = _unflatten(values, rows, cols)
    elif method == "lora":
        state["a"] = values[:cols]
        state["b"] = values[cols:]
    else:
        state["logits"] = values


def compare(steps: int = 30, seed: int = 0, rows: int = 4, cols: int = 4, samples: int = 32, lr: float = 0.2) -> dict:
    """Run the three methods for the same number of steps on one synthetic slice."""
    if steps <= 0:
        raise ValueError("steps must be positive")
    rng = random.Random(seed)
    base, inputs, targets = _synthetic_slice(rng, rows, cols, samples)
    scores = DT.wanda_scores(base, _column_norms(inputs, cols))
    logit_rng = random.Random(seed + 1)
    methods = {}
    for method in ("dt", "lora", "fft"):
        state = {"base": _copy(base)}
        if method == "fft":
            state["weight"] = _copy(base)
        elif method == "lora":
            lora_rng = random.Random(seed + 2)
            state["a"] = [lora_rng.gauss(0.0, 0.02) for _ in range(cols)]
            state["b"] = [0.0] * rows
        else:
            state["logits"] = DT.init_logits(scores, logit_rng)
        start_weight = _effective(method, base, state, 0, steps)
        loss_start = _task_loss(start_weight, inputs, targets)
        if method == "dt":
            loss_start = DT.deletion_loss(loss_start, start_weight)
        for step in range(steps):
            state["alpha"] = DT.sharpness(step, steps)
            current = _effective(method, base, state, step, steps)
            grad = _task_grad(current, inputs, targets)
            if method == "dt":
                # d/dG of -lambda * ||W * mask||^2, through the soft mask.
                alpha = state["alpha"]
                mask = DT.soft_mask(state["logits"], alpha)
                flat = _flatten(current)
                cursor = 0
                for row in range(rows):
                    for col in range(cols):
                        bit = mask[cursor]
                        extra = -2.0 * DT.LAMBDA_SFT * flat[cursor] * base[row][col] * alpha * bit * (1.0 - bit)
                        grad[row][col] += extra
                        cursor += 1
            packed = _pack_grad(method, grad, state)
            values = _params(method, state)
            _set_params(method, state, [value - lr * part for value, part in zip(values, packed)])
        end_weight = _effective(method, base, state, steps, steps)
        loss_end = _task_loss(end_weight, inputs, targets)
        if method == "dt":
            loss_end = DT.deletion_loss(loss_end, end_weight)
            keep = DT.hard_keep(state["logits"])
            deleted = keep.count(False) / len(keep)
        else:
            deleted = None
        methods[method] = {
            "steps": steps,
            "loss_start": loss_start,
            "loss_end": loss_end,
            "base_unchanged": state.get("weight", base) == base if method != "fft" else state["weight"] != base,
            "deleted_fraction": deleted,
        }
        if method == "fft":
            methods[method]["base_unchanged"] = False
            methods[method]["base_changed"] = state["weight"] != base
        else:
            methods[method]["base_changed"] = False
    return {"seed": seed, "steps": steps, "slice": "synthetic", "rows": samples, "methods": methods}


# ----------------------------------------------------------------------------------------------------------
# Multi-Layer Architecture & Forgetting Sweep (MLP gate only, all MLP, attention) across 3 deletion fractions
# ----------------------------------------------------------------------------------------------------------

class MultiLayerModel:
    """Models multi-matrix layer targets: mlp_gate, all_mlp, and attention."""

    def __init__(self, target_type: str = "mlp_gate", dim: int = 4, rng: random.Random | None = None):
        self.target_type = target_type
        self.dim = dim
        self.rng = rng or random.Random(0)
        self.weights = {}
        if target_type == "mlp_gate":
            self.weights["gate"] = [[self.rng.uniform(-0.3, 0.3) for _ in range(dim)] for _ in range(dim)]
        elif target_type == "all_mlp":
            self.weights["gate"] = [[self.rng.uniform(-0.3, 0.3) for _ in range(dim)] for _ in range(dim)]
            self.weights["up"] = [[self.rng.uniform(-0.3, 0.3) for _ in range(dim)] for _ in range(dim)]
            self.weights["down"] = [[self.rng.uniform(-0.3, 0.3) for _ in range(dim)] for _ in range(dim)]
        elif target_type == "attention":
            self.weights["q"] = [[self.rng.uniform(-0.3, 0.3) for _ in range(dim)] for _ in range(dim)]
            self.weights["k"] = [[self.rng.uniform(-0.3, 0.3) for _ in range(dim)] for _ in range(dim)]
            self.weights["v"] = [[self.rng.uniform(-0.3, 0.3) for _ in range(dim)] for _ in range(dim)]
            self.weights["o"] = [[self.rng.uniform(-0.3, 0.3) for _ in range(dim)] for _ in range(dim)]
        else:
            raise ValueError(f"Unknown target_type: {target_type!r}")

    def forward_sample(self, weights: dict[str, list[list[float]]], x):
        if self.target_type == "mlp_gate":
            return [math.tanh(val) for val in _matvec(weights["gate"], x)]
        elif self.target_type == "all_mlp":
            # SwiGLU: h = tanh(W_gate * x) * (W_up * x); y = W_down * h
            hg = [math.tanh(val) for val in _matvec(weights["gate"], x)]
            hu = _matvec(weights["up"], x)
            h = [g * u for g, u in zip(hg, hu)]
            return _matvec(weights["down"], h)
        elif self.target_type == "attention":
            # Multi-head attention with sequence of tokens
            q_proj = [_matvec(weights["q"], tok) for tok in x]
            k_proj = [_matvec(weights["k"], tok) for tok in x]
            v_proj = [_matvec(weights["v"], tok) for tok in x]
            scale = 1.0 / math.sqrt(self.dim)
            out_tokens = []
            for i in range(len(x)):
                logits = [_dot(q_proj[i], k_proj[j]) * scale for j in range(len(x))]
                attn = _softmax(logits)
                context = [sum(attn[j] * v_proj[j][d] for j in range(len(x))) for d in range(self.dim)]
                out_tokens.append(_matvec(weights["o"], context))
            return out_tokens

    def forward(self, weights: dict[str, list[list[float]]], inputs):
        return [self.forward_sample(weights, x) for x in inputs]

    def loss(self, weights: dict[str, list[list[float]]], inputs, targets) -> float:
        preds = self.forward(weights, inputs)
        total = 0.0
        count = 0
        if self.target_type == "attention":
            for pred_seq, targ_seq in zip(preds, targets):
                for pred, targ in zip(pred_seq, targ_seq):
                    for p, t in zip(pred, targ):
                        total += (p - t) * (p - t)
                        count += 1
        else:
            for pred, targ in zip(preds, targets):
                for p, t in zip(pred, targ):
                    total += (p - t) * (p - t)
                    count += 1
        return total / count

    def grad(self, weights: dict[str, list[list[float]]], inputs, targets, eps: float = 1e-5) -> dict[str, list[list[float]]]:
        if self.target_type == "mlp_gate":
            rows = len(weights["gate"])
            cols = len(weights["gate"][0])
            g = [[0.0] * cols for _ in range(rows)]
            preds = self.forward(weights, inputs)
            scale = 2.0 / (len(inputs) * rows)
            for x, pred, targ in zip(inputs, preds, targets):
                for r in range(rows):
                    res = pred[r] - targ[r]
                    slope = 1.0 - pred[r] * pred[r]
                    factor = scale * res * slope
                    for c in range(cols):
                        g[r][c] += factor * x[c]
            return {"gate": g}
        else:
            grads = {}
            for name, mat in weights.items():
                g_mat = []
                for r in range(len(mat)):
                    g_row = []
                    for c in range(len(mat[0])):
                        orig = mat[r][c]
                        mat[r][c] = orig + eps
                        l_plus = self.loss(weights, inputs, targets)
                        mat[r][c] = orig - eps
                        l_minus = self.loss(weights, inputs, targets)
                        mat[r][c] = orig
                        g_row.append((l_plus - l_minus) / (2.0 * eps))
                    g_mat.append(g_row)
                grads[name] = g_mat
            return grads


def _sweep_column_norms(inputs, cols, target_type):
    if target_type == "attention":
        flat_inputs = [tok for seq in inputs for tok in seq]
    else:
        flat_inputs = inputs
    norms = []
    for col in range(cols):
        norms.append(math.sqrt(sum(sample[col] * sample[col] for sample in flat_inputs)))
    return norms


def compare_sweep_cell(
    target_type: str = "mlp_gate",
    method: str = "dt",
    eta: float = 0.20,
    steps: int = 30,
    seed: int = 0,
    lr: float = 0.2,
    dim: int = 4,
    samples: int = 32,
) -> dict:
    """Evaluates task gain and catastrophic forgetting for a single cell."""
    rng = random.Random(seed)
    model = MultiLayerModel(target_type, dim=dim, rng=rng)
    base_weights = _copy_weights(model.weights)

    # Base task distribution (pre-trained distribution)
    if target_type == "attention":
        base_inputs = [[[rng.uniform(-1.0, 1.0) for _ in range(dim)] for _ in range(2)] for _ in range(samples)]
        task_inputs = [[[rng.uniform(-1.0, 1.0) for _ in range(dim)] for _ in range(2)] for _ in range(samples)]
    else:
        base_inputs = [[rng.uniform(-1.0, 1.0) for _ in range(dim)] for _ in range(samples)]
        task_inputs = [[rng.uniform(-1.0, 1.0) for _ in range(dim)] for _ in range(samples)]

    base_targets = model.forward(base_weights, base_inputs)

    # Fine-tuning task teacher (shifted weights)
    teacher_weights = _copy_weights(base_weights)
    for k in teacher_weights:
        for r in range(len(teacher_weights[k])):
            for c in range(len(teacher_weights[k][0])):
                teacher_weights[k][r][c] += rng.uniform(-0.2, 0.2)
    task_targets = model.forward(teacher_weights, task_inputs)

    col_norms = _sweep_column_norms(task_inputs, dim, target_type)

    state = {}
    if method == "fft":
        state["weights"] = _copy_weights(base_weights)
    elif method == "lora":
        lora_rng = random.Random(seed + 2)
        state["lora_a"] = {}
        state["lora_b"] = {}
        for k, mat in base_weights.items():
            state["lora_a"][k] = [lora_rng.gauss(0.0, 0.02) for _ in range(dim)]
            state["lora_b"][k] = [0.0] * dim
    elif method == "dt":
        state["logits"] = {}
        logit_rng = random.Random(seed + 1)
        for k, mat in base_weights.items():
            scores = DT.wanda_scores(mat, col_norms)
            state["logits"][k] = DT.init_logits(scores, logit_rng, eta=eta)

    def get_effective(step, is_eval=False):
        if method == "fft":
            return state["weights"]
        elif method == "lora":
            eff = {}
            for k, mat in base_weights.items():
                rows = len(mat)
                cols = len(mat[0])
                eff[k] = [
                    [mat[r][c] + state["lora_b"][k][r] * state["lora_a"][k][c] for c in range(cols)]
                    for r in range(rows)
                ]
            return eff
        else:  # dt
            eff = {}
            alpha = DT.sharpness(step, steps)
            for k, mat in base_weights.items():
                if is_eval:
                    keep = DT.hard_keep(state["logits"][k])
                    mask = [1.0 if b else 0.0 for b in keep]
                else:
                    mask = DT.soft_mask(state["logits"][k], alpha)
                eff[k] = DT.apply_mask(mat, mask)
            return eff

    # Step 0 evaluation
    start_eff = get_effective(0, is_eval=True)
    task_loss_start = model.loss(start_eff, task_inputs, task_targets)
    base_loss_start = model.loss(start_eff, base_inputs, base_targets)

    # 30-step training loop
    for step in range(steps):
        current_eff = get_effective(step, is_eval=False)
        grads = model.grad(current_eff, task_inputs, task_targets)
        alpha = DT.sharpness(step, steps)

        if method == "fft":
            for k in state["weights"]:
                for r in range(dim):
                    for c in range(dim):
                        state["weights"][k][r][c] -= lr * grads[k][r][c]
        elif method == "lora":
            for k in base_weights:
                for r in range(dim):
                    for c in range(dim):
                        g_val = grads[k][r][c]
                        state["lora_a"][k][c] -= lr * g_val * state["lora_b"][k][r]
                        state["lora_b"][k][r] -= lr * g_val * state["lora_a"][k][c]
        elif method == "dt":
            for k in base_weights:
                mat = base_weights[k]
                mask = DT.soft_mask(state["logits"][k], alpha)
                flat_curr = _flatten(current_eff[k])
                flat_base = _flatten(mat)
                flat_grad = _flatten(grads[k])
                new_logits = list(state["logits"][k])
                for idx in range(len(new_logits)):
                    bit = mask[idx]
                    d_task = flat_grad[idx] * flat_base[idx] * alpha * bit * (1.0 - bit)
                    d_reg = -2.0 * DT.LAMBDA_SFT * flat_curr[idx] * flat_base[idx] * alpha * bit * (1.0 - bit)
                    total_g = d_task + d_reg
                    new_logits[idx] -= lr * total_g
                state["logits"][k] = new_logits

    # Final step evaluation
    end_eff = get_effective(steps, is_eval=True)
    task_loss_end = model.loss(end_eff, task_inputs, task_targets)
    base_loss_end = model.loss(end_eff, base_inputs, base_targets)

    if method == "dt":
        all_keeps = []
        for k in state["logits"]:
            all_keeps.extend(DT.hard_keep(state["logits"][k]))
        deleted_frac = all_keeps.count(False) / len(all_keeps)
    else:
        deleted_frac = 0.0

    return {
        "target_type": target_type,
        "method": method,
        "eta": eta if method == "dt" else None,
        "task_loss_start": task_loss_start,
        "task_loss_end": task_loss_end,
        "task_gain": task_loss_start - task_loss_end,
        "base_loss_start": base_loss_start,
        "base_loss_end": base_loss_end,
        "forgetting": base_loss_end - base_loss_start,
        "base_changed": (method == "fft"),
        "deleted_fraction": deleted_frac,
    }


def compare_sweep(
    steps: int = 30,
    seed: int = 0,
    layer_targets: tuple[str, ...] = ("mlp_gate", "all_mlp", "attention"),
    deletion_fractions: tuple[float, ...] = (0.20, 0.50, 0.80),
    lr: float = 0.2,
) -> dict:
    """Runs the full evaluation across layer targets, deletion fractions, and baselines."""
    results = []
    layer_labels = {
        "mlp_gate": "MLP gate only",
        "all_mlp": "all MLP",
        "attention": "attention",
    }
    for layer in layer_targets:
        layer_label = layer_labels.get(layer, layer)
        # 1. Full fine-tuning baseline
        fft_res = compare_sweep_cell(target_type=layer, method="fft", steps=steps, seed=seed, lr=lr)
        fft_res["layer_label"] = layer_label
        results.append(fft_res)

        # 2. LoRA baseline
        lora_res = compare_sweep_cell(target_type=layer, method="lora", steps=steps, seed=seed, lr=lr)
        lora_res["layer_label"] = layer_label
        results.append(lora_res)

        # 3. Deletion Tuning across 3 deletion fractions
        for p in deletion_fractions:
            dt_res = compare_sweep_cell(target_type=layer, method="dt", eta=p, steps=steps, seed=seed, lr=lr)
            dt_res["layer_label"] = layer_label
            results.append(dt_res)

    return {
        "seed": seed,
        "steps": steps,
        "layer_targets": list(layer_targets),
        "deletion_fractions": list(deletion_fractions),
        "records": results,
    }


def format_markdown_table(sweep_report: dict) -> str:
    """Formats sweep report into GitHub Flavored Markdown table."""
    lines = [
        "| Layer Target | Method | Target Deletion Fraction | Deleted Fraction | Task Loss (Step 0) | Task Loss (Step 30) | Task Gain (Δ Loss) | Forgetting (Δ Base Loss) | Base Weight Changed |",
        "|---|---|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for r in sweep_report["records"]:
        method_name = "Full Fine-Tuning" if r["method"] == "fft" else ("LoRA (rank 1)" if r["method"] == "lora" else "Deletion Tuning")
        target_del = f"{r['eta']:.2f}" if r["eta"] is not None else "-"
        del_frac = f"{r['deleted_fraction']:.2f}" if r["deleted_fraction"] > 0 else "0.00"
        changed = "yes" if r["base_changed"] else "no"
        lines.append(
            f"| {r['layer_label']} | {method_name} | {target_del} | {del_frac} | {r['task_loss_start']:.6f} | {r['task_loss_end']:.6f} | {r['task_gain']:+.6f} | {r['forgetting']:+.6f} | {changed} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--sweep", action="store_true", help="Run full sweep across 3 layer targets and 3 deletion fractions")
    parser.add_argument("--table", action="store_true", help="Print formatted markdown table")
    args = parser.parse_args()

    if args.sweep:
        report = compare_sweep(steps=args.steps, seed=args.seed)
        if args.table:
            print(format_markdown_table(report))
        else:
            print(json.dumps(report, indent=2))
    else:
        print(json.dumps(compare(steps=args.steps, seed=args.seed), indent=2))


if __name__ == "__main__":
    main()
