Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | arc_challenge | 500 | 54.6 | 54.2 | -0.4 (-3.3 to +2.5) | 29 / 27 | 0.894 |
| Q4_K_M | hellaswag | 400 | 63.2 | 62.3 | -1.0 (-4.0 to +2.0) | 21 / 17 | 0.627 |
| Q4_K_M | mmlu | 570 | 72.1 | 69.6 | -2.5 (-4.9 to -0.0) | 32 / 18 | 0.065 |
| Q4_K_M | gsm8k | 200 | 87.0 | 74.0 | -13.0 (-18.9 to -7.1) | 33 / 7 | 0.000 |
| Q4_K_M | truthfulqa_mc2 | 200 | 60.3 | 60.0 | -0.3 (-3.8 to +3.3) | - | - |
