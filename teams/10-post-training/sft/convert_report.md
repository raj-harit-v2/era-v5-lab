# `sft/convert.py`: 1,000-row test

`convert.py` turns one candidate SFT set into chat-format v0 JSONL with loss masks and writes a manifest next to it. This page records the 1,000-row test on four sets from `sft_mix_proposal.md`. No data file is committed; the outputs stay local.

## What one output row holds

```json
{"id": "sft-code-codeforces-cots/<row index>", "set": "sft-code-codeforces-cots", "source_id": "1991/A", "effort": "16k",
 "text": "<|im_start|>system\nReasoning effort: 16k<|im_end|>\n<|im_start|>user\n...<|endoftext|>",
 "train_spans": [[start, end], ...], "input_ids": [...], "loss_mask": [0, 0, 1, ...]}
```

- `text` is exactly `render.render(messages, effort)`. `render.py` is not changed. Every written row is read back with `render.parse()` during the run.
- `train_spans` are half-open character spans. Trained (1): each assistant turn body (think span, tool calls, visible reply) and its closing `<|im_end|>`. Not trained (0): system turn (with the effort line and, for agent sets, the tool schemas), user turns, tool results, the `<|im_start|>assistant` header, the newline after `<|im_end|>`, and `<|endoftext|>`. This is the policy in `sft_mix_proposal.md` section 1, gate 3.
- `input_ids` and `loss_mask` are written only with `--tokenizer`. A token is trained only if it lies fully inside a span, so a token that straddles a turn boundary is never trained.
- `id` is `<set>/<row index in the source split>`, so it stays unique even when the source repeats its own ids (the 972 codeforces-cots rows cover 200 problems, several generations each). The source id is kept as `source_id`.
- `id` and `text` are the fields `teams/09-evaluation/decontam/decontam_check.py` reads (`--id-field id`), so the decontamination run can take these files as they are.
- `effort` is the smallest budget (1k, 4k, 16k, 64k) that holds the row's trace: every think span, tool call and tool result, with their markers (`sft_mix_proposal.md` section 4). Visible reply text is not counted. A row over 64k is skipped.

The manifest holds set, source, language, generator model, licence and decision (read from the Stage 1 table in `licences/licence_table.md`), rows scanned / in / out, skips by reason, the effort mix, `content_sha256` of the JSONL bytes, which counter set the effort, and the input. A set marked `excluded`, or missing from the table, is refused.

## Adapters

| Set | Source | What the adapter does | Rows it skips |
|---|---|---|---|
| `sft-code-self-oss-instruct` | bigcode/self-oss-instruct-sc2-exec-filter-50k | `instruction` becomes the user turn, `response` the assistant turn | none so far |
| `sft-code-codeforces-cots` | open-r1/codeforces-cots (`solutions`) | splits the R1 reply into `think` (inside `<think>...</think>`) and the visible answer | `finish_reason != stop` (cut-off generations); a reply without one leading think block |
| `sft-code-swe-rebench-openhands` | nebius/SWE-rebench-openhands-trajectories | OpenAI-style turns; tool calls go through `render.py` (call `id` kept); tool schemas as JSON text in the system turn | `resolved != 1` (failed trajectories) |
| `sft-indic-aya-dataset` | CohereLabs/aya_dataset | `inputs` / `targets`; G10 text-prep (`swe-task/hindi_text_prep.py`: strip U+200B and U+FEFF, keep ZWJ and ZWNJ, no NFKC) | selects only the 10 Indic languages of the proposal (aya codes `hin mar tam tel kan ben guj mal ory pan`) |

Any row that `render()` rejects (for example a leftover plain `<think>` tag or tool arguments that are not JSON) is skipped and counted under the renderer's message. So are rows with a missing or null field, an empty user or assistant turn, or text that is not valid UTF-8. Nothing is patched.

`--hf-rows` reads the datasets-server API and stops with an error if a page comes back from the wrong offset or with a truncated cell, so a network fault cannot silently repeat or cut rows.

## Results (2 Nov 2026)

Tokenizer: Team 3 tokenizer v0.1, rebuilt locally from `theschoolofai/BrahmicTokenizer-131K` with `teams/03-tokenizer/v0/build_v0.py` and `build_v0_1.py`. Its sha256 `a33c9907...e578` matches `teams/03-tokenizer/v0/SHA256SUMS`. This is not the frozen tokenizer (Team 3 freezes it on Sat 14 Nov), so effort tiers and token counts must be rerun then.

| Set | Rows in | Rows out | Skipped | Effort 1k / 4k / 16k / 64k | Tokens | Trained tokens | `content_sha256` |
|---|---:|---:|---|---|---:|---:|---|
| `sft-code-self-oss-instruct` | 1,000 | 1,000 | 0 | 1,000 / 0 / 0 / 0 | 304,193 | 171,391 (56.3%) | `57ba674c...14d8` |
| `sft-code-codeforces-cots` | 1,000 | 972 | 28 not finished | 30 / 222 / 543 / 177 | 10,360,525 | 9,658,518 (93.2%) | `5b17291d...c88d` |
| `sft-code-swe-rebench-openhands` | 1,000 | 468 | 508 not resolved, 24 over 64k | 0 / 0 / 2 / 466 | 22,891,994 | 6,489,393 (28.3%) | `dd6fbfe5...aca5` |
| `sft-indic-aya-dataset` | 1,000 (of 4,850 scanned) | 1,000 | 0 | 1,000 / 0 / 0 / 0 | 351,403 | 234,831 (66.8%) | `3a01b154...bc4a` |

Rows in are rows 0 to 999 of each `train` split, read with `--hf-rows 1000`; for aya, the first 1,000 Indic rows of the `train` parquet. aya_dataset has no Odia rows, so its Indic rows are the other 9 languages.

## Checks on the outputs

- **Round trip:** all 3,440 written rows parse back with `render.parse()` and carry the effort they were rendered with.
- **Token IDs:** `input_ids` decode back to `text`, and equal a fresh encode of `text`, for every row.
- **Ids:** unique in every file.
- **No prompt token trained:** in all four sets, 0 trained tokens fall outside a train span.
- **Span starts:** every span starts right after `<|im_start|>assistant\n`, ends with `<|im_end|>`, and holds no `<|im_start|>`.
- **Coverage:** every span character is covered by a trained token in three sets. In aya, 21 characters are not: when an answer starts with a newline, the tokenizer merges the header newline and that newline into one token, which straddles the boundary and stays untrained (by the rule above).
- **Determinism:** a rerun of aya gives the same `content_sha256`. Before the `source_id` field was added, self-oss and SWE-rebench gave the same hash from `--hf-rows` and from a separate download of the same rows.
- `python -m pytest teams/10-post-training/tests teams/10-post-training/sft -q`: 56 passed (36 existing, 20 new).

## How to reproduce

```bash
python teams/03-tokenizer/v0/build_v0.py BrahmicTokenizer-131K/tokenizer.json v0.json
python teams/03-tokenizer/v0/build_v0_1.py v0.json tokenizer_v0_1.json
python teams/10-post-training/sft/convert.py --set sft-code-self-oss-instruct --hf-rows 1000 --out out/self-oss.jsonl --tokenizer tokenizer_v0_1.json
python teams/10-post-training/sft/convert.py --set sft-code-codeforces-cots --hf-rows 1000 --out out/codeforces.jsonl --tokenizer tokenizer_v0_1.json
python teams/10-post-training/sft/convert.py --set sft-code-swe-rebench-openhands --hf-rows 1000 --out out/swe-rebench.jsonl --tokenizer tokenizer_v0_1.json
# aya: download default/train/0000.parquet from the datasets-server /parquet listing first
python teams/10-post-training/sft/convert.py --set sft-indic-aya-dataset --input aya_train.parquet --limit 1000 --out out/aya.jsonl --tokenizer tokenizer_v0_1.json
```

Without `--tokenizer` the effort count is UTF-8 bytes / 4, and the manifest says so.

## Not done or not verified

- **Frozen tokenizer:** the counts above use v0.1. Rerun on Sat 14 Nov.
- **Decontamination:** not run. Team 9's fingerprints v2 arrive Wed 4 Nov; the outputs are in the format `decontam_check.py` reads.
- **Other sets:** only 4 of the proposal's sets have adapters. Each new set needs one small adapter function and one fixture test.
- **Tool-result IDs:** `render.py` keeps a call `id` inside the tool call but has no slot for `tool_call_id` on the result, so results are matched by order (as `chat_format_v0.md` says).
- **SWE trajectories:** nearly all fall in 64k, because tool results (file contents, test logs) count toward the trace as the proposal says. If TSAI wants tool results out of the budget, it is a one-line change to `TRACE`.
- **Licence tags** are taken as written in `licence_table.md`; this script does not re-check them.
