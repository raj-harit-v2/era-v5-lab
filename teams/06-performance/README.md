# Team 06-performance

Put your work in a **topic folder**: `teams/06-performance/<topic>/<file>`, for example `teams/06-performance/harness/run.py`.
Team documents named in the week plan (for example `benchmarks_v1.md`) may sit directly in the team folder. The team lead decides the topic names. Do not make personal folders. Do not make new folders under `teams/`.
Open a pull request; the lead reviews and merges it. The pr-guard check must pass.

## What this is

Performance work for the lab model: a harness that times every part of the training step, a correctness framework
that proves fast code gives the right result, and the measured baselines. Everything is driven by config: a new
model is a new YAML file in `configs/`, not new code.

## The lab model (`configs/base.yaml`)

| Part | Setting |
|---|---|
| Data | FineWeb sample-10BT retokenized with [BrahmicTokenizer-131K](https://github.com/theschoolofai/BrahmicTokenizer-131K) (131,072 IDs), random 256-token windows |
| Embedding | Kronecker Embedding v2 (G4's raw byte table, `models/ke2.py`), untied head |
| Attention | 8 heads, width 256, eager; GQA via `model.n_kv_head`; learned positions or `model.position=rope` |
| FFN | Dense GELU MLP (256 -> 1024 -> 256); `model.activation=swiglu`; `model.ffn=moe`: 1 shared + top-2 of 8 routed |
| Stack | Reversible midpoint, 6 layers, pre-LN inside `f` |
| Optimizer | `polar_muon_adamw`: Polar Express Muon on 2D block weights, AdamW on the rest |
| MTP | Off; `model.mtp=true` adds a second head on token t+2 |

`configs/tiny_cpu.yaml` is the same model shrunk for a laptop. The plain NanoGPT comparison is
`model.embedding=table model.reversible=false optim.name=adamw`. Every switch and the region it changes is in
[`docs/PARTS.md`](docs/PARTS.md); the `ce_impl` variants are in [`docs/LINEAR_CE.md`](docs/LINEAR_CE.md).

`model.ce_impl=triton_ce` selects the in-repo Triton CE reduction kernel. Existing `torch`, `chunked`, `fused`, `fused_cached`, `fused_liger`, and `fused_cce` values remain available for comparison; the last two are PyTorch references inspired by upstream algorithms. See [`docs/LINEAR_CE.md`](docs/LINEAR_CE.md) for A100/H100 correctness checks and matched benchmark commands.

For `triton_ce`, `model.ce_triton_backward=auto` chooses vocabulary or token streaming to accumulate the smaller gradient. Vocabulary streaming writes each weight-gradient slice once. `ce_triton_scratch_mb=64` caps derivative and forward-statistics scratch separately; token/vocabulary chunk limits control the launch/memory tradeoff. FP16 gradient products stay fp32 and mean/loss scaling happens after accumulation. The earlier `chunked` and `recompute` paths remain selectable. Debug target validation is explicit because it synchronizes the GPU. See the CE docs for precision controls, isolated kernel regions, and server timing commands; no speedup is established yet.

`model.ln_impl=torch_ln|triton_ln` selects PyTorch LayerNorm (default) or the in-repo Triton version for both pre-LN block norms and `ln_f`. The Triton module falls back to PyTorch for unsupported inputs; `meta.layer_norm` and printed notes identify each resolved backend. Its deterministic backward scratch is bounded by GPU SM count and skips frozen parameter gradients. Level-3 timing records `fwd:blockN.ln1`, `fwd:blockN.ln2`, `fwd:head+loss.ln_f`, and the eager backward stages `bwd:ln.triton.rows` / `bwd:ln.triton.params`. See [`docs/LAYER_NORM.md`](docs/LAYER_NORM.md) for correctness and benchmark commands.

## Folder layout

```
configs/       base.yaml (every setting; the default of bench, smoke and the tests), tiny_cpu.yaml, batch32.yaml
models/        config.py, gpt.py, linear_ce.py, ke1.py, ke2.py, moe.py, reversible.py, optim.py
dataio/        tokenizer.py (pinned BrahmicTokenizer-131K), prepare_fineweb.py, loader.py
perfkit/       regions.py, timer.py, bench.py, parts.py, part_ops.py, metrics.py, mfu_fixture.py, events.py, report.py,
               roofline.py, schema.py, smoke.py, requirements.txt
correctness/   framework.py, conftest.py and the test files
results/       README.md (index of every result, with GPU and commit) and the result pages; runs/ is bench output
               (shared as gists; committed only when a result page links to it, see results/README.md)
docs/          PARTS.md (every part we time, timing rules, switches), METRICS.md (MFU / HFU and system metrics),
               G8_HANDOFF.md (the contract with G8), LINEAR_CE.md (the ce_impl variants), ROOFLINE.md (estimator)
```

Each file's docstring says what it does; the run JSON format is `REQUIRED` in `perfkit/schema.py`.

## Status

- **Gate 1 done:** harness, correctness framework and pairs, metrics, report, and the A100 baseline
  ([`results/baseline_v0.md`](results/baseline_v0.md): 42.9 ms per step, 95,400 tokens/s, MFU 7.6%, commit
  `f1ed7f2`), with the five slowest parts ([`results/slowest5_v0.md`](results/slowest5_v0.md)).
- **Week 2:** see [`results/README.md`](results/README.md) (repeat check on other hosts, speed v1, head + loss).
- **Left:**
  1. G5's configs as `configs/g5_*.yaml`.
  2. The MoE all-to-all timed on 2+ GPUs (`torchrun ... --modes comm model.ffn=moe`).
  3. A `@pair` test of `muon_impl=batched`, `adamw_impl=foreach` and `data.prefetch` against the loop reference.
  4. Server A/B of `model.moe.dispatch=sorted` before it becomes the default (it gives idle experts zero
     gradients, not None).
  5. Time and token goodput.
  6. A multi-process (DDP) optimizer test: the optimizers are single-process only, not tested under DDP or sharding.

## How to run

Every command runs from `teams/06-performance/` and reads `configs/base.yaml`; add `key=value` overrides for any of
its keys (an unknown key is an error). Give the GPU name and commit with every timing you share.

```bash
# 1. Install (laptop: in a venv outside the repo). Colab has torch: pip install -q tokenizers datasets pyyaml pytest
pip install -r perfkit/requirements.txt

# 2. Tests (CPU is fine): only what base.yaml selects, or every test with --all-configs
python -m pytest correctness -q -rs
python -m pytest correctness -q -rs --all-configs

# 3. Data: FineWeb sample-10BT with the pinned tokenizer (val + 1 train shard, 1M tokens each, ~8 MB)
python -m dataio.prepare_fineweb

# 4. Smoke test: does the config build, train and run at a sane speed?
python -m perfkit.smoke
python -m perfkit.smoke --config configs/tiny_cpu.yaml

# 5. Bench + 5% repeat check: two runs, each in its own process
python -m perfkit.bench --level 3 --repeat 2 --tag normal_rep; echo "exit=$?"
python -m perfkit.bench --level 3 --repeat 2 --tag mtp_rep model.mtp=true; echo "exit=$?"

# 6. A/B of an implementation switch against an earlier run
python -m perfkit.bench --level 3 --against results/runs/<torch-tag>.json model.ce_impl=fused
```

Exit codes: 0 ok, 1 run JSON incomplete, 2 a part outside the 5% rule, 3 out of GPU memory (add
`model.ce_impl=chunked` or lower `run.batch_size`), 4 no data (run step 3, or add `data.source=synthetic`).

**Tokenizer and data.** `tokenizer.json` comes only from the source repo at commit
`7dfcf398172c825c6689ad578e8b484ca5f57bc9`, SHA-256 checked, never from Hugging Face. It and the uint32 shards
are cached in `~/.cache/era-perf/` (`data.dir`); bench's traces and checkpoints too (`ERA_PERF_CACHE` moves those).
Offline: `data.tokenizer_path=<path>` (tests: `BRAHMIC_TOKENIZER_PATH`).

**Batch size.** `run.batch_size` is 16 in `base.yaml`; use 8 on a T4 / P100 / V100. `configs/batch32.yaml` is the
same model at B=32 (A100 / L4 / H100), LR unchanged. `run.dtype: bf16` on a GPU
without native bf16 runs fp16 + GradScaler.

**A good smoke run:** reconstruction error below 1e-3, loss starting near ln(131072) = 11.78 and falling, p10 / p90
within a few % of the median, all weights finite. Reference (A100-SXM4-40GB, bf16, B=16, commit `f1ed7f2`):
46.2 ms/step, 88,700 tokens/s, 6.5 GB peak. Smoke numbers are not the baseline: those come from bench.

**The 5% rule.** Two runs of the same code, GPU and config are compared part by part (the step, every part at
level <= `report.gate_level`, checkpoint save, the measured all-to-all). A part passes within 5% (slower / faster -
1, `report.tol_pct`) or less than 0.05 ms apart (`report.abs_tol_ms`). Compare runs of at least 100 steps. Read the
`[warn]` lines: a dirty tree, the wrong vocabulary, recorder overhead above 2%, a spread above 10% or a throttled
GPU make the numbers not count.

**Run files.** Each run writes `results/runs/<tag>.json`, `<tag>.md`, the live `<tag>.jsonl` and, with layer +
trace modes, one small trace per slowest part in `<tag>_parts/`. Full profiler traces stay in
`~/.cache/era-perf/traces/`. `python -m perfkit.report b.json --compare a.json` rebuilds the comparison.

**Colab** (GPU runtime): clone, `git checkout g6/dev`, `%cd teams/06-performance` (not `!cd`), then run the steps
above with `!` in front. Colab deletes `/content` and the data cache when the session ends.
