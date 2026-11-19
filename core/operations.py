MASK32 = 0xFFFFFFFF

def add32(a: int, b: int) -> int:
    """Addition modulo 2**32."""
    return (a + b) & MASK32

def xor32(a: int, b: int) -> int:
    """XOR limité à 32 bits."""
    return (a ^ b) & MASK32

def rotl32(value: int, count: int) -> int:
    """Rotation circulaire à gauche sur 32 bits."""
    value &= MASK32
    count %= 32
    if count == 0:
        return value
    return ((value << count) | (value >> (32 - count))) & MASK32

def word_details(value: int) -> dict:
    value &= MASK32
    return {
        "hex": f"0x{value:08X}",
        "decimal": value,
        "binary": f"{value:032b}",
    }

def parse_hex_bytes(value: str, expected_length: int, label: str) -> bytes:
    cleaned = value.replace(" ", "").replace(":", "").replace("-", "")
    try:
        result = bytes.fromhex(cleaned)
    except ValueError as exc:
        raise ValueError(f"{label} : saisissez une valeur hexadécimale valide.") from exc
    if len(result) != expected_length:
        raise ValueError(f"{label} : {expected_length} octets requis ({expected_length * 2} caractères hexadécimaux).")
    return result
