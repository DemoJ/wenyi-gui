from __future__ import annotations

import json

from .commands import RUNTIME_ROOT

RECENT_FILE = RUNTIME_ROOT / "recent_tasks.json"


def load_recent() -> dict[str, str]:
    """input_path(绝对) -> 书名，GUI 本地记录以便续跑时定位源文件。"""
    try:
        return json.loads(RECENT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_recent(data: dict[str, str]) -> None:
    RECENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RECENT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
