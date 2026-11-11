Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | arc_challenge | 500 | 48.6 | 48.0 | -0.6 (-2.8 to +1.6) | 17 / 14 | 0.720 |
| Q4_K_M | hellaswag | 400 | 61.0 | 60.8 | -0.2 (-2.4 to +1.9) | 10 / 9 | 1.000 |
| Q4_K_M | mmlu | 570 | 73.2 | 71.4 | -1.8 (-3.9 to +0.4) | 25 / 15 | 0.154 |
| Q4_K_M | gsm8k | 200 | 59.5 | 50.0 | -9.5 (-17.9 to -1.1) | 47 / 28 | 0.037 |
| Q4_K_M | truthfulqa_mc2 | 200 | 50.0 | 48.6 | -1.4 (-2.8 to -0.0) | - | - |
