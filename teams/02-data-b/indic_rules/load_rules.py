"""load_rules.py - reads the rules out of medicine_indic.md, so the tests run on the sheet itself.

    from load_rules import load
    for rule in load():                      # in run order
        action, text = rule.medicine(doc)    # doc = {doc_id, text, url, lang_label, pack_id}

Each python block runs in its own namespace, as in harm_test_indic.py and Data A's clean.py. The code in the sheet is
run as code: read it first.
"""
import re
from pathlib import Path
from types import SimpleNamespace

SHEET = Path(__file__).resolve().parent / "medicine_indic.md"
FENCE = re.compile(r"^```python\n(.*?)^```$", re.S | re.M)
FIELDS = ("RULE_ID", "CODE", "ACTION", "STAGE", "STATUS", "LANGS", "ORIGIN", "SOURCE", "AUTHOR")


def load(sheet=SHEET):
    rules = []
    for k, m in enumerate(FENCE.finditer(Path(sheet).read_text(encoding="utf-8")), 1):
        ns = {"__name__": "indic_rule"}
        exec(compile(m.group(1), f"{Path(sheet).name} block {k}", "exec"), ns)
        rules.append(SimpleNamespace(**{f: ns[f] for f in FIELDS}, medicine=ns["medicine"]))
    return rules
