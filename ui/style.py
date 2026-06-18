"""共享样式表"""

STYLE = """
QMainWindow {
    background: #1e1e2e;
}
QWidget {
    color: #cdd6f4;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
}
QPushButton {
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
}
QPushButton:hover {
    background: #313244;
}
QLabel {
    color: #cdd6f4;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px;
    color: #cdd6f4;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #89b4fa;
}
QComboBox {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
    color: #cdd6f4;
}
QComboBox QAbstractItemView {
    background: #313244;
    border: 1px solid #45475a;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}
QTableWidget {
    background: #1e1e2e;
    alternate-background-color: #313244;
    border: 1px solid #45475a;
    gridline-color: #45475a;
    color: #cdd6f4;
}
QTableWidget::item:selected {
    background: #89b4fa;
    color: #1e1e2e;
}
QHeaderView::section {
    background: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 6px;
}
QScrollBar:vertical {
    background: #1e1e2e;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #1e1e2e;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #45475a;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QCheckBox {
    color: #cdd6f4;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #45475a;
    border-radius: 4px;
    background: #313244;
}
QCheckBox::indicator:checked {
    background: #89b4fa;
    border-color: #89b4fa;
}
QGroupBox {
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QDateTimeEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
    color: #cdd6f4;
}
QDateTimeEdit:focus, QSpinBox:focus {
    border: 1px solid #89b4fa;
}
QSlider::groove:horizontal {
    background: #45475a;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #89b4fa;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: #89b4fa;
    border-radius: 3px;
}
QTabWidget::pane {
    border: 1px solid #45475a;
    background: #1e1e2e;
}
QTabBar::tab {
    background: #313244;
    color: #a6adc8;
    padding: 8px 16px;
    border: 1px solid #45475a;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #1e1e2e;
    color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
}
QCalendarWidget {
    background: #1e1e2e;
    color: #cdd6f4;
}
QCalendarWidget QToolButton {
    color: #cdd6f4;
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
}
QCalendarWidget QToolButton:hover {
    background: #45475a;
}
QCalendarWidget QMenu {
    background: #313244;
    color: #cdd6f4;
}
QCalendarWidget QSpinBox {
    background: #313244;
    color: #cdd6f4;
}
"""
