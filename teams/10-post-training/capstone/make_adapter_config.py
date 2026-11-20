"""Write a team5_adapter run_folder config for a folder Team 5's train_week2.py wrote (day-one and rehearsal use).

    python capstone/make_adapter_config.py --g5-root <lab checkout or bundle/lab> --run-folder <dir> \
        --tokenizer tokenizer.json --byte-table raw_table_P32.npz --origin g10_rehearsal --out adapter.yaml

With a git checkout the G5 commit is pinned and verified; without one (`--no-git`) every harness file is pinned by
hash instead. Trainable set: everything except the MoE routers (frozen for RL; SFT overrides per method).
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path

import yaml

SPECIAL = {"pad": {"token": "<|pad|>", "id": 130726}, "end_of_turn": {"token": "<|im_end|>", "id": 130816},
           "end_of_sequence": {"token": "<|endoftext|>", "id": 130822}, "im_start": {"token": "<|im_start|>", "id": 129994},
           "stop": ["end_of_turn", "end_of_sequence"]}


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_probe(path: Path) -> dict:
    """Team 5's probe for a delivered checkpoint: {"ids": [token ids], "expected_mean_nll": float, "atol": optional}.
    team5_adapter refuses an origin g5_delivery run folder without it (real mode needs probe.ids and probe.expected_mean_nll)."""
    import json  # noqa: PLC0415
    import math  # noqa: PLC0415
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    ids, nll = p.get("ids"), p.get("expected_mean_nll")
    if not (isinstance(ids, list) and len(ids) >= 2 and all(isinstance(i, int) and not isinstance(i, bool) and i >= 0 for i in ids)):
        raise ValueError(f"probe file {path}: 'ids' must be a list of at least 2 token ids")
    if isinstance(nll, bool) or not isinstance(nll, (int, float)) or not math.isfinite(nll):
        raise ValueError(f"probe file {path}: 'expected_mean_nll' must be a finite number")
    return {"ids": ids, "expected_mean_nll": float(nll), **({"atol": float(p["atol"])} if p.get("atol") is not None else {})}


def write_config(out: Path, g5_root: Path, run_folder: Path, tokenizer: Path, table: Path, team10: Path,
                 origin: str = "g10_rehearsal", require_git: bool = True, source_commit: str | None = None,
                 probe: dict | None = None) -> Path:
    import numpy as np  # noqa: PLC0415
    team5 = Path(g5_root) / "teams" / "05-architecture"
    files = {f"harness/week2/{p.name}": sha(p) for p in sorted((team5 / "harness" / "week2").glob("*.py"))}
    files["harness/train_week2.py"] = sha(team5 / "harness" / "train_week2.py")
    g5 = {"root": str(Path(g5_root).resolve()), "files_sha256": files}
    if require_git:
        g5["commit"] = subprocess.check_output(["git", "-C", str(g5_root), "rev-parse", "HEAD"], text=True).strip()
    else:
        g5.update(commit=None, pin="file_hashes", source_commit=source_commit)
    with np.load(table, allow_pickle=False) as z:
        content = str(z["table_sha256"])
    template = Path(team10) / "chat-format" / "chat_template.jinja"
    cfg = {"mode": "run_folder", "g5": g5,
           "run_folder": {"path": str(Path(run_folder).resolve()), "origin": origin,
                          "manifest_sha256": sha(Path(run_folder) / "manifest.json"),
                          "checkpoint_sha256": sha(Path(run_folder) / "checkpoint.pt")},
           "ke2": {"table": str(Path(table).resolve()), "table_file_sha256": sha(table), "table_content_sha256": content,
                   "vocab_size": 131072, "pos_dim": 32},
           "tokenizer": {"path": str(Path(tokenizer).resolve()), "sha256": sha(tokenizer),
                         "chat_template": str(template.resolve()), "chat_template_sha256": sha(template)},
           "special_tokens": SPECIAL,
           "trainable": {"router_patterns": [r"(^|\.)moe\.router\.weight$"],
                         "trainable_patterns": [r"^(?!.*\.moe\.router\.).*"]}}
    if probe is not None:
        cfg["probe"] = probe
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--g5-root", type=Path, required=True)
    ap.add_argument("--run-folder", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--byte-table", type=Path, required=True)
    ap.add_argument("--origin", choices=("g10_rehearsal", "g5_delivery"), default="g10_rehearsal")
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--source-commit")
    ap.add_argument("--probe-file", type=Path, help="json {ids, expected_mean_nll[, atol]} from Team 5; needed for --origin g5_delivery")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    write_config(a.out, a.g5_root, a.run_folder, a.tokenizer, a.byte_table, Path(__file__).resolve().parents[1],
                 a.origin, not a.no_git, a.source_commit, load_probe(a.probe_file) if a.probe_file else None)
    print(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
