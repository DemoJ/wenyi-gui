# Wenyi GUI

Wenyi GUI 是 [Wenyi](https://github.com/BigDawnGhost/wenyi) 的第三方桌面图形界面，由本仓库独立维护。GUI 使用 PySide6 构建，并通过子进程调用 Wenyi CLI。

本项目不属于 Wenyi 官方仓库。为了在上游尚未发布 Python 包或核心可执行文件时仍可开发和构建，Wenyi 核心源码放在 `vendor/wenyi/`，但不会提交到本仓库。

## 项目结构

```text
wenyi-gui/
├─ .github/workflows/     # GUI 测试和 Windows 构建
├─ docs/                  # GUI 项目文档
├─ gui/                   # GUI 源码及测试
├─ vendor/wenyi/          # Wenyi 上游源码，本地克隆且不提交
├─ build-windows.ps1      # Windows 完整发行包构建脚本
├─ main.py                # GUI 开发和打包入口
└─ pyproject.toml         # GUI 项目依赖
```

运行时产生的配置、任务记录、输出和状态默认保存在 `.runtime/`。打包后，这些文件保存在 `文译.exe` 所在目录。

## 准备核心

首次开发前，将上游源码克隆到固定目录：

```powershell
git clone https://github.com/BigDawnGhost/wenyi.git vendor/wenyi
```

更新核心时：

```powershell
git -C vendor/wenyi pull --ff-only
```

`vendor/wenyi/` 是独立的本地仓库，并已被根目录 `.gitignore` 忽略。不要在其中实现 GUI 功能；核心修复应优先提交给上游项目。

## 开发运行

需要 Python 3.10+、[uv](https://docs.astral.sh/uv/) 以及已经准备好的 `vendor/wenyi/`：

```powershell
uv sync
uv run python main.py
```

也可以使用项目安装的命令入口：

```powershell
uv run wenyi-gui
```

GUI 在开发环境中执行以下核心命令：

```powershell
uv run --project vendor/wenyi trans-novel
```

运行 GUI 测试：

```powershell
uv run pytest
```

## Windows 构建

```powershell
.\build-windows.ps1
```

脚本会分别构建 Wenyi 核心和 GUI，然后生成：

```text
dist/文译/
├─ 文译.exe
├─ trans-novel.exe
├─ LICENSE.txt
└─ licenses/WENYI-LICENSE.txt
```

最终用户不需要安装 Python 或 uv。发布时应压缩并分发整个 `dist/文译/` 目录。

更多说明参见 [Windows 构建文档](docs/windows-build.md)。

## 问题归属

- GUI 界面、任务管理、桌面打包问题：提交到本仓库。
- 翻译能力、CLI、格式解析和模型调用问题：优先提交到 [Wenyi](https://github.com/BigDawnGhost/wenyi)。
- GUI 对核心内部接口的兼容补丁位于 `gui/wrapper.py`，上游核心升级后应重点验证该文件。

## 许可证

Wenyi GUI 代码使用 [MIT License](LICENSE)。Wenyi 核心使用其自己的 MIT License，详见 `vendor/wenyi/LICENSE`。发布包会保留该许可证。
