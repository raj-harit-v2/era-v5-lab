# Smoke run of train_week2.py for the rotation job request (14 Nov 2026)

This is the test log for `../../2026-11-14-rotation-attn2-seed1237.md`. It shows that `train_week2.py` runs the two arms of the request end to end. It is a smoke run on tiny synthetic text. It is not a quality result, and every summary says `eligible_for_quality_comparison: false`.

- **What ran:** `attn2_swa128_sink.yaml` (attn-2) and `t2.yaml` (reference), seed 1237, CPU, fp32, 6 steps, context 160, batch 1, `--smoke --no-checkpoint`. The model keeps the T2 shape (about 237.05 million parameters, 8 layers, 16 routed and 1 shared expert), and the attn-2 manifest shows pattern L L L G L L L G, window 128, sink true.
- **Result:** both runs exit 0 and finish all 6 steps with finite losses. Training CE goes from 11.86 to 4.55 (attn-2) and from 11.87 to 4.73 (reference). Wall time is 22 s and 18 s. The log is `smoke.log`; each arm folder has `manifest.json`, `summary.json`, `metrics.jsonl`, `losses.txt` and `total_losses.txt`.
- **Tokenizer:** built from `theschoolofai/BrahmicTokenizer-131K` at commit `7dfcf398172c825c6689ad578e8b484ca5f57bc9` with `teams/03-tokenizer/v0/build_v0.py`. Its sha256 is `2de039f2…f8e5`, the one in `teams/03-tokenizer/v0/SHA256SUMS`.
- **Byte table:** `python teams/04-ke2/src/build_tables.py --tokenizer tokenizer_v0.json --out inputs/tables --pos-dims 32`. The raw P32 table has file sha256 `5e995086…dd77f` and content sha256 `47d411a9…f869f`, the same as in the TSAI attention records (`evidence/2026-11-10-attention-smoke/attn-0-cpu/command.json` and `evidence/2026-11-10-attention-screen/README.md`). The table in `teams/04-ke2/results/tables/` is bound to the baseline tokenizer, so the harness refuses it for v0.
- **Text:** `inputs/synthetic_train.jsonl` (4 documents) and `inputs/synthetic_heldout.jsonl` (3 documents: English, code, Hindi), written for this smoke run.
- **Environment:** Python 3.12, torch 2.5.1+cpu, tokenizers 0.20.3, numpy 2.2.5, PyYAML 6.0.3.

The paths in `smoke.log` are shown as `./inputs/...` and `./out/...`. The run used the same files from a scratch folder.

**With the real held-out files.** One more run of the attn-2 command used the real `heldout_v1` (`teams/05-architecture/heldout_v1/data/`), its sources file, `results/heldout_v1.sha256`, the held-out report and `--lr 0.001`, 2 smoke steps. The harness accepted all of them: the manifest was written with 1,059 held-out documents and held-out sha256 `21c6e4b2…4312bb`, the same as the TSAI attention screen. I stopped it after 500 seconds without a result, because scoring 1,059 documents on a CPU is too slow. It is not part of the evidence above. The full-size run needs the GPU.

This smoke does not test the official run: no GPU, bf16, full context 2048, 1,221 steps or the real `heldout_v1` and training bundle. TSAI runs those.
