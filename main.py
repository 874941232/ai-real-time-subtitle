"""Entry point: launches the main window."""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AI 实时字幕")
    app.setOrganizationName("0723Audio")
    # Don't quit when floating subtitle is closed
    app.setQuitOnLastWindowClosed(False)

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
