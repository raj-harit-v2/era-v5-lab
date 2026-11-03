"""Check the executable G5 runtime schema, separately from the Week-1 checker."""
import argparse
from pathlib import Path
import json
from week2.config import load,load_runtime,validate
from week2.artifacts import Artifacts
from train_week2 import apply_resolution

def main():
    p=argparse.ArgumentParser()
    p.add_argument("config",type=Path)
    p.add_argument("--resolution",type=Path)
    p.add_argument("--runtime",type=Path)
    p.add_argument("--lr",type=float)
    p.add_argument("--tokenizer",type=Path)
    p.add_argument("--byte-table",type=Path)
    a=p.parse_args()
    try:
        cfg=load_runtime(a.config,a.runtime)
        if a.resolution:cfg=apply_resolution(cfg,load(a.resolution))
        if a.lr is not None:cfg["optim"]["lr"]=a.lr
        errors=validate(cfg)
        for error in errors:print(error)
        print(str(len(errors))+" errors")
        if errors:return 1
        m=cfg["model"]
        print(json.dumps({"profile":cfg["intended"]["profile"],"width":m["n_embd"],"layers":m["n_layer"],"heads":m["n_head"],"kv_heads":m["n_kv_head"],"expert_ffn":m["moe"]["ffn_hidden"],"context":m["block_size"],"output_head":"dense_untied","baseline_approval":cfg["approval"]["status"],"provenance":cfg["provenance"]},indent=2))
        if bool(a.tokenizer)!=bool(a.byte_table):raise ValueError("Provide tokenizer AND byte table")
        if a.tokenizer:
            artifacts=Artifacts(a.tokenizer,a.byte_table)
            if len(artifacts.lengths)!=m["vocab_size"] or artifacts.pos_dim!=m["ke_max_pos"]:raise ValueError("Config/artifact shape mismatch")
            print(json.dumps(artifacts.identity(),indent=2))
        print("Runtime specification valid; smoke-only status is not experimental approval")
        return 0
    except (ValueError,KeyError,OSError) as e:print(str(e));return 1

if __name__=="__main__":raise SystemExit(main())
