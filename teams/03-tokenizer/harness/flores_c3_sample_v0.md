# FLORES-200 fertility: C3 sample-v0 vs BrahmicTokenizer-131K

Run for PR #305. Candidate: C3 sample-v0 sha256 `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3` (#195).
Data: FLORES-200 from https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz (dev+devtest).

## Command

```bash
python teams/03-tokenizer/harness/run_harness.py \
  --tokenizers BrahmicTokenizer-131K \
  --brahmic-dir /path/to/BrahmicTokenizer-131K \
  --flores-dir /path/to/flores200_dataset \
  --candidate c3=/path/to/c3/tokenizer.json \
  --suites flores --check-reference
```

## Pass bar

| Check | C3 | Baseline | Δ | result |
|---|---|---|---|---|
| Indic mean | 2.3505 | 2.8355 | -17.10% | PASS |
| English | 1.2334 | 1.2352 | -0.15% | PASS |
| Baseline vs reference | | | max \|Δ\| = 0.0000 | PASS |

## Per-language fertility (tokens / word, lower is better)

| Tokenizer | En | Hi | Bn | Ta | Te | Kn | Ml | Mr | Gu | Pa | Or | As | Mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BrahmicTokenizer-131K | 1.2352 | 1.6429 | 2.3295 | 3.1166 | 3.0292 | 3.2734 | 3.4738 | 2.5723 | 2.2748 | 2.5955 | 4.1287 | 2.7535 | 2.8355 |
| c3 | 1.2334 | 1.6193 | 2.2293 | 2.5927 | 2.5531 | 2.7469 | 3.0324 | 2.0943 | 2.2092 | 2.0129 | 2.4861 | 2.2788 | 2.3505 |
| Δ% vs baseline | -0.15% | -1.44% | -4.30% | -16.81% | -15.72% | -16.08% | -12.71% | -18.58% | -2.88% | -22.45% | -39.78% | -17.24% | -17.10% |

Note: `--suites code` (HumanEval/MBPP/GSM8K) was not run here (Hugging Face SSL failure on this machine). Harini’s #276 already reports those for C3.
