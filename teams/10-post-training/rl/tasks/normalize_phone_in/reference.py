import unicodedata
def normalize_phone_in(s):
    t = "".join(c for c in s if c not in " -()")
    out = []
    for i, c in enumerate(t):
        if c == "+" and i == 0:
            out.append(c)
            continue
        d = unicodedata.decimal(c, None)
        if d is None:
            return None
        out.append(str(d))
    t = "".join(out)
    if t.startswith("+"):
        if not (t.startswith("+91") and len(t) == 13):
            return None
        d = t[3:]
    elif t.startswith("0091") and len(t) == 14:
        d = t[4:]
    elif t.startswith("91") and len(t) == 12:
        d = t[2:]
    elif t.startswith("0") and len(t) == 11:
        d = t[1:]
    elif len(t) == 10:
        d = t
    else:
        return None
    if not d.isascii() or not d.isdigit() or d[0] not in "6789":
        return None
    return "+91" + d
