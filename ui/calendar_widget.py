"""日历视图组件 — 月视图/轴视图/四象限视图/甘特图"""

from datetime import datetime, date, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QTabWidget, QCalendarWidget, QListWidget, QListWidgetItem,
    QCheckBox, QSlider, QLabel, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPalette, QTextCharFormat,
)

from model.models import TodoModel, ReminderModel

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
    "peach": "#fab387",
    "maroon": "#eba0ac",
}

QUADRANT_COLORS = {1: MOCHA["red"], 2: MOCHA["blue"], 3: MOCHA["yellow"], 4: MOCHA["green"]}
QUADRANT_LABELS = {1: "Q1: 紧急重要", 2: "Q2: 重要不紧急", 3: "Q3: 紧急不重要", 4: "Q4: 不紧急不重要"}

REPEAT_LABELS = {
    "none": "不重复", "daily": "每天", "weekly": "每周",
    "monthly": "每月", "quarterly": "每季度", "yearly": "每年",
}

CALENDAR_STYLE = f"""
QCalendarWidget {{
    background: {MOCHA['base']};
    color: {MOCHA['text']};
    border: 1px solid {MOCHA['surface1']};
    border-radius: 8px;
}}
QCalendarWidget QToolButton {{
    color: {MOCHA['text']};
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px 10px;
    font-weight: bold;
    font-size: 13px;
}}
QCalendarWidget QToolButton:hover {{
    background: {MOCHA['surface0']};
}}
QCalendarWidget QToolButton::menu-indicator {{
    image: none;
}}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background: {MOCHA['surface0']};
    border-radius: 8px 8px 0 0;
}}
QCalendarWidget QWidget#qt_calendar_prevmonth,
QCalendarWidget QWidget#qt_calendar_nextmonth {{
    qproperty-text: "";
}}
QCalendarWidget QTableView {{
    background: {MOCHA['base']};
    border: none;
    outline: none;
    gridline-color: {MOCHA['surface0']};
}}
QCalendarWidget QTableView::item {{
    padding: 6px;
    color: {MOCHA['text']};
    border-radius: 4px;
}}
QCalendarWidget QTableView::item:hover {{
    background: {MOCHA['surface0']};
}}
QCalendarWidget QTableView::item:selected {{
    background: {MOCHA['blue']};
    color: {MOCHA['base']};
}}
QCalendarWidget QAbstractItemView:enabled {{
    font-size: 13px;
}}
"""

LIST_STYLE = f"""
QListWidget {{
    background: {MOCHA['surface0']};
    border: none;
    border-radius: 6px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 6px 8px;
    border-bottom: 1px solid {MOCHA['base']};
    color: {MOCHA['text']};
}}
QListWidget::item:hover {{
    background: {MOCHA['surface1']};
}}
"""

TAB_STYLE = f"""
QTabWidget::pane {{
    border: 1px solid {MOCHA['surface1']};
    background: {MOCHA['base']};
    border-radius: 8px;
}}
QTabBar::tab {{
    background: {MOCHA['surface0']};
    color: {MOCHA['subtext']};
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    background: {MOCHA['base']};
    color: {MOCHA['text']};
    border-bottom: 2px solid {MOCHA['blue']};
}}
QTabBar::tab:hover:!selected {{
    background: {MOCHA['surface1']};
}}
"""


class _GanttCanvas(QWidget):
    """甘特图绘制画布"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._todos = []
        self.setMinimumHeight(200)

    def set_todos(self, todos):
        self._todos = todos
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, QColor(MOCHA["base"]))

        todos = [t for t in self._todos if t.get("due_date")]
        if not todos:
            painter.setPen(QColor(MOCHA["subtext"]))
            painter.setFont(QFont("Microsoft YaHei", 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "暂无含截止日期的待办")
            return

        row_h = 40
        top_margin = 20
        left_margin = 180
        right_margin = 40
        bar_area_w = w - left_margin - right_margin

        today = date.today()
        all_dates = []
        for t in todos:
            try:
                d = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
                all_dates.append(d)
            except Exception:
                pass
            try:
                c = t.get("created_at", "")
                if c:
                    d = datetime.strptime(c[:10], "%Y-%m-%d").date()
                    all_dates.append(d)
            except Exception:
                pass
        if not all_dates:
            return

        min_date = min(all_dates) - timedelta(days=1)
        max_date = max(all_dates) + timedelta(days=1)
        total_days = (max_date - min_date).days or 1

        def date_to_x(d):
            return left_margin + int((d - min_date).days / total_days * bar_area_w)

        # draw header with month labels
        painter.setPen(QPen(QColor(MOCHA["subtext"]), 1))
        painter.setFont(QFont("Microsoft YaHei", 8))
        cursor = min_date.replace(day=1)
        while cursor <= max_date:
            x = date_to_x(cursor)
            painter.drawLine(x, top_margin, x, h - 10)
            if cursor.day == 1:
                painter.drawText(x + 3, top_margin - 4, cursor.strftime("%Y-%m"))
            cursor = cursor.replace(day=1)
            try:
                cursor = cursor.replace(month=cursor.month + 1)
            except ValueError:
                cursor = cursor.replace(year=cursor.year + 1, month=1)

        # today line
        if min_date <= today <= max_date:
            tx = date_to_x(today)
            painter.setPen(QPen(QColor(MOCHA["pink"]), 1, Qt.PenStyle.DashLine))
            painter.drawLine(tx, top_margin, tx, h - 10)

        # draw bars
        for i, t in enumerate(todos):
            y = top_margin + 20 + i * row_h
            if y > h:
                break

            # label
            painter.setPen(QColor(MOCHA["text"]))
            painter.setFont(QFont("Microsoft YaHei", 9))
            content = t["content"]
            painter.drawText(8, y + 4, left_margin - 16, 16,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             content[:24])

            # bar
            quadrant = t.get("quadrant", 1)
            color = QColor(QUADRANT_COLORS.get(quadrant, MOCHA["blue"]))

            try:
                start_d = datetime.strptime(t.get("created_at", "")[:10], "%Y-%m-%d").date()
            except Exception:
                start_d = min_date
            try:
                end_d = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
            except Exception:
                end_d = max_date

            bar_x = date_to_x(start_d)
            bar_end = date_to_x(end_d)
            bar_w = max(bar_end - bar_x, 6)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color.darker(160)))
            painter.drawRoundedRect(int(bar_x), int(y), int(bar_w), 20, 4, 4)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(int(bar_x + 1), int(y + 1), int(bar_w - 2), 18, 4, 4)

            # due date label
            painter.setPen(QColor(MOCHA["subtext"]))
            painter.setFont(QFont("Microsoft YaHei", 7))
            painter.drawText(int(bar_end + 4), int(y + 2), right_margin, 16,
                             Qt.AlignmentFlag.AlignLeft, end_d.strftime("%m-%d"))


class _TimelineItem(QFrame):
    """轴视图单条时间线项"""

    def __init__(self, remind_time, title, repeat_type, is_important, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            _TimelineItem {{
                background: {MOCHA['surface0']};
                border-radius: 8px;
                border-left: 3px solid {MOCHA['blue']};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        time_lbl = QLabel(remind_time)
        time_lbl.setStyleSheet(f"color: {MOCHA['teal']}; font-size: 12px; font-weight: bold;")
        time_lbl.setFixedWidth(140)
        layout.addWidget(time_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {MOCHA['text']}; font-size: 13px;")
        layout.addWidget(title_lbl, 1)

        repeat_lbl = QLabel(REPEAT_LABELS.get(repeat_type, "不重复"))
        repeat_lbl.setStyleSheet(f"color: {MOCHA['subtext']}; font-size: 11px;")
        repeat_lbl.setFixedWidth(60)
        layout.addWidget(repeat_lbl)


class _QuadrantCard(QFrame):
    """四象限视图卡片"""

    def __init__(self, title, color, quadrant, parent=None):
        super().__init__(parent)
        self._quadrant = quadrant
        self.setStyleSheet(f"""
            _QuadrantCard {{
                background: {MOCHA['surface0']};
                border: 2px solid {color};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)

        header = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold;")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        self.count_label = QLabel("0 项")
        self.count_label.setStyleSheet(f"color: {MOCHA['text']}; font-size: 32px; font-weight: bold;")
        layout.addWidget(self.count_label, 1, Qt.AlignmentFlag.AlignCenter)

    def set_count(self, n):
        self.count_label.setText(f"{n} 项")


class CalendarWidget(QWidget):
    """日历视图组件"""

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._refresh()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)

        self.tabs.addTab(self._create_month_tab(), "月视图")
        self.tabs.addTab(self._create_timeline_tab(), "轴视图")
        self.tabs.addTab(self._create_quadrant_tab(), "四象限视图")
        self.tabs.addTab(self._create_gantt_tab(), "甘特图")

        layout.addWidget(self.tabs, 1)

        # bottom controls
        controls = QHBoxLayout()
        controls.setContentsMargins(4, 4, 4, 4)
        controls.setSpacing(12)

        self.desktop_check = QCheckBox("嵌入桌面")
        self.desktop_check.setStyleSheet(f"color: {MOCHA['text']}; font-size: 13px;")
        self.desktop_check.toggled.connect(self._toggle_desktop_embed)
        controls.addWidget(self.desktop_check)

        controls.addSpacing(16)

        opacity_label = QLabel("透明度:")
        opacity_label.setStyleSheet(f"color: {MOCHA['subtext']}; font-size: 12px;")
        controls.addWidget(opacity_label)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedWidth(150)
        self.opacity_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {MOCHA['surface1']};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {MOCHA['blue']};
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: {MOCHA['blue']};
                border-radius: 2px;
            }}
        """)
        self.opacity_slider.valueChanged.connect(self._set_opacity)
        controls.addWidget(self.opacity_slider)

        opacity_val = QLabel("100%")
        opacity_val.setStyleSheet(f"color: {MOCHA['subtext']}; font-size: 12px;")
        self.opacity_slider.valueChanged.connect(
            lambda v: opacity_val.setText(f"{v}%")
        )
        controls.addWidget(opacity_val)

        controls.addStretch()
        layout.addLayout(controls)

    # ------------------------------------------------------------------
    # Tab 1: 月视图
    # ------------------------------------------------------------------

    def _create_month_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setStyleSheet(CALENDAR_STYLE)
        self.calendar.selectionChanged.connect(self._on_date_selected)
        layout.addWidget(self.calendar)

        self.selected_date_label = QLabel()
        self.selected_date_label.setStyleSheet(
            f"color: {MOCHA['blue']}; font-size: 14px; font-weight: bold; padding: 4px 0;"
        )
        layout.addWidget(self.selected_date_label)

        self.month_list = QListWidget()
        self.month_list.setStyleSheet(LIST_STYLE)
        self.month_list.setMaximumHeight(200)
        layout.addWidget(self.month_list)

        return tab

    # ------------------------------------------------------------------
    # Tab 2: 轴视图
    # ------------------------------------------------------------------

    def _create_timeline_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {MOCHA['base']}; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {MOCHA['surface1']}; border-radius: 3px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {MOCHA['surface2']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self.timeline_container = QWidget()
        self.timeline_container.setStyleSheet(f"background: transparent;")
        self.timeline_layout = QVBoxLayout(self.timeline_container)
        self.timeline_layout.setContentsMargins(4, 4, 4, 4)
        self.timeline_layout.setSpacing(6)
        self.timeline_layout.addStretch()

        scroll.setWidget(self.timeline_container)
        layout.addWidget(scroll)

        return tab

    # ------------------------------------------------------------------
    # Tab 3: 四象限视图
    # ------------------------------------------------------------------

    def _create_quadrant_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        grid = QGridLayout()
        grid.setSpacing(12)

        self.quadrant_cards = {}
        quadrants = [
            ("Q1: 紧急且重要", MOCHA["red"], 1),
            ("Q2: 重要不紧急", MOCHA["blue"], 2),
            ("Q3: 紧急不重要", MOCHA["yellow"], 3),
            ("Q4: 不紧急不重要", MOCHA["green"], 4),
        ]
        for i, (title, color, q) in enumerate(quadrants):
            card = _QuadrantCard(title, color, q)
            self.quadrant_cards[q] = card
            grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid)

        return tab

    # ------------------------------------------------------------------
    # Tab 4: 甘特图
    # ------------------------------------------------------------------

    def _create_gantt_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        legend = QHBoxLayout()
        for q, color in QUADRANT_COLORS.items():
            dot = QLabel(" ● ")
            dot.setStyleSheet(f"color: {color}; font-size: 16px;")
            lbl = QLabel(QUADRANT_LABELS[q])
            lbl.setStyleSheet(f"color: {MOCHA['subtext']}; font-size: 11px;")
            legend.addWidget(dot)
            legend.addWidget(lbl)
            legend.addSpacing(8)
        legend.addStretch()
        layout.addLayout(legend)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: 1px solid {MOCHA['surface1']}; border-radius: 8px; }}
            QScrollBar:vertical {{
                background: {MOCHA['base']}; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {MOCHA['surface1']}; border-radius: 3px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {MOCHA['surface2']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self.gantt_canvas = _GanttCanvas()
        scroll.setWidget(self.gantt_canvas)
        layout.addWidget(scroll, 1)

        return tab

    # ------------------------------------------------------------------
    # refresh
    # ------------------------------------------------------------------

    def _refresh(self):
        self._refresh_month_view()
        self._refresh_timeline()
        self._refresh_quadrant()
        self._refresh_gantt()

    def _refresh_month_view(self):
        self._on_date_selected()

    def _on_date_selected(self):
        qdate = self.calendar.selectedDate()
        date_str = qdate.toString("yyyy-MM-dd")
        self.selected_date_label.setText(f"📅 {date_str}")

        self.month_list.clear()

        # reminders for this date
        reminders = ReminderModel.get_all()
        day_reminders = [
            r for r in reminders
            if r.get("remind_time", "").startswith(date_str)
        ]
        if day_reminders:
            header = QListWidgetItem("🔔 提醒")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setForeground(QColor(MOCHA["peach"]))
            font = QFont("Microsoft YaHei", 11)
            font.setBold(True)
            header.setFont(font)
            self.month_list.addItem(header)
            for r in day_reminders:
                item = QListWidgetItem(f"  {r.get('remind_time', '')[11:16] or '--:--'}  {r['title']}")
                item.setForeground(QColor(MOCHA["text"]))
                self.month_list.addItem(item)

        # todos for this date
        todos = TodoModel.get_all()
        day_todos = [
            t for t in todos
            if not t.get("is_completed") and t.get("due_date") == date_str
        ]
        if day_todos:
            header = QListWidgetItem("📋 待办")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setForeground(QColor(MOCHA["teal"]))
            font = QFont("Microsoft YaHei", 11)
            font.setBold(True)
            header.setFont(font)
            self.month_list.addItem(header)
            for t in day_todos:
                q = t.get("quadrant", 1)
                item = QListWidgetItem(f"  [{QUADRANT_LABELS[q][:2]}] {t['content']}")
                item.setForeground(QColor(QUADRANT_COLORS.get(q, MOCHA["text"])))
                self.month_list.addItem(item)

        if not day_reminders and not day_todos:
            empty = QListWidgetItem("  暂无提醒或待办")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            empty.setForeground(QColor(MOCHA["subtext"]))
            self.month_list.addItem(empty)

    def _refresh_timeline(self):
        # clear existing items
        while self.timeline_layout.count() > 1:
            item = self.timeline_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        reminders = ReminderModel.get_all()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        upcoming = [r for r in reminders if r.get("remind_time", "") >= now]
        upcoming.sort(key=lambda r: r.get("remind_time", ""))

        for r in upcoming[:50]:
            rt = r.get("remind_time", "")
            title = r.get("title", "")
            repeat = r.get("repeat_type", "none")
            important = r.get("is_important", False)

            item = _TimelineItem(rt, title, repeat, important)
            self.timeline_layout.insertWidget(self.timeline_layout.count() - 1, item)

    def _refresh_quadrant(self):
        todos = TodoModel.get_all()
        counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for t in todos:
            if not t.get("is_completed") and not t.get("is_deleted"):
                q = t.get("quadrant", 1)
                counts[q] = counts.get(q, 0) + 1

        for q, card in self.quadrant_cards.items():
            card.set_count(counts.get(q, 0))

    def _refresh_gantt(self):
        todos = TodoModel.get_all()
        self.gantt_canvas.set_todos(todos)

    # ------------------------------------------------------------------
    # embed / opacity
    # ------------------------------------------------------------------

    def _toggle_desktop_embed(self, checked):
        from PyQt6.QtCore import Qt as _Qt
        top = self.window()
        if checked:
            top.setWindowFlags(
                top.windowFlags()
                | _Qt.WindowType.FramelessWindowHint
                | _Qt.WindowType.WindowStaysOnBottomHint
                | _Qt.WindowType.Tool
            )
        else:
            top.setWindowFlags(
                (top.windowFlags() & ~_Qt.WindowType.FramelessWindowHint
                 & ~_Qt.WindowType.WindowStaysOnBottomHint
                 & ~_Qt.WindowType.Tool)
                | _Qt.WindowType.Window
            )
        top.show()

    def _set_opacity(self, value):
        top = self.window()
        if hasattr(top, 'set_opacity'):
            top.set_opacity(value)
