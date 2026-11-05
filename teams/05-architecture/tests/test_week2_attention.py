"""Attention contract, independent visibility checks and deterministic resume."""
import copy
import io
from pathlib import Path
import sys
import unittest
import torch
from torch.nn import functional as F
TEAM=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TEAM/"harness"))
sys.path.insert(0,str(TEAM/"tests"))
from test_week2_model import fixture
from week2.model import GQA,LanguageModel
from week2.config import load_runtime,validate

def spec(kind):
    c,rows,lengths=fixture();m=c["model"]
    if kind=="mqa":m["n_kv_head"]=1
    if kind=="local":m.update(attn_pattern=["L","G"],attn_window=3,attn_sink=True)
    if kind=="partial":m["rotary_fraction"]=0.5
    if kind=="gate":m.update(attn_gate=True,attn_gate_input="normalized",attn_gate_bias=False,attn_gate_init="linear_default")
    return c,rows,lengths

def train(kind,steps=4,state=None):
    c,rows,lengths=spec(kind);torch.manual_seed(1234)
    model=LanguageModel(c["model"],rows,lengths);opt=torch.optim.AdamW(model.parameters(),lr=.001)
    if state:
        model.load_state_dict(state["model"]);opt.load_state_dict(state["optimizer"]);torch.set_rng_state(state["rng"])
    ids=torch.arange(16).reshape(2,8)%31;valid=torch.ones_like(ids,dtype=torch.bool);trace=[]
    for _ in range(steps):
        opt.zero_grad();loss=F.cross_entropy(model(ids,valid).reshape(-1,31),(ids+1).reshape(-1)%31)
        if not torch.isfinite(loss):raise AssertionError("Nonfinite loss")
        loss.backward()
        for p in model.parameters():
            if p.grad is not None and not torch.isfinite(p.grad).all():raise AssertionError("Nonfinite gradient")
        opt.step();trace.append(float(loss.detach()).hex())
    buf=io.BytesIO();torch.save(dict(model=model.state_dict(),optimizer=opt.state_dict(),rng=torch.get_rng_state()),buf);buf.seek(0)
    return trace,torch.load(buf,weights_only=False)

class AttentionTests(unittest.TestCase):
    def setUp(self):torch.manual_seed(1234);self.c,_,_=fixture();self.m=self.c["model"];self.x=torch.randn(2,8,16)
    def test_disabled_options_preserve_initialization_output_and_rng(self):
        torch.manual_seed(1234);a=GQA(self.m);rng=torch.get_rng_state()
        m=copy.deepcopy(self.m);m.update(attn_pattern=["G","G"],attn_sink=False,attn_gate=False)
        torch.manual_seed(1234);b=GQA(m)
        self.assertTrue(torch.equal(rng,torch.get_rng_state()))
        self.assertEqual(list(a.state_dict()),list(b.state_dict()))
        self.assertTrue(torch.equal(a(self.x),b(self.x)))
    def test_local_full_window_exact_global(self):
        a=GQA(self.m);m=copy.deepcopy(self.m);m.update(attn_pattern=["L","G"],attn_window=8)
        b=GQA(m);b.load_state_dict(a.state_dict());self.assertTrue(torch.equal(a(self.x),b(self.x)))
    def test_window_one_reads_only_self(self):
        m=copy.deepcopy(self.m);m.update(attn_pattern=["L","G"],attn_window=1);a=GQA(m)
        expected=a.o(a.v(self.x).view(2,8,2,4).repeat_interleave(2,dim=2).reshape(2,8,16))
        self.assertTrue(torch.equal(a(self.x),expected))
    def test_outside_window_and_future_excluded(self):
        m=copy.deepcopy(self.m);m.update(attn_pattern=["L","G"],attn_window=3);a=GQA(m)
        y=self.x.clone();y[:,0:3]+=100;y[:,6:]+=100
        self.assertTrue(torch.equal(a(self.x)[:,5],a(y)[:,5]))
    def test_sink_negative_infinity_exact_no_sink(self):
        m=copy.deepcopy(self.m);m.update(attn_pattern=["L","G"],attn_window=3);a=GQA(m)
        m["attn_sink"]=True;b=GQA(m);b.load_state_dict(a.state_dict(),strict=False)
        with torch.no_grad():b.sink.fill_(-float("inf"))
        self.assertTrue(torch.equal(a(self.x),b(self.x)))
    def test_sink_receives_gradient_local_only(self):
        c,_,_=spec("local");a=GQA(c["model"],0);b=GQA(c["model"],1)
        a(self.x).square().sum().backward();self.assertIsNotNone(a.sink.grad);self.assertTrue(torch.isfinite(a.sink.grad).all());self.assertIsNone(b.sink)
    def test_partial_rotary_leaves_tail_exact(self):
        c,_,_=spec("partial");a=GQA(c["model"]);x=torch.randn(2,4,8,4);y=a.rotary(x)
        self.assertTrue(torch.equal(x[...,2:],y[...,2:]));self.assertFalse(torch.equal(x[...,:2],y[...,:2]))
    def test_partial_rotary_uses_rotated_dimension_frequencies(self):
        c,_,_=spec("partial");a=GQA(c["model"]);x=torch.ones(1,1,3,4);y=a.rotary(x)
        angles=torch.arange(3).float();expected=torch.stack((angles.cos()-angles.sin(),angles.sin()+angles.cos()),-1)
        torch.testing.assert_close(y[0,0,:,:2],expected,rtol=0,atol=0)
    def test_zero_gate_is_half_attention_and_gets_gradient(self):
        a=GQA(self.m);c,_,_=spec("gate");c["model"]["attn_gate_init"]="zero";b=GQA(c["model"]);b.load_state_dict(a.state_dict(),strict=False)
        torch.testing.assert_close(b(self.x),a(self.x)*.5,rtol=0,atol=0)
        b(self.x).square().sum().backward();self.assertGreater(float(b.gate.weight.grad.abs().sum()),0)
    def test_confirmed_gate_matches_plain_linear_initialization_and_rng(self):
        c,_,_=spec("gate");m=c["model"];width=m["n_embd"]
        torch.manual_seed(1234)
        # Match the four ordinary Q/K/V/O constructors preceding the gate.
        torch.nn.Linear(width,width,bias=False)
        torch.nn.Linear(width,m["n_kv_head"]*(width//m["n_head"]),bias=False)
        torch.nn.Linear(width,m["n_kv_head"]*(width//m["n_head"]),bias=False)
        torch.nn.Linear(width,width,bias=False)
        expected=torch.nn.Linear(width,width,bias=False);rng=torch.get_rng_state()
        torch.manual_seed(1234);actual=GQA(m)
        self.assertIsNone(actual.gate.bias)
        self.assertTrue(torch.equal(actual.gate.weight,expected.weight))
        self.assertTrue(torch.equal(torch.get_rng_state(),rng))
        self.assertGreater(float(actual.gate.weight.detach().abs().sum()),0)
    def test_confirmed_gate_reads_same_normalized_tensor_as_queries(self):
        c,rows,lengths=spec("gate");model=LanguageModel(c["model"],rows,lengths);seen={}
        q=model.blocks[0].attn.q.register_forward_pre_hook(lambda module,args:seen.update(q=args[0].detach().clone()))
        g=model.blocks[0].attn.gate.register_forward_pre_hook(lambda module,args:seen.update(gate=args[0].detach().clone()))
        try:
            ids=torch.arange(8)[None,:];model(ids,torch.ones_like(ids,dtype=torch.bool))
        finally:q.remove();g.remove()
        self.assertTrue(torch.equal(seen["q"],seen["gate"]))
    def test_residual_gate_requires_and_uses_residual(self):
        c,_,_=spec("gate");c["model"].update(attn_gate_input="residual",attn_gate_init="linear_default",attn_gate_bias=True);a=GQA(c["model"])
        with self.assertRaises(ValueError):a(self.x)
        self.assertFalse(torch.equal(a(self.x,self.x),a(self.x,self.x+10)))
    def test_each_arm_forward_backward_repeat_and_serialized_resume(self):
        for kind in ["baseline","mqa","local","partial","gate"]:
            with self.subTest(kind=kind):
                full,state=train(kind);repeat,again=train(kind);first,part=train(kind,2);rest,resumed=train(kind,2,part)
                self.assertEqual(full,repeat);self.assertEqual(full,first+rest)
                for k,v in state["model"].items():self.assertTrue(torch.equal(v,again["model"][k]) and torch.equal(v,resumed["model"][k]),k)
    def test_right_padding_does_not_affect_valid_prefix(self):
        for kind in ["baseline","mqa","local","partial","gate"]:
            c,rows,lengths=spec(kind);a=LanguageModel(c["model"],rows,lengths);ids=torch.arange(8)[None,:];other=ids.clone();other[:,5:]=20;valid=torch.arange(8)[None,:]<5
            self.assertTrue(torch.equal(a(ids,valid)[:,:5],a(other,valid)[:,:5]),kind)

class AttentionConfigTests(unittest.TestCase):
    def test_all_four_runnable_arms(self):
        for name in ["attn1_mqa","attn2_swa128_sink","attn3_prope_half","attn4_gate"]:
            self.assertEqual(validate(load_runtime(TEAM/("configs/arms/"+name+".yaml"))),[])
        m=load_runtime(TEAM/"configs/arms/attn4_gate.yaml")["model"]
        self.assertEqual((m["attn_gate_input"],m["attn_gate_bias"],m["attn_gate_init"]),("normalized",False,"linear_default"))
    def test_invalid_attention_contracts_rejected(self):
        cases=[dict(attn_pattern=["L"]),dict(attn_pattern=["X","G"]),dict(attn_pattern=["L","G"],attn_window=0),dict(attn_pattern=["L","G"],attn_window=9),dict(attn_sink=True),dict(attn_window=3),dict(rotary_fraction=.3),dict(attn_gate=True),dict(attn_gate=False,attn_gate_init="zero")]
        for change in cases:
            c,_,_=fixture();c["model"].update(change)
            self.assertTrue(validate(c),change)
    def test_arm_fields_reach_model(self):
        c=load_runtime(TEAM/"configs/arms/attn2_swa128_sink.yaml")
        self.assertEqual(c["model"]["attn_pattern"],["L","L","L","G","L","L","L","G"])
        self.assertEqual(c["model"]["attn_window"],128);self.assertIs(c["model"]["attn_sink"],True)
        self.assertEqual(load_runtime(TEAM/"configs/arms/attn3_prope_half.yaml")["model"]["rotary_fraction"],.5)

if __name__=="__main__":unittest.main()
