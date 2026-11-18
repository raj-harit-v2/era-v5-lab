"""Matched CPU benchmark: dr_grpo policy_loss vs objective_v1 (batched) vs the lead's scalar reference, k=8, T=1024.
Same tensors for every arm; forward+backward for the torch arms (backward into a leaf new_lp), forward for the
reference (it has no autograd). 20 timed repeats after 3 warmups; median and min reported."""
import importlib.util, json, platform, statistics, sys, time
from pathlib import Path
import torch
RL = Path(sys.argv[1]); sys.path.insert(0, str(RL / "rl-loop"))
import grpo
spec = importlib.util.spec_from_file_location("lead_obj", RL / "rl" / "objective_v1.py")
ref = importlib.util.module_from_spec(spec); sys.modules["lead_obj"] = ref; spec.loader.exec_module(ref)
torch.set_num_threads(int(sys.argv[2]) if len(sys.argv) > 2 else 2)
k, T, R = 8, 1024, 20
g = torch.Generator().manual_seed(0)
new = -torch.rand(k, T, generator=g) * 3 - 0.01
old = new + 0.15 * torch.randn(k, T, generator=g)
lengths = torch.tensor([1024, 900, 700, 512, 1024, 300, 64, 1000])
cm = torch.arange(T)[None] < lengths[:, None]
rewards = torch.tensor([1., 0., 0., 1., 0., 1., 0., 0.])
adv_dr = grpo.advantages(rewards, "dr_grpo"); adv_v1 = grpo.advantages(rewards, "objective_v1")
def run_dr():
    x = new.clone().requires_grad_(True); l, _ = grpo.policy_loss(x, old, adv_dr, cm, "dr_grpo"); l.backward(); return float(l.detach())
def run_v1():
    x = new.clone().requires_grad_(True); l, st = grpo.objective_v1_loss(x, old, adv_v1, cm); l.backward(); return float(l.detach())
rolls = None
def run_ref():
    rs = [ref.Rollout(float(rewards[i]), tuple(new[i][cm[i]].double().tolist()),
                      tuple(torch.exp(new[i][cm[i]].double() - old[i][cm[i]].double()).tolist())) for i in range(k)]
    return ref.objective_v1([rs]).loss
def bench(fn):
    for _ in range(3): fn()
    ts = []
    for _ in range(R):
        t0 = time.perf_counter(); v = fn(); ts.append(time.perf_counter() - t0)
    return {"median_ms": round(1e3 * statistics.median(ts), 4), "min_ms": round(1e3 * min(ts), 4), "value": v}
res = {"config": {"k": k, "T": T, "real_tokens": int(cm.sum()), "repeats": R, "warmup": 3, "dtype": "float32 (ratio in float64)",
                  "threads": torch.get_num_threads(), "torch": torch.__version__, "machine": platform.machine(),
                  "platform": platform.platform()},
       "dr_grpo_policy_loss_fwd_bwd": bench(run_dr), "objective_v1_batched_fwd_bwd": bench(run_v1),
       "lead_reference_scalar_fwd_only": bench(run_ref)}
res["objective_v1_matches_reference"] = abs(res["objective_v1_batched_fwd_bwd"]["value"] - res["lead_reference_scalar_fwd_only"]["value"]) <= 1e-6 * max(1, abs(res["lead_reference_scalar_fwd_only"]["value"]))
x = new.clone(); _, st = grpo.objective_v1_loss(x, old, adv_v1, cm)
res["objective_v1_masked_frac"] = round(1 - int(st["inside"]) / int(st["tokens"]), 4)
print(json.dumps(res, indent=1))
