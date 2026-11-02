"""TSAI job: rebuild C3 sample-v0 (#195) from pinned inputs and check its sha256 against c3_s0_manifest.json.

Runs with no network. Reads only the inputs named in the config, writes only to ./out/:

1. Check every input file against its pinned sha256 (corpus60 text, the sample v0 SHA256SUMS and manifest,
   BrahmicTokenizer-131K tokenizer.json, o200k_base.tiktoken).
2. Build tokenizer v0 and v0.1 from BrahmicTokenizer-131K (v0/build_v0.py, v0/build_v0_1.py).
3. Turn sample v0 train/ into corpus_s0 (sample_to_corpus.py, Pa and As from corpus60) and check the four
   files mix_s0.json uses against the hashes in c3_s0_manifest.json.
4. Run train_bpe.py with the C3 flags and mix_s0.json (paths pointed at the inputs; same files, order, factors).
5. Write out/result.json with the sha256 and PASS/FAIL, then delete the intermediate corpus.

    python teams/03-tokenizer/train/rebuild_c3_s0.py --config teams/03-tokenizer/train/rebuild_c3_s0.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOK = HERE.parent
O200K_URL = "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check(path, want, what):
    got = sha256_file(path)
    print(f"  {'ok  ' if got == want else 'FAIL'} {what}: {got}", flush=True)
    if got != want:
        sys.exit(f"ERROR: {what} ({path}) sha256 {got}, wanted {want}.")


def run(cmd, env=None):
    print("$ " + " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, env=env)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    manifest = json.loads((HERE / "c3_s0_manifest.json").read_text())
    want = manifest["sha256"]
    out = Path("out")
    out.mkdir(exist_ok=True)
    t0 = time.time()
    import tiktoken
    import tokenizers
    print(f"python {platform.python_version()}  tiktoken {tiktoken.__version__}  tokenizers {tokenizers.__version__}  "
          f"{platform.platform()}", flush=True)

    print("1. pinned inputs", flush=True)
    corpus60, sample = Path(cfg["corpus60"]), Path(cfg["sample_v0"])
    for lang, entry in manifest["corpus"].items():
        check(corpus60 / entry["file"], entry["sha256"], f"corpus60/{entry['file']}")
    check(sample / "sample_manifest.json", manifest["sample_v0"]["sample_manifest_sha256"], "sample v0 manifest")
    check(sample / "SHA256SUMS", cfg["sample_v0_sha256sums_sha256"], "sample v0 SHA256SUMS")
    check(cfg["brahmic_tokenizer"], cfg["brahmic_tokenizer_sha256"], "BrahmicTokenizer-131K tokenizer.json")
    check(cfg["o200k_base"], cfg["o200k_base_sha256"], "o200k_base.tiktoken")
    # tiktoken looks for the file under TIKTOKEN_CACHE_DIR/sha1(url) before it tries the network.
    cache = out / "tiktoken_cache"
    cache.mkdir(exist_ok=True)
    shutil.copyfile(cfg["o200k_base"], cache / hashlib.sha1(O200K_URL.encode()).hexdigest())
    env = {**os.environ, "TIKTOKEN_CACHE_DIR": str(cache.resolve())}

    print("2. tokenizer v0 and v0.1", flush=True)
    for d in ("v0", "v0.1"):
        (out / d).mkdir(exist_ok=True)
    run([sys.executable, TOK / "v0/build_v0.py", cfg["brahmic_tokenizer"], out / "v0/tokenizer.json"])
    run([sys.executable, TOK / "v0/build_v0_1.py", out / "v0/tokenizer.json", out / "v0.1/tokenizer.json"])

    print("3. corpus_s0 from sample v0 train/", flush=True)
    corpus_s0 = out / "corpus_s0"
    run([sys.executable, HERE / "sample_to_corpus.py", "--sample", sample, "--out", corpus_s0,
         "--fallback", corpus60, "--fallback-langs", "Pa,As"])
    dirs = {"corpus60": corpus60, "corpus_s0": corpus_s0}
    for lang, units in manifest["mix"].items():
        for u in units:
            check(dirs[u["dir"]] / u["file"], u["sha256"], f"mix {lang}: {u['dir']}/{u['file']}")
    mix = json.loads((HERE / "mix_s0.json").read_text())
    resolved = {k: v if k.startswith("_") else [[str(dirs[p.split("/")[0]].resolve() / p.split("/", 1)[1]), f]
                                                 for p, f in v] for k, v in mix.items()}
    (out / "mix_s0_resolved.json").write_text(json.dumps(resolved, indent=1))

    print("4. train_bpe.py (C3 flags + mix_s0.json)", flush=True)
    run([sys.executable, HERE / "train_bpe.py", "--corpus", corpus60, "--out", out / "c3_s0",
         "--slots", HERE / "slots_v2.json", "--special-layout", "v0", "--v0-tokenizer", out / "v0.1/tokenizer.json",
         "--normalizer", "v1", "--mix", out / "mix_s0_resolved.json"], env=env)

    got = sha256_file(out / "c3_s0/tokenizer.json")
    result = {"question": "Does a fresh build of C3 sample-v0 at the #195 commit give the committed sha256?",
              "expected_sha256": want, "built_sha256": got, "result": "PASS" if got == want else "FAIL",
              "seconds": round(time.time() - t0)}
    (out / "result.json").write_text(json.dumps(result, indent=2))
    for tmp in (corpus_s0, cache, out / "v0"):
        shutil.rmtree(tmp)
    print(json.dumps(result, indent=2), flush=True)
    sys.exit(0 if got == want else 1)


if __name__ == "__main__":
    main()
