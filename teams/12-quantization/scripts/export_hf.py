#!/usr/bin/env python3
"""G12 week 3: G5 checkpoint -> Hugging Face `GraniteMoeSharedForCausalLM` folder (docs/unsupported_parts.md, sections 8 and 9).

    python teams/12-quantization/scripts/export_hf.py --checkpoint <run dir | checkpoint.pt | model.safetensors> \\
        --out <hf dir> [--spec <manifest.json | spec.json | spec.yaml>] [--tokenizer tokenizer.json] [--verify 64]

The input is a checkpoint of G5's `LanguageModel` (teams/05-architecture/harness/week2/model.py):
  - a train_week2.py run folder (checkpoint.pt + manifest.json): nothing else is needed;
  - a checkpoint.pt ({"model": state_dict, ...}) or a bare state_dict in .pt / .safetensors (Team 07's
    export_safetensors), with --spec: a file that holds the model settings, either the `model` mapping itself or
    a mapping with it under `model` or `config.model` (manifest.json has it there).

The export is exact, not an approximation. Four rewrites:
  9.1  KE2 + projection -> one `V x d_model` table, built by running the harness module itself over every id
  9.3  `mtp_head` is dropped (next-token generation does not use it)
  9.4  q/k rows reordered per head from adjacent pairs to split halves (the RoPE layout of HF and vLLM; llama.cpp's
       converter permutes them back)
  9.6  the shared experts are merged into one SwiGLU of width S*h
and `attention_multiplier = head_dim ** -0.5` (9.5). Sizes are read from the tensor shapes and must agree with the
spec. Anything this export cannot represent stops it with a message: an attention gate (attn-4), partial RoPE
(attn-3), a local window or sink (attn-2), expert biases, or a tensor name it does not know.

--verify N runs test A1 of section 12: N random prompts through G5's model and through `transformers`'
GraniteMoeSharedForCausalLM loaded from the export, both fp32 on CPU. It exits 1 unless the largest logit
difference is below --verify-tol and the top-1 token is the same at every position.

Writes config.json, generation_config.json, model.safetensors (--dtype, default bf16) and export_report.json. With
--tokenizer it also copies tokenizer.json and writes tokenizer_config.json (--bos / --eos), so the folder loads with
AutoTokenizer and vLLM. Needs torch, transformers and safetensors (the converter venv of quantize_eval.py has them).
"""
from __future__ import annotations

import argparse, hashlib, json, math, shutil, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HARNESS = REPO_ROOT / 'teams/05-architecture/harness'
SPEC_KEYS = ('n_head', 'rope_theta', 'norm_eps')          # not readable from tensor shapes
UNSUPPORTED = 'see teams/12-quantization/docs/unsupported_parts.md, section 10'


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(16 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def find_checkpoint(path: Path) -> tuple[Path, Path | None]:
    """Return (weights file, spec file or None) for a run folder or a single file."""
    if path.is_dir():
        for name in ('checkpoint.pt', 'model.safetensors'):
            if (path / name).exists():
                manifest = path / 'manifest.json'
                return path / name, manifest if manifest.exists() else None
        sys.exit(f'{path}: no checkpoint.pt or model.safetensors in this folder')
    if not path.exists():
        sys.exit(f'{path}: no such checkpoint')
    manifest = path.with_name('manifest.json')
    return path, manifest if manifest.exists() else None


def load_state(weights: Path) -> dict:
    import torch
    if weights.suffix == '.safetensors':
        from safetensors.torch import load_file
        return load_file(str(weights))
    # weights_only=False: the harness checkpoint also holds Python and numpy RNG state. Load only your own files.
    obj = torch.load(weights, map_location='cpu', weights_only=False)
    state = obj.get('model', obj) if isinstance(obj, dict) else obj
    if not isinstance(state, dict) or not all(hasattr(v, 'shape') for v in state.values()):
        sys.exit(f'{weights}: expected a state_dict, or a dict with the state_dict under "model"')
    return state


def load_spec(path: Path | None) -> dict:
    """The harness `model` mapping, from manifest.json (config.model), a config (model) or the mapping itself."""
    if path is None:
        return {}
    text = Path(path).read_text(encoding='utf-8')
    if Path(path).suffix in ('.yaml', '.yml'):
        import yaml
        obj = yaml.safe_load(text)
    else:
        obj = json.loads(text)
    for keys in (('config', 'model'), ('model',)):
        node = obj
        for k in keys:
            node = node.get(k) if isinstance(node, dict) else None
        if isinstance(node, dict):
            return node
    return obj


def resolve_spec(state: dict, given: dict) -> dict:
    """The full harness spec: sizes from the tensor shapes, the rest from `given`. Stops on anything not exportable."""
    known = ('embedding.', 'blocks.', 'norm.weight', 'head.weight', 'mtp_head.weight')
    strange = sorted(k for k in state if not k.startswith(known))
    if strange:
        sys.exit(f'not a G5 LanguageModel checkpoint: unknown tensors {strange[:5]}')
    for part, why in (('.attn.gate.', 'an attention output gate (attn-4)'), ('.attn.sink', 'attention sinks (attn-2)'),
                      ('.bias', 'bias tensors')):
        hit = [k for k in state if part in k or k.endswith(part)]
        if hit:
            sys.exit(f'cannot export {why}: {hit[0]}; {UNSUPPORTED}')
    vocab, width = state['head.weight'].shape
    n_layer = 1 + max(int(k.split('.')[1]) for k in state if k.startswith('blocks.'))
    moe = 'blocks.0.moe.'
    n_exp = state[moe + 'router.weight'].shape[0]
    n_shared = len({k.split('.')[4] for k in state if k.startswith(moe + 'shared.')})
    hidden = state[moe + 'experts.0.gate.weight'].shape[0]
    missing = [k for k in SPEC_KEYS if given.get(k) is None] + ([] if given.get('moe', {}).get('top_k') else ['moe.top_k'])
    if missing:
        sys.exit(f'the spec does not give {missing}: pass --spec (a run\'s manifest.json has them)')
    n_head = int(given['n_head'])
    head_dim = width // n_head
    n_kv = state['blocks.0.attn.k.weight'].shape[0] // head_dim
    if width % n_head or head_dim % 2 or state['blocks.0.attn.k.weight'].shape[0] % head_dim or n_head % n_kv:
        sys.exit(f'n_head {n_head} does not fit d_model {width} and the k projection {tuple(state["blocks.0.attn.k.weight"].shape)}')
    if given.get('rotary_fraction', 1.0) != 1.0:
        sys.exit(f'cannot export partial RoPE (attn-3, rotary_fraction {given["rotary_fraction"]}); {UNSUPPORTED}')
    if 'L' in (given.get('attn_pattern') or []):
        sys.exit(f'cannot export local-window layers (attn-2) yet; {UNSUPPORTED}')
    spec = dict(vocab_size=vocab, n_embd=width, n_layer=n_layer, n_head=n_head, n_kv_head=n_kv,
                rope_theta=float(given['rope_theta']), norm_eps=float(given['norm_eps']),
                block_size=int(given.get('block_size') or 0), mtp='mtp_head.weight' in state,
                moe=dict(num_experts=n_exp, num_shared=n_shared, top_k=int(given['moe']['top_k']), ffn_hidden=hidden, bias=False))
    # the spec must not contradict the tensors: a wrong spec file would export a different model silently
    for key, got in (('vocab_size', vocab), ('n_embd', width), ('n_layer', n_layer), ('n_kv_head', n_kv)):
        if given.get(key) not in (None, got):
            sys.exit(f'spec says {key} = {given[key]}, the checkpoint has {got}')
    for key, got in (('num_experts', n_exp), ('num_shared', n_shared), ('ffn_hidden', hidden)):
        if given.get('moe', {}).get(key) not in (None, got):
            sys.exit(f'spec says moe.{key} = {given["moe"][key]}, the checkpoint has {got}')
    if not 1 <= spec['moe']['top_k'] <= n_exp:
        sys.exit(f'moe.top_k {spec["moe"]["top_k"]} is outside 1..{n_exp}')
    return spec


def fold_ke2(state: dict, width: int, chunk: int = 8192):
    """9.1: the embedding of every id, from the harness module itself (so it includes its eps and std convention)."""
    import torch
    sys.path.insert(0, str(HARNESS))
    from week2.model import KE2
    rows, lengths = state['embedding.rows'], state['embedding.lengths']
    ke2 = KE2(rows.numpy(), lengths.numpy(), width)
    ke2.projection.weight.data.copy_(state['embedding.projection.weight'].float())
    with torch.no_grad():
        return torch.cat([ke2(torch.arange(i, min(i + chunk, len(rows)))) for i in range(0, len(rows), chunk)])


def to_halves(w, n_heads: int):
    """9.4: per head, output rows (0, 1, 2, ...) -> (0, 2, 4, ..., 1, 3, 5, ...)."""
    import torch
    d = w.shape[0] // n_heads
    order = torch.cat((torch.arange(0, d, 2), torch.arange(1, d, 2)))
    return w.reshape(n_heads, d, -1)[:, order, :].reshape(w.shape).contiguous()


def convert_state(state: dict, spec: dict) -> dict:
    """G5 state_dict -> GraniteMoeShared state_dict (fp32)."""
    import torch
    f = lambda k: state[k].float()
    out = {'model.embed_tokens.weight': fold_ke2(state, spec['n_embd']),
           'model.norm.weight': f('norm.weight'), 'lm_head.weight': f('head.weight')}
    E, S = spec['moe']['num_experts'], spec['moe']['num_shared']
    for i in range(spec['n_layer']):
        g, h = f'blocks.{i}.', f'model.layers.{i}.'
        out[h + 'input_layernorm.weight'] = f(g + 'n1.weight')
        out[h + 'post_attention_layernorm.weight'] = f(g + 'n2.weight')
        out[h + 'self_attn.q_proj.weight'] = to_halves(f(g + 'attn.q.weight'), spec['n_head'])
        out[h + 'self_attn.k_proj.weight'] = to_halves(f(g + 'attn.k.weight'), spec['n_kv_head'])
        out[h + 'self_attn.v_proj.weight'] = f(g + 'attn.v.weight')
        out[h + 'self_attn.o_proj.weight'] = f(g + 'attn.o.weight')
        out[h + 'block_sparse_moe.router.layer.weight'] = f(g + 'moe.router.weight')
        ex = lambda part: torch.stack([f(f'{g}moe.experts.{e}.{part}.weight') for e in range(E)])
        out[h + 'block_sparse_moe.input_linear.weight'] = torch.cat((ex('gate'), ex('up')), dim=1)   # [E, 2h, d], gate first
        out[h + 'block_sparse_moe.output_linear.weight'] = ex('down')                                # [E, d, h]
        if S:  # 9.6: stack gate rows, stack up rows, concatenate down columns
            sh = lambda part, dim: torch.cat([f(f'{g}moe.shared.{s}.{part}.weight') for s in range(S)], dim=dim)
            out[h + 'shared_mlp.input_linear.weight'] = torch.cat((sh('gate', 0), sh('up', 0)), dim=0)
            out[h + 'shared_mlp.output_linear.weight'] = sh('down', 1)
    return out


def hf_config(spec: dict, bos_id, eos_id, pad_id, dtype: str):
    from transformers import GraniteMoeSharedConfig
    head_dim = spec['n_embd'] // spec['n_head']
    return GraniteMoeSharedConfig(
        vocab_size=spec['vocab_size'], hidden_size=spec['n_embd'], num_hidden_layers=spec['n_layer'],
        num_attention_heads=spec['n_head'], num_key_value_heads=spec['n_kv_head'],
        intermediate_size=spec['moe']['ffn_hidden'],
        shared_intermediate_size=spec['moe']['num_shared'] * spec['moe']['ffn_hidden'],
        num_local_experts=spec['moe']['num_experts'], num_experts_per_tok=spec['moe']['top_k'],
        hidden_act='silu', rms_norm_eps=spec['norm_eps'], rope_theta=spec['rope_theta'],
        position_embedding_type='rope', max_position_embeddings=spec['block_size'] or 2048,
        attention_multiplier=head_dim ** -0.5, embedding_multiplier=1.0, residual_multiplier=1.0, logits_scaling=1.0,
        attention_dropout=0.0, tie_word_embeddings=False, use_cache=True, output_router_logits=False,
        bos_token_id=bos_id, eos_token_id=eos_id, pad_token_id=pad_id, torch_dtype=dtype,
        architectures=['GraniteMoeSharedForCausalLM'])


def verify(state: dict, spec: dict, config, new_state: dict, n_prompts: int, tol: float, seed: int = 0) -> dict:
    """Test A1: G5's LanguageModel against transformers' GraniteMoeSharedForCausalLM, fp32, random prompts."""
    import torch
    from transformers import GraniteMoeSharedForCausalLM
    sys.path.insert(0, str(HARNESS))
    from week2.model import LanguageModel
    ref = LanguageModel(dict(spec, mtp='mtp_head.weight' in state), state['embedding.rows'].numpy(),
                        state['embedding.lengths'].numpy()).eval()
    ref.load_state_dict(state, strict=True)
    hf = GraniteMoeSharedForCausalLM(config).float().eval()
    hf.load_state_dict(new_state, strict=True)
    T = min(spec['block_size'] or 64, 64)
    gen = torch.Generator().manual_seed(seed)
    worst, same, total = 0.0, 0, 0
    with torch.no_grad():
        for _ in range(n_prompts):
            ids = torch.randint(0, spec['vocab_size'], (1, T), generator=gen)
            a = ref(ids, torch.ones_like(ids, dtype=torch.bool))
            b = hf(input_ids=ids).logits
            worst = max(worst, (a - b).abs().max().item())
            same += (a.argmax(-1) == b.argmax(-1)).sum().item()
            total += T
    return dict(test='A1', prompts=n_prompts, tokens_per_prompt=T, max_abs_logit_diff=worst, tolerance=tol,
                same_top1=same, positions=total, passed=bool(worst <= tol and same == total))


def token_id(tokenizer_json: Path, token: str):
    """The id of an added (special) token, or None."""
    tok = json.loads(Path(tokenizer_json).read_text(encoding='utf-8'))
    return next((a['id'] for a in tok.get('added_tokens', []) if a['content'] == token), None)


def export(checkpoint: Path, out: Path, spec_path: Path | None = None, tokenizer: Path | None = None,
           bos: str = '<|begin_of_text|>', eos: str = '<|endoftext|>', pad: str = '<|pad|>', dtype: str = 'bf16',
           n_verify: int = 0, tol: float = 1e-3) -> dict:
    import torch
    from safetensors.torch import save_file
    from transformers import GraniteMoeSharedForCausalLM
    weights, found_spec = find_checkpoint(Path(checkpoint))
    state = load_state(weights)
    spec = resolve_spec(state, load_spec(spec_path or found_spec))
    ids = {name: token_id(tokenizer, tok) if tokenizer else None for name, tok in (('bos', bos), ('eos', eos), ('pad', pad))}
    if tokenizer:
        n_tok = 1 + max(max(json.loads(Path(tokenizer).read_text(encoding='utf-8'))['model']['vocab'].values()),
                        max(i for i in ids.values() if i is not None) if any(i is not None for i in ids.values()) else 0)
        if n_tok > spec['vocab_size']:
            sys.exit(f'the tokenizer has {n_tok:,} ids, the checkpoint\'s head {spec["vocab_size"]:,}')
        for name in ('bos', 'eos'):
            if ids[name] is None:
                sys.exit(f'{tokenizer}: no special token {dict(bos=bos, eos=eos)[name]!r} (set --{name})')
    torch_dtype = dict(bf16=torch.bfloat16, fp32=torch.float32)[dtype]
    config = hf_config(spec, ids['bos'], ids['eos'], ids['pad'], dict(bf16='bfloat16', fp32='float32')[dtype])
    new_state = convert_state(state, spec)
    # the target key list and shapes come from transformers itself; both must match before anything is written
    want = {k: tuple(v.shape) for k, v in GraniteMoeSharedForCausalLM(config).state_dict().items()}
    have = {k: tuple(v.shape) for k, v in new_state.items()}
    if want != have:
        diff = sorted(set(want) ^ set(have)) or [f'{k}: {have[k]} != {want[k]}' for k in want if have[k] != want[k]]
        sys.exit(f'export does not match transformers\' GraniteMoeSharedForCausalLM: {diff[:5]}')
    report = dict(checkpoint=str(weights), checkpoint_sha256=file_sha256(weights), spec=spec, dtype=dtype,
                  parameters=sum(v.numel() for v in new_state.values()),
                  dropped=sorted(k for k in state if k == 'mtp_head.weight' or k.startswith('embedding.')),
                  token_ids=ids)
    if n_verify:
        report['verify'] = verify(state, spec, config, new_state, n_verify, tol)
        v = report['verify']
        print(f'A1: max logit difference {v["max_abs_logit_diff"]:.3g} (limit {tol:g}), same top-1 on '
              f'{v["same_top1"]}/{v["positions"]} positions: {"PASS" if v["passed"] else "FAIL"}', flush=True)
        if not v['passed']:
            sys.exit(1)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    config.save_pretrained(out)
    (out / 'generation_config.json').write_text(json.dumps(
        {k: v for k, v in dict(bos_token_id=ids['bos'], eos_token_id=ids['eos'], pad_token_id=ids['pad']).items()
         if v is not None}, indent=2) + '\n', encoding='utf-8')
    save_file({k: v.to(torch_dtype).contiguous() for k, v in new_state.items()}, str(out / 'model.safetensors'),
              metadata={'format': 'pt'})
    if tokenizer:
        shutil.copyfile(tokenizer, out / 'tokenizer.json')
        # nothing is added when encoding (as in teams/03-tokenizer/release/tokenizer_config.json)
        roles = dict(tokenizer_class='PreTrainedTokenizerFast', bos_token=bos, eos_token=eos,
                     pad_token=pad if ids['pad'] is not None else None)
        (out / 'tokenizer_config.json').write_text(json.dumps(
            dict({k: v for k, v in roles.items() if v}, add_bos_token=False, add_eos_token=False,
                 clean_up_tokenization_spaces=False), indent=2) + '\n', encoding='utf-8')
        report['tokenizer_sha256'] = file_sha256(tokenizer)
    (out / 'export_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'exported {report["parameters"]:,} parameters ({dtype}) to {out}', flush=True)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--checkpoint', type=Path, required=True, help='run folder, checkpoint.pt or model.safetensors')
    ap.add_argument('--out', type=Path, required=True, help='folder for the Hugging Face model')
    ap.add_argument('--spec', type=Path, help='model settings (manifest.json, or a json/yaml with the model mapping)')
    ap.add_argument('--tokenizer', type=Path, help='tokenizer.json to put in the folder')
    ap.add_argument('--bos', default='<|begin_of_text|>')
    ap.add_argument('--eos', default='<|endoftext|>', help='end of document in the frozen tokenizer')
    ap.add_argument('--pad', default='<|pad|>')
    ap.add_argument('--dtype', choices=['bf16', 'fp32'], default='bf16')
    ap.add_argument('--verify', type=int, default=0, metavar='N', help='run test A1 on N random prompts first')
    ap.add_argument('--verify-tol', type=float, default=1e-3, help='largest fp32 logit difference allowed in A1')
    a = ap.parse_args()
    export(a.checkpoint, a.out, a.spec, a.tokenizer, a.bos, a.eos, a.pad, a.dtype, a.verify, a.verify_tol)


if __name__ == '__main__':
    main()
