# intword with negative numbers

Upstream issue: https://github.com/python-humanize/humanize/issues/12 (opened by @maxrioux100 on 2022-05-02). Text copied unchanged.

### What did you do?

```python
import humanize
print(humanize.intword(-1000000000))
```

### What did you expect to happen?

```
-1.0 billion
```

### What actually happened?

```
-1000000000
```

### What versions are you using?

* OS: Windows 10
* Python: 3.10.4
* Humanize: 3.14
