from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from .operations import add32, xor32, rotl32, word_details

CONSTANTS = (0x61707865, 0x3320646E, 0x79622D32, 0x6B206574)

def words_from_bytes(data: bytes) -> list[int]:
    if len(data) % 4:
        raise ValueError("La longueur doit être un multiple de 4 octets.")
    return [int.from_bytes(data[i:i+4], "little") for i in range(0, len(data), 4)]

def initial_state(key: bytes, counter: int, nonce: bytes) -> list[int]:
    if len(key) != 32:
        raise ValueError("La clé ChaCha20 doit contenir exactement 32 octets.")
    if len(nonce) != 12:
        raise ValueError("Le nonce ChaCha20 doit contenir exactement 12 octets.")
    if not 0 <= counter <= 0xFFFFFFFF:
        raise ValueError("Le compteur doit être compris entre 0 et 2^32-1.")
    return list(CONSTANTS) + words_from_bytes(key) + [counter] + words_from_bytes(nonce)

def quarter_round(state: list[int], ai: int, bi: int, ci: int, di: int,
                  on_event: Callable[[dict], None] | None = None,
                  round_no: int = 0, qr_no: int = 0, qr_kind: str = "") -> None:
    """Exécute un quarter-round RFC 8439 et peut tracer chacune des 12 opérations."""
    a, b, c, d = state[ai], state[bi], state[ci], state[di]

    def emit(op, target, before, operands, after, explanation, rotation=None):
        if on_event:
            on_event({
                "round": round_no, "quarter_round": qr_no, "kind": qr_kind,
                "operation": op, "target": target,
                "indices": {"a": ai, "b": bi, "c": ci, "d": di},
                "before": before, "operands": operands, "after": after,
                "explanation": explanation, "rotation": rotation,
                "state": state.copy(),
            })

    old = a; a = add32(a, b); state[ai] = a
    emit("ADD", "a", old, {"b": b, "modulus": "2^32"}, a,
         "Addition modulo 2^32 : les bits au-delà de 32 bits sont ignorés.")
    old = d; d = xor32(d, a); state[di] = d
    emit("XOR", "d", old, {"a": a}, d,
         "XOR bit à bit : le bit vaut 1 lorsque les deux bits sont différents.")
    old = d; d = rotl32(d, 16); state[di] = d
    emit("ROTL", "d", old, {"count": 16}, d,
         "Rotation circulaire à gauche de 16 bits : les bits sortants reviennent à droite.", 16)

    old = c; c = add32(c, d); state[ci] = c
    emit("ADD", "c", old, {"d": d, "modulus": "2^32"}, c,
         "Addition modulo 2^32.")
    old = b; b = xor32(b, c); state[bi] = b
    emit("XOR", "b", old, {"c": c}, b, "XOR bit à bit.")
    old = b; b = rotl32(b, 12); state[bi] = b
    emit("ROTL", "b", old, {"count": 12}, b,
         "Rotation circulaire à gauche de 12 bits.", 12)

    old = a; a = add32(a, b); state[ai] = a
    emit("ADD", "a", old, {"b": b, "modulus": "2^32"}, a, "Addition modulo 2^32.")
    old = d; d = xor32(d, a); state[di] = d
    emit("XOR", "d", old, {"a": a}, d, "XOR bit à bit.")
    old = d; d = rotl32(d, 8); state[di] = d
    emit("ROTL", "d", old, {"count": 8}, d, "Rotation circulaire à gauche de 8 bits.", 8)

    old = c; c = add32(c, d); state[ci] = c
    emit("ADD", "c", old, {"d": d, "modulus": "2^32"}, c, "Addition modulo 2^32.")
    old = b; b = xor32(b, c); state[bi] = b
    emit("XOR", "b", old, {"c": c}, b, "XOR bit à bit.")
    old = b; b = rotl32(b, 7); state[bi] = b
    emit("ROTL", "b", old, {"count": 7}, b, "Rotation circulaire à gauche de 7 bits.", 7)

@dataclass
class BlockResult:
    initial: list[int]
    working: list[int]
    output_words: list[int]
    keystream: bytes
    events: list[dict]

def chacha20_block(key: bytes, counter: int, nonce: bytes, trace: bool = False) -> BlockResult:
    initial = initial_state(key, counter, nonce)
    working = initial.copy()
    events: list[dict] = []

    def record(event):
        event["step"] = len(events) + 1
        events.append(event)

    qr_no = 0
    for double_round in range(10):
        round_col = double_round * 2 + 1
        column_quarters = [
            (0, 4, 8, 12), (1, 5, 9, 13),
            (2, 6, 10, 14), (3, 7, 11, 15),
        ]
        for indices in column_quarters:
            qr_no += 1
            quarter_round(working, *indices, on_event=record if trace else None,
                          round_no=round_col, qr_no=qr_no, qr_kind="Colonne")

        round_diag = round_col + 1
        diagonal_quarters = [
            (0, 5, 10, 15), (1, 6, 11, 12),
            (2, 7, 8, 13), (3, 4, 9, 14),
        ]
        for indices in diagonal_quarters:
            qr_no += 1
            quarter_round(working, *indices, on_event=record if trace else None,
                          round_no=round_diag, qr_no=qr_no, qr_kind="Diagonale")

    output_words = [add32(x, y) for x, y in zip(initial, working)]
    if trace:
        feed_state = working.copy()
        for index, (before, added, after) in enumerate(zip(working, initial, output_words)):
            feed_state[index] = after
            events.append({
                "step": len(events) + 1, "round": 20, "quarter_round": None,
                "kind": "Addition finale", "operation": "FEED-FORWARD",
                "target": f"mot[{index}]", "before": before,
                "operands": {"état_initial": added, "modulus": "2^32"},
                "after": after,
                "explanation": "Addition du mot de l'état initial au mot transformé, modulo 2^32.",
                "rotation": None, "state": feed_state.copy(),
            })
    keystream = b"".join(w.to_bytes(4, "little") for w in output_words)
    return BlockResult(initial, working, output_words, keystream, events)

def chacha20_encrypt(key: bytes, nonce: bytes, counter: int, message: bytes) -> bytes:
    if len(key) != 32 or len(nonce) != 12:
        raise ValueError("Clé de 32 octets et nonce de 12 octets requis.")
    if not 0 <= counter <= 0xFFFFFFFF:
        raise ValueError("Compteur invalide.")
    output = bytearray()
    for offset in range(0, len(message), 64):
        block_counter = counter + offset // 64
        if block_counter > 0xFFFFFFFF:
            raise ValueError("Dépassement du compteur ChaCha20.")
        stream = chacha20_block(key, block_counter, nonce).keystream
        chunk = message[offset:offset+64]
        output.extend(a ^ b for a, b in zip(chunk, stream))
    return bytes(output)

def describe_byte_xor(message: bytes, keystream: bytes) -> list[dict]:
    rows = []
    for i, value in enumerate(message):
        key_byte = keystream[i]
        encrypted = value ^ key_byte
        rows.append({
            "index": i, "plain": value, "key": key_byte, "cipher": encrypted,
            "plain_hex": f"0x{value:02X}", "key_hex": f"0x{key_byte:02X}",
            "cipher_hex": f"0x{encrypted:02X}",
        })
    return rows
