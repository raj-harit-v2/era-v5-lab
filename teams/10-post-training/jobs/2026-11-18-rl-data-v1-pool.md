# Job request: RL data v1 and its Team 9 pool files, rebuild and store

Why a job request: the instructor's reply in the G10 group on 14 Nov 2026 was "do not commit large files. Commit the
script, the manifest with sha256 and the row count, and the rebuild recipe. If TSAI needs the built file, send a job
request and TSAI stores it." The work order also says "we give to Team 9" the RL pool for its check (Wed 18 Nov). This
job rebuilds RL data v1 from pinned bytes so that TSAI holds the files Team 9 checks. It adds no new cleaning rule:
the decontamination is Team 9's own tool and fingerprint set, run as it was on 11 Nov.

**Lead decisions before sending (16 Nov):**
1. Route: approved for TSAI rebuild & storage (`Lead approval: saitej123`) so Team 9 reads deterministic files from TSAI storage (we can also supply the 8.7 MB close pool directly if requested).
2. Pool flags: keep `python2_only` (`1,545` tasks) in the v1 close pool (`3,577` tasks) for Team 9 decontamination and TSAI admission (`stdio_check.py` scores candidate Python 3 completions against pinned I/O pairs; `drop_python2: false` remains reversible via `--drop-python2`). Keep the 116 `statement_less` tasks and 55 `effort_suite` tasks excluded; MATH (`7,209`) stays in its separate reserved part pending TSAI admission.

The evaluation-firewall lists are in the merged team PR #524; the lead's explicit confirmation of the RL held-out size is pending. The job can run without them, as described under "Without the two lists" below.

```
Team:            10-post-training
Owner:           f20201351h-maker
Lead approval:   saitej123 (approved, 16 Nov; evaluation-firewall lists and the two extra pool files added afterwards, to confirm)
Question:        Does a rebuild of RL data v1 from pinned bytes give exactly the 12 output sha256 recorded in teams/10-post-training/rl-data/rebuild_v1/pins_v1.json ("expected"), so TSAI can store the pool files for Team 9's check?
Script:          teams/10-post-training/rl-data/rebuild_v1/rebuild_v1.py   (in this PR; it runs the four step scripts next to it and sft/decontam_run.py)
Command:         python teams/10-post-training/rl-data/rebuild_v1/rebuild_v1.py --cc-dir ROOT/code_contests/data --math-dir ROOT/hendrycks_math --math500 ROOT/math500/test.jsonl --g9-tools ROOT/g9/teams/09-evaluation/decontam --out out/run --rl-heldout-ids ROOT/rl_heldout_v1_ids.txt --sft-heldout-match-ids ROOT/sft_heldout_match_ids.txt
Config:          teams/10-post-training/rl-data/rebuild_v1/pins_v1.json (every input by file name, size and sha256; the step scripts' sha256; the 12 expected outputs)
Inputs:          deepmind/code_contests @ 802411c3010cb00d1b05bad57ca77365a3c699d6, the 39 train parquets (7.5 GB);
                 EleutherAI/hendrycks_math @ 21a5633873b6a120296cce3e2df9d5550074f4a3, the 7 train parquets (3.0 MB);
                 HuggingFaceH4/MATH-500 test.jsonl (git blob 2376b9a1, sha256 35dc4108...; read only by the overlap guard);
                 Team 9 decontam tools + fingerprints v2 at commit b470b4c0 (set sha256 2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a).
                 Evaluation firewall (G10 lead, 16 Nov): ROOT/rl_heldout_v1_ids.txt (the RL held-out set, 255 task ids, sha256 0e2c6f7835d98fdef72b76320604e020e3803ad650d88fcc64885843bdc09163) and ROOT/sft_heldout_match_ids.txt (82 pool tasks whose problem is in the SFT held-out split, sha256 105103bebd0ba77f93d76536f7d8924e34edf16fd3121c60711199e82c0cf160); private, attached to this request, pinned under `firewall` in pins_v1.json.
                 The driver refuses any input whose size or sha256 differs from the pin. No network or key is needed once ROOT is staged.
Hardware:        CPU, 2 cores, 4 GB RAM, 20 GB free disk (estimate: 7.5 GB inputs, under 0.2 GB outputs; peak memory not measured)
Max time:        15 minutes
Precision:       not used
Measures:        sha256 and row counts of the v1 files, the decontam clean files and the four pool files (out/run/rebuild_summary.json)
Expected result: {"outputs_checked": 14, "mismatches": {}, "ok": true, "code_pool": 3577, "math_reserved": 7209, "code_train_pool": 3251, "rl_heldout": 255}
                 Without the two lists: omit --rl-heldout-ids and --sft-heldout-match-ids; the first 12 outputs are checked and the two new pool files are reported missing. Team 9's close pool and the probe's cc.jsonl do not need the lists.
Outputs:         out/run/rebuild_summary.json, out/run/build_counts.json, out/run/decontam/*.record.json (under 1 MB) back to the repo. To TSAI storage for Team 9: out/run/pool/*.jsonl (6 files: the four below plus the RL training pool and the RL held-out part) and out/run/out/v1/{cc,math}.jsonl.
Test log:        teams/10-post-training/jobs/2026-11-18-rl-data-v1-pool.log (same script, Apple M1 Pro, 16 Nov; details in teams/10-post-training/results/rl_data_v1_close.md, section 1)
```

## Pool files (JSONL `{id, text}`, for Team 9's `decontam_check.py --id-field id`)

| File | Rows | sha256 |
|---|---:|---|
| `pool/rl-code-v1-close.pool.jsonl` (code pool after the flags) | 3,577 | `71e000f4a34081a8b9d45e9558747fa69de44c1c6a0770ad2d2a6e3b0b3efbfc` |
| `pool/rl-code-v1-train.pool.jsonl` (RL training pool: close pool minus the RL held-out set and the 82 SFT held-out matches) | 3,251 | `cd1aa76ef1216f6fc6fdcf63fc0b69c98fa6a5d58a510f28be9050fecbedcce1` |
| `pool/rl-code-v1-heldout.pool.jsonl` (RL held-out set v1: evaluation only, never trained, also out of SFT training) | 255 | `935857bb0246172aa0439445dd54ef9bbbe282ad2b5ea87ddd100429c9e31ae5` |
| `pool/rl-math-v1-reserved.pool.jsonl` (MATH reserved part) | 7,209 | `f90a7b1fe5a6b1c946151a2bf69fe85b605c7ce7d487a5c26776fd8523f3c25a` |
| `pool/rl-code-code-contests-noncf.v1.pool.jsonl` (all of v1 code) | 3,723 | `84b0a645882fd3c518eb543432f3758bbde564e9aab3dca99e534834abc2b5f1` |
| `pool/rl-math-hendrycks-math-train.v1.pool.jsonl` (all of v1 MATH) | 7,234 | `5148ce7a52f8767755957d8981bc9db3a62d8049fcc3369835223762d8180de4` |

code text = the problem statement; MATH text = problem, blank line, reference answer (the answer drives the reward).

## Run root

```
ROOT/code_contests/data/train-000NN-of-00039-*.parquet   39 files at the pinned revision
ROOT/hendrycks_math/<subject>/train-00000-of-00001.parquet   7 subjects
ROOT/math500/test.jsonl
ROOT/g9/teams/09-evaluation/{decontam,fingerprints}      Team 9 at b470b4c0
```

## Resource basis (measured, 16 Nov)

Rebuild from the repo copy on an Apple M1 Pro (8 cores, shared, load average 12-20): 77 s wall, 61 s user CPU.
Pins 6 s, build 11 s, decontam (both sets) 58 s, guard + assemble 2 s, pools under 1 s. Memory was not measured;
the build reads one parquet at a time (largest 227 MB on disk). The 15-minute limit is about 10 times the measurement.

## Evaluation firewall (added 16 Nov, after the lead's approval of this route)

Lead's ruling (G10 group, 16 Nov): problems used to evaluate RL stay out of training, the SFT held-out split stays out of
the RL training pool, and the training pools may overlap. The close pool (3,577, Team 9's check) is unchanged; the two
private lists split it into the RL training pool (3,251) and the RL held-out set (255 = the 15 Nov run's 96 + the 160
planned for E10; 252 of them are in the close pool, 3 are effort-suite or statement-less tasks). The 82 SFT held-out
matches are 73 confirmed + 9 possible matches of `sft/cross_stage_overlap.py`; 8 of them are also RL held-out.
Record: `rl-data/manifests/rl_data_v1_close.json` (`rl_heldout_v1`, `sft_heldout`, `parts.code.train_pool_*`,
`parts.heldout`). Local rebuild with the lists, from scratch, Apple M1 Pro (shared): `{"outputs_checked": 14,
"mismatches": {}, "ok": true, "code_pool": 3577, "math_reserved": 7209, "code_train_pool": 3251, "rl_heldout": 255}`,
90.7 s wall. Without the lists the first 12 outputs still match and the two new files are reported missing.

