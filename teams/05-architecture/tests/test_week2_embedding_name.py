"""The arm value for the input embedding: ``ke2`` is the name, ``ke1`` is the older name.

Both select the same input path, the G4 raw-code projection in ``week2.model.KE2``.
Team 4 asked for the name ``ke2`` so that a reader does not think KE1 is in use.
The output head is not touched. It stays dense and untied.
"""

from contextlib import contextmanager
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import numpy as np
import torch

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
from week2.config import KE2_EMBEDDING_NAMES, load, load_runtime, merge, validate
from week2.model import LanguageModel

ARMS = ["t1.yaml", "t2.yaml", "t3.yaml"]
OLD_LINE = "  embedding: ke1\n"


@contextmanager
def copied_team():
    """A private copy of the files load_runtime reads, so an arm file can be edited."""
    with tempfile.TemporaryDirectory() as tmp:
        team = Path(tmp) / "teams/05-architecture"
        shutil.copytree(TEAM / "configs/arms", team / "configs/arms")
        (team / "configs/small").mkdir(parents=True)
        (team / "experiments").mkdir()
        for name in [
            "configs/runtime.yaml",
            "configs/open_choices.json",
            "configs/small/smoke_resolution.yaml",
            "experiments/plan_v1.md",
        ]:
            shutil.copy2(TEAM / name, team / name)
        yield team


def set_embedding(team, arm, value):
    path = team / "configs/arms" / arm
    text = path.read_text()
    if text.count(OLD_LINE) != 1:
        raise AssertionError(arm + " does not hold exactly one embedding line")
    path.write_text(text.replace(OLD_LINE, "  embedding: " + value + "\n"))
    return path


def embedding_errors(config):
    return [e for e in validate(config) if "embedding" in e]


class EmbeddingNameTests(unittest.TestCase):
    def test_ke2_is_the_name_and_ke1_is_the_older_name(self):
        self.assertEqual(KE2_EMBEDDING_NAMES, ("ke2", "ke1"))

    def test_arm_value_ke2_loads_and_validates(self):
        with copied_team() as team:
            runtime = team / "configs/runtime.yaml"
            for arm in ARMS:
                old = load_runtime(team / "configs/arms" / arm, runtime)
                new = load_runtime(set_embedding(team, arm, "ke2"), runtime)
                self.assertEqual(new["model"]["embedding"], "ke2", arm)
                self.assertEqual(embedding_errors(new), [], arm)
                # Nothing else in the model, optimizer or run settings moves.
                self.assertEqual(old["model"].pop("embedding"), "ke1", arm)
                new["model"].pop("embedding")
                for section in ["model", "optim", "run"]:
                    self.assertEqual(new[section], old[section], arm + " " + section)

    def test_arm_files_written_with_ke1_still_load(self):
        for arm in ARMS:
            config = load_runtime(TEAM / "configs/arms" / arm)
            self.assertIn(config["model"]["embedding"], KE2_EMBEDDING_NAMES, arm)
            self.assertEqual(embedding_errors(config), [], arm)

    def test_any_other_value_is_refused(self):
        for value in ["table", "ke3", "KE2", "null"]:
            with copied_team() as team:
                path = set_embedding(team, "t1.yaml", value)
                with self.assertRaisesRegex(ValueError, "Kronecker/MoE path"):
                    load_runtime(path, team / "configs/runtime.yaml")
        config = load_runtime(TEAM / "configs/arms/t1.yaml")
        config["model"]["embedding"] = "table"
        errors = embedding_errors(config)
        self.assertEqual(len(errors), 1)
        self.assertIn("ke2", errors[0])

    def test_both_names_build_the_same_model(self):
        rng = np.random.default_rng(7)
        rows = rng.integers(0, 256, (31, 4), dtype=np.uint8)
        lengths = rng.integers(1, 5, 31, dtype=np.int16)
        states = []
        for name in KE2_EMBEDDING_NAMES:
            config = merge(
                load_runtime(TEAM / "configs/arms/t1.yaml"),
                load(TEAM / "configs/small/smoke_resolution.yaml"),
            )
            model = config["model"]
            model.update(
                embedding=name,
                vocab_size=31,
                n_embd=16,
                n_layer=2,
                n_head=4,
                n_kv_head=2,
                block_size=8,
            )
            model["moe"].update(num_experts=4, top_k=2, num_shared=1, ffn_hidden=24)
            torch.manual_seed(11)
            states.append(LanguageModel(model, rows, lengths).state_dict())
        self.assertEqual(states[0].keys(), states[1].keys())
        for key in states[0]:
            self.assertTrue(torch.equal(states[0][key], states[1][key]), key)


if __name__ == "__main__":
    unittest.main()
