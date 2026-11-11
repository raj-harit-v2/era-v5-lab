"""Build one G10 SWE environment from a merged upstream GitHub PR.

All environment content comes from the upstream PR: the issue text from the linked GitHub issue, the gold
patch from the PR's non-test files, and the hidden tests from the PR's test files. This script writes no
issue text, test or fix of its own; it only cuts the PR apart, pins the environment and measures which
tests flip.

Steps:
  1. Read the PR, its linked issues and its commits with `gh api`. Refuse PRs or issues that mention an
     AI coding tool (TSAI 3 Nov rule: closed-model output is out; an unknown generator is out).
  2. Clone the repo into a cache, take base_commit = merge-base(PR base, PR head), and split
     `git diff base_commit PR-head` into gold.patch (non-test files) and test.patch (test files).
  3. Resolve dependencies as of the merge date (`uv pip install --exclude-newer`) in a throwaway image,
     freeze them into requirements.lock, and write a Dockerfile that installs exactly that lock.
     The image holds the repo at base_commit with no git history (the fix cannot be read from .git).
  4. Run the hidden tests twice before and twice after the gold patch. FAIL_TO_PASS = tests that pass
     after and fail (or are missing) before; PASS_TO_PASS = tests that pass on both sides. Flaky tests
     are dropped. Then run `verify.py --check` for the 5-run gold check.

Usage:
    python make_env.py --repo pallets/click --pr 1934 [--python 3.9] [--deps "pytest==6.2.4"]
           [--targets tests/test_options.py] [--allow-markers] [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import import_pool  # noqa: E402
import verify  # noqa: E402

CACHE = Path.home() / ".cache" / "g10-swe" / "repos"
UV_VERSION = "0.13.7"
GO_IMAGE = "golang:1.21-bookworm"
# Build tools may be newer than the merge date: setuptools before 64 cannot do PEP 660 editable installs.
# Runtime and test dependencies stay as of the merge date.
BUILD_TOOLS_DATE = "2025-06-01"


def build_tools(date: str) -> str:
    return f"--exclude-newer-package setuptools={date} --exclude-newer-package wheel={date}"
AI_MARKERS = re.compile(
    r"\b(claude|anthropic|copilot|codex|chatgpt|gpt-[345]|openai|gemini|devin|llm)\b|cursor[ .](ai|agent|com|sh)\b|"
    r"generated with|ai[- ]assisted|co-authored-by:[^\n]*(bot|ai)\b", re.I)
TEST_REQ_FILES = ("requirements/tests.txt", "requirements/test.txt", "requirements-test.txt",
                  "requirements-tests.txt", "test-requirements.txt", "tests/requirements.txt",
                  "requirements_test.txt", "requirements-dev.txt", "dev-requirements.txt", "requirements/dev.txt")


def sh(cmd: list[str], **kw) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout


def gh_json(path: str) -> dict | list:
    return json.loads(sh(["gh", "api", path]))


def gh_graphql_issues(owner: str, name: str, number: int) -> list[dict]:
    q = """query($o:String!,$n:String!,$p:Int!){repository(owner:$o,name:$n){pullRequest(number:$p){
      closingIssuesReferences(first:5){nodes{number title body url createdAt author{login}}}}}}"""
    out = json.loads(sh(["gh", "api", "graphql", "-f", f"query={q}", "-F", f"o={owner}", "-F", f"n={name}",
                         "-F", f"p={number}"]))
    return out["data"]["repository"]["pullRequest"]["closingIssuesReferences"]["nodes"]


def python_for(year: int) -> str:
    return "3.8" if year <= 2020 else "3.9" if year == 2021 else "3.10"


def image_digest(ref: str) -> str:
    out = sh(["docker", "buildx", "imagetools", "inspect", ref])
    return re.search(r"^Digest:\s+(sha256:[0-9a-f]+)", out, re.M).group(1)


def dockerfile(base_image: str, repo: str, sha: str, install: str, lang: str = "python") -> str:
    tools = ("" if lang == "go" else
             f"RUN pip install --no-cache-dir uv=={UV_VERSION} \\\n"
             "    && uv venv --quiet --python /usr/local/bin/python3 /venv\n"
             "ENV VIRTUAL_ENV=/venv PATH=/venv/bin:$PATH\n")
    return f"""# G10 SWE environment image. Repo at the PR base commit, no git history, pinned dependencies.
FROM {base_image}
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \\
    && rm -rf /var/lib/apt/lists/*
{tools}RUN git clone --quiet https://github.com/{repo}.git /repo && cd /repo \\
    && git checkout --quiet {sha} \\
    && git submodule update --init --recursive --quiet \\
    && find . -name .git -prune -exec rm -rf {{}} + \\
    && git init --quiet && git add -A \\
    && git -c user.name=base -c user.email=base@localhost commit --quiet -m base
WORKDIR /repo
{install}
RUN useradd --create-home runner && chown -R runner /repo
USER runner
"""


def install_spec(cache: Path, sha: str, extra: list[str]) -> list[str]:
    files = set(sh(["git", "-C", str(cache), "ls-tree", "-r", "--name-only", sha]).split())
    spec = ["-e", "."]
    meta = ""
    for f in ("setup.cfg", "setup.py", "pyproject.toml"):
        if f in files:
            meta += sh(["git", "-C", str(cache), "show", f"{sha}:{f}"])
    for key in ("test", "tests", "testing"):
        if re.search(rf"""(^|\s|["']){key}\s*(=|["']\s*:)""", meta, re.M) and "extras" in meta:
            spec = ["-e", f".[{key}]"]
            break
    for req in TEST_REQ_FILES:
        if req in files:
            spec += ["-r", f"/repo/{req}"]
            break
    return spec + ["pytest"] + extra


def build(tag: str, context: Path) -> None:
    proc = subprocess.run(["docker", "build", "--progress=plain", "-t", tag, str(context)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"docker build failed for {tag}:\n{proc.stderr[-3000:]}")


def lock_dependencies(base_image: str, repo: str, sha: str, date: str, spec: list[str],
                      tools_date: str = BUILD_TOOLS_DATE) -> str:
    """Resolve deps as of `date` in a throwaway image and return a frozen requirements.lock."""
    args = " ".join(spec)
    install = f"RUN uv pip install --exclude-newer {date} {build_tools(tools_date)} {args}"
    tag = f"g10-swe-explore/{sha[:12]}"
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "Dockerfile").write_text(dockerfile(base_image, repo, sha, install), encoding="utf-8")
        build(tag, Path(tmp))
    frozen = sh(["docker", "run", "--rm", "--network=none", tag, "uv", "pip", "freeze"])
    keep = [line for line in frozen.splitlines() if line.strip() and not line.startswith("-e") and "file:///repo" not in line
            and not line.startswith(("uv==", "pip=="))]
    subprocess.run(["docker", "rmi", "-f", tag], capture_output=True)
    return "\n".join(sorted(keep, key=str.lower)) + "\n"


def flips(env_dir: Path, env: dict, gold: str, runs: int = 2) -> tuple[list[str], list[str], dict]:
    befores, afters = [], []
    for _ in range(runs):
        b = verify.run_side(env_dir, env, None)
        a = verify.run_side(env_dir, env, gold)
        for side, name in ((b, "before"), (a, "after")):
            if "error" in side:
                raise SystemExit(f"{name} run failed: {side['error']}")
        befores.append(b["results"])
        afters.append(a["results"])
    names = set().union(*befores, *afters)
    passed_after = {t for t in names if all(r.get(t, False) for r in afters)}
    failed_before = {t for t in names if all(not r.get(t, False) for r in befores)}
    passed_before = {t for t in names if all(r.get(t, False) for r in befores)}
    f2p = sorted(passed_after & failed_before)
    p2p = sorted(passed_after & passed_before)
    flaky = sorted(names - set(f2p) - set(p2p) - {t for t in names if all(not r.get(t, False) for r in afters)})
    return f2p, p2p, {"flaky_dropped": flaky,
                      "fail_after": sorted(t for t in names if all(not r.get(t, False) for r in afters))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--python", help="Python version (default: by merge year, 3.8 / 3.9 / 3.10)")
    ap.add_argument("--deps", default="", help="extra pip requirements for the tests, space separated")
    ap.add_argument("--targets", default="", help="test files to run (default: .py test files in test.patch)")
    ap.add_argument("--licence", default="", help="SPDX id of the repo licence (default: from GitHub)")
    ap.add_argument("--build-tools-date", default=BUILD_TOOLS_DATE,
                    help="newest setuptools/wheel allowed for building the project (default %(default)s)")
    ap.add_argument("--allow-markers", action="store_true", help="build even if an AI-tool marker is found")
    ap.add_argument("--out-dir", type=Path, help="where to write the env folder (default: swe-envs/)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing env folder")
    args = ap.parse_args(argv)

    owner, name = args.repo.split("/")
    pr = gh_json(f"repos/{args.repo}/pulls/{args.pr}")
    if not pr.get("merged_at"):
        raise SystemExit("PR is not merged")
    issues = gh_graphql_issues(owner, name, args.pr)
    if not issues:
        raise SystemExit("PR closes no GitHub issue; we need a human issue for the problem statement")
    commits = gh_json(f"repos/{args.repo}/pulls/{args.pr}/commits")
    scan = "\n".join([pr.get("body") or "", *[c["commit"]["message"] for c in commits],
                      *[(i["title"] or "") + "\n" + (i["body"] or "") for i in issues]])
    hits = sorted({m.group(0).lower() for m in AI_MARKERS.finditer(scan)})
    if hits and not args.allow_markers:
        raise SystemExit(f"AI-tool markers found in the PR, commits or issue: {hits}")

    instance_id = f"{owner}__{name}-{args.pr}".lower()
    env_dir = (args.out_dir or HERE) / instance_id
    if env_dir.exists() and not args.force:
        raise SystemExit(f"{env_dir} exists (use --force)")

    cache = CACHE / f"{owner}__{name}"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        sh(["git", "clone", "--quiet", f"https://github.com/{args.repo}.git", str(cache)])
    sh(["git", "-C", str(cache), "fetch", "--quiet", "origin", f"pull/{args.pr}/head:refs/g10/pr{args.pr}"])
    head = pr["head"]["sha"]
    base = sh(["git", "-C", str(cache), "merge-base", pr["base"]["sha"], head]).strip()
    diff = sh(["git", "-C", str(cache), "diff", "--no-color", "--no-ext-diff", base, head])
    if "GIT binary patch" in diff or "Binary files" in diff:
        raise SystemExit("PR has binary changes")
    gold, test = verify.split_patch(diff)
    if not gold.strip() or not test.strip():
        raise SystemExit("PR needs both a source change and a test change")
    test_files = verify.patch_paths(test)
    lang = "go" if any(p.endswith(".go") for p in verify.patch_paths(gold)) else "python"
    if lang == "go":
        pkgs = sorted({"./" + (p.rsplit("/", 1)[0] if "/" in p else "") for p in test_files if p.endswith("_test.go")})
        targets = args.targets.split() or pkgs
    else:
        targets = args.targets.split() or [p for p in test_files if p.endswith(".py") and verify.is_test_path(p)
                                           and p.rsplit("/", 1)[-1] not in ("conftest.py", "__init__.py")]
    if not targets:
        raise SystemExit("no runnable test file in test.patch; give --targets")

    merged = pr["merged_at"][:10]
    licence = args.licence or ((gh_json(f"repos/{args.repo}").get("license") or {}).get("spdx_id") or "not stated")
    if licence not in import_pool.PERMISSIVE_SPDX:
        raise SystemExit(f"repo licence is {licence!r}; read the LICENSE file and pass --licence <SPDX> if it is "
                         "permissive")
    env_dir.mkdir(parents=True, exist_ok=True)
    if lang == "go":
        py = None
        base_image = f"{GO_IMAGE}@{image_digest(GO_IMAGE)}"
        lock = sh(["git", "-C", str(cache), "show", f"{base}:go.sum"]) if "go.sum" in sh(
            ["git", "-C", str(cache), "ls-tree", "--name-only", base]).split() else ""
        (env_dir / "requirements.lock").write_text(
            "# Go modules are pinned by go.mod/go.sum at base_commit; copy of go.sum below (empty: no deps).\n"
            + lock, encoding="utf-8")
        install = ("ENV GOFLAGS=-mod=readonly GOTOOLCHAIN=local GOCACHE=/tmp/gocache\n"
                   "RUN if [ -f go.mod ]; then go mod download; else go mod init "
                   f"github.com/{args.repo} && go mod tidy; fi\n"
                   "RUN chmod -R a+rwX /go")
        test_cmd = "go test -json -count=1 " + " ".join(targets)
    else:
        py = args.python or python_for(int(merged[:4]))
        base_image = f"python:{py}-slim@{image_digest(f'python:{py}-slim')}"
        lock = lock_dependencies(base_image, args.repo, base, merged, install_spec(cache, base, args.deps.split()),
                                args.build_tools_date)
        (env_dir / "requirements.lock").write_text(lock, encoding="utf-8")
        install = ("COPY requirements.lock /tmp/requirements.lock\n"
                   "RUN uv pip install --no-deps -r /tmp/requirements.lock \\\n"
                   f"    && uv pip install --no-deps --exclude-newer {merged} {build_tools(args.build_tools_date)} -e .")
        test_cmd = "python -m pytest -p no:cacheprovider -o addopts= -q " + " ".join(targets)
    (env_dir / "Dockerfile").write_text(dockerfile(base_image, args.repo, base, install, lang), encoding="utf-8")
    (env_dir / "gold.patch").write_text(gold, encoding="utf-8")
    (env_dir / "test.patch").write_text(test, encoding="utf-8")
    issue_md = []
    for i in issues:
        issue_md += [f"# {i['title']}", "",
                     f"Upstream issue: {i['url']} (opened by @{(i['author'] or {}).get('login', 'ghost')} "
                     f"on {i['createdAt'][:10]}). Text copied unchanged.", "", (i["body"] or "").strip(), ""]
    (env_dir / "issue.md").write_text("\n".join(issue_md), encoding="utf-8")

    env = {
        "instance_id": instance_id,
        "repo": args.repo,
        "licence": licence,
        "base_commit": base,
        "pr_head_commit": head,
        "merge_commit": pr.get("merge_commit_sha"),
        "pr_url": pr["html_url"],
        "issue_urls": [i["url"] for i in issues],
        "merged_at": pr["merged_at"],
        "provenance": {
            "problem_statement": "human: upstream GitHub issue text, unchanged (issue.md)",
            "patch": f"human: non-test files of upstream PR #{args.pr} by @{pr['user']['login']} (gold.patch)",
            "test_patch": f"human: test files of upstream PR #{args.pr} (test.patch)",
            "generator": "none",
            "ai_marker_scan": "markers found: " + ", ".join(hits) if hits else
                              "no AI-tool markers in the PR body, commits or issue",
        },
        "language": lang,
        "python": py,
        "base_image": base_image,
        "image": f"g10-swe/{instance_id}:v1",
        "dependencies_as_of": merged if lang == "python" else "go.sum at base_commit",
        "build_tools_as_of": args.build_tools_date if lang == "python" else None,
        "test_files": test_files,
        "test_cmd": test_cmd,
        "timeout_s": 300,
        "FAIL_TO_PASS": [],
        "PASS_TO_PASS": [],
        "quality_verdict": "unreviewed",  # set to keep / keep-flagged after a SWE-bench Verified style review
    }
    (env_dir / "env.json").write_text(json.dumps(env, indent=1) + "\n", encoding="utf-8")
    subprocess.run(["docker", "rmi", "-f", env["image"]], capture_output=True)
    verify.ensure_image(env_dir, env)
    f2p, p2p, notes = flips(env_dir, env, gold)
    if not f2p:
        raise SystemExit(f"no FAIL_TO_PASS test (fail_after={notes['fail_after'][:5]})")
    env.update(FAIL_TO_PASS=f2p, PASS_TO_PASS=p2p, build_notes=notes)
    (env_dir / "env.json").write_text(json.dumps(env, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"instance_id": instance_id, "f2p": len(f2p), "p2p": len(p2p),
                      "flaky_dropped": len(notes["flaky_dropped"]), "fail_after": len(notes["fail_after"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
