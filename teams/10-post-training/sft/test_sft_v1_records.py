"""Tests for sft_v1_worklist.py, sft_v1_records.py and the batched path of convert.py.

Fixture rows are hand-written; the toy tokenizer is a character-level one built here, so no data and no external
tokenizer file is needed.
"""

from __future__ import annotations

import importlib.util
import json
import string
from pathlib import Path

import pytest

tokenizers = pytest.importorskip("tokenizers")
np = pytest.importorskip("numpy")

HERE = Path(__file__).resolve().parent

# A named decorator: pr-guard takes a dotted decorator line of a diff for an email address.
fixture = pytest.fixture
parametrize = pytest.mark.parametrize


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


convert = _load("g10_convert_t", "convert.py")
records = _load("g10_records_t", "sft_v1_records.py")
worklist = _load("g10_worklist_t", "sft_v1_worklist.py")
T = convert.T


@fixture(scope="module")
def toy_tokenizer(tmp_path_factory) -> str:
    """One token per character plus the nine chat markers as added (special) tokens."""
    from tokenizers import Regex, Tokenizer, decoders, models, normalizers, pre_tokenizers

    chars = string.printable + "éèàǜ"
    vocab = {c: i for i, c in enumerate(dict.fromkeys(chars))}
    vocab["[UNK]"] = len(vocab)
    tok = Tokenizer(models.WordLevel(vocab, unk_token="[UNK]"))
    tok.normalizer = normalizers.NFC()
    tok.pre_tokenizer = pre_tokenizers.Split(Regex("[\\s\\S]"), "isolated")
    tok.decoder = decoders.Fuse()
    tok.add_special_tokens([T[k] for k in ("endoftext", "im_start", "im_end", "think", "think_end", "tool_call",
                                           "tool_call_end", "tool_result", "tool_result_end")])
    path = tmp_path_factory.mktemp("tok") / "toy.json"
    tok.save(str(path))
    return str(path)


COMMIT = {"commit": "c", "instruction": "Write add(a, b).", "response": "def add(a, b):\n    return a + b\n"}
CODEFORCES = {"id": "1/A", "finish_reason": "stop", "messages": [
    {"role": "user", "content": "Sum two numbers."},
    {"role": "assistant", "content": "<think>\nRead, add.\n</think>\n\nprint(1 + 1)"}]}
AGENT = {"uuid": "u1", "tools": [{"name": "f", "parameters": {}}], "messages": [
    {"role": "user", "content": "Call f."},
    {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "f", "arguments": {"x": 1}}, "id": "c1"}]},
    {"role": "tool", "content": "42"},
    {"role": "assistant", "content": "It returned 42."}]}


def _write_rows(toy, set_id, rows, tmp_path, limit=None):
    out = tmp_path / "o.jsonl"
    with open(out, "w", encoding="utf-8") as sink:
        _, manifest = convert.convert(set_id, rows, limit, toy, 0, sink)
    return out, manifest


def test_batched_convert_equals_row_by_row(toy_tokenizer, tmp_path):
    """Chunked `encode_batch` gives the lines, counters and hash of one-row-at-a-time processing."""
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(toy_tokenizer)
    rows = [CODEFORCES, dict(CODEFORCES, finish_reason="length"), CODEFORCES] * 40  # 120 rows: several chunks, mixed skips
    _, manifest = _write_rows(toy_tokenizer, "sft-code-codeforces-cots", rows, tmp_path)
    digest, lines = __import__("hashlib").sha256(), 0
    skipped = {}
    for i, row in enumerate(rows):  # reference: the pre-batching loop, written out with convert_row
        try:
            effort, text, spans = convert.convert_row(convert.codeforces_cots(row), lambda t: len(tok.encode(t, add_special_tokens=False).ids))
        except convert.Skip as exc:
            skipped[str(exc)] = skipped.get(str(exc), 0) + 1
            continue
        enc = tok.encode(text, add_special_tokens=False)
        sample = {"id": f"sft-code-codeforces-cots/{i}", "set": "sft-code-codeforces-cots", "source_id": row["id"], "effort": effort,
                  "text": text, "train_spans": [list(s) for s in spans], "input_ids": enc.ids,
                  "loss_mask": convert.token_mask(spans, enc.offsets)}
        digest.update((json.dumps(sample, ensure_ascii=False) + "\n").encode("utf-8"))
        lines += 1
    assert manifest["rows"] == lines == 80 and manifest["skipped"] == skipped
    assert manifest["content_sha256"] == digest.hexdigest()


def test_limit_stops_inside_a_chunk(toy_tokenizer, tmp_path):
    _, manifest = _write_rows(toy_tokenizer, "sft-code-commitpackft", [COMMIT] * 100, tmp_path, limit=37)
    assert manifest["rows_in"] == 37 and manifest["rows_scanned"] == 37 and manifest["rows"] == 37


def test_record_checks_pass_on_clean_rows_and_count_tool_blocks(toy_tokenizer, tmp_path):
    out, _ = _write_rows(toy_tokenizer, "sft-agentic-nemotron-agentic-v1", [AGENT, dict(AGENT, uuid="u2")], tmp_path)
    res = records.check_files([out], toy_tokenizer)
    assert res["checks_ok"], res["checks_failed"]
    assert res["rows"] == 2 and res["tool_call_blocks"] == 2 and res["tool_result_blocks"] == 2
    assert res["train_spans"] == 4 and res["unique_ids"] and res["tool_call_tokens_untrained"] == 0
    assert 0 < res["trained_share"] < 1 and res["shifted_supervised_targets"] == res["trained_tokens"]


def _break_first_row(out: Path, edit) -> None:
    lines = out.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    edit(row)
    lines[0] = json.dumps(row, ensure_ascii=False)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_check_catches_a_trained_tool_result_token(toy_tokenizer, tmp_path):
    out, _ = _write_rows(toy_tokenizer, "sft-agentic-nemotron-agentic-v1", [AGENT], tmp_path)
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(toy_tokenizer)

    def edit(row):
        enc = tok.encode(row["text"], add_special_tokens=False)
        a = row["text"].index(T["tool_result"])
        i = next(k for k, (s, e) in enumerate(enc.offsets) if s >= a + len(T["tool_result"]) + 1 and e > s)
        row["loss_mask"][i] = 1

    _break_first_row(out, edit)
    res = records.check_files([out], toy_tokenizer)
    assert not res["checks_ok"]
    assert {"tool_result_token_trained", "trained_token_outside_span"} <= set(res["checks_failed"])


def test_check_catches_a_trained_eos_a_duplicate_id_and_changed_ids(toy_tokenizer, tmp_path):
    out, _ = _write_rows(toy_tokenizer, "sft-code-commitpackft", [COMMIT, COMMIT], tmp_path)
    lines = out.read_text(encoding="utf-8").splitlines()
    first, second = json.loads(lines[0]), json.loads(lines[1])
    first["loss_mask"][-1] = 1
    second["id"] = first["id"]
    second["input_ids"][5] = (second["input_ids"][5] + 1) % 50
    out.write_text("\n".join(json.dumps(r) for r in (first, second)) + "\n", encoding="utf-8")
    res = records.check_files([out], toy_tokenizer)
    assert {"eos_missing_or_trained", "duplicate_id", "input_ids_differ_from_fresh_encode", "decode_differs_from_text"} <= set(res["checks_failed"])


def test_check_catches_a_changed_effort_line(toy_tokenizer, tmp_path):
    out, _ = _write_rows(toy_tokenizer, "sft-code-commitpackft", [COMMIT], tmp_path)
    _break_first_row(out, lambda row: row.update(effort="64k"))
    assert "parse_effort_differs" in records.check_files([out], toy_tokenizer)["checks_failed"]


def test_normaliser_only_decode_difference_is_not_a_failure(toy_tokenizer, tmp_path):
    row = dict(COMMIT, response="café au lait")  # e + combining acute: NFC turns it into one character
    out, _ = _write_rows(toy_tokenizer, "sft-code-commitpackft", [row], tmp_path)
    res = records.check_files([out], toy_tokenizer)
    assert res["checks_ok"] and res["info"] == {"decode_equals_normalised_text_only": 1}


# --- work list -----------------------------------------------------------------------------------

def test_generator_flags():
    flags = worklist.generator_flags
    assert flags("sft-dolly-15k", "none (human-written; no model generator)") == []
    assert flags("sft-code-opencodereasoning", "DeepSeek-R1 (MIT, open weights)") == []
    assert flags("sft-x", "GPT-OSS-120B (Apache-2.0), Qwen3-32B (Apache-2.0)") == []
    assert "closed_model" in flags("sft-x", "GPT-4o (OpenAI, proprietary closed)")
    assert "use_restricted_or_llama" in flags("sft-x", "Llama-3.3-70B-Instruct (Llama 3.3 Community Licence)")
    assert "modified_mit_generator" in flags("sft-x", "Kimi-K2-Instruct (Modified MIT)")
    assert "unknown_generator" in flags("sft-x", "unknown generator")
    got = flags("sft-chat-nemotron-if-v1", "chat split open; structured-outputs split has unknown generator (exclude structured-outputs split)")
    assert "adapter_reads_unknown_generator_split:structured_outputs" in got


def test_worklist_rules_hold_on_the_branch_documents():
    w = worklist.build(None)
    by = {r["set"]: r for r in w["sets"]}
    assert by["sft-code-opencodereasoning-2"]["track"] == "owned"
    for r in w["sets"]:
        if r["decision_class"] == "excluded" or not r["adapter"] or not r["in_proposal_text"]:
            assert r["track"] in ("out", "owned"), r["set"]
        if r["track"] in ("allowed", "reserved"):
            assert not r["flags"] and r["adapter"] and r["in_proposal_text"] and r["decision_class"] != "excluded"
        if r["track"] == "allowed":
            assert r["decision"].startswith("allowed")
        if r["track"] == "reserved":
            assert r["decision"].startswith("TSAI reserves")
    assert by["sft-chat-nemotron-if-v1"]["track"] == "hold"
    assert set(w["lists"]["allowed"]).isdisjoint(w["lists"]["reserved"])
    assert w["counts"]["stage1_sets"] == len(w["sets"])


def test_convert_reads_the_pinned_revision(monkeypatch):
    seen = []

    class Boom(Exception):
        pass

    def fake_urlopen(url, timeout=0):
        seen.append(url if isinstance(url, str) else url.full_url)
        raise Boom

    monkeypatch.setattr(convert.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(convert, "REVISIONS", {"org/repo": "a" * 40})
    with pytest.raises(Boom):
        list(convert._one_file_rows("org/repo", "data/x.jsonl", 0, 1))
    with pytest.raises(Boom):
        list(convert._one_file_rows("other/repo", "data/x.jsonl", 0, 1))
    assert seen[0] == f"https://huggingface.co/datasets/org/repo/resolve/{'a' * 40}/data/x.jsonl"
    assert seen[1].endswith("/other/repo/resolve/main/data/x.jsonl")


def test_hub_byte_guard_stops_a_run(monkeypatch):
    monkeypatch.setenv("G10_MAX_HUB_BYTES", "100")
    monkeypatch.setattr(convert, "BYTES_READ", 101)
    with pytest.raises(SystemExit):
        convert._guard_bytes()
    monkeypatch.setattr(convert, "BYTES_READ", 99)
    convert._guard_bytes()


# --- ledger integration --------------------------------------------------------------------------

def _c3_rec(**kw):
    rec = {"set_id": "sft-dolly-15k", "scope": "first 1,000 rows, C3", "rows_in": 1000, "rows": 1000, "sequence_tokens": 193844,
           "shifted_supervised_targets": 84057, "tokenizer_sha256": "a" * 64, "content_sha256": "b" * 64,
           "length": {"p50": 129, "p95": 536, "max": 2549}, "rows_over_max_len": 0, "checks_ok": True}
    rec.update(kw)
    return rec


def test_ledger_takes_c3_records_with_their_own_scope(tmp_path):
    mi = _load("g10_mix_inventory_t", "mix_inventory.py")
    path = tmp_path / "c3.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in (
        _c3_rec(), _c3_rec(scope="full set, converted, not decontaminated", rows=15011),
        _c3_rec(set_id="sft-not-in-the-table"))) + "\n", encoding="utf-8")
    records = mi.collect(HERE.parent, None, None, path)
    c3 = [r for r in records if r["type"] == "c3_token_record"]
    assert [r["scope"] for r in c3] == ["first 1,000 rows, C3", "full set, converted, not decontaminated"]
    assert c3[0]["licence_decision"] == "allowed"
    meta = records[0]
    assert meta["counts"]["sets_with_c3_records"] == 1 and meta["counts"]["c3_records"] == 2
    assert any(r["type"] == "contradiction" and r["kind"] == "c3_record_set_not_in_licence_table" for r in records)
    md = mi.render_markdown(records)
    assert "## 8. C3 token records (WP14), by scope" in md and "not the current C3 pack state" in md
    assert mi.dump_jsonl(records) == mi.dump_jsonl(mi.collect(HERE.parent, None, None, path))  # deterministic
    # measured-token supply is untouched: a C3 record is not a kept-row record
    assert meta["counts"]["sets_with_measured_tokens"] == 1


def test_ledger_without_c3_records_has_no_section_8():
    mi = _load("g10_mix_inventory_t2", "mix_inventory.py")
    md = mi.render_markdown(mi.collect(HERE.parent, None, None))
    assert "## 8." not in md and "sets_with_c3_records" not in json.dumps(mi.collect(HERE.parent, None, None)[0])


def test_c3_record_needs_its_scope_and_hash(tmp_path):
    mi = _load("g10_mix_inventory_t3", "mix_inventory.py")
    bad = tmp_path / "bad.jsonl"
    rec = _c3_rec()
    del rec["scope"]
    bad.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        mi.read_c3_records(bad)


# --- guards of the full-conversion command -------------------------------------------------------

def test_only_the_c3_tokenizer_is_accepted(tmp_path):
    other = tmp_path / "other.json"
    other.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit):
        records.require_c3(str(other))
    records.require_c3(str(other), allow_other=True)


def test_the_default_pin_is_p1536_and_c3_needs_its_label(tmp_path):
    """New records use p1536 (TSAI froze it on 15 Nov 2026); a C3 file is refused unless C3 is asked for by name."""
    import argparse

    tok = tmp_path / "tok.json"
    tok.write_text("{}", encoding="utf-8")
    assert records.FROZEN_TOKENIZERS["p1536"] == "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
    assert records.DEFAULT_TOKENIZER == "p1536"
    with pytest.raises(SystemExit, match="pinned p1536 tokenizer"):
        records.require_tokenizer(str(tok))
    with pytest.raises(SystemExit, match="unknown tokenizer label"):
        records.require_tokenizer(str(tok), "c4")
    real = records.sha256_file(tok)
    pins = dict(records.FROZEN_TOKENIZERS)
    try:
        records.FROZEN_TOKENIZERS["c3"] = real  # stand-in: this file plays C3
        with pytest.raises(SystemExit):
            records.require_tokenizer(str(tok))  # still not p1536
        ns = argparse.Namespace(tokenizer=str(tok), tokenizer_label="c3", allow_other_tokenizer=False)
        assert records._tok_label(ns) == "C3"
    finally:
        records.FROZEN_TOKENIZERS.clear()
        records.FROZEN_TOKENIZERS.update(pins)


def test_global_budget_refuses_a_start_that_would_pass_it(tmp_path):
    import argparse

    (tmp_path / "earlier-set").mkdir()
    (tmp_path / "earlier-set" / "part0000.jsonl.gz").write_bytes(b"x" * 2_000_000)  # 2 MB already written by another set
    a = argparse.Namespace(set="sft-dolly-15k", tokenizer="unused", allow_other_tokenizer=True, threads=1, out_dir=str(tmp_path),
                           budget_gb=0.0005, global_budget_gb=0.002)  # 0.5 MB more would pass 2 MB (0.002 GiB = 2.1 MB)
    with pytest.raises(SystemExit) as err:
        records.cmd_full(a)
    assert "global budget" in str(err.value)


def test_verify_local_checks_the_pinned_sha256(tmp_path, capsys):
    import argparse
    import hashlib

    repo, name = "databricks/databricks-dolly-15k", "databricks-dolly-15k.jsonl"
    root = tmp_path / "hub"
    (root / repo).mkdir(parents=True)
    data = b'{"a": 1}\n'
    (root / repo / name).write_bytes(data)
    pins = {"datasets": {repo: {"sha": "a" * 40, "files": {name: {"size": len(data), "lfs_sha256": hashlib.sha256(data).hexdigest()}}}}}
    pin_file = tmp_path / "pins.json"
    pin_file.write_text(json.dumps(pins), encoding="utf-8")
    a = argparse.Namespace(set="sft-dolly-15k", root=str(root), revisions_json=str(pin_file))
    assert records.cmd_verify_local(a) == 0
    (root / repo / name).write_bytes(b'{"a": 2}\n')  # same size, different bytes
    assert records.cmd_verify_local(a) == 1
    assert "DIFFER" in capsys.readouterr().out


# --- finalize / check-parts ----------------------------------------------------------------------

def _make_full_output(toy, tmp_path, n_rows=7, rows_per_part=3):
    """A finished `full` output for a toy set: gzip parts of real convert.py lines, plus the manifest convert.py writes."""
    import gzip as gz
    import hashlib as hl

    set_id, repo = "sft-code-commitpackft", "bigcode/commitpackft"
    rows = [dict(COMMIT, commit=f"c{i}", response=f"def f{i}(a):\n    return a + {i}\n") for i in range(n_rows)]
    lines, manifest = convert.convert(set_id, rows, None, toy)
    out_dir = tmp_path / "full" / set_id
    out_dir.mkdir(parents=True)
    names = []
    for k in range(0, len(lines), rows_per_part):
        name = f"{set_id}.part{k // rows_per_part:04d}.jsonl"
        with gz.open(out_dir / f"{name}.gz", "wb") as f:
            f.write("".join(lines[k:k + rows_per_part]).encode("utf-8"))
        names.append(name)
    tsha = hl.sha256(Path(toy).read_bytes()).hexdigest()
    manifest.update(parts=names, input="hub file test", index_base=0, hub_revision="a" * 40)
    assert manifest["effort_counter"] == f"tokenizer sha256 {tsha}"
    (out_dir / f"{set_id}.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"datasets": {repo: {"sha": "a" * 40, "files": {}}}}), encoding="utf-8")
    return set_id, out_dir, pins, manifest


def _fin_args(toy, tmp_path, set_id, pins, **kw):
    import argparse

    base = dict(set=set_id, tokenizer=toy, revisions_json=str(pins), out_dir=str(tmp_path / "full"), record_dir=str(tmp_path / "rec"),
                partials_dir=tmp_path / "partials", no_reuse=False, rerun_rows=0, threads=1, max_hub_gb=1.0, local_root=None,
                status="converted, not decontaminated; not a pack", allow_other_tokenizer=True)
    base.update(kw)
    return argparse.Namespace(**base)


def test_finalize_writes_the_record_that_a_single_pass_check_gives(toy_tokenizer, tmp_path):
    set_id, out_dir, pins, manifest = _make_full_output(toy_tokenizer, tmp_path)
    parts = sorted(out_dir.glob("*.gz"))
    one_pass = records.check_files(parts, toy_tokenizer)
    # stored per-part checks for the first two parts only: the third is checked inside finalize
    a = _fin_args(toy_tokenizer, tmp_path, set_id, pins, max_seconds=None)
    tok, tsha = records.load_tok(toy_tokenizer), records.sha256_file(Path(toy_tokenizer))
    for gz in parts[:2]:
        records.write_json_atomic(records.partial_path(a.partials_dir, gz), records.check_part(gz, tok, tsha))
    assert records.cmd_finalize(a) == 0
    rec = json.loads((tmp_path / "rec" / f"{set_id}.full.record.json").read_text(encoding="utf-8"))
    assert rec["checks"] == one_pass and rec["content_sha256"] == manifest["content_sha256"]
    assert rec["finalized"]["parts_reused_from_stored_checks"] == 2 and rec["finalized"]["parts_checked_here"] == 1
    assert rec["convert"]["wall_s"] is None and rec["convert"]["max_rss_mb"] is None and rec["rows_per_s_convert"] is None
    assert [p["name"] for p in rec["parts"]] == [p.name for p in parts] and rec["rows_out"] == 7
    assert not list((tmp_path / "rec").glob("*.tmp"))
    with pytest.raises(SystemExit):  # a record is never overwritten
        records.cmd_finalize(a)


def test_merge_counts_a_duplicate_id_across_parts_once_like_a_single_pass(toy_tokenizer, tmp_path):
    import gzip as gz

    set_id, out_dir, pins, _ = _make_full_output(toy_tokenizer, tmp_path, n_rows=4, rows_per_part=2)
    first = (out_dir / f"{set_id}.part0000.jsonl.gz")
    copy = tmp_path / "dup.part0001.jsonl.gz"
    copy.write_bytes(first.read_bytes())  # the same two ids again, in another file
    res = records.check_files([first, copy], toy_tokenizer)
    assert res["checks_failed"] == {"duplicate_id": 2} and not res["unique_ids"]
    assert records.check_files([first], toy_tokenizer)["checks_ok"]


@parametrize("damage", ["missing_manifest", "extra_part", "wrong_content_sha", "wrong_revision", "wrong_tokenizer_note", "corrupt_gzip",
                        "row_count", "missing_part"])
def test_finalize_refuses_a_damaged_output_and_writes_nothing(toy_tokenizer, tmp_path, damage):
    set_id, out_dir, pins, manifest = _make_full_output(toy_tokenizer, tmp_path)
    mpath = out_dir / f"{set_id}.manifest.json"
    if damage == "missing_manifest":
        mpath.unlink()
    elif damage == "extra_part":
        (out_dir / f"{set_id}.part0099.jsonl.gz").write_bytes(b"")
    elif damage == "missing_part":
        (out_dir / f"{set_id}.part0001.jsonl.gz").unlink()
    elif damage in ("wrong_content_sha", "row_count", "wrong_tokenizer_note"):
        key, val = {"wrong_content_sha": ("content_sha256", "0" * 64), "row_count": ("rows", 99),
                    "wrong_tokenizer_note": ("effort_counter", "tokenizer sha256 " + "1" * 64)}[damage]
        mpath.write_text(json.dumps(dict(manifest, **{key: val})), encoding="utf-8")
    elif damage == "wrong_revision":
        pins.write_text(json.dumps({"datasets": {"bigcode/commitpackft": {"sha": "b" * 40, "files": {}}}}), encoding="utf-8")
    elif damage == "corrupt_gzip":
        path = out_dir / f"{set_id}.part0001.jsonl.gz"
        raw = bytearray(path.read_bytes())
        raw[len(raw) // 2] ^= 0xFF  # a flipped byte inside the compressed stream
        path.write_bytes(bytes(raw))
    import zlib

    with pytest.raises((SystemExit, OSError, EOFError, zlib.error)):
        records.cmd_finalize(_fin_args(toy_tokenizer, tmp_path, set_id, pins))
    assert not (tmp_path / "rec" / f"{set_id}.full.record.json").exists()


def test_a_stored_check_is_ignored_when_its_part_changed_or_the_checker_changed(toy_tokenizer, tmp_path):
    set_id, out_dir, pins, _ = _make_full_output(toy_tokenizer, tmp_path)
    gz = sorted(out_dir.glob("*.gz"))[0]
    tok, tsha = records.load_tok(toy_tokenizer), records.sha256_file(Path(toy_tokenizer))
    pdir = tmp_path / "partials"
    part = records.check_part(gz, tok, tsha)
    records.write_json_atomic(records.partial_path(pdir, gz), part)
    assert records.load_valid_partial(pdir, gz, tsha) is not None
    assert records.load_valid_partial(pdir, gz, "f" * 64) is None  # other tokenizer
    records.write_json_atomic(records.partial_path(pdir, gz), dict(part, checker_version="old"), overwrite=True)
    assert records.load_valid_partial(pdir, gz, tsha) is None  # other checker
    records.write_json_atomic(records.partial_path(pdir, gz), part, overwrite=True)
    gz.write_bytes(gz.read_bytes() + b"\0")  # trailing byte: different file
    assert records.load_valid_partial(pdir, gz, tsha) is None


@parametrize("dependency", ["renderer", "markers", "tokenizers", "max_len"])
def test_stored_check_is_rejected_after_a_dependency_changes(toy_tokenizer, tmp_path, monkeypatch, dependency):
    _, out_dir, _, _ = _make_full_output(toy_tokenizer, tmp_path)
    gz = sorted(out_dir.glob("*.gz"))[0]
    tok, tsha = records.load_tok(toy_tokenizer), records.sha256_file(Path(toy_tokenizer))
    pdir = tmp_path / "partials"
    records.write_json_atomic(records.partial_path(pdir, gz), records.check_part(gz, tok, tsha))
    assert records.load_valid_partial(pdir, gz, tsha) is not None
    if dependency == "renderer":
        changed = tmp_path / "render_changed.py"
        changed.write_bytes(Path(records.render.__file__).read_bytes() + b"\n# changed renderer revision\n")
        monkeypatch.setattr(records.render, "__file__", str(changed))
    elif dependency == "markers":
        assignments = dict(records.render.ASSIGNED_SURFACES)
        key = next(iter(assignments))
        name, surface = assignments[key]
        assignments[key] = (name, surface + "changed")
        monkeypatch.setattr(records.render, "ASSIGNED_SURFACES", assignments)
    elif dependency == "tokenizers":
        import tokenizers
        monkeypatch.setattr(tokenizers, "__version__", tokenizers.__version__ + "-changed")
    else:
        monkeypatch.setattr(records, "MAX_LEN", records.MAX_LEN + 1)
    assert records.load_valid_partial(pdir, gz, tsha) is None


def test_complete_gz_parts_skips_a_part_whose_plain_file_still_exists(tmp_path):
    d = tmp_path / "s"
    d.mkdir()
    (d / "s.part0000.jsonl.gz").write_bytes(b"x")
    (d / "s.part0001.jsonl.gz").write_bytes(b"x")  # being written: its plain part has not been removed yet
    (d / "s.part0001.jsonl").write_bytes(b"x")
    (d / "s.part0002.jsonl.tmp").write_bytes(b"x")
    assert [p.name for p in records.complete_gz_parts(d, "s")] == ["s.part0000.jsonl.gz"]


def test_atomic_cache_writers_use_distinct_temporary_files(tmp_path, monkeypatch):
    """Opposing part-check workers can finish the same part at the same instant."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    path = tmp_path / "part.check.json"
    barrier = Barrier(2)
    replace = records.os.replace
    sources = []

    def simultaneous_replace(source, target):
        sources.append(str(source))
        barrier.wait(timeout=5)
        return replace(source, target)

    monkeypatch.setattr(records.os, "replace", simultaneous_replace)
    payloads = [{"writer": i, "payload": str(i) * 2048} for i in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(records.write_json_atomic, path, obj, overwrite=True) for obj in payloads]
        for future in futures:
            future.result(timeout=10)
    assert len(set(sources)) == 2
    assert json.loads(path.read_text()) in payloads
    assert not list(tmp_path.glob("*.tmp"))


def test_atomic_record_refuses_a_concurrent_second_finalizer(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    path = tmp_path / "full.record.json"
    barrier = Barrier(2)
    link = records.os.link

    def simultaneous_link(source, target):
        barrier.wait(timeout=5)
        return link(source, target)

    def publish(value):
        try:
            records.write_json_atomic(path, {"writer": value})
        except SystemExit as error:
            assert "not overwritten" in str(error)
            return "refused"
        return "published"

    monkeypatch.setattr(records.os, "link", simultaneous_link)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish, i) for i in range(2)]
        outcomes = [f.result(timeout=10) for f in futures]
    assert sorted(outcomes) == ["published", "refused"]
    assert json.loads(path.read_text())["writer"] in (0, 1)
    assert not list(tmp_path.glob("*.tmp"))


def test_record_rejects_untrained_tokens_inside_a_tool_call(toy_tokenizer, tmp_path):
    from tokenizers import Tokenizer

    out, _ = _write_rows(toy_tokenizer, "sft-agentic-nemotron-agentic-v1", [AGENT], tmp_path)
    row = json.loads(out.read_text())
    enc = Tokenizer.from_file(toy_tokenizer).encode(row["text"], add_special_tokens=False)
    start = row["text"].index(T["tool_call"])
    end = row["text"].index(T["tool_call_end"], start) + len(T["tool_call_end"])
    token = next(i for i, (a, b) in enumerate(enc.offsets) if start < a < b < end and row["loss_mask"][i])
    row["loss_mask"][token] = 0
    out.write_text(json.dumps(row) + "\n")
    result = records.check_files([out], toy_tokenizer)
    assert result["tool_call_tokens_untrained"] == 1
    assert not result["checks_ok"]
    assert result["checks_failed"]["tool_call_token_untrained"] == 1
