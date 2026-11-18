#!/usr/bin/env python3
"""Test A3 of docs/unsupported_parts.md, section 12: does llama.cpp compute what G5's model computes?

    python check_gguf_logits.py --checkpoint <run dir | checkpoint.pt | model.safetensors> --gguf <bf16.gguf> \\
        --llama-server <llama-server binary> [--spec manifest.json] [--prompts 16] [--out a3.json]

Serves the bf16 GGUF with llama-server (CPU), sends N prompts of random token ids, and compares the log-probabilities
of llama.cpp's top-5 next tokens with G5's `LanguageModel` (CPU) on the same ids. G5's model is given the weights
the GGUF holds (bf16-rounded matrices, the folded embedding table), so only the runtime's arithmetic differs. Pass:
the same top-1 token on every prompt and every difference below --tol. Exit 0 pass, 1 fail.

How to read it. llama.cpp keeps keys and values in fp16 and uses its own kernels, so the two never agree exactly.
On random test models (make_random_checkpoint.py, 16 prompts) a correct export gave 0.003 to 0.03, with one outlier
of 0.18 and one changed top-1 at --std 0.2; an export without the q/k reordering gave up to 3.5 and 11 changed
top-1 of 16 at --std 0.3, but looked the same as a correct one at --std 0.05, where attention is nearly uniform.
So a clear FAIL is a wiring error, and a near miss needs a look. The limit 0.05 is not calibrated on a trained
checkpoint yet: no such checkpoint existed when this was written.

export_hf.py --verify is test A1 (the export against G5); this is the same question for the runtime. Needs torch.
"""
from __future__ import annotations

import argparse, json, socket, subprocess, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_hf  # noqa: E402


def check(checkpoint: Path, gguf: Path, server: Path, spec_path: Path | None = None, prompts: int = 16,
          length: int = 48, tol: float = 0.05, seed: int = 0) -> dict:
    import torch
    sys.path.insert(0, str(export_hf.HARNESS))
    from week2.model import LanguageModel
    weights, found = export_hf.find_checkpoint(Path(checkpoint))
    state = export_hf.load_state(weights)
    spec = export_hf.resolve_spec(state, export_hf.load_spec(spec_path or found))
    ref = LanguageModel(spec, state['embedding.rows'].numpy(), state['embedding.lengths'].numpy()).eval()
    # The reference uses the weights the GGUF holds: every matrix rounded to bf16, and the folded embedding table
    # in place of KE2. What is left is the runtime's own arithmetic, so a small tolerance is a real test.
    bf16 = lambda t: t.to(torch.bfloat16).float() if t.is_floating_point() and t.ndim > 1 else t
    ref.load_state_dict({k: bf16(v) for k, v in state.items()})
    table = bf16(export_hf.fold_ke2(state, spec['n_embd']))
    ref.embedding.forward = lambda ids: table[ids]
    length = min(length, spec['block_size'] or length)
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([str(server), '-m', str(gguf), '--port', str(port), '-ngl', '0', '-c', str(2 * length),
                            '--no-webui', '-np', '1'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f'http://127.0.0.1:{port}'
    try:
        for _ in range(600):
            try:
                if json.load(urllib.request.urlopen(base + '/health', timeout=2)).get('status') == 'ok': break
            except Exception: pass
            if srv.poll() is not None: sys.exit(f'llama-server exited while loading {gguf}')
            time.sleep(0.5)
        gen = torch.Generator().manual_seed(seed)
        worst, same, done, skipped = 0.0, 0, 0, 0
        while done < prompts and skipped < 10 * prompts:
            ids = torch.randint(0, spec['vocab_size'], (1, length), generator=gen)
            body = dict(prompt=ids[0].tolist(), n_predict=1, n_probs=5, temperature=0, cache_prompt=False)
            req = urllib.request.Request(base + '/completion', json.dumps(body).encode(), {'Content-Type': 'application/json'})
            probs = json.load(urllib.request.urlopen(req, timeout=600)).get('completion_probabilities')
            if not probs:  # the server gives no probabilities when the token is part of a UTF-8 character
                skipped += 1
                continue
            top = probs[0]['top_logprobs']
            with torch.no_grad():
                logp = ref(ids, torch.ones_like(ids, dtype=torch.bool))[0, -1].float().log_softmax(-1)
            same += top[0]['id'] == int(logp.argmax())
            worst = max(worst, max(abs(t['logprob'] - logp[t['id']].item()) for t in top))
            done += 1
        if done < prompts: sys.exit(f'llama-server returned probabilities for only {done} of {done + skipped} prompts')
    finally:
        srv.terminate()
        try: srv.wait(30)
        except subprocess.TimeoutExpired: srv.kill()
    return dict(test='A3', prompts=prompts, skipped=skipped, tokens_per_prompt=length, same_top1=same, max_abs_logprob_diff=worst,
                tolerance=tol, passed=bool(same == prompts and worst <= tol))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--checkpoint', type=Path, required=True)
    ap.add_argument('--gguf', type=Path, required=True, help='the bf16 GGUF made from the checkpoint')
    ap.add_argument('--llama-server', type=Path, required=True)
    ap.add_argument('--spec', type=Path)
    ap.add_argument('--prompts', type=int, default=16)
    ap.add_argument('--tol', type=float, default=0.05)
    ap.add_argument('--out', type=Path, help='write the result as JSON')
    a = ap.parse_args()
    r = check(a.checkpoint, a.gguf, a.llama_server, a.spec, a.prompts, tol=a.tol)
    print(f'A3: same top-1 on {r["same_top1"]}/{r["prompts"]} prompts, max log-probability difference '
          f'{r["max_abs_logprob_diff"]:.4f} (limit {a.tol:g}): {"PASS" if r["passed"] else "FAIL"}', flush=True)
    if a.out:
        a.out.write_text(json.dumps(r, indent=2) + '\n', encoding='utf-8')
    sys.exit(0 if r['passed'] else 1)


if __name__ == '__main__':
    main()
