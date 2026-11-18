Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | arc_challenge | 500 | 43.6 | 42.0 | -1.6 (-4.7 to +1.5) | 35 / 27 | 0.374 |
| Q4_K_M | hellaswag | 400 | 52.8 | 49.2 | -3.5 (-6.6 to -0.4) | 27 / 13 | 0.038 |
| Q4_K_M | mmlu | 570 | 59.1 | 60.0 | +0.9 (-2.1 to +3.8) | 34 / 39 | 0.640 |
| Q4_K_M | gsm8k | 200 | 66.0 | 62.0 | -4.0 (-9.7 to +1.7) | 21 / 13 | 0.229 |
| Q4_K_M | truthfulqa_mc2 | 200 | 47.9 | 41.5 | -6.4 (-9.6 to -3.2) | - | - |
