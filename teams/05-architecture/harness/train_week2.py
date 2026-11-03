"""G5 Week-2 trainer. Accepted Week-1 train.py is deliberately unchanged."""
from __future__ import annotations
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import argparse
from contextlib import nullcontext
import hashlib
import importlib
import json
from pathlib import Path
import random
import time
import numpy as np
import torch
from week2.artifacts import Artifacts, sha256
from week2.config import load, load_runtime, merge, validate
from week2.data import DocumentWindows, BatchStream
from week2.model import LanguageModel
from week2.evaluation import evaluate, token_nll

class JsonWriter:
    def __init__(self, out, cadence=10):
        self.file=(out/"metrics.jsonl").open("w",encoding="utf8");self.cadence=cadence
    def write(self,row):
        self.file.write(json.dumps(row,allow_nan=False)+"\n")
        if row.get("step",0)%self.cadence==0:self.flush()
    def flush(self):self.file.flush()
    def close(self):self.file.close()

def model_hash(model):
    h=hashlib.sha256()
    for name,value in sorted(model.state_dict().items()):
        h.update(name.encode());h.update(str(value.dtype).encode());h.update(str(tuple(value.shape)).encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()

def apply_resolution(cfg,resolution):
    allowed={"approval.status","approval.reference","model.rope_theta","model.norm_eps",
             
             "model.mtp_weight","model.moe.bias","evaluation.approved","run.micro_batch_size"}
    def paths(obj,prefix=""):
        out=[]
        for k,v in obj.items():
            key=prefix+k
            out.extend(paths(v,key+".")) if isinstance(v,dict) else out.append(key)
        return out
    unknown=set(paths(resolution))-allowed
    if unknown:raise ValueError("Resolution cannot change fixed sizes/arms: "+str(sorted(unknown)))
    for key, value in cfg.get("provenance",{}).get("lead_explicit_choices",{}).items():
        node=resolution
        for component in key.split("."):
            if not isinstance(node,dict) or component not in node:break
            node=node[component]
        else:
            if node != value:
                raise ValueError("Resolution conflicts with explicit lead choice: "+key)
    return merge(cfg,resolution)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ["config","tokenizer","byte-table","train-data","heldout-data","out"]:
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--runtime",type=Path,help="Harness-only runtime contract; dimensions remain lead-owned")
    p.add_argument("--resolution",type=Path,help="Reviewed baseline choices, separate from fixed sizes")
    p.add_argument("--heldout-sources",type=Path,help="PR191 per-document source/slice sidecar")
    p.add_argument("--heldout-sha256",type=Path,help="Official results/heldout_v1.sha256 file")
    p.add_argument("--heldout-report",type=Path,help="Data-owner JSON provenance; see HARNESS_WEEK2.md")
    p.add_argument("--lr",type=float,help="Explicit LR override, recorded in manifest; no optimizer default")
    p.add_argument("--seed",type=int)
    p.add_argument("--device",choices=["cpu","cuda"],default="cpu")
    p.add_argument("--smoke",action="store_true",help="Marks output NOT a quality result and permits provisional choices")
    p.add_argument("--smoke-steps",type=int,default=3)
    p.add_argument("--smoke-seq-len",type=int)
    p.add_argument("--smoke-batch-size",type=int)
    p.add_argument("--logger-factory",help="module:function returning writer(out_dir) with write/flush/close")
    p.add_argument("--stop-after",type=int)
    p.add_argument("--no-checkpoint",action="store_true",help="Smoke checks only: omit large checkpoint output")
    p.add_argument("--resume",type=Path,help="Only load your own trusted harness checkpoint")
    args=p.parse_args();started=time.perf_counter()
    if args.out.exists() and any(args.out.iterdir()):p.error("Use a fresh output directory")
    cfg=load_runtime(args.config,args.runtime)
    if args.resolution is None:
        if not args.smoke:p.error("Baseline choices pending: supply an agreed resolution file")
        args.resolution=Path(__file__).resolve().parents[1]/"configs/small/smoke_resolution.yaml"
    cfg=apply_resolution(cfg,load(args.resolution))
    if args.lr is not None:cfg["optim"]["lr"]=args.lr
    if args.seed is not None:cfg["run"]["seed"]=args.seed
    if args.smoke:
        cfg["run"]["steps"]=args.smoke_steps
        cfg["run"]["dtype"]="fp32" if args.device=="cpu" else cfg["run"]["dtype"]
        if args.smoke_seq_len:cfg["model"]["block_size"]=args.smoke_seq_len
        if args.smoke_batch_size:cfg["run"]["batch_size"]=args.smoke_batch_size;cfg["run"]["micro_batch_size"]=args.smoke_batch_size
    else:
        if args.device!="cuda" or cfg["run"]["dtype"]!="bf16":p.error("Lead plan requires GPU BF16 for quality runs")
        if cfg["approval"]["status"]!="agreed" or not cfg["approval"]["reference"] or not cfg["evaluation"]["approved"]:
            p.error("Baseline/head/scoring agreements are pending; use smoke mode for development")
        if not args.heldout_sources or not args.heldout_sha256:p.error("Quality scoring requires official heldout hash and slice sources")
        if not args.heldout_report:p.error("Data-owner heldout zero-match provenance required")
        if args.no_checkpoint:p.error("Quality runs must save checkpoint state")
        if args.smoke_seq_len or args.smoke_batch_size:p.error("Smoke shape overrides forbidden in quality runs")
    errors=validate(cfg)
    if errors:p.error("; ".join(errors))
    if args.smoke_steps<=0 or (args.stop_after is not None and args.stop_after<=0):p.error("Step counts must be positive")
    device=torch.device(args.device)
    if device.type=="cuda" and (not torch.cuda.is_available()):p.error("CUDA unavailable")
    if device.type=="cuda" and cfg["run"]["dtype"]=="bf16" and torch.cuda.get_device_capability()[0]<8:
        p.error("Native BF16 hardware required; no silent FP16 substitution")
    seed=cfg["run"]["seed"];random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    artifacts=Artifacts(args.tokenizer,args.byte_table)
    if len(artifacts.lengths)!=cfg["model"]["vocab_size"]:p.error("Model/tokenizer vocabulary mismatch")
    if artifacts.pos_dim!=cfg["model"]["ke_max_pos"]:p.error("Byte-table P differs from model config")
    train_hash=sha256(args.train_data);heldout_hash=sha256(args.heldout_data)
    if train_hash==heldout_hash:p.error("Training and holdout files are identical")
    train=DocumentWindows(args.train_data,artifacts,cfg["model"]["block_size"])
    val=DocumentWindows(args.heldout_data,artifacts,cfg["model"]["block_size"],require_ids=not args.smoke,sources_path=args.heldout_sources)
    if train.document_hashes & val.document_hashes:p.error("Exact document overlap between train and holdout")
    if args.heldout_sha256:
        lines=[line.split() for line in args.heldout_sha256.read_text(encoding='utf8').splitlines() if line.strip()]
        if len(lines)!=1 or len(lines[0])!=2 or lines[0][0]!=heldout_hash:p.error('Official heldout checksum mismatch')
        if Path(lines[0][1].lstrip('*')).name!=args.heldout_data.name:p.error('Official checksum names a different heldout file')
    if not args.smoke and set(val.slice_raw_bytes)!={'en','code','math','sci','hi','bn','ta','te','kn','ml','mr','gu','pa','or','as'}:p.error('Official holdout must provide all 15 slices')
    report=None
    if args.heldout_report:
        report=json.loads(args.heldout_report.read_text(encoding="utf8"))
        if (report.get("heldout_sha256")!=heldout_hash or type(report.get("matches")) is not int or report["matches"]!=0
            or not report.get("fingerprint_set_id") or report.get("scope")!="full"
            or report.get("docs_checked")!=val.document_count):
            p.error("Heldout report must bind this file/document count to full-set zero matches")
    model=LanguageModel(cfg["model"],artifacts.bytes,artifacts.lengths).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=cfg["optim"]["lr"],betas=tuple(cfg["optim"]["betas"]),eps=cfg["optim"]["eps"],weight_decay=cfg["optim"]["weight_decay"])
    stream=BatchStream(train,cfg["run"]["batch_size"],seed)
    def amp():
        return torch.autocast(device_type="cuda",dtype=torch.bfloat16) if device.type=="cuda" and cfg["run"]["dtype"]=="bf16" else nullcontext()
    source_files=[Path(__file__),*Path(__file__).with_name("week2").glob("*.py")]
    sources={f.name:sha256(f) for f in source_files}
    identity={"config":cfg,"artifacts":artifacts.identity(),"train_sha256":train_hash,"heldout_sha256":heldout_hash,
              "heldout_sources_sha256":sha256(args.heldout_sources) if args.heldout_sources else None,
              "heldout_checksum_sha256":sha256(args.heldout_sha256) if args.heldout_sha256 else None,
              "sources":sources,"device":str(device),"torch":torch.__version__,"smoke":args.smoke}
    identity_hash=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    args.out.mkdir(parents=True,exist_ok=True)
    manifest={**identity,"identity_sha256":identity_hash,"baseline_commit":cfg["provenance"]["lead_snapshot"],
              "parameters":model.parameter_count(),"gpu":torch.cuda.get_device_name() if device.type=="cuda" else None,
              "status":"SMOKE_NOT_A_QUALITY_RESULT" if args.smoke else "AGREED_BASELINE_RUN",
              "heldout_provenance":report,"g8_external_writer":bool(args.logger_factory),
              "token_budget_note":"Input positions include right padding; scored tokens/bytes reported separately",
              "train_documents":train.document_count,"heldout_documents":val.document_count}
    (args.out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf8")
    external=None
    if args.logger_factory:
        module,name=args.logger_factory.split(":",1);external=getattr(importlib.import_module(module),name)(args.out)
    writer=JsonWriter(args.out,cfg["run"]["flush_every_steps"])
    rows=[];trace=[];ntp_trace=[];completed=0;resumed_seconds=0.0
    if args.resume:
        checkpoint=torch.load(args.resume,map_location=device,weights_only=False)
        if checkpoint["identity_sha256"]!=identity_hash:p.error("Resume code/config/artifact/data/device/software identity changed")
        model.load_state_dict(checkpoint["model"]);optimizer.load_state_dict(checkpoint["optimizer"])
        stream.load_state_dict(checkpoint["stream"]);torch.set_rng_state(checkpoint["torch_rng"].cpu())
        if checkpoint["cuda_rng"] is not None:torch.cuda.set_rng_state_all([v.cpu() for v in checkpoint["cuda_rng"]])
        random.setstate(checkpoint["python_rng"]);np.random.set_state(checkpoint["numpy_rng"])
        completed=checkpoint["step"];trace=checkpoint["trace"];ntp_trace=checkpoint["ntp_trace"]
        rows=checkpoint["rows"];resumed_seconds=checkpoint["wall_seconds"]
    def log(row):
        for key in ["tokens_per_second","loss_ntp","loss_mtp","loss","lr","gpu_alloc_gb","gradient_norm"]:
            row.setdefault(key, float(cfg["optim"]["lr"]) if key=="lr" else 0.0)
        writer.write(row)
        if external:external.write(row)
    try:
        for row in rows:log(row)
        if not rows:
            row=dict(step=0,**evaluate(model,val,1,device,amp));rows.append(row);log(row)
        steps=cfg["run"]["steps"]
        if args.stop_after is not None:steps=min(steps,args.stop_after)
        timed_out=False
        for step in range(completed+1,steps+1):
            if resumed_seconds+time.perf_counter()-started>=cfg["run"]["max_time_min"]*60:timed_out=True;break
            if device.type=="cuda":torch.cuda.synchronize()
            tick=time.perf_counter();x,y,lengths=stream.next(device)
            optimizer.zero_grad(set_to_none=True);count=int((y!=-100).sum());mtp_count=int((y[:,1:]!=-100).sum())
            total=0.0;ntp_value=0.0;mtp_value=0.0;micro=cfg["run"]["micro_batch_size"]
            for start in range(0,len(x),micro):
                tx,ty=x[start:start+micro],y[start:start+micro]
                with amp():
                    logits,mtp_logits=model(tx,ty!=-100,return_mtp=True)
                    ntp=token_nll(logits,ty).sum()/count
                    mtp=None
                    if mtp_logits is not None:
                        targets=torch.full_like(ty,-100);targets[:,:-1]=ty[:,1:]
                        mtp=token_nll(mtp_logits,targets).sum()/max(mtp_count,1)
                    loss=ntp if mtp is None or cfg["model"]["mtp_weight"]==0 else ntp+cfg["model"]["mtp_weight"]*mtp
                if not torch.isfinite(loss):raise ValueError("Nonfinite training objective")
                if mtp is not None and not torch.isfinite(mtp):raise ValueError("Nonfinite MTP component")
                loss.backward();total+=float(loss.detach());ntp_value+=float(ntp.detach())
                if mtp is not None:mtp_value+=float(mtp.detach())
            for name,param in model.named_parameters():
                if param.grad is not None and not torch.isfinite(param.grad).all():raise ValueError("Nonfinite gradient: "+name)
            norm=torch.nn.utils.clip_grad_norm_(model.parameters(),cfg["run"]["grad_clip"],error_if_nonfinite=True)
            optimizer.step()
            if any(not torch.isfinite(v).all() for v in model.parameters()):raise ValueError("Nonfinite parameter")
            if device.type=="cuda":torch.cuda.synchronize()
            ms=(time.perf_counter()-tick)*1000;trace.append(total);ntp_trace.append(ntp_value);completed=step
            row={"step":step,"train/ce_loss":ntp_value,"loss_total":total,"loss_ntp":ntp_value,"loss_mtp":mtp_value if cfg["model"]["mtp"] else 0.0,
                 "mtp_weight":cfg["model"]["mtp_weight"],"loss":ntp_value,"lr":cfg["optim"]["lr"],"gradient_norm":float(norm),
                 "gradient_clipping_applied":float(norm)>cfg["run"]["grad_clip"],"train/scored_tokens":count,"train/input_positions":x.numel(),
                 "train/utf8_bytes":int(lengths.sum()),"perf/step_ms":ms,"tokens_per_second":x.numel()/(ms/1000),
                 "gpu_alloc_gb":torch.cuda.memory_allocated()/1024**3 if device.type=="cuda" else 0.0}
            if step%cfg["run"]["eval_every_steps"]==0 or step==cfg["run"]["steps"]:
                row.update(evaluate(model,val,1,device,amp))
            rows.append(row);log(row)
        # Interrupted segments must not introduce extra validation events into resume history.
        writer.flush()
        if external:external.flush()
        wall=resumed_seconds+time.perf_counter()-started
        if not args.no_checkpoint:
            torch.save({"model":model.state_dict(),"optimizer":optimizer.state_dict(),"stream":stream.state_dict(),"torch_rng":torch.get_rng_state(),
                        "cuda_rng":torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,"python_rng":random.getstate(),"numpy_rng":np.random.get_state(),
                        "step":completed,"identity_sha256":identity_hash,"trace":trace,"ntp_trace":ntp_trace,"rows":rows,"wall_seconds":wall},args.out/"checkpoint.pt")
        (args.out/"losses.txt").write_text("\n".join(v.hex() for v in ntp_trace)+"\n",encoding="utf8")
        (args.out/"total_losses.txt").write_text("\n".join(v.hex() for v in trace)+"\n",encoding="utf8")
        full=completed==cfg["run"]["steps"] and not timed_out
        (args.out/"summary.json").write_text(json.dumps({"status":"SMOKE" if args.smoke else ("COMPLETED" if full else "INCOMPLETE_NOT_A_RESULT"),
            "steps":completed,"wall_seconds":wall,"timed_out":timed_out,"first_ce":ntp_trace[0] if ntp_trace else None,
            "last_ce":ntp_trace[-1] if ntp_trace else None,"final_model_sha256":model_hash(model),"eligible_for_quality_comparison":full and not args.smoke},indent=2),encoding="utf8")
    finally:
        writer.close()
        if external:external.close()

if __name__=="__main__":main()
