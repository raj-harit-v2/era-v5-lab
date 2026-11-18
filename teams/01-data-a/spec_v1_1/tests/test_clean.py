"""Tests of spec_v1_1/clean.py, the cleaner built from the combined sheet sheets/specv1_1.md, and of use_clean.py.

  python3 -m unittest discover -s spec_v1_1/tests      (from teams/01-data-a)

All text is made up.
"""
import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DATA_A = Path(__file__).resolve().parents[2]
SPEC = DATA_A / "spec_v1_1"
CLEAN = SPEC / "clean.py"
SHEET = SPEC / "sheets" / "specv1_1.md"
ADDITIONS = SPEC / "sheets" / "specv1_1_additions.md"
BUILD = SPEC / "build" / "build_clean.py"

_spec = importlib.util.spec_from_file_location("clean_v1_1", CLEAN)
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)

# the 24 spec v1.1 rules and their packs, from the additions sheet
V11 = dict(re.findall(r'^RULE_ID = "([^"]+)"\n(?:.*\n)*?ORIGIN = "([^"]+)"', ADDITIONS.read_text(encoding="utf-8"), re.M))


def doc(pack, text, lang="en"):
    return {"doc_id": "0" * 16, "text": text, "url": "", "lang_label": lang, "pack_id": pack}


def pipeline(family):
    return [c._ID[make] for make in c._PIPELINES[family]]


class Build(unittest.TestCase):
    def test_clean_py_is_built_from_the_combined_sheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "clean.py"
            subprocess.run([sys.executable, "-I", str(BUILD), "--sheet", str(SHEET), "--out", str(out)],
                           check=True, capture_output=True)
            self.assertEqual(out.read_bytes(), CLEAN.read_bytes(),
                             "spec_v1_1/clean.py is out of date: rebuild it from sheets/specv1_1.md")

    def test_246_rules_and_the_shared_f1(self):
        self.assertEqual(len(c._RULE), 247)
        self.assertIn("f1_rule.py", c._RULE)
        counts = {family: len(rules) for family, rules in c._PIPELINES.items()}
        self.assertEqual(counts, {"code": 24, "english": 23, "math": 22, "sci": 24, "indic": 153})

    def test_every_v1_1_rule_runs_on_its_origin_packs_only(self):
        self.assertEqual(len(V11), 24)
        for rid, origin in V11.items():
            self.assertEqual(set(c.SCOPE[rid]), set(origin.split(", ")), rid)


class Order(unittest.TestCase):
    def test_each_family_runs_spec_v1_first_then_spec_v1_1(self):
        for family in c._PIPELINES:
            ids = [rid for rid in pipeline(family) if rid != "DA-F1-005"]
            new = [rid in V11 for rid in ids]
            if any(new):
                first = new.index(True)
                self.assertTrue(all(new[first:]), f"{family}: a spec v1 rule runs after a v1.1 rule")

    def test_english_ends_with_the_instructors_f1(self):
        ids = pipeline("english")
        self.assertEqual(ids[-1], "DA-F1-005")
        self.assertEqual(ids[-4:-1], ["DA-A8-003", "DA-D7-001", "DA-A8-004"])

    def test_the_shared_f1_covers_code_math_sci_and_indic(self):
        packs = c.SCOPE["f1_rule.py"]
        for family in ("code", "math", "sci", "indic"):
            for pack in {p for p, f in c._FAMILY.items() if f == family}:
                self.assertIn(pack, packs, pack)
        self.assertFalse({p for p, f in c._FAMILY.items() if f == "english"} & set(packs))


class Routing(unittest.TestCase):
    def test_a_v1_1_rule_fires_through_clean(self):
        action, text = c.clean(doc("en-nemotroncc", "You can import your fileEdit with ease."))
        self.assertEqual(action, "fix")
        self.assertIn("file Edit", text)

    def test_a_v1_1_rule_is_off_on_other_packs(self):
        for pack in ("en-dclm", "en-fineweb-edu", "en-nemotroncc-synth"):
            self.assertIn("fileEdit", c.clean(doc(pack, "You can import your fileEdit with ease."))[1], pack)

    def test_the_indic_rule_fires_only_on_its_pack(self):
        text = "అతను వచ్చాడు .. తర్వాత వెళ్ళాడు"
        self.assertIn("...", c.clean(doc("ind-te-sangraha-v", text, "tel_Telu"))[1])
        self.assertNotIn("...", c.clean(doc("ind-te-fw2", text, "tel_Telu"))[1])

    def test_a_code_rule_fires_on_lang_label_code(self):
        text = "﻿import os\nprint(os.getcwd())\n"
        for pack in ("code-cpp", "code-go", "code-java", "code-js-ts", "code-python", "code-rust"):
            self.assertNotIn("﻿", c.clean(doc(pack, text, "code"))[1], pack)

    def test_cadj_and_unknown_packs_pass_unchanged(self):
        text = "You can import your fileEdit with ease .. ﻿"
        for pack in ("cadj-commits", "cadj-notebooks", "cadj-stackexchange", "no-such-pack", None):
            self.assertEqual(c.clean(doc(pack, text)), ("keep", text), pack)


class UseClean(unittest.TestCase):
    def test_a_spec_v1_tool_gets_spec_v1_1_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = Path(tmp) / "tool.py"
            tool.write_text("import sys\nsys.path.insert(0, %r)\nimport clean\nprint(clean.__file__)\n"
                            % str(DATA_A / "spec_v1"), encoding="utf-8")
            out = subprocess.run([sys.executable, "-I", str(SPEC / "use_clean.py"), str(tool)],
                                 check=True, capture_output=True, text=True).stdout.strip()
        self.assertEqual(Path(out).resolve(), CLEAN.resolve())

    def test_the_tool_gets_its_own_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = Path(tmp) / "tool.py"
            tool.write_text("import sys\nprint(sys.argv[1:])\n", encoding="utf-8")
            out = subprocess.run([sys.executable, "-I", str(SPEC / "use_clean.py"), str(tool), "--pack", "x"],
                                 check=True, capture_output=True, text=True).stdout.strip()
        self.assertEqual(out, "['--pack', 'x']")

    def test_a_missing_tool_is_refused(self):
        run = subprocess.run([sys.executable, "-I", str(SPEC / "use_clean.py"), "no_such_tool.py"],
                             capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("no such tool", run.stderr)


if __name__ == "__main__":
    unittest.main()
