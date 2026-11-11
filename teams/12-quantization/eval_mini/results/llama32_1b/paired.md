Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | arc_challenge | 500 | 35.4 | 37.0 | +1.6 (-0.9 to +4.1) | 16 / 24 | 0.268 |
| Q4_K_M | hellaswag | 400 | 55.8 | 54.5 | -1.2 (-2.9 to +0.4) | 8 / 3 | 0.227 |
| Q4_K_M | mmlu | 570 | 48.1 | 47.9 | -0.2 (-2.7 to +2.3) | 27 / 26 | 1.000 |
| Q4_K_M | gsm8k | 200 | 30.5 | 26.5 | -4.0 (-9.7 to +1.7) | 21 / 13 | 0.229 |
| Q4_K_M | truthfulqa_mc2 | 200 | 43.8 | 44.4 | +0.5 (-0.6 to +1.7) | - | - |
