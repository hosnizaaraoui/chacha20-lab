"""Construit le calcul vertical (façon « opération posée ») d'une étape."""
from __future__ import annotations
from ui.theme import ACCENT, GREEN, RED, MUTED

MASK32 = 0xFFFFFFFF


def operand_name(event: dict):
    return next((k for k in event.get("operands", {}) if k in "abcd" and len(k) == 1), None)


def formula(event: dict) -> str:
    t, op = event["target"], event["operation"]
    o = operand_name(event)
    if op == "ADD":
        return f"{t} ← {t} + {o}  (mod 2³²)"
    if op == "XOR":
        return f"{t} ← {t} ⊕ {o}"
    if op == "ROTL":
        return f"{t} ← {t} <<< {event.get('rotation')}"
    return f"{t} ← {t} + état initial"


def _bits(value: int, colors: dict | None = None, dim_zero: bool = False) -> str:
    s = f"{value & MASK32:032b}"
    out = []
    for i, ch in enumerate(s):
        if i and i % 4 == 0:
            out.append("&nbsp;")
        c = colors.get(i) if colors else None
        if c:
            out.append(f"<span style='color:{c};font-weight:800'>{ch}</span>")
        elif dim_zero and ch == "0":
            out.append("<span style='color:#C5C8D8'>0</span>")
        else:
            out.append(ch)
    return "".join(out)


def _mask_colors(mask: int, color: str) -> dict:
    return {i: color for i in range(32) if (mask >> (31 - i)) & 1}


def _row(label: str, content: str, label_color: str = MUTED) -> str:
    return (f"<tr><td align='right' style='color:{label_color};padding-right:10px;white-space:nowrap'>"
            f"{label}</td><td style='white-space:nowrap'>{content}</td></tr>")


SEP = "<tr><td></td><td style='color:#C5C8D8'>" + "─" * 39 + "</td></tr>"


def build_calc_html(event: dict) -> str:
    op = event["operation"]
    t = event["target"]
    o = operand_name(event)
    before, after = event["before"], event["after"]
    rows, notes = [], []

    if op == "ADD":
        operand = event["operands"][o]
        carries = before ^ operand ^ after           # bit i = retenue entrant dans le bit i
        overflow = (before + operand) >> 32
        rows.append(_row("retenues", _bits(carries, _mask_colors(carries, ACCENT), True), ACCENT))
        rows.append(_row(f"{t}", _bits(before)))
        rows.append(_row(f"+ {o}", _bits(operand)))
        rows.append(SEP)
        rows.append(_row(f"= {t}'", _bits(after, _mask_colors(before ^ after, GREEN)), GREEN))
        notes.append(f"<span style='color:{ACCENT}'><b>Violet</b></span> : une retenue entre dans ce bit. "
                     f"<span style='color:{GREEN}'><b>Vert</b></span> : bit modifié.")
        if overflow:
            notes.append("Dépassement de 32 bits : la retenue finale est <b>ignorée</b> (modulo 2³²).")
        notes.append(f"0x{before:08X} + 0x{operand:08X} = 0x{after:08X}")
        notes.append(f"{before} + {operand} = {before + operand}  →  mod 2³² = {after}")

    elif op == "XOR":
        operand = event["operands"][o]
        rows.append(_row(f"{t}", _bits(before)))
        rows.append(_row(f"⊕ {o}", _bits(operand, _mask_colors(operand, ACCENT)), ACCENT))
        rows.append(SEP)
        rows.append(_row(f"= {t}'", _bits(after, _mask_colors(operand, GREEN)), GREEN))
        notes.append(f"Là où <span style='color:{ACCENT}'><b>{o} vaut 1</b></span>, le bit de {t} est "
                     f"<b>inversé</b> (<span style='color:{GREEN}'>vert</span>) ; ailleurs il reste identique.")
        notes.append(f"0x{before:08X} ⊕ 0x{operand:08X} = 0x{after:08X}")

    elif op == "ROTL":
        n = event.get("rotation") or 0
        s = f"{before:032b}"
        wrapped, rest = s[:n], s[n:]

        def grp(txt_red, txt_black, red_first):
            full = (txt_red + txt_black) if red_first else (txt_black + txt_red)
            colors = {i: RED for i in range(n)} if red_first else {i: RED for i in range(32 - n, 32)}
            return _bits(int(full, 2), colors)

        rows.append(_row(f"{t}", grp(wrapped, rest, True)))
        rows.append(_row(f"<<< {n}", f"<span style='color:{RED}'>↶ les {n} bits de gauche passent à droite</span>", RED))
        rows.append(SEP)
        rows.append(_row(f"= {t}'", grp(wrapped, rest, False), GREEN))
        notes.append(f"<span style='color:{RED}'><b>Rouge</b></span> : bits qui sortent à gauche et reviennent à droite. "
                     "Aucun bit n'est perdu.")
        notes.append(f"0x{before:08X} <<< {n} = 0x{after:08X}")

    else:  # FEED-FORWARD
        operand = event["operands"].get("état_initial", 0)
        rows.append(_row("mot", _bits(before)))
        rows.append(_row("+ initial", _bits(operand)))
        rows.append(SEP)
        rows.append(_row("= sortie", _bits(after), GREEN))
        notes.append(f"0x{before:08X} + 0x{operand:08X} = 0x{after:08X}")

    table = ("<table cellspacing='0' cellpadding='3' "
             "style='font-family:monospace;font-size:14px;'>" + "".join(rows) + "</table>")
    note_html = "".join(f"<p style='margin:4px 0;color:#4A4E69;font-family:sans-serif;font-size:12px'>{n}</p>"
                        for n in notes)
    return table + "<br>" + note_html
