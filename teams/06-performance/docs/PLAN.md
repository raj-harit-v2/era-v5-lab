# G6 week 1 plan

**Week 1: timing harness, correctness framework, first baseline.**

Scope decisions:
- **Lab architecture:** BrahmicTokenizer-131K from its pinned GitHub source, raw FineWeb sample-10BT retokenized to uint32 shards,
  Kronecker Embedding v2 (G4's raw table), eager attention (8 heads; GQA by config), dense MLP (MoE with 1 shared
  + top-2 of 8 routed experts by config), Polar Express Muon + AdamW, reversible midpoint stack with pre-LN inside
  `f` (classic Post-LN cannot be inverted, see `models/gpt.py`), optional MTP head. This is `configs/base.yaml`,
  the only model config (the earlier `lab_small.yaml` was folded into it in PR #29).
- **Model: NanoGPT, driven only by config.** When G5 (Architecture) sends their config details and
  harness, we add **a YAML file, not code**.
- **Embedding:** KE2 (from G4) is the default; KE v1 stays as `model.embedding=ke1`, the table as `table`.
- Lab parts to time: attention, MLP or MoE (top-2 of 8), reversible midpoint stack, KE2 / KE v1, Muon, AdamW,
  checkpoint save, MoE all-to-all.

---

## 1. Gate 1: what we must deliver

| Deliverable | File |
|---|---|
| Timing harness | `perfkit/timer.py`, `perfkit/bench.py` |
| Correctness framework + test pairs | `correctness/framework.py`, `test_ke.py`, `test_attention.py`, `test_moe.py`, `test_reversible.py` |
| Baseline with GPU name and commit ID | `results/baseline_v0.md` |
| Five slowest parts, each with a trace and one week-2 idea | `results/slowest5_v0.md` |
| System metrics + MFU method to G8 | `docs/METRICS.md` + hand-off meeting |

Gate 1 checks:
1. `pytest teams/06-performance/correctness -q` gives 0 failures.
2. The lead multiplies one fast output by 1.01, and a test fails.
3. Two baseline runs agree within 5% for each part.

---

## 2. Step 0: freeze the interfaces

One skeleton PR: folders, the interfaces below, the lab model, stubs with their signatures, these rules.
After it, every module is built against the interfaces, never against another module's internals,
so modules can be built in parallel and in any order.

### 2.1 Folder layout

```
teams/06-performance/
  configs/        base.yaml, tiny_cpu.yaml
  models/         config.py, gpt.py, moe.py, reversible.py, ke1.py, ke2.py, optim.py
  dataio/         tokenizer.py, prepare_fineweb.py, loader.py
  perfkit/        timer.py, regions.py, bench.py, parts.py, metrics.py, events.py, report.py, roofline.py, schema.py, smoke.py
  correctness/    conftest.py, framework.py, test_framework.py,
                  test pairs: test_attention.py, test_ke.py, test_ke2.py, test_moe.py, test_reversible.py, test_ce.py, test_model.py
                  harness: test_timer.py, test_bench.py, test_events.py, test_parts.py, test_report.py, test_roofline.py
                  optimizer and data: test_optimizer.py (includes tokenizer + KE integration), test_tokenizer.py
                  metrics: test_metrics.py
  results/        README.md, baseline_v0.md, slowest5_v0.md, runs/ (bench output, not committed)
  docs/           PLAN.md, PARTS.md, METRICS.md, ROOFLINE.md
```

Shared files (`config.py`, `regions.py`, `schema.py`, the `framework.py` registry)
are interfaces: change them only with the whole team agreeing.

### 2.2 Model config (`models/config.py`)

```python
@dataclass
class ModelConfig:
    vocab_size: int = 131072     # exact BrahmicTokenizer-131K vocabulary
    block_size: int = 512        # sequence length (base.yaml: 256)
    n_layer: int = 9             # base.yaml: 6
    n_head: int = 8
    n_kv_head: int = None        # GQA; None = n_head
    n_embd: int = 256
    attn_impl: str = "sdpa"      # sdpa | eager (explicit softmax; base.yaml: eager)
    mlp_ratio: int = 4
    activation: str = "gelu"    # gelu | swiglu (SiLU(c_gate x) * c_fc x -> c_proj, no biases): MLP + all experts
    embedding: str = "table"     # table (tied head) | ke1 | ke2 (untied head; base.yaml: ke2)
    ke_max_pos: int = 32         # KE: 256 bytes x 32 positions = 8192-dim code
    ke_mode: str = "dynamic"     # KE v1: dynamic (codec every step) | cached (V x D table)
    ffn: str = "mlp"             # mlp | moe
    moe: dict = {num_experts: 8, top_k: 2, num_shared: 0, bias_gamma: 0.01, dispatch: "loop"}
                                 # lab: num_shared 1; dispatch: loop | sorted; unknown keys fail
    reversible: bool = False     # True: midpoint stack
    rev_h: float = 1.0           # midpoint step size
    ce_impl: str = "torch"       # torch (full fp32 logits) | chunked (ce_chunks pieces, checkpointed)
    ce_chunks: int = 8
    mtp: bool = False            # True: second untied head on token t+2; loss = ntp + mtp
```

The dataclass defaults are the plain model; `configs/base.yaml` sets the lab values.

- YAML files with `inherit: base.yaml`. Command-line overrides: `model.n_layer=4 run.batch_size=16`.
- **Rule:** no number about the model is hard-coded anywhere else. Everything reads `cfg`.
- G5's config later = a new `configs/g5_*.yaml`. If G5 has a field we lack, add it to `ModelConfig` with a default.

### 2.3 Model (`models/gpt.py`)

```python
model = GPT(cfg, token_bytes=None)            # token_bytes only for embedding=ke1
logits, loss = model(idx, targets)            # idx, targets: [B, T] int64
total, active = model.param_counts()          # active = what one token multiplies with (for MFU)
model.moe_layers()                            # list of MoE modules (bias update after each step)
```

### 2.4 Timing markers (`perfkit/regions.py`)

```python
with region("block3.attn", level=2):  ...     # a named piece of work
x = mark(x, "block3")                         # backward boundary: when grad reaches x
with phase("bwd.recompute"):  ...             # prefix, so recompute is not counted as forward
```

- Names: `<phase>:<part>`, e.g. `fwd:block3.attn.qkv`, `bwd:head+loss`, `opt:opt.muon`.
- Levels: 1 = phases (data, fwd, bwd, opt). 2 = per layer and big parts (embed, blockN, head+loss, optimizer).
  3 = inside a layer (qkv, sdpa, router, each expert).
- **When timing is off, `region` returns a shared do-nothing context and `mark` returns its input.**
  The model code keeps its markers forever.

### 2.5 Timing rules

1. CUDA events only. **No `synchronize`, `.item()` or `print` inside a timed step.** Read events after the steps.
2. Warmup steps first (default 10). Then measure (default 100 steps, `report.min_compare_steps`: with 50, small parts drifted between runs).
3. Report median, p10, p90, IQR. Never the mean. (`timer.stats()` also stores min, max, mean, std and
   `spread_pct` = (p90 - p10) / median, for information; a gated part with spread above 10% gets a warning.)
4. Measure the overhead: steps alternate timing on and off. Above 2%, the numbers are flagged.

### 2.6 Run JSON (written by bench, read by report and G8)

```
meta:      gpu, gpu_spec, torch, cuda, driver, device, commit, dirty, config_file, overrides, tag, time
           [reconstruction_err]                                  cuda / driver are None on CPU
           [run_id, node_id, events_jsonl, dtype, dtype_requested, notes, batch_size, seq_len, tokens_per_step, vocab_size, data_source,
            tokenizer {name, revision, sha256, vocab_size}, lr_schedule, python, bench_version, timing,
            loss_after_first_step, loss_end, compute_capability, sm_count, gpu_mem_gb, gpu_count,
            gpu_index, gpu_uuid, gpu_pci_bus_id,
            telemetry_start, telemetry {after_warmup, during_steps, end}]
config:    run, data, model, optim, bench                        the full merged config
clean:     step_ms {median,p10,p90,iqr,n}, data_ms {median,p10,p90,iqr,n}
           [raw_step_ms, events_created_during_steps]
layer:     level, overhead_pct, step_ms, step_ms_recorder_off,
           regions { "<phase>:<name>": {median,p10,p90,iqr,n,level,calls_per_step} }
                   [each region: min, max, mean, std, spread_pct, pass]
           [data_host_ms, data_note, events_per_step, steps, events_created_during_steps,
            events_created_while_measuring,
            inner_pass {level, overhead_pct, step_ms, step_ms_recorder_off, events_per_step,
                        events_created_during_steps, events_created_while_measuring}]
trace:     trace_file, top_ops, gpu_busy_pct, kernels_per_step
           [steps, host_syncs_per_step, sync_sites, parts_note,
            parts [{part, ms, pct, instances, level, region, file, bytes, calls_in_step, calls_kept, stride,
                    gpu_events}]]
[system]:  source, interval_ms, during, samples,                 CUDA only, sampled through the clean steps
           metrics {gpu_util_pct, mem_util_pct, mem_used_mib, sm_clock_mhz, mem_clock_mhz, power_w, temp_c:
                    {min, median, max, mean}}  [slowdown_samples, slowdown_reasons]
[JSONL]:  versioned live gpu_sample per GPU sample and step_timing per clean step; run_id, node_id,
          GPU UUID/PCI bus ID or rank/local_rank, timestamp, step, raw sample metrics or data_ms/raw_step_ms
metrics:   tokens_per_step, tokens_per_s, mfu, hfu, mfu_unavailable_reason, hfu_unavailable_reason,
           params_total, params_active, model_flops_per_token, peak_tflops
[memory]:  peak_allocated_gb, peak_reserved_gb (GiB despite `_gb` names), unit=GiB, gpu {name,index,uuid,pci_bus_id}
[goodput]: badput_s {startup, first_step, warmup}                [time_goodput, token_goodput_per_s: to write]
[checkpoint]: save_ms, to_cpu_ms, write_ms {stats}, size_mb, write_mb_per_s, level, repeats,
              discarded_first, pinned, where
[comm]:    moe_a2a {bytes_per_call, payload_mb_per_call, payload_dtype, calls_per_layer, calls_per_step, dtype,
           level, measured, [reason] | [world_size, backend, per_call_ms, per_call_ms_slowest_rank,
           per_step_ms, events_created_during_steps (max across ranks), note]}
[warnings]: ["..."]                                               rule checks and noisy parts, in words
```

`perfkit/schema.py` (`REQUIRED`, `REGION_KEYS`) is the source of truth; this is a copy. `[...]` = optional.
meta, config, clean and metrics are always there; layer and trace only when that mode ran; system only on CUDA.
`bwd:stack` is the whole stack backward in both stacks, like `fwd:stack` (`perfkit/bench.py` step 6).
New fields can be added; existing ones are not renamed without telling the team and G8.

### 2.7 Test pair (`correctness/framework.py`)

```python
@pair("moe.loop", tol=1e-4)
def _(device):
    ...
    return Case(ref=ref_fn, fast=fast_fn, inputs=[x], params_ref=[...], params_fast=[...])
```

- The reference is written **independently** from the definition, in fp64. Never by calling the fast code.
- Error = `||fast - ref|| / ||ref||` on outputs and gradients. (Do not use `torch.allclose` defaults: in bf16
  they let a 1% error pass.)
- Tolerance per dtype (`TOLERANCES` in `framework.py`, measured on the full lab model): fp32 outputs 1e-5,
  gradients 5e-5; bf16 outputs 1e-2, gradients 3e-2; fp8 is measured and added when an fp8 path exists.
  fp32 tolerances are below 1e-2 always.
- `test_framework.py` multiplies every fp32 pair's fast output by 1.01 and expects a failure (a bf16 tolerance
  cannot see a 1% error, so bf16 pairs are not in this drill).
- Each pair's worst error is printed at the end of every pytest run (`conftest.py`).

---

### 2.8 The skeleton (what step 0 ships)

Interfaces: `models/config.py`, `perfkit/regions.py` (the API; the recorders were stubs, now in `perfkit/timer.py`), `perfkit/schema.py`
(run JSON + `example_run()`), `correctness/framework.py` (the pair registry; the checks were stubs),
`correctness/conftest.py`.

The lab model, so it runs end to end from day one (MVPs, verified against fp64 references and on an A100):
`models/gpt.py` (GQA, pre-LN, MoE / KE / reversible plug in), `models/ke1.py` (ported from
theschoolofai/kronecker-embeddings), `models/moe.py`, `models/reversible.py`, `models/optim.py` (Muon),
`dataio/loader.py`, `dataio/prepare_fineweb.py`, `perfkit/smoke.py`.

Every other file is a stub: the right signatures, a docstring with the MVP, extras and
"done when". Calling a stub raises `NotImplementedError`, and `correctness/conftest.py` reports such a
test as **skipped** (named, with `-rs`), not failed. So tests can be written before the code they test, and
a module's tests start running the moment it is written. At Gate 1 no stub skip may be left. (Today no stub
is left. Some tests skip for hardware reasons: they need CUDA,
CUDA bf16, torch >= 2.5 for SDPA `enable_gqa`, or a non-Windows OS. Those skips are expected on a laptop.)

## 3. What we have, and what is left

Status "Stub": the file raises `NotImplementedError`. Its docstring has the full MVP, the extras and "done when".

### Model and data

| File | Role | Status |
|---|---|---|
| `configs/*.yaml` | `base` (every setting; the lab model), `tiny_cpu` (laptop) | Implemented |
| `models/config.py` | `ModelConfig`, YAML with `inherit:`, `key=value` overrides; unknown or bad keys fail early | Implemented |
| `models/gpt.py` | GQA attention, pre-LN blocks, plain or reversible stack, untied head for KE, `ce_impl` torch / chunked loss (both average over non-ignored targets) | Verified against fp64 references and on an A100 |
| `models/ke1.py` | Kronecker Embedding v1 (ported from theschoolofai/kronecker-embeddings), `ke_mode` dynamic and cached, Brahmic source vocabulary byte table | Bit-identical to the upstream package |
| `models/ke2.py` | Kronecker Embedding v2 on G4's raw byte table (`teams/04-ke2`), one `embedding_bag` over the support columns plus a row sum; the per-token tables are built once at init | Verified against G4's fp64 dense encoder (`test_ke2.py`) |
| `models/moe.py` | 1 shared + top-2 of 8 routed experts, fp32 router, bias balancing, routing replay; `DISPATCH` = `loop` (reference, default) and `sorted` (padded per-expert batched matmul, one host sync per call) | Both dispatches verified against a token-by-token fp64 reference |
| `models/reversible.py` | Midpoint stack, custom backward (invert, recompute, local backward), `reconstruction_error` | Exact in fp64; bf16 reconstruction 2.5e-4 on an A100 |
| `models/optim.py` | `adamw`; `muon` = Muon (2D block weights including routers) + AdamW (embedding parameters, head, norm gains, biases); `polar_muon_adamw` (Polar Express Muon + AdamW, single process, the default); `muon_impl` loop / batched (default batched); `adamw_impl` loop / foreach for `polar_muon_adamw` (default foreach); Newton-Schulz FLOPs; constant / cosine LR schedule | Implemented; tested in `test_optimizer.py`. No `@pair` test yet of the batched / foreach paths against the loop reference. Local process only, not tested under DDP or sharding |
| `dataio/tokenizer.py` | BrahmicTokenizer-131K `tokenizer.json` from the pinned GitHub commit, SHA-256 checked, never from the Hub | Implemented; `test_tokenizer.py` |
| `dataio/prepare_fineweb.py` | Retokenizes raw FineWeb sample-10BT with the pinned tokenizer; uint32 shards with a header and manifest | Used for the A100 baseline |
| `dataio/loader.py` | Random windows from the shards (or synthetic), pinned copy, KE byte table; `data.prefetch` samples the next batch after backward is queued | Used for the A100 baseline |

### Timing harness

| File | Role | Status |
|---|---|---|
| `perfkit/regions.py` (API) | `region(name, level)` marks a piece of work. `mark(x, name)` marks where the backward reaches a tensor. `phase("bwd.recompute")` prefixes names. `point(name)` records one instant (bench puts `__bwd_start__` / `__bwd_end__` around the backward). When timing is off, these cost nothing. | Implemented |
| Markers in the model | `gpt.py`, `moe.py`, `ke1.py`, `reversible.py`, `optim.py` call `region` and `mark` with the names in `PARTS.md` | In place |
| `perfkit/timer.py` | `StepTimer` (CUDA event pair per step), `EventPool` (events made before the measured steps), `EventRecorder`, `ProfilerRecorder`, `Buckets` (badput wall clock), `stats()`, `sync()`, backward segments from `mark()` points, per-part aggregation, paired overhead, kernel summary, host-sync count | Implemented; `test_timer.py` |
| `perfkit/bench.py` | The command-line tool: clean, layer, trace, checkpoint and comm modes, `--repeat N` (each run in its own process), `--against` 5% check with A/B labelling, rule checks and warnings, exit codes 0 to 4 | Implemented; `test_bench.py` on CPU; A100 baseline from it |
| `perfkit/parts.py` | The five slowest parts from the layer regions and one small Chrome trace per part, cut from the full trace | Implemented; `test_parts.py` |
| `perfkit/schema.py` | The run JSON format, with `validate_run` and `example_run` | Implemented |
| `perfkit/metrics.py` | MFU, HFU (with unavailable reasons), peak TFLOPS table, memory, `GpuSampler` (nvidia-smi through the clean steps, every visible GPU), telemetry and slowdown reasons, run metadata, commit and dirty tree | Implemented. Still to write: time and token goodput |
| `perfkit/events.py` | Live JSONL sidecar for G8: `gpu_sample` and `step_timing` events, written off the training thread | Implemented; `test_events.py` |
| `docs/METRICS.md` | The system metrics and the MFU method, for the G8 hand-off | Written |
| `perfkit/report.py` | `render` (run Markdown, written next to every run JSON), `compare` (5% or 0.05 ms two-run check, refuses different GPU / commit / dirty tree / config), `baseline_md`, `slowest_md`, A/B of `IMPL_SWITCHES` | Implemented; `test_report.py` |
| `perfkit/roofline.py` | Shape-based forward FLOPs/bytes/kernel estimates, compute/bandwidth/launch ceilings, optional comparison with measured regions | Implemented; `test_roofline.py`; cross-GPU validation awaits server run JSONs |
| `docs/ROOFLINE.md` | Estimator assumptions, formula, and command for comparing predictions with measured regions | Written |
| `perfkit/smoke.py` | Quick check: one CUDA event pair per whole step, no per-part numbers | Produced the A100 smoke reference numbers |

### Correctness

| File | Role | Status |
|---|---|---|
| `correctness/framework.py` (registry) | `Case`, `Pair`, `@pair`, `pairs_in`, `to64`; `TOLERANCES` per dtype, fp32 always < 1e-2 | Implemented |
| `correctness/conftest.py` | `sys.path` (so the Gate command works from the repo root), `device` fixture, stub = skipped, error report | Implemented |
| `correctness/framework.py` (checks) | `rel_err`, `check` (outputs + gradients, same seeded cotangent, one backward per side), `scaled(1.01)`, `RESULTS` error report | Implemented |
| `correctness/test_framework.py` | 1.01 on every fp32 pair, wrong gradient, NaN, wrong shape must all fail | Implemented |
| `correctness/test_attention.py` | Naive fp64 attention (GQA, both code paths) vs the model's attention, causality, path agreement | Implemented; errors ~3e-7 |
| `correctness/test_ke.py` | KE v1 built byte by byte in fp64 vs `ke1.py`, every mode; Brahmic source vocabulary byte table | Implemented |
| `correctness/test_ke2.py` | KE2 vs G4's dense fp64 encoder: random, edge-case and G4's committed table, fp32 and bf16 | Implemented |
| `correctness/test_moe.py` | Token-by-token fp64 MoE vs every entry in `DISPATCH`; routing replay (near-tie test); bias balancing; fp32 router; shared expert; init scale | Implemented |
| `correctness/test_reversible.py` | Custom backward vs plain autograd (MLP and MoE); inversion; bf16 reconstruction (CUDA bf16 only) | Implemented |
| `correctness/test_ce.py` | `ce_impl=chunked` vs `torch` and a definition, with masked targets | Implemented |
| `correctness/test_model.py` | The whole GPT (`base.yaml` and one variant per choice: chunked loss, MTP, sdpa, KE1, table, MoE, plain stack; fp32 and bf16) vs an fp64 model from the definitions, real Brahmic tokens | Implemented; catches 6 injected model bugs |
| `correctness/test_optimizer.py`, `test_tokenizer.py`, `test_metrics.py`, `test_report.py` | Optimizer assignment, updates, state restore and FLOPs; tokenizer contract; metric formulas and GPU peaks; report 5% gate and Markdown output; real-tokenizer + KE + optimizer integration is folded into `test_optimizer.py` | Implemented; CUDA bf16 loop/batched tolerance still needs validation on target GPU |

### Gate 1

Done: harness, correctness framework and pairs, `docs/METRICS.md`, `report.py`, and the A100 baseline pairs
(`results/baseline_v0.md`, `results/slowest5_v0.md`, commit `f1ed7f2`, `configs/base.yaml`). On that commit:
`pytest correctness -q -rs --all-configs` gives 375 passed, 1 xfailed, 0 failed, 0 skipped.

Left after Gate 1:
1. G5's configs as `configs/g5_*.yaml`.
2. The MoE all-to-all timed on 2+ GPUs (`torchrun ... --modes comm model.ffn=moe`); one GPU only records the payload.
3. A `@pair` test for `muon_impl=batched` and `adamw_impl=foreach` against the loop reference, and for
   `data.prefetch` (same batches).
4. The 5% repeat check on hosts other than Colab (`results/repeat_check_v1.md`, week 2): the CPU-paced parts move
   on Modal, checkpoint save on Windows.
5. Server A/B timing of `model.moe.dispatch=sorted` before it becomes a default (it also needs an
   optimizer-safe treatment of idle experts' zero gradients).
6. Time and token goodput.
7. A multi-process (DDP) optimizer test; see README "Distributed optimizer follow-up".

Counters describe Python Event objects, not guaranteed CUDA runtime handle creation.
StepTimer counters remain cumulative across resets; recorder-pool counts are separate.
Communication reports the maximum allocation count across distributed ranks.
