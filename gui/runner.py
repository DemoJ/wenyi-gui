from __future__ import annotations

import locale
import subprocess
import sys

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal


def _decode(data: bytes) -> str:
    """按可能编码依次尝试解码子进程输出，兼容 Windows 控制台编码。"""
    for enc in ("utf-8", locale.getpreferredencoding(False), "gbk", "cp936"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


class CommandRunner(QObject):
    """用 QProcess 启动 trans-novel 子进程，支持实时日志与取消（终止进程）。"""

    log = Signal(str)
    status_changed = Signal(str)
    finished = Signal(int, bool)  # exit_code, cancelled

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._proc = QProcess(self)
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(self._on_error)
        self._proc.started.connect(self._on_started)
        self._cancelled = False
        self._stop_requested = False
        self._termination_started = False
        self._finished_emitted = False
        self._stdout_buf = bytearray()
        self._stderr_buf = bytearray()
        self._kill_timer = QTimer(self)
        self._kill_timer.setSingleShot(True)
        self._kill_timer.timeout.connect(self._kill_if_running)
        self._stop_poll_timer = QTimer(self)
        self._stop_poll_timer.setInterval(100)
        self._stop_poll_timer.timeout.connect(self._poll_stopping_process)
        self._stop_watchdog = QTimer(self)
        self._stop_watchdog.setSingleShot(True)
        self._stop_watchdog.timeout.connect(self._finish_stuck_stop)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        error_msg = self._proc.errorString()
        if error == QProcess.ProcessError.FailedToStart:
            self.log.emit(f"启动失败: {error_msg}")
            self._emit_finished(-1)
        elif error == QProcess.ProcessError.Crashed:
            self.log.emit(f"进程崩溃: {error_msg}")
            # Note: Crashed usually also emits finished, so we don't emit it here.
        else:
            self.log.emit(f"进程错误: {error_msg}")

    def start(self, argv: list[str], env: dict[str, str] | None = None,
              cwd: str | None = None) -> None:
        self._cancelled = False
        self._stop_requested = False
        self._termination_started = False
        self._finished_emitted = False
        self._kill_timer.stop()
        self._stop_poll_timer.stop()
        self._stop_watchdog.stop()
        self.status_changed.emit("运行中…")
        env_obj = QProcessEnvironment.systemEnvironment()
        # 避免 GUI 自有 venv 的 VIRTUAL_ENV 触发 uv 的警告
        env_obj.remove("VIRTUAL_ENV")
        env_obj.remove("VIRTUAL_ENV_PROMPT")
        # 强制禁用缓冲，使得日志事实输出
        env_obj.insert("PYTHONUNBUFFERED", "1")
        if env:
            for key, value in env.items():
                env_obj.insert(key, value)
        self._proc.setProcessEnvironment(env_obj)
        if cwd:
            self._proc.setWorkingDirectory(cwd)
        self._proc.start(argv[0], argv[1:])

    def is_active(self) -> bool:
        return not self._finished_emitted and self._proc.state() in {
            QProcess.ProcessState.Starting,
            QProcess.ProcessState.Running,
        }

    def stop(self) -> None:
        self._stop_requested = True
        self._cancelled = True
        
        state = self._proc.state()
        if state in {QProcess.ProcessState.Running, QProcess.ProcessState.Starting}:
            self.status_changed.emit("正在停止…")
            self._stop_watchdog.start(2000)
            self._stop_poll_timer.start()
            if state == QProcess.ProcessState.Running:
                self._terminate_tree()

    def _on_started(self) -> None:
        if self._stop_requested:
            self._terminate_tree()

    def _terminate_tree(self) -> None:
        if self._termination_started:
            return
        self._termination_started = True
        pid = self._proc.processId()
        if sys.platform == "win32" and pid > 0:
            # 不在 GUI 线程等待 taskkill，否则系统命令卡顿或超时会冻结停止流程。
            try:
                subprocess.Popen(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except OSError as exc:
                self.log.emit(f"终止进程树失败，将强制结束主进程: {exc}")
        else:
            self._proc.terminate()

        self._kill_timer.start(1000)

    def _kill_if_running(self) -> None:
        if self._proc.state() in {
            QProcess.ProcessState.Starting,
            QProcess.ProcessState.Running,
        }:
            self._proc.kill()

    def _poll_stopping_process(self) -> None:
        if self._proc.state() == QProcess.ProcessState.NotRunning:
            self._emit_finished(-1)

    def _finish_stuck_stop(self) -> None:
        """极端情况下 Qt 未收到进程退出通知，也要解除界面的停止状态。"""
        if self._finished_emitted:
            return
        self._kill_if_running()
        self.log.emit("停止进程超时，已强制结束。")
        self._emit_finished(-1)

    def _on_stdout(self) -> None:
        self._stdout_buf.extend(bytes(self._proc.readAllStandardOutput()))
        self._process_buffer(self._stdout_buf)

    def _on_stderr(self) -> None:
        self._stderr_buf.extend(bytes(self._proc.readAllStandardError()))
        self._process_buffer(self._stderr_buf)

    def _process_buffer(self, buf: bytearray) -> None:
        while b"\n" in buf:
            idx = buf.index(b"\n")
            line_data = buf[:idx] # exclude \n
            del buf[:idx+1] # remove up to and including \n
            if line_data.endswith(b"\r"):
                line_data = line_data[:-1]
            self.log.emit(_decode(line_data))

    def _on_finished(self, exit_code: int, _exit_status) -> None:
        # flush remaining
        if self._stdout_buf:
            self.log.emit(_decode(self._stdout_buf))
            self._stdout_buf.clear()
        if self._stderr_buf:
            self.log.emit(_decode(self._stderr_buf))
            self._stderr_buf.clear()
            
        self._emit_finished(exit_code)

    def _emit_finished(self, exit_code: int) -> None:
        if self._finished_emitted:
            return
        self._finished_emitted = True
        self._kill_timer.stop()
        self._stop_poll_timer.stop()
        self._stop_watchdog.stop()
        self.finished.emit(exit_code, self._cancelled)
