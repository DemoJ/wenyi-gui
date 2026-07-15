from __future__ import annotations

from gui import commands


def test_development_paths_are_separated() -> None:
    assert commands.CORE_ROOT == commands.GUI_ROOT / "vendor" / "wenyi"
    assert commands.RUNTIME_ROOT == commands.GUI_ROOT / ".runtime"
    assert commands.CONFIG_PATH == commands.RUNTIME_ROOT / "config.yaml"


def test_default_prefix_runs_vendored_core() -> None:
    assert commands.default_prefix() == [
        "uv",
        "run",
        "--project",
        str(commands.CORE_ROOT),
        "trans-novel",
    ]
