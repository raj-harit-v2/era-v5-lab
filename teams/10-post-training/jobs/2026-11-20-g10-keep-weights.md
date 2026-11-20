# G10 job request (DRAFT, not sent): keep one SFT arm's weights for Team 9

Same job as #587 with two extra flags. It runs the A2 and A4 arms as before and, for the one arm named by `--keep-arm`, also
writes its final plain weights through Team 7's Checkpointer as a run folder, the layout Team 9's `run_lab_ckpt.py --run-dir
<kept dir>/g10-sft-a2` takes (RL model scores, forgetting check). What was and was not read back is in the test log paragraph below.

```bash
python capstone/sft_job_v1.py --g5-root <lab checkout> --run-folder <dir with manifest.json/checkpoint.pt/summary.json> \
    --tokenizer tokenizer.json --byte-table raw_table_P32.npz --heldout H.jsonl --heldout-sources S.jsonl \
    --packs <shard-00000>/pack.firewalled.jsonl ... --rl-tasks cc.jsonl --rl-ids capstone/probe_rl_easy_ids.txt \
    --device cuda --out out/ \
    --keep-weights-dir kept/ --keep-arm a2
```

What leaves the job: one run folder `kept/g10-sft-a2/` (latest.json, commits.jsonl, one step folder with the weights and Team 7's
MANIFEST.json), plus its path, manifest sha256 and step in `summary.json`. Size is the weights only, no optimizer state. Measured by
building the #587 model on CPU (Team 5 `configs/arms/t2.yaml` through `week2.config.load_runtime`, with a stand-in byte table; the script is in the evidence folder, not in this PR): 237,052,416 parameters, so 237,052,416 x 4
bytes = 0.948 GB (0.883 GiB) of fp32 weights, 0.953 GB with the byte-table buffers in the state dict. (An earlier estimate of about 183
million parameters, taken from the dry run 1 checkpoint size, was wrong.) The save was not timed at this size; the measured save is on the tiny stand-in (below).
What still never leaves: the built rows, the held-out answers, the generations and the other arm's weights, all deleted as in #587.
Nothing else changes: without the two flags the outputs are byte-identical to #587.

Test log (CPU, Mac, 19 Nov 2026; not a GPU run, not the real checkpoint). The job script itself, on a stand-in run folder (Team 5 week2 model,
width 64, 2 layers, trained 20 CPU steps with this tree's Team 5 code), with the same reduced settings as the #587 CPU log plus
`--keep-weights-dir kept/ --keep-arm a2`: exit 0, 5 of 5 steps ok, 313.6 s wall, run folder `kept/g10-sft-a2/` of 46 MB (10.6 million
parameters). Team 7's `export_safetensors` run with Team 9's own model builder and probe (`lm_eval_lab.build_model`, `probe_loss`) on that
folder: integrity and probe bits pass, the exported file loads `strict=True` into a fresh Team 5 LanguageModel, and its whole-file sha256
equals the one the job's reload check recorded. The default `run_lab_ckpt.py` smoke scorer cannot read it: it builds Team 5's tiny MoE, so
the keys differ. The real scorer (`--scorer lm_eval_lab:team5`) needs `lm_eval`, which was not installed on this Mac, so scoring was not run.
`rl_job_v1.py --keep-weights-dir` on the same stand-in (stand-in reward, 3 updates, paused after 2 and resumed): exit 0 both times, the folder
`g10-rl-final` appears only after the last update. The RL job keeps the trainer's saved trainable tensors, which `rl-loop/train.py` stores in
bf16, laid over the start weights; so the kept RL weights are bf16-rounded on the trainable tensors (the rest are the start weights, fp32).
