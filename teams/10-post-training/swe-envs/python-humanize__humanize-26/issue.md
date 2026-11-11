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
