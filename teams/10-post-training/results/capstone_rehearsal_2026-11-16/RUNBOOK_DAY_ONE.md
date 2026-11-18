> Local `private/`, `logs/` and script paths below refer to the original experiment workspace; public validation is attached under `teams/10-post-training/jobs/evidence/2026-11-16-g10-capstone-rehearsal/`.

> Publication update, 16 November 2026: the instructor now reports #475 completed with p1536 and a final checkpoint at TSAI. The local findings below describe harness `ae4c03d`; the actual probe must use the source checkout and artifacts recorded by #475. CUDA/T2 and vLLM remain unmeasured by G10. No checkpoint access is assumed.

# Runbook: the day a real capstone checkpoint arrives (written 16 Nov 2026)

Code: `teams/10-post-training/{capstone,rl-loop}` on branch `g10-capstone-rehearsal-f20201351h-maker` (not yet
merged; until it is, run from `research/repos/g10-capstone-rehearsal-wt`). Every command below ran on the d128
laptop stand-in on 16 Nov (RESULTS.md has the output). Times marked **ESTIMATE** are scaled from those runs and are
not measurements; re-measure on the first real step.

What "arrives" means: a run folder written by Team 5's `train_week2.py` (`manifest.json`, `checkpoint.pt`,
`summary.json`), either shared with G10 or readable by a TSAI job. Variables used below:

```bash
LAB=<lab checkout at the commit the run used>       # its harness hashes must equal manifest["sources"]
RUN=<run folder>
TOK=<p1536 tokenizer.json>                          # sha256 e6b93a93...a64b
TAB=<Team 4 p1536 raw_table_P32.npz>                # or build: python -I $LAB/teams/04-ke2/src/build_tables.py --tokenizer $TOK --out ke2 --pos-dims 32
G10=teams/10-post-training
```

## 0. Preconditions (5 minutes)

1. Same Team 5 code as the run: `git -C $LAB rev-parse HEAD` is the dry-run commit. The adapter refuses otherwise.
2. Tokenizer: Team 5's `artifacts.py` pins tokenizer v0; if the run used p1536, the run was launched with an override.
   Our launcher (`capstone/g5_launch.py`) records that override in `G10_LAUNCH.json`; TSAI's may not.
3. Held-out: heldout_v1's bn/pa/as documents do not round-trip under p1536 (DEFECTS item 2). Use the exact held-out file and scoring code the run used; newer TSAI runs report scores on original bytes.

## 1. Probe (one command, no training): 10-30 minutes ESTIMATE on one GPU at T2

```bash
python $G10/capstone/day_one_probe.py --g5-root $LAB --run-folder $RUN --tokenizer $TOK --byte-table $TAB \
  --heldout <heldout.jsonl> --heldout-sources <sources.jsonl> --sft-eval <dolly_eval.jsonl> \
  --rl-tasks <RL data v1 cc.jsonl> --rl-ids <easiest-rung ids> --device cuda --out probe/
```

Read in this order: `adapter.json` (status, `model_hash_g5` equals summary.json), `forgetting.json` (the bpb SFT
must not lose), `format.json` (base model: expect ~0 closed `<|im_end|>`), `rl_screen.json` (expect pass 0 and
"no code block"), `mismatch.json` (decides routing precision for RL, rule below), `sampling.json` (decides sampler).

Decision rules (from the rehearsal preregistration and WORKING_PLAN section 6):
- mismatch `bf16_batch_vs_fp32_row.outside` < 0.1%: nothing to do. 0.1-1%: run RL with `train.autocast` unset (fp32)
  or keep the router in fp32 (it already is in G5) and recheck; > 1%: routing replay before any RL.
- sampling: if `kv.new_tokens_per_s` x 8 rows makes one RL step's sampling < 50% of the step, use the native sampler
  (`model.kv_cache: true`); otherwise ask G12 for the Granite export + vLLM.

## 2. SFT: rows, then three arms

Rows (CPU, minutes): re-tokenise G10 chat-format rows with the frozen tokenizer and assistant-only masks.

```bash
python $G10/capstone/sft_rows.py --rows <converter parts or OCR-2 pack files> --tokenizer $TOK --byte-table $TAB \
  --max-tokens <model context> --out sft/rows.jsonl     # then split by the "split" field into train / eval files
python $G10/capstone/make_adapter_config.py --g5-root $LAB --run-folder $RUN --tokenizer $TOK --byte-table $TAB \
  --origin g5_delivery --out adapter.yaml               # g10_rehearsal if no probe NLL from Team 5
```

Arms (one command each; same rows, steps and seed):

```bash
python $G10/capstone/sft_g5.py --adapter-config adapter.yaml --train sft/train.jsonl --eval sft/eval.jsonl \
  --method full --steps 600 --batch 16 --lr 3e-4 --device cuda --heldout <heldout> --heldout-sources <sources> \
  --rl-tasks <cc.jsonl> --rl-ids <easiest-rung ids> --out sft_full
# --method lora --lr 1e-3 --marker-rows --wd 0          (LoRA + the nine marker head rows)
# --method dt --dt-targets g5_mlp --marker-rows --wd 0  (Deletion Tuning on every expert's gate/up/down)
# --method markers --marker-rows --wd 0                 (control: nine head rows only)
```

Each writes `sft_report.json`: mask checks on real rows, step-1 writeback (FP32 vs what BF16 storage would keep),
frozen-weight hash, reload parity, eval NLL, forgetting bpb, format screen (closed `<|im_end|>`, failure reasons),
RL screen before/after. Judge by generation and forgetting, never by teacher-forced loss alone (R3).
Time per arm at T2: ESTIMATE 20-60 min on one H100-class GPU for 600 steps x 16 rows x <= 2,048 tokens.

## 3. RL (only once the RL screen shows mixed groups)

```yaml
# rl.yaml (train.py)
model: {kind: team5_adapter, adapter_config: adapter.yaml, kv_cache: true}   # allow_fixture_smoke: true for rehearsal
task: {kind: stdio, tasks: <cc.jsonl>, train_ids: <screened mixed ids>, heldout_ids: <unfiltered held-out ids>}
train: {algo: objective_v1, steps: 60, prompts_per_step: 16, k: 8, max_new: 1024, temperature: 1.0, lr: 1.0e-6,
        ppo_epochs: 1, kl_coef: 0.0, sampler: policy, autocast: bf16, fp32_master: true, eval_every: 10,
        eval_k: 4, state_dir: state, state_every: 5, reward_pool: 8}
```

```bash
python $G10/rl-loop/train.py --config rl.yaml
```

`autocast: bf16` matters: a G5 checkpoint is stored in fp32, so without it the run is all-fp32 (slower, and the
mismatch probe's fp32 numbers apply). Watch `groups_used` per step: when it falls to about half its start, refresh the
prompts (R4). Resume after a kill is exact to the run-to-run floor (bit-exact with one thread; rehearsal RESULTS).

## Measured on the d128 stand-in (16 Nov, for scale only)

| step | measured | where |
|---|---|---|
| day-one probe, all six steps | 11 min on MPS (format screen 2.3 min, RL screen 95 prompts x 8: 5.7 min) | `private/dayone_b` |
| SFT arm, 300 steps x 16 rows (~130 tokens) | 2-3.5 min train + ~1 min eval, CPU | `private/sft_b/*` |
| RL step, 8 prompts x k 8, 72-96 new tokens | 13.5 s (stdio) to 25 s (toy, with backward), CPU; sampling 64-100% | `rl/b_*_cpu` |
| sampler | KV cache 258.6 tok/s (MPS) / 947.6 (CPU); re-forward 163.8 / 108.4 | `bench/` |

Scaling to T2 (ESTIMATE, labelled): parameters x10, context x8. Per-token sampling cost grows roughly with active
parameters (~x6) and attention with context; expect the native KV sampler at T2 on one H100-class GPU to need a
measurement before choosing between it and vLLM. Use MPS only for fixed shapes on a Mac: it rebuilds kernels for every
new batch shape (SFT step 1: 85 s on MPS vs 1.0 s on CPU).

## 4. What to do first if something fails

| Symptom | Likely cause | Check |
|---|---|---|
| adapter: "trained with a different model.py" | wrong lab commit | `jq .sources $RUN/manifest.json` vs `shasum -a 256 $LAB/teams/05-architecture/harness/week2/*.py` |
| adapter: model_hash differs from summary.json | checkpoint from another step or a damaged copy | re-copy; compare `checkpoint_sha256` |
| SFT: "rows exceed block_size" | rows rendered for a longer context | re-run `sft_rows.py --max-tokens <block_size>` |
| RL: crash "same dtype float != BFloat16" | model cast to bf16 without autocast (KE2 returns fp32) | set `train.autocast: bf16` |
| RL: every group dropped | no prompt is solvable yet | read `rl_screen.json` reasons; SFT first |
| machine slows to a crawl during scoring | orphaned sandbox containers from a killed scorer | `docker ps`; kill `python:3.12-slim` containers older than the run |
