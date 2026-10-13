from __future__ import annotations

from html import escape

from PySide6.QtCore import Signal, QTimer, Qt, QSize
from PySide6.QtGui import QIcon, QTextCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QToolButton, QHBoxLayout, QLabel, QFrame, QFileDialog
from pathlib import Path


class ChatPanel(QWidget):
    submitted = Signal(str, str)
    stop_requested = Signal()
    voice_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        self.activity = QTextEdit(readOnly=True)
        self.activity.setObjectName("activity")
        self.activity.hide()
        self.chat = QTextEdit(readOnly=True)
        self.chat.setObjectName("conversation")
        self.chat.setAcceptRichText(True)
        self.chat.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input = QLineEdit()
        self.input.setObjectName("prompt")
        self.input.setPlaceholderText("输入消息，或让 Agent 操作本机…")
        self.composer = QFrame(objectName="composer")
        composer_layout = QHBoxLayout(self.composer)
        composer_layout.setContentsMargins(8, 7, 8, 7)
        composer_layout.setSpacing(8)
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "icons" / "microphone.svg"
        stop_icon_path = Path(__file__).resolve().parents[1] / "assets" / "icons" / "stop.svg"
        self._voice_icon = QIcon(str(icon_path))
        self._stop_icon = QIcon(str(stop_icon_path))
        self.voice_button = QToolButton()
        self.voice_button.setObjectName("voiceButton")
        self.voice_button.setIcon(self._voice_icon)
        self.voice_button.setIconSize(QSize(16, 16))
        self.voice_button.setAutoRaise(True)
        self.voice_button.setToolTip("本机语音输入")
        self.voice_button.clicked.connect(self.voice_requested.emit)
        self.send_button = QToolButton()
        self.send_button.setObjectName("sendButton")
        self.send_button.setText("发送")
        self.send_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.send_button.clicked.connect(self.submit)
        self.input.returnPressed.connect(self.submit)
        self.image_button = QToolButton()
        self.image_button.setObjectName("imageButton")
        self.image_button.setText("＋")
        self.image_button.setToolTip("选择图片发送给当前模型")
        self.image_button.clicked.connect(self.choose_image)
        self.pending_image = ""
        self.ai_label = QLabel("本地模型", objectName="aiLabel")
        self.progress_label = QLabel("", objectName="progressLabel")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.hide()
        self.status_label = QLabel("", objectName="streamStatus")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        composer_layout.addWidget(self.voice_button)
        composer_layout.addWidget(self.image_button)
        composer_layout.addWidget(self.input, 1)
        composer_layout.addWidget(self.status_label, 0)
        composer_layout.addWidget(self.send_button, 0)
        layout.addWidget(self.chat, 1)
        layout.addWidget(self.ai_label, 0, Qt.AlignHCenter)
        layout.addWidget(self.progress_label, 0, Qt.AlignHCenter)
        layout.addWidget(self.composer)
        self._stream_cursor = None
        self._dots = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def set_voice_listening(self, listening):
        self.voice_button.setProperty("listening", bool(listening))
        self.voice_button.setIcon(self._stop_icon if listening else self._voice_icon)
        self.voice_button.setToolTip("停止聆听" if listening else "本机语音输入")
        self.voice_button.setEnabled(True)
        self.voice_button.style().unpolish(self.voice_button)
        self.voice_button.style().polish(self.voice_button)

    def set_progress(self, text="", active=True):
        if not text or not active:
            self.progress_label.hide()
            self.progress_label.clear()
            return
        self.progress_label.setProperty("active", True)
        self.progress_label.setText(text)
        self.progress_label.show()
        self._dots = 0
        if not self._timer.isActive():
            self._timer.start(450)

    def finish_progress(self):
        self.progress_label.setProperty("active", False)
        self.progress_label.hide()
        self.progress_label.clear()

    def submit(self):
        if self.send_button.property("running"):
            self.stop_requested.emit()
            return
        text = self.input.text().strip()
        if text or self.pending_image:
            self.input.clear()
            display=text or "请分析这张图片。"
            if self.pending_image:
                display += f"  [图片：{Path(self.pending_image).name}]"
            self.append("你", display)
            image=self.pending_image
            self.pending_image=""
            self.image_button.setText("＋")
            self.submitted.emit(text or "请分析这张图片。", image)

    def choose_image(self):
        path,_=QFileDialog.getOpenFileName(self,"选择图片","","图片文件 (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        self.pending_image=path
        self.image_button.setText("📎")
        self.image_button.setToolTip(f"已选择图片：{path}")
        self.input.setFocus()

    def append(self, role, text):
        self.chat.append(f'<p class="message"><span class="role">{escape(str(role))}</span> {escape(str(text)).replace(chr(10), "<br>")}</p>')
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def begin_stream(self):
        self.chat.append('<p class="message assistant"><span class="role">Agent</span> <span class="streaming"></span></p>')
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._stream_cursor = cursor

    def append_stream(self, text):
        if not text:
            return
        if self._stream_cursor is None:
            self.begin_stream()
        self._stream_cursor.insertText(str(text))
        self.chat.setTextCursor(self._stream_cursor)
        self.chat.ensureCursorVisible()

    def finish_stream(self):
        self._stream_cursor = None

    def append_activity(self, text):
        self.activity.append(text)

    def set_running(self, running):
        self.send_button.setProperty("running", running)
        self.send_button.setText("停止 Agent" if running else "发送")
        self.status_label.setText("正在运行" if running else "")
        self.voice_button.setEnabled(not running)
        self.image_button.setEnabled(not running)
        self.send_button.style().unpolish(self.send_button)
        self.send_button.style().polish(self.send_button)
        if running:
            self._timer.start(450)
        else:
            self._timer.stop()
            self.finish_stream()
            self.finish_progress()

    def _animate(self):
        self._dots = (self._dots + 1) % 4
        dots = "." * self._dots
        if self.send_button.property("running"):
            self.send_button.setText(f"停止 Agent{dots}")
        if self.progress_label.isVisible():
            base = self.progress_label.text().rstrip(".")
            self.progress_label.setText(f"{base}{dots}")
