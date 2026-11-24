Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | mmlu | 14042 | 47.5 | 45.2 | -2.3 (-3.0 to -1.6) | 1448 / 1124 | 0.000 |
| Q4_K_M | arc_challenge | 1172 | 46.5 | 46.2 | -0.3 (-1.9 to +1.4) | 48 / 45 | 0.836 |
| Q8_0 | mmlu | 14042 | 47.5 | 47.4 | -0.0 (-0.4 to +0.3) | 326 / 320 | 0.844 |
| Q8_0 | arc_challenge | 1172 | 46.5 | 46.2 | -0.3 (-1.2 to +0.5) | 16 / 12 | 0.572 |
