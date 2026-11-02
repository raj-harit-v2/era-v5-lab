# Cleaning packs with clean.py

This guide has two parts.

- **[Part 1: Clean your packs](#part-1-clean-your-packs)** is for anyone with packs to clean. You don't need to know Python: you copy a few commands into a terminal and change the folder names to yours.
- **[Part 2: For developers](#part-2-for-developers)** is for the people who change the rules, rebuild `clean.py`, or run the tests and harm tests. You don't need it to clean packs.

# Part 1: Clean your packs

## What the cleaner does

A pack is a Parquet file of documents. The cleaner reads every document and does one of three things with it:

| result | what it means |
|---|---|
| keep | nothing wrong was found: the document is unchanged |
| fix | something inside it was repaired or removed, for example broken characters, leftover web-page text, template junk, or a private person's phone number, email or address, which is replaced with `<PHONE>`, `<EMAIL>` or `<ADDRESS>` |
| drop | the document is left out, for example because it is cut off, spam, mostly in the wrong language, or a known private record |

It knows 13 packs, in four families. Each pack gets only its own family's rules.

| family | packs |
|---|---|
| code | `code-cpp`, `code-go`, `code-java`, `code-js-ts`, `code-python`, `code-rust` |
| English | `en-dclm`, `en-fineweb-edu`, `en-nemotroncc`, `en-nemotroncc-synth` |
| math | `math-finemath`, `math-megamath` |
| science | `sci-finepdfs` |

A pack it doesn't know, for example an Indic pack, comes out unchanged: nothing in it is cleaned.

## Before you start (once)

You need a terminal. On a Mac, open **Terminal** (in Applications, then Utilities). The commands below are for Mac and Linux.

**1. Check that Python is installed.** Type this and press Enter:

```bash
python3 --version
```

You need `Python 3.9` or higher. If you see `command not found`, install Python from https://www.python.org/downloads/, then open a new terminal window.

**2. Install the three packages the cleaner needs:**

```bash
python3 -m pip install pyarrow ftfy tree-sitter-language-pack
```

**3. Get the code**, if you don't already have the `era-v5-lab` folder. This command downloads it into the folder your terminal is in:

```bash
git clone --branch g1-specv1 https://github.com/patilvijay23/era-v5-lab.git
```

Without git: open https://github.com/patilvijay23/era-v5-lab/tree/g1-specv1, click **Code**, then **Download ZIP**, and unzip it.

**4. Put your packs in one folder**, for example a folder called `packs` in your home folder. Each file must be named exactly after its pack, for example `en-dclm.parquet`: the cleaner uses the name to choose the rules. Ask your team lead for the link to the packs.

## Clean one pack

**1. Go to the team folder.** Replace `<path to>` with where the `era-v5-lab` folder is on your computer:

```bash
cd <path to>/era-v5-lab/teams/01-data-a
```

For example, if it is in your home folder: `cd ~/era-v5-lab/teams/01-data-a`.

**2. Run the cleaner.** This example cleans `en-dclm.parquet` from the `packs` folder and writes the results to a folder called `clean_out`, both in your home folder:

```bash
python3 spec_v1/run_clean.py --pack ~/packs/en-dclm.parquet --out ~/clean_out
```

Change the pack name and the two folders to yours. `--out` is where the results go; the folder is made if it doesn't exist. Choose a folder outside `era-v5-lab` (see [Keep the results private](#keep-the-results-private)).

The file name must be one of the 13 pack names, for example `en-dclm.parquet`. With any other name the cleaner stops at once and writes nothing, because it has no rules for that pack (see [If something goes wrong](#if-something-goes-wrong)).

**3. Read the line it prints.** After a few seconds you see one line like this (the long code at the end is shortened here):

```
{'pack': 'en-dclm.parquet', 'pack_id': 'en-dclm', 'family': 'english', 'rows': 500, 'actions': {'keep': 437, 'fix': 54, 'drop': 9}, 'errors': [], 'seconds': 12.2, 'docs_per_second': 41.1, 'clean_py_sha256': '…'} dropped: 9
```

| part | what it means |
|---|---|
| `pack_id`, `family` | the pack, and the family whose rules ran |
| `rows` | how many documents the pack has |
| `keep`, `fix`, `drop` | how many documents were kept unchanged, cleaned, or left out |
| `errors` | should be `[]`. Anything else means some documents could not be cleaned. |
| `clean_py_sha256` | a fingerprint of the cleaner that ran. Two runs with the same fingerprint used exactly the same rules. |

**4. Find the results** in your `--out` folder. For `en-dclm` they are:

| file | what it is |
|---|---|
| `en-dclm_clean.parquet` | the cleaned pack: every kept and fixed document, with its cleaned text. Dropped documents are not in it. |
| `en-dclm_summary.json` | the counts above, the IDs of the dropped documents and any errors. It holds no document text. |

## Clean all your packs in one go

From the team folder, set your two folders on the first two lines, then run the whole block. It cleans each of the 13 packs it finds in your packs folder and says which ones it skipped:

```bash
PACKS=~/packs
OUT=~/clean_out
for p in code-cpp code-go code-java code-js-ts code-python code-rust en-dclm en-fineweb-edu en-nemotroncc en-nemotroncc-synth math-finemath math-megamath sci-finepdfs; do
  if [ -f "$PACKS/$p.parquet" ]; then python3 spec_v1/run_clean.py --pack "$PACKS/$p.parquet" --out "$OUT" || echo "$p: stopped or had errors, see the line above"; else echo "$p: not in $PACKS, skipped"; fi
done
```

## How to tell it worked

- Every pack printed its line, with `'errors': []`.
- No pack stopped with `is not one of the 13 packs`.
- The numbers are close to these, from a test run on 1 Nov (500 documents per pack):

| pack | kept | fixed | dropped |
|---|---:|---:|---:|
| `en-dclm` | 437 | 54 | 9 |
| `en-fineweb-edu` | 487 | 12 | 1 |
| `en-nemotroncc` | 421 | 62 | 17 |
| `en-nemotroncc-synth` | 467 | 32 | 1 |
| `sci-finepdfs` | 442 | 45 | 13 |

## If something goes wrong

| what you see | what to do |
|---|---|
| `python3: command not found` | Install Python (step 1 of [Before you start](#before-you-start-once)) and open a new terminal window. |
| `No module named 'pyarrow'`, `'ftfy'` or `'tree_sitter_language_pack'` | Run the install command in step 2 of [Before you start](#before-you-start-once). |
| `can't open file ... spec_v1/run_clean.py` | You are not in the team folder. Run the `cd` command in step 1 of [Clean one pack](#clean-one-pack). |
| `FileNotFoundError` with your pack's path | The folder or the file name is wrong. Check both, and that the file name ends in `.parquet`. |
| `... is not one of the 13 packs clean.py has rules for, so nothing would be cleaned` | The file name is not one of the 13 pack names, so the cleaner stopped without writing anything. If it is one of the 13 packs under another name, rename the file, for example to `en-dclm.parquet`. If it is a new pack, don't rename it: ask the Data A team to add it (see [Add a new pack](#add-a-new-pack)). |
| `doc_id ... has pack_id '...'` | The file name doesn't match the pack inside it. Rename the file to the name shown in quotes, plus `.parquet`. |
| `errors` is not `[]` | Those documents could not be cleaned and are left out of the cleaned pack. Send the `_summary.json` file to the Data A team: it holds only IDs and error types. |

## Keep the results private

The cleaned packs contain the documents' text. Keep them outside the `era-v5-lab` folder, don't upload or share them, and never commit them to GitHub. The `_summary.json` files hold only IDs and counts, so they are safe to share with the team.

# Part 2: For developers

The rest of this guide is for people who change the rules, rebuild `clean.py`, or run the tests and harm tests. Paths start at `teams/01-data-a/`.

`spec_v1/clean.py` holds the 70 rules of `spec_v1/sheets/specv1.md` and the shared F1 rule, `spec_v1/tools/f1_rule.py`. The rules come from four families, which together cover 13 packs. It has one function per disease code, 24 in all, and `clean(doc)`, which runs a document through every rule of its family in sheet order. At the top is `SCOPE`, a table of the packs each rule applies to. A rule runs only on its own packs, and its harm test uses only the gold sets of those packs.

`clean.py` is generated. Do not edit it: change `specv1.md` and rebuild (step 1).

`clean.py` is the only cleaner, and `run_clean.py` cleans a pack of any family with it.

## Contents of Part 2

1. [Where everything is](#where-everything-is)
2. [Every script: command, what it needs, what it writes](#every-script-command-what-it-needs-what-it-writes)
3. [What you need](#what-you-need)
4. [Quick start](#quick-start)
5. [Step 1: build clean.py](#step-1-build-cleanpy)
6. [Step 2: run the unit tests](#step-2-run-the-unit-tests)
7. [Step 3: clean a pack](#step-3-clean-a-pack)
8. [Step 4: run the harm tests](#step-4-run-the-harm-tests)
9. [Other checks](#other-checks)
10. [The normaliser](#the-normaliser-spec_v1toolsnormalizepy)
11. [Use clean.py from Python](#use-cleanpy-from-python)
12. [The 24 functions](#the-24-functions)
13. [Run order in each family](#run-order-in-each-family)
14. [The scope table](#the-scope-table)
15. [Troubleshooting](#troubleshooting)

## Where everything is

Paths start at `teams/01-data-a/`. The sheets are in `spec_v1/sheets/`, the tools in `spec_v1/tools/` and the results in `spec_v1/results/cleaner/` (checks of `clean.py`) and `spec_v1/results/sheets/` (checks of the family sheets). The team's shared tools, `harm_test.py` among them, are in `tools/`, and the gold sets in `gold/`.

```
spec_v1/
  clean.py                       the cleaner: generated, do not edit
  run_clean.py                   cleans one pack with clean.py
  README_clean.md                this file
  sheets/specv1.md               the rules: the one sheet clean.py is built from
  sheets/medicine_<family>.md    the family sheets that specv1.md collates (code, english, math, sci)
  tools/build_clean.py           writes clean.py from sheets/specv1.md
  tools/f1_rule.py               the shared F1 rule; the build pastes it into clean.py
  tools/make_harm_tests.py       the harm tests: each rule on the gold sets of its own packs
  tools/validate_specv1.py       checks specv1.md itself on every pack and writes its validation table
  tools/verify_clean.py          checks clean.py on the code packs
  tools/f1_eval.py               checks the shared F1 on the code packs
  tools/normalize.py             the normaliser: words for G9, keys for duplicates; never changes a document
  tools/*_english.py             checks on the English packs: see tools/README_english.md
  tests/test_clean.py            the unit tests of clean.py
  tests/test_normalize.py        the unit tests of tools/normalize.py
  tests/test_run_clean.py        the unit tests of run_clean.py
  results/cleaner/               harm_tests.md, specv1_<pack>_harm.json, specv1_validation.json and the English checks
  results/sheets/                harm reports of the family sheets
```

## Every script: command, what it needs, what it writes

Run every command from `teams/01-data-a/`. "Packages" are what `pip install` must have added. `../..` is the `era-v5-lab` folder: the harm tests read `harm_test.py` from its `teams/01-data-a/tools/` and the gold sets from its `teams/01-data-a/gold/`.

| script | command | packages | also needs | writes |
|---|---|---|---|---|
| `spec_v1/tools/build_clean.py` | `python -I spec_v1/tools/build_clean.py` | none (Python 3.9+) | `spec_v1/sheets/specv1.md`, `spec_v1/tools/f1_rule.py` | `spec_v1/clean.py` |
| `spec_v1/tests/` (`test_clean.py`, `test_normalize.py`, `test_run_clean.py`) | `python -m pytest spec_v1/tests` | `pytest`, `pyarrow`, `ftfy`, `tree-sitter-language-pack` | `spec_v1/clean.py`, `spec_v1/run_clean.py`, `spec_v1/sheets/specv1.md`, `spec_v1/tools/build_clean.py`, `spec_v1/tools/normalize.py` | nothing (`test_run_clean.py` writes made-up packs to a temporary folder) |
| `spec_v1/run_clean.py` | `python -I spec_v1/run_clean.py --pack <packs folder>/<pack_id>.parquet --out <results folder>` | `pyarrow`, `ftfy`, `tree-sitter-language-pack` | the pack | `<results folder>/<pack>_clean.parquet`, `<results folder>/<pack>_summary.json` |
| `spec_v1/tools/make_harm_tests.py` | `python -I spec_v1/tools/make_harm_tests.py ../.. <packs folder> [<more packs folders>]` | `pyarrow`, `ftfy`, `tree-sitter-language-pack` | `tools/harm_test.py`, `gold/`, the packs | `spec_v1/results/cleaner/harm_tests.md`, `spec_v1/results/cleaner/specv1_<pack>_harm.json` |
| `spec_v1/tools/validate_specv1.py` | `python -I spec_v1/tools/validate_specv1.py --packs <packs folder> --gold gold` | `pyarrow`, `ftfy` | `tools/harm_test.py`, `gold/`, the packs | the validation table and card evidence inside `spec_v1/sheets/specv1.md`, `spec_v1/results/cleaner/specv1_validation.json` |
| `spec_v1/tools/verify_clean.py` | `python -I spec_v1/tools/verify_clean.py ../.. <packs folder> spec_v1/sheets/medicine_code.md` | `pyarrow`, `tree-sitter-language-pack` | `gold/`, the annotators' labels in `diagnosis/submissions/`, the six code packs | prints only |
| `spec_v1/tools/f1_eval.py` | `python -I spec_v1/tools/f1_eval.py ../.. <packs folder> [docs per pack, default 40]` | `pyarrow`, `tree-sitter-language-pack` | `gold/`, the annotators' labels in `diagnosis/submissions/`, the six code packs | prints only |
| `spec_v1/tools/normalize.py` | `python -I spec_v1/tools/normalize.py --pack <packs folder>/<pack_id>.parquet` | `pyarrow` (only for `--pack`) | the pack | prints only |
| English checks | `spec_v1/tools/verify_clean_english.py`, `f1_eval_english.py`, `order_checks_english.py`, `make_harm_tests_english.py` | `pyarrow`, `ftfy` | see [tools/README_english.md](tools/README_english.md) | `spec_v1/results/cleaner/` |

The pack files are not in the repo; get your link from the lab plan sheet. Each must be named `<pack_id>.parquet`.

## What you need

| what | why |
|---|---|
| Python 3.9 or later (tested on 3.12) | `functools.cache` |
| `pyarrow` | reads and writes the Parquet packs |
| `ftfy` | the English mojibake rule, `DA-A3-002` |
| `tree-sitter-language-pack` | the shared F1 on code: it looks for private details only inside comments and strings |
| `pytest` | the unit tests |
| the packs, `<pack_id>.parquet` | not in the repo; get your link from the lab plan sheet |
| the gold sets, `gold/<pack>_gold.csv` | in the repo; only for step 4 and the [other checks](#other-checks) |

```bash
pip install pyarrow ftfy tree-sitter-language-pack pytest
```

`clean.py` imports without `ftfy` and `tree-sitter-language-pack`. Without them, the rules that need them raise an error when they run. `run_clean.py` then reports those documents as errors (see [Troubleshooting](#troubleshooting)).

### The packs

| family | packs |
|---|---|
| code | `code-cpp`, `code-go`, `code-java`, `code-js-ts`, `code-python`, `code-rust` |
| english | `en-dclm`, `en-fineweb-edu`, `en-nemotroncc`, `en-nemotroncc-synth` |
| math | `math-finemath`, `math-megamath` |
| sci | `sci-finepdfs` |

A pack file must be named after its pack ID, for example `en-dclm.parquet`. It needs the columns `doc_id`, `text`, `url` and `lang_label`. The `pack_id` column may be missing: `run_clean.py` then takes the pack ID from the file name. `run_clean.py` stops on any file name that is not one of these 13 pack IDs.

## Quick start

Run these from `teams/01-data-a/`. First install the packages, once. Include `tree-sitter-language-pack`: without it, the shared F1 cannot read code files and 5 unit tests are skipped.

```bash
pip install pyarrow ftfy tree-sitter-language-pack pytest
```

```bash
python -I spec_v1/tools/build_clean.py
```

```bash
python -m pytest spec_v1/tests
```

```bash
python -I spec_v1/run_clean.py --pack <packs folder>/en-dclm.parquet --out <results folder outside the repo>
```

```bash
python -I spec_v1/tools/make_harm_tests.py ../.. <packs folder>
```

## Step 1: build clean.py

```bash
python -I spec_v1/tools/build_clean.py
```

This reads `spec_v1/sheets/specv1.md` and writes `spec_v1/clean.py`. Use `--sheet` and `--out` to read or write somewhere else:

```bash
python -I spec_v1/tools/build_clean.py --sheet spec_v1/sheets/specv1.md --out /tmp/clean.py
```

**Rebuild after every change to `specv1.md` or `spec_v1/tools/f1_rule.py`.** The build gives the same file every time, and a unit test checks that `clean.py` matches a fresh build.

### What the build does

1. It finds each `## Medicine N — <family> / <code> / \`<ID>\`` section and its Python block.
2. It reads the block's packs: the `SPEC_PACKS` line, and for a math rule its `ORIGIN` packs as well (`PACKS = set(ORIGIN.split(", "))`). The rule's scope is the packs both allow.
3. It writes those packs into `SCOPE` at the top of `clean.py`, and points the block's `SPEC_PACKS` (and `PACKS`) at its `SCOPE` entry. So pack IDs are written in one place.
4. It puts each block in its own closure (`_<family>_<code>_<nnn>`), so helpers with the same name in two blocks do not clash. Two other changes are made to the blocks:
   - The `AUTHOR` line is dropped.
   - The code `DA-B4-009` rule no longer rewrites `<EMAIL>`, which is the F1 tag.
5. It adds `spec_v1/tools/f1_rule.py` as the shared F1, in `SCOPE` under the name `f1_rule.py`, for the code, math and science packs (`SHARED_F1_FAMILIES`). English keeps `DA-F1-005`.
6. It writes the 24 disease-code functions, `RULES`, `_PIPELINES` (each family's rules in sheet order), `_FAMILY` (pack to family) and `clean()`.

### What it prints

One line for each docstring or verbose regex whose indentation changed, for example `DA-E1-001 code strings changed: 1 [...]`. These are expected: the indentation of a docstring or a verbose regex does not change what the rule does. The last line is the summary:

```
clean.py: rules 70 + shared F1 | code 24 rules on 6 packs, english 20 rules on 4 packs, math 14 rules on 2 packs, sci 12 rules on 1 packs | functions: 24
```

### When the build stops

It stops with an `AssertionError` that names the rule, and writes nothing, when:

- a section has no Python block, or more than one;
- the block's `RULE_ID` or `CODE` does not match its heading;
- two rules share an ID, or the sections are not numbered 1, 2, 3, ...;
- a block does not have exactly one `SPEC_PACKS` line, or its scope is empty;
- a block reads `pack_id` anywhere except its pack check;
- one pack belongs to two families;
- `DA-F1-005`, the instructor's F1 rule, is missing, not under F1, or not on all four English packs.

## Step 2: run the unit tests

```bash
python -m pytest spec_v1/tests
```

The unit tests are in three files, one per module. `spec_v1/tests/test_clean.py` tests `clean.py`, in six sections:

| section | what it tests |
|---|---|
| 1. Every disease-code function | Each of the 24 functions, on every family that has a rule for it: a sick document it fixes or drops (with the exact text after the fix for English), and clean documents of every family that it keeps. One test checks the table covers every function and family in `clean.py`, so a new rule cannot go untested. |
| 2. The scope table and the build | The scope table, on all 13 packs:<br>• every rule has one entry, and each pack is in one family;<br>• each family runs in sheet order;<br>• the F1 rules cover their family, `DA-F1-005` on all four English packs;<br>• a rule acts on its own packs only, and nothing runs without a known `pack_id`;<br>• the build reproduces `clean.py` and stops on a bad scope. |
| 3. The code family | A licence goes and the build tag stays, a generated file is dropped, the shared F1 on prose and in code, the code B4 rule keeps the `<EMAIL>` tag, and a second clean changes nothing. |
| 4. The English family | Look-alikes kept, other languages untouched, ZWJ and ZWNJ kept, F1 tags survive a second clean, and `clean()` equal to the English rules of `specv1.md`. |
| 5. The math family | A teaser cut trimmed to its last sentence, a second clean changes nothing, a Symbol-font glyph mapped, cp866 mojibake repaired, BBCode maths converted, repeated answer options kept, foreign-script spam removed, Greek letters kept. |
| 6. The shared F1 on math and science | The prose path of `spec_v1/tools/f1_rule.py`: private phones, emails and addresses get their tag, a listing of individuals is dropped, organisations and look-alikes are kept, and it runs only on the math and science packs with their own language tags. |

`spec_v1/tests/test_normalize.py` tests `spec_v1/tools/normalize.py`: G9's own examples; each A1 character and listed compatibility form matching the plain word; ZWJ and ZWNJ kept, so words that differ by one stay different; Indic spellings of the same word (nukta, two-part vowel signs, chillu, khanda ta) matching; no full NFKC; the keys evening out B1, A2, A1, A5, case and spacing; and that no document or `clean()` result changes.

`spec_v1/tests/test_run_clean.py` tests `spec_v1/run_clean.py` on made-up packs it writes to a temporary folder:

- a known pack is cleaned exactly as `clean.clean()` cleans each document;
- its summary holds `pack_id`, `family` and the SHA-256 of `clean.py`, and no text;
- a pack name that is not one of the 13 stops the run with exit code 1, before the file is read and before the `--out` folder is made, whether the file has no `pack_id` column, the new name in it, or an old name in it;
- a `pack_id` column that does not match the file name stops the run.

Every text in the tests is made up. Some science rules act only on documents the reviewers listed, so those tests use the doc_ids named in `specv1.md`. Expect `520 passed` (461 in `test_clean.py`, 53 in `test_normalize.py`, 6 in `test_run_clean.py`) with `tree-sitter-language-pack` installed. Without it, 515 pass and 5 are skipped: the shared F1 on code (`pip install tree-sitter-language-pack`).

## Step 3: clean a pack

### `clean.py` and `run_clean.py`

`clean.py` holds the rules but is not a program you run on its own. It has no command line: `python spec_v1/clean.py` defines its functions, prints nothing and exits, without reading any pack. To clean a pack, run `run_clean.py`, which calls `clean.py` for you.

`run_clean.py` is in the repo beside `clean.py`, at `spec_v1/run_clean.py`. It loads `clean.py` from its own folder, so keep the two together. For each pack it:

1. checks that the file name is one of the 13 pack IDs, and stops otherwise, before it reads the file or makes the `--out` folder. `clean.py` has no rules for any other pack, so every document would pass through unchanged and the run would still look successful;
2. reads the pack's Parquet file, and fills in `pack_id` from the file name if the pack has no such column. If the column is there, it must match the file name;
3. calls `clean.clean(doc)` on every document (`import clean as c`, then `c.clean(row)`);
4. writes the kept documents with their cleaned text, and a summary of what happened, including the SHA-256 of the `clean.py` that ran.

Every keep, fix and drop comes from `clean.py`; `run_clean.py` only reads and writes the files around it. Your own code can do the same by importing `clean.py` (see [Use clean.py from Python](#use-cleanpy-from-python)).

### Run it

```bash
python -I spec_v1/run_clean.py --pack <packs folder>/en-dclm.parquet --out <results folder>
```

| option | meaning |
|---|---|
| `--pack` | The pack, a Parquet file named `<pack_id>.parquet`, for one of the 13 packs in [the scope table](#the-scope-table). Any other name stops the run. |
| `--out` | The folder for the results; it is made if missing. Without `--out` it is `out`, a folder inside the one you run from: run from `teams/01-data-a/`, that is `teams/01-data-a/out/`. |

It reads only the pack, writes only to `--out`, and needs no network.

**Point `--out` outside the repo**, for example `--out ~/clean_out`, or delete the folder after use. The cleaned Parquet files hold document text and are several MB each: they must not be committed, and pr-guard rejects files over 5 MB.

### What it writes

| file | what is in it |
|---|---|
| `<results folder>/<pack>_clean.parquet` | The documents that were kept, with their cleaned text and all their columns. A `pack_id` column is added if the pack had none. |
| `<results folder>/<pack>_summary.json` | IDs and counts only, no text: `pack` (the file name), `pack_id`, `family`, `rows`, `actions` (keep / fix / drop), `errors` (doc_id and error type), `dropped` (doc_ids), `seconds`, `docs_per_second`, and `clean_py_sha256`, the SHA-256 of the `clean.py` that ran. Two summaries with the same `clean_py_sha256` came from the same rules. To check which `clean.py` you have: `shasum -a 256 spec_v1/clean.py`. |

A test run on the English packs (1 Nov, 500 documents each, 0 errors):

| pack | kept | fixed | dropped | time |
|---|---:|---:|---:|---:|
| `en-dclm` | 437 | 54 | 9 | 12.2 s |
| `en-fineweb-edu` | 487 | 12 | 1 | 6.1 s |
| `en-nemotroncc` | 421 | 62 | 17 | 5.9 s |
| `en-nemotroncc-synth` | 467 | 32 | 1 | 3.6 s |

`sci-finepdfs`: 442 kept, 45 fixed, 13 dropped, in about 4 seconds.

`run_clean.py` exits with 0 when no rule raised and 1 when one did. A document whose rule raised is left out of `_clean.parquet`, and its doc_id is listed under `errors`. It also exits with 1, and writes nothing, when:

- the file name is not one of the 13 pack IDs (checked first, before the file is read);
- the pack's `pack_id` column does not match its file name.

### All 13 packs

```bash
PACKS=<packs folder>
OUT=<results folder outside the repo>
for p in code-cpp code-go code-java code-js-ts code-python code-rust en-dclm en-fineweb-edu en-nemotroncc en-nemotroncc-synth math-finemath math-megamath sci-finepdfs; do
  python -I spec_v1/run_clean.py --pack "$PACKS/$p.parquet" --out "$OUT" || echo "$p: see $OUT/${p}_summary.json"
done
```

## Step 4: run the harm tests

```bash
python -I spec_v1/tools/make_harm_tests.py ../.. <packs folder> [<another packs folder> ...]
```

| argument | meaning |
|---|---|
| `../..` | The `era-v5-lab` folder, seen from `teams/01-data-a/`. The script reads `teams/01-data-a/tools/harm_test.py` and `teams/01-data-a/gold/<pack>_gold.csv` from it. `harm_test.py` is imported as it is, never changed. |
| `<packs folder>` | One or more folders holding the packs; a pack is looked for in each. |
| `--out` | The report (default `spec_v1/results/cleaner/harm_tests.md`). |
| `--results` | The folder for the per-pack JSON reports (default `spec_v1/results/cleaner`). |

### What it tests on each pack

1. **Each rule alone,** but only a rule whose `SCOPE` entry includes this pack, on that pack's gold set.
2. **Each disease-code function,** on the packs where one of its rules applies.
3. **`clean()`,** on the gold set, and on the whole pack for the fixed and dropped counts.
4. **The scope table holds:** every rule that does not apply to the pack is run on the whole pack, past the scope check. It must change nothing, drop nothing and raise nothing.
5. **The cross-check:** the `clean()` gold result is compared with `spec_v1/results/cleaner/specv1_validation.json` when both used the same gold and pack. The code, math and science packs may differ, because `clean.py` adds the shared F1 on them, and the `DA-B4-009` change on code.

### The limit

At most `max(1, floor(1% of gold))` gold documents changed or dropped, for each pack on its own; packs are never pooled.

- An empty gold set is NOT TESTABLE.
- An error is never a PASS.
- A rule passes only if it passes on every pack of its scope.

### What it writes

| file | what is in it |
|---|---|
| `spec_v1/results/cleaner/harm_tests.md` | Section 1: `clean()` per pack. Section 2: each rule alone, one table per family, with `·` where the rule does not apply. Section 3: each function per pack. Then the packs it could not run. |
| `spec_v1/results/cleaner/specv1_<pack>_harm.json` | The same per pack, with the affected gold doc_ids and the sha256 of the pack, the gold, `clean.py` and `harm_test.py`. No text. |

It exits with 0 when everything it ran passed. It exits with 1 when any result is not PASS, a gold set is empty, or a rule acted on a pack it does not apply to. A pack it cannot find is listed as not run and does not fail the run. So run it where all 13 packs are before you commit `harm_tests.md`.

## Other checks

These are not needed to build or run `clean.py`, but they are how the numbers in `spec_v1/sheets/specv1.md` and `spec_v1/results/cleaner/` were made.

### `spec_v1/tools/validate_specv1.py`: check `specv1.md` itself

It runs every block of `spec_v1/sheets/specv1.md` (the sheet, not `clean.py`) on each pack's gold set and whole pack, then rewrites the validation table and the "Current gold harm" lines inside `specv1.md`, and writes `spec_v1/results/cleaner/specv1_validation.json`.

It uses `harm_test.py` from `tools/` and the gold sets in `gold/`:

```bash
python -I spec_v1/tools/validate_specv1.py --packs <packs folder> --gold gold
```

It changes `specv1.md`, but only the text around the code: `clean.py` does not need a rebuild. Run the unit tests after it.

### `spec_v1/tools/verify_clean.py` and `spec_v1/tools/f1_eval.py`: the code packs

Both run on the six code packs only and print IDs, counts and masked shapes, never a private value. They also count the rows the annotators labelled, from `diagnosis/submissions/<pack>/<reader>/labels.csv` in the `era-v5-lab` folder; on this branch that folder holds only a README, so those counts come out as 0 until the label files are there. `verify_clean.py` checks that `clean.py` gives what `spec_v1/sheets/medicine_code.md` gives, what the shared F1 does per pack, and that a second clean changes nothing. `f1_eval.py` checks the shared F1 with made-up values planted in real gold docs, and what B4 does to its tags.

```bash
python -I spec_v1/tools/verify_clean.py ../.. <packs folder> spec_v1/sheets/medicine_code.md
```

```bash
python -I spec_v1/tools/f1_eval.py ../.. <packs folder>
```

### The English checks

`spec_v1/tools/verify_clean_english.py`, `f1_eval_english.py`, `order_checks_english.py` and `make_harm_tests_english.py` check the English packs in more detail. Their commands and run order are in [tools/README_english.md](tools/README_english.md).

## The normaliser: `spec_v1/tools/normalize.py`

### G9 fingerprint contract and limitations

The G9 adapter is `normalize(text)` / `words_with_offsets(text)` with
`NORMALIZE_ID = "g1-spec-v1"`. This word-fingerprint interface does **not**
perform B1 HTML-entity decoding or A2 control-character removal. Those are
additional operations of `match_key()` and `line_keys()` only. These APIs are
different comparison representations and must not be substituted for each other.

Run applicable `clean.py` rules on training documents first, exclude documents
marked `drop`, then fingerprint the retained cleaned text. Benchmark inputs
need a separately agreed preprocessing policy; do not assign them arbitrary
Data A `pack_id` values. A3 mojibake repairs remain in pack-scoped cleaning.

`words_with_offsets()` reports the start of a raw word in the text passed to it
(Python character offset). Expanded tokens can share an offset, such as
`½` -> `[("1", 0), ("2", 0)]`. Offsets for cleaned documents refer to the
cleaned text, not automatically to the original document.

Record the `NORMALIZE_ID`, source commit SHA, Python/Unicode-data versions,
and G9 fingerprint-set SHA-256. Any change to the output of `normalize()`
requires a new normalization ID and a fingerprint rebuild.

A standard copy of a text, for comparing and matching. **It never changes a document:** code compares the copies, and the document keeps its own text, so nothing is fixed or dropped by it. `clean.py` does not use it. It gives the copy in two shapes:

| function | returns | for |
|---|---|---|
| `normalize(text)` | a list of words | decontamination fingerprints. Team 1 shares it with G9: same interface as `teams/09-evaluation/decontam/normalize.py`, with `words_with_offsets(text)`, `NORMALIZE_ID` (`g1-spec-v1`) and `DESCRIPTION` |
| `match_key(text)` | one key for the whole text, punctuation kept | comparing documents or passages: H1 exact and H2 near duplicates |
| `line_keys(text)` | one key per line | comparing lines: C1 boilerplate phrases, C2 repeated lines, E4 licence headers |
| `explain(text)` | the steps of the keys that change this text | logging which diseases a key evened out |

Both shapes treat characters the same way, for every language and pack: a benchmark item has no pack, and both sides of a match must get exactly the same treatment.

| step | disease | what happens in the copy |
|---|---|---|
| `B1` (keys only) | HTML entities | whole entities ending in `;` are decoded: `&amp;`, `&nbsp;`, `&#2361;`. Not `&reg` inside a URL. |
| `A2` (keys only) | control characters | `\r\n` and `\r` become `\n`; U+0000–001F (but tab and newline) and U+007F–009F go |
| `A1` | invisible junk | zero-width space, BOM, soft hyphen and the bidi marks U+202A–202E, U+2066–2069 go. ZWJ and ZWNJ stay. |
| `A5` | wrong normal form | NFC, the form `DISEASES.md` names. Only these compatibility characters are folded: Latin ligatures (`ﬁ` becomes `fi`), fullwidth ASCII, vulgar fractions and Arabic presentation forms. The old ZWJ spellings of the Malayalam chillus and of Bengali khanda ta become the single letters Unicode has for them. |
| `case` | (none) | `casefold()`, then NFC again: `ß` and `SS` compare equal |
| `space` (keys only) | (none) | runs of spaces and tabs become one space |

`normalize()` then keeps only words: runs of letters, marks and numbers, plus ZWJ and ZWNJ. Everything else separates words. Changing any of its steps changes `NORMALIZE_ID`, and G9 refuses fingerprints built with another one.

What it never does, so it cannot cause the damage of `DISEASES.md` section G: no full NFKC (superscripts such as `x²`, circled digits and Indic digits stay as they are), no ZWJ or ZWNJ removed except in the two chillu and khanda ta spellings that have a single letter, and no vowel sign or virama split from its letter.

It does not repair A3 mojibake or other per-family problems: `clean.py` does that before matching. It also lower-cases math variables, so `X` and `x` compare equal.

From Python, run from `teams/01-data-a/`:

```python
import sys
sys.path.insert(0, "spec_v1/tools")
from normalize import normalize, match_key, line_keys, explain

normalize("Janet\u2019s DUCKS, lay 16-eggs!")              # ['janet', 's', 'ducks', 'lay', '16', 'eggs']
match_key("Fish &amp; chips") == match_key("fish & CHIPS")   # True
explain("Caf\u00e9\u200b")                                   # ['A1', 'case']
```

To see how many documents of a pack each step of the keys would even out (IDs and counts only, never text):

```bash
python -I spec_v1/tools/normalize.py --pack <packs folder>/en-dclm.parquet
```

On `en-dclm`, for example: B1 1 document, A2 3, A1 10, A5 6, case 500, space 260. Its tests are in `spec_v1/tests/test_normalize.py`.

## Use clean.py from Python

```python
import sys
sys.path.insert(0, "spec_v1")
import clean

doc = {"doc_id": "x", "text": "Some text.", "url": "", "lang_label": "en", "pack_id": "en-dclm"}
action, text = clean.clean(doc)          # the whole pipeline of the doc's family
action, text = clean.RULES["B4"](doc)    # one disease code: its rules for this pack, in sheet order
clean.SCOPE["DA-A1-005"]                 # frozenset({'math-finemath'})
clean._FAMILY["en-dclm"]                 # 'english'
```

- **`action`:** `"keep"`, `"fix"` or `"drop"`.
- **`text`:** the cleaned text after a fix. After a keep or a drop it is the original text.
- **The document:** never changed in place.
- **Without a known pack:** a document with no `pack_id`, or one that no family has, comes back as `("keep", text)`. Such a document is not eligible for release.

> **Check the pack before you call `clean()`.** `clean()` does not raise on an unknown pack: it returns `("keep", text)`, which looks the same as a clean document. `run_clean.py` checks for you; your own code must check too, for example:
>
> ```python
> if doc.get("pack_id") not in clean._FAMILY:
>     raise ValueError(f"clean.py has no rules for pack {doc.get('pack_id')!r}")
> ```

## The 24 functions

One function per disease code. Each runs the rules of that code that apply to the document's pack. `·` means the family has no rule for that code.

| function | code | english | math | sci |
|---|---|---|---|---|
| `a1` | `DA-A1-001` | `DA-A1-004` | `DA-A1-005` | `DA-A1-006` |
| `a2` | `DA-A2-007` | `DA-A2-008` | · | · |
| `a6` | `DA-A6-001` | · | `DA-A6-003` | `DA-A6-002` |
| `a4` | `DA-A4-002`, `DA-A4-003` | · | · | · |
| `a5` | · | `DA-A5-001` | `DA-A5-002` | · |
| `a3` | · | `DA-A3-002` | `DA-A3-001` | · |
| `b1` | · | `DA-B1-002` | · | · |
| `b2` | · | `DA-B2-002` | `DA-B2-001` | `DA-B2-003` |
| `b5` | · | · | `DA-B5-001` | `DA-B5-002` |
| `b3` | `DA-B3-001` | · | · | · |
| `e1` | `DA-E1-001`, `DA-E1-004`, `DA-E1-008`, `DA-E1-006`, `DA-E1-005`, `DA-E1-007` | · | · | · |
| `e2` | `DA-E2-001` | · | · | · |
| `c3` | `DA-C3-002` | `DA-C3-001`, `DA-C3-003` | `DA-C3-004`, `DA-C3-005` | `DA-C3-006` |
| `c4` | `DA-C4-002` | · | · | `DA-C4-003` |
| `c5` | · | `DA-C5-002`, `DA-C5-005` | `DA-C5-001`, `DA-C5-006` | · |
| `d4` | · | `DA-D4-001` | · | · |
| `e4` | `DA-E4-005`, `DA-E4-010`, `DA-E4-009`, `DA-E4-007` | · | · | · |
| `c1` | `DA-C1-004`, `DA-C1-005` | `DA-C1-006` | `DA-C1-001` | `DA-C1-007` |
| `c2` | · | `DA-C2-003` | `DA-C2-001` | `DA-C2-004` |
| `d1` | · | · | · | `DA-D1-001` |
| `d3` | · | `DA-D3-003` | `DA-D3-005` | `DA-D3-004` |
| `b4` | `DA-B4-009` | `DA-B4-007`, `DA-B4-008`, `DA-B4-012`, `DA-B4-010`, `DA-B4-011` | `DA-B4-001` | `DA-B4-013` |
| `e3` | `DA-E3-003`, `DA-E3-004` | · | · | · |
| `f1` | `f1_rule.py` (shared) | `DA-F1-005` | `f1_rule.py` (shared) | `DA-F1-006`, then `f1_rule.py` (shared) |

`RULES` maps each code to its function in the order above. `harm_test.py --rules spec_v1/clean.py --rule all` runs them in that order. That order is not a family's run order: use `clean()` for the real pipeline.

## Run order in each family

`clean()` runs these in order. A drop ends the document, and a fix passes the new text to the next rule. The code, math and science families then run the shared F1 last.

| family | order |
|---|---|
| code | A1-001, A2-007, A6-001, A4-002, A4-003, B3-001, E1-001, E1-004, E1-008, E1-006, E1-005, E1-007, E2-001, C3-002, C4-002, E4-005, E4-010, E4-009, E4-007, C1-004, C1-005, B4-009, E3-003, E3-004, then the shared F1 |
| english | A1-004, A2-008, A5-001, A3-002, B1-002, B2-002, C3-001, C3-003, C5-002, D4-001, C1-006, C2-003, C5-005, D3-003, B4-007, B4-008, B4-012, B4-010, B4-011, F1-005 |
| math | A3-001, A1-005, A6-003, A5-002, B2-001, B4-001, B5-001, C5-001, D3-005, C3-004, C1-001, C2-001, C5-006, C3-005, then the shared F1 |
| sci | B4-013, B2-003, B5-002, A1-006, A6-002, C1-007, C2-004, C3-006, C4-003, D1-001, F1-006, D3-004, then the shared F1 |

## The scope table

```python
SCOPE = {
    "DA-A1-001": frozenset({"code-cpp", "code-go", "code-java", "code-js-ts", "code-python", "code-rust"}),  # code A1, medicine 1
    ...
    "DA-A1-005": frozenset({"math-finemath"}),  # math A1, medicine 46
    ...
    "f1_rule.py": frozenset({"code-cpp", ..., "math-finemath", "math-megamath", "sci-finepdfs"}),  # the shared F1: code, math and sci packs
}
```

Each rule applies to every pack of its family, except for seven math rules whose `ORIGIN` names one math pack:

| packs | rules |
|---|---|
| `math-finemath` only | `DA-A1-005`, `DA-A6-003`, `DA-C1-001`, `DA-C2-001`, `DA-C3-004`, `DA-C3-005` |
| `math-megamath` only | `DA-C5-001` |

The scope is checked twice, and both checks read `SCOPE`:

- `_run` skips a rule whose `SCOPE` entry does not hold the document's `pack_id`.
- Each rule's own pack check reads its `SCOPE` entry.

**To change a rule's packs,** do these in order:

1. Edit its `SPEC_PACKS` line in `specv1.md`. For a math rule, edit `ORIGIN` too.
2. Rebuild (step 1).
3. Run the unit tests (step 2).
4. Run the harm tests (step 4).

### Add a new pack

`clean.py` cleans only the 13 packs in `SCOPE`, and `run_clean.py` stops on any other. A new pack, or a new version of one such as `en-fineweb-edu-v2`, is not cleaned until it is added. Do not rename it to a known pack ID, and do not choose rules by name prefix (`en-*`, `code-*`): each rule's scope is tested on the gold sets of its own packs only. To add one, in order:

1. Get a gold set for it in `gold/<pack_id>_gold.csv`. Without one its harm test is NOT TESTABLE, and its rules cannot be signed off.
2. Add the pack ID to the `SPEC_PACKS` line of each rule that should run on it in `specv1.md`.
3. Rebuild (step 1). The pack then has a family in `clean._FAMILY`, and `run_clean.py` accepts it.
4. Add it to `FAMILIES` in `spec_v1/tests/test_clean.py` and run the unit tests (step 2).
5. Run the harm tests (step 4) on all the packs.

## Troubleshooting

| what you see | why | what to do |
|---|---|---|
| `<file>: '<name>' is not one of the 13 packs clean.py has rules for` and exit code 1, nothing written | The file name is not one of the 13 pack IDs. Without this stop, every document would pass through unchanged. | If it is a known pack under another name, name the file `<pack_id>.parquet`. If it is a new pack, see [Add a new pack](#add-a-new-pack). |
| `<file>: doc_id ... has pack_id '...'` and exit code 1 | The pack's `pack_id` column does not match its file name. | Rename the file to the pack ID in the column. |
| `errors` lists `ModuleNotFoundError` on English documents | `ftfy` is not installed (`DA-A3-002`). | `pip install ftfy` |
| `errors` lists `ModuleNotFoundError` on code documents | `tree-sitter-language-pack` is not installed. The shared F1 needs it when it finds an email, phone or address in code. | `pip install tree-sitter-language-pack` |
| `make_harm_tests.py` stops with `ModuleNotFoundError: No module named 'harm_test'` | Its first argument is not the `era-v5-lab` folder. | Run it from `teams/01-data-a/` and pass `../..`. |
| `harm_tests.md` lists packs as "pack not on this machine" | The pack is in none of the folders you passed. | Pass every folder that holds packs. |
| `harm_tests.md` says "other snapshot" | Your gold set or pack is not the one `specv1_validation.json` used, so the two are not compared. | Use the gold sets in `gold/` and the current packs. |
| `AssertionError` from `build_clean.py` | The sheet breaks one of the checks under [When the build stops](#when-the-build-stops). | Fix the rule the message names, and rebuild. |
| `test_the_build_writes_this_clean_py` fails | `specv1.md` or `f1_rule.py` changed after the last build. | Rebuild (step 1). |

## What not to do

- Do not edit `clean.py`. It is generated.
- Do not commit a `harm_tests.md` made without all 13 packs.
- Do not commit packs or `_clean.parquet` outputs.
- Do not take a rule off a pack to make a harm test pass. A failing rule stays in, and blocks release until it is reviewed, as `specv1.md` says.
