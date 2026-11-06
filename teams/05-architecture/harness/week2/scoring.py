"""PR191 source binding and PR197 three-group scoring; no corpus mutation."""

import hashlib
import json
import math
from pathlib import Path

INDIC = ('hi', 'bn', 'ta', 'te', 'kn', 'ml', 'mr', 'gu', 'pa', 'or', 'as')


def source_slices(path, records):
    """Require exact id/order/text binding to the owner's sources sidecar."""
    sources = [
        json.loads(line)
        for line in Path(path).read_text(encoding='utf8').splitlines()
        if line.strip()
    ]
    if len(sources) != len(records):
        raise ValueError('Source/document count mismatch')
    result = []
    seen = set()
    for row, doc in zip(sources, records):
        identity = doc.get('id')
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError('Unique nonempty string IDs required for slice scoring')
        seen.add(identity)
        if row.get('id') != identity:
            raise ValueError('Source id/order mismatch')
        if (
            row.get('text_sha256')
            != hashlib.sha256(doc['text'].encode('utf8')).hexdigest()
        ):
            raise ValueError('Source text hash mismatch')
        name = row.get('slice')
        if name not in ('en', 'code', 'math', 'sci', *INDIC):
            raise ValueError('Unknown heldout slice: ' + str(name))
        result.append(name)
    return result


def group_metrics(slices):
    """Inputs are BPB after summing nats/bytes WITHIN each slice."""
    required = {'en', 'code', *INDIC}
    if not required <= slices.keys():
        raise ValueError(
            'Missing required score slices: ' + str(sorted(required - slices.keys()))
        )
    if any(not math.isfinite(v) or v < 0 for v in slices.values()):
        raise ValueError('Invalid slice BPB')
    # Give each Indic slice equal weight in the Indic group mean.
    indic = math.fsum(slices[k] for k in INDIC) / len(INDIC)
    return {
        'val/groups/english_bpb': slices['en'],
        'val/groups/code_bpb': slices['code'],
        'val/groups/indic_mean_bpb': indic,
        'val/three_group_bpb': math.fsum([slices['en'], slices['code'], indic]) / 3,
    }


def compare_arms(challenger, runner_up):
    """Compare completed runs at seeds 1234..1236; conservative max spread guard.

    Each record: seed, eligible_for_quality_comparison and three group metrics.
    Caller identifies the plan-required comparator (runner-up or family baseline).
    """
    keys = ('val/three_group_bpb', 'val/groups/code_bpb', 'val/groups/indic_mean_bpb')

    def stats(rows):
        if len(rows) != 3 or {r['seed'] for r in rows} != {1234, 1235, 1236}:
            raise ValueError('Exactly seeds 1234, 1235 and 1236 required')
        if not all(r.get('eligible_for_quality_comparison') is True for r in rows):
            raise ValueError('Incomplete/smoke runs cannot select winners')
        out = {}
        for k in keys:
            values = [r[k] for r in rows]
            if not all(
                type(v) in (float, int) and math.isfinite(v) and v >= 0 for v in values
            ):
                raise ValueError('Invalid result metric')
            out[k] = {
                'mean': math.fsum(values) / 3,
                'spread': max(values) - min(values),
            }
        return out

    a, b = stats(challenger), stats(runner_up)
    gain = b[keys[0]]['mean'] - a[keys[0]]['mean']
    threshold = max(a[keys[0]]['spread'], b[keys[0]]['spread'])
    guards = {
        k: a[k]['mean'] - b[k]['mean'] <= max(a[k]['spread'], b[k]['spread'])
        for k in keys[1:]
    }
    return {
        'wins': gain > threshold and all(guards.values()),
        'score_improvement': gain,
        'required_improvement': threshold,
        'regression_guards': guards,
        'challenger': a,
        'comparator': b,
        'noise_policy': 'larger of the two arms seed spreads for each compared metric',
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Compare completed three-seed arms; input JSON has challenger and runner_up arrays.'
    )
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    payload = json.loads(args.results.read_text(encoding='utf8'))
    print(
        json.dumps(
            compare_arms(payload['challenger'], payload['runner_up']),
            indent=2,
            allow_nan=False,
        )
    )
