# eval-mini v1: result schema

**Status: ready for review, 3 Nov 2026.** It becomes final when its PR merges (due Wed 4 Nov). Section 6 stays
provisional until Team 7's layout hand-off (PR #245, due Wed 4 Nov).

Used by:
- Team 8, which ingests eval-mini results;
- Team 12, which scores quantized formats with eval-mini;
- `harness_lab/run_lab_ckpt.py`, which scores lab checkpoints.

## 1. What changes from v0

| | v0 | v1 |
|---|---|---|
| Shape | two shapes: a flat `records` list (`eval_mini_v0.json`, PR #21) and a file nested by model (`eval_mini_v0_code_indic.json`, PR #88) | one flat `records` list for every source |
| Units | fractions 0–1 (PR #21), points (PR #88) | **points 0–100** everywhere |
| Model revision | per record (PR #21), per model (PR #88) | per record |
| Harness version | per record (PR #21), in `env` (PR #88) | per record, as `{name, version}` |
| Seed | 42 per record (PR #21), not recorded (PR #88) | per record, all four seeds |
| Lab checkpoints, quantized formats | no field for them | `checkpoint`, `format`, `backend` |

## 2. File layout

```json
{
  "schema_version": "eval_mini_v1",
  "generated": "2026-11-03",
  "sources": [
    {"path": "teams/09-evaluation/results/eval_mini_v0.json", "sha256": "<sha256 of the file>", "schema_version": "eval_mini_v0"}
  ],
  "notes": ["<file-level notes, see section 8>"],
  "records": [ { "...": "one object per score, section 3" } ]
}
```

UTF-8, LF line endings, records sorted by the key in section 4. Writing the same inputs twice gives a byte-identical file.

**JSON, not JSON Lines.** The file is one JSON document, because `sources` and `notes` describe the whole file. Each item
of `records` is one complete row: nothing in it depends on the rest of the file. To get JSON Lines, run this in `results/`:

```bash
python -c "import json; [print(json.dumps(r)) for r in json.load(open('eval_mini_v1.json', encoding='utf-8'))['records']]" > eval_mini_v1.jsonl
```

**Nested fields stay nested.** `checkpoint`, `seed` and `harness` are objects; `derived_from` and `notes` are lists. A reader
that needs flat columns uses dotted names: `seed.random`, `harness.version`, `checkpoint.step`.

**Nulls.** A required field with no value is JSON `null`. It is never left out, and never written as `NaN`, `Infinity`,
`"N/A"` or `""`. Only `checkpoint`, `dtype`, `seed`, `stderr` and the optional `n_items_total`, `profile` and `derived_from`
can be null, so the key (section 4) and `value` never are. A run with no score has no record. lm-eval writes `"N/A"` when it
cannot compute a standard error: a writer turns that into `null`.

## 3. Record fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `model` | str | yes | Hugging Face id of the model that ran (`Qwen/Qwen2.5-1.5B`), or `lab:<run>` for a lab checkpoint (section 6) |
| `model_revision` | str | yes | Hugging Face commit sha (40 hex characters); for a lab checkpoint, a sha256 (section 6) |
| `checkpoint` | object or null | yes | null for Hugging Face models; for a lab checkpoint `{run, branch, step, epoch, tokens_seen, path}` (section 6) |
| `format` | str | yes | weights format as evaluated: `bf16` for the Hugging Face runs; Team 12's format name for quantized runs (`Q4_K_M`) |
| `backend` | str | yes | `hf` (transformers through lm-eval), `lab` (a lab model wrapper) or the backend text Team 12 reports (`llama-cpp-python 0.3.36 (in-process, logits_all)`). For reading only: not part of the key |
| `dtype` | str or null | yes | dtype as reported: `bfloat16`; Team 12's files repeat the format name here |
| `task` | str | yes | lm-eval task name (`arc_challenge`, `leaderboard_mmlu_pro`, `milu_Hindi`, …); code: `humaneval`, `humaneval_plus`, `mbpp`, `mbpp_plus`; derived: `arc_average` |
| `metric` | str | yes | `acc`, `acc_norm`, `exact_match`; code: `pass@1` |
| `filter` | str | yes | lm-eval answer filter: `none`, `strict-match`, `flexible-extract`; code: `none` |
| `primary` | bool | yes | true for the one metric and filter per task that reports use |
| `value` | number | yes | **points 0–100**, 2 decimals |
| `stderr` | number or null | yes | points, 2 decimals; null where it is not computed (code) |
| `n_items` | int | yes | items scored |
| `n_items_total` | int or null | no | items in the full split |
| `item_set` | str | yes | `full`; `limit:<N>` (lm-eval's first N items); or `spec:<spec_sha256>` (the items listed in an eval-mini spec file) |
| `profile` | str or null | no | v0 profile name (`mini`, `check`) or eval-mini part (`code_indic`). For reading only: not part of the key |
| `num_fewshot` | int | yes | few-shot examples (0 for code) |
| `decoding` | str | yes | `loglikelihood` (scored choices) or `greedy` (generation) |
| `seed` | object or null | yes | `{random, numpy, torch, fewshot}`; null only for 0-shot greedy runs, where no seed changes the result (section 5) |
| `harness` | object | yes | `{name, version}`, for example `{"name": "lm_eval", "version": "0.4.13"}` or `{"name": "evalplus", "version": "0.3.1"}`; optional `script_sha256` (the G9 script that ran it, as Team 12 records it) |
| `hardware` | str | yes | GPU or device as reported |
| `run_date` | str | yes | `YYYY-MM-DD` |
| `derived_from` | list of str or null | no | the tasks a derived score is computed from (`arc_average`: `arc_easy`, `arc_challenge`) |
| `notes` | list of str | no | notes that apply to this record only |

## 4. Record key

A record is identified by:

**`model`, `model_revision`, `format`, `item_set`, `task`, `num_fewshot`, `metric`, `filter`**

No two records in a file share a key. Every part is needed:
- `model_revision`: Qwen2.5-1.5B is scored at two revisions, `8faed761` (PR #21) and `e5dfabbc` (PR #88).
- `format`: Team 12 scores one model in several formats.
- `item_set`: GSM8K is scored on different items, the first 200 (PR #21, `mini`) and 100 spec items (PR #88).
- `num_fewshot`: PR #21 scores ARC-Challenge at 0 and 25 shots, and GSM8K at 4 and 5 shots, on the same full sets.

The model name alone never identifies a score.

## 5. Seeds

| Source | Seeds recorded in v1 | Where it comes from |
|---|---|---|
| `harness/run_eval_mini.py` (PR #21, Team 12) | `{42, 42, 42, 42}` | one `--seed`, passed to all four (`run_task`) |
| `harness_code_indic/run_lm_eval.py` (PR #88) | `{0, 1234, 1234, 1234}` | it passes no seed, so lm-eval 0.4.13's defaults apply (`lm_eval/defaults.py`) |
| evalplus code runs (PR #88) | null | 0-shot, greedy |

The eval-mini spec's `seed` (20261028) chooses which items are in the item set. It is not a run seed, and `item_set` already records it through `spec_sha256`.

## 6. Lab checkpoints (provisional)

Team 7's checkpoint code is merged (PR #150, `ckpt/ckpt.py`). It stores a checkpoint at
`<remote_root>/<run_id>/<branch>/step_<N>-e<E>/`: sharded files plus a `MANIFEST.json` that lists every file with its
sha256 and is written last. `<N>` is zero-padded to 8 digits (`step_00002000-e1`). PR #245 (open) puts a queue job's
checkpoints under `./out/<job_run_id>/ckpt/<arm>/`, so there `<remote_root>` is `./out/<job_run_id>/ckpt` and `<run_id>` is
the arm (`main`, `a`, `b`).

Read only the folder that `latest.json` or a `commits.jsonl` line names, never one found by listing, and get the weights
through `export_safetensors()`, not from the shards (PR #245, section 5).

| v1 field | Value |
|---|---|
| `model` | `lab:<run>` |
| `model_revision` | sha256 of the bytes of `MANIFEST.json`. A sharded checkpoint has no single weights file |
| `checkpoint.run` | `<run>`: `MANIFEST.json` `run_id`; in a queue job `<job_run_id>/<arm>`, because the arm alone (`main`) repeats in every job |
| `checkpoint.branch` | `MANIFEST.json` `branch` |
| `checkpoint.step` | `MANIFEST.json` `step` |
| `checkpoint.epoch` | `epoch` in `latest.json` or the `commits.jsonl` line: the `<E>` in the folder name. It counts restart attempts; it is not a training epoch |
| `checkpoint.tokens_seen` | `MANIFEST.json` `tokens` |
| `checkpoint.path` | `<remote_root>/<run_id>/` + `path` from that same pointer |
| `format`, `backend` | the dtype evaluated (`bf16`); `hf` if the export loads through transformers, otherwise `lab` |

```json
{
  "model": "lab:<run>",
  "model_revision": "<sha256 of MANIFEST.json>",
  "checkpoint": {"run": "<run>", "branch": "<branch>", "step": 2000, "epoch": 1, "tokens_seen": 2048000, "path": "<remote_root>/<run_id>/<branch>/step_00002000-e1"},
  "format": "bf16",
  "backend": "lab",
  "...": "the other fields as in section 3"
}
```

**A checkpoint without Team 7's `MANIFEST.json`.** Team 5's `harness/train_week2.py` writes one `checkpoint.pt` and its own
lowercase `manifest.json`. For such a file, `model_revision` is the sha256 of the checkpoint file, `<run>` is the run's
folder name, `checkpoint.step` is the file's `step`, and fields the file does not hold (`branch`, `epoch`, `tokens_seen`)
are null.

**The tiny MoE, for a CPU test.** Team 5's tiny MoE harness (`harness/train.py`) saves no checkpoint. Team 7's
`jobs/restore_test/restore_test.py` saves the same `TinyMoE` through `Checkpointer`, in the layout above, under `out/ckpt_store/`.

`convert_v0_to_v1.check(doc, 0)` runs the section 7 checks on any v1 document, so a writer can test its own output with it.
Team 8 plots scores over training by `checkpoint.step`.

## 7. Converting the v0 files

The converter is `results/convert_v0_to_v1.py`. It reads both v0 files and `harness_code_indic/eval_mini_v0_spec.json`, and writes
`results/eval_mini_v1.json`. `harness/run_eval_mini.py` does not change: Team 12 checks its sha256 when combining runs.

Team 12 can run it on its `eval_mini/results/raw/*/*/summary.json` files. It stops with an error on
`eval_code_indic/results/raw/*/*/summary.json` (PR #219): those records keep the model, revision and harness in `run_meta`,
and they record no seed. A file whose `run_meta.model` is not the model that ran (PR #259 notes this for its two files) must
be corrected first: the converter cannot detect it.

| v1 field | From `eval_mini_v0.json` (PR #21; also Team 12's `summary.json`) | From `eval_mini_v0_code_indic.json` (PR #88) |
|---|---|---|
| `model` | `model` | `hf_id` |
| `model_revision` | `model_revision` | `revision` |
| `format`, `backend` | `bf16`, `hf` (Team 12: `run_meta.format`, `run_meta.backend`) | `bf16`, `hf` |
| `task`, `metric`, `filter` | as is | `scores` key; `metric` string split at the comma (`acc,none` → `acc` + `none`). Code: base → `humaneval` / `mbpp`, plus → `humaneval_plus` / `mbpp_plus`, metric `pass@1`, filter `none` |
| `value`, `stderr` | × 100, rounded to 2 decimals | as is; code `stderr` null |
| `n_items`, `n_items_total` | as is | `n`; total from the spec's `n_test_docs` (code: 164 and 378) |
| `item_set` | `full` if `limit` is null, else `limit:<limit>` | `spec:<spec_sha256>`; code `full` |
| `num_fewshot` | as is | from the spec (5); code 0 |
| `decoding` | `greedy` for `gsm8k`, else `loglikelihood` | the same; code `greedy` |
| `seed` | `{42, 42, 42, 42}` | `{0, 1234, 1234, 1234}`; code null |
| `harness` | `{lm_eval, harness_version}` | `{lm_eval, env.lm_eval}`; code `{evalplus, 0.3.1}` (the spec's `code.harness`) |
| `hardware` | `hardware` | `gpu.before.gpu` |
| `run_date` | `run_date` | the file's `generated` date (2026-10-27) |
| `primary` | `primary` | true (the file holds one metric per task) |
| `profile` | `profile` | `code_indic` |
| `derived_from` | `derived_from` (only `arc_average`) | null |

Expected result: **98 records** (59 from PR #21, 27 lm-eval scores and 12 code scores from PR #88).

The `run_date` of the PR #88 records is the day that file was assembled, because it holds no per-run date. `compare.py`
rewrites that date whenever it regenerates the file, so re-run the converter only if the scores in the file change.

The converter prints these checks:

| Check | Expected |
|---|---|
| record count | 98 |
| records missing a required field | 0 |
| values outside 0–100 | 0 |
| stderr neither null nor a number ≥ 0 | 0 |
| duplicate keys (section 4) | 0 |
| records with an empty `model_revision` | 0 |
| records with neither a seed nor greedy decoding | 0 |
| a second build | byte-identical file |

## 8. File-level notes

- Subset scores (`limit:` and `spec:` item sets) are for comparing checkpoints and formats. They are not comparable to
  published full-set scores.
- Noise: on Qwen2.5-1.5B, changing only the attention kernel moved 100-item tasks by up to 2 items. Treat a difference of
  about 2 points on a 100-item task as noise.
- GSM8K: our 4-shot full-set scores are 6–7 points under Qwen's own report. The gap is prompt format: lm-eval and the
  SmolLM2 card's lighteval agree with each other and not with Qwen's figure (`results/compare_v0.md`).
- HellaSwag: its items are internal only (the Hugging Face copy states no licence). v1 keeps its scores, because scores of
  public models are not items.

## 9. Open points

1. **Team 8:** section 2 sets the format (JSON, nested objects, `null`). Team 8 confirms that its ingest reads it (PR #250).
2. **Team 7:** PR #245 (due Wed 4 Nov) sets the queue job paths in section 6.
