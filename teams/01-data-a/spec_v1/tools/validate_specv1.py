"""Validate consolidated spec with repository rule execution and the repository minimum-one harm policy.

Usage: python validate_specv1.py --packs /path/to/packs --gold /path/to/gold
Writes IDs, counts and digests; never source text. Source medicines are not modified.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from fractions import Fraction
import pyarrow.parquet as pq

SPEC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPEC.parent / 'tools'))
import harm_test as ht


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(result, n):
    changed, dropped, errors = result
    return {'n': n, 'changed': changed, 'dropped': dropped, 'errors': errors,
            'limit_documents': ht.allowed_documents(n, Fraction(1)) if n else 0,
            'result': 'ERROR' if errors else 'NOT TESTABLE' if not n else
            'PASS' if ht.harm_percent(len(changed), len(dropped), n, Fraction(1))[1] else 'FAIL'}


def add_card_evidence(src, report, rules, all_docs):
    """Attach fresh per-card harm and exact original excerpts without exposing private spans."""
    for i, (rid, fn) in enumerate(rules, 1):
        start = src.index(f"## Medicine {i} —")
        next_start = src.find(f"## Medicine {i + 1} —", start)
        end = next_start if next_start != -1 else len(src)
        card = src[start:end]
        # Replace our generated block on subsequent runs.
        card = re.sub(r"(?s)<!-- CARD EVIDENCE -->.*?<!-- END CARD EVIDENCE -->\n*", "", card)
        measured = []
        examples = []
        code = rid.split("-")[1]
        for pack, data in report['packs'].items():
            if rid not in data['independent_gold_rules']:
                continue
            result = data['independent_gold_rules'][rid]
            measured.append(f"{pack}: {len(result['changed'])} changed / {len(result['dropped'])} dropped "
                            f"of {result['n']} ({result['result']})")
            if code in {'F1', 'E3'}:
                continue  # Private details and credentials never appear as public evidence.
            for doc_id, doc in all_docs[pack].items():
                if len(examples) >= 3:
                    break
                try:
                    verdict, new = ht._invoke(fn, doc, 5)
                except Exception:
                    continue  # The separate test report records errors; this is example selection only.
                if verdict not in {'fix', 'drop'}:
                    continue
                offset = len(os.path.commonprefix([doc['text'], new])) if verdict == 'fix' else 0
                lo = max(0, offset - 8)
                excerpt = doc['text'][lo:offset + 24] if verdict == 'fix' else doc['text'][:64]
                # Withhold any span that might expose contact details or a long identifier.
                if '@' in excerpt or re.search(r"(?:\d[ .()+-]*){7,}", excerpt):
                    continue
                literal = json.dumps(excerpt, ensure_ascii=True).replace('`', r'\u0060')
                examples.append(f"- `{doc_id}` ({pack}), original offset {lo}: `{literal}` ({verdict}).")
        evidence = "<!-- CARD EVIDENCE -->\n**Current gold harm:** " + '; '.join(measured) + '.\n\n'
        if examples:
            evidence += ("**Exact source characters:** JSON string literals below decode to verbatim original "
                         "characters. Fix excerpts surround the first edit; drop excerpts identify the affected "
                         "source document and do not establish which substring caused the drop. These are "
                         "execution examples, not additional independently adjudicated labels.\n\n" +
                         '\n'.join(examples) + '\n')
        if len(examples) < 3:
            evidence += (f"\n**Example gap:** {len(examples)}/3 publishable execution excerpts; "
                         "private/credential spans are withheld and fewer than three affected records may exist. "
                         "Complete reviewed evidence before freeze.\n")
        evidence += '<!-- END CARD EVIDENCE -->\n\n'
        marker = re.search(r"(?m)^2\. \*\*Medicine:", card)
        assert marker, rid
        card = card[:marker.start()] + evidence + card[marker.start():]
        src = src[:start] + card + src[end:]
    return src


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--packs', required=True, type=Path)
    ap.add_argument('--gold', required=True, type=Path)
    args = ap.parse_args()
    sheet = SPEC / 'sheets' / 'specv1.md'
    ns, code_digest = ht.load_rules(sheet)
    rules = list(ns['RULES_BY_ID'].items())
    packs = sorted({p for _, fn in rules for p in fn.__globals__['SPEC_PACKS']})
    report = {'rules_code_sha256': code_digest, 'sources': {
        p.name: digest(p) for p in (SPEC / 'sheets').glob('medicine_*.md')
        if p.name in {'medicine_code.md', 'medicine_english.md', 'medicine_math.md', 'medicine_sci.md'}},
        'execution': 'harm_test.load_rules/run_rule/run_sheet; repository 1% minimum-one comparison; 5s timeout per rule/document',
        'harm_runner_sha256': digest(Path(ht.__file__)),
        'harm_policy': {'limit_percent': 1, 'allowed_documents': 'max(1, floor(n / 100))'},
        'packs': {}}
    lines = ['Fresh local execution using the repository loader, mutation checks, timeouts and pipeline runner; verdicts use the repository policy: at most `max(1, floor(gold_count / 100))` changed-or-dropped gold documents per rule and combined pipeline, per pack. Reports contain IDs and digests only. `pack_id` is supplied from each validated pack filename when absent in Parquet.\n',
             '| Pack | Gold n | Gold changed / dropped | Result | Full pack fixed / dropped | Errors (gold / pack) |',
             '|---|---:|---:|---|---:|---:|']
    all_docs = {}
    for pack in packs:
        path = args.packs / (pack + '.parquet')
        gold = args.gold / (pack + '_gold.csv')
        ids = ht.read_gold(gold)
        # The repository validates metadata and gold membership before provenance injection.
        gold_docs = ht.read_pack_docs(path, ids)
        rows = pq.read_table(path).to_pylist()
        docs = {}
        for row in rows:
            if not isinstance(row.get('doc_id'), str) or not isinstance(row.get('text'), str):
                raise ValueError('invalid doc_id/text in ' + pack)
            if row['doc_id'] in docs:
                raise ValueError('duplicate doc_id in ' + pack)
            if row.get('pack_id', pack) != pack:
                raise ValueError('pack provenance mismatch')
            row['pack_id'] = pack
            docs[row['doc_id']] = row
        all_docs[pack] = docs
        for doc in gold_docs.values():
            doc['pack_id'] = pack
        applicable = [(rid, fn) for rid, fn in rules if pack in fn.__globals__['SPEC_PACKS']]
        single = {rid: summarize(ht.run_rule(fn, gold_docs, 5), len(ids)) for rid, fn in applicable}
        combined = summarize(ht.run_sheet(rules, gold_docs, 5), len(ids))
        full = summarize(ht.run_sheet(rules, docs, 5), len(docs))
        # A full-pack rate is impact, not gold harm acceptance.
        full.pop('result')
        outside = [(rid, fn) for rid, fn in rules if pack not in fn.__globals__['SPEC_PACKS']]
        guard_result = ht.run_sheet(outside, docs, 5)
        if any(guard_result):
            raise ValueError('out-of-pack rule changed, dropped or errored on ' + pack)
        report['packs'][pack] = {'pack_sha256': digest(path), 'gold_sha256': digest(gold),
            'gold_path': str(gold.resolve()), 'pack_path': str(path.resolve()),
            'independent_gold_rules': single, 'combined_gold': combined, 'combined_pack': full,
            'out_of_pack_guard': 'PASS'}
        lines.append(f'| {pack} | {len(ids)} | {len(combined["changed"])} / {len(combined["dropped"])} | {combined["result"]} | {len(full["changed"])} / {len(full["dropped"])} | {len(combined["errors"])} / {len(full["errors"])} |')
        print(pack, combined['result'], 'gold', len(combined['changed']), len(combined['dropped']), 'pack errors', len(full['errors']), flush=True)
    failures = [(p, rid, r['result']) for p, v in report['packs'].items()
                for rid, r in v['independent_gold_rules'].items() if r['result'] != 'PASS']
    lines += ['\nIndependent gold rules failing the repository minimum-one limit: ' +
              (', '.join(f'`{p}/{rid}` ({verdict})' for p, rid, verdict in failures) or 'none') + '.',
              '\nAll other independently tested in-scope rules passed. Every out-of-pack guard passed on all source documents. Results apply to the snapshots recorded in [results/cleaner/specv1_validation.json](../results/cleaner/specv1_validation.json). A failed candidate is retained for review and blocks release; it is not silently disabled to improve harm numbers.',
              '\nReproduce from the repository root (Python requires `pyarrow` and `ftfy`):\n\n```bash\npython3 teams/01-data-a/spec_v1/tools/validate_specv1.py \\\n  --packs /home/vijay/projects/erav5/erav5-lab-other-files/packs \\\n  --gold /home/vijay/projects/erav5/era-v5-lab-second-clone/teams/01-data-a/gold\n```']
    src = sheet.read_text()
    start = src.index('<!-- VALIDATION -->')
    end = src.index('\n## Medicine 1 ', start)
    src = src[:start] + '<!-- VALIDATION -->\n\n' + '\n'.join(lines) + '\n\n' + src[end:]
    src = add_card_evidence(src, report, rules, all_docs)
    sheet.write_text(src)
    report['spec_sha256'] = digest(sheet)
    out = SPEC / 'results/cleaner/specv1_validation.json'
    out.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
