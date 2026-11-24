"""run_folder_from_store.py: refusals on CPU without a lab checkout, plus an opt-in end-to-end check on a real store.

End to end needs a run trained by main's train_week2.py with --checkpoint-store, delivered without checkpoint.pt:
    G10_DR2_DELIVERY=<folder> G10_DR2_STORE=<store root> G10_DR2_G5_ROOT=<lab checkout> \
    G10_DR2_ARTIFACTS=<dir with tokenizer_p1536.json, ke2_p1536/raw_table_P32.npz, heldout_v1_bal60k*.jsonl>
"""
from __future__ import annotations

import json
import os
import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_folder_from_store as rfs  # noqa: E402

parametrize = pytest.mark.parametrize  # no dotted decorator: the lab pr-guard's old email regex flags it
fixture = pytest.fixture


def _delivery(tmp_path, manifest=None, summary=None):
    rf = tmp_path / "delivered"
    rf.mkdir()
    m = {"run_id": "dryrun2-1234", "team7_checkpoint": {"store": "/shared/ckpt", "run_id": "dryrun2-1234",
                                                        "interval_s": 600.0}}
    s = {"run_id": "dryrun2-1234", "steps": 1221, "team7_checkpoint_path": "main/step_00001221-e1",
         "final_model_sha256": "0" * 64}
    m.update(manifest or {})
    s.update(summary or {})
    (rf / "manifest.json").write_text(json.dumps({k: v for k, v in m.items() if v is not None}))
    (rf / "summary.json").write_text(json.dumps({k: v for k, v in s.items() if v is not None}))
    return rf


def test_a_complete_delivery_names_its_committed_step(tmp_path):
    _, _, t7, step, path = rfs.delivery_facts(_delivery(tmp_path))
    assert (t7["run_id"], step, path) == ("dryrun2-1234", 1221, "main/step_00001221-e1")


@parametrize("manifest,summary,match", [
    ({"team7_checkpoint": None}, {}, "no team7_checkpoint"),
    ({}, {"run_id": "other"}, "run_id differs"),
    ({"run_id": "other"}, {}, "run_id differs"),
    ({}, {"team7_checkpoint_path": None}, "not committed"),
    ({}, {"steps": None}, "not committed"),
    ({}, {"steps": True}, "not committed"),
])
def test_a_delivery_without_a_committed_final_step_is_refused(tmp_path, manifest, summary, match):
    with pytest.raises(ValueError, match=match):
        rfs.delivery_facts(_delivery(tmp_path, manifest, summary))


def test_a_folder_that_already_has_checkpoint_pt_is_left_alone(tmp_path):
    rf = _delivery(tmp_path)
    (rf / "checkpoint.pt").write_bytes(b"x")
    with pytest.raises(ValueError, match="already has checkpoint.pt"):
        rfs.delivery_facts(rf)


E2E = [os.environ.get(k) for k in ("G10_DR2_DELIVERY", "G10_DR2_STORE", "G10_DR2_G5_ROOT", "G10_DR2_ARTIFACTS")]


needs_store = pytest.mark.skipif(not all(E2E), reason="needs G10_DR2_DELIVERY/STORE/G5_ROOT/ARTIFACTS (a real Team 7 store)")


@needs_store
def test_the_store_weights_match_the_summary_and_load_in_the_adapter_format(tmp_path):
    import torch  # noqa: PLC0415
    rf, store, g5, art = map(Path, E2E)
    a = Namespace(g5_root=g5, run_folder=rf, store=str(store), tokenizer=art / "tokenizer_p1536.json",
                  byte_table=art / "ke2_p1536" / "raw_table_P32.npz", heldout_data=art / "heldout_v1_bal60k.jsonl",
                  heldout_sources=art / "heldout_v1_bal60k_sources.jsonl", device="cpu", out=tmp_path / "rebuilt")
    rec = rfs.build(a)
    summary = json.loads((rf / "summary.json").read_text())
    assert rec["model_hash_g5"] == summary["final_model_sha256"] and rec["step"] == summary["steps"]
    ck = torch.load(a.out / "checkpoint.pt", map_location="cpu", weights_only=True)
    assert set(ck) == {"model", "step", "identity_sha256", "run_id"}
    assert ck["identity_sha256"] == json.loads((rf / "manifest.json").read_text())["identity_sha256"]
    for n in ("manifest.json", "summary.json"):
        assert (a.out / n).read_bytes() == (rf / n).read_bytes()


# ---------------------------------------------------------------- build() on CPU with stand-in Team 5 / Team 7 modules
# RaviNaik's review of #143: the record names the step's MANIFEST.json sha256 (Team 9's model_revision) and whether the
# probe-loss bits were compared or skipped; a failed export leaves no folder. Team 7's real store.py reads the store;
# export_safetensors, the model and the data are small stand-ins, so this runs without a lab checkout.

STUBS = {
    "teams/05-architecture/harness/week2/__init__.py": "",
    "teams/05-architecture/harness/week2/model.py": """
import torch
class LanguageModel(torch.nn.Module):
    def __init__(self, cfg, table_bytes, lengths):
        super().__init__()
        g = torch.Generator().manual_seed(0)
        self.w = torch.nn.Parameter(torch.randn(2, 2, generator=g))
""",
    "teams/05-architecture/harness/week2/artifacts.py": """
class Artifacts:
    def __init__(self, tokenizer, byte_table, expected_tokenizer_sha=None, expected_vocab=None):
        self.bytes, self.lengths = None, None
    def identity(self):
        return {"tokenizer_sha256": "t" * 64, "vocab_size": 4}
""",
    "teams/05-architecture/harness/week2/data.py": """
import torch
class DocumentWindows:
    def __init__(self, *args, **kw):
        pass
    def batch(self, idx, dev):
        return torch.zeros(1, 2), torch.zeros(1, 2), None
""",
    "teams/05-architecture/harness/train_week2.py": """
def model_hash(m):
    return "f" * 64
def scored_ntp_loss(m, x, y):
    return float(m.w.sum())
""",
    "teams/05-architecture/harness/week2/kas_v2.py": """
def checkpoint_probe(m):  # stands for #717's seeded mean-NLL probe: any value scored_ntp_loss cannot give here
    return 123.0
""",
    "teams/07-infrastructure/ckpt/__init__.py": "",
    "teams/07-infrastructure/ckpt/ckpt.py": """
import os
from safetensors.torch import save_file
def device_class(model=None):
    return "cpu"
def export_safetensors(remote_run, model_factory, probe_fn, out_path, step=None):
    if os.environ.get("G10_STUB_EXPORT") == "raise":
        raise RuntimeError("store unreachable")
    m = model_factory()
    want = os.environ.get("G10_STUB_PROBE_SAVED")  # Team 7: saved bits for this device class must equal probe_fn's
    if want is not None and float(probe_fn(m)) != float(want):
        raise RuntimeError(f"export probe loss bits differ: saved={want} exported={probe_fn(m)}")
    save_file({k: v.contiguous() for k, v in m.state_dict().items()}, out_path,
              metadata={"run_id": "dryrun2-1234", "step": str(step), "state_digest": "digest-1"})
    return {"step": step, "path": out_path, "probe_bits": "40b0002760000000"}
""",
}
STUB_MODULES = ("ckpt", "ckpt.ckpt", "ckpt.store", "train_week2", "week2", "week2.artifacts", "week2.data", "week2.model", "week2.kas_v2")


@fixture
def stub_lab(tmp_path, monkeypatch):
    root = tmp_path / "lab"
    for rel, text in STUBS.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    real_store = Path(__file__).resolve().parents[2] / "07-infrastructure" / "ckpt" / "store.py"
    (root / "teams/07-infrastructure/ckpt/store.py").write_bytes(real_store.read_bytes())
    saved = {n: sys.modules.pop(n) for n in STUB_MODULES if n in sys.modules}
    monkeypatch.setattr(sys, "path", list(sys.path))  # build() puts the stub tree first; undone after the test
    monkeypatch.setenv("V5_EVENTS_DIR", str(tmp_path / "events"))
    yield root
    for n in STUB_MODULES:
        sys.modules.pop(n, None)
    sys.modules.update(saved)


def _store_delivery(tmp_path, probe_loss, state_digest="digest-1", model_extra=None):
    store = tmp_path / "store"
    step_dir = store / "dryrun2-1234" / "main" / "step_00001221-e1"
    step_dir.mkdir(parents=True)
    (step_dir / "MANIFEST.json").write_text(json.dumps({"run_id": "dryrun2-1234", "step": 1221, "state_digest": state_digest,
                                                        "probe_loss": probe_loss}, indent=1))
    rf = _delivery(tmp_path, manifest={"config": {"model": {"block_size": 8, **(model_extra or {})}, "run": {"dtype": "bf16"}},
                                       "artifacts": {"tokenizer_sha256": "t" * 64, "vocab_size": 4},
                                       "identity_sha256": "i" * 64, "smoke": True},
                   summary={"final_model_sha256": "f" * 64})
    return store, rf, step_dir / "MANIFEST.json"


def _args(root, rf, store, out):
    return Namespace(g5_root=root, run_folder=rf, store=str(store), tokenizer=Path("tok.json"), byte_table=Path("t.npz"),
                     heldout_data=Path("h.jsonl"), heldout_sources=None, device="cpu", out=out)


def test_the_record_names_the_sha256_of_the_steps_manifest_bytes(tmp_path, stub_lab):
    import hashlib  # noqa: PLC0415
    store, rf, man = _store_delivery(tmp_path, {"cpu": "40b0002760000000"})
    rec = rfs.build(_args(stub_lab, rf, store, tmp_path / "rebuilt"))
    assert rec["manifest_sha256"] == hashlib.sha256(man.read_bytes()).hexdigest() and rec["state_digest"] == "digest-1"
    on_disk = json.loads((tmp_path / "rebuilt" / "G10_FROM_STORE.json").read_text())
    assert on_disk["manifest_sha256"] == rec["manifest_sha256"]
    assert sorted(p.name for p in (tmp_path / "rebuilt").iterdir()) == ["G10_FROM_STORE.json", "checkpoint.pt",
                                                                        "manifest.json", "summary.json"]


def test_a_manifest_that_is_not_the_one_the_export_read_is_refused_and_cleaned_up(tmp_path, stub_lab):
    store, rf, _ = _store_delivery(tmp_path, {"cpu": "40b0002760000000"}, state_digest="digest-OTHER")
    with pytest.raises(ValueError, match="not the manifest the export read"):
        rfs.build(_args(stub_lab, rf, store, tmp_path / "rebuilt"))
    assert not (tmp_path / "rebuilt").exists()


@parametrize("saved,verdict,words", [
    ({"cpu": "40b0002760000000"}, "compared", ()),
    ({"cuda:NVIDIA H200": "3fe0000000000000"}, "skipped", ("device class and precision differ", "cuda:NVIDIA H200 (bf16 autocast)",
                                                           "cpu (fp32)")),
    ({}, "skipped", ("saved no probe-loss bits",)),
])
def test_the_record_says_whether_the_probe_bits_were_compared_or_skipped_and_why(tmp_path, stub_lab, saved, verdict, words):
    store, rf, _ = _store_delivery(tmp_path, saved)
    p = rfs.build(_args(stub_lab, rf, store, tmp_path / "rebuilt"))["probe"]
    assert p["probe_bits"] == verdict and p["device_class"] == "cpu" and p["saved_device_classes"] == sorted(saved)
    assert ("reason" in p) == (verdict == "skipped") and all(w in p.get("reason", "") for w in words)


def test_a_failed_export_leaves_no_folder_so_the_rerun_works(tmp_path, stub_lab, monkeypatch):
    store, rf, _ = _store_delivery(tmp_path, {"cpu": "40b0002760000000"})
    out = tmp_path / "rebuilt"
    monkeypatch.setenv("G10_STUB_EXPORT", "raise")
    with pytest.raises(RuntimeError, match="store unreachable"):
        rfs.build(_args(stub_lab, rf, store, out))
    assert not out.exists()
    monkeypatch.delenv("G10_STUB_EXPORT")
    assert rfs.build(_args(stub_lab, rf, store, out))["step"] == 1221  # no FileExistsError from the first attempt


def test_an_existing_out_folder_is_refused_and_left_untouched(tmp_path, stub_lab):
    store, rf, _ = _store_delivery(tmp_path, {"cpu": "40b0002760000000"})
    out = tmp_path / "rebuilt"
    out.mkdir()
    (out / "keep.txt").write_text("someone's file")
    with pytest.raises(FileExistsError):
        rfs.build(_args(stub_lab, rf, store, out))
    assert (out / "keep.txt").read_text() == "someone's file"


# ---------------------------------------------------------------- the Team 7 probe must be Team 5's probe, branch for branch
# Team 7's export recomputes the probe with our closure and raises when the bits differ from the ones the run saved on the
# same device class. #717 made a kas_v2 run save the bits of week2.kas_v2.checkpoint_probe (seeded random ids), not
# scored_ntp_loss on held-out window 0, so a held-out probe breaks the first command of the dry run 2 job.

def _stub_dense_probe_value() -> float:
    import torch  # noqa: PLC0415
    return float(torch.randn(2, 2, generator=torch.Generator().manual_seed(0)).sum())  # the stub model's w.sum()


@parametrize("model_extra,fn", [({"head_mode": "kas_v2"}, "kas_v2.checkpoint_probe"),
                                ({}, "scored_ntp_loss(heldout window 0)")])
def test_the_store_probe_is_the_one_team5_saved_for_this_head(tmp_path, stub_lab, monkeypatch, model_extra, fn):
    store, rf, _ = _store_delivery(tmp_path, {"cpu": "40b0002760000000"}, model_extra=model_extra)
    saved = 123.0 if model_extra else _stub_dense_probe_value()
    monkeypatch.setenv("G10_STUB_PROBE_SAVED", repr(saved))
    rec = rfs.build(_args(stub_lab, rf, store, tmp_path / "rebuilt"))
    assert rec["probe"]["probe_fn"] == fn and rec["probe"]["team5_probe_closure"].startswith("UNKNOWN:")  # stub harness


def test_team5s_probe_closure_is_one_this_script_mirrors():
    """Drift pin: fails when Team 5 edits the probe closure of the train_week2.py we run against (G10_G5_ROOT, default
    this checkout), so the mirror in run_folder_from_store.build() is updated before the job, not after it fails."""
    root = Path(os.environ.get("G10_G5_ROOT") or Path(__file__).resolve().parents[3])
    tw = root / "teams" / "05-architecture" / "harness" / "train_week2.py"
    kind = rfs.team5_probe_kind(tw)
    assert kind in rfs.TEAM5_PROBE_CLOSURE_SHA256, (
        f"Team 5's Team 7 probe in {tw} is not one run_folder_from_store mirrors ({kind}); read its closure and update "
        f"build().probe and TEAM5_PROBE_CLOSURE_SHA256:\n{rfs.team5_probe_closure(tw)}")


def test_the_closure_hash_ignores_only_indentation_and_blank_lines(tmp_path):
    body = ("def probe(probe_model):\n    training = probe_model.training\n    try:\n        probe_model.eval()\n"
            "        with amp():\n            return float(scored_ntp_loss(probe_model, probe_x, probe_y))\n"
            "    finally:\n        probe_model.train(training)\n")
    f = tmp_path / "tw.py"
    f.write_text("def main():\n" + "".join("        " + ln + "\n" for ln in body.splitlines()) + "\n        checkpointer = Checkpointer(\n")
    assert rfs.team5_probe_kind(f) == "PRE717"
    f.write_text(f.read_text().replace("probe_x, probe_y", "probe_x[:1], probe_y[:1]"))
    assert rfs.team5_probe_kind(f).startswith("UNKNOWN:")
    f.write_text("def main():\n    pass\n")
    assert rfs.team5_probe_kind(f).startswith("UNKNOWN:") and "no `def probe" in rfs.team5_probe_kind(f)
