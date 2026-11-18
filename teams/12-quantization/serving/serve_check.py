"""Serve one checkpoint on vLLM's OpenAI-compatible endpoint with our chat template and parsers, then send 100 fixed
prompts and check that reasoning and tool calls come back in the right fields (G12 week 3, task 4).

    python teams/12-quantization/serving/serve_check.py --model /path/to/checkpoint \\
        --vllm-arg=--max-model-len=4096 --out out

Starts `vllm serve` with:
  * --chat-template      teams/10-post-training/chat-format/chat_template.jinja (G10 v0, unchanged)
  * --reasoning-parser   g10 (plugin g10_parsers.py): <|think|> ... <|/think|>  -> message.reasoning
  * --tool-call-parser   g10 (same plugin), --enable-auto-tool-choice: <|tool_call|>{json}<|/tool_call|> -> message.tool_calls
Then it sends prompts_v1.jsonl (100 prompts, tools from tools_v1.json) at temperature 0, plus a streamed copy of
--stream-check of them. Each answer is checked:
  * fields: no chat marker (<|think|>, <|tool_call|>, <|im_end|>, ...) left in content, reasoning or tool arguments.
    Every answer that has one is replayed: /tokenize renders the same prompt, /v1/completions regenerates the raw
    text at the same settings, and g10_parsers parses it offline. If that gives the fields the server returned, the
    parser did its job and the model broke the G10 layout (for example a think block after the answer); that is
    reported, not failed. Otherwise it counts as a parser fault. Exit code 1 if any request fails or any marker is
    not explained by the replay.
  * behaviour: reason prompts have reasoning, tool prompts call the expected tool with valid JSON arguments,
    no_tool / tool_result prompts call none. This measures the model, not the server. It is reported, not enforced.
  * streaming: the streamed reasoning, content and tool calls equal the non-streamed ones.
Writes to --out: serve_check.md (summary), summary.json, serve_check.jsonl (one row per prompt, texts cut to
2,000 characters), vllm_server.log.

Job request rules (JOB_REQUEST.md): no network except the local server, no keys, reads only its inputs, writes
only --out. --base-url uses a server that is already running and skips the launch.

Stand-in models. Until a config v1 checkpoint is exported (unsupported_parts.md §8), a stand-in model that never
saw our markers is served. --format-hint on (the default) adds a system message that teaches the markers. Use
--format-hint off for a model trained on the G10 format. The G10 template does not render the request's `tools`
list. --tools-in-system auto (the default) therefore writes the tool schemas into the system message when the
template does not mention `tools`.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
from g10_parsers import CALL, MARKERS, THINK, THINK_END, parse_tool_calls, split_reasoning  # noqa: E402

NATIVE_MARKERS = ("<think>", "</think>", "<tool_call>", "</tool_call>")   # a stand-in falling back to its own format
CATEGORIES = ("chat", "reason", "tool", "tool_result", "no_tool")
TEXT_CAP = 2000

FORMAT_HINT = (
    "Answer in this exact format.\n"
    "1. Start with your thinking, once, between the markers <|think|> and <|/think|>, each marker on its own line. "
    "Nothing comes before <|think|>.\n"
    "2. After <|/think|>, write the final answer for the user, in the user's language, with no markers.\n"
)
FORMAT_HINT_TOOLS = (                          # only when the request offers tools: a hint without tools invited calls
    "To call one of the tools below instead of answering, write this right after <|/think|> and nothing after it:\n"
    "<|tool_call|>\n"
    '{"arguments": {"<parameter>": <value>}, "name": "<tool name>"}\n'
    "<|/tool_call|>\n"
    "Call only the tools listed below. If a tool result is already in the conversation, answer from it and do not "
    "call the tool again."
)


# ------------------------------------------------------------------------------ helpers

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    """Repo-relative path when the file is in this repo, else the path as given (a job may copy inputs)."""
    p = path.resolve()
    return str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(path)


def http_json(url: str, body: dict | None = None, timeout: float = 600.0):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode())


def http_stream(url: str, body: dict, timeout: float = 600.0):
    """Yield the JSON chunks of an SSE stream."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if payload == "[DONE]":
                return
            yield json.loads(payload)


def gpu_info() -> str:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return "none (nvidia-smi not found)"
    try:
        out = subprocess.run([exe, "--query-gpu=name,memory.total,compute_cap", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        return out.replace("\n", "; ") or "unknown"
    except Exception as e:                                            # noqa: BLE001
        return f"unknown ({e})"


def versions() -> dict:
    from importlib import metadata
    out = {"python": platform.python_version()}
    for pkg in ("vllm", "torch", "transformers"):
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            out[pkg] = None
    return out


def leaks(text: str | None, markers) -> list[str]:
    return [m for m in markers if text and m in text]


def to_ascii_digits(text: str) -> str:
    """Devanagari, Bengali, Tamil, Telugu, Kannada digits -> 0-9, so an answer check reads Indic numerals too."""
    out = []
    for ch in text:
        for zero in (0x0966, 0x09E6, 0x0BE6, 0x0C66, 0x0CE6):
            if zero <= ord(ch) <= zero + 9:
                ch = str(ord(ch) - zero)
                break
        out.append(ch)
    return "".join(out)


def has_number(text: str | None, answer: str) -> bool:
    if not text:
        return False
    nums = re.findall(r"\d+(?:\.\d+)?", to_ascii_digits(text).replace(",", ""))
    return any(n == answer or ("." in n and n.rstrip("0").rstrip(".") == answer) for n in nums)   # 36.0 == 36


# ------------------------------------------------------------------------------ server

def launch(args, out: Path):
    vllm_bin = Path(sys.executable).with_name("vllm")
    if vllm_bin.exists():
        cmd = [str(vllm_bin), "serve", args.model]
    else:
        cmd = [sys.executable, "-m", "vllm.entrypoints.openai.api_server", "--model", args.model]
    cmd += ["--served-model-name", args.served_name, "--host", "127.0.0.1", "--port", str(args.port),
            "--seed", str(args.seed), "--chat-template", str(args.chat_template),
            "--reasoning-parser-plugin", str(args.parsers), "--reasoning-parser", "g10",
            "--enable-auto-tool-choice", "--tool-parser-plugin", str(args.parsers), "--tool-call-parser", "g10"]
    cmd += args.vllm_arg
    log = open(out / "vllm_server.log", "w")
    print("launch:", " ".join(cmd), flush=True)
    t0 = time.time()
    env = dict(os.environ, HF_HUB_OFFLINE=os.environ.get("HF_HUB_OFFLINE", "1"))   # job rule: no network
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
    base = f"http://127.0.0.1:{args.port}"
    while time.time() - t0 < args.startup_timeout:
        if proc.poll() is not None:
            log.close()
            tail = (out / "vllm_server.log").read_text(errors="replace")[-4000:]
            raise SystemExit(f"vLLM exited with code {proc.returncode} before it was ready. Log tail:\n{tail}")
        try:
            if urllib.request.urlopen(base + "/health", timeout=5).status == 200:
                return proc, base, time.time() - t0, cmd
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(5)
    proc.terminate()
    raise SystemExit(f"vLLM not ready after {args.startup_timeout} s; see {out / 'vllm_server.log'}")


# ------------------------------------------------------------------------------ requests

def build_body(row, tools_db, args, served_name, stream=False):
    msgs = [dict(m) for m in row["messages"]]
    system = []
    tools = [tools_db[n] for n in row["tools"] or []]
    if args.format_hint == "on":
        system.append(FORMAT_HINT + (FORMAT_HINT_TOOLS if tools else ""))
    if tools and args.tools_in_system_on:
        system.append("You can call these tools:\n" +
                      "\n".join(json.dumps(t["function"], ensure_ascii=False) for t in tools))
    if system:
        msgs.insert(0, {"role": "system", "content": "\n\n".join(system)})
    body = {"model": served_name, "messages": msgs, "max_tokens": args.max_tokens, "temperature": args.temperature,
            "seed": args.seed, "skip_special_tokens": False}
    if row.get("effort"):
        body["chat_template_kwargs"] = {"effort": row["effort"]}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if stream:
        body["stream"] = True
        body["stream_options"] = {"include_usage": True}
    return body


def send(base, body):
    t0 = time.time()
    try:
        status, resp = http_json(base + "/v1/chat/completions", body)
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": e.read().decode(errors="replace")[:500], "latency_s": time.time() - t0}
    except Exception as e:                                            # noqa: BLE001
        return {"status": None, "error": repr(e)[:500], "latency_s": time.time() - t0}
    choice = resp["choices"][0]
    msg = choice["message"]
    calls = [{"name": (c.get("function") or {}).get("name"), "arguments": (c.get("function") or {}).get("arguments"),
              "id": c.get("id")} for c in msg.get("tool_calls") or []]
    usage = resp.get("usage") or {}
    return {"status": status, "latency_s": time.time() - t0, "finish_reason": choice.get("finish_reason"),
            "reasoning": msg.get("reasoning") or msg.get("reasoning_content"), "content": msg.get("content"),
            "tool_calls": calls, "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens")}


def send_stream(base, body):
    t0, first = time.time(), None
    reasoning, content, calls, finish = "", "", {}, None
    try:
        for chunk in http_stream(base + "/v1/chat/completions", body):
            for ch in chunk.get("choices") or []:
                d = ch.get("delta") or {}
                if first is None and (d.get("content") or d.get("reasoning") or d.get("tool_calls")):
                    first = time.time() - t0
                reasoning += d.get("reasoning") or d.get("reasoning_content") or ""
                content += d.get("content") or ""
                for tc in d.get("tool_calls") or []:
                    c = calls.setdefault(tc.get("index", 0), {"name": None, "arguments": "", "id": None})
                    fn = tc.get("function") or {}
                    c["name"] = c["name"] or fn.get("name")
                    c["arguments"] += fn.get("arguments") or ""
                    c["id"] = c["id"] or tc.get("id")
                finish = ch.get("finish_reason") or finish
    except Exception as e:                                            # noqa: BLE001
        return {"error": repr(e)[:500]}
    return {"reasoning": reasoning or None, "content": content or None,
            "tool_calls": [calls[i] for i in sorted(calls)], "finish_reason": finish,
            "ttft_s": first, "latency_s": time.time() - t0}


# ------------------------------------------------------------------------------ checks

def check_row(row, r, tools_db):
    exp = row["expect"]
    res = {"http_ok": r.get("status") == 200}
    if not res["http_ok"]:
        return res
    texts = [r["reasoning"], r["content"]] + [c["arguments"] for c in r["tool_calls"]]
    res["marker_leaks"] = sorted({m for t in texts for m in leaks(t, MARKERS)})
    res["native_markers"] = sorted({m for t in texts for m in leaks(t, NATIVE_MARKERS)})
    res["fields_ok"] = not res["marker_leaks"]
    res["has_reasoning"] = bool(r["reasoning"] and r["reasoning"].strip())
    res["has_content"] = bool(r["content"] and r["content"].strip())
    res["n_tool_calls"] = len(r["tool_calls"])
    offered = set(row["tools"] or [])
    args_ok = []
    for c in r["tool_calls"]:
        try:
            a = json.loads(c["arguments"] or "")
            ok = isinstance(a, dict) and c["name"] in offered and all(
                k in a for k in tools_db[c["name"]]["function"]["parameters"].get("required", []))
        except (ValueError, KeyError):
            ok = False
        args_ok.append(ok)
    res["tool_args_ok"] = all(args_ok) if args_ok else None
    cat = row["category"]
    if cat == "chat":
        res["behaviour_ok"] = res["has_content"]
    elif cat == "reason":
        res["behaviour_ok"] = res["has_reasoning"] and res["has_content"]
        res["answer_ok"] = has_number(r["content"], exp["answer"])
    elif cat == "tool":
        res["behaviour_ok"] = (res["n_tool_calls"] >= 1 and r["tool_calls"][0]["name"] == exp["tool"]
                               and bool(res["tool_args_ok"]))
    else:                                                             # tool_result, no_tool
        res["behaviour_ok"] = res["n_tool_calls"] == 0 and res["has_content"]
        if exp.get("answer_substring"):
            res["answer_ok"] = exp["answer_substring"] in to_ascii_digits(r["content"] or "")
    return res


def same_fields(a, b) -> bool:
    def norm(r):
        calls = []
        for c in r.get("tool_calls") or []:
            try:
                args = json.loads(c["arguments"] or "null")
            except ValueError:
                args = c["arguments"]
            calls.append((c["name"], args))
        return ((r.get("reasoning") or "").strip(), (r.get("content") or "").strip(), calls)
    return norm(a) == norm(b)


def offline_fields(raw: str, row) -> dict:
    """The fields the g10 parsers give for this raw output, applied as vLLM does: reasoning first, then tool calls
    only when the request offers tools (tool_choice "auto"). Without tools the rest stays content."""
    reasoning, content = split_reasoning(raw, final=True)
    calls = []
    if row["tools"]:
        found, visible = parse_tool_calls(content or "")
        if found:
            calls, content = found, visible
    if content is not None and not content.strip():
        content = None
    return {"reasoning": reasoning, "content": content,
            "tool_calls": [{"name": c["name"], "arguments": c["arguments"]} for c in calls]}


def violation_reasons(raw: str, row) -> list[str]:
    """How a raw output breaks the G10 assistant layout (think block first, then tool calls, then the answer)."""
    why, s = [], raw.lstrip()
    if THINK in raw and not s.startswith(THINK):
        why.append("think block after the answer")
    elif raw.count(THINK) > 1:
        why.append("second think block")
    if raw.count(THINK_END) > raw.count(THINK):
        why.append("stray <|/think|>")
    if CALL in raw:
        why.append("tool call although no tools were offered" if not row["tools"]
                   else "tool call the layout does not allow (malformed, or after the answer)")
    return why or ["marker outside the G10 layout"]


def replay(base, body) -> dict:
    """The raw text for this request: /tokenize renders the prompt (same server, template, tools, effort) and
    /v1/completions regenerates it at the same settings, with no parser in between."""
    tok_req = {"model": body["model"], "messages": body["messages"], "add_generation_prompt": True}
    for k in ("tools", "chat_template_kwargs"):
        if k in body:
            tok_req[k] = body[k]
    try:
        _, tok = http_json(base + "/tokenize", tok_req)
        _, comp = http_json(base + "/v1/completions", {
            "model": body["model"], "prompt": tok["tokens"], "max_tokens": body["max_tokens"],
            "temperature": body["temperature"], "seed": body["seed"], "skip_special_tokens": False})
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"}
    except Exception as e:                                            # noqa: BLE001
        return {"error": repr(e)[:300]}
    return {"raw": comp["choices"][0]["text"], "finish_reason": comp["choices"][0].get("finish_reason")}


def stream_leaks(st) -> list[str]:
    if "error" in st:
        return []
    texts = [st.get("reasoning"), st.get("content")] + [c["arguments"] for c in st.get("tool_calls") or []]
    return sorted({m for t in texts for m in leaks(t, MARKERS)})


# ------------------------------------------------------------------------------ report

def pct(n, d):
    return f"{n}/{d}" if d else "-"


def quantile(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def write_md(path: Path, s: dict):
    L = []
    L.append(f"# Serving check: {s['label']}\n")
    L.append(f"{s['finished']} · vLLM {s['versions'].get('vllm')} · GPU {s['gpu']} · model `{s['model']}`\n")
    g = s["gate"]
    L.append("## Result\n")
    L.append(f"- **Requests:** {g['http_ok']} returned HTTP 200.")
    L.append(f"- **Fields (the serving check): {'PASS' if g['pass'] else 'FAIL'}.** {g['fields_ok']} answers have no "
             f"chat marker in `content`, `reasoning` or tool arguments. Every other answer was replayed (raw text "
             f"regenerated, parsed offline by g10_parsers): model broke the G10 layout and the parser placed it as "
             f"specified: {g['model_breaks']}; parser fault or not explained: {g['parser_faults']}.")
    L.append(f"- **Reasoning in `message.reasoning`:** {g['reasoning']} reason prompts.")
    L.append(f"- **Tool calls in `message.tool_calls`:** {g['tool_calls']} tool prompts call the expected tool "
             f"with valid JSON arguments.")
    L.append(f"- **No tool call when none is needed:** {g['no_tool']} (tool_result + no_tool prompts).")
    L.append(f"- **Streaming matches non-streaming:** {g['stream_agree']} streamed prompts give the same "
             f"reasoning, content and tool calls.")
    L.append(f"- **Model fell back to its own markers** (`<think>`, `<tool_call>`): {g['native']} answers. That is "
             f"model behaviour, not a parser fault.\n")
    L.append("## Per category\n")
    L.append("| Category | n | HTTP 200 | fields ok | expected behaviour | answer right | reasoning present | "
             "tool calls | p50 latency s | p95 latency s | completion tokens (mean) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for c, v in s["per_category"].items():
        L.append(f"| {c} | {v['n']} | {v['http_ok']} | {v['fields_ok']} | {v['behaviour_ok']} | {v['answer_ok']} | "
                 f"{v['has_reasoning']} | {v['tool_calls']} | {v['p50_s']} | {v['p95_s']} | {v['mean_completion_tokens']} |")
    L.append("")
    t = s["timing"]
    L.append("## Time and cost\n")
    L.append(f"- Server start to ready: {t['startup_s']} s. 100 prompts at concurrency {s['settings']['concurrency']}: "
             f"{t['prompts_wall_s']} s. Streamed copies: {t['stream_wall_s']} s. Replays: {t['replay_wall_s']} s. Total: {t['total_wall_s']} s.")
    L.append(f"- Output: {t['completion_tokens']} completion tokens, {t['tokens_per_s']} tokens/s (all requests "
             f"together, non-streamed pass).")
    L.append(f"- GPU time: {t['gpu_hours']} GPU-hours ({s['settings']['n_gpus']} GPU); cost at "
             f"${s['settings']['usd_per_gpu_hour']}/GPU-hour: ${t['cost_usd']}.\n")
    if s["failures"]:
        L.append("## Prompts not as expected\n")
        L.append("| id | lang | what |")
        L.append("|---|---|---|")
        for f in s["failures"]:
            L.append(f"| {f['id']} | {f['lang']} | {f['what']} |")
        L.append("")
    L.append("## Setup\n")
    st = s["settings"]
    L.append(f"- Chat template `{st['chat_template']}` (sha256 `{st['chat_template_sha256'][:12]}`), parsers "
             f"`{st['parsers']}` (sha256 `{st['parsers_sha256'][:12]}`), prompts `{st['prompts']}` "
             f"(sha256 `{st['prompts_sha256'][:12]}`).")
    L.append(f"- temperature {st['temperature']}, seed {st['seed']}, max_tokens {st['max_tokens']}, "
             f"format hint {st['format_hint']}, tools in system message {st['tools_in_system']}, "
             f"`skip_special_tokens: false` on every request.")
    L.append(f"- Versions: {json.dumps(s['versions'])}.")
    if s.get("server_cmd"):
        L.append(f"- Server: `{' '.join(s['server_cmd'])}`")
    L.append(f"- Check: `{s['command']}`\n")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------ main

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--model", help="checkpoint folder (Hugging Face layout) or model id already in the local cache")
    p.add_argument("--served-name", default=None)
    p.add_argument("--label", default=None, help="name for the report title (default: the model folder name)")
    p.add_argument("--base-url", default=None, help="use a running server, for example http://127.0.0.1:8000")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--vllm-arg", action="append", default=[], help="extra `vllm serve` argument, repeatable: "
                   "--vllm-arg=--max-model-len=4096")
    p.add_argument("--chat-template", type=Path,
                   default=REPO / "teams" / "10-post-training" / "chat-format" / "chat_template.jinja")
    p.add_argument("--parsers", type=Path, default=HERE / "g10_parsers.py")
    p.add_argument("--prompts", type=Path, default=HERE / "prompts_v1.jsonl")
    p.add_argument("--tools", type=Path, default=HERE / "tools_v1.json")
    p.add_argument("--out", type=Path, default=Path("out"))
    p.add_argument("--max-tokens", type=int, default=1024)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--stream-check", type=int, default=20, help="prompts also sent streamed (spread over categories)")
    p.add_argument("--format-hint", choices=("on", "off"), default="on")
    p.add_argument("--tools-in-system", choices=("auto", "on", "off"), default="auto")
    p.add_argument("--limit", type=int, default=None, help="first N prompts only (smoke test)")
    p.add_argument("--startup-timeout", type=int, default=1800)
    p.add_argument("--n-gpus", type=int, default=1)
    p.add_argument("--usd-per-gpu-hour", type=float, default=0.0, help="0 for Kaggle / Colab free tiers")
    args = p.parse_args(argv)
    if not args.model and not args.base_url:
        p.error("--model or --base-url is required")

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in args.prompts.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit:
        rows = rows[: args.limit]
    tools_db = json.loads(args.tools.read_text(encoding="utf-8"))
    template_text = args.chat_template.read_text(encoding="utf-8")
    args.tools_in_system_on = (args.tools_in_system == "on" or
                               (args.tools_in_system == "auto" and "tools" not in template_text))
    args.served_name = args.served_name or (Path(args.model).name if args.model else "model")
    label = args.label or args.served_name

    t_start = time.time()
    proc, server_cmd, startup_s = None, None, 0.0
    if args.base_url:
        base = args.base_url.rstrip("/")
        _, models = http_json(base + "/v1/models", timeout=30)
        args.served_name = models["data"][0]["id"]
    else:
        proc, base, startup_s, server_cmd = launch(args, out)
    print(f"server ready in {startup_s:.0f} s at {base}", flush=True)

    try:
        t0 = time.time()
        with cf.ThreadPoolExecutor(args.concurrency) as ex:
            results = list(ex.map(lambda r: send(base, build_body(r, tools_db, args, args.served_name)), rows))
        prompts_wall = time.time() - t0

        by_cat = {c: [i for i, r in enumerate(rows) if r["category"] == c] for c in CATEGORIES}
        per = max(1, args.stream_check // max(1, sum(1 for v in by_cat.values() if v)))
        stream_idx = sorted(i for v in by_cat.values() for i in v[:per])[: args.stream_check]
        t0 = time.time()
        streamed = {i: send_stream(base, build_body(rows[i], tools_db, args, args.served_name, stream=True))
                    for i in stream_idx}                                # one at a time: closest to the greedy pass
        stream_wall = time.time() - t0

        # every answer with a marker in a field: regenerate the raw text and parse it offline (one at a time)
        flagged = [i for i, (row, r) in enumerate(zip(rows, results)) if r.get("status") == 200 and
                   (check_row(row, r, tools_db)["marker_leaks"] or (i in streamed and stream_leaks(streamed[i])))]
        t0 = time.time()
        replays = {i: replay(base, build_body(rows[i], tools_db, args, args.served_name)) for i in flagged}
        replay_wall = time.time() - t0
    finally:
        if proc is not None:
            proc.send_signal(signal.SIGINT)                    # vLLM's clean shutdown (SIGTERM logs a dead engine)
            try:
                proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                proc.kill()
    total_wall = time.time() - t_start

    # ---- per-row records
    records, failures = [], []
    for i, (row, r) in enumerate(zip(rows, results)):
        chk = check_row(row, r, tools_db)
        rec = {"id": row["id"], "category": row["category"], "lang": row["lang"], "effort": row.get("effort"),
               **{k: r.get(k) for k in ("status", "latency_s", "finish_reason", "prompt_tokens", "completion_tokens",
                                        "error")}, **chk,
               "reasoning": (r.get("reasoning") or "")[:TEXT_CAP] or None,
               "content": (r.get("content") or "")[:TEXT_CAP] or None,
               "tool_calls": r.get("tool_calls")}
        if i in streamed:
            st = streamed[i]
            rec["stream_agree"] = "error" not in st and r.get("status") == 200 and same_fields(r, st)
            rec["stream_ttft_s"] = st.get("ttft_s")
            rec["stream_marker_leaks"] = stream_leaks(st) if "error" not in st else None
            rec["stream"] = {"reasoning": (st.get("reasoning") or "")[:TEXT_CAP] or None,
                             "content": (st.get("content") or "")[:TEXT_CAP] or None,
                             "tool_calls": st.get("tool_calls"), "error": st.get("error")}
        if i in replays:
            rp = replays[i]
            if "error" in rp:
                rec["leak_cause"], rec["leak_why"] = "unexplained", [f"replay failed: {rp['error']}"]
            elif not same_fields(offline_fields(rp["raw"], row), r):
                rec["leak_cause"] = "unexplained"
                rec["leak_why"] = ["the replayed raw text parses to other fields (a parser fault, or the model "
                                   "answered differently this time)"]
            elif not chk["marker_leaks"]:
                rec["leak_cause"], rec["leak_why"] = "parser", ["marker only in the streamed fields"]
            else:
                rec["leak_cause"], rec["leak_why"] = "model", violation_reasons(rp["raw"], row)
            rec["replay_raw"] = (rp.get("raw") or "")[:TEXT_CAP] or None
        records.append(rec)
        what = []
        if not chk["http_ok"]:
            what.append(f"HTTP {r.get('status')}: {r.get('error', '')[:120]}")
        else:
            if chk["marker_leaks"] or rec.get("stream_marker_leaks"):
                cause = {"model": "model broke the G10 layout", "parser": "PARSER FAULT",
                         "unexplained": "NOT EXPLAINED"}.get(rec.get("leak_cause"), "?")
                markers = sorted(set(chk["marker_leaks"]) | set(rec.get("stream_marker_leaks") or []))
                what.append(f"marker in a field ({cause}: {', '.join(rec.get('leak_why') or [])}): "
                            + " ".join(f"`{m}`" for m in markers))
            if not chk["behaviour_ok"]:
                cat = row["category"]
                if cat == "reason" and not chk["has_reasoning"]:
                    what.append("no reasoning")
                if cat == "tool":
                    got = [c["name"] for c in r["tool_calls"]]
                    what.append(f"expected {row['expect']['tool']}, got {got or 'no call'}"
                                + ("" if chk["tool_args_ok"] in (True, None) else ", bad arguments"))
                if cat in ("tool_result", "no_tool") and chk["n_tool_calls"]:
                    what.append(f"called {[c['name'] for c in r['tool_calls']]}")
                if not chk["has_content"] and cat != "tool":
                    what.append("empty content" + (f" (finish {r.get('finish_reason')})" if r.get("finish_reason")
                                                   else ""))
            if chk["native_markers"]:
                what.append("own markers " + " ".join(f"`{m}`" for m in chk["native_markers"]))
            if rec.get("stream_agree") is False:
                what.append("stream differs")
        if what:
            failures.append({"id": row["id"], "lang": row["lang"], "what": "; ".join(what)})

    with open(out / "serve_check.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---- summary
    ok = [x for x in records if x["http_ok"]]
    per_category = {}
    for c in CATEGORIES:
        xs = [x for x in records if x["category"] == c]
        if not xs:
            continue
        good = [x for x in xs if x["http_ok"]]
        lat = [x["latency_s"] for x in good]
        toks = [x["completion_tokens"] for x in good if x["completion_tokens"] is not None]
        ans = [x for x in good if "answer_ok" in x]
        per_category[c] = {
            "n": len(xs), "http_ok": pct(len(good), len(xs)),
            "fields_ok": pct(sum(x["fields_ok"] for x in good), len(good)),
            "behaviour_ok": pct(sum(x["behaviour_ok"] for x in good), len(good)),
            "answer_ok": pct(sum(x["answer_ok"] for x in ans), len(ans)),
            "has_reasoning": pct(sum(x["has_reasoning"] for x in good), len(good)),
            "tool_calls": pct(sum(x["n_tool_calls"] > 0 for x in good), len(good)),
            "p50_s": round(quantile(lat, 0.5), 2) if lat else None,
            "p95_s": round(quantile(lat, 0.95), 2) if lat else None,
            "mean_completion_tokens": round(statistics.mean(toks)) if toks else None,
        }
    n_tok = sum(x["completion_tokens"] or 0 for x in ok)
    streamed_recs = [x for x in records if "stream_agree" in x]
    fields_ok = sum(x["fields_ok"] for x in ok)
    leaked = [x for x in ok if "leak_cause" in x]
    model_breaks = sum(x["leak_cause"] == "model" for x in leaked)
    parser_faults = len(leaked) - model_breaks
    all_pass = len(ok) == len(records) and parser_faults == 0

    def cat_count(c, key):
        xs = [x for x in ok if x["category"] == c]
        return sum(bool(x[key]) for x in xs), len(xs)

    r_n, r_d = cat_count("reason", "has_reasoning")
    t_n, t_d = cat_count("tool", "behaviour_ok")
    nt = [x for x in ok if x["category"] in ("tool_result", "no_tool")]
    gpu_hours = total_wall / 3600 * args.n_gpus
    summary = {
        "label": label, "model": args.model or args.base_url,
        "finished": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "gpu": gpu_info(), "versions": versions(), "platform": platform.platform(),
        "gate": {"http_ok": pct(len(ok), len(records)), "fields_ok": pct(fields_ok, len(ok)), "pass": all_pass,
                 "model_breaks": model_breaks, "parser_faults": parser_faults,
                 "reasoning": pct(r_n, r_d), "tool_calls": pct(t_n, t_d),
                 "no_tool": pct(sum(x["n_tool_calls"] == 0 for x in nt), len(nt)),
                 "stream_agree": pct(sum(bool(x["stream_agree"]) for x in streamed_recs), len(streamed_recs)),
                 "native": pct(sum(bool(x["native_markers"]) for x in ok), len(ok))},
        "per_category": per_category,
        "timing": {"startup_s": round(startup_s), "prompts_wall_s": round(prompts_wall, 1),
                   "stream_wall_s": round(stream_wall, 1), "replay_wall_s": round(replay_wall, 1),
                   "total_wall_s": round(total_wall),
                   "completion_tokens": n_tok, "tokens_per_s": round(n_tok / prompts_wall, 1) if prompts_wall else None,
                   "gpu_hours": round(gpu_hours, 3), "cost_usd": round(gpu_hours * args.usd_per_gpu_hour, 2)},
        "settings": {"chat_template": rel(args.chat_template), "chat_template_sha256": sha256(args.chat_template),
                     "parsers": rel(args.parsers), "parsers_sha256": sha256(args.parsers),
                     "prompts": rel(args.prompts), "prompts_sha256": sha256(args.prompts),
                     "temperature": args.temperature, "seed": args.seed, "max_tokens": args.max_tokens,
                     "concurrency": args.concurrency, "format_hint": args.format_hint,
                     "tools_in_system": args.tools_in_system_on, "n_gpus": args.n_gpus,
                     "usd_per_gpu_hour": args.usd_per_gpu_hour},
        "server_cmd": server_cmd, "command": " ".join([Path(sys.argv[0]).name] + (argv or sys.argv[1:])),
        "failures": failures,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_md(out / "serve_check.md", summary)
    print(json.dumps(summary["gate"], ensure_ascii=False))
    print(f"wrote {out / 'serve_check.md'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
