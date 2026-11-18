# MoE trust-region note for the lead: the objective_v1 mask fires from numerics on an MoE (E3), 15 Nov 2026

**Surrogate evidence, one seed.** Public OLMoE-1B-7B-0125-Instruct (MoE, 64 experts, top-8) and a dense control,
Qwen2.5-Coder-1.5B-Instruct, both Apache-2.0. Neither is the capstone model (16 routed + 1 shared experts, top-2,
G6 kernels). No reward and no update: this measures only what the mask would do before the policy moves. It is a note
for the owner of `rl/objective_v1.*`, which this PR does not edit.

## Question

With identical weights in sampler and trainer, what share of sampled tokens falls outside objective_v1's ratio region
[0.8, 1.2]? With identical weights every ratio should be 1, so anything outside is numerics: kernels, batch shapes and,
in an MoE, routing.

## Setup

`rl-loop/mismatch_probe.py` (new). 48 code_contests statements x 8 samples, 512 new tokens, temperature 1, vLLM 0.32.0
sampler (bf16), HF trainer with fp32 attention masters under bf16 autocast (the trainer's own setup).
`allenai/OLMoE-1B-7B-0125-Instruct` @ `b89a7c4b` and `Qwen/Qwen2.5-Coder-1.5B-Instruct` @ `2e1fd397`. One NVIDIA L40S
call (439 s); torch 2.13.0+cu130, transformers 5.19.0. Evidence: `fable_20261115_evidence/e3_probe_result.json`.
The Modal driver (`modal_e3.py`) stayed local; per model it ran:

```bash
python rl-loop/mismatch_probe.py --model <weights> --prompts <statements.jsonl> --out <probe.json> --n 48 --k 8 --max-new 512   # plus --dense for Qwen
```

Three comparisons on the same tokens: **engine** (trainer, one row per forward, vs the sampler's reported
log-probabilities: what the trainer masks on), **batch** (trainer, all 8 rows in one forward vs one row per forward),
**repeat** (the same trainer forward twice).

## Result (R2)

| | OLMoE (MoE) | Qwen 1.5B (dense) |
|---|---:|---:|
| Real tokens | 193,796 | 174,346 |
| Outside the region, trainer vs sampler | **2.04%** | 0.044% |
| Outside the region, trainer 8-row forward vs trainer 1-row forward | **1.75%** | 0.045% |
| Outside the region, same trainer forward twice | 0 | 0 |
| K3 gap, trainer vs sampler | 0.0020 | 0.0003 |
| Sequences with at least one masked token | 100% | 17.4% |
| Tokens whose expert set differs in some layer, 1-row vs 8-row forward | 44.8% | n/a |
| Tokens whose top-1 expert differs, 1-row vs 8-row | 1.3% | n/a |

*Surrogate models, one sampling seed.*

Masked share by the sampler's probability of the token (OLMoE / dense): below 0.1: **14.7%** / 0.56%; 0.1 to 0.5:
6.5% / 0.11%; 0.5 to 0.9: 0.7% / 0; above 0.9: 0 / 0. It does not depend on position in the completion.

What this establishes:

1. The prediction "the mask acts as a numerics filter on an MoE" held: about 46 times the dense rate.
2. Most of it is not an engine difference. The trainer disagrees with itself by almost as much when the only change is
   how many rows share a forward pass. The forward is deterministic when repeated.
3. The mask is not neutral: it removes about one in seven of the rarest sampled tokens, which carry most of the
   policy-gradient signal, before the policy has moved at all.

What it does not establish: any number for the capstone model, or that this hurts learning.

## It is bf16 inside the trainer, but fp32 in the trainer does not close the gap to the sampler (R2b)

Same probe on OLMoE with the training model entirely in fp32 (vLLM sampler still bf16), 32 prompts x 8, 384 new
tokens, 97,811 real tokens, NVIDIA A100 80GB PCIe (`e3_probe_result_fp32.json`; driver arguments
`--n 32 --k 8 --max-new 384 --hf-dtype float32 --vllm-util 0.25`):

| | bf16 trainer (R2) | fp32 trainer |
|---|---:|---:|
| Outside the region, 8-row vs 1-row forward | 1.75% | **0.001%** |
| Tokens whose expert set differs in some layer, 8-row vs 1-row | 44.8% | **0.13%** |
| Tokens whose top-1 expert differs | 1.3% | 0.003% |
| Outside the region, trainer vs (bf16) sampler | 2.04% | 1.34% |

*Surrogate model, one sampling seed; the fp32 column uses fewer prompts and shorter completions than the bf16 column.*

The trainer's disagreement with itself is bf16 rounding tipping near-tied router scores, and it vanishes in fp32.
Against a bf16 sampler the gap only shrinks from 2.0% to 1.3%: to remove it, both engines have to make the same routing
decision (matched precision on the routing path in both, or the sampler's routes replayed in the trainer). A third
probe (bf16, sampled by the training model itself with HF `generate`, `--sampler hf --hf-dtype bfloat16`,
`e3_probe_result_hf_bfloat16.json`) reproduced the bf16 batch column (1.71%, 44.9%).

## Suggested next step for the lead (not run)

Run `mismatch_probe.py` on the capstone-family checkpoint with its real sampler as soon as G5 ships one (under $1 at
these sizes), then decide with the lead between matched router precision, routing replay, or a wider/looser mask for
MoE. This note does not propose a change to `rl/objective_v1.*`.

## Unresolved

- **E3 went over its $1 cap: about $2.54 (ledger estimate).** Two probes that sampled with HF `generate` instead of
  vLLM took over 22 minutes each; the fp32 one hit its 1,500 s function timeout with no result ($1.00 spent for
  nothing). The time estimate was wrong. That probe was replaced by the vLLM-sampled fp32 probe on an A100 above.
- One sampling seed per probe; the fp32 probe is smaller than the bf16 one.

## Not measured

The capstone model, top-2 routing, G6 kernels, any effect on learning (no update was made), routing replay, matched
router precision in vLLM, and engine gaps at other batch sizes.
