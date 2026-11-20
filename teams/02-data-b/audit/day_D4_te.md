# Telugu reader audit — 18 November 2026

Reader: Jeevan (oddjoker91)
Issue: #527
Source: Issue #527 · TSAI 16 Nov p1536 shards · Random(4) · 25 fw2 + 25 sangraha-v

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| fab5d5dde67ea6b9 | ind-te-fw2-train-000000 | ok |  |  | C6 summary: At offsets 417, 521, and 849. - Standardize pause punctuation or ellipses (“..”)  |
| 8a73eb6aa6810afc | ind-te-fw2-train-000000 | finding | D4 | 807 | D4 summary: At offsets 807, 1185, 1286, 1420, 1683, 1994, 2056, 2239, 2537, 2610, 2711, 2873, 3117, 3315, 3558, 3645, and 3803 - Bad machine translation appears in 17 places, causing incorrect meanings, broken sentences, and confusing cricket descriptions. |
| a5958f84af8dae22 | ind-te-fw2-train-000000 | finding | D4 | 872 | D4 summary: At offsets 872, 1048, and 2227 - Bad machine translation appears in 3 places, causing broken grammar, unclear anti-ageing advice, and an incorrect translation of "grime" as "గజ్జ" (itch). |
| 153285e2e7adbd34 | ind-te-fw2-train-000000 | finding | C1 | 5389 | C1 summary: At offset 5389 - Site navigation categories are left after the lunch-box article. C6 summary: standardize pause punctuation or ellipses (“...” at offsets 239, 405, 519, 695, 802, 996, 1080, 1132, 1221, 1261, 1899, 2192, 2220, 2822, 4295, 4373, 4526, and 5001, “..” at offsets 3577 and 5371). |
| 4f377b8c28b09590 | ind-te-fw2-train-000000 | ok |  |  |  |
| 94b6adae3ce872a2 | ind-te-fw2-train-000000 | finding | C1 | 0 | C1 summary: At offsets 0 and 2400 - Unrelated article links appear before the main story, and the article refers to a slideshow that is missing from the text. C6 summary: standardize pause punctuation or ellipses (“..” at offsets 41, 184, 208, 320, 339, 394, 485, 1885, 2416, 2431, 2802, 2857, 2891, and 5395, “...” at offsets 105, 954, 2250, 2333, 2451, 2471, 3139, 3449, 3668, 3983, 4331, 4619, 4916, 5300, and 5309, “....” at offset 881, “.....” at offset 5851). |
| dc37923ec8efe6da | ind-te-fw2-train-000000 | ok |  |  | C6 summary: standardize pause punctuation or ellipses (“…” at offset 2321, “..” at offsets 2328 and 2353). |
| 476ebc3ae4e21d16 | ind-te-fw2-train-000000 | finding | B4 | 2807 | B4 summary: At offset 2807 - A `<PHONE>` placeholder appears after the author's name because the original phone number was redacted. C6 summary: At offset 2484 - standardize pause punctuation (“..”) |
| 2e80a0142cf0918e | ind-te-fw2-train-000000 | ok |  |  | C6 summary: Standardize pause punctuation or ellipses (“..” at offsets 563, 650, 679, 687, 928, and 936, “…” at offsets 741 and 782) |
| 0ed57d6658a51ed0 | ind-te-fw2-train-000000 | finding | C1 | 1408 | C1 summary: At offsets 1408, 2433, and 2495 - An unrelated headline interrupts the article, and news-site promotions and category links appear at the end. C6 summary: At offsets 90, 201, 1425, 1491, 1679, 1697, 1717, 1822, and 2324 - Standardize pause punctuation or ellipses (“..”) |
| 6330519780b7aa36 | ind-te-fw2-train-000000 | finding | A3 | 2353 | A3 summary: At offsets 2353 and 7553 - A stray Latin character (Å) appears inside a Telugu word, and an unwanted symbol (‡) appears after a seat category. C6 summary: At offsets 315 and 5996 (“..”), and 1813, 3055, and 3979 (“...”) - Standardize pause punctuation or ellipses. |
| 47f871f9e869f3d8 | ind-te-fw2-train-000000 | finding | C1 | 662 | C1 summary: At offset 662 - An English app advertisement appears after the article. B4 summary: At offset 741 - A leftover YouTube video embed tag appears at the end of the article. |
| 7ce18abfa9c69925 | ind-te-fw2-train-000000 | finding | D4 | 42 | D4 summary: At offsets 42, 333, 647, and 886 - Bad machine translation makes the enamel pin descriptions confusing, mixes unrelated phrases, and incorrectly translates "hanging" as execution by hanging. C1 summary: At offset 943 - Product tab and menu labels are joined together into a meaningless line. |
| 0d09d4224ede9b6b | ind-te-fw2-train-000000 | ok |  |  |  |
| cec6c45042d50bda | ind-te-fw2-train-000000 | ok |  |  | C6 summary: standardize pause punctuation or ellipses (“...”) at offsets 690, 1193, 1279, 1403, and 1548. |
| c7a54a063e9947ce | ind-te-fw2-train-000000 | ok |  |  | C6 summary: standardize pause punctuation or ellipses (“..”) at offsets 381, 388, and 872. |
| a08e03399539c434 | ind-te-fw2-train-000000 | finding | C1 | 0 | C1 summary: At offset 0 - Unrelated news headlines appear before the main article. D1 summary: At offset 1680 - An English Instagram caption interrupts the Telugu article. B4 summary: At offset 1959 - An incomplete Instagram embed line remains in the article. C6 summary: standardize pause punctuation or ellipses (“..”) at offsets 133, 184, 453, 1435, 1744, 1820, and 2044. |
| f59b120ab1a2e489 | ind-te-fw2-train-000000 | finding | C4 | 1415 | C4 summary: At offset 1415 - An unrelated article about actor Gopichand starts in the middle of the Radhika Apte story. C1 summary: At offset 1833 - Unrelated article links appear at the end of the story. C6 summary: standardize pause punctuation or ellipses (“..” at offsets 80, 105, 172, 278, 760, 1229, 1864, 1977, and 2564, “...” at offsets 1446, 2130, 2256, and 2343, “......” at offset 2081, “....” at offset 2216). |
| df42ebcb389501e6 | ind-te-fw2-train-000000 | finding | D4 | 89 | D4 summary: At offsets 89, 571, 700, 900, 1037, 1280, 1472, 1695, 2097, 2481, 2645, and 3139 - Bad machine translation appears in 12 places, causing broken grammar, incorrect meanings, confusing descriptions of straw hats, and unclear instructions about hat styles and fitting. |
| 8a7eaf8a1412fd68 | ind-te-fw2-train-000000 | ok |  |  | C6 summary: At offset 27 - Standardize pause punctuation or ellipses (“..”). |
| f70e8ed9dba39ac0 | ind-te-fw2-train-000000 | ok |  |  | C6 summary: standardize pause punctuation or ellipses (“..”) at offsets 1013 and 1502. |
| 384dd45efa1911d5 | ind-te-fw2-train-000000 | ok |  |  | C6 summary: standardize pause punctuation or ellipses (“..” at offsets 385, 583, 1547, 2262, 2319, and 2337, “…..” at offsets 707 and 1955, “……” at offset 1389). |
| 694770ec83673a12 | ind-te-fw2-train-000000 | ok |  |  | C6 summary: standardize pause punctuation or ellipses (“…” at offset 577, “..” at offset 934). |
| 59f8801218e49ffb | ind-te-fw2-train-000000 | finding | C1 | 0 | C1 summary: At offsets 0, 21, and 58 - Author details, publication date, and an image caption appear before the main article. |
| 08dc9def41ac6446 | ind-te-fw2-train-000000 | finding | C1 | 504 | C1 summary: At offsets 504, 1088, 1635, 2144, and 2667 - Unrelated "Read Also" news links interrupt the article and appear at the end. G3 summary: At offset 1352 - A broken sentence leaves a phrase without clear meaning before the father's quote. C6 summary: standardize pause punctuation or ellipses (“..” at offsets 57, 581, 609, 899, 935, 1220, 1265, 1700, 1744, 1807, 1870, 1960, 2004, 2067, 2180, 2392, 2504, 2619, and 2698, “…” at offset 552, “...” at offset 1132). |
| 606617882c752c2d | ind-te-sangraha-v-train-000000 | ok |  |  |  |
| 84626d9f75147b0d | ind-te-sangraha-v-train-000000 | finding | G1 | 1533 | G1 summary: At offset 1533 - A name starts with a broken Telugu character, making it unreadable. C3 summary: At offset 5108 - The story ends abruptly after a phone greeting, suggesting that the remaining text is missing. C6 summary: standardize pause punctuation or ellipses (“. .”) at offsets 488, 1165, and 3165. |
| 877d099280b0963a | ind-te-sangraha-v-train-000000 | finding | C3 | 847 | C3 summary: At offset 847 - The sentence ends in the middle of a word and suddenly switches to a new topic, suggesting missing text. C6 summary: At offset 636 - Standardize pause punctuation or ellipses (“..”). |
| a6ff849009cf79d5 | ind-te-sangraha-v-train-000000 | ok |  |  | C6 summary: standardize pause punctuation or ellipses (“. .”) at offsets 488 and 634. |
| 9c37e12adc4dfa7a | ind-te-sangraha-v-train-000000 | ok |  |  | C6 summary: standardize pause punctuation or ellipses (“. .”) at offsets 189 and 394. |
| 02fe0ed1ba74bb94 | ind-te-sangraha-v-train-000000 | ok |  |  |  |
| b318fe11242b32e7 | ind-te-sangraha-v-train-000000 | finding | C3 | 5378 | C3 summary: At offset 5378 - The document ends with a heading about another problem in the education system, but the following content is missing. C6 summary: standardize pause punctuation or ellipses (“...”) at offsets 1520 and 4694. |
| 73c1decf96634ede | ind-te-sangraha-v-train-000000 | ok |  |  | C6 summary: standardize pause punctuation or ellipses (“. .”) at offsets 416, 517, 596, 651, 756, 1101, 1175, 1270, 1315, and 1367. |
| 8857c8469fd63ca3 | ind-te-sangraha-v-train-000000 | finding | C1 | 0 | C1 summary: At offset 0 - The headline is repeated as the first sentence of the article. |
| 24f01326d7d6976e | ind-te-sangraha-v-train-000000 | finding | G1 | 505 | G1 summary: At offsets 505 and 979 - extra space inside a telugu word. present in the original  before cleaning C3 summary: At offset 1233 - The paragraph ends abruptly after mentioning Kshemendra, with the remaining text missing. |
| b3c65b5c1cc1bd73 | ind-te-sangraha-v-train-000000 | ok |  |  | C6 summary: At offset 420 - Standardize pause punctuation or ellipses (“...”). |
| 11f3ca4e627c5177 | ind-te-sangraha-v-train-000000 | finding | G1 | 736 | G1 summary: At offset 736 - An unwanted space splits the word “కొనియాడారు” into two parts. |
| b73ec9aa75575e33 | ind-te-sangraha-v-train-000000 | ok |  |  | C6 summary: At offset 1144 - Standardize pause punctuation or ellipses (“. .”). |
| 318c09f41a3309b0 | ind-te-sangraha-v-train-000000 | finding | G1 | 266 | G1 summary: At offsets 266 and 1939 - extra space inside a telugu word. present in the original before cleaning C3 summary: At offset 2314 - The document ends in the middle of a sentence, with the remaining text missing. |
| 85c371eab86e00d1 | ind-te-sangraha-v-train-000000 | ok |  |  |  |
| b23ac5e37e0db14b | ind-te-sangraha-v-train-000000 | finding | C1 | 0 | C1 summary: At offsets 0, 468, 965, 1401, and 1901 - Unrelated news headlines and site navigation links appear before and throughout the article. G3 summary: At offset 755 - A missing word makes the sentence about Niharika's wedding incomplete. C6 summary: standardize pause punctuation or ellipses (“..” at offsets 122, 175, 239, 344, 368, 521, 600, 1015, 1085, 1225, and 1473, “...” at offsets 438, 895, 987, 1448, 1638, 1966, 2405, 2482, and 2581). |
| 3b8292a2ff76207c | ind-te-sangraha-v-train-000000 | ok |  |  |  |
| 1ce3984fa36503d5 | ind-te-sangraha-v-train-000000 | ok |  |  |  |
| cd90441ae93698d9 | ind-te-sangraha-v-train-000000 | ok |  |  | C6 summary: At offset 100 - Standardize pause punctuation or ellipses (“. . .”). |
| 121972abe90438b1 | ind-te-sangraha-v-train-000000 | finding | C1 | 1606 | C1 summary: At offsets 1606, 1654, and 1727 - Three unrelated article links appear at the end of the main article. C6 summary: standardize pause punctuation or ellipses (“. .” at offsets 1647, 1669, 1720, and 1794, “...” at offset 1747). |
| 2e19392605f8a30f | ind-te-sangraha-v-train-000000 | finding | C3 | 1948 | C3 summary: At offset 1948 - The poem ends abruptly in the middle of a word, with the remaining text missing. |
| bc769bc8a85a8140 | ind-te-sangraha-v-train-000000 | finding | C1 | 981 | C1 summary: At offset 981 - A website advertising disclaimer appears at the end of the article. C6 summary: At offset 833 - Standardize pause punctuation or ellipses (“. .”). |
| 8b795f4012f73b8f | ind-te-sangraha-v-train-000000 | finding | A3 | 32 | A3 summary: At offsets 32, 169, 217, and 432 - Broken words and incorrect characters make parts of the article about actors, films, and performances difficult to understand. |
| ab9fe3bc8182b406 | ind-te-sangraha-v-train-000000 | finding | C1 | 2115 | C1 summary: At offset 2115 - An unrelated "Read Also" link appears at the end of the article. C6 summary: At offsets 55, 425, 1034, 2164, and 2186 - Standardize pause punctuation or ellipses (“..”). |
| 7e6149c4dce6f995 | ind-te-sangraha-v-train-000000 | ok |  |  | C6 summary: At offsets 27, 1020, and 1719 (“. . .”), and 96, 402, 471, 592, 630, and 1624 (“. .”) - Standardize pause punctuation or ellipses. |

Documents read: 50/50
OK: 23
Documents with a finding: 27
Codes found: D4, C1, B4, A3, C4, G1, C3
Cleaning-introduced findings: 1 (B4, the phone-redaction placeholder)
G1 findings already present in the original: 4
C1 boilerplate findings remaining after cleaning: 12

Only reviewed rows are exported. Full document text and private backups must stay out of Git.
