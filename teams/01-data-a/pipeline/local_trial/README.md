# Local trial of the pipeline

Run the whole pipeline on six small files on your own machine, stage by stage, before you raise a job request. `JOB_REQUEST.md` rule 2
asks for a log of the same script on your own machine, and these commands make it. The configs in `configs/` are also the examples to
copy for a job: pick the one that matches your scenario, paste its command into the request, and change only what the last section lists.

Everything that defines a run is a key in its config file, and the command is only `--config <file>`. That is what a TSAI job's
`Command:` line carries.

| | |
|---|---|
| **Input** | six parts of TSAI's tokenizer sample v0: five held-out parts (`code-go`, `code-rust`, `en-dclm`, `ind-hi-sangraha-v`, `ind-ta-fw2`) and one train part (`code-rust/part-00001`). 26 MB, about 17.8K rows |
| **Why a train part** | held-out parts are never removed by dedup and never sharded, so without a train part dedup and shards would test nothing. `ind-ta-fw2` has no cleaning rules, so it tests the pass-through |
| **Needs** | the sample folder (`sample_manifest.json`, `train/`, `heldout/`); Python with the pipeline's packages (`pyarrow`, `ftfy`, `tree-sitter`, `numpy`, `scipy`, `tokenizers`, `torch`: [spec_v1/requirements.txt](../../spec_v1/requirements.txt) and the notes in [../README.md](../README.md)); Linux or macOS (`overlap.py` uses `resource`); the dedup scripts in `teams/01-data-a/dedup/` |
| **Time** | a few minutes; F2 takes most of it (about 20 s per worker to load G9's fingerprint set) |

Run every command from the repository root, with the Python that has the packages (for example `conda activate era5`).

## Files

| File | What it is |
|---|---|
| `configs/1-full.json` | **scenario 1**: the whole chain, clean to shards |
| `configs/2-stop-at-clean.json` | **scenario 2**: stop after a stage with `"to"` |
| `configs/3a-steps-to-dedup.json`, `3b-steps-apply-to-f2.json`, `3c-steps-survivor-loss-and-shards.json` | **scenario 3**: one run in three steps (`"to"`, then `"from"`), all with run id `trial-steps` |
| `configs/4-adopt-clean.json` | **scenario 4**: adopt the clean folder of scenario 3 and run only overlap and dedup |
| `configs/5-error-from-without-record.json`, `6-error-changed-folder.json` | **scenario 5**: runs that must stop with a clear message |
| `show.py` | prints a run's totals, a line per stage and any failed check |

Each config has a `_comment` that says what it shows.

## 1. Set up the inputs

Put the six parts and the sample manifest under `inputs/local_trial/`. Set `SAMPLE` once to your copy of the sample (TSAI's `week-2` folder), then
copy from it. The clean job checks every part against the manifest's size and sha256 before it starts.

```bash
export SAMPLE=/path/to/tokenizer_sample_v0
for part in heldout/code-go/part-00000 heldout/code-rust/part-00000 heldout/en-dclm/part-00000 heldout/ind-hi-sangraha-v/part-00000 heldout/ind-ta-fw2/part-00000 train/code-rust/part-00001; do
  mkdir -p "inputs/local_trial/$(dirname $part)" && cp "$SAMPLE/$part.parquet" "inputs/local_trial/$part.parquet"
done
cp "$SAMPLE/sample_manifest.json" inputs/local_trial/sample_manifest.json
mkdir -p out/local_trial
```

The shards stage needs a `tokenizer.json`. These configs use `any_tokenizer: true`, so any file works and the shards are marked `test`. G6's
baseline tokenizer is fetched once into `~/.cache` (it needs the network the first time):

```bash
cp "$(python -I -c "import sys; sys.path.insert(0, 'teams/06-performance'); from dataio.tokenizer import BrahmicTokenizer as B; print(B().path)" 2>/dev/null | tail -1)" inputs/local_trial/tokenizer.json
```

The manifest is the full sample's `sample_manifest.json` (86 parts): the clean job refuses a smaller one. `"only"` in the config picks
the six parts. It must be this file, because the config pins its sha256 (`7fd647c8…`).

## 2. Check a config without running it

```bash
python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/pipeline/local_trial/configs/1-full.json --plan
```

This checks the config like a run and prints every stage's folder and command, without running or writing anything. It works the same on
every config below. (The shards stage checks that `inputs/local_trial/tokenizer.json` exists, even for a plan.)

## Where the output goes

The default is the config's `"out": "out/pipeline"`, and every run gets its own folder, `out/pipeline/<run_id>/`, named by the config's `run_id`.
Everything the run makes is inside it. TSAI jobs write only under `./out/`, so keep this.

```
out/pipeline/<run_id>/
  cfg/                    the exact config each of clean, overlap and dedup ran with: the settings file plus the paths the runner filled in
  clean/ overlap/ dedup/  the three stages' outputs (an adopted stage stays in its own folder)
  deduped/ final/ report/ apply, F2 and survivor loss: `final/` holds the pipeline's data output and the `.f2.json` reports
  shards/                 the shards, shards_summary.json and a copy of cleaning_pipeline.json (if the config has a shards stage)
  logs/                   each script's output (clean.log, overlap.log, f2_*.log, shards.log, ...)
  pipeline_manifest.json  the config that ran, each stage's counts, digests and checks, and the settings hashes
  cleaning_pipeline.json  which clean.py, F2 set, dedup list and settings produced the shards
```

The clean job refuses a run folder that already exists, so a new run needs a new `run_id` (change it in the config), or delete the folder
(see the end of section 3).

## 3. Scenarios

After every run, `show.py` prints the totals, a line per stage and any failed check. It exits with `1` if a check failed.

### Scenario 1: the whole chain

Clean, overlap, dedup, apply, F2, survivor loss and shards. The `tee` keeps the log you attach to a job request.

```bash
python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/pipeline/local_trial/configs/1-full.json 2>&1 | tee out/local_trial/1-full.log
python teams/01-data-a/pipeline/local_trial/show.py trial-full
```

Expect: every stage ran, `failed checks: none`, and `out/pipeline/trial-full/shards/` holds one `code-rust` shard (the held-out `code-rust`
part is `not_sharded`; `shards_summary.json` says how many rows fit). About 17.8K rows go in, and a little fewer come out of clean.

### Scenario 2: stop after a stage

`"to": "clean"` stops after clean. Only the stages up to `to` are checked, so a clean-only job needs no other stage entries.

```bash
python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/pipeline/local_trial/configs/2-stop-at-clean.json 2>&1 | tee out/local_trial/2-stop-at-clean.log
python teams/01-data-a/pipeline/local_trial/show.py trial-stop-clean
```

Expect: `out/pipeline/trial-stop-clean/` holds only `clean/`, `cfg/`, `logs/` and the manifest.

### Scenario 3: one run in steps

Three configs with the same `run_id` (`trial-steps`), so they share one folder. Step b skips the stages the manifest already holds, after checking
that their folders still match the digests it recorded. Run the steps in order.

```bash
python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/pipeline/local_trial/configs/3a-steps-to-dedup.json
python teams/01-data-a/pipeline/local_trial/show.py trial-steps

python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/pipeline/local_trial/configs/3b-steps-apply-to-f2.json
python teams/01-data-a/pipeline/local_trial/show.py trial-steps

python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/pipeline/local_trial/configs/3c-steps-survivor-loss-and-shards.json
python teams/01-data-a/pipeline/local_trial/show.py trial-steps
```

Expect: after 3a, clean, overlap and dedup; after 3b, apply and F2 are added; after 3c, survivor loss and shards. `show.py` lists the stages
recorded so far.

### Scenario 4: adopt a folder from another run

The `clean` stage is `{"mode": "adopt", "output": "out/pipeline/trial-steps/clean"}`: it is not run again, and overlap and dedup run on it. This is how a
dedup job starts from a cleaned folder TSAI returned. Run scenario 3 first.

```bash
python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/pipeline/local_trial/configs/4-adopt-clean.json 2>&1 | tee out/local_trial/4-adopt-clean.log
python teams/01-data-a/pipeline/local_trial/show.py trial-adopt
```

Expect: `clean` is listed as `adopt`, and `out/pipeline/trial-adopt/` has `overlap/` and `dedup/` but no `clean/`.

### Scenario 5: runs that must stop

Each of these should stop with a clear message and a non-zero exit code. Run them after scenario 1.

```bash
# a. run a finished run again: the clean job refuses the existing folder ("output folder already exists")
#    (this also overwrites that run's logs/clean.log with the error)
python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/pipeline/local_trial/configs/1-full.json

# b. "from" on a run with no manifest ("stage clean has no record")
python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/pipeline/local_trial/configs/5-error-from-without-record.json

# c. resume after a stage's folder changed ("changed after the manifest recorded it; rerun from dedup")
echo x >> out/pipeline/trial-full/dedup/remove_list.csv
python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/pipeline/local_trial/configs/6-error-changed-folder.json
```

Test c corrupts the `trial-full` run on purpose. Delete the trial runs before you run the scenarios again:

```bash
rm -rf out/pipeline/trial-full out/pipeline/trial-stop-clean out/pipeline/trial-steps out/pipeline/trial-adopt out/pipeline/trial-bad-from
```

## From the trial to a job request

1. Copy the config closest to your job to `jobs/<date>-<name>/run.json` and edit the copy (the table below).
2. Run your edited config here on the trial parts (keep `only` and the trial input), so the log shows your exact config working:

   ```bash
   python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/jobs/<date>-<name>/run.json 2>&1 | tee teams/01-data-a/jobs/<date>-<name>/logs/local-trial.txt
   ```
3. Write the request `jobs/<date>-<name>.md` from `JOB_REQUEST.md`:
   - `Script:` `teams/01-data-a/pipeline/run_pipeline.py`
   - `Command:` `python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/jobs/<date>-<name>/run.json`
   - `Config:` `teams/01-data-a/jobs/<date>-<name>/run.json`
   - `Test log:` `teams/01-data-a/jobs/<date>-<name>/logs/local-trial.txt`
   - `Inputs:`, `Hardware:`, `Max time:`, `Measures:` and `Expected result:` as the job needs; the `Outputs:` are under `out/pipeline/<run_id>/`.
4. A job answers one question, reads only its inputs and writes only under `./out/`. A request to clean the full corpus is not allowed
   (`JOB_REQUEST.md`, rule 6); the sample v0 jobs were sample-only, as TSAI clarified. The settings files your config names (and the runner
   itself) must be in the request's PR or already merged, because TSAI runs from the repository.

### What to change in the run config for a TSAI run

| Key | In the trial | For TSAI's run |
|---|---|---|
| `run_id` | `trial-…` | a new, unique name for the job, such as `dedup-pr<N>`. TSAI's machine writes `out/pipeline/<run_id>/`, and the clean job refuses an existing folder |
| `stages.clean.input` | `inputs/local_trial` | the folder TSAI staged, `inputs/tokenizer_sample_v0` (repo-relative; no absolute paths) |
| `stages.clean.only` | the six trial parts | delete the key for the whole sample (all 86 parts); keep a list only for a job on chosen parts |
| `stages.clean.manifest_sha256`, `expected_parts` | sample v0's values | the same for sample v0; new values for any other input set, which brings its own manifest |
| `stages.clean.manifest` | not set: `sample_manifest.json` in the input folder | leave it out if TSAI's staged folder holds `sample_manifest.json`; otherwise set it to a tracked copy, such as `teams/01-data-a/jobs/2026-11-02-tokenizer-sample-v0-clean/tokenizer_sample_v0_manifest.json` |
| `stages.<clean · overlap · dedup>` with `"mode": "adopt"` | only scenario 4 | to start from a folder an earlier TSAI job returned, `{"mode": "adopt", "output": "out/<folder on TSAI's machine>"}`; the rest of the stages run |
| `to`, `from` | scenarios 2 and 3 | `to` for a job that stops early (a clean-only job: `"to": "clean"`); delete both for the whole chain. Resuming with `from` needs the run's manifest, which a new TSAI run does not have |
| `stages.shards` | `any_tokenizer: true`, `tokens`, `packs: ["code-rust"]`, the trial tokenizer | G3's frozen p1536 `tokenizer.json` (repo-relative path on TSAI's machine), no `any_tokenizer`, no `tokens` (the default is 2^26 per shard); `packs` only lists packs that have a lane in `shards/pack_table.json`, which is the code packs for now. Delete the whole key if the job needs no shards: a run with shards stops when no shard could be written |
| `stages.clean.workers` | `2` | parts cleaned at once, one process each (about 250 MB per worker); delete the key to use `clean.json`'s value (4), and size it to the request's CPUs and RAM. The output is the same for any number |
| `stages.f2.workers` | `2` | each worker needs about 1.1 GB, plus the documents in flight: size it to the request's RAM (8 GiB: at most 4) |
| `stages.<…>.settings` | the committed settings files | the same files; to try other settings, copy one into the job folder, edit the copy and point `settings` at it |
| `out` | `out/pipeline` | keep `out/pipeline`: a job writes only under `./out/` |

Run `--plan` on the final file (section 2) and paste that output into the request if it helps the reviewer.

## Not tested here

- G3's frozen p1536 tokenizer: the trial's shards use any tokenizer and are marked `test`.
- The full sample (86 parts), and TSAI's machine and staging.
- Packs outside the six: the trial covers one train code pack, four held-out packs and one pack without cleaning rules.

`inputs/` and `out/` are not committed, but they are not git-ignored either: check `git status` before you commit and never `git add -A`
at the repository root.
