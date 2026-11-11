#!/usr/bin/env python3
"""detector.py - does a document contain romanised Indic (D2: an Indian language written in Latin letters)?

The rule, in a few lines:
  1. Take the words written in Latin letters, after removing URLs, emails, @handles and #hashtags. Words in capitals
     only (ANI, AAP, EMI) are acronyms more often than not, so they are skipped too.
  2. Count the ones that are common romanised Indic words (INDIC below: short function words and stock phrases such as
     hai, nahi, kaise, kya, aur, ke, ki, ko, se for Hindi, and a few for bn, mr, ta, te, kn, ml, gu).
     Words that are also English (in, to, me, is ...) are not on the list, so plain English text scores zero.
  3. Count the letters with IAST diacritics (ā ī ū ṛ ṃ ṅ ñ ṭ ḍ ṇ ś ṣ ḥ), the scholarly way of romanising Sanskrit.
  4. The document is romanised Indic when it has at least MIN_HITS Indic words, of which at least MIN_DISTINCT are
     different words (one scheme name repeated, "Yojana Yojana Yojana", is not enough), or at least MIN_IAST IAST
     letters inside Latin words of at least two letters.
That is all: no model, no training. The thresholds were chosen on testset_100.csv (see eval_v1.md).

Usage
  python3 detector.py "aap kaise ho, sab theek hai?"      prints the decision and the words it matched
  from detector import detect; detect(text) -> {"romanised": bool, "hits": int, "iast": int, "latin_words": int, ...}
"""
import re
import sys

MIN_HITS = 3
MIN_DISTINCT = 2
MIN_IAST = 5

# Common romanised words per language. Each is frequent in casual romanised writing and is not an English word
# (words such as "in", "to", "me", "hi", "is", "na" are left out on purpose, so English does not trigger the rule).
INDIC = {
    "hi": """hai hain hoon hu hota hoti hote tha thi nahi nahin nhi kya kyu kyun kyon kaise kaisa kaisi kahan
             kab kaun kitna kitne aur bhi ka ki ke ko se ye yeh wo woh vo mera meri mere tera teri tumhara hamara
             apna apni apne aap aapka aapki hum tum mujhe tujhe usko unko uski uska unki liye wala wale wali raha
             rahi rahe karna karne karte karta kare karen karein kiya kijiye hona hone gaya gayi diya jata jati
             jaata sakta sakte chahiye ek sab bahut kuch accha acha theek thik abhi phir lekin agar jab yahan
             wahan aaj kal mein mai bhai ji matlab sirf yojana bharti rashifal shayari""",
    "bn": """ami tumi apni amar tomar achhe korbo kore korte hobe hoy hoyeche kono keno kemon kotha bolbo
             tomay ekta onek bhalo valo kintu ebong jodi""",
    "mr": """ahe aahe aahet nahi mala tula tumhi amhi kasa kashi kase ani zala jhala kela keli hoti""",
    "ta": """enna illa illai unga enga naan nee avan aval romba irukku irukken irrunga sollu vanakkam payangal
             nanmaigal vilai matrum alavu valipadu muraigal payanpaadugal marundhalavu vilaivugal pakka eppadi""",
    "te": """andaru bagunnara bagundi emi enti ledu undi unnaru chala kani inka okka meeru nenu memu cheyandi
             ela enduku""",
    "kn": """nanu naanu neenu avaru illa ide beku maadi hege yenu enu alli nanage nimage kelasa""",
    "ml": """njan ningal enthu illa undu aanu cheyyuka""",
    "gu": """che chhe tame ame shu kem nathi""",
}
INDIC_WORDS = {w for ws in INDIC.values() for w in ws.split()}

IAST = set("āīūṛṝḷṃṁṅñṭḍṇśṣḥĀĪŪṚṜḶṂṀṄÑṬḌṆŚṢḤ")
NOISE = re.compile(r"https?://\S+|www\.\S+|\S+@\S+|[@#]\w+")
WORD = re.compile(r"[A-Za-zāīūṛṝḷṃṁṅñṭḍṇśṣḥĀĪŪṚṜḶṂṀṄÑṬḌṆŚṢḤ]+")


def detect(text, min_hits=MIN_HITS, min_distinct=MIN_DISTINCT, min_iast=MIN_IAST):
    """Decision and the counts behind it, for one document."""
    words = [w for w in WORD.findall(NOISE.sub(" ", text or "")) if not (len(w) > 1 and w.isupper())]
    hits = [w.lower() for w in words if w.lower() in INDIC_WORDS]
    distinct = len(set(hits))
    iast = sum(c in IAST for w in words if len(w) >= 2 for c in w)
    return {"romanised": (len(hits) >= min_hits and distinct >= min_distinct) or iast >= min_iast,
            "hits": len(hits), "distinct": distinct, "iast": iast, "latin_words": len(words),
            "examples": sorted(set(hits))[:8]}


if __name__ == "__main__":
    r = detect(" ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read())
    print(r)
