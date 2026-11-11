# Status of every Indic medicine

373 medicines in 22 packs, from the open diagnosis PRs that add `diagnosis/submissions/ind-*/*/medicine.md` (listed 2 Nov 2026; PRs #177 and #256 added 5 Nov). PR #176 is the same branch and commit as #71, so it is counted once.

TSAI (G2, 1 Nov): a rule stays out of spec v1 if, on Wed 4 Nov at 23:59 IST, its harm result is missing or was run on a set other than its own pack's gold. TSAI (#240, 4 Nov 17:47 IST): only a result on today's gold counts; a rule without one is not rejected, it waits for the next spec. The groups below are read from each author's own harm text, or from a re-run on today's gold where one exists; an author who thinks their rule is in the wrong group can say so in this PR.

| group | medicines |
|---|---|
| ready: passes on its own pack's gold set, at today's size | 243 |
| gold set empty, not testable | 27 |
| ready: Data B's rewrite, OK'd by the author | 17 |
| flag only: a note, not a rule (TSAI ruling 4) | 16 |
| no **Disease:** line and no python block (the harm tool cannot read it) | 14 |
| rewrite by Data B passes on today's gold; waiting for the author's OK in their PR | 14 |
| in words only: no **Disease:** line and no python block (the harm tool cannot read it) | 10 |
| needs a reviewer's input (for example a list of verified fixes), so it cannot run on a document alone | 6 |
| rewrite by Data B: needs lists from the whole pack or the metadata, so it cannot run on a document alone | 5 |
| held: its only job is to turn a visarga used as a colon into ':'; TSAI (#240 review, 5 Nov): a visarga used as a colon is clean, in every script, so the rule waits for the next spec | 4 |
| held: adds a ZWJ by design; for spec v1 the Gate 2 joiner check stays, so it waits for v2 (TSAI, G2 4 Nov 14:20 IST) | 3 |
| held: it turns ':' into a visarga (Sanskrit); TSAI (#240, 5 Nov): in spec v1 no rule converts between a visarga and a colon, in either direction, so the rule waits for the next spec (a colon-to-visarga fix in Sanskrit can come back with its own harm test) | 2 |
| not a rule: the author keeps D3 as a candidate (`_candidate_d3`), with no rule in code | 1 |
| not a rule: the author's sheet says "Medicine: none"; cure_d3 was a tested candidate she rejected | 1 |
| rewrite by Data B fails on today's gold set of its pack | 1 |
| held for spec v2: adds a ZWJ by design, and for v1 the Gate 2 joiner check stays (TSAI, G2 4 Nov) | 1 |
| fails on today's gold set of its pack (re-run on 3 to 5 Nov) | 1 |
| rule in code that takes the document (it needs the URL), kept outside a python block because harm_test_indic.py passes only the text; gold set empty, not testable | 1 |
| held: untested: it needs the Itihasa test sentences (ITIHASA_TEST_SN), benchmark text that the eval firewall rule keeps out of the repo (G 4 Nov 12:19 IST); waits for the next spec | 1 |
| not a rule: the author's G2 fixes the extraction step, not the text, so it has no rule in code | 1 |
| held: untested: it needs the FLORES-200 / IN22 / Itihasa benchmark files, so its gold run cannot fire; waits for the next spec (TSAI, G2 5 Nov 08:32 IST) | 1 |
| held: its only job is to turn ஃ into ':' (Unicode names ஃ the Tamil visarga); TSAI (#240, 5 Nov): in spec v1 no rule converts between a visarga and a colon, in either direction, so the rule waits for the next spec | 1 |
| held: C6 is a new code; TSAI (G2 5 Nov) puts it in spec v1 once the code owner approves #177 after the label fixes | 1 |
| held: D3 is a label only (TSAI, 31 Oct); the code-owner review asks to move it to a candidate for spec v2 | 1 |

## Per pack

| pack | gold docs today (main `ea7b533`) | ready | not ready yet | no python block |
|---|---|---|---|---|
| ind-bn-fw2 | 244 | 23 | 4 | 0 |
| ind-bn-sangraha-v | 142 | 13 | 10 | 0 |
| ind-gu-fw2 | 80 | 20 | 0 | 0 |
| ind-hi-fw2 | 234 | 14 | 0 | 0 |
| ind-hi-hplt | 62 | 33 | 16 | 0 |
| ind-hi-indiccorp | 425 | 6 | 1 | 0 |
| ind-hi-sangraha-s | 24 | 9 | 1 | 0 |
| ind-hi-sangraha-v | 0 | 0 | 8 | 0 |
| ind-kn-fw2 | 114 | 7 | 2 | 0 |
| ind-kn-sangraha-s | 27 | 12 | 1 | 0 |
| ind-kn-sangraha-v | 103 | 15 | 1 | 0 |
| ind-ml-fw2 | 0 | 0 | 3 | 0 |
| ind-mr-fw2 | 142 | 20 | 8 | 0 |
| ind-mr-sangraha-v | 88 | 13 | 7 | 0 |
| ind-or-fw2 | 0 | 0 | 11 | 0 |
| ind-sa-fw2 | 71 | 27 | 5 | 0 |
| ind-ta-fw2 | 0 | 0 | 8 | 0 |
| ind-ta-sangraha-s | 0 | 0 | 9 | 0 |
| ind-ta-sangraha-v | 141 | 17 | 5 | 0 |
| ind-te-fw2 | 18 | 12 | 4 | 0 |
| ind-te-sangraha-s | 24 | 8 | 7 | 0 |
| ind-te-sangraha-v | 18 | 11 | 2 | 0 |

## Every medicine

| pack | author | PR | code | disease | group | rule ID |
|---|---|---|---|---|---|---|
| ind-bn-fw2 | AditeyaAItronics | #64 | A3 | Mojibake | ready: passes on its own pack's gold set, at today's size | `DB-A3-003` |
| ind-bn-fw2 | AditeyaAItronics | #64 | A5 | Wrong normal form | ready: passes on its own pack's gold set, at today's size | `DB-A5-001` |
| ind-bn-fw2 | AditeyaAItronics | #64 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-001` |
| ind-bn-fw2 | AditeyaAItronics | #64 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-001` |
| ind-bn-fw2 | AditeyaAItronics | #64 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-001` |
| ind-bn-fw2 | AditeyaAItronics | #64 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-001` |
| ind-bn-fw2 | AditeyaAItronics | #64 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-001` |
| ind-bn-fw2 | AditeyaAItronics | #64 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-007` |
| ind-bn-fw2 | AditeyaAItronics | #64 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-001` |
| ind-bn-fw2 | AditeyaAItronics | #64 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-001` |
| ind-bn-fw2 | AditeyaAItronics | #64 | F3 | Harmful content | ready: passes on its own pack's gold set, at today's size | `DB-F3-001` |
| ind-bn-fw2 | AditeyaAItronics | #64 | G2 | Lost ZWJ or ZWNJ | held: adds a ZWJ by design; for spec v1 the Gate 2 joiner check stays, so it waits for v2 (TSAI, G2 4 Nov 14:20 IST) |  |
| ind-bn-fw2 | aneeshads | #256 | A6 | Wrong or mixed script | in words only: no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-bn-fw2 | aneeshads | #256 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-024` |
| ind-bn-fw2 | aneeshads | #256 | D3 | Mixed language | not a rule: the author keeps D3 as a candidate (`_candidate_d3`), with no rule in code |  |
| ind-bn-fw2 | sohamniyogi | #138 | A3 | Mojibake | ready: passes on its own pack's gold set, at today's size | `DB-A3-001` |
| ind-bn-fw2 | sohamniyogi | #138 | A5 | Wrong normal form | ready: passes on its own pack's gold set, at today's size | `DB-A5-002` |
| ind-bn-fw2 | sohamniyogi | #138 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-002` |
| ind-bn-fw2 | sohamniyogi | #138 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-002` |
| ind-bn-fw2 | sohamniyogi | #138 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-002` |
| ind-bn-fw2 | sohamniyogi | #138 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-005` |
| ind-bn-fw2 | sohamniyogi | #138 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-008` |
| ind-bn-fw2 | sohamniyogi | #138 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-002` |
| ind-bn-fw2 | sohamniyogi | #138 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-002` |
| ind-bn-fw2 | sohamniyogi | #138 | F3 | Harmful content | ready: passes on its own pack's gold set, at today's size | `DB-F3-002` |
| ind-bn-fw2 | sohamniyogi | #138 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-001` |
| ind-bn-fw2 | sohamniyogi | #138 | G2 | Lost ZWJ or ZWNJ | held: adds a ZWJ by design; for spec v1 the Gate 2 joiner check stays, so it waits for v2 (TSAI, G2 4 Nov 14:20 IST) |  |
| ind-bn-sangraha-v | aneeshads | #30 | A3 | Mojibake | ready: passes on its own pack's gold set, at today's size | `DB-A3-007` |
| ind-bn-sangraha-v | aneeshads | #30 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-020` |
| ind-bn-sangraha-v | aneeshads | #30 | B4 | Template and code junk in prose | ready: passes on its own pack's gold set, at today's size | `DB-B4-009` |
| ind-bn-sangraha-v | aneeshads | #30 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-023` |
| ind-bn-sangraha-v | aneeshads | #30 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-020` |
| ind-bn-sangraha-v | aneeshads | #30 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-015` |
| ind-bn-sangraha-v | aneeshads | #30 | D3 | Mixed language | not a rule: the author's sheet says "Medicine: none"; cure_d3 was a tested candidate she rejected |  |
| ind-bn-sangraha-v | aneeshads | #30 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-015` |
| ind-bn-sangraha-v | aneeshads | #30 | G2 | Lost ZWJ or ZWNJ | held: adds a ZWJ by design; for spec v1 the Gate 2 joiner check stays, so it waits for v2 (TSAI, G2 4 Nov 14:20 IST) |  |
| ind-bn-sangraha-v | aneeshads | #30 | G4 | Over-normalised | ready: passes on its own pack's gold set, at today's size | `DB-G4-006` |
| ind-bn-sangraha-v | pratik-2025 | #112 | A2 | Control characters | ready: Data B's rewrite, OK'd by the author | `DB-A2-001` |
| ind-bn-sangraha-v | pratik-2025 | #112 | A3 | Mojibake | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-bn-sangraha-v | pratik-2025 | #112 | C1 | Boilerplate | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-bn-sangraha-v | pratik-2025 | #112 | C2 | Repeated lines | ready: Data B's rewrite, OK'd by the author | `DB-C2-023` |
| ind-bn-sangraha-v | pratik-2025 | #112 | C3 | Truncated document | rewrite by Data B fails on today's gold set of its pack |  |
| ind-bn-sangraha-v | pratik-2025 | #112 | C4 | Two documents joined | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-bn-sangraha-v | pratik-2025 | #112 | C5 | Lists of keywords or links | ready: Data B's rewrite, OK'd by the author | `DB-C5-021` |
| ind-bn-sangraha-v | pratik-2025 | #112 | D2 | Romanised Indic | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-bn-sangraha-v | pratik-2025 | #112 | D3 | Mixed language | ready: Data B's rewrite, OK'd by the author | `DB-D3-021` |
| ind-bn-sangraha-v | pratik-2025 | #112 | D4 | Bad machine translation | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-bn-sangraha-v | pratik-2025 | #112 | D5 | Translationese | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-bn-sangraha-v | pratik-2025 | #112 | G1 | Cut at the vowel sign | ready: Data B's rewrite, OK'd by the author | `DB-G1-017` |
| ind-bn-sangraha-v | pratik-2025 | #112 | G2 | Lost ZWJ or ZWNJ | held for spec v2: adds a ZWJ by design, and for v1 the Gate 2 joiner check stays (TSAI, G2 4 Nov) |  |
| ind-gu-fw2 | Nisarg189 | #18 | A3 | Mojibake | ready: passes on its own pack's gold set, at today's size | `DB-A3-002` |
| ind-gu-fw2 | Nisarg189 | #18 | A5 | Wrong normal form | ready: passes on its own pack's gold set, at today's size | `DB-A5-003` |
| ind-gu-fw2 | Nisarg189 | #18 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-015` |
| ind-gu-fw2 | Nisarg189 | #18 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-003` |
| ind-gu-fw2 | Nisarg189 | #18 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-007` |
| ind-gu-fw2 | Nisarg189 | #18 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-009` |
| ind-gu-fw2 | Nisarg189 | #18 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-003` |
| ind-gu-fw2 | Nisarg189 | #18 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-003` |
| ind-gu-fw2 | Nisarg189 | #18 | F1 | Personal data | ready: passes on its own pack's gold set, at today's size | `DB-F1-001` |
| ind-gu-fw2 | Nisarg189 | #18 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-002` |
| ind-gu-fw2 | vedang-patel-10 | #91 | A5 | Wrong normal form | ready: passes on its own pack's gold set, at today's size | `DB-A5-004` |
| ind-gu-fw2 | vedang-patel-10 | #91 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-003` |
| ind-gu-fw2 | vedang-patel-10 | #91 | B4 | Template and code junk in prose | ready: passes on its own pack's gold set, at today's size | `DB-B4-001` |
| ind-gu-fw2 | vedang-patel-10 | #91 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-004` |
| ind-gu-fw2 | vedang-patel-10 | #91 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-003` |
| ind-gu-fw2 | vedang-patel-10 | #91 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-010` |
| ind-gu-fw2 | vedang-patel-10 | #91 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-004` |
| ind-gu-fw2 | vedang-patel-10 | #91 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-004` |
| ind-gu-fw2 | vedang-patel-10 | #91 | F1 | Personal data | ready: passes on its own pack's gold set, at today's size | `DB-F1-002` |
| ind-gu-fw2 | vedang-patel-10 | #91 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-003` |
| ind-hi-fw2 | raj-harit-v2 | #8 | B2 | HTML or XML tags | ready: passes on its own pack's gold set, at today's size | `DB-B2-001` |
| ind-hi-fw2 | raj-harit-v2 | #8 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-005` |
| ind-hi-fw2 | raj-harit-v2 | #8 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-006` |
| ind-hi-fw2 | raj-harit-v2 | #8 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-002` |
| ind-hi-fw2 | raj-harit-v2 | #8 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-005` |
| ind-hi-fw2 | revantg | #23 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-017` |
| ind-hi-fw2 | revantg | #23 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-014` |
| ind-hi-fw2 | revantg | #23 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-015` |
| ind-hi-fw2 | revantg | #23 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-012` |
| ind-hi-fw2 | revantg | #23 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-016` |
| ind-hi-fw2 | revantg | #23 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-015` |
| ind-hi-fw2 | revantg | #23 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-013` |
| ind-hi-fw2 | revantg | #23 | D5 | Translationese | ready: passes on its own pack's gold set, at today's size | `DB-D5-003` |
| ind-hi-fw2 | revantg | #23 | F3 | Harmful content | ready: passes on its own pack's gold set, at today's size | `DB-F3-004` |
| ind-hi-hplt | gmrammohan15 | #70 | A5 | Wrong normal form | rewrite by Data B: needs lists from the whole pack or the metadata, so it cannot run on a document alone |  |
| ind-hi-hplt | gmrammohan15 | #70 | A6 | Wrong or mixed script | ready: Data B's rewrite, OK'd by the author | `DB-A6-017` |
| ind-hi-hplt | gmrammohan15 | #70 | C1 | Boilerplate | rewrite by Data B: needs lists from the whole pack or the metadata, so it cannot run on a document alone |  |
| ind-hi-hplt | gmrammohan15 | #70 | C2 | Repeated lines | ready: Data B's rewrite, OK'd by the author | `DB-C2-021` |
| ind-hi-hplt | gmrammohan15 | #70 | C3 | Truncated document | ready: Data B's rewrite, OK'd by the author | `DB-C3-022` |
| ind-hi-hplt | gmrammohan15 | #70 | C4 | Two documents joined | ready: Data B's rewrite, OK'd by the author | `DB-C4-016` |
| ind-hi-hplt | gmrammohan15 | #70 | C5 | Lists of keywords or links | ready: Data B's rewrite, OK'd by the author | `DB-C5-019` |
| ind-hi-hplt | gmrammohan15 | #70 | D2 | Romanised Indic | ready: Data B's rewrite, OK'd by the author | `DB-D2-003` |
| ind-hi-hplt | gmrammohan15 | #70 | D3 | Mixed language | ready: Data B's rewrite, OK'd by the author | `DB-D3-020` |
| ind-hi-hplt | gmrammohan15 | #70 | D4 | Bad machine translation | rewrite by Data B: needs lists from the whole pack or the metadata, so it cannot run on a document alone |  |
| ind-hi-hplt | gmrammohan15 | #70 | D5 | Translationese | rewrite by Data B: needs lists from the whole pack or the metadata, so it cannot run on a document alone |  |
| ind-hi-hplt | gmrammohan15 | #70 | F1 | Personal data | ready: Data B's rewrite, OK'd by the author | `DB-F1-012` |
| ind-hi-hplt | gmrammohan15 | #70 | G1 | Cut at the vowel sign | ready: Data B's rewrite, OK'd by the author | `DB-G1-016` |
| ind-hi-hplt | gmrammohan15 | #70 | G4 | Over-normalised | ready: Data B's rewrite, OK'd by the author | `DB-G4-007` |
| ind-hi-hplt | narasimhatejav | #170 | A5 | Wrong normal form | ready: passes on its own pack's gold set, at today's size | `DB-A5-005` |
| ind-hi-hplt | narasimhatejav | #170 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-004` |
| ind-hi-hplt | narasimhatejav | #170 | B2 | HTML or XML tags | ready: passes on its own pack's gold set, at today's size | `DB-B2-002` |
| ind-hi-hplt | narasimhatejav | #170 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-006` |
| ind-hi-hplt | narasimhatejav | #170 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-004` |
| ind-hi-hplt | narasimhatejav | #170 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-002` |
| ind-hi-hplt | narasimhatejav | #170 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-003` |
| ind-hi-hplt | narasimhatejav | #170 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-001` |
| ind-hi-hplt | narasimhatejav | #170 | D2 | Romanised Indic | ready: passes on its own pack's gold set, at today's size | `DB-D2-001` |
| ind-hi-hplt | narasimhatejav | #170 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-006` |
| ind-hi-hplt | narasimhatejav | #170 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-005` |
| ind-hi-hplt | narasimhatejav | #170 | D5 | Translationese | ready: passes on its own pack's gold set, at today's size | `DB-D5-002` |
| ind-hi-hplt | narasimhatejav | #170 | F1 | Personal data | ready: passes on its own pack's gold set, at today's size | `DB-F1-003` |
| ind-hi-hplt | narasimhatejav | #170 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-004` |
| ind-hi-hplt | pankajkr23 | #83 | A6 | Wrong or mixed script | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-hi-hplt | pankajkr23 | #83 | B2 | HTML or XML tags | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-hi-hplt | pankajkr23 | #83 | C1 | Boilerplate | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-hi-hplt | pankajkr23 | #83 | C2 | Repeated lines | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-hi-hplt | pankajkr23 | #83 | C3 | Truncated document | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-hi-hplt | pankajkr23 | #83 | C4 | Two documents joined | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-hi-hplt | pankajkr23 | #83 | C5 | Lists of keywords or links | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-hi-hplt | pankajkr23 | #83 | D2 | Romanised Indic | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-hi-hplt | pankajkr23 | #83 | D3 | Mixed language | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-hi-hplt | pankajkr23 | #83 | D4 | Bad machine translation | rewrite by Data B: needs lists from the whole pack or the metadata, so it cannot run on a document alone |  |
| ind-hi-hplt | pankajkr23 | #83 | F1 | Personal data | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-hi-hplt | pankajkr23 | #83 | G1 | Cut at the vowel sign | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-hi-hplt | therahulbhati | #24 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-005` |
| ind-hi-hplt | therahulbhati | #24 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-007` |
| ind-hi-hplt | therahulbhati | #24 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-005` |
| ind-hi-hplt | therahulbhati | #24 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-007` |
| ind-hi-hplt | therahulbhati | #24 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-004` |
| ind-hi-hplt | therahulbhati | #24 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-002` |
| ind-hi-hplt | therahulbhati | #24 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-007` |
| ind-hi-hplt | therahulbhati | #24 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-006` |
| ind-hi-hplt | therahulbhati | #24 | F1 | Personal data | ready: passes on its own pack's gold set, at today's size | `DB-F1-004` |
| ind-hi-indiccorp | rajiviyer | #13 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-018` |
| ind-hi-indiccorp | rajiviyer | #13 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-016` |
| ind-hi-indiccorp | rajiviyer | #13 | D4 | Bad machine translation | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-hi-indiccorp | rajiviyer | #13 | F1 | Personal data | ready: passes on its own pack's gold set, at today's size | `DB-F1-011` |
| ind-hi-indiccorp | ranjani-cse | #11 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-025` |
| ind-hi-indiccorp | ranjani-cse | #11 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-012` |
| ind-hi-indiccorp | ranjani-cse | #11 | G3 | Indic dropped by an English rule | ready: passes on its own pack's gold set, at today's size | `DB-G3-003` |
| ind-hi-sangraha-s | rjvim | #106 | A6 | Wrong or mixed script | held: its only job is to turn a visarga used as a colon into ':'; TSAI (#240 review, 5 Nov): a visarga used as a colon is clean, in every script, so the rule waits for the next spec |  |
| ind-hi-sangraha-s | rjvim | #106 | B2 | HTML or XML tags | ready: passes on its own pack's gold set, at today's size | `DB-B2-008` |
| ind-hi-sangraha-s | rjvim | #106 | B4 | Template and code junk in prose | ready: passes on its own pack's gold set, at today's size | `DB-B4-010` |
| ind-hi-sangraha-s | rjvim | #106 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-019` |
| ind-hi-sangraha-s | rjvim | #106 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-023` |
| ind-hi-sangraha-s | rjvim | #106 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-018` |
| ind-hi-sangraha-s | tejaswivinnakota | #160 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-019` |
| ind-hi-sangraha-s | tejaswivinnakota | #160 | B2 | HTML or XML tags | ready: passes on its own pack's gold set, at today's size | `DB-B2-009` |
| ind-hi-sangraha-s | tejaswivinnakota | #160 | B4 | Template and code junk in prose | ready: passes on its own pack's gold set, at today's size | `DB-B4-008` |
| ind-hi-sangraha-s | tejaswivinnakota | #160 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-019` |
| ind-hi-sangraha-v | shishir13 | #100 | A5 | Wrong normal form | gold set empty, not testable |  |
| ind-hi-sangraha-v | shishir13 | #100 | C1 | Boilerplate | gold set empty, not testable |  |
| ind-hi-sangraha-v | shishir13 | #100 | C2 | Repeated lines | gold set empty, not testable |  |
| ind-hi-sangraha-v | shishir13 | #100 | C3 | Truncated document | gold set empty, not testable |  |
| ind-hi-sangraha-v | shishir13 | #100 | C4 | Two documents joined | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-hi-sangraha-v | shishir13 | #100 | C5 | Lists of keywords or links | gold set empty, not testable |  |
| ind-hi-sangraha-v | shishir13 | #100 | D3 | Mixed language | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-hi-sangraha-v | shishir13 | #100 | D4 | Bad machine translation | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-kn-fw2 | LokeshJatangi | #63 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-008` |
| ind-kn-fw2 | LokeshJatangi | #63 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-006` |
| ind-kn-fw2 | LokeshJatangi | #63 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-011` |
| ind-kn-fw2 | LokeshJatangi | #63 | F1 | Personal data | fails on today's gold set of its pack (re-run on 3 to 5 Nov) |  |
| ind-kn-fw2 | keshavamurali | #47 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-009` |
| ind-kn-fw2 | keshavamurali | #47 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-007` |
| ind-kn-fw2 | keshavamurali | #47 | C4 | Two documents joined | in words only: no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-kn-fw2 | keshavamurali | #47 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-012` |
| ind-kn-fw2 | keshavamurali | #47 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-005` |
| ind-kn-sangraha-s | millermuttu | #104 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-006` |
| ind-kn-sangraha-s | millermuttu | #104 | B2 | HTML or XML tags | ready: passes on its own pack's gold set, at today's size | `DB-B2-003` |
| ind-kn-sangraha-s | millermuttu | #104 | B3 | Ghost chat markers | ready: passes on its own pack's gold set, at today's size | `DB-B3-001` |
| ind-kn-sangraha-s | millermuttu | #104 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-010` |
| ind-kn-sangraha-s | millermuttu | #104 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-008` |
| ind-kn-sangraha-s | millermuttu | #104 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-008` |
| ind-kn-sangraha-s | subramanyanaik | #94 | A3 | Mojibake | ready: passes on its own pack's gold set, at today's size | `DB-A3-005` |
| ind-kn-sangraha-s | subramanyanaik | #94 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-016` |
| ind-kn-sangraha-s | subramanyanaik | #94 | B2 | HTML or XML tags | ready: passes on its own pack's gold set, at today's size | `DB-B2-006` |
| ind-kn-sangraha-s | subramanyanaik | #94 | B3 | Ghost chat markers | ready: passes on its own pack's gold set, at today's size | `DB-B3-002` |
| ind-kn-sangraha-s | subramanyanaik | #94 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-017` |
| ind-kn-sangraha-s | subramanyanaik | #94 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-014` |
| ind-kn-sangraha-s | subramanyanaik | #94 | G4 | Over-normalised | held: its only job is to turn a visarga used as a colon into ':'; TSAI (#240 review, 5 Nov): a visarga used as a colon is clean, in every script, so the rule waits for the next spec |  |
| ind-kn-sangraha-v | Anusha-raju | #40 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-019` |
| ind-kn-sangraha-v | Anusha-raju | #40 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-018` |
| ind-kn-sangraha-v | Anusha-raju | #40 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-016` |
| ind-kn-sangraha-v | Anusha-raju | #40 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-015` |
| ind-kn-sangraha-v | pyru | #25 | A3 | Mojibake | ready: passes on its own pack's gold set, at today's size | `DB-A3-004` |
| ind-kn-sangraha-v | pyru | #25 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-007` |
| ind-kn-sangraha-v | pyru | #25 | B4 | Template and code junk in prose | ready: passes on its own pack's gold set, at today's size | `DB-B4-002` |
| ind-kn-sangraha-v | pyru | #25 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-011` |
| ind-kn-sangraha-v | pyru | #25 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-008` |
| ind-kn-sangraha-v | pyru | #25 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-009` |
| ind-kn-sangraha-v | pyru | #25 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-008` |
| ind-kn-sangraha-v | pyru | #25 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-003` |
| ind-kn-sangraha-v | pyru | #25 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-009` |
| ind-kn-sangraha-v | pyru | #25 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-007` |
| ind-kn-sangraha-v | pyru | #25 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-011` |
| ind-kn-sangraha-v | pyru | #25 | G4 | Over-normalised | held: its only job is to turn a visarga used as a colon into ':'; TSAI (#240 review, 5 Nov): a visarga used as a colon is clean, in every script, so the rule waits for the next spec |  |
| ind-ml-fw2 | umeshnmenon | #116 | C1 | Boilerplate | gold set empty, not testable |  |
| ind-ml-fw2 | umeshnmenon | #116 | C4 | Two documents joined | gold set empty, not testable |  |
| ind-ml-fw2 | umeshnmenon | #116 | D3 | Mixed language | gold set empty, not testable |  |
| ind-mr-fw2 | adinathauti | #114 | A1 | Invisible junk characters | ready: passes on its own pack's gold set, at today's size | `DB-A1-001` |
| ind-mr-fw2 | adinathauti | #114 | A3 | Mojibake | ready: passes on its own pack's gold set, at today's size | `DB-A3-006` |
| ind-mr-fw2 | adinathauti | #114 | A5 | Wrong normal form | ready: passes on its own pack's gold set, at today's size | `DB-A5-009` |
| ind-mr-fw2 | adinathauti | #114 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-020` |
| ind-mr-fw2 | adinathauti | #114 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-015` |
| ind-mr-fw2 | adinathauti | #114 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-019` |
| ind-mr-fw2 | adinathauti | #114 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-017` |
| ind-mr-fw2 | thinktinkergreen | #50 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-008` |
| ind-mr-fw2 | thinktinkergreen | #50 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-009` |
| ind-mr-fw2 | thinktinkergreen | #50 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-003` |
| ind-mr-fw2 | thinktinkergreen | #50 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-005` |
| ind-mr-fw2 | thinktinkergreen | #50 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-004` |
| ind-mr-fw2 | thinktinkergreen | #50 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-010` |
| ind-mr-fw2 | thinktinkergreen | #50 | F1 | Personal data | ready: passes on its own pack's gold set, at today's size | `DB-F1-006` |
| ind-mr-fw2 | thinktinkergreen | #50 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-006` |
| ind-mr-fw2 | thinktinkergreen | #50 | G4 | Over-normalised | ready: passes on its own pack's gold set, at today's size | `DB-G4-002` |
| ind-mr-fw2 | vpw | #43 | A5 | Wrong normal form | in words only: no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-fw2 | vpw | #43 | B4 | Template and code junk in prose | ready: passes on its own pack's gold set, at today's size | `DB-B4-011` |
| ind-mr-fw2 | vpw | #43 | C1 | Boilerplate | in words only: no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-fw2 | vpw | #43 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-022` |
| ind-mr-fw2 | vpw | #43 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-024` |
| ind-mr-fw2 | vpw | #43 | C4 | Two documents joined | in words only: no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-fw2 | vpw | #43 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-020` |
| ind-mr-fw2 | vpw | #43 | D3 | Mixed language | in words only: no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-fw2 | vpw | #43 | D4 | Bad machine translation | in words only: no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-fw2 | vpw | #43 | D5 | Translationese | in words only: no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-fw2 | vpw | #43 | F1 | Personal data | in words only: no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-fw2 | vpw | #43 | G2 | Lost ZWJ or ZWNJ | in words only: no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-sangraha-v | avnishbm | #46 | A6 | Wrong or mixed script | ready: Data B's rewrite, OK'd by the author | `DB-A6-021` |
| ind-mr-sangraha-v | avnishbm | #46 | B4 | Template and code junk in prose | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-sangraha-v | avnishbm | #46 | C1 | Boilerplate | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-sangraha-v | avnishbm | #46 | C3 | Truncated document | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-sangraha-v | avnishbm | #46 | C4 | Two documents joined | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-sangraha-v | avnishbm | #46 | C5 | Lists of keywords or links | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-sangraha-v | avnishbm | #46 | D3 | Mixed language | ready: Data B's rewrite, OK'd by the author | `DB-D3-022` |
| ind-mr-sangraha-v | avnishbm | #46 | D4 | Bad machine translation | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-sangraha-v | avnishbm | #46 | F1 | Personal data | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-mr-sangraha-v | patilvijay23 | #19 | A5 | Wrong normal form | ready: passes on its own pack's gold set, at today's size | `DB-A5-006` |
| ind-mr-sangraha-v | patilvijay23 | #19 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-009` |
| ind-mr-sangraha-v | patilvijay23 | #19 | B4 | Template and code junk in prose | ready: passes on its own pack's gold set, at today's size | `DB-B4-003` |
| ind-mr-sangraha-v | patilvijay23 | #19 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-012` |
| ind-mr-sangraha-v | patilvijay23 | #19 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-010` |
| ind-mr-sangraha-v | patilvijay23 | #19 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-010` |
| ind-mr-sangraha-v | patilvijay23 | #19 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-009` |
| ind-mr-sangraha-v | patilvijay23 | #19 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-013` |
| ind-mr-sangraha-v | patilvijay23 | #19 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-011` |
| ind-mr-sangraha-v | patilvijay23 | #19 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-008` |
| ind-mr-sangraha-v | patilvijay23 | #19 | F1 | Personal data | ready: passes on its own pack's gold set, at today's size | `DB-F1-007` |
| ind-or-fw2 | Pritish52718 | #86 | A5 | Wrong normal form | gold set empty, not testable |  |
| ind-or-fw2 | Pritish52718 | #86 | A6 | Wrong or mixed script | gold set empty, not testable |  |
| ind-or-fw2 | Pritish52718 | #86 | C1 | Boilerplate | gold set empty, not testable |  |
| ind-or-fw2 | Pritish52718 | #86 | C3 | Truncated document | gold set empty, not testable |  |
| ind-or-fw2 | Pritish52718 | #86 | C4 | Two documents joined | gold set empty, not testable |  |
| ind-or-fw2 | Pritish52718 | #86 | D3 | Mixed language | gold set empty, not testable |  |
| ind-or-fw2 | Pritish52718 | #86 | D4 | Bad machine translation | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-or-fw2 | Pritish52718 | #86 | F1 | Personal data | gold set empty, not testable |  |
| ind-or-fw2 | Pritish52718 | #86 | F3 | Harmful content | rule in code that takes the document (it needs the URL), kept outside a python block because harm_test_indic.py passes only the text; gold set empty, not testable |  |
| ind-or-fw2 | Pritish52718 | #86 | G1 | Cut at the vowel sign | gold set empty, not testable |  |
| ind-or-fw2 | Pritish52718 | #86 | G2 | Lost ZWJ or ZWNJ | gold set empty, not testable |  |
| ind-sa-fw2 | dattatreyamanjunath | #45 | A4 | Replacement characters | ready: passes on its own pack's gold set, at today's size | `DB-A4-001` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | A5 | Wrong normal form | ready: passes on its own pack's gold set, at today's size | `DB-A5-007` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | A6 | Wrong or mixed script | held: it turns ':' into a visarga (Sanskrit); TSAI (#240, 5 Nov): in spec v1 no rule converts between a visarga and a colon, in either direction, so the rule waits for the next spec (a colon-to-visarga fix in Sanskrit can come back with its own harm test) |  |
| ind-sa-fw2 | dattatreyamanjunath | #45 | B4 | Template and code junk in prose | ready: passes on its own pack's gold set, at today's size | `DB-B4-004` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-013` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-004` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-010` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-014` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | D2 | Romanised Indic | ready: passes on its own pack's gold set, at today's size | `DB-D2-002` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-012` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-009` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | F1 | Personal data | ready: passes on its own pack's gold set, at today's size | `DB-F1-008` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | F2 | Benchmark leak | held: untested: it needs the Itihasa test sentences (ITIHASA_TEST_SN), benchmark text that the eval firewall rule keeps out of the repo (G 4 Nov 12:19 IST); waits for the next spec |  |
| ind-sa-fw2 | dattatreyamanjunath | #45 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-007` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | G2 | Lost ZWJ or ZWNJ | not a rule: the author's G2 fixes the extraction step, not the text, so it has no rule in code |  |
| ind-sa-fw2 | dattatreyamanjunath | #45 | G3 | Indic dropped by an English rule | ready: passes on its own pack's gold set, at today's size | `DB-G3-001` |
| ind-sa-fw2 | dattatreyamanjunath | #45 | H3 | The same content in another source or language | ready: passes on its own pack's gold set, at today's size | `DB-H3-001` |
| ind-sa-fw2 | swatibansal | #80 | A5 | Wrong normal form | ready: passes on its own pack's gold set, at today's size | `DB-A5-008` |
| ind-sa-fw2 | swatibansal | #80 | A6 | Wrong or mixed script | held: it turns ':' into a visarga (Sanskrit); TSAI (#240, 5 Nov): in spec v1 no rule converts between a visarga and a colon, in either direction, so the rule waits for the next spec (a colon-to-visarga fix in Sanskrit can come back with its own harm test) |  |
| ind-sa-fw2 | swatibansal | #80 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-014` |
| ind-sa-fw2 | swatibansal | #80 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-011` |
| ind-sa-fw2 | swatibansal | #80 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-011` |
| ind-sa-fw2 | swatibansal | #80 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-011` |
| ind-sa-fw2 | swatibansal | #80 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-015` |
| ind-sa-fw2 | swatibansal | #80 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-013` |
| ind-sa-fw2 | swatibansal | #80 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-010` |
| ind-sa-fw2 | swatibansal | #80 | F1 | Personal data | ready: passes on its own pack's gold set, at today's size | `DB-F1-009` |
| ind-sa-fw2 | swatibansal | #80 | F2 | Benchmark leak | held: untested: it needs the FLORES-200 / IN22 / Itihasa benchmark files, so its gold run cannot fire; waits for the next spec (TSAI, G2 5 Nov 08:32 IST) |  |
| ind-sa-fw2 | swatibansal | #80 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-008` |
| ind-sa-fw2 | swatibansal | #80 | G2 | Lost ZWJ or ZWNJ | ready: passes on its own pack's gold set, at today's size | `DB-G2-003` |
| ind-sa-fw2 | swatibansal | #80 | G4 | Over-normalised | ready: passes on its own pack's gold set, at today's size | `DB-G4-003` |
| ind-sa-fw2 | swatibansal | #80 | H3 | The same content in another source or language | ready: passes on its own pack's gold set, at today's size | `DB-H3-002` |
| ind-ta-fw2 | Dharshanthaigu | #169 | A6 | Wrong or mixed script | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-ta-fw2 | Dharshanthaigu | #169 | C1 | Boilerplate | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-ta-fw2 | Dharshanthaigu | #169 | C2 | Repeated lines | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-ta-fw2 | Dharshanthaigu | #169 | C3 | Truncated document | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-ta-fw2 | Dharshanthaigu | #169 | C5 | Lists of keywords or links | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-ta-fw2 | Dharshanthaigu | #169 | D3 | Mixed language | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-ta-fw2 | Dharshanthaigu | #169 | D4 | Bad machine translation | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-ta-fw2 | Dharshanthaigu | #169 | G1 | Cut at the vowel sign | gold set empty, not testable |  |
| ind-ta-sangraha-s | truesrini | #105 | A6 | Wrong or mixed script | gold set empty, not testable |  |
| ind-ta-sangraha-s | truesrini | #105 | B2 | HTML or XML tags | gold set empty, not testable |  |
| ind-ta-sangraha-s | truesrini | #105 | B4 | Template and code junk in prose | gold set empty, not testable |  |
| ind-ta-sangraha-s | truesrini | #105 | C2 | Repeated lines | gold set empty, not testable |  |
| ind-ta-sangraha-s | truesrini | #105 | C3 | Truncated document | gold set empty, not testable |  |
| ind-ta-sangraha-s | truesrini | #105 | D4 | Bad machine translation | gold set empty, not testable |  |
| ind-ta-sangraha-s | truesrini | #105 | D5 | Translationese | gold set empty, not testable |  |
| ind-ta-sangraha-s | truesrini | #105 | G3 | Indic dropped by an English rule | gold set empty, not testable |  |
| ind-ta-sangraha-s | truesrini | #105 | G4 | Over-normalised | gold set empty, not testable |  |
| ind-ta-sangraha-v | Hemaaaa04 | #57 | B4 | Template and code junk in prose | ready: passes on its own pack's gold set, at today's size | `DB-B4-007` |
| ind-ta-sangraha-v | Hemaaaa04 | #57 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-021` |
| ind-ta-sangraha-v | Hemaaaa04 | #57 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-016` |
| ind-ta-sangraha-v | Hemaaaa04 | #57 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-021` |
| ind-ta-sangraha-v | Hemaaaa04 | #57 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-013` |
| ind-ta-sangraha-v | Hemaaaa04 | #57 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-017` |
| ind-ta-sangraha-v | Hemaaaa04 | #57 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-018` |
| ind-ta-sangraha-v | Hemaaaa04 | #57 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-017` |
| ind-ta-sangraha-v | Hemaaaa04 | #57 | F3 | Harmful content | ready: passes on its own pack's gold set, at today's size | `DB-F3-005` |
| ind-ta-sangraha-v | Hemaaaa04 | #57 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-013` |
| ind-ta-sangraha-v | abinesh1 | #101 | A6 | Wrong or mixed script | held: its only job is to turn ஃ into ':' (Unicode names ஃ the Tamil visarga); TSAI (#240, 5 Nov): in spec v1 no rule converts between a visarga and a colon, in either direction, so the rule waits for the next spec |  |
| ind-ta-sangraha-v | abinesh1 | #101 | B4 | Template and code junk in prose | ready: passes on its own pack's gold set, at today's size | `DB-B4-005` |
| ind-ta-sangraha-v | abinesh1 | #101 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-015` |
| ind-ta-sangraha-v | abinesh1 | #101 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-012` |
| ind-ta-sangraha-v | abinesh1 | #101 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-012` |
| ind-ta-sangraha-v | abinesh1 | #101 | C4 | Two documents joined | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-ta-sangraha-v | abinesh1 | #101 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-005` |
| ind-ta-sangraha-v | abinesh1 | #101 | D3 | Mixed language | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-ta-sangraha-v | abinesh1 | #101 | D4 | Bad machine translation | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-ta-sangraha-v | abinesh1 | #101 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-009` |
| ind-ta-sangraha-v | abinesh1 | #101 | G3 | Indic dropped by an English rule | flag only: a note, not a rule (TSAI ruling 4) |  |
| ind-ta-sangraha-v | abinesh1 | #101 | G4 | Over-normalised | ready: passes on its own pack's gold set, at today's size | `DB-G4-004` |
| ind-te-fw2 | bedathurihari | #58 | C1 | Boilerplate | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-te-fw2 | bedathurihari | #58 | C2 | Repeated lines | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-te-fw2 | bedathurihari | #58 | D3 | Mixed language | rewrite by Data B passes on today's gold; waiting for the author's OK in their PR |  |
| ind-te-fw2 | bedathurihari | #58 | F1 | Personal data | no **Disease:** line and no python block (the harm tool cannot read it) |  |
| ind-te-fw2 | sandeepkunkunuru | #3 | A6 | Wrong or mixed script | ready: passes on its own pack's gold set, at today's size | `DB-A6-013` |
| ind-te-fw2 | sandeepkunkunuru | #3 | B2 | HTML or XML tags | ready: passes on its own pack's gold set, at today's size | `DB-B2-004` |
| ind-te-fw2 | sandeepkunkunuru | #3 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-016` |
| ind-te-fw2 | sandeepkunkunuru | #3 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-013` |
| ind-te-fw2 | sandeepkunkunuru | #3 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-013` |
| ind-te-fw2 | sandeepkunkunuru | #3 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-006` |
| ind-te-fw2 | sandeepkunkunuru | #3 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-006` |
| ind-te-fw2 | sandeepkunkunuru | #3 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-014` |
| ind-te-fw2 | sandeepkunkunuru | #3 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-011` |
| ind-te-fw2 | sandeepkunkunuru | #3 | F1 | Personal data | ready: passes on its own pack's gold set, at today's size | `DB-F1-010` |
| ind-te-fw2 | sandeepkunkunuru | #3 | F3 | Harmful content | ready: passes on its own pack's gold set, at today's size | `DB-F3-003` |
| ind-te-fw2 | sandeepkunkunuru | #3 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-010` |
| ind-te-sangraha-s | murthyap63-a11y | #71 | A3 | Mojibake | needs a reviewer's input (for example a list of verified fixes), so it cannot run on a document alone |  |
| ind-te-sangraha-s | murthyap63-a11y | #71 | A6 | Wrong or mixed script | needs a reviewer's input (for example a list of verified fixes), so it cannot run on a document alone |  |
| ind-te-sangraha-s | murthyap63-a11y | #71 | B2 | HTML or XML tags | ready: passes on its own pack's gold set, at today's size | `DB-B2-007` |
| ind-te-sangraha-s | murthyap63-a11y | #71 | B4 | Template and code junk in prose | needs a reviewer's input (for example a list of verified fixes), so it cannot run on a document alone |  |
| ind-te-sangraha-s | murthyap63-a11y | #71 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-017` |
| ind-te-sangraha-s | murthyap63-a11y | #71 | C3 | Truncated document | needs a reviewer's input (for example a list of verified fixes), so it cannot run on a document alone |  |
| ind-te-sangraha-s | murthyap63-a11y | #71 | D4 | Bad machine translation | needs a reviewer's input (for example a list of verified fixes), so it cannot run on a document alone |  |
| ind-te-sangraha-s | murthyap63-a11y | #71 | D5 | Translationese | needs a reviewer's input (for example a list of verified fixes), so it cannot run on a document alone |  |
| ind-te-sangraha-s | shankarpandala | #92 | A6 | Wrong or mixed script | held: its only job is to turn a visarga used as a colon into ':'; TSAI (#240 review, 5 Nov): a visarga used as a colon is clean, in every script, so the rule waits for the next spec |  |
| ind-te-sangraha-s | shankarpandala | #92 | B2 | HTML or XML tags | ready: passes on its own pack's gold set, at today's size | `DB-B2-005` |
| ind-te-sangraha-s | shankarpandala | #92 | B4 | Template and code junk in prose | ready: passes on its own pack's gold set, at today's size | `DB-B4-006` |
| ind-te-sangraha-s | shankarpandala | #92 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-014` |
| ind-te-sangraha-s | shankarpandala | #92 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-012` |
| ind-te-sangraha-s | shankarpandala | #92 | D5 | Translationese | ready: passes on its own pack's gold set, at today's size | `DB-D5-001` |
| ind-te-sangraha-s | shankarpandala | #92 | G3 | Indic dropped by an English rule | ready: passes on its own pack's gold set, at today's size | `DB-G3-002` |
| ind-te-sangraha-v | SreekanthZipsy | #109 | A1 | Invisible junk characters | ready: passes on its own pack's gold set, at today's size | `DB-A1-002` |
| ind-te-sangraha-v | SreekanthZipsy | #109 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-022` |
| ind-te-sangraha-v | SreekanthZipsy | #109 | C2 | Repeated lines | ready: passes on its own pack's gold set, at today's size | `DB-C2-018` |
| ind-te-sangraha-v | SreekanthZipsy | #109 | C3 | Truncated document | ready: passes on its own pack's gold set, at today's size | `DB-C3-020` |
| ind-te-sangraha-v | SreekanthZipsy | #109 | C4 | Two documents joined | ready: passes on its own pack's gold set, at today's size | `DB-C4-014` |
| ind-te-sangraha-v | SreekanthZipsy | #109 | C5 | Lists of keywords or links | ready: passes on its own pack's gold set, at today's size | `DB-C5-018` |
| ind-te-sangraha-v | SreekanthZipsy | #109 | D3 | Mixed language | ready: passes on its own pack's gold set, at today's size | `DB-D3-019` |
| ind-te-sangraha-v | SreekanthZipsy | #109 | D4 | Bad machine translation | ready: passes on its own pack's gold set, at today's size | `DB-D4-016` |
| ind-te-sangraha-v | SreekanthZipsy | #109 | D5 | Translationese | ready: passes on its own pack's gold set, at today's size | `DB-D5-004` |
| ind-te-sangraha-v | SreekanthZipsy | #109 | G1 | Cut at the vowel sign | ready: passes on its own pack's gold set, at today's size | `DB-G1-014` |
| ind-te-sangraha-v | oddjoker91 | #177 | C1 | Boilerplate | ready: passes on its own pack's gold set, at today's size | `DB-C1-025` |
| ind-te-sangraha-v | oddjoker91 | #177 | C6 | Repeated punctuation (new code, TSAI 5 Nov; not yet in DISEASES.md) | held: C6 is a new code; TSAI (G2 5 Nov) puts it in spec v1 once the code owner approves #177 after the label fixes |  |
| ind-te-sangraha-v | oddjoker91 | #177 | D3 | Mixed language | held: D3 is a label only (TSAI, 31 Oct); the code-owner review asks to move it to a candidate for spec v2 |  |
