"""SFT/RL evaluation firewall for the OCR-2 pack (G10, 16 Nov 2026): drop evaluation problems from SFT training.

Lead's ruling (G10 group, 16 Nov): problems used to evaluate RL or effort (the RL held-out set and the code prompts of
the effort suite) stay out of SFT training; the SFT held-out split stays out of the RL training pool; the two training
pools may overlap. This file applies the first half to a finished OCR-2 pack, as a step after `run_ocr2.py`:

    python sft/eval_firewall.py apply --pack out/run/shards/shard-NNNNN/pack/pack.jsonl \
        --sidecar out/run/shards/shard-NNNNN/join/joined.sidecar.jsonl \
        --families eval_firewall_families_v1.txt --families-sha256 <pinned> \
        --out <store>/shard-NNNNN/pack.firewalled.jsonl --report <store>/shard-NNNNN/firewall_report.json

    python sft/eval_firewall.py predict --rowstats <per-row stats>.jsonl.gz ... --families <list> --families-sha256 <pinned> \
        --out <prediction.json>

`apply` keeps every training row whose problem family key (sidecar `problem_family_key`, the sha256 of the
whitespace-normalised statement that the held-out split also uses) is not in the list, in the pack's own order and with
its bytes unchanged, so the firewalled pack is a byte-for-byte subsequence of the verified pack. The held-out file is not
touched (an evaluation problem in the SFT held-out split stays an evaluation problem). The report has counts, tokens and
sha256 only. `predict` gives the same counts per shard from per-row stats (fields `family`, `status`, `tokens`,
`targets`), so the result of `apply` can be predicted for shards whose pack bytes are not on hand.

Why a separate step: `run_ocr2.py` hashes its code and policy into the run id, and its per-shard pack sha256 values are
already verified for all 70 shards. Filtering after the pack stage leaves those records valid and adds one checkable
step. The family list is private (it names evaluation problems); its sha256 and size go into the public record and a
mismatched list is refused.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path

SCHEMA = "g10-ocr2-eval-firewall/1"
ID_RE = re.compile(r'^\{"id": "([^"]+)"')


class FirewallError(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def load_families(path: Path, expect_sha256: str | None) -> frozenset[str]:
    """One `sha256:<hex>` family key per line, sorted, no duplicates. Refused if its sha256 is not the pinned one."""
    got = sha256_file(path)
    if expect_sha256 is not None and got != expect_sha256:
        raise FirewallError(f"{path.name} has sha256 {got}, not the pinned {expect_sha256}")
    keys = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if keys != sorted(set(keys)) or not all(re.fullmatch(r"sha256:[0-9a-f]{64}", k) for k in keys):
        raise FirewallError(f"{path.name}: keys must be sorted, unique `sha256:<64 hex>` lines")
    return frozenset(keys)


def write_families(keys, path: Path) -> str:
    path.write_text("".join(f"{k}\n" for k in sorted(set(keys))), encoding="utf-8")
    return sha256_file(path)


def apply(pack: Path, sidecar: Path, families: frozenset[str], out: Path) -> dict:
    fam = {}
    with open(sidecar, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            fam[e["rendered_id"]] = e["problem_family_key"]
    kept = removed = tok_kept = tok_removed = tgt_kept = tgt_removed = 0
    removed_families: set[str] = set()
    h_in, h_out = hashlib.sha256(), hashlib.sha256()
    tmp = out.with_name(out.name + ".tmp")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(pack, "rb") as src, open(tmp, "wb") as dst:
        for raw in src:
            h_in.update(raw)
            line = raw.decode("utf-8")
            m = ID_RE.match(line)
            row = json.loads(line)
            rid = m.group(1) if m else row["id"]
            if rid not in fam:
                raise FirewallError(f"pack row {rid} is not in the sidecar")
            n, t = len(row["input_ids"]), sum(row["loss_mask"][1:])
            if fam[rid] in families:
                removed, tok_removed, tgt_removed = removed + 1, tok_removed + n, tgt_removed + t
                removed_families.add(fam[rid])
            else:
                kept, tok_kept, tgt_kept = kept + 1, tok_kept + n, tgt_kept + t
                dst.write(raw)
                h_out.update(raw)
        dst.flush()
        os.fsync(dst.fileno())
    os.replace(tmp, out)
    return {"schema": SCHEMA, "pack_sha256_in": h_in.hexdigest(), "rows_in": kept + removed,
            "rows_removed": removed, "rows_kept": kept, "tokens_removed": tok_removed, "tokens_kept": tok_kept,
            "shifted_targets_removed": tgt_removed, "shifted_targets_kept": tgt_kept,
            "families_removed": len(removed_families), "firewalled_pack_sha256": h_out.hexdigest(),
            "firewalled_pack_bytes": out.stat().st_size}


def predict(rowstats: list[Path], families: frozenset[str]) -> dict:
    per: dict[str, Counter] = {}
    fam_by: dict[str, set] = {}
    for path in sorted(rowstats):
        shard = re.search(r"shard-(\d+)", path.name)
        key = str(int(shard.group(1))) if shard else path.name
        c = per.setdefault(key, Counter())
        fs = fam_by.setdefault(key, set())
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                hit = r["family"] in families
                if r["status"] == "pack":
                    side = "removed" if hit else "kept"
                    c[f"rows_{side}"] += 1
                    c[f"tokens_{side}"] += r["tokens"]
                    c[f"shifted_targets_{side}"] += r["targets"]
                    if hit:
                        fs.add(r["family"])
                elif r["status"] == "heldout" and hit:
                    c["heldout_rows_in_list"] += 1
    shards = {k: {**{f: per[k].get(f, 0) for f in ("rows_kept", "rows_removed", "tokens_kept", "tokens_removed",
                                                    "shifted_targets_kept", "shifted_targets_removed", "heldout_rows_in_list")},
                  "families_removed": len(fam_by[k])}
              for k in sorted(per, key=lambda x: int(x) if x.isdigit() else x)}
    tot = Counter()
    for v in shards.values():
        tot.update({k: v[k] for k in v if k != "families_removed"})
    all_fams = set().union(*fam_by.values()) if fam_by else set()
    return {"schema": SCHEMA, "shards": shards, "totals": dict(tot), "families_removed": len(all_fams),
            "list_families_not_in_pack": len(families - all_fams)}


def record(prediction: dict, applied: dict[str, dict], variants: dict[str, dict], sets: dict, ruling: str,
           unfirewalled_manifest: dict, unfirewalled_name: str) -> dict:
    """The public record: rule, list hashes, per-shard prediction, actual results on the shards applied locally."""
    shards = prediction["shards"]
    checks = {}
    keys = ("rows_kept", "rows_removed", "tokens_kept", "tokens_removed", "shifted_targets_kept",
            "shifted_targets_removed", "families_removed")
    actual = {}
    for sid, rep in sorted(applied.items(), key=lambda kv: int(kv[0])):
        pred = shards[sid]
        man = unfirewalled_manifest["shards"][int(sid)]
        actual[sid] = {"pack_sha256_in": rep["pack_sha256_in"], "firewalled_pack_sha256": rep["firewalled_pack_sha256"],
                       "firewalled_pack_bytes": rep["firewalled_pack_bytes"], **{k: rep[k] for k in keys}}
        checks[f"shard{sid}.input_is_the_verified_pack"] = rep["pack_sha256_in"] == man["pack_sha256"]
        checks[f"shard{sid}.predicted_equals_actual"] = all(rep[k] == pred[k] for k in keys)
    f = unfirewalled_manifest["funnel"]
    t = prediction["totals"]
    checks["totals.rows_reconcile_with_the_pack_manifest"] = t["rows_kept"] + t["rows_removed"] == f["pack.train_rows"]
    checks["totals.tokens_reconcile_with_the_pack_manifest"] = t["tokens_kept"] + t["tokens_removed"] == f["train.tokens"]
    checks["totals.targets_reconcile_with_the_pack_manifest"] = (t["shifted_targets_kept"] + t["shifted_targets_removed"]
                                                                  == f["train.shifted_assistant_targets"])
    checks["heldout_split_untouched"] = t.get("heldout_rows_in_list", 0) == 0
    checks["every_shard_predicted"] = sorted(map(int, shards)) == list(range(len(unfirewalled_manifest["shards"])))
    return {
        "schema": SCHEMA, "set": "sft-code-opencodereasoning-2", "ruling": ruling,
        "rule": "drop every training row whose problem family key is in the list; the held-out file and every other row "
                "are unchanged; the firewalled pack is an ordered byte subsequence of the verified pack",
        "applied_after": {"manifest": unfirewalled_name, "run_id": unfirewalled_manifest["build"]["run_id"],
                          "note": "the per-shard pack sha256 values of that manifest stay the verified input of this step"},
        "families": {"sha256": prediction["families_sha256"], "count": prediction["families_in_list"],
                     "list": "private (names evaluation problems); sent to TSAI with the job request",
                     "in_pack": prediction["families_removed"], "not_in_pack": prediction["list_families_not_in_pack"]},
        "sets": sets, "variants": variants,
        "totals": {"before": {"rows": f["pack.train_rows"], "tokens": f["train.tokens"],
                              "shifted_targets": f["train.shifted_assistant_targets"]},
                   "removed": {"rows": t["rows_removed"], "tokens": t["tokens_removed"], "shifted_targets": t["shifted_targets_removed"]},
                   "after": {"rows": t["rows_kept"], "tokens": t["tokens_kept"], "shifted_targets": t["shifted_targets_kept"]},
                   "token_share_removed": round(t["tokens_removed"] / f["train.tokens"], 6),
                   "heldout_rows_in_list": t.get("heldout_rows_in_list", 0)},
        "predicted_by_shard": shards, "applied_locally": actual, "checks": checks,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("apply")
    a1.add_argument("--pack", type=Path, required=True)
    a1.add_argument("--sidecar", type=Path, required=True)
    a1.add_argument("--families", type=Path, required=True)
    a1.add_argument("--families-sha256", required=True)
    a1.add_argument("--out", type=Path, required=True)
    a1.add_argument("--report", type=Path, required=True)
    a2 = sub.add_parser("predict")
    a2.add_argument("--rowstats", type=Path, nargs="+", required=True)
    a2.add_argument("--families", type=Path, required=True)
    a2.add_argument("--families-sha256", required=True)
    a2.add_argument("--out", type=Path, required=True)
    a3 = sub.add_parser("record", help="assemble the public record from a prediction and local apply reports")
    a3.add_argument("--prediction", type=Path, required=True)
    a3.add_argument("--apply-report", action="append", default=[], help="SHARD=report.json (repeatable)")
    a3.add_argument("--variant", action="append", default=[], help="NAME=prediction.json (other lists, for sizing)")
    a3.add_argument("--sets", type=Path, required=True, help="public JSON: per evaluation set, counts only")
    a3.add_argument("--ruling", required=True)
    a3.add_argument("--manifest", type=Path, required=True, help="the verified (unfirewalled) pack manifest")
    a3.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "record":
        pred = json.loads(a.prediction.read_text(encoding="utf-8"))
        applied = {kv.split("=", 1)[0]: json.loads(Path(kv.split("=", 1)[1]).read_text(encoding="utf-8")) for kv in a.apply_report}
        variants = {}
        for kv in a.variant:
            name, path = kv.split("=", 1)
            v = json.loads(Path(path).read_text(encoding="utf-8"))
            variants[name] = {"families_sha256": v["families_sha256"], "families": v["families_in_list"],
                              "families_in_pack": v["families_removed"], **{f"removed_{k}": v["totals"][k] for k in
                                                                              ("rows_removed", "tokens_removed")}}
        rec = record(pred, applied, variants, json.loads(a.sets.read_text(encoding="utf-8")), a.ruling,
                     json.loads(a.manifest.read_text(encoding="utf-8")), a.manifest.name)
        a.out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        bad = [k for k, v in rec["checks"].items() if not v]
        print(json.dumps({"checks": len(rec["checks"]), "failed": bad, **rec["totals"]["removed"]}))
        return 1 if bad else 0
    try:
        fams = load_families(a.families, a.families_sha256)
        if a.cmd == "apply":
            rep = apply(a.pack, a.sidecar, fams, a.out)
            rep.update(families_sha256=a.families_sha256, families_in_list=len(fams))
            a.report.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps({k: rep[k] for k in ("rows_in", "rows_removed", "rows_kept", "tokens_removed", "firewalled_pack_sha256")}))
        else:
            rep = predict(a.rowstats, fams)
            rep.update(families_sha256=a.families_sha256, families_in_list=len(fams))
            a.out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps({"shards": len(rep["shards"]), **rep["totals"], "families_removed": rep["families_removed"]}))
    except FirewallError as exc:
        print(f"eval_firewall: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
