"""Evidence probe for the toy DT sweep (sft/dt_vs_fft.py). Does not change product code.

It reads sft/dt_vs_fft.py, adds read-only measurement of the DT cells in memory, runs the sweep
and prints, per seed: hard-mask bits that flipped between init and end, deleted share at init and
end, max |delta G|, mean sigmoid slope at the first and last step, and the share of logits with
|alpha * G| < log(99).

  python3 -I teams/10-post-training/results/dt_toy_sharpness_check_20261117/probe.py \
      --sharpness 100 1000 --seeds 0 1 2            # current default
  ... --sharpness 1000 10000 ...                    # the old setting
  ... --lr 0 ...                                    # prior-only control (no training)
"""
import argparse
import math
import sys
from pathlib import Path

SFT = Path(__file__).resolve().parents[2] / "sft"
src = (SFT / "dt_vs_fft.py").read_text()


def rep(old, new):
    global src
    assert src.count(old) == 1, old
    src = src.replace(old, new)


rep("HERE = Path(__file__).resolve().parent", f"HERE = Path({str(SFT)!r})\nPROBE = []")
rep('''            state["logits"][k] = DT.init_logits(scores, logit_rng, eta=eta)
''', '''            state["logits"][k] = DT.init_logits(scores, logit_rng, eta=eta)
        probe = {"target_type": target_type, "eta": eta, "seed": seed,
                 "logits0": {k: list(v) for k, v in state["logits"].items()},
                 "keep0": {k: DT.hard_keep(v) for k, v in state["logits"].items()},
                 "bitgrad": [], "sat": []}
''')
rep('''        elif method == "dt":
            for k in base_weights:
                mat = base_weights[k]
                mask = DT.soft_mask(state["logits"][k], alpha)
''', '''        elif method == "dt":
            _m = [b for k in base_weights for b in DT.soft_mask(state["logits"][k], alpha)]
            _l = [g for k in base_weights for g in state["logits"][k]]
            probe["bitgrad"].append(sum(b * (1 - b) for b in _m) / len(_m))
            probe["sat"].append(sum(1 for g in _l if abs(alpha * g) < math.log(99)) / len(_l))
            for k in base_weights:
                mat = base_weights[k]
                mask = DT.soft_mask(state["logits"][k], alpha)
''')
rep('''    return {
        "target_type": target_type,
        "method": method,
        "eta": eta if method == "dt" else None,''', '''    if method == "dt":
        n = sum(len(v) for v in state["logits"].values())
        probe["flips"] = sum(a != b for k in state["logits"] for a, b in zip(probe["keep0"][k], DT.hard_keep(state["logits"][k])))
        probe["n"] = n
        probe["del_init"] = sum(not b for k in probe["keep0"] for b in probe["keep0"][k]) / n
        probe["del_end"] = deleted_frac
        probe["max_dG"] = max(abs(a - b) for k in state["logits"] for a, b in zip(probe["logits0"][k], state["logits"][k]))
        probe["slope"] = (probe["bitgrad"][0], probe["bitgrad"][-1])
        probe["sat"] = (probe["sat"][0], probe["sat"][-1])
        probe["loss"] = (task_loss_start, task_loss_end)
        PROBE.append(probe)
    return {
        "target_type": target_type,
        "method": method,
        "eta": eta if method == "dt" else None,''')

ap = argparse.ArgumentParser()
ap.add_argument("--sharpness", type=float, nargs=2, default=None, metavar=("START", "END"))
ap.add_argument("--seeds", type=int, nargs="+", default=[0])
ap.add_argument("--lr", type=float, default=0.2)
args = ap.parse_args()

ns = {"__name__": "dt_vs_fft_probe", "__file__": str(SFT / "dt_vs_fft.py"), "math": math}
exec(compile(src, "dt_vs_fft_probe", "exec"), ns)
if args.sharpness:
    orig = ns["DT"].sharpness
    ns["DT"].sharpness = lambda step, total, start=0, end=0: orig(step, total, *args.sharpness)
print("seed | cell | eta | flips/bits | deleted init->end | max|dG| | slope first/last | share |aG|<log99 first/last | task loss start->end")
for seed in args.seeds:
    ns["PROBE"].clear()
    ns["compare_sweep"](steps=30, seed=seed, lr=args.lr)
    for p in ns["PROBE"]:
        print(f"{seed} | {p['target_type']} | {p['eta']:.2f} | {p['flips']}/{p['n']} | {p['del_init']:.4f}->{p['del_end']:.4f} | "
              f"{p['max_dG']:.1e} | {p['slope'][0]:.1e}/{p['slope'][1]:.1e} | {p['sat'][0]:.2f}/{p['sat'][1]:.2f} | "
              f"{p['loss'][0]:.6f}->{p['loss'][1]:.6f}")
