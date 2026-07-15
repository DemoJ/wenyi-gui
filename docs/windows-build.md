# Windows GUI 构建

## 前置条件

- Windows 10 或 Windows 11
- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- 位于 `vendor/wenyi/` 的 Wenyi 上游源码

首次准备核心：

```powershell
git clone https://github.com/BigDawnGhost/wenyi.git vendor/wenyi
```

## 构建

在项目根目录执行：

```powershell
.\build-windows.ps1
```

脚本执行以下步骤：

1. 使用 `vendor/wenyi/pyproject.toml` 创建核心构建环境。
2. 将 `gui/wrapper.py` 打包为单文件 `trans-novel.exe`。
3. 使用根目录 `pyproject.toml` 构建 PySide6 GUI。
4. 将核心、GUI、默认配置和许可证整理到 `dist/文译/`。

构建结果：

```text
dist/文译/
├─ 文译.exe
├─ trans-novel.exe
├─ LICENSE.txt
└─ licenses/
   └─ WENYI-LICENSE.txt
```

## 验证

验证核心入口：

```powershell
.\dist\文译\trans-novel.exe --help
```

随后启动 `dist/文译/文译.exe`，确认配置初始化、设置保存、任务启动和停止功能正常。发布时压缩整个 `dist/文译/`，不能只分发 `文译.exe`。

## 核心版本

本地构建使用 `vendor/wenyi/` 当前检出的提交。发布前建议记录版本：

```powershell
git -C vendor/wenyi rev-parse HEAD
```

GitHub Actions 默认检出上游 `main` 最新版本。如需可复现发布，应在工作流的核心 checkout 步骤中设置固定的 `ref`。
