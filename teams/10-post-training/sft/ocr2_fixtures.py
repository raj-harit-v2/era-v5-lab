"""Shared fixtures for the OCR-2 join tests (G10).

Everything here is a synthetic placeholder built in a temporary folder: tagged strings, not problems and
not solutions. Fixtures are tests. They are never training data: every manifest written here carries
`"test_fixture": true`, and `pack_admission.py` refuses a pack from such a run.

The toy benchmark items are the made-up ones of `test_decontam_run.py` (as in Team 9's own tests).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import convert as g10  # noqa: E402
import decontam_run  # noqa: E402
import prepare_ocr2 as join  # noqa: E402
from test_decontam_run import CANARY, COPY, TOY  # noqa: E402,F401

SET_ID = join.SET_ID
TOOLS = decontam_run.DEFAULT_TOOLS
REVISION = "f" * 40  # a fixture revision, not a real commit
SHARED = "FIXTURE statement SHARED: the same placeholder sits in a train split and in a test split."


def statement(tag: str) -> str:
    return f"FIXTURE statement {tag}: synthetic placeholder, not a real problem."


# source key -> ordered files -> statements. taco/train crosses a file boundary at ordinal 3.
DEFAULT_SOURCES = {
    "taco/train": [("taco-train-a", [statement("T0"), statement("T1"), statement("T2")]),
                   ("taco-train-b", [statement("T3"), statement("T4")])],
    "taco/test": [("taco-test-a", [statement("X0"), SHARED])],
    "apps/train": [("apps-train-a", [statement("A0"), statement("A1"), SHARED])],
    "apps/test": [("apps-test-a", [statement("Y0")])],
    "code_contests/train": [("cc-train-a", ["FIXTURE statement C0 quotes a toy benchmark item. " + COPY, statement("C1")])],
}
FIELD = {"taco": "question", "apps": "question", "code_contests": "description"}


def ocr_row(n: int, dataset: str, split: str, index, **over) -> dict:
    row = {"id": f"fx{n:04d}", "question_id": f"fq{n:04d}", "license": "apache-2.0", "question": "-",
           "r1_generation": f"<think>fixture trace {n}</think>\n\nfixture reply {n}",
           "qwq_critique": "fixture critique", "solution": "pass", "judgement": "right", "pass_rate": "1.0",
           "dataset": dataset, "split": split, "source": "fixture", "difficulty": "fixture", "index": index}
    row.update(over)
    return row


def write_jsonl(path: Path, rows) -> str:
    data = "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows).encode("ascii")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def toy_fingerprints(folder: Path) -> tuple[Path, str]:
    """A fingerprint set of two made-up items, built with Team 9's own code. Returns (folder, set_sha256)."""
    sys.path.insert(0, str(TOOLS))
    try:
        import fpset
        import registry
    finally:
        sys.path.remove(str(TOOLS))
    folder.mkdir(parents=True, exist_ok=True)
    data = folder / "toy.jsonl"
    data.write_text("".join(json.dumps(r) + "\n" for r in TOY), encoding="utf-8")
    reg_file = folder / "benchmarks.toml"
    reg_file.write_text(f'''
[toy]
name = "Toy"
status = "active"
tags = ["english"]
licence = "test only"
source = "local"
files = [{{ path = "{data.as_posix()}" }}]
id = "{{qid}}"
dedupe = true
texts = ["{{question}}"]
canaries = ["{{canary|guid}}"]
''', encoding="utf-8")
    reg = registry.load(reg_file)
    out = folder / "set"
    canaries: set = set()
    norm = fpset.DEFAULT_NORM
    fpset.write_benchmark(out, "toy", registry.items("toy", reg["toy"], folder, canaries),
                          registry.run_lengths(reg["toy"]), {"name": "Toy", "tags": reg["toy"]["tags"]},
                          canaries=canaries, boilerplate=fpset.Boilerplate(norm=norm), norm=norm)
    return out, fpset.write_index(out, {}, norm)


def toy_tokenizer(path: Path) -> str:
    """A tiny byte-level BPE with the chat markers as special tokens. Returns its sha256."""
    import tokenizers

    tok = tokenizers.Tokenizer(tokenizers.models.BPE(unk_token=None))
    tok.pre_tokenizer = tokenizers.pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = tokenizers.decoders.ByteLevel()
    trainer = tokenizers.trainers.BpeTrainer(vocab_size=400, special_tokens=list(g10.T.values()),
                                             initial_alphabet=tokenizers.pre_tokenizers.ByteLevel.alphabet())
    tok.train_from_iterator([statement("T0"), "fixture trace 1", "fixture reply 1"], trainer)
    tok.save(str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


class World:
    """One temporary world: source files, OCR-2 shard inputs, source manifest, policy, tokenizer, toy set."""

    def __init__(self, root: Path, shards: dict, *, sources=None, n_shards=2, shard_rows=None, toy=None,
                 tokenizer=None, policy=None, verified=("taco/train", "apps/train"), max_sequence_tokens=None,
                 cross_checks=None):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.sources = sources or DEFAULT_SOURCES
        self.source_specs = {}
        for key, files in self.sources.items():
            dataset, split = key.rsplit("/", 1)
            protected = split != "train"
            entries = []
            for name, texts in files:
                path = root / f"{name}.jsonl"
                sha = write_jsonl(path, [{FIELD[dataset]: t, "name": f"{name}/{n}"} for n, t in enumerate(texts)])
                entries.append({"name": name, "path": path.name, "sha256": sha, "rows": len(texts)})
            self.source_specs[key] = {
                "dataset": dataset, "split": split, "repo": f"fixture/{dataset}", "revision": REVISION, "kind": "jsonl",
                "assembly": FIELD[dataset], "protected": protected, "problem_id_field": "name", "files": entries,
                "total_rows": sum(e["rows"] for e in entries),
                "identity": {"level": "verified" if key in verified else "diagnostic"},
                **({"cross_checks": cross_checks[key]} if cross_checks and key in cross_checks else {}),
            }
        self.inputs = []
        for shard_id, rows in sorted(shards.items()):
            path = root / f"ocr2-shard-{shard_id}.jsonl"
            self.inputs.append({"shard_id": shard_id, "path": path.name, "sha256": write_jsonl(path, rows),
                                "rows": len(rows), "row_offset": 0, "coverage": "full"})
        shard_rows = shard_rows or {}
        self.shards = [{"shard_id": n, "path": f"train/python/train-{n:05d}-of-{n_shards:05d}.parquet", "sha256": None,
                        "bytes": None, "rows": shard_rows.get(n, len(shards[n]) if n in shards else None)}
                       for n in range(n_shards)]
        self.toy, self.toy_sha = toy if toy else (None, "0" * 64)
        self.tokenizer, self.tokenizer_sha = tokenizer if tokenizer else (None, None)
        self.max_sequence_tokens = max_sequence_tokens
        self.manifest_path = root / "source_manifest.json"
        self.policy_path = root / "policy.json"
        self.policy = json.loads((HERE / "ocr2_policy.json").read_text(encoding="utf-8"))
        self.policy["pack"] = {"approved_tokenizer_sha256": [self.tokenizer_sha] if self.tokenizer_sha else [],
                               "approved_fingerprint_set_sha256": [self.toy_sha]}
        for key, value in (policy or {}).items():
            self.policy[key] = value
        self.write()

    def manifest(self) -> dict:
        manifest = {
            "schema": "g10-ocr2-source-manifest/1", "test_fixture": True,
            "ocr2": {"repo": "nvidia/OpenCodeReasoning-2", "revision": REVISION, "config": "python",
                     "shards": self.shards, "inputs": self.inputs},
            "sources": self.source_specs,
            "conversion": {"max_sequence_tokens": self.max_sequence_tokens},
            "screening": {"tools_dir": str(TOOLS), "set_sha256": self.toy_sha},
        }
        if self.tokenizer:
            manifest["conversion"]["tokenizer"] = {"path": str(self.tokenizer), "sha256": self.tokenizer_sha}
        if self.toy:
            manifest["screening"]["fingerprints_test_only"] = str(self.toy)
        return manifest

    def write(self) -> None:
        self.manifest_path.write_text(json.dumps(self.manifest(), indent=1) + "\n", encoding="utf-8")
        self.policy_path.write_text(json.dumps(self.policy, indent=1) + "\n", encoding="utf-8")

    def shard_input(self, shard_id: int) -> Path:
        return self.root / f"ocr2-shard-{shard_id}.jsonl"

    def index_path(self) -> Path:
        """One index file per manifest content: an index is never reused for another manifest."""
        return self.root / f"index-{hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()[:12]}.sqlite"

    def prepare(self, out: Path, shard_id: int = 0, mode: str = "diagnostic") -> dict:
        return join.prepare(self.manifest_path, self.policy_path, self.shard_input(shard_id), shard_id, out, mode,
                            self.index_path())


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def allow_everything(world: World) -> None:
    """Turn the fixture policy into a fully approved one (the licence table must be patched by the test)."""
    world.policy["set_decision"] = "allowed"
    for src in world.policy["sources"].values():
        src["training_approved"] = True
        src["statement_licence"] = src["statement_licence"] or "fixture-terms"
        src["attribution"] = src["attribution"] or "fixture attribution"
    world.write()
