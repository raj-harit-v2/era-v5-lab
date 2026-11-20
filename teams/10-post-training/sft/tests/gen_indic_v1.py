"""Write `indic_v1.jsonl`: held-out Indic prompts for the SFT evaluation (eval_v1.md).

Run: python gen_indic_v1.py   (writes the file next to this script, deterministic)

Ten Brahmic scripts: hi, mr (Devanagari), ta, te, kn, bn, gu, ml, or, pa. Each row is one prompt in chat format v0
(`messages` ends at the user turn) and an `expect` that one scorer in scorers.py reads:
  kind "answer": a short question with a fixed answer. `accept` lists the accepted spellings and numbers (digits of
                 any script count as the same digit). The reply must hold one of them and be at most `max_chars` long.
  kind "script": a writing request. The reply must be written in the target script (`script_share` of its letters,
                 at least `min_letters` letters).
  kind "copy":   repeat a text exactly. The reply must hold the text unchanged, ZWJ and ZWNJ included.
Items are evaluation-only and are never trained on. Native-speaker review is recorded on every row in
`review`: hi, mr, te and kn are reviewed; the other six scripts are not yet, and must be before their numbers are quoted.
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE = (
    "original: written by Claude (AI assistant) for Ravi Naik (RaviNaik), 2026-11-15; not from any benchmark; "
    "evaluation-only (TSAI data rule, 3 Nov)"
)
REVIEWED = {"hi", "mr", "te", "kn", "ta", "bn", "gu", "ml", "or", "pa"}  # languages a native speaker has checked
REVIEW_YES = "wording reviewed by a native speaker"
REVIEW_NO = "wording not reviewed by a native speaker"
SYSTEM = "You are a helpful assistant. Answer briefly."
ZWJ, ZWNJ = "‍", "‌"

SCRIPT_OF = {
    "hi": "DEVANAGARI", "mr": "DEVANAGARI", "ta": "TAMIL", "te": "TELUGU", "kn": "KANNADA",
    "bn": "BENGALI", "gu": "GUJARATI", "ml": "MALAYALAM", "or": "ORIYA", "pa": "GURMUKHI",
}


def row(rid, kind, lang, user, expect):
    return {
        "id": rid, "kind": kind, "lang": lang, "source": SOURCE, "review": REVIEW_YES if lang in REVIEWED else REVIEW_NO,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
        "expect": {"kind": kind, **expect},
    }


def answer(rid, lang, user, *accept, max_chars=300):
    return row(rid, "answer", lang, user, {"accept": list(accept), "max_chars": max_chars})


def script(rid, lang, user):
    return row(rid, "script", lang, user, {"script": SCRIPT_OF[lang], "script_share": 0.8, "min_letters": 20})


def copy(rid, lang, text):
    return row(rid, "copy", lang, f"Repeat this text exactly, with no change: {text}", {"text": text})


ROWS = [
    # --- short questions with one answer (2 per script) ---
    answer("in-ans-hi-1", "hi", "एक सप्ताह में कितने दिन होते हैं?", "7", "सात"),
    answer("in-ans-hi-2", "hi", "५ + ७ कितना होता है?", "12", "बारह"),
    answer("in-ans-mr-1", "mr", "महाराष्ट्राची राजधानी कोणती?", "मुंबई", "मुम्बई"),
    answer("in-ans-mr-2", "mr", "एका वर्षात किती महिने असतात?", "12", "बारा"),
    answer("in-ans-ta-1", "ta", "தமிழ்நாட்டின் தலைநகரம் எது?", "சென்னை"),
    answer("in-ans-ta-2", "ta", "ஒரு மணி நேரத்தில் எத்தனை நிமிடங்கள் உள்ளன?", "60", "அறுபது"),
    answer("in-ans-te-1", "te", "తెలంగాణ రాజధాని ఏది?", "హైదరాబాద్", "హైదరాబాదు"),
    answer("in-ans-te-2", "te", "ఒక వారంలో ఎన్ని రోజులు ఉంటాయి?", "7", "ఏడు"),
    answer("in-ans-kn-1", "kn", "ಕರ್ನಾಟಕದ ರಾಜಧಾನಿ ಯಾವುದು?", "ಬೆಂಗಳೂರು"),
    answer("in-ans-kn-2", "kn", "ಒಂದು ವರ್ಷದಲ್ಲಿ ಎಷ್ಟು ತಿಂಗಳುಗಳಿವೆ?", "12", "ಹನ್ನೆರಡು"),
    answer("in-ans-bn-1", "bn", "পশ্চিমবঙ্গের রাজধানী কী?", "কলকাতা", "কোলকাতা"),
    answer("in-ans-bn-2", "bn", "একটি ত্রিভুজের কয়টি বাহু থাকে?", "3", "তিন"),
    answer("in-ans-gu-1", "gu", "ગુજરાતની રાજધાની કઈ છે?", "ગાંધીનગર"),
    answer("in-ans-gu-2", "gu", "એક દિવસમાં કેટલા કલાક હોય છે?", "24", "ચોવીસ"),
    answer("in-ans-ml-1", "ml", "കേരളത്തിന്റെ തലസ്ഥാനം ഏതാണ്?", "തിരുവനന്തപുരം"),
    answer("in-ans-ml-2", "ml", "ഒരു ദിവസത്തിൽ എത്ര മണിക്കൂർ ഉണ്ട്?", "24", "ഇരുപത്തിനാൽ", "ഇരുപത്തിനാല്"),
    answer("in-ans-or-1", "or", "ଓଡ଼ିଶାର ରାଜଧାନୀ କେଉଁଟି?", "ଭୁବନେଶ୍ୱର", "ଭୁବନେଶ୍ବର"),
    answer("in-ans-or-2", "or", "ଏକ ସପ୍ତାହରେ କେତେ ଦିନ ଥାଏ?", "7", "ସାତ"),
    answer("in-ans-pa-1", "pa", "ਪੰਜਾਬ ਦੀ ਰਾਜਧਾਨੀ ਕਿਹੜੀ ਹੈ?", "ਚੰਡੀਗੜ੍ਹ"),
    answer("in-ans-pa-2", "pa", "ਇੱਕ ਹਫ਼ਤੇ ਵਿੱਚ ਕਿੰਨੇ ਦਿਨ ਹੁੰਦੇ ਹਨ?", "7", "ਸੱਤ"),
    # --- sums written with the digits of the script ---
    answer("in-num-bn", "bn", "৫ + ৩ কত?", "8", "আট"),
    answer("in-num-ta", "ta", "௩ + ௪ எவ்வளவு?", "7", "ஏழு"),
    answer("in-num-gu", "gu", "૬ + ૩ કેટલા થાય?", "9", "નવ"),
    answer("in-num-pa", "pa", "੪ + ੪ ਕਿੰਨੇ ਹੁੰਦੇ ਹਨ?", "8", "ਅੱਠ"),
    # --- the reply must be in the script ---
    script("in-scr-hi", "hi", "बारिश के मौसम के बारे में दो वाक्य लिखिए।"),
    script("in-scr-mr", "mr", "पावसाळ्याबद्दल दोन वाक्ये लिहा."),
    script("in-scr-ta", "ta", "மழைக்காலத்தைப் பற்றி இரண்டு வாக்கியங்கள் எழுதுங்கள்."),
    script("in-scr-te", "te", "వర్షాకాలం గురించి రెండు వాక్యాలు రాయండి."),
    script("in-scr-kn", "kn", "ಮಳೆಗಾಲದ ಬಗ್ಗೆ ಎರಡು ವಾಕ್ಯಗಳನ್ನು ಬರೆಯಿರಿ."),
    script("in-scr-bn", "bn", "বর্ষাকাল সম্পর্কে দুটি বাক্য লেখো।"),
    script("in-scr-gu", "gu", "ચોમાસા વિશે બે વાક્યો લખો."),
    script("in-scr-ml", "ml", "മഴക്കാലത്തെക്കുറിച്ച് രണ്ട് വാക്യങ്ങൾ എഴുതുക."),
    script("in-scr-or", "or", "ବର୍ଷା ଋତୁ ବିଷୟରେ ଦୁଇଟି ବାକ୍ୟ ଲେଖ"),
    script("in-scr-pa", "pa", "ਬਰਸਾਤ ਦੇ ਮੌਸਮ ਬਾਰੇ ਦੋ ਵਾਕ ਲਿਖੋ।"),
    script("in-scr-en-hi", "hi", "Write two sentences about the sea in Hindi, in the Devanagari script."),
    script("in-scr-en-ta", "ta", "Write two sentences about the sea in Tamil, in the Tamil script."),
    script("in-scr-en-te", "te", "Write two sentences about the sea in Telugu, in the Telugu script."),
    script("in-scr-en-bn", "bn", "Write two sentences about the sea in Bengali, in the Bengali script."),
    # --- the reply must keep ZWJ, ZWNJ and conjuncts unchanged ---
    copy("in-cpy-hi-zwj", "hi", f"क्{ZWJ}षमा"),
    copy("in-cpy-hi-zwnj", "hi", f"क्{ZWNJ}षमा"),
    copy("in-cpy-bn-zwj", "bn", f"র{ZWJ}্যাব"),
    copy("in-cpy-ml-zwj", "ml", f"അവന്{ZWJ}"),
    copy("in-cpy-ta", "ta", "க்ஷேத்ரம்"),
    copy("in-cpy-te", "te", "శ్రీరామ నవమి"),
]


def main() -> None:
    out = Path(__file__).with_name("indic_v1.jsonl")
    ids = [r["id"] for r in ROWS]
    assert len(ids) == len(set(ids))
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for r in ROWS:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(ROWS)} rows to {out}")


if __name__ == "__main__":
    main()
