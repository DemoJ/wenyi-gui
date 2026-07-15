from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def main() -> None:
    output = Path(sys.argv[1])
    source = Path(__file__).resolve().parent / "assets" / "wenyi.svg"
    image = QImage(256, 256, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    renderer = QSvgRenderer(QByteArray(source.read_bytes()))
    renderer.render(painter, QRectF(0, 0, 256, 256))
    painter.end()
    if not image.save(str(output), "PNG"):
        raise RuntimeError(f"图标生成失败：{output}")


if __name__ == "__main__":
    main()
