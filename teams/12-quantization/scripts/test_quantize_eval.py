#!/usr/bin/env python3
"""Tests for the checkpoint path of quantize_eval.py that need no llama.cpp:  python test_quantize_eval.py

The whole flow (export, convert, quantize, serve, score) is tested by running it on make_random_checkpoint.py output.
"""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import quantize_eval as q  # noqa: E402


def tokenizer(path: Path, n: int):
    path.write_text(json.dumps({'model': {'vocab': {f't{i}': i for i in range(n - 1)}},
                                'added_tokens': [{'id': n - 1, 'content': '<|endoftext|>'}]}), encoding='utf-8')
    return path


class CheckpointPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def hf_folder(self, vocab):
        d = self.dir / 'model'; d.mkdir()
        (d / 'config.json').write_text(json.dumps({'vocab_size': vocab}), encoding='utf-8')
        (d / 'model.safetensors').write_bytes(b'weights')
        (d / 'tokenizer.json').write_text('{"old": true}', encoding='utf-8')
        (d / 'vocab.json').write_text('{}', encoding='utf-8')
        return d

    def test_stage_replaces_the_tokenizer_and_keeps_the_weights(self):
        tok = tokenizer(self.dir / 'tokenizer.json', 10)
        out = q.stage_tokenizer(self.hf_folder(10), tok, self.dir / 'staged', '<|begin_of_text|>', '<|endoftext|>')
        self.assertEqual((out / 'tokenizer.json').read_bytes(), tok.read_bytes())
        self.assertEqual((out / 'model.safetensors').read_bytes(), b'weights')
        self.assertFalse((out / 'vocab.json').exists())      # the model's own tokenizer files are left out
        self.assertEqual(json.loads((out / 'tokenizer_config.json').read_text())['eos_token'], '<|endoftext|>')

    def test_stage_refuses_a_tokenizer_bigger_than_the_table(self):
        with self.assertRaises(SystemExit) as e:
            q.stage_tokenizer(self.hf_folder(9), tokenizer(self.dir / 'tokenizer.json', 10), self.dir / 'staged', 'b', 'e')
        self.assertIn('refusing', str(e.exception))

    def test_weights_file_of_a_checkpoint(self):
        run = self.dir / 'run'; run.mkdir()
        (run / 'checkpoint.pt').write_bytes(b'x')
        self.assertEqual(q.checkpoint_weights(run), run / 'checkpoint.pt')
        self.assertEqual(q.checkpoint_weights(run / 'checkpoint.pt'), run / 'checkpoint.pt')
        with self.assertRaises(SystemExit):
            q.checkpoint_weights(self.dir)

    def test_wrong_tokenizer_hash_stops_before_any_work(self):
        tok = tokenizer(self.dir / 'tokenizer.json', 10)
        r = subprocess.run([sys.executable, str(HERE / 'quantize_eval.py'), '--checkpoint', str(self.dir), '--tokenizer', str(tok),
                            '--work', str(self.dir / 'work'), '--llama-bin', str(self.dir / 'no-such-dir')],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn('refusing', r.stderr)
        self.assertIn(q.FROZEN_TOKENIZER_SHA256, r.stderr)   # the default is the frozen tokenizer
        self.assertFalse((self.dir / 'work' / 'hf').exists())


if __name__ == '__main__':
    unittest.main(verbosity=1)
