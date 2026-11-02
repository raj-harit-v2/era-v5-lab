"""Evidence for every current code medicine on every code pack. Read-only: runs rules, writes evidence.json.

Inputs (a scratch checkout of g1-harm-test, passed as argv[1]):
  gold/      official gold CSVs of the branch
  rules/     rules files written by medicine_extract.py from the latest open-PR medicine.md files
  medicines/submissions/  the sheets, for the medicines the extractor cannot take
  diagnosis/submissions/  the latest labels.csv of every annotator

  python -I compile_evidence.py <checkout> <packs dir>   -> ../results/sheets/evidence.json
"""
import csv, inspect, json, os, re, sys, textwrap, time
from collections import defaultdict
from pathlib import Path
import pyarrow.parquet as pq

WT, PACKS = Path(sys.argv[1]), Path(sys.argv[2])
TEAM = WT / "teams" / "01-data-a"
PACK_IDS = ["code-go", "code-rust", "code-js-ts", "code-java", "code-cpp", "code-python"]
HERE = Path(__file__).resolve().parent
CODE = re.compile(r"[A-H][1-9]")


def takes_doc(fn):
    try: return list(inspect.signature(fn).parameters)[0] == "doc"
    except (TypeError, ValueError, IndexError): return False


def classify(text, out):
    """keep / fix / drop. True and None mean drop, as their authors wrote them."""
    if out is None or out is True: return "drop"
    if out is False: return "keep"
    if isinstance(out, str): return "fix" if out != text else "keep"
    if isinstance(out, tuple) and len(out) == 2:
        if out[0] == "drop": return "drop"
        return "fix" if out[1] != text else "keep"
    raise TypeError(type(out).__name__)


def md_blocks(path):
    return [textwrap.dedent(b) for b in re.findall(r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S)]


E4_FIX_WRAPPER = r'''

# Changes to amukka's rule. The code above is theirs except that the comment regex is now an argument.
NO_HASH = re.compile(r"^\s*(//(?![!/])|/\*(?![!*])|\*|\*/)")  # "#" starts real code in C++ and Rust: #include, #[derive]
KEEP_LINE = re.compile(r"^(#!|#.*coding[:=]|\s*//\s*(go:|\+build))")  # read by the interpreter or the build, not licence text


def medicine_e4_fixed(doc):
    text = doc["text"]
    comment = COMMENT_LINE if doc.get("lang_label") == "python" else NO_HASH
    new = text
    while True:  # two stacked licence blocks: apply(apply(doc)) == apply(doc)
        action, out = e4_licence_header(new, comment)
        if action != "fix" or out == new:
            break
        new = out
    if new == text:
        return ("keep", text)
    now = set(new.split("\n"))
    kept = [l for l in text.split("\n")[:60] if KEEP_LINE.match(l) and l not in now]
    return ("fix", "\n".join(kept + [new]) if kept else new)
'''


def amukka_source():
    ns, kept = {"re": re}, []
    for b in md_blocks(TEAM / "medicines" / "submissions" / "code-rust" / "amukka" / "medicine.md"):
        try: exec(b, ns); kept.append(b)
        except Exception: pass  # block 1 is a fragment that needs a variable from elsewhere
    return "\n\n".join(kept)


def e4_fixed_source():
    """amukka's e4_licence_header with the comment regex as an argument, plus the wrapper above."""
    src = amukka_source()
    a = "def e4_licence_header(text: str):"
    assert src.count(a) == 1 and src.count("COMMENT_LINE.match(lines[i") == 2
    head, tail = src.split(a)
    end = tail.index("\ndef ", 1)
    fn = tail[:end].replace("COMMENT_LINE.match(lines[i", "comment_line.match(lines[i")
    return head + "def e4_licence_header(text: str, comment_line=COMMENT_LINE):" + fn + tail[end:] + E4_FIX_WRAPPER


def load_candidates():
    """[{id, handle, pack, code, fn, how}]: every medicine that can run on one document with no extra input."""
    reg = {e["id"]: e for e in json.loads((TEAM / "rules" / "registry.json").read_text(encoding="utf-8"))["rules"]}
    out = []
    for pack in sorted(p.name for p in (TEAM / "rules").iterdir() if p.is_dir() and p.name.startswith("code-")):
        for f in sorted((TEAM / "rules" / pack).glob("*.py")):
            ns = {"__name__": "rules"}
            exec(compile(f.read_text(encoding="utf-8"), f.name, "exec"), ns)
            for rid, fn in (ns.get("RULES_BY_ID") or {}).items():
                if reg.get(rid, {}).get("withdrawn"): continue
                out.append(dict(id=rid, handle=f.stem, pack=pack, code=rid.split("-")[1], fn=fn, how="extractor"))
            if f.stem == "RaviNaik":  # their E4 section holds 3 functions, so the extractor takes none; the two rules are clear
                out.append(dict(id="RaviNaik:E4", handle=f.stem, pack=pack, code="E4", fn=ns["strip_licence_header"], how="by hand: E4 section has 3 functions"))
                out.append(dict(id="RaviNaik:B4", handle=f.stem, pack=pack, code="B4", fn=ns["fix_placeholders"], how="by hand: B4 function sits in their E4 section"))
            if f.stem == "vaibh27":
                out.append(dict(id="vaibh27:C4", handle=f.stem, pack=pack, code="C4", fn=ns["m9_drop_joined"], how="by hand: C4 section has 3 functions"))
    subs = TEAM / "medicines" / "submissions"
    # amukka: a RULES dict in a block, which the extractor no longer reads; IDs are already in the registry
    ns = {"__name__": "rules", "re": re}
    for b in md_blocks(subs / "code-rust" / "amukka" / "medicine.md"):
        try: exec(b, ns)
        except Exception: pass  # block 1 is a fragment that needs a variable from elsewhere
    ids = {e["code"]: rid for rid, e in reg.items() if e["handle"] == "amukka" and e["pack"] == "code-rust"}
    for code, fn in ns["RULES"].items():
        out.append(dict(id=ids[code], handle="amukka", pack="code-rust", code=code, fn=fn, how="by hand: RULES dict, not read by the extractor"))
    ns = {"__name__": "rules", "re": re}
    exec(e4_fixed_source(), ns)
    out.append(dict(id="amukka:E4fix", handle="amukka", pack="code-rust", code="E4", fn=ns["medicine_e4_fixed"], how="changed: DA-E4-004 with 3 bugs fixed"))
    # new rule for E3: placeholder instead of the secret, written for this sheet
    ns = {"__name__": "rules"}
    exec((HERE / "e3_rule.py").read_text(encoding="utf-8"), ns)
    out.append(dict(id="new:E3", handle="TEJASKUMAR-REDDY-J", pack="code-go", code="E3", fn=ns["medicine_e3"], how="new rule, written for this sheet"))
    # AjaySnl and udisinghania: no **Disease:** lines
    ns = {"__name__": "rules", "re": re}
    exec(md_blocks(subs / "code-js-ts" / "AjaySnl" / "medicine.md")[0], ns)
    out.append(dict(id="AjaySnl:B3", handle="AjaySnl", pack="code-js-ts", code="B3", fn=ns["fix_b3"], how="by hand: no **Disease:** lines"))
    ns = {"__name__": "rules", "re": re}
    exec(md_blocks(subs / "code-go" / "udisinghania" / "medicine.md")[1], ns)
    out.append(dict(id="udisinghania:B3", handle="udisinghania", pack="code-go", code="B3", fn=ns["fix_b3"], how="by hand: no **Disease:** lines"))
    return out


def load_data():
    data = {}
    for pack in PACK_IDS:
        rows = pq.read_table(PACKS / f"{pack}.parquet", columns=["doc_id", "lang_label", "url", "text"]).to_pylist()
        ids = {r["doc_id"] for r in rows}
        gold = {r["doc_id"] for r in csv.DictReader(open(TEAM / "gold" / f"{pack}_gold.csv", encoding="utf-8"))}
        assert gold <= ids, pack
        sick, clean, sheets = defaultdict(set), set(), {}
        for p in sorted((WT / "diagnosis" / "submissions" / pack).glob("*/labels.csv")):
            raw = p.read_bytes()
            try: txt = raw.decode("utf-8-sig")
            except UnicodeDecodeError: txt = raw.decode("cp1252", "replace")
            n = 0
            for r in csv.DictReader(txt.splitlines()):
                d = (r.get("doc_id") or "").strip()
                if d not in ids: continue
                n += 1
                verdict = (r.get("verdict") or "").strip()
                if verdict == "clean": clean.add(d)
                if verdict in ("fix", "drop"):
                    for c in CODE.findall(r.get("diseases") or ""): sick[c].add(d)
            sheets[p.parent.name] = n
        data[pack] = dict(rows=rows, gold=gold, sick=sick, clean=clean, sheets=sheets)
    return data


def main():
    cands, data = load_candidates(), load_data()
    ev = dict(packs={p: dict(n=len(d["rows"]), gold=len(d["gold"]), sheets=d["sheets"], sick={c: sorted(v) for c, v in d["sick"].items()},
                             clean=sorted(d["clean"]), gold_ids=sorted(d["gold"])) for p, d in data.items()}, rules={})
    for c in cands:
        t0 = time.time(); per = {}
        by_doc = takes_doc(c["fn"])
        for pack, d in data.items():
            drop, fix, err = [], [], []
            for r in d["rows"]:
                try: v = classify(r["text"], c["fn"](dict(r) if by_doc else r["text"]))
                except Exception as e: err.append((r["doc_id"], type(e).__name__)); continue
                if v == "drop": drop.append(r["doc_id"])
                elif v == "fix": fix.append(r["doc_id"])
            per[pack] = dict(drop=drop, fix=fix, err=err)
        ev["rules"][c["id"]] = dict(handle=c["handle"], pack=c["pack"], code=c["code"], how=c["how"], per=per)
        print(f"{c['id']:18} {c['handle']:20} {time.time() - t0:6.1f}s", file=sys.stderr, flush=True)
    (HERE.parent / "results" / "sheets" / "evidence.json").write_text(json.dumps(ev), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
