#!/usr/bin/env python3
"""Build the G5 held-out set v1 (scored in bits per byte) as one JSONL file, heldout_v1.jsonl.

Lives in teams/05-architecture/heldout_v1/; it builds the file in heldout_v1/data/.
The set is permanent: it scores the week-2 arms, the dry runs and the final model, so it must never be
trained on. Every source is a split its makers set aside, with an accepted licence, and is not a benchmark.
The file holds 15 slices, one after the other; each id starts with its slice:

    en                  c4-val-               allenai/c4 en, validation (ODC-By)
    hi bn ta te kn ml   fw2-<lang>-test-      HuggingFaceFW/fineweb-2, test, the 11 G3 languages (ODC-By)
    mr gu pa or as
    math                owm-test-             EleutherAI/proof-pile-2 open-web-math, test (ODC-By)
    sci                 pes2o-val-            allenai/peS2o v2, validation (ODC-By)
    code                vault-<lang>-test-    Fsoft-AIC/the-vault-function, test: Python, C++, Go, Java,
                                              JavaScript, Rust in turn; only functions whose repo licences
                                              are all permissive (dataset: MIT)

Never FLORES, IN22, MILU, GSM8K, HumanEval or MBPP: Team 9's decontam_check.py must flag 0 documents.
Each line is {"id": "...", "text": "..."} in UTF-8. Ids are unique. Dataset revisions are pinned and
documents are taken in the order the source stores them, so a rebuild gives the same bytes.

    python build_heldout.py --out heldout_v1/data --docs 20      # a small sample: 20 documents per slice
    python build_heldout.py --out heldout_v1/data --mb 0.25      # about 0.25 MB of text per slice

Also writes, next to it:
    heldout_v1_sources.jsonl   source tracking, one line per document in the same order and with the same id:
                               slice, dataset, revision, file, row (in that source file, counting skipped rows),
                               source_id, url, licence, text_sha256
    heldout_manifest.json      the selection rule, both files' sha256, and per slice the dataset, pinned
                               revision, part, id prefix, documents, text bytes, documents skipped for personal data
    SHA256SUMS                 the sha256 of both JSONL files (sha256sum -c format)
Text bytes = sum of len(text.encode("utf-8")), the denominator of bits per byte.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

INDIC = {
    "hi": "hin_Deva", "bn": "ben_Beng", "ta": "tam_Taml", "te": "tel_Telu",
    "kn": "kan_Knda", "ml": "mal_Mlym", "mr": "mar_Deva", "gu": "guj_Gujr",
    "pa": "pan_Guru", "or": "ory_Orya", "as": "asm_Beng",
}
# Dataset revisions pinned on 1 Nov 2026 (HfApi().dataset_info(repo).sha), so a rebuild reads the same rows.
REV = {
    "allenai/c4": "1588ec454efa1a09f29cd18ddd04fe05fc8653a2",
    "HuggingFaceFW/fineweb-2": "af9c13333eb981300149d5ca60a8e9d659b276b9",
    "EleutherAI/proof-pile-2": "901a9273a770e9d4138c5ddd91802f9c5c6cdc4b",
    "allenai/peS2o": "636a503e44a3ca1b58e01fb61eab0825cd574de0",
    "Fsoft-AIC/the-vault-function": "505c679056e49a2a269b64777ee7c496d22e1440",
}
CODE_LANGS = {"py": "python", "cpp": "cpp", "go": "go", "java": "java", "js": "javascript", "rs": "rust"}
PERMISSIVE = {"MIT", "MIT-0", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense", "CC0-1.0",
              "0BSD", "Zlib", "BSL-1.0"}
SELECTION = ("Rows in the order the source stores them (code: the six languages in turn); text stripped; empty "
             "texts skipped; code only when every repo licence is permissive; a document with an email address, "
             "a phone number or a secret-looking string is skipped (no personal data in the repo, and pr-guard "
             "rejects emails); documents found in review are dropped by id (DROPPED_IN_REVIEW) and still count toward "
             "the size budget; stop at --docs documents or once --mb megabytes of text are reached. "
             "No shuffling, no other filtering.")
# The email and secret patterns are the lab's pr-guard patterns (.github/workflows/pr-guard.yml).
EMAIL = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9][A-Za-z0-9._%+-]*@(?!users\.noreply\.github\.com\b|example\.(?:com|org)\b)"
                   r"(?:[A-Za-z0-9-]+\.)+(?:com|org|net|edu|gov|mil|int|in|io|ai|co|uk|us|me|dev|app|info|biz|ac|ca|au|de|fr|jp|sg|ae)\b",
                   re.I)
SECRET = re.compile(r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}"
                    r"|\bsk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}")
PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"
                   r"|(?<!\d)\+\d{1,3}[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}(?!\d)")


# Documents Team 9's decontam_check.py flagged (full fingerprint set). Dropped by id, with the reason.
EXCLUDE = {
    "owm-test-000011": "shares 13-word runs with LiveCodeBench release_v6 items (coverage 1%); fingerprints v1, 1 Nov 2026",
}

# Documents found in the G5 lead's review of PR #191 (2 Nov 2026) with a phone number or an email address that the
# filter above did not catch (US-style numbers, a number written in Odia digits, the email@example.com placeholder).
# Dropped by id. They still count toward their slice's size budget, so every other document stays where it was.
DROPPED_IN_REVIEW = {
    "c4-val-000018": "phone number (US format), lead review of PR #191, 2 Nov 2026",
    "c4-val-000030": "phone numbers (US format), lead review of PR #191, 2 Nov 2026",
    "c4-val-000059": "phone number (US format, dots), lead review of PR #191, 2 Nov 2026",
    "c4-val-000094": "phone number (US format), lead review of PR #191, 2 Nov 2026",
    "fw2-or-test-000030": "email address (email@example.com placeholder), lead review of PR #191, 2 Nov 2026",
    "fw2-or-test-000046": "phone number written in Odia digits, lead review of PR #191, 2 Nov 2026",
}


def personal(text):
    return bool(EMAIL.search(text) or PHONE.search(text) or SECRET.search(text))


def rows(kind, repo, path):
    """Stream one file of a dataset repo at its pinned revision with a generic reader (no loading scripts)."""
    from datasets import load_dataset
    url = f"hf://datasets/{repo}@{REV[repo]}/{path}"
    return iter(load_dataset(kind, data_files=url, split="train", streaming=True))


def code_docs():
    """(id, text, origin): the six languages in turn, permissive licences only.
    origin.row is the row number in that language's test file, counting the rows that were skipped."""
    repo = "Fsoft-AIC/the-vault-function"
    streams = {short: enumerate(rows("parquet", repo, f"data/test/{lang}-00000-of-00001.parquet"))
               for short, lang in CODE_LANGS.items()}
    count = dict.fromkeys(streams, 0)
    while streams:
        for short in list(streams):
            for i, row in streams[short]:
                licences = row["license"] or []
                if licences and all(x in PERMISSIVE for x in licences):
                    origin = {"file": f"data/test/{CODE_LANGS[short]}-00000-of-00001.parquet", "row": i,
                              "source_id": f"{row['path']}@{row['hexsha']}", "url": f"https://github.com/{row['repo']}",
                              "licence": "+".join(licences)}
                    yield f"vault-{short}-test-{count[short]:06d}", row["original_string"], origin
                    count[short] += 1
                    break
            else:
                del streams[short]


def text_docs(it, prefix, file, licence, id_field=None):
    """(id, text, origin) for a stream of rows with a "text" field; origin.row is the row number in the source file."""
    for i, row in enumerate(it):
        origin = {"file": file, "row": i, "source_id": row.get(id_field) if id_field else None,
                  "url": row.get("url"), "licence": licence}
        yield f"{prefix}-{i:06d}", row["text"], origin


def sources():
    """(slice code, dataset, part, id prefix, document generator factory)."""
    from datasets import load_dataset
    c4, fw2, pp2, pes2o = "allenai/c4", "HuggingFaceFW/fineweb-2", "EleutherAI/proof-pile-2", "allenai/peS2o"
    c4_file, owm_file, pes2o_file = ("en/c4-validation.00000-of-00008.json.gz", "open-web-math/test/test.jsonl.zst",
                                     "data/v2/validation-00000-of-00002.json.gz")
    odc = "ODC-By-1.0"
    yield "en", c4, c4_file, "c4-val", lambda: text_docs(rows("json", c4, c4_file), "c4-val", c4_file, odc)
    for code, config in INDIC.items():
        yield code, fw2, f"{config} test", f"fw2-{code}-test", (lambda c=config, k=code: text_docs(
            load_dataset(fw2, name=c, split="test", streaming=True, revision=REV[fw2]), f"fw2-{k}-test",
            f"data/{c}/test", odc, id_field="id"))
    yield "math", pp2, owm_file, "owm-test", lambda: text_docs(rows("json", pp2, owm_file), "owm-test", owm_file, odc)
    yield "sci", pes2o, pes2o_file, "pes2o-val", lambda: text_docs(
        rows("json", pes2o, pes2o_file), "pes2o-val", pes2o_file, odc, id_field="id")
    yield ("code", "Fsoft-AIC/the-vault-function", "data/test/{" + ",".join(CODE_LANGS.values()) + "}",
           "vault-<lang>-test", code_docs)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(out, n_docs, budget):
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"selection": SELECTION, "licence": "ODC-By 1.0 (C4, FineWeb-2, OpenWebMath, peS2o); MIT (The Vault)",
                "line_format": '{"id": ..., "text": ...}, UTF-8, one document per line',
                "excluded_benchmark_matches": EXCLUDE, "dropped_in_review": DROPPED_IN_REVIEW,
                "file": {}, "sources_file": {}, "slices": {}}
    path, src_path = out / "heldout_v1.jsonl", out / "heldout_v1_sources.jsonl"
    h, hs, total_docs, total_bytes = hashlib.sha256(), hashlib.sha256(), 0, 0
    with path.open("w", encoding="utf-8", newline="\n") as f, src_path.open("w", encoding="utf-8", newline="\n") as g:
        for code, repo, part, prefix, docs_of in sources():
            docs, text_bytes, skipped, dropped, used = 0, 0, 0, 0, 0
            for doc_id, raw, origin in docs_of():
                text = (raw or "").strip()
                if not text or doc_id in EXCLUDE:
                    continue
                if personal(text) or personal(origin.get("url") or "") or personal(origin.get("source_id") or ""):
                    skipped += 1
                    continue
                used += len(text.encode("utf-8"))  # size budget, counting documents dropped in review
                if doc_id in DROPPED_IN_REVIEW:
                    dropped += 1
                    if budget and used >= budget:
                        break
                    continue
                line = json.dumps({"id": doc_id, "text": text}, ensure_ascii=False) + "\n"
                f.write(line)
                h.update(line.encode("utf-8"))
                src = {"id": doc_id, "slice": code, "dataset": repo, "revision": REV[repo], **origin,
                       "text_sha256": sha256_text(text)}
                src_line = json.dumps(src, ensure_ascii=False) + "\n"
                g.write(src_line)
                hs.update(src_line.encode("utf-8"))
                docs += 1
                text_bytes += len(text.encode("utf-8"))
                if (n_docs and docs >= n_docs) or (budget and used >= budget):
                    break
            manifest["slices"][code] = {"dataset": repo, "revision": REV[repo], "part": part, "id_prefix": prefix,
                                        "docs": docs, "text_bytes": text_bytes, "skipped_personal": skipped,
                                        "dropped_in_review": dropped}
            total_docs += docs
            total_bytes += text_bytes
            print(f"{code}: {docs} docs, {text_bytes:,} text bytes, {skipped} skipped (personal data), "
                  f"{dropped} dropped in review", flush=True)
    digest, src_digest = h.hexdigest(), hs.hexdigest()
    manifest["file"] = {"name": path.name, "docs": total_docs, "text_bytes": total_bytes, "sha256": digest}
    manifest["sources_file"] = {"name": src_path.name, "docs": total_docs, "sha256": src_digest,
                                "fields": ["id", "slice", "dataset", "revision", "file", "row", "source_id", "url",
                                           "licence", "text_sha256"]}
    (out / "heldout_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                               encoding="utf-8", newline="\n")
    # sha256sum format, so `sha256sum -c SHA256SUMS` in this folder checks both files
    (out / "SHA256SUMS").write_text(f"{digest}  {path.name}\n{src_digest}  {src_path.name}\n",
                                    encoding="utf-8", newline="\n")
    print(f"{path.name}: {total_docs} docs, {total_bytes:,} text bytes, sha256 {digest}", flush=True)
    print(f"{src_path.name}: sha256 {src_digest}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, help="output directory")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--docs", type=int, help="documents per slice")
    g.add_argument("--mb", type=float, help="megabytes of text per slice")
    a = ap.parse_args()
    build(Path(a.out), a.docs, int(a.mb * 1_000_000) if a.mb else None)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
