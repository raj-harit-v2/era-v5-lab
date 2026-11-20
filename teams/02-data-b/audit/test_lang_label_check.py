#!/usr/bin/env python3
"""Unit tests of lang_id.py and lang_label_check.py, on made-up text only. No IndicLID model is needed: a stub
labels each paragraph. Run: python -m unittest test_lang_label_check (from teams/02-data-b/audit)."""
import csv
import tempfile
import unittest
import unicodedata
from pathlib import Path

import lang_id
import lang_label_check as llc

CFG = lang_id.load_config()
HI = ("मुझे आज स्कूल जाना है और फिर मैं घर आऊँगा। यह बहुत अच्छा था और वह भी साथ में गया। "
      "उसने कहा कि वह कल फिर आएगा और हम सब साथ में खाना खाएँगे।")
MR = ("मला आज शाळेत जायचे आहे आणि नंतर मी घरी येईन. हे खूप चांगले आहे आणि त्यांनी मध्ये काम केले. "
      "आम्ही सगळे उद्या पुन्हा भेटणार आहोत आणि तसेच जेवण करणार आहोत.")
SA = ("अहं विद्यालयं गच्छामि। रामः वनं गच्छति। सः अपि तत्र अस्ति इति। "
      "तस्य पुत्रः अपि तत्र एव गच्छति च। अत्र किम् अस्ति इति सः पृच्छति।")
BN = ("আমি আজ স্কুলে যাব এবং তারপর বাড়ি ফিরব। তিনি কিন্তু সেখান থেকে আমাদের জন্য এসেছিলেন। "
      "আমরা সবাই কাল আবার দেখা করব এবং একসঙ্গে খাওয়া দাওয়া করব।")
AS = ("মই আজি বিদ্যালয়লৈ যাম আৰু তাৰ পিছত ঘৰলৈ উভতি আহিম। তেওঁ আৰু তেওঁৰ বাবে কৰা কাম। "
      "আমি সকলোৱে কালি পুনৰ লগ পাম আৰু একেলগে খাম।")
SA_BENG = ("তুষ্টোঽস্মি ভক্ত্যা তে ইতি উবাচ। গতিং মে দেহি দেবেশ যত্র তে চ সন্তি। "
           "সঃ অপি তত্র এব অস্তি ইতি চ। অহম্ তু তৎ কৃত্বা ভবতি। নমঃ তে দেবেশ মম গতিং দেহি ইতি উবাচ।")


def stub(labels):
    """A predict function: the label of a paragraph is the first key of `labels` found in it, else hin_Deva."""
    def predict(texts):
        return [next((lab for key, lab in labels.items() if key in t), "hin_Deva") for t in texts]
    return predict


class MarkerTest(unittest.TestCase):
    def vote(self, text, langs):
        return lang_id.marker_vote(lang_id.markers(text, langs, CFG), CFG)

    def test_hindi_marathi_sanskrit(self):
        langs = ["hi", "mr", "sa", "ne", "kok"]
        self.assertEqual(self.vote(HI, langs), "hi")
        self.assertEqual(self.vote(MR, langs), "mr")
        self.assertEqual(self.vote(SA, langs), "sa")

    def test_bengali_assamese(self):
        self.assertEqual(self.vote(BN, ["bn", "as"]), "bn")
        self.assertEqual(self.vote(AS, ["bn", "as"]), "as")

    def test_too_few_markers_is_unknown(self):
        self.assertEqual(self.vote("राम आज घर", ["hi", "mr"]), "unknown")


class JudgeTest(unittest.TestCase):
    def test_agree(self):
        r = lang_id.judge(HI, "hi", stub({}), CFG)
        self.assertEqual((r["verdict"], r["lid_lang"]), ("agree", "hi"))

    def test_maithili_label_counts_as_hindi(self):
        self.assertEqual(lang_id.judge(HI, "hi", stub({"मुझे": "mai_Deva"}), CFG)["verdict"], "agree")

    def test_mislabelled_needs_both_signals(self):
        r = lang_id.judge(MR, "hi", stub({"मला": "mar_Deva"}), CFG)
        self.assertEqual((r["verdict"], r["lid_lang"], r["marker_lang"]), ("mislabelled", "mr", "mr"))
        # IndicLID says Marathi, the marker words say Hindi: not confirmed
        self.assertEqual(lang_id.judge(HI, "hi", stub({"मुझे": "mar_Deva"}), CFG)["verdict"], "uncertain")

    def test_split_vote_is_uncertain(self):
        text = MR + "\n" + HI  # in a Sanskrit pack: half Marathi, half Hindi, neither reaches the vote share
        r = lang_id.judge(text, "sa", stub({"मला": "mar_Deva"}), CFG)
        self.assertIn(r["lid_lang"], ("hi", "mr"))
        self.assertLess(r["vote_share"], CFG["min_vote_share"])
        self.assertEqual(r["verdict"], "uncertain")

    def test_vote_is_weighted_by_letters(self):
        text = MR + "\n" + "हे आहे."  # a long Marathi paragraph and a short one the stub calls Hindi
        r = lang_id.judge(text, "mr", stub({"मला": "mar_Deva", "हे आहे": "hin_Deva"}), CFG)
        self.assertEqual(r["lid_lang"], "mr")

    def test_unknown_label_is_never_mislabelled(self):
        r = lang_id.judge(MR, "hi", stub({"मला": "doi_Deva"}), CFG)
        self.assertEqual((r["lid_lang"], r["verdict"]), ("other:doi_Deva", "uncertain"))

    def test_short_and_other_script(self):
        self.assertEqual(lang_id.judge("आहे", "mr", stub({}), CFG)["verdict"], "short")
        # under min_letters_to_flag (100): judged, but a disagreement is too short to trust
        self.assertEqual(lang_id.judge(MR[:60], "mr", stub({}), CFG)["verdict"], "short_disagree")
        self.assertEqual(lang_id.judge(MR[:60], "mr", stub({"मला": "mar_Deva"}), CFG)["verdict"], "agree")
        english = "This page is mostly English text with a short Hindi line. " * 12 + HI
        self.assertEqual(lang_id.judge(english, "hi", stub({}), CFG)["verdict"], "other_script")

    def test_other_scripts_are_not_sent_to_the_model(self):
        seen = []

        def predict(texts):
            seen.extend(texts)
            return ["hin_Deva"] * len(texts)
        lang_id.judge(HI + " Breaking News today", "hi", predict, CFG)
        self.assertTrue(seen and not any("Breaking" in t for t in seen))

    def test_nfc_only_and_text_not_returned(self):
        nfd = unicodedata.normalize("NFD", "क़िला " + HI)
        r = lang_id.judge(nfd, "hi", stub({}), CFG)
        self.assertFalse(any(isinstance(v, str) and len(v) > 40 for v in r.values()))
        src = (Path(lang_id.__file__)).read_text(encoding="utf-8")
        self.assertNotIn('"NFKC"', src)
        self.assertNotIn('"NFKD"', src)


    def test_repeated_paragraphs_count_once(self):
        text = "\n".join([MR] + ["शैली पृष्ठभूमि सफेद रंग नौ क्रमांक एक दो तीन चार"] * 6)
        r = lang_id.judge(text, "mr", stub({"मला": "mar_Deva", "शैली": "hin_Deva"}), CFG)
        self.assertEqual(r["lid_lang"], "mr")

    def test_hindi_with_visarga_words_is_not_sanskrit(self):
        text = HI + " उपायः शुभ रंगः हरा, शुभ अंकः तीन। अतः प्रातः काल।"
        self.assertNotEqual(lang_id.marker_vote(lang_id.markers(text, ["hi", "sa"], CFG), CFG), "sa")

    def test_outside_label_with_pack_markers_agrees(self):
        r = lang_id.judge(HI, "hi", stub({"मुझे": "brx_Deva"}), CFG)
        self.assertEqual((r["lid_lang"], r["verdict"], r["found_lang"]), ("other:brx_Deva", "agree", "hi"))

    def test_sanskrit_in_bengali_script(self):
        r = lang_id.judge(SA_BENG, "bn", stub({"তুষ্টো": "asm_Beng"}), CFG)
        self.assertEqual((r["verdict"], r["found_lang"]), ("mislabelled", "sa_Beng"))
        # IndicLID says Bengali: the pack's language, so agree (both signals are needed to flag)
        self.assertEqual(lang_id.judge(SA_BENG, "bn", stub({"তুষ্টো": "ben_Beng"}), CFG)["verdict"], "agree")


    def test_marker_group_is_compared_as_one(self):
        # Sanskrit in Bengali script also hits the Assamese letter ra: the group beats Bengali, Sanskrit is named
        hits = {"bn": 2, "as": 24, "sa_Beng": 40}
        from collections import Counter
        self.assertEqual(lang_id.marker_vote(Counter(hits), CFG), "sa_Beng")
        self.assertEqual(lang_id.marker_vote(Counter({"bn": 20, "as": 24, "sa_Beng": 16}), CFG), "as")  # stronger member
        self.assertEqual(lang_id.marker_vote(Counter({"bn": 30, "as": 24, "sa_Beng": 16}), CFG), "unknown")  # 40 < 2 x 30


    def test_sign_letters_are_counted_not_judged(self):
        r = lang_id.judge(BN + " রৰৰ", "bn", stub({"আমি": "ben_Beng"}), CFG)
        self.assertIn("as(ৰ):2", r["sign_letters"])
        self.assertIn("bn(র):", r["sign_letters"])
        self.assertEqual(r["verdict"], "agree")  # the letters are evidence for readers, not a verdict
        self.assertIn("mr(ळ):2", lang_id.judge(MR, "mr", stub({"मला": "mar_Deva"}), CFG)["sign_letters"])


class FlagTest(unittest.TestCase):
    def test_threshold_is_strictly_over(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            rates = d / "rates.csv"
            with open(rates, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["pack", "filter", "docs_in", "docs_dropped", "note"])
                w.writerows([["ind-mr-fw2", "a", 100, 20, "x"], ["ind-mr-fw2", "b", 100, 21, "x"],
                             ["ind-hi-fw2", "c", 0, 0, "x"]])
            ids = d / "ids.csv"
            with open(ids, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows([["pack", "filter", "doc_id"], ["ind-mr-fw2", "b", "x1"], ["ind-mr-fw2", "b", "x2"]])
            work = d / "work"
            work.mkdir()
            with open(work / "ind-mr-fw2_lang.csv", "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows([["doc_id", "verdict"], ["x1", "mislabelled"]])
            out = llc.flag(CFG, d, rates, 0.20, ids, work)
            self.assertEqual([r["over_threshold"] for r in out], [0, 1, 0])
            self.assertEqual((out[1]["mislabelled"], out[1]["not_checked"]), (1, 1))

    def test_threshold_is_configurable(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            rates = d / "rates.csv"
            rates.write_text("pack,filter,docs_in,docs_dropped,note\nind-sa-fw2,a,100,15,x\n", encoding="utf-8")
            self.assertEqual(llc.flag(CFG, d, rates, 0.10)[0]["over_threshold"], 1)
            self.assertEqual(llc.flag(CFG, d, rates, 0.20)[0]["over_threshold"], 0)

    def test_reads_the_shard_audit_format(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            rates = d / "audit_v1.csv"
            rates.write_text("pack_id,lang,shards,docs_raw,docs_kept,docs_dropped,drop_rate\n"
                             "ind-hi-fw2,hi,1,100,79,21,21.00%\n"
                             "ind-hi-hplt,hi,1,100,90,10,10.00%\n"
                             "ind-ml-fw2,ml,0,50,0,50,no shard\n", encoding="utf-8")
            out = llc.flag(CFG, d, rates, 0.20)
            self.assertEqual([r["over_threshold"] for r in out], [1, 0, 0])
            self.assertEqual(out[2]["status"], "no shard (not cleaned)")
            self.assertEqual(out[0]["filter"], llc.WHOLE_PIPELINE)


class ConfigTest(unittest.TestCase):
    def test_every_pack_language_has_a_script_and_markers(self):
        for pack, lang in CFG["packs"].items():
            self.assertIn(CFG["lang_script"][lang], lang_id.SCRIPT_RANGES, pack)
            self.assertIn(lang, CFG["markers"], pack)

    def test_mapped_labels_are_known_languages(self):
        for lab, lang in CFG["lid_label_to_lang"].items():
            self.assertIn(lang, CFG["lang_script"], lab)


if __name__ == "__main__":
    unittest.main()
