# ExpandRLE

Write `func ExpandRLE(s string, maxLen int) (string, error)` that expands run-length text such as `3a2b` into `aaabb`.

- The text is a list of groups. Each group is a count (one or more ASCII digits) followed by exactly one byte that is **not** an ASCII digit. The count says how many times to repeat that byte.
- A count must be at least 1 and must not start with `0`.
- The empty string expands to the empty string.
- If the result would be longer than `maxLen` bytes, return an error. Check the limit **before** building the text, so `ExpandRLE("2000000000x", 10)` returns an error at once and never allocates that much. A count too large for an `int` is also an error.
- A count with no byte after it (`3a2`), a group without a count (`a`), and a zero or zero-led count (`0a`, `03a`) are errors.
- On an error, return `""` and a non-nil error.

Examples:

- `ExpandRLE("3a2b", 100)` returns `"aaabb", nil`
- `ExpandRLE("12x", 11)` returns an error

Write one Go file: `package main`, standard library only. Do not define `main` or `init`. Put your answer in one ```go block.
