"""计算器"""

from PyQt6.QtWidgets import QWidget, QGridLayout, QLineEdit, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt


class CalculatorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setStyleSheet("font-size: 20px; padding: 10px; background: #1e1e2e; color: #cdd6f4;")
        layout.addWidget(self.display)

        grid = QGridLayout()
        buttons = [
            ("C", 0, 0), ("÷", 0, 1), ("×", 0, 2), ("⌫", 0, 3),
            ("7", 1, 0), ("8", 1, 1), ("9", 1, 2), ("-", 1, 3),
            ("4", 2, 0), ("5", 2, 1), ("6", 2, 2), ("+", 2, 3),
            ("1", 3, 0), ("2", 3, 1), ("3", 3, 2), ("=", 3, 3),
            ("0", 4, 0), (".", 4, 1), ("(", 4, 2), (")", 4, 3),
        ]
        for text, r, c in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(55, 45)
            btn.clicked.connect(lambda checked, t=text: self._on_click(t))
            if text in ("=",):
                btn.setStyleSheet("background: #89b4fa; color: #1e1e2e; font-weight: bold;")
            elif text in ("C", "⌫"):
                btn.setStyleSheet("background: #f38ba8; color: #1e1e2e;")
            grid.addWidget(btn, r, c)
        layout.addLayout(grid)

    def _on_click(self, text):
        if text == "C":
            self.display.clear()
        elif text == "⌫":
            self.display.setText(self.display.text()[:-1])
        elif text == "=":
            try:
                expr = self.display.text().replace("×", "*").replace("÷", "/")
                result = eval(expr)
                self.display.setText(str(result))
            except Exception:
                self.display.setText("错误")
        else:
            self.display.setText(self.display.text() + text)
