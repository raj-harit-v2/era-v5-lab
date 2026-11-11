# Cannot compare with list or string

Upstream issue: https://github.com/python-semver/python-semver/issues/244 (opened by @tomschr on 2020-04-26). Text copied unchanged.

# Situation

A `VersionInfo` instance has the ability to compare with another `VersionInfo` instance, a tuple, or a dict :

```python
>>> import semver
>>> v1 = semver.VersionInfo.parse("1.2.3")
>>> v1 < (1, 2, 4)
True
```

However, it is not possible for a list or a string:

```python
>>> v1 < [1, 2, 4]
Traceback (most recent call last):
...
TypeError: other type <class 'list'> must be in (<class 'semver.VersionInfo'>, <class 'dict'>, <class 'tuple'>)
>>> v1 < "1.2.4"
Traceback (most recent call last):
...
TypeError: other type <class 'str'> must be in (<class 'semver.VersionInfo'>, <class 'dict'>, <class 'tuple'>)
```

# Situation

After analyzing the situation above, I found the `comparator` which allows `VersionInfo` instance, a tuple, or a dict :


```python
def comparator(operator):
    """Wrap a VersionInfo binary op method in a type-check."""

    @wraps(operator)
    def wrapper(self, other):
        comparable_types = (VersionInfo, dict, tuple)  # bug!
        if not isinstance(other, comparable_types):
            raise TypeError(
                "other type %r must be in %r" % (type(other), comparable_types)
            )
        return operator(self, other)

    return wrapper
```

We should add a list and a string to the allowed types. 

Would that be ok @python-semver/reviewers?
