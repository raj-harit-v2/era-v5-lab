# TSAI decision on F1, 31 Oct: a typed placeholder for a private person's details, drop a personal listing, keep organisations.
# In code, a value is replaced only inside a comment or a string, found with tree-sitter. So `x = 555-010-0199` stays. Prose has no tree:
# math and science packs take the prose path (_F1_PROSE), which reads the block around a value instead. Indic packs (ind-*)
# take the Indic path (_f1_indic): Indian phone formats, digits in any Indic script, Indian organisation domains and words.
from bisect import bisect_right
from functools import cache
import re

_F1_TREE = {"cpp", "go", "java", "javascript", "python", "rust", "typescript"}
_F1_CODE_PACKS = {"code-cpp": "cpp", "code-go": "go", "code-java": "java",
                  "code-js-ts": "typescript", "code-python": "python", "code-rust": "rust"}
_F1_LANGS = set(_F1_TREE)  # families with a harm test so far. Prose families go here after theirs; prose has no tree, so regex alone decides
# Prose packs with their own harm test run the prose path below instead (block context, contact cards, people tables), not the
# line regex. The pack decides, by pack_id prefix, not the language label: "en" is shared with the English family, which has its
# own F1 rule, and the label for one pack differs between the week-1 sample packs ("eng_Latn" for science) and the week-2 data
# ("en"). A doc without a pack_id never takes this path.
_F1_PROSE = ("math-", "sci-")
# Code-adjacent packs mix prose, code and data in one text, with no single parser for it. In cadj-commits only e-mail addresses
# are masked, never a phone or an address and never a drop: on the sample, the phone and address patterns hit IP addresses,
# part numbers, colour values and pixel arrays. As in the cadj-commits medicine (diagnosis/submissions/cadj-commits/kunal2016/
# medicine.md, medicine 1), made-up addresses at test domains and mail@ stay. Deferred (24 Nov 2026): cadj-notebooks and
# cadj-stackexchange (no gold set; on the sample, stackexchange's e-mail-like strings are ssh and git logins, URLs with a user
# name, systemd units and code), and the medicine's LinkedIn profile URLs.
_F1_EMAIL_ONLY = ("cadj-commits",)
_F1_CADJ_SAFE = re.compile(r"(?i)(^|\.)(test\.com|domain\.com|email\.com|noreply\.github\.com)$")
_F1_CADJ_ROLE = re.compile(r"(?i)^mail$")
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
_F1_DIGIT = re.compile(r"\d")  # the same Unicode decimal digits required by PHONE and ADDRESS


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


def _f1_emails(line):
    """(start, end, "<EMAIL>") of each private e-mail address on one line: not a role mailbox, an example domain or a file name."""
    return [(m.start(), m.end(), "<EMAIL>") for m in _F1_EMAIL.finditer(line)
            if not (_F1_ROLE.match(m.group(1)) or _F1_SAFE_DOMAIN.search(m.group(2)) or _F1_FILE_END.search(m.group(2)))] if "@" in line else []


def _f1_emails_only(text):
    """The text with each private e-mail address replaced by <EMAIL> (cadj-commits)."""
    if "@" not in text:
        return text
    out = []
    for line in text.split("\n"):
        for s, e, tag in reversed(_f1_emails(line)):
            m = _F1_EMAIL.match(line, s)
            if _F1_CADJ_SAFE.search(m.group(2)) or _F1_CADJ_ROLE.match(m.group(1)):
                continue
            line = line[:s] + tag + line[e:]
        out.append(line)
    return "\n".join(out)


def _f1_hits(line, previous):
    """(start, end, tag) of a private person's details on one line. An organisation on this line or the one above keeps its phone and address."""
    out = _f1_emails(line)
    if not _F1_DIGIT.search(line):
        return out  # email finditer already orders the spans; no phone/address can match
    org = None
    for rx, tag in ((_F1_PHONE, "<PHONE>"), (_F1_ADDRESS, "<ADDRESS>")):
        for m in rx.finditer(line):
            if tag == "<PHONE>" and not _f1_is_phone(m, line):
                continue
            # Organisation context only matters when a phone/address could actually be masked.
            if org is None:
                org = bool(_F1_ORG.search(line) or _F1_ORG.search(previous))
            if org:
                return out  # all phones/addresses stay; only the ordered email spans remain
            if not any(s < m.end() and m.start() < e for s, e, _ in out):
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
# Speed: every match of the pattern above holds " at " and a host name, so a text without this cannot match, and the slower
# search for the whole pattern is skipped.
_F1P_AT_HOST = re.compile(r" at (?:[a-z0-9-]+\.)+[a-z]{2,}")
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
_F1P_PHONE_NA = r"(?<![\w/.-])(?:\+?1[ .-]?)?(?:\(\d{3}\)\s?|\d{3}[ .-])\d{3}[ .-]\d{4}(?![\w/-])"   # North American
_F1P_PHONE_INTL = r"(?<![\w/.-])\+\d{1,3}(?:[ .-]?\(?\d{1,4}\)?){2,5}\d(?![\w/-])"                   # +international
_F1P_PHONE = re.compile(_F1P_PHONE_NA + "|" + _F1P_PHONE_INTL)       # the same pattern as before, written in two parts
# Speed: the international form starts with a literal "+", so in a text with no "+" only the North American form can match, and a
# regex of that form alone finds exactly the same matches (the engine tries the first form first and the second can never match).
_F1P_PHONE_NA_ONLY = re.compile(_F1P_PHONE_NA)
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
    if re.match(r"^[-*\u2022]\s", text[lo:start].lstrip()):
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
    if "@" in out:                       # speed: _F1P_EMAIL needs an "@", and most texts have none
        out = _F1P_EMAIL.sub(_F1P_email, out)
    if _F1P_AT_HOST.search(out):         # speed: see _F1P_AT_HOST
        out = _F1P_AT_EMAIL.sub(lambda m: m.group(0).replace(m.group(1) + " at " + m.group(2), _F1P_EMAIL_PH)
                           if _F1P_email_is_private(m.string, m.start(1), m.end(2), m.group(1), m.group(2)) else m.group(0), out)

    def phone(m):
        if _F1P_TOLL_FREE.match(m.group(0)):
            return m.group(0)
        verdict = _F1P_context(m.string, m.start(), m.end())
        if verdict is None:
            verdict = _F1P_value_alone(m.string, m.start(), m.end()) and _F1P_card(_F1P_window(m.string, m.start(), m.end())[0])
        return _F1P_PHONE_PH if verdict else m.group(0)
    out = (_F1P_PHONE if "+" in out else _F1P_PHONE_NA_ONLY).sub(phone, out)     # speed: see _F1P_PHONE_NA_ONLY

    def address(m):
        verdict = _F1P_context(m.string, m.start(), m.end())
        if verdict is None:          # an address with a private phone or email next to it
            verdict = bool(re.search(r"<(?:PHONE|EMAIL)>", m.string[m.end():m.end() + 120]))
        return _F1P_ADDRESS_PH if verdict else m.group(0)
    out = _F1P_ADDRESS.sub(address, out)
    return out


# ---------------------------------------------------------------- Indic path (ind-* packs)
# The same TSAI ruling for Indian text: <PHONE> and <EMAIL> for a private person, organisations and public offices kept.
# - A mobile number (+91 / 0 / 91 and ten digits from 6-9, in any spacing, in Latin or any Indic digits) is private unless
#   its block names an organisation or public office (English or Indian-language words, a website, an organisation's
#   email). Indian web text puts personal mobiles in ads, profiles and matrimonials with no label, so a bare one is private.
# - A landline (0 + STD code + number) is kept unless a private label sits on it (Home:, \u092e\u094b\u092c\u093e\u0907\u0932, ...).
# - Toll-free (1800, 1860) numbers are kept.
# - An email is private unless it is a role mailbox, an example domain, an Indian organisation domain (.gov.in, .nic.in,
#   .ac.in, .edu.in, .res.in, .ernet.in, .org.in, .co.in) or its block names an organisation.
# Not done: street addresses (Indian addresses have no fixed form), personal listings.
_F1I_DIGITS = str.maketrans({chr(base + d): str(d) for base in (0x0966, 0x09E6, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66,
                                                                 0x0CE6, 0x0D66) for d in range(10)})   # one char for one char
_F1I_MOBILE = re.compile(r"(?<![\w/.+-])(?:(?:\+|00)[ \t]?91[ \t-]?|91[ \t-]?|0[ \t-]?)?"
                         r"(?:[6-9][0-9]{4}[ \t-]?[0-9]{5}|[6-9][0-9]{2}[ \t-][0-9]{3}[ \t-][0-9]{4})(?![\w/-]|\.[0-9])", re.A)
_F1I_LANDLINE = re.compile(r"(?<![\w/.+-])(?:\+91[ \t-]?)?\(?0[1-9][0-9]{1,3}\)?[ \t-]?[2-9][0-9]{2,3}[ \t-]?[0-9]{3,4}(?![\w/-]|\.[0-9])", re.A)
_F1I_TOLL_FREE = re.compile(r"(?<![\w/.+-])18[06]0[ \t-]?[0-9]{3}[ \t-]?[0-9]{3,4}(?![\w/-])", re.A)
# Speed: most texts hold no phone number, and each of the three regexes above starts with a lookbehind, so the engine tries every
# position. A text that lacks the core every match must contain (the regex without its lookarounds and optional prefixes) cannot
# match, so the regex is skipped. A regex that starts with a literal or a character set is scanned much faster.
_F1I_INDIC_DIGIT = re.compile("[" + "".join(map(chr, _F1I_DIGITS)) + "]")   # the characters _F1I_DIGITS maps: none in the text, nothing to translate
_F1I_MOBILE_CORE = re.compile(r"[6-9][0-9]{4}[ \t-]?[0-9]{5}|[6-9][0-9]{2}[ \t-][0-9]{3}[ \t-][0-9]{4}", re.A)
_F1I_LANDLINE_CORE = re.compile(r"0[1-9][0-9]{1,3}\)?[ \t-]?[2-9][0-9]{2,3}[ \t-]?[0-9]{3,4}", re.A)   # _F1I_TOLL_FREE needs "1800" or "1860"
_F1I_ORG_DOMAIN = re.compile(r"(?i)(?:^|\.)(?:gov|nic|ac|edu|res|ernet|org|co|mil)\.in$")
_F1I_ORG_WORDS = re.compile(
    "\u0915\u093e\u0930\u094d\u092f\u093e\u0932\u092f|\u0935\u093f\u092d\u093e\u0917|\u092e\u0902\u0924\u094d\u0930\u093e\u0932\u092f|\u092e\u0928\u094d\u0924\u094d\u0930\u093e\u0932\u092f|\u0938\u0930\u0915\u093e\u0930|\u0936\u093e\u0938\u0928|\u0935\u093f\u0936\u094d\u0935\u0935\u093f\u0926\u094d\u092f\u093e\u0932\u092f|\u092e\u0939\u093e\u0935\u093f\u0926\u094d\u092f\u093e\u0932\u092f|\u0935\u093f\u0926\u094d\u092f\u093e\u0932\u092f|\u0935\u093f\u0926\u094d\u092f\u093e\u092a\u0940\u0920|\u0938\u0902\u0938\u094d\u0925\u093e\u0928|\u0938\u0902\u0938\u094d\u0925\u093e|\u0915\u0902\u092a\u0928\u0940|\u0915\u092e\u094d\u092a\u0928\u0940|"
    "\u0932\u093f\u092e\u093f\u091f\u0947\u0921|\u092a\u094d\u0930\u093e\u0907\u0935\u0947\u091f|\u092c\u0948\u0902\u0915|\u0905\u0938\u094d\u092a\u0924\u093e\u0932|\u0930\u0941\u0917\u094d\u0923\u093e\u0932\u092f|\u092a\u0941\u0932\u093f\u0938|\u092a\u094b\u0932\u0940\u0938|\u0928\u0917\u0930 \u0928\u093f\u0917\u092e|\u092e\u0939\u093e\u0928\u0917\u0930\u092a\u093e\u0932\u093f\u0915\u093e|\u0928\u0917\u0930\u092a\u093e\u0932\u093f\u0915\u093e|\u092a\u0902\u091a\u093e\u092f\u0924|\u0917\u094d\u0930\u093e\u092e\u092a\u0902\u091a\u093e\u092f\u0924|\u0939\u0947\u0932\u094d\u092a\u0932\u093e\u0907\u0928|\u091f\u094b\u0932 \u092b\u094d\u0930\u0940|"
    "\u0917\u094d\u0930\u093e\u0939\u0915 \u0938\u0947\u0935\u093e|\u0906\u092f\u094b\u0917|\u092a\u0930\u093f\u0937\u0926|\u0928\u093f\u0917\u092e|\u092e\u0902\u0921\u0933|\u092e\u0923\u094d\u0921\u0932|\u0938\u092e\u093f\u0924\u093f|\u0928\u094d\u092f\u093e\u092f\u093e\u0932\u092f|"
    "\u0995\u09be\u09b0\u09cd\u09af\u09be\u09b2\u09af\u09bc|\u09a6\u09aa\u09cd\u09a4\u09b0|\u09ac\u09bf\u09ad\u09be\u0997|\u09ae\u09a8\u09cd\u09a4\u09cd\u09b0\u0995|\u09b8\u09b0\u0995\u09be\u09b0|\u09ac\u09bf\u09b6\u09cd\u09ac\u09ac\u09bf\u09a6\u09cd\u09af\u09be\u09b2\u09af\u09bc|\u09ae\u09b9\u09be\u09ac\u09bf\u09a6\u09cd\u09af\u09be\u09b2\u09af\u09bc|\u09ac\u09bf\u09a6\u09cd\u09af\u09be\u09b2\u09af\u09bc|\u09b8\u0982\u09b8\u09cd\u09a5\u09be|\u0995\u09cb\u09ae\u09cd\u09aa\u09be\u09a8\u09bf|\u09ac\u09cd\u09af\u09be\u0982\u0995|\u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2|\u09aa\u09c1\u09b2\u09bf\u09b6|\u09aa\u09cc\u09b0\u09b8\u09ad\u09be|"
    "\u0a95\u0a9a\u0ac7\u0ab0\u0ac0|\u0a95\u0abe\u0ab0\u0acd\u0aaf\u0abe\u0ab2\u0aaf|\u0ab5\u0abf\u0aad\u0abe\u0a97|\u0ab8\u0ab0\u0a95\u0abe\u0ab0|\u0aaf\u0ac1\u0aa8\u0abf\u0ab5\u0ab0\u0acd\u0ab8\u0abf\u0a9f\u0ac0|\u0ab5\u0abf\u0ab6\u0acd\u0ab5\u0ab5\u0abf\u0aa6\u0acd\u0aaf\u0abe\u0ab2\u0aaf|\u0ab6\u0abe\u0ab3\u0abe|\u0ab8\u0a82\u0ab8\u0acd\u0aa5\u0abe|\u0a95\u0a82\u0aaa\u0aa8\u0ac0|\u0aac\u0ac7\u0a82\u0a95|\u0ab9\u0acb\u0ab8\u0acd\u0aaa\u0abf\u0a9f\u0ab2|\u0aaa\u0acb\u0ab2\u0ac0\u0ab8|"
    "\u0a26\u0a2b\u0a3c\u0a24\u0a30|\u0a26\u0a2b\u0a24\u0a30|\u0a35\u0a3f\u0a2d\u0a3e\u0a17|\u0a38\u0a30\u0a15\u0a3e\u0a30|\u0a2f\u0a42\u0a28\u0a40\u0a35\u0a30\u0a38\u0a3f\u0a1f\u0a40|\u0a2c\u0a48\u0a02\u0a15|\u0a39\u0a38\u0a2a\u0a24\u0a3e\u0a32|\u0a2a\u0a41\u0a32\u0a3f\u0a38|"
    "\u0b15\u0b3e\u0b30\u0b4d\u0b2f\u0b4d\u0b5f\u0b3e\u0b33\u0b5f|\u0b2c\u0b3f\u0b2d\u0b3e\u0b17|\u0b38\u0b30\u0b15\u0b3e\u0b30|\u0b2c\u0b3f\u0b36\u0b4d\u0b71\u0b2c\u0b3f\u0b26\u0b4d\u0b5f\u0b3e\u0b33\u0b5f|\u0b2c\u0b4d\u0b5f\u0b3e\u0b19\u0b4d\u0b15|\u0b39\u0b38\u0b4d\u0b2a\u0b3f\u0b1f\u0b3e\u0b32|\u0b2a\u0b4b\u0b32\u0b3f\u0b38|"
    "\u0b85\u0bb2\u0bc1\u0bb5\u0bb2\u0b95\u0bae\u0bcd|\u0ba4\u0bc1\u0bb1\u0bc8|\u0b85\u0bb0\u0b9a\u0bc1|\u0b85\u0bae\u0bc8\u0b9a\u0bcd\u0b9a\u0b95\u0bae\u0bcd|\u0baa\u0bb2\u0bcd\u0b95\u0bb2\u0bc8\u0b95\u0bcd\u0b95\u0bb4\u0b95\u0bae\u0bcd|\u0b95\u0bb2\u0bcd\u0bb2\u0bc2\u0bb0\u0bbf|\u0baa\u0bb3\u0bcd\u0bb3\u0bbf|\u0ba8\u0bbf\u0bb1\u0bc1\u0bb5\u0ba9\u0bae\u0bcd|\u0bb5\u0b99\u0bcd\u0b95\u0bbf|\u0bae\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bc1\u0bb5\u0bae\u0ba9\u0bc8|\u0b95\u0bbe\u0bb5\u0bb2\u0bcd|\u0bae\u0bbe\u0ba8\u0b95\u0bb0\u0bbe\u0b9f\u0bcd\u0b9a\u0bbf|"
    "\u0c15\u0c3e\u0c30\u0c4d\u0c2f\u0c3e\u0c32\u0c2f\u0c02|\u0c36\u0c3e\u0c16|\u0c2a\u0c4d\u0c30\u0c2d\u0c41\u0c24\u0c4d\u0c35|\u0c35\u0c3f\u0c36\u0c4d\u0c35\u0c35\u0c3f\u0c26\u0c4d\u0c2f\u0c3e\u0c32\u0c2f\u0c02|\u0c15\u0c33\u0c3e\u0c36\u0c3e\u0c32|\u0c2a\u0c3e\u0c20\u0c36\u0c3e\u0c32|\u0c38\u0c02\u0c38\u0c4d\u0c25|\u0c2c\u0c4d\u0c2f\u0c3e\u0c02\u0c15\u0c41|\u0c06\u0c38\u0c41\u0c2a\u0c24\u0c4d\u0c30\u0c3f|\u0c2a\u0c4b\u0c32\u0c40\u0c38\u0c41|"
    "\u0c95\u0c9a\u0cc7\u0cb0\u0cbf|\u0c87\u0cb2\u0cbe\u0c96\u0cc6|\u0cb8\u0cb0\u0ccd\u0c95\u0cbe\u0cb0|\u0cb5\u0cbf\u0cb6\u0ccd\u0cb5\u0cb5\u0cbf\u0ca6\u0ccd\u0caf\u0cbe\u0cb2\u0caf|\u0c95\u0cbe\u0cb2\u0cc7\u0c9c\u0cc1|\u0cb6\u0cbe\u0cb2\u0cc6|\u0cb8\u0c82\u0cb8\u0ccd\u0ca5\u0cc6|\u0cac\u0ccd\u0caf\u0cbe\u0c82\u0c95\u0ccd|\u0c86\u0cb8\u0ccd\u0caa\u0ca4\u0ccd\u0cb0\u0cc6|\u0caa\u0cca\u0cb2\u0cc0\u0cb8\u0ccd|"
    "\u0d15\u0d3e\u0d30\u0d4d\u0d2f\u0d3e\u0d32\u0d2f\u0d02|\u0d13\u0d2b\u0d40\u0d38\u0d4d|\u0d35\u0d15\u0d41\u0d2a\u0d4d\u0d2a\u0d4d|\u0d38\u0d7c\u0d15\u0d4d\u0d15\u0d3e\u0d7c|\u0d38\u0d7c\u0d35\u0d15\u0d32\u0d3e\u0d36\u0d3e\u0d32|\u0d15\u0d4b\u0d33\u0d47\u0d1c\u0d4d|\u0d38\u0d4d\u0d15\u0d42\u0d7e|\u0d38\u0d4d\u0d25\u0d3e\u0d2a\u0d28\u0d02|\u0d2c\u0d3e\u0d19\u0d4d\u0d15\u0d4d|\u0d06\u0d36\u0d41\u0d2a\u0d24\u0d4d\u0d30\u0d3f|\u0d2a\u0d4b\u0d32\u0d40\u0d38\u0d4d")
_F1I_PRIVATE = re.compile(          # a private label right before the value
    r"(?i)(?:\b(?:home|residence|cell|mobile|mob|private|personal|whatsapp)\b\.?\s*(?:(?:phone|tel|no|number)\.?\s*)?[:#-]?"
    "|(?:\u092e\u094b\u092c\u093e\u0907\u0932|\u092e\u094b\u092c\u093e\u0908\u0932|\u092e\u094b\\.|\u092e\u094b\u092c\u093e\\.|\u0928\u093f\u091c\u0940|\u0935\u094d\u092f\u0915\u094d\u0924\u093f\u0917\u0924|\u09ae\u09cb\u09ac\u09be\u0987\u09b2|\u09ae\u09cb\\.|\u0aae\u0acb\u0aac\u0abe\u0a87\u0ab2|\u0aae\u0acb\\.|\u0a2e\u0a4b\u0a2c\u0a3e\u0a08\u0a32|\u0b2e\u0b4b\u0b2c\u0b3e\u0b07\u0b32|\u0b95\u0bc8\u0baa\u0bc7\u0b9a\u0bbf|\u0b85\u0bb2\u0bc8\u0baa\u0bc7\u0b9a\u0bbf|\u0c2e\u0c4a\u0c2c\u0c48\u0c32\u0c4d|"
    "\u0cae\u0cca\u0cac\u0cc8\u0cb2\u0ccd|\u0d2e\u0d4a\u0d2c\u0d48\u0d7d)\\s*(?:\u0928\u0902\\.?|\u0928\u0902\u092c\u0930|\u0915\u094d\u0930\u092e\u093e\u0902\u0915|no\\.?)?\\s*[:#-]?"
    "|(?:\u0918\u0930|\u0928\u093f\u0935\u093e\u0938|\u09ac\u09be\u09a1\u09bc\u09bf|\u0998\u09b0|\u0a98\u0ab0|\u0a18\u0a30|\u0b18\u0b30|\u0bb5\u0bc0\u0b9f\u0bc1|\u0c07\u0c32\u0c4d\u0c32\u0c41|\u0cae\u0ca8\u0cc6|\u0d35\u0d40\u0d1f\u0d4d)\\s*(?:\u0915\u093e|\u091a\u093e|\u091a\u0940|\u0928\u0902\\.?|\u092b\u093c\u094b\u0928|\u092b\u094b\u0928)?\\s*[:#-])\\s*$")


_F1I_PERSONAL = re.compile(
    r"(?i)(?:\b(?:personal|private|home|residence)\b\s*(?:(?:mobile|phone|tel|email|e-mail|whatsapp)\b\s*)?"
    r"(?:(?:no\.?|number)\s*)?|(?:निजी|व्यक्तिगत|घर|निवास)\s*(?:मोबाइल|फोन|फ़ोन|ईमेल|ई-मेल)?\s*)[:#-]?\s*$")


def _F1I_org_near(text, start, end):
    left, right = _F1P_window(text, start, end)
    ctx = _F1P_EMAILISH.sub(" ", left + " " + right)
    if _F1I_ORG_WORDS.search(ctx) or _F1P_ORG.search(ctx):
        return True
    return any(_F1P_ROLE_LOCAL.match(m.group(1)) or _F1I_ORG_DOMAIN.search(m.group(2))
               for m in _F1P_EMAIL.finditer(left + " " + right))


def _F1I_labelled(text, start):
    return bool(_F1I_PRIVATE.search(text[max(0, start - 30):start]))


def _f1_indic(text):
    # Indic digits read as 0-9; same length, so spans match the text. A text with none of those characters is its own key.
    key = text.translate(_F1I_DIGITS) if _F1I_INDIC_DIGIT.search(text) else text
    spans = []
    if "1800" in key or "1860" in key:           # speed: see _F1I_MOBILE_CORE
        for m in _F1I_TOLL_FREE.finditer(key):
            spans.append((m.start(), m.end(), None))
    taken = lambda s, e: any(a < e and s < b for a, b, _ in spans)
    if _F1I_MOBILE_CORE.search(key):
        for m in _F1I_MOBILE.finditer(key):
            if not taken(m.start(), m.end()):
                private = bool(_F1I_PERSONAL.search(text[max(0, m.start() - 50):m.start()])) or not _F1I_org_near(text, m.start(), m.end())
                spans.append((m.start(), m.end(), _F1P_PHONE_PH if private else None))
    if _F1I_LANDLINE_CORE.search(key):
        for m in _F1I_LANDLINE.finditer(key):
            if not taken(m.start(), m.end()):
                line = text[text.rfind("\n", 0, m.start()) + 1:m.start()]
                private = bool(_F1I_PERSONAL.search(text[max(0, m.start() - 50):m.start()])) or (
                    _F1I_labelled(text, m.start()) and not (_F1I_ORG_WORDS.search(line) or _F1P_ORG.search(line)))
                spans.append((m.start(), m.end(), _F1P_PHONE_PH if private else None))
    out, last = [], 0
    for s, e, tag in sorted(spans):
        if tag:
            out += [text[last:s], tag]
            last = e
    out = "".join(out) + text[last:]

    def email(m):
        local, domain = m.group(1), m.group(2)
        if _F1P_SAFE_DOMAIN.search(domain) or _F1P_ROLE_LOCAL.match(local) or _F1I_ORG_DOMAIN.search(domain):
            return m.group(0)
        if not _F1I_PERSONAL.search(m.string[max(0, m.start() - 50):m.start()]) and _F1I_org_near(m.string, m.start(), m.end()):
            return m.group(0)
        return _F1P_EMAIL_PH
    return _F1P_EMAIL.sub(email, out) if "@" in out else out      # speed: _F1P_EMAIL needs an "@"


def f1(doc):
    """F1: <PHONE>, <EMAIL>, <ADDRESS> for a private person. Drop when lines with such details hold most of the text."""
    text, lang = doc["text"], doc.get("lang_label")
    pack = str(doc.get("pack_id") or "")
    # Code packs use the generic tag "code"; choose their parser without changing row metadata.
    # Keep an explicit language tag (notably JavaScript versus TypeScript) when supplied.
    if lang == "code":
        lang = _F1_CODE_PACKS.get(pack, lang)
    if pack in _F1_EMAIL_ONLY:                  # cadj-commits: e-mail addresses only, never a drop
        new = _f1_emails_only(text)
        return ("fix" if new != text else "keep", new)
    if pack.startswith("ind-"):                 # Indic packs: any language tag
        new = _f1_indic(text)
        return ("fix" if new != text else "keep", new)
    if lang not in _F1_TREE and pack.startswith(_F1_PROSE):      # a code label keeps the tree path, whatever the pack
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
