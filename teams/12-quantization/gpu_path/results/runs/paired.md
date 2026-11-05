Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| W4A16 | arc_challenge | 500 | 46.8 | 47.2 | +0.4 (-1.9 to +2.7) | 16 / 18 | 0.864 |
| W4A16 | hellaswag | 400 | 66.0 | 66.0 | +0.0 (-2.0 to +2.0) | 8 / 8 | 1.000 |
| W4A16 | mmlu | 570 | 53.9 | 51.2 | -2.6 (-5.2 to -0.1) | 35 / 20 | 0.058 |
| W4A16 | gsm8k | 200 | 11.5 | 10.5 | -1.0 (-5.2 to +3.2) | 10 / 8 | 0.815 |
| W4A16 | truthfulqa_mc2 | 200 | 37.2 | 36.6 | -0.6 (-1.7 to +0.4) | - | - |
