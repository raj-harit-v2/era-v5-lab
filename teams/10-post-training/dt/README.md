# Deletion Tuning (DT)

`mask.py` ports the official Deletion Tuning code (agentic-learning-ai-lab/deleting-weights @ `94f0340e`, MIT; paper
arXiv 2611.10866v1 §4-5.1) for the SFT bench. One FP32 logit G per targeted weight; training uses W·sigmoid(αG), every
evaluation uses W·1[G>0] (baked into plain `nn.Linear` by `bake()`, so any Hugging Face loader sees the hard mask).
Differences from the official code: a present bias is kept, Wanda norms skip padding tokens, masks are packed with
numpy.packbits + zlib.

```bash
python sft/bench/train.py --train <slice>/train.tok.jsonl --model <dir> --revision none --tokenizer-dir <dir> \
    --method dt --dt-targets gate --lr 2e-3 --steps 400 --device cuda --autocast bf16 --grad-checkpointing --out <run>
python -m pytest dt/tests -q        # 12 tests, CPU, no download
```

`--train-marker-rows` (with `--method dt` or `lora`) also trains the embedding rows of the mapped chat markers. That is a
**hybrid control**, not pure DT; it needs `--wd 0`. Results: `../results/dt_sft_surrogate.md`. `run_triple.sh` reproduces one
checkpoint's pure full / LoRA / DT row (job request `../jobs/2026-11-19-dt-vs-fft-1.7b.md`).

`LICENSE.upstream` preserves the official MIT notice. `analysis.py` collects evaluation-only per-row NLL and computes paired cluster-bootstrap intervals (see the report for measured scope):

```bash
python dt/analysis.py collect --model "$MODEL" --split-file "$SUPPLEMENT" --device cuda --out "$OUT/dt.json"
python dt/analysis.py bootstrap --arm "dt=$OUT/dt.json" --arm "full=$OUT/full.json" --pair dt:full --out "$OUT/bootstrap.json"
```

Raw per-row outputs are private. Aggregate intervals and parity metadata are in `../results/dt_bpb_uncertainty.json`. This is an offline forward-only analysis path, not a training hot path.
