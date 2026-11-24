"""Rebuild the run folder G10's jobs read from a Team 5 delivery whose weights are only in the Team 7 checkpoint store.

Dry run 2's job request (`teams/05-architecture/jobs/2026-11-22-dryrun2.md`, "Outputs") delivers
`manifest.json, summary.json, metrics.jsonl, losses.txt, total_losses.txt` and says "The checkpoint stays on the job
machine"; the weights are committed to the Team 7 store (`--checkpoint-store`, `--run-id`). Every G10 entry point
(`team5_adapter.py` run_folder mode, `make_probe_file.py`, `day_one_probe.py`, `sft_job_v1.py`, `rl_job_v1.py`,
`dryrun2_dt_compare.py`) reads `checkpoint.pt` beside the manifest, so they all refuse that delivery as it is.

This script reads the committed step with Team 7's own `ckpt.ckpt.export_safetensors` (file sha256, strict keys and,
on the same device class, the saved probe-loss bits are checked there), loads it strictly into Team 5's
`LanguageModel`, and refuses unless Team 5's `model_hash` of the loaded weights equals `summary.json`
`final_model_sha256`. Only then it writes `<out>/checkpoint.pt` = {"model", "step", "identity_sha256", "run_id"} (the
keys G10 reads; no optimizer or RNG state, so it cannot resume Team 5's run) plus copies of the delivered files.
No check downstream changes: the adapter still pins the Team 5 sources, the manifest hash, and the model hash.

    PYTHONPATH=<lab>/teams/07-infrastructure python teams/10-post-training/capstone/run_folder_from_store.py \
        --g5-root <lab checkout> --run-folder <delivered out/dryrun2-1234> --store <store root> \
        --tokenizer <tokenizer.json> --byte-table <raw_table_P32.npz> \
        --heldout-data <heldout jsonl the run used> --heldout-sources <its sources jsonl> --out <new run folder>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path

DELIVERED = ("manifest.json", "summary.json", "metrics.jsonl", "losses.txt", "total_losses.txt")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def delivery_facts(rf: Path) -> tuple[dict, dict, dict, int, str]:
    """manifest, summary, team7 block, committed final step and its store path; ValueError when the delivery cannot
    have its weights in a Team 7 store or the files disagree on the run."""
    if (rf / "checkpoint.pt").exists():
        raise ValueError(f"{rf} already has checkpoint.pt: pass it to the jobs as it is")
    manifest = json.loads((rf / "manifest.json").read_text(encoding="utf8"))
    summary = json.loads((rf / "summary.json").read_text(encoding="utf8"))
    t7 = manifest.get("team7_checkpoint")
    if not t7 or not t7.get("run_id"):
        raise ValueError("manifest.json has no team7_checkpoint: the run did not commit to a Team 7 store")
    if summary.get("run_id") != t7["run_id"] or manifest.get("run_id") != t7["run_id"]:
        raise ValueError(f"run_id differs: manifest {manifest.get('run_id')}, summary {summary.get('run_id')}, "
                         f"team7 {t7['run_id']}")
    step = summary.get("steps")
    path = summary.get("team7_checkpoint_path")
    if not isinstance(step, int) or isinstance(step, bool) or not path:
        raise ValueError("summary.json lacks steps/team7_checkpoint_path: the final step was not committed")
    return manifest, summary, t7, step, path


def build(a) -> dict:
    rf = a.run_folder
    manifest, summary, t7, step, path = delivery_facts(rf)
    harness = (a.g5_root / "teams" / "05-architecture" / "harness").resolve()
    infra = (a.g5_root / "teams" / "07-infrastructure").resolve()
    for p in (harness, infra):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import torch  # noqa: PLC0415
    from ckpt.ckpt import export_safetensors  # noqa: PLC0415  Team 7, unmodified
    from safetensors.torch import load_file  # noqa: PLC0415
    from train_week2 import model_hash, scored_ntp_loss  # noqa: PLC0415  Team 5, unmodified
    from week2.artifacts import Artifacts  # noqa: PLC0415
    from week2.data import DocumentWindows  # noqa: PLC0415
    from week2.model import LanguageModel  # noqa: PLC0415

    store = str(a.store) if a.store else t7["store"]
    cfg, want = manifest["config"], manifest["artifacts"]
    artifacts = Artifacts(a.tokenizer, a.byte_table, expected_tokenizer_sha=want["tokenizer_sha256"],
                          expected_vocab=want["vocab_size"])
    if artifacts.identity() != want:
        raise ValueError("tokenizer or byte table differs from the ones the run used")
    dev = torch.device(a.device)
    val = DocumentWindows(a.heldout_data, artifacts, cfg["model"]["block_size"],
                          require_ids=not manifest.get("smoke"), sources_path=a.heldout_sources)
    probe_x, probe_y, _ = val.batch([0], dev)

    def factory():
        return LanguageModel(cfg["model"], artifacts.bytes, artifacts.lengths).to(dev)

    @torch.no_grad()
    def probe(m):  # train_week2.py's Team 7 probe: held-out window 0, eval mode, its amp() rule
        amp = (torch.autocast(device_type="cuda", dtype=torch.bfloat16)
               if dev.type == "cuda" and cfg["run"]["dtype"] == "bf16" else nullcontext())
        m.eval()
        with amp:
            return float(scored_ntp_loss(m, probe_x, probe_y))

    os.environ.setdefault("V5_EVENTS_DIR", tempfile.mkdtemp(prefix="g10_store_events_"))
    a.out.mkdir(parents=True, exist_ok=False)
    tmp = a.out / ".export.safetensors"
    info = export_safetensors(f"{store.rstrip('/')}/{t7['run_id']}", factory, probe, str(tmp), step=step)
    model = factory()
    model.load_state_dict(load_file(str(tmp)), strict=True)
    tmp.unlink()
    got = model_hash(model)
    if got != summary.get("final_model_sha256"):
        shutil.rmtree(a.out)
        raise ValueError(f"store step {step} weights hash {got} != summary.json final_model_sha256 "
                         f"{summary.get('final_model_sha256')}")
    for name in DELIVERED:
        if (rf / name).is_file():
            shutil.copy2(rf / name, a.out / name)
    torch.save({"model": model.state_dict(), "step": step, "identity_sha256": manifest["identity_sha256"],
                "run_id": t7["run_id"]}, a.out / "checkpoint.pt")
    record = {
        "made_by": "teams/10-post-training/capstone/run_folder_from_store.py",
        "delivered_folder": str(rf), "store": store, "run_id": t7["run_id"], "step": step,
        "team7_checkpoint_path": path, "export": {k: info[k] for k in ("step", "probe_bits")},
        "model_hash_g5": got, "matches_summary_final_model_sha256": True,
        "delivered_sha256": {n: sha256_file(rf / n) for n in DELIVERED if (rf / n).is_file()},
        "checkpoint_sha256": sha256_file(a.out / "checkpoint.pt"), "device": a.device, "torch": torch.__version__,
    }
    (a.out / "G10_FROM_STORE.json").write_text(json.dumps(record, indent=2), encoding="utf8")
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--g5-root", type=Path, required=True)
    ap.add_argument("--run-folder", type=Path, required=True, help="the delivered out/<run-id> folder")
    ap.add_argument("--store", help="Team 7 store root, if not at the path the manifest recorded on the job machine")
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--byte-table", type=Path, required=True)
    ap.add_argument("--heldout-data", type=Path, required=True, help="held-out jsonl the run used (probe window 0)")
    ap.add_argument("--heldout-sources", type=Path)
    ap.add_argument("--device", default="cpu", choices=("cpu", "cuda"))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    rec = build(a)
    print(json.dumps({k: rec[k] for k in ("run_id", "step", "model_hash_g5", "export", "checkpoint_sha256")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
