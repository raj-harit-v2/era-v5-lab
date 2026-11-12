Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | arc_challenge | 500 | 48.6 | 48.2 | -0.4 (-2.9 to +2.1) | 22 / 20 | 0.878 |
| Q4_K_M | hellaswag | 400 | 56.0 | 52.2 | -3.8 (-6.9 to -0.6) | 28 / 13 | 0.028 |
| Q4_K_M | mmlu | 570 | 61.2 | 60.0 | -1.2 (-4.2 to +1.7) | 41 / 34 | 0.489 |
| Q4_K_M | gsm8k | 200 | 58.5 | 44.5 | -14.0 (-20.8 to -7.2) | 40 / 12 | 0.000 |
| Q4_K_M | truthfulqa_mc2 | 200 | 49.8 | 55.5 | +5.7 (+1.7 to +9.6) | - | - |
