from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent
GUI_ROOT = GUI_DIR.parent
CORE_ROOT = GUI_ROOT / "vendor" / "wenyi"
FROZEN = getattr(sys, "frozen", False)
APP_DIR = Path(sys.executable).resolve().parent if FROZEN else GUI_ROOT
RUNTIME_ROOT = APP_DIR if FROZEN else GUI_ROOT / ".runtime"
REPO_ROOT = RUNTIME_ROOT
CONFIG_PATH = RUNTIME_ROOT / "config.yaml"

# 项目实际支持的 LLM 提供商（与 trans_novel/llm/base.py 保持一致）
LLM_PROVIDERS = [
    "deepseek",
    "openai",
    "openrouter",
    "openai-compatible",
    "ollama",
    "vllm",
    "fake"
]


def default_prefix() -> list[str]:
    """返回开发环境或打包环境中的核心命令入口。"""
    if FROZEN:
        return [str(APP_DIR / "trans-novel.exe")]
    return ["uv", "run", "--project", str(CORE_ROOT), "trans-novel"]


def prepare_runtime() -> None:
    """在程序根目录创建运行目录，并在首次运行时放置默认配置。"""
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        return
    bundled_root = Path(getattr(sys, "_MEIPASS", GUI_ROOT))
    source = bundled_root / "config.yaml"
    if not source.exists():
        source = CORE_ROOT / "config.yaml"
    if not source.exists():
        raise FileNotFoundError(
            "未找到 Wenyi 核心配置。请将上游仓库克隆到 "
            f"{CORE_ROOT}"
        )
    shutil.copy2(source, CONFIG_PATH)


def resolve_runtime_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else REPO_ROOT / path


def build_argv(prefix: list[str], config_path: str, subcommand_args: list[str]) -> list[str]:
    """拼接完整 argv：前缀 --config <路径> <子命令参数>。"""
    return [*prefix, "--config", config_path, *subcommand_args]


def update_yaml_config(config_path: str, provider: str, base_url: str, models: dict[str, str]) -> None:
    """原子化更新 YAML 配置，一次性修改并利用 os.replace 保证安全性。"""
    from pathlib import Path
    import os
    path = Path(config_path)
    if not path.is_absolute():
        path = resolve_runtime_path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到配置文件: {config_path}")
        
    text = path.read_text(encoding="utf-8")
    
    # 1. Update provider
    if provider not in LLM_PROVIDERS:
        raise ValueError(f"不支持的 provider: {provider}")
    
    text, n = re.subn(
        r"(?m)^(  provider:).*$",
        f"  provider: {provider}",
        text,
        count=1,
    )
    if n == 0:
        text, n2 = re.subn(
            r"(?m)^(llm:\s*)$",
            f"\\1\n  provider: {provider}",
            text,
            count=1,
        )
        if n2 == 0:
            raise RuntimeError("更新 provider 失败，配置文件格式无法解析。")
            
    if provider != "fake":
        api_env = f"{provider.upper().replace('-', '_')}_API_KEY"
        text = re.sub(
            r"(?m)^(  api_key_env:).*$",
            f"  api_key_env: {api_env}",
            text,
            count=1,
        )
        
    # 2. Update base_url
    text, n = re.subn(
        r"(?m)^(  base_url:).*$",
        f"  base_url: {base_url}",
        text,
        count=1,
    )
    if n == 0:
        raise RuntimeError("更新 base_url 失败，配置文件格式无法解析。")
        
    # 3. Update models
    lines = text.splitlines()
    tier: str | None = None
    modified_count = 0
    for i, line in enumerate(lines):
        m = re.match(r"^    (strong|cheap|fast):\s*$", line)
        if m:
            tier = m.group(1)
            continue
        if tier is not None:
            m2 = re.match(r"^(      model:\s*)(.*?)(\s*#.*)?$", line)
            if m2 and tier in models:
                lines[i] = f"{m2.group(1)}{models[tier]}{m2.group(3) or ''}"
                modified_count += 1
                tier = None
                
    if models and modified_count < len(models):
        raise RuntimeError(f"更新 models 失败，需要更新 {len(models)} 个，但只找到了 {modified_count} 个。")
        
    text = "\n".join(lines) + "\n"
    
    # 4. Atomic write
    tmp_path = path.with_suffix(".yaml.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(str(tmp_path), str(path))


def read_config_base_url(config_path: str) -> str:
    """读取配置文件 llm.base_url 的值。"""
    path = Path(config_path)
    if not path.is_absolute():
        path = resolve_runtime_path(config_path)
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
        m = re.search(r"(?m)^  base_url:\s*(.+?)(?:\s*#.*)?$", text)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return ""


def read_config_models(config_path: str) -> dict[str, str]:
    """读取配置文件 llm.tiers 下 strong / cheap / fast 各档的 model 值。"""
    result: dict[str, str] = {}
    path = Path(config_path)
    if not path.is_absolute():
        path = resolve_runtime_path(config_path)
    if not path.exists():
        return result
    try:
        tier: str | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^    (strong|cheap|fast):\s*$", line)
            if m:
                tier = m.group(1)
                continue
            if tier is not None:
                m2 = re.match(r"^      model:\s*(.+?)(?:\s*#.*)?$", line)
                if m2:
                    result[tier] = m2.group(1).strip()
                    tier = None
    except Exception:
        pass
    return result


import uuid

def generate_task_config(config_path: str, lang: str, state_dir: str = "") -> str:
    """生成一个包含特定 source_lang 和 state_dir 的临时独立配置文件，供当前任务独占使用。
    返回生成的新配置文件的绝对路径。
    """
    path = Path(config_path)
    if not path.is_absolute():
        path = resolve_runtime_path(config_path)
    if not path.exists():
        raise RuntimeError(f"基础配置文件不存在：{path}")
        
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"读取基础配置文件失败：{e}")
        
    if not text.strip():
        raise RuntimeError("基础配置文件为空。")

    new_text, n = re.subn(
        r"(?m)^(  source:).*$",
        f"\\1 {lang}",
        text,
        count=1,
    )
    if n == 0:
        new_text = re.sub(
            r"(?m)^(language:\s*)$",
            f"\\1\n  source: {lang}",
            text,
            count=1,
        )
        
    if state_dir:
        # Note: Windows paths might contain backslashes, so we convert to forward slashes to avoid yaml issues
        safe_state_dir = state_dir.replace("\\", "/")
        new_text, n = re.subn(
            r"(?m)^(  state_dir:).*$",
            f"\\1 {safe_state_dir}",
            new_text,
            count=1,
        )
        if n == 0:
            new_text = re.sub(
                r"(?m)^(paths:\s*)$",
                f"\\1\n  state_dir: {safe_state_dir}",
                new_text,
                count=1,
            )

    config_dir = REPO_ROOT / "task-configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    task_config_path = config_dir / f"config_{uuid.uuid4().hex}.yaml"
    
    try:
        task_config_path.write_text(new_text, encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"写入独立任务配置文件失败：{e}")
        
    return str(task_config_path.absolute())
