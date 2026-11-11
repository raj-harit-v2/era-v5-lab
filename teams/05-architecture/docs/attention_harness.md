# Native attention integration

Base: current main checkout 26a52fedb71162ad4890e20e0e4ade50913234cc. No PR241/Muon code is included. Specification: Revant PR274 a6f5939; later group instruction accepts window+sink bundling and not-worse rules. Approval/run gates are unchanged.

Optional arm-owned keys: attn_pattern (one G/L per layer; absent means global), attn_window (1..block_size, only with L), attn_sink (boolean, local layers only), attn_gate (boolean, default false). rotary_fraction supports 1.0 and 0.5; the even rotated dimension is twice floor(fraction*head_dim/2), at least 2. Frequencies use that rotated dimension. Global layer numbering comes from the list, zero-based.

Sink: per-query-head FP32 trainable zero logit, appended to the FP32 softmax denominator with no value vector. A sink of negative infinity uses the exact no-sink path. Local visibility includes the query and W-1 preceding positions. This dense reference mask does not provide sparse-kernel acceleration or an inference cache.

Gate: per-channel width-to-width sigmoid before output projection. With attn_gate=true, attn_gate_input, attn_gate_bias and attn_gate_init must all be explicit. Input is normalized attention input or pre-norm residual; initialization is zero (sigmoid 0.5 initially) or linear_default (PyTorch Linear initialization). Revant confirmed the attn-4 choices: normalized input (same as Q/K/V), bias false, linear_default with no extra initialization call. attn4_gate.yaml now resolves with these values. Alternative options remain implementation options, not additional experiment arms. Gate options affect only the gate-enabled path; disabled paths allocate no new random parameters.

Arm configs are for the native G5 harness, not yet supported by G6's loader. Existing T1/T2/T3 and EXP1 files are unchanged. The four new files use PR274's proposed names; coordinate ownership with Revant before committing duplicate files. attn1/2/3/4 resolve with merged #253 runtime values. None has job/run approval inferred from successful validation. The LR remains inherited 0.001 pending the shared experiment decision, with comparison_final false.

Right-padded, document-isolated windows remain the data contract. No new arbitrary internal padding or packed-document support is claimed. Full-context, full-RoPE, gate-disabled defaults retain the legacy computation and initialization. Training metrics/checkpoint source identity already include the resolved model config and week2 Python sources, so train_week2.py needs no edits.

Before jobs: owner publishes job requests with actual same-script CPU log, artifact/heldout evidence, approved resolution and final common LR. Revalidate combined main after PR241 lands. Not-worse acceptance is documented metadata here; the existing winner-only comparison helper is not silently changed into a not-worse selector. Final attention comparisons must apply the approved rule explicitly.

## PR274 review alignment (4 Nov 2026)

Reviewed the PR body, current file at a6f5939, issue comments, inline comments and both submitted reviews. The lead and TSAI approved the four candidates; TSAI explicitly accepts window+sink as one arm and the not-worse rule for attn-1/2/3. attn-4 retains the winner rule. The PR was still open when checked. No baseline sharing or third-seed owner is inferred from these approvals. Three-seed evaluation remains the plan; assigning who runs the third seed is the lead's decision.

For attn-1/2/3, evaluate each metric independently: three-group mean, code mean, Indic mean. For a metric M, pass when mean_M(candidate)-mean_M(attn0) <= max(range_M(candidate), range_M(attn0)); lower is better. All three must pass. For attn-4 use the plan's improvement/winner rule. acceptance_rule in intended is documentation/provenance, not an executable selector; compare_arms in week2/scoring.py remains winner-only and must not be used to declare these not-worse arms failed. This package changes the model/loader, not the scoring API. No experiment result is included.

The PR names five model keys. This implementation follows them and adds three explicit gate details (input, bias, initialization) because the approved text does not settle those choices. This adds no new attention arm. Revant subsequently resolved all three: normalized, false, linear_default. No gate-definition question remains.
