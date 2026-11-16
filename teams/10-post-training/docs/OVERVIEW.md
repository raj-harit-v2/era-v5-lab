# Team 10 (Post-training and Agentic): folder overview

The rules for where files go are in `teams/10-post-training/README.md`. This page says what each folder holds and where its README is. Paths are relative to `teams/10-post-training/`.

| Folder | What it holds | README |
|---|---|---|
| `special-tokens/` | The special-token lists prepared for Team 3 (v0 and the consolidated v1 with real IDs). | `special-tokens/README.md` |
| `chat-format/` | Chat format v0: the specification, the renderer and parser, the Jinja template and the tokenizer v0.1 check. | `chat-format/README.md` |
| `licences/` | The licence table: every SFT and RL set we considered, with licence, generator model and decision. | `licences/README.md` |
| `sft/` | SFT data tools: conversion to chat format, decontamination, the decontam report and mix proposal, and the OCR-2 pack admission scripts. | `sft/README.md` |
| `rl/` | The RL code verifier and tasks, the single reward entry point, the warm container pool and the RL decontam report. | `rl/README.md` |
| `rl-data/` | RL data builders, the pass-rate filter, the survey and the answer checkers. | `rl-data/README.md` |
| `rl-loop/` | The group-relative RL loop with a frozen MoE router, and its Team 5 adapter. | `rl-loop/README.md` |
| `swe-envs/` | SWE environments built from real pull requests, with verifier and gold check. | `swe-envs/README.md` |
| `swe-task/`, `swe-task-go/` | Small end-to-end SWE demonstrations (Python, Hindi, Kannada, Tamil, Go). | `swe-task/README.md`, `swe-task-go/README.md` |
| `eval/` | The effort evaluation suite and its Stage A and B runners. | `eval/README.md` |
| `results/` | Measured outputs of the runs above. | `results/README.md` |
| `docs/` | The eligibility ledger (generated). | `docs/README.md` |
| `tests/` | Tests for the chat format, special tokens, text preparation and the licence table. | `tests/README.md` |

How the pieces connect: `licences/` decides which sets may be used, `sft/convert.py` turns an allowed set into `chat-format/` rows, `sft/decontam_run.py` checks those rows against Team 9's fingerprints, and `sft/sft_mix_proposal.md` says how the kept rows are mixed. The RL side is `rl-data/` (data builders and checkers), `rl/` (verifier, tasks and rewards) and `rl-loop/` (training).
