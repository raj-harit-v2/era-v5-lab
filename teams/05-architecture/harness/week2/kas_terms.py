"""Unigram initialization and correction-row dropout for the KAS head."""

import math
import torch

from .unigram import additive_log_prior


@torch.no_grad()
def initialize_unigram_(parameter, counts, *, add_eos_per_document):
    """Initialize the trainable float32 head.unigram from verified raw counts.

    Add one to every ID, normalize, log, subtract the vocabulary mean, then store
    float32. Arithmetic before storage uses Python double precision; bitwise
    parity with the pinned implementation's intermediate dtype is not claimed.
    EOS addition is an explicit p1536 adaptation, not a reference default.
    """
    if not isinstance(parameter, torch.nn.Parameter) or not parameter.requires_grad:
        raise ValueError("head.unigram must be a trainable Parameter")
    if parameter.dtype != torch.float32 or tuple(parameter.shape) != (len(counts.counts),):
        raise ValueError("head.unigram must be float32 with one scalar per vocabulary ID")
    values, identity = additive_log_prior(counts, smoothing=1.0,
                                         add_eos_per_document=add_eos_per_document)
    mean = math.fsum(values) / len(values)
    centered = [value - mean for value in values]
    parameter.copy_(torch.tensor(centered, dtype=torch.float32, device=parameter.device))
    return {
        **identity,
        "centering": "subtract_vocabulary_mean",
        "initialization_math_dtype": "float64",
        "storage_dtype": "float32",
        "trainable": True,
    }


def correction_row_dropout(tok_u, *, probability, training, generator=None):
    """Apply inverted row dropout only to the supplied V x rank correction.

    The chosen arm must explicitly pass probability=0.05. One independent mask
    of shape [V, 1] is sampled per invocation; the caller owns invocation timing.
    No per-step caching or microbatch-sharing semantics are asserted here. The
    input parameter is never modified, and eval consumes no RNG. Apply this to
    tok_u only, never to the codec, unigram, output projection or final logits.
    """
    if tok_u.ndim != 2 or not tok_u.is_floating_point():
        raise ValueError("Token correction must be a floating V x rank tensor")
    if type(training) is not bool:
        raise ValueError("Training mode must be boolean")
    if type(probability) not in (int, float) or not math.isfinite(probability) or not 0 <= probability < 1:
        raise ValueError("Dropout probability must be finite in [0, 1)")
    if not training or probability == 0:
        return tok_u
    keep = 1.0 - probability
    mask = torch.rand((tok_u.shape[0], 1), device=tok_u.device, generator=generator) < keep
    return tok_u * mask.to(tok_u.dtype) / keep
