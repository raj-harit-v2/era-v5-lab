"""Tests for pack_admission.py (G10): a diagnostic permission is never a training admission.

    G10_DECONTAM_TOOLS=<lab main>/teams/09-evaluation/decontam pytest teams/10-post-training/sft/test_pack_admission.py -q

No network. Rows are synthetic placeholders from ocr2_fixtures.py and a toy fingerprint set: tests only.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import convert as g10  # noqa: E402
import pack_admission as pack  # noqa: E402
import run_ocr2  # noqa: E402
from ocr2_fixtures import (SET_ID, World, allow_everything, ocr_row, read_jsonl, statement, toy_fingerprints,  # noqa: E402
                           toy_tokenizer)

# Named decorators: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize
module_fixture = pytest.fixture(scope="module")

ALL_TRAIN = ("taco/train", "apps/train", "code_contests/train")
ROWS = [ocr_row(0, "apps", "test", "0"),            # upstream test row: never joined
        ocr_row(1, "taco", "train", "0"),
        ocr_row(2, "code_contests", "train", "0"),  # its statement quotes a toy benchmark item: removed by the scan
        ocr_row(3, "taco", "train", "3"),
        ocr_row(4, "apps", "train", "1")]
LIMIT = 4096


def allowed_row():
    return dict(g10.licence_row(SET_ID), decision="allowed")


@module_fixture
def kit(tmp_path_factory):
    root = tmp_path_factory.mktemp("kit")
    return {"tokenizer": (root / "tokenizer.json", toy_tokenizer(root / "tokenizer.json")), "toy": toy_fingerprints(root / "fp")}


@module_fixture
def diagnostic(tmp_path_factory, kit):
    root = tmp_path_factory.mktemp("diagnostic")
    world = World(root / "w", {0: ROWS}, n_shards=1, verified=ALL_TRAIN, **kit)
    coverage = run_ocr2.run(world.manifest_path, world.policy_path, "0", 1, root / "run")
    return world, coverage, root / "run" / "shards" / "shard-00000"


@module_fixture
def admission(tmp_path_factory, kit):
    """A run where every approval exists: the licence table (patched), the policy, verified sources."""
    root = tmp_path_factory.mktemp("admission")
    world = World(root / "w", {0: ROWS}, n_shards=1, verified=ALL_TRAIN, max_sequence_tokens=LIMIT, **kit)
    allow_everything(world)
    with pytest.MonkeyPatch.context() as patch:
        row = allowed_row()
        patch.setattr(g10, "licence_row", lambda set_id, table=None: row)
        coverage = run_ocr2.run(world.manifest_path, world.policy_path, "0", 1, root / "run", mode="admission")
    return world, coverage, root / "run" / "shards" / "shard-00000"


def real_pack_manifest(tmp_path, admission, monkeypatch):
    """A copy of the admission shard with a pack manifest that does not carry the fixture flag.

    Only a test may do this: it shows the gate opens when, and only when, nothing is missing.
    """
    world, _, shard = admission
    row = allowed_row()
    monkeypatch.setattr(g10, "licence_row", lambda set_id, table=None: row)
    copy = tmp_path / "shard"
    shutil.copytree(shard, copy)
    policy = tmp_path / "policy.json"
    shutil.copy(world.policy_path, policy)
    manifest = json.loads((copy / "pack" / "pack_manifest.json").read_text())
    manifest.update(test_fixture=False, policy=str(policy))
    path = copy / "manual" / "pack_manifest.json"
    path.parent.mkdir()
    path.write_text(json.dumps(manifest))
    return copy, path, policy


def rewrite(path, change):
    value = json.loads(path.read_text())
    change(value)
    path.write_text(json.dumps(value, indent=1) + "\n")


# --- run level ---------------------------------------------------------------------------------

def test_report_mode_names_the_blockers_and_writes_no_rows(diagnostic, tmp_path):
    _, coverage, shard = diagnostic
    counts = coverage["shards"][0]["counts"]["pack"]
    assert coverage["shards"][0]["final_state"] == "pack_report"
    assert (counts["attempted"], counts["row_checks_passed"], counts["admitted"], counts["emitted"]) == (3, 3, 0, 0)
    assert not counts["training_admissible"]
    assert {"set_not_allowed_in_policy", "set_not_allowed_in_licence_table", "join_not_in_admission_mode", "test_fixture_run",
            "context_limit_not_set", "source_not_approved_for_training:taco"} <= set(counts["blockers"])
    assert sorted(p.name for p in (shard / "pack").iterdir()) == ["pack_manifest.json", "pack_report.json"]
    out = tmp_path / "pack.jsonl"
    code = pack.main(["--manifest", str(shard / "pack" / "pack_manifest.json"), "--mode", "training", "--out", str(out)])
    assert code == 3 and list(tmp_path.iterdir()) == []  # refused: no pack, no partial file, no admission record


def test_a_fixture_run_is_never_a_training_pack(admission):
    _, coverage, shard = admission
    info = coverage["shards"][0]
    assert info["state"] == "complete" and info["final_state"] == "pack_refused"
    assert info["counts"]["pack"]["blockers"] == ["test_fixture_run"]  # every other approval is present
    assert (info["counts"]["pack"]["row_checks_passed"], info["counts"]["pack"]["admitted"], info["counts"]["pack"]["emitted"]) == (3, 0, 0)
    assert not (shard / "pack" / "pack.jsonl").exists() and not (shard / "pack" / "pack.jsonl.tmp").exists()
    assert run_ocr2.mode_refused(coverage)


def test_with_every_approval_the_checked_rows_are_admitted_byte_for_byte(admission, tmp_path, monkeypatch):
    copy, manifest, _ = real_pack_manifest(tmp_path, admission, monkeypatch)
    out = tmp_path / "pack.jsonl"
    report = pack.evaluate(manifest, "training", out)
    assert report["training_admissible"] and report["blockers"] == []
    assert (report["attempted"], report["row_checks_passed"], report["pack_rejected"], report["admitted"], report["emitted"]) == (3, 3, 0, 3, 3)
    assert out.read_bytes() == (copy / "screen" / f"{SET_ID}.clean.jsonl").read_bytes()
    assert report["pack_sha256"] == pack.si.sha256_file(out) and report["context_limit"] == LIMIT
    assert report["passed_rows"]["by_source"] == {"apps/train": 1, "taco/train": 2}
    assert report["passed_rows"]["shifted_assistant_targets"] > 0 and report["passed_rows"]["unique_families"] == 3
    again = pack.evaluate(manifest, "report")
    assert again["training_admissible"] and again["admitted"] == 0 and again["emitted"] == 0  # a report admits nothing


def policy_change(change):
    return lambda copy, manifest, policy: rewrite(policy, change)


def record_change(change):
    return lambda copy, manifest, policy: rewrite(copy / "screen" / f"{SET_ID}.record.json", change)


def manifest_change(change):
    return lambda copy, manifest, policy: rewrite(manifest, change)


def append_line(relative):
    def breaker(copy, manifest, policy):
        path = copy / relative
        path.write_bytes(path.read_bytes() + path.read_bytes().splitlines(keepends=True)[0])
    return breaker


@parametrize("breaker,blocker", [
    (policy_change(lambda p: p["teacher"].update(model="")), "teacher_unknown_or_not_approved"),
    (policy_change(lambda p: p["teacher"].update(approved=False)), "teacher_unknown_or_not_approved"),
    (policy_change(lambda p: p["sources"]["taco"].update(training_approved=False)), "source_not_approved_for_training:taco"),
    (policy_change(lambda p: p["sources"]["apps"].update(statement_licence="")), "source_terms_or_attribution_unknown:apps"),
    (policy_change(lambda p: p["sources"]["taco"].update(attribution="")), "source_terms_or_attribution_unknown:taco"),
    (policy_change(lambda p: p.update(set_decision="TSAI reserves")), "set_not_allowed_in_policy"),
    (policy_change(lambda p: p["pack"].update(approved_tokenizer_sha256=[])), "tokenizer_not_approved"),
    (policy_change(lambda p: p["pack"].update(approved_fingerprint_set_sha256=[])), "fingerprint_set_not_approved"),
    (policy_change(lambda p: p.update(note="any edit after the join")), "policy_changed_since_join"),
    (manifest_change(lambda m: m.update(max_sequence_tokens=None)), "context_limit_not_set"),
    (manifest_change(lambda m: m.update(tokenizer=None)), "tokenizer_missing"),
    (manifest_change(lambda m: m.pop("test_fixture")), "test_fixture_run"),
    (manifest_change(lambda m: m.update(decontam_record=None)), "scan_record_missing"),
    (record_change(lambda r: r.update(rows_canary=1)), "canary_found_or_scan_incomplete"),
    (record_change(lambda r: r["recheck_on_clean"].update(flagged=1)), "second_pass_missing_or_has_hits"),
    (record_change(lambda r: r.update(recheck_on_clean=None)), "second_pass_missing_or_has_hits"),
    (record_change(lambda r: r.update(scope="benchmarks: toy")), "scan_scope_not_full_set"),
    (record_change(lambda r: r.update(clean_files_deleted=True)), "clean_file_was_dropped"),
    (record_change(lambda r: r["checks"].update(ids_unique=False)), "scan_not_ok"),
    (append_line(f"screen/{SET_ID}.clean.jsonl"), "retained_file_not_the_scanned_clean_file"),
    (append_line("rendered/rendered.jsonl"), "scan_ran_on_another_render"),
    (append_line("join/joined.sidecar.jsonl"), "sidecar_not_the_joined_one"),
    (lambda copy, manifest, policy: rewrite(copy / "join" / "join_manifest.json", lambda j: j.update(mode="diagnostic")),
     "join_not_in_admission_mode"),
])
def test_one_missing_approval_closes_the_gate(admission, tmp_path, monkeypatch, breaker, blocker):
    copy, manifest, policy = real_pack_manifest(tmp_path, admission, monkeypatch)
    breaker(copy, manifest, policy)
    out = tmp_path / "out" / "pack.jsonl"
    out.parent.mkdir()
    try:
        report = pack.evaluate(manifest, "training", out)
    except pack.PackError:
        assert blocker == "sidecar_not_the_joined_one"  # a sidecar that names an id twice is not read at all
        report = None
    if report is not None:
        assert blocker in report["blockers"] and not report["training_admissible"]
        assert report["admitted"] == 0 and report["emitted"] == 0 and report["pack_sha256"] is None
    assert list(out.parent.iterdir()) == []
    assert pack.main(["--manifest", str(manifest), "--mode", "training", "--out", str(out)]) in (2, 3)
    assert list(out.parent.iterdir()) == []


def test_the_licence_table_is_read_and_decides(admission, tmp_path, monkeypatch):
    _, manifest, _ = real_pack_manifest(tmp_path, admission, monkeypatch)
    monkeypatch.undo()  # the real table again: TSAI reserves
    report = pack.evaluate(manifest, "training", tmp_path / "pack.jsonl")
    assert {"set_not_allowed_in_licence_table", "policy_and_licence_table_disagree"} <= set(report["blockers"])
    assert not (tmp_path / "pack.jsonl").exists()


# --- row level ---------------------------------------------------------------------------------

def test_row_checks(diagnostic):
    world, _, shard = diagnostic
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(world.tokenizer))
    policy = world.policy
    rows = read_jsonl(shard / "screen" / f"{SET_ID}.clean.jsonl")
    sidecar = {e["rendered_id"]: e for e in read_jsonl(shard / "join" / "joined.sidecar.jsonl")}
    row = rows[0]
    entry = sidecar[row["id"]]
    size = len(row["input_ids"])

    def outcome(r=row, e=entry, t=tok, limit=None):
        return pack.row_outcome(r, e, policy, t, limit)[0]

    assert pack.row_outcome(row, entry, policy, tok, None) == ("passed_row_checks", size, sum(row["loss_mask"][1:]))
    assert outcome(limit=size) == "passed_row_checks" and outcome(limit=size - 1) == "rejected_context_overflow"
    assert outcome(e=None) == "rejected_unmapped_id"
    assert outcome(r={**row, "source_id": "fx9999"}) == "rejected_identity_mismatch"
    assert outcome(r={**row, "set": "sft-other"}) == "rejected_identity_mismatch"
    assert outcome(e={**entry, "split_membership": "test"}) == "rejected_protected_split"
    assert outcome(r={**row, "train_spans": []}) == "rejected_no_target_span"
    assert outcome(r={k: v for k, v in row.items() if k != "input_ids"}) == "rejected_not_tokenized"
    assert outcome(t=None) == "rejected_not_tokenized"
    flipped = [1 - row["loss_mask"][0]] + row["loss_mask"][1:]
    assert outcome(r={**row, "loss_mask": flipped}) == "rejected_mask_mismatch"
    assert outcome(r={**row, "input_ids": row["input_ids"][:-1], "loss_mask": row["loss_mask"][:-1]}) == "rejected_mask_mismatch"
    assert outcome(r={**row, "text": row["text"].replace(statement("T0"), statement("T1"))}) == "rejected_mask_mismatch"


def test_a_row_with_no_shifted_assistant_target_is_rejected(diagnostic):
    world, _, shard = diagnostic
    row = read_jsonl(shard / "screen" / f"{SET_ID}.clean.jsonl")[0]
    entry = {e["rendered_id"]: e for e in read_jsonl(shard / "join" / "joined.sidecar.jsonl")}[row["id"]]
    span = tuple(row["train_spans"][0])

    class OneTokenTarget:
        """A tokenizer whose only token is the whole assistant span: its mask is [1], and mask[1:] is empty."""

        def encode(self, text, add_special_tokens=False):
            return type("Encoding", (), {"ids": [7], "offsets": [span]})()

    lone = {**row, "input_ids": [7], "loss_mask": [1]}
    assert pack.row_outcome(lone, entry, world.policy, OneTokenTarget(), None)[0] == "rejected_empty_shifted_target"


def test_rejected_rows_are_counted_and_the_counts_conserve(admission, tmp_path, monkeypatch):
    copy, manifest, _ = real_pack_manifest(tmp_path, admission, monkeypatch)
    clean = copy / "screen" / f"{SET_ID}.clean.jsonl"
    rows = read_jsonl(clean)
    longest = max(len(r["input_ids"]) for r in rows)
    rewrite(manifest, lambda m: m.update(max_sequence_tokens=longest - 1))
    report = pack.evaluate(manifest, "report")
    assert report["row_outcomes"]["rejected_context_overflow"] >= 1
    assert report["attempted"] == 3 == report["pack_rejected"] + report["row_checks_passed"]
    clean.write_bytes(clean.read_bytes() + clean.read_bytes().splitlines(keepends=True)[0])  # one id twice
    report = pack.evaluate(manifest, "report")
    assert report["row_outcomes"]["rejected_duplicate_id"] == 1 and report["attempted"] == 4
    assert {"retained_file_not_the_scanned_clean_file", "retained_row_count_differs_from_scan_record"} <= set(report["blockers"])
