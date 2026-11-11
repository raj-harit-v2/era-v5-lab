# TypeError: argument of type 'StrictUndefined' is not iterable when callin `value in dict` with missing key

Upstream issue: https://github.com/pallets/jinja/issues/1198 (opened by @HumanUser on 2020-04-23). Text copied unchanged.

## Expected Behavior
raising of UndefinedError with text message ```'dict object' has no attribute 'missing_key'```

## Actual Behavior
TypeError with text ```argument of type 'StrictUndefined' is not iterable``` is raised

## Template Code
```jinja
{% if 'value' in data['missing_key'] %}{% endif %}
{{ 'value' in data['missing_key'] }}
```

## MCVE
```python
#!/usr/bin/env python3
import jinja2

def main():
    text = '''{{ 'value' in data['missing_key'] }}'''  # both fails
    text = '''{% if 'value' in data['missing_key'] %}{% endif %}'''

    environment = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
    )
    template = environment.from_string(text)
    template.render(data={})

if __name__ == '__main__':
    main()
```

## Full Traceback
```pytb
Traceback (most recent call last):
  File "./mcve.py", line 16, in <module>
    main()
  File "./mcve.py", line 12, in main
    template.render(data={})
  File "/usr/local/lib/python3.6/dist-packages/jinja2/environment.py", line 1090, in render
    self.environment.handle_exception()
  File "/usr/local/lib/python3.6/dist-packages/jinja2/environment.py", line 832, in handle_exception
    reraise(*rewrite_traceback_stack(source=source))
  File "/usr/local/lib/python3.6/dist-packages/jinja2/_compat.py", line 28, in reraise
    raise value.with_traceback(tb)
  File "<template>", line 1, in top-level template code
TypeError: argument of type 'StrictUndefined' is not iterable
```

## Your Environment
* Python version: 3.6.8 (default, Jan 14 2019, 11:02:34) [GCC 8.0.1 20180414 (experimental) [trunk revision 259383]]
* Jinja version: 2.11.2
* OS version: Ubuntu 18.04.2 LTS

Here i try to check some variants of errors for different templates: https://github.com/HumanUser/jinja2_strict_undefined
Another thing i noticed that DebugUndefined is not really debug in some cases.
