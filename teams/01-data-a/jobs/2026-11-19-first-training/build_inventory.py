"""Freeze staged raw Parquet inputs into a manifest and pipeline-compatible inventory.

Run before cleaning; requires PyArrow. All paths are relative to --input-root,
with layout <train|heldout>/<pack>/part-<number>.parquet. No sampling or file limit is used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def identity(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def build(root, out, scope_file):
    import pyarrow.parquet as pq

    scope = json.loads(scope_file.read_bytes())
    policy = scope['dedup_policy']
    approval = scope.get('tsai_manifest_approval')
    if not isinstance(approval, str) or not approval.strip():
        raise ValueError('approved scope has no tsai_manifest_approval text to record')
    config = REPO / policy['file']
    if sha256(config) != policy['sha256']:
        raise ValueError('dedup.json changed: review and refresh the approved scope first')
    dedup = json.loads(config.read_bytes())
    packs = scope['packs']
    ids = [p['pack_id'] for p in packs]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError('approved scope must list distinct pack IDs')
    if scope['allowed_train_packs'] != ids:
        raise ValueError('allowed train list differs from the approved pack list')
    if scope['split_policy']['shard_splits'] != ['train']:
        raise ValueError('only train may be sharded')
    if (set(scope['splits']) != {'train', 'heldout'}
            or scope['splits']['train']['expected'] != ['written', 'empty', 'all_left_out']
            or scope['splits']['heldout']['expected'] != 'not_sharded'):
        raise ValueError('inventory must expect train written/empty/all_left_out and heldout not_sharded')
    if dedup['default_licence_usable'] is not False:
        raise ValueError('unknown packs must remain unusable by default')
    for pack in ids:
        if dedup['licence_usable'].get(pack) is not True or pack not in dedup['pack_order']:
            raise ValueError(f'pack is not explicitly eligible and ranked: {pack}')
    if not root.is_dir():
        raise ValueError(f'input root is not a directory: {root}')
    if out.exists():
        raise ValueError(f'output already exists; use a new folder: {out}')
    if out == root or root in out.parents or out in root.parents:
        raise ValueError('output folder must not overlap the raw input root')
    paths = sorted(root.rglob('*.parquet'))
    if not paths:
        raise ValueError('no raw Parquet parts found')
    counts = {(split, pack): 0 for split in scope['splits'] for pack in ids}
    shards, indices = [], {}
    for path in paths:
        relative = path.relative_to(root)
        if (len(relative.parts) != 3 or path.resolve() != path.absolute()
                or not path.is_file()):
            raise ValueError(f'expected regular <split>/<pack>/<file>.parquet: {relative}')
        split, pack, _ = relative.parts
        if (split, pack) not in counts:
            raise ValueError(f'unapproved pack or split: {relative}')
        match = re.fullmatch(r'part-([0-9]+)\.parquet', path.name)
        if not match:
            raise ValueError(f'part name is incompatible with the sharder: {relative}')
        key = split, pack, int(match.group(1))
        if key in indices:
            raise ValueError(f'duplicate numeric part index: {indices[key]} and {relative}')
        indices[key] = relative.as_posix()
        before = path.stat()
        with pq.ParquetFile(path) as parquet:
            rows = parquet.metadata.num_rows
            columns = parquet.schema_arrow.names
        missing = sorted(set(scope['required_columns']) - set(columns))
        if missing:
            raise ValueError(f'{relative}: missing columns {missing}')
        digest = sha256(path)
        after = path.stat()
        if identity(before) != identity(after):
            raise ValueError(f'input changed while reading: {relative}')
        shards.append({'path': relative.as_posix(), 'split': split, 'pack_id': pack,
                       'rows': rows, 'bytes': after.st_size, 'sha256': digest})
        counts[split, pack] += 1
    missing = [f'{split}/{pack}' for (split, pack), n in counts.items()
               if n < scope['splits'][split]['minimum_parts_per_pack']]
    if missing:
        raise ValueError('missing required pack/split inputs: ' + ', '.join(missing))
    if sorted(root.rglob('*.parquet')) != paths:
        raise ValueError('input part list changed while scanning')
    manifest = {
        'name': 'era-v5-lab first training inputs',
        '_scope': 'Source scope as approved in approved_inputs.json (approved_inputs_sha256); actual files enumerated before cleaning.',
        '_source_metadata': 'Source labels copied from sample v0; fetch revisions require separate provenance.',
        'approved_inputs_sha256': sha256(scope_file),
        'source_policy': scope['source_policy'],
        'total_docs': sum(p['rows'] for p in shards),
        'total_file_bytes': sum(p['bytes'] for p in shards),
        'packs': [{k: p[k] for k in ('pack_id', 'group', 'lang_label', 'source',
                                   'source_revision', 'license', 'license_source', 'subset_requirements',
                                   'language', 'script', 'domain', 'lane')} for p in packs],
        'shards': shards,
    }
    manifest_bytes = encoded(manifest)
    inventory = {
        '_status': 'materialized_from_staged_raw_inputs',
        '_approval': approval,
        'input_manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
        'packs': ids,
        'parts': [{'part': p['path'], 'split': p['split'], 'pack_id': p['pack_id'],
                   'raw_sha256': p['sha256'], 'raw_rows': p['rows'],
                   'expected': scope['splits'][p['split']]['expected']} for p in shards],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.input-inventory-', dir=out.parent) as tmp:
        bundle = Path(tmp) / 'bundle'
        bundle.mkdir()
        (bundle / 'input_manifest.json').write_bytes(manifest_bytes)
        (bundle / 'expected_inventory.json').write_bytes(encoded(inventory))
        os.rename(bundle, out)
    return {'packs': len(ids), 'parts': len(shards), 'raw_rows': manifest['total_docs'],
            'input_manifest_sha256': inventory['input_manifest_sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='new folder for the two frozen JSON files')
    parser.add_argument('--scope', type=Path, default=HERE / 'approved_inputs.json')
    args = parser.parse_args()
    try:
        summary = build(args.input_root.resolve(), args.out.resolve(), args.scope.resolve())
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f'build_inventory: {exc}\n')
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
