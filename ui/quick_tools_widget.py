"""快捷工具栏"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

from model.models import QuickToolModel


class QuickToolsBar(QWidget):
    tool_clicked = pyqtSignal(str)

    TOOL_ICONS = {
        "calculator": "🔢 计算器",
        "ledger": "💰 小账本",
        "translator": "🌐 翻译",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(4)

        label = QLabel("快捷工具")
        label.setFont(QFont("Microsoft YaHei", 10))
        label.setStyleSheet("color: #585b70; padding: 4px 8px;")
        layout.addWidget(label)

        tools = QuickToolModel.get_all()
        for t in tools:
            text = self.TOOL_ICONS.get(t["tool_type"], f"🔧 {t['name']}")
            btn = QPushButton(text)
            btn.setFont(QFont("Microsoft YaHei", 10))
            btn.setFixedHeight(32)
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding-left: 12px; color: #a6adc8; }"
                "QPushButton:hover { background: #313244; color: #cdd6f4; }"
            )
            btn.clicked.connect(lambda checked, tt=t["tool_type"]: self.tool_clicked.emit(tt))
            layout.addWidget(btn)
