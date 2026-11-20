"""Tests for inventory_check.py: the expected inventory against a ledger folder and a shard summary.

Everything is made up here: a ledger folder is its summary plus Parquet files with the two columns the check reads
(split, part), and a shards folder is its shards_summary.json. The runner's side is tested in test_run_pipeline.py.

  python -m pytest teams/01-data-a/pipeline/tests/test_inventory_check.py -q
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq

from conftest import PIPELINE
import inventory_check as ic

A, B, H, E = ("train/code-go/part-00000.parquet", "train/code-go/part-00001.parquet", "heldout/code-go/part-00000.parquet",
              "train/en-dclm/part-00000.parquet")
ROWS = {A: 5, B: 3, H: 2, E: 4}
MANIFEST = "ab" * 32


def sha_of(name):
    """A made-up sha256 per part: 64 hex characters that differ from part to part."""
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def entry(name, **change):
    """One part of an inventory as the real file has it; a field given as ... is left out."""
    split, pack, _ = name.split("/")
    e = {"split": split, "pack_id": pack, "part": name, "raw_sha256": sha_of(name), "raw_rows": ROWS.get(name, 1),
         "expected": "written" if split == "train" else "not_sharded"}
    e.update(change)
    return {k: v for k, v in e.items() if v is not ...}


def write_inventory(tmp_path, parts=None, name="expected_inventory.json", **top):
    parts = [entry(p) for p in (A, B, H, E)] if parts is None else parts
    inv = {"_comment": "made up", "input_manifest_sha256": MANIFEST, "parts": parts}
    if "packs" not in top:  # the packs of the parts, unless the test gives its own (or parts that are not entries)
        entries = parts if isinstance(parts, list) and all(isinstance(p, dict) for p in parts) else []
        inv["packs"] = sorted({p["part"].split("/")[1] for p in entries if isinstance(p.get("part"), str) and p["part"].count("/") == 2}) or ["code-go", "en-dclm"]
    inv.update(top)
    path = tmp_path / name
    path.write_text(json.dumps({k: v for k, v in inv.items() if v is not ...}), encoding="utf-8")
    return path


def write_ledger(folder, rows=None, hashes=None, mode="B", packs=None, sep="/"):
    """A ledger folder as the check reads it: <split>/<pack>.parquet with split and part, and ledger_summary.json with
    clean_mode, the raw files (part, sha256) and by_pack ({pack: {split: {"kept": n}}}). packs: the pack ids of the
    summary, as a list (2 kept documents each) or as {pack: kept}; default: the packs of the rows. sep: the separator
    in part names."""
    rows = dict(ROWS) if rows is None else rows
    by_file = {}
    for name, n in rows.items():
        split, pack, file = name.split("/")
        by_file.setdefault((split, pack), []).extend([{"split": split, "part": f"{pack}{sep}{file}"}] * n)
    schema = pa.schema([("split", pa.string()), ("part", pa.string())])
    for (split, pack), docs in by_file.items():
        (folder / split).mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(docs, schema=schema), folder / split / f"{pack}.parquet")
    hashes = {name: sha_of(name) for name in rows} if hashes is None else hashes
    packs = sorted({n.split("/")[1] for n in rows}) if packs is None else packs
    packs = packs if isinstance(packs, dict) else {p: 2 for p in packs}
    summary = {"clean_mode": mode, "by_pack": {p: {"train": {"rows": kept + 1, "kept": kept}} for p, kept in packs.items()},
               "inputs": {"raw": {"path": "made up", "files": [{"part": n.replace("/", sep), "file": n, "sha256": h} for n, h in hashes.items()]}
                          if mode == "B" else None}}
    (folder / "ledger_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return folder


def write_shards(folder, parts=None):
    folder.mkdir(parents=True, exist_ok=True)
    if parts is None:
        parts = {n: {"pack_id": n.split("/")[1], "status": "written" if n.startswith("train/") else "not_sharded"} for n in ROWS}
    (folder / "shards_summary.json").write_text(json.dumps({"run_id": "made-up", "parts": parts}), encoding="utf-8")
    return folder


def failed(report):
    return [c["check"].removeprefix("inventory: ") for c in report["checks"] if not c["ok"]]


PACKS_CHECK = "every listed pack is in the ledger, and no other pack has kept documents"


@pytest.fixture
def sides(tmp_path):
    return write_ledger(tmp_path / "ledger"), write_shards(tmp_path / "shards")


# --- the whole check ----------------------------------------------------------------------------------------------
def test_a_run_that_matches_its_inventory_passes(tmp_path, sides):
    inv = ic.load(write_inventory(tmp_path))
    r = ic.check(inv, *sides)
    assert r["ok"] and len(r["checks"]) == 8 and all(c["check"].startswith("inventory: ") for c in r["checks"])
    assert r["inventory"] == {"file": (tmp_path / "expected_inventory.json").as_posix(), "sha256": inv["sha256"],
                              "input_manifest_sha256": MANIFEST, "packs": 2, "parts": 4, "expected": {"not_sharded": 1, "written": 3}}
    assert r["ledger"] == {"folder": sides[0].as_posix(), "clean_mode": "B", "parts": 4, "packs": 2, "rows": 14}
    assert r["shards"] == {"folder": sides[1].as_posix(), "parts": 4, "statuses": {"not_sharded": 1, "written": 3}}
    assert all(v == [] for v in r["differences"].values()) and len(r["differences"]) == 10
    assert r["tool"] == "inventory_check.py" and len(r["code_sha256"]) == 64


def test_one_side_alone_runs_only_its_checks(tmp_path, sides):
    inv = ic.load(write_inventory(tmp_path))
    ledger_only, shards_only = ic.check(inv, ledger=sides[0]), ic.check(inv, shards=sides[1])
    assert (len(ledger_only["checks"]), len(shards_only["checks"])) == (5, 3)
    assert "shards" not in ledger_only and "ledger" not in shards_only and ledger_only["ok"] and shards_only["ok"]


# --- the inventory file -------------------------------------------------------------------------------------------
def test_load_gives_one_shape_with_defaults(tmp_path):
    """split and pack_id may be left out (they are in the part's name); "_..." keys are comments, at the top and in a part."""
    parts = [entry(A, split=..., pack_id=..., _note="a comment"), entry(H, expected=["not_sharded", "empty"])]
    inv = ic.load(write_inventory(tmp_path, parts, packs=["code-go"], _made_by="a comment"))
    assert inv["packs"] == ["code-go"] and list(inv["parts"]) == [A, H]
    assert inv["parts"][A] == {"split": "train", "pack_id": "code-go", "expected": ["written"], "raw_sha256": sha_of(A), "raw_rows": 5}
    assert inv["parts"][H]["expected"] == ["empty", "not_sharded"]
    assert ic.described(inv)["expected"] == {"empty|not_sharded": 1, "written": 1}


def test_the_file_is_read_once_and_the_sha256_is_of_what_was_parsed(tmp_path, monkeypatch):
    file = write_inventory(tmp_path)
    content, reads = file.read_bytes(), []
    real = Path.read_bytes

    def counted(self):
        reads.append(self.name)
        return real(self)
    monkeypatch.setattr(Path, "read_bytes", counted)
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: pytest.fail("the inventory is read a second time"))
    inv = ic.load(file)
    assert reads == ["expected_inventory.json"] and inv["sha256"] == hashlib.sha256(content).hexdigest()


BAD = [
    ({"packs": ...}, "\"packs\" must be a list"), ({"packs": []}, "\"packs\" must be a list"),
    ({"packs": ["code-go", 3]}, "\"packs\" must be a list"), ({"packs": ["code-go", "en-dclm", "code-go"]}, "listed twice in \"packs\""),
    ({"parts": ...}, "\"parts\" must be a list"), ({"parts": []}, "\"parts\" must be a list"),
    ({"parts": ["train/code-go/part-00000.parquet"]}, "is not an object"),
    ({"input_manifest_sha256": "ABC"}, "input_manifest_sha256 must be 64"),
    ({"input_manifest_sha256": ...}, "input_manifest_sha256 is missing"), ({"input_manifest_sha256": None}, "input_manifest_sha256 is missing"),
    ({"packs": ["code-go", "en-dclm", "sci-x"]}, "pack 'sci-x' is in \"packs\" but no part is of it"),
    ({"manifest_sha256": MANIFEST}, "unknown key 'manifest_sha256'; an inventory has input_manifest_sha256, packs, parts"),
    ({"Packs": ["code-go"]}, "unknown key 'Packs'"),
]


@pytest.mark.parametrize("top, message", BAD)
def test_a_malformed_inventory_is_refused(tmp_path, top, message):
    with pytest.raises(ic.Stop, match=message):
        ic.load(write_inventory(tmp_path, **top))


BAD_PART = [
    ({"part": ...}, "expected <split>/<pack>/<file>.parquet"), ({"part": "code-go/part-00000.parquet"}, "expected <split>/<pack>"),
    ({"part": "test/code-go/part-00000.parquet"}, "split train or heldout"), ({"part": "train/code-go/part-00000.txt"}, "expected <split>"),
    ({"part": "train/../part-00000.parquet"}, "expected <split>"), ({"part": "train\\code-go\\part-00000.parquet"}, "expected <split>"),
    ({"part": A}, "is listed twice"), ({"split": "heldout"}, "\"split\" is 'heldout', the part is under train/"),
    ({"split": None}, "\"split\" is None"),
    ({"pack_id": "en-dclm"}, "\"pack_id\" is 'en-dclm', the part is under train/code-go/"), ({"pack_id": 7}, "\"pack_id\" is 7"),
    ({"part": "train/sci-x/part-00000.parquet", "pack_id": ...}, "its pack 'sci-x' is not in \"packs\""),
    ({"expected": ...}, "\"expected\" must be a status"), ({"expected": []}, "\"expected\" must be a status"),
    ({"expected": ["written", 1]}, "\"expected\" must be a status"), ({"expected": ""}, "\"expected\" must be a status"),
    ({"expected": "failed"}, "no run may expect"), ({"expected": ["written", "skipped"]}, "names 'skipped'"),
    ({"raw_sha256": "12ab"}, "raw_sha256 must be 64"), ({"raw_sha256": "G" * 64}, "raw_sha256 must be 64"),
    ({"raw_sha256": ...}, "raw_sha256 is missing .the sha256 of the raw part."), ({"raw_sha256": None}, "raw_sha256 is missing"),
    ({"raw_rows": ...}, "raw_rows is missing .the rows of the raw part."), ({"raw_rows": None}, "raw_rows is missing"),
    ({"raw_rows": -1}, "raw_rows is -1"), ({"raw_rows": 2.0}, "raw_rows is 2.0"), ({"raw_rows": True}, "raw_rows is True"),
    # the input manifest's own names for the two fields: left as they are, nothing would be compared
    ({"raw_sha256": ..., "sha256": "0" * 64}, "unknown key 'sha256'; a part has part, expected, raw_sha256, raw_rows, split, pack_id"),
    ({"raw_rows": ..., "rows": 3}, "unknown key 'rows'"), ({"status": "written"}, "unknown key 'status'"),
]


@pytest.mark.parametrize("change, message", BAD_PART)
def test_a_malformed_part_is_refused(tmp_path, change, message):
    parts = [entry(A), entry(B, **change), entry(H), entry(E)]
    packs = ["code-go", "en-dclm"]  # as they are, so that only the part is wrong
    with pytest.raises(ic.Stop, match=message):
        ic.load(write_inventory(tmp_path, parts, packs=packs))


def test_a_file_that_is_not_an_inventory_is_refused(tmp_path):
    with pytest.raises(ic.Stop, match="is not a file"):
        ic.load(tmp_path / "nope.json")
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ic.Stop, match="is not valid JSON"):
        ic.load(tmp_path / "bad.json")
    (tmp_path / "list.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ic.Stop, match="expected a JSON object"):
        ic.load(tmp_path / "list.json")


# --- the ledger side ----------------------------------------------------------------------------------------------
def test_a_listed_part_the_ledger_lacks_fails_and_is_named(tmp_path, sides):
    extra = "train/code-go/part-00002.parquet"
    inv = ic.load(write_inventory(tmp_path, [entry(p) for p in (A, B, H, E, extra)]))
    r = ic.check(inv, ledger=sides[0])
    assert failed(r) == ["the ledger holds exactly the listed parts"] and r["differences"]["ledger_parts_missing"] == [extra]
    detail = next(c["detail"] for c in r["checks"] if not c["ok"])
    assert detail == f"1 listed part(s) not in the ledger, e.g. {extra}; 0 ledger part(s) not listed"


def test_a_ledger_part_that_is_not_listed_fails_and_is_named(tmp_path, sides):
    inv = ic.load(write_inventory(tmp_path, [entry(p) for p in (A, H, E)]))
    r = ic.check(inv, ledger=sides[0])
    assert failed(r) == ["the ledger holds exactly the listed parts"] and r["differences"]["ledger_parts_unlisted"] == [B]
    assert f"1 ledger part(s) not listed, e.g. {B}" in next(c["detail"] for c in r["checks"] if not c["ok"])


def test_a_listed_pack_missing_from_the_ledger_fails(tmp_path):
    inv = ic.load(write_inventory(tmp_path))
    r = ic.check(inv, ledger=write_ledger(tmp_path / "ledger", packs=["code-go"]))
    assert failed(r) == [PACKS_CHECK] and r["differences"]["ledger_packs_missing"] == ["en-dclm"]
    assert r["checks"][2]["detail"] == "1 listed pack(s) not in the ledger, e.g. en-dclm; 0 pack(s) that are not listed have kept documents"


def test_a_pack_that_is_not_listed_fails_only_when_it_has_kept_documents(tmp_path):
    """A document with another pack_id inside a listed part: when the cleaner dropped it (or dedup or F2 took it out),
    nothing of that pack goes on; when one was kept, an unlisted pack would reach the shards."""
    inv = ic.load(write_inventory(tmp_path))
    r = ic.check(inv, ledger=write_ledger(tmp_path / "l1", packs={"code-go": 2, "en-dclm": 2, "ghost-pack": 0}))
    assert r["ok"] and r["differences"]["ledger_packs_unlisted"] == []
    assert r["checks"][2]["detail"] == "all 2 listed packs; 1 other pack id(s) among the documents, none kept, e.g. ghost-pack"
    r = ic.check(inv, ledger=write_ledger(tmp_path / "l2", packs={"code-go": 2, "en-dclm": 2, "ghost-pack": 3}))
    assert failed(r) == [PACKS_CHECK] and r["differences"]["ledger_packs_unlisted"] == [{"pack": "ghost-pack", "kept": 3}]
    assert r["checks"][2]["detail"] == ("0 listed pack(s) not in the ledger; 1 pack(s) that are not listed have kept documents, "
                                        "e.g. ghost-pack (3 kept)")
    assert ic.check(inv, ledger=write_ledger(tmp_path / "l3"))["checks"][2]["detail"] == "all 2 listed packs, and no other"


def test_another_raw_file_or_another_row_count_fails_and_says_both_values(tmp_path):
    inv = ic.load(write_inventory(tmp_path))
    other = {n: ("0" * 64 if n == B else sha_of(n)) for n in ROWS}
    r = ic.check(inv, ledger=write_ledger(tmp_path / "l1", hashes=other))
    assert failed(r) == ["each part's raw file is the listed one (sha256)"]
    assert r["differences"]["raw_sha256"] == [{"part": B, "ledger": "0" * 64, "listed": sha_of(B)}]
    assert f"1 of 4 part(s) differ, e.g. {B}: ledger read 000000000000…, listed {sha_of(B)[:12]}…" in json.dumps(r, ensure_ascii=False)
    r = ic.check(inv, ledger=write_ledger(tmp_path / "l2", rows={**ROWS, E: 9}))
    assert failed(r) == ["each part's raw rows are the listed ones"]
    assert r["differences"]["raw_rows"] == [{"part": E, "ledger": 9, "listed": 4}]


def test_a_raw_file_the_ledger_recorded_no_hash_for_differs(tmp_path):
    """Every listed part is compared on its raw sha256: a part without a recorded hash is a difference, not a skip."""
    hashes = {n: sha_of(n) for n in ROWS if n != H}
    r = ic.check(ic.load(write_inventory(tmp_path)), ledger=write_ledger(tmp_path / "ledger", hashes=hashes))
    assert failed(r) == ["each part's raw file is the listed one (sha256)"]
    assert r["differences"]["raw_sha256"] == [{"part": H, "ledger": None, "listed": sha_of(H)}]
    assert f"{H}: ledger read none, listed" in r["checks"][3]["detail"]


def test_a_raw_part_without_rows_is_still_a_part_of_the_ledger(tmp_path):
    """ledger.py lists every raw file it read; a raw part with no document has no row in the Parquet."""
    empty = "train/en-dclm/part-00001.parquet"
    ledger = write_ledger(tmp_path / "ledger", hashes={**{n: sha_of(n) for n in ROWS}, empty: sha_of(empty)})
    inv = ic.load(write_inventory(tmp_path, [entry(p) for p in (A, B, H, E)] + [entry(empty, raw_rows=0)]))
    assert ic.check(inv, ledger=ledger)["ok"]
    inv = ic.load(write_inventory(tmp_path, [entry(p) for p in (A, B, H, E)] + [entry(empty, raw_rows=6)]))
    assert ic.check(inv, ledger=ledger)["differences"]["raw_rows"] == [{"part": empty, "ledger": 0, "listed": 6}]


def test_a_pack_whose_parts_all_list_no_rows_need_not_be_in_the_ledger(tmp_path):
    empty = "train/sci-x/part-00000.parquet"
    ledger = write_ledger(tmp_path / "ledger", hashes={**{n: sha_of(n) for n in ROWS}, empty: sha_of(empty)})
    inv = ic.load(write_inventory(tmp_path, [entry(p) for p in (A, B, H, E)] + [entry(empty, raw_rows=0)]))
    assert ic.check(inv, ledger=ledger)["ok"]
    inv = ic.load(write_inventory(tmp_path, [entry(p) for p in (A, B, H, E)] + [entry(empty, raw_rows=1)]))
    assert PACKS_CHECK in failed(ic.check(inv, ledger=ledger))  # with a row listed, the pack must be there


def test_a_ledger_without_the_raw_parts_fails(tmp_path):
    """Mode C: the ledger starts at the cleaned documents, so the raw rows and hashes cannot be checked."""
    r = ic.check(ic.load(write_inventory(tmp_path)), ledger=write_ledger(tmp_path / "ledger", mode="C"))
    assert failed(r) == ["the ledger accounts for every raw document (mode B)", "each part's raw file is the listed one (sha256)",
                         "each part's raw rows are the listed ones"]
    assert "not checked" in r["checks"][3]["detail"] and "not checked" in r["checks"][4]["detail"]


def test_part_names_with_backslashes_in_the_ledger_are_the_same_parts(tmp_path):
    """In the summary's raw files and in the Parquet's part column alike."""
    r = ic.check(ic.load(write_inventory(tmp_path)), ledger=write_ledger(tmp_path / "ledger", sep="\\"))
    assert r["ok"] and r["ledger"]["parts"] == 4


def test_a_folder_that_is_not_a_ledger_stops(tmp_path, sides):
    inv = ic.load(write_inventory(tmp_path))
    with pytest.raises(ic.Stop, match="no ledger_summary.json"):
        ic.check(inv, ledger=tmp_path / "nowhere")
    (sides[0] / "train" / "code-go.parquet").write_bytes(b"not parquet")
    with pytest.raises(ic.Stop, match="code-go.parquet cannot be read as a ledger file"):
        ic.check(inv, ledger=sides[0])
    only_summary = tmp_path / "only"
    only_summary.mkdir()
    (only_summary / "ledger_summary.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ic.Stop, match="no <split>/<pack>.parquet files"):
        ic.check(inv, ledger=only_summary)


@pytest.mark.parametrize("summary, message", [
    ([], "the ledger's summary .* is not a JSON object"), ("made up", "is not a JSON object"),
    ({"clean_mode": "B", "inputs": {"raw": {"files": [{"sha256": "0" * 64}]}}}, "inputs.raw.files is not a list of .part, sha256. entries"),
    ({"clean_mode": "B", "inputs": {"raw": {"files": {"a": 1}}}}, "inputs.raw.files is not a list"),
    ({"clean_mode": "B", "by_pack": ["code-go"]}, "by_pack is not .pack: .split: counts.."),
    ({"clean_mode": "B", "by_pack": {"code-go": {"train": 3}}}, "by_pack is not"),
    ({"clean_mode": "B", "by_pack": {"code-go": {"train": {"kept": "3"}}}}, "by_pack 'code-go' has a kept count that is not a whole number"),
    # a pack without a usable kept count is not read as a pack with nothing kept (it could be an unlisted one)
    ({"clean_mode": "B", "by_pack": {"ghost-pack": {"train": {"rows": 3}}}}, "by_pack 'ghost-pack' has a kept count that is not a whole number >= 0"),
    ({"clean_mode": "B", "by_pack": {"ghost-pack": {"train": {"kept": None}}}}, "by_pack 'ghost-pack' has a kept count"),
    ({"clean_mode": "B", "by_pack": {"ghost-pack": {"train": {"kept": 2}, "heldout": {"kept": -2}}}}, "by_pack 'ghost-pack' has a kept count"),
])
def test_a_ledger_summary_that_is_not_what_ledger_py_writes_stops_with_a_message(tmp_path, sides, summary, message):
    (sides[0] / "ledger_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ic.Stop, match=message):
        ic.check(ic.load(write_inventory(tmp_path)), ledger=sides[0])


# --- the shard side -----------------------------------------------------------------------------------------------
def summary_parts(**change):
    parts = {n: {"pack_id": n.split("/")[1], "status": "written" if n.startswith("train/") else "not_sharded"} for n in ROWS}
    for name, e in change.items():
        if e is None:
            parts.pop(name)
        else:
            parts[name] = e
    return parts


def test_a_listed_part_missing_from_the_shard_summary_fails_and_so_does_an_unlisted_one(tmp_path):
    inv = ic.load(write_inventory(tmp_path))
    r = ic.check(inv, shards=write_shards(tmp_path / "s1", summary_parts(**{E: None})))
    assert failed(r) == ["the shard summary holds exactly the listed parts"] and r["differences"]["shard_parts_missing"] == [E]
    other = "train/en-dclm/part-00007.parquet"
    r = ic.check(inv, shards=write_shards(tmp_path / "s2", summary_parts(**{other: {"pack_id": "en-dclm", "status": "written"}})))
    assert failed(r) == ["the shard summary holds exactly the listed parts"] and r["differences"]["shard_parts_unlisted"] == [other]
    assert f"1 part(s) in it not listed, e.g. {other}" in r["checks"][0]["detail"]


@pytest.mark.parametrize("status", ["failed", "skipped", "not_sharded", "writen", None])
def test_a_part_that_ended_in_another_status_fails_and_says_both(tmp_path, status):
    inv = ic.load(write_inventory(tmp_path))
    r = ic.check(inv, shards=write_shards(tmp_path / "shards", summary_parts(**{B: {"pack_id": "code-go", "status": status}})))
    assert failed(r) == ["every part ended in a listed status"]
    assert r["differences"]["status"] == [{"part": B, "status": status, "listed": ["written"]}]
    assert r["checks"][1]["detail"] == f"1 of 4 part(s) differ, e.g. {B}: status {status!r}, listed written"


def test_a_list_of_statuses_accepts_any_of_them(tmp_path):
    """A status the shard writer gets later (a part with no document left) needs only the inventory to list it."""
    shards = write_shards(tmp_path / "shards", summary_parts(**{B: {"pack_id": "code-go", "status": "empty"}}))
    one = ic.load(write_inventory(tmp_path, [entry(A), entry(B), entry(H), entry(E)], name="one.json"))
    assert failed(ic.check(one, shards=shards)) == ["every part ended in a listed status"]
    two = ic.load(write_inventory(tmp_path, [entry(A), entry(B, expected=["written", "empty"]), entry(H), entry(E)], name="two.json"))
    assert ic.check(two, shards=shards)["ok"]


def test_a_part_of_another_pack_than_listed_fails_and_so_does_an_entry_without_a_pack(tmp_path):
    inv = ic.load(write_inventory(tmp_path))
    r = ic.check(inv, shards=write_shards(tmp_path / "s1", summary_parts(**{A: {"pack_id": "en-dclm", "status": "written"}})))
    assert failed(r) == ["every part is of its listed pack"]
    assert r["differences"]["pack"] == [{"part": A, "pack_id": "en-dclm", "listed": "code-go"}]
    r = ic.check(inv, shards=write_shards(tmp_path / "s2", summary_parts(**{A: {"status": "written"}})))
    assert failed(r) == ["every part is of its listed pack"]
    assert r["differences"]["pack"] == [{"part": A, "pack_id": None, "listed": "code-go"}]
    assert r["checks"][2]["detail"] == f"1 of 4 part(s) differ, e.g. {A}: pack_id None, listed 'code-go'"


def test_part_names_with_backslashes_are_the_same_parts(tmp_path):
    parts = {n.replace("/", "\\"): e for n, e in summary_parts().items()}
    assert ic.check(ic.load(write_inventory(tmp_path)), shards=write_shards(tmp_path / "shards", parts))["ok"]


def test_a_folder_without_a_shard_summary_stops(tmp_path):
    inv = ic.load(write_inventory(tmp_path))
    with pytest.raises(ic.Stop, match="no shards_summary.json"):
        ic.check(inv, shards=tmp_path / "nowhere")
    for n, (summary, message) in enumerate((({"parts": []}, "has no \"parts\" object"), ({"parts": {"a": 1}}, "has no \"parts\" object"),
                                            ({"run_id": "made-up"}, "has no \"parts\" object"), ([], "the shard summary .* is not a JSON object"))):
        folder = tmp_path / f"s{n}"
        folder.mkdir()
        (folder / "shards_summary.json").write_text(json.dumps(summary), encoding="utf-8")
        with pytest.raises(ic.Stop, match=message):
            ic.check(inv, shards=folder)


# --- the input manifest (the clean job's summary) -----------------------------------------------------------------
MANIFEST_CHECK = "made from the input manifest the clean job read"


def cleaned_folder(tmp_path, summary):
    folder = tmp_path / "cleaned"
    folder.mkdir(exist_ok=True)
    (folder / "job_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return folder


def test_the_inventory_must_be_of_the_input_manifest_the_clean_job_read(tmp_path, sides):
    inv = ic.load(write_inventory(tmp_path))
    r = ic.check(inv, *sides, cleaned=cleaned_folder(tmp_path, {"manifest_sha256": MANIFEST}))
    assert r["ok"] and r["checks"][0]["check"] == "inventory: " + MANIFEST_CHECK and len(r["checks"]) == 9
    assert r["differences"]["input_manifest_sha256"] == [] and len(r["differences"]) == 11
    r = ic.check(inv, *sides, cleaned=cleaned_folder(tmp_path, {"manifest_sha256": "cd" * 32}))
    assert failed(r) == [MANIFEST_CHECK]
    assert r["checks"][0]["detail"] == "clean job manifest_sha256 cdcdcdcdcdcd…, inventory input_manifest_sha256 abababababab…"
    assert r["differences"]["input_manifest_sha256"] == [{"clean_job": "cd" * 32, "listed": MANIFEST}]


def test_a_clean_job_that_names_no_input_manifest_fails_the_check(tmp_path, sides):
    """The comparison is never left out: a summary without manifest_sha256, or no summary at all, is a failed check."""
    inv = ic.load(write_inventory(tmp_path))
    r = ic.check(inv, *sides, cleaned=cleaned_folder(tmp_path, {"clean_sha256": "c" * 64}))
    assert failed(r) == [MANIFEST_CHECK] and len(r["checks"]) == 9
    assert r["checks"][0]["detail"].startswith("the clean job's job_summary.json records no manifest_sha256; inventory")
    assert r["differences"]["input_manifest_sha256"] == [{"clean_job": None, "listed": MANIFEST}]
    r = ic.check(inv, *sides, cleaned=tmp_path / "no-such-folder")
    assert failed(r) == [MANIFEST_CHECK] and r["checks"][0]["detail"].startswith("the cleaned folder has no job_summary.json")
    with pytest.raises(ic.Stop, match="the clean job's summary .* is not a JSON object"):
        ic.check(inv, *sides, cleaned=cleaned_folder(tmp_path, ["made up"]))
    assert len(ic.check(inv, *sides)["checks"]) == 8  # without the cleaned folder the manifest is not compared at all


# --- the command line ---------------------------------------------------------------------------------------------
def cli(*args):
    return subprocess.run([sys.executable, "-B", str(PIPELINE / "inventory_check.py"), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def test_cli_writes_the_report_and_exits_0_or_1(tmp_path, sides):
    good = cli("--inventory", write_inventory(tmp_path), "--ledger", sides[0], "--shards", sides[1], "--out", tmp_path / "r" / "report.json")
    assert good.returncode == 0 and json.loads(good.stdout) == {"ok": True, "checks": 8, "failed": 0, "parts": 4, "packs": 2}
    assert json.loads((tmp_path / "r" / "report.json").read_text(encoding="utf-8"))["ok"] is True
    assert sorted(p.name for p in (tmp_path / "r").iterdir()) == ["report.json"]  # no .tmp left
    short = write_inventory(tmp_path, [entry(p) for p in (A, H, E)], name="short.json")
    bad = cli("--inventory", short, "--ledger", sides[0], "--shards", sides[1], "--out", tmp_path / "bad.json")
    assert bad.returncode == 1 and json.loads(bad.stdout.splitlines()[0])["failed"] == 2
    assert "inventory_check: inventory: the ledger holds exactly the listed parts" in bad.stderr and B in bad.stderr
    report = json.loads((tmp_path / "bad.json").read_text(encoding="utf-8"))
    assert report["ok"] is False and report["differences"]["shard_parts_unlisted"] == [B]


def test_cli_with_the_cleaned_folder_checks_the_input_manifest(tmp_path, sides):
    inv = write_inventory(tmp_path)
    good = cli("--inventory", inv, "--ledger", sides[0], "--shards", sides[1], "--cleaned", cleaned_folder(tmp_path, {"manifest_sha256": MANIFEST}))
    assert good.returncode == 0 and json.loads(good.stdout)["checks"] == 9
    other = cli("--inventory", inv, "--ledger", sides[0], "--cleaned", cleaned_folder(tmp_path, {"manifest_sha256": "cd" * 32}))
    assert other.returncode == 1 and "made from the input manifest the clean job read: clean job manifest_sha256 cdcdcdcdcdcd" in other.stderr
    none = cli("--inventory", inv, "--ledger", sides[0], "--cleaned", cleaned_folder(tmp_path, {}))
    assert none.returncode == 1 and "records no manifest_sha256" in none.stderr


def test_cli_needs_something_to_check_against_and_names_an_unreadable_input(tmp_path, sides):
    inv = write_inventory(tmp_path)
    nothing = cli("--inventory", inv)
    assert nothing.returncode == 2 and "give --ledger, --shards or both" in nothing.stderr
    missing = cli("--inventory", tmp_path / "nope.json", "--ledger", sides[0])
    assert missing.returncode == 1 and "inventory_check: " in missing.stderr and "is not a file" in missing.stderr
    no_ledger = cli("--inventory", inv, "--ledger", tmp_path / "nowhere")
    assert no_ledger.returncode == 1 and "no ledger_summary.json" in no_ledger.stderr
    (sides[1] / "shards_summary.json").write_text("[]", encoding="utf-8")
    not_object = cli("--inventory", inv, "--shards", sides[1])
    assert not_object.returncode == 1 and "is not a JSON object" in not_object.stderr and "Traceback" not in not_object.stderr
