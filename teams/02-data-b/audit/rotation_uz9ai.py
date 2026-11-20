#!/usr/bin/env python3
"""Reproducible code-point audit of deterministic Kannada shard samples.

Shard parsing and batch decoding use ``read_shard`` from ``indic_audit.py``. Arrow kernels perform the
joiner counts. No document text is printed or written.

Requires the third-party ``regex`` package, which is not in the standard library.

Run from this folder, with the shard files and tokenizer under the current directory:

  uv run python rotation_uz9ai.py --shard shards/ind-kn-sangraha-v-train-000000.bin \\
      --tokenizer p1536_tokenizer.json --days 4 5 --sample-size 50

The report is written to rotation_uz9ai.md in the current directory unless --out is given.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shlex
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pyarrow as pa
import pyarrow.compute as pc
import regex
from tokenizers import Tokenizer

from indic_audit import read_shard

DEFAULT_EOS_ID = 130822
ZWJ = "\u200d"
ZWNJ = "\u200c"

# Unicode names make this an exact list, avoiding unassigned code points in the
# Kannada block. The task asks for dependent vowel signs and virama, not every
# Kannada combining mark.
KANNADA_VOWEL_SIGNS_AND_VIRAMA = "".join(
    chr(cp)
    for cp in range(0x0C80, 0x0D00)
    if unicodedata.name(chr(cp), "").startswith("KANNADA VOWEL SIGN")
    or unicodedata.name(chr(cp), "") == "KANNADA SIGN VIRAMA"
)

G1_RE = regex.compile(
    rf"(?V1)(?<=[\s\p{{P}}\p{{Nd}}\p{{Script=Latin}}])"
    rf"[{regex.escape(KANNADA_VOWEL_SIGNS_AND_VIRAMA)}]"
)
JOINER_RUN_RE = regex.compile(r"[\u200c\u200d]+")
A1_RE = regex.compile(r"[\u200b\ufeff\u00ad\u202a-\u202e\u2066-\u2069]")
A4_RE = regex.compile(r"\ufffd")
WORD_RE = regex.compile(r"(?V1)[\p{L}\p{M}\u200c\u200d]+")
KANNADA_LETTER_RE = regex.compile(r"(?V1)[\p{L}&&\p{Script=Kannada}]")
FOREIGN_LETTER_RE = regex.compile(
    r"(?V1)[\p{L}--[\p{Script=Kannada}\p{Script=Common}\p{Script=Inherited}]]+"
)

A1_NOTES = {
    0x200B: "zero-width space",
    0xFEFF: "byte-order mark",
    0x00AD: "soft hyphen",
    **{cp: "bidi embedding or override mark" for cp in range(0x202A, 0x202F)},
    **{cp: "bidi isolate mark" for cp in range(0x2066, 0x206A)},
}


@dataclass(frozen=True)
class Finding:
    doc_id: str
    code: str
    offset: int
    hex_dump: str
    note: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hex_context(text: str, start: int, end: int, radius: int = 3) -> str:
    """Return only code points, with up to radius code points on each side."""
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return " ".join(f"U+{ord(char):04X}" for char in text[left:right])


def is_word_content(char: str) -> bool:
    """Letters, marks and numbers count as content adjacent to a joiner."""
    return bool(char) and unicodedata.category(char)[0] in "LMN"


def inspect_text(doc_id: str, text: str) -> list[Finding]:
    """Find G1, G2, A1, A4 and A6 issues in one decoded document.

    This loops over regex matches in one sampled document, never over tokens.
    Regex matching itself runs in the regex engine.
    """
    findings: list[Finding] = []

    for match in G1_RE.finditer(text):
        cp = ord(match.group())
        kind = "virama" if cp == 0x0CCD else "vowel sign"
        previous = ord(text[match.start() - 1])
        findings.append(
            Finding(
                doc_id,
                "G1",
                match.start(),
                hex_context(text, match.start(), match.end()),
                f"Kannada {kind} after U+{previous:04X}",
            )
        )

    for match in JOINER_RUN_RE.finditer(text):
        start, end = match.span()
        notes: list[str] = []
        if end - start > 1:
            notes.append("adjacent or doubled joiners")
        if start == 0 or not is_word_content(text[start - 1]):
            notes.append("joiner at word start")
        if end == len(text) or not is_word_content(text[end]):
            notes.append("joiner at word end")
        if notes:
            findings.append(
                Finding(
                    doc_id,
                    "G2",
                    start,
                    hex_context(text, start, end),
                    "; ".join(notes),
                )
            )

    for match in A1_RE.finditer(text):
        cp = ord(match.group())
        findings.append(
            Finding(
                doc_id,
                "A1",
                match.start(),
                hex_context(text, match.start(), match.end()),
                f"{A1_NOTES[cp]} U+{cp:04X}",
            )
        )

    for match in A4_RE.finditer(text):
        findings.append(
            Finding(
                doc_id,
                "A4",
                match.start(),
                hex_context(text, match.start(), match.end()),
                "replacement character U+FFFD",
            )
        )

    for word in WORD_RE.finditer(text):
        word_text = word.group()
        if not KANNADA_LETTER_RE.search(word_text):
            continue
        for foreign in FOREIGN_LETTER_RE.finditer(word_text):
            start = word.start() + foreign.start()
            first_cp = ord(text[start])
            findings.append(
                Finding(
                    doc_id,
                    "A6",
                    start,
                    hex_context(text, start, start + 1),
                    f"non-Kannada letter run beginning U+{first_cp:04X} inside Kannada word",
                )
            )

    return findings


def verify_files(shard: Path, tokenizer_path: Path) -> tuple[dict, dict[str, str]]:
    stem = shard.with_suffix("")
    manifest_path = stem.with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = {
        "payload": shard,
        "index": stem.with_suffix(".idx.npy"),
        "metadata": stem.with_suffix(".docs.parquet"),
        "quality_report": stem.with_suffix(".quality_report.json"),
        "tokenizer": tokenizer_path,
    }
    expected = {
        "payload": manifest["payload_sha256"],
        "index": manifest["index_sha256"],
        "metadata": manifest["sample_metadata_sha256"],
        "quality_report": manifest["quality_report_sha256"],
        "tokenizer": manifest["tokenizer_sha256"],
    }
    actual = {name: sha256(path) for name, path in paths.items()}
    mismatches = [name for name in expected if actual[name] != expected[name]]
    if mismatches:
        raise SystemExit("SHA-256 mismatch: " + ", ".join(mismatches))
    return manifest, actual


def count_joiners(texts: pa.Array) -> tuple[int, int]:
    zwj = pc.sum(pc.count_substring(texts, ZWJ)).as_py() or 0
    zwnj = pc.sum(pc.count_substring(texts, ZWNJ)).as_py() or 0
    return int(zwj), int(zwnj)


def markdown_table(rows: Sequence[Sequence[object]]) -> str:
    return "\n".join("| " + " | ".join(str(value) for value in row) + " |" for row in rows)


def render_report(
    *,
    shard: Path,
    tokenizer_path: Path,
    out_path: Path,
    days: list[int],
    sample_size: int,
    all_documents: bool,
    per_day_indices: dict[int, list[int]],
    selected_indices: list[int],
    selected_doc_ids: list[str],
    per_day_counts: dict[int, tuple[int, int]],
    unique_counts: tuple[int, int],
    findings: list[Finding],
    doc_count: int,
    token_count: int,
    hashes: dict[str, str],
    command: str,
    final_lines: list[str],
    elapsed: float,
) -> str:
    by_code = {code: sum(f.code == code for f in findings) for code in ("G1", "G2", "A1", "A4", "A6")}
    documents_with_findings = len({f.doc_id for f in findings})

    if all_documents:
        sample_rows: list[list[object]] = [
            ["scope", "documents checked", "ZWJ (U+200D)", "ZWNJ (U+200C)"],
            ["---", "---:", "---:", "---:"],
            ["all", len(selected_indices), *unique_counts],
        ]
        scope_lines = f"""- Mode: full shard (`--all`)
- Documents checked: {len(selected_indices)}"""
        joiner_note = "The `all` row covers every document in shard order."
        selection_note = "Code-point checks are applied to every decoded document."
    else:
        sample_rows = [
            ["day/seed", "documents drawn", "ZWJ (U+200D)", "ZWNJ (U+200C)"],
            ["---:", "---:", "---:", "---:"],
        ]
        for day in days:
            sample_rows.append([day, len(per_day_indices[day]), *per_day_counts[day]])
        sample_rows.append(["unique", len(selected_indices), *unique_counts])
        scope_lines = f"""- Mode: deterministic samples
- Deterministic seeds: {", ".join(map(str, days))}
- Sample size per seed: {sample_size}
- Sample draws: {sum(len(values) for values in per_day_indices.values())}
- Unique documents checked: {len(selected_indices)}"""
        joiner_note = "The `unique` row de-duplicates documents selected by more than one seed. Day rows represent each reproducible draw independently."
        selection_note = "Deterministic sample selection is applied before the code-point checks."

    documents_checked = "\n".join(
        f"- `{row}: {doc_id}`" for row, doc_id in zip(selected_indices, selected_doc_ids, strict=True)
    )

    finding_rows: list[list[object]] = [
        ["doc_id", "code", "offset", "hex dump", "note"],
        ["---", "---", "---:", "---", "---"],
    ]
    finding_rows.extend(
        [f.doc_id, f.code, f.offset, f"`{f.hex_dump}`", f.note] for f in findings
    )
    if not findings:
        finding_rows.append(["—", "—", "—", "—", "No findings"])

    code_summary = ", ".join(f"{code}: {by_code[code]}" for code in ("G1", "G2", "A1", "A4", "A6"))
    return f"""# Kannada shard rotation audit: uz9ai

## Scope and method

- Shard: `{shard}`
- Frozen tokenizer: `{tokenizer_path}`
- Documents in shard: {doc_count}
- Payload tokens: {token_count}
{scope_lines}
- Offsets are zero-based Unicode code-point offsets in decoded shard text.
- Hex dumps contain the finding and at most three code points on each side. No document text is included.

The script imports `read_shard()` from `indic_audit.py`, validates the shard through that reader, and batch-decodes the complete shard with the frozen tokenizer. {selection_note} Joiners are counted with PyArrow kernels. There is no Python loop over tokens.

<details><summary>Documents checked (shard row: doc_id)</summary>

{documents_checked}

</details>

## Input integrity

All hashes matched the shard manifest.

| input | SHA-256 |
|---|---|
| payload | `{hashes['payload']}` |
| index | `{hashes['index']}` |
| document metadata | `{hashes['metadata']}` |
| quality report | `{hashes['quality_report']}` |
| tokenizer | `{hashes['tokenizer']}` |

## Joiner counts

{markdown_table(sample_rows)}

{joiner_note}

## Findings

{markdown_table(finding_rows)}

Summary: {len(findings)} findings in {documents_with_findings} documents. {code_summary}.

The cleaned shard can show joiner counts and malformed joiner positions. Establishing that a joiner was lost requires raw pre-cleaning text; the before/after comparison is covered separately by `indic_audit.py`.

## Reproduction evidence

Command:

```console
{command}
```

Final output lines:

```text
{chr(10).join(final_lines)}
```

Audit wall time reported by the script: {elapsed:.3f} seconds.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shard",
        type=Path,
        default=Path("shards/ind-kn-sangraha-v-train-000000.bin"),
    )
    parser.add_argument("--tokenizer", type=Path, default=Path("p1536_tokenizer.json"))
    parser.add_argument("--days", type=int, nargs="+", default=[4, 5])
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument(
        "--all",
        action="store_true",
        help="check every document of the shard instead of the samples",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("rotation_uz9ai.md"),
    )
    return parser.parse_args()


def main() -> None:
    started = time.perf_counter()
    args = parse_args()
    if not args.all and len(set(args.days)) != len(args.days):
        raise SystemExit("--days must not contain duplicates")
    if not args.all and args.sample_size < 1:
        raise SystemExit("--sample-size must be positive")

    manifest, hashes = verify_files(args.shard, args.tokenizer)
    tokenizer = Tokenizer.from_file(str(args.tokenizer))
    all_doc_ids, all_texts = read_shard(
        args.shard, tokenizer, int(manifest.get("eos_token_id", DEFAULT_EOS_ID))
    )
    doc_count = len(all_doc_ids)
    token_count = int(manifest["token_count"])
    if doc_count != int(manifest["doc_count"]):
        raise SystemExit("manifest document count does not match the parsed shard")
    if not args.all and args.sample_size > doc_count:
        raise SystemExit("--sample-size exceeds the shard document count")

    if args.all:
        per_day_indices: dict[int, list[int]] = {}
        per_day_counts: dict[int, tuple[int, int]] = {}
        selected_indices = list(range(doc_count))
        doc_ids = all_doc_ids.to_pylist()
        text_array = all_texts
    else:
        per_day_indices = {
            day: random.Random(day).sample(range(doc_count), args.sample_size)
            for day in args.days
        }
        selected_indices = list(
            dict.fromkeys(index for day in args.days for index in per_day_indices[day])
        )
        take_indices = pa.array(selected_indices, type=pa.int64())
        doc_ids = pc.take(all_doc_ids, take_indices).to_pylist()
        text_array = pc.take(all_texts, take_indices)
        per_day_counts = {
            day: count_joiners(
                pc.take(all_texts, pa.array(per_day_indices[day], type=pa.int64()))
            )
            for day in args.days
        }
    texts = text_array.to_pylist()
    unique_counts = count_joiners(text_array)

    findings = [
        finding
        for doc_id, text in zip(doc_ids, texts, strict=True)
        for finding in inspect_text(doc_id, text)
    ]
    document_order = {doc_id: position for position, doc_id in enumerate(doc_ids)}
    findings.sort(key=lambda f: (document_order[f.doc_id], f.offset, f.code, f.note))

    by_code = {code: sum(f.code == code for f in findings) for code in ("G1", "G2", "A1", "A4", "A6")}
    documents_with_findings = len({f.doc_id for f in findings})
    elapsed = time.perf_counter() - started

    command_parts = [
        "uv", "run", "python", "rotation_uz9ai.py",
        "--shard", str(args.shard), "--tokenizer", str(args.tokenizer),
    ]
    if args.all:
        command_parts.append("--all")
        scope_output = f"mode=all documents_checked={len(selected_indices)}"
    else:
        command_parts.extend([
            "--days", *(str(day) for day in args.days),
            "--sample-size", str(args.sample_size),
        ])
        scope_output = (
            f"mode=sample sample_draws={sum(map(len, per_day_indices.values()))} "
            f"unique_documents={len(selected_indices)}"
        )
    command_parts.extend(["--out", str(args.out)])
    command = shlex.join(command_parts)
    code_counts = ",".join(f"{code}:{by_code[code]}" for code in ("G1", "G2", "A1", "A4", "A6"))
    final_lines = [
        scope_output,
        f"checked_zwj={unique_counts[0]} checked_zwnj={unique_counts[1]}",
        f"findings={len(findings)} documents_with_findings={documents_with_findings}",
        f"findings_by_code={code_counts}",
        f"report={args.out}",
        f"audit_wall_time_seconds={elapsed:.3f}",
    ]

    report = render_report(
        shard=args.shard,
        tokenizer_path=args.tokenizer,
        out_path=args.out,
        days=args.days,
        sample_size=args.sample_size,
        all_documents=args.all,
        per_day_indices=per_day_indices,
        selected_indices=selected_indices,
        selected_doc_ids=doc_ids,
        per_day_counts=per_day_counts,
        unique_counts=unique_counts,
        findings=findings,
        doc_count=doc_count,
        token_count=token_count,
        hashes=hashes,
        command=command,
        final_lines=final_lines,
        elapsed=elapsed,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print("\n".join(final_lines))


if __name__ == "__main__":
    main()
