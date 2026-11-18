"""Deterministic WP5 pilot staging from the reproduced RL data v1 code_contests file (sha256 91ee9951...).
Eligible: statement <= 768 Qwen2.5-Coder tokens (prompt + 1024 new tokens fit max_model_len 2048).
Split by h = sha256("g10-wp5-split:" + id): held-out if int(h) % 10 == 0, else train; each ordered by h.
Train candidates = first 64 of train (mixed-band screen happens in the job). Held-out = first 48 of held-out,
NOT filtered by pass rate. Writes records (data: local/Modal volume only) and id lists, plus a metadata summary."""
import hashlib, json, collections
from pathlib import Path
from tokenizers import Tokenizer
SRC = Path("rldata_rebuild/out/v1/cc.jsonl")
assert hashlib.sha256(SRC.read_bytes()).hexdigest() == "91ee99512f0411aea2de4ca5eaf10b87b2d8f785ca73747bf8deb45dd6ea9be0"
tok = Tokenizer.from_file("qwen_tok/tokenizer.json")
rows = [json.loads(l) for l in open(SRC, encoding="utf-8")]
h = lambda i: hashlib.sha256(f"g10-wp5-split:{i}".encode()).hexdigest()
elig = [r for r in rows if len(tok.encode(r["statement"]).ids) <= 768]
train = sorted((r for r in elig if int(h(r["id"]), 16) % 10), key=lambda r: h(r["id"]))
held = sorted((r for r in elig if int(h(r["id"]), 16) % 10 == 0), key=lambda r: h(r["id"]))
tr, ho = train[:64], held[:48]
assert not {r["id"] for r in tr} & {r["id"] for r in ho}
out = Path("wp5/data"); out.mkdir(exist_ok=True)
(out / "pilot_tasks.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in tr + ho))
(out / "train_ids.txt").write_text("".join(r["id"] + "\n" for r in tr))
(out / "heldout_ids.txt").write_text("".join(r["id"] + "\n" for r in ho))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
meta = {"source_sha256": "91ee99512f0411aea2de4ca5eaf10b87b2d8f785ca73747bf8deb45dd6ea9be0", "v1_rows": len(rows),
        "eligible_le_768_tokens": len(elig), "train_pool": len(train), "heldout_pool": len(held),
        "train_candidates": len(tr), "heldout": len(ho),
        "train_by_judge": dict(collections.Counter(r["judge"] for r in tr)),
        "heldout_by_judge": dict(collections.Counter(r["judge"] for r in ho)),
        "files_sha256": {p.name: sha(p) for p in sorted(out.iterdir())}}
Path("wp5/staging.json").write_text(json.dumps(meta, indent=1)); print(json.dumps(meta, indent=1))
