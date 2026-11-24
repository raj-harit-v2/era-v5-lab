"""Rollout samplers: k completions for each prompt of a step, all at once.

Every sampler returns one Rollout per prompt, in the same shape the trainer already uses:
    seq         [k, P + max_new]  the prompt (no padding) followed by the completion, padded at the end
    cmask       [k, max_new]      True for completion tokens up to and including EOS
    rollout_lp  [k, max_new] or None   log-probability of each sampled token under the sampler (vLLM only)

Samplers (config `train.sampler`):
    policy     the old path: one generate per prompt (Team 5's model has no padding mask, so it needs this)
    g5_batch   Team 5's model: all prompts x k in one KV-cached decode (g5_decode.sample_many: left padding, per-row
               positions, padding masked in our attention), in chunks of at most `max_rows` rows
    hf_batch   one left-padded model.generate over all prompts x k (Hugging Face models)
    vllm       a vLLM engine in the same process and on the same GPU; after each optimiser step the trainer
               pushes the trainable weights into it with sync(). Only the trainable tensors move (attention only:
               about 0.5 GB in bf16 for OLMoE-1B-7B), not the full 13.8 GB.

Why rollout_lp matters: vLLM's kernels differ from the training forward, so the sampler's distribution is not
exactly the trained policy (reported K3 KL between engines: 1e-3 to 1e-1 for MoE models, research/g10_gpu/
q3_rollouts.md). The trainer logs that gap and can correct for it with truncated importance sampling.
vLLM reports logprobs of the raw model distribution, which equals the sampling distribution only at
temperature 1 with top_p 1 and no top_k, so use those settings when the correction is on.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import torch


@dataclass
class Rollout:
    seq: torch.Tensor
    cmask: torch.Tensor
    rollout_lp: torch.Tensor | None = None


def completion_mask(comp: torch.Tensor, eos_id: int | None) -> torch.Tensor:
    """True up to and including the first EOS of each row; everything after it is False."""
    if eos_id is None:
        return torch.ones_like(comp, dtype=torch.bool)
    is_eos = (comp == eos_id).long()
    return ~((torch.cumsum(is_eos, 1) - is_eos) > 0)


class PolicySampler:
    """One generate call per prompt (works for every model kind)."""

    def __init__(self, policy):
        self.policy = policy

    def sample(self, prompts, k, max_new, temperature, generator=None) -> list[Rollout]:
        return [Rollout(*self.policy.sample(p, k, max_new, temperature, generator)) for p in prompts]


class G5BatchSampler:
    """All prompts x k in one decode through policy.sample_many (Team 5's model, g5_decode.sample_many). Prompts are
    taken in chunks of at most max_rows rows (KV cache and the [rows, vocab] logits grow with rows)."""

    def __init__(self, policy, max_rows: int = 128):
        if max_rows < 1:
            raise ValueError("sampler_max_rows must be at least 1")
        self.policy = policy
        self.max_rows = max_rows

    def sample(self, prompts, k, max_new, temperature, generator=None) -> list[Rollout]:
        per = max(1, self.max_rows // k)
        out = []
        for i in range(0, len(prompts), per):
            out += [Rollout(s, m) for s, m in self.policy.sample_many(prompts[i:i + per], k, max_new, temperature, generator)]
        return out


class HFBatchSampler:
    """All prompts x k in one left-padded model.generate. Hugging Face models only (they take a padding mask)."""

    def __init__(self, policy, pad_id: int | None = None):
        self.policy = policy
        self.pad_id = pad_id if pad_id is not None else (policy.eos_id if policy.eos_id is not None else 0)

    @torch.no_grad()
    def sample(self, prompts, k, max_new, temperature, generator=None) -> list[Rollout]:
        pol, dev, pad = self.policy, self.policy.device, self.pad_id
        if generator is not None:  # generate() has no generator argument; seed torch from ours
            torch.manual_seed(int(torch.randint(0, 2**31 - 1, (1,), generator=generator)))
        width = max(len(p) for p in prompts)
        rows, masks = [], []
        for p in prompts:
            for _ in range(k):
                rows.append([pad] * (width - len(p)) + list(p))
                masks.append([0] * (width - len(p)) + [1] * len(p))
        ids = torch.tensor(rows, dtype=torch.long, device=dev)
        attn = torch.tensor(masks, dtype=torch.long, device=dev)
        was_training = pol.model.training
        pol.model.eval()
        with pol.autocast():
            out = pol.model.generate(input_ids=ids, attention_mask=attn, max_new_tokens=max_new,
                                     min_new_tokens=max_new if pol.eos_id is None else 0,
                                     do_sample=temperature > 0,
                                     temperature=temperature if temperature > 0 else None,
                                     top_k=0, top_p=1.0, eos_token_id=pol.eos_id, pad_token_id=pad)
        pol.model.train(was_training)
        comp = out[:, width:]
        if comp.shape[1] < max_new:
            comp = torch.cat([comp, torch.full((comp.shape[0], max_new - comp.shape[1]), pad, device=dev)], 1)
        cmask = completion_mask(comp, pol.eos_id)
        result = []
        for i, p in enumerate(prompts):
            c, m = comp[i * k:(i + 1) * k], cmask[i * k:(i + 1) * k]
            prompt = torch.tensor([list(p)] * k, dtype=torch.long, device=dev)
            result.append(Rollout(torch.cat([prompt, c], 1), m))
        return result


class VLLMSampler:
    """A vLLM engine colocated with the trainer (same process, same GPU).

    Create it BEFORE loading the training model: vLLM reserves `gpu_memory_utilization` of the GPU at start.
    """

    def __init__(self, model_path: str, gpu_memory_utilization: float = 0.3, max_model_len: int = 4096,
                 seed: int = 0, enable_sleep_mode: bool = False, dtype: str = "bfloat16", enforce_eager: bool = False):
        os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")  # keep the engine in this process (weight sync)
        from vllm import LLM  # noqa: PLC0415  (GPU-only dependency)
        self.llm = LLM(model=model_path, dtype=dtype, gpu_memory_utilization=gpu_memory_utilization,
                       max_model_len=max_model_len, seed=seed, enable_sleep_mode=enable_sleep_mode,
                       enforce_eager=enforce_eager)
        self.sleep_mode = enable_sleep_mode
        self.eos_id: int | None = None
        self.pad_id = 0
        self.device = "cuda"
        self.sync_path: str | None = None  # which weight-loading route worked (recorded in the run summary)

    def bind(self, eos_id: int | None, pad_id: int | None, device: str) -> "VLLMSampler":
        self.eos_id, self.device = eos_id, device
        self.pad_id = pad_id if pad_id is not None else (eos_id if eos_id is not None else 0)
        return self

    @torch.no_grad()
    def sample(self, prompts, k, max_new, temperature, generator=None) -> list[Rollout]:
        from vllm import SamplingParams  # noqa: PLC0415
        seed = int(torch.randint(0, 2**31 - 1, (1,), generator=generator)) if generator is not None else None
        sp = SamplingParams(n=k, max_tokens=max_new, temperature=temperature, top_p=1.0, logprobs=0, seed=seed,
                            ignore_eos=self.eos_id is None, detokenize=False)
        outs = self.llm.generate([{"prompt_token_ids": list(p)} for p in prompts], sp, use_tqdm=False)
        result = []
        for p, o in zip(prompts, outs):
            comp = torch.full((k, max_new), self.pad_id, dtype=torch.long)
            lp = torch.zeros(k, max_new)
            cmask = torch.zeros(k, max_new, dtype=torch.bool)
            for j, c in enumerate(o.outputs):
                ids = list(c.token_ids)[:max_new]
                comp[j, :len(ids)] = torch.tensor(ids, dtype=torch.long)
                cmask[j, :len(ids)] = True
                for t, (tok, d) in enumerate(zip(ids, c.logprobs or [])):
                    lp[j, t] = d[tok].logprob
            prompt = torch.tensor([list(p)] * k, dtype=torch.long)
            result.append(Rollout(torch.cat([prompt, comp], 1).to(self.device), cmask.to(self.device),
                                  lp.to(self.device)))
        return result

    def _load(self, weights: list[tuple[str, torch.Tensor]]) -> None:
        def load_on_worker(worker, w):  # runs inside the vLLM worker (same process here)
            worker.model_runner.model.load_weights(weights=w)
            return True

        try:
            self.llm.collective_rpc(load_on_worker, args=(weights,))
            self.sync_path = "collective_rpc"
            return
        except Exception as first:  # noqa: BLE001  (fall back to the attribute route TRL uses)
            engine = self.llm.llm_engine
            for chain in (("model_executor", "driver_worker", "worker", "model_runner", "model"),
                          ("model_executor", "driver_worker", "model_runner", "model"),
                          ("engine_core", "engine_core", "model_executor", "driver_worker", "worker", "model_runner",
                           "model")):
                obj = engine
                try:
                    for a in chain:
                        obj = getattr(obj, a)
                except AttributeError:
                    continue
                obj.load_weights(weights=weights)
                self.sync_path = ".".join(chain)
                return
            raise RuntimeError(f"could not reach the vLLM model to load weights: {first!r}") from first

    @torch.no_grad()
    def sync(self, named_params: Iterable[tuple[str, torch.Tensor]]) -> int:
        """Push weights (Hugging Face names) into vLLM and drop its prefix cache. Returns the bytes sent."""
        weights = [(n, p.detach().to(torch.bfloat16).contiguous()) for n, p in named_params]
        self._load(weights)
        self.llm.reset_prefix_cache()  # cached KV from the old weights must not be reused
        return sum(w.numel() * w.element_size() for _, w in weights)

    def sleep(self) -> None:
        if self.sleep_mode:
            self.llm.sleep(level=1)

    def wake_up(self) -> None:
        if self.sleep_mode:
            self.llm.wake_up()


def make_sampler(kind: str, policy, vllm: VLLMSampler | None = None, pad_id: int | None = None, max_rows: int = 128):
    if kind == "policy":
        return PolicySampler(policy)
    if kind == "g5_batch":
        if not hasattr(policy, "sample_many"):
            raise ValueError("sampler g5_batch needs a policy with sample_many (Team 5's adapter policy)")
        return G5BatchSampler(policy, max_rows)
    if kind == "hf_batch":
        return HFBatchSampler(policy, pad_id)
    if kind == "vllm":
        if vllm is None:
            raise ValueError("sampler vllm needs a VLLMSampler created before the model")
        return vllm.bind(policy.eos_id, pad_id, policy.device)
    raise ValueError(f"unknown sampler {kind!r}; choose policy, g5_batch, hf_batch or vllm")
