"""Prepare a deterministic 38-pack synthetic smoke run; never reads or replaces TSAI's cleaned data."""
import json
from pathlib import Path
import random

import pyarrow as pa
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[4]
ROOT = REPO / "out/overlap_rerun_local"


def main():
    ROOT.mkdir(parents=True, exist_ok=False)
    config = json.loads((REPO / "teams/01-data-a/dedup/overlap.json").read_text())
    for index, pack in enumerate(config["expected_packs"]):
        rng = random.Random(index)
        words = [f"word{rng.randrange(1000000)}" for _ in range(100)]
        if pack.startswith("code-"):
            # Lexically valid assignment-like code in all configured lexers; 24 nonblank lines.
            original = "\n".join(f"value_{index}_{j} = input_{index} + {j};" for j in range(24))
            edited = original.replace(f"value_{index}_0", "edited", 1)
        else:
            original = " ".join(words) + " solve x = -2"
            edited = original.replace(words[0], "edited", 1)
        for split, texts in (("train", (original, edited)), ("heldout", (original, "unrelated " + pack))):
            path = ROOT / "inputs" / split / pack / "part-00000.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(pa.Table.from_pylist([
                {"pack_id": pack, "doc_id": f"{pack}-{split}-{i}", "text": text,
                 "url": f"https://example.invalid/{pack}/{split}/{i}"}
                for i, text in enumerate(texts)]), path)
    config.update(inputs="out/overlap_rerun_local/inputs", out="out/overlap_rerun_local/overlap")
    (ROOT / "overlap.json").write_text(json.dumps(config, indent=2) + "\n")
    dedup = json.loads((REPO / "teams/01-data-a/dedup/dedup.json").read_text())
    dedup.update(results=config["out"], inputs=config["inputs"], out="out/overlap_rerun_local/dedup")
    (ROOT / "dedup.json").write_text(json.dumps(dedup, indent=2) + "\n")
    print("Prepared synthetic inputs: 38 packs, 76 parts, 152 documents (76 train, 76 heldout).")
    print("Configs: out/overlap_rerun_local/{overlap,dedup}.json")


if __name__ == "__main__":
    main()
