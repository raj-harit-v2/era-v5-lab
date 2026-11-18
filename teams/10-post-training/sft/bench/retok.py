"""Re-tokenise G10 chat-format v0 rows for a surrogate model, keeping G10's loss mask (WP3 bench).

The pack rows carry `text` (G10 marker surfaces) and `train_spans` (character spans, `convert.train_spans`).
This module maps every G10 marker to ONE existing special token of the surrogate tokenizer, so no embedding row
is added (a later Deletion Tuning run must be able to say "no weight was written"), re-tokenises in one batch and
rebuilds the 0/1 token mask with the same `train_spans` and `token_mask` functions imported from `sft/convert.py`.

Marker table for HuggingFaceTB/SmolLM2-135M @ 93efa2f097d58c2a74874c7e644dbc9b0cee75a2 (checked against its
tokenizer_config.json `added_tokens_decoder`, all `special: true`; each surface encodes to exactly one id):

    G10 marker          surrogate surface    id   note
    <|endoftext|>       <|endoftext|>        0    native (also the model's bos/eos/unk)
    <|im_start|>        <|im_start|>         1    native, same surface
    <|im_end|>          <|im_end|>           2    native, same surface
    <|think|>           <jupyter_script>     15   existing special, repurposed
    <|/think|>          <empty_output>       16   existing special, repurposed
    tool markers (4)    not mapped           -    rows that contain one are rejected (`unmapped_marker`)

Ids 15 and 16 were picked because their embedding rows have the same norm (3.308) as ids 1, 2, 5 and 7-16, which
look untrained in the base checkpoint, while ids 0, 3, 4 and 6 differ (6 is 6.745). A row whose content already
contains any surrogate special surface is rejected (`surrogate_special_in_content`), so a special id in the output
always means a G10 marker.

Target bytes: for bits per byte, the denominator is the UTF-8 bytes of the G10-surface assistant spans (body and its
`<|im_end|>`, counted once each; a marker counts its G10 surface). This is the same for the base and every trained checkpoint.

    python retok.py --tokenizer <tokenizer.json> --in split.jsonl --out split.tok.jsonl
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SFT = HERE.parent


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


convert = _load("g10_convert_for_bench", SFT / "convert.py")
render = convert.render
T = render.T

SURROGATE = {
    "model": "HuggingFaceTB/SmolLM2-135M",
    "revision": "93efa2f097d58c2a74874c7e644dbc9b0cee75a2",
    "tokenizer_sha256": "9ca9acddb6525a194ec8ac7a87f24fbba7232a9a15ffa1af0c1224fcd888e47c",
}
# G10 marker name -> (surrogate surface, surrogate id)
MARKER_MAP: dict[str, tuple[str, int]] = {
    "endoftext": ("<|endoftext|>", 0),
    "im_start": ("<|im_start|>", 1),
    "im_end": ("<|im_end|>", 2),
    "think": ("<jupyter_script>", 15),
    "think_end": ("<empty_output>", 16),
}
UNMAPPED = ("tool_call", "tool_call_end", "tool_result", "tool_result_end")
SURROGATE_SPECIALS = (
    "<|endoftext|>", "<|im_start|>", "<|im_end|>", "<repo_name>", "<reponame>", "<file_sep>", "<filename>",
    "<gh_stars>", "<issue_start>", "<issue_comment>", "<issue_closed>", "<jupyter_start>", "<jupyter_text>",
    "<jupyter_code>", "<jupyter_output>", "<jupyter_script>", "<empty_output>",
)
IM_END_ID = MARKER_MAP["im_end"][1]
EOS_ID = MARKER_MAP["endoftext"][1]

_G10_SURFACE_TO_NAME = {T[name]: name for name in (*MARKER_MAP, *UNMAPPED)}
_G10_RE = re.compile("|".join(re.escape(s) for s in sorted(_G10_SURFACE_TO_NAME, key=len, reverse=True)))
_SURR_TO_G10 = {surf: T[name] for name, (surf, _) in MARKER_MAP.items()}
_SURR_RE = re.compile("|".join(re.escape(s) for s in sorted(_SURR_TO_G10, key=len, reverse=True)))
# surfaces that may not appear in content: every surrogate special that is not also a G10 marker surface
_FOREIGN = tuple(s for s in SURROGATE_SPECIALS if s not in _G10_SURFACE_TO_NAME)


class RetokReject(ValueError):
    """The row cannot be mapped to the surrogate without ambiguity."""


def check_tokenizer(tok) -> None:
    """Every mapped surface must be one special token with the expected id."""
    for name, (surf, want) in MARKER_MAP.items():
        ids = tok.encode(surf, add_special_tokens=False).ids
        if ids != [want]:
            raise RuntimeError(f"surrogate tokenizer maps {surf} ({name}) to {ids}, expected [{want}]")


def to_surrogate(text: str) -> tuple[str, list[tuple[int, int, int]]]:
    """Replace G10 marker surfaces. Returns (surrogate text, [(pack_start, surr_start, pack_len, surr_len)...])."""
    for surf in _FOREIGN:
        if surf in text:
            raise RetokReject("surrogate_special_in_content")
    out, moves, pos, delta = [], [], 0, 0
    for m in _G10_RE.finditer(text):
        name = _G10_SURFACE_TO_NAME[m.group()]
        if name not in MARKER_MAP:
            raise RetokReject("unmapped_marker")
        surf = MARKER_MAP[name][0]
        out.append(text[pos : m.start()])
        out.append(surf)
        moves.append((m.start(), m.start() + delta, len(m.group()), len(surf)))
        delta += len(surf) - len(m.group())
        pos = m.end()
    out.append(text[pos:])
    return "".join(out), moves


def from_surrogate(text: str) -> str:
    """Inverse surface map (used on generated text; no other surrogate special may be present)."""
    return _SURR_RE.sub(lambda m: _SURR_TO_G10[m.group()], text)


def _offset_mappers(moves):
    """Pack offset -> surrogate offset and back, for offsets at marker edges or outside markers."""
    pstarts = [m[0] for m in moves]
    sstarts = [m[1] for m in moves]

    def p2s(p: int) -> int:
        i = bisect.bisect_right(pstarts, p) - 1
        if i < 0:
            return p
        ps, ss, pl, sl = moves[i]
        if p < ps + pl and p != ps:
            raise ValueError("offset inside a marker")
        return ss + (p - ps) if p == ps else ss + sl + (p - ps - pl)

    def s2p(s: int) -> int:
        i = bisect.bisect_right(sstarts, s) - 1
        if i < 0:
            return s
        ps, ss, pl, sl = moves[i]
        if s < ss + sl:  # inside or at the start of a surrogate marker: snap to the marker's start/end
            return ps if s == ss else ps + pl
        return ps + pl + (s - ss - sl)

    return p2s, s2p


def span_bytes(text: str, spans) -> int:
    """UTF-8 bytes of the G10-surface train spans, each byte counted once.

    (Until 14 Nov evening this summed the bytes under every trained token's offsets. Byte-fallback tokens of one
    character share that character's offsets, so non-ASCII text was over-counted; tokens and masks were unaffected.)
    """
    return sum(len(text[a:b].encode("utf-8")) for a, b in spans)


def target_bytes_of(surrogate_text: str) -> int:
    """The same count recomputed from a tokenised row's `surrogate_text` (reverse marker map + convert.train_spans)."""
    g10 = from_surrogate(surrogate_text)
    return span_bytes(g10, convert.train_spans(g10))


def retokenize(rows: list[dict], tok, max_tokens: int | None = None) -> tuple[list[dict], dict]:
    """Map + batch-encode rows. Returns (tokenised rows, rejection counts). Input rows need `text`, `train_spans`.

    Output row = input row minus C3 ids/mask, plus `surrogate_text`, `input_ids`, `loss_mask`, `prompt_len`,
    `target_tokens`, `target_bytes`. Rows longer than `max_tokens` are rejected as `over_max_tokens`.
    """
    check_tokenizer(tok)
    rejected: dict[str, int] = {}
    prepared = []
    for row in rows:
        try:
            spans = [tuple(s) for s in row["train_spans"]]
            if spans != convert.train_spans(row["text"]):
                raise RetokReject("pack_spans_differ_from_convert")
            surr, moves = to_surrogate(row["text"])
            p2s, s2p = _offset_mappers(moves)
            sspans = [(p2s(a), p2s(b)) for a, b in spans]
            if sspans != convert.train_spans(surr):
                raise RetokReject("mapped_spans_differ_from_convert")
            prepared.append((row, surr, moves, spans, sspans, s2p))
        except RetokReject as exc:
            rejected[str(exc)] = rejected.get(str(exc), 0) + 1
    encs = tok.encode_batch([p[1] for p in prepared], add_special_tokens=False)
    out = []
    for (row, surr, moves, spans, sspans, s2p), enc in zip(prepared, encs):
        ids, offsets = enc.ids, enc.offsets
        if max_tokens is not None and len(ids) > max_tokens:
            rejected["over_max_tokens"] = rejected.get("over_max_tokens", 0) + 1
            continue
        n_special = sum(1 for t in ids if t < len(SURROGATE_SPECIALS))
        if n_special != len(moves):
            rejected["special_count_mismatch"] = rejected.get("special_count_mismatch", 0) + 1
            continue
        mask = convert.token_mask(sspans, offsets)
        if sum(mask[1:]) == 0:
            rejected["zero_targets"] = rejected.get("zero_targets", 0) + 1
            continue
        tgt = [i for i, m in enumerate(mask) if m]
        tbytes = span_bytes(row["text"], spans)
        first = sspans[0][0]
        prompt_len = next(i for i, (a, _) in enumerate(offsets) if a >= first)
        if offsets[prompt_len - 1][1] > first:
            rejected["prompt_boundary_straddled"] = rejected.get("prompt_boundary_straddled", 0) + 1
            continue
        new = {k: v for k, v in row.items() if k not in ("input_ids", "loss_mask")}
        new.update(surrogate_text=surr, input_ids=ids, loss_mask=mask, prompt_len=prompt_len,
                   target_tokens=len(tgt), target_bytes=tbytes)
        out.append(new)
    return out, rejected


def load_tokenizer(path: str | Path):
    from tokenizers import Tokenizer

    data = Path(path).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    tok = Tokenizer.from_str(data.decode("utf-8"))
    check_tokenizer(tok)
    return tok, sha


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int)
    args = ap.parse_args(argv)
    tok, sha = load_tokenizer(args.tokenizer)
    if sha != SURROGATE["tokenizer_sha256"]:
        print(f"warning: tokenizer sha256 {sha} is not the pinned SmolLM2 one", file=sys.stderr)
    rows = [json.loads(l) for l in Path(args.inp).read_text(encoding="utf-8").splitlines() if l.strip()]
    out, rejected = retokenize(rows, tok, args.max_tokens)
    blob = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out).encode("utf-8")
    Path(args.out).write_bytes(blob)
    print(json.dumps({"rows_in": len(rows), "rows_out": len(out), "rejected": rejected, "tokenizer_sha256": sha,
                      "sha256": hashlib.sha256(blob).hexdigest()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
