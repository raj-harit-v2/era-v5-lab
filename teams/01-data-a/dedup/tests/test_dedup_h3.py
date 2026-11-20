"""Tests for H3 in dedup.py (h3_join.py) on small made-up runs (no real data).
Run: python -m pytest -q teams/01-data-a/dedup/tests"""
import csv
import json

import pytest

pytest.importorskip("pyarrow")
from test_dedup import config, make_run, repo  # noqa: E402,F401  (repo is a fixture)
import dedup  # noqa: E402

HEADER = ["pack_id_a", "split_a", "part_a", "row_in_part_a", "doc_id_a",
          "pack_id_b", "split_b", "part_b", "row_in_part_b", "doc_id_b", "lang_a", "lang_b", "coverage"]


def key(docs, i):
    """(pack_id, split, part, row_in_part, doc_id) of docs[i], as make_run numbers rows."""
    d, p, s, _ = docs[i]
    return [p, s, f"{p}/part-00000.parquet", sum(1 for x in docs[:i] if x[1] == p and x[2] == s), d]


def write_h3(root, docs, edges, header=HEADER):
    """edges: [(i, j, coverage)]."""
    p = root / "res" / "h3_matches.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for i, j, cov in edges:
            w.writerow(key(docs, i) + key(docs, j) + ["hin_Deva", "eng_Latn", cov])
    return "res/h3_matches.csv"


def run(repo, **over):
    s = dedup.run(dedup.load_config(config(repo, **over)))
    out = repo / "out/dedup"
    log = [json.loads(l) for l in (out / "dedup_log.jsonl").read_text(encoding="utf-8").splitlines()]
    pairs = list(csv.DictReader((out / "h3_pairs.csv").open(encoding="utf-8"))) if (out / "h3_pairs.csv").exists() else None
    return s, {e["removed_id"]: e for e in log}, pairs


DOCS = [("h", "ind-x-fw2", "heldout", 100), ("t", "en-a", "train", 100)]


def test_report_only_by_default(repo):
    make_run(repo, DOCS, [])
    s, log, pairs = run(repo, h3={"matches": write_h3(repo, DOCS, [(0, 1, 0.8)])})
    assert log == {} and s["removed"] == 0
    assert pairs[0]["outcome"] == "would_remove" and s["h3"]["outcomes"]["would_remove"] == 1


def test_train_translation_of_heldout_is_removed_when_allowed(repo):
    make_run(repo, DOCS, [])
    s, log, pairs = run(repo, h3={"matches": write_h3(repo, DOCS, [(0, 1, 0.8)]), "remove": True})
    assert set(log) == {"t"}
    e = log["t"]
    assert (e["rule"], e["stage"], e["priority_rule"], e["kept_id"], e["similarity"]) == ("H3", "cross_language", 0, "h", 0.8)
    assert s["heldout_removed"] == 0 and s["by_pack"]["en-a"]["removed_H3"] == 1
    assert pairs[0]["outcome"] == "removed"


def _roles(repo):
    return {r["doc_id"]: r["role"] for r in csv.DictReader((repo / "out/dedup/dedup_groups.csv").open(encoding="utf-8"))}


def _removed(repo):
    return sorted(r["doc_id"] for r in csv.DictReader((repo / "out/dedup/remove_list.csv").open(encoding="utf-8")))


@pytest.mark.parametrize("remove", [False, True])
def test_only_direct_edges_remove_group_survivor_stays(repo, remove):
    # TSAI, #625, 19 Nov: only direct edges remove. a and b are H2 copies (b survives, rule 3); H3 matches a, already
    # removed by H2, with held-out h. b was never matched with h, so it stays, in both modes
    docs = [("a", "en-a", "train", 100), ("b", "en-a", "train", 120), ("h", "ind-x-fw2", "heldout", 100)]
    make_run(repo, docs, [(0, 1, "H2", 0.9, "")])
    s, log, pairs = run(repo, h3={"matches": write_h3(repo, docs, [(0, 2, 0.75)]), "remove": remove})
    assert set(log) == {"a"} and log["a"]["rule"] == "H2"
    assert pairs[0]["outcome"] == "already_removed"
    assert _roles(repo) == {"a": "removed", "b": "survivor"} and _removed(repo) == ["a"]
    assert s["h3"]["removed"] == 0 and s["h3"]["train_docs_targeted"] == 0 and s["h3"]["groups_survivor_removed"] == 0


def test_direct_edge_to_group_survivor_removes_only_it(repo):
    # H3 matches b, the survivor of H2 group {a, b}, with held-out h: b goes, a was already removed by H2
    docs = [("a", "en-a", "train", 100), ("b", "en-a", "train", 120), ("h", "ind-x-fw2", "heldout", 100)]
    make_run(repo, docs, [(0, 1, "H2", 0.9, "")])
    s, log, pairs = run(repo, h3={"matches": write_h3(repo, docs, [(1, 2, 0.75)]), "remove": True})
    assert log["b"]["rule"] == "H3" and log["b"]["kept_id"] == "h" and pairs[0]["outcome"] == "removed"
    assert _roles(repo) == {"a": "removed", "b": "removed"} and s["h3"]["groups_survivor_removed"] == 1
    assert _removed(repo) == ["a", "b"] and s["h3"]["train_docs_targeted"] == 1


def test_chain_through_heldout_copy_is_reported_not_removed(repo):
    # c is an H1 copy of held-out h (h survives, rule 0); H3 matches c with train t. t was never matched with h
    # itself, so it stays: reported_indirect
    docs = [("h", "ind-x-fw2", "heldout", 100), ("c", "ind-x-fw2", "train", 100), ("t", "en-a", "train", 100)]
    make_run(repo, docs, [(0, 1, "H1", 1.0, "")])
    s, log, pairs = run(repo, h3={"matches": write_h3(repo, docs, [(1, 2, 0.8)]), "remove": True})
    assert set(log) == {"c"} and pairs[0]["outcome"] == "reported_indirect" and s["h3"]["removed"] == 0


def test_report_only_counts_match_remove_mode(repo):
    # would_remove and removed pick the same edges; two edges to one train doc count it once
    docs = [("h1", "ind-x-fw2", "heldout", 100), ("h2", "ind-x-fw2", "heldout", 110), ("t", "en-a", "train", 100)]
    make_run(repo, docs, [])
    edges = [(0, 2, 0.8), (1, 2, 0.7)]
    s0, _, p0 = run(repo, h3={"matches": write_h3(repo, docs, edges)})
    s1, log, p1 = run(repo, h3={"matches": write_h3(repo, docs, edges), "remove": True})
    assert [p["outcome"] for p in p0] == ["would_remove"] * 2 and [p["outcome"] for p in p1] == ["removed"] * 2
    assert s0["h3"]["train_docs_targeted"] == s1["h3"]["train_docs_targeted"] == s1["h3"]["removed"] == 1
    assert set(log) == {"t"}


def test_heldout_heldout_and_train_train_are_reported_not_removed(repo):
    docs = [("h1", "ind-x-fw2", "heldout", 100), ("h2", "en-a", "heldout", 100),
            ("t1", "ind-x-fw2", "train", 100), ("t2", "en-b", "train", 100)]
    make_run(repo, docs, [])
    s, log, pairs = run(repo, h3={"matches": write_h3(repo, docs, [(0, 1, 0.9), (2, 3, 0.9)]), "remove": True})
    assert log == {} and s["heldout_removed"] == 0
    assert sorted(p["outcome"] for p in pairs) == ["reported_heldout_heldout", "reported_train_train"]


def test_parallel_pack_pairs_are_skipped(repo):
    docs = [("h", "ind-x-sangraha-v", "heldout", 100), ("t", "ind-x-sangraha-v", "train", 100)]
    make_run(repo, docs, [])
    s, log, pairs = run(repo, h3={"matches": write_h3(repo, docs, [(0, 1, 0.9)]), "remove": True,
                                  "parallel_packs": ["ind-x-sangraha-v"]})
    assert log == {} and pairs[0]["outcome"] == "parallel_pack"


def test_pair_inside_one_group_changes_nothing(repo):
    docs = [("a", "en-a", "train", 100), ("b", "en-b", "train", 120)]
    make_run(repo, docs, [(0, 1, "H2", 0.9, "")])
    s, log, pairs = run(repo, h3={"matches": write_h3(repo, docs, [(0, 1, 0.9)]), "remove": True})
    assert set(log) == {"a"} and log["a"]["rule"] == "H2" and pairs[0]["outcome"] == "same_group"


def test_doc_id_mismatch_stops(repo):
    make_run(repo, DOCS, [])
    p = write_h3(repo, DOCS, [(0, 1, 0.8)])
    f = repo / p
    f.write_text(f.read_text(encoding="utf-8").replace(",t,", ",zz,"), encoding="utf-8")
    with pytest.raises(dedup.Fatal, match="not in overlap_docs.parquet with the same doc_id"):
        run(repo, h3={"matches": p})


def test_bad_header_stops(repo):
    make_run(repo, DOCS, [])
    p = write_h3(repo, DOCS, [(0, 1, 0.8)], header=["row_a", "row_b"] + HEADER[2:])
    with pytest.raises(dedup.Fatal, match="header must be"):
        run(repo, h3={"matches": p})


def test_without_h3_nothing_changes(repo):
    make_run(repo, DOCS, [])
    s, _, pairs = run(repo)
    assert "h3" not in s and "h3" not in s["config"] and pairs is None
    assert "removed_H3" not in s["by_pack"]["en-a"]


def test_bad_h3_config_stops(repo):
    make_run(repo, DOCS, [])
    with pytest.raises(dedup.Fatal, match="h3.remove"):
        run(repo, h3={"matches": "res/x.csv", "remove": "yes"})
