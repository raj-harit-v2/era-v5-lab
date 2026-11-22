"""TST through the real trainer: the phase switches at tst_frac, and the logged token count stays the real one."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from test_week2_model import TEAM, fixture
import train_week2


class TstTrainerTests(unittest.TestCase):
    def run_trainer(self, tst):
        cfg, byte_rows, _ = fixture()
        cfg["model"]["ke_max_pos"] = byte_rows.shape[1]
        cfg["model"]["block_size"] = 12
        if tst:
            cfg["run"].update(tst=True, tst_bag=3, tst_frac=0.5)
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
        with TemporaryDirectory() as temp:
            root = Path(temp)
            train = root / "train.jsonl"
            val = root / "val.jsonl"
            train.write_text('{"text":"' + "abcdefghijklmnop" * 4 + '"}\n', encoding="utf8")
            val.write_text('{"text":"' + "ponmlkjihgfedcba" * 2 + '"}\n', encoding="utf8")
            argv = [
                "train_week2.py", "--config", "fixture.yaml",
                "--tokenizer", "fixture.json", "--byte-table", "fixture.npz",
                "--train-data", str(train), "--heldout-data", str(val),
                "--smoke", "--smoke-steps", "4", "--smoke-batch-size", "1", "--smoke-seq-len", "12",
                "--no-checkpoint", "--out", str(root / "out"),
            ]
            with (
                patch.object(train_week2, "load_runtime", return_value=cfg),
                patch.object(train_week2, "Artifacts", return_value=artifacts),
                patch.object(sys, "argv", argv),
            ):
                train_week2.main()
            rows = [json.loads(l) for l in (root / "out" / "metrics.jsonl").read_text(encoding="utf8").splitlines()]
        return [r for r in rows if "perf/step_ms" in r]

    def test_scored_tokens_are_real_tokens_in_both_phases(self):
        on, off = self.run_trainer(True), self.run_trainer(False)
        self.assertEqual(len(on), 4)
        # Same data, same batches: the logged token count does not change with TST (it is not the bag count).
        self.assertEqual([r["train/scored_tokens"] for r in on], [r["train/scored_tokens"] for r in off])
        self.assertTrue(all(r["train/scored_tokens"] > 3 for r in on))
        # TST only in the first half: steps 1 and 2 differ from normal training, steps 3 and 4 use the normal loss.
        self.assertNotEqual(on[0]["loss_ntp"], off[0]["loss_ntp"])
        self.assertTrue(all(np.isfinite(r["loss_ntp"]) for r in on))


if __name__ == "__main__":
    unittest.main()
