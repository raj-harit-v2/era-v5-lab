"""vLLM reasoning and tool-call parsers for the G10 chat format v0.

Format (teams/10-post-training/chat-format/chat_template.jinja, chat_format_v0.md). An assistant turn is

    <|think|>\\n{reasoning}\\n<|/think|>\\n                     optional
    <|tool_call|>\\n{"arguments":{...},"name":"..."}\\n<|/tool_call|>\\n    zero or more
    {visible content}<|im_end|>

With the frozen Team 3 tokenizer each marker is one special token (<|think|> 130823, <|/think|> 130824,
<|tool_call|> 130773, <|/tool_call|> 130825). No built-in vLLM parser knows these markers: deepseek_r1 / qwen3 look
for <think>, hermes for <tool_call>. Hermes's streaming also assumes "name" comes before "arguments", and G10 writes
"arguments" first.

Serve (vLLM 0.33.0, the version pinned in gpu_path/results/environment.json):

    vllm serve MODEL \\
        --chat-template teams/10-post-training/chat-format/chat_template.jinja \\
        --reasoning-parser-plugin teams/12-quantization/serving/g10_parsers.py --reasoning-parser g10 \\
        --enable-auto-tool-choice \\
        --tool-parser-plugin teams/12-quantization/serving/g10_parsers.py --tool-call-parser g10

Clients send "skip_special_tokens": false (serve_check.py does). Otherwise vLLM drops the special marker tokens
before the parser sees them, and reasoning shows up as plain content. The tool parser also sets it on requests
that carry tools.

Markers are matched as text, so the parsers also work with a stand-in model whose tokenizer splits them into
several tokens. They use token ids only as a fast path when the markers are single tokens.

The module is in two parts:
  * plain Python (split_reasoning, parse_tool_calls, ReasoningStream, ToolCallStream), tested without vLLM in
    test_g10_parsers.py;
  * thin vLLM adapters (G10ReasoningParser, G10ToolParser), registered as "g10" when vLLM can be imported.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Iterable, Sequence

THINK, THINK_END = "<|think|>", "<|/think|>"
CALL, CALL_END = "<|tool_call|>", "<|/tool_call|>"
IM_START = "<|im_start|>"
MARKERS = (THINK, THINK_END, CALL, CALL_END, "<|tool_result|>", "<|/tool_result|>", IM_START, "<|im_end|>",
           "<|endoftext|>")


# ------------------------------------------------------------------------------ plain Python core

def _overlap(text: str, tag: str) -> int:
    """Length of the longest suffix of text that is a proper prefix of tag (a tag that may still be arriving)."""
    for n in range(min(len(text), len(tag) - 1), 0, -1):
        if tag.startswith(text[-n:]):
            return n
    return 0


def _drop_one(text: str, prefix: str = "", suffix: str = "") -> str:
    if prefix and text.startswith(prefix):
        text = text[len(prefix):]
    if suffix and text.endswith(suffix):
        text = text[: -len(suffix)]
    return text


def split_reasoning(text: str, final: bool = True) -> tuple[str | None, str | None]:
    """Split one assistant output into (reasoning, content).

    A reasoning block counts only at the start of the output (after optional whitespace). The newline the template
    writes after <|think|> and before <|/think|> are removed, and content loses its leading whitespace. final=False is the
    streaming view of a prefix: it holds back anything that may still change (a partial marker, a trailing newline
    that may precede <|/think|>, and an output too short to tell whether it opens with <|think|>). It returns
    (None, None) while undecided."""
    stripped = text.lstrip()
    if not stripped.startswith(THINK):
        if not final and THINK.startswith(stripped):
            return None, None                        # "", "  " or "<|th": may still become <|think|>
        return None, (stripped if stripped else None)
    body = _drop_one(stripped[len(THINK):], prefix="\n")
    end = body.find(THINK_END)
    if end < 0:                                      # reasoning still open (streaming) or cut off (max_tokens)
        if not final:
            body = body[: len(body) - _overlap(body, THINK_END)]
            body = _drop_one(body, suffix="\n")
        return body, None
    reasoning = _drop_one(body[:end], suffix="\n")
    content = body[end + len(THINK_END):].lstrip()           # visible text: leading whitespace carries nothing
    if not final and content == "":
        return reasoning, None
    return reasoning, (content if content else None)


def _no_think_decided(text: str) -> bool:
    """True once the output has visibly started without <|think|> (so there is no reasoning block)."""
    s = text.lstrip()
    return bool(s) and not s.startswith(THINK) and not THINK.startswith(s)


def reasoning_ended(text: str) -> bool:
    """Has the reasoning of the open assistant turn ended? text: a decoded prompt or a decoded output.

    A prompt holds earlier turns whose <|think|> ... <|/think|> must not count: only the text after the last
    <|im_start|> (the open turn) is read. The generation prompt "<|im_start|>assistant\\n" leaves it empty, so
    reasoning has not ended. An output with no reasoning block ends reasoning as soon as it starts with something
    else."""
    k = text.rfind(IM_START)
    if k >= 0:
        turn = text[k + len(IM_START):]
        text = turn.split("\n", 1)[1] if "\n" in turn else ""
    s = text.lstrip()
    if s.startswith(THINK):
        return THINK_END in s
    return _no_think_decided(s)


def _call_from_json(obj) -> dict | None:
    """{"name", "arguments" (JSON string), "id" or None} from a parsed tool-call body, or None if it is not one.
    Accepts the G10 shape {"arguments", "name", "id"?} and the OpenAI shape {"function": {...}, "id"?}, which
    the G10 template writes for history tool calls that arrive in OpenAI form."""
    if not isinstance(obj, dict):
        return None
    fn = obj.get("function") if isinstance(obj.get("function"), dict) else obj
    name = fn.get("name")
    if not isinstance(name, str) or not name:
        return None
    args = fn.get("arguments", {})
    if isinstance(args, str):
        try:
            json.loads(args)
        except ValueError:
            args = json.dumps(args, ensure_ascii=False)          # a bare string argument becomes a JSON string
    else:
        args = json.dumps(args, ensure_ascii=False)
    call_id = obj.get("id")
    return {"name": name, "arguments": args, "id": call_id if isinstance(call_id, str) and call_id else None}


def _regions(text: str):
    """Yield ("text", s) and ("call", body, complete) pieces of an output in order. A call with no closing marker
    runs to the end of the text, and complete is False."""
    pos = 0
    while True:
        i = text.find(CALL, pos)
        if i < 0:
            yield ("text", text[pos:])
            return
        yield ("text", text[pos:i])
        j = text.find(CALL_END, i + len(CALL))
        if j < 0:
            yield ("call", text[i + len(CALL):], False)
            return
        yield ("call", text[i + len(CALL):j], True)
        pos = j + len(CALL_END)


def parse_tool_calls(text: str) -> tuple[list[dict], str | None]:
    """All tool calls of a complete output, and the visible content around them (stripped; None if empty).
    A call region whose body is not a valid call stays in the content, so nothing is silently dropped."""
    calls, content = [], []
    for piece in _regions(text):
        if piece[0] == "text":
            content.append(piece[1])
            continue
        _, body, complete = piece
        try:
            call = _call_from_json(json.loads(body.strip()))
        except ValueError:
            call = None
        if call is None:
            content.append(CALL + body + (CALL_END if complete else ""))
        else:
            calls.append(call)
    visible = "".join(content).strip()
    return calls, (visible if visible else None)


class ReasoningStream:
    """Streaming split: feed the whole output so far, get back the (reasoning, content) text not yet sent."""

    def __init__(self):
        self.sent_reasoning = ""
        self.sent_content = ""

    def feed(self, current_text: str) -> tuple[str | None, str | None]:
        reasoning, content = split_reasoning(current_text, final=False)
        return self._diff(reasoning, content)

    def flush(self, text: str) -> tuple[str | None, str | None]:
        """At the end of the output: whatever the streaming view held back."""
        reasoning, content = split_reasoning(text, final=True)
        return self._diff(reasoning, content)

    def _diff(self, reasoning, content):
        new_r = new_c = None
        if reasoning is not None and len(reasoning) > len(self.sent_reasoning):
            new_r = reasoning[len(self.sent_reasoning):]
            self.sent_reasoning = reasoning
        if content is not None and len(content) > len(self.sent_content):
            new_c = content[len(self.sent_content):]
            self.sent_content = content
        return new_r, new_c


class ToolCallStream:
    """Streaming tool calls: feed the whole post-reasoning text so far, get back (new content, new complete calls).

    A call is sent whole, name and arguments in one delta, once its region is closed or its JSON body is complete.
    That keeps "arguments"-before-"name" bodies correct. Content is the text outside call regions, with leading
    whitespace removed and trailing whitespace and partial markers held back. So the streamed content equals
    parse_tool_calls' content once the output is finished."""

    def __init__(self):
        self.sent_content = ""
        self.calls: list[dict] = []

    def _view(self, text: str, final: bool) -> tuple[list[dict], str]:
        calls, content = [], []
        for piece in _regions(text):
            if piece[0] == "text":
                content.append(piece[1])
                continue
            _, body, closed = piece
            body_s = body if closed else body[: len(body) - _overlap(body, CALL_END)]
            try:
                call = _call_from_json(json.loads(body_s.strip()))
            except ValueError:
                call = None
            if call is not None:
                calls.append(call)
            elif closed or final:
                content.append(CALL + body + (CALL_END if closed else ""))
            else:
                break                                 # open call, body still arriving: nothing after it yet
        visible = "".join(content).lstrip()
        if not final:
            visible = visible[: len(visible) - _overlap(visible, CALL)].rstrip()
        else:
            visible = visible.rstrip()
        return calls, visible

    def feed(self, current_text: str, final: bool = False) -> tuple[str | None, list[dict]]:
        calls, visible = self._view(current_text, final)
        new_calls = calls[len(self.calls):]
        self.calls.extend(new_calls)
        new_content = None
        if len(visible) > len(self.sent_content) and visible.startswith(self.sent_content):
            new_content = visible[len(self.sent_content):]
            self.sent_content = visible
        return new_content, new_calls


# ------------------------------------------------------------------------------ vLLM adapters

def _make_call_id() -> str:
    try:
        from vllm.renderers.chat_utils import make_tool_call_id
        return make_tool_call_id()
    except Exception:                                            # noqa: BLE001  (any vLLM layout change)
        return f"chatcmpl-tool-{uuid.uuid4().hex}"


try:
    from vllm.entrypoints.generate.base.protocol import (
        DeltaFunctionCall,
        DeltaMessage,
        DeltaToolCall,
        ExtractedToolCallInformation,
        FunctionCall,
        ToolCall,
    )
    from vllm.reasoning import ReasoningParser, ReasoningParserManager
    from vllm.tool_parsers import ToolParser, ToolParserManager
    HAVE_VLLM = True
except ImportError:                                              # plain-Python use and the CPU tests
    HAVE_VLLM = False


if HAVE_VLLM:

    class _MarkerIds:
        """Token ids of the markers when each is one token in this tokenizer, else None (text-only matching)."""

        def __init__(self, tokenizer):
            vocab = tokenizer.get_vocab() if tokenizer is not None else {}
            self.think = vocab.get(THINK)
            self.think_end = vocab.get(THINK_END)
            self.special = self.think is not None and self.think_end is not None

    def _decode(tokenizer, ids) -> str:
        ids = list(ids)
        return tokenizer.decode(ids, skip_special_tokens=False) if ids else ""

    class G10ReasoningParser(ReasoningParser):
        """<|think|> ... <|/think|> at the start of the assistant output -> the `reasoning` field."""

        def __init__(self, tokenizer, *args, **kwargs):
            super().__init__(tokenizer, *args, **kwargs)
            self._ids = _MarkerIds(tokenizer)
            self._stream = ReasoningStream()

        @property
        def reasoning_start_str(self) -> str:
            return THINK

        @property
        def reasoning_end_str(self) -> str:
            return THINK_END

        def adjust_request(self, request):
            if self._ids.special:
                request.skip_special_tokens = False
            return request

        def is_reasoning_end(self, input_ids: Sequence[int]) -> bool:
            return reasoning_ended(_decode(self.model_tokenizer, input_ids))

        def is_reasoning_end_streaming(self, input_ids: Sequence[int], delta_ids: Iterable[int]) -> bool:
            delta = list(delta_ids)
            if self._ids.special and self._ids.think_end in delta:
                return True
            ids = list(input_ids)
            # the end marker is at most a few tokens long: decode only the tail, not the whole output each step
            if THINK_END in _decode(self.model_tokenizer, ids[-(len(delta) + 16):]):
                return True
            return len(ids) <= 32 and _no_think_decided(_decode(self.model_tokenizer, ids))

        def extract_content_ids(self, input_ids: list[int]) -> list[int]:
            ids = list(input_ids)
            if self._ids.special and self._ids.think_end in ids:
                return ids[ids.index(self._ids.think_end) + 1:]
            text = _decode(self.model_tokenizer, ids)
            if THINK in text or THINK_END in text:
                return []                     # text-mode marker: the tool phase reads text, not these ids
            return ids

        def count_reasoning_tokens(self, token_ids: Sequence[int]) -> int:
            if not self._ids.special:
                return 0
            ids = list(token_ids)
            if self._ids.think not in ids:
                return 0
            start = ids.index(self._ids.think) + 1
            end = ids.index(self._ids.think_end, start) if self._ids.think_end in ids[start:] else len(ids)
            return end - start

        def extract_reasoning(self, model_output: str, request) -> tuple[str | None, str | None]:
            return split_reasoning(model_output, final=True)

        def extract_reasoning_streaming(self, previous_text, current_text, delta_text, previous_token_ids,
                                        current_token_ids, delta_token_ids):
            reasoning, content = self._stream.feed(current_text)
            if reasoning is None and content is None:
                return None
            return DeltaMessage(reasoning=reasoning, content=content)

        def get_streaming_fallback_content(self, previous_text: str, request) -> str | None:
            """Called by vLLM when the output ends while reasoning is still open: send what was held back."""
            _, content = self._stream.flush(previous_text)
            return content

    class G10ToolParser(ToolParser):
        """<|tool_call|>{json}<|/tool_call|> -> `tool_calls`; the text around the calls -> `content`."""

        # tool_choice "required" / named would make vLLM force a plain JSON list, not our markers: parse those
        # through extract_tool_calls like "auto".
        supports_required_and_named = False

        def __init__(self, tokenizer, tools=None):
            super().__init__(tokenizer, tools)
            self._stream = ToolCallStream()

        def adjust_request(self, request):
            request = super().adjust_request(request)
            if request.tools and request.tool_choice != "none":
                request.skip_special_tokens = False
            return request

        def extract_tool_calls(self, model_output: str, request) -> ExtractedToolCallInformation:
            calls, content = parse_tool_calls(model_output)
            if not calls:
                return ExtractedToolCallInformation(tools_called=False, tool_calls=[], content=model_output)
            tool_calls = []
            for c in calls:
                kw = {"id": c["id"]} if c["id"] else {}
                tool_calls.append(ToolCall(type="function",
                                           function=FunctionCall(name=c["name"], arguments=c["arguments"]), **kw))
            return ExtractedToolCallInformation(tools_called=True, tool_calls=tool_calls, content=content)

        def extract_tool_calls_streaming(self, previous_text, current_text, delta_text, previous_token_ids,
                                         current_token_ids, delta_token_ids, request):
            content, new_calls = self._stream.feed(current_text)
            deltas = []
            for c in new_calls:
                index = len(self.prev_tool_call_arr)
                self.prev_tool_call_arr.append({"name": c["name"], "arguments": c["arguments"]})
                self.streamed_args_for_tool.append(c["arguments"])
                self.current_tool_id = index
                deltas.append(DeltaToolCall(
                    index=index, type="function", id=c["id"] or _make_call_id(),
                    function=DeltaFunctionCall(name=c["name"], arguments=c["arguments"]).model_dump(exclude_none=True),
                ))
            if content is None and not deltas:
                return None
            return DeltaMessage(content=content, tool_calls=deltas)

    # Eager registration: the class objects themselves, no lazy re-import by module name.
    ReasoningParserManager.register_module(name="g10", module=G10ReasoningParser)
    ToolParserManager.register_module(name="g10", module=G10ToolParser)
