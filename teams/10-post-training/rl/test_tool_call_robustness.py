"""Single-call boundary and mutation checks; follow-up to PR #109.

CPU-only verifier tests. Expected payloads stay in this test and temporary
hidden_tests.json files. Mutations affect temporary copies, never production.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
VERIFIER = HERE / "tool_call_verifier.py"
# Independent contract value: do not derive the size oracle from the verifier.
LIMIT = 65_536
EXPECTED = {
    "name": "fixture_lookup",
    "arguments": {
        "city": "München",
        "history": False,
        "options": {"labels": ["east", "west"], "limit": 3},
    },
}

# Named decorators match the existing tests and avoid the PR guard's email lint.
cases = pytest.mark.parametrize
fixture = pytest.fixture


def load_verifier(path):
    spec = importlib.util.spec_from_file_location("tool_call_robustness_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def block(payload):
    return "<|tool_call|>\n" + payload + "\n<|/tool_call|>"


def completion(call=None, **kwargs):
    return block(json.dumps(EXPECTED if call is None else call, ensure_ascii=False, **kwargs))


def changed_argument(key, value):
    call = copy.deepcopy(EXPECTED)
    call["arguments"][key] = value
    return completion(call)


def boundary_cases():
    """Input/expected-score pairs, independent of the production comparator."""
    good = completion()
    payload = json.dumps(EXPECTED, ensure_ascii=False)
    result = [
        ("correct", good, 1.0),
        ("key-order-and-whitespace", completion({
            "arguments": EXPECTED["arguments"], "name": EXPECTED["name"],
        }, indent=2), 1.0),
        ("unicode-escape-equivalence", block(json.dumps(EXPECTED, ensure_ascii=True)), 1.0),
        ("escaped-tool-name", block(payload.replace("fixture_lookup", r"fixture_\u006cookup")), 1.0),
        ("allowed-json-whitespace", "\t\r\n" + good + "\r\n\t", 1.0),
        ("optional-string-id", completion({**EXPECTED, "id": "fixture-1"}), 1.0),
        ("wrong-tool", completion({**EXPECTED, "name": "fixture_delete"}), 0.0),
        ("wrong-value", changed_argument("city", "Berlin"), 0.0),
        ("unicode-lookalike", changed_argument("city", "Münchеn"), 0.0),  # Cyrillic e
        ("unicode-normalization-is-not-implicit", changed_argument("city", "Mu\u0308nchen"), 0.0),
        ("boolean-is-not-zero", changed_argument("history", 0), 0.0),
        ("array-order-matters", changed_argument("options", {
            "labels": ["west", "east"], "limit": 3,
        }), 0.0),
        ("empty", "", 0.0),
        ("plain-reply", "I found the requested information.", 0.0),
        ("missing-markers", payload, 0.0),
        ("quoted-call", "Example only:\n" + good, 0.0),
        ("multiple-calls", good + good, 0.0),
        ("duplicate-top-level", block(payload.replace(
            '"name": "fixture_lookup"', '"name": "wrong", "name": "fixture_lookup"',
        )), 0.0),
        ("duplicate-argument", block(payload.replace(
            '"history": false', '"history": true, "history": false',
        )), 0.0),
        ("duplicate-nested-key", block(payload.replace(
            '"limit": 3', '"limit": 9, "limit": 3',
        )), 0.0),
        ("trailing-object", block(payload + " {}"), 0.0),
        ("trailing-null", block(payload + " null"), 0.0),
        ("escaped-marker", block(payload.replace(
            "München", r"\u003c|tool_call|\u003e",
        )), 0.0),
        ("raw-high-surrogate", changed_argument("city", "\ud800"), 0.0),
        ("raw-low-surrogate", changed_argument("city", "\udfff"), 0.0),
        ("escaped-surrogate", block(payload.replace("München", r"\ud800")), 0.0),
    ]
    for size, expected_score in [(LIMIT - 1, 1.0), (LIMIT, 1.0), (LIMIT + 1, 0.0)]:
        # Padding outside the action must still count toward the original limit.
        padded = good + " " * (size - len(good))
        assert len(padded) == size
        result.append((f"size-{size}", padded, expected_score))
    for number in ["NaN", "Infinity", "-Infinity", "1e9999", "-1e9999"]:
        result.append((f"invalid-number-{number}", block(payload.replace('"limit": 3', f'"limit": {number}')), 0.0))
    for char in ["\x00", "\x01", "\x08", "\x0b", "\x0c", "\x1b", "\x1f"]:
        result.append((f"raw-control-{ord(char):02x}", char + good, 0.0))
    for call_id in [None, 0, [], {}]:
        result.append((f"invalid-id-{type(call_id).__name__}", completion({**EXPECTED, "id": call_id}), 0.0))
    return result


BOUNDARIES = boundary_cases()


@fixture
def verifier():
    return load_verifier(VERIFIER)


@fixture
def task_dir(tmp_path):
    task = tmp_path / "fixture"
    task.mkdir()
    (task / "hidden_tests.json").write_text(
        json.dumps({"expected_call": EXPECTED}, ensure_ascii=False), encoding="utf-8",
    )
    return task


@cases("case_id,text,expected_score", BOUNDARIES, ids=[c[0] for c in BOUNDARIES])
def test_tool_call_boundary_contract(verifier, task_dir, case_id, text, expected_score):
    result = verifier.reward(task_dir, text)
    assert result["reward"] == expected_score, case_id
    assert result["task_id"] == task_dir.name
    assert isinstance(result["reason"], str)


def test_tool_call_excessive_nesting_returns_zero_without_crashing(task_dir):
    # Fix recursion depth only in a child; do not change pytest's own interpreter.
    script = """
import importlib.util
import sys
from pathlib import Path
sys.setrecursionlimit(1000)
spec = importlib.util.spec_from_file_location('nesting_verifier', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
payload = '{"name":"fixture_lookup","arguments":{"nested":' + '[' * 2000 + '0' + ']' * 2000 + '}}'
text = '<|tool_call|>' + payload + '<|/tool_call|>'
print(module.reward(Path(sys.argv[2]), text)['reward'])
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, str(VERIFIER), str(task_dir)],
        capture_output=True, text=True, timeout=10, check=True,
    )
    assert result.stdout.strip() == "0.0"
    assert result.stderr == ""


@cases("raw", [
    "{", "null", "[]", "{}",
    '{"expected_call":null}',
    '{"expected_call":{"name":"fixture_lookup","arguments":[]}}',
    '{"expected_call":{"name":"fixture_lookup","arguments":{},"id":"unexpected"}}',
    '{"expected_call":{"name":"fixture_lookup","arguments":{"value":NaN}}}',
    '{"expected_call":{"name":"fixture_lookup","arguments":{"value":1e9999}}}',
    '{"expected_call":{"name":"wrong","name":"fixture_lookup","arguments":{}}}',
], ids=["syntax", "null", "array", "missing-reference", "null-reference", "argument-type",
        "unexpected-reference-id", "non-json-number", "overflowing-number", "duplicate-key"])
def test_tool_call_bad_hidden_config_raises_instead_of_model_zero(verifier, task_dir, raw):
    (task_dir / "hidden_tests.json").write_text(raw, encoding="utf-8")
    # Both valid and invalid candidate text must leave the configuration error visible.
    for text in [completion(), ""]:
        with pytest.raises(ValueError):
            verifier.reward(task_dir, text)


def test_tool_call_missing_hidden_config_raises(verifier, task_dir):
    (task_dir / "hidden_tests.json").unlink()
    for text in [completion(), ""]:
        with pytest.raises(FileNotFoundError):
            verifier.reward(task_dir, text)


# Exactly one source anchor must match. Source drift requires explicit review,
# never a silent skipped mutation or a change to the checked-in verifier.
MUTATIONS = [
    ("ignore-tool-name", '"name": call["name"]',
     '"name": _loads(expected)["name"]', "wrong-tool"),
    ("ignore-arguments", '"arguments": call["arguments"]',
     '"arguments": _loads(expected)["arguments"]', "wrong-value"),
    ("accept-duplicate-keys", "object_pairs_hook=_object", "object_pairs_hook=dict", "duplicate-nested-key"),
    ("bypass-size-limit", "len(completion) > MAX_COMPLETION_CHARS", "False", f"size-{LIMIT + 1}"),
]


@cases("mutation,anchor,replacement,witness", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_tool_call_contract_detects_deliberate_mutation(
    verifier, task_dir, tmp_path, record_property, mutation, anchor, replacement, witness,
):
    source = VERIFIER.read_text(encoding="utf-8")
    assert source.count(anchor) == 1, f"Review mutation anchor after source change: {mutation}"
    mutated = source.replace(anchor, replacement, 1)
    assert mutated != source
    mutation_file = tmp_path / f"{mutation.replace('-', '_')}.py"
    mutation_file.write_text(mutated, encoding="utf-8")
    mutant = load_verifier(mutation_file)

    detected_by = []
    for case_id, text, expected_score in BOUNDARIES:
        assert verifier.reward(task_dir, text)["reward"] == expected_score, case_id
        # Exceptions are harness failures, not evidence of a detected reward bug.
        actual = mutant.reward(task_dir, text)["reward"]
        assert actual in (0.0, 1.0), f"Non-binary mutant reward: {mutation}"
        if actual != expected_score:
            detected_by.append(case_id)
        if expected_score == 1.0:
            assert actual == 1.0, f"Mutation broke a valid control: {mutation}/{case_id}"

    assert witness in detected_by, f"Mutation survived its required witness: {mutation}"
    record_property("mutation", mutation)
    record_property("detected_by", ", ".join(detected_by))
    print(f"{mutation} detected by: {', '.join(detected_by)}")
