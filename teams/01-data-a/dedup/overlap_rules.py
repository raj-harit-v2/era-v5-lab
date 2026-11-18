"""H1/H2 eligibility for overlap measurement; never removes documents.

Code uses Pygments' built-in language lexers (https://pygments.org/docs/api/).
Raw word-Jaccard measurements remain separate from the eligible duplicate pairs.
"""
from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import re

from h1_sha256 import h1_key
from jaccard_matrix import gram_hashes

CODE_LEXERS = {"code-cpp": "cpp", "code-go": "go", "code-java": "java",
               "code-js-ts": "typescript", "code-python": "python", "code-rust": "rust"}
THRESHOLDS = {"prose": 0.80, "code": 0.85, "math": 0.90}
NUMBERS = re.compile(r"[+\-−]?(?:\d+(?:[.,]\d+)*|\.\d+)(?:[eE][+-]?\d+)?")


def domain(pack):
    if pack.startswith("code-"):
        if pack not in CODE_LEXERS:
            raise ValueError(f"no code lexer configured for {pack}")
        return "code"
    if pack.startswith("math-"):
        return "math"
    return "prose"


@lru_cache(maxsize=None)
def lexer(pack):
    from pygments.lexers import get_lexer_by_name
    return get_lexer_by_name(CODE_LEXERS[pack], stripnl=False, ensurenl=False)


def code_shingles(text, pack):
    """Token 5-grams; comments/licence comment headers excluded, strings/preprocessor kept.

    Case and token values are preserved. Minimum length counts nonblank lines after comment removal.
    Whitespace tokens are ignored; lexer token boundaries define the token sequence.
    """
    from pygments import lex
    from pygments.token import Comment, String
    tokens, lines = [], []
    for kind, value in lex(text, lexer(pack)):
        # Preprocessor directives are meaningful code, although Pygments puts them under Comment.
        comment = kind in Comment and kind not in Comment.Preproc and kind not in Comment.PreprocFile
        licence_docstring = (not tokens and kind in String.Doc
                             and re.search(r"copyright|licen[cs]e|SPDX", value, re.I))
        if comment or licence_docstring:
            lines.append("\n" * value.count("\n"))
            continue
        lines.append(value)
        if value.strip():
            tokens.append(value)
    # Hashing is bulk; the Pygments iterator above still needs Python filtering to preserve v1 token semantics.
    return gram_hashes(tokens, 5), sum(bool(line.strip()) for line in "".join(lines).splitlines())


def gram_set(blob):
    """Decode fixed-width digests in NumPy; preserve all eight bytes, including trailing NULs."""
    import numpy as np
    return set(np.frombuffer(blob, dtype="V8").tolist())


def code_scores(code, block):
    """Exact all-pair code Jaccard, independently of the raw-word reporting floor."""
    import numpy as np
    from scipy import sparse
    ids = sorted(i for i, (blob, lines) in code.items() if lines >= 20 and blob)
    if len(ids) < 2:
        return
    sizes = np.array([len(code[i][0]) // 8 for i in ids], dtype=np.int64)
    hashes = np.frombuffer(b"".join(code[i][0] for i in ids), dtype=np.int64)
    _, cols = np.unique(hashes, return_inverse=True)
    rows = np.repeat(np.arange(len(ids)), sizes)
    X = sparse.csr_matrix((np.ones(len(cols), np.int32), (rows, cols)))
    XT = X.T.tocsr()
    del hashes, cols, rows
    for lo in range(0, len(ids), block):
        P = (X[lo:lo + block] @ XT).tocoo()
        a, b = P.row.astype(np.int64) + lo, P.col.astype(np.int64)
        mask = b > a
        a, b, inter = a[mask], b[mask], P.data[mask].astype(np.int64)
        score = inter / (sizes[a] + sizes[b] - inter)
        keep = score >= 0.85
        a, b, score = a[keep], b[keep], score[keep]
        # Emit in (row_a, row_b) order. The sparse product's column order follows the 5-gram hash values, so without
        # this the order of the rows in overlap_matches.csv would change whenever the hashing changes, with the same
        # pairs and scores.
        order = np.lexsort((b, a))
        for x, y, s in zip(a[order], b[order], score[order]):
            yield ids[x], ids[y], float(s)


def qualifying_pairs(parts, docs, I, J, S, exact, read_file, block):
    """Yield row_a, row_b, rule, word_jaccard, code_jaccard.

    Mixed-domain H2 pairs must meet BOTH domains' conditions on BOTH documents.
    For mixed code/text pairs, lex both texts with the code member's language lexer.
    Code/code pairs use each member's own language lexer. H1 bypasses H2 length guards.
    """
    domains = [domain(d[0]) for d in docs]
    candidates, wanted, needed_lexers = [], set(), defaultdict(set)
    for x, y, score, is_exact in zip(I, J, S, exact):
        a, b = int(x), int(y)
        if is_exact:
            yield a, b, "H1", float(score), ""
            continue
        types = {domains[a], domains[b]}
        if types == {"code"}:
            continue  # Independent token-Jaccard pass below also finds low-word-Jaccard copies.
        threshold = max(THRESHOLDS[t] for t in types if t != "code")
        if score < threshold or ("prose" in types and min(docs[a][5], docs[b][5]) < 50):
            continue
        candidates.append((a, b, float(score)))
        if types & {"math", "code"}:
            wanted.update((a, b))
        if "code" in types:
            code_pack = docs[a][0] if domains[a] == "code" else docs[b][0]
            needed_lexers[a].add(code_pack)
            needed_lexers[b].add(code_pack)

    # Re-read selected rows for math guards/mixed code views, plus all code rows for code/code detection.
    # No document text is retained or written to the returned artifacts.
    numbers, code, mixed = {}, {}, {}
    selected = defaultdict(dict)
    for i, d in enumerate(docs):
        if i in wanted or domains[i] == "code":
            selected[d[1], d[2]][d[3]] = i
    seen = 0
    for split, part, path in parts:
        rows = selected.get((split, part), {})
        if not rows:
            continue
        for row, pack, doc_id, text in read_file(path):
            if row not in rows:
                continue
            i = rows[row]
            seen += 1
            if (pack, split, part, row, doc_id) != (*docs[i][:4], docs[i][4]):
                raise ValueError("input rows changed between overlap passes")
            text = text or ""
            key = h1_key(text)
            if hashlib.sha256(key.encode("utf-8")).hexdigest() != docs[i][7]:
                raise ValueError("input text changed between overlap passes")
            if i in wanted:
                numbers[i] = Counter(NUMBERS.findall(key))
            if domains[i] == "code":
                code[i] = code_shingles(text, pack)
            for code_pack in needed_lexers.get(i, ()):
                mixed[i, code_pack] = code[i] if pack == code_pack else code_shingles(text, code_pack)
    if seen != sum(map(len, selected.values())):
        raise ValueError("input row count changed between overlap passes")

    for a, b, score in candidates:
        types = {domains[a], domains[b]}
        if "math" in types and numbers[a] != numbers[b]:
            continue
        code_score = ""
        if "code" in types:
            pack = docs[a][0] if domains[a] == "code" else docs[b][0]
            ba, la = mixed[a, pack]
            bb, lb = mixed[b, pack]
            if min(la, lb) < 20:
                continue
            ga, gb = gram_set(ba), gram_set(bb)
            code_score = len(ga & gb) / len(ga | gb) if ga or gb else 0.0
            if code_score < THRESHOLDS["code"]:
                continue
        yield a, b, "H2", score, code_score
    del mixed, numbers, candidates
    for a, b, score in code_scores(code, block):
        if docs[a][7] != docs[b][7]:  # H1 pairs have already been emitted once.
            yield a, b, "H2", "", score
