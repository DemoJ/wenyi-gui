from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..theme import ACCENT, icon
from .active_task_card import ActiveTaskCard

# 输入格式与原项目一致：trans_novel/ingest/segmenter.py 支持 .epub / .txt / .md(.markdown/.text) / .fb2
INPUT_FILTER = "电子书 (*.epub *.txt *.md *.markdown *.text *.fb2)"
INPUT_HINT = "或点击此处选择文件　·　支持 EPUB / TXT / MD / FB2"


class DropZone(QFrame):
    """大面板拖拽区：无活跃任务时撑满首页，有任务后隐藏改为紧凑按钮。"""

    file_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("dropzone")
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(icon("upload", "#6C5CE7", 44).pixmap(44, 44))
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_lbl)

        title = QLabel("拖入电子书开始翻译")
        title.setObjectName("drop_title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        sub = QLabel(INPUT_HINT)
        sub.setObjectName("drop_sub")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

    def mousePressEvent(self, _event):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择电子书", "", INPUT_FILTER
        )
        if path:
            self.file_selected.emit(path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                "QFrame#dropzone { border: 1px solid #6C5CE7; "
                "background: #FFFFFF; border-radius: 16px; }"
            )

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        event.accept()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        import os
        from PySide6.QtWidgets import QMessageBox
        self.setStyleSheet("")
        
        urls = event.mimeData().urls()
        if not urls:
            return
            
        if len(urls) > 1:
            QMessageBox.warning(self, "无效操作", "每次只能拖入一本电子书，请勿多选。")
            return
            
        url = urls[0]
        if not url.isLocalFile():
            QMessageBox.warning(self, "无效操作", "请拖入本地文件，不支持网络链接。")
            return
            
        local = url.toLocalFile()
        if not os.path.exists(local):
            QMessageBox.warning(self, "文件不存在", f"找不到指定的文件：\n{local}")
            return
            
        if not os.path.isfile(local):
            QMessageBox.warning(self, "无效格式", "请拖入具体的文件，不支持直接拖入文件夹。")
            return
            
        ext = os.path.splitext(local)[1].lower()
        if ext not in (".epub", ".txt", ".md", ".markdown", ".text", ".fb2"):
            QMessageBox.warning(self, "格式不支持", "目前只支持 .epub / .txt / .md / .fb2 格式的电子书。")
            return
            
        self.file_selected.emit(local)


class HomePage(QWidget):
    open_task = Signal(str)
    stop_requested = Signal(str)
    log_requested = Signal(str)
    retry_requested = Signal(str)
    delete_requested = Signal(str)
    open_dir_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # 大拖拽面板（无任务时撑满，有任务后隐藏）
        self.drop = DropZone()
        self.drop.file_selected.connect(self.open_task)
        layout.addWidget(self.drop, 1)

        # ── 活跃任务卡片（含标题栏 + 添加按钮 + 任务列表）──
        self._active_card = QFrame()
        self._active_card.setObjectName("card")
        active_layout = QVBoxLayout(self._active_card)
        active_layout.setContentsMargins(18, 16, 18, 16)
        active_layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        active_header = QLabel("活跃任务")
        active_header.setObjectName("title")
        header_row.addWidget(active_header)
        header_row.addStretch(1)
        self._add_btn = QPushButton("添加书籍")
        self._add_btn.setIcon(icon("upload", "#FFFFFF", 16))
        self._add_btn.setObjectName("primary")
        self._add_btn.clicked.connect(self._pick_file)
        header_row.addWidget(self._add_btn)
        active_layout.addLayout(header_row)

        self._active_list = QListWidget()
        self._active_list.setObjectName("tasklist")
        self._active_list.setSpacing(12)
        self._active_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._active_list.setStyleSheet(
            "QListWidget#tasklist { border: none; background: transparent; outline: 0; }"
            "QListWidget#tasklist::item { background: transparent; outline: 0; }"
            "QListWidget#tasklist::item:hover { background: transparent; outline: 0; }"
            "QListWidget#tasklist::item:selected { background: transparent; outline: 0; }"
        )
        active_layout.addWidget(self._active_list, 1)
        self._active_card.setVisible(False)
        layout.addWidget(self._active_card, 1)

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择电子书", "", INPUT_FILTER)
        if path:
            self.open_task.emit(path)

    # ── 活跃任务管理 ──

    def add_active_task(self, input_path: str, title: str, state_dir: str, is_restored: bool = False) -> None:
        """添加一个活跃任务卡片。首次添加时切换为紧凑模式。"""
        # 清理可能残留的相同任务（避免分身）
        self.remove_active_task(input_path)
        
        if not self._active_card.isVisible():
            self.drop.setVisible(False)
            self._active_card.setVisible(True)

        card = ActiveTaskCard(input_path, title, state_dir, is_restored=is_restored)
        card.stop_requested.connect(self.stop_requested)
        card.log_requested.connect(self.log_requested)
        card.retry_requested.connect(self.retry_requested)
        card.delete_requested.connect(self.delete_requested)
        card.open_dir_requested.connect(self.open_dir_requested)
        item = QListWidgetItem()
        self._active_list.insertItem(0, item)
        item.setSizeHint(card.sizeHint())
        self._active_list.setItemWidget(item, card)

    def update_task_status(self, input_path: str, status: str) -> None:
        card = self._find_active_card(input_path)
        if card:
            card.set_status(status)

    def set_task_finished(self, input_path: str, state_code: str, status_text: str) -> None:
        card = self._find_active_card(input_path)
        if card:
            card.set_finished(state_code, status_text)

    def _find_active_card(self, input_path: str) -> ActiveTaskCard | None:
        import os
        norm_input = os.path.normcase(input_path)
        for i in range(self._active_list.count()):
            item = self._active_list.item(i)
            widget = self._active_list.itemWidget(item)
            if isinstance(widget, ActiveTaskCard) and os.path.normcase(widget.input_path) == norm_input:
                return widget
        return None

    def remove_active_task(self, input_path: str) -> None:
        import os
        norm_input = os.path.normcase(input_path)
        
        items_to_remove = []
        for i in range(self._active_list.count()):
            item = self._active_list.item(i)
            widget = self._active_list.itemWidget(item)
            if isinstance(widget, ActiveTaskCard) and os.path.normcase(widget.input_path) == norm_input:
                items_to_remove.append(item)
                
        for item in items_to_remove:
            row = self._active_list.row(item)
            self._active_list.takeItem(row)
            
        if self._active_list.count() == 0:
            self._active_card.setVisible(False)
            self.drop.setVisible(True)
