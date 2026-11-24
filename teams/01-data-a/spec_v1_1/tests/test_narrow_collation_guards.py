"""Preservation boundaries extracted from #86; synthetic text only."""
import importlib.util
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("narrow_clean", SPEC / "clean.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def run(rid, text, pack, url=""):
    return c._RULE[rid]()({"doc_id": "synthetic", "text": text, "pack_id": pack,
                           "url": url, "lang_label": "go" if pack.startswith("code-") else "en"})


@pytest.mark.parametrize("pack", ["code-cpp", "code-go", "code-java", "code-js-ts", "code-python", "code-rust"])
def test_a6_preserves_real_cyrillic_but_corrects_isolated_lookalikes(pack):
    text = "IP_сервера %sПогода \\nИли pаss"
    assert run("DA-A6-001", text, pack) == ("fix", text[:-4] + "pass")


@pytest.mark.parametrize("url", ["https://example.org/testdata/fixture.txt", "src/parser_test.go"])
def test_a6_preserves_test_fixtures(url):
    assert run("DA-A6-001", "pаss", "code-go", url) == ("keep", "pаss")
    assert run("DA-A6-001", "pаss", "code-go", "src/parser.go") == ("fix", "pass")


@pytest.mark.parametrize("opening,closing", [("```python", "```"), ("~~~", "~~~~"), ("````", "````")])
def test_english_repeated_lines_inside_fences_are_preserved(opening, closing):
    line = "repeat this line verbatim"
    fenced = opening + "\n" + (line + "\n") * 3 + closing
    prose = (line + "\n") * 3
    text = fenced + "\n" + prose
    assert run("DA-C2-003", text, "en-fineweb-edu") == ("fix", fenced + "\n" + line + "\n\n\n")


def test_fence_must_close_with_the_same_marker_and_sufficient_length():
    line = "repeat this line verbatim\n"
    for text in ["````\n" + line + "```\n" + line * 3,
                 "```\n" + line + "~~~\n" + line * 3,
                 "```\n" + line + "```not a closing fence\n" + line * 3]:
        assert run("DA-C2-003", text, "en-fineweb-edu") == ("keep", text)


@pytest.mark.parametrize("pack", ["en-dclm", "en-fineweb-edu", "en-nemotroncc", "en-nemotroncc-synth"])
@pytest.mark.parametrize("quote", ["”", "’", "»"])
def test_closing_quotes_preserve_text_but_do_not_disable_truncation(pack, quote):
    text = "The heading reads: of" + quote
    assert run("DA-C3-003", text, pack) == ("keep", text)
    assert run("DA-C3-003", "A fragment ends with of", pack)[0] == "drop"
    assert run("DA-C3-003", "A long sentence. " * 200 + "of", pack)[0] == "drop"
    assert run("DA-C3-003", "An excerpt […]", pack)[0] == "drop"


def test_scientific_repeat_must_start_at_a_line_boundary():
    lead = "A scientific paragraph with useful content. " * 6
    text = lead + "different middle " + lead + "new ending."
    assert run("DA-C2-004", text, "sci-finepdfs") == ("keep", text)


def test_scientific_repeat_does_not_cut_a_partial_paragraph():
    paragraph = "The opening has a unique prefix for exact matching. " + "A scientific paragraph with useful content. " * 6
    lead = paragraph + "\n\n" + "Partial duplicate followed by original material " * 2
    text = lead + "\n" + paragraph + "\n\nPartial duplicate followed by new material."
    expected = lead + "\nPartial duplicate followed by new material."
    assert run("DA-C2-004", text, "sci-finepdfs") == ("fix", expected)
    unbroken = paragraph + "\n" + paragraph + "different tail."
    assert run("DA-C2-004", unbroken, "sci-finepdfs") == ("keep", unbroken)


@pytest.mark.parametrize("pack", ["en-dclm", "en-fineweb-edu", "en-nemotroncc", "en-nemotroncc-synth"])
def test_doi_exclusion_does_not_unmask_a_phone_or_regress_binary_values(pack):
    doi = "10.1034/j.1399-3054.1998.00001.x"
    text = "doi: " + doi + "; phone 212-555-0199"
    assert run("DA-F1-005", text, pack) == ("fix", "doi: " + doi + "; phone <PHONE>")
    binary = "binary value: 1010 1110 1010"
    assert run("DA-F1-005", binary, pack) == ("keep", binary)
    assert run("DA-F1-005", "phone: 1010 1110 1010", pack)[0] == "fix"


def test_amendments_keep_existing_pack_boundaries():
    for rid in ["DA-A6-001", "DA-C2-004", "DA-C2-003", "DA-C3-003", "DA-F1-005"]:
        text = "pаss\nphone 212-555-0199\nends with of"
        assert run(rid, text, "cadj-commits") == ("keep", text)
