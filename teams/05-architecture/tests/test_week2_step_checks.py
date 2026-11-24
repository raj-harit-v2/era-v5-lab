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
    def run_injected_failure(self, *, after_update, device="cpu"):
        cfg, byte_rows, _ = fixture()
        cfg["model"]["ke_max_pos"] = byte_rows.shape[1]
        artifacts = SimpleNamespace(
            bytes=byte_rows, lengths=np.ones(len(byte_rows), dtype=np.int16),
            pos_dim=byte_rows.shape[1], bos_id=0, pad_id=1, normalize_input=False,
            encode=lambda text: [ord(char) - ord("a") + 2 for char in text], identity=lambda: {},
        )
        original_build = train_week2.build_optimizer
        steps = []

        def build(model, settings):
            optimizer = original_build(model, settings)
            original_step = optimizer.step
            if not after_update:
                model.embedding.projection.weight.register_hook(lambda gradient: gradient * float("nan"))

            def step():
                steps.append(True)
                original_step()
                if after_update:
                    with torch.no_grad():
                        model.embedding.projection.weight.fill_(float("inf"))
            optimizer.step = step
            return optimizer

        with TemporaryDirectory() as temp:
            root = Path(temp)
            train, heldout = root / "train.jsonl", root / "heldout.jsonl"
            train.write_text('{"text":"aaaa"}\n', encoding="utf8")
            heldout.write_text('{"text":"bbbb"}\n', encoding="utf8")
            with (
                patch.object(sys, "argv", ["train_week2.py", "--config", "fixture.yaml",
                    "--tokenizer", "fixture.json", "--byte-table", "fixture.npz",
                    "--train-data", str(train), "--heldout-data", str(heldout),
                    "--smoke", "--smoke-steps", "1", "--device", device, "--no-checkpoint", "--out", str(root / "out")]),
                patch.object(train_week2, "load_runtime", return_value=deepcopy(cfg)),
                patch.object(train_week2, "Artifacts", return_value=artifacts),
                patch.object(train_week2, "build_optimizer", side_effect=build),
            ):
                with self.assertRaises(train_week2.NonfiniteTrainingError) as error:
                    train_week2.main()
        return str(error.exception), len(steps)

    def test_trainer_names_post_update_parameter_failure(self):
        message, steps = self.run_injected_failure(after_update=True)
        self.assertIn("Nonfinite parameter after optimizer step; tensors: embedding.projection.weight", message)
        self.assertEqual(steps, 1)

    def test_trainer_names_observed_bad_gradients_and_does_not_update(self):
        message, steps = self.run_injected_failure(after_update=False)
        self.assertIn("Nonfinite gradient norm", message)
        self.assertIn("after clipping", message)
        self.assertIn("embedding.projection.weight", message)
        self.assertEqual(steps, 0)

    @unittest.skipUnless(torch.cuda.is_available(), "CUDA required")
    def test_cuda_trainer_failure_diagnostics(self):
        for after_update in (False, True):
            with self.subTest(after_update=after_update):
                message, steps = self.run_injected_failure(after_update=after_update, device="cuda")
                self.assertIn("embedding.projection.weight", message)
                self.assertEqual(steps, int(after_update))
                self.assertIn("after optimizer step" if after_update else "after clipping", message)

    def test_norm_overflow_does_not_invent_a_nonfinite_tensor(self):
        model = torch.nn.Linear(2, 1)
        model.weight.grad = torch.full_like(model.weight, 1e30)
        model.bias.grad = None
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=False)
        with self.assertRaisesRegex(train_week2.NonfiniteTrainingError, "no nonfinite tensors found"):
            checked_step_losses([torch.tensor([1., 1., 0.])], norm, model)

    def test_finite_step_does_not_inspect_tensors(self):
        with patch.object(train_week2, "nonfinite_tensor_detail", side_effect=AssertionError("unexpected scan")):
            self.assertEqual(checked_step_losses([torch.tensor([1., 1., 0.])], torch.tensor(1.), object()), (1., 1., 0.))

    def test_failure_inspection_is_bounded_and_distinguishes_gradients(self):
        model = torch.nn.ParameterDict({f"weight_{i}": torch.nn.Parameter(torch.ones(1)) for i in range(10)})
        for parameter in model.parameters():
            parameter.grad = torch.full_like(parameter, float("nan"))
        detail = train_week2.nonfinite_tensor_detail(model, gradients=True)
        self.assertIn("weight_0", detail)
        self.assertIn("weight_2", detail)
        self.assertNotIn("weight_3", detail)
        self.assertTrue(detail.endswith("... further tensors not listed"))
        self.assertIn("no nonfinite tensors", train_week2.nonfinite_tensor_detail(model))

    def test_nonfinite_norm_reports_postclip_state_without_claiming_original_source(self):
        model = torch.nn.Linear(2, 1)
        model.weight.grad = torch.tensor([[float("inf"), 1.]])
        model.bias.grad = None
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=False)
        with self.assertRaisesRegex(train_week2.NonfiniteTrainingError, "after clipping.*propagated.*weight"):
            checked_step_losses([torch.tensor([1., 1., 0.])], norm, model)

    def test_complete_errors_bound_long_names_and_preserve_context(self):
        parameter = torch.nn.Parameter(torch.tensor([float("nan")]))
        parameter.grad = torch.tensor([float("inf")])
        names = [("blocks." + "very_long_component." * 80 + str(i) + ".weight", parameter) for i in range(10)]
        model = SimpleNamespace(named_parameters=lambda: iter(names))
        for gradients, prefix in ((True, "Nonfinite gradient norm"), (False, "Nonfinite parameter after optimizer step")):
            message = train_week2.nonfinite_error_message(prefix, model, gradients=gradients)
            self.assertLessEqual(len(message), 400)
            self.assertTrue(message.startswith(prefix))
            self.assertIn("... further tensors not listed", message)
            self.assertIn("0.weight", message)
            self.assertIn("2.weight", message)
            self.assertNotIn("3.weight", message)
            if gradients:
                self.assertIn("after clipping; nonfinites may have propagated", message)

    def test_complete_message_has_explicit_character_truncation(self):
        model = SimpleNamespace(named_parameters=lambda: iter(()))
        message = train_week2.nonfinite_error_message("x" * 500, model)
        self.assertEqual(len(message), 400)
        self.assertTrue(message.endswith("... [truncated]"))

    def test_long_inspection_exception_type_is_bounded(self):
        error = type("Diagnostic" + "x" * 500, (RuntimeError,), {})
        model = SimpleNamespace(named_parameters=lambda: (_ for _ in ()).throw(error()))
        message = train_week2.nonfinite_error_message("Nonfinite gradient norm", model, gradients=True)
        self.assertLessEqual(len(message), 400)
        self.assertIn("inspection unavailable", message)
        self.assertNotIn("x" * 65, message)

    def test_parameter_inspection_names_only_affected_parameters(self):
        model = torch.nn.Linear(2, 1)
        with torch.no_grad():
            model.bias.fill_(float("nan"))
        self.assertEqual(train_week2.nonfinite_tensor_detail(model), "; tensors: bias")

    def test_diagnostic_failure_does_not_hide_nonfinite_error(self):
        model = SimpleNamespace(named_parameters=lambda: (_ for _ in ()).throw(RuntimeError("unavailable")))
        with self.assertRaisesRegex(train_week2.NonfiniteTrainingError, "Nonfinite gradient norm.*inspection unavailable"):
            checked_step_losses([torch.tensor([1., 1., 0.])], torch.tensor(float("nan")), model)

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
