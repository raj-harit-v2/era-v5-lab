import hashlib, json, math, sys, tempfile, unittest
from pathlib import Path
from contextlib import nullcontext
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'harness'))
from week2.scoring import INDIC, group_metrics, source_slices, compare_arms
from week2.data import DocumentWindows
from week2.evaluation import evaluate
from test_week2_bpb import ByteFixture, UniformModel


class SliceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.docs = [{'id': str(i), 'text': 'hello ' * (i + 1)} for i in range(15)]
        self.rows = [
            {
                'id': d['id'],
                'slice': name,
                'text_sha256': hashlib.sha256(d['text'].encode()).hexdigest(),
            }
            for d, name in zip(self.docs, ['en', 'code', *INDIC, 'math', 'sci'])
        ]
        self.text = self.root / 'heldout.jsonl'
        self.sources = self.root / 'sources.jsonl'
        self.text.write_text(''.join(json.dumps(d) + '\n' for d in self.docs))
        self.save()

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        self.sources.write_text(''.join(json.dumps(d) + '\n' for d in self.rows))

    def test_uniform_all_slices_and_group_score(self):
        ds = DocumentWindows(self.text, ByteFixture(), 7, True, self.sources)
        r = evaluate(UniformModel(), ds, 4, 'cpu', nullcontext)
        self.assertAlmostEqual(r['val/three_group_bpb'], math.log2(258), places=5)
        self.assertEqual(
            sum(
                r[f'val/slices/{k}/utf8_bytes']
                for k in ['en', 'code', *INDIC, 'math', 'sci']
            ),
            ds.raw_bytes,
        )
        self.assertEqual(r, evaluate(UniformModel(), ds, 1, 'cpu', nullcontext))

    def test_source_order_mismatch(self):
        self.rows.reverse()
        self.save()
        with self.assertRaisesRegex(ValueError, 'order'):
            source_slices(self.sources, self.docs)

    def test_text_mutation_rejected(self):
        self.docs[0]['text'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'text hash'):
            source_slices(self.sources, self.docs)

    def test_missing_source_rejected(self):
        self.rows.pop()
        self.save()
        with self.assertRaisesRegex(ValueError, 'count'):
            source_slices(self.sources, self.docs)

    def test_unknown_slice_rejected(self):
        self.rows[0]['slice'] = 'unknown'
        self.save()
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            source_slices(self.sources, self.docs)

    def test_macro_mean_not_pooled_or_math_science(self):
        d = {k: 3.0 for k in INDIC}
        d.update(en=1.0, code=2.0, math=100.0, sci=200.0)
        self.assertEqual(group_metrics(d)['val/three_group_bpb'], 2.0)

    def test_missing_indic_slice_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Missing'):
            group_metrics({'en': 1.0, 'code': 2.0})


class WinnerTests(unittest.TestCase):
    def runs(self, score, code=2.0, indic=2.0):
        return [
            dict(
                seed=s,
                eligible_for_quality_comparison=True,
                **{
                    'val/three_group_bpb': score + o,
                    'val/groups/code_bpb': code + o,
                    'val/groups/indic_mean_bpb': indic + o,
                },
            )
            for s, o in zip([1234, 1235, 1236], [-0.01, 0, 0.01])
        ]

    def test_clear_improvement_wins(self):
        self.assertTrue(compare_arms(self.runs(1.5), self.runs(2.0))['wins'])

    def test_seed_noise_blocks(self):
        # A lower mean alone does not clear the measured seed spread.
        self.assertFalse(compare_arms(self.runs(1.99), self.runs(2.0))['wins'])

    def test_code_regression_blocks(self):
        self.assertFalse(compare_arms(self.runs(1.5, code=2.2), self.runs(2.0))['wins'])

    def test_indic_regression_blocks(self):
        self.assertFalse(
            compare_arms(self.runs(1.5, indic=2.2), self.runs(2.0))['wins']
        )

    def test_missing_seed_rejected(self):
        with self.assertRaisesRegex(ValueError, 'seeds'):
            compare_arms(self.runs(1.5)[:2], self.runs(2.0))

    def test_smoke_cannot_win(self):
        r = self.runs(1.5)
        r[0]['eligible_for_quality_comparison'] = False
        with self.assertRaisesRegex(ValueError, 'smoke'):
            compare_arms(r, self.runs(2.0))


if __name__ == '__main__':
    unittest.main()
