Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | arc_challenge | 500 | 46.8 | 44.2 | -2.6 (-5.4 to +0.2) | 32 / 19 | 0.092 |
| Q4_K_M | hellaswag | 400 | 59.0 | 58.5 | -0.5 (-3.1 to +2.1) | 15 / 13 | 0.851 |
| Q4_K_M | mmlu | 570 | 60.9 | 57.2 | -3.7 (-6.5 to -0.9) | 44 / 23 | 0.014 |
| Q4_K_M | gsm8k | 200 | 71.5 | 76.5 | +5.0 (-1.2 to +11.2) | 15 / 25 | 0.154 |
| Q4_K_M | truthfulqa_mc2 | 200 | 54.3 | 51.7 | -2.6 (-4.9 to -0.3) | - | - |
