"""Tests for cross_stage_overlap.py. Synthetic statements only (generated words, no real problem text)."""

import gzip
import hashlib
import json
import random
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cross_stage_overlap as co  # noqa: E402
import source_index as si  # noqa: E402


def vocab(seed: int, n: int) -> list[str]:
    rng = random.Random(seed)
    return ["".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(4, 9))) for _ in range(n)]


def statement(seed: int, n: int = 120) -> str:
    return " ".join(vocab(seed, n)) + "."


IO_FORMAT = ("Input The first line contains an integer T denoting the number of test cases. Each of the next T lines "
             "contains two integers A and B. Output For each test case print a single line with the answer.")


def test_exact_key_is_the_source_index_family_key():
    for text in ("a  b\n c", "é́ x", "  padded  "):
        assert co.exact_key(text) == si.family_sha256(text)


def test_same_problem_through_two_sources_matches():
    base = statement(1)
    # TACO-style copy: markup, math delimiters, headings, different whitespace
    taco = "-----Problem----- " + base.replace(" ", "  ", 5) + " -----Input----- $T$ cases"
    rl = {"rl-a": base}
    out = co.match(rl, {"taco-copy": taco, "other": statement(2)})
    assert [(m.pack_key, m.tier) for m in out["rl-a"]] == [("taco-copy", "shingle")]
    assert out["rl-a"][0].coverage > 0.9


def test_exact_and_normalised_tiers():
    base = statement(3)
    out = co.match({"r": base, "s": base.upper()}, {"p1": " ".join(base.split()), "p2": base.replace(".", " .")})
    assert {m.pack_key: m.tier for m in out["r"]} == {"p1": "key", "p2": "norm"}
    assert {m.pack_key: m.tier for m in out["s"]} == {"p1": "norm", "p2": "norm"}


def test_boilerplate_io_text_alone_does_not_match():
    a = statement(4, 60) + " " + IO_FORMAT
    b = statement(5, 60) + " " + IO_FORMAT
    out = co.match({"r": a}, {"p": b})
    assert co.confirmed_pack_keys(out.get("r", [])) == set()   # a 60-word statement shares ~30% of its shingles: `possible`, never a match
    assert co.best_tier(out["r"]) == "possible"
    # a realistic statement is mostly its own text: the shared format block is far below every tier
    long_a = statement(6, 200) + " " + IO_FORMAT
    long_b = statement(7, 200) + " " + IO_FORMAT
    assert co.best_tier(co.match({"r": long_a}, {"p": long_b}).get("r", [])) is None


def test_sibling_problems_are_only_possible():
    shared = vocab(8, 70)
    a = " ".join(vocab(9, 40) + shared + vocab(10, 20))
    b = " ".join(vocab(11, 40) + shared + vocab(12, 20))
    out = co.match({"r": a}, {"p": b})
    (m,) = out["r"]
    assert m.tier == "possible" and co.POSSIBLE <= m.coverage < co.CONFIRM
    assert co.best_tier(out["r"]) == "possible"
    assert co.confirmed_pack_keys(out["r"]) == set()


def test_short_statement_matches_only_by_key_or_norm():
    short = "print the sum of two numbers"
    out = co.match({"r": short}, {"p1": "Print the SUM of two numbers.", "p2": "print the sum of two numbers and then stop reading"})
    assert [(m.pack_key, m.tier) for m in out["r"]] == [("p1", "norm")]


def test_near_misses_are_returned_only_on_request():
    base = vocab(13, 100)
    rl = " ".join(base)
    pack = " ".join(base[:25] + vocab(14, 75))   # roughly 12 of 88 shingles: below POSSIBLE
    assert co.match({"r": rl}, {"p": pack}) == {}
    near = co.match({"r": rl}, {"p": pack}, floor=0.05)
    assert near["r"][0].tier == "near" and co.best_tier(near["r"]) is None


def test_thresholds_are_checked():
    with pytest.raises(ValueError):
        co.match({"r": "x"}, {"p": "y"}, confirm=0.1, possible=0.5)


def test_match_is_deterministic_and_order_free():
    texts = {f"r{i}": statement(100 + i) for i in range(6)}
    pack = {f"p{i}": (texts[f"r{i}"] if i % 2 else statement(200 + i)) for i in range(6)}
    first = co.match(texts, pack)
    shuffled_rl = dict(reversed(list(texts.items())))
    shuffled_pack = dict(reversed(list(pack.items())))
    second = co.match(shuffled_rl, shuffled_pack)
    assert {k: v for k, v in first.items()} == {k: v for k, v in second.items()}
    assert first == co.match(texts, pack)


# --- the record, end to end on a toy build -----------------------------------------------------

def _toy(tmp_path: Path):
    """Three RL problems; a pack of four families: one by exact text (via code_contests rows), one copy through TACO, one
    sibling, one unrelated. Two shards of row stats."""
    rl = {"cc-one": statement(20), "cc-two": statement(21), "cc-three": statement(22), "cc-four": statement(23)}
    shared = vocab(24, 70)
    sibling = " ".join(vocab(25, 40) + shared + vocab(26, 20))
    rl["cc-three"] = " ".join(vocab(27, 40) + shared + vocab(28, 20))
    pack_text = {
        "A": rl["cc-one"],                                    # same text, reached through code_contests rows
        "B": "-----Problem----- " + rl["cc-two"].replace(" ", "  ", 4),   # same problem, TACO markup
        "C": sibling,                                         # sibling of cc-three
        "D": statement(29),                                   # unrelated
    }
    fam = {k: hashlib.sha256(" ".join(v.split()).encode()).hexdigest() for k, v in pack_text.items()}
    db = tmp_path / "idx.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE rows (source_key TEXT, ordinal INTEGER, file_ordinal INTEGER, local_ordinal INTEGER,"
                " problem_id TEXT, question TEXT, question_sha256 TEXT, family_sha256 TEXT)")
    for i, (k, v) in enumerate(pack_text.items()):
        con.execute("INSERT INTO rows VALUES (?,?,?,?,?,?,?,?)",
                    ("code_contests/train" if k == "A" else "taco/train", i, 0, i, None, v, "x", fam[k]))
    con.commit()
    con.close()
    rows = {0: [], 1: []}
    for k, shard, source, n in (("A", 0, "code_contests", 3), ("B", 0, "taco", 2), ("B", 1, "taco", 4), ("C", 1, "apps", 5), ("D", 1, "taco", 7)):
        for j in range(n):
            rows[shard].append({"id": f"row-{k}-{shard}-{j}", "source": source, "family": "sha256:" + fam[k], "status": "pack",
                                "tokens": 100 * (j + 1), "trained": 90 * (j + 1)})
    rows[0].append({"id": "held", "source": "taco", "family": "sha256:" + fam["D"], "status": "heldout", "tokens": 5, "trained": 4})
    rs = tmp_path / "rowstats"
    rs.mkdir()
    for shard, rr in rows.items():
        with gzip.open(rs / f"shard-{shard:05d}.jsonl.gz", "wt") as f:
            f.write("\n".join(json.dumps(r) for r in rr) + "\n")
    cc = tmp_path / "cc.jsonl"
    cc.write_text("\n".join(json.dumps({"id": k, "statement": v}) for k, v in rl.items()) + "\n")
    (tmp_path / "pool.txt").write_text("\n".join(["cc-one", "cc-two", "cc-three"]) + "\n")
    (tmp_path / "held.txt").write_text("cc-four\ncc-two\n")
    (tmp_path / "rung.txt").write_text("cc-one\ncc-three\n")
    (tmp_path / "effort.json").write_text(json.dumps({"slots": [{"category": "code", "task_id": "cc-one"}, {"category": "math", "task_id": "m1"}]}))
    (tmp_path / "sft.json").write_text(json.dumps({"sets": {"ocr": {"in_pack": True, "area": "code", "admission": {"tokens_kept": 1}},
                                                           "dolly": {"in_pack": True, "area": "general", "admission": {"tokens_kept": 1000}}}}))
    return rl, pack_text


def _run(tmp_path: Path, name: str):
    out = tmp_path / name
    out.mkdir()
    argv = ["build", "--source-index", str(tmp_path / "idx.sqlite"), "--rowstats-dir", str(tmp_path / "rowstats"),
            "--rl-cc", str(tmp_path / "cc.jsonl"), "--pool-ids", str(tmp_path / "pool.txt"),
            "--set", f"heldout_e1_15nov={tmp_path / 'held.txt'}", "--effort-manifest", str(tmp_path / "effort.json"),
            "--rung-ids", str(tmp_path / "rung.txt"), "--sft-manifest", str(tmp_path / "sft.json"),
            "--private-dir", str(out / "private"), "--out-json", str(out / "rec.json"), "--out-md", str(out / "rec.md")]
    assert co.main(argv) == 0
    return out


def test_record_counts_routes_and_private_split(tmp_path):
    _toy(tmp_path)
    out = _run(tmp_path, "r1")
    rec = json.loads((out / "rec.json").read_text())
    pool = rec["sets"]["rl_code_pool"]
    assert pool["rl_problems"] == 3 and pool["found_in_pack"] == 2 and pool["possible_only"] == 1
    assert pool["found_by_tier"] == {"key": 1, "shingle": 1}
    assert pool["distinct_pack_problems"] == 2
    assert pool["reached_through_code_contests_rows"] == 1 and pool["reached_only_through_taco_or_apps_rows"] == 1
    assert pool["pack"]["rows"][:2] == [5, 4] and pool["pack"]["rows_total"] == 9      # A: 3 in shard 0; B: 2 + 4
    assert pool["pack"]["tokens_total"] == (100 + 200 + 300) + (100 + 200) + (100 + 200 + 300 + 400)
    assert rec["sets"]["heldout_e1_15nov"]["found_in_pack"] == 1                                    # cc-four is unrelated; cc-two matches
    assert rec["sets"]["effort_suite_code"]["rl_problems"] == 1                         # the math slot is not a code slot
    assert rec["pack"]["rows"] == 21 and rec["pack"]["problems"] == 4 and rec["pack"]["row_status_counts"]["heldout"] == 1
    held = rec["ocr2_heldout_vs_rl_pool"]                                               # the one held-out row is family D
    assert held["ocr2_heldout_rows"] == 1 and held["ocr2_heldout_problems"] == 1 and held["found_in_pack"] == 0
    sz = rec["sizing"]
    assert sz["rl_drop_pool_overlap"] == {"pool_problems": 3, "dropped": 2, "left": 1, "easiest_rung_problems": 2,
                                          "easiest_rung_dropped": 1, "easiest_rung_left": 1}
    assert sz["sft_drop_pool_overlap"]["rows"] == 9
    priv = json.loads((out / "private" / "cross_stage_overlap_keys.json").read_text())
    assert priv["rl_code_pool"]["found"] == ["cc-one", "cc-two"] and priv["rl_code_pool"]["only_taco_apps"] == ["cc-two"]
    assert priv["rl_code_pool"]["possible_only"] == ["cc-three"]


def test_public_files_hold_no_ids_or_statement_text(tmp_path):
    rl, pack = _toy(tmp_path)
    out = _run(tmp_path, "r2")
    public = (out / "rec.json").read_text() + (out / "rec.md").read_text()
    for rid in rl:
        assert rid not in public
    for text in list(rl.values()) + list(pack.values()):
        for w in vocab_words(text)[:20]:
            assert w not in public.split(), w


def vocab_words(text: str) -> list[str]:
    return [w for w in text.replace(".", "").split() if len(w) >= 6]


def test_build_is_deterministic(tmp_path):
    _toy(tmp_path)
    a = _run(tmp_path, "a")
    b = _run(tmp_path, "b")
    for name in ("rec.json", "rec.md", "private/cross_stage_overlap_keys.json", "private/cross_stage_overlap_matches.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_incomplete_join_stops_the_build(tmp_path):
    _toy(tmp_path)
    con = sqlite3.connect(tmp_path / "idx.sqlite")
    con.execute("DELETE FROM rows WHERE source_key = 'code_contests/train'")
    con.commit()
    con.close()
    with pytest.raises(SystemExit, match="no statement in the source index"):
        _run(tmp_path, "bad")


def test_unknown_rl_id_stops_the_build(tmp_path):
    _toy(tmp_path)
    (tmp_path / "held.txt").write_text("cc-four\nnot-in-the-rl-file\n")
    with pytest.raises(SystemExit, match="not in the RL v1 code file"):
        _run(tmp_path, "bad2")


def test_a_shard_in_two_row_stat_folders_is_refused(tmp_path):
    _toy(tmp_path)
    with pytest.raises(ValueError, match="two row-stat folders"):
        co.load_rowstats([str(tmp_path / "rowstats"), str(tmp_path / "rowstats")])


def test_missing_default_set_name_is_an_error_not_a_smaller_row(tmp_path):
    _toy(tmp_path)
    out = tmp_path / "bad3"
    out.mkdir()
    argv = ["build", "--source-index", str(tmp_path / "idx.sqlite"), "--rowstats-dir", str(tmp_path / "rowstats"),
            "--rl-cc", str(tmp_path / "cc.jsonl"), "--pool-ids", str(tmp_path / "pool.txt"),
            "--set", f"heldout_other_name={tmp_path / 'held.txt'}", "--effort-manifest", str(tmp_path / "effort.json"),
            "--rung-ids", str(tmp_path / "rung.txt"), "--sft-manifest", str(tmp_path / "sft.json"),
            "--private-dir", str(out / "private"), "--out-json", str(out / "rec.json"), "--out-md", str(out / "rec.md")]
    with pytest.raises(ValueError, match="heldout_e1_15nov"):
        co.main(argv)
    assert not (out / "rec.json").exists()


def test_possible_upper_bound_covers_the_eval_sets_too(tmp_path):
    _toy(tmp_path)
    (tmp_path / "held.txt").write_text("cc-three\ncc-four\n")             # cc-three is a sibling of pack family C: possible only
    rec = json.loads((_run(tmp_path, "r4") / "rec.json").read_text())
    z = rec["sizing"]
    assert rec["sets"]["heldout_e1_15nov"]["found_in_pack"] == 0 and rec["sets"]["heldout_e1_15nov"]["possible_only"] == 1
    assert z["sft_drop_e1_heldout_and_effort"]["pack_problems"] == 1      # the effort slot cc-one -> family A
    assert z["sft_drop_e1_heldout_and_effort_incl_possible_upper_bound"]["pack_problems"] == 2
    assert z["sft_drop_eval_sets_only_incl_possible_upper_bound"]["pack_problems"] == 2


def _ms(*pairs):
    return [co.Match(k, t, c) for k, t, c in pairs]


def test_sensitivity_counts_problems_near_the_confirm_level():
    matches = {"a": _ms(("p", "possible", 0.62)),                               # just below: would flip at 0.60
               "b": _ms(("p", "shingle", 0.67)),                                # just above: would flip at 0.70
               "c": _ms(("p", "shingle", 0.95)),                                # far above
               "d": _ms(("p", "key", 1.0), ("q", "shingle", 0.66)),             # the key match decides, not the level
               "e": _ms(("p", "possible", 0.30)),
               "f": _ms(("p", "shingle", 0.90), ("q", "shingle", 0.66))}        # best coverage 0.90
    s = co.sensitivity(list("abcdefg"), matches)
    assert s["possible_with_coverage_in_band_below_confirm"] == 1 and s["confirmed_with_coverage_in_band_above_confirm"] == 1


def test_pack_manifest_hash_is_recorded_when_given(tmp_path):
    _toy(tmp_path)
    m = tmp_path / "manifest.json"
    m.write_text("{}")
    out = tmp_path / "r5"
    out.mkdir()
    argv = ["build", "--source-index", str(tmp_path / "idx.sqlite"), "--rowstats-dir", str(tmp_path / "rowstats"),
            "--rl-cc", str(tmp_path / "cc.jsonl"), "--pool-ids", str(tmp_path / "pool.txt"),
            "--set", f"heldout_e1_15nov={tmp_path / 'held.txt'}", "--effort-manifest", str(tmp_path / "effort.json"),
            "--rung-ids", str(tmp_path / "rung.txt"), "--sft-manifest", str(tmp_path / "sft.json"), "--pack-manifest", str(m),
            "--private-dir", str(out / "private"), "--out-json", str(out / "rec.json"), "--out-md", str(out / "rec.md")]
    assert co.main(argv) == 0
    rec = json.loads((out / "rec.json").read_text())
    assert rec["inputs"]["pack_manifest_sha256"] == co.sha256_file(m)
    assert rec["inputs"]["pack_manifest_sha256"] in (out / "rec.md").read_text()
