# Romanised Indic (D2) policy, v1

Issue #213, part 2. How romanised Indic text (an Indian language in Latin letters, D2 in `diagnosis/DISEASES.md`)
is measured and capped in the training corpus. The cap value is a Gate 2 decision (14 Nov); this file gives the
measurements and the options.

## Rules (TSAI in G2, 5 Nov)

1. The cap applies to the training corpus. The detector is run over the corpus; the gold sets are used only for the
   harm test.
2. The cap is measured in **tokens**, per language, because the data mix is set in tokens.
3. A document is **romanised** when most of its words are romanised. A native-script article with one romanised
   heading or comment stays a native document.
4. When a language is over the cap, whole romanised documents are dropped, chosen at random with a fixed seed. No
   passages are stripped and nothing is transliterated, since both change the text of a document.

## Detector: word list, not IndicLID

`doc_detector.py` cuts a document into lines and sentences, a segment classifier marks the romanised segments, and the
document is romanised when the Latin-letter words in those segments are more than 50% of all its words (any script).
Two segment classifiers were compared on the same rows (`eval_v2.py`, `eval_v2.md`):

- **word list**: a segment is romanised when it has at least 2 different words from the romanised word list in
  `detector.py`, or at least 2 IAST letters;
- **IndicLID** (AI4Bharat, MIT licence): a segment is romanised when IndicLID labels it as an Indian language in
  Latin letters (`hin_Latn`, `tel_Latn`, ...).

Scored at the contains level (the document has at least one romanised segment, which is what readers marked as D2) on
the 100 labelled documents of part 1 (`testset_100.csv`), and on all 1,957 gold documents (17 packs), where every flag
is a false positive:

| tool | precision / recall, readers' labels | precision / recall, checked labels | gold flagged | pack documents flagged (of 11,000) |
|---|---|---|---|---|
| **word list** | 100% / 48% | 92% / 70% | **0** | 39 |
| IndicLID | 76% / 56% | 58% / 67% | 9 | 578 |

At the majority level (the rule for the cap) neither tool flags a gold document. The word list flags no pack document;
IndicLID flags one, a Hindi page whose broken text (hundreds of `<unk>` tokens and `Â` characters) it labels as
romanised Konkani.

**Choice: the word list**, by TSAI's rule (better on the gold check). IndicLID's errors come from how it works:

- it always picks a language, so short Latin fragments such as names and datelines ("( Sikka )", "Orchha Ramraja
  Sarkar Mandir", "xslt.") become romanised Indic;
- it is trained on full sentences, and web text is full of headings and names;
- it sends a segment to its native-script model when most characters are not Latin, so a Hinglish line mixed with
  Devanagari comes back as Hindi in Devanagari and its romanised part is missed.

Tuning did not change the choice (`indiclid_variants.py`, `eval_v2_indiclid_variants.md`, 18 settings):

| IndicLID setting | precision / recall, readers' labels | gold flagged | pack documents flagged |
|---|---|---|---|
| as published | 76% / 56% | 9 | 578 |
| segments with at least 4 Latin words, score at least 0.9 (fewest gold flags) | 100% / 29% | 1 | 62 |
| Latin words of each segment only (fixes the mixed lines) | 66% / 79% | 73 | 2,213 |

No setting reaches 0 gold flags, and the one closest to it finds fewer D2 documents than the word list.

## Measurement on the sample packs

`token_share.py`, word-list detector, all 22 `ind-*` sample packs (500 documents each), `romanised_token_share_v1.csv`:

| lang | tokens | romanised documents | cap share | romanised segment tokens in native documents |
|---|---|---|---|---|
| hi | 2,678,910 | 0 | 0% | 1,088 (0.041%) |
| ta | 1,518,893 | 0 | 0% | 765 (0.050%) |
| te | 1,628,410 | 0 | 0% | 456 (0.028%) |
| gu | 438,226 | 0 | 0% | 97 (0.022%) |
| sa | 1,607,854 | 0 | 0% | 326 (0.020%) |
| bn | 952,141 | 0 | 0% | 140 (0.015%) |
| mr | 886,761 | 0 | 0% | 49 (0.006%) |
| kn | 1,540,104 | 0 | 0% | 80 (0.005%) |
| ml, or | 866,051 | 0 | 0% | 0 |
| **all** | **12,117,350** | **0** | **0%** | **3,001 (0.025%)** |

- **Cap share** = tokens of romanised documents / all tokens of the language. The word list finds no sample document
  that is mostly romanised; its highest share is 35% (ind-hi-indiccorp `62707cd1ddf37b45`).
- The last column is for scale only: romanised headings, comments and verses inside native documents. Rule 3 keeps
  them, and the cap does not count them.
- The word list misses romanised words that are not on it, so its shares are low. A bound that does not depend on the
  list: a document cannot be more romanised than its share of Latin-letter words. 37 of the 11,000 documents have more
  than half their words in Latin letters. In review (#327) these were found to be English, another language (one is
  Guarani) or broken text, apart from a Kannada phrasebook (ind-kn-sangraha-v `da01db2cbb02e54d`: Kannada, romanised
  Kannada and Spanish side by side, so well under half romanised). The closest real case is ind-te-fw2
  `8cac6c338ccde963`: by a
  rough count about 40% of its words are romanised Telugu (55% are Latin-letter words, the rest of the Latin text is
  English), while the word list gives 10% because common words in it (naku, nannu, ani, andi, tanu) are not on the
  list. It stays under 50%, and both readers drop it (F3), so it changes nothing here.
- **Tokenizer: stand-in.** Tokens are counted with BrahmicTokenizer-131K (`github.com/theschoolofai/BrahmicTokenizer-131K`,
  commit `7dfcf398`), the baseline team 03-tokenizer measures its candidates against. When the project tokenizer is
  final, re-run `python token_share.py --tokenizer <its tokenizer.json>` and update this table.

## Cap options for Gate 2

The sample has no romanised documents, so none of these drops anything from it. The cap is a safeguard for the full
corpus, where a source not in the sample (for example a forum or chat crawl) could be mostly romanised.

| option | cap per language (romanised document tokens) | effect |
|---|---|---|
| A | 0% | drop every romanised document |
| **B (proposed)** | **1%** | keep a small amount of romanised text, since users type romanised Hindi, Tamil and others; drop only if a source brings in more |
| C | 2% | as B, more permissive |

Proposal: **B, 1% per language.** It is about 40 times the romanised share seen inside native documents in the sample,
so it will not bind unless a new source is heavy in romanised text, and it still bounds what such a source can add.

## How the cap is applied

For each language, on the training corpus:

1. Run `doc_detector.decide` (word list) on every document.
2. Count tokens with the project tokenizer: `R` = tokens of romanised documents, `T` = all tokens of the language.
3. If `R / T` is above the cap, sort the romanised doc_ids, shuffle them with `random.Random(0).shuffle`, and drop the
   documents in that order until `R / T` is at or below the cap. Sorting first makes the order the same however the
   documents are read. Dropped documents are removed whole and listed with their doc_ids.
4. Harm test: no gold document may be dropped. On the current gold sets the detector flags 0 at the majority level.

## Wrong D2 marks and gold

Readers' D2 marks are not all correct: 19 of the 52 hold no romanised Indic phrase (`checked_labels.csv`). Only two of
them kept a clean document out of a gold set (ind-bn-sangraha-v `aecb9893b814c81f`, ind-hi-fw2 `3776d34f591f896d`).
Data B checked them in #213: under the document rule both are native documents, and the readers are asked to change
their rows to clean, so the next gold rebuild includes them. They are also good gold cases for the cap: native
documents with a little romanised text, which the cap must not drop. The other sheets are not re-done.

The gold check above uses the 1,957 gold documents on main. After the gold rebuild (#229) merges, gold will have 2,081
documents in 18 packs, including ind-hi-sangraha-v; the gold check (`eval_v2.py`) will be re-run then.

## Limits

- Measured on 22 sample packs of 500 documents, not the full corpus. The full run may find romanised documents the
  sample does not have.
- The word list misses romanised text that uses words not on it (short SEO titles, single words, and common Telugu
  words such as naku, nannu, ani); see `eval_v1.md`.
- Precision and recall are measured at the contains level only: readers marked D2 for any romanised text, so there is
  no labelled set of mostly-romanised documents.

## Files

| file | what |
|---|---|
| `doc_detector.py` | document rule (romanised when more than 50% of the words are) |
| `indiclid_segments.py` | IndicLID as a segment classifier, labels cached in `indiclid/` (not committed) |
| `eval_v2.py`, `eval_v2.md` | word list against IndicLID, precision, recall and gold check |
| `indiclid_variants.py`, `eval_v2_indiclid_variants.md` | IndicLID with length and score thresholds |
| `token_share.py`, `romanised_token_share_v1.csv` | token share per language |
