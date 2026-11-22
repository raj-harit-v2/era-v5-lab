"""Exercise logger setup, checkpoint resume, and replay through the G5 CLI."""

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


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf8").splitlines()]


class G8LoggerTests(unittest.TestCase):
    def test_resume_keeps_run_id_and_replays_once(self):
        cfg, byte_rows, _ = fixture()
        cfg["model"]["ke_max_pos"] = byte_rows.shape[1]
        artifacts = SimpleNamespace(
            bytes=byte_rows,
            lengths=np.ones(len(byte_rows), dtype=np.int16),
            pos_dim=byte_rows.shape[1],
            bos_id=0,
            pad_id=1,
            normalize_input=False,
            encode=lambda text: [ord(char) - ord("a") + 2 for char in text],
            identity=lambda: {},
        )
        logger_dir = TEAM.parent / "08-monitoring" / "metrics_logger"
        with TemporaryDirectory() as temp:
            root = Path(temp)
            train = root / "train.jsonl"
            val = root / "val.jsonl"
            train.write_text('{"text":"aaaa"}\n', encoding="utf8")
            val.write_text('{"text":"bbbb"}\n', encoding="utf8")
            common = [
                "train_week2.py", "--config", "fixture.yaml",
                "--tokenizer", "fixture.json", "--byte-table", "fixture.npz",
                "--train-data", str(train), "--heldout-data", str(val),
                "--smoke", "--smoke-steps", "2", "--smoke-batch-size", "1",
                "--logger-factory", "g5_adapter:make_writer",
            ]

            def run(name, *args):
                out = root / name
                with patch.object(sys, "argv", [*common, "--out", str(out), *args]):
                    train_week2.main()
                return out

            with (
                patch.object(train_week2, "load_runtime", return_value=cfg),
                patch.object(train_week2, "Artifacts", return_value=artifacts),
                patch.object(sys, "path", [str(logger_dir), *sys.path]),
            ):
                first = run("first", "--run-id", "job-42.g5", "--stop-after", "1")
                resumed = run("resumed", "--resume", str(first / "checkpoint.pt"))
                explicit_resume = run(
                    "explicit-resume", "--resume", str(first / "checkpoint.pt"), "--run-id", "job-42.g5"
                )
                with self.assertRaises(SystemExit) as mismatch:
                    run("mismatch", "--resume", str(first / "checkpoint.pt"), "--run-id", "other-job")
                self.assertEqual(mismatch.exception.code, 2)
                self.assertFalse((root / "mismatch" / "manifest.json").exists())
                independent = run("independent", "--no-checkpoint")
                legacy_state = torch.load(
                    first / "checkpoint.pt", map_location="cpu", weights_only=False
                )
                legacy_state.pop("run_id")
                legacy_checkpoint = root / "legacy.pt"
                torch.save(legacy_state, legacy_checkpoint)
                legacy = run("legacy", "--resume", str(legacy_checkpoint))

            def manifest(out):
                return json.loads((out / "manifest.json").read_text(encoding="utf8"))

            run_id = manifest(first)["run_id"]
            self.assertEqual(manifest(resumed)["run_id"], run_id)
            self.assertEqual(run_id, "job-42.g5")
            self.assertEqual(manifest(explicit_resume)["run_id"], run_id)
            self.assertRegex(manifest(independent)["run_id"], r"^[0-9a-f]{32}$")
            self.assertEqual(manifest(first)["identity_sha256"], manifest(independent)["identity_sha256"])
            self.assertEqual(manifest(legacy)["run_id"], train_week2.sha256(legacy_checkpoint))
            self.assertEqual((resumed / "losses.txt").read_bytes(), (independent / "losses.txt").read_bytes())
            for out, steps in ((first, [0, 1]), (resumed, [0, 1, 2])):
                with self.subTest(out=out.name):
                    summary = json.loads((out / "summary.json").read_text(encoding="utf8"))
                    self.assertEqual(summary["run_id"], run_id)
                    checkpoint = torch.load(out / "checkpoint.pt", map_location="cpu", weights_only=False)
                    self.assertEqual(checkpoint["run_id"], run_id)
                    g8 = read_jsonl(out / "g8" / "metrics.jsonl")
                    native = read_jsonl(out / "metrics.jsonl")
                    self.assertEqual([row["step"] for row in g8], steps)
                    self.assertEqual([row["step"] for row in native], steps)
                    self.assertEqual({row["run_id"] for row in g8}, {run_id})
                    self.assertNotIn("run_id", native[0])


if __name__ == "__main__":
    unittest.main()
