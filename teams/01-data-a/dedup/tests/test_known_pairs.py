"""E3 of dedup_design_v1.md: known pairs with a known answer, run through overlap.py and its family rules.

The other tests already cover an edited copy, exact scores against brute force, the math numbers rule, code comment
removal and mixed families. These four cover the rest of E3:

  must be caught   a whitespace/case variant (H1), a truncated copy (H2, while it keeps about 80% of the text)
  must be kept     same-topic pages, code that shares only its imports

Every text here is made up; none comes from a pack. The job runs in-process with its repository root pointed at a
temporary folder, as in test_overlap.py, so nothing is read from or written to the real inputs/ or out/.

  python3 -B -m pytest dedup/tests/test_known_pairs.py
"""
import csv
import sys
from pathlib import Path

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("pygments")
pq = pytest.importorskip("pyarrow.parquet")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_overlap import make_config, make_sample, run  # noqa: E402


def overlap(tmp_path, monkeypatch, parts):
    """Run overlap.py on made-up parts. Returns, keyed by the sorted pair of doc_ids: the qualifying matches
    (overlap_matches.csv rows), the raw word scores at or above the 0.50 floor (overlap_pairs.csv), and each
    document's word count (overlap_docs.parquet)."""
    out, pairs, _ = run(monkeypatch, tmp_path, make_config(tmp_path, make_sample(tmp_path, parts)))
    docs = pq.read_table(out / "overlap_docs.parquet").to_pylist()
    ids = {d["row"]: d["doc_id"] for d in docs}
    key = lambda r: tuple(sorted((ids[int(r["row_a"])], ids[int(r["row_b"])])))
    with (out / "overlap_matches.csv").open(newline="") as f:
        matches = {key(m): m for m in csv.DictReader(f)}
    raw = {key(p): float(p["jaccard"]) for p in pairs}
    return matches, raw, {d["doc_id"]: d["words"] for d in docs}


# Must be caught


ARTICLE = ("The river rises every monsoon and the fields along its banks turn into shallow lakes for a few weeks. "
           "Farmers move their cattle to higher ground, store grain on raised platforms and wait for the water to "
           "fall. When it does, it leaves behind a thin layer of silt that makes the soil rich enough for two "
           "harvests, which is why families have stayed on this land for generations despite the floods.")


def test_whitespace_and_case_variant_is_an_exact_copy(tmp_path, monkeypatch):
    words = ARTICLE.split()
    # Upper case, title case, tabs, doubled spaces, Windows and blank line breaks, padding at both ends.
    variant = ("   " + "\t".join(w.upper() if i % 3 == 0 else w for i, w in enumerate(words[:30]))
               + "\r\n\r\n" + "   ".join(words[30:]).title() + "  \n")
    parts = {"train/en-a/a.parquet": [("original", ARTICLE)],
             "train/en-b/a.parquet": [("variant", variant)]}
    matches, _, words_of = overlap(tmp_path, monkeypatch, parts)
    assert words_of["original"] >= 50
    assert matches.keys() == {("original", "variant")}
    m = matches["original", "variant"]
    assert (m["rule"], m["stage"], float(m["word_jaccard"])) == ("H1", "cross_pack", 1.0)


FULL = " ".join(f"word{i}" for i in range(100))   # 100 distinct words: 96 distinct 5-grams


@pytest.mark.parametrize("kept, caught", [(90, True), (85, True), (80, False), (50, False)])
def test_truncated_copy_is_caught_only_while_it_keeps_about_80_percent(tmp_path, monkeypatch, kept, caught):
    # A copy that keeps the first `kept` words shares all its kept - 4 5-grams with the full text, so its word
    # Jaccard is (kept - 4) / 96: 0.896 for 90 words, 0.844 for 85, 0.792 for 80 and 0.479 for 50. The prose
    # threshold is 0.80, so a copy cut by more than about a fifth is missed (a known limit of Jaccard, which compares
    # the two documents as a whole: it does not ask whether one is contained in the other).
    parts = {"train/en-a/a.parquet": [("full", FULL), ("cut", " ".join(FULL.split()[:kept]))]}
    matches, raw, _ = overlap(tmp_path, monkeypatch, parts)
    score = (kept - 4) / 96
    if caught:
        assert matches.keys() == {("cut", "full")}
        m = matches["cut", "full"]
        assert m["rule"] == "H2" and float(m["word_jaccard"]) == pytest.approx(score, abs=1e-6)
    else:
        assert not matches
        if score >= 0.50:
            assert raw["cut", "full"] == pytest.approx(score, abs=1e-6)
        else:
            assert ("cut", "full") not in raw   # below the 0.50 reporting floor


# Must be kept


HEADER = "Nature notes for young readers: simple science explained in plain words, every week. "
BEES_A = HEADER + (
    "Honey bees collect nectar from flowers and carry it back to the hive in a special stomach. Inside the hive, "
    "worker bees pass the nectar from one bee to another, and enzymes slowly break its sugars down. The bees then "
    "spread it thinly across the wax cells and fan their wings until most of the water evaporates. When the honey "
    "is thick enough, they seal each cell with a cap of fresh wax.")
BEES_B = HEADER + (
    "A single worker bee makes only a small fraction of a teaspoon of honey in her whole life. She visits hundreds "
    "of flowers on each trip, drinking nectar and gathering pollen on the hairs of her legs. Back at the colony, "
    "nectar is stored in wax cells, where the warmth of the hive and the beating of many wings dry it out. "
    "Beekeepers take only the extra honey and leave enough for the colony to survive the winter.")


def test_same_topic_pages_are_kept(tmp_path, monkeypatch):
    # Two pages from the same site on the same topic: the same site header and the same vocabulary (bees, nectar,
    # hive, wax, cells, wings, honey), but different sentences, so they share few 5-grams.
    parts = {"train/en-a/a.parquet": [("bees-a", BEES_A), ("bees-b", BEES_B)]}
    matches, raw, words_of = overlap(tmp_path, monkeypatch, parts)
    assert min(words_of.values()) >= 50   # kept for their score, not for the 50-word minimum
    assert not matches
    assert ("bees-a", "bees-b") not in raw   # below even the 0.50 reporting floor


IMPORTS = """import os
import sys
import json
import math
import time
import random
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
from typing import Dict, List, Optional
"""
SETTINGS = IMPORTS + '''

def load_settings(path):
    with open(path) as handle:
        settings = json.load(handle)
    settings.setdefault("retries", 3)
    settings.setdefault("timeout", 30)
    return settings


def backoff(attempt, base=0.5):
    delay = base * math.pow(2, attempt)
    return delay + random.random() * 0.1


def main():
    settings = load_settings(Path(sys.argv[1]))
    for attempt in range(settings["retries"]):
        time.sleep(backoff(attempt))
    print(os.getcwd(), settings["timeout"])
'''
WORDS = IMPORTS + '''

def count_words(folder):
    counts = Counter()
    for name in sorted(os.listdir(folder)):
        text = Path(folder, name).read_text()
        counts.update(text.lower().split())
    return counts


def pairs_of(words):
    return [a + "-" + b for a, b in combinations(sorted(words), 2)]


def report(counts, top=10):
    started = time.time()
    for word, n in counts.most_common(top):
        print(json.dumps({"word": word, "n": n}))
    print("took", round(time.time() - started, 3), file=sys.stderr)
'''
FORK = SETTINGS.replace('"timeout", 30', '"timeout", 60')   # a fork with one value changed


def test_code_sharing_only_its_imports_is_kept(tmp_path, monkeypatch):
    # The same 10 import lines, then different programs (both files have 20 or more code lines, so the token pass
    # scores them). The fork is the control: it shows the token pass ran and catches a real copy.
    parts = {"train/code-python/a.parquet": [("settings", SETTINGS), ("words", WORDS), ("fork", FORK)]}
    matches, _, _ = overlap(tmp_path, monkeypatch, parts)
    assert matches.keys() == {("fork", "settings")}
    m = matches["fork", "settings"]
    assert (m["rule"], m["word_jaccard"]) == ("H2", "")   # code pairs come only from the token pass
    assert float(m["code_jaccard"]) >= 0.85
