#!/usr/bin/env python3
"""G3: FLORES-200 fertility of IndicTrans2, IndicBERT v2 and Sarvam-1, next to BrahmicTokenizer-131K and C3.

Uses the G3 harness's own load_flores / run_flores (teams/03-tokenizer/harness/run_harness.py), so the method is the
same as every other row in COMPARE.md: tokens per whitespace word on FLORES-200 dev+devtest, no special tokens.

    python3 teams/03-tokenizer/harness/comparators.py --lab <era-v5-lab clone> --brahmic-dir <BrahmicTokenizer-131K> \
        --flores-dir <flores200_dataset> --c3 <tokenizer.json> --out-dir <folder>

Tokenizers (the Hugging Face commit actually used is recorded in the output):
  Sarvam-1         sarvamai/sarvam-1, the revision pinned in the harness REGISTRY
  IndicBERTv2      ai4bharat/IndicBERTv2-MLM-only (AutoTokenizer, add_special_tokens=False)
  IndicBERTv2-SS   ai4bharat/IndicBERTv2-SS, cross-check against the value already in COMPARE.md
  IndicTrans2      the source-side SentencePiece models of IndicTrans2: model.SRC of the indic-en model for the
                   Indic languages, model.SRC of the en-indic model for English. Raw text, as for every other
                   tokenizer (IndicTrans2's own pipeline adds language tags and an IndicNLP normalisation first;
                   both are left out so the row compares the vocabulary only).
A tokenizer that fails to load (gated repo, no login) is reported and skipped; the others still run.
"""
import argparse, importlib.util, json, sys, time
from pathlib import Path

IT2_REPOS = {"indic": ["ai4bharat/indictrans2-indic-en-1B", "ai4bharat/indictrans2-indic-en-dist-200M"],
             "en": ["ai4bharat/indictrans2-en-indic-1B", "ai4bharat/indictrans2-en-indic-dist-200M"]}


def hf_sha(repo, rev=None):
    try:
        from huggingface_hub import model_info
        return model_info(repo, revision=rev).sha
    except Exception:
        return rev or "unknown"


def hf_tok(repo, rev=None):
    from transformers import AutoTokenizer
    t = AutoTokenizer.from_pretrained(repo, revision=rev, trust_remote_code=False)
    return (lambda s: t.encode(s, add_special_tokens=False)), f"{repo}@{hf_sha(repo, rev)}"


def it2_spm():
    """IndicTrans2: one SentencePiece per side. Returns an encoder that picks by language label."""
    import sentencepiece as spm
    from huggingface_hub import hf_hub_download
    models, used = {}, []
    for side, repos in IT2_REPOS.items():
        err = None
        for repo in repos:
            try:
                path = hf_hub_download(repo, "model.SRC")
                models[side] = spm.SentencePieceProcessor(model_file=path)
                used.append(f"{repo}@{hf_sha(repo)} model.SRC")
                break
            except Exception as e:
                err = e
        if side not in models:
            raise RuntimeError(f"IndicTrans2 {side} model.SRC not available: {err}")
    return models, "; ".join(used)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lab", required=True); ap.add_argument("--brahmic-dir", required=True)
    ap.add_argument("--flores-dir", required=True); ap.add_argument("--c3", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("run_harness", Path(a.lab) / "teams/03-tokenizer/harness/run_harness.py")
    H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
    texts = H.load_flores(a.flores_dir)

    rows, sources = {}, {}
    def add(name, build):
        t0 = time.time()
        try:
            enc, src = build()
        except Exception as e:
            print(f"=== {name}: LOAD FAIL {type(e).__name__}: {str(e)[:200]}", flush=True)
            return
        rows[name], sources[name] = H.run_flores(enc, texts), src
        print(f"=== {name}: Indic mean={rows[name]['Mean']:.4f} En={rows[name]['En']:.4f} ({time.time()-t0:.1f}s)", flush=True)

    add(H.BASELINE, lambda: (H.make_encoder("local", str(Path(a.brahmic_dir) / "tokenizer.json"), None), "BrahmicTokenizer-131K tokenizer.json"))
    add("C3 sample-v0", lambda: (H.make_encoder("local", a.c3, None), a.c3))
    _, src, rev = H.REGISTRY["Sarvam-1"]
    add("Sarvam-1", lambda: hf_tok(src, rev))
    add("IndicBERTv2", lambda: hf_tok("ai4bharat/IndicBERTv2-MLM-only"))
    add("IndicBERTv2-SS", lambda: hf_tok("ai4bharat/IndicBERTv2-SS"))

    def build_it2():
        models, used = it2_spm()
        # run_flores calls enc(line) per language; wrap it so each language uses its side's model
        class Enc:
            lang = None
            def __call__(self, s):
                return models["en" if self.lang == "En" else "indic"].encode(s)
        return Enc(), used
    try:
        enc, used = build_it2()
        row = {}
        for lbl, lines in texts.items():          # the same formula as run_flores, one language at a time
            enc.lang = lbl
            tok = sum(len(enc(line)) for line in lines)
            words = sum(len(line.split()) for line in lines)
            row[lbl] = round(tok / max(words, 1), 4)
        have = [l for l in H.INDIC if l in row]
        row["Mean"] = round(sum(row[l] for l in have) / len(have), 4)
        rows["IndicTrans2"], sources["IndicTrans2"] = row, used
        print(f"=== IndicTrans2: Indic mean={row['Mean']:.4f} En={row['En']:.4f}", flush=True)
    except Exception as e:
        print(f"=== IndicTrans2: LOAD FAIL {type(e).__name__}: {str(e)[:200]}", flush=True)

    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "comparators_flores.json").write_text(json.dumps({"rows": rows, "sources": sources}, indent=2))
    cols = [lbl for _, lbl in H.LANGS] + ["Mean"]
    md = ["| Tokenizer | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for n, r in rows.items():
        md.append(f"| {n} | " + " | ".join(f"{r[c]:.4f}" for c in cols) + " |")
    (out / "comparators_flores.md").write_text("\n".join(md) + "\n")
    print("\n" + "\n".join(md))
    print("\nSources:"); [print(f"  {n}: {s}") for n, s in sources.items()]
    # cross-checks against values already in COMPARE.md
    ref = {"Sarvam-1": {"Ta": 2.1554, "Ml": 2.8345, "Mean": 2.3004}, "IndicBERTv2-SS": {"Hi": 1.2460, "Mr": 1.4678}}
    for n, vals in ref.items():
        if n in rows:
            d = max(abs(rows[n][k] - v) for k, v in vals.items())
            print(f"cross-check {n} vs COMPARE.md: max |d| = {d:.4f} -> {'OK' if d <= 0.001 else 'DIFFERENT'}")


if __name__ == "__main__":
    sys.exit(main())
