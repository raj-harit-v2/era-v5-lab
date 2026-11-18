#!/usr/bin/env python3
"""G10 Automated Pre-Flight Quality Gate Runner.

Executes all 5 mandatory Quality Gates before pushing or raising a PR:
  Gate 1: Repository Boundary, PR-Guard & Static Hygiene
  Gate 2: Unit & Regression Invariants (Pytest)
  Gate 3: Wire-Protocol & Dual-Perspective API Contracts (OpenAI SDK + Jinja Autoescape)
  Gate 4: Training-Serving Parity & Delimiter Token Alignment
  Gate 5: Automated Evidence Verification & Exit Code Enforcement
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# Path Resolution
_HERE = Path(__file__).resolve().parent
_TEAM = _HERE.parent
_REPO = _TEAM.parent.parent

# Color Helpers
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log_pass(msg: str) -> None:
    print(f"  {GREEN}[PASS]{RESET} {msg}")


def log_fail(msg: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {msg}")


def log_info(msg: str) -> None:
    print(f"  {BLUE}[INFO]{RESET} {msg}")


# -----------------------------------------------------------------------------
# Gate 1: Repository Boundary & Static Hygiene
# -----------------------------------------------------------------------------
def check_gate_1() -> bool:
    print(f"\n{BLUE}=== Gate 1: Repository Boundary & Static Hygiene ==={RESET}")
    all_ok = True

    # 1.1 Boundary & Topic-Folder Depth Scan
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(_REPO),
            capture_output=True,
            text=True,
            check=True,
        )
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        for line in lines:
            parts = line.split(maxsplit=1)
            if len(parts) < 2:
                continue
            fpath = parts[1].rstrip("/")
            # Check team boundary
            if not fpath.startswith("teams/10-post-training"):
                log_fail(f"Boundary violation: Modified file outside teams/10-post-training/: {fpath}")
                all_ok = False
            # Check PR Guard topic depth for files (directories in porcelain will have files inside)
            f_p = Path(_REPO / fpath)
            if f_p.is_file():
                f_parts = Path(fpath).parts
                if f_parts[0] == "teams" and len(f_parts) < 4 and not fpath.lower().endswith(".md"):
                    log_fail(f"PR-Guard violation: Non-markdown file not in a topic folder (depth < 4): {fpath}")
                    all_ok = False
        if all_ok:
            log_pass("All modified files reside strictly within teams/10-post-training/ topic subdirectories")
    except Exception as e:
        log_fail(f"Git status inspection failed: {e}")
        all_ok = False

    # 1.2 Secret & Credential Scan
    secret_patterns = [
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    ]
    secret_found = False
    for root, _, files in os.walk(_TEAM):
        if ".git" in root or "__pycache__" in root or ".pytest_cache" in root or ".ruff_cache" in root:
            continue
        for file in files:
            p = Path(root) / file
            if p.suffix in (".py", ".jinja", ".json", ".md", ".sh"):
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    for pat in secret_patterns:
                        if pat.search(text):
                            log_fail(f"Potential secret detected in {p.relative_to(_TEAM)}")
                            secret_found = True
                            all_ok = False
                except Exception:
                    pass
    if not secret_found:
        log_pass("Secret & credential scan clean (Zero private keys, API keys, or tokens detected)")

    # 1.3 Ruff Lint & Style
    ruff_bin = _REPO / ".venv" / "bin" / "ruff"
    if not ruff_bin.is_file():
        ruff_bin = Path(sys.executable).parent / "ruff"
    if ruff_bin.is_file():
        try:
            target_files = [
                str(_TEAM / "chat-format"),
                str(_TEAM / "scripts"),
                str(_TEAM / "tests" / "test_chat_template.py"),
                str(_TEAM / "tests" / "test_frozen_tokenizer.py"),
                str(_TEAM / "tests" / "test_render.py"),
            ]
            r = subprocess.run(
                [str(ruff_bin), "check"] + target_files,
                capture_output=True,
                text=True,
            )
            if r.returncode == 0:
                log_pass("Ruff static linter passed with zero errors")
            else:
                log_fail(f"Ruff reported lint errors:\n{r.stdout}")
                all_ok = False
        except Exception as e:
            log_info(f"Skipping ruff execution: {e}")
    else:
        log_info("Ruff binary not found in virtualenv; skipping ruff check")

    return all_ok


# -----------------------------------------------------------------------------
# Gate 2: Core Test Suite & AST Invariants
# -----------------------------------------------------------------------------
def check_gate_2() -> bool:
    print(f"\n{BLUE}=== Gate 2: Core Unit & Regression Invariants ==={RESET}")
    pytest_bin = _REPO / ".venv" / "bin" / "pytest"
    if not pytest_bin.is_file():
        pytest_bin = Path(sys.executable).parent / "pytest"

    if not pytest_bin.is_file():
        log_fail("pytest executable not found in virtual environments")
        return False

    test_targets = [
        str(_TEAM / "tests" / "test_render.py"),
        str(_TEAM / "tests" / "test_frozen_tokenizer.py"),
        str(_TEAM / "tests" / "test_chat_template.py"),
        str(_TEAM / "tests" / "test_chat_template_parity.py"),
    ]
    try:
        cmd = [str(pytest_bin)] + test_targets + ["-v", "-rs"]
        res = subprocess.run(cmd, cwd=str(_TEAM), capture_output=True, text=True)
        if res.returncode == 0:
            log_pass("All core test suites passed cleanly (render.py, frozen tokenizer, chat template)")
            return True
        else:
            log_fail(f"Test suite failures detected:\n{res.stdout}\n{res.stderr}")
            return False
    except Exception as e:
        log_fail(f"Failed to execute pytest: {e}")
        return False


# -----------------------------------------------------------------------------
# Gate 3: Wire-Protocol & Dual-Perspective API Contracts
# -----------------------------------------------------------------------------
def check_gate_3() -> bool:
    print(f"\n{BLUE}=== Gate 3: Wire-Protocol & Dual-Perspective API Contracts ==={RESET}")
    all_ok = True

    try:
        import json as _json

        template_path = _TEAM / "chat-format" / "chat_template.jinja"
        template_content = template_path.read_text(encoding="utf-8")

        # Compile in the vLLM / transformers execution environment
        try:
            from transformers.utils.chat_template_utils import _compile_jinja_template
            tmpl = _compile_jinja_template(template_content)
        except Exception:
            from jinja2.sandbox import ImmutableSandboxedEnvironment

            def _tojson(x, ensure_ascii=False, indent=None, separators=None, sort_keys=False):
                return _json.dumps(x, ensure_ascii=ensure_ascii, indent=indent, separators=separators, sort_keys=sort_keys)

            env = ImmutableSandboxedEnvironment(
                trim_blocks=True,
                lstrip_blocks=True,
                extensions=["jinja2.ext.loopcontrols"],
                autoescape=False,
            )
            env.filters["tojson"] = _tojson
            tmpl = env.from_string(template_content)

        # 3.1 Test Top-Level `tools` Injection (OpenAI Spec & SFT Parity)
        tools_fixture = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Fetch weather for city",
                    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
                },
            }
        ]
        out_with_tools = tmpl.render(
            messages=[{"role": "user", "content": "How is the weather in Delhi?"}],
            tools=tools_fixture,
            effort="4k",
            add_generation_prompt=True,
        )

        if ("# Tools" not in out_with_tools and "Tools:" not in out_with_tools) or "get_weather" not in out_with_tools:
            log_fail("chat_template.jinja failed to render top-level 'tools' parameter under Tools header in system turn")
            all_ok = False
        else:
            log_pass("Top-level OpenAI 'tools' schema injection verified under Tools header")

        # 3.2 Test OpenAI Assistant `tool_calls` Unwrapping
        openai_history = [
            {"role": "user", "content": "Get weather"},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {"name": "get_weather", "arguments": {"city": "Bengaluru"}},
                    }
                ],
            },
            {"role": "tool", "content": "Sunny 28C"},
        ]
        out_history = tmpl.render(
            messages=openai_history,
            effort="4k",
            add_generation_prompt=True,
        )

        if '"type": "function"' in out_history or '"type":"function"' in out_history or '"function": {' in out_history or '"function":{' in out_history:
            log_fail("chat_template.jinja failed to unwrap OpenAI tool_calls wrapper; raw 'function' envelope emitted")
            all_ok = False
        elif ("get_weather" in out_history and "arguments" in out_history and "Bengaluru" in out_history):
            log_pass("OpenAI history tool_calls correctly unwrapped to {'name': ..., 'arguments': ...}")
        else:
            log_fail("chat_template.jinja did not format unwrapped tool_calls correctly")
            all_ok = False

        # 3.3 Test Jinja HTML-Escaping Safety
        if "&lt;|im_start|&gt;" in out_with_tools or "&lt;|im_end|&gt;" in out_with_tools:
            log_fail("Jinja autoescaping hazard detected: special tokens were HTML-escaped into &lt; and &gt;")
            all_ok = False
        elif "<|im_start|>" in out_with_tools and "<|im_end|>" in out_with_tools:
            log_pass("Delimiter escaping safety verified (Special tokens preserved as raw byte markers)")
        else:
            log_fail("Missing expected ChatML delimiters in rendered output")
            all_ok = False

    except Exception as e:
        log_fail(f"Gate 3 wire-protocol verification encountered an exception: {e}")
        all_ok = False

    return all_ok


# -----------------------------------------------------------------------------
# Gate 4: Training-Serving Parity & Delimiter Token Alignment
# -----------------------------------------------------------------------------
def check_gate_4() -> bool:
    print(f"\n{BLUE}=== Gate 4: Training-Serving Parity & Delimiter Token Alignment ==={RESET}")
    all_ok = True

    # 4.1 Verify Delimiter Token IDs Aligned with Team 3 Frozen Tokenizer
    expected_markers = {
        "<|im_start|>": 129994,
        "<|im_end|>": 130816,
        "<|tool_call|>": 130773,
        "<|tool_result|>": 130774,
        "<|endoftext|>": 130822,
        "<|think|>": 130823,
        "<|/think|>": 130824,
        "<|/tool_call|>": 130825,
        "<|/tool_result|>": 130826,
    }

    render_path = _TEAM / "chat-format" / "render.py"
    if render_path.is_file():
        spec = compile(render_path.read_text(encoding="utf-8"), str(render_path), "exec")
        ns: dict = {"__file__": str(render_path)}
        exec(spec, ns)
        assigned = ns.get("ASSIGNED_SURFACES", {})
        id_to_surf = {idx: surf for idx, (_, surf) in assigned.items()}
        for surf, expected_id in expected_markers.items():
            if id_to_surf.get(expected_id) != surf:
                log_fail(f"Delimiter ID mismatch: {surf} expected ID {expected_id}, got {id_to_surf.get(expected_id)}")
                all_ok = False
        if all_ok:
            log_pass("All 9 active ChatML v0 markers align with exact frozen tokenizer IDs (129994, 130816, 130822..130826)")
    else:
        log_fail(f"Missing {render_path}")
        all_ok = False

    # 4.2 Verify Reasoning Effort Budgets
    budgets = {"1k": 1024, "4k": 4096, "16k": 16384, "64k": 65536}
    if ns.get("EFFORT_BUDGETS") == budgets:
        log_pass("Reasoning effort budgets verified: 1k (1024), 4k (4096), 16k (16384), 64k (65536)")
    else:
        log_fail(f"Reasoning effort budgets discrepancy: {ns.get('EFFORT_BUDGETS')}")
        all_ok = False

    return all_ok


# -----------------------------------------------------------------------------
# Gate 5: Summary & Exit Code Enforcement
# -----------------------------------------------------------------------------
def main() -> int:
    print("=" * 80)
    print("G10 POST-TRAINING: AUTOMATED PRE-FLIGHT QUALITY GATES")
    print(f"Target Directory: {_TEAM}")
    print("=" * 80)

    g1 = check_gate_1()
    g2 = check_gate_2()
    g3 = check_gate_3()
    g4 = check_gate_4()

    print("\n" + "=" * 80)
    print("PRE-FLIGHT QUALITY GATE SUMMARY")
    print("=" * 80)
    print(f"  Gate 1 (Boundary, PR-Guard & Static Hygiene):    {GREEN + 'PASS' if g1 else RED + 'FAIL'}{RESET}")
    print(f"  Gate 2 (Core Unit & Regression Invariants):      {GREEN + 'PASS' if g2 else RED + 'FAIL'}{RESET}")
    print(f"  Gate 3 (Wire-Protocol & Dual-Perspective API):   {GREEN + 'PASS' if g3 else RED + 'FAIL'}{RESET}")
    print(f"  Gate 4 (Training-Serving Delimiter Parity):      {GREEN + 'PASS' if g4 else RED + 'FAIL'}{RESET}")
    print("=" * 80)

    if g1 and g2 and g3 and g4:
        print(f"{GREEN}ALL QUALITY GATES PASSED. Work is certified ready for PR presentation.{RESET}\n")
        evidence_path = _TEAM / "results" / "preflight_evidence.md"
        evidence_path.write_text(
            "# G10 Automated Pre-Flight Quality Gate Evidence\n\n"
            "**Document:** `teams/10-post-training/docs/quality_gates.md`  \n"
            "**Runner:** `teams/10-post-training/scripts/preflight_check.py`  \n"
            "**Verdict:** `ALL QUALITY GATES PASSED (EXIT CODE 0)`  \n\n"
            "| Gate | Category | Status | Details |\n"
            "|---|---|:---:|---|\n"
            "| **Gate 1** | Repository Boundary & Static Hygiene | **PASS** | Modified files strictly within `teams/10-post-training/` topic folders; clean secret scan |\n"
            "| **Gate 2** | Core Unit & Regression Invariants | **PASS** | Pytest suites green (render.py, frozen tokenizer, chat template, parity) |\n"
            "| **Gate 3** | Wire-Protocol & Dual-Perspective API | **PASS** | OpenAI `tools` injection and assistant `tool_calls` unwrapping verified; autoescaping safe |\n"
            "| **Gate 4** | Training-Serving Parity & Delimiters | **PASS** | All 9 ChatML markers aligned with frozen tokenizer IDs; effort budgets verified |\n"
            "| **Gate 5** | Pre-Flight Automated Sign-Off | **PASS** | Circuit breaker disarmed; certified ready for PR presentation |\n",
            encoding="utf-8",
        )
        return 0
    else:
        print(f"{RED}QUALITY GATES FAILED. Trip circuit breaker. Do not push until issues are resolved.{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
