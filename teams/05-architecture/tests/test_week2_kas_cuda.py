"""KAS CUDA parity and the trainer's bf16/float32-parameter execution path."""

import copy
import unittest

import numpy as np
import torch
from torch.nn import functional as F

import test_week2_kas_v2 as kas_fixture
from week2.kas_v2 import FIXTURE, KASCodec, KASHead, KASInput
from week2.optim import build_optimizer
from week2.config import load_runtime, validate


class KASValidationConfigTests(unittest.TestCase):
    def test_cuda_arm_keeps_dryrun_model_and_recipe_with_bounded_context_and_batch(self):
        arms = kas_fixture.TEAM / "configs/arms"
        reference = load_runtime(arms / "dryrun2.yaml")
        actual = load_runtime(arms / "kas_v2_cuda_validation.yaml")
        expected_model = copy.deepcopy(reference["model"])
        expected_model["block_size"] = 32
        self.assertEqual(actual["model"], expected_model)
        self.assertEqual(actual["optim"], reference["optim"])
        self.assertEqual(actual["run"]["batch_size"], 2)
        self.assertEqual(actual["run"]["micro_batch_size"], 1)
        self.assertEqual(actual["run"]["dtype"], "bf16")
        self.assertFalse(actual["intended"]["comparison_final"])
        self.assertEqual(validate(actual), [])


@unittest.skipUnless(torch.cuda.is_available(), "CUDA GPU required")
class KASCudaTests(unittest.TestCase):
    def setUp(self):
        previous = torch.are_deterministic_algorithms_enabled()
        tf32 = torch.backends.cuda.matmul.allow_tf32
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        self.addCleanup(torch.use_deterministic_algorithms, previous)
        self.addCleanup(setattr, torch.backends.cuda.matmul, "allow_tf32", tf32)
        rng = torch.random.fork_rng(devices=[0])
        rng.__enter__()
        self.addCleanup(rng.__exit__, None, None, None)
        torch.manual_seed(1234)

    def require_bf16(self):
        if torch.cuda.get_device_capability()[0] < 8:
            self.skipTest("Native bf16 hardware required by the trainer")

    def model(self):
        helper = kas_fixture.ModelIntegration()
        self.addCleanup(helper.doCleanups)
        cfg, rows, lengths, model = helper.model()
        return cfg, model.cuda()

    def test_public_fixture_cuda_float64_and_fp32(self):
        with np.load(FIXTURE, allow_pickle=False) as z:
            codec = KASCodec().cuda()
            rows = torch.from_numpy(z["bytes"].copy())
            lengths = torch.from_numpy(z["lengths"].copy()).long()
            head = KASHead(rows, lengths, 32, codec).double().cuda().eval()
            embedding = KASInput(rows, lengths, 32, codec).double().cuda()
            with torch.no_grad():
                for name in ("W_out", "beta", "unigram", "tok_u", "tok_c"):
                    getattr(head, name).copy_(torch.from_numpy(z[name]))
                embedding.projection.weight.copy_(torch.from_numpy(z["W_proj"]).t())
            h = torch.from_numpy(z["h"].copy()).cuda()
            expected = torch.from_numpy(z["logits"].copy()).cuda()
            torch.testing.assert_close(head(h), expected, rtol=0, atol=1e-10)
            output = embedding(torch.arange(len(rows), device="cuda"))
            torch.testing.assert_close(output.cpu(), torch.from_numpy(z["E"]), rtol=0, atol=1e-10)
            output.sum().backward()
            expected_gradient = torch.from_numpy(z["K"].sum(axis=0)).expand(32, -1)
            torch.testing.assert_close(embedding.projection.weight.grad.cpu(), expected_gradient,
                                       rtol=1e-10, atol=1e-10)
            head.float()
            relative = (head(h.float()).double() - expected).abs() / expected.abs().amax(1, keepdim=True)
            self.assertLess(relative.max().item(), 1e-5)

    def test_bf16_autocast_keeps_codec_and_head_precision(self):
        self.require_bf16()
        _, model = self.model()
        observed = []
        handle = model.blocks[0].attn.q.register_forward_hook(lambda _m, _i, out: observed.append(out.dtype))
        self.addCleanup(handle.remove)
        ids = torch.arange(16, device="cuda").reshape(2, 8)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(ids, torch.ones_like(ids, dtype=torch.bool))
            loss = F.cross_entropy(logits.reshape(-1, 31), ((ids + 1) % 31).reshape(-1))
        self.assertEqual(observed, [torch.bfloat16])
        self.assertEqual(logits.dtype, torch.float32)
        self.assertEqual(model.codec.G.dtype, torch.float64)
        self.assertEqual(model.codec.Phi.dtype, torch.float64)
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        for name, param in model.head.named_parameters():
            self.assertEqual(param.dtype, torch.float32, name)
            self.assertIsNotNone(param.grad, name)
            self.assertTrue(torch.isfinite(param.grad).all(), name)
        self.assertTrue(torch.isfinite(model.embedding.projection.weight.grad).all())

    def test_bf16_accumulated_optimizer_and_rng_resume(self):
        self.require_bf16()
        cfg, model = self.model()
        optimizer = build_optimizer(model, cfg["optim"])
        ids = torch.arange(32, device="cuda").reshape(4, 8) % 31

        def step(m, opt):
            m.train()
            opt.zero_grad(set_to_none=True)
            losses = []
            m.clear_router_bias_load()
            for micro in ids.split(2):
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    logits = m(micro, torch.ones_like(micro, dtype=torch.bool))
                    loss = F.cross_entropy(logits.reshape(-1, 31), ((micro + 1) % 31).reshape(-1)) / 2
                loss.backward()
                losses.append(loss.detach())
            m.update_router_bias()
            torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0, error_if_nonfinite=True)
            opt.step()
            return torch.stack(losses)

        step(model, optimizer)
        state = copy.deepcopy(model.state_dict())
        optim_state = copy.deepcopy(optimizer.state_dict())
        cpu_rng, cuda_rng = torch.get_rng_state(), torch.cuda.get_rng_state_all()
        expected_loss = step(model, optimizer)
        expected_model = copy.deepcopy(model.state_dict())
        expected_optim = copy.deepcopy(optimizer.state_dict())
        _, restored = self.model()
        restored.load_state_dict(state, strict=True)
        resumed_optim = build_optimizer(restored, cfg["optim"])
        resumed_optim.load_state_dict(optim_state)
        torch.set_rng_state(cpu_rng)
        torch.cuda.set_rng_state_all(cuda_rng)
        actual_loss = step(restored, resumed_optim)
        torch.testing.assert_close(actual_loss, expected_loss, rtol=0, atol=0)
        for name, value in restored.state_dict().items():
            torch.testing.assert_close(value, expected_model[name], rtol=0, atol=0, msg=name)

        def same(actual, expected):
            if isinstance(actual, torch.Tensor):
                torch.testing.assert_close(actual, expected, rtol=0, atol=0)
            elif isinstance(actual, dict):
                self.assertEqual(actual.keys(), expected.keys())
                for key in actual:
                    same(actual[key], expected[key])
            elif isinstance(actual, (tuple, list)):
                self.assertEqual(len(actual), len(expected))
                for a, b in zip(actual, expected):
                    same(a, b)
            else:
                self.assertEqual(actual, expected)
        same(resumed_optim.state_dict(), expected_optim)


if __name__ == "__main__":
    unittest.main()
