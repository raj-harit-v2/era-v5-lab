"""Tests for `per_token_parquet.py` (`v5-token-records/1` schema, ZSTD-3, gating, 14-day retention)."""
from __future__ import annotations

import math
import os
from pathlib import Path
import sys
import time

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from per_token_parquet import (
    IGNORE_INDEX,
    PER_TOKEN_PARQUET_SCHEMA,
    PerTokenActivationPolicy,
    PerTokenParquetWriter,
    is_incident_retained,
    partition_path,
    prune_expired_parquet,
)


def _sample_rows(step: int):
    return [
        {
            "step": step,
            "batch_idx": 0,
            "seq_idx": 0,
            "token_id": 1024,
            "target_id": 2048,
            "loss_nats": 1.3862944,
            "utf8_bytes": 2,
            "entropy": 2.5,
            "top1_id": 2048,
            "top1_prob": 0.62,
            "expert_ids": [1, 5],
            "expert_weights": [0.7, 0.3],
        },
        {
            "step": step,
            "batch_idx": 0,
            "seq_idx": 1,
            "token_id": 2048,
            "target_id": IGNORE_INDEX,
            "loss_nats": 0.0,
            "entropy": 2.1,
            "top1_id": 99,
            "top1_prob": 0.40,
            "expert_ids": None,
            "expert_weights": None,
        },
    ]


def test_parquet_schema_roundtrip_and_partition_layout(tmp_path):
    writer = PerTokenParquetWriter(tmp_path, "dryrun1_smoke")
    out = writer.write_step(42, _sample_rows(42), rank=3, step_loss=2.4, mean_entropy=2.3)
    assert out == partition_path(tmp_path, "dryrun1_smoke", 42, rank=3)
    assert out is not None and out.exists()
    assert "run_id=dryrun1_smoke" in str(out)
    assert "step_bucket=0" in str(out)
    assert out.name == "part-step_00000042-rank_03.parquet"

    meta = pq.read_metadata(out)
    assert meta.num_rows == 2
    assert meta.row_group(0).column(0).compression.upper() == "ZSTD"

    tbl = pq.ParquetFile(out).read()
    assert tbl.column_names == PER_TOKEN_PARQUET_SCHEMA.names
    rows = tbl.to_pylist()
    assert rows[0]["is_correct"] == 1
    assert rows[0]["loss_bpc"] is not None and math.isclose(rows[0]["loss_bpc"], 1.0, rel_tol=1e-5)
    assert rows[0]["expert_ids"] == [1, 5]
    # Masked target (-100) must store NULL loss_bpc and is_correct == 0
    assert rows[1]["target_id"] == IGNORE_INDEX
    assert rows[1]["loss_bpc"] is None
    assert rows[1]["is_correct"] == 0
    assert rows[1]["expert_ids"] is None


def test_activation_gating_triggers(tmp_path):
    pol = PerTokenActivationPolicy(warmup_end_step=2, checkpoint_interval=500, min_ema_warmup=5)
    writer = PerTokenParquetWriter(tmp_path, "gate_test", policy=pol)

    # 1. Warmup steps 0..2 record; steady steps 3..20 skip
    assert writer.write_step(0, _sample_rows(0), step_loss=2.5, mean_entropy=2.4) is not None
    for s in range(1, 15):
        res = writer.write_step(s, _sample_rows(s), step_loss=2.5 + (s % 2) * 0.01, mean_entropy=2.4)
        if s <= 2:
            assert res is not None
        else:
            assert res is None

    # 2. Checkpoint window around 500 ([480, 510]) records; 479 skips
    assert writer.write_step(479, _sample_rows(479), step_loss=2.5, mean_entropy=2.4) is None
    assert writer.write_step(480, _sample_rows(480), step_loss=2.5, mean_entropy=2.4) is not None
    assert writer.write_step(510, _sample_rows(510), step_loss=2.5, mean_entropy=2.4) is not None
    assert writer.write_step(511, _sample_rows(511), step_loss=2.5, mean_entropy=2.4) is None

    # 3. 2x loss spike at step 600 triggers incident retention + 10-step tail (601..610)
    spike_file = writer.write_step(600, _sample_rows(600), step_loss=6.0, mean_entropy=2.4)
    assert spike_file is not None
    assert is_incident_retained(spike_file)
    assert writer.write_step(610, _sample_rows(610), step_loss=2.5, mean_entropy=2.4) is not None
    assert writer.write_step(611, _sample_rows(611), step_loss=2.5, mean_entropy=2.4) is None

    # 4. Entropy divergence (< 0.5 or > 8.0) and eval-slice override
    ent_file = writer.write_step(700, _sample_rows(700), step_loss=2.5, mean_entropy=0.2)
    assert ent_file is not None and is_incident_retained(ent_file)
    assert writer.write_step(750, _sample_rows(750), step_loss=2.5, mean_entropy=2.4, is_eval_slice=True) is not None


def test_14_day_retention_prunes_normal_files_and_keeps_incidents(tmp_path):
    writer = PerTokenParquetWriter(tmp_path, "ttl_run")
    normal_old = writer.write_step(1, _sample_rows(1), step_loss=2.5, mean_entropy=2.4)
    incident_old = writer.write_step(2, _sample_rows(2), step_loss=float("nan"), mean_entropy=2.4)
    normal_recent = writer.write_step(3, _sample_rows(3), step_loss=2.5, mean_entropy=2.4, force=True)

    assert normal_old and incident_old and normal_recent
    now = time.time()
    sixteen_days_ago = now - 16 * 86_400
    os.utime(normal_old, (sixteen_days_ago, sixteen_days_ago))
    os.utime(incident_old, (sixteen_days_ago, sixteen_days_ago))

    removed = prune_expired_parquet(tmp_path, retention_days=14, now_ts=now)
    assert removed == [normal_old]
    assert not normal_old.exists()
    assert incident_old.exists(), "INCIDENT_RETAIN=true file must survive 14-day pruning"
    assert normal_recent.exists()
