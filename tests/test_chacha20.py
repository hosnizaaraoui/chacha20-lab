"""Tests du coeur ChaCha20 : vecteurs de test RFC 8439 + comparaison avec `cryptography`."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chacha20 import chacha20_block, chacha20_encrypt, quarter_round  # noqa: E402
from core.operations import add32, rotl32, parse_hex_bytes  # noqa: E402

KEY = bytes(range(32))


def test_quarter_round_rfc_2_1_1():
    """RFC 8439 section 2.1.1 : quarter-round sur (a, b, c, d)."""
    state = [0x11111111, 0x01020304, 0x9B8D6F43, 0x01234567]
    quarter_round(state, 0, 1, 2, 3)
    assert state == [0xEA2A92F4, 0xCB1CF8CE, 0x4581472E, 0x5881C4BB]


def test_block_rfc_2_3_2():
    """RFC 8439 section 2.3.2 : bloc de keystream, compteur = 1."""
    nonce = bytes.fromhex("000000090000004a00000000")
    block = chacha20_block(KEY, 1, nonce)
    assert block.keystream.hex().startswith("10f1e7e4d13b5915500fdd1fa32071c4")
    assert len(block.keystream) == 64


def test_encrypt_rfc_2_4_2():
    """RFC 8439 section 2.4.2 : chiffrement du message « sunscreen »."""
    nonce = bytes.fromhex("000000000000004a00000000")
    plaintext = (b"Ladies and Gentlemen of the class of '99: If I could offer you "
                 b"only one tip for the future, sunscreen would be it.")
    ciphertext = chacha20_encrypt(KEY, nonce, 1, plaintext)
    assert ciphertext.hex().startswith("6e2e359a2568f98041ba0728dd0d6981")
    assert chacha20_encrypt(KEY, nonce, 1, ciphertext) == plaintext


def test_trace_has_expected_number_of_steps():
    """80 quarter-rounds x 12 operations + 16 additions finales = 976 etapes."""
    block = chacha20_block(KEY, 1, bytes(12), trace=True)
    assert len(block.events) == 80 * 12 + 16


def test_matches_cryptography_library():
    pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms

    nonce = os.urandom(12)
    message = os.urandom(300)
    counter = 7
    reference = Cipher(
        algorithms.ChaCha20(KEY, counter.to_bytes(4, "little") + nonce), mode=None
    ).encryptor().update(message)
    assert chacha20_encrypt(KEY, nonce, counter, message) == reference


def test_primitives():
    assert add32(0xFFFFFFFF, 1) == 0
    assert rotl32(0x80000000, 1) == 1


def test_input_validation():
    with pytest.raises(ValueError):
        chacha20_block(b"short", 0, bytes(12))
    with pytest.raises(ValueError):
        parse_hex_bytes("zz", 1, "Clé")
