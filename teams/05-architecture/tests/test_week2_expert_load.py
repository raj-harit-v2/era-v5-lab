"""Check MoE telemetry against the trainer and G8 logger contracts."""

from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from test_week2_model import TEAM, fixture
import train_week2
from week2.model import LanguageModel


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf8").splitlines()]


class ExpertLoadTests(unittest.TestCase):
    def test_negative_sampling_interval_is_rejected_before_loading_inputs(self):
        args = [
            "train_week2.py", "--config", "fixture.yaml",
            "--tokenizer", "fixture.json", "--byte-table", "fixture.npz",
            "--train-data", "train.jsonl", "--heldout-data", "val.jsonl",
            "--out", "unused", "--smoke", "--expert-load-every", "-1",
        ]
        errors = io.StringIO()
        with (
            patch.object(sys, "argv", args),
            patch.object(train_week2, "load_runtime") as load_runtime,
            redirect_stderr(errors),
            self.assertRaises(SystemExit) as raised,
        ):
            train_week2.main()
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--expert-load-every must be nonnegative", errors.getvalue())
        load_runtime.assert_not_called()

    def test_counts_actual_top_k_picks_and_excludes_padding_and_eval(self):
        cfg, byte_rows, lengths = fixture()
        model = LanguageModel(cfg["model"], byte_rows, lengths)
        layer = model.blocks[0].moe
        with torch.no_grad():
            layer.router.weight.zero_()
            layer.router.weight[:, 0] = torch.arange(1, 5)
        inputs = torch.zeros(1, 3, cfg["model"]["n_embd"])
        inputs[0, :, 0] = torch.tensor([1.0, -1.0, 1.0])
        model.start_expert_load()
        layer(inputs, torch.tensor([[True, False, False]]))
        layer(inputs, torch.tensor([[False, True, True]]))
        layer.eval()
        layer(inputs, torch.ones((1, 3), dtype=torch.bool))
        first, second = model.finish_expert_load()
        self.assertEqual(first, [1, 1, 2, 2])
        self.assertEqual(second, [0, 0, 0, 0])
        self.assertTrue(all(block.moe.expert_load is None for block in model.blocks))
        layer.train()
        layer(inputs, torch.ones((1, 3), dtype=torch.bool))
        self.assertIsNone(layer.expert_load)
        model.start_expert_load()
        layer(inputs, torch.tensor([[True, False, False]]))
        self.assertEqual(model.finish_expert_load(), [[0, 0, 1, 1], [0, 0, 0, 0]])
        self.assertTrue(all(block.moe.expert_load is None for block in model.blocks))

    def test_sampled_training_rows_reach_g8_without_changing_model(self):
        cfg, byte_rows, _ = fixture()
        cfg["model"]["ke_max_pos"] = byte_rows.shape[1]
        cfg["run"].update(batch_size=2, micro_batch_size=1)
        artifacts = SimpleNamespace(
            bytes=byte_rows,
            lengths=np.ones(len(byte_rows), dtype=np.int16),
            pos_dim=byte_rows.shape[1],
            bos_id=0,
            pad_id=1,
            encode=lambda text: [ord(char) - ord("a") + 2 for char in text],
            identity=lambda: {},
            normalize_input=False,
        )
        logger_dir = TEAM.parent / "08-monitoring" / "metrics_logger"
        with TemporaryDirectory() as temp:
            root = Path(temp)
            train = root / "train.jsonl"
            val = root / "val.jsonl"
            train.write_text('{"text":"aaaa"}\n{"text":"aaa"}\n', encoding="utf8")
            val.write_text('{"text":"bbbb"}\n', encoding="utf8")
            common = [
                "train_week2.py", "--config", "fixture.yaml",
                "--tokenizer", "fixture.json", "--byte-table", "fixture.npz",
                "--train-data", str(train), "--heldout-data", str(val),
                "--smoke", "--smoke-steps", "4", "--no-checkpoint",
                "--logger-factory", "g5_adapter:make_writer",
            ]

            def run(name, *args):
                out = root / name
                run_args = [*common, "--out", str(out), *args]
                if "--checkpoint-store" in args:
                    run_args.remove("--no-checkpoint")
                with patch.object(sys, "argv", run_args):
                    train_week2.main()
                return out

            with (
                patch.object(train_week2, "load_runtime", return_value=cfg),
                patch.object(train_week2, "Artifacts", return_value=artifacts),
                patch.object(sys, "path", [str(logger_dir), str(TEAM.parent / "07-infrastructure"), *sys.path]),
            ):
                with patch.object(
                    LanguageModel, "start_expert_load",
                    side_effect=AssertionError("Default must not collect telemetry"),
                ):
                    plain = run("plain")
                sampled = run("sampled", "--expert-load-every", "2")
                sampled_baseline = run(
                    "sampled-baseline", "--expert-load-every", "2", "--no-consolidate-step-checks"
                )
                committed = [
                    "--checkpoint-store", str(root / "store"), "--run-id", "g5-telemetry-resume",
                    "--expert-load-every", "2", "--checkpoint-at-start",
                ]
                run("segment", *committed, "--stop-after", "2")
                resumed = run("resumed", *committed, "--resume-committed")

            plain_rows = read_rows(plain / "metrics.jsonl")
            sampled_rows = read_rows(sampled / "metrics.jsonl")
            baseline_rows = read_rows(sampled_baseline / "metrics.jsonl")
            g8_rows = read_rows(sampled / "g8" / "metrics.jsonl")
            for path in (resumed / "metrics.jsonl", resumed / "g8" / "metrics.jsonl"):
                replayed = read_rows(path)
                self.assertEqual(
                    [(row["step"], row.get("expert_load")) for row in replayed],
                    [(row["step"], row.get("expert_load")) for row in sampled_rows],
                )
            self.assertTrue(all("expert_load" not in row for row in plain_rows))
            self.assertEqual(json.loads((plain / "manifest.json").read_text())["expert_load_every"], 0)
            for rows in (sampled_rows, g8_rows):
                self.assertEqual([row["step"] for row in rows], [0, 1, 2, 3, 4])
                self.assertEqual([row["step"] for row in rows if "expert_load" in row], [2, 4])
            self.assertEqual(
                [(row["step"], row.get("expert_load")) for row in baseline_rows],
                [(row["step"], row.get("expert_load")) for row in sampled_rows],
            )
            g8_by_step = {row["step"]: row for row in g8_rows}
            for row in sampled_rows:
                if "expert_load" not in row:
                    continue
                loads = row["expert_load"]
                self.assertEqual(len(loads), cfg["model"]["n_layer"])
                self.assertLess(row["train/scored_tokens"], row["train/input_positions"])
                for layer in loads:
                    self.assertEqual(len(layer), cfg["model"]["moe"]["num_experts"])
                    self.assertTrue(all(type(count) is int and count >= 0 for count in layer))
                    self.assertEqual(sum(layer), row["train/scored_tokens"] * cfg["model"]["moe"]["top_k"])
                self.assertEqual(g8_by_step[row["step"]]["expert_load"], loads)
                self.assertIn("expert_load_imbalance", g8_by_step[row["step"]])
            self.assertEqual((sampled / "losses.txt").read_bytes(), (plain / "losses.txt").read_bytes())
            self.assertEqual((sampled_baseline / "losses.txt").read_bytes(), (plain / "losses.txt").read_bytes())
            self.assertEqual((resumed / "losses.txt").read_bytes(), (plain / "losses.txt").read_bytes())
            summaries = [
                json.loads((out / "summary.json").read_text(encoding="utf8"))
                for out in (plain, sampled, sampled_baseline, resumed)
            ]
            self.assertEqual(summaries[0]["final_model_sha256"], summaries[1]["final_model_sha256"])
            self.assertEqual(summaries[0]["final_model_sha256"], summaries[2]["final_model_sha256"])
            self.assertEqual(summaries[0]["final_model_sha256"], summaries[3]["final_model_sha256"])


if __name__ == "__main__":
    unittest.main()
