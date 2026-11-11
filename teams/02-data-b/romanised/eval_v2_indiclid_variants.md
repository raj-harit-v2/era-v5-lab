# IndicLID with length and score thresholds, against the word list

Contains level (at least one romanised segment). Precision / recall on `testset_100.csv`; gold flagged = false positives among the 1957 gold documents; packs flagged = documents flagged among all 11000 pack documents (readers marked about 52 as D2).

| tool | IndicLID input | min Latin words | min score | readers P / R | checked P / R | gold flagged | packs flagged |
|---|---|---|---|---|---|---|---|
| word list | - | - | - | 100% / 48% | 92% / 70% | 0 | 39 |
| IndicLID | whole segment | 1 | 0.0 | 76% / 56% | 58% / 67% | 9 | 578 |
| IndicLID | whole segment | 1 | 0.8 | 78% / 56% | 59% / 67% | 6 | 433 |
| IndicLID | whole segment | 1 | 0.9 | 81% / 50% | 66% / 64% | 3 | 352 |
| IndicLID | whole segment | 3 | 0.0 | 91% / 40% | 78% / 55% | 4 | 194 |
| IndicLID | whole segment | 3 | 0.8 | 95% / 40% | 82% / 55% | 3 | 135 |
| IndicLID | whole segment | 3 | 0.9 | 100% / 38% | 85% / 52% | 2 | 107 |
| IndicLID | whole segment | 4 | 0.0 | 89% / 31% | 83% / 45% | 2 | 112 |
| IndicLID | whole segment | 4 | 0.8 | 94% / 31% | 88% / 45% | 2 | 79 |
| IndicLID | whole segment | 4 | 0.9 | 100% / 29% | 93% / 42% | 1 | 62 |
| IndicLID | Latin words only | 1 | 0.0 | 66% / 79% | 44% / 82% | 73 | 2213 |
| IndicLID | Latin words only | 1 | 0.8 | 68% / 79% | 45% / 82% | 61 | 1953 |
| IndicLID | Latin words only | 1 | 0.9 | 67% / 73% | 44% / 76% | 51 | 1750 |
| IndicLID | Latin words only | 3 | 0.0 | 84% / 60% | 59% / 67% | 15 | 551 |
| IndicLID | Latin words only | 3 | 0.8 | 87% / 50% | 63% / 58% | 12 | 422 |
| IndicLID | Latin words only | 3 | 0.9 | 86% / 48% | 66% / 58% | 11 | 343 |
| IndicLID | Latin words only | 4 | 0.0 | 86% / 48% | 66% / 58% | 8 | 297 |
| IndicLID | Latin words only | 4 | 0.8 | 87% / 38% | 65% / 45% | 6 | 226 |
| IndicLID | Latin words only | 4 | 0.9 | 86% / 37% | 68% / 45% | 5 | 181 |
