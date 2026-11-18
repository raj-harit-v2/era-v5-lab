"""Exact JSON tool-call rewards. Model output is parsed as data, never executed.

Expected calls are read only from each task's hidden_tests.json. No expected payload
or argument-level feedback is returned in the reward info.
"""
from __future__ import annotations

import json
from pathlib import Path

OPEN = "<|tool_call|>"
CLOSE = "<|/tool_call|>"
MAX_COMPLETION_CHARS = 65536


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _constant(_):
    raise ValueError("non-JSON number")


def _loads(text: str):
    return json.loads(text, object_pairs_hook=_object, parse_constant=_constant)


def actionable_body(completion: str) -> str:
    """Remove only the allowed assistant envelope, never search prose for a call.

    A single plain reasoning block may precede the action. Control tokens inside
    reasoning, extra turns, examples and code fences are not executable actions.
    """
    if not isinstance(completion, str) or len(completion) > MAX_COMPLETION_CHARS:
        raise ValueError("invalid or oversized completion")
    if any(ord(c) < 32 and c not in "\t\r\n" for c in completion):
        raise ValueError("control character in completion")
    completion.encode("utf-8")  # refuse unpaired surrogates
    body = completion.strip()
    for stop in ("<|endoftext|>", "<|im_end|>"):
        if body.endswith(stop):
            body = body[:-len(stop)].rstrip()
    if body.startswith("<|think|>"):
        end = body.find("<|/think|>", len("<|think|>"))
        if end < 0:
            raise ValueError("unclosed reasoning block")
        reasoning = body[len("<|think|>"):end]
        if "<|" in reasoning or "|>" in reasoning:
            raise ValueError("control token inside reasoning")
        body = body[end + len("<|/think|>"):].strip()
    return body


def canonical(value) -> str:
    """Preserve JSON types and string values; ignore object key order and JSON spacing."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _valid_call(call) -> bool:
    return (
        isinstance(call, dict)
        and {"name", "arguments"} <= set(call) <= {"name", "arguments", "id"}
        and isinstance(call["name"], str)
        and bool(call["name"])
        and isinstance(call["arguments"], dict)
        and ("id" not in call or isinstance(call["id"], str))
    )


def _expected(task_dir: Path) -> dict:
    # Configuration errors propagate instead of looking like a model's wrong answer.
    hidden = _loads((task_dir / "hidden_tests.json").read_text(encoding="utf-8"))
    expected = hidden.get("expected_call") if isinstance(hidden, dict) else None
    if not _valid_call(expected) or set(expected) != {"name", "arguments"}:
        raise ValueError("invalid hidden tool-call specification")
    canonical(expected)
    return expected


def reward(task_dir: Path, completion: str) -> dict:
    task_dir = Path(task_dir)
    expected = canonical(_expected(task_dir))
    info = {"task_id": task_dir.name, "reward": 0.0, "reason": ""}
    try:
        body = actionable_body(completion)
        if (not body.startswith(OPEN) or not body.endswith(CLOSE)
                or body.count(OPEN) != 1 or body.count(CLOSE) != 1):
            return {**info, "reason": "expected one top-level tool-call block"}
        payload = body[len(OPEN):-len(CLOSE)]
        if "<|" in payload or "|>" in payload:
            return {**info, "reason": "control token inside tool-call payload"}
        call = _loads(payload)
        if not _valid_call(call):
            return {**info, "reason": "invalid tool-call payload"}
        # Optional transport ids do not change the requested function or its arguments.
        actual = canonical({"name": call["name"], "arguments": call["arguments"]})
    except (ValueError, RecursionError):
        return {**info, "reason": "invalid tool-call JSON"}
    if actual != expected:
        return {**info, "reason": "tool call does not match"}
    return {**info, "reward": 1.0, "reason": "exact match"}


def known_outputs(task_dir: Path) -> tuple[str, str]:
    """Verifier self-check fixtures; never use these to construct a model prompt."""
    good = OPEN + "\n" + canonical(_expected(Path(task_dir))) + "\n" + CLOSE
    return good, OPEN + '\n{"name":"__wrong_tool__","arguments":{}}\n' + CLOSE
