"""Synthetic regressions for code-pack F1 dispatch and Sanskrit number preservation (#734)."""
import importlib.util
from pathlib import Path

import pytest

@pytest.fixture
def cleaner():
    path = Path(__file__).resolve().parents[1] / 'clean.py'
    spec = importlib.util.spec_from_file_location('regression_v1_1', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def document(pack, text, lang):
    return dict(doc_id='synthetic', text=text, url='', pack_id=pack, lang_label=lang)


@pytest.mark.parametrize('pack, lang, prefix, string_line', [
    ('code-cpp', 'cpp', '//', 'const char* owner = "{email}";'),
    ('code-go', 'go', '//', 'package main\nconst owner = "{email}"'),
    ('code-java', 'java', '//', 'class A {{ String owner = "{email}"; }}'),
    ('code-js-ts', 'typescript', '//', 'const owner: string = "{email}";'),
    ('code-python', 'python', '#', 'owner = "{email}"'),
    ('code-rust', 'rust', '//', 'const OWNER: &str = "{email}";'),
])
def test_generic_code_tag_masks_contacts_with_the_packs_parser(cleaner, pack, lang, prefix, string_line):
    c = cleaner
    pytest.importorskip('tree_sitter_language_pack')
    email = 'jordan' + '@' + 'mail.io'
    for text in (f'{prefix} by {email}\n', string_line.format(email=email) + '\n'):
        row = document(pack, text, 'code')
        original = dict(row)
        result = c.f1(row)
        assert result == c.f1(dict(row, lang_label=lang))
        assert result == ('fix', text.replace(email, '<EMAIL>'))
        assert c.f1(dict(row, text=result[1])) == ('keep', result[1])
        assert row == original


def test_generic_code_tag_preserves_arithmetic_and_runs_in_clean(cleaner):
    c = cleaner
    pytest.importorskip('tree_sitter_language_pack')
    text = 'package main\nvar x = 555-010-0199\n'
    assert c.f1(document('code-go', text, 'code')) == ('keep', text)
    text = 'package main // by jordan' + '@' + 'mail.io\n'
    assert c.clean(document('code-go', text, 'code')) == ('fix', 'package main // by <EMAIL>\n')


def test_explicit_code_language_is_preserved(cleaner, monkeypatch):
    c = cleaner
    seen = []
    def spans(text, lang):
        seen.append(lang)
        return [(0, len(text.encode('utf-8')))]
    monkeypatch.setattr(c, '_f1_text_spans', spans)
    c.f1(document('code-js-ts', '// by jordan' + '@' + 'mail.io\n', 'javascript'))
    assert seen == ['javascript']


def test_unknown_code_pack_does_not_guess_a_parser(cleaner):
    c = cleaner
    text = '// by jordan' + '@' + 'mail.io\n'
    assert c._shared_f1(document('code-unknown', text, 'code')) == ('keep', text)


@pytest.mark.parametrize('text', ['श्लोकः॥१०० अनन्तरम्।', 'श्लोकः॥100 अनन्तरम्।',
                                 'वर्षे १९९६तमे संवत्सरे।', 'वर्षे 1996तमे संवत्सरे।',
                                 'वर्षा१९९६तमे संवत्सरे।'])
def test_sanskrit_b4_preserves_numbers_and_removes_wiki_markup(cleaner, text):
    c = cleaner
    row = document('ind-sa-fw2', text, 'san_Deva')
    rule = c._RULE['DB-B4-004']()
    assert rule(row) == ('keep', text)
    marked = "{{template}}'''[[लेखः|" + text + "]]'''↩"
    assert rule(dict(row, text=marked)) == ('fix', text)


# ---------------------------------------------------------------- cadj-commits: e-mail addresses only
def test_cadj_commits_masks_private_emails_and_nothing_else(cleaner):
    c = cleaner
    private = 'jordan.lee' + '@' + 'mail.io'
    text = ('Fix the parser\n\nSigned-off-by: Jordan Lee <' + private + '>\n'
            'support' + '@' + 'acme.io, dev' + '@' + 'example.com, someone' + '@' + 'users.noreply.github.com, logo' + '@' + '2x.png\n'
            'ping 192.168.127.12 or call +1 (555) 010-0199; part 307-355-022; rgb 255 239 213\n'
            '42 Wallaby Way, Sydney\n')
    action, out = c.clean(document('cadj-commits', text, 'code'))
    assert (action, out) == ('fix', text.replace(private, '<EMAIL>'))
    assert c.clean(document('cadj-commits', out, 'code')) == ('keep', out)


def test_cadj_commits_never_drops(cleaner):
    c = cleaner
    card = ''.join(f'user{i}' + '@' + 'mail.io\n' for i in range(8))
    action, out = c.clean(document('cadj-commits', card, 'code'))
    assert action == 'fix' and out == '<EMAIL>\n' * 8
    assert c.clean(document('cadj-commits', 'no address here\n', 'code')) == ('keep', 'no address here\n')


def test_cadj_commits_keeps_test_domains_mail_and_profile_urls(cleaner):
    # diagnosis/submissions/cadj-commits/kunal2016/medicine.md, medicine 1: test domains and mail@ stay.
    # Its LinkedIn profile URLs are deferred, so they stay too.
    c = cleaner
    text = ('fake = "jane' + '@' + 'test.com"; mail' + '@' + 'acme.io; x' + '@' + 'domain.com\n'
            'see https://www.linkedin.com/in/jane-doe-123/ and http://linkedin.com/in/jdoe\n')
    assert c.clean(document('cadj-commits', text, 'code')) == ('keep', text)


def test_every_family_has_a_pipeline(cleaner):
    # a harm adapter runs _PIPELINES[_FAMILY[pack]]: every family needs an entry, code-adjacent an empty one
    c = cleaner
    assert set(c._FAMILY.values()) <= set(c._PIPELINES)
    assert c._PIPELINES['code-adjacent'] == ()
    assert [p for p, f in c._FAMILY.items() if f == 'code-adjacent'] == ['cadj-commits']
    assert 'cadj-commits' in c.SCOPE['f1_rule.py']
    assert not [rid for rid, packs in c.SCOPE.items() if 'cadj-commits' in packs and rid != 'f1_rule.py']
    text = 'Signed-off-by: Jordan Lee <jordan.lee' + '@' + 'mail.io>\n'
    row = document('cadj-commits', text, 'code')
    family = c._PIPELINES[c._FAMILY['cadj-commits']]
    assert c._run(row, *family, c._shared_f1_rule) == c.clean(row) == ('fix', 'Signed-off-by: Jordan Lee <<EMAIL>>\n')


@pytest.mark.parametrize('pack, lang', [('cadj-notebooks', 'code'), ('cadj-stackexchange', 'en')])
def test_deferred_code_adjacent_packs_pass_through(cleaner, pack, lang):
    # no gold set yet; stackexchange's e-mail-like strings are mostly ssh and git logins and URLs with a user name
    c = cleaner
    text = ('by jordan.lee' + '@' + 'mail.io; try `ssh pi' + '@' + 'raspberrypi.com` or git clone https://me' + '@' + 'bitbucket.org/x.git\n'
            'see https://www.linkedin.com/in/jane-doe-123/\n')
    assert c.clean(document(pack, text, lang)) == ('keep', text)
    assert pack not in c._FAMILY and pack not in c.SCOPE['f1_rule.py']
