# Scripts behind the code sheet

These make `sheets/medicine_code.md`, `sheets/decisions_code.md` and `results/sheets/`. Picks and reasons are written by hand in `compile_medicine_code.py`; every number is computed.

| file | what it does |
|---|---|
| `run_all.py` | Runs the steps below that make files. Start here. |
| `collect_inputs.py` | Copies the latest code `labels.csv` and `medicine.md` of every open PR into a checkout. |
| `compile_evidence.py` | Runs every medicine on every pack: `results/sheets/evidence.json`, IDs only. |
| `compile_medicine_code.py` | The picks. Writes `medicine_code.md` and `decisions_code.md`. Copies each rule from its author's code, then checks the copy behaves the same on every doc. |
| `e3_rule.py` | Source of the new rule `DA-E3-004`. |
| `verdict_block.md` | Top of `decisions_code.md`, by hand. |
| `inputs/code-go_medicine.md` | Input for the code-go rules. PR 73 has an older file, and a later file merges the two E3 rules. |
| `audit_final.py` | What the harm test cannot see: code changed, idempotence, guard, residue, risky drops, order reversed. |
| `post_clean.py` | Stage 90: empty docs, and docs left with no code. |
| `stress_docs.py` | Which disputed docs the sheet touches, and which reader disputes each. |
| `regex_on_issues.py` | What the picked rules catch on labelled rows, what the missed rows look like, and the short-note E4 option. |
| `e1_triggers.py` | Why `DA-E1-008` drops each js-ts file, and `DA-E4-006` against `DA-E4-007`. |
| `sheet_compare.py` | Two sheets over all packs: which docs end differently. |

## Reproduce

Needs the 6 code packs as `<packs>/code-<lang>.parquet`, `pyarrow`, and a local clone with `origin` (`theschoolofai/era-v5-lab`). `open_prs.json` is the API list of open PRs, with `number` and `updated_at`.

```
git fetch origin main "+refs/pull/*/head:refs/remotes/pr/*"
git worktree add --detach <checkout> bae5163
python -I collect_inputs.py <clone> <checkout> open_prs.json
```

Then from `<checkout>`:

```
cp <spec>/scripts/inputs/code-go_medicine.md teams/01-data-a/medicines/submissions/code-go/TEJASKUMAR-REDDY-J/medicine.md
python -I teams/01-data-a/tools/medicine_extract.py --dir teams/01-data-a/medicines/submissions --registry teams/01-data-a/rules/registry.json
python -I teams/01-data-a/tools/build_gold.py --include-open-prs --allow-disputed --pack-prefixes code- --out <stress gold>
```

Then the sheet and its results, followed by the checks:

```
python -I run_all.py <checkout> <packs> --stress-gold <stress gold>
python -I audit_final.py <checkout> <packs>
python -I post_clean.py ../sheets/medicine_code.md <packs>
python -I stress_docs.py <checkout> <packs> <stress gold>
python -I regex_on_issues.py <checkout> <packs>
```

PRs keep moving. `results/sheets/inputs_manifest.json` holds the digest of every input used here, so compare against it before trusting a rerun. New inputs give new numbers and can shift rule IDs.

`build_gold.py` reads the open PRs from GitHub, so it needs a token, and it reads their latest state.
