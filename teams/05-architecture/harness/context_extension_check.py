"""Offline, fixed-weight 2K/4K RoPE/YaRN check on frozen G5 heldout_v1 text.

Stage SmolLM-135M revision 1d461723eec654e65efdc40cf49301c89c0c92f4
in the local Hugging Face cache. Only the canonical model ID is accepted.
Run from an isolated working directory; writes only ./out/.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import platform
from datetime import datetime, timezone

MODEL_ID = 'HuggingFaceTB/SmolLM-135M'
MODEL_REVISION = '1d461723eec654e65efdc40cf49301c89c0c92f4'
INPUT_SHA256 = '21c6e4b2df8dae9d69e254f4a00fc934d2a3c70f0675065a03724299d94312bb'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--heldout', type=Path, required=True)
    parser.add_argument('--model-path', choices=[MODEL_ID], default=MODEL_ID)
    args = parser.parse_args()
    raw = args.heldout.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == INPUT_SHA256, 'Frozen input bytes differ'
    import torch
    import torch.nn.functional as F
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

    assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    torch.manual_seed(1234)
    torch.set_num_threads(16)
    torch.set_float32_matmul_precision('highest')
    load = dict(revision=MODEL_REVISION, local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, **load)
    documents = []
    for line in raw.decode('utf-8').splitlines():
        row = json.loads(line)
        if not row['id'].startswith(('c4-val', 'owm-test', 'pes2o-val')):
            continue
        ids = tokenizer(row['text'], add_special_tokens=False, truncation=False)['input_ids']
        if len(ids) < 4096:
            continue
        ids = ids[:4096]
        documents.append(dict(id=row['id'], ids=ids,
            text_sha256=hashlib.sha256(row['text'].encode('utf-8')).hexdigest(),
            tokens_sha256=hashlib.sha256(json.dumps(ids).encode()).hexdigest()))
        if len(documents) == 3:
            break
    assert len(documents) == 3, 'Need three complete eligible 4K documents; do not pack or repeat'
    long = torch.tensor([d['ids'] for d in documents], device='cuda', dtype=torch.long)
    short = long[:, -2048:].contiguous()
    assert torch.equal(long[:, -512:], short[:, -512:])
    models = {}
    for method in ['Original RoPE', 'YaRN x2']:
        config = AutoConfig.from_pretrained(args.model_path, **load)
        assert config.max_position_embeddings == 2048
        if method == 'YaRN x2':
            config.max_position_embeddings = 4096
            config.rope_parameters = dict(rope_type='yarn', rope_theta=10000., factor=2.,
                original_max_position_embeddings=2048, beta_fast=32., beta_slow=1.)
        models[method] = AutoModelForCausalLM.from_pretrained(args.model_path,
            config=config, dtype=torch.bfloat16, attn_implementation='eager', **load).to('cuda').eval()
    assert all(torch.equal(p,q) for p,q in zip(models['Original RoPE'].parameters(),models['YaRN x2'].parameters()))
    result = []; token_loss = {}
    with torch.inference_mode():
        for arm, method, length in [('A','Original RoPE',2048),('B','Original RoPE',4096),('C','YaRN x2',4096),('D','YaRN x2',2048)]:
            x = short if length == 2048 else long
            outputs = models[method](input_ids=x, use_cache=False)
            logits = outputs.logits[:, -513:-1].float()
            loss = F.cross_entropy(logits.reshape(-1,logits.shape[-1]), x[:, -512:].reshape(-1),reduction='none').view(3,512)
            assert torch.isfinite(loss).all()
            token_loss[arm] = loss.cpu().tolist()
            for doc,nll in zip(documents,loss.mean(1).tolist()):
                result.append(dict(Run=arm,Method=method,Context=length,Document=doc['id'],NLL=nll,Perplexity=math.exp(nll),scored_tokens=512))
            del outputs, logits, loss
    summary=[]
    for arm in 'ABCD':
        selected=[r for r in result if r['Run']==arm]
        nll=math.fsum(r['NLL'] for r in selected)/3
        summary.append(dict(Run=arm,Method=selected[0]['Method'],Context=selected[0]['Context'],NLL=nll,Perplexity=math.exp(nll),scored_tokens=1536))
    out=Path.cwd()/'out';out.mkdir(exist_ok=True)
    for name,rows in [('document_results.csv',result),('summary.csv',summary)]:
        with (out/name).open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (out/'input_fixtures.json').write_text(json.dumps(documents,indent=2)+'\n')
    (out/'per_token_nll.json').write_text(json.dumps(token_loss)+'\n')
    manifest=dict(executed_at_utc=datetime.now(timezone.utc).isoformat(),model_id=MODEL_ID,model_revision=MODEL_REVISION,
        corpus='G5 heldout_v1, approved benchmark-free text',input_sha256=INPUT_SHA256,
        selection='First three complete records >=4096 tokens in c4-val/owm-test/pes2o-val source order; no packing, repetition or outcome-based selection',
        documents=[{k:v for k,v in d.items() if k!='ids'} for d in documents],attention_backend='eager',dtype='bfloat16',
        scored_targets='same final 512 IDs per document in all four arms',max_input_length=4096,weights='identical, fixed',
        no_training=True,full_vocabulary_head=True,checks=dict(input_hash=True,three_complete_documents=True,identical_targets=True,identical_weights=True,finite_all_four=True),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        environment=dict(python=platform.python_version(),torch=torch.__version__,transformers=importlib.metadata.version('transformers'),cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0)),
        scope='Self-run small-model subset, not a TSAI-returned run or full heldout_v1 score; no speed benchmark',summary=summary)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
