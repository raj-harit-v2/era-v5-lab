Write `normalize_phone_in(s)`. It turns a text that holds an Indian mobile number into the form `"+91"` followed by 10 ASCII digits, or returns `None` when the text is not a valid number.

Steps:
1. Remove every space (U+0020 only), hyphen `-` and parenthesis `(` `)`. Other whitespace is not removed.
2. Replace every Unicode decimal digit (any script, for example Devanagari or Arabic-Indic) with its ASCII digit. After this, the text may contain only ASCII digits, plus a single `+` as its very first character. If anything else is left (a letter, another symbol, a `+` anywhere else, whitespace other than the removed spaces), return `None`.
3. Take off the country or trunk prefix. Exactly one of these forms is accepted, checked on the cleaned text `t`:
   - `t` starts with `+`: it must be `+91` followed by exactly 10 digits;
   - `t` starts with `0091` and has 14 characters;
   - `t` starts with `91` and has 12 characters;
   - `t` starts with `0` and has 11 characters;
   - `t` has exactly 10 characters.
   Otherwise return `None`.
4. The 10 remaining digits must start with 6, 7, 8 or 9. Otherwise return `None`.

Return `"+91" + digits`.

Examples:
- `normalize_phone_in('98765 43210')` returns `'+919876543210'`
- `normalize_phone_in('+91-87654-32109')` returns `'+918765432109'`
- `normalize_phone_in('12345 67890')` returns `None`

Reply with the complete code in one ```python block. Use only the standard library.
