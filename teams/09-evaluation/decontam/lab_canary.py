"""The lab canary string (G9). One place for the string, the stamp, the canary files and the search.

Every file that holds eval items (questions, answers, prompts) carries the lab canary line.
If the canary turns up in a training document, eval data reached the training data.
canary_scan.py looks for it, and so does decontam_check.py (through fpset.Fingerprints).

The canary is plain ASCII text, not a special token (TSAI, G10 chat, 29 Oct): a special
token never comes out of normal tokenization, so leaked text would not contain it.
ASCII also keeps it the same in JSON written with ensure_ascii=True.

The full string is built from parts and never written out whole in this repo (code or docs).
If the repo itself is crawled into training data, it does not carry the canary, so the
canary keeps working as a marker and our own scans do not flag the repo.

Do not change the parts. Files stamped with the old string would no longer be found.
"""

import json
from pathlib import Path

# The ID part was made once with uuid.uuid4().
_ID_PARTS = ("era-v5-lab", "eval", "43c1a566-5d44-4c5b-96ae-b53b4188b0ec")
LAB_CANARY = ":".join(_ID_PARTS)  # the searched-for marker
LAB_CANARY_ID = _ID_PARTS[0]
# The line written into eval files, in the style of the BIG-bench, GPQA and HLE canaries.
LAB_CANARY_LINE = " ".join(("ERA V5 LAB EVALUATION DATA.", "IT MUST NEVER APPEAR IN TRAINING DATA.",
                            "canary GUID", LAB_CANARY))
MARKDOWN_LINE = f"<!-- {LAB_CANARY_LINE} -->"


def stamp(record):
    """Return a copy of a dict with the canary line as its first key."""
    return {"canary": LAB_CANARY_LINE, **{k: v for k, v in record.items() if k != "canary"}}


def read_canary_file(path):
    """The canary strings in one canaries.txt: one per line, stripped, blank lines skipped."""
    return [s for s in (line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines()) if s]


def load_canaries(fingerprint_dir=None):
    """Canary string -> source ID: the lab canary, plus the benchmark canaries of a fingerprint set
    (the benchmarks whose entry in the set's MANIFEST.json has canaries, for example GPQA and HLE).
    fingerprint_dir=None gives the lab canary only. A folder without MANIFEST.json is an error,
    so a wrong path cannot quietly drop the benchmark canaries."""
    canaries = {LAB_CANARY: LAB_CANARY_ID}
    if fingerprint_dir is None:
        return canaries
    d = Path(fingerprint_dir)
    manifest = d / "MANIFEST.json"
    if not manifest.is_file():
        raise FileNotFoundError(f"{manifest} not found: not a fingerprint set folder")
    for bid, bm in sorted(json.loads(manifest.read_text(encoding="utf-8"))["benchmarks"].items()):
        if bm.get("canaries"):
            for c in read_canary_file(d / bid / "canaries.txt"):
                canaries.setdefault(c, bid)
    return canaries


def find(text, canaries):
    """Every occurrence of every canary in text, as (offset, canary), by offset."""
    out = []
    for c in canaries:
        if not c:
            raise ValueError("empty canary string")
        i = text.find(c)
        while i != -1:
            out.append((i, c))
            i = text.find(c, i + 1)
    return sorted(out)
