| Measure | Base | After SFT | Change |
|---|---|---|---|
| Held-out bits per byte (G5 held-out v1, all) | 1.0981 | 1.1365 | +0.0384 |
| bits per byte, group val/groups/code_bpb | 0.7552 | 0.8035 | +0.0484 |
| bits per byte, group val/groups/english_bpb | 0.9952 | 1.0400 | +0.0448 |
| bits per byte, group val/groups/indic_mean_bpb | 1.1815 | 1.2138 | +0.0323 |
| bits per byte, group val/three_group_bpb | 0.9773 | 1.0191 | +0.0418 |
| arc_challenge acc_norm (n=500) | 0.2720 | 0.2740 | +0.0020 (stderr 0.0282) |
| hellaswag acc_norm (n=400) | 0.4325 | 0.4375 | +0.0050 (stderr 0.0351) |

Verdict: No forgetting beyond the limits.
Limits: bits per byte may rise by at most 0.05; a benchmark may fall by at most 2.0 x its combined stderr (and 0.01 absolute).
Held-out file sha256: 21c6e4b2df8dae9d69e254f4a00fc934d2a3c70f0675065a03724299d94312bb
