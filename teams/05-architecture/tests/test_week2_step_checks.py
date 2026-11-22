from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from train_week2 import checked_step_losses
import train_week2
from test_week2_model import fixture


class ConsolidatedChecksTests(unittest.TestCase):
    def test_metrics_are_summed_in_microbatch_order(self):
        rows = [torch.tensor([3.0, 2.0, 1.0]), torch.tensor([6.0, 4.0, 2.0])]
        self.assertEqual(checked_step_losses(rows, torch.tensor(1.0)), (9.0, 6.0, 3.0))

    def test_rejects_nonfinite_losses_or_preclip_norm(self):
        with self.assertRaisesRegex(ValueError, "objective or MTP"):
            checked_step_losses([torch.tensor([1.0, 1.0, float("nan")])], torch.tensor(1.0))
        with self.assertRaisesRegex(ValueError, "gradient norm"):
            checked_step_losses([torch.tensor([1.0, 1.0, 0.0])], torch.tensor(float("inf")))

    def test_default_matches_baseline_repeat_and_checkpoint_resume(self):
        cfg, byte_rows, _ = fixture()
        cfg["model"]["ke_max_pos"] = byte_rows.shape[1]
        artifacts = SimpleNamespace(
            bytes=byte_rows,
            lengths=np.ones(len(byte_rows), dtype=np.int16),
            pos_dim=byte_rows.shape[1],
            bos_id=0, pad_id=1, normalize_input=False,
            encode=lambda text: [ord(char) - ord("a") + 2 for char in text],
            identity=lambda: {},
        )
        with TemporaryDirectory() as temp:
            root = Path(temp)
            train, heldout = root / "train.jsonl", root / "heldout.jsonl"
            train.write_text('{"text":"aaaa"}\n', encoding="utf8")
            heldout.write_text('{"text":"bbbb"}\n', encoding="utf8")
            common = [
                "train_week2.py", "--config", "fixture.yaml",
                "--tokenizer", "fixture.json", "--byte-table", "fixture.npz",
                "--train-data", str(train), "--heldout-data", str(heldout),
                "--smoke", "--smoke-steps", "3", "--smoke-batch-size", "2",
                "--seed", "1234",
            ]

            def run(name, *extra):
                out = root / name
                with (
                    patch.object(sys, "argv", [*common, "--out", str(out), *extra]),
                    patch.object(train_week2, "load_runtime", return_value=deepcopy(cfg)),
                    patch.object(train_week2, "Artifacts", return_value=artifacts),
                ):
                    train_week2.main()
                return out

            baseline = run("baseline", "--no-consolidate-step-checks")
            default = run("default")
            repeat = run("repeat")
            segment = run("segment", "--stop-after", "1")
            resumed = run("resumed", "--resume", str(segment / "checkpoint.pt"))
            expected = (baseline / "losses.txt").read_bytes()
            summary = json.loads((baseline / "summary.json").read_text())
            for out in (default, repeat, resumed):
                with self.subTest(out=out.name):
                    self.assertEqual((out / "losses.txt").read_bytes(), expected)
                    actual = json.loads((out / "summary.json").read_text())
                    self.assertEqual(actual["final_model_sha256"], summary["final_model_sha256"])
                    manifest = json.loads((out / "manifest.json").read_text())
                    self.assertIs(manifest["consolidate_step_checks"], True)

    def test_nonfinite_gradient_blocks_the_optimizer_update(self):
        parameter = torch.nn.Parameter(torch.tensor([1.0]))
        optimizer = torch.optim.AdamW([parameter], lr=0.01)
        parameter.grad = torch.tensor([float("nan")])
        original = parameter.detach().clone()
        with patch.object(optimizer, "step", wraps=optimizer.step) as step:
            with self.assertRaisesRegex(ValueError, "gradient norm"):
                norm = torch.nn.utils.clip_grad_norm_(
                    [parameter], 1.0, error_if_nonfinite=False
                )
                checked_step_losses([torch.tensor([1.0, 1.0, 0.0])], norm)
                optimizer.step()
            step.assert_not_called()
        torch.testing.assert_close(parameter, original, rtol=0, atol=0)
