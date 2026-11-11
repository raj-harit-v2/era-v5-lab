# Tomlkit 0.11.2 issue parsing array with comment when later subsections are present

Upstream issue: https://github.com/python-poetry/tomlkit/issues/222 (opened by @airstandley on 2022-08-09). Text copied unchanged.

Poetry recently started failing to parse one of our project's pyproject.toml files, and we tracked it down to the bump from tomlkit 0.11.1 to 0.11.2.

Specifically 0.11.1 succeed in parsing the file while 0.11.2 fails causes poetry to throw the parsing error
`[packages.0] None is not of type 'object'`. 

Investigating further showed that the issue was that commented lines in the array were being parsed as array items.

It took quite a big of testing to figure out exactly what scenario caused the array with comments to be parsed incorrectly. Specifically it's when there is another subsection later in the file.

Reproduced with the following toy example:
```
from tomlkit import parse
content = """
[section.subsection]
my_array = [
   # This is a comment
   { item = 1 }
]

[section.othersubsection]
key = "value"
"""
parse(content)
```

`{'section': {'subsection': {'my_array': [None, {'item': 1}]}, 'othersubsection': {'key': 'value'}}}`

Note that order matters, the following parses correctly
```
content ="""
[section.subsection]
key = "value"

[section.othersubsection]
array = [
  # Comment
  { item = 1 }
]
 """
 ```
