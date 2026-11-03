"""MFU task: MFU/HFU method, run-level scope and the G6 -> G8 contract.  CPU only.

Method and field names are in docs/METRICS.md section 2.

How to read this file
---------------------
* Tests tagged "[GUARD]" pin behaviour that g6/dev already has. They must keep passing: they stop the MFU task
  change from silently moving numbers G8 already ingested.
* Tests tagged "[NEW]" pin the MFU task behaviour. Their expected values are worked out by hand in the comments, never read back from the
  function under test. The method itself is still a proposal until both leads approve it.
* Proposed names used here (change them together with the implementation if the leads decide differently):
    perfkit.metrics.mfu_run(flops, global_tokens_per_s, peaks_tflops, ranks=None)
    perfkit.metrics.flops_per_token(..., method="g6-v1" | "g6-v2", ke2_mean_support_len=None)
    new unavailable-reason codes: participants_unavailable, participant_peak_unavailable,
                                  invalid_global_throughput, duplicate_participants
    new run["metrics"] fields: mfu_method, mfu_scope ("selected_gpu" | "run"), participants, global_tokens_per_s

Terms: FLOP = one add or multiply; a matmul of (m x k) by (k x n) is 2*m*k*n FLOP. MFU = model FLOP/s divided
by the hardware's peak FLOP/s. HFU also counts extra work the hardware really did (recompute, optimizer).

Run:  python -m pytest correctness/test_mfu_method.py -q     (from teams/06-performance)
"""
import math
from types import SimpleNamespace

import pytest
import torch
from torch.utils.flop_counter import FlopCounterMode

from models.config import ModelConfig
from models.gpt import GPT
from perfkit import metrics
from perfkit.metrics import flops_per_token, mfu, peak_tflops, peak_unavailable_reason
from perfkit.schema import METRIC_UNAVAILABLE_REASONS, example_run, validate_run

# ---------------------------------------------------------------------------------------------- fixtures
# One hand-sized model used by the ledger tests. Every number below is worked out on paper:
#   V=16 vocab, d=8 width, L=1 layer, 2 heads, MLP hidden h = 4*d = 32, GELU, tied head, block_size 8.
V, D, L, H = 16, 8, 1, 32
ATTN_W = 3 * D * D + D * D            # c_attn (q, k, v) + c_proj weights = 192 + 64 = 256
MLP_W = 2 * D * H                      # c_fc + c_proj = 2 * 8 * 32 = 512
HEAD_W = V * D                         # LM head matmul (tied to the table, but the matmul still runs) = 128
ACTIVE = HEAD_W + L * (ATTN_W + MLP_W)  # 128 + 768 = 896 matmul weights one token passes through
assert ACTIVE == 896


def _attn_flops(T):
    """12 * L * d * T: attention scores + weighted values, forward + backward, non-causal (PaLM / our convention)."""
    return 12 * L * D * T


def _tiny(**kw):
    cfg = dict(vocab_size=V, block_size=8, n_layer=L, n_head=2, n_embd=D)
    cfg.update(kw)
    return GPT(ModelConfig(**cfg))


def _tiny_ke2(ke_max_pos=2, **kw):
    """A real GPT with a real KE2Embedding. GPT takes token_bytes, so G4's 131072-token table is not needed: here
    the bytes are (token id, 0) and every token has length 1 or 2. D = 256 * P = 512, so the projection has 8 * 512
    = 4096 weights. Active = head 128 + projection 4096 + attention and MLP 768 = 4992."""
    tb = torch.stack([torch.arange(V), torch.zeros(V, dtype=torch.long)], dim=1).to(torch.uint8)
    lens = torch.tensor([1, 2] * (V // 2))
    return GPT(ModelConfig(vocab_size=V, block_size=8, n_layer=L, n_head=2, n_embd=D, embedding="ke2",
                           ke_max_pos=ke_max_pos, **kw), token_bytes=(tb, lens))


def _run_level():
    """Fetch mfu_run lazily so that, before the implementation exists, each [NEW] test fails on its own
    (AttributeError) instead of the whole file failing to import."""
    return metrics.mfu_run


FLOPS = {"model_flops_per_token": 2e8, "hw_flops_per_token": 3e8}   # round numbers for the run-level algebra


# =================================================================================================== C1
# Why: MFU is only as good as its FLOP count. This test writes the count out per matrix, from the model's
# shapes, so it does not repeat the code's own formula. If someone changes what param_counts() includes, this
# fails. Value to us: a wrong count shifts every MFU number G8 charts.

def test_c1_hand_counted_ledger_model_and_hardware_flops():   # [GUARD]
    T = 4
    model = _tiny()
    out = flops_per_token(model, T)
    # model FLOP/token = 6 per active weight (2 forward + 4 backward) + attention term
    #   6 * 896 + 12*1*8*4 = 5376 + 384 = 5760
    assert out["params_active"] == 896
    assert out["model_flops_per_token"] == 6 * ACTIVE + _attn_flops(T) == 5760
    # no recompute, no optimizer => hardware FLOPs equal model FLOPs
    assert out["hw_flops_per_token"] == 5760


@pytest.mark.parametrize(
    ("overrides", "extra_hw"),
    [
        # one stack forward = 2*(active - head - ke) + 4*L*d*T = 2*768 + 4*8*4 = 1536 + 128 = 1664
        ({"reversible": True, "rev_impl": "two_pass"}, 2 * 1664),   # invert + recompute = 2 extra stack forwards
        ({"reversible": True, "rev_impl": "one_pass"}, 1 * 1664),   # one_pass reuses the inversion: 1 extra forward
        ({"ce_impl": "chunked"}, 2 * HEAD_W),                        # chunked CE recomputes the head matmul: 2*128
        ({"ce_impl": "fused_cce"}, 2 * HEAD_W),                      # same for the fused_cce path
        ({"ce_impl": "fused"}, 0),                                   # caches gradients in forward: no recompute
        ({"ce_impl": "fused_cached"}, 0),                            # same, with fixed token tiles
        ({"ce_impl": "fused_liger"}, 0),                             # same
    ],
)
def test_c1_hardware_flops_add_only_the_recompute_that_really_runs(overrides, extra_hw):   # [GUARD]
    # Why: HFU = MFU numerator + the extra work. Each row says which feature adds which literal amount.
    # A wrong sign or a missing branch (e.g. forgetting rev_impl) would make HFU lie about wasted work.
    out = flops_per_token(_tiny(**overrides), 4)
    assert out["model_flops_per_token"] == 5760
    assert out["hw_flops_per_token"] == 5760 + extra_hw


def test_c1_swiglu_counts_three_ffn_matrices():   # [GUARD]
    # Why: #39 merged SwiGLU. Gate, up and down are 3 matrices: 3 * 8 * 32 = 768, not 2 * 8 * 32 = 512.
    # active = 128 + 256 + 768 = 1152 ; FLOPs = 6 * 1152 + 384 = 7296
    out = flops_per_token(_tiny(activation="swiglu"), 4)
    assert out["params_active"] == 1152
    assert out["model_flops_per_token"] == 7296


def test_c1_moe_counts_router_and_only_the_active_experts_at_their_own_width():   # [GUARD]
    # Why: #41 and #42 merged grouped dispatch and model.moe.ffn_hidden. Compute follows the experts one token uses.
    # router 8 * 4 = 32 ; one expert 2 * 8 * 16 = 256 ; top_k 1 + shared 1 = 2 experts = 512
    # active = 128 + 256 + 32 + 512 = 928 ; FLOPs = 6 * 928 + 384 = 5952
    moe = dict(num_experts=4, top_k=1, num_shared=1, bias_gamma=0.01, dispatch="loop", ffn_hidden=16)
    out = flops_per_token(_tiny(ffn="moe", moe=moe), 4)
    assert out["params_active"] == 928
    assert out["model_flops_per_token"] == 5952


# =================================================================================================== C2
# Why: with mtp=true there is a second head. It runs on T-1 positions (the last position has no t+2 target).
# The current code counts it on all T positions, so it over-counts by 1/T of the MTP head's work. The
# independent oracle below (PyTorch's own FLOP counter) shows the over-count is exactly that.

@pytest.mark.parametrize("T", [2, 4, 8])
def test_c2_mtp_head_counts_t_minus_1_positions_v2(T):   # [NEW]
    # base (no MTP) per token = 6*896 + 12*8*T ; MTP head adds 6 * 128 * (T-1)/T per input token
    base = 6 * ACTIVE + _attn_flops(T)
    expected = base + 6 * HEAD_W * (T - 1) / T
    out = flops_per_token(_tiny(mtp=True), T, method="g6-v2")
    assert out["model_flops_per_token"] == pytest.approx(expected)


def test_c2_mtp_v1_keeps_counting_all_positions():   # [GUARD]
    # Why: the legacy method must stay as documented so already-ingested baselines can be reproduced.
    T = 4
    out = flops_per_token(_tiny(mtp=True), T)      # today's call, no `method` argument
    assert out["model_flops_per_token"] == 6 * (ACTIVE + HEAD_W) + _attn_flops(T) == 6528


# =================================================================================================== C3
# Why: G8's handoff doc says the KE2 projection (256 x 8192 in the real model) is counted as a dense matmul, but
# KE2 really runs as an embedding_bag over a handful of columns, so MFU reads ~5% high. Proposal D1: take the
# projection out of 6N and add the small real lookup cost.
# HAND DERIVATION to confirm with G4/G6 before approving: per token, the forward sums L_support columns of
# length d (2*L*d FLOP: multiply by the per-sample weight and add) and the backward scatters gradients into
# the same columns (another 2*L*d). That is 4 FLOP per support cell per output channel.
# NOT in that term (open point in the guide, D1): the row sum low[L] * W.sum(1) in models/ke2.py. By hand it is
# about 2*D*d/(B*T) + 4*d FLOP per token, 2,048 at base.yaml, or about 0.001% of the model FLOPs.

KE2_FLOPS_PER_SUPPORT_CELL_PER_CHANNEL = 4


def test_c3_ke2_v1_charges_the_projection_as_a_dense_matmul():   # [GUARD]
    # legacy: 6 * 4992 + 384 = 29952 + 384 = 30336
    out = flops_per_token(_tiny_ke2(), 4)
    assert out["params_active"] == 4992
    assert out["model_flops_per_token"] == 30336


def test_c3_ke2_v2_replaces_projection_matmul_with_lookup_cost():   # [NEW]
    model = _tiny_ke2()
    T, Lbar = 4, 5.0                              # Lbar = mean number of support columns per token
    ke_w = 8 * 512
    v1 = flops_per_token(model, T)["model_flops_per_token"]
    v2 = flops_per_token(model, T, method="g6-v2", ke2_mean_support_len=Lbar)["model_flops_per_token"]
    # new: remove 6*4096 = 24576, add 4 * 5 * 8 = 160  =>  30336 - 24576 + 160 = 5920
    assert v2 == v1 - 6 * ke_w + KE2_FLOPS_PER_SUPPORT_CELL_PER_CHANNEL * Lbar * 8 == 5920


def test_c3_ke2_v2_without_a_support_length_is_an_error():   # [NEW]
    # Why: a silent default would make every KE2 MFU depend on a number nobody chose.
    with pytest.raises(ValueError):
        flops_per_token(_tiny_ke2(), 4, method="g6-v2")


def test_c3_ke2_v2_does_not_change_raw_parameter_counts():   # [NEW]
    # Why: the convention changes the FLOP ledger, not the model. G8 reads params_total / params_active.
    model = _tiny_ke2()
    a = flops_per_token(model, 4)
    b = flops_per_token(model, 4, method="g6-v2", ke2_mean_support_len=5.0)
    assert (a["params_total"], a["params_active"]) == (b["params_total"], b["params_active"])


def test_c3_v2_changes_only_model_flops_recompute_terms_are_untouched():   # [NEW]
    # Why: the HFU "extra work" terms (reversible, head recompute) must not drift when KE2/MTP accounting does.
    model = _tiny(reversible=True, ce_impl="chunked")
    v1 = flops_per_token(model, 4, method="g6-v1")
    v2 = flops_per_token(model, 4, method="g6-v2")
    assert v2["hw_flops_per_token"] - v2["model_flops_per_token"] == v1["hw_flops_per_token"] - v1["model_flops_per_token"]


# =================================================================================================== C4
# Why: G8 has ingested eight baseline files and the docs quote a worked example (A100, 247 MFLOP/token,
# 95,459 tokens/s -> 23.6 TFLOPS, MFU 7.6%, HFU 8.4%). If our change shifts those numbers silently, the
# charts and the handoff doc become wrong. These are the "nothing moved" guards.

def test_c4_documented_a100_worked_example_still_reproduces():   # [GUARD]
    # docs/METRICS.md section 2: model 247 MFLOP, hardware 276 MFLOP per token.
    out = mfu({"model_flops_per_token": 247e6, "hw_flops_per_token": 276e6}, 95_459, 312)
    assert out["model_tflops_per_s"] == pytest.approx(23.58, abs=0.01)   # 247e6 * 95459 / 1e12
    assert round(out["mfu"], 3) == 0.076
    assert round(out["hfu"], 3) == 0.084


def test_c4_documented_a100_mtp_example_still_reproduces():   # [GUARD]
    # docs/METRICS.md section 2, model.mtp=true: 448 / 477 MFLOP per token, 59,691 tokens/s -> 8.6% / 9.1%.
    out = mfu({"model_flops_per_token": 448e6, "hw_flops_per_token": 477e6}, 59_691, 312)
    assert round(out["mfu"], 3) == 0.086
    assert round(out["hfu"], 3) == 0.091


def test_c4_default_method_equals_explicit_legacy_method():   # [NEW]
    # Why: until both leads approve g6-v2, the default must stay g6-v1, so calling without `method` is unchanged.
    # Approval does not switch anything by itself. Moving to g6-v2 means changing metrics.DEFAULT_METHOD, having bench
    # pass ke2_mean_support_len, and updating this test and test_c14_bench_writes_the_method_and_scope.
    # Old run files keep their numbers: a file with no mfu_method counts as g6-v1.
    for kw in ({}, {"mtp": True}, {"reversible": True}, {"ce_impl": "chunked"}):
        m = _tiny(**kw)
        assert flops_per_token(m, 4) == flops_per_token(m, 4, method="g6-v1")


# =================================================================================================== C5
# Why: this is the G6/G8 scope question ("world_size * peak_tflops in the denominator") turned into a test.
# If k identical GPUs each do the same work, run-level utilization must equal the single-GPU utilization.
# A bench that divided local throughput by k * peak would report 1/k of this.

@pytest.mark.parametrize("k", [1, 2, 4, 8])
def test_c5_k_identical_gpus_give_the_single_gpu_utilization(k):   # [NEW]
    per_gpu_tps, peak = 95_459.0, 312.0
    one = mfu(FLOPS, per_gpu_tps, peak)
    run = _run_level()(FLOPS, k * per_gpu_tps, [peak] * k)
    assert run["mfu"] == pytest.approx(one["mfu"])
    assert run["hfu"] == pytest.approx(one["hfu"])
    assert run["model_tflops_per_s"] == pytest.approx(k * one["model_tflops_per_s"])   # total FLOP/s scales with k


def test_c5_run_level_hand_value():   # [NEW]
    # 2e8 FLOP/token * 190,000 tok/s = 3.8e13 FLOP/s ; denominator 2 * 312e12 = 6.24e14 ; ratio = 0.060897...
    out = _run_level()(FLOPS, 190_000.0, [312.0, 312.0])
    assert out["mfu"] == pytest.approx(3.8e13 / 6.24e14)
    assert out["hfu"] == pytest.approx(5.7e13 / 6.24e14)         # 3e8 * 190000 = 5.7e13


# =================================================================================================== C6
# Why: every other test here checks our reasoning against our reasoning. This one asks PyTorch itself to count
# the FLOPs of a real forward+backward pass (torch.utils.flop_counter), which is independent evidence. With
# eager attention (explicit matmuls) the counter must equal our model FLOPs exactly: 46,080 for B*T=8 tokens
# at T=4. (With SDPA the counter counts attention differently, so we do not compare that path.)
# The counter sees matmuls only, not embedding_bag or elementwise ops. That is what makes the KE2 test useful.

def _counted_flops(model, B, T):
    x = torch.randint(0, V, (B, T))
    y = torch.randint(0, V, (B, T))
    with FlopCounterMode(display=False) as fc:
        _, loss = model(x, y)
        loss.backward()
    return fc.get_total_flops()


def test_c6_flop_counter_agrees_with_analytic_count_for_plain_model():   # [GUARD]
    B, T = 2, 4
    model = _tiny(attn_impl="eager")
    analytic = flops_per_token(model, T)["model_flops_per_token"] * B * T
    assert analytic == 5760 * 8
    assert _counted_flops(model, B, T) == analytic


def test_c6_flop_counter_shows_the_mtp_over_count_and_v2_fixes_it():   # [NEW]
    B, T = 2, 4
    model = _tiny(attn_impl="eager", mtp=True)
    counted = _counted_flops(model, B, T)
    # the MTP head runs on B*(T-1) positions, not B*T: counted = 50,688 (legacy method says 52,224)
    v1 = flops_per_token(model, T)["model_flops_per_token"] * B * T
    assert v1 - counted == 6 * HEAD_W * B          # over-count = 6 * 128 * (one missing position per sequence) = 1536
    v2 = flops_per_token(model, T, method="g6-v2")["model_flops_per_token"] * B * T
    assert v2 == pytest.approx(counted)


def test_c6_flop_counter_sees_no_dense_matmul_for_the_ke2_projection():   # [NEW]
    # Why: independent evidence for D1. The counter finds the same 46,080 FLOPs as the plain model (5760 per token
    # * 8 tokens), so the real KE2 path runs no dense projection matmul. Legacy charges it 6 * 4096 per token.
    B, T, Lbar = 2, 4, 1.5                         # _tiny_ke2 lengths alternate 1 and 2
    model = _tiny_ke2(attn_impl="eager")
    counted = _counted_flops(model, B, T)
    assert counted == 5760 * B * T == 46080
    assert flops_per_token(model, T)["model_flops_per_token"] * B * T - counted == 6 * 4096 * B * T
    v2 = flops_per_token(model, T, method="g6-v2", ke2_mean_support_len=Lbar)["model_flops_per_token"] * B * T
    assert v2 - counted == 4 * Lbar * 8 * B * T    # only the lookup cost, which the counter cannot see


# =================================================================================================== C7
# Why: if the GPUs differ (an A100 and an H100 in one job), capacity is the SUM of the individual peaks, not
# world_size times one of them. Using 2 x 312 for an A100+H100 pair would overstate utilization by a lot.

def test_c7_heterogeneous_peaks_are_summed():   # [NEW]
    # 2e8 * 100,000 = 2e13 FLOP/s ; capacity (312 + 989) TFLOPS = 1.301e15 ; ratio = 0.015373...
    out = _run_level()(FLOPS, 100_000.0, [312.0, 989.0])
    assert out["mfu"] == pytest.approx(2e13 / 1.301e15)
    assert out["mfu"] != pytest.approx(2e13 / (2 * 312e12))      # not world_size * first peak
    assert out["mfu"] != pytest.approx(2e13 / (2 * 989e12))      # not world_size * last peak


# =================================================================================================== C8
# Why: G8 treats `null` + a reason code as "missing", but 0 as a real (terrible) measurement. Any bad input
# must produce null with the right reason, never 0, never a clipped value, never an exception.

@pytest.mark.parametrize(
    ("peaks", "tps", "reason"),
    [
        ([], 1e5, "participants_unavailable"),                      # nobody took part
        ([312.0, None], 1e5, "participant_peak_unavailable"),       # one GPU has no known peak
        ([312.0, float("nan")], 1e5, "participant_peak_unavailable"),
        ([312.0, 0.0], 1e5, "participant_peak_unavailable"),
        ([312.0, -1.0], 1e5, "participant_peak_unavailable"),
        ([312.0, float("inf")], 1e5, "participant_peak_unavailable"),
        ([312.0], float("nan"), "invalid_global_throughput"),
        ([312.0], 0.0, "invalid_global_throughput"),
        ([312.0], -5.0, "invalid_global_throughput"),
        ([312.0], None, "invalid_global_throughput"),
    ],
)
def test_c8_bad_inputs_give_null_with_reason_not_zero(peaks, tps, reason):   # [NEW]
    out = _run_level()(FLOPS, tps, peaks)
    assert out["mfu"] is None and out["hfu"] is None
    assert out["mfu_unavailable_reason"] == reason
    assert out["hfu_unavailable_reason"] == reason
    assert reason in METRIC_UNAVAILABLE_REASONS


def test_c8_missing_hw_flops_keeps_mfu_but_not_hfu():   # [NEW]
    # Why: same rule as the single-GPU path (test_metrics.py): HFU can be unknown while MFU is fine.
    out = _run_level()({"model_flops_per_token": 2e8, "hw_flops_per_token": None}, 1e5, [312.0])
    assert out["mfu"] == pytest.approx(2e8 * 1e5 / 312e12)
    assert out["hfu"] is None and out["hfu_unavailable_reason"] == "hw_flops_unavailable"


def test_c8_mfu_above_one_is_not_clipped():   # [NEW]
    # Why: >1 means a wrong peak or an over-counted FLOP ledger. Clipping to 1 would hide the bug.
    out = _run_level()({"model_flops_per_token": 1e12, "hw_flops_per_token": 1e12}, 1e6, [1.0])
    assert out["mfu"] > 1.0 and out["mfu"] == pytest.approx(1e18 / 1e12)


# =================================================================================================== C9
# Why: a machine can show 8 GPUs while the job uses 1 (idle or telemetry-only GPUs). The participants list is
# the only input; if the code consulted torch.cuda.device_count() the answer would change with the machine.

def test_c9_result_does_not_depend_on_visible_gpu_count(monkeypatch):   # [NEW]
    baseline = _run_level()(FLOPS, 95_459.0, [312.0])

    def boom(*a, **k):
        raise AssertionError("mfu_run must not look at torch.cuda.device_count()")

    monkeypatch.setattr(torch.cuda, "device_count", boom)
    assert _run_level()(FLOPS, 95_459.0, [312.0]) == baseline


# =================================================================================================== C10
# Why: if the same rank is reported twice (a logging bug, or a retry), its tokens and peak would be added twice.
# Throughput would double with the peak, so the ratio would look right while the totals are wrong. Reject it.

def test_c10_duplicate_ranks_are_rejected():   # [NEW]
    out = _run_level()(FLOPS, 190_000.0, [312.0, 312.0], ranks=[0, 0])
    assert out["mfu"] is None
    assert out["mfu_unavailable_reason"] == "duplicate_participants"
    assert "duplicate_participants" in METRIC_UNAVAILABLE_REASONS


def test_c10_distinct_ranks_are_accepted():   # [NEW]
    out = _run_level()(FLOPS, 190_000.0, [312.0, 312.0], ranks=[0, 1])
    assert out["mfu"] == pytest.approx(3.8e13 / 6.24e14)


# =================================================================================================== C11
# Why: G8's ingester reads the run JSON. New fields must be additive (old files still validate) and the schema
# must keep rejecting inconsistent null/reason combinations, or G8 would see "missing" without a cause.

def test_c11_legacy_run_without_new_fields_still_validates():   # [GUARD]
    assert validate_run(example_run()) == []


def test_c11_unknown_reason_code_is_still_rejected():   # [GUARD]
    run = example_run()
    run["metrics"]["mfu"], run["metrics"]["mfu_unavailable_reason"] = None, "made_up_reason"
    assert validate_run(run) != []


def test_c11_null_without_reason_is_still_rejected():   # [GUARD]
    run = example_run()
    run["metrics"]["mfu"], run["metrics"]["mfu_unavailable_reason"] = None, None
    assert validate_run(run) != []


@pytest.mark.parametrize("code", ["participants_unavailable", "participant_peak_unavailable",
                                  "invalid_global_throughput", "duplicate_participants"])
def test_c11_new_reason_codes_are_registered(code):   # [NEW]
    assert code in METRIC_UNAVAILABLE_REASONS
    run = example_run()
    run["metrics"].update(mfu=None, hfu=None, mfu_unavailable_reason=code, hfu_unavailable_reason=code)
    assert validate_run(run) == []


def test_c11_run_scope_block_validates_and_bad_scope_is_rejected():   # [NEW]
    run = example_run()
    run["metrics"].update(
        mfu_method="g6-v2", mfu_scope="run", global_tokens_per_s=190_000.0,
        participants={"world_size": 2, "peak_tflops_sum": 624.0,
                      "devices": [{"name": "NVIDIA A100-SXM4-80GB", "peak_tflops": 312.0}] * 2,
                      "topology": {"dp": 2, "tp": 1, "pp": 1, "ep": 1}})
    assert validate_run(run) == []
    run["metrics"]["mfu_scope"] = "galaxy"
    assert validate_run(run) != []


def test_c11_run_scope_without_participants_is_rejected():   # [NEW]
    # Why: a "run" level number with no list of who took part cannot be audited by G8.
    run = example_run()
    run["metrics"].update(mfu_method="g6-v2", mfu_scope="run", global_tokens_per_s=190_000.0)
    assert validate_run(run) != []


# =================================================================================================== C12
# Why: the peak is the denominator. The names below are what the NVIDIA driver / PyTorch really report. A wrong
# table row is a silent error: H100 PCIe (756) vs H100 SXM (989) is a ~30% shift in every MFU on that card.

@pytest.mark.parametrize(
    ("name", "dtype", "peak"),
    [
        ("NVIDIA A100-SXM4-80GB", "bf16", 312),
        ("NVIDIA A100 80GB PCIe", "bf16", 312),
        ("NVIDIA H100 80GB HBM3", "bf16", 989),     # SXM board
        ("NVIDIA H100 PCIe", "bf16", 756),          # PCIe board is slower than SXM
        ("NVIDIA H200", "bf16", 989),
    ],
)
def test_c12_driver_device_names_map_to_the_intended_peak(name, dtype, peak):   # [GUARD]
    assert peak_tflops(name, dtype)[0] == peak


def test_c12_rtx_5070_ti_has_no_table_peak_so_mfu_needs_an_override():   # [GUARD]
    # Why: documents that local MFU on this machine is null/unknown_gpu unless --peak-tflops is given.
    assert peak_tflops("NVIDIA GeForce RTX 5070 Ti", "bf16") == (None, None)
    assert peak_unavailable_reason("NVIDIA GeForce RTX 5070 Ti", "bf16") == "unknown_gpu"
    assert peak_unavailable_reason("NVIDIA GeForce RTX 5070 Ti", "bf16", 123.0) is None   # override accepted
    assert math.isfinite(mfu({"model_flops_per_token": 1e8, "hw_flops_per_token": 1e8}, 1e5, 123.0)["mfu"])


# =================================================================================================== C13
# Why: #49 merged RoPE (model.position=rope). It removes the position table and adds an elementwise rotation of q
# and k. The rotation is not a matmul, and MFU does not count elementwise work (the same as GELU and SiLU * up), so
# switching to RoPE must not move MFU. perfkit/roofline.py does count the rotation, because it models real cost.

def _rope(**kw):
    return _tiny(position="rope", rope_theta=10000.0, **kw)


def test_c13_rope_leaves_the_flop_count_unchanged():   # [GUARD]
    assert flops_per_token(_rope(), 4)["model_flops_per_token"] == 5760
    assert flops_per_token(_rope(), 4)["params_active"] == 896


def test_c13_rope_removes_only_the_position_table_from_total_parameters():   # [GUARD]
    # block_size * d = 8 * 8 = 64 weights. Lookup tables were never in N, so params_active does not move.
    assert _tiny().param_counts()[0] - _rope().param_counts()[0] == 64


def test_c13_flop_counter_agrees_with_analytic_count_for_rope():   # [GUARD]
    # The counter ignores the elementwise rotation, so it cannot show the rotation's size; it shows nothing else moved.
    B, T = 2, 4
    assert _counted_flops(_rope(attn_impl="eager"), B, T) == 5760 * B * T


def test_c13_rope_v1_and_v2_agree():   # [NEW]
    # no KE2 and no MTP here, so the method id must make no difference
    assert flops_per_token(_rope(), 4, method="g6-v2") == flops_per_token(_rope(), 4, method="g6-v1")


# =================================================================================================== C14
# Why: the fields and checks that carry the method into the run JSON and the report, where G8 and readers see them.

def test_c14_bench_writes_the_method_and_scope():   # [NEW]
    from perfkit.bench import compute_metrics
    s = SimpleNamespace(core=_tiny(), loader=SimpleNamespace(B=2, T=4), opt=SimpleNamespace(flops=lambda: 0.0))
    out = compute_metrics(s, 10.0, 312.0)
    assert out["mfu_method"] == "g6-v1" and out["mfu_scope"] == "selected_gpu"


def test_c14_schema_rejects_an_unknown_method():   # [NEW]
    run = example_run()
    run["metrics"]["mfu_method"] = "made-up"
    assert validate_run(run) != []


def test_c14_compute_metrics_still_gives_the_selected_gpu_numbers():   # [GUARD]
    # 8 tokens in 10 ms = 800 tokens/s ; 5760 * 800 / 312e12
    from perfkit.bench import compute_metrics
    s = SimpleNamespace(core=_tiny(), loader=SimpleNamespace(B=2, T=4), opt=SimpleNamespace(flops=lambda: 0.0))
    out = compute_metrics(s, 10.0, 312.0)
    assert out["tokens_per_s"] == pytest.approx(800.0)
    assert out["mfu"] == pytest.approx(5760 * 800 / 312e12)


def test_c14_report_warns_when_utilization_is_above_one():   # [NEW]
    # Why: MFU above 1 is kept as it is (test_c8), so the report has to point at it.
    from perfkit.report import _utilization_warnings
    assert _utilization_warnings({"mfu": 0.5, "hfu": None}) == []
    warned = _utilization_warnings({"mfu": 1.2, "hfu": 1.5})
    assert len(warned) == 2 and "MFU is 120.0%" in warned[0] and "HFU is 150.0%" in warned[1]


# =================================================================================================== C15
# Why: docs/METRICS.md quotes these g6-v2 numbers. Recomputed here from the same rounded inputs so the doc cannot drift.
# KE2 at base.yaml: 6 * 256 * 8192 = 12,582,912 FLOP out, 4 * L * 256 in, with L = 6.585 (mean bytes over the vocabulary).

def test_c15_metrics_doc_g6_v2_worked_examples():   # [NEW]
    ke_out, ke_in = 6 * 256 * 8192, 4 * 6.585 * 256
    normal, normal_hw = 247e6 - ke_out + ke_in, 276e6 - ke_out + ke_in
    out = mfu({"model_flops_per_token": normal, "hw_flops_per_token": normal_hw}, 95_459, 312)
    assert round(normal / 1e6, 1) == 234.4 and round(out["mfu"], 3) == 0.072 and round(out["hfu"], 3) == 0.081
    mtp_out = 6 * 131072 * 256 / 256                 # the MTP head on T-1 of T = 256 positions
    mtp, mtp_hw = 448e6 - ke_out + ke_in - mtp_out, 477e6 - ke_out + ke_in - mtp_out
    out = mfu({"model_flops_per_token": mtp, "hw_flops_per_token": mtp_hw}, 59_691, 312)
    assert round(mtp / 1e6, 1) == 434.6 and round(out["mfu"], 3) == 0.083 and round(out["hfu"], 3) == 0.089


def test_c15_metrics_doc_run_level_example():   # [NEW]
    run = _run_level()({"model_flops_per_token": 247e6, "hw_flops_per_token": 276e6}, 190_918.0, [312.0, 312.0])
    assert round(run["mfu"], 3) == 0.076 and round(run["hfu"], 3) == 0.084


# =================================================================================================== C16
# Why: the multi-GPU fixture is what a Modal or TSAI run would execute, so its single-process path must keep working.

def test_c16_fixture_one_process_agrees_with_the_selected_gpu_formula(tmp_path, monkeypatch):   # [GUARD]
    import json
    from pathlib import Path
    from perfkit import mfu_fixture
    monkeypatch.delenv("WORLD_SIZE", raising=False)
    cfg = Path(mfu_fixture.ROOT) / "configs" / "tiny_cpu.yaml"
    out = tmp_path / "out.json"
    assert mfu_fixture.main(["--config", str(cfg), "--steps", "2", "--warmup", "0", "--dtype", "fp32",
                             "--peak-tflops", "1", "--out", str(out)]) == 0
    res = json.loads(out.read_text())
    assert res["world_size"] == 1 and res["mfu_scope"] == "run" and res["peak_source"] == "override"
    assert res["run"]["mfu"] == pytest.approx(res["per_rank_mfu"][0])
    assert 1 <= res["mean_support_len"] <= 32        # tiny_cpu.yaml keeps P = 32 byte slots
    assert res["flops_g6_v2"]["model_flops_per_token"] < res["flops_g6_v1"]["model_flops_per_token"]
