from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QTextEdit, QPushButton, QVBoxLayout, QWidget


class LogView(QWidget):
    """运行日志显示区（只读）+ 清空按钮。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("运行日志"))
        top.addStretch(1)
        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.clicked.connect(lambda: self.text.clear())
        top.addWidget(self.clear_btn)
        layout.addLayout(top)
        self.text = QTextEdit()
        self.text.setObjectName("log")
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.text.document().setMaximumBlockCount(2000)
        layout.addWidget(self.text, 1)

    def append(self, line: str) -> None:
        self.text.append(line)
