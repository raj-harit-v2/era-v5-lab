# Custom parts of config v1, checked against Team 6 (Performance)

**Status:** draft, 17 Nov 2026. Allocated by Shivanshu (lead), 14 Nov: "Check the reversible recompute and each
custom part of config v1 with Team 6." Due Thu 19 Nov.

**Why this file.** `config_v1.yaml` (signed at Gate 2, 14 Nov) fixes several non-standard architecture and
optimizer pieces. The model that trains the real checkpoint is the reference implementation in
`teams/05-architecture/harness/week2/model.py` ("Reference GQA/RoPE/SwiGLU MoE... No fused kernels, reversible
layers or expert parallelism are claimed"). Team 6 maintains a separate, faster implementation of the same math
(`teams/06-performance/models/`), timed and correctness-checked against a reference through their `PAIRS`
framework (`correctness/framework.py`), with config switches documented in `docs/PARTS.md`. This file checks each
custom part of `config_v1.yaml` against what Team 6's performance harness actually implements and tests today, so
Team 6 knows which path to optimize and where production (week2) and performance (Team 6) code have not yet been
checked against each other.

**Checked against:**
- `teams/05-architecture/configs/config_v1.yaml` (Gate 2, 14 Nov) and `teams/05-architecture/configs/open_choices.json`.
- `teams/05-architecture/harness/week2/model.py` and `train_week2.py` (the actual production training code).
- `teams/06-performance/docs/PARTS.md`, `docs/LINEAR_CE.md`, `models/moe.py`, `models/reversible.py`,
  `correctness/test_reversible.py`, `correctness/test_ke2.py` (read 17 Nov 2026).
- No checkpoint of the config v1 model exists yet (sizes are still `null`); this is a code-level check, the same
  caveat G12's `docs/unsupported_parts.md` part 2 noted for the same reason.

## Summary

| Part | week2 (production) today | Team 6 (performance) today | Gap / open question | Plan |
|---|---|---|---|---|
| KE2 input embedding | own `KE2`/`codec()` in `model.py`, closed-form, G4-compatible by convention | `models/ke2.py` `KE2Embedding`, checked against **Team 4's** reference codec (`test_ke2.py`) | no test pairs week2's `KE2` directly against Team 6's `KE2Embedding` — both claim G4-compatibility independently | **ask Team 6**: add a pair against `week2/model.py::KE2.projected`, not only Team 4's codec |
| Output head (tied vs untied) | `model.py` always builds untied `head` | not config v1's call; serving-side per G12 part 1 §2 | `exp2_adamw.yaml`/`exp2_muon.yaml` `intended.tied_embeddings_intended: true` disagrees with `model.py`'s untied head (also flagged by G12 `unsupported_parts.md` §9.2) | **resolve wording**: the `intended` block is stale/aspirational, not a behavior switch; confirm with lead and fix the arm files or the comment |
| MoE dispatch (16 experts, 1 shared, top-2, router fp32) | its own "execution-only fast path": dense batched `einsum` over every expert, not through any named dispatch | `models/moe.py` registers exactly `DISPATCH = {loop, sorted, grouped}`; "loop is the reference" | week2's dense/batched approach doesn't match any of the three names, so it isn't in Team 6's `PAIRS` correctness suite or `PARTS.md` timings at all | **ask Team 6**: is week2's approach a fourth dispatch strategy, or equivalent to `grouped`? Either name it and add a pair, or confirm Team 6's faster path is validated as a drop-in replacement before anyone swaps it into week2 |
| Optimizer (Muon on 2D matrices, AdamW elsewhere, momentum 0.95 Nesterov, wd 0, router on Muon) | own backend from Deepjyoti Saha's #241 (`optim.name: muon`) | `PARTS.md` lists `optim.name: polar_muon_adamw \| muon \| adamw` and `optim.muon_impl: batched \| loop` | unclear whether #241's backend *is* Team 6's `muon`/`batched` path, or a second, independently-written implementation | **ask Team 6 directly**: confirm whether #241 and their `optim.muon_impl=batched` are the same code path (shared) or parallel implementations that could drift |
| Reversible recompute | **not used.** `week2/config.py` hard-rejects anything but `reversible: false` ("Reversibility unresolved or unsupported; must be explicit false") | **built and correctness-tested.** `models/reversible.py`: `ReversibleStack`/`ReversibleOnePassStack`, `model.rev_impl: two_pass \| one_pass`, `correctness/test_reversible.py` passing (tol 1e-5/5e-5, bf16 property test) | `config_v1.yaml` doesn't mention `model.reversible` at all — no decision was made either way at Gate 2 | **not a Gate 2 blocker.** Team 6's implementation exists and is tested on synthetic shapes (3-layer, 32-dim), not on config v1's real sizes (still `null`). Revisit once model sizes are fixed, if memory pressure at T3+ makes it worth enabling; flag to Team 6/lead as a week-3+ option, not a current gap |
| Cross-entropy over the full 131,072-vocab head | plain full `[tokens, 131072]` fp32 logits via `token_nll`, no chunking (`train_week2.py`) — `PARTS.md` itself calls this bottleneck "**memory (fp32 logits)**" | 7 built implementations (`model.ce_impl`: `torch`/`chunked`/`fused`/`fused_cached`/`fused_liger`/`fused_cce`/`triton_ce`), exactly aimed at this bottleneck (`docs/LINEAR_CE.md`) | Team 6 already solved the problem week2 has, but none of it is wired into `train_week2.py` | **ask Team 6**: which `ce_impl` is validated end-to-end (forward+backward, with the MTP head) against week2's exact `token_nll`, and is it ready to drop into `train_week2.py` once a lead signs off |
| Attention (`attn_impl: eager` for determinism) | `GQA` in `model.py`, eager only, no flag | `model.attn_impl: eager \| sdpa`, "same maths, compared as a different config" per `PARTS.md` | none found | **no action**; Team 6 already tracks this correctly as an implementation-only switch |

## Detail

### 1. KE2 input embedding

`week2/model.py`'s `KE2`/`codec()` is its own implementation: dense reference `codec()` plus a sparse closed-form
`KE2.projected()`, both tested (per the module's own docstring convention) against "the same unbiased-std
convention as G4" — i.e. Team 4's codec, the same target Team 6 checks against in `correctness/test_ke2.py`
("Kronecker Embedding v2 (models/ke2.py) against G4's dense fp64 encoder... The reference shares no code with the
fast embedding_bag path"). So week2's `KE2` and Team 6's `KE2Embedding` are each independently checked against
Team 4's reference, but nothing pairs them **against each other**. Two implementations that both match a third
can still disagree in rounding or edge cases (padding, awkward token lengths) neither test happens to cover.

**Ask:** Team 6 adds a `week2_ke2` pair in `test_ke2.py` (or an equivalent script) against
`week2/model.py::KE2.projected`, using the same edge-case and bf16 cases already in the `ke2.edge`/`ke2.bf16`
pairs.

### 2. Output head: tied vs untied

`model.py` always constructs an untied `head = nn.Linear(n_embd, vocab_size, bias=False)` ("Dense untied output
head per TSAI review" — the docstring). `config_v1.yaml` leaves `embedding.ke2_output_dim: null`, which per
`model.py`'s own behavior means untied. But `teams/05-architecture/configs/arms/exp2_adamw.yaml` and
`exp2_muon.yaml` both set `intended.tied_embeddings_intended: true`. G12's `unsupported_parts.md` §9.2 already
flagged exactly this contradiction on the serving side ("the T1 and T2 arm files say `tied_embeddings_intended:
true`, while `model.py` is untied"). This isn't new, but it is a "custom part" worth closing out here too, since
it affects what Team 6 benchmarks (a tied head changes the embedding-gradient path and the head's memory
footprint).

**Ask:** confirm with the lead whether `tied_embeddings_intended` in the arm files is stale metadata (carried over
from an earlier draft) or an actual pending decision; if stale, fix the comment/field rather than leave two
documents disagreeing.

### 3. MoE dispatch

`config_v1.yaml` fixes 16 routed experts, 1 shared, top-2, router in fp32. `week2/model.py::MoE.forward` computes
this with its own "Execution-only fast path": it stacks every expert's weights into `[E, h, w]` tensors and runs
one batched `einsum` over all experts for every token, then masks to the top-k gates — explicitly commented as
avoiding "data-dependent shapes" and "host synchronisation". Team 6's `models/moe.py` instead registers exactly
three dispatch strategies, `DISPATCH = {"loop", "sorted", "grouped"}` — `loop` is their reference, `sorted` and
`grouped` "pack routes into a padded buffer". None of the three names is week2's dense/batched-over-all-experts
approach. That means week2's actual MoE execution path is outside Team 6's `PAIRS` correctness suite and outside
every row in `PARTS.md`'s bottleneck table — Team 6 has not timed or correctness-checked the thing that will
actually run in production.

**Ask:** does week2's dense `einsum` approach correspond to `grouped` (both avoid a python-level loop per expert),
or is it a fourth, uncatalogued strategy? Either way, Team 6 should register and correctness-test week2's own
approach (or confirm one of the three already matches it bit-for-bit) before claiming any speedup over it.

### 4. Optimizer: Muon

`config_v1.yaml` sets `optim.name: muon`, applied per `exp2_muon.yaml` as `muon_lr` for the 2D matrices (attention,
router, experts), `optim.lr` through AdamW for the embedding, output head and norms, momentum 0.95 Nesterov,
weight decay 0, router on Muon (set in Deepjyoti Saha's #241, the backend week2 actually uses). `PARTS.md` lists
`optim.name: polar_muon_adamw | muon | adamw` and a separate `optim.muon_impl: batched | loop` switch under Team 6.
It isn't clear from the docs whether Team 6's `muon`/`batched` entry **is** #241's backend (i.e. the same module,
imported) or an independent reimplementation written in parallel. If the two have diverged even slightly (e.g. a
different Newton-Schulz iteration count, a different momentum handling), timing numbers from Team 6's harness
would not predict week2's actual step time or convergence.

**Ask Team 6 directly:** is `optim.muon_impl=batched` the same code as #241, or a separate implementation? If
separate, which one does the week2 harness actually call, and has anyone diffed the two numerically?

### 5. Reversible recompute

This is the specific item named in the lead's allocation. `config_v1.yaml` makes **no decision** on
`model.reversible` — it isn't in the Gate 2 settings list at all. `week2/harness/week2/config.py` is stricter than
"undecided": it actively rejects anything other than `False` ("Reversibility unresolved or unsupported; must be
explicit false"), so week2 cannot currently run a reversible stack even if someone wanted to.

Team 6, meanwhile, has a working, tested reversible implementation: `models/reversible.py`'s
`ReversibleStack`/`ReversibleOnePassStack` (midpoint update `p_next = p_prev + 2h·f(p_curr)`, invertible, two
backward strategies via `model.rev_impl: two_pass | one_pass`), with `correctness/test_reversible.py` passing
against plain autograd on fp64 (tolerances 1e-5 grad, and a bf16 property test with reconstruction error < 1e-3 at
9 and 24 layers). `PARTS.md` already has timed regions for it (`bwd.invert`, `bwd.recompute`, `bwd:blockN.grad`).

So the gap isn't that reversible recompute is unsupported — Team 6 built and tested it — it's that **nothing in
config v1 adopts it, and week2's harness is wired to refuse it outright.** Team 6's tests also run on synthetic
shapes (3 layers, 32-dim) rather than config v1's real sizes, which are still `null`.

**This is not a Gate 2 blocker.** Reversible recompute trades compute for activation memory; it only matters once
real model sizes are fixed and only if a deeper configuration (T3 or beyond) hits a memory wall that `model.ce_impl`
and `model.moe.dispatch` choices don't already solve. Recommend recording this as a **known, available option for
week 3+**, not something to force into Gate 2: flag it to the lead and to Team 6 so it's on record, but don't
propose changing `config_v1.yaml` or `week2/config.py`'s current refusal now.

### 6. Cross-entropy over the full 131,072-vocab head

`train_week2.py` computes the training loss as plain `token_nll(logits, ty)` over the full `[tokens, 131072]`
logits tensor the untied head produces — no chunking, no fused kernel. `PARTS.md`'s own bottleneck table calls the
final-head-plus-loss region's bottleneck "**memory (fp32 logits)**", which is exactly what this is. Team 6 has
already built seven alternative implementations for precisely this (`docs/LINEAR_CE.md`: `torch`, `chunked`,
`fused`, `fused_cached`, `fused_liger`, `fused_cce`, `triton_ce`), including a from-scratch Triton kernel that
never materializes the full logits tensor. None of this is used by `train_week2.py` today.

Given the large vocabulary (131,072, driven by tokenizer v0/p1536) and that config v1 keeps the head untied
(dense `[n_embd, vocab_size]`), this is the single clearest place Team 6's performance work could change week2's
actual memory/step-time profile once a lead signs off on swapping it in.

**Ask Team 6:** which `ce_impl` is validated end-to-end (forward **and** backward, including the optional MTP head
and `mtp_weight` combination week2 uses) against week2's exact `token_nll`, and what would it take to wire one in
for a real training run.

### 7. Attention (eager only)

`config_v1.yaml`: `attention.impl: eager`, "Keep the v0 attention... not part of the model", for determinism
across seeds. `model.py::GQA` implements eager attention only, with no alternate kernel. Team 6 tracks
`model.attn_impl: eager | sdpa` correctly in `PARTS.md` as "same maths, compared as a different config" — this is
the one part of config v1 where production and performance code are already aligned with no open question.

## What we need from Team 6, and by when

| From | What | When | Used in |
|---|---|---|---|
| Team 6 | Confirm whether `optim.muon_impl=batched` is #241's backend or a separate implementation | before any Muon timing number is trusted for week2 | §4 |
| Team 6 | Add a correctness pair between `week2/model.py::KE2` and `models/ke2.py::KE2Embedding` (not only each against Team 4's codec) | before KE2 timings are used to justify a week2 change | §1 |
| Team 6 | Confirm whether week2's dense-`einsum` MoE dispatch matches `grouped`, or register it as its own strategy | before any MoE dispatch speedup claim is applied to week2 | §3 |
| Team 6 | Say which `ce_impl` is validated against week2's exact `token_nll` (forward + backward + MTP) | before proposing to wire a fused CE kernel into `train_week2.py` | §6 |
| Lead (Shivanshu) | Resolve `tied_embeddings_intended: true` vs `model.py`'s untied head | before the next arm file is cut from these templates | §2 |
| Lead | Decide whether reversible recompute is worth revisiting once model sizes are fixed | week 3+, not Gate 2 | §5 |

## Not covered here

Serving/export-side custom parts (KE2 folding, Granite MoE Shared export, RoPE pair layout, tokenizer
pre-tokenizer/normalizer) are already documented in G12's `teams/12-quantization/docs/unsupported_parts.md` and
are not duplicated here; this file is scoped to config v1 vs **Team 6's training-performance** code, per the
lead's allocation.
