import re
_PAT = re.compile(r"[ \t]*(?:(\d+)d)?[ \t]*(?:(\d+)h)?[ \t]*(?:(\d+)m)?[ \t]*(?:(\d+)s)?[ \t]*", re.I | re.A)
def parse_duration(s):
    m = _PAT.fullmatch(s)
    if m is None or all(g is None for g in m.groups()):
        raise ValueError("bad duration")
    d, h, mi, sec = (int(g) if g is not None else 0 for g in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + sec
