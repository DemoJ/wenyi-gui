from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..commands import (
    LLM_PROVIDERS,
    read_config_base_url,
    read_config_models,
    update_yaml_config,
)
from ..settings import save_settings
from ..widgets.common import FlatCombo, PathField

# 下拉框展示名 → 实际 provider 值
_PROVIDER_LABELS = {
    "deepseek": "DeepSeek（默认）",
    "openai": "OpenAI",
    "openrouter": "OpenRouter",
    "openai-compatible": "OpenAI 兼容接口",
    "ollama": "Ollama (本地部署)",
    "vllm": "vLLM",
    "fake": "离线测试（Fake，不发网络请求）",
}

# (档位, 简洁标签, 悬停说明)，说明取自 config.yaml 对各档角色的描述
TIER_MODELS = [
    ("strong", "强力档模型", "翻译 / 润色 / 全局分析 / 标题"),
    ("cheap", "审校档模型", "审校 / 一致性 QA / 回译比对（判断类，保留思考）"),
    ("fast", "快速档模型", "梗概 / 全书概览 / 术语抽取 / 回译（机械任务，免思考）"),
]

_LABEL_WIDTH = 150

# 状态提示配色（与 theme.py 色板一致，内联避免额外导入）
_CLR_SUCCESS = "#16A34A"
_CLR_ERROR = "#DC2626"
_CLR_INFO = "#6B7280"


class SettingsPage(QWidget):
    saved = Signal(dict)

    def __init__(self, settings: dict[str, str], parent: QWidget | None = None):
        super().__init__(parent)
        self._settings = settings
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        form = QFormLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # ── LLM 提供商 ──
        self.provider = FlatCombo()
        for p in LLM_PROVIDERS:
            self.provider.addItem(_PROVIDER_LABELS.get(p, p), p)
        self.provider.currentIndexChanged.connect(self._on_provider_changed)

        # ── API Key（根据 provider 动态启用/禁用 + 提示联动）──
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText("非「离线测试」时必填")
        self.api_key_hint = QLabel("必填")
        self.api_key_hint.setObjectName("path_hint")
        api_key_box = QWidget()
        av = QVBoxLayout(api_key_box)
        av.setContentsMargins(0, 0, 0, 0)
        av.setSpacing(4)
        av.addWidget(self.api_key)
        av.addWidget(self.api_key_hint)

        # ── API 地址（provider 为 fake 时同样禁用）──
        self.base_url = QLineEdit()
        self.base_url.setPlaceholderText("https://api.deepseek.com")

        self.max_tokens = QLineEdit()
        self.max_tokens.setPlaceholderText("4096")
        
        # ── 模型档位 ──
        self.model_fields: dict[str, QLineEdit] = {}
        self.state_dir = PathField(mode="dir")
        self.output_dir = PathField(mode="dir")

        # ── 保存按钮 ──
        self.save_btn = QPushButton("保存设置")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._save)

        # ── 状态提示：保存成功/失败的内联反馈，成功消息 3 秒后自动淡出 ──
        self.status_label = QLabel()
        self.status_label.setObjectName("path_hint")
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(lambda: self.status_label.setText(""))

        # ── 分组一：模型配置 ──
        form.addRow(self._section("模型配置"))
        form.addRow("LLM 提供商", self.provider)
        form.addRow("API Key", api_key_box)
        form.addRow("API 地址", self.base_url)
        form.addRow("Max Tokens", self.max_tokens)
        for tier, label, desc in TIER_MODELS:
            field = QLineEdit()
            field.setToolTip(desc)
            field.setPlaceholderText("必填")
            self.model_fields[tier] = field
            lbl = QLabel(label)
            lbl.setToolTip(desc)
            form.addRow(lbl, field)

        # ── 分组二：存储设置 ──
        form.addRow(self._section("存储设置"))
        form.addRow("缓存文件目录", self.state_dir)
        form.addRow("翻译电子书输出目录", self.output_dir)

        # 保存按钮 + 状态提示：右对齐到字段列
        btn_row = QWidget()
        bh = QHBoxLayout(btn_row)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.addStretch(1)
        bh.addWidget(self.status_label)
        bh.addSpacing(8)
        bh.addWidget(self.save_btn)
        form.addRow("", btn_row)
        root.addWidget(card)
        root.addStretch(1)

        # 固定标签列宽，长短标签右对齐到同一基线，视觉节奏稳定
        for i in range(form.rowCount()):
            item = form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            if item and item.widget():
                item.widget().setFixedWidth(_LABEL_WIDTH)

        self._fill()

    @staticmethod
    def _section(title: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 12, 0, 6)
        label = QLabel(title)
        label.setObjectName("section_title")
        v.addWidget(label)
        return w

    # ── 交互联动 ──────────────────────────────────────────

    def _on_provider_changed(self) -> None:
        """provider 切换时即时联动 API Key / API 地址字段：fake 禁用并改提示，其余启用并标为必填。"""
        provider = self.provider.currentData() or "deepseek"
        is_fake = provider == "fake"
        self.api_key.setEnabled(not is_fake)
        self.base_url.setEnabled(not is_fake)
        if is_fake:
            self.api_key.setText("")
            self.api_key_hint.setText("无需填写")
            self.api_key_hint.setStyleSheet(f"color: {_CLR_INFO};")
            self.base_url.setText("")
            self.base_url.setPlaceholderText("无需填写")
        else:
            self.api_key_hint.setText("必填")
            self.api_key_hint.setStyleSheet("")
            placeholders = {
                "deepseek": "https://api.deepseek.com",
                "openai": "https://api.openai.com/v1",
                "openrouter": "https://openrouter.ai/api/v1",
                "openai-compatible": "填写兼容的 API Base URL",
                "ollama": "http://localhost:11434/v1",
                "vllm": "http://localhost:8000/v1"
            }
            self.base_url.setPlaceholderText(placeholders.get(provider, "留空则使用默认地址"))

    # ── 数据填充 ──────────────────────────────────────────

    def _fill(self) -> None:
        provider = self._settings.get("provider", "deepseek")
        idx = self.provider.findData(provider)
        if idx >= 0:
            self.provider.setCurrentIndex(idx)
        elif self.provider.count():
            self.provider.setCurrentIndex(0)
        self.api_key.setText(self._settings.get("api_key", ""))
        self._on_provider_changed()  # 同步 API Key 字段初始状态

        config_path = self._settings.get("config_path", "config.yaml")
        models = read_config_models(config_path)
        for tier, _, _ in TIER_MODELS:
            field = self.model_fields[tier]
            field.setText(models.get(tier, self._settings.get(f"model_{tier}", "")))

        self.base_url.setText(
            read_config_base_url(config_path)
            or self._settings.get("base_url", "https://api.deepseek.com")
        )
        
        self.max_tokens.setText(self._settings.get("max_tokens", "4096"))

        self.state_dir.set_path(self._settings.get("state_dir", "state"))
        self.output_dir.set_path(self._settings.get("output_dir", "output"))

    # ── 状态提示 ──────────────────────────────────────────

    def _show_status(self, text: str, kind: str = "info") -> None:
        """在保存按钮左侧显示内联状态提示。success 3 秒后自动消失，error 持续显示。"""
        color = {
            "success": _CLR_SUCCESS,
            "error": _CLR_ERROR,
        }.get(kind, _CLR_INFO)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 9pt; font-weight: 600;")
        self.status_label.setText(text)
        if kind == "success":
            self._status_timer.start(3000)
        else:
            self._status_timer.stop()

    # ── 保存 ──────────────────────────────────────────────

    def _save(self) -> None:
        provider = self.provider.currentData() or "deepseek"
        key = self.api_key.text().strip()

        # 1) API Key：非 fake 时必填
        if provider != "fake" and not key:
            self._show_status("API Key 不能为空", "error")
            self.api_key.setFocus()
            return

        # 2) API 地址：非 fake 时必填
        base_url = self.base_url.text().strip()
        if provider != "fake" and not base_url:
            self._show_status("API 地址不能为空", "error")
            self.base_url.setFocus()
            return

        # 3) max_tokens 校验
        max_tokens_val = self.max_tokens.text().strip()
        if max_tokens_val and not max_tokens_val.isdigit():
            self._show_status("Max Tokens 必须是数字", "error")
            self.max_tokens.setFocus()
            return
            
        # 4) 模型档位：不能为空
        for tier, label, _ in TIER_MODELS:
            if not self.model_fields[tier].text().strip():
                self._show_status(f"{label}不能为空", "error")
                self.model_fields[tier].setFocus()
                return

        # 5) 目录：不能为空
        state_dir = self.state_dir.path()
        if not state_dir:
            self._show_status("缓存文件目录不能为空", "error")
            self.state_dir.edit.setFocus()
            return
        output_dir = self.output_dir.path()
        if not output_dir:
            self._show_status("翻译电子书输出目录不能为空", "error")
            self.output_dir.edit.setFocus()
            return

        models = {tier: self.model_fields[tier].text().strip() for tier, _, _ in TIER_MODELS}
        data = {
            "config_path": self._settings.get("config_path", "config.yaml"),
            "api_key": key,
            "provider": provider,
            "base_url": base_url,
            "max_tokens": max_tokens_val or "4096",
            # 命令前缀使用默认值，不设给用户
            "prefix": self._settings.get("prefix", ""),
            "state_dir": state_dir,
            "output_dir": output_dir,
            "model_strong": models["strong"],
            "model_cheap": models["cheap"],
            "model_fast": models["fast"],
        }
        try:
            update_yaml_config(data["config_path"], provider, base_url, models)
            save_settings(data)
        except Exception as e:
            self._show_status(f"保存失败：{e}", "error")
            return
        self._settings.update(data)
        self.saved.emit(data)
        self._show_status("✓ 设置已保存", "success")
