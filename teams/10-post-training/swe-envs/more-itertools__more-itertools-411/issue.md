# Inconsistent return type for distinct_permutations

Upstream issue: https://github.com/more-itertools/more-itertools/issues/410 (opened by @ilai-deutel on 2020-03-28). Text copied unchanged.

Before `r` was added to `distinct_permutations`, the function yielded tuples, like `permutations`:

```python
>>> list(distinct_permutations([1, 0, 1]))
[(1, 0, 1), (0, 1, 1), (1, 1, 0)]
>>> list(distinct_permutations([1]))
[(1,)]
```

With `r`, the function yields lists in certain cases, tuples in others:

```python
>>> list(distinct_permutations([1, 0, 1], r=1))
[(0,), (1,)]
>>> list(distinct_permutations([1, 0, 1], r=2))
[(0, 1), (1, 0), (1, 1)]
>>> list(distinct_permutations([1], r=1))
[[1]]
```

I think that having a special case when `r == 1` and  `item_count == 1` would solve the issue.
