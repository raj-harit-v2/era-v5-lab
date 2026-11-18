# Model card text: Training data, Data B part

Date: 16 Nov 2026

Section "Training data" of `teams/11-release/model_card/model_card_outline.md`: the public data sources, and the
problems we found in them. Owner teams: Data A, Data B (Data A leads). This file is the Data B part: the
Indian-language and code-adjacent sources. Release edits it into the model card and TSAI approves it.

## Text

Data B (the team for Indian-language and code-adjacent data) checked the Indian-language part of the training data.
It also checked the code-adjacent part: commit messages, notebooks and question-and-answer posts.

The Indian-language text comes from public collections: FineWeb-2, Sangraha, HPLT and IndicCorp. It covers Bengali,
Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Sanskrit, Tamil and Telugu. Sangraha has a verified part and a
synthetic part, which is machine-translated text.

The code-adjacent text comes from CommitPackFT, a public set of Kaggle notebooks, and Stack Exchange posts from the
StarCoder2 extra data.

Native readers read samples of each source. They labelled each document with a shared list of data problems. For each
language, the documents that both of their readers marked clean form a gold set. Data B uses the gold sets to test that
a cleaning rule does not harm good text.

The readers found these problems:

- The share of clean documents depends strongly on the source. The machine-translated part of Sangraha has the fewest
  clean documents of all the sources.
- Telugu has the least clean text of the languages that a second reader also checked.
- Native readers rated the machine-translated text. No language reached the quality bar that Data B proposed, so the
  native Indian-language share of the mix leaves translated text out.
- Romanised Indian-language text, an Indian language written in Latin letters, is rare in the samples. The mix caps it
  at 1% of the tokens of each language.
- Malayalam and Odia had no second reader, so Data B could not measure their clean share.

Indian scripts break easily. Data B looked for invisible characters, text in the wrong script, words cut before a vowel
sign, and lost joiner characters (ZWJ and ZWNJ). In the cleaned training shards, no joiner was lost from the text that
cleaning kept.

Text in Indian languages, in their own scripts, is 8% of every training batch.

## Where each statement comes from (for the review, not for the model card)

| Statement | Source |
|---|---|
| Sources of each pack | the lab's pack list (plan sheet of 24 Oct 2026): `HuggingFaceFW/fineweb-2`, `ai4bharat/sangraha`, HPLT 3.0, `ai4bharat/IndicCorpV2`, `bigcode/commitpackft`, `HuggingFaceTB/issues-kaggle-notebooks`, `bigcode/starcoder2data-extras` |
| Sangraha synthetic = machine-translated | #212 |
| Gold sets, readers, harm test | `diagnosis/DISEASES.md` section 5, `teams/02-data-b/gold/` |
| Clean share by source; Telugu; Malayalam and Odia | `teams/02-data-b/native_indic_share_v1.md`, sections 2 and 3 |
| Translated text rated, no language reaches the bar | `teams/02-data-b/translation/quality_v1.md`, `agreement_v1.md` (#440) |
| Romanised text rare; cap of 1% | `romanised/romanised_policy_v1.md`, #481; TSAI approved the number for public text on #460 |
| Joiners kept in the cleaned shards | #523 (`audit/audit_v1.csv`) |
| 8% of every batch | TSAI's comment on #460 (16 Nov) |

No other number is in the text, so no `[number: waiting for TSAI]` is needed. Problems that Data B found in the
code-adjacent packs are not in this version: their readers add them.
