"""时间轴/操作历史组件"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QCheckBox,
    QHeaderView, QMenu, QDialog, QLabel, QTextEdit, QFormLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QColor

from model.models import TimelineModel, NoteModel, TodoModel, ReminderModel
from model.database import db
from ui.style import STYLE

ACTION_MAP = {"create": "新建", "modify": "修改", "delete": "删除", "restore": "恢复"}
TARGET_MAP = {"note": "便签", "todo": "待办", "reminder": "提醒"}
ACTION_COLORS = {
    "create": QColor("#a6e3a1"),
    "modify": QColor("#89b4fa"),
    "delete": QColor("#f38ba8"),
    "restore": QColor("#fab387"),
}
RESTORE_MODEL = {"note": NoteModel, "todo": TodoModel, "reminder": ReminderModel}


class TimelineWidget(QWidget):
    timeline_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLE)
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # --- 筛选栏 ---
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self._target_combo = QComboBox()
        self._target_combo.addItems(["全部", "便签", "待办", "提醒"])
        self._target_combo.setFont(QFont("Microsoft YaHei", 10))
        filter_bar.addWidget(QLabel("对象:"))
        filter_bar.addWidget(self._target_combo)

        self._action_combo = QComboBox()
        self._action_combo.addItems(["全部", "新建", "修改", "删除", "恢复"])
        self._action_combo.setFont(QFont("Microsoft YaHei", 10))
        filter_bar.addWidget(QLabel("操作:"))
        filter_bar.addWidget(self._action_combo)

        self._keyword_edit = QLineEdit()
        self._keyword_edit.setPlaceholderText("🔍 搜索详情...")
        self._keyword_edit.setFont(QFont("Microsoft YaHei", 10))
        filter_bar.addWidget(self._keyword_edit)

        self._search_btn = QPushButton("搜索")
        self._search_btn.setFont(QFont("Microsoft YaHei", 10))
        self._search_btn.setFixedHeight(32)
        self._search_btn.clicked.connect(self._load)
        filter_bar.addWidget(self._search_btn)

        layout.addLayout(filter_bar)

        # --- 仅删除项 ---
        self._deleted_only_cb = QCheckBox("仅显示已删除项（可恢复）")
        self._deleted_only_cb.setFont(QFont("Microsoft YaHei", 10))
        self._deleted_only_cb.stateChanged.connect(self._load)
        layout.addWidget(self._deleted_only_cb)

        # --- 时间轴表格 ---
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["时间", "操作类型", "对象类型", "详情"])
        self._table.setFont(QFont("Microsoft YaHei", 10))
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)

        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        vh = self._table.verticalHeader()
        vh.setVisible(False)

        layout.addWidget(self._table, stretch=1)

    # ========== 数据加载 ==========

    def _load(self):
        target_raw = self._target_combo.currentText()
        action_raw = self._action_combo.currentText()
        keyword = self._keyword_edit.text().strip()

        target_type = None
        if target_raw == "便签":
            target_type = "note"
        elif target_raw == "待办":
            target_type = "todo"
        elif target_raw == "提醒":
            target_type = "reminder"

        action_type = None
        rev_action = {v: k for k, v in ACTION_MAP.items()}
        if action_raw in rev_action:
            action_type = rev_action[action_raw]

        if self._deleted_only_cb.isChecked():
            action_type = "delete"

        records = TimelineModel.get_all(
            target_type=target_type,
            action_type=action_type,
            keyword=keyword,
            limit=500,
        )

        self._table.setRowCount(len(records))
        for row, r in enumerate(records):
            # 时间
            time_item = QTableWidgetItem(r.get("created_at", ""))
            time_item.setData(Qt.ItemDataRole.UserRole, r)
            self._table.setItem(row, 0, time_item)

            # 操作类型（带颜色）
            act = r.get("action_type", "")
            act_text = ACTION_MAP.get(act, act)
            act_item = QTableWidgetItem(act_text)
            color = ACTION_COLORS.get(act, QColor("#cdd6f4"))
            act_item.setForeground(color)
            self._table.setItem(row, 1, act_item)

            # 对象类型
            tgt = r.get("target_type", "")
            tgt_text = TARGET_MAP.get(tgt, tgt)
            self._table.setItem(row, 2, QTableWidgetItem(tgt_text))

            # 详情
            self._table.setItem(row, 3, QTableWidgetItem(r.get("detail", "")))

    # ========== 右键菜单 ==========

    def _on_context_menu(self, pos):
        item = self._table.itemAt(pos)
        if not item:
            return
        row = item.row()
        time_item = self._table.item(row, 0)
        if not time_item:
            return
        record = time_item.data(Qt.ItemDataRole.UserRole)
        if not record:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #313244; color: #cdd6f4; border: 1px solid #45475a; }"
            "QMenu::item { padding: 6px 24px; }"
            "QMenu::item:selected { background: #45475a; }"
        )

        if record.get("action_type") == "delete":
            restore_action = QAction("🔄 恢复", menu)
            restore_action.triggered.connect(lambda: self._on_restore(record))
            menu.addAction(restore_action)

        detail_action = QAction("📋 查看详情", menu)
        detail_action.triggered.connect(lambda: self._on_view_detail(record))
        menu.addAction(detail_action)

        menu.exec(self._table.mapToGlobal(pos))

    # ========== 恢复操作 ==========

    def _on_restore(self, record):
        target_type = record.get("target_type")
        target_id = record.get("target_id")
        model_cls = RESTORE_MODEL.get(target_type)
        if model_cls:
            model_cls.restore(target_id)
            self._load()
            self.timeline_changed.emit()

    # ========== 查看详情 ==========

    def _on_view_detail(self, record):
        dialog = QDialog(self)
        dialog.setWindowTitle("操作详情")
        dialog.resize(550, 400)
        dialog.setStyleSheet(STYLE)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 基本信息
        form = QFormLayout()
        form.setSpacing(6)

        act = ACTION_MAP.get(record.get("action_type", ""), "")
        tgt = TARGET_MAP.get(record.get("target_type", ""), "")
        form.addRow("时间:", QLabel(record.get("created_at", "")))
        form.addRow("操作:", QLabel(act))
        form.addRow("对象:", QLabel(f"{tgt} (ID: {record.get('target_id', '')})"))
        form.addRow("详情:", QLabel(record.get("detail", "")))
        layout.addLayout(form)

        # 旧数据
        old_data = record.get("old_data", "") or ""
        if old_data:
            layout.addWidget(QLabel("旧数据:"))
            old_edit = QTextEdit()
            old_edit.setReadOnly(True)
            old_edit.setFont(QFont("Microsoft YaHei", 9))
            old_edit.setMaximumHeight(100)
            old_edit.setPlainText(self._format_json(old_data))
            layout.addWidget(old_edit)

        # 新数据
        new_data = record.get("new_data", "") or ""
        if new_data:
            layout.addWidget(QLabel("新数据:"))
            new_edit = QTextEdit()
            new_edit.setReadOnly(True)
            new_edit.setFont(QFont("Microsoft YaHei", 9))
            new_edit.setMaximumHeight(100)
            new_edit.setPlainText(self._format_json(new_data))
            layout.addWidget(new_edit)

        close_btn = QPushButton("关闭")
        close_btn.setFixedHeight(32)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

    @staticmethod
    def _format_json(text):
        import json
        try:
            return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            return text
