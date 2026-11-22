#!/usr/bin/env python3
"""Guards llamacpp_lm.py against the shifted-logprob bug (instructor's request, 28 Oct).

    python test_llamacpp_lm.py <model.gguf>        # exits non-zero if a check fails
    EVAL_MINI_GGUF=<model.gguf> python -m pytest test_llamacpp_lm.py

llama-cpp-python's server returns prompt log-probabilities one position late: log p(" Paris" | "The capital of
France is") came back as -8.58, the value of the distribution AFTER " Paris", instead of -0.49. lm_eval sums
such values without any error. The checks compare LlamaCppLM with the same model's own greedy generation, so
they hold for any GGUF, not only one model's numbers:

  1. the score of " Paris" equals the log-probability greedy generation reports for that token;
  2. it is NOT the off-by-one value (the generated token's log-probability one position later);
  3. scoring with the prefix cache equals scoring every request from scratch;
  4. the most likely continuation of an easy multiple-choice item is the right one.
"""
from __future__ import annotations

import os, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llamacpp_lm import LlamaCppLM  # noqa: E402

CONTEXT, ANSWER = "The capital of France is", " Paris"
TOL = 0.05   # nats; GPU kernels for different batch shapes differ by ~0.004


class _Req:
    def __init__(self, *args):
        self.args = args


def check(gguf: str) -> list[str]:
    lm = LlamaCppLM(gguf, n_ctx=512)
    failures = []

    # the answer's FIRST token under this model's tokenizer: " Paris" is one token for OLMoE and sarvam-1 (so the
    # check is unchanged there), " Par" + "is" for Granite 3.0; generation reports one token's log-probability
    _, cont = lm._encode_pair(CONTEXT, ANSWER)
    answer = lm.llm.detokenize(cont[:1]).decode("utf-8", errors="replace")

    # the model's own greedy next token after CONTEXT, with its log-probability, from generation
    gen = lm.llm.create_completion(prompt=CONTEXT, max_tokens=1, temperature=0.0, top_k=1, logprobs=5)
    top = gen["choices"][0]["logprobs"]["top_logprobs"][0]
    if answer not in top:
        return [f"model does not rank {answer!r} (first token of {ANSWER!r}) in its top-5 after {CONTEXT!r} ({top}); "
                "use a stronger model"]
    lp_gen = top[answer]
    lm.llm.reset()

    lp, greedy = lm.loglikelihood([_Req(CONTEXT, answer)], disable_tqdm=True)[0]
    if abs(lp - lp_gen) > TOL:
        failures.append(f"1. score {lp:.3f} != generation's {lp_gen:.3f} for {answer!r}")

    # the off-by-one value: the answer tokens read from the rows one position later (row i, not i-1), the
    # server's bug; computed from the logit rows the scoring call above left behind, so it is always finite
    ctx, cont = lm._encode_pair(CONTEXT, answer)
    rows = np.asarray(lm.llm.scores[len(ctx): len(ctx) + len(cont)], dtype=np.float64)
    after = float((rows - np.logaddexp.reduce(rows, axis=1, keepdims=True))[np.arange(len(cont)), cont].sum())
    if abs(lp - after) <= TOL and abs(lp_gen - after) > TOL:
        failures.append(f"2. score {lp:.3f} equals the off-by-one value {after:.3f}")

    reqs = [_Req("Question: Which gas do plants absorb from the air to make food?\nAnswer:", c)
            for c in (" Carbon dioxide", " Oxygen", " Nitrogen", " Helium")]
    lm.llm.reset()
    cached = lm.loglikelihood(reqs, disable_tqdm=True)
    fresh = []
    for r in reqs:
        lm.llm.reset()
        fresh.append(lm.loglikelihood([r], disable_tqdm=True)[0])
    worst = max(abs(a[0] - b[0]) for a, b in zip(cached, fresh))
    if worst > TOL:
        failures.append(f"3. prefix cache changes a score by {worst:.4f}")
    if max(range(4), key=lambda i: cached[i][0]) != 0:
        failures.append(f"4. easy item answered wrong: {[round(c[0], 2) for c in cached]}")

    print(f"{Path(gguf).name}: log p({answer!r}) = {lp:.3f}, generation {lp_gen:.3f}, off-by-one value {after:.3f}; "
          f"cache max diff {worst:.4f}")
    return failures


def test_logprobs_not_shifted():   # pytest entry point
    gguf = os.environ.get("EVAL_MINI_GGUF")
    if not gguf:
        import pytest
        pytest.skip("set EVAL_MINI_GGUF to a GGUF file")
    assert not check(gguf)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    fails = check(sys.argv[1])
    for f in fails:
        print("FAIL", f)
    print("PASS" if not fails else f"{len(fails)} check(s) failed")
    sys.exit(1 if fails else 0)
