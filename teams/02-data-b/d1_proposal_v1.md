# D1 script share: Data B's proposal (v1, draft of 12 Nov 2026)

For issue #214 (script-aware filters, G2) and the Gate 2 plan in #217. The filter itself is in
`filters/medicine.md` ("Medicine 1: script share"). This note says what we propose to run, why, and what we do not know yet.

**In short.** D1 measures how much of a document is in the pack's own script. We propose: keep at 0.50 or more, flag and
keep from 0.30 to 0.50, drop only under 0.30 when another script is the largest, and never judge a document under
20 letters. On the 10 packs we hold (5,000 documents) this drops nothing and flags 8 code-mixed pages. We cannot yet show
that it catches wrong-language pages, because the packs where readers found them are not on hand.

## 1. What D1 is

D1 is "wrong language label" in `diagnosis/DISEASES.md`: a document whose letters are mostly in another script than the
pack's. Readers marked it in 38 rows of 10 packs; most in `ind-te-sangraha-v` (12), `ind-sa-fw2` (6) and `ind-hi-hplt` (4).
No Data B rule covered D1 in any pack before this one.

The filter counts letters and combining signs by Unicode script (digits, punctuation, dandas, spaces, ZWJ and ZWNJ are not
counted) and divides the pack's script count by all letters. It returns a verdict only; it never changes the text. NFC is
used to count, never NFKC. The pack's script comes from the environment variable `D1_SCRIPT` (`run_harm.py` sets it per
pack), because a text-only function cannot be told the pack.

## 2. Evidence (measured on the 10 packs on hand, 500 documents each; `filters/d1_share_stats.py`)

| Pack | Script | Lowest share | Under 0.7 | Under 0.5 | Under 0.3 | Gold docs | Lowest share in gold |
|---|---|---|---|---|---|---|---|
| ind-bn-fw2 | Bengali | 0.43 | 3 | 1 | 0 | 227 | 0.81 |
| ind-bn-sangraha-v | Bengali | 0.56 | 6 | 0 | 0 | 137 | 1.00 |
| ind-hi-sangraha-s | Devanagari | 0.31 | 1 | 1 | 0 | 24 | 1.00 |
| ind-kn-fw2 | Kannada | 0.41 | 8 | 2 | 0 | 115 | 0.96 |
| ind-kn-sangraha-s | Kannada | 0.94 | 0 | 0 | 0 | 22 | 0.99 |
| ind-ml-fw2 | Malayalam | 0.44 | 6 | 1 | 0 | 0 | none yet |
| ind-or-fw2 | Odia | 0.40 | 5 | 1 | 0 | 0 | none yet |
| ind-ta-fw2 | Tamil | 0.43 | 2 | 2 | 0 | 0 | none yet |
| ind-ta-sangraha-s | Tamil | 0.95 | 0 | 0 | 0 | 0 | none yet |
| ind-te-sangraha-s | Telugu | 0.92 | 0 | 0 | 0 | 24 | 0.93 |
| **All 10** | | **0.31** | **31** | **8** | **0** | 549 | **0.81** |

- All 8 documents under 0.5 have Latin letters as the largest other script, at 56% to 69%. They are code-mixed pages
  (a few Indic lines among English text), not pages in another Indic script. No document has another Indic script as its
  largest.
- No document in the 10 packs is under 0.30, so the drop rule never fires there. One Hindi document (ind-hi-sangraha-s) sits at
  0.31, Latin 69%: it is the one case where the 0.30 line decides, and it is flagged and kept.
- Harm test (each pack on its own gold set): D1 changes or drops 0 gold documents in all 6 testable packs (PASS). The
  other 4 packs have no gold set yet ("gold set empty, not testable"); on all 500 of their documents D1 also drops 0.

## 3. What the evidence says

1. **Clean text is safe at these lines.** The lowest share in any gold (clean) document is 0.81; everywhere else 0.93 or
   more. A drop line of 0.30 is far below that.
2. **The only low-share pages we see are code-mixed.** The issue's own warning is that a language filter that sees a few
   English words can throw away a good page. A page that is 57% to 69% Latin is probably mostly English, but it may also be a
   real Indic page quoting English; D1 should not drop it on this evidence alone. That is why the middle band is a flag
   and not a drop.
3. **We have not shown that D1 catches the defect.** A pass on gold shows no harm; it does not show recall. The three
   packs with most D1 marks (`ind-te-sangraha-v`, `ind-sa-fw2`, `ind-hi-hplt`) are among the pack files we do not hold.
4. **Devanagari is a known limit.** Hindi, Marathi and Sanskrit share one script, so a Hindi page in a Marathi pack has a
   share of 1.00 and is kept. Script share cannot see it (also said in #214). Two of the three packs with most marks are
   Devanagari packs (`ind-sa-fw2`, `ind-hi-hplt`), so this may matter; we cannot measure it yet.

## 4. Proposal

| Option | Rule | On the 10 packs | Risk |
|---|---|---|---|
| A. Flag only | never drop; a share under 0.50 is a flag | 0 dropped, 8 flagged | Wrong-language pages stay in the data; the flag needs someone downstream to act on it |
| **B. Proposed** | keep at 0.50 or more; flag from 0.30 to 0.50 and keep; drop under 0.30 when another script is the largest; under 20 letters, keep | 0 dropped, 8 flagged | A wrong-language page that is partly in the pack's script (0.30 to 0.50) is kept and flagged only |
| C. Stricter | drop under 0.50 | 8 dropped (0.16%), all code-mixed | Drops code-mixed pages that may be good Indic text |

**Recommendation: B.** It drops only documents that are mostly in another script, which is what the disease means, and it
leaves the code-mixed middle for a flag. The numbers 0.50, 0.30 and 20 are ours; the data above only shows that they are
safe on clean text, not that they are the best values.

**Devanagari.** Leave it as it is for v1 and say so (option A in `filters/questions_for_tsai.md`, question 4). A
Hindi-versus-Marathi check needs a language-ID tool and the packs we are missing.

**Hand-off to Data A.** The function needs to know the pack's script. Where it is called with the text only, it asks just
that the document is mostly in some Indic script, which is weaker. We suggest Data A passes the pack's script, as
`run_harm.py` does with `D1_SCRIPT`; this needs agreement.

## 5. What we do not know yet (so this draft will change)

- Whether D1 catches the wrong-language pages readers marked: the packs holding most of the 38 marks are not on hand
  (pack links are the open question in `filters/questions_for_tsai.md`, question 5).
- How many of those marks are the same-script case (Hindi in Marathi, Marathi in Sanskrit).
- Whether TSAI wants a flagged document dropped later, or only listed.
- Whether 0.50 and 0.30 are the right lines. We can tune them once the packs with D1 marks are here, but the lines
  must stay below every gold document (today's lowest: 0.81).

## 6. Where the numbers come from

- Shares and counts: `python filters/d1_share_stats.py --packs-dir <packs> --gold-dir <gold_set>` (counts only, no
  document text) on the 9 pack files on hand.
- Harm results: `filters/harm_<pack>.md`, made by `filters/run_harm.py` with `tools/harm_test_indic.py`.
- D1 mark counts (38 rows, 10 packs; 12, 6 and 4 in the three largest): issue #214, comment of 7 Nov, and `filters/medicine.md`.
- Unit tests of the filter: `filters/test_filters.py` (made-up text only).
