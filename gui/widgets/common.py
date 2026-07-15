from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..theme import ACCENT, BG, BORDER, CHIP_GRAY, CHIP_GREEN, TEXT_MUTED, icon

_WARN = "#D97706"


class PathField(QWidget):
    """文件/目录选择行：标签 + 文本框（右侧内嵌浏览图标）+ 解析反馈。"""

    def __init__(self, label: str = "", mode: str = "file", file_filter: str = "",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._mode = mode
        self._filter = file_filter

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if label:
            row.addWidget(QLabel(label))
        self.edit = QLineEdit()
        self.edit.textChanged.connect(self._update_status)
        browse = self.edit.addAction(icon("folder", TEXT_MUTED, 16), QLineEdit.TrailingPosition)
        browse.triggered.connect(self._browse)
        row.addWidget(self.edit, 1)
        layout.addLayout(row)

        hint_row = QHBoxLayout()
        hint_row.setContentsMargins(0, 0, 0, 0)
        self.status_icon = QLabel()
        self.status_icon.setPixmap(icon("info", CHIP_GRAY, 14).pixmap(14, 14))
        self.hint = QLabel()
        self.hint.setObjectName("path_hint")
        hint_row.addWidget(self.status_icon)
        hint_row.addWidget(self.hint, 1)
        layout.addLayout(hint_row)

        self._update_status()

    def _browse(self) -> None:
        if self._mode == "file":
            path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", self._filter)
        else:
            path = QFileDialog.getExistingDirectory(self, "选择目录")
        if path:
            self.edit.setText(path)
            self._update_status()

    def _update_status(self) -> None:
        raw = self.edit.text().strip()
        if not raw:
            self.status_icon.setPixmap(icon("info", CHIP_GRAY, 14).pixmap(14, 14))
            self.hint.setText("")
            return
        try:
            p = Path(raw).resolve()
        except Exception:
            p = Path(os.path.abspath(raw))
        if self._mode == "file":
            target, kind = p.parent, "父目录"
        else:
            target, kind = p, "目录"
        if target.exists():
            if os.access(str(target), os.W_OK):
                self.status_icon.setPixmap(icon("check", CHIP_GREEN, 14).pixmap(14, 14))
                state = ""
            else:
                self.status_icon.setPixmap(icon("warn", _WARN, 14).pixmap(14, 14))
                state = "（只读）"
        else:
            self.status_icon.setPixmap(icon("info", CHIP_GRAY, 14).pixmap(14, 14))
            state = "（首次运行将自动创建）"
        self.hint.setText(f"{kind}：{p} {state}".strip())

    def path(self) -> str:
        return self.edit.text().strip()

    def set_path(self, value: str) -> None:
        self.edit.setText(value)
        self._update_status()


class FlatCombo(QComboBox):
    """扁平下拉框：去掉原生凸起的箭头按钮，自绘右侧灰色 chevron，统一界面风格。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QComboBox {{ padding-right: 26px; border: 1px solid {BORDER}; "
            f"border-radius: 8px; padding: 7px 26px 7px 10px; background: {BG}; }}"
            f"QComboBox:focus {{ border-color: {ACCENT}; }}"
            "QComboBox::drop-down { width: 0; border: none; }"
            "QComboBox::down-arrow { image: none; }"
            f"QComboBox QAbstractItemView {{ border: 1px solid {BORDER}; "
            f"border-radius: 8px; background: {BG}; selection-background-color: {ACCENT}; }}"
        )

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        cx = r.right() - 14
        cy = r.center().y()
        pen = QPen(QColor(TEXT_MUTED), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(cx - 4, cy - 3, cx, cy + 3)
        painter.drawLine(cx, cy + 3, cx + 4, cy - 3)
        painter.end()
