# Special-token roles for the frozen tokenizer (C3 sample-v0)

Applies to `tokenizer.json` sha256 `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3` (#340).
`added_tokens` with `special: true` in `tokenizer.json` is the source of truth for which ids are special (356 ids, same as v0/v0.1).
The two JSON files here only name the roles, so `AutoTokenizer.from_pretrained` loads them the same way for every team.

| Role | Token | Id | Why |
|---|---|---|---|
| bos | `<\|begin_of_text\|>` | 130725 | baseline bos, unchanged |
| eos | `<\|endoftext\|>` | 130822 | G10 v0.1 end-of-document marker; Data A's shards end every doc with it (#373) |
| pad | `<\|pad\|>` | 130726 | baseline pad, unchanged |
| unk | `<\|unk\|>` | 130727 | byte-level BPE never emits it; named for loaders that need one |

Notes
- Id 36 `<|end_of_text|>` is the baseline's old eos. It stays special but has no role; do not use it as eos.
- Chat turns end with `<|im_end|>` (130816), G10's ChatML marker. That is a turn marker, not eos.
- `add_bos_token` and `add_eos_token` are false: the shard writer adds the eos itself, and the harness measures without bos/eos.
- The ids were checked by rebuilding v0.1 from the baseline (`v0/build_v0.py`, `v0/build_v0_1.py` give sha256 `a33c9907…e578`); C3 keeps the v0.1 special ids (`train/c3_s0_manifest.json`: `special_layout` v0, `v0_tokenizer` v0.1).
