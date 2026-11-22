"""Adapt the single-process G5 trainer to Team 7's checkpoint contract."""

import hashlib
import os
from pathlib import Path
import tempfile

import torch


class CheckpointProgress:
    def __init__(self, stream, identity, run_id):
        self.stream = stream
        self.identity = identity
        self.run_id = run_id
        self.history = None

    def state_dict(self):
        sampler = self.stream.state_dict()
        sampler["rng"] = sampler["rng"].tolist()
        return {
            "identity_sha256": self.identity, "run_id": self.run_id,
            "sampler": sampler, "history": self.history,
        }

    def load_state_dict(self, state):
        if state["identity_sha256"] != self.identity:
            raise ValueError("G5 code/config/artifact/data/device/software identity changed")
        if state.get("run_id") != self.run_id:
            raise ValueError("G5 checkpoint run ID does not match --run-id")
        sampler = dict(state["sampler"])
        sampler["rng"] = torch.tensor(sampler["rng"], dtype=torch.uint8, device="cpu")
        self.stream.load_state_dict(sampler)
        self.history = state["history"]

    def next_batch_id(self):
        state = self.stream.state_dict()
        try:
            batch = self.stream.next("cpu")
        finally:
            self.stream.load_state_dict(state)
        digest = hashlib.sha256()
        for tensor in batch:
            digest.update(tensor.numpy().tobytes())
        return {"position": state["offset"], "sha256": digest.hexdigest()}


def write_native_checkpoint(state, path):
    """Publish the compatibility artifact only after its write has finished."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".checkpoint-", delete=False) as stream:
            temporary = Path(stream.name)
            torch.save(state, stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
