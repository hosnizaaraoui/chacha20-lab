from __future__ import annotations
import math
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QRect, QPoint, QSize
)
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QSlider, QTextBrowser, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from core.chacha20 import chacha20_block, chacha20_encrypt, describe_byte_xor
from simulation.controller import SimulationController
from ui.theme import *
from ui.widgets import Card, CollapsibleCard, RegisterRow, StepDots
from ui.settings_panel import SettingsPanel, qr_description
from ui.calc_view import build_calc_html, formula, operand_name
from ui.aes_compare import AesCompareDialog, aes_info_for
from ui.pages.base_page import BasePage

EXPLAIN = {
    "ADD": ("L'addition modulo 2³² ressemble à une addition normale, sauf que si le résultat dépasse "
            "32 bits, le bit en trop disparaît. Les retenues se propagent de droite à gauche : "
            "c'est ce qui rend l'opération non linéaire."),
    "XOR": ("Le XOR compare les bits un par un : identiques → 0, différents → 1. "
            "Chaque 1 de l'opérande inverse le bit correspondant du mot cible."),
    "ROTL": ("La rotation décale tous les bits vers la gauche ; ceux qui sortent à gauche "
             "reviennent à droite. Aucun bit n'est perdu, mais leurs positions changent."),
}
MAX_CHIPS = 16


class SimulationPage(BasePage):
    def __init__(self, window, parent=None):
        super().__init__(window, parent)

        self.key = bytes.fromhex(RFC_KEY)
        self.nonce = bytes.fromhex(RFC_NONCE)
        self.counter = 1
        self.message = DEFAULT_MESSAGE
        self.qr = 1

        self.block = None
        self.events = []
        self._all_events = []         # full 80-QR trace
        self.controller = SimulationController()

        self._token = 0
        self._chips = []
        self._pulse_state = 0

        self.word_colors = []
        self._reset_word_colors()
        self.compare_mode = True
        self.phase = "sim"

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step_forward)
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._animate_pulse)
        self.pulse_timer.start(50)

        self._build()
        self.generate_simulation()
        self._build_message_chips()

    def stop_timers(self):
        self.timer.stop()
        self.pulse_timer.stop()

    # ---------------------------------------------------------------- build
    def _build(self):
        self._build_header()
        self._build_settings()
        self._build_info_bar()
        self._build_machine()
        self._build_calc_and_explain()
        self._build_state_matrix()
        self._build_encryption()
        self._build_controls()

    def _build_header(self):
        header = QHBoxLayout()
        header.setSpacing(14)
        icon = QLabel("💻")
        icon.setObjectName("hdr_icon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(48, 48)
        tb = QVBoxLayout()
        tb.setSpacing(2)
        title = QLabel("ChaCha20 : Un quarter-round en détail")
        title.setObjectName("title")
        desc = QLabel(
            "Regardez les 4 mots a, b, c, d se transformer bit par bit : additions, XOR et rotations ! 🚀")
        desc.setObjectName("muted")
        tb.addWidget(title)
        tb.addWidget(desc)
        header.addWidget(icon)
        header.addLayout(tb)
        header.addStretch()
        self.layout.addLayout(header)

    def _build_settings(self):
        self.settings = SettingsPanel()
        self.settings.applied.connect(self._on_settings_applied)
        self.settings_card = CollapsibleCard(
            "⚙️  Paramètres : clé, nonce, message", self.settings, expanded=False)
        self.layout.addWidget(self.settings_card)

    def _on_settings_applied(self, key, nonce, counter, message, qr):
        self.timer.stop()
        self.play_btn.setText("▶ Lire")
        self.play_btn.setEnabled(True)
        self.key, self.nonce, self.counter, self.message, self.qr = (
            key, nonce, counter, message, qr)
        self.generate_simulation()
        self.settings_card.set_expanded(False)
        self.scroll.verticalScrollBar().setValue(0)

    def _build_info_bar(self):
        info_bar = Card()
        il = QHBoxLayout(info_bar)
        il.setContentsMargins(24, 16, 24, 16)
        il.setSpacing(0)

        def make_info(icon_txt, label):
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(12)
            ic = QLabel(icon_txt)
            ic.setObjectName("stat_icon")
            ic.setAlignment(Qt.AlignCenter)
            ic.setFixedSize(42, 42)
            vb = QVBoxLayout()
            vb.setSpacing(0)
            lb = QLabel(label)
            lb.setObjectName("stat_label")
            vl = QLabel("")
            vl.setObjectName("info_val")
            vb.addWidget(lb)
            vb.addWidget(vl)
            l.addWidget(ic)
            l.addLayout(vb)
            l.addStretch()
            return w, vl

        def vsep():
            s = QFrame()
            s.setObjectName("vsep")
            s.setFixedWidth(1)
            return s

        w1, self.info_input = make_info("📦", "Message")
        w2, self.info_key = make_info("🔑", "Clé (aperçu)")
        w3, self.info_nonce = make_info("🎲", "Nonce (aperçu)")
        w4, self.info_round = make_info("🔄", "Observation")

        for i, w in enumerate((w1, w2, w3, w4)):
            if i:
                il.addSpacing(18)
                il.addWidget(vsep())
                il.addSpacing(18)
            il.addWidget(w, 1)

        # --- QR stepper (navigate the 80 quarter-rounds)
        qr_box = QWidget()
        ql = QHBoxLayout(qr_box)
        ql.setContentsMargins(6, 0, 0, 0)
        ql.setSpacing(4)

        self.qr_label = QLabel("QR 1/80")
        self.qr_label.setObjectName("formula")

        prev_qr = QPushButton("◀")
        prev_qr.setFixedWidth(28)
        prev_qr.setObjectName("prev_qr")
        prev_qr.setCursor(Qt.PointingHandCursor)
        prev_qr.clicked.connect(lambda: self._shift_qr(-1))

        next_qr = QPushButton("▶")
        next_qr.setFixedWidth(28)
        next_qr.setObjectName("next_qr")
        next_qr.setCursor(Qt.PointingHandCursor)
        next_qr.clicked.connect(lambda: self._shift_qr(1))

        ql.addWidget(prev_qr)
        ql.addWidget(next_qr)
        il.addSpacing(12)
        il.addWidget(qr_box)

        edit_btn = QPushButton("✏️  Modifier")
        edit_btn.setObjectName("link_btn")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.clicked.connect(self._open_settings)
        il.addSpacing(8)
        il.addWidget(edit_btn)
        self.layout.addWidget(info_bar)

    def _shift_qr(self, delta):
        new_qr = max(1, min(80, self.qr + delta))
        if new_qr == self.qr:
            return
        self.timer.stop()
        self.play_btn.setText("▶ Lire")
        self.play_btn.setEnabled(True)
        self.qr = new_qr
        self.generate_simulation()

    def _open_settings(self):
        self.settings_card.set_expanded(True)
        self.scroll.ensureWidgetVisible(self.settings_card)

    def _build_machine(self):
        self.machine_card = Card()
        self.fly = QLabel("", self.machine_card)
        self.fly.setObjectName("operand_fly")
        self.fly.setAlignment(Qt.AlignCenter)
        self.fly.hide()
        self._fly_anim = QPropertyAnimation(self.fly, b"geometry", self)
        self._fly_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._fly_anim.finished.connect(self._fly_done)
        self._fly_cb = None

        ml = QVBoxLayout(self.machine_card)
        ml.setContentsMargins(24, 18, 24, 18)
        ml.setSpacing(10)

        top = QHBoxLayout()
        m_title = QLabel("⚙️  La machine en action")
        m_title.setObjectName("section")
        top.addWidget(m_title)
        top.addStretch()
        self.chips_wrap = QWidget()
        cw = QHBoxLayout(self.chips_wrap)
        cw.setContentsMargins(0, 0, 0, 0)
        cw.setSpacing(8)
        self.op_chips = {}
        for op, text in (("ADD", "➕ ADD"), ("XOR", "⊕ XOR"), ("ROTL", "🔄 ROTL")):
            chip = QLabel(text)
            chip.setObjectName("op_chip")
            chip.setProperty("active", "false")
            cw.addWidget(chip)
            self.op_chips[op] = chip
        top.addWidget(self.chips_wrap)
        ml.addLayout(top)

        strip = QWidget()
        strip.setFixedHeight(60)
        sl = QHBoxLayout(strip)
        sl.setContentsMargins(0, 4, 0, 4)
        sl.setSpacing(14)
        cap = QLabel("Message initial")
        cap.setObjectName("stat_label")
        sl.addWidget(cap)
        self.chips_layout = QHBoxLayout()
        self.chips_layout.setSpacing(6)
        sl.addLayout(self.chips_layout)
        sl.addStretch()
        ml.addWidget(strip)

        self.rows_container = QWidget()
        rcl = QVBoxLayout(self.rows_container)
        rcl.setContentsMargins(0, 0, 0, 0)
        rcl.setSpacing(10)
        self.rows = {}
        for name in "abcd":
            row = RegisterRow(name)
            rcl.addWidget(row)
            self.rows[name] = row

        self.dots_wrap = QWidget()
        dl = QHBoxLayout(self.dots_wrap)
        dl.setContentsMargins(4, 4, 0, 0)
        dl.setSpacing(14)
        cap2 = QLabel("Étapes")
        cap2.setObjectName("stat_label")
        self.step_dots = StepDots()
        self.step_dots.clicked.connect(self._seek)
        self.step_label = QLabel("")
        self.step_label.setObjectName("formula")
        dl.addWidget(cap2)
        dl.addWidget(self.step_dots)
        dl.addStretch()
        dl.addWidget(self.step_label)
        rcl.addWidget(self.dots_wrap)
        ml.addWidget(self.rows_container)

        self.result_btn = QPushButton(
            "✨ Voir le résultat final : keystream ⊕ message")
        self.result_btn.setObjectName("primary")
        self.result_btn.setCursor(Qt.PointingHandCursor)
        self.result_btn.clicked.connect(self.show_result_phase)
        self.result_btn.hide()
        ml.addWidget(self.result_btn)

        self.result_panel = QWidget()
        rpl = QVBoxLayout(self.result_panel)
        rpl.setContentsMargins(0, 0, 0, 0)
        rpl.setSpacing(10)
        self.result_msg = QLabel(
            "🔄 En continuant, nous obtiendrons un keystream mélangé par tous les mots : "
            "le message va maintenant être chiffré par XOR avec ce keystream.")
        self.result_msg.setObjectName("takeaway")
        self.result_msg.setWordWrap(True)
        rpl.addWidget(self.result_msg)
        self.result_view = QTextBrowser()
        self.result_view.setMinimumHeight(250)
        rpl.addWidget(self.result_view)
        self.result_panel.hide()
        ml.addWidget(self.result_panel)

        self.layout.addWidget(self.machine_card)

    def _build_calc_and_explain(self):
        middle = QHBoxLayout()
        middle.setSpacing(20)

        calc_card = Card()
        cl = QVBoxLayout(calc_card)
        cl.setContentsMargins(22, 18, 22, 18)
        cl.setSpacing(8)
        c_title = QLabel("🧮  Calcul vertical")
        c_title.setObjectName("section")
        cl.addWidget(c_title)
        self.calc_view = QTextBrowser()
        self.calc_view.setMinimumHeight(250)
        cl.addWidget(self.calc_view, 1)
        middle.addWidget(calc_card, 3)

        expl = QWidget()
        el = QVBoxLayout(expl)
        el.setContentsMargins(0, 0, 0, 0)
        el.setSpacing(10)
        self.op_badge = QLabel("Étape 1")
        self.op_badge.setObjectName("formula")
        el.addWidget(self.op_badge)
        self.explanation = QLabel("...")
        self.explanation.setWordWrap(True)
        self.explanation.setObjectName("explanation")
        el.addWidget(self.explanation)
        self.aes_btn = QPushButton("≈  AES")
        self.aes_btn.setObjectName("aes_btn")
        self.aes_btn.setCursor(Qt.PointingHandCursor)
        self.aes_btn.clicked.connect(self._open_aes)
        el.addWidget(self.aes_btn)
        el.addStretch()
        self.expl_card = CollapsibleCard(
            "💡  Explication de l'étape", expl, expanded=True)
        middle.addWidget(self.expl_card, 2, Qt.AlignTop)
        self.layout.addLayout(middle)
        self.expl_card.setMinimumHeight(310)

    def _build_state_matrix(self):
        matrix_card = Card()
        ml = QVBoxLayout(matrix_card)
        ml.setContentsMargins(22, 18, 22, 18)
        ml.setSpacing(10)

        m_header = QHBoxLayout()
        m_title = QLabel("🔲  Matrice d'État — mélange des mots")
        m_title.setObjectName("section")
        m_header.addWidget(m_title)
        m_header.addStretch()
        self.compare_btn = QPushButton("Vue comparative")
        self.compare_btn.setObjectName("link_btn")
        self.compare_btn.setCheckable(True)
        self.compare_btn.setCursor(Qt.PointingHandCursor)
        self.compare_btn.clicked.connect(self._toggle_compare)
        m_header.addWidget(self.compare_btn)
        ml.addLayout(m_header)

        matrix_container = QWidget()
        matrix_layout = QHBoxLayout(matrix_container)
        matrix_layout.setContentsMargins(0, 0, 0, 0)
        matrix_layout.setSpacing(14)

        self.table_before = self._make_matrix_table()
        self.table_after = self._make_matrix_table()
        self.lbl_before = QLabel("AVANT")
        self.lbl_before.setAlignment(Qt.AlignCenter)
        self.lbl_before.setObjectName("muted")
        self.lbl_after = QLabel("APRÈS")
        self.lbl_after.setAlignment(Qt.AlignCenter)
        self.lbl_after.setObjectName("muted")

        matrix_layout.addWidget(self.lbl_before)
        matrix_layout.addWidget(self.table_before, 1)
        matrix_layout.addWidget(self.lbl_after)
        matrix_layout.addWidget(self.table_after, 1)
        ml.addWidget(matrix_container)

        legend = QHBoxLayout()
        legend.addWidget(QLabel("Légende :"))
        for text, color in (("Constant", MATRIX_CONSTANT), ("Key", MATRIX_KEY),
                            ("Counter", MATRIX_COUNTER), ("Nonce", MATRIX_NONCE)):
            lbl = QLabel(f"■ {text}")
            lbl.setStyleSheet(
                f"color:{color}; font-weight:bold; margin-right:15px;")
            legend.addWidget(lbl)
        legend.addStretch()
        ml.addLayout(legend)
        self.layout.addWidget(matrix_card)

    def _make_matrix_table(self):
        t = QTableWidget(4, 4)
        t.setObjectName("stateMatrix")
        t.horizontalHeader().setVisible(False)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionMode(QTableWidget.NoSelection)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setFocusPolicy(Qt.NoFocus)
        t.setMinimumHeight(190)
        t.setShowGrid(True)
        t.setFrameShape(QFrame.NoFrame)
        return t

    def _build_encryption(self):
        self.enc_view = QTextBrowser()
        self.enc_view.setMinimumHeight(230)
        self.enc_card = CollapsibleCard(
            "🔒  Chiffrement du message : lettre ⊕ keystream", self.enc_view, expanded=True)
        self.layout.addWidget(self.enc_card)

    def _build_controls(self):
        dock = QWidget()
        dock.setObjectName("controlsDock")
        wl = QVBoxLayout(dock)

        controls = Card()
        cl2 = QHBoxLayout(controls)
        cl2.setContentsMargins(20, 14, 20, 14)
        cl2.setSpacing(10)

        self.prev_btn = QPushButton("← Précédent")
        self.prev_btn.clicked.connect(self.step_backward)
        self.play_btn = QPushButton("▶ Lire")
        self.play_btn.setObjectName("play_btn")
        self.play_btn.clicked.connect(self.toggle_play)
        self.next_btn = QPushButton("Suivant →")
        self.next_btn.clicked.connect(self.step_forward)
        self.restart_btn = QPushButton("↺ Recommencer")
        self.restart_btn.clicked.connect(self._restart_sim)

        for b in (self.prev_btn, self.play_btn, self.next_btn, self.restart_btn):
            b.setCursor(Qt.PointingHandCursor)
            cl2.addWidget(b)
        cl2.addStretch()

        cl2.addWidget(QLabel("⏱ Vitesse"))
        self.speed = QSlider(Qt.Horizontal)
        self.speed.setRange(1, 20)
        self.speed.setValue(5)
        self.speed.setFixedWidth(160)
        self.speed.valueChanged.connect(self._speed_changed)
        cl2.addWidget(self.speed)

        self.speed_value = QLabel("1.0x")
        self.speed_value.setObjectName("info_val")
        cl2.addWidget(self.speed_value)

        wl.addWidget(controls)
        self.outer.addWidget(dock, 0)

    # ------------------------------------------------------ Simulation core
    def _reset_word_colors(self):
        self.word_colors = [QColor(MATRIX_CONSTANT) for _ in range(4)] + \
                           [QColor(MATRIX_KEY) for _ in range(8)] + \
                           [QColor(MATRIX_COUNTER)] + \
                           [QColor(MATRIX_NONCE) for _ in range(3)]

    def _toggle_compare(self):
        self.compare_mode = self.compare_btn.isChecked()
        self.lbl_before.setVisible(self.compare_mode)
        self.table_before.setVisible(self.compare_mode)
        self.lbl_after.setVisible(True)
        self.table_after.setVisible(True)
        self.render_current(animate=False)

    def _update_word_colors(self, event):
        op = event["operation"]
        ind = event["indices"]
        if op not in ("ADD", "XOR"):
            return
        if op == "ADD":
            source, target = ind["b"], ind["a"]
        else:
            source = ind["a"] if event["target"] == "d" else ind["c"]
            target = ind["d"] if event["target"] == "d" else ind["b"]
        c1, c2 = self.word_colors[source], self.word_colors[target]
        mixed = QColor((c1.red() + c2.red()) // 2,
                       (c1.green() + c2.green()) // 2,
                       (c1.blue() + c2.blue()) // 2)
        self.word_colors[target] = mixed

    def _populate_matrix(self, table, state, active_indices):
        for i, val in enumerate(state):
            row, col = i // 4, i % 4
            item = QTableWidgetItem(f"0x{val:08X}")
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QBrush(self.word_colors[i]))
            font = QFont("monospace")
            font.setPointSize(10)
            if i in active_indices:
                item.setBackground(QBrush(QColor(108, 77, 255, 45)))
                font.setBold(True)
            item.setFont(font)
            table.setItem(row, col, item)

    def generate_simulation(self):
        try:
            # 1) Generate the full trace once
            self.block = chacha20_block(
                self.key, self.counter, self.nonce, trace=True)
            self._all_events = self.block.events

            # 2) Slice the events for the selected QR
            start = (self.qr - 1) * 12
            end = self.qr * 12
            self.events = self._all_events[start:end]
            self.controller.set_events(self.events)

            # 3) Step dots + tips
            tips = [
                f"Étape {i + 1} : {formula(e)}"
                for i, e in enumerate(self.events)
            ]
            self.step_dots.set_ops(
                [e["operation"] for e in self.events], tips)

            # 4) Reset per-step state
            self._reset_word_colors()
            self._update_info()

            # 5) Render from step 0
            self.controller.seek(0)
            self.render_current(animate=False)
            self._update_encryption()

            # 6) Restore sim phase
            self.phase = "sim"
            self.rows_container.show()
            self.result_btn.hide()
            self.result_panel.hide()
            self.chips_wrap.show()
            self._build_message_chips()
            self.play_btn.setEnabled(True)
        except Exception as exc:
            QMessageBox.warning(self, "Erreur", str(exc))

    def _update_info(self):
        msg = self.message
        preview = msg if len(msg) <= 12 else msg[:11] + "…"
        self.info_input.setText(f"« {preview} »")
        self.info_input.setToolTip(
            f"{msg}  ({len(msg.encode('utf-8'))} octets)")
        for lbl, data in ((self.info_key, self.key), (self.info_nonce, self.nonce)):
            h = data.hex()
            lbl.setText(f"{h[:6]}…{h[-4:]}")
            lbl.setToolTip(h)
        self.info_round.setText(f"QR {self.qr}/80 · {qr_description(self.qr)}")
        if hasattr(self, "qr_label"):
            self.qr_label.setText(f"QR {self.qr}/80")

    def _update_encryption(self):
        msg = self.message.encode("utf-8")
        ks = b"".join(
            chacha20_block(self.key, self.counter + i, self.nonce).keystream
            for i in range((len(msg) + 63) // 64)
        )
        rows = describe_byte_xor(msg, ks)
        cipher = bytes(r["cipher"] for r in rows)

        # Patch the first keystream byte from the current QR's live x[0]
        live = bool(self.events)
        if live:
            last_state = self.events[-1]["state"]
            live_x0 = last_state[0]
            initial_x0 = self.block.initial[0]
            x0_out = (initial_x0 + live_x0) & 0xFFFFFFFF
            live_byte = x0_out & 0xFF
            if rows:
                r0 = rows[0]
                r0["key"] = live_byte
                r0["cipher"] = r0["plain"] ^ live_byte
                r0["key_hex"] = f"0x{live_byte:02X}"
                r0["cipher_hex"] = f"0x{r0['cipher']:02X}"
                cipher = bytes(r["cipher"] for r in rows)

        def ch(b: int) -> str:
            return "␣" if b == 32 else (chr(b) if 33 <= b < 127 else "·")

        shown = rows[:MAX_CHIPS]
        extra = len(rows) - len(shown)

        mono = "'JetBrains Mono','Consolas',monospace"
        sans = "'Inter','Segoe UI',sans-serif"
        gap = '<p style="margin:0; font-size:8px;">&nbsp;</p>'

        def card(inner: str, bg: str = "#FFFFFF", border: str = BORDER) -> str:
            return (
                f'<table width="100%" cellspacing="0" cellpadding="14" '
                f'style="background-color:{bg}; border:1px solid {border};">'
                f"<tr><td>{inner}</td></tr></table>"
            )

        # ── 1. En-tête : titre + badge QR ───────────────────────────────────
        header = f"""
        <table width="100%" cellspacing="0" cellpadding="0"><tr>
          <td style="font-family:{sans}; font-size:15px; font-weight:800; color:{TEXT};">
            🔐&nbsp; Keystream ⊕ Message → Chiffré
          </td>
        </tr></table>
        <p style="margin:8px 0 0 0; font-family:{sans}; font-size:12px; color:{MUTED};">
          Chaque octet du message est combiné par XOR avec l'octet correspondant du keystream.
        </p>
        """

        # ── 2. Grille des octets ────────────────────────────────────────────
        def grid_row(icon, label, cells, bg, fg, size=14, bold=False):
            weight = "800" if bold else "600"
            out = (
                f'<td align="right" style="padding:0 10px 0 0; color:{MUTED}; font-family:{sans};'
                f' font-size:11px; font-weight:800; white-space:nowrap;">{icon}&nbsp;{label}</td>'
            )
            for i, c in enumerate(cells):
                edge = ORANGE if (live and i == 0) else bg
                out += (
                    f'<td align="center" bgcolor="{bg}" style="background-color:{bg}; color:{fg};'
                    f" font-family:{mono}; font-size:{size}px; font-weight:{weight};"
                    f' padding:8px 10px; border:2px solid {edge};">{c}</td>'
                )
            return f"<tr>{out}</tr>"

        grid = '<table cellspacing="5" cellpadding="0">'
        grid += grid_row("📝", "LETTRE", [ch(r["plain"]) for r in shown],
                         ACCENT_SOFT, ACCENT_DARK, size=17, bold=True)
        grid += grid_row("&nbsp;", "CLAIR", [r["plain_hex"][2:] for r in shown],
                         "#F3F4F8", TEXT)
        grid += grid_row("⊕", "KEYSTREAM", [r["key_hex"][2:] for r in shown],
                         "#E8F0FF", "#1D4ED8")
        grid += grid_row("=", "CHIFFRÉ", [r["cipher_hex"][2:] for r in shown],
                         ACCENT, "#FFFFFF", bold=True)
        grid += "</table>"
        if extra:
            grid += (f'<p style="margin:6px 0 0 0; font-family:{sans}; font-size:12px; '
                     f'color:{MUTED};">… +{extra} octets non affichés</p>')

        # ── 3. Ciphertext complet ───────────────────────────────────────────
        hexstr = cipher.hex()
        spaced = " ".join(hexstr[i:i + 2] for i in range(0, len(hexstr), 2))
        cipher_box = f"""
        <p style="margin:0 0 8px 0; font-family:{sans}; font-size:11px; font-weight:800; color:{MUTED};">
          CIPHERTEXT COMPLET · {len(cipher)} OCTETS
        </p>
        <table width="100%" cellspacing="0" cellpadding="10"
               style="background-color:#F8F9FC; border:1px solid {BORDER};"><tr>
          <td style="font-family:{mono}; font-size:14px; font-weight:700; color:{ACCENT_DARK};">
            {spaced}
          </td>
        </tr></table>
        """

        # ── 4. Note déchiffrement ───────────────────────────────────────────
        note = f"""
        <p style="margin:0; font-family:{sans}; font-size:13px; color:{ACCENT_DARK};">
          💡&nbsp; Le déchiffrement utilise <b>les mêmes opérations</b> (XOR avec le même keystream).
          <span style="color:{TEXT_SOFT}; font-weight:400;">Le keystream provient du bloc complet de
          20 rondes ; la machine ci-dessus montre un seul quarter-round de ce calcul.</span>
        </p>
        """

        html = (
            card(header) + gap
            + card(grid) + gap
            + card(cipher_box) + gap
            + card(note, bg=ACCENT_SOFT, border=ACCENT_BORDER)
        )
        self.enc_view.setHtml(html)
        self.result_view.setHtml(html)

    def _build_message_chips(self):
        for chip in self._chips:
            self.chips_layout.removeWidget(chip)
            chip.deleteLater()
        self._chips = []
        text = self.message
        for ch in text[:MAX_CHIPS]:
            chip = QLabel("␣" if ch == " " else ch)
            chip.setObjectName("chip_space" if ch == " " else "chip")
            chip.setAlignment(Qt.AlignCenter)
            chip.setFixedSize(38, 46)
            self.chips_layout.addWidget(chip)
            self._chips.append(chip)
        if len(text) > MAX_CHIPS:
            more = QLabel(f"+{len(text) - MAX_CHIPS}")
            more.setObjectName("muted")
            self.chips_layout.addWidget(more)
            self._chips.append(more)

    def _animate_pulse(self):
        self._pulse_state = (self._pulse_state + 1) % 60
        pulse = (math.sin(self._pulse_state * math.pi / 30) + 1) / 2
        r = int(108 + (164 - 108) * pulse)
        g = int(77 + (140 - 77) * pulse)
        color = f"rgb({r}, {g}, 255)"
        cur = self.controller.current
        active = cur["operation"] if cur else None
        for op, chip in self.op_chips.items():
            style = f"border:2px solid {color};" if op == active else ""
            if chip.property("_s") != style:
                chip.setProperty("_s", style)
                chip.setStyleSheet(style)

        if cur and hasattr(self, "table_after"):
            alpha = int(30 + 40 * pulse)
            for table in (getattr(self, "table_before", None),
                          getattr(self, "table_after", None)):
                if not table or not table.isVisible():
                    continue
                for i in cur["indices"].values():
                    item = table.item(i // 4, i % 4)
                    if item:
                        item.setBackground(QBrush(QColor(108, 77, 255, alpha)))

    def _set_active_chip(self, op):
        for k, chip in self.op_chips.items():
            val = "true" if k == op else "false"
            if chip.property("active") != val:
                chip.setProperty("active", val)
                chip.style().unpolish(chip)
                chip.style().polish(chip)

    def _anim_ms(self):
        return max(180, min(1100, int(self._step_interval() * 0.7)))

    def _step_interval(self):
        return int(1600 / (self.speed.value() / 5))

    def render_current(self, animate=True):
        event = self.controller.current
        if not event:
            return
        self._token += 1
        token = self._token
        self._fly_anim.stop()
        self.fly.hide()
        self._fly_cb = None

        idx, total = self.controller.index, self.controller.total
        op, tgt = event["operation"], event["target"]
        src = operand_name(event)
        ind, state = event["indices"], event["state"]

        for name in "abcd":
            row = self.rows[name]
            after = state[ind[name]]
            row.set_state(event["before"] if name == tgt else after,
                          f"x[{ind[name]}]")
            row.set_role("target" if name == tgt else (
                "source" if name == src else "idle"))

        self._set_active_chip(op)
        self.step_dots.set_current(idx)
        self.step_label.setText(f"{idx + 1}/{total}  {formula(event)}")
        self.op_badge.setText(f"Étape {idx + 1}/{total} · {formula(event)}")
        self.explanation.setText(f"{EXPLAIN.get(op, event['explanation'])}")
        self.calc_view.setHtml(build_calc_html(event))

        info = aes_info_for(event)
        names = {"direct": "≈  Équivalent AES",
                 "partial": "≈  Proche d'AES",
                 "none": "ⓘ  Pas d'équivalent AES"}
        self.aes_btn.setText(
            f"{names[info['level']]} : {info['aes_name'].split(' (')[0]}\n"
            "Voir la différence ➜")

        self._update_word_colors(event)
        active_idx = set(ind.values())
        if self.compare_mode:
            state_before = list(event["state"])
            state_before[ind[tgt]] = event["before"]
            self._populate_matrix(self.table_before, state_before, active_idx)
            self._populate_matrix(self.table_after, event["state"], active_idx)
        else:
            self._populate_matrix(self.table_after, event["state"], active_idx)

        if animate:
            self._play_step_animation(event, token, src)
        else:
            self.rows[tgt].set_state(event["after"], f"x[{ind[tgt]}]")

        self.prev_btn.setEnabled(idx > 0)
        self.next_btn.setEnabled(idx < total - 1)
        if idx == total - 1:
            self.timer.stop()
            self.play_btn.setText("▶ Lire")
            self.result_btn.show()
        elif self.timer.isActive():
            self.play_btn.setText("⏸ Pause")
        else:
            self.play_btn.setText("▶ Lire")

    def _play_step_animation(self, event, token, src):
        op, tgt = event["operation"], event["target"]
        row = self.rows[tgt]
        dur = self._anim_ms()
        kind = {"ADD": "add", "XOR": "xor", "ROTL": "rotl"}[op]

        def run_bits():
            if token != self._token:
                return
            rot = int(event.get("rotation") or 0)
            row.animate(kind, int(event["before"]), int(event["after"]),
                        rot, int(dur * 0.65))

        if op in ("ADD", "XOR") and src:
            self._fly_operand(src, tgt, event, int(
                dur * 0.35), run_bits, token)
        else:
            run_bits()

    def _fly_operand(self, src, tgt, event, ms, done, token):
        a = self.rows[src].hex_label
        b = self.rows[tgt].hex_label
        size = QSize(150, 30)
        start = QRect(a.mapTo(self.machine_card, QPoint(-4, 0)), size)
        end = QRect(b.mapTo(self.machine_card, QPoint(-4, 0)), size)
        sym = "+" if event["operation"] == "ADD" else "⊕"
        self.fly.setText(f"{sym} 0x{event['operands'][src]:08X}")
        self.fly.setGeometry(start)
        self.fly.show()
        self.fly.raise_()
        self._fly_cb = done
        self._fly_anim.setDuration(max(80, ms))
        self._fly_anim.setStartValue(start)
        self._fly_anim.setEndValue(end)
        self._fly_anim.start()

    def _fly_done(self):
        self.fly.hide()
        cb, self._fly_cb = self._fly_cb, None
        if cb:
            cb()

    def show_result_phase(self):
        if self.phase == "result":
            return
        self.phase = "result"
        self.timer.stop()
        self._token += 1

        self.rows_container.hide()
        self.chips_wrap.hide()
        self.result_btn.hide()
        self.result_panel.show()

        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.play_btn.setText("▶ Lire")

    def _restart_sim(self):
        self.timer.stop()
        self.controller.reset()
        self.phase = "sim"
        self.rows_container.show()
        self.chips_wrap.show()
        self.result_btn.hide()
        self.result_panel.hide()
        self.play_btn.setEnabled(True)
        self._build_message_chips()
        self.generate_simulation()

    def step_forward(self):
        if self.controller.index < self.controller.total - 1:
            self.controller.next()
            self.render_current()
        else:
            self.timer.stop()

    def step_backward(self):
        self.timer.stop()
        self.controller.previous()
        self.render_current()

    def _seek(self, index):
        self.timer.stop()
        self.controller.seek(index)
        self.render_current()

    def toggle_play(self):
        if self.phase == "result":
            self._restart_sim()
        if self.timer.isActive():
            self.timer.stop()
            self.play_btn.setText("▶ Lire")
        else:
            if self.controller.index >= self.controller.total - 1:
                self.controller.reset()
                self.render_current()
                self.result_btn.hide()
            self.timer.start(self._step_interval())
            self.play_btn.setText("⏸ Pause")

    def _speed_changed(self, value):
        self.speed_value.setText(f"{value / 5:.1f}x")
        if self.timer.isActive():
            self.timer.setInterval(self._step_interval())

    def _open_aes(self):
        event = self.controller.current
        if not event:
            return
        self.timer.stop()
        self.play_btn.setText("▶ Lire")
        AesCompareDialog(event, self).exec()
