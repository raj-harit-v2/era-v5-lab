"""Build RL data v1 task records from the pinned bytes, with the PR #54 builders deciding what is kept.

The keep/drop decision is made only by teams/10-post-training/rl-data/build.py (`other_judge_rows`) and
build_math.py (`math_rows`), imported unchanged. This wrapper feeds them one row at a time so it can
  - attach provenance to every kept record (dataset, revision, split, file, file sha256, source ordinal, licence),
  - name the reason for every dropped row, with a cross-check: the wrapper's own reason must say "keep" exactly
    when the builder kept the row (any disagreement stops the build),
  - enforce the hard limits: no Codeforces-sourced rows (code_contests source == 2), MATH train files only.

    python build_v1.py <rl-data dir> <pins_verified.json> <cc-pinned-manifest.json> <math dir> <math_pin.json> <out dir>
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

RLDATA, PINS, CC_MANIFEST, MATH_DIR, MATH_PIN, OUT = map(Path, sys.argv[1:7])
sys.path.insert(0, str(RLDATA))
import build  # noqa: E402  (PR #54, unchanged)
import build_math  # noqa: E402  (PR #54, unchanged)

pins = json.loads(PINS.read_text())
assert pins["all_ok"], "pins_verified.json says a file failed its pin; refusing to build"
pinned_sha = {(r["source"], r["file"]): r["sha256"] for r in pins["files"]}

# The four non-Codeforces judges build.py documents for --sources. Codeforces (2) is excluded by hard limit 3.
JUDGES = {build.JUDGES[j] for j in ("aizu", "atcoder", "codechef", "hackerearth")}
MAX_TESTS = 20  # build.py default
CC_COLS = ["name", "description", "public_tests", "private_tests", "generated_tests", "source", "cf_rating",
           "cf_contest_id", "cf_index", "input_file", "output_file", "difficulty"]


def file_sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def cc_reason(r):
    """Why build.other_judge_rows would drop this row (None = it keeps it). Order mirrors build.py."""
    if r.get("source") == build.JUDGES["codeforces"]:
        return "codeforces_source_excluded (hard limit: Team 9 pool confirmation open)"
    if r.get("source") not in JUDGES:
        return f"judge_not_in_builder_list ({ {v: k for k, v in build.JUDGES.items()}.get(r.get('source'))})"
    if r.get("input_file") or r.get("output_file"):
        return "file_io_not_stdio"
    if not r.get("description"):
        return "no_statement"
    n = sum(len((r.get(k) or {}).get("input", [])) for k in ("public_tests", "private_tests", "generated_tests"))
    if n < 3:
        return "fewer_than_3_tests"
    return None


def build_cc():
    import pyarrow.parquet as pq
    m = json.loads(CC_MANIFEST.read_text())["sources"]["code_contests/train"]
    meta = build.SOURCES["code_contests"]
    out, reasons, seen, rows_in, renamed, by_judge = [], Counter(), set(), 0, 0, Counter()
    for f in m["files"]:
        p = Path(f["path"])
        sha = file_sha(p)
        assert sha == pinned_sha[("code_contests", p.name)] == f["sha256"], p.name
        rows = pq.read_table(p, columns=CC_COLS).to_pylist()
        assert len(rows) == f["rows"], (p.name, len(rows), f["rows"])
        for ordinal, r in enumerate(rows):
            rows_in += 1
            why = cc_reason(r)
            if r.get("source") == build.JUDGES["codeforces"]:
                got = []  # never passed to the builder
            else:
                got = build.other_judge_rows([r], JUDGES, MAX_TESTS, seen)
            if bool(got) != (why is None):
                raise SystemExit(f"reason/builder disagreement at {p.name}#{ordinal}: reason={why} kept={bool(got)}")
            if not got:
                reasons[why] += 1
                continue
            t = got[0]
            base = f"cc-{t['judge']}-" + "".join(c if c.isalnum() else "_" for c in (r.get("name") or "noname"))[:60]
            renamed += t["id"] != base  # builder added -2, -3 ... because an earlier row had the same name
            n_tests = sum(len((r.get(k) or {}).get("input", [])) for k in ("public_tests", "private_tests",
                                                                           "generated_tests"))
            by_judge[t["judge"]] += 1
            t["provenance"] = {"dataset": meta["dataset"], "revision": m["revision"], "split": "train",
                               "file": p.name, "file_sha256": sha, "source_ordinal": ordinal,
                               "licence": meta["licence"], "generator": meta["generator"],
                               "tests_available": n_tests, "tests_kept": len(t["tests"])}
            out.append(t)
    return out, {"rows_in": rows_in, "rows_out": len(out), "rejections": dict(reasons.most_common()),
                 "kept_by_judge": dict(by_judge.most_common()), "ids_suffixed_for_duplicate_names": renamed}


def build_math_records():
    import pyarrow.parquet as pq
    mp = json.loads(MATH_PIN.read_text())
    out, reasons, rows_in, by_subject = [], Counter(), 0, Counter()
    for s in build_math.SUBJECTS:
        files = sorted((MATH_DIR / s).glob("train-*.parquet"))
        assert len(files) == 1 and not list((MATH_DIR / s).glob("test-*")), s  # train only, one file per subject
        p = files[0]
        rel = f"{s}/{p.name}"
        sha = file_sha(p)
        assert sha == pinned_sha[("hendrycks_math", rel)], rel
        rows = pq.read_table(p, columns=["problem", "solution", "level"]).to_pylist()
        got, skipped = build_math.math_rows(s, rows)  # the builder's ids are math-<subject>-<row ordinal>
        rows_in += len(rows)
        # Attribute every skipped row (the builder only counts them).
        kept_ord = {int(t["id"].rsplit("-", 1)[1]) for t in got}
        for i, r in enumerate(rows):
            if i in kept_ord:
                continue
            reasons["no_problem" if not r.get("problem") else "no_boxed_answer_in_solution"] += 1
        assert len(rows) - len(kept_ord) == skipped
        for t in got:
            t["provenance"] = {"dataset": mp["dataset"], "revision": mp["revision"], "split": "train",
                               "file": rel, "file_sha256": sha, "source_ordinal": int(t["id"].rsplit("-", 1)[1]),
                               "licence": build_math.META["licence"], "generator": build_math.META["generator"]}
            by_subject[s] += 1
        out += got
    return out, {"rows_in": rows_in, "rows_out": len(out), "rejections": dict(reasons.most_common()),
                 "kept_by_subject": dict(by_subject)}


def write(path, recs):
    with open(path, "w", encoding="utf-8") as f:
        for t in recs:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cc, cc_counts = build_cc()
    math, math_counts = build_math_records()
    for name, recs in (("cc", cc), ("math", math)):
        ids = [t["id"] for t in recs]
        assert len(ids) == len(set(ids)), f"duplicate ids in {name}"
        assert all(t.get("provenance", {}).get("file_sha256") for t in recs)
    assert not any(t.get("judge") == "codeforces" or "Codeforces" in t["source"] for t in cc)
    write(OUT / "cc_tasks.jsonl", cc)
    write(OUT / "math_tasks.jsonl", math)
    # Decontamination inputs: id + text. code_contests: the statement. MATH: problem + blank line + reference
    # answer (the answer drives the reward, so it is checked too; same convention as the 5 Nov run).
    write(OUT / "cc_text.jsonl", [{"id": t["id"], "text": t["statement"]} for t in cc])
    write(OUT / "math_text.jsonl", [{"id": t["id"], "text": t["problem"] + "\n\n" + t["answer"]} for t in math])
    # Exact duplicate statements (kept by the builder; reported, not removed).
    dup = {n: sum(c - 1 for c in Counter(hashlib.sha256(t[k].encode()).hexdigest() for t in r).values() if c > 1)
           for n, r, k in (("code_contests", cc, "statement"), ("math", math, "problem"))}
    counts = {"code_contests": cc_counts, "hendrycks_math_train": math_counts,
              "exact_duplicate_texts_beyond_first": dup,
              "outputs": {p.name: file_sha(p) for p in sorted(OUT.glob("*.jsonl"))}}
    (OUT / "build_counts.json").write_text(json.dumps(counts, indent=1))
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
