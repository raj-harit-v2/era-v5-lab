"""Rebuild the run folder G10's jobs read from a Team 5 delivery whose weights are only in the Team 7 checkpoint store.

Dry run 2's job request (`teams/05-architecture/jobs/2026-11-22-dryrun2.md`, "Outputs") delivers
`manifest.json, summary.json, metrics.jsonl, losses.txt, total_losses.txt` and says "The checkpoint stays on the job
machine"; the weights are committed to the Team 7 store (`--checkpoint-store`, `--run-id`). Every G10 entry point
(`team5_adapter.py` run_folder mode, `make_probe_file.py`, `day_one_probe.py`, `sft_job_v1.py`, `rl_job_v1.py`,
`dryrun2_dt_compare.py`) reads `checkpoint.pt` beside the manifest, so they all refuse that delivery as it is.

This script reads the committed step with Team 7's own `ckpt.ckpt.export_safetensors` (file sha256 and strict keys
are checked there), loads it strictly into Team 5's `LanguageModel`, and refuses unless Team 5's `model_hash` of the
loaded weights equals `summary.json` `final_model_sha256`. Only then it writes `<out>/checkpoint.pt` = {"model", "step",
"identity_sha256", "run_id"} (the keys G10 reads; no optimizer or RNG state, so it cannot resume Team 5's run) plus copies
of the delivered files. No check downstream changes: the adapter still pins the Team 5 sources, the manifest hash, and
the model hash.

`G10_FROM_STORE.json` also records:
- `manifest_sha256`: sha256 of the step's `MANIFEST.json` bytes, which Team 9's reader reports as `model_revision` for a
  lab checkpoint (teams/09-evaluation/results/eval_mini_v1_schema.md). It is the manifest the export read: its
  `state_digest` must equal the one Team 7 wrote into the exported file.
- `probe`: `probe_bits` "compared" or "skipped". Team 7 compares the probe-loss bits only when the store saved bits for
  the device class the export runs on (`ckpt.device_class`: "cpu", or "cuda:<GPU name>"). Dry run 2 trains on a GPU
  under bf16 autocast and this script defaults to `--device cpu` (fp32), so there the bits are skipped and the record
  says why; the binding check is then the model hash. Pass `--device cuda` on the same GPU model to have them compared.

Any failure after `<out>` is created removes `<out>`, so a rerun starts clean; an `<out>` that already exists is refused
and left as it is.

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

# Team 5's Team 7 probe (train_week2.py, the `probe` closure passed to Checkpointer) as this script mirrors it. Team 7's
# export recomputes the probe with OUR closure and raises RestoreCheckError when the bits differ from the ones the run
# saved for the same device class, so a closure that drifts from Team 5's breaks the first command of the TSAI job.
# Known closures (sha256 of the dedented text, see team5_probe_closure): before #717 (scored_ntp_loss on held-out window
# 0) and #717 (61f0a3ae: `checkpoint_probe` when model.head_mode is kas_v2). test_run_folder_from_store pins the G5
# root's closure to this set, so an upstream edit fails a test instead of the job.
TEAM5_PROBE_CLOSURES = {
    "PRE717": "scored_ntp_loss on held-out window 0 under amp()",
    "KAS717": "kas_v2: week2.kas_v2.checkpoint_probe(model); else scored_ntp_loss on held-out window 0; under amp()",
}
TEAM5_PROBE_CLOSURE_SHA256 = {
    "PRE717": "db809250dc549b7be8533ee5a448fbb28428cfec9b2186878547620f3b8f1718",  # train_week2.py at 00e10c6b (d2d7a21e)
    "KAS717": "c37ac45b199b026cfa5efaa5b48efc1e5bbeb5e064fbc57e4bc55858a3128ddb",  # train_week2.py at 61f0a3ae / eef1834d
}


def team5_probe_closure(train_week2_path: Path) -> str:
    """The text of train_week2.py's `def probe(probe_model):` closure (up to `checkpointer = Checkpointer(`), dedented."""
    lines = Path(train_week2_path).read_text(encoding="utf8").splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "def probe(probe_model):"), None)
    if start is None:
        raise ValueError(f"{train_week2_path}: no `def probe(probe_model):` closure (Team 5 changed its Team 7 probe)")
    end = next((i for i in range(start, len(lines)) if lines[i].strip().startswith("checkpointer = Checkpointer(")), None)
    if end is None:
        raise ValueError(f"{train_week2_path}: the probe closure is not followed by `checkpointer = Checkpointer(`")
    block = [ln for ln in lines[start:end] if ln.strip()]
    indent = min(len(ln) - len(ln.lstrip()) for ln in block)
    return "\n".join(ln[indent:] for ln in block) + "\n"


def team5_probe_kind(train_week2_path: Path) -> str:
    """'PRE717' or 'KAS717' when Team 5's closure is one this script mirrors, else 'UNKNOWN:<why>'. Recorded, never
    refused: Team 7's export is the binding probe check and raises on its own when the bits differ."""
    try:
        sha = hashlib.sha256(team5_probe_closure(train_week2_path).encode()).hexdigest()
    except (OSError, ValueError) as e:
        return f"UNKNOWN:{e}"
    return next((k for k, v in TEAM5_PROBE_CLOSURE_SHA256.items() if v == sha), f"UNKNOWN:{sha}")


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


def probe_record(saved: dict, here: str, run_dtype: str) -> dict:
    """Whether Team 7's export compared the probe-loss bits (it does only when the store saved bits for this device class)
    and, if not, why. `saved`: the manifest's probe_loss {device_class: bits}; `here`: device class of the export."""
    def precision(dc: str) -> str:  # the probe's amp rule (train_week2.py, and probe() below)
        return "bf16 autocast" if dc.startswith("cuda") and run_dtype == "bf16" else "fp32"
    rec = {"device_class": here, "precision": precision(here), "saved_device_classes": sorted(saved)}
    if here in saved:
        return {"probe_bits": "compared", **rec, "saved_bits": saved[here]}
    if not saved:
        why = "the store saved no probe-loss bits for this step"
    else:
        others = ", ".join(f"{d} ({precision(d)})" for d in sorted(saved))
        diff = "device class" + (" and precision" if all(precision(d) != precision(here) for d in saved) else "")
        why = (f"{diff} differ: the store saved bits on {others}, this export ran on {here} ({precision(here)}); "
               f"Team 7 compares bits only on the device class that saved them")
    return {"probe_bits": "skipped", **rec, "reason": why}


def build(a) -> dict:
    rf = a.run_folder
    manifest, summary, t7, step, path = delivery_facts(rf)
    harness = (a.g5_root / "teams" / "05-architecture" / "harness").resolve()
    infra = (a.g5_root / "teams" / "07-infrastructure").resolve()
    for p in (harness, infra):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import torch  # noqa: PLC0415
    from ckpt.ckpt import device_class, export_safetensors  # noqa: PLC0415  Team 7, unmodified
    from ckpt.store import join, open_store  # noqa: PLC0415
    from safetensors import safe_open  # noqa: PLC0415
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

    probe_kind = team5_probe_kind(harness / "train_week2.py")
    kas = cfg["model"].get("head_mode") == "kas_v2"

    @torch.no_grad()
    def probe(m):  # train_week2.py's Team 7 probe, branch for branch (TEAM5_PROBE_CLOSURES): eval mode, its amp() rule
        amp = (torch.autocast(device_type="cuda", dtype=torch.bfloat16)
               if dev.type == "cuda" and cfg["run"]["dtype"] == "bf16" else nullcontext())
        m.eval()
        with amp:
            if kas:  # #717: a kas_v2 run saves the bits of Team 5's seeded checkpoint_probe, not the held-out window
                from week2.kas_v2 import checkpoint_probe  # noqa: PLC0415  Team 5, unmodified
                return checkpoint_probe(m)
            return float(scored_ntp_loss(m, probe_x, probe_y))

    os.environ.setdefault("V5_EVENTS_DIR", tempfile.mkdtemp(prefix="g10_store_events_"))
    a.out.mkdir(parents=True, exist_ok=False)  # outside the try: an existing folder is refused and never removed
    try:
        tmp = a.out / ".export.safetensors"
        info = export_safetensors(f"{store.rstrip('/')}/{t7['run_id']}", factory, probe, str(tmp), step=step)
        with safe_open(str(tmp), framework="pt") as f_:
            exported_digest = (f_.metadata() or {}).get("state_digest")
        man_tmp = a.out / ".MANIFEST.json"
        man_sha, _ = open_store(store).get_file(join(t7["run_id"], path, "MANIFEST.json"), str(man_tmp))
        step_man = json.loads(man_tmp.read_text(encoding="utf8"))
        man_tmp.unlink()
        if step_man.get("state_digest") != exported_digest or step_man.get("step") != info["step"]:
            raise ValueError(f"{path}/MANIFEST.json (step {step_man.get('step')}, state_digest "
                             f"{step_man.get('state_digest')}) is not the manifest the export read (step {info['step']}, "
                             f"state_digest {exported_digest})")
        model = factory()
        model.load_state_dict(load_file(str(tmp)), strict=True)
        tmp.unlink()
        got = model_hash(model)
        if got != summary.get("final_model_sha256"):
            raise ValueError(f"store step {step} weights hash {got} != summary.json final_model_sha256 "
                             f"{summary.get('final_model_sha256')}")
        probe_rec = probe_record(step_man.get("probe_loss") or {}, device_class(model), cfg["run"].get("dtype"))
        probe_rec.update({"probe_fn": "kas_v2.checkpoint_probe" if kas else "scored_ntp_loss(heldout window 0)",
                          "team5_probe_closure": probe_kind})
        for name in DELIVERED:
            if (rf / name).is_file():
                shutil.copy2(rf / name, a.out / name)
        torch.save({"model": model.state_dict(), "step": step, "identity_sha256": manifest["identity_sha256"],
                    "run_id": t7["run_id"]}, a.out / "checkpoint.pt")
        record = {
            "made_by": "teams/10-post-training/capstone/run_folder_from_store.py",
            "delivered_folder": str(rf), "store": store, "run_id": t7["run_id"], "step": step,
            "team7_checkpoint_path": path, "export": {k: info[k] for k in ("step", "probe_bits")},
            "manifest_sha256": man_sha, "state_digest": exported_digest, "probe": probe_rec,
            "model_hash_g5": got, "matches_summary_final_model_sha256": True,
            "delivered_sha256": {n: sha256_file(rf / n) for n in DELIVERED if (rf / n).is_file()},
            "checkpoint_sha256": sha256_file(a.out / "checkpoint.pt"), "device": a.device, "torch": torch.__version__,
        }
        (a.out / "G10_FROM_STORE.json").write_text(json.dumps(record, indent=2), encoding="utf8")
    except BaseException:
        shutil.rmtree(a.out, ignore_errors=True)
        raise
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
    print(json.dumps({k: rec[k] for k in ("run_id", "step", "model_hash_g5", "manifest_sha256", "export", "checkpoint_sha256")}
                     | {"probe_bits": rec["probe"]["probe_bits"], **({"probe_reason": rec["probe"]["reason"]}
                                                                      if "reason" in rec["probe"] else {})}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
