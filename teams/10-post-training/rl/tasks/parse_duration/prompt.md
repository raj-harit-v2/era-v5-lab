Write `parse_duration(s)`: convert a duration text to a whole number of seconds.

Format: one to four parts, each an unsigned ASCII integer immediately followed by a unit: `d` (86400 s), `h` (3600 s), `m` (60 s) or `s` (1 s). Units are case-insensitive. Parts must appear in the order d, h, m, s and each unit may appear at most once. Spaces or tabs are allowed between parts and around the whole text, but not between a number and its unit.

Raise `ValueError` for anything else: an empty or blank text, a missing or unknown unit, a repeated or out-of-order unit, a sign, a decimal point, a non-ASCII digit.

Examples:
- `parse_duration('1h30m')` returns `5400`
- `parse_duration('90s')` returns `90`
- `parse_duration('2d 3h 4m 5s')` returns `183845`

Reply with the complete code in one ```python block. Use only the standard library.
