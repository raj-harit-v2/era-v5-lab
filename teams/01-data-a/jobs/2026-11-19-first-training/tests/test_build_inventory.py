"""Input coverage and train/heldout contract checks using real synthetic Parquets."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import types

import pytest

pa = pytest.importorskip('pyarrow')
import pyarrow.parquet as pq

JOB = Path(__file__).resolve().parents[1]
REPO = JOB.parents[3]
spec = importlib.util.spec_from_file_location('first_training_inputs', JOB / 'build_inventory.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
run_spec = importlib.util.spec_from_file_location('first_training_prepare', JOB / 'prepare_run.py')
prepare_run = importlib.util.module_from_spec(run_spec)
run_spec.loader.exec_module(prepare_run)
sys.path.insert(0, str(REPO / 'teams/01-data-a/pipeline'))
import inventory_check


@pytest.fixture
def scope():
    return json.loads((JOB / 'approved_inputs.json').read_bytes())


@pytest.fixture
def raw(tmp_path, scope):
    root = tmp_path / 'raw'
    for pack in scope['packs']:
        for split in ('train', 'heldout'):
            folder = root / split / pack['pack_id']
            folder.mkdir(parents=True)
            n = 2 if split == 'train' else 1
            table = pa.table({'doc_id': [f'{split}-{i}' for i in range(n)],
                              'text': ['synthetic input'] * n,
                              'pack_id': [pack['pack_id']] * n,
                              'lang_label': [pack['lang_label']] * n})
            pq.write_table(table, folder / 'part-00000.parquet')
    return root


def run(raw, out, scope_file=None):
    return builder.build(raw, out, scope_file or JOB / 'approved_inputs.json')


def test_scope_matches_the_actual_dedup_allowlist_and_source_policy(scope):
    config = json.loads((REPO / scope['dedup_policy']['file']).read_bytes())
    sample = json.loads((REPO / scope['sample_reference']['file']).read_bytes())
    assert len(scope['allowed_train_packs']) == 38
    assert set(scope['allowed_train_packs']) == set(config['pack_order']) == set(config['licence_usable'])
    assert all(config['licence_usable'].values()) and config['default_licence_usable'] is False
    assert set(scope['allowed_train_packs']) == {p['pack_id'] for p in sample['packs']}
    assert all(scope['source_policy']['commit'] in p['license_source'] for p in scope['packs'])
    assert 'chandassu' not in scope['allowed_train_packs']


def test_expanded_inputs_preserve_both_splits_but_only_train_expects_shards(raw, tmp_path):
    original = raw / 'train/code-go/part-00000.parquet'
    for index in range(1, 21):
        original.with_name(f'part-{index:05d}.parquet').write_bytes(original.read_bytes())
    out = tmp_path / 'frozen'
    summary = run(raw, out)
    inventory = inventory_check.load(out / 'expected_inventory.json')
    manifest_bytes = (out / 'input_manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    assert summary['parts'] == len(inventory['parts']) == 96  # production is not limited to 86
    assert inventory['input_manifest_sha256'] == hashlib.sha256(manifest_bytes).hexdigest()
    assert manifest['total_docs'] == 154
    scope = json.loads((JOB / 'approved_inputs.json').read_bytes())
    raw_inventory = json.loads((out / 'expected_inventory.json').read_text())
    assert raw_inventory['_approval'] == scope['tsai_manifest_approval']  # copied from the approved scope
    assert raw_inventory['_approval'].startswith('confirmed_22_nov_2026')
    assert 'assumption' not in raw_inventory['_approval'] and 'assumption' not in manifest['_scope']
    for name, entry in inventory['parts'].items():
        assert entry['raw_sha256'] == hashlib.sha256((raw / name).read_bytes()).hexdigest()
        assert entry['raw_rows'] == pq.ParquetFile(raw / name).metadata.num_rows
        assert entry['expected'] == (['all_left_out', 'empty', 'written'] if entry['split'] == 'train' else ['not_sharded'])
    assert all(p['license_source'] and p['license'] for p in manifest['packs'])
    assert len([p for p in inventory['parts'].values() if p['split'] == 'heldout']) == 38
    shards = tmp_path / 'shards'
    shards.mkdir()
    entries = {name: {'pack_id': p['pack_id'], 'status': p['expected'][0]}
               for name, p in inventory['parts'].items()}
    (shards / 'shards_summary.json').write_text(json.dumps({'parts': entries}))
    assert inventory_check.check(inventory, shards=shards)['ok']
    entries['heldout/code-go/part-00000.parquet']['status'] = 'written'
    (shards / 'shards_summary.json').write_text(json.dumps({'parts': entries}))
    assert not inventory_check.check(inventory, shards=shards)['ok']


@pytest.mark.parametrize("partial", [False, True])
def test_prepare_run_pins_the_actual_inventory_and_refuses_incomplete_pack_metadata(raw, tmp_path, scope, monkeypatch, partial):
    out = tmp_path / 'out' / 'inputs'
    selected = json.loads((JOB / 'staged_packs_33.json').read_text()) if partial else None
    if partial:
        for pack in set(scope['allowed_train_packs']) - set(selected):
            for split in ('train', 'heldout'):
                (raw / split / pack / 'part-00000.parquet').unlink()
        scope['packs'] = [p for p in scope['packs'] if p['pack_id'] in selected]
    builder.build(raw, out, JOB / 'approved_inputs.json', selected)
    monkeypatch.setattr(prepare_run, 'REPO', tmp_path)
    tokenizer = tmp_path / 'tokenizer.json'
    tokenizer.write_text('{}', encoding='utf-8')
    monkeypatch.setattr(prepare_run, 'TOKENIZER_SHA256', prepare_run.sha256(tokenizer))
    model = tmp_path / 'model'
    model.mkdir()
    pins = {}
    for name in prepare_run.MODEL_FILES:
        file = model / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(name.encode())
        pins[name] = (file.stat().st_size, prepare_run.sha256(file))
    monkeypatch.setattr(prepare_run, 'MODEL_FILES', pins)
    base = json.loads((REPO / 'teams/01-data-a/shards/pack_table.json').read_text())['packs']
    table = {'packs': {p['pack_id']: {**base[p['pack_id']], 'lane': base[p['pack_id']]['lane'] or 'test',
                                     'license': p['license'], 'license_source': p['license_source']}
                       for p in scope['packs']}}
    table_path = tmp_path / 'pack_table.json'
    table_path.write_text(json.dumps(table), encoding='utf-8')
    table['packs']['ind-sa-fw2']['lane'] = None
    table_path.write_text(json.dumps(table), encoding='utf-8')
    with pytest.raises(ValueError, match='incomplete metadata for ind-sa-fw2'):
        prepare_run.prepare(out, raw, tokenizer, table_path, 'first-training-v1', model)
    table['packs']['ind-sa-fw2']['lane'] = 'test'
    table_path.write_text(json.dumps(table), encoding='utf-8')
    (model / 'config.json').write_bytes(b'changed')
    with pytest.raises(ValueError, match='offline H3 model differs'):
        prepare_run.prepare(out, raw, tokenizer, table_path, 'first-training-v1', model)
    assert not (out / 'run.json').exists()
    (model / 'config.json').write_bytes(b'config.json')
    cfg = json.loads(prepare_run.prepare(out, raw, tokenizer, table_path, 'first-training-v1', model,
                                        f2_workers=30).read_text())
    assert cfg['inventory'] == 'out/inputs/expected_inventory.json'
    assert cfg['stages']['clean']['expected_parts'] == {'train': 33 if partial else 38, 'heldout': 33 if partial else 38}
    assert cfg['stages']['overlap']['script'].endswith('/minhash_overlap.py')
    assert cfg['stages']['overlap']['settings'].endswith('/minhash_overlap_partial.json' if partial else '/minhash_overlap.json')
    assert cfg['run_id'] == 'first-training-v1'
    assert cfg['stages']['shards']['dataset_version'] == 'corpus-v1'  # not derived from run_id
    assert cfg['intermediates'] == 'keep' and cfg['stages']['h3']['mode'] == 'run'
    assert cfg['stages']['f2'] == {'pool': True, 'workers': 30}
    # the staged-data sizing gate: a clean-only run without the inventory, and the full run adopting its folder
    clean = json.loads((out / 'run_clean.json').read_text())
    production = json.loads((out / 'run_production.json').read_text())
    assert clean['run_id'] == 'first-training-v1-clean' and clean['to'] == 'clean' and 'inventory' not in clean
    assert clean['stages'] == cfg['stages']
    assert production['stages']['clean'] == {'mode': 'adopt', 'output': 'out/pipeline/first-training-v1-clean/clean'}
    assert production['inventory'] == cfg['inventory'] and production['run_id'] == cfg['run_id'] and 'to' not in production
    assert {k: v for k, v in production['stages'].items() if k != 'clean'} == {k: v for k, v in cfg['stages'].items() if k != 'clean'}
    with pytest.raises(ValueError, match='run config already exists'):
        prepare_run.prepare(out, raw, tokenizer, table_path, 'first-training-v1', model)
    (out / 'run.json').unlink()
    with pytest.raises(ValueError, match='run_clean.json'):          # a gate config left behind is refused too
        prepare_run.prepare(out, raw, tokenizer, table_path, 'first-training-v1', model)
    for name in prepare_run.GATE_CONFIGS:
        (out / name).unlink()
    cfg = json.loads(prepare_run.prepare(out, raw, tokenizer, None, 'first-training-v1', model).read_text())
    generated = json.loads((out / 'pack_metadata.json').read_text())['packs']
    assert cfg['stages']['f2']['workers'] == 1
    assert cfg['stages']['shards']['pack_table'] == 'out/inputs/pack_metadata.json'
    assert len(generated) == (33 if partial else 38)
    assert generated['ind-sa-fw2']['lane'] == 'indic'
    assert generated['code-go']['license'] == next(p['license'] for p in scope['packs'] if p['pack_id'] == 'code-go')


@pytest.mark.parametrize('workers', [0, -1, True, '30'])
def test_prepare_run_rejects_invalid_worker_counts(tmp_path, workers):
    with pytest.raises(ValueError, match='f2_workers must be a positive integer'):
        prepare_run.prepare(tmp_path, tmp_path, tmp_path, tmp_path, 'run', f2_workers=workers)


def test_approved_scope_contains_production_shard_metadata():
    here = REPO / 'teams/01-data-a/jobs/2026-11-19-first-training'
    packs = json.loads((here / 'approved_inputs.json').read_text())['packs']
    metadata = json.loads((REPO / 'teams/01-data-a/shards/pack_table.json').read_text())['packs']
    for p in packs:
        assert all(isinstance(p[k], str) and p[k] for k in
                   ('language', 'script', 'domain', 'lane', 'license', 'license_source'))
        assert all(p[k] == metadata[p['pack_id']][k] for k in ('language', 'script', 'domain', 'lane'))


def test_submission_preserves_rehearsed_h3_settings_and_shard_metadata():
    here = REPO / 'teams/01-data-a/jobs/2026-11-19-first-training'
    evidence = here.parent / 'logs/2026-11-19-first-training-rehearsal-38packs'
    assert json.loads((here / 'h3.json').read_text()) == json.loads((evidence / 'config/h3.json').read_text())
    scope = json.loads((here / 'approved_inputs.json').read_text())
    fields = ('language', 'script', 'domain', 'lane', 'license', 'license_source')
    generated = {p['pack_id']: {k: p[k] for k in fields} for p in scope['packs']}
    rehearsed = json.loads((evidence / 'config/pack_table_job_shaped.json').read_text())['packs']
    assert generated == rehearsed


def test_identical_staging_produces_identical_frozen_files(raw, tmp_path):
    first, second = tmp_path / 'first', tmp_path / 'second'
    run(raw, first)
    run(raw, second)
    for name in ('input_manifest.json', 'expected_inventory.json'):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_prepare_run_refuses_an_inventory_from_another_approved_scope(raw, tmp_path, monkeypatch):
    out = tmp_path / 'out' / 'inputs'
    run(raw, out)
    monkeypatch.setattr(prepare_run, 'REPO', tmp_path)
    manifest = out / 'input_manifest.json'
    data = json.loads(manifest.read_text())
    data['approved_inputs_sha256'] = '0' * 64
    manifest.write_text(json.dumps(data))
    inventory = out / 'expected_inventory.json'
    data = json.loads(inventory.read_text())
    data['input_manifest_sha256'] = prepare_run.sha256(manifest)
    inventory.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='another approved_inputs.json'):
        prepare_run.prepare(out, raw, tmp_path / 'tokenizer.json', None, 'first-training-v1')
    assert not (out / 'run.json').exists() and not (out / 'pack_metadata.json').exists()


@pytest.mark.parametrize('name,message', [
    ('train/not-approved/part-00000.parquet', 'unapproved pack or split'),
    ('validation/code-go/part-00000.parquet', 'unapproved pack or split'),
    ('train/code-go/notes.parquet', 'incompatible with the sharder'),
    ('train/code-go/part-0.parquet', 'duplicate numeric part index'),
    ('train/code-go/nested/part-00001.parquet', 'expected regular'),
])
def test_incompatible_inputs_are_rejected_before_publication(raw, tmp_path, name, message):
    extra = raw / name
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_bytes((raw / 'train/code-go/part-00000.parquet').read_bytes())
    out = tmp_path / 'bad'
    with pytest.raises(ValueError, match=message):
        run(raw, out)
    assert not out.exists()


def test_missing_required_heldout_pack_is_rejected(raw, tmp_path):
    (raw / 'heldout/code-go/part-00000.parquet').unlink()
    with pytest.raises(ValueError, match='missing required pack/split'):
        run(raw, tmp_path / 'missing')


def test_missing_columns_are_rejected(raw, tmp_path):
    pq.write_table(pa.table({'text': ['missing identifiers']}), raw / 'train/code-go/part-00000.parquet')
    with pytest.raises(ValueError, match='missing columns'):
        run(raw, tmp_path / 'schema')


def test_mismatched_dedup_policy_pin_is_rejected(raw, tmp_path, scope):
    scope['dedup_policy']['sha256'] = '0' * 64
    file = tmp_path / 'altered_scope.json'
    file.write_text(json.dumps(scope))
    with pytest.raises(ValueError, match='dedup.json changed'):
        run(raw, tmp_path / 'pins', file)


def test_frozen_output_cannot_be_overwritten(raw, tmp_path):
    out = tmp_path / 'frozen'
    run(raw, out)
    before = (out / 'expected_inventory.json').read_bytes()
    with pytest.raises(ValueError, match='already exists'):
        run(raw, out)
    assert (out / 'expected_inventory.json').read_bytes() == before


def test_scope_cannot_enable_heldout_sharding(raw, tmp_path, scope):
    scope['split_policy']['shard_splits'].append('heldout')
    file = tmp_path / 'wrong_scope.json'
    file.write_text(json.dumps(scope))
    with pytest.raises(ValueError, match='only train may be sharded'):
        run(raw, tmp_path / 'wrong_split', file)


def test_scope_without_a_recorded_tsai_approval_is_rejected(raw, tmp_path, scope):
    del scope['tsai_manifest_approval']
    file = tmp_path / 'unconfirmed_scope.json'
    file.write_text(json.dumps(scope))
    with pytest.raises(ValueError, match='no tsai_manifest_approval'):
        run(raw, tmp_path / 'unconfirmed', file)
    assert not (tmp_path / 'unconfirmed').exists()


def test_prepare_run_refuses_to_start_without_the_f1_grammars(monkeypatch):
    fake = types.ModuleType('tree_sitter_language_pack')
    fake.downloaded_languages = lambda: ['cpp', 'go']
    monkeypatch.setitem(sys.modules, 'tree_sitter_language_pack', fake)
    with pytest.raises(ValueError, match='java, javascript, python, rust, typescript; run the setup step'):
        prepare_run.check_f1_parsers()
    fake.downloaded_languages = lambda: list(prepare_run.F1_PARSERS)
    prepare_run.check_f1_parsers()


def test_prepare_run_checks_the_grammars_before_anything_else(monkeypatch, tmp_path):
    def missing():
        raise ValueError('tree-sitter grammars for F1 are not downloaded: go; run the setup step')
    monkeypatch.setattr(prepare_run, 'check_f1_parsers', missing)
    monkeypatch.setattr(prepare_run, 'prepare', lambda *a, **k: pytest.fail('prepare ran without the grammars'))
    monkeypatch.setattr(sys, 'argv', ['prepare_run.py', '--bundle', str(tmp_path), '--input-root', str(tmp_path),
                                      '--tokenizer', str(tmp_path), '--run-id', 'run'])
    with pytest.raises(SystemExit) as stop:
        prepare_run.main()
    assert stop.value.code == 1


def test_f1_grammars_match_the_cleaner():
    rule = (REPO / 'teams/01-data-a/spec_v1_1/build/f1_rule.py').read_text(encoding='utf-8')
    assert ast.literal_eval(re.search(r'^_F1_TREE = (\{[^}]*\})', rule, re.M).group(1)) == set(prepare_run.F1_PARSERS)


def test_partial_inventory_freezes_selected_and_deferred_packs(raw, tmp_path, scope):
    selected = [p for p in scope['allowed_train_packs'] if p in json.loads((JOB / 'staged_packs_33.json').read_text())]
    deferred = [p for p in scope['allowed_train_packs'] if p not in selected]
    for pack in deferred:
        for split in ('train', 'heldout'):
            (raw / split / pack / 'part-00000.parquet').unlink()
    out = tmp_path / 'partial'
    summary = builder.build(raw, out, JOB / 'approved_inputs.json', list(reversed(selected)))
    manifest = json.loads((out / 'input_manifest.json').read_text())
    inventory = inventory_check.load(out / 'expected_inventory.json')
    assert summary['packs'] == 33 and summary['parts'] == 66
    assert set(inventory['packs']) == set(selected)
    assert manifest['pack_selection']['selected_packs'] == selected
    assert manifest['pack_selection']['deferred_packs'] == deferred
    assert {p['pack_id'] for p in manifest['packs']} == set(selected)
    # A missing split for a selected pack must never become another implicit exclusion.
    (raw / 'heldout' / selected[0] / 'part-00000.parquet').unlink()
    with pytest.raises(ValueError, match='missing required pack/split'):
        builder.build(raw, tmp_path / 'missing-selected', JOB / 'approved_inputs.json', selected)


@pytest.mark.parametrize('kind', ['short', 'duplicate', 'unknown', 'not-list'])
def test_invalid_partial_selection_is_rejected(raw, tmp_path, scope, kind):
    selected = scope['allowed_train_packs'][:33]
    if kind == 'short':
        selected.pop()
    elif kind == 'duplicate':
        selected[-1] = selected[0]
    elif kind == 'unknown':
        selected[-1] = 'not-approved'
    else:
        selected = {'packs': selected}
    with pytest.raises(ValueError, match='33 distinct approved'):
        builder.build(raw, tmp_path / 'bad-selection', JOB / 'approved_inputs.json', selected)


def test_partial_selection_rejects_staged_files_outside_selection(raw, tmp_path, scope):
    with pytest.raises(ValueError, match='unapproved pack or split'):
        builder.build(raw, tmp_path / 'unexpected', JOB / 'approved_inputs.json', scope['allowed_train_packs'][:33])


def test_prepare_rejects_inconsistent_partial_selection(raw, tmp_path, scope, monkeypatch):
    out = tmp_path / 'out' / 'inputs'
    run(raw, out)
    monkeypatch.setattr(prepare_run, 'REPO', tmp_path)
    manifest_path = out / 'input_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['pack_selection'] = {'selected_packs': scope['allowed_train_packs'][:33],
                                  'deferred_packs': [], 'approval': 'partial run'}
    manifest_path.write_text(json.dumps(manifest))
    inventory_path = out / 'expected_inventory.json'
    inventory = json.loads(inventory_path.read_text())
    inventory['input_manifest_sha256'] = prepare_run.sha256(manifest_path)
    inventory_path.write_text(json.dumps(inventory))
    with pytest.raises(ValueError, match='invalid 33-pack selection'):
        prepare_run.prepare(out, raw, tmp_path / 'tokenizer.json', None, 'partial-run')
    assert not (out / 'run.json').exists()


def test_confirmed_staged_selection_matches_tsai_exclusions(scope):
    selected = json.loads((JOB / 'staged_packs_33.json').read_text())
    assert len(selected) == len(set(selected)) == 33
    assert set(scope['allowed_train_packs']) - set(selected) == {
        'en-dclm', 'en-nemotroncc', 'en-nemotroncc-synth', 'math-finemath', 'ind-hi-hplt'}
    assert set(selected) <= set(scope['allowed_train_packs'])
