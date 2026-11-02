# TSAI decision on F1, 31 Oct: a typed placeholder for a private person's details, drop a personal listing, keep organisations.
# In code, a value is replaced only inside a comment or a string, found with tree-sitter. So `x = 555-010-0199` stays. Prose has no tree:
# math and science packs take the prose path (_F1_PROSE), which reads the block around a value instead.
from bisect import bisect_right

_F1_TREE = {"cpp", "go", "java", "javascript", "python", "rust", "typescript"}
_F1_LANGS = set(_F1_TREE)  # families with a harm test so far. Prose families go here after theirs; prose has no tree, so regex alone decides
# Prose packs with their own harm test run the prose path below instead (block context, contact cards, people tables), not the
# line regex. Keyed by pack_id prefix, because "en" is shared with the English family, which has no F1 harm test yet. A doc
# without a pack_id never takes this path.
_F1_PROSE = {"math-": {"en"}, "sci-": {"eng_Latn"}}
_F1_EMAIL = re.compile(r"(?<![\w.+%-])([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})(?![\w-])")
_F1_ROLE = re.compile(r"(?i)^(info|contact|contacts|support|help|helpdesk|admin|administrator|sales|office|press|media|hello|enquiries|inquiries|"
                      r"webmaster|postmaster|noreply|no-reply|donotreply|service|services|customerservice|billing|careers|jobs|hr|legal|security|abuse|team|git|root)$")
_F1_SAFE_DOMAIN = re.compile(r"(?i)(^|\.)(example\.(com|org|net)|localhost|test|invalid|users\.noreply\.github\.com)$|(^|\.)(gov|mil)(\.[a-z]{2})?$")
_F1_FILE_END = re.compile(r"(?i)\.(js|ts|py|go|rs|java|c|h|cpp|hpp|css|html|md|json|png|jpg|svg|gif)$")  # npm scopes and retina image names
_F1_PHONE = re.compile(r"(?<![\w.+/#=-])(?:(?:\+\d{1,3}[ .-]?)?(?:\(?\d{2,5}\)?[ .-]){1,3}\d{3,5}|\+?\d{10,13})(?![\w/-]|\.\d)")
_F1_PHONE_WORD = re.compile(r"(?i)\b(tel|telephone|phone|mobile|cell|fax|whatsapp|call me)\b[^\n]{0,30}$")
_F1_ADDRESS = re.compile(r"\b\d{1,5}[A-Za-z]?\s+(?:[A-Z][A-Za-z]*\.?\s+){1,4}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl|Terrace|Crescent|Nagar|Marg|Colony)\b\.?")
_F1_ORG = re.compile(r"(?i)\b(inc|ltd|llc|corp|corporation|company|university|college|school|hospital|clinic|department|dept|ministry|council|office|"
                     r"embassy|police|bank|library|museum|hotel|restaurant|customer service|support|helpline|hotline|toll[- ]free|headquarters|hq|reception|sales)\b")


@cache
def _f1_parser(lang):
    from tree_sitter_language_pack import get_parser  # no silent fallback: without the parser a hit in code raises, and the harm test shows it
    return get_parser(lang)


def _f1_text_spans(text, lang):
    """Sorted (start byte, end byte) of the comments and strings of a code file."""
    out, stack = [], [_f1_parser(lang).parse(text.encode("utf-8", "replace")).root_node]
    while stack:
        n = stack.pop()
        if "comment" in n.type or "string" in n.type or n.type == "jsx_text":
            out.append((n.start_byte, n.end_byte))
        else:
            stack.extend(n.children)
    return sorted(out)


def _f1_is_phone(m, line):
    digits = sum(c.isdigit() for c in m.group())
    if not 10 <= digits <= 13:
        return False
    if m.group().startswith("+") or _F1_PHONE_WORD.search(line[:m.start()]):
        return True
    return bool(re.fullmatch(r"\(?\d{3}\)?[ -]\d{3}-\d{4}", m.group()))  # the plain US form; digit groups alone are too common in data


def _f1_hits(line, previous):
    """(start, end, tag) of a private person's details on one line. An organisation on this line or the one above keeps its phone and address."""
    out = [(m.start(), m.end(), "<EMAIL>") for m in _F1_EMAIL.finditer(line)
           if not (_F1_ROLE.match(m.group(1)) or _F1_SAFE_DOMAIN.search(m.group(2)) or _F1_FILE_END.search(m.group(2)))]
    if not (_F1_ORG.search(line) or _F1_ORG.search(previous)):
        for rx, tag in ((_F1_PHONE, "<PHONE>"), (_F1_ADDRESS, "<ADDRESS>")):
            for m in rx.finditer(line):
                if (tag != "<PHONE>" or _f1_is_phone(m, line)) and not any(s < m.end() and m.start() < e for s, e, _ in out):
                    out.append((m.start(), m.end(), tag))
    return sorted(out)


# ---------------------------------------------------------------- prose path (math, science)
# A value is private when a private label sits on it ("Home:", "Cell:", "Daytime Phone"), when it is in a person's contact
# card (each field on its own line, two personal fields or more), or in a | Name | Telephone | table. It is kept when the
# block or the heading above names an organisation or public office, for toll-free numbers, role mailboxes and example
# domains. A page made mostly of "SURNAME, Forenames, age, address" entries is dropped. Mailing-list "name at host" only
# when alone on a line or inside <...>.
_F1P_PHONE_PH, _F1P_EMAIL_PH, _F1P_ADDRESS_PH = "<PHONE>", "<EMAIL>", "<ADDRESS>"
_F1P_PLACEHOLDER = re.compile(r"<(?:PHONE|EMAIL|ADDRESS)>")

# ---------------------------------------------------------------- emails
_F1P_EMAIL = re.compile(r"(?<![\w.+-])([A-Za-z0-9][A-Za-z0-9._%+-]*)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})(?![\w-])")
# "name at host.tld" as written in mailing-list archives: only alone on its line, or inside <...>
_F1P_AT_EMAIL = re.compile(r"(?m)(?:^[ \t]*|<)([a-z0-9][a-z0-9._%+-]*) at ((?:[a-z0-9-]+\.)+[a-z]{2,})(?=[ \t]*$|>)")
_F1P_ROLE_LOCAL = re.compile(
    r"^(?:info|admin|administrator|team|contact|contactus|support|hello|office|mail|webmaster|help|helpdesk|"
    r"no-?reply|donotreply|sales|security|abuse|postmaster|enquiries|enquiry|inquiries|press|media|news|"
    r"hr|jobs|careers|clerk|library|admissions|registrar|events|feedback|service|services|billing|accounts|"
    r"orders|editor|editors|editorial|journal|publications|marketing|communications|general|reception|"
    r"secretary|secretariat|board|council|dept|department|root|bugs|devnull|lists?|"
    r"[a-z]+-(?:dev|devel|users|announce|discuss|help|bugs|request)s?)$", re.I)
_F1P_SAFE_DOMAIN = re.compile(r"(?:^|\.)(?:example\.(?:com|org|net)|test\.com|localhost|domain\.com|email\.com|"
                         r"(?:users\.)?noreply\.github\.com)$", re.I)


_F1P_EMAIL_ORG = re.compile(
    r"(?i)\b(?:contact\s+us|enquir(?:y|ies)|inquir(?:y|ies)|customer|for\s+more\s+information|discount|offers?|"
    r"office\s+hours?|department|faculty|professor|lecturer|instructor|university|college|school|company|"
    r"inc|ltd|llc|corporation|agency|office|council|board|commission|clinic|hospital)\b")


def _F1P_email_is_private(text, start, end, local, domain):
    if _F1P_SAFE_DOMAIN.search(domain) or _F1P_ROLE_LOCAL.match(local):
        return False
    near = text[max(0, start - 160):start] + " " + text[end:end + 40]      # may cross one blank line ("Contact us")
    return not _F1P_EMAIL_ORG.search(_F1P_EMAILISH.sub(" ", near))


def _F1P_email(m):
    return _F1P_EMAIL_PH if _F1P_email_is_private(m.string, m.start(), m.end(), m.group(1), m.group(2)) else m.group(0)


# ---------------------------------------------------------------- context: organisation or private person
_F1P_ORG = re.compile(
    r"\b(?:inc|llc|l\.l\.c|ltd|limited|corp|corporation|company|co\.|plc|gmbh|llp|l\.l\.p|"
    r"university|college|school|academy|institute|institution|laborator(?:y|ies)|"
    r"department|dept|division|office|bureau|agency|authority|commission|committee|council|board|ministry|"
    r"city|county|town|township|village|borough|parish|state|federal|government|municipal|district|"
    r"court|police|sheriff|fire|army|navy|air\s+force|afb|hospital|clinic|medical|health|center|centre|"
    r"library|museum|church|foundation|association|society|federation|union|network|services?|hotline|"
    r"helpline|crisis|switchboard|reception|headquarters|firm|attorneys?|law|realty|group|hotel|bank|"
    r"store|restaurant|press|publish(?:er|ing)|journal|newspaper|customer|toll[- ]free|website|serves|"
    r"programs?|programmes?|pantry|shelter|extension|resources?|assistance|ministr(?:y|ies)|coalition|"
    r"partnership|alliance|cooperative|clerk|commissioner|mayor|manager|director|coordinator|officer|"
    r"superintendent|principal|dean|professor|faculty|staff|"
    r"www\.|https?://|\.gov\b|\.edu\b|\.org\b)", re.I)
# a private label right before or after the value: "Home:", "Home Phone", "(cell)", "Daytime Phone"
_F1P_PL = r"(?:home|residence|cell|mobile|private|personal|daytime|evening|preferred)"
# the label form only: "Home: ", "Home Phone ", "Cell #", "(mobile)", not a word inside a name ("Children's Home")
_F1P_PRIVATE_BEFORE = re.compile(rf"(?i)\b{_F1P_PL}\s*(?:(?:phone|tel(?:ephone)?|number|no\.)\s*[:#-]?|[:#])\s*$")
_F1P_PRIVATE_AFTER = re.compile(rf"(?i)^\s*[(\[]?\s*{_F1P_PL}\b")
_F1P_EMAILISH = re.compile(r"[\w.+-]+@[\w.-]+|\b[a-z0-9._%+-]+ at (?:[a-z0-9-]+\.)+[a-z]{2,}\b|<(?:PHONE|EMAIL|ADDRESS)>")
_F1P_HEADING = re.compile(r"(?m)^(?:#{1,6} .*|\*\*[^*\n]{2,120}\*\*)[ \t]*$")


def _F1P_window(text, start, end, before=160, after=60):
    """The text around a value inside its block: never crosses a blank line."""
    lo = text.rfind("\n\n", 0, start)
    lo = max(lo + 2 if lo >= 0 else 0, start - before)
    hi = text.find("\n\n", end)
    hi = min(hi if hi >= 0 else len(text), end + after)
    return text[lo:start], text[end:hi]


def _F1P_context(text, start, end):
    """True: a private label sits on the value. False: an organisation is named in the block or the heading
    above it. None: no evidence."""
    left, right = _F1P_window(text, start, end)
    line = text[text.rfind("\n", 0, start) + 1:start] + " " + text[end:(text.find("\n", end) + 1 or len(text) + 1) - 1]
    if (_F1P_PRIVATE_BEFORE.search(left[-30:]) or _F1P_PRIVATE_AFTER.search(right[:16])) \
            and not _F1P_ORG.search(re.sub(rf"(?i){_F1P_PL}|phone|tel(?:ephone)?|number", " ", line)):
        return True
    heads = [h.group(0) for h in _F1P_HEADING.finditer(text, max(0, start - 600), start)]
    ctx = _F1P_ADDRESS.sub(" ", _F1P_EMAILISH.sub(" ", left + right + " " + (heads[-1] if heads else "")))
    if _F1P_ORG.search(ctx):          # street names ("College Ave", "Court St") and placeholders are not evidence
        return False
    return None


# ---------------------------------------------------------------- phones
_F1P_PHONE = re.compile(
    r"(?<![\w/.-])(?:\+?1[ .-]?)?(?:\(\d{3}\)\s?|\d{3}[ .-])\d{3}[ .-]\d{4}(?![\w/-])"   # North American
    r"|(?<![\w/.-])\+\d{1,3}(?:[ .-]?\(?\d{1,4}\)?){2,5}\d(?![\w/-])")                     # +international
_F1P_TOLL_FREE = re.compile(r"^(?:\+?1[ .-]?)?\(?(?:800|888|877|866|855|844|833)\b")

# ---------------------------------------------------------------- street addresses
_F1P_STREET = (r"(?i:street|st|road|rd|lane|ln|avenue|ave|drive|dr|trail|trl|court|ct|way|boulevard|blvd|place|pl|"
          r"circle|cir|terrace|ter|mansions|gardens|close|crescent|cres|parkway|pkwy|row|square|sq|grove)")
_F1P_ADDRESS = re.compile(
    rf"\b\d{{1,5}}[A-Za-z]?,?[ \t]+(?:[NSEW]\.?[ \t]+)?(?:[A-Z][a-z]+\.?[ \t]+){{1,3}}{_F1P_STREET}\b\.?"
    rf"(?:,?[ \t]*(?:Apt|Unit|#)[ \t]*\w+)?"
    rf"(?:,?[ \t]*\n?[ \t]*[A-Z][A-Za-z.' -]{{1,30}},?[ \t]+(?:[A-Z]{{2}}|[A-Z][a-z]+)\.?,?[ \t]+\d{{5}}(?:-\d{{4}})?)?")
# a contact card: a line in the same block that is only a name (2 or 3 capitalised words) or a social handle
_F1P_PERSON_CARD = re.compile(r"(?m)^[ \t]*(?:[A-Z][a-z]+(?:[ .-][A-Z][a-z]*\.?){1,2}|@\w{3,})[ \t]*$")


def _F1P_card(left):
    """A person's contact card: at least two personal fields in the block above the value, e.g. a name-only line
    (with no organisation word) plus a street address, an email or a social handle. A name with a phone alone is
    not enough: directories of organisations look the same."""
    names = [m.group(0) for m in _F1P_PERSON_CARD.finditer(left) if not _F1P_ORG.search(m.group(0))]
    fields = sum([bool(names), bool(_F1P_ADDRESS.search(left) or "<ADDRESS>" in left), bool(re.search(r"[\w.+-]+@[\w.-]+|<EMAIL>", left)),
                  bool(re.search(r"(?m)^[ \t]*@\w{3,}", left))])
    return fields >= 2


def _F1P_value_alone(text, start, end):
    """A contact card puts each field on its own line: the value's line holds no name and is no list item."""
    lo = text.rfind("\n", 0, start) + 1
    hi = text.find("\n", end)
    rest = (text[lo:start] + " " + text[end:hi if hi >= 0 else len(text)]).strip()
    if re.match(r"^[-*•]\s", text[lo:start].lstrip()):
        return False
    rest = _F1P_PLACEHOLDER.sub(" ", _F1P_PHONE.sub(" ", rest))
    return not re.search(r"[A-Z]", rest) and len(re.findall(r"[a-z]+", rest)) <= 2


# ---------------------------------------------------------------- tables of people: | Name | Telephone | Fax |
_F1P_TABLE_HEAD = re.compile(r"(?i)^\|.*\bname\b.*\|.*\b(?:telephone|phone|tel|fax|mobile|cell)\b.*\|[ \t]*$")
_F1P_PHONE_COL = re.compile(r"(?i)telephone|phone|\btel\b|fax|mobile|cell")


def _F1P_people_tables(text):
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        head = lines[i]
        if _F1P_TABLE_HEAD.match(head) and not _F1P_ORG.search(re.sub(r"(?i)\bname\b", "", head)):
            cols = [c for c in head.strip().strip("|").split("|")]
            phone_cols = {k for k, c in enumerate(cols) if _F1P_PHONE_COL.search(c)}
            j = i + 1
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                cells = lines[j].strip().strip("|").split("|")
                if not all(set(c.strip()) <= set("-: ") for c in cells):      # skip the |---| line
                    for k in phone_cols:
                        if k < len(cells) and sum(ch.isdigit() for ch in cells[k]) >= 7 \
                                and re.fullmatch(r"[\s+()\d./-]+", cells[k]):
                            cells[k] = " " + _F1P_PHONE_PH + " "
                    lines[j] = "|" + "|".join(cells) + "|"
                j += 1
            i = j
        else:
            i += 1
    return "\n".join(lines)


# ---------------------------------------------------------------- personal listings
# "SURNAME, Forenames, 37, <address>, <occupation>": notices about named individuals, one per line
_F1P_NOTICE = re.compile(r"(?m)^[A-Z][A-Z'-]+(?: [A-Z][A-Z'-]+)*, [A-Z][a-z]+(?: [A-Z][a-z.]+)*,? (?:\d{1,3}, )?.*$")


def _F1P_listing_share(text):
    total = len(text.strip()) or 1
    return sum(len(m.group(0)) for m in _F1P_NOTICE.finditer(text)) / total


# ---------------------------------------------------------------- the rule
def _f1_prose(text):
    if _F1P_listing_share(text) > 0.5:
        return ("drop", "")

    out = _F1P_people_tables(text)
    out = _F1P_EMAIL.sub(_F1P_email, out)
    out = _F1P_AT_EMAIL.sub(lambda m: m.group(0).replace(m.group(1) + " at " + m.group(2), _F1P_EMAIL_PH)
                       if _F1P_email_is_private(m.string, m.start(1), m.end(2), m.group(1), m.group(2)) else m.group(0), out)

    def phone(m):
        if _F1P_TOLL_FREE.match(m.group(0)):
            return m.group(0)
        verdict = _F1P_context(m.string, m.start(), m.end())
        if verdict is None:
            verdict = _F1P_value_alone(m.string, m.start(), m.end()) and _F1P_card(_F1P_window(m.string, m.start(), m.end())[0])
        return _F1P_PHONE_PH if verdict else m.group(0)
    out = _F1P_PHONE.sub(phone, out)

    def address(m):
        verdict = _F1P_context(m.string, m.start(), m.end())
        if verdict is None:          # an address with a private phone or email next to it
            verdict = bool(re.search(r"<(?:PHONE|EMAIL)>", m.string[m.end():m.end() + 120]))
        return _F1P_ADDRESS_PH if verdict else m.group(0)
    out = _F1P_ADDRESS.sub(address, out)
    return out


def f1(doc):
    """F1: <PHONE>, <EMAIL>, <ADDRESS> for a private person. Drop when lines with such details hold most of the text."""
    text, lang = doc["text"], doc.get("lang_label")
    pack = str(doc.get("pack_id") or "")
    if lang not in _F1_TREE and any(pack.startswith(p) and lang in tags for p, tags in _F1_PROSE.items()):
        new = _f1_prose(text)
        if isinstance(new, tuple):
            return ("drop", text)
        return ("fix" if new != text else "keep", new)
    if lang not in _F1_LANGS:
        return ("keep", text)
    out, hit_lines, hit_chars, previous, pos, spans = [], 0, 0, "", 0, None
    for line in text.split("\n"):
        new, last = [], 0
        for s, e, tag in _f1_hits(line, previous):
            if lang in _F1_TREE:
                if spans is None:
                    spans = _f1_text_spans(text, lang)
                    starts = [a for a, _ in spans]
                b = len(text[:pos + s].encode("utf-8", "replace"))
                i = bisect_right(starts, b) - 1
                if i < 0 or b >= spans[i][1]:
                    continue  # in code, not in a comment or a string
            new += [line[last:s], tag]
            last = e
        if new:
            hit_lines += 1
            hit_chars += len(line.strip())
        out.append("".join(new) + line[last:])
        previous = line
        pos += len(line) + 1
    if hit_lines >= 5 and hit_chars > 0.5 * sum(len(l.strip()) for l in text.split("\n")):
        return ("drop", text)
    new = "\n".join(out)
    return ("fix" if new != text else "keep", new)
