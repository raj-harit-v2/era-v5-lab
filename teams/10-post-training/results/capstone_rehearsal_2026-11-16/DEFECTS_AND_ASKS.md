> Local `private/`, `logs/` and script paths below refer to the original experiment workspace; public validation is attached under `teams/10-post-training/jobs/evidence/2026-11-16-g10-capstone-rehearsal/`.

> Publication update, 16 November 2026: the instructor now reports #475 completed with p1536 and a final checkpoint at TSAI. The local findings below describe harness `ae4c03d`; the actual probe must use the source checkout and artifacts recorded by #475. CUDA/T2 and vLLM remain unmeasured by G10. No checkpoint access is assumed.

# Defects and asks from the capstone rehearsal (16 Nov 2026)

Update 16 Nov midday: the instructor confirmed p1536 for SFT data v1, and dry run 1 (#475: T2, Muon, p1536, seed
1234, 1,221 steps) is running on TSAI's side, checkpoint saved only at the end. Items 1 and 2 therefore matter for
#475's own run (if it started, it was launched with some override of the v0 pin and some held-out copy; we only need to
know which, so the probe uses the same). Item 8 is now the job request in `jobs_draft/2026-11-17-g10-dryrun1-probe.md`.

Each note is one sentence of fact plus the ask, ready to paste. Evidence paths are in this work folder. Checked on lab
main `ae4c03d` (Team 5 harness) and the frozen tokenizer p1536 (sha256 e6b93a93…a64b). None of these were edited in
another team's files; G10-side fixes are in `research/repos/g10-capstone-rehearsal-wt` (uncommitted).

## Team 5 (Architecture)

1. **Tokenizer pin.** `harness/week2/artifacts.py` defaults `expected_tokenizer_sha` to tokenizer v0 (`2de039f2…`) and
   `train_week2.py` never overrides it, so the trainer refuses C3 and p1536 at startup.
   Ask: could the trainer take the tokenizer hash from the config or a flag (p1536 since the Gate 3 notice), so dry run
   1 does not need a code patch?

2. **heldout_v1 does not round-trip under the frozen tokenizer.** All 74 bn, pa and as documents of heldout_v1 (74 of
   1,059) fail `Artifacts.encode`'s exact byte check under both C3 and p1536, because the tokenizer's normaliser
   composes nukta forms (for example য + ় → য়), so `train_week2.py` stops while loading the official held-out file.
   Ask: do you want heldout_v1 re-issued with tokenizer-normalised text (new hash, same documents), or should bpb be
   scored on the normalised bytes? G9 and Team 3 probably need to agree the byte count. (Evidence: `artifacts/heldout_v1_bal60k.note.json`, the
   script in STATUS.md; the first check was a full pass over heldout_v1.)

3. **bf16 storage needs autocast.** `KE2.projected` returns fp32 by design, so a `LanguageModel` whose weights are
   stored in bf16 only runs under autocast (a plain bf16 forward stops with a dtype mismatch in the first attention
   projection). Not a bug for `train_week2.py` (fp32 weights under CUDA autocast); noting it because exporters and
   RL code that cast the whole model to bf16 will hit it. Ask: none, unless you want a one-line note in decisions.md.

4. **No KV cache.** `LanguageModel.forward` has no cache, so every generator re-runs the full sequence per token. G10
   now has its own cached decoder built from your modules (`rl-loop/g5_decode.py`, parity < 1e-4 against your forward,
   global attention only; local-window/sink/gate layers refused). Ask: if attn-2/3/4 become the baseline, tell us so we
   extend the decoder before the RL run.

## Team 4 (KE2)

5. **p1536 byte table.** We built the p1536 raw table locally with your `src/build_tables.py`: format v2, P32,
   131,072 unique rows, 0 truncated, 9 rows containing U+FFFD, content sha256 `21072027b19e…` (file sha256
   `e19a6cae8a6e…`). Ask: when you publish the official p1536 table hash, could you post it so we can confirm ours
   matches before anyone trains on it?

## Team 3 (Tokenizer)

6. **Encode is not byte-preserving for non-normalised text.** The p1536 (and C3) normaliser rewrites nukta and chillu
   sequences, so any text not already normalised decodes to different bytes than it was given. That breaks bpb byte
   counts and Team 5's strict loader (item 2). Ask: are Data A/B shards normalised before encoding, and can the release
   README say that `encode` is byte-exact only on normalised input?

## Team 12 (Quantization / serving)

7. **vLLM path for RL sampling.** G10's native sampler on the G5 model is now KV-cached (on a d128 stand-in: 8.7 → 258.6
   new tokens/s on MPS and 38.9 → 947.6 on CPU against the old re-forward loop, identical tokens), but a colocated vLLM sampler would still be
   faster at T2 size, and your `export_hf.py` (Granite MoE Shared) is the only route. Ask: once a dry-run-1 checkpoint
   exists, could you post the logit max-diff and top-1 agreement of the export on it with the p1536 tokenizer and our
   chat template, so we know whether objective_v1's trust-region ratio would see an engine gap?

## TSAI

8. **A checkpoint for G10, or a run on your side.** All G10 post-training evidence is on surrogate models; our
   rehearsal ran the whole SFT and RL chain on Team 5's code at d128 trained on this laptop. Ask: could TSAI either
   share one dry-run-1 run folder (manifest.json, checkpoint.pt, summary.json) with G10, or run our one-command
   day-one probe on it (job request draft `jobs_draft/2026-11-17-g10-dryrun1-probe.md`, outputs JSON only, < 1 MB)?

9. **Context length vs SFT data.** At the dry-run context of 2,048 tokens, 13.8% of OCR-2 rows fit untruncated (median
   5,677 tokens under p1536; Dolly 99.8%). Ask: is the post-training context of the capstone decided? SFT data v1's
   reasoning traces need 8k to 16k.

## G10 internal (our own code; fixed here or listed as follow-ups)

10. Fixed: `Team5Policy.sample` ran outside the trainer's autocast, so sampler and trainer would differ in precision
    (and a bf16-stored G5 model would crash while sampling).
11. Fixed: a G5 checkpoint is stored in fp32, so `fp32_master` converts nothing and the RL trainer ran the G5 model
    entirely in fp32; `train.autocast: bf16` now makes the compute dtype explicit.
12. Fixed: `Bundle.sample` projected every position through the 131,072-row head at each step; it now projects the
    last position only, and `model.kv_cache: true` uses the cached decoder.
13a. Open (DT on MoE): experts that receive no calibration token get no Wanda prior, so their random gate logits delete
    about half their weights under the hard mask (30 of 204 expert layers on the d128 stand-in; deletion at init 11.7%
    against the 5% prior). Needs a per-expert calibration floor or "keep" prior for unseen experts before DT is used.
13. Fixed: DT's target sets (`gate_proj` substrings) match nothing in the G5 model and a substring "o" would match
    everything; anchored `g5_*` sets added. DT's Wanda calibration crashed on G5 experts (they receive gathered rows,
    shared experts receive all flattened rows); the hook now handles both.
14. Fixed: a skipped adapter test had silently gone stale after durable trainer state added `evals.jsonl`.
15. Follow-up (not fixed here, overlaps PR 97's files): on 15 Nov at 17:03 IST seven verifier sandbox containers
    (`python:3.12-slim`, `--network=none --read-only`) were left running for 13 hours at ~100% CPU each, because the
    `docker kill` on timeout lives in the scoring process and that process was stopped. Fix: give the container its
    own limit (`timeout -s KILL <wall>` inside the container command, or `--stop-timeout` plus a reaper) in
    `rl/verifier.py` and `rl-data/stdio_check.py`.
