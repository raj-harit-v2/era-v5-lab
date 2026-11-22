"""G10 effort evaluation (Package T2): fixed prompts crossed with the four effort labels 1k, 4k, 16k, 64k.

The requested effort label and the enforced generation cap are separate fields in every record. The label is the
plain-text line `Reasoning effort: {label}` (chat-format v0); the cap is the max_new_tokens the harness enforces.
A text instruction is not a budget mechanism, so the suite measures three things apart: whether the output follows
the format, whether it stays inside the imposed cap, and whether it is correct.

Stages
    A   10-prompt canary (the slots listed in the manifest), every label, common cap 1024. Default.
    B   every resolved prompt, every label, common cap 1024. Isolates the effect of the effort text at a fixed cap.
    C   preregistered subset, per-label ceilings from the real context. Off unless `--stage C` is given.
Neither B's common cap nor C's subset shows full four-tier compliance; the summary says which cells ran.

Prompts
    `effort_manifest.json` points at rows of pinned upstream files (dataset, revision, file sha256, row index, field)
    and holds the sha256 of every prompt text, never the text. `--source-dir name=DIR` gives local copies of the
    pinned files; each text is re-read and its hash checked before anything runs. Slots without an approved
    human-written source are recorded as unavailable with the reason and are never filled with generated text.
    The prompt is the raw task text. An instruction wrapper is optional (`--instruction kind=FILE`, written by a
    team member, as in rl-data/survey.py) and its sha256 goes into every record.

Checkers
    math -> rl-data/math_check.score, stdio code -> rl-data/stdio_check.score (Docker), loaded from `--checker-dir`
    (default ../rl-data). If a checker or execution is unavailable, functional success is None with the reason,
    never 0.

Outputs
    One JSONL record per (slot, label) plus summary.json. Every record carries `do_not_train: true` and
    `artifact: g10-effort-eval-output`. `guard` fails if a training file holds such a record, an eval task id, or
    an eval prompt. Eval outputs never enter a training artifact.

Usage (from teams/10-post-training)
    python eval/effort_suite.py verify --manifest eval/effort_manifest.json
    python eval/effort_suite.py plan --manifest eval/effort_manifest.json --stage B
    python eval/effort_suite.py run --manifest eval/effort_manifest.json --stage A --backend hf --model PATH \
        --source-dir code_contests=DIR --source-dir hendrycks_math=DIR --out OUT
    python eval/effort_suite.py run ... --backend team5 --adapter-config CFG.yaml        # G10 template, G5 model
    python eval/effort_suite.py guard --manifest eval/effort_manifest.json --training FILE.jsonl [...]
    python eval/effort_suite.py compare A/summary.json B/summary.json
    python eval/effort_suite.py build-manifest ...   # how effort_manifest.json was made (see --help)
"""

from __future__ import annotations

import argparse
import copy
import ast
import hashlib
import importlib.util
import json
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent

SCHEMA = "g10-effort-manifest/1"
OUTPUT_ARTIFACT = "g10-effort-eval-output"
STAGE_CAP = 1024  # common cap for stages A and B (G10_TRAINING.md section 4)
STAGES = ("A", "B", "C")
COMPOSITION = {"code": 30, "math": 25, "tool_agentic": 20, "indic": 15, "general": 10}  # declared dev sample


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render = _load("g10_render_effort", TEAM / "chat-format" / "render.py")
T = render.T
LABELS = tuple(sorted(render.EFFORT_BUDGETS, key=render.EFFORT_BUDGETS.get))  # 1k, 4k, 16k, 64k
# The converter's trace contract (sft/convert.py TRACE): think spans, tool calls and tool results with markers.
TRACE = re.compile(
    "|".join(
        f"{re.escape(T[a])}.*?{re.escape(T[b])}"
        for a, b in (("think", "think_end"), ("tool_call", "tool_call_end"), ("tool_result", "tool_result_end"))
    ),
    re.S,
)


class ManifestError(ValueError):
    """The manifest is malformed or its hash does not verify."""


class SourceError(ValueError):
    """A pinned source file or prompt text does not match the manifest."""


# --- manifest ---------------------------------------------------------------------------------------------

def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def manifest_digest(manifest: dict) -> str:
    """sha256 of the canonical JSON of the manifest without its own `manifest_sha256` field."""
    return hashlib.sha256(canonical({k: v for k, v in manifest.items() if k != "manifest_sha256"})).hexdigest()


def seal(manifest: dict) -> dict:
    out = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    out["manifest_sha256"] = manifest_digest(out)
    return out


RESOLVED_KEYS = ("slot", "category", "status", "task_id", "group", "dataset", "revision", "split", "file",
                 "file_sha256", "row_index", "field", "text_sha256", "licence", "licence_decision", "generator",
                 "checker")


def validate(manifest: dict) -> dict:
    """Check structure and hash. Returns the manifest; raises ManifestError."""
    if manifest.get("schema") != SCHEMA:
        raise ManifestError(f"schema must be {SCHEMA}")
    if manifest.get("manifest_sha256") != manifest_digest(manifest):
        raise ManifestError("manifest_sha256 does not verify: the manifest changed after it was sealed")
    if tuple(manifest.get("labels", ())) != LABELS:
        raise ManifestError(f"labels must be {list(LABELS)} (render.EFFORT_BUDGETS order)")
    slots = manifest.get("slots")
    if not isinstance(slots, list) or not slots:
        raise ManifestError("slots must be a non-empty list")
    ids = [s.get("slot") for s in slots]
    if len(set(ids)) != len(ids):
        raise ManifestError("duplicate slot ids")
    counts: dict[str, int] = {}
    for s in slots:
        counts[s.get("category")] = counts.get(s.get("category"), 0) + 1
        if s.get("status") == "resolved":
            missing = [k for k in RESOLVED_KEYS if k not in s]
            if missing:
                raise ManifestError(f"slot {s.get('slot')}: missing {missing}")
            if not re.fullmatch(r"[0-9a-f]{64}", str(s["text_sha256"])):
                raise ManifestError(f"slot {s['slot']}: text_sha256 is not a sha256")
        elif s.get("status") == "unavailable":
            if not s.get("reason"):
                raise ManifestError(f"slot {s.get('slot')}: unavailable slots need a reason")
        else:
            raise ManifestError(f"slot {s.get('slot')}: status must be resolved or unavailable")
    if counts != manifest.get("composition"):
        raise ManifestError(f"slot counts {counts} differ from composition {manifest.get('composition')}")
    resolved = {s["slot"] for s in slots if s["status"] == "resolved"}
    tasks = [s["task_id"] for s in slots if s["status"] == "resolved"]
    if len(set(tasks)) != len(tasks):
        raise ManifestError("a task appears in two slots")
    for stage in ("A", "C"):
        chosen = manifest.get("stages", {}).get(stage, {}).get("slots", [])
        if not set(chosen) <= resolved:
            raise ManifestError(f"stage {stage} lists slots that are not resolved")
    if len(manifest["stages"]["A"]["slots"]) != 10:
        raise ManifestError("stage A must list exactly 10 slots")
    excl = manifest.get("training_exclusion", {})
    if sorted(excl.get("task_ids", [])) != sorted(tasks):
        raise ManifestError("training_exclusion.task_ids must list every resolved task")
    return manifest


def load_manifest(path: Path | str) -> dict:
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))


# --- the matrix -------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Cell:
    slot: str
    label: str
    seed: int


def prompt_seed(base_seed: int, slot: str) -> int:
    """The same seed for a prompt under every label and checkpoint."""
    return int(hashlib.sha256(f"{base_seed}:{slot}".encode()).hexdigest()[:8], 16)


def stage_slots(manifest: dict, stage: str) -> list[str]:
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    order = [s["slot"] for s in manifest["slots"] if s["status"] == "resolved"]
    if stage == "B":
        return order
    chosen = set(manifest["stages"][stage]["slots"])
    return [s for s in order if s in chosen]


def iter_matrix(manifest: dict, stage: str, base_seed: int | None = None) -> list[Cell]:
    """Slot-major, labels in budget order. Unavailable slots are never in the matrix."""
    seed = manifest["base_seed"] if base_seed is None else base_seed
    return [Cell(slot, label, prompt_seed(seed, slot)) for slot in stage_slots(manifest, stage) for label in LABELS]


# --- prompt resolution ------------------------------------------------------------------------------------

@dataclass
class Prompt:
    slot: str
    category: str
    task_id: str
    text: str            # raw task text, hash-checked
    checker: str         # "math" | "stdio" | "none"
    task: dict = field(default_factory=dict)  # what the checker needs (answer or tests)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_row(path: Path, row_index: int, columns: list[str]) -> dict:
    import pyarrow.parquet as pq  # noqa: PLC0415

    pf = pq.ParquetFile(path)
    start = 0
    for g in range(pf.num_row_groups):
        n = pf.metadata.row_group(g).num_rows
        if row_index < start + n:
            table = pf.read_row_group(g, columns=columns)
            return table.slice(row_index - start, 1).to_pylist()[0]
        start += n
    raise SourceError(f"{path}: row {row_index} out of range ({start} rows)")


def code_tests(row: dict, max_tests: int) -> list[dict]:
    """Same order and cap as rl-data/build.py: public, private, generated tests."""
    tests: list[dict] = []
    for key in ("public_tests", "private_tests", "generated_tests"):
        t = row.get(key) or {}
        tests += [{"input": i, "output": o} for i, o in zip(t.get("input", []) or [], t.get("output", []) or [])]
    return tests[:max_tests]


def resolve_prompts(manifest: dict, source_dirs: dict[str, Path], verify_files: bool = True,
                    last_boxed: Callable[[str], str | None] | None = None,
                    slots: Iterable[str] | None = None) -> dict[str, Prompt]:
    """Read every needed slot from its pinned file and check file and text hashes."""
    wanted = set(slots) if slots is not None else None
    sources = manifest["sources"]
    checked: dict[Path, str] = {}
    out: dict[str, Prompt] = {}
    for s in manifest["slots"]:
        if s["status"] != "resolved" or (wanted is not None and s["slot"] not in wanted):
            continue
        key = s["source"]
        if key not in source_dirs:
            raise SourceError(f"slot {s['slot']}: no --source-dir for {key} ({sources[key]['dataset']}"
                              f"@{sources[key]['revision']})")
        path = Path(source_dirs[key]) / s["file"]
        if not path.is_file():
            raise SourceError(f"{path}: missing")
        if verify_files:
            if path not in checked:
                checked[path] = sha256_file(path)
            if checked[path] != s["file_sha256"]:
                raise SourceError(f"{path}: sha256 {checked[path]} != pinned {s['file_sha256']}")
        if s["checker"] == "api_call":
            out[s["slot"]] = _resolve_api_call(s, Path(source_dirs[key]), path, verify_files)
            continue
        cols = [s["field"]] + list(s.get("checker_fields", []))
        row = _read_row(path, s["row_index"], cols)
        text = row[s["field"]]
        if not isinstance(text, str) or sha256_text(text) != s["text_sha256"]:
            raise SourceError(f"slot {s['slot']}: prompt text hash does not match the manifest")
        task: dict = {"id": s["task_id"]}
        if s["checker"] == "stdio":
            task["tests"] = code_tests(row, s["max_tests"])
            task["time_limit_s"] = s["time_limit_s"]
            if sha256_text(json.dumps(task["tests"], ensure_ascii=False, sort_keys=True)) != s["tests_sha256"]:
                raise SourceError(f"slot {s['slot']}: tests hash does not match the manifest")
        elif s["checker"] == "answer_key":
            if sha256_text(row["answerKey"]) != s["answer_sha256"]:
                raise SourceError(f"slot {s['slot']}: answer key hash does not match the manifest")
            task["answer"] = row["answerKey"]
        elif s["checker"] == "math" and last_boxed is not None:
            answer = last_boxed(row["solution"])
            if answer is None or sha256_text(answer) != s["answer_sha256"]:
                raise SourceError(f"slot {s['slot']}: reference answer hash does not match the manifest")
            task["answer"] = answer
        out[s["slot"]] = Prompt(s["slot"], s["category"], s["task_id"], text, s["checker"], task)
    return out


# --- v2 slots: API-Bank calls and closed-form questions (proposed manifest) ------------------------------

# Fixed harness instructions for the two new kinds. They live in code, not in the manifest, and are not part of any
# hashed prompt text. A team-written --instruction file for the same kind replaces them.
DEFAULT_INSTRUCTIONS = {
    "answer_key": "Answer the multiple-choice question below. Reply with the letter of the correct option and "
                  "nothing else.\n\n{problem}",
    "api_call": "Based on the API descriptions and the conversation, write the one API call the AI should make next, "
                "in the format [ApiName(key1='value1', key2='value2')]. Output only that call.\n\n{problem}",
}


def apibank_docs(api_dir: Path) -> dict[str, tuple[str, str]]:
    """{ApiName: (file relative to the api-bank folder, description JSON)} read with ast, never executed.

    The JSON has the same keys and order as the set's tool_manager.get_api_description: name, description,
    input_parameters, output_parameters.
    """
    docs: dict[str, tuple[str, str]] = {}
    for f in sorted(Path(api_dir).glob("*.py")):
        for node in ast.parse(f.read_text(encoding="utf-8")).body:
            if not isinstance(node, ast.ClassDef):
                continue
            attrs = {}
            for st in node.body:
                if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) \
                        and st.targets[0].id in ("description", "input_parameters", "output_parameters"):
                    attrs[st.targets[0].id] = ast.literal_eval(st.value)
            if len(attrs) == 3:
                info = {"name": node.name, **{k: attrs[k] for k in ("description", "input_parameters",
                                                                       "output_parameters")}}
                docs[node.name] = (f"apis/{f.name}", json.dumps(info))
    return docs


def apibank_history_line(item: dict) -> str:
    """One dialogue turn in the set's own rendering (evaluator.py): User:/AI: text, API turns as call + Response."""
    if item["role"] in ("User", "AI"):
        return f"{item['role']}: {item['text']}"
    if item["role"] == "API":
        args = ", ".join(f"{k}='{v}'" for k, v in item["param_dict"].items())
        return f"[{item['api_name']}({args})] Response: {item['result']['output']}"
    raise SourceError(f"unknown dialogue role {item['role']!r}")


def apibank_prompt(rows: list[dict], call_index: int, docs: dict[str, tuple[str, str]]) -> tuple[str, list[str]]:
    """(prompt text, doc files used) for the API call at rows[call_index]: the set's API descriptions for every API
    in the dialogue (sorted by name) and the dialogue before that call. Only the set's own text."""
    names = sorted({r["api_name"] for r in rows if r["role"] == "API"})
    body = "\n".join(docs[n][1] for n in names)
    history = "\n".join(apibank_history_line(r) for r in rows[:call_index])
    return f"API descriptions:\n{body}\n\n{history}", sorted({docs[n][0] for n in names})


def _resolve_api_call(s: dict, base: Path, path: Path, verify_files: bool) -> "Prompt":
    docs_files = s["doc_files"]
    if verify_files:
        if sha256_file(path) != s["file_sha256"]:
            raise SourceError(f"{path}: sha256 differs from the pin")
        for rel, want in docs_files.items():
            if sha256_file(base / rel) != want:
                raise SourceError(f"{base / rel}: sha256 differs from the pin")
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    docs = apibank_docs(base / "apis")
    text, used = apibank_prompt(rows, s["row_index"], docs)
    if sorted(docs_files) != used or sha256_text(text) != s["text_sha256"]:
        raise SourceError(f"slot {s['slot']}: prompt text hash does not match the manifest")
    gold = rows[s["row_index"]]
    if gold["role"] != "API":
        raise SourceError(f"slot {s['slot']}: row {s['row_index']} is not an API call")
    task = {"id": s["task_id"], "api_name": gold["api_name"], "param_dict": gold["param_dict"]}
    if sha256_text(json.dumps(task["param_dict"], sort_keys=True, ensure_ascii=False) + "|" + task["api_name"]) \
            != s["gold_sha256"]:
        raise SourceError(f"slot {s['slot']}: gold call hash does not match the manifest")
    return Prompt(s["slot"], s["category"], s["task_id"], text, s["checker"], task)


def _final_text(completion: str) -> str:
    """The completion with closed think spans removed (the part after the reasoning trace)."""
    return re.sub(f"{re.escape(T['think'])}.*?{re.escape(T['think_end'])}", "", completion, flags=re.S)


_LETTER = r"[A-H]"
_ANSWER_LINE = re.compile(rf"(?i:answer)\s*(?i:is|:)\s*\(?({_LETTER})\)?(?![A-Za-z0-9])")
_BARE_LETTER = re.compile(rf"\(?({_LETTER})\)?[.)]?")


def extract_answer_key(completion: str) -> str | None:
    """The single option letter A-H the completion commits to, or None.

    Rules, first hit wins, on the text after any closed think span: (1) the content of the last \\boxed{...}
    (as the math checker takes a final answer from the last box), if that content is one capital letter, optionally
    in parentheses; (2) the last "answer is X" or "answer: X" phrase (case-insensitive on the phrase, capital
    letter X); (3) the whole reply is one capital letter with optional parentheses or a trailing full stop.
    Anything else, including a letter buried in prose, is None. The letter is not compared case-insensitively.
    """
    text = _final_text(completion).strip()
    if not text:
        return None
    boxes = list(re.finditer(r"\\(?:boxed|fbox)\s*\{\s*\(?(" + _LETTER + r")\)?\s*\}", text))
    if boxes:
        return boxes[-1].group(1)
    hits = list(_ANSWER_LINE.finditer(text))
    if hits:
        return hits[-1].group(1)
    m = _BARE_LETTER.fullmatch(text)
    return m.group(1) if m else None


def score_answer_key(task: dict, completion: str) -> dict:
    out = {"task_id": task["id"], "reward": 0}
    got = extract_answer_key(completion)
    if got is None:
        return {**out, "reason": "no answer found"}
    ok = got == task["answer"]
    return {**out, "reward": int(ok), "reason": "correct" if ok else "wrong answer"}


_API_CALL = re.compile(r"\[(\w+)\((.*?)\)\]", re.S)


def parse_one_api_call(completion: str) -> tuple[str, dict] | None:
    """Parse exactly one call in API-Bank's bracket format [Name(key='value', ...)] from the text after any closed
    think span. Keyword arguments only, literal values only. Returns (name, {key: value}) or None when there is no
    call, more than one call, a positional argument, a repeated key or a value that is not a literal."""
    text = _final_text(completion)
    calls = list(_API_CALL.finditer(text))
    if len(calls) != 1:
        return None
    name, args = calls[0].group(1), calls[0].group(2)
    try:
        node = ast.parse(f"f({args})", mode="eval").body
        if node.args or any(k.arg is None for k in node.keywords):
            return None
        keys = [k.arg for k in node.keywords]
        if len(set(keys)) != len(keys):
            return None
        return name, {k.arg: ast.literal_eval(k.value) for k in node.keywords}
    except (SyntaxError, ValueError):
        return None


def score_api_call(task: dict, completion: str) -> dict:
    """1 only if the API name and every parameter equal the gold call; a value matches when it equals the gold value
    or has the same string form. An extra or a missing parameter fails. Stricter than the set's own evaluator,
    which executes the call and uses a per-API tolerance."""
    out = {"task_id": task["id"], "reward": 0}
    parsed = parse_one_api_call(completion)
    if parsed is None:
        return {**out, "reason": "no single well-formed API call found"}
    name, params = parsed
    if name != task["api_name"]:
        return {**out, "reason": f"API name mismatch: {name}"}
    gold = task["param_dict"]
    if set(params) != set(gold):
        return {**out, "reason": f"parameter names differ: missing {sorted(set(gold) - set(params))}, "
                                 f"extra {sorted(set(params) - set(gold))}"}
    bad = [k for k in gold if params[k] != gold[k] and str(params[k]) != str(gold[k])]
    if bad:
        return {**out, "reason": f"parameter values differ: {sorted(bad)}"}
    return {**out, "reward": 1, "reason": "correct"}


def apply_instruction(prompt_text: str, instruction: str | None) -> str:
    """Raw task text unless a team-written instruction file (with {problem}) is supplied for this kind."""
    if instruction is None:
        return prompt_text
    if instruction.count("{problem}") != 1:
        raise ValueError("an instruction file must contain {problem} exactly once")
    return instruction.replace("{problem}", prompt_text)


# --- checkers ---------------------------------------------------------------------------------------------

def load_checkers(checker_dir: Path, execute_code: bool) -> tuple[dict, dict, Callable | None]:
    """({kind: score_fn or None}, {kind: reason when None}, last_boxed or None)."""
    fns: dict[str, Callable | None] = {"math": None, "stdio": None, "none": None,
                                       "answer_key": score_answer_key, "api_call": score_api_call}
    why = {"none": "no automatic checker for this category (needs the team's blinded human rubric)"}
    last_boxed = None
    mpath = checker_dir / "math_check.py"
    if mpath.is_file():
        try:
            mod = _load("g10_effort_math_check", mpath)
            import math_verify  # noqa: F401, PLC0415
            fns["math"], last_boxed = mod.score, mod.last_boxed
        except ImportError as exc:
            why["math"] = f"math checker not importable: {exc}"
    else:
        why["math"] = f"{mpath} not found (rl-data checkers, PR saitej123/era-v5-lab#54)"
    spath = checker_dir / "stdio_check.py"
    if not execute_code:
        why["stdio"] = "code execution disabled (--no-exec)"
    elif spath.is_file():
        fns["stdio"] = _load("g10_effort_stdio_check", spath).score
    else:
        why["stdio"] = f"{spath} not found (rl-data checkers, PR saitej123/era-v5-lab#54)"
    for k in fns:
        if fns[k] is not None:
            why.pop(k, None)
    return fns, why, last_boxed


# --- completion analysis ----------------------------------------------------------------------------------

def analyse(text: str, count: Callable[[str], int]) -> dict:
    """Format checks on one assistant completion (stop marker already removed).

    parse_status: ok | empty | malformed. trace_tokens is an int only when parse_status is ok; a malformed or
    unclosed trace reports the parser failure and the raw length, never a zero trace length.
    """
    raw_tokens = count(text) if text else 0
    out = {"parse_status": None, "parse_error": None, "trace_tokens": None, "raw_completion_tokens": raw_tokens,
           "think_unclosed": text.count(T["think"]) > text.count(T["think_end"]),
           "n_tool_calls": None, "tool_call_valid": None, "tool_result_tokens": 0}
    if not text:
        out.update(parse_status="empty", parse_error="empty completion")
        return out
    # render.parse needs the system effort turn first; the label does not affect how the assistant turn parses.
    probe = (f"{T['im_start']}system\n{render.EFFORT_PREFIX}{LABELS[0]}{T['im_end']}\n"
             f"{T['im_start']}assistant\n{text}{T['im_end']}\n{T['endoftext']}")
    try:
        message = render.parse(probe)["messages"][-1]
        if message.get("role") != "assistant":
            raise render.RenderError("completion did not parse as one assistant turn")
    except render.RenderError as exc:
        out.update(parse_status="malformed", parse_error=str(exc))
        if T["tool_call"] in text:
            out["tool_call_valid"] = False
        return out
    spans = [m.group() for m in TRACE.finditer(text)]
    calls = message.get("tool_calls") or []
    out.update(parse_status="ok", trace_tokens=sum(count(s) for s in spans), n_tool_calls=len(calls),
               tool_call_valid=(True if calls else None))
    out["tool_result_tokens"] = sum(count(s) for s in spans if s.startswith(T["tool_result"]))
    return out


# --- backends ---------------------------------------------------------------------------------------------

@dataclass
class Generation:
    completion_ids: list[int]
    text: str            # decoded up to, not including, the first stop id; interior markers kept
    stop_reason: str     # "stop:<id>" or "length"


class Backend:
    """prompt_ids(text, label) -> ids; generate(ids, cap, seed, temperature) -> Generation; count(text) -> int."""

    name = "abstract"
    template = "none"
    context: int = 0
    model_id = ""

    def prompt_ids(self, text: str, label: str) -> list[int]:
        raise NotImplementedError

    def generate(self, ids: list[int], cap: int, seed: int, temperature: float) -> Generation:
        raise NotImplementedError

    def count(self, text: str) -> int:
        raise NotImplementedError


class HFBackend(Backend):
    """Open checkpoint through transformers with its own chat template: an optimization diagnostic only.

    The effort line goes into a system message. The final G10 effort comparison uses TeamFiveBackend.
    """

    name = "hf"
    template = "native"

    def __init__(self, model_path: str, device: str = "auto", context: int | None = None):
        import torch  # noqa: PLC0415
        from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415

        sys.path.insert(0, str(TEAM / "rl-loop"))
        import runtime  # noqa: PLC0415  rl-loop/runtime.py

        self.device, _ = runtime.resolve_device(device)
        self.tok = AutoTokenizer.from_pretrained(model_path)
        if not getattr(self.tok, "chat_template", None):
            raise ValueError(f"{model_path}: tokenizer has no chat template")
        dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=dtype).to(self.device).eval()
        self.context = int(context or getattr(self.model.config, "max_position_embeddings", 0))
        if not self.context:
            raise ValueError("model context length unknown; pass --context")
        gen = self.model.generation_config
        eos = gen.eos_token_id if gen.eos_token_id is not None else self.tok.eos_token_id
        self.stop_ids = sorted({eos} if isinstance(eos, int) else set(eos))
        self.model_id = model_path
        self.torch = torch

    def prompt_ids(self, text: str, label: str) -> list[int]:
        msgs = [{"role": "system", "content": f"{render.EFFORT_PREFIX}{label}"}, {"role": "user", "content": text}]
        return list(self.tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True))

    def generate(self, ids: list[int], cap: int, seed: int, temperature: float) -> Generation:
        torch = self.torch
        torch.manual_seed(seed)
        x = torch.tensor([ids], device=self.device)
        with torch.no_grad():
            y = self.model.generate(x, attention_mask=torch.ones_like(x), max_new_tokens=cap,
                                    do_sample=temperature > 0, temperature=temperature if temperature > 0 else None,
                                    top_p=None, top_k=None, eos_token_id=self.stop_ids,
                                    pad_token_id=self.tok.pad_token_id or self.stop_ids[0])
        new = y[0, len(ids):].tolist()
        return _cut(new, self.stop_ids, lambda c: self.tok.decode(c, skip_special_tokens=False))

    def count(self, text: str) -> int:
        return len(self.tok.encode(text, add_special_tokens=False))


class TeamFiveBackend(Backend):
    """G5 model with the G10 template through rl-loop/team5_adapter.py. Only a READY real bundle is a result."""

    name = "team5"
    template = "g10"

    def __init__(self, adapter_config: str, device: str = "cpu", allow_fixture: bool = False):
        import torch  # noqa: PLC0415

        sys.path.insert(0, str(TEAM / "rl-loop"))
        import team5_adapter as ta  # noqa: PLC0415

        result = ta.build(adapter_config, device=device)
        if result.status == ta.WAITING:
            raise ta.WaitingForArtifact(result)
        if allow_fixture and result.status == ta.FIXTURE_READY:
            self.bundle, self.fixture = result.require_bundle(), True
        else:
            self.bundle, self.fixture = ta.require_learning_ready(result), False
        self.context = int(self.bundle.spec["block_size"])
        self.stop_ids = list(self.bundle.special["stop_ids"])
        self.model_id = f"g5:{result.manifest.get('g5', {}).get('commit', '?')}"
        self.device, self.torch = device, torch

    def prompt_ids(self, text: str, label: str) -> list[int]:
        return self.bundle.encode_generation_prefix([{"role": "user", "content": text}], effort=label)

    def generate(self, ids: list[int], cap: int, seed: int, temperature: float) -> Generation:
        torch = self.torch
        gen = torch.Generator(device=self.device).manual_seed(seed) if temperature > 0 else None
        seq, cmask, _ = self.bundle.sample(ids, 1, cap, temperature, gen)
        new = seq[0, len(ids):][cmask[0]].tolist()
        return _cut(new, self.stop_ids, lambda c: self.bundle.decode_completion(c, cut_at_stop=False))

    def count(self, text: str) -> int:
        return len(self.bundle.artifacts.encode(text))


def _cut(new: list[int], stop_ids: list[int], decode: Callable[[list[int]], str]) -> Generation:
    for j, t in enumerate(new):
        if t in stop_ids:
            return Generation(new[: j + 1], decode(new[:j]), f"stop:{t}")
    return Generation(new, decode(new), "length")


# --- running ----------------------------------------------------------------------------------------------

def plan_caps(backend: Backend, prompts: dict[str, Prompt], cells: list[Cell], stage: str,
              instructions: dict[str, str | None], reply_allowance: int) -> dict[tuple[str, str], dict]:
    """Preflight prompt + cap against the real context for every cell.

    A/B: one common cap per prompt across labels, STAGE_CAP or lower when the context forces it (recorded).
    C: ceiling = label budget + reply_allowance, bounded by the context; a ceiling below the label budget cannot
    test that label and the cell is unsupported.
    """
    out: dict[tuple[str, str], dict] = {}
    by_slot: dict[str, list[Cell]] = {}
    for c in cells:
        by_slot.setdefault(c.slot, []).append(c)
    for slot, cs in by_slot.items():
        p = prompts[slot]
        text = apply_instruction(p.text, instructions.get(p.checker))
        ids = {c.label: backend.prompt_ids(text, c.label) for c in cs}
        room = backend.context - max(len(v) for v in ids.values())
        for c in cs:
            plen = len(ids[c.label])
            if stage in ("A", "B"):
                cap = min(STAGE_CAP, room)
                if cap <= 0:
                    out[(slot, c.label)] = {"supported": False, "cap": 0, "prompt_tokens": plen,
                                            "note": f"prompt {plen} fills the context {backend.context}"}
                else:
                    note = None if cap == STAGE_CAP else f"common cap lowered to {cap} by context {backend.context}"
                    out[(slot, c.label)] = {"supported": True, "cap": cap, "prompt_tokens": plen, "note": note}
            else:
                budget = render.EFFORT_BUDGETS[c.label]
                cap = min(budget + reply_allowance, backend.context - plen)
                if cap < budget:
                    out[(slot, c.label)] = {"supported": False, "cap": max(cap, 0), "prompt_tokens": plen,
                                            "note": f"context {backend.context} cannot hold prompt {plen} + "
                                                    f"{c.label} budget {budget}"}
                else:
                    out[(slot, c.label)] = {"supported": True, "cap": cap, "prompt_tokens": plen,
                                            "note": None if cap == budget + reply_allowance else
                                            f"ceiling bounded by context to {cap}"}
    return out


def run_cell(backend: Backend, prompt: Prompt, cell: Cell, cap_plan: dict, temperature: float,
             instruction: str | None, checker: Callable | None, checker_why: str | None) -> dict:
    base = {"artifact": OUTPUT_ARTIFACT, "do_not_train": True, "slot": cell.slot, "category": prompt.category,
            "task_id": prompt.task_id, "requested_effort": cell.label,
            "requested_budget_tokens": render.EFFORT_BUDGETS[cell.label], "enforced_cap": cap_plan["cap"],
            "cap_note": cap_plan["note"], "seed": cell.seed, "temperature": temperature,
            "prompt_tokens": cap_plan["prompt_tokens"], "backend": backend.name, "template": backend.template,
            "model_id": backend.model_id,
            "instruction_sha256": sha256_text(instruction) if instruction is not None else None}
    if not cap_plan["supported"]:
        return {**base, "ran": False, "unsupported_reason": cap_plan["note"]}
    text = apply_instruction(prompt.text, instruction)
    t0 = time.perf_counter()
    gen = backend.generate(backend.prompt_ids(text, cell.label), cap_plan["cap"], cell.seed, temperature)
    wall = time.perf_counter() - t0
    truncated = gen.stop_reason == "length"
    rec = {**base, "ran": True, "generated_tokens": len(gen.completion_ids), "stop_reason": gen.stop_reason,
           "truncated": truncated, "censored": truncated,
           "context_tokens_total": cap_plan["prompt_tokens"] + len(gen.completion_ids), "wall_s": round(wall, 3),
           "completion": gen.text, "completion_sha256": sha256_text(gen.text)}
    rec.update(analyse(gen.text, backend.count))
    if checker is None:
        rec["functional"] = {"checker": prompt.checker, "success": None, "reason": checker_why}
    else:
        try:
            r = checker(prompt.task, gen.text)
            rec["functional"] = {"checker": prompt.checker, "success": int(r["reward"]), "reason": r.get("reason")}
        except Exception as exc:  # noqa: BLE001  a checker crash is recorded, not hidden
            rec["functional"] = {"checker": prompt.checker, "success": None, "reason": f"checker error: {exc!r}"}
    return rec


def _rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None}


def summarise(records: list[dict], manifest: dict, stage: str) -> dict:
    """Per label: success over every run cell with a checker (censored cells stay in the denominator)."""
    per_label = {}
    for label in LABELS:
        rs = [r for r in records if r["requested_effort"] == label]
        ran = [r for r in rs if r.get("ran")]
        checked = [r for r in ran if r["functional"]["success"] is not None]
        toks = [r["generated_tokens"] for r in ran]
        traces = [r["trace_tokens"] for r in ran if r["parse_status"] == "ok"]
        calls = [r for r in ran if r["tool_call_valid"] is not None]
        per_label[label] = {
            "cells": len(rs), "ran": len(ran), "unsupported": len(rs) - len(ran),
            "functional_success": _rate(sum(r["functional"]["success"] for r in checked), len(checked)),
            "functional_success_censored_in_denominator": sum(1 for r in checked if r["censored"]),
            "no_checker": len(ran) - len(checked),
            "parse_ok": _rate(sum(r["parse_status"] == "ok" for r in ran), len(ran)),
            "parse_malformed": sum(r["parse_status"] == "malformed" for r in ran),
            "empty": sum(r["parse_status"] == "empty" for r in ran),
            "censored_at_cap": _rate(sum(r["censored"] for r in ran), len(ran)),
            "tool_call_valid": _rate(sum(bool(r["tool_call_valid"]) for r in calls), len(calls)),
            "generated_tokens_mean": round(statistics.fmean(toks), 1) if toks else None,
            "generated_tokens_median": statistics.median(toks) if toks else None,
            "trace_tokens_median_parsed_only": statistics.median(traces) if traces else None,
            "wall_s_total": round(sum(r["wall_s"] for r in ran), 2),
        }
    # matched per-prompt changes against the 1k label (same prompt, same seed)
    by = {(r["slot"], r["requested_effort"]): r for r in records if r.get("ran")}
    matched = {}
    for label in LABELS[1:]:
        flips = {"gained": 0, "lost": 0, "same": 0}
        dtok = []
        for slot in {r["slot"] for r in records}:
            a, b = by.get((slot, LABELS[0])), by.get((slot, label))
            if not a or not b:
                continue
            dtok.append(b["generated_tokens"] - a["generated_tokens"])
            sa, sb = a["functional"]["success"], b["functional"]["success"]
            if sa is None or sb is None:
                continue
            flips["gained" if sb > sa else "lost" if sb < sa else "same"] += 1
        matched[f"{label}_vs_{LABELS[0]}"] = {"success_changes": flips, "pairs": len(dtok),
                                              "generated_tokens_delta_median": statistics.median(dtok) if dtok else None}
    unavailable = [{"slot": s["slot"], "category": s["category"], "reason": s["reason"]}
                   for s in manifest["slots"] if s["status"] == "unavailable"]
    return {"artifact": OUTPUT_ARTIFACT, "do_not_train": True, "manifest_sha256": manifest["manifest_sha256"],
            "stage": stage, "cells_ran": sorted([r["slot"], r["requested_effort"]] for r in records if r.get("ran")),
            "cells_unsupported": sorted([r["slot"], r["requested_effort"], r["unsupported_reason"]]
                                        for r in records if not r.get("ran")),
            "per_label": per_label, "matched_vs_1k": matched, "unavailable_slots": len(unavailable),
            "unavailable_by_category": {c: sum(1 for u in unavailable if u["category"] == c)
                                        for c in COMPOSITION if any(u["category"] == c for u in unavailable)},
            "interpretation": "A plain-text effort label is not budget enforcement. Stage A/B use one common cap, so "
                              "they test the effect of the label text at a fixed cap, not four-tier compliance."}


def run_stage(manifest: dict, stage: str, backend: Backend, prompts: dict[str, Prompt], out_dir: Path,
              checkers: dict, checker_why: dict, instructions: dict[str, str | None], temperature: float = 0.0,
              reply_allowance: int = 1024, base_seed: int | None = None) -> dict:
    cells = iter_matrix(manifest, stage, base_seed)
    caps = plan_caps(backend, prompts, cells, stage, instructions, reply_allowance)
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    with open(out_dir / f"effort_stage{stage}.jsonl", "w", encoding="utf-8") as f:
        for c in cells:
            p = prompts[c.slot]
            rec = run_cell(backend, p, c, caps[(c.slot, c.label)], temperature, instructions.get(p.checker),
                           checkers.get(p.checker), checker_why.get(p.checker))
            rec.update(manifest_sha256=manifest["manifest_sha256"], stage=stage)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            records.append(rec)
    summary = summarise(records, manifest, stage)
    summary.update(backend=backend.name, template=backend.template, model_id=backend.model_id,
                   context=backend.context, temperature=temperature,
                   fixture_smoke=bool(getattr(backend, "fixture", False)),
                   instructions={k: sha256_text(v) for k, v in instructions.items() if v is not None})
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


# --- guard and compare ------------------------------------------------------------------------------------

def _strings(obj) -> Iterable[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def guard(manifest: dict, training_files: list[Path], prompt_texts: list[str] | None = None) -> list[str]:
    """Problems found in training files: eval output records, eval task ids, eval prompt texts."""
    ids = set(manifest["training_exclusion"]["task_ids"])
    hashes = set(manifest["training_exclusion"]["text_sha256"])
    problems = []
    for path in training_files:
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    obj = line
                if isinstance(obj, dict) and (obj.get("artifact") == OUTPUT_ARTIFACT or obj.get("do_not_train")):
                    problems.append(f"{path}:{n}: an effort-eval output record")
                    continue
                if isinstance(obj, dict) and obj.get("id") in ids:
                    problems.append(f"{path}:{n}: eval task id {obj['id']}")
                    continue
                for s in _strings(obj):
                    if sha256_text(s) in hashes or (prompt_texts and any(t in s for t in prompt_texts)):
                        problems.append(f"{path}:{n}: contains an eval prompt")
                        break
    return problems


def compare(a: dict, b: dict) -> dict:
    """Matched checkpoint comparison: same manifest, same stage, cells that ran in both."""
    if a["manifest_sha256"] != b["manifest_sha256"] or a["stage"] != b["stage"]:
        raise ValueError("summaries come from different manifests or stages; not comparable")
    common = sorted({tuple(x) for x in a["cells_ran"]} & {tuple(x) for x in b["cells_ran"]})
    return {"manifest_sha256": a["manifest_sha256"], "stage": a["stage"], "matched_cells": len(common),
            "per_label": {lab: {k: (a["per_label"][lab][k], b["per_label"][lab][k])
                                for k in ("functional_success", "parse_ok", "censored_at_cap",
                                          "generated_tokens_median")} for lab in LABELS},
            "note": "per-cell records hold the matched per-prompt changes; this view is aggregate only"}


# --- manifest build (how effort_manifest.json was made) ---------------------------------------------------

def _rank(seed: str, task_id: str) -> str:
    return hashlib.sha256(f"{seed}:{task_id}".encode()).hexdigest()


def select(rows: list[dict], strata_key: Callable[[dict], str], quotas: dict[str, int], seed: str) -> list[dict]:
    """Deterministic stratified pick: lowest sha256(seed:id) within each stratum."""
    picked = []
    for stratum, n in quotas.items():
        pool = sorted((r for r in rows if strata_key(r) == stratum), key=lambda r: _rank(seed, r["id"]))
        if len(pool) < n:
            raise ValueError(f"stratum {stratum}: {len(pool)} candidates < {n}")
        picked += pool[:n]
    return picked


def build_manifest(args) -> dict:
    exclude: set[str] = set()
    for p in args.exclude_ids:
        exclude |= {x.strip() for x in Path(p).read_text().split() if x.strip()}
    load = lambda p: [json.loads(x) for x in open(p, encoding="utf-8")]  # noqa: E731
    cc = [r for r in load(args.rl_v1_cc) if r["id"] not in exclude]
    math = [r for r in load(args.rl_v1_math) if r["id"] not in exclude and r["level"] != "Level ?"]
    cc_pick = select(cc, lambda r: r["judge"], {"aizu": 8, "atcoder": 7, "codechef": 7, "hackerearth": 8}, args.seed)
    m_pick = select(math, lambda r: r["level"], {f"Level {i}": 5 for i in range(1, 6)}, args.seed)
    dirs = dict(x.split("=", 1) for x in args.source_dir)
    mc = _load("g10_effort_math_check_build", Path(args.checker_dir) / "math_check.py")
    slots = []
    for i, r in enumerate(cc_pick):
        pv = r["provenance"]
        row = _read_row(Path(dirs["code_contests"]) / pv["file"], pv["source_ordinal"],
                        ["description", "public_tests", "private_tests", "generated_tests"])
        if row["description"] != r["statement"]:
            raise SourceError(f"{r['id']}: upstream description differs from the RL v1 statement")
        tests = code_tests(row, 20)
        if tests != r["tests"]:
            raise SourceError(f"{r['id']}: upstream tests differ from the RL v1 tests")
        slots.append({"slot": f"code-{i:02d}", "category": "code", "status": "resolved", "task_id": r["id"],
                      "group": f"code_contests/{r['judge']}/{r['id']}", "source": "code_contests",
                      "dataset": pv["dataset"], "revision": pv["revision"], "split": pv["split"], "file": pv["file"],
                      "file_sha256": pv["file_sha256"], "row_index": pv["source_ordinal"], "field": "description",
                      "checker_fields": ["public_tests", "private_tests", "generated_tests"],
                      "text_sha256": sha256_text(r["statement"]), "checker": "stdio", "max_tests": 20,
                      "time_limit_s": r["time_limit_s"],
                      "tests_sha256": sha256_text(json.dumps(tests, ensure_ascii=False, sort_keys=True)),
                      "strata": {"judge": r["judge"], "difficulty": r.get("difficulty")},
                      "licence": pv["licence"], "licence_decision": "allowed (TSAI, 6 Nov): rl-code-code-contests",
                      "generator": pv["generator"]})
    for i, r in enumerate(m_pick):
        pv = r["provenance"]
        row = _read_row(Path(dirs["hendrycks_math"]) / pv["file"], pv["source_ordinal"], ["problem", "solution"])
        if row["problem"] != r["problem"] or mc.last_boxed(row["solution"]) != r["answer"]:
            raise SourceError(f"{r['id']}: upstream row differs from the RL v1 record")
        slots.append({"slot": f"math-{i:02d}", "category": "math", "status": "resolved", "task_id": r["id"],
                      "group": f"hendrycks_math/{r['subject']}/{pv['source_ordinal']}", "source": "hendrycks_math",
                      "dataset": pv["dataset"], "revision": pv["revision"], "split": pv["split"], "file": pv["file"],
                      "file_sha256": pv["file_sha256"], "row_index": pv["source_ordinal"], "field": "problem",
                      "checker_fields": ["solution"], "text_sha256": sha256_text(r["problem"]), "checker": "math",
                      "answer_sha256": sha256_text(r["answer"]),
                      "strata": {"level": r["level"], "subject": r["subject"]}, "licence": pv["licence"],
                      "licence_decision": "named eligible in the T2 brief (MIT); no row in licences/licence_table.md yet",
                      "generator": pv["generator"]})
    reasons = json.loads(Path(args.unavailable).read_text(encoding="utf-8"))
    for cat in ("tool_agentic", "indic", "general"):
        for i in range(COMPOSITION[cat]):
            slots.append({"slot": f"{cat}-{i:02d}", "category": cat, "status": "unavailable",
                          "reason": reasons[cat]})
    resolved = [s for s in slots if s["status"] == "resolved"]
    firsts: dict[tuple, list[str]] = {}
    for s in resolved:  # slots in selection order, grouped by stratum
        stratum = s["strata"]["judge"] if s["category"] == "code" else s["strata"]["level"]
        firsts.setdefault((s["category"], stratum), []).append(s["slot"])
    code_first = [v[0] for k, v in firsts.items() if k[0] == "code"]   # one per judge (4)
    math_first = [v[0] for k, v in firsts.items() if k[0] == "math"]   # one per level (5)
    code_second = next(v[1] for k, v in firsts.items() if k[0] == "code")
    stage_a = code_first + [code_second] + math_first               # 5 code + 5 math, every stratum
    stage_c = code_first + math_first[1:]                            # 4 code + math levels 2 to 5
    manifest = {
        "schema": SCHEMA, "suite": "g10-effort-dev-v1", "frozen": True,
        "note": "Declared development sample (G10_TRAINING.md section 4), not an official G9 weighting. It becomes "
                "development evidence once inspected. Prompt texts are not stored here: each slot points at a row of "
                "a pinned upstream file and holds the sha256 of its text.",
        "labels": list(LABELS), "budgets": {k: render.EFFORT_BUDGETS[k] for k in LABELS},
        "composition": dict(COMPOSITION), "base_seed": args.base_seed, "selection_seed": args.seed,
        "selection": {"pool": "RL v1 candidates (local build of 11 Nov: code_contests non-Codeforces after decontam "
                              "v2; hendrycks MATH train after decontam v2 and the MATH-500 13-gram guard)",
                      "rl_v1_cc_sha256": sha256_file(Path(args.rl_v1_cc)),
                      "rl_v1_math_sha256": sha256_file(Path(args.rl_v1_math)),
                      "excluded_id_files": {Path(p).name: sha256_file(Path(p)) for p in args.exclude_ids},
                      "excluded_ids": len(exclude),
                      "rule": "lowest sha256(selection_seed:id) per stratum; code 8 aizu/7 atcoder/7 codechef/"
                              "8 hackerearth; math 5 per level 1-5"},
        "sources": {
            "code_contests": {"dataset": "deepmind/code_contests", "revision": cc_pick[0]["provenance"]["revision"],
                              "split": "train", "licence": "CC-BY-4.0"},
            "hendrycks_math": {"dataset": "EleutherAI/hendrycks_math", "revision": m_pick[0]["provenance"]["revision"],
                               "split": "train", "licence": "MIT"}},
        "stages": {"A": {"slots": stage_a, "cap": STAGE_CAP,
                         "note": "10-prompt canary, every label: first slot of each code judge and math level, "
                                 "plus the second aizu slot"},
                   "B": {"slots": "all resolved", "cap": STAGE_CAP, "note": "every resolved prompt, every label"},
                   "C": {"slots": stage_c, "cap": "label budget + reply allowance, bounded by the real context",
                         "note": "preregistered subset (first slot of each code judge, first slot of math levels "
                                 "2 to 5); runs only with --stage C"}},
        "slots": slots,
        "training_exclusion": {
            "rule": "These tasks are held out of every SFT/RL training artifact while this suite is in use; RL v1 "
                    "must drop them before training. Run `effort_suite.py guard` on each training file.",
            "task_ids": [s["task_id"] for s in resolved], "text_sha256": [s["text_sha256"] for s in resolved]},
    }
    return seal(manifest)


def build_v2_manifest(args) -> dict:
    """The proposed v2 manifest: v1 unchanged, plus 20 API-Bank call slots (tool_agentic) and 10 QASC slots
    (general), picked with v1's rule: lowest sha256(selection_seed:id), one slot per distinct question (QASC) or per
    dialogue file and per API name (API-Bank). The 15 indic slots stay unavailable."""
    v1 = json.loads(Path(args.v1).read_text(encoding="utf-8"))
    seed = v1["selection_seed"]
    pins = json.loads(Path(args.pins).read_text(encoding="utf-8"))
    qdir, adir = Path(args.qasc_dir), Path(args.apibank_dir)
    qfile = "data/validation-00000-of-00001.parquet"
    import pyarrow.parquet as pq  # noqa: PLC0415
    qrows = pq.read_table(qdir / qfile, columns=["id", "question", "answerKey", "formatted_question"]).to_pylist()
    for i, r in enumerate(qrows):
        r["row_index"] = i
    seen, qpick = set(), []
    for r in sorted(qrows, key=lambda r: _rank(seed, r["id"])):
        if r["question"] in seen:
            continue
        seen.add(r["question"])
        qpick.append(r)
        if len(qpick) == COMPOSITION["general"]:
            break
    docs = apibank_docs(adir / "apis")
    ddir = adir / "lv1-lv2-samples" / "level-1-given-desc"
    cand = []
    for f in sorted(ddir.glob("*-level-1-*.jsonl")):
        rows = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        cand += [{"id": f"apibank/{f.name}#{i}", "file": f.name, "row_index": i, "rows": rows}
                 for i, r in enumerate(rows) if r["role"] == "API"]
    used, used_apis, apick = set(), set(), []
    for r in sorted(cand, key=lambda r: _rank(seed, r["id"])):
        api = r["rows"][r["row_index"]]["api_name"]
        # one call per dialogue file and per API: the set has several near-identical dialogues for one API
        # (same gold call), which would count one item twice
        if r["file"] in used or api in used_apis:
            continue
        used.add(r["file"])
        used_apis.add(api)
        apick.append(r)
        if len(apick) == COMPOSITION["tool_agentic"]:
            break
    q_rev, a_rev = args.qasc_revision, args.apibank_revision
    new: dict[str, dict] = {}
    for i, r in enumerate(apick):
        text, used_docs = apibank_prompt(r["rows"], r["row_index"], docs)
        gold = r["rows"][r["row_index"]]
        rel = f"lv1-lv2-samples/level-1-given-desc/{r['file']}"
        new[f"tool_agentic-{i:02d}"] = {
            "slot": f"tool_agentic-{i:02d}", "category": "tool_agentic", "status": "resolved", "task_id": r["id"],
            "group": r["file"], "source": "api_bank", "dataset": "AlibabaResearch/DAMO-ConvAI (api-bank)",
            "revision": a_rev, "split": "lv1-lv2-samples/level-1-given-desc", "file": rel,
            "file_sha256": pins[f"api-bank/{rel}"], "row_index": r["row_index"], "field": "api_descriptions+dialogue",
            "doc_files": {d: pins[f"api-bank/{d}"] for d in used_docs}, "text_sha256": sha256_text(text),
            "checker": "api_call",
            "gold_sha256": sha256_text(json.dumps(gold["param_dict"], sort_keys=True, ensure_ascii=False) + "|"
                                       + gold["api_name"]),
            "licence": "Apache-2.0", "licence_decision": "proposed 20 Nov 2026: licence row awaiting lead sign-off",
            "generator": "none (annotator-written evaluation dialogues; the API results in them are the set's own)"}
    for i, r in enumerate(qpick):
        new[f"general-{i:02d}"] = {
            "slot": f"general-{i:02d}", "category": "general", "status": "resolved", "task_id": f"qasc-{r['id']}",
            "group": f"qasc/{r['id']}", "source": "qasc", "dataset": "allenai/qasc", "revision": q_rev,
            "split": "validation", "file": qfile, "file_sha256": pins[f"qasc/{qfile}"], "row_index": r["row_index"],
            "field": "formatted_question", "checker_fields": ["answerKey"],
            "text_sha256": sha256_text(r["formatted_question"]), "checker": "answer_key",
            "answer_sha256": sha256_text(r["answerKey"]), "licence": "CC-BY-4.0",
            "licence_decision": "proposed 20 Nov 2026: licence row awaiting lead sign-off",
            "generator": "none (human-authored crowd-sourced questions)"}
    out = copy.deepcopy(v1)
    out.pop("manifest_sha256")
    out["suite"] = "g10-effort-dev-v2-proposed"
    out["frozen"] = True
    out["note"] = (v1["note"] + " PROPOSED v2 (20 Nov 2026): v1's 55 resolved slots unchanged, 30 new slots resolved "
                   "(20 API-Bank calls, 10 QASC questions), 15 indic slots still unavailable. It becomes the suite "
                   "only when the lead signs the two licence rows; effort_manifest.json (v1) is not changed.")
    out["selection_v2"] = {
        "rule": "lowest sha256(selection_seed:id) over every candidate; QASC: one slot per distinct question text "
                "(validation split, 926 rows, 902 distinct questions), id = the row id; API-Bank: every API call in "
                "the level-1 dialogue files (lv1-lv2-samples/level-1-given-desc, files named *-level-1-*), at most "
                "one call per dialogue file and at most one call per API name, id = apibank/<file>#<line index>",
        "qasc_candidates": len(qrows), "apibank_candidates": len(cand), "apibank_files": len({c['file'] for c in cand})}
    out["sources"]["qasc"] = {"dataset": "allenai/qasc", "revision": q_rev, "split": "validation",
                              "licence": "CC-BY-4.0"}
    out["sources"]["api_bank"] = {"dataset": "AlibabaResearch/DAMO-ConvAI api-bank/", "revision": a_rev,
                                  "split": "lv1-lv2-samples/level-1-given-desc", "licence": "Apache-2.0",
                                  "licence_file": "api-bank/LICENSE (the repository root has a different licence)"}
    out["slots"] = [new.get(s["slot"], s) for s in v1["slots"]]
    resolved = [s for s in out["slots"] if s["status"] == "resolved"]
    out["training_exclusion"] = {**v1["training_exclusion"], "task_ids": [s["task_id"] for s in resolved],
                                 "text_sha256": [s["text_sha256"] for s in resolved]}
    return seal(out)


# --- CLI --------------------------------------------------------------------------------------------------

def _dirs(pairs: list[str]) -> dict[str, Path]:
    out = {}
    for p in pairs or []:
        k, _, v = p.partition("=")
        if not v:
            raise SystemExit(f"--source-dir needs name=DIR, got {p!r}")
        out[k] = Path(v)
    return out


def _instructions(pairs: list[str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {"math": None, "stdio": None, "none": None, **DEFAULT_INSTRUCTIONS}
    for p in pairs or []:
        k, _, v = p.partition("=")
        if k not in out or not v:
            raise SystemExit("--instruction needs kind=FILE with kind in math, stdio, none, answer_key, api_call; "
                             f"got {p!r}")
        out[k] = Path(v).read_text(encoding="utf-8")
        apply_instruction("x", out[k])
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify", help="check the manifest hash and structure; with --source-dir, every prompt")
    v.add_argument("--manifest", default=str(HERE / "effort_manifest.json"))
    v.add_argument("--source-dir", action="append", default=[])
    v.add_argument("--checker-dir", default=str(TEAM / "rl-data"))

    p = sub.add_parser("plan", help="print the cells of a stage without a model")
    p.add_argument("--manifest", default=str(HERE / "effort_manifest.json"))
    p.add_argument("--stage", choices=STAGES, default="A")

    r = sub.add_parser("run", help="generate and score one stage")
    r.add_argument("--manifest", default=str(HERE / "effort_manifest.json"))
    r.add_argument("--stage", choices=STAGES, default="A", help="A (default), B, or C (explicit only)")
    r.add_argument("--backend", choices=("hf", "team5"), required=True)
    r.add_argument("--model", help="hf: model path or Hub id (native template; a diagnostic run)")
    r.add_argument("--adapter-config", help="team5: rl-loop adapter config (G10 template)")
    r.add_argument("--allow-fixture-smoke", action="store_true", help="team5: run a FIXTURE bundle; never a result")
    r.add_argument("--device", default="auto")
    r.add_argument("--context", type=int, help="hf: override the model context length")
    r.add_argument("--source-dir", action="append", default=[], help="name=DIR with the pinned files")
    r.add_argument("--checker-dir", default=str(TEAM / "rl-data"))
    r.add_argument("--no-exec", action="store_true", help="do not execute code (code success becomes None)")
    r.add_argument("--instruction", action="append", default=[], help="kind=FILE, team-written, with {problem}")
    r.add_argument("--temperature", type=float, default=0.0)
    r.add_argument("--reply-allowance", type=int, default=1024, help="stage C: tokens above the label budget")
    r.add_argument("--no-verify-files", action="store_true", help="skip file sha256 (text hashes still checked)")
    r.add_argument("--out", required=True)

    g = sub.add_parser("guard", help="fail if a training file holds eval outputs, eval ids or eval prompts")
    g.add_argument("--manifest", default=str(HERE / "effort_manifest.json"))
    g.add_argument("--training", action="append", required=True)
    g.add_argument("--source-dir", action="append", default=[], help="also search for the prompt texts")

    c = sub.add_parser("compare", help="aggregate matched comparison of two summaries")
    c.add_argument("a")
    c.add_argument("b")

    b = sub.add_parser("build-manifest", help="select prompts from the RL v1 candidates and seal a manifest")
    b.add_argument("--rl-v1-cc", required=True)
    b.add_argument("--rl-v1-math", required=True)
    b.add_argument("--exclude-ids", action="append", default=[], help="id lists used by earlier experiments")
    b.add_argument("--source-dir", action="append", default=[])
    b.add_argument("--checker-dir", default=str(TEAM / "rl-data"))
    b.add_argument("--unavailable", required=True, help="JSON {category: reason} for slots with no source")
    b.add_argument("--seed", default="g10-effort-dev-v1")
    b.add_argument("--base-seed", type=int, default=20261111)
    b.add_argument("--out", required=True)

    b2 = sub.add_parser("build-v2-manifest", help="seal the proposed v2 manifest (v1 slots + API-Bank + QASC)")
    b2.add_argument("--v1", default=str(HERE / "effort_manifest.json"))
    b2.add_argument("--pins", required=True, help="JSON {relative path: sha256} of the downloaded files")
    b2.add_argument("--qasc-dir", required=True)
    b2.add_argument("--qasc-revision", required=True)
    b2.add_argument("--apibank-dir", required=True)
    b2.add_argument("--apibank-revision", required=True)
    b2.add_argument("--out", required=True)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "build-manifest":
        m = build_manifest(args)
        Path(args.out).write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"manifest_sha256": m["manifest_sha256"],
                          "resolved": sum(s["status"] == "resolved" for s in m["slots"])}))
        return 0
    if args.cmd == "build-v2-manifest":
        m = build_v2_manifest(args)
        Path(args.out).write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"manifest_sha256": m["manifest_sha256"],
                          "resolved": sum(s["status"] == "resolved" for s in m["slots"])}))
        return 0
    if args.cmd == "compare":
        a, b_ = (json.loads(Path(x).read_text(encoding="utf-8")) for x in (args.a, args.b))
        print(json.dumps(compare(a, b_), indent=1))
        return 0

    manifest = load_manifest(args.manifest)
    if args.cmd == "verify":
        out = {"manifest_sha256": manifest["manifest_sha256"],
               "resolved": sum(s["status"] == "resolved" for s in manifest["slots"]),
               "unavailable": sum(s["status"] == "unavailable" for s in manifest["slots"])}
        if args.source_dir:
            _, _, lb = load_checkers(Path(args.checker_dir), execute_code=False)
            out["prompts_verified"] = len(resolve_prompts(manifest, _dirs(args.source_dir), last_boxed=lb))
            out["answers_verified"] = lb is not None
        print(json.dumps(out))
        return 0
    if args.cmd == "plan":
        cells = iter_matrix(manifest, args.stage)
        print(json.dumps({"stage": args.stage, "cells": len(cells), "prompts": len({c.slot for c in cells}),
                          "labels": list(LABELS), "cap": manifest["stages"][args.stage]["cap"],
                          "unavailable_slots": sum(s["status"] == "unavailable" for s in manifest["slots"])}))
        return 0
    if args.cmd == "guard":
        texts = None
        if args.source_dir:
            texts = [p.text for p in resolve_prompts(manifest, _dirs(args.source_dir)).values()]
        problems = guard(manifest, [Path(x) for x in args.training], texts)
        for x in problems[:50]:
            print(x)
        print(json.dumps({"problems": len(problems)}))
        return 1 if problems else 0

    # run
    instructions = _instructions(args.instruction)
    checkers, why, last_boxed = load_checkers(Path(args.checker_dir), execute_code=not args.no_exec)
    prompts = resolve_prompts(manifest, _dirs(args.source_dir), verify_files=not args.no_verify_files,
                              last_boxed=last_boxed, slots=stage_slots(manifest, args.stage))
    if args.backend == "hf":
        if not args.model:
            raise SystemExit("--backend hf needs --model")
        backend: Backend = HFBackend(args.model, args.device, args.context)
    else:
        if not args.adapter_config:
            raise SystemExit("--backend team5 needs --adapter-config")
        dev = "cpu" if args.device == "auto" else args.device
        backend = TeamFiveBackend(args.adapter_config, dev, args.allow_fixture_smoke)
    s = run_stage(manifest, args.stage, backend, prompts, Path(args.out), checkers, why, instructions,
                  args.temperature, args.reply_allowance)
    print(json.dumps({k: s[k] for k in ("stage", "manifest_sha256", "template", "unavailable_slots")}
                     | {"cells_ran": len(s["cells_ran"]), "cells_unsupported": len(s["cells_unsupported"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
