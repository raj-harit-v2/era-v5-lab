"""The clean stage's sample manifest, checked in one place: by stage_args (so --plan sees it) and by clean_job.py
(just before it starts). Standard library only.

The manifest is the pinned description of the input set: for each raw part its path, split, pack, rows, bytes and sha256,
and the sample's total_docs. validate() says whether it is the pinned file and describes a consistent set.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath

SPLITS = ("train", "heldout")  # the only splits the clean job accepts


class ManifestError(ValueError):
    """The manifest is missing, is not the pinned file, or does not describe a consistent input set."""


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def part_path(value):
    """A manifest part path as split/pack/file; anything else is an error."""
    p = PurePosixPath(str(value))
    if p.is_absolute() or ".." in p.parts or "\\" in str(value) or len(p.parts) != 3 or p.parts[0] not in SPLITS:
        raise ManifestError(f"unexpected part path {value!r}: expected <{'|'.join(SPLITS)}>/<pack>/<file>")
    return p


def validate(path, pin, expected_parts, only=()):
    """The manifest's data, once it is the pinned file and consistent; ManifestError (naming what is wrong) otherwise.
    expected_parts: {split: part count} from the run config. only: parts a trial run asks for."""
    path = Path(path)
    if not path.is_file():
        raise ManifestError(f"the sample manifest {path} is not there")
    got = sha256(path)
    if got != pin:
        raise ManifestError(f"the sample manifest {path} has sha256 {got[:12]}…, the pin is {pin[:12]}…")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        shards, total = data["shards"], data["total_docs"]
        if not isinstance(shards, list) or not all(isinstance(s, dict) for s in shards) or not isinstance(total, int):
            raise TypeError
    except (ValueError, KeyError, TypeError):
        raise ManifestError(f"the sample manifest {path} has no list of 'shards' (objects) and integer 'total_docs'") from None
    counts = dict(Counter(s.get("split") for s in shards))
    if counts != dict(expected_parts):
        raise ManifestError(f"the manifest has parts {counts}, stages.clean.expected_parts says {dict(expected_parts)}")
    seen = set()
    for s in shards:
        p = part_path(s.get("path"))
        if s["path"] in seen or p.parts[0] != s["split"] or p.parts[1] != s.get("pack_id"):
            raise ManifestError(f"duplicate or inconsistent manifest entry {s['path']}")
        seen.add(s["path"])
        if not (isinstance(s.get("rows"), int) and isinstance(s.get("bytes"), int)
                and isinstance(s.get("sha256"), str) and len(s["sha256"]) == 64):
            raise ManifestError(f"manifest entry {s['path']} lacks rows, bytes or a sha256")
    if sum(s["rows"] for s in shards) != total:
        raise ManifestError("the manifest's row totals disagree: the parts do not add up to total_docs")
    if set(only) - seen:
        raise ManifestError("requested part(s) are not in the manifest: " + ", ".join(sorted(set(only) - seen)))
    return data
