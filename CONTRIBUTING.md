# 贡献指南

## 开发环境

```powershell
git clone https://github.com/BigDawnGhost/wenyi.git vendor/wenyi
uv sync
uv run pytest
uv run python main.py
```

## 目录边界

- `gui/` 只维护桌面 GUI、核心命令适配和 GUI 测试。
- `vendor/wenyi/` 是被忽略的独立上游仓库，不接受 GUI 改动。
- `.runtime/` 是本地运行数据，不应提交。
- `build-windows.ps1` 和 `.github/workflows/` 负责发行构建。

核心行为修改应优先向上游 Wenyi 提交。如果 GUI 必须临时兼容某个核心版本，请将修改限制在适配层，并在提交中说明对应的上游版本。

## 提交前检查

```powershell
uv run pytest
.\build-windows.ps1
.\dist\文译\trans-novel.exe --help
```
