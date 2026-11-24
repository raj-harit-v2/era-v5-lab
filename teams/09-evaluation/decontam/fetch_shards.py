"""Download training shards from a shard_links.tsv, as the step before check_shards.py (G9).

    python fetch_shards.py shard_links.tsv --out <folder>
    python fetch_shards.py shard_links.tsv --out <folder> --only code-cpp-train-000000 ind-gu-fw2-train-000000

This is the only step that uses the network. check_shards.py reads the folder this writes and does not download, so
the check can run as a TSAI job with no network that reads only its inputs.

For each shard it downloads <shard_id>.json (the manifest) first, every time, because an old manifest with the same
shard name must not be used, then .bin, .idx.npy and .docs.parquet, several
files at the same time (--parallel, default 8). Each file is checked against the sha256 in the manifest
(payload_sha256, index_sha256, sample_metadata_sha256) before it gets its final name, so a broken or cut download never
looks like a shard. A file that is already there with the right sha256 is not downloaded again. The quality report is
not needed for the check and is not downloaded.

shard_links.tsv: lines starting with # are comments, then a header 'file<TAB>url', then one line per file.
Exit code: 0 when every file is there and matches its manifest, 1 when a file failed, 2 for a usage error.
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RETRY_SLEEP = 2  # seconds, times the attempt number
DATA_FILES = ((".bin", "payload_sha256"), (".idx.npy", "index_sha256"), (".docs.parquet", "sample_metadata_sha256"))


class FetchError(Exception):
    pass


def read_links(path):
    """{file name: url} from shard_links.tsv."""
    links = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2 or parts[0] == "file":
            continue
        links[parts[0]] = parts[1]
    return links


def shard_ids(links):
    return sorted(name[: -len(".bin")] for name in links if name.endswith(".bin"))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest, want_sha=None, tries=3, opener=urllib.request.urlopen):
    """Download url to dest through dest.part. With want_sha, the file must have that sha256."""
    tmp = dest.with_name(dest.name + ".part")
    for attempt in range(1, tries + 1):
        try:
            h = hashlib.sha256()
            with opener(url, timeout=120) as r, open(tmp, "wb") as f:
                for chunk in iter(lambda: r.read(1 << 20), b""):
                    f.write(chunk)
                    h.update(chunk)
            if want_sha and h.hexdigest() != want_sha:
                raise FetchError(f"sha256 {h.hexdigest()} is not the manifest's {want_sha}")
            os.replace(tmp, dest)
            return
        except Exception as e:  # network error, expired link or wrong bytes: retry, then report
            tmp.unlink(missing_ok=True)
            if attempt == tries:
                raise FetchError(f"{dest.name}: {type(e).__name__}: {e}") from None
            time.sleep(RETRY_SLEEP * attempt)


def manifest_of(shard_id, links, out, opener):
    """Download the manifest every time (it is small): a manifest already in the folder can be from an older shard
    with the same name, and the data files are checked against it."""
    path = out / f"{shard_id}.json"
    if f"{shard_id}.json" not in links:
        raise FetchError(f"{shard_id}.json is not in the links file")
    download(links[f"{shard_id}.json"], path, opener=opener)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise FetchError(f"{shard_id}.json is not valid JSON: {e}") from None


def file_jobs(shard_id, manifest, links, out):
    """(url, dest, sha256) for each data file that is missing or does not match the manifest."""
    jobs = []
    for ext, key in DATA_FILES:
        name = shard_id + ext
        dest = out / name
        want = manifest.get(key)
        if not want:
            raise FetchError(f"{shard_id}.json has no {key}")
        if dest.exists() and sha256_file(dest) == want:
            continue
        if name not in links:
            raise FetchError(f"{name} is not in the links file")
        jobs.append((links[name], dest, want))
    return jobs


def main(argv=None, opener=urllib.request.urlopen):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("links", type=Path, help="TSAI's shard_links.tsv")
    ap.add_argument("--out", type=Path, required=True, help="folder for the shard files")
    ap.add_argument("--only", nargs="+", metavar="SHARD_ID", help="download only these shards")
    ap.add_argument("--parallel", type=int, default=8, help="files at the same time (default 8)")
    a = ap.parse_args(argv)
    if a.parallel < 1:
        ap.error("--parallel must be 1 or more")
    links = read_links(a.links)
    ids = shard_ids(links)
    if a.only:
        missing = sorted(set(a.only) - set(ids))
        if missing:
            ap.error(f"not in the links file: {' '.join(missing)}")
        ids = [i for i in ids if i in set(a.only)]
    if not ids:
        ap.error("no shards to download")
    a.out.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    failed, jobs = [], []
    with ThreadPoolExecutor(a.parallel) as ex:
        for shard_id, got in zip(ids, ex.map(lambda s: _try(manifest_of, s, links, a.out, opener), ids)):
            if isinstance(got, FetchError):
                print(f"{shard_id}: FAILED: {got}", file=sys.stderr)
                failed.append(shard_id)
                continue
            try:
                jobs += [(shard_id, *j) for j in file_jobs(shard_id, got, links, a.out)]
            except FetchError as e:
                print(f"{shard_id}: FAILED: {e}", file=sys.stderr)
                failed.append(shard_id)
        jobs.sort(key=lambda j: j[2].suffix != ".bin")  # the big .bin files first
        results = ex.map(lambda j: _try(download, j[1], j[2], j[3], opener=opener), jobs)
        for (shard_id, _, dest, _), got in zip(jobs, results):
            if isinstance(got, FetchError):
                print(f"{shard_id}: FAILED: {got}", file=sys.stderr)
                if shard_id not in failed:
                    failed.append(shard_id)
    print(f"{len(ids) - len(failed)} of {len(ids)} shard(s) ready in {a.out} ({len(jobs)} file(s) downloaded, "
          f"{time.time() - t0:.0f} s)" + (f"; FAILED: {' '.join(failed)}" if failed else ""), file=sys.stderr)
    return 1 if failed else 0


def _try(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except FetchError as e:
        return e


if __name__ == "__main__":
    sys.exit(main())
