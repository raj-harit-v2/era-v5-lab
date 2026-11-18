# MergeIntervals

Write `func MergeIntervals(iv [][]int) ([][]int, error)`. Each interval is `[lo, hi]` and includes both ends.

- Merge intervals that overlap **or touch**. `[1,3]` and `[4,6]` touch, because 3 and 4 are neighbours, so they become `[1,6]`. `[1,3]` and `[5,6]` stay apart.
- Return the merged intervals sorted by `lo`. Do not change the input slice.
- An empty input gives an empty, non-nil result (prints as `[]`).
- If any interval does not have exactly two numbers, or has `lo > hi`, return a nil result and a non-nil error.

Examples:

- `MergeIntervals([][]int{{1,3},{2,6},{8,10}})` returns `[[1 6] [8 10]], nil`
- `MergeIntervals([][]int{{1,3},{4,6}})` returns `[[1 6]], nil`
- `MergeIntervals([][]int{{5,1}})` returns an error

Write one Go file: `package main`, standard library only. Do not define `main` or `init`. Put your answer in one ```go block.
