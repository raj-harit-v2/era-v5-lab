# Indic sources v1: new sources and their licences, for the Gate 2 source list

Deliverable of #215. It is for Data A's `dedup/source_priority_v1.md`.

The file lists public Indic datasets the lab does not use yet (section 1), the sources it already has and how they could be extended to more languages (section 2), and the sources that are Out (section 3). Each one gets a decision under the lab's licence rule:

- **In:** permissive licences, CC-BY-SA (with attribution), and gpt-oss output.
- **Out:** non-commercial (NC), no-derivatives (ND) or no stated licence; text made by closed OpenAI, Anthropic or Google models, or by Llama models; and any source we can't trace. Research-only or non-commercial-only datasets are Out.

Licences, sizes and gating were read from each dataset card and the Hugging Face API on 31 Oct and 14 Nov 2026. The FinePDFs and FineWeb-2 sizes come from the Hugging Face size API (train split), because their cards have no per-language table. A licence tag is not legal clearance, so G10 has the final say. Nobody was contacted.

**Downloadable directly?** "Yes" means the files can be fetched with no sign-in step. "Click-through" means the dataset is gated on Hugging Face with automatic approval: you log in, accept the terms on the dataset page once, and then download with your HF token. No one has to be contacted for either.

All the Hugging Face sets can be downloaded with the `hf` CLI, for example:

```
hf download HuggingFaceFW/finepdfs --repo-type dataset --include "data/tam_Taml/train/*" --local-dir finepdfs
```

---

## 1. New Indic sources for consideration (In)

These datasets have no pack or G10 set in the lab in any language. FineWeb-2, Sangraha, IndicCorp, FinePDFs and Aya are already in the lab, so their proposed extensions to more languages or subsets are in section 2.4. Language codes: hi, bn, mr, ta, te, kn, gu, ml, or, pa, as, sa, ur.

| # | Dataset | Languages and size | Text type | Licence (card) | Generator | Downloadable directly? | Download path | Decision and reason |
|---|---|---|---|---|---|---|---|---|
| N1 | [Pralekha](https://huggingface.co/datasets/ai4bharat/Pralekha) | Docs: ur 331K; hi 307K; ta 224K; mr 203K; te 165K; pa 163K; bn 144K; gu 102K; ml 102K; kn 93K; or 69K (2.35M docs, 14.7 GB in all) | Document-level English-Indic aligned articles (PIB, Mann Ki Baat) | CC BY 4.0 | None (card: human-written or human-verified) | Yes | [`train/eng_<iso3>-*.parquet`](https://huggingface.co/datasets/ai4bharat/Pralekha/tree/main/train), [`alignable/<iso3>-*.parquet`](https://huggingface.co/datasets/ai4bharat/Pralekha/tree/main/alignable) | **In.** The lab has no document-level parallel text. Its unaligned part is sampled from Sangraha unverified, so dedup it against Sangraha unverified (E5) |
| N2 | [Wikipedia](https://huggingface.co/datasets/wikimedia/wikipedia) (dump 20231101) | Articles: hi 163K; bn 143K; mr 94K; te 88K; ml 86K; pa 51K; kn 31K; gu 30K; or 17K; as 12K; sa 12K; ta about 190K (2023-06 TFDS dump) | Encyclopedia | CC BY-SA 3.0 / GFDL | None | Yes | [`20231101.<code>/`](https://huggingface.co/datasets/wikimedia/wikipedia/tree/main), e.g. `20231101.ta/` | **In**, with attribution (CC-BY-SA). Check against Wikipedia-based benchmarks (IndicGenBench, IndicGLUE) before training |
| N3 | [Wikisource](https://huggingface.co/datasets/wikimedia/wikisource) (dump 20231201) | Texts: sa 23K; kn 15K; te 9K; ml 6K; ta 4.7K; hi 3.5K; mr 1.5K; as 1.2K; gu 0.8K; or 0.7K; pa 0.1K | Classical and public-domain literature | CC BY-SA 3.0 / GFDL | None | Yes | [`20231201.<code>/`](https://huggingface.co/datasets/wikimedia/wikisource/tree/main), e.g. `20231201.ta/` | **In**, with attribution. Covers much of the classical text that Project Madurai holds (Out, section 3) |
| N4 | [Aksharantar](https://huggingface.co/datasets/ai4bharat/Aksharantar) | Train word pairs: ml 4.1M; ta 3.2M; kn 2.9M; te 2.4M; sa 1.8M; mr 1.5M; hi 1.3M; bn 1.2M; gu 1.1M; ur 0.7M; pa 0.5M; or 0.3M; as 0.2M (26M in all) | Native word and romanised spelling pairs | Card prose: CC-BY (manual part), CC0 (mined and existing parts); the tag only says "cc" | None (pairs scored with IndicXlit, not written by it) | Yes | `<iso3>.zip`, e.g. [`tam.zip`](https://huggingface.co/datasets/ai4bharat/Aksharantar/blob/main/tam.zip) | **In.** For romanised (D2) work in `teams/02-data-b/romanised/` |
| N5 | [Dakshina](https://github.com/google-research-datasets/dakshina) | bn, gu, hi, kn, ml, mr, pa, ta, te, ur (+ sd, si): 25K-word lexicon and 10K romanised sentences per language | Romanisation lexicon, hand-romanised sentences, Wikipedia native text | CC BY-SA 4.0 | None (human-romanised) | Yes | [`dakshina_dataset_v1.0.tar`](https://storage.googleapis.com/gresearch/dakshina/dakshina_dataset_v1.0.tar) (repo archived Apr 2026, still downloadable) | **In**, with attribution. Good as a romanised test set |
| N6 | [BPCC](https://huggingface.co/datasets/ai4bharat/BPCC), human parts only (`wiki`, `daily`) | 22 languages; Wiki 644K and Daily 139K sentence pairs in all | Human-translated English-Indic sentences | CC-BY-4.0 (card, for BPCC-H Wiki and Daily) | None | Click-through | `wiki/<iso3>_<Script>.tsv`, `daily/<iso3>_<Script>.tsv` (after accepting terms) | **In** for these two parts. The mined and back-translated parts are not proposed (section 1.1) |
| N7 | [Shrutilipi](https://huggingface.co/datasets/ai4bharat/Shrutilipi) | 12 languages (bn, gu, hi, kn, ml, mr, or, pa, sa, ta, te, ur), 6,400+ hours in all; no per-language hours on the card | All India Radio news, audio and transcripts | CC BY 4.0 | None | Click-through | `<language>/train-*.parquet`, e.g. `tamil/` (68 shards; audio included, 271 GB in all) | **In.** Spoken-news register. Only the transcripts are needed, but they ship inside the audio parquet files |
| N8 | [IndicVoices](https://huggingface.co/datasets/ai4bharat/IndicVoices) | 22 languages, 11.2K transcribed hours in all; no per-language hours on the card | Natural, extempore and conversational speech; human transcripts | CC BY 4.0 | None | Click-through | `<language>/train-*.parquet`, e.g. `tamil/` (745 GB in all, with audio) | **In.** The only conversational and dialect register. Large download for a small amount of text |
| N9 | [MADLAD-400](https://huggingface.co/datasets/allenai/MADLAD-400) | Docs: hi 4.5M; ta 2.6M; ml 2.1M; te 1.7M; mr 1.7M; bn 1.1M; gu 660K; kn 658K; ur 467K; pa 151K; or 101K; as 34K (no sa folder) | Web (Common Crawl to Aug 2022) | ODC-By tag; card prose says CC-BY-4.0 | None | Yes | `data-v1p5/<code>/clean_docs_v2-*.jsonl.gz` | **In**, low priority. It is Common Crawl again, so most of it will dedup against fw2 |

### 1.1 In by licence, but not recommended (new datasets and extensions of existing ones)

| Dataset | Why not |
|---|---|
| [Sangraha](https://huggingface.co/datasets/ai4bharat/sangraha) **synthetic** for more languages (`synthetic/<lang_Script>/`) | IndicTrans2 translation of English Wikipedia. The rule allows it, but Data B measured `sangraha-s` at 5.0% clean, the lowest of any source |
| BPCC back-translation part | Generated by IndicTrans2 models. Same reason |
| BPCC mined part (`samanantar_v2/`, `nllb_filtered/`, `comparable/`) | Tagged CC0, but it repackages Samanantar, whose own card is CC-BY-NC-4.0. G10 should rule on it first |
| [Kathbath](https://huggingface.co/datasets/ai4bharat/Kathbath) | Read-aloud IndicCorp sentences, so its text repeats IndicCorp (E1) |
| [HPLT 3.0](https://hplt-project.org/datasets/v3.0) other languages (`wget -i https://data.hplt-project.org/three/sorted/<code>.map`) | Same terms as `ind-hi-hplt` (CC0 packaging, web terms for the text), which G10 left open. The Hindi HPLT pack is also only 12.4% clean |
| [CulturaX](https://huggingface.co/datasets/uonlp/CulturaX) | Gated, the licence just follows mC4 and OSCAR, and it is Common Crawl again |

### 1.2 Before training any of these

- Run G9's decontamination (FLORES, IN22, MILU, and Itihasa for Sanskrit). Wikipedia, Pralekha and the news sets need the most care.
- Dedup the Common Crawl sources (IndicCorp, Sangraha unverified, MADLAD) against the existing `fw2` and `sangraha-v` packs.
- Keep the attribution for the CC-BY and CC-BY-SA sources (E3, E5, E6, N1 to N8).

---

## 2. Existing Indic sources in the lab

These are the packs in `diagnosis/submissions/` (38 packs, 25 of them Indic), checked against `main` (`teams/01-data-a/jobs/2026-11-02-tokenizer-sample-v0-clean/tokenizer_sample_v0_manifest.json`, `teams/10-post-training/licences/licence_table.md`, `teams/05-architecture/heldout_v1/`) and the open PRs. #255's `dedup/source_priority_v1.md` ranks these packs only. No open PR adds a new Indic source.

### 2.1 Pretraining packs (sample v0)

| Source | Packs | Languages | Licence (G10 table or card) |
|---|---|---|---|
| [FineWeb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | `ind-<lang>-fw2` | hi, bn, mr, ta, te, kn, gu, ml, or, sa | ODC-By 1.0 |
| [Sangraha](https://huggingface.co/datasets/ai4bharat/sangraha) verified | `ind-<lang>-sangraha-v` | hi, bn, mr, ta, te, kn | CC-BY-4.0 |
| Sangraha synthetic | `ind-<lang>-sangraha-s` | hi, ta, te, kn | CC-BY-4.0 |
| [IndicCorp v2](https://huggingface.co/datasets/ai4bharat/IndicCorpV2) | `ind-hi-indiccorp` | hi | CC-BY-4.0 (G10) / CC0 (card) |
| [HPLT 3.0](https://data.hplt-project.org/three/sorted/hin_Deva) | `ind-hi-hplt` | hi | CC0 packaging / web terms (G10: not verified) |
| [chandassu](https://huggingface.co/datasets/BodduSriPavan111/chandassu) | `chandassu` (G10 stage 0) | te | MIT |

FinePDFs is in the lab for English only (`sci-finepdfs`), and Aya is in G10's SFT sets (2.2). Neither has an Indic pretraining pack.

Held-out only: FineWeb-2 test splits for 11 Indic languages, including pa and as (`heldout_v1`), which have no training pack.

### 2.2 SFT sets (G10)

| Source | G10 set | Decision in G10's table |
|---|---|---|
| [Aya Dataset](https://huggingface.co/datasets/CohereLabs/aya_dataset) | `sft-indic-aya-dataset` | TSAI reserves (human-written, Apache-2.0) |
| [Aya Collection](https://huggingface.co/datasets/CohereLabs/aya_collection), 12 templated Indic subsets | `sft-indic-aya-collection` | TSAI reserves (10 of 12 usable per `aya_licence_check.md`) |
| [indic-align](https://huggingface.co/datasets/ai4bharat/indic-align) `OpenAssistant_T`, `Dolly_T` | `sft-indic-indic-align-oasst-t`, `-dolly-t` | TSAI reserves / allowed with attribution |
| Coding and CS conversational Indic, orca-math Hindi, Aryabhatta, samvaad-hi, indic-instruct (Hindi), IndicGuard | various `sft-indic-*` | See G10's table |

### 2.3 Evaluation and decontamination (not training sources)

FLORES-200, IN22-Gen and IN22-Conv, MILU, IndicGenBench, Itihasa (Sanskrit), OneRuler. New sources must be checked against these.


### 2.4 Existing sources: proposed extensions (In)

These sources are already in the lab, but only for some languages or subsets. The rows below cover the languages and subsets that have **no pack yet**: none of them is in `diagnosis/submissions/` or in the sample-v0 manifest. They are recommendations, ordered by priority, and should be read together with section 1.

| # | Dataset | Languages and size | Text type | Licence (card) | Generator | Downloadable directly? | Download path | Decision and reason |
|---|---|---|---|---|---|---|---|---|
| E1 | [IndicCorp v2](https://huggingface.co/datasets/ai4bharat/IndicCorpV2) (all languages except hi, which the lab has) | bn, mr, ta, te, kn, gu, ml, or, pa, as, sa, ur. 20.9B tokens over 24 languages; no per-language size on the card | News and web | CC0 (card). G10's table lists CC-BY-4.0 for `ind-hi-indiccorp`; it is In either way | None | Yes | `data/<code>.txt`, e.g. [`data/ta.txt`](https://huggingface.co/datasets/ai4bharat/IndicCorpV2/blob/main/data/ta.txt), `data/te.txt`, `data/pa.txt` | **In.** Permissive. `ind-hi-indiccorp` is the cleanest pack measured so far (85.0% clean, against 25.8% for fw2, `native_indic_share_v1.md`), and the same source exists for every other language. It is the best fix for Telugu (4.0% clean over its three packs) |
| E2 | [FineWeb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) `pan_Guru`, `asm_Beng` | pa 944K docs / 1.58 GB; as 267K docs / 0.39 GB | Web | ODC-By 1.0 | None | Yes | [`data/pan_Guru/train/`](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/tree/main/data/pan_Guru/train), [`data/asm_Beng/train/`](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/tree/main/data/asm_Beng/train) | **In.** Permissive, and already the lab's main Indic source. Punjabi and Assamese are scored in `heldout_v1` but have no training pack |
| E3 | [Sangraha](https://huggingface.co/datasets/ai4bharat/sangraha) **verified**, for languages without a `sangraha-v` pack | Tokens: gu 3,648M; ml 2,731M; sa 1,329M; or 1,177M; pa 1,075M; as 292M | Web and PDFs, checked by AI4Bharat | CC-BY-4.0 | None | Yes | `verified/<iso3>/`, e.g. [`verified/guj/`](https://huggingface.co/datasets/ai4bharat/sangraha/tree/main/verified) | **In.** Same source and licence as the six `sangraha-v` packs. It gives gu, ml, or and sa a second source, and pa and as their first |
| E4 | [FinePDFs](https://huggingface.co/datasets/HuggingFaceFW/finepdfs) | hi 849K docs / 12.95 GB; bn 539K / 6.33 GB; mr 185K / 3.26 GB; ta 99.6K / 3.12 GB (4.61B Llama-3.2 tokens); sa 19.5K / 1.60 GB; gu 83K / 1.41 GB; pa 14.6K / 0.39 GB; ml 53.5K / 0.27 GB; te 31K / 0.22 GB; kn 35K / 0.22 GB; or 5.7K / 0.03 GB; as 1.5K / 0.01 GB | Long-form text extracted from PDFs (reports, books, government and academic papers) | ODC-By 1.0 | None (extracted, not generated) | Yes | `data/<iso3>_<Script>/train/`, e.g. [`data/tam_Taml/train/`](https://huggingface.co/datasets/HuggingFaceFW/finepdfs/tree/main/data/tam_Taml/train), `data/hin_Deva/train/` | **In.** Permissive. The lab uses FinePDFs for English only (`sci-finepdfs`). It is the only long-form Indic source and is large for hi, bn, mr and ta |
| E5 | Sangraha **unverified** | Tokens: hi 12,348M; bn 5,609M; ta 1,516M; mr 652M; te 647M; gu 597M; ml 548M; kn 389M; pa 137M | Web, not checked by AI4Bharat | CC-BY-4.0 | None | Yes | `unverified/<iso3>/`, e.g. [`unverified/tam/`](https://huggingface.co/datasets/ai4bharat/sangraha/tree/main/unverified) | **In**, after the Data B cleaning rules. Worth it mainly for hi, bn and ta |
| E6 | [Aya Collection (language split)](https://huggingface.co/datasets/CohereLabs/aya_collection_language_split), templated Indic subsets only | Folders `tamil/`, `hindi/`, `bengali/`, `telugu/`, `marathi/`, `gujarati/`, `kannada/`, `malayalam/`, `panjabi/`, `urdu/`. Tamil about 4.15M rows (all subsets) | Templated instruction data (SFT) | Apache-2.0 | None for the templated subsets (fluent-speaker templates over existing data) | Yes | [`<language>/`](https://huggingface.co/datasets/CohereLabs/aya_collection_language_split/tree/main), e.g. `tamil/` | **In for the templated subsets only**, the same ones G10 already allows (`sft-indic-aya-collection`, `aya_licence_check.md`), e.g. `templated_tamil_stories`, `templated_tamil_thirukkural`. This repo is the per-language copy of `aya_collection`. Its `translated_*` subsets are Out (section 3) |

---

## 3. Out

| Dataset | Licence (card) | Downloadable directly? | Decision and reason |
|---|---|---|---|
| [Varta](https://huggingface.co/datasets/rahular/varta) | "cc", with no version or variant | Yes | **Out**, no traceable licence. "cc" alone could be NC or ND. It covers ta and 14 other languages, so it is worth asking TSAI whether the authors' paper states a licence |
| [XL-Sum](https://huggingface.co/datasets/csebuetnlp/xlsum) | CC BY-NC-SA 4.0 | Yes | **Out**, non-commercial |
| [Updesh_beta](https://huggingface.co/datasets/microsoft/Updesh_beta) | Microsoft Research License: non-commercial research only | Yes | **Out**, research-only. It also uses Llama-3.1-405B and Llama 3.3 70B in its pipeline. G10 has already excluded it (`sft-indic-updesh`) |
| [Aya Collection (language split)](https://huggingface.co/datasets/CohereLabs/aya_collection_language_split) `translated_*` subsets, and `templated_hindi_headline` | Apache-2.0 wrapper; upstream sources not listed | Yes | **Out.** The translations were made with NLLB-3.3B, whose model licence is CC-BY-NC-4.0. The English sources are not named, and at least one (`soda`) is InstructGPT output. G10 already excludes these (`sft-indic-aya-collection-other`). `templated_hindi_headline` is CC BY-NC-SA upstream |
| [Samanantar](https://huggingface.co/datasets/ai4bharat/samanantar) | CC-BY-NC-4.0 | Yes | **Out**, non-commercial |
| [IndicNLG suite](https://huggingface.co/datasets/ai4bharat/IndicSentenceSummarization) (sentence summarisation, headline generation) | CC-BY-NC-4.0 | Yes | **Out**, non-commercial |
| Tamil Alpaca / Tamil Orca | Built from GPT outputs | Yes | **Out**, text made by closed OpenAI models |
| [indic-align](https://huggingface.co/datasets/ai4bharat/indic-align), all subsets except `OpenAssistant_T` and `Dolly_T` | CC-BY-4.0 tag | Yes | **Out**, Llama-2-70B-Chat output. G10 already excludes it |
| [Project Madurai](https://www.projectmadurai.org) | No standard licence: each text must keep its credit header, and the coordinators ask to be contacted before redistribution | No (scrape, or an unofficial HF mirror) | **Out**, no stated licence, and TSAI asked us not to contact organisations. Wikisource (N3) covers much of it |
| Tamil Virtual Academy Corpus Bank, Noolaham, NDLI, LDC-IL, TDIL-DC | No open licence found | No (registration or request) | **Out**, no stated licence, and access means contacting them |
