"""Fingerprints.check gives the same result as the reference lookup (G9).

    pytest teams/09-evaluation/decontam/tests/test_fast_check.py -q

check() hashes each gram as a slice of one UTF-8 buffer. reference_check below is the earlier code, which hashed
each gram with gram_hash and int(..., 16). Both must give the same (flagged, hits) for every document: the same items,
gram counts, coverage and offsets. The documents mix item texts, short texts, repeats, Indic and accented words,
punctuation and random words, so they have many hits of every run length.
"""

import random

import fpset
from fpset import Fingerprints, gram_hash

WORDS = ("river city night answer quiz which flows through old the of a an in on is was क़लम ગુજરાતી ಕನ್ನಡ मराठी "
         "café naïve straße ½ 16 eggs ducks lay janet's DUCKS, lay 16-eggs! def return import x = y + 1").split()


def reference_check(self, text, min_hits=1):
    ws = self.norm.words_with_offsets(text)
    matched, first = {}, {}
    for n, table in self.owner.items():
        seen = set()
        for i in range(len(ws) - n + 1):
            k = int(gram_hash([w for w, _ in ws[i:i + n]]), 16)
            o = table.get(k)
            if o is None or k in seen:
                continue
            seen.add(k)
            for idx in (o if isinstance(o, tuple) else (o,)):
                matched[idx] = matched.get(idx, 0) + 1
                first[idx] = min(first.get(idx, ws[i][1]), ws[i][1])
    hits = [{"item": self.refs[idx], "grams": c, "item_grams": self.size[idx],
             "coverage": round(c / self.size[idx], 3), "offset": first[idx]}
            for idx, c in matched.items()]
    hits.sort(key=lambda h: (-h["coverage"], -h["grams"], h["item"]))
    canary_hits = [{"item": f"{bid}:canary", "canary": c, "offset": text.find(c)}
                   for c, bid in self.canaries.items() if c in text]
    flagged = bool(canary_hits) or any(h["grams"] >= min_hits for h in hits)
    return flagged, canary_hits + hits


def random_text(rng, n):
    return " ".join(rng.choice(WORDS) for _ in range(n))


def build(tmp_path, rng):
    items, texts = [], []
    for i in range(40):
        prose = random_text(rng, rng.choice([9, 11, 14, 25, 60]))  # short texts (8-12 words) and long ones
        code = random_text(rng, 30)
        texts += [prose, code]
        items.append((f"bench:test:{i}", {"prose": [prose], "code": [code]}))
    items.append(("bench:test:dup", {"prose": [texts[4]]}))  # a gram owned by two items
    out = tmp_path / "set"
    fpset.write_benchmark(out, "bench", items, {"prose": 13, "code": 20}, {"name": "Bench", "tags": ["english"]},
                          canaries={"CANARY-GUID-1234"})
    fpset.write_index(out)
    return Fingerprints(out), texts


def test_check_matches_reference_on_documents_with_hits(tmp_path):
    rng = random.Random(7)
    fp, texts = build(tmp_path, rng)
    docs = ["", "one", "CANARY-GUID-1234 inside", texts[0] + " " + texts[0]]
    for _ in range(400):
        parts = [random_text(rng, rng.randint(0, 40))]
        for _ in range(rng.randint(0, 3)):
            t = rng.choice(texts).split()
            a = rng.randint(0, len(t) // 2)
            parts.append(" ".join(t[a:]) if rng.random() < 0.5 else " ".join(t))
            parts.append(random_text(rng, rng.randint(0, 5)))
        docs.append(rng.choice([" ", "\n", ". ", " — "]).join(parts))
    n_flagged = 0
    for doc in docs:
        for min_hits in (1, 3):
            want = reference_check(fp, doc, min_hits)
            assert fp.check(doc, min_hits) == want
            n_flagged += want[0]
    assert n_flagged > 200  # the test has many hits, not only clean documents


def test_check_matches_reference_on_the_shipped_set():
    fp = Fingerprints(fpset.Path(__file__).resolve().parent.parent.parent / "fingerprints" / fpset.VERSION)
    rng = random.Random(11)
    for _ in range(50):
        doc = random_text(rng, rng.randint(0, 300))
        assert fp.check(doc) == reference_check(fp, doc)
