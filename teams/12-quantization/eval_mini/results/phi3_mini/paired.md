Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | arc_challenge | 500 | 55.6 | 54.6 | -1.0 (-3.3 to +1.3) | 19 / 14 | 0.487 |
| Q4_K_M | hellaswag | 400 | 65.0 | 64.5 | -0.5 (-2.2 to +1.2) | 7 / 5 | 0.774 |
| Q4_K_M | mmlu | 570 | 71.4 | 69.5 | -1.9 (-4.0 to +0.2) | 24 / 13 | 0.099 |
| Q4_K_M | gsm8k | 200 | 77.5 | 74.5 | -3.0 (-8.7 to +2.7) | 20 / 14 | 0.392 |
| Q4_K_M | truthfulqa_mc2 | 200 | 55.2 | 57.0 | +1.8 (+0.5 to +3.1) | - | - |
