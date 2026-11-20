"""Tests for pack_table.py and pack_table.json (the real table, plus made-up tables for the errors).

  python -m pytest teams/01-data-a/shards/tests/test_pack_table.py
"""
import json
import sys
from pathlib import Path

import pytest

SHARDS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARDS))
sys.path.insert(0, str(SHARDS.parent / "spec_v1"))
import pack_table  # noqa: E402

SCRIPT = {"bn": "Beng", "gu": "Gujr", "hi": "Deva", "kn": "Knda", "ml": "Mlym", "mr": "Deva", "or": "Orya", "sa": "Deva",
          "ta": "Taml", "te": "Telu"}


@pytest.fixture(scope="module")
def table():
    return pack_table.load()


def test_table_has_the_38_week2_packs(table):
    kinds = {k: sorted(p for p in table if p.startswith(k + "-")) for k in ("cadj", "code", "en", "ind", "math", "sci")}
    assert [len(v) for v in kinds.values()] == [3, 6, 4, 22, 2, 1]
    assert sum(len(v) for v in kinds.values()) == len(table) == 38


def test_domain_agrees_with_clean_py(table):
    clean = pytest.importorskip("clean")
    for pack, family in clean._FAMILY.items():
        assert table[pack]["domain"] == family, pack


def test_indic_rows_follow_the_pack_name(table):
    for pack, r in table.items():
        if pack.startswith("ind-"):
            lang = pack.split("-")[1]
            assert (r["language"], r["script"], r["domain"]) == (lang, SCRIPT[lang], "indic"), pack


def test_code_rows_follow_the_pack_name(table):
    for pack, r in table.items():
        if pack.startswith("code-"):
            assert r == {"language": pack[5:], "script": "Latn", "domain": "code", "lane": "code"}, pack


def test_row_matches_the_committed_sample():
    sample = json.loads((SHARDS / "sample" / "code-go-train-000000.json").read_text(encoding="utf-8"))
    r = pack_table.row("code-go")
    assert r == {k: sample[v] for k, v in (("language", "language"), ("script", "script"), ("domain", "domain"),
                                           ("lane", "capability_lane"))}


def test_every_pack_has_a_lane_from_the_agreed_six(table):
    assert pack_table.LANES == ("code", "code-adjacent", "english", "indic", "math", "science")
    assert {pack: r["lane"] for pack, r in table.items() if r["lane"] not in pack_table.LANES} == {}


def test_lane_counts_and_rule(table):
    lane_of = {"cadj": "code-adjacent", "code": "code", "en": "english", "ind": "indic", "math": "math", "sci": "science"}
    for pack, r in table.items():
        assert r["lane"] == lane_of[pack.split("-")[0]], pack
    counts = {lane: sum(r["lane"] == lane for r in table.values()) for lane in pack_table.LANES}
    assert counts == {"code": 6, "code-adjacent": 3, "english": 4, "indic": 22, "math": 2, "science": 1}


def test_a_null_lane_is_refused(tmp_path):
    table = table_of(tmp_path, {"en-dclm": {**LICENSED, "lane": None}})
    with pytest.raises(pack_table.PackTableError, match="en-dclm has no lane"):
        pack_table.row("en-dclm", table)


@pytest.mark.parametrize("lane", ["general_language", "code_adjacent", "indic_hi", "general", "test", "Code"])
def test_a_lane_outside_the_agreed_six_is_refused_in_every_table(tmp_path, lane):
    with pytest.raises(pack_table.PackTableError, match="en-dclm.lane is .* expected one of code, code-adjacent"):
        table_of(tmp_path, {"en-dclm": {**LICENSED, "lane": lane}})


def test_an_unknown_pack_is_refused(table):
    with pytest.raises(pack_table.PackTableError, match="no-such-pack is not in pack_table.json"):
        pack_table.row("no-such-pack", table)


def test_row_is_a_copy(table):
    pack_table.row("code-go", table)["lane"] = "changed"
    assert table["code-go"]["lane"] == "code"


@pytest.mark.parametrize("bad, message", [
    ({"language": "go", "script": "Latn", "domain": "code"}, "has fields"),
    ({"language": "go", "script": "Latn", "domain": "code", "lane": "code", "x": "y"}, "has fields"),
    ({"language": "", "script": "Latn", "domain": "code", "lane": "code"}, "non-empty string or null"),
    ({"language": "go", "script": 7, "domain": "code", "lane": "code"}, "non-empty string or null"),
])
def test_a_malformed_row_is_refused(tmp_path, bad, message):
    path = tmp_path / "t.json"
    path.write_text(json.dumps({"packs": {"code-go": bad}}), encoding="utf-8")
    with pytest.raises(pack_table.PackTableError, match=message):
        pack_table.load(path)


LICENSED = {"language": "go", "script": "Latn", "domain": "code", "lane": "code",
            "license": "apache-2.0", "license_source": "licence_table.md at fb7d5e6"}


def table_of(tmp_path, rows):
    path = tmp_path / "t.json"
    path.write_text(json.dumps({"_comment": "a job's pack table", "packs": rows}), encoding="utf-8")
    return pack_table.load(path)


def test_a_table_with_licences_gives_them_in_the_row(tmp_path):
    """The shard job's table: a row also names the pack's licence and where that licence is recorded."""
    table = table_of(tmp_path, {"code-go": LICENSED, "en-dclm": {k: LICENSED[k] for k in pack_table.FIELDS}})
    assert pack_table.row("code-go", table) == LICENSED
    assert set(pack_table.row("en-dclm", table)) == set(pack_table.FIELDS)  # a row without them stays as it was


@pytest.mark.parametrize("field", ["license", "license_source", "lane"])
def test_a_null_licence_is_refused_like_a_null_lane(tmp_path, field):
    table = table_of(tmp_path, {"code-go": {**LICENSED, field: None}})
    with pytest.raises(pack_table.PackTableError, match=f"code-go has no {field} in pack_table.json"):
        pack_table.row("code-go", table)


@pytest.mark.parametrize("drop", ["license", "license_source"])
def test_a_licence_without_where_it_is_recorded_is_refused(tmp_path, drop):
    with pytest.raises(pack_table.PackTableError, match="has fields .*with or without license and license_source"):
        table_of(tmp_path, {"code-go": {k: v for k, v in LICENSED.items() if k != drop}})


def test_a_row_that_is_not_an_object_is_refused(tmp_path):
    with pytest.raises(pack_table.PackTableError, match="code-go has fields str"):
        table_of(tmp_path, {"code-go": "go"})
