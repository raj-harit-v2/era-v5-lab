# End-to-end frozen C3 smoke

RTX 3070 Laptop GPU (8 GiB), CUDA BF16, PyTorch 2.5.1. Seed 1235, 3 steps, context 32, global batch 2, microbatch 2. The checkout used for this smoke was a local copy of the #441 speed-fix integration plus the C3 scoring patch in this directory, with checked-in runtime.yaml. The official request pins 71bc0fb with TSAI's Gate 2 speed fixes and staged runtime_fast.yaml. Those official inputs and the full T2 shape remain unverified here.

The two synthetic files in this directory contain decomposed Bengali nukta so this test exercises the normalization and byte-accounting path. Stage them under ./inputs/, alongside the verified tokenizer_c3.json and raw_table_c3_P32.npz. Leave G5_DOCUMENT_CACHE_DIR unset. Run from the test checkout root with the tested Python environment active.

```bash
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_muon.yaml --runtime teams/05-architecture/configs/runtime.yaml --tokenizer-release frozen-c3 --tokenizer ./inputs/tokenizer_c3.json --byte-table ./inputs/raw_table_c3_P32.npz --train-data ./inputs/synthetic_train.jsonl --heldout-data ./inputs/synthetic_heldout.jsonl --device cuda --seed 1235 --smoke --smoke-steps 3 --smoke-seq-len 32 --smoke-batch-size 2 --no-checkpoint --out ./out/c3-smoke
```

Exit 0. The trainer writes its output to files. Last lines from summary.json:

```text
  "first_ce": 11.539518356323242,
  "last_ce": 5.380922317504883,
  "final_model_sha256": "fe7162c4a31a1bc0ade3a5c539dc479f28d21ef72f44ddb8e532d0a886d7b910",
  "eligible_for_quality_comparison": false
}
```

Measured trainer wall time: 5.98 seconds. The pinned-base C3 patch also loaded the full original heldout_v1: 1,059 documents, 15 slices, 3,775,551 original bytes, and 3,762,753 normalized bytes.
