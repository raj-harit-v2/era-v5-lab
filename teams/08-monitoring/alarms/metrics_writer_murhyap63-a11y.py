"""Small test-compatible MetricsWriter for standalone Team 8 telemetry fixture."""
import json
import math
from pathlib import Path

FLUSH_EVERY = 10


def _has_nonfinite(value):
    if isinstance(value, dict):
        return any(_has_nonfinite(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_nonfinite(v) for v in value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return not math.isfinite(float(value))
    return False


class MetricsWriter:
    def __init__(self, path, flush_every=FLUSH_EVERY):
        if flush_every < 1:
            raise ValueError("flush_every must be >= 1")
        self.path = Path(path)
        self.flush_every = flush_every
        self.handle = self.path.open("w", encoding="utf-8")
        self.buffer = []

    def write(self, step, **metrics):
        row = {"step": step, **metrics}
        # Metrics in this isolated fixture are plain JSON scalar fields.
        self.buffer.append(json.dumps(row, allow_nan=True))
        if _has_nonfinite(metrics) or step % self.flush_every == 0:
            self.flush()

    def flush(self):
        if self.buffer:
            self.handle.write("\n".join(self.buffer) + "\n")
            self.handle.flush()
            self.buffer.clear()

    def close(self):
        self.flush()
        self.handle.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
