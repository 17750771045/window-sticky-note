"""便签组件 — 支持文本/图片/音频/视频/文档多种类型"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QListWidget, QListWidgetItem, QFileDialog,
    QLabel, QMenu, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QAction

from model.models import NoteModel
from model.models import CategoryModel

NOTE_TYPES = ["text", "image", "audio", "video", "doc"]
TYPE_ICONS = {"text": "📝", "image": "🖼️", "audio": "🎵", "video": "🎬", "doc": "📄"}
FILE_FILTERS = {
    "image": "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)",
    "audio": "音频文件 (*.mp3 *.wav *.ogg *.flac *.aac)",
    "video": "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv)",
    "doc": "文档文件 (*.pdf *.doc *.docx *.xls *.xlsx *.txt)",
}


class NoteWidget(QWidget):
    note_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        from ui.style import STYLE
        self.setStyleSheet(STYLE)

        self._current_note_id = None
        self._current_type = "text"
        self._current_file = ""
        self._dirty = False
        self._type_buttons = {}

        self._setup_ui()
        self._setup_auto_save()
        self._load_notes()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # --- 工具栏 ---
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        for nt in NOTE_TYPES:
            btn = QPushButton(f"{TYPE_ICONS[nt]} {nt}")
            btn.setFont(QFont("Microsoft YaHei", 10))
            btn.setFixedHeight(30)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=nt: self._on_type_changed(t))
            btn.setStyleSheet(
                "QPushButton { color: #a6adc8; }"
                "QPushButton:checked { background: #313244; color: #89b4fa; }"
            )
            self._type_buttons[nt] = btn
            toolbar.addWidget(btn)

        self._type_buttons["text"].setChecked(True)
        toolbar.addStretch()

        self._category_combo = QComboBox()
        self._category_combo.setFixedWidth(120)
        self._category_combo.setFont(QFont("Microsoft YaHei", 10))
        self._category_combo.currentIndexChanged.connect(self._on_category_changed)
        toolbar.addWidget(QLabel("分类:"))
        toolbar.addWidget(self._category_combo)

        layout.addLayout(toolbar)

        # 加载分类
        self._refresh_categories()

        # --- 编辑器区 ---
        editor_frame = QFrame()
        editor_frame.setStyleSheet("QFrame { background: #313244; border-radius: 6px; }")
        editor_layout = QVBoxLayout(editor_frame)
        editor_layout.setContentsMargins(8, 8, 8, 8)
        editor_layout.setSpacing(6)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("标题（可选）")
        self._title_edit.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self._title_edit.textChanged.connect(self._mark_dirty)
        editor_layout.addWidget(self._title_edit)

        self._editor_stack = QWidget()
        self._editor_stack.setLayout(QVBoxLayout())
        self._editor_stack.layout().setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self._editor_stack)

        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("输入便签内容...")
        self._text_edit.setFont(QFont("Microsoft YaHei", 10))
        self._text_edit.textChanged.connect(self._on_text_changed)
        self._editor_stack.layout().addWidget(self._text_edit)

        self._file_label = QLabel("未选择文件")
        self._file_label.setFont(QFont("Microsoft YaHei", 10))
        self._file_label.setStyleSheet("color: #a6adc8; padding: 12px;")
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_label.hide()
        self._editor_stack.layout().addWidget(self._file_label)

        self._browse_btn = QPushButton("📎 选择文件")
        self._browse_btn.setFont(QFont("Microsoft YaHei", 10))
        self._browse_btn.setFixedHeight(30)
        self._browse_btn.clicked.connect(self._on_browse_file)
        self._browse_btn.hide()
        self._editor_stack.layout().addWidget(self._browse_btn)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)
        
        self._new_btn = QPushButton("✏️ 新建便签")
        self._new_btn.setFont(QFont("Microsoft YaHei", 10))
        self._new_btn.setFixedHeight(32)
        self._new_btn.clicked.connect(self._on_new_note)
        btn_layout.addWidget(self._new_btn)
        
        self._save_btn = QPushButton("💾 保存便签")
        self._save_btn.setFont(QFont("Microsoft YaHei", 10))
        self._save_btn.setFixedHeight(32)
        self._save_btn.clicked.connect(self._on_save_note)
        btn_layout.addWidget(self._save_btn)
        
        editor_layout.addLayout(btn_layout)

        layout.addWidget(editor_frame, stretch=1)

        # --- 搜索栏 ---
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍 搜索便签...")
        self._search_edit.setFont(QFont("Microsoft YaHei", 10))
        self._search_edit.textChanged.connect(self._on_search)
        layout.addWidget(self._search_edit)

        # --- 便签列表 ---
        self._note_list = QListWidget()
        self._note_list.setFont(QFont("Microsoft YaHei", 10))
        self._note_list.setStyleSheet(
            "QListWidget { background: #1e1e2e; border: 1px solid #45475a; }"
            "QListWidget::item { padding: 8px; }"
            "QListWidget::item:hover { background: #313244; }"
            "QListWidget::item:selected { background: #45475a; }"
        )
        self._note_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._note_list.customContextMenuRequested.connect(self._on_context_menu)
        self._note_list.itemClicked.connect(self._on_note_selected)
        layout.addWidget(self._note_list, stretch=2)

    # ========== 分类 ==========

    def _refresh_categories(self):
        self._category_combo.blockSignals(True)
        self._category_combo.clear()
        self._category_combo.addItem("全部分类", 0)
        for cat in CategoryModel.get_all():
            self._category_combo.addItem(cat["name"], cat["id"])
        self._category_combo.blockSignals(False)

    def _on_category_changed(self):
        self._load_notes()

    # ========== 类型切换 ==========

    def _on_type_changed(self, nt):
        for t, btn in self._type_buttons.items():
            btn.setChecked(t == nt)
        self._current_type = nt
        self._reset_editor()

    def _reset_editor(self):
        if self._current_type == "text":
            self._text_edit.show()
            self._file_label.hide()
            self._browse_btn.hide()
            self._text_edit.clear()
            self._text_edit.setReadOnly(False)
        else:
            self._text_edit.hide()
            self._file_label.show()
            self._browse_btn.show()
            self._file_label.setText("未选择文件")
        self._current_file = ""
        self._current_note_id = None
        self._title_edit.clear()
        self._dirty = False

    # ========== 新建便签 ==========

    def _on_new_note(self):
        self._reset_editor()

    # ========== 文件选择 ==========

    def _on_browse_file(self):
        ffilter = FILE_FILTERS.get(self._current_type, "所有文件 (*)")
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", ffilter)
        if file_path:
            self._current_file = file_path
            import os
            self._file_label.setText(f"📎 {os.path.basename(file_path)}")
            self._file_label.setToolTip(file_path)
            self._dirty = True

    # ========== 保存 ==========

    def _on_text_changed(self):
        self._dirty = True

    def _mark_dirty(self):
        self._dirty = True

    def _setup_auto_save(self):
        self._auto_save_timer = QTimer()
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._auto_save_timer.start(3000)

    def _auto_save(self):
        if not self._dirty:
            return
        if self._current_type != "text":
            return
        content = self._text_edit.toPlainText()
        title = self._title_edit.text().strip()
        if not content and not title and self._current_file:
            return
        self._do_save(title, content)

    def _on_save_note(self):
        title = self._title_edit.text().strip()
        content = self._text_edit.toPlainText() if self._current_type == "text" else ""
        self._do_save(title, content)

    def _do_save(self, title, content):
        cid = self._category_combo.currentData() or 1
        if self._current_note_id:
            NoteModel.update(
                self._current_note_id,
                title=title,
                content=content,
                note_type=self._current_type,
                file_path=self._current_file,
                category_id=cid,
            )
        else:
            auto_title = title or content[:20] or self._current_file or "未命名便签"
            self._current_note_id = NoteModel.add(
                title=auto_title,
                content=content,
                note_type=self._current_type,
                file_path=self._current_file,
                category_id=cid,
            )
        self._dirty = False
        self._load_notes()
        self.note_changed.emit()

    # ========== 列表与搜索 ==========

    def _load_notes(self):
        self._note_list.clear()
        cid = self._category_combo.currentData() or 1
        keyword = self._search_edit.text().strip().lower()
        notes = NoteModel.get_all(category_id=cid)

        for n in notes:
            if keyword:
                title = (n.get("title") or "").lower()
                content = (n.get("content") or "").lower()
                fpath = (n.get("file_path") or "").lower()
                if keyword not in title and keyword not in content and keyword not in fpath:
                    continue

            nt = n.get("note_type", "text")
            icon = TYPE_ICONS.get(nt, "📝")
            title = n.get("title") or n.get("content", "")[:30] or n.get("file_path", "") or "无标题"
            if len(title) > 40:
                title = title[:40] + "…"
            item = QListWidgetItem(f"{icon}  {title}")
            item.setData(Qt.ItemDataRole.UserRole, n["id"])
            item.setToolTip(
                f"类型: {nt}\n标题: {n.get('title', '')}\n"
                f"文件: {n.get('file_path', '')}\n更新: {n.get('updated_at', '')}"
            )
            self._note_list.addItem(item)

    def _on_search(self):
        self._load_notes()

    def _on_note_selected(self, item):
        nid = item.data(Qt.ItemDataRole.UserRole)
        note = NoteModel.get_by_id(nid)
        if not note:
            return
        self._current_note_id = note["id"]
        self._current_type = note.get("note_type", "text")
        self._current_file = note.get("file_path", "")
        self._title_edit.setText(note.get("title", ""))

        for t, btn in self._type_buttons.items():
            btn.setChecked(t == self._current_type)

        if self._current_type == "text":
            self._text_edit.show()
            self._file_label.hide()
            self._browse_btn.hide()
            self._text_edit.setReadOnly(False)
            self._text_edit.blockSignals(True)
            self._text_edit.setPlainText(note.get("content", ""))
            self._text_edit.blockSignals(False)
        else:
            self._text_edit.hide()
            self._file_label.show()
            self._browse_btn.show()
            if self._current_file:
                import os
                self._file_label.setText(f"📎 {os.path.basename(self._current_file)}")
                self._file_label.setToolTip(self._current_file)
            else:
                self._file_label.setText("未选择文件")
        self._dirty = False

    # ========== 右键菜单 ==========

    def _on_context_menu(self, pos):
        item = self._note_list.itemAt(pos)
        if not item:
            return
        nid = item.data(Qt.ItemDataRole.UserRole)
        note = NoteModel.get_by_id(nid)
        if not note:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #313244; color: #cdd6f4; border: 1px solid #45475a; }"
            "QMenu::item { padding: 6px 24px; }"
            "QMenu::item:selected { background: #45475a; }"
        )

        edit_action = QAction("✏️ 编辑", menu)
        edit_action.triggered.connect(lambda: self._on_edit_note(nid))
        menu.addAction(edit_action)

        if note.get("is_deleted"):
            restore_action = QAction("🔄 恢复", menu)
            restore_action.triggered.connect(lambda: self._on_restore_note(nid))
            menu.addAction(restore_action)
        else:
            delete_action = QAction("🗑️ 删除", menu)
            delete_action.triggered.connect(lambda: self._on_delete_note(nid))
            menu.addAction(delete_action)

        menu.exec(self._note_list.mapToGlobal(pos))

    def _on_edit_note(self, nid):
        note = NoteModel.get_by_id(nid)
        if not note or note.get("is_deleted"):
            return
        self._current_note_id = note["id"]
        self._current_type = note.get("note_type", "text")
        self._current_file = note.get("file_path", "")
        self._title_edit.setText(note.get("title", ""))

        for t, btn in self._type_buttons.items():
            btn.setChecked(t == self._current_type)

        if self._current_type == "text":
            self._text_edit.show()
            self._file_label.hide()
            self._browse_btn.hide()
            self._text_edit.setReadOnly(False)
            self._text_edit.blockSignals(True)
            self._text_edit.setPlainText(note.get("content", ""))
            self._text_edit.blockSignals(False)
        else:
            self._text_edit.hide()
            self._file_label.show()
            self._browse_btn.show()
            if self._current_file:
                import os
                self._file_label.setText(f"📎 {os.path.basename(self._current_file)}")
                self._file_label.setToolTip(self._current_file)
            else:
                self._file_label.setText("未选择文件")
        self._dirty = False

    def _on_delete_note(self, nid):
        NoteModel.delete(nid)
        if self._current_note_id == nid:
            self._reset_editor()
        self._load_notes()
        self.note_changed.emit()

    def _on_restore_note(self, nid):
        NoteModel.restore(nid)
        self._load_notes()
        self.note_changed.emit()
