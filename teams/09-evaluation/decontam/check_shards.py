"""Run the full shard check on many training shards in one command (G9).

    python fetch_shards.py shard_links.tsv --out <shards>          # step 1, the only step with network
    python check_shards.py <shards> --tokenizer <p1536>/tokenizer.json --work <dir> \
        --compare ../results/decontam_shards.md                    # step 2, no network
    python check_shards.py <shards> ... --only code-cpp-train-000000 ind-gu-fw2-train-000000

For each shard this runs the same chain as results/decontam_shards.md, with the scripts unchanged:
decode_shard.py (checks the shard against its manifest) -> decontam_check.py (full set: no --benchmarks, --tags or
--exclude) and canary_scan.py on the decoded text. It does not download and needs no network, so it can run as a job
that reads only its inputs.

Speed. All steps of all shards share one pool of --jobs worker processes:
  - the biggest shards (by .bin size) start first, so a big shard does not start last and hold up the end;
  - a decoded shard is cut into parts of about --part-tokens tokens (whole documents, in shard order), and
    decontam_check.py runs on each part in its own process, so one big shard uses many cores. The flagged count is
    the sum over the parts. A document is checked alone, so the parts give the same result as one run on the shard;
  - canary_scan.py reads all parts of a shard in one process.
--jobs defaults to the number of cores, but at most one per 2.5 GB of memory (one decontam_check.py holds the
fingerprint set, about 1.4 GB). Peak disk use is about two decoded copies of --jobs shards.

  --compare  a markdown file with shard table rows (shard_id, payload_sha256, docs, tokens). Each checked shard must
             match its first row there; a mismatch or a missing row is reported and makes the exit code 1.

A .bin in the folder without its three other shard files counts as an incomplete download and fails the run, so keep
only shards in the folder. Decoded text in <work>/text from an earlier or stopped run is deleted at the start, and at
the end unless --keep-text is given (--keep-text keeps it until the next run on the folder).

Results go to <work>/results/<shard_id>.json, one file per shard, written only when all steps finish. A second run
skips a shard that already has a result for the same tokenizer, fingerprint set (set_sha256), check code (code_sha256:
the scripts and the tokenizers version) and shard payload (resume after a stop). One run at a time can use a --work
folder: a second run stops with an error. Use a local --work folder: the lock is not reliable on a network drive. Use
--force to check again. The decoded text is deleted after the checks unless --keep-text is given.

At the end it prints a markdown table in the format of results/decontam_shards.md, plus the fingerprint set_sha256
and the canary count. Exit code: 0 when every shard passed with 0 flagged and 0 canary hits and matched --compare;
1 when a shard failed a step, has a hit or does not match; 2 for a usage error. It never prints document text.
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHARD_EXTS = (".bin", ".idx.npy", ".docs.parquet", ".json")
GB_PER_JOB = 2.5
# The code a result depends on: this runner, the three scripts and the modules they import. Its sha256 (with the
# tokenizers version, which the decode uses) is stored in each result, so a code change checks the shards again.
CODE_FILES = ("check_shards.py", "decode_shard.py", "decontam_check.py", "canary_scan.py", "fpset.py", "normalize.py",
              "lab_canary.py", "g1_spec_v1_normalize.py")
LOCK_NAME = ".check_shards.lock"
SPLITS_AT_ONCE = 2  # a split holds one decoded shard in this process: limit how many at a time
SET_LINE = re.compile(r"^fingerprints (\S+) set_sha256 ([0-9a-f]{64}) \((.+)\)$", re.M)
DECONTAM_LINE = re.compile(r"^docs (\d+) flagged (\d+) ", re.M)
CANARY_COUNT = re.compile(r"^canaries (\d+) from (.+)$", re.M)
CANARY_LINE = re.compile(r"^docs (\d+) with_canary (\d+) hits (\d+)", re.M)
# A table row: an optional "| # |" column, then shard_id, payload_sha256, docs, tokens.
ROW = re.compile(r"^\|(?:\s*\d+\s*\|)?\s*`?([a-z0-9-]+-\d{6})`?\s*\|\s*`?([0-9a-f]{64})`?\s*\|\s*([\d,]+)\s*\|"
                 r"\s*([\d,]+)\s*\|")


class CheckError(Exception):
    pass


def default_jobs():
    cores = os.cpu_count() or 1
    try:
        mem_gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
    except (ValueError, OSError, AttributeError):  # no sysconf (Windows): use the core count with a safe cap
        return max(1, min(cores, 4))
    return max(1, min(cores, int(mem_gb // GB_PER_JOB)))


def fingerprint_set_sha(folder):
    """set_sha256 from a fingerprint set's MANIFEST.json (decontam_check.py checks it against SHA256SUMS)."""
    try:
        sha = json.loads((Path(folder) / "MANIFEST.json").read_text(encoding="utf-8"))["set_sha256"]
    except (OSError, ValueError, KeyError) as e:
        raise CheckError(f"{folder}: no fingerprint set with a set_sha256 ({type(e).__name__}: {e})") from None
    if not re.fullmatch(r"[0-9a-f]{64}", str(sha)):
        raise CheckError(f"{folder}: set_sha256 {sha!r} is not a sha256")
    return sha


def default_fingerprints():
    """The set decontam_check.py and canary_scan.py use without --fingerprints (fpset.VERSION)."""
    if str(HERE) not in sys.path:  # python -I leaves the script's folder out of sys.path
        sys.path.insert(0, str(HERE))
    from fpset import VERSION

    return HERE.parent / "fingerprints" / VERSION


def code_sha256():
    """sha256 of CODE_FILES (line ends read as LF, so a Windows checkout gives the same value) and the tokenizers
    version."""
    h = hashlib.sha256()
    for name in CODE_FILES:
        data = (HERE / name).read_bytes().replace(b"\r\n", b"\n")
        h.update(f"{name} {hashlib.sha256(data).hexdigest()}\n".encode())
    try:
        from importlib.metadata import version

        tok_version = version("tokenizers")
    except Exception:  # not installed: the decode step reports it
        tok_version = "unknown"
    h.update(f"tokenizers {tok_version}\n".encode())
    return h.hexdigest()


def lock_work(work):
    """Hold a lock on <work> for this run, so a second run on the same folder stops at once instead of deleting the
    first run's files. The operating system releases the lock when the process ends, also after a crash."""
    f = open(work / LOCK_NAME, "a+")
    try:
        if os.name == "nt":
            import msvcrt

            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        raise CheckError(f"another check_shards.py run uses {work}: wait for it, or use another --work "
                         "folder") from None
    return f


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def first_line(err, code):
    lines = [ln for ln in err.strip().splitlines() if ln.strip()]
    return lines[0] if lines else f"exit {code}"


def split_parts(text_path, part_tokens, out_dir):
    """Cut a decoded shard into parts of whole documents, about part_tokens each. Return the part paths."""
    import pyarrow.parquet as pq

    table = pq.read_table(text_path, columns=["doc_id", "text", "n_tokens"])
    sizes = table.column("n_tokens").to_pylist()
    n_parts = max(1, min(len(sizes), math.ceil(sum(sizes) / part_tokens)))
    target = sum(sizes) / n_parts
    bounds, acc = [0], 0
    for i, s in enumerate(sizes):
        acc += s
        if acc >= target * len(bounds) and len(bounds) < n_parts and i + 1 < len(sizes):
            bounds.append(i + 1)
    bounds.append(len(sizes))
    stem = text_path.name[: -len(".text.parquet")]
    paths = []
    for k in range(len(bounds) - 1):
        p = out_dir / f"{stem}.part{k:03d}.text.parquet"
        pq.write_table(table.slice(bounds[k], bounds[k + 1] - bounds[k]).select(["doc_id", "text"]), p)
        paths.append(p)
    return paths


def check_one(shard_id, a, tok_sha, pool):
    """Decode one shard, run both checks on its parts, return the result dict (never document text)."""
    bin_path = a.shards / f"{shard_id}.bin"
    text_dir = a.work / "text"
    t0 = time.time()
    code, out, err = pool.submit(run, [sys.executable, str(HERE / "decode_shard.py"), str(bin_path),
                                       "--tokenizer", str(a.tokenizer), "--out", str(text_dir)]).result()
    if code != 0:
        raise CheckError(f"decode_shard.py failed: {first_line(err, code)}")
    summary = json.loads(out.strip().splitlines()[-1])
    text_path = Path(summary["out"])
    parts = []
    try:
        with a.split_lock:
            parts = split_parts(text_path, a.part_tokens, text_dir)
        if not a.keep_text:
            text_path.unlink(missing_ok=True)
        fp = ["--fingerprints", str(a.fingerprints)] if a.fingerprints else []
        f_dec = [pool.submit(run, [sys.executable, str(HERE / "decontam_check.py"), str(p)] + fp) for p in parts]
        f_can = pool.submit(run, [sys.executable, str(HERE / "canary_scan.py")] + [str(p) for p in parts] + fp)
        dec = [f.result() for f in f_dec]
        code_c, out_c, err_c = f_can.result()
    finally:  # never leave document text behind, also when a step fails
        for p in parts:
            p.unlink(missing_ok=True)
        if not a.keep_text:
            text_path.unlink(missing_ok=True)

    sets, n_docs, n_flagged, flagged_ids = set(), 0, 0, []
    for code_d, out_d, err_d in dec:
        m_set, m_dec = SET_LINE.search(err_d), DECONTAM_LINE.search(err_d)
        if code_d != 0 or not m_set or not m_dec:
            raise CheckError(f"decontam_check.py failed (exit {code_d}): {err_d.strip()[-300:]}")
        sets.add(m_set.groups())
        n_docs += int(m_dec.group(1))
        n_flagged += int(m_dec.group(2))
        flagged_ids += [json.loads(line)["doc_id"] for line in out_d.splitlines() if line.strip()]
    if len(sets) != 1:
        raise CheckError(f"the parts used different fingerprint sets: {sorted(sets)}")
    version, set_sha, scope = sets.pop()
    m_cc, m_can = CANARY_COUNT.search(err_c), CANARY_LINE.search(err_c)
    if code_c not in (0, 1) or not m_cc or not m_can:  # 1 = hits (counted below), 2 = a file was skipped
        raise CheckError(f"canary_scan.py failed (exit {code_c}): {err_c.strip()[-300:]}")
    if n_docs != summary["docs"] or int(m_can.group(1)) != summary["docs"]:
        raise CheckError(f"document counts differ: decode {summary['docs']}, decontam {n_docs}, "
                         f"canary {m_can.group(1)}")
    canary_hits = [json.loads(line) for line in out_c.splitlines() if line.strip()]
    return {
        "shard_id": shard_id,
        "payload_sha256": summary["payload_sha256"],
        "docs": summary["docs"],
        "tokens": summary["tokens"],
        "dataset_version": summary["dataset_version"],
        "split": summary["split"],
        "tokenizer_sha256": tok_sha,
        "fingerprints_version": version,
        "set_sha256": set_sha,
        "scope": scope,
        "flagged": n_flagged,
        "flagged_doc_ids": flagged_ids,
        "canaries_checked": int(m_cc.group(1)),
        "canary_hits": int(m_can.group(3)),
        "canary_hit_list": [{"canary": h["canary"], "doc_id": h["doc_id"], "offset": h["offset"]} for h in canary_hits],
        "parts": len(dec),
        "seconds": round(time.time() - t0, 1),
    }


def read_reference(path):
    """{shard_id: (payload_sha256, docs, tokens)} from the first row of each shard in a markdown file."""
    ref = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if m:
            ref.setdefault(m.group(1), (m.group(2), int(m.group(3).replace(",", "")),
                                        int(m.group(4).replace(",", ""))))
    return ref


def compare(result, ref):
    """List of mismatch strings (empty when the shard matches its row)."""
    row = ref.get(result["shard_id"])
    if row is None:
        return ["no row in the --compare file"]
    issues = []
    for name, want, got in (("payload_sha256", row[0], result["payload_sha256"]),
                            ("docs", row[1], result["docs"]), ("tokens", row[2], result["tokens"])):
        if want != got:
            issues.append(f"{name} {got} != {want}")
    return issues


def table(results, ref):
    lines = ["| # | shard_id | payload_sha256 | docs | tokens | flagged | canary hits |"
             + (" matches --compare |" if ref is not None else ""),
             "|---:|---|---|---:|---:|---:|---:|" + ("---|" if ref is not None else "")]
    for n, r in enumerate(results, 1):
        line = (f"| {n} | `{r['shard_id']}` | `{r['payload_sha256']}` | {r['docs']:,} | {r['tokens']:,} | "
                f"{r['flagged']} | {r['canary_hits']} |")
        if ref is not None:
            issues = compare(r, ref)
            line += " yes |" if not issues else f" NO: {'; '.join(issues)} |"
        lines.append(line)
    return "\n".join(lines)


def find_shards(folder):
    """Shard IDs in a folder: every .bin with all four shard files next to it, biggest .bin first."""
    ids, incomplete = [], []
    for b in Path(folder).glob("*.bin"):
        shard_id = b.name[: -len(".bin")]
        if all((b.parent / f"{shard_id}{ext}").exists() for ext in SHARD_EXTS):
            ids.append((b.stat().st_size, shard_id))
        else:
            incomplete.append(shard_id)
    return [s for _, s in sorted(ids, key=lambda x: (-x[0], x[1]))], sorted(incomplete)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shards", type=Path, help="folder with the shard files (fetch_shards.py --out)")
    ap.add_argument("--tokenizer", type=Path, required=True, help="the frozen tokenizer.json the shards name")
    ap.add_argument("--work", type=Path, required=True,
                    help="work folder: text/ (decoded text while it runs: never commit it) and results/")
    ap.add_argument("--only", nargs="+", metavar="SHARD_ID", help="check only these shards")
    ap.add_argument("--fingerprints", type=Path, help="fingerprint set folder (default: the scripts' default, v2)")
    ap.add_argument("--jobs", type=int, default=default_jobs(),
                    help=f"worker processes (default {default_jobs()} here: cores, at most one per "
                         f"{GB_PER_JOB} GB of memory)")
    ap.add_argument("--part-tokens", type=int, default=16_000_000,
                    help="tokens per decontam_check.py part (default 16,000,000)")
    ap.add_argument("--compare", type=Path, help="markdown shard table to check payload_sha256, docs and tokens")
    ap.add_argument("--keep-text", action="store_true",
                    help="keep <work>/text/<shard_id>.text.parquet until the next run on this --work folder")
    ap.add_argument("--force", action="store_true", help="check again shards that already have a result")
    a = ap.parse_args(argv)

    if a.jobs < 1:
        ap.error("--jobs must be 1 or more")
    if a.part_tokens < 1:
        ap.error("--part-tokens must be 1 or more")
    if not a.tokenizer.is_file():
        ap.error(f"{a.tokenizer} not found")
    if not a.shards.is_dir():
        ap.error(f"{a.shards} is not a folder")
    tok_sha = sha256_file(a.tokenizer)
    try:
        set_sha = fingerprint_set_sha(a.fingerprints or default_fingerprints())
    except CheckError as e:
        ap.error(str(e))
    for sub in ("text", "results"):
        (a.work / sub).mkdir(parents=True, exist_ok=True)
    try:
        work_lock = lock_work(a.work)  # before the cleanup below, which deletes text another run can still use
    except CheckError as e:
        ap.error(str(e))
    try:
        return run_checks(a, tok_sha, set_sha, code_sha256(), ap)
    finally:
        if not a.keep_text:
            clean_text(a.work)  # also text a step of a crashed earlier run wrote after this run started
        work_lock.close()


def clean_text(work):
    """Delete decoded text in <work>/text. Called while this run holds the lock, so no other run uses the folder:
    a file there is this run's, or from a stopped run (also from a step of a crashed run that went on after it)."""
    for old in (work / "text").glob("*.text.parquet*"):
        old.unlink(missing_ok=True)


def run_checks(a, tok_sha, set_sha, code_sha, ap):
    clean_text(a.work)  # text from an earlier run is never a valid input
    a.split_lock = threading.Semaphore(SPLITS_AT_ONCE)

    ids, incomplete = find_shards(a.shards)
    if a.only:
        missing = sorted(set(a.only) - set(ids) - set(incomplete))
        if missing:
            ap.error(f"not found: {' '.join(missing)}")
        ids = [i for i in ids if i in set(a.only)]
        incomplete = [i for i in incomplete if i in set(a.only)]
    for shard_id in incomplete:
        print(f"{shard_id}: FAILED: a shard file is missing (run fetch_shards.py again)", file=sys.stderr)
    if not ids and not incomplete:
        ap.error("no shards to check")
    ref = read_reference(a.compare) if a.compare else None
    lock = threading.Lock()

    def task(shard_id, pool):
        rp = a.work / "results" / f"{shard_id}.json"
        if rp.exists() and not a.force:
            old = json.loads(rp.read_text())
            manifest = json.loads((a.shards / f"{shard_id}.json").read_text())
            if (old.get("tokenizer_sha256") == tok_sha and old.get("set_sha256") == set_sha
                    and old.get("code_sha256") == code_sha
                    and old.get("payload_sha256") == manifest.get("payload_sha256")):
                with lock:
                    print(f"{shard_id}: result kept from an earlier run (use --force to check again)", file=sys.stderr)
                return old
        try:
            r = check_one(shard_id, a, tok_sha, pool)
            r["code_sha256"] = code_sha
        except Exception as e:  # one bad shard must not stop the others
            with lock:
                print(f"{shard_id}: FAILED: {e}", file=sys.stderr)
            return None
        tmp = rp.with_name(rp.name + ".tmp")
        tmp.write_text(json.dumps(r, indent=1) + "\n")
        os.replace(tmp, rp)
        with lock:
            print(f"{shard_id}: docs {r['docs']} tokens {r['tokens']} flagged {r['flagged']} "
                  f"canary hits {r['canary_hits']} ({r['parts']} part(s), {r['seconds']} s)", file=sys.stderr)
        return r

    t0 = time.time()
    # pool runs the worker processes. shard_pool runs one thread per shard in progress, which only waits on pool;
    # its size limits the decoded text on disk to --jobs shards at a time.
    with ThreadPoolExecutor(a.jobs) as pool, ThreadPoolExecutor(a.jobs) as shard_pool:
        out = list(shard_pool.map(lambda s: task(s, pool), ids))
    results = sorted((r for r in out if r is not None), key=lambda r: r["shard_id"])
    failed = sorted([i for i, r in zip(ids, out) if r is None] + incomplete)

    print(table(results, ref))
    sets = sorted({(r["fingerprints_version"], r["set_sha256"], r["scope"]) for r in results})
    for version, sha, scope in sets:
        print(f"\nFingerprint set: {version}, set_sha256 `{sha}`, scope `{scope}`")
    canaries = sorted({r["canaries_checked"] for r in results})
    if canaries:
        print(f"Canaries checked per shard: {', '.join(map(str, canaries))}")
    print(f"Tokenizer sha256: `{tok_sha}`")
    print(f"Total: {len(results)} shards, {sum(r['docs'] for r in results):,} docs, "
          f"{sum(r['tokens'] for r in results):,} tokens, {sum(r['flagged'] for r in results)} flagged, "
          f"{sum(r['canary_hits'] for r in results)} canary hits")
    print(f"checked {len(results)} of {len(ids) + len(incomplete)} shard(s) in {time.time() - t0:.0f} s with "
          f"--jobs {a.jobs}" + (f"; FAILED: {' '.join(failed)}" if failed else ""), file=sys.stderr)

    other_set = sorted(r["shard_id"] for r in results if r["set_sha256"] != set_sha)
    if other_set:
        print(f"set_sha256 is not {set_sha} for: {' '.join(other_set)}", file=sys.stderr)
    bad = bool(failed) or len(sets) > 1 or bool(other_set)
    bad |= any(r["flagged"] or r["canary_hits"] for r in results)
    bad |= ref is not None and any(compare(r, ref) for r in results)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
