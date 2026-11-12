# medicine.md — ind-mr-fw2 (handle: vpw)

Prescriptions for every disease found **≥ 5×** across the 500-doc pack. Counts are
from `labels.csv` (500 rows: **269 clean, 200 fix, 31 drop**).

## Harm-test protocol

Updated 3 Nov after TSAI ruled on #211 (a harm result counts only on today's gold
set of the rule's own pack). The rules for **C2, C3, C5 and B4** are now code in
this file: each one is a `medicine_<code>(text)` function in a python block under a
`**Disease:** <code>` line, and returns the new text, `True` (drop) or the same text
(keep). Run with Data B's tool:

`python3 teams/02-data-b/tools/harm_test_indic.py --medicine diagnosis/submissions/ind-mr-fw2/vpw/medicine.md --pack ind-mr-fw2.parquet --gold-dir teams/02-data-b/gold`

The gold set is `teams/02-data-b/gold/ind-mr-fw2_gold.csv` (142 docs; a rule may
change or drop at most 1 of them: 1% or 1 document, whichever is more). The gold
set is two-reader, so it replaces my single-reader proxy for the result table
below. The older per-rule figures in each section (/269) are against my own 269
clean docs and are kept as the second check.

**C1 and C4** need a cross-document index (a chunk that recurs in >= 4 docs), so
they cannot run as a per-document rule and stay described in words. **F1** is
covered by Data A's shared F1 rule. **D3** is label-only, **D4** and **D5** are
review-only, **G2** and **A5** are not submitted as code here.

Rules are the exact regex/predicate the fixer would run. For F1, evidence is
type + offset only — the value is never copied, hex left empty.

---

## C1 — boilerplate / chrome contamination — **165**

Site furniture welded onto article text: inline teasers (`हेही वाचा`, `हे ही वाचा`,
`देखील वाचा`, `आणखी वाचा`, `नक्की वाचा`), share CTAs (`Whatsapp स्टेटस, Facebook,
Instagram`), CMS leaks (`Web Title`, `This News has been`), footers (`Copyright`,
`आपल्या शहरातील ताज्या बातम्या … डाउनलोड करा`, `Read the latest Marathi news …
Saam TV`, `Read Goa news in Marathi`), `View this post on Instagram`.

Examples: `9c9cb2366bc14d88` ('This News has been'), `d40a6e0c632b3dd0` (e-paper
footer @0 + Copyright), `a84ec9a0a34a3f12` (city-news chunk + Copyright tail).

**Scope refinement (this pass):** C1 is site *chrome*, not every non-prose line.
An author/editor **byline** (`Edited by - <name>`, an individual journalist's
`@handle`) and an in-body informational pointer (`<official-site> आहे, येथे क्लिक
करून …` = "here is the official source, click to reach it") are legitimate article
metadata — **not C1**. A *publication's* own promo handle (`@maharashtracity`), a
"join our channel/Telegram" CTA, a "buy on Amazon" CTA, a share CTA, and a site
footer **are C1**. Line drawn: a *person's* name/handle as attribution is kept; a
*publication's* chrome is stripped.

**Medicine (two-stage, action = fix / strip):**
1. **Cross-document shingle index** (primary, high precision): drop any text chunk
   that recurs verbatim across **≥ 4 documents** — this is how pass-1 found C1 and
   is self-calibrating: unique article prose never repeats, so it is untouched.
2. **Pure-boilerplate line anchors** (supplement): strip whole lines matching the
   fixed teaser/CTA/footer marker set above, **only when the line is a document
   head/tail** (first/last ~3 lines).

**Harm test:** the line-anchored marker strip applied doc-wide touches **10/269
(3.7%) → FAILS**. The hits are real clean articles whose *body* carries a phrase
like `महत्वाच्या बातम्या` as a sub-heading, not as chrome — the marker can't tell a
heading from a footer. The stage-1 shingle index (measured, not asserted) touches
**1/269 (0.4%) → PASS**: the single hit, `51b91de49faf6839`, carries a
`View this post on Instagram` line that recurs across ≥4 docs — genuine boilerplate,
so stripping it is arguably correct, and it is well under the bar. The pack-wide
shingle set is **10 lines** (≥20 chars, ≥4 docs).

**Prescription:** ship **stage 1** as the automatic fix; apply stage-2 markers only
when the line is also a head/tail line or confirmed by a second reader. The
doc-wide marker strip is too aggressive — documented side-effect, do not run it
unscoped.

**Side effects:** stage-2 unscoped removes legitimate in-body sub-headings.

---

## D3 — foreign-language content (label, don't judge) — **123**

English/Hindi titles and full sentences sitting in a Marathi doc. Per the field
guide this is **natural** — labelled, never dropped or "fixed." Conservative
tagging: English **title prefix** or a **full** English/Hindi sentence only; bare
loanwords and parenthetical glosses skipped.

This pass settled the policy explicitly: D3 is **"label it, do not judge it."** A
doc whose *only* finding is D3 is therefore `clean+D3` (verdict `clean`, disease
`D3`), not `fix` — 34 such rows were flipped from `fix` to `clean` this pass, and
D3-only docs found later were labelled `clean+D3` directly (43 `clean+D3` total).

Examples: `00eed90bde196e9c` ('How To Find Sweet Watermelon:', now `clean+D3`),
`45099f1718f10018` ('Lioness And Leopard Fight Viral Video'), `924d41c82dfe4138`
('Viral Video').

**Medicine:** action = **none (label only)**. Detector = script-run test: a
contiguous run of ≥ 4 Latin tokens forming a title or sentence → tag D3. No text
is altered.

**Harm test:** rule writes **0** bytes → **0/269 → PASS** trivially. (A D3 tag on
a clean doc is metadata, not harm.)

**Side effects:** none — non-destructive. One second-order effect worth noting:
keeping English glosses/sentences inside clean docs is what interacts with the C5
SEO-slug clause (see C5) — the slug clause is gated so it does not touch them.

---

## C2 — intra-document duplication — **18**

Same line/paragraph repeated inside one doc beyond natural refrain.

Examples: `052f2791183c599c` (`आधी रोटी खाएंगे…` ×5), `2542e8ad88e5f64e`
(birthday-wishes block), `0e8893761b8a7317`.

**Medicine (action = fix / dedupe):** collapse a line to one copy only when it
repeats **≥ 5×** *and* is **≥ 20 chars** (guards poem refrains, quiz-answer
labels, section headers — all deliberately declined during labelling).

**Disease:** C2

```python
def medicine_c2(text):
    """Collapse a line that repeats >= 5 times (and is >= 20 chars) to its first copy."""
    lines = text.split("\n")
    count = {}
    for l in lines:
        k = l.strip()
        if len(k) >= 20:
            count[k] = count.get(k, 0) + 1
    rep = {k for k, n in count.items() if n >= 5}
    if not rep:
        return text
    seen, out = set(), []
    for l in lines:
        k = l.strip()
        if k in rep:
            if k in seen:
                continue
            seen.add(k)
        out.append(l)
    return "\n".join(out)
```

**Harm test:** **0/269 → PASS**. The ≥5×/≥20-char gate skips benign structural
repeats (quiz `उत्तर:`, verse refrains) a naive "any repeated line" rule flattens.

**Gold-set harm (142 docs, 3 Nov):** 0/142 changed, 0/142 dropped → **PASS**;
independently re-run by millermuttu with the same result.

**Side effects:** a genuine 5× rhetorical refrain ≥20 chars would be clipped —
rare; accept.

---

## G2 — legacy-font (Shree-Lipi / ISCII) damage — **15**

Virama/nukta/colon corruption from legacy-font→Unicode conversion, four sub-forms:
1. `ऱ+य` with dropped virama (U+0931 U+092F), e.g. `मोठय़ा`=मोठ्या;
2. stray nukta `य़` (U+092F U+093C), e.g. `झेंडय़ाखाली`=झेंड्याखाली;
3. `रु/रू → ऊ` glyph substitution, e.g. `तऊणाच्या`=तरुणाच्या;
4. **standalone visarga `ः` (U+0903) used as the dateline colon**, e.g.
   `नवी मुंबई ः` — the old dateline-colon glyph survives on the visarga codepoint.

Examples: `db98ccd3357dd806` (`मोठय़ा`), `dd4c7834eff01ca4` (`रु/रू→ऊ`, systematic),
`506a604b057244e5` (visarga-as-colon `ता. १९ ः`).

**Medicine (action = fix / recompose):** `U+0931 U+092F` → `ऱ्य`; strip stray
`U+093C` after `य`/`र` where it yields a non-word; `ऊ→रू` **only inside a flagged
legacy-font doc** (context gate); a lone `U+0903` bounded by spaces → `:` (dateline
colon). The conjunct-gibberish variant (fully garbled `डअध छज …`) is unrecoverable
→ `drop` or flag, not auto-fix.

**Harm test:** legacy patterns (`ऱय`, stray `य़`, standalone visarga-colon) occur in
**0/269** clean docs → PASS. The visarga-colon rule is gated to a space-bounded lone
U+0903 so it never touches a legitimate word-final visarga (`स्वतःच`, `यशः`).

**Side effects:** `ऊ→रू` is context-gated to legacy docs to avoid corrupting the
legitimate vowel ऊ; outside that gate, leave alone.

---

## D4 — broken machine translation — **12** · (drop)

Ungrammatical word-salad Marathi from MT of foreign-site content; word order
destroyed. Examples: `48fa412a505a1e68` (Spanish grooming site, `hombresconestilo.com/mr/`),
`fc9290beea94f4df`, `fef7b755c76715d1`.

**Medicine:** action = **drop** (unsalvageable). Detector: source URL carries an
MT marker (`/mr/`, `/mt/`, translate param) **and** a Marathi grammaticality score
below threshold → drop. **Both gates are required.**

**Harm test:** the URL marker **alone** touches **3/269 (1.1%) → FAILS**:
`526f8907` (inheritanceneeds.com/mr/), `38326254` (happiesthealth.com/mr/),
`089a742f` (thefreemedia.in/mr/) are all `/mr/` localized URLs whose Marathi is
**fluent** and was read clean. So the grammaticality gate is doing real work — it
is what keeps these three out of the drop set. With no local grammaticality scorer,
D4 ships as **review-assisted** (URL marker shortlists candidates; a reader
confirms the word-salad before drop), not fully automatic.

**Side effects:** URL-marker-alone would wrongly drop fluent localized content
(the 3 docs above) — never ship it without the second gate.

---

## C3 — truncation — **10** · (fix/drop)

Doc cut mid-sentence or carrying an explicit truncation marker. Examples:
`c5c7f7feea32245d` (ends `[…]` @445), `340ec57eef39bb14` (archive listing of
teasers, many cut mid-sentence → drop), `23d8d35ab252e3c4` (incomplete Wikipedia
para).

**Medicine (action = drop if body lost, else fix/trim):** flag only on **explicit
truncation markers** — `[…]`, `Continue Reading`, `Read More`, trailing `...` at
EOF — not on "no terminal punctuation."

**Disease:** C3

```python
import re

_C3_MARK = re.compile(r"\[…\]|\[\.\.\.\]|Continue Reading|Read More")
_C3_TAIL = re.compile(r"(?:\s*(?:\[…\]|\[\.\.\.\]|…\]|Continue Reading|Read More|\.\.\.))+\s*\Z")

def medicine_c3(text):
    """Drop a teaser listing (>= 3 explicit truncation markers); else trim a truncation marker at the end of the text."""
    if len(_C3_MARK.findall(text)) >= 3:
        return True
    return _C3_TAIL.sub("", text)
```

**Harm test:** the naive "ends without sentence punctuation" rule touches **31/269
(11.5%) → FAILS** (clean docs legitimately end on a heading, list item, or quote).
The explicit-marker rule touches **1/269 (0.4%) → PASS** — the single hit,
`c85acdaeebe64599`, ends `…स्लाईड्सवर क्लिक करा...` (a "click next slide" CTA whose
trailing `...` is rhetorical, not truncation). Under the bar, documented.

**Gold-set harm (142 docs, 3 Nov):** 0/142 changed, 0/142 dropped → **PASS**;
independently re-run by millermuttu with the same result.

**Side effects:** rare clean docs ending in a rhetorical `...` CTA (1 above) would
be mis-flagged; the explicit-`[…]`/`Continue Reading` subset avoids even that.

---

## C5 — keyword / link lists, SEO spam — **10** · (fix)

Tag clouds, SEO keyword-slugs, product keyword lists, and leaked page URL-slugs
dumped into article text. Examples: `626fc9159542b61c` (`Tags: Diabetes`),
`4ab66b3a5d21bfe7` (SEO slug `(odi world cup 2023 hardik pandya fitness upadte …)`),
`bc8ad309586730d2` (`बांबू पलंग / बांबू खुर्ची / बांबू टेबल …` repeated-head product
list), `d371d07939ac6d17` (the page's own URL-slug `keto diet good for weight loss`
leaked inline as a standalone line, verbatim from `ujobs.in/keto-diet-good-for-weight-loss/`).

**Medicine (action = fix / strip the list block):** strip a line/segment matching
any of (a) an explicit tag label `^(Tags?|टॅग|कीवर्ड)\s*:`; (b) an English SEO slug
— ≥ 5 consecutive all-lowercase-ascii/digit tokens, **gated to a line-dominant run
outside parentheses**; (c) a `/`- or `|`-separated run of ≥ 4 items sharing a
repeated head word (Devanagari keyword list).

**Disease:** C5

```python
import re

_TAG = re.compile(r"^\s*(?:tags?|टॅग[स्]?|कीवर्ड[स्]?)\s*[:：]", re.I)
_SLUG = re.compile(r"(?:\b[a-z0-9]+\b[ \-]){4,}\b[a-z0-9]+\b")

def _c5_line(line):
    ls = line.strip()
    if _TAG.match(line):
        return True                                   # (a) explicit tag label
    if "(" not in ls and ")" not in ls:               # (b) standalone SEO slug, not a parenthetical gloss
        for m in _SLUG.finditer(ls):
            g = m.group()
            if len(g.split()) >= 5 and len(g) >= 0.7 * len(ls):
                return True
    items = [x.strip() for x in re.split(r"[/|]", line) if x.strip()]
    if len(items) >= 4:                               # (c) repeated-head keyword list
        heads = [x.split()[0] for x in items]
        top = max(heads.count(h) for h in set(heads))
        if top >= max(2, len(items) // 2):
            return True
    return False

def medicine_c5(text):
    """Remove whole lines that are a tag cloud, an SEO slug or a repeated-head keyword list."""
    lines = text.split("\n")
    keep = [l for l in lines if not _c5_line(l)]
    return text if len(keep) == len(lines) else "\n".join(keep)
```

**Harm test:** the naive "any line with ≥6 comma/pipe tokens" rule touches **30/269
(11.2%) → FAILS** (normal Marathi comma lists). The SEO-slug clause (b) interacts
with the D3 "label, don't judge" policy: English glosses/sentences kept inside
clean docs (`a729bd3f` `(… memorial by social activists jalgaon news)`,
`fa3ce28286fd823b` `(uddhav thackeray and sanjay raut meet …)`) read like lowercase
slugs — **ungated**, clause (b) touches **2/269 (0.7%)**, under the bar but for the
wrong reason. **Gating clause (b) to a line-dominant, non-parenthetical run** drops
both (they are parenthetical) → **0/269 → PASS**, while still firing on genuine
standalone slugs: the URL-slug leak in `d371d07` and the shopping slug in
`97333df118ec5df2`. It declines `4ab66b3a`'s *parenthetical* slug automatically —
correct, since auto-stripping a parenthetical English run blind is the same
over-reach that would hit the two D3 glosses; that doc is a `fix` doc already
settled by reading.

**Gold-set harm (142 docs, 3 Nov):** 0/142 changed, 0/142 dropped → **PASS**;
independently re-run by millermuttu with the same result.

**Side effects:** none on the clean set under the gate (0/269). Ungated, two D3
parenthetical glosses would be touched — benign (a kept D3 gloss is not damaged by
a flag), and the gate removes even that.

---

## B4 — template / code junk / filter-evasion — **8** · (fix)

`:-`/`-`/`'` inserted inside words to dodge filters; unrendered WP shortcodes
(`[sc_fs_faq …]`, `[ad_1]`); placeholder PII (`firstname.lastname@example.org`);
stray markup glyphs (orphaned superscript `⁵`). Examples: `f21b3178cb113107`
(`ध:- म:- का:- वू:- न`), `05045fec2475fdb9` (shortcode @8232), `a17a859aa9af0546`
(placeholder email `firstname.lastname@example.org`).

**Medicine (action = fix):** (a) strip known shortcode tokens by literal list;
(b) remove intra-word `:-` only when a doc has **≥ 3** intra-word `:-` occurrences
(filter-evasion signature), re-joining the splinters; (c) delete a lone orphaned
superscript/markup glyph on its own line.

**Disease:** B4

```python
import re

_SHORTCODE = re.compile(r"\[/?(?:sc_[a-z0-9_]+|ad_\d+|vc_[a-z0-9_]+|caption|gallery)\b[^\]\n]*\]")
_SPLINTER = re.compile(r"(?<=[ऀ-ॿ]):-[ ]?(?=[ऀ-ॿ])")
_ORPHAN = re.compile(r"(?m)^[ \t]*[⁰¹²³⁴⁵⁶⁷⁸⁹]+[ \t]*(?:\n|\Z)")
_PLACEHOLDER = re.compile(r"(?m)^[ \t]*firstname\.lastname@example\.(?:org|com)[ \t]*(?:\n|\Z)")

def medicine_b4(text):
    """(a) strip known shortcodes; (b) re-join splinters only in a doc with >= 3 intra-word ':-';
    (c) delete a lone superscript glyph on its own line; (d) delete a placeholder-email line."""
    out = _SHORTCODE.sub("", text)
    if len(_SPLINTER.findall(out)) >= 3:
        out = _SPLINTER.sub("", out)
    out = _ORPHAN.sub("", out)
    return _PLACEHOLDER.sub("", out)
```

**Harm test:** the naive "remove any `:-`" rule touches **11/269 (4.1%) → FAILS** —
`:-` is a normal dateline/time separator (`मुंबई :-`, `10:-30`). The **tokens +
intra-word-`:-` ≥ 3** rule touches **0/269 → PASS**: no clean doc splinters 3+ words.

**Gold-set harm (142 docs, 3 Nov):** 0/142 changed, 0/142 dropped → **PASS**;
independently re-run by millermuttu with the same result.

**Side effects:** none under the ≥3 gate; the blunt `:-` strip mangles datelines
(documented — do not ship).

---

## D5 — translationese — **8** · (drop)

Literal MT that is grammatical but unnatural — calqued English idioms. Examples:
`8201070a548d3e9d` ('एक लहान बाटली खूप लांब जाईल' = "a little bottle goes a long
way"), `d9abc0a9e976cd2f` (codegym auto-translation), `235af31f6022ea73`.

**Medicine:** action = **drop**. No reliable automatic detector — flagged by reader
judgement on calque idioms + foreign source domain. **Do not auto-run**; this is a
human-review disease.

**Harm test:** no automatic rule to run → not applicable (review-only). Any
automated proxy for translationese would over-reach; left as review-only.

**Side effects:** none automatic; manual drop risks subjectivity — keep the
foreign-domain corroboration requirement.

---

## F1 — PII leak — **8** · (fix)

Phone numbers (Latin or Devanagari digits), emails leaked into body. **Never copy
the value** — evidence is type + offset only, hex empty. Examples:
`26dda2c33506f1ff` (phone @2435), `dac55ea8bc131eb1` (phone @108), `6169b09fe7801904`
(email @1171).

**Medicine (action = fix / redact):** redact matches of a phone regex
(`(?<!\d)[6-9]\d{9}(?!\d)` + Devanagari-digit and delimited variants) and an email
regex, replacing with a `[redacted]` token. Offsets logged, values never stored.

**Harm test:** **0/269 → PASS** — the phone/email regexes match nothing in the
clean set. (Placeholder `example.org` emails are the B4 cases, which are `fix`
docs, not clean.)

**Side effects:** a 10-digit non-phone (e.g. a long ID) could be redacted — low
rate; the `[6-9]` leading-digit gate limits it to plausible Indian mobiles.

---

## C4 — two/more documents joined — **5** · (drop, mostly)

Genuinely unrelated texts concatenated with no boundary. Examples:
`1686935b1034083d` (unrelated company share-price paragraphs joined → drop),
`5e5dfd4352f5175a` (BenQ monitor review + Dutch Zelda-wiki content → drop),
`6584bcd16dc3fdbf` (op-ed index: 5 unrelated teaser blocks), `05b7b743f394e916`
(incomplete clips of unrelated news joined), `99aa07a986e2d813` (disjoint
travel-post excerpts).

**Scope refinement (this pass):** C4 was over-applied. An article followed by a
site's *related-headline widget* (`महत्वाच्या बातम्या`, "You may like") is **not**
two documents — that is a boilerplate link block → **C1 (+C5)**. Three docs were
recoded C4 → C1;C5 (`654e623661c0b8c6`, `8207d3c24ce05878`, `0cd78c6d499c4cb5`),
leaving only genuine two-unrelated-text splices. C4 fell **8 → 5**.

**Medicine:** two paths. (a) Shared-block removal: the same **cross-document shingle
index as C1 stage-1** (chunk recurs across ≥ 4 docs → strip). (b) True two-doc
splices (topic A then unrelated topic B) have no automatic cut point → **drop**.

**Harm test:** the shingle index touches **1/269 (0.4%) → PASS** (the same single
Instagram-caption doc as C1 stage-1; it shares one implementation). The splice-drop
path is review-flagged (no safe automatic boundary detector).

**Side effects:** none beyond C1 stage-1's; the splice case is human-confirmed.

---

## A5 — अॅ dual-encoding — **3** · (fix) · *below the 5× bar, retained for the record*

Same vowel sign encoded two ways: `अ + ॅ` (U+0905 U+0945) vs `ऍ` (U+090D). NFC does
**not** unify them, so one word gets two token IDs.

**Correction this pass (important):** A5 was **over-counted at 13**. Ten of those
docs contained **only** `अॅ` (`अ`+`ॅ`) — which is the *normal* Marathi spelling of
the æ loanword sound (अॅप, अॅक्शन, अॅलोवेरा) and renders correctly — with **no
co-occurring `ऍ`**. A single consistent encoding is not dual-encoding, so those ten
were removed from A5. Only docs where **both forms co-occur** remain: **3** —
`d9abc0a9e976cd2f` (drop/D5), `ae7305a6399c73a4` (drop/D4), `3a87c3949bbefd3e`
(fix/C1;D3). At 3 this is **below the ≥5× medicine bar**; kept here because the
NFC-invisible dual-encoding finding and its coexist gate are instructive, and the
harm result still holds.

**Medicine (action = fix / normalize):** normalize to a single form **only in docs
where both encodings co-occur** (the coexist gate). Do **not** normalize everywhere.

**Harm test:** the naive "normalize every अॅ" rule touches **14/269 (5.2%) → FAILS**
— because अॅप / अॅक्शन / अॅलोवेरा are *normal* Marathi loanword spellings. The
**coexist-only** rule touches **0/269 → PASS**: a clean doc uses one consistent
encoding, never both.

**Side effects:** none under the coexist gate; unscoped normalization mangles
everyday loanwords (documented — do not ship unscoped).

---

## Harm test on the TSAI gold set (3 Nov)

Medicine sha256 is printed by the tool; gold set `ind-mr-fw2_gold.csv`, 142 documents,
limit 1 changed or dropped. ZWJ/ZWNJ audit and normal-form audit (NFC, compatibility
characters) pass for every rule.

| Rule | Changed | Dropped | Result | My 269 clean docs | Fires on its labelled docs |
|---|---|---|---|---|---|
| C2 | 0/142 | 0/142 | PASS | 0 | 2 of 18 |
| C3 | 0/142 | 0/142 | PASS | 1 (`c85acdae`, a rhetorical `...` CTA) | 2 of 10 (1 trim, 1 drop) |
| C5 | 0/142 | 0/142 | PASS | 0 | 4 of 10 |
| B4 | 0/142 | 0/142 | PASS | 0 | 5 of 8 |
| all four in order | 0/142 | 0/142 | PASS | | |

A rule that changes nothing also passes, so the last column checks that each rule
does fire. The recall is partial on purpose: the gates are the narrow versions that
passed the harm bar. C2 is the weakest: 16 of the 18 labelled docs repeat text
inside one line or fewer than 5 times, not whole lines 5 or more times. Lowering the
gate to 3 repeats also touches 0/269 of my clean docs and would catch 3 more, but
it risks clipping a refrain, so it is not shipped without a second reader. B4
misses `40835ade`, `d105bc0a` (drop) and `e24303fd` (a Cloudflare `[email protected]` token).
C5 misses 6 labelled docs: the parenthetical slug in `4ab66b3a` on purpose (see C5),
the product list `bc8ad309`, two related-link blocks, the drop doc `340ec57e` and `5c05e182`.

---

## Summary table

| Disease | Count | Action | Naive rule (harm/269) | Shipped rule (harm/269) |
|---|---|---|---|---|
| C1 | 165 | fix/strip | markers 10 (3.7%) FAIL | shingle ≥4 docs → 1 (0.4%) PASS (stage-2 scoped) |
| D3 | 123 | label only | — | 0 PASS (non-destructive) |
| C2 | 18 | fix/dedupe | — | ≥5× & ≥20ch → 0 PASS |
| G2 | 15 | fix/recompose | — | legacy patterns → 0 PASS |
| D4 | 12 | drop | URL-marker 3 (1.1%) FAIL | URL + gram gate → review-assisted |
| C3 | 10 | fix/drop | no-punct 31 (11.5%) FAIL | explicit markers → 1 (0.4%) PASS |
| C5 | 10 | fix/strip | token-list 30 (11.2%) FAIL | tag + gated-slug + head-list → 0 PASS |
| B4 | 8 | fix | any `:-` 11 (4.1%) FAIL | tokens + `:-`≥3 → 0 PASS |
| D5 | 8 | drop | — | review-only (no auto rule) |
| F1 | 8 | fix/redact | — | phone+email regex → 0 PASS |
| C4 | 5 | drop/fix | — | shingle ≥4 docs → 1 (0.4%) PASS (splice=drop) |
| A5 | 3 | fix/normalize | all-अॅ 14 (5.2%) FAIL | coexist-only → 0 PASS (sub-threshold) |

**Headline finding:** every naive first-pass medicine that looked obvious (strip all
boilerplate markers, normalize all अॅ, drop any unpunctuated tail, remove any `:-`,
strip any comma-list) **FAILS** the 1% harm bar — each over-reaches into normal
Marathi. The shipped rules are the *narrowed* versions (co-occurrence gate,
cross-document recurrence, explicit markers, count thresholds, tag/slug shapes),
all **≤ 1/269 → PASS**. Two diseases cannot be fully automated to the bar and ship
**review-assisted**: **D4** (URL marker alone wrongly drops 3 fluent localized docs
— needs a grammaticality gate) and **D5** (no reliable automatic detector).

**Interaction worth flagging:** the D3 "label, don't judge" policy (keep English
titles/sentences inside clean docs) and the C5 SEO-slug fixer **conflict** — an
ungated lowercase-run detector reads a kept English gloss as a keyword slug. The
slug clause is therefore gated to line-dominant, non-parenthetical runs (0/269).
Any future language-aware fixer must respect the same line: D3 content is kept, so
a destructive rule must never key on "looks like English."

**Caveat:** the proxy gold set is one reader (me). A real two-reader gold set would
likely expose further C1/D3/C5 edge cases; the PASS results are necessary, not
sufficient.
