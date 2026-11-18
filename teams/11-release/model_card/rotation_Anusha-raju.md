# Model card rotation review: Architecture

**Date:** 16 Nov 2026  
**Reviewer team:** Architecture, on rotation to Release  
**Section:** Architecture, in `model_card_outline.md`  
**Evidence read:** #237, #281, #374, #443, #447, #450, #466, `teams/05-architecture/configs/config_v1.yaml`, `teams/05-architecture/decisions.md`, `teams/05-architecture/experiments/results_v1.md`, `teams/05-architecture/jobs/evidence/2026-11-10-attention-screen/README.md`

The Architecture section has no text yet, so this review covers the current outline row and its evidence.
R1 reviews the row. R2 marks each claim that has no evidence.

## R1: review of the Architecture row

The row says: "The shape of the model, in general terms."
The owner team is Architecture, the status is empty and the Lead OK is recorded, with no public source.

### What the evidence supports

Gate 2 (the second lab decision point) signed these choices on 14 Nov 2026.
The Architecture team recorded them in config v1 (#447). TSAI merged #447.
TSAI approved these choices in the Gate 2 update (#443).

- The attention stays the v0 attention, the version from config v0.
- The model is a mixture of experts (MoE): 16 routed experts plus 1 shared expert, top-2.

These choices have approved, public evidence.

### What the evidence does not support yet

- **Model size.** Config v1 leaves the layer count, the width, the head count and the feed-forward size empty.
  The test sizes in the experiments are not the model size.
- **Context length.** Config v1 leaves the sequence length empty.
- **Output head.** Config v1 leaves the KE2 output size empty. TSAI decides the output head.
  The outline puts KE2 in its own row, with no design details.
- **Reasons from results.** No final held-out result for the attention and expert choices is on main.
  #374 records none for them. The attention screen on main is one seed and marked preliminary.
  Job requests #450 and #466 quote later results, but only for comparison, not as results on main.
  So there is evidence that Gate 2 chose them, but no evidence that they scored best.

## R2: claims and evidence

| # | Claim | Evidence | Result |
|---|---|---|---|
| 1 | The owner team is Architecture | The outline in #237, approved by the Release lead | has evidence |
| 2 | The status is empty | No section text exists on main | has evidence |
| 3 | The Architecture lead confirmed the row | #281 added the OK. Neither #281 nor #237 has a public OK comment for this row | no public evidence |
| 4 | The shape of the model is known | #447 sets the attention and the experts. Config v1 leaves the sizes empty | has evidence, in part |
| 5 | The attention is the v0 attention | Config v1 (#447), approved in #443 | has evidence |
| 6 | 16 routed experts plus 1 shared, top-2 | Config v1 (#447), approved in #443 | has evidence |
| 7 | The model size: layers, width, heads and feed-forward size | Empty in config v1 | no evidence. Write `[number: waiting for TSAI]` |
| 8 | The context length | Empty in config v1 | no evidence |
| 9 | The output head | Empty in config v1. TSAI decides the output head | no evidence |
| 10 | Claims 5 and 6 rest on test results | #374 records no result for the attention or expert choices. The attention screen on main is one seed and marked preliminary. #450 and #466 quote later results only for comparison | no evidence. Only the Gate 2 decision supports them |
