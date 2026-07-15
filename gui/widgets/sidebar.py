from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..theme import ACCENT, icon

_NAV_BG = f"rgba(108, 92, 231, 0.18)"
_HOVER_BG = "rgba(255, 255, 255, 0.06)"
_TEXT = "rgba(255, 255, 255, 0.68)"
_TEXT_SEL = "#FFFFFF"


class NavItem(QWidget):
    clicked = Signal()

    def __init__(self, name: str, key: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("navitem")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(46)
        self._checked = False
        self._hover = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.bar = QFrame()
        self.bar.setObjectName("navbar")
        self.bar.setFixedWidth(3)
        layout.addWidget(self.bar)

        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(icon(key, "#FFFFFF", 18).pixmap(18, 18))
        self.icon_lbl.setFixedSize(18, 18)

        self.text = QLabel(name)
        self.text.setObjectName("navtext")

        inner = QHBoxLayout()
        inner.setContentsMargins(14, 0, 14, 0)
        inner.setSpacing(10)
        inner.addWidget(self.icon_lbl)
        inner.addWidget(self.text)
        inner.addStretch(1)
        layout.addLayout(inner, 1)

        self._apply()

    def _apply(self) -> None:
        if self._checked:
            bg, bar, txt = _NAV_BG, ACCENT, _TEXT_SEL
        elif self._hover:
            bg, bar, txt = _HOVER_BG, "transparent", "rgba(255,255,255,0.85)"
        else:
            bg, bar, txt = "transparent", "transparent", _TEXT
        self.setStyleSheet(f"QWidget#navitem {{ background: {bg}; }}")
        self.bar.setStyleSheet(f"QFrame#navbar {{ background: {bar}; }}")
        self.text.setStyleSheet(f"QLabel#navtext {{ color: {txt}; font-size: 11pt; }}")

    def set_checked(self, value: bool) -> None:
        self._checked = value
        self._apply()

    def enterEvent(self, _event: QEnterEvent) -> None:
        self._hover = True
        self._apply()

    def leaveEvent(self, _event) -> None:
        self._hover = False
        self._apply()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class Sidebar(QWidget):
    currentChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("sidebarbg")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(168)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 10, 8, 8)
        self._layout.setSpacing(4)

        self.items: list[NavItem] = []
        for name, key in (("首页", "home"), ("设置", "settings")):
            self._add_item(name, key)

        self._layout.addStretch(1)

        foot = QWidget()
        foot.setObjectName("sidefoot")
        foot.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        foot_layout = QVBoxLayout(foot)
        foot_layout.setContentsMargins(14, 14, 14, 16)
        foot_layout.setSpacing(8)
        deco = QLabel()
        deco.setPixmap(icon("book", "#FFFFFF", 26).pixmap(26, 26))
        foot_layout.addWidget(deco)
        tip = QLabel("让译文如母语般流淌")
        tip.setStyleSheet(
            "color: rgba(255,255,255,0.55); font-size: 8.5pt; font-weight: 400;"
        )
        tip.setWordWrap(True)
        foot_layout.addWidget(tip)
        self._layout.addWidget(foot)

        self.items[0].set_checked(True)

    def _add_item(self, name: str, key: str) -> int:
        """创建 NavItem 并插入到 stretch 之前，返回其在 items 列表中的索引。"""
        item = NavItem(name, key)
        idx = len(self.items)
        self._layout.insertWidget(idx, item)
        item.clicked.connect(lambda item=item: self._on_clicked(item))
        self.items.append(item)
        return idx

    def _on_clicked(self, item: NavItem) -> None:
        """点击时动态查找索引，避免 add/remove 后索引失效。"""
        try:
            idx = self.items.index(item)
        except ValueError:
            return
        self._select(idx)

    def _select(self, idx: int) -> None:
        for i, item in enumerate(self.items):
            item.set_checked(i == idx)
        self.currentChanged.emit(idx)

    def set_current(self, idx: int) -> None:
        """更新视觉选中状态，不触发 currentChanged（用于程序化导航）。"""
        for i, item in enumerate(self.items):
            item.set_checked(i == idx)
