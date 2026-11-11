Write `session_split(timestamps, idle)`. `timestamps` is a list of integers (seconds) in any order, duplicates allowed. Sort them, then cut a new session whenever the gap to the previous timestamp is strictly greater than `idle`.

Return a list with one entry `[first, last, count]` per session, in time order (`count` includes duplicates). An empty list gives `[]`. Raise `ValueError` if `idle` is negative.

Examples:
- `session_split([10, 20, 100, 105], 30)` returns `[[10, 20, 2], [100, 105, 2]]`
- `session_split([5, 5, 5], 0)` returns `[[5, 5, 3]]`
- `session_split([], 10)` returns `[]`

Reply with the complete code in one ```python block. Use only the standard library.
