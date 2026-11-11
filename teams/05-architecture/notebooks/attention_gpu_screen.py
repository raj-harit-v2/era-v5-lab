import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", auto_download=["html"])

with app.setup:
    import csv
    import hashlib
    import shlex
    import zipfile
    import importlib.metadata as metadata
    import json
    import os
    import platform
    import shutil
    import subprocess
    import sys
    from concurrent.futures import ThreadPoolExecutor
    from dataclasses import dataclass
    from pathlib import Path
    from urllib.request import urlopen

    # Set the deterministic CUDA contract before the first GPU operation.
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import torch

    # The existing project is CPU-thread sensitive; keep smoke jobs predictable.
    torch.set_num_threads(4)
    import math
    import statistics
    import time
    import yaml



@app.cell(hide_code=True)
def lab_intro():
    mo.md(r"""
    # Attention GPU lab · one-seed screen

    **Goal:** compare five attention designs with one reproducible training start.
    We use **seed 1235** for every design, as requested. A seed fixes the random
    starting weights and training-data order; it is not an architecture setting.

    The same seed scored best in the earlier learning-rate screen. That observation
    is specific to those runs and does not guarantee the best start for these models.
    This notebook separates **synthetic execution checks** from the full-step
    **real-data screen**. Model and optimizer mathematics stay upstream; a documented CPU-sampler restore repair enables GPU checkpoint resume.

    Opening the notebook starts no training. Run controls are explicit and jobs run
    with optional capacity-checked overlap. Evidence downloads exclude datasets, token caches and model checkpoints.
    """)
    return


@app.cell(hide_code=True)
def reading_the_settings():
    mo.md(r"""
    ## Reading the run settings

    | Setting | Meaning here |
    |---|---|
    | Token | One numbered piece of text produced by the tokenizer |
    | Context 2,048 | Up to 2,048 tokens in one text window |
    | Global batch 8 | Eight windows contribute to one weight update |
    | Microbatch 1 | Process those windows one at a time, accumulating the update |
    | Learning rate 0.001 | The proposed size scale for weight updates |
    | bf16 | The GPU number format used for the model calculations |
    | BPB | Prediction error in bits per original text byte; lower is better |

    A training-loss curve shows progress on training batches. The held-out BPB
    measures prediction on separate text. A single seed provides no seed range.
    """)
    return


@app.cell
def background_task_registry():
    # Keep background tasks alive across display and setup refreshes.
    job_registry = {}

    return (job_registry,)


@app.cell
def hardware():
    hardware = {
        "python": platform.python_version(),
        "cpu_cores_visible": os.cpu_count(),
        "ram_gib_visible": round(
            os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 2**30, 1
        ),
        "packages": {
            name: metadata.version(name)
            for name in ("marimo", "torch", "numpy", "tokenizers", "PyYAML", "matplotlib")
        },
        "cuda_available": torch.cuda.is_available(),
    }
    if hardware["cuda_available"]:
        _gpu = torch.cuda.get_device_properties(0)
        hardware.update(
            gpu=_gpu.name,
            gpu_memory_gib=round(_gpu.total_memory / 2**30, 1),
            compute_capability=f"{_gpu.major}.{_gpu.minor}",
            cuda_runtime=torch.version.cuda,
            bf16_supported=torch.cuda.is_bf16_supported(),
        )
    hardware["container_limits"] = {
        str(_path): _path.read_text().strip()
        for _path in (
            Path("/sys/fs/cgroup/cpu.max"),
            Path("/sys/fs/cgroup/memory.max"),
        )
        if _path.exists()
    }
    hardware
    return (hardware,)


@app.cell(hide_code=True)
def hardware_cards(hardware):
    mo.Html(f"""
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:12px 0">
      <div style="padding:18px;border:1px solid #60a5fa;border-radius:12px">
        <div style="font-size:12px;opacity:.7">GPU memory</div>
        <div style="font-size:28px;font-weight:650">{hardware.get("gpu_memory_gib", 0)} GiB</div>
        <div style="font-size:12px">{hardware.get("gpu", "CPU only")}</div>
      </div>
      <div style="padding:18px;border:1px solid #94a3b8;border-radius:12px">
        <div style="font-size:12px;opacity:.7">Visible CPU / RAM</div>
        <div style="font-size:28px;font-weight:650">{hardware["cpu_cores_visible"]} / {hardware["ram_gib_visible"]} GiB</div>
        <div style="font-size:12px">Container visibility; limits are recorded above.</div>
      </div>
      <div style="padding:18px;border:1px solid #34d399;border-radius:12px">
        <div style="font-size:12px;opacity:.7">Installed runtime</div>
        <div style="font-size:28px;font-weight:650">PyTorch {hardware["packages"]["torch"]}</div>
        <div style="font-size:12px">Versions are recorded, not silently changed.</div>
      </div>
    </div>
    """)
    return


@app.function
def run_checked(command, *, cwd=None, log_path=None, timeout=180):
    """Run a fixed command, keep its full log, and show a short readable tail."""
    result = subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    if log_path is not None:
        Path(log_path).write_text(result.stdout, encoding="utf-8")
    print(result.stdout[-1800:])
    if result.returncode:
        raise RuntimeError(f"Command failed with exit code {result.returncode}")
    return result.stdout


@app.cell
def workspace(hardware):
    LAB_DIR = Path(os.environ.get("ATTENTION_GPU_DIR", str(Path.cwd() / "attention-gpu-lab")))
    INPUTS_DIR = LAB_DIR / "inputs"
    RUNS_DIR = LAB_DIR / "runs"
    REPORTS_DIR = LAB_DIR / "reports"
    SOURCE_COMMIT = "c1849c1b9dd11eec9ed1958c07deee173ca73265"
    REPO_DIR = LAB_DIR / ("source-" + SOURCE_COMMIT[:12])
    REPO_URL = "https://github.com/revantg/era-v5-lab.git"

    for _directory in (LAB_DIR, INPUTS_DIR, RUNS_DIR, REPORTS_DIR):
        _directory.mkdir(parents=True, exist_ok=True)

    if not (REPO_DIR / ".git").exists():
        run_checked(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, REPO_DIR])

    # Preserve tracked source edits; runtime __pycache__ files are harmless untracked outputs.
    if (REPO_DIR / ".git/index").exists():
        if run_checked(["git","-C",REPO_DIR,"status","--porcelain","--untracked-files=no"]).strip():
            raise RuntimeError("Preserve unexpected source edits before changing revisions.")
    run_checked(["git", "-C", REPO_DIR, "checkout", "--detach", SOURCE_COMMIT])

    source_provenance = {
        "repository": REPO_URL,
        "commit": run_checked(["git", "-C", REPO_DIR, "rev-parse", "HEAD"]).strip(),
        "hardware": hardware,
    }
    (REPORTS_DIR / "environment.json").write_text(
        json.dumps(source_provenance, indent=2), encoding="utf-8"
    )
    mo.md(f"Source pinned to **{source_provenance['commit'][:12]}**. Evidence lives in **{LAB_DIR}**.")
    return (
        INPUTS_DIR,
        LAB_DIR,
        REPORTS_DIR,
        REPO_DIR,
        RUNS_DIR,
        SOURCE_COMMIT,
        source_provenance,
    )


@app.cell
def gpu_driver(REPORTS_DIR):
    _driver_result = subprocess.run(
        ["nvidia-smi", "--query-gpu=driver_version,name,memory.total", "--format=csv,noheader"],
        text=True, capture_output=True, check=True,
    )
    gpu_driver_info = {
        "nvidia_smi": _driver_result.stdout.strip(),
        "cuda_runtime": torch.version.cuda,
        "torch_threads_in_notebook": torch.get_num_threads(),
        "child_cpu_threads": 4,
        "deterministic_cublas_workspace": ":4096:8",
    }
    (REPORTS_DIR / "gpu-driver.json").write_text(
        json.dumps(gpu_driver_info, indent=2), encoding="utf-8"
    )
    gpu_driver_info
    return


@app.cell(hide_code=True)
def inputs_intro():
    mo.md(r"""
    ## Inputs: real tokenizer, synthetic text

    The **tokenizer** turns text into token numbers. The trainer checks its exact
    identity, even during a smoke test.

    We rebuild the published course tokenizer from its pinned public source and use
    the course's own tool to create its matching token-to-byte table. We do not
    replace either validator or model code.

    The training sentences below are synthetic English, code, and Hindi examples.
    They exercise the program without claiming to be the official evaluation set.
    """)
    return


@app.function
def sha256_file(path):
    """Fingerprint a file without loading large artifacts into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@app.cell
def tokenizer_assets(INPUTS_DIR, REPORTS_DIR, REPO_DIR):
    BASELINE_TOKENIZER_URL = (
        "https://raw.githubusercontent.com/theschoolofai/BrahmicTokenizer-131K/"
        "7dfcf398172c825c6689ad578e8b484ca5f57bc9/tokenizer.json"
    )
    BASELINE_SHA = "01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff"
    TOKENIZER_SHA = "2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5"
    BASELINE_TOKENIZER = INPUTS_DIR / "baseline_tokenizer.json"
    TOKENIZER_PATH = INPUTS_DIR / "tokenizer_v0.json"
    TABLE_DIR = INPUTS_DIR / "tables"
    BYTE_TABLE_PATH = TABLE_DIR / "raw_table_P32.npz"

    if not BASELINE_TOKENIZER.exists():
        with urlopen(BASELINE_TOKENIZER_URL, timeout=30) as response:
            BASELINE_TOKENIZER.write_bytes(response.read())
    assert sha256_file(BASELINE_TOKENIZER) == BASELINE_SHA

    if not TOKENIZER_PATH.exists():
        run_checked(
            [sys.executable, REPO_DIR / "teams/03-tokenizer/v0/build_v0.py",
             BASELINE_TOKENIZER, TOKENIZER_PATH],
            log_path=REPORTS_DIR / "build_tokenizer.log",
        )
    assert sha256_file(TOKENIZER_PATH) == TOKENIZER_SHA

    if not BYTE_TABLE_PATH.exists():
        run_checked(
            [sys.executable, REPO_DIR / "teams/04-ke2/src/build_tables.py",
             "--tokenizer", TOKENIZER_PATH, "--out", TABLE_DIR, "--pos-dims", "32"],
            log_path=REPORTS_DIR / "build_byte_table.log",
        )
    print("Official tokenizer v0 rebuilt and hash-verified.")
    print("Matching raw-byte table:", BYTE_TABLE_PATH.name)
    return BYTE_TABLE_PATH, TOKENIZER_PATH


@app.cell
def course_imports(BYTE_TABLE_PATH, LAB_DIR, REPO_DIR, TOKENIZER_PATH):
    _loaded = sys.modules.get("week2")
    if _loaded is not None and getattr(_loaded, "__file__", None):
        _loaded_path = Path(_loaded.__file__).resolve()
        _expected = REPO_DIR / "teams/05-architecture/harness"
        if not _loaded_path.is_relative_to(_expected):
            if not _loaded_path.is_relative_to(LAB_DIR):
                raise RuntimeError("An unrelated week2 package is already imported")
            for _module_name in list(sys.modules):
                if _module_name == "week2" or _module_name.startswith("week2.") or _module_name == "train_week2":
                    sys.modules.pop(_module_name)
    HARNESS_DIR = REPO_DIR / "teams/05-architecture/harness"
    if str(HARNESS_DIR) not in sys.path:
        sys.path.insert(0, str(HARNESS_DIR))

    from week2.artifacts import Artifacts
    from week2.config import load_runtime, validate as validate_config

    # This is the real validator: it checks every vocabulary row, not a mock.
    artifacts = Artifacts(TOKENIZER_PATH, BYTE_TABLE_PATH)
    assert artifacts.table_content_sha == (
        "47d411a9c6cae6fa2075935567243e51f4efbc377ccef3eef42c32fce66f869f"
    )
    artifacts.identity()
    return HARNESS_DIR, artifacts, load_runtime, validate_config


@app.cell
def gpu_resume_repair(HARNESS_DIR, REPORTS_DIR, source_provenance):
    sampler_patch_sha = "0bff11279729d373a10d1e43e5830029caac95cf4602d9f41de3f9e3bc0dd862"
    assert sha256_file(HARNESS_DIR / "week2/data.py") == sampler_patch_sha
    source_provenance["execution_features"] = {
        "data_implementation_sha256":sampler_patch_sha,
        "features":["CPU sampler RNG restore","verified numeric window cache"],
        "model_and_optimizer_math_changed":False,
    }
    (REPORTS_DIR / "environment.json").write_text(json.dumps(source_provenance,indent=2))
    mo.callout("Execution source is pinned. The optional window cache and CPU RNG restore "
               "have native/cached/restart equivalence evidence; model mathematics are unchanged.",
               kind="info")

    return (sampler_patch_sha,)


@app.cell
def synthetic_inputs(INPUTS_DIR, REPORTS_DIR, artifacts):
    TRAIN_PATH = INPUTS_DIR / "synthetic_train.jsonl"
    HELDOUT_PATH = INPUTS_DIR / "synthetic_heldout.jsonl"

    train_records = [
        {"id": "synthetic-train-en-1",
         "text": "A blue bird lands beside a quiet river. The water moves slowly. " * 40},
        {"id": "synthetic-train-en-2",
         "text": "We measure small steps carefully and write down what we observe. " * 40},
        {"id": "synthetic-train-code",
         "text": "def add(a, b):\n    return a + b\n\nassert add(2, 3) == 5\n" * 30},
        {"id": "synthetic-train-hi",
         "text": "यह एक छोटा परीक्षण है। हम परिणाम लिखते हैं और फिर उन्हें जाँचते हैं। " * 35},
        ]
    heldout_records = [
        {"id": "synthetic-eval-en", "text": "The green boat rests beside the bridge."},
        {"id": "synthetic-eval-code", "text": "def square(x):\n    return x * x\n"},
        {"id": "synthetic-eval-hi", "text": "आज हम एक नया उदाहरण जाँचते हैं।"},
    ]
    for _path, _records in (
        (TRAIN_PATH, train_records), (HELDOUT_PATH, heldout_records)
    ):
        _path.write_text(
            "".join(json.dumps(_row, ensure_ascii=False) + "\n" for _row in _records),
            encoding="utf-8",
        )

    _train_hashes = {hashlib.sha256(r["text"].encode()).hexdigest() for r in train_records}
    _eval_hashes = {hashlib.sha256(r["text"].encode()).hexdigest() for r in heldout_records}
    assert _train_hashes.isdisjoint(_eval_hashes)

    input_token_counts = [
        {"document": row["id"], "tokens": len(artifacts.encode(row["text"]))}
        for row in train_records + heldout_records
    ]
    assert max(row["tokens"] for row in input_token_counts[:len(train_records)]) > 128

    input_provenance = {
        **artifacts.identity(),
        "train_sha256": sha256_file(TRAIN_PATH),
        "heldout_sha256": sha256_file(HELDOUT_PATH),
        "data_kind": "synthetic smoke text; not official quality evaluation",
        "documents": input_token_counts,
    }
    (REPORTS_DIR / "inputs.json").write_text(
        json.dumps(input_provenance, indent=2), encoding="utf-8"
    )
    mo.ui.table(input_token_counts, selection=None)
    return (HELDOUT_PATH,)


@app.cell
def attention_cases(REPO_DIR, load_runtime, validate_config):
    @dataclass(frozen=True)
    class AttentionCase:
        key: str
        title: str
        config_file: str
        change: str

    ATTENTION_CASES = (
        AttentionCase("attn-0", "Reference", "t2.yaml", "Existing global attention"),
        AttentionCase("attn-1", "More key/value sharing", "attn1_mqa.yaml", "One KV head"),
        AttentionCase("attn-2", "Recent text + learned sink", "attn2_swa128_sink.yaml", "128-token local windows"),
        AttentionCase("attn-3", "Partial position rotation", "attn3_prope_half.yaml", "Rotate half of each head"),
        AttentionCase("attn-4", "Learned output gate", "attn4_gate.yaml", "Gate the attention output"),
    )

    ARM_DIR = REPO_DIR / "teams/05-architecture/configs/arms"
    arm_configurations = {}
    for _case in ATTENTION_CASES:
        _configuration = load_runtime(ARM_DIR / _case.config_file)
        _errors = validate_config(_configuration)
        assert not _errors, (_case.key, _errors)
        arm_configurations[_case.key] = _configuration

    mo.ui.table([
        {
            "design": case.key,
            "plain-language label": case.title,
            "change": case.change,
            "layers": arm_configurations[case.key]["model"]["n_layer"],
            "width": arm_configurations[case.key]["model"]["n_embd"],
            "official context": arm_configurations[case.key]["model"]["block_size"],
        }
        for case in ATTENTION_CASES
    ], selection=None)
    return ARM_DIR, ATTENTION_CASES, arm_configurations


@app.cell
def attention_map(ATTENTION_CASES):
    _patterns = {
        "attn-0": "GGGGGGGG", "attn-1": "GGGGGGGG",
        "attn-2": "LLLGLLLG", "attn-3": "GGGGGGGG", "attn-4": "GGGGGGGG",
    }
    _map_rows = []
    for _case in ATTENTION_CASES:
        _layers = "".join(
            f'<span title="Layer {_index + 1}: '
            f'{"global attention" if _kind == "G" else "recent 128 tokens + learned sink"}" '
            f'style="display:inline-flex;width:30px;height:30px;align-items:center;'
            f'justify-content:center;border-radius:6px;background:'
            f'{"#dbeafe" if _kind == "G" else "#ccfbf1"};color:#0f172a;font-size:12px">'
            f'{_kind}</span>'
            for _index, _kind in enumerate(_patterns[_case.key])
        )
        _map_rows.append(
            f'<div style="display:grid;grid-template-columns:200px 1fr;gap:14px;'
            f'align-items:center;margin:8px 0">'
            f'<div style="font-size:13px"><strong>{_case.key}</strong> · {_case.title}</div>'
            f'<div style="display:flex;gap:5px">{_layers}</div></div>'
        )
    mo.Html(
        '<div style="padding:18px;border:1px solid #94a3b8;border-radius:12px">'
        '<div style="font-weight:650;margin-bottom:12px">One eight-layer recipe, five attention choices</div>'
        + "".join(_map_rows)
        + '<div style="font-size:12px;opacity:.8;margin-top:12px">'
        'G = can attend to earlier text across the context. '
        'L = only the recent 128 tokens, with a learned sink. '
        'The other rows change sharing, position features, or gating while keeping global layers.'
        '</div></div>'
    )
    return


@app.cell
def single_seed_plan(ATTENTION_CASES):
    SCREEN_SEED = 1235
    SCREEN_LR = 0.001
    QUALITY_STEPS = 1221
    DIAGNOSTIC_STEPS = 8

    previous_seed_scores = [
        {"learning rate": rate, "seed 1234": a, "seed 1235": b, "seed 1236": c}
        for rate, a, b, c in (
            (0.0001, 2.3730, 2.3653, 2.3862),
            (0.0003, 2.1357, 2.1214, 2.1642),
            (0.001, 1.9757, 1.9617, 1.9684),
            (0.003, 2.1000, 2.0377, 2.0935),
            (0.01, 2.3222, 2.1969, 2.3417),
        )
    ]
    mo.vstack([
        mo.md("""
        ## One seed, five fresh starts

        Seed **1235** had the lowest reported evaluation error at every learning rate
        in [the previous small-model experiment](https://github.com/theschoolofai/era-v5-lab/pull/310#issuecomment-6702949196).
        We fix that seed **before** running the five attention designs. This is a
        single-seed screen, not a search for each design's luckiest run.

        The requested real-data screen is **1,221 updates per design**, context 2,048,
        global batch 8 and microbatch 1. Learning rate **0.001** remains the proposed
        common value until the lead confirms it. The course's final three-seed
        comparison is separate; this notebook does not revise the submitted request.
        """),
        mo.ui.table(previous_seed_scores, selection=None),
        mo.ui.table([
            {"design": case.key, "description": case.title,
             "seed": SCREEN_SEED, "requested steps": QUALITY_STEPS,
             "context": 2048, "global batch": 8, "microbatch": 1}
            for case in ATTENTION_CASES
        ], selection=None),
    ])
    return DIAGNOSTIC_STEPS, QUALITY_STEPS, SCREEN_LR, SCREEN_SEED


@app.cell(hide_code=True)
def execution_diagram(REPORTS_DIR, gpu_refresh):
    gpu_refresh.value
    _path = REPORTS_DIR / "screen-comparison.json"
    _done = len(json.loads(_path.read_text())) if _path.exists() else 0
    mo.vstack([
        mo.md("## From a launch check to comparison evidence"),
        mo.mermaid("""
        flowchart LR
            A[Pinned source and verified GPU] --> B[Tokenizer and exact byte table]
            B --> C[Synthetic checks and faithful restart]
            B --> D[Protected real text]
            D --> E[Verified ordered window cache]
            E --> F[Five designs with bounded overlap]
            F --> G[Measured scores and limitations]
            G --> H[Three-seed final comparison when approved]
            classDef ready fill:#e7f5ee,stroke:#198754,color:#123c2b;
            classDef pending fill:#fff4da,stroke:#cc8b00,color:#634600;
            class A,B,C,D,E ready;
            class H pending;
        """),
        mo.md(f"**{_done}/5 designs complete.** Up to three isolated trainers share spare GPU capacity. "
              "One seed provides no run-to-run spread."),
    ])
    return


@app.cell
def long_synthetic_inputs(INPUTS_DIR, artifacts):
    LONG_TRAIN_PATH = INPUTS_DIR / "synthetic_long_train.jsonl"
    _sentences = (
        "A blue bird follows a quiet river. We record each observation carefully. ",
        "def square(value):\n    return value * value\n\nassert square(3) == 9\n",
        "यह एक कृत्रिम परीक्षण है। हम हर चरण का परिणाम ध्यान से लिखते हैं। ",
    )
    long_input_counts = []
    with LONG_TRAIN_PATH.open("w", encoding="utf-8") as _stream:
        for _index in range(8):
            _text = _sentences[_index % len(_sentences)] * 320
            _tokens = len(artifacts.encode(_text))
            assert _tokens > 2048
            _stream.write(json.dumps({"id": f"synthetic-long-{_index}", "text": _text},
                                     ensure_ascii=False) + "\n")
            long_input_counts.append({"synthetic document": _index, "tokens": _tokens})
    mo.vstack([
        mo.md("## Full-size execution fixtures\n\nThese longer **synthetic** documents "
              "fill 2,048-token windows. They test memory and execution; their scores "
              "must not rank the attention designs."),
        mo.ui.table(long_input_counts, selection=None),
    ])
    return (LONG_TRAIN_PATH,)


@app.cell
def execution_helpers(
    ARM_DIR,
    BYTE_TABLE_PATH,
    DIAGNOSTIC_STEPS,
    HARNESS_DIR,
    HELDOUT_PATH,
    LONG_TRAIN_PATH,
    REPORTS_DIR,
    REPO_DIR,
    RUNS_DIR,
    SCREEN_LR,
    SCREEN_SEED,
    SOURCE_COMMIT,
    TOKENIZER_PATH,
    arm_configurations,
    load_runtime,
):
    def training_rows(output):
        path = Path(output) / "metrics.jsonl"
        if not path.exists():
            return []
        return [row for line in path.read_text().splitlines() if line.strip()
                if "train/ce_loss" in (row := json.loads(line))]


    def child_environment():
        return {**os.environ, "PYTHONPATH": str(HARNESS_DIR),
                "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4",
                "CUBLAS_WORKSPACE_CONFIG": ":4096:8", "PYTHONUNBUFFERED": "1"}


    def trainer_command(case, output, *, steps=DIAGNOSTIC_STEPS,
                        checkpoint=False, stop_after=None, resume=None):
        """Use supported development flags; preserve the complete model/batch shape."""
        command = [
            sys.executable, str(HARNESS_DIR / "train_week2.py"),
            "--config", str(ARM_DIR / case.config_file),
            "--tokenizer", str(TOKENIZER_PATH), "--byte-table", str(BYTE_TABLE_PATH),
            "--train-data", str(LONG_TRAIN_PATH), "--heldout-data", str(HELDOUT_PATH),
            "--device", "cuda", "--seed", str(SCREEN_SEED), "--lr", str(SCREEN_LR),
            "--smoke", "--smoke-steps", str(steps), "--out", str(output),
        ]
        if not checkpoint:
            command.append("--no-checkpoint")
        if stop_after is not None:
            command.extend(["--stop-after", str(stop_after)])
        if resume is not None:
            command.extend(["--resume", str(resume)])
        return command


    def run_recorded(command, output, *, timeout=600, cache_dir=None):
        """Reuse matching complete evidence; preserve any incomplete or changed run."""
        output = Path(output)
        receipt_path = REPORTS_DIR / f"{output.name}-command.json"
        receipt = {
            "command": command, "source_commit": SOURCE_COMMIT,
            "torch": torch.__version__, "tokenizer_sha256": sha256_file(TOKENIZER_PATH),
            "byte_table_sha256": sha256_file(BYTE_TABLE_PATH),
            "train_sha256": sha256_file(LONG_TRAIN_PATH),
            "heldout_sha256": sha256_file(HELDOUT_PATH),
            "document_cache_dir": str(cache_dir) if cache_dir is not None else None,
        }
        if output.exists() and any(output.iterdir()):
            required = (output / "summary.json", output / "manifest.json", receipt_path)
            if not all(path.exists() for path in required):
                raise FileExistsError(f"Preserve incomplete evidence; choose a fresh workspace: {output}")
            previous = json.loads(receipt_path.read_text())
            summary = json.loads((output / "summary.json").read_text())
            manifest = json.loads((output / "manifest.json").read_text())
            identity_fields = ("torch", "tokenizer_sha256", "byte_table_sha256",
                               "train_sha256", "heldout_sha256", "document_cache_dir")
            assert all(previous.get(key) == receipt[key] for key in identity_fields), \
                "Execution inputs changed; preserve this evidence and use a fresh workspace."
            source_files = [HARNESS_DIR / "train_week2.py",
                            *sorted((HARNESS_DIR / "week2").glob("*.py"))]
            assert manifest["sources"] == {path.name:sha256_file(path) for path in source_files}, \
                "Execution source changed; use a fresh workspace."

            def argument(arguments, flag, default=None):
                return arguments[arguments.index(flag)+1] if flag in arguments else default

            expected = load_runtime(argument(command,"--config"))
            expected["run"]["seed"] = int(argument(command,"--seed"))
            expected["run"]["steps"] = int(argument(command,"--smoke-steps"))
            expected["optim"]["lr"] = float(argument(command,"--lr"))
            assert manifest["config"] == expected
            for flag in ("--stop-after", "--resume"):
                assert argument(previous["command"],flag) == argument(command,flag)
            assert ("--no-checkpoint" in previous["command"]) == ("--no-checkpoint" in command)
            steps = min(expected["run"]["steps"],
                        int(argument(command,"--stop-after",expected["run"]["steps"])))
            rows = training_rows(output)
            assert summary["steps"] == steps and len(rows) == steps and not summary["timed_out"]
            assert manifest["smoke"] and not summary["eligible_for_quality_comparison"]
            assert all(math.isfinite(row[key]) for row in rows
                       for key in ("train/ce_loss", "gradient_norm", "perf/step_ms"))
            if "--no-checkpoint" not in command:
                assert (output / "checkpoint.pt").exists()
            return summary

        if receipt_path.exists():
            raise FileExistsError("A prior attempt has a command receipt; choose a fresh workspace.")
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding="utf-8")
        started = time.monotonic()
        environment = {**child_environment(),
                       **({"G5_DOCUMENT_CACHE_DIR":str(cache_dir)} if cache_dir is not None else {})}
        with (REPORTS_DIR / f"{output.name}.log").open("w") as log:
            subprocess.run(command,cwd=REPO_DIR,env=environment,stdout=log,
                           stderr=subprocess.STDOUT,check=True,timeout=timeout)
        receipt["observed_process_wall_seconds"] = time.monotonic()-started
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding="utf-8")
        return json.loads((output / "summary.json").read_text())


    def run_diagnostic(case):
        output = RUNS_DIR / f"{case.key}-gpu-seed{SCREEN_SEED}-full-shape"
        summary = run_recorded(trainer_command(case, output), output)
        manifest = json.loads((output / "manifest.json").read_text())
        rows = training_rows(output)
        cfg = manifest["config"]
        assert cfg["model"] == arm_configurations[case.key]["model"]
        assert cfg["run"]["batch_size"] == 8 and cfg["run"]["micro_batch_size"] == 1
        assert cfg["run"]["seed"] == SCREEN_SEED
        assert len(rows) == DIAGNOSTIC_STEPS and summary["steps"] == DIAGNOSTIC_STEPS
        assert manifest["smoke"] and not summary["eligible_for_quality_comparison"]
        assert all(math.isfinite(row[key]) for row in rows
                   for key in ("train/ce_loss", "gradient_norm", "perf/step_ms"))
        assert all(row["train/input_positions"] == 8 * 2048 for row in rows)
        return {"design": case.key, "seed": SCREEN_SEED, "steps": summary["steps"],
                "first loss": rows[0]["train/ce_loss"], "last loss": rows[-1]["train/ce_loss"],
                "median step seconds": statistics.median(row["perf/step_ms"] for row in rows)/1000,
                "quality result": False, "status": "passed"}


    def run_existing_verification():
        command = [sys.executable, "-m", "unittest", "discover",
                   "-s", str(REPO_DIR / "teams/05-architecture/tests"),
                   "-p", "test_week2*.py", "-v"]
        with (REPORTS_DIR / "unit-tests.log").open("w") as log:
            subprocess.run(command,cwd=REPO_DIR,env=child_environment(),
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        return "Existing tests passed"


    return (
        child_environment,
        run_diagnostic,
        run_existing_verification,
        run_recorded,
        trainer_command,
        training_rows,
    )


@app.cell(hide_code=True)
def checkpoint_explanation():
    mo.md("""
    ## Can a stopped GPU job continue faithfully?

    A **checkpoint** saves weights, optimizer state and random-number state. We test
    the reference design three ways: **six steps continuously**, **three steps then
    save**, and **resume that saved state to step six**. The final weights and every
    training loss must match exactly. Checkpoints stay in the workspace and are
    excluded from evidence downloads.
    """)
    return


@app.cell
def checkpoint_verification(
    ATTENTION_CASES,
    HARNESS_DIR,
    REPORTS_DIR,
    RUNS_DIR,
    SCREEN_SEED,
    run_recorded,
    sampler_patch_sha,
    trainer_command,
):
    def run_checkpoint_verification():
        assert sha256_file(HARNESS_DIR / "week2/data.py") == sampler_patch_sha
        case = ATTENTION_CASES[0]
        continuous = RUNS_DIR / f"restart-fixed-continuous-seed{SCREEN_SEED}"
        interrupted = RUNS_DIR / f"restart-fixed-interrupted-seed{SCREEN_SEED}"
        resumed = RUNS_DIR / f"restart-fixed-resumed-seed{SCREEN_SEED}"
        start = time.monotonic()
        full = run_recorded(trainer_command(case, continuous, steps=6, checkpoint=True), continuous)
        partial = run_recorded(trainer_command(case, interrupted, steps=6,
                                              checkpoint=True, stop_after=3), interrupted)
        restored = run_recorded(trainer_command(case, resumed, steps=6, checkpoint=True,
                                               resume=interrupted / "checkpoint.pt"), resumed)
        assert partial["steps"] == 3 and full["steps"] == restored["steps"] == 6
        assert full["final_model_sha256"] == restored["final_model_sha256"]
        assert (continuous / "losses.txt").read_bytes() == (resumed / "losses.txt").read_bytes()
        assert (continuous / "total_losses.txt").read_bytes() == (resumed / "total_losses.txt").read_bytes()
        assert all(not item["eligible_for_quality_comparison"] for item in (full, partial, restored))
        result = {"status": "passed", "seed": SCREEN_SEED, "split_step": 3,
                  "final_step": 6, "losses_byte_identical": True,
                  "final_model_sha256": full["final_model_sha256"],
                  "checkpoint_sizes_bytes": {p.parent.name:p.stat().st_size
                      for p in (continuous / "checkpoint.pt", interrupted / "checkpoint.pt",
                                resumed / "checkpoint.pt")},
                  "process_wall_seconds": time.monotonic() - start,
                  "quality_result": False}
        (REPORTS_DIR / "checkpoint-verification.json").write_text(json.dumps(result, indent=2))
        return result

    return (run_checkpoint_verification,)


@app.cell
def restart_repair_control():
    restart_button = mo.ui.run_button(label='Verify repaired GPU checkpoint resume')
    restart_button
    return (restart_button,)


@app.cell
def restart_repair_queue(
    job_registry,
    restart_button,
    run_checkpoint_verification,
):
    restart_executor = None
    if restart_button.value and not (job_registry.get("restart") and not job_registry["restart"].done()):
        restart_executor = ThreadPoolExecutor(max_workers=1)
        job_registry["restart"] = restart_executor.submit(run_checkpoint_verification)
    restart_future = job_registry.get("restart")
    mo.md("Restart verification status is shown below.")

    return


@app.cell
def gpu_run_controls():
    run_gpu_checks = mo.ui.run_button(label="Run GPU execution and restart checks")
    mo.vstack([
        mo.md("**Explicit execution:** queues existing verification, then the five "
              "GPU designs, then one reference restart test. Jobs run sequentially. "
              "This button never starts the pending real-data comparison."),
        run_gpu_checks,
    ])
    return (run_gpu_checks,)


@app.cell
def gpu_execution_queue(
    ATTENTION_CASES,
    run_checkpoint_verification,
    run_diagnostic,
    run_existing_verification,
    run_gpu_checks,
):
    gpu_jobs = {}
    gpu_executor = None
    if run_gpu_checks.value:
        gpu_executor = ThreadPoolExecutor(max_workers=1)
        gpu_jobs["existing tests"] = gpu_executor.submit(run_existing_verification)
        for _case in ATTENTION_CASES:
            gpu_jobs[_case.key] = gpu_executor.submit(run_diagnostic, _case)
        gpu_jobs["checkpoint restart"] = gpu_executor.submit(run_checkpoint_verification)
    mo.md("GPU queue is idle." if not gpu_jobs else "GPU checks are queued. Refresh below to follow progress.")
    return


@app.cell
def gpu_results_refresh():
    gpu_refresh = mo.ui.refresh(options=["10s", "30s", "1m"], default_interval="30s", label="Refresh progress")
    gpu_refresh
    return (gpu_refresh,)


@app.cell
def gpu_results(REPORTS_DIR, gpu_refresh):
    gpu_refresh.value
    gpu_status_rows = []
    _unit_log = REPORTS_DIR / 'cache-harness-tests.log'
    if _unit_log.exists():
        gpu_status_rows.append({'check':'Existing verification suite','status':'passed' if '\nOK' in _unit_log.read_text() else 'inspect log','detail':'113 current-harness tests'})
    _saved = REPORTS_DIR / 'gpu-diagnostic-results.json'
    if _saved.exists():
        for _row in json.loads(_saved.read_text()):
            gpu_status_rows.append({'check':_row['design'], 'status':_row['status'], 'detail':f"{_row['steps']} GPU steps; seed {_row['seed']}; loss {_row['first loss']:.3f} → {_row['last loss']:.3f}"})
    _restart = REPORTS_DIR / 'checkpoint-verification.json'
    if _restart.exists():
        _receipt = json.loads(_restart.read_text())
        gpu_status_rows.append({'check':'Repaired checkpoint resume','status':_receipt['status'],'detail':'Continuous and resumed losses / final weights match exactly'})
    mo.ui.table(gpu_status_rows, selection=None)

    return


@app.cell
def gpu_diagnostic_plots(
    ATTENTION_CASES,
    REPORTS_DIR,
    RUNS_DIR,
    SCREEN_SEED,
    gpu_refresh,
    training_rows,
):
    gpu_refresh.value
    gpu_diagnostic_figure, _axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for _case in ATTENTION_CASES:
        _rows = training_rows(RUNS_DIR / f"{_case.key}-gpu-seed{SCREEN_SEED}-full-shape")
        if _rows:
            _axes[0].plot([r["step"] for r in _rows], [r["train/ce_loss"] for r in _rows],
                          marker="o", markersize=3, label=_case.key)
            _axes[1].plot([r["step"] for r in _rows], [r["perf/step_ms"]/1000 for r in _rows],
                          marker="o", markersize=3, label=_case.key)
    for _axis in _axes:
        _axis.set_xlabel("Training update")
        _axis.grid(alpha=0.2)
    _axes[0].set_ylabel("Training cross-entropy loss")
    _axes[1].set_ylabel("Trainer step time (seconds)")
    _axes[0].legend(fontsize=8)
    gpu_diagnostic_figure.suptitle(f"Synthetic full-size GPU checks · seed {SCREEN_SEED} · not quality results")
    gpu_diagnostic_figure.savefig(REPORTS_DIR / "gpu-diagnostic-losses.png", dpi=170)
    gpu_diagnostic_figure
    return


@app.cell(hide_code=True)
def real_data_explanation():
    mo.md("""
    ## Real-data screen: a reproducible preparation route

    The original job's staged JSONL files are not published. The course does publish
    **48 cleaned training Parquets across 38 packs** and a permanent G5 held-out set
    with all 15 evaluation slices. We can use these sources for a clearly identified
    new screen; we do not claim byte-for-byte equivalence with job #310.

    1. Download only **TRAIN** parts and verify each official file checksum.
    2. Run the existing **full G9 v2 fingerprint check**, including G5 hold-out protection.
    3. Remove flagged documents and exact hold-out duplicates; keep every other document.
    4. Preserve document IDs and text in deterministic manifest order. No new mixture
       weights or arbitrary subset are introduced.
    5. Check the permanent held-out set against all other v2 fingerprints, and scan canaries.

    The cleaned sample's own held-out split lacks Punjabi and Assamese, so we use the
    published permanent **1,059-document / 15-slice G5 held-out set** instead. This
    choice and all resulting hashes are recorded. Approval remains **pending**:
    the requested one-seed run is explicitly a **preliminary development screen**.
    """)
    return


@app.cell
def data_preparation_helpers(
    INPUTS_DIR,
    REPORTS_DIR,
    REPO_DIR,
    SCREEN_SEED,
    SOURCE_COMMIT,
):
    def write_json_file(path, value):
        path = Path(path)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
        temporary.replace(path)


    def prepare_real_data():
        """Reconstruct a declared screen dataset from checked course TRAIN sources."""
        import re
        import urllib.parse
        import pyarrow.parquet as parquet

        target = INPUTS_DIR / "preliminary"
        cache = INPUTS_DIR / "cleaned-train"
        target.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)
        cached_path = target / "provenance.json"
        if cached_path.exists():
            cached = json.loads(cached_path.read_text())
            if cached["source_commit"] != SOURCE_COMMIT:
                _changed = subprocess.check_output(["git","-C",str(REPO_DIR),"diff","--name-only",cached["source_commit"],SOURCE_COMMIT,"--","teams/09-evaluation"],text=True)
                assert not _changed.strip(), "Protection code changed; prepare and verify inputs again"
            assert cached["manifest_sha256"] == sha256_file(target / "cleaned_manifest.json")
            assert cached["train_sha256"] == sha256_file(target / "train.jsonl")
            assert cached["heldout_sha256"] == sha256_file(target / "heldout.jsonl")
            assert cached["source_sidecar_sha256"] == sha256_file(target / "heldout_sources.jsonl")
            current_set = REPO_DIR / "teams/09-evaluation/fingerprints/v2/SHA256SUMS"
            assert cached["fingerprint_set_id"] == sha256_file(current_set)
            return cached
        progress_path = REPORTS_DIR / "data-progress.json"
        progress = {"stage": "discovering public course sources", "downloaded": 0,
                    "parts": 48, "checked": 0, "converted": 0}
        write_json_file(progress_path, progress)

        widget_url = "https://axiom.theschoolofai.in/widgets/cap_plan_sheet.html"
        with urlopen(widget_url, timeout=60) as response:
            page = response.read().decode("utf-8")
        marker = re.search(r"\bconst\s+DATA\s*=\s*", page)
        if marker is None:
            raise ValueError("The published course data index changed shape")
        course = json.JSONDecoder().raw_decode(page, marker.end())[0]["tokclean"]
        approved_host = "theschoolofai-lab-llm-data-006547668672.s3.amazonaws.com"

        def fetch_file(url, destination, expected_sha=None):
            # Signed URLs are consumed in memory, never printed or saved in evidence.
            parts = urllib.parse.urlsplit(url)
            if parts.scheme != "https" or parts.hostname != approved_host:
                raise ValueError("Unexpected course storage destination")
            destination = Path(destination)
            if destination.exists() and expected_sha and sha256_file(destination) == expected_sha:
                return destination
            temporary = destination.with_suffix(destination.suffix + ".part")
            try:
                with urlopen(url, timeout=120) as response, temporary.open("wb") as stream:
                    if urllib.parse.urlsplit(response.geturl()).hostname != approved_host:
                        raise ValueError("Unexpected storage redirect")
                    shutil.copyfileobj(response, stream, length=1024 * 1024)
            except Exception as error:
                raise RuntimeError(f"Download failed for {destination.name}: {type(error).__name__}") from None
            if expected_sha and sha256_file(temporary) != expected_sha:
                raise ValueError(f"Checksum mismatch for {destination.name}")
            temporary.replace(destination)
            return destination

        metadata = {entry["name"]: entry["url"] for entry in course["meta"]}
        manifest_path = fetch_file(metadata["cleaned_manifest.json"], target / "cleaned_manifest.json",
            "7e5b04a3a2cdc3fac673dad2f0610e2b9f430c4986f81bec46d993939dcf7f04")
        manifest = json.loads(manifest_path.read_text())
        urls = {
            f"train/{pack['pack']}/part-{index:05d}.parquet": url
            for pack in course["packs"] for index, url in enumerate(pack["train"])
        }
        training_parts = sorted((part for part in manifest["parts"] if part["split"] == "train"),
                                key=lambda part: part["part"])
        assert len(training_parts) == 48 and len({p["pack_id"] for p in training_parts}) == 38

        def download_part(part):
            name = part["part"].replace("/", "__")
            return fetch_file(urls[part["part"]], cache / name, part["output_sha256"])

        progress["stage"] = "downloading and verifying all 48 TRAIN parts"
        write_json_file(progress_path, progress)
        part_paths = {}
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(download_part, part): part for part in training_parts}
            from concurrent.futures import as_completed
            for future in as_completed(futures):
                part = futures[future]
                part_paths[part["part"]] = future.result()
                progress["downloaded"] += 1
                write_json_file(progress_path, progress)

        decontam = REPO_DIR / "teams/09-evaluation/decontam"
        g9_environment = {**os.environ, "PYTHONPATH": str(decontam),
                          "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        fingerprints = REPO_DIR / "teams/09-evaluation/fingerprints/v2"
        actual_fp_sha = sha256_file(fingerprints / "SHA256SUMS")
        assert actual_fp_sha == "2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a"
        audit = REPORTS_DIR / "data-audit"
        audit.mkdir(exist_ok=True)

        def check_part(part):
            path = part_paths[part["part"]]
            key = path.stem
            flags = audit / f"{key}-flags.jsonl"
            log_path = audit / f"{key}-check.log"
            command = [sys.executable, str(decontam / "decontam_check.py"), str(path)]
            with flags.open("w") as output, log_path.open("w") as log:
                subprocess.run(command, cwd=REPO_DIR, env=g9_environment, stdout=output, stderr=log,
                               check=True, timeout=14400)
            text = log_path.read_text()
            match = re.search(r"docs (\d+) flagged (\d+)", text)
            if not match or int(match[1]) != part["output_rows"]:
                raise ValueError(f"Incomplete fingerprint scan: {part['part']}")
            if "(full set)" not in text or actual_fp_sha not in text:
                raise ValueError("A partial fingerprint scan cannot prepare this training input")
            return flags

        progress["stage"] = "full G9 v2 protection checks (8 CPU workers)"
        write_json_file(progress_path, progress)
        flag_paths = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(check_part, part): part for part in training_parts}
            for future in as_completed(futures):
                part = futures[future]
                flag_paths[part["part"]] = future.result()
                progress["checked"] += 1
                write_json_file(progress_path, progress)

        frozen = REPO_DIR / "teams/05-architecture/heldout_v1"
        heldout = target / "heldout.jsonl"
        sources = target / "heldout_sources.jsonl"
        shutil.copyfile(frozen / "data/heldout_v1.jsonl", heldout)
        shutil.copyfile(frozen / "data/heldout_v1_sources.jsonl", sources)
        heldout_sha = sha256_file(heldout)
        assert heldout_sha == "21c6e4b2df8dae9d69e254f4a00fc934d2a3c70f0675065a03724299d94312bb"
        heldout_hashes = {hashlib.sha256(json.loads(line)["text"].encode()).hexdigest()
                          for line in heldout.read_text().splitlines() if line.strip()}

        progress["stage"] = "serializing verified retained documents without changing text"
        write_json_file(progress_path, progress)
        train = target / "train.jsonl"
        seen_ids = set()
        counters = {"source_documents": 0, "retained_documents": 0,
                    "fingerprint_flagged_removed": 0, "exact_heldout_duplicates_removed": 0,
                    "empty_documents_removed": 0, "retained_utf8_bytes": 0}
        per_pack = {}
        with train.open("w", encoding="utf-8") as output:
            for part in training_parts:
                flagged = {str(json.loads(line)["doc_id"]) for line in
                           flag_paths[part["part"]].read_text().splitlines() if line.strip()}
                pqfile = parquet.ParquetFile(part_paths[part["part"]])
                for batch in pqfile.iter_batches(batch_size=512, columns=["doc_id", "text"]):
                    for record in batch.to_pylist():
                        counters["source_documents"] += 1
                        identity, text = str(record["doc_id"]), record["text"] or ""
                        if identity in flagged:
                            counters["fingerprint_flagged_removed"] += 1
                            continue
                        if not text:
                            counters["empty_documents_removed"] += 1
                            continue
                        if hashlib.sha256(text.encode()).hexdigest() in heldout_hashes:
                            counters["exact_heldout_duplicates_removed"] += 1
                            continue
                        if identity in seen_ids:
                            raise ValueError("Duplicate retained document ID; preserve and investigate")
                        seen_ids.add(identity)
                        output.write(json.dumps({"id": identity, "text": text},
                                                ensure_ascii=False, separators=(",", ":")) + "\n")
                        counters["retained_documents"] += 1
                        counters["retained_utf8_bytes"] += len(text.encode())
                        per_pack[part["pack_id"]] = per_pack.get(part["pack_id"], 0) + 1
                progress["converted"] += 1
                progress["retained_documents"] = counters["retained_documents"]
                write_json_file(progress_path, progress)
        assert counters["source_documents"] == 1402081 and len(per_pack) == 38

        progress["stage"] = "checking the permanent heldout and final training canaries"
        write_json_file(progress_path, progress)
        heldout_flags = audit / "heldout-v2-flags.jsonl"
        heldout_log = audit / "heldout-v2-check.log"
        with heldout_flags.open("w") as output, heldout_log.open("w") as log:
            subprocess.run([sys.executable, str(decontam / "decontam_check.py"), str(heldout),
                            "--id-field", "id", "--exclude", "heldout_g5_v1"],
                           cwd=REPO_DIR, env=g9_environment, stdout=output, stderr=log, check=True, timeout=900)
        assert not heldout_flags.read_text().strip()
        assert "docs 1059 flagged 0" in heldout_log.read_text()
        for label, path in (("train", train), ("heldout", heldout)):
            with (audit / f"{label}-canary-flags.jsonl").open("w") as output,              (audit / f"{label}-canary.log").open("w") as log:
                subprocess.run([sys.executable, str(decontam / "canary_scan.py"), str(path),
                                "--id-field", "id"], cwd=REPO_DIR, env=g9_environment,
                               stdout=output, stderr=log, check=True, timeout=1800)

        (target / "heldout.sha256").write_text(f"{heldout_sha}  heldout.jsonl\n")
        report = {"heldout_sha256": heldout_sha, "matches": 0, "docs_checked": 1059,
                  "scope": "full", "fingerprint_set_id": actual_fp_sha,
                  "scope_detail": "Full applicable v2 set, excluding only the heldout's protected self entry",
                  "excluded_protected_self": ["heldout_g5_v1"],
                  "canary_hits": 0, "source_commit": SOURCE_COMMIT}
        write_json_file(target / "heldout_report.json", report)
        provenance = {"kind": "provisional reconstructed real-data screen; not job310 equivalence",
            "source_commit": SOURCE_COMMIT, "manifest_sha256": sha256_file(manifest_path),
            "train_sha256": sha256_file(train), "heldout_sha256": heldout_sha,
            "source_sidecar_sha256": sha256_file(sources), "fingerprint_set_id": actual_fp_sha,
            "train_parts": 48, "packs": 38, "counters": counters, "retained_by_pack": per_pack,
            "selection": "All 48 TRAIN parts, sorted manifest path then original row order; no subset or reweighting",
            "training_check": "Every source document checked against full v2; flagged IDs and exact heldout copies removed; retained text unchanged",
            "canary_hits": 0, "approval": "pending", "seed": SCREEN_SEED,
            "serialization": "UTF-8 JSONL id/text, ensure_ascii=False, compact separators"}
        write_json_file(target / "provenance.json", provenance)
        progress.update(stage="ready for the preliminary screen", complete=True, **counters)
        write_json_file(progress_path, progress)
        return provenance

    return prepare_real_data, write_json_file


@app.cell
def prepare_data_control():
    prepare_data_button = mo.ui.run_button(label="Prepare all published TRAIN parts and verify protection checks")
    mo.vstack([
        mo.md("**Data preparation:** downloads about 1.74 GiB and runs CPU checks. "
              "It never downloads evaluation benchmark text or publishes dataset files."),
        prepare_data_button,
    ])
    return (prepare_data_button,)


@app.cell
def data_preparation_queue(
    job_registry,
    prepare_data_button,
    prepare_real_data,
):
    data_executor = None
    if prepare_data_button.value and not (job_registry.get("data") and not job_registry["data"].done()):
        data_executor = ThreadPoolExecutor(max_workers=1)
        job_registry["data"] = data_executor.submit(prepare_real_data)
    data_future = job_registry.get("data")
    mo.md("Data preparation status is shown below.")

    return (data_future,)


@app.cell(hide_code=True)
def data_readiness(INPUTS_DIR, REPORTS_DIR, data_future, gpu_refresh):
    gpu_refresh.value
    _progress_path = REPORTS_DIR / "data-progress.json"
    data_progress = json.loads(_progress_path.read_text()) if _progress_path.exists() else {"stage":"not started"}
    screen_inputs_ready = (INPUTS_DIR / "preliminary/provenance.json").exists()
    _error = str(data_future.exception()) if data_future is not None and data_future.done() and data_future.exception() else None
    mo.vstack([
        mo.md("## Data readiness\n\n" + data_progress["stage"]),
        mo.hstack([
            mo.stat(label="Files verified",value=f"{data_progress.get('downloaded',0)} / 48"),
            mo.stat(label="Full protection checks",value=f"{data_progress.get('checked',0)} / 48"),
            mo.stat(label="Training documents retained",value=f"{data_progress.get('retained_documents',0):,}"),
        ],justify="space-between"),
        mo.callout(_error,kind="danger") if _error else mo.callout(
            "The reconstructed input bundle is ready. This remains a preliminary screen; approval is pending."
            if screen_inputs_ready else "Real-data runs wait for verified preparation.",
            kind="info"),
    ])

    return


@app.cell(hide_code=True)
def screen_explanation():
    mo.md("""
    ## The five real-data runs

    This screen trains every design for **1,221 updates**, using **seed 1235**,
    context **2,048**, global batch **8**, microbatch **1**, native **bf16** and
    AdamW learning rate **0.001**. Each run starts fresh on the same prepared data.

    The run is explicitly **provisional**: it uses the supported development flag
    with the full step budget, not a reduced model or shorter context. Checkpoints
    remain enabled. Every trainer manifest therefore says `smoke=true`, and every
    summary remains **ineligible for the course's final quality comparison**.

    We will report the actual evaluation scores and their differences from the
    reference, but will not invent seed ranges or declare a three-seed winner.
    """)
    return


@app.cell
def window_cache_explanation():
    mo.md("""
    ## Prepare text once, reuse the same windows

    A **tokenizer** converts text into numbered pieces; a **window** is the sequence
    of those pieces used by the model. The optional **cache** stores exactly the same
    ordered windows in numeric files. A read-only memory map loads only needed pages.

    This avoids repeated CPU tokenization and large Python lists. Checksums bind the
    cache to its input, tokenizer, byte table and window settings. Damaged or
    incompatible files cause an error. Uncached, cached and resumed GPU checks gave
    byte-identical losses and identical weights; **113 harness tests passed**.
    """)
    return


@app.cell
def window_cache_helpers(
    BYTE_TABLE_PATH,
    HARNESS_DIR,
    HELDOUT_PATH,
    INPUTS_DIR,
    LAB_DIR,
    LONG_TRAIN_PATH,
    REPORTS_DIR,
    REPO_DIR,
    SOURCE_COMMIT,
    TOKENIZER_PATH,
    child_environment,
    write_json_file,
):
    WINDOW_CACHE_DIR = LAB_DIR / "window-cache"
    CACHE_DATA_SHA = "0bff11279729d373a10d1e43e5830029caac95cf4602d9f41de3f9e3bc0dd862"
    CACHE_BUILDER_SHA = "4bd0ba15e2d065b0edb99a2b5c580a1111668c622f6aff521c3e3927553f2e47"

    def build_one_window_cache(path, label, *, sources=None, workers=12):
        builder = REPO_DIR / "teams/05-architecture/notebooks/build_window_cache.py"
        assert sha256_file(builder) == CACHE_BUILDER_SHA
        assert sha256_file(HARNESS_DIR / "week2/data.py") == CACHE_DATA_SHA
        command = [sys.executable, str(builder), "--input", str(path),
                   "--tokenizer", str(TOKENIZER_PATH), "--byte-table", str(BYTE_TABLE_PATH),
                   "--seq-len", "2048", "--cache-dir", str(WINDOW_CACHE_DIR),
                   "--workers", str(workers),
                   "--progress-json", str(REPORTS_DIR / f"cache-{label}-progress.json")]
        if sources is not None:
            command.extend(["--sources", str(sources)])
        receipt = {"command":command, "source_commit":SOURCE_COMMIT,
                   "builder_sha256":CACHE_BUILDER_SHA,"data_sha256":CACHE_DATA_SHA}
        write_json_file(REPORTS_DIR / f"cache-{label}-command.json",receipt)
        with (REPORTS_DIR / f"cache-{label}.log").open("w") as log:
            subprocess.run(command,cwd=REPO_DIR,env=child_environment(),
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=14400)
        progress = json.loads((REPORTS_DIR / f"cache-{label}-progress.json").read_text())
        assert progress["stage"] in ("complete","verified existing cache")
        return progress

    def build_synthetic_window_caches():
        return [
            build_one_window_cache(LONG_TRAIN_PATH,"synthetic-train",workers=2),
            build_one_window_cache(HELDOUT_PATH,"synthetic-heldout",workers=2),
        ]

    def build_real_window_caches():
        bundle = INPUTS_DIR / "preliminary"
        return [
            build_one_window_cache(bundle / "train.jsonl","real-train",workers=12),
            build_one_window_cache(bundle / "heldout.jsonl","real-heldout",
                                   sources=bundle / "heldout_sources.jsonl",workers=2),
        ]


    return CACHE_DATA_SHA, WINDOW_CACHE_DIR, build_real_window_caches


@app.cell(hide_code=True)
def window_cache_control():
    prepare_cache_button = mo.ui.run_button(label="Build the verified reusable real-data cache")
    mo.vstack([
        mo.md("## Cache the dataset once\n\nThe existing strict tokenizer/byte checks run "
              "in ordered CPU workers. Numeric, read-only windows preserve every document "
              "and avoid rebuilding the full corpus in RAM for each GPU run."),
        prepare_cache_button,
    ])

    return (prepare_cache_button,)


@app.cell
def window_cache_queue(
    build_real_window_caches,
    job_registry,
    prepare_cache_button,
):
    cache_executor = None
    if prepare_cache_button.value and not (job_registry.get("cache") and not job_registry["cache"].done()):
        cache_executor = ThreadPoolExecutor(max_workers=1)
        job_registry["cache"] = cache_executor.submit(build_real_window_caches)
    cache_future = job_registry.get("cache")
    mo.md("Cache construction status is shown below.")

    return (cache_future,)


@app.cell
def window_cache_monitor(REPORTS_DIR, cache_future, gpu_refresh):
    gpu_refresh.value
    _cache_progress_path = REPORTS_DIR / "cache-real-train-progress.json"
    cache_progress = json.loads(_cache_progress_path.read_text()) if _cache_progress_path.exists() else {"stage":"starting"}
    _cache_error = str(cache_future.exception()) if cache_future is not None and cache_future.done() and cache_future.exception() else None
    mo.vstack([
        mo.md("**Tokenized-window cache:** " + cache_progress["stage"]),
        mo.hstack([
            mo.stat(label="Documents cached",value=f"{cache_progress.get('document_count',0):,} / 1,400,499"),
            mo.stat(label="Tokens preserved",value=f"{cache_progress.get('tokens',0):,}"),
            mo.stat(label="Windows prepared",value=f"{cache_progress.get('windows',0):,}"),
        ],justify="space-between"),
        mo.callout(_cache_error,kind="danger") if _cache_error else
            mo.md("Text and order are unchanged. Cached arrays are checksummed and verified before use."),
    ])

    return


@app.cell
def cache_gpu_equivalence(
    ATTENTION_CASES,
    CACHE_DATA_SHA,
    HARNESS_DIR,
    REPORTS_DIR,
    RUNS_DIR,
    SCREEN_SEED,
    WINDOW_CACHE_DIR,
    run_recorded,
    trainer_command,
    write_json_file,
):
    def verify_cached_gpu_execution():
        assert sha256_file(HARNESS_DIR / "week2/data.py") == CACHE_DATA_SHA
        case = ATTENTION_CASES[0]
        directories = {name:RUNS_DIR / f"cache-proof-{name}-seed{SCREEN_SEED}"
                       for name in ("native","cached","interrupted","resumed")}
        native = run_recorded(trainer_command(case,directories["native"],steps=6),
                              directories["native"])
        cached = run_recorded(trainer_command(case,directories["cached"],steps=6),
                              directories["cached"],cache_dir=WINDOW_CACHE_DIR)
        partial = run_recorded(trainer_command(case,directories["interrupted"],steps=6,
                                              checkpoint=True,stop_after=3),
                               directories["interrupted"],cache_dir=WINDOW_CACHE_DIR)
        resumed = run_recorded(trainer_command(case,directories["resumed"],steps=6,
                            checkpoint=True,resume=directories["interrupted"]/"checkpoint.pt"),
                               directories["resumed"],cache_dir=WINDOW_CACHE_DIR)
        assert partial["steps"] == 3
        assert native["final_model_sha256"] == cached["final_model_sha256"] == resumed["final_model_sha256"]
        for filename in ("losses.txt","total_losses.txt"):
            assert (directories["native"]/filename).read_bytes() == (directories["cached"]/filename).read_bytes()
            assert (directories["native"]/filename).read_bytes() == (directories["resumed"]/filename).read_bytes()
        receipt = {"status":"passed","seed":SCREEN_SEED,"steps":6,
                   "cached_vs_native_losses_byte_identical":True,
                   "cached_resume_losses_byte_identical":True,
                   "final_model_sha256":native["final_model_sha256"],
                   "data_implementation_sha256":CACHE_DATA_SHA,"quality_result":False}
        write_json_file(REPORTS_DIR/"cache-gpu-equivalence.json",receipt)
        return receipt


    return (verify_cached_gpu_execution,)


@app.cell
def cache_gpu_control():
    run_cache_proof_button = mo.ui.run_button(label="Verify cached vs native GPU execution")
    mo.vstack([mo.md("The same six-step model run must produce byte-identical losses "
                    "and identical final weights, both without the cache and with it. "
                    "A cached three-plus-three restart must match too."),
               run_cache_proof_button])

    return (run_cache_proof_button,)


@app.cell
def cache_gpu_queue(
    job_registry,
    run_cache_proof_button,
    verify_cached_gpu_execution,
):
    cache_proof_executor = None
    if run_cache_proof_button.value and not (job_registry.get("cache_proof") and not job_registry["cache_proof"].done()):
        cache_proof_executor = ThreadPoolExecutor(max_workers=1)
        job_registry["cache_proof"] = cache_proof_executor.submit(verify_cached_gpu_execution)
    cache_proof_future = job_registry.get("cache_proof")
    mo.md("Cached GPU equivalence status is saved in the evidence report.")

    return (cache_proof_future,)


@app.cell
def real_screen_runner(
    ARM_DIR,
    ATTENTION_CASES,
    BYTE_TABLE_PATH,
    HARNESS_DIR,
    INPUTS_DIR,
    QUALITY_STEPS,
    REPORTS_DIR,
    REPO_DIR,
    RUNS_DIR,
    SCREEN_LR,
    SCREEN_SEED,
    SOURCE_COMMIT,
    TOKENIZER_PATH,
    WINDOW_CACHE_DIR,
    arm_configurations,
    child_environment,
    hardware,
    sampler_patch_sha,
    write_json_file,
):
    def screen_training_rows(output):
        """Read complete flushed records while a trainer is still writing."""
        path = Path(output) / "metrics.jsonl"
        if not path.exists():
            return []
        rows = []
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "train/ce_loss" in row:
                rows.append(row)
        return rows


    def screen_command(case, output):
        bundle = INPUTS_DIR / "preliminary"
        return [
            sys.executable, str(HARNESS_DIR / "train_week2.py"),
            "--config", str(ARM_DIR / case.config_file),
            "--runtime", str(REPO_DIR / "teams/05-architecture/configs/runtime.yaml"),
            "--tokenizer", str(TOKENIZER_PATH), "--byte-table", str(BYTE_TABLE_PATH),
            "--train-data", str(bundle / "train.jsonl"),
            "--heldout-data", str(bundle / "heldout.jsonl"),
            "--heldout-sources", str(bundle / "heldout_sources.jsonl"),
            "--heldout-sha256", str(bundle / "heldout.sha256"),
            "--heldout-report", str(bundle / "heldout_report.json"),
            "--seed", str(SCREEN_SEED), "--lr", str(SCREEN_LR), "--device", "cuda",
            "--smoke", "--smoke-steps", str(QUALITY_STEPS), "--out", str(output),
        ]


    def validate_screen_result(case, output, provenance):
        manifest = json.loads((output / "manifest.json").read_text())
        summary = json.loads((output / "summary.json").read_text())
        expected = json.loads(json.dumps(arm_configurations[case.key]))
        expected["run"]["seed"] = SCREEN_SEED
        expected["run"]["steps"] = QUALITY_STEPS
        expected["optim"]["lr"] = SCREEN_LR
        assert manifest["config"] == expected
        assert manifest["torch"] == torch.__version__
        assert manifest["smoke"] and not summary["eligible_for_quality_comparison"]
        assert manifest["train_sha256"] == provenance["train_sha256"]
        assert manifest["heldout_sha256"] == provenance["heldout_sha256"]
        assert manifest["sources"]["data.py"] == sampler_patch_sha
        source_files = [HARNESS_DIR / "train_week2.py", *sorted((HARNESS_DIR / "week2").glob("*.py"))]
        assert manifest["sources"] == {p.name:sha256_file(p) for p in source_files}
        rows = screen_training_rows(output)
        assert summary["steps"] == QUALITY_STEPS and not summary["timed_out"]
        assert len(rows) == QUALITY_STEPS
        assert all(math.isfinite(row[k]) for row in rows
                   for k in ("train/ce_loss", "gradient_norm", "perf/step_ms"))
        last = rows[-1]
        keys = ("val/three_group_bpb", "val/groups/code_bpb", "val/groups/indic_mean_bpb")
        assert all(math.isfinite(last[k]) for k in keys)
        return {"design":case.key, "seed":SCREEN_SEED, "steps":summary["steps"],
                "three-group BPB":last[keys[0]], "code BPB":last[keys[1]],
                "Indic BPB":last[keys[2]], "wall minutes":summary["wall_seconds"]/60,
                "median step seconds":statistics.median(r["perf/step_ms"] for r in rows)/1000,
                "scored training tokens":sum(r["train/scored_tokens"] for r in rows),
                "status":"complete preliminary run", "final comparison eligible":False}


    def run_single_seed_screen(preparation, cache_check, equivalence_check):
        """Wait for the verified prerequisites, then run five isolated GPU jobs."""
        progress_path = REPORTS_DIR / "screen-progress.json"
        state = {"stage":"waiting for verified reusable cache", "seed":SCREEN_SEED,
                 "completed_designs":0, "total_designs":5, "completed_steps":0,
                 "steps_per_design":QUALITY_STEPS, "preliminary":True}
        write_json_file(progress_path, state)
        if preparation is None or cache_check is None or equivalence_check is None:
            raise RuntimeError("Start input preparation and repaired restart verification first")
        provenance = preparation.result()
        cache_check.result()
        equivalence = equivalence_check.result()
        assert equivalence["status"] == "passed"
        assert equivalence["data_implementation_sha256"] == sampler_patch_sha
        assert sha256_file(HARNESS_DIR / "week2/data.py") == sampler_patch_sha
        bundle = INPUTS_DIR / "preliminary"
        assert sha256_file(bundle / "train.jsonl") == provenance["train_sha256"]
        assert sha256_file(bundle / "heldout.jsonl") == provenance["heldout_sha256"]
        output_root = RUNS_DIR / f"preliminary-cached-seed{SCREEN_SEED}-v1"
        output_root.mkdir(exist_ok=True)
        comparison = []

        for case in ATTENTION_CASES:
            output = output_root / case.key
            if (output / "summary.json").exists():
                comparison.append(validate_screen_result(case, output, provenance))
                reference = comparison[0]["three-group BPB"]
                for row in comparison:
                    row["BPB difference from reference"] = row["three-group BPB"]-reference
                write_json_file(REPORTS_DIR / "screen-comparison.json", comparison)
                state.update(completed_designs=len(comparison))
                write_json_file(progress_path,state)
                continue
            if output.exists() and any(output.iterdir()):
                raise RuntimeError(f"Inspect incomplete output before choosing a resume action: {case.key}")
            command = screen_command(case, output)
            write_json_file(REPORTS_DIR / f"screen-{case.key}-command.json", {
                "command":command, "source_commit":SOURCE_COMMIT,
                "data_loader_patch_sha256":sampler_patch_sha, "inputs":provenance,
                "purpose":"single-seed preliminary screen, not final course comparison"})
            state.pop("latest_training_loss",None)
            state.pop("process_ram_gib",None)
            state.pop("process_wall_minutes",None)
            state.update(stage="loading data / initial evaluation", design=case.key,
                         completed_steps=0, completed_designs=len(comparison))
            write_json_file(progress_path, state)
            started = time.monotonic()
            with (REPORTS_DIR / f"screen-{case.key}.log").open("w") as log:
                process = subprocess.Popen(command, cwd=REPO_DIR, env={**child_environment(), "G5_DOCUMENT_CACHE_DIR": str(WINDOW_CACHE_DIR)},
                                           stdout=log, stderr=subprocess.STDOUT)
                try:
                    while process.poll() is None:
                        rows = screen_training_rows(output)
                        if rows:
                            state.update(stage="training / scheduled heldout evaluation",
                                         completed_steps=rows[-1]["step"],
                                         latest_training_loss=rows[-1]["train/ce_loss"])
                        memory = Path(f"/proc/{process.pid}/status")
                        if memory.exists():
                            for line in memory.read_text().splitlines():
                                if line.startswith("VmRSS:"):
                                    state["process_ram_gib"] = int(line.split()[1])/1024**2
                                    if state["process_ram_gib"] > hardware["ram_gib_visible"]*0.75:
                                        raise MemoryError("Trainer exceeded its reserved host-memory budget")
                        state["process_wall_minutes"] = (time.monotonic()-started)/60
                        write_json_file(progress_path, state)
                        if time.monotonic()-started > 6600:
                            raise TimeoutError("Trainer exceeded 110 minutes including final serialization")
                        time.sleep(5)
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            process.kill()
                    process.wait()
            if process.returncode:
                state.update(stage="stopped: inspect trainer log", exit_code=process.returncode)
                write_json_file(progress_path, state)
                raise RuntimeError(f"{case.key} trainer failed; see screen-{case.key}.log")
            comparison.append(validate_screen_result(case, output, provenance))
            reference = comparison[0]["three-group BPB"]
            for row in comparison:
                row["BPB difference from reference"] = row["three-group BPB"]-reference
            write_json_file(REPORTS_DIR / "screen-comparison.json", comparison)
            state.update(completed_designs=len(comparison))
            write_json_file(progress_path, state)
        state.update(stage="all five preliminary runs complete", completed_designs=len(comparison),
                     completed_steps=QUALITY_STEPS,design="all five",complete=True)
        write_json_file(progress_path, state)
        return comparison

    return (
        run_single_seed_screen,
        screen_command,
        screen_training_rows,
        validate_screen_result,
    )


@app.cell
def real_screen_control():
    run_screen_button = mo.ui.run_button(label="Queue the five real-data, single-seed runs")
    mo.vstack([
        mo.md("This queues one GPU job at a time **after** data preparation and restart "
              "verification finish. It preserves pending approval and enables checkpointing. "
              "The full 90-minute limit remains in the trainer configuration for each design."),
        run_screen_button,
    ])
    return (run_screen_button,)


@app.cell
def real_screen_queue(
    cache_future,
    cache_proof_future,
    data_future,
    job_registry,
    run_screen_button,
    run_single_seed_screen,
):
    screen_executor = None
    if run_screen_button.value and not (job_registry.get("screen") and not job_registry["screen"].done()):
        screen_executor = ThreadPoolExecutor(max_workers=1)
        job_registry["screen"] = screen_executor.submit(
            run_single_seed_screen, data_future, cache_future, cache_proof_future)
    screen_future = job_registry.get("screen")
    mo.md("The real-data GPU queue is idle." if screen_future is None else
          "The real-data queue is active; all five jobs use the same verified cache and source.")

    return (screen_future,)


@app.cell
def parallel_execution_helpers(
    ATTENTION_CASES,
    INPUTS_DIR,
    QUALITY_STEPS,
    REPORTS_DIR,
    REPO_DIR,
    RUNS_DIR,
    SCREEN_SEED,
    SOURCE_COMMIT,
    WINDOW_CACHE_DIR,
    cache_future,
    cache_proof_future,
    child_environment,
    data_future,
    hardware,
    sampler_patch_sha,
    screen_command,
    screen_training_rows,
    validate_screen_result,
    write_json_file,
):
    OVERLAP_LIMIT = 3  # One sequential queue plus at most two independent designs.

    def refresh_completed_designs():
        """Merge only validated, completed runs; never promote an in-progress score."""
        provenance_path = INPUTS_DIR / "preliminary/provenance.json"
        if not provenance_path.exists():
            return []
        provenance = json.loads(provenance_path.read_text())
        root = RUNS_DIR / f"preliminary-cached-seed{SCREEN_SEED}-v1"
        rows = [validate_screen_result(case, root / case.key, provenance)
                for case in ATTENTION_CASES if (root / case.key / "summary.json").exists()]
        if rows and rows[0]["design"] == "attn-0":
            reference = rows[0]["three-group BPB"]
            for row in rows:
                row["BPB difference from reference"] = row["three-group BPB"] - reference
            write_json_file(REPORTS_DIR / "screen-comparison.json", rows)
        return rows


    def run_overlapped_design(case):
        """Use an isolated trainer process with exactly the original run settings."""
        provenance = data_future.result()
        cache_future.result()
        assert cache_proof_future.result()["status"] == "passed"
        output = RUNS_DIR / f"preliminary-cached-seed{SCREEN_SEED}-v1" / case.key
        if (output / "summary.json").exists():
            return validate_screen_result(case, output, provenance)
        if output.exists() and any(output.iterdir()):
            raise RuntimeError(f"Preserve incomplete output before rerunning {case.key}")
        command = screen_command(case, output)
        write_json_file(REPORTS_DIR / f"screen-{case.key}-command.json", {
            "command":command, "source_commit":SOURCE_COMMIT, "inputs":provenance,
            "execution_mode":"independent process, bounded overlap",
            "maximum_concurrent_trainers":OVERLAP_LIMIT,
            "data_loader_patch_sha256":sampler_patch_sha,
            "timings_are_comparative_benchmarks":False,
            "purpose":"single-seed preliminary screen, not final course comparison",
        })
        progress = {"design":case.key, "stage":"loading / initial evaluation",
                    "completed_steps":0, "seed":SCREEN_SEED, "preliminary":True}
        progress_path = REPORTS_DIR / f"screen-{case.key}-progress.json"
        write_json_file(progress_path, progress)
        started = time.monotonic()
        environment = {**child_environment(), "G5_DOCUMENT_CACHE_DIR":str(WINDOW_CACHE_DIR)}
        with (REPORTS_DIR / f"screen-{case.key}.log").open("w") as log:
            process = subprocess.Popen(command,cwd=REPO_DIR,env=environment,
                                       stdout=log,stderr=subprocess.STDOUT)
            try:
                while process.poll() is None:
                    rows = screen_training_rows(output)
                    if rows:
                        progress.update(stage="training / heldout evaluation",
                                        completed_steps=rows[-1]["step"],
                                        latest_training_loss=rows[-1]["train/ce_loss"])
                    memory_path = Path(f"/proc/{process.pid}/status")
                    if memory_path.exists():
                        for line in memory_path.read_text().splitlines():
                            if line.startswith("VmRSS:"):
                                progress["process_ram_gib"] = int(line.split()[1])/1024**2
                                if progress["process_ram_gib"] > hardware["ram_gib_visible"]*0.5:
                                    raise MemoryError("Overlapped trainer exceeded its host-memory reserve")
                    progress["process_wall_minutes"] = (time.monotonic()-started)/60
                    write_json_file(progress_path,progress)
                    if time.monotonic()-started > 6600:
                        raise TimeoutError("Overlapped trainer exceeded its process allowance")
                    time.sleep(5)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                process.wait()
        if process.returncode:
            progress.update(stage="failed: inspect trainer log",exit_code=process.returncode)
            write_json_file(progress_path,progress)
            raise RuntimeError(f"{case.key} failed; inspect its preserved log")
        result = validate_screen_result(case,output,provenance)
        progress.update(stage="complete preliminary run",complete=True,completed_steps=QUALITY_STEPS)
        write_json_file(progress_path,progress)
        write_json_file(REPORTS_DIR / f"screen-{case.key}-result.json",result)
        return result


    return OVERLAP_LIMIT, refresh_completed_designs, run_overlapped_design


@app.cell(hide_code=True)
def parallel_execution_controls():
    overlap_gate_button = mo.ui.run_button(label="Overlap output-gate design")
    overlap_rope_button = mo.ui.run_button(label="Overlap half-RoPE design")
    mo.vstack([
        mo.md("""
    ## Use spare GPU capacity across independent runs

    A measured single trainer used about 12.2 GiB of 95 GiB, 37–52% GPU activity and
    roughly 150 W of a 600 W limit. The trainer runs eight microbatches in sequence,
    dispatches experts through Python loops and checks each gradient/parameter for
    finite values every update. These small operations and CPU/GPU handoffs are
    plausible sources of the measured idle gaps; this is a code/telemetry inference,
    not a detailed kernel profile. Up to **three isolated trainers** can overlap to fill some of those
    gaps, without changing any design's seed, data, microbatch, optimizer or updates.

    The first queue still handles the reference, shared-key/value and windowed
    designs. These optional controls let the last two designs run alongside it.
    Opening the notebook never starts them. Overlapped wall times include contention
    and must not be treated as comparative speed benchmarks.
    """),
        mo.hstack([overlap_gate_button,overlap_rope_button]),
    ])
    return overlap_gate_button, overlap_rope_button


@app.cell
def parallel_execution_queue(
    ATTENTION_CASES,
    job_registry,
    overlap_gate_button,
    overlap_rope_button,
    run_overlapped_design,
):
    overlap_executor = ThreadPoolExecutor(max_workers=2)
    for _key, _button in (("attn-4",overlap_gate_button),("attn-3",overlap_rope_button)):
        _registry_key = "overlap-"+_key
        if _button.value and _registry_key not in job_registry:
            if not (job_registry.get("screen") and not job_registry["screen"].done()):
                raise RuntimeError("Start the main screen before enabling overlap.")
            _case = next(case for case in ATTENTION_CASES if case.key == _key)
            job_registry[_registry_key] = overlap_executor.submit(run_overlapped_design,_case)
    mo.md("Optional parallel jobs are retained across notebook display refreshes.")
    return


@app.cell
def parallel_execution_monitor(
    ATTENTION_CASES,
    REPORTS_DIR,
    gpu_refresh,
    job_registry,
    refresh_completed_designs,
):
    gpu_refresh.value
    overlap_completed = refresh_completed_designs()
    _overlap_rows = []
    for _case in ATTENTION_CASES:
        _file = REPORTS_DIR / f"screen-{_case.key}-progress.json"
        if _file.exists():
            _p = json.loads(_file.read_text())
            _overlap_rows.append({"design":_case.key,"stage":_p["stage"],
                                  "updates":_p.get("completed_steps",0),
                                  "minutes":round(_p.get("process_wall_minutes",0),1)})
    _overlap_errors = [str(f.exception()) for k,f in job_registry.items()
                       if k.startswith("overlap-") and f.done() and f.exception()]
    mo.vstack([
        mo.md(f"### Combined screen: {len(overlap_completed)}/5 complete"),
        mo.ui.table(_overlap_rows,selection=None) if _overlap_rows else mo.md("No overlapped job started."),
        *[mo.callout(error,kind="danger") for error in _overlap_errors],
    ])
    return


@app.cell
def screen_monitor(QUALITY_STEPS, REPORTS_DIR, gpu_refresh, screen_future):
    gpu_refresh.value
    _path = REPORTS_DIR / "screen-progress.json"
    screen_progress = json.loads(_path.read_text()) if _path.exists() else {"stage":"not queued"}
    _comparison = REPORTS_DIR / "screen-comparison.json"
    screen_comparison = json.loads(_comparison.read_text()) if _comparison.exists() else []
    _error = str(screen_future.exception()) if screen_future is not None and screen_future.done() and screen_future.exception() else None
    mo.vstack([
        mo.md("## Real-data run monitor\n\n**" + screen_progress["stage"] + "**"),
        mo.hstack([
            mo.stat(label="Current design",value=screen_progress.get("design","—")),
            mo.stat(label="Completed updates",value=f"{screen_progress.get('completed_steps',0):,} / {QUALITY_STEPS:,}"),
            mo.stat(label="Finished designs",value=f"{screen_progress.get('completed_designs',0)} / 5"),
        ],justify="space-between"),
        mo.md(f"Current process: **{screen_progress.get('process_wall_minutes',0):.1f} minutes**; "
              f"host memory **{screen_progress.get('process_ram_gib',0):.1f} GiB**."),
        mo.callout(_error,kind="danger") if _error else mo.md(
            "Lower BPB means lower prediction error per byte. One seed does not measure run-to-run variation."),
        mo.ui.table([{k:row[k] for k in ("design","three-group BPB","code BPB","Indic BPB",
                                        "BPB difference from reference","wall minutes")}
                     for row in screen_comparison],selection=None) if screen_comparison else
            mo.md("No completed real-data runs yet."),
    ])

    return


@app.cell
def screen_loss_plots(
    ATTENTION_CASES,
    REPORTS_DIR,
    RUNS_DIR,
    SCREEN_SEED,
    gpu_refresh,
    screen_training_rows,
):
    gpu_refresh.value
    _styles = ("-", "--", "-.", ":", (0,(5,1,1,1,1,1)))
    screen_figure, _axes = plt.subplots(1,2,figsize=(12,4.4),sharey=True,layout="constrained")
    for _index, _case in enumerate(ATTENTION_CASES):
        _rows = screen_training_rows(RUNS_DIR / f"preliminary-cached-seed{SCREEN_SEED}-v1" / _case.key)
        if not _rows:
            continue
        _steps = [row["step"] for row in _rows]
        _losses = [row["train/ce_loss"] for row in _rows]
        _color = f"C{_index}"
        _axes[0].plot(_steps,_losses,color=_color,linestyle=_styles[_index],alpha=.5,linewidth=.7,label=_case.title)
        if len(_losses) >= 25:
            _smoothed = np.convolve(_losses,np.ones(25)/25,mode="valid")
            _axes[1].plot(_steps[24:],_smoothed,color=_color,linestyle=_styles[_index],linewidth=1.4)
    for _axis, _title in zip(_axes,("Raw training batches","25-update moving average")):
        _axis.set_title(_title)
        _axis.set_xlabel("Weight updates",fontsize=13)
        _axis.tick_params(labelsize=12)
        _axis.grid(alpha=.2)
    _axes[0].set_ylabel("Training cross-entropy loss",fontsize=13)
    screen_figure.suptitle(f"Preliminary real-data screen · seed {SCREEN_SEED}")
    if _axes[0].has_data():
        screen_figure.legend(*_axes[0].get_legend_handles_labels(),loc="outside lower center",ncol=3,fontsize=12)
        screen_figure.savefig(REPORTS_DIR / "screen-losses.png",dpi=170)
    plt.close(screen_figure)
    screen_figure
    return


@app.cell
def heldout_bpb_plots(
    ATTENTION_CASES,
    REPORTS_DIR,
    RUNS_DIR,
    SCREEN_SEED,
    gpu_refresh,
):
    gpu_refresh.value
    _styles = ("-", "--", "-.", ":", (0,(5,1,1,1,1,1)))
    evaluation_figure, _axes = plt.subplots(1,3,figsize=(12,4.4),layout="constrained")
    _metrics = [
        ("val/three_group_bpb","Three-group BPB"),
        ("val/groups/code_bpb","Code BPB"),
        ("val/groups/indic_mean_bpb","Indic BPB"),
    ]
    for _index,_case in enumerate(ATTENTION_CASES):
        _path = RUNS_DIR / f"preliminary-cached-seed{SCREEN_SEED}-v1" / _case.key / "metrics.jsonl"
        _rows = []
        if _path.exists():
            for _line in _path.read_text().splitlines():
                try:
                    _row = json.loads(_line)
                except json.JSONDecodeError:
                    continue
                if "val/three_group_bpb" in _row:
                    _rows.append(_row)
        for _axis,(_key,_label) in zip(_axes,_metrics):
            if _rows:
                _axis.plot([r["step"] for r in _rows],[r[_key] for r in _rows],
                           linewidth=1.2,color=f"C{_index}",linestyle=_styles[_index],label=_case.title)
            _axis.set_title(_label)
            _axis.set_xlabel("Training update",fontsize=13)
            _axis.tick_params(labelsize=12)
            _axis.grid(alpha=.2)
    _axes[0].set_ylabel("Prediction error per byte; lower is better",fontsize=13)
    if _axes[0].has_data():
        evaluation_figure.legend(*_axes[0].get_legend_handles_labels(),loc="outside lower center",ncol=3,fontsize=12)
        evaluation_figure.savefig(REPORTS_DIR/"screen-heldout-bpb.png",dpi=170)
    plt.close(evaluation_figure)
    evaluation_figure

    return


@app.cell
def result_table_exports(
    ATTENTION_CASES,
    OVERLAP_LIMIT,
    QUALITY_STEPS,
    REPORTS_DIR,
    RUNS_DIR,
    SCREEN_SEED,
    SOURCE_COMMIT,
    refresh_completed_designs,
    screen_training_rows,
    write_json_file,
):
    def export_result_tables():
        """Save readable comparisons, every slice, and the unchanged 15-request status."""
        comparison = refresh_completed_designs()
        labels = {case.key:case.title for case in ATTENTION_CASES}
        root = RUNS_DIR / f"preliminary-cached-seed{SCREEN_SEED}-v1"

        def write_table(filename, rows):
            if not rows:
                return
            with (REPORTS_DIR / filename).open("w",newline="",encoding="utf-8") as stream:
                writer = csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)

        friendly = [{"description":labels[row["design"]],**row} for row in comparison]
        write_table("screen-comparison.csv",friendly)
        slices = []
        for row in comparison:
            output = root / row["design"]
            manifest = json.loads((output / "manifest.json").read_text())
            last = screen_training_rows(output)[-1]
            names = sorted(key.split("/")[2] for key in last
                           if key.startswith("val/slices/") and key.endswith("/bpb"))
            assert len(names) == 15 and manifest["heldout_documents"] == 1059
            assert manifest["train_documents"] == 1400499
            assert sum(last[f"val/slices/{name}/utf8_bytes"] for name in names) == last["val/utf8_bytes"] == 3775551
            for name in names:
                slices.append({"design":row["design"],"description":labels[row["design"]],
                               "seed":SCREEN_SEED,"slice":name,
                               "BPB":last[f"val/slices/{name}/bpb"],
                               "raw UTF-8 bytes":last[f"val/slices/{name}/utf8_bytes"],
                               "scored tokens":last[f"val/slices/{name}/scored_tokens"]})
        write_table("screen-slice-scores.csv",slices)
        completed = {row["design"]:row for row in comparison}
        requests = []
        for seed in (1234,1235,1236):
            for case in ATTENTION_CASES:
                local = completed.get(case.key) if seed == SCREEN_SEED else None
                requests.append({"design":case.key,"description":case.title,"seed":seed,
                                 "local status":"complete preliminary run" if local else "no completed local result",
                                 "updates":local["steps"] if local else "",
                                 "final quality eligible":False,
                                 "note":"One-seed development evidence; approval pending" if local else
                                        "Official request unchanged; local scope was one seed"})
        write_table("requested-seed-status.csv",requests)
        write_json_file(REPORTS_DIR / "screen-final-verification.json",{
            "completed_preliminary_runs":len(comparison),"seed":SCREEN_SEED,
            "source_commit":SOURCE_COMMIT,"all_steps_complete":all(row["steps"]==QUALITY_STEPS for row in comparison),
            "training_scored_tokens_per_design":sorted({row["scored training tokens"] for row in comparison}),
            "slice_rows":len(slices),"heldout_bytes_per_design":3775551,
            "harness_tests_passed":113,"final_quality_result":False,
            "seed_spread":None,"maximum_concurrent_trainers":OVERLAP_LIMIT,
            "timings_are_comparative_benchmarks":False,
        })
        return comparison


    return (export_result_tables,)


@app.cell
def score_reading_guide():
    mo.md("""
    ## Reading the final scores

    **Bits per byte (BPB)** measures prediction error on the separate held-out text;
    lower is better. The primary **three-group score** equally averages English,
    code, and the mean of the eleven Indic-language scores. Math and science are
    also retained in the full 15-slice report.

    The difference column subtracts the reference score. A negative value means
    lower observed error on this seed. One seed cannot provide a seed range or
    establish the course's final acceptance rule.

    For the handoff, use the recorded scores, complete source/data identities and
    loss plots. The submitted request still covers all three seeds. Common settings
    and approval must be confirmed before the final course comparison.
    """)
    return


@app.cell
def evidence_download_controls(LAB_DIR):
    save_evidence_button = mo.ui.run_button(label="Save current evidence archive")
    GPU_EVIDENCE_PATH = LAB_DIR / "attention-gpu-evidence.zip"
    mo.vstack([
        mo.md("## Save evidence\n\nSource, commands, test logs, hashes, metrics and plots "
              "are included. Raw datasets, signed download URLs and checkpoints are excluded. "
              "An archive saved before completion is a progress snapshot."),
        save_evidence_button,
    ])

    return GPU_EVIDENCE_PATH, save_evidence_button


@app.cell
def evidence_downloads(
    GPU_EVIDENCE_PATH,
    INPUTS_DIR,
    REPORTS_DIR,
    RUNS_DIR,
    export_result_tables,
    save_evidence_button,
):
    if save_evidence_button.value:
        export_result_tables()
        with zipfile.ZipFile(GPU_EVIDENCE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as _bundle:
            for _file in sorted(REPORTS_DIR.rglob("*")):
                if _file.is_file() and _file.suffix in {".json", ".jsonl", ".csv", ".log", ".png"}:
                    _bundle.write(_file, "reports/" + str(_file.relative_to(REPORTS_DIR)))
            for _file in sorted(RUNS_DIR.rglob("*")):
                if _file.is_file() and _file.name in {
                        "manifest.json", "summary.json", "metrics.jsonl",
                        "losses.txt", "total_losses.txt"}:
                    _bundle.write(_file, "runs/" + str(_file.relative_to(RUNS_DIR)))
            for _name in ("provenance.json", "heldout_report.json", "heldout.sha256"):
                _file = INPUTS_DIR / "preliminary" / _name
                if _file.exists():
                    _bundle.write(_file, "input-provenance/" + _name)
            _bundle.write(Path(mo.notebook_location()), "attention_gpu_screen.py")
    mo.download(GPU_EVIDENCE_PATH.read_bytes(),filename="attention-gpu-evidence.zip",
                label="Download current evidence") if GPU_EVIDENCE_PATH.exists() else mo.md("No archive saved yet.")

    return


if __name__ == "__main__":
    app.run()
