"""Executable Parquet writer, gating policy, and 14-day retention manager for `v5-token-records/1`.

Implements `teams/08-monitoring/docs/per_token_records.md` (Team 08 & Team 05):
  - PyArrow schema (`PER_TOKEN_PARQUET_SCHEMA`) with dictionary-encoded token IDs and fixed-size MoE lists.
  - Hierarchical path layout:
        records/per_token/run_id={run_id}/step_bucket={step_bucket}/part-step_{step:08d}-rank_{rank:02d}.parquet
  - ZSTD compression (level 3) and 65,536-row groups.
  - Four deterministic activation triggers (diagnostic warmup / checkpoint windows, 3-sigma EMA / non-finite /
    2x loss anomaly with 10-step post-anomaly tail, entropy divergence < 0.5 or > 8.0 nats, and explicit /
    eval-slice override).
  - 14-day retention pruning that honours `INCIDENT_RETAIN=true` Parquet file metadata.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import time
from typing import Iterable, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA_VERSION = "v5-token-records/1"
DEFAULT_RETENTION_DAYS = 14
DEFAULT_ROW_GROUP_SIZE = 65_536
IGNORE_INDEX = -100
LN2 = math.log(2.0)

PER_TOKEN_PARQUET_SCHEMA = pa.schema(
    [
        pa.field("step", pa.uint64(), nullable=False),
        pa.field("batch_idx", pa.uint16(), nullable=False),
        pa.field("seq_idx", pa.uint16(), nullable=False),
        pa.field("token_id", pa.dictionary(pa.int32(), pa.uint32()), nullable=False),
        pa.field("target_id", pa.int64(), nullable=False),
        pa.field("loss_nats", pa.float32(), nullable=False),
        pa.field("loss_bpc", pa.float32(), nullable=True),
        pa.field("entropy", pa.float32(), nullable=False),
        pa.field("top1_id", pa.dictionary(pa.int32(), pa.uint32()), nullable=False),
        pa.field("top1_prob", pa.float32(), nullable=False),
        pa.field("is_correct", pa.uint8(), nullable=False),
        # Validated to length 2 on non-null rows in build_arrow_table(); stored as standard Parquet LIST
        # so nullable dense-layer rows round-trip without PyArrow's FixedSizeList null-element reader bug.
        pa.field("expert_ids", pa.list_(pa.uint8()), nullable=True),
        pa.field("expert_weights", pa.list_(pa.float32()), nullable=True),
    ]
)


def partition_path(root_dir: str | os.PathLike, run_id: str, step: int, rank: int = 0) -> Path:
    """Return canonical Parquet path for `(run_id, step, rank)`."""
    if step < 0:
        raise ValueError(f"step must be non-negative, got {step}")
    if rank < 0:
        raise ValueError(f"rank must be non-negative, got {rank}")
    step_bucket = (step // 1000) * 1000
    return (
        Path(root_dir)
        / "records"
        / "per_token"
        / f"run_id={run_id}"
        / f"step_bucket={step_bucket}"
        / f"part-step_{step:08d}-rank_{rank:02d}.parquet"
    )


class PerTokenActivationPolicy:
    """Deterministic step-level gating policy from `docs/per_token_records.md` §5."""

    def __init__(
        self,
        *,
        warmup_end_step: int = 100,
        checkpoint_interval: int | None = None,
        ckpt_pre_steps: int = 20,
        ckpt_post_steps: int = 10,
        ema_alpha: float = 0.05,
        sigma_threshold: float = 3.0,
        spike_ratio: float = 2.0,
        anomaly_tail_steps: int = 10,
        entropy_min: float = 0.5,
        entropy_max: float = 8.0,
        min_ema_warmup: int = 5,
    ) -> None:
        self.warmup_end_step = warmup_end_step
        self.checkpoint_interval = checkpoint_interval
        self.ckpt_pre_steps = ckpt_pre_steps
        self.ckpt_post_steps = ckpt_post_steps
        self.ema_alpha = ema_alpha
        self.sigma_threshold = sigma_threshold
        self.spike_ratio = spike_ratio
        self.anomaly_tail_steps = anomaly_tail_steps
        self.entropy_min = entropy_min
        self.entropy_max = entropy_max
        self.min_ema_warmup = min_ema_warmup

        self._ema_mean: float | None = None
        self._ema_var: float = 0.0
        self._seen: int = 0
        self._anomaly_until_step: int = -1

    def evaluate(
        self,
        step: int,
        *,
        step_loss: float | None = None,
        mean_entropy: float | None = None,
        is_eval_slice: bool = False,
        force: bool = False,
    ) -> tuple[bool, list[str]]:
        """Return `(should_record, reasons)` and advance internal EMA state."""
        reasons: list[str] = []

        if force:
            reasons.append("explicit_flag")
        if is_eval_slice:
            reasons.append("eval_slice")
        if 0 <= step <= self.warmup_end_step:
            reasons.append("diagnostic_warmup")

        if self.checkpoint_interval and self.checkpoint_interval > 0 and step > 0:
            nearest_k = round(step / self.checkpoint_interval)
            if nearest_k >= 1:
                ckpt_step = nearest_k * self.checkpoint_interval
                if (ckpt_step - self.ckpt_pre_steps) <= step <= (ckpt_step + self.ckpt_post_steps):
                    reasons.append("checkpoint_window")

        anomaly_now = False
        if step_loss is not None:
            val = float(step_loss)
            if not math.isfinite(val):
                reasons.append("loss_non_finite")
                anomaly_now = True
            else:
                if self._ema_mean is None:
                    self._ema_mean = val
                    self._ema_var = 0.0
                    self._seen = 1
                else:
                    delta = abs(val - self._ema_mean)
                    sigma = math.sqrt(max(self._ema_var, 1e-12))
                    if self._seen >= self.min_ema_warmup:
                        if self._ema_mean > 0 and val >= self.spike_ratio * self._ema_mean:
                            reasons.append("loss_spike_2x")
                            anomaly_now = True
                        elif sigma > 0 and delta > self.sigma_threshold * sigma:
                            reasons.append("loss_ema_3sigma")
                            anomaly_now = True
                    # Update EMA stats on finite observations that are not wild 2x spikes
                    if not anomaly_now:
                        a = self.ema_alpha
                        diff = val - self._ema_mean
                        self._ema_mean = (1.0 - a) * self._ema_mean + a * val
                        if self._seen == 1:
                            self._ema_var = diff * diff
                        else:
                            self._ema_var = (1.0 - a) * (self._ema_var + a * diff * diff)
                        self._seen += 1

        if anomaly_now:
            self._anomaly_until_step = max(self._anomaly_until_step, step + self.anomaly_tail_steps)
        elif step <= self._anomaly_until_step:
            reasons.append("post_anomaly_tail")

        if mean_entropy is not None:
            ent = float(mean_entropy)
            if not math.isfinite(ent) or ent < self.entropy_min or ent > self.entropy_max:
                reasons.append("entropy_divergence")

        return (len(reasons) > 0), reasons


def build_arrow_table(records: Sequence[Mapping[str, object]]) -> pa.Table:
    """Convert row dicts into a schema-validated `PER_TOKEN_PARQUET_SCHEMA` PyArrow Table."""
    cols: dict[str, list] = {field.name: [] for field in PER_TOKEN_PARQUET_SCHEMA}
    for row in records:
        target_id = int(row["target_id"])
        loss_nats = float(row["loss_nats"])
        top1_id = int(row["top1_id"])
        if target_id == IGNORE_INDEX:
            loss_bpc = None
            is_correct = 0
        else:
            raw_bpc = row.get("loss_bpc")
            if raw_bpc is not None:
                loss_bpc = float(raw_bpc)
            else:
                utf8_bytes = row.get("utf8_bytes")
                loss_bpc = (loss_nats / (LN2 * float(utf8_bytes))) if utf8_bytes else None
            is_correct = int(row.get("is_correct", int(top1_id == target_id)))

        expert_ids = row.get("expert_ids")
        expert_weights = row.get("expert_weights")
        if expert_ids is not None:
            expert_ids = [int(x) for x in expert_ids]
            if len(expert_ids) != 2:
                raise ValueError(f"expert_ids must have length 2, got {len(expert_ids)}")
        if expert_weights is not None:
            expert_weights = [float(x) for x in expert_weights]
            if len(expert_weights) != 2:
                raise ValueError(f"expert_weights must have length 2, got {len(expert_weights)}")

        cols["step"].append(int(row["step"]))
        cols["batch_idx"].append(int(row["batch_idx"]))
        cols["seq_idx"].append(int(row["seq_idx"]))
        cols["token_id"].append(int(row["token_id"]))
        cols["target_id"].append(target_id)
        cols["loss_nats"].append(loss_nats)
        cols["loss_bpc"].append(loss_bpc)
        cols["entropy"].append(float(row["entropy"]))
        cols["top1_id"].append(top1_id)
        cols["top1_prob"].append(float(row["top1_prob"]))
        cols["is_correct"].append(is_correct)
        cols["expert_ids"].append(expert_ids)
        cols["expert_weights"].append(expert_weights)

    arrays = [
        pa.array(cols["step"], type=pa.uint64()),
        pa.array(cols["batch_idx"], type=pa.uint16()),
        pa.array(cols["seq_idx"], type=pa.uint16()),
        pa.array(cols["token_id"], type=pa.uint32()).dictionary_encode(),
        pa.array(cols["target_id"], type=pa.int64()),
        pa.array(cols["loss_nats"], type=pa.float32()),
        pa.array(cols["loss_bpc"], type=pa.float32()),
        pa.array(cols["entropy"], type=pa.float32()),
        pa.array(cols["top1_id"], type=pa.uint32()).dictionary_encode(),
        pa.array(cols["top1_prob"], type=pa.float32()),
        pa.array(cols["is_correct"], type=pa.uint8()),
        pa.array(cols["expert_ids"], type=pa.list_(pa.uint8())),
        pa.array(cols["expert_weights"], type=pa.list_(pa.float32())),
    ]
    return pa.Table.from_arrays(arrays, schema=PER_TOKEN_PARQUET_SCHEMA)


class PerTokenParquetWriter:
    """Writes gated per-token step records to ZSTD-3 Parquet partitions."""

    def __init__(
        self,
        root_dir: str | os.PathLike,
        run_id: str,
        *,
        policy: PerTokenActivationPolicy | None = None,
        compression_level: int = 3,
        row_group_size: int = DEFAULT_ROW_GROUP_SIZE,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.run_id = run_id
        self.policy = policy or PerTokenActivationPolicy()
        self.compression_level = compression_level
        self.row_group_size = row_group_size

    def write_step(
        self,
        step: int,
        records: Sequence[Mapping[str, object]],
        *,
        rank: int = 0,
        step_loss: float | None = None,
        mean_entropy: float | None = None,
        is_eval_slice: bool = False,
        force: bool = False,
        incident_retain: bool = False,
    ) -> Path | None:
        """Evaluate gating policy and write Parquet partition when active; else return `None`."""
        active, reasons = self.policy.evaluate(
            step,
            step_loss=step_loss,
            mean_entropy=mean_entropy,
            is_eval_slice=is_eval_slice,
            force=force,
        )
        if not active or not records:
            return None

        auto_incident = incident_retain or any(
            r in ("loss_non_finite", "loss_spike_2x", "loss_ema_3sigma", "entropy_divergence")
            for r in reasons
        )
        table = build_arrow_table(records)
        meta = dict(table.schema.metadata or {})
        meta[b"schema_version"] = SCHEMA_VERSION.encode("utf-8")
        meta[b"run_id"] = self.run_id.encode("utf-8")
        meta[b"trigger_reasons"] = ",".join(reasons).encode("utf-8")
        meta[b"INCIDENT_RETAIN"] = b"true" if auto_incident else b"false"
        table = table.replace_schema_metadata(meta)

        out_path = partition_path(self.root_dir, self.run_id, step, rank=rank)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = out_path.with_suffix(".parquet.tmp")
        pq.write_table(
            table,
            tmp_path,
            compression="zstd",
            compression_level=self.compression_level,
            row_group_size=self.row_group_size,
        )
        os.replace(tmp_path, out_path)
        return out_path


def is_incident_retained(parquet_file: str | os.PathLike) -> bool:
    """Return True if the Parquet file carries `INCIDENT_RETAIN=true` in its schema metadata."""
    schema = pq.read_schema(parquet_file)
    meta = schema.metadata or {}
    return meta.get(b"INCIDENT_RETAIN", b"false").lower() == b"true"


def prune_expired_parquet(
    root_dir: str | os.PathLike,
    *,
    retention_days: float = DEFAULT_RETENTION_DAYS,
    now_ts: float | None = None,
) -> list[Path]:
    """Delete `.parquet` files older than `retention_days` unless `INCIDENT_RETAIN=true`."""
    base = Path(root_dir) / "records" / "per_token"
    if not base.exists():
        return []
    now = time.time() if now_ts is None else float(now_ts)
    cutoff = now - retention_days * 86_400.0
    removed: list[Path] = []
    for p in sorted(base.rglob("*.parquet")):
        if p.stat().st_mtime >= cutoff:
            continue
        if is_incident_retained(p):
            continue
        p.unlink()
        removed.append(p)
    return removed
