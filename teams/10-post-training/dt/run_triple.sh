#!/usr/bin/env bash
# Train and evaluate the pure full / LoRA / DT triple of the WP2 study for one checkpoint, seed 1, with the frozen settings
# (full 1e-4, LoRA r4 1e-3, DT gate_proj 2e-3; 400 steps x 8 rows; bf16 autocast, FP32 master; DT alpha 100->1000,
# eta 1/2048, lambda 1e-5). Writes only under $OUT. Usage: dt/run_triple.sh <model dir> <slice dir> <out dir>
set -euo pipefail
if [[ "$#" != 3 ]]; then
  echo 'Usage: run_triple.sh <model dir> <slice dir> <out dir>' >&2
  exit 2
fi
# Resolve caller-relative inputs before moving to the package directory.
MODEL="$(cd "$1" && pwd)"; SLICE="$(cd "$2" && pwd)"
mkdir -p "$3"
OUT="$(cd "$3" && pwd)"
cd "$(dirname "$0")/.."
mkdir -p "$OUT"
python sft/bench/evaluate.py --model "$MODEL" --split-file "$SLICE/test.tok.jsonl" --metrics bpb,format,forget --gen-limit 200 \
  --gen-batch 37 --token-budget 16384 --device cuda --generations-out "$OUT/base-test.gens.jsonl" --out "$OUT/base-test.json"
for spec in full:1e-4 lora:1e-3 dt:2e-3; do
  m="${spec%%:*}"; lr="${spec#*:}"
  python sft/bench/train.py --train "$SLICE/train.tok.jsonl" --model "$MODEL" --revision none --tokenizer-dir "$MODEL" \
    --method "$m" --steps 400 --lr "$lr" --seed 1 --device cuda --autocast bf16 --micro-tokens 8192 --grad-checkpointing \
    --log-every 50 --out "$OUT/$m"
  python sft/bench/evaluate.py --model "$OUT/$m/model" --split-file "$SLICE/test.tok.jsonl" --metrics bpb,format,forget \
    --gen-limit 200 --gen-batch 37 --token-budget 16384 --device cuda --generations-out "$OUT/$m-test.gens.jsonl" --out "$OUT/$m-test.json"
done
