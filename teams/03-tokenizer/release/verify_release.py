#!/usr/bin/env python3
"""
verify_release.py
=================

Checks a downloaded copy of the frozen G3 tokenizer (C3 sample-v0, #340) before a team uses it:

  1. tokenizer.json has the sha256 pinned in release/SHA256SUMS, and every repo file listed there matches.
  2. Structure: BPE, vocab 131,072 (ids 0..131071, no gaps), 130,460 merges, 356 special tokens.
  3. Roles: bos / eos / pad / unk in special_tokens_map.json have the ids in SPECIAL_TOKENS.md, and each
     special token encodes to exactly its own id.
  4. Round trip: decode(encode(x)) == normalizer(x) on a short line in each of the 11 Indic languages,
     English and code. Nothing is added: no bos, no eos.
  5. With transformers installed: AutoTokenizer.from_pretrained on tokenizer.json plus the two configs
     here gives the same ids and eos_token_id 130822.

Only the standard library and `tokenizers` are needed (`transformers` for check 5, skipped without it).

    python teams/03-tokenizer/release/verify_release.py /path/to/tokenizer.json
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent
VOCAB, MERGES, SPECIALS = 131072, 130460, 356

SAMPLES = {
    "Hi": "भारत एक विशाल देश है।", "Mr": "माझे नाव राम आहे.", "Bn": "আমার সোনার বাংলা",
    "As": "মোৰ নাম অসম", "Ta": "வணக்கம் உலகம்", "Te": "నమస్కారం ప్రపంచం", "Kn": "ನಮಸ್ಕಾರ ಜಗತ್ತು",
    "Ml": "നമസ്കാരം ലോകം", "Gu": "નમસ્તે દુનિયા", "Pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "Or": "ନମସ୍କାର ଦୁନିଆ",
    "En": "The quick brown fox jumps over the lazy dog.",
    "Code": "def add(a, b):\n    return a + b  # sum\n",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pinned():
    """{path relative to teams/03-tokenizer: sha256} from release/SHA256SUMS."""
    out = {}
    for line in (HERE / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            out[name.lstrip("*")] = digest
    return out


def role_ids():
    """{role: id} from the table in SPECIAL_TOKENS.md."""
    rows = re.findall(r"^\| (bos|eos|pad|unk) \| `[^`]+` \| (\d+) \|", (HERE / "SPECIAL_TOKENS.md").read_text(encoding="utf-8"), re.M)
    return {role: int(i) for role, i in rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tokenizer", help="the downloaded tokenizer.json")
    args = ap.parse_args()
    problems = []

    def check(ok, what):
        print(f"  {'ok  ' if ok else 'FAIL'} {what}", flush=True)
        if not ok:
            problems.append(what)

    print("1. sha256")
    sums = pinned()
    got = sha256(args.tokenizer)
    check(got == sums["release/tokenizer.json"], f"tokenizer.json {got}")
    for name, digest in sums.items():
        if name != "release/tokenizer.json":
            check((TEAM / name).is_file() and sha256(TEAM / name) == digest, f"repo file {name}")

    print("2. structure")
    raw = json.loads(Path(args.tokenizer).read_text(encoding="utf-8"))
    model, added = raw["model"], raw["added_tokens"]
    ids = sorted({*model["vocab"].values(), *(a["id"] for a in added)})
    check(model["type"] == "BPE", f"model type {model['type']}")
    check(ids == list(range(VOCAB)), f"ids 0..{VOCAB - 1} with no gaps ({len(ids)} ids)")
    check(len(model["merges"]) == MERGES, f"{len(model['merges'])} merges")
    check(sum(a["special"] for a in added) == SPECIALS, f"{sum(a['special'] for a in added)} special tokens")

    print("3. special-token roles")
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(args.tokenizer)
    roles = role_ids()
    names = json.loads((HERE / "special_tokens_map.json").read_text(encoding="utf-8"))
    for role in ("bos", "eos", "pad", "unk"):
        name = names[f"{role}_token"]
        check(tok.token_to_id(name) == roles.get(role), f"{role} {name} = {tok.token_to_id(name)} (SPECIAL_TOKENS.md: {roles.get(role)})")
    single = [a for a in added if a["special"] and tok.encode(a["content"], add_special_tokens=False).ids != [a["id"]]]
    check(not single, f"each of the {SPECIALS} special tokens encodes to its own single id"
          + (f" ({len(single)} do not, first {single[0]['content']})" if single else ""))

    print("4. round trip (no bos / eos added)")
    for lang, text in SAMPLES.items():
        enc = tok.encode(text, add_special_tokens=False).ids
        want = tok.normalizer.normalize_str(text) if tok.normalizer else text
        check(tok.decode(enc, skip_special_tokens=False) == want and roles["bos"] not in enc and roles["eos"] not in enc,
              f"{lang}: {len(enc)} tokens")

    print("5. transformers AutoTokenizer")
    try:
        from transformers import AutoTokenizer
    except ImportError:
        print("  skip transformers is not installed")
    else:
        with tempfile.TemporaryDirectory() as d:
            for f in ("tokenizer_config.json", "special_tokens_map.json"):
                shutil.copyfile(HERE / f, Path(d) / f)
            shutil.copyfile(args.tokenizer, Path(d) / "tokenizer.json")
            hf = AutoTokenizer.from_pretrained(d)
            check(hf.eos_token_id == roles["eos"], f"eos_token_id {hf.eos_token_id}")
            check(all(hf.encode(t) == tok.encode(t, add_special_tokens=False).ids for t in SAMPLES.values()),
                  "same ids as tokenizers, nothing added")

    print("RESULT:", "FAIL" if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
