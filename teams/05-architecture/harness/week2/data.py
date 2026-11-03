"""Document-isolated teacher forcing; every text token/byte scored once."""
from pathlib import Path
import json
import hashlib
import torch

def read_texts(path,require_ids=False,records=False):
    path=Path(path)
    if path.suffix==".jsonl":
        seen=set()
        with path.open(encoding="utf8",errors="strict") as f:
            for n,line in enumerate(f,1):
                if not line.strip():continue
                obj=json.loads(line)
                if not isinstance(obj,dict) or not isinstance(obj.get("text"),str):
                    raise ValueError(f"{path}:{n}: expected text string")
                if require_ids and "id" not in obj:raise ValueError(f"{path}:{n}: missing document id")
                if "id" in obj:
                    if type(obj["id"]) not in (str,int):raise ValueError("Document id must be string or integer")
                    identity=(type(obj["id"]).__name__,str(obj["id"]))
                    if identity in seen:raise ValueError("Duplicate document id")
                    seen.add(identity)
                yield obj if records else obj["text"]
    elif path.suffix==".txt":
        yield {"text":path.read_text(encoding="utf8",errors="strict")} if records else path.read_text(encoding="utf8",errors="strict")
    else:raise ValueError("Week-2 byte-auditable input supports JSONL text documents or UTF-8 TXT")

class DocumentWindows:
    def __init__(self,path,artifacts,seq_len,require_ids=False,sources_path=None):
        self.windows=[];self.raw_bytes=0;self.tokens=0;self.document_hashes=set();self.document_count=0
        self.pad_id=artifacts.pad_id;self.seq_len=seq_len
        records=list(read_texts(path,require_ids=require_ids,records=True))
        from .scoring import source_slices
        slices=source_slices(sources_path,records) if sources_path else [None]*len(records)
        self.window_slices=[]
        self.slice_raw_bytes={}
        for doc,slice_name in zip(records,slices):
            text=doc['text']
            if slice_name is not None:self.slice_raw_bytes[slice_name]=self.slice_raw_bytes.get(slice_name,0)+len(text.encode('utf8'))
            self.document_count+=1
            self.document_hashes.add(hashlib.sha256(text.encode("utf8")).hexdigest())
            ids=artifacts.encode(text)
            self.raw_bytes+=len(text.encode("utf8"));self.tokens+=len(ids)
            for start in range(0,len(ids),seq_len):
                target=ids[start:start+seq_len]
                previous=artifacts.bos_id if start==0 else ids[start-1]
                inputs=[previous]+target[:-1]
                lengths=[int(artifacts.lengths[i]) for i in target]
                self.windows.append((inputs,target,lengths))
                self.window_slices.append(slice_name)
        if not self.windows or not self.raw_bytes:raise ValueError("Empty/zero-byte dataset")
        if sum(sum(x[2]) for x in self.windows)!=self.raw_bytes:raise ValueError("Byte conservation failed")

    def batch(self,indices,device):
        rows=[self.windows[int(i)] for i in indices]
        # No cross-document attention: every row is one window of one document.
        x=torch.full((len(rows),self.seq_len),self.pad_id,dtype=torch.long)
        y=torch.full_like(x,-100);lengths=torch.zeros_like(x)
        for i,(a,b,c) in enumerate(rows):
            x[i,:len(a)]=torch.tensor(a);y[i,:len(b)]=torch.tensor(b);lengths[i,:len(c)]=torch.tensor(c)
        return x.to(device),y.to(device),lengths.to(device)

class BatchStream:
    def __init__(self,dataset,batch_size,seed):
        self.dataset=dataset;self.batch_size=batch_size
        self.generator=torch.Generator().manual_seed(seed)
        self.order=torch.randperm(len(dataset.windows),generator=self.generator).tolist();self.offset=0
    def next(self,device):
        ids=[]
        while len(ids)<self.batch_size:
            if self.offset==len(self.order):
                self.order=torch.randperm(len(self.dataset.windows),generator=self.generator).tolist();self.offset=0
            n=min(self.batch_size-len(ids),len(self.order)-self.offset)
            ids+=self.order[self.offset:self.offset+n];self.offset+=n
        return self.dataset.batch(ids,device)
    def state_dict(self):return dict(order=self.order,offset=self.offset,rng=self.generator.get_state())
    def load_state_dict(self,state):
        self.order=state["order"];self.offset=state["offset"];self.generator.set_state(state["rng"])
