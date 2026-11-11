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



@app.cell(hide_code=True)
def lab_intro():
    mo.md(r"""
    # Attention smoke lab

    **Question:** can the existing reference model and four attention alternatives
    complete a few training steps correctly?

    A **smoke test** is a short launch check. It is not evidence that one model is
    better. We use real course tokenizer assets with clearly labeled synthetic text.

    **Plan:** inspect hardware → pin source code → prepare inputs → test five designs
    → save evidence → prepare the compute request.

    The model implementation stays in the course repository. This notebook contains
    readable setup, test orchestration, and explanations.
    """)
    return


@app.cell(hide_code=True)
def glossary():
    mo.md(r"""
    ## A few labels used below

    - **Reference / baseline:** the existing design we compare against.
    - **Arm:** one version of the experiment. There are five versions here.
    - **T2:** the course's medium-sized model recipe; it is a settings file.
    - **bf16 / fp32:** number formats used for GPU / CPU calculations in these tests.
    - **Raw-byte table:** the tokenizer's matching lookup table; P32 means rows hold
      up to 32 bytes per token.

    The official comparison uses longer training and the approved real dataset.
    These short synthetic runs establish that the program launches and learns.
    """)
    return


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
    LAB_DIR = Path(os.environ.get("ATTENTION_SMOKE_DIR", str(Path.cwd() / "attention-smoke-lab")))
    INPUTS_DIR = LAB_DIR / "inputs"
    RUNS_DIR = LAB_DIR / "runs"
    REPORTS_DIR = LAB_DIR / "reports"
    REPO_DIR = LAB_DIR / "era-v5-lab"
    SOURCE_COMMIT = "c9cac5a0d5811e712212a37a01d6c540346ff1a1"
    REPO_URL = "https://github.com/theschoolofai/era-v5-lab.git"

    for _directory in (LAB_DIR, INPUTS_DIR, RUNS_DIR, REPORTS_DIR):
        _directory.mkdir(parents=True, exist_ok=True)

    if not (REPO_DIR / ".git").exists():
        run_checked(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, REPO_DIR])

    # Preserve tracked source edits; runtime __pycache__ files are harmless untracked outputs.
    if (REPO_DIR / ".git/index").exists():
        if run_checked(["git", "-C", REPO_DIR, "status", "--porcelain", "--untracked-files=no"]).strip():
            raise RuntimeError("The source checkout has edits; preserve them before changing revisions.")
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

    return INPUTS_DIR, LAB_DIR, REPORTS_DIR, REPO_DIR, RUNS_DIR, SOURCE_COMMIT


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
def course_imports(BYTE_TABLE_PATH, REPO_DIR, TOKENIZER_PATH):
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

    return HELDOUT_PATH, TRAIN_PATH, input_provenance


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


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
def smoke_intro():
    mo.md(r"""
    ## What the short runs prove

    We keep the real model width, depth, experts, vocabulary, and attention choices.
    Only the supported smoke settings shrink the work:

    | Setting | CPU launch check | GPU launch check | Official comparison |
    |---|---:|---:|---:|
    | Training steps | 6 | 8 | 1,221 |
    | Context length | 160 | 160 | 2,048 |
    | Sequences per update | 1 | 1 | 8 |
    | Number format | fp32 | bf16 | bf16 |
    | Quality result? | No | No | Requires official data and approval |

    A **seed** selects a reproducible random start. These launch checks use 1234.
    The later quality comparison still requires 1234, 1235, and 1236.

    The windowed design sees only the latest 128 tokens in its local layers.
    Our 160-token smoke context therefore exercises the boundary.
    """)
    return


@app.cell(hide_code=True)
def verification_intro():
    mo.md(r"""
    ## Verification before interpreting anything

    The existing test suite checks attention boundaries, gate behavior, gradients,
    repeatability, checkpoint restore, and byte accounting. We run it unchanged.

    Below, CPU and GPU runs execute the **actual training program**. A finite loss
    means the arithmetic stayed valid. A few losses can fluctuate because consecutive
    steps use different text; the plots are launch diagnostics, not a ranking.
    """)
    return


@app.cell
def smoke_runner(
    ARM_DIR,
    BYTE_TABLE_PATH,
    HARNESS_DIR,
    HELDOUT_PATH,
    REPORTS_DIR,
    REPO_DIR,
    RUNS_DIR,
    SOURCE_COMMIT,
    TOKENIZER_PATH,
    TRAIN_PATH,
    arm_configurations,
    artifacts,
    input_provenance,
):
    SMOKE_STEPS = {"cpu": 6, "cuda": 8}
    SMOKE_CONTEXT = 160
    SMOKE_SEED = 1234

    def smoke_directory(case, device):
        return RUNS_DIR / (
            f"{case.key}-{device}-{SMOKE_STEPS[device]}steps-ctx{SMOKE_CONTEXT}"
        )

    def read_smoke_result(case, device):
        """Validate a completed run before treating its files as reusable evidence."""
        output = smoke_directory(case, device)
        if not (output / "summary.json").exists():
            return {"design": case.key, "device": device, "status": "not run"}
        summary = json.loads((output / "summary.json").read_text())
        manifest = json.loads((output / "manifest.json").read_text())
        records = [
            json.loads(line) for line in (output / "metrics.jsonl").read_text().splitlines()
            if line.strip()
        ]
        # The trainer also records an initial evaluation at step 0.
        updates = [row for row in records if "train/ce_loss" in row]
        expected = json.loads(json.dumps(arm_configurations[case.key]))
        expected["model"]["block_size"] = SMOKE_CONTEXT
        expected["run"].update(
            steps=SMOKE_STEPS[device], batch_size=1, micro_batch_size=1, seed=SMOKE_SEED,
            dtype="fp32" if device == "cpu" else expected["run"]["dtype"],
        )
        assert summary["status"] == "SMOKE" and not summary["timed_out"]
        assert manifest["smoke"] and not summary["eligible_for_quality_comparison"]
        assert summary["steps"] == len(updates) == SMOKE_STEPS[device]
        assert manifest["config"] == expected, "Cached training settings differ; use a fresh workspace."
        assert manifest["artifacts"] == artifacts.identity()
        assert manifest["train_sha256"] == sha256_file(TRAIN_PATH)
        assert manifest["heldout_sha256"] == sha256_file(HELDOUT_PATH)
        assert manifest["torch"] == torch.__version__, "Use a fresh work directory for a different PyTorch runtime."
        source_files = [HARNESS_DIR / "train_week2.py", *(HARNESS_DIR / "week2").glob("*.py")]
        assert manifest["sources"] == {path.name: sha256_file(path) for path in source_files}
        assert all(np.isfinite([row["loss"], row["gradient_norm"]]).all() for row in updates)
        return {
            "design": case.key, "device": device, "status": "passed",
            "steps": summary["steps"], "first loss": summary["first_ce"],
            "last loss": summary["last_ce"],
            "wall seconds": round(summary["wall_seconds"], 2),
        }

    def run_smoke(case, device):
        """Run the existing trainer. Completed, matching evidence is reused."""
        output = smoke_directory(case, device)
        if (output / "summary.json").exists():
            return read_smoke_result(case, device)
        if output.exists() and any(output.iterdir()):
            raise RuntimeError(f"Inspect incomplete evidence before retrying: {output}")

        command = [
            sys.executable, str(HARNESS_DIR / "train_week2.py"),
            "--config", str(ARM_DIR / case.config_file),
            "--tokenizer", str(TOKENIZER_PATH), "--byte-table", str(BYTE_TABLE_PATH),
            "--train-data", str(TRAIN_PATH), "--heldout-data", str(HELDOUT_PATH),
            "--device", device, "--seed", str(SMOKE_SEED),
            "--smoke", "--smoke-steps", str(SMOKE_STEPS[device]),
            "--smoke-seq-len", str(SMOKE_CONTEXT), "--smoke-batch-size", "1",
            "--no-checkpoint", "--out", str(output),
        ]
        command_record = {
            "command": command, "commit": SOURCE_COMMIT,
            "config_sha256": sha256_file(ARM_DIR / case.config_file),
            "inputs": input_provenance,
        }
        (REPORTS_DIR / f"{output.name}-command.json").write_text(
            json.dumps(command_record, indent=2), encoding="utf-8"
        )
        environment = {
            **os.environ, "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4",
            "PYTHONUNBUFFERED": "1", "PYTHONPATH": str(HARNESS_DIR),
            "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
        }
        with (REPORTS_DIR / f"{output.name}.log").open("w") as log:
            subprocess.run(command, cwd=REPO_DIR, env=environment, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=300)
        return read_smoke_result(case, device)

    def run_existing_tests():
        """Run the unmodified verification suite and preserve its output."""
        command = [
            sys.executable, "-m", "unittest", "discover",
            "-s", str(REPO_DIR / "teams/05-architecture/tests"),
            "-p", "test_week2*.py", "-v",
        ]
        with (REPORTS_DIR / "unit-tests.log").open("w") as log:
            subprocess.run(
                command, cwd=REPO_DIR, stdout=log, stderr=subprocess.STDOUT,
                env={**os.environ, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                     "PYTHONPATH": str(HARNESS_DIR)},
                check=True, timeout=120,
            )
        return "Existing tests passed."


    return read_smoke_result, run_existing_tests, run_smoke, smoke_directory


@app.cell
def run_controls(hardware):
    run_checks = mo.ui.run_button(label="Run verification and smoke tests")
    include_gpu_checks = mo.ui.checkbox(
        value=hardware["cuda_available"] and hardware.get("bf16_supported", False),
        disabled=not (hardware["cuda_available"] and hardware.get("bf16_supported", False)),
        label="Include GPU bf16 checks",
    )
    mo.vstack([
        mo.md("**Run deliberately:** opening this notebook does not start training. "
              "The button queues one test at a time; matching completed runs are reused."),
        mo.hstack([run_checks, include_gpu_checks]),
    ])

    return include_gpu_checks, run_checks


@app.cell
def run_queue(
    ATTENTION_CASES,
    include_gpu_checks,
    run_checks,
    run_existing_tests,
    run_smoke,
):
    smoke_futures = {}
    smoke_executor = None
    if run_checks.value:
        # Serial execution avoids launching five large models into limited RAM.
        smoke_executor = ThreadPoolExecutor(max_workers=1)
        smoke_futures["tests"] = smoke_executor.submit(run_existing_tests)
        for _device in ("cpu", "cuda"):
            if _device == "cuda" and not include_gpu_checks.value:
                continue
            for _case in ATTENTION_CASES:
                smoke_futures[(_case.key, _device)] = smoke_executor.submit(
                    run_smoke, _case, _device
                )
    mo.md("The queue is idle. Existing evidence is shown below." if not smoke_futures
          else "Checks are queued in the background. Refresh the results to follow progress.")

    return (smoke_futures,)


@app.cell
def results_refresh():
    results_refresh = mo.ui.refresh(label="Refresh completed results")
    results_refresh

    return (results_refresh,)


@app.cell
def results(
    ATTENTION_CASES,
    REPORTS_DIR,
    include_gpu_checks,
    read_smoke_result,
    results_refresh,
    smoke_futures,
):
    results_refresh.value
    display_rows = []
    for _device in ("cpu", "cuda"):
        if _device == "cuda" and not include_gpu_checks.value:
            continue
        for _case in ATTENTION_CASES:
            _future = smoke_futures.get((_case.key, _device))
            if _future is not None and not _future.done():
                _row = {"design": _case.key, "device": _device,
                        "status": "running" if _future.running() else "queued"}
            elif _future is not None and _future.exception() is not None:
                _row = {"design": _case.key, "device": _device,
                        "status": f"failed: {_future.exception()}"}
            else:
                _row = read_smoke_result(_case, _device)
            display_rows.append(_row)

    _unit_log_path = REPORTS_DIR / "unit-tests.log"
    unit_log_text = _unit_log_path.read_text() if _unit_log_path.exists() else ""
    _unit_tail = "\n".join(unit_log_text.splitlines()[-4:])
    mo.vstack([
        mo.ui.table(display_rows, selection=None),
        mo.md("**Existing verification suite:**\n\n" + _unit_tail.replace("\n", "  \n")),
        mo.md("Wall times include startup and evaluation. These are not speed benchmarks."),
    ])

    return display_rows, unit_log_text


@app.cell
def loss_plots(ATTENTION_CASES, REPORTS_DIR, results_refresh, smoke_directory):
    results_refresh.value
    loss_figure, _axes = plt.subplots(2, 3, figsize=(11, 5.4), constrained_layout=True)
    for _axis, _case in zip(_axes.flat, ATTENTION_CASES):
        for _device, _label, _color, _marker in (
            ("cpu", "CPU fp32", "#64748b", "s"),
            ("cuda", "GPU bf16", "#2563eb", "o"),
        ):
            _path = smoke_directory(_case, _device) / "metrics.jsonl"
            if not _path.exists():
                continue
            _rows = [json.loads(line) for line in _path.read_text().splitlines() if line.strip()]
            _rows = [row for row in _rows if "train/ce_loss" in row]
            if _rows:
                _axis.plot(
                    [row["step"] for row in _rows],
                    [row["train/ce_loss"] for row in _rows],
                    color=_color, label=_label, marker=_marker,
                    linestyle="--" if _device == "cpu" else "-",
                    markersize=5 if _device == "cpu" else 3,
                    markerfacecolor="none" if _device == "cpu" else _color,
                )
        _axis.set_title(f"{_case.key}: {_case.title}", fontsize=9)
        _axis.set_xlabel("Training step", fontsize=8)
        _axis.set_ylabel("Training loss", fontsize=8)
        _axis.grid(alpha=0.2)
        if _axis.lines:
            _axis.legend(fontsize=7)
    _axes.flat[-1].axis("off")
    _axes.flat[-1].text(
        0.05, 0.75,
        "Loss measures prediction error.\nLower is better on that batch.\n\n"
        "These short synthetic traces\ncheck execution, not model quality.",
        fontsize=10, va="top",
    )
    loss_figure.suptitle("Attention smoke diagnostics", fontsize=12)
    loss_figure.savefig(REPORTS_DIR / "smoke-losses.png", dpi=160)
    plt.close(loss_figure)
    loss_figure

    return


@app.cell
def full_shape_results(LAB_DIR):
    full_shape_path = LAB_DIR / 'full-shape-probe' / 'probe-summary.json'
    full_shape_rows = json.loads(full_shape_path.read_text()) if full_shape_path.exists() else []
    mo.vstack([
        mo.md(r'''
        ## Optional: does the full training shape fit?

        The short checks above use shorter sequences and smaller batches. The separate
        `full_shape_probe.py` helper in this repository's notebooks folder checks three
        GPU steps at **2048 tokens, global batch 8, microbatch 1** for each design.
        Run it after setup, pointing `--workspace` to the workspace shown above.

        It uses longer synthetic documents. Timing excludes the official evaluation
        and checkpoint workload; it cannot establish a complete 90-minute run.
        Saved results appear below after this cell is refreshed. Memory is sampled
        total device use, rather than the trainer's peak tensor allocation.
        '''),
        mo.ui.table(full_shape_rows, selection=None) if full_shape_rows else
            mo.md('No full-size probe results in this workspace yet.'),
    ])

    return


@app.cell
def evidence_export(
    ATTENTION_CASES,
    LAB_DIR,
    REPORTS_DIR,
    SOURCE_COMMIT,
    display_rows,
    hardware,
    input_provenance,
    read_smoke_result,
    results_refresh,
    smoke_directory,
    unit_log_text,
):
    results_refresh.value
    _ready = len(display_rows) >= 5 and all(row["status"] == "passed" for row in display_rows)
    mo.stop(not _ready, mo.md("Complete the selected checks before exporting evidence."))

    EVIDENCE_DIR = LAB_DIR / "smoke-evidence"
    EVIDENCE_DIR.mkdir(exist_ok=True)
    for _case in ATTENTION_CASES:
        for _device in ("cpu", "cuda"):
            _output = smoke_directory(_case, _device)
            if not (_output / "summary.json").exists():
                continue
            read_smoke_result(_case, _device)
            _destination = EVIDENCE_DIR / f"{_case.key}-{_device}"
            _destination.mkdir(exist_ok=True)
            for _name in ("manifest.json", "summary.json", "metrics.jsonl", "losses.txt"):
                shutil.copy2(_output / _name, _destination / _name)
            _record = REPORTS_DIR / f"{_output.name}-command.json"
            shutil.copy2(_record, _destination / "command.json")

    for _name in ("environment.json", "inputs.json", "unit-tests.log",
                  "smoke-losses.png", "gpu-driver.json"):
        shutil.copy2(REPORTS_DIR / _name, EVIDENCE_DIR / _name)

    verification_summary = {
        "source_commit": SOURCE_COMMIT,
        "existing_tests_passed": 102 if "Ran 102 tests" in unit_log_text and unit_log_text.rstrip().endswith("OK") else None,
        "cpu_smokes_passed": sum(r["device"] == "cpu" and r["status"] == "passed" for r in display_rows),
        "gpu_bf16_smokes_passed": sum(r["device"] == "cuda" and r["status"] == "passed" for r in display_rows),
        "quality_results": False,
        "runs": display_rows,
        "runtime": hardware,
        "inputs": input_provenance,
    }
    (EVIDENCE_DIR / "verification-summary.json").write_text(
        json.dumps(verification_summary, indent=2), encoding="utf-8"
    )
    with (EVIDENCE_DIR / "smoke-summary.csv").open("w", newline="") as _handle:
        _writer = csv.DictWriter(_handle, fieldnames=list(display_rows[0]))
        _writer.writeheader()
        _writer.writerows(display_rows)

    BUNDLE_PATH = LAB_DIR / "attention-smoke-evidence.zip"
    with zipfile.ZipFile(BUNDLE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as _archive:
        for _file in sorted(EVIDENCE_DIR.rglob("*")):
            if _file.is_file():
                _archive.write(_file, _file.relative_to(EVIDENCE_DIR))
    mo.md("Original manifests, per-step metrics, commands, versions and hashes are packaged.")

    return (BUNDLE_PATH,)


@app.cell(hide_code=True)
def next_steps():
    mo.md(r"""
    ## What comes next?

    All selected checks must finish with finite losses and the expected step count.
    Every result here is explicitly a **smoke result**, using synthetic text.

    A full attention comparison requires the approved real data and runtime settings,
    2,048-token contexts, batch 8, 1,221 steps within 90 minutes, and three independent
    seeds per design. The course permits an owner's GPU when it meets that budget.
    Those full runs have not been launched here.

    Use the evidence archive in the compute request or the approved local-run handoff.
    Keep downloaded tokenizers, run outputs, archives and rendered reports out of Git.
    """)
    return


@app.cell
def downloads(BUNDLE_PATH):
    mo.hstack([
        mo.download(
            data=lambda: BUNDLE_PATH.read_bytes(), filename=BUNDLE_PATH.name,
            mimetype="application/zip", label="Download smoke evidence",
        ),
        mo.download(
            data=lambda: Path(mo.notebook_location()).read_bytes(),
            filename="attention_smoke.py", mimetype="text/x-python",
            label="Download notebook source",
        ),
    ])

    return


if __name__ == "__main__":
    app.run()
