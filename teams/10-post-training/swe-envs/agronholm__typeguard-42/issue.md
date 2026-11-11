# typing.* types do not have __name__ and they error when generating messages.

Upstream issue: https://github.com/agronholm/typeguard/issues/41 (opened by @dalejung on 2018-08-10). Text copied unchanged.

```
        T = TypeVar('T', int, Collection)
        def foo(a: T, b: T):
            assert check_argument_types()

        with pytest.raises(TypeError):
            foo('aa', 'bb')
```

Shouldn't fail but does since `Collection.__name__` does not exist.
