# SFT v1 full C3 conversion: nvidia/Nemotron-Math-v2

```
Team:            10-post-training
Owner:           f20201351h-maker
Lead approval:   saitej123
Question:        How many rows, tokens, loss-masked targets and rows over 32,768 tokens does a full C3 conversion of nvidia/Nemotron-Math-v2 at revision 8e793210e175 give, and do all row checks pass?
Script:          teams/10-post-training/sft/sft_v1_records.py   (with sft/convert.py, chat-format/render.py and sft/results/sft_v1_hf_pins.json, all in this PR)
Command:         python teams/10-post-training/sft/sft_v1_records.py full --set sft-math-nemotron-math-v2 --tokenizer tokenizer.json --revisions-json teams/10-post-training/sft/results/sft_v1_hf_pins.json --local-root hub --out-dir out/full --record-dir out --budget-gb 300 --global-budget-gb 300 --max-hub-gb 63 --threads 4
Config:          teams/10-post-training/sft/results/sft_v1_hf_pins.json
Inputs:          nvidia/Nemotron-Math-v2 at 8e793210e175b6406c752a870f585f62de98c0d3, 50.3 GB, 5 parquet files, staged under hub/nvidia/Nemotron-Math-v2/ and checked first with: python teams/10-post-training/sft/sft_v1_records.py verify-local --set sft-math-nemotron-math-v2 --root hub --revisions-json teams/10-post-training/sft/results/sft_v1_hf_pins.json ; C3 tokenizer.json (sha256 15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3, supplied by TSAI; the script refuses any other file)
Hardware:        CPU
Max time:        6766 (minutes; estimate, see below)
Precision:       not used
Measures:        rows out, tokens, targets, effort rows, rows over 32,768, check failures, content_sha256 of each part
Expected result: from the 2,000-row test: 1964 of 2,000 rows convert, target share 99.3%, 293 rows over 32,768 in that prefix; all checks pass
Outputs:         out/sft-math-nemotron-math-v2.full.record.json (under 1 MB). The gzipped parts (about 269 GB, estimate) go to TSAI storage, not to the PR.
Test log:        teams/10-post-training/jobs/2026-11-14-sft-v1-math-v2-full.log
```

What the job does: streams nothing from the network. It reads the staged files, converts every row the adapter selects with `sft/convert.py` (chat-format v0, loss masks, C3 token ids), gzips each finished part and checks that it decompresses to the same bytes, runs the row checks (parse round trip, ids equal a fresh encode, decode equals the text or its C3-normalised form, no trained token outside an assistant span, no trained tool-result token, EOS last and untrained, unique ids), and reruns the first 2,000 rows to compare hashes. It stops if the output passes `--budget-gb`.

Estimate, not a measurement: 7,079,896 rows (the 6 Nov decontamination run's rows-in for this set, from an older conversion) at 27.07 rows/s (test, 4 threads, includes the Hub read) is about 73 hours of conversion, plus about 40 hours for the check pass at the test's check rate. The test prefix may not represent the rest of the set. 37.9 KB of gzip per output row in the test gives about 269 GB. More cores shorten the tokenizer part only.

What this output is not: it is a conversion, not a pack. It has not been through the decontamination run at this revision, no held-out id list has been applied, and it contains rows over 32,768 tokens that a pack must drop. Decontamination stays TSAI's applied step (rule 6 of the job rules); this job does not clean or filter rows. Licence state: allowed (CC-BY-SA, attribution needed).
