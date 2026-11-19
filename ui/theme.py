"""Palette et feuille de style (thème clair moderne)."""

# ── Palette principale ──────────────────────────────────────────────────────
ACCENT = "#6C4DFF"
ACCENT_DARK = "#4B35D6"
ACCENT_SOFT = "#F1EEFF"
ACCENT_BORDER = "#DDD6FF"
BG = "#F5F6FB"
PANEL = "#FFFFFF"
BORDER = "#E7E9F2"
INPUT_BORDER = "#DADDEA"
TEXT = "#1F1D33"
TEXT_SOFT = "#4A4E69"
MUTED = "#6B7089"
GREEN = "#0E9F6E"
RED = "#E5484D"
BLUE = "#3B82F6"
ORANGE = "#F59E0B"

# Dégradé des boutons / bannières
GRAD = "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7C5CFF, stop:1 #5B8CFF)"
GRAD_HOVER = "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8F73FF, stop:1 #70A0FF)"
GRAD_DIAG = "qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #7C5CFF, stop:1 #5B8CFF)"

OP_COLORS = {"ADD": BLUE, "XOR": ACCENT, "ROTL": ORANGE}

RFC_KEY = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
RFC_NONCE = "000000090000004a00000000"
DEFAULT_MESSAGE = "ATTACK AT DAWN"

# --- State Matrix palette (origin-based word colors) ---
MATRIX_CONSTANT = "#F5A524"   # warm gold
MATRIX_KEY = GREEN            # mint/green
MATRIX_COUNTER = RED          # coral red
MATRIX_NONCE = BLUE           # blue

MATRIX_GRID = "#ECEEF4"       # subtle gridline, close to BORDER

# ── QSS : tableau de la state matrix ────────────────────────────────────────
MATRIX_QSS = f"""
QTableWidget#stateMatrix {{
    background: #F8F9FC;
    border: 1px solid {BORDER};
    border-radius: 12px;
    gridline-color: {MATRIX_GRID};
    selection-background-color: transparent;
    outline: 0;
}}
QTableWidget#stateMatrix::item {{
    padding: 4px;
}}
QTableWidget#stateMatrix QHeaderView::section {{
    background: transparent;
    border: none;
}}
"""

# ── QSS : timeline (page À propos) ──────────────────────────────────────────
TIMELINE_QSS = f"""
#timeline_year {{
    color: {ACCENT};
    font-size: 13px;
    font-weight: 800;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}}
#timeline_dot_ancestor {{ color: #94A3B8; font-size: 18px; }}
#timeline_dot_birth    {{ color: {BLUE}; font-size: 18px; }}
#timeline_dot_adoption {{ color: #8B5CF6; font-size: 18px; }}
#timeline_dot_standard {{ color: {GREEN}; font-size: 18px; }}
#timeline_dot_modern   {{ color: {ORANGE}; font-size: 18px; }}
#timeline_dot_now      {{ color: {RED}; font-size: 18px; }}

#timeline_card {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
#timeline_name {{
    font-size: 14px;
    font-weight: 800;
    color: {TEXT};
}}
#timeline_connector {{
    background: {BORDER};
    border-radius: 1px;
}}
"""


def build_stylesheet() -> str:
    return f"""
    /* ===================== Base ===================== */
    QWidget {{ color:{TEXT}; font-family:'Inter','Segoe UI','DejaVu Sans',sans-serif; font-size:13px; }}
    QMainWindow, #root, #page, QDialog {{ background:{BG}; }}
    QScrollArea {{ background:{BG}; border:none; }}
    QLabel {{ background:transparent; }}
    QToolTip {{ background:{PANEL}; color:{TEXT}; border:1px solid {BORDER}; padding:6px; }}

    /* ===================== Sidebar ===================== */
    #sidebar {{ background:{PANEL}; border-right:1px solid {BORDER}; }}
    #logo_tile {{ font-size:26px; border-radius:14px;
        background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #8B73FF, stop:1 #5B8CFF); }}
    #logo_title {{ font-size:20px; font-weight:800; }}
    #logo_sub {{ font-size:13px; font-weight:600; color:{ACCENT}; }}
    #bubble {{ background:{ACCENT_SOFT}; color:{ACCENT_DARK}; border:1px solid {ACCENT_BORDER};
        border-radius:16px; padding:14px; font-weight:700; }}
    QPushButton#nav {{ text-align:left; background:transparent; border:0; padding:12px 14px;
        color:{MUTED}; font-weight:600; font-size:14px; border-radius:12px; }}
    QPushButton#nav:hover {{ background:#F6F4FF; color:{ACCENT_DARK}; }}
    QPushButton#nav:checked {{ background:{ACCENT_SOFT}; color:{ACCENT_DARK}; }}
    QPushButton#launch_btn {{ color:white; border:none; border-radius:14px; padding:14px;
        font-weight:700; font-size:14px; background:{GRAD}; }}
    QPushButton#launch_btn:hover {{ background:{GRAD_HOVER}; }}

    /* ===================== Titles & text ===================== */
    #hdr_icon {{ font-size:22px; border-radius:14px; background:{ACCENT_SOFT}; }}
    #title {{ font-size:24px; font-weight:800; }}
    #muted {{ color:{MUTED}; }}
    #section {{ font-size:14px; font-weight:700; }}
    #formula {{ font-family:monospace; font-size:15px; font-weight:800; color:{ACCENT_DARK}; }}
    #explanation {{ color:{TEXT_SOFT}; font-size:13px; }}
    #error_label {{ color:{RED}; font-weight:600; }}
    #ok_label {{ color:{GREEN}; font-weight:600; }}

    /* ===================== Cards ===================== */
    #card {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:18px; }}
    #stat_icon {{ font-size:18px; background:{ACCENT_SOFT}; border-radius:12px; }}
    #stat_label {{ font-size:11px; font-weight:600; color:{MUTED}; }}
    #info_val {{ font-size:15px; font-weight:700; font-family:monospace; color:{ACCENT_DARK}; }}
    #vsep {{ background:{BORDER}; border:none; }}
    QPushButton#collapse_header {{ text-align:left; background:transparent; border:none;
        padding:16px 22px; font-size:14px; font-weight:700; border-radius:18px; }}
    QPushButton#collapse_header:hover {{ background:#FAF9FF; color:{ACCENT_DARK}; }}
    QPushButton#link_btn {{ background:{ACCENT_SOFT}; color:{ACCENT_DARK}; border:1px solid {ACCENT_BORDER};
        border-radius:10px; padding:8px 14px; font-weight:700; }}
    QPushButton#link_btn:hover {{ background:#E7E1FF; }}

    /* ===================== Machine ===================== */
    #chip {{ background:{ACCENT_SOFT}; border:1px solid {ACCENT_BORDER}; border-radius:10px;
        font-size:18px; font-weight:700; color:{ACCENT_DARK}; }}
    #chip_space {{ background:transparent; border:1px dashed #D5D8E6; border-radius:10px;
        font-size:14px; color:#B0B4C8; }}
    #chip_fly {{ background:{ACCENT_SOFT}; border:2px solid {ACCENT}; border-radius:10px;
        font-size:18px; font-weight:800; color:{ACCENT_DARK}; }}
    #operand_fly {{ background:{ACCENT}; color:white; border-radius:12px; font-family:monospace;
        font-size:14px; font-weight:800; }}
    #op_chip {{ background:#F6F7FB; border:2px solid transparent; border-radius:12px;
        padding:6px 12px; font-weight:700; color:{MUTED}; }}
    #op_chip[active="true"] {{ background:#E7E1FF; color:{ACCENT_DARK}; }}

    #reg_row {{ background:#FAFAFE; border:2px solid transparent; border-radius:14px; }}
    #reg_row[role="target"] {{ background:#F3F0FF; border:2px solid {ACCENT}; }}
    #reg_row[role="source"] {{ background:#F0F6FF; border:2px dashed #7FA6FF; }}
    #reg_name {{ background:{ACCENT_SOFT}; color:{ACCENT_DARK}; font-weight:800; font-size:16px;
        border-radius:10px; }}
    #reg_row[role="target"] #reg_name {{ background:{ACCENT}; color:white; }}
    #reg_row[role="source"] #reg_name {{ background:#7FA6FF; color:white; }}
    #reg_idx {{ color:{MUTED}; font-size:11px; font-family:monospace; }}
    #reg_hex {{ font-family:monospace; font-size:14px; font-weight:800; color:{ACCENT_DARK}; }}

    /* ===================== Calc / text views ===================== */
    QTextEdit, QTextBrowser {{ background:#F8F9FC; border:1px solid {BORDER}; border-radius:12px; padding:10px; }}

    /* ===================== Inputs (bloc unique) ===================== */
    QLineEdit, QSpinBox, QDoubleSpinBox {{
        background:{PANEL};
        color:{TEXT};
        border:1px solid {INPUT_BORDER};
        border-radius:10px;
        padding:8px 12px;
        font-family:monospace;
        font-size:13px;
        selection-background-color:{ACCENT};
        selection-color:white;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
    QPushButton#prev_qr:focus, QPushButton#next_qr:focus {{
        border:1px solid {ACCENT};
    }}
    QLineEdit[invalid="true"] {{ border:1px solid {RED}; background:#FFF5F5; }}
    QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background:#F3F4F8; color:#A9ADBF; border-color:#ECEEF4;
    }}
    /* Le QLineEdit interne d'une spinbox garde son propre style neutre */
    QSpinBox QLineEdit, QDoubleSpinBox QLineEdit {{
        background:transparent; color:{TEXT}; border:none; padding:0;
    }}

    /* ===================== SpinBox : boutons haut / bas ===================== */
    QSpinBox, QDoubleSpinBox {{ font-size:14px; padding-right:26px; }}
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        subcontrol-origin:border;
        background:{ACCENT_SOFT};
        border-left:1px solid {INPUT_BORDER};
        width:20px;
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-position:top right;
        border-top-right-radius:9px;
        border-bottom:1px solid {INPUT_BORDER};
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-position:bottom right;
        border-bottom-right-radius:9px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover,
    QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{ background:#E7E1FF; }}
    QSpinBox::up-button:pressed, QSpinBox::down-button:pressed,
    QDoubleSpinBox::up-button:pressed, QDoubleSpinBox::down-button:pressed {{ background:{ACCENT}; }}

    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        image:none; width:0; height:0;
        border-left:5px solid transparent;
        border-right:5px solid transparent;
        border-bottom:5px solid {ACCENT};
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image:none; width:0; height:0;
        border-left:5px solid transparent;
        border-right:5px solid transparent;
        border-top:5px solid {ACCENT};
    }}
    QSpinBox::up-arrow:pressed, QDoubleSpinBox::up-arrow:pressed {{ border-bottom-color:white; }}
    QSpinBox::down-arrow:pressed, QDoubleSpinBox::down-arrow:pressed {{ border-top-color:white; }}

    /* ===================== Buttons ===================== */
    QPushButton {{ background:{PANEL}; border:1px solid {INPUT_BORDER}; border-radius:11px;
        padding:9px 18px; font-weight:600; }}
    QPushButton:hover {{ background:#F6F4FF; border-color:{ACCENT}; color:{ACCENT_DARK}; }}
    QPushButton:disabled {{ background:#F3F4F8; color:#A9ADBF; border-color:#ECEEF4; }}
    QPushButton#play_btn, QPushButton#primary {{ color:white; border:none; padding:9px 24px;
        background:{GRAD}; }}
    QPushButton#play_btn:hover, QPushButton#primary:hover {{ color:white; background:{GRAD_HOVER}; }}
    QPushButton#play_btn:disabled, QPushButton#primary:disabled, QPushButton#launch_btn:disabled {{
        background:#D9DAE6; color:#9A9DB3; }}
    QPushButton#aes_btn {{ background:#FFF8EB; color:#B45309; border:1px solid #FCD9A0; text-align:left; }}
    QPushButton#aes_btn:hover {{ background:#FFF1D6; border-color:{ORANGE}; color:#92400E; }}
    QPushButton#tiny {{ padding:8px 12px; }}
    QPushButton#prev_qr, QPushButton#next_qr {{ padding:8px 0; color:{ACCENT}; background:{ACCENT_SOFT}; border-radius:8px; }}

    /* ===================== Slider & scrollbar ===================== */
    QSlider::groove:horizontal {{ height:6px; background:#E3E5F0; border-radius:3px; }}
    QSlider::sub-page:horizontal {{ background:{ACCENT}; border-radius:3px; }}
    QSlider::handle:horizontal {{ background:white; border:2px solid {ACCENT}; width:14px; margin:-6px 0; border-radius:9px; }}
    QScrollBar:vertical {{ background:transparent; width:10px; margin:2px; }}
    QScrollBar::handle:vertical {{ background:#D5D8E6; border-radius:4px; min-height:30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}

    /* ===================== Usages page ===================== */
    #usageCard {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:14px; min-height:200px; }}
    #usageCard:hover {{ border:1px solid {ACCENT}; background:#FAF9FF; }}
    #usageTitle {{ font-size:16px; font-weight:800; color:{TEXT}; }}
    #usageShort {{ font-size:13px; color:{TEXT_SOFT}; }}
    #usageTag {{ background:{ACCENT_SOFT}; color:{ACCENT_DARK}; border:1px solid {ACCENT_BORDER};
        border-radius:8px; padding:3px 8px; font-size:11px; font-weight:700; }}
    #usageTagMore {{ background:#F3F4F8; color:{MUTED}; border:1px solid {BORDER};
        border-radius:8px; padding:3px 8px; font-size:11px; font-weight:700; }}
    #usageHint {{ font-size:11px; color:{ACCENT}; font-weight:700; }}

    /* ===================== Usage dialog ===================== */
    #usageDialogCard {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:16px; }}
    #usageDialogBody {{ background:transparent; }}
    #usageDialogTitle {{ font-size:22px; font-weight:800; color:{TEXT}; }}
    #usageDialogText {{ font-size:14px; color:{TEXT_SOFT}; }}
    #usageDialogSubTitle {{ font-size:13px; font-weight:800; color:{ACCENT_DARK}; margin-top:8px; }}

    /* ===================== Intro page ===================== */
    #introCard {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:24px; }}
    #introTitle {{ font-size:28px; font-weight:800; color:{TEXT}; }}
    #introText {{ font-size:16px; color:{TEXT_SOFT}; }}
    #introDot {{ color:#D5D8E6; font-size:14px; }}
    #introDotActive {{ color:{ACCENT}; font-size:14px; }}

    /* ===================== Quiz page ===================== */
    QProgressBar#quizProgress {{ background:#F1F1F6; border:none; border-radius:6px; }}
    QProgressBar#quizProgress::chunk {{ background:{GRAD}; border-radius:6px; }}
    #quizQuestion {{ font-size:20px; font-weight:800; color:{TEXT}; }}
    QPushButton#quizChoice {{ background:#FAFAFE; border:2px solid {BORDER}; border-radius:10px;
        padding:12px 16px; text-align:left; font-size:14px; font-weight:600; color:{TEXT}; }}
    QPushButton#quizChoice:hover {{ background:{ACCENT_SOFT}; border-color:{ACCENT}; color:{ACCENT_DARK}; }}
    QPushButton#quizChoice:disabled {{ color:{TEXT}; }}
    #resultCard {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:24px; }}

    /* ===================== AES dialog ===================== */
    /* 1. Header */
    #aes_header {{ background:{GRAD_DIAG}; border-radius:20px; }}
    #aes_eyebrow {{ color:rgba(255,255,255,190); font-size:11px; font-weight:800; }}
    #aes_title {{ color:white; font-size:22px; font-weight:800; }}
    #aes_name {{ color:rgba(255,255,255,235); font-size:13px; }}

    /* 2. Badges */
    #badge_direct, #badge_partial, #badge_none {{
        border-radius:11px; padding:5px 12px; font-size:12px; font-weight:800; }}
    #badge_direct  {{ background:#DCFCE7; color:#166534; }}
    #badge_partial {{ background:#FEF3C7; color:#92400E; }}
    #badge_none    {{ background:#FEE2E2; color:#991B1B; }}

    /* 3. Cartes "se ressemble" / "diffère" (bordure uniforme : les bordures
          d'épaisseurs différentes + border-radius donnent des coins moches en QSS) */
    #aes_same_card {{ background:#F3FCF6; border:1px solid #86EFAC; border-radius:16px; }}
    #aes_diff_card {{ background:#FFF6F6; border:1px solid #FCA5A5; border-radius:16px; }}
    #aes_card_title_same {{ color:#166534; font-size:14px; font-weight:800; }}
    #aes_card_title_diff {{ color:#991B1B; font-size:14px; font-weight:800; }}

    /* 4. Puces */
    #aes_dot_same, #aes_dot_diff {{ font-size:10px; font-weight:800; min-width:18px; max-width:18px; }}
    #aes_dot_same {{ color:#16A34A; }}
    #aes_dot_diff {{ color:{RED}; }}
    #aes_bullet_text {{ color:#374151; font-size:13px; }}

    /* 5. À retenir */
    #aes_takeaway {{ background:{ACCENT_SOFT}; border:1px solid {ACCENT_BORDER}; border-radius:14px; }}
    #aes_takeaway_icon {{ font-size:20px; background:transparent; }}
    #aes_takeaway_text {{ color:{ACCENT_DARK}; font-size:14px; font-weight:700; }}

    /* 6. Vue d'ensemble */
    #aes_overview {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:16px; }}
    #aes_overview_title {{ font-size:14px; font-weight:800; color:{TEXT}; }}
    #ov_head_blank {{ background:transparent; }}
    #ov_head_aes, #ov_head_cc {{ font-size:12px; font-weight:800; padding:8px 12px; border-radius:8px; }}
    #ov_head_aes {{ background:#FFF4E0; color:#B45309; }}
    #ov_head_cc  {{ background:#EFEBFF; color:{ACCENT_DARK}; }}
    #ov_key  {{ color:{MUTED}; font-weight:700; padding:8px 12px; }}
    #ov_cell {{ color:{TEXT}; padding:8px 12px; }}
    #ov_key[alt="true"], #ov_cell[alt="true"] {{ background:#F8F9FC; }}

    /* 7. Footer */
    #aes_footer {{ background:transparent; }}
    #aes_footer QPushButton#primary {{ min-width:110px; padding:10px 26px; border-radius:12px; }}
    """ + MATRIX_QSS + TIMELINE_QSS
