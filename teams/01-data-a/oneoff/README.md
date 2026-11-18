# One-off scripts: how the code sheet was made

> **Kept for the record, not part of the pipeline.** These scripts built the code family's sheet from the open PRs of one day. Run them from this folder (`teams/01-data-a/oneoff/`) against the old `bae5163` checkout; they write into `spec_v1/`. Script owners: delete the ones you no longer need.

These make `spec_v1/sheets/medicine_code.md`, `spec_v1/sheets/decisions_code.md` and `results/spec_v1/sheets/`. Picks and reasons are written by hand in `compile_medicine_code.py`; every number is computed.

| file | what it does |
|---|---|
| `run_all.py` | Runs the steps below that make files. Start here. |
| `collect_inputs.py` | Copies the latest code `labels.csv` and `medicine.md` of every open PR into a checkout. |
| `compile_evidence.py` | Runs every medicine on every pack: `results/spec_v1/sheets/evidence.json`, IDs only. |
| `compile_medicine_code.py` | The picks. Writes `spec_v1/sheets/medicine_code.md` and `spec_v1/sheets/decisions_code.md`. Copies each rule from its author's code, then checks the copy behaves the same on every doc. |
| `e3_rule.py` | Source of the new rule `DA-E3-004`. |
| `verdict_block.md` | Top of `decisions_code.md`, by hand. |
| `code-go_medicine.md` | Input for the code-go rules. PR 73 has an older file, and a later file merges the two E3 rules. |
| `audit_final.py` | What the harm test cannot see: code changed, idempotence, guard, residue, risky drops, order reversed. |
| `post_clean.py` | Stage 90: empty docs, and docs left with no code. |
| `stress_docs.py` | Which disputed docs the sheet touches, and which reader disputes each. |
| `regex_on_issues.py` | What the picked rules catch on labelled rows, what the missed rows look like, and the short-note E4 option. |
| `e1_triggers.py` | Why `DA-E1-008` drops each js-ts file, and `DA-E4-006` against `DA-E4-007`. |
| `sheet_compare.py` | Two sheets over all packs: which docs end differently. |
| `speed_compare.sh` | Not part of the code sheet. The one script for the `clean.py` speed-up routine: run it once per rule, before committing: `speed_compare.sh --rules <RULE_ID>`. Checks that clean.py is the fresh build, pytest passes, the output sha256 is unchanged and the harm tests are unchanged, measures docs/s and per-rule time, counts the documents the rule changes, and prints a SUMMARY for the log entry in `results/spec_v1/speed_v1.md`. `--sheet FILE` makes the build check use another sheet than `specv1.md` (for example the combined `spec_v1_1/sheets/specv1_1.md`); the other steps test `clean.py` itself. `--before-clean FILE` and `--after-clean FILE` use a given `clean.py` instead of the one in a revision, for a change that is in a sheet (for example `specv1_1.md`) but not yet in the committed `clean.py`. `-h` lists the options. |
| `speed_check.py` | Called by `speed_compare.sh`: `run` hashes and times a `clean.py` per pack, `compare` shows whether two runs have the same output sha256 and the docs/s change, `count` gives how many documents a rule fixes or drops. |
| `speed_handoff.md` | Handoff for the speed-up routine: setup, scratch folder, backup of the starting `clean.py`, the steps for each rule, how to avoid merge conflicts, and what is different for the Indic rules. |

## Reproduce

Needs the 6 code packs as `<packs>/code-<lang>.parquet`, `pyarrow`, and a local clone with `origin` (`theschoolofai/era-v5-lab`). `open_prs.json` is the API list of open PRs, with `number` and `updated_at`.

```
git fetch origin main "+refs/pull/*/head:refs/remotes/pr/*"
git worktree add --detach <checkout> bae5163
python -I collect_inputs.py <clone> <checkout> open_prs.json
```

Then from `<checkout>` (the old layout, so the harness is still under `tools/` there; `<oneoff>` is this folder in your current clone):

```
cp <oneoff>/code-go_medicine.md teams/01-data-a/medicines/submissions/code-go/TEJASKUMAR-REDDY-J/medicine.md
python -I teams/01-data-a/tools/medicine_extract.py --dir teams/01-data-a/medicines/submissions --registry teams/01-data-a/rules/registry.json
python -I teams/01-data-a/tools/build_gold.py --include-open-prs --allow-disputed --pack-prefixes code- --out <stress gold>
```

Then the sheet and its results, followed by the checks:

```
python -I run_all.py <checkout> <packs> --stress-gold <stress gold>
python -I audit_final.py <checkout> <packs>
python -I post_clean.py ../spec_v1/sheets/medicine_code.md <packs>
python -I stress_docs.py <checkout> <packs> <stress gold>
python -I regex_on_issues.py <checkout> <packs>
```

PRs keep moving. `results/spec_v1/sheets/inputs_manifest.json` holds the digest of every input used here, so compare against it before trusting a rerun. New inputs give new numbers and can shift rule IDs.

`build_gold.py` reads the open PRs from GitHub, so it needs a token, and it reads their latest state.
