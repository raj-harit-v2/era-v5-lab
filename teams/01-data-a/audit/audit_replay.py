"""Replay the sampled documents of a finished clean job rule by rule, for the reading audit.

    python -I teams/01-data-a/audit/audit_replay.py --job <clean job output folder> --input-root <raw parts folder> \\
        --out <folder> [--pack en-dclm ...]

The job's rule_examples.csv names, for each pack and rule, a few documents that rule acted on. This script runs those
documents again through the cleaner the job used (the path and sha256 pin come from job_summary.json) and records every rule
that acted on each one, with the text before and after. Rules run in sequence, so a document that several rules changed
shows every step, not only the rule it was sampled for. Nothing is written to the job's folder, and the job is not rerun:
only the sampled documents (a few hundred per pack) go through the cleaner.

For each pack it writes <out>/<pack>/
    docs.csv      one row per document: the rules it was sampled for, every rule that acted on it, the final action
    trace.jsonl   one line per step: doc_id, step, rule_id, action, text_before, text_after
    raw.parquet, cleaned.parquet   the raw and the cleaned rows of these documents (a dropped document has no cleaned row)
    ids.txt       the doc_ids, for view_reading.py --ids

Each replay is checked against the job's own output: the replayed action and text must be what the job wrote, and the rules
the document was sampled for must be among the rules replayed. A document that fails is marked replay_ok=False in docs.csv
and the script exits with 1. The files hold document text: keep <out> outside the job folder and out of the repository.
"""
import sys
sys.dont_write_bytecode = True

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

PIPELINE = Path(__file__).resolve().parents[1] / 'pipeline'
sys.path.insert(0, str(PIPELINE))  # python -I does not put any folder on sys.path
import clean_job as job  # the job's own loader and rule wrapper

DOC_COLUMNS = ['pack_id', 'doc_id', 'part', 'sampled_for', 'rules', 'final_action', 'chars_raw', 'chars_cleaned', 'replay_ok']


class Trace(job.RuleCounter):
    """The job's own rule wrapper calls note() for every fix or drop, with the text the rule saw and what it returned;
    here that is all recorded, for one document at a time (the caller empties `steps` before each)."""

    def __init__(self):
        super().__init__(audit_samples=1)  # any value above 0 turns note() on
        self.steps = []

    def note(self, rid, doc, action, text):
        self.steps.append(dict(rule_id=rid, action=action, text_before=doc['text'],
                               text_after=None if action == 'drop' else text))


def examples(job_dir, packs):
    """{pack: {part: {doc_id: [rules it was sampled for]}}} from rule_examples.csv, in the file's order."""
    path = job_dir / 'rule_examples.csv'
    if not path.is_file():
        raise job.JobError(f'{path} is not there: was the job run with audit_samples above 0?')
    found = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    with path.open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            if row['doc_id'] and (not packs or row['pack_id'] in packs):
                found[row['pack_id']][row['part']][row['doc_id']].append(row['rule_id'])
    missing = sorted(set(packs) - set(found))
    if missing:
        raise job.JobError('no examples for pack(s): ' + ', '.join(missing))
    return found


def read_rows(path, ids):
    """({doc_id: row}, schema) for the rows of the part with these doc_ids."""
    table = pq.read_table(path, filters=[('doc_id', 'in', sorted(ids))])
    return {row['doc_id']: row for row in table.to_pylist()}, table.schema


def replay_pack(pack, parts, job_dir, input_root, out, trace):
    docs, steps, raw_rows, cleaned_rows = [], [], [], []
    for part, wanted in parts.items():
        raw, schema = read_rows(input_root / part, wanted)
        cleaned, _ = read_rows(job_dir / part, wanted)  # a dropped document is not in the job's part
        for doc_id, sampled in wanted.items():
            if doc_id not in raw:
                raise job.JobError(f'{doc_id} is not in the raw part {input_root / part}')
            trace.steps = []
            action, text = job.clean.clean(raw[doc_id])
            expected = cleaned.get(doc_id)
            same = expected is None if action == 'drop' else expected is not None and expected['text'] == text
            rules = [step['rule_id'] for step in trace.steps]
            raw_rows.append(raw[doc_id])
            if expected is not None:
                cleaned_rows.append(expected)
            steps += [dict(doc_id=doc_id, step=n, **step) for n, step in enumerate(trace.steps, 1)]
            docs.append(dict(pack_id=pack, doc_id=doc_id, part=part, sampled_for='|'.join(sampled), rules='|'.join(rules),
                             final_action=action, chars_raw=len(raw[doc_id]['text']),
                             chars_cleaned='' if expected is None else len(expected['text']),
                             replay_ok=same and set(sampled) <= set(rules)))
    folder = out / pack
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'docs.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=DOC_COLUMNS)
        writer.writeheader()
        writer.writerows(docs)
    with (folder / 'trace.jsonl').open('w', encoding='utf-8') as stream:
        stream.writelines(json.dumps(step, ensure_ascii=False) + '\n' for step in steps)
    pq.write_table(pa.Table.from_pylist(raw_rows, schema=schema), folder / 'raw.parquet', compression='zstd')
    pq.write_table(pa.Table.from_pylist(cleaned_rows, schema=schema), folder / 'cleaned.parquet', compression='zstd')
    (folder / 'ids.txt').write_text(''.join(d['doc_id'] + '\n' for d in docs), encoding='utf-8')
    return docs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--job', type=Path, required=True, help='the finished clean job folder (job_summary.json, rule_examples.csv)')
    parser.add_argument('--input-root', type=Path, required=True, help='the folder with the raw parts the job read')
    parser.add_argument('--out', type=Path, required=True, help='where the replay goes (holds document text)')
    parser.add_argument('--pack', action='append', default=[], help='a pack to replay; repeatable (default: every pack with examples)')
    args = parser.parse_args(argv)
    job_dir, out = args.job.resolve(), args.out.resolve()
    if out == job_dir or job_dir in out.parents:
        raise job.JobError('--out must be outside the job folder: it holds document text')
    summary = job.read_json(job_dir / 'job_summary.json')
    if not summary.get('audit_samples'):
        raise job.JobError('the job was run with audit_samples 0: it has no examples')
    job.load_clean(job.REPO / summary['clean_path'], summary['clean_sha256'])
    found = examples(job_dir, set(args.pack))
    trace, failed = Trace(), []
    with trace.instrument():
        for pack in sorted(found):
            docs = replay_pack(pack, found[pack], job_dir, args.input_root.resolve(), out, trace)
            failed += [d['pack_id'] + ' ' + d['doc_id'] for d in docs if not d['replay_ok']]
            print(json.dumps({'pack': pack, 'documents': len(docs), 'replay_ok': sum(d['replay_ok'] for d in docs)}, sort_keys=True))
    if failed:
        print(f'ERROR: {len(failed)} document(s) did not replay as the job cleaned them: ' + ', '.join(failed[:10]), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except job.JobError as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
