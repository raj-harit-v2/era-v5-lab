"""Tests for the rules in sheets/medicine_math.md, loaded the way harmtest/harm_test.py loads them. All text is made up.

  python3 -m unittest discover -s spec_v1_1/tests      (from teams/01-data-a)
"""
import sys
import unittest
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPEC.parent / "harmtest"))  # harm_test.py moved here from tools/ (theschoolofai/era-v5-lab#244)
import harm_test  # noqa: E402  (only its loader is used; the file is not changed)

SHEET = SPEC / "sheets" / "medicine_math.md"
RULES, _ = harm_test.load_rules(SHEET)
RULES = RULES["RULES_BY_ID"]


def doc(text, pack="math-finemath", lang="en"):
    return {"doc_id": "0" * 16, "text": text, "url": "", "lang_label": lang, "pack_id": pack}


def run(rule_id, text, **kw):
    return RULES[rule_id](doc(text, **kw))


class Sheet(unittest.TestCase):
    def test_one_rule_for_each_new_math_disease(self):
        self.assertEqual(sorted(RULES), ["DA-A8-001", "DA-C7-001", "DA-C7-002", "DA-C8-001", "DA-C8-002", "DA-C9-001",
                                         "DA-C9-003", "DA-D6-001"])

    def test_no_rule_uses_the_indic_code_c6(self):
        for rid, rule in RULES.items():
            self.assertNotEqual(rule.__globals__["CODE"], "C6", rid)

    def test_no_rule_touches_a_doc_with_no_pack(self):
        for rid in RULES:
            self.assertEqual(run(rid, "Find your perfect private math tutor =\n=\n=", pack=None)[0], "keep", rid)


class A8(unittest.TestCase):
    R = "DA-A8-001"

    def test_a_word_glued_to_a_sentence_word_is_split(self):
        self.assertEqual(run(self.R, "The answer is HydrogenWhen we heat it."),
                         ("fix", "The answer is Hydrogen When we heat it."))
        self.assertEqual(run(self.R, "Practice ProblemsThe first one"), ("fix", "Practice Problems The first one"))
        self.assertEqual(run(self.R, "Exercises: 30 minQuestions"), ("fix", "Exercises: 30 min Questions"))

    def test_a_missing_space_after_a_full_stop(self):
        self.assertEqual(run(self.R, "It ends here.The next part"), ("fix", "It ends here. The next part"))

    def test_brand_and_code_names_stay(self):
        text = "Use JavaScript, WordPress, PowerPoint, LinkedIn, YouTube and maxValue."
        self.assertEqual(run(self.R, text), ("keep", text))

    def test_code_lines_and_fences_stay(self):
        for text in ("if (x) { return sumThe; }", "```\nsumThe\n```", "a == bThe"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_idempotent(self):
        once = run(self.R, "ProblemsThe end.The next")[1]
        self.assertEqual(run(self.R, once), ("keep", once))

    def test_other_packs_and_languages_pass(self):
        self.assertEqual(run(self.R, "ProblemsThe", pack="sci-finepdfs"), ("keep", "ProblemsThe"))
        self.assertEqual(run(self.R, "ProblemsThe", lang="hi"), ("keep", "ProblemsThe"))


NUMBER_FACTS = """# 36871
## Basic properties
Odd, composite.
## Prime Factorization of 36871
36871 = 7 x 5267
## Divisors of 36871
1, 7, 5267, 36871
## 36871 as geometric shapes
### Circle
Diameter 73742
## Cryptographic Hash Functions
md5 ...
"""

PERCENT_OFF = """# How much is fifteen percent off forty one
### Inputs
### Results
### 1) What is 15 percent off \\$41? Find the amount of discount.
### 2) How much to pay for an item of \\$41 when discounted 15 percent?
### 3) 6.15 is what percent off \\$41?
"""

LESSON = """# Factors and multiples
## Prime factorization of 12
12 = 2 x 2 x 3.
## Divisors of 12
1, 2, 3, 4, 6, 12.
## Practice
Find the divisors of 18.
"""


class C9Templates(unittest.TestCase):
    R = "DA-C9-003"

    def test_number_fact_page_is_dropped(self):
        self.assertEqual(run(self.R, NUMBER_FACTS)[0], "drop")

    def test_one_dollar_amount_in_three_headings_is_dropped(self):
        self.assertEqual(run(self.R, PERCENT_OFF)[0], "drop")

    def test_unit_converter_sentence_is_dropped(self):
        text = "The answer is one Megaampere is equal to 1000000 Watt/Volt. Feel free to use our online unit conversion calculator."
        self.assertEqual(run(self.R, text, pack="math-megamath")[0], "drop")

    def test_converter_and_conversion_table_headings(self):
        text = "## 68.71 kg in lbs\ntext\n## 68.71 kg to lbs converter\ntext\n## Conversion table\n"
        self.assertEqual(run(self.R, text)[0], "drop")

    def test_lesson_with_weak_headings_only_is_kept(self):
        self.assertEqual(run(self.R, LESSON), ("keep", LESSON))

    def test_years_and_short_numbers_in_headings_do_not_count(self):
        text = "## 2019 paper\nq\n## 2019 answers\na\n## 2019 marks\nm\n## Class 10 Chapter 12\n## Class 10 Chapter 13\n## Class 10 Chapter 14\n"
        self.assertEqual(run(self.R, text), ("keep", text))

    def test_text_without_headings_is_kept(self):
        self.assertEqual(run(self.R, "Divisors of 36871 are 1, 7, 5267 and 36871."), ("keep", "Divisors of 36871 are 1, 7, 5267 and 36871."))

    def test_other_packs_pass(self):
        self.assertEqual(run(self.R, NUMBER_FACTS, pack="sci-finepdfs"), ("keep", NUMBER_FACTS))


class C9(unittest.TestCase):
    R = "DA-C9-001"

    def test_sales_and_spinner_pages_are_dropped(self):
        for text in ("## Find your perfect private math tutor in Forest\nLessons from $20.",
                     "Algebra help\n367 math teachers in Forest",
                     "# App that will do your homework for you\nSnap a photo.",
                     "Road distance Maladzyechna Pskov\n512 km",
                     "## Find an East Chicago Prealgebra Tutor\nText",
                     "If you ally dependence such a referred essential math book that will provide you worth"):
            self.assertEqual(run(self.R, text, pack="math-megamath")[0], "drop", text)

    def test_an_injected_line_is_removed(self):
        text = "You are watching: The product of nine and a number\nThe product of nine and a number is 9n."
        self.assertEqual(run(self.R, text), ("fix", "The product of nine and a number is 9n."))

    def test_ordinary_lessons_stay(self):
        text = "A tutor can help you find the answer. We solve problems step by step, as in Lesson 3."
        self.assertEqual(run(self.R, text), ("keep", text))


FORUM = ("# Thread\nUser post here.\nIn summary, the conversation discusses a proof.\nMore user text.\n"
         "1. What is X?\n\nX is a thing.\n\n2. Why is X?\n\nBecause.\n\n3. How is X used?\n\nLike so.\n\n"
         "4. Can X fail?\n\nNo.\n\n• Other Physics Topics\n3\n")
FORUM_CLEAN = "# Thread\nUser post here.\nMore user text.\n\n• Other Physics Topics\n3\n"


class D6(unittest.TestCase):
    R = "DA-D6-001"

    def test_forum_summary_and_faq_are_removed(self):
        self.assertEqual(run(self.R, FORUM), ("fix", FORUM_CLEAN))

    def test_forum_summary_alone_is_removed(self):
        text = "Question?\nIn summary, the discussion is about limits.\nReply: use L'Hopital."
        self.assertEqual(run(self.R, text), ("fix", "Question?\nReply: use L'Hopital."))

    def test_machine_written_articles_are_dropped(self):
        for text in ("# Topic\n## Introduction to Algebra\nt\n## Introduction to Geometry\nt\n## Understanding Calculus\nt\n"
                     "In summary, algebra is important.\n",
                     "## FAQ 1: How long does it take?\nA week.\n## Conclusion\nDone.\n"):
            self.assertEqual(run(self.R, text)[0], "drop", text)

    def test_one_sign_alone_is_kept(self):
        for text in ("## Lesson\ntext\n## Conclusion\nWe learned x.\n",
                     "1. What is X?\n\nA\n\n2. Why?\n\nB\n\n3. How?\n\nC\n\n4. When?\n\nD\n"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_off_on_megamath(self):
        self.assertEqual(run(self.R, FORUM, pack="math-megamath"), ("keep", FORUM))


class C7Formulas(unittest.TestCase):
    R = "DA-C7-001"

    def test_four_gaps_drop_the_doc(self):
        text = ("The number of fish in tank B =\nUse Binet's formula to show that .\n"
                "Comparing , we can see that it holds.\nThe area of the circle is\nNow find the perimeter.")
        self.assertEqual(run(self.R, text)[0], "drop")

    def test_empty_answer_options_drop_the_doc(self):
        self.assertEqual(run(self.R, "Q1. Find the value.\n(A)\n(B)\n(C)\n(D)\n", pack="math-megamath")[0], "drop")

    def test_sentences_cut_where_the_formula_was_drop_the_doc(self):
        text = ("The equation of the parallel line is\nUse it to find the area.\nThe radius of the circle is\nSo we get\n"
                "The slope is\nThen draw it.")
        self.assertEqual(run(self.R, text)[0], "drop")

    def test_sentences_that_carry_on_are_kept(self):
        for text in ("The only force acting on a ball is\nA. gravity\nB. friction\nThe speed of the ball is\nA. 2 m/s\n"
                     "The mass is\nA. 1 kg\nThe charge is\nA. 0",
                     "which clearly gives\na^2 + a = 0\nThese are\n• Define subproblems\nthe world of\nnatural units\n"
                     "The answer is\nx = 5"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_complete_working_and_two_gaps_are_kept(self):
        for text in ("x = 5\ny = x + 2 = 7\nThe answer is 7.", "a =\nb =\nThat is all.", "Is it true? Yes.",
                     "6.75 + 4.16 =\n\n10.91\n\n19.7 - 6.9 =\n\n12.8\n\n2 + 2 =\n\n4"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_option_labels_above_their_options_are_kept(self):
        text = "Which is fastest?\n(a)\nv\n(b)\nv2\n(c)\nv3\n(d)\nv4\n"
        self.assertEqual(run(self.R, text), ("keep", text))


LONG = "This lesson explains forces on structures in detail. " * 45


class C7Figures(unittest.TestCase):
    R = "DA-C7-002"

    def test_a_short_problem_with_a_missing_figure_is_dropped(self):
        text = "Figure P9.26 shows the thrust of a rocket. Find the impulse."
        self.assertEqual(run(self.R, text, pack="math-megamath")[0], "drop")

    def test_a_long_doc_with_two_references_is_dropped(self):
        text = LONG + "Find the forces in the truss shown below. Then see Figure 3.12."
        self.assertEqual(run(self.R, text, pack="math-megamath")[0], "drop")

    def test_a_long_doc_with_one_reference_is_kept(self):
        text = LONG + "The graph below shows the speed."
        self.assertEqual(run(self.R, text, pack="math-megamath"), ("keep", text))

    def test_off_on_finemath(self):
        text = "Figure 1 shows the graph."
        self.assertEqual(run(self.R, text), ("keep", text))


class C8Formulas(unittest.TestCase):
    R = "DA-C8-001"

    def test_a_formula_split_one_token_per_line_is_dropped(self):
        text = "Max\n\n+\n\n+\n\n(\n\n0\n\n+\n\n(\n\n+\n\n0\n\nthe rest of the problem"
        self.assertEqual(run(self.R, text)[0], "drop")

    def test_a_column_of_plain_numbers_is_kept(self):
        text = "Topics\n13\n722\n22\n1K\n29\n2K\n6\n844\n14\n2K\n"
        self.assertEqual(run(self.R, text), ("keep", text))

    def test_a_short_run_is_kept(self):
        text = "Solve\nx\n+\n2\n=\n5\nand check."
        self.assertEqual(run(self.R, text), ("keep", text))

    def test_options_one_per_line_are_kept(self):
        text = "Pick one\n(a)\n0\n(b)\n6\n(c)\n2\n(d)\n1\n(e)\n-1\n"
        self.assertEqual(run(self.R, text), ("keep", text))


class C8Tables(unittest.TestCase):
    R = "DA-C8-002"

    def test_a_flattened_table_row_drops_the_doc(self):
        for text in ("m n mod m 2 3 4 5 6 7 8 9 1 1 3 1 1 2 7 7 1 2 3 4\n",
                     "Facts\n3 + 4 = 7 7 - 3 = 4 4 + 3 = 7 7 - 4 = 3 1 + 1 = 2\n"):
            self.assertEqual(run(self.R, text)[0], "drop", text)

    def test_short_numeric_lines_and_prose_are_kept(self):
        for text in ("2 + 3 = 5 and 5 - 3 = 2, so 4 + 1 = 5", "The values 2, 3, 5 and 7 are the primes below ten."):
            self.assertEqual(run(self.R, text), ("keep", text), text)


if __name__ == "__main__":
    unittest.main()
