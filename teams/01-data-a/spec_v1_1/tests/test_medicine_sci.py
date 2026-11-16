"""Tests for the rules in sheets/medicine_sci.md, loaded the way harmtest/harm_test.py loads them. All text is made up.

  python3 -m unittest discover -s spec_v1_1/tests      (from teams/01-data-a)
"""
import sys
import unittest
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPEC.parent / "harmtest"))  # harm_test.py moved here from tools/ (theschoolofai/era-v5-lab#244)
import harm_test  # noqa: E402  (only its loader is used; the file is not changed)

SHEET = SPEC / "sheets" / "medicine_sci.md"
RULES, _ = harm_test.load_rules(SHEET)
RULES = RULES["RULES_BY_ID"]


def doc(text, pack="sci-finepdfs"):
    return {"doc_id": "0" * 16, "text": text, "url": "", "lang_label": "en", "pack_id": pack}


def run(rule_id, text, **kw):
    return RULES[rule_id](doc(text, **kw))


class Sheet(unittest.TestCase):
    def test_one_rule_for_each_new_science_disease(self):
        self.assertEqual(sorted(RULES), ["DA-A7-001", "DA-A7-002", "DA-A7-003", "DA-A8-002", "DA-B6-001",
                                         "DA-C7-003", "DA-C7-004", "DA-C7-005", "DA-C8-003", "DA-C8-004",
                                         "DA-C8-005", "DA-C9-002"])

    def test_every_rule_is_off_on_other_packs(self):
        text = "company- owned ____________\n| 332 50.4 |  |\nIf you ally dependence such a referred book"
        for rid in RULES:
            self.assertEqual(run(rid, text, pack="math-finemath"), ("keep", text), rid)
            self.assertEqual(run(rid, text, pack=None), ("keep", text), rid)


class A7(unittest.TestCase):
    R = "DA-A7-001"

    def test_split_words_are_joined_with_the_hyphen_kept(self):
        self.assertEqual(run(self.R, "McDonald's company- owned and performance- based stores"),
                         ("fix", "McDonald's company-owned and performance-based stores"))
        self.assertEqual(run(self.R, "the stereo- scopic glasses"), ("fix", "the stereo-scopic glasses"))

    def test_day_to_day(self):
        self.assertEqual(run(self.R, "the day- to-day work"), ("fix", "the day-to-day work"))

    def test_suspended_hyphens_stay(self):
        for text in ("pre- and post-test scores", "a two- to three-fold rise", "first- or second-order", "low- versus high-dose"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_other_dashes_stay(self):
        for text in ("x- axis", "- a list item", "a - b", "Section A- Part", "COVID- 19", "pages 10- 12"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_idempotent(self):
        once = run(self.R, "company- owned, day- to-day")[1]
        self.assertEqual(run(self.R, once), ("keep", once))


class C9(unittest.TestCase):
    R = "DA-C9-002"

    def test_spinner_pages_are_dropped(self):
        pages = "\n".join(f"Page {n}/33" for n in range(1, 6))
        for text in ("If you ally dependence such a referred physics book that will provide you worth",
                     "Right here, we have countless books probability theory and examples",
                     "Access Free Ebook Physics Notes\nSome words.",
                     "Physics Ebook\n" + pages):
            self.assertEqual(run(self.R, text)[0], "drop", text)

    def test_a_report_with_page_markers_is_kept(self):
        text = "Page 1/3 of the report.\nDownload the PDF here.\nPage 2/3\nPage 3/3"
        self.assertEqual(run(self.R, text), ("keep", text))


class B6(unittest.TestCase):
    R = "DA-B6-001"

    def test_a_blank_form_is_dropped(self):
        text = "Name: ____________________ Phone: ____________\nAddress: ________________________"
        self.assertEqual(run(self.R, text)[0], "drop")

    def test_a_few_blanks_in_a_long_text_are_kept(self):
        text = "Fill in: x = _____ .\n" + "The rest of this page explains the method in words. " * 10
        self.assertEqual(run(self.R, text), ("keep", text))

    def test_a_page_under_30_percent_blanks_is_kept(self):
        text = "Q: " + "_" * 25 + " " + "word " * 15  # 25 of 87 non-space characters
        self.assertEqual(run(self.R, text), ("keep", text))


class C7Tables(unittest.TestCase):
    R = "DA-C7-003"

    def test_a_dangling_list_intro_is_cut(self):
        text = ("The Anti Ragging Committee of Samata College is constituted with the following members.\n"
                "The committee will look into the matters regarding complaints received from the students.")
        self.assertEqual(run(self.R, text), ("fix", text.replace(" with the following members.", ".")))

    def test_an_intro_followed_by_its_list_stays(self):
        for text in ("The committee is constituted with the following members:\n1. Dr. A, Chair\n2. Mr. B",
                     "The committee has the following members:\nDr. A. Kumar (Chair)",
                     "Consider the following: a long sentence that goes on to explain the whole idea in detail here."):
            self.assertEqual(run(self.R, text), ("keep", text), text)


class C8Order(unittest.TestCase):
    R = "DA-C8-004"

    def test_steps_out_of_order_are_put_back(self):
        text = "1. Remove the mount.\n2. Position washer.\n3. Attach tube.\n5. Tighten nut.\n4. Attach mount.\nObserve specs."
        want = "1. Remove the mount.\n2. Position washer.\n3. Attach tube.\n4. Attach mount.\n5. Tighten nut.\nObserve specs."
        self.assertEqual(run(self.R, text), ("fix", want))

    def test_other_lists_stay(self):
        for text in ("1. a\n2. b\n3. c", "3. c\n2. b\n1. a", "1. a\n3. b\n2. c\n7. d", "2. b\n1. a\nend"):
            self.assertEqual(run(self.R, text), ("keep", text), text)


class C8Cells(unittest.TestCase):
    R = "DA-C8-003"

    def test_two_numbers_in_one_cell_are_split_into_the_empty_cell(self):
        text = "| Female | 332 50.4 |  | 48.5 |\n| Male | 327 49.6 |  | 51.5 |"
        want = "| Female | 332 | 50.4 | 48.5 |\n| Male | 327 | 49.6 | 51.5 |"
        self.assertEqual(run(self.R, text), ("fix", want))

    def test_full_cells_and_prose_stay(self):
        for text in ("| A | 10 20 | 30 |", "332 50.4 |  |", "| Total | 1,323 |  |"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_idempotent(self):
        once = run(self.R, "| Female | 332 50.4 |  | 48.5 |")[1]
        self.assertEqual(run(self.R, once), ("keep", once))


# ---- sections 7-12, added 13 Nov from Utkarsh's reading (mittalutkarsh/era-v5-lab#5) ----------------------------

NEW_13_NOV = ("DA-A7-002", "DA-A7-003", "DA-A8-002", "DA-C7-005", "DA-C7-004", "DA-C8-005")
P = "The project will improve water quality and habitat for fish and wildlife in the stream."
Q = "The work also includes planting native trees along the banks to hold the soil in place."


class NewRulesOffOtherPacks(unittest.TestCase):
    def test_the_13_nov_rules_are_off_on_other_packs(self):
        text = ("D\n\neveloping a committee for the whole association\nF OODS L IMITED S OUTH H IGH\n"
                "MACEDuration: 5\n![x](image1.png)\nPage 1")
        for rid in NEW_13_NOV:
            self.assertEqual(run(rid, text, pack="math-finemath"), ("keep", text), rid)
            self.assertEqual(run(rid, text, pack=None), ("keep", text), rid)


class A7DropCap(unittest.TestCase):
    R = "DA-A7-002"

    def test_a_drop_cap_is_joined_to_its_word(self):
        text = "D\n\neveloping a Resort and Leisure Ministries Committee\n\nBo Simms"
        self.assertEqual(run(self.R, text), ("fix", "Developing a Resort and Leisure Ministries Committee\n\nBo Simms"))

    def test_words_and_cells_stay(self):
        for text in ("A\n\nnew approach to the teaching of science", "I\n\nam writing to you about the project",
                     "T\n\nF\n\nE", "B\n\nok", "D\n\nDeveloping a Resort and Leisure Committee"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_idempotent(self):
        once = run(self.R, "D\n\neveloping a Resort and Leisure Ministries Committee")[1]
        self.assertEqual(run(self.R, once), ("keep", once))


class A7SmallCaps(unittest.TestCase):
    R = "DA-A7-003"

    def test_small_caps_are_joined(self):
        text = "L AKEVILLE S OUTH H IGH S CHOOL\n\nS TUDENT A NNOUNCEMENTS\n\nM AY 27, 2022\n\nSENIOR INFO"
        want = "LAKEVILLE SOUTH HIGH SCHOOL\n\nSTUDENT ANNOUNCEMENTS\n\nMAY 27, 2022\n\nSENIOR INFO"
        self.assertEqual(run(self.R, text), ("fix", want))

    def test_a_few_capital_pairs_stay(self):
        for text in ("A NEW STUDY OF T CELLS", "VITAMIN D AND E LEVELS", "I AM A NEW MEMBER\nT CELLS and B CELLS"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_ordinary_capitals_in_the_gold_set_stay(self):
        # look-alikes of the 3 gold docs the first version changed (13 Nov): course codes next to lowercase
        # names, an all-capitals title full of whole words, and a possessive 'S
        for text in ("| G CHEM 10050| General Chemistry I |\n| G CHEM 10051| General Chemistry II |\n| D BIOL 12070| Cell Biology |",
                     "AN ORDINANCE ADOPTING A REVISED CODE FOR DISTRICTS A, B, C, D AND E, BEING ALL THE AREAS\n"
                     "DISTRICTS A, B, C, D AND E OF THE COUNTY\nTHE DISTRICTS D AND E ARE EXCLUDED FROM THE PLAN",
                     "“ST. MARY’S ENGLISH SCHOOL”\nTO: ST MARY’S ENGLISH SCHOOL\nST MARY’S ENGLISH MEDIUM SCHOOL"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_idempotent(self):
        once = run(self.R, "F OODS L IMITED M R . V IJAYA K UMAR - CFO, A PEX F ROZEN F OODS")[1]
        self.assertEqual(once, "FOODS LIMITED M R . VIJAYA KUMAR - CFO, APEX FROZEN FOODS")
        self.assertEqual(run(self.R, once), ("keep", once))


class A8Labels(unittest.TestCase):
    R = "DA-A8-002"

    def test_glued_field_labels_get_their_space(self):
        text = "Client:  MACEDuration:  On-goingCurrent Value:  £372,500"
        self.assertEqual(run(self.R, text), ("fix", "Client:  MACE Duration:  On-going Current Value:  £372,500"))

    def test_other_words_stay(self):
        for text in ("Telephone: 01234 567890", "JavaScript: a language", "Duration: 3 years",
                     "the Value: 5 units", "Contact us for details", "NEILABERCROMBIEGOVERNOR"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_idempotent(self):
        once = run(self.R, "MACEDuration:  On-goingCurrent Value:")[1]
        self.assertEqual(run(self.R, once), ("keep", once))


class C7NearEmpty(unittest.TestCase):
    R = "DA-C7-005"

    def test_a_title_with_no_body_is_dropped(self):
        text = "Riverside Riding Club Unaffiliated Dressage\n\nSunday, December 11, 2016 - Sunday, December 11, 2016"
        self.assertEqual(run(self.R, text)[0], "drop")

    def test_a_doc_of_250_characters_or_more_is_kept(self):
        text = "word " * 50 + "end."  # 254 characters
        self.assertEqual(run(self.R, text), ("keep", text))


class C7Images(unittest.TestCase):
    R = "DA-C7-004"

    def test_links_become_their_captions(self):
        text = ("SEM was used.\n\n![Particle size distribution](image1.png)\n\n![SEM showing sizes](image2.png)\n\n"
                "Fig. 1. (a) Particle size distribution")
        want = ("SEM was used.\n\nParticle size distribution\n\nSEM showing sizes\n\n"
                "Fig. 1. (a) Particle size distribution")
        self.assertEqual(run(self.R, text), ("fix", want))

    def test_links_with_no_caption_go(self):
        self.assertEqual(run(self.R, "Text.\n\n![](image)\n\nMore text."), ("fix", "Text.\n\nMore text."))
        self.assertEqual(run(self.R, "Text.\n\n![ ](image4.png) ![](image5.png)"), ("fix", "Text."))

    def test_an_inline_link_keeps_its_caption(self):
        text = "The block diagram ![Figure 1-1: Power path](image) shows the charger."
        self.assertEqual(run(self.R, text), ("fix", "The block diagram Figure 1-1: Power path shows the charger."))

    def test_real_links_and_words_stay(self):
        for text in ("![logo](https://example.org/logo.png)", "![chart](figures/chart1.png)",
                     "[image](image1.png)", "an image of the cell"):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_idempotent(self):
        once = run(self.R, "A.\n\n![x](image1.png)\n\nB ![y](image) C\n\n![](image3.jpg)")[1]
        self.assertEqual(once, "A.\n\nx\n\nB y C")
        self.assertEqual(run(self.R, once), ("keep", once))


class C8Pages(unittest.TestCase):
    R = "DA-C8-005"

    def test_page_lines_go(self):
        for footer in ("Page 10 of 11", "Page 1", "PAGE 3/12", "Page No. – Page No."):
            self.assertEqual(run(self.R, P + "\n\n" + footer + "\n\n" + Q), ("fix", P + "\n\n" + Q), footer)

    def test_page_numbers_first_last_and_between_paragraphs_go(self):
        self.assertEqual(run(self.R, P + "\n\n3"), ("fix", P))
        self.assertEqual(run(self.R, "14\n\nFrom Daylight Harvesting to Daylight Autonomy\n\n" + P),
                         ("fix", "From Daylight Harvesting to Daylight Autonomy\n\n" + P))
        self.assertEqual(run(self.R, P + "\n\n2\n\n" + Q), ("fix", P + "\n\n" + Q))

    def test_a_repeated_date_footer_goes(self):
        text = P + "\n\n10/21/2011\n\n" + Q + "\n\n10/21/2011\n\n" + P
        self.assertEqual(run(self.R, text), ("fix", P + "\n\n" + Q + "\n\n" + P))

    def test_dates_under_a_signature_stay(self):
        # look-alike of gold doc 8a2493cdf33f9a38 (13 Nov): signed comments, each dated under the name
        text = "Jane Doe\nSpringfield\n4/21/20\n\n" + P + "\n\nJohn Roe\n4/21/20\n\n" + Q + "\n\nAnn Poe\n4/21/20\n\n" + P
        self.assertEqual(run(self.R, text), ("keep", text))

    def test_a_date_left_alone_after_a_page_line_goes_in_one_run(self):
        text = P + "\n\nPage 2\n10/21/2011\n\n" + Q + "\n\nPage 3\n10/21/2011\n\n" + P
        self.assertEqual(run(self.R, text), ("fix", P + "\n\n" + Q + "\n\n" + P))

    def test_numbers_in_tables_lists_and_sentences_stay(self):
        for text in ("Year\n\n2010\n\n2011\n\n2012", "Date of visit:\n\n10/21/2011\n\n" + P, "Section\n\n2\n\nMethods",
                     "The number of samples that passed every quality check in the final round was\n\n12",
                     "14\n\n15\n\nContents", "The answer is 42."):
            self.assertEqual(run(self.R, text), ("keep", text), text)

    def test_idempotent(self):
        once = run(self.R, "Page 1\n\n14\n\nTitle of the paper\n\n" + P + "\n\n2\n\n" + Q + "\n\n7")[1]
        self.assertEqual(once, "Title of the paper\n\n" + P + "\n\n" + Q)
        self.assertEqual(run(self.R, once), ("keep", once))


if __name__ == "__main__":
    unittest.main()
