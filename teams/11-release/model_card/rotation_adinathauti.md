# Rotation review: Training infrastructure

Rotation: adinathauti, Team 11 (Release), Week 3.
Section reviewed: Training infrastructure, `model_card_outline.md`.

---

## R1: Claims in the section row

The outline row says: "How the run saves, restores and restarts after a crash."
Owner team: Infrastructure. Status: empty. Lead OK: pending.

Because the section text is empty, this review checks the outline row and its supporting documents.

| Claim | Evidence | On main? |
|---|---|---|
| The run saves checkpoints | `teams/07-infrastructure/docs/checkpoint_design_v0.md` sections 5 and 7 (save protocol and triggers); merged in #418, updated in #510 | Yes |
| The run restores from a checkpoint | `teams/07-infrastructure/docs/runbook.md` sections 3 and 6 (restore steps); merged in #380, updated in #510 | Yes |
| The run restarts after a crash | `teams/07-infrastructure/docs/runbook.md` section 1 (exit codes and actions, crash requeue path); `teams/07-infrastructure/docs/checkpoint_design_v0.md` section 7 (trigger table, exit code contract) | Yes |
| Checkpoint interval set from measured times | `teams/07-infrastructure/docs/checkpoint_interval.md`; merged in #463 | Yes |
| Lead OK for Infrastructure | No public evidence | Not on GitHub |

---

## R2: Claims with no public evidence

- **Lead OK: pending.** The outline row shows `pending`. No public GitHub comment or PR records this confirmation.
- **Section text: empty.** The Infrastructure team has not written the model card text yet. There is no section text to check for unsupported claims.

---

## Notes

The save, restore and restart steps are described in `teams/07-infrastructure/docs/` on main. The outline row scope matches these documents. Once the Infrastructure team writes the section text, the review should check each sentence against those documents and mark any claim that goes beyond them.
