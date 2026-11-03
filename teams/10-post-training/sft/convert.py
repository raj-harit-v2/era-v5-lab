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
import importlib.util
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable, Iterator

TEAM = Path(__file__).resolve().parents[1]
LICENCE_TABLE = TEAM / "licences" / "licence_table.md"


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


# set id -> (adapter, source id field, Hugging Face config/split, row selection or None, selection note)
ADAPTERS: dict[str, tuple[Callable[[dict], list[dict]], str, tuple[str, str], Callable[[dict], bool] | None, str]] = {
    "sft-code-commitpackft": (commitpackft, "commit", ("python", "train"), None, ""),
    "sft-code-codeforces-cots": (codeforces_cots, "id", ("solutions", "train"), None, ""),
    "sft-code-swe-rebench-openhands": (swe_rebench_openhands, "trajectory_id", ("default", "train"), None, ""),
    "sft-indic-aya-dataset": (
        aya_dataset, "", ("default", "train"),
        lambda row: row["language_code"] in AYA_INDIC, "language_code in " + ",".join(sorted(AYA_INDIC)),
    ),
}


# --- licence table ---------------------------------------------------------------------------

def licence_row(set_id: str, table: Path = LICENCE_TABLE) -> dict:
    """Read one set's row from the Stage 1 (SFT) table of licence_table.md."""
    stage1 = table.read_text(encoding="utf-8").split("### Stage 1", 1)[1].split("\n### ", 1)[0]
    for line in stage1.splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(cells) == 6 and cells[0] == set_id:
            source = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cells[1])
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
    set_id: str, rows: Iterable[dict], limit: int | None, tokenizer_path: str | None, first_index: int = 0
) -> tuple[list[str], dict]:
    """Convert up to `limit` selected rows. Returns (JSONL lines, manifest).

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
    skipped: Counter = Counter()
    efforts: Counter = Counter()
    scanned = taken = tokens = trained = 0
    for index, row in enumerate(rows):
        scanned += 1
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
            lines.append(json.dumps(sample, ensure_ascii=False) + "\n")
        if limit and taken >= limit:
            break

    manifest = {
        **meta,
        "rows_scanned": scanned,
        "rows_in": taken,
        "rows": len(lines),
        "skipped": dict(skipped.most_common()),
        "effort": {e: efforts[e] for e in EFFORTS},
        "content_sha256": hashlib.sha256("".join(lines).encode("utf-8")).hexdigest(),
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", required=True, choices=sorted(ADAPTERS))
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=Path, help="local .parquet or .jsonl with the set's own columns")
    src.add_argument("--hf-rows", type=int, help="fetch this many rows from the Hugging Face datasets-server")
    ap.add_argument("--hf-offset", type=int, default=0)
    ap.add_argument("--limit", type=int, help="stop after this many selected rows")
    ap.add_argument("--tokenizer", help="tokenizer.json for real token counts, input_ids and loss_mask")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    meta = licence_row(a.set)
    check_allowed(meta)
    if a.input:
        rows, where = read_rows(a.input), f"file {a.input.name}"
    else:
        config, split = ADAPTERS[a.set][2]
        rows = hf_rows(meta["source"], config, split, a.hf_offset, a.hf_rows)
        where = f"datasets-server {meta['source']} {config}/{split} rows {a.hf_offset}..{a.hf_offset + a.hf_rows - 1}"
    lines, manifest = convert(a.set, rows, a.limit, a.tokenizer, a.hf_offset if a.hf_rows else 0)
    manifest["input"] = where
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes("".join(lines).encode("utf-8"))
    Path(f"{a.out}.manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("set", "rows_in", "rows", "skipped", "effort", "content_sha256")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
