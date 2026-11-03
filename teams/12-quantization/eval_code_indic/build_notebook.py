#!/usr/bin/env python3
"""Build eval_code_indic.ipynb (Kaggle or Colab) from the .py files here and in ../eval_mini.

    python build_notebook.py

The notebook carries its own copy of run_code_indic_gguf.py, paired.py and, from ../eval_mini, llamacpp_lm.py,
run_mini_gguf.py (machine name), test_llamacpp_lm.py and paired.py (as paired_stats.py). Setup, the llama-cpp-python
build and the bf16 conversion are the cells of ../eval_mini/build_notebook.py, reused as they are, so both
notebooks score with the same backend. G9's spec and MILU task configs come from upstream at a pinned commit.
"""
import hashlib, importlib.util, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MINI = HERE.parent / "eval_mini"
SOURCES = {"run_code_indic_gguf.py": HERE / "run_code_indic_gguf.py", "paired.py": HERE / "paired.py",
           "llamacpp_lm.py": MINI / "llamacpp_lm.py", "run_mini_gguf.py": MINI / "run_mini_gguf.py",
           "test_llamacpp_lm.py": MINI / "test_llamacpp_lm.py", "paired_stats.py": MINI / "paired.py"}
G9_COMMIT = "fa5d87e41ebeca1ecf4546091f32a16d179bbafb"   # upstream main, 1 Nov; harness_code_indic as of 28 Oct
EVALPLUS_DEPS = ("wget==3.2 tempdir==0.7.1 multipledispatch==1.0.0 appdirs==1.4.4 termcolor==3.3.0 fire==0.7.1 "
                 "tree-sitter==0.26.0 tree-sitter-python==0.25.0 rich==15.0.0 psutil==7.2.2")

_spec = importlib.util.spec_from_file_location("mini_build", MINI / "build_notebook.py")
mini = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(mini)
md, code = mini.md, mini.code


def reuse(i, replacements=()):
    """Cell i of eval_mini's notebook, with exact-text replacements (each must match)."""
    text = "".join(mini.CELLS[i]["source"])
    for old, new in replacements:
        assert old in text, f"eval_mini cell {i} changed: {old!r} not found"
        text = text.replace(old, new)
    return code(text)


CELLS = [
md("""
# G12: G9's eval-mini v0 code + Indic on OLMoE GGUF files (Kaggle or Colab)

Runs G9's code + Indic half of eval-mini v0 (`teams/09-evaluation/harness_code_indic/eval_mini_v0_spec.json`):
MMLU-Pro 300, GSM8K 100, Belebele hin/tel/tam and MILU Hindi/Telugu/Tamil/Bengali 100 each (5-shot, lm_eval
0.4.13), HumanEval+ 164 and MBPP+ 378 (evalplus 0.3.1, greedy, base prompt). Every format goes through the same
backend as `eval_mini.ipynb` (llama-cpp-python in-process, each file checked by `test_llamacpp_lm.py` first), with
per-item logs, then each format is compared with bf16 item by item (`paired.py`).

- **MILU is gated** on Hugging Face: accept its terms at https://huggingface.co/datasets/ai4bharat/MILU with your
  account, make a read token, and add it as a secret named `HF_TOKEN` (Kaggle: Add-ons → Secrets; Colab: the key
  icon). Without it the run stops, unless you set `SKIP_GATED = True`.
- **Kaggle:** Accelerator **GPU T4 x2**, Internet **on**, then **Save Version → Save & Run All (Commit)**.
  `LIMIT = 3` gives a quick end-to-end check first.
- Code answers are executed by evalplus on the notebook's machine (Linux).
"""),
code("""
# --- settings -----------------------------------------------------------------------------------------------
FORMATS   = ["bf16", "Q8_0"]   # <-- formats for this run; G12 week 2: bf16, Q8_0, Q4_K_M, Q3_K_M
RUN_BY    = ""                 # <-- your GitHub handle, recorded with the results
LIMIT     = None               # None = the full set; 3 = quick end-to-end check (not combinable)
SKIP_GATED = False             # True = leave out MILU (no Hugging Face token)
ONLY_TASKS = None              # e.g. ["milu_Hindi", "milu_Telugu", "milu_Tamil", "milu_Bengali"]: run just these
BASE      = "bf16"             # paired comparison is made against this when it is in the same run
N_CTX     = 4096               # OLMoE's trained context; longer 5-shot prompts are left-truncated (counted per task)
MODEL, REVISION = "allenai/OLMoE-1B-7B-0924", "6d84c48581ece794365f2b8e9cfb043c68ade9c5"  # team pin
LLAMA_TAG = "b11669"           # llama.cpp build of the team's conversion/quantization
LLAMA_CPP_PYTHON = "0.3.36"    # in-process log-probabilities checked correct with this version
G9_REPO, G9_COMMIT = "https://github.com/theschoolofai/era-v5-lab", "__G9_COMMIT__"
DRIVE_DIR = "/content/drive/MyDrive/era-v5-g12/eval_code_indic"   # Colab, when Drive mounts
BF16_FALLBACK_GPU_LAYERS = 12  # of 16 layers, only if bf16 does not fit on the GPU(s)
NOTEBOOK_VERSION = "__NOTEBOOK_VERSION__"   # fingerprint of the embedded code
assert FORMATS and all(f in {"bf16", "Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M", "Q2_K"} for f in FORMATS), FORMATS
"""),
reuse(2, [('"/kaggle/working/eval_mini_out", "/kaggle/tmp/eval_mini_work"',
           '"/kaggle/working/eval_code_indic_out", "/kaggle/tmp/eval_code_indic_work"'),
          ('"/content/eval_mini_out", "/content/work"', '"/content/eval_code_indic_out", "/content/work"'),
          ('CODE = f"{WORK}/eval_mini_code"', 'CODE = f"{WORK}/eval_code_indic_code"'),
          ('"LLAMA_TAG", "LLAMA_CPP_PYTHON", "BF16_FALLBACK_GPU_LAYERS")',
           '"LLAMA_TAG", "LLAMA_CPP_PYTHON", "BF16_FALLBACK_GPU_LAYERS", "SKIP_GATED", "ONLY_TASKS", "N_CTX", "G9_COMMIT")')]),
code("""
# MILU is gated: checked before the long build, so a missing secret or missing access stops the run in the first
# minute. MILU_REVISION is the spec's dataset revision (checked against the spec below, once it is downloaded).
MILU_REVISION = "846d7016558b2004386f30e59a2158731262492f"
# the token comes from the platform's secrets (never printed) and reaches the runs through HF_TOKEN
token = os.environ.get("HF_TOKEN")
if not token and IN_KAGGLE:
    try:
        from kaggle_secrets import UserSecretsClient
        token = UserSecretsClient().get_secret("HF_TOKEN")
    except Exception as e:
        print(f"no Kaggle secret HF_TOKEN ({type(e).__name__})")
if not token and IN_COLAB:
    try:
        from google.colab import userdata
        token = userdata.get("HF_TOKEN")
    except Exception as e:
        print(f"no Colab secret HF_TOKEN ({type(e).__name__})")
if not SKIP_GATED:
    if not token:
        raise RuntimeError("no HF_TOKEN secret: add your Hugging Face token as the secret HF_TOKEN, attached to this "
                           "notebook, or set SKIP_GATED = True")
    import urllib.request
    # a data file: a gated repo serves its README without a token, so only a data file tests access
    req = urllib.request.Request(f"https://huggingface.co/datasets/ai4bharat/MILU/resolve/{MILU_REVISION}/Hindi/test-00000-of-00001.parquet",
                                 headers={"Authorization": f"Bearer {token}", "Range": "bytes=0-99"})
    try:
        urllib.request.urlopen(req, timeout=30).read(100)
    except Exception as e:
        raise RuntimeError("cannot read ai4bharat/MILU: accept its terms on Hugging Face with the account of your "
                           f"HF_TOKEN, or set SKIP_GATED = True ({e})")
    os.environ["HF_TOKEN"] = token
    print("MILU: access OK")
ENV["milu"] = not SKIP_GATED; save_env()
"""),
"__SOURCE_CELL__",
reuse(4, [('f"{LLAMA_SPEC} lm_eval==0.4.13 datasets==5.1.0 && touch {EVAL_VENV}/.ready"',
           # evalplus without its dependencies: they include transformers and stop-sequencer (torch), which this
           # venv must not have; the ones the code path imports are listed and pinned
           'f"{LLAMA_SPEC} lm_eval==0.4.13 datasets==5.1.0 __EVALPLUS_DEPS__ "\n'
           '       f"&& uv pip install -q --python {EVAL_VENV}/bin/python --no-deps evalplus==0.3.1 && touch {EVAL_VENV}/.ready"'),
          ("\"import importlib.util, json, llama_cpp, lm_eval, datasets, platform\",",
           "\"import importlib.util, json, llama_cpp, lm_eval, datasets, platform, evalplus.evaluate\","),
          ("\"  'lm_eval': lm_eval.__version__, 'datasets': datasets.__version__,\",",
           "\"  'lm_eval': lm_eval.__version__, 'datasets': datasets.__version__, 'evalplus': evalplus.__version__,\",")]),
code("""
# G9's definition at a pinned commit: the spec (tasks, doc_ids, shots) and the MILU task configs
G9_DIR = f"{WORK}/g9/teams/09-evaluation/harness_code_indic"
if not os.path.exists(f"{G9_DIR}/eval_mini_v0_spec.json"):
    sh(f"rm -rf {WORK}/g9 && git clone -q --filter=blob:none --no-checkout {G9_REPO} {WORK}/g9 "
       f"&& git -C {WORK}/g9 sparse-checkout set teams/09-evaluation/harness_code_indic "
       f"&& git -C {WORK}/g9 checkout -q {G9_COMMIT}")
ENV["g9_commit"] = G9_COMMIT; save_env()

spec = json.load(open(f"{G9_DIR}/eval_mini_v0_spec.json"))
assert not ENV["milu"] or spec["tasks"]["milu_Hindi"]["dataset_revision"] == MILU_REVISION, "MILU revision changed"
"""),
reuse(6),
code("""
# every format: quantize (output layer Q8_0 below 8 bits, as scripts/quantize_eval.py), check the backend on this
# file, run all tasks. Saved after each task; a format whose tasks are all done is skipped.
spec = json.load(open(f"{G9_DIR}/eval_mini_v0_spec.json"))
TASKS = [t for t, v in spec["tasks"].items() if not (SKIP_GATED and v["dataset"] == "ai4bharat/MILU")]
TASKS += ["humaneval_plus", "mbpp_plus"]
if ONLY_TASKS:
    assert set(ONLY_TASKS) <= set(TASKS), ONLY_TASKS
    TASKS = [t for t in TASKS if t in ONLY_TASKS]
RUNS = f"{OUT}/runs_" + "-".join(FORMATS) + (f"_limit{LIMIT}" if LIMIT else "") + ("_" + "-".join(ONLY_TASKS) if ONLY_TASKS else "")

def finished(fmt):
    p = f"{RUNS}/{fmt}/summary.json"
    return os.path.exists(p) and {r["task"] for r in json.load(open(p))["records"]} >= set(TASKS)

def tensor_types(gguf):
    \"\"\"Router (ffn_gate_inp) and output-layer tensor types, read with gguf-py from the converter's venv; the
    same check as scripts/quantize_eval.py. The run stops if the router is not F32 or BF16.\"\"\"
    code = ("import sys,collections; from gguf import GGUFReader\\n"
            "t=collections.defaultdict(set)\\n"
            "for x in GGUFReader(sys.argv[1]).tensors:\\n"
            "  k='router' if 'ffn_gate_inp' in x.name else 'output' if x.name=='output.weight' else 'embd' if x.name=='token_embd.weight' else None\\n"
            "  if k: t[k].add(x.tensor_type.name)\\n"
            "print('|'.join(sorted(t['router'])) or '-', '|'.join(sorted(t['output'])) or 'tied:'+'|'.join(sorted(t['embd'])))")
    out = subprocess.run(["env", "-u", "PYTHONPATH", f"{WORK}/convert-venv/bin/python", "-c", code, gguf],
                         capture_output=True, text=True, check=True).stdout.split()
    types = {"router": out[0], "output": out[1]}
    if types["router"] != "-" and not set(types["router"].split("|")) <= {"F32", "BF16"}:
        raise RuntimeError(f"{gguf}: router tensors are {types['router']}, not F32/BF16")
    return types

def run_format(fmt, gguf, gpu_layers):
    sh(f"cd {CODE} && {EVAL_PY} run_code_indic_gguf.py --gguf {gguf} --format {fmt} --out {RUNS} "
       f"--g9-dir {G9_DIR} --n-ctx {N_CTX} --n-gpu-layers {gpu_layers} --tasks {' '.join(TASKS)}"
       + (f" --limit {LIMIT}" if LIMIT else ""), log=f"{OUT}/logs/run_{fmt}.log")

for fmt in FORMATS:
    if finished(fmt):
        print(f"{fmt}: all tasks done, skipped"); continue
    t0 = time.time()
    gguf = BF16 if fmt == "bf16" else f"{WORK}/{NAME}-{fmt}.gguf"
    made_here = False
    if not os.path.exists(gguf):
        extra = "" if fmt == "Q8_0" else "--output-tensor-type q8_0"
        sh(f"{QUANTIZE} {extra} {BF16} {gguf} {fmt}", log=f"{OUT}/logs/quantize_{fmt}.log"); made_here = True
    types = tensor_types(gguf); print(f"{fmt}: router {types['router']}, output {types['output']}")
    sh(f"cd {CODE} && {EVAL_PY} test_llamacpp_lm.py {gguf}", log=f"{OUT}/logs/test_llamacpp_lm_{fmt}.log")
    gpu_layers = -1
    try:
        run_format(fmt, gguf, gpu_layers)
    except RuntimeError:
        tail = open(f"{OUT}/logs/run_{fmt}.log").read()[-20000:].lower()
        if fmt != "bf16" or not any(k in tail for k in ("out of memory", "failed to allocate", "cudamalloc")):
            raise
        gpu_layers = BF16_FALLBACK_GPU_LAYERS
        print(f"bf16 ran out of GPU memory with all layers on the GPU; retrying with {gpu_layers} GPU layers")
        run_format(fmt, gguf, gpu_layers)
    ENV["formats"][fmt] = {"gpu_layers": gpu_layers, "gguf_bytes": os.path.getsize(gguf), "tensor_types": types,
                           "wall_clock_s": round(time.time() - t0), "finished": datetime.datetime.now().isoformat(timespec="seconds")}
    save_env()
    if made_here and fmt != "bf16":
        os.remove(gguf)
"""),
code("""
# results: scores per format (points), the paired comparison with the base, a zip of everything
import pandas as pd
rows = []
for p in sorted(glob.glob(f"{RUNS}/*/summary.json")):
    s = json.load(open(p))
    for r in s["records"]:
        rows.append({"format": s["run_meta"]["format"], "task": r["task"], "metric": f"{r['metric']} {r['filter']}",
                     "points": round(100 * r["value"], 1), "stderr": round(100 * (r["stderr"] or 0), 1),
                     "n": r["n_items"], "seconds": r["wall_clock_s"], "truncated": r.get("truncated_requests")})
long = pd.DataFrame(rows)
long.to_csv(f"{RUNS}/scores_long.csv", index=False)
scores = long.pivot_table(index="format", columns="task", values="points").reindex([f for f in FORMATS if f in set(long.format)])
scores.to_csv(f"{RUNS}/scores.csv")
print(scores.T.to_string())
if os.path.exists(f"{RUNS}/{BASE}/summary.json") and len(FORMATS) > 1:
    sh(f"{EVAL_PY} {CODE}/paired.py {RUNS} --base {BASE} --out {RUNS}/paired.md")
ENV["finished"] = datetime.datetime.now().isoformat(timespec="seconds"); save_env()
shutil.copy(f"{OUT}/environment.json", f"{RUNS}/environment.json")
shutil.copytree(f"{OUT}/logs", f"{RUNS}/logs", dirs_exist_ok=True)
zip_path = shutil.make_archive(RUNS, "zip", RUNS)
print("\\nEverything is in", RUNS, "and", zip_path)
"""),
md("""
## Send back

**Kaggle:** download `eval_code_indic_out/runs*.zip` from the version's Output tab. **Colab:** it is in the Drive
folder, or download it from the runtime before the session ends. Per format: `summary.json`, one `*.samples.jsonl`
per task (doc_id and metric values only), `evalplus/` (answers and evalplus's results); plus `scores.csv`,
`scores_long.csv`, `paired.md`, `environment.json` and `logs/`.
"""),
]


def build() -> Path:
    src = {name: path.read_text() for name, path in SOURCES.items()}
    writer = ["# the evaluation code, embedded by eval_code_indic/build_notebook.py",
              "SOURCES = " + json.dumps(src, ensure_ascii=True, indent=0),
              "for _name, _text in SOURCES.items():",
              "    open(f\"{CODE}/{_name}\", \"w\").write(_text)",
              "print(\"wrote\", sorted(SOURCES), \"to\", CODE)"]
    version = hashlib.sha256(("".join(src[k] for k in sorted(src)) + Path(__file__).read_text()
                              + (MINI / "build_notebook.py").read_text()).encode()).hexdigest()[:12]
    cells = [code("\n".join(writer)) if c == "__SOURCE_CELL__" else c for c in CELLS]
    subs = {"__NOTEBOOK_VERSION__": version, "__G9_COMMIT__": G9_COMMIT, "__EVALPLUS_DEPS__": EVALPLUS_DEPS}
    for c in cells:
        for k, v in subs.items():
            c["source"] = [line.replace(k, v) for line in c["source"]]
    nb = {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                       "language_info": {"name": "python"}, "accelerator": "GPU",
                       "colab": {"provenance": [], "gpuType": "T4"}}}
    out = HERE / "eval_code_indic.ipynb"
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=True) + "\n")
    return out


if __name__ == "__main__":
    print("wrote", build())
