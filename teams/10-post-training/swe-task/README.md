# SWE task demonstrations

Small end-to-end software-engineering tasks that show the chat format and a fail, patch, pass cycle. The Hindi, Kannada and Tamil runners save measured evidence (logs, the trajectory and a summary) to an output folder, by default a temporary one. The written-up results are in `results/`.

| Files | What it does |
|---|---|
| `calc.py`, `test_calc.py`, `Dockerfile`, `run_e2e.py` | A toy bug in `calc.py` (`return a + b + 1`), seeded and then patched inside Docker (results: `results/swe_e2e.md`). |
| `hindi_text_prep.py`, `Dockerfile.hindi`, `run_hindi_e2e.py` | Prepare Hindi (Devanagari) text for the tokenizer without changing what it says (results: `results/hindi_swe_e2e.md`). |
| `kannada_text_prep.py`, `kannada_examples.py`, `preview_kannada.py`, `Dockerfile.kannada`, `run_kannada_e2e.py` | Kannada demonstration: marker checking that removes only ZWSP and BOM, reviewed example words, and an offline browser preview of the rendered text (results: `results/kannada_swe_e2e.md`). |
| `tamil_utf8_io.py`, `run_tamil_e2e.py` | Write Tamil and other Unicode text without changing its code points (results: `results/tamil_swe_e2e.md`). |

The Go version is in `swe-task-go/`. The checks for these files are in `tests/`. The real SWE environments are in `swe-envs/`.

## Gate

Week 1 work on the G10 chat format and one SWE task end to end. These are not the RL environments; those are in `../swe-envs/`.

## What has been measured (committed reports)

- `results/swe_e2e.md`: the calculator task, run in Docker, before and after the patch.
- `results/hindi_swe_e2e.md`: run 30 Oct 2026 in Docker. The report says it is an authored smoke task and that it does not run a model, train a model or report a SWE-bench score.
- `results/tamil_swe_e2e.md`: run 28 Oct 2026 with local Python subprocesses, no Docker. Same statement about no model and no score.
- `results/kannada_swe_e2e.md`: Kannada serialization and a before/after run. The report also lists a browser check of eight examples; that check is not reproduced by these files.

## What has not been measured

- No model has attempted any of these tasks.
- No score of any kind. These tasks have one bug each and are too small to compare models.
- Hindi and Tamil use authored strings, not diagnosis-pack text (their reports say so).
- The Docker runs have not been repeated for this README.

## Tests

Task tests sit in `test_calc.py` and in `../tests/` (`test_hindi_text_prep.py`, `test_kannada_text_prep.py`, `test_tamil_utf8_io.py`, `test_kannada_chat_format.py`).

## Reports

- [../results/swe_e2e.md](../results/swe_e2e.md)
- [../results/hindi_swe_e2e.md](../results/hindi_swe_e2e.md)
- [../results/kannada_swe_e2e.md](../results/kannada_swe_e2e.md)
- [../results/tamil_swe_e2e.md](../results/tamil_swe_e2e.md)
