"""Cross-stage overlap record: SFT data v1 (the OCR-2 pack) against the RL side, one row per distinct problem (G10).

The pack has 418,496 training rows but only ~15k distinct source problems: every OCR-2 row names a problem
`(dataset, split, ordinal)` in TACO, APPS or code_contests, and the build stores the problem's content identity
(`family`, `source_index.family_sha256`). This module matches RL problems to those problems, never to rows, then
counts pack rows and tokens per problem from the per-row stats the build wrote.

Matching tiers, strongest first. A pair is reported once, at its strongest tier:
  key       same `family_sha256`: byte-equal statement after NFC and whitespace collapse
  norm      same statement after lower-casing and keeping only [a-z0-9] words
  shingle   at least CONFIRM of the RL statement's 13-word shingles occur in one pack statement
  possible  between POSSIBLE and CONFIRM: mostly sibling problems of one series that share template text
            (stack / queue / priority queue; RMQ / RSQ). Not counted as a match; kept as an upper bound.
key, norm and shingle are "confirmed". The first rule (13-word shingles, at least 20% coverage, run on 16 Nov by the
G10 recipe session) counted `possible` as a match; reading 30 such pairs found 22 siblings
(see `sft/results/cross_stage_overlap_v1.md`, section Validation), so the confirm level was raised to 0.65 (the middle of the empty stretch 0.615 to 0.70 between the
highest sibling and the lowest true copy that were read).

The module reads private inputs and writes private key lists plus a public record of counts and hashes. It adds
flags only; it changes neither the pack nor the RL pool.

    python cross_stage_overlap.py build --source-index source_index.sqlite --rowstats-dir DIR [--rowstats-dir DIR]
        --rl-cc cc.jsonl --pool-ids pool.txt --set NAME=ids.txt ... --effort-manifest effort_manifest.json
        --rung-ids rung1.txt --sft-manifest sft_data_v1_manifest.json
        [--pack-manifest ocr2_pack_v1_p1536_manifest.json]
        --private-dir PRIVATE/ --out-json cross_stage_overlap_v1.json --validation validation.json --out-md cross_stage_overlap_v1.md
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "g10-cross-stage-overlap/1"
SHINGLE_WORDS = 13
CONFIRM = 0.65
POSSIBLE = 0.20
BAND = 0.05           # sensitivity window around CONFIRM
HELDOUT_SET = "heldout_e1_15nov"
EFFORT_SET = "effort_suite_code"
CONFIRMED = ("key", "norm", "shingle")
TIERS = CONFIRMED + ("possible",)
_RANK = {"key": 0, "norm": 1, "shingle": 2, "possible": 3, "near": 4}
_WORD = re.compile(r"[a-z0-9]+")


# --- the matcher (pure functions) --------------------------------------------------------------

def exact_key(text: str) -> str:
    """Same function as `source_index.family_sha256`: NFC, whitespace collapsed, sha256."""
    return hashlib.sha256(" ".join(unicodedata.normalize("NFC", text).split()).encode("utf-8")).hexdigest()


def words(text: str) -> list[str]:
    return _WORD.findall(unicodedata.normalize("NFC", text).lower())


def norm_key(text: str) -> str:
    return hashlib.sha256(" ".join(words(text)).encode("utf-8")).hexdigest()


def shingles(text: str, n: int = SHINGLE_WORDS) -> set[str]:
    w = words(text)
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


@dataclass(frozen=True)
class Match:
    pack_key: str
    tier: str           # key | norm | shingle | possible | near
    coverage: float     # share of the RL statement's shingles found in the pack statement; 1.0 for key and norm


def match(rl: dict[str, str], pack: dict[str, str], n: int = SHINGLE_WORDS, confirm: float = CONFIRM,
          possible: float = POSSIBLE, floor: float | None = None) -> dict[str, list[Match]]:
    """RL id -> its matches in the pack, strongest tier first. Both maps are id/key -> statement text.

    An RL statement with fewer than `n` words has no shingles and can match only by key or norm.
    `floor` (default: no near misses) also returns pairs with coverage in [floor, possible) as tier "near";
    that is for reading near misses by hand, `summarise` never counts them.
    """
    if not 0 < possible <= confirm <= 1:
        raise ValueError("need 0 < possible <= confirm <= 1")
    rl_exact: dict[str, list[str]] = collections.defaultdict(list)
    rl_norm: dict[str, list[str]] = collections.defaultdict(list)
    rl_sh: dict[str, set[str]] = {}
    index: dict[str, set[str]] = collections.defaultdict(set)
    for rid, text in rl.items():
        rl_exact[exact_key(text)].append(rid)
        rl_norm[norm_key(text)].append(rid)
        rl_sh[rid] = shingles(text, n)
        for x in rl_sh[rid]:
            index[x].add(rid)
    low = possible if floor is None else min(floor, possible)
    out: dict[str, dict[str, Match]] = collections.defaultdict(dict)
    for pk, text in pack.items():
        for rid in rl_exact.get(exact_key(text), ()):
            out[rid][pk] = Match(pk, "key", 1.0)
        for rid in rl_norm.get(norm_key(text), ()):
            out[rid].setdefault(pk, Match(pk, "norm", 1.0))
        hits: collections.Counter = collections.Counter()
        for x in shingles(text, n):
            for rid in index.get(x, ()):
                hits[rid] += 1
        for rid, h in hits.items():
            if pk in out.get(rid, ()):
                continue
            cov = h / len(rl_sh[rid])
            if cov >= confirm:
                out[rid][pk] = Match(pk, "shingle", cov)
            elif cov >= possible:
                out[rid][pk] = Match(pk, "possible", cov)
            elif cov >= low:
                out[rid][pk] = Match(pk, "near", cov)
    return {rid: sorted(d.values(), key=lambda m: (_RANK[m.tier], -m.coverage, m.pack_key)) for rid, d in out.items()}


def confirmed_pack_keys(matches: list[Match]) -> set[str]:
    return {m.pack_key for m in matches if m.tier in CONFIRMED}


def best_tier(matches: list[Match]) -> str | None:
    tiers = [m.tier for m in matches if m.tier in TIERS]
    return min(tiers, key=_RANK.__getitem__) if tiers else None


# --- inputs ------------------------------------------------------------------------------------

def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ids_sha256(ids) -> str:
    """The convention of rl_v1_close.py: sorted ids, one per line, trailing newline."""
    return hashlib.sha256(("\n".join(sorted(ids)) + "\n").encode()).hexdigest()


def read_ids(path) -> list[str]:
    return [x for x in Path(path).read_text().split() if x]


def load_rowstats(dirs: list[str]) -> tuple[dict[int, list[dict]], list[str]]:
    """Per-row build stats of the pack, by shard: {shard: [row dict]}; plus the sorted file hashes."""
    by_shard: dict[int, list[dict]] = {}
    hashes = []
    for d in dirs:
        for f in sorted(Path(d).glob("shard-*.jsonl.gz")):
            shard = int(re.search(r"shard-(\d+)", f.name).group(1))
            if shard in by_shard:
                raise ValueError(f"shard {shard} appears in two row-stat folders")
            with gzip.open(f, "rt", encoding="utf-8") as stream:
                by_shard[shard] = [json.loads(line) for line in stream if line.strip()]
            hashes.append(f"{f.name}:{sha256_file(f)}")
    return by_shard, sorted(hashes)


def pack_problems(by_shard: dict[int, list[dict]], status: str = "pack") -> dict[str, dict]:
    """family -> {"rows": {shard: n}, "tokens": {shard: n}, "trained": {shard: n}, "sources": Counter} over the rows with
    this status ("pack" = SFT training rows, "heldout" = the OCR-2 held-out eval rows)."""
    fams: dict[str, dict] = {}
    for shard, rows in by_shard.items():
        for r in rows:
            if r["status"] != status:
                continue
            f = fams.setdefault(r["family"], {"rows": collections.Counter(), "tokens": collections.Counter(),
                                              "trained": collections.Counter(), "sources": collections.Counter()})
            f["rows"][shard] += 1
            f["tokens"][shard] += r["tokens"]
            f["trained"][shard] += r["trained"]
            f["sources"][r["source"]] += 1
    return fams


def pack_statements(index_path, families: list[str]) -> dict[str, str]:
    """family key ('sha256:<hex>') -> statement text, from the source index (read-only). Protected splits have no text."""
    con = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    text = {}
    for fam in families:
        row = con.execute("SELECT question FROM rows WHERE family_sha256 = ? AND question IS NOT NULL ORDER BY source_key, ordinal LIMIT 1",
                          (fam.split(":", 1)[-1],)).fetchone()
        if row:
            text[fam] = row[0]
    con.close()
    return text


# --- the record --------------------------------------------------------------------------------

def per_shard_totals(fams: dict[str, dict], keys, shards: int) -> dict:
    rows = [0] * shards
    tokens = [0] * shards
    for k in keys:
        for s, n in fams[k]["rows"].items():
            rows[s] += n
        for s, n in fams[k]["tokens"].items():
            tokens[s] += n
    return {"rows": rows, "tokens": tokens, "rows_total": sum(rows), "tokens_total": sum(tokens)}


def sensitivity(rl_ids: list[str], matches: dict[str, list[Match]], confirm: float = CONFIRM, band: float = BAND) -> dict:
    """How far the confirmed count moves if the confirm level is shifted by `band`.

    Only problems whose status rests on shingle coverage count: a key or norm match does not depend on the level. For each such
    problem the best coverage over its shingle and possible pairs decides its tier.
    """
    below = above = 0
    for r in rl_ids:
        ms = matches.get(r, [])
        if any(m.tier in ("key", "norm") for m in ms):
            continue
        cov = [m.coverage for m in ms if m.tier in ("shingle", "possible")]
        if not cov:
            continue
        best = max(cov)
        if confirm - band <= best < confirm:
            below += 1
        elif confirm <= best < confirm + band:
            above += 1
    return {"band": band, "possible_with_coverage_in_band_below_confirm": below,
            "confirmed_with_coverage_in_band_above_confirm": above,
            "reading": "the confirmed count would rise by the first number if the level were confirm - band, and fall by the second if it were confirm + band"}


def summarise(rl_ids: list[str], matches: dict[str, list[Match]], fams: dict[str, dict],
              nshards: int) -> tuple[dict, dict]:
    """Public counts and private key lists for one RL-side set."""
    found = [r for r in rl_ids if best_tier(matches.get(r, [])) in CONFIRMED]
    poss = [r for r in rl_ids if best_tier(matches.get(r, [])) == "possible"]
    packs = set()
    for r in found:
        packs |= confirmed_pack_keys(matches[r])
    # route: does a confirmed pack problem reach the pack through a code_contests row, or only through TACO/APPS rows?
    via_cc = [r for r in found if any(fams[k]["sources"].get("code_contests") for k in confirmed_pack_keys(matches[r]))]
    other_only = [r for r in found if r not in set(via_cc)]
    other_route = [r for r in found if any(any(s != "code_contests" for s in fams[k]["sources"])
                                           for k in confirmed_pack_keys(matches[r]))]
    pub = {
        "rl_problems": len(rl_ids),
        "sensitivity_to_confirm": sensitivity(rl_ids, matches),
        "found_in_pack": len(found),
        "found_by_tier": dict(collections.Counter(best_tier(matches[r]) for r in found)),
        "possible_only": len(poss),
        "distinct_pack_problems": len(packs),
        "reached_through_code_contests_rows": len(via_cc),
        "reached_only_through_taco_or_apps_rows": len(other_only),
        "reached_also_through_taco_or_apps_rows": len(other_route),
        "pack": per_shard_totals(fams, packs, nshards),
    }
    poss_packs = set()
    for r in poss:
        poss_packs |= {m.pack_key for m in matches[r] if m.tier == "possible"}
    priv = {"found": sorted(found), "possible_only": sorted(poss), "pack_families": sorted(packs),
            "possible_pack_families": sorted(poss_packs),
            "only_taco_apps": sorted(other_only),
            "tier_and_coverage": {r: [best_tier(matches[r]), round(max(m.coverage for m in matches[r]
                                                                       if m.tier in TIERS), 4)] for r in found + poss}}
    return pub, priv


def size_choices(sets: dict[str, list[str]], private: dict[str, dict], fams: dict[str, dict], rung: list[str],
                 other_area_tokens: int, eval_sets: list[str], nshards: int) -> dict:
    """What each choice costs. The numbers only size the choices; none of them is applied here."""
    pack_rows = sum(sum(f["rows"].values()) for f in fams.values())
    pack_tokens = sum(sum(f["tokens"].values()) for f in fams.values())

    def drop(keys: set[str]) -> dict:
        t = per_shard_totals(fams, keys, nshards)
        return {"pack_problems": len(keys), "rows": t["rows_total"], "tokens": t["tokens_total"],
                "share_of_pack_rows": round(t["rows_total"] / pack_rows, 4),
                "share_of_pack_tokens": round(t["tokens_total"] / pack_tokens, 4),
                "share_of_v1_admitted_tokens": round(t["tokens_total"] / (pack_tokens + other_area_tokens), 4),
                "tokens_per_shard_min_max": [min(t["tokens"]), max(t["tokens"])]}

    for name in ("rl_code_pool", HELDOUT_SET, EFFORT_SET):
        if name not in private:
            raise ValueError(f"set {name!r} is missing: the sizing needs it (got {sorted(private)}); pass --set {name}=ids.txt")
    for name in eval_sets:
        if name not in private:
            raise ValueError(f"evaluation set {name!r} has no summary")
    pool_keys = set(private["rl_code_pool"]["pack_families"])
    eval_keys: set[str] = set()
    eval_poss: set[str] = set()
    for n in eval_sets:
        eval_keys |= set(private[n]["pack_families"])
        eval_poss |= set(private[n]["possible_pack_families"])
    narrow_keys = set(private[HELDOUT_SET]["pack_families"]) | set(private[EFFORT_SET]["pack_families"])
    narrow_poss = set(private[HELDOUT_SET]["possible_pack_families"]) | set(private[EFFORT_SET]["possible_pack_families"])
    found_pool = set(private["rl_code_pool"]["found"])
    rung_found = [r for r in rung if r in found_pool]
    return {
        "basis": "pack problems matched at a confirmed tier; v1 admitted tokens = pack tokens + Dolly + dolly-t (C3 counts "
                 "from the v1 manifest, 0.2% of the mix); the `incl_possible_upper_bound` rows add the pack problems of the `possible` tier",
        "sft_drop_pool_overlap": drop(pool_keys),
        "sft_drop_pool_overlap_incl_possible_upper_bound": drop(pool_keys | set(private["rl_code_pool"]["possible_pack_families"])),
        "sft_drop_eval_sets_only": drop(eval_keys),
        "sft_drop_eval_sets_only_incl_possible_upper_bound": drop(eval_keys | eval_poss),
        "sft_drop_e1_heldout_and_effort": drop(narrow_keys),
        "sft_drop_e1_heldout_and_effort_incl_possible_upper_bound": drop(narrow_keys | narrow_poss),
        "sft_drop_pool_overlap_and_eval": drop(pool_keys | eval_keys),
        "rl_drop_pool_overlap": {"pool_problems": len(sets["rl_code_pool"]), "dropped": len(found_pool),
                                 "left": len(sets["rl_code_pool"]) - len(found_pool),
                                 "easiest_rung_problems": len(rung), "easiest_rung_dropped": len(rung_found),
                                 "easiest_rung_left": len(rung) - len(rung_found)},
        "eval_sets": eval_sets,
    }


def shard_slice(rl_ids: list[str], matches: dict[str, list[Match]], fams: dict[str, dict], shards: range) -> dict:
    """The same count restricted to some shards, to compare with the 4-shard count of 16 Nov."""
    def reaches(r: str, tiers) -> bool:
        return any(m.tier in tiers and any(s in shards for s in fams[m.pack_key]["rows"]) for m in matches.get(r, []))
    rows = 0
    keys = set()
    for r in rl_ids:
        keys |= {m.pack_key for m in matches.get(r, []) if m.tier in CONFIRMED}
    for k in keys:
        rows += sum(n for s, n in fams[k]["rows"].items() if s in shards)
    return {"shards": [shards.start, shards.stop - 1], "rl_problems_confirmed_with_rows_there": sum(reaches(r, CONFIRMED) for r in rl_ids),
            "rl_problems_confirmed_or_possible_with_rows_there": sum(reaches(r, TIERS) for r in rl_ids),
            "pack_rows_of_confirmed_problems": rows}


def effort_code_ids(manifest: dict) -> list[str]:
    return [s["task_id"] for s in manifest["slots"] if s.get("category") == "code" and s.get("task_id")]


def build(args) -> dict:
    cc = {}
    for line in open(args.rl_cc, encoding="utf-8"):
        row = json.loads(line)
        cc[row["id"]] = row["statement"]
    manifest = json.load(open(args.effort_manifest, encoding="utf-8"))
    sets = {"rl_code_pool": read_ids(args.pool_ids)}
    for spec in args.set:
        name, _, path = spec.partition("=")
        sets[name] = read_ids(path)
    sets["effort_suite_code"] = effort_code_ids(manifest)
    by_shard, row_hashes = load_rowstats(args.rowstats_dir)
    fams = pack_problems(by_shard)
    text = pack_statements(args.source_index, sorted(fams))
    missing = sorted(set(fams) - set(text))
    if missing:
        raise SystemExit(f"{len(missing)} pack families have no statement in the source index: not a complete join")
    wanted = {i for ids in sets.values() for i in ids}
    absent = sorted(wanted - set(cc))
    if absent:
        raise SystemExit(f"{len(absent)} RL ids are not in the RL v1 code file (first: {absent[0]})")
    matches = match({i: cc[i] for i in sorted(wanted)}, text)
    public_sets, private_sets = {}, {}
    for name, ids in sets.items():
        public_sets[name], private_sets[name] = summarise(ids, matches, fams, len(by_shard))
    held_fams = pack_problems(by_shard, "heldout")
    held_text = pack_statements(args.source_index, sorted(held_fams))
    pool_text = {i: cc[i] for i in sets["rl_code_pool"]}
    held_matches = match(pool_text, held_text)
    held_pub, held_priv = summarise(sets["rl_code_pool"], held_matches, held_fams, len(by_shard))
    held_pub["ocr2_heldout_problems"] = len(held_fams)
    held_pub["ocr2_heldout_rows"] = sum(sum(f["rows"].values()) for f in held_fams.values())
    rung = read_ids(args.rung_ids)
    other = 0
    sft = json.load(open(args.sft_manifest, encoding="utf-8"))
    for name, spec in sft["sets"].items():
        if spec.get("in_pack") and spec.get("area") != "code":
            other += spec["admission"]["tokens_kept"]
    eval_sets = [n for n in sets if n not in ("rl_code_pool",)]
    sizing = size_choices(sets, private_sets, fams, rung, other, eval_sets, len(by_shard))
    totals = per_shard_totals(fams, set(fams), len(by_shard))
    status = collections.Counter()
    for rows in by_shard.values():
        for r in rows:
            status[r["status"]] += 1
    record = {
        "schema": SCHEMA,
        "rule": {"shingle_words": SHINGLE_WORDS, "confirm_coverage": CONFIRM, "possible_coverage": POSSIBLE,
                 "tiers": "key (same family_sha256), norm (same lower-cased [a-z0-9] words), shingle (RL coverage >= confirm); "
                          "possible (coverage in [possible, confirm)) is reported apart and never counted as a match",
                 "unit": "distinct problem: the pack's family key (sha256 of the whitespace-normalised statement)"},
        "pack": {"problems": len(fams), "rows": totals["rows_total"], "tokens": totals["tokens_total"],
                 "token_basis": "p1536 token counts from the build's per-row stats", "shards": len(by_shard),
                 "row_status_counts": dict(status), "per_shard": {"rows": totals["rows"], "tokens": totals["tokens"]}},
        "sets": public_sets,
        "sizing": sizing,
        "ocr2_heldout_vs_rl_pool": held_pub,
        "reconciliation_4_shards": shard_slice(sets["rl_code_pool"], matches, fams, range(0, 4)),
        "inputs": {"rl_cc_sha256": sha256_file(args.rl_cc), "effort_manifest_sha256": sha256_file(args.effort_manifest),
                   "source_index_sha256": sha256_file(args.source_index),
                   "pack_manifest_sha256": sha256_file(args.pack_manifest) if args.pack_manifest else None,
                   "rowstats_files": len(row_hashes),
                   "rowstats_sha256": hashlib.sha256("\n".join(row_hashes).encode()).hexdigest(),
                   "id_lists_sha256": {n: ids_sha256(ids) for n, ids in sets.items()},
                   "set_sizes": {n: len(ids) for n, ids in sets.items()},
                   "rung_ids_sha256": ids_sha256(rung),
                   "sft_manifest_sha256": sha256_file(args.sft_manifest)},
        "validation": json.load(open(args.validation, encoding="utf-8")) if args.validation else None,
        "private": {"note": "key lists, tiers and coverage per RL id stay in the private folder; not part of the record"},
    }
    private = Path(args.private_dir)
    private.mkdir(parents=True, exist_ok=True)
    private_sets["_ocr2_heldout_vs_rl_pool"] = held_priv
    (private / "cross_stage_overlap_keys.json").write_text(json.dumps(private_sets, indent=1, sort_keys=True))
    (private / "cross_stage_overlap_matches.json").write_text(json.dumps(
        {r: [[m.pack_key, m.tier, round(m.coverage, 4)] for m in ms] for r, ms in matches.items()}, sort_keys=True))
    return record


def _n(x: int) -> str:
    return f"{x:,}"


def render_md(rec: dict) -> str:
    """The public report from the record: counts and hashes only."""
    P, S, Z = rec["pack"], rec["sets"], rec["sizing"]
    known = {"rl_code_pool": "(a) RL data v1 code pool", "heldout_e1_15nov": "(b1) RL held-out, 15 Nov runs (E1; includes the pilot's 48)",
             "heldout_e10_planned": "(b2) RL held-out, E10 plan", "effort_suite_code": "(c) effort suite, code slots"}
    out = ["# Cross-stage overlap: SFT data v1 (OCR-2 pack) against the RL side", "",
           "Record `cross_stage_overlap_v1.json`, built by `cross_stage_overlap.py`. Counts and hashes only: no statement text,",
           "problem id or key is in this file. The key lists are private. Nothing in the pack or the RL pool was changed;",
           "this record is the flags a later ruling can apply.", "",
           f"The unit is the distinct problem. The pack has {_n(P['rows'])} training rows over {_n(P['problems'])} distinct problems "
           f"({P['shards']} shards; tokens {_n(P['tokens'])}, {P['token_basis']}).", "",
           "## Result", "",
           "| RL-side set | RL problems | Found in the pack (confirmed) | key / norm / shingle | Also `possible` only | Distinct pack problems | Pack rows | Pack tokens |",
           "|---|---:|---:|---|---:|---:|---:|---:|"]
    names = {k: known.get(k, k) for k in S}
    for k, label in names.items():
        s = S[k]
        t = s["found_by_tier"]
        out.append(f"| {label} | {_n(s['rl_problems'])} | {_n(s['found_in_pack'])} ({s['found_in_pack'] / s['rl_problems']:.0%}) | "
                   f"{t.get('key', 0)} / {t.get('norm', 0)} / {t.get('shingle', 0)} | {s['possible_only']} | "
                   f"{_n(s['distinct_pack_problems'])} | {_n(s['pack']['rows_total'])} | {_n(s['pack']['tokens_total'])} |")
    out += ["", "The sets overlap: (b1) and (b2) are drawn from the pool, the effort suite is not in the pool (the close flag removes it). "
            "No RL held-out set is defined in RL data v1 itself (`rl_data_v1_close.json` has no held-out flag); (b1) and (b2) are the lists "
            "the 15 Nov experiments and the E10 plan used.", "",
            "Route into the pack (confirmed matches). A match by dataset id alone would find only the code_contests route.", "",
            "| Set | Through code_contests rows | Only through TACO or APPS rows | Also through TACO or APPS rows |", "|---|---:|---:|---:|"]
    for k, label in names.items():
        s = S[k]
        out.append(f"| {label} | {_n(s['reached_through_code_contests_rows'])} | {_n(s['reached_only_through_taco_or_apps_rows'])} | "
                   f"{_n(s['reached_also_through_taco_or_apps_rows'])} |")
    r = rec["reconciliation_4_shards"]
    out += ["", f"Per shard: the JSON holds rows and tokens for all {P['shards']} shards for each set. Pool overlap per shard ranges "
            f"{_n(min(S['rl_code_pool']['pack']['rows']))} to {_n(max(S['rl_code_pool']['pack']['rows']))} rows.", "",
            "Against the 4-shard count of 16 Nov (the G10 recipe session's measurement: 2,384 of 3,577 with a statement in shards 0-3, "
            f"first rule): the same four shards under this rule give {_n(r['rl_problems_confirmed_with_rows_there'])} confirmed and "
            f"{_n(r['rl_problems_confirmed_or_possible_with_rows_there'])} confirmed or possible, {_n(r['pack_rows_of_confirmed_problems'])} pack rows. "
            "The old count was over the rendered user turn of each row and the old rule counted siblings; this one is over distinct problems.", ""]
    v = rec.get("validation")
    if v:
        f, n, k = v["first_rule"], v["near_misses"], v["key_tier"]
        out += ["## Validation (read on 16 Nov, private)", "",
                f"- First rule (13-word shingles, at least 20% of the RL statement, whole pool): {f['shingle_pairs_read']} non-exact pairs read: "
                f"{f['same_problem']} the same problem, {f['sibling_problem_of_same_series']} a sibling problem of the same series "
                f"(precision {f['precision_of_the_shingle_tier']:.0%}). Band 0.20 to 0.65: {f['by_band']['0.20-0.65']['same']} of "
                f"{f['by_band']['0.20-0.65']['pairs']} the same. Band 0.65 and above: {f['by_band']['0.65+']['same']} of {f['by_band']['0.65+']['pairs']} the same "
                f"(the differences were exponent and ordinal formatting). Highest sibling coverage {f['largest_sibling_coverage']}.",
                f"- Normalised-text tier: {v['norm_tier']['same_problem']} of {v['norm_tier']['pairs_read']} read are the same problem (markup differences only).",
                f"- Exact-key tier: identical text by construction; {k['rl_statements_read']} shortest RL statements read for stub collisions: {k['note'].split(': ', 1)[1]}.",
                f"- Near misses just under the first rule (coverage 0.09 to 0.20): {n['pairs_read']} read, {n['different_problem']} different problems, "
                f"{n['uncertain_same_task_other_wording']} same task in other wording (not counted), 0 the same statement. "
                "No missed copy was found there; this says nothing about copies whose text was rewritten more.",
                f"- Change made once, after reading: {v['change_after_reading']}. The {v['in_sample_note'].split('the ', 1)[1]}.", ""]
    out += ["## Sizing the choices (no choice is made here)", "",
            "| Choice | Pack problems | Pack rows | Pack tokens | Share of pack rows | Share of pack tokens | Share of v1 admitted tokens |", "|---|---:|---:|---:|---:|---:|---:|"]
    for k, label in (("sft_drop_pool_overlap", "(i) SFT drops every problem found in the RL pool"),
                     ("sft_drop_eval_sets_only", "minimum: SFT drops problems of (b1), (b2), (c) only"),
                     ("sft_drop_eval_sets_only_incl_possible_upper_bound", "minimum, counting the `possible` tier too (upper bound)"),
                     ("sft_drop_e1_heldout_and_effort", "minimum, narrower: (b1) and (c) only"),
                     ("sft_drop_e1_heldout_and_effort_incl_possible_upper_bound", "minimum, narrower, counting the `possible` tier too (upper bound)"),
                     ("sft_drop_pool_overlap_and_eval", "(i) plus the minimum"),
                     ("sft_drop_pool_overlap_incl_possible_upper_bound", "(i) counting the `possible` tier too (upper bound)")):
        d = Z[k]
        out.append(f"| {label} | {_n(d['pack_problems'])} | {_n(d['rows'])} | {_n(d['tokens'])} | {d['share_of_pack_rows']:.1%} | "
                   f"{d['share_of_pack_tokens']:.1%} | {d['share_of_v1_admitted_tokens']:.1%} |")
    out += ["", "Shares are of the pack's rows and of the pack's tokens (two different columns: a problem's rows are not all the same length, "
            "so the two shares differ).", ""]
    out += ["## Sensitivity to the confirm level", "",
            f"The confirm level ({rec['rule']['confirm_coverage']}) was set after reading pairs. How many problems sit within "
            f"{S['rl_code_pool']['sensitivity_to_confirm']['band']} of it (only problems that rest on shingle coverage; key and norm matches do not depend on it):", "",
            "| RL-side set | `possible` with best coverage just below the level (would be confirmed at level - band) | confirmed with best coverage just above it (would drop at level + band) |",
            "|---|---:|---:|"]
    for k, label in names.items():
        t = S[k]["sensitivity_to_confirm"]
        out.append(f"| {label} | {t['possible_with_coverage_in_band_below_confirm']} | {t['confirmed_with_coverage_in_band_above_confirm']} |")
    out.append("")
    d = Z["rl_drop_pool_overlap"]
    h = rec["ocr2_heldout_vs_rl_pool"]
    out += ["", f"The other direction: the OCR-2 held-out eval split ({_n(h['ocr2_heldout_rows'])} rows, {_n(h['ocr2_heldout_problems'])} problems) "
            f"against the RL pool: {_n(h['found_in_pack'])} pool problems ({h['found_in_pack'] / h['rl_problems']:.0%}) are in it, "
            f"{_n(h['distinct_pack_problems'])} held-out problems, {_n(h['pack']['rows_total'])} held-out rows "
            f"({h['found_by_tier'].get('key', 0)} key / {h['found_by_tier'].get('norm', 0)} norm / {h['found_by_tier'].get('shingle', 0)} shingle). "
            "Keeping the held-out split out of the RL training pool would drop these pool problems."]
    out += ["", f"(ii) RL drops every pool problem found in the pack: {_n(d['dropped'])} of {_n(d['pool_problems'])} go, {_n(d['left'])} stay; "
            f"of the {d['easiest_rung_problems']} easiest-rung problems {d['easiest_rung_dropped']} go and {d['easiest_rung_left']} stay.", "",
            "Mix areas: the pack is the whole code area and 99.8% of the admitted v1 tokens, so its share of lost tokens is also the code area's "
            "share lost. The other areas hold almost nothing admitted (`sft_data_v1.md`, area budget); a budget anchored on the code area "
            "shrinks every area's need with it.",
            "",
            "`Distinct pack problems` counts family keys: one RL problem can match two (the same text under TACO and under APPS), so it can "
            "exceed the number of RL problems found.", ""]
    out += ["## Rule and inputs", "", f"Rule: {rec['rule']['tiers']}. Shingles: {rec['rule']['shingle_words']} words, confirm at "
            f"{rec['rule']['confirm_coverage']}, possible from {rec['rule']['possible_coverage']}.", "", "| Input | sha256 or size |", "|---|---|"]
    i = rec["inputs"]
    for k in ("rl_cc_sha256", "effort_manifest_sha256", "source_index_sha256", "rowstats_sha256", "pack_manifest_sha256",
              "rung_ids_sha256", "sft_manifest_sha256"):
        if i.get(k):
            out.append(f"| {k} | `{i[k]}` |")
    for n_, h in i["id_lists_sha256"].items():
        out.append(f"| id list {n_} ({i['set_sizes'][n_]}) | `{h}` |")
    out.append(f"| row-stat files | {i['rowstats_files']} |")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--source-index", required=True)
    b.add_argument("--rowstats-dir", action="append", required=True)
    b.add_argument("--rl-cc", required=True)
    b.add_argument("--pool-ids", required=True)
    b.add_argument("--set", action="append", default=[], help="NAME=ids.txt (an RL held-out or evaluation list)")
    b.add_argument("--effort-manifest", required=True)
    b.add_argument("--rung-ids", required=True, help="the easiest-rung problem ids (a subset of the pool)")
    b.add_argument("--sft-manifest", required=True, help="sft_data_v1_manifest.json (tokens of the non-code sets)")
    b.add_argument("--pack-manifest", help="ocr2_pack_v1_p1536_manifest.json: its sha256 is recorded next to the row-stat hash, "
                                           "so the pack totals can be checked against the merged manifest")
    b.add_argument("--validation", help="counts-only JSON of the hand read (kept with the record)")
    b.add_argument("--private-dir", required=True)
    b.add_argument("--out-json", required=True)
    b.add_argument("--out-md", required=True)
    args = ap.parse_args(argv)
    record = build(args)
    Path(args.out_json).write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    Path(args.out_md).write_text(render_md(record))
    print(json.dumps({n: {k: s[k] for k in ("rl_problems", "found_in_pack", "distinct_pack_problems")}
                      for n, s in record["sets"].items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
