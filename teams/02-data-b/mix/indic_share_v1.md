# Native Indic share of every batch, v1 (16 Nov 2026)

Week 3, task 2 of the Data B work order (due Tue 17 Nov). It applies TSAI's two decisions of 16 Nov (G2) to the mix:

1. **Native-script Indic is a fixed 8% of every batch**, as in the V4 run and as taught in Session 5. V5 has no data
   selector, so the 8% is the fixed share of each batch.
2. **Romanised Indic is capped at 1% of tokens per language**, a ceiling and not a target (#481, proposal B). When a
   language is over the cap, whole romanised documents are dropped at random with the fixed seed. The rules stay as
   written in `romanised/romanised_policy_v1.md`. No romanised data is created.

This file splits the 8% across languages, from native token counts.

## Split of the 8%

| Language | Native packs in the shards | Native tokens (p1536) | Share of native tokens | **Share of every batch** |
|---|---|---:|---:|---:|
| hi | fw2, hplt, indiccorp, sangraha-v | 35,677,306 | 29.90% | **1.97%** |
| gu | fw2 | 16,066,252 | 13.47% | **1.05%** |
| bn | fw2, sangraha-v | 15,142,730 | 12.69% | **1.01%** |
| mr | fw2, sangraha-v | 14,405,459 | 12.07% | **0.98%** |
| sa | fw2 | 13,940,676 | 11.68% | **0.95%** |
| te | fw2, sangraha-v | 10,084,490 | 8.45% | **0.77%** |
| kn | fw2, sangraha-v | 9,498,844 | 7.96% | **0.75%** |
| ta | sangraha-v | 4,497,005 | 3.77% | **0.51%** |
| ml | no shard yet | 0 | 0 | **0** (0.3% floor once it has a shard) |
| or | no shard yet | 0 | 0 | **0** (0.3% floor once it has a shard) |
| **all** | 15 packs | **119,312,762** | 100% | **8.00%** |

The shares are rounded to two decimals, so the column adds up to 7.99; unrounded it is 8.00.

## How the split is made

- **Native tokens** are the `token_count` of the shard manifests: TSAI's 18 Indic shards of 16 Nov (sample v0 train
  parts, after `clean.py` and F2, frozen tokenizer p1536, sha256 `e6b93a93...`; EOS included). `share_split.py` stops
  if a manifest names another tokenizer.
- **Translated text is left out.** The `sangraha-s` packs are machine-translated (#212): hi 5,988,971, kn 5,217,346
  and te 4,781,160 tokens. No language meets the rating condition (`translation/quality_v1.md`, `agreement_v1.md`),
  so translated text is 0% until TSAI decides the translated languages at Gate 3.
- **Floor, then proportion.** Each language with a shard gets 0.3 points of the 8%. The other 5.6 points are shared in
  proportion to native tokens. A language with no shard gets nothing now, and its floor is added when it has a shard.

## Why a floor (proposed value, not derived from the data)

A split by tokens alone mostly counts packs, not languages. Each pack is one sample v0 part of 4.5 to 16.1 million
native tokens, so Hindi, with four native packs, would get 2.39 points and Tamil, with one, 0.30. The floor
keeps every language with clean text in every batch. This is the idea of Session 5's protected floors for scarce lanes,
applied here to each language (my extension). It also keeps a language in the mix when its cleaner rules come late.
The floor of 0.3 points (2.4 of the 8) is my value. With it, Hindi gets 1.97 points and Tamil 0.51.

## Romanised cap

The #400 rerun with the frozen tokenizer (#481) found 0 romanised documents in the 22 sample packs (10,076,158
tokens). The cap share is 0% in every language, and romanised segments inside native documents are 0.029% of tokens.
So the cap removes nothing in the sample. It is applied to the training corpus with `romanised/token_share.py`.

## What this means for the shards

- The three `sangraha-s` shards (`ind-hi-sangraha-s`, `ind-kn-sangraha-s`, `ind-te-sangraha-s`) are not part of the 8%
  until Gate 3 admits a translated language.
- If a translated language is admitted, Data B's proposal (`native_indic_share_v1.md`, option B) puts its translated
  text inside that language's share, at most 9% of it. TSAI has not decided this.

## When to rerun `share_split.py`

- when `ind-ml-fw2`, `ind-or-fw2` or `ind-ta-fw2` get a shard (task 1, cleaner rules). `ind-ta-sangraha-s` is
  translated and is left out either way;
- when the full-corpus shards replace the sample v0 shards;
- when TSAI changes the 8% or decides on translated text at Gate 3.

## Not known yet

- **Supply.** Session 5's check is share x run size <= supply (up to 4x supply means repeated data). The V5 run size is
  not decided, so the check cannot be made yet. The sample v0 parts are a sample, so they do not give the supply of a
  language either.
- Malayalam, Odia and Tamil `fw2` have no shard, so their native tokens are not measured with p1536 after cleaning.

## Files

- `share_split.py`: reads the shard manifests and writes `indic_share_v1.csv`. Standard library only.
- `indic_share_v1.csv`: the table above, written by `share_split.py`.

Command (shards downloaded from TSAI's list of 16 Nov):

```
python share_split.py --shards-dir shards --tokenizer-sha256 \
    e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b --total 8 --floor 0.3 --out indic_share_v1.csv
```
