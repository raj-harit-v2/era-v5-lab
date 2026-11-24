#!/usr/bin/env python3
"""Build eval_wide.ipynb (Kaggle) from the .py files here and in ../eval_mini.

    python build_notebook.py

Reuses eval_mini's setup, llama-cpp-python build, eval venv and bf16 conversion cells (read from
../eval_mini/build_notebook.py, so a fix there carries over), then runs run_wide_gguf.py per format and
paired.py. The notebook embeds its own copy of the code, so it runs without a branch being pushed.
G9's MILU task configs come from upstream main (sparse clone of teams/09-evaluation/harness_code_indic).
"""
import hashlib, importlib.util, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MINI = HERE.parent / "eval_mini"
# file name in the notebook's code folder -> source file
SOURCES = {"llamacpp_lm.py": MINI / "llamacpp_lm.py", "run_mini_gguf.py": MINI / "run_mini_gguf.py",
           "test_llamacpp_lm.py": MINI / "test_llamacpp_lm.py", "paired_stats.py": MINI / "paired.py",
           "run_wide_gguf.py": HERE / "run_wide_gguf.py", "paired.py": HERE / "paired.py"}

_spec = importlib.util.spec_from_file_location("mini_build", MINI / "build_notebook.py")
mini = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(mini)


def pick(marker: str) -> dict:
    hits = [c for c in mini.CELLS if isinstance(c, dict) and c["cell_type"] == "code" and marker in "".join(c["source"])]
    assert len(hits) == 1, (marker, len(hits))
    return hits[0]


md, code = mini.md, mini.code

CELLS = [
md("""
# G12: wide benchmark pass on GGUF files (Kaggle)

Full MMLU, ARC-C and MILU (Kannada, Hindi, Telugu, Tamil, Bengali) on bf16 and the llama.cpp formats you list, through
the same in-process llama-cpp-python backend as eval_mini, with per-item logs, then each format against bf16 item by
item. Scope and sample sizes: `teams/12-quantization/docs/wide_benchmark_scope.md`.

**Timing run first:** keep `CAP = 20` and `FORMATS = ["bf16"]`, then send back the `s/item` line of every task.
For the real run set `CAP` to the agreed value (or `None` for full splits) and your assigned formats.

Kaggle: Accelerator **GPU T4 x2**, Internet **on**, Add-ons, Secrets: `HF_TOKEN` (read token of an account that accepted
the terms of `ai4bharat/MILU`). Use **Save Version, Save & Run All (Commit)**.
"""),
code("""
# --- settings -----------------------------------------------------------------------------------------------
FORMATS   = ["bf16"]           # <-- your formats: bf16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, Q2_K
RUN_BY    = ""                 # <-- your GitHub handle, recorded with the results
CAP       = 20                 # items per task (MMLU: per subject); None = full splits. Same cap for every format of a model
SKIP_GATED = False             # True leaves MILU out (no HF_TOKEN)
TASKS     = None               # None = every task of run_wide_gguf.WIDE; or a list, e.g. ["mmlu", "arc_challenge"]
N_CTX     = 4096
BASE      = "bf16"
MODEL, REVISION = "sarvamai/sarvam-1", "e9607337286ddf496d4a2562b194e489dcf3feea"   # Granite 3.0 MoE: pin from #643
LLAMA_TAG = "b11669"
LLAMA_CPP_PYTHON = "0.3.36"
DRIVE_DIR = "/content/drive/MyDrive/era-v5-g12/eval_wide"
BF16_FALLBACK_GPU_LAYERS = 12  # only if bf16 does not fit on the GPUs
LIMIT = None                   # unused here; kept because the shared setup cells record it
NOTEBOOK_VERSION = "__NOTEBOOK_VERSION__"
assert FORMATS and all(f in {"bf16", "Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M", "Q2_K"} for f in FORMATS), FORMATS
"""),
pick("LOCAL_TEST = bool(os.environ"),          # environment, folders, sh()
"__SOURCE_CELL__",
pick("llama-cpp-python with CUDA"),            # CUDA wheel + evaluation venv
code("""
# G9's MILU task configs (upstream main), HF token for the gated MILU dataset
G9_DIR = f"{WORK}/era-v5-lab/teams/09-evaluation/harness_code_indic"
if not os.path.isdir(G9_DIR):
    sh(f"git clone -q --depth 1 --filter=blob:none --sparse https://github.com/theschoolofai/era-v5-lab {WORK}/era-v5-lab "
       f"&& git -C {WORK}/era-v5-lab sparse-checkout set teams/09-evaluation/harness_code_indic")
sys.path.insert(0, CODE)
if not SKIP_GATED:
    try:
        from kaggle_secrets import UserSecretsClient
        os.environ["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
    except Exception as e:
        if not os.environ.get("HF_TOKEN"):
            raise RuntimeError(f"HF_TOKEN missing ({e!r}): add it under Add-ons, Secrets, or set SKIP_GATED = True")
    sh(f"curl -fsS -o /dev/null -H 'Authorization: Bearer '$HF_TOKEN https://huggingface.co/api/datasets/ai4bharat/MILU "
       "|| (echo 'HF_TOKEN cannot read ai4bharat/MILU: accept its terms with that account' && false)")
"""),
pick("bf16 GGUF: the llama.cpp converter"),    # llama-quantize build + conversion
code("""
# every format: quantize (output layer Q8_0 below 8 bits, as quantize_eval.py), guard test, wide pass, per-task save
RUNS = f"{OUT}/runs_" + "-".join(FORMATS) + (f"_cap{CAP}" if CAP else "_full")

def run_format(fmt, gguf, gpu_layers):
    sh(f"cd {CODE} && {EVAL_PY} run_wide_gguf.py --gguf {gguf} --format {fmt} --out {RUNS} --g9-dir {G9_DIR} "
       f"--model {MODEL} --revision {REVISION} --n-ctx {N_CTX} --n-gpu-layers {gpu_layers}"
       + (f" --cap {CAP}" if CAP else "") + (" --skip-gated" if SKIP_GATED else "")
       + (" --tasks " + " ".join(TASKS) if TASKS else ""), log=f"{OUT}/logs/run_{fmt}.log")

for fmt in FORMATS:
    t0 = time.time()
    gguf = BF16 if fmt == "bf16" else f"{WORK}/{NAME}-{fmt}.gguf"
    made_here = False
    if not os.path.exists(gguf):
        extra = "" if fmt == "Q8_0" else "--output-tensor-type q8_0"
        sh(f"{QUANTIZE} {extra} {BF16} {gguf} {fmt}", log=f"{OUT}/logs/quantize_{fmt}.log"); made_here = True
    sh(f"cd {CODE} && {EVAL_PY} test_llamacpp_lm.py {gguf}", log=f"{OUT}/logs/test_llamacpp_lm_{fmt}.log")
    gpu_layers = -1
    try:
        run_format(fmt, gguf, gpu_layers)
    except RuntimeError:
        tail = open(f"{OUT}/logs/run_{fmt}.log").read()[-20000:].lower()
        if fmt != "bf16" or not any(k in tail for k in ("out of memory", "failed to allocate", "cudamalloc")):
            raise
        gpu_layers = BF16_FALLBACK_GPU_LAYERS
        print(f"bf16 ran out of GPU memory; retrying with {gpu_layers} GPU layers")
        run_format(fmt, gguf, gpu_layers)
    ENV["formats"][fmt] = {"gpu_layers": gpu_layers, "gguf_bytes": os.path.getsize(gguf),
                           "wall_clock_s": round(time.time() - t0), "finished": datetime.datetime.now().isoformat(timespec="seconds")}
    save_env()
    if made_here and fmt != "bf16":
        os.remove(gguf)
"""),
code("""
# results: timing per task, paired comparison with the base, a zip of everything
rows = []
for p in sorted(glob.glob(f"{RUNS}/*/summary.json")):
    s = json.load(open(p))
    for r in s["records"]:
        rows.append({"format": s["run_meta"]["format"], "task": r["task"], "n": r["n_items"], "score": round(100 * r["value"], 1),
                     "seconds": r["wall_clock_s"], "s_per_item": round(r["wall_clock_s"] / r["n_items"], 3),
                     "truncated": r["truncated_requests"]})
import pandas as pd
long = pd.DataFrame(rows); long.to_csv(f"{RUNS}/scores_long.csv", index=False)
print(long.to_string(index=False))
if os.path.exists(f"{RUNS}/{BASE}/summary.json") and len(FORMATS) > 1:
    sh(f"{EVAL_PY} {CODE}/paired.py {RUNS} --base {BASE} --out {RUNS}/paired.md")
ENV["finished"] = datetime.datetime.now().isoformat(timespec="seconds"); save_env()
shutil.copy(f"{OUT}/environment.json", f"{RUNS}/environment.json")
shutil.copytree(f"{OUT}/logs", f"{RUNS}/logs", dirs_exist_ok=True)
zip_path = shutil.make_archive(RUNS, "zip", RUNS)
print("\\nEverything is in", RUNS, "and", zip_path, "(Kaggle: the version's Output tab)")
"""),
]


def build() -> Path:
    src = {name: path.read_text() for name, path in SOURCES.items()}
    writer = ["# the evaluation code, embedded by build_notebook.py",
              "SOURCES = " + json.dumps(src, ensure_ascii=True, indent=0),
              "for _name, _text in SOURCES.items():",
              "    open(f\"{CODE}/{_name}\", \"w\").write(_text)",
              "print(\"wrote\", sorted(SOURCES), \"to\", CODE)"]
    version = hashlib.sha256("".join(src[k] for k in sorted(src)).encode()).hexdigest()[:12]
    cells = [code("\n".join(writer)) if c == "__SOURCE_CELL__" else c for c in CELLS]
    for c in cells:
        c["source"] = [line.replace("__NOTEBOOK_VERSION__", version) for line in c["source"]]
    nb = {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                       "language_info": {"name": "python"}, "accelerator": "GPU"}}
    out = HERE / "eval_wide.ipynb"
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=True) + "\n")
    return out


if __name__ == "__main__":
    print("wrote", build())
