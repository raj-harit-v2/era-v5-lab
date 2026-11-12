Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | arc_challenge | 500 | 51.4 | 49.6 | -1.8 (-4.0 to +0.4) | 21 / 12 | 0.163 |
| Q4_K_M | hellaswag | 400 | 64.0 | 63.7 | -0.2 (-2.1 to +1.6) | 8 / 7 | 1.000 |
| Q4_K_M | mmlu | 570 | 63.2 | 61.4 | -1.8 (-3.9 to +0.4) | 25 / 15 | 0.154 |
| Q4_K_M | gsm8k | 200 | 67.5 | 74.0 | +6.5 (+1.5 to +11.5) | 7 / 20 | 0.019 |
| Q4_K_M | truthfulqa_mc2 | 200 | 52.9 | 53.7 | +0.8 (-0.5 to +2.0) | - | - |
