"""简易翻译器 (调用免费API)"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox,
    QPushButton, QLabel,
)
from PyQt6.QtCore import QThread, pyqtSignal
import urllib.request
import urllib.parse
import json


class TranslateThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, text, src, dst):
        super().__init__()
        self.text = text
        self.src = src
        self.dst = dst

    def run(self):
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": self.src,
                "tl": self.dst,
                "dt": "t",
                "q": self.text,
            }
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                result = "".join([s[0] for s in data[0] if s[0]])
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class TranslatorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 语言选择
        lang_row = QHBoxLayout()
        self.src_combo = QComboBox()
        self.src_combo.addItems(["自动检测", "中文", "英语", "日语", "韩语", "法语", "德语", "西班牙语"])
        self.dst_combo = QComboBox()
        self.dst_combo.addItems(["中文", "英语", "日语", "韩语", "法语", "德语", "西班牙语"])
        self.dst_combo.setCurrentIndex(1)

        lang_row.addWidget(QLabel("源语言:"))
        lang_row.addWidget(self.src_combo)
        lang_row.addWidget(QLabel("目标:"))
        lang_row.addWidget(self.dst_combo)

        swap_btn = QPushButton("↔")
        swap_btn.clicked.connect(self._swap_lang)
        lang_row.addWidget(swap_btn)
        lang_row.addStretch()
        layout.addLayout(lang_row)

        # 输入
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("输入要翻译的文字...")
        self.input_text.setMaximumHeight(120)
        layout.addWidget(self.input_text)

        # 按钮
        btn_row = QHBoxLayout()
        self.translate_btn = QPushButton("翻译")
        self.translate_btn.clicked.connect(self._translate)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(lambda: self.input_text.clear() or self.output_text.clear())
        btn_row.addStretch()
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(self.translate_btn)
        layout.addLayout(btn_row)

        # 输出
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("翻译结果...")
        layout.addWidget(self.output_text)

    def _get_lang_code(self, text):
        mapping = {"自动检测": "auto", "中文": "zh-CN", "英语": "en", "日语": "ja",
                   "韩语": "ko", "法语": "fr", "德语": "de", "西班牙语": "es"}
        return mapping.get(text, "auto")

    def _swap_lang(self):
        if self.src_combo.currentIndex() <= 0:
            return
        src = self.src_combo.currentIndex()
        dst = self.dst_combo.currentIndex()
        self.src_combo.setCurrentIndex(dst + 1 if dst + 1 < self.src_combo.count() else dst)
        self.dst_combo.setCurrentIndex(src - 1 if src - 1 >= 0 else src)

    def _translate(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            return
        self.translate_btn.setEnabled(False)
        self.translate_btn.setText("翻译中...")
        src = self._get_lang_code(self.src_combo.currentText())
        dst = self._get_lang_code(self.dst_combo.currentText())
        self._thread = TranslateThread(text, src, dst)
        self._thread.finished.connect(self._on_result)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_result(self, text):
        self.output_text.setText(text)
        self.translate_btn.setEnabled(True)
        self.translate_btn.setText("翻译")

    def _on_error(self, msg):
        self.output_text.setText(f"翻译失败: {msg}")
        self.translate_btn.setEnabled(True)
        self.translate_btn.setText("翻译")
