# Team 06-performance

Put your work in a **topic folder**: `teams/06-performance/<topic>/<file>`, for example `teams/06-performance/harness/run.py`.
Team documents named in the week plan (for example `benchmarks_v1.md`) may sit directly in the team folder. The team lead decides the topic names. Do not make personal folders. Do not make new folders under `teams/`.
Open a pull request; the lead reviews and merges it. The pr-guard check must pass.

## What this is

Week-1 performance work for the lab model: a timing harness that times every part of the training step,
a correctness framework that proves fast code gives the right result, and the first baseline.
Everything is driven by config: a new model is a new YAML file in `configs/`, not new code.

## The lab model (`configs/base.yaml`)

| Part | Setting |
|---|---|
| Data | Raw FineWeb sample-10BT retokenized with BrahmicTokenizer-131K, random 256-token windows (`model.block_size`), next batch prefetched after backward (`data.prefetch`) |
| Tokenizer | [BrahmicTokenizer-131K source repo](https://github.com/theschoolofai/BrahmicTokenizer-131K), exactly 131,072 IDs |
| Embedding | Kronecker Embedding v2 (G4 raw byte table, `models/ke2.py`): fixed code (256 x 32 = 8192) + `Linear(8192 -> 256)`, computed as one `embedding_bag`; untied head |
| Attention | 8 heads, width 256, eager (explicit softmax, `model.attn_impl`); GQA via `model.n_kv_head` |
| FFN | Dense MLP (256 -> 1024 -> 256), GELU; `model.activation=swiglu`: SiLU(gate) * up, 3 matrices, no biases. MoE (`model.ffn=moe`): 1 shared + top-2 of 8 routed experts, bias balancing, fp32 router; the experts use the same activation |
| Stack | Reversible midpoint, 6 layers, pre-LN inside `f`; the backward rebuilds each layer's input |
| Optimizer | `polar_muon_adamw`: Polar Express Muon on 2D block weights (`muon_impl: batched`), AdamW on embedding parameters (including the KE projection), output head, norm gains and biases (`adamw_impl: foreach`) |
| MTP | Off; `model.mtp=true` adds a second untied head on token t+2 (G5 config_v0) |
| Size | Reported from the selected config at runtime with the full 131,072-token vocabulary |

`configs/base.yaml` is the only model config; G5's configs will be new YAML files that inherit it.
`configs/tiny_cpu.yaml` is the same model shrunk for a laptop. The plain NanoGPT comparison is
`model.embedding=table model.reversible=false optim.name=adamw`.

`optim.name=polar_muon_adamw` (the default) is a single-process combined optimizer using Polar Express Muon + AdamW updates (including row equilibration, Muon+ norm correction, variance reduction, and cautious Muon decay). `optim.name=muon` is the earlier Muon + AdamW hybrid. Both use ordinary PyTorch ops; fused kernels, distributed collectives, and sharded optimizer state are not integrated.

`model.moe.dispatch=loop|sorted` selects the reference per-expert gather or the sorted dispatch. The sorted path orders token/expert assignments, packs them into a padded per-expert buffer and runs each expert MLP as one batched matmul. Its scatters and gathers use unique indices, so gradients are bit-identical across runs on CUDA. It reads back only the largest per-expert route count (one host sync per layer call). For an idle expert it produces zero gradient tensors where the loop leaves gradients as `None`; this can change optimizer-state updates, so `loop` remains the default pending an optimizer-safe treatment and server benchmark. Run the dispatch checks with `python -m pytest correctness/test_moe.py -q`.

`optim.muon_impl=loop|batched` selects the per-matrix Muon reference or the shape-batched path (default `batched`: same-shaped matrices are stacked and updated at once, for `muon` and `polar_muon_adamw`). `optim.adamw_impl=loop|foreach` does the same for the AdamW part of `polar_muon_adamw` (default `foreach`: `torch._foreach` multi-tensor ops). `data.prefetch=true|false` samples, checks and pins the next batch after backward is queued (default `true`; the same batches either way).

## Folder layout

```
configs/       base.yaml (every setting; the default config of bench, smoke and test_model.py), tiny_cpu.yaml
models/        config.py, gpt.py, ke1.py, ke2.py, moe.py, reversible.py, optim.py
dataio/        tokenizer.py (pinned BrahmicTokenizer-131K), prepare_fineweb.py, loader.py
perfkit/       regions.py, timer.py, bench.py, parts.py, metrics.py, events.py, report.py, roofline.py, schema.py, smoke.py
correctness/   framework.py, conftest.py and the test files
results/       README.md, baseline_v0.md, slowest5_v0.md; runs/ is bench output (not committed, shared as gists)
docs/          PLAN.md (interfaces, what is done and left), PARTS.md (every part we time),
               METRICS.md (MFU / HFU and system metrics, for G8), ROOFLINE.md (analytical estimator)
```

## Status

- **Done for Gate 1:** the lab model and data pipeline on the Brahmic vocabulary; the step timer, event recorders
  and bench (`perfkit/timer.py`, `perfkit/bench.py`) with clean, layer, trace, checkpoint and comm modes, a small
  trace per slowest part (`perfkit/parts.py`), GPU system metrics and the live JSONL sidecar for G8; `--repeat`
  with each run in its own process; metrics and MFU (`perfkit/metrics.py`, `docs/METRICS.md`); the report and
  5% comparison with the 0.05 ms floor (`perfkit/report.py`); the correctness framework with the 1.01 drill and
  determinism check, and test pairs for attention, KE1, KE2, MoE (both dispatches), reversible, chunked loss and
  the whole model (fp32 and bf16, with and without MTP); tests for the timer, bench, events, part traces, report,
  roofline, optimizer and tokenizer; the roofline estimator (`perfkit/roofline.py`).
- **Baseline v0 (A100-SXM4-40GB, commit `f1ed7f2`, `configs/base.yaml`):** 42.9 ms per step, 95,400 tokens/s,
  MFU 7.6%; two runs agree within 0.5% on every gated part except `data` (3.85%, 0.001 ms apart), and the MTP pair
  within 0.4% ([`results/baseline_v0.md`](results/baseline_v0.md)). The five slowest parts, each with a trace and
  a week-2 idea: [`results/slowest5_v0.md`](results/slowest5_v0.md).
- **Left:** G5's configs (`configs/g5_*.yaml`), the MoE all-to-all timed on 2 GPUs (`torchrun`,
  `model.ffn=moe`), a `@pair` test for the batched / foreach optimizer paths against the loop reference, the 5%
  check on hosts other than Colab (the CPU-paced parts move on Modal, checkpoint save on Windows), time and token
  goodput.

**Distributed optimizer follow-up:** the current Muon/AdamW implementation is local-process only. A DDP integration is implementable follow-up work: make parameter selection robust to the DDP `module.` prefix (or build from the unwrapped module), handle MoE experts unused on a rank, and add a multi-process correctness/smoke test. The current optimizer should not be treated as tested for DDP or ZeRO-style sharding.

The full table is in [`docs/PLAN.md`](docs/PLAN.md) section 3. Every part we time is in [`docs/PARTS.md`](docs/PARTS.md).

## Quick start (main steps)

Every command runs from `teams/06-performance/` and reads `configs/base.yaml`: change the model, batch, sequence
length or bench settings there, or add `key=value` overrides (an unknown key is an error). On Colab, put `!` in
front of each command; torch is already installed there, do not reinstall it.

```bash
# 1. Install (laptop: inside a venv)
pip install -q tokenizers datasets pyyaml pytest numpy

# 2. Correctness: only the tests for what base.yaml selects (add --all-configs to run every test, e.g. Gate 1)
python -m pytest correctness -q -rs

# 3. Real data: FineWeb sample-10BT retokenized with BrahmicTokenizer-131K (val + 1 train shard, 1M tokens each)
python -m dataio.prepare_fineweb

# 4. Smoke test: does base.yaml build, train and run at a sane speed?
python -m perfkit.smoke

# 5. Benchmark + 5% repeat check, normal run (base.yaml as it is): two runs, exit 0 = PASS, 2 = a part outside
python -m perfkit.bench --level 3 --repeat 2 --tag normal_rep; echo "exit=$?"

# 6. Benchmark + 5% repeat check, MTP run (second head on token t+2)
python -m perfkit.bench --level 3 --repeat 2 --tag mtp_rep model.mtp=true; echo "exit=$?"

# 7. Colab only: download the results
# !zip -qr /content/results.zip results/runs
# from google.colab import files; files.download("/content/results.zip")
```

Exit codes: 0 ok, 1 run JSON incomplete, 2 a part outside the 5% rule (see "The 5% rule" below), 3 out of GPU memory (add
`model.ce_impl=chunked` or lower `run.batch_size`), 4 no data (run step 3). The sections below explain each step.

## How to run

Every command runs from `teams/06-performance/`. Give the GPU name with every timing you share.

**1. Get the code**

```bash
git clone <REPO_URL> era-v5-lab          # the URL of the integration branch is posted in the G6 group
cd era-v5-lab && git checkout g6/dev && cd teams/06-performance
```

**2. Install.** Laptop (venv outside the repo): `python -m venv ~/.venvs/g6 && source ~/.venvs/g6/bin/activate`,
then `pip install -r perfkit/requirements.txt`. Colab (torch is already installed, do not reinstall it):
`pip install -q tokenizers datasets pyyaml pytest`.

**3. Tests** (CPU is fine)

```bash
python -m pytest correctness -q -rs              # only what configs/base.yaml uses (the rest is deselected)
python -m pytest correctness -q -rs --all-configs  # every test, every choice (Gate 1)
```

A test that hits an unfinished stub is SKIPPED and named; at Gate 1 no stub skip may be left. Some tests skip
for hardware reasons (CUDA only, CUDA bf16, torch >= 2.5 for GQA SDPA, not on Windows); those are expected on a
laptop. The tokenizer tests need `tokenizer.json`: the pinned download, or `BRAHMIC_TOKENIZER_PATH` (step 4).

**4. Tokenizer and data:** the tokenizer is loaded exclusively from `tokenizer.json` in the
[source repo](https://github.com/theschoolofai/BrahmicTokenizer-131K), pinned to commit
`7dfcf398172c825c6689ad578e8b484ca5f57bc9` and verified by SHA-256. It is never loaded from
Hugging Face. The default downloads that GitHub file into `~/.cache/era-perf/BrahmicTokenizer-131K/`.
For an offline run, clone the source repo and set `data.tokenizer_path=/path/to/BrahmicTokenizer-131K/tokenizer.json`.
Tests accept the same path via `BRAHMIC_TOKENIZER_PATH`.

Data preparation streams raw text from FineWeb sample-10BT and encodes it with that artifact.
New shards use uint32 (IDs exceed 65,535) and a tokenizer metadata manifest. Existing GPT-2 shards
are incompatible and must be prepared again. Data stays outside git, by default in
`~/.cache/era-perf/fineweb-brahmic131k/`.

```bash
python -m dataio.prepare_fineweb                 # val + 1 train shard, 1M tokens each (~8 MB total)
# Offline tokenizer: append --tokenizer-path /path/to/source-checkout/tokenizer.json
```

For a quick check without FineWeb, add `data.source=synthetic`. Synthetic runs still use the
real Brahmic vocabulary and KE byte table, including special tokens and raw partial UTF-8 bytes.

**5. Smoke test the model** (not the baseline: Gate 1 numbers come from `perfkit.bench` on committed code)

```bash
python -m perfkit.smoke                                      # configs/base.yaml
python -m perfkit.smoke model.embedding=table model.reversible=false optim.name=adamw   # plain NanoGPT for comparison
python -m perfkit.smoke --config configs/tiny_cpu.yaml       # laptop, seconds; numbers mean nothing
python -m perfkit.smoke model.ce_impl=chunked                # if out of memory; then lower run.batch_size (8 on a T4)
python -m perfkit.smoke --steps 500 --warmup 0               # longer training run (every step is a real train step)
```

Device, precision, batch and step counts come from the config only (`run.device`, `run.dtype`, `run.batch_size`, `smoke.warmup`, `smoke.steps`), the same keys bench reads. `run.batch_size` is 16 in `base.yaml`; set 8 on a T4 / P100 / V100. `run.dtype: bf16` on a GPU without native bf16 runs fp16 + GradScaler.
`key=value` overrides work for any key of `configs/base.yaml`. A good run: reconstruction error below
1e-3 (`OK`), loss starting at about ln(131072) = 11.78 and falling, p10 / p90 within a few % of the median,
`all weights finite: True`.

**6. Training schedule:** timing runs use a constant learning rate by default. To inspect training
loss with cosine decay and optional linear warmup, add optimizer overrides; schedule duration follows
the run's `--steps` plus timing warmup steps.

```bash
python -m perfkit.smoke --steps 20 --warmup 5 optim.schedule=cosine optim.warmup_steps=3
```

Compare the Polar Express MuonAdamW update with the current hybrid optimizer using the same model and data:

```bash
python -m perfkit.smoke --steps 20 --warmup 5 optim.name=muon
python -m perfkit.smoke --steps 20 --warmup 5 optim.name=polar_muon_adamw
```

Timing results for the Brahmic vocabulary: [`results/baseline_v0.md`](results/baseline_v0.md).

**7. Bench** (per-part timing; Gate 1 numbers come from here, on committed code)

```bash
python -m perfkit.bench --config configs/tiny_cpu.yaml                      # laptop: proves it runs; writes to ~/.cache/era-perf/runs-smoke/
python -m perfkit.bench --config configs/base.yaml --level 3 --tag a                              # first baseline run
python -m perfkit.bench --config configs/base.yaml --level 3 --tag b --against results/runs/a.json # 5% check
torchrun --nproc_per_node 2 -m perfkit.bench --config configs/base.yaml --modes comm model.ffn=moe # 2+ GPUs (base.yaml is dense: no all-to-all without ffn=moe)
```

**The 5% rule (agreed with TSAI, 30 Oct; other teams use the same check).** Two runs of the same code, GPU and
config are compared part by part: the whole step, the step parts and whole blocks (level <= `report.gate_level`),
checkpoint save and the measured all-to-all. A part passes when the two runs are **within 5%**
(`report.tol_pct`; gap = slower / faster - 1) **or differ by less than 0.05 ms** (`report.abs_tol_ms`). The 0.05 ms
floor is there because a very small part (for example `data` at 0.03 ms) can be 10% apart on timer noise alone,
a few microseconds that the GPU timer cannot resolve. Both run times and their difference in ms are reported for
every part, also for the parts that pass on the 0.05 ms rule (marked `ok (< 0.05 ms)`). Each part is the median
over `bench.steps` measured steps; compare runs of at least `report.min_compare_steps` (100) steps, so that small
parts are the median of many calls (bench warns below that). The change column shows (this - other) / other,
the gate uses slower / faster - 1, so very near 5% the two can differ.

Defaults (`configs/base.yaml`, `bench:`): all modes (clean, layer, trace, checkpoint, comm), 100 measured steps
after 10 warmup, 10 checkpoint saves after one warm save that is not counted. B is `run.batch_size` from the config,
never picked from the GPU (16 in `base.yaml`; set 8 on a T4 / P100 / V100);
the run JSON records the B it used, and `--against` refuses two runs with different B. On one GPU the all-to-all
is not timed (its payload is recorded; with `ffn: mlp` there is none); time it under `torchrun` on 2+ GPUs with
`model.ffn=moe` (Kaggle T4 x2). A level-3 run takes about a minute on an A100. Run the two baselines back to back
in one session.

Each run writes `results/runs/<tag>.json` (the format is in `docs/PLAN.md` 2.6; run files are not committed, share
them as a gist), a Markdown report next to it
(`<tag>.md`, from `perfkit.report.render`), and with layer + trace modes one small trace per slowest part in
`results/runs/<tag>_parts/`. It prints the parts at level <= 2 (gated) and the parts inside a block (information
only). Read the `[warn]` lines: a dirty tree, the wrong vocabulary, recorder overhead above 2%, a gated part with
p10..p90 spread above 10% or a throttled GPU make the numbers not count. Exit codes: 0 ok, 1 run JSON incomplete,
2 `--against` / `--repeat` found a part outside 5%, 3 out of GPU memory, 4 no data (prepare it, or add
`data.source=synthetic`). The checkpoint files go to `~/.cache/era-perf/ckpt/` and are deleted after; set
`ERA_PERF_CACHE` to move the cache.

Build the report files from two run JSONs (writes `<run>.md` next to the first JSON; exit code 2 on a FAIL):

```bash
python -m perfkit.report results/runs/b.json --compare results/runs/a.json --baseline /tmp/baseline.md --slowest /tmp/slowest5.md
```

The committed `results/baseline_v0.md` and `results/slowest5_v0.md` are hand-written write-ups of the two pairs (normal and MTP),
not this command's output; do not overwrite them. `compare` refuses a pair on different GPUs, commits,
vocabularies, dtypes, batch or sequence sizes, with a dirty tree, or with different model / optimizer / data
config (other than `IMPL_SWITCHES`).

**Colab** (Runtime → Change runtime type → GPU), one cell each so a failing step is easy to see:

```python
!nvidia-smi --query-gpu=name,memory.total --format=csv
!git clone -q <REPO_URL> /content/era-v5-lab
%cd /content/era-v5-lab
!git checkout -q g6/dev
%cd teams/06-performance
!pip install -q tokenizers datasets pyyaml pytest
```
```python
!python -m dataio.prepare_fineweb
```
```python
!python -m pytest correctness -q -rs
```
```python
!python -m perfkit.smoke
```

Reference (smoke, A100-SXM4-40GB, bf16, B=16, commit `f1ed7f2`): 46.2 ms/step, 88,700 tokens/s, peak memory
6.5 GB (mostly the fp32 logits of the 131K vocabulary), loss 11.84 -> 7.67 in 40 steps.
Use `%cd`, not `!cd` (`!cd` changes the folder for that line only). Colab deletes `/content` and the data
cache when the session ends.
