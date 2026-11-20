You have a shell in /repo, a checkout of a Python project at the commit just before an upstream fix. There is no network. The tests that cover the issue below are already in the checkout.

Reply with exactly one shell command in one ```bash block: a pytest command that runs the whole test file covering the issue. Use only `pytest` or `python -m pytest`, a file path from the list below, and optionally -q, -v, -s or --tb=<style>. One line: no pipes, `cd`, quotes or environment variables. Do not explain.

Issue (upstream text, unchanged):

# humanize.intcomma(num, ndigits=0) does not behave as expected

Upstream issue: https://github.com/python-humanize/humanize/issues/24 (opened by @CoinSearchr on 2022-06-20). Text copied unchanged.

### What did you do?
Run a call like `humanize.intcomma(12345.111, ndigits=0)`.

### What did you expect to happen?
I expected the return value to be `"12,345"`.

If ndigits=0, I would expect there to be no digits after the decimal place (i.e., 0 decimal digits).

### What actually happened?
 The return value is `"12,345.111"`.

### Alternative Solution
If it is decided that changing this behavior is completely inappropriate, then it is critical that the documentation be updated to explain:
* ndigits must be >0
* If **ndigits=0** or ndigits=None, then all digits are kept.

### What versions are you using?
* OS: Ubuntu
* Python: 3.9
* Humanize: 4.1.0

Test files in the repository:

tests/__init__.py
tests/test_filesize.py
tests/test_i18n.py
tests/test_number.py
tests/test_time.py
