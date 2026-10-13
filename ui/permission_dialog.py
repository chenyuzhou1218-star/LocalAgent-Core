from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QPushButton,QHBoxLayout

class PermissionDialog(QDialog):
    def __init__(self,request,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agent 权限请求")
        self.setModal(True)
        self.setMinimumWidth(430)
        self.setMaximumWidth(520)
        box=QVBoxLayout(self)
        box.setContentsMargins(22, 20, 22, 20)
        box.setSpacing(12)
        title=QLabel("是否允许 Agent 执行此操作？")
        title.setObjectName("dialogTitle")
        box.addWidget(title)

        def short(value,limit=150):
            text=str(value or "").replace("\r", "").strip()
            return text if len(text) <= limit else text[:limit].rstrip()+"…"

        # 只展示摘要，避免命令参数或长文本把确认框撑得很长。
        summary=QLabel(
            f"操作：{short(request.action,60)}\n"
            f"目标：{short(request.target,170)}\n"
            f"风险：{short(request.risk,30)}\n"
            f"理由：{short(request.reason,120)}"
        )
        summary.setObjectName("permissionSummary")
        summary.setWordWrap(True)
        summary.setMaximumHeight(118)
        box.addWidget(summary)

        row=QHBoxLayout()
        row.setSpacing(12)
        deny=QPushButton("拒绝", objectName="permissionDeny")
        allow=QPushButton("同意", objectName="permissionAllow")
        deny.setMinimumHeight(40)
        allow.setMinimumHeight(40)
        deny.setMinimumWidth(150)
        allow.setMinimumWidth(150)
        row.addWidget(deny)
        row.addWidget(allow)
        box.addLayout(row)
        deny.clicked.connect(self.reject)
        allow.clicked.connect(self.accept)
