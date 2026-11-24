# Team 10 Week 4 Execution Plan & Gate 4 Tracker (Sun 22 Nov – Sat 28 Nov 2026)

Active branch: `g10-week4-post-training` (cut cleanly from `main` `a2e7fc6a` after `#681`, `#693`, `#684`, `#697`, `#608`, `#694`, `#686`, `#700`, and `#669` merged). Public text names teams and GitHub handles only.

## 1. Gate 4 Objective (due Fri 27 Nov, 11:59 PM IST; Go/No-Go Sat 28 Nov)

Per TSAI rulings (21 Nov 2026), closing **Gate 3 item 7 (SFT/RL method)** requires **both** results on the **dry run 2 checkpoint** (test-scale + untied KE2/KAS output head `a10_kas_tokdrop` + Team 7 `Checkpointer` with `probe_loss` via `#608`):
1. **DT vs LoRA vs Full FT** at equal optimizer steps (`capstone/dryrun2_dt_compare.py`, `jobs/2026-11-26-g10-dryrun2-dt-vs-fft.md`) — paper-repo 17 Nov DT settings (`g5_gate`, `lr 5e-4`, `alpha 100 -> 1000`, `eta 1/2048`, `lambda 1e-5 -> 0`, `band_at_init`).
2. **DT-then-RL chain** (`jobs/2026-11-17-dt-then-rl-code.md`, `rl-loop/config/task11_code_canary.yaml`) run on the kept DT arm's three canary files (`model.safetensors`, `dt_keep_masks.bin`, `dt_keep_masks.bin.json`).

## 2. Official 21 Nov TSAI Rulings (applied on `main` via `#693`)

- `sft-indic-nemotron-personas-india`: **`excluded`** (untraceable generator model).
- `rl-math-hendrycks` (7,209 reserved MATH tasks): **`excluded`** from RL v1 training (benchmark data never trains the model).
- `python2_only` (1,545 code tasks): **kept** in RL v1 (`3,577` close pool / `3,251` train / `255` held-out).
- **Indic RL templates:** proceed with programmatic value fills on human-written templates, conditional on **Team 2 native-reader sign-off** before admission.
- **Eval-mini / firewall split:** Team 9's watcher scores ARC-Challenge & HellaSwag on base + kept SFT checkpoints in bf16 autocast (divided by 100 for `forgetting.py`); Team 10 runs held-out bpb only (`sft/bench/evaluate.py --metrics forget --dtype auto`). `jobs/2026-11-18-g10-eval-mini-forgetting.md` is withdrawn.
- **`#565` & `#587`:** Team 9 cleared `#565`'s Codeforces decontamination read on the access list (`#697`); TSAI is queuing `#565` and `#587`.

## 3. Critical-Path Schedule (D1–D7)

| Day | Date | Milestone / Team 10 Deliverable |
|---|---|---|
| D1 | Sun 22 Nov | Cut clean `g10-week4-post-training`; land `dryrun2_dt_compare.py` + KE2/KAS head readiness guards (`sft_g5.py`, `keep_weights.py`) + lead route decision in `g10-sft-keep-weights.md`. |
| D2 | Mon 23 Nov | Audit Team 5's KE2/KAS `model.py` integration (`#694`/`#702`/`#706`) against `team5_adapter.py`, `sft_g5.py`, `dt/mask.py`, `keep_weights.py`, `make_probe_file.py`; begin Indic human templates with Team 2. |
| D3 | Tue 24 Nov | **Dry run 2 starts.** Complete **Team 7 Checkpointer wiring verification (both ways)** against `#608` (`team7_checkpoints.py`) + Team 9 `run_lab_ckpt.py`. |
| D4 | Wed 25 Nov | Attach local CPU stand-in logs for `jobs/2026-11-26-g10-dryrun2-dt-vs-fft.md` and `jobs/2026-11-17-dt-then-rl-code.md` on Team 5's KE2/KAS model class; review `#587` & `#133` (E9 1.7B) results if returned. |
| D5 | Thu 26 Nov | **Dry run 2 ends (blocked until `corpus-v1` shards exist per Team 5, 23 Nov).** Receive checkpoint from Team 5 (`#608` store, no new manifest field); submit dry-run-2 DT vs LoRA vs Full FT job immediately, then DT-then-RL canary on `keep_canary/dt/`. Deliver Team 9 `eval_schedule.md` item #7 checkpoint schedule. |
| D6 | Fri 27 Nov | Record dry-run-2 DT vs LoRA vs Full FT (`results/dt_vs_fft.md`) and DT-then-RL (`results/dt_then_rl.md`) + `results/gate4_summary.md`. **Gate 4 evidence due 11:59 PM IST.** |
| D7 | Sat 28 Nov | Gate 4: Go or no-go on the main training run. |

## 4. Team 10 Workstream Owners (updated 23 Nov — remaining items rebalanced)

| Track | Scope | Files |
|---|---|---|
| Lead (`saitej123`) | Gate 4 orchestration, dry-run-2 comparison wrapper & job draft, `g5_batch` RL wiring, `#142` Qwen3 ladder approval, Team 5/7/9 handoffs, PR merges, `results/gate4_summary.md` | `capstone/dryrun2_dt_compare.py`, `jobs/2026-11-26-g10-dryrun2-dt-vs-fft.md`, `jobs/2026-11-23-g10-dt-large-model.md`, `results/gate4_summary.md` |
| KE2/KAS + Dry Run 2 Pipeline (`f20201351h-maker`) | `#135`, `#139`–`#145` merged (KE2/KAS head/input adapter, `g5_batch` 12.8x sampler, `run_folder_from_store.py`, Qwen3 4B/8B ladder). Next: re-verify after Team 5 `#717` merges + analyze returned `#565`/`#587`/`#133`/`#142` logs | `rl-loop/team5_adapter.py`, `capstone/`, `jobs/2026-11-26-g10-dryrun2-dt-vs-fft.md` |
| DT-then-RL Chain (`Hemaaaa04`) | Update `jobs/2026-11-17-dt-then-rl-code.md` & `rl-loop/config/task11_code_canary.yaml` for dry run 2 (KE2/KAS, `g5_batch`, `66` free-reward ids, `keep_canary/dt/`), verify `keep_zero`, record `results/dt_then_rl.md` | `jobs/2026-11-17-dt-then-rl-code.md`, `rl-loop/config/task11_code_canary.yaml`, `results/dt_then_rl.md` |
| Team 7/9 Bridge & Phi-MoE Baselines (`RaviNaik`) | `#136`, `#138`, `#146`, `#147` merged (`watcher_rows_to_report.py`, dtype guard, `#608` store check, 7.65B `Phi-mini-MoE` DT). Next: add LoRA/Full-FT baselines to `results/dt_phi_moe.md` + dry-run-2 forgetting verdicts | `results/dt_phi_moe.md`, `capstone/watcher_rows_to_report.py`, `sft/tests/forgetting.py` |
| DT Table & Effort v2 (`thinkTinkerGreen`) | API-Bank / `Nemotron-SFT-Agentic-v2` overlap check (`eval/README.md`) + dry-run-2 **DT vs LoRA vs Full FT** results table in `results/dt_vs_fft.md` | `results/dt_vs_fft.md`, `eval/` |
| Indic RL Templates (`gmrammohan15`, plus Tamil templates by `ranjani-cse`) | Author human-written templates in `rl/indic/templates/indic_templates.yaml`, run `generate.py --check` + Team 9 decontam + Team 2 native-reader sign-off (`team2_reviewer`) | `rl/indic/templates/indic_templates.yaml`, `rl/indic_prompts_v0.md` |
| Verifier Hardening & Licence Hygiene (`AjaySnl`, `ranjani-cse`, `LokeshJatangi`, `naveen333nav`, `jssunil`, `rl/agentic` owner) | Edge-case hardening & Docker checks across `rl/js/`, `rl/math/`, `rl/tool_call_verifier.py` (+ `#686` template parity), `rl/toolresult/`, `rl/jsts/`, `rl/agentic/` (+ `stdio_check` / `free_reward_ids`), and `licences/licence_table.md` | `rl/`, `licences/licence_table.md` |
