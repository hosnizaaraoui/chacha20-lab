from __future__ import annotations
import random
from PySide6.QtCore import (
    Qt, QTimer, QPoint, QRectF, QPropertyAnimation, QSequentialAnimationGroup,
    QVariantAnimation, QEasingCurve, QAbstractAnimation
)
from PySide6.QtGui import QColor, QPainter, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QProgressBar, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
)
from .questions import QUESTIONS
from ui.theme import ACCENT, ACCENT_DARK, ACCENT_SOFT, GREEN, RED, TEXT, MUTED
from ui.pages.base_page import BasePage

Q_PER_QUIZ = 10


TIME_PER_Q = 20          # seconds per question, 0 = no timer
AMBER = "#F59E0B"
QT_MAX = 16777215


class Confetti(QWidget):
    """Transparent overlay that draws falling confetti."""
    COLORS = [ACCENT, GREEN, AMBER, "#EC4899", "#38BDF8"]

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._parts = []
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._step)
        self.hide()

    def burst(self, n: int = 140):
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()
        w, h = self.width(), self.height()
        for _ in range(n):
            self._parts.append({
                "x": w / 2 + random.uniform(-80, 80),
                "y": h * 0.35,
                "vx": random.uniform(-7, 7),
                "vy": random.uniform(-14, -4),
                "a": random.uniform(0, 360),
                "va": random.uniform(-12, 12),
                "s": random.uniform(6, 11),
                "c": QColor(random.choice(self.COLORS)),
            })
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self._parts.clear()
        self.hide()

    def _step(self):
        h = self.height()
        for p in self._parts:
            p["vy"] += 0.35
            p["vx"] *= 0.99
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["a"] += p["va"]
        self._parts = [p for p in self._parts if p["y"] < h + 20]
        if not self._parts:
            self.stop()
            return
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for c in self._parts:
            p.save()
            p.translate(c["x"], c["y"])
            p.rotate(c["a"])
            s = c["s"]
            p.fillRect(QRectF(-s / 2, -s / 4, s, s / 2), c["c"])
            p.restore()


class QuizPage(BasePage):
    def __init__(self, window, parent=None):
        super().__init__(window, parent)
        self._deck = []
        self._index = 0
        self._score = 0
        self._wrong = 0
        self._streak = 0
        self._selected = None
        self._validated = False
        self._hurry = False
        self._busy = False              # True while the card is flipping
        self._timer_anim = None
        self._timer_color = None
        self._flip_seq = None
        self._flip_widget = None
        self._flip_host = None
        self._coach_key = None
        self._coach_anim = None
        self._build()
        self.confetti = Confetti(self)
        self._install_shortcuts()

    # ------------------------------------------------------------ build
    def _build(self):
        layout = self.layout

        header = QHBoxLayout()
        header.setSpacing(14)
        icon = QLabel("🧠")
        icon.setObjectName("hdr_icon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(48, 48)
        tb = QVBoxLayout()
        tb.setSpacing(2)
        title = QLabel("Quiz ChaCha20")
        title.setObjectName("title")
        sub = QLabel(
            "Testez vos connaissances — 10 questions tirées au hasard")
        sub.setObjectName("muted")
        tb.addWidget(title)
        tb.addWidget(sub)
        header.addWidget(icon)
        header.addLayout(tb)
        header.addStretch()
        layout.addLayout(header)

        top = QHBoxLayout()
        top.setSpacing(16)
        self.score_label = QLabel("Score : 0 / 0")
        self.score_label.setObjectName("section")
        top.addWidget(self.score_label)

        self.streak_label = QLabel("")
        self.streak_label.setStyleSheet(
            f"color:{AMBER}; font-weight:800; font-size:14px;")
        self.streak_label.hide()
        top.addWidget(self.streak_label)
        top.addStretch()

        self.progress = QProgressBar()
        self.progress.setObjectName("quizProgress")
        self.progress.setRange(0, Q_PER_QUIZ)
        self.progress.setValue(0)
        self.progress.setFixedWidth(220)
        self.progress.setFixedHeight(12)
        self.progress.setTextVisible(False)
        top.addWidget(self.progress)
        layout.addLayout(top)

        # ---- two-column area: [ questions 2/3 | coach 1/3 ] -------------
        self.quiz_area = QWidget()
        body = QHBoxLayout(self.quiz_area)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(18)

        # LEFT column -------------------------------------------------
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)

        self.timer_bar = QProgressBar()
        self.timer_bar.setRange(0, 1000)
        self.timer_bar.setValue(1000)
        self.timer_bar.setTextVisible(False)
        self.timer_bar.setFixedHeight(6)
        self.timer_bar.setVisible(bool(TIME_PER_Q))
        ll.addWidget(self.timer_bar)

        # Host that keeps the flipping card centered in the column.
        # Spacers (stretch 1) + card (stretch 1000): when the card's
        # maximumWidth shrinks, the spacers absorb the free space equally.
        self.flip_host = QWidget()
        fh = QHBoxLayout(self.flip_host)
        fh.setContentsMargins(0, 0, 0, 0)
        fh.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("card")
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(32, 28, 32, 28)
        cl.setSpacing(16)

        self.q_number = QLabel("")
        self.q_number.setObjectName("muted")
        cl.addWidget(self.q_number)

        self.q_text = QLabel("")
        self.q_text.setObjectName("quizQuestion")
        self.q_text.setWordWrap(True)
        cl.addWidget(self.q_text)

        self.choices_layout = QVBoxLayout()
        self.choices_layout.setSpacing(10)
        self.choice_buttons = []
        cl.addLayout(self.choices_layout)

        self.feedback = QLabel("")
        self.feedback.setWordWrap(True)
        self.feedback.hide()
        cl.addWidget(self.feedback)

        self.btn_row = QHBoxLayout()
        self.btn_row.setSpacing(10)

        self.validate_btn = QPushButton("Valider ma réponse ✓")
        self.validate_btn.setObjectName("primary")
        self.validate_btn.setCursor(Qt.PointingHandCursor)
        self.validate_btn.setEnabled(False)
        self.validate_btn.clicked.connect(lambda: self._validate())

        self.next_btn = QPushButton("Question suivante →")
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self._next_question)
        self.next_btn.hide()

        self.btn_row.addWidget(self.validate_btn)
        self.btn_row.addWidget(self.next_btn)
        self.btn_row.addStretch()
        cl.addLayout(self.btn_row)

        fh.addStretch(1)
        fh.addWidget(self.card, 1000)
        fh.addStretch(1)

        ll.addWidget(self.flip_host)
        ll.addStretch()

        # RIGHT column: coach panel ------------------------------------
        self.coach = QFrame()
        self.coach.setObjectName("card")
        cc = QVBoxLayout(self.coach)
        cc.setContentsMargins(24, 28, 24, 28)
        cc.setSpacing(14)
        cc.setAlignment(Qt.AlignCenter)

        self.coach_emoji = QLabel("👋")
        self.coach_emoji.setAlignment(Qt.AlignCenter)
        self.coach_emoji.setFixedHeight(88)       # stable while it bounces
        self.coach_emoji.setStyleSheet("font-size: 64px;")
        cc.addWidget(self.coach_emoji)

        self.coach_text = QLabel("")
        self.coach_text.setAlignment(Qt.AlignCenter)
        self.coach_text.setWordWrap(True)
        self.coach_text.setStyleSheet(
            f"color:{TEXT}; font-size:15px; font-weight:700;")
        cc.addWidget(self.coach_text)

        self.coach_stats = QLabel("✅ 0    ❌ 0")
        self.coach_stats.setAlignment(Qt.AlignCenter)
        self.coach_stats.setObjectName("muted")
        cc.addWidget(self.coach_stats)

        body.addWidget(left, 2)
        body.addWidget(self.coach, 1)
        layout.addWidget(self.quiz_area)

        # ---- Result card (replaces both columns) -------------------------
        self.result_card = QFrame()
        self.result_card.setObjectName("resultCard")
        self.result_card.setMaximumWidth(560)
        self.result_card.hide()
        rl = QVBoxLayout(self.result_card)
        rl.setContentsMargins(48, 48, 48, 48)
        rl.setSpacing(18)
        rl.setAlignment(Qt.AlignCenter)

        self.result_emoji = QLabel("🏆")
        self.result_emoji.setAlignment(Qt.AlignCenter)
        self.result_emoji.setFixedHeight(120)
        self.result_emoji.setStyleSheet("font-size: 96px;")
        rl.addWidget(self.result_emoji)

        self.result_title = QLabel("")
        self.result_title.setAlignment(Qt.AlignCenter)
        self.result_title.setWordWrap(True)
        self.result_title.setStyleSheet(
            "font-size: 28px; font-weight: 800; color: #1F1D33;")
        rl.addWidget(self.result_title)

        self.result_pct = QLabel("")
        self.result_pct.setAlignment(Qt.AlignCenter)
        rl.addWidget(self.result_pct)

        self.result_text = QLabel("")
        self.result_text.setAlignment(Qt.AlignCenter)
        self.result_text.setWordWrap(True)
        self.result_text.setObjectName("explanation")
        rl.addWidget(self.result_text)

        self.restart_btn = QPushButton("↺ Recommencer")
        self.restart_btn.setObjectName("primary")
        self.restart_btn.setCursor(Qt.PointingHandCursor)
        self.restart_btn.clicked.connect(self.start_quiz)
        rl.addWidget(self.restart_btn, 0, Qt.AlignCenter)

        layout.addWidget(self.result_card, 0, Qt.AlignCenter)
        layout.addStretch()

    # ------------------------------------------------------------ keyboard
    def _install_shortcuts(self):
        def add(seq, fn):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.WindowShortcut)
            sc.activated.connect(fn)

        for i in range(4):
            add(str(i + 1), lambda i=i: self._select_key(i))
            add(chr(65 + i), lambda i=i: self._select_key(i))
        add("Return", self._enter)
        add("Enter", self._enter)
        add("Up", lambda: self._move(-1))
        add("Down", lambda: self._move(1))

    def _select_key(self, i: int):
        if self.quiz_area.isVisible() and not self._validated \
                and i < len(self.choice_buttons):
            self._select(i)

    def _move(self, delta: int):
        if not self.quiz_area.isVisible() or self._validated \
                or not self.choice_buttons:
            return
        n = len(self.choice_buttons)
        idx = 0 if self._selected is None else (self._selected + delta) % n
        self._select(idx)

    def _enter(self):
        if not self.isVisible() or self._busy:
            return
        if self.result_card.isVisible():
            self.start_quiz()
        elif self._validated:
            self._next_question()
        elif self._selected is not None:
            self._validate()

    # ------------------------------------------------------------ lifecycle
    def showEvent(self, ev):
        super().showEvent(ev)
        if not self._deck:
            QTimer.singleShot(0, self.start_quiz)
        elif self._timer_anim is not None and \
                self._timer_anim.state() == QAbstractAnimation.State.Paused:
            self._timer_anim.resume()

    def hideEvent(self, ev):
        super().hideEvent(ev)
        if self._timer_anim is not None and \
                self._timer_anim.state() == QAbstractAnimation.State.Running:
            self._timer_anim.pause()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if hasattr(self, "confetti"):
            self.confetti.setGeometry(self.rect())

    # ------------------------------------------------------------ flow
    def start_quiz(self):
        self.confetti.stop()
        self._cancel_flip()
        self._stop_timer()
        self._deck = random.sample(QUESTIONS, min(Q_PER_QUIZ, len(QUESTIONS)))
        self._index = 0
        self._score = 0
        self._wrong = 0
        self._streak = 0
        self._selected = None
        self._validated = False
        self._coach_key = None

        self.result_card.hide()
        self.quiz_area.show()
        self.card.setEnabled(True)
        self._update_score()
        self._update_streak()
        self._animate_progress(0)
        self._show_question(first=True)

    def _show_question(self, first: bool = False):
        """Flip the card; the content is swapped when it's edge-on."""
        self._flip(
            self.card, self._column_width(),
            on_mid=self._populate_question,
            host=self.flip_host, shrink=not first)

    def _populate_question(self):
        self._selected = None
        self._validated = False
        self._hurry = False

        q = self._deck[self._index]
        self.q_number.setText(
            f"Question {self._index + 1} / {len(self._deck)}")
        self.q_text.setText(q["q"])
        self.feedback.hide()
        self._update_score()

        self.validate_btn.show()
        self.validate_btn.setEnabled(False)
        self.next_btn.hide()
        self.next_btn.setEnabled(False)
        self.next_btn.setText("Question suivante →")

        for btn in self.choice_buttons:
            self.choices_layout.removeWidget(btn)
            btn.deleteLater()
        self.choice_buttons = []

        for i, choice in enumerate(q["choices"]):
            b = QPushButton(f"{chr(65 + i)}.  {choice}")
            b.setObjectName("quizChoice")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda checked, idx=i: self._select(idx))
            self.choices_layout.addWidget(b)
            self.choice_buttons.append(b)

        self._stagger_in(self.choice_buttons, base=120)
        self._start_timer()
        self._set_coach(*self._coach_idle())

    def _select(self, idx: int):
        if self._validated or self._busy:
            return
        first_pick = self._selected is None
        self._selected = idx
        self.validate_btn.setEnabled(True)

        for i, btn in enumerate(self.choice_buttons):
            if i == idx:
                btn.setStyleSheet(
                    f"background:{ACCENT_SOFT}; border:2px solid {ACCENT};"
                    f"color:{ACCENT_DARK}; border-radius:10px;"
                    "padding:12px 16px; text-align:left; font-weight:700;")
            else:
                btn.setStyleSheet("")
        self._pulse(self.choice_buttons[idx], ACCENT, duration=260, start=22)

        if first_pick and not self._hurry:
            self._set_coach("🤔", "Tu es sûr ? Valide quand tu veux.")

    def _validate(self, timed_out: bool = False):
        if self._validated or self._busy:
            return
        if self._selected is None and not timed_out:
            return
        self._validated = True
        self._stop_timer()

        q = self._deck[self._index]
        correct = q["answer"]
        is_correct = self._selected == correct

        if is_correct:
            self._score += 1
            self._streak += 1
        else:
            self._wrong += 1
            self._streak = 0
        self._update_score()
        self._update_streak()
        if is_correct:
            self._fade_in(self.score_label)

        for btn in self.choice_buttons:
            btn.setEnabled(False)

        for i, btn in enumerate(self.choice_buttons):
            if i == correct:
                btn.setStyleSheet(
                    f"background:{GREEN}22; color:{GREEN}; border:2px solid {GREEN};"
                    "border-radius:10px; padding:12px 16px;"
                    "text-align:left; font-weight:700;")
                self._pulse(btn, GREEN)
            elif i == self._selected and not is_correct:
                btn.setStyleSheet(
                    f"background:{RED}22; color:{RED}; border:2px solid {RED};"
                    "border-radius:10px; padding:12px 16px;"
                    "text-align:left; font-weight:700;")
                self._pulse(btn, RED)
                self._shake(btn)
            else:
                btn.setStyleSheet(
                    "background:#FAFAFE; color:#6B7089;"
                    "border:2px solid #E7E9F2; border-radius:10px;"
                    "padding:12px 16px; text-align:left;")

        no_answer = timed_out and self._selected is None
        if no_answer:
            prefix = "⏱ Temps écoulé !"
        elif is_correct:
            prefix = "✅ Bonne réponse !"
        else:
            prefix = "❌ Mauvaise réponse."
        col = GREEN if is_correct else RED
        self.feedback.setText(f"{prefix}  {q['explain']}")
        self.feedback.setStyleSheet(
            f"color:{col}; background:{col}11; border:1px solid {col}44;"
            "border-radius:10px; padding:12px 16px;"
            "font-size:13px; font-weight:600;")
        self.feedback.show()
        self._fade_in(self.feedback)

        self.validate_btn.hide()
        self.next_btn.show()
        self.next_btn.setEnabled(True)
        if self._index >= len(self._deck) - 1:
            self.next_btn.setText("Voir le résultat →")

        self._set_coach(*self._coach_after(is_correct, no_answer))

    def _next_question(self):
        if self._busy or not self._validated:
            return
        if self._index >= len(self._deck) - 1:
            self._show_result()
            return
        self._index += 1
        self._animate_progress(self._index)
        self._show_question()

    # ------------------------------------------------------------ coach
    def _coach_idle(self):
        if self._index == 0:
            return "👋", "Prêt ? Choisis une réponse puis valide."
        if self._index >= len(self._deck) - 1:
            return "🏁", "Dernière question, donne tout !"
        if self._score > self._wrong:
            return "😎", "Tu es bien parti, continue !"
        if self._score == self._wrong:
            return "🧠", "Concentre-toi, tu peux le faire."
        return "💪", "Accroche-toi, tout est encore possible."

    def _coach_after(self, is_correct: bool, no_answer: bool):
        if no_answer:
            return "⏱", "Temps écoulé ! Lis l'explication."
        if is_correct:
            if self._streak >= 3:
                return "🔥", "Tu es en feu !"
            if self._score > self._wrong:
                return "😎", "Continue comme ça !"
            return "🙂", "Bien joué, tu remontes !"
        if self._score > self._wrong:
            return "💪", "Pas grave, tu mènes encore !"
        if self._score == self._wrong:
            return "🤔", "Égalité… reste concentré."
        return "📚", "Relis l'explication, ça va venir."

    def _set_coach(self, emoji: str, text: str):
        if (emoji, text) == self._coach_key:
            return
        self._coach_key = (emoji, text)
        self.coach_emoji.setText(emoji)
        self.coach_text.setText(text)
        self._fade_in(self.coach_text)

        old = self._coach_anim
        if old is not None:
            old.stop()
            old.deleteLater()
        pop = QVariantAnimation(self)
        pop.setDuration(520)
        pop.setStartValue(30)
        pop.setEndValue(64)
        pop.setEasingCurve(QEasingCurve.OutBack)
        pop.valueChanged.connect(
            lambda v: self.coach_emoji.setStyleSheet(
                f"font-size: {int(v)}px;"))
        self._coach_anim = pop
        pop.start()

    # ------------------------------------------------------------ countdown
    def _start_timer(self):
        self._stop_timer()
        if not TIME_PER_Q:
            return
        self.timer_bar.setValue(1000)
        self._timer_color = None
        self._set_timer_color(GREEN)

        a = QVariantAnimation(self)
        a.setDuration(TIME_PER_Q * 1000)
        a.setStartValue(1000)
        a.setEndValue(0)
        a.setEasingCurve(QEasingCurve.Linear)
        a.valueChanged.connect(self._on_tick)
        a.finished.connect(self._on_timeout)
        self._timer_anim = a
        a.start()

    def _stop_timer(self):
        a = self._timer_anim
        self._timer_anim = None
        if a is not None:
            a.blockSignals(True)
            a.stop()
            a.deleteLater()

    def _on_tick(self, v):
        v = int(v)
        self.timer_bar.setValue(v)
        self._set_timer_color(GREEN if v > 500 else AMBER if v > 200 else RED)
        if v <= 250 and not self._hurry and not self._validated:
            self._hurry = True
            self._set_coach("😰", "Dépêche-toi, le temps file !")

    def _set_timer_color(self, color: str):
        if color == self._timer_color:
            return
        self._timer_color = color
        self.timer_bar.setStyleSheet(
            "QProgressBar{background:#E7E9F2; border:none; border-radius:3px;}"
            f"QProgressBar::chunk{{background:{color}; border-radius:3px;}}")

    def _on_timeout(self):
        self._stop_timer()
        self._validate(timed_out=True)

    # ------------------------------------------------------------ result
    def _show_result(self):
        self._stop_timer()
        self.quiz_area.hide()
        self.result_card.show()

        total = len(self._deck)
        pct = int(self._score * 100 / total)

        if pct == 100:
            emoji, title, color = "🏆", "Parfait !", GREEN
        elif pct >= 80:
            emoji, title, color = "🌟", "Excellent !", GREEN
        elif pct >= 60:
            emoji, title, color = "👍", "Bien joué !", ACCENT_DARK
        elif pct >= 40:
            emoji, title, color = "🙂", "Pas mal !", "#B45309"
        else:
            emoji, title, color = "📚", "À retravailler…", RED

        self.result_emoji.setText(emoji)
        self.result_title.setText(title)
        self.result_pct.setText("0%")
        self.result_pct.setStyleSheet(
            f"font-size: 56px; font-weight: 900; color: {color};")
        self.result_text.setText(
            f"{self._score} / {total} bonnes réponses.\n"
            "Recommencez pour tirer un nouveau jeu de questions.")

        self._flip(self.result_card, 560, shrink=False)
        self._fade_in(self.result_title)

        pop = QVariantAnimation(self)
        pop.setDuration(650)
        pop.setStartValue(20)
        pop.setEndValue(96)
        pop.setEasingCurve(QEasingCurve.OutBack)
        pop.valueChanged.connect(
            lambda v: self.result_emoji.setStyleSheet(
                f"font-size: {int(v)}px;"))
        pop.start(QAbstractAnimation.DeleteWhenStopped)

        cnt = QVariantAnimation(self)
        cnt.setDuration(900)
        cnt.setStartValue(0)
        cnt.setEndValue(pct)
        cnt.setEasingCurve(QEasingCurve.OutCubic)
        cnt.valueChanged.connect(
            lambda v: self.result_pct.setText(f"{int(v)}%"))
        cnt.start(QAbstractAnimation.DeleteWhenStopped)

        if pct >= 80:
            QTimer.singleShot(300, self.confetti.burst)

    # ------------------------------------------------------------ animations
    def _column_width(self) -> int:
        w = self.flip_host.width()
        return w if w > 200 else max(self.width() * 2 // 3, 300)

    def _cancel_flip(self):
        """Abort a running flip and restore the widget (stop() emits no finished)."""
        if self._flip_seq is None:
            return
        self._flip_seq.stop()
        self._flip_seq = None
        w = self._flip_widget
        if w is not None:
            w.setMaximumWidth(w.property("_orig_max") or QT_MAX)
        self._release_host()
        self._busy = False

    def _release_host(self):
        h = self._flip_host
        if h is not None:
            h.setMinimumHeight(0)
            h.setMaximumHeight(QT_MAX)
        self._flip_host = None

    def _flip(self, widget: QWidget, full_w: int, on_mid=None,
              host: QWidget | None = None, shrink: bool = True):
        """Horizontal flip: shrink to 0 width -> on_mid() swaps content -> grow back.
        `host` has its height locked during the flip so nothing jitters."""
        self._cancel_flip()

        orig_max = widget.property("_orig_max")
        if orig_max is None:
            orig_max = widget.maximumWidth()
            widget.setProperty("_orig_max", orig_max)
        widget.setMaximumWidth(orig_max)
        widget.setVisible(True)
        full_w = max(int(full_w), 200)

        self._busy = True
        self._flip_widget = widget
        self._flip_host = host
        if host is not None and shrink and host.height() > 0:
            host.setFixedHeight(host.height())

        def swap():
            if on_mid:
                on_mid()
            if host is not None:
                lay = widget.layout()
                h = lay.totalHeightForWidth(full_w) if lay else -1
                if h <= 0:
                    h = widget.sizeHint().height()
                host.setFixedHeight(h)

        seq = QSequentialAnimationGroup(self)
        if shrink:
            a1 = QPropertyAnimation(widget, b"maximumWidth", self)
            a1.setDuration(180)
            a1.setStartValue(full_w)
            a1.setEndValue(0)
            a1.setEasingCurve(QEasingCurve.InCubic)
            a1.finished.connect(swap)
            seq.addAnimation(a1)
            seq.addPause(20)
        else:
            widget.setMaximumWidth(0)
            swap()

        a2 = QPropertyAnimation(widget, b"maximumWidth", self)
        a2.setDuration(220)
        a2.setStartValue(0)
        a2.setEndValue(full_w)
        a2.setEasingCurve(QEasingCurve.OutCubic)
        seq.addAnimation(a2)

        def done():
            widget.setMaximumWidth(orig_max)
            self._release_host()
            self._flip_seq = None
            self._busy = False

        seq.finished.connect(done)
        self._flip_seq = seq
        seq.start(QAbstractAnimation.DeleteWhenStopped)

    @staticmethod
    def _clear_effect(w: QWidget):
        try:
            w.setGraphicsEffect(None)
        except RuntimeError:        # widget already deleted
            pass

    def _stagger_in(self, widgets, base: int = 120, step: int = 70):
        """Fade choices in one after another."""
        for i, w in enumerate(widgets):
            eff = QGraphicsOpacityEffect(w)
            eff.setOpacity(0.0)
            w.setGraphicsEffect(eff)
            a = QPropertyAnimation(eff, b"opacity", self)
            a.setDuration(300)
            a.setStartValue(0.0)
            a.setEndValue(1.0)
            a.setEasingCurve(QEasingCurve.OutCubic)
            a.finished.connect(lambda w=w: self._clear_effect(w))
            QTimer.singleShot(
                base + i * step,
                lambda a=a: a.start(QAbstractAnimation.DeleteWhenStopped))

    def _shake(self, btn: QPushButton):
        x, y = btn.x(), btn.y()
        anim = QPropertyAnimation(btn, b"pos", self)
        anim.setDuration(380)
        for t, dx in ((0, 0), (0.15, -10), (0.3, 10), (0.45, -8),
                      (0.6, 6), (0.8, -3), (1, 0)):
            anim.setKeyValueAt(t, QPoint(x + dx, y))
        anim.start(QAbstractAnimation.DeleteWhenStopped)

    def _pulse(self, btn: QPushButton, color: str,
               duration: int = 500, start: int = 36):
        if not btn:
            return
        shadow = QGraphicsDropShadowEffect(btn)
        shadow.setBlurRadius(start)
        shadow.setColor(QColor(color))
        shadow.setOffset(0, 0)
        btn.setGraphicsEffect(shadow)
        anim = QPropertyAnimation(shadow, b"blurRadius", self)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: self._clear_effect(btn))
        anim.start(QAbstractAnimation.DeleteWhenStopped)

    def _fade_in(self, widget: QWidget):
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(350)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: self._clear_effect(widget))
        anim.start(QAbstractAnimation.DeleteWhenStopped)

    def _animate_progress(self, target: int):
        anim = QPropertyAnimation(self.progress, b"value", self)
        anim.setDuration(400)
        anim.setStartValue(self.progress.value())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QAbstractAnimation.DeleteWhenStopped)

    # ------------------------------------------------------------ misc
    def _update_score(self):
        answered = self._score + self._wrong
        self.score_label.setText(f"Score : {self._score} / {answered}")
        self.coach_stats.setText(f"✅ {self._score}    ❌ {self._wrong}")

    def _update_streak(self):
        if self._streak >= 2:
            self.streak_label.setText(f"🔥 Série : {self._streak}")
            self.streak_label.show()
            self._fade_in(self.streak_label)
        else:
            self.streak_label.hide()
