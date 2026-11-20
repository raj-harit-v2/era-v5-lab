#!/usr/bin/env python3
"""lang_id.py - the language of one document, for languages that share a script (Week-3 task 5).

D1 (script share, filters/medicine.md) cannot see a Hindi page in a Marathi pack: both are Devanagari. This module
gives each document two independent language signals and a verdict:

1. IndicLID's native-script model (IndicLID-FTN, a fastText classifier, AI4Bharat, MIT licence). Each paragraph is
   labelled on its own; the paragraphs then vote, weighted by their number of letters in the pack's script. The model's
   own scores are about 1.0 for almost every input, so they are not used as a confidence; the vote share is.
2. Marker words: frequent function words (and a few letters, such as ळ, ৰ and ৱ) that belong to one language of the
   script and not to the others.

Verdict for a document of pack language L:
  short         fewer than min_letters letters in the pack's script: not judged
  other_script  under half its letters are in the pack's script: that is D1's case, not this check's
  agree         IndicLID's vote says L (or, v2, IndicLID gives a label outside this check and the marker words say L)
  mislabelled   IndicLID's vote says another language M with a vote share of at least min_vote_share, AND the marker
                words say M too (both signals must agree, as agreed with the lead). v2: for a language IndicLID has no
                class for (marker_only_langs: Sanskrit in Bengali script), IndicLID must say "not L" with that vote
                share and the marker words name the language.
  uncertain     IndicLID says another language, but the vote is split or the marker words do not confirm it
  short_disagree  (v2) an 'uncertain' document under min_letters_to_flag letters: too short to trust IndicLID

found_lang is the language the check settles on (the pack's for agree, the other language for mislabelled).
v2 (17 Nov), after reviewing the v1 flags: repeated paragraphs count once; the loose Sanskrit word endings (ः, म्)
are no longer markers; labels outside the check's languages are no evidence on their own; short disagreements get
their own verdict; Sanskrit in Bengali script is found through a marker group with Assamese. See lang_label_check.md.

Text is read as NFC and never changed. Only labels, shares and counts leave this module, never text.
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The same ranges as D1 in filters/medicine.md, for the scripts this check covers.
SCRIPT_RANGES = {
    "Devanagari": ((0x0900, 0x097F), (0xA8E0, 0xA8FF), (0x1CD0, 0x1CFF)),
    "Bengali": ((0x0980, 0x09FF),),
}
WORD = re.compile(r"[^\s.,;:!?\"'()\[\]{}<>«»“”‘’|/\\\-–—।॥0-9०-९০-৯]+")
VERDICTS = ("short", "other_script", "agree", "mislabelled", "uncertain", "short_disagree")


def load_config(path=HERE / "lang_label_config.json"):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    cfg["_dir"] = str(Path(path).resolve().parent)
    return cfg


def cfg_path(cfg, key):
    """A path from the config, relative to the config file's folder."""
    p = Path(cfg[key])
    return p if p.is_absolute() else Path(cfg["_dir"]) / p


def in_script(ch, script):
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in SCRIPT_RANGES[script])


def letter_counts(text, script):
    """(letters of the pack's script, all letters). Letters and combining signs only, as D1 counts them."""
    own = total = 0
    for ch in text:
        if unicodedata.category(ch)[0] in "LM":
            total += 1
            own += in_script(ch, script)
    return own, total


def keep_script(text, script):
    """Only the pack's script, spaces and punctuation: other scripts are D1's business and would confuse the LID."""
    return "".join(ch if (in_script(ch, script) or not unicodedata.category(ch)[0] in "LM") else " " for ch in text)


def paragraphs(text, script, min_letters):
    """[(paragraph text, letters)] for the paragraphs with enough letters of the pack's script.

    A paragraph repeated in the document counts once (v2): repeated table or menu lines must not outvote the prose."""
    out, seen = [], set()
    for para in re.split(r"\n\s*\n|\n", text):
        para = " ".join(keep_script(para, script).split())
        n = letter_counts(para, script)[0]
        if n >= min_letters and para not in seen:
            seen.add(para)
            out.append((para, n))
    return out


def letter_signs(text, script, cfg):
    """Counts of the letters that tell languages of one script apart (config distinguishing_letters), as 'lang:n;...'.
    Evidence for readers only; the verdict does not use it."""
    counts = Counter()
    for ch, lang in cfg.get("distinguishing_letters", {}).get(script, {}).items():
        n = text.count(ch)
        if n:
            counts[f"{lang}({ch})"] += n
    return ";".join(f"{k}:{n}" for k, n in sorted(counts.items()))


def markers(text, langs, cfg):
    """Marker-word hits per language (only the languages of the pack's script are asked)."""
    hits = Counter()
    words = WORD.findall(text)
    for lang in langs:
        spec = cfg["markers"].get(lang, {})
        wordset = set(spec.get("words", []))
        suffixes = tuple(spec.get("suffixes", []))
        letters = spec.get("letters", [])
        for w in words:
            if w in wordset or (suffixes and w.endswith(suffixes) and len(w) > max(map(len, suffixes)))\
                    or any(c in w for c in letters):
                hits[lang] += 1
    return hits


def group_of(lang, cfg):
    """The marker group of a language (itself when it is in none). A group holds languages that share marker letters,
    such as Assamese and Sanskrit in Bengali script (both write ৰ), so their hits must not cancel each other."""
    for g in cfg.get("marker_groups", []):
        if lang in g:
            return tuple(g)
    return (lang,)


def marker_vote(hits, cfg):
    """The language the marker words point to, or 'unknown' when they are too few or too close.

    Groups are compared first (min hits and ratio against the next group); the group's strongest language is named."""
    if not hits:
        return "unknown"
    groups = Counter()
    for lang, n in hits.items():
        groups[group_of(lang, cfg)] += n
    (best, n1), *rest = groups.most_common()
    n2 = rest[0][1] if rest else 0
    if n1 >= cfg["marker_min_hits"] and n1 >= cfg["marker_min_ratio"] * n2:
        return max(best, key=lambda lg: hits.get(lg, 0))
    return "unknown"


class FastTextLID:
    """IndicLID-FTN. fastText is imported only here, so the tests and the report need no model."""

    def __init__(self, model_path):
        import fasttext  # noqa: PLC0415
        fasttext.FastText.eprint = lambda *a, **k: None  # silence the load warning
        self.model = fasttext.load_model(str(model_path))

    def __call__(self, texts):
        labels, _ = self.model.predict([t.replace("\n", " ") for t in texts], k=1)
        return [lab[0].replace("__label__", "") if lab else "other" for lab in labels]


def lid_vote(paras, predict, cfg):
    """(language, raw IndicLID label, vote share) from the letter-weighted vote of the paragraphs."""
    labels = predict([p for p, _ in paras])
    votes, raw = Counter(), Counter()
    for (_, n), lab in zip(paras, labels):
        lang = cfg["lid_label_to_lang"].get(lab, "other:" + lab)
        votes[lang] += n
        raw[lab] += n
    lang, w = votes.most_common(1)[0]
    top_raw = max((lab for lab in raw if cfg["lid_label_to_lang"].get(lab, "other:" + lab) == lang), key=raw.get)
    return lang, top_raw, w / sum(votes.values())


def judge(text, pack_lang, predict, cfg):
    """The verdict and both signals for one document. No text in the result."""
    script = cfg["lang_script"][pack_lang]
    text = unicodedata.normalize("NFC", text or "")
    own, total = letter_counts(text, script)
    res = {"script_share": round(own / total, 4) if total else 0.0, "letters": own,
           "lid_lang": "", "lid_label": "", "vote_share": "", "marker_lang": "", "verdict": "", "found_lang": "",
           "sign_letters": letter_signs(text, script, cfg)}
    if own < cfg["min_letters"]:
        res["verdict"] = "short"
        return res
    if own / total < 0.5:
        res["verdict"] = "other_script"
        return res
    paras = paragraphs(text, script, cfg["min_paragraph_letters"])
    if not paras:  # only short paragraphs: judge the whole document as one
        whole = " ".join(keep_script(text, script).split())
        paras = [(whole, own)]
    lang, label, share = lid_vote(paras, predict, cfg)
    same_script = [lg for lg, sc in cfg["lang_script"].items() if sc == script]
    mlang = marker_vote(markers(" ".join(p for p, _ in paras), same_script, cfg), cfg)
    res.update(lid_lang=lang, lid_label=label, vote_share=round(share, 4), marker_lang=mlang)
    if lang == pack_lang:
        res.update(verdict="agree", found_lang=pack_lang)
    elif lang.startswith("other:"):
        # v2: a label outside this check's languages (Bodo, Kashmiri, Dogri ...) is no evidence on its own. IndicLID
        # gives them to plain Hindi news lines. The marker words decide between agree and uncertain.
        res.update(verdict="agree", found_lang=pack_lang) if mlang == pack_lang else \
            res.update(verdict="uncertain", found_lang=lang if mlang == "unknown" else mlang)
    elif share >= cfg["min_vote_share"] and mlang != "unknown" and group_of(mlang, cfg) == group_of(lang, cfg):
        # Both signals name the same other language. v2: or the same marker group, so Sanskrit in Bengali script
        # (no IndicLID class: it says Assamese) is flagged, and the marker words name it.
        res.update(verdict="mislabelled", found_lang=mlang)
    else:
        res.update(verdict="uncertain", found_lang=lang)
    if res["verdict"] == "uncertain" and own < cfg.get("min_letters_to_flag", 0):
        res["verdict"] = "short_disagree"  # v2: too short for IndicLID to be trusted when it disagrees
    return res
