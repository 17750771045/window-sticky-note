from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox, QFrame,
    QLineEdit, QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QLabel, QMenu, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QAction

from model.models import TodoModel, CategoryModel
from model.database import db

# Catppuccin Mocha palette
MOCHA = {
    "base": "#1e1e2e",
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


class QuadrantListWidget(QListWidget):
    order_changed = pyqtSignal()
    add_todo_requested = pyqtSignal(int)  # quadrant
    edit_todo_requested = pyqtSignal(int, str)  # tid, content

    def __init__(self, quadrant, parent=None):
        super().__init__(parent)
        self._quadrant = quadrant
        self._loading = False
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setStyleSheet(
            f"QListWidget {{ background: transparent; border: none; "
            f"border-radius: 6px; padding: 5px; outline: none; }}"
            f"QListWidget::item {{ padding: 4px 6px; margin-bottom: 2px; border: none; outline: none; background: transparent; border-radius: 4px; min-height: 20px; }}"
            f"QListWidget::item:selected {{ background: {MOCHA['surface1']}; border: none; outline: none; }}"
            f"QListWidget::item:hover {{ background: {MOCHA['surface1']}; border: none; outline: none; }}"
        )
        self.itemChanged.connect(self._on_item_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    @property
    def quadrant(self):
        return self._quadrant

    def set_loading(self, v):
        self._loading = v

    def _on_item_double_clicked(self, item):
        tid = item.data(Qt.ItemDataRole.UserRole)
        todo = TodoModel.get_by_id(tid)
        content = todo["content"] if todo else ""
        self.edit_todo_requested.emit(tid, content)

    def mouseDoubleClickEvent(self, event):
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        if item is None:
            self.add_todo_requested.emit(self._quadrant)
        else:
            super().mouseDoubleClickEvent(event)

    def _on_item_changed(self, item):
        if self._loading:
            return
        tid = item.data(Qt.ItemDataRole.UserRole)
        if not tid:
            return
        checked = item.checkState() == Qt.CheckState.Checked
        is_completed = item.data(Qt.ItemDataRole.UserRole + 1)
        if bool(checked) == bool(is_completed):
            return
        TodoModel.toggle_complete(tid)
        item.setData(Qt.ItemDataRole.UserRole + 1, 1 if checked else 0)
        font = item.font()
        font.setStrikeOut(checked)
        item.setFont(font)
        item.setForeground(QColor(MOCHA["surface1"] if checked else MOCHA["text"]))

    def dropEvent(self, event):
        source = event.source()
        if source is self:
            super().dropEvent(event)
            self.order_changed.emit()
        elif isinstance(source, QuadrantListWidget):
            item = source.currentItem()
            if item is None:
                event.ignore()
                return
            tid = item.data(Qt.ItemDataRole.UserRole)
            row = source.row(item)
            taken = source.takeItem(row)
            drop_pos = self.indexAt(event.position().toPoint())
            if drop_pos.isValid():
                self.insertItem(drop_pos.row(), taken)
            else:
                self.addItem(taken)
            TodoModel.update(tid, quadrant=self._quadrant)
            source.order_changed.emit()
            self.order_changed.emit()
        else:
            event.ignore()


class TodoWidget(QWidget):
    QUADRANT_INFO = [
        ("紧急", MOCHA["red"], 1),
        ("不急", MOCHA["blue"], 2),
    ]

    def __init__(self):
        super().__init__()
        self.lists = {}
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        # --- category filter bar ---
        flt = QHBoxLayout()
        flt.addWidget(QLabel("分类筛选:"))
        self.cat_filter = QComboBox()
        self.cat_filter.addItem("全部分类", 0)
        self.cat_filter.currentIndexChanged.connect(self._refresh)
        flt.addWidget(self.cat_filter)
        flt.addStretch()
        
        self.done_btn = QPushButton("✅")
        self.done_btn.setFixedSize(32, 28)
        self.done_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 16px;
                padding: 0;
            }
            QPushButton:hover {
                background: #313244;
                border-radius: 4px;
            }
        """)
        self.done_btn.setToolTip("已办理")
        self.done_btn.clicked.connect(self._show_done)
        flt.addWidget(self.done_btn)
        
        self.trash_btn = QPushButton("🗑️")
        self.trash_btn.setFixedSize(32, 28)
        self.trash_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 16px;
                padding: 0;
            }
            QPushButton:hover {
                background: #313244;
                border-radius: 4px;
            }
        """)
        self.trash_btn.setToolTip("回收站")
        self.trash_btn.clicked.connect(self._show_trash)
        flt.addWidget(self.trash_btn)
        
        layout.addLayout(flt)

        # --- vertical quadrant list ---
        vbox = QVBoxLayout()
        for i, (title, color, q) in enumerate(self.QUADRANT_INFO):
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    border: 2px solid {color};
                    border-radius: 10px;
                    background: {MOCHA['base']};
                }}
            """)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(0, 0, 0, 0)
            
            header = QWidget()
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(8, 4, 8, 4)
            header_layout.setSpacing(8)
            
            title_label = QLabel(title)
            title_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            
            add_btn = QPushButton("+")
            add_btn.setFixedSize(15, 15)
            add_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: {MOCHA['base']};
                    border: none;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    opacity: 0.8;
                }}
            """)
            add_btn.clicked.connect(lambda checked, quad=q: self._add_todo_to_quadrant(quad))
            header_layout.addWidget(add_btn)
            
            frame_layout.addWidget(header)
            
            lst = QuadrantListWidget(q)
            lst.order_changed.connect(self._sync_sort_orders)
            lst.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            lst.customContextMenuRequested.connect(
                lambda pos, l=lst: self._context_menu(l, pos)
            )
            lst.add_todo_requested.connect(self._add_todo_to_quadrant)
            lst.edit_todo_requested.connect(self._edit_todo)
            
            list_container = QWidget()
            list_layout = QVBoxLayout(list_container)
            list_layout.setContentsMargins(6, 6, 6, 6)
            list_layout.addWidget(lst)
            frame_layout.addWidget(list_container)
            lst.setMinimumHeight(60)
            
            self.lists[q] = lst
#            frame.setMinimumHeight(150)
#            frame.setMaximumHeight(400)
            vbox.addWidget(frame, 1)

        layout.addLayout(vbox)

    # ------------------------------------------------------------------
    # data / refresh
    # ------------------------------------------------------------------

    def _refresh_categories(self):
        cats = CategoryModel.get_all()
        current = self.cat_filter.currentData()
        self.cat_filter.blockSignals(True)
        self.cat_filter.clear()
        self.cat_filter.addItem("全部分类", 0)
        for c in cats:
            self.cat_filter.addItem(c["name"], c["id"])
        idx = self.cat_filter.findData(current)
        if idx >= 0:
            self.cat_filter.setCurrentIndex(idx)
        self.cat_filter.blockSignals(False)

    _CAT_COLORS = [
        "#89b4fa", "#a6e3a1", "#f9e2af", "#f38ba8", "#b4befe",
        "#94e2d5", "#f5c2e7", "#fab387", "#eba0ac", "#89b4fa",
    ]

    def _get_category_color(self, cat_id):
        if cat_id <= 0:
            return MOCHA["subtext"]
        return self._CAT_COLORS[(cat_id - 1) % len(self._CAT_COLORS)]

    def _refresh(self):
        self._refresh_categories()
        cat_id = self.cat_filter.currentData()
        all_todos = TodoModel.get_all(category_id=cat_id) if cat_id else TodoModel.get_all()
        all_todos = [t for t in all_todos if t["is_completed"] == 0]
        cats = {c["id"]: c["name"] for c in CategoryModel.get_all()}

        for q, lst in self.lists.items():
            lst.set_loading(True)
            lst.blockSignals(True)
            lst.clear()
            for t in all_todos:
                if t["quadrant"] != q:
                    continue
                cat_name = cats.get(t["category_id"], "")
                cat_color = self._get_category_color(t["category_id"])
                
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, t["id"])
                item.setData(Qt.ItemDataRole.UserRole + 1, t["is_completed"])
                item.setData(Qt.ItemDataRole.UserRole + 2, t["category_id"])
                
                if cat_name:
                    from PyQt6.QtWidgets import QCheckBox
                    widget = QWidget()
                    widget.setStyleSheet("background: transparent; border: none;")
                    layout = QHBoxLayout(widget)
                    layout.setContentsMargins(0, 2, 8, 2)
                    layout.setSpacing(6)
                    
                    checkbox = QCheckBox()
                    checkbox.setChecked(bool(t["is_completed"]))
                    checkbox.setStyleSheet("background: transparent; border: none;")
                    checkbox.stateChanged.connect(
                        lambda state, tid=t["id"], item=item: self._on_checkbox_changed(tid, item, state)
                    )
                    layout.addWidget(checkbox)
                    
                    content_label = QLabel(t["content"])
                    content_label.setStyleSheet(f"color: {MOCHA['text']}; background: transparent;")
                    content_label.setWordWrap(True)
                    content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                    if t["is_completed"]:
                        font = QFont()
                        font.setStrikeOut(True)
                        content_label.setFont(font)
                        content_label.setStyleSheet(f"color: {MOCHA['surface1']}; background: transparent;")
                    
                    layout.addWidget(content_label)
                    layout.addStretch()
                    
                    cat_label = QLabel(f"[{cat_name}]")
                    cat_label.setStyleSheet(f"color: {cat_color}; font-size: 12px; background: transparent;")
                    layout.addWidget(cat_label)
                    
                    hint = widget.sizeHint()
                    content_label.adjustSize()
                    hint.setHeight(max(content_label.height() + 12, 48))
                    item.setSizeHint(hint)
                    lst.addItem(item)
                    lst.setItemWidget(item, widget)
                else:
                    lst.addItem(item)
            lst.blockSignals(False)
            lst.set_loading(False)

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------

    def _add_todo(self):
        content = self.input.text().strip()
        if not content:
            return
        quadrant = self.q_combo.currentIndex() + 1
        cat_id = self.cat_combo.currentData() or 1
        TodoModel.add(content, quadrant=quadrant, category_id=cat_id)
        self.input.clear()
        self._refresh()

    def _sync_sort_orders(self):
        for q, lst in self.lists.items():
            for i in range(lst.count()):
                item = lst.item(i)
                tid = item.data(Qt.ItemDataRole.UserRole)
                if tid:
                    TodoModel.update(tid, quadrant=q, sort_order=i)

    def _context_menu(self, lst, pos):
        item = lst.itemAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {MOCHA['surface0']}; border: 1px solid {MOCHA['surface1']}; }}
            QMenu::item {{ padding: 6px 28px; color: {MOCHA['text']}; }}
            QMenu::item:selected {{ background: {MOCHA['surface1']}; }}
            QMenu::separator {{ height: 1px; background: {MOCHA['surface1']}; margin: 4px 8px; }}
        """)

        if item:
            tid = item.data(Qt.ItemDataRole.UserRole)
            is_completed = item.data(Qt.ItemDataRole.UserRole + 1)

            toggle = QAction("取消完成" if is_completed else "标记完成", self)
            toggle.triggered.connect(lambda checked, tid=tid: self._toggle_complete(tid))
            menu.addAction(toggle)

            del_action = QAction("删除", self)
            del_action.triggered.connect(lambda checked, tid=tid: self._delete_todo(tid))
            menu.addAction(del_action)

        restore_action = QAction("恢复已删除待办", self)
        restore_action.triggered.connect(self._restore_deleted)
        menu.addSeparator()
        menu.addAction(restore_action)

        menu.exec(lst.mapToGlobal(pos))

    def _toggle_complete(self, tid):
        TodoModel.toggle_complete(tid)
        self._refresh()

    def _on_checkbox_changed(self, tid, item, state):
        checked = state == Qt.CheckState.Checked.value
        TodoModel.toggle_complete(tid)
        self._refresh()

    def _delete_todo(self, tid):
        TodoModel.delete(tid)
        self._refresh()

    def _restore_deleted(self):
        deleted = TodoModel.get_all(include_deleted=True)
        deleted = [t for t in deleted if t["is_deleted"] == 1]
        if not deleted:
            return
        for t in deleted:
            TodoModel.restore(t["id"])
        self._refresh()

    def _show_done(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QMessageBox
        
        dones = TodoModel.get_all()
        dones = [t for t in dones if t["is_completed"] == 1]
        
        dialog = QDialog(self)
        dialog.setWindowTitle("已办理")
        dialog.resize(400, 300)
        dialog.setStyleSheet(f"background: {MOCHA['base']};")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        
        title_label = QLabel(f"<font color='{MOCHA['text']}'>已完成的待办 ({len(dones)})</font>")
        layout.addWidget(title_label)
        
        self.done_list = QListWidget()
        self.done_list.setStyleSheet(f"""
            QListWidget {{ background: {MOCHA['surface0']}; border: none; border-radius: 6px; }}
            QListWidget::item {{ padding: 8px; color: {MOCHA['subtext']}; text-decoration: line-through; }}
        """)
        
        for t in dones:
            item = QListWidgetItem(t["content"])
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self.done_list.addItem(item)
        
        layout.addWidget(self.done_list)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        restore_btn = QPushButton("恢复选中")
        restore_btn.clicked.connect(self._restore_selected_from_done)
        restore_btn.setStyleSheet(f"""
            QPushButton {{ background: {MOCHA['blue']}; color: {MOCHA['base']}; border: none; padding: 6px 16px; border-radius: 4px; }}
            QPushButton:hover {{ background: #74c7ec; }}
        """)
        btn_layout.addWidget(restore_btn)
        
        clear_btn = QPushButton("清空已办理")
        clear_btn.clicked.connect(self._clear_done)
        clear_btn.setStyleSheet(f"""
            QPushButton {{ background: {MOCHA['green']}; color: {MOCHA['base']}; border: none; padding: 6px 16px; border-radius: 4px; }}
            QPushButton:hover {{ background: #94e2d5; }}
        """)
        btn_layout.addWidget(clear_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: {MOCHA['surface1']}; color: {MOCHA['text']}; border: none; padding: 6px 16px; border-radius: 4px; }}
            QPushButton:hover {{ background: {MOCHA['surface2']}; }}
        """)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        dialog.exec()

    def _restore_selected_from_done(self):
        selected = self.done_list.selectedItems()
        if not selected:
            return
        for item in selected:
            tid = item.data(Qt.ItemDataRole.UserRole)
            TodoModel.toggle_complete(tid)
            row = self.done_list.row(item)
            self.done_list.takeItem(row)
        self._refresh()

    def _clear_done(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有已完成的待办吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            dones = TodoModel.get_all()
            dones = [t for t in dones if t["is_completed"] == 1]
            for t in dones:
                TodoModel.delete(t["id"])
            self._refresh()
            self.done_list.clear()

    def _show_trash(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QMessageBox
        
        deleted = TodoModel.get_all(include_deleted=True)
        deleted = [t for t in deleted if t["is_deleted"] == 1]
        
        dialog = QDialog(self)
        dialog.setWindowTitle("回收站")
        dialog.resize(400, 300)
        dialog.setStyleSheet(f"background: {MOCHA['base']};")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        
        title_label = QLabel(f"<font color='{MOCHA['text']}'>已删除的待办 ({len(deleted)})</font>")
        layout.addWidget(title_label)
        
        self.trash_list = QListWidget()
        self.trash_list.setStyleSheet(f"""
            QListWidget {{ background: {MOCHA['surface0']}; border: none; border-radius: 6px; }}
            QListWidget::item {{ padding: 8px; color: {MOCHA['text']}; }}
        """)
        
        for t in deleted:
            item = QListWidgetItem(t["content"])
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self.trash_list.addItem(item)
        
        layout.addWidget(self.trash_list)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        restore_btn = QPushButton("恢复选中")
        restore_btn.clicked.connect(self._restore_selected_from_trash)
        restore_btn.setStyleSheet(f"""
            QPushButton {{ background: {MOCHA['blue']}; color: {MOCHA['base']}; border: none; padding: 6px 16px; border-radius: 4px; }}
            QPushButton:hover {{ background: #74c7ec; }}
        """)
        btn_layout.addWidget(restore_btn)
        
        delete_all_btn = QPushButton("清空回收站")
        delete_all_btn.clicked.connect(self._clear_trash)
        delete_all_btn.setStyleSheet(f"""
            QPushButton {{ background: {MOCHA['red']}; color: white; border: none; padding: 6px 16px; border-radius: 4px; }}
            QPushButton:hover {{ background: #eba0ac; }}
        """)
        btn_layout.addWidget(delete_all_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: {MOCHA['surface1']}; color: {MOCHA['text']}; border: none; padding: 6px 16px; border-radius: 4px; }}
            QPushButton:hover {{ background: {MOCHA['surface2']}; }}
        """)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        dialog.exec()

    def _restore_selected_from_trash(self):
        selected = self.trash_list.selectedItems()
        if not selected:
            return
        for item in selected:
            tid = item.data(Qt.ItemDataRole.UserRole)
            TodoModel.restore(tid)
            row = self.trash_list.row(item)
            self.trash_list.takeItem(row)
        self._refresh()

    def _clear_trash(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认清空", "确定要永久删除所有已删除的待办吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            deleted = TodoModel.get_all(include_deleted=True)
            deleted = [t for t in deleted if t["is_deleted"] == 1]
            for t in deleted:
                db.execute("DELETE FROM todos WHERE id=?", [t["id"]])
            self._refresh()
            self.trash_list.clear()

    def _setup_content_edit_keys(self, edit):
        """在 QTextEdit 中，Enter 提交对话框，Ctrl+Enter 手动换行"""
        edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QTextEdit
        if isinstance(obj, QTextEdit) and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                obj.insertPlainText("\n")
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() == Qt.KeyboardModifier.NoModifier:
                dlg = obj.window()
                from PyQt6.QtWidgets import QDialog
                if isinstance(dlg, QDialog):
                    dlg.accept()
                return True
        return super().eventFilter(obj, event)

    def _add_todo_to_quadrant(self, quadrant):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QComboBox, QPushButton
        dialog = QDialog(self)
        dialog.setWindowTitle("添加待办")
        dialog.resize(400, 180)
        dialog.setStyleSheet(f"background: {MOCHA['base']};")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(QLabel(f"<font color='{MOCHA['text']}'>待办内容 (Ctrl+Enter 换行):</font>"))
        content_edit = QTextEdit()
        content_edit.setPlaceholderText("输入待办内容…")
        content_edit.setFixedHeight(80)
        content_edit.setAcceptRichText(False)
        content_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._setup_content_edit_keys(content_edit)
        layout.addWidget(content_edit)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel(f"<font color='{MOCHA['text']}'>分类:</font>"))
        cat_combo = QComboBox()
        cat_combo.addItem("无分类", 0)
        for c in CategoryModel.get_all():
            cat_combo.addItem(c["name"], c["id"])
        row2.addWidget(cat_combo)
        layout.addLayout(row2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        if dialog.exec():
            content = content_edit.toPlainText().strip()
            cat_id = cat_combo.currentData() or 1
            if content:
                TodoModel.add(content, quadrant=quadrant, category_id=cat_id)
                self._refresh()

    def _edit_todo(self, tid, old_content):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QComboBox, QPushButton
        
        current_todo = TodoModel.get_by_id(tid)
        current_cat_id = current_todo["category_id"] if current_todo else 1

        dialog = QDialog(self)
        dialog.setWindowTitle("编辑待办")
        dialog.resize(400, 180)
        dialog.setStyleSheet(f"background: {MOCHA['base']};")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(QLabel(f"<font color='{MOCHA['text']}'>待办内容 (Ctrl+Enter 换行):</font>"))
        content_edit = QTextEdit(old_content)
        content_edit.setFixedHeight(80)
        content_edit.setAcceptRichText(False)
        content_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._setup_content_edit_keys(content_edit)
        layout.addWidget(content_edit)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel(f"<font color='{MOCHA['text']}'>分类:</font>"))
        cat_combo = QComboBox()
        cat_combo.addItem("无分类", 0)
        for c in CategoryModel.get_all():
            cat_combo.addItem(c["name"], c["id"])
        cat_combo.setCurrentIndex(cat_combo.findData(current_cat_id))
        row2.addWidget(cat_combo)
        layout.addLayout(row2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        if dialog.exec():
            content = content_edit.toPlainText().strip()
            cat_id = cat_combo.currentData() or 1
            if content:
                TodoModel.update(tid, content=content, category_id=cat_id)
                self._refresh()
