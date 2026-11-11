# Medicine sheet: cadj-commits (pradeep-kumar-gs)

Built from 500 labelled rows of 500 documents. One section for each disease labelled in more than 5 documents.

## Medicine 1: F1

1. **Disease:** F1, 43 documents in this pack. Examples: `e0c1e30626b9b1ff` (at line 31; at line 60); `6454d40260da86f0` (at line 23; at lines 48-49; at lines 22-23); `49b151d5092e2af4` (at lines 25-26; at lines 63-64; at lines 62-63).
2. **Medicine:** Replace real-looking email addresses with <EMAIL>; example.com/test/localhost stay.

   ```python
   def fix_emails(text: str) -> str:
       """F1: replace real-looking email addresses with a placeholder (example.com and test addresses stay)."""
       email = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])")
       keep = re.compile(r"(?i)@(?:[\w-]+\.)*(?:example\.(?:com|org|net)|test|invalid|localhost)$")
       return email.sub(lambda m: m.group(0) if keep.search(m.group(0)) else "<EMAIL>", text)
   ```

3. **Action:** fix the text.
4. **Harm test:** gold set of 413 documents: 1 changed, 0 dropped (0.2%). **PASS** (limit 1%).
5. **Side effects:**
   - Email-parsing tests lose their sample addresses.
   - Organisation addresses (a project's security or support mailbox) are replaced too.
   - Misses 2 of the 43 documents you labelled F1 (e.g. `d6617dadff45989c`, `1ed9b4ca0577b614`): those need a hand fix or a better rule.
   - Also changes 4 labelled document(s) you did not mark F1 (e.g. `47bb35e905ade74d`, `bb55c9242d2f7e4f`, `cd54c02ce8f0a908`): check them.

## Medicine 2: E4

1. **Disease:** E4, 31 documents in this pack. Examples: `e08f880ce9aa8920` (/* * Licensed under the Apache License, Version 2.0 (the "License"); * you may not use this file except in compliance with the License. * You may obtain a copy of the License at * * http://www.apache.org/licenses/LICENSE-2.0 * * Unless required by applicable law or agreed to in writing, software * distributed under the License is distributed on an "AS IS" BASIS, * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. * See the License for the specific language governing permissions and * limitations under the License. */ packa at lines 53-66); `97dcab67c73a7eaa` (/* Copyright 2011-2017 Frederic Langlet Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. you may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License. */ at lines 42-55); `a20a794c2c45c020` (/* * Copyright 2020 ThoughtWorks, Inc. * * Licensed under the Apache License, Version 2.0 (the "License"); * you may not use this file except in compliance with the License. * You may obtain a copy of the License at * * http://www.apache.org/licenses/LICENSE-2.0 * * Unless required by applicable law or agreed to in writing, software * distributed under the License is distributed on an "AS IS" BASIS, * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. * See the License for the specific language governing permissions and * limitations under the License. */ at lines 54-68; * you may not use this file except in compliance with the License. * You may obtain a copy of the License at * * http://www.apache.org/licenses/LICENSE-2.0 * * Unless required by applicable law or agreed to in writing, software * distributed under the License is distributed on an "AS IS" BASIS, * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. * See the License for the specific language governing permissions and * limitations under the License. at lines 9-22).
2. **Medicine:** Remove the leading comment block when it contains licence text, in old and new contents.

   ```python
   def fix_licence_header(text: str) -> str:
       """E4: remove a leading comment block that contains licence text, from every code section."""
       def strip(s: str) -> str:
           off, block = _leading_comment(s)
           if off < 0 or not LICENCE_RE.search(block):
               return s
           return s[:off] + s[off + len(block):].lstrip("\n")
       return _per_section(text, strip, CODE)
   ```

3. **Action:** fix the text.
4. **Harm test:** gold set of 413 documents: 16 changed, 0 dropped (3.9%). **FAIL** (limit 1%).
5. **Side effects:**
   - A module docstring that mentions a licence is removed with its other text.
   - Licence attribution must be kept in metadata (meta.license), not lost.
   - Also changes 27 labelled document(s) you did not mark E4 (e.g. `f1655eb8394db886`, `d6617dadff45989c`, `8c10cefe5e1ec99b`): check them.

