"""Unit tests for h3_signals.py, the language-neutral signals of H3: sentences, numbers, Latin-script tokens, the URL key
and the length ratio, and the batch functions that h3.py uses, each checked against its per-document reference. Every
text and URL here is made up.

  python3 -B -m pytest dedup/tests/test_h3_signals.py
"""
import sys
from collections import Counter
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pa = pytest.importorskip("pyarrow")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from h3_signals import (head_texts, latin_share, latin_token_lists, latin_tokens, length_ratio,  # noqa: E402
                        multiset_jaccard, number_tokens, numbers, pair_overlap, sentences_batch, split_sentences,
                        url_key, url_keys)

AT = "@"   # joined into the URLs with a user name, so no text here looks like an email address
TEXTS = [
    "First sentence here. Second one is here!\nThird line is also here।  Fourth",
    "यह पहला वाक्य है। यह दूसरा वाक्य है॥ यह तीसरा वाक्य है।",
    "Menu\nA   long enough sentence   here. Another long enough one here. A third long enough one.",
    "",
    None,
    "No break after this. Next one starts　after an ideographic space? Yes!\r\nWindows line end. Tab\there.",
    "Wait... what? Really!? Yes. . . ok\n\n\n  spaced   out\x1c line here.",
    "वर्ष २०२४ में 1,00,000 लोग; 2024 और 007. ১২ জন, pi is 3.14, 0,5 and 00.10 x9y 12abc NASA-ISRO in2024 API",
    "भारत में NASA और ISRO ने in 2024 में काम किया\nmixedCase Token99 a1b2c3 ab 9lives 2024",
]
URLS = [
    "https://hi.wikipedia.org/wiki/Taj_Mahal", "https://en.m.wikipedia.org/wiki/Taj_Mahal",
    "https://www.example.com/hi/news/7", "https://example.com/news/7", "https://example.com/en-us/about",
    "https://example.com/hindi/story", "https://example.com/news/7?lang=hi&id=3", "https://example.com/news/7?id=3",
    "https://hi.example.com/", "", None, "not a url", "https://blog.example.com/a", "https://example.in/a",
    "  HTTPS://User:pw" + AT + "WWW.Example.COM:8080/Hi/News/7?b=2&a=1&&LANG=en#top  ", "https://www.m.example.org/x",
    "https://www.hi.www.example.org/x", "https://m.org/x", "https://[::1]/x", "//example.com/x",
    "https://example.com?id=3", "https://example.com/hi/en/x", "https://example.com/x?locale=hi&q",
]


def per_text(values, parent, n):
    """The flat values of a batch function, back in one list per text."""
    out = [[] for _ in range(n)]
    for v, p in zip(values.to_pylist(), parent.tolist()):
        out[p].append(v)
    return out


def test_sentences_split_at_end_marks_and_line_breaks():
    text = "First sentence here. Second one is here!\nThird line is also here।  Fourth"
    assert split_sentences(text, min_chars=10) == ["First sentence here.", "Second one is here!",
                                                   "Third line is also here।"]


def test_sentences_split_at_danda_and_double_danda():
    text = "यह पहला वाक्य है। यह दूसरा वाक्य है॥ यह तीसरा वाक्य है।"
    assert split_sentences(text, min_chars=5) == ["यह पहला वाक्य है।", "यह दूसरा वाक्य है॥", "यह तीसरा वाक्य है।"]


def test_sentences_short_ones_dropped_spaces_collapsed_and_capped():
    text = "Menu\nA   long enough sentence   here. Another long enough one here. A third long enough one."
    assert split_sentences(text, min_chars=10) == ["A long enough sentence here.", "Another long enough one here.",
                                                   "A third long enough one."]
    assert split_sentences(text, min_chars=10, max_sentences=2) == ["A long enough sentence here.",
                                                                    "Another long enough one here."]
    assert split_sentences("", 10) == [] and split_sentences(None, 10) == []


def test_numbers_match_across_scripts_and_grouping():
    assert numbers("वर्ष २०२४ में 1,00,000 लोग; 2024 और 007") == Counter({"2024": 2, "100000": 1, "7": 1})
    assert numbers("১২ জন") == Counter({"12": 1})          # Bengali digits
    assert numbers("pi is 3.14") == Counter({"3.14": 1})
    assert numbers("no digits") == Counter()


def test_multiset_jaccard():
    a, b = Counter({"1": 2, "2": 1}), Counter({"1": 1, "3": 1})
    assert multiset_jaccard(a, b) == 1 / 4                  # min counts 1 / max counts 2 + 1 + 1
    assert multiset_jaccard(a, a) == 1.0
    assert multiset_jaccard(Counter(), Counter()) is None
    assert multiset_jaccard(a, Counter()) == 0.0


def test_latin_tokens_and_share():
    hindi = latin_tokens("भारत में NASA और ISRO ने in 2024 में काम किया")
    assert hindi == {"nasa", "isro"}                        # "in" is too short; 2024 is not a word
    english = latin_tokens("NASA and ISRO worked together in 2024")
    assert latin_share(hindi, english) == 1.0
    assert latin_share(hindi, {"nasa", "other", "words"}) == 0.5
    assert latin_share(set(), english) is None


def test_url_key_language_subdomain():
    assert url_key("https://hi.wikipedia.org/wiki/Taj_Mahal") == ("wikipedia.org/wiki/taj_mahal", "hi")
    assert url_key("https://en.m.wikipedia.org/wiki/Taj_Mahal") == ("wikipedia.org/wiki/taj_mahal", "en")


def test_url_key_language_path_segment():
    assert url_key("https://www.example.com/hi/news/7") == ("example.com/news/7", "hi")
    assert url_key("https://example.com/news/7") == ("example.com/news/7", None)   # same key, no marker
    assert url_key("https://example.com/en-us/about") == ("example.com/about", "en")
    assert url_key("https://example.com/hindi/story") == ("example.com/story", "hi")


def test_url_key_language_query_parameter():
    assert url_key("https://example.com/news/7?lang=hi&id=3") == ("example.com/news/7?id=3", "hi")
    assert url_key("https://example.com/news/7?id=3") == ("example.com/news/7?id=3", None)


def test_url_key_none_for_home_pages_and_missing_urls():
    assert url_key("https://hi.example.com/") == (None, "hi")
    assert url_key("") == (None, None) and url_key(None) == (None, None)
    assert url_key("not a url") == (None, None)


def test_url_key_keeps_other_subdomains_and_short_hosts():
    assert url_key("https://blog.example.com/a") == ("blog.example.com/a", None)
    assert url_key("https://example.in/a") == ("example.in/a", None)


def test_url_key_keeps_query_fields_as_written_and_sorted():
    assert url_key("https://example.com/x?b=2&a=1&lang=hi") == ("example.com/x?a=1&b=2", "hi")
    assert url_key("https://user" + AT + "www.Example.com:8080/X#top") == ("example.com/x", None)
    assert url_key("https://[::1]/x") == (None, None)


def test_length_ratio():
    assert length_ratio(100, 250) == 2.5 == length_ratio(250, 100)
    assert length_ratio(0, 10) == float("inf")


@pytest.mark.parametrize("min_chars,max_sentences", [(1, None), (10, None), (10, 2), (5, 1)])
def test_sentences_batch_matches_split_sentences(min_chars, max_sentences):
    s, parent = sentences_batch(pa.array(TEXTS, pa.string()), min_chars, max_sentences)
    assert per_text(s, parent, len(TEXTS)) == [split_sentences(t, min_chars, max_sentences) for t in TEXTS]


def test_head_texts_join_the_first_sentences():
    s, parent = sentences_batch(pa.array(TEXTS, pa.string()), 10)
    assert head_texts(s, parent, len(TEXTS), 2).to_pylist() == [" ".join(split_sentences(t, 10)[:2]) for t in TEXTS]


def test_number_tokens_match_numbers():
    tok, parent = number_tokens(pa.array(TEXTS, pa.string()))
    assert [Counter(x) for x in per_text(tok, parent, len(TEXTS))] == [numbers(t) for t in TEXTS]


def test_latin_token_lists_match_latin_tokens():
    tok, parent = latin_token_lists(pa.array(TEXTS, pa.string()))
    assert [set(x) for x in per_text(tok, parent, len(TEXTS))] == [latin_tokens(t) for t in TEXTS]


def same(got, want):
    return got is None and want is None or (got is not None and want is not None and abs(got - want) < 1e-12)


def test_pair_overlap_matches_multiset_jaccard_and_latin_share():
    texts = pa.array(TEXTS, pa.string())
    A, B = np.array([0, 7, 7, 8, 3, 1]), np.array([1, 8, 1, 2, 4, 7])
    tok, parent = number_tokens(texts)
    sh, sa, sb = pair_overlap(tok, parent, len(TEXTS), A, B, distinct=False)
    for p, (a, b) in enumerate(zip(A.tolist(), B.tolist())):
        got = None if sa[p] + sb[p] == 0 else sh[p] / (sa[p] + sb[p] - sh[p])
        assert same(got, multiset_jaccard(numbers(TEXTS[a]), numbers(TEXTS[b]))), (a, b)
    tok, parent = latin_token_lists(texts)
    sh, sa, sb = pair_overlap(tok, parent, len(TEXTS), A, B, distinct=True)
    for p, (a, b) in enumerate(zip(A.tolist(), B.tolist())):
        got = None if min(sa[p], sb[p]) == 0 else sh[p] / min(sa[p], sb[p])
        assert same(got, latin_share(latin_tokens(TEXTS[a]), latin_tokens(TEXTS[b]))), (a, b)


def test_url_keys_match_url_key():
    assert url_keys(pa.array(URLS, pa.string())).to_pylist() == [url_key(u)[0] for u in URLS]
