"""Sample completions from a saved run state (or from the base model) and score them, without training.

    python sample_from_state.py --model <folder> --tasks tasks.jsonl --ids heldout=heldout_ids.txt --ids cohort=ids.txt \
        --out completions.jsonl [--state state.stepNNNNNN.pt] [--k 8] [--max-new 1024]

The sampler is the colocated vLLM engine alone: a state's trainable tensors are pushed into it exactly as the trainer
does after an update, so no training model is loaded. Writes one private JSON line per completion
{set, id, text, reward} (model text: never commit it) and prints pass rates only.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--ids", action="append", required=True, help="name=path, repeatable")
    ap.add_argument("--out", required=True)
    ap.add_argument("--state")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--max-new", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=4321)
    ap.add_argument("--workers", type=int, default=32)
    a = ap.parse_args()
    import score_pool  # noqa: PLC0415
    pool = score_pool.ScorePool(a.workers)  # before the engine loads
    import rollout  # noqa: PLC0415
    from transformers import AutoTokenizer  # noqa: PLC0415
    t0 = time.time()
    vllm = rollout.VLLMSampler(a.model, seed=a.seed, gpu_memory_utilization=0.85, max_model_len=2048)
    tok = AutoTokenizer.from_pretrained(a.model, local_files_only=True)
    vllm.bind(tok.eos_token_id, tok.pad_token_id, "cuda")
    step = None
    if a.state:
        st = torch.load(a.state, map_location="cpu", weights_only=False)
        step = st["step"]
        vllm.sync(list(st["trainable"].items()))
        del st
    by_id = {}
    for line in Path(a.tasks).read_text(encoding="utf-8").splitlines():
        if line.strip():
            t = json.loads(line)
            by_id[t["id"]] = t
    gen = torch.Generator().manual_seed(a.seed)
    summary = {"state_step": step, "k": a.k, "sets": {}}
    with open(a.out, "w", encoding="utf-8") as f:
        for spec in a.ids:
            name, path = spec.split("=", 1)
            ids = [x.strip() for x in Path(path).read_text().splitlines() if x.strip()]
            prompts = []
            for i in ids:
                p = tok.apply_chat_template([{"role": "user", "content": by_id[i]["statement"]}],
                                            add_generation_prompt=True, tokenize=True)
                prompts.append([int(x) for x in (p["input_ids"] if hasattr(p, "keys") else p)])
            rolls = vllm.sample(prompts, a.k, a.max_new, 1.0, gen)
            items, owner = [], []
            for i, p, r in zip(ids, prompts, rolls):
                for row, m in zip(r.seq[:, len(p):], r.cmask):
                    items.append((by_id[i], tok.decode(row[m].tolist(), skip_special_tokens=True)))
                    owner.append(i)
            res = pool.score(items)
            for i, (_, text), r in zip(owner, items, res):
                f.write(json.dumps({"set": name, "id": i, "text": text, "reward": float(r["reward"])}) + "\n")
            summary["sets"][name] = {"problems": len(ids), "completions": len(res),
                                     "pass": sum(r["reward"] for r in res) / max(len(res), 1)}
    pool.close()
    summary["seconds"] = round(time.time() - t0, 1)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
