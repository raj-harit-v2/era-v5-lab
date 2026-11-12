"""Direct entry point for teams/08-monitoring/alarms/test_alarms.py (mirrors tests/test_alarms.py)."""
import importlib.util
from pathlib import Path

_IMPL_PATH = Path(__file__).resolve().parent / "tests" / "test_alarms.py"
_SPEC = importlib.util.spec_from_file_location("_alarms_tests_impl", _IMPL_PATH)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

for _k, _v in vars(_MOD).items():
    if _k.startswith("test_"):
        globals()[_k] = _v
