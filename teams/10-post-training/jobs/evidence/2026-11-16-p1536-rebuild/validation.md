# p1536 rebuild validation — 16 November 2026

This is execution evidence, not delivery of the training files. Shards 0–3 ran on Apple M1 Pro (8 cores, 16 GB); shards 4–69 ran on Civo (16 vCPU, 32 GB, MUM1). Every shard invoked the pinned `sft/run_ocr2.py` admission pipeline, followed by independent C3/p1536 effort recounts. The pack manifest records the source, code, policy and tokenizer hashes. No rows or private IDs are included here.

## CPU batch and final output

On Civo, from the staged work root:

```bash
export TOKENIZERS_PARALLELISM=false
for i in $(seq 1 6); do
  setsid nohup ~/venv/bin/python run_shards.py --tag final --shards 4:70 --workers 3 --min-free-gb 8 > ~/run_final_d$i.log 2>&1 < /dev/null &
  sleep 3
done
```

The orchestration driver is outside Git. Its public executable path is:

```bash
python teams/10-post-training/sft/run_ocr2.py --manifest ROOT/source_manifest.json --policy teams/10-post-training/sft/ocr2_policy.json --shards N --workers 1 --out-dir out/shard-N --mode admission
# --resume is added after an interrupted stage; N identifies one pinned source-manifest shard.
```

Final output: **66/66 complete, 0 final failures, 0 recount mismatches**. Wall time: **2 h 34 m 50 s**. Initial 18-way concurrency caused OOM failures; reducing to 12 workers allowed all interrupted shards to recover. This does not establish that 18 workers fit 32 GB. The mean recorded final invocation was 30 m 35 s; it excludes earlier terminated invocations for six resumed shards, while the total wall time includes recovery. Sampled peak load: 19.01; peak disk use: 64.23 GiB. See `civo_pass1_summary.json` for scope and events.

All 272 result/statistics/ID/log/monitor files (33,415,791 bytes) were copied back and individually checked against remote SHA256. The instance was then deleted with user approval. Training and held-out JSONL files for shards 4–69 were discarded after verification by the requested no-keep-pack pass.

## Aggregate and correctness

The existing aggregator, pointed at a separate combined directory, passed **48/48 checks over 70 shards**. Original Mac and Civo results were preserved. Held-out IDs match C3; the C3 records remain byte-identical. Every rendered row's p1536 effort recount matches its tier.

Results: 418,496 training rows, 8,507 held-out rows, 2,661,573,319 training tokens, maximum length 29,846, and 35 rendered rows changing effort tier. TSAI's provisional admission limit is 32,768. The 2,048-token length column is diagnostic only.

Independent semantic mask check on retained train and held-out packs 0–3, using W for the local rebuild workspace:

```bash
P0="$W/private/runs_kept/p1536/shard-00000/shards/shard-00000/pack"
PACKS=("$P0/pack.jsonl" "$P0/pack.heldout_eval_v1.jsonl")
for n in 00001 00002 00003; do
  PACKS+=("$W/private/packs/p1536/shard-$n/pack.jsonl" "$W/private/packs/p1536/shard-$n/pack.heldout_eval_v1.jsonl")
done
python teams/10-post-training/sft/check_pack_rows.py --pack "${PACKS[@]}" --tokenizer "$W/root/tokenizer/p1536.json" --report mask_check.json --dump "$W/private/token_mask_dump.txt"
```

Final output: `{"ok":true,"rows":32855,"max_length":19366,"violations":{},"trained_tokens_by_role":{"assistant":197584460}}`; **108.46 s** on M1 Pro CPU. For shards 4–69 the executed admission pipeline recomputed IDs and masks for every row. Full retained-pack comparisons and final SFT test results are attached in `publication_finalize.log`.

## Matched timing and limits

One matched shard-0 pair on the same contended M1 Pro, C3/p1536 seconds: render 174/179, pack 215/192, screen 1,987/1,926, pipeline wall 2,454/2,357. The C3 control reproduced all six 14-Nov file hashes; p1536 bytes change by design. One pair does not establish a causal speed difference. No matched TSAI six-worker/full-retention runtime was measured. The requested storage and runtime are estimates and caps.

Pinned fingerprints v2 omit HumanEval, HumanEval+, MBPP and MBPP+; these results do not claim coverage of those benchmarks. Fourteen source checks remain human decisions, with those keys excluded. Proofs/reserves, missing mix areas and storage delivery remain separate gates. This PR does not close the full SFT mixture or claim a completed TSAI storage run.

## Final publication checks

`pytest sft -q -p no:cacheprovider -rs`: **991 passed, 2 skipped in 91.58 s**, with OMP/MKL threads set to 2 and the pinned Team 9 tools enabled. Both skips are unset G10_BENCH_SLICE. The finalizer returned `FINALIZE_OK`; 40/40 C3 records remain unchanged. Before this final evidence attachment, local guard passed 46 files and the added-line scrub was clean. Final attached logs contain no rows, private IDs or user filesystem paths.
