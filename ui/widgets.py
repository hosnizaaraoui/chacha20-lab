"""Widgets réutilisables : cartes, panneau repliable, rangée de bits animée, etc."""
from __future__ import annotations
import math
from PySide6.QtCore import (
    Qt, QRectF, QSize, Signal, QVariantAnimation, QEasingCurve, QPropertyAnimation,
    QEvent, QPointF, QSequentialAnimationGroup
)
from PySide6.QtGui import QColor, QPainter, QFont, QFontDatabase, QPen
from PySide6.QtWidgets import (
    QFrame, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
from ui.theme import (
    ACCENT, ACCENT_DARK, GREEN, RED, MUTED, OP_COLORS
)

MASK32 = 0xFFFFFFFF
QWIDGETSIZE_MAX = 16777215


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(40, 36, 90, 30))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)


class CollapsibleCard(Card):
    """Carte dont le contenu se replie / se déplie avec une animation."""

    def __init__(self, title: str, content: QWidget, expanded: bool = True, parent=None):
        super().__init__(parent)
        self._title = title
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.header = QPushButton()
        self.header.setObjectName("collapse_header")
        self.header.setCheckable(True)
        self.header.setCursor(Qt.PointingHandCursor)

        self.content = content
        self._wrap = QWidget()
        wl = QVBoxLayout(self._wrap)
        wl.setContentsMargins(22, 0, 22, 18)
        wl.addWidget(content)

        lay.addWidget(self.header)
        lay.addWidget(self._wrap)

        self._anim = QPropertyAnimation(self._wrap, b"maximumHeight", self)
        self._anim.setDuration(260)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim.finished.connect(self._after_anim)

        self.header.setChecked(expanded)
        self._refresh_title(expanded)
        self._wrap.setVisible(expanded)
        self.header.toggled.connect(self._toggle)

    def _refresh_title(self, opened: bool):
        self.header.setText(f"{'▾' if opened else '▸'}   {self._title}")

    def set_expanded(self, opened: bool):
        self.header.setChecked(opened)

    def _toggle(self, opened: bool):
        self._refresh_title(opened)
        self._anim.stop()
        if opened:
            self._wrap.setMaximumHeight(0)
            self._wrap.setVisible(True)
            target = max(self._wrap.sizeHint().height(),
                         self._wrap.minimumSizeHint().height())
            self._anim.setStartValue(0)
            self._anim.setEndValue(target)
        else:
            self._anim.setStartValue(self._wrap.height())
            self._anim.setEndValue(0)
        self._anim.start()

    def _after_anim(self):
        if self.header.isChecked():
            self._wrap.setMaximumHeight(QWIDGETSIZE_MAX)
        else:
            self._wrap.setVisible(False)


class BitRow(QWidget):
    """32 bits dessinés sous forme de cellules, avec 3 animations :
    - 'add'  : la retenue se propage du bit de poids faible vers la gauche
    - 'xor'  : les bits concernés se retournent (flip)
    - 'rotl' : les bits glissent vers la gauche et ceux qui sortent
               réapparaissent à droite (rotation circulaire)
    """
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._from = 0
        self._to = 0
        self._mode = "static"
        self._shift = 0
        self._t = 0.0
        self.setFixedHeight(38)
        self.setMinimumWidth(32 * 13)
        self._font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self._font.setPointSize(10)
        self._font.setBold(True)

        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._on_tick)
        self._anim.finished.connect(self._on_done)

    # --- API ---------------------------------------------------------------
    def value(self) -> int:
        return self._value

    def set_value(self, v: int):
        self._anim.stop()
        self._mode = "static"
        self._value = v & MASK32
        self.update()

    def animate(self, kind: str, before: int, after: int, shift: int = 0, duration: int = 700):
        self._anim.stop()
        self._mode = kind
        self._from = before & MASK32
        self._to = after & MASK32
        self._shift = shift
        self._t = 0.0
        self._anim.setDuration(max(80, duration))
        self._anim.setEasingCurve(
            QEasingCurve.InOutCubic if kind == "rotl" else QEasingCurve.Linear)
        self._anim.start()

    def _on_tick(self, v):
        self._t = float(v)
        self.update()

    def _on_done(self):
        self._value = self._to
        self._mode = "static"
        self.update()
        self.finished.emit()

    # --- painting ----------------------------------------------------------
    @staticmethod
    def _bit(v, i):
        return (v >> (31 - i)) & 1

    def _draw_cell(self, p, x, cw, h, bit, style="normal", sy=1.0):
        rect = QRectF(x + 1.5, 5, cw - 3, h - 10)
        fills = {
            "normal": ("#E3DCFF" if bit else "#FFFFFF", ACCENT_DARK if bit else "#9A9EB5", "#E3E5F0"),
            "changed": ("#D7F5E8", GREEN, "#9BE3C3"),
            "front": ("#BDB0FF", "#2D1FA0", ACCENT),
            "flip": ("#CFC3FF", "#2D1FA0", ACCENT),
            "wrap": ("#FFE3E5", RED, "#F8B4B8"),
        }
        fill, fg, border = fills[style]
        p.save()
        if sy != 1.0:
            c = rect.center()
            p.translate(c)
            p.scale(1.0, max(0.06, sy))
            p.translate(-c)
        p.setPen(QPen(QColor(border), 1))
        p.setBrush(QColor(fill))
        p.drawRoundedRect(rect, 5, 5)
        p.setPen(QColor(fg))
        p.setFont(self._font)
        p.drawText(rect, Qt.AlignCenter, "1" if bit else "0")
        p.restore()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cw = w / 32.0

        # byte bands
        for b in range(4):
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#F1F2FA" if b % 2 == 0 else "#F7F8FC"))
            p.drawRoundedRect(
                QRectF(b * 8 * cw + 1, 1, 8 * cw - 2, h - 2), 8, 8)

        mode, t = self._mode, self._t
        if mode == "static":
            for i in range(32):
                self._draw_cell(p, i * cw, cw, h, self._bit(self._value, i))

        elif mode == "add":
            k = t * 32.0
            changed = self._from ^ self._to
            for i in range(32):
                q = 31 - i                       # index depuis le bit de poids faible
                resolved = q < k
                bit = self._bit(self._to if resolved else self._from, i)
                style = "normal"
                if resolved and (changed >> q) & 1:
                    style = "changed"
                if int(k) == q and t < 1.0:
                    style = "front"              # le front de la retenue
                self._draw_cell(p, i * cw, cw, h, bit, style)

        elif mode == "xor":
            changed = self._from ^ self._to
            for i in range(32):
                q = 31 - i
                if (changed >> q) & 1:
                    bit = self._bit(self._from if t < 0.5 else self._to, i)
                    sy = abs(math.cos(math.pi * t))
                    self._draw_cell(p, i * cw, cw, h, bit,
                                    "flip" if t < 1 else "changed", sy)
                else:
                    self._draw_cell(p, i * cw, cw, h, self._bit(self._from, i))

        elif mode == "rotl":
            p.setClipRect(QRectF(0, 0, w, h))
            s = self._shift * t
            for i in range(32):
                x = i - s
                style = "wrap" if i < self._shift else "normal"
                bit = self._bit(self._from, i)
                self._draw_cell(p, x * cw, cw, h, bit, style)
                if x < 0:
                    self._draw_cell(p, (x + 32) * cw, cw, h, bit, style)


class RegisterRow(QFrame):
    """Un des 4 mots a, b, c, d du quarter-round."""

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("reg_row")
        self.setProperty("role", "idle")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 12, 6)
        lay.setSpacing(12)

        self.name_label = QLabel(name)
        self.name_label.setObjectName("reg_name")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFixedSize(34, 34)

        self.idx_label = QLabel("x[0]")
        self.idx_label.setObjectName("reg_idx")
        self.idx_label.setFixedWidth(34)

        self.hex_label = QLabel("0x00000000")
        self.hex_label.setObjectName("reg_hex")
        self.hex_label.setFixedWidth(116)

        self.bits = BitRow()
        self.bits.finished.connect(self._refresh_hex)

        lay.addWidget(self.name_label)
        lay.addWidget(self.idx_label)
        lay.addWidget(self.hex_label)
        lay.addWidget(self.bits, 1)

    def _refresh_hex(self):
        self.hex_label.setText(f"0x{self.bits.value():08X}")

    def set_state(self, value: int, index_text: str):
        self.bits.set_value(value)
        self.idx_label.setText(index_text)
        self._refresh_hex()

    def animate(self, kind, before, after, shift, duration):
        self.bits.animate(kind, before, after, shift, duration)

    def set_role(self, role: str):
        if self.property("role") == role:
            return
        self.setProperty("role", role)
        for w in (self, self.name_label):
            w.style().unpolish(w)
            w.style().polish(w)


class StepDots(QWidget):
    """Les 12 opérations d'un quarter-round, cliquables pour sauter à une étape."""
    clicked = Signal(int)
    STEP = 36

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ops, self._tips, self._cur = [], [], 0
        self.setFixedHeight(40)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def set_ops(self, ops, tips):
        self._ops, self._tips = list(ops), list(tips)
        self.setMinimumWidth(len(self._ops) * self.STEP)
        self.update()

    def set_current(self, i):
        self._cur = i
        self.update()

    def sizeHint(self):
        return QSize(len(self._ops) * self.STEP, 40)

    def _index_at(self, x):
        i = int(x // self.STEP)
        return i if 0 <= i < len(self._ops) else -1

    def mouseMoveEvent(self, e):
        i = self._index_at(e.position().x())
        self.setToolTip(self._tips[i] if i >= 0 else "")

    def mousePressEvent(self, e):
        i = self._index_at(e.position().x())
        if i >= 0:
            self.clicked.emit(i)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        symbols = {"ADD": "+", "XOR": "⊕", "ROTL": "↻"}
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSize(11)
        p.setFont(font)
        for i, op in enumerate(self._ops):
            color = QColor(OP_COLORS.get(op, MUTED))
            cx = i * self.STEP + self.STEP / 2
            r = 14 if i == self._cur else 11
            rect = QRectF(cx - r, 20 - r, 2 * r, 2 * r)
            if i == self._cur:
                p.setPen(QPen(color, 3))
                p.setBrush(color)
                glow = QColor(color)
                glow.setAlpha(50)
                p.save()
                p.setPen(Qt.NoPen)
                p.setBrush(glow)
                p.drawEllipse(QRectF(cx - 19, 1, 38, 38))
                p.restore()
                p.setPen(QPen(color.darker(120), 2))
                p.setBrush(color)
                p.drawEllipse(rect)
                p.setPen(Qt.white)
            elif i < self._cur:
                fill = QColor(color)
                fill.setAlpha(190)
                p.setPen(Qt.NoPen)
                p.setBrush(fill)
                p.drawEllipse(rect)
                p.setPen(Qt.white)
            else:
                p.setPen(QPen(color, 2))
                p.setBrush(Qt.white)
                p.drawEllipse(rect)
                p.setPen(color)
            p.drawText(rect, Qt.AlignCenter, symbols.get(op, "?"))


KIND_COLORS = {
    "ancestor": "#8b93a7",
    "birth":    "#4ade80",
    "adoption": "#60a5fa",
    "standard": "#f59e0b",
    "modern":   "#a78bfa",
    "now":      "#f472b6",
}


class TimelineGutter(QWidget):
    """Vertical line + dot, painted so segments join seamlessly between rows."""
    DOT_Y = 24

    def __init__(self, color, first, last, parent=None):
        super().__init__(parent)
        self.setFixedWidth(32)
        self._color = QColor(color)
        self._first = first
        self._last = last

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx = self.width() / 2

        top = self.DOT_Y if self._first else 0
        bottom = self.DOT_Y if self._last else self.height()
        p.setPen(QPen(QColor("#3a3f4b"), 2))
        p.drawLine(QPointF(cx, top), QPointF(cx, bottom))

        p.setPen(Qt.NoPen)
        halo = QColor(self._color)
        halo.setAlpha(60)
        p.setBrush(halo)
        p.drawEllipse(QPointF(cx, self.DOT_Y), 10, 10)
        p.setBrush(self._color)
        p.drawEllipse(QPointF(cx, self.DOT_Y), 6, 6)


class TimelineRow(QWidget):
    def __init__(self, year, name, desc, kind, first=False, last=False, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        year_lbl = QLabel(year)
        year_lbl.setObjectName("timeline_year")
        year_lbl.setFixedWidth(80)
        year_lbl.setAlignment(Qt.AlignRight | Qt.AlignTop)
        # tweak to line up with the dot
        year_lbl.setContentsMargins(0, 14, 8, 0)
        lay.addWidget(year_lbl)

        lay.addWidget(TimelineGutter(
            KIND_COLORS.get(kind, "#8b93a7"), first, last))

        # card + bottom gap (the gap lives here so the gutter line stays continuous)
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0 if last else 14)

        card = QFrame()
        card.setObjectName("timeline_card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(4)
        name_lbl = QLabel(name)
        name_lbl.setObjectName("timeline_name")
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setObjectName("explanation")
        cl.addWidget(name_lbl)
        cl.addWidget(desc_lbl)
        wl.addWidget(card)

        lay.addWidget(wrap, 1)
