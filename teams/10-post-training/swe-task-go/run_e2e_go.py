"""End-to-end Go SWE task runner (Go tests run in Docker, trajectory rendered with render.py).

Run from the repository root:

    python teams/10-post-training/swe-task-go/run_e2e_go.py

1. Copies the Go task to a temp directory (the repo files are never edited).
2. Runs `go test ./...` in a locked-down golang container: expects a failure (exit 1).
3. Applies the patch (`i := 1` -> `i := 0`) and runs `go test ./...` again: expects a pass (exit 0).
4. Runs `go vet ./...` on the patched copy.
5. Renders the whole agent trajectory with chat_format_v0 (effort 4k) and checks the parse round trip,
   that Go tabs and CRLF survive, and that a literal control marker in Go source is rejected.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = os.environ.get("G10_GO_IMAGE", "golang:1.23-alpine")
TASK_FILES = ("go.mod", "stats.go", "stats_test.go")

_spec = importlib.util.spec_from_file_location(
    "g10_render", HERE.parent / "chat-format" / "render.py"
)
assert _spec is not None and _spec.loader is not None
render_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_mod)


def docker_go(workdir: Path, *go_args: str) -> tuple[int, str]:
    """Run `go <args>` in an air-gapped, non-root container on a copy of the task."""
    cmd = [
        "docker", "run", "--rm",
        "--network", "none",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-e", "HOME=/tmp", "-e", "GOCACHE=/tmp/gocache",
        "-v", f"{workdir}:/work", "-w", "/work",
        IMAGE, "go", *go_args,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="g10-go-swe-") as tmp:
        work = Path(tmp)
        for name in TASK_FILES:
            shutil.copy(HERE / name, work / name)
        src_file = work / "stats.go"
        before_src = src_file.read_text(encoding="utf-8")

        fail_code, fail_out = docker_go(work, "test", "./...")
        print(f"[step 1] initial test exit={fail_code}")
        print(fail_out)
        assert fail_code != 0, "expected the seeded version to fail"

        patched_src = before_src.replace("i := 1;", "i := 0;")
        assert patched_src != before_src, "patch did not apply"
        src_file.write_text(patched_src, encoding="utf-8")
        pass_code, pass_out = docker_go(work, "test", "./...")
        print(f"[step 2] post-patch test exit={pass_code}")
        print(pass_out)
        assert pass_code == 0, "expected the patched version to pass"

        fmt_code, fmt_out = docker_go(work, "vet", "./...")
        print(f"[step 3] go vet exit={fmt_code} {fmt_out}".rstrip())
        assert fmt_code == 0, "go vet failed after the patch"

    messages = [
        {"role": "system", "content": "You edit Go code and you report only what a tool returned."},
        {"role": "user", "content": "TestSum fails in stats.go. Fix Sum."},
        {
            "role": "assistant",
            "content": "I am reading stats.go before editing it.",
            "tool_calls": [{"name": "read_file", "arguments": {"path": "stats.go"}}],
        },
        {"role": "tool", "content": before_src},
        {
            "role": "assistant",
            "content": "The loop starts at index 1 and skips the first element.",
            "tool_calls": [
                {
                    "name": "apply_patch",
                    "arguments": {
                        "path": "stats.go",
                        "old": "for i := 1; i < len(nums); i++ {",
                        "new": "for i := 0; i < len(nums); i++ {",
                    },
                }
            ],
        },
        {"role": "tool", "content": pass_out},
        {"role": "assistant", "content": "go test ./... passes with exit code 0."},
    ]
    transcript = render_mod.render(messages, effort="4k")
    parsed = render_mod.parse(transcript)
    assert parsed == {"effort": "4k", "messages": messages}, "round trip changed the messages"
    assert "\t" in transcript, "Go tabs were lost"
    print(f"[step 4] chat_format_v0 render/parse verified: effort={parsed['effort']} turns={len(parsed['messages'])}")

    # Go-specific edge cases for the renderer.
    crlf_src = "package x\r\n\r\nfunc f(ch chan int) int {\r\n\treturn <-ch\r\n}\r\n"
    crlf_msgs = [{"role": "user", "content": "fix"}, {"role": "tool", "content": crlf_src}]
    assert render_mod.parse(render_mod.render(crlf_msgs, effort="4k"))["messages"] == crlf_msgs
    print("[step 5] tabs, CRLF and the channel operator <- survive the round trip")
    for literal in ('s := "<|im_start|>"', 's := "<think>"'):
        try:
            render_mod.render([{"role": "user", "content": literal}], effort="4k")
        except render_mod.RenderError as exc:
            print(f"[step 6] rejected as expected: {literal} -> {exc}")
        else:
            raise AssertionError(f"marker was accepted: {literal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
