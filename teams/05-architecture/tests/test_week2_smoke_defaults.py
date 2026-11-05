"""Smoke follows runtime unless a caller explicitly selects a resolution."""
from pathlib import Path
import copy,json,subprocess,sys,tempfile,unittest
from unittest.mock import patch
TEAM=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TEAM/"harness"))
from train_week2 import resolve_run_config
from week2.config import load_runtime,validate

class SmokeDefaultsTests(unittest.TestCase):
    def cfg(self):return load_runtime(TEAM/"configs/arms/exp1/lr_1e-3.yaml")
    def test_default_preserves_all_runtime_settings_and_does_not_read_fixture(self):
        c=self.cfg()
        with patch("train_week2.load",side_effect=AssertionError("Implicit file read")):
            result=resolve_run_config(c,None,True)
        self.assertEqual(c,result);self.assertEqual(result["model"]["norm_eps"],1e-5)
        self.assertEqual(result["model"]["rope_theta"],10000);self.assertEqual(validate(result),[])
    def test_future_runtime_value_not_replaced_with_hardcoded_epsilon(self):
        c=self.cfg();c["model"]["norm_eps"]=2e-5
        self.assertEqual(resolve_run_config(c,None,True)["model"]["norm_eps"],2e-5)
    def test_resolution_result_is_independent(self):
        c=self.cfg();result=resolve_run_config(c,None,True);result["model"]["norm_eps"]=.01
        self.assertEqual(c["model"]["norm_eps"],1e-5)
    def test_default_does_not_grant_approvals(self):
        c=self.cfg();result=resolve_run_config(c,None,True)
        self.assertEqual(result["approval"],c["approval"]);self.assertEqual(result["evaluation"],c["evaluation"])
        self.assertEqual(result["approval"]["status"],"pending");self.assertIs(result["evaluation"]["approved"],False)
    def test_explicit_development_resolution_still_applies(self):
        result=resolve_run_config(self.cfg(),TEAM/"configs/small/smoke_resolution.yaml",True)
        self.assertEqual(result["model"]["norm_eps"],1e-6)
    def test_non_smoke_without_resolution_still_rejected(self):
        with self.assertRaisesRegex(ValueError,"supply an agreed resolution"):resolve_run_config(self.cfg(),None,False)
    def test_explicit_resolution_keeps_allowlist_and_conflict_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"resolution.yaml";p.write_text("model: {n_embd: 64}\n")
            with self.assertRaisesRegex(ValueError,"fixed sizes"):resolve_run_config(self.cfg(),p,True)
            c=self.cfg();c["provenance"]["lead_explicit_choices"]["model.norm_eps"]=1e-5;p.write_text("model: {norm_eps: 0.000001}\n")
            with self.assertRaisesRegex(ValueError,"conflicts"):resolve_run_config(c,p,True)
    def test_explicit_empty_resolution_works_for_non_smoke_config_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"resolution.yaml";p.write_text("{}\n")
            result=resolve_run_config(self.cfg(),p,False)
            self.assertEqual(result["model"]["norm_eps"],1e-5)
            self.assertIs(result["evaluation"]["approved"],False)

if __name__=="__main__":unittest.main()
