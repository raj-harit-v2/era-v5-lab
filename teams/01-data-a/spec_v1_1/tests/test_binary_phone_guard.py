"""Synthetic regression cases for the narrowly scoped DA-F1-005 binary guard."""
import importlib.util
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('binary_guard_clean', SPEC / 'clean.py')
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)


def apply(text, pack='en-dclm'):
    return c.f1(dict(doc_id='synthetic', text=text, url='', pack_id=pack, lang_label='en'))


@pytest.mark.parametrize('pack', ['en-dclm', 'en-fineweb-edu', 'en-nemotroncc', 'en-nemotroncc-synth'])
@pytest.mark.parametrize('text', [
    'The binary number is 1111 1111 1111 in this example.',
    'Binary: 1010 1100 0011',
    'BINARY VALUE = `1111 1111 1111`',
    'The bit pattern is 0000 1010 1111.',
])
def test_explicit_binary_value_is_kept(pack, text):
    assert apply(text, pack) == ('keep', text)


@pytest.mark.parametrize('text', [
    'My phone: 1111 1111 1111',
    'My phone in binary: 1111 1111 1111',
    '1111 1111 1111',
    'Binary tutorial. My phone: 1111 1111 1111',
    'Binary: 1111 1111 1112',
    'Binary: +111 1111 1111',
    'Binary: 1111 1111 1111 2222',
    'Binary: 1111-1111-1111',
    'The binary number is discussed here. Call 555-867-5309.',
])
def test_ambiguous_or_explicit_phone_still_uses_existing_masking(text):
    action, result = apply(text)
    assert action == 'fix' and '<PHONE>' in result


def test_binary_guard_does_not_exempt_other_phones_on_the_same_line():
    text = 'Binary: 1111 1111 1111; my phone: 555-867-5309'
    expected = 'Binary: 1111 1111 1111; my phone: <PHONE>'
    assert apply(text) == ('fix', expected)
    assert apply(expected) == ('keep', expected)


def test_toll_free_contact_stays_unchanged():
    text = 'Call 1-800-555-0199.'
    assert apply(text) == ('keep', text)
