# Dry run 1 full-run evidence (exp2_muon, T2, seed 1234, frozen p1536)

Follow-up to #475. The evidence folder committed on `2026-11-15-dryrun1` held only
the 3-step smoke run (`status: SMOKE`). This folder holds the full run TSAI used
for the Gate 2 / Gate 3 dry run 1 number, rerun from the same `cmd.sh`.

- status: COMPLETED, 1221 steps, exit 0
- final `val/bpb`: 1.5159 (matches the dry run 1 number already in the week 3 tracker
  and in #491's restore-drill baseline)
- `final_model_sha256`: `93e5f454c8a583eb2552006c0272c2c36fc1deed3e605ec9c46af797ffe81981`

No hardware name, model, or timing details beyond `wall_seconds` from the run's own
summary.json are added here.
