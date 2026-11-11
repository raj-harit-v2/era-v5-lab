import unicodedata
_BASE = {"ascii": 0x30, "devanagari": 0x966, "bengali": 0x9E6, "tamil": 0xBE6}
def transliterate_digits(s, target):
    if target not in _BASE:
        raise ValueError("unknown target")
    base = _BASE[target]
    out = []
    for c in s:
        d = unicodedata.decimal(c, None)
        out.append(chr(base + d) if d is not None else c)
    return "".join(out)
