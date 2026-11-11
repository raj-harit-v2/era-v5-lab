# Team 07 architecture decision records

**Not technical, or new to the team? Read the [team briefing](../TEAM_BRIEFING.md) first**: every decision, why we
made it, and what we rejected, in plain words.

One ADR per decision area. Each records the context, the options we weighed, the choice, and what it costs us.
Every decision has an **"In simple words"** box, so anyone in the lab can follow it without the jargon.
Status moves **Proposed → Accepted** once the lead (sureshmantha) approves the PR. Later changes go in a new ADR
that supersedes the old one; accepted ADRs are not rewritten.

| ADR | Title | Status | Code |
|---|---|---|---|
| [0001](0001-checkpoint-format-and-commit.md) | Checkpoint format, commit protocol and restore checks | Proposed | `ckpt/`, `support/simulation/trainer/`, [checkpoint_design_v0.md](../docs/checkpoint_design_v0.md) |
| [0002](0002-job-queue-slurm.md) | Job queue on self-managed Slurm on cloud GPU nodes, validated in Docker Slurm: image, storage, access, events, goodput | Proposed | `slurm/`, `support/simulation/slurm-docker/`, `support/simulation/` |
| [0003](0003-node-health-checks.md) | Node health checks and hang policy | Proposed | `health/` |
| [0004](0004-cost-model-and-alerting.md) | Cost model, purchase options and severity-tiered alerting | Proposed | `support/cost/`, `metrics/`, [metrics_catalog.md](../support/docs/metrics_catalog.md) |

Template: Context · Decision drivers · Options considered · Decision · **Metrics** (LOW / MEDIUM / HIGH thresholds
in `metrics/catalog.yaml`) · Consequences · Validation · Open points.

Shared across all four:

- exit codes 0 / 75 / 78 (ADR 0001 §6; the health CLI uses its own 0/3/4);
- the event schema and UTC time (ADR 0002 §8, `common/events.py`);
- goodput buckets and incident records (ADR 0002 §9, `metrics/evaluate.py`);
- severity tiers HIGH (page now) / MEDIUM (today) / LOW (weekly) (ADR 0004 §4).

Simulation evidence: [sim_results.md](../support/docs/sim_results.md). Review of gaps and their status:
[review_week1.md](../support/docs/review_week1.md).
