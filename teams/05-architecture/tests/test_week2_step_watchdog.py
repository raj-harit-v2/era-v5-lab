"""Exercise the watchdog exit contract through the G5 CLI in a child process."""

from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from test_week2_model import TEAM, fixture
import train_week2


def run_fixture(root, mode):
    root = Path(root)
    cfg, byte_rows, _ = fixture()
    cfg["model"]["ke_max_pos"] = byte_rows.shape[1]
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
    train = root / "train.jsonl"
    val = root / "val.jsonl"
    train.write_text('{"text":"aaaa"}\n', encoding="utf8")
    val.write_text('{"text":"bbbb"}\n', encoding="utf8")
    args = [
        "train_week2.py", "--config", "fixture.yaml",
        "--tokenizer", "fixture.json", "--byte-table", "fixture.npz",
        "--train-data", str(train), "--heldout-data", str(val),
        "--out", str(root / "out"),
        "--smoke", "--smoke-steps", "2", "--smoke-batch-size", "1", "--no-checkpoint",
    ]
    if mode == "off":
        args.extend(["--watchdog-s", "0"])
    if mode == "cli":
        args.extend(["--watchdog-s", "5"])
    next_batch = train_week2.BatchStream.next
    evaluate = train_week2.evaluate
    steps = 0
    evaluations = 0

    def read_batch(stream, device):
        nonlocal steps
        steps += 1
        if mode == "batch" and steps == 2:
            time.sleep(8)
        return next_batch(stream, device)

    def run_evaluation(*args, **kwargs):
        nonlocal evaluations
        evaluations += 1
        if (mode == "initial_eval" and evaluations == 1) or (mode == "eval" and evaluations == 2):
            time.sleep(8)
        if mode in ("off", "cli") and evaluations == 1:
            time.sleep(1.75)
        return evaluate(*args, **kwargs)

    with ExitStack() as stack:
        stack.enter_context(patch.object(train_week2, "load_runtime", return_value=cfg))
        stack.enter_context(patch.object(train_week2, "Artifacts", return_value=artifacts))
        stack.enter_context(patch.object(train_week2.BatchStream, "next", read_batch))
        stack.enter_context(patch.object(train_week2, "evaluate", run_evaluation))
        if mode == "save":
            args.remove("--no-checkpoint")
            args.extend([
                "--checkpoint-store", str(root / "store"), "--run-id", "watchdog-save",
                "--checkpoint-interval-s", "0.001",
            ])
            from ckpt.ckpt import Checkpointer

            save = Checkpointer.save

            def stalled_save(checkpointer, *args, **kwargs):
                if kwargs["reason"] == "interval":
                    time.sleep(8)
                return save(checkpointer, *args, **kwargs)

            stack.enter_context(patch.object(Checkpointer, "save", stalled_save))
        stack.enter_context(patch.object(sys, "argv", args))
        train_week2.main()


class StepWatchdogTests(unittest.TestCase):
    def launch(self, root, mode, limit="1.5"):
        paths = [str(TEAM / "tests"), str(TEAM.parent / "07-infrastructure")]
        if os.environ.get("PYTHONPATH"):
            paths.append(os.environ["PYTHONPATH"])
        env = {
            **os.environ, "PYTHONPATH": os.pathsep.join(paths), "OMP_NUM_THREADS": "1",
            "WATCHDOG_S": limit, "RUN_ID": "g5-watchdog-test",
            "V5_EVENTS_DIR": str(root / "events"), "V5_RUNS_DIR": str(root / "notes"),
        }
        script = (
            "import sys; from test_week2_step_watchdog import run_fixture; "
            "run_fixture(sys.argv[1], sys.argv[2])"
        )
        return subprocess.run(
            [sys.executable, "-B", "-c", script, str(root), mode],
            env=env, capture_output=True, text=True, timeout=35,
        )

    def assert_timeout(self, mode, step, frame):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            result = self.launch(root, mode)
            self.assertEqual(result.returncode, 75, result.stderr)
            self.assertIn("G5 step watchdog", result.stderr)
            self.assertIn(frame, result.stderr)
            event_file, = (root / "events").glob("*.jsonl")
            event = json.loads(event_file.read_text())
            self.assertEqual((event["event"], event["step"]), ("train.watchdog", step))
            self.assertEqual(event["limit_s"], 1.5)
            note_file, = (root / "notes" / "g5-watchdog-test").glob("*.json")
            note = json.loads(note_file.read_text())
            self.assertEqual((note["code"], note["cause"], note["step"]), (75, "hang_watchdog", step))
            self.assertFalse((root / "out" / "summary.json").exists())

    def test_environment_timeout_catches_stalled_second_step(self):
        self.assert_timeout("batch", 1, "in read_batch")

    def test_initial_evaluation_stall_trips_watchdog(self):
        self.assert_timeout("initial_eval", 0, "in run_evaluation")

    def test_in_loop_evaluation_stall_reports_completed_step(self):
        self.assert_timeout("eval", 2, "in run_evaluation")

    @unittest.skipUnless(hasattr(train_week2, "CheckpointProgress"), "Requires the #608 integration")
    def test_periodic_save_stall_trips_watchdog(self):
        self.assert_timeout("save", 1, "in stalled_save")

    def test_explicit_zero_and_cli_timeout_override_environment(self):
        for mode in ("off", "cli"):
            with self.subTest(mode=mode), TemporaryDirectory() as temp:
                root = Path(temp)
                result = self.launch(root, mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((root / "events").exists())
                summary = json.loads((root / "out" / "summary.json").read_text())
                self.assertEqual(summary["steps"], 2)


if __name__ == "__main__":
    unittest.main()
