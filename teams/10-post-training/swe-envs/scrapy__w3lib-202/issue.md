# Function `convert_entity` does not catch `OverflowError` 

Upstream issue: https://github.com/scrapy/w3lib/issues/199 (opened by @ghost on 2022-10-31). Text copied unchanged.

Error:
```
OverflowError
Python int too large to convert to C int
```

`w3lib` version -> `2.0.1`
`Python` version -> `3.8.13`

<img width="1131" alt="Screenshot 2022-10-31 at 10 02 22" src="https://user-images.githubusercontent.com/107861298/198971171-1af35f01-42d2-413a-8c47-9d2c3dc6ece1.png">
