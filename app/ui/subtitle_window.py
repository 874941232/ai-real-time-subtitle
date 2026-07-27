"""Floating subtitle window — dark tech style."""
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QVariantAnimation, QEasingCurve, QSize, QEvent
from PyQt6.QtGui import QFont, QFontMetrics, QColor
from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QPushButton, QApplication, QSizeGrip, QColorDialog)


class _DragLabel(QLabel):
    """Label that forwards mouse events to parent for dragging."""
    def mousePressEvent(self, e):
        p = self.parentWidget()
        while p is not None and not isinstance(p, SubtitleWindow):
            p = p.parentWidget()
        if p:
            p.mousePressEvent(e)

    def mouseMoveEvent(self, e):
        p = self.parentWidget()
        while p is not None and not isinstance(p, SubtitleWindow):
            p = p.parentWidget()
        if p:
            p.mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        p = self.parentWidget()
        while p is not None and not isinstance(p, SubtitleWindow):
            p = p.parentWidget()
        if p:
            p.mouseReleaseEvent(e)


class SubtitleWindow(QWidget):
    text_updated = pyqtSignal(str)

    MIN_FONT = 14
    MAX_FONT = 60

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self._dragging = False
        self._drag_offset = QPoint(0, 0)
        self._lines: list[str] = []
        self._scroll_anim = None
        self._all_sentences: list[str] = []

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Main container with rounded corners and border
        self._container = QWidget(self)
        self._container.setObjectName("container")
        self._container.setStyleSheet(
            f"""
            QWidget#container {{
                background-color: {self.cfg.bg_color};
                border: 1px solid #3a3a5a;
                border-radius: 12px;
            }}
            """
        )

        outer = QVBoxLayout(self._container)
        outer.setContentsMargins(12, 8, 12, 12)
        outer.setSpacing(4)

        # Top toolbar (auto-hide)
        self._toolbar = QWidget(self._container)
        self._toolbar.setStyleSheet(
            f"""
            background-color: transparent;
            """
        )
        top_bar = QHBoxLayout(self._toolbar)
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(6)
        top_bar.addStretch()

        self._btn_text_color = QPushButton("A", self._toolbar)
        self._btn_text_color.setFixedSize(22, 22)
        self._btn_text_color.setToolTip("文字颜色")
        self._btn_text_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_text_color.clicked.connect(self._pick_text_color)
        top_bar.addWidget(self._btn_text_color)

        self._btn_bg_color = QPushButton("▣", self._toolbar)
        self._btn_bg_color.setFixedSize(22, 22)
        self._btn_bg_color.setToolTip("背景颜色")
        self._btn_bg_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_bg_color.clicked.connect(self._pick_bg_color)
        top_bar.addWidget(self._btn_bg_color)

        self._btn_minus = QPushButton("−", self._toolbar)
        self._btn_minus.setFixedSize(22, 22)
        self._btn_minus.setToolTip("减小字体")
        self._btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_minus.clicked.connect(self._decrease_font)
        top_bar.addWidget(self._btn_minus)

        self._btn_plus = QPushButton("+", self._toolbar)
        self._btn_plus.setFixedSize(22, 22)
        self._btn_plus.setToolTip("增大字体")
        self._btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_plus.clicked.connect(self._increase_font)
        top_bar.addWidget(self._btn_plus)

        self._btn_close = QPushButton("✕", self._toolbar)
        self._btn_close.setFixedSize(22, 22)
        self._btn_close.setToolTip("隐藏字幕窗口")
        self._btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_close.clicked.connect(self.hide)
        top_bar.addWidget(self._btn_close)
        outer.addWidget(self._toolbar)

        # Content area
        self._content = QWidget(self._container)
        self._content.setAutoFillBackground(True)
        pal = self._content.palette()
        pal.setColor(self._content.backgroundRole(), QColor(0, 0, 0, 1))
        self._content.setPalette(pal)
        self._content.installEventFilter(self)
        outer.addWidget(self._content, 1)

        self._label_top = _DragLabel("点击主窗口的「开始」启动识别", self._content)
        self._label_top.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_top.setWordWrap(True)
        self._label_top.setAutoFillBackground(True)

        self._label_bottom = _DragLabel("", self._content)
        self._label_bottom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_bottom.setWordWrap(True)
        self._label_bottom.setAutoFillBackground(True)

        # Size grip
        self._size_grip = QSizeGrip(self._container)
        self._size_grip.setFixedSize(14, 14)
        self._size_grip.setStyleSheet(
            "QSizeGrip { background: rgba(255,255,255,0.2); border-radius: 3px; }"
            "QSizeGrip:hover { background: rgba(255,255,255,0.4); }"
        )

        # Toolbar auto-hide timer
        self._toolbar_timer = None
        self._toolbar_opacity = 1.0

        self._apply_style()
        self._apply_position()
        self.setMinimumSize(QSize(320, 90))
        self.resize(720, 200)

    def _line_height(self) -> int:
        font = QFont(self.cfg.font_family, self.cfg.font_size)
        font.setBold(True)
        fm = QFontMetrics(font)
        return fm.lineSpacing()

    def _max_visible_lines(self) -> int:
        ch = self._content.height()
        lh = self._line_height()
        if lh <= 0:
            return 1
        return max(1, ch // lh)

    def _apply_style(self) -> None:
        font = QFont(self.cfg.font_family, self.cfg.font_size)
        font.setBold(True)

        # Update container background
        self._container.setStyleSheet(
            f"""
            QWidget#container {{
                background-color: {self.cfg.bg_color};
                border: 1px solid #3a3a5a;
                border-radius: 12px;
            }}
            """
        )

        label_style = (
            f"color: {self.cfg.text_color};"
            f" background-color: transparent;"
            " padding: 8px 16px;"
        )
        for lbl in [self._label_top, self._label_bottom]:
            lbl.setFont(font)
            lbl.setStyleSheet(label_style)

        # Toolbar button styles
        btn_style = (
            f"QPushButton {{"
            f"    background-color: rgba(255,255,255,0.1);"
            f"    color: {self.cfg.text_color};"
            f"    border: none;"
            f"    border-radius: 4px;"
            f"    font-size: 11px;"
            f"    font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{"
            f"    background-color: rgba(255,255,255,0.25);"
            f"}}"
        )
        for btn in [self._btn_text_color, self._btn_bg_color,
                    self._btn_minus, self._btn_plus, self._btn_close]:
            btn.setStyleSheet(btn_style)

        self._layout_labels()
        self._refresh_display()

    def _pick_text_color(self):
        init = QColor(self.cfg.text_color)
        if not init.isValid():
            init = QColor("#FFFFFF")
        color = QColorDialog.getColor(init, self, "选择文字颜色")
        if color.isValid():
            self.cfg.text_color = color.name()
            self._apply_style()
            self._save_subtitle_config()

    def _pick_bg_color(self):
        init = QColor(self.cfg.bg_color)
        if not init.isValid():
            init = QColor("#80000000")
        color = QColorDialog.getColor(
            init, self, "选择背景颜色",
            QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            self.cfg.bg_color = color.name(QColor.NameFormat.HexArgb)
            self._apply_style()
            self._save_subtitle_config()

    def _save_subtitle_config(self):
        try:
            from app.core import config as cfg_mod
            full_cfg = cfg_mod.load()
            full_cfg.subtitle = self.cfg
            cfg_mod.save(full_cfg)
        except Exception:
            pass

    def _layout_labels(self) -> None:
        cw = self._content.width()
        ch = self._content.height()
        self._label_top.setGeometry(0, 0, cw, ch)
        self._label_bottom.setGeometry(0, ch, cw, ch)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._container.resize(self.size())
        self._layout_labels()
        self._size_grip.move(
            self._container.width() - 18,
            self._container.height() - 18
        )
        self._apply_style()

    def _refresh_display(self) -> None:
        max_lines = self._max_visible_lines()
        if self._all_sentences:
            visible = self._all_sentences[-max_lines:]
            self._lines = visible
            self._label_top.setText("\n".join(self._lines))

    def _apply_position(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        w = self.width()
        h = self.height()
        if self.cfg.position == "top":
            x = (geo.width() - w) // 2 + geo.x()
            y = geo.y() + 40
        elif self.cfg.position == "middle":
            x = (geo.width() - w) // 2 + geo.x()
            y = (geo.height() - h) // 2 + geo.y()
        else:
            x = (geo.width() - w) // 2 + geo.x()
            y = geo.y() + geo.height() - h - 60
        self.move(x, y)

    def update_config(self, cfg) -> None:
        self.cfg = cfg
        self._apply_style()
        self._apply_position()

    def _increase_font(self) -> None:
        if self.cfg.font_size < self.MAX_FONT:
            self.cfg.font_size += 2
            self._apply_style()

    def _decrease_font(self) -> None:
        if self.cfg.font_size > self.MIN_FONT:
            self.cfg.font_size -= 2
            self._apply_style()

    def set_text(self, text: str) -> None:
        if not text:
            self._all_sentences = []
            self._lines = []
            self._label_top.setText("")
            return
        import re
        parts = [p.strip() for p in re.split(r'\n', text) if p.strip()]
        if not parts:
            return

        old_count = len(self._all_sentences)
        for part in parts:
            if self._all_sentences and self._all_sentences[-1] == part:
                continue
            if self._all_sentences and part in self._all_sentences[-5:]:
                continue
            self._all_sentences.append(part)

        if len(self._all_sentences) > 50:
            self._all_sentences = self._all_sentences[-50:]

        if len(self._all_sentences) == old_count:
            return

        max_lines = self._max_visible_lines()
        visible = self._all_sentences[-max_lines:]
        old_visible = list(self._lines)
        self._lines = visible
        new_text = "\n".join(self._lines)

        if not old_visible:
            self._label_top.setText(new_text)
        else:
            self._animate_scroll(new_text)

        self.text_updated.emit(new_text)

    def append_partial(self, text: str) -> None:
        if not text:
            return
        max_lines = self._max_visible_lines()
        if self._all_sentences:
            self._all_sentences[-1] = text
        else:
            self._all_sentences = [text]
        self._lines = self._all_sentences[-max_lines:]
        self._label_top.setText("\n".join(self._lines))

    def _animate_scroll(self, new_text: str) -> None:
        if self._scroll_anim and self._scroll_anim.state() == self._scroll_anim.State.Running:
            self._scroll_anim.stop()

        ch = self._content.height()
        lh = self._line_height()
        scroll_dist = lh

        self._label_bottom.setText(new_text)
        self._label_bottom.move(0, ch)
        self._label_bottom.show()

        self._scroll_anim = QVariantAnimation(self)
        self._scroll_anim.setDuration(350)
        self._scroll_anim.setStartValue(0.0)
        self._scroll_anim.setEndValue(1.0)
        self._scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def update_scroll(progress: float):
            offset = int(scroll_dist * progress)
            self._label_top.move(0, -offset)
            self._label_bottom.move(0, ch - offset)

        self._scroll_anim.valueChanged.connect(lambda v: update_scroll(v))

        def finish_scroll():
            self._label_top.setText(new_text)
            self._label_top.move(0, 0)
            self._label_bottom.setText("")
            self._label_bottom.move(0, ch)

        self._scroll_anim.finished.connect(finish_scroll)
        self._scroll_anim.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._dragging and (e.buttons() & Qt.MouseButton.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_offset)
            e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            e.accept()

    def eventFilter(self, watched, event):
        if watched is self._content and event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonRelease,
        ):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self.mousePressEvent(event)
                return True
            if event.type() == QEvent.Type.MouseMove:
                self.mouseMoveEvent(event)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self.mouseReleaseEvent(event)
                return True
        return super().eventFilter(watched, event)
