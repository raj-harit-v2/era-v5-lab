"""Write the probe file a delivered Team 5 run folder needs before G10's adapter accepts it.

`rl-loop/team5_adapter.py` refuses a run folder of origin `g5_delivery` unless it is given
`{"ids": [...], "expected_mean_nll": <float>, "atol": <float>}`: the mean next-token NLL of the delivered weights on a
short fixed token sequence, computed WITHOUT the adapter. The adapter then computes the same number through its own
loading and forward code and stops on a difference above `atol`. Team 5's harness does not write such a number and a
run that was not saved by Team 7's Checkpointer has no `probe_loss`, so this script computes it.

It uses Team 5's code only, the way `teams/05-architecture/harness/save_hidden_vectors.py` loads a finished run:
`Artifacts`, `LanguageModel(config["model"], bytes, lengths)`, `load_state_dict(checkpoint["model"])`, and the trainer's
own loss `train_week2.scored_ntp_loss`. Nothing from `team5_adapter.py` is imported, so the two numbers are independent
except for the weights and Team 5's model class.

Numerics: float32, no autocast, `model.eval()`. That is what the adapter's probe check runs, on any device. Run this
with the same `--device` the job will use; the device and torch version are recorded in the file.

    python teams/10-post-training/capstone/make_probe_file.py --g5-root <REPO> --run <RUN_FOLDER> \
        --tokenizer <TOKENIZER_JSON> --byte-table <RAW_TABLE_NPZ> --out <PROBE_JSON> [--device cpu|cuda]

then pass `--probe-file <PROBE_JSON>` to `capstone/rl_job_v1.py` (or `make_adapter_config.py`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# A fixed sentence with prose, digits and a line of code. It only has to be short and fixed; it is not data.
PROBE_TEXT = ("The probe checks that two loaders agree on one checkpoint. 12 + 30 = 42.\n"
              "def add(a, b):\n    return a + b\n")
DEFAULT_ATOL = 1e-4  # the adapter's own default


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_ids(text: str) -> list[int]:
    try:
        ids = [int(t) for t in text.replace(",", " ").split()]
    except ValueError as e:
        raise ValueError(f"--ids must be integers separated by commas or spaces: {e}") from None
    return ids


def check_ids(ids: list[int], vocab_size: int, block_size: int) -> None:
    if len(ids) < 2:
        raise ValueError("the probe needs at least 2 token ids (one next-token target)")
    if len(ids) > block_size:
        raise ValueError(f"{len(ids)} probe ids exceed the run's block_size {block_size}")
    if min(ids) < 0 or max(ids) >= vocab_size:
        raise ValueError(f"probe id outside the vocabulary of {vocab_size}")


def compute(g5_root: Path, run: Path, tokenizer: Path, byte_table: Path, device: str = "cpu",
            ids: list[int] | None = None, atol: float = DEFAULT_ATOL) -> dict:
    """The probe record for `run`, from Team 5's loader and Team 5's loss. Raises ValueError on any identity mismatch."""
    harness = (Path(g5_root) / "teams" / "05-architecture" / "harness").resolve()
    if not (harness / "train_week2.py").is_file():
        raise ValueError(f"train_week2.py not found under {harness}")
    if str(harness) not in sys.path:
        sys.path.insert(0, str(harness))
    import torch  # noqa: PLC0415
    from train_week2 import model_hash, scored_ntp_loss  # noqa: PLC0415
    from week2.artifacts import Artifacts  # noqa: PLC0415
    from week2.model import LanguageModel  # noqa: PLC0415

    run = Path(run)
    man_path, ck_path = run / "manifest.json", run / "checkpoint.pt"
    for p in (man_path, ck_path):
        if not p.is_file():
            raise ValueError(f"{p} is missing: --run must be the output folder of train_week2.py")
    manifest = json.loads(man_path.read_text(encoding="utf8"))
    cfg, want = manifest["config"], manifest["artifacts"]
    # The manifest names the tokenizer the run used; Artifacts refuses a file with another sha256.
    artifacts = Artifacts(tokenizer, byte_table, expected_tokenizer_sha=want["tokenizer_sha256"],
                          expected_vocab=want["vocab_size"])
    if artifacts.identity() != want:
        raise ValueError("tokenizer or byte table differs from the ones the run used")
    if device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA unavailable")
    dev = torch.device(device)
    checkpoint = torch.load(ck_path, map_location=dev, weights_only=False)
    if checkpoint["identity_sha256"] != manifest["identity_sha256"]:
        raise ValueError("checkpoint.pt and manifest.json come from different runs")
    model = LanguageModel(cfg["model"], artifacts.bytes, artifacts.lengths).to(dev)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    weights = model_hash(model)
    summary_path = run / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf8"))
        if summary.get("steps") == checkpoint["step"] and summary.get("final_model_sha256") != weights:
            raise ValueError("loaded weights differ from final_model_sha256 in summary.json")

    text = None
    if ids is None:
        text, ids = PROBE_TEXT, list(artifacts.encode(PROBE_TEXT))
    check_ids(ids, cfg["model"]["vocab_size"], cfg["model"]["block_size"])
    seq = torch.tensor([ids], dtype=torch.long, device=dev)
    inputs, targets = seq[:, :-1], seq[:, 1:]  # position t predicts token t+1; every target is scored
    with torch.no_grad():
        total = float(scored_ntp_loss(model, inputs, targets))
    n = targets.numel()
    mean = total / n
    if mean != mean or mean in (float("inf"), float("-inf")):
        raise ValueError(f"probe NLL is not finite ({mean})")
    return {
        "ids": ids, "expected_mean_nll": mean, "atol": float(atol),
        "targets": n, "text": text, "ids_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
        "computed_by": "capstone/make_probe_file.py: Team 5 Artifacts + LanguageModel + train_week2.scored_ntp_loss, "
                       "float32, no autocast, eval mode; team5_adapter not imported",
        "device": device, "torch": torch.__version__,
        "run": {"run_id": manifest.get("run_id"), "identity_sha256": manifest["identity_sha256"],
                "step": checkpoint["step"], "model_hash_g5": weights, "status": manifest.get("status"),
                "manifest_sha256": sha256_file(man_path), "checkpoint_sha256": sha256_file(ck_path)},
        "g5_sources_sha256": {f.name: sha256_file(f) for f in
                              [harness / "train_week2.py", *sorted((harness / "week2").glob("*.py"))]},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--g5-root", type=Path, required=True, help="repository root that holds teams/05-architecture/harness")
    ap.add_argument("--run", type=Path, required=True, help="output folder of train_week2.py (manifest.json, checkpoint.pt)")
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--byte-table", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="probe json to write; must not exist")
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    ap.add_argument("--ids", help="token ids to use instead of the built-in sentence, separated by commas or spaces")
    ap.add_argument("--atol", type=float, default=DEFAULT_ATOL, help="tolerance written into the file (adapter default 1e-4)")
    a = ap.parse_args(argv)
    if a.out.exists():
        ap.error("output file exists; name a new file")
    try:
        rec = compute(a.g5_root, a.run, a.tokenizer, a.byte_table, a.device,
                      parse_ids(a.ids) if a.ids is not None else None, a.atol)
    except ValueError as e:
        ap.error(str(e))
    a.out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf8")
    print(f"probe file {a.out}: {rec['targets']} targets, expected_mean_nll {rec['expected_mean_nll']:.6f}, "
          f"atol {rec['atol']}, device {rec['device']}, weights {rec['run']['model_hash_g5'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
