# Medicine sheet: code-java (riyaagrahari)

Pack: 500 Java files from `bigcode/starcoderdata:java`. Verdicts: 163 clean, 321 fix, 16 drop.

**About the harm tests.** The official Java gold set is not in the repository, so I could not run on it. As a stand-in I ran each medicine on (a) the 163 rows of this pack that I labelled `clean`, and (b) 17 independent `.java` files from my own machine. Both runs are reported below. Please re-run on the official gold set before merging any medicine into the pipeline. The pass limit is 1% of the gold set, which is about 2 documents of 200.

Disease counts in this pack (documents): B3 250, B4 82, E4 73, A2 44, E1 14. A1 1, A4 2, C1 1, E3 1, F1 2 are each five or fewer, so they have no full medicine (see the end).

## Medicine 1: B3 ghost special tokens

1. **Disease:** B3, 250 documents (50%). The StarCoder metadata tokens `<reponame>`, `<filename>` and `<gh_stars>` sit at the start of the text as plain characters. Examples: `d0947d80d45f7ce3` (`<filename>` at offset 0), `c9eb2d8e4f9cacde` (`<reponame>` at offset 0), `4b761af28be90423` (`<filename>` at offset 0, `<gh_stars>` at offset 35). No other chat or FIM tokens (`<|im_start|>`, `[INST]`, `<fim_*>`) were found anywhere in the pack.
2. **Medicine:** the tokens appear only in a run at the start of the file, ending with a newline. Remove that run.
   ```python
   import re
   TOK = re.compile(r'^(?:<(?:reponame|filename|gh_stars)>[^\n<]*)+\n?')
   def fix_b3(text): return TOK.sub('', text, count=1)
   ```
   The repository, path and star count can be kept in metadata columns if needed.
3. **Action:** fix the text.
4. **Harm test:** clean rows of this pack (n=163): 0 changed, 0 dropped. Local Java files (n=17): 0 changed, 0 dropped. It acted on all 250 labelled documents.
5. **Side effects:** the regex is anchored to the start, so a file that legitimately contains these strings later (for example a Java file that parses StarCoder data) is not touched. A file whose first real line starts with `<reponame>` would lose it. None was seen. The tokens carry repo names, so a metadata copy should be made before removal.

## Medicine 2: B4 PII-redaction placeholders left in text

1. **Disease:** B4, 82 documents. An earlier PII filter replaced names, emails, passwords and keys with literal placeholders, and they remain in comments and strings. The model would learn to write them. Examples: `13a397d8bedc6210` (`<NAME>` at offset 159, `<EMAIL>` at offset 167), `8c9a9aa845f91a2c` (a `<PASSWORD>` placeholder in a string), `4b761af28be90423` (`<NAME>` at offset 218).
2. **Medicine:** remove the four placeholder strings.
   ```python
   import re
   PH = re.compile(r'<(?:NAME|EMAIL|PASSWORD|KEY)>')
   def fix_b4(text): return PH.sub('', text)
   ```
3. **Action:** fix the text. A stronger option is to replace each placeholder with a plausible fake value, which keeps the grammar of the comment intact.
4. **Harm test:** clean rows of this pack (n=163): 0 changed, 0 dropped. Local Java files (n=17): 0 changed, 0 dropped. It acted on all 82 labelled documents.
5. **Side effects:** only these four names are matched. Generic type parameters such as `Set<UUID>`, `IVL<REAL>`, `<TYPE_OUTPUT>` are not touched. A `<KEY>` or `<NAME>` used as a real type parameter in Java would be removed and break the code. I saw none. Removing the placeholder can leave an empty string such as `password("")`, which is harmless.

## Medicine 3: A2 carriage returns (CRLF)

1. **Disease:** A2, 44 documents. The only control character in the pack is CR (U+000D) in Windows line endings. The viewer shows it as a hidden control character. Examples: `e0ebe203093970dc` (38 CR, first at offset 17), `7fc99d2b6e1e3d08`, `1a1a1d7ab0bf9188` (177 CR).
2. **Medicine:** turn CRLF, and any lone CR, into LF.
   ```python
   def fix_a2(text): return text.replace('\r\n', '\n').replace('\r', '\n')
   ```
3. **Action:** fix the text.
4. **Harm test:** clean rows of this pack (n=163): 0 changed, 0 dropped. Local Java files (n=17): 0 changed, 0 dropped. It acted on all 44 labelled documents.
5. **Side effects:** Windows files in a real gold set will be changed, and that is the intended effect. A Java string literal that contains `\r` is written as an escape, not as a raw character, so code meaning is unchanged. Line numbers do not change. The medicine does not touch tab or newline.

## Medicine 4: E4 repeated licence header

1. **Disease:** E4, 73 documents. A long licence block comment sits at the top. Apache-2.0 appears in 62 files, MIT in 7 and GPL/LGPL in 4. Examples: `5655154f71365c63`, `86534a30f79557fb`, `c70422358a640e42`. Offsets are 0 in most files, or just after the token prefix.
2. **Medicine:** if the first block comment (after the token prefix and any BOM or blank lines) has at least 8 lines and names Apache, MIT or GPL, remove it. Keep the copyright holder in the metadata.
   ```python
   import re
   TOK = re.compile(r'^(?:<(?:reponame|filename|gh_stars)>[^\n<]*)+\n?')
   LIC = re.compile(r'Apache License|Licensed to the Apache|Permission is hereby granted|GNU (Lesser |Affero )?General Public License')
   def fix_e4(text):
       b = TOK.sub('', text, count=1)
       lead = len(b) - len(b.lstrip('\ufeff \r\n\t'))
       m = re.match(r'/\*.*?\*/', b[lead:], re.S)
       if m and m.group(0).count('\n') >= 7 and LIC.search(m.group(0)):
           return text[:len(text) - len(b)] + b[lead + m.end():].lstrip('\r\n')
       return text
   ```
3. **Action:** fix the text.
4. **Harm test:** clean rows of this pack (n=163): 0 changed, 0 dropped. Local Java files (n=17): 0 changed, 0 dropped. It acted on 72 of the 73 labelled documents. One labelled file uses a header style the regex misses.
5. **Side effects:** on a real corpus this changes every licensed file, so it only passes the 1% limit if the gold set has no licence headers. Removing licence text is a legal question for the licence team, because some licences require the notice to stay with the code. Keep a metadata copy. The 8-line floor keeps short `Copyright (c) ...` lines.

## Medicine 5: E1 generated or decompiled code

1. **Disease:** E1, 14 documents. Examples: `c6016e9ce2c607c5` ("This class was generated by ..."), `73e175e90e6e37da` (AutoRest "Code generated by"), `905fe4685c78e088` (Android `R.java`, "AUTO-GENERATED FILE. DO NOT MODIFY."). Others are decompiler output (Jad, Procyon, jadx) and Scala-to-Java stubs whose every body is `throw new RuntimeException`.
2. **Medicine:** drop the document if a generator or decompiler marker appears in the text.
   ```python
   import re
   GEN = re.compile(r'Decompiled by (Jad|Procyon)|Code generated by [^\n]{0,60}Generator|AUTO-GENERATED FILE'
                    r'|generated by a tool and any changes will be overwritten|Automatically generated - do not modify'
                    r'|This class was (automatically )?generated by|auto generated by the swagger'
                    r'|This is a generated file\. Not intended for manual editing')
   def drop_e1(text): return bool(GEN.search(text))
   ```
3. **Action:** drop the document.
4. **Harm test:** clean rows of this pack (n=163): 0 changed, 0 dropped. Local Java files (n=17): 0 changed, 0 dropped. It acts on 10 of the 14 labelled documents. The other 4 have no text marker (stub files, jadx output, obfuscated classes) and need a structural rule.
5. **Side effects:** the IDE comment `// TODO Auto-generated method stub` and the annotation `@GeneratedValue` are not matched, and these are normal hand-written code. A hand-written file that quotes a generator marker in a comment would be dropped. The marker list is short, so coverage is incomplete and generator names change.

## Diseases found five times or fewer

No full medicine is required. For the record:

- A1: 1 file (`beae2c42d8a34ccc`, BOM U+FEFF at offset 63, after the token prefix). Remove U+FEFF.
- A4: 2 files (`912c53fa71c7d9ad`, 6 U+FFFD; `9b95cf192922d106`, 10 U+FFFD). The bytes are lost and cannot be recovered. The damage is in comments and author lines, so the code still works.
- C1: 1 file (`1227540794647c4d`, scraped LeetCode text "sample 1 ms submission" and underscore rules).
- E3: 1 file (`76f01e2eb8018be6`, an API key at offset 1011 and an API token at offset 1223). Value not copied. Drop the file.
- F1: 2 files (`1a1a1d7ab0bf9188`, phone number at offsets 40 and 1499; `8e1a4d379dd64269`, a test file of customer contact records).

## Things I decided not to label

- Javadoc entities such as `&lt;` and `&quot;` (B1) and `<p>` or `<pre>` tags (B2): normal and needed in Javadoc.
- Chinese, Korean, French and Russian comments: not a disease in code.
- `@author` names with no email or phone: not labelled F1.
- LeetCode problem text in comments: not a benchmark test set, so not F2.
- No H1/H2 duplicates, no truncated files and no joined files were found (checked by exact match, 6-token shingle overlap, brace balance and package-line count).
