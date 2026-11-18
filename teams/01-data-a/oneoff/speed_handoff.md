# Handoff: speeding up slow rules in clean.py

The routine for making a slow rule in `clean.py` faster without changing its output, and for logging it. It was worked out on the English rules (`DA-F1-005`, `DA-D3-003`, `DA-C5-002`, `DA-B4-010`); section 7 covers what is different for the Indic rules, which are the next job. Read [results/spec_v1/speed_v1.md](../results/spec_v1/speed_v1.md) first: it is the log you add to: each fix is one row in two tables and one line of text.

## 1. The task

Before cleaning at scale (Gate 2), `clean.py` must be faster on raw web text. A few rules take most of the time while changing under 1% of documents. For each slow rule: find it with the profile, make it faster **without changing the output**, and prove three things:

1. the output sha256 of every pack is the same before and after (the sha256 covers each document's `doc_id`, final action and final cleaned text, in order, so equal means byte-identical),
2. the harm tests give the same results,
3. the whole pytest suite passes.

Then add an entry to the speed log: docs/s before and after, what the fix was, and how many documents the rule changes.

## 2. The tools (all in `oneoff/`)

| tool | use |
|---|---|
| `speed_compare.sh` | **the one you run, once per rule, before you commit it.** It runs `build` (clean.py is the fresh build), `pytest`, `trees` (before = the last commit, after = your working copy), `speed` (output sha256 and docs/s on every pack), `profile` (per-rule time), `harm` (harm tests, before against after) and `count` (documents the rule changes), then prints a SUMMARY with the figures for the log entry and `RESULT: PASS` or `FAIL`. Everything is saved in `$WORK/run-<time>.log`. `speed_compare.sh -h` lists the options; `--sheet FILE` makes `build` check `clean.py` against another sheet than `specv1.md` (for example the combined `spec_v1_1/sheets/specv1_1.md`). Only `build` reads a sheet: `speed`, `profile`, `harm` and `count` run the `clean.py` of each tree. `--before-clean FILE` and `--after-clean FILE` put a given `clean.py` in a tree instead of the one in `--before` / `--after`, for a change that is in a sheet but not yet in the committed `clean.py` (build both with `build_clean.py --sheet ... --out FILE`). |
| `speed_check.py` | the measuring part, called by `speed_compare.sh`: `run` hashes and times `clean.py` on each pack, `compare` shows whether two runs have the same output sha256, `count` counts the documents a rule changes. You rarely call it directly. |

Run them in a plain terminal, not inside VS Code (long runs can crash it). Never run two timing runs at the same time: on this laptop CPUs 0 and 1 are two threads of one core, so they slow each other (`speed_compare.sh` pins to CPU 0).

## 3. One-time setup

From the repository root. `$PARENT` is the folder that holds `week1-packs` and `week-2`.

```bash
cd <path>/era-v5-lab
PY=/home/forest/miniconda3/envs/era5/bin/python           # any Python with pyarrow
PARENT=$(dirname "$PWD")
WORK=$PARENT/scratchpad/clean-speed-mine                  # your scratch folder: outside the repo, survives a reboot
mkdir -p "$WORK"

# back up the cleaner you start from and note where you started (your safety net)
START=$(git rev-parse --short HEAD)
cp teams/01-data-a/spec_v1/clean.py "$WORK/before-clean.py"
echo "start commit $START, clean.py $(sha256sum teams/01-data-a/spec_v1/clean.py | cut -c1-12)" | tee "$WORK/START.txt"
```

Get the original back any time with `git show $START:teams/01-data-a/spec_v1/clean.py`, or rebuild the current one with `python -I teams/01-data-a/spec_v1/build/build_clean.py`. At the end, `speed_compare.sh --before $START --after HEAD ...` gives the before and after of all your fixes together.

The packs are `<pack_id>.parquet` files in one folder (`--packs`). The default is `$PARENT/week1-packs`: 13 packs of 500 documents, which is the English, code, math and science set. For other packs (Indic), make your own folder; see section 7.

## 4. The routine for each rule

1. **Find the slowest rule that is yours.**
   ```bash
   $PY -I teams/01-data-a/spec_v1/run_clean.py --pack "$PARENT/week1-packs/en-dclm.parquet" --out "$WORK/profile" 2>&1 | tail -13
   ```
   It lists the 10 slowest rules with their share of the time and ms per doc. Do it for a few packs of the family you work on and pick the top rule you own. Note its id, share and ms/doc.
2. **Understand it.** Find its block in `spec_v1_1/sheets/specv1_1.md` (`RULE_ID = "..."`). The time usually goes in a regex or a per-character or per-line loop that runs on every document even when it cannot match. Look for a *cheap necessary condition*: a substring or character test that must hold before the rule can change anything, or an early exit once the answer is certain. Time the parts of the rule on a pack before you change anything, so you fix the part that costs.
3. **Change the block in `specv1_1.md`** (spec v1 is frozen), or the shared F1 in `spec_v1/build/f1_rule.py`. The result must stay exactly the same. Keep the author's names and logic recognisable and add a short comment on why the fast path is safe. The `medicine_<family>.md` files are not read by the build and are not edited.
4. **Rebuild** `clean.py`: `python -I teams/01-data-a/spec_v1/build/build_clean.py`. Only your block should differ from the previous `clean.py`.
5. **Write tests**, in the speed-up test file, not in `test_clean.py`. Copy the idea of the English ones in `tests/spec_v1/test_speed_equivalence.py` (see the `c5_`, `d3_`, `b4_` tests): keep a copy of the **old rule code** in the test as the reference, then (a) hand-written cases at the edges of the fast path, (b) a random-document comparison with the reference (4,000 documents, with a check that drops and fixes both occur), (c) a sweep around any threshold.
6. **Run the new tests and the whole suite:** `$PY -m pytest teams/01-data-a/tests -q`. Optional but worth doing once per rule: break your fix on purpose in `clean.py` (for example turn a `<=` into `<`), run only your new tests and see them fail, then rebuild `clean.py`. Tests that pass on a broken fix prove nothing.
7. **The full check, before you commit:**
   ```bash
   teams/01-data-a/oneoff/speed_compare.sh --work "$WORK" --rules <RULE_ID>
   ```
   It takes about 6 to 8 minutes and ends with a SUMMARY. It must say `RESULT: PASS`, `output sha256: the same on 13 of 13 packs` and `harm: unchanged`, and the line `clean.py <old sha> -> <new sha>` must show two different shas. If you already committed the fix, use `--before HEAD~1 --after HEAD`; the script stops with a message if before and after are the same file.
8. **Log it** in `speed_v1.md` (or in your own log file, in the same format): a row in the speed table (docs/s before and after on the two packs, rule time before and after), a row in the status table (output sha256, harm tests, pytest count, documents changed, `clean.py` sha, commit), and one line in "What each fix did" with the fix in one or two sentences. The numbers come from the SUMMARY, which also names the next slowest rules.
9. **Commit** the fix and the log entry together, in one commit per rule (`specv1_1.md` or `f1_rule.py`, `clean.py`, the tests, the speed log). A commit cannot contain its own id, so write `this commit` in the entry's commit field, or fill in the id with the next commit. Then go back to step 1.

## 5. Merging two people's work

Two people edit different rules, so most files merge on their own. Three need care:

| file | what to do |
|---|---|
| `spec_v1/clean.py` | **never merge by hand.** After merging the branches, rebuild with `build_clean.py` and run `speed_compare.sh build pytest`. On a conflict, take either side and rebuild. |
| `tests/spec_v1/test_speed_equivalence.py` | the speed-up tests of the English rules. The second person puts theirs in a new file (`tests/spec_v1/test_speed_equivalence_indic.py`) so the two never touch the same lines. `test_clean.py` stays as it was. |
| `results/spec_v1/speed_v1.md` | the second person writes entries in `results/spec_v1/speed_v1_indic.md` (or `speed_v1_code.md` for code packs) in the same format; they are linked from the main log. |

Make one commit per rule, with its log entry. Do not commit the scratch folder. Example of the message style: `Speed up DA-C5-002 spam rule - search the nine patterns as one union first, check for 6 "|" before the keyword-line regex (0.65 to 0.27 ms/doc) + update medicine_english.md and tests`.

## 6. Things that cost time

- **Timings vary by about 5%** on a laptop. Treat a speed-up under 1.1x as noise, and close other programs.
- **A rule that rarely fires** may show 0 documents changed on a 500-document pack. Count it on a bigger slice too (`--limit 20000`).
- **If the output sha256 differs on a pack,** find the first document that differs (run both `clean.py` on the pack and compare per document) before changing anything else.
- **If clean.py gets damaged:** rebuild it with `build_clean.py`; `$WORK/before-clean.py` is the original.

## 7. Indic rules: what is different

The Indic rules (ids `DB-...`, family `indic`, 152 rules on 17 packs) belong to team 02-data-b (PR #240). The Indic sheet and the checks have a few special rules; the details are in [spec_v1/README_indic.md](../spec_v1/README_indic.md).

- **Edit only the rule's block in `specv1.md`** (heading `## Medicine N — indic / <code> / <id>`). **Do not edit `sheets/medicine_indic.md`:** `tests/spec_v1/test_indic_pr240.py::test_ready_source_matches_the_pinned_upstream_blob` pins it to Data B's source by hash and fails on one changed byte. Tell team 02 which rules you changed, since `specv1.md` then differs from their source for those rules.
- **Do not re-run `build/integrate_indic.py` after editing a block.** It refreshes the Indic cards in `specv1.md` from the source sheet and would probably overwrite the edit. If you ever must, check `git diff` afterwards.
- **Shared and borrowed rules.** Some Indic rules run on several packs (see `SCOPE` at the top of `clean.py`); one change affects all of them, so check every pack the rule applies to. The shared F1 rule runs last on every Indic pack.
- **The 13 English, code, math and science packs must stay identical too.** Put them in the same packs folder, so the check covers them.
- **Packs.** All 17 Indic packs are in week-2: `$PARENT/week-2/train/<pack>/part-00000.parquet`, tens of thousands of documents each. Make one folder with symlinks named `<pack_id>.parquet` and use `--limit 2000` so the before and after runs see the same first 2,000 documents:
  ```bash
  mkdir -p "$WORK/packs-all"
  for p in code-cpp code-go code-java code-js-ts code-python code-rust en-dclm en-fineweb-edu en-nemotroncc en-nemotroncc-synth math-finemath math-megamath sci-finepdfs; do
    ln -sf "$PARENT/week1-packs/$p.parquet" "$WORK/packs-all/$p.parquet"
  done
  for p in ind-bn-fw2 ind-bn-sangraha-v ind-gu-fw2 ind-hi-fw2 ind-hi-hplt ind-hi-indiccorp ind-hi-sangraha-s ind-kn-fw2 ind-kn-sangraha-s \
           ind-kn-sangraha-v ind-mr-fw2 ind-mr-sangraha-v ind-sa-fw2 ind-ta-sangraha-v ind-te-fw2 ind-te-sangraha-s ind-te-sangraha-v; do
    ln -sf "$PARENT/week-2/train/$p/part-00000.parquet" "$WORK/packs-all/$p.parquet"
  done
  ```
  Then add `--packs "$WORK/packs-all" --include-all --limit 2000 --profile-packs "ind-hi-fw2 ind-bn-fw2 ind-ta-sangraha-v ind-te-fw2"` to every `speed_compare.sh` command in section 4 (and `--count-packs` with the packs your rule applies to). The speed check then covers 30 packs and must say `30 of 30`.
- **Harm tests for Indic.** The `harm` stage runs the generic `make_harm_tests.py`, which only covers packs found in its packs folder. The Indic checks are listed in `README_indic.md` ("Rebuild and validate"): `validate/validate_specv1.py`, `validate/check_indic_integration.py --baseline <saved clean.py>` and `validate/harm_f1_indic.py`. They need the week-1 Indic diagnosis packs and gold (`--packs`, `--gold teams/02-data-b/gold`); ask Smita where those are on your machine and which one the instructor wants quoted. Run the same command with the before `clean.py` (`$WORK/before-clean.py`) and the after one, and compare. `check_indic_integration.py --baseline` does the comparison itself.
- **Slices can miss rare rules.** Before you log an Indic fix, run `speed_compare.sh ... --limit 20000 speed` once on the pack the rule fires on most.

## 8. What to hand back

For each rule: the commit, your log entry, and the list of rule ids whose blocks in `specv1.md` no longer match Data B's source. After the merge, `clean.py` is rebuilt once and the full check is run on the merged result.
