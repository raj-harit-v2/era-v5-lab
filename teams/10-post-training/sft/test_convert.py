"""Tests for sft/convert.py. Fixture rows are hand-written in each set's schema (no real data)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("g10_convert", HERE / "convert.py")
assert spec is not None and spec.loader is not None
convert = importlib.util.module_from_spec(spec)
spec.loader.exec_module(convert)
render, T = convert.render, convert.T

# A named decorator: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize


COMMITPACK = {"commit": "c7", "instruction": "Write add(a, b).", "response": "def add(a, b):\n    return a + b\n"}
SELF_OSS = COMMITPACK
CODEFORCES = {
    "id": "1/A", "finish_reason": "stop",
    "messages": [
        {"role": "user", "content": "Print the sum of two numbers."},
        {"role": "assistant", "content": "<think>\nRead two ints, print a+b.\n</think>\n\nprint(sum(map(int, input().split())))"},
    ],
}
SWE = {
    "trajectory_id": "t1", "resolved": 1,
    "tools": [{"type": "function", "function": {"name": "bash", "parameters": {"type": "object"}}}],
    "trajectory": [
        {"role": "system", "content": "You are an agent.", "tool_calls": None},
        {"role": "user", "content": "Fix slugify.", "tool_calls": None},
        {"role": "assistant", "content": "Look first.",
         "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "bash", "arguments": "{\"command\": \"cat slug.py\"}"}}]},
        {"role": "tool", "content": "def slugify(s): ...", "tool_call_id": "c1", "tool_calls": None},
        {"role": "assistant", "content": "Done.", "tool_calls": None},
    ],
}
AYA = {"inputs": "नमस्ते​?", "targets": "क्‍ष और क्‌ष﻿", "language_code": "hin"}
INDIC_ALIGN = {
    "doc_id": "d1", "num_turns": 2,
    "eng_Latn": [["Hi?", "Hello."], ["Why?", "Because."]],
    "hin_Latn": [["Hello.", "Hi?"], ["Because.", "Why?"]],
    **{col: [[f"{col} प्रश्न​", f"{col} क्‍ष﻿"], [f"{col} फिर?", f"{col} क्‌ष"]]
       for col in convert.INDIC_ALIGN_COLUMNS},
}

NEMOTRON_TOOLS = {
    "uuid": "u1",
    "tools": [{"type": "function", "function": {"name": "get_balance", "parameters": {"type": "object"}}}],
    "messages": [
        {"role": "system", "content": ""},
        {"role": "user", "content": "Balance of address A?"},
        {"role": "assistant", "content": "", "reasoning_content": "Call the tool.",
         "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "get_balance", "arguments": {"address": "A"}}}]},
        {"role": "tool", "content": {"balance": "0.1"}, "tool_call_id": "c1"},
        {"role": "assistant", "content": "It is 0.1.", "tool_calls": None, "reasoning_content": "Report it."},
    ],
}
NEMOTRON_MATH = {
    "uuid": "m1", "tools": [],
    "messages": [
        {"role": "user", "content": "What is 1+1?", "reasoning_content": None, "tool_calls": []},
        {"role": "assistant", "content": "2", "reasoning_content": "Add.", "tool_calls": []},
    ],
}
CASCADE = {"messages": [{"role": "user", "content": "Fix the bug. Reply in a <think> and </think> block."},
                        {"role": "assistant", "content": "<think>\nLook at the diff.\n</think>\nPatch applied."}]}
OPENCODE = {"id": "o1", "input": "Sum two ints.", "output": "<think>\nRead, add.\n</think>\n\nprint(a + b)"}
DOLLY = {"instruction": "Name a colour.", "context": "Think of the sky.", "response": "Blue."}


OMR = {"problem": "2+2?", "inference_mode": "cot", "generated_solution": "<think>\nAdd.\n</think>\n\\boxed{4}"}
OPENR1_RAW = {"problem": "2+2?", "generations": ["<think>\nAdd.\n</think>\nFour."],
              "correctness": {"llama_verification": [True]}}
OT3 = {"conversations": [{"from": "human", "value": "Sum?"}, {"from": "gpt", "value": "<think> Add them. </think> The sum."}]}
OCR2 = {"id": "q1", "question": "Print 1.", "r1_generation": "<think>\nprint it\n</think>\nprint(1)"}
OPENR1 = {"uuid": "r1", "messages": CASCADE["messages"]}


BESPOKE = {"system": "Think first.", "conversations": [
    {"from": "user", "value": "2+2?"},
    {"from": "assistant", "value": "<|begin_of_thought|>\n\nAdd.\n\n<|end_of_thought|>\n\n<|begin_of_solution|>\n\n4\n\n<|end_of_solution|>"}]}
SWE_ZERO = {"trajectory_id": "z1", "model_patch": "diff --git a/x b/x",
            "trajectory": [dict(m, tool_calls=m.get("tool_calls")) for m in SWE["trajectory"]]}
TERMINAL = {"conversations": [{"role": "user", "content": "ls?"},
                              {"role": "assistant", "content": "<think>\nList.\n</think>\nls -la"}]}


OASST_THREAD = {"id": "t1", "lang": "en", "messages": [
    {"role": "user", "text": "Hi?"}, {"role": "assistant", "text": "Hello."}, {"role": "user", "text": "Bye?"},
    {"role": "assistant", "text": "Bye."}]}


AYA_COLLECTION = {"id": 1, "inputs": "ఈ రిడిల్ కి జవాబు ఇవ్వు​", "targets": "సమాధానం", "language": "tel"}


def one(set_id: str, row: dict) -> tuple[dict, dict]:
    lines, manifest = convert.convert(set_id, [row], None, None)
    assert len(lines) == 1, manifest["skipped"]
    return json.loads(lines[0]), manifest


def trained_text(sample: dict) -> list[str]:
    return [sample["text"][s:e] for s, e in sample["train_spans"]]


@parametrize("set_id,row", [
    ("sft-code-commitpackft", COMMITPACK),
    ("sft-code-codeforces-cots", CODEFORCES),
    ("sft-code-swe-rebench-openhands", SWE),
    ("sft-indic-aya-dataset", AYA),
    ("sft-indic-indic-align-oasst-t", INDIC_ALIGN),
    ("sft-code-nemotron-cuda", NEMOTRON_TOOLS),
    ("sft-agentic-nemotron-agentic-v1", NEMOTRON_TOOLS),
    ("sft-agentic-nemotron-sft-agentic-v2-tool-calling", NEMOTRON_TOOLS),
    ("sft-math-nemotron-math-v2", NEMOTRON_MATH),
    ("sft-code-nemotron-cascade-swe", CASCADE),
    ("sft-code-opencodereasoning", OPENCODE),
    ("sft-dolly-15k", DOLLY),
    ("sft-math-nemotron-sft-math-v4", NEMOTRON_MATH),
    ("sft-rl-math-openmathreasoning", OMR),
    ("sft-math-openr1-math", OPENR1),
    ("sft-math-openr1-math-raw", OPENR1_RAW),
    ("sft-stem-code-openthoughts3", OT3),
    ("sft-code-opencodereasoning-2", OCR2),
    ("sft-science-nemotron-science", NEMOTRON_MATH),
    ("sft-chat-nemotron-if-v1", NEMOTRON_MATH),
    ("sft-chat-nemotron-if-v2", NEMOTRON_TOOLS),
    ("sft-math-nemotron-proofs", NEMOTRON_MATH),
])
def test_every_adapter_renders_and_parses_back(set_id, row):
    sample, manifest = one(set_id, row)
    adapter = convert.ADAPTERS[set_id][0]
    assert sample["text"] == render.render(adapter(row), sample["effort"])
    assert render.parse(sample["text"])["effort"] == sample["effort"]
    assert manifest["rows"] == manifest["rows_in"] == 1


def test_mask_trains_assistant_bodies_and_im_end_only():
    sample, _ = one("sft-code-swe-rebench-openhands", SWE)
    text, spans = sample["text"], trained_text(sample)
    assert len(spans) == 2
    assert spans[0].startswith(f"{T['tool_call']}\n") and spans[0].endswith(f"Look first.{T['im_end']}")
    assert spans[1] == f"Done.{T['im_end']}"
    untrained = text
    for piece in spans:
        untrained = untrained.replace(piece, "", 1)
    # prompt side: system with effort line and tools, user, tool result, headers, endoftext
    for needle in ("Reasoning effort:", "Tools:", "Fix slugify.", T["tool_result"], "def slugify", T["endoftext"]):
        assert needle in untrained and all(needle not in piece for piece in spans)


def test_codeforces_think_goes_in_the_think_span():
    sample, _ = one("sft-code-codeforces-cots", CODEFORCES)
    (body,) = trained_text(sample)
    assert body == f"{T['think']}\nRead two ints, print a+b.\n{T['think_end']}\nprint(sum(map(int, input().split()))){T['im_end']}"
    assert "<think>" not in sample["text"]


def test_codeforces_unfinished_or_unsplittable_rows_are_skipped_with_reason():
    rows = [dict(CODEFORCES, finish_reason="length"),
            dict(CODEFORCES, messages=[CODEFORCES["messages"][0], {"role": "assistant", "content": "no think"}]),
            dict(CODEFORCES, messages=[CODEFORCES["messages"][0],
                                       {"role": "assistant", "content": "<think>a</think> b <think>c</think>"}])]
    lines, manifest = convert.convert("sft-code-codeforces-cots", rows, None, None)
    assert lines == [] and manifest["rows_in"] == 3
    assert manifest["skipped"] == {
        "generation did not finish (finish_reason != stop)": 1,
        "assistant turn does not start with one <think>...</think> block": 1,
        "content contains plain-text marker <think>; every chat marker must be one special token": 1,
    }


def test_swe_unresolved_trajectory_is_skipped():
    lines, manifest = convert.convert("sft-code-swe-rebench-openhands", [dict(SWE, resolved=0)], None, None)
    assert lines == [] and manifest["skipped"] == {"trajectory did not resolve the issue (resolved != 1)": 1}


def test_aya_keeps_zwj_zwnj_strips_zwsp_bom_and_selects_indic_only():
    rows = [dict(AYA, language_code="yor"), AYA]
    lines, manifest = convert.convert("sft-indic-aya-dataset", rows, None, None)
    assert manifest["rows_scanned"] == 2 and manifest["rows_in"] == 1 and len(lines) == 1
    sample = json.loads(lines[0])
    assert sample["id"] == "sft-indic-aya-dataset/1"
    assert "‍" in sample["text"] and "‌" in sample["text"]
    assert "​" not in sample["text"] and "﻿" not in sample["text"]


def test_indic_align_takes_one_native_column_per_doc_id_and_keeps_turn_order():
    col = convert.indic_align_column("d1")
    assert col in convert.INDIC_ALIGN_COLUMNS and convert.indic_align_column("d1") == col
    sample, manifest = one("sft-indic-indic-align-oasst-t", INDIC_ALIGN)
    assert sample["source_id"] == "d1"
    assert trained_text(sample) == [f"{col} क्‍ष{T['im_end']}", f"{col} क्‌ष{T['im_end']}"]
    assert f"{col} प्रश्न" in sample["text"] and f"{col} फिर?" in sample["text"]
    assert "​" not in sample["text"] and "Hello." not in sample["text"]
    others = [c for c in convert.INDIC_ALIGN_COLUMNS if c != col]
    assert all(f"{c} " not in sample["text"] for c in others)
    assert manifest["source"] == "ai4bharat/indic-align" and "IndicTrans2" in manifest["generator_model"]
    # ids spread over the ten languages instead of copying one conversation ten times
    assert len({convert.indic_align_column(f"doc-{i}") for i in range(200)}) == 10


def test_indic_align_thread_ending_on_user_drops_that_turn():
    col = convert.indic_align_column("d1")
    row = dict(INDIC_ALIGN, **{col: [["प्रश्न", "उत्तर", "धन्यवाद, और?"]]})
    sample, _ = one("sft-indic-indic-align-oasst-t", row)
    assert trained_text(sample) == [f"उत्तर{T['im_end']}"] and "धन्यवाद" not in sample["text"]


def test_indic_align_rows_that_do_not_alternate_are_skipped():
    col = convert.indic_align_column("d1")
    rows = [dict(INDIC_ALIGN, **{col: [["only one"]]}), dict(INDIC_ALIGN, **{col: []}),
            dict(INDIC_ALIGN, **{col: [["q", "a", "q"], ["q", "a"]]})]
    lines, manifest = convert.convert("sft-indic-indic-align-oasst-t", rows, None, None)
    assert lines == [] and manifest["skipped"] == {"translated turns do not alternate user, assistant": 3}


def test_effort_is_smallest_budget_holding_think_and_tool_trace():
    def row(think_chars: int) -> dict:
        reply = "<think>" + "x" * think_chars + "</think>answer"
        return dict(CODEFORCES, messages=[CODEFORCES["messages"][0], {"role": "assistant", "content": reply}])

    # trace = "<|think|>\n" + think + "\n<|/think|>" counted as UTF-8 bytes / 4
    markers = len(f"{T['think']}\n\n{T['think_end']}".encode())
    budgets = {"1k": 1024, "4k": 4096, "16k": 16384, "64k": 65536}
    for effort, budget in budgets.items():
        sample, _ = one("sft-code-codeforces-cots", row(4 * budget - markers))
        assert sample["effort"] == effort
    lines, manifest = convert.convert("sft-code-codeforces-cots", [row(4 * 65536)], None, None)
    assert lines == [] and manifest["skipped"] == {"trace over the 64k effort budget": 1}


def test_no_trace_is_1k_and_reply_text_is_not_counted():
    sample, _ = one("sft-code-commitpackft", dict(COMMITPACK, response="y" * 100_000))
    assert sample["effort"] == "1k"


def test_token_mask_trains_only_tokens_fully_inside_a_span():
    spans = [(5, 10), (20, 25)]
    offsets = [(0, 5), (5, 8), (8, 10), (10, 12), (9, 11), (19, 21), (20, 25), (25, 25), (7, 7)]
    assert convert.token_mask(spans, offsets) == [0, 1, 1, 0, 0, 0, 1, 0, 0]


def test_manifest_reads_licence_table_and_hash_is_stable():
    a_lines, a = convert.convert("sft-code-commitpackft", [COMMITPACK, COMMITPACK], None, None)
    b_lines, b = convert.convert("sft-code-commitpackft", [COMMITPACK, COMMITPACK], None, None)
    assert a_lines == b_lines and a["content_sha256"] == b["content_sha256"]
    assert a["source"] == "bigcode/commitpackft"
    assert a["licence"].startswith("mit") and a["decision"] == "TSAI reserves"
    assert "commits" in a["generator_model"]
    assert a["rows"] == 2 and a["effort"] == {"1k": 2, "4k": 0, "16k": 0, "64k": 0}
    assert "estimate" in a["effort_counter"]


def test_limit_counts_selected_rows():
    lines, manifest = convert.convert("sft-code-commitpackft", [COMMITPACK] * 5, 3, None)
    assert len(lines) == 3 and manifest["rows_in"] == 3


def test_excluded_or_unknown_sets_are_refused(tmp_path):
    table = tmp_path / "licence_table.md"
    table.write_text(
        "### Stage 1: SFT\n\n| Set | Source | Language | Generator model | Licence | Decision |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| sft-x | [a/b](https://x) | English | GPT-4 (OpenAI, closed) | mit | excluded |\n\n### Stage 2\n",
        encoding="utf-8",
    )
    row = convert.licence_row("sft-x", table)
    assert row["source"] == "a/b" and row["decision"] == "excluded"
    with pytest.raises(SystemExit):
        convert.check_allowed(row)
    with pytest.raises(SystemExit):
        convert.licence_row("sft-missing", table)
    # excluded sets in the real table are refused too (including StarCoder2 OpenRAIL-M)
    with pytest.raises(SystemExit):
        convert.check_allowed(convert.licence_row("sft-openhermes-2.5"))
    with pytest.raises(SystemExit):
        convert.check_allowed(convert.licence_row("sft-code-self-oss-instruct"))


def test_every_adapter_set_is_allowed_in_the_licence_table():
    for set_id in convert.ADAPTERS:
        convert.check_allowed(convert.licence_row(set_id))


def test_ids_stay_unique_when_the_source_repeats_its_ids():
    lines, _ = convert.convert("sft-code-codeforces-cots", [CODEFORCES, CODEFORCES], None, None, first_index=800)
    samples = [json.loads(line) for line in lines]
    assert [s["id"] for s in samples] == ["sft-code-codeforces-cots/800", "sft-code-codeforces-cots/801"]
    assert [s["source_id"] for s in samples] == ["1/A", "1/A"]


def test_bad_rows_are_skipped_not_fatal():
    rows = [{"instruction": "x"}, {"instruction": None, "response": "y"}, COMMITPACK,
            dict(COMMITPACK, response="")]
    lines, manifest = convert.convert("sft-code-commitpackft", rows, None, None)
    assert len(lines) == 1
    assert manifest["skipped"] == {"missing or malformed field (KeyError)": 1,
                                   "empty user turn": 1, "empty assistant turn": 1}


def test_tokenizer_path_writes_ids_and_mask(tmp_path):
    tokenizers = pytest.importorskip("tokenizers")
    tok = tokenizers.Tokenizer(tokenizers.models.BPE(unk_token=None))
    tok.pre_tokenizer = tokenizers.pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = tokenizers.decoders.ByteLevel()
    trainer = tokenizers.trainers.BpeTrainer(
        vocab_size=400, special_tokens=list(T.values()),
        initial_alphabet=tokenizers.pre_tokenizers.ByteLevel.alphabet())
    tok.train_from_iterator(["def add(a, b): return a + b", "Write add."], trainer)
    path = tmp_path / "tokenizer.json"
    tok.save(str(path))
    lines, manifest = convert.convert("sft-code-swe-rebench-openhands", [SWE], None, str(path))
    sample = json.loads(lines[0])
    assert tok.decode(sample["input_ids"], skip_special_tokens=False) == sample["text"]
    assert len(sample["loss_mask"]) == len(sample["input_ids"]) == manifest["tokens"]
    assert sum(sample["loss_mask"]) == manifest["trained_tokens"] > 0
    ids = dict(zip(sample["input_ids"], sample["loss_mask"]))
    im_end, tool_result = tok.token_to_id(T["im_end"]), tok.token_to_id(T["tool_result"])
    assert ids[tool_result] == 0
    trained_ends = [m for i, m in zip(sample["input_ids"], sample["loss_mask"]) if i == im_end]
    assert trained_ends.count(1) == 2  # the two assistant turns; system, user and tool ends stay 0
    assert manifest["effort_counter"].startswith("tokenizer sha256 ")


def test_hf_rows_refuses_a_page_from_the_wrong_offset(monkeypatch):
    class Page:
        def __init__(self, body): self.body = body
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, *a): return self.body

    body = json.dumps({"rows": [{"row_idx": 700, "row": {}, "truncated_cells": []}]}).encode()
    monkeypatch.setattr(convert.urllib.request, "urlopen", lambda *a, **k: Page(body))
    with pytest.raises(RuntimeError, match="got row_idx 700"):
        list(convert.hf_rows("a/b", "default", "train", 800, 1))


def test_nemotron_chat_drops_empty_system_keeps_think_and_tool_turn():
    sample, _ = one("sft-agentic-nemotron-agentic-v1", NEMOTRON_TOOLS)
    assert "Tools:" in sample["text"] and "get_balance" in sample["text"]
    assert '"balance": "0.1"' in sample["text"]
    spans = trained_text(sample)
    assert spans[0].startswith(T["think"]) and "Call the tool." in spans[0]
    assert spans[-1].endswith(f"It is 0.1.{T['im_end']}")


def test_nemotron_chat_fills_empty_tool_turn():
    row = json.loads(json.dumps(NEMOTRON_TOOLS))
    row["messages"][3]["content"] = ""
    sample, _ = one("sft-code-nemotron-cuda", row)
    assert "(no output)" in sample["text"]


def test_cascade_and_opencode_think_blocks_go_to_think_span():
    for set_id, row, thought in (("sft-code-nemotron-cascade-swe", CASCADE, "Look at the diff."),
                                 ("sft-code-opencodereasoning", OPENCODE, "Read, add.")):
        sample, _ = one(set_id, row)
        assert thought in trained_text(sample)[0] and "<think>" not in sample["text"]


def test_opencode_without_think_is_skipped():
    lines, manifest = convert.convert("sft-code-opencodereasoning", [dict(OPENCODE, output="print(a)")], None, None)
    assert lines == [] and list(manifest["skipped"]) == ["output does not start with one <think>...</think> block"]


def test_dolly_t_keeps_only_questions_that_had_no_context(monkeypatch):
    source = [{"instruction": "Hi? ", "context": "", "response": "x"},
              {"instruction": "Summarise this.", "context": "A passage.", "response": "y"}]
    monkeypatch.setattr(convert, "_dolly_no_context", None)
    monkeypatch.setattr(convert, "hf_file_rows", lambda ds, path, off, n: iter(source))
    assert convert.dolly_no_context_questions() == frozenset({"Hi?"})
    had_context = dict(INDIC_ALIGN, doc_id="d2", eng_Latn=[["Summarise this.", "Short."]])
    not_in_dolly = dict(INDIC_ALIGN, doc_id="d3", eng_Latn=[["Unknown question?", "No."]])
    lines, manifest = convert.convert("sft-indic-indic-align-dolly-t", [INDIC_ALIGN, had_context, not_in_dolly], None, None)
    assert manifest["rows_scanned"] == 3 and manifest["rows_in"] == 1 and len(lines) == 1
    assert json.loads(lines[0])["source_id"] == "d1"
    assert "no context passage" in manifest["selection"]


def test_indic_align_sets_read_hub_files_so_the_pipeline_can_run_them():
    for set_id in ("sft-indic-indic-align-oasst-t", "sft-indic-indic-align-dolly-t"):
        assert convert.ADAPTERS[set_id][2][0] == "file"


def test_dolly_puts_context_after_instruction():
    sample, _ = one("sft-dolly-15k", DOLLY)
    assert "Name a colour.\n\nThink of the sky." in sample["text"]


def test_cascade_prompt_tag_names_are_bracketed():
    sample, _ = one("sft-code-nemotron-cascade-swe", CASCADE)
    assert "Reply in a [think] and [/think] block." in sample["text"]


@parametrize("set_id,row,reason", [
    ("sft-rl-math-openmathreasoning", dict(OMR, inference_mode="tir"), "tool-integrated (non-cot) solution"),
    ("sft-code-opencodereasoning-2", dict(OCR2, question="-"), "question is withheld upstream (stored as '-')"),
    ("sft-math-nemotron-proofs", {"uuid": "p", "messages": []}, "row has no messages (statement only)"),
    ("sft-math-openr1-math-raw", dict(OPENR1_RAW, generations=["no think"]),
     "first generation does not start with one <think>...</think> block"),
])
def test_new_adapters_skip_with_reason(set_id, row, reason):
    lines, manifest = convert.convert(set_id, [row], None, None)
    assert lines == [] and manifest["skipped"] == {reason: 1}


def test_openthoughts_think_with_inline_spaces():
    sample, _ = one("sft-stem-code-openthoughts3", OT3)
    assert "Add them." in trained_text(sample)[0] and "The sum." in trained_text(sample)[0]


def test_bespoke_thought_and_solution_blocks_split():
    sample, _ = one("sft-bespoke-stratos-17k", BESPOKE)
    assert "<|begin_of" not in sample["text"].replace(T["think"], "") and "Think first." not in sample["text"]
    assert trained_text(sample)[0] == f"{T['think']}\nAdd.\n{T['think_end']}\n4{T['im_end']}"


def test_swe_zero_without_patch_is_skipped():
    lines, manifest = convert.convert("sft-code-swe-zero-openhands", [dict(SWE_ZERO, model_patch="")], None, None)
    assert lines == [] and manifest["skipped"] == {"trajectory has no model_patch": 1}


def test_oasst2_thread_must_end_on_assistant():
    row = dict(OASST_THREAD, messages=OASST_THREAD["messages"][:3])
    lines, manifest = convert.convert("sft-oasst2", [row], None, None)
    assert lines == [] and manifest["skipped"] == {"thread does not end on an assistant reply": 1}


def _msg(mid, parent, role, text, rank=None, **kw):
    return dict({"message_id": mid, "parent_id": parent, "role": role, "text": text, "rank": rank, "lang": "en",
                 "deleted": False, "synthetic": False, "tree_state": "ready_for_export"}, **kw)


def test_oasst2_build_follows_best_ranked_reply_and_drops_bad_rows():
    rows = [_msg("p", None, "prompter", "Q"),
            _msg("a1", "p", "assistant", "second", rank=1), _msg("a0", "p", "assistant", "best", rank=0),
            _msg("a2", "p", "assistant", "gone", rank=0, deleted=True),
            _msg("u1", "a0", "prompter", "more?", rank=0), _msg("a3", "u1", "assistant", "yes", rank=0),
            _msg("x", None, "prompter", "unexported", tree_state="growing"),
            _msg("s", None, "prompter", "synthetic", synthetic=True)]
    (thread,) = list(convert.oasst2_build(rows, 0, 10))
    assert [m["text"] for m in thread["messages"]] == ["Q", "best", "more?", "yes"]
    assert thread["id"] == "p"


def test_aya_collection_strips_zero_width_space_and_skips_empty_targets():
    sample, _ = one("sft-indic-aya-collection", AYA_COLLECTION)
    assert "\u200b" not in sample["text"]
    lines, manifest = convert.convert("sft-indic-aya-collection", [dict(AYA_COLLECTION, targets=" ")], None, None)
    assert lines == [] and manifest["skipped"] == {"empty input or target": 1}


def test_convert_streams_to_a_sink_with_the_same_manifest(tmp_path):
    rows = [COMMITPACK, dict(COMMITPACK, response="x = 1\n")]
    lines, manifest = convert.convert("sft-code-commitpackft", rows, None, None)
    with open(tmp_path / "out.jsonl", "w", encoding="utf-8", newline="") as sink:
        none, streamed = convert.convert("sft-code-commitpackft", rows, None, None, 0, sink)
    assert none == [] and (tmp_path / "out.jsonl").read_text(encoding="utf-8") == "".join(lines)
    assert streamed == manifest


def test_multi_file_rows_are_counted_across_files(monkeypatch):
    files = {"a": [{"i": 0}, {"i": 1}], "b": [{"i": 2}, {"i": 3}]}
    monkeypatch.setattr(convert, "_one_file_rows", lambda ds, p, off, n: iter(files[p][off:off + n]))

    def got(off, n):
        return [r["i"] for r in convert.hf_file_rows("x/y", "a|b", off, n)]

    assert got(0, 10) == [0, 1, 2, 3] and got(1, 2) == [1, 2] and got(0, 3) == [0, 1, 2]


def test_file_rows_resume_after_a_connection_reset(monkeypatch):
    calls = []

    def flaky(ds, p, off, n):
        calls.append(off)
        for i in range(off, 5):
            if len(calls) == 1 and i == 3:
                raise ConnectionResetError("reset")
            yield {"i": i}

    monkeypatch.setattr(convert, "_one_file_rows", flaky)
    monkeypatch.setattr(convert.time, "sleep", lambda s: None)
    assert [r["i"] for r in convert.hf_file_rows("x/y", "a", 0, 100)] == [0, 1, 2, 3, 4]
    assert calls == [0, 3]


def test_rolling_sink_writes_whole_parts(tmp_path):
    sink = convert.RollingSink(tmp_path / "set", 0.00005)  # 50 bytes
    for i in range(7):
        sink.write(json.dumps({"id": i}) + "\n")
    assert not list(tmp_path.glob("*.tmp")) or len(list(tmp_path.glob("*.tmp"))) <= 1
    sink.close()
    parts = sorted(tmp_path.glob("set.part*.jsonl"))
    assert len(parts) > 1 and not list(tmp_path.glob("*.tmp"))
    assert [json.loads(ln)["id"] for p in parts for ln in p.read_text().splitlines()] == list(range(7))


def test_progress_callback_and_index_base():
    seen = []
    rows = [{"instruction": f"q{i}", "context": "", "response": f"a{i}", "category": "x"} for i in range(1500)]
    lines, manifest = convert.convert("sft-dolly-15k", rows, None, None, first_index=5_000, progress=lambda s, w: seen.append((s, w)))
    assert json.loads(lines[0])["id"] == "sft-dolly-15k/5000" and json.loads(lines[-1])["id"] == "sft-dolly-15k/6499"
    assert manifest["rows"] == 1500 and (not seen or seen[-1][0] <= 1500)


def test_openr1_raw_keeps_only_rows_whose_first_generation_passed():
    select = convert.ADAPTERS["sft-math-openr1-math-raw"][3]
    assert select({"correctness": {"llama_verification": [True, False]}})
    assert not select({"correctness": {"llama_verification": [False, True]}})
    assert not select({"correctness": {}}) and not select({})


def test_full_set_sources_of_the_five_sets():
    spec = {s: convert.ADAPTERS[s][2][1] for s in ("sft-code-nemotron-cascade-swe", "sft-code-opencodereasoning",
                                                   "sft-math-openr1-math", "sft-math-openr1-math-raw")}
    assert spec["sft-code-nemotron-cascade-swe"].count("|") == 2
    assert spec["sft-code-opencodereasoning"] == "glob:split_0/" and spec["sft-math-openr1-math"] == "glob:all/train-"
    assert spec["sft-math-openr1-math-raw"] == "glob:data/"


def test_full_set_sources_of_swe_zero_and_the_two_jsonl_sets():
    assert convert.ADAPTERS["sft-code-swe-zero-openhands"][2][1] == "glob:data/"
    assert convert.ADAPTERS["sft-chat-nemotron-if-v2"][2][1] == "data/reasoning_on.jsonl"
    assert convert.ADAPTERS["sft-agentic-nemotron-sft-agentic-v2-tool-calling"][2][1] == "data/tool_calling.jsonl"


def test_full_set_sources_of_the_three_downloaded_math_sets():
    assert convert.ADAPTERS["sft-math-nemotron-math-v2"][2][1] == "glob:data/*.parquet"
    assert convert.ADAPTERS["sft-rl-math-openmathreasoning"][2][1] == "glob:data/cot-"
    assert convert.ADAPTERS["sft-math-nemotron-proofs"][2][1] == "data/lean.jsonl"


def test_local_copy_of_a_repo_is_read_instead_of_the_hub(tmp_path, monkeypatch):
    pq = pytest.importorskip("pyarrow.parquet")
    import pyarrow as pa

    data = tmp_path / "org" / "repo" / "data"
    data.mkdir(parents=True)
    pq.write_table(pa.table({"a": [1, 2, 3]}), data / "x-0.parquet")
    pq.write_table(pa.table({"a": [4, 5]}), data / "x-1.parquet")
    (data / "x-2.jsonl").write_text('{"a": 6}\n{"a": 7}', encoding="utf-8")  # last line without a newline
    (data / "other.parquet").write_bytes(b"")
    monkeypatch.setenv("G10_LOCAL_ROOT", str(tmp_path))
    assert convert.expand_paths("org/repo", "glob:data/x-") == ["data/x-0.parquet", "data/x-1.parquet", "data/x-2.jsonl"]
    assert convert.expand_paths("org/repo", "glob:data/*.jsonl") == ["data/x-2.jsonl"]
    rows = list(convert.hf_file_rows("org/repo", "glob:data/x-", 0, 100))
    assert [r["a"] for r in rows] == [1, 2, 3, 4, 5, 6, 7]
    assert [r["a"] for r in convert.hf_file_rows("org/repo", "glob:data/x-", 2, 3)] == [3, 4, 5]


def test_full_set_source_of_openthoughts3():
    assert convert.ADAPTERS["sft-stem-code-openthoughts3"][2][1] == "glob:data/*.parquet"


def test_full_set_source_of_proofs_v3_sft():
    assert convert.ADAPTERS["sft-math-nemotron-proofs-v3-sft"][2][1] == "glob:data/*.jsonl"


def test_xlam_row_becomes_one_tool_call_turn():
    row = {"id": 7, "query": "Q?", "tools": json.dumps([{"name": "f", "parameters": {}}]),
           "answers": json.dumps([{"name": "f", "arguments": {"x": 1}}])}
    m = convert.xlam_function_calling(row)
    assert [x["role"] for x in m] == ["system", "user", "assistant"]
    assert m[2]["tool_calls"][0]["function"] == {"name": "f", "arguments": {"x": 1}}
    assert m[0]["content"].startswith("Tools:\n")
    with pytest.raises(convert.Skip):
        convert.xlam_function_calling({**row, "answers": "[]"})
    with pytest.raises(convert.Skip):
        convert.xlam_function_calling({**row, "answers": "not json"})


def test_xlam_json_array_is_read_from_a_local_copy(tmp_path):
    f = tmp_path / "x.json"
    f.write_text(json.dumps([{"id": i} for i in range(5)]))
    assert [r["id"] for r in convert._local_file_rows(f, 1, 3)] == [1, 2, 3]


def test_commitpackft_reads_every_language_file_so_the_pipeline_can_run_it():
    assert convert.ADAPTERS["sft-code-commitpackft"][2] == ("file", "glob:data/*/data.jsonl")


def test_a_json_array_file_needs_a_local_copy(tmp_path, monkeypatch):
    monkeypatch.setenv("G10_LOCAL_ROOT", str(tmp_path))
    with pytest.raises(SystemExit, match="G10_LOCAL_ROOT"):
        list(convert._one_file_rows("org/repo", "x.json", 0, 5))
