Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | arc_challenge | 500 | 43.4 | 42.6 | -0.8 (-3.3 to +1.7) | 22 / 18 | 0.636 |
| Q4_K_M | hellaswag | 400 | 59.5 | 58.8 | -0.8 (-2.9 to +1.4) | 11 / 8 | 0.648 |
| Q4_K_M | mmlu | 570 | 63.3 | 62.6 | -0.7 (-2.8 to +1.4) | 21 / 17 | 0.627 |
| Q4_K_M | gsm8k | 200 | 60.5 | 55.5 | -5.0 (-11.5 to +1.5) | 27 / 17 | 0.174 |
| Q4_K_M | truthfulqa_mc2 | 200 | 46.6 | 46.1 | -0.6 (-2.1 to +1.0) | - | - |
| Q5_K_M | arc_challenge | 500 | 43.4 | 44.4 | +1.0 (-1.2 to +3.2) | 13 / 18 | 0.473 |
| Q5_K_M | hellaswag | 400 | 59.5 | 58.2 | -1.2 (-2.5 to +0.0) | 6 / 1 | 0.125 |
| Q5_K_M | mmlu | 570 | 63.3 | 63.5 | +0.2 (-1.6 to +2.0) | 13 / 14 | 1.000 |
| Q5_K_M | gsm8k | 200 | 60.5 | 61.0 | +0.5 (-4.6 to +5.6) | 13 / 14 | 1.000 |
| Q5_K_M | truthfulqa_mc2 | 200 | 46.6 | 46.7 | +0.1 (-0.6 to +0.8) | - | - |
| Q6_K | arc_challenge | 500 | 43.4 | 44.4 | +1.0 (-0.3 to +2.3) | 3 / 8 | 0.227 |
| Q6_K | hellaswag | 400 | 59.5 | 58.2 | -1.2 (-2.3 to -0.2) | 5 / 0 | 0.062 |
| Q6_K | mmlu | 570 | 63.3 | 64.0 | +0.7 (-0.8 to +2.2) | 7 / 11 | 0.481 |
| Q6_K | gsm8k | 200 | 60.5 | 63.0 | +2.5 (-2.0 to +7.0) | 8 / 13 | 0.383 |
| Q6_K | truthfulqa_mc2 | 200 | 46.6 | 47.0 | +0.4 (-0.0 to +0.8) | - | - |
