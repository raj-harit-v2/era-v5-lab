Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | arc_challenge | 500 | 53.2 | 51.8 | -1.4 (-3.8 to +1.0) | 22 / 15 | 0.324 |
| Q4_K_M | hellaswag | 400 | 58.0 | 56.5 | -1.5 (-3.9 to +0.9) | 15 / 9 | 0.307 |
| Q4_K_M | mmlu | 570 | 73.9 | 71.4 | -2.5 (-4.7 to -0.2) | 29 / 15 | 0.049 |
| Q4_K_M | gsm8k | 200 | 85.5 | 86.0 | +0.5 (-4.4 to +5.4) | 12 / 13 | 1.000 |
| Q4_K_M | truthfulqa_mc2 | 200 | 52.9 | 53.9 | +1.1 (-0.5 to +2.7) | - | - |
