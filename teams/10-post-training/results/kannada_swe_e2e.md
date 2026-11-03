# Kannada chat-format and SWE verification

Kannada chat serialization and browser output are verified using the shared
`render.py` format for `ind-kn-fw2`.

## Coverage

- Words: `ಮನೆ`, `ಕನ್ನಡ`, `ಅಕ್ಕ`, `ಶಕ್ತಿ`.
- ZWNJ: `ಒನ್‌ಪ್ಲಸ್`, with `U+200C` after virama.
- RA: default, ZWJ-before-virama and legacy ZWJ-after-virama sequences.
- Exact text preservation across message fields and all four effort levels.
- SWE demonstration: failing tests → code patch → passing tests in a temporary copy.

## Verified results

- All 31 G10 tests passed (27 existing + 4 new Kannada tests).
- Local and Docker SWE runs had one failing test before the patch and both tests
  passed afterward.
- The 11-message trajectory round-tripped at `1k`, `4k`, `16k` and `64k`.
- All eight browser examples matched the expected appearance in Chrome on Linux
  using Noto Sans Kannada. The screenshot is included in the PR.
- The Kannada conversation in `chat_format_v0.md` was also visually confirmed.

Character preservation is checked automatically; visual appearance was checked
separately in the browser. The shared renderer and token allocation are unchanged.

## SWE before and after

The runner deliberately introduces a faulty version of `prepare_text()` in a
temporary copy. It measures the failure, applies the patch and reruns the tests.
The checked-in helper stays unchanged throughout the demonstration.

**Before:** the temporary helper applies NFKC and removes ZWNJ (`U+200C`) and
ZWJ (`U+200D`), in addition to ZWSP/BOM. This changes supplied text and removes
the distinction between the RA sequences.

**After:** the patched helper removes only ZWSP (`U+200B`) and BOM (`U+FEFF`).
It preserves the remaining code points and their order without normalization.

```diff
-STRIP = frozenset({"\u200b", "\u200c", "\u200d", "\ufeff"})
+STRIP = frozenset({"\u200b", "\ufeff"})
-    return "".join(ch for ch in unicodedata.normalize("NFKC", text) if ch not in STRIP)
+    return "".join(ch for ch in text if ch not in STRIP)
```

| Input | Before patch | After patch |
| --- | --- | --- |
| `ಒನ್‌ಪ್ಲಸ್`, containing ZWNJ | ZWNJ removed: `ಒನ್ಪ್ಲಸ್` | Original ZWNJ preserved |
| RA + ZWJ + virama + KA | ZWJ removed: RA + virama + KA | Original order preserved |
| RA + virama + ZWJ + KA | ZWJ removed: RA + virama + KA | Original order preserved |
| Mixed text containing `10²` | NFKC changes it to `102` | `10²` preserved |

The text-preservation test fails before the patch because these outputs differ
from the original inputs. The control-removal/marker test already passes: ZWSP
and BOM are removed, and a marker hidden with ZWSP is exposed for rejection by
the renderer. The patch preserves that behavior while fixing text preservation.

| Stage | Passed | Failed | Errors |
| --- | --- | --- | --- |
| Before patch | 1 | 1 | 0 |
| After patch | 2 | 0 | 0 |

These outcomes were verified locally and in Docker. Actual file contents, test
output and patch observations form the recorded Kannada tool trajectory.

## Reproduce

From the repository root:

```sh
python3 -B -m pytest -q -p no:cacheprovider teams/10-post-training/tests
python3 -B teams/10-post-training/swe-task/run_kannada_e2e.py --output-dir /tmp/g10-kannada-local
python3 -B teams/10-post-training/swe-task/preview_kannada.py
```

Browser preview: `file:///tmp/g10-kannada-preview.html`.
