# G3 Tokenizer: Gate 2 freeze report (10 Nov 2026)

> Gate 2 proposal. If the Thu 12 Nov retrain on Data A's cleaned sample beats C3 sample-v0 under the same rules (pass bar, no language worse, fresh build matches), this PR is updated with the new sha before Thu 12 Nov 23:59 IST. Otherwise C3 sample-v0 below is the frozen tokenizer.

## 1. Decision

Freeze **C3 sample-v0** as the G3 tokenizer for training.

| Field | Value |
|---|---|
| Candidate | C3 = o200k swap + slots_v2 + normalizer v1, v0.1 specials, text mix `mix_s0.json` |
| tokenizer.json sha256 | `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3` |
| Manifest | `train/c3_s0_manifest.json` (#195) |
| Vocab / merges | 131,072 / 130,460 |
| Special ids | 356, same ids as v0 (G10 v0.1 names in `g10_slot_00..04`) |

Why C3 over C1/C2: all three pass (#276), and C3 has the best mean Indic: C1 −16.28%, C2 −16.47%, C3 −17.10%. English and code are the same for all three (shared o200k base). C2's slot split helps Ta/Te/Kn/Or but costs Gu +5.0% and Pa +3.2%. C3's normalizer wins back most of Pa (−2.7%) and helps As −2.6% and Bn −1.6% on FLORES.

## 2. Pass bar (FLORES-200 + code, vs BrahmicTokenizer-131K = v0)

Bar: mean Indic lower, and English, HumanEval and MBPP at most 2% worse. Source: COMPARE.md (#276, Harini).

| Metric | Baseline | C3 | Change | Result |
|---|---|---|---|---|
| Mean Indic fertility | 2.8355 | 2.3505 | −17.10% | PASS |
| English fertility | 1.2352 | 1.2334 | −0.15% | PASS |
| HumanEval tok/char | 0.2951 | 0.2953 | +0.07% | PASS |
| MBPP tok/char | 0.3195 | 0.3203 | +0.25% | PASS |

C3 beats the baseline on all 12 FLORES languages. Biggest gains are on the v0 weak spots: Or −39.8%, Pa −22.4%, Mr −18.6%. On the held-out FineWeb-2 check split, the mean Indic change is −17.54% (COMPARE.md, sample-v0 section).

No outside tokenizer passes. Every one that beats the bar on Indic (Gemma-4, Sarvam-30B, Sarvam-1) is at least 13% worse on code.

## 3. Independent reproduction

| Check | Who | Result |
|---|---|---|
| Fresh build gives the same sha (TSAI job #218, no network) | TSAI queue, `jobs/2026-11-02-c3-s0-rebuild.*` | PASS, 15468e66…, 319 s CPU |
| Build twice locally | Soham, manifest `rebuild_sha256` | PASS |
| Kannada FLORES | Vijay Patil | 3.2734 → 2.7469 (−16.08%), matches #276 |
| Telugu FLORES | Pritish Nayak | 3.0292 → 2.5531 (−15.72%), matches #276 |
| Telugu web text (FineWeb-2 check, 189 docs) | Pritish Nayak | 2.9790 → 2.5237 (−15.28%), matches COMPARE.md |
| Odia FLORES + code | Deepjyoti Saha | 4.1287 → 2.4861 (−39.78%), matches #276 |
| Tamil FLORES | Stephen Raj Arokiasamy | 3.1166 → 2.5927 (−16.81%), matches #276 |
| Punjabi FLORES | Raghav Tayal | 2.5955 → 2.0129 (−22.45%), matches #276 |
| Baseline reference check | all of the above | PASS (max abs diff 0.0000) |

## 4. Round trip (#305, Riya)

`decode(encode(x)) == normalizer(x)` on the sample-v0 heldout text: 38 packs, 13,154 docs (up to 1,000 per pack, chosen by sha256 of doc_id).

| Tokenizer | Failures | Result |
|---|---|---|
| BrahmicTokenizer-131K | 0 | PASS |
| C3 sample-v0 | 0 | PASS |

The C3 normalizer changed 406 docs. That is expected: the round trip checks against the normalised text. Known caveat (normalizer.md, #134): Bn/Pa nukta text comes back in its composed form, so `decode(encode(x))` can differ from the raw `x`.

## 5. Cross-team checks

- **G4 collision count** (Avnish): v0, v0.1, v1-c1 and the committed C1–C3 all have V=131,072 and max 32 bytes, with 0 raw-table collisions at P=32/64. U+FFFD-collapse excess: C1 1,095, C2/C3 1,096 (v0: 1,141). Coverage of the sample-v0 shas (#195) was asked on 5 Nov; the answer is added here when it arrives.
- **G10 specials**: v0.1 ChatML markers are in place with unchanged ids (#173).
- **Team 4 hand-off** (Sonu Agarwal): the C1–C3 sample-v0 shas are sent to G4.
- **G12 llama.cpp round trip** (Shubham Saxena, task 9): runs on C3 sample-v0 with Team 3's held-out text. GGUF conversion drops the normalizer, so ids can differ on text the normalizer changes; G12 reports that as a known limit.

## 6. Known limits

- The sample has no Pa or As, so those blocks stay on corpus60.
- Gu check split: about 2.5% line overlap with the sample's train text, so Gu check gains may be slightly optimistic. FLORES Gu (−2.9%) is unaffected.
- Sarvam-1 still leads C3 on Telugu: by 16.5% on FLORES, shrinking to 6.2% on web text (Pritish).
- Windows: verify scripts need `transformers` + `PYTHONUTF8=1`, and `fetch_corpus.py` hashes LF but writes CRLF (Deepjyoti). Fix in progress (Dhruv Vyas).
- tokenizer.json (8 MB) is over pr-guard's 5 MB limit, so it is not in the repo. It lives on the private Kaggle dataset; rebuild it from the manifest.

## 7. release/

`release/SHA256SUMS` lists the frozen tokenizer.json and every repo file needed to rebuild it. Check with:

```
cd teams/03-tokenizer && sha256sum -c release/SHA256SUMS --ignore-missing
```

`tokenizer.json` itself is not in the repo (8 MB > 5 MB pr-guard limit); put the Kaggle copy at `release/tokenizer.json` to check it too. A fresh build gives the same sha: TSAI job #218 (`jobs/2026-11-02-c3-s0-rebuild.*`) and `rebuild_sha256` in the manifest.
