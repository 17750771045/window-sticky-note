"""主窗口 — MVVM架构，无边框窗口 + 手动缩放 + 侧边栏折叠 + 置顶 + 开机自启"""

import os
import sys
import json
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QApplication, QSizePolicy,
    QSystemTrayIcon, QMenu,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QMouseEvent, QCursor, QIcon

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(__file__))

CONFIG_PATH = os.path.join(get_app_dir(), "window_config.json")

from ui.style import STYLE
from ui.note_widget import NoteWidget
from ui.todo_widget import TodoWidget
from ui.reminder_widget import ReminderWidget
from ui.calendar_widget import CalendarWidget
from ui.timeline_widget import TimelineWidget
from ui.category_widget import CategoryWidget
from ui.quick_tools_widget import QuickToolsBar

# 开机自启快捷方式路径
STARTUP_DIR = os.path.join(
    os.environ.get("APPDATA", ""),
    r"Microsoft\Windows\Start Menu\Programs\Startup",
)
STARTUP_LINK = os.path.join(STARTUP_DIR, "便利贴.lnk")

def save_window_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_window_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# ── 光标映射 ──
_CURSORS = {
    "tl": Qt.CursorShape.SizeFDiagCursor,
    "tr": Qt.CursorShape.SizeBDiagCursor,
    "bl": Qt.CursorShape.SizeBDiagCursor,
    "br": Qt.CursorShape.SizeFDiagCursor,
    "t": Qt.CursorShape.SizeVerCursor,
    "b": Qt.CursorShape.SizeVerCursor,
    "l": Qt.CursorShape.SizeHorCursor,
    "r": Qt.CursorShape.SizeHorCursor,
}


class TitleBar(QFrame):
    """自定义标题栏：拖拽移动、双击最大化、置顶/自启/折叠按钮"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet("background: #181825; border-bottom: 1px solid #313244;")
        self._parent = parent
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 4, 0)
        layout.setSpacing(6)

        # 折叠按钮
        self._fold_btn = QPushButton("☰")
        self._fold_btn.setToolTip("折叠/展开侧边栏")
        self._fold_btn.setFixedSize(32, 28)
        self._fold_btn.setStyleSheet(self._btn_style("#cdd6f4"))
        self._fold_btn.clicked.connect(self._toggle_sidebar)
        layout.addWidget(self._fold_btn)

        title = QLabel("便利贴")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #89b4fa; border: none;")
        layout.addWidget(title)
        layout.addStretch()

        # 置顶按钮
        self._pin_btn = QPushButton("📌")
        self._pin_btn.setToolTip("桌面置顶")
        self._pin_btn.setFixedSize(32, 28)
        self._pin_btn.setStyleSheet(self._btn_style("#cdd6f4"))
        self._pin_btn.clicked.connect(self._toggle_pin)
        layout.addWidget(self._pin_btn)
        
        # 开机自启按钮
        self._startup_btn = QPushButton("🚀")
        self._startup_btn.setToolTip("开机自启动")
        self._startup_btn.setFixedSize(32, 28)
        self._startup_btn.setStyleSheet(self._btn_style("#cdd6f4"))
        self._startup_btn.clicked.connect(self._toggle_startup)
        self._update_startup_style()
        layout.addWidget(self._startup_btn)
        
        # 延迟更新置顶按钮状态（等待窗口标志设置完成）
        QTimer.singleShot(0, self._update_pin_style)

        layout.addSpacing(6)

        for icon, slot, tip in [
            ("─", self._on_minimize, "最小化"),
            ("□", self._on_maximize, "最大化"),
            ("✕", self._on_close, "关闭"),
        ]:
            btn = QPushButton(icon)
            btn.setToolTip(tip)
            btn.setFixedSize(32, 28)
            btn.setStyleSheet(self._btn_style("#f38ba8" if icon == "✕" else "#cdd6f4"))
            btn.clicked.connect(slot)
            layout.addWidget(btn)

    def _btn_style(self, color):
        return (
            f"QPushButton {{ color: {color}; background: transparent; border: none; "
            f"font-size: 14px; padding: 0; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: #313244; }}"
        )

    def _update_pin_style(self):
        """根据当前窗口标志更新置顶按钮样式"""
        if self._parent.windowFlags() & Qt.WindowType.WindowStaysOnTopHint:
            self._pin_btn.setStyleSheet(self._btn_style("#89b4fa"))
        else:
            self._pin_btn.setStyleSheet(self._btn_style("#cdd6f4"))

    def _toggle_sidebar(self):
        self._parent._toggle_sidebar()

    def _toggle_pin(self):
        flags = self._parent.windowFlags()
        if flags & Qt.WindowType.WindowStaysOnTopHint:
            self._parent.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
            self._pin_btn.setStyleSheet(self._btn_style("#cdd6f4"))
            self._show_toast("已关闭桌面置顶")
        else:
            self._parent.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
            self._pin_btn.setStyleSheet(self._btn_style("#89b4fa"))
            self._show_toast("已开启桌面置顶\n窗口将始终显示在最前面")
        self._parent.show()

    def _toggle_startup(self):
        if os.path.exists(STARTUP_LINK):
            os.remove(STARTUP_LINK)
            self._show_toast("已关闭开机自启动")
        else:
            self._create_shortcut()
            self._show_toast("已开启开机自启动\n下次开机将自动运行便利贴")
        self._update_startup_style()

    def _update_startup_style(self):
        if os.path.exists(STARTUP_LINK):
            self._startup_btn.setStyleSheet(self._btn_style("#89b4fa"))
            self._startup_btn.setToolTip("开机自启动 (已开启)")
        else:
            self._startup_btn.setStyleSheet(self._btn_style("#cdd6f4"))
            self._startup_btn.setToolTip("开机自启动 (已关闭)")

    def _create_shortcut(self):
        try:
            import pythoncom
            from win32com.client import Dispatch
            pythoncom.CoInitialize()
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(STARTUP_LINK)
            shortcut.TargetPath = sys.executable
            shortcut.Arguments = f'"{os.path.abspath(sys.argv[0])}"'
            shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(sys.argv[0]))
            shortcut.Description = "便利贴"
            shortcut.Save()
        except ImportError:
            bat_path = STARTUP_LINK.replace(".lnk", ".bat")
            with open(bat_path, "w") as f:
                f.write(f'@echo off\nstart "" "{sys.executable}" "{os.path.abspath(sys.argv[0])}"')

    def _show_toast(self, message):
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self._parent)
        msg.setWindowTitle("提示")
        msg.setText(message)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.show()

    def _on_minimize(self):
        self._parent.showMinimized()

    def _on_maximize(self):
        if self._parent.isMaximized():
            self._parent.showNormal()
        else:
            self._parent.showMaximized()

    def _on_close(self):
        self._parent.close()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self._parent.move(self._parent.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self._on_maximize()
        super().mouseDoubleClickEvent(event)


# =================================================================
#  MainWindow — 边缘缩放通过 6px 裸窗口边距实现
# =================================================================
class MainWindow(QMainWindow):
    BORDER = 8
    SIDEBAR_WIDTH = 200

    def __init__(self):
        super().__init__()
        self.setWindowTitle("便利贴 - 随手记 · 高效管理")
        self.setWindowIcon(QIcon(os.path.join(get_app_dir(), "zhang.jpg")))
        self.setMinimumSize(200, 200)
        
        # 先加载配置，确定是否需要置顶
        config = load_window_config()
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowMinimizeButtonHint
        if config.get("stays_on_top", False):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        
        self._nav_buttons = []
        self._sidebar_collapsed = False
        self._resize_edge = None
        self._resize_pos = None
        self._opacity = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._setup_ui()
        self._setup_tray()
        self._start_reminder_checker()
        self._load_window_state(config)

    def _setup_tray(self):
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(QIcon(os.path.join(get_app_dir(), "zhang.jpg")))
        self._tray_icon.setToolTip("便利贴")

        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示")
        show_action.triggered.connect(self._show_from_tray)
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self._really_quit)
        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

        self._closing = False

    def _show_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _really_quit(self):
        self._closing = True
        self.close()

    def _load_window_state(self, config=None):
        if config is None:
            config = load_window_config()
        
        if "geometry" in config:
            geo = config["geometry"]
            if all(k in geo for k in ["x", "y", "width", "height"]):
                self.setGeometry(geo["x"], geo["y"], geo["width"], geo["height"])
        else:
            self.resize(1200, 800)
        
        if "maximized" in config and config["maximized"]:
            self.showMaximized()
        
        if "sidebar_collapsed" in config:
            self._sidebar_collapsed = config["sidebar_collapsed"]
            if self._sidebar_collapsed:
                self._toggle_sidebar()
        
        if "current_page" in config:
            page = config["current_page"]
            if 0 <= page < self.stack.count():
                self._switch_page(page)

    def closeEvent(self, event):
        geo = self.geometry()
        config = {
            "geometry": {
                "x": geo.x(),
                "y": geo.y(),
                "width": geo.width(),
                "height": geo.height(),
            },
            "maximized": self.isMaximized(),
            "sidebar_collapsed": self._sidebar_collapsed,
            "current_page": self.stack.currentIndex(),
            "stays_on_top": bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint),
        }
        save_window_config(config)
        if self._closing:
            super().closeEvent(event)
        else:
            event.ignore()
            self.hide()

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self._central = central
        self._apply_opacity_bg()
        self.setCentralWidget(central)

        # 6px 边距 = 裸窗口边缘，主窗口 mouse 事件可捕获
        root = QVBoxLayout(central)
        root.setContentsMargins(self.BORDER, self.BORDER, self.BORDER, self.BORDER)
        root.setSpacing(0)

        self._title_bar = TitleBar(self)
        root.addWidget(self._title_bar)

        body = QWidget()
        self._body_layout = QHBoxLayout(body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)

        self._sidebar = self._build_sidebar()
        self._body_layout.addWidget(self._sidebar)

        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.stack.addWidget(NoteWidget())
        self.stack.addWidget(TodoWidget())
        self.stack.addWidget(ReminderWidget())
        self.stack.addWidget(CalendarWidget())
        self.stack.addWidget(TimelineWidget())
        self.stack.addWidget(CategoryWidget())

        self._body_layout.addWidget(self.stack, 1)
        root.addWidget(body, 1)

        self._switch_page(0)

        # 确保所有容器背景应用透明度
        self._apply_opacity_bg()

    # ── 透明度 ──

    def set_opacity(self, value):
        """设置背景透明度 (0.1~1.0)，文本保持不透明"""
        self._opacity = value / 100.0
        self._apply_opacity_bg()

    def _apply_opacity_bg(self):
        a = self._opacity
        # 主背景 rgba
        self._central.setStyleSheet(f"background: rgba(30, 30, 46, {a:.2f});")
        # 侧边栏 & 标题栏 rgba
        if hasattr(self, '_sidebar'):
            self._sidebar.setStyleSheet(
                f"background: rgba(24, 24, 37, {a:.2f});"
                f"border-right: 1px solid rgba(49, 50, 68, {a:.2f});"
            )
        if hasattr(self, '_title_bar'):
            self._title_bar.setStyleSheet(
                f"background: rgba(24, 24, 37, {a:.2f});"
                f"border-bottom: 1px solid rgba(49, 50, 68, {a:.2f});"
            )

    # ── 侧边栏 ──

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(self.SIDEBAR_WIDTH)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(4)

        nav_items = [
            ("📝 便签", 0),
            ("✅ 待办清单", 1),
            ("⏰ 提醒系统", 2),
            ("📅 日历视图", 3),
            ("🕐 时间轴", 4),
            ("📂 分类管理", 5),
        ]

        self._nav_texts = []
        for text, idx in nav_items:
            btn = QPushButton(text)
            btn.setFont(QFont("Microsoft YaHei", 11))
            btn.setFixedHeight(36)
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding-left: 16px; color: #a6adc8; }"
                "QPushButton:hover { background: #313244; color: #cdd6f4; }"
            )
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)
            self._nav_texts.append(text)

        sidebar_layout.addStretch()

        self.quick_tools = QuickToolsBar()
        self.quick_tools.tool_clicked.connect(self._on_quick_tool)
        sidebar_layout.addWidget(self.quick_tools)

        return sidebar

    def _toggle_sidebar(self):
        self._sidebar_collapsed = not self._sidebar_collapsed
        if self._sidebar_collapsed:
            self._sidebar.setFixedWidth(0)
            self._sidebar.setVisible(False)
            for btn in self._nav_buttons:
                btn.setVisible(False)
            self.quick_tools.setVisible(False)
        else:
            self._sidebar.setVisible(True)
            self._sidebar.setFixedWidth(self.SIDEBAR_WIDTH)
            for btn in self._nav_buttons:
                btn.setVisible(True)
            self.quick_tools.setVisible(True)

    # ══════════ 窗口缩放 ══════════

    def _edge_at(self, pos):
        x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        b = self.BORDER
        left = x < b
        right = x > w - b
        top = y < b
        bottom = y > h - b
        if top and left:
            return "tl"
        if top and right:
            return "tr"
        if bottom and left:
            return "bl"
        if bottom and right:
            return "br"
        if top:
            return "t"
        if bottom:
            return "b"
        if left:
            return "l"
        if right:
            return "r"
        return None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._edge_at(event.pos())
            if edge:
                self._resize_edge = edge
                self._resize_pos = event.globalPosition().toPoint()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._resize_edge and self._resize_pos is not None:
            self._perform_resize(event)
            return
        self.setCursor(_CURSORS.get(self._edge_at(event.pos()), Qt.CursorShape.ArrowCursor))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._resize_edge = None
        self._resize_pos = None
        super().mouseReleaseEvent(event)

    def _perform_resize(self, event: QMouseEvent):
        delta = event.globalPosition().toPoint() - self._resize_pos
        geo = self.geometry()
        edge = self._resize_edge

        if "l" in edge:
            new_x = geo.x() + delta.x()
            new_w = geo.width() - delta.x()
            if new_w >= self.minimumWidth():
                geo.setX(new_x)
                geo.setWidth(new_w)
                self._resize_pos.setX(event.globalPosition().toPoint().x())
        if "r" in edge:
            new_w = geo.width() + delta.x()
            if new_w >= self.minimumWidth():
                geo.setWidth(new_w)
                self._resize_pos.setX(event.globalPosition().toPoint().x())
        if "t" in edge:
            new_y = geo.y() + delta.y()
            new_h = geo.height() - delta.y()
            if new_h >= self.minimumHeight():
                geo.setY(new_y)
                geo.setHeight(new_h)
                self._resize_pos.setY(event.globalPosition().toPoint().y())
        if "b" in edge:
            new_h = geo.height() + delta.y()
            if new_h >= self.minimumHeight():
                geo.setHeight(new_h)
                self._resize_pos.setY(event.globalPosition().toPoint().y())

        self.setGeometry(geo)

    # ══════════ 页面切换 ══════════

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            if i == index:
                btn.setStyleSheet(
                    "QPushButton { text-align: left; padding-left: 16px; "
                    "background: #313244; color: #89b4fa; font-weight: bold; border-left: 3px solid #89b4fa; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { text-align: left; padding-left: 16px; "
                    "color: #a6adc8; } QPushButton:hover { background: #313244; color: #cdd6f4; }"
                )

    def _on_quick_tool(self, tool_type):
        from PyQt6.QtWidgets import QDialog
        dialog = QDialog(self)
        dialog.setWindowTitle("快捷工具")
        dialog.resize(400, 500)
        dialog.setStyleSheet(STYLE)

        layout = QVBoxLayout(dialog)
        if tool_type == "calculator":
            from tools.calculator import CalculatorWidget
            layout.addWidget(CalculatorWidget())
        elif tool_type == "ledger":
            from tools.ledger import LedgerWidget
            layout.addWidget(LedgerWidget())
        elif tool_type == "translator":
            from tools.translator import TranslatorWidget
            layout.addWidget(TranslatorWidget())

        dialog.exec()

    # ── 提醒 ──

    def _start_reminder_checker(self):
        self._reminder_timer = QTimer()
        self._reminder_timer.timeout.connect(self._check_reminders)
        self._reminder_timer.start(30000)
        self._check_reminders()

    def _check_reminders(self):
        from model.models import ReminderModel
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        reminders = ReminderModel.get_upcoming(50)
        for r in reminders:
            if r["remind_time"] <= now and not r["is_triggered"]:
                self._show_reminder_popup(r)
                ReminderModel.update(r["id"], is_triggered=1)

    def _show_reminder_popup(self, reminder):
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("⏰ 提醒")
        msg.setText(f"<b>{reminder['title']}</b>")
        if reminder["content"]:
            msg.setInformativeText(reminder["content"])
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.show()