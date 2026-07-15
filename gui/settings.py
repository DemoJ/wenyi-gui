from __future__ import annotations

import json

from .commands import CONFIG_PATH, RUNTIME_ROOT, default_prefix

SETTINGS_FILE = RUNTIME_ROOT / "settings.json"


def default_settings() -> dict[str, str]:
    return {
        "config_path": str(CONFIG_PATH),
        "api_key": "",
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com",
        "prefix": " ".join(default_prefix()),
        "state_dir": str(RUNTIME_ROOT / "state"),
        "output_dir": str(RUNTIME_ROOT / "output"),
        "model_strong": "deepseek-v4-pro",
        "model_cheap": "deepseek-v4-flash",
        "model_fast": "deepseek-v4-flash",
        "max_tokens": "4096",
    }


def load_settings() -> dict[str, str]:
    data = default_settings()

    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        data.update({k: v for k, v in saved.items() if k in data})
    except Exception:
        pass
    if data["config_path"] == "config.yaml":
        data["config_path"] = str(CONFIG_PATH)
    if data["prefix"].startswith("uv "):
        data["prefix"] = " ".join(default_prefix())
    return data


def save_settings(data: dict[str, str]) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
