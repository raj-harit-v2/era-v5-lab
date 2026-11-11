"""Adapter so G5's week-2 trainer writes G8 metrics through MetricsWriter.

teams/05-architecture/harness/train_week2.py takes `--logger-factory module:function`. It calls
`function(out_dir)` once and then, for every row it logs, `writer.write(row)` with one dict (the step is
`row["step"]`), plus `flush()` and `close()`. MetricsWriter takes `write(step, **metrics)`, so it does not plug
in directly. `make_writer` returns an object with the trainer's interface that passes each row on:

    cd teams/05-architecture/harness
    PYTHONPATH=../../08-monitoring/metrics_logger \\
        python train_week2.py ... --out runs/r1 --logger-factory g5_adapter:make_writer

G8 rows go to `<out>/g8/metrics.jsonl`. G5's own `<out>/metrics.jsonl` is left alone (its JsonWriter opens it
with "w", so the two must not share a file). Load the G8 file into ClickHouse with the run name:

    python teams/08-monitoring/clickhouse/load_jsonl.py runs/r1/g8/metrics.jsonl --run-id r1

What happens to G5's row:
- `loss_ntp`, `loss_mtp`, `tokens_per_second` are written as they are; `gpu_alloc_gb` becomes `gpu_alloc_gib`.
- `gradient_clipping_applied` (a bool in G5's row) is stored as 0 / 1.
- On validation steps, `val/nll_nats` / `val/scored_tokens` give `validation_loss` (MetricsWriter does this).
- `tokens_per_byte` is worked out as `train/scored_tokens / train/utf8_bytes` (the whole batch), unless the
  row already has it.
- G5-only names that have no G8 metric (`train/ce_loss`, `loss_total`, `perf/step_ms`, `val/bpb`, ...) are
  dropped without a warning. Any other unknown name still gets MetricsWriter's one-time warning, so a new G5
  field is noticed.
"""

import os

from metrics_writer import FLUSH_EVERY, MetricsWriter

# Fields in G5's row that have no G8 metric. Dropped quietly (MetricsWriter would warn once for each).
G5_ONLY = frozenset({
    "train/ce_loss", "loss_total", "train/scored_tokens", "train/input_positions", "train/utf8_bytes",
    "perf/step_ms", "val/bpb", "val/perplexity",
})


def _tokens_per_byte(row):
    tokens, nbytes = row.get("train/scored_tokens"), row.get("train/utf8_bytes")
    if isinstance(tokens, bool) or isinstance(nbytes, bool):
        return None
    try:
        tokens, nbytes = float(tokens), float(nbytes)
    except (TypeError, ValueError):
        return None
    if nbytes <= 0 or tokens < 0:
        return None
    return tokens / nbytes


class G5Writer:
    """The trainer's writer interface (write(row) / flush() / close()) over a MetricsWriter."""

    def __init__(self, path, flush_every=FLUSH_EVERY):
        self.writer = MetricsWriter(path, flush_every=flush_every)
        self.path = path

    def write(self, row):
        if "step" not in row:
            raise ValueError("G5 row has no 'step'")
        metrics = {name: value for name, value in row.items() if name != "step" and name not in G5_ONLY}
        if "tokens_per_byte" not in metrics:
            tpb = _tokens_per_byte(row)
            if tpb is not None:
                metrics["tokens_per_byte"] = tpb
        self.writer.write(int(row["step"]), **metrics)

    def flush(self):
        self.writer.flush()

    def close(self):
        self.writer.close()


def make_writer(out_dir):
    """Factory for train_week2.py's --logger-factory: rows go to <out_dir>/g8/metrics.jsonl."""
    return G5Writer(os.path.join(os.fspath(out_dir), "g8", "metrics.jsonl"))
