"""Heldout sum-of-loss / sum-of-raw-bytes scorer, never batch-mean BPB."""
import math
import torch
from torch.nn import functional as F

def token_nll(logits,targets):
    return F.cross_entropy(logits.float().reshape(-1,logits.shape[-1]),targets.reshape(-1),ignore_index=-100,reduction="none").reshape(targets.shape)

@torch.no_grad()
def evaluate(model,dataset,batch_size,device,autocast_context):
    training=model.training;cpu_rng=torch.get_rng_state();cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
    values=[];byte_count=0;token_count=0;by_slice={}
    try:
        model.eval()
        for start in range(0,len(dataset.windows),batch_size):
            x,y,lengths=dataset.batch(range(start,min(start+batch_size,len(dataset.windows))),device)
            with autocast_context():nll=token_nll(model(x,y!=-100),y)
            if not torch.isfinite(nll).all():raise ValueError("Nonfinite heldout NLL")
            values.append(math.fsum(nll[y!=-100].double().cpu().tolist()))
            byte_count+=int(lengths.sum());token_count+=int((y!=-100).sum())
            for offset in range(len(x)):
                name=dataset.window_slices[start+offset]
                if name is not None:
                    totals=by_slice.setdefault(name,{'nats':[],'bytes':0,'tokens':0})
                    totals['nats'].append(math.fsum(nll[offset][y[offset]!=-100].double().cpu().tolist()))
                    totals['bytes']+=int(lengths[offset].sum());totals['tokens']+=int((y[offset]!=-100).sum())
        if byte_count!=dataset.raw_bytes:raise ValueError("Heldout denominator failed byte conservation")
        total=math.fsum(values)
        result={"val/nll_nats":total,"val/utf8_bytes":byte_count,"val/scored_tokens":token_count,
                "val/bpb":total/math.log(2)/byte_count,"val/perplexity":math.exp(total/token_count)}
        if by_slice:
            from .scoring import group_metrics
            bpbs={}
            for name,totals in sorted(by_slice.items()):
                if totals['bytes']!=dataset.slice_raw_bytes[name] or totals['bytes']<=0:raise ValueError('Slice byte conservation failed')
                nats=math.fsum(totals['nats']);bpbs[name]=nats/math.log(2)/totals['bytes']
                result.update({f'val/slices/{name}/bpb':bpbs[name],f'val/slices/{name}/nll_nats':nats,
                               f'val/slices/{name}/utf8_bytes':totals['bytes'],f'val/slices/{name}/scored_tokens':totals['tokens']})
            result.update(group_metrics(bpbs))
        return result
    finally:
        model.train(training);torch.set_rng_state(cpu_rng)
        if cuda_rng is not None:torch.cuda.set_rng_state_all(cuda_rng)
