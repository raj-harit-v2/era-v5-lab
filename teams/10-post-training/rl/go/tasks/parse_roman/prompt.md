# ParseRoman

Write `func ParseRoman(s string) (int, error)` that converts a Roman numeral to an integer.

- Only the standard written form of a number from 1 to 3999 is valid: `IV` is 4, but `IIII` is an error. `IX` is 9, `XC` is 90, `CM` is 900, and so on.
- Capital letters only. `iv` is an error.
- The empty string, other characters, spaces, and any non-standard order or repeat (`VX`, `IL`, `MMMM`, `VV`, `IIX`) are errors.
- On an error, return 0 and a non-nil error.

Examples:

- `ParseRoman("XIV")` returns `14, nil`
- `ParseRoman("MCMXCIV")` returns `1994, nil`
- `ParseRoman("IC")` returns an error

Write one Go file: `package main`, standard library only. Do not define `main` or `init`. Put your answer in one ```go block.
