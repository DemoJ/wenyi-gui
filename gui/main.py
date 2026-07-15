from __future__ import annotations

import sys

import os
import ctypes

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .commands import prepare_runtime
from .theme import apply_theme, icon, ACCENT


def main() -> int:
    prepare_runtime()
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("diyun.wenyi.transnovel.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app_icon = icon("logo", ACCENT, 256)
    app.setWindowIcon(app_icon)
    apply_theme(app)
    app.setApplicationName("文译")
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    win = MainWindow()
    win.setWindowIcon(app_icon)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
