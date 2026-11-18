#!/usr/bin/env python3
"""Save a Team 5 LanguageModel through Team 7's Checkpointer: a checkpoint store for the watcher's end-to-end test.

No trainer on main saves a LanguageModel through Team 7's Checkpointer yet, so this script makes the layout dry run 1
will have (commits.jsonl, latest.json, <branch>/step_<N>-e<E>/ with MANIFEST.json) from the model class dry run 1
trains. Between commits it takes a few AdamW steps on Team 7's synthetic tokens, so every commit holds other weights.
The probe is lm_eval_lab.probe_loss, the one the scorer checks at export. The model map is written to
<out>/model.json; pass it to the scorer with --model-config.

    python teams/09-evaluation/harness_lab/tests/make_lab_store.py --arm teams/05-architecture/configs/arms/t2.yaml \\
        --tokenizer <tokenizer.json> --tokenizer-sha256 <sha256> --byte-table <raw table .npz> --out <dir>

Writes only to --out. Not a training run: the weights are a few steps away from random.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent                                  # teams/09-evaluation/harness_lab
TEAM07 = LAB.parents[1] / "07-infrastructure"
sys.path[:0] = [str(LAB), str(TEAM07), str(TEAM07 / "support" / "simulation")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], allow_abbrev=False)
    ap.add_argument("--arm", type=Path, required=True, help="Team 5 arm YAML (configs/arms/...)")
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--tokenizer-sha256", required=True)
    ap.add_argument("--byte-table", type=Path, required=True)
    ap.add_argument("--n-layer", type=int, help="override the arm's layer count (a smaller model for a CPU test)")
    ap.add_argument("--commits", type=int, default=3)
    ap.add_argument("--final", action="store_true",
                    help='commit the last checkpoint with reason "final", as Team 7\'s trainer ends a run')
    ap.add_argument("--steps-per-commit", type=int, default=2)
    ap.add_argument("--run-id", default="lab-store")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists() and any(a.out.iterdir()):
        ap.error(f"{a.out} is not empty: use a fresh folder")

    import torch
    import torch.nn.functional as F

    from ckpt.ckpt import Checkpointer
    from lm_eval_lab import build_model, load_model_config, probe_loss, week2
    from trainer.tiny import SyntheticLoader

    os.environ["TOKENIZER_SHA"] = a.tokenizer_sha256          # recorded in MANIFEST.json env.tokenizer_sha
    torch.use_deterministic_algorithms(True)
    m = load_model_config(a.arm)
    if a.n_layer:
        m["n_layer"] = a.n_layer
    Artifacts, _ = week2()
    art = Artifacts(a.tokenizer, a.byte_table, expected_tokenizer_sha=a.tokenizer_sha256, expected_vocab=m["vocab_size"])
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "model.json").write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")
    model = build_model(m, art).train()
    print(f"model: {sum(p.numel() for p in model.parameters()):,} parameters ({a.arm.name}, n_layer {m['n_layer']})")
    optim = torch.optim.AdamW(model.parameters(), lr=1e-3)
    loader = SyntheticLoader(0, 2, 0, 1)
    code = (LAB / "lm_eval_lab.py", LAB.parents[1] / "05-architecture" / "harness" / "week2" / "model.py", Path(__file__))
    ck = Checkpointer(a.run_id, str(a.out / "local"), str(a.out / "store"), config_path=str(a.arm), seed=0,
                      code_paths=tuple(str(p) for p in code))
    threads, step = torch.get_num_threads(), 0
    for n in range(1, a.commits + 1):
        t0 = time.perf_counter()
        reason = "final" if a.final and n == a.commits else "interval"
        for _ in range(a.steps_per_commit):
            ids = loader.next()                     # Team 7's synthetic ids (0..255), valid ids of any vocab
            logits = model(ids[:, :-1], torch.ones_like(ids[:, :-1], dtype=torch.bool))
            loss = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), ids[:, 1:].reshape(-1))
            optim.zero_grad(set_to_none=True)
            loss.backward()
            optim.step()
            step += 1
        torch.set_num_threads(1)                    # the probe bits must match run_lab_ckpt.py's export settings
        if not (ck.save(step, model, optim, loader, probe_loss, tokens=step * ids.numel(), reason=reason) and ck.wait()):
            raise SystemExit(f"checkpoint at step {step} was not committed")
        torch.set_num_threads(threads)
        model.train()
        print(f"committed step {step} ({reason}, loss {loss.item():.3f}) in {time.perf_counter() - t0:.1f} s", flush=True)
    print(f"run folder: {(a.out / 'store' / a.run_id).as_posix()}")
    print(f"model config: {(a.out / 'model.json').as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
