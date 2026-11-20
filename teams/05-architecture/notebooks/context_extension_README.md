# Guided context-extension experiment

Open [context_extension.ipynb](context_extension.ipynb) in Jupyter, VS Code or Colab.
Start with the assignment and method-choice sections, then read the four matched
conditions. Code comments explain the positional settings, data selection,
next-token shift and timing scope.

The notebook has **16 freshly executed code cells**, with tables, PNG charts
and a final run manifest saved in its outputs. Execution finished at `2026-11-18T07:27:09.670544+00:00`.
The first result panel is explicitly labelled as the original pilot snapshot;
outputs below the code cells come from the readability rerun. All code cells
completed without error. Maximum mean-NLL drift from the original BF16 pilot:
`0` nats/token. See [the execution receipt](../results/context_extension/readability_rerun.json).

## How it fits the submission

The G5 task is a long-context design plus a small-model extension test. The
primary G5-corpus result uses eager attention and the full vocabulary head in
[the separate runner](../harness/context_extension_check.py) and
[the submission plan](../docs/long_context_plan.md). This notebook teaches the
earlier WikiText pilot, which uses SDPA and a tail-only output head. Its losses
and performance figures remain separate from the G5-corpus measurements.

## Run again

Use Python 3.13 and a CUDA GPU supporting BF16 with a compatible driver.
From the repository root:

```bash
python -m pip install -r teams/05-architecture/notebooks/requirements-context-extension.txt
jupyter lab teams/05-architecture/notebooks/context_extension.ipynb
```

Select the matching Python kernel and Run All. Model and dataset revisions are
pinned. New files go to `out/context_extension_pilot/` below the kernel working
directory; committed measurements are not overwritten. The full sweep reaches
48 repeated inputs and was run on an approximately 95-GiB GPU. Its timing and
precision checks are exploratory evaluation measurements.

For a noninteractive execution outside the source tree:

```bash
jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=1800 --output context_extension_executed.ipynb --output-dir /tmp teams/05-architecture/notebooks/context_extension.ipynb
```

Offline evidence checks need only Python's standard library:

```bash
python teams/05-architecture/tests/verify_context_extension.py
```

Original executed source and replay hashes remain in
[source_provenance.json](../results/context_extension/source_provenance.json).
The exact historical source is preserved in Git commit
`9539c7be6263b3fe429a5096dac8c77ed1428f63`.
