"""Independent BPB tests; no G6 model or training corpus required."""
from contextlib import nullcontext
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
import torch
TEAM=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TEAM/"harness"))
from week2.data import DocumentWindows,BatchStream
from week2.evaluation import evaluate

class ByteFixture:
    # UTF-8 bytes themselves are fixture IDs; NOT the real tokenizer.
    bos_id=256
    pad_id=257
    lengths=[1]*256+[0,0]
    def encode(self,text):return list(text.encode("utf8"))

class UniformModel(torch.nn.Module):
    def forward(self,x,valid):return torch.zeros(*x.shape,258,device=x.device)

class BPBTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/"heldout.jsonl"
        self.texts=["Hello world!", "नमस्ते", "ଓଡ଼ିଆ", "a"]
        self.path.write_text("\n".join(json.dumps({"text":t},ensure_ascii=False) for t in self.texts)+"\n",encoding="utf8")
        self.ds=DocumentWindows(self.path,ByteFixture(),7)
    def tearDown(self):self.tmp.cleanup()
    def score(self,batch=1,model=None):return evaluate(model or UniformModel(),self.ds,batch,torch.device("cpu"),nullcontext)
    def test_exact_utf8_byte_conservation(self):
        self.assertEqual(self.ds.raw_bytes,sum(len(t.encode("utf8")) for t in self.texts))
        self.assertEqual(sum(sum(w[2]) for w in self.ds.windows),self.ds.raw_bytes)
    def test_uniform_distribution_known_answer(self):
        result=self.score()
        self.assertAlmostEqual(result["val/bpb"],math.log2(258),places=5)
        self.assertEqual(result["val/scored_tokens"],self.ds.raw_bytes)
    def test_batch_partition_invariance(self):
        a=self.score(1);b=self.score(3)
        self.assertEqual(a,b)
    def test_first_and_tail_tokens_are_scored_once(self):
        rebuilt=[]
        for x,y,lengths in self.ds.windows:rebuilt.extend(y)
        self.assertEqual(rebuilt,list("".join(self.texts).encode("utf8")))
    def test_padding_is_not_scored(self):
        x,y,b=self.ds.batch(range(len(self.ds.windows)),torch.device("cpu"))
        self.assertTrue((y==-100).any())
        self.assertTrue(torch.equal(b[y==-100],torch.zeros_like(b[y==-100])))
        self.assertEqual(int((y!=-100).sum()),self.ds.tokens)
    def test_eval_preserves_training_mode_and_rng(self):
        model=UniformModel();model.train();torch.manual_seed(1234)
        state=torch.get_rng_state().clone();self.score(model=model)
        self.assertTrue(model.training);self.assertTrue(torch.equal(state,torch.get_rng_state()))
    def test_isolated_sampler_repeatability(self):
        a=BatchStream(self.ds,3,1234);b=BatchStream(self.ds,3,1234)
        for _ in range(5):
            for x,y in zip(a.next(torch.device("cpu")),b.next(torch.device("cpu"))):self.assertTrue(torch.equal(x,y))
    def test_empty_input_rejected(self):
        self.path.write_text("",encoding="utf8")
        with self.assertRaises(ValueError):DocumentWindows(self.path,ByteFixture(),7)

if __name__=="__main__":unittest.main()
