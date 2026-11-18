"""SFT data v1 pack manifest (G10, work-order task 1): one record per set in scope, and the #391 area budget.

    python sft/sft_v1_manifest.py --tokenizer p1536 --out sft/results/sft_data_v1_p1536_manifest.json
    python sft/sft_v1_manifest.py --tokenizer c3 --out <file>      # the C3 record's inputs (14-16 Nov)

Reads only files in this folder, chosen by `--tokenizer` (VARIANTS below): the admission summaries, the full
conversion records, the OCR-2 pack manifest, the loss-mask reports (counts only), the prefix records of sets whose
full build is a pending job and, for p1536, the context-length tables (`sft_v1_lengths.py`) and the OCR-2 effort-tier
report. It writes counts, hashes and revisions: no row text or id. TSAI froze p1536 on 15 Nov 2026 (Gate 3 notice);
the C3 manifest (`results/sft_data_v1_c3_manifest.json`) is kept unchanged as a record.

Context length: for every in-pack set and #391 area, the rows and tokens that fit 2,048, 4,096, 8,192 and 32,768
tokens (a row fits when its whole length does), and the #391 budget recomputed with only the rows that fit.

Scope (BLOCKED B1 fallback, no admission ruling for the TSAI-reserves sets): the sets whose licence decision is
`allowed` and the TSAI-admitted OCR-2 pack. A set is `in_pack` only when its decontamination covers the whole set;
otherwise it is listed with its status and does not count toward the area budget.

Area budget: the #391 shares are shares of the mix, not absolute sizes. With Code the only area that has a large
admitted set, the budget is anchored on it: total = Code tokens / Code share, and every other area needs share x total.
This says how far each area falls short if v1 kept Code at its admitted size; a smaller total (dropping Code rows)
scales every need down by the same factor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
SCHEMA = "g10-sft-data-v1-manifest/1"
MAX_LEN = 32768

# #391 shares (sft_mix_proposal.md section 2 and the 3 Nov revision); fallback from section 3, Area 6
SHARES = {"code": 0.35, "agentic": 0.25, "tool_use": 0.15, "indic": 0.15, "general": 0.07, "safety": 0.03}
SHARES_NO_SAFETY = {**SHARES, "general": 0.10, "safety": 0.0}

# sets in scope: allowed licence decision (or TSAI-admitted), with their #391 area
IN_SCOPE = {
    "sft-code-opencodereasoning-2": "code",
    "sft-dolly-15k": "general",
    "sft-indic-indic-align-dolly-t": "indic",
    "sft-math-nemotron-proofs": "general",
    "sft-math-nemotron-math-v2": "general",
}
JOBS = {
    "sft-math-nemotron-proofs": "jobs/2026-11-16-sft-v1-proofs-decontam.md",
    "sft-math-nemotron-math-v2": "jobs/2026-11-14-sft-v1-math-v2-full.md",
    "sft-code-opencodereasoning-2": "jobs/2026-11-17-ocr2-pack-v1-p1536.md",
}
C3_SHA256 = "15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3"
P1536_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
# input files per tokenizer. Sets without a p1536 build (Proofs, math-v2: not in the pack either way) keep their C3
# records and say so.
VARIANTS = {
    "p1536": {"sha256": P1536_SHA256, "records": "sft_v1_records_p1536", "admission": "sft_v1_admission_p1536",
              "mask_dir": "sft_v1_mask_checks_p1536", "pack_manifest": "ocr2_pack_v1_p1536_manifest.json",
              "ocr2_job": "jobs/2026-11-17-ocr2-pack-v1-p1536.md", "lengths": "sft_v1_lengths_p1536",
              "effort": "ocr2_pack_v1_p1536_effort_tiers.json", "rebuilt": ("sft-dolly-15k", "sft-indic-indic-align-dolly-t"),
              "firewall": "ocr2_eval_firewall_v1.json"},
    # the p1536 pack before the evaluation firewall (16 Nov), kept as a record like C3
    "p1536-nofirewall": {"sha256": P1536_SHA256, "records": "sft_v1_records_p1536", "admission": "sft_v1_admission_p1536",
                         "mask_dir": "sft_v1_mask_checks_p1536", "pack_manifest": "ocr2_pack_v1_p1536_manifest.json",
                         "ocr2_job": "jobs/2026-11-17-ocr2-pack-v1-p1536.md", "lengths": "sft_v1_lengths_p1536",
                         "lengths_suffix": {"sft-code-opencodereasoning-2": ".nofirewall"},
                         "effort": "ocr2_pack_v1_p1536_effort_tiers.json",
                         "rebuilt": ("sft-dolly-15k", "sft-indic-indic-align-dolly-t")},
    "c3": {"sha256": C3_SHA256, "records": "sft_v1_records", "admission": "sft_v1_admission",
           "mask_dir": "sft_v1_mask_checks", "pack_manifest": "ocr2_pack_v1_c3_manifest.json",
           "ocr2_job": "jobs/2026-11-16-ocr2-pack-v1-c3.md", "lengths": None, "effort": None,
           "rebuilt": ("sft-dolly-15k", "sft-indic-indic-align-dolly-t", "sft-math-nemotron-proofs")},
}
LIMITS = ("2048", "4096", "8192", "32768")
# what fills each area that has no admitted set (the ruling that would add it)
FILLED_BY = {
    "code": "B1: opencodereasoning, codeforces-cots, commitpackft (TSAI reserves)",
    "agentic": "B1: swe-rebench-openhands, nemotron-terminal, nemotron-cascade-swe (TSAI reserves)",
    "tool_use": "B1: agentic-v1, agentic-v2 tool-calling (TSAI reserves); B2: xlam-60k (held)",
    "indic": "B1: aya-dataset, aya-collection 10 subsets, indic-align-oasst-t (TSAI reserves); B3: templated_hindi_news",
    "general": "B1: openthoughts3, openmathreasoning, openr1-math, nemotron-science, bespoke-stratos, glm51-phd, oasst2, "
               "proofs-v3-sft (TSAI reserves); B2: nemotron-if-v1/v2, science-v2 (held); B6: Proofs decontam",
    "safety": "B7: TSAI names a safety set with chat rows, or the 0% safety / 10% general fallback",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def from_admission(set_id: str, results: Path, mask_dir: Path | None, v: dict | None = None) -> dict:
    v = v or VARIANTS["c3"]
    adm_path = results / v["admission"] / f"{set_id}.admission.json"
    rec_path = results / v["records"] / f"{set_id}.full.record.json"
    adm, rec = load(adm_path), load(rec_path)
    assert adm["record"]["content_sha256"] == rec["content_sha256"], f"{set_id}: admission bound to another conversion"
    assert rec["tokenizer_sha256"] == v["sha256"] == adm["record"]["tokenizer_sha256"], f"{set_id}: record is not {v['sha256'][:8]}"
    complete = bool(adm["decontam"]["complete"])
    out = {
        "area": IN_SCOPE[set_id], "source": rec["source"], "revision": rec["hub_revision"], "input": rec["input"],
        "selection": rec["selection"], "generator": rec["generator_model"], "licence": rec["licence"],
        "licence_decision": rec["decision"], "tokenizer_sha256": rec["tokenizer_sha256"],
        "conversion": {"rows_in": rec["rows_in"], "rows": rec["rows_out"], "tokens": rec["checks"]["tokens"],
                       "trained_tokens": rec["checks"]["trained_tokens"], "skipped": rec["skipped"],
                       "row_checks_ok": rec["checks"]["checks_ok"], "deterministic_rerun": rec["deterministic_rerun"],
                       "content_sha256": rec["content_sha256"], "parts": len(rec["parts"]),
                       "record": {"name": rec_path.name, "sha256": sha256_file(rec_path)}},
        "decontam": adm["decontam"],
        "over_length": {"max_sequence_tokens": MAX_LEN, "rows_dropped": adm["excluded_each"]["over_max_len"],
                        "kept_max_len": adm["kept_max_len"]},
        "admission": {"rows_kept": adm["rows_kept"], "tokens_kept": adm["tokens_kept"], "rows_excluded": adm["rows_excluded"],
                      "excluded_each": adm["excluded_each"], "kept_ids_sha256": adm["kept_ids_sha256"],
                      "excluded_sha256": adm["excluded_sha256"], "status": adm["status"],
                      "summary": {"name": adm_path.name, "sha256": sha256_file(adm_path)}},
        "in_pack": complete and adm["status"] == "admissible",
        "status": "admissible" if complete and adm["status"] == "admissible" else adm["status"],
    }
    out["loss_mask"] = mask_entry(set_id, mask_dir)
    if set_id in JOBS:
        out["job_request"] = JOBS[set_id]
    out["admission"]["summary"]["folder"] = v["admission"]
    out["conversion"]["record"]["folder"] = v["records"]
    return out


def from_c3_only(set_id: str, results: Path) -> dict:
    """A set with no p1536 build: its C3 records, marked as such and never in the pack."""
    out = from_admission(set_id, results, results / "sft_v1_mask_checks", VARIANTS["c3"])
    out.update(in_pack=False, status=f"C3 conversion only (not rebuilt with p1536); {out['status']}; not in the pack",
               p1536_rebuild="part of its pending job request: the rebuild runs with p1536 before decontam")
    return out


def mask_entry(set_id: str, mask_dir: Path | None) -> dict:
    if mask_dir is None:
        return {"checked": False}
    hits = sorted(mask_dir.glob(f"{set_id}*.json"))
    if not hits:
        return {"checked": False}
    r = load(hits[0])
    mask_bad = {k: v for k, v in r["violations"].items() if k != "over_limit"}
    return {"checked": True, "report": hits[0].name, "rows_checked": r["rows"], "tokens_checked": r["tokens"],
            "mask_violations": mask_bad, "rows_over_limit_before_admission": r["violations"].get("over_limit", 0),
            "trained_tokens_by_role": r["trained_tokens_by_role"], "mask_ok": not mask_bad and r["rows"] > 0,
            "scope": r.get("scope", "every converted row of the set")}


def from_ocr2(results: Path, mask_dir: Path | None, v: dict | None = None) -> dict:
    v = v or VARIANTS["c3"]
    path = results / v["pack_manifest"]
    m = load(path)
    assert m["build"]["tokenizer_sha256"] == v["sha256"], f"{path.name} is not a {v['sha256'][:8]} build"
    f = m["funnel"]
    rows, toks, tgts, fw = f["pack.train_rows"], f["train.tokens"], f["train.shifted_assistant_targets"], None
    if v.get("firewall"):
        fw = load(results / v["firewall"])
        assert fw["applied_after"]["run_id"] == m["build"]["run_id"] and all(fw["checks"].values()), "firewall record"
        assert fw["totals"]["before"] == {"rows": rows, "tokens": toks, "shifted_targets": tgts}, "firewall vs pack funnel"
        rows, toks, tgts = (fw["totals"]["after"][k] for k in ("rows", "tokens", "shifted_targets"))
    out = {
        "area": "code", "source": m["sources"]["ocr2"]["repo"], "revision": m["sources"]["ocr2"]["revision"],
        "joined_sources": {k: v["revision"] for k, v in m["sources"].items() if k.endswith("/train") and not v.get("protected")},
        "generator": "DeepSeek-R1 (MIT) for the trained reasoning and solutions; QwQ-32B (Apache-2.0) critiques are a "
                     "filter signal only, never a target (licence_table.md, ocr2_policy.json teacher)",
        "licence": "cc-by-4.0 (Hub tag); joined questions from TACO, APPS and code_contests train at pinned revisions",
        "licence_decision": "allowed (TSAI admitted, 11 Nov 2026)", "tokenizer_sha256": m["build"]["tokenizer_sha256"],
        "decontam": {"complete": m["checks"]["decontam.full_set_v2"] and m["checks"]["decontam.second_pass_zero_hits"],
                     "covers": "whole set, all 70 shards", "rows_flagged": f["screened.rows_flagged"],
                     "rows_canary": f["screened.rows_canary"], "by_benchmark": m["decontam_flagged_by_benchmark"],
                     "fingerprint_set_sha256": m["build"]["fingerprint_set_sha256"]},
        "over_length": {"max_sequence_tokens": m["build"]["max_sequence_tokens"], "rows_dropped": 0,
                        "kept_max_len": m["max_length_tokens"]},
        "heldout": {"rows": m["heldout_eval_v1"]["rows"], "families": m["heldout_eval_v1"]["families"],
                    "id_list_sha256": m["heldout_eval_v1"]["id_list_sha256"], "salt": m["heldout_eval_v1"]["rule"]["salt"],
                    "fraction": m["heldout_eval_v1"]["rule"]["fraction"]},
        "unclear_source_left_out": {"keys": m["unclear_source"]["keys"], "rows": m["unclear_source"]["rows_excluded"]},
        "admission": {"rows_kept": rows, "tokens_kept": toks, "trained_tokens": tgts,
                      "status": "admitted, pack built" + (", evaluation firewall applied" if fw else "")},
        "pack": {"run_id": m["build"]["run_id"], "shards": len(m["shards"]), "manifest": {"name": path.name, "sha256": sha256_file(path)},
                 "acceptance_checks": f"{sum(m['checks'].values())} of {len(m['checks'])}"},
        "loss_mask": ocr2_mask(m, mask_dir, v),
        "in_pack": True, "status": "admitted; pack final as built" + (" + evaluation firewall" if fw else ""),
        "job_request": v["ocr2_job"],
    }
    if fw:
        out["eval_firewall"] = {
            "record": {"name": v["firewall"], "sha256": sha256_file(results / v["firewall"])},
            "rule": fw["rule"], "families_sha256": fw["families"]["sha256"], "families": fw["families"]["count"],
            "families_in_pack": fw["families"]["in_pack"], "removed": fw["totals"]["removed"],
            "token_share_removed": fw["totals"]["token_share_removed"],
            "before": fw["totals"]["before"], "checks": f"{sum(fw['checks'].values())} of {len(fw['checks'])}"}
    return out


def ocr2_mask(m: dict, mask_dir: Path | None, v: dict) -> dict:
    if v["sha256"] == C3_SHA256:
        return {"checked": True, "mask_ok": True, "rows_checked": 32855, "tokens_checked": 212547311,
                "mask_violations": {}, "report": "ocr2_pack_v1_c3.md, Checks (14 Nov build)",
                "scope": "check_pack_rows.py on every train and held-out row of shards 0-3; shards 4-69 only by "
                         "pack_admission.py's in-pipeline recompute (ids and mask equal a fresh tokenisation), "
                         "because their bytes were deleted in the containers"}
    hits = sorted(mask_dir.glob("sft-code-opencodereasoning-2*.json")) if mask_dir else []
    if not hits:
        return {"checked": False, "note": "pack_admission.py recompute only"}
    rows = toks = 0
    bad: dict = {}
    for h in hits:
        r = load(h)
        rows, toks = rows + r["rows"], toks + r["tokens"]
        for k, n in r["violations"].items():
            bad[k] = bad.get(k, 0) + n
    return {"checked": True, "mask_ok": not bad and rows > 0, "rows_checked": rows, "tokens_checked": toks,
            "mask_violations": bad, "reports": [h.name for h in hits],
            "scope": "check_pack_rows.py on every train and held-out row of the shards whose p1536 pack bytes were kept "
                     "(see reports); every other shard by pack_admission.py's in-pipeline recompute (ids and mask equal a "
                     "fresh p1536 tokenisation), its bytes deleted after the build"}


def from_prefix(set_id: str, results: Path) -> dict:
    path = results / "sft_v1_records" / f"{set_id}.record.json"
    rec = load(path)
    c = rec["checks"]
    return {"area": IN_SCOPE[set_id], "source": rec["source"], "revision": rec["hub_revision"], "generator": rec["generator_model"],
            "licence": rec["licence"], "licence_decision": rec["decision"], "tokenizer_sha256": rec["tokenizer_sha256"],
            "prefix_record": {"name": path.name, "sha256": sha256_file(path), "scope": rec["scope"], "rows": c["rows"],
                              "tokens": c["tokens"], "rows_over_max_len": c["rows_over_max_len"], "row_checks_ok": c["checks_ok"]},
            "decontam": {"complete": False, "covers": "not run at this revision"},
            "in_pack": False, "status": "full conversion pending (job request)", "job_request": JOBS[set_id]}


def budget(sets: dict, shares: dict) -> dict:
    have = {a: 0 for a in shares}
    for s in sets.values():
        if s["in_pack"]:
            have[s["area"]] += s["admission"]["tokens_kept"]
    anchor = have["code"] / shares["code"] if have["code"] else 0
    rows = {}
    for a, share in shares.items():
        need = round(share * anchor)
        rows[a] = {"share": share, "tokens_admitted": have[a], "tokens_needed_at_code_anchor": need,
                   "fill": round(have[a] / need, 6) if need else None,
                   "shortfall_tokens": max(need - have[a], 0), "filled_by": FILLED_BY[a]}
    total = sum(have.values())
    return {"anchor": "Code at its admitted size", "total_at_anchor": round(anchor), "tokens_admitted_total": total,
            "admitted_share_by_area": {a: round(have[a] / total, 6) if total else 0 for a in shares}, "areas": rows}


def context_lengths(sets: dict, results: Path, v: dict) -> dict:
    """Rows/tokens fitting each context per in-pack set and area, and the #391 budget at each length."""
    folder = results / v["lengths"]
    per_set = {}
    for k in sorted(sets):
        if not sets[k]["in_pack"]:
            continue
        name = f"{k}{v.get('lengths_suffix', {}).get(k, '')}.json"
        t = load(folder / name)
        assert t["tokenizer_sha256"] == v["sha256"] and t["rows"] == sets[k]["admission"]["rows_kept"], k
        assert t["tokens"] == sets[k]["admission"]["tokens_kept"], f"{k}: length table tokens != admitted tokens"
        per_set[k] = {"area": sets[k]["area"], "rows": t["rows"], "tokens": t["tokens"], "length": t.get("length"),
                      "by_limit": t["by_limit"], "table": {"name": f"{v['lengths']}/{name}",
                                                           "sha256": sha256_file(folder / name)}}
    by_area, budgets = {}, {}
    for L in LIMITS:
        areas = {a: {"rows_fit": 0, "rows": 0, "tokens_fit": 0, "tokens": 0} for a in SHARES}
        for k, t in per_set.items():
            a = areas[t["area"]]
            a["rows"] += t["rows"]
            a["tokens"] += t["tokens"]
            a["rows_fit"] += t["by_limit"][L]["rows_fit"]
            a["tokens_fit"] += t["by_limit"][L]["tokens_fit"]
        for a in areas.values():
            a["tokens_fit_share"] = round(a["tokens_fit"] / a["tokens"], 6) if a["tokens"] else None
            a["rows_fit_share"] = round(a["rows_fit"] / a["rows"], 6) if a["rows"] else None
        by_area[L] = areas
        fitted = {k: {"in_pack": True, "area": t["area"], "admission": {"tokens_kept": t["by_limit"][L]["tokens_fit"]}}
                  for k, t in per_set.items()}
        b391, b10 = budget(fitted, SHARES), budget(fitted, SHARES_NO_SAFETY)
        budgets[L] = {"tokens_fit_total": b391["tokens_admitted_total"], "share_by_area": b391["admitted_share_by_area"],
                      "share_391": SHARES,
                      "fill_at_code_anchor_391": {a: r["fill"] for a, r in b391["areas"].items()},
                      "fill_at_code_anchor_no_safety_fallback": {a: r["fill"] for a, r in b10["areas"].items()}}
    code = by_area["2048"]["code"]
    return {"fit_rule": "a row fits a context of L tokens when its whole length (prompt + response + markers) is <= L; "
                        "rows that do not fit are counted as lost (cutting a row removes its answer and closing <|im_end|>)",
            "per_set": per_set, "by_area": by_area, "budget_by_limit": budgets,
            "code_at_2048": {"rows_fit_share": code["rows_fit_share"], "tokens_fit_share": code["tokens_fit_share"],
                             "rows_fit": code["rows_fit"], "tokens_fit": code["tokens_fit"]}}


def build(results: Path, mask_dir: Path | None, tokenizer: str = "c3") -> dict:
    v = VARIANTS[tokenizer]
    sets = {"sft-code-opencodereasoning-2": from_ocr2(results, mask_dir, v)}
    for s in ("sft-dolly-15k", "sft-indic-indic-align-dolly-t", "sft-math-nemotron-proofs"):
        sets[s] = from_admission(s, results, mask_dir, v) if s in v["rebuilt"] else from_c3_only(s, results)
    sets["sft-math-nemotron-math-v2"] = from_prefix("sft-math-nemotron-math-v2", results)
    extra = {}
    if v["lengths"]:
        extra["context_length"] = context_lengths(sets, results, v)
    if v["effort"]:
        e = load(results / v["effort"])
        extra["effort_tiers_ocr2"] = {k: e[k] for k in ("rule", "rows_checked", "rows_changing_tier", "to_higher_tier",
                                                         "to_lower_tier", "rows_changing_tier_in_train_pack",
                                                         "matrix_c3_to_p1536_all_rendered", "tier_totals_rendered")} | {
            "report": {"name": v["effort"], "sha256": sha256_file(results / v["effort"])},
            "other_sets": "Dolly and dolly-t: every row is 1k under both tokenizers (no trace); 0 rows change tier"}
    if v["sha256"] == P1536_SHA256:
        tok = {"sha256": P1536_SHA256, "name": "p1536",
               "note": "every count here is p1536 (TSAI Gate 3 notice, 15 Nov 2026; instructor to G10, 16 Nov: rebuild SFT "
                       "data v1 with p1536). Special tokens and ids are those of C3 (356 added, eos 130822), vocabulary "
                       "131,072. The C3 manifest stays as a record: results/sft_data_v1_c3_manifest.json. Proofs and "
                       "math-v2 are listed from their C3 records and are not in the pack.",
               "c3_record": {"name": "sft_data_v1_c3_manifest.json",
                             "sha256": sha256_file(results / "sft_data_v1_c3_manifest.json")
                             if (results / "sft_data_v1_c3_manifest.json").is_file() else None}}
        if v.get("firewall"):
            tok["firewall_note"] = ("OCR-2 counts are after the SFT/RL evaluation firewall (lead, 16 Nov; "
                                    "results/ocr2_eval_firewall_v1.json). The p1536 manifest before it stays as a record: "
                                    "results/sft_data_v1_p1536_nofirewall_manifest.json.")
    else:
        tok = {"sha256": C3_SHA256, "name": "C3",
               "note": "every count here is C3. TSAI's Gate 3 notice (15 Nov 2026) moved new work to p1536 "
                       "(sha256 e6b93a93...; same special ids, eos 130822, same vocabulary size). Transfer "
                       "measured on Dolly, dolly-t, OCR-2 shards 0-3 and 10 Proofs parts: "
                       "results/sft_v1_p1536_transfer.json"}
    return {
        "schema": SCHEMA,
        "scope": "BLOCKED B1 fallback: sets with an allowed licence decision plus the TSAI-admitted OCR-2 pack; no "
                 "TSAI-reserves set is in scope until admitted",
        "tokenizer": tok,
        "max_sequence_tokens": MAX_LEN,
        "loss_mask_rule": "assistant bodies and their closing <|im_end|> are trained; system, user, tool results, role "
                          "headers, <|im_start|> and the final <|endoftext|> (130822) are not",
        "sets": sets,
        "in_pack": sorted(k for k, v in sets.items() if v["in_pack"]),
        "budget_391": budget(sets, SHARES),
        "budget_no_safety_fallback": budget(sets, SHARES_NO_SAFETY),
        **extra,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", choices=sorted(VARIANTS), default="p1536")
    ap.add_argument("--results", type=Path, default=RESULTS)
    ap.add_argument("--mask-dir", type=Path, help="default: the variant's mask-check folder")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    mask_dir = a.mask_dir or a.results / VARIANTS[a.tokenizer]["mask_dir"]
    m = build(a.results, mask_dir if mask_dir.is_dir() else None, a.tokenizer)
    a.out.write_text(json.dumps(m, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    b = m["budget_391"]
    print(f"in pack: {', '.join(m['in_pack'])}; admitted tokens {b['tokens_admitted_total']:,}")
    for area, r in b["areas"].items():
        fill = "n/a" if r["fill"] is None else f"{r['fill']:.2%}"
        print(f"  {area:<9} share {r['share']:.0%} admitted {r['tokens_admitted']:>14,} need {r['tokens_needed_at_code_anchor']:>14,} fill {fill}")
    if "context_length" in m:
        c = m["context_length"]["code_at_2048"]
        print(f"code at 2,048 tokens: {c['rows_fit_share']:.1%} of rows, {c['tokens_fit_share']:.1%} of tokens fit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
