"""Edge-case tests for the G10 math verifier (Ranjani, week 4)."""
from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from math_verifier import parse_number  # noqa: E402

F = Fraction


def test_plain_fraction():
    assert parse_number("5/6") == F(5, 6)


def test_frac_latex():
    assert parse_number(r"\frac{5}{6}") == F(5, 6)


def test_dfrac_short():
    assert parse_number(r"\dfrac56") == F(5, 6)


def test_nested_frac():
    assert parse_number(r"\frac{1}{\frac{2}{3}}") == F(3, 2)


def test_double_nested_frac():
    assert parse_number(r"\frac{\frac{1}{2}}{3}") == F(1, 6)


def test_negative_denominator():
    assert parse_number(r"\frac{1}{-2}") == F(-1, 2)


def test_negative_numerator():
    assert parse_number(r"-\frac{1}{2}") == F(-1, 2)


def test_unicode_half():
    assert parse_number("½") == F(1, 2)


def test_unicode_three_quarters():
    assert parse_number("¾") == F(3, 4)


def test_mixed_number_fails_closed():
    assert parse_number(r"1\frac{1}{2}") is None


def test_decimal():
    assert parse_number("0.5") == F(1, 2)


def test_negative_decimal():
    assert parse_number("-3.0") == F(-3)


def test_boxed():
    assert parse_number(r"\boxed{5}") == F(5)


def test_unicode_minus():
    assert parse_number("\u22125") == F(-5)


def test_empty_is_none():
    assert parse_number("") is None


def test_garbage_is_none():
    assert parse_number("hello") is None
