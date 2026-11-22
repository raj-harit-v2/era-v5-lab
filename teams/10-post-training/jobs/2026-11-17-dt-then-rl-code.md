# Job request draft — Deletion Tuning SFT followed by code RL

**Status:** Pending private inputs, local verification of the staged configuration, and lead approval. The request has not been sent. The three-step canary checks integration and RL signal. The full run measures held-out reward change.

```text
Team:            10-post-training
Owner:           Hema Varshini Palpandian (Hemaaaa04)
Lead approval:   pending saitej123
Question:        After Deletion Tuning SFT, can the delivered Team 5 model take code-verifier RL updates while its deleted weights stay zero?
Script:          teams/10-post-training/rl-loop/train.py
Command:         G10_STDIO_RUNNER=docker python teams/10-post-training/rl-loop/train.py --config teams/10-post-training/rl-loop/config/task11_code_canary.yaml
Config:          teams/10-post-training/rl-loop/config/task11_code_canary.yaml (stage inputs and fill checkpoint and mask SHA-256 pins)
Inputs:          Team 5 delivered run folder and adapter dependencies, DT+marker-row SFT model.safetensors with dt_keep_masks.bin and dt_keep_masks.bin.json, screened RL data v1 Code Contests cc.jsonl and disjoint canary ID lists
Hardware:        1 GPU, requested >=40 GB, Python verifier image preloaded
Max time:        Proposed 30 minutes for the canary, subject to lead review
Precision:       bf16 compute, fp32 master weights
Measures:        Mixed groups, verifier failure reasons, optimizer updates and stored-update share, deleted nonzero count, held-out reward at step 0 and at the last completed step, per-step keep_zero_checks time, peak GPU memory, and persistent mask tensor bytes
Expected result: Mixed groups and code reward are unknown. The mask check should see a positive deletion count and zero regrowth.
Outputs:         under out/task11-code-canary/. Return aggregate status, counts, rewards and timing. Per-problem records, IDs, paths and generations stay private.
Test log:        CPU trainer and mask handoff checks in ../results/dt_then_rl_evidence/validation.md. Staged end-to-end test log pending. Attach the exact staged command, final output lines, exit status, and wall time before submission.
```

## Staging and acceptance

- TSAI holds the [completed dry-run-1 checkpoint](https://github.com/theschoolofai/era-v5-lab/pull/475) and approved a [separate day-one probe](https://github.com/theschoolofai/era-v5-lab/pull/558). Use the p1536 tokenizer and KE2 table recorded in the actual run manifest. Produce the DT SFT checkpoint with [the Team 5 SFT driver](../capstone/sft_g5.py) on the approved slice. Stage the baked state, both mask files, and verified adapter config together. Fill in all three SHA-256 pins. The adapter selection must include the masked parameters and keep the router frozen.
- Stage 16 training prompts from the rebuilt RL data v1 training pool and an 8-prompt subset of its designated RL held-out pool fixed before sampling. Confirm admission, check that the lists are disjoint, and check that each rendered prompt plus completion allowance fits the delivered model. The [RL pool job](2026-11-18-rl-data-v1-pool.md) defines the evaluation firewall. This path uses the same [Python stdio verifier](../rl-data/stdio_check.py) as Task 6 with the Team 5 sampler.
- The canary first verifies that the scorer accepts a known correct answer and rejects a known wrong answer. Any verifier runner failure aborts scoring. The screen then uses eight samples per training prompt. Fewer than four mixed groups yields `NO_GO_MIXED_BAND`. With enough signal, check that at least one optimizer update changes stored weights, the initial deletion count is positive, the maximum deleted-nonzero count is zero, and the router checksum stays fixed. Return the failure breakdown if the canary stops.
- Report the post-step scan time from `times_s.keep_zero_checks`, the run's peak GPU memory, and the estimated persistent storage for the Boolean masks and gradient-hook copies from `keep_zero.persistent_mask_tensor_bytes`.
- After a successful canary and lead approval, set the training budget and time cap for the full run. Freeze the held-out split and sampling settings before that run. Record step-0 and final rewards on the DT SFT checkpoint, their paired prompt-level difference and interval, optimizer updates, and deletion integrity. Task 6's Qwen 7B result used a different model and sampler. Use its protocol as a reference and interpret Task 11's gain against its own step 0.


## Update 20 Nov 2026 (f20201351h-maker): staged local test log on a stand-in (CPU)

This is not a result on the dry run 1 checkpoint. The model is a Team 5 week2 LanguageModel (2 layers, width 64, 10.6 million parameters, random init, 20 CPU smoke steps) and the canary's expected status on it is NO_GO_MIXED_BAND.

1. DT SFT state, from the job script itself (default settings of the DT flags; rows are the #587 slice settings reduced to 10 steps, batch 16, as in the #587 CPU log):
   `python capstone/sft_job_v1.py --g5-root <worktree> --run-folder <stand-in run> ... --device cpu --method dt_markers --keep-canary-state-dir <dir> --keep-arm a2 --out <out>`
   Result: exit 0, `{"ok": true, "steps": 5, "failed_steps": []}`, 331.0 s wall. `<dir>/a2/` holds `model.safetensors`, `dt_keep_masks.bin`, `dt_keep_masks.bin.json` and `SHA256SUMS` (`sha256sum -c` OK); summary.json records the same three sha256 values.
2. Canary config staged for CPU: the three sha pins filled from that folder, device cpu, local input paths, `allow_fixture_smoke: true`, max_new 48, eval_k 2, reward_pool 4, no autocast, 16 train ids and 6 held-out ids; every other line is the repo file's.
3. Canary run with the trainer's reward replaced by a seeded coin (p 0.4, dry run only, the same patch point as `rl_job_v1.py --stand-in-reward`): exit 0, 72.3 s, 3 optimizer updates, 106,420 deleted entries at the start, deleted-nonzero 0 at every step and at the end, `keep_zero_checks` 0.017 to 0.020 s per step, `persistent_mask_tensor_bytes` 8,355,840, stored-update share 0.930, peak memory footprint 2.8 GB (`/usr/bin/time -l`).
4. The same canary with the real stdio verifier (Docker) on an earlier stand-in (19 Nov, same config shape): exit 0, 22.5 s, `NO_GO_MIXED_BAND`, 0 of 16 prompts mixed, as expected for a random model.
Not shown by any of this: a pass rate or learning signal, real sizes or timings, GPU or bf16 behaviour, the admission and length check of the 16 prompts, the probe check of a delivered run folder.
Still blocked for the real canary: a DT SFT state made from dry run 1 (the job script can now make it, but its DT settings are the lead's and this task's owner's choice, and it needs the #587 result and a probe expectation for the #475 checkpoint; see `2026-11-20-g10-dt-sft-dryrun1.md`).
