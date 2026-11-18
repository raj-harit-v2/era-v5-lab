"""Tests for the Indic scorer in scorers.py: correct answers, wrong answers and the ways a model could cheat."""

from __future__ import annotations

import importlib.util
import json
import unicodedata
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("g10_scorers_indic", HERE / "scorers.py")
assert spec is not None and spec.loader is not None
scorers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorers)
T = scorers.T

# A named decorator: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize

INDIC = scorers.load_jsonl(HERE / "indic_v1.jsonl")
BY_ID = {r["id"]: r for r in INDIC}
LANGS = ["hi", "mr", "ta", "te", "kn", "bn", "gu", "ml", "or", "pa"]
SCRIPT_OF = {"hi": "DEVANAGARI", "mr": "DEVANAGARI", "ta": "TAMIL", "te": "TELUGU", "kn": "KANNADA",
             "bn": "BENGALI", "gu": "GUJARATI", "ml": "MALAYALAM", "or": "ORIYA", "pa": "GURMUKHI"}
# Native text per script that is not any script-row prompt: the two question prompts of the same language.
SAMPLE = {lang: BY_ID[f"in-ans-{lang}-1"]["messages"][-1]["content"] + " " + BY_ID[f"in-ans-{lang}-2"]["messages"][-1]["content"]
          for lang in LANGS}


def say(text):
    return text + T["im_end"]


def user_of(row):
    return row["messages"][-1]["content"]


def reference(row):
    e = row["expect"]
    if e["kind"] == "answer":
        return say(f"उत्तर: {e['accept'][0]}" if row["lang"] in ("hi", "mr") else f"{e['accept'][0]}")
    if e["kind"] == "script":
        return say(SAMPLE[row["lang"]])
    return say(f"यह रहा: {e['text']}")


# --- the set ----------------------------------------------------------------------------------------------


def test_set_covers_ten_scripts_and_three_kinds():
    assert len(INDIC) == len({r["id"] for r in INDIC}) == 44
    assert {r["lang"] for r in INDIC} == set(LANGS)
    assert {r["kind"] for r in INDIC} == {"answer", "script", "copy"}
    for lang in LANGS:
        assert sum(r["kind"] == "answer" and r["lang"] == lang for r in INDIC) >= 2, lang
        assert any(r["kind"] == "script" and r["lang"] == lang for r in INDIC), lang


def test_every_row_says_who_wrote_it_and_whether_a_native_speaker_reviewed_it():
    for r in INDIC:
        assert r["source"].startswith("original:") and "evaluation-only" in r["source"]
        if r["lang"] in {"hi", "mr", "te", "kn"}:
            assert r["review"] == "wording reviewed by a native speaker", r["id"]
        else:
            assert r["review"] == "wording not reviewed by a native speaker", r["id"]


def test_every_prompt_renders_and_parses_back():
    for r in INDIC:
        parsed = scorers.render.parse(scorers.render.render(r["messages"], "1k"))
        assert parsed["messages"][-1]["role"] == "user"
        assert scorers.build_prompt(r).endswith(f"{T['im_start']}assistant\n")


def test_the_stated_script_is_the_script_of_the_language():
    for r in INDIC:
        e = r["expect"]
        if e["kind"] == "script":
            assert e["script"] == SCRIPT_OF[r["lang"]], r["id"]


def test_native_prompts_and_accepted_words_are_written_in_the_right_script():
    for r in INDIC:
        target = SCRIPT_OF[r["lang"]]
        e = r["expect"]
        if r["id"].startswith("in-scr-en-"):
            continue
        share, _ = scorers.script_share(user_of(r) if e["kind"] != "copy" else e["text"], target)
        assert share >= 0.85, (r["id"], share)
        for word in e.get("accept", []):
            if not word.isdigit():
                assert scorers.script_share(word, target)[0] == 1.0, (r["id"], word)


def test_copy_rows_really_hold_zwj_or_zwnj_where_the_id_says_so():
    for rid, mark in (("in-cpy-hi-zwj", "‍"), ("in-cpy-hi-zwnj", "‌"),
                      ("in-cpy-bn-zwj", "‍"), ("in-cpy-ml-zwj", "‍")):
        assert mark in BY_ID[rid]["expect"]["text"] and mark in user_of(BY_ID[rid]), rid


def test_no_accepted_answer_is_already_in_its_prompt():
    for r in INDIC:
        if r["kind"] == "answer":
            plain = scorers._plain(user_of(r))
            assert not any(scorers._holds(plain, a) for a in r["expect"]["accept"]), r["id"]


# --- right answers ----------------------------------------------------------------------------------------


@parametrize("row", INDIC, ids=[r["id"] for r in INDIC])
def test_reference_answer_scores_one(row):
    got = scorers.score_indic(row, reference(row))
    assert got["score"] == 1, got


@parametrize("row", [r for r in INDIC if r["kind"] == "answer"], ids=lambda r: r["id"])
def test_every_accepted_spelling_scores_one(row):
    for word in row["expect"]["accept"]:
        assert scorers.score_indic(row, say(f"{word}।"))["score"] == 1, word


def test_digits_of_any_script_are_the_same_number():
    row = BY_ID["in-ans-hi-2"]  # accepts 12
    for reply in ("12", "१२", "उत्तर १२ है", "बारह"):
        assert scorers.score_indic(row, say(reply))["score"] == 1, reply
    tamil = BY_ID["in-ans-ta-2"]  # accepts 60
    assert scorers.score_indic(tamil, say("௬௦"))["score"] == 1
    assert scorers.fold_digits("௬௦ ১২ ७") == "60 12 7"


def test_the_stage_of_a_digit_is_respected():
    row = BY_ID["in-ans-hi-1"]  # accepts 7 and सात
    assert scorers.score_indic(row, say("17"))["score"] == 0
    assert scorers.score_indic(row, say("७०"))["score"] == 0
    assert scorers.score_indic(row, say("सात दिन"))["score"] == 1


def test_a_reply_may_carry_a_think_block_before_the_answer():
    row = BY_ID["in-ans-mr-1"]
    text = f"{T['think']}\nविचार\n{T['think_end']}\nमुंबई" + T["im_end"]
    assert scorers.score_indic(row, text)["score"] == 1


# --- wrong answers and cheating ---------------------------------------------------------------------------


@parametrize("row", [r for r in INDIC if r["kind"] == "answer"], ids=lambda r: r["id"])
def test_a_wrong_answer_scores_zero(row):
    assert scorers.score_indic(row, say("मुझे नहीं पता"))["score"] == 0
    assert scorers.score_indic(row, say("999"))["score"] == 0


def test_a_list_of_every_answer_is_too_long():
    row = BY_ID["in-ans-hi-1"]
    shotgun = " ".join(str(n) for n in range(1, 400))
    got = scorers.score_indic(row, say(shotgun))
    assert got["score"] == 0 and "longer than" in got["reason"]


@parametrize("row", INDIC, ids=[r["id"] for r in INDIC])
def test_empty_or_off_topic_replies_score_zero(row):
    for text in ("", " ", T["im_end"], say("Happy to help."), say("ठीक है")):
        assert scorers.score_indic(row, text)["score"] == 0, (row["id"], text)


@parametrize("row", [r for r in INDIC if r["kind"] != "copy"], ids=lambda r: r["id"])
def test_repeating_the_prompt_scores_zero(row):
    got = scorers.score_indic(row, say(user_of(row)))
    assert got["score"] == 0


def test_a_tool_call_or_a_broken_turn_scores_zero():
    row = BY_ID["in-ans-hi-1"]
    call = f"{T['tool_call']}\n{{\"arguments\":{{}},\"name\":\"x\"}}\n{T['tool_call_end']}\n" + T["im_end"]
    assert scorers.score_indic(row, call)["score"] == 0
    assert scorers.score_indic(row, say("सात") + f"{T['im_start']}user\nhi")["score"] == 0


# --- script check -----------------------------------------------------------------------------------------


def test_a_reply_in_another_script_scores_zero():
    row = BY_ID["in-scr-ta"]
    assert scorers.score_indic(row, say(SAMPLE["ta"]))["score"] == 1
    for lang in ("hi", "te", "kn", "bn"):
        got = scorers.score_indic(row, say(SAMPLE[lang] + " " + SAMPLE[lang]))
        assert got["score"] == 0 and "TAMIL" in got["reason"], lang
    assert scorers.score_indic(row, say("It rains a lot in the monsoon season, and the fields turn green."))["score"] == 0


def test_hindi_and_marathi_share_a_script():
    assert scorers.script_share(SAMPLE["mr"], "DEVANAGARI")[0] == 1.0
    assert scorers.score_indic(BY_ID["in-scr-hi"], say(SAMPLE["mr"] + " " + SAMPLE["mr"]))["score"] == 1


def test_a_little_latin_is_allowed_but_not_half():
    row = BY_ID["in-scr-hi"]
    text = SAMPLE["hi"] + " " + SAMPLE["hi"] + " monsoon"
    assert scorers.score_indic(row, say(text))["score"] == 1
    half = SAMPLE["hi"] + " this reply is mostly written in english letters instead"
    assert scorers.score_indic(row, say(half))["score"] == 0


def test_digits_and_punctuation_do_not_help_a_short_reply():
    row = BY_ID["in-scr-hi"]
    got = scorers.score_indic(row, say("बारिश। 1234567890 !!!"))
    assert got["score"] == 0 and "fewer than" in got["reason"]


def test_script_share_ignores_zwj_and_zwnj():
    plain = scorers.script_share("क्षमा", "DEVANAGARI")
    assert scorers.script_share("क्‍षमा", "DEVANAGARI")[0] == plain[0] == 1.0


# --- ZWJ, ZWNJ and conjuncts ------------------------------------------------------------------------------


@parametrize("rid", ["in-cpy-hi-zwj", "in-cpy-hi-zwnj", "in-cpy-bn-zwj", "in-cpy-ml-zwj"])
def test_dropping_or_swapping_the_joiner_scores_zero(rid):
    row = BY_ID[rid]
    text = row["expect"]["text"]
    assert scorers.score_indic(row, say(text))["score"] == 1
    assert scorers.score_indic(row, say(text.replace("‍", "").replace("‌", "")))["score"] == 0
    swapped = text.replace("‍", "‌") if "‍" in text else text.replace("‌", "‍")
    assert scorers.score_indic(row, say(swapped))["score"] == 0


def test_the_zwj_and_zwnj_rows_are_different_words():
    assert BY_ID["in-cpy-hi-zwj"]["expect"]["text"] != BY_ID["in-cpy-hi-zwnj"]["expect"]["text"]


def test_a_copy_may_sit_inside_a_longer_reply_and_may_use_the_other_nukta_spelling():
    row = BY_ID["in-cpy-te"]
    assert scorers.score_indic(row, say("ఇదిగో: శ్రీరామ నవమి. సరేనా?"))["score"] == 1
    decomposed = unicodedata.normalize("NFD", row["expect"]["text"])
    assert scorers.score_indic(row, say(decomposed))["score"] == 1


# --- sets and command line --------------------------------------------------------------------------------


def test_set_score_reports_kind_and_language_and_counts_a_missing_row_as_zero():
    gens = {r["id"]: reference(r) for r in INDIC if r["lang"] != "hi"}
    out = scorers.score_indic_set(INDIC, gens)
    assert out["n"] == 44 and 0 < out["exact"] < 1
    assert out["by_lang"]["hi"] == 0.0 and out["by_lang"]["ta"] == 1.0
    assert set(out["by_kind"]) == {"answer", "copy", "script"}


def test_set_score_of_all_reference_answers_is_one():
    out = scorers.score_indic_set(INDIC, {r["id"]: reference(r) for r in INDIC})
    assert out["exact"] == 1.0 and all(v == 1.0 for v in out["by_lang"].values())


def test_command_line_scores_an_indic_run_file(tmp_path):
    rows = str(HERE / "indic_v1.jsonl")
    gens = tmp_path / "gens.jsonl"
    chosen = INDIC[:22]
    gens.write_text("".join(json.dumps({"id": r["id"], "generation": reference(r)}, ensure_ascii=False) + "\n"
                            for r in chosen), encoding="utf-8")
    out = tmp_path / "report.json"
    assert scorers.main(["indic", "--rows", rows, "--generations", str(gens), "--out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["n"] == 44 and report["exact"] == 0.5


# --- regressions found in review --------------------------------------------------------------------------


@parametrize("reply", ["लगभग 7.5 दिन", "1,7", "7,5", "17", "70", "7.25"])
def test_a_number_inside_a_longer_number_does_not_count(reply):
    assert scorers.score_indic(BY_ID["in-ans-hi-1"], say(reply))["score"] == 0


@parametrize("reply", ["7", "7 दिन", "7.", "7, यानी सात", "(7)", "७।", "हफ्ते में 7 दिन होते हैं।"])
def test_the_number_still_counts_with_ordinary_punctuation_around_it(reply):
    assert scorers.score_indic(BY_ID["in-ans-hi-1"], say(reply))["score"] == 1


def test_restating_the_question_before_the_answer_is_fine():
    row = BY_ID["in-ans-hi-1"]
    assert scorers.score_indic(row, say(user_of(row) + " सात"))["score"] == 1
    assert scorers.score_indic(row, say(user_of(row)))["score"] == 0


def test_quoting_the_request_before_writing_is_fine_but_only_the_new_words_count():
    row = BY_ID["in-scr-hi"]
    new = "बारिश आती है और खेत हरे हो जाते हैं। नदियाँ भर जाती हैं।"
    assert scorers.score_indic(row, say(user_of(row) + " " + new))["score"] == 1
    echo = scorers.score_indic(row, say(user_of(row)))
    assert echo["score"] == 0 and echo["reason"] == "the reply only repeats the prompt"
    assert scorers.score_indic(row, say(user_of(row) + " हाँ"))["score"] == 0


@parametrize("rid, word", [("in-ans-te-1", "హైదరాబాదు"), ("in-ans-mr-1", "मुम्बई"), ("in-ans-bn-1", "কোলকাতা")])
def test_common_alternative_spellings_of_a_capital_are_accepted(rid, word):
    assert scorers.score_indic(BY_ID[rid], say(word))["score"] == 1


def test_every_spelling_of_a_malayalam_chillu_is_the_same_answer():
    row = BY_ID["in-ans-ml-2"]  # 24: ഇരുപത്തിനാല്
    stem = "ഇരുപത്തിനാ"
    for last in ("ൽ", "ല്‍", "ല്"):  # atomic chillu, consonant + virama + ZWJ, virama
        assert scorers.score_indic(row, say(stem + last))["score"] == 1, [hex(ord(c)) for c in last]
    assert scorers.score_indic(row, say(stem + "ള്‍"))["score"] == 0  # a different letter


def test_the_malayalam_copy_row_still_wants_the_exact_old_spelling():
    row = BY_ID["in-cpy-ml-zwj"]
    atomic = row["expect"]["text"].replace("ന്‍", "ൻ")
    assert atomic != row["expect"]["text"]
    assert scorers.score_indic(row, say(atomic))["score"] == 0


def test_a_negated_answer_still_passes_which_the_scorer_cannot_tell():
    # Known limit, kept as a test so nobody believes otherwise: matching is by words, not by meaning.
    assert scorers.score_indic(BY_ID["in-ans-mr-1"], say("मुंबई नाही, पुणे"))["score"] == 1


def test_chillu_folding_makes_the_old_and_new_spelling_the_same_text():
    # The accepted 24-word happens to be a prefix of its old spelling, so test the folding itself: ന്‍ and ൻ.
    old, new = "അവന്‍", "അവൻ"
    assert old != new and scorers._plain(old) == scorers._plain(new)
    assert scorers._holds(scorers._plain("ഇതാണ് " + old), new)
    assert scorers._holds(scorers._plain("ഇതാണ് " + new), old)
    assert not scorers._holds(scorers._plain("ഇതാണ് അവൾ"), new)
