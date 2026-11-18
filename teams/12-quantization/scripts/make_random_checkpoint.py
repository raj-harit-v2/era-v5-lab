#!/usr/bin/env python3
"""A small random G5 checkpoint, to test the quantize flow before a trained checkpoint exists.

    python make_random_checkpoint.py --tokenizer tokenizer.json --out <run dir> [--d-model 64 --n-layer 2 ...]

Writes <run dir>/checkpoint.pt and manifest.json in the layout of teams/05-architecture/harness/train_week2.py, so
quantize_eval.py --checkpoint <run dir> and export_hf.py read it like a real run. The weights are random: the
scores of such a model mean nothing; only the flow is tested. The KE2 byte table is built from tokenizer.json
(each token's bytes, cut at --pos-dim), not from G4's file. Needs torch, numpy and G5's harness in this repo.
"""
import argparse, json, sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'teams/05-architecture/harness'))
from week2.model import LanguageModel  # noqa: E402


def byte_table(tokenizer_json: Path, pos_dim: int):
    """rows [V, P] uint8 and lengths [V]: the UTF-8 bytes of every token (byte-level BPE alphabet as in GPT-2)."""
    tok = json.loads(tokenizer_json.read_text(encoding='utf-8'))
    alphabet = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    chars = alphabet.copy()
    for b in range(256):
        if b not in alphabet:
            chars.append(256 + len(alphabet) - 188)
            alphabet.append(b)
    inverse = {chr(c): b for b, c in zip(alphabet, chars)}
    added = {a['id']: a['content'].encode('utf-8') for a in tok.get('added_tokens', [])}
    pieces = {i: p for p, i in tok['model']['vocab'].items()}
    n = 1 + max(max(pieces), max(added, default=0))
    rows, lengths = np.zeros((n, pos_dim), dtype=np.uint8), np.ones(n, dtype=np.int16)
    for i in range(n):
        raw = added[i] if i in added else bytes(inverse[c] for c in pieces.get(i, '!'))
        raw = raw[:pos_dim] or b'!'
        rows[i, :len(raw)] = np.frombuffer(raw, dtype=np.uint8)
        lengths[i] = len(raw)
    return rows, lengths


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tokenizer', type=Path, required=True, help='tokenizer.json: sets the vocabulary and the byte table')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--d-model', type=int, default=64)
    ap.add_argument('--n-layer', type=int, default=2)
    ap.add_argument('--n-head', type=int, default=4)
    ap.add_argument('--n-kv-head', type=int, default=2)
    ap.add_argument('--d-ff', type=int, default=128, help='width of one expert')
    ap.add_argument('--n-expert', type=int, default=16)
    ap.add_argument('--n-shared', type=int, default=1)
    ap.add_argument('--top-k', type=int, default=2)
    ap.add_argument('--seq-len', type=int, default=1024)
    ap.add_argument('--pos-dim', type=int, default=32)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--std', type=float, default=0.1, help='every matrix is drawn from N(0, std). With the default '
                    'initialisation the attention is close to uniform, and a wrong RoPE layout would change nothing')
    a = ap.parse_args()
    rows, lengths = byte_table(a.tokenizer, a.pos_dim)
    model = dict(vocab_size=len(rows), n_embd=a.d_model, n_layer=a.n_layer, n_head=a.n_head, n_kv_head=a.n_kv_head,
                 block_size=a.seq_len, ke_max_pos=a.pos_dim, rope_theta=10000.0, rotary_fraction=1.0, norm_eps=1e-5,
                 mtp=False, moe=dict(num_experts=a.n_expert, num_shared=a.n_shared, top_k=a.top_k, ffn_hidden=a.d_ff, bias=False))
    torch.manual_seed(a.seed)
    net = LanguageModel(model, rows, lengths)
    with torch.no_grad():
        for key, p in net.named_parameters():
            p.uniform_(0.5, 1.5) if p.ndim == 1 else p.normal_(std=a.std)   # ndim 1: the norm weights
    a.out.mkdir(parents=True, exist_ok=True)
    torch.save({'model': net.state_dict(), 'step': 0}, a.out / 'checkpoint.pt')
    (a.out / 'manifest.json').write_text(json.dumps(
        {'config': {'model': model}, 'parameters': net.parameter_count(), 'status': 'RANDOM_WEIGHTS_FLOW_TEST_ONLY'},
        indent=2) + '\n', encoding='utf-8')
    print(f'{a.out}: random G5 model, {net.parameter_count():,} parameters, vocabulary {len(rows):,}')


if __name__ == '__main__':
    main()
