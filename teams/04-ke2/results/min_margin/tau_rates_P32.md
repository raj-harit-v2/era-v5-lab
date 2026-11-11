10,000 query tokens (seed 0), P = 32, raw byte table of 131,072 codes. Proposed tau = **0.3**.

| condition | mean cos to true code | argmax accuracy | structural (Theorem 2) accuracy | tau 0.0: accept / acc. among accepted / wrong-accept | tau 0.3: accept / acc. among accepted / wrong-accept | tau 0.5: accept / acc. among accepted / wrong-accept | tau 0.7: accept / acc. among accepted / wrong-accept | tau 0.9: accept / acc. among accepted / wrong-accept |
|---|---|---|---|---|---|---|---|---|
| clean_fp32 | 1.000 | 1.0000 | 1.0000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 |
| clean_bf16 | 1.000 | 1.0000 | 1.0000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 |
| noise_cos_0.95 | 0.950 | 1.0000 | 1.0000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 |
| noise_cos_0.9 | 0.900 | 1.0000 | 1.0000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 0.500 / 1.000 / 0.000 |
| noise_cos_0.8 | 0.800 | 1.0000 | 1.0000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 0.000 / - / 0.000 |
| noise_cos_0.7 | 0.700 | 1.0000 | 1.0000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 0.505 / 1.000 / 0.000 | 0.000 / - / 0.000 |
| noise_cos_0.5 | 0.500 | 1.0000 | 0.9857 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 0.501 / 1.000 / 0.000 | 0.000 / - / 0.000 | 0.000 / - / 0.000 |
| noise_cos_0.3 | 0.300 | 1.0000 | 0.0000 | 1.000 / 1.000 / 0.000 | 0.508 / 1.000 / 0.000 | 0.000 / - / 0.000 | 0.000 / - / 0.000 | 0.000 / - / 0.000 |
| garbage | - | 0.0000 | - | 1.000 / 0.000 / 1.000 | 0.000 / - / 0.000 | 0.000 / - / 0.000 | 0.000 / - / 0.000 | 0.000 / - / 0.000 |
| rival_mix_0.3 | 0.988 | 1.0000 | 0.4946 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 |
| rival_mix_0.45 | 0.971 | 1.0000 | 0.4420 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | 0.999 / 1.000 / 0.000 |
| rival_mix_0.55 | 0.957 | 0.0000 | 0.4405 | 1.000 / 0.000 / 1.000 | 1.000 / 0.000 / 1.000 | 1.000 / 0.000 / 1.000 | 1.000 / 0.000 / 1.000 | 0.999 / 0.000 / 0.999 |
| rival_mix_0.7 | 0.930 | 0.0000 | 0.4182 | 1.000 / 0.000 / 1.000 | 1.000 / 0.000 / 1.000 | 1.000 / 0.000 / 1.000 | 1.000 / 0.000 / 1.000 | 1.000 / 0.000 / 1.000 |

Rule: tau is the smallest value in the grid that accepts at most 1% of `garbage` queries while keeping at least 99% of the correct decodes in every isotropic condition with target cosine >= 0.7 (`noise_cos_0.95`, `noise_cos_0.9`, `noise_cos_0.8`, `noise_cos_0.7`); if no tau satisfies both, the smallest that rejects garbage is returned and the quality floor is reported as not met; if none rejects garbage, the largest tau in the grid.

tau is a garbage filter: it rejects vectors far from every code; it cannot separate a near-code wrong answer from a right one (best cosine above 0.77 in every rival_mix condition). Wrong-accept rate at tau = 0.3 by condition (the confusions tau does not catch): rival_mix_0.3: 0.000, rival_mix_0.45: 0.000, rival_mix_0.55: 1.000, rival_mix_0.7: 1.000. The margin (best minus second-best cosine) is the quantity that detects rival confusions, and Team 5's decoder should report both.
