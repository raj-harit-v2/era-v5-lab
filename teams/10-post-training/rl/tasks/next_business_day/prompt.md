Write `next_business_day(day, holidays)`. `day` is a string `YYYY-MM-DD` (exactly four digits, a dash, two digits, a dash, two digits, ASCII only) and `holidays` is a list of strings in the same format. Return, in the same format, the first date strictly after `day` that is not a Saturday, not a Sunday and not in `holidays`.

Raise `ValueError` if `day` or any holiday is not in that format or is not a real calendar date (for example `2023-02-29`), and also if no such business day exists up to and including `9999-12-31`. Use the standard library.

Examples:
- `next_business_day('2024-03-13', [])` returns `'2024-03-14'`
- `next_business_day('2024-03-15', [])` returns `'2024-03-18'`
- `next_business_day('2024-03-13', ['2024-03-14'])` returns `'2024-03-15'`

Reply with the complete code in one ```python block. Use only the standard library.
