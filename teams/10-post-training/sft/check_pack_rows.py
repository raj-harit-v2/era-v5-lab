"""Independent loss-mask check of an admitted OCR-2 pack (G10).

    python check_pack_rows.py --pack pack.jsonl --sidecar joined.sidecar.jsonl --tokenizer c3.json \
        --report check.json [--dump sample.txt --per-source 20 --seed 0]

`pack_admission.py` proves that each row's ids and mask recompute from its text and train spans. This
checks what the mask MEANS, by walking the token ids alone with the chat markers as a state machine:

    every row       starts with <|im_start|> (untrained) and ends with <|endoftext|> (untrained: the EOS is
                    not a supervised token in SFT data v1; training covers the assistant body + <|im_end|>)
    every token     trained only inside an assistant turn (role read from the ids after <|im_start|>);
                    no <|im_start|> or <|endoftext|> is ever trained; no system or user token is trained
    every turn      an assistant turn's closing <|im_end|> is trained; other turns' <|im_end|> are not;
                    the role header (`assistant` + newline) is never trained
    every row       at least one shifted target (mask[1:]) and length <= --limit

Converted SFT parts (`convert.py` output, `.jsonl` or `.jsonl.gz`) carry the same `input_ids` / `loss_mask`, so the
same check runs on any SFT set: leave out `--sidecar` and rows are grouped by their `set` field instead of an OCR-2
source.

    python check_pack_rows.py --pack <set>.part0000.jsonl.gz ... --tokenizer c3.json --report check.json

It exits 1 on any violation. `--dump` writes, for `--per-source` rows per source (seeded), each token
beside its mask bit and its shifted label (the token it is the target for). The dump holds row text:
keep it private and out of Git. The report holds counts only.
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
from collections import Counter
from pathlib import Path

MARKERS = ("<|endoftext|>", "<|im_start|>", "<|im_end|>")


def check_row(ids: list, mask: list, ids_of: dict, decode) -> tuple[Counter, dict]:
    """Violations and per-role trained-token counts of one row, from ids and mask only."""
    bad: Counter = Counter()
    eot, start, end = ids_of["<|endoftext|>"], ids_of["<|im_start|>"], ids_of["<|im_end|>"]
    if len(ids) != len(mask) or any(m not in (0, 1) for m in mask):
        bad["mask_shape"] += 1
        return bad, {}
    if not ids or ids[0] != start or mask[0]:
        bad["first_token_not_untrained_im_start"] += 1
    if ids[-1] != eot or mask[-1]:
        bad["last_token_not_untrained_endoftext"] += 1
    if sum(mask[1:]) == 0:
        bad["no_shifted_target"] += 1
    trained_by_role: Counter = Counter()
    role, header, i = None, False, 0
    while i < len(ids):
        tok, m = ids[i], mask[i]
        if tok == start:
            if m:
                bad["im_start_trained"] += 1
            j, name = i + 1, ""  # the role name runs up to the first newline
            while j < len(ids) and "\n" not in name:
                if mask[j]:
                    bad["role_header_trained"] += 1
                name += decode([ids[j]])
                j += 1
            role, header = name.strip(), True
            i = j
            continue
        if tok == eot and m:
            bad["endoftext_trained"] += 1
        if tok == end:
            if role == "assistant" and not m:
                bad["assistant_im_end_not_trained"] += 1
            if role != "assistant" and m:
                bad[f"{role}_im_end_trained"] += 1
            if m:
                trained_by_role[role] += 1
            role = None
        elif m:
            trained_by_role[role] += 1
            if role != "assistant":
                bad[f"trained_outside_assistant:{role}"] += 1
        i += 1
    return bad, dict(trained_by_role)


def open_rows(path: Path):
    """A pack or converted part, plain or gzip."""
    return gzip.open(path, "rt", encoding="utf-8") if str(path).endswith(".gz") else open(path, encoding="utf-8")


def dump_row(stream, rid: str, source: str, ids: list, mask: list, tok_str) -> None:
    stream.write(f"\n=== {rid}  [{source}]  tokens {len(ids)}  trained {sum(mask)}  shifted targets {sum(mask[1:])}\n")
    stream.write("pos   id      mask  token                         | shifted label (target at pos-1 -> this token)\n")
    edges = {0, len(ids) - 1}
    for k in range(1, len(ids)):
        if mask[k] != mask[k - 1]:
            edges.update({k - 2, k - 1, k, k + 1})
    show = sorted(p for p in edges | set(range(min(12, len(ids)))) if 0 <= p < len(ids))
    last = -1
    for p in show:
        if p > last + 1:
            stream.write("  ...\n")
        label = f"target of pos {p - 1}" if p > 0 and mask[p] else ""
        stream.write(f"{p:<5} {ids[p]:<7} {mask[p]:<5} {tok_str(ids[p])!r:<29} | {label}\n")
        last = p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", type=Path, nargs="+", required=True, help="pack JSONL file(s)")
    ap.add_argument("--sidecar", type=Path, nargs="+", default=None,
                    help="joined.sidecar.jsonl of the same OCR-2 shard(s); leave out for converted SFT parts (grouped by `set`)")
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=32768)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--dump", type=Path, help="private decoded sample (holds text)")
    ap.add_argument("--per-source", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(args.tokenizer))
    ids_of = {m: tok.token_to_id(m) for m in MARKERS}
    if None in ids_of.values():
        print(f"check_pack_rows: the tokenizer lacks a marker: {ids_of}", file=sys.stderr)
        return 2
    cache: dict = {}

    def decode(ids):
        key = ids[0]
        if key not in cache:
            cache[key] = tok.decode(ids, skip_special_tokens=False)
        return cache[key]

    source_of = {}
    for path in args.sidecar or ():
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                entry = json.loads(line)
                source_of[entry["rendered_id"]] = f"{entry['source_row_key'][2]}/{entry['split_membership']}"
    violations: Counter = Counter()
    rows_bad: Counter = Counter()
    trained_by_role: Counter = Counter()
    by_source: Counter = Counter()
    max_len, rows, tokens, trained = 0, 0, 0, 0
    sample_ids: dict = {}
    def source_for(row):
        return source_of.get(row["id"], "(no sidecar entry)") if args.sidecar else row.get("set", "(no set field)")

    for path in args.pack:
        with open_rows(path) as stream:
            for line in stream:
                row = json.loads(line)
                ids, mask = row["input_ids"], row["loss_mask"]
                source = source_for(row)
                bad, roles = check_row(ids, mask, ids_of, decode)
                if len(ids) > args.limit:
                    bad["over_limit"] += 1
                if source == "(no sidecar entry)":
                    bad["no_sidecar_entry"] += 1
                violations.update(bad)
                rows_bad[source] += bool(bad)
                trained_by_role.update(roles)
                by_source[source] += 1
                sample_ids.setdefault(source, []).append(row["id"])
                rows, tokens, trained = rows + 1, tokens + len(ids), trained + sum(mask)
                max_len = max(max_len, len(ids))
    rng = random.Random(args.seed)
    picked = {s: set(rng.sample(v, min(args.per_source, len(v)))) for s, v in sorted(sample_ids.items())}
    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as out:
            out.write("PRIVATE: decoded pack rows (text). Not for Git.\n")
            for path in args.pack:
                with open_rows(path) as stream:
                    for line in stream:
                        row = json.loads(line)
                        source = source_for(row)
                        if row["id"] in picked.get(source, ()):
                            dump_row(out, row["id"], source, row["input_ids"], row["loss_mask"], tok.id_to_token)
    report = {"schema": "g10-ocr2-pack-row-check/1", "rows": rows, "tokens": tokens, "trained_tokens": trained,
              "max_length": max_len, "limit": args.limit, "by_source": dict(sorted(by_source.items())),
              "trained_tokens_by_role": {str(k): v for k, v in sorted(trained_by_role.items(), key=lambda kv: str(kv[0]))},
              "violations": dict(sorted(violations.items())), "rows_with_violations_by_source": dict(sorted(rows_bad.items())),
              "sampled_per_source": {s: len(v) for s, v in picked.items()}, "seed": args.seed,
              "marker_ids": ids_of, "ok": not violations and rows > 0}
    args.report.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("ok", "rows", "max_length", "violations", "trained_tokens_by_role")}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
