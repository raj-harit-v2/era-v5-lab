# Team 10-post-training

Put your work in a **topic folder**: `teams/10-post-training/<topic>/<file>`, for example `teams/10-post-training/harness/run.py`.
Team documents named in the week plan (for example `benchmarks_v1.md`) may sit directly in the team folder. The team lead decides the topic names. Do not make personal folders. Do not make new folders under `teams/`.
Open a pull request; the lead reviews and merges it. The pr-guard check must pass.

## Index (state on 12 Nov 2026)

This is an index of what is in the folder. It does not claim results; each linked file says what it measured and what it did not.

1. [licences/licence_table.md](licences/licence_table.md): licence, generator and decision for each dataset. Many sets are `TSAI reserves`, which is not approval for training. See [licences/README.md](licences/README.md).
2. [sft/sft_mix_proposal.md](sft/sft_mix_proposal.md): proposed SFT area shares and effort distribution, with revision notes to 9 Nov. See [sft/README.md](sft/README.md).
3. [sft/decontam_report.md](sft/decontam_report.md): decontamination records for 34 SFT sets against Team 9 fingerprints v2. Companion: [docs/eligibility_ledger.md](docs/eligibility_ledger.md).
4. [results/effort_probe.md](results/effort_probe.md): the reasoning-effort suite and its CPU checks (11 Nov). Later Stage B result: [results/effort_stageB_qwen_2026-11-12/report.md](results/effort_stageB_qwen_2026-11-12/report.md). See [eval/README.md](eval/README.md).
5. [results/](results/README.md): every committed run report, with what each does not show.
6. [rl-loop/README.md](rl-loop/README.md): the RL loop with a frozen router, laptop smoke tests only.
7. [docs/OVERVIEW.md](docs/OVERVIEW.md): one line per folder, with the README to open.

### Folder READMEs

| Folder | README |
|---|---|
| `chat-format/` | [chat-format/README.md](chat-format/README.md) |
| `docs/` | [docs/README.md](docs/README.md), with a one-page folder overview in [docs/OVERVIEW.md](docs/OVERVIEW.md) |
| `eval/` | [eval/README.md](eval/README.md) |
| `licences/` | [licences/README.md](licences/README.md) |
| `results/` | [results/README.md](results/README.md) |
| `rl/` | [rl/README.md](rl/README.md) |
| `rl-data/` | [rl-data/README.md](rl-data/README.md) |
| `rl-loop/` | [rl-loop/README.md](rl-loop/README.md) |
| `sft/` | [sft/README.md](sft/README.md) |
| `special-tokens/` | [special-tokens/README.md](special-tokens/README.md) |
| `swe-envs/` | [swe-envs/README.md](swe-envs/README.md) |
| `swe-task/` | [swe-task/README.md](swe-task/README.md) |
| `swe-task-go/` | [swe-task-go/README.md](swe-task-go/README.md) |
| `tests/` | [tests/README.md](tests/README.md) |


## Blockers (12 Nov)

- **Tokenizer not in the repo.** Gate 2 references sha 15468e66... (TSAI announces the freeze at Gate 2; until then G10 uses C3 sample-v0) (the C3 sample-v0 rebuild listed in `teams/03-tokenizer/README.md`). `teams/03-tokenizer/` has build scripts and `SHA256SUMS`, not that `tokenizer.json`. The committed [results/render_frozen_tokenizer.txt](results/render_frozen_tokenizer.txt) is for v0.1 (sha a33c9907...), a different file.
- **SFT admission blocked (Gate 2).** `max_sequence_tokens` is null (`context_limit_not_set`), and source identity is not verified for `apps/train`, `code_contests/train` and `taco/train`. 0 OCR-2 rows are admitted. See [sft/README.md](sft/README.md).
- **Codeforces pool held.** 69,690 `open-r1/codeforces` train rows stay held until the producer revision is settled.
- **`max_sequence_tokens` is only proposed.** [sft/max_sequence_tokens_proposal.md](sft/max_sequence_tokens_proposal.md) proposes 32768 for TSAI's signature at Gate 2 (14 Nov).
- **50-answer reward audit blocked on the RL artifact.** This is stated in the task brief; no file on this branch describes the audit or the artifact.
