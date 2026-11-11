"""V5 checkpoint library (ADR 0001).

In simple words:
- A checkpoint is a saved copy of everything training needs to continue: weights, optimizer, random
  number generators and the data position. If a machine dies, we continue from the last copy, so we only
  lose the work done since that copy, not the money already spent.
- We save in two steps. First a quick copy to the node's own disk (training waits for this part, the
  "stall"). Then, in the background, an upload to S3 while training continues.
- A checkpoint only counts once it is "committed": every file is uploaded, its checksum is checked,
  and the MANIFEST (the list of files and checksums) is written last. The `latest.json` pointer is
  moved only after that. So a half-written checkpoint can never be picked by mistake.
- On restore we check the checkpoint before trusting it: checksums, exact key names and shapes, a
  digest of every tensor, and the loss of one fixed probe batch, compared bit for bit.
- Only one attempt of a run may commit (fencing). A job that Slurm thinks is dead can still be running
  (a node cut off from the network, then back). Each attempt claims a new "epoch" in `latest.json` before
  it restores, and every later write of `latest.json` is conditional on the version that attempt wrote
  (S3 If-Match). So an old attempt's commit is refused (FencedError) and it stops; it can never move the
  pointer back. Each attempt also writes into its own step folders (`step_<N>-e<epoch>`), so two attempts
  never mix files.

Storage layout (the S3 bucket is a directory in the Docker test):
    <remote_root>/<run_id>/latest.json             pointer to the newest committed checkpoint + the epoch
    <remote_root>/<run_id>/commits.jsonl           every commit, in order (restore never lists dirs)
    <remote_root>/<run_id>/pins.json               steps a person has pinned (never deleted)
    <remote_root>/<run_id>/<branch>/step_<N>-e<E>/ DCP files, extra_rank<r>.json, sums_rank<r>.json, MANIFEST.json
"""
import argparse
import base64
import hashlib
import json
import os
import pickle
import platform
import random
import shutil
import struct
import subprocess
import sys
import threading
import time
import warnings
from functools import lru_cache

import numpy as np
import torch
import torch.distributed as dist
import torch.distributed.checkpoint as dcp
from torch.distributed.checkpoint.state_dict import get_state_dict, set_state_dict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ckpt.store import Conflict, open_store, wait_for  # noqa: E402
from common.events import Timer, emit  # noqa: E402

# DCP warns about single-process use and storage internals; they are expected here.
warnings.filterwarnings("ignore", category=UserWarning, module=r"torch\.distributed\.checkpoint")

# Exit codes shared by the trainer, the job script and Slurm (ADR 0001 §6).
EXIT_DONE = 0     # finished
EXIT_RETRY = 75   # state is safe (saved, or nothing to save): requeue, maybe on another node
EXIT_FATAL = 78   # retrying will not help (NaN, failed checks): hold the job and page a person

MANIFEST = "MANIFEST.json"
SCHEMA = "v5-ckpt/2"         # 2: logical fingerprints (reshard-safe), async save, loader_global


class CheckpointError(Exception):
    pass


class IntegrityError(CheckpointError):
    """A file does not match its checksum. Try the previous checkpoint."""


class RestoreCheckError(CheckpointError):
    """The restored state is not the saved state. Try the previous checkpoint."""


class StrictLoadError(CheckpointError):
    """Key names or shapes differ from the model. Every checkpoint would fail the same way: stop."""


class EnvMismatchError(CheckpointError):
    """Software or config differs from the saved run. Stop unless --allow-env-change is given."""


class NonFiniteError(CheckpointError):
    """NaN or Inf in the state. Never save it."""


class ReshardError(CheckpointError):
    """The loader saved per-rank positions, so this checkpoint cannot resume at another world size."""


class UploadTimeout(CheckpointError):
    """A rank did not finish its upload in time. This save is not committed; training continues."""


class FrozenChangedError(CheckpointError):
    """A frozen tensor (e.g. the KE2 Kronecker tables) changed since the last checkpoint: training touched a part
    that must never change. Never saved; hold the job (millermuttu's rule, team 07: check at save, not only at restore)."""


class DataManifestError(CheckpointError):
    """The data loader's shard list (manifest sha) differs from the one the checkpoint was trained on. Resuming
    would continue on other data without anyone noticing: hold the job."""


class FencedError(CheckpointError):
    """A newer attempt of this run has claimed `latest.json`. This attempt must not commit: stop."""


# ----------------------------------------------------------------------------- small helpers

def rank() -> int:
    return dist.get_rank() if dist.is_initialized() else 0


def world() -> int:
    return dist.get_world_size() if dist.is_initialized() else 1


def local_rank() -> int:
    return int(os.environ.get("LOCAL_RANK", os.environ.get("SLURM_LOCALID", "0")))


def barrier():
    if dist.is_initialized():
        dist.barrier()


def comm_device() -> torch.device:
    """NCCL only reduces GPU tensors; gloo reduces CPU tensors."""
    if dist.is_initialized() and dist.get_backend() == "nccl":
        return torch.device("cuda", torch.cuda.current_device())
    return torch.device("cpu")


def all_true(flag: bool) -> bool:
    if not dist.is_initialized():
        return flag
    t = torch.tensor([0 if flag else 1], dtype=torch.int32, device=comm_device())
    dist.all_reduce(t, op=dist.ReduceOp.MAX)
    return t.item() == 0


def broadcast_obj(obj):
    if not dist.is_initialized():
        return obj
    box = [obj]
    dist.broadcast_object_list(box, src=0)
    return box[0]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_with_sha(src: str, dst: str) -> tuple:
    """Copy src to dst through a temp name, so a reader never sees half a file. Returns (sha256, bytes)."""
    h = hashlib.sha256()
    n = 0
    tmp = dst + ".part"
    with open(src, "rb") as fi, open(tmp, "wb") as fo:
        for chunk in iter(lambda: fi.read(1 << 20), b""):
            h.update(chunk)
            fo.write(chunk)
            n += len(chunk)
        fo.flush()
        os.fsync(fo.fileno())
    os.replace(tmp, dst)
    return h.hexdigest(), n


def write_json_atomic(path: str, obj) -> None:
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def float_bits(x: float) -> str:
    """The exact bits of a float, so two values compare exactly, not after rounding."""
    return struct.pack(">d", float(x)).hex()


def flatten(sd, prefix: str = "") -> dict:
    out = {}
    if isinstance(sd, dict):
        for k, v in sd.items():
            out.update(flatten(v, f"{prefix}{k}."))
    elif isinstance(sd, (list, tuple)):
        for i, v in enumerate(sd):
            out.update(flatten(v, f"{prefix}{i}."))
    else:
        out[prefix[:-1]] = sd
    return out


def tensor_items(sd) -> list:
    return sorted((k, v) for k, v in flatten(sd).items() if isinstance(v, torch.Tensor))


def own_cpu_copies(obj):
    """The same state with every plain CPU tensor cloned (anything else, e.g. a GPU tensor, is left as is).

    Why: dcp.async_save "stages" the state by moving it to host memory, but a tensor that is already on the CPU
    is staged without a copy (torch 2.5: `_offload_state_dict_to_cpu` returns the same storage). The background
    writer would then read weights the optimizer is already changing, and the files would hold a later state than
    the digest we recorded. Found by the kill_during_save drill (run 13): the committed checkpoint failed its
    restore proofs. GPU tensors are copied by DCP itself."""
    if isinstance(obj, dict):
        return {k: own_cpu_copies(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(own_cpu_copies(v) for v in obj)
    if isinstance(obj, torch.Tensor) and not hasattr(obj, "placements") and obj.device.type == "cpu":
        return obj.detach().clone()
    return obj


def local_part(t: torch.Tensor) -> torch.Tensor:
    """This rank's piece of a tensor: the local shard of an FSDP2/TP DTensor, or the tensor itself."""
    return t.to_local() if hasattr(t, "to_local") else t


def shard_place(t: torch.Tensor):
    """(local piece, its offset in the full tensor per dim, whether this rank adds it to the fingerprint).

    A plain tensor is a full copy on every rank (DDP), so only rank 0 adds it. A DTensor shard is added by
    every rank that holds a different piece; replicated copies are added once (mesh coordinate 0)."""
    if not hasattr(t, "placements"):
        return t, (0,) * t.dim(), rank() == 0
    try:
        from torch.distributed.tensor._utils import compute_local_shape_and_global_offset
    except ImportError:  # torch < 2.5
        from torch.distributed._tensor._utils import compute_local_shape_and_global_offset
    loc = t.to_local()
    shape, off = compute_local_shape_and_global_offset(t.shape, t.device_mesh, t.placements)
    if tuple(loc.shape) != tuple(shape):
        raise CheckpointError(f"shard of shape {tuple(loc.shape)} does not match its placement {tuple(shape)}")
    coord = t.device_mesh.get_coordinate() or ()
    dup = any(p.is_replicate() and coord[i] != 0 for i, p in enumerate(t.placements))
    return loc, tuple(off), not dup


FP_M = 2 ** 31 - 1          # a prime; every sum below stays far inside int64, so the arithmetic is exact
FP_CHUNK = 1 << 22          # elements per pass: bounds the extra GPU memory to about 200 MB
_WORD = {1: torch.uint8, 2: torch.int16, 4: torch.int32, 8: torch.int32}


def _fingerprint_piece(loc: torch.Tensor, off: tuple, shape: tuple) -> torch.Tensor:
    """Two sums over the raw bits of this piece, each word weighted by its position in the FULL tensor."""
    t = loc.detach().contiguous()
    if t.dtype == torch.bool:
        t = t.to(torch.uint8)
    per = max(1, t.element_size() // 4)                     # 64-bit values are two 32-bit words
    words = t.reshape(*t.shape, 1).view(_WORD[t.element_size()]).reshape(*t.shape, per) if t.dim() else \
        t.reshape(1, 1).view(_WORD[t.element_size()]).reshape(per)
    mask = (1 << (8 * min(t.element_size(), 4))) - 1
    strides = [1] * len(shape)
    for d in range(len(shape) - 2, -1, -1):
        strides[d] = strides[d + 1] * shape[d + 1]
    acc = torch.zeros(2, dtype=torch.int64, device=t.device)
    rows = t.shape[0] if t.dim() else 1
    per_row = max(1, words.numel() // max(rows, 1))
    step = max(1, FP_CHUNK // per_row)
    for r0 in range(0, rows, step):
        w = (words[r0:r0 + step] if t.dim() else words).to(torch.int64) & mask
        idx = torch.zeros(w.shape[:-1], dtype=torch.int64, device=t.device)
        for d in range(t.dim()):                            # global element index, from the shard offset
            ar = torch.arange(w.shape[d], dtype=torch.int64, device=t.device) + off[d] + (r0 if d == 0 else 0)
            idx = idx + (ar * strides[d]).reshape([-1 if i == d else 1 for i in range(t.dim())])
        gi = idx.unsqueeze(-1) * per + torch.arange(per, dtype=torch.int64, device=t.device)
        w1 = gi % FP_M + 1
        w2 = (gi * 48271) % FP_M + 1
        acc[0] += ((w % FP_M) * w1 % FP_M).sum() % FP_M
        acc[1] += ((w % FP_M) * w2 % FP_M).sum() % FP_M
    return acc % FP_M


def fingerprints(sd, keys=None) -> dict:
    """{key: "h1-h2"} for the LOGICAL tensors, the same at any world size or sharding (ADR 0001 §8).

    In simple words: every rank adds up its own piece, weighting each number by its place in the full tensor,
    then one all-reduce adds the pieces. Moving pieces between ranks (resharding) cannot change the sum, but
    any wrong or swapped number does. Integer sums on the GPU: milliseconds, not the minutes of a sha256."""
    items = [(k, t) for k, t in tensor_items(sd) if keys is None or k in keys]
    if not items:
        return {}
    dev = comm_device()
    out = torch.zeros(len(items), 2, dtype=torch.int64, device=dev)
    for i, (_, t) in enumerate(items):
        loc, off, add = shard_place(t)
        if add and loc.numel():
            out[i] = _fingerprint_piece(loc, off, tuple(t.shape)).to(dev)
    if dist.is_initialized():
        dist.all_reduce(out, op=dist.ReduceOp.SUM)
    out = (out % FP_M).tolist()
    return {k: f"{a:08x}-{b:08x}" for (k, _), (a, b) in zip(items, out)}


def state_digest(sd) -> str:
    """One hash over every tensor's name, dtype, shape and fingerprint. Equal digest = identical state."""
    h = hashlib.sha256()
    fp = fingerprints(sd)
    for k, t in tensor_items(sd):
        h.update(f"{k}|{t.dtype}|{tuple(t.shape)}|{fp[k]};".encode())
    return h.hexdigest()


def key_spec(sd) -> dict:
    return {k: [list(t.shape), str(t.dtype)] for k, t in tensor_items(sd)}


def all_finite(sd) -> bool:
    return all(torch.isfinite(local_part(t)).all().item() for _, t in tensor_items(sd) if t.is_floating_point())


def device_class(model=None) -> str:
    """Where the probe loss is computed: CPU and each GPU model give different (but repeatable) bits."""
    dev = next(model.parameters()).device if model is not None else torch.device("cpu")
    if dev.type == "cuda":
        return f"cuda:{torch.cuda.get_device_name(dev)}"
    return dev.type


CKPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _git(*args):
    """stdout of a git command run in this file's checkout (not the cwd), or None without git metadata."""
    try:
        r = subprocess.run(["git", "-C", CKPT_DIR, *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


@lru_cache(maxsize=None)
def provenance(env_sha: str) -> dict:
    """Which source commit this process runs (issue #298). Recorded in the manifest, never must-match.

    GIT_SHA wins if set (an exported tree, a job package); else the checkout's HEAD; else "none".
    Cached per GIT_SHA value, so the warning events below fire once per process, not on every save.
    """
    head = _git("rev-parse", "HEAD")
    dirty = None if head is None else bool(_git("status", "--porcelain", "--untracked-files=no"))
    out = {"git_sha": env_sha or head or "none", "git_sha_source": "env" if env_sha else "git" if head else "none",
           "git_dirty": dirty}
    if env_sha and head and not (head.startswith(env_sha) or env_sha.startswith(head)):
        out["git_sha_checkout"] = head
        if rank() == 0:
            emit("checkpoint.provenance_mismatch", git_sha_env=env_sha, git_sha_checkout=head)
    if out["git_sha_source"] == "none" and rank() == 0:
        emit("checkpoint.provenance_unknown", missing="git", detail="GIT_SHA unset and no git checkout")
    return out


def code_paths_from_env() -> list:
    """V5_CODE_PATHS: extra files that change the numbers, separated by os.pathsep (':' on Linux/macOS)."""
    return [p for p in os.environ.get("V5_CODE_PATHS", "").split(os.pathsep) if p]


def code_sha256(paths=()) -> str:
    """One sha256 over the contents of ckpt.py plus the files that change the numbers (trainer, model,
    loader). Sorted per-file hashes, so the same files on another machine or path give the same value."""
    files = {os.path.realpath(__file__)} | {os.path.realpath(p) for p in [*paths, *code_paths_from_env()]}
    return hashlib.sha256("\n".join(sorted(sha256_file(f) for f in files)).encode()).hexdigest()


def env_manifest(config_path: str = None, code_paths=()) -> dict:
    env = {
        **provenance(os.environ.get("GIT_SHA", "")),
        "code_sha256": code_sha256(code_paths),
        "image_digest": os.environ.get("IMAGE_DIGEST", "unknown"),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "cuda": torch.version.cuda or "none",
        "nccl": ".".join(map(str, torch.cuda.nccl.version())) if torch.cuda.is_available() else "none",
        "tokenizer_sha": os.environ.get("TOKENIZER_SHA", "unknown"),
        "config_sha256": sha256_file(config_path) if config_path and os.path.exists(config_path) else "none",
        # Found in the Docker test: OMP_NUM_THREADS changes the last bits of the loss on CPU even with
        # torch.set_num_threads(1). Thread count is part of the environment for a bit-equal resume.
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS", "unset"),
        # Team 04's embedding policy (KE2 Kronecker tables or plain): weights mean something else under another
        # policy even with the same shapes (millermuttu's meta field, team 07).
        "embedding_policy_id": os.environ.get("V5_EMBEDDING_POLICY_ID", "none"),
    }
    return env


# Fields that must match to resume. A change in any of them changes the numbers training produces.
# git_sha is not here (issue #298): a docs-only commit must not hold the run; code_sha256 checks the code itself.
ENV_MUST_MATCH = ("image_digest", "torch", "cuda", "nccl", "config_sha256", "tokenizer_sha", "code_sha256",
                  "omp_num_threads", "embedding_policy_id")
# What a field means in a manifest written before the field existed.
ENV_DEFAULTS = {"embedding_policy_id": "none"}
# Fields not checked against a manifest written before they existed (we cannot know the old value).
ENV_NOT_CHECKED_IF_MISSING = ("code_sha256",)


def env_diff(saved: dict, now: dict, keys) -> dict:
    """{key: [saved, now]} for every key that differs."""
    return {k: [saved.get(k, ENV_DEFAULTS.get(k)), now.get(k)] for k in keys
            if not (k in ENV_NOT_CHECKED_IF_MISSING and k not in saved)
            and saved.get(k, ENV_DEFAULTS.get(k)) != now.get(k)}


def load_loader_state(loader, state: dict):
    """The loader refuses a state from another shard list by raising ValueError (loader contract)."""
    try:
        loader.load_state_dict(state)
    except ValueError as e:
        raise DataManifestError(f"data loader refused the saved position: {e}") from e


def rng_capture() -> dict:
    st = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
        "cuda": [torch.cuda.get_rng_state(i) for i in range(torch.cuda.device_count())]
        if torch.cuda.is_available() else [],
    }
    return {"pickle_b64": base64.b64encode(pickle.dumps(st)).decode()}


def rng_restore(d: dict) -> None:
    st = pickle.loads(base64.b64decode(d["pickle_b64"]))
    random.setstate(st["python"])
    np.random.set_state(st["numpy"])
    torch.set_rng_state(st["torch_cpu"])
    for i, s in enumerate(st["cuda"][: torch.cuda.device_count()]):
        torch.cuda.set_rng_state(s, i)


def rng_reseed(seed: int, step: int, r: int) -> None:
    """After a world-size change the old per-rank RNG streams do not map to the new ranks."""
    s = (seed * 1_000_003 + step * 101 + r) % (2 ** 31)
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)


# ----------------------------------------------------------------------------- the checkpointer

def drill_value(name: str):
    """Test-only hooks for the Docker drills: a number in $V5_DRILL_DIR/<name>. Never set in production."""
    d = os.environ.get("V5_DRILL_DIR")
    p = os.path.join(d, name) if d else None
    if p and os.path.exists(p):
        try:
            return float(open(p).read().strip())
        except ValueError:
            return None
    return None


def run_url(remote_root: str, run_id: str) -> str:
    return remote_root.rstrip("/") + "/" + run_id


class Checkpointer:
    def __init__(self, run_id: str, local_root: str, remote_root: str, branch: str = "main",
                 keep_local: int = 2, config_path: str = None, seed: int = 0,
                 frozen_keys: tuple = (), upload_timeout_s: float = 300.0, nvme_headroom: float = 1.2,
                 verify_mode: str = None, code_paths=()):
        self.run_id = run_id
        self.branch = branch
        self.local_run = os.path.join(local_root, run_id)
        self.remote_url = run_url(remote_root, run_id)
        self.store = open_store(self.remote_url)
        self.keep_local = keep_local
        self.config_path = config_path
        # files whose change changes the numbers (code_sha256); checked now so a typo fails at start, not at save
        self.code_paths = tuple(code_paths)
        missing = [p for p in [*self.code_paths, *code_paths_from_env()] if not os.path.isfile(p)]
        if missing:
            raise FileNotFoundError(f"code_paths / V5_CODE_PATHS: no such file: {missing}")
        if not self.code_paths and not code_paths_from_env() and rank() == 0:
            emit("checkpoint.provenance_unknown", missing="code_paths",
                 detail="code_sha256 covers ckpt.py only; pass code_paths or set V5_CODE_PATHS")
        self.seed = seed
        self.frozen_keys = tuple(frozen_keys)
        self.upload_timeout_s = upload_timeout_s
        self.nvme_headroom = nvme_headroom
        # full: re-read and hash every object (tests, small checkpoints); head: trust S3's stored checksum
        self.verify_mode = verify_mode or os.environ.get("V5_VERIFY_MODE", "full")
        # async (default where torch has it): the stall is only the GPU -> host copy (ADR 0001 §2)
        self.async_save = hasattr(dcp, "async_save") and os.environ.get("V5_ASYNC_SAVE", "1") == "1"
        self._group = None
        self._thread = None
        self._ok = True
        self.last_rank_bytes = 0
        self.last_commit_step = None
        self.last_commit_time = None
        self.epoch = None        # this attempt's claim on latest.json (fencing); set by claim()
        self._ptr_ver = None     # version of latest.json this attempt last wrote (S3 ETag)
        self.fenced = False      # rank 0: a commit was refused because a newer attempt took over
        self._frozen_ref = None  # frozen fingerprints of the last restore or save, for the check at save
        os.makedirs(self.local_run, exist_ok=True)

    # ---- paths
    def step_rel(self, branch: str, step: int) -> str:
        return f"{branch}/step_{step:08d}-e{self.epoch}"

    # ---- fencing (ADR 0001 §3)
    def claim(self) -> int:
        """Claim the run for this attempt: epoch + 1 in latest.json, written only if latest.json is still the
        version we read. Every rank calls it; rank 0 writes. Returns the new epoch.

        In simple words: whoever claimed last owns the run. An older attempt that is still alive finds out
        at its next commit (its conditional write fails) and stops without touching the pointer."""
        if self.epoch is not None:
            return self.epoch
        out = None
        if rank() == 0:
            st = self.store
            for _ in range(20):
                cur, ver = st.get_json_ver("latest.json")
                cur = cur or {"step": None, "branch": None, "path": None}
                new = dict(cur, epoch=int(cur.get("epoch", 0)) + 1, job=os.environ.get("SLURM_JOB_ID"),
                           host=platform.node(), claimed_at=time.time())
                try:
                    self._ptr_ver = st.put_json_if("latest.json", new, ver)
                    out = (new["epoch"], None)
                    emit("checkpoint.claimed", epoch=new["epoch"], previous=cur.get("epoch"), job=new["job"],
                         step=cur.get("step"))
                    break
                except Conflict:
                    after = st.get_json_ver("latest.json")[0] or {}
                    if int(after.get("epoch", 0)) > int(cur.get("epoch", 0)):
                        # another attempt claimed at the same moment: it is the newer one
                        out = (None, f"attempt epoch {after.get('epoch')} claimed the run first")
                        break
                    # the old owner committed between our read and our write: read again
            else:
                out = (None, "latest.json kept changing; could not claim the run")
        epoch, err = broadcast_obj(out)
        if err:
            if rank() == 0:
                emit("checkpoint.fenced", phase="claim", detail=err)
            raise FencedError(err)
        self.epoch = epoch
        return epoch

    def check_frozen(self, frozen: dict, step: int):
        """Refuse to save when a frozen tensor changed since the last restore or save (same on every rank: the
        fingerprints come from one all-reduce)."""
        ref = self._frozen_ref
        changed = sorted(k for k in frozen if ref is not None and k in ref and ref[k] != frozen[k])
        if changed:
            if rank() == 0:
                emit("checkpoint.failed", step=step, cause="FrozenChangedError", detail=f"changed: {changed}")
            raise FrozenChangedError(f"frozen tensors changed since the last checkpoint: {changed}; not saved")
        self._frozen_ref = dict(frozen)

    def any_fenced(self) -> bool:
        """True on every rank if rank 0 had a commit refused (collective: all ranks must call it)."""
        return not all_true(not self.fenced)

    # ---- save
    def save(self, step: int, model, optim, loader, probe_fn, tokens: int = 0, reason: str = "interval") -> bool:
        """Blocking part of a save (the stall). The upload and commit run in a background thread.
        Returns False if the save was skipped (no disk space). Raises NonFiniteError on NaN/Inf."""
        t = Timer()
        self.claim()             # a no-op after restore(); a save without a restore claims here
        if rank() == 0:
            emit("checkpoint.started", step=step, reason=reason, branch=self.branch)
        waited = 0.0
        if self._thread is not None and self._thread.is_alive():
            # Only one save in flight. Waiting here is stall time: the interval is too short.
            tw = Timer()
            self._thread.join()
            waited = tw.s()
            if rank() == 0:
                emit("checkpoint.backpressure", step=step, waited_s=waited)

        msd, osd = get_state_dict(model, optim)
        state = {"model": msd, "optim": osd}
        if not all_true(all_finite(state)):
            if rank() == 0:
                emit("checkpoint.failed", step=step, cause="nonfinite", stall_s=t.s())
            raise NonFiniteError(f"NaN/Inf in the state at step {step}; not saved")

        local_dir = os.path.join(self.local_run, self.step_rel(self.branch, step))
        os.makedirs(local_dir, exist_ok=True)
        free = shutil.disk_usage(local_dir).free
        need = self.last_rank_bytes * int(os.environ.get("SLURM_NTASKS_PER_NODE", "1")) * self.nvme_headroom
        if not all_true(free >= need):
            if rank() == 0:
                emit("checkpoint.failed", step=step, cause="nvme_full", free_bytes=free, need_bytes=need)
            return False

        # Every rank runs these: under FSDP a forward pass and the fingerprint are collectives, and a
        # rank-0-only call would wait forever for the others.
        digest = state_digest(state)
        frozen = fingerprints(state, {f"model.{k}" for k in self.frozen_keys})
        self.check_frozen({k[len("model."):]: v for k, v in frozen.items()}, step)
        probe = float_bits(probe_fn(model))
        ld = loader.state_dict()
        loader_global = all_true(json.dumps(ld, sort_keys=True) == broadcast_obj(json.dumps(ld, sort_keys=True)))

        # The stall ends when the state is copied to host memory. dcp.async_save does that copy, then writes
        # the files from a background thread on its own gloo group (so it never shares NCCL with training).
        # It does not copy tensors that are already on the CPU, so we do (own_cpu_copies, test T27).
        fut = None
        if self.async_save:
            fut = dcp.async_save(own_cpu_copies(state), checkpoint_id=local_dir, process_group=self._save_group())
        else:
            dcp.save(state, checkpoint_id=local_dir)
        extra = {"step": step, "tokens": tokens, "world_size": world(), "rank": rank(),
                 "rng": rng_capture(), "loader": ld}
        with open(os.path.join(local_dir, f"extra_rank{rank()}.json"), "w") as f:
            json.dump(extra, f)

        meta = None
        if rank() == 0:
            meta = {
                "schema": SCHEMA, "run_id": self.run_id, "branch": self.branch, "step": step,
                "tokens": tokens, "world_size": world(), "reason": reason,
                "env": env_manifest(self.config_path, self.code_paths),
                "keys": key_spec(state),
                "state_digest": digest,
                "frozen": {k[len("model."):]: v for k, v in frozen.items()},
                "probe_loss": {device_class(model): probe},
                "next_batch": loader.next_batch_id(),
                # True: the data position is one global ledger offset, the same on every rank, so a restore
                # at another world size is safe (loader_contract.py). False: resume only at this world size.
                "loader_global": loader_global,
                "async_save": fut is not None,
            }
        stall = t.s()
        self._ok = True
        self._thread = threading.Thread(target=self._upload_and_commit,
                                        args=(step, local_dir, meta, stall, waited, fut), daemon=True)
        self._thread.start()
        return True

    def _save_group(self):
        """A gloo group just for checkpoint writes, made once (every rank must make it together)."""
        if not dist.is_initialized():
            return None
        if self._group is None:
            self._group = dist.new_group(backend="gloo")
        return self._group

    def _own_files(self, local_dir: str) -> list:
        r = rank()
        names = [n for n in os.listdir(local_dir)
                 if n.startswith(f"__{r}_") or n == f"extra_rank{r}.json" or (r == 0 and n == ".metadata")]
        return sorted(names)

    def _upload_and_commit(self, step, local_dir, meta, stall, waited, fut=None):
        t_start = time.time()
        rel = self.step_rel(self.branch, step)
        st = self.store
        try:
            tw = Timer()
            if fut is not None:
                fut.result()  # the async DCP write to this node's disk has finished (raises if it failed)
            write_s = tw.s()
            tu = Timer()
            sums, nbytes = {}, 0
            delay = drill_value("upload_delay_s")
            for name in self._own_files(local_dir):
                if delay:
                    time.sleep(delay)  # drill only: a slow upload, so a kill lands mid-save
                sha, n = st.put_file(os.path.join(local_dir, name), f"{rel}/{name}")
                sums[name] = {"sha256": sha, "bytes": n}
                nbytes += n
            self.last_rank_bytes = nbytes
            upload_s = tu.s()
            st.put_json(f"{rel}/sums_rank{rank()}.json", sums)
            if rank() != 0:
                return
            # Rank 0 waits for every rank's upload, then checks every object again in S3.
            files = {}
            for r in range(meta["world_size"]):
                key = f"{rel}/sums_rank{r}.json"
                if not wait_for(lambda: st.exists(key), self.upload_timeout_s):
                    raise UploadTimeout(f"rank {r} did not finish its upload in time")
                files.update(st.get_json(key))
            tv = Timer()
            bad = [n for n, s in files.items() if st.sha256(f"{rel}/{n}", self.verify_mode) != s["sha256"]]
            if bad:
                raise IntegrityError(f"checksum mismatch after upload: {bad}")
            verify_s = tv.s()
            total = sum(s["bytes"] for s in files.values())
            manifest = dict(meta, files=files, total_bytes=total, stall_s=stall,
                            committed_at=time.time(), store=st.kind)
            if os.environ.get("V5_TEST_CRASH_BEFORE_SEAL") == "1":
                os._exit(9)  # test T4 only: the process dies after the upload, before the seal
            st.put_json(f"{rel}/{MANIFEST}", manifest)
            # The commit point. Conditional: if a newer attempt claimed the run, this write fails and the
            # pointer stays theirs. The MANIFEST above sits in this attempt's own folder and is never used.
            try:
                self._ptr_ver = st.put_json_if("latest.json", {
                    "step": step, "branch": self.branch, "path": rel, "epoch": self.epoch,
                    "job": os.environ.get("SLURM_JOB_ID"), "host": platform.node()}, self._ptr_ver)
            except Conflict:
                now = st.get_json_ver("latest.json")[0] or {}
                raise FencedError(f"step {step} not committed: attempt epoch {now.get('epoch')} (job "
                                  f"{now.get('job')}) owns the run, this attempt is epoch {self.epoch}")
            st.append_line("commits.jsonl", json.dumps({"step": step, "branch": self.branch, "path": rel,
                                                        "time": manifest["committed_at"], "reason": meta["reason"],
                                                        "epoch": self.epoch}))
            self.last_commit_step, self.last_commit_time = step, manifest["committed_at"]
            latency = round(time.time() - t_start, 4)
            emit("checkpoint.committed", step=step, branch=self.branch, reason=meta["reason"], stall_s=stall,
                 backpressure_s=waited, commit_latency_s=latency, write_s=write_s, upload_s=upload_s, verify_s=verify_s,
                 bytes=total, store=st.kind, upload_gbps=round(nbytes * 8 / 1e9 / max(upload_s, 1e-6), 4))
        except Exception as e:  # noqa: BLE001 - every failure must become an event, then the caller decides
            self._ok = False
            if isinstance(e, FencedError):
                self.fenced = True
                emit("checkpoint.fenced", phase="commit", step=step, epoch=self.epoch, detail=str(e)[:500])
            emit("checkpoint.failed", step=step, cause=type(e).__name__, detail=str(e)[:500])
        finally:
            if local_rank() == 0:
                self._local_retention()

    def wait(self) -> bool:
        """Block until the background upload is done. Call before exiting, so the save is committed."""
        if self._thread is not None:
            self._thread.join()
        return all_true(self._ok)

    def _local_retention(self):
        dirs = []
        for b in os.listdir(self.local_run):
            bd = os.path.join(self.local_run, b)
            if os.path.isdir(bd) and b != "restore":
                dirs += [os.path.join(bd, s) for s in os.listdir(bd) if s.startswith("step_")]
        dirs.sort(key=lambda p: os.path.getmtime(p))
        for d in dirs[: max(0, len(dirs) - self.keep_local)]:
            shutil.rmtree(d, ignore_errors=True)

    # ---- restore
    def commits(self) -> list:
        if not self.store.exists("commits.jsonl"):
            return []
        return [json.loads(line) for line in self.store.get_text("commits.jsonl").splitlines() if line.strip()]

    def candidates(self, from_step: int = None) -> list:
        commits = self.commits()
        if from_step is not None:
            return [c for c in reversed(commits) if c["step"] == from_step][:1]
        if not self.store.exists("latest.json"):
            return []
        first = self.store.get_json("latest.json")
        rest = [c for c in reversed(commits) if c["path"] != first.get("path")]
        # a claim with no commit yet has path None: only the commit history is left to try
        return ([first] if first.get("path") else []) + rest

    def restore(self, model, optim, loader, probe_fn, from_step: int = None, skip: int = 0,
                new_branch: str = None, allow_env_change: bool = False):
        """Load the newest good checkpoint. Returns a dict about the restore, or None for a fresh start."""
        self.claim()             # before reading anything: from here on an older attempt cannot commit
        cands = self.candidates(from_step)
        if not cands:
            if from_step is not None:
                raise CheckpointError(f"no committed checkpoint at step {from_step}")
            return None
        for c in cands:
            try:
                info = self._restore_one(c, model, optim, loader, probe_fn, skip, allow_env_change)
                if new_branch:
                    self.branch = new_branch
                    info["branch"] = new_branch
                elif info["resharded"]:
                    self.branch = f"{c['branch']}-resharded-w{world()}"
                else:
                    self.branch = c["branch"]
                if rank() == 0:
                    emit("restore.done", **info)
                return info
            except (IntegrityError, RestoreCheckError) as e:
                if rank() == 0:
                    emit("restore.failed", step=c["step"], cause=type(e).__name__, detail=str(e)[:800],
                         fallback=from_step is None)
                if from_step is not None:
                    raise
        raise CheckpointError("no usable checkpoint: every committed checkpoint failed its checks")

    def _restore_one(self, c, model, optim, loader, probe_fn, skip, allow_env_change) -> dict:
        t = Timer()
        st = self.store
        rel = c["path"]
        man = st.get_json(f"{rel}/{MANIFEST}")
        if rank() == 0:
            emit("restore.started", step=man["step"], path=rel)
        delay = drill_value("restore_delay_s")
        if delay:
            time.sleep(delay)  # drill only: a slow restore, so a kill lands mid-restore

        # 1. Checksums of the objects in S3.
        tv = Timer()
        bad = None
        if rank() == 0:
            bad = [n for n, s in man["files"].items() if st.sha256(f"{rel}/{n}", self.verify_mode) != s["sha256"]]
        bad = broadcast_obj(bad)
        if bad:
            raise IntegrityError(f"step {c['step']}: checksum mismatch in {bad}")
        verify_s = tv.s()

        # 2. Environment.
        now = env_manifest(self.config_path, self.code_paths)
        diff = env_diff(man["env"], now, ENV_MUST_MATCH)
        if diff and not allow_env_change:
            raise EnvMismatchError(f"environment differs from the checkpoint: {diff}")

        # 3. Download to this node's disk (one copy per node), checking each copy's checksum.
        td = Timer()
        local_dir = os.path.join(self.local_run, "restore", rel)
        if local_rank() == 0:
            os.makedirs(local_dir, exist_ok=True)
            for n, s in man["files"].items():
                sha, _ = st.get_file(f"{rel}/{n}", os.path.join(local_dir, n))
                if sha != s["sha256"]:
                    raise IntegrityError(f"local copy of {n} is damaged")
        barrier()
        download_s = td.s()

        # 4. Strict key check: every name, shape and dtype must match. Lists every bad key.
        msd, osd = get_state_dict(model, optim)
        target = {"model": msd, "optim": osd}
        want, have = man["keys"], key_spec(target)
        missing = sorted(set(want) - set(have))
        unexpected = sorted(set(have) - set(want))
        changed = sorted(k for k in set(want) & set(have) if want[k] != have[k])
        if missing or unexpected or changed:
            raise StrictLoadError(f"strict load failed: missing in model={missing} "
                                  f"not in checkpoint={unexpected} shape/dtype differs={changed}")

        # 5. Load tensors (DCP reshards to the current world size), then RNG and data position.
        tl = Timer()
        dcp.load(target, checkpoint_id=local_dir)
        set_state_dict(model, optim, model_state_dict=target["model"], optim_state_dict=target["optim"])
        resharded = man["world_size"] != world()
        if resharded and not man.get("loader_global", False):
            raise ReshardError(f"step {c['step']} was saved at world size {man['world_size']} by a data loader "
                               f"with per-rank positions; it can only resume at that world size, not {world()}")
        extra_rank = 0 if resharded else rank()  # loader_global: every rank saved the same data position
        with open(os.path.join(local_dir, f"extra_rank{extra_rank}.json")) as f:
            extra = json.load(f)
        load_loader_state(loader, extra["loader"])
        if resharded:
            rng_reseed(self.seed, man["step"], rank())
        else:
            rng_restore(extra["rng"])
        load_s = tl.s()

        # 6. Checks: the restored state must be the saved state.
        tc = Timer()
        msd, osd = get_state_dict(model, optim)
        restored = {"model": msd, "optim": osd}
        problems = []
        digest = state_digest(restored)
        if digest != man["state_digest"]:
            problems.append(f"state digest saved={man['state_digest']} restored={digest}")
        dc = device_class(model)
        probe_now = float_bits(probe_fn(model))
        probe_saved = man["probe_loss"].get(dc)
        if probe_saved is not None and probe_now != probe_saved:
            problems.append(f"probe loss bits saved={probe_saved} restored={probe_now} ({dc})")
        nb = loader.next_batch_id()
        if nb != man["next_batch"]:
            problems.append(f"next batch saved={man['next_batch']} restored={nb}")
        frozen_now = fingerprints(restored, {f"model.{k}" for k in man["frozen"]})
        for k, h in man["frozen"].items():
            if frozen_now.get(f"model.{k}") != h:
                problems.append(f"frozen tensor {k} fingerprint differs")
        if not all_true(not problems):
            raise RestoreCheckError(f"step {c['step']}: " + "; ".join(problems or ["check failed on another rank"]))
        checks_s = tc.s()

        self._frozen_ref = dict(man["frozen"])
        if skip:
            loader.add_skip(skip)
        return {"step": man["step"], "tokens": man["tokens"], "branch": c["branch"], "from_path": rel,
                "resharded": resharded, "saved_world": man["world_size"], "world": world(),
                "env_override": sorted(diff) if diff else [], "skip": skip,
                "probe_recorded": probe_saved is not None, "store": st.kind,
                "verify_s": verify_s, "download_s": download_s, "load_s": load_s, "checks_s": checks_s,
                "restore_s": t.s()}


# ----------------------------------------------------------------------------- retention (own cloud role)

def run_retention(remote_run: str, keep: int = 3, protect_every: int = 0, dry_run: bool = False,
                  orphan_age_s: float = 3600.0) -> dict:
    """Delete old checkpoints from S3, never a protected one.

    In simple words: S3 storage costs money every month, so we keep only the newest few checkpoints,
    plus the ones that must never be lost (every N-th for evaluation, the final one, pinned ones, and
    whatever `latest.json` points to). On the cloud this runs as its own job with the only cloud role that may
    delete; the training job cannot delete anything.
    """
    st = open_store(remote_run)
    commits = []
    if st.exists("commits.jsonl"):
        commits = [json.loads(line) for line in st.get_text("commits.jsonl").splitlines() if line.strip()]
    pins = set(st.get_json("pins.json")) if st.exists("pins.json") else set()
    latest = st.get_json("latest.json")["path"] if st.exists("latest.json") else None
    protected = {c["path"] for i, c in enumerate(commits)
                 if (protect_every and (i + 1) % protect_every == 0) or c["reason"] == "final"
                 or c["step"] in pins}
    if latest:
        protected.add(latest)
    newest = {c["path"] for c in commits[-keep:]}
    committed = {c["path"] for c in commits}
    dirs = {}
    for o in st.list(""):
        parts = o["key"].split("/")
        if len(parts) >= 3 and parts[1].startswith("step_"):
            d = dirs.setdefault(f"{parts[0]}/{parts[1]}", {"size": 0, "mtime": 0, "manifest": False})
            d["size"] += o["size"]
            d["mtime"] = max(d["mtime"], o["mtime"])
            d["manifest"] |= parts[-1] == MANIFEST
    deleted, orphans, freed = [], [], 0
    for rel in sorted(dirs):
        d = dirs[rel]
        if rel in protected or rel in newest:
            continue
        if rel not in committed and not d["manifest"]:
            if time.time() - d["mtime"] < orphan_age_s:
                continue  # maybe a save still in flight
            orphans.append(rel)
        else:
            deleted.append(rel)
        freed += d["size"]
        if not dry_run:
            st.delete_prefix(rel)
    out = {"deleted": deleted, "orphans": orphans, "protected": sorted(protected), "freed_bytes": freed,
           "kept": sorted(newest | protected), "store": st.kind}
    emit("checkpoint.retention", **{k: v for k, v in out.items() if k != "kept"}, dry_run=dry_run)
    return out


# ----------------------------------------------------------------------------- export for other teams

def export_safetensors(remote_run: str, model_factory, probe_fn, out_path: str, step: int = None) -> dict:
    """dcp -> safetensors for Teams 09/11/12, with the same strict-key and probe-loss checks.

    In simple words: other teams get one plain file format that any tool can read, and we prove the
    exported weights give exactly the same probe loss as the checkpoint.
    """
    import tempfile

    from safetensors.torch import load_file, save_file

    root, run_id = remote_run.rstrip("/").rsplit("/", 1)
    ck = Checkpointer(run_id, local_root=tempfile.mkdtemp(), remote_root=root)
    c = ck.candidates(step)[0]
    man = ck.store.get_json(f"{c['path']}/{MANIFEST}")
    local_dir = os.path.join(ck.local_run, "export", c["path"])
    for n, s in man["files"].items():
        sha, _ = ck.store.get_file(f"{c['path']}/{n}", os.path.join(local_dir, n))
        if sha != s["sha256"]:
            raise IntegrityError(f"export: {n} is damaged")
    if man.get("backend") == "deepspeed":
        from ckpt.ds_ckpt import export_ds
        return export_ds(ck, c, man, local_dir, model_factory, probe_fn, out_path)
    model = model_factory()
    target = {"model": model.state_dict()}
    want = {k: v for k, v in man["keys"].items() if k.startswith("model.")}
    have = key_spec(target)
    if want != have:
        raise StrictLoadError(f"export key mismatch: missing={sorted(set(want) - set(have))} "
                              f"extra={sorted(set(have) - set(want))}")
    dcp.load(target, checkpoint_id=local_dir)
    model.load_state_dict(target["model"], strict=True)
    save_file({k: v.contiguous() for k, v in model.state_dict().items()}, out_path,
              metadata={"run_id": man["run_id"], "step": str(man["step"]), "state_digest": man["state_digest"]})
    shutil.rmtree(ck.local_run, ignore_errors=True)
    fresh = model_factory()
    fresh.load_state_dict(load_file(out_path), strict=True)
    bits = float_bits(probe_fn(fresh))
    saved = man["probe_loss"].get(device_class(fresh))
    ok = saved is None or bits == saved
    emit("export.done" if ok else "export.failed", step=man["step"], path=out_path, probe_equal=ok)
    if not ok:
        raise RestoreCheckError(f"export probe loss bits differ: saved={saved} exported={bits}")
    return {"step": man["step"], "path": out_path, "probe_bits": bits}


def probe_store(remote_run: str) -> dict:
    """Pre-flight for a run's checkpoint store (launch.sh step `store`). Fencing (§3) is only safe if the store
    refuses a write against an old version; an S3 endpoint or emulator that ignores If-Match would let two
    attempts commit. Writes and deletes one scratch object; never touches latest.json."""
    st = open_store(remote_run)
    key = f"_probe/{platform.node()}-{os.getpid()}.json"
    out = {"store": st.kind, "run": remote_run, "write": False, "stale_refused": False, "new_refused": False}
    try:
        v1 = st.put_json_if(key, {"n": 1}, None)
        out["write"] = st.get_json_ver(key)[0] == {"n": 1}
        st.put_json_if(key, {"n": 2}, v1)
        try:
            st.put_json_if(key, {"n": 3}, v1)
        except Conflict:
            out["stale_refused"] = True
        try:
            st.put_json_if(key, {"n": 4}, None)
        except Conflict:
            out["new_refused"] = True
    except Exception as e:  # noqa: BLE001 - the probe reports, the operator decides
        out["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    finally:
        try:
            st.delete_prefix("_probe")
        except Exception:  # noqa: BLE001
            pass
    out["ok"] = out["write"] and out["stale_refused"] and out["new_refused"]
    return out


# ----------------------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description="V5 checkpoint tools")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="check every file of a committed checkpoint against its manifest")
    v.add_argument("--run", required=True, help="<remote_root>/<run_id>: a folder or s3://bucket/prefix/run")
    v.add_argument("--step", type=int)
    r = sub.add_parser("retention", help="delete old, unprotected checkpoints")
    r.add_argument("--run", required=True)
    r.add_argument("--keep", type=int, default=3)
    r.add_argument("--protect-every", type=int, default=0)
    r.add_argument("--dry-run", action="store_true")
    ls = sub.add_parser("list", help="list committed checkpoints")
    ls.add_argument("--run", required=True)
    p = sub.add_parser("pin", help="protect a step from retention")
    p.add_argument("--run", required=True)
    p.add_argument("--step", type=int, required=True)
    ps = sub.add_parser("probe-store", help="before a run: can we write, read, and is a stale write refused?")
    ps.add_argument("--run", required=True)
    a = ap.parse_args()

    if a.cmd == "probe-store":
        out = probe_store(a.run)
        print(json.dumps(out))
        return 0 if out["ok"] else 1
    if a.cmd == "retention":
        print(json.dumps(run_retention(a.run, a.keep, a.protect_every, a.dry_run), indent=1))
        return 0
    root, run_id = a.run.rstrip("/").rsplit("/", 1)
    ck = Checkpointer(run_id, local_root="/tmp", remote_root=root)
    if a.cmd == "list":
        for c in ck.commits():
            print(json.dumps(c))
        return 0
    if a.cmd == "pin":
        pins = ck.store.get_json("pins.json") if ck.store.exists("pins.json") else []
        ck.store.put_json("pins.json", sorted(set(pins) | {a.step}))
        return 0
    c = ck.candidates(a.step)[0]
    man = ck.store.get_json(f"{c['path']}/{MANIFEST}")
    bad = [n for n, s in man["files"].items() if ck.store.sha256(f"{c['path']}/{n}") != s["sha256"]]
    print(json.dumps({"step": c["step"], "path": c["path"], "files": len(man["files"]), "bad": bad}))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
