from __future__ import annotations
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QSequentialAnimationGroup,
    QParallelAnimationGroup, QEasingCurve, QAbstractAnimation, Signal
)
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QGraphicsOpacityEffect
)
from ui.theme import ACCENT, ACCENT_DARK, ACCENT_SOFT, TEXT, MUTED


# Chaque scène : (emoji, titre, texte)
SCENES = [
    ("🧠", "2005 — Une idée simple",
     "Daniel J. Bernstein, cryptographe et mathématicien, se demande comment "
     "construire un chiffrement rapide sans dépendre d'accélération matérielle."),
    ("🌀", "Salsa20 — premier jet",
     "Il publie Salsa20, un chiffrement par flot basé sur trois opérations "
     "simples : addition, rotation, XOR (ARX). Pas de S-box, pas de tables."),
    ("🔧", "2008 — Une amélioration",
     "Il retravaille Salsa20 pour améliorer la diffusion des bits. "
     "Le résultat : ChaCha20, plus rapide et plus sûr."),
    ("🌍", "Aujourd'hui",
     "ChaCha20 est partout : TLS 1.3, WireGuard, SSH, Android, "
     "le générateur aléatoire de Linux…"),
    ("⚙️", "Entrons dans la machine",
     "Nous allons observer un quarter-round : 4 mots a, b, c, d qui se "
     "transforment via ADD, XOR et ROTL. C'est le cœur de ChaCha20."),
]


class IntroPage(QWidget):
    finished = Signal()

    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("page")
        self._index = 0
        self._animating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        # Carte centrale
        self.card = QFrame()
        self.card.setObjectName("introCard")
        self.card.setFixedWidth(720)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(48, 48, 48, 48)
        card_layout.setSpacing(24)
        card_layout.setAlignment(Qt.AlignCenter)

        self.emoji = QLabel("🧠")
        self.emoji.setObjectName("iconLabel")
        self.emoji.setAlignment(Qt.AlignCenter)
        self.emoji.setStyleSheet("font-size: 90px;")
        card_layout.addWidget(self.emoji)

        self.title = QLabel("")
        self.title.setObjectName("introTitle")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setWordWrap(True)
        card_layout.addWidget(self.title)

        self.text = QLabel("")
        self.text.setObjectName("introText")
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setWordWrap(True)
        card_layout.addWidget(self.text)

        # Indicateur de progression
        self.dots_row = QHBoxLayout()
        self.dots_row.setSpacing(8)
        self.dots_row.setAlignment(Qt.AlignCenter)
        self.dots = []
        for _ in SCENES:
            dot = QLabel("●")
            dot.setObjectName("introDot")
            self.dots.append(dot)
            self.dots_row.addWidget(dot)
        card_layout.addSpacing(16)
        card_layout.addLayout(self.dots_row)

        layout.addWidget(self.card, 0, Qt.AlignCenter)

        # Boutons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setAlignment(Qt.AlignCenter)

        self.skip_btn = QPushButton("Passer l'intro →")
        self.skip_btn.setObjectName("link_btn")
        self.skip_btn.setCursor(Qt.PointingHandCursor)
        self.skip_btn.clicked.connect(self._finish)

        self.next_btn = QPushButton("Suivant →")
        self.next_btn.setObjectName("primary")
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(self._next)

        btn_row.addWidget(self.skip_btn)
        btn_row.addWidget(self.next_btn)
        layout.addSpacing(24)
        layout.addLayout(btn_row)

        # Timer auto-advance
        self._timer = QTimer(self)
        self._timer.setInterval(4000)
        self._timer.timeout.connect(self._next)

        # Opacity effect pour le fade
        self._effect = QGraphicsOpacityEffect(self.card)
        self.card.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)

    def showEvent(self, ev):
        super().showEvent(ev)
        if self._index == 0 and not self._animating:
            self._render_scene()
            self._timer.start()

    # ------------------------------------------------------------ render
    def _render_scene(self):
        self._animating = True
        emoji, title, text = SCENES[self._index]

        # Fade out
        fade_out = QPropertyAnimation(self._effect, b"opacity", self)
        fade_out.setDuration(250)
        fade_out.setStartValue(self._effect.opacity())
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.OutCubic)

        def swap_and_fade_in():
            self.emoji.setText(emoji)
            self.title.setText(title)
            self.text.setText(text)
            for i, d in enumerate(self.dots):
                d.setObjectName("introDotActive" if i ==
                                self._index else "introDot")
                d.setStyleSheet("")
            fade_in = QPropertyAnimation(self._effect, b"opacity", self)
            fade_in.setDuration(400)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.OutCubic)
            fade_in.finished.connect(
                lambda: setattr(self, "_animating", False))
            fade_in.start(QAbstractAnimation.DeleteWhenStopped)
            self._fade_in = fade_in

        fade_out.finished.connect(swap_and_fade_in)
        fade_out.start(QAbstractAnimation.DeleteWhenStopped)
        self._fade_out = fade_out

    # ------------------------------------------------------------ control
    def _next(self):
        if self._animating:
            return
        if self._index >= len(SCENES) - 1:
            self._finish()
            return
        self._index += 1
        self._render_scene()
        self._timer.start()

    def _finish(self):
        self._timer.stop()
        self.finished.emit()

    def start(self):
        """Relance l'intro depuis le début."""
        self._index = 0
        self._effect.setOpacity(0.0)
        self._timer.start()
        self._render_scene()
