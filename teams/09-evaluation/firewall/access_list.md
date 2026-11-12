# Eval access list

Who may read the eval folder, as defined in [eval_firewall.md](eval_firewall.md), section 2. Last updated Wed 11 Nov 2026.

This list is a record, not a lock. It sets no permission. On the lab compute, TSAI places eval files only for an
approved Team 9 job (`eval_firewall.md`, section 3, rule 4). Everyone listed follows the handling rules in section 4 of
that file.

GitHub handles only: the repo is public, and a person is named only after they sign the consent form. A row with no
handle yet gives the team and `handle to confirm`. `to confirm` means the entry could not be confirmed from the repo or
the G9 group yet. Never add emails or keys here.

## 1. Standing access

| Handle | Role | From | Until | Also works on |
|---|---|---|---|---|
| `theschoolofai` | TSAI, runs approved jobs | 24 Oct | open | not applicable |
| `rahulni` | Team 9 lead | 24 Oct | open | Team 3 (weeks 2 to 3), Team 5 (weeks 3 to 5) |
| `Anusha-raju` | Core member | 24 Oct | open | to confirm |
| `maheshsv` | Core member | 24 Oct | open | Team 1 (week 2) |
| `Nisarg189` | Core member (role A) | 24 Oct | open | to confirm |
| `raghavTayal` | Core member (role C) | 24 Oct | open | to confirm |
| `Sagar063` | Core member | 24 Oct | open | to confirm |
| Team 9, handle to confirm | Core member | 24 Oct | open | to confirm |
| `shishir13` | Core member (role D) | 24 Oct | open | Team 12 (#259) |

## 2. Week-2 rotators: one benchmark, time-limited

Task: run one benchmark on one open model and add a row to `results/rotation_checks.md`.

Rotators count as Team 9 for that one benchmark, from 1 Nov until the row merges, and at the latest Sat 14 Nov
(`eval_firewall.md`, section 7, point 4). No `--log-samples`. After the row merges, delete the items and caches and add
the date here.

| Handle | From team | Benchmark (model) | Status on 4 Nov | Ended |
|---|---|---|---|---|
| `sandeepkunkunuru` | Team 8 lead | BBH (Qwen2.5-1.5B) | Row open, #199 | |
| `sureshmantha` | Team 7 lead | MuSR (Qwen2.5-0.5B) | Row merged, #251; deletion to confirm | 3 Nov |
| `udisinghania` | Team 5 | ARC-Challenge (Qwen2.5-1.5B) | Row merged, #303; deletion confirmed in G9 on 10 Nov | 10 Nov |
| `shank343` | Team 6 | BBH (llama-3.2-3b) | Row merged, #290; deletion confirmed in G9 on 5 Nov | 4 Nov |
| `millermuttu` | Team 7 | BBH (gemma-2-2b) | Row open, #279 | |
| `saitej123` | Team 10 lead | MMLU-Pro (Qwen2.5-1.5B) | Row open, #271 | |
| `arunnayan` | to confirm | to confirm | to confirm | |
| `tejaswivinnakota` (to confirm) | to confirm | to confirm | to confirm | |
| `vedang-patel-10` | Team 5 | MuSR (llama-3.2-3b) | Claimed | |

## 3. Week-3 rotators: no access needed

Task, from 15 Nov: run the decontamination check on 2 shards. That needs the fingerprints and the shards, not eval
files, so these rotators do not download any benchmark for this task.

| Handle |
|---|
| `avnishbm` (to confirm) |
| `rajiviyer` |
| `ranjani-cse` (to confirm) |
| `sourav-dhar` |
| `truesrini` |
| `tanmays369` |
| `TEJASKUMAR-REDDY-J` |
| `vedapragna-cs` |
| `patilvijay23` |

## 4. Accepted reads outside Team 9

TSAI accepted these on 4 Nov. They are recorded here so that the list matches what happens.

| Who | What they read | Where it shows | Decision |
|---|---|---|---|
| Team 12: `s9k96`, `SreekanthZipsy`, `therahulbhati` | Eval-mini items, for quantized formats | `teams/12-quantization/eval_mini/README.md`, #219 | Named exception under section 4 of `eval_firewall.md` (section 7, point 2) |
| Rotators and others on Team 12 runs: `TharunSivamani`, `ranjani-cse`, `shishir13` | Eval-mini items | #236, #259 and `TharunSivamani`'s rotation PRs | Same |
| Whoever runs Team 3's scripts | FLORES-200, HumanEval, MBPP; also GSM8K's train split, which the fingerprints do not cover | `teams/03-tokenizer/harness/run_harness.py`, `teams/03-tokenizer/train/fetch_heldout.py` | Allowed as measuring reads (`eval_firewall.md`, section 7, point 3) |

## 5. Everyone else

No access. Apart from section 4, any other student, and any job other than an approved Team 9 job, does not read the
eval folder. Everyone may read the fingerprints, scores and benchmark names, which are public.

## 6. How to change this list

1. Add your row by PR **before** you download an eval file. One change per PR.
2. The Team 9 lead reviews it. TSAI approves the lead's own changes.
3. When access ends, add the date by PR. Do not delete the row, because the list is the record of who held the files.
