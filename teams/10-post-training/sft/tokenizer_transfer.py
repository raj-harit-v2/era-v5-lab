"""Does converted SFT data carry over to another tokenizer? (G10; written for the 15 Nov C3 -> p1536 notice.)

    python sft/tokenizer_transfer.py --old <C3 tokenizer.json> --new <p1536 tokenizer.json> --out <report.json> \
        <label>=<file>[,<file>...] ...

Rows need id, text, train_spans, effort, input_ids, loss_mask (convert.py parts and OCR-2 pack files both have them).
For every row: re-encode the stored text with the old tokenizer (must equal the stored ids: method check) and the new
one; rebuild the mask from the stored character spans (`convert.token_mask`) and run `check_pack_rows.check_row` on it;
recompute the effort tier from the new trace-token counts (`convert.pick_effort`); count rows crossing 32,768.
A tier change rewrites the row's `Reasoning effort:` line, so it means re-rendering, not only re-encoding.
The report holds counts only. Read-only; no file is changed.
"""
import argparse
import gzip
import json
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "chat-format"))
import check_pack_rows as cpr  # noqa: E402
import convert  # noqa: E402

LIMIT = 32768


def rows(files):
    for f in files:
        op = gzip.open if f.endswith(".gz") else open
        with op(f, "rt", encoding="utf-8") as s:
            for line in s:
                yield json.loads(line)


def tier(n):
    try:
        return convert.pick_effort(n)
    except convert.Skip:
        return "over64k"


def measure(files, old, new, chunk=64):
    ids_of = {m: new.token_to_id(m) for m in cpr.MARKERS}
    cache = {}

    def decode(ids):
        if ids[0] not in cache:
            cache[ids[0]] = new.decode(ids, skip_special_tokens=False)
        return cache[ids[0]]

    st = Counter()
    eff = Counter()
    viol = Counter()
    maxlen = {"old": 0, "new": 0}
    buf = []

    def flush():
        texts = [r["text"] for r in buf]
        e3 = old.encode_batch(texts, add_special_tokens=False)
        ep = new.encode_batch(texts, add_special_tokens=False)
        segs = [[m.group() for m in convert.TRACE.finditer(t)] for t in texts]
        flat = [s for ss in segs for s in ss]
        counts = iter([len(e.ids) for e in new.encode_batch(flat, add_special_tokens=False)] if flat else [])
        for r, a, b, ss in zip(buf, e3, ep, segs):
            st["rows"] += 1
            st["old_reencode_equal"] += a.ids == r["input_ids"]
            mask = convert.token_mask([tuple(s) for s in r["train_spans"]], b.offsets)
            bad, _ = cpr.check_row(b.ids, mask, ids_of, decode)
            viol.update(bad)
            n3, n15 = len(r["input_ids"]), len(b.ids)
            st["tokens_old"] += n3
            st["tokens_new"] += n15
            st["trained_old"] += sum(r["loss_mask"])
            st["trained_new"] += sum(mask)
            maxlen["old"], maxlen["new"] = max(maxlen["old"], n3), max(maxlen["new"], n15)
            st["over_limit_old"] += n3 > LIMIT
            st["over_limit_new"] += n15 > LIMIT
            st["enter_limit"] += n3 > LIMIT >= n15  # over the limit before, within it now: would join the pack
            st["leave_limit"] += n15 > LIMIT >= n3  # within before, over now: would leave the pack
            t15 = tier(sum(next(counts) for _ in ss)) if ss else convert.EFFORTS[0]
            eff[f"{r['effort']}->{t15}"] += 1
            st["effort_changed"] += t15 != r["effort"]
        buf.clear()

    for r in rows(files):
        buf.append(r)
        if len(buf) >= chunk:
            flush()
    if buf:
        flush()
    return {**dict(st), "max_len": maxlen, "token_ratio_new_over_old": round(st["tokens_new"] / st["tokens_old"], 5) if st["tokens_old"] else None,
            "mask_violations_new": dict(viol), "effort_transitions": dict(sorted(eff.items()))}


def main(argv=None) -> int:
    from tokenizers import Tokenizer  # noqa: PLC0415

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("sets", nargs="+", help="label=file[,file...]")
    a = ap.parse_args(argv)
    old, new = Tokenizer.from_file(a.old), Tokenizer.from_file(a.new)
    res = {}
    for arg in a.sets:
        label, files = arg.split("=", 1)
        t0 = time.monotonic()
        res[label] = measure(files.split(","), old, new)
        res[label]["seconds"] = round(time.monotonic() - t0, 1)
        a.out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        r = res[label]
        print(json.dumps({"set": label, "rows": r["rows"], "old_reencode_equal": r["old_reencode_equal"],
                          "ratio": r["token_ratio_new_over_old"], "effort_changed": r["effort_changed"],
                          "enter": r["enter_limit"], "leave": r["leave_limit"], "viol": r["mask_violations_new"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
