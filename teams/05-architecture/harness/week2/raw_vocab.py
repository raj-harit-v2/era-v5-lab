"""Strict raw tokenizer bytes, matching Team 4's public byte-table contract.

ByteLevel pieces are byte encodings, not standalone Unicode text. In particular,
decoding a single token can replace an incomplete UTF-8 sequence with U+FFFD.
Added tokens instead use their literal UTF-8 content, including special tokens.
"""


class VocabHoleError(ValueError):
    """A vocabulary ID is absent or has no bytes; never substitute an empty row."""


def raw_token_bytes(spec, vocab_size, max_bytes=32):
    """Return exact bytes in ID order without calling tokenizer.decode().

    The frozen p1536 tokenizer uses a ByteLevel BPE vocabulary. The inverse
    alphabet and added-token precedence follow teams/04-ke2/src/ke2/tokenizer.py.
    A missing or empty token raises VocabHoleError, as in Team 4's strict builder.
    Overlength tokens fail rather than being truncated to the codec's limit.
    """
    alphabet = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    chars = alphabet.copy()
    extra = 0
    for byte in range(256):
        if byte not in alphabet:
            alphabet.append(byte)
            chars.append(256 + extra)
            extra += 1
    inverse = {chr(char): byte for byte, char in zip(alphabet, chars)}
    pieces = {tid: piece for piece, tid in spec["model"]["vocab"].items()}
    added = {token["id"]: token["content"] for token in spec.get("added_tokens", [])}
    rows = []
    for tid in range(vocab_size):
        if tid in added:
            raw = added[tid].encode("utf8")
        elif tid in pieces:
            try:
                raw = bytes(inverse[char] for char in pieces[tid])
            except KeyError as error:
                raise ValueError(f"Token ID {tid} contains a non-ByteLevel character") from error
        else:
            raise VocabHoleError(f"token id {tid} has no vocabulary entry (hole in id space)")
        if not raw:
            raise VocabHoleError(f"token id {tid} yields an empty byte string")
        if len(raw) > max_bytes:
            raise ValueError(f"Token ID {tid} has {len(raw)} bytes, exceeding limit {max_bytes}")
        rows.append(raw)
    return tuple(rows)
