# Hindi text-preparation SWE task: measured Docker run

Run date: 30 October 2026. Image built from `python:3.12-slim` (Python 3.12.16), Docker Desktop 29.2.0.
This is an authored software-repair smoke task with Hindi instructions and authored test strings. It does not
use diagnosis-pack text, run a model, train a model, or report a SWE-bench score.

## Task and result

`swe-task/hindi_text_prep.py` prepares Hindi text for the tokenizer. The runner copies it, its tests and
`render.py` into a temporary task directory. It then seeds a bug that follows the `special_tokens_v1.md`
pre-tokenization line literally (NFKC plus removal of `U+200B..U+200D`). It reads that file, measures the
failure, applies the repair and measures success. The checked-in helper stays correct throughout.

The repair, as applied by the trajectory's `apply_patch`:

```diff
-import unicodedata
-STRIP = frozenset({"\u200b", "\u200c", "\u200d", "\ufeff"})
+STRIP = frozenset({"\u200b", "\ufeff"})
-    return "".join(ch for ch in unicodedata.normalize("NFKC", text) if ch not in STRIP)
+    return "".join(ch for ch in text if ch not in STRIP)
```

| Check | Measured outcome |
| --- | --- |
| Seeded v1 rule | 6 tests run; 4 failures; exit 1 |
| Repair | 6 tests run; 0 failures; exit 0; `OK` |
| Trajectory | 11 messages, 2 think spans; exact render/parse equality at `1k`, `4k`, `16k`, `64k` |
| Marker scan | IDs `0, 1, 2, 24, 25, 26, 27, 28, 29`; synthetic surface scan only |
| Reproducibility | two Docker runs gave byte-identical `summary.json` |

Patched file SHA-256 (equals the checked-in helper):
`0d767db2b9edc12aa3e6ae4342d8e3bfa92a5855525063a6261b3910168a8778`.

The four failing cases are the ones the v1 rule breaks. The two passing cases show the repair keeps its
security purpose:

| Test | v1 rule | Repair |
| --- | --- | --- |
| ZWJ half form `क्‍ष` kept | fail (ZWJ removed) | pass |
| ZWNJ kept | fail (ZWNJ removed) | pass |
| Precomposed nukta `ज़िंदगी` keeps `U+095B` | fail (split into `U+091C U+093C`) | pass |
| `10² वर्ग मीटर` not folded | fail (became `102`) | pass |
| `U+200B` and BOM removed | pass | pass |
| `<\|think\|>` hidden with `U+200B` rejected by `render.py` after prep | pass | pass |

`render.py` on its own does not reject a marker with a zero-width space inside it. The rejection depends on
`prepare_text()` removing `U+200B` first.

Measured on the runner's sample string (code points):

```text
input        0915 094D 200D 0937 0020 0915 094D 200C 0937 0020 095B 093F 0902 0926 0917 0940 0020 0031 0030 00B2 ...
seeded bug   0915 094D 0937 0020 0915 094D 0937 0020 091C 093C 093F 0902 0926 0917 0940 0020 0031 0030 0032 ...
repair       identical to input
```

## Reproduce from `teams/10-post-training`

```sh
docker build -f swe-task/Dockerfile.hindi -t g10-hindi-swe .
mkdir -p /tmp/g10-hindi-evidence
docker run --rm --network none --cap-drop=ALL --read-only --tmpfs /tmp \
  -v /tmp/g10-hindi-evidence:/evidence g10-hindi-swe
```

Without Docker: `python3 -B swe-task/run_hindi_e2e.py` (prints its evidence directory), and
`python3 -B -m unittest discover -s tests -p test_hindi_text_prep.py -v` for the checked-in helper.

The evidence directory holds `baseline.log`, `patched.log`, `trajectory.json`, `trajectory.chatml.txt` and
`summary.json`. The trajectory files differ between runs only in test timings inside the logged tool output.

## Recorded trajectory and limits

The eleven messages are: system, Hindi user request, assistant think + `read_file`, actual file content,
assistant `run_tests`, actual failing result, assistant think + `apply_patch`, actual patch result, assistant
`run_tests`, actual passing result, Hindi final reply. The runner authors the transcript from the execution
record; it is not a model-generated trajectory.

The shared `chat-format/render.py` and token allocation are used unchanged. The marker scan checks the
renderer's declared surfaces only. G3's real tokenizer, loss masks, effort-budget enforcement and tool-call ID
linking are outside this task. The `ind-hi-hplt` pack itself has no precomposed nukta letters and no ZWJ/ZWNJ.
