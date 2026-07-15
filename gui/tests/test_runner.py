from __future__ import annotations

import sys
import time

import pytest

QCoreApplication = pytest.importorskip("PySide6.QtCore").QCoreApplication

from gui.runner import CommandRunner


def _wait_until(predicate, timeout: float = 8.0) -> bool:
    app = QCoreApplication.instance() or QCoreApplication([])
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_stop_finishes_running_process() -> None:
    runner = CommandRunner()
    statuses: list[str] = []
    results: list[tuple[int, bool]] = []
    runner.status_changed.connect(statuses.append)
    runner.finished.connect(lambda code, cancelled: results.append((code, cancelled)))

    runner.start([sys.executable, "-c", "import time; time.sleep(30)"])
    assert _wait_until(runner.is_active, timeout=3)

    runner.stop()

    started_stopping = time.monotonic()
    assert _wait_until(lambda: bool(results))
    assert time.monotonic() - started_stopping < 3
    assert results[0][1] is True
    assert statuses[-1] == "正在停止…"
    assert not runner.is_active()


def test_finished_is_emitted_only_once() -> None:
    runner = CommandRunner()
    results: list[tuple[int, bool]] = []
    runner.finished.connect(lambda code, cancelled: results.append((code, cancelled)))

    runner._cancelled = True
    runner._emit_finished(-1)
    runner._emit_finished(-1)

    assert results == [(-1, True)]
