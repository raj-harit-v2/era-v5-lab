You have a shell in /repo, a checkout of a Python project at the commit just before an upstream fix. There is no network. The tests that cover the issue below are already in the checkout.

Reply with exactly one shell command in one ```bash block: a pytest command that runs the whole test file covering the issue. Use only `pytest` or `python -m pytest`, a file path from the list below, and optionally -q, -v, -s or --tb=<style>. One line: no pipes, `cd`, quotes or environment variables. Do not explain.

Issue (upstream text, unchanged):

# daterange(start, stop, inclusive=True) returns an infinite iterator when start is same as stop

Upstream issue: https://github.com/mahmoud/boltons/issues/297 (opened by @0x1997 on 2021-12-15). Text copied unchanged.

expected to get `start` exactly once.

Test files in the repository:

tests/.coveragerc
tests/__init__.py
tests/conftest.py
tests/jsonl_test_data.txt
tests/newlines_test_data.txt
tests/test_cacheutils.py
tests/test_debugutils_trace.py
tests/test_dictutils.py
tests/test_ecoutils.py
tests/test_fileutils.py
tests/test_formatutils.py
tests/test_funcutils.py
tests/test_funcutils_fb.py
tests/test_funcutils_fb_py3.py
tests/test_funcutils_fb_py37.py
tests/test_gcutils.py
tests/test_ioutils.py
tests/test_iterutils.py
tests/test_jsonutils.py
tests/test_listutils.py
tests/test_mathutils.py
tests/test_namedutils.py
tests/test_queueutils.py
tests/test_setutils.py
tests/test_socketutils.py
tests/test_statsutils.py
tests/test_statsutils_histogram.py
tests/test_strutils.py
tests/test_tableutils.py
tests/test_tbutils.py
tests/test_tbutils_parsed_exc.py
tests/test_timeutils.py
tests/test_typeutils.py
tests/test_urlutils.py
