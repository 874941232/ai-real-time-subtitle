"""Main control window: start/stop toggle, status, button to show subtitle."""
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QStatusBar,
                             QSystemTrayIcon, QMenu, QApplication)
from PyQt6.QtGui import QIcon, QAction

from app.core import config as cfg_mod
from app.ui.subtitle_window import SubtitleWindow
from app.ui.settings_dialog import SettingsDialog
from app.controller import SubtitleController


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI 实时字幕 1.0")
        self.resize(520, 160)
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

        head = QLabel("🎧  AI 实时字幕 — 自动识别系统声音 (网易云 / 浏览器 / 任意播放器)")
        head.setStyleSheet("font-size: 15px; font-weight: 600; padding: 6px 0;")
        v.addWidget(head)

        # engine + toggle row
        row1 = QHBoxLayout()
        self.lbl_engine = QLabel("引擎: 未启动")
        self.lbl_engine.setStyleSheet("color: #555;")
        row1.addWidget(self.lbl_engine)
        row1.addStretch()
        self.btn_toggle = QPushButton("▶  开始")
        self.btn_toggle.setStyleSheet("padding: 8px 28px; font-weight: 600;")
        self.btn_toggle.clicked.connect(self._on_toggle)
        row1.addWidget(self.btn_toggle)
        v.addLayout(row1)

        # subtitle button row
        row2 = QHBoxLayout()
        self.btn_show_sub = QPushButton("显示 / 隐藏字幕")
        self.btn_show_sub.clicked.connect(self._toggle_subtitle)
        self.btn_settings = QPushButton("⚙  设置")
        self.btn_settings.clicked.connect(self._open_settings)
        row2.addWidget(self.btn_show_sub)
        row2.addWidget(self.btn_settings)
        row2.addStretch()
        v.addLayout(row2)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("就绪")

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        menu = QMenu()
        a_show = QAction("显示主窗口", self); a_show.triggered.connect(self.showNormal)
        a_toggle = QAction("显示/隐藏字幕", self); a_toggle.triggered.connect(self._toggle_subtitle)
        a_quit = QAction("退出", self); a_quit.triggered.connect(self._quit_app)
        menu.addAction(a_show); menu.addAction(a_toggle); menu.addSeparator(); menu.addAction(a_quit)
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
            self.btn_toggle.setText("▶  开始")
            self._refresh_status()
        else:
            self.controller.start()
            self.btn_toggle.setText("■  停止")
            # auto show subtitle on first start
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
            self.statusBar().showMessage("设置已保存", 2000)

    # ---------------- Controller callbacks ----------------
    @pyqtSlot(str)
    def _on_status(self, msg: str):
        self.statusBar().showMessage(msg, 4000)

    @pyqtSlot(str)
    def _on_engine(self, name: str):
        self.lbl_engine.setText(f"引擎: {name}")

    def _refresh_status(self):
        self.lbl_engine.setText(f"引擎: {self.controller.current_engine_name}")
        if self.controller.running:
            self.btn_toggle.setText("■  停止")
        else:
            self.btn_toggle.setText("▶  开始")

    def closeEvent(self, e):
        self.controller.stop()
        self.subtitle_win.hide()
        QApplication.quit()
