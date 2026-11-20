You have a shell in /repo, a checkout of a Python project at the commit just before an upstream fix. There is no network. The tests that cover the issue below are already in the checkout.

Reply with exactly one shell command in one ```bash block: a pytest command that runs the whole test file covering the issue. Use only `pytest` or `python -m pytest`, a file path from the list below, and optionally -q, -v, -s or --tb=<style>. One line: no pipes, `cd`, quotes or environment variables. Do not explain.

Issue (upstream text, unchanged):

# IPv4 validator accepts any number of 0's in a segment

Upstream issue: https://github.com/python-validators/validators/issues/190 (opened by @tomguyatt on 2021-04-29). Text copied unchanged.

**Version: 0.18.2**

The `ipv4` validator only tests that:

- The number of dot-delimited groups is 4
- Each group represents a 'digit'
- The value of each digit is `>= 0` & `< 256`

Therefore a segment can contain as many zeroes as you like, and it'll still validate:

```python
In [18]: validators.ipv4("00000.00000.00000.00000")
Out[18]: True
```

```python
In [19]: validators.ipv4("192.168.123.000000000")
Out[19]: True
```

Test files in the repository:

tests/__init__.py
tests/i18n/__init__.py
tests/i18n/test_es.py
tests/i18n/test_fi.py
tests/test_between.py
tests/test_btc_address.py
tests/test_card.py
tests/test_domain.py
tests/test_email.py
tests/test_extremes.py
tests/test_iban.py
tests/test_ipv4.py
tests/test_ipv4_cidr.py
tests/test_ipv6.py
tests/test_ipv6_cidr.py
tests/test_length.py
tests/test_mac_address.py
tests/test_md5.py
tests/test_sha1.py
tests/test_sha224.py
tests/test_sha256.py
tests/test_sha512.py
tests/test_slug.py
tests/test_url.py
tests/test_uuid.py
tests/test_validation_failure.py
