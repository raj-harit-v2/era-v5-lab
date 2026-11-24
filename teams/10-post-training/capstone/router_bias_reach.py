"""How much Team 5's loss-free balancer bias changes routing and loss on a delivered run folder.

Team 5's MoE (#748, teams/05-architecture/harness/week2/model.py) chooses experts with
`topk(scores + router_bias)` when `moe.bias_gamma != 0` and with plain `topk(scores)` when it is 0; the gate values stay the
unbiased softmax either way. So a reader that drops the bias (a missing buffer zero-filled on load, #750, or a model built
from an arm with gamma 0) routes like `router_bias = 0`. This script measures, on held-out windows, per MoE layer:

- `set_changed`: share of valid (token, layer) positions whose chosen expert SET differs between bias as delivered and
  bias zeroed (G12's measure on 23 Nov: "share of positions whose chosen expert set changes");
- `top1_agree`: share of positions whose highest-ranked chosen expert is the same (G12 also reported this);
- `bias_absmax`;
and, over the whole model, the mean next-token NLL with the bias as delivered and with every `router_bias` zeroed (the
same computation as gamma 0, since gamma 0 takes `topk(scores)` and the same unbiased gates).

Team 5's code only (Artifacts, LanguageModel, DocumentWindows, train_week2.scored_ntp_loss); eval mode, fp32, no autocast.

    python capstone/router_bias_reach.py --g5-root <lab> --run-folder <run folder with checkpoint.pt> \
        --tokenizer <tokenizer.json> --byte-table <raw_table_P32.npz> --heldout <heldout jsonl> [--windows 8] --out <json>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def reach(model, batches, moe_cls, scored_ntp_loss) -> dict:
    """batches: list of (x, y) with y == -100 at unscored positions. Returns per-layer and whole-model numbers."""
    import torch  # noqa: PLC0415

    moes = [(n, m) for n, m in model.named_modules() if isinstance(m, moe_cls)]
    stats = {n: {"positions": 0, "set_changed": 0, "top1_agree": 0} for n, _ in moes}

    def hook(name):
        def pre(mod, args):
            x, valid = args[0], args[1]
            flat = x.reshape(-1, x.shape[-1]).float()
            active = valid.reshape(-1)
            scores = torch.nn.functional.linear(flat, mod.router.weight.float()).softmax(-1)
            biased = (scores + mod.router_bias.to(scores.dtype)).topk(mod.topk, dim=-1).indices
            plain = scores.topk(mod.topk, dim=-1).indices
            same_set = (biased.sort(-1).values == plain.sort(-1).values).all(-1)
            s = stats[name]
            s["positions"] += int(active.sum())
            s["set_changed"] += int((~same_set & active).sum())
            s["top1_agree"] += int(((biased[:, 0] == plain[:, 0]) & active).sum())
        return pre

    handles = [m.register_forward_pre_hook(hook(n)) for n, m in moes]
    model.eval()
    try:
        with torch.no_grad():
            nll_b = tok = 0.0
            for x, y in batches:
                nll_b += float(scored_ntp_loss(model, x, y))
                tok += int((y != -100).sum())
    finally:
        for h in handles:
            h.remove()
    saved = {n: m.router_bias.detach().clone() for n, m in moes}
    gammas = {n: m.balance_gamma for n, m in moes}
    try:
        for _, m in moes:
            m.router_bias.zero_()
        with torch.no_grad():
            nll_0 = sum(float(scored_ntp_loss(model, x, y)) for x, y in batches)
    finally:
        for n, m in moes:
            m.router_bias.copy_(saved[n])
    layers = {n: {"bias_absmax": float(saved[n].abs().max()), "bias_gamma": gammas[n], "positions": s["positions"],
                  "set_changed": s["set_changed"] / max(s["positions"], 1), "top1_agree": s["top1_agree"] / max(s["positions"], 1)}
              for n, s in stats.items()}
    return {"layers": layers, "scored_tokens": tok, "mean_nll_bias_as_delivered": nll_b / tok,
            "mean_nll_bias_zeroed": nll_0 / tok, "nll_change_if_dropped": (nll_0 - nll_b) / tok,
            "note": "bias read only when bias_gamma != 0; zeroed bias == the gamma-0 path (same unbiased gates)"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--g5-root", type=Path, required=True)
    ap.add_argument("--run-folder", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--byte-table", type=Path, required=True)
    ap.add_argument("--heldout", type=Path, required=True)
    ap.add_argument("--windows", type=int, default=8, help="held-out windows (0..N-1), one per forward")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    harness = (a.g5_root / "teams" / "05-architecture" / "harness").resolve()
    sys.path.insert(0, str(harness))
    import torch  # noqa: PLC0415
    from train_week2 import scored_ntp_loss  # noqa: PLC0415
    from week2.artifacts import Artifacts  # noqa: PLC0415
    from week2.data import DocumentWindows  # noqa: PLC0415
    from week2.model import MoE, LanguageModel  # noqa: PLC0415

    t0 = time.time()
    man = json.loads((a.run_folder / "manifest.json").read_text(encoding="utf8"))
    cfg, want = man["config"], man["artifacts"]
    art = Artifacts(a.tokenizer, a.byte_table, expected_tokenizer_sha=want["tokenizer_sha256"], expected_vocab=want["vocab_size"])
    model = LanguageModel(cfg["model"], art.bytes, art.lengths)
    ck = torch.load(a.run_folder / "checkpoint.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(ck["model"], strict=True)
    model.to(a.device)
    val = DocumentWindows(a.heldout, art, cfg["model"]["block_size"])
    n = min(a.windows, len(val.windows))
    batches = [val.batch([i], torch.device(a.device))[:2] for i in range(n)]
    rec = reach(model, batches, MoE, scored_ntp_loss)
    rec.update({"run_folder": str(a.run_folder), "windows": n, "head_mode": cfg["model"].get("head_mode", "dense"),
                "seconds": round(time.time() - t0, 1)})
    a.out.write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("scored_tokens", "mean_nll_bias_as_delivered", "mean_nll_bias_zeroed",
                                          "nll_change_if_dropped")} | {"layers": rec["layers"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
