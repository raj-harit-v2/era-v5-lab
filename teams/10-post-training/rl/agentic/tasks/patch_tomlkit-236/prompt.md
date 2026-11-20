You have a checkout of a Python project at the commit just before an upstream fix. Reply with exactly one unified diff in one ```diff block that fixes the issue below. Do not edit test files. Do not explain.

Issue (upstream text, unchanged):

# Cannot dump nested arrays of tables

Upstream issue: https://github.com/python-poetry/tomlkit/issues/232 (opened by @Aloxaf on 2022-09-08). Text copied unchanged.

```python
In [12]: tomlkit.dumps({'a': [[ {'b': 1} ]]})
Out[12]: 'a = [b = 1\n]\n'

In [13]: tomlkit.__version__
Out[13]: '0.11.4'
```
