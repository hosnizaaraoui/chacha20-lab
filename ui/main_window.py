from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QStackedWidget
)
from ui.pages.intro_page import IntroPage
from ui.theme import build_stylesheet
from ui.pages import (
    SimulationPage, AboutPage, UsagesPage, QuizPage, IntroPage
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChaCha20 Lab — Une seule ronde")
        self.resize(1480, 940)
        self.setMinimumSize(1120, 720)

        central = QWidget()
        central.setObjectName("root")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ------------ Sidebar ------------
        self.sidebar = QFrame()
        sidebar = self.sidebar
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(22, 28, 22, 24)
        side.setSpacing(10)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(12)
        logo_img = QLabel("🕵️")
        logo_img.setObjectName("logo_tile")
        logo_img.setAlignment(Qt.AlignCenter)
        logo_img.setFixedSize(52, 52)
        logo_text = QVBoxLayout()
        logo_text.setSpacing(0)
        t1 = QLabel("ChaCha20")
        t1.setObjectName("logo_title")
        t2 = QLabel("Pas à pas")
        t2.setObjectName("logo_sub")
        logo_text.addWidget(t1)
        logo_text.addWidget(t2)
        logo_row.addWidget(logo_img)
        logo_row.addLayout(logo_text)
        logo_row.addStretch()
        side.addLayout(logo_row)
        side.addSpacing(26)

        self.nav_buttons = []
        for name, index in (
            ("▶  Simulation", 1),
            ("🌍  Usages", 2),
            ("🧠  Quiz", 3),
            ("ⓘ  À propos", 4),
        ):
            b = QPushButton(name)
            b.setCheckable(True)
            b.setObjectName("nav")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(
                lambda checked, idx=index: self._switch_page(idx))
            side.addWidget(b)
            self.nav_buttons.append(b)
        self.nav_buttons[0].setChecked(True)

        side.addStretch()

        bubble = QLabel("Prêt à découvrir\nla magie de ChaCha20 ? ✨")
        bubble.setObjectName("bubble")
        bubble.setWordWrap(True)
        bubble.setAlignment(Qt.AlignCenter)
        self.replay_btn = QPushButton("🎬  Rejouer l'intro")
        self.replay_btn.setCursor(Qt.PointingHandCursor)
        self.replay_btn.clicked.connect(self._replay_intro)
        side.addWidget(self.replay_btn)
        side.addWidget(bubble)
        mascot = QLabel("🐧")
        mascot.setAlignment(Qt.AlignCenter)
        mascot.setStyleSheet("font-size: 64px;")
        side.addWidget(mascot)
        self.launch_btn = QPushButton("▶  Lancer la simulation")
        self.launch_btn.setObjectName("launch_btn")
        self.launch_btn.setCursor(Qt.PointingHandCursor)
        self.launch_btn.clicked.connect(self._launch)
        side.addWidget(self.launch_btn)
        root.addWidget(sidebar)

        # ------------ Pages ------------
        self.stacked_widget = QStackedWidget()
        # pages
        self.intro_page = IntroPage(self)
        self.simulation_page = SimulationPage(self)
        self.usages_page = UsagesPage(self)
        self.quiz_page = QuizPage(self)
        self.about_page = AboutPage(self)

        self.stacked_widget.addWidget(self.intro_page)       # 0
        self.stacked_widget.addWidget(self.simulation_page)  # 1
        self.stacked_widget.addWidget(self.usages_page)      # 2
        self.stacked_widget.addWidget(self.quiz_page)        # 3
        self.stacked_widget.addWidget(self.about_page)       # 4

        self.intro_page.finished.connect(self._on_intro_done)

        root.addWidget(self.stacked_widget, 1)
        self.setCentralWidget(central)

        # Cacher la sidebar au démarrage
        self.sidebar.setVisible(False)
        self.stacked_widget.setCurrentIndex(0)
        self.setStyleSheet(build_stylesheet())

    def _on_intro_done(self):
        self.sidebar.setVisible(True)
        self.stacked_widget.setCurrentIndex(1)   # simulation
        self.nav_buttons[0].setChecked(True)

    def _replay_intro(self):
        self.sidebar.setVisible(False)
        self.stacked_widget.setCurrentIndex(0)
        self.intro_page.start()

    def _launch(self):
        self._switch_page(0)
        self.simulation_page.toggle_play()

    def _switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        # On ne coche que les pages 1..3 (la nav)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked((i + 1) == index)

    def closeEvent(self, event):
        self.simulation_page.stop_timers()
        super().closeEvent(event)
