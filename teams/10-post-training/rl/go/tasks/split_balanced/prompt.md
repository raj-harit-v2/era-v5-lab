# SplitBalanced

Write `func SplitBalanced(xs []int, parts int) ([][]int, error)` that splits `xs` into exactly `parts` consecutive chunks.

- Keep the order of the elements. Every element is in exactly one chunk.
- The chunk sizes differ by at most 1, and the larger chunks come first.
- If `parts` is larger than `len(xs)`, the last chunks are empty. An empty chunk is an empty non-nil slice, so it prints as `[]`, never `null`.
- If `parts` is 0 or negative, return a nil result and a non-nil error.

Examples:

- `SplitBalanced([]int{1,2,3,4,5}, 2)` returns `[[1 2 3] [4 5]], nil`
- `SplitBalanced([]int{1,2,3}, 5)` returns `[[1] [2] [3] [] []], nil`
- `SplitBalanced([]int{1,2}, 0)` returns an error

Write one Go file: `package main`, standard library only. Do not define `main` or `init`. Put your answer in one ```go block.
