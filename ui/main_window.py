from __future__ import annotations

import json
import ctypes
import sys
import uuid
from datetime import datetime
from pathlib import Path
from threading import Event

from PySide6.QtCore import QThread, Signal, Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QComboBox, QVBoxLayout, QWidget, QToolButton,
    QFrame, QListWidget, QListWidgetItem, QCheckBox, QTextEdit,
)

from .chat_panel import ChatPanel
from .permission_dialog import PermissionDialog
from .theme import STYLE
from core.approvals import PermissionMode
from core.task_manager import Task
from tools.voice_input import listen_once


class Worker(QThread):
    done = Signal(str)
    stream = Signal(str, str)

    def __init__(self, loop, task, history):
        super().__init__()
        self.loop = loop
        self.task = task
        self.history = history

    def run(self):
        def on_stream(kind, text):
            self.stream.emit(kind, text)

        self.done.emit(self.loop.run(self.task, self.history, on_stream=on_stream))


class VoiceWorker(QThread):
    result = Signal(object)

    def __init__(self):
        super().__init__()
        self.stop_event = Event()

    def cancel(self):
        self.stop_event.set()

    def run(self):
        self.result.emit(listen_once(stop_event=self.stop_event))


class ModelRefreshWorker(QThread):
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def run(self):
        try:
            self.result.emit(self.manager.refresh())
        except Exception as exc:
            self.failed.emit(str(exc))


class ApiDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API 接口")
        self.setMinimumWidth(430)
        form = QFormLayout(self)
        title = QLabel("接口设置", objectName="dialogTitle")
        form.addRow(title)
        self.provider = QComboBox()
        self.provider.addItems(["ollama", "openai-compatible"])
        self.provider.setCurrentText(config.get("provider", "ollama"))
        configured_url = config.get("ollama_base_url", "") if config.get("provider") == "ollama" else config.get("base_url", "")
        self.base_url = QLineEdit(configured_url, objectName="settingsField")
        self.base_url.setPlaceholderText("例如 http://127.0.0.1:11434/v1")
        self.api_key = QLineEdit(config.get("api_key", ""), objectName="settingsField")
        self.api_key.setEchoMode(QLineEdit.Password)
        self.model = QLineEdit(config.get("model", ""), objectName="settingsField")
        self.model.setPlaceholderText("接口模型名称")
        relay=config.get("relay", {})
        self.relay_enabled=QCheckBox("启用本地中转站（仅本机）")
        self.relay_enabled.setChecked(bool(relay.get("enabled", False)))
        self.relay_port=QLineEdit(str(relay.get("port", 8765)), objectName="settingsField")
        self.relay_port.setPlaceholderText("8765")
        self.relay_token=QLineEdit(str(relay.get("auth_token", "")), objectName="settingsField")
        self.relay_token.setEchoMode(QLineEdit.Password)
        self.relay_token.setPlaceholderText("可选；留空表示本机免密")
        form.addRow("接口模式", self.provider)
        form.addRow("API 地址", self.base_url)
        form.addRow("API Key", self.api_key)
        form.addRow("模型", self.model)
        form.addRow("本地服务", self.relay_enabled)
        form.addRow("中转端口", self.relay_port)
        form.addRow("中转密码", self.relay_token)
        self.provider.currentTextChanged.connect(self.apply_provider_preset)
        self.test_button = QPushButton("测试接口")
        self.test_button.clicked.connect(self.test_connection)
        form.addRow("", self.test_button)
        self.test_status = QLabel("", objectName="muted")
        self.test_status.setWordWrap(True)
        form.addRow("状态", self.test_status)
        note = QLabel("通用 OpenAI-compatible 适配：OpenAI、DeepSeek、MiniMax、豆包/火山引擎、通义千问及其他兼容服务都可使用。填写服务商的兼容 API 根地址、API Key 和模型名即可，不需要为每家服务单独写代码。API Key 只保存在本机 config.json。", objectName="muted")
        note.setWordWrap(True)
        form.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def apply_provider_preset(self, provider):
        if provider == "deepseek":
            current_url=self.base_url.text().strip()
            if not current_url or "api.openai.com" in current_url or "127.0.0.1:11434" in current_url:
                self.base_url.setText("https://api.deepseek.com")
            if not self.model.text().strip() or self.model.text().strip() in {"llama3.1:8b", "deepseek-chat", "deepseek-reasoner"}:
                self.model.setText("deepseek-flash")
        elif provider == "openai-compatible" and not self.base_url.text().strip():
            self.base_url.setText("https://api.openai.com/v1")

    def test_connection(self):
        self.test_button.setEnabled(False)
        self.test_status.setText("正在连接…")
        from models.openai_compatible import OpenAICompatibleProvider
        try:
            if self.provider.currentText() == "ollama":
                from models.ollama import OllamaProvider
                result={"success":OllamaProvider(self.base_url.text().strip() or "http://127.0.0.1:11434").is_online()}
                if not result["success"]: result["error"]="Ollama 未连接"
            else:
                result=OpenAICompatibleProvider(self.base_url.text().strip(),self.api_key.text(),8).check_connection()
            self.test_status.setText(("✓ " if result.get("success") else "✗ ") + (result.get("message") or result.get("error", "测试失败")))
        except Exception as exc:
            self.test_status.setText(f"✗ {exc}")
        finally:
            self.test_button.setEnabled(True)


class ReasoningDialog(QDialog):
    def __init__(self, options, current="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("思考强度")
        self.setMinimumWidth(330)
        layout=QFormLayout(self)
        layout.addRow(QLabel("选择当前模型支持的思考强度", objectName="dialogTitle"))
        self.picker=QComboBox(objectName="settingsField")
        for label,value in options:
            self.picker.addItem(label, value)
        index=self.picker.findData(current)
        self.picker.setCurrentIndex(index if index >= 0 else 0)
        layout.addRow("强度", self.picker)
        note=QLabel("只显示当前模型和接口支持的选项；普通模型不会显示此设置。", objectName="muted")
        note.setWordWrap(True)
        layout.addRow(note)
        buttons=QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class MainWindow(QMainWindow):
    approval_signal = Signal(object)
    task_signal = Signal(object)
    tool_signal = Signal(str, object)
    progress_signal = Signal(object)

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.history = []
        self.session_id = uuid.uuid4().hex
        self._streamed_reply = False
        self._narration_streaming = False
        self.history_path = Path(__file__).resolve().parents[1] / "data" / "history" / "conversations.json"
        self.assets_dir = Path(__file__).resolve().parents[1] / "assets" / "icons"
        self.saved_sessions = []
        self.preview_files = {}
        self._pending_approval = None
        self.model_refresh_worker = None
        self.setWindowTitle("本地 Agent")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.Window)
        self.setWindowOpacity(0.86)
        self.resize(860, 620)
        self.setMinimumSize(420, 320)
        self.setStyleSheet(STYLE)
        self.build()
        self.wire()

    def build(self):
        root = QWidget(objectName="glassShell")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.drawer = QFrame(objectName="settingsDrawer")
        self.drawer.setFixedWidth(285)
        self.drawer.hide()
        drawer_layout = QVBoxLayout(self.drawer)
        drawer_layout.setContentsMargins(20, 24, 18, 20)
        drawer_layout.setSpacing(12)
        drawer_header = QHBoxLayout()
        drawer_icon = QToolButton(objectName="appIcon")
        drawer_icon.setIcon(self.asset_icon("app.svg"))
        drawer_icon.setIconSize(QSize(25, 25))
        drawer_icon.setEnabled(False)
        drawer_header.addWidget(drawer_icon)
        drawer_title = QLabel("设置与资料", objectName="drawerTitle")
        drawer_header.addWidget(drawer_title)
        drawer_header.addStretch(1)
        drawer_close = QToolButton(objectName="drawerClose")
        drawer_close.setText("×")
        drawer_close.setToolTip("关闭侧栏")
        drawer_close.clicked.connect(self.toggle_drawer)
        drawer_header.addWidget(drawer_close)
        drawer_layout.addLayout(drawer_header)
        self.drawer_meta = QLabel("本地会话与模型信息", objectName="drawerMeta")
        self.drawer_meta.setWordWrap(True)
        drawer_layout.addWidget(self.drawer_meta)
        permission_title=QLabel("操作确认", objectName="muted")
        drawer_layout.addWidget(permission_title)
        self.permission_picker=QComboBox(objectName="settingsField")
        self.permission_picker.addItem("完全不受控制", PermissionMode.UNRESTRICTED.value)
        self.permission_picker.addItem("部分提醒（高风险操作提醒）", PermissionMode.ASK_RISKY.value)
        self.permission_picker.addItem("全部提醒", PermissionMode.ASK_ALL.value)
        drawer_layout.addWidget(QLabel("语言", objectName="muted"))
        self.language_picker = QComboBox(objectName="settingsField")
        self.language_picker.addItems(["中文", "English"])
        self.language_picker.setCurrentText("English" if self.app.config.get("language") == "en" else "中文")
        drawer_layout.addWidget(self.language_picker)
        current_mode=self.app.permissions.mode.value
        current_index=self.permission_picker.findData(current_mode)
        self.permission_picker.setCurrentIndex(current_index if current_index >= 0 else 1)
        drawer_layout.addWidget(self.permission_picker)
        drawer_layout.addWidget(QLabel("语言", objectName="languageLabel"))
        self.language_picker = QComboBox(objectName="settingsField")
        self.language_picker.addItems(["中文", "English"])
        self.language_picker.setCurrentText("English" if self.app.config.get("language") == "en" else "中文")
        drawer_layout.addWidget(self.language_picker)
        self.history_list = QListWidget(objectName="historyList")
        self.history_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.itemClicked.connect(self.load_session_item)
        drawer_layout.addWidget(self.history_list, 1)
        drawer_actions = QHBoxLayout()
        new_button = QPushButton("新建对话", objectName="drawerAction")
        new_button.clicked.connect(self.new_session)
        backup_button = QPushButton("备份", objectName="drawerAction")
        backup_button.clicked.connect(self.backup_history)
        drawer_actions.addWidget(new_button)
        drawer_actions.addWidget(backup_button)
        drawer_layout.addLayout(drawer_actions)
        self.drawer_status = QLabel("", objectName="drawerStatus")
        drawer_layout.addWidget(self.drawer_status)
        shell.addWidget(self.drawer)

        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(34, 24, 34, 26)
        outer.setSpacing(12)
        shell.addWidget(content, 1)

        self.header_bar = QWidget(objectName="contentHeader")
        header = QHBoxLayout(self.header_bar)
        header.setContentsMargins(14, 10, 12, 4)
        header.setSpacing(8)
        logo = QToolButton(objectName="appIcon")
        logo.setIcon(self.asset_icon("app.svg"))
        logo.setIconSize(QSize(28, 28))
        logo.setEnabled(False)
        header.addWidget(logo)
        title = QLabel("LOCAL AGENT", objectName="appTitle")
        header.addWidget(title)
        self.status_top = QLabel("就绪", objectName="statusTop")
        header.addWidget(self.status_top)
        header.addStretch(1)
        self.model_picker = QComboBox(objectName="modelPicker")
        self.model_picker.setToolTip("选择本地模型或已配置的 API 模型")
        header.addWidget(self.model_picker)
        self.reasoning_button = QPushButton("思考", objectName="reasoningButton")
        self.reasoning_button.setToolTip("选择当前模型支持的思考强度")
        self.reasoning_button.hide()
        header.addWidget(self.reasoning_button)
        self.api_button = QPushButton("API")
        self.api_button.setObjectName("compactButton")
        self.api_button.setToolTip("配置 OpenAI-compatible API")
        header.addWidget(self.api_button)
        self.settings_button = QToolButton(objectName="settingsButton")
        self.settings_button.setIcon(self.asset_icon("settings.svg"))
        self.settings_button.setIconSize(QSize(16, 16))
        self.settings_button.setToolTip("设置、历史与备份")
        header.addWidget(self.settings_button)
        self.preview_button = QToolButton(objectName="previewButton")
        self.preview_button.setText("›")
        self.preview_button.setToolTip("查看 Agent 最近编辑的文件")
        header.addWidget(self.preview_button)
        outer.addWidget(self.header_bar)

        self.chat = ChatPanel()
        outer.addWidget(self.chat, 1)

        self.preview_drawer = QFrame(objectName="previewDrawer")
        self.preview_drawer.setFixedWidth(370)
        self.preview_drawer.hide()
        preview_layout = QVBoxLayout(self.preview_drawer)
        preview_layout.setContentsMargins(14, 20, 14, 18)
        preview_layout.setSpacing(9)
        preview_header = QHBoxLayout()
        preview_title = QLabel("工作区预览", objectName="previewTitle")
        preview_header.addWidget(preview_title)
        preview_header.addStretch(1)
        preview_close = QToolButton(objectName="drawerClose")
        preview_close.setText("×")
        preview_close.setToolTip("关闭预览")
        preview_close.clicked.connect(self.toggle_preview)
        preview_header.addWidget(preview_close)
        preview_layout.addLayout(preview_header)
        self.preview_status = QLabel("Agent 编辑的文件会显示在这里", objectName="muted")
        self.preview_status.setWordWrap(True)
        preview_layout.addWidget(self.preview_status)
        self.preview_list = QListWidget(objectName="previewList")
        self.preview_list.setMaximumHeight(125)
        self.preview_list.itemClicked.connect(self.show_preview_item)
        preview_layout.addWidget(self.preview_list)
        self.preview_path = QLabel("", objectName="previewPath")
        self.preview_path.setWordWrap(True)
        preview_layout.addWidget(self.preview_path)
        self.preview_content = QTextEdit(readOnly=True, objectName="previewContent")
        self.preview_content.setLineWrapMode(QTextEdit.NoWrap)
        self.preview_content.setPlaceholderText("选择一个文件查看实际内容")
        preview_layout.addWidget(self.preview_content, 1)
        shell.addWidget(self.preview_drawer)

    def wire(self):
        self.app.permissions.callback = self.ask_permission
        self.approval_signal.connect(self.show_approval)
        self.task_signal.connect(self.update_task)
        self.tool_signal.connect(self.handle_tool)
        self.progress_signal.connect(self.handle_progress)
        self.chat.submitted.connect(self.start_task)
        self.chat.stop_requested.connect(self.stop_task)
        self.chat.voice_requested.connect(self.start_voice)
        self.model_picker.currentTextChanged.connect(self.choose_model)
        self.reasoning_button.clicked.connect(self.open_reasoning_dialog)
        self.api_button.clicked.connect(self.open_api_dialog)
        self.settings_button.clicked.connect(self.toggle_drawer)
        self.preview_button.clicked.connect(self.toggle_preview)
        self.permission_picker.currentIndexChanged.connect(self.change_permission_mode)
        self.language_picker.currentTextChanged.connect(self.change_language)
        self.app.events.subscribe("task", lambda task: self.task_signal.emit(task))
        self.app.events.subscribe("tool", lambda name, result: self.tool_signal.emit(name, result))
        self.app.events.subscribe("progress", lambda item: self.progress_signal.emit(item))
        self.populate_models()
        self.load_history()
        self.update_ai_label()
        self.change_language(self.language_picker.currentText())
        # Let Qt paint the window first; slow Ollama/API discovery happens behind it.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(80, self.refresh_models_async)

    def refresh_models_async(self):
        if self.model_refresh_worker and self.model_refresh_worker.isRunning():
            return
        self.model_refresh_worker = ModelRefreshWorker(self.app.model_manager)
        self.model_refresh_worker.result.connect(self.finish_model_refresh)
        self.model_refresh_worker.failed.connect(lambda _: self.update_ai_label())
        self.model_refresh_worker.start()

    def finish_model_refresh(self, models):
        self.populate_models()
        self.update_ai_label()

    def asset_icon(self, name):
        return QIcon(str(self.assets_dir / name))

    def toggle_drawer(self):
        self.drawer.setVisible(not self.drawer.isVisible())
        if self.drawer.isVisible():
            self.refresh_history_list()

    def change_language(self, language):
        english = language == "English"
        self.app.config["language"] = "en" if english else "zh"
        self.app.save_config()
        translations = {
            "设置与资料": "Settings & Profile", "本地会话与模型信息": "Local sessions and model information",
            "操作确认": "Permission mode", "完全不受控制": "Unrestricted", "部分提醒（高风险操作提醒）": "Ask for risky actions",
            "全部提醒": "Ask for every action", "语言": "Language", "新建对话": "New chat", "备份": "Backup",
            "关闭侧栏": "Close sidebar", "就绪": "Ready", "思考": "Reasoning", "API": "API",
            "设置、历史与备份": "Settings, history and backup", "查看 Agent 最近编辑的文件": "View files recently edited by Agent",
            "发送": "Send", "停止 Agent": "Stop Agent", "输入消息，或让 Agent 操作本机…": "Type a message or ask Agent to use this computer…",
            "本地模型": "Local model", "本机语音输入": "Voice input", "停止聆听": "Stop listening",
            "选择图片发送给当前模型": "Choose an image for the current model", "当前任务：等待": "Current task: idle",
            "工具": "Tool", "完成": "Completed", "失败": "Failed", "未知错误": "Unknown error",
        }
        def translate(value):
            if not value:
                return value
            if english:
                return translations.get(value, value)
            reverse = {v: k for k, v in translations.items()}
            return reverse.get(value, value)
        for widget_type in (QLabel, QPushButton, QToolButton, QCheckBox):
            for widget in self.findChildren(widget_type):
                widget.setText(translate(widget.text()))
                if widget.toolTip():
                    widget.setToolTip(translate(widget.toolTip()))
        for combo in self.findChildren(QComboBox):
            for index in range(combo.count()):
                combo.setItemText(index, translate(combo.itemText(index)))
        self.input.setPlaceholderText(translate(self.input.placeholderText()))
        self.language_picker.blockSignals(True)
        self.language_picker.setCurrentText("English" if english else "中文")
        self.language_picker.blockSignals(False)

    def toggle_preview(self):
        self.preview_drawer.setVisible(not self.preview_drawer.isVisible())
        self.preview_button.setText("‹" if self.preview_drawer.isVisible() else "›")
        if self.preview_drawer.isVisible() and self.preview_files and not self.preview_list.currentItem():
            self.preview_list.setCurrentRow(0)
            self.show_preview_item(self.preview_list.currentItem())

    def update_preview_from_tool(self, name, result):
        if not isinstance(result, dict) or not result.get("success"):
            return
        path = result.get("path") or result.get("destination")
        if not path:
            return
        path = str(path)
        if name in {"write_file", "append_file", "read_file", "file_info", "create_folder", "copy_file", "move_file"}:
            self.preview_files[path] = {"path": path, "kind": "folder" if name == "create_folder" else "file"}
            self.preview_list.clear()
            for item_path, item in self.preview_files.items():
                label = ("📁 " if item["kind"] == "folder" else "📄 ") + item_path
                row = QListWidgetItem(label)
                row.setData(Qt.UserRole, item_path)
                self.preview_list.addItem(row)
            if not self.preview_drawer.isVisible():
                self.toggle_preview()
            self.preview_list.setCurrentRow(self.preview_list.count() - 1)
            self.show_preview_item(self.preview_list.currentItem())

    def show_preview_item(self, item):
        if not item:
            return
        path = str(item.data(Qt.UserRole) or "")
        self.preview_path.setText(path)
        target = Path(path)
        try:
            if target.is_dir():
                names = [f"{p.name}{'/' if p.is_dir() else ''}" for p in target.iterdir()]
                self.preview_content.setPlainText("文件夹内容：\n" + "\n".join(names))
                self.preview_status.setText("Agent 刚刚创建或修改了这个文件夹")
            elif target.is_file():
                content = target.read_text(encoding="utf-8", errors="replace")
                self.preview_content.setPlainText(content)
                self.preview_status.setText(f"已读取实际文件内容 · {target.stat().st_size} 字节")
            else:
                self.preview_content.setPlainText("文件当前不存在或无法读取")
                self.preview_status.setText("无法读取这个路径")
        except Exception as exc:
            self.preview_content.setPlainText(f"读取失败：{exc}")
            self.preview_status.setText("读取文件时发生错误")

    def change_permission_mode(self, index):
        value=self.permission_picker.itemData(index)
        if not value:
            return
        self.app.set_permission_mode(PermissionMode(value))
        self.drawer_status.setText(f"已设置：{self.permission_picker.currentText()}")

    def refresh_history_list(self):
        self.history_list.clear()
        for session in reversed(self.saved_sessions):
            item = QListWidgetItem(session.get("title") or "新会话")
            item.setData(Qt.UserRole, session.get("id"))
            item.setToolTip(session.get("updated", ""))
            self.history_list.addItem(item)
        self.drawer_meta.setText(
            f"{len(self.saved_sessions)} 个本地会话\n"
            f"历史：{self.history_path.parent}\n"
            f"工作区：{self.app.config.get('workspace', '')}"
        )

    def load_session_item(self, item):
        session_id = item.data(Qt.UserRole)
        session = next((s for s in self.saved_sessions if s.get("id") == session_id), None)
        if not session:
            return
        self.restore_session(session)
        self.status_top.setText("已载入历史会话")
        self.drawer.hide()

    def restore_session(self, session):
        self.session_id = session.get("id") or uuid.uuid4().hex
        self.history = list(session.get("messages") or [])
        self.chat.chat.clear()
        for message in self.history:
            role = "你" if message.get("role") == "user" else "Agent"
            self.chat.append(role, message.get("content", ""))
        self.status_top.setText("已恢复上次会话")

    def backup_history(self):
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        backup_dir = self.history_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        target = backup_dir / f"conversations-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        target.write_text(self.history_path.read_text(encoding="utf-8") if self.history_path.exists() else "[]", encoding="utf-8")
        self.drawer_status.setText(f"已备份：{target.name}")

    def populate_models(self):
        self.model_picker.blockSignals(True)
        self.model_picker.clear()
        options=self.app.model_manager.model_options()
        if not options:
            options=[{"label":"未检测到本地或 API 模型","source":"","model":""}]
        for option in options:
            self.model_picker.addItem(option["label"],option)
        active=self.app.model_manager.active_model()
        active_source="ollama" if self.app.model_manager.provider_name=="ollama" else "api"
        for index,option in enumerate(options):
            if option.get("model")==active and option.get("source")==active_source:
                self.model_picker.setCurrentIndex(index)
                break
        self.model_picker.blockSignals(False)

    def choose_model(self, _label):
        option=self.model_picker.currentData() or {}
        if option.get("model"):
            self.app.set_model(option["model"],option.get("source"))
            self.update_ai_label()

    def update_reasoning_button(self):
        options=self.app.model_manager.reasoning_options()
        self.reasoning_button.setVisible(bool(options))
        if options:
            current=self.app.config.get("reasoning_effort")
            label=next((label for label,value in options if value == current), "思考")
            self.reasoning_button.setText(f"思考：{label}" if current else "思考")

    def open_reasoning_dialog(self):
        options=self.app.model_manager.reasoning_options()
        if not options:
            self.reasoning_button.hide()
            return
        dialog=ReasoningDialog(options,self.app.config.get("reasoning_effort"),self)
        if dialog.exec() == QDialog.Accepted:
            self.app.config["reasoning_effort"]=dialog.picker.currentData()
            self.app.save_config()
            self.update_reasoning_button()

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                dwm = ctypes.windll.dwmapi
                dark = ctypes.c_int(1)
                for attribute in (20, 19):
                    dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(dark), ctypes.sizeof(dark))
                black = ctypes.c_int(0)
                white = ctypes.c_int(0xFFFFFF)
                dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(black), ctypes.sizeof(black))
                dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(white), ctypes.sizeof(white))
            except Exception:
                pass

    def update_ai_label(self):
        model = self.app.model_manager.active_model() or "未选择模型"
        provider = self.app.model_manager.provider_name
        state = "已连接" if self.app.model_manager.online() else "待连接"
        self.chat.ai_label.setText(f"{provider} · {model} · {state}")
        self.update_reasoning_button()

    def open_api_dialog(self):
        dialog = ApiDialog(self.app.config, self)
        if dialog.exec() != QDialog.Accepted:
            return
        self.app.config["provider"] = dialog.provider.currentText()
        if self.app.config["provider"] == "ollama":
            self.app.config["ollama_base_url"] = dialog.base_url.text().strip() or "http://127.0.0.1:11434"
        else:
            self.app.config["base_url"] = dialog.base_url.text().strip()
        self.app.config["api_key"] = dialog.api_key.text()
        self.app.config["model"] = dialog.model.text().strip()
        try:
            relay_port=int(dialog.relay_port.text().strip() or "8765")
            if not 1 <= relay_port <= 65535:
                raise ValueError
        except ValueError:
            self.status_top.setText("中转端口无效")
            return
        self.app.config["relay"]={"enabled":dialog.relay_enabled.isChecked(),"host":"127.0.0.1","port":relay_port,"auth_token":dialog.relay_token.text()}
        self.app.model_manager.provider_name = self.app.config["provider"]
        self.app.save_config()
        relay_result=self.app.apply_relay_config()
        self.populate_models()
        self.update_ai_label()
        self.refresh_models_async()
        if dialog.relay_enabled.isChecked():
            self.status_top.setText("中转站已启动" if relay_result.get("success") else f"中转站失败：{relay_result.get('error','未知错误')}")

    def handle_tool(self, name, result):
        self.update_preview_from_tool(name, result)
        if result.get("success") is False:
            self.status_top.setText(f"工具失败：{name}")
        else:
            self.status_top.setText(f"已完成：{name}")

    def handle_progress(self, item):
        kind = item.get("kind") if isinstance(item, dict) else "info"
        if kind == "assistant_note":
            self.chat.append("Agent", item.get("text", ""))
            self.chat.set_progress("正在思考")
        elif kind == "tool_start":
            name = item.get("name", "工具")
            args = json.dumps(item.get("arguments", {}), ensure_ascii=False, default=str)
            self.status_top.setText(f"正在使用 {name}…")
            self.chat.append("Agent", f"我先调用 {name} 来处理这一部分。")
            self.chat.set_progress(f"正在调用 {name}")
            self.chat.append("执行", f"{name}\n参数：{args}")
        elif kind == "tool_result":
            name = item.get("name", "工具")
            mark = "完成" if item.get("success") else "失败"
            self.chat.append("Agent", f"已使用 {name}，{mark}。")
            self.chat.append("结果", f"{name} · {mark}\n{item.get('text', '')}")
            self.chat.set_progress("继续处理")
        elif kind == "thinking":
            self.status_top.setText("思考中…")
            self.chat.set_progress("正在思考")
        elif kind == "verification_start":
            self.status_top.setText("最终检查中…")
            self.chat.set_progress("正在进行最终验收检查")
        elif kind == "empty_response":
            self.status_top.setText("模型未返回内容，正在重试…")
            self.chat.set_progress("模型没有返回内容，正在重新请求")
        elif kind == "loop_blocked":
            self.status_top.setText("已阻止重复调用")
            self.chat.set_progress("重复工具调用已停止，正在整理结论")
        elif kind == "error":
            self.status_top.setText("请求失败")
            self.chat.set_progress("处理失败", active=False)

    def handle_stream(self, kind, text):
        if kind == "narration":
            if not self._narration_streaming:
                self.chat.begin_stream()
                self._narration_streaming = True
            self.chat.append_stream(text)
            self.chat.set_progress("正在组织下一步")
        elif kind == "narration_done":
            self.chat.finish_stream()
            self._narration_streaming = False
            self.chat.set_progress("正在准备下一步")
        elif kind == "content":
            if not self._streamed_reply:
                self.chat.begin_stream()
                self._streamed_reply = True
            self.chat.append_stream(text)
            self.status_top.setText("输出中…")
            self.chat.set_progress("正在整理回答", active=False)
        elif kind == "reasoning":
            self.status_top.setText("深度思考中…")

    def ask_permission(self, request):
        holder = {"request": request, "event": Event(), "allowed": False}
        self._pending_approval = holder
        self.approval_signal.emit(holder)
        holder["event"].wait()
        if self._pending_approval is holder:
            self._pending_approval = None
        return holder["allowed"]

    def show_approval(self, holder):
        holder["allowed"] = PermissionDialog(holder["request"], self).exec() == PermissionDialog.Accepted
        holder["event"].set()

    def start_task(self, text, image_path=""):
        if hasattr(self, "worker") and self.worker.isRunning():
            return
        self.app.computer.resume()
        # 被终止的那一轮只保留在界面历史中，不再作为下一轮模型上下文。
        # 否则模型可能把新消息误判成“继续上一条未完成任务”。
        context_history = self._model_context_history()
        message={"role": "user", "content": text}
        if image_path:
            message["image_path"]=image_path
        self.history.append(message)
        self._streamed_reply = False
        self._narration_streaming = False
        self.task = Task(text, image_path=image_path)
        self.worker = Worker(self.app.loop, self.task, context_history)
        self.worker.stream.connect(self.handle_stream)
        self.worker.done.connect(self.finish_task)
        self.chat.set_running(True)
        self.chat.set_progress("正在思考")
        self.status_top.setText("思考中…")
        self.worker.start()

    def _model_context_history(self):
        """Return prior completed turns, excluding any cancelled turn pair."""
        result = []
        index = 0
        while index < len(self.history):
            item = self.history[index]
            is_user = isinstance(item, dict) and item.get("role") == "user"
            if is_user and index + 1 < len(self.history):
                next_item = self.history[index + 1]
                next_content = str(next_item.get("content", "")) if isinstance(next_item, dict) else ""
                if next_item.get("role") == "assistant" and next_content.startswith("⏹ 当前任务已终止"):
                    index += 2
                    continue
            result.append(item)
            index += 1
        return result

    def finish_task(self, reply):
        self.chat.finish_stream()
        stopped = getattr(getattr(self, "task", None), "stopped", False)
        if not self._streamed_reply and reply and not (stopped and getattr(self.task, "stop_recorded", False)):
            self.chat.append("Agent", reply)
        if not (stopped and getattr(self.task, "stop_recorded", False)):
            self.history.append({"role": "assistant", "content": reply})
        self.chat.set_running(False)
        self.chat.finish_progress()
        self.status_top.setText("已停止" if stopped else "就绪")
        self.save_history()
        if stopped:
            self.app.computer.resume()

    def start_voice(self):
        if hasattr(self, "voice_worker") and self.voice_worker.isRunning():
            self.cancel_voice()
            return
        self.status_top.setText("聆听中…")
        self.chat.set_voice_listening(True)
        self.voice_worker = VoiceWorker()
        self.voice_worker.result.connect(self.finish_voice)
        self.voice_worker.start()

    def cancel_voice(self):
        worker = getattr(self, "voice_worker", None)
        if worker and worker.isRunning():
            worker.cancel()
        self.chat.set_voice_listening(False)
        self.status_top.setText("已取消聆听")

    def finish_voice(self, result):
        self.chat.set_voice_listening(False)
        if result.get("cancelled"):
            self.status_top.setText("已取消聆听")
            return
        if result.get("success") and result.get("text"):
            self.chat.input.setText(result["text"])
            self.chat.input.setFocus()
            self.status_top.setText("已识别，请确认发送")
        else:
            self.status_top.setText("语音不可用")
            self.chat.append("系统", result.get("error", "未检测到 Windows 语音识别器"))

    def stop_task(self):
        if hasattr(self, "task"):
            self.task.stop()
            if not getattr(self.task, "stop_recorded", False):
                self.task.stop_recorded=True
                self.history.append({"role":"assistant","content":"⏹ 当前任务已终止。后续消息可以继续这个会话。"})
                self.chat.append("Agent","⏹ 当前任务已终止。后续消息可以继续这个会话。")
                self.save_history()
        pending=self._pending_approval
        if pending:
            pending["allowed"]=False
            pending["event"].set()
        self.app.computer.stop()
        self.app.cancel_tools()
        self.app.model_manager.cancel_active()
        try:
            self.app.browser.close()
        except Exception:
            pass
        self.chat.set_running(False)
        self.status_top.setText("已停止")

    def new_session(self):
        self.history = []
        self.session_id = uuid.uuid4().hex
        self.chat.chat.clear()
        self.chat.set_running(False)
        self.status_top.setText("就绪")

    def load_history(self):
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.saved_sessions = json.loads(self.history_path.read_text(encoding="utf-8"))
        except Exception:
            self.saved_sessions = []
        if hasattr(self, "history_list"):
            self.refresh_history_list()
            if self.saved_sessions:
                self.restore_session(self.saved_sessions[-1])

    def save_history(self):
        title = next((m["content"][:48] for m in self.history if m.get("role") == "user"), "新会话")
        record = {"id": self.session_id, "title": title, "updated": datetime.now().astimezone().isoformat(), "messages": self.history[-40:]}
        self.saved_sessions = [s for s in self.saved_sessions if s.get("id") != self.session_id] + [record]
        self.saved_sessions = self.saved_sessions[-50:]
        self.history_path.write_text(json.dumps(self.saved_sessions, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_task(self, task):
        if task.status.value in ("运行工具", "运行中"):
            self.status_top.setText("执行中…")

    def closeEvent(self, event):
        worker=getattr(self,"worker",None)
        if worker and worker.isRunning():
            self.task.stop()
            if not getattr(self.task, "stop_recorded", False):
                self.history.append({"role":"assistant","content":"⏹ 当前任务已终止。下次打开后可以继续这个会话。"})
            self.app.cancel_tools()
            self.app.model_manager.cancel_active()
        if self.history:
            self.save_history()
        self.app.stop_relay()
        super().closeEvent(event)

