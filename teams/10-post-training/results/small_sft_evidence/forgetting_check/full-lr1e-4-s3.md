| Measure | Base | After SFT | Change |
|---|---|---|---|
| Held-out bits per byte (G5 held-out v1, all) | 1.0981 | 1.1488 | +0.0507 (at the limit) |
| bits per byte, group val/groups/code_bpb | 0.7552 | 0.8369 | +0.0817 |
| bits per byte, group val/groups/english_bpb | 0.9952 | 1.0479 | +0.0527 |
| bits per byte, group val/groups/indic_mean_bpb | 1.1815 | 1.2243 | +0.0428 |
| bits per byte, group val/three_group_bpb | 0.9773 | 1.0364 | +0.0591 |
| arc_challenge acc_norm (n=500) | 0.2720 | 0.2840 | +0.0120 (stderr 0.0284) |
| hellaswag acc_norm (n=400) | 0.4325 | 0.4350 | +0.0025 (stderr 0.0351) |

Verdict: FORGETTING: held-out bits per byte rose by +0.0507 (limit 0.05)
Limits: bits per byte may rise by at most 0.05; a benchmark may fall by at most 2.0 x its combined stderr (and 0.01 absolute).
Held-out file sha256: 21c6e4b2df8dae9d69e254f4a00fc934d2a3c70f0675065a03724299d94312bb
At the limit (within 0.01 of it, either side; the verdict is a close call, read the numbers): bits per byte.
