# removing a nested table results in generation of an additional table header

Upstream issue: https://github.com/python-poetry/tomlkit/issues/217 (opened by @decathorpe on 2022-07-29). Text copied unchanged.

Removing a nested table will result in additional, unnecessary table header that was not present in the original TOML.

There's also a trailing newline where there was none previously, but that's probably OK, given that the number of empty lines actually stays the same.

```python
import tomlkit

test = """\
[hello.one]
number = 1

[hello.two]
number = 2
"""

data = tomlkit.parse(test)
del data["hello"]["two"]

expected = """\
[hello.one]
number = 1

"""

actual = """\
[hello]
[hello.one]
number = 1

"""

tomlkit.dumps(data) == expected  # False
tomlkit.dumps(data) == actual  # True
```

---

Tested with tomlkit 0.11.1.
