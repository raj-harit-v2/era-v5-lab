# ParseKV

Write `func ParseKV(line string) (map[string]string, error)` that parses a log-style line such as `user=ana msg="hello world"`.

Rules:

- Pairs are separated by one or more spaces. Spaces at the start and the end are ignored.
- A key starts with an ASCII letter or `_` and continues with ASCII letters, digits or `_`. It is followed directly by `=`.
- A value is either bare or quoted.
  - A bare value runs up to the next space or the end. It may be empty (`k=`). It must not contain `"` or `=`.
  - A quoted value starts and ends with `"`. Inside, `\"` means a quote and `\\` means a backslash. Any other backslash sequence is an error. After the closing quote there must be a space or the end of the line.
- If a key appears twice, the last value wins.
- An empty line, or a line of spaces, gives an empty, non-nil map.

Return a non-nil error (and a nil map) for anything else: a pair without `=`, a bad key, an unterminated quote, a bad escape, or text glued to a closing quote.

Examples:

- `ParseKV("a=1 b=two")` returns `{"a": "1", "b": "two"}`
- `ParseKV("msg=\"hello world\" n=3")` returns `{"msg": "hello world", "n": "3"}`
- `ParseKV("x=\"open")` returns an error

Write one Go file: `package main`, standard library only. Do not define `main` or `init`. Put your answer in one ```go block.
