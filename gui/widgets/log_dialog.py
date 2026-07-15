from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QWidget,
)

from .log_view import LogView


class LogDialog(QDialog):
    """实时日志弹窗：非模态，关闭后翻译继续运行。"""

    closed = Signal()

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"日志 — {title}")
        self.resize(720, 480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.log_view = LogView()
        layout.addWidget(self.log_view)

    def append(self, line: str) -> None:
        self.log_view.append(line)
