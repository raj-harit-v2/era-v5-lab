# `uniqueItems` check only validates the first two entries for types with a `__len__` implementation 

Upstream issue: https://github.com/python-jsonschema/jsonschema/issues/866 (opened by @omaskery on 2021-10-25). Text copied unchanged.

After updating to a newer version of `jsonschema`, we now find that it does not notice violations of the `uniqueItems` constraint on lists.

By stepping through the code, I think I've found the issue in this code (originally introduced in [this commit][issue-commit] in [this PR][issue-pr], but now found [here][current-location]):

```python
        sort = sorted(unbool(i) for i in container)
        sliced = itertools.islice(sort, 1, None)

        for i, j in zip(sort, sliced):
            return not _sequence_equal(i, j)
```

Notice that the for loop will always return on the first iteration, without examining subsequent values.

This code looks like it's supposed to be seeing if any two successive elements is the same, but with the return statement it would only detect unique constraint violations between the first two elements.

I think this bug has escaped notice so far for two reasons:
* I believe that all of the unit tests for this code only test unique constraint violations in the first two elements
* This issue only presents if the _elements_ of the container have a `__len__` implementation. If a `TypeError` or `NotImplementedError` is raised then the "slow, brute force" path runs - and it does not have the same bug.

I wonder if this code is instead supposed to be:

```diff
         sort = sorted(unbool(i) for i in container)
         sliced = itertools.islice(sort, 1, None)
 
         for i, j in zip(sort, sliced):
-            return not _sequence_equal(i, j)
+            if _sequence_equal(i, j):
+                return False
```

---

For what it's worth, here's some noddy test code I put together to explore the issue:

```python
def test(container):
    print(f"uniq({container}) = {uniq(container)}")


TEST_CASES = [
    [],
    [1],
    [1, 2],
    [1, 2, 3, 4, 5],
    [1, 2, 3, 3, 5],
    [1, 1, 3, 4, 5],

    ["a"],
    ["a", "b"],
    ["a", "b", "c", "d", "e"],
    ["a", "b", "c", "c", "e"],
    ["a", "a", "c", "d", "e"],
]


for test_case in TEST_CASES:
    test(test_case)
```

And here is the output I got:

```
uniq([]) = True
uniq([1]) = True
uniq([1, 2]) = True
uniq([1, 2, 3, 4, 5]) = True
uniq([1, 2, 3, 3, 5]) = False
uniq([1, 1, 3, 4, 5]) = False
uniq(['a']) = True
uniq(['a', 'b']) = True
uniq(['a', 'b', 'c', 'd', 'e']) = True
uniq(['a', 'b', 'c', 'c', 'e']) = True
uniq(['a', 'a', 'c', 'd', 'e']) = False
```

[issue-commit]: https://github.com/Julian/jsonschema/commit/bd54c5cf5b1d39b34ad3ef6927b9db1198dce124
[issue-line]: https://github.com/Julian/jsonschema/commit/bd54c5cf5b1d39b34ad3ef6927b9db1198dce124#diff-421ec3d9b287f996ad5b6f29ba5c5e77873b0632d825c1f4d21630ace5cdd0e4R228
[issue-pr]: https://github.com/Julian/jsonschema/issues/686
[current-location]: https://github.com/Julian/jsonschema/blob/main/jsonschema/_utils.py#L180-L184
