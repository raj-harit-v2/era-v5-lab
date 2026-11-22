# Wide benchmark pass: scope (G12, week 4)

Gate 3 item 9 needs a benchmark large enough to **see** quantization drift on MoE and Indic models. The 200-item
stand-in and the 1,870-item eval_mini cannot. This page fixes what the wide pass runs and why.

## Why the current sets are too small

Items needed to detect a drop at 80% power and p < 0.01 (McNemar), from OLMoE's paired bf16 against Q4_K_M data
(`eval_mini/results/raw`), where the discordant rate is the share of items that flip:

| Task | Items now | Discordant | For a 2-point drop | For a 1-point drop |
|---|---:|---:|---:|---:|
| ARC-C | 500 | 3.8% | 1,110 | 4,440 |
| HellaSwag | 400 | 3.7% | 1,100 | 4,380 |
| MMLU | 570 | 7.5% | 2,200 | 8,810 |
| GSM8K | 200 | 10.0% | 2,920 | 11,680 |

Q3_K_M flips more items (MMLU 11.6%), so it needs more still. Method: n = (2.576 + 0.842)^2 * discordant / drop^2.

## What the wide pass runs

| Task | Items (full split) | Shots | Why |
|---|---:|---:|---|
| MMLU | 14,042 | 0 | English baseline; enough for 1 point |
| ARC-C | 1,172 | 0 | enough for 2 points |
| MILU Kannada | 6,234 | 5 | the language that drops most in #643/#646 |
| MILU Hindi, Telugu, Tamil, Bengali | 14,831 / 7,304 / 6,372 / 6,637 | 5 | Indic spread; shots as G9's eval_mini v0 |

GSM8K is left out: sarvam-1 answers about 3% at bf16, so there is no room to fall.

**Models:** sarvam-1 (Indic, 8k context) and Granite 3.0 3B-A800M MoE (`ibm-granite/granite-3.0-3b-a800m-base` @
`142d2c8e3f7f`, 40 experts top-8, English tasks only). The 1B-A400M Granite of #643 scored 27.1% on MMLU (1,140 items,
bf16, timing run), 2 points above the 25% chance line, so its items flip at random and MMLU cannot show its drift; the
3B-A800M is the same family and architecture (`granitemoe`). **Formats:** bf16, Q8_0, Q4_K_M, Q3_K_M. Q3_K_M is
included because that is where OLMoE's first benchmark loss appears. Every file keeps `output.weight` at Q8_0 and the
router at F32, as in the rest of G12.

## Method

`eval_wide/run_wide_gguf.py` runs each GGUF through the same in-process llama-cpp-python backend as `eval_mini`, and
`eval_wide/paired.py` compares each format with bf16 item by item (difference, 95% CI, McNemar). Same model revision,
seed, `n_ctx` and runner hash across formats; `summary.json` records them. Only task, doc_id, filter and metric are
stored per item (Team 9's firewall).

## Budget

Throughput is not measured yet. OLMoE took about 1 hour per 1,870 items on a Kaggle T4x2, so a full pass is several
hours per format. If a timing run says it does not fit, `--cap N` limits every task to its first N items (MMLU: N per
subject). The cap is recorded, and the same cap must be used for every format of a model. The Gate 4 evidence states
the item counts actually run.
