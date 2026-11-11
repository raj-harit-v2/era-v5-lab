"""Convert one candidate SFT set to chat-format v0 JSONL with loss masks and a manifest.

Every row goes through `chat-format/render.py` unchanged, so the text is exactly what
`render()` produces and `parse()` reads back. The loss mask is a list of half-open character
spans `[start, end)`: each assistant turn body (think span, tool calls, visible reply) and
its closing `<|im_end|>` are trained (1). System (with the effort line), user and tool turns,
the `<|im_start|>assistant` header, the newline after `<|im_end|>` and the final
`<|endoftext|>` are not (0). With `--tokenizer`, each row also gets `input_ids` and a 0/1
`loss_mask` per token; a token is trained only if it lies fully inside a span.

The effort level is the smallest budget (1k, 4k, 16k, 64k) that holds the row's trace: every
think span, tool call and tool result with their markers (`sft_mix_proposal.md` section 4).
Without `--tokenizer` the count is an estimate (UTF-8 bytes / 4), recorded in the manifest.

Licence, source, generator model and decision come from the Stage 1 table in
`licences/licence_table.md`. Sets marked `excluded`, or missing from the table, are refused.
Rows that do not fit the chat format are skipped and counted by reason, never patched.

Usage:
    python convert.py --set sft-code-codeforces-cots --hf-rows 1000 --out out/codeforces.jsonl
    python convert.py --set sft-indic-aya-dataset --input aya_train.parquet --limit 1000 \
        --out out/aya.jsonl --tokenizer tokenizer.json

Writes `<out>` and `<out>.manifest.json`. Data files are never committed.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import http.client
import io
import importlib.util
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable, Iterator

TEAM = Path(__file__).resolve().parents[1]
LICENCE_TABLE = TEAM / "licences" / "licence_table.md"
BYTES_READ = 0  # bytes fetched from the Hub by this process (progress reporting)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render = _load("g10_render", TEAM / "chat-format" / "render.py")
text_prep = _load("g10_text_prep", TEAM / "swe-task" / "hindi_text_prep.py")
T = render.T
EFFORTS = sorted(render.EFFORT_BUDGETS, key=render.EFFORT_BUDGETS.get)
ASSISTANT_HEAD = f"{T['im_start']}assistant\n"
TRACE = re.compile(
    "|".join(
        f"{re.escape(T[a])}.*?{re.escape(T[b])}"
        for a, b in (("think", "think_end"), ("tool_call", "tool_call_end"), ("tool_result", "tool_result_end"))
    ),
    re.S,
)


class Skip(Exception):
    """The row is left out; the message is the reason counted in the manifest."""


# --- adapters: one source row -> chat-format messages ----------------------------------------

def commitpackft(row: dict) -> list[dict]:
    if "instruction" in row and "response" in row:
        return [
            {"role": "user", "content": row["instruction"]},
            {"role": "assistant", "content": row["response"]},
        ]
    subject = row["subject"]
    old_contents = row["old_contents"]
    new_contents = row["new_contents"]
    user_prompt = f"{subject}\n\n{old_contents}".strip() if old_contents else subject
    return [
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": new_contents},
    ]


def self_oss_instruct(row: dict) -> list[dict]:
    return [
        {"role": "user", "content": row["instruction"]},
        {"role": "assistant", "content": row["response"]},
    ]


_THINK = re.compile(r"\s*<think>(.*?)</think>\s*(.*)", re.S)


def codeforces_cots(row: dict) -> list[dict]:
    if row.get("finish_reason") != "stop":
        raise Skip("generation did not finish (finish_reason != stop)")
    messages = []
    for message in row["messages"]:
        if message["role"] != "assistant":
            messages.append({"role": message["role"], "content": message["content"]})
            continue
        hit = _THINK.fullmatch(message["content"])
        if not hit:
            raise Skip("assistant turn does not start with one <think>...</think> block")
        messages.append({"role": "assistant", "think": hit[1].strip(), "content": hit[2]})
    return messages


def swe_rebench_openhands(row: dict) -> list[dict]:
    if row.get("resolved") != 1:
        raise Skip("trajectory did not resolve the issue (resolved != 1)")
    messages = []
    for index, message in enumerate(row["trajectory"]):
        role, content = message["role"], message.get("content") or ""
        if role == "system" and index == 0:
            # Tool schemas go in the system turn as plain JSON text (chat_format_v0.md, Tier 1).
            tools = json.dumps(row["tools"], ensure_ascii=False, sort_keys=True)
            messages.append({"role": "system", "content": f"{content}\n\nTools:\n{tools}"})
        elif role == "assistant":
            calls = [{"function": c["function"], "id": c.get("id")} for c in message.get("tool_calls") or []]
            messages.append({"role": "assistant", "content": content, "tool_calls": calls})
        else:
            messages.append({"role": role, "content": content})
    return messages


# The 10 Indic languages of the proposal (hi, mr, ta, te, kn, bn, gu, ml, or, pa), as aya's ISO 639-3 codes.
AYA_INDIC = frozenset({"hin", "mar", "tam", "tel", "kan", "ben", "guj", "mal", "ory", "pan"})


def aya_dataset(row: dict) -> list[dict]:
    # G10 text-prep rule: strip U+200B and U+FEFF only; ZWJ/ZWNJ stay; no NFKC.
    return [
        {"role": "user", "content": text_prep.prepare_text(row["inputs"])},
        {"role": "assistant", "content": text_prep.prepare_text(row["targets"])},
    ]


# indic-align columns for the same 10 languages. Only native script: in the `_Latn` columns the
# turn order is not reliable (answer before question in Dolly_T).
INDIC_ALIGN_COLUMNS = ("ben_Beng", "guj_Gujr", "hin_Deva", "kan_Knda", "mal_Mlym",
                       "mar_Deva", "ory_Orya", "pan_Guru", "tam_Taml", "tel_Telu")


def indic_align_column(doc_id: str) -> str:
    """One language per source conversation, fixed by its doc_id.

    Every row holds the same conversation translated into each language; taking all of them
    would add ten near-copies of one conversation.
    """
    digest = hashlib.sha256(doc_id.encode("utf-8")).digest()
    return INDIC_ALIGN_COLUMNS[int.from_bytes(digest[:8], "big") % len(INDIC_ALIGN_COLUMNS)]


def indic_align_t(row: dict) -> list[dict]:
    # Each inner list alternates user, assistant, user, ... A thread that ends on a user turn
    # has no reply to train on, so that last turn is dropped.
    threads = row[indic_align_column(row["doc_id"])]
    if threads and len(threads[-1]) % 2:
        threads = [*threads[:-1], threads[-1][:-1]]
    if not threads or any(not thread or len(thread) % 2 for thread in threads):
        raise Skip("translated turns do not alternate user, assistant")
    return [{"role": ("user", "assistant")[i % 2], "content": text_prep.prepare_text(text)}
            for thread in threads for i, text in enumerate(thread)]


DOLLY_SOURCE = ("databricks/databricks-dolly-15k", "databricks-dolly-15k.jsonl")
_dolly_no_context: frozenset[str] | None = None


def dolly_no_context_questions() -> frozenset[str]:
    """English instructions of the Dolly rows that have no context passage (read once from the Hub file)."""
    global _dolly_no_context
    if _dolly_no_context is None:
        _dolly_no_context = frozenset(row["instruction"].strip() for row in hf_file_rows(*DOLLY_SOURCE, 0, 10**9)
                                      if not (row.get("context") or "").strip())
    return _dolly_no_context


def dolly_t_without_context(row: dict) -> bool:
    """Dolly_T drops Dolly's context passage, so a row whose question had one would ask about text that is
    not there. Keep a row only if its English question matches a Dolly row with no context."""
    eng = row.get("eng_Latn") or []
    return bool(eng and eng[0]) and eng[0][0].strip() in dolly_no_context_questions()


# --- adapters for the nvidia / open-r1 families (reasoning_content, tool_calls, tool turns) -----

def _text(value) -> str:
    """Message or tool content as text: JSON objects (some tool results) are written out as JSON."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def nemotron_chat(row: dict) -> list[dict]:
    """Rows with `messages` of role/content plus optional reasoning_content, tool_calls and tool turns.

    Covers Nemotron CUDA, Agentic v1/v2 (tool calling), Math v2/v4/Proofs, Science and the
    Instruction-Following sets. An empty system turn is dropped.
    """
    messages: list[dict] = []
    for message in row["messages"]:
        role, content = message["role"], _text(message.get("content"))
        if role == "system" and not content.strip():
            continue
        if role == "assistant":
            out: dict = {"role": "assistant", "content": content}
            think = message.get("reasoning_content") or message.get("reasoning")
            if think:
                out["think"] = str(think).strip()
            calls = [{"function": c["function"], "id": c.get("id")} for c in message.get("tool_calls") or []]
            if calls:
                out["tool_calls"] = calls
            if not content.strip() and not calls and not think:
                raise Skip("assistant turn is empty")
            messages.append(out)
        elif role == "tool":
            # Commands with no output come back empty; render.py needs a non-empty tool turn.
            messages.append({"role": "tool", "content": content if content.strip() else "(no output)"})
        else:
            messages.append({"role": role, "content": content})
    if row.get("tools") and messages and messages[0]["role"] == "system":
        tools = json.dumps(row["tools"], ensure_ascii=False, sort_keys=True)
        messages[0] = {"role": "system", "content": f"{messages[0]['content']}\n\nTools:\n{tools}"}
    elif row.get("tools"):
        tools = json.dumps(row["tools"], ensure_ascii=False, sort_keys=True)
        messages.insert(0, {"role": "system", "content": f"Tools:\n{tools}"})
    return messages


def xlam_function_calling(row: dict) -> list[dict]:
    """Salesforce xLAM: `query`, `tools` and `answers` (the last two are JSON text). One user turn, one assistant turn of tool calls."""
    try:
        tools, answers = json.loads(row["tools"]), json.loads(row["answers"])
    except (TypeError, ValueError):
        raise Skip("tools or answers is not valid JSON") from None
    calls = [{"function": {"name": a["name"], "arguments": a.get("arguments") or {}}, "id": None}
             for a in answers if isinstance(a, dict) and a.get("name")]
    if not calls or len(calls) != len(answers):
        raise Skip("no usable tool call")
    system = "Tools:\n" + json.dumps(tools, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": system}, {"role": "user", "content": _text(row["query"])},
            {"role": "assistant", "content": "", "tool_calls": calls}]


def think_tag_messages(row: dict) -> list[dict]:
    """`messages` or `conversations` whose assistant turns carry one leading <think>...</think> block
    (Nemotron Cascade SWE, Nemotron Terminal)."""
    source = row.get("messages") or row.get("conversations")
    messages = []
    for message in source:
        if message["role"] != "assistant":
            # The Cascade prompts end with a sentence naming the tags; render.py refuses the literal
            # tags in content, so the sentence is written with square brackets.
            text = message["content"].replace("</think>", "[/think]").replace("<think>", "[think]")
            messages.append({"role": message["role"], "content": text})
            continue
        hit = _THINK.fullmatch(message["content"])
        messages.append(
            {"role": "assistant", "think": hit[1].strip(), "content": hit[2]} if hit
            else {"role": "assistant", "content": message["content"]}
        )
    return messages


def opencodereasoning(row: dict) -> list[dict]:
    hit = _THINK.fullmatch(row["output"])
    if not hit:
        raise Skip("output does not start with one <think>...</think> block")
    return [
        {"role": "user", "content": row["input"]},
        {"role": "assistant", "think": hit[1].strip(), "content": hit[2]},
    ]


def dolly(row: dict) -> list[dict]:
    prompt = f"{row['instruction']}\n\n{row['context']}".strip() if row.get("context") else row["instruction"]
    return [{"role": "user", "content": prompt}, {"role": "assistant", "content": row["response"]}]


def openmathreasoning(row: dict) -> list[dict]:
    if row.get("inference_mode") != "cot":
        raise Skip("tool-integrated (non-cot) solution")
    hit = _THINK.fullmatch(row["generated_solution"])
    if not hit:
        raise Skip("solution does not start with one <think>...</think> block")
    return [{"role": "user", "content": row["problem"]},
            {"role": "assistant", "think": hit[1].strip(), "content": hit[2]}]


def _raw_verified(row: dict) -> bool:
    """Licence table: keep OpenR1-Math-Raw rows with a passing correctness flag (here: the first generation's)."""
    ok = ((row.get("correctness") or {}).get("llama_verification") or [False])[0]
    return ok is True


def openr1_math_raw(row: dict) -> list[dict]:
    """Problem plus the first generation; the Raw set has no `messages`."""
    hit = _THINK.fullmatch(row["generations"][0] or "")
    if not hit:
        raise Skip("first generation does not start with one <think>...</think> block")
    return [{"role": "user", "content": row["problem"]},
            {"role": "assistant", "think": hit[1].strip(), "content": hit[2]}]


_SHAREGPT_ROLE = {"human": "user", "gpt": "assistant", "system": "system"}


def sharegpt_think(row: dict) -> list[dict]:
    """OpenThoughts3: `conversations` of from/value; the gpt turn opens with <think> ... </think>."""
    messages = []
    for turn in row["conversations"]:
        role = _SHAREGPT_ROLE[turn["from"]]
        if role != "assistant":
            messages.append({"role": role, "content": turn["value"]})
            continue
        hit = _THINK.fullmatch(turn["value"])
        if not hit:
            # In OpenThoughts3 most unmatched turns open <think> and never close it (cut-off reasoning).
            raise Skip("assistant turn is not one <think>...</think> block (reasoning not closed)")
        messages.append({"role": "assistant", "think": hit[1].strip(), "content": hit[2]})
    return messages


def opencodereasoning_2(row: dict) -> list[dict]:
    # Most questions are withheld upstream and stored as "-"; without the question there is no prompt.
    if row["question"].strip() in ("", "-"):
        raise Skip("question is withheld upstream (stored as '-')")
    hit = _THINK.fullmatch(row["r1_generation"])
    if not hit:
        raise Skip("generation does not start with one <think>...</think> block")
    return [{"role": "user", "content": row["question"]},
            {"role": "assistant", "think": hit[1].strip(), "content": hit[2]}]


def nemotron_chat_nonempty(row: dict) -> list[dict]:
    if not row.get("messages"):
        raise Skip("row has no messages (statement only)")
    return nemotron_chat(row)


_BESPOKE = re.compile(r"\s*<\|begin_of_thought\|>(.*?)<\|end_of_thought\|>\s*<\|begin_of_solution\|>(.*?)<\|end_of_solution\|>\s*", re.S)


def bespoke_stratos(row: dict) -> list[dict]:
    """Thought and solution blocks of Bespoke-Stratos become the think span and the answer.

    The row's `system` prompt only explains those blocks, so it is not carried over.
    """
    messages = []
    for turn in row["conversations"]:
        if turn["from"] == "user":
            messages.append({"role": "user", "content": turn["value"]})
            continue
        hit = _BESPOKE.fullmatch(turn["value"])
        if not hit:
            raise Skip("assistant turn is not one thought block followed by one solution block")
        messages.append({"role": "assistant", "think": hit[1].strip(), "content": hit[2].strip()})
    return messages


def swe_zero(row: dict) -> list[dict]:
    """OpenHands trajectories without a tool list or a resolved flag; rows with no final patch are left out."""
    if not (row.get("model_patch") or "").strip():
        raise Skip("trajectory has no model_patch")
    messages = []
    for message in row["trajectory"]:
        role, content = message["role"], _text(message.get("content"))
        if role == "assistant":
            calls = [{"function": c["function"], "id": c.get("id")} for c in message.get("tool_calls") or []]
            messages.append({"role": "assistant", "content": content, **({"tool_calls": calls} if calls else {})})
        elif role == "tool":
            messages.append({"role": "tool", "content": content if content.strip() else "(no output)"})
        else:
            messages.append({"role": role, "content": content})
    return messages


def oasst2_thread(row: dict) -> list[dict]:
    """One root-to-leaf thread built by `oasst2_threads`; roles are already user / assistant."""
    if not row["messages"] or row["messages"][-1]["role"] != "assistant":
        raise Skip("thread does not end on an assistant reply")
    return [{"role": m["role"], "content": m["text"]} for m in row["messages"]]


def oasst2_threads(dataset: str, path: str, offset: int, n: int) -> Iterator[dict]:
    """Read the oasst2 parquet from the Hub and rebuild threads (see `oasst2_build`)."""
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(io.BufferedReader(_RangeFile(f"https://huggingface.co/datasets/{dataset}/resolve/main/{urllib.parse.quote(path)}"),
                                          buffer_size=4 << 20))
    yield from oasst2_build((m for batch in pf.iter_batches(batch_size=4096) for m in batch.to_pylist()), offset, n)


def oasst2_build(messages: Iterable[dict], offset: int, n: int) -> Iterator[dict]:
    """OpenAssistant oasst2 stores one message per row. Rebuild threads: for each prompt, follow only the
    best-ranked (rank 0, or unranked when alone) reply at every step, one thread per prompt.
    Deleted, synthetic and non-exported trees are left out."""
    by_parent: dict[str | None, list[dict]] = {}
    for m in messages:
        if m["deleted"] or m["synthetic"] or m["tree_state"] != "ready_for_export":
            continue
        by_parent.setdefault(m["parent_id"], []).append(m)

    def best(children: list[dict]) -> dict | None:
        ranked = sorted(children, key=lambda c: (c["rank"] is None, c["rank"] if c["rank"] is not None else 0, c["message_id"]))
        return ranked[0] if ranked else None

    count = 0
    for root in sorted(by_parent.get(None, []), key=lambda m: m["message_id"]):
        thread = [root]
        while True:
            nxt = best(by_parent.get(thread[-1]["message_id"], []))
            if nxt is None:
                break
            thread.append(nxt)
        count += 1
        if count <= offset:
            continue
        yield {"id": root["message_id"], "lang": root["lang"],
               "messages": [{"role": "user" if m["role"] == "prompter" else "assistant", "text": m["text"]} for m in thread]}
        if count >= offset + n:
            return


AYA_COLLECTION_SUBSETS = tuple(
    f"templated_{name}/train-00000-of-00001.parquet"
    for name in ("bengali_news", "hindi_headline", "hindi_news", "indic_paraphrase", "indic_sentiment", "tamil_stories",
                 "tamil_thirukkural", "telugu_food", "telugu_jokes", "telugu_news", "telugu_poems", "telugu_riddles")
)


def aya_collection(row: dict) -> list[dict]:
    if not row["inputs"].strip() or not row["targets"].strip():
        raise Skip("empty input or target")
    return [
        {"role": "user", "content": text_prep.prepare_text(row["inputs"])},
        {"role": "assistant", "content": text_prep.prepare_text(row["targets"])},
    ]


def aya_collection_rows(dataset: str, _path: str, offset: int, n: int) -> Iterator[dict]:
    """The 12 Indic templated subsets, an equal share of `n` rows from the start of each (offset applies per subset)."""
    share = max(1, n // len(AYA_COLLECTION_SUBSETS))
    for path in AYA_COLLECTION_SUBSETS:
        for attempt in range(4):
            try:
                rows = list(hf_file_rows(dataset, path, offset, share))
                break
            except OSError:  # URLError and connection resets on the Hub
                if attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))
        for row in rows:
            row["subset"] = path.split("/")[0]
            yield row


# set id -> (adapter, source id field, Hugging Face config/split, row selection or None, selection note)
ADAPTERS: dict[str, tuple[Callable[[dict], list[dict]], str, tuple[str, str], Callable[[dict], bool] | None, str]] = {
    "sft-code-commitpackft": (commitpackft, "commit", ("file", "glob:data/*/data.jsonl"), None, "all 277 language files (data/<language>/data.jsonl)"),
    "sft-code-codeforces-cots": (codeforces_cots, "id", ("file", "glob:solutions/"), None, "solutions config"),
    "sft-code-swe-rebench-openhands": (swe_rebench_openhands, "trajectory_id", ("file", "trajectories.parquet"), None, ""),
    "sft-indic-aya-dataset": (
        aya_dataset, "", ("file", "data/train-00000-of-00001.parquet"),
        lambda row: row["language_code"] in AYA_INDIC, "language_code in " + ",".join(sorted(AYA_INDIC)),
    ),
    "sft-indic-indic-align-oasst-t": (
        indic_align_t, "doc_id", ("file", "indicalign-instruct/oasst/oasst.parquet"), None,
        "one native-script column per row by sha256(doc_id) from " + ",".join(INDIC_ALIGN_COLUMNS),
    ),
    "sft-code-nemotron-cuda": (nemotron_chat, "", ("file", "data/train.jsonl"), None, ""),
    "sft-agentic-nemotron-agentic-v1": (nemotron_chat, "uuid", ("file", "data/tool_calling.jsonl"), None, "tool_calling file"),
    "sft-agentic-nemotron-sft-agentic-v2-tool-calling": (nemotron_chat, "", ("file", "data/tool_calling.jsonl"), None, ""),
    "sft-math-nemotron-math-v2": (nemotron_chat, "uuid", ("file", "glob:data/*.parquet"), None,
        "all 5 parquet files (high x3, medium, low); the jsonl copies of the same data are not read"),
    "sft-code-nemotron-cascade-swe": (think_tag_messages, "", ("file", "swe_localization.jsonl|swe_repair.jsonl|swe_testgen.jsonl"), None,
        "all three files (localization, repair, testgen)"),
    "sft-code-opencodereasoning": (opencodereasoning, "id", ("file", "glob:split_0/"), None,
        "split_0, all 30 shards (split_1 withholds the questions)"),
    "sft-math-nemotron-sft-math-v4": (nemotron_chat, "uuid", ("file", "glob:data/"), None, "all 12 shards"),
    "sft-rl-math-openmathreasoning": (openmathreasoning, "", ("file", "glob:data/cot-"), None, "all 144 cot shards"),
    "sft-math-openr1-math": (think_tag_messages, "uuid", ("file", "glob:all/train-"), None, "config all, 20 shards"),
    "sft-math-openr1-math-raw": (openr1_math_raw, "", ("file", "glob:data/"), _raw_verified,
        "all 39 shards; first generation, rows whose first generation passes llama_verification"),
    "sft-stem-code-openthoughts3": (sharegpt_think, "", ("file", "glob:data/*.parquet"), None, "all 120 parquet shards"),
    "sft-code-opencodereasoning-2": (opencodereasoning_2, "id", ("file", "train/python/train-00000-of-00070.parquet"), None, "python, first shard"),
    "sft-science-nemotron-science": (nemotron_chat, "uuid", ("file", "data/MCQ.jsonl"), None, "MCQ file"),
    "sft-chat-nemotron-if-v1": (nemotron_chat, "uuid", ("file", "data/structured_outputs.jsonl"), None, "structured_outputs file"),
    "sft-chat-nemotron-if-v2": (nemotron_chat, "uuid", ("file", "data/reasoning_on.jsonl"), None, "reasoning_on file"),
    "sft-math-nemotron-proofs": (nemotron_chat_nonempty, "uuid", ("file", "data/lean.jsonl"), None, "whole lean file"),
    "sft-bespoke-stratos-17k": (bespoke_stratos, "", ("file", "data/train-00000-of-00001.parquet"), None, ""),
    "sft-code-swe-zero-openhands": (swe_zero, "trajectory_id", ("file", "glob:data/"), None, "all 64 shards"),
    "sft-code-nemotron-terminal": (think_tag_messages, "", ("file", "dataset_adapters/code.parquet"), None, "code adapter file"),
    "sft-science-nemotron-science-v2": (nemotron_chat, "uuid", ("file", "syn_mcq.jsonl"), None, "syn_mcq file"),
    "sft-code-nemotron-opencode": (nemotron_chat, "uuid", ("file", "agent_skills/data.jsonl"), None, "agent_skills file"),
    "sft-indic-indic-align-dolly-t": (
        indic_align_t, "doc_id", ("file", "indicalign-instruct/dolly/Dolly.parquet"), dolly_t_without_context,
        "rows whose English question has no context passage in databricks-dolly-15k; one native-script column "
        "per row by sha256(doc_id) from " + ",".join(INDIC_ALIGN_COLUMNS),
    ),
    "sft-science-glm51-phd": (sharegpt_think, "id", ("file", "PHD-Science.jsonl"), None, "PHD-Science config"),
    "sft-salesforce-xlam-60k": (xlam_function_calling, "id", ("file", "xlam_function_calling_60k.json"), None, "all rows"),
    "sft-math-nemotron-proofs-v3-sft": (nemotron_chat, "uuid", ("file", "glob:data/*.jsonl"), None, "all 10 jsonl files"),
    "sft-oasst2": (oasst2_thread, "id", ("oasst2", "data/train-00000-of-00001-88ba0162028a73fc.parquet"), None,
                   "best-ranked reply at each step; not deleted, not synthetic, ready_for_export trees"),
    "sft-indic-aya-collection": (aya_collection, "", ("aya", ""), None,
                                 "12 templated Indic subsets, equal share of rows from the start of each"),
    "sft-dolly-15k": (dolly, "", ("file", "databricks-dolly-15k.jsonl"), None, ""),
}


# --- licence table ---------------------------------------------------------------------------

def licence_row(set_id: str, table: Path = LICENCE_TABLE) -> dict:
    """Read one set's row from the Stage 1 (SFT) table of licence_table.md."""
    stage1 = table.read_text(encoding="utf-8").split("### Stage 1", 1)[1].split("\n### ", 1)[0]
    for line in stage1.splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(cells) == 6 and cells[0] == set_id:
            source = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cells[1]).split(" (")[0]
            return {"set": set_id, "source": source, "language": cells[2], "generator_model": cells[3],
                    "licence": cells[4], "decision": cells[5]}
    raise SystemExit(f"{set_id} is not in the Stage 1 table of {table}")


def check_allowed(row: dict) -> None:
    if not row["decision"].startswith(("TSAI reserves", "allowed")):
        raise SystemExit(f"{row['set']} has decision {row['decision']!r}; only TSAI reserves or allowed sets convert")


# --- one row -> one sample -------------------------------------------------------------------

def train_spans(text: str) -> list[tuple[int, int]]:
    """Character spans SFT trains on: each assistant body plus its <|im_end|>.

    Content can never hold a chat marker (render rejects it), so the markers are unambiguous.
    """
    spans, pos = [], 0
    while (start := text.find(ASSISTANT_HEAD, pos)) >= 0:
        start += len(ASSISTANT_HEAD)
        end = text.index(T["im_end"], start) + len(T["im_end"])
        spans.append((start, end))
        pos = end
    return spans


def token_mask(spans: list[tuple[int, int]], offsets: list[tuple[int, int]]) -> list[int]:
    """0/1 per token: 1 only if the token's (start, end) lies fully inside one span.

    A token that straddles a span edge, or a zero-width token the tokenizer adds itself, is 0,
    so no prompt character is ever a target. `spans` must be sorted and must not overlap.
    """
    starts = [start for start, _ in spans]
    mask = []
    for start, end in offsets:
        i = bisect.bisect_right(starts, start) - 1
        mask.append(int(start < end and i >= 0 and end <= spans[i][1]))
    return mask


def pick_effort(trace_tokens: int) -> str:
    for effort in EFFORTS:
        if trace_tokens <= render.EFFORT_BUDGETS[effort]:
            return effort
    raise Skip("trace over the 64k effort budget")


def convert_row(messages: list[dict], count: Callable[[str], int]) -> tuple[str, str, list[tuple[int, int]]]:
    """Render one transcript; return (effort, text, train spans). Raises Skip if it does not fit."""
    if any(m.get("role") == "user" and not m.get("content") for m in messages):
        raise Skip("empty user turn")
    try:
        probe = render.render(messages, EFFORTS[0])  # the trace does not depend on the effort line
        effort = pick_effort(sum(count(m.group()) for m in TRACE.finditer(probe)))
        text = render.render(messages, effort)
    except render.RenderError as exc:
        raise Skip(re.sub(r"^message \d+ ", "", str(exc))) from None
    if render.parse(text)["effort"] != effort:  # every written row must read back
        raise AssertionError("render/parse disagree")
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        raise Skip("text has a lone surrogate (not valid UTF-8)") from None
    spans = train_spans(text)
    if any(end - start == len(T["im_end"]) for start, end in spans):
        raise Skip("empty assistant turn")
    return effort, text, spans


def convert(
    set_id: str, rows: Iterable[dict], limit: int | None, tokenizer_path: str | None, first_index: int = 0, sink=None, progress=None
) -> tuple[list[str], dict]:
    """Convert up to `limit` selected rows. Returns (JSONL lines, manifest).

    With `sink` (a text file open for writing) the lines are written there as they are made and the returned
    list is empty, so a large set does not have to fit in memory; the manifest is the same.

    A row's id is `<set>/<row index in the source split>` (`first_index` is the index of the first
    row given), so ids stay unique when a source repeats its own ids (codeforces-cots has several
    generations per problem). The source's own id, if it has one, is kept as `source_id`.
    """
    meta = licence_row(set_id)
    check_allowed(meta)
    adapter, id_field, _, select, select_note = ADAPTERS[set_id]
    if tokenizer_path:
        from tokenizers import Tokenizer

        tok = Tokenizer.from_file(tokenizer_path)

        def count(text: str) -> int:
            return len(tok.encode(text, add_special_tokens=False).ids)

        counter = "tokenizer sha256 " + hashlib.sha256(Path(tokenizer_path).read_bytes()).hexdigest()
    else:
        tok = None

        def count(text: str) -> int:
            return (len(text.encode("utf-8")) + 3) // 4

        counter = "estimate: UTF-8 bytes / 4 (no tokenizer given)"

    lines: list[str] = []
    written = 0
    digest = hashlib.sha256()
    skipped: Counter = Counter()
    efforts: Counter = Counter()
    scanned = taken = tokens = trained = 0
    last_report = time.monotonic()
    for index, row in enumerate(rows):
        scanned += 1
        if progress and scanned % 500 == 0 and time.monotonic() - last_report >= 2:
            last_report = time.monotonic()
            progress(scanned, written)
        if select and not select(row):
            continue
        taken += 1
        try:
            try:
                messages = adapter(row)
            except (KeyError, TypeError, AttributeError) as exc:
                raise Skip(f"missing or malformed field ({type(exc).__name__})") from None
            effort, text, spans = convert_row(messages, count)
        except Skip as exc:
            skipped[str(exc)] += 1
        else:
            efforts[effort] += 1
            sample = {"id": f"{set_id}/{first_index + index}", "set": set_id}
            if id_field:
                sample["source_id"] = row.get(id_field)
            sample.update(effort=effort, text=text, train_spans=[list(s) for s in spans])
            if tok:
                enc = tok.encode(text, add_special_tokens=False)
                sample["input_ids"] = enc.ids
                sample["loss_mask"] = token_mask(spans, enc.offsets)
                tokens += len(enc.ids)
                trained += sum(sample["loss_mask"])
            line = json.dumps(sample, ensure_ascii=False) + "\n"
            written += 1
            digest.update(line.encode("utf-8"))
            if sink is not None:
                sink.write(line)
            else:
                lines.append(line)
        if limit and taken >= limit:
            break

    manifest = {
        **meta,
        "rows_scanned": scanned,
        "rows_in": taken,
        "rows": written,
        "skipped": dict(skipped.most_common()),
        "effort": {e: efforts[e] for e in EFFORTS},
        "content_sha256": digest.hexdigest(),
        "effort_counter": counter,
        "selection": select_note or "all rows",
    }
    if tok:
        manifest["tokens"], manifest["trained_tokens"] = tokens, trained
    return lines, manifest


# --- input -----------------------------------------------------------------------------------

def read_rows(path: Path) -> Iterator[dict]:
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq

        for batch in pq.ParquetFile(path).iter_batches(batch_size=512):
            yield from batch.to_pylist()
    else:
        with path.open(encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)


def hf_rows(dataset: str, config: str, split: str, offset: int, n: int) -> Iterator[dict]:
    """First rows of a public Hugging Face set through the datasets-server API (100 per call)."""
    for start in range(offset, offset + n, 100):
        query = urllib.parse.urlencode({"dataset": dataset, "config": config, "split": split,
                                        "offset": start, "length": min(100, offset + n - start)})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(f"https://datasets-server.huggingface.co/rows?{query}", timeout=120) as r:
                    page = json.load(r)["rows"]
                break
            except (OSError, ValueError, KeyError, http.client.HTTPException):
                if attempt == 4:
                    raise
                time.sleep(5 * (attempt + 1))
        if not page:
            return
        for want, item in enumerate(page, start):
            # never convert a truncated cell or a row from the wrong offset
            if item["row_idx"] != want or item.get("truncated_cells"):
                raise RuntimeError(f"datasets-server row {want}: got row_idx {item['row_idx']}, "
                                   f"truncated {item.get('truncated_cells')}")
            yield item["row"]


class _RangeFile(io.RawIOBase):
    """Read-only, seekable view of a remote file through HTTP range requests (for parquet footers and row groups)."""

    def __init__(self, url: str):
        self.url, self.pos = url, 0
        request = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
        with urllib.request.urlopen(request, timeout=120) as r:
            self.size = int(r.headers["Content-Range"].rsplit("/", 1)[1])

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = (offset, self.pos + offset, self.size + offset)[whence]
        return self.pos

    def readinto(self, buffer) -> int:
        want = min(len(buffer), self.size - self.pos)
        if want <= 0:
            return 0
        for attempt in range(5):
            try:
                request = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + want - 1}"})
                with urllib.request.urlopen(request, timeout=120) as r:
                    data = r.read()
                break
            except (OSError, http.client.HTTPException):
                if attempt == 4:
                    raise
                time.sleep(5 * (attempt + 1))
        global BYTES_READ
        buffer[: len(data)] = data
        self.pos += len(data)
        BYTES_READ += len(data)
        return len(data)


def local_path(dataset: str, path: str) -> Path | None:
    """`$G10_LOCAL_ROOT/<dataset>/<path>` when that variable is set and the file or folder exists (a downloaded copy)."""
    root = os.environ.get("G10_LOCAL_ROOT")
    if not root:
        return None
    p = Path(root) / dataset / path
    return p if p.exists() else None


def expand_paths(dataset: str, spec: str) -> list[str]:
    """`a|b` is a list of files; `glob:dir/` is every .parquet or .jsonl file directly under that prefix."""
    if spec.startswith("glob:"):
        prefix, _, suffix = spec[5:].partition("*")  # `glob:data/*.parquet` keeps one file type
        local = local_path(dataset, prefix.rpartition("/")[0] or ".")
        if local is not None and local.is_dir():  # a local copy of the repo (G10_LOCAL_ROOT)
            names = sorted(p.relative_to(local_path(dataset, ".")).as_posix() for p in local.rglob("*")
                           if p.is_file() and p.as_posix().endswith(suffix or (".parquet", ".jsonl"))
                           and p.relative_to(local_path(dataset, ".")).as_posix().startswith(prefix))
            if not names:
                raise SystemExit(f"no data files under {prefix} in the local copy of {dataset}")
            return names
        for attempt in range(4):
            try:
                with urllib.request.urlopen(f"https://huggingface.co/api/datasets/{dataset}/tree/main?recursive=1", timeout=60) as r:
                    tree = json.load(r)
                break
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))
        names = sorted(x["path"] for x in tree if x["path"].startswith(prefix)
                       and x["path"].endswith(suffix or (".parquet", ".jsonl")))
        if not names:
            raise SystemExit(f"no data files under {prefix} in {dataset}")
        return names
    return spec.split("|")


def hf_file_rows(dataset: str, path: str, offset: int, n: int) -> Iterator[dict]:
    """Rows of one or several data files (see `expand_paths`), counted across the files in order.

    A connection reset in the middle of a file is retried from the row where it stopped.
    """
    skipped = left = 0
    for each in expand_paths(dataset, path):
        done = 0
        for attempt in range(8):
            try:
                for row in _one_file_rows(dataset, each, done, n):
                    done += 1
                    if skipped < offset:
                        skipped += 1
                        continue
                    yield row
                    left += 1
                    if left >= n:
                        return
                break
            except (OSError, http.client.HTTPException):  # URLError, connection reset, short read, IncompleteRead
                if attempt == 7:
                    raise
                time.sleep(10 * (attempt + 1))


def _local_file_rows(file: Path, offset: int, n: int) -> Iterator[dict]:
    """The same rows as `_one_file_rows`, from a file on disk."""
    global BYTES_READ
    taken = 0
    if file.suffix == ".parquet":
        import pyarrow.parquet as pq

        pf = pq.ParquetFile(file)
        per_row = file.stat().st_size / max(pf.metadata.num_rows, 1)
        for batch in pf.iter_batches(batch_size=64):
            BYTES_READ += int(per_row * batch.num_rows)
            for row in batch.to_pylist():
                if taken >= offset + n:
                    return
                if taken >= offset:
                    yield row
                taken += 1
        return
    if file.suffix == ".json":  # one JSON array (xLAM, 96 MB): read whole
        BYTES_READ += file.stat().st_size
        yield from json.loads(file.read_text(encoding="utf-8"))[offset:offset + n]
        return
    with open(file, "rb") as f:
        for line in f:
            BYTES_READ += len(line)
            if taken >= offset + n:
                return
            if taken >= offset:
                yield json.loads(line)  # the file was checked against the Hub sha256 when it was downloaded
            taken += 1


def _one_file_rows(dataset: str, path: str, offset: int, n: int) -> Iterator[dict]:
    """First rows of one data file in a public Hugging Face dataset repo (.jsonl or .parquet), read from the start.

    Only the bytes needed are fetched: a .jsonl is streamed and closed after the last row, a .parquet is read
    row group by row group through range requests. Rows are never truncated, unlike the datasets-server API.
    """
    url = f"https://huggingface.co/datasets/{dataset}/resolve/main/{urllib.parse.quote(path)}"
    taken = 0
    local = local_path(dataset, path)
    if local is not None and local.is_file():
        yield from _local_file_rows(local, offset, n)
        return
    if path.endswith(".json"):  # one JSON array, not lines (xLAM 60k is also gated): it is read from a local copy
        raise SystemExit(f"{dataset}/{path} is a single JSON array: download it and set G10_LOCAL_ROOT to the folder that holds it")
    if path.endswith(".parquet"):
        import pyarrow.parquet as pq

        pf = pq.ParquetFile(io.BufferedReader(_RangeFile(url), buffer_size=4 << 20))
        for batch in pf.iter_batches(batch_size=64):
            for row in batch.to_pylist():
                if taken >= offset + n:
                    return
                if taken >= offset:
                    yield row
                taken += 1
        return
    with urllib.request.urlopen(url, timeout=120) as r:
        global BYTES_READ
        for line in r:
            BYTES_READ += len(line)
            if taken >= offset + n:
                return
            if taken >= offset:
                try:
                    if not line.endswith(b"\n") and not r.isclosed():
                        raise ValueError("line cut short")
                    yield json.loads(line)
                except ValueError as exc:  # a connection that drops mid-line gives a cut-off last line: retry
                    raise OSError(f"truncated download in {path} at row {taken}: {exc}") from None
            taken += 1


class RollingSink:
    """Write JSONL lines into `<prefix>.partNNNN.jsonl` files of about `mb` MB each.

    A part is written under a `.tmp` name and renamed when it is complete, so a reader that looks for `*.jsonl`
    only ever sees whole parts (and a part never ends inside a line).
    """

    def __init__(self, prefix: Path, mb: float):
        self.prefix, self.limit, self.n, self.size, self.f = Path(prefix), int(mb * 1e6), 0, 0, None
        self.parts: list[Path] = []

    def _open(self):
        self.f = open(f"{self.prefix}.part{self.n:04d}.jsonl.tmp", "w", encoding="utf-8", newline="")
        self.size = 0

    def _close(self):
        if self.f:
            self.f.close()
            final = Path(f"{self.prefix}.part{self.n:04d}.jsonl")
            Path(f"{final}.tmp").rename(final)
            self.parts.append(final)
            self.f, self.n = None, self.n + 1

    def write(self, line: str) -> None:
        if self.f is None:
            self._open()
        self.f.write(line)
        self.size += len(line.encode("utf-8"))
        if self.size >= self.limit:
            self._close()

    def close(self) -> None:
        self._close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", required=True, choices=sorted(ADAPTERS))
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=Path, help="local .parquet or .jsonl with the set's own columns")
    src.add_argument("--hf-rows", type=int, help="fetch this many rows from the Hugging Face datasets-server")
    src.add_argument("--hf-file", type=int, metavar="N",
                     help="read N rows from the set's own file in the Hub repo (ranged download, no row-size limit)")
    ap.add_argument("--hf-offset", type=int, default=0)
    ap.add_argument("--limit", type=int, help="stop after this many selected rows")
    ap.add_argument("--tokenizer", help="tokenizer.json for real token counts, input_ids and loss_mask")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--file-spec", help="with --hf-file: read this file (or `a|b` list) instead of the set's whole source")
    ap.add_argument("--index-base", type=int, help="ids start at <set>/<this number> (for parallel runs on file groups)")
    ap.add_argument("--roll-mb", type=float, help="write <out>.partNNNN.jsonl parts of about this size instead of one file")
    ap.add_argument("--progress", type=Path, help="rewrite this JSON file every few seconds with rows and bytes read")
    a = ap.parse_args()

    meta = licence_row(a.set)
    check_allowed(meta)
    if a.input:
        rows, where = read_rows(a.input), f"file {a.input.name}"
    elif a.hf_file:
        kind, path = ADAPTERS[a.set][2]
        path = a.file_spec or path
        reader = {"oasst2": oasst2_threads, "aya": aya_collection_rows}.get(kind, hf_file_rows)
        rows = reader(meta["source"], path, a.hf_offset, a.hf_file)
        where = f"hub file {meta['source']} {path} rows {a.hf_offset}..{a.hf_offset + a.hf_file - 1}"
    else:
        config, split = ADAPTERS[a.set][2]
        rows = hf_rows(meta["source"], config, split, a.hf_offset, a.hf_rows)
        where = f"datasets-server {meta['source']} {config}/{split} rows {a.hf_offset}..{a.hf_offset + a.hf_rows - 1}"
    a.out.parent.mkdir(parents=True, exist_ok=True)
    first = a.index_base if a.index_base is not None else (a.hf_offset if (a.hf_rows or a.hf_file) else 0)

    def report(scanned: int, written: int) -> None:
        if a.progress:
            tmp = Path(f"{a.progress}.tmp")
            tmp.write_text(json.dumps({"rows_scanned": scanned, "rows": written, "bytes_read": BYTES_READ,
                                       "at": time.time()}), encoding="utf-8")
            tmp.replace(a.progress)

    if a.roll_mb:
        sink = RollingSink(a.out, a.roll_mb)
        _, manifest = convert(a.set, rows, a.limit, a.tokenizer, first, sink, report)
        sink.close()
        manifest["parts"] = [p.name for p in sink.parts]
        manifest_path = Path(f"{a.out}.manifest.json")
    else:
        with open(a.out, "w", encoding="utf-8", newline="") as sink:
            _, manifest = convert(a.set, rows, a.limit, a.tokenizer, first, sink, report)
        manifest_path = Path(f"{a.out}.manifest.json")
    report(manifest["rows_scanned"], manifest["rows"])
    manifest["input"] = where
    manifest["index_base"] = first
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("set", "rows_in", "rows", "skipped", "effort", "content_sha256")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
