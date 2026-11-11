# SWE env quality review (SWE-bench Verified criteria), 4 Nov 2026
Reviewer: model-assisted review (Claude Sonnet), needs a human spot-check. The two drops were re-checked against issue.md and test.patch in a second read (both need exact error messages the issue never mentions) and are **not** in `swe-envs/`. The review is metadata for choosing envs; it is not training data.

The five keep-flagged envs stay in `swe-envs/`: they pass the gold check, but a correct fix that reads the issue differently can still fail them. RL runs can down-weight or skip them.

Scores: 0 = fine, 3 = unusable. Judged by reading issue.md, gold.patch, test.patch and the FAIL_TO_PASS ids. Nothing was executed, so "fails before the fix" was not re-verified.

| # | instance_id | underspecified (0-3) | tests_beyond_issue (0-3) | difficulty | other problems | verdict | one-line reason (max 25 words) |
|---|---|---|---|---|---|---|---|
| 1 | agronholm__typeguard-42 | 1 | 1 | <15 min | Image uses Python 3.8 (2018 PR); the gold check confirms both F2P tests fail at base | keep | Clear symptom (AttributeError on typing.* names); tests only expect TypeError. |
| 2 | mahmoud__boltons-302 | 1 | 1 | <15 min | Test uses date.today() (harmless) | keep | One-line issue, but same start and stop is clear; test also wants empty result when non-inclusive, which is the natural reading. |
| 3 | masterminds__semver-134 | 0 | 0 | <15 min | Go repo; issue quotes the README rule | keep | Exact repro and expected result given; test is one added table row. |
| 4 | masterminds__semver-142 | 0 | 1 | <15 min | Go repo | keep | Repro and failing line named; extra <=4.5 rows follow from the same dirty-version rule. |
| 5 | masterminds__semver-181 | 1 | 3 | <15 min | Go repo; F2P TestConstraintsValidate changes an existing error string | drop | TestConstraintsValidate requires a new exact error message the issue never mentions; a correct behavioural fix fails it. |
| 6 | more-itertools__more-itertools-411 | 0 | 1 | <15 min | Issue proposes the exact fix | keep | Expected tuple output stated; tests add r=0 and empty cases that follow from matching itertools.permutations. |
| 7 | more-itertools__more-itertools-659 | 1 | 0 | <15 min | Issue is phrased as a question | keep | Author expects no trailing empty list; the intended behaviour is implied, and the test is a single case. |
| 8 | pallets__click-1934 | 0 | 0 | <15 min | Issue gives the exact one-line fix | keep | Repro, expected value and fix given; parametrised tests only check is_bool_flag. |
| 9 | pallets__click-1990 | 0 | 0 | 15 min-1 h | none | keep | Issue states the expected "Missing option" error, matching the test assertion. |
| 10 | pallets__jinja-1204 | 0 | 0 | <15 min | none | keep | Expected UndefinedError for "in" on Undefined is explicit; test asserts exactly that. |
| 11 | pallets__jinja-1522 | 0 | 0 | <15 min | Fix is a revert to identity hash | keep | Issue shows hash() raising; test only requires hash() to succeed, so any hashable fix passes. |
| 12 | python-humanize__humanize-26 | 0 | 0 | <15 min | none | keep | ndigits=0 should round to zero decimals; the single test case matches. |
| 13 | python-humanize__humanize-41 | 0 | 0 | 15 min-1 h | none | keep | Negative intword expected "-1.0 billion"; the other negative cases follow by symmetry. |
| 14 | python-jsonschema__jsonschema-875 | 0 | 0 | <15 min | Issue gives the exact fix; F2P are 12 un-skipped suite cases | keep | Bug, cause and fix are explicit; tests just remove skips for the uniqueItems cases. |
| 15 | python-poetry__tomlkit-219 | 1 | 1 | 1-4 h | Needs tomlkit container internals; exact output string compared | keep | Expected output shown; test compares exact dump text including a blank line, which the issue calls acceptable. |
| 16 | python-poetry__tomlkit-221 | 1 | 2 | 15 min-1 h | Issue number mismatch (221 vs 222); issue is about parse, test is copy.copy | keep-flagged | Issue shows parse yielding None items; test uses copy.copy on such an array, so a parser-only fix could fail. |
| 17 | python-poetry__tomlkit-236 | 2 | 1 | 15 min-1 h | none | keep-flagged | Issue shows only wrong output, no expected output; test demands exact inline-table text "[[{a = 1}]]" (the only valid TOML form). |
| 18 | python-semver__python-semver-245 | 1 | 1 | 15 min-1 h | Large doc changes in gold, not needed | keep | List and string comparison requested; tests add ValueError for malformed strings, which follows from parsing the string. |
| 19 | python-semver__python-semver-261 | 2 | 3 | 15 min-1 h | One-sentence issue; tests rework negative-index and slice rules | drop | Issue covers only falsy parts; tests also require negative-index IndexError behaviour and specific messages never mentioned. |
| 20 | python-validators__validators-191 | 1 | 2 | <15 min | none | keep-flagged | Issue is about long zero runs; test needs "0127.0.0.1" rejected, so only a max-3-characters rule (or no leading zeros) passes. |
| 21 | scrapy__w3lib-136 | 2 | 1 | <15 min | Title and main proposal say raise ValueError; test needs strip | keep-flagged | Issue prefers raising an error and mentions strip only as a weaker option; test requires stripping, trailing spaces included. |
| 22 | scrapy__w3lib-196 | 1 | 2 | 15 min-1 h | none | keep-flagged | Issue asks for idempotency; test also requires %26 to become & in userinfo, so a minimal escape-preserving fix fails. |
| 23 | scrapy__w3lib-202 | 0 | 1 | <15 min | none | keep | OverflowError should be caught; test expects the same results as other illegal entities, a natural reading. |

## Summary
- keep: 16 (typeguard-42, boltons-302, semver-134, semver-142, more-itertools-411, more-itertools-659, click-1934, click-1990, jinja-1204, jinja-1522, humanize-26, humanize-41, jsonschema-875, tomlkit-219, python-semver-245, w3lib-202)
- keep-flagged: 5 (tomlkit-221, tomlkit-236, validators-191, w3lib-136, w3lib-196)
- drop: 2 (masterminds__semver-181, python-semver__python-semver-261)
- 21 usable, so dropping the two gives at least the 20 needed without being lenient.

Human should look first at:
1. python-semver-261 and masterminds__semver-181 (the drops): confirm the hidden-test problem.
2. scrapy__w3lib-136 (issue says raise, test says strip) and tomlkit-221 (issue/test mismatch).
3. typeguard-42: run the F2P test on the env's Python version to confirm it fails before the fix.
4. Most envs reveal the fix in the issue (click-1934, jsonschema-875, more-itertools-411); this makes them easy, not invalid.
