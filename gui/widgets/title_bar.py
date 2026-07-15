from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from ..theme import icon


class TitleBar(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("titlebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(42)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 6, 0)
        layout.setSpacing(2)

        logo = QLabel()
        logo.setPixmap(icon("book", "#FFFFFF", 20).pixmap(20, 20))
        layout.addWidget(logo)

        wordmark = QLabel("文译")
        wordmark.setObjectName("wordmark")
        layout.addWidget(wordmark)

        layout.addStretch(1)

        self.btn_min = QPushButton()
        self.btn_min.setObjectName("winbtn")
        self.btn_min.setIcon(icon("minimize", "#FFFFFF", 18))
        self.btn_min.setFixedSize(40, 30)
        self.btn_min.clicked.connect(lambda: self.window().showMinimized())
        layout.addWidget(self.btn_min)

        self.btn_max = QPushButton()
        self.btn_max.setObjectName("winbtn")
        self.btn_max.setIcon(icon("maximize", "#FFFFFF", 18))
        self.btn_max.setFixedSize(40, 30)
        self.btn_max.clicked.connect(self._toggle_max)
        layout.addWidget(self.btn_max)

        self.btn_close = QPushButton()
        self.btn_close.setObjectName("closebtn")
        self.btn_close.setIcon(icon("close", "#FFFFFF", 18))
        self.btn_close.setFixedSize(40, 30)
        self.btn_close.clicked.connect(lambda: self.window().close())
        layout.addWidget(self.btn_close)

        self._drag = None

    def _toggle_max(self) -> None:
        win = self.window()
        if win.isMaximized():
            win.showNormal()
            self.btn_max.setIcon(icon("maximize", "#FFFFFF", 18))
        else:
            win.showMaximized()
            self.btn_max.setIcon(icon("restore", "#FFFFFF", 18))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag is not None and event.buttons() & Qt.MouseButton.LeftButton:
            win = self.window()
            win.move(win.pos() + event.globalPosition().toPoint() - self._drag)
            self._drag = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag = None
        super().mouseReleaseEvent(event)
