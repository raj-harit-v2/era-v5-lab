# RL data v1: tasks the model can learn from

GRPO learns only from groups whose rewards differ (see `rl-loop/grpo.py`). A task the starting model never solves, or always solves, gives no signal. So RL data v1 is built in three steps:
1. take human-written problems with tests;
2. add an easier rung for a very small model;
3. keep only the tasks the starting model sometimes solves.

```bash
# 1. stdio tasks from a local copy of deepmind/code_contests (no network; TSAI publishes approved sets as packs)
python teams/10-post-training/rl-data/build.py --source code_contests --parquet <train-*.parquet> --out out/tasks.jsonl

# 2. the easy rung, from templates written by people on the team (empty until TSAI answers; see easy_rung.py)
python teams/10-post-training/rl-data/easy_rung.py --templates teams/10-post-training/rl-data/templates/easy_rung_templates.yaml --out out/easy.jsonl

# 3. keep tasks with 0 < pass rate < 1 for a given starting model (any OpenAI-compatible endpoint, e.g. llama-server)
python teams/10-post-training/rl-data/filter.py --tasks out/tasks.jsonl --server http://127.0.0.1:8080 --k 8 --out out/manifest.json

python -m pytest teams/10-post-training/rl-data/test_rl_data.py -q -p no:cacheprovider
```

## DeepCoder Python

See the [Week 3 Task 2 pilot](deepcoder.md) for the pinned PrimeIntellect build, Docker verifier checks, and decontamination evidence.

## Files

| File | What |
|---|---|
| `stdio_check.py` | Reward for stdin/stdout tasks, with the same rule as `rl/verifier.py`: the sandbox gets the program and the inputs only, and the outputs are compared here. A program can't fake a pass, because it never sees the right answers. Fresh `python:3.12-slim` container, no network, the verifier's limits. |
| `build.py` | `deepmind/code_contests` (Codeforces rows, rating band, up to 20 tests) to task records. Each record keeps source, licence, generator and the licence-table set id. |
| `filter.py` | Samples k answers per task from the starting model, scores them, and writes a manifest of ids, pass rates and keep / too_hard / too_easy. |
| `easy_rung.py` | Program-generated tasks whose answers come from running a human reference solution. **The templates (statement and reference solution) must be written by a person, never by a model**, because they become training text. `templates/easy_rung_templates.yaml` is empty on purpose. |
| `results/rl_data_filter_olmoe.md` | The filter run on 36 Codeforces problems for OLMoE-1B-7B-0125-Instruct. |

## Rules this follows

- **Data rule (TSAI, 3 Nov):** human-written problems and tests only. Every task records its generator and licence. No Claude-written task text: the 10 tasks in `rl/tasks` say "written by Claude" in their `task.json`, so they are used for evaluation only until TSAI says otherwise.
- **Licences:** `deepmind/code_contests` is CC-BY-4.0 and `TSAI reserves` in `licences/licence_table.md` (`rl-code-code-contests`). TSAI picks the RL sets.
- **No data in the repo:** task records and manifests go to `out/`. Only the summary in `results/` is committed: ids and numbers, no problem text.
- **Decontamination:** run the task statements through the decontamination runner from #34 (fingerprints v2, full set) before any training. Codeforces problems overlap with code benchmarks.

## Evaluation recommendation: score on the unused source tests too (16 Nov)

A code_contests task in RL data v1 keeps 20 tests; the pinned source row usually has more (median 101). The training
reward stays on the kept 20. Held-out evaluation should also run the unused source tests where they exist: in the
15 Nov audit 5 of 162 rewarded completions at step 0 (3.1%) and 19 of 627 from the trained state (3.0%) failed a test
the reward never ran. Evidence: `../results/verifier_data_note_20261115.md` (R5), `../results/code_rl_e1_20261115.md`
(R5b), `../results/fable_20261115_evidence/reward_audit_e1a.json`. This is a recommendation; the reward is unchanged.

## RL data v1 close (16 Nov)

`rl_v1_close.py` applies the pool flags (116 statement-less tasks and the 55 effort-suite tasks out; Python-2-only
references sized, not applied; MATH kept as a separate reserved part) as fields of `manifests/rl_data_v1_close.json`.
Each flag is reversed or applied by one switch. Report: `../results/rl_data_v1_close.md`.

## Rebuild RL data v1 from pinned bytes (16 Nov)

`rebuild_v1/rebuild_v1.py` rebuilds both v1 sets, re-runs Team 9's decontamination, writes the Team 9 pool files and
checks 12 outputs against `rebuild_v1/pins_v1.json` (file names, sizes and sha256 only; no local paths). The four step
scripts in `rebuild_v1/` are byte copies of the 11 Nov scripts that produced the recorded hashes; the driver refuses a
changed copy. Job request: `../jobs/2026-11-18-rl-data-v1-pool.md`.

```bash
python teams/10-post-training/rl-data/rebuild_v1/rebuild_v1.py --cc-dir <code_contests@802411c3>/data \
    --math-dir <hendrycks_math@21a56338> --math500 <MATH-500 test.jsonl> --g9-tools <Team 9 decontam @ b470b4c0> --out out/run
```
