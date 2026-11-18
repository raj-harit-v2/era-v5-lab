"""LabLM checks with a stub model (no checkpoint, tokenizer or dataset needed): run with
    pytest teams/09-evaluation/harness_lab/tests -q

The stub's hidden state at position t is the mean of the embeddings of tokens 0..t, so it is causal like Team 5's model,
and right padding cannot change a real position. `Reference` is #387's scoring loop, kept here unchanged, so the batched
code is checked against the code TSAI was first shown.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from torch import nn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from lm_eval_lab import TIER_ROLE, LabLM, check_lm_eval_version, split_pair, without_env_report  # noqa: E402

V = 2 + 256 + 1          # pad, bos, one id per byte, and one id ("~") whose table bytes are wrong on purpose
BAD = V - 1


class StubTokenizer:
    """One id per UTF-8 byte; "~" maps to BAD, whose table row is "-", so its text does not round-trip."""

    def _ids(self, text):
        return [BAD if b == ord("~") else 2 + b for b in text.encode("utf-8")]

    def encode(self, text, add_special_tokens=False):
        return SimpleNamespace(ids=self._ids(text))

    def encode_batch(self, texts, add_special_tokens=False):
        return [self.encode(t) for t in texts]


class StubArtifacts:
    """The parts of Team 5's week2 Artifacts that LabLM uses, with the same strict encode."""
    pad_id, bos_id = 0, 1

    def __init__(self):
        self.tokenizer = StubTokenizer()
        self.bytes = np.zeros((V, 4), dtype=np.uint8)
        self.lengths = np.ones(V, dtype=np.int16)
        self.bytes[2:2 + 256, 0] = np.arange(256)
        self.bytes[BAD, 0] = ord("-")

    def encode(self, text):
        ids = self.tokenizer.encode(text).ids
        if b"".join(self.bytes[i, : int(self.lengths[i])].tobytes() for i in ids) != text.encode("utf8"):
            raise ValueError("Tokenizer/table does not exactly reconstruct source UTF-8; BPB would be invalid")
        return ids


class StubModel(nn.Module):
    def __init__(self):
        super().__init__()
        torch.manual_seed(0)
        self.emb = nn.Embedding(V, 16)
        self.head = nn.Linear(16, V, bias=False)

    def hidden(self, ids, valid):
        e = self.emb(ids) * valid[..., None]
        steps = torch.arange(1, ids.shape[1] + 1, dtype=e.dtype, device=ids.device)[None, :, None]
        return e.cumsum(1) / steps


class Reference:
    """#387's LabLM.loglikelihood (12 Nov): one head call and two host syncs per request."""

    def __init__(self, model, art, block_size, max_batch_tokens=16384):
        self.model, self.art, self.block, self.max_batch_tokens = model, art, block_size, max_batch_tokens

    def _encode(self, text):
        if not text:
            return []
        try:
            return self.art.encode(text)
        except ValueError:
            return self.art.tokenizer.encode(text, add_special_tokens=False).ids

    def _pair(self, context, continuation):
        n_spaces = len(context) - len(context.rstrip())
        if n_spaces:
            continuation, context = context[-n_spaces:] + continuation, context[:-n_spaces]
        ctx = self._encode(context)
        whole = self._encode(context + continuation)
        cont = whole[len(ctx):]
        if not cont:
            raise ValueError("a continuation produced no tokens")
        return [self.art.bos_id] + ctx, cont

    def _score_batch(self, batch, seqs, out):
        width = max(len(seqs[i][0]) for i in batch)
        ids = torch.full((len(batch), width), self.art.pad_id, dtype=torch.long)
        valid = torch.zeros((len(batch), width), dtype=torch.bool)
        for j, i in enumerate(batch):
            x = seqs[i][0]
            ids[j, : len(x)] = torch.tensor(x, dtype=torch.long)
            valid[j, : len(x)] = True
        with torch.no_grad():
            hidden = self.model.hidden(ids, valid)
            for j, i in enumerate(batch):
                x, targets = seqs[i]
                end, n = len(x), len(targets)
                logp = torch.log_softmax(self.model.head(hidden[j, end - n: end]).float(), dim=-1)
                t = torch.tensor(targets, dtype=torch.long)
                out[i] = (float(logp.gather(1, t[:, None]).sum().item()), bool((logp.argmax(-1) == t).all().item()))

    def loglikelihood(self, requests):
        seqs = []
        for req in requests:
            ctx, cont = self._pair(*req.args)
            toks = (ctx + cont)[-(self.block + 1):]
            n_cont = min(len(cont), len(toks) - 1)
            seqs.append((toks[:-1], toks[-n_cont:]))
        order = sorted(range(len(seqs)), key=lambda i: -len(seqs[i][0]))
        out, batch = [None] * len(seqs), []
        for i in order:
            if batch and (len(batch) + 1) * len(seqs[batch[0]][0]) > self.max_batch_tokens:
                self._score_batch(batch, seqs, out)
                batch = []
            batch.append(i)
        if batch:
            self._score_batch(batch, seqs, out)
        return out


QUESTION = "Question: which letter? Answer:"
PAIRS = ([(QUESTION, f" {c}") for c in "ABCD"]                      # one multiple-choice item: 4 requests, 1 row
         + [("Question: 2+2=", " 4"), ("Short", " answer that is longer"), ("Trailing space ", "moves"),
            ("", "empty context"), ("tilde ~ text", " and ~ more"), ("Short", " answer that is longer")])


def reqs(pairs):
    return [SimpleNamespace(args=p) for p in pairs]


@pytest.mark.parametrize("budget", [8, 64, 100000])
@pytest.mark.parametrize("head_rows", [1, 3, None])
def test_matches_reference(budget, head_rows):
    model, art = StubModel().eval(), StubArtifacts()
    lm = LabLM(model, art, block_size=512, device="cpu", bf16=False, max_batch_tokens=budget, head_rows=head_rows)
    got = lm.loglikelihood(reqs(PAIRS))
    want = Reference(model, art, 512, budget).loglikelihood(reqs(PAIRS))
    for (lp, greedy), (ref_lp, ref_greedy) in zip(got, want):
        assert lp == pytest.approx(ref_lp, abs=1e-4) and greedy == ref_greedy
    assert all(type(lp) is float and type(g) is bool for lp, g in got)


@torch.no_grad()
def manual(model, art, context, continuation, block):
    context, continuation = split_pair(context, continuation)
    ctx = art.tokenizer.encode(context).ids
    cont = art.tokenizer.encode(context + continuation).ids[len(ctx):]
    toks = ([art.bos_id] + ctx + cont)[-(block + 1):]
    x = torch.tensor([toks[:-1]])
    logp = torch.log_softmax(model.head(model.hidden(x, torch.ones_like(x, dtype=torch.bool)))[0], -1)
    m = min(len(cont), len(toks) - 1)
    return float(logp[-m:].gather(1, torch.tensor(toks[-m:])[:, None]).sum())


def test_matches_a_hand_computed_sum():
    model, art = StubModel().eval(), StubArtifacts()
    lm = LabLM(model, art, block_size=512, device="cpu", bf16=False)
    for (ctx, cont), (lp, _) in zip(PAIRS, lm.loglikelihood(reqs(PAIRS))):
        assert lp == pytest.approx(manual(model, art, ctx, cont, 512), abs=1e-4)


def test_answer_options_share_one_forward_row():
    lm = LabLM(StubModel().eval(), StubArtifacts(), block_size=512, device="cpu", bf16=False)
    lm.loglikelihood(reqs(PAIRS))
    # the 4 options of one item share a row, and the repeated ("Short", ...) request shares one: 10 requests, 6 rows
    assert (lm.requests_scored, lm.rows_scored) == (len(PAIRS), len(PAIRS) - 4)


def test_left_truncation_keeps_the_continuation():
    model, art = StubModel().eval(), StubArtifacts()
    lm = LabLM(model, art, block_size=8, device="cpu", bf16=False)
    pairs = [("a long context of many bytes", " end"), ("x", " a continuation longer than the block")]
    got = lm.loglikelihood(reqs(pairs))
    want = Reference(model, art, 8).loglikelihood(reqs(pairs))
    for (lp, g), (ref_lp, ref_g), (ctx, cont) in zip(got, want, pairs):
        assert lp == pytest.approx(ref_lp, abs=1e-4) and g == ref_g
        assert lp == pytest.approx(manual(model, art, ctx, cont, 8), abs=1e-4)


def test_encode_fallbacks_are_counted_once_per_text():
    lm = LabLM(StubModel().eval(), StubArtifacts(), block_size=512, device="cpu", bf16=False)
    lm.loglikelihood(reqs([("tilde ~ text", " a"), ("tilde ~ text", " b")]))
    # the context and both joined strings hold "~"; the ids are still the tokenizer's, as in #387
    assert lm.encode_fallbacks == 3


def test_same_numbers_twice():
    model, art = StubModel().eval(), StubArtifacts()
    lm = LabLM(model, art, block_size=512, device="cpu", bf16=False)
    assert lm.loglikelihood(reqs(PAIRS)) == lm.loglikelihood(reqs(PAIRS))


def test_empty_continuation_is_refused():
    lm = LabLM(StubModel(), StubArtifacts(), block_size=16, device="cpu", bf16=False)
    with pytest.raises(ValueError):
        lm.loglikelihood(reqs([("context", "")]))


def test_generation_is_refused():
    lm = LabLM(StubModel(), StubArtifacts(), block_size=16, device="cpu", bf16=False)
    with pytest.raises(NotImplementedError):
        lm.generate_until([])


def test_the_env_report_is_skipped_and_restored():
    """simple_evaluate calls add_env_info and get_git_commit_hash by these module names (lm-eval 0.4.13); if a new
    version stops doing so, the skip would silently do nothing, so this checks the call sites too."""
    import inspect

    import lm_eval.evaluator as ev

    source = inspect.getsource(ev.simple_evaluate)
    assert "add_env_info(results)" in source and "get_git_commit_hash()" in source
    before = ev.add_env_info, ev.get_git_commit_hash
    with without_env_report():
        results = {}
        assert ev.add_env_info(results) is None and results == {} and ev.get_git_commit_hash() is None
    assert (ev.add_env_info, ev.get_git_commit_hash) == before


def test_the_lm_eval_version_is_pinned():
    from importlib import metadata

    check_lm_eval_version({"lm_eval_version": metadata.version("lm_eval")})
    with pytest.raises(SystemExit, match="pins lm-eval 0.0.1"):
        check_lm_eval_version({"lm_eval_version": "0.0.1"})


def test_tiers_split_the_config_by_role():
    import yaml

    cfg = yaml.safe_load((HERE.parent / "eval_lab_v1.yaml").read_text(encoding="utf-8"))
    tasks = {e["task"]: e["role"] for g in cfg["groups"] for e in g["tasks"]}
    tier = {name: {t for t, r in tasks.items() if r in roles} for name, roles in TIER_ROLE.items()}
    assert tier["A"] == {"mmlu", "milu_Hindi", "milu_Telugu", "milu_Tamil", "milu_Bengali"} == set(
        cfg["guard"]["expected_items"])
    assert tier["B"] == {"arc_challenge", "hellaswag", "leaderboard_mmlu_pro", "belebele_hin_Deva",
                         "belebele_tel_Telu", "belebele_tam_Taml"}
    assert tier["AB"] == set(tasks)
