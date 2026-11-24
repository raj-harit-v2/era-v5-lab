"""G5 implementation parity with the public Team 4 #765 fixture."""

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
from week2.kas_v2 import KASCodec, KASInput, KASHead, FIXTURE
from week2.model import LanguageModel
from week2.optim import build_optimizer
from week2.config import load_runtime, validate, merge, load
from test_week2_model import fixture


class FixtureParity(unittest.TestCase):
    def setUp(self):
        self.z = np.load(FIXTURE, allow_pickle=False)
        self.addCleanup(self.z.close)
        self.codec = KASCodec()
        self.rows = torch.from_numpy(self.z["bytes"].copy())
        self.lengths = torch.from_numpy(self.z["lengths"].copy()).long()

    def head(self):
        head = KASHead(self.rows, self.lengths, 32, self.codec).double().eval()
        with torch.no_grad():
            for name in ("W_out", "beta", "unigram", "tok_u", "tok_c"):
                getattr(head, name).copy_(torch.from_numpy(self.z[name]))
        return head

    def test_positions_codes_and_embedding(self):
        positions = self.codec.positions(self.rows, self.lengths)
        codes = self.codec.codes(self.rows, self.lengths)
        torch.testing.assert_close(positions, torch.from_numpy(self.z["M_pos"]), rtol=0, atol=1e-10)
        torch.testing.assert_close(codes, torch.from_numpy(self.z["K"]), rtol=0, atol=1e-10)
        embedding = KASInput(self.rows, self.lengths, 32, self.codec).double()
        with torch.no_grad():
            embedding.projection.weight.copy_(torch.from_numpy(self.z["W_proj"]).t())
        output = embedding(torch.arange(len(self.rows)))
        torch.testing.assert_close(output, torch.from_numpy(self.z["E"]), rtol=0, atol=1e-10)
        weights = torch.linspace(-1, 1, output.numel(), dtype=torch.float64).reshape_as(output)
        (output * weights).sum().backward()
        expected_gradient = weights.t() @ torch.from_numpy(self.z["K"])
        torch.testing.assert_close(embedding.projection.weight.grad, expected_gradient, rtol=1e-10, atol=1e-10)

    def test_head_float64_float32_and_fixed_dropout(self):
        head = self.head()
        h = torch.from_numpy(self.z["h"])
        expected = torch.from_numpy(self.z["logits"])
        torch.testing.assert_close(head(h), expected, rtol=0, atol=1e-10)
        keep = torch.from_numpy(self.z["keep"]).reshape(-1, 1)
        head.train()
        with patch("week2.kas_v2.correction_row_dropout", side_effect=lambda u, **kw: u * keep / 0.95):
            torch.testing.assert_close(head(h), torch.from_numpy(self.z["logits_dropped"]), rtol=0, atol=1e-10)
        head.float().eval()
        error = (head(h.float()).double() - expected).abs() / expected.abs().amax(1, keepdim=True)
        self.assertLess(error.max().item(), 1e-5)

    def test_fused_head_gradients_match_independent_dense_equation(self):
        head = self.head()
        h = torch.from_numpy(self.z["h"].copy()).requires_grad_()
        reference_h = h.detach().clone().requires_grad_()
        params = {name: getattr(head, name).detach().clone().requires_grad_()
                  for name in ("W_out", "beta", "unigram", "tok_u", "tok_c")}
        position = (reference_h @ params["W_out"]).reshape(-1, 64, 32)
        scores = torch.einsum("vcp,ncp->nv", torch.from_numpy(self.z["M_pos"]), position)
        reference = scores * params["beta"][self.lengths] + params["unigram"]
        reference = reference + (reference_h @ params["tok_c"].t()) @ params["tok_u"].t()
        weights = torch.linspace(-1, 1, reference.numel(), dtype=torch.float64).reshape_as(reference)
        (head(h) * weights).sum().backward()
        (reference * weights).sum().backward()
        torch.testing.assert_close(h.grad, reference_h.grad, rtol=1e-10, atol=1e-10)
        for name, parameter in params.items():
            torch.testing.assert_close(getattr(head, name).grad, parameter.grad, rtol=1e-10, atol=1e-10)

    def test_full_p1536_fingerprints(self):
        table = np.load(TEAM.parent / "04-ke2/results/tables/p1536-s0/raw_table_P32.npz")
        meta = json.loads(FIXTURE.with_suffix(".json").read_text())
        fp32, bf16 = hashlib.sha256(), hashlib.sha256()
        for start in range(0, len(table["lengths"]), 4096):
            rows = torch.from_numpy(table["bytes"][start:start + 4096].copy())
            lengths = torch.from_numpy(table["lengths"][start:start + 4096].copy()).long()
            codes = self.codec.codes(rows, lengths).float()
            fp32.update(codes.numpy().tobytes())
            bf16.update(codes.bfloat16().view(torch.uint16).numpy().tobytes())
        self.assertEqual(fp32.hexdigest(), meta["p1536_codes_fp32_sha256"])
        self.assertEqual(bf16.hexdigest(), meta["p1536_codes_bf16_sha256"])


class ModelIntegration(unittest.TestCase):
    def model(self):
        cfg, rows, lengths = fixture()
        rows = np.pad(rows, ((0, 0), (0, 28)))
        count = len(rows)
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "counts.json"
        spec = {"tokenizer_sha256": "a" * 64, "vocab_size": count,
                "total": [1] * count, "special_ids": [0, 1], "eos_id": 0,
                "summary": {"tokens": count, "ids_seen": count, "ids_zero": 0,
                            "special_ids_seen": 2, "docs": 1},
                "sources": {"fixture": {"sha256": "b" * 64, "bytes": count, "tokens": count, "docs": 1}}}
        path.write_text(json.dumps(spec))
        cfg["model"].update(head_mode="kas_v2", ke_max_pos=32, kas_prior={
            "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "tokenizer_sha256": "a" * 64, "add_eos_per_document": False})
        cfg["optim"].update(name="muon", muon_lr=0.006)
        return cfg, rows, lengths, LanguageModel(cfg["model"], rows, lengths)

    def test_actual_head_parameters_grouping_forward_and_strict_reload(self):
        cfg, rows, lengths, model = self.model()
        optimizer = build_optimizer(model, cfg["optim"])
        owners = {id(p): name for name, opt in optimizer.named for group in opt.param_groups for p in group["params"]}
        self.assertEqual({n for n, _ in model.head.named_parameters()}, {"W_out", "beta", "unigram", "tok_u", "tok_c"})
        for name, p in model.head.named_parameters():
            self.assertEqual(owners[id(p)], "adamw", name)
        self.assertNotEqual(model.head.W_out.data_ptr(), model.embedding.projection.weight.data_ptr())
        ids = torch.arange(8).reshape(1, 8)
        model.eval()
        logits = model(ids, torch.ones_like(ids, dtype=torch.bool))
        self.assertEqual(logits.shape, (1, 8, 31))
        restored = LanguageModel(cfg["model"], rows, lengths).eval()
        restored.load_state_dict(model.state_dict(), strict=True)
        torch.testing.assert_close(restored(ids, torch.ones_like(ids, dtype=torch.bool)), logits, rtol=0, atol=0)

    def test_team7_step_zero_and_committed_resume_with_real_kas_head(self):
        import test_week2_team7_checkpoints as checkpoint_tests
        for at_start in (False, True):
            cfg, rows, lengths, _ = self.model()
            with patch.object(checkpoint_tests, "fixture", side_effect=lambda mtp=False: (copy.deepcopy(cfg), rows, lengths)):
                checkpoint_tests.Team7CheckpointTests.check_resume(self, "muon", False, at_start=at_start)

    def test_team9_native_loader_and_seeded_probe_contract(self):
        import importlib.util
        from week2.kas_v2 import checkpoint_probe
        from train_week2 import model_hash

        cfg, rows, lengths, model = self.model()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "checkpoint.pt"
            torch.save({"model": model.state_dict()}, path)
            script = TEAM.parent / "09-evaluation/harness_lab/run_lab_ckpt.py"
            spec = importlib.util.spec_from_file_location("kas_team9_loader", script)
            loader = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(loader)
            restored = LanguageModel(cfg["model"], rows, lengths)
            loader.load_team5_weights(path, restored, model_hash(model))
            restored.train()
            rng = torch.get_rng_state().clone()
            result = checkpoint_probe(restored)
            self.assertTrue(restored.training)
            self.assertTrue(torch.equal(rng, torch.get_rng_state()))
            ids = torch.randint(0, 31, (2, 32), generator=torch.Generator().manual_seed(1234))
            restored.eval()
            with torch.no_grad():
                logits = restored(ids, torch.ones_like(ids, dtype=torch.bool))
                expected = torch.nn.functional.cross_entropy(logits[:, :-1].reshape(-1, 31), ids[:, 1:].reshape(-1))
            self.assertEqual(result.hex(), float(expected).hex())

    def test_config_dryrun_arm_selects_kas(self):
        cfg = merge(load_runtime(TEAM / "configs/arms/dryrun2.yaml"), load(TEAM / "configs/small/smoke_resolution.yaml"))
        self.assertEqual(cfg["model"]["head_mode"], "kas_v2")
        self.assertEqual(validate(cfg), [])


if __name__ == "__main__":
    unittest.main()
