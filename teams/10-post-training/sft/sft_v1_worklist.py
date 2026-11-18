#!/usr/bin/env python3
"""Deterministic work list for SFT data v1 token records (WP14).

    python sft_v1_worklist.py fetch-hf --out hf_pins.json          # public metadata only: revision, gate flag, file sizes and LFS sha256
    python sft_v1_worklist.py build --hf-pins hf_pins.json --out-json worklist.json --out-md worklist.md

Work list = sets with an adapter in `convert.py` ADAPTERS, intersected with the licence-table decision and with
the SFT mix proposal (#391). Every Stage 1 set gets one record with the reasons it is in or out. A mix listing
never overrides a decision: `excluded` stays out, `TSAI reserves` is never called admitted, and a set whose
generator text shows a data-rule conflict is held for a ruling. Nothing here reads dataset rows.

Tracks
    allowed   decision starts with `allowed`, adapter, in the proposal, no data-rule flag. Eligible for full conversion.
    reserved  decision is `TSAI reserves`, adapter, in the proposal, no flag. Token records are a measurement only:
              the set is NOT admitted and never becomes a pack from this tool.
    owned     OCR-2 is the WP1 pack; it is not converted or counted here.
    hold      a data-rule flag needs a TSAI ruling first; the set is not converted.
    out       no adapter, not in the proposal, or excluded; the reason is recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent
SCHEMA = "g10-sft-v1-worklist/1"
OWNED_BY_WP1 = {"sft-code-opencodereasoning-2"}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


inv = _load("g10_mix_inventory_wl", HERE / "mix_inventory.py")
conv = _load("g10_convert_wl", HERE / "convert.py")

# Data-rule flags read from the licence table's generator text (CLAUDE.md, TSAI data rule, 3 Nov).
FLAG_PATTERNS = (
    ("closed_model", re.compile(r"\b(GPT-?3\.5|GPT-?4o?|ChatGPT|OpenAI|Claude|Anthropic|Gemini)\b(?!.{0,3}OSS)", re.I)),
    ("use_restricted_or_llama", re.compile(r"Llama|OpenRAIL|StarCoder2|DeepSeek Licen[cs]e|Tongyi|Qianwen", re.I)),
    ("modified_mit_generator", re.compile(r"Modified MIT", re.I)),
    ("unknown_generator", re.compile(r"unknown generator|generator is unknown|generator is not stated", re.I)),
)
SPLIT_UNKNOWN = re.compile(r"([A-Za-z0-9_-]+)[ -]split has unknown generator", re.I)


def adapter_file_spec(set_id: str) -> str:
    return conv.ADAPTERS[set_id][2][1] if set_id in conv.ADAPTERS else ""


def generator_flags(set_id: str, generator: str) -> list[str]:
    flags = [name for name, pat in FLAG_PATTERNS if pat.search(generator)]
    # A split named as having an unknown generator, and read by the adapter, is a conflict of its own.
    for hit in SPLIT_UNKNOWN.finditer(generator):
        token = hit.group(1).lower().replace("-", "_")
        if token in adapter_file_spec(set_id).lower().replace("-", "_"):
            flags.append(f"adapter_reads_unknown_generator_split:{token}")
    if "gated" in generator.lower():
        flags.append("gated")
    return flags


CAVEAT_WORDS = re.compile(r"unchecked|unknown|not stated|not name|does not name|unverified|conflict|restrict(?!ed model)|non-commercial|CC-BY-NC|no generator", re.I)


def licence_caveats(text: str) -> dict[str, list[str]]:
    """Sentences of each set's `Our opinion` / `Decision` lines in the licence table that raise a provenance or licence caveat."""
    out: dict[str, list[str]] = {}
    for block in re.split(r"\n(?=### `sft-)", text):
        head = re.match(r"### `([^`]+)`", block)
        if not head:
            continue
        found = []
        for line in block.splitlines():
            if line.startswith(("- **Our opinion:**", "- **Decision:**", "- **Generator model:**", "- **Licence:**")):
                for sent in re.split(r"(?<=[.;])\s+", line):
                    if CAVEAT_WORDS.search(sent):
                        found.append(re.sub(r"\s+", " ", sent.strip())[:320])
        if found:
            out[head.group(1)] = found
    return out


def source_repo(cell: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cell).split(" (")[0].split(",")[0].strip()


def decision_class(raw: str) -> str:
    low = raw.lower()
    if low.startswith("excluded"):
        return "excluded"
    if low.startswith("allowed"):
        return "allowed"
    if low.startswith("tsai reserves"):
        return "reserved"
    return "undecided"


def build(pins: dict | None) -> dict:
    licence = inv.parse_licence_stage1((TEAM / "licences/licence_table.md").read_text(encoding="utf-8"))
    proposal_text = (TEAM / "sft/sft_mix_proposal.md").read_text(encoding="utf-8")
    prop = inv.parse_proposal(proposal_text)
    area_of = {s: a for a, v in prop["areas"].items() for s in v["sets"]}
    area_of.update(inv.INFERRED_AREA)
    caveats = licence_caveats((TEAM / "licences/licence_table.md").read_text(encoding="utf-8"))
    records = []
    for set_id, row in sorted(licence.items()):
        dclass = decision_class(row["decision_raw"])
        reasons, flags = [], []
        has_adapter = set_id in conv.ADAPTERS
        in_area_table = set_id in {s for v in prop["areas"].values() for s in v["sets"]}
        in_proposal = set_id in proposal_text
        generator = re.sub(r"\s+", " ", row["generator"])
        if dclass != "excluded":
            flags = generator_flags(set_id, generator)
        # track, first matching rule wins; every failed condition is still listed as a reason.
        if dclass == "excluded":
            reasons.append("licence decision is excluded")
        if dclass == "undecided":
            reasons.append(f"licence decision is {row['decision_raw']!r}, neither allowed nor TSAI reserves")
        if not has_adapter:
            reasons.append("no adapter in convert.py ADAPTERS")
        if not in_proposal:
            reasons.append("not named in sft_mix_proposal.md (#391)")
        elif not in_area_table:
            reasons.append("named in the proposal text but not in the section 2 area table")
        if set_id in OWNED_BY_WP1:
            track = "owned"
            reasons.append("OCR-2 is the WP1 pack: not converted or counted here")
        elif dclass == "excluded" or dclass == "undecided" or not has_adapter or not in_proposal:
            track = "out"
        elif [f for f in flags if f != "gated"] or "gated" in flags:
            track = "hold"
            reasons.extend(f"data-rule flag: {f}" for f in flags)
        elif dclass == "allowed":
            track = "allowed"
            reasons.append("allowed + adapter + in proposal, generator text shows no flag")
        else:
            track = "reserved"
            reasons.append("TSAI reserves: measurement only, not admitted")
        rec = {"set": set_id, "source": source_repo(row["source"]), "decision": row["decision_raw"], "decision_class": dclass,
               "adapter": has_adapter, "in_area_table": in_area_table, "in_proposal_text": in_proposal,
               "area": area_of.get(set_id), "generator": generator, "licence": re.sub(r"\s+", " ", row["licence"]),
               "flags": flags, "track": track, "reasons": reasons, "licence_table_caveats": caveats.get(set_id, []),
               "selection": conv.ADAPTERS[set_id][4] if has_adapter else None,
               "file_spec": adapter_file_spec(set_id) or None}
        if pins and rec["source"] in pins.get("datasets", {}):
            p = pins["datasets"][rec["source"]]
            rec["hf"] = {k: p.get(k) for k in ("sha", "gated", "last_modified", "card_licence", "card_sha256")}
        records.append(rec)
    summary = {t: sorted(r["set"] for r in records if r["track"] == t) for t in ("allowed", "reserved", "owned", "hold", "out")}
    return {"schema": SCHEMA,
            "inputs_sha256": {"licence_table": hashlib.sha256((TEAM / "licences/licence_table.md").read_bytes()).hexdigest(),
                              "sft_mix_proposal": hashlib.sha256((TEAM / "sft/sft_mix_proposal.md").read_bytes()).hexdigest(),
                              "convert_py": hashlib.sha256((HERE / "convert.py").read_bytes()).hexdigest()},
            "counts": {k: len(v) for k, v in summary.items()} | {"stage1_sets": len(records), "adapters": len(conv.ADAPTERS)},
            "lists": summary, "sets": records}


def write_md(w: dict, path: Path) -> None:
    out = ["# SFT v1 work list (generated by `sft/sft_v1_worklist.py`)", "",
           "No dataset rows are read. `reserved` means TSAI has not admitted the set: its token records are measurements only.", "",
           "Inputs (sha256): " + ", ".join(f"`{k}` `{v[:12]}…`" for k, v in w["inputs_sha256"].items()), "",
           f"Stage 1 sets: {w['counts']['stage1_sets']}; adapters in `convert.py`: {w['counts']['adapters']}.", ""]
    for track, title in (("allowed", "Allowed, in the proposal, with an adapter"), ("reserved", "TSAI reserves, in the proposal, with an adapter (measurement only)"),
                         ("owned", "Owned by WP1"), ("hold", "Held for a data-rule ruling"), ("out", "Out of the work list")):
        rows = [r for r in w["sets"] if r["track"] == track]
        out += [f"## {title} ({len(rows)})", ""]
        if not rows:
            out += ["none", ""]
            continue
        out += ["| Set | Area | Decision | Reasons / flags | Pinned revision |", "|---|---|---|---|---|"]
        for r in rows:
            rev = (r.get("hf") or {}).get("sha")
            why = "; ".join(r["reasons"])
            out.append(f"| `{r['set']}` | {r['area'] or '-'} | {r['decision'][:40]} | {why} | {('`' + rev[:12] + '`') if rev else '-'} |")
        out.append("")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def fetch(path: Path) -> None:
    """Public Hub metadata for each non-excluded Stage 1 set: revision sha, gate flag, card licence, file sizes, LFS sha256."""
    licence = inv.parse_licence_stage1((TEAM / "licences/licence_table.md").read_text(encoding="utf-8"))
    repos = sorted({source_repo(r["source"]) for s, r in licence.items() if decision_class(r["decision_raw"]) != "excluded"})
    out = {"schema": SCHEMA + "-hf-pins", "datasets": {}}
    for repo in repos:
        try:
            with urllib.request.urlopen(f"https://huggingface.co/api/datasets/{repo}?blobs=true", timeout=60) as r:
                d = json.load(r)
            card = (d.get("cardData") or {})
            lic = card.get("license")
            readme = None
            try:
                with urllib.request.urlopen(f"https://huggingface.co/datasets/{repo}/resolve/{d['sha']}/README.md", timeout=60) as r:
                    readme = hashlib.sha256(r.read()).hexdigest()
            except OSError:
                pass
            out["datasets"][repo] = {
                "sha": d["sha"], "gated": d.get("gated"), "last_modified": d.get("lastModified"), "card_licence": lic,
                "card_sha256": readme,
                "files": {s["rfilename"]: {"size": s.get("size"), "lfs_sha256": (s.get("lfs") or {}).get("sha256"), "blob_id": s.get("blobId")}
                          for s in d.get("siblings", [])}}
        except OSError as exc:
            out["datasets"][repo] = {"error": f"{type(exc).__name__}: {exc}"}
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(out['datasets'])} repos, {sum('error' in v for v in out['datasets'].values())} errors")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["fetch-hf", "build"])
    ap.add_argument("--hf-pins", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    a = ap.parse_args()
    if a.command == "fetch-hf":
        fetch(a.out)
        return 0
    pins = json.loads(a.hf_pins.read_text(encoding="utf-8")) if a.hf_pins else None
    w = build(pins)
    if a.out_json:
        a.out_json.write_text(json.dumps(w, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.out_md:
        write_md(w, a.out_md)
    print(json.dumps(w["counts"]))
    for t, v in w["lists"].items():
        print(f"{t}: {len(v)}", *(v if t != "out" else []), sep="\n  " if t != "out" else " ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
