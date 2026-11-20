# camelToSnake

Write a function `camelToSnake(s)` that converts a camelCase or PascalCase string to snake_case.

**Conversion rule**: for each character in the string, if it is an uppercase ASCII letter (A–Z), prepend an underscore `_` and lowercase it. Then, if the **first character of the input** was an uppercase letter, remove the one leading underscore that was inserted for it.

```
camelToSnake("helloWorld")   // "hello_world"
camelToSnake("parseHTTP")    // "parse_h_t_t_p"
camelToSnake("PascalCase")   // "pascal_case"
```

**Constraints**:
- Throw `TypeError` if `s` is not a string.
- Throw `RangeError` if `s` is an empty string.
- Existing underscores, digits, and punctuation pass through unchanged.
- Only ASCII uppercase letters (A–Z) trigger insertion of `_`.
- A leading underscore that was already present in the input is preserved; only the underscore inserted for an uppercase first character is removed.
