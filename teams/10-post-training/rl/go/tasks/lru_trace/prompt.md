# LRUTrace

Write `func LRUTrace(capacity int, ops []string) ([]string, error)` that runs a least-recently-used cache and returns what each `get` printed.

Each operation is one string with single spaces:

- `put KEY VALUE` stores the value (both are non-empty words without spaces). Storing a key that is already there replaces its value. The key becomes the most recently used. If the cache now holds more than `capacity` keys, remove the least recently used one.
- `get KEY` appends the value to the result, or `-` if the key is not in the cache. A hit makes the key the most recently used. A miss changes nothing.

Return the results of the `get` operations in order. If there are none, the result is an empty, non-nil slice (prints as `[]`).

Return a nil result and a non-nil error if `capacity` is 0 or negative, or if any operation is not exactly one of the two forms above (stop at the first bad one).

Examples:

- `LRUTrace(2, []string{"put a 1","put b 2","get a","put c 3","get b"})` returns `[1 -]`, because `b` was the least recently used when `c` came in.
- `LRUTrace(1, []string{"get a"})` returns `[-]`

Write one Go file: `package main`, standard library only. Do not define `main` or `init`. Put your answer in one ```go block.
