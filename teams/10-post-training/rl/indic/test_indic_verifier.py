"""Tests for indic_verifier.py: one correct and one wrong answer for every task, the cheating cases, the
normalisation rules and the task lint.

Run:  python -m pytest teams/10-post-training/rl/indic/test_indic_verifier.py -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"
spec = importlib.util.spec_from_file_location("g10_indic_verifier", HERE / "indic_verifier.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# Named decorator: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize

THINK = "<|think|>\nपहले सवाल को ध्यान से पढ़ते हैं।\n<|/think|>\n"

# One correct and one wrong completion per task, written the way a model would reply (thinking, then a short answer).
CASES = {
    "hi_mango_count": ("48 - 17 = 31, फिर 31 + 9 = 40।\n<answer>40</answer>",
                       "48 - 17 - 9 = 22।\n<answer>22</answer>"),
    "hi_weekday_after": ("10 दिन = 1 सप्ताह और 3 दिन। बुधवार के 3 दिन बाद शनिवार।\n<answer>शनिवार</answer>",
                         "बुधवार के 2 दिन बाद शुक्रवार।\n<answer>शुक्रवार</answer>"),
    "hi_number_words": ("तीन लाख = 300000, पाँच हज़ार = 5000, बयालीस = 42।\n<answer>३,०५,०४२</answer>",
                        "<answer>350042</answer>"),
    "ta_class_present": ("23 + 19 = 42, 42 - 6 = 36.\n<answer>36</answer>",
                         "23 + 19 = 42.\n<answer>42</answer>"),
    "bn_largest_choice": ("৫০২ সবচেয়ে বড়।\n<answer>খ</answer>",
                          "<answer>ঘ</answer>"),
    "te_passage_who": ("రాము తన చెల్లెలుతో వెళ్ళాడు.\n<answer>సీత</answer>",
                       "<answer>గోపాల్</answer>"),
}


def task(name: str) -> Path:
    return TASKS / name


def score(name: str, completion: str) -> dict:
    return v.reward(task(name), completion)


def test_every_shipped_task_has_a_correct_and_a_wrong_case():
    assert sorted(CASES) == sorted(p.parent.name for p in TASKS.glob("*/task.json"))


@parametrize("name", sorted(CASES))
def test_correct_answer_scores_one(name):
    r = score(name, THINK + CASES[name][0])
    assert r["reward"] == 1, r


@parametrize("name", sorted(CASES))
def test_wrong_answer_scores_zero(name):
    r = score(name, THINK + CASES[name][1])
    assert r["reward"] == 0 and r["reason"] in ("wrong answer", "answer is not in the task's script"), r


@parametrize("name", sorted(CASES))
def test_shipped_task_passes_the_lint(name):
    assert v.check_task(task(name)) == []


def test_reply_never_contains_the_expected_answer():
    r = score("hi_mango_count", "<answer>41</answer>")
    assert "40" not in json.dumps(r)


# --- answer extraction and cheating ------------------------------------------------------------

def test_no_answer_tag_scores_zero():
    assert score("hi_mango_count", "उत्तर 40 है।")["reason"] == "no answer tag"


def test_empty_answer_scores_zero():
    assert score("hi_mango_count", "<answer> । </answer>")["reason"] == "empty answer"


def test_two_different_answers_score_zero_even_if_one_is_right():
    r = score("hi_mango_count", "<answer>40</answer> या शायद <answer>22</answer>")
    assert r["reward"] == 0 and r["reason"] == "more than one answer"


def test_the_same_answer_repeated_is_fine():
    assert score("hi_mango_count", "<answer>40</answer>\nफिर से: <answer>४०</answer>")["reward"] == 1


def test_a_list_of_guesses_in_one_tag_scores_zero():
    assert score("hi_mango_count", "<answer>38 39 40 41</answer>")["reward"] == 0
    long_guess = "<answer>" + " ".join(str(i) for i in range(100)) + "</answer>"
    assert score("hi_mango_count", long_guess)["reason"] == "answer too long"


def test_an_answer_inside_the_think_span_does_not_count():
    r = score("hi_mango_count", "<|think|>\n<answer>40</answer>\n<|/think|>\nपता नहीं।")
    assert r["reward"] == 0 and r["reason"] == "no answer tag"


def test_only_the_reply_after_the_last_think_span_counts():
    two_spans = "<|think|>a<|/think|>b <answer>22</answer><|think|>c<|/think|><answer>40</answer>"
    assert score("hi_mango_count", two_spans)["reward"] == 1  # with the first span's end, two answers would score 0
    assert score("hi_mango_count", "<|think|>a<|/think|><answer>40</answer><|think|>c<|/think|>")["reason"] == "no answer tag"


def test_a_think_span_that_never_closes_has_no_answer():
    assert score("hi_mango_count", "<|think|>\nसोच रहा हूँ <answer>40</answer>")["reason"] == "think span not closed"


def test_a_think_span_reopened_after_the_last_close_has_no_answer():
    r = score("hi_mango_count", THINK + "<|think|> <answer>40</answer>")
    assert r["reason"] == "think span not closed"


def test_only_the_last_part_of_a_huge_reply_is_read():
    filler = "क" * (v.MAX_SCAN_CHARS + 10)
    assert score("hi_mango_count", "<answer>40</answer>" + filler)["reason"] == "no answer tag"
    assert score("hi_mango_count", filler + "<answer>40</answer>")["reward"] == 1


def test_an_unclosed_or_nested_tag_does_not_score():
    assert score("hi_mango_count", "<answer>40")["reward"] == 0
    assert score("hi_mango_count", "<answer><answer>40</answer>")["reward"] == 0


def test_extra_words_or_units_with_an_integer_score_zero():
    assert score("hi_mango_count", "<answer>40 आम</answer>")["reason"] == "answer is not an integer"
    assert score("hi_mango_count", "<answer>चालीस</answer>")["reason"] == "answer is not an integer"


# --- normalisation -----------------------------------------------------------------------------

def test_the_tasks_own_digits_equal_ascii_digits():
    for answer in ("40", "४०"):
        assert score("hi_mango_count", f"<answer>{answer}</answer>")["reward"] == 1, answer
    for answer in ("36", "௩௬"):
        assert score("ta_class_present", f"<answer>{answer}</answer>")["reward"] == 1, answer


def test_another_scripts_digits_score_zero():
    for answer in ("৪০", "௪௦", "٤٠", "\uff14\uff10"):  # Bengali, Tamil, Arabic-Indic, fullwidth
        assert score("hi_mango_count", f"<answer>{answer}</answer>")["reason"] == "answer is not an integer", answer
    assert score("ta_class_present", "<answer>३६</answer>")["reward"] == 0


def test_a_leading_zero_scores_zero():
    for answer in ("040", "0040", "०४०", "0,040"):
        assert score("hi_mango_count", f"<answer>{answer}</answer>")["reward"] == 0, answer
    item = v.prepare({"id": "zero", "answer_type": "integer", "script": "Deva"}, [0])
    assert v.score(item, "<answer>0</answer>")["reward"] == 1 and v.score(item, "<answer>०</answer>")["reward"] == 1


def test_a_leak_in_the_prompt_is_found_in_any_script_and_with_leading_zeros():
    for shown in ("40", "४०", "৪০", "040"):
        assert v.answer_in_prompt(f"कुल {shown} आम", "integer", [40]), shown


def test_digits_of_two_scripts_in_one_number_score_zero():
    assert score("hi_mango_count", "<answer>4०</answer>")["reward"] == 0


def test_indian_and_western_grouping_both_work_and_bad_grouping_fails():
    for answer in ("305042", "3,05,042", "305,042", "३,०५,०४२"):
        assert score("hi_number_words", f"<answer>{answer}</answer>")["reward"] == 1, answer
    for answer in ("30,50,42", "3,050,42", "305 042"):
        assert score("hi_number_words", f"<answer>{answer}</answer>")["reward"] == 0, answer


def test_end_marks_quotes_and_spaces_are_ignored():
    for answer in ("शनिवार।", "  शनिवार  ", "“शनिवार”", "शनिवार."):
        assert score("hi_weekday_after", f"<answer>{answer}</answer>")["reward"] == 1, answer


def test_decomposed_text_equals_composed_text():
    composed = "ख़रीद"  # ख + nukta, composed form in the prompt
    assert v.normalise(unicodedata.normalize("NFD", composed)) == v.normalise(composed)
    nfd = unicodedata.normalize("NFD", "শনিবার")
    assert v.normalise(nfd) == v.normalise("শনিবার")


def test_normalisation_is_nfc_not_nfkc():
    # NFKC would turn superscript two into "2" and fullwidth a into "a"; NFC keeps both.
    assert v.normalise("x\u00b2") == "x\u00b2" and v.normalise("\uff41") == "\uff41"
    item = v.prepare({"id": "nfc", "answer_type": "text", "script": "Latn"}, ["a2"])
    assert v.score(item, "<answer>\uff41\u00b2</answer>")["reward"] == 0


def test_latin_letters_are_case_folded():
    assert v.normalise("ABC Def") == "abc def"
    item = v.prepare({"id": "fold", "answer_type": "choice", "script": "Latn"}, ["B"])
    assert v.score(item, "<answer>b</answer>")["reward"] == 1 and v.score(item, "<answer>c</answer>")["reward"] == 0


def test_zero_width_space_and_bom_are_removed_but_zwj_and_zwnj_are_kept():
    assert v.normalise("\ufeffशनि\u200bवार") == "शनिवार"
    assert v.normalise("क्\u200dष") != v.normalise("क्ष")
    assert v.normalise("क्\u200cष") != v.normalise("क्ष")


def test_a_text_answer_in_the_wrong_script_scores_zero():
    r = score("hi_weekday_after", "<answer>Shanivar</answer>")
    assert r["reward"] == 0 and r["reason"] == "answer is not in the task's script"
    assert score("te_passage_who", "<answer>Sita</answer>")["reason"] == "answer is not in the task's script"


def test_every_accepted_variant_scores_one():
    assert score("te_passage_who", "<answer>సీతతో</answer>")["reward"] == 1


def test_a_choice_needs_the_right_label():
    assert score("bn_largest_choice", "<answer>(খ)</answer>")["reward"] == 1
    assert score("bn_largest_choice", "<answer>৫০২</answer>")["reward"] == 0


def test_score_works_on_a_prepared_item_without_a_folder():
    item = v.prepare({"id": "gen-1", "answer_type": "integer", "script": "Deva"}, [7])
    assert v.score(item, "<answer>७</answer>")["reward"] == 1
    assert v.score(item, "<answer>8</answer>")["reward"] == 0


# --- task lint ---------------------------------------------------------------------------------

def _copy(tmp_path: Path, name: str = "hi_mango_count") -> Path:
    d = tmp_path / name
    shutil.copytree(task(name), d)
    return d


def _edit(path: Path, **changes) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(changes)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_lint_catches_an_answer_in_the_prompt(tmp_path):
    d = _copy(tmp_path)
    (d / "prompt.md").write_text("सीमा के पास ४० आम हैं। <answer>संख्या</answer>", encoding="utf-8")
    assert any("appears in prompt.md" in p for p in v.check_task(d))


def test_lint_catches_a_text_answer_in_the_prompt_unless_it_is_a_span_task(tmp_path):
    d = _copy(tmp_path, "hi_weekday_after")
    (d / "prompt.md").write_text("आज शनिवार है? <answer>वार</answer>", encoding="utf-8")
    assert any("appears in prompt.md" in p for p in v.check_task(d))
    _edit(d / "task.json", answer_in_prompt=True)
    assert v.check_task(d) == []


def test_lint_catches_a_wrong_answer_that_is_also_accepted(tmp_path):
    d = _copy(tmp_path)
    _edit(d / "answer.json", wrong=[40])
    assert any("both accepted and wrong" in p for p in v.check_task(d))


def test_lint_needs_wrong_answers_and_int_answers_for_integer_tasks(tmp_path):
    d = _copy(tmp_path)
    _edit(d / "answer.json", wrong=[])
    assert any("wrong must be" in p for p in v.check_task(d))
    _edit(d / "answer.json", accepted=["40"], wrong=[22])
    assert any("accepted must be" in p for p in v.check_task(d))
    _edit(d / "answer.json", accepted=[True], wrong=[22])
    assert any("accepted must be" in p for p in v.check_task(d))


def test_lint_catches_an_accepted_text_answer_in_another_script(tmp_path):
    d = _copy(tmp_path, "hi_weekday_after")
    _edit(d / "answer.json", accepted=["शनिवार", "Saturday"], wrong=["शुक्रवार"])
    assert any("outside the task's script" in p for p in v.check_task(d))


def test_lint_catches_a_choice_answer_that_is_not_an_option(tmp_path):
    d = _copy(tmp_path, "bn_largest_choice")
    _edit(d / "answer.json", accepted=["ঙ"])
    assert any("not one of the choices" in p for p in v.check_task(d))


def test_lint_requires_the_answer_tag_in_the_prompt(tmp_path):
    d = _copy(tmp_path)
    (d / "prompt.md").write_text("सीमा के पास कितने आम हैं?", encoding="utf-8")
    assert any("<answer>" in p for p in v.check_task(d))


def test_lint_rejects_a_train_task_written_by_a_model_or_without_a_reviewer(tmp_path):
    d = _copy(tmp_path)
    _edit(d / "task.json", eligibility="train")
    problems = v.check_task(d)
    assert any("names a model" in p for p in problems) and any("team2_reviewer" in p for p in problems)
    _edit(d / "task.json", source="original: written by gmrammohan15, 2026-11-16", team2_reviewer="gmrammohan15")
    assert any("team2_reviewer" in p for p in v.check_task(d))
    _edit(d / "task.json", team2_reviewer="mittalutkarsh")
    assert v.check_task(d) == []


def test_lint_catches_a_folder_name_that_differs_from_the_id(tmp_path):
    d = _copy(tmp_path)
    d.rename(tmp_path / "other_name")
    assert any("differs from the folder name" in p for p in v.check_task(tmp_path / "other_name"))


def test_task_cache_sees_an_edited_answer(tmp_path):
    d = _copy(tmp_path)
    assert v.reward(d, "<answer>40</answer>")["reward"] == 1
    _edit(d / "answer.json", accepted=[41], wrong=[40])
    assert v.reward(d, "<answer>40</answer>")["reward"] == 0


# --- CLI ---------------------------------------------------------------------------------------

def test_cli_reward_check_all_and_missing_folder(tmp_path):
    f = tmp_path / "c.txt"
    f.write_text(CASES["hi_mango_count"][0], encoding="utf-8")
    cli = [sys.executable, str(HERE / "indic_verifier.py")]
    out = subprocess.run(cli + ["--reward", str(task("hi_mango_count")), str(f)], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout)["reward"] == 1
    assert subprocess.run(cli + ["--check-all"], capture_output=True, check=False).returncode == 0
    assert subprocess.run(cli + ["--check-task", str(tmp_path / "nope")], capture_output=True, check=False).returncode == 2


def test_bench_scores_every_correct_case_and_no_wrong_case():
    r = v.bench(n=1200)
    assert r["rewards"] == 600 and r["per_second"] > 0
