#!/usr/bin/env python3
"""Tests for export_hf.py on small random G5 models (CPU, a few seconds):  python test_export_hf.py

Needs torch, transformers, safetensors and numpy. The models are random; the tests check the export, not a score.
"""
import contextlib, io, json, sys, tempfile, unittest
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export_hf  # noqa: E402

sys.path.insert(0, str(export_hf.HARNESS))
from week2.model import LanguageModel  # noqa: E402


def spec(**over):
    m = dict(vocab_size=300, n_embd=32, n_layer=2, n_head=4, n_kv_head=2, block_size=24, rope_theta=10000.0,
             norm_eps=1e-5, mtp=False, moe=dict(num_experts=4, num_shared=1, top_k=2, ffn_hidden=48, bias=False))
    moe = over.pop('moe', {})
    m.update(over)
    m['moe'].update(moe)
    return m


def random_model(m, seed=0):
    """A LanguageModel whose every weight is random (norm weights too, or a swapped norm would go unseen)."""
    rng = np.random.default_rng(seed)
    rows = rng.integers(0, 256, (m['vocab_size'], 8), dtype=np.uint8)
    lengths = rng.integers(1, 9, m['vocab_size'], dtype=np.int16)
    torch.manual_seed(seed)
    model = LanguageModel(m, rows, lengths)
    with torch.no_grad():
        for name, p in model.named_parameters():
            if name.endswith(('n1.weight', 'n2.weight', 'norm.weight')):
                p.uniform_(0.5, 1.5)
            elif 'sink' not in name:
                p.normal_(std=0.3)
    return model


def save_run(folder: Path, m, model, as_safetensors=False):
    folder.mkdir(parents=True, exist_ok=True)
    if as_safetensors:
        from safetensors.torch import save_file
        save_file({k: v.contiguous() for k, v in model.state_dict().items()}, str(folder / 'model.safetensors'))
    else:
        torch.save({'model': model.state_dict(), 'step': 3}, folder / 'checkpoint.pt')
    (folder / 'manifest.json').write_text(json.dumps({'config': {'model': m}}), encoding='utf-8')
    return folder


def quiet_export(*args, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return export_hf.export(*args, **kw)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, m, **kw):
        run = save_run(self.dir / 'run', m, random_model(m), **kw)
        report = quiet_export(run, self.dir / 'hf', dtype='fp32', n_verify=4, tol=1e-4)
        self.assertTrue(report['verify']['passed'], report['verify'])
        return report

    def test_default_block_matches_g5(self):
        report = self.check(spec())
        self.assertEqual(report['verify']['same_top1'], report['verify']['positions'])
        cfg = json.loads((self.dir / 'hf/config.json').read_text())
        self.assertEqual(cfg['architectures'], ['GraniteMoeSharedForCausalLM'])
        self.assertAlmostEqual(cfg['attention_multiplier'], 8 ** -0.5)
        self.assertEqual((cfg['intermediate_size'], cfg['shared_intermediate_size']), (48, 48))

    def test_several_shared_experts_merge(self):
        self.check(spec(moe=dict(num_shared=3)))
        self.assertEqual(json.loads((self.dir / 'hf/config.json').read_text())['shared_intermediate_size'], 144)

    def test_no_shared_expert(self):
        self.check(spec(moe=dict(num_shared=0)))

    def test_mqa_and_mtp_head_dropped(self):
        report = self.check(spec(n_kv_head=1, mtp=True))
        self.assertIn('mtp_head.weight', report['dropped'])

    def test_safetensors_checkpoint(self):
        self.check(spec(), as_safetensors=True)

    def test_reloads_from_disk_in_bf16(self):
        from transformers import AutoModelForCausalLM
        m = spec()
        model = random_model(m)
        quiet_export(save_run(self.dir / 'run', m, model), self.dir / 'hf')
        hf = AutoModelForCausalLM.from_pretrained(self.dir / 'hf', dtype=torch.float32).eval()
        ids = torch.randint(0, 300, (1, 16), generator=torch.Generator().manual_seed(1))
        with torch.no_grad():
            diff = (model(ids, torch.ones_like(ids, dtype=torch.bool)) - hf(input_ids=ids).logits).abs().max().item()
        self.assertLess(diff, 0.5)      # bf16 rounding of random 0.3-std weights, not a wiring error
        self.assertGreater(diff, 0.0)

    def test_a_wrong_rewrite_is_caught(self):
        """Without the q/k row reordering the logits differ, so A1 is a real test of 9.4."""
        m = spec()
        run = save_run(self.dir / 'run', m, random_model(m))
        keep = export_hf.to_halves
        export_hf.to_halves = lambda w, n: w
        try:
            with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
                export_hf.export(run, self.dir / 'hf', dtype='fp32', n_verify=4, tol=1e-4)
        finally:
            export_hf.to_halves = keep
        self.assertFalse((self.dir / 'hf').exists())

    def refused(self, m, text, spec_file=None, edit=None):
        model = random_model(m)
        run = save_run(self.dir / 'run', m, model)
        if edit:
            state = model.state_dict()
            edit(state)
            torch.save({'model': state}, run / 'checkpoint.pt')
        with self.assertRaises(SystemExit) as e:
            quiet_export(run, self.dir / 'hf', spec_path=spec_file)
        self.assertIn(text, str(e.exception))
        self.assertFalse((self.dir / 'hf').exists())

    def test_refuses_attention_gate(self):
        self.refused(spec(attn_gate=True, attn_gate_input='normalized', attn_gate_bias=False, attn_gate_init='zero'), 'attn-4')

    def test_refuses_partial_rope(self):
        self.refused(spec(rotary_fraction=0.5), 'attn-3')

    def test_refuses_window_layers(self):
        self.refused(spec(attn_pattern=['L', 'G'], attn_window=8), 'attn-2')

    def test_refuses_spec_that_contradicts_the_tensors(self):
        wrong = self.dir / 'wrong.json'
        wrong.write_text(json.dumps(dict(spec(), n_layer=5)), encoding='utf-8')
        self.refused(spec(), 'n_layer = 5', spec_file=wrong)

    def test_refuses_missing_spec(self):
        empty = self.dir / 'empty.json'
        empty.write_text('{}', encoding='utf-8')
        self.refused(spec(), 'n_head', spec_file=empty)

    def test_refuses_unknown_tensor(self):
        self.refused(spec(), 'unknown tensors', edit=lambda s: s.update({'extra.weight': torch.zeros(1)}))


if __name__ == '__main__':
    unittest.main(verbosity=1)
