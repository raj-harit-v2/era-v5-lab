"""SDPA global attention: same math as eager GQA, local layers untouched, eager path unchanged."""

import copy
import math
from pathlib import Path
import sys
import unittest
import torch
from torch.nn import functional as F

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
sys.path.insert(0, str(TEAM / "tests"))
from test_week2_model import fixture
from week2.config import load, load_runtime, merge, validate
from week2.model import GQA, LanguageModel


def legacy_eager(attn, x):
    """The eager GQA forward before the SDPA switch, kept to prove the eager path is unchanged."""
    b, t, w = x.shape
    q = attn.rotary(attn.q(x).view(b, t, attn.nh, attn.d).transpose(1, 2))
    k = attn.rotary(attn.k(x).view(b, t, attn.nkv, attn.d).transpose(1, 2)).repeat_interleave(
        attn.nh // attn.nkv, dim=1
    )
    v = attn.v(x).view(b, t, attn.nkv, attn.d).transpose(1, 2).repeat_interleave(attn.nh // attn.nkv, dim=1)
    logits = q.float() @ k.float().transpose(-2, -1) / math.sqrt(attn.d)
    mask = torch.ones(t, t, dtype=torch.bool, device=x.device).tril()
    if attn.local:
        positions = torch.arange(t, device=x.device)
        mask = mask & ((positions[:, None] - positions[None, :]) < attn.window)
    logits = logits.masked_fill(~mask, float("-inf"))
    if attn.sink is not None and not bool(torch.isneginf(attn.sink).all()):
        sink = attn.sink.float().view(1, attn.nh, 1, 1).expand(b, -1, t, -1)
        a = torch.cat((logits, sink), dim=-1).softmax(-1)[..., :t].to(v.dtype)
    else:
        a = logits.softmax(-1).to(v.dtype)
    return attn.o((a @ v).transpose(1, 2).reshape(b, t, w))


def model_spec(impl, n_kv_head=2, **extra):
    c, rows, lengths = fixture()
    c["model"].update(attn_impl=impl, n_kv_head=n_kv_head, **extra)
    return c, rows, lengths


def loss_and_grads(model, ids, valid):
    model.zero_grad(set_to_none=True)
    logits = model(ids, valid)
    loss = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), (ids + 1).reshape(-1) % 31)
    loss.backward()
    return logits.detach(), {n: p.grad.clone() for n, p in model.named_parameters() if p.grad is not None}


class SdpaConfigTests(unittest.TestCase):
    def test_dryrun2_sdpa_arm_is_valid_and_only_changes_attention(self):
        small = load(TEAM / "configs/small/smoke_resolution.yaml")
        sdpa = merge(load_runtime(TEAM / "configs/arms/dryrun2_sdpa.yaml"), small)
        eager = merge(load_runtime(TEAM / "configs/arms/dryrun2.yaml"), small)
        self.assertEqual(validate(sdpa), [])
        self.assertEqual(sdpa["model"]["attn_impl"], "sdpa")
        self.assertEqual(eager["model"]["attn_impl"], "eager")
        self.assertEqual({**sdpa["model"], "attn_impl": "eager"}, eager["model"])
        self.assertEqual((sdpa["optim"], sdpa["run"]), (eager["optim"], eager["run"]))

    def test_unknown_attention_impl_is_refused(self):
        c, _, _ = model_spec("flash")
        self.assertIn("attn_impl must be eager or sdpa", validate(c))


class SdpaParityTests(unittest.TestCase):
    def test_eager_path_matches_the_legacy_forward_bitwise(self):
        for kind in ["global", "local"]:
            extra = dict(attn_pattern=["L", "G"], attn_window=3, attn_sink=True) if kind == "local" else {}
            c, _, _ = model_spec("eager", **extra)
            torch.manual_seed(1234)
            attn = GQA(c["model"], 0)
            if attn.sink is not None:
                torch.nn.init.normal_(attn.sink)
            x = torch.randn(2, 8, 16)
            with self.subTest(kind=kind):
                self.assertTrue(torch.equal(attn(x), legacy_eager(attn, x)))

    def test_sdpa_matches_eager_forward_and_gradients(self):
        for n_kv in [1, 2, 4]:
            torch.manual_seed(1234)
            c, rows, lengths = model_spec("eager", n_kv_head=n_kv)
            eager = LanguageModel(c["model"], rows, lengths)
            c_sdpa = copy.deepcopy(c)
            c_sdpa["model"]["attn_impl"] = "sdpa"
            sdpa = LanguageModel(c_sdpa["model"], rows, lengths)
            sdpa.load_state_dict(eager.state_dict())
            ids = torch.arange(16).reshape(2, 8) % 31
            valid = torch.ones_like(ids, dtype=torch.bool)
            ref_logits, ref_grads = loss_and_grads(eager, ids, valid)
            logits, grads = loss_and_grads(sdpa, ids, valid)
            with self.subTest(n_kv_head=n_kv):
                torch.testing.assert_close(logits, ref_logits, rtol=1e-5, atol=1e-5)
                self.assertEqual(grads.keys(), ref_grads.keys())
                for name in ref_grads:
                    torch.testing.assert_close(grads[name], ref_grads[name], rtol=1e-4, atol=1e-5, msg=name)

    def test_local_layers_stay_eager(self):
        c, _, _ = model_spec("sdpa", attn_pattern=["L", "G"], attn_window=3, attn_sink=True)
        self.assertEqual(validate(c), [])
        local, global_ = GQA(c["model"], 0), GQA(c["model"], 1)
        self.assertFalse(local.sdpa)
        self.assertTrue(global_.sdpa)
        self.assertIsNotNone(local.sink)

    def test_sdpa_adds_no_parameters_or_state(self):
        c, rows, lengths = model_spec("eager")
        eager = LanguageModel(c["model"], rows, lengths)
        c["model"]["attn_impl"] = "sdpa"
        sdpa = LanguageModel(c["model"], rows, lengths)
        self.assertEqual(
            {k: v.shape for k, v in eager.state_dict().items()},
            {k: v.shape for k, v in sdpa.state_dict().items()},
        )


@unittest.skipUnless(torch.cuda.is_available(), "CUDA only")
class SdpaCudaTests(unittest.TestCase):
    def setUp(self):
        torch.use_deterministic_algorithms(True)

    def tearDown(self):
        torch.use_deterministic_algorithms(False)

    def attention_pair(self):
        torch.manual_seed(1234)
        c, _, _ = model_spec("eager")
        c["model"].update(n_embd=256, n_head=4, n_kv_head=2, block_size=256)
        eager = GQA(c["model"], 0).cuda()
        c["model"]["attn_impl"] = "sdpa"
        sdpa = GQA(c["model"], 0).cuda()
        sdpa.load_state_dict(eager.state_dict())
        x = torch.randn(2, 256, 256, device="cuda")
        return eager, sdpa, x

    def run_bf16(self, attn, x):
        attn.zero_grad(set_to_none=True)
        x = x.clone().requires_grad_()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            out = attn(x)
        out.float().square().mean().backward()
        return out.float(), x.grad, [p.grad.clone() for p in attn.parameters()]

    def test_bf16_sdpa_close_to_eager(self):
        eager, sdpa, x = self.attention_pair()
        ref, ref_dx, _ = self.run_bf16(eager, x)
        out, dx, _ = self.run_bf16(sdpa, x)
        torch.testing.assert_close(out, ref, rtol=2e-2, atol=2e-2)
        torch.testing.assert_close(dx, ref_dx, rtol=5e-2, atol=5e-3)

    def test_bf16_sdpa_backward_repeats_bitwise(self):
        _, sdpa, x = self.attention_pair()
        first = self.run_bf16(sdpa, x)
        second = self.run_bf16(sdpa, x)
        self.assertTrue(torch.equal(first[0], second[0]))
        self.assertTrue(torch.equal(first[1], second[1]))
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(first[2], second[2])))

    def cuda_kernels(self, attn, x):
        """Names of the CUDA kernels one bf16 forward + backward launches."""
        from torch.profiler import ProfilerActivity, profile

        self.run_bf16(attn, x)   # warm-up outside the capture
        torch.cuda.synchronize()
        with profile(activities=[ProfilerActivity.CUDA]) as prof:
            self.run_bf16(attn, x)
            torch.cuda.synchronize()
        return sorted({e.key for e in prof.key_averages()})

    def test_flash_backend_runs_under_the_trainer_settings(self):
        """Flash alone can serve the trainer's call: GQA, causal, bf16, deterministic mode, head dim 64."""
        from torch.nn.attention import SDPBackend, sdpa_kernel

        _, sdpa, x = self.attention_pair()
        with sdpa_kernel([SDPBackend.FLASH_ATTENTION]):
            out, dx, grads = self.run_bf16(sdpa, x)
        self.assertTrue(torch.isfinite(out).all() and torch.isfinite(dx).all())
        self.assertTrue(all(torch.isfinite(g).all() for g in grads))

    def test_default_backend_is_flash(self):
        """With no backend forced (as in the trainer), the fused kernels are Flash, not the math fallback."""
        _, sdpa, x = self.attention_pair()
        kernels = self.cuda_kernels(sdpa, x)
        attention = [k for k in kernels if "flash" in k.lower() or "fmha" in k.lower() or "efficient" in k.lower()]
        self.assertTrue(any("flash" in k.lower() for k in attention), "attention kernels: " + "; ".join(kernels))


if __name__ == "__main__":
    unittest.main()
