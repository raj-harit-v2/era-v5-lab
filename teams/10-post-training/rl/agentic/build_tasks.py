"""Build agentic task folders from existing swe-envs (harness code; the only text written here is the fixed
output-format header of each prompt).

    python rl/agentic/build_tasks.py command <instance_id> [--id TASK_ID]
    python rl/agentic/build_tasks.py patch <instance_id> [--id TASK_ID]

A command task gets prompt.md = fixed header + the upstream issue text (swe-envs/<id>/issue.md, unchanged) + a
listing of the test files at the base commit (read from the env image with `git ls-files`), and
hidden/expected.json = the recorded test command, the set of tests that command runs (measured by running it
through the verifier's own path) and the FAIL_TO_PASS tests that must fail. A patch task gets prompt.md only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agentic_verifier as av  # noqa: E402

COMMAND_HEADER = """You have a shell in /repo, a checkout of a Python project at the commit just before an upstream fix. \
There is no network. The tests that cover the issue below are already in the checkout.

Reply with exactly one shell command in one ```bash block: a pytest command that runs the whole test file covering \
the issue. Use only `pytest` or `python -m pytest`, a file path from the list below, and optionally -q, -v, -s or \
--tb=<style>. One line: no pipes, `cd`, quotes or environment variables. Do not explain.
"""
PATCH_HEADER = """You have a checkout of a Python project at the commit just before an upstream fix. Reply with exactly \
one unified diff in one ```diff block that fixes the issue below. Do not edit test files. Do not explain.
"""


def test_listing(env_dir: Path, env: dict) -> list[str]:
    av.swe_verify().ensure_image(env_dir, env)
    script = "cd /repo && git ls-files | grep -E '(^|/)tests?/|(^|/)test_[^/]*\\.py$|_tests?\\.py$' | sort"
    out = subprocess.run(["docker", "run", "--rm", "--network=none", env["image"], "bash", "-c", script],
                         capture_output=True, text=True, check=True).stdout
    return out.split()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=av.MODES)
    ap.add_argument("instance_id")
    ap.add_argument("--id")
    a = ap.parse_args()
    env_dir = av.SWE_ENVS / a.instance_id
    env = json.loads((env_dir / "env.json").read_text(encoding="utf-8"))
    short = a.instance_id.split("__", 1)[1]
    task_id = a.id or (f"run_tests_{short}" if a.mode == "command" else f"patch_{short}")
    out = av.TASKS / task_id
    out.mkdir(parents=True, exist_ok=True)
    issue = (env_dir / "issue.md").read_text(encoding="utf-8").strip()
    meta = {"id": task_id, "mode": a.mode, "swe_env": a.instance_id, "language": env.get("language", "python"),
            "title": issue.splitlines()[0].lstrip("# ").strip()[:120],
            "source": f"{env['repo']} PR {env['pr_url'].rsplit('/', 1)[-1]} ({env['licence']}); issue text, tests and "
                      f"test command are the human records of swe-envs/{a.instance_id}; generator: none"}
    count = None
    if a.mode == "patch":
        meta["pool_overlap"] = f"swe/{a.instance_id}"
        prompt = PATCH_HEADER + "\nIssue (upstream text, unchanged):\n\n" + issue + "\n"
    else:
        (out / "hidden").mkdir(exist_ok=True)
        listing = test_listing(env_dir, env)
        prompt = (COMMAND_HEADER + "\nIssue (upstream text, unchanged):\n\n" + issue + "\n\nTest files in the "
                  "repository:\n\n" + "\n".join(listing) + "\n")
        cands = [f for f in listing if re.search(r"(^|/)test_[^/]*\.py$|_tests?\.py$", f)]
        meta["candidate_test_files"] = len(cands)
        meta["chance_level"] = round(1 / len(cands), 3)  # picking a listed test file at random
        args, why = av.parse_command(env["test_cmd"])
        assert args is not None, why
        side = av.run_command(env_dir, env, args)
        assert "ran" in side, side
        ran = side["ran"]
        must_fail = sorted(env["FAIL_TO_PASS"])
        assert all(not ran.get(t, True) for t in must_fail), "a FAIL_TO_PASS test did not fail at base"
        assert set(env["FAIL_TO_PASS"] + env["PASS_TO_PASS"]) <= set(ran), "recorded tests missing from the run"
        count = len(ran)
        (out / "hidden" / "expected.json").write_text(json.dumps(
            {"recorded_command": env["test_cmd"], "expected_tests": sorted(ran), "must_fail": must_fail,
             "note": "hidden: never put this folder in a prompt"}, indent=1) + "\n", encoding="utf-8")
    (out / "task.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "prompt.md").write_text(prompt, encoding="utf-8")
    print(json.dumps({"built": task_id, "tests_in_expected_set": count}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
