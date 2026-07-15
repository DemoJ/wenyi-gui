from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import json
import os
import re
import time
from PySide6.QtCore import QTimer

from ..theme import ACCENT, DANGER, TEXT_MUTED, icon


class _ElidedLabel(QLabel):
    """自动在右侧截断文字并显示省略号的 QLabel，tooltip 保留全文。"""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._full = text
        self.setWordWrap(False)
        self.setToolTip(text)

    def setText(self, text: str) -> None:
        self._full = text
        self.setToolTip(text)
        self._elide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide()

    def _elide(self) -> None:
        fm = QFontMetrics(self.font())
        elided = fm.elidedText(self._full, Qt.TextElideMode.ElideRight, self.width())
        super().setText(elided)


class ActiveTaskCard(QFrame):
    """活跃任务卡片：图标 + 书名 + 状态胶囊 + 日志/操作按钮。"""

    stop_requested = Signal(str)
    retry_requested = Signal(str)
    delete_requested = Signal(str)
    log_requested = Signal(str)
    open_dir_requested = Signal(str)

    def __init__(self, input_path: str, title: str, state_dir: str = "", is_restored: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.input_path = input_path
        self.title = title
        self.state_dir = state_dir
        self.is_restored = is_restored
        self.setObjectName("active_task_card")

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(14)

        # 图标容器（带圆角和主题色背景）
        icon_container = QFrame()
        icon_container.setFixedSize(42, 42)
        icon_container.setObjectName("task_icon_container")
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignCenter)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon("book", ACCENT, 24).pixmap(24, 24))
        icon_layout.addWidget(icon_lbl)
        row.addWidget(icon_container)

        vbox = QVBoxLayout()
        vbox.setSpacing(4)
        
        self.name_lbl = _ElidedLabel(title)
        self.name_lbl.setObjectName("tasktitle")
        vbox.addWidget(self.name_lbl)

        prog_row = QHBoxLayout()
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setTextVisible(False)
        
        self.prog_lbl = QLabel("准备中…")
        self.prog_lbl.setObjectName("subtitle")
        
        prog_row.addWidget(self.prog_bar, 1)
        prog_row.addWidget(self.prog_lbl)
        vbox.addLayout(prog_row)
        
        row.addLayout(vbox, 1)

        self.chip = QLabel("● 运行中")
        self.chip.setObjectName("chip")
        self.chip.setProperty("state", "running")
        self.chip.setAlignment(Qt.AlignCenter)
        row.addWidget(self.chip)

        self.log_btn = QPushButton()
        self.log_btn.setIcon(icon("report", TEXT_MUTED, 18))
        self.log_btn.setToolTip("查看日志")
        self.log_btn.setFixedSize(36, 36)
        self.log_btn.setObjectName("action_btn")
        self.log_btn.setCursor(Qt.PointingHandCursor)
        self.log_btn.clicked.connect(lambda: self.log_requested.emit(self.input_path))
        row.addWidget(self.log_btn)

        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(icon("pause", TEXT_MUTED, 18))
        self.stop_btn.setToolTip("暂停 (保存当前进度)")
        self.stop_btn.setFixedSize(36, 36)
        self.stop_btn.setObjectName("action_btn")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(lambda: self.stop_requested.emit(self.input_path))
        row.addWidget(self.stop_btn)

        self.open_dir_btn = QPushButton()
        self.open_dir_btn.setIcon(icon("folder", TEXT_MUTED, 18))
        self.open_dir_btn.setToolTip("打开输出目录")
        self.open_dir_btn.setFixedSize(36, 36)
        self.open_dir_btn.setObjectName("action_btn")
        self.open_dir_btn.setCursor(Qt.PointingHandCursor)
        self.open_dir_btn.clicked.connect(lambda: self.open_dir_requested.emit(self.input_path))
        self.open_dir_btn.setVisible(False)
        row.addWidget(self.open_dir_btn)

        self.retry_btn = QPushButton()
        self.retry_btn.setIcon(icon("play", TEXT_MUTED, 18))
        self.retry_btn.setToolTip("继续翻译")
        self.retry_btn.setFixedSize(36, 36)
        self.retry_btn.setObjectName("action_btn")
        self.retry_btn.setCursor(Qt.PointingHandCursor)
        self.retry_btn.clicked.connect(lambda: self.retry_requested.emit(self.input_path))
        self.retry_btn.setVisible(False)
        row.addWidget(self.retry_btn)

        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(icon("close", DANGER, 18))
        self.delete_btn.setToolTip("删除任务记录")
        self.delete_btn.setFixedSize(36, 36)
        self.delete_btn.setObjectName("action_btn_danger")
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.input_path))
        self.delete_btn.setVisible(False)
        row.addWidget(self.delete_btn)

        self._start_time = time.time()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_progress)
        
        if self.is_restored:
            self._restore_state()
        else:
            self._timer.start(2000)

    def _restore_state(self) -> None:
        """从缓存恢复任务状态，设置 UI 为已暂停或已完成。"""
        # 借用 _poll_progress 里的定位逻辑找到 manifest
        if not hasattr(self, "_cached_manifest"):
            self._cached_manifest = None
        if self.state_dir and not self._cached_manifest:
            from pathlib import Path
            from ..commands import REPO_ROOT
            state_root = REPO_ROOT / self.state_dir
            if state_root.exists() and state_root.is_dir():
                for d in state_root.iterdir():
                    if not d.is_dir():
                        continue
                    mp = d / "manifest.json"
                    if mp.exists():
                        try:
                            tmp_data = json.loads(mp.read_text(encoding="utf-8"))
                            sp = tmp_data.get("source_path")
                            if sp and Path(sp) == Path(self.input_path):
                                self._cached_manifest = mp
                                break
                        except Exception:
                            pass
        
        prog_text = ""
        is_done = False
        if self._cached_manifest and self._cached_manifest.exists():
            try:
                data = json.loads(self._cached_manifest.read_text(encoding="utf-8"))
                chapters = data.get("chapters", [])
                total = len(chapters)
                done = sum(1 for c in chapters if c.get("status") == "done")
                is_done = False
                
                if total > 0 and done == total:
                    events_path = self._cached_manifest.parent / "events.jsonl"
                    if events_path.exists():
                        try:
                            content = events_path.read_text(encoding="utf-8")
                            if '"event": "run_steps_finished"' in content:
                                is_done = True
                        except Exception:
                            pass
                
                if data.get("status") == "done":
                    is_done = True

                if total > 0:
                    prog_text = f"{done}/{total} 章"
                    self.prog_bar.setValue(int(done / total * 100))
            except Exception:
                pass
        
        if is_done:
            self.set_finished("success", "已完成")
        else:
            self.set_finished("cancelled", "已暂停")
            
        if prog_text:
            self.prog_lbl.setText(f"{prog_text} · 历史进度")
        else:
            self.prog_lbl.setText("暂无进度")

    def _poll_progress(self, force: bool = False) -> None:
        if not force and self.chip.property("state") != "running":
            return
            
        # 1. 更新用时
        elapsed = int(time.time() - self._start_time)
        m, s = divmod(elapsed, 60)
        h, m = divmod(m, 60)
        time_str = f"已用时 {h:02d}:{m:02d}:{s:02d}" if h > 0 else f"已用时 {m:02d}:{s:02d}"
        
        # 2. 读取进度
        prog_text = ""
        
        if not hasattr(self, "_cached_manifest"):
            self._cached_manifest = None
            
        if self.state_dir and not self._cached_manifest:
            from pathlib import Path
            from ..commands import REPO_ROOT
            state_root = REPO_ROOT / self.state_dir
            if state_root.exists() and state_root.is_dir():
                for d in state_root.iterdir():
                    if not d.is_dir():
                        continue
                    mp = d / "manifest.json"
                    if mp.exists():
                        try:
                            tmp_data = json.loads(mp.read_text(encoding="utf-8"))
                            sp = tmp_data.get("source_path")
                            if sp and Path(sp) == Path(self.input_path):
                                self._cached_manifest = mp
                                break
                        except Exception:
                            pass
                            
        if self._cached_manifest and self._cached_manifest.exists():
            try:
                data = json.loads(self._cached_manifest.read_text(encoding="utf-8"))
                chapters = data.get("chapters", [])
                total = len(chapters)
                done = sum(1 for c in chapters if c.get("status") == "done")
                
                if total > 0:
                    pct = int(done / total * 100)
                    prog_text = f"{done}/{total} 章 · {pct}%"
                    self.prog_bar.setValue(pct)
            except Exception:
                pass
        
        # 组合显示
        if prog_text:
            self.prog_lbl.setText(f"{prog_text} · {time_str}")
        else:
            self.prog_lbl.setText(f"处理中… · {time_str}")

    def set_status(self, text: str, state: str = "running") -> None:
        if not text.startswith("● "):
            text = f"● {text}"
        self.chip.setText(text)
        self.chip.setProperty("state", state)
        self.chip.style().unpolish(self.chip)
        self.chip.style().polish(self.chip)

    def set_finished(self, state_code: str, status_text: str) -> None:
        self.stop_btn.setVisible(False)
        self.delete_btn.setVisible(True)
        
        if state_code == "cancelled":
            self.chip.setProperty("state", "default")
            self.retry_btn.setVisible(True)
            self.open_dir_btn.setVisible(False)
        elif state_code == "success":
            self.chip.setProperty("state", "done")
            self.retry_btn.setVisible(False)
            self.open_dir_btn.setVisible(True)
        else:
            self.chip.setProperty("state", "error")
            self.retry_btn.setVisible(True)
            self.open_dir_btn.setVisible(False)
            
        self.chip.setText(f"● {status_text}")
        self.chip.style().unpolish(self.chip)
        self.chip.style().polish(self.chip)
        
        # 强制刷新进度显示
        self._poll_progress(force=True)
        
        # 强制刷新样式
        self.chip.style().unpolish(self.chip)
        self.chip.style().polish(self.chip)
        
        if self._timer.isActive():
            self._timer.stop()
