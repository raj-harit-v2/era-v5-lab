"""Unit tests for minhash_overlap.py, the MinHash + LSH overlap stage: same duplicate groups and rules as overlap.py on
made-up data (prose, math, code, empty and held-out documents), the files dedup.py and the runner read, no N x N
outputs, resume per part, star buckets and config checks. Every text here is made up. The job runs in-process with its
repository root pointed at a temporary folder.

  python3 -B -m pytest dedup/tests/test_minhash_overlap.py
"""
import csv
import json
import random
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("pygments")
pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq  # noqa: E402
from scipy.sparse import coo_matrix  # noqa: E402
from scipy.sparse.csgraph import connected_components  # noqa: E402

DEDUP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEDUP))
import minhash_overlap as mh  # noqa: E402
try:   # overlap.py (the exact method) imports resource, which Windows does not have
    import overlap as ov  # noqa: E402
except ImportError:
    ov = None
needs_v1 = pytest.mark.skipif(ov is None, reason="overlap.py needs the resource module (not on Windows)")

WORDS = ("river stone bridge garden market window letter silver forest engine harbour lantern meadow pencil orchard "
         "valley thunder candle mirror basket ladder copper island marble needle saddle temple violin whistle yellow "
         "anchor blanket castle dragon falcon glacier hammer jungle kettle lemon magnet nectar pepper quartz rocket").split()


def prose(rng, n=120):
    return " ".join(rng.choice(WORDS) for _ in range(n))


def edit(rng, text, k):
    w = text.split(" ")
    for i in rng.sample(range(len(w)), k):
        w[i] = rng.choice(WORDS)
    return " ".join(w)


def code(rng, n=30):
    return "\n".join(f"func f{i}(x int) int {{ return x * {rng.randint(1, 99)} + {i} }}" for i in range(n))


def sample(seed=7):
    """Parts with planted copies: exact (H1), near (prose H2), math with and without the same numbers, code H2."""
    rng = random.Random(seed)
    a, b, c = prose(rng), prose(rng), prose(rng)
    m = prose(rng, 80) + " the answer is 42 and 17"
    g = code(rng)
    g2 = "// a comment line\n" + g                         # comments are not code tokens: same tokens, new H1 key
    parts = {
        "train/en-a/part-00000.parquet": [("a1", a), ("a2", edit(rng, a, 1)), ("a3", c), ("a4", ""), ("a5", prose(rng))],
        "train/en-b/part-00000.parquet": [("b1", a.upper()), ("b2", b), ("b3", ""), ("b4", edit(rng, c, 2))],
        "heldout/en-b/part-00000.parquet": [("hb1", edit(rng, b, 1)), ("hb2", prose(rng))],
        "train/math-x/part-00000.parquet": [("m1", m), ("m2", m.replace("42", "43")), ("m3", m + " ")],
        "train/code-go/part-00000.parquet": [("g1", g), ("g2", g2), ("g3", code(rng))],
    }
    return parts


def write(root, parts):
    base = root / "inputs" / "cleaned"
    for split in ("train", "heldout"):
        (base / split).mkdir(parents=True, exist_ok=True)
    for name, docs in parts.items():
        p = base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist([{"pack_id": name.split("/")[1], "doc_id": d, "text": t} for d, t in docs]), p)


def config(root, name, out, **over):
    p = root / f"{name}.json"
    p.write_text(json.dumps({"inputs": "inputs/cleaned", "out": out, **over}))
    return p


def run_mh(monkeypatch, root, cfg):
    monkeypatch.setattr(mh, "REPO", root)
    monkeypatch.setattr(sys, "argv", ["minhash_overlap.py", "--config", str(cfg)])
    mh.main()
    out = root / json.loads(cfg.read_text())["out"]
    return out, json.loads((out / "overlap_summary.json").read_text())


def run_v1(monkeypatch, root, cfg):
    monkeypatch.setattr(ov, "REPO", root)
    monkeypatch.setattr(sys, "argv", ["overlap.py", "--config", str(cfg)])
    ov.main()
    return root / json.loads(cfg.read_text())["out"]


def groups(out):
    """Duplicate groups as dedup.py forms them: connected components of the matches, empty documents set aside."""
    docs = pq.read_table(out / "overlap_docs.parquet").to_pandas()
    empty = set(docs.index[docs.shingles == 0])
    with open(out / "overlap_matches.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    e = [(int(r["row_a"]), int(r["row_b"])) for r in rows if int(r["row_a"]) not in empty]
    n = len(docs)
    a = np.array([x for x, _ in e] + [0]); b = np.array([y for _, y in e] + [0])
    _, lab = connected_components(coo_matrix((np.ones(len(a)), (a, b)), shape=(n, n)), directed=False)
    out_groups = {}
    for i, l in enumerate(lab):
        out_groups.setdefault(l, []).append(docs.id[i])
    rules = {(docs.id[int(r["row_a"])], docs.id[int(r["row_b"])]): r["rule"] for r in rows}
    return {tuple(sorted(g)) for g in out_groups.values() if len(g) > 1}, rules, docs


@pytest.fixture
def mh_run(tmp_path, monkeypatch):
    write(tmp_path, sample())
    return run_mh(monkeypatch, tmp_path, config(tmp_path, "mh", "out/mh", workers=1))


@needs_v1
def test_same_documents_and_duplicate_groups_as_overlap_py(tmp_path, monkeypatch, mh_run):
    out, _ = mh_run
    v1 = run_v1(monkeypatch, tmp_path, config(tmp_path, "v1", "out/v1"))
    g1, r1, d1 = groups(v1)
    g2, r2, d2 = groups(out)
    assert d1.equals(d2)
    assert g1 == g2
    assert g1   # the sample has groups
    # every H2 pair of v1 is an H2 pair here; H1 groups may be written as star edges
    assert {p for p, r in r1.items() if r == "H2"} == {p for p, r in r2.items() if r == "H2"}


def test_planted_copies_are_found_with_v1_rules(mh_run):
    out, _ = mh_run
    g, rules, _ = groups(out)
    flat = {d for grp in g for d in grp}
    assert ("en-a-a1", "en-b-b1") in rules and rules["en-a-a1", "en-b-b1"] == "H1"      # case only: H1
    assert rules.get(("en-a-a1", "en-a-a2")) == "H2"                                    # one word changed
    assert ("en-b-b2" in flat) and ("en-b-hb1" in flat)                                 # train <-> held-out
    assert ("math-x-m1", "math-x-m2") not in rules                                      # different numbers
    assert rules.get(("code-go-g1", "code-go-g2")) == "H2"                              # same code tokens
    assert "en-a-a5" not in flat


def test_writes_what_dedup_and_the_runner_read_and_no_all_pairs_outputs(mh_run):
    out, s = mh_run
    for name in ("overlap_summary.json", "overlap_matches.csv", "overlap_docs.parquet"):
        assert (out / name).is_file()
    assert not (out / "overlap_matrix.npz").exists() and not (out / "overlap_histogram.csv").exists()
    assert s["status"] == "complete" and s["method"] == "minhash_lsh"
    assert s["documents_all"] == 17
    for name in ("overlap_matches.csv", "overlap_docs.parquet"):
        assert s["outputs"][name]["sha256"] == mh.sha256_file(out / name)
    assert {p["part"] for p in s["inputs"]["parts"]} == {"train/en-a/part-00000.parquet", "train/en-b/part-00000.parquet",
                                                        "heldout/en-b/part-00000.parquet", "train/math-x/part-00000.parquet",
                                                        "train/code-go/part-00000.parquet"}
    assert "overlap_docs.parquet" not in s["returned_files"]


def test_a_rerun_reuses_every_part_and_a_changed_part_is_redone(tmp_path, monkeypatch):
    write(tmp_path, sample())
    cfg = config(tmp_path, "mh", "out/mh", workers=1)
    out, s1 = run_mh(monkeypatch, tmp_path, cfg)
    first = mh.sha256_file(out / "overlap_matches.csv")
    _, s2 = run_mh(monkeypatch, tmp_path, cfg)
    assert s2["minhash"]["parts_reused"] == 5 and mh.sha256_file(out / "overlap_matches.csv") == first
    p = tmp_path / "inputs/cleaned/train/en-a/part-00000.parquet"
    t = pq.read_table(p).to_pylist(); t[4]["text"] = "something else entirely now"
    pq.write_table(pa.Table.from_pylist(t), p)
    _, s3 = run_mh(monkeypatch, tmp_path, cfg)
    assert s3["minhash"]["parts_reused"] == 4


def test_a_bucket_over_max_bucket_gives_star_edges_and_the_same_group(tmp_path, monkeypatch):
    rng = random.Random(3)
    base = prose(rng, 200)
    write(tmp_path, {"train/en-a/part-00000.parquet": [(f"d{i}", edit(rng, base, 1)) for i in range(8)]})
    _, s = run_mh(monkeypatch, tmp_path, config(tmp_path, "mh", "out/mh", workers=1, max_bucket=3))
    g, _, _ = groups(tmp_path / "out/mh")
    assert s["minhash"]["word"]["star_buckets"] > 0
    assert len(g) == 1 and len(next(iter(g))) == 8


@pytest.mark.parametrize("over, message", [({"hashes": 100, "bands": 32}, "multiple of bands"),
                                           ({"k": 4}, "k must be 5"), ({"max_output_mb": 60}, "at most 50"),
                                           ({"out": "elsewhere"}, "inside out/"), ({"nope": 1}, "unknown keys")])
def test_a_bad_config_is_refused(tmp_path, monkeypatch, over, message):
    monkeypatch.setattr(mh, "REPO", tmp_path)
    p = tmp_path / "c.json"; p.write_text(json.dumps({"inputs": "inputs/cleaned", "out": "out/t", **over}))
    with pytest.raises(SystemExit) as e:
        mh.load_config(p)
    assert message in str(e.value)


def test_overlap_json_settings_are_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(mh, "REPO", tmp_path)
    cfg = mh.load_config(DEDUP / "overlap.json")
    assert cfg["hashes"] == 128 and cfg["bands"] == 32 and cfg["expected_packs"]


def test_p_found_matches_the_band_formula():
    r, b = 4, 32
    assert abs((1 - (1 - 0.8 ** r) ** b) - 0.99999995) < 1e-7
