"""Build JS/TS task folders from an Exercism track clone (harness code; the only text written here is the fixed
output-format header of each prompt).

    python rl/jsts/build_tasks.py --track javascript --clone <clone of exercism/javascript> --slug two-fer
    python rl/jsts/build_tasks.py --track typescript --clone <clone of exercism/typescript> --pick 4 --seed 17

The clone may be blobless (`git clone --filter=blob:none --no-checkout`): files are read with `git show HEAD:path`.
--pick takes the first N of a seeded shuffle of the exercises whose proof file was first added on or before 2022-12-31, with
one solution file, one spec file, at most 30 tests and no import of fs, child_process or the network.
A task folder: task.json, prompt.md (header + upstream instructions + upstream stub), stub/<solution file>,
hidden/<spec file> (xtest/xit/xdescribe enabled), hidden/<reference file> (the upstream proof solution).
The expected test count is measured by running the reference in the sandbox image.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jsts_verifier as jv  # noqa: E402

TRACKS = {"javascript": ("js", "https://github.com/exercism/javascript"),
          "typescript": ("ts", "https://github.com/exercism/typescript")}
HEADER = """Write a solution module for the exercise below. Reply with exactly one fenced {fence} code block holding \
the complete contents of `{solution}`: keep the names and the export style of the starting file at the end of this \
message, and use no packages. Do not explain.
"""


def git(clone: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True, check=True).stdout


def show(clone: Path, path: str) -> str | None:
    r = subprocess.run(["git", "-C", str(clone), "show", f"HEAD:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def eligible(clone: Path, lang: str, slug: str) -> bool:
    """One exercise passes the filters in the module docstring (reads a few blobs, so it is slow on a blobless clone)."""
    added = git(clone, "log", "--diff-filter=A", "--format=%cs", "--",
                f"exercises/practice/{slug}/.meta/proof.ci.{lang}").split()
    if not added or added[-1] > "2022-12-31":
        return False
    cfg = json.loads(show(clone, f"exercises/practice/{slug}/.meta/config.json") or "{}")
    files = cfg.get("files", {})
    if len(files.get("solution", [])) != 1 or len(files.get("test", [])) != 1 or len(files.get("example", [])) != 1:
        return False
    spec = show(clone, f"exercises/practice/{slug}/{files['test'][0]}") or ""
    ref = show(clone, f"exercises/practice/{slug}/{files['example'][0]}") or ""
    if len(re.findall(r"\b(?:x?test|x?it)\(", spec)) > 30 or re.search(r"\b(fs|child_process|http|net)\b['\"]", spec + ref):
        return False
    return True


def pick(clone: Path, lang: str, n: int, seed: int) -> list[str]:
    """The first n eligible exercises of a seeded shuffle of all exercises that have a reference file."""
    paths = git(clone, "ls-tree", "-r", "--name-only", "HEAD", "exercises/practice").split()
    slugs = sorted({p.split("/")[2] for p in paths if p.endswith(f".meta/proof.ci.{lang}")})
    random.Random(seed).shuffle(slugs)
    out = []
    for s in slugs:
        if eligible(clone, lang, s):
            out.append(s)
            if len(out) == n:
                break
    return out


def enable_tests(spec: str) -> str:
    """Switch xtest/xit/xdescribe calls on, and keep the @jest/globals import list valid (no duplicates, no x names)."""
    spec = re.sub(r"\bx(test|it|describe)\b(?=\s*[(.])", r"\1", spec)

    def fix(m: re.Match) -> str:
        names = [n.strip() for n in m.group(1).split(",") if n.strip() and not re.fullmatch(r"x(test|it|describe)", n.strip())]
        for used in ("test", "it", "describe"):
            if re.search(rf"\b{used}\s*[(.]", spec) and used not in names:
                names.append(used)
        return "import { " + ", ".join(dict.fromkeys(names)) + " } from '@jest/globals'"

    return re.sub(r"import\s*\{([^}]*)\}\s*from\s*['\"]@jest/globals['\"]", fix, spec)


def build(clone: Path, track: str, slug: str) -> dict:
    lang, repo = TRACKS[track]
    base = f"exercises/practice/{slug}"
    cfg = json.loads(show(clone, f"{base}/.meta/config.json"))
    sol, spec_name, ex = cfg["files"]["solution"][0], cfg["files"]["test"][0], cfg["files"]["example"][0]
    stub, spec, ref = show(clone, f"{base}/{sol}"), show(clone, f"{base}/{spec_name}"), show(clone, f"{base}/{ex}")
    docs = [show(clone, f"{base}/.docs/{n}") for n in ("introduction.md", "instructions.md", "instructions.append.md")]
    statement = "\n\n".join(d.strip() for d in docs if d)
    spec = enable_tests(spec)
    first_added = git(clone, "log", "--diff-filter=A", "--format=%cs", "--", f"{base}/.meta/proof.ci.{lang}").split()[-1]
    head = git(clone, "rev-parse", "HEAD").strip()
    task_id = slug
    out = jv.TASKS / lang / task_id
    (out / "hidden").mkdir(parents=True, exist_ok=True)
    (out / "stub").mkdir(exist_ok=True)
    fence = {"js": "javascript", "ts": "typescript"}[lang]
    meta = {"id": task_id, "language": lang, "slug": slug, "solution_file": sol, "spec_file": spec_name,
            "reference_file": ex.split("/")[-1], "expected_tests": 0,
            "source": f"exercism/{track} exercises/practice/{slug} at commit {head}", "source_url": repo,
            "licence": "MIT", "first_added": first_added,
            "authors": cfg.get("authors", []),
            "generator": "none (human-written: statement, stub, reference solution and tests are upstream files)"}
    (out / "hidden" / spec_name).write_text(spec, encoding="utf-8")
    (out / "hidden" / meta["reference_file"]).write_text(ref, encoding="utf-8")
    (out / "stub" / sol).write_text(stub, encoding="utf-8")
    (out / "prompt.md").write_text(HEADER.format(fence=fence, solution=sol) + "\n" + statement + "\n\nStarting file `"
                                   + sol + "`:\n\n```" + fence + "\n" + stub.rstrip() + "\n```\n", encoding="utf-8")
    (out / "task.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    good, _ = jv.known_outputs(out)
    side = jv.run_candidate(out, meta, jv.extract_code(good, lang)[0])
    assert "passed" in side and not side["failed"] and side["passed"] > 0, (slug, side)
    meta["expected_tests"] = side["passed"]
    (out / "task.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"built": f"{lang}/{task_id}", "tests": side["passed"]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--track", required=True, choices=TRACKS)
    ap.add_argument("--clone", required=True, type=Path)
    ap.add_argument("--slug", action="append")
    ap.add_argument("--pick", type=int)
    ap.add_argument("--seed", type=int, default=17)
    a = ap.parse_args()
    lang = TRACKS[a.track][0]
    slugs = a.slug or pick(a.clone, lang, a.pick, a.seed)
    for s in slugs:
        print(json.dumps(build(a.clone, a.track, s)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
