from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..commands import REPO_ROOT, build_argv
from ..runner import CommandRunner
from ..widgets.log_view import LogView


class TaskPage(QWidget):
    go_home = Signal()

    def __init__(self, input_path: str, settings: dict[str, str],
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.input_path = input_path
        self.settings = settings
        self.runner = CommandRunner(self)
        self.runner.log.connect(self._on_log)
        self.runner.status_changed.connect(self._on_status)
        self.runner.finished.connect(self._on_finished)
        self._build_ui()
        self.title_label.setText(Path(input_path).name)
        self.log.append(f"已载入：{input_path}（开始翻译将自动续跑已有进度）")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        top = QHBoxLayout()
        back = QPushButton("← 首页")
        back.setObjectName("ghost")
        back.clicked.connect(self.go_home)
        top.addWidget(back)
        top.addStretch(1)
        self.title_label = QLabel("未选择文件")
        self.title_label.setObjectName("title")
        top.addWidget(self.title_label)
        root.addLayout(top)

        root.addWidget(self._action_card())

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.log = LogView()
        root.addWidget(self.log, 1)

    def _action_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        row = QHBoxLayout(card)
        row.setContentsMargins(18, 14, 18, 14)
        row.setSpacing(12)
        self.run_btn = QPushButton("开始 / 继续翻译")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self._run_translate)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.runner.stop)
        row.addWidget(self.run_btn)
        row.addWidget(self.stop_btn)
        row.addStretch(1)
        return card

    def set_settings(self, settings: dict[str, str]) -> None:
        self.settings = settings

    def _run(self, sub_args: list[str], cwd: str | None = None) -> None:
        if not self.input_path:
            self.log.append("[提示] 请先选择电子书文件。")
            return
        if self.runner.is_running():
            self.log.append("[提示] 当前已有翻译进程在运行。")
            return
        argv = build_argv(self._prefix(), self._config(), sub_args)
        env = self._env()
        self.log.append("> " + " ".join(argv))
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress.setVisible(True)
        self.runner.start(argv, env or None, cwd or str(REPO_ROOT))

    def _run_translate(self) -> None:
        args = ["translate", self.input_path, "--format", "epub"]
        od = (self.settings.get("output_dir", "") or "").strip()
        if od:
            stem = Path(self.input_path).stem
            args += ["--out", str(Path(od) / f"{stem}.zh.epub")]
        self._run(args)

    def _prefix(self) -> list[str]:
        return self.settings.get("prefix", "").split()

    def _config(self) -> str:
        return self.settings.get("config_path", "config.yaml")

    def _env(self) -> dict[str, str]:
        # 选「离线测试」时不需要 Key；否则把用户填写的 Key 通过环境变量注入子进程
        # （与 config.yaml 默认的 api_key_env 保持一致，对用户不可见）
        if self.settings.get("provider") == "fake":
            return {}
        key = self.settings.get("api_key", "")
        if not key:
            return {}
        return {"DEEPSEEK_API_KEY": key}

    def _on_log(self, line: str) -> None:
        self.log.append(line)

    def _on_status(self, text: str) -> None:
        self.progress.setFormat(text)

    def _on_finished(self, exit_code: int, cancelled: bool) -> None:
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setVisible(False)
        if cancelled:
            self.log.append("[已取消] 进程已终止，已完成进度保留，可继续翻译。")
        else:
            self.log.append(f"[结束] 退出码 {exit_code}")
