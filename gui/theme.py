from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

# ── 色彩 token（全局唯一来源）──────────────────────────────────────
BG = "#FFFFFF"
BG_SOFT = "#F5F6FA"
SIDEBAR = "#1C1D2B"          # 带一点蓝紫的深色，非纯黑
SIDEBAR_HOVER = "#262838"
SIDEBAR_SEL = "#2A2C42"
ACCENT = "#6C5CE7"          # 贯穿全局的紫
ACCENT_STRONG = "#5A4BD6"
ACCENT_SOFT = "#ECE9FB"     # 浅紫底（亮色区域里的 chip/背景）
TEXT = "#1F2430"
TEXT_MUTED = "#6B7280"
SIDEBAR_TEXT = "rgba(255,255,255,0.70)"
SIDEBAR_TEXT_SEL = "#FFFFFF"
BORDER = "#E6E8EC"
WINDOW_BORDER = "#C9CDD6"     # 窗口外框线（中性灰，非强调色）
DANGER = "#DC2626"
CHIP_GREEN = "#16A34A"
CHIP_GRAY = "#9AA1AD"
LOG_BG = "#1E2230"
LOG_TEXT = "#D6E2FF"

_STROKE = 'stroke="{c}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"'
_FILL = 'fill="{c}" stroke="none"'

_SVG = {
    "logo": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M4 5.5C4 4 7 3 12 3s8 1 8 2.5v13c0-1.5-3-2.5-8-2.5S4 17 4 18.5z"/><path d="M12 3v13"/></g></svg>',
    "home": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M4 11l8-7 8 7"/><path d="M6 9.5V20h12v-9.5"/></g></svg>',
    "settings": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="3"/><path d="M12 2.4v2.6M12 19v2.6M2.4 12h2.6M19 12h2.6M5 5l1.9 1.9M17.1 17.1 19 19M19 5l-1.9 1.9M6.9 17.1 5 19"/></g></svg>',
    "upload": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M12 15V4M8 8l4-4 4 4M5 20h14"/></g></svg>',
    "book": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M4 5.5C4 4 7 3 12 3s8 1 8 2.5v13c0-1.5-3-2.5-8-2.5S4 17 4 18.5z"/><path d="M12 3v13"/></g></svg>',
    "status": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M5 7h14M5 12h14M5 17h14"/></g></svg>',
    "glossary": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M9 6h11M9 12h11M9 18h11"/></g><g {_FILL}><circle cx="4.5" cy="6" r="0.9"/><circle cx="4.5" cy="12" r="0.9"/><circle cx="4.5" cy="18" r="0.9"/></g></svg>',
    "assemble": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/></g></svg>',
    "qa": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M12 3l7 3v5c0 5-3 8-7 9-4-1-7-4-7-9V6z"/><path d="M9 12l2 2 4-4"/></g></svg>',
    "report": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4V3h6v1M9 10h6M9 14h6M9 18h4"/></g></svg>',
    "minimize": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M5 12h14"/></g></svg>',
    "maximize": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><rect x="5" y="5" width="14" height="14" rx="2"/></g></svg>',
    "restore": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><rect x="8" y="8" width="11" height="11" rx="2"/><path d="M5 16V6h10"/></g></svg>',
    "pause": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_FILL}><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></g></svg>',
    "play": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_FILL}><path d="M5 3l14 9-14 9z"/></g></svg>',
    "retry": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></g></svg>',
    "close": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M6 6l12 12M18 6L6 18"/></g></svg>',
    "folder": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></g></svg>',
    "check": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M5 13l4 4 10-11"/></g></svg>',
    "warn": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><path d="M12 4l9 16H3z"/><path d="M12 10v5M12 17.5v.5"/></g></svg>',
    "info": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g {_STROKE}><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.5"/></g></svg>',
}


def icon(name: str, color: str = ACCENT, size: int = 22) -> QIcon:
    svg = _SVG.get(name)
    if not svg:
        return QIcon()
    renderer = QSvgRenderer(QByteArray(svg.replace("{c}", color).encode("utf-8")))
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(0)
    painter = QPainter(img)
    renderer.render(painter)
    painter.end()
    return QIcon(QPixmap.fromImage(img))


APP_STYLE = f"""
QWidget {{
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 10pt;
    color: {TEXT};
}}
QWidget#central {{ background: transparent; }}
QWidget#frame {{
    background: {BG_SOFT};
    border: 1px solid {WINDOW_BORDER};
    border-radius: 8px;
}}
QWidget#sidebarbg, QWidget#sidefoot, QWidget#titlebar {{ background: {SIDEBAR}; }}

/* 侧栏导航项（NavItem 用 Python 控制外观，避免原生描边框） */

/* 卡片 */
QFrame#card {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

/* 按钮 */
QPushButton {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
QPushButton:disabled {{ color: {CHIP_GRAY}; border-color: {BORDER}; }}
QPushButton#primary {{
    background: {ACCENT};
    border: none;
    color: #FFFFFF;
    font-weight: 600;
    padding: 10px 20px;
}}
QPushButton#primary:hover {{ background: {ACCENT_STRONG}; }}
QPushButton#ghost {{ border: none; color: {TEXT_MUTED}; background: transparent; }}
QPushButton#ghost:hover {{ color: {ACCENT}; background: {BG_SOFT}; }}
QPushButton#danger {{ color: {DANGER}; border-color: #F0C2C2; }}
QPushButton#danger:hover {{ background: #FEF2F2; border-color: {DANGER}; }}

/* 上传区：白色卡片 + 1px 细边，悬停/拖拽触发强调色边框（静止也有容器感） */
QFrame#dropzone {{
    border: 1px solid {BORDER};
    border-radius: 16px;
    background: #FFFFFF;
    padding: 30px;
}}
QFrame#dropzone:hover {{
    border-color: {ACCENT};
}}
QLabel#drop_title {{ color: {ACCENT}; font-size: 14pt; font-weight: 700; }}
QLabel#drop_sub {{ color: {TEXT_MUTED}; font-size: 10pt; }}

/* 空状态 */
QLabel#empty_title {{ color: {TEXT}; font-size: 12pt; font-weight: 600; }}
QLabel#empty_sub {{ color: {TEXT_MUTED}; font-size: 10pt; }}

QLabel#title {{ font-size: 15pt; font-weight: 700; }}
QLabel#subtitle {{ color: {TEXT_MUTED}; font-size: 10pt; }}
QLabel#tasktitle {{ font-size: 11pt; font-weight: 600; }}
QLabel#wordmark {{ color: #FFFFFF; font-size: 14pt; font-weight: 700; }}

QLineEdit, QComboBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 10px;
    background: {BG};
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled {{ color: {CHIP_GRAY}; background: {BG_SOFT}; }}
QComboBox QAbstractItemView {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background: {BG};
    selection-background-color: {ACCENT};
}}

/* 设置页：分组标题（仅文字 + 上边距，不再用分割线） */
QLabel#section_title {{
    font-size: 11pt;
    font-weight: 700;
    color: {ACCENT};
}}

/* 设置页：路径解析反馈（图标 + 绝对路径 / 是否可写） */
QLabel#path_hint {{
    color: {TEXT_MUTED};
    font-size: 9pt;
}}

QTextEdit#log {{
    background: {LOG_BG};
    color: {LOG_TEXT};
    border: 1px solid #2C313C;
    border-radius: 10px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 9.5pt;
    padding: 10px;
}}

QProgressBar {{
    border: none;
    border-radius: 6px;
    background: {BORDER};
    height: 8px;
    text-align: center;
    color: {TEXT_MUTED};
    font-size: 8pt;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 6px; }}

QLabel#chip {{
    background: transparent;
    padding: 0;
    font-size: 10pt;
    font-weight: 600;
}}
QLabel#chip[state="default"] {{ color: #6B7280; }}
QLabel#chip[state="done"] {{ color: #10B981; }}
QLabel#chip[state="running"] {{ color: {ACCENT}; }}
QLabel#chip[state="error"] {{ color: #EF4444; }}

QPushButton#action_btn, QPushButton#action_btn_danger {{
    border: 1px solid {BORDER};
    background: #FFFFFF;
    border-radius: 8px;
}}
QPushButton#action_btn:hover {{ background: #F3F4F6; border-color: {ACCENT}; }}
QPushButton#action_btn_danger:hover {{ background: #FEE2E2; border-color: {DANGER}; }}

/* 活跃任务项卡片 */
QFrame#active_task_card {{
    background: {BG_SOFT};
    border: 1px solid transparent;
    border-radius: 12px;
}}
QFrame#active_task_card:hover {{
    background: #FFFFFF;
    border: 1px solid {ACCENT};
}}
QFrame#task_icon_container {{
    background: {ACCENT_SOFT};
    border-radius: 10px;
}}

/* 窗口控制按钮：min/max/close 统一为透明底 + 白色线性图标 */
QPushButton#winbtn, QPushButton#closebtn {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 0;
    qproperty-iconSize: 18px 18px;
}}
QPushButton#winbtn:hover {{ background: {SIDEBAR_HOVER}; }}
QPushButton#closebtn:hover {{ background: {DANGER}; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(APP_STYLE)
