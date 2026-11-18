# OCR-2 pack — proposed `max_sequence_tokens = 32768`

**Owner:** f20201351h-maker (G10)
**For:** TSAI signature at Gate 2 (Sat 14 Nov 2026), per TSAI's request of 12 Nov 2026.
**Status (14 Nov 2026):** accepted by TSAI as provisional for SFT data v1 (G10 group, decisions for the OCR-2 pack). The pack v1 is built at 32768 with the C3 tokenizer: no row is over the limit; the longest is 29,829 C3 tokens (`results/ocr2_pack_v1.md`). The measurements below are the original proposal's, on the v0.1 tokenizer.

**Original status:** proposal only. No pack is built and no SFT number is reported until TSAI signs this and the frozen C3 tokenizer is usable by Team 10.

## Proposal

`max_sequence_tokens = 32768` for the `sft-code-opencodereasoning-2` pack.

One line of reason: the longest kept sample is **29,851 tokens** (measured), so **32768** is the smallest standard cap that retains 100% of the kept 427,152 rows and 2,539,177,884 trained tokens; **16384** retains only 414,211 rows (96.97%) and 2,307,031,985 trained tokens (90.86%), silently discarding 12,941 rows and 232,145,899 trained tokens (9.14%), all from the 16k-32k band.

(The contexts the T2 development probes used — OLMoE-1B-7B-0924-Instruct at 4,096, Qwen3.6-35B-A3B-FP8 at 8,192, both with a 1,024 completion cap — were stand-ins and do not bound this value.)

## Measured

Context-length study over the 70-shard OCR-2 run (11 Nov 2026, `rendered` vs `kept` populations, all 70 shards, conservation holds exactly). Cap rule: a row is retained under cap C if its whole rendered sequence fits; rows over the cap are dropped whole; truncation is not modelled. A packer that adds a BOS/separator per row would add that many tokens per sample (inferred, not checked).

| Cap | Rows retained | % rows | Trained tokens retained | % trained | Rows dropped | Trained tokens dropped |
|---:|---:|---:|---:|---:|---:|---:|
| 4,096 | 180,026 | 42.15 | 355,697,114 | 14.01 | 247,126 | 2,183,480,770 |
| 16,384 | 414,211 | 96.97 | 2,307,031,985 | 90.86 | 12,941 | 232,145,899 |
| **32,768** | **427,152** | **100.00** | **2,539,177,884** | **100.00** | **0** | **0** |

Kept-population lengths: min 234, p50 5,007, p90 13,624, p95 15,529, p99 19,078, p99.9 23,696, **max 29,851**, mean 6,356.

## Why 32768 and not 16384

- 16384 would delete the 16k-32k band: 232M trained tokens (9.14%) and the longest, hardest reasoning traces — the band the 64k-effort examples concentrate in. This data cannot be re-created without another OCR-2 pass.
- The cost of 32768 at pack time is zero: nothing is filtered. Any attention cost arrives only if G5 chooses a 32k training context, which is G5's call, not this PR's. A shortened pack chosen here cannot be undone.
- 32768 is the smallest power-of-two cap that admits the measured longest row (29,851) with headroom.

## Tokenizer status (as stated by TSAI in G10, 12 Nov 2026)

- The frozen C3 sample-v0 tokenizer (sha256 `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3`; rebuild PASS on 02 Nov 2026, `teams/03-tokenizer/jobs/2026-11-02-c3-s0-rebuild.log`; Gate 2 evidence per the G3 README) is on Soham's Kaggle dataset.
- Rajiv asked Soham and Harini to add the waiting people.
- TSAI asks for a route that needs no per-version access going forward.
- Until Team 10 can use the file, admission of the pack and any SFT number are held by TSAI's instruction. This PR does not attempt admission: `pack_admission.py --mode report` exits blocked on the missing approved tokenizer and the unset context limit, and that is the expected state.

## What this PR does not do

- No admitted data, no pack, no training, no SFT numbers.
- No change to `ocr2_policy.json`, the licence table, the mix, or any decision TSAI owns.
- No claim that 32768 is optimal for quality; it is the smallest standard cap that loses nothing measurable. Quality effects beyond this are unmeasured and are not claimed.
