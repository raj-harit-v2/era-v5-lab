# Option.is_bool_flag is set to True even if the option is not a flag

Upstream issue: https://github.com/pallets/click/issues/1925 (opened by @janluke on 2021-05-21). Text copied unchanged.

This is relevant only for Click 8.0.1, since the following line was introduced in PR https://github.com/pallets/click/pull/1913:

https://github.com/pallets/click/blob/af0af571cbbd921d3974a0ff9cf58a4b26bb852b/src/click/core.py#L2531

The solution is as easy as:

```python
self.is_bool_flag = self.is_flag and isinstance(self.type, types.BoolParamType)
```
Available to open a PR.

## Demonstration code
```python
import click

@click.command()
@click.option('--switch', type=bool)
def f(switch):
    print(switch)


if __name__ == '__main__':
    assert not f.params[0].is_flag
    assert f.params[0].is_bool_flag
    f('--switch'.split())
```
```
Error: Option '--switch' requires an argument.
```
