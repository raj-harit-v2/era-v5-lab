"""Heldout sum-of-loss / sum-of-raw-bytes scorer, never batch-mean BPB."""

import math
import torch
from torch.nn import functional as F
from torch.nn.utils.rnn import pad_sequence


EVAL_BATCH_TOKENS = 16_384
# Bound the dense vocabulary projection and FP32 cross-entropy workspace.
EVAL_HEAD_TOKENS = 512


# Keep per-token losses so evaluation can normalize by bytes after summing.
def token_nll(logits, targets):
    return F.cross_entropy(
        logits.float().reshape(-1, logits.shape[-1]),
        targets.reshape(-1),
        ignore_index=-100,
        reduction="none",
    ).reshape(targets.shape)


def _length_batches(windows, max_batch_tokens):
    if max_batch_tokens <= 0:
        raise ValueError("Evaluation token budget must be positive")
    indices = sorted(range(len(windows)), key=lambda i: len(windows[i][1]))
    batch = []
    for i in indices:
        width = len(windows[i][1])
        if width > max_batch_tokens:
            raise ValueError("Evaluation window exceeds token budget")
        # Widths are nondecreasing, so this bounds the padded batch as well.
        if batch and (len(batch) + 1) * width > max_batch_tokens:
            yield batch
            batch = []
        batch.append(i)
    if batch:
        yield batch


def _scored_batches(model, dataset, device, autocast_context, max_batch_tokens):
    for indices in _length_batches(dataset.windows, max_batch_tokens):
        rows = [dataset.windows[i] for i in indices]
        # Each row is an independent document window with right padding only.
        x = pad_sequence(
            [torch.tensor(row[0], dtype=torch.long) for row in rows],
            batch_first=True,
            padding_value=dataset.pad_id,
        ).to(device)
        y = pad_sequence(
            [torch.tensor(row[1], dtype=torch.long) for row in rows],
            batch_first=True,
            padding_value=-100,
        ).to(device)
        valid = y != -100
        with autocast_context():
            hidden = model.hidden(x, valid)[valid]
            targets = y[valid]
            nll = torch.cat(
                [
                    token_nll(model.head(h), t)
                    for h, t in zip(
                        hidden.split(EVAL_HEAD_TOKENS), targets.split(EVAL_HEAD_TOKENS)
                    )
                ]
            )
        if not torch.isfinite(nll).all():
            raise ValueError("Nonfinite heldout NLL")
        # One device transfer per batch. The packed loss vector follows row order.
        losses = nll.double().cpu().tolist()
        offset = 0
        for i, (_, targets, lengths) in zip(indices, rows):
            count = len(targets)
            yield i, math.fsum(losses[offset : offset + count]), sum(lengths), count
            offset += count


def _fixed_batches(model, dataset, batch_size, device, autocast_context):
    for start in range(0, len(dataset.windows), batch_size):
        indices = range(start, min(start + batch_size, len(dataset.windows)))
        x, y, lengths = dataset.batch(indices, device)
        with autocast_context():
            nll = token_nll(model(x, y != -100), y)
        if not torch.isfinite(nll).all():
            raise ValueError("Nonfinite heldout NLL")
        for i, row, targets, row_lengths in zip(indices, nll, y, lengths):
            valid = targets != -100
            yield i, math.fsum(row[valid].double().cpu().tolist()), int(
                row_lengths.sum()
            ), int(valid.sum())


@torch.no_grad()
def evaluate(
    model, dataset, batch_size, device, autocast_context, *, max_batch_tokens=None
):
    training = model.training
    cpu_rng = torch.get_rng_state()
    cuda_rng = torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
    values = []
    byte_count = 0
    token_count = 0
    by_slice = {}
    try:
        model.eval()
        rows = (
            _fixed_batches(model, dataset, batch_size, device, autocast_context)
            if max_batch_tokens is None
            else _scored_batches(
                model, dataset, device, autocast_context, max_batch_tokens
            )
        )
        for i, nats, size, count in rows:
            values.append(nats)
            byte_count += size
            token_count += count
            name = dataset.window_slices[i]
            if name is not None:
                totals = by_slice.setdefault(
                    name, {'nats': [], 'bytes': 0, 'tokens': 0}
                )
                totals['nats'].append(nats)
                totals['bytes'] += size
                totals['tokens'] += count
        if byte_count != dataset.raw_bytes:
            raise ValueError("Heldout denominator failed byte conservation")
        total = math.fsum(values)
        result = {
            "val/nll_nats": total,
            "val/utf8_bytes": byte_count,
            "val/scored_tokens": token_count,
            "val/bpb": total / math.log(2) / byte_count,
            "val/perplexity": math.exp(total / token_count),
        }
        if by_slice:
            from .scoring import group_metrics

            bpbs = {}
            for name, totals in sorted(by_slice.items()):
                if (
                    totals['bytes'] != dataset.slice_raw_bytes[name]
                    or totals['bytes'] <= 0
                ):
                    raise ValueError('Slice byte conservation failed')
                nats = math.fsum(totals['nats'])
                bpbs[name] = nats / math.log(2) / totals['bytes']
                result.update(
                    {
                        f'val/slices/{name}/bpb': bpbs[name],
                        f'val/slices/{name}/nll_nats': nats,
                        f'val/slices/{name}/utf8_bytes': totals['bytes'],
                        f'val/slices/{name}/scored_tokens': totals['tokens'],
                    }
                )
            result.update(group_metrics(bpbs))
        return result
    finally:
        model.train(training)
        torch.set_rng_state(cpu_rng)
        if cuda_rng is not None:
            torch.cuda.set_rng_state_all(cuda_rng)
