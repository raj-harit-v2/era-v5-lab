import re
from datetime import date as _date, timedelta
_FMT = re.compile(r"\d{4}-\d{2}-\d{2}", re.A)
def _parse(s):
    if not _FMT.fullmatch(s):
        raise ValueError("bad date")
    return _date(int(s[:4]), int(s[5:7]), int(s[8:10]))
def next_business_day(day, holidays):
    start = _parse(day)
    hol = {_parse(h) for h in holidays}
    d = start
    while True:
        if d == _date.max:
            raise ValueError("no business day left")
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in hol:
            return d.isoformat()
