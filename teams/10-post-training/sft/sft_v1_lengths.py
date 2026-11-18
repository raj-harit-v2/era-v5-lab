"""Context-length table for one SFT data v1 set: how many rows and tokens fit a given context (G10, 16 Nov 2026).

    python sft/sft_v1_lengths.py --set sft-dolly-15k --area general --rows <private parts>/*.jsonl.gz \
        [--keep-ids <private admit dir>/sft-dolly-15k.kept_ids.txt] [--status pack] \
        --tokenizer-sha256 e6b93a93... --out sft/results/sft_v1_lengths_p1536/sft-dolly-15k.json

Rows are JSONL (plain or .gz) with either `input_ids` + `loss_mask` (a conversion or a pack) or `tokens` + `targets`
(per-row stats of a pack build, with a `status` field). Only rows that are in the set as admitted are counted:
`--keep-ids` (one id per line) and/or `--status` (rows whose `status` equals it). A row fits a context of L tokens
when its whole token count is <= L (the chat format has no row split: a cut row loses its answer and its <|im_end|>).
`tokens_if_truncated` is what a cut-at-L policy would keep, for comparison only.

Output (public): counts only, no ids or text. Shifted targets are `loss_mask[1:]` summed, as `pack_admission.py`
counts them.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np

SCHEMA = "g10-sft-v1-lengths/1"
LIMITS = (2048, 4096, 8192, 32768)


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else open(path, encoding="utf-8")


def read_lengths(paths: list[Path], keep: set[str] | None, status: str | None,
                 exclude_families: frozenset[str] | None = None) -> tuple[np.ndarray, np.ndarray, int]:
    toks, tgts, seen = [], [], 0
    for path in paths:
        with open_text(path) as f:
            for line in f:
                row = json.loads(line)
                seen += 1
                if keep is not None and row["id"] not in keep:
                    continue
                if status is not None and row.get("status") != status:
                    continue
                if exclude_families and row.get("family") in exclude_families:
                    continue  # e.g. the evaluation firewall (eval_firewall.py): rows dropped from SFT training
                if "input_ids" in row:
                    toks.append(len(row["input_ids"]))
                    tgts.append(sum(row["loss_mask"][1:]))
                else:
                    toks.append(row["tokens"])
                    tgts.append(row["targets"])
    return np.asarray(toks, dtype=np.int64), np.asarray(tgts, dtype=np.int64), seen


def table(tokens: np.ndarray, targets: np.ndarray, limits=LIMITS) -> dict:
    n, total, total_t = len(tokens), int(tokens.sum()), int(targets.sum())
    out = {"rows": n, "tokens": total, "shifted_targets": total_t, "by_limit": {}}
    if n:
        q = np.percentile(tokens, [50, 90, 99]).round().astype(int).tolist()
        out["length"] = {"min": int(tokens.min()), "p50": q[0], "p90": q[1], "p99": q[2], "max": int(tokens.max()),
                         "mean": round(float(tokens.mean()), 1)}
    for L in limits:
        fit = tokens <= L
        out["by_limit"][str(L)] = {
            "rows_fit": int(fit.sum()), "rows_fit_share": round(float(fit.mean()), 6) if n else None,
            "tokens_fit": int(tokens[fit].sum()), "tokens_fit_share": round(float(tokens[fit].sum()) / total, 6) if total else None,
            "shifted_targets_fit": int(targets[fit].sum()),
            "tokens_if_truncated": int(np.minimum(tokens, L).sum()),
        }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", required=True)
    ap.add_argument("--area", required=True)
    ap.add_argument("--rows", type=Path, nargs="+", required=True)
    ap.add_argument("--keep-ids", type=Path)
    ap.add_argument("--status")
    ap.add_argument("--exclude-families", type=Path, help="family-key list (eval_firewall.py format): rows of these families are left out")
    ap.add_argument("--exclude-families-sha256", help="pinned sha256 of --exclude-families")
    ap.add_argument("--tokenizer-sha256", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    keep = None
    if a.keep_ids:
        keep = {line.strip() for line in a.keep_ids.read_text(encoding="utf-8").splitlines() if line.strip()}
    excl = None
    if a.exclude_families:
        import eval_firewall  # noqa: PLC0415 (same folder)
        excl = eval_firewall.load_families(a.exclude_families, a.exclude_families_sha256)
    tokens, targets, seen = read_lengths(sorted(a.rows), keep, a.status, excl)
    if keep is not None and len(tokens) != len(keep):
        raise SystemExit(f"{len(tokens)} rows matched, but --keep-ids lists {len(keep)}")
    out = {"schema": SCHEMA, "set": a.set, "area": a.area, "tokenizer_sha256": a.tokenizer_sha256,
           "rows_read": seen, "filter": {"keep_ids": bool(keep), "status": a.status,
                                          **({"exclude_families_sha256": eval_firewall.sha256_file(a.exclude_families),
                                              "exclude_families": len(excl)} if excl else {})},
           "fit_rule": "a row fits L when its whole token count is <= L", "note": a.note, **table(tokens, targets)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    fits = ", ".join(f"{L}: {v['rows_fit_share']:.1%} rows / {v['tokens_fit_share']:.1%} tokens"
                     for L, v in out["by_limit"].items()) if out["rows"] else "no rows"
    print(f"{a.set}: {out['rows']} rows, {out['tokens']:,} tokens; fit {fits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
