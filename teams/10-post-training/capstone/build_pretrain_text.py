"""Build a small local pre-training text file (UTF-8 JSONL of {id, text}) for a capstone-family stand-in model.

Stand-in only: the capstone's real pre-training mixture (TSAI-staged bundle, Data A/B shards) is not on this
machine. Two local sources, both human-written and permissively licensed:

* code: `.py` files of installed Python packages whose licence is MIT, BSD or Apache (allowlist below, checked
  against each distribution's metadata at build time); files under 200 B or over 64 KiB are skipped, exact
  duplicates dropped.
* English prose: Dolly-15k (CC-BY-SA-3.0, human-written) rows from G10's local SFT build, only rows whose id hash
  falls in the pre-training half (`dolly_half(id) == 0`); the other half is kept for SFT and its evaluation, so the
  SFT test never scores rows the base model read. Chat markers are stripped; user and assistant text are kept.

The output and its manifest go to a private folder (they hold text). Nothing here becomes capstone training data.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata as md
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
from tokenizers import Tokenizer

PERMISSIVE = ("MIT", "BSD", "Apache", "ISC")
# Import directory -> distribution name. Only these are read.
PACKAGES = {
    "torch": "torch", "torchgen": "torch", "functorch": "torch", "transformers": "transformers", "sympy": "sympy",
    "pandas": "pandas", "numpy": "numpy", "networkx": "networkx", "datasets": "datasets",
    "huggingface_hub": "huggingface_hub", "setuptools": "setuptools", "_pytest": "pytest", "aiohttp": "aiohttp",
    "requests": "requests", "urllib3": "urllib3", "click": "click", "rich": "rich", "pygments": "Pygments",
    "jinja2": "Jinja2", "yaml": "PyYAML", "packaging": "packaging", "fsspec": "fsspec", "dateutil": "python-dateutil",
    "anyio": "anyio", "attr": "attrs", "pyparsing": "pyparsing", "h11": "h11", "idna": "idna", "multidict": "multidict",
    "yarl": "yarl", "websockets": "websockets", "typer": "typer", "filelock": "filelock", "mpmath": "mpmath",
    "pyarrow": "pyarrow", "safetensors": "safetensors", "tokenizers": "tokenizers"
}
TURN = re.compile(r"<\|im_start\|>(user|assistant)\n(.*?)<\|im_end\|>", re.S)


def licence_of(dist: str) -> str:
    meta = md.metadata(dist)
    parts = [meta.get("License-Expression") or "", (meta.get("License") or "")[:80]]
    parts += [c.split("::")[-1].strip() for c in (meta.get_all("Classifier") or []) if c.startswith("License")]
    return " | ".join(p.replace("\n", " ") for p in parts if p)


def dolly_half(row_id: str) -> int:
    return hashlib.sha256(row_id.encode()).digest()[0] & 1


def code_docs(site: Path, max_bytes: int):
    seen, total = set(), 0
    for pkg, dist in sorted(PACKAGES.items()):
        if dist is None or not (site / pkg).is_dir():
            continue
        lic = licence_of(dist)
        if not any(k in lic for k in PERMISSIVE):
            raise SystemExit(f"{dist}: licence not in allowlist: {lic}")
        for path in sorted((site / pkg).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            raw = path.read_bytes()
            if not 200 <= len(raw) <= 65536:
                continue
            h = hashlib.sha256(raw).hexdigest()
            if h in seen:
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            seen.add(h)
            total += len(raw)
            yield {"id": f"code/{path.relative_to(site).as_posix()}", "text": text}, dist, lic
            if total >= max_bytes:
                return


def dolly_docs(parts: list[Path]):
    for part in parts:
        with gzip.open(part, "rt", encoding="utf8") as f:
            for line in f:
                row = json.loads(line)
                if dolly_half(row["id"]) != 0:
                    continue
                turns = [t.strip() for _, t in TURN.findall(row["text"])]
                text = "\n\n".join(t for t in turns if t)
                if text:
                    yield {"id": f"dolly/{row['id']}", "text": text}


class RoundTrip:
    """Keep a document only if tokenizer ids -> raw byte table rows reproduce its UTF-8 bytes exactly (Team 5's
    `Artifacts.encode` refuses anything else). An NFC-normalised copy is tried before dropping."""

    def __init__(self, tokenizer: Path, table: Path):
        self.tok = Tokenizer.from_file(str(tokenizer))
        self.tok.no_padding()
        self.tok.no_truncation()
        with np.load(table, allow_pickle=False) as z:
            self.rows, self.lengths = z["bytes"].copy(), z["lengths"].copy()
        self.stats = {"exact": 0, "nfc": 0, "dropped": 0}

    def ok(self, text: str) -> bool:
        ids = self.tok.encode(text, add_special_tokens=False).ids
        raw = b"".join(self.rows[i, : int(self.lengths[i])].tobytes() for i in ids)
        return raw == text.encode("utf8")

    def __call__(self, text: str) -> str | None:
        if self.ok(text):
            self.stats["exact"] += 1
            return text
        nfc = unicodedata.normalize("NFC", text)
        if nfc != text and self.ok(nfc):
            self.stats["nfc"] += 1
            return nfc
        self.stats["dropped"] += 1
        return None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--site-packages", type=Path, required=True)
    p.add_argument("--dolly-parts", type=Path, nargs="+", required=True)
    p.add_argument("--code-mb", type=float, default=40.0)
    p.add_argument("--tokenizer", type=Path, required=True)
    p.add_argument("--byte-table", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    rt = RoundTrip(a.tokenizer, a.byte_table)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    counts, licences = {"code": [0, 0], "dolly": [0, 0]}, {}
    with a.out.open("w", encoding="utf8") as f:
        for doc, dist, lic in code_docs(a.site_packages, int(a.code_mb * 2**20)):
            doc["text"] = rt(doc["text"])
            if doc["text"] is None:
                continue
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            counts["code"][0] += 1
            counts["code"][1] += len(doc["text"].encode())
            licences[dist] = lic
        for doc in dolly_docs(a.dolly_parts):
            doc["text"] = rt(doc["text"])
            if doc["text"] is None:
                continue
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            counts["dolly"][0] += 1
            counts["dolly"][1] += len(doc["text"].encode())
    h = hashlib.sha256(a.out.read_bytes()).hexdigest()
    manifest = {"file": a.out.name, "sha256": h, "docs_bytes": counts, "code_licences": licences,
                "roundtrip": rt.stats, "tokenizer_sha256": hashlib.sha256(a.tokenizer.read_bytes()).hexdigest(),
                "dolly_rule": "sha256(row id)[0] & 1 == 0 -> pre-training half; == 1 -> SFT half",
                "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    a.out.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf8")
    print(json.dumps({"sha256": h, "docs_bytes": counts, "roundtrip": rt.stats}))


if __name__ == "__main__":
    main()
