"""小账本"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from datetime import datetime
from model.models import LedgerModel


class LedgerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 输入区域
        input_row = QHBoxLayout()
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("金额")
        self.amount_input.setFixedWidth(100)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["支出", "收入"])

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("分类(如:餐饮)")
        self.category_input.setFixedWidth(120)

        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("备注")

        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add_record)

        input_row.addWidget(QLabel("金额:"))
        input_row.addWidget(self.amount_input)
        input_row.addWidget(self.type_combo)
        input_row.addWidget(self.category_input)
        input_row.addWidget(self.note_input)
        input_row.addWidget(add_btn)
        input_row.addStretch()
        layout.addLayout(input_row)

        # 汇总
        self.summary_label = QLabel("本月支出: ¥0.00  收入: ¥0.00  结余: ¥0.00")
        layout.addWidget(self.summary_label)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["日期", "类型", "金额", "分类", "备注"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.table)

    def _load_data(self):
        year_month = datetime.now().strftime("%Y-%m")
        records = LedgerModel.get_all(year_month)
        self.table.setRowCount(len(records))
        for i, r in enumerate(records):
            self.table.setItem(i, 0, QTableWidgetItem(r["ledger_date"]))
            t = "收入" if r["ledger_type"] == "income" else "支出"
            self.table.setItem(i, 1, QTableWidgetItem(t))
            self.table.setItem(i, 2, QTableWidgetItem(f"¥{r['amount']:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(r.get("category", "")))
            self.table.setItem(i, 4, QTableWidgetItem(r.get("note", "")))

        summary = LedgerModel.get_summary(year_month)
        income = sum(s["total"] for s in summary if s["ledger_type"] == "income")
        expense = sum(s["total"] for s in summary if s["ledger_type"] == "expense")
        self.summary_label.setText(
            f"本月支出: ¥{expense:.2f}  收入: ¥{income:.2f}  结余: ¥{income - expense:.2f}"
        )

    def _add_record(self):
        try:
            amount = float(self.amount_input.text())
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效金额")
            return
        t = "income" if self.type_combo.currentText() == "收入" else "expense"
        LedgerModel.add(amount, t, self.category_input.text(), self.note_input.text())
        self.amount_input.clear()
        self.note_input.clear()
        self._load_data()

    def _on_context_menu(self, pos):
        from PyQt6.QtWidgets import QMenu
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        menu = QMenu()
        del_action = menu.addAction("删除")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == del_action:
            records = LedgerModel.get_all(datetime.now().strftime("%Y-%m"))
            if row < len(records):
                LedgerModel.delete(records[row]["id"])
                self._load_data()
