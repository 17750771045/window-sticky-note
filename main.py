"""便利贴 - 随手记 · 高效管理"""
import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from ui.main_window import MainWindow, get_app_dir
from ui.style import STYLE


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    app.setApplicationName("便利贴-zy")
    app.setWindowIcon(QIcon(os.path.join(get_app_dir(), "zhang.jpg")))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
