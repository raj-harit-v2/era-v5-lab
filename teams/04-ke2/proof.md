# KE2 week 1: forward encode proof

Lemma 1, Lemma 2 and Theorem 1 for the Kronecker codec, with numerical checks.
Code: `src/proofs/` (`forward.py`, `proof_checks.py`). Tests: `tests/` (`test_lemma1.py`, `test_lemma2.py`, `test_theorem1.py`,
`test_proof_checks.py`). Real-tokenizer results: `results/proof_checks.json`. Run: `pytest teams/04-ke2/tests -q`
(needs the kronecker-embeddings package, see the end).

**Provenance.** The codec is the one in https://github.com/theschoolofai/kronecker-embeddings
(`kronecker_embeddings/codec.py`, V1 paper arXiv:2605.29459, section 3). The statements and proofs are
written for this lab. The paper states no lemmas. The statements are proposals and are open to change.
The cut rule used in Lemma 2 is the repository's own (`utf8_safe_truncate`). A variant that keeps the bytes of tokens that are not
valid UTF-8 is described as a possible fix in section 2.

## 0. Setup and notation

- P is 32 or 64 (`pos_dim`). The alphabet has 256 byte values, so a code has D = 256P entries.
- A token has raw bytes r (its real vocabulary bytes). The codec sees the cut string s = tau_P(r), with |s| = L <= P (tau_P is the repository cut rule, section 2).
  |s| is the number of bytes of s.
- Code of s = s_0 ... s_{L-1}, as in `kronecker_codec`:
  1. Make a vector x of length D with x[s_p * P + p] = 1/sqrt(L) for p = 0 .. L-1, and 0 elsewhere.
  2. z-normalise: z = (x - mean(x)) / (std(x) + eps), with the unbiased std and eps = 1e-6.
- Cell i of the vector is byte i div P at position i mod P.
- For the empty string (L = 0) x = 0, so z = 0.

## 1. Lemma 1: the codec is injective

**Statement.** Let s, s' be byte strings with |s| <= P and |s'| <= P. If code(s) = code(s'), then s = s'.
Also, the code of a non-empty string is never the all-zero code.

**Proof.** Take a non-empty s with L bytes, 1 <= L <= P. Then L < D.

1. The L lit cells are distinct, because cell s_p * P + p has remainder p when divided by P, so no two share a position.
   Exactly L entries of x are 1/sqrt(L) and D - L > 0 entries are 0.
2. mean(x) = m = sqrt(L)/D. The sum of squares of x is 1, so the unbiased variance is v = (1 - L/D) / (D - 1) > 0.
   Let sigma = sqrt(v) + eps > 0.
3. So z has exactly two values:
   high h = (1/sqrt(L) - m) / sigma on the lit cells, low u = -m / sigma on all other cells.
   Their difference is h - u = 1 / (sqrt(L) * sigma) > 0, so h > u. In particular z is not the zero vector.
4. The lit cells are the cells with value h, found as the cells above (h + u)/2. In each position p = 0 .. L-1 there is
   exactly one lit cell i, and the byte at p is i div P. The number of lit cells is L.
5. So s can be computed from z alone. If code(s) = code(s'), both strings are computed from the same vector, so s = s'.
6. The empty string gives z = 0 (section 0), and every non-empty string gives a non-zero z (step 3), so they never agree.
   Two non-empty strings of different length differ in the number of lit cells, so they are covered by step 5. QED

**Remark (floating point).** Rounding to bf16 never swaps h and u, because rounding is monotone. It could merge them only
if h - u were smaller than the bf16 spacing. Since sigma <= 1/sqrt(D - 1) + eps, h - u is at least 0.999 * sqrt((D - 1)/L),
which is at least 15.9 for both P = 32 and P = 64 (the eps term changes it by less than 0.02%). The spacing of bf16 at
values of that size is at most 0.5.

**Numerical checks** (`test_lemma1.py`):

| Check | Size | Result |
|---|---|---|
| exactly 2 distinct values, fp32 and bf16 | P = 32, 64; every L from 1 to P; 3 random strings each | pass |
| the two values equal the closed form h, u of step 3 (relative error 1e-3) | P = 32, 64; every L | pass |
| gap h - u after rounding to bf16 | P = 32, 64; every L | > 8 in all cases (the smallest seen earlier was 16.0) |
| bytes read back from the code equal the input, fp32 and bf16 | edge strings (`00`, `ff`, length P, all bytes) and 3,000 random strings per P | pass |
| empty string gives the zero code, no non-empty string does | 200 random strings per P | pass |
| distinct strings give distinct codes, fp32 and bf16 | at least 20,000 distinct strings per P, including near neighbours (one byte changed, two swapped, one added) | pass |

## 2. Lemma 2: the cut to P is safe and predictable

**The rule tau_P(r)** (the repository's `utf8_safe_truncate`):
1. If |r| <= P, return r.
2. Otherwise try c = P, P-1, P-2, P-3 in that order. Return r[0:c] for the first c where r[0:c] is valid UTF-8.
3. If none of the four is valid, return the empty string.

**Statement.** For every byte string r and P >= 4:
(a) tau_P(r) is a prefix of r.
(b) If |r| <= P then tau_P(r) = r.
(c) If |r| > P then tau_P(r) is valid UTF-8, and it is empty or has P - 3 to P bytes.
(d) If r is valid UTF-8, then tau_P(r) is valid UTF-8 and not empty, so no letter is split and a valid token is never cut to nothing.
(e) tau_P(tau_P(r)) = tau_P(r).
(f) If |r| > P and tau_P(r) is empty, then r is not valid UTF-8.

**Proof.** (a), (b), (c): we return all of r, or a valid prefix r[0:c] with c one of P, P-1, P-2, P-3, or the empty string. (e): the
result has length <= P, so rule 1 returns it unchanged. (f) is (d) read backwards.
(d): let r be valid UTF-8 with |r| > P. A prefix of a valid string is valid exactly when the cut falls between letters, that is,
when r[c] is not a continuation byte (a byte in 0x80 .. 0xBF). A letter has at most 4 bytes: a lead byte, then at most 3
continuation bytes. If r[P] is not a continuation byte, c = P is valid. Otherwise the letter that contains r[P] starts at some
q with P - 3 <= q < P, and r[q+1] .. r[P] are all continuation bytes; going down from P, the first position that is not a
continuation byte is q, so some c in P, P-1, P-2, P-3 is valid, and the first valid one is returned. QED

**Where it empties a token.** A token longer than P bytes that is not valid UTF-8 can have no valid prefix among the four, for
example one that starts with the tail byte of a letter. Then tau_P(r) is empty and the token gets the all-zero code, the same code
as every other such token and as the empty token. Example, P = 32, a 36-byte token (a stray tail byte `95`, twenty `a`, then the
Kannada letters ka, na, virama, na, da):

```
95 | 61 x20 | e0 b2 95 | e0 b2 a8 | e0 b3 8d | e0 b2 a8 | e0 b2 a1
```

The repository rule returns 0 bytes (no prefix is valid UTF-8, because every prefix starts with `95`).

This cannot happen inside the repository's own pipeline (`build_byte_buffer`): there the bytes come from `decode([id])`, which is
always valid UTF-8, so by (d) nothing is emptied. It can happen once the raw vocabulary bytes (the raw byte table) are fed to the
repository rule, because a raw token can be invalid UTF-8.

**Possible fix (proposal, not in the repository).** tau'_P(r): if |r| <= P return r; otherwise take the first c in P, P-1, P-2, P-3
where r[c] is not a continuation byte and return r[0:c]; if there is none, return r[0:P]. It keeps the bytes of tokens that are
not valid UTF-8 and never cuts a non-empty token to nothing: (a), (b), (c) with no empty case, and (e) hold, and tau'_P(r) =
tau_P(r) on valid UTF-8. On the 36-byte token above it returns 30 bytes (`95`, twenty `a`, ka, na, virama). Theorem 1 holds for
tau'_P in the same way, and the tests check both rules. Whether the KE2 code should keep or empty such tokens is a question for TSAI.

**Note on the real vocabulary.** BrahmicTokenizer-131K has no ordinary token longer than 32 bytes (longest: 32; special tokens: at most 20),
so for P = 32 and P = 64 neither rule cuts anything and tau_P(r) = r for every token (section 4). The lemma is still needed for
smaller P, for other tokenizers, and for the provisional tokenizer from G3 (due 28 Oct), whose longest token is not yet known.

**Numerical checks** (`test_lemma2.py`):

| Check | Size | Result |
|---|---|---|
| (a), (b), (c), (e) for both rules, on raw bytes, half of them continuation bytes | P = 32, 64; 5,000 strings each, lengths 0 to 199 | pass |
| (d): valid UTF-8 stays valid, is never emptied, and both rules agree with `utf8_safe_truncate` (Latin, accents, Kannada, Devanagari, CJK, emoji, ZWJ) | P = 32, 64; 5,000 strings each (more than 500 longer than P) | pass |
| (c) repository rule: a cut token is empty or valid UTF-8; more than 500 strings per P really hit the empty case; the proposed rule never returns empty for a non-empty token | P = 32, 64; 5,000 strings each | pass |
| the 36-byte example: repository rule returns 0 bytes, proposed rule returns 30 | one token, P = 32 | pass |

## 3. Theorem 1: the codec never causes a collision

**Statement.** Let r, r' be the byte strings that a table feeds to the codec for two tokens (the raw vocabulary bytes in the
raw byte table). Then code(tau_P(r)) = code(tau_P(r')) if and only if tau_P(r) = tau_P(r').

**Proof.** (if) The code is a function of the string. (only if) By Lemma 2 (b) and (c), both cut strings have at most P bytes
(the empty string is covered by Lemma 1, step 6), so Lemma 1 applies. QED. The same proof works for tau'_P.

**Scope.** The theorem is about the strings that a table feeds to the codec. It does not say what a given way of building the table
feeds. If the table is built with `decode([id])`, partial-letter tokens are fed as U+FFFD and collide (section 4). That is a
property of the table, not of the codec, and it is why the raw byte table uses the real vocabulary bytes.

**Corollary (causes).** Two different tokens share a code only if the strings fed to the codec become equal after the cut.
For a pair of tokens, with raw bytes r, r' and fed bytes f, f' (equal to r, r' in the raw byte table), the reason is
the first of these that applies, in this order (`pair_cause` in `forward.py`):

| Cause | Condition |
|---|---|
| `empty` | both fed strings are empty (empty tokens) |
| `cut_to_empty` | the cut string is empty but a fed string is not (a long token that is not valid UTF-8, repository rule only; Lemma 2) |
| `same_raw` | r = r' (duplicate surface forms, a special token with the text of an ordinary token, an agreed marker policy) |
| `bad_bytes_in` | r != r' but f = f' (for example U+FFFD from `decode([id])`; not possible in the raw byte table) |
| `truncation` | f != f' but tau_P(f) = tau_P(f') (at least one is longer than P, and they agree up to the cut) |

A group of more than two tokens that share a code can mix these causes, one per pair.

**Numerical checks** (`test_theorem1.py`), on a synthetic vocabulary of 1,717 tokens that contains every cause
(families that share a long start, runs of `-` of length 33 to 74, exact duplicates, `<s>` twice, partial letters with
U+FFFD bytes, long tokens that start with a stray tail byte, empty tokens). Run for both cut rules:

| Check | Result |
|---|---|
| the grouping of tokens by code equals the grouping by cut string, P = 32 and 64, fp32 and bf16 | pass |
| every pair of tokens that share a code gets one of the five causes; all five occur with the repository rule, and all but `cut_to_empty` with the proposed rule | pass |
| `pair_cause` on small hand-made cases | pass |

All 13 synthetic-data tests: `13 passed` (CPU, torch).

## 4. The real tokenizer, and what this does not cover

**BrahmicTokenizer-131K** (`tokenizer.json` sha256 `01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff`, 131,072 ids,
356 special tokens, normalizer null, no byte fallback). Raw bytes come from the vocabulary strings by inverting the GPT-2
byte-to-unicode map. The code is `src/proofs/proof_checks.py` (uses `forward.py`) and `tests/test_proof_checks.py`; run them as in section 7.
Every number below is in `results/proof_checks.json`. The tokenizer files are not in this repository.

| Table fed to the codec | P | distinct codes (of 131,072) | tokens that cannot be produced | pair causes |
|---|---|---|---|---|
| raw vocabulary bytes | 32 and 64, fp32 and bf16 | 131,072 | 0 | none |
| `decode([id])` bytes from the repo's `token_id_to_bytes` and the real `tokenizers` decoder | 32 and 64, fp32 and bf16 | 129,931 | 1,141 in 10 groups (largest 658, 396, 82) | all `bad_bytes_in` |

- Groups by code equal groups by cut string in all four cases, as Theorem 1 says. Every pair in the 10 groups has the cause `bad_bytes_in`;
  `empty`, `cut_to_empty`, `same_raw` and `truncation` do not occur.
- The longest ordinary token is 32 bytes (none over 32), so P = 32 and P = 64 give identical results and no token is cut.
- 1,306 tokens (1.0%) are not valid UTF-8 (they contain part of a letter). 197 of them start with a stray continuation byte. Only 16
  contain the Kannada lead bytes `E0 B2` / `E0 B3`. The real U+FFFD token is id 99666.
- Hash of the raw table (for each id: the id as 4 bytes, the length as 2 bytes, then the bytes): `18c7f6a382fd6668ec73f56e589fbfbc13fec7c6ad5403a2d79ba6198ecc0d3c`.

**Not covered.**
- **The decoder is `tokenizers` 0.23.1,** the Rust engine behind HF fast tokenizers, called through a thin adapter (only the four named specials take the literal-text path). `transformers` itself was not run. The bytes fed equal a plain model (invalid bytes replaced by U+FFFD) for all 131,072 ids. The cut rule in these runs is the repository's; the proposed rule gives the same groups here.
- **Lemma 2's cut branch** (both rules) is checked only on random and synthetic strings, since no real token is longer than 32 bytes.
- **Special tokens** are included here as their literal text. The final policy (the G10 list, due 31 Oct) can change what is fed to the
  codec, but not the theorem. Whether to keep `<s>` text and the special token apart is a policy decision.
- **Normalisation.** NFC or NFKC changes the bytes, so it changes the codes. The tokenizer has no normalizer, so this happens in the data pipeline. The proof starts from the bytes.
- **Exact arithmetic.** The proof is exact. The checks cover fp32 and bf16 and show that the lit and unlit values stay apart.
- **Decoding from a predicted vector** (noisy input, margins) is covered by Theorems 2 and 3 in sections 5 and 6. A rejection
  threshold (tau) is not covered anywhere in this document.

## 5. Theorem 2: exact structural decode (week 2)

Section 4 lists decoding from a predicted vector as not covered by the week-1 proof. This section and section 6 now
cover it (noisy input and margins). The choice of tau is still not covered.

**Decoder.** For a vector q of length D = 256P and a cut-off theta, let C = {cells i with q_i > theta}.

- If C is empty, the decoder returns the empty string.
- If C has exactly one cell in each position 0 .. |C|-1 and none elsewhere, the decoder returns the string s with
  s_p = i div P for the cell i of position p (as in Lemma 1, step 4).
- Otherwise it returns **invalid**.

A returned string is looked up in the raw byte table. The result is the one token ID with that string, or **not a token**.
Code: `decode_structural` and `decode_structural_batch` in `src/proofs/decode_theorems.py`.

**Statement.** Let t be a token whose cut string s = tau_P(r) has 1 <= L <= P bytes, and let z = code(s).

(a) **Clean codes.** With theta = 8, the decoder returns s from z, and the lookup returns t. This holds in exact
    arithmetic, fp32 and bf16.
(b) **Room for error.** If every entry of q is within delta of z, |q_i - z_i| < delta for all i, with
    delta = min(h - theta, theta - u), the decoder still returns s and the lookup t. For theta = 8,
    delta = 7.966 for every string of at most P bytes (P = 32 and 64). For the real tokens (L <= 32):
    delta = 7.966 at P = 32 and 8.008 at P = 64 (`error_room`).
(c) **The same answer everywhere.** The decoder uses only comparisons with theta and whole-number arithmetic
    (div, mod, a table lookup). So the same input array gives the same output on any machine, in any batch size and
    in any order. No floating-point sum is involved.

**Proof.** (a) By Lemma 1, z has the value h on the L lit cells and u on the others. For 1 <= L <= P, the smallest h is
15.966 (at L = P) and -0.063 < u < 0 (Lemma 1, step 3, evaluated with `code_values` for every L). So u < 0 < theta < h. bf16 rounding is monotone, so it keeps
h above 15.87 and u below 0 (Lemma 1 remark). So C is exactly the lit cells, and Lemma 1 step 4 reads back s. The raw
byte table gives 131,072 distinct strings (section 4), so exactly one ID has the string s.
(b) If |q_i - z_i| < delta, a lit cell has q_i > h - delta >= theta, and any other cell has
q_i < u + delta <= theta. So C is again exactly the lit cells.
(c) Each output is a function of the boolean values q_i > theta, which IEEE 754 computes exactly. QED

**What it does not say.** Outside the bound in (b), the decoder can return invalid, not a token, or **a different
token**: noise that happens to form another token's pattern. The theorem promises nothing there. Part (c) is about
the decoder only. Whether the vectors fed to it are identical across runs is the determinism task. The fixed cut-off
of 8 and its room for error first appear in `proof_explained.md` (figure 6); this theorem states them formally and
adds the ID lookup and (c).
Structured noise is the realistic case and is outside (b): a mixture q = (1 - a) code(t) + a code(t') with a = 0.3
already lifts a cell of t' above the cut-off when t' is shorter than 12 bytes (0.3 h(L') > 8 for L' <= 11), while
cos(q, code(t)) is still about 0.988, so the decoder returns invalid or, for an extension rival, t'. The structural
decoder is therefore not for predicted vectors: use nearest-code cosine (Theorem 3) and report the margin
(`min_margin.md`).

**Numerical checks** (`results/decode_checks.json`, `src/proofs/decode_checks.py`; tests `test_theorem2.py`):

| Check | P = 32 | P = 64 |
|---|---|---|
| clean code of every token decodes to its own ID, fp32 and bf16 | 131,072 / 131,072 | 131,072 / 131,072 |
| uniform noise of up to 0.999 delta, 2,000 tokens | all own ID | all own ID |
| every cell pushed 0.999 delta towards theta, 2,000 tokens | all own ID | all own ID |
| one lit cell of 32 spaces (ID 50346) moved just below theta | decodes as 31 spaces (ID 83647) | the same |
| one at a time, as a batch, shuffled | identical | identical |

The last-but-one row is an example for "what it does not say": at P = 32 a push of 7.976, just past delta, gives another
token (at P = 64 the lit value is higher and the same cell has to move 14.61).

## 6. Theorem 3: nearest-code cosine (week 2)

**Statement.** For non-empty strings a and b with La and Lb bytes (at most P), let
m = the number of positions p < min(La, Lb) with a_p = b_p, and D = 256P. Then

    cos(code(a), code(b)) = ( m / sqrt(La * Lb)  -  sqrt(La * Lb) / D ) / sqrt( (1 - La/D) * (1 - Lb/D) )

The value does not depend on eps (`closed_form_cosine`). Consequences:

(a) cos(code(a), code(b)) = 1 if and only if a = b.
(b) **Clean codes decode exactly.** Nearest-code decoding by cosine over the raw byte table returns t from code(t),
    with no tie, for every token t.
(c) **Worst case.** Over all pairs of different strings of at most 32 bytes (the longest real token), the largest
    cosine is c* = 0.984191 at P = 32 (0.984221 at P = 64). It is reached when one string is the other minus its
    last byte, at lengths 31 and 32 (`worst_case_cosine`). BrahmicTokenizer-131K has exactly one such pair:
    31 spaces (ID 83647) and 32 spaces (ID 50346). So the smallest decode margin over the vocabulary is
    1 - c* = 0.015809 at P = 32 (0.015779 at P = 64).
(d) **Guarantee for a noisy vector.** For any non-zero q with cos(q, code(t)) > sqrt((1 + c*)/2) = 0.99604
    (0.99605 at P = 64), nearest-code decoding returns t (`guarantee_cosine`).

**Proof.** Write x_a for the vector before z-normalisation (La cells of 1/sqrt(La)) and mu_a = sqrt(La)/D for its mean.
code(a) = (x_a - mu_a)/sigma_a with sigma_a > 0. A positive scale does not change a cosine, so eps cancels and
cos(code(a), code(b)) = cos(x_a - mu_a, x_b - mu_b).

- The lit cells of a and b coincide exactly where a_p = b_p, so <x_a, x_b> = m / sqrt(La * Lb).
- The sum of x_a is sqrt(La), so <x_a - mu_a, x_b - mu_b> = <x_a, x_b> - sqrt(La * Lb)/D.
- |x_a - mu_a|^2 = 1 - La/D. Dividing gives the formula.

(a) Equality in Cauchy-Schwarz needs x_a - mu_a = c (x_b - mu_b) with c > 0. More than D - La - Lb > 0 cells are 0 in
    both, and on those cells the equation gives mu_a = c mu_b. So x_a = c x_b, the lit cells are the same,
    La = Lb, c = 1, and a = b by Lemma 1.
(b) The raw byte table has 131,072 distinct strings (section 4), so by (a) every other token has cosine < 1 with
    code(t).
(c) The formula depends only on (La, Lb, m) with 1 <= La <= Lb <= 32 and 0 <= m <= La (m < La when La = Lb), and it
    grows with m. These are finitely many cases; all were enumerated, and the maximum is at (31, 32, 31).
(d) Let phi* = arccos c*, the smallest angle between two different codes. If the angle from q to code(t) is below
    phi*/2, then for every other token t' the angle from q to code(t') is above phi* - phi*/2 = phi*/2, by the
    triangle inequality for angles. So code(t) is strictly closest. cos(phi*/2) = sqrt((1 + c*)/2). QED

**What it does not say.** (d) is a sufficient condition. A vector below 0.99604 can still decode correctly; the
condition only rules out the worst case. Whether a trained model's output vectors come that close is not a question
about the codec: static decodability is not contextual decodability. The 4,096-sample minimum margin in
`results/decode_ref/summary.json` (0.0318) did not include the 31/32-space pair; (c) gives the full-vocabulary
minimum. Both theorems are for the V1 codec (`kronecker-embeddings`), not for other codecs.

**Numerical checks** (`results/decode_checks.json`; tests `test_theorem3.py`). 10,010 real token pairs of
BrahmicTokenizer-131K, seed 0: 2,500 random, 2,500 prefix (one token is the other minus its last byte), 2,500 of the
same length differing in one byte, 2,500 nearest neighbours (a sampled token and its closest other code over the whole
vocabulary), and 10 hand-picked (space runs of 30, 31 and 32 bytes, the longest and shortest tokens).

| Check | P = 32 | P = 64 |
|---|---|---|
| formula vs the codec's cosine, max abs error, float64 / float32 / bfloat16 | 1.4e-15 / 1.3e-15 / 4.6e-8 | 1.7e-15 / 1.6e-15 / 2.2e-8 |
| largest cosine in any group, and the bound c* | 0.984191 (edge pairs) <= c* | 0.984221 <= c* |
| largest cosine among the 2,500 nearest neighbours | 0.976949 | 0.976979 |
| pairs of different tokens with cosine 1 | 0 | 0 |
| cosine of 31 vs 32 spaces from the codec | 0.984191 = c* | 0.984221 = c* |
| clean codes of 502 tokens decoded over the whole vocabulary | all own ID, min margin 0.015809 = 1 - c* | all own ID, min margin 0.015779 = 1 - c* |
| q between 32 and 31 spaces, just above the guarantee (cosine to 32 spaces) | 0.996056: decodes 32 spaces | 0.996063: decodes 32 spaces |
| the same, just below the guarantee | 0.996024: decodes 31 spaces | 0.996032: decodes 31 spaces |
| 500 random tokens with noise at cosine 0.99614 (P = 64: 0.99615) to their code | all own ID | all own ID |

The two "q between" rows show that (d) is tight: just past the guarantee, the worst pair swaps.

## 7. Run it

The commands use bash `export`; on Windows cmd use `set NAME=value`.

```
git clone https://github.com/theschoolofai/kronecker-embeddings
pip install torch pytest
# either pip install -e kronecker-embeddings, or point the tests at its src folder:
export KRONECKER_SRC=<path to kronecker-embeddings>/src
pytest teams/04-ke2/tests -q
```

`tests/conftest.py` and the scripts also find a folder named `kronecker-embeddings` next to the lab repository (see `src/ke2/upstream.py`).

On the real tokenizer (needs `pip install tokenizers`; download `tokenizer.json`, `tokenizer_config.json` and
`special_tokens_map.json` from https://huggingface.co/theschoolofai/BrahmicTokenizer-131K into a folder outside this repository):

```
export BRAHMIC_TOKENIZER_DIR=<that folder>
pytest teams/04-ke2/tests/test_proof_checks.py -q          # skipped when the variable is not set
python teams/04-ke2/src/proofs/proof_checks.py $BRAHMIC_TOKENIZER_DIR       # rewrites results/proof_checks.json
```

Section 4 gives the expected numbers. With the tokenizer all 16 proof tests pass (about 2.5 minutes on CPU), including one that
compares `results/proof_checks.json` with a fresh run; without it, 13 pass and 3 are skipped.

### Week-2 checks

On the real tokenizer, with the same variables:

```
python teams/04-ke2/src/proofs/decode_checks.py      # rewrites results/decode_checks.json (about 4 minutes on a laptop CPU)
pytest teams/04-ke2/tests/test_theorem2.py teams/04-ke2/tests/test_theorem3.py -q
```

Code: `src/proofs/decode_theorems.py`, `src/proofs/decode_checks.py`. Tests: `tests/test_theorem2.py`, `tests/test_theorem3.py`
(14 tests, a few seconds; the 2 that read `results/decode_checks.json` are skipped without the tokenizer).
