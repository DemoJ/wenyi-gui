from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QColor

from .common import FlatCombo
from ..theme import ACCENT, icon

LANG_OPTIONS = [
    ("自动识别 (Auto)", "auto"),
    ("日语 (ja)", "ja"),
    ("英语 (en)", "en"),
    ("韩语 (ko)", "ko"),
    ("俄语 (ru)", "ru"),
    ("法语 (fr)", "fr"),
    ("德语 (de)", "de"),
    ("西班牙语 (es)", "es"),
]

FORMAT_OPTIONS = [
    ("单语 EPUB", "epub"),
    ("双语对照 EPUB", "epub-bilingual"),
    ("纯文本 TXT", "txt"),
]


class TaskConfigDialog(QDialog):
    """翻译任务配置弹窗：选择源语言和输出格式。"""

    def __init__(self, input_path: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        title = Path(input_path).stem
        self.setFixedSize(420, 260)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 容器 Frame
        self.container = QFrame(self)
        self.container.setObjectName("dialog_container")
        self.container.setStyleSheet("QFrame#dialog_container { background: #FFFFFF; border-radius: 12px; border: 1px solid #E5E7EB; }")
        
        shadow = QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.container.setGraphicsEffect(shadow)

        main_layout.addWidget(self.container)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Title
        title_lbl = QLabel(f"《{title}》")
        title_lbl.setObjectName("title")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        # 源语言
        lang_row = QHBoxLayout()
        lang_lbl = QLabel("源语言：")
        lang_lbl.setFixedWidth(80)
        self.lang_combo = FlatCombo()
        for text, _ in LANG_OPTIONS:
            self.lang_combo.addItem(text)
        lang_row.addWidget(lang_lbl)
        lang_row.addWidget(self.lang_combo, 1)
        layout.addLayout(lang_row)

        # 输出格式
        fmt_row = QHBoxLayout()
        fmt_lbl = QLabel("输出格式：")
        fmt_lbl.setFixedWidth(80)
        self.fmt_combo = FlatCombo()
        for text, _ in FORMAT_OPTIONS:
            self.fmt_combo.addItem(text)
        fmt_row.addWidget(fmt_lbl)
        fmt_row.addWidget(self.fmt_combo, 1)
        layout.addLayout(fmt_row)

        layout.addStretch(1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("开始翻译")
        self.ok_btn.setObjectName("primary")
        self.ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.ok_btn)

        layout.addLayout(btn_row)

    def get_config(self) -> dict[str, str]:
        """返回配置字典。"""
        lang_idx = self.lang_combo.currentIndex()
        fmt_idx = self.fmt_combo.currentIndex()
        return {
            "source_lang": LANG_OPTIONS[lang_idx][1],
            "format": FORMAT_OPTIONS[fmt_idx][1],
        }
