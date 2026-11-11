Write `transliterate_digits(s, target)`. Replace every Unicode decimal digit in `s` (any script: ASCII, Devanagari, Bengali, Tamil, Arabic-Indic, fullwidth and so on) by the digit with the same value in the `target` script, and leave every other character unchanged.

`target` is one of `"ascii"` (0-9), `"devanagari"` (U+0966 to U+096F), `"bengali"` (U+09E6 to U+09EF) or `"tamil"` (U+0BE6 to U+0BEF). Any other `target` raises `ValueError`, even when `s` has no digits. Characters that only look like digits but are not decimal digits (for example superscript `²` or `½`) stay unchanged.

Examples:
- `transliterate_digits('Room 101', 'devanagari')` returns `'Room १०१'`
- `transliterate_digits('৪২ items', 'ascii')` returns `'42 items'`
- `transliterate_digits('no digits', 'tamil')` returns `'no digits'`

Reply with the complete code in one ```python block. Use only the standard library.
