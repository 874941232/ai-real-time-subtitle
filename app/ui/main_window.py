"""Main control window — dark tech style."""
from PyQt6.QtCore import Qt, pyqtSlot, QSize
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QApplication,
                             QSystemTrayIcon, QMenu)
from PyQt6.QtGui import QIcon, QAction, QFont, QColor

from app.core import config as cfg_mod
from app.ui.subtitle_window import SubtitleWindow
from app.ui.settings_dialog import SettingsDialog
from app.controller import SubtitleController


# Dark theme palette
DARK_BG = "#0f0f1a"
DARK_CARD = "#1a1a2e"
ACCENT = "#00d4ff"
ACCENT_HOVER = "#33e0ff"
TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#8888aa"
BORDER = "#2a2a4a"

MAIN_STYLE = f"""
QMainWindow {{
    background-color: {DARK_BG};
}}
QLabel {{
    color: {TEXT_PRIMARY};
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
}}
QPushButton#startBtn {{
    background-color: {ACCENT};
    color: {DARK_BG};
    border: none;
    border-radius: 35px;
    padding: 0;
    font-size: 16px;
    font-weight: 700;
    font-family: "Microsoft YaHei";
}}
QPushButton#startBtn:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#startBtn:pressed {{
    background-color: {ACCENT};
}}
QPushButton#iconBtn {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-family: "Microsoft YaHei";
}}
QPushButton#iconBtn:hover {{
    background-color: {DARK_CARD};
    color: {TEXT_PRIMARY};
    border-color: {ACCENT};
}}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI 实时字幕")
        self.resize(480, 340)
        self.setStyleSheet(MAIN_STYLE)
        self.cfg = cfg_mod.load()

        # subtitle window (floating)
        self.subtitle_win = SubtitleWindow(self.cfg.subtitle)

        # controller (audio + ASR)
        self.controller = SubtitleController(self.cfg, self)
        self.controller.status_changed.connect(self._on_status)
        self.controller.text_ready.connect(self.subtitle_win.set_text)
        self.controller.partial_text.connect(self.subtitle_win.append_partial)
        self.controller.engine_changed.connect(self._on_engine)

        self._build_ui()
        self._build_tray()
        self._refresh_status()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setContentsMargins(40, 30, 40, 30)
        v.setSpacing(20)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        title = QLabel("AI 实时字幕")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #ffffff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(title)

        # Subtitle
        sub = QLabel("自动识别系统声音，实时显示字幕")
        sub.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY};")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(sub)

        v.addSpacing(20)

        # Big circular start/stop button
        self.btn_toggle = QPushButton("▶")
        self.btn_toggle.setObjectName("startBtn")
        self.btn_toggle.setFixedSize(70, 70)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self._on_toggle)
        v.addWidget(self.btn_toggle, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status label under button
        self.lbl_status = QLabel("点击开始识别")
        self.lbl_status.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.lbl_status)

        v.addStretch()

        # Engine info
        self.lbl_engine = QLabel("引擎: 未启动")
        self.lbl_engine.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        self.lbl_engine.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.lbl_engine)

        # Bottom action bar
        h = QHBoxLayout()
        h.setSpacing(12)
        h.addStretch()

        self.btn_show_sub = QPushButton("字幕")
        self.btn_show_sub.setObjectName("iconBtn")
        self.btn_show_sub.setFixedWidth(70)
        self.btn_show_sub.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_show_sub.clicked.connect(self._toggle_subtitle)
        h.addWidget(self.btn_show_sub)

        self.btn_settings = QPushButton("设置")
        self.btn_settings.setObjectName("iconBtn")
        self.btn_settings.setFixedWidth(70)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self._open_settings)
        h.addWidget(self.btn_settings)

        h.addStretch()
        v.addLayout(h)

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        menu = QMenu()
        a_show = QAction("显示主窗口", self)
        a_show.triggered.connect(self.showNormal)
        a_toggle = QAction("显示/隐藏字幕", self)
        a_toggle.triggered.connect(self._toggle_subtitle)
        a_quit = QAction("退出", self)
        a_quit.triggered.connect(self._quit_app)
        menu.addAction(a_show)
        menu.addAction(a_toggle)
        menu.addSeparator()
        menu.addAction(a_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self._on_tray_activated(r))
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_subtitle()

    def _quit_app(self):
        self.controller.stop()
        QApplication.quit()

    # ---------------- Actions ----------------
    def _on_toggle(self):
        if self.controller.running:
            self.controller.stop()
            self.btn_toggle.setText("▶")
            self.lbl_status.setText("点击开始识别")
            self._refresh_status()
        else:
            self.controller.start()
            self.btn_toggle.setText("■")
            self.lbl_status.setText("识别中...")
            if not self.subtitle_win.isVisible():
                self.subtitle_win.show()

    def _toggle_subtitle(self):
        if self.subtitle_win.isVisible():
            self.subtitle_win.hide()
        else:
            self.subtitle_win.show()
            self.subtitle_win.raise_()

    def _open_settings(self):
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            self.cfg = dlg.result_config()
            self.controller.update_config(self.cfg)
            self.lbl_status.setText("设置已保存")

    # ---------------- Controller callbacks ----------------
    @pyqtSlot(str)
    def _on_status(self, msg: str):
        self.lbl_status.setText(msg)

    @pyqtSlot(str)
    def _on_engine(self, name: str):
        self.lbl_engine.setText(f"引擎: {name}")

    def _refresh_status(self):
        self.lbl_engine.setText(f"引擎: {self.controller.current_engine_name}")
        if self.controller.running:
            self.btn_toggle.setText("■")
            self.lbl_status.setText("识别中...")
        else:
            self.btn_toggle.setText("▶")
            self.lbl_status.setText("点击开始识别")

    def closeEvent(self, e):
        self.controller.stop()
        self.subtitle_win.hide()
        QApplication.quit()
