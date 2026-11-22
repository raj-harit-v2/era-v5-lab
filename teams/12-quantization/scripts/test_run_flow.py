#!/usr/bin/env python3
"""run_flow.py builds the two commands and stops at the first failure (stub runner, nothing is run):  python test_run_flow.py"""
import argparse, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_flow as r  # noqa: E402


def ns(**kw):
    return argparse.Namespace(**{"checkpoint": "c", "tokenizer": "t.json", "tokenizer_sha256": None, "eval": "e.json", "work": "w",
                                 "out": "o", "manifest": None, "source_dir": [], **kw})


class RunFlowTests(unittest.TestCase):
    def test_second_command_reads_the_gguf_dir_and_scores_of_the_first(self):
        qe, flow = r.commands(ns(), [])
        self.assertEqual(qe[qe.index("--scores-out") + 1], flow[flow.index("--scores") + 1])
        self.assertEqual(qe[qe.index("--work") + 1], flow[flow.index("--gguf-dir") + 1])
        self.assertIn("--delete-ggufs", flow); self.assertNotIn("--manifest", flow)
        self.assertEqual(flow[flow.index("--formats") + 1], "Q8_0,Q4_K_M")

    def test_manifest_and_source_dirs_go_to_the_flow_and_extra_args_to_quantize_eval(self):
        qe, flow = r.commands(ns(manifest="m.json", source_dir=["a=1", "b=2"], tokenizer_sha256="f" * 64), ["--roundtrip"])
        self.assertEqual(flow[flow.index("--manifest"):][:6], ["--manifest", "m.json", "--source-dir", "a=1", "--source-dir", "b=2"])
        self.assertIn("--roundtrip", qe); self.assertEqual(qe[qe.index("--tokenizer-sha256") + 1], "f" * 64)

    def test_stops_at_the_first_non_zero_exit(self):
        seen = []
        def runner(c, code):
            seen.append(Path(c[1]).name); return argparse.Namespace(returncode=code)
        cmds = r.commands(ns(), [])
        self.assertEqual(r.run_all(cmds, lambda c: runner(c, 3)), 3); self.assertEqual(seen, ["quantize_eval.py"])
        seen.clear()
        self.assertEqual(r.run_all(cmds, lambda c: runner(c, 0)), 0); self.assertEqual(seen, ["quantize_eval.py", "flow_fixed_prompts.py"])


if __name__ == "__main__":
    unittest.main()
