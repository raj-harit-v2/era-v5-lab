# TopWords

Write `func TopWords(text string, k int) []string` that returns the `k` most frequent words in `text`.

- A word is a run of ASCII letters, with optional single apostrophes **between** letters (`don't`, `o'clock`). Everything else separates words. A leading or trailing apostrophe is not part of the word (`'hi'` is `hi`), and two apostrophes in a row split the word.
- Compare in lower case, and return the words in lower case.
- Sort by count, highest first. Words with the same count are sorted alphabetically (byte order).
- If there are fewer than `k` different words, return all of them. If `k` is 0 or negative, or there are no words, return an empty, non-nil slice (prints as `[]`).

Examples:

- `TopWords("the cat and the hat", 2)` returns `[the and]`
- `TopWords("Don't stop, don't!", 5)` returns `[don't stop]`

Write one Go file: `package main`, standard library only. Do not define `main` or `init`. Put your answer in one ```go block.
