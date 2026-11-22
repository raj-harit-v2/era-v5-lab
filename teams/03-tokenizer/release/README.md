# G3 frozen tokenizer: p1536

The tokenizer for training is **p1536**, frozen by TSAI on 16 Nov 2026. From week 3 on, all numbers use p1536.

p1536 is C3 sample-v0 plus 1,536 extra merges per Indic script, on more unused o200k base ids (#414, v2_spec idea 1). It replaces C3 sample-v0 (`15468e66…`, #340), which is archived in `archive/c3-sample-v0/`.

| Field | Value |
|---|---|
| `tokenizer.json` sha256 | `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` |
| Vocab / merges | 131,072 (ids 0..131071) / 130,460 |
| Special tokens | 356, the same ids as C3, v0 and v0.1. The `added_tokens` entries are byte-for-byte the same as C3's. |
| eos | `<\|endoftext\|>` 130822, added by Data A's shard writer after every document |
| bos / pad / unk | 130725 / 130726 / 130727 (`SPECIAL_TOKENS.md`) |
| Build manifest | `../train/p1536_s0_manifest.json` (sha256 of all 30 inputs) |
| Pass bar (FLORES-200 + code, vs BrahmicTokenizer-131K) | Mean Indic −24.81% (C3: −17.10%); En −0.11%, HumanEval +0.07%, MBPP +0.28%: PASS (`../COMPARE.md`, #436) |

What changes from C3:
- **Every C3 id keeps its token, except 13,824.** Those ids held o200k base tokens that our English/code text never uses; they now hold the extra Indic merges, 1,536 per script, appended to that script's merges. The 356 specials and all 16,739 script-block ids are unchanged (`check_ids.py --old-has-swap`, #414).
- **Indic text needs fewer tokens:** −9.30% against C3 on FLORES-200, and −9.51% on the FineWeb-2 check split. Every language gets better.

## Files

| File | What |
|---|---|
| `tokenizer.json` | Not in the repo: at 6.6 MB it is over the 5 MB pr-guard limit. Download it (below) and put it here. `.gitignore` keeps it out of commits. |
| `tokenizer_config.json`, `special_tokens_map.json` | Name the bos / eos / pad / unk roles, so `AutoTokenizer.from_pretrained` loads the same way for every team. Nothing is added when encoding. The roles are unchanged from C3. Since 20 Nov `tokenizer_config.json` also embeds G10's chat template (`chat_template.jinja` sha256 `b00137fe…`, byte-identical to `teams/12-quantization/tokenizer/chat_template.jinja`), so servers no longer need `--chat-template` (chat_format_check finding 5). |
| `generation_config.json` | `eos_token_id: [130816, 130822]`: generation stops at `<\|im_end\|>` (end of a chat turn) or `<\|endoftext\|>` (chat_format_check finding 2). |
| `SPECIAL_TOKENS.md` | The special-token roles and why (#407), on the p1536 sha. |
| `SHA256SUMS` | sha256 of `tokenizer.json` and of every repo file needed to check or rebuild it. |
| `verify_release.py` | Checks a downloaded copy (below). |
| `archive/c3-sample-v0/` | The previous freeze (C3, #340, #465), with its own README, SHA256SUMS and verify script. |

## 1. Get it

Download `tokenizer.json` (6.0 MB) from Google Drive, open to anyone with the link, no sign-in: [tokenizer.json](https://drive.google.com/file/d/1CoAWJ18ujjnDY3_wdQNO1-2fB_9jUCbI/view?usp=sharing). Put it at `teams/03-tokenizer/release/tokenizer.json`.

From a terminal or a job host:

```
curl -L -o teams/03-tokenizer/release/tokenizer.json 'https://drive.usercontent.google.com/download?id=1CoAWJ18ujjnDY3_wdQNO1-2fB_9jUCbI&export=download&confirm=t'
```

The same file is also in the private Kaggle dataset [`sohiyiy/p1536-sample-v0`](https://www.kaggle.com/datasets/sohiyiy/p1536-sample-v0) (ask G3 for access), with the build manifest and its own `SHA256SUMS`:

```
kaggle datasets download -p teams/03-tokenizer/release --unzip sohiyiy/p1536-sample-v0
```

Whichever copy you use, check its sha256 (below) before using it.

## 2. Check it

```
cd teams/03-tokenizer && sha256sum -c release/SHA256SUMS     # macOS: shasum -a 256 -c release/SHA256SUMS
python release/verify_release.py release/tokenizer.json
```

`verify_release.py` needs only `tokenizers` (and `transformers` for its last check). It checks:
- the sha256 and the pinned repo files;
- the vocab, merges and special-token counts;
- the role ids (eos 130822), and that each special token is one token;
- a round trip on a line in each of the 11 Indic languages, English and code;
- that `AutoTokenizer` gives the same ids.

It prints `RESULT: PASS` and exits 0, or names what failed. Any other file fails on the sha, C3 included.

## 3. Use it

```python
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("teams/03-tokenizer/release")   # tokenizer.json + the two configs
ids = tok.encode("भारत एक विशाल देश है।")                             # no bos, no eos added
assert tok.eos_token_id == 130822
```

With `tokenizers` only: `Tokenizer.from_file("teams/03-tokenizer/release/tokenizer.json")`, and encode with `add_special_tokens=False`.

- The normalizer (NFC plus the fixes in `../v1/normalizer.md`, the same as C3's) is part of `tokenizer.json`. So `decode(encode(x))` gives the normalised text, which can differ from raw `x` on Bengali / Punjabi nukta text.
- Tools that drop the normalizer, for example the GGUF conversion, can give different ids on such text.
- Record the sha256 with anything you build from the ids. Data A's shards carry it as `tokenizer_sha256`.
- Ids made with C3 are not p1536 ids for Indic text. Re-tokenize; do not mix the two.

## 4. Rebuild it

A fresh build from the pinned inputs gives the same bytes. `rebuild_cand.py` is `rebuild_c3_s0.py` (TSAI job #218) with the candidate as a parameter:

```
python teams/03-tokenizer/train/rebuild_cand.py --config teams/03-tokenizer/train/rebuild_cand.json --cand p1536
```

- **Inputs:** under `./inputs/`, the same as the C3 job, pinned by sha256: corpus60, tokenizer sample v0, BrahmicTokenizer-131K and o200k_base (table in `../jobs/2026-11-02-c3-s0-rebuild.md`). The script also checks the repo files the manifest pins: `train_bpe.py`, `slots_p1536.json`, `o200k_v2.json`, `mix_s0.json` and the normalizer. It checks the v0.1 tokenizer it builds too.
- **Packages:** `tiktoken==0.14.0`, `tokenizers==0.23.3`, `pyarrow`.
- **Run:** about 6 minutes on CPU. No network is needed.
- **Result:** `out/result.json` with the built sha256 and PASS / FAIL.
- `--cand c3` and `--cand p768` rebuild the other two.

Builds so far, all `e6b93a93…`:

| When | Code | Log |
|---|---|---|
| #414, built twice | `train_bpe.py` `341ef046…` | manifest `rebuild_sha256`, `reproducible` |
| 16 Nov, `rebuild_cand.py --cand p1536` (no network) | the files pinned in `SHA256SUMS` | `../jobs/2026-11-16-p1536-rebuild.log` |
