"""Validate the committed G5 context-extension measurement snapshot without a GPU."""
from pathlib import Path
import csv
import hashlib
import json
import math
import ast

TEAM = Path(__file__).resolve().parents[1]
RESULTS = TEAM / 'results' / 'context_extension'


def rows(name):
    with (RESULTS / name).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def close(actual, expected, tolerance=1e-8):
    assert math.isfinite(actual) and abs(actual - expected) <= tolerance, (actual, expected)


class WithoutDocstrings(ast.NodeTransformer):
    """Compare executable function logic while allowing explanatory docstrings."""

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            node.body.pop(0)
        return node


def main():
    source = TEAM / 'notebooks' / 'context_extension.ipynb'
    notebook = json.loads(source.read_text())
    assert notebook['nbformat'] == 4
    assert notebook['metadata']['kernelspec']['name'] == 'python3'
    assert 'marimo' not in source.read_text().lower(), 'Presentation-framework reference remains'
    code_cells = [cell for cell in notebook['cells'] if cell['cell_type'] == 'code']
    receipt = json.loads((RESULTS / 'readability_rerun.json').read_text())
    assert len(code_cells) == receipt['code_cells_executed']
    source_texts = [''.join(cell['source']) for cell in code_cells]
    for index, (cell, code) in enumerate(zip(code_cells, source_texts)):
        compile(code, f'notebook-cell-{index}', 'exec')
        assert cell['execution_count'] == index + 1
        assert all(output['output_type'] != 'error' for output in cell['outputs'])
    code = '\n\n'.join(source_texts)
    assert 'mo.' not in code
    assert hashlib.sha256(code.encode()).hexdigest() == notebook['metadata']['experiment']['source_code_sha256']
    assert notebook['metadata']['experiment']['execution_status'] == 'executed_successfully'
    assert receipt['status'] == 'passed' and receipt['error_outputs'] == 0
    assert receipt['source_code_sha256'] == notebook['metadata']['experiment']['source_code_sha256']
    assert receipt['executed_notebook_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert len(receipt['checks']) == 7 and all(check['Outcome'] == 'PASS' for check in receipt['checks'])
    assert receipt['model_revision'] == '1d461723eec654e65efdc40cf49301c89c0c92f4'
    assert receipt['dataset_revision'] == 'b08601e04326c79dfdd32d625aee71d232d685c3'
    provenance = json.loads((RESULTS / 'source_provenance.json').read_text())
    preserved = provenance['current_jupyter']['preserved_function_ast_sha256']
    functions = {node.name: node for node in ast.walk(WithoutDocstrings().visit(ast.parse(code))) if isinstance(node, ast.FunctionDef)}
    for name, expected in preserved.items():
        assert hashlib.sha256(ast.dump(functions[name], include_attributes=False).encode()).hexdigest() == expected
    doc_rows = rows('document_results.csv')
    summary = rows('summary.csv')
    assert len(doc_rows) == 12 and len(summary) == 4
    assert [row['Run'] for row in summary] == list('ABCD')
    expected_context = dict(A=2048, B=4096, C=4096, D=2048)
    means = {}
    documents = None
    for row in summary:
        arm = row['Run']
        selected = [r for r in doc_rows if r['Run'] == arm]
        assert len(selected) == 3
        titles = {r['Document'] for r in selected}
        documents = documents or titles
        assert titles == documents and len(documents) == 3
        assert all(int(r['Context']) == expected_context[arm] for r in selected)
        assert all(int(r['Scored tokens']) == 512 for r in selected)
        mean = math.fsum(float(r['NLL']) for r in selected) / len(selected)
        close(float(row['NLL']), mean)
        close(float(row['Perplexity']), math.exp(mean), 1e-6)
        assert int(row['Context']) == expected_context[arm]
        assert int(row['scored_tokens']) == 1536
        means[arm] = mean
    manifest = json.loads((RESULTS / 'manifest.json').read_text())
    close(means['C'] - means['B'], manifest['long_mean_nll_change'])
    close(means['D'] - means['A'], manifest['short_mean_nll_change'])
    close(means['C'] - means['A'], manifest['long_vs_native_nll_change'])
    assert means['C'] < means['B'] and means['C'] > means['A']
    assert len(manifest['checks']) == 7
    assert all(check['Outcome'] == 'PASS' for check in manifest['checks'])
    hashes = json.loads((RESULTS / 'input_hashes.json').read_text())
    assert len(hashes) == 3 and {r['title'] for r in hashes} == documents
    assert all(len(r['tokens_sha256']) == 64 for r in hashes)
    assert {row['title']: row['tokens_sha256'] for row in receipt['input_hashes']} == {
        row['title']: row['tokens_sha256'] for row in hashes
    }
    rerun_means = {}
    for row in receipt['summary']:
        selected = [item for item in receipt['document_results'] if item['Run'] == row['Run']]
        assert len(selected) == 3 and {item['Document'] for item in selected} == documents
        assert all(int(item['Scored tokens']) == 512 for item in selected)
        mean = math.fsum(float(item['NLL']) for item in selected) / 3
        close(float(row['NLL']), mean)
        close(float(row['Perplexity']), math.exp(mean), 1e-6)
        assert int(row['scored_tokens']) == 1536
        rerun_means[row['Run']] = mean
    close(rerun_means['C'] - rerun_means['D'], receipt['extra_prefix_nll_change'])
    close(max(abs(rerun_means[arm] - means[arm]) for arm in means), receipt['max_mean_nll_drift_from_historical_pilot'])
    approved = json.loads((RESULTS / 'approved_manifest.json').read_text())
    runner = TEAM / 'harness' / 'context_extension_check.py'
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == approved['source_sha256']
    assert approved['attention_backend'] == 'eager' and approved['full_vocabulary_head']
    assert approved['input_sha256'] == '21c6e4b2df8dae9d69e254f4a00fc934d2a3c70f0675065a03724299d94312bb'
    assert all(approved['checks'].values())
    actual_docs = rows('approved_document_results.csv')
    actual_summary = rows('approved_summary.csv')
    assert len(actual_docs) == 12 and len(actual_summary) == 4
    approved_means = {}
    for row in actual_summary:
        selected = [r for r in actual_docs if r['Run'] == row['Run']]
        assert len(selected) == 3 and all(int(r['scored_tokens']) == 512 for r in selected)
        assert {r['Document'] for r in selected} == {r['id'] for r in approved['documents']}
        assert all(int(r['Context']) == expected_context[row['Run']] for r in selected)
        mean = math.fsum(float(r['NLL']) for r in selected) / 3
        close(float(row['NLL']), mean)
        close(float(row['Perplexity']), math.exp(mean), 1e-6)
        assert int(row['scored_tokens']) == 1536
        approved_means[row['Run']] = mean
    assert approved_means['C'] < approved_means['B']
    assert approved_means['C'] > approved_means['A'] and approved_means['C'] > approved_means['D']
    recorded = json.loads((RESULTS / 'file_manifest.json').read_text())
    for relative_path, expected in recorded.items():
        path = TEAM / relative_path
        assert path.is_file(), relative_path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative_path
    print('PASS: standard Jupyter structure, syntax, code hash, preserved scoring/selection functions;')
    print('      fresh GPU receipt, execution counts, no error outputs, matched inputs and rerun arithmetic;')
    print('      executed eager-runner hash;')
    print('      both studies: document rows, equal-target-count aggregates, NLL/perplexity arithmetic;')
    print('      reported conclusions, corpus hash, check receipts, fixture hashes and file integrity.')
    print('This verifies the saved execution evidence; it does not launch another GPU job or imply PR acceptance.')


if __name__ == '__main__':
    main()
