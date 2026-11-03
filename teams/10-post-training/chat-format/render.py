"""Render and parse ChatML-style chat format v0 using Team 3's tokenizer IDs.

Rule (instructor, 27 Oct & Week 2 brief):
- Special tokens only for structure the model must never confuse with normal text:
  role-turn start/end, tool-call start/end, tool-result start/end, thinking start/end.
- Values inside that structure (tool names, arguments, effort level, options) are plain text.
- Effort is a plain-text line at the top of the first system turn: `Reasoning effort: {level}`.
- Token IDs are read from Team 3's tokenizer specification (`teams/03-tokenizer/v0/build_v0_1.py`
  / `special_slots.md`, or a `tokenizer.json` file). The old 000..255 slot numbering is removed:
  IDs 0..255 are byte tokens in BrahmicTokenizer-131K.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

G10_SLOT_START = 130822
G10_SLOT_COUNT = 64  # g10_slot_00 (130822) .. g10_slot_63 (130885)

EFFORT_BUDGETS = {
    "1k": 1024,
    "4k": 4096,
    "16k": 16384,
    "64k": 65536,
}

# Surface -> canonical G10 marker name for the 9 active ChatML v0 markers.
MARKER_NAMES: dict[str, str] = {
    "<|endoftext|>": "endoftext",
    "<|im_start|>": "im_start",
    "<|im_end|>": "im_end",
    "<|think|>": "think",
    "<|/think|>": "think_end",
    "<|tool_call|>": "tool_call",
    "<|/tool_call|>": "tool_call_end",
    "<|tool_result|>": "tool_result",
    "<|/tool_result|>": "tool_result_end",
}

_HERE = Path(__file__).resolve().parent
_TEAM = _HERE.parent
_REPO_ROOT = _TEAM.parent.parent
TEAM3_BUILD_V0_1 = _REPO_ROOT / "teams" / "03-tokenizer" / "v0" / "build_v0_1.py"
TEAM3_SPECIAL_SLOTS = _REPO_ROOT / "teams" / "03-tokenizer" / "v0" / "special_slots.md"
G10_SPECIAL_TOKENS_V1 = _TEAM / "special-tokens" / "special_tokens_v1.md"


def load_team3_marker_ids(tokenizer_path: Path | str | None = None) -> dict[int, tuple[str, str]]:
    """Read G10's ChatML v0 marker IDs from Team 3's tokenizer file.

    1. If `tokenizer_path` is a Hugging Face `tokenizer.json`, reads `added_tokens`.
    2. Otherwise reads `EXISTING` and `RENAMES` from `teams/03-tokenizer/v0/build_v0_1.py`.
    3. If running in an isolated container where only `teams/10-post-training` is mounted,
       reads the machine-readable table in `special-tokens/special_tokens_v1.md`.
    """
    if tokenizer_path is not None:
        path = Path(tokenizer_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        by_surface = {
            tok["content"]: int(tok["id"])
            for tok in data.get("added_tokens", [])
            if tok.get("special")
        }
        mapped: dict[int, tuple[str, str]] = {}
        for surf, name in MARKER_NAMES.items():
            if surf not in by_surface:
                raise ValueError(f"missing special token {surf} in {path}")
            mapped[by_surface[surf]] = (name, surf)
        return dict(sorted(mapped.items()))

    if TEAM3_BUILD_V0_1.is_file():
        tree = ast.parse(TEAM3_BUILD_V0_1.read_text(encoding="utf-8"), filename=str(TEAM3_BUILD_V0_1))
        existing: dict[str, int] = {}
        renames: dict[str, tuple[int, str]] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                target = node.targets[0].id
                if target == "EXISTING":
                    existing = ast.literal_eval(node.value)
                elif target == "RENAMES":
                    renames = ast.literal_eval(node.value)
        surface_to_id: dict[str, int] = dict(existing)
        for tok_id, surf in renames.values():
            surface_to_id[surf] = int(tok_id)
        mapped = {
            surface_to_id[surf]: (name, surf)
            for surf, name in MARKER_NAMES.items()
            if surf in surface_to_id
        }
        if len(mapped) == len(MARKER_NAMES):
            return dict(sorted(mapped.items()))

    if G10_SPECIAL_TOKENS_V1.is_file():
        mapped = {}
        for line in G10_SPECIAL_TOKENS_V1.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if len(parts) >= 3 and parts[0].isdigit() and parts[2] in MARKER_NAMES:
                tok_id = int(parts[0])
                surf = parts[2]
                mapped[tok_id] = (MARKER_NAMES[surf], surf)
        if len(mapped) == len(MARKER_NAMES):
            return dict(sorted(mapped.items()))

    raise RuntimeError("Could not load Team 3 tokenizer marker IDs")


# Exact Team 3 tokenizer ID -> (name, atomic special-token surface).
ASSIGNED_SURFACES: dict[int, tuple[str, str]] = load_team3_marker_ids()
ASSIGNED: dict[int, str] = {idx: name for idx, (name, _) in ASSIGNED_SURFACES.items()}
ROLES = ("system", "user", "assistant", "tool")
EFFORT_PREFIX = "Reasoning effort: "

# Plain-text XML tags and Unicode look-alikes that must NEVER be used in place of atomic special tokens.
# Note: bare <think> (ID 128512 in the base tokenizer) is never used by chat_format_v0.
_PLAIN_TEXT_LOOKALIKES = (
    "<think>",
    "</think>",
    "<tool_call>",
    "</tool_call>",
    "<tool_result>",
    "</tool_result>",
    "<｜think｜>",
    "<｜/think｜>",
    "<｜tool_call｜>",
    "<｜/tool_call｜>",
    "<｜tool_result｜>",
    "<｜/tool_result｜>",
    "＜think＞",
    "＜/think＞",
    "＜tool_call＞",
    "＜/tool_call＞",
    "＜tool_result＞",
    "＜/tool_result＞",
)


def surface(name: str) -> str:
    for n, surf in ASSIGNED_SURFACES.values():
        if n == name:
            return surf
    return f"<|{name}|>"


def g10_slot_name(slot_index: int) -> str:
    return f"g10_slot_{slot_index:02d}"


def all_tokens() -> list[tuple[int, str, str, str]]:
    """Return (token_id, name, surface, status) for G10's existing base specials and 64 G10 slots (130822..130885)."""
    rows: list[tuple[int, str, str, str]] = []
    for tok_id, (name, surf) in sorted(ASSIGNED_SURFACES.items()):
        if tok_id < G10_SLOT_START:
            rows.append((tok_id, name, surf, "assigned"))
    for slot_idx in range(G10_SLOT_COUNT):
        tok_id = G10_SLOT_START + slot_idx
        if tok_id in ASSIGNED_SURFACES:
            name, surf = ASSIGNED_SURFACES[tok_id]
            rows.append((tok_id, name, surf, "assigned"))
        else:
            name = g10_slot_name(slot_idx)
            rows.append((tok_id, name, f"<|{name}|>", "reserved"))
    return rows


def by_name() -> dict[str, str]:
    return {name: token for _, name, token, _ in all_tokens()}


def id_by_surface() -> dict[str, int]:
    return {token: index for index, _, token, _ in all_tokens()}


T = by_name()
_ID_BY_SURFACE = id_by_surface()
_SURFACES = sorted(T.values(), key=len, reverse=True)


class RenderError(ValueError):
    """The transcript is not valid chat-format v0."""


def effort_limit(effort: str) -> int:
    try:
        return EFFORT_BUDGETS[effort]
    except KeyError as exc:
        raise RenderError(
            f"effort must be one of {', '.join(EFFORT_BUDGETS)}"
        ) from exc


def _reject_specials(text: str, where: str) -> None:
    for token in _SURFACES:
        if token in text:
            raise RenderError(f"{where} contains special token {token}")
    for tag in _PLAIN_TEXT_LOOKALIKES:
        if tag in text:
            raise RenderError(
                f"{where} contains plain-text marker {tag}; every chat marker must be one special token"
            )


def _call_json(call: object) -> str:
    if not isinstance(call, dict):
        raise RenderError("tool call must be an object")
    if "function" in call and isinstance(call["function"], dict):
        fn = call["function"]
        name = fn.get("name")
        arguments = fn.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise RenderError("tool call arguments must be valid JSON") from exc
    else:
        name = call.get("name")
        arguments = call.get("arguments", {})
    if not isinstance(name, str) or name == "":
        raise RenderError("tool call name must be a non-empty string")
    if not isinstance(arguments, dict):
        raise RenderError("tool call arguments must be an object")
    call_dict = {"arguments": arguments, "name": name}
    if "id" in call and isinstance(call["id"], str):
        call_dict["id"] = call["id"]
    try:
        payload = json.dumps(
            call_dict,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except TypeError as exc:
        raise RenderError("tool call arguments must be JSON values") from exc
    _reject_specials(payload, "tool call")
    return payload


def _turn(role: str, body: str) -> str:
    return f"{T['im_start']}{role}\n{body}{T['im_end']}\n"


def render(messages: list[dict], effort: str = "4k") -> str:
    """Render a transcript in ChatML v0 where every chat marker is one special token."""
    effort_limit(effort)
    if not isinstance(messages, list) or not messages:
        raise RenderError("messages must be a non-empty list")

    parts: list[str] = []
    first = messages[0]
    if not (isinstance(first, dict) and first.get("role") == "system"):
        parts.append(_turn("system", f"{EFFORT_PREFIX}{effort}"))
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise RenderError(f"message {index} must be an object")
        role = message.get("role")
        if role not in ROLES:
            raise RenderError(f"message {index} has role {role!r}")
        content = message.get("content", "")
        if content is None:
            content = ""
        if not isinstance(content, str):
            raise RenderError(f"message {index} content must be a string")
        _reject_specials(content, f"message {index} content")

        if role == "assistant":
            body: list[str] = []
            think = message.get("think") or ""
            if think:
                if not isinstance(think, str):
                    raise RenderError(f"message {index} think must be a string")
                _reject_specials(think, f"message {index} think")
                body.append(f"{T['think']}\n{think}\n{T['think_end']}\n")
            for call in message.get("tool_calls") or []:
                body.append(f"{T['tool_call']}\n{_call_json(call)}\n{T['tool_call_end']}\n")
            if content:
                body.append(content)
            parts.append(_turn("assistant", "".join(body)))
        elif role == "tool":
            if content == "":
                raise RenderError(f"message {index} tool content is empty")
            parts.append(
                _turn("tool", f"{T['tool_result']}\n{content}\n{T['tool_result_end']}")
            )
        elif role == "system" and index == 0:
            if content.startswith(EFFORT_PREFIX):
                raise RenderError(f"system content must not start with {EFFORT_PREFIX!r}")
            line = f"{EFFORT_PREFIX}{effort}"
            parts.append(_turn("system", f"{line}\n\n{content}" if content else line))
        else:
            parts.append(_turn(role, content))
    parts.append(T["endoftext"])
    return "".join(parts)


def tokenize_markers(text: str) -> list[tuple[str, int | str]]:
    """Split rendered text into ('special', token_id) and ('text', str) items.

    Proves for Team 3 (G3) that every chat marker is tokenized as a single
    Team 3 special token ID (129994, 130773, 130774, 130816, 130822..130826)
    and never left in a plain-text span.
    """
    items: list[tuple[str, int | str]] = []
    pos = 0
    buf_start = 0
    n = len(text)
    while pos < n:
        matched = None
        for surf in _SURFACES:
            if text.startswith(surf, pos):
                matched = surf
                break
        if matched is not None:
            if pos > buf_start:
                items.append(("text", text[buf_start:pos]))
            items.append(("special", _ID_BY_SURFACE[matched]))
            pos += len(matched)
            buf_start = pos
        else:
            pos += 1
    if n > buf_start:
        items.append(("text", text[buf_start:n]))
    return items


def _parse_system_effort(body: str) -> tuple[str, str]:
    """Split the first system turn into (effort level, remaining system content)."""
    if not body.startswith(EFFORT_PREFIX):
        raise RenderError(f"first system turn must start with {EFFORT_PREFIX!r}")
    rest = body[len(EFFORT_PREFIX) :]
    level, _sep, content = rest.partition("\n\n")
    if level not in EFFORT_BUDGETS:
        raise RenderError(f"effort must be one of {', '.join(EFFORT_BUDGETS)}")
    return level, content


def _parse_assistant(body: str) -> dict:
    message: dict = {"role": "assistant"}
    think_open = f"{T['think']}\n"
    think_close = f"\n{T['think_end']}\n"
    call_open = f"{T['tool_call']}\n"
    call_close = f"\n{T['tool_call_end']}\n"

    while True:
        if body.startswith(think_open):
            end = body.find(think_close)
            if end < 0:
                raise RenderError(f"missing {T['think_end']}")
            think = body[len(think_open) : end]
            _reject_specials(think, "parsed think")
            message["think"] = think
            body = body[end + len(think_close) :]
            continue
        if body.startswith(call_open):
            end = body.find(call_close)
            if end < 0:
                raise RenderError(f"missing {T['tool_call_end']}")
            payload = body[len(call_open) : end]
            _reject_specials(payload, "parsed tool call")
            try:
                call = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise RenderError("tool call is not JSON") from exc
            message.setdefault("tool_calls", []).append(call)
            body = body[end + len(call_close) :]
            continue
        break

    if body:
        _reject_specials(body, "parsed text")
        message["content"] = body
    return message


def parse(text: str) -> dict:
    """Inverse of `render` for transcripts this module produced."""
    if not isinstance(text, str) or not text.endswith(T["endoftext"]):
        raise RenderError("transcript must end with <|endoftext|>")
    pos = 0
    end = len(text) - len(T["endoftext"])
    messages: list[dict] = []
    effort: str | None = None

    while pos < end:
        if not text.startswith(T["im_start"], pos):
            raise RenderError(f"expected <|im_start|> at offset {pos}")
        pos += len(T["im_start"])
        newline = text.find("\n", pos)
        if newline < 0 or newline > end:
            raise RenderError("turn is missing a role")
        role = text[pos:newline]
        if role not in ROLES:
            raise RenderError(f"unknown role {role!r}")
        pos = newline + 1
        close = text.find(T["im_end"], pos)
        if close < 0 or close > end:
            raise RenderError("missing <|im_end|>")
        body = text[pos:close]
        pos = close + len(T["im_end"])
        if text.startswith("\n", pos):
            pos += 1

        if not messages and effort is None:
            if role != "system":
                raise RenderError("first turn must be the system turn with the effort line")
            effort, body = _parse_system_effort(body)
            _reject_specials(body, "parsed text")
            if body:
                messages.append({"role": "system", "content": body})
            continue
        if role == "assistant":
            messages.append(_parse_assistant(body))
        elif role == "tool":
            open_tag = f"{T['tool_result']}\n"
            close_tag = f"\n{T['tool_result_end']}"
            if not body.startswith(open_tag) or not body.endswith(close_tag):
                raise RenderError("tool turn must wrap output in <|tool_result|>...<|/tool_result|>")
            content = body[len(open_tag) : len(body) - len(close_tag)]
            if content == "":
                raise RenderError("tool content is empty")
            _reject_specials(content, "parsed text")
            messages.append({"role": "tool", "content": content})
        else:
            _reject_specials(body, "parsed text")
            messages.append({"role": role, "content": body})

    if pos != end:
        raise RenderError("trailing bytes before endoftext")
    return {"effort": effort, "messages": messages}
