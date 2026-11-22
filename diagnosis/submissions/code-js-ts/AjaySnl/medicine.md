# Medicine sheet: code-js-ts (AjaySnl)

Write one section for each disease that you found more than five times.

---

## Medicine 1 — B3: StarCoder ghost tokens

### 1. Disease

**Disease:** B3

**Count in pack:** 258 documents out of 500

**Description:** Documents from `bigcode/starcoderdata` carry StarCoder preprocessing tokens embedded in their text. These tokens were inserted by StarCoder's data pipeline to mark metadata (repository name, filename, star count) and to anonymise personal data (email addresses and author names). They are not part of the original source code. Training V5 on text containing these tokens would teach the model to generate them as plain text.

The tokens observed:

| Token | Docs containing token | Total occurrences |
|---|---|---|
| `<gh_stars>` | 107 | 107 |
| `<filename>` | 105 | 105 |
| `<reponame>` | 101 | 101 |
| `<NAME>` | 14 | 25 |
| `<EMAIL>` | 10 | 29 |

`<filename>`, `<reponame>`, and `<gh_stars>` each appear at most once per document (always as a prefix block). `<EMAIL>` and `<NAME>` may appear multiple times per document (once for each anonymised value).

**Four examples:**

**Example A — `<filename>` and `<gh_stars>` prefix block:**
- `doc_id=c38890881e99e48e`
- Text starts: `<filename>src/extended-repeater.js<gh_stars>0\nimport { NotImplementedError }...`
- `'<filename>'` at offset 0; `'<gh_stars>'` at offset 34

**Example B — `<reponame>` prefix:**
- `doc_id=c09dabc135210035`
- Text starts: `<reponame>heminjohnson/Node-Chat-App-With-Socket.io\nvar expect = require('expect')`
- `'<reponame>'` at offset 0

**Example C — `<EMAIL>` anonymisation token in test code:**
- `doc_id=ec27a58ce8941db1`
- Text contains: `...rule.passes('<EMAIL>', { primary_email: '<EMAIL>' })...`
- `'<EMAIL>'` at offsets 202, 230, 328 (multiple occurrences; 29 total across 10 documents)

**Example D — `<NAME>` author anonymisation token in licence header:**
- `doc_id=ac23df9698407bac`
- Text starts: `/** * Copyright (c) 2020 <NAME> * Licensed under the Apache License...`
- `'<NAME>'` at offset 32

---

### 2. Medicine

**Rule in words:**

1. Strip the StarCoder prefix block from the **absolute beginning** of the document. The block consists of one to five consecutive lines, each starting with `<reponame>`, `<filename>`, or `<gh_stars>` (in any order), followed by their value on the same line. The match must begin at character position 0.
2. Replace any remaining `<EMAIL>` tokens in the document body with `user@example.com`.
3. Replace any remaining `<NAME>` tokens with `[AUTHOR]`.
4. Remove any other ghost-marker tokens (chat template tokens) if present.

**Rule in code:**

```python
import re

# \A anchors to the absolute start of the string.
# This prevents the regex from matching a <filename>-like line in the middle
# of a document body. Using ^ with re.MULTILINE would incorrectly match
# any line starting with the token, not only the document's first line.
_STARCODER_LINE = r'<(?:reponame|filename|gh_stars)>[^\n]*\n?'
STARCODER_PREFIX_RE = re.compile(r'\A(?:' + _STARCODER_LINE + r'){1,5}')

# Replace <EMAIL> anonymisation tokens.
# user@example.com uses the IANA-reserved example.com domain (RFC 2606)
# and is a syntactically valid RFC 5321 email address.
# The old placeholder [email protected] was NOT RFC 5321 valid.
EMAIL_TOKEN_RE = re.compile(r'<EMAIL>')

# Replace <NAME> anonymisation tokens.
NAME_TOKEN_RE = re.compile(r'<NAME>')

# Remove other ghost markers (chat-template tokens) if present.
OTHER_GHOST_RE = re.compile(
    r'<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>'
    r'|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>'
    r'|<think>|</think>'
)

def cure_b3(text: str) -> str:
    """Strip StarCoder prefix and replace anonymisation tokens."""
    text = STARCODER_PREFIX_RE.sub('', text, count=1)
    text = EMAIL_TOKEN_RE.sub('user@example.com', text)
    text = NAME_TOKEN_RE.sub('[AUTHOR]', text)
    text = OTHER_GHOST_RE.sub('', text)
    return text
```

---

### 3. Action

**Action:** fix

**Fix the text.** The underlying code is valid; only the StarCoder metadata prefix and anonymisation tokens need to be removed or replaced. Dropping the whole document would be wasteful for 258 otherwise-clean files.

Exception: if B3 co-occurs with E1 (compiled/generated code) or E3 (embedded secrets), the verdict is `drop` regardless of this medicine, because the other disease takes precedence.

---

### 4. Harm test

#### 4a. Regression tests (automated, pass/fail)

20 unit tests covering:

| Test group | Cases covered | Result |
|---|---|---|
| Anchor correctness | Valid prefix stripped; body token NOT stripped; no-prefix doc unchanged; trailing blank after prefix | 6/6 pass |
| Token-like strings in code | `<filename>` in `//` comment; in string literal; in object value; in JSX attr (with whitespace); at non-zero line start | 5/5 pass |
| EMAIL replacement | String-literal context; known test-literal regression; EMAIL inside prefix block | 3/3 pass |
| NAME replacement | Copyright header; doc without token | 2/2 pass |
| OTHER_GHOST_RE | Chat token stripped from body; `<s>` HTML tag preserved; chat token in string literal removed; chat token in comment removed | 4/4 pass |

**Total: 20/20 pass.**

Key result for the anchor fix: test `1c` confirms that a `<filename>` line in the document body is **not** stripped with the `\A` anchor. The old `re.MULTILINE` version incorrectly stripped it (test `1d` documents the bug).

Tests `5c` and `5d` document that `OTHER_GHOST_RE` removes ghost tokens globally — including from inside string literals and comments. This is the intended behaviour (see side effect 8 below) and is tested, not assumed.

#### 4b. Official harm test result

**Command:**
```
python -I teams/01-data-a/tools/harm_test.py \
  --pack code-js-ts.parquet \
  --gold teams/01-data-a/gold/code-js-ts_gold.csv \
  --rules diagnosis/submissions/code-js-ts/AjaySnl/medicine.md \
  --rule B3
```

| Metric | Value |
|---|---|
| Gold documents evaluated | 204 |
| Documents changed | 0 |
| Documents dropped | 0 |
| Limit | 2 (max(1, 1% of 204)) |
| Result | **PASS** |
| Exit code | 0 |

---

### 5. Side effects

**1. `re.MULTILINE` anchor bug (fixed in this version).**  
The previous version used `re.compile(r'^...', re.MULTILINE)`. With that flag, `^` matches at the start of any line, not only at position 0. A document whose body contained a line starting with `<filename>…` would have had that line stripped. The fixed regex uses `\A`, which anchors exclusively to position 0 regardless of flags.

**2. StarCoder token in a string literal or comment at the document's first line.**  
If a document's very first line is a JavaScript string or comment that begins with the token text — for example, if a file starts with `const marker = '<filename>'` — the prefix regex would NOT match (the line starts with `const`, not `<filename>`). The medicine is safe in this respect. However, if a file starts with a bare `<filename>src/utils.js` line for reasons other than StarCoder preprocessing, that line would be stripped. This is considered benign: such a line would not be valid JavaScript.

**3. `<EMAIL>` in a test that validates the literal string `<EMAIL>`.**  
Document `ec27a58ce8941db1` uses `<EMAIL>` as an argument to a "Different" rule validator:  
`rule.passes('<EMAIL>', { primary_email: '<EMAIL>' })`  
After applying `fix_b3()`, both occurrences become `user@example.com`. For this specific test, the semantics are preserved: the "Different" rule compares input against `primary_email`; when both are the same value, the rule fails and `toBeFalsy()` still passes. However, for any test that checks whether the input is a **valid email address**, the replacement changes the outcome: `<EMAIL>` is not a valid email (so a validator would reject it), while `user@example.com` is a valid RFC 5321 address (so a validator would accept it). Such tests would change from passing to failing after the fix. This is a **known side effect** that cannot be avoided without knowing the full semantics of the test.

**4. `<EMAIL>` placeholder choice.**  
The old placeholder `[email protected]` was **not** RFC 5321 valid: the local part `[email protected]` contains brackets that are only valid inside a quoted string. The replacement `user@example.com` uses the IANA-reserved `example.com` domain (RFC 2606) and is syntactically valid. This reduces the risk of the placeholder being rejected by email-format validators.

**5. `<NAME>` in JSX-like angle-bracket syntax.**  
`<NAME>` could in theory be interpreted as a JSX element. However, JSX component names must begin with an uppercase letter; `<name>` would be a native DOM element, and `<NAME>` in all-uppercase does not correspond to any standard HTML tag or common JSX convention. The replacement `[AUTHOR]` introduces square brackets that are not valid JSX syntax, but since the surrounding context is a JSDoc comment block (`/** Copyright (c) 2020 <NAME> */`), this is acceptable: the comment is not parsed as JSX.

**6. Loss of file-path and star-count context.**  
The `<filename>` and `<gh_stars>` prefixes encode the original file path and GitHub star count. Stripping them removes this context. This is intentional: the signals were not part of the original file content, and V5 should not learn to generate them.

**7. Prefix quantifier limit.**  
The regex allows up to five consecutive metadata lines (`{1,5}`). If a rare document has more than five such lines, the sixth and beyond are preserved. Adjust the quantifier if a higher-count prefix format is observed in the full dataset.

**8. `OTHER_GHOST_RE` removes chat-template tokens globally, including from string literals and comments.**  
`OTHER_GHOST_RE` does not check whether a ghost token appears inside a JavaScript string literal, template string, or comment. Code that stores or documents chat-template token names as string values — for example, a library that parses or formats LLM prompts — will have those strings altered. This is intentional: DISEASES.md states that "a ghost marker in pre-training text teaches the model to write our special tokens as plain text", with no exception for string or comment contexts. No documents in the first-150 pack sample contained `<|im_start|>` or other chat-template tokens in any context; this side effect is low-risk for the `code-js-ts` pack.

---

*Medicine sheet: B3 and E1 documented. Only B3 (258 occurrences) and E1 (11 confirmed, 1 B3-only reclassification) qualify at the > 5-occurrence threshold. E3 has 1 occurrence — below threshold.*

---

## Medicine 2 — E1: Minified or generated code

### 1. Disease

**Disease:** E1

**Count in pack:** 11 confirmed E1 documents (one document initially labelled E1 was reclassified as B3-only after investigation; see labels.csv for `e6e3d412559d3d91`)

**Description:** Minified bundles and compiler-generated JavaScript/TypeScript files. DISEASES.md definition: "one very long line; 'auto-generated, do not edit'". These files cannot be meaningfully cleaned — the original source is not present. Training on them would teach the model to produce minified or compiler-generated output patterns.

**Detection tiers:**

| Tier | Signal | Example |
|---|---|---|
| T1 | Autogenerated notice in the leading `/* */` block comment | AutoRest, Hardhat, ethers.js ABIs |
| T2a | Any line ≥ 500 chars | Minified bundles |
| T2b | Any line ≥ 300 chars + `//# sourceMappingURL=*.{js,ts}.map` at line start | Compiled TypeScript with source map |
| T3 | Webpack bootstrap banner | `module.exports = /******/ (function(modules)` |
| T4 | `Object.defineProperty(exports, "__esModule", …)` + compiler-specific helper | TypeScript/Babel compiler output |

---

### 2. Medicine

**Rule in words:** Drop the document. Minified or compiler-generated code cannot be meaningfully cleaned; the original source is absent.

**Rule in code:**

```python
import re

_SC_LINE = r'<(?:reponame|filename|gh_stars)>[^\n]*\n?'
_STARCODER_PREFIX_RE = re.compile(r'\A(?:' + _SC_LINE + r'){1,5}')

_LEADING_BLOCK_RE = re.compile(r'\A\s*/\*+.*?\*/', re.DOTALL)
_AUTOGEN_RE = re.compile(
    r'autogenerated\s+file'
    r'|this\s+file\s+was\s+autogenerated'
    r'|code\s+generated\s+by.*?will\s+be\s+lost\s+if.*?regenerated',
    re.IGNORECASE | re.DOTALL,
)

_LONG_LINE_RE = re.compile(r'.{500,}')

_MOD_LINE_RE = re.compile(r'.{300,}')
_SOURCEMAP_LINE_RE = re.compile(
    r'^\s*//\s*#\s*sourceMappingURL=\S+\.(?:js|ts)\.map',
    re.IGNORECASE | re.MULTILINE,
)

_WEBPACK_RE = re.compile(
    r'module\.exports\s*=\s*\n?/\*+/\s*\(function\(modules\)',
    re.MULTILINE,
)

_CC_ESMOD = r'[^/*"\'' + r'`\n]'

_ESMODULE_RE = re.compile(
    r'^' + _CC_ESMOD + r'*Object\.defineProperty\s*\(\s*exports\s*,\s*["\']__esModule["\']',
    re.MULTILINE,
)

_INTEROP_RE = re.compile(
    r'^' + _CC_ESMOD + r'*_interopRequireDefault\s*\(\s*require\s*\('
    r'|^' + _CC_ESMOD + r'*function\s+_interopRequireDefault\s*\(',
    re.MULTILINE,
)

_JSX_RUNTIME_RE = re.compile(
    r'^' + _CC_ESMOD + r'*\bjsx_runtime_1\s*=\s*require\s*\('
    r'|^' + _CC_ESMOD + r'*\bjsx_runtime_1\.\w+\s*\(',
    re.MULTILINE,
)

_TSLIB_RE = re.compile(
    r'^' + _CC_ESMOD + r'*\btslib_1\s*=\s*require\s*\('
    r'|^' + _CC_ESMOD + r'*\btslib_1\.__\w+\s*\(',
    re.MULTILINE,
)

_TSCLASS_RE = re.compile(
    r'^' + _CC_ESMOD + r'*var\s+(\w+)\s*=\s*\(\s*function\s*\(\s*\)\s*\{'
    r'.*?function\s+\1\s*\('
    r'.*?return\s+\1\b'
    r'.*?\}\s*\(\s*\)\s*\)',
    re.DOTALL | re.MULTILINE,
)

_SOURCEMAP_HELPER_RE = re.compile(
    r'^\s*//\s*#\s*sourceMappingURL=',
    re.MULTILINE,
)

def drop_e1(text: str) -> bool:
    effective = _STARCODER_PREFIX_RE.sub('', text, count=1)
    m = _LEADING_BLOCK_RE.match(effective)
    if m and _AUTOGEN_RE.search(m.group()):
        return True
    if _LONG_LINE_RE.search(effective):
        return True
    if _MOD_LINE_RE.search(effective) and _SOURCEMAP_LINE_RE.search(effective):
        return True
    if _WEBPACK_RE.search(effective):
        return True
    if _ESMODULE_RE.search(effective) and (
        _INTEROP_RE.search(effective)
        or _JSX_RUNTIME_RE.search(effective)
        or _TSLIB_RE.search(effective)
        or _TSCLASS_RE.search(effective)
        or _SOURCEMAP_HELPER_RE.search(effective)
    ):
        return True
    return False
```

**Known false-positive scenarios (documented, not resolvable without a parser):**

The Tier-4 line-prefix guard `[^/*"'\`\n]*` filters identifiers appearing after `/`, `*`, `"`, `'`, or `` ` `` **on the same line**. It does not resolve two cases that require a JavaScript parser:

1. Bare-text `/* */` block comment interiors with no leading `*` per line (tests P8, Q5, Q9 in the v6 test suite).
2. Identifiers on interior lines of multiline template literals (tests R1–R5).

None of the 204 gold documents triggered these scenarios (0 false positives in the official test).

---

### 3. Action

**Action:** drop

Drop the document. The underlying source code is not present. The document cannot be meaningfully cleaned.

**Interaction with B3:** When B3 co-occurs with E1, this rule takes precedence. The document is dropped. The `drop_e1()` function strips any StarCoder prefix internally before detection.

---

### 4. Harm test

#### 4a. Validation against labelled E1 documents

| doc_id | drop_e1 result | Detection tier |
|---|---|---|
| `0c10e83429b075c5` | True (drop) | T1 |
| `3b8592acb706fa75` | True (drop) | T2b |
| `5e36e510c966759b` | True (drop) | T3 |
| `748d8d68086d6405` | True (drop) | T4 |
| `7edec6fc57a3a792` | True (drop) | T2a |
| `82221f225ca38f48` | True (drop) | T1 |
| `981b0586c9ab0fb7` | True (drop) | T4 |
| `991e567591fcf611` | True (drop) | T1 |
| `e6e3d412559d3d91` | **False (keep)** | NONE — B3-only, reclassified |
| `e8483df9bbdbd7f3` | True (drop) | T2a |
| `e91eca5bfe735229` | True (drop) | T4 |
| `f348c1a155dff382` | True (drop) | T2a |

`e6e3d412559d3d91` was initially labelled E1 but reclassified as B3-only after investigation. Its "do not edit" phrase appears inside a JavaScript template literal in a generator script, not in a file-level autogenerated notice. The document has zero compiler-output signals.

**11/11 genuine E1 documents correctly classified for dropping. 1/1 reclassified document correctly retained.**

#### 4b. Official harm test result

**Command:**
```
python -I teams/01-data-a/tools/harm_test.py \
  --pack code-js-ts.parquet \
  --gold teams/01-data-a/gold/code-js-ts_gold.csv \
  --rules diagnosis/submissions/code-js-ts/AjaySnl/medicine.md \
  --rule E1
```

| Metric | Value |
|---|---|
| Gold documents evaluated | 204 |
| Documents changed | 0 |
| Documents dropped | 0 |
| Limit | 2 (max(1, 1% of 204)) |
| Result | **PASS** |
| Exit code | 0 |

---

## Audit coverage notes

The official taxonomy (DISEASES.md) lists 37 disease codes across groups A–H. The first-150 diagnosis systematically checked the following codes:

| Code | Method | Finding |
|---|---|---|
| A1 | Character scan, all 500 docs | 1 doc |
| A2 | Character scan, all 500 docs | 0 docs |
| A4 | U+FFFD scan, all 500 docs | 0 docs |
| B3 | GHOST_RE regex scan, all 500 docs | 258 docs |
| E1 | TypeScript compiler-signal regex + line-length heuristic + manual inspection | 12 docs |
| E3 | Secret-pattern regex (type+offset only; no values recorded) | 1 doc |
| H1 | MD5 fingerprint comparison across all 500 docs | 0 duplicates |

The following codes were **not** checked systematically:

- **A3** (mojibake): Broad pattern scan found 0 occurrences in first 500 chars of any of the 500 documents.
- **A5, A6** (wrong normalisation form, mixed script): Not checked. Unlikely in GitHub JavaScript/TypeScript source.
- **B1, B2** (HTML entities, raw HTML tags): Not checked. JSX/TSX legitimately contains HTML-like syntax; false-positive rate would be high without a parser.
- **B4, B5** (template junk in prose, broken Markdown/LaTeX): Not applicable to a code pack.
- **C1–C5** (boilerplate, repeated lines, truncation, joined docs, spam): C3 checked heuristically (last-char scan, 0 suspects). C4 not checked. Others not applicable to code.
- **D1–D5** (language/script issues): Not applicable to JS/TS code pack.
- **E2** (data blobs): Not specifically checked; long-line heuristic in E1 scanner captures the most obvious cases.
- **E4** (repeated licence headers): Not checked systematically; two docs had 2 licence phrases but both were single-header files.
- **E5** (broken encoding in code): Broad mojibake scan found 0 occurrences.
- **E6** (not code): Not checked; all documents originate from `bigcode/starcoderdata` code corpus.
- **F1** (personal data): Email scan found 0 real email addresses (all `<EMAIL>` tokens classified as B3). Phone numbers, addresses, and other PII not checked.
- **F2, F3** (benchmark leakage, harmful content): Not checked; would require human judgment.
- **G1–G4** (Indic script damage): Not applicable to a JS/TS pack.
- **H2** (near-duplicates): Not checked. Same-text-length pairs in the full 500 had no candidates flagged by MD5 (0 exact duplicates); near-duplicate comparison not performed.
- **H3** (cross-source duplicates): Not checked.

**Conclusion:** The diagnosis is comprehensive for A1, A2, A4, B3, E1, E3, and H1 across all 500 documents. The remaining codes are either inapplicable to the JavaScript/TypeScript code-pack format, were ruled out by targeted checks, or remain unaudited. The submission does not claim comprehensive coverage of the full 37-code taxonomy.
