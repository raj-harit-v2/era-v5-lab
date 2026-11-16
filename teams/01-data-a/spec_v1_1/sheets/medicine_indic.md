# medicine_indic: the Indic family's Spec v1.1 medicine (Data B)

**Draft, 13 Nov.** This sheet carries the Indic family's one new disease in `NEW_DISEASES.md` into the Spec v1.1 consolidated sheet (`specv1_1_additions.md`, and through it the combined `specv1_1.md`), in the same form as the Data A sheets. The rule is Data B's.

- **Source:** oddjoker91's `diagnosis/submissions/ind-te-sangraha-v/oddjoker91/medicine.md`, Medicine 1 (theschoolofai/era-v5-lab#177). Data B listed it for Spec v1.1 in theschoolofai/era-v5-lab#216.
- **The code:** Data B's function `medicine_c6` is copied **unchanged**. Only the block's header lines (`RULE_ID`, `CODE`, `ORIGIN` …) and a `pack_id` check are added around it, the way spec v1 wrapped its source rules. So the block loads with `harmtest/harm_test.py`, and the rule runs only on the pack where the disease was found.
- **Not here:** Medicines 2 and 3 of the same sheet (C1 and C2) are spec v1 codes, not new diseases, so they stay in Data B's sheet.
- **Harm test:** Data B's `teams/02-data-b/tools/harm_test_indic.py`, which adds the joiner (ZWJ/ZWNJ) and normal-form audits that Indic text needs.

| # | ID | disease | action | stage | ind-te-sangraha-v | reading docs treated |
|---|---|---|---|---|---|---|
| 1 | `DB-C6-001` | C6 inconsistent punctuation: runs of dots | fix | 10 | 2/80 FAIL; both are gold contradictions, so 0/78 PASS without them (13 Nov) | 144 of 161 C6-labelled docs (Data B's diagnosis labels, 500 docs) |

## 1. `DB-C6-001` · C6 inconsistent punctuation: runs of dots · fix · stage 10

1. **Disease:** C6, the Indic family's code. TSAI ruled on 5 Nov that C6 goes into the spec. Punctuation is broken up or repeated: runs of two or more dots, with or without spaces between them, where one full stop or a standard `...` was meant. Found in ind-te-sangraha-v by one reader (oddjoker91, #177): 161 of 500 docs (32%). Examples:
   - `2a0cfe90fd36e4ed`: `. .`
   - `11960d16258cd4b5`: `..`
   - `05fa567dfc849e6b`: `. . .`
2. **Medicine:** turn a run of two or more ASCII dots, including spaces or tabs between them, into exactly `...`. It never joins dots across a line break. A single dot and Unicode `…` stay. An existing `...` is matched but stays the same. Data B's separate decimal repair (`3. 67` → `3.67`) is deferred and isn't here: together with this rule it changed 2 of 18 gold docs and failed.

```python
RULE_ID = "DB-C6-001"
CODE = "C6"  # the Indic family's code (TSAI ruling, 5 Nov)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "ind-te-sangraha-v"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "ind-te-sangraha-v"  # oddjoker91's sheet, theschoolofai/era-v5-lab#177, Medicine 1
AUTHOR = "oddjoker91"
# ---- Data B's medicine, copied unchanged from diagnosis/submissions/ind-te-sangraha-v/oddjoker91/medicine.md ----
import re
_DOT_RUN = re.compile(r'\.(?:[^\S\r\n]*\.)+')
def medicine_c6(text):
    return _DOT_RUN.sub('...', text)
# ---- end of Data B's medicine ----


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c6(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix; it never drops a doc. **Runs on:** ind-te-sangraha-v. **Docs it treats:** 144 of the 161 C6-labelled docs in Data B's diagnosis. On the 500-doc diagnosis pack, 241 docs change.
4. **Harm test** (Data B's `harm_test_indic.py`):
   - **ind-te-sangraha-v, 13 Nov (aneeshads), on the 80-doc gold:** 2/80 changed, 0 dropped: **FAIL**, over the limit of 1. The joiner and normal-form audits pass. C6 → C1 → C2 in order is also 2/80; C1 and C2 change none. Report: `results/sheets/indic_sangraha-v_harm.md`. The pack file is `ind-te-sangraha-v.parquet`, the 500 docs that were read; the Week-1 copy in `Cap1-packs` holds none of the 80 gold docs.
   - **The 2 docs are gold contradictions:** `85644a4840025b6f` has `..` after మాట్లాడుతూ ("speaking"), before a quote, and `01418489e7410bdf` has `..` after మరణిస్తే ("if they die"). Both readers (oddjoker91 and sreekanthzipsy) marked the docs clean. But oddjoker91 labelled a bare `..` as C6 in other docs of the pack: 23 C6 labels point at a 2-character span. Vijay agreed to marking gold contradictions, so they are left out of the count: **0/78, PASS**. They are to be re-read at the next gold refresh.
   - **A narrower version was tried and not taken (13 Nov):** leaving a bare `..` alone, it passed at 0/80, and changed none of the sangraha-s gold docs. But it treated only 102 of the 161 labelled docs, so Data B's function stays unchanged.
   - **ind-te-sangraha-v, 9 Nov (Data B), on the old 18-doc gold:** 1/18 changed (`85644a4840025b6f`), 0 dropped. That is PASS under the 1-doc allowance, and the joiner and normal-form audits pass. C6 → C1 → C2 in order also passes at 1/18.
   - **The sangraha-s packs, 13 Nov (aneeshads):** Data B's function, which has no pack check, ran on every gold doc and changed none. That is 0/24 on ind-hi-sangraha-s, 0/22 on ind-kn-sangraha-s and 0/24 on ind-te-sangraha-s, all PASS with the audits passing. ind-ta-sangraha-s has no gold set. Report: `results/sheets/indic_sangraha-s_harm.md`. With this sheet's pack check, the rule is off on those packs.
5. **Side effects:**
   - Dots used on purpose are changed, such as four dots for a full stop plus an ellipsis (`....` becomes `...`).
   - A bare `..` used as a pause in Telugu news writing becomes `...`, as in the 2 gold contradictions. Whether that `..` is a disease is open for Data B.
   - Code, paths and other structured text may use dots meaningfully.
   - It doesn't fix every C6 case, or make an affected doc clean.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Author: oddjoker91 (Data B). Source: theschoolofai/era-v5-lab#177, listed for v1.1 in theschoolofai/era-v5-lab#216. Carried into this sheet by aneeshads, 13 Nov.
