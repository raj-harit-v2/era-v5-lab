"""Tests for check_pack_rows.py (G10): the mask check reads roles from the ids alone.

    pytest teams/10-post-training/sft/test_check_pack_rows.py -q

No network, no tokenizer file: a toy vocabulary of placeholder strings stands in. Tests only.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_pack_rows as cpr  # noqa: E402

VOCAB = {0: "<|endoftext|>", 1: "<|im_start|>", 2: "<|im_end|>", 3: "system", 4: "user", 5: "assistant", 6: "\n", 7: "x", 8: "y"}
IDS_OF = {v: k for k, v in VOCAB.items() if v.startswith("<|")}


def decode(ids):
    return "".join(VOCAB[i] for i in ids)


# <|im_start|>system\nx<|im_end|>\n<|im_start|>user\nx<|im_end|>\n<|im_start|>assistant\nxy<|im_end|>\n<|endoftext|>
ROW = [1, 3, 6, 7, 2, 6, 1, 4, 6, 7, 2, 6, 1, 5, 6, 7, 8, 2, 6, 0]
GOOD = [0] * 15 + [1, 1, 1] + [0, 0]


def check(mask, ids=ROW):
    return cpr.check_row(ids, mask, IDS_OF, decode)


def test_a_correct_row_has_no_violation_and_trains_only_the_assistant():
    bad, roles = check(GOOD)
    assert not bad and roles == {"assistant": 3}


def flip(pos):
    mask = list(GOOD)
    mask[pos] = 1 - mask[pos]
    return mask


def test_each_kind_of_wrong_mask_is_named():
    assert check(flip(3))[0] == {"trained_outside_assistant:system": 1}
    assert check(flip(9))[0] == {"trained_outside_assistant:user": 1}
    assert check(flip(10))[0] == {"user_im_end_trained": 1}
    assert check(flip(17))[0] == {"assistant_im_end_not_trained": 1}
    assert check(flip(13))[0] == {"role_header_trained": 1}
    assert check(flip(19))[0] == {"last_token_not_untrained_endoftext": 1, "endoftext_trained": 1,
                                  "trained_outside_assistant:None": 1}  # the EOS sits after every turn
    assert check(flip(0))[0] == {"first_token_not_untrained_im_start": 1, "im_start_trained": 1}
    assert check([0] * len(ROW))[0] == {"no_shifted_target": 1, "assistant_im_end_not_trained": 1}
    assert check(GOOD[:-1])[0] == {"mask_shape": 1}
    assert check(GOOD[:-1], ROW[:-1])[0] == {"last_token_not_untrained_endoftext": 1}


def _toy_tokenizer(tmp_path):
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel

    path = tmp_path / "toy.json"
    Tokenizer(WordLevel({v: k for k, v in VOCAB.items()}, unk_token="x")).save(str(path))
    return path


def test_converted_gz_parts_are_checked_without_a_sidecar_and_grouped_by_set(tmp_path):
    import gzip
    import json

    part = tmp_path / "sft-toy.part0000.jsonl.gz"
    rows = [{"id": "sft-toy/0", "set": "sft-toy", "input_ids": ROW, "loss_mask": GOOD},
            {"id": "sft-toy/1", "set": "sft-toy", "input_ids": ROW, "loss_mask": flip(9)}]
    with gzip.open(part, "wt", encoding="utf-8") as out:
        out.writelines(json.dumps(r) + "\n" for r in rows)
    tok = _toy_tokenizer(tmp_path)
    report = tmp_path / "check.json"
    assert cpr.main(["--pack", str(part), "--tokenizer", str(tok), "--report", str(report)]) == 1
    got = json.loads(report.read_text())
    assert got["by_source"] == {"sft-toy": 2} and got["rows_with_violations_by_source"] == {"sft-toy": 1}
    assert got["violations"] == {"trained_outside_assistant:user": 1} and "no_sidecar_entry" not in got["violations"]
    with gzip.open(part, "wt", encoding="utf-8") as out:
        out.write(json.dumps(rows[0]) + "\n")
    assert cpr.main(["--pack", str(part), "--tokenizer", str(tok), "--report", str(report)]) == 0
    assert json.loads(report.read_text())["ok"] is True
