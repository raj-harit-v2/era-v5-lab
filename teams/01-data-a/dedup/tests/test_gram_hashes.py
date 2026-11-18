"""gram_hashes (jaccard_matrix.py): the bulk 5-gram hashing must give the same shingle sets as the BLAKE2b hashing it
replaced (same sizes, same Jaccard for every pair), and the same values on every machine.

Run: python3 -B -m pytest teams/01-data-a/dedup/tests/test_gram_hashes.py
"""
import hashlib
import random
import sys
from itertools import combinations
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("pandas")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jaccard_matrix import gram_hashes, shingles  # noqa: E402


def old_word_grams(words, k=5):
    """The BLAKE2b word shingles used up to 43fa750."""
    return {hashlib.blake2b(" ".join(words[i:i + k]).encode("utf-8"), digest_size=8).digest()
            for i in range(len(words) - k + 1)}


def old_code_grams(tokens, k=5):
    """The length-prefixed BLAKE2b code shingles of b1e6548."""
    enc = [f"{len(t)}:{t}".encode("utf-8") for t in tokens]
    return {hashlib.blake2b(b"".join(enc[i:i + k]), digest_size=8).digest() for i in range(len(enc) - k + 1)}


def new_set(blob):
    return set(np.frombuffer(blob, dtype=np.uint64).tolist())


def jac(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


def corpus(seed, n=60, vocab=40, length=(5, 120)):
    """Texts from a small vocabulary, many of them edited copies of each other, so pairs share many 5-grams."""
    r = random.Random(seed)
    words = [f"w{i}" for i in range(vocab)] + ["ಕನ್ನಡ", "తెలుగు", "தமிழ்", "हिन्दी", "naïve", "", "{", "}"]
    base = [[r.choice(words) for _ in range(r.randint(*length))] for _ in range(n // 3)]
    out = []
    for b in base:
        out.append(b)
        for _ in range(2):
            c = list(b)
            for _ in range(r.randint(0, 4)):
                c[r.randrange(len(c))] = r.choice(words)
            out.append(c)
    return out


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_same_sets_and_jaccard_as_blake2b_for_words(seed):
    docs = corpus(seed)
    old = [old_word_grams(d) for d in docs]
    new = [new_set(gram_hashes(d, 5)) for d in docs]
    assert [len(s) for s in old] == [len(s) for s in new]
    for i, j in combinations(range(len(docs)), 2):
        assert jac(old[i], old[j]) == jac(new[i], new[j])


@pytest.mark.parametrize("seed", [4, 5])
def test_same_sets_and_jaccard_as_before_for_code_tokens(seed):
    docs = corpus(seed)
    old = [old_code_grams(d) for d in docs]
    new = [new_set(gram_hashes(d, 5)) for d in docs]
    assert [len(s) for s in old] == [len(s) for s in new]
    for i, j in combinations(range(len(docs)), 2):
        assert jac(old[i], old[j]) == jac(new[i], new[j])


def test_fixed_values_on_every_machine():
    # Pinned on 13 Nov 2026 (pandas 2.3.3, numpy 2.2.6). A change here means the hashing changed: every overlap
    # output would then need the byte-identical check again.
    assert np.frombuffer(gram_hashes("the cat sat on the mat today".split(), 5), dtype=np.uint64).tolist() == [
        5286434728063237159, 7986168261747576119, 14880685628675004354]
    assert np.frombuffer(gram_hashes(["fn", "main", "(", ")", "{", "}"], 5), dtype=np.uint64).tolist() == [
        9010501124320606578, 13310747600817821665]


def test_order_matters_and_short_input():
    assert gram_hashes(list("abcde"), 5) != gram_hashes(list("edcba"), 5)
    assert gram_hashes(["ab", "c", "d", "e", "f"], 5) != gram_hashes(["a", "bc", "d", "e", "f"], 5)
    assert gram_hashes(list("abcd"), 5) == b""
    blob, words = shingles("short key", 5)
    assert words == 2 and len(blob) == 8 and shingles("", 5) == (b"", 0)


def test_gram_set_preserves_binary_digests():
    from overlap_rules import gram_set
    values = [b"\x00" * 8, b"a" + b"\x00" * 7, b"\xff" * 8]
    assert gram_set(b"".join(values + values)) == set(values)
    assert gram_set(b"") == set()
