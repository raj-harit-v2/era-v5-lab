# Eval firewall

Rule v1, written by the Team 9 lead on Tue 3 Nov 2026 and updated on Wed 4 Nov with TSAI's review. Section 1 is TSAI's
rule. Sections 2 to 5 are how it applies. Section 6 was checked on `main` at `3a835ef`. Section 7 records TSAI's decisions.

Who may read: [access_list.md](access_list.md). Paths are under `teams/09-evaluation/` unless they say otherwise.

## 1. The rule

> Only Team 9 and TSAI read the eval folder. No training job reads it.

**What holds this rule.** The job rule (section 3), the fingerprint and canary checks (section 5), and people following
the handling rules (section 4). On the lab compute there is no shared eval path (section 3, rule 4).

## 2. What "the eval folder" means

The lab repo is public, so the eval folder cannot be `teams/09-evaluation/`. It means the files that hold benchmark
item text, wherever they are. TSAI confirmed this reading (section 7, point 8).

| Inside the firewall: restricted | Outside: public, anyone may read |
|---|---|
| Benchmark questions, answers, prompts, few-shot examples, solutions and tests | Benchmark names, licences, counts and pins (`benchmarks_v1.md`, moving out of `benchmarks/` in #174; `decontam/benchmarks.toml`) |
| Built item files (`harness_code_indic/runs/eval_mini_v0_items.json`) | Fingerprint sets and their canary files (`fingerprints/`). Teams 1, 2 and 10 need them. |
| Per-item logs with text (`harness_code_indic/runs/<model>/<tag>/samples_<n>.jsonl`, from `--log-samples`) | Score files (`results/*.json`, `results/compare_*.md`) and `eval_mini_v0_spec.json` |
| Dataset caches that hold a benchmark (`runs/`, `hf_cache/`, any Hugging Face cache) | Per-item rows with only task, doc ID, filter and metric values |

Where the files may be:

| Place | Status |
|---|---|
| Lab compute | No shared eval path. Only in an approved Team 9 job's own folder (section 3, rule 4) |
| Own machine, Colab, Kaggle | Only for people on the access list, under section 4 |
| Any Git repo or fork, PR, issue, chat or paste site | Never |

## 3. The job rule

This is the main protection. The benchmarks are public downloads and people rotate between teams, so a rule about
people alone cannot hold. Jobs are different: under `JOB_REQUEST.md` a script has no network and reads only its
inputs, so the request, its config and its script show what the job can read.

Two paths never go through a job request: full-data cleaning, which TSAI applies itself (`JOB_REQUEST.md`, rule 6),
and the main run (Team 7 `USER_GUIDE.md`, section 1.2). The rule applies to them too, but no request
or audit shows it, so the shard check in section 5 is what holds there.

A **training job** is any job that makes or changes what the model learns from: model training, tokenizer training,
data cleaning, data selection, post-training data.

1. A training job never names the eval folder or a benchmark dataset in `Inputs:`, `Config:` or `Command:`.
2. Only a Team 9 job reads eval item files, unless section 7 gives an exception.
3. Reading a fingerprint set is not a read of the eval folder. Any team may run `decontam_check.py` and `canary_scan.py`.
4. There is no shared eval path on the lab compute. TSAI places eval files only for an approved Team 9 job, in that
   job's own folder, and deletes them when the job ends. An eval job never runs on a training node (Team 7
   `USER_GUIDE.md`, section 4).
5. An eval job writes scores only. TSAI returns a job's logs and results to this public repo, so an eval job does not
   use `--log-samples` and writes no item text to `./out/` or to its log. Before the results come back,
   `canary_scan.py out <job log> --lab-only` must exit 0.

**Who checks.** The team lead and TSAI read the `Inputs:`, `Config:` and `Command:` lines, and the config and script
they point to, when they approve a request. Team 9 also runs this before each gate and sends any hit to TSAI. It
searches the request files only, so it does not see inside a config or a script. A hit is a question, not proof of a
breach:

```
git grep -n -i -E 'gsm8k|mmlu|milu|humaneval|mbpp|hellaswag|arc.challenge|arc.easy|truthfulqa|bbh|musr|belebele|flores|in22|gpqa|aime.20|[^a-z]hle[^a-z]|gaia|longbench|swe.bench|livecodebench|codeforces|terminal.bench|bfcl' -- 'teams/*/jobs/*.md'
```

## 4. Handling rules

These apply to everyone on the access list.

1. Item text goes in no repo, fork, PR, issue, chat, paste site or public notebook. Quote only the task, the document
   ID and the offset.
2. Per-item logs with text never go in Git. Rotators do not use `--log-samples` at all (`results/rotation_checks.md`).
   A core member who needs one to debug keeps it under the gitignored `runs/` and deletes it afterwards.
3. Colab and Kaggle notebooks stay private, with no public version or dataset that holds items or text outputs.
4. Keep eval work apart from other work: its own folder and its own Hugging Face cache (`HF_HOME`). No data, tokenizer
   or training script reads that folder or cache.
5. If you also work on a data, tokenizer or training task, say so in the access list. Never use item text in that work.
6. When your access ends, delete the items, logs and caches, and add the end date to the access list.
7. A new script that writes eval items stamps them with the lab canary: `lab_canary.stamp()` for JSON,
   `lab_canary.MARKDOWN_LINE` for Markdown. The full canary string is never written out whole in this repo.

## 5. What catches a leak

| Layer | Catches | Misses |
|---|---|---|
| Job rule (section 3) | A training job that names an eval file or a benchmark | Text copied by hand; a benchmark inside a larger dataset; work on own machines, full-data cleaning and the main run, none of which reach a job request |
| Fingerprints (`decontam_check.py`, the formal check) | A copy of an item from any benchmark in the set's `MANIFEST.json` | Benchmarks that are not in the set |
| Canary (`canary_scan.py`) | Text copied from a stamped file | A copy from the public source, or from any file that was not stamped |

**When the checks run.** Every shard passes `decontam_check.py` and `canary_scan.py` before a training job reads it, and
the report keeps the `set_sha256`. Teams 1, 2 and 10 run the checks on their data. TSAI runs them on the full-data
clean (section 7, point 7).

**Known gap.** Fingerprints v1 has 17 benchmarks. `decontam/benchmarks.toml` has no row for ARC-Challenge, ARC-Easy,
HellaSwag, TruthfulQA, MMLU-Pro, BBH, MuSR, HumanEval, HumanEval+, MBPP, MBPP+ or Belebele, and Team 9's harnesses run all
of these. If one of them enters training data from its public source, neither check finds it, so only the job rule
stands. The planned v2 additions do not close this. Any score on these tasks for a lab checkpoint must say that the
task was not decontaminated (`results/eval_mini_lab_ckpts.md`, due Fri 13 Nov).

**If a check hits:**

1. Stop using that shard or file.
2. Post in the G9 group and tag TSAI. Give only the canary or item ID, the document ID and the offset, never the text.
3. TSAI decides what happens to the data. The hit stays on record, even if it is later explained.

For `canary_scan.py`, exit code 1 means a canary was found. Exit code 2 means a file could not be read, so the scan
is incomplete. Neither is a pass.

## 6. State on Tue 3 Nov

Text searches of tracked files at `3a835ef`, plus the open PRs named below. They say nothing about machines, Colab,
Kaggle or other repos.

| Check | Result |
|---|---|
| Job requests on `main` (2 files) | No benchmark named |
| Job requests in open PRs (#239, #244; 3 files) | No benchmark named |
| Scripts that load a benchmark by dataset name, outside Teams 9 and 12 | Only Team 3 (section 7, point 3) |
| Per-item logs on `main` | 79 `*.samples.jsonl` files under `teams/12-quantization/`, 21,458 rows: only `task`, `doc_id`, `filter` and metric values, no item text |
| Lab canary GUID in the repo | Only in `decontam/lab_canary.py`, in parts, as designed |

## 7. TSAI's decisions

From TSAI's review of this rule on Wed 4 Nov.

| # | Question | Decision |
|---|---|---|
| 1 | Where is the eval folder on the lab compute? | There is no shared eval path. TSAI places eval files only for an approved Team 9 job, in that job's own folder, and deletes them when the job ends. |
| 2 | Do Team 12's eval-mini runs count as eval reads? | Yes, as a named exception under section 4. Team 12 removes the pointer in `teams/12-quantization/eval_mini/README.md` to the old fork commit. |
| 3 | Do Team 3's measuring scripts count? | Allowed. `teams/03-tokenizer/harness/run_harness.py` and `teams/03-tokenizer/train/fetch_heldout.py` are measuring reads, and no eval text may reach a training corpus. Team 3 corrects the line in `teams/03-tokenizer/train/v2_spec.md` that says no v2 script reads these benchmarks. |
| 4 | Do rotators count as Team 9? | Yes, for their one benchmark, until their row merges and at the latest Sat 14 Nov. |
| 5 | Is Team 5's held-out set inside the firewall? | No. Fingerprints v2 include it, so no training document may contain it. |
| 6 | Who tells the other teams? | TSAI announces the rule in CAP after this merges. |
| 7 | Who checks training data, and when? | Every shard passes `decontam_check.py` and `canary_scan.py` before a training job reads it, and the report keeps the `set_sha256`. Teams 1, 2 and 10 run the checks on their data. TSAI runs them on the full-data clean. |
| 8 | Is section 2 the right reading of "the eval folder"? | Yes. "Publishes" in TSAI's 2 Nov note means a restricted location. Fingerprints and scores stay public. |
