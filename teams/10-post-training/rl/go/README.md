# Go tasks for RL data v1 (`go_verifier.py`, `tasks/`)

The same design as the Python verifier (`../verifier.py`), for Go code: a candidate answers with one `package main` Go block (standard library only, no `main`). The sandbox gets the candidate's code and the inputs only; the generic runner `_go_runner.go` calls the entry point with reflection and writes the outputs; `go_verifier.py` compares them with the expected values, which never enter the sandbox. The entry point may return `T`, `(T, error)` or `error`.

```text
rl/go/
  README.md            this file
  go_verifier.py       reward(), check_task() and the command line
  _go_runner.go        runs inside the sandbox: calls the entry point, writes results.json (inputs only)
  go.Dockerfile        the sandbox image (standard-library build cache baked in)
  test_go_verifier.py  correct and wrong answer for every task, the cheating cases, the lint
  tasks/<task_id>/     task.json, prompt.md, visible_tests.json, hidden_tests.json, reference.go
```

Needs: Python 3.10 or later with `pytest`, and `go` (1.23 or later) on `PATH`. `--sandbox docker` also needs Docker (see below).

```bash
python teams/10-post-training/rl/go/go_verifier.py --check-task teams/10-post-training/rl/go/tasks/<task_id> [--sandbox docker]
python teams/10-post-training/rl/go/go_verifier.py --reward teams/10-post-training/rl/go/tasks/<task_id> completion.txt [--sandbox docker]
python -m pytest teams/10-post-training/rl/go/test_go_verifier.py -q -p no:cacheprovider
```

- `completion.txt` is a model answer: any text with a fenced Go block (the last one counts), for example:

  ````text
  Here is my answer.
  ```go
  package main
  func ParseRoman(s string) (int, error) { ... }
  ```
  ````

  The command prints one JSON line with `reward` (1 only if every visible and hidden test passes), `passed`, `total` and a `reason`. It never prints which hidden test failed. Exit code 2 means a missing task folder or file.
- To add a task: copy a folder in `tasks/`, change the five files, then run `--check-task` on it with both sandboxes. The lint needs 2 or 3 visible and at least 10 hidden tests, a reference that scores 1, an exported entry-point name, no hidden call written in the prompt, and a `source` that starts with `original` and says who wrote it. Add a wrong answer for it to `WRONG` in `test_go_verifier.py`.
- A task folder has the same files as a Python task, with `reference.go` and `"language": "go"` in `task.json`. A case is `{"args": [...], "expected": ...}`, or `{"args": [...], "raises": "error"}` (the function returns a non-nil error) or `"raises": "panic"`. An empty result must be a non-nil slice or map (it must not print as `null`); the prompt says so.
- `--sandbox docker` needs the image from `go.Dockerfile`: `docker build -f teams/10-post-training/rl/go/go.Dockerfile -t g10-go-rl:1 teams/10-post-training/rl/go` (`G10_GO_IMAGE` names another image). It bakes in the standard-library build cache, so one run takes about a second instead of 17. The container has no network, a read-only root, no capabilities, 768 MB, 1 CPU and 128 processes. The container script discards the candidate's output, and a missing image or daemon raises `RuntimeError` instead of scoring 0. The work folder is a host temp folder bounded only by a 64 MB limit per file, so point `TMPDIR` at a size-limited volume for long training runs. The default `process` sandbox is for unit tests only (it has no network or file isolation, and Go cannot run under the memory and process limits used for Python).
- **Who wrote the tasks, and how they may be used.** Like the Python tasks in `../tasks/`, these tasks, tests and references were written by Claude (AI assistant) for Ravi Naik, and each `task.json` says so. TSAI's data rule of 3 Nov (`../../rl-data/README.md`) allows human-written problems only for training, so these tasks are for evaluation and for testing the verifier until TSAI says otherwise. None comes from a benchmark.
- Tasks so far (10): `parse_size`, `parse_kv_line`, `split_balanced`, `merge_intervals`, `parse_roman`, `top_words`, `lru_trace`, `expand_rle`, `compare_semver`, `cidr_contains`. Each has a correct and a wrong answer in `test_go_verifier.py`, plus the cheating cases (exit in `init`, forged result file, printing, hard-coded examples, infinite loop, panic, no network).
- **Decontamination (14 Nov):** the prompt and the reference solution of each of the 10 tasks (20 documents) were checked with `teams/09-evaluation/decontam/decontam_check.py` (fingerprints v2, full set, `set_sha256` `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`) and `canary_scan.py`, lab main `3af7741`. Result: 0 flagged, 0 canary. To repeat it, write one JSONL line per prompt and per reference (`doc_id`, `text`) and run both scripts on it. Hidden tests are not text a benchmark holds, and are not sent to the model.
