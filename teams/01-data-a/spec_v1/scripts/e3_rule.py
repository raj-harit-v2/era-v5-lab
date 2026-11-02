import math
import re

PLACEHOLDER = "EXAMPLE_SECRET"
# well-known formats: the format itself is the proof, whatever the variable is called
KNOWN = [re.compile(p) for p in (
    r"\bAIza[0-9A-Za-z_\-]{35}\b",                                   # Google API key
    r"\bAKIA[0-9A-Z]{16}\b",                                         # AWS access key
    r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",                               # GitHub token
    r"\bgithub_pat_[A-Za-z0-9_]{40,}\b",                             # GitHub fine-grained token
    r"\bsk-[A-Za-z0-9_\-]{20,}\b",                                   # sk- API key
    r"\b[rs]k_live_[0-9A-Za-z]{16,}\b",                              # Stripe live key
    r"\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}\b",             # SendGrid key
    r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b",                            # Slack token
    r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b",  # JWT
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
)]
# a secret-like name, an optional type, an assignment, then a quoted literal
ASSIGNED = re.compile(
    r"""(?ix)
    (?P<head>
      \b[\w\-]*(?:secret|token|api[_\-]?key|app[_\-]?key|auth[_\-]?key|access[_\-]?key|client[_\-]?key|private[_\-]?key|passw(?:or)?d|pwd|\bkey)[\w\-]*
      ["']?
      (?:\s*:\s*&?(?:'\w+\s+)?[\w<>\[\]]{1,20})?   # Rust and TypeScript types: SECRET: &'static str = "..."
      \s*(?::=|=>|=|:)\s*
      (?P<quote>["'`])
    )
    (?P<value>[^"'`\s\\]{16,200})
    (?P=quote)
    """)
SDK_KEY = re.compile(r"""(?P<head>\bnew\s+Pusher\(\s*(?P<quote>["'`]))[0-9a-fA-F]{16,}(?P=quote)""")  # a key passed by position
DUMMY = re.compile(r"(?i)example|sample|dummy|test|fake|mock|placeholder|changeme|change_me|your|xxxx|0000|1234|abcd|secret|password|token|<|>|\$\{|\{\{|%s")


def _entropy(v):
    n = len(v)
    return -sum(c / n * math.log2(c / n) for c in (v.count(ch) for ch in set(v)))


def _looks_random(v):
    """A real key is a run of mixed letters and digits, not a word, an identifier, a path, a version or a dummy."""
    if DUMMY.search(v) or "." in v or v.count("/") > 2:
        return False
    if not (re.search(r"[0-9]", v) and re.search(r"[A-Za-z]", v)):  # enum names and plain words have no digits
        return False
    if sum(ch.isdigit() for ch in v) < 0.15 * len(v):                # user_profile_settings_v2
        return False
    return _entropy(v) >= 3.0


def medicine_e3(text):
    new = text
    for rx in KNOWN:
        new = rx.sub(PLACEHOLDER, new)
    new = SDK_KEY.sub(lambda m: m.group("head") + PLACEHOLDER + m.group("quote"), new)
    new = ASSIGNED.sub(lambda m: m.group("head") + PLACEHOLDER + m.group("quote") if _looks_random(m.group("value")) else m.group(0), new)
    return new
