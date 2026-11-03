# Tamil UTF-8 SWE task: measured local run

Run date: 28 October 2026. Python: 3.9.6. This is an authored local software
repair smoke task with Tamil instructions and authored test strings. It does not
use diagnosis-pack text, run a model, train a model, or report a SWE-bench score.
Execution used local Python subprocesses; Docker was not used.

## Task and result

The writer must preserve Tamil text, combining sequences, ZWJ/ZWNJ and mixed
newline sequences exactly. The runner copies the correct helper and regression
tests into a temporary task directory, introduces an ASCII writer defect, reads
that file, measures failure, applies the UTF-8 repair and measures success.
The checked-in helper remains correct throughout the run.

```diff
-    with Path(path).open("w", encoding="ascii", errors="ignore", newline="") as stream:
+    with Path(path).open("w", encoding="utf-8", newline="") as stream:
```

| Check | Measured outcome |
| --- | --- |
| ASCII baseline | 4 tests run; 4 failures; exit 1 |
| UTF-8 repair | 4 tests run; 0 failures; exit 0; `OK` |
| Checked-in helper regression suite | 4 tests; `OK` |
| Trajectory | 11 messages; effort `4k`; exact render/parse equality |
| Output file | 101 bytes; exact equality with authored text encoded as UTF-8 |
| Marker scan | IDs `0, 1, 2, 26, 27, 28, 29`; synthetic surface scan only |

Output SHA-256:
`6525f0c6ea3ea558485c753118c0e54e6bf2de1fc514bada529b9ff39be3983f`.

The four regression cases cover Tamil mixed with ASCII, distinct composed and
decomposed vowel sequences, both joiner characters, and LF/CRLF/CR preservation.
They compare both decoded content and exact UTF-8 bytes.

## Reproduce from the repository root

```sh
python3 -B -m unittest discover -s teams/10-post-training/tests -p test_tamil_utf8_io.py -v
python3 -B teams/10-post-training/swe-task/run_tamil_e2e.py
```

The runner prints its evidence directory. To choose an evidence directory, add
`--output-dir <directory-outside-the-repository>`. Its temporary task directory
is removed after execution; the chosen evidence directory persists.

The runner saves the measured evidence in the output directory it prints:
`baseline.log`, `patched.log`, `trajectory.json`, `trajectory.chatml.txt`,
`summary.json` and the actual UTF-8 output `tamil_roundtrip.txt`. These are local
review artifacts; regenerate them with the runner.

## Recorded trajectory and limits

The eleven messages are: system, Tamil user, assistant `read_file`, actual file
result, assistant `run_tests`, actual failing test result, assistant `apply_patch`,
actual patch result, assistant `run_tests`, actual passing test result, Tamil
final reply. Tool observations contain the measured source, process return
codes and stdout/stderr. The runner authors this transcript from the execution
record; it is not a model-generated agent trajectory. No thinking span is added.

The shared `chat-format/render.py` and token allocation are used unchanged. The
marker scan verifies the renderer's declared surfaces only. G3's actual tokenizer
registration, training loss masks, effort-budget enforcement and tool-call ID
linking remain outside this smoke task.
