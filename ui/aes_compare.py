"""Comparaison d'une opération ChaCha20 avec son équivalent (ou non) dans AES."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget
)

LEVEL_TEXT = {
    "direct": "Équivalent direct",
    "partial": "Équivalent partiel",
    "none": "Pas d'équivalent",
}

_ADD = {
    "title": "ADD : addition modulo 2³²",
    "aes_name": "Aucun équivalent direct (le plus proche : AddRoundKey / MixColumns)",
    "level": "none",
    "same": [
        "Même objectif : mélanger les bits pour que chaque bit de sortie dépende de nombreux bits d'entrée (diffusion).",
    ],
    "diff": [
        "AES n'additionne jamais d'entiers : ses « additions » sont des XOR (addition dans GF(2⁸)), donc linéaires.",
        "L'addition modulo 2³² produit des retenues : un bit du résultat dépend de tous les bits de poids plus faible. C'est la source de non-linéarité de ChaCha20.",
        "AES obtient sa non-linéarité avec la S-box de SubBytes (une table de 256 valeurs). ChaCha20 n'a aucune table : exécution en temps constant, pas d'attaque par cache-timing.",
    ],
    "takeaway": "ChaCha20 remplace la S-box d'AES par des additions avec retenue.",
}

_XOR = {
    "title": "XOR : OU exclusif bit à bit",
    "aes_name": "AddRoundKey",
    "level": "direct",
    "same": [
        "Même opération : un XOR bit à bit, linéaire et auto-inverse (x ⊕ k ⊕ k = x).",
        "Dans les deux cas, on injecte de l'information (clé ou autre mot) dans l'état.",
    ],
    "diff": [
        "AES : l'état est XORé avec une sous-clé de ronde, fixe et indépendante des données (issue du key schedule).",
        "ChaCha20 : on XOR avec un autre mot de l'état (ex. d ⊕ a), donc dépendant des données. La clé n'entre qu'au départ, dans l'état initial.",
        "AddRoundKey agit sur 128 bits d'un coup ; ici on traite un mot de 32 bits à la fois, au sein d'un quarter-round.",
        "Dans AES, AddRoundKey seul ne mélange rien : la diffusion vient de ShiftRows + MixColumns.",
    ],
    "takeaway": "Le XOR est le point commun parfait entre les deux algorithmes.",
}

_ROTL_BYTE = {
    "title": "ROTL {n} : rotation circulaire de {n} bits",
    "aes_name": "ShiftRows (et RotWord du key schedule)",
    "level": "partial",
    "same": [
        "Une rotation de {n} bits déplace des octets entiers : {n_text}",
        "RotWord, dans le key schedule d'AES, tourne un mot de 4 octets d'un octet : c'est l'équivalent d'un ROTL 8.",
    ],
    "diff": [
        "ShiftRows décale les lignes de la matrice 4×4 d'octets : les octets changent de colonne, ce qui diffuse entre colonnes. Ici la rotation reste dans un seul mot de 32 bits.",
        "AES applique des décalages différents selon la ligne (0, 1, 2, 3 octets) ; ChaCha20 applique la même rotation à tout le mot.",
        "ShiftRows est une pure permutation d'octets ; la rotation ChaCha20 n'a d'effet que combinée aux ADD et XOR voisins.",
    ],
    "takeaway": "Rotation d'octets : cousine de ShiftRows, mais à l'intérieur d'un seul mot.",
}

_ROTL_BIT = {
    "title": "ROTL {n} : rotation circulaire de {n} bits",
    "aes_name": "Aucun équivalent (proche, par son rôle, de MixColumns)",
    "level": "none",
    "same": [
        "Rôle de diffusion identique : déplacer les bits pour que le prochain ADD / XOR les combine avec d'autres bits.",
    ],
    "diff": [
        "{n} n'est pas un multiple de 8 : les bits traversent les frontières d'octets. AES ne fait jamais cela : il travaille toujours octet par octet.",
        "AES diffuse avec MixColumns : multiplication de chaque colonne par une matrice fixe dans GF(2⁸), plus coûteuse en logiciel sans AES-NI.",
        "ChaCha20 obtient un effet comparable avec des rotations et des additions très simples (16, 12, 8, 7 choisis pour maximiser la diffusion).",
    ],
    "takeaway": "Rotation au bit près : une spécialité ARX, sans équivalent dans AES.",
}

OVERVIEW = [
    ("Type", "Chiffrement par blocs (128 bits)",
     "Chiffrement par flot (keystream)"),
    ("Structure", "SubBytes, ShiftRows, MixColumns, AddRoundKey",
     "ARX : Add, Rotate, XOR"),
    ("Rondes", "10 / 12 / 14", "20"),
    ("État", "matrice 4×4 d'octets (128 bits)",
     "matrice 4×4 de mots 32 bits (512 bits)"),
    ("Non-linéarité", "S-box (table)", "addition modulo 2³²"),
    ("Déchiffrement", "opérations inverses",
     "mêmes opérations (XOR avec le keystream)"),
    ("Temps constant", "avec AES-NI ou bitslicing", "naturellement, sans table"),
]


def aes_info_for(event: dict) -> dict:
    """Retourne la fiche de comparaison AES pour l'événement donné."""
    op = event["operation"]
    if op == "ADD":
        info = dict(_ADD)
    elif op == "XOR":
        info = dict(_XOR)
    elif op == "ROTL":
        n = event.get("rotation") or 0
        if n % 8 == 0:
            row = {8: "elle correspond à ShiftRows sur la ligne 1 (décalage d'1 octet).",
                   16: "elle correspond à ShiftRows sur la ligne 2 (décalage de 2 octets) : les deux moitiés du mot sont échangées."
                   }.get(n, "c'est un décalage d'octets entiers, comme ShiftRows.")
            info = dict(_ROTL_BYTE, n_text=row)
        else:
            info = dict(_ROTL_BIT)
        fmt = {"n": n, "n_text": info.get("n_text", "")}
        for key in ("title", "same", "diff"):
            val = info[key]
            info[key] = ([s.format(**fmt) for s in val] if isinstance(val, list)
                         else val.format(**fmt))
    else:
        info = dict(_ADD)
    return info


def _bullet_list(items, kind: str) -> QWidget:
    """Liste de puces : kind = 'same' ou 'diff' (sert aux objectName du QSS)."""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    for text in items:
        row = QHBoxLayout()
        row.setSpacing(6)
        dot = QLabel("●")
        dot.setObjectName(f"aes_dot_{kind}")
        t = QLabel(text)
        t.setObjectName("aes_bullet_text")
        t.setWordWrap(True)
        row.addWidget(dot, 0, Qt.AlignTop)
        row.addWidget(t, 1)
        lay.addLayout(row)
    return w


def _card(object_name: str, title: str, title_name: str, body: QWidget) -> QFrame:
    box = QFrame()
    box.setObjectName(object_name)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(18, 16, 18, 16)
    lay.setSpacing(12)
    t = QLabel(title)
    t.setObjectName(title_name)
    lay.addWidget(t)
    lay.addWidget(body)
    lay.addStretch()
    return box


class AesCompareDialog(QDialog):
    def __init__(self, event: dict, parent=None):
        super().__init__(parent)
        info = aes_info_for(event)
        self.setWindowTitle("ChaCha20 vs AES")
        self.resize(900, 720)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body.setObjectName("page")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(26, 24, 26, 16)
        lay.setSpacing(16)

        # 1) En-tête
        header = QFrame()
        header.setObjectName("aes_header")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(24, 20, 24, 20)
        hl.setSpacing(8)

        eyebrow = QLabel("CHACHA20  ↔  AES")
        eyebrow.setObjectName("aes_eyebrow")
        title = QLabel(info["title"])
        title.setObjectName("aes_title")
        title.setWordWrap(True)

        meta = QHBoxLayout()
        meta.setSpacing(12)
        badge = QLabel(LEVEL_TEXT[info["level"]])
        badge.setObjectName(f"badge_{info['level']}")
        name = QLabel(f"Côté AES : <b>{info['aes_name']}</b>")
        name.setObjectName("aes_name")
        name.setWordWrap(True)
        meta.addWidget(badge, 0, Qt.AlignTop)
        meta.addWidget(name, 1)

        hl.addWidget(eyebrow)
        hl.addWidget(title)
        hl.addLayout(meta)
        lay.addWidget(header)

        # 2) Cartes côte à côte
        cols = QHBoxLayout()
        cols.setSpacing(16)
        cols.addWidget(_card("aes_same_card", "✅  Ce qui se ressemble",
                             "aes_card_title_same", _bullet_list(info["same"], "same")), 1)
        cols.addWidget(_card("aes_diff_card", "⚡  Ce qui diffère",
                             "aes_card_title_diff", _bullet_list(info["diff"], "diff")), 1)
        lay.addLayout(cols)

        # 3) À retenir
        take = QFrame()
        take.setObjectName("aes_takeaway")
        tl = QHBoxLayout(take)
        tl.setContentsMargins(18, 14, 18, 14)
        tl.setSpacing(12)
        icon = QLabel("💡")
        icon.setObjectName("aes_takeaway_icon")
        text = QLabel(info["takeaway"])
        text.setObjectName("aes_takeaway_text")
        text.setWordWrap(True)
        tl.addWidget(icon, 0, Qt.AlignTop)
        tl.addWidget(text, 1)
        lay.addWidget(take)

        # 4) Vue d'ensemble
        lay.addWidget(self._overview())

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # 5) Pied
        footer = QWidget()
        footer.setObjectName("aes_footer")
        bar = QHBoxLayout(footer)
        bar.setContentsMargins(26, 10, 26, 18)
        bar.addStretch()
        close = QPushButton("Fermer")
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        bar.addWidget(close)
        outer.addWidget(footer)

    @staticmethod
    def _overview() -> QFrame:
        box = QFrame()
        box.setObjectName("aes_overview")
        v = QVBoxLayout(box)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)

        t = QLabel("📊  Vue d'ensemble : AES vs ChaCha20")
        t.setObjectName("aes_overview_title")
        v.addWidget(t)

        grid = QGridLayout()
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(2)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 3)

        blank = QLabel("")
        blank.setObjectName("ov_head_blank")
        h_aes = QLabel("AES")
        h_aes.setObjectName("ov_head_aes")
        h_cc = QLabel("ChaCha20")
        h_cc.setObjectName("ov_head_cc")
        grid.addWidget(blank, 0, 0)
        grid.addWidget(h_aes, 0, 1)
        grid.addWidget(h_cc, 0, 2)

        for i, (a, b, c) in enumerate(OVERVIEW, start=1):
            alt = "true" if i % 2 == 0 else "false"
            for col, (txt, oid) in enumerate(((a, "ov_key"), (b, "ov_cell"), (c, "ov_cell"))):
                lbl = QLabel(txt)
                lbl.setObjectName(oid)
                lbl.setWordWrap(True)
                lbl.setProperty("alt", alt)
                grid.addWidget(lbl, i, col)
        v.addLayout(grid)
        return box
