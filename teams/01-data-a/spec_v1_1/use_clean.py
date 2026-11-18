"""Run a spec v1 tool, unchanged, on spec_v1_1/clean.py.

    python3 -I teams/01-data-a/spec_v1_1/use_clean.py <tool.py> [the tool's arguments ...]

The spec v1 tools (spec_v1/run_clean.py, spec_v1/run_tokenizer_sample.py, spec_v1/validate/make_harm_tests.py)
each `import clean` from spec_v1/. This loads spec_v1_1/clean.py as the module `clean` first, so their import
gets it, then runs the tool as its own script.
"""
import importlib.util
import runpy
import sys
from pathlib import Path

CLEAN = Path(__file__).resolve().parent / "clean.py"


def load_clean():
    spec = importlib.util.spec_from_file_location("clean", CLEAN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["clean"] = module
    spec.loader.exec_module(module)
    return module


def main(argv):
    if not argv or not argv[0].endswith(".py"):
        sys.exit("usage: use_clean.py <tool.py> [the tool's arguments ...]")
    tool = Path(argv[0]).resolve()
    if not tool.is_file():
        sys.exit(f"no such tool: {argv[0]}")
    load_clean()
    sys.argv = [str(tool), *argv[1:]]
    runpy.run_path(str(tool), run_name="__main__")


if __name__ == "__main__":
    main(sys.argv[1:])
