#!/bin/zsh
# Build the PRIVATE Kaggle dataset folder for capstone/kaggle_t4.py. Usage:
#   capstone/make_kaggle_bundle.sh <lab checkout at the pinned commit> <this G10 checkout root> <heldout dir> <sft dir> <out dir>
# heldout dir: heldout_v1_bal60k.jsonl + _sources.jsonl; sft dir: dolly_train.jsonl / dolly_eval.jsonl (optional).
# Copies only what the script imports; writes BUNDLE_MANIFEST.json with the lab commit and a sha256 per file.
set -euo pipefail
LAB=$1; G10=$2; HELD=$3; SFT=$4; OUT=$5
[[ -e $OUT ]] && { echo "refusing: $OUT exists"; exit 1; }
mkdir -p $OUT/lab/teams $OUT/teams $OUT/overlay/configs/arms $OUT/overlay/experiments $OUT/heldout $OUT/sft
T5=$LAB/teams/05-architecture
mkdir -p $OUT/lab/teams/05-architecture $OUT/lab/teams/04-ke2
cp -R $T5/harness $OUT/lab/teams/05-architecture/
cp -R $LAB/teams/04-ke2/src $OUT/lab/teams/04-ke2/
cp $T5/configs/runtime.yaml $OUT/overlay/configs/
cp $T5/configs/arms/{t1,t2,exp2_muon}.yaml $OUT/overlay/configs/arms/
cp $T5/experiments/plan_v1.md $OUT/overlay/experiments/
mkdir -p $OUT/teams/10-post-training/sft
for d in capstone rl-loop dt chat-format special-tokens rl rl-data; do cp -R $G10/teams/10-post-training/$d $OUT/teams/10-post-training/; done
cp -R $G10/teams/10-post-training/sft/bench $OUT/teams/10-post-training/sft/
cp $G10/teams/10-post-training/sft/{train_probe.py,convert.py} $OUT/teams/10-post-training/sft/
cp $HELD/heldout_v1_bal60k.jsonl $HELD/heldout_v1_bal60k_sources.jsonl $OUT/heldout/
# SFT rows and RL screen inputs, by these names when present: {dolly,ocr2}_{train,eval}.jsonl, rl_tasks.jsonl, rl_easy_ids.txt
for f in dolly_train.jsonl dolly_eval.jsonl ocr2_train.jsonl ocr2_eval.jsonl rl_tasks.jsonl rl_easy_ids.txt; do
  [[ -f $SFT/$f ]] && cp $SFT/$f $OUT/sft/
done
find $OUT -name __pycache__ -type d -prune -exec rm -rf {} +
python3 - "$OUT" "$(git -C $LAB rev-parse HEAD)" <<'PY'
import hashlib, json, pathlib, sys
out, commit = pathlib.Path(sys.argv[1]), sys.argv[2]
files = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob("*")) if p.is_file()}
(out / "BUNDLE_MANIFEST.json").write_text(json.dumps({"lab_commit": commit, "files": files}, indent=1))
print(len(files), "files")
PY
