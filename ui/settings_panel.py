"""Panneau de paramètres : clé, nonce, compteur, message et quarter-round observé."""
from __future__ import annotations
import os
import random
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox, QWidget, QGridLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QHBoxLayout, QVBoxLayout
)
from core.operations import parse_hex_bytes
from ui.theme import RFC_KEY, RFC_NONCE, DEFAULT_MESSAGE

SAMPLE_MESSAGES = [
    "ATTACK AT DAWN", "HELLO CHACHA20", "SECRET MESSAGE", "BONJOUR TUNISIE",
    "TOP SECRET 42", "MEET ME AT NOON", "CRYPTO IS FUN",
]
MAX_MESSAGE_BYTES = 128


def qr_description(n: int) -> str:
    """Ex. 'Ronde 1/20 · Colonne' pour le quarter-round n°n (1..80)."""
    rnd = (n - 1) // 4 + 1
    kind = "Colo" if ((n - 1) // 4) % 2 == 0 else "Diag"
    return f"Ronde {rnd}/20 · {kind}"


class SettingsPanel(QWidget):
    # key, nonce, counter, message, qr
    applied = Signal(bytes, bytes, int, str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        g = QGridLayout(self)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)
        g.setColumnStretch(1, 1)

        # Clé
        g.addWidget(self._lbl("🔑  Clé"), 0, 0)
        self.key_edit = QLineEdit(RFC_KEY)
        self.key_hint = QLabel()
        self.key_hint.setObjectName("muted")
        key_rand = QPushButton("🎲")
        key_rand.setObjectName("tiny")
        key_rand.setToolTip("Clé aléatoire")
        key_rand.clicked.connect(
            lambda: self.key_edit.setText(os.urandom(32).hex()))
        g.addWidget(self.key_edit, 0, 1)
        g.addWidget(key_rand, 0, 2)
        g.addWidget(self.key_hint, 1, 1)

        # Nonce
        g.addWidget(self._lbl("🎲  Nonce"), 2, 0)
        self.nonce_edit = QLineEdit(RFC_NONCE)
        self.nonce_hint = QLabel()
        self.nonce_hint.setObjectName("muted")
        nonce_rand = QPushButton("🎲")
        nonce_rand.setObjectName("tiny")
        nonce_rand.setToolTip("Nonce aléatoire")
        nonce_rand.clicked.connect(
            lambda: self.nonce_edit.setText(os.urandom(12).hex()))
        g.addWidget(self.nonce_edit, 2, 1)
        g.addWidget(nonce_rand, 2, 2)
        g.addWidget(self.nonce_hint, 3, 1)

        # Compteur + quarter-round
        row = QHBoxLayout()
        row.setSpacing(10)
        self.counter = QSpinBox()
        self.counter.setRange(0, 2_000_000_000)
        self.counter.setValue(1)
        self.counter.setFixedWidth(150)
        self.counter.setKeyboardTracking(True)
        self.counter.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.counter.setReadOnly(False)
        self.counter.setFocusPolicy(Qt.StrongFocus)

        self.qr = QSpinBox()
        self.qr.setRange(1, 80)
        self.qr.setValue(1)
        self.qr.setFixedWidth(90)
        self.qr.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.qr.setToolTip('1 à 80 (↑ / ↓ ou molette)')
        self.qr_info = QLabel(qr_description(1))
        self.qr_info.setObjectName("muted")
        self.qr.valueChanged.connect(
            lambda n: self.qr_info.setText(qr_description(n)))
        row.addWidget(self.counter)
        row.addSpacing(18)
        row.addWidget(QLabel("Quarter-round observé"))
        row.addWidget(self.qr)
        row.addWidget(self.qr_info)
        row.addStretch()
        g.addWidget(self._lbl("🔢  Compteur"), 4, 0)
        g.addLayout(row, 4, 1, 1, 2)

        # Message
        g.addWidget(self._lbl("✉️  Message"), 5, 0)
        self.msg_edit = QLineEdit(DEFAULT_MESSAGE)
        self.msg_edit.setPlaceholderText("Tapez le message à chiffrer…")
        msg_rand = QPushButton("🎲")
        msg_rand.setObjectName("tiny")
        msg_rand.setToolTip("Message d'exemple")
        msg_rand.clicked.connect(lambda: self.msg_edit.setText(
            random.choice(SAMPLE_MESSAGES)))
        g.addWidget(self.msg_edit, 5, 1)
        g.addWidget(msg_rand, 5, 2)

        # Status + boutons
        self.status = QLabel("")
        self.status.setObjectName("error_label")
        self.status.setWordWrap(True)
        g.addWidget(self.status, 6, 0, 1, 3)

        btns = QHBoxLayout()
        reset = QPushButton("↺  Vecteur de test RFC 8439")
        reset.clicked.connect(self.reset_rfc)
        self.apply_btn = QPushButton("✔  Appliquer et relancer")
        self.apply_btn.setObjectName("primary")
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self._apply)
        btns.addWidget(reset)
        btns.addStretch()
        btns.addWidget(self.apply_btn)
        g.addLayout(btns, 7, 0, 1, 3)

        self.key_edit.textChanged.connect(self._validate)
        self.nonce_edit.textChanged.connect(self._validate)
        self.msg_edit.textChanged.connect(self._validate)
        self.msg_edit.returnPressed.connect(self._apply)
        self._validate()

    @staticmethod
    def _lbl(text):
        l = QLabel(text)
        l.setObjectName("section")
        return l

    @staticmethod
    def _clean(text):
        return text.replace(" ", "").replace(":", "").replace("-", "")

    def _mark(self, edit, bad):
        edit.setProperty("invalid", "true" if bad else "false")
        edit.style().unpolish(edit)
        edit.style().polish(edit)

    def _validate(self):
        ok = True
        for edit, hint, nbytes, label in ((self.key_edit, self.key_hint, 32, "clé"),
                                          (self.nonce_edit, self.nonce_hint, 12, "nonce")):
            cleaned = self._clean(edit.text())
            try:
                bytes.fromhex(cleaned)
                valid_hex = True
            except ValueError:
                valid_hex = False
            good = valid_hex and len(cleaned) == nbytes * 2
            hint.setText(
                f"{len(cleaned)}/{nbytes * 2} caractères hexadécimaux ({nbytes} octets)")
            self._mark(edit, not good)
            ok &= good
        msg_len = len(self.msg_edit.text().encode("utf-8"))
        msg_ok = 0 < msg_len <= MAX_MESSAGE_BYTES
        self._mark(self.msg_edit, not msg_ok)
        ok &= msg_ok
        self.apply_btn.setEnabled(ok)
        if not ok:
            self.status.setText("Vérifiez les champs en rouge (clé 64 hex, nonce 24 hex, "
                                f"message de 1 à {MAX_MESSAGE_BYTES} octets).")
        else:
            self.status.setText("")
        return ok

    def reset_rfc(self):
        self.key_edit.setText(RFC_KEY)
        self.nonce_edit.setText(RFC_NONCE)
        self.counter.setValue(1)
        self.qr.setValue(1)
        self.msg_edit.setText(DEFAULT_MESSAGE)

    def _apply(self):
        if not self._validate():
            return
        try:
            key = parse_hex_bytes(self.key_edit.text(), 32, "Clé")
            nonce = parse_hex_bytes(self.nonce_edit.text(), 12, "Nonce")
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self.applied.emit(key, nonce, self.counter.value(),
                          self.msg_edit.text(), self.qr.value())
