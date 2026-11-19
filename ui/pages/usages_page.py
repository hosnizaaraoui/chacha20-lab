from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QDialog, QScrollArea
)
from ui.widgets import Card
from ui.pages.base_page import BasePage
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtGui import QColor


USAGES = [
    {
        "id": 1,
        "title": "VPN : WireGuard",
        "short": "ChaCha20-Poly1305 est le chiffrement imposé par WireGuard.",
        "full": "WireGuard utilise ChaCha20-Poly1305 pour chiffrer et authentifier chaque paquet du tunnel, avec une suite cryptographique fixe plutôt que négociable. Cela réduit la surface d'attaque et donne de bonnes performances sur CPU sans accélération AES.",
        "projects": ["WireGuard", "Tailscale", "Mullvad VPN", "NordLynx (NordVPN)", "OpenVPN 2.5+"],
    },
    {
        "id": 2,
        "title": "HTTPS / TLS 1.3",
        "short": "Suite TLS_CHACHA20_POLY1305_SHA256 définie par le standard TLS 1.3.",
        "full": "ChaCha20-Poly1305 fait partie des suites de chiffrement de TLS 1.3 (RFC 8446, spécifié dans la RFC 8439). Les navigateurs et serveurs la choisissent surtout quand le client n'a pas d'accélération matérielle AES, comme certains smartphones d'entrée de gamme.",
        "projects": ["Google Chrome", "Firefox", "Cloudflare", "OpenSSL", "BoringSSL", "Go (crypto/tls)", "rustls"],
    },
    {
        "id": 3,
        "title": "HTTP/3 et QUIC",
        "short": "Chiffrement des paquets QUIC, qui forment la base de HTTP/3.",
        "full": "QUIC s'appuie sur TLS 1.3 et peut donc utiliser ChaCha20-Poly1305 pour chiffrer ses paquets. ChaCha20 sert aussi à la protection des en-têtes de paquets dans QUIC.",
        "projects": ["Google (QUIC)", "Cloudflare quiche", "quic-go", "msquic (Microsoft)"],
    },
    {
        "id": 4,
        "title": "Connexions SSH",
        "short": "chacha20-poly1305@openssh.com, chiffrement moderne d'OpenSSH.",
        "full": "OpenSSH propose le chiffrement chacha20-poly1305@openssh.com pour protéger les sessions distantes, et il est placé en tête des préférences par défaut depuis OpenSSH 6.9. Il protège les commandes, les transferts de fichiers et les tunnels.",
        "projects": ["OpenSSH", "Dropbear", "libssh"],
    },
    {
        "id": 5,
        "title": "Générateur aléatoire du noyau Linux",
        "short": "ChaCha20 alimente /dev/urandom et getrandom().",
        "full": "Depuis Linux 4.8, le générateur de nombres pseudo-aléatoires du noyau est basé sur ChaCha20. Il produit les clés, nonces et valeurs aléatoires utilisés par tout le système.",
        "projects": ["Noyau Linux (/dev/urandom, getrandom)", "OpenBSD (arc4random)", "Rust rand (StdRng)"],
    },
    {
        "id": 6,
        "title": "Chiffrement de fichiers",
        "short": "L'outil age utilise ChaCha20-Poly1305 pour chiffrer fichiers et archives.",
        "full": "L'outil age, conçu comme une alternative simple à GPG, chiffre les fichiers avec ChaCha20-Poly1305. Les bibliothèques libsodium et Tink proposent aussi des chiffrements AEAD de la famille ChaCha20 pour les applications.",
        "projects": ["age", "libsodium (XChaCha20-Poly1305)", "Google Tink", "Rclone crypt (XSalsa20)"],
    },
    {
        "id": 7,
        "title": "Chiffrement de disque Android",
        "short": "Adiantum chiffre le stockage des téléphones sans accélération AES.",
        "full": "Google a conçu Adiantum, basé sur XChaCha12 et AES, pour chiffrer le stockage des appareils Android d'entrée de gamme dépourvus d'instructions AES matérielles. Il est intégré au noyau Linux.",
        "projects": ["Android (Adiantum)", "Noyau Linux (fscrypt, dm-crypt)"],
    },
    {
        "id": 8,
        "title": "Protocole Noise",
        "short": "Framework de handshakes sécurisés avec ChaChaPoly comme option.",
        "full": "Le Noise Protocol Framework permet de construire des protocoles de communication sécurisés, avec ChaCha20-Poly1305 comme l'un de ses chiffrements standards. WireGuard et le Lightning Network s'en servent.",
        "projects": ["WireGuard", "Lightning Network (BOLT 8)", "libp2p (Noise)"],
    },
    {
        "id": 9,
        "title": "Réseaux pair-à-pair",
        "short": "Chiffrement des canaux entre nœuds décentralisés.",
        "full": "Plusieurs projets décentralisés l'utilisent pour sécuriser les connexions entre nœuds. Le Lightning Network chiffre ses messages avec ChaCha20-Poly1305 via Noise, et libp2p propose Noise ainsi que TLS 1.3 (donc ChaCha20-Poly1305) comme transports sécurisés.",
        "projects": ["Lightning Network", "libp2p (IPFS, Ethereum 2.0)"],
    },
    {
        "id": 10,
        "title": "Bibliothèques crypto",
        "short": "Disponible dans les bibliothèques que les développeurs utilisent tous les jours.",
        "full": "ChaCha20-Poly1305 est implémenté dans les bibliothèques cryptographiques majeures, ce qui permet de l'utiliser dans tout type d'application (API, messagerie, stockage) sans réimplémenter l'algorithme.",
        "projects": ["OpenSSL", "libsodium", "BoringSSL", "Go x/crypto", "RustCrypto", "Python cryptography"],
    },
]


class UsageCard(QFrame):
    """Carte cliquable pour un usage. Émet un signal via .clicked callback."""

    def __init__(self, data: dict, on_click, parent=None):
        super().__init__(parent)
        self.setObjectName("usageCard")
        self.setCursor(Qt.PointingHandCursor)
        self._on_click = on_click
        self._data = data

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        title = QLabel(data["title"])
        title.setObjectName("usageTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        short = QLabel(data["short"])
        short.setObjectName("usageShort")
        short.setWordWrap(True)
        layout.addWidget(short)

        # Projets tags
        tags = QHBoxLayout()
        tags.setSpacing(6)
        tags.setContentsMargins(0, 4, 0, 0)
        for name in data["projects"][:3]:
            tag = QLabel(name)
            tag.setObjectName("usageTag")
            tags.addWidget(tag)
        if len(data["projects"]) > 3:
            more = QLabel(f"+{len(data['projects']) - 3}")
            more.setObjectName("usageTagMore")
            tags.addWidget(more)
        tags.addStretch()
        layout.addLayout(tags)

        hint = QLabel("Cliquer pour en savoir plus →")
        hint.setObjectName("usageHint")
        layout.addWidget(hint)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._on_click(self._data)
        super().mousePressEvent(ev)


class UsageDialog(QDialog):
    """Modale affichant la description complète d'un usage."""

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(data["title"])
        self.setMinimumSize(620, 420)
        self.resize(700, 460)

        # Le QDialog lui-même garde le fond normal (BG = #F5F6FB)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(0)

        # Conteneur arrondi blanc
        self.card = QFrame()
        self.card.setObjectName("usageDialogCard")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(shadow)

        outer.addWidget(self.card)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel(data["title"])
        title.setObjectName("usageDialogTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        body = QWidget()
        body.setObjectName("usageDialogBody")
        body.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(12)

        full = QLabel(data["full"])
        full.setWordWrap(True)
        full.setObjectName("usageDialogText")
        bl.addWidget(full)

        proj_title = QLabel("Utilisé par")
        proj_title.setObjectName("usageDialogSubTitle")
        bl.addWidget(proj_title)

        for name in data["projects"]:
            row = QLabel(f"•  {name}")
            row.setObjectName("usageDialogText")
            bl.addWidget(row)

        bl.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        close = QPushButton("Fermer")
        close.setObjectName("link_btn")
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.accept)
        row_btn = QHBoxLayout()
        row_btn.addStretch()
        row_btn.addWidget(close)
        layout.addLayout(row_btn)


class UsagesPage(BasePage):
    def __init__(self, window, parent=None):
        super().__init__(window, parent)
        self._build()

    def _build(self):
        # Header
        header = QHBoxLayout()
        header.setSpacing(14)
        icon = QLabel("🌍")
        icon.setObjectName("hdr_icon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(48, 48)
        tb = QVBoxLayout()
        tb.setSpacing(2)
        title = QLabel("Usages de ChaCha20")
        title.setObjectName("title")
        subtitle = QLabel(
            "Où et comment ChaCha20 est-il utilisé dans le monde réel ? Clique sur une carte pour voir la description complète."
        )
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        tb.addWidget(title)
        tb.addWidget(subtitle)
        header.addWidget(icon)
        header.addLayout(tb)
        header.addStretch()
        self.layout.addLayout(header)

        # Grid of cards (2 columns)
        grid = QHBoxLayout()
        grid.setSpacing(16)
        col_left = QVBoxLayout()
        col_right = QVBoxLayout()
        col_left.setSpacing(16)
        col_right.setSpacing(16)

        for i, data in enumerate(USAGES):
            card = UsageCard(data, self._open_dialog)
            shadow = QGraphicsDropShadowEffect(card)
            shadow.setBlurRadius(32)
            shadow.setColor(QColor(0, 0, 0, 25))
            shadow.setOffset(0, 6)
            card.setGraphicsEffect(shadow)
            if i % 2 == 0:
                col_left.addWidget(card)
            else:
                col_right.addWidget(card)

        grid.addLayout(col_left, 1)
        grid.addLayout(col_right, 1)
        self.layout.addLayout(grid)
        self.layout.addStretch()

    def _open_dialog(self, data: dict):
        dlg = UsageDialog(data, self)
        dlg.exec()
