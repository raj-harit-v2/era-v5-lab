"""What a shard manifest says about a pack: language, script, domain and capability lane, and for a table that gives
them the pack's licence and where that licence is recorded, from pack_table.json or the job's own pack table.

  row("code-go")  ->  {"language": "go", "script": "Latn", "domain": "code", "lane": "code"}
  row("code-go", load(<job's table>))  ->  the same, with "license" and "license_source"

A pack that is not in the table, or has a null field (a licence that is not settled is null), is an error: nothing is
guessed, because a manifest never changes after it is written. The lane is one of LANES, in every table.
"""
import json
from pathlib import Path

TABLE = Path(__file__).with_name("pack_table.json")
FIELDS = ("language", "script", "domain", "lane")
LICENCE = ("license", "license_source")  # optional: a row has both or neither (the shard job's table has both)
LANES = ("code", "code-adjacent", "english", "indic", "math", "science")  # TSAI, 16 Nov 2026 (job request PR #47)


class PackTableError(Exception):
    pass


def load(path=TABLE):
    """The table as {pack_id: row}; every row has exactly FIELDS, with or without both LICENCE fields, each a non-empty
    string or null."""
    packs = json.loads(Path(path).read_text(encoding="utf-8"))["packs"]
    for pack, r in packs.items():
        if not isinstance(r, dict) or set(FIELDS) - set(r) or set(r) - set(FIELDS) not in (set(), set(LICENCE)):
            got = sorted(r) if isinstance(r, dict) else type(r).__name__
            raise PackTableError(f"{path}: {pack} has fields {got}, expected {sorted(FIELDS)}, with or without "
                                 f"{' and '.join(LICENCE)}")
        for field, value in r.items():
            if value is not None and not (isinstance(value, str) and value):
                raise PackTableError(f"{path}: {pack}.{field} must be a non-empty string or null, not {value!r}")
        if r["lane"] is not None and r["lane"] not in LANES:
            raise PackTableError(f"{path}: {pack}.lane is {r['lane']!r}, expected one of {', '.join(LANES)} or null")
    return packs


def row(pack_id, table=None):
    """The pack's row, with no null field (the licence fields too, when the table has them); PackTableError says what
    is missing."""
    table = load() if table is None else table
    if pack_id not in table:
        raise PackTableError(f"{pack_id} is not in pack_table.json")
    missing = [f for f in (*FIELDS, *LICENCE) if f in table[pack_id] and table[pack_id][f] is None]
    if missing:
        raise PackTableError(f"{pack_id} has no {' or '.join(missing)} in pack_table.json")
    return dict(table[pack_id])
