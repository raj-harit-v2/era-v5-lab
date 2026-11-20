"""ILLUSTRATION ONLY. Build the sample log for dryrun1_loss_sample_attn0.md: the real attn-0 metrics with injected events.

Usage (from the repository root):
    python -I teams/05-architecture/experiments/results/dryrun1_make_sample_log.py

Reads   teams/05-architecture/jobs/evidence/2026-11-10-attention-screen/attn-0/metrics.jsonl (the real T2 reference
        run of 10 Nov, 1,221 steps) and
writes  teams/05-architecture/experiments/results/dryrun1_sample_log.jsonl, the same values with the events below
        injected, so the sample record can show every kind of row the real record may need. Deterministic: the
        output is the same on every run. Nothing here happened in a real run.

Injected events (attempt = one launch of the trainer; a rollback starts a new attempt at an earlier step):
  1. step 300, attempt 1: loss_ntp x 2.0 for one step (a single loss spike; the run goes on).
  2. step 520, attempt 1: a preemption, exit 75 (saved, requeued, no step lost). It changes no metric: a requeue
     that loses no step is only in the job log, so the sample's stops table adds it by hand.
  3. steps 700 to 702, attempt 1: loss_ntp x 2.0 three steps in a row (Team 7's guard stops: exit 78, held).
     A person rolls back to the checkpoint at step 650: attempt 2 starts at step 651.
  4. step 950, attempt 2: loss_ntp, loss_mtp and gradient_norm are NaN (stop: exit 78, held). A person rolls back
     to step 900: attempt 3 starts at step 901.
  The real gradient-norm spike at step 1085 stays as it is (attempt 3).
After a rollback the real procedure skips 5 batches (USER_GUIDE section 5.4), so the steps run again would see
different data; for the illustration they reuse the original values.
Only the fields the record uses are kept: step, loss_ntp, loss_mtp, gradient_norm, lr, tokens_per_second,
train/ce_loss, val/bpb.
"""
import json
from pathlib import Path

SRC = Path("teams/05-architecture/jobs/evidence/2026-11-10-attention-screen/attn-0/metrics.jsonl")
DST = Path("teams/05-architecture/experiments/results/dryrun1_sample_log.jsonl")
KEEP = ("step", "loss_ntp", "loss_mtp", "gradient_norm", "lr", "tokens_per_second", "train/ce_loss", "val/bpb")
LOSS_SPIKES = {300: 2.0, 700: 2.0, 701: 2.0, 702: 2.0}  # attempt 1 only
NAN_STEP = 950  # attempt 2 only
ATTEMPTS = [(0, 702), (651, 950), (901, 1221)]  # (first step, last step) of each attempt; step 0 is the evaluation-only row


def main():
    if not SRC.exists():
        raise SystemExit(f"{SRC} not found: run from the repository root")
    real = {}
    for line in SRC.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            real[r["step"]] = {k: r[k] for k in KEEP if k in r}
    out = []
    for n, (first, last) in enumerate(ATTEMPTS, 1):
        for s in range(first, last + 1):
            r = dict(real[s])
            if n == 1 and s in LOSS_SPIKES:
                r["loss_ntp"] = r["loss_ntp"] * LOSS_SPIKES[s]
            if n == 2 and s == NAN_STEP:
                for k in ("loss_ntp", "loss_mtp", "gradient_norm"):
                    r[k] = float("nan")
                r.pop("val/bpb", None)
            out.append(json.dumps(r, ensure_ascii=False, allow_nan=True))
    DST.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {DST}: {len(out)} rows in {len(ATTEMPTS)} attempts (ILLUSTRATION: injected events, not a real run)")


if __name__ == "__main__":
    main()
