"""Runs the two templates from issue.md, and the hidden test's template, with each Undefined class."""
import jinja2

TEMPLATES = (
    "{{ 'value' in data['missing_key'] }}",
    "{% if 'value' in data['missing_key'] %}{% endif %}",
    "{{ 'foo' in missing }}",
)
CLASSES = (jinja2.StrictUndefined, jinja2.Undefined, jinja2.DebugUndefined, jinja2.ChainableUndefined)

for cls in CLASSES:
    for text in TEMPLATES:
        env = jinja2.Environment(undefined=cls)
        try:
            result = "rendered " + repr(env.from_string(text).render(data={}))
        except Exception as exc:  # report whatever the template raises
            result = f"raised {type(exc).__name__}: {exc}"
        print(f"{cls.__name__} | {text} | {result}")
