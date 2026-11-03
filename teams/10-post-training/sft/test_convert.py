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


def one(set_id: str, row: dict) -> tuple[dict, dict]:
    lines, manifest = convert.convert(set_id, [row], None, None)
    assert len(lines) == 1, manifest["skipped"]
    return json.loads(lines[0]), manifest


def trained_text(sample: dict) -> list[str]:
    return [sample["text"][s:e] for s, e in sample["train_spans"]]


@pytest.mark.parametrize("set_id,row", [
    ("sft-code-commitpackft", COMMITPACK),
    ("sft-code-codeforces-cots", CODEFORCES),
    ("sft-code-swe-rebench-openhands", SWE),
    ("sft-indic-aya-dataset", AYA),
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
