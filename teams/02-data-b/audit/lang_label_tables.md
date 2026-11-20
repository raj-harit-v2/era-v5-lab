# Language-label check: tables
Made by `lang_label_check.py report` from the CSV files in this folder. Counts and IDs only. The findings and limits are in `lang_label_check.md`.

## 1. On what readers labelled (diagnosis packs)

| pack | labelled_docs | d1_docs | same_script_d1_docs | caught_mislabelled | caught_uncertain | non_d1_docs | non_d1_mislabelled | non_d1_uncertain | gold_docs | gold_mislabelled | gold_uncertain |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ind-hi-fw2 | 500 | 1 | 0 | 0 | 0 | 499 | 0 | 0 | 185 | 0 | 0 |
| ind-hi-hplt | 500 | 1 | 1 | 0 | 0 | 499 | 0 | 0 | 37 | 0 | 0 |
| ind-hi-indiccorp | 500 | 0 | 0 | 0 | 0 | 500 | 0 | 0 | 425 | 0 | 0 |
| ind-hi-sangraha-s | 500 | 0 | 0 | 0 | 0 | 500 | 0 | 0 | 24 | 0 | 0 |
| ind-hi-sangraha-v | 500 | 3 | 3 | 0 | 0 | 497 | 0 | 0 | 219 | 0 | 0 |
| ind-mr-fw2 | 500 | 0 | 0 | 0 | 0 | 500 | 0 | 0 | 158 | 0 | 0 |
| ind-mr-sangraha-v | 500 | 0 | 0 | 0 | 0 | 500 | 0 | 0 | 99 | 0 | 0 |
| ind-sa-fw2 | 500 | 6 | 1 | 0 | 0 | 494 | 0 | 0 | 71 | 0 | 0 |
| ind-bn-fw2 | 500 | 1 | 0 | 0 | 0 | 499 | 0 | 0 | 227 | 0 | 0 |
| ind-bn-sangraha-v | 500 | 1 | 1 | 0 | 0 | 499 | 0 | 0 | 145 | 0 | 0 |

### Documents readers marked D1 (same_script_d1 = 1 when at least 0.9 of the letters are in the pack's script)

| pack | doc_id | d1_readers | script_share | same_script_d1 | verdict | lid_label | vote_share | marker_lang | sign_letters |
|---|---|---|---|---|---|---|---|---|---|
| ind-hi-fw2 | b64bd6512a79ebbf | 1 | 0.8969 | 0 | agree | hin_Deva | 1.0 | hi |  |
| ind-hi-hplt | ea08837da929d92e | 4 | 1.0 | 1 | agree | hin_Deva | 1.0 | hi |  |
| ind-hi-sangraha-v | 086a0ded5e57ab37 | 1 | 1.0 | 1 | agree | hin_Deva | 0.6166 | hi | mr(ळ):1;sa(ऽ):1 |
| ind-hi-sangraha-v | 4456ad657bbe6741 | 1 | 1.0 | 1 | agree | hin_Deva | 0.675 | hi | vedic_accent(॑):9;vedic_accent(॒):9 |
| ind-hi-sangraha-v | e9d916f88e246a48 | 1 | 1.0 | 1 | agree | hin_Deva | 0.7591 | hi |  |
| ind-sa-fw2 | 03335864ad554e39 | 1 | 0.445 | 0 | other_script |  |  |  |  |
| ind-sa-fw2 | 1a70e9add5363d50 | 1 | 0.5007 | 0 | agree | san_Deva | 1.0 | sa | sa(ऽ):1 |
| ind-sa-fw2 | 7625ac472b005f22 | 1 | 0.9452 | 1 | agree | san_Deva | 0.7852 | unknown |  |
| ind-sa-fw2 | 7bc67301a58f3aec | 1 | 0.4938 | 0 | other_script |  |  |  |  |
| ind-sa-fw2 | b7d0ec485aed0bd6 | 1 | 0.8286 | 0 | agree | san_Deva | 0.8035 | unknown | sa(ऽ):2 |
| ind-sa-fw2 | ba33ff38890a9be3 | 1 | 0.5176 | 0 | agree | san_Deva | 1.0 | sa |  |
| ind-bn-fw2 | 3f0c89c1bc69537e | 2 | 0.4331 | 0 | other_script |  |  |  | bn(র):224 |
| ind-bn-sangraha-v | 7160f28b914f8629 | 1 | 1.0 | 1 | agree | ben_Beng | 0.9652 | unknown | as(ৰ):2;bn(র):53 |

## 2. CAP-1 packs (inputs of the p1536 shards)

| pack | docs_checked | short | other_script | judged | agree_pct | mislabelled | mislabelled_pct | mislabelled_as | uncertain | uncertain_pct | uncertain_lid_says | short_disagree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ind-hi-fw2 | 14393 | 0 | 80 | 14313 | 99.99 | 0 | 0.00 |  | 1 | 0.01 | sa:1 | 0 |
| ind-hi-hplt | 8840 | 0 | 19 | 8821 | 100.00 | 0 | 0.00 |  | 0 | 0.00 |  | 0 |
| ind-hi-indiccorp | 111930 | 2881 | 11 | 109038 | 98.99 | 0 | 0.00 |  | 30 | 0.03 | ne:11; other:brx_Deva:11; mr:3; other:kas_Deva:3; sa:2 | 1066 |
| ind-hi-sangraha-s | 8368 | 251 | 4 | 8113 | 97.93 | 0 | 0.00 |  | 23 | 0.28 | sa:16; ne:3; other:kas_Deva:3; other:brx_Deva:1 | 145 |
| ind-hi-sangraha-v | 14831 | 1 | 22 | 14808 | 99.72 | 0 | 0.00 |  | 41 | 0.28 | sa:39; other:doi_Deva:1; ne:1 | 0 |
| ind-mr-fw2 | 11555 | 0 | 13 | 11542 | 99.98 | 0 | 0.00 |  | 2 | 0.02 | hi:1; kok:1 | 0 |
| ind-mr-sangraha-v | 12299 | 3 | 5 | 12291 | 99.89 | 0 | 0.00 |  | 13 | 0.11 | hi:10; kok:2; sa:1 | 0 |
| ind-sa-fw2 | 5963 | 0 | 18 | 5945 | 100.00 | 0 | 0.00 |  | 0 | 0.00 |  | 0 |
| ind-bn-fw2 | 11317 | 0 | 38 | 11279 | 100.00 | 0 | 0.00 |  | 0 | 0.00 |  | 0 |
| ind-bn-sangraha-v | 10430 | 2 | 7 | 10421 | 99.94 | 2 | 0.02 | sa_Beng:2 | 4 | 0.04 | as:4 | 0 |

IndicLID-FTN labels (letter-weighted top label of each judged document):

| pack | lid_labels |
|---|---|
| ind-hi-fw2 | hin_Deva:14145; mai_Deva:158; brx_Deva:7; kas_Deva:2; san_Deva:1 |
| ind-hi-hplt | hin_Deva:8749; mai_Deva:71; brx_Deva:1 |
| ind-hi-indiccorp | hin_Deva:105719; mai_Deva:2040; brx_Deva:503; kas_Deva:408; doi_Deva:164; nep_Deva:95 |
| ind-hi-sangraha-s | hin_Deva:7896; san_Deva:110; mai_Deva:47; kas_Deva:24; mar_Deva:23; nep_Deva:10 |
| ind-hi-sangraha-v | hin_Deva:14492; mai_Deva:260; san_Deva:39; brx_Deva:14; doi_Deva:1; kas_Deva:1 |
| ind-mr-fw2 | mar_Deva:11540; hin_Deva:1; kok_Deva:1 |
| ind-mr-sangraha-v | mar_Deva:12278; mai_Deva:8; kok_Deva:2; hin_Deva:2; san_Deva:1 |
| ind-sa-fw2 | san_Deva:5945 |
| ind-bn-fw2 | ben_Beng:11279 |
| ind-bn-sangraha-v | ben_Beng:10415; asm_Beng:6 |

## 3. Filters that drop over 20%

Drop rates from `audit_v1.csv`. A filter's drops are at most its pack's drops, so a pack under the line has no filter over it.

| pack | lang | filter | docs_in | docs_dropped | drop_rate_pct | status | over_threshold |
|---|---|---|---|---|---|---|---|
| ind-bn-fw2 | bn | clean.py all rules (no per-filter counts) | 11205 | 501 | 4.47 | cleaned | 0 |
| ind-bn-sangraha-v | bn | clean.py all rules (no per-filter counts) | 10328 | 216 | 2.09 | cleaned | 0 |
| ind-gu-fw2 | gu | clean.py all rules (no per-filter counts) | 23118 | 429 | 1.86 | cleaned | 0 |
| ind-hi-fw2 | hi | clean.py all rules (no per-filter counts) | 14261 | 488 | 3.42 | cleaned | 0 |
| ind-hi-hplt | hi | clean.py all rules (no per-filter counts) | 8745 | 359 | 4.11 | cleaned | 0 |
| ind-hi-indiccorp | hi | clean.py all rules (no per-filter counts) | 110836 | 1168 | 1.05 | cleaned | 0 |
| ind-hi-sangraha-s | hi | clean.py all rules (no per-filter counts) | 8280 | 813 | 9.82 | cleaned | 0 |
| ind-hi-sangraha-v | hi | clean.py all rules (no per-filter counts) | 14709 | 226 | 1.54 | cleaned | 0 |
| ind-kn-fw2 | kn | clean.py all rules (no per-filter counts) | 7834 | 99 | 1.26 | cleaned | 0 |
| ind-kn-sangraha-s | kn | clean.py all rules (no per-filter counts) | 5191 | 6 | 0.12 | cleaned | 0 |
| ind-kn-sangraha-v | kn | clean.py all rules (no per-filter counts) | 8551 | 197 | 2.30 | cleaned | 0 |
| ind-ml-fw2 | ml | clean.py all rules (no per-filter counts) | 18976 | 18976 |  | no shard (not cleaned) | 0 |
| ind-mr-fw2 | mr | clean.py all rules (no per-filter counts) | 11460 | 210 | 1.83 | cleaned | 0 |
| ind-mr-sangraha-v | mr | clean.py all rules (no per-filter counts) | 12172 | 8 | 0.07 | cleaned | 0 |
| ind-or-fw2 | or | clean.py all rules (no per-filter counts) | 33684 | 33684 |  | no shard (not cleaned) | 0 |
| ind-sa-fw2 | sa | clean.py all rules (no per-filter counts) | 5908 | 241 | 4.08 | cleaned | 0 |
| ind-ta-fw2 | ta | clean.py all rules (no per-filter counts) | 6766 | 6766 |  | no shard (not cleaned) | 0 |
| ind-ta-sangraha-s | ta | clean.py all rules (no per-filter counts) | 4336 | 4336 |  | no shard (not cleaned) | 0 |
| ind-ta-sangraha-v | ta | clean.py all rules (no per-filter counts) | 6796 | 1 | 0.01 | cleaned | 0 |
| ind-te-fw2 | te | clean.py all rules (no per-filter counts) | 5997 | 327 | 5.45 | cleaned | 0 |
| ind-te-sangraha-s | te | clean.py all rules (no per-filter counts) | 4782 | 363 | 7.59 | cleaned | 0 |
| ind-te-sangraha-v | te | clean.py all rules (no per-filter counts) | 8609 | 16 | 0.19 | cleaned | 0 |

0 of 22 rows are over the line.
