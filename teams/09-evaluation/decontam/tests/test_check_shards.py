"""Tests for check_shards.py and fetch_shards.py (G9).

    pytest teams/09-evaluation/decontam/tests/test_check_shards.py -q

They test the parts that do not need a real shard: the reference table, the comparison, the order of the shards,
the cut into parts, resume, the exit code, and the download step (with a fake opener, no network). check_one (which
calls decode_shard.py, decontam_check.py and canary_scan.py) is replaced by a stub where a test needs no shard. The
three scripts have their own tests.
"""

import hashlib
import io
import json
from pathlib import Path

import pytest

import check_shards as cs
import fetch_shards as fs

pq = pytest.importorskip("pyarrow.parquet")
pa = pytest.importorskip("pyarrow")

SHA_A = "a" * 64
SHA_B = "b" * 64


def result(shard_id, sha=SHA_A, docs=10, tokens=100, flagged=0, canary_hits=0):
    return {"shard_id": shard_id, "payload_sha256": sha, "docs": docs, "tokens": tokens, "dataset_version": "v0",
            "split": "train", "tokenizer_sha256": "t" * 64, "fingerprints_version": "v2", "set_sha256": "5" * 64,
            "scope": "full set", "flagged": flagged, "flagged_doc_ids": [], "canaries_checked": 4,
            "canary_hits": canary_hits, "canary_hit_list": [], "parts": 1, "seconds": 0.1}


# ---- check_shards.py ----
def test_read_reference_reads_rows_with_and_without_a_number_column(tmp_path):
    p = tmp_path / "ref.md"
    p.write_text("| # | shard_id | payload_sha256 | docs | tokens | flagged | canary hits |\n"
                 "|---:|---|---|---:|---:|---:|---:|\n"
                 f"| 1 | `code-go-train-000000` | `{SHA_A}` | 56,588 | 56,698,571 | 0 | 0 |\n"
                 f"| `ind-hi-x-train-000000` | `{SHA_B}` | 14,483 | 9,254,413 | 0 | 0 |\n"
                 f"| 9 | `code-go-train-000000` | `{SHA_B}` | 1 | 1 | 0 | 0 |\n"
                 "| not | a | row |\n")
    ref = cs.read_reference(p)
    assert ref == {"code-go-train-000000": (SHA_A, 56588, 56698571),   # the first row of a shard counts
                   "ind-hi-x-train-000000": (SHA_B, 14483, 9254413)}


def test_compare_lists_each_mismatch():
    ref = {"s-train-000000": (SHA_A, 10, 100)}
    assert cs.compare(result("s-train-000000"), ref) == []
    issues = cs.compare(result("s-train-000000", sha=SHA_B, docs=11), ref)
    assert len(issues) == 2 and issues[0].startswith("payload_sha256") and issues[1].startswith("docs")
    assert cs.compare(result("other-train-000000"), ref) == ["no row in the --compare file"]


def test_table_marks_mismatch():
    ref = {"s-train-000000": (SHA_A, 10, 100)}
    lines = cs.table([result("s-train-000000"), result("s-train-000000", tokens=99)], ref).splitlines()
    assert lines[2].endswith("| yes |")
    assert "NO: tokens 99 != 100" in lines[3]


def make_shards(tmp_path, sizes):
    """Fake shard files: {shard_id: .bin size}. The manifest holds the payload sha256 of the result stub."""
    folder = tmp_path / "in"
    folder.mkdir()
    for shard_id, size in sizes.items():
        (folder / f"{shard_id}.bin").write_bytes(b"x" * size)
        for ext in (".idx.npy", ".docs.parquet"):
            (folder / f"{shard_id}{ext}").write_bytes(b"x")
        (folder / f"{shard_id}.json").write_text(json.dumps({"payload_sha256": SHA_A}))
    tok = tmp_path / "tokenizer.json"
    tok.write_text("{}")
    return folder, tok


def test_find_shards_puts_the_biggest_first_and_lists_incomplete(tmp_path):
    folder, _ = make_shards(tmp_path, {"a-train-000000": 5, "b-train-000000": 50, "c-train-000000": 20})
    (folder / "d-train-000000.bin").write_bytes(b"x")  # no other file: an incomplete download
    ids, incomplete = cs.find_shards(folder)
    assert ids == ["b-train-000000", "c-train-000000", "a-train-000000"]
    assert incomplete == ["d-train-000000"]


def test_split_parts_keeps_every_document_once_in_order(tmp_path):
    n_tokens = [5, 1, 30, 2, 2, 8, 1, 1, 40, 3]
    t = pa.table({"doc_id": [f"d{i}" for i in range(10)], "text": [f"text {i}" for i in range(10)],
                  "n_tokens": n_tokens})
    src = tmp_path / "s-train-000000.text.parquet"
    pq.write_table(t, src)
    # Parts hold whole documents, so a big document can take the place of several parts: at most ceil(93 / n).
    for part_tokens, max_parts in ((1000, 1), (40, 3), (1, 10)):
        parts = cs.split_parts(src, part_tokens, tmp_path)
        assert 1 <= len(parts) <= max_parts
        assert all(pq.read_metadata(p).num_rows > 0 for p in parts)
        got = [r for p in parts for r in pq.read_table(p).column("doc_id").to_pylist()]
        assert got == [f"d{i}" for i in range(10)]
        assert pq.read_table(parts[0]).column_names == ["doc_id", "text"]
        for p in parts:
            p.unlink()


def fake_set(tmp_path, sha="5" * 64, name="fp"):
    """A folder with only the MANIFEST.json that check_shards.py reads set_sha256 from (the stubs never load it)."""
    d = tmp_path / name
    d.mkdir(exist_ok=True)
    (d / "MANIFEST.json").write_text(json.dumps({"version": "v2", "set_sha256": sha}))
    return d


def run_main(tmp_path, folder, tok, work, *extra):
    fp = [] if "--fingerprints" in extra else ["--fingerprints", str(fake_set(tmp_path))]
    return cs.main([str(folder), "--tokenizer", str(tok), "--work", str(tmp_path / work), "--jobs", "2", *fp,
                    *extra])


def test_resume_skips_done_shard_and_force_reruns(tmp_path, monkeypatch):
    folder, tok = make_shards(tmp_path, {"a-train-000000": 1, "b-train-000000": 1})
    calls = []

    def fake(shard_id, a, tok_sha, pool):
        calls.append(shard_id)
        r = result(shard_id)
        r["tokenizer_sha256"] = tok_sha
        return r

    monkeypatch.setattr(cs, "check_one", fake)
    assert run_main(tmp_path, folder, tok, "w") == 0
    assert sorted(calls) == ["a-train-000000", "b-train-000000"]
    calls.clear()
    assert run_main(tmp_path, folder, tok, "w") == 0
    assert calls == []
    assert run_main(tmp_path, folder, tok, "w", "--force", "--only", "b-train-000000") == 0
    assert calls == ["b-train-000000"]
    # A changed shard (new payload in its manifest) is checked again.
    (folder / "a-train-000000.json").write_text(json.dumps({"payload_sha256": SHA_B}))
    calls.clear()
    run_main(tmp_path, folder, tok, "w")
    assert calls == ["a-train-000000"]


def test_exit_code_1_on_hit_failure_mismatch_or_missing_file(tmp_path, monkeypatch):
    folder, tok = make_shards(tmp_path, {"a-train-000000": 1})
    monkeypatch.setattr(cs, "check_one", lambda s, a, t, p: result(s, flagged=1))
    assert run_main(tmp_path, folder, tok, "w1") == 1
    monkeypatch.setattr(cs, "check_one", lambda s, a, t, p: result(s, canary_hits=1))
    assert run_main(tmp_path, folder, tok, "w2") == 1

    def fail(s, a, t, p):
        raise cs.CheckError("decode_shard.py failed")

    monkeypatch.setattr(cs, "check_one", fail)
    assert run_main(tmp_path, folder, tok, "w3") == 1
    assert not (tmp_path / "w3" / "results" / "a-train-000000.json").exists()

    ref = tmp_path / "ref.md"
    ref.write_text(f"| 1 | `a-train-000000` | `{SHA_B}` | 10 | 100 | 0 | 0 |\n")
    monkeypatch.setattr(cs, "check_one", lambda s, a, t, p: result(s))
    assert run_main(tmp_path, folder, tok, "w4", "--compare", str(ref)) == 1
    ref.write_text(f"| 1 | `a-train-000000` | `{SHA_A}` | 10 | 100 | 0 | 0 |\n")
    assert run_main(tmp_path, folder, tok, "w5", "--compare", str(ref)) == 0

    (folder / "a-train-000000.idx.npy").unlink()
    assert run_main(tmp_path, folder, tok, "w6") == 1


def test_unknown_only_id_is_usage_error(tmp_path):
    folder, tok = make_shards(tmp_path, {"a-train-000000": 1})
    with pytest.raises(SystemExit) as e:
        run_main(tmp_path, folder, tok, "w", "--only", "missing-train-000000")
    assert e.value.code == 2


def test_default_jobs_is_at_least_one():
    assert cs.default_jobs() >= 1


# ---- fetch_shards.py ----
def test_read_links_skips_comments_and_header(tmp_path):
    p = tmp_path / "links.tsv"
    p.write_text("# comment line\nfile\turl\nx-train-000000.bin\thttps://h/x.bin?sig=1\n"
                 "x-train-000000.json\thttps://h/x.json\n\ny-train-000001.bin\thttps://h/y.bin\n")
    links = fs.read_links(p)
    assert links["x-train-000000.bin"] == "https://h/x.bin?sig=1"
    assert "file" not in links
    assert fs.shard_ids(links) == ["x-train-000000", "y-train-000001"]


def fake_store(shard_id, bad_bin=False):
    data = {".bin": b"payload", ".idx.npy": b"index", ".docs.parquet": b"docs"}
    manifest = {"payload_sha256": hashlib.sha256(data[".bin"]).hexdigest(),
                "index_sha256": hashlib.sha256(data[".idx.npy"]).hexdigest(),
                "sample_metadata_sha256": hashlib.sha256(data[".docs.parquet"]).hexdigest()}
    if bad_bin:
        data[".bin"] = b"cut"
    store = {f"https://h/{shard_id}{ext}": body for ext, body in data.items()}
    store[f"https://h/{shard_id}.json"] = json.dumps(manifest).encode()
    return store


def links_file(tmp_path, store):
    p = tmp_path / "links.tsv"
    p.write_text("file\turl\n" + "".join(f"{u.rsplit('/', 1)[1]}\t{u}\n" for u in store))
    return p


def test_fetch_downloads_checks_and_skips_good_files(tmp_path):
    store = fake_store("a-train-000000")
    calls = []

    def opener(url, timeout=None):
        calls.append(url)
        return io.BytesIO(store[url])

    links, out = links_file(tmp_path, store), tmp_path / "out"
    assert fs.main([str(links), "--out", str(out)], opener=opener) == 0
    assert sorted(p.name for p in out.iterdir()) == ["a-train-000000.bin", "a-train-000000.docs.parquet",
                                                      "a-train-000000.idx.npy", "a-train-000000.json"]
    calls.clear()
    assert fs.main([str(links), "--out", str(out)], opener=opener) == 0
    assert calls == ["https://h/a-train-000000.json"]  # only the manifest again: the data files match it


def test_fetch_replaces_an_old_manifest_with_the_same_shard_name(tmp_path):
    out = tmp_path / "out"
    old = fake_store("a-train-000000")
    fs.main([str(links_file(tmp_path, old)), "--out", str(out)], opener=lambda u, timeout=None: io.BytesIO(old[u]))
    new = {u: (b if not u.endswith(".bin") else b"new payload") for u, b in old.items()}
    m = json.loads(new["https://h/a-train-000000.json"])
    m["payload_sha256"] = hashlib.sha256(b"new payload").hexdigest()
    new["https://h/a-train-000000.json"] = json.dumps(m).encode()
    assert fs.main([str(links_file(tmp_path, new)), "--out", str(out)],
                   opener=lambda u, timeout=None: io.BytesIO(new[u])) == 0
    assert (out / "a-train-000000.bin").read_bytes() == b"new payload"


def test_fetch_refuses_a_file_with_the_wrong_sha256(tmp_path, monkeypatch):
    monkeypatch.setattr(fs, "RETRY_SLEEP", 0)
    store = fake_store("a-train-000000", bad_bin=True)
    out = tmp_path / "out"
    code = fs.main([str(links_file(tmp_path, store)), "--out", str(out)],
                   opener=lambda url, timeout=None: io.BytesIO(store[url]))
    assert code == 1
    assert not (out / "a-train-000000.bin").exists() and not (out / "a-train-000000.bin.part").exists()


def test_old_text_is_deleted_at_the_start(tmp_path, monkeypatch):
    folder, tok = make_shards(tmp_path, {"a-train-000000": 1})
    text = tmp_path / "w" / "text"
    text.mkdir(parents=True)
    for name in ("a-train-000000.text.parquet", "a-train-000000.part000.text.parquet", "x.text.parquet.tmp"):
        (text / name).write_text("document text")
    monkeypatch.setattr(cs, "check_one", lambda s, a, t, p: result(s))
    assert run_main(tmp_path, folder, tok, "w") == 0
    assert list(text.iterdir()) == []


def test_no_text_is_left_when_a_step_fails(tmp_path, monkeypatch):
    """check_one with a decode that writes text and a split that fails: the decoded text is deleted."""
    folder, tok = make_shards(tmp_path, {"a-train-000000": 1})
    work = tmp_path / "w"

    def fake_run(cmd):
        out = Path(cmd[cmd.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "a-train-000000.text.parquet").write_text("document text")
        return 0, json.dumps({"out": str(out / "a-train-000000.text.parquet"), "payload_sha256": SHA_A, "docs": 1,
                              "tokens": 1, "dataset_version": "v0", "split": "train"}), ""

    def bad_split(*args):
        raise OSError("disk full")

    monkeypatch.setattr(cs, "run", fake_run)
    monkeypatch.setattr(cs, "split_parts", bad_split)
    assert run_main(tmp_path, folder, tok, "w") == 1
    assert list((work / "text").iterdir()) == []


# ---- the fingerprint set ----
def test_resume_checks_again_when_the_fingerprint_set_changes(tmp_path, monkeypatch):
    folder, tok = make_shards(tmp_path, {"a-train-000000": 1})
    calls = []

    def fake(shard_id, a, tok_sha, pool):
        calls.append(shard_id)
        r = result(shard_id)
        r["tokenizer_sha256"] = tok_sha
        r["set_sha256"] = json.loads((a.fingerprints / "MANIFEST.json").read_text())["set_sha256"]
        return r

    monkeypatch.setattr(cs, "check_one", fake)
    set_1, set_2 = fake_set(tmp_path, "1" * 64, "set1"), fake_set(tmp_path, "2" * 64, "set2")
    assert run_main(tmp_path, folder, tok, "w", "--fingerprints", str(set_1)) == 0
    assert run_main(tmp_path, folder, tok, "w", "--fingerprints", str(set_1)) == 0
    assert calls == ["a-train-000000"]  # same set: the result is kept
    assert run_main(tmp_path, folder, tok, "w", "--fingerprints", str(set_2)) == 0
    assert calls == ["a-train-000000", "a-train-000000"]  # another set: checked again
    saved = json.loads((tmp_path / "w" / "results" / "a-train-000000.json").read_text())
    assert saved["set_sha256"] == "2" * 64


def test_a_result_from_another_set_fails_the_run(tmp_path, monkeypatch):
    folder, tok = make_shards(tmp_path, {"a-train-000000": 1})
    monkeypatch.setattr(cs, "check_one", lambda s, a, t, p: result(s))  # set_sha256 "5" * 64
    assert run_main(tmp_path, folder, tok, "w", "--fingerprints", str(fake_set(tmp_path, "9" * 64, "x"))) == 1


def test_a_folder_without_a_set_is_a_usage_error(tmp_path):
    folder, tok = make_shards(tmp_path, {"a-train-000000": 1})
    (tmp_path / "empty").mkdir()
    with pytest.raises(SystemExit) as e:
        run_main(tmp_path, folder, tok, "w", "--fingerprints", str(tmp_path / "empty"))
    assert e.value.code == 2


def test_planted_leaks_are_caught_through_the_parts(tmp_path, monkeypatch):
    """The real decontam_check.py and canary_scan.py on a small set: a benchmark text and the lab canary planted in
    documents of different parts are found, with their doc_id, and nothing else (check 3 of decontam_shards.md).
    Only the decode is replaced, because a real decode needs a real shard and the frozen tokenizer."""
    import fpset
    from lab_canary import LAB_CANARY

    item = ("the old stone bridge over the quiet river was built by farmers who carried every rock "
            "from the hills above the village")
    fp_dir = tmp_path / "set"
    fpset.write_benchmark(fp_dir, "bench", [("bench:test:0", {"prose": [item]})], {"prose": 13, "code": 20},
                          {"name": "Bench", "tags": ["english"]})
    fpset.write_index(fp_dir)

    filler = "numbers letters and other plain words in a clean training document number"
    texts = [f"{filler} {i}" for i in range(12)]
    texts[5] = f"{filler} five. A story: {item}. The end."
    texts[10] = f"{filler} ten {LAB_CANARY} more words"
    shard_id = "a-train-000000"
    folder, tok = make_shards(tmp_path, {shard_id: 1})
    real_run = cs.run

    def run(cmd):
        if not cmd[1].endswith("decode_shard.py"):
            return real_run(cmd)
        out = Path(cmd[cmd.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{shard_id}.text.parquet"
        pq.write_table(pa.table({"doc_id": [f"d{i}" for i in range(12)], "text": texts, "n_tokens": [10] * 12}), path)
        return 0, json.dumps({"out": str(path), "payload_sha256": SHA_A, "docs": 12, "tokens": 120,
                              "dataset_version": "test", "split": "train"}), ""

    monkeypatch.setattr(cs, "run", run)
    code = run_main(tmp_path, folder, tok, "w", "--fingerprints", str(fp_dir), "--part-tokens", "40")
    assert code == 1  # hits make the exit code 1
    r = json.loads((tmp_path / "w" / "results" / f"{shard_id}.json").read_text())
    assert r["parts"] == 3 and r["docs"] == 12
    assert r["flagged"] == 2 and sorted(r["flagged_doc_ids"]) == ["d10", "d5"]
    assert r["canary_hits"] == 1 and r["canary_hit_list"][0]["doc_id"] == "d10"
    assert r["set_sha256"] == json.loads((fp_dir / "MANIFEST.json").read_text())["set_sha256"]
    assert list((tmp_path / "w" / "text").iterdir()) == []


def test_runs_as_a_script_in_isolated_mode(tmp_path):
    """python -I leaves the script's folder out of sys.path: the default fingerprint set must still be found."""
    import subprocess
    import sys

    (tmp_path / "shards").mkdir()
    tok = tmp_path / "tokenizer.json"
    tok.write_text("{}")
    p = subprocess.run([sys.executable, "-I", str(Path(cs.__file__)), str(tmp_path / "shards"), "--tokenizer",
                        str(tok), "--work", str(tmp_path / "w")], capture_output=True, text=True)
    assert p.returncode == 2 and "no shards to check" in p.stderr and "Traceback" not in p.stderr


# ---- one run per work folder, and the check code ----
def test_a_second_run_on_the_same_work_folder_stops(tmp_path, monkeypatch):
    folder, tok = make_shards(tmp_path, {"a-train-000000": 1})
    monkeypatch.setattr(cs, "check_one", lambda s, a, t, p: result(s))
    work = tmp_path / "w"
    work.mkdir()
    (work / "text").mkdir()
    (work / "text" / "a-train-000000.text.parquet").write_text("text of the first run")
    held = cs.lock_work(work)  # a first run that is still working
    with pytest.raises(SystemExit) as e:
        run_main(tmp_path, folder, tok, "w")
    assert e.value.code == 2
    assert (work / "text" / "a-train-000000.text.parquet").exists()  # the first run's files are not touched
    held.close()
    assert run_main(tmp_path, folder, tok, "w") == 0  # free again after the first run ends


def test_resume_checks_again_when_the_check_code_changes(tmp_path, monkeypatch):
    folder, tok = make_shards(tmp_path, {"a-train-000000": 1})
    calls = []

    def fake(shard_id, a, tok_sha, pool):
        calls.append(shard_id)
        r = result(shard_id)
        r["tokenizer_sha256"] = tok_sha
        return r

    monkeypatch.setattr(cs, "check_one", fake)
    assert run_main(tmp_path, folder, tok, "w") == 0
    assert run_main(tmp_path, folder, tok, "w") == 0
    assert calls == ["a-train-000000"]
    monkeypatch.setattr(cs, "code_sha256", lambda: "c" * 64)  # as after a change in normalize.py
    assert run_main(tmp_path, folder, tok, "w") == 0
    assert calls == ["a-train-000000", "a-train-000000"]
    saved = json.loads((tmp_path / "w" / "results" / "a-train-000000.json").read_text())
    assert saved["code_sha256"] == "c" * 64


def test_code_sha256_covers_each_file_and_ignores_line_ends(tmp_path, monkeypatch):
    for name in cs.CODE_FILES:
        (tmp_path / name).write_bytes(b"line one\nline two\n")
    monkeypatch.setattr(cs, "HERE", tmp_path)
    base = cs.code_sha256()
    (tmp_path / "normalize.py").write_bytes(b"line one\r\nline two\r\n")  # a Windows checkout
    assert cs.code_sha256() == base
    (tmp_path / "normalize.py").write_bytes(b"line one\nline 2\n")
    assert cs.code_sha256() != base


def test_code_files_are_the_local_imports():
    """CODE_FILES must name every module of this folder that the checks import."""
    import ast

    here = Path(cs.__file__).resolve().parent
    local = {p.stem for p in here.glob("*.py")}
    todo, seen = ["check_shards", "decode_shard", "decontam_check", "canary_scan"], set()
    while todo:
        mod = todo.pop()
        if mod in seen:
            continue
        seen.add(mod)
        for node in ast.walk(ast.parse((here / f"{mod}.py").read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            todo += [n.split(".")[0] for n in names if n.split(".")[0] in local]
    assert seen <= {Path(n).stem for n in cs.CODE_FILES}


def test_text_written_late_by_a_crashed_run_is_deleted_at_the_end(tmp_path, monkeypatch):
    """A step of a crashed run can go on and write text after this run started: the end of this run deletes it,
    and --keep-text keeps the text."""
    folder, tok = make_shards(tmp_path, {"a-train-000000": 1})

    def fake(shard_id, a, tok_sha, pool):
        (a.work / "text" / "other-train-000000.text.parquet").write_text("text from a step of a crashed run")
        return result(shard_id)

    monkeypatch.setattr(cs, "check_one", fake)
    assert run_main(tmp_path, folder, tok, "w") == 0
    assert list((tmp_path / "w" / "text").iterdir()) == []
    assert run_main(tmp_path, folder, tok, "k", "--keep-text") == 0
    assert [p.name for p in (tmp_path / "k" / "text").iterdir()] == ["other-train-000000.text.parquet"]
