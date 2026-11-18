"""Tests for tokenizer_transfer.py (G10). Fake character tokenizers stand in; no tokenizer file, no data.

    pytest teams/10-post-training/sft/test_tokenizer_transfer.py -q
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import convert  # noqa: E402
import tokenizer_transfer as tt  # noqa: E402

MARKERS = ["<|endoftext|>", "<|im_start|>", "<|im_end|>", "<|think|>", "<|/think|>"]
SPLIT = re.compile("(" + "|".join(re.escape(m) for m in MARKERS) + ")")


class Enc:
    def __init__(self, ids, offsets):
        self.ids, self.offsets = ids, offsets


class CharTok:
    """One token per character (markers are one token each); `double` makes every 'a' two tokens."""

    def __init__(self, double=False):
        self.double, self.vocab = double, {m: i for i, m in enumerate(MARKERS)}

    def _id(self, piece):
        return self.vocab.setdefault(piece, len(self.vocab))

    def encode(self, text):
        ids, offs, pos = [], [], 0
        for part in SPLIT.split(text):
            if part in MARKERS:
                ids.append(self._id(part))
                offs.append((pos, pos + len(part)))
            else:
                for k, ch in enumerate(part):
                    if self.double and ch == "a":
                        ids += [self._id("a1"), self._id("a2")]
                        offs += [(pos + k, pos + k + 1)] * 2
                    else:
                        ids.append(self._id(ch))
                        offs.append((pos + k, pos + k + 1))
            pos += len(part)
        return Enc(ids, offs)

    def encode_batch(self, texts, add_special_tokens=False):
        return [self.encode(t) for t in texts]

    def token_to_id(self, m):
        return self._id(m)

    def decode(self, ids, skip_special_tokens=False):
        inv = {v: k for k, v in self.vocab.items()}
        return "".join({"a1": "a", "a2": ""}.get(inv[i], inv[i]) for i in ids)


def row(tok, trace_chars):
    text = ("<|im_start|>user\nq<|im_end|>\n<|im_start|>assistant\n<|think|>" + "a" * trace_chars
            + "<|/think|>ok<|im_end|>\n<|endoftext|>")
    spans = convert.train_spans(text)
    enc = tok.encode(text)
    return {"id": "x/0", "text": text, "train_spans": [list(s) for s in spans], "effort": "1k",
            "input_ids": enc.ids, "loss_mask": convert.token_mask(spans, enc.offsets)}


def test_the_same_tokenizer_transfers_with_nothing_changed(tmp_path):
    tok = CharTok()
    f = tmp_path / "part.jsonl"
    f.write_text(json.dumps(row(tok, 900)) + "\n")
    r = tt.measure([str(f)], tok, tok)
    assert r["rows"] == r["old_reencode_equal"] == 1 and r["token_ratio_new_over_old"] == 1.0
    assert r["effort_changed"] == 0 and r["mask_violations_new"] == {} and r["trained_new"] == r["trained_old"]


def test_a_longer_trace_under_the_new_tokenizer_is_reported_as_a_tier_change(tmp_path):
    old, new = CharTok(), CharTok(double=True)
    f = tmp_path / "part.jsonl"
    f.write_text(json.dumps(row(old, 900)) + "\n")  # 900 + 2 marker tokens <= 1024 under old, 1802 under new
    r = tt.measure([str(f)], old, new)
    assert r["effort_changed"] == 1 and r["effort_transitions"] == {"1k->4k": 1}
    assert r["token_ratio_new_over_old"] > 1 and r["mask_violations_new"] == {}
    assert r["enter_limit"] == r["leave_limit"] == 0
