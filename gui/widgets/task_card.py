from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..tasks import TaskInfo
from ..theme import ACCENT, icon


class TaskCard(QFrame):
    resume_clicked = Signal(TaskInfo, str)

    def __init__(self, task: TaskInfo, known_input: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.task = task
        self.known_input = known_input

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon("book", ACCENT, 28).pixmap(28, 28))
        layout.addWidget(icon_lbl)

        info = QVBoxLayout()
        info.setSpacing(6)
        name = QLabel(task.title)
        name.setObjectName("tasktitle")
        meta = QHBoxLayout()
        meta.setSpacing(8)
        progress = QLabel(task.progress_text())
        progress.setObjectName("subtitle")
        meta.addWidget(progress)
        meta.addWidget(self._chip())
        meta.addStretch(1)
        info.addWidget(name)
        info.addLayout(meta)
        layout.addLayout(info, 1)

        btn = QPushButton("继续翻译")
        btn.setObjectName("primary")
        btn.clicked.connect(self.resume)
        layout.addWidget(btn)

    def _chip(self) -> QLabel:
        chip = QLabel(self._chip_text())
        chip.setObjectName("chip")
        if self.task.total and self.task.done >= self.task.total:
            chip.setObjectName("chip done")
        elif self.task.done:
            chip.setObjectName("chip running")
        return chip

    def _chip_text(self) -> str:
        if not self.task.status:
            return "未开始"
        return self.task.status

    def resume(self) -> None:
        self.resume_clicked.emit(self.task, self.known_input)
