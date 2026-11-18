# ParseSize

Write `func ParseSize(s string) (int64, error)` that turns a size such as `"1.5KiB"` into a number of bytes.

Format: optional white space, a non-negative number (digits with at most one `.`), optional white space, an optional unit, optional white space.

Units are not case-sensitive. No unit means bytes.

| Unit | Bytes |
|---|---|
| B | 1 |
| KB, MB, GB | 1000, 1000000, 1000000000 |
| KiB, MiB, GiB | 1024, 1048576, 1073741824 |

The result is rounded down to a whole number of bytes. Compute it exactly: do not lose precision with floating point.

Return a non-nil error (and 0) when the text has no number, has a second `.`, has an unknown unit or any other extra text, is negative, or does not fit in an `int64`.

Examples:

- `ParseSize("1KiB")` returns `1024, nil`
- `ParseSize("2.5 MB")` returns `2500000, nil`
- `ParseSize("abc")` returns an error

Write one Go file: `package main`, standard library only. Do not define `main` or `init`. Put your answer in one ```go block.
