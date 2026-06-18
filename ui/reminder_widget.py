"""提醒管理组件 — 支持公历/农历、重复、间隔提醒"""

from datetime import datetime, date

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLineEdit, QTextEdit, QDateTimeEdit, QComboBox, QCheckBox,
    QSpinBox, QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QMenu, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QAction, QColor

from model.models import ReminderModel
from model.models import CategoryModel
from tools.lunar import LunarCalendar

MOCHA = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "blue": "#89b4fa",
    "red": "#f38ba8",
    "yellow": "#f9e2af",
    "green": "#a6e3a1",
    "lavender": "#b4befe",
    "teal": "#94e2d5",
    "pink": "#f5c2e7",
}

REPEAT_TYPES = ["none", "daily", "weekly", "monthly", "quarterly", "yearly"]
REPEAT_LABELS = {
    "none": "不重复", "daily": "每天", "weekly": "每周",
    "monthly": "每月", "quarterly": "每季度", "yearly": "每年",
}

TABLE_STYLE = f"""
QTableWidget {{
    background: {MOCHA['base']};
    alternate-background-color: {MOCHA['surface0']};
    border: 1px solid {MOCHA['surface1']};
    gridline-color: {MOCHA['surface1']};
    color: {MOCHA['text']};
    selection-background-color: {MOCHA['blue']};
    selection-color: {MOCHA['base']};
}}
QTableWidget::item {{
    padding: 6px;
    border-bottom: 1px solid {MOCHA['surface0']};
}}
QHeaderView::section {{
    background: {MOCHA['surface0']};
    color: {MOCHA['subtext']};
    border: none;
    border-bottom: 2px solid {MOCHA['surface1']};
    padding: 8px 6px;
    font-weight: bold;
}}
QScrollBar:vertical {{
    background: {MOCHA['base']};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {MOCHA['surface1']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {MOCHA['surface2']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""

INPUT_STYLE = f"""
    background: {MOCHA['surface0']};
    border: 1px solid {MOCHA['surface1']};
    border-radius: 6px;
    padding: 6px;
    color: {MOCHA['text']};
    font-size: 13px;
"""


class ReminderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._editing_id = None
        self._setup_ui()
        self._refresh()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # ---- input form ----
        form_frame = QFrame()
        form_frame.setStyleSheet(f"QFrame {{ background: {MOCHA['surface0']}; border-radius: 10px; padding: 4px; }}")
        form_layout = QGridLayout(form_frame)
        form_layout.setContentsMargins(16, 12, 16, 12)
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(12)

        lbl_style = f"color: {MOCHA['subtext']}; font-size: 12px;"

        # row 0: title + category
        self.title_label = QLabel("标题 *")
        self.title_label.setStyleSheet(lbl_style)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("提醒标题（必填）")
        self.title_edit.setStyleSheet(INPUT_STYLE)
        form_layout.addWidget(self.title_label, 0, 0)
        form_layout.addWidget(self.title_edit, 0, 1)

        cat_label = QLabel("分类")
        cat_label.setStyleSheet(lbl_style)
        self.cat_edit = QComboBox()
        self.cat_edit.addItem("无分类", 0)
        self.cat_edit.setStyleSheet(INPUT_STYLE)
        form_layout.addWidget(cat_label, 0, 2)
        form_layout.addWidget(self.cat_edit, 0, 3)

        # row 1: remind_time + lunar info
        time_label = QLabel("提醒时间")
        time_label.setStyleSheet(lbl_style)
        self.time_edit = QDateTimeEdit()
        self.time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.time_edit.setCalendarPopup(True)
        self.time_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.time_edit.setStyleSheet(INPUT_STYLE)
        form_layout.addWidget(time_label, 1, 0)
        form_layout.addWidget(self.time_edit, 1, 1)

        self.lunar_label = QLabel("")
        self.lunar_label.setStyleSheet(f"color: {MOCHA['teal']}; font-size: 11px; padding: 6px;")
        form_layout.addWidget(self.lunar_label, 1, 2, 1, 2)

        # row 2: repeat + interval
        repeat_label = QLabel("重复类型")
        repeat_label.setStyleSheet(lbl_style)
        self.repeat_edit = QComboBox()
        for r in REPEAT_TYPES:
            self.repeat_edit.addItem(REPEAT_LABELS[r], r)
        self.repeat_edit.setStyleSheet(INPUT_STYLE)
        self.repeat_edit.currentIndexChanged.connect(self._on_repeat_changed)
        form_layout.addWidget(repeat_label, 2, 0)
        form_layout.addWidget(self.repeat_edit, 2, 1)

        interval_label = QLabel("间隔(分钟)")
        interval_label.setStyleSheet(lbl_style)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(0, 1440)
        self.interval_spin.setValue(0)
        self.interval_spin.setSuffix(" 分钟")
        self.interval_spin.setStyleSheet(INPUT_STYLE)
        form_layout.addWidget(interval_label, 2, 2)
        form_layout.addWidget(self.interval_spin, 2, 3)

        # row 3: checkboxes
        check_row = QHBoxLayout()
        check_row.setSpacing(20)

        self.lunar_check = QCheckBox("农历提醒")
        self.lunar_check.setStyleSheet(f"color: {MOCHA['text']}; font-size: 13px;")
        self.lunar_check.toggled.connect(self._update_lunar_preview)
        check_row.addWidget(self.lunar_check)

        self.important_check = QCheckBox("重要事项")
        self.important_check.setStyleSheet(f"color: {MOCHA['text']}; font-size: 13px;")
        check_row.addWidget(self.important_check)

        check_row.addStretch()
        form_layout.addLayout(check_row, 3, 0, 1, 4)

        # row 4: content
        content_label = QLabel("内容描述")
        content_label.setStyleSheet(lbl_style)
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("提醒描述（可选）")
        self.content_edit.setMaximumHeight(80)
        self.content_edit.setStyleSheet(INPUT_STYLE)
        form_layout.addWidget(content_label, 4, 0)
        form_layout.addWidget(self.content_edit, 4, 1, 1, 3)

        # row 5: action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.add_btn = QPushButton("添加提醒")
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {MOCHA['blue']};
                color: {MOCHA['base']};
                font-weight: bold;
                padding: 8px 20px;
                font-size: 13px;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: #74c7ec; }}
        """)
        self.add_btn.clicked.connect(self._on_save)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {MOCHA['surface1']};
                color: {MOCHA['text']};
                padding: 8px 20px;
                font-size: 13px;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: {MOCHA['surface2']}; }}
        """)
        self.cancel_btn.clicked.connect(self._clear_form)
        self.cancel_btn.hide()

        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        form_layout.addLayout(btn_row, 5, 0, 1, 4)

        layout.addWidget(form_frame)

        # ---- filter bar ----
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        filter_bar.addWidget(QLabel("分类筛选:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("全部分类", 0)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.filter_combo.setStyleSheet(INPUT_STYLE)
        filter_bar.addWidget(self.filter_combo)

        filter_bar.addSpacing(20)

        self.deleted_check = QCheckBox("显示已删除")
        self.deleted_check.setStyleSheet(f"color: {MOCHA['subtext']}; font-size: 12px;")
        self.deleted_check.toggled.connect(self._on_filter_changed)
        filter_bar.addWidget(self.deleted_check)

        filter_bar.addStretch()
        layout.addLayout(filter_bar)

        # ---- table ----
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["标题", "内容", "提醒时间", "重复类型", "农历", "重要", "状态"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.cellClicked.connect(self._on_row_clicked)

        layout.addWidget(self.table)

    # ------------------------------------------------------------------
    # data
    # ------------------------------------------------------------------

    def _refresh(self):
        self._refresh_categories()
        self._load_reminders()
        self._update_lunar_preview()

    def _refresh_categories(self):
        cats = CategoryModel.get_all()
        for combo in (self.filter_combo, self.cat_edit):
            current = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("全部分类" if combo is self.filter_combo else "无分类", 0)
            for c in cats:
                combo.addItem(c["name"], c["id"])
            idx = combo.findData(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def _load_reminders(self):
        cat_id = self.filter_combo.currentData()
        show_deleted = self.deleted_check.isChecked()
        reminders = ReminderModel.get_all(include_deleted=show_deleted)

        if cat_id and cat_id > 0:
            reminders = [r for r in reminders if r.get("category_id") == cat_id]

        self.table.setRowCount(len(reminders))
        for row, r in enumerate(reminders):
            self._set_table_row(row, r)

    def _set_table_row(self, row, r):
        deleted = r.get("is_deleted", 0)
        triggered = r.get("is_triggered", 0)
        is_important = r.get("is_important", 0)

        items = [
            ("title", r.get("title", "")),
            ("content", r.get("content", "")),
            ("remind_time", r.get("remind_time", "")),
            ("repeat", REPEAT_LABELS.get(r.get("repeat_type", "none"), "不重复")),
            ("lunar", "是" if r.get("is_lunar") else "否"),
            ("important", "⭐" if is_important else ""),
        ]

        for col, (_, val) in enumerate(items):
            item = QTableWidgetItem(str(val))
            item.setData(Qt.ItemDataRole.UserRole, r["id"])
            if deleted:
                item.setForeground(QColor(MOCHA["surface2"]))
            elif triggered:
                item.setForeground(QColor(MOCHA["green"]))
            elif is_important:
                item.setForeground(QColor(MOCHA["red"]))
            self.table.setItem(row, col, item)

        # status column
        if deleted:
            status = "已删除"
            color = MOCHA["surface2"]
        elif triggered:
            status = "已触发"
            color = MOCHA["green"]
        else:
            status = "待提醒"
            color = MOCHA["teal"]
        status_item = QTableWidgetItem(status)
        status_item.setData(Qt.ItemDataRole.UserRole, r["id"])
        status_item.setForeground(QColor(color))
        self.table.setItem(row, 6, status_item)

        if is_important:
            status_item.setForeground(QColor(MOCHA["red"]))

    # ------------------------------------------------------------------
    # form actions
    # ------------------------------------------------------------------

    def _on_save(self):
        title = self.title_edit.text().strip()
        if not title:
            return

        remind_time = self.time_edit.dateTime().toString("yyyy-MM-dd HH:mm")
        content = self.content_edit.toPlainText().strip()
        repeat_type = self.repeat_edit.currentData()
        is_lunar = self.lunar_check.isChecked()
        is_important = self.important_check.isChecked()
        interval_minutes = self.interval_spin.value()
        category_id = self.cat_edit.currentData() or 1

        if self._editing_id:
            ReminderModel.update(
                self._editing_id,
                title=title,
                content=content,
                remind_time=remind_time,
                repeat_type=repeat_type,
                is_lunar=1 if is_lunar else 0,
                is_important=1 if is_important else 0,
                interval_minutes=interval_minutes,
                category_id=category_id,
                is_triggered=0,
            )
        else:
            ReminderModel.add(
                title=title,
                remind_time=remind_time,
                content=content,
                repeat_type=repeat_type,
                is_lunar=is_lunar,
                is_important=is_important,
                interval_minutes=interval_minutes,
                category_id=category_id,
            )

        self._clear_form()
        self._refresh()

    def _clear_form(self):
        self._editing_id = None
        self.title_edit.clear()
        self.content_edit.clear()
        self.time_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.repeat_edit.setCurrentIndex(0)
        self.lunar_check.setChecked(False)
        self.important_check.setChecked(False)
        self.interval_spin.setValue(0)
        self.cat_edit.setCurrentIndex(0)
        self.add_btn.setText("添加提醒")
        self.cancel_btn.hide()

    # ------------------------------------------------------------------
    # table interactions
    # ------------------------------------------------------------------

    def _on_row_clicked(self, row, col):
        item = self.table.item(row, 0)
        if not item:
            return
        rid = item.data(Qt.ItemDataRole.UserRole)
        reminders = ReminderModel.get_all(include_deleted=True)
        r = next((x for x in reminders if x["id"] == rid), None)
        if not r or r.get("is_deleted"):
            return

        self._editing_id = r["id"]
        self.title_edit.setText(r.get("title", ""))
        self.content_edit.setPlainText(r.get("content", ""))

        try:
            dt = QDateTime.fromString(r.get("remind_time", ""), "yyyy-MM-dd HH:mm")
            if dt.isValid():
                self.time_edit.setDateTime(dt)
        except Exception:
            pass

        idx = self.repeat_edit.findData(r.get("repeat_type", "none"))
        if idx >= 0:
            self.repeat_edit.setCurrentIndex(idx)

        self.lunar_check.setChecked(bool(r.get("is_lunar")))
        self.important_check.setChecked(bool(r.get("is_important")))
        self.interval_spin.setValue(r.get("interval_minutes", 0))

        cat_idx = self.cat_edit.findData(r.get("category_id", 0))
        if cat_idx >= 0:
            self.cat_edit.setCurrentIndex(cat_idx)

        self.add_btn.setText("更新提醒")
        self.cancel_btn.show()
        self._update_lunar_preview()

    def _on_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        rid = item.data(Qt.ItemDataRole.UserRole)
        reminders = ReminderModel.get_all(include_deleted=True)
        r = next((x for x in reminders if x["id"] == rid), None)
        if not r:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {MOCHA['surface0']}; border: 1px solid {MOCHA['surface1']}; }}
            QMenu::item {{ padding: 6px 28px; color: {MOCHA['text']}; }}
            QMenu::item:selected {{ background: {MOCHA['surface1']}; }}
            QMenu::separator {{ height: 1px; background: {MOCHA['surface1']}; margin: 4px 8px; }}
        """)

        if r.get("is_deleted"):
            restore_action = QAction("恢复提醒", self)
            restore_action.triggered.connect(lambda checked, rid=rid: self._restore(rid))
            menu.addAction(restore_action)
        else:
            edit_action = QAction("编辑", self)
            edit_action.triggered.connect(lambda checked, r=row: self._on_row_clicked(r, 0))
            menu.addAction(edit_action)

            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda checked, rid=rid: self._delete(rid))
            menu.addAction(delete_action)

        menu.exec(self.table.mapToGlobal(pos))

    # ------------------------------------------------------------------
    # filter
    # ------------------------------------------------------------------

    def _on_filter_changed(self):
        self._load_reminders()

    def _on_repeat_changed(self):
        repeat = self.repeat_edit.currentData()
        self.interval_spin.setEnabled(repeat == "none")

    # ------------------------------------------------------------------
    # lunar
    # ------------------------------------------------------------------

    def _update_lunar_preview(self):
        if self.lunar_check.isChecked():
            qdt = self.time_edit.dateTime()
            solar = date(qdt.date().year(), qdt.date().month(), qdt.date().day())
            lunar_str = LunarCalendar.format_lunar_date(solar)
            self.lunar_label.setText(f"农历: {lunar_str}" if lunar_str else "")
            self.lunar_label.show()
        else:
            self.lunar_label.hide()

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------

    def _delete(self, rid):
        ReminderModel.delete(rid)
        if self._editing_id == rid:
            self._clear_form()
        self._refresh()

    def _restore(self, rid):
        ReminderModel.restore(rid)
        self._refresh()
