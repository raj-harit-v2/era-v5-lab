"""tokens_per_byte for one optimizer step: scored tokens divided by the UTF-8 bytes they encode.

A rise means the tokenizer splits the batch's text into more pieces per byte: a new language mix, a tokenizer
swap, or text the normalizer did not expect. It is a data and tokenizer health metric, not a model metric.

The G5 week-2 trainer (teams/05-architecture/harness/train_week2.py) already has both parts at each step:
`y` (targets, -100 at padding) and `lengths` (UTF-8 bytes of each target token, 0 at padding), from
DocumentWindows.batch(). Its metrics.jsonl also has them as `train/scored_tokens` and `train/utf8_bytes`, so
the Grafana panel can work the ratio out for runs that do not log tokens_per_byte.

    stats = tokens_per_byte(y, lengths, langs=[dataset.window_slices[i] for i in batch_ids])
    writer.write(step, **stats, ...)

writes `tokens_per_byte` (whole batch) and `tokens_per_byte_by_lang` ({slice: value}). The ClickHouse loader
stores the dict as `tokens_per_byte_by_lang.<slice>` (for example `tokens_per_byte_by_lang.hi`). Slice names are
G5's: en, code, math, sci, hi, bn, ta, te, kn, ml, mr, gu, pa, or, as. Rows without a tag (None) count toward
the batch total only. Pass the whole optimizer step (all micro-batches); across data-parallel ranks, sum
tokens and bytes before dividing, not the per-rank ratios.
"""

IGNORE_INDEX = -100


def _rows(x):
    if hasattr(x, "tolist"):  # numpy array, torch tensor
        x = x.tolist()
    if not isinstance(x, (list, tuple)):
        raise TypeError("expected a 1-D or 2-D array of tokens or byte lengths")
    if x and not isinstance(x[0], (list, tuple)):
        x = [x]  # one row
    return [list(r) for r in x]


def tokens_per_byte(targets, byte_lengths, langs=None, ignore_index=IGNORE_INDEX):
    """{"tokens_per_byte": float, "tokens_per_byte_by_lang": {lang: float}} for one batch.

    targets: [rows, seq] token ids, `ignore_index` at padding. byte_lengths: same shape, UTF-8 bytes per target
    token (0 at padding). langs: optional, one tag per row (or None). A token counts when its target is not
    `ignore_index`; its bytes count with it. Returns {} when the batch has no bytes, so nothing is written.
    `tokens_per_byte_by_lang` is left out when no row has a tag.
    """
    t_rows, b_rows = _rows(targets), _rows(byte_lengths)
    if len(t_rows) != len(b_rows) or any(len(t) != len(b) for t, b in zip(t_rows, b_rows)):
        raise ValueError("targets and byte_lengths must have the same shape")
    if langs is None:
        langs = [None] * len(t_rows)
    elif len(langs) != len(t_rows):
        raise ValueError("langs needs one tag per row")
    total_tokens = total_bytes = 0
    by_lang = {}
    for t_row, b_row, lang in zip(t_rows, b_rows, langs):
        tokens = nbytes = 0
        for t, b in zip(t_row, b_row):
            if t != ignore_index:
                if b < 0:
                    raise ValueError("negative byte length")
                tokens += 1
                nbytes += b
        total_tokens += tokens
        total_bytes += nbytes
        if lang is not None:
            counts = by_lang.setdefault(str(lang), [0, 0])
            counts[0] += tokens
            counts[1] += nbytes
    if total_bytes <= 0:
        return {}
    stats = {"tokens_per_byte": total_tokens / total_bytes}
    lang_stats = {lang: t / b for lang, (t, b) in sorted(by_lang.items()) if b > 0}
    if lang_stats:
        stats["tokens_per_byte_by_lang"] = lang_stats
    return stats
