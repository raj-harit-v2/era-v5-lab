"""Theorem 2: exact structural decode (proof.md section 6). Synthetic strings, CPU, a few seconds."""

import random

import numpy as np
import torch
from decode_theorems import THETA, decode_structural, decode_structural_batch, error_room

from forward import codes, expected_values

PS = (32, 64)
DTYPES = (torch.float32, torch.bfloat16)


def rand_bytes(rng, L):
    return bytes(rng.randrange(256) for _ in range(L))


def strings_for(P, rng, n=500):
    edge = [b"\x00", b"\xff", b"a", b"\x00" * P, b"\xff" * P, b" " * 31, b" " * 32, bytes(range(P))]
    return edge + [rand_bytes(rng, rng.randrange(1, P + 1)) for _ in range(n)]


def test_clean_codes_decode_exactly_in_fp32_and_bf16():
    rng = random.Random(0)
    for P in PS:
        strings = strings_for(P, rng)
        for dtype in DTYPES:
            got = decode_structural_batch(codes(strings, P, dtype), P)
            assert got == strings, (P, dtype)


def test_cut_off_8_lies_between_the_two_values_for_every_length():
    for P in PS:
        for L in range(1, P + 1):
            hi, lo = expected_values(L, P)
            assert lo < 0 < THETA < hi, (P, L, hi, lo)


def test_room_for_error_values():
    assert abs(error_room(32) - 7.9663) < 1e-3
    assert abs(error_room(64, 32) - 8.0078) < 1e-3
    assert error_room(64) > 7.96


def test_noise_inside_the_room_never_changes_the_answer():
    rng = random.Random(1)
    nrng = np.random.default_rng(1)
    for P in PS:
        strings = strings_for(P, rng, n=300)
        z = codes(strings, P).numpy().astype(np.float64)
        delta = 0.999 * error_room(P)
        noisy = z + nrng.uniform(-delta, delta, size=z.shape)
        assert decode_structural_batch(noisy, P) == strings, P
        hi, lo = z.max(1, keepdims=True), z.min(1, keepdims=True)
        worst = np.where(z == hi, hi - delta, lo + delta)  # every cell pushed towards the cut-off
        assert decode_structural_batch(worst, P) == strings, P


def test_a_push_just_outside_the_room_can_give_another_string():
    for P in PS:
        z = codes([b" " * 32], P).numpy().astype(np.float64)[0]
        z[0x20 * P + 31] = THETA - 0.01  # the last lit cell drops just below the cut-off
        assert decode_structural(z, P) == b" " * 31, P  # a different, valid string: the theorem promises nothing here


def test_invalid_patterns_are_reported():
    P = 32
    z = codes([b"abc"], P).numpy().astype(np.float64)[0]
    two_in_one_position = z.copy()
    two_in_one_position[ord("x") * P + 1] = 20.0
    assert decode_structural(two_in_one_position, P) is None
    gap = z.copy()
    gap[ord("b") * P + 1] = 0.0  # position 1 goes dark, position 2 stays lit
    assert decode_structural(gap, P) is None
    assert decode_structural(np.zeros(256 * P), P) == b""  # nothing above the cut-off: the empty string


def test_same_answer_for_any_batch_size_and_order():
    rng = random.Random(2)
    P = 32
    strings = strings_for(P, rng, n=200)
    batch = codes(strings, P)
    whole = decode_structural_batch(batch, P)
    assert [decode_structural(batch[k], P) for k in range(len(strings))] == whole
    perm = list(range(len(strings)))
    rng.shuffle(perm)
    shuffled = decode_structural_batch(batch[perm], P)
    assert [shuffled[perm.index(k)] for k in range(len(strings))] == whole
