"""Tests for sft_v1_manifest.py (G10): the SFT data v1 manifest and its #391 area budget.

    pytest teams/10-post-training/sft/test_sft_v1_manifest.py -q

Uses only files committed in sft/results (no data, no network).
"""

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sft_v1_manifest as man  # noqa: E402


def test_budget_anchors_on_code_and_sizes_every_area_from_its_share():
    sets = {"a": {"in_pack": True, "area": "code", "admission": {"tokens_kept": 350}},
            "b": {"in_pack": True, "area": "indic", "admission": {"tokens_kept": 30}},
            "c": {"in_pack": False, "area": "general", "admission": {"tokens_kept": 10**9}}}
    b = man.budget(sets, man.SHARES)
    assert b["total_at_anchor"] == 1000 and b["tokens_admitted_total"] == 380
    assert b["areas"]["indic"] == {**b["areas"]["indic"], "tokens_needed_at_code_anchor": 150, "shortfall_tokens": 120, "fill": 0.2}
    assert b["areas"]["general"]["tokens_admitted"] == 0  # a set that is not in the pack never counts
    assert b["areas"]["code"]["fill"] == 1.0 and b["areas"]["code"]["shortfall_tokens"] == 0
    assert sum(man.SHARES.values()) == pytest.approx(1.0) and sum(man.SHARES_NO_SAFETY.values()) == pytest.approx(1.0)


def test_the_committed_records_give_a_consistent_manifest(tmp_path):
    m = man.build(man.RESULTS, None)
    assert m["in_pack"] == ["sft-code-opencodereasoning-2", "sft-dolly-15k", "sft-indic-indic-align-dolly-t"]
    s = m["sets"]
    assert s["sft-math-nemotron-proofs"]["status"] == "decontam_pending" and not s["sft-math-nemotron-proofs"]["in_pack"]
    assert s["sft-math-nemotron-math-v2"]["in_pack"] is False
    for k in m["in_pack"]:
        assert s[k]["decontam"]["complete"] is True
        assert s[k]["over_length"]["kept_max_len"] <= man.MAX_LEN
    adm = s["sft-dolly-15k"]["admission"]
    conv = s["sft-dolly-15k"]["conversion"]
    assert adm["rows_kept"] + adm["rows_excluded"] == conv["rows"]
    b = m["budget_391"]
    assert b["areas"]["agentic"]["tokens_admitted"] == 0 and b["areas"]["tool_use"]["tokens_admitted"] == 0
    assert b["tokens_admitted_total"] == sum(s[k]["admission"]["tokens_kept"] for k in m["in_pack"])
    out = tmp_path / "m.json"
    assert man.main(["--tokenizer", "c3", "--out", str(out), "--mask-dir", str(tmp_path / "none")]) == 0
    assert json.loads(out.read_text())["schema"] == man.SCHEMA


def test_an_admission_bound_to_another_conversion_is_refused(tmp_path):
    for sub in ("sft_v1_admission", "sft_v1_records"):
        (tmp_path / sub).mkdir()
    name = "sft-dolly-15k"
    adm = json.loads((man.RESULTS / "sft_v1_admission" / f"{name}.admission.json").read_text())
    adm["record"]["content_sha256"] = "0" * 64
    (tmp_path / "sft_v1_admission" / f"{name}.admission.json").write_text(json.dumps(adm))
    rec = man.RESULTS / "sft_v1_records" / f"{name}.full.record.json"
    (tmp_path / "sft_v1_records" / rec.name).write_bytes(rec.read_bytes())
    with pytest.raises(AssertionError, match="another conversion"):
        man.from_admission(name, tmp_path, None)


def test_the_p1536_records_give_a_consistent_manifest(tmp_path):
    """The p1536 rebuild (16-17 Nov): same sets in the pack, every in-pack record is p1536, the context table adds up."""
    m = man.build(man.RESULTS, man.RESULTS / "sft_v1_mask_checks_p1536", "p1536")
    c3 = json.loads((man.RESULTS / "sft_data_v1_c3_manifest.json").read_text())
    assert m["in_pack"] == c3["in_pack"] == ["sft-code-opencodereasoning-2", "sft-dolly-15k", "sft-indic-indic-align-dolly-t"]
    s = m["sets"]
    for k in m["in_pack"]:
        assert s[k]["tokenizer_sha256"] == man.P1536_SHA256 and s[k]["decontam"]["complete"] is True
        removed = s[k].get("eval_firewall", {}).get("removed", {}).get("rows", 0)  # only OCR-2 has the firewall
        assert s[k]["admission"]["rows_kept"] + removed == c3["sets"][k]["admission"]["rows_kept"]  # same rows as C3
        assert s[k]["loss_mask"]["mask_ok"] is True
    fw = s["sft-code-opencodereasoning-2"]["eval_firewall"]
    assert fw["checks"] == "13 of 13" and fw["removed"]["rows"] > 0 and fw["token_share_removed"] < 0.02
    assert s["sft-dolly-15k"]["admission"]["kept_ids_sha256"] == c3["sets"]["sft-dolly-15k"]["admission"]["kept_ids_sha256"]
    for k in ("sft-math-nemotron-proofs", "sft-math-nemotron-math-v2"):
        assert s[k]["in_pack"] is False
    cl = m["context_length"]
    for L in man.LIMITS:
        fit = sum(t["by_limit"][L]["tokens_fit"] for t in cl["per_set"].values())
        assert fit == cl["budget_by_limit"][L]["tokens_fit_total"]
        assert sum(cl["by_area"][L][a]["tokens_fit"] for a in man.SHARES) == fit
    assert cl["budget_by_limit"]["32768"]["tokens_fit_total"] == m["budget_391"]["tokens_admitted_total"]
    assert 0 < cl["code_at_2048"]["tokens_fit_share"] < cl["code_at_2048"]["rows_fit_share"] < 1
    out = tmp_path / "m.json"
    assert man.main(["--out", str(out)]) == 0  # p1536 is the default
    assert json.loads(out.read_text())["tokenizer"]["name"] == "p1536"


def test_the_p1536_record_before_the_firewall_regenerates(tmp_path):
    """The 16 Nov p1536 manifest (before the evaluation firewall) is kept as a record and still regenerates."""
    rec = json.loads((man.RESULTS / "sft_data_v1_p1536_nofirewall_manifest.json").read_text())
    m = json.loads(json.dumps(man.build(man.RESULTS, man.RESULTS / "sft_v1_mask_checks_p1536", "p1536-nofirewall")))
    code = m["context_length"]["per_set"]["sft-code-opencodereasoning-2"]["table"]
    assert code["name"].endswith(".nofirewall.json")
    code["name"] = rec["context_length"]["per_set"]["sft-code-opencodereasoning-2"]["table"]["name"]  # renamed file
    assert m == rec
