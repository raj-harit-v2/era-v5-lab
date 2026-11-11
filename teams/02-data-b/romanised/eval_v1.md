# D2 detector on 100 labelled documents (v1)

Test set: `testset_100.csv`, 100 documents: 52 that a reader marked D2 and 48 that no reader marked D2 (half of those chosen among documents with at least 10% Latin letters).

Ground truth: the readers' labels (a document is D2 when at least one reader marked it D2). Next to them, the checked labels: 19 reader D2 marks were looked at again and hold no romanised Indic phrase (English text, or a proper name only); `checked_labels.csv` gives the reason for each, and they are listed at the end. No negative was changed.

Detector rule: at least 3 romanised Indic words, 2 of them different, or at least 5 IAST letters (see `detector.py`).

## Result

| labels | D2 docs | flagged | true pos | false pos | missed | precision | recall |
|---|---|---|---|---|---|---|---|
| readers' labels (ground truth) | 52 | 22 | 22 | 0 | 30 | 100% | 42% |
| checked labels | 33 | 22 | 21 | 1 | 12 | 95% | 64% |

## Gold check (false positives)

Gold documents are ones two readers marked clean, so none is D2 and every flag is a false positive. On all gold documents in `teams/02-data-b/gold/` (1957 in 17 packs) the detector flags **0**.

| pack | gold docs | flagged |
|---|---|---|
| ind-bn-fw2 | 244 | 0 |
| ind-bn-sangraha-v | 142 | 0 |
| ind-gu-fw2 | 80 | 0 |
| ind-hi-fw2 | 234 | 0 |
| ind-hi-hplt | 62 | 0 |
| ind-hi-indiccorp | 425 | 0 |
| ind-hi-sangraha-s | 24 | 0 |
| ind-kn-fw2 | 114 | 0 |
| ind-kn-sangraha-s | 27 | 0 |
| ind-kn-sangraha-v | 103 | 0 |
| ind-mr-fw2 | 142 | 0 |
| ind-mr-sangraha-v | 88 | 0 |
| ind-sa-fw2 | 71 | 0 |
| ind-ta-sangraha-v | 141 | 0 |
| ind-te-fw2 | 18 | 0 |
| ind-te-sangraha-s | 24 | 0 |
| ind-te-sangraha-v | 18 | 0 |

## Other thresholds

| min hits | min distinct | min IAST | flagged | precision (readers) | recall (readers) | precision (checked) | recall (checked) | gold flagged |
|---|---|---|---|---|---|---|---|---|
| 2 | 1 | 3 | 28 | 100% | 54% | 89% | 76% | 0 |
| 2 | 1 | 5 | 28 | 100% | 54% | 89% | 76% | 0 |
| 2 | 1 | 10 | 27 | 100% | 52% | 93% | 76% | 0 |
| 2 | 2 | 3 | 25 | 100% | 48% | 92% | 70% | 0 |
| 2 | 2 | 5 | 25 | 100% | 48% | 92% | 70% | 0 |
| 2 | 2 | 10 | 24 | 100% | 46% | 96% | 70% | 0 |
| 3 | 1 | 3 | 22 | 100% | 42% | 95% | 64% | 0 |
| 3 | 1 | 5 | 22 | 100% | 42% | 95% | 64% | 0 |
| 3 | 1 | 10 | 21 | 100% | 40% | 100% | 64% | 0 |
| 3 | 2 | 3 | 22 | 100% | 42% | 95% | 64% | 0 |
| 3 | 2 | 5 | 22 | 100% | 42% | 95% | 64% | 0 **(used)** |
| 3 | 2 | 10 | 21 | 100% | 40% | 100% | 64% | 0 |
| 4 | 1 | 3 | 20 | 100% | 38% | 95% | 58% | 0 |
| 4 | 1 | 5 | 20 | 100% | 38% | 95% | 58% | 0 |
| 4 | 1 | 10 | 19 | 100% | 37% | 100% | 58% | 0 |
| 4 | 2 | 3 | 20 | 100% | 38% | 95% | 58% | 0 |
| 4 | 2 | 5 | 20 | 100% | 38% | 95% | 58% | 0 |
| 4 | 2 | 10 | 19 | 100% | 37% | 100% | 58% | 0 |
| 5 | 1 | 3 | 16 | 100% | 31% | 94% | 45% | 0 |
| 5 | 1 | 5 | 16 | 100% | 31% | 94% | 45% | 0 |
| 5 | 1 | 10 | 15 | 100% | 29% | 100% | 45% | 0 |
| 5 | 2 | 3 | 16 | 100% | 31% | 94% | 45% | 0 |
| 5 | 2 | 5 | 16 | 100% | 31% | 94% | 45% | 0 |
| 5 | 2 | 10 | 15 | 100% | 29% | 100% | 45% | 0 |

## Missed (reader D2, not flagged): 30

18 of them are among the checked-label changes (a note is given).

| doc_id | pack | D2 marks / readers | Indic words (distinct) | IAST | words matched | checked note |
|---|---|---|---|---|---|---|
| 7e24bbd21ca4942b | ind-bn-sangraha-v | 1/2 | 1 (1) | 0 | rashifal | - |
| a3a0a3d543d77afe | ind-bn-sangraha-v | 1/2 | 0 (0) | 0 | - | only an English project name in brackets (Iceland Deep Drilling Project) |
| aecb9893b814c81f | ind-bn-sangraha-v | 1/2 | 0 (0) | 0 | - | only a film title and a person's name in brackets (Kakababur Protyaborton; Srijit Mukherjee) |
| 3776d34f591f896d | ind-hi-fw2 | 1/2 | 0 (0) | 0 | - | one romanised word used as a title (Paheliyan) |
| ee19639bfb2e22a0 | ind-hi-fw2 | 1/2 | 1 (1) | 0 | ki | only a film title (Satyaprem Ki Katha) and hashtags; the rest is English |
| 25f028264b1d21a1 | ind-hi-hplt | 2/4 | 2 (1) | 0 | ke | - |
| 27c3cc715e797fcf | ind-hi-hplt | 1/4 | 2 (2) | 0 | ek, ka | only titles of textbook lessons and books (Naya Raasta; Kavya Manjari); the rest is English footer |
| 2d3b04f109d069ec | ind-hi-hplt | 4/4 | 2 (2) | 0 | hai, kya | - |
| 3cf3a36bf10de245 | ind-hi-hplt | 1/4 | 1 (1) | 0 | bharti | - |
| 7143c8411c407518 | ind-hi-hplt | 1/4 | 0 (0) | 0 | - | one romanised word (Matka); the other Latin text is English headings |
| 7b6db4f0bb885a22 | ind-hi-hplt | 3/4 | 1 (1) | 0 | ka | - |
| 8298b653e0d7e1b6 | ind-hi-hplt | 1/4 | 1 (1) | 0 | yojana | only a scheme name (Rajasthan Free Tablet Yojana) |
| 8a6a9e11bf0f5d9f | ind-hi-hplt | 1/4 | 2 (1) | 0 | bharti | - |
| a42a9bf9f5e4dc0b | ind-hi-hplt | 1/4 | 1 (1) | 0 | bharti | - |
| c80b6ba958512284 | ind-hi-hplt | 2/4 | 0 (0) | 0 | - | - |
| e988773eff0ee985 | ind-hi-hplt | 1/4 | 2 (1) | 0 | yojana | only scheme and job names (PM e-Bus Sewa yojna; Mahila samman savings certificate) |
| ef3ed1ee60b1d6fd | ind-hi-hplt | 1/4 | 0 (0) | 0 | - | only a book title (Chanakya Niti); the rest is English |
| 4d9bf15a8b501e04 | ind-mr-fw2 | 1/3 | 0 (0) | 0 | - | only a newspaper name (Loksatta) |
| 6584bcd16dc3fdbf | ind-mr-fw2 | 1/3 | 0 (0) | 0 | - | English text |
| 8542df4ed14728c2 | ind-mr-fw2 | 1/3 | 0 (0) | 0 | - | English text and a newspaper name (Dainik Gomantak) |
| e6b4976ea98d0201 | ind-mr-fw2 | 1/3 | 0 (0) | 0 | - | - |
| 49ee950543dc49b6 | ind-sa-fw2 | 1/2 | 0 (0) | 0 | - | English site interface and a table of accented letters; no romanised Sanskrit text |
| 6a58a10566aca6d8 | ind-sa-fw2 | 1/2 | 0 (0) | 0 | - | only a title (Swasti Vachan); the reader's evidence is about ASCII dandas |
| 7bc67301a58f3aec | ind-sa-fw2 | 1/2 | 1 (1) | 0 | mere | - |
| adebf77350ddfac0 | ind-sa-fw2 | 1/2 | 0 (0) | 0 | - | English site interface and a table of accented letters; no romanised Sanskrit text |
| 128625bd74c59385 | ind-ta-fw2 | 1/1 | 0 (0) | 0 | - | English drug names (Paracetamol Tablet Uses in Tamil) |
| aabcbb5c1a89c890 | ind-ta-fw2 | 1/1 | 0 (0) | 0 | - | only a deity and mantra name in an English heading (Varahi amman mantharm in tamil) |
| fdf1699f0d8575a1 | ind-ta-fw2 | 1/1 | 0 (0) | 0 | - | English headings (How to apply child aadhar card in tamil) |
| 13de1d751434be22 | ind-ta-sangraha-v | 1/2 | 2 (2) | 0 | irrunga, unga | - |
| b54a137e794fc027 | ind-ta-sangraha-v | 1/2 | 1 (1) | 0 | ji | - |

## False alarms (flagged, no reader D2): 0

| doc_id | pack | D2 marks / readers | Indic words (distinct) | IAST | words matched | checked note |
|---|---|---|---|---|---|---|

## Reader D2 marks changed to 0 in the checked labels: 19

| doc_id | pack | D2 marks / readers | Indic words (distinct) | IAST | words matched | checked note |
|---|---|---|---|---|---|---|
| a3a0a3d543d77afe | ind-bn-sangraha-v | 1/2 | 0 (0) | 0 | - | only an English project name in brackets (Iceland Deep Drilling Project) |
| aecb9893b814c81f | ind-bn-sangraha-v | 1/2 | 0 (0) | 0 | - | only a film title and a person's name in brackets (Kakababur Protyaborton; Srijit Mukherjee) |
| 3776d34f591f896d | ind-hi-fw2 | 1/2 | 0 (0) | 0 | - | one romanised word used as a title (Paheliyan) |
| ee19639bfb2e22a0 | ind-hi-fw2 | 1/2 | 1 (1) | 0 | ki | only a film title (Satyaprem Ki Katha) and hashtags; the rest is English |
| 27c3cc715e797fcf | ind-hi-hplt | 1/4 | 2 (2) | 0 | ek, ka | only titles of textbook lessons and books (Naya Raasta; Kavya Manjari); the rest is English footer |
| 7143c8411c407518 | ind-hi-hplt | 1/4 | 0 (0) | 0 | - | one romanised word (Matka); the other Latin text is English headings |
| 8298b653e0d7e1b6 | ind-hi-hplt | 1/4 | 1 (1) | 0 | yojana | only a scheme name (Rajasthan Free Tablet Yojana) |
| e988773eff0ee985 | ind-hi-hplt | 1/4 | 2 (1) | 0 | yojana | only scheme and job names (PM e-Bus Sewa yojna; Mahila samman savings certificate) |
| ef3ed1ee60b1d6fd | ind-hi-hplt | 1/4 | 0 (0) | 0 | - | only a book title (Chanakya Niti); the rest is English |
| 4d9bf15a8b501e04 | ind-mr-fw2 | 1/3 | 0 (0) | 0 | - | only a newspaper name (Loksatta) |
| 6584bcd16dc3fdbf | ind-mr-fw2 | 1/3 | 0 (0) | 0 | - | English text |
| 8542df4ed14728c2 | ind-mr-fw2 | 1/3 | 0 (0) | 0 | - | English text and a newspaper name (Dainik Gomantak) |
| 49ee950543dc49b6 | ind-sa-fw2 | 1/2 | 0 (0) | 0 | - | English site interface and a table of accented letters; no romanised Sanskrit text |
| 6a58a10566aca6d8 | ind-sa-fw2 | 1/2 | 0 (0) | 0 | - | only a title (Swasti Vachan); the reader's evidence is about ASCII dandas |
| 8f8f2c783674d31f | ind-sa-fw2 | 1/2 | 0 (0) | 8 | - | romanised Arabic (Bismillahir Rahmanir Rahim); not an Indian language |
| adebf77350ddfac0 | ind-sa-fw2 | 1/2 | 0 (0) | 0 | - | English site interface and a table of accented letters; no romanised Sanskrit text |
| 128625bd74c59385 | ind-ta-fw2 | 1/1 | 0 (0) | 0 | - | English drug names (Paracetamol Tablet Uses in Tamil) |
| aabcbb5c1a89c890 | ind-ta-fw2 | 1/1 | 0 (0) | 0 | - | only a deity and mantra name in an English heading (Varahi amman mantharm in tamil) |
| fdf1699f0d8575a1 | ind-ta-fw2 | 1/1 | 0 (0) | 0 | - | English headings (How to apply child aadhar card in tamil) |
