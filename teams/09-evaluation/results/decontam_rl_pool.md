# Decontamination of the RL prompt pool (Team 10, RL data v1)

G9 Evaluation, week 3, task 5. Author: shishir13. Status: **complete**. All 6 pool files are checked and the Codeforces side check is done.

No benchmark text, no pool text and no prompt appears in this file or in the PR. Only ids, counts and hashes.

## 1. Result

Full fingerprint set, `decontam_check.py`, 13-word prose / 20-token code runs, `--min-hits 1` (default). v2 is the main result; v1 is the second column.

| Pool file | Docs | sha256 of the file (matches #564) | v2 flagged (main) | v1 flagged |
|---|---|---|---|---|
| rl-code-v1-close | 3,577 | 71e000f4a34081a8b9d45e9558747fa69de44c1c6a0770ad2d2a6e3b0b3efbfc | 0 | 0 |
| rl-math-v1-reserved | 7,209 | f90a7b1fe5a6b1c946151a2bf69fe85b605c7ce7d487a5c26776fd8523f3c25a | 0 | 0 |
| rl-code-code-contests-noncf | 3,723 | 84b0a645882fd3c518eb543432f3758bbde564e9aab3dca99e534834abc2b5f1 | 0 | 0 |
| rl-math-hendrycks-math-train | 7,234 | 5148ce7a52f8767755957d8981bc9db3a62d8049fcc3369835223762d8180de4 | 0 | 0 |
| rl-code-v1-train | 3,251 | cd1aa76ef1216f6fc6fdcf63fc0b69c98fa6a5d58a510f28be9050fecbedcce1 | 0 | 0 |
| rl-code-v1-heldout | 255 | 935857bb0246172aa0439445dd54ef9bbbe282ad2b5ea87ddd100429c9e31ae5 | 0 | 0 |

Fingerprint sets (both printed by the tool in its summary line):

| Set | Folder on main | set_sha256 |
|---|---|---|
| v2 (main result) | `teams/09-evaluation/fingerprints/v2` | 2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a |
| v1 | `teams/09-evaluation/fingerprints/v1` | 11e290a44d1467875fdf8bebc55eab21f0a6367f411aab98a4a027a546fd372e |

v2 is the set task 2 used on all 41 shards and the set #564 pins. Both sets give 0 flagged documents on all six files (25,249 documents).

## 2. How the pool was obtained

The six pool files were not available on main or in a PR at the time of this check. They were rebuilt from the inputs pinned in
`teams/10-post-training/rl-data/rebuild_v1/pins_v1.json` (Team 10, #564), with Team 10's own script:

1. Downloaded the pinned inputs and checked each file's size and sha256 against the pins: 39 code_contests train parquets (revision 802411c3,
   7,509,753,086 bytes), 7 hendrycks_math parquets (revision 21a56338) and the MATH-500 `test.jsonl`. All matched.
2. Extracted the Team 9 decontam tools at commit b470b4c0 (`git archive b470b4c0`), as `rebuild_v1.py --g9-tools` requires.
3. Ran the rebuild on **Linux** (WSL, Ubuntu, Python 3.14, pyarrow 26), with the two private id lists that Team 10 shared for this check
   (`rl_heldout_v1_ids.txt`, 255 ids, sha256 0e2c6f78...9163; `sft_heldout_match_ids.txt`, 82 ids, sha256 105103be...f160; both equal the
   pins in #564). The lists are not in this PR:

```
python teams/10-post-training/rl-data/rebuild_v1/rebuild_v1.py --cc-dir <code_contests/data> --math-dir <hendrycks_math>   --math500 <math500/test.jsonl> --g9-tools <teams/09-evaluation/decontam at b470b4c0> --out <out>   --rl-heldout-ids <rl_heldout_v1_ids.txt> --sft-heldout-match-ids <sft_heldout_match_ids.txt>
```

4. `rebuild_v1.py` compared its 14 expected outputs with `pins_v1.json`: **14 of 14 match, no mismatches**. All six pool files match the sha256
   in #564 byte for byte (table in section 1). A first run without the two lists matched 12 of 14 (train and held-out were not built).
5. A first run on Windows did not reproduce the hashes: Windows writes CRLF line endings, and the step scripts must also be LF to match their pinned
   sha256. Use Linux for this rebuild.

## 3. Commands

For each pool file `<file>` (from the folder `teams/09-evaluation/decontam`), once with v2 and once with v1:

```
python decontam_check.py <file>.jsonl --fingerprints ../fingerprints/v2 --id-field id --text-field text
python decontam_check.py <file>.jsonl --fingerprints ../fingerprints/v1 --id-field id --text-field text
```

No `--benchmarks`, `--tags` or `--exclude`: this is the formal check against the full set. Each run printed
`docs <n> flagged 0 (0.00%) by benchmark {}` and wrote no flagged line. The tool prints ids, benchmark item ids and offsets, never text.
Fingerprints are the files on main; `fingerprints/.gitattributes` keeps their bytes unchanged on Windows.

## 4. rl-code-codeforces is not part of RL data v1

Sai Teja confirmed on 18 Nov that `rl-code-codeforces` is a separate set and not in RL data v1. Its own numbers from Team 10: 8,891 rows kept
of 9,556, clean v2 sha256 `220b2f86a415…`, and 41 rows excluded by policy (contests 1990, 1991, 1992, 1994, 1995, 1996, 1997; ids in
`teams/10-post-training/rl-data/rl-code-codeforces.excluded_ids.jsonl`). The six files above contain no Codeforces rows: the judges in the
code pool are aizu, atcoder, codechef and hackerearth.

Side check (Nisarg's 12 Nov ask): a Div. 1 problem reworded for Div. 2 shares no 13-word run with the benchmark but sits in a neighbouring contest id.
`decontam/contest_id_check.py` (added in this PR, with `tests/test_contest_id_check.py` and a README section) compares contest ids only:

```
python contest_id_check.py --benchmark <open-r1/codeforces test parquet> --pool <rows.jsonl> --window 3 --out report.json --drop ids.txt
```

The benchmark (open-r1/codeforces test, revision fbe3f6e9, parquet sha256 f3e241f6…) has 468 problems in 64 contests with ids 1993 to 2067.
The 41 policy-excluded rows are all within 3 contest ids of benchmark contests 1993 and 1998 to 2000, so the policy drop covers the neighbours.
Team 10 shared the ids of the 8,891 kept rows (`rl-code-codeforces.kept_ids.jsonl`, one `{contest_id, problem_id}` per line, 1,777 contests,
sha256 49b19bdcf6470f47563cf406fe01086c71ab49393ab19bc69bf5af06bb95e1f4; ids only, not in this PR). Result with `--window 3`:

| Measure | Value |
|---|---|
| rows | 8,891 |
| rows without a readable contest id | 0 |
| pool contests | 1,777 |
| rows in a benchmark contest (distance 0) | 0 |
| rows in the next contest (distance 1) | 0 |
| rows within 3 contest ids | 0 |

No kept row is in or next to a benchmark contest. This agrees with the policy drop: the 41 excluded rows were the neighbours.

## 5. Not covered

Nothing is pending. This check covers the six RL data v1 pool files and the kept rl-code-codeforces ids. It reads the pool as rebuilt from the pinned
inputs, not a copy of the files from Team 10's job output; the sha256 values above show they are the same bytes.
