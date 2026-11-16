# G3 frozen tokenizer: C3 sample-v0

The tokenizer for training is **C3 sample-v0**, frozen in #340 (Gate 2, `../freeze_report.md`).

| Field | Value |
|---|---|
| `tokenizer.json` sha256 | `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3` |
| Vocab / merges | 131,072 (ids 0..131071) / 130,460 |
| Special tokens | 356, same ids as v0 / v0.1 |
| eos | `<\|endoftext\|>` 130822, added by Data A's shard writer after every document |
| bos / pad / unk | 130725 / 130726 / 130727 (`SPECIAL_TOKENS.md`) |
| Build manifest | `../train/c3_s0_manifest.json` (every input's sha256) |

## Files

| File | What |
|---|---|
| `tokenizer.json` | Not in the repo: at 8 MB it is over the 5 MB pr-guard limit. Download it (below) and put it here. |
| `tokenizer_config.json`, `special_tokens_map.json` | Name the bos / eos / pad / unk roles, so `AutoTokenizer.from_pretrained` loads the same way for every team. Nothing is added when encoding. |
| `SPECIAL_TOKENS.md` | The special-token roles and why (#407). |
| `SHA256SUMS` | sha256 of `tokenizer.json` and of every repo file needed to check or rebuild it. |
| `verify_release.py` | Checks a downloaded copy (below). |

## 1. Get it

Download `tokenizer.json` from the Kaggle dataset [`sohiyiy/c3-sample-v0`](https://www.kaggle.com/datasets/sohiyiy/c3-sample-v0) and put it at `teams/03-tokenizer/release/tokenizer.json`. The dataset is private; ask G3 for access. It also holds the build manifest and its own `SHA256SUMS`.

```
kaggle datasets download -p teams/03-tokenizer/release --unzip sohiyiy/c3-sample-v0
```

## 2. Check it

```
cd teams/03-tokenizer && sha256sum -c release/SHA256SUMS     # macOS: shasum -a 256 -c release/SHA256SUMS
python release/verify_release.py release/tokenizer.json
```

`verify_release.py` needs only `tokenizers` (and `transformers` for its last check). It checks:
- the sha256 and the pinned repo files;
- the vocab, merges and special-token counts;
- the role ids, and that each special token is one token;
- a round trip on a line in each of the 11 Indic languages, English and code;
- that `AutoTokenizer` gives the same ids.

It prints `RESULT: PASS` and exits 0, or names what failed. Any other file, for example a candidate such as p1536, fails on the sha.

## 3. Use it

```python
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("teams/03-tokenizer/release")   # tokenizer.json + the two configs
ids = tok.encode("भारत एक विशाल देश है।")                             # no bos, no eos added
assert tok.eos_token_id == 130822
```

With `tokenizers` only: `Tokenizer.from_file("teams/03-tokenizer/release/tokenizer.json")`, and encode with `add_special_tokens=False`.

- The normalizer (NFC plus the fixes in `../v1/normalizer.md`) is part of `tokenizer.json`. So `decode(encode(x))` gives the normalised text, which can differ from raw `x` on Bengali / Punjabi nukta text.
- Tools that drop the normalizer, for example the GGUF conversion, can give different ids on such text.
- Record the sha256 with anything you build from the ids. Data A's shards carry it as `tokenizer_sha256`.

## 4. Rebuild it

A fresh build from the pinned inputs gives the same bytes. Run the TSAI job script:

```
python teams/03-tokenizer/train/rebuild_c3_s0.py --config teams/03-tokenizer/train/rebuild_c3_s0.json
```

- **Inputs:** under `./inputs/`, pinned by sha256: corpus60, tokenizer sample v0, BrahmicTokenizer-131K and o200k_base. The table is in `../jobs/2026-11-02-c3-s0-rebuild.md`.
- **Packages:** `tiktoken==0.14.0`, `tokenizers==0.23.3`, `pyarrow`.
- **Run:** about 5 minutes on CPU. No network is needed.
- **Result:** the script checks every input before it builds, then writes `out/result.json` with the built sha256 and PASS / FAIL.

Builds so far, all `15468e66…`:

| When | Code | Log |
|---|---|---|
| #195, built twice | #195 | manifest `rebuild_sha256` |
| 2 Nov, TSAI job #218 (no network) | #195 | `../jobs/2026-11-02-c3-s0-rebuild.log` |
| 13 Nov, the `train_bpe.py` pinned now (#414) | `341ef046…` | `../jobs/2026-11-13-c3-s0-rebuild-pr414.log` |
