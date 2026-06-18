"""分类管理组件"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMenu, QMessageBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QAction

from model.models import CategoryModel, NoteModel, TodoModel, ReminderModel


class CategoryWidget(QWidget):
    category_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        from ui.style import STYLE
        self.setStyleSheet(STYLE)
        self._setup_ui()
        self._load_categories()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # --- 信息标签 ---
        info_label = QLabel("最多50个分类，每类1000条记录")
        info_label.setFont(QFont("Microsoft YaHei", 10))
        info_label.setStyleSheet("color: #a6adc8; padding: 4px 0;")
        layout.addWidget(info_label)

        # --- 输入行 ---
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("输入分类名称...")
        self._name_edit.setFont(QFont("Microsoft YaHei", 10))
        self._name_edit.returnPressed.connect(self._on_add_category)
        input_row.addWidget(self._name_edit, stretch=1)

        self._add_btn = QPushButton("➕ 添加分类")
        self._add_btn.setFont(QFont("Microsoft YaHei", 10))
        self._add_btn.setFixedHeight(34)
        self._add_btn.setStyleSheet(
            "QPushButton { background: #89b4fa; color: #1e1e2e; }"
            "QPushButton:hover { background: #b4d0fb; }"
        )
        self._add_btn.clicked.connect(self._on_add_category)
        input_row.addWidget(self._add_btn)

        layout.addLayout(input_row)

        # --- 分类表格 ---
        self._table = QTableWidget()
        self._table.setFont(QFont("Microsoft YaHei", 10))
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["ID", "名称", "排序", "创建时间", "条目数"])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.itemChanged.connect(self._on_item_changed)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setDefaultSectionSize(34)

        layout.addWidget(self._table, stretch=1)

    # ========== 数据加载 ==========

    def _count_items(self, cid):
        notes = NoteModel.get_all(category_id=cid)
        todos = TodoModel.get_all(category_id=cid)
        reminders = [r for r in ReminderModel.get_all() if r.get("category_id") == cid]
        return len(notes) + len(todos) + len(reminders)

    def _load_categories(self):
        self._table.setRowCount(0)
        categories = CategoryModel.get_all()
        for row, cat in enumerate(categories):
            self._table.insertRow(row)
            cid = cat["id"]

            item_id = self._make_item(str(cid), editable=False)
            self._table.setItem(row, 0, item_id)

            item_name = self._make_item(cat["name"], editable=True)
            item_name.setData(Qt.ItemDataRole.UserRole, cid)
            self._table.setItem(row, 1, item_name)

            item_sort = self._make_item(str(cat.get("sort_order", "")), editable=False)
            self._table.setItem(row, 2, item_sort)

            item_time = self._make_item(cat.get("created_at", ""), editable=False)
            self._table.setItem(row, 3, item_time)

            count = self._count_items(cid)
            item_count = self._make_item(str(count), editable=False)
            item_count.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 4, item_count)

    def _make_item(self, text, editable=False):
        item = QTableWidgetItem(text)
        if editable:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    # ========== 添加分类 ==========

    def _on_add_category(self):
        name = self._name_edit.text().strip()
        if not name:
            return
        cid = CategoryModel.add(name)
        if cid is None:
            QMessageBox.warning(self, "提示", f"已达到最大分类数量（{CategoryModel.MAX_COUNT}个）")
            return
        self._name_edit.clear()
        self._load_categories()
        self.category_changed.emit()

    # ========== 内联编辑 ==========

    def _on_item_changed(self, item):
        if item.column() != 1:
            return
        cid = item.data(Qt.ItemDataRole.UserRole)
        if cid is None:
            return
        new_name = item.text().strip()
        if new_name:
            CategoryModel.update_name(cid, new_name)
            self.category_changed.emit()

    # ========== 右键菜单 ==========

    def _on_context_menu(self, pos):
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if not item:
            return
        cid = self._table.item(row, 1).data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #313244; color: #cdd6f4; border: 1px solid #45475a; }"
            "QMenu::item { padding: 6px 24px; }"
            "QMenu::item:selected { background: #45475a; }"
        )

        edit_action = QAction("✏️ 编辑", menu)
        edit_action.triggered.connect(lambda: self._on_edit(row))
        menu.addAction(edit_action)

        delete_action = QAction("🗑️ 删除", menu)
        delete_action.triggered.connect(lambda: self._on_delete_category(cid))
        menu.addAction(delete_action)

        menu.exec(self._table.mapToGlobal(pos))

    def _on_edit(self, row):
        self._table.editItem(self._table.item(row, 1))

    def _on_delete_category(self, cid):
        if cid <= 0:
            return
        count = self._count_items(cid)
        if count > 0:
            reply = QMessageBox.question(
                self, "确认删除",
                f"该分类下有 {count} 条记录（便签/待办/提醒），\n删除分类不会删除这些记录，确定继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        CategoryModel.delete(cid)
        self._load_categories()
        self.category_changed.emit()
