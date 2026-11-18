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
