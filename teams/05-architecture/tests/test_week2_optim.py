from pathlib import Path
import sys
import unittest
import torch
from torch.nn import functional as F
TEAM=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TEAM/"harness"))
sys.path.insert(0,str(TEAM/"tests"))
from week2.config import load,load_runtime,merge,validate
from week2.model import LanguageModel
from week2.optim import Muon,Optimizers,build_optimizer,describe,uses_muon,zeropower_via_newtonschulz5
from test_week2_model import fixture

def muon_fixture(muon_lr=0.02):
    c,rows,lengths=fixture();c["optim"].update(name="muon",muon_lr=muon_lr);return c,rows,lengths

def train(c,rows,lengths,steps=3,opt=None,model=None):
    if model is None:torch.manual_seed(1234);model=LanguageModel(c["model"],rows,lengths)
    if opt is None:opt=build_optimizer(model,c["optim"])
    ids=torch.arange(16).reshape(2,8)%31;values=[]
    for _ in range(steps):
        opt.zero_grad(set_to_none=True)
        loss=F.cross_entropy(model(ids,torch.ones_like(ids,dtype=torch.bool)).reshape(-1,31),(ids+1).reshape(-1)%31)
        loss.backward();opt.step();values.append(float(loss.detach()).hex())
    return model,opt,values

class SplitTests(unittest.TestCase):
    def test_every_parameter_in_exactly_one_optimizer(self):
        c,rows,lengths=muon_fixture();m=LanguageModel(c["model"],rows,lengths);opt=build_optimizer(m,c["optim"])
        self.assertIsInstance(opt,Optimizers)
        ids=[id(p) for _,o in opt.named for g in o.param_groups for p in g["params"]]
        self.assertEqual(len(ids),len(set(ids)));self.assertEqual(set(ids),{id(p) for p in m.parameters()})
    def test_block_matrices_on_muon_rest_on_adamw(self):
        c,rows,lengths=muon_fixture();m=LanguageModel(c["model"],rows,lengths);opt=dict(build_optimizer(m,c["optim"]).named)
        muon={id(p) for g in opt["muon"].param_groups for p in g["params"]}
        names={n for n,p in m.named_parameters() if id(p) in muon}
        for expected in ["blocks.0.attn.q.weight","blocks.0.attn.o.weight","blocks.0.moe.router.weight",
                         "blocks.0.moe.experts.0.gate.weight","blocks.0.moe.shared.0.down.weight"]:self.assertIn(expected,names)
        for n,p in m.named_parameters():
            if n.startswith("embedding.") or n.startswith("head.") or "norm" in n or n.startswith("blocks.0.n1"):self.assertNotIn(n,names)
        self.assertTrue(all(p.ndim==2 for n,p in m.named_parameters() if n in names))
        self.assertEqual(opt["muon"].param_groups[0]["lr"],0.02);self.assertEqual(opt["adamw"].param_groups[0]["lr"],1e-3)
    def test_adamw_arm_unchanged(self):
        c,rows,lengths=fixture();m=LanguageModel(c["model"],rows,lengths);opt=build_optimizer(m,c["optim"])
        self.assertIs(type(opt),torch.optim.AdamW);self.assertEqual(describe(m,c["optim"])["name"],"adamw")

class StepTests(unittest.TestCase):
    def test_one_step_moves_muon_and_adamw_weights(self):
        c,rows,lengths=muon_fixture();torch.manual_seed(1234);m=LanguageModel(c["model"],rows,lengths)
        before={n:p.detach().clone() for n,p in m.named_parameters()};train(c,rows,lengths,1,model=m)
        for n in ["blocks.0.attn.q.weight","embedding.projection.weight","head.weight"]:
            self.assertFalse(torch.equal(before[n],dict(m.named_parameters())[n]),n)
    def test_unused_expert_not_updated(self):
        p=torch.nn.Parameter(torch.ones(4,3));o=Muon([p],lr=0.1);o.step()
        self.assertTrue(torch.equal(p,torch.ones(4,3)));self.assertNotIn("buf",o.state[p])
    def test_update_is_orthogonalised_and_scaled(self):
        g=torch.randn(8,4,dtype=torch.float64);u=zeropower_via_newtonschulz5(g).double()
        s=torch.linalg.svdvals(u);self.assertTrue(((s>0.5)&(s<1.5)).all(),s)
        p=torch.nn.Parameter(torch.zeros(8,4));p.grad=g.float();o=Muon([p],lr=0.1,momentum=0.0,nesterov=False);o.step()
        torch.testing.assert_close(-p.detach(),0.1*2**0.5*zeropower_via_newtonschulz5(g.float()).float())
    def test_same_seed_same_trace(self):
        c,rows,lengths=muon_fixture()
        self.assertEqual(train(c,rows,lengths)[2],train(c,rows,lengths)[2])
    def test_different_muon_lr_changes_trace(self):
        self.assertNotEqual(train(*muon_fixture(0.001))[2],train(*muon_fixture(0.1))[2])
    def test_resume_matches_uninterrupted(self):
        c,rows,lengths=muon_fixture();_,_,full=train(c,rows,lengths,4)
        m,opt,first=train(c,rows,lengths,2);state={"model":m.state_dict(),"optimizer":opt.state_dict()}
        torch.manual_seed(999);m2=LanguageModel(c["model"],rows,lengths);m2.load_state_dict(state["model"])
        opt2=build_optimizer(m2,c["optim"]);opt2.load_state_dict(state["optimizer"])
        _,_,rest=train(c,rows,lengths,2,opt=opt2,model=m2);self.assertEqual(first+rest,full)
    def test_state_names_must_match(self):
        c,rows,lengths=muon_fixture();m=LanguageModel(c["model"],rows,lengths);opt=build_optimizer(m,c["optim"])
        with self.assertRaisesRegex(ValueError,"state names"):opt.load_state_dict({"adamw":{}})

class ConfigTests(unittest.TestCase):
    def resolved(self,path):return merge(load_runtime(TEAM/"configs/arms"/path),load(TEAM/"configs/small/smoke_resolution.yaml"))
    def test_three_screen_arms(self):
        for name,rate in [("1e-3",1e-3),("1e-2",1e-2),("1e-1",1e-1)]:
            c=self.resolved("muon_screen/muon_"+name+".yaml")
            self.assertEqual((c["optim"]["name"],c["optim"]["muon_lr"],c["optim"]["lr"]),("muon",rate,1e-3))
            self.assertEqual((c["model"]["n_embd"],c["run"]["seed"],c["intended"]["max_time_min"]),(256,1234,30))
            self.assertEqual(validate(c),[])
    def test_muon_without_rate_rejected(self):
        c=self.resolved("muon_screen/muon_1e-2.yaml");c["optim"]["muon_lr"]=None
        self.assertTrue(any("muon_lr" in e for e in validate(c)))
    def test_adamw_with_muon_rate_rejected(self):
        c=self.resolved("exp1/lr_1e-3.yaml");c["optim"]["muon_lr"]=0.01
        self.assertTrue(any("muon_lr" in e for e in validate(c)))
    def test_unknown_optimizer_rejected(self):
        c=self.resolved("muon_screen/muon_1e-2.yaml");c["optim"]["name"]="sgd"
        self.assertTrue(any("never replaced silently" in e for e in validate(c)))
    def test_manifest_record(self):
        c,rows,lengths=muon_fixture(0.01);m=LanguageModel(c["model"],rows,lengths);d=describe(m,c["optim"])
        self.assertEqual((d["name"],d["muon_lr"],d["adamw_lr"],d["momentum"]),("muon",0.01,1e-3,0.95))
        self.assertEqual(d["muon_parameters"]+d["adamw_parameters"],m.parameter_count())

if __name__=="__main__":unittest.main()
