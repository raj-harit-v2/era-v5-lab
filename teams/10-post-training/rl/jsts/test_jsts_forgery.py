"""Attacks on jsts_verifier.py (report forgery and matcher tampering): every one must score 0 in the real sandbox.

Run:  python -m pytest teams/10-post-training/rl/jsts/test_jsts_forgery.py -q -p no:cacheprovider
Needs Docker and the image g10-jsts-rl:1 (README.md); skipped, with the reason, when either is missing.
The candidates in attacks.py are FIXTURES written to attack the verifier; they are not training data.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v = _load("jsts_verifier")
attacks = _load("attacks")
parametrize = pytest.mark.parametrize  # named: pr-guard reads a dotted decorator line of a diff as an email address


def _docker_image_ok() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "image", "inspect", v.IMAGE], capture_output=True).returncode == 0


needs_image = pytest.mark.skipif(not _docker_image_ok(), reason=f"docker or the image {v.IMAGE} is missing")
TASK = v.TASKS / "js" / "binary"


def _score(code: str) -> dict:
    return v.reward(TASK, "```javascript\n" + code + "\n```")


@needs_image
@parametrize("label", sorted(attacks.ATTACKS))
def test_attack_scores_zero(label):
    _, code = attacks.ATTACKS[label]
    out = _score(code)
    assert out["reward"] == 0, (label, out)


@needs_image
@parametrize("label", sorted(attacks.TASK_ATTACKS))
def test_realm_attack_scores_zero(label):
    """Attacks that edit the spec's jest realm before the run (J1, J1b, J5) or tamper unselectively (J1c): the candidate
    is loaded in its own V8 context behind a copying membrane (membrane.cjs), so none of them reaches the test registry."""
    task, fence, _, fname = attacks.TASK_ATTACKS[label]
    code = (HERE / "attack_fixtures" / fname).read_text()
    out = v.reward(v.TASKS / task, f"```{fence}\n{code}\n```")
    assert out["reward"] == 0, (label, out)


@needs_image
def test_every_reference_scores_one_and_every_stub_zero_behind_the_membrane():
    """The membrane must not change what a correct solution scores: all references 1, all stubs 0."""
    for meta in sorted(v.TASKS.glob("*/*/task.json")):
        good, bad = v.known_outputs(meta.parent)
        assert v.reward(meta.parent, good)["reward"] == 1, (meta.parent.name, "reference")
        assert v.reward(meta.parent, bad)["reward"] == 0, (meta.parent.name, "stub")


@needs_image
def test_a_jest_realm_escape_does_not_get_out_of_the_candidate_context():
    """Before the membrane (job T) the canary caught this (reason "canary"); now the candidate context has no `expect`
    to reach through, so the load fails and every test fails. Either way the reward is 0 and no test passes."""
    out = _score(attacks.ATTACKS["tamper_object_is_outer_realm"][1])
    assert out["reward"] == 0 and "did not pass" in out["reason"], out


@needs_image
def test_the_report_cannot_be_written_by_the_candidate_user():
    """The jest parent is root and prints the report to a root-owned file; the candidate runs as `runner`."""
    probe = ("const fs = require('fs'); const out = [];\n"
             "for (const t of ['/tmp/g10_out', '/tmp/g10_log']) { try { fs.appendFileSync(t, 'x'); out.push(t + ' WRITABLE'); } catch (e) {} }\n"
             "if (process.getuid() === 0) out.push('RUNS AS ROOT');\n"
             "if (out.length) throw new Error(out.join(', '));\n" + attacks.EXPORT)
    out = _score(probe)
    assert "WRITABLE" not in out["reason"] and "ROOT" not in out["reason"], out


@needs_image
def test_a_correct_solution_still_scores_one_and_the_guard_costs_little():
    good, _ = v.known_outputs(TASK)
    t0 = time.time()
    out = v.reward(TASK, good)
    assert out["reward"] == 1, out
    assert time.time() - t0 < 10  # measured ~1 s on an M1 Pro; the old runner took ~0.8 s
