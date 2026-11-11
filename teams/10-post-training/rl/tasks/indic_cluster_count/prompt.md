Write `cluster_count(s)`: the number of user-perceived characters ("clusters") in `s`. Work on code points and use only the standard library.

A code point starts a new cluster unless it continues the previous one. The first code point always starts a cluster. A code point continues the previous cluster when any of these holds:
1. its Unicode general category starts with `M` (combining marks, vowel signs, anusvara, virama and so on);
2. it is ZERO WIDTH JOINER (U+200D) or ZERO WIDTH NON-JOINER (U+200C);
3. it is a letter (general category starts with `L`) and the previous code point is a virama, meaning `unicodedata.combining(previous) == 9`, or a ZWJ/ZWNJ that directly follows a virama. (So consonant + virama + consonant is one cluster, and so is consonant + virama + ZWJ + consonant. A space or digit after a virama still starts a new cluster.)

The empty string gives `0`. Spaces, digits and punctuation count like any other code point that starts a cluster.

Examples:
- `cluster_count('नमस्ते')` returns `3`
- `cluster_count('abc')` returns `3`
- `cluster_count('')` returns `0`

Reply with the complete code in one ```python block. Use only the standard library.
