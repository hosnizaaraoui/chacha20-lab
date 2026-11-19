from __future__ import annotations
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QSequentialAnimationGroup, QEasingCurve
)
from PySide6.QtWidgets import (
    QWidget, QGraphicsOpacityEffect, QVBoxLayout, QScrollArea, QFrame
)


class BasePage(QWidget):
    """Common scaffolding: a scrollable body + a fixed area below it."""

    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("page")

        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.body = QWidget()
        self.body.setObjectName("page")
        self.layout = QVBoxLayout(self.body)
        self.layout.setContentsMargins(36, 28, 36, 20)
        self.layout.setSpacing(20)

        self.scroll.setWidget(self.body)
        self.outer.addWidget(self.scroll, 1)

    def set_opacity(self, widget, value):
        eff = widget.graphicsEffect()
        if not isinstance(eff, QGraphicsOpacityEffect):
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)
        eff.setOpacity(value)
        return eff

    def fade(self, widget, end, ms, delay=0):
        eff = widget.graphicsEffect()
        if not isinstance(eff, QGraphicsOpacityEffect):
            eff = self.set_opacity(widget, 1.0)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(ms)
        anim.setStartValue(eff.opacity())
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        if not delay:
            return anim
        seq = QSequentialAnimationGroup(self)
        seq.addPause(delay)
        seq.addAnimation(anim)
        return seq
