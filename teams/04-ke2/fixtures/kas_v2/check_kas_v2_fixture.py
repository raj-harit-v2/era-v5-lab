"""Check an implementation of the KE2 input embedding and KAS head against the Team 4 fixture, with numpy only.

    python teams/04-ke2/fixtures/kas_v2/check_kas_v2_fixture.py                       # self-check: the equations below vs the fixture
    python teams/04-ke2/fixtures/kas_v2/check_kas_v2_fixture.py --p1536-table PATH    # also fingerprint the full 131,072-id code table

The fixture (``kas_v2_fixture.npz`` + ``kas_v2_fixture.json``) was produced by the pinned reference (ke2-head 81cf1c0,
arm ``a10_kas_tokdrop``) at the chosen configuration, d_c = 64, L_max = 32, D = 2,048, on 48 real p1536 tokens.  The
functions below are the integration contract written out as code.  To test your own module, replace the two
``reference_*`` calls in ``main`` with calls into it (or import these functions in your test and compare), keeping the
tolerances in the JSON: float64 within 1e-10 absolute, float32 within 1e-5 of each row's largest |logit|.

Shapes and layouts (fixture order = the order of ``ids``):
  G (256, 64)        byte codebook, unit-norm rows: 8 Walsh bit columns (sign of G[b, j] for j < 8 gives bit j of b)
                     then 56 seeded Hadamard columns.  Phi (32, 32) orthogonal, Phi @ Phi.T = I.
  M_pos (V, 64, 32)  M_pos[v][:, p] = G[b_p] / sqrt(L_v) for p < L_v, zero columns for p >= L_v (padding = zeros)
  K (V, 2048)        K_v = (M_pos[v] @ Phi).reshape(-1): row-major over (c, k).  Unit norm.  No z-normalisation.
  W_proj (2048, 32)  E_v = K_v @ W_proj.                       init: randn * 2048**-0.5
  W_out (32, 2048)   S_n = (h_n @ W_out).reshape(64, 32), position domain (c, p); Phi is NOT applied on the head side.
                                                               init: randn * 2048**-0.5
  beta (33,)         per token *length* 0..32.                 init: ones
  unigram (V,)       per token.                                init: zeros, then centred log((count+1)/(N+V))
  tok_u (V, 64)      per-token rows.                           init: randn * 0.02 * 64**-0.5
  tok_c (64, 32)     context map.                              init: randn * 32**-0.5
  logits[n, v] = beta[L_v] * <M_pos[v], S_n>  +  unigram[v]  +  (h_n @ tok_c.T) @ tok_u[v]
  training only:     tok_u rows multiplied by keep[v] / (1 - 0.05), keep ~ Bernoulli(0.95) drawn on every head forward
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NPZ, META = HERE / "kas_v2_fixture.npz", HERE / "kas_v2_fixture.json"
D_C, L_MAX, TOK_DROPOUT = 64, 32, 0.05


# ------------------------------------------------------------------ the contract, as equations

def reference_positions(G: np.ndarray, rows: list[bytes], L_max: int = L_MAX) -> np.ndarray:
    """(V, d_c, L_max): byte codes placed at their positions, scaled by 1/sqrt(L); zero padding."""
    M = np.zeros((len(rows), G.shape[1], L_max))
    for i, r in enumerate(rows):
        r = r[:L_max]
        for p, b in enumerate(r):
            M[i, :, p] = G[b] / np.sqrt(len(r))
    return M


def reference_codes(G: np.ndarray, Phi: np.ndarray, rows: list[bytes]) -> np.ndarray:
    """(V, D): K_v = vec(M_pos[v] @ Phi)."""
    M = reference_positions(G, rows, Phi.shape[0])
    return (M @ Phi).reshape(len(rows), -1)


def reference_embedding(K: np.ndarray, W_proj: np.ndarray) -> np.ndarray:
    return K @ W_proj


def reference_logits(h, M_pos, lengths, W_out, beta, unigram, tok_u, tok_c, keep=None, p=TOK_DROPOUT):
    """(N, V) logits.  ``keep`` (V,) 0/1 applies the training-time row dropout exactly as the reference does."""
    N = h.shape[0]
    S = (h @ W_out).reshape(N, M_pos.shape[1], M_pos.shape[2])
    byte_score = np.einsum("vcp,ncp->nv", M_pos, S)
    U = tok_u if keep is None else tok_u * keep[:, None] / (1.0 - p)
    return beta[lengths][None, :] * byte_score + unigram[None, :] + (h @ tok_c.T) @ U.T


def bf16_bits(K32: np.ndarray) -> np.ndarray:
    u = np.ascontiguousarray(K32, dtype=np.float32).view(np.uint32).astype(np.uint64)
    return ((u + 0x7FFF + ((u >> 16) & 1)) >> 16).astype(np.uint16)


def fingerprint_table(G, Phi, bytes_, lengths, chunk=4096):
    """sha256 of the fp32 code table and of its bf16 bit patterns, row-major, original id order."""
    h32, hbf = hashlib.sha256(), hashlib.sha256()
    for lo in range(0, len(lengths), chunk):
        rows = [bytes_[i, : lengths[i]].tobytes() for i in range(lo, min(lo + chunk, len(lengths)))]
        K32 = reference_codes(G, Phi, rows).astype(np.float32)
        h32.update(np.ascontiguousarray(K32).tobytes())
        hbf.update(np.ascontiguousarray(bf16_bits(K32)).tobytes())
    return h32.hexdigest(), hbf.hexdigest()


# ------------------------------------------------------------------ checks

def run_checks(z, meta, p1536_table: Path | None = None) -> dict:
    tol64, tol32 = meta["tolerances"]["float64_abs"], meta["tolerances"]["float32_rel_to_row_max"]
    rows = [z["bytes"][i, : z["lengths"][i]].tobytes() for i in range(len(z["ids"]))]
    assert [r.hex() for r in rows] == meta["bytes_hex"], "fixture bytes disagree with the JSON"
    G, Phi = z["G"], z["Phi"]
    out = {
        "G_rows_unit_norm": float(np.abs(np.linalg.norm(G, axis=1) - 1).max()),
        "G_bit_columns_decode_bytes": bool(all((G[b, :8] < 0).astype(int) @ (1 << np.arange(8)) == b for b in range(256))),
        "Phi_orthogonal": float(np.abs(Phi @ Phi.T - np.eye(L_MAX)).max()),
    }
    M = reference_positions(G, rows)
    K = reference_codes(G, Phi, rows)
    out["M_pos_abs"] = float(np.abs(M - z["M_pos"]).max())
    out["K_abs"] = float(np.abs(K - z["K"]).max())
    out["K_unit_norm"] = float(np.abs(np.linalg.norm(K, axis=1) - 1).max())
    out["E_abs"] = float(np.abs(reference_embedding(K, z["W_proj"]) - z["E"]).max())
    args = (z["h"], M, z["lengths"], z["W_out"], z["beta"], z["unigram"], z["tok_u"], z["tok_c"])
    logits = reference_logits(*args)
    out["logits_float64_abs"] = float(np.abs(logits - z["logits"]).max())
    row_max = np.abs(z["logits"]).max(axis=1, keepdims=True)
    out["logits_f32_rel_to_row_max"] = float((np.abs(z["logits_f32"] - z["logits"]) / row_max).max())
    out["logits_dropped_abs"] = float(np.abs(reference_logits(*args, keep=z["keep"]) - z["logits_dropped"]).max())
    out["pass"] = (
        out["G_bit_columns_decode_bytes"] and out["Phi_orthogonal"] < 1e-12
        and out["M_pos_abs"] < tol64 and out["K_abs"] < tol64 and out["E_abs"] < tol64
        and out["logits_float64_abs"] < tol64 and out["logits_f32_rel_to_row_max"] < tol32 and out["logits_dropped_abs"] < tol64
    )
    if p1536_table is not None:
        t = np.load(p1536_table, allow_pickle=False)
        assert str(t["tokenizer_sha256"]) == meta["tokenizer_sha256"], "not the frozen p1536 table"
        sha32, shabf = fingerprint_table(G, Phi, t["bytes"], t["lengths"].astype(np.int64))
        out["p1536_codes_fp32_sha256_matches"] = sha32 == meta["p1536_codes_fp32_sha256"]
        out["p1536_codes_bf16_sha256_matches"] = shabf == meta["p1536_codes_bf16_sha256"]
        out["pass"] = out["pass"] and out["p1536_codes_fp32_sha256_matches"] and out["p1536_codes_bf16_sha256_matches"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--p1536-table", type=Path, default=None, help="raw_table_P32.npz: also check the full-table fingerprints")
    a = ap.parse_args(argv)
    meta = json.loads(META.read_text(encoding="utf-8"))
    assert hashlib.sha256(NPZ.read_bytes()).hexdigest() == meta["npz_sha256"], "kas_v2_fixture.npz does not match its JSON"
    z = np.load(NPZ, allow_pickle=False)
    out = run_checks(z, meta, a.p1536_table)
    print(json.dumps(out, indent=1))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
