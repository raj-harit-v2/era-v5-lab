"""Restore test: a run restored from a checkpoint continues exactly as if it had never stopped.

In simple words:
- Run A trains the Team 05 tiny MoE from step 0 to 200 with no stop, and saves a checkpoint at step 100.
- Run B trains from step 0, saves at step 100, and stops at step 150 (its processes exit). New processes then
  restore Run B's step-100 checkpoint with our Checkpointer and train on to step 200.
- For every step 101..200 the training losses (next-token and t+2) must be bit-equal and the batch data ID
  (global batch position + sha256 of the batch tokens) must be the same. Then the data stream resumed at the
  right place and nothing was lost in the save and restore.

Exit 0 and one PASS line when everything matches; exit 1 and the first step that differs otherwise;
exit 78 if a run crashed. Writes only to --out (default out/ next to this script, git-ignored).

    python restore_test.py                       # 1 CPU process
    python restore_test.py --nproc 2             # 2 CPU processes (gloo, DDP)
    python restore_test.py --nproc 2 --device cuda
"""
import argparse
import hashlib
import json
import os
import shutil
import socket
import sys
from pathlib import Path

import torch
import torch.distributed as dist
import torch.multiprocessing as mp
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[1]                                   # teams/07-infrastructure
HARNESS = TEAM.parent / "05-architecture" / "harness"    # Team 05's tiny MoE (imported, never edited)
sys.path[:0] = [str(TEAM), str(TEAM / "support" / "simulation"), str(HARNESS)]
from check_config import errors_for, load_settings, merge  # noqa: E402
from ckpt.ckpt import EXIT_FATAL, Checkpointer, float_bits  # noqa: E402
from train import TinyMoE, as_map, stream_for  # noqa: E402
from trainer.tiny import SyntheticLoader  # noqa: E402

CONFIGS = TEAM.parent / "05-architecture" / "configs"
MIN_TORCH = "2.14.1"
FIELDS = ("loss_ntp_bits", "loss_mtp_bits", "batch_id")


class StreamLoader(SyntheticLoader):
    """Team 05's seeded stream behind the loader contract (ckpt/loader_contract.py).

    Global batch p is rows p*B..(p+1)*B of stream_for(); each rank takes rows rank::world. Position, skip list,
    state_dict and next_batch_id come from SyntheticLoader unchanged."""

    def __init__(self, cfg: dict, seed: int, rank: int, world: int):
        super().__init__(seed, int(cfg["tiny.batch"]), rank, world)
        self.stream = stream_for(cfg, seed)
        self.manifest = hashlib.sha256(self.stream.numpy().tobytes()).hexdigest()

    def _global(self, p: int) -> torch.Tensor:
        return self.stream[p * self.global_batch:(p + 1) * self.global_batch]


def load_cfg(config: Path, tiny: Path, steps: int) -> dict:
    settings = merge(load_settings(config), tiny)
    found = errors_for(settings)
    if found:
        raise SystemExit("\n".join(found))
    cfg = as_map(settings)
    cfg["tiny.steps"] = steps   # the stream must hold `steps` batches; Team 05's file says 40
    return cfg


def losses(model, tokens):
    """Team 05's loss, exactly as in harness/train.py run()."""
    logits, mtp_logits = model(tokens)
    ntp = F.cross_entropy(logits[:, :-1].reshape(-1, logits.shape[-1]), tokens[:, 1:].reshape(-1))
    mtp = F.cross_entropy(mtp_logits[:, :-2].reshape(-1, mtp_logits.shape[-1]), tokens[:, 2:].reshape(-1))
    return ntp, mtp


def global_mean(x: torch.Tensor, world: int) -> float:
    if world == 1:
        return float(x.detach())
    t = x.detach().clone()
    dist.all_reduce(t)
    return float(t / world)


def segment(rank: int, world: int, a: argparse.Namespace, run_id: str, label: str, restore: bool, stop_at: int):
    """One launch of a run: fresh processes, fresh model. Rank 0 writes <out>/<label>.jsonl."""
    os.environ.update(RANK=str(rank), WORLD_SIZE=str(world), LOCAL_RANK=str(rank), RUN_ID=run_id)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    if a.device == "cuda":
        dev = torch.device("cuda", rank)
        torch.cuda.set_device(dev)
    else:
        dev = torch.device("cpu")
    if world > 1:
        dist.init_process_group("nccl" if dev.type == "cuda" else "gloo", rank=rank, world_size=world)

    cfg = load_cfg(a.config, a.tiny, a.steps)
    seed = int(cfg["run.seed"])
    torch.manual_seed(seed)
    model = TinyMoE(cfg).to(dev)
    net = model
    if world > 1:
        # No buffer sync at all: the embedding's int16 length buffer cannot go through gloo ("Invalid scalar
        # type"), and the buffers are built the same way on every rank and never change. init_sync=False skips
        # DDP's start-up broadcast of weights AND buffers, so we broadcast the weights ourselves.
        for t in model.parameters():
            dist.broadcast(t.data, src=0)
        net = torch.nn.parallel.DistributedDataParallel(
            model, device_ids=[dev.index] if dev.type == "cuda" else None,
            init_sync=False, forward_sync_buffers=False)
    optim = torch.optim.AdamW(model.parameters(), lr=float(cfg["optim.lr"]))
    loader = StreamLoader(cfg, seed, rank, world)
    clip = float(cfg["run.grad_clip"])
    probe_batch = stream_for(cfg, seed + 1)[:int(cfg["tiny.batch"])]

    def probe(m) -> float:
        m = getattr(m, "module", m)
        m.eval()
        with torch.no_grad():
            ntp, _ = losses(m, probe_batch.to(dev))
        m.train()
        return ntp.item()

    ck = Checkpointer(run_id, str(a.out / "ckpt_local" / label), str(a.out / "ckpt_store"),
                      config_path=str(a.tiny), seed=seed)
    step = 0
    if restore:
        info = ck.restore(net, optim, loader, probe, from_step=a.save_at)
        if info["step"] != a.save_at:
            raise RuntimeError(f"restored step {info['step']}, wanted {a.save_at}")
        step = a.save_at

    rows = []
    while step < stop_at:
        batch_id = loader.next_batch_id()
        tokens = loader.next().to(dev)
        optim.zero_grad(set_to_none=True)
        ntp, mtp = losses(net, tokens)
        (ntp + mtp).backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
        optim.step()
        step += 1
        n, m = global_mean(ntp, world), global_mean(mtp, world)
        rows.append({"step": step, "loss_ntp": n, "loss_mtp": m, "loss_ntp_bits": float_bits(n),
                     "loss_mtp_bits": float_bits(m), "batch_id": batch_id})
        if step == a.save_at and not restore:
            if not (ck.save(step, net, optim, loader, probe, reason="restore_test") and ck.wait()):
                raise RuntimeError(f"checkpoint at step {step} was not committed")

    if rank == 0:
        with open(a.out / f"{label}.jsonl", "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
    if world > 1:
        dist.barrier()
        dist.destroy_process_group()


def launch(a, run_id: str, label: str, restore: bool, stop_at: int) -> list:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        os.environ.update(MASTER_ADDR="127.0.0.1", MASTER_PORT=str(s.getsockname()[1]))
    mp.spawn(segment, args=(a.nproc, a, run_id, label, restore, stop_at), nprocs=a.nproc)
    with open(a.out / f"{label}.jsonl") as f:
        return [json.loads(line) for line in f]


def first_diff(run_a: list, run_b: list, first: int, last: int):
    by_a, by_b = {r["step"]: r for r in run_a}, {r["step"]: r for r in run_b}
    for step in range(first, last + 1):
        if step not in by_a or step not in by_b:
            return {"step": step, "field": "missing", "a": step in by_a, "b": step in by_b}
        for field in FIELDS:
            if by_a[step][field] != by_b[step][field]:
                return {"step": step, "field": field, "a": by_a[step][field], "b": by_b[step][field]}
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--nproc", type=int, default=1, help="devices: CPU processes, or GPUs with --device cuda")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--save-at", type=int, default=100)
    ap.add_argument("--stop-at", type=int, default=150, help="Run B's first launch stops here")
    ap.add_argument("--out", type=Path, default=HERE / "out")
    ap.add_argument("--config", type=Path, default=CONFIGS / "config_v0.yaml")
    ap.add_argument("--tiny", type=Path, default=CONFIGS / "small" / "tiny_moe.yaml")
    a = ap.parse_args(argv)
    if torch.__version__ < MIN_TORCH:
        ap.error(f"needs torch {MIN_TORCH} or newer (DDP init_sync / forward_sync_buffers), found {torch.__version__}")
    if not 0 < a.save_at < a.stop_at <= a.steps:
        ap.error("need 0 < --save-at < --stop-at <= --steps")
    if a.device == "cuda" and torch.cuda.device_count() < a.nproc:
        ap.error(f"--nproc {a.nproc} needs {a.nproc} GPUs, found {torch.cuda.device_count()}")
    a.out = a.out.resolve()
    a.config, a.tiny = a.config.resolve(), a.tiny.resolve()

    # A fresh store every time: an old commits.jsonl or latest.json would be restored from instead.
    for name in ("ckpt_local", "ckpt_store", "events"):
        shutil.rmtree(a.out / name, ignore_errors=True)
    a.out.mkdir(parents=True, exist_ok=True)
    os.environ["V5_EVENTS_DIR"] = str(a.out / "events")
    # cuBLAS needs a fixed workspace to give the same bits every run (PyTorch reproducibility notes).
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

    try:
        run_a = launch(a, "restore-a", "run_a", False, a.steps)
        run_b1 = launch(a, "restore-b", "run_b_before_stop", False, a.stop_at)
        run_b2 = launch(a, "restore-b", "run_b_after_restore", True, a.steps)
    except Exception as e:  # noqa: BLE001 - a crash in any run is a failed test, not a mismatch
        print(f"FAIL restore_test: a run crashed: {type(e).__name__}: {e}", file=sys.stderr)
        return EXIT_FATAL

    first, last = a.save_at + 1, a.steps
    diff = first_diff(run_a, run_b2, first, last)
    result = {"pass": diff is None, "first_diff": diff, "nproc": a.nproc, "device": a.device, "steps": a.steps,
              "save_at": a.save_at, "stop_at": a.stop_at, "compared_steps": [first, last], "fields": FIELDS,
              "torch": torch.__version__, "run_a": run_a,
              "run_b": [r for r in run_b1 if r["step"] <= a.save_at] + run_b2}
    (a.out / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    where = f"nproc={a.nproc} {a.device}: steps {first}-{last}"
    if diff is None:
        print(f"PASS restore_test {where}: loss_ntp and loss_mtp bit-equal, data ids equal")
        return 0
    print(f"FAIL restore_test {where}: first difference at step {diff['step']} in {diff['field']}: "
          f"a={diff['a']} b={diff['b']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
