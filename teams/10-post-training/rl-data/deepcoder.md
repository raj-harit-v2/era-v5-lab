# DeepCoder Python pilot for Week 3 Task 2

TSAI approved [DeepCoder](../licences/licence_table.md#rl-code-deepcoder--deepcoder-preview-dataset) on 6 November for training-split rows that pass Team 9 decontamination. This pilot uses only Python stdin/stdout tasks from the `primeintellect` training configuration. The builder pins the first shard by SHA-256. That fixes the source rows and keeps `lcbv5` and the test split out of the build.

The adapter produces records for the existing [stdio scorer](stdio_check.py) and [pass-rate filter](filter.py). Candidate code runs in the network-disabled Python Docker sandbox. The scorer compares the whitespace-separated output tokens on the host, where the expected values stay. Every accepted task uses all its published cases. The builder limits eligibility to the scorer's case and output limits and requires a fenced Python reference. Problems that need a custom checker or numeric tolerance may be rejected by the token comparison.

## Evidence

The [manifest](deepcoder_pilot.json) records a pilot over the first 20 source rows. The adapter accepted 17 candidates. Team 9 v2 full-set decontamination removed 3 benchmark overlaps and found 0 canaries. The recheck found 0 overlaps on the 14 retained statements. Four references disagreed with the token comparison. The manifest lists each skipped row ID and the verifier's reason. The other **10 tasks** scored **1** for the published reference and **0** for a valid Python program that prints nothing. Each retained task ran 18 or 19 cases.

Verification used Python 3.12 and the existing `python:3.12-slim` image resolved to `python@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30`. The Docker regression test also checks that a program that subtracts instead of adding scores **0** on the addition fixture. The manifest records the real source IDs, results and hashes. The local output pack includes statements and tests, with references removed.

## Rebuild

Run from the repository root with Python 3.10 or later, PyArrow, and a running Docker daemon. The source shard is about 450 MiB. Store the shard, intermediate files and built pack outside Git.

```bash
rl_data=teams/10-post-training/rl-data
pilot_dir=$(mktemp -d)
shard=train-00000-of-00005.parquet
revision=780aeec7b7716e34f0b9e02bb624fc6ad8384725
source=https://huggingface.co/datasets/agentica-org/DeepCoder-Preview-Dataset
curl --fail --location "$source/resolve/$revision/primeintellect/$shard" -o "$pilot_dir/$shard"

python "$rl_data/build_deepcoder.py" prepare --shard "$pilot_dir/$shard" \
  --scan-rows 20 --out "$pilot_dir/candidates.jsonl"
python teams/10-post-training/sft/decontam_run.py --set rl-code-deepcoder \
  --input "$pilot_dir/candidates.jsonl" --text-field statement --out-dir "$pilot_dir/audit"

sandbox_image=python@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30
docker pull "$sandbox_image"
G10_RL_IMAGE="$sandbox_image" G10_STDIO_RUNNER=docker python "$rl_data/build_deepcoder.py" verify \
  --record "$pilot_dir/audit/rl-code-deepcoder.record.json" \
  --out "$pilot_dir/tasks.jsonl" --manifest "$pilot_dir/manifest.json"
diff -u "$rl_data/deepcoder_pilot.json" "$pilot_dir/manifest.json"

G10_RL_IMAGE="$sandbox_image" G10_STDIO_RUNNER=docker python -m pytest \
  "$rl_data/test_deepcoder.py" "$rl_data/test_rl_data.py" -q -p no:cacheprovider
```

For a training job, run the [pass-rate filter](filter.py) on the rebuilt `tasks.jsonl` against the job's starting model. Use tasks that produce both passing and failing samples. This pilot establishes verifier behavior. Model pass rates and training reward are still to be measured.
