import unicodedata
ZW = ("\u200d", "\u200c")
def _virama(c):
    return c != "" and unicodedata.combining(c) == 9
def cluster_count(s):
    n = 0
    prev = prev2 = ""
    for ch in s:
        cat = unicodedata.category(ch)
        joins = cat.startswith("M") or ch in ZW or (
            cat.startswith("L") and (_virama(prev) or (prev in ZW and _virama(prev2))))
        if prev == "" or not joins:
            n += 1
        prev2, prev = prev, ch
    return n
