# Medicine sheet: code-go

Pack: **500 Go records**. Harm tests run on **31 October 2026** with the supplied g1-harm-test runner and `code-go_gold.csv`: **163 clean documents with two listed readers**. The permitted limit is `max(1, floor(0.01 × 163)) = 1` changed or dropped gold document. The original pack was not modified.

## Gold-set harm-test summary

| Medicine | Gold documents tested | Changed | Dropped | Errors | Affected | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| B3 | 163 | 0 | 0 | 0 | 0.00% | **PASS** |
| B4 | 163 | 0 | 0 | 0 | 0.00% | **PASS** |
| E1 | 163 | 0 | 0 | 0 | 0.00% | **PASS** |
| E2 | 163 | 0 | 0 | 0 | 0.00% | **PASS** |
| E4 | 163 | 0 | 0 | 0 | 0.00% | **PASS** |
| All five in order | 163 | 0 | 0 | 0 | 0.00% | **PASS** |

## Pack counts and medicine coverage

| Disease | Labelled records | Action | Coverage on the 500-record pack |
| --- | ---: | --- | --- |
| B3 — Dataset markers | 247 | Fix | All 247 marker lines removed. |
| B4 — PII placeholders | 43 | Fix | 41 records changed; 40 fully handled. Records 97, 293 and 364 need manual repair. |
| E1 — Generated code | 41 | Drop selected files | 12 matched automatically; 27 other drop verdicts remain manual. Retain useful generated records 113 and 125. |
| E2 — Data blobs | 8 | Drop selected files | Seven protobuf descriptor files matched; retain transaction fixture 360. |
| E4 — Repeated licence headers | 44 | Fix | All 44 matched: 39 Apache and 5 MIT. |

The medicine counts overlap because a record can carry several codes. The gold harm test measures effects on clean documents; coverage above records which labelled cases the rules handle. A document selected by both E1 and E2 is dropped once.

## Medicine 1: B3 — Dataset markers

1. **Disease:** B3; 247 labelled records.

| Record | doc_id | Offset | Exact characters |
| ---: | --- | ---: | --- |
| 3 | `2f6d4b8c8e3fcbd5` | 0 | `<reponame>` |
| 6 | `2bdf36ae14fd90fa` | 0 | `<gh_stars>` |
| 8 | `b0eed26ac2f6a1a7` | 0 | `<filename>` |

2. **Medicine:** Remove the first line when it starts with an observed StarCoder metadata marker. The value may be arbitrary. This rule applies to the known one-line wrapper format; it does not delete other text before package.

```python
import re

MARKER_LINE = re.compile(r'\A<(?:reponame|filename|gh_stars)>[^\r\n]*\r?\n')

def fix_b3(text):
    match = MARKER_LINE.match(text)
    return text[match.end():] if match else text
```

3. **Action:** Fix. The read-only check on all 500 records changed exactly the 247 labelled B3 records. No documents were dropped.

4. **Harm test:** PASS.

| Gold documents tested | Changed | Dropped | Errors | Affected | Allowed changes/drops | Result |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 163 | 0 | 0 | 0 | 0.00% | 1 | **PASS** |

5. **Side effects:** A genuine source line that begins with one of these markers could be removed. Code sharing that line would also be lost. This rule covers the three marker types present in this pack; issue and jupyter formats need separate review.

## Medicine 2: B4 — PII placeholders

1. **Disease:** B4; 43 labelled records.

| Record | doc_id | Offset | Exact characters |
| ---: | --- | ---: | --- |
| 1 | `f08e1abfa9c2ebdc` | 138 | `<EMAIL>` |
| 27 | `c05ecf8c28dd8d51` | 20 | `<NAME>` |
| 96 | `3bfbdf84356326dc` | 150 | `<KEY>` |

2. **Medicine:** Replace prior PII-cleaning placeholders only inside Go comments and string literals. In comments, use wording such as name withheld; in strings, use explicitly synthetic example values. These values do not reconstruct the original identity or credential. Leave expression/identifier placeholders, directives, runes and malformed quoted input for review. Each call computes its own positions, so an earlier B3 edit does not invalidate saved offsets.

```python
import re

def medicine_b4(text):
    # Recognize Go comments, strings and runes; a bare quote is malformed.
    token = re.compile(
        r'//[^\r\n]*|/\*[\s\S]*?\*/|"(?:\\[^\r\n]|[^"\\\r\n])*"'
        r'|`[^`]*`|\'(?:\\[^\r\n]|[^\'\\\r\n])*\'|/\*|["\'`]')
    placeholder = re.compile(r'<(?:NAME|EMAIL|KEY|PASSWORD)>')
    comments = {'<NAME>': 'name withheld', '<EMAIL>': 'email withheld',
                '<KEY>': 'key withheld', '<PASSWORD>': 'password withheld'}
    literals = {'<NAME>': 'Example User', '<EMAIL>': 'user@example.com',
                '<KEY>': 'example-key', '<PASSWORD>': 'example-password'}
    start = 0
    if re.match(r'\A<(?:reponame|filename|gh_stars)>', text):
        newline = text.find('\n')
        if newline < 0:
            return text
        start = newline + 1
    patches = []
    for match in token.finditer(text, start):
        part = match.group()
        if part in ('"', "'", '`', '/*'):
            return text  # Leave malformed lexical input for manual review.
        if part.startswith("'"):
            continue
        if part.startswith(('//go:', '// +build', '//line ', '//export ')):
            continue
        values = comments if part.startswith(('//', '/*')) else literals
        replacement = placeholder.sub(lambda m: values[m.group()], part)
        if replacement != part:
            patches.append((match.start(), match.end(), replacement))
    for begin, end, replacement in reversed(patches):
        text = text[:begin] + replacement + text[end:]
    return text
```

3. **Action:** Fix the supported comment/string occurrences. Across 500 records, 41 of the 43 labelled B4 records changed; all targeted placeholders were removed in 40. Record 97 was only partly repaired. Records 293 and 364 were left unchanged. Review all three before claiming complete B4 treatment.

4. **Harm test:** PASS.

| Gold documents tested | Changed | Dropped | Errors | Affected | Allowed changes/drops | Result |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 163 | 0 | 0 | 0 | 0.00% | 1 | **PASS** |

5. **Side effects:** Synthetic literals can alter expected test outputs, authentication examples or API behaviour. A literal HTML element named NAME could be mistaken for a placeholder. Replacements in comments preserve the fact that attribution is withheld. This is a proposed training-text repair, not proof that the resulting Go program still behaves correctly.

## Medicine 3: E1 — Generated code

1. **Disease:** E1; 41 labelled records.

| Record | doc_id | Offset | Exact characters |
| ---: | --- | ---: | --- |
| 20 | `3c4db0c3d41b7673` | 1018 | `m.ctrl.Call` |
| 145 | `91bf17319ac11223` | 922 | `protoimpl.MessageState` |
| 321 | `fe2c1445611e0cfc` | 416 | `MarshalJSONBuf` |

2. **Medicine:** Drop a document only when its generator notice is corroborated by a supported implementation pattern: protobuf machinery, MockGen controller dispatch, controller/deepcopy routines or ffjson serializers. Ignore StarCoder metadata when checking generator evidence. Keep explicit Test/Benchmark/Example functions. The rule intentionally leaves unsupported generator families for manual review; a header alone is insufficient.

```python
import re

def medicine_e1(text):
    package = re.search(r"(?m)^package\s+[A-Za-z_]\w*", text)
    if not package:
        return text
    header, body = text[:package.start()], text[package.end():]
    header = re.sub(r'\A<(?:reponame|filename|gh_stars)>[^\r\n]*\r?\n', '', header, count=1)
    if not re.search(r"generated|auto-generated", header, re.I):
        return text
    if re.search(r"(?m)^func\s+(?:Test|Benchmark|Example)\w*\s*\(", body):
        return text
    protobuf = ("protoc-gen-go" in header and
                bool(re.search(r"protoimpl\.|XXX_Unmarshal|proto\.Register(?:Type|File)|\bProtoMessage\(\)", body)))
    mock = ("MockGen" in header and "gomock.Controller" in body and
            bool(re.search(r"\.ctrl\.Call\(", body)))
    deepcopy = (bool(re.search(r"deepcopy|controller-gen", header, re.I)) and
                "DeepCopyInto(" in body and "DeepCopy()" in body)
    ffjson = ("ffjson" in header.lower() and
              "fflib.FFLexer" in body and "MarshalJSONBuf" in body)
    return ("drop", text) if any((protobuf, mock, deepcopy, ffjson)) else text
```

3. **Action:** Drop the 12 documents matched by this conservative rule: records 20, 34, 145, 174, 200, 221, 321, 347, 350, 377, 412 and 473. This does not automate all 39 workbook E1 drop verdicts. The other 27 proposed drops are outside this executable subset; their manual verdicts require implementation evidence. Records 113 and 125 remain retained, with B3 fixes. Record 13 is retained with an E4 fix and has no E1 label.

4. **Harm test:** PASS.

| Gold documents tested | Changed | Dropped | Errors | Affected | Allowed changes/drops | Result |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 163 | 0 | 0 | 0 | 0.00% | 1 | **PASS** |

5. **Side effects:** Useful generated libraries can match and be dropped. Generated tests without a conventional Test/Benchmark/Example declaration may also match. Other generator families and minified files are missed. The gold PASS applies only to this executable subset, not to every manual E1 verdict.

## Medicine 4: E2 — Embedded data blobs

1. **Disease:** E2; 8 labelled records.

| Record | doc_id | Offset | Exact characters |
| ---: | --- | ---: | --- |
| 34 | `637118880fa53f2f` | 5772 | `0x1f, 0x8b, 0x08, 0x00` |
| 145 | `91bf17319ac11223` | 23994 | `0x0a, 0x23, 0x64, 0x69` |
| 377 | `023d4d7c1524277f` | 1495 | `0x1f, 0x8b, 0x08, 0x00` |

2. **Medicine:** Drop a generated protobuf descriptor document when the protoc-gen-go notice, protobuf implementation and a descriptor byte array of at least 32 hexadecimal bytes are all present. Allow comments inside that generated array. Remove the entire selected document rather than deleting bytes required by retained code.

```python
import re

def medicine_e2(text):
    package = re.search(r"(?m)^package\s+[A-Za-z_]\w*", text)
    if not package:
        return text
    header, body = text[:package.start()], text[package.end():]
    header = re.sub(r'\A<(?:reponame|filename|gh_stars)>[^\r\n]*\r?\n', '', header, count=1)
    if "protoc-gen-go" not in header:
        return text
    if not re.search(r"protoimpl\.|XXX_Unmarshal|proto\.Register(?:Type|File)|\bProtoMessage\(\)", body):
        return text
    for descriptor in re.finditer(
            r'\b(?:fileDescriptor\w*|\w+_rawDesc)\s*=\s*\[\]byte\s*\{', body):
        payload = body[descriptor.end():].split('}', 1)[0]
        payload = re.sub(r'//[^\r\n]*|/\*[\s\S]*?\*/', '', payload)
        if re.fullmatch(r'\s*(?:0x[0-9a-fA-F]{2}\s*,\s*){32,}', payload):
            return ('drop', text)
    return text
```

3. **Action:** Drop records 34, 145, 174, 347, 377, 412 and 473. Keep record 360, whose data is a required transaction fixture; its B3 wrapper can be fixed separately. These seven selected files also match E1, so the combined run drops each only once.

4. **Harm test:** PASS.

| Gold documents tested | Changed | Dropped | Errors | Affected | Allowed changes/drops | Result |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 163 | 0 | 0 | 0 | 0.00% | 1 | **PASS** |

5. **Side effects:** A useful protobuf example may contain the same descriptor pattern and be excluded. Other data blobs, base64 and different generated descriptor formats are outside this rule. An array length alone is never sufficient to drop an ordinary fixture.

## Medicine 5: E4 — Repeated licence headers

1. **Disease:** E4; 44 labelled records: 39 Apache and 5 MIT.

| Record | doc_id | Offset | Exact characters |
| ---: | --- | ---: | --- |
| 13 | `83381a2f882bdce3` | 95 | `Permission is hereby granted` |
| 27 | `c05ecf8c28dd8d51` | 43 | `Licensed under the Apache License` |
| 58 | `312d930b2b41cf89` | 79 | `Licensed under the Apache License` |

2. **Medicine:** Recognize complete known Apache/MIT clauses inside the leading Go comment region, which may be before package or directly after it. Normalize only whitespace and comment decoration for comparison. Accept the explicitly represented URL, terminal-period and Apache wording variants. Replace the matched clauses with the matching SPDX identifier. Preserve all surrounding text, including copyright holders, other notices, build tags, generator notices and package documentation. No source IDs or gold membership are used by the rule. Unknown wording remains unchanged. The original pack and its full notices must remain associated with doc_id; this creates only a training-text view.

```python
"""E4 candidate: exact known licence clauses inside leading Go comments only."""
import re

_E4_APACHE = ('Licensed under the Apache License, Version 2.0 (the "License"); '
'you may not use this file except in compliance with the License. '
'You may obtain a copy of the License at {url} '
'Unless required by applicable law or agreed to in writing, software '
'distributed under the License is distributed on an "AS IS" BASIS, '
'WITHOUT WARRANTIES{conditions} OF ANY KIND, either express or implied. '
'See the License for the specific language governing permissions and '
'limitations under the License{period}')
_E4_MIT = ('Permission is hereby granted, free of charge, to any person obtaining a '
'copy of this software and associated documentation files (the "Software"), to deal '
'in the Software without restriction, including without limitation the rights '
' to use, copy, modify, merge, publish, distribute, sublicense, and/or sell '
'copies of the Software, and to permit persons to whom the Software is '
'furnished to do so, subject to the following conditions: '
'The above copyright notice and this permission notice shall be included in '
'all copies or substantial portions of the Software. '
'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR '
'IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, '
'FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE '
'AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER '
'LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, '
'OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.')

def _e4_patterns():
    templates = [(_E4_MIT, 'MIT')]
    for url in ('http://www.apache.org/licenses/LICENSE-2.0',
                'https://www.apache.org/licenses/LICENSE-2.0',
                'https://opensource.org/licenses/Apache-2.0'):
        for conditions in (' OR CONDITIONS', ''):
            for period in ('.', ''):
                templates.append((_E4_APACHE.format(url=url, conditions=conditions,
                                                    period=period), 'Apache-2.0'))
    return [(re.compile(re.escape(' '.join(t.split())) + r'(?!\w)'), licence)
            for t, licence in templates]

def _e4_groups(text):
    # Scan actual leading syntax, including comments directly after package.
    prefix = re.match(r'\A<(?:reponame|filename|gh_stars)>[^\r\n]*\r?\n', text)
    pos = prefix.end() if prefix else 0
    groups, current, package_seen = [], [], False
    while pos < len(text):
        white = re.match(r'\s*', text[pos:]); pos += white.end()
        if text.startswith('//', pos):
            end = text.find('\n', pos)
            end = len(text) if end < 0 else end
            current.append((pos, end, 'line')); pos = end
        elif text.startswith('/*', pos):
            end = text.find('*/', pos + 2)
            if end < 0:
                return []  # Unterminated header is left for manual review.
            current.append((pos, end + 2, 'block')); pos = end + 2
        else:
            if current: groups.append(current); current = []
            package = re.match(r'package\s+[A-Za-z_]\w*\b', text[pos:])
            if package_seen or not package:
                break
            package_seen = True; pos += package.end()
    if current: groups.append(current)
    return groups if package_seen else []

def _e4_patches(text):
    patches = []
    patterns = _e4_patterns()
    for group in _e4_groups(text):
        chars, offsets, styles = [], [], []
        for start, end, style in group:
            a, b = start + 2, end - 2 if style == 'block' else end
            pos = a
            for line in text[a:b].splitlines(keepends=True):
                decoration = re.match(r'[ \t]*\*(?:[ \t]|$)', line) if style == 'block' else None
                skip = decoration.end() if decoration else 0
                for j, ch in enumerate(line[skip:], pos + skip):
                    if ch.isspace():
                        if chars and chars[-1] != ' ':
                            chars.append(' '); offsets.append(j); styles.append(style)
                    else:
                        chars.append(ch); offsets.append(j); styles.append(style)
                pos += len(line)
            if chars and chars[-1] != ' ':
                chars.append(' '); offsets.append(b); styles.append(style)
        normalized = ''.join(chars)
        for pattern, licence in patterns:
            for match in pattern.finditer(normalized):
                a, b = offsets[match.start()], offsets[match.end() - 1] + 1
                if styles[match.start()] != styles[match.end() - 1]:
                    continue
                if any(not (b <= x or a >= y) for x, y, _ in patches):
                    continue
                patches.append((a, b, licence))
    return sorted(patches)

def medicine_e4(text):
    for start, end, licence in reversed(_e4_patches(text)):
        text = text[:start] + 'SPDX-License-Identifier: ' + licence + text[end:]
    return text
```

3. **Action:** Fix retained documents. All 44 labelled headers are matched, with no matches outside those 44 in the 500-record pack. Executable tokens, Go directives and surrounding text were preserved; all 44 outputs were stable on a second application. Existing E1/E2 drop decisions take precedence over an E4 text fix.

4. **Harm test:** PASS.

| Gold documents tested | Changed | Dropped | Errors | Affected | Allowed changes/drops | Result |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 163 | 0 | 0 | 0 | 0.00% | 1 | **PASS** |

5. **Side effects:** Unknown licences and modified clauses are intentionally missed. A package comment quoting the entire known licence as a meaningful example could match. SPDX is shorthand and does not preserve the full original notice; retain the original source archive and provenance separately. The checks establish preservation of Go tokens and directives, not compilation or behavioural equivalence. They do not justify removing all text before package.
