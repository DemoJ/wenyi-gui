from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainterPath, QRegion
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .commands import REPO_ROOT, build_argv, generate_task_config, resolve_runtime_path
from .runner import CommandRunner
from .settings import load_settings
from .widgets.home_page import HomePage
from .widgets.log_dialog import LogDialog
from .widgets.settings_page import SettingsPage
from .widgets.sidebar import Sidebar
from .widgets.task_config_dialog import TaskConfigDialog
from .widgets.title_bar import TitleBar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(1000, 720)
        self.settings = load_settings()

        # 活跃翻译注册表
        self._runners: dict[str, CommandRunner] = {}
        self._log_buffers: dict[str, list[str]] = {}
        self._log_dialogs: dict[str, LogDialog] = {}

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(0)

        frame = QWidget()
        frame.setObjectName("frame")
        frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        root.addWidget(frame)
        self._frame = frame
        self._frame_radius = 8

        shadow = QGraphicsDropShadowEffect(frame)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(17, 18, 23, 70))
        frame.setGraphicsEffect(shadow)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        frame_layout.addWidget(TitleBar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        frame_layout.addLayout(body, 1)

        body.addWidget(self._build_sidebar())

        self.pages = QStackedWidget()
        body.addWidget(self.pages, 1)

        self.home = HomePage()
        self.home.open_task.connect(self._open_task)
        self.home.stop_requested.connect(self._stop_task)
        self.home.log_requested.connect(self._show_log)
        self.home.retry_requested.connect(self._retry_task)
        self.home.delete_requested.connect(self._confirm_delete_task)
        self.home.open_dir_requested.connect(self._open_result_dir)
        self.settings_page = SettingsPage(self.settings)
        self.settings_page.saved.connect(self._on_settings_saved)

        self.pages.addWidget(self.home)          # index 0
        self.pages.addWidget(self.settings_page)  # index 1

        self.nav.set_current(0)
        self._load_persisted_tasks()

    def _load_persisted_tasks(self) -> None:
        from .tasks import load_recent, save_recent
        state_dir = self.settings.get("state_dir", "state")
        recents = load_recent()
        new_recents = {}
        migrated = False
        
        # recent_tasks.json is a dict mapping input_path -> title (or dict with title and config)
        # Iterating over it gives oldest first (if insertion order is preserved),
        # and add_active_task inserts at index 0, so the newest task will end up at the top.
        for input_path, val in recents.items():
            norm_path = str(Path(input_path).resolve().absolute())
            if norm_path != input_path:
                migrated = True
            
            new_recents[norm_path] = val
            
            try:
                if isinstance(val, dict):
                    title = val.get("title", Path(norm_path).stem)
                    state_dir = val.get("state_dir", self.settings.get("state_dir", "state"))
                else:
                    title = val
                    state_dir = self.settings.get("state_dir", "state")
                self.home.add_active_task(norm_path, title, state_dir, is_restored=True)
            except Exception as e:
                print(f"恢复历史任务 {input_path} 失败: {e}")
            
        if migrated:
            save_recent(new_recents)

    def _build_sidebar(self) -> QWidget:
        self.nav = Sidebar()
        self.nav.currentChanged.connect(self._switch)
        return self.nav

    def _apply_frame_mask(self) -> None:
        r = self._frame_radius
        path = QPainterPath()
        path.addRoundedRect(self._frame.rect(), r, r)
        self._frame.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_frame_mask()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_frame_mask()

    def closeEvent(self, event) -> None:
        running_runners = [r for r in self._runners.values() if r.is_active()]
        if not running_runners:
            event.accept()
            return
            
        reply = QMessageBox.question(
            self, "退出程序",
            f"当前有 {len(running_runners)} 个正在运行的翻译任务。\n强制退出将中断这些任务（已完成的进度将保留）。是否确认退出？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            event.ignore()
            return
            
        # 确认退出，停止所有运行中的任务并等待其结束
        for r in running_runners:
            r.stop()
            
        import time
        from PySide6.QtWidgets import QApplication
        start_time = time.time()
        while time.time() - start_time < 3.5:
            QApplication.processEvents()
            if all(not r.is_active() for r in running_runners):
                break
            time.sleep(0.1)
            
        if any(r.is_active() for r in running_runners):
            QMessageBox.warning(self, "退出超时", "部分任务未能完全响应停止指令，程序将被强制关闭。")
            
        event.accept()

    def _switch(self, row: int) -> None:
        if row == 0:
            self.pages.setCurrentWidget(self.home)
        elif row == 1:
            self.pages.setCurrentWidget(self.settings_page)

    # ── 翻译任务管理 ──

    def _open_task(self, input_path: str) -> None:
        """选书后的入口：弹出配置 -> 创建 runner -> 加入活跃列表。"""
        input_path = str(Path(input_path).resolve().absolute())
        
        # 已在运行则直接显示日志
        runner = self._runners.get(input_path)
        if runner and runner.is_active():
            self._show_log(input_path)
            return

        # 弹出任务配置
        dlg = TaskConfigDialog(input_path, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            config = dlg.get_config()
            self._start_task(input_path, config)

    def _start_task(self, input_path: str, config: dict[str, str]) -> None:
        title = Path(input_path).stem
        fmt = config["format"]

        # 提前计算输出路径以进行覆盖/冲突校验
        od = (self.settings.get("output_dir", "") or "").strip()
        if od:
            od_path = Path(od)
            if not od_path.is_absolute():
                od_path = resolve_runtime_path(od)
            out_dir = od_path
        else:
            out_dir = Path(input_path).parent
            
        # 验证并创建输出目录
        try:
            if out_dir.exists() and not out_dir.is_dir():
                raise RuntimeError("输出路径已存在且不是一个目录。")
            out_dir.mkdir(parents=True, exist_ok=True)
            
            # 测试写入权限
            import uuid
            test_file = out_dir / f".write_test_{uuid.uuid4().hex}"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "输出目录无效", f"无法使用指定的输出目录：\n{out_dir}\n\n错误信息：{e}\n\n请检查路径是否合法且具备写入权限。")
            return

        if fmt == "txt":
            out_files = [out_dir / f"{title}.zh.txt"]
        elif fmt == "epub-bilingual":
            out_files = [out_dir / f"{title}.zh-bi.epub"]
        else:
            out_files = [out_dir / f"{title}.zh.epub"]

        # 检查是否有其他正在运行的任务占用同一个输出文件
        for r_path, r in self._runners.items():
            if r.is_active():
                r_out_files = getattr(r, 'target_out_files', [])
                for out_file in out_files:
                    if out_file in r_out_files:
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.warning(self, "输出冲突", f"另一个正在运行的任务将输出到同一个文件：\n{out_file}\n\n为避免冲突，请等待其完成或修改输出目录。")
                        return

        # 检查输出文件是否已存在（仅提示，允许覆盖）
        existing_files = [f for f in out_files if f.exists()]
        if existing_files:
            from PySide6.QtWidgets import QMessageBox
            file_list_str = "\n".join(str(f) for f in existing_files)
            reply = QMessageBox.question(
                self,
                "文件已存在",
                f"以下目标输出文件已存在：\n{file_list_str}\n\n翻译完成后该文件将被无情覆盖。是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # 生成任务独立的临时配置文件，避免并发写入竞态
        lang = config["source_lang"]
        base_config_path = self._config()
        state_dir = self.settings.get("state_dir", "state").strip()
        
        try:
            task_config_path = generate_task_config(base_config_path, lang, state_dir=state_dir)
        except RuntimeError as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "配置生成失败", str(e))
            return

        # 创建 runner 并连接信号
        runner = CommandRunner(self)
        runner.target_out_files = out_files
        runner.log.connect(lambda line, p=input_path, r=runner: self._on_task_log(p, line, r))
        runner.status_changed.connect(lambda text, p=input_path, r=runner: self._on_task_status(p, text, r))
        runner.finished.connect(
            lambda code, cancelled, p=input_path, r=runner: self._on_task_finished(p, code, cancelled, r)
        )
        self._runners[input_path] = runner
        import collections
        self._log_buffers[input_path] = collections.deque(maxlen=2000)

        # 添加活跃任务到首页
        state_dir = self.settings.get("state_dir", "state")
        self.home.add_active_task(input_path, title, state_dir)

        # 记录最近任务及其配置 (包含 state_dir 和 独立配置文件路径)
        task_info = {
            "config": config,
            "state_dir": state_dir,
            "out_files": [str(f) for f in out_files],
            "task_config_path": str(task_config_path)
        }
        self._remember(input_path, task_info=task_info)

        # 构建命令
        fmt = config["format"]
        if fmt == "txt":
            args = ["translate", input_path, "--format", "txt", "--mono", "--no-bilingual"]
        elif fmt == "epub-bilingual":
            args = ["translate", input_path, "--format", "epub", "--bilingual", "--no-mono"]
        else:
            args = ["translate", input_path, "--format", "epub", "--mono", "--no-bilingual"]

        od = (self.settings.get("output_dir", "") or "").strip()
        if od:
            if fmt == "epub-bilingual":
                args += ["--out", str(out_dir / f"{title}.zh.epub")]
            else:
                args += ["--out", str(out_files[0])]
        
        argv = build_argv(self._prefix(), task_config_path, args)
        env = self._env()
        runner.start(argv, env or None, str(REPO_ROOT))

    def _retry_task(self, input_path: str) -> None:
        """继续翻译：跳过弹窗，直接使用保存的配置或默认配置启动。"""
        runner = self._runners.get(input_path)
        if runner and runner.is_active():
            self._show_log(input_path)
            return

        from .tasks import load_recent
        recent = load_recent()
        val = recent.get(input_path, {})
        if isinstance(val, dict):
            config = val.get("config", {})
        else:
            config = {}
            
        if not config:
            config = {"source_lang": "auto", "format": "epub"}
            
        self._delete_task(input_path, clear_cache=False)
        self._start_task(input_path, config)

    def _confirm_delete_task(self, input_path: str) -> None:
        title = Path(input_path).stem
        reply = QMessageBox.question(
            self, "删除任务",
            f"确认删除《{title}》的翻译任务？\n这将永久清理该任务的进度和缓存文件，且不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_task(input_path, clear_cache=True)

    def _open_result_dir(self, input_path: str) -> None:
        import os
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        from .tasks import load_recent
        recent = load_recent().get(input_path)
        out_files = []
        if isinstance(recent, dict):
            out_files = recent.get("out_files", [])
            
        if out_files and out_files[0]:
            target_dir = os.path.dirname(out_files[0])
        else:
            target_dir = os.path.dirname(input_path)
            
        if os.path.exists(target_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(target_dir))
        else:
            QMessageBox.warning(self, "未找到目录", f"输出目录不存在：\n{target_dir}")

    def _delete_task(self, input_path: str, clear_cache: bool = True) -> None:
        """删除任务：停止后台如果运行，清理日志和界面列表，可选清理缓存。"""
        from .tasks import load_recent
        recent = load_recent().get(input_path)
        state_dir_str = "state"
        if isinstance(recent, dict):
            state_dir_str = recent.get("state_dir", "state")
            
        runner = self._runners.get(input_path)
        if runner and runner.is_active():
            runner._pending_delete = True
            runner._pending_clear_cache = clear_cache
            runner._pending_state_dir = state_dir_str
            runner.stop()
            self.home.update_task_status(input_path, "正在删除…")
            return
            
        if runner:
            self._runners.pop(input_path, None)
        
        self._log_buffers.pop(input_path, None)
        dlg = self._log_dialogs.pop(input_path, None)
        if dlg:
            dlg.close()
        
        self.home.remove_active_task(input_path)
        self._forget(input_path)

        if clear_cache:
            import shutil
            import json
            from PySide6.QtCore import QTimer
            
            state_dir_str = getattr(runner, "_pending_state_dir", state_dir_str) if runner else state_dir_str
            target_state_dir = resolve_runtime_path(state_dir_str)
            
            def _do_rmtree():
                if target_state_dir.exists() and target_state_dir.is_dir():
                    for d in target_state_dir.iterdir():
                        if not d.is_dir():
                            continue
                        manifest = d / "manifest.json"
                        if manifest.exists():
                            try:
                                data = json.loads(manifest.read_text(encoding="utf-8"))
                                sp = data.get("source_path")
                                if sp and Path(sp) == Path(input_path):
                                    shutil.rmtree(d, ignore_errors=True)
                                    break
                            except Exception:
                                pass
                        
            # 延迟 500ms 执行删除，确保底层进程已完全退出且文件锁已释放
            QTimer.singleShot(500, _do_rmtree)

    def _stop_task(self, input_path: str) -> None:
        """停止翻译：确认弹窗 → 终止进程。"""
        title = Path(input_path).stem
        reply = QMessageBox.question(
            self, "停止翻译",
            f"确认停止《{title}》的翻译？\n已完成进度将保留。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            runner = self._runners.get(input_path)
            if runner:
                runner.stop()

    def _show_log(self, input_path: str) -> None:
        """打开日志弹窗（非模态，翻译继续运行）。"""
        dlg = self._log_dialogs.get(input_path)
        if dlg:
            dlg.raise_()
            dlg.activateWindow()
            return

        title = Path(input_path).stem
        dlg = LogDialog(title, self)
        for line in self._log_buffers.get(input_path, []):
            dlg.append(line)
        dlg.finished.connect(lambda _, p=input_path: self._log_dialogs.pop(p, None))
        self._log_dialogs[input_path] = dlg
        dlg.show()

    # ── runner 信号处理 ──

    def _on_task_log(self, input_path: str, line: str, runner: CommandRunner) -> None:
        if self._runners.get(input_path) is not runner:
            return
        if input_path in self._log_buffers:
            self._log_buffers[input_path].append(line)
        dlg = self._log_dialogs.get(input_path)
        if dlg:
            dlg.append(line)

    def _on_task_status(self, input_path: str, text: str, runner: CommandRunner) -> None:
        if self._runners.get(input_path) is not runner:
            return
        self.home.update_task_status(input_path, text)

    def _on_task_finished(self, input_path: str, exit_code: int, cancelled: bool, runner: CommandRunner) -> None:
        if self._runners.get(input_path) is not runner:
            return
            
        if getattr(runner, "_pending_delete", False):
            self._delete_task(input_path, clear_cache=getattr(runner, "_pending_clear_cache", False))
            return
            
        if cancelled:
            self.home.set_task_finished(input_path, "cancelled", "已暂停")
        elif exit_code != 0:
            self.home.set_task_finished(input_path, "error", "错误")
        else:
            self.home.set_task_finished(input_path, "success", "已完成")

    # ── 命令构建辅助 ──

    def _prefix(self) -> list[str]:
        import sys
        if getattr(sys, "frozen", False):
            from .commands import default_prefix
            return default_prefix()
        prefix = self.settings.get("prefix", "").split()
        if not prefix:
            from .commands import default_prefix
            return default_prefix()
        if prefix[-1] == "trans-novel":
            from .commands import GUI_DIR
            prefix[-1] = "python"
            prefix.append(str(GUI_DIR / "wrapper.py"))
        return prefix

    def _config(self) -> str:
        p = Path(self.settings.get("config_path", "config.yaml"))
        if not p.is_absolute():
            p = resolve_runtime_path(str(p))
        return str(p)

    def _env(self) -> dict[str, str]:
        provider = self.settings.get("provider", "deepseek")
        if provider == "fake":
            return {}
        key = self.settings.get("api_key", "")
        if not key:
            return {}
        api_env = f"{provider.upper().replace('-', '_')}_API_KEY"
        # 同时设置旧版默认的 DEEPSEEK_API_KEY 和动态的 env，确保向下/向上的兼容性
        env = {
            "DEEPSEEK_API_KEY": key,
            api_env: key,
        }
        max_tokens = self.settings.get("max_tokens", "4096")
        if max_tokens:
            env["GUI_MAX_TOKENS"] = max_tokens
        return env

    # ── 其他 ──

    def _remember(self, input_path: str, task_info: dict | None = None, config: dict[str, str] | None = None) -> None:
        from .tasks import load_recent, save_recent

        recent = load_recent()
        if input_path in recent:
            old_val = recent[input_path]
            del recent[input_path]
        else:
            old_val = Path(input_path).stem
            
        title = Path(input_path).stem
        if isinstance(old_val, dict):
            title = old_val.get("title", title)
            saved_data = old_val.copy()
        else:
            title = old_val
            saved_data = {"title": title}
            
        if task_info is not None:
            saved_data.update(task_info)
        elif config is not None:
            saved_data["config"] = config
            
        saved_data["title"] = title
        recent[input_path] = saved_data
        save_recent(recent)

    def _forget(self, input_path: str) -> None:
        from .tasks import load_recent, save_recent
        recent = load_recent()
        if input_path in recent:
            val = recent[input_path]
            if isinstance(val, dict):
                config_path = val.get("task_config_path")
                if config_path:
                    try:
                        Path(config_path).unlink(missing_ok=True)
                    except Exception:
                        pass
            del recent[input_path]
            save_recent(recent)

    def _on_settings_saved(self, data: dict[str, str]) -> None:
        self.settings = data
