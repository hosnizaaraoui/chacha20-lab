from __future__ import annotations
from PySide6.QtCore import (
    Qt, QEvent, QPropertyAnimation, QSequentialAnimationGroup,
    QEasingCurve
)
from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QWidget
from ui.widgets import Card, TimelineRow
from ui.pages.base_page import BasePage


class AboutPage(BasePage):
    def __init__(self, window, parent=None):
        super().__init__(window, parent)
        self._timeline_items = []
        self._tl_anim = None
        self._build()
        self.installEventFilter(self)

    def _build(self):
        header = QHBoxLayout()
        header.setSpacing(14)
        icon = QLabel("ⓘ")
        icon.setObjectName("hdr_icon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(48, 48)
        tb = QVBoxLayout()
        tb.setSpacing(2)
        title = QLabel("À propos de ChaCha20")
        title.setObjectName("title")
        subtitle = QLabel(
            "Un chiffrement par flot moderne, rapide et ARX-based.")
        subtitle.setObjectName("muted")
        tb.addWidget(title)
        tb.addWidget(subtitle)
        header.addWidget(icon)
        header.addLayout(tb)
        header.addStretch()
        self.layout.addLayout(header)

        intro = Card()
        il = QVBoxLayout(intro)
        il.setContentsMargins(24, 20, 24, 20)
        il.setSpacing(10)
        it = QLabel("ChaCha20, c'est quoi ?")
        it.setObjectName("section")
        il.addWidget(it)
        txt = QLabel(
            "ChaCha20 est un chiffrement par flot conçu par <b>Daniel J. Bernstein</b> en 2008. "
            "Il utilise uniquement des additions, rotations et XOR (ARX) — pas de S-box, "
            "pas de lookup tables. C'est ce qui le rend rapide, sûr, et résistant aux attaques "
            "par canaux auxiliaires."
        )
        txt.setWordWrap(True)
        txt.setObjectName("explanation")
        il.addWidget(txt)
        self.layout.addWidget(intro)

        tl_title = QLabel("📜  Histoire de ChaCha20")
        tl_title.setObjectName("section")
        self.layout.addWidget(tl_title)
        self.layout.addWidget(self._build_timeline())

        std = Card()
        sl = QVBoxLayout(std)
        sl.setContentsMargins(24, 20, 24, 20)
        sl.setSpacing(10)
        st = QLabel("📖  ChaCha20 dans les standards")
        st.setObjectName("section")
        sl.addWidget(st)
        for name, desc in (
            ("RFC 7539", "2015 — ChaCha20 & Poly1305 pour IETF, proposé par A. Langley."),
            ("RFC 8439", "2018 — Révision officielle de RFC 7539, avec les vecteurs de test."),
            ("TLS 1.3", "2018 — ChaCha20-Poly1305 est un cipher suite obligatoire."),
            ("WireGuard", "2018 — Utilise ChaCha20-Poly1305 comme chiffrement principal."),
        ):
            row = QLabel(f"<b>{name}</b> — {desc}")
            row.setWordWrap(True)
            row.setObjectName("explanation")
            sl.addWidget(row)
        self.layout.addWidget(std)
        self.layout.addStretch()

    def _build_timeline(self):
        container = QWidget()
        vl = QVBoxLayout(container)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)
        events = [
            ("2005", "Salsa20", "Daniel J. Bernstein propose Salsa20 — l'ancêtre direct de ChaCha20.", "ancestor"),
            ("2008", "ChaCha20",
             "Bernstein publie ChaCha20 comme une amélioration de Salsa20.", "birth"),
            ("2013", "Google l'adopte",
             "Google choisit ChaCha20 pour Chrome en l'absence d'AES hardware.", "adoption"),
            ("2015", "RFC 7539", "ChaCha20-Poly1305 devient un standard IETF.", "standard"),
            ("2018", "RFC 8439", "Révision officielle. ChaCha20 est partout : TLS 1.3, WireGuard, QUIC.", "modern"),
            ("2024", "Toujours moderne",
             "Toujours utilisé par défaut. ARX pour l'éternité.", "now"),
        ]
        self._timeline_items = []
        for i, (year, name, desc, kind) in enumerate(events):
            row = TimelineRow(year, name, desc, kind,
                              first=(i == 0), last=(i == len(events) - 1))
            self._timeline_items.append(row)
            vl.addWidget(row)
        return container

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Show and obj is self:
            self._animate_timeline()
        return super().eventFilter(obj, ev)

    def _animate_timeline(self):
        items = self._timeline_items
        if not items:
            return
        old = self._tl_anim
        if old is not None:
            old.stop()
            old.deleteLater()
        group = QSequentialAnimationGroup(self)
        for item in items:
            eff = self.set_opacity(item, 0.0)
            anim = QPropertyAnimation(eff, b"opacity")
            anim.setDuration(350)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            group.addPause(80)
            group.addAnimation(anim)

        def _cleanup():
            for item in items:
                item.setGraphicsEffect(None)

        group.finished.connect(_cleanup)
        self._tl_anim = group
        group.start()
