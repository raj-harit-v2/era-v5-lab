Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | arc_challenge | 500 | 52.0 | 51.6 | -0.4 (-2.4 to +1.6) | 14 / 12 | 0.845 |
| Q4_K_M | hellaswag | 400 | 55.5 | 55.5 | +0.0 (-2.1 to +2.1) | 9 / 9 | 1.000 |
| Q4_K_M | mmlu | 570 | 73.2 | 72.5 | -0.7 (-3.0 to +1.6) | 24 / 20 | 0.652 |
| Q4_K_M | gsm8k | 200 | 68.0 | 66.0 | -2.0 (-9.1 to +5.1) | 28 / 24 | 0.678 |
| Q4_K_M | truthfulqa_mc2 | 200 | 55.4 | 54.4 | -1.0 (-2.7 to +0.7) | - | - |
