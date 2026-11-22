Paired against **bf16** on the same items. Differences in points (format minus base); b = right in base, wrong in format; c = the reverse.

| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|---|---|---|
| Q4_K_M | mmlu | 114 | 49.1 | 49.1 | +0.0 (-7.3 to +7.3) | 9 / 9 | 1.000 |
| Q4_K_M | arc_challenge | 2 | 100.0 | 100.0 | +0.0 (+0.0 to +0.0) | 0 / 0 | 1.000 |
| Q4_K_M | milu_Kannada | 2 | 0.0 | 0.0 | +0.0 (+0.0 to +0.0) | 0 / 0 | 1.000 |
| Q4_K_M | milu_Hindi | 2 | 100.0 | 50.0 | -50.0 (-119.3 to +19.3) | 1 / 0 | 1.000 |
| Q4_K_M | milu_Telugu | 2 | 50.0 | 50.0 | +0.0 (+0.0 to +0.0) | 0 / 0 | 1.000 |
| Q4_K_M | milu_Tamil | 2 | 50.0 | 100.0 | +50.0 (-19.3 to +119.3) | 0 / 1 | 1.000 |
| Q4_K_M | milu_Bengali | 2 | 0.0 | 50.0 | +50.0 (-19.3 to +119.3) | 0 / 1 | 1.000 |
