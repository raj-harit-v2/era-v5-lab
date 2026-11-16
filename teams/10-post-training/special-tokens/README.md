# Special tokens

The special-token lists G10 prepared for the Tokenizer team (Team 3 / G3), with v1 also prepared for Team 4 and Team 9. The lead owns the final list, and TSAI reviews it at the Gate.

| File | What it is |
|---|---|
| `special_tokens_v0.md` | The first list: the 27 Oct ruling, the 256 reserved IDs (`0..255`), what is assigned and what stays reserved, and the token-smuggling defences. |
| `special_tokens_v1.md` | The consolidated allocation: the marker IDs, a machine-readable table for Team 3's tokenizer training and a pre-training sanity section. It replaces the 000 to 255 numbering of v0 with the real Team 3 token IDs, and records that reasoning effort is a plain-text system line (`Reasoning effort: {1k|4k|16k|64k}`) and not a token. |

Use `special_tokens_v1.md` for current IDs. Keep v0 for the reasoning behind each marker. The format that uses these tokens is in `chat-format/`.

## Gate

Gate 1 deliverable "Special-token list and chat format" (draft 28 Oct, final 31 Oct, plan sheet). `v1` is addressed to Teams 3, 4 and 9.

## What has been measured

These files are specifications. The only committed run that exercises the ids is `../results/render_frozen_tokenizer.txt`: one report on Team 3's tokenizer v0.1 that records the nine active markers as single tokens with the ids in `v1`. See `../chat-format/README.md`.

`v1` says some dataset checks found no ghost tokens (for example 0 of 500 documents in the `code-python` pack). Those checks are described in the file; this README has not re-run them.

## What has not been measured

- No check on the Gate 2 tokenizer (sha 15468e66...). That file is not in the repo as of 12 Nov.
- No model has been trained with these markers.
- The `v0` numbering is superseded. Use `v1` for ids.

## Reports

- [../results/render_frozen_tokenizer.txt](../results/render_frozen_tokenizer.txt)
- [../chat-format/chat_format_v0.md](../chat-format/chat_format_v0.md)
