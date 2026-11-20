"""The pipeline's clean stage: run a manifest's raw parts through a pinned clean.py, with sequential per-rule counts.

    python -I teams/01-data-a/pipeline/clean_job.py --config <run>/cfg/clean.json [--only <part> ...] [--resume]

The config is the clean settings file (pipeline/clean.json: "clean", the path of the cleaner, and its pin "clean_sha256",
"batch_size", "unsupported_policy") with what run_pipeline.py fills in (input_root, output_root, manifest, manifest_sha256,
expected_parts, sample). The cleaner is read once: its sha256 must be the pin, and the file that was hashed is the file that
runs. The input set is the manifest, checked by clean_manifest.validate (the check --plan runs too): any number of parts,
as long as they match expected_parts.

Offline. Writes exclusively beneath ./out/. Train and heldout stay separate. No source text is printed or added to
reports. The original clean.clean() and _run() execute; factories are wrapped only for counting. F2 is not part of this
job. A pack the cleaner has no rules for is copied through with the status unsupported_passthrough.

Resume. A part is finished when its report exists: the part is written first, the report last. An interrupted or failed
job leaves job_state.json (what it was started with) and the parts it finished. Run it again with "resume": true in the
config (or --resume): parts whose part and report still verify are kept, a part that was being written is redone, and
job_summary.json is built from all the reports. It stops, changing nothing, when the job was started with another
clean.py, job script, manifest or part selection, or when a finished part does not verify; it names each such part and the
two files to delete before the next run. A finished job (job_summary.json) is never resumed or overwritten.
"""
import sys
sys.dont_write_bytecode = True

import argparse
import bisect
from collections import Counter, defaultdict
from contextlib import contextmanager
import csv
from functools import cache
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
try:
    import resource  # Unix only: peak memory for the job log
except ImportError:  # Windows: the run works, peak memory is not recorded
    resource = None
import time
import types
import zlib

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))  # python -I does not put the script's folder on sys.path
import clean_manifest

REQUIRED = ('clean', 'clean_sha256', 'manifest', 'manifest_sha256', 'expected_parts', 'batch_size', 'unsupported_policy', 'audit_samples')
clean = None  # the cleaner module, set by load_clean()


class JobError(Exception):
    pass


def load_clean(path, pin):
    """The cleaner at `path` as the module `clean`, once its sha256 is `pin`. The bytes that are hashed are the bytes that
    run. The module is not registered in sys.modules, so nothing else in the process sees it."""
    global clean
    path = Path(path)
    if not path.is_file():
        raise JobError(f'the cleaner {path} is not there')
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != pin:
        raise JobError(f'clean.py differs from the pin: {path} has sha256 {hashlib.sha256(source).hexdigest()[:12]}…, '
                       f'the config pins {pin[:12]}…')
    module = types.ModuleType('clean')
    module.__file__ = str(path)
    exec(compile(source, str(path), 'exec'), module.__dict__)
    clean = module
    return module


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def peak_rss_mib():
    if resource is None:
        return None
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    unit = 1024 * 1024 if sys.platform == 'darwin' else 1024
    return round(rss / unit, 3)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def safe_path(value):
    try:
        return clean_manifest.part_path(value)
    except clean_manifest.ManifestError as exc:
        raise JobError(str(exc)) from None


def output_folder(value):
    allowed = (Path.cwd() / 'out').resolve()
    path = Path(value).resolve()
    if path == allowed or not path.is_relative_to(allowed):
        raise JobError('output must be a named subfolder of ./out/')
    return path


def manifest(config, only=()):
    """The input set: the manifest, once it is the pinned file and matches expected_parts (clean_manifest.validate, the
    check --plan runs too) and holds every part in `only`."""
    try:
        return clean_manifest.validate(REPO / config['manifest'], config['manifest_sha256'], config['expected_parts'], only)
    except clean_manifest.ManifestError as exc:
        raise JobError(str(exc)) from None


def resolve_input(root, shard, hashes):
    p = safe_path(shard['path'])
    # Official layout split/pack/part, or the user's organized pack/split/part.
    candidates = [root / p, root / p.parts[1] / p.parts[0] / p.parts[2]]
    for folder in (root / p.parts[0] / p.parts[1], root / p.parts[1] / p.parts[0]):
        candidates.extend(sorted(folder.glob('*.parquet')))
    for candidate in dict.fromkeys(candidates):
        if not candidate.is_file() or candidate.stat().st_size != shard['bytes']:
            continue
        if candidate not in hashes:
            hashes[candidate] = digest(candidate)
        if hashes[candidate] == shard['sha256']:
            return candidate
    raise JobError('missing or checksum-mismatched sample part: ' + shard['path'])


STATE = 'job_state.json'


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def open_output(output, fingerprint, resume):
    """(state, resumed) for the output folder; nothing is written or deleted here.

    No folder (or an empty one): a new job. A folder with job_summary.json is a finished job: never touched. Otherwise it
    must hold this runner's job_state.json, and `resume` must be set, and the job must have been started with the same
    clean.py, runner, manifest and parts."""
    if not output.exists() or not any(output.iterdir()):
        return {'fingerprint': fingerprint, 'attempts': []}, False
    if (output / 'job_summary.json').exists():
        raise JobError('output folder holds a finished job; choose a fresh ./out/<job>/')
    if not (output / STATE).is_file():
        raise JobError('output folder already exists and is not an interrupted job (no ' + STATE + '); choose a fresh ./out/<job>/')
    if not resume:
        raise JobError('output folder holds an interrupted job: set "resume": true in the config (or pass --resume) to '
                       'continue it, or choose a fresh ./out/<job>/')
    state = read_json(output / STATE)
    started = state.get('fingerprint') if isinstance(state, dict) else None
    if started != fingerprint:
        keys = sorted(k for k in fingerprint if not isinstance(started, dict) or started.get(k) != fingerprint[k])
        raise JobError('cannot resume: the job was started with another ' + ', '.join(keys) + '; choose a fresh ./out/<job>/')
    if not isinstance(state.get('attempts'), list):
        raise JobError('cannot resume: ' + STATE + ' has no attempts list')
    return state, True


def verify_part(output, shard, supported, audit_samples=0):
    """Why a finished part (its part and its report both exist) does not verify, or None. Cheap checks first, then the
    sha256 of the part, which the report recorded when the part was published."""
    relative = shard['path']
    destination, report_path = output / relative, output / 'reports' / (relative + '.json')
    try:
        report = read_json(report_path)
    except (OSError, ValueError):
        return 'its report cannot be read as JSON', None
    if not isinstance(report, dict):
        return 'its report is not a JSON object', None
    expected = {'part': relative, 'pack_id': shard['pack_id'], 'split': shard['split'], 'input_sha256': shard['sha256'],
                'input_rows': shard['rows'], 'status': 'cleaned' if supported else 'unsupported_passthrough', 'errors': 0}
    for key, value in expected.items():
        if report.get(key) != value:
            return f'its report says {key} = {report.get(key)!r}, the job expects {value!r}', None
    actions = report.get('actions')
    if not isinstance(actions, dict) or not isinstance(report.get('output_rows'), int) or not isinstance(report.get('rule_counts'), dict) \
            or sum(actions.values()) != report['input_rows'] or report['output_rows'] + actions.get('drop', 0) != report['input_rows']:
        return 'its report does not add up (actions, output_rows, input_rows)', None
    try:
        rows = pq.ParquetFile(destination).metadata.num_rows
    except Exception as exc:
        return f'the part cannot be read as Parquet ({type(exc).__name__})', None
    if rows != report['output_rows']:
        return f'the part has {rows} rows, its report says {report["output_rows"]}', None
    if audit_samples and not (output / 'audit' / (relative + '.json')).is_file():
        return f'its audit file audit/{relative}.json is missing', None
    if digest(destination) != report.get('output_sha256'):
        return 'the part has another sha256 than its report records', None
    return None, report


def shown(path):
    """The path as the person who has to delete it types it: relative to where the job runs."""
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return str(path)


def plan_resume(output, shards, audit_samples=0):
    """({part path: its report} for the parts to keep, [paths to delete before redoing the others]).

    Every part is looked at before anything is changed, and a finished part that does not verify stops the job
    naming the part and the two files to delete."""
    kept, cleanup, problems = {}, [], []
    for shard in shards:
        relative = shard['path']
        destination, report_path = output / relative, output / 'reports' / (relative + '.json')
        leftovers = [destination.with_name(destination.name + '.tmp'), report_path.with_name(report_path.name + '.tmp')]
        cleanup += [p for p in leftovers if p.exists()]
        if destination.is_file() and report_path.is_file():
            why, report = verify_part(output, shard, shard['pack_id'] in clean._FAMILY, audit_samples)
            if why:
                problems.append(f'{relative}: {why} (delete {shown(destination)} and '
                                f'{shown(report_path)} to redo it)')
            else:
                kept[relative] = report
        elif report_path.exists():
            problems.append(f'{relative}: a report without its part (delete {shown(report_path)} to redo it)')
        elif destination.exists():  # published, but the report was never written: not a finished part
            cleanup.append(destination)
    if problems:
        more = f' (and {len(problems) - 5} more)' if len(problems) > 5 else ''
        raise JobError(f'cannot resume: {len(problems)} part(s) do not verify, nothing was changed. ' + '; '.join(problems[:5]) + more)
    return kept, cleanup


class RuleCounter:
    def __init__(self, audit_samples=0):
        self.counts = defaultdict(Counter)
        self.audit_samples = audit_samples  # documents to remember per rule; 0 remembers none
        self.samples = defaultdict(list)  # rule id -> up to audit_samples (key, doc_id, action, chars_before, chars_after)

    def note(self, rid, doc, action, text):
        """Remember a document this rule fixed or dropped, if it is among the audit_samples lowest keys so far. The key is a
        hash of rule id and doc_id, so the same documents are picked whatever the order of rows or parts, and after a resume."""
        doc_id = doc.get('doc_id')
        key = zlib.crc32(f'{rid}\0{doc_id}'.encode())
        picked = self.samples[rid]
        if len(picked) < self.audit_samples or key < picked[-1][0]:
            bisect.insort(picked, (key, doc_id, action, len(doc['text']), None if action == 'drop' else len(text)))
            del picked[self.audit_samples:]

    @contextmanager
    def instrument(self):
        original_run = clean._run
        original_ids = dict(clean._ID)
        wrappers = {}

        def wrap(make, rid):
            @cache
            def factory():
                rule = make()

                def counted(doc):
                    try:
                        result = rule(doc)
                        if (not isinstance(result, tuple) or len(result) != 2
                                or result[0] not in {'keep', 'fix', 'drop'} or not isinstance(result[1], str)):
                            raise JobError('invalid rule result')
                    except Exception:
                        self.counts[rid]['error'] += 1
                        raise
                    self.counts[rid][result[0]] += 1
                    if result[0] != 'keep' and self.audit_samples:  # the keep path, nearly all calls, does nothing extra
                        self.note(rid, doc, *result)
                    return result
                return counted
            return factory

        for rid, make in clean._RULE.items():
            wrapped = wrap(make, rid)
            wrappers[make] = wrapped
            clean._ID[wrapped] = rid

        def counted_run(doc, *factories):
            return original_run(doc, *(wrappers[make] for make in factories))

        clean._run = counted_run
        try:
            yield
        finally:
            clean._run = original_run
            clean._ID.clear()
            clean._ID.update(original_ids)


def applicable_rules(pack):
    return [rid for rid in clean._RULE if pack in clean.SCOPE[rid]]


def process_part(source, shard, output, batch_size, audit_samples=0):
    started = time.monotonic()
    relative, pack = shard['path'], shard['pack_id']
    destination = output / relative
    report_path = output / 'reports' / (relative + '.json')
    if destination.exists() or report_path.exists():
        raise JobError('refusing to overwrite existing part: ' + relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.tmp')
    source_file = pq.ParquetFile(source)
    if source_file.metadata.num_rows != shard['rows']:
        raise JobError('input row count differs from sample manifest: ' + relative)
    if not {'doc_id', 'text', 'pack_id', 'lang_label'}.issubset(source_file.schema_arrow.names):
        raise JobError('missing required input columns: ' + relative)
    counter, actions, rows, tags, seen = RuleCounter(audit_samples), Counter(), 0, set(), set()
    supported = pack in clean._FAMILY
    try:
        with counter.instrument(), pq.ParquetWriter(temporary, source_file.schema_arrow, compression='zstd') as writer:
            for batch in source_file.iter_batches(batch_size=batch_size):
                kept = []
                for row in batch.to_pylist():
                    doc_id = row['doc_id']
                    if not isinstance(doc_id, str) or doc_id in seen or not isinstance(row['text'], str):
                        raise JobError('invalid text or duplicate doc_id: ' + relative)
                    if row['pack_id'] != pack:
                        raise JobError('pack_id differs from manifest: ' + relative)
                    seen.add(doc_id)
                    tags.add(row['lang_label'])
                    try:
                        action, text = clean.clean(row)
                    except Exception as exc:
                        write_json(output / 'failure.json', {'part': relative, 'doc_id': doc_id,
                                   'error_type': type(exc).__name__, 'processed_rows': rows,
                                   'rule_counts': dict(counter.counts)})
                        raise JobError('cleaner error: ' + relative + ' doc_id=' + doc_id + ' type=' + type(exc).__name__) from None
                    actions[action] += 1
                    if action != 'drop':
                        kept.append(dict(row, text=text))
                    rows += 1
                if kept:
                    writer.write_table(pa.Table.from_pylist(kept, schema=source_file.schema_arrow))
        if rows != shard['rows']:
            raise JobError('processed rows disagree with manifest: ' + relative)
        if digest(source) != shard['sha256']:
            raise JobError('input changed during processing: ' + relative)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    kept_count = actions['keep'] + actions['fix']
    if pq.ParquetFile(destination).metadata.num_rows != kept_count:
        raise JobError('output row count mismatch: ' + relative)
    per_rule = {}
    for rid in applicable_rules(pack):
        counts = counter.counts[rid]
        invoked = sum(counts.values())
        per_rule[rid] = {kind: counts[kind] for kind in ('keep', 'fix', 'drop', 'error')}
        per_rule[rid].update(invocations=invoked, eligible_by_pack=rows, not_reached=rows-invoked)
    result = {'part': relative, 'pack_id': pack, 'split': shard['split'],
              'status': 'cleaned' if supported else 'unsupported_passthrough',
              'input_sha256': shard['sha256'], 'output_sha256': digest(destination),
              'input_rows': rows, 'output_rows': kept_count,
              'actions': dict(actions), 'errors': 0, 'rule_counts': per_rule,
              'language_tags': sorted(tags, key=str), 'seconds': round(time.monotonic()-started, 3)}
    assert sum(actions.values()) == rows and kept_count + actions['drop'] == rows
    if audit_samples:  # before the report: the report is what marks the part as finished
        write_json(output / 'audit' / (relative + '.json'),
                   {'part': relative, 'pack_id': pack, 'samples_per_rule': audit_samples,
                    'rules': {rid: [dict(zip(('key', 'doc_id', 'action', 'chars_before', 'chars_after'), s)) for s in picked]
                              for rid, picked in sorted(counter.samples.items())}})
    write_json(report_path, result)
    print(json.dumps({k: result[k] for k in ('part', 'status', 'input_rows', 'output_rows', 'actions', 'errors', 'seconds')}, sort_keys=True), flush=True)
    return result


EXAMPLE_COLUMNS = ['pack_id', 'rule_id', 'rank', 'doc_id', 'split', 'part', 'action', 'chars_before', 'chars_after',
                   'pack_fixes', 'pack_drops']


def write_examples(output, reports, audit_samples):
    """rule_examples.csv: for every rule that applies to a pack, the audit_samples documents with the lowest keys over all the
    pack's parts (every part uses the same key, so these are the lowest of the parts' lowest), and the rule's fix and drop
    counts in the pack. A rule that changed nothing in the pack has one row with no document: it never fired."""
    picked, totals = defaultdict(list), defaultdict(Counter)
    for report in reports:
        pack, sidecar = report['pack_id'], output / 'audit' / (report['part'] + '.json')
        if not sidecar.is_file():
            raise JobError(f"the audit file of {report['part']} is missing: delete its part and report to redo it")
        for rid, counts in report['rule_counts'].items():
            totals[pack, rid].update(fix=counts['fix'], drop=counts['drop'])
        for rid, docs in read_json(sidecar)['rules'].items():
            picked[pack, rid] += [dict(doc, part=report['part'], split=report['split']) for doc in docs]
    order = {rid: n for n, rid in enumerate(clean._RULE)}
    with (output / 'rule_examples.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=EXAMPLE_COLUMNS)
        writer.writeheader()
        for pack, rid in sorted(totals, key=lambda k: (k[0], order[k[1]])):
            base = dict(pack_id=pack, rule_id=rid, pack_fixes=totals[pack, rid]['fix'], pack_drops=totals[pack, rid]['drop'])
            docs = sorted(picked[pack, rid], key=lambda d: d['key'])[:audit_samples]
            if not docs:
                writer.writerow(base)
            for rank, doc in enumerate(docs, 1):
                writer.writerow(dict(base, rank=rank, **{k: doc[k] for k in EXAMPLE_COLUMNS[3:9]}))


def write_aggregate(output, reports, provenance, expected_count, audit_samples=0):
    aggregate = {rid: Counter() for rid in clean._RULE}
    for report in reports:
        for rid, counts in report['rule_counts'].items():
            aggregate[rid].update(counts)
    with (output / 'rule_counts.csv').open('w', newline='', encoding='utf-8') as stream:
        columns = ['rule_id', 'eligible_by_pack', 'invocations', 'keep', 'fix', 'drop', 'error', 'not_reached']
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for rid, counts in aggregate.items():
            writer.writerow(dict(rule_id=rid, **{key:counts[key] for key in columns[1:]}))
    if audit_samples:
        write_examples(output, reports, audit_samples)
    summary = dict(provenance, completed_parts=len(reports), expected_parts=expected_count,
                   input_rows=sum(r['input_rows'] for r in reports), output_rows=sum(r['output_rows'] for r in reports),
                   actions=dict(sum((Counter(r['actions']) for r in reports), Counter())),
                   errors=sum(r['errors'] for r in reports),
                   unsupported_parts=[r['part'] for r in reports if r['status']=='unsupported_passthrough'],
                   parts=reports,
                   rule_count_semantics='sequential invocations inside actual clean.clean/_run; fixes on later-dropped docs still count; not independent rule hits')
    write_json(output / 'job_summary.json', summary)
    write_json(output / 'cleaned_manifest.json', {'sample':provenance['sample'], 'complete_sample':len(reports)==expected_count,
               'parts':[{k:r[k] for k in ('part','pack_id','split','status','output_rows','output_sha256')} for r in reports]})
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--input-root', type=Path, help='the folder with the raw parts, instead of input_root in the config')
    parser.add_argument('--out', type=Path, help='the output folder, instead of output_root in the config; still restricted to ./out/<job>/')
    parser.add_argument('--only', action='append', default=[], help='manifest part path for a trial on some parts; repeatable')
    parser.add_argument('--resume', action='store_true', help='continue an interrupted job in its output folder (same as "resume": true in the config)')
    args = parser.parse_args(argv)
    started = time.monotonic()
    config = read_json(args.config)
    missing = [key for key in REQUIRED if key not in config]
    if missing:
        raise JobError('the config lacks ' + ', '.join(missing))
    if not (args.input_root or config.get('input_root')) or not (args.out or config.get('output_root')):
        raise JobError('the config lacks input_root or output_root (or pass --input-root and --out)')
    if config.get('optional_f2'):
        raise JobError('this job runs clean.py only; F2 is its own stage')
    if config['unsupported_policy'] != 'passthrough_with_explicit_status':
        raise JobError('unsupported pack policy must be explicit')
    if type(config['batch_size']) is not int or config['batch_size'] < 1:
        raise JobError('batch_size must be a positive integer')
    if type(config['audit_samples']) is not int or config['audit_samples'] < 0:
        raise JobError('audit_samples must be a whole number, 0 or more (0 writes no audit samples)')
    if not isinstance(config.get('resume', False), bool):
        raise JobError('resume must be true or false')
    resume = config.get('resume', False) or args.resume
    load_clean(REPO / config['clean'], config['clean_sha256'])
    data = manifest(config, args.only)
    shards = [s for s in data['shards'] if not args.only or s['path'] in args.only]
    output = output_folder(args.out or config['output_root'])
    fingerprint = {'clean_sha256': config['clean_sha256'], 'runner_sha256': digest(Path(__file__)),
                   'manifest_sha256': config['manifest_sha256'], 'selected_parts': sorted(s['path'] for s in shards),
                   'audit_samples': config['audit_samples']}
    state, resumed = open_output(output, fingerprint, resume)
    # A resumed job looks at every finished part before it changes anything, and keeps those that verify.
    kept, cleanup = plan_resume(output, shards, config['audit_samples']) if resumed else ({}, [])
    todo = [s for s in shards if s['path'] not in kept]
    input_root = (args.input_root or Path(config['input_root'])).resolve()
    # All inputs still to be cleaned are checksummed before creating or changing outputs (a kept part's input was
    # checked against the manifest when it was cleaned: its report records that sha256).
    hashes = {}
    resolved = {s['path']: resolve_input(input_root, s, hashes) for s in todo}
    for leftover in cleanup:
        leftover.unlink()
    output.mkdir(parents=True, exist_ok=True)
    if resumed:
        for earlier in state['attempts']:
            if earlier.get('status') == 'running':  # killed before it could say how it ended
                earlier['status'] = 'interrupted'
        failure = output / 'failure.json'
        if failure.exists():  # the earlier attempt's failure is kept in its record
            state['attempts'][-1].setdefault('failure', read_json(failure))
            failure.unlink()
    packages = {name:importlib.metadata.version(name) for name in ('pyarrow','ftfy','tree-sitter','tree-sitter-language-pack')}
    attempt = {'started': now(), 'resumed': resumed, 'kept_parts': len(kept), 'python': sys.version.split()[0],
               'packages': packages, 'status': 'running'}
    state['attempts'].append(attempt)
    write_json(output / STATE, state)
    provenance = {'sample':config.get('sample') or data.get('name'), 'manifest_sha256':config['manifest_sha256'],
                  'clean_sha256':fingerprint['clean_sha256'], 'runner_sha256':fingerprint['runner_sha256'],
                  'clean_path':config['clean'], 'config_sha256':digest(args.config), 'audit_samples':config['audit_samples'],
                  'scope':'partial (--only)' if args.only else 'full manifest',
                  'optional_f2':False, 'python':sys.version.split()[0],
                  'packages':packages,
                  'rule_scope':{rid:sorted(packs) for rid,packs in clean.SCOPE.items()}}
    print(json.dumps({'event':'start', 'selected_parts':len(shards), 'manifest_parts':len(data['shards']),
                      'sample_rows':data['total_docs'], 'clean_sha256':provenance['clean_sha256'],
                      'runner_sha256':provenance['runner_sha256'], 'scope':provenance['scope'],
                      'resumed':resumed, 'kept_parts':len(kept)}, sort_keys=True), flush=True)
    reports = []
    try:
        for shard in shards:
            if shard['path'] in kept:
                report = kept[shard['path']]
                reports.append(report)
                print(json.dumps({**{k: report[k] for k in ('part', 'status', 'input_rows', 'output_rows', 'actions', 'errors', 'seconds')},
                                  'resumed': True}, sort_keys=True), flush=True)
            else:
                reports.append(process_part(resolved[shard['path']], shard, output, config['batch_size'],
                                            audit_samples=config['audit_samples']))
    except JobError as exc:
        attempt.update(status='failed', error=str(exc), ended=now())
        write_json(output / STATE, state)
        raise
    attempt.update(status='complete', ended=now())
    provenance.update(wall_seconds=round(time.monotonic()-started,3),
                      peak_rss_mib=peak_rss_mib(), resumed_parts=len(kept), attempts=state['attempts'])
    summary = write_aggregate(output, reports, provenance, len(data['shards']), config['audit_samples'])
    write_json(output / STATE, state)
    print(json.dumps({'event':'complete', **{key:summary[key] for key in ('completed_parts','input_rows','output_rows','errors','actions','wall_seconds','peak_rss_mib')}}, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except JobError as exc:
        print('ERROR: '+str(exc), file=sys.stderr)
        raise SystemExit(1)
