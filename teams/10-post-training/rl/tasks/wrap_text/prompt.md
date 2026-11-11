Write `wrap_text(text, width)`. Split `text` into words on whitespace (`str.split()`), then pack the words greedily into lines of at most `width` code points, with a single space between words on a line. Return the list of lines (no trailing spaces). A text with no words gives `[]`. Raise `ValueError` if `width < 1`.

A word longer than `width` is first cut into pieces of exactly `width` code points (the last piece may be shorter). Every piece except the last goes on a line of its own; if a line is open, close it first. The last piece is then placed like an ordinary word, so later words may follow it on the same line.

Examples:
- `wrap_text('the quick brown fox', 10)` returns `['the quick', 'brown fox']`
- `wrap_text('abcdefghij kl', 4)` returns `['abcd', 'efgh', 'ij', 'kl']`
- `wrap_text('   ', 5)` returns `[]`

Reply with the complete code in one ```python block. Use only the standard library.
