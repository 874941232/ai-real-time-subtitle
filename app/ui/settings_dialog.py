"""Settings dialog — dark tech style with sidebar navigation."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QLineEdit, QComboBox, QPushButton,
                             QVBoxLayout, QHBoxLayout, QLabel, QWidget,
                             QDoubleSpinBox, QMessageBox, QStackedWidget,
                             QFrame, QSizePolicy)
from app.core import config as cfg_mod
from app.core.audio_capture import list_loopback_devices


# Dark theme palette
DARK_BG = "#0f0f1a"
DARK_CARD = "#1a1a2e"
DARKER_CARD = "#141428"
ACCENT = "#00d4ff"
ACCENT_HOVER = "#33e0ff"
TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#8888aa"
BORDER = "#2a2a4a"
SUCCESS = "#00e676"
WARNING = "#ffab40"

SETTINGS_STYLE = f"""
QDialog {{
    background-color: {DARK_BG};
}}
QLabel {{
    color: {TEXT_PRIMARY};
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
}}
QLabel#sectionTitle {{
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
}}
QLabel#hintLabel {{
    font-size: 11px;
    color: {TEXT_SECONDARY};
}}
QLabel#navLabel {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
    padding: 2px 0;
}}
QPushButton#navBtn {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
    font-family: "Microsoft YaHei";
    text-align: left;
}}
QPushButton#navBtn:hover {{
    background-color: {DARK_CARD};
    color: {TEXT_PRIMARY};
}}
QPushButton#navBtn:checked {{
    background-color: {DARK_CARD};
    color: {ACCENT};
    font-weight: 600;
}}
QPushButton#actionBtn {{
    background-color: {DARK_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 12px;
    font-family: "Microsoft YaHei";
}}
QPushButton#actionBtn:hover {{
    background-color: {DARKER_CARD};
    border-color: {ACCENT};
}}
QPushButton#primaryBtn {{
    background-color: {ACCENT};
    color: {DARK_BG};
    border: none;
    border-radius: 8px;
    padding: 8px 24px;
    font-size: 12px;
    font-weight: 700;
    font-family: "Microsoft YaHei";
}}
QPushButton#primaryBtn:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#testBtn {{
    background-color: transparent;
    color: {ACCENT};
    border: 1px solid {ACCENT};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 11px;
    font-family: "Microsoft YaHei";
}}
QPushButton#testBtn:hover {{
    background-color: {ACCENT};
    color: {DARK_BG};
}}
QLineEdit {{
    background-color: {DARK_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
    font-family: "Microsoft YaHei";
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}
QComboBox {{
    background-color: {DARK_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
    font-family: "Microsoft YaHei";
    min-width: 200px;
}}
QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {DARK_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    selection-background-color: {DARKER_CARD};
}}
QDoubleSpinBox {{
    background-color: {DARK_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
    font-family: "Microsoft YaHei";
}}
QDoubleSpinBox:focus {{
    border-color: {ACCENT};
}}
QFrame#card {{
    background-color: {DARK_CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#card:hover {{
    border-color: {ACCENT};
}}
"""


class SettingsDialog(QDialog):
    def __init__(self, current: cfg_mod.AppConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(720, 520)
        self.setStyleSheet(SETTINGS_STYLE)
        self._cfg = current
        self._nav_buttons = []
        self._build_ui()
        self._populate()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Left sidebar ----
        sidebar = QWidget()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet(f"background-color: {DARK_BG};")
        s_v = QVBoxLayout(sidebar)
        s_v.setContentsMargins(12, 20, 12, 20)
        s_v.setSpacing(4)

        # Sidebar title
        title = QLabel("设置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #ffffff;")
        s_v.addWidget(title)
        s_v.addSpacing(16)

        nav_items = [
            ("识别", 0),
            ("API", 1),
            ("音频", 2),
            ("模型", 3),
        ]
        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self._switch_page(i))
            s_v.addWidget(btn)
            self._nav_buttons.append(btn)

        s_v.addStretch()

        # Close button at bottom
        btn_close = QPushButton("关闭")
        btn_close.setObjectName("navBtn")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        s_v.addWidget(btn_close)

        root.addWidget(sidebar)

        # ---- Right content area ----
        content_area = QWidget()
        content_area.setStyleSheet(f"background-color: {DARK_BG};")
        c_v = QVBoxLayout(content_area)
        c_v.setContentsMargins(24, 20, 24, 20)
        c_v.setSpacing(16)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_page_recognition())
        self._stack.addWidget(self._build_page_api())
        self._stack.addWidget(self._build_page_audio())
        self._stack.addWidget(self._build_page_model())
        c_v.addWidget(self._stack)

        # Footer buttons
        footer = QHBoxLayout()
        footer.addStretch()
        btn_save = QPushButton("保存")
        btn_save.setObjectName("primaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._on_save)
        footer.addWidget(btn_save)
        c_v.addLayout(footer)

        root.addWidget(content_area, 1)

        # Select first nav
        self._switch_page(0)

    def _switch_page(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == idx)

    def _build_page_recognition(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)

        title = QLabel("识别设置")
        title.setObjectName("sectionTitle")
        v.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        c_v = QVBoxLayout(card)
        c_v.setContentsMargins(20, 20, 20, 20)
        c_v.setSpacing(16)

        # Mode
        row1 = QHBoxLayout()
        lbl1 = QLabel("识别模式")
        lbl1.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        row1.addWidget(lbl1)
        row1.addStretch()
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems([
            "本地 SenseVoice (离线无限量)",
            "百度在线 (永久免费)",
            "阿里云在线 (每日免费额度)",
            "自动模式 (百度优先，失败回退本地)",
        ])
        row1.addWidget(self.cmb_mode)
        c_v.addLayout(row1)

        # Language
        row2 = QHBoxLayout()
        lbl2 = QLabel("识别语言")
        lbl2.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        row2.addWidget(lbl2)
        row2.addStretch()
        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["中文", "英文", "自动检测"])
        row2.addWidget(self.cmb_lang)
        c_v.addLayout(row2)

        v.addWidget(card)
        v.addStretch()
        return page

    def _build_page_api(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)

        title = QLabel("API 配置")
        title.setObjectName("sectionTitle")
        v.addWidget(title)

        # Baidu card
        card_baidu = QFrame()
        card_baidu.setObjectName("card")
        c_v = QVBoxLayout(card_baidu)
        c_v.setContentsMargins(20, 20, 20, 20)
        c_v.setSpacing(12)

        lbl_baidu = QLabel("百度语音")
        lbl_baidu.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff;")
        c_v.addWidget(lbl_baidu)

        hint_baidu = QLabel("永久免费，需在百度智能云创建语音技术应用")
        hint_baidu.setObjectName("hintLabel")
        c_v.addWidget(hint_baidu)

        self.ed_baidu_api = QLineEdit()
        self.ed_baidu_api.setPlaceholderText("API Key")
        c_v.addWidget(self.ed_baidu_api)

        self.ed_baidu_secret = QLineEdit()
        self.ed_baidu_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_baidu_secret.setPlaceholderText("Secret Key")
        c_v.addWidget(self.ed_baidu_secret)

        btn_test_baidu = QPushButton("测试连接")
        btn_test_baidu.setObjectName("testBtn")
        btn_test_baidu.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test_baidu.clicked.connect(self._test_baidu_api)
        btn_test_baidu.setMaximumWidth(100)
        c_v.addWidget(btn_test_baidu)

        v.addWidget(card_baidu)

        # Aliyun card
        card_ali = QFrame()
        card_ali.setObjectName("card")
        c_v2 = QVBoxLayout(card_ali)
        c_v2.setContentsMargins(20, 20, 20, 20)
        c_v2.setSpacing(12)

        lbl_ali = QLabel("阿里云语音")
        lbl_ali.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff;")
        c_v2.addWidget(lbl_ali)

        hint_ali = QLabel("每日有免费额度，需开通智能语音交互服务")
        hint_ali.setObjectName("hintLabel")
        c_v2.addWidget(hint_ali)

        self.ed_ali_id = QLineEdit()
        self.ed_ali_id.setPlaceholderText("AccessKey ID")
        c_v2.addWidget(self.ed_ali_id)

        self.ed_ali_secret = QLineEdit()
        self.ed_ali_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_ali_secret.setPlaceholderText("AccessKey Secret")
        c_v2.addWidget(self.ed_ali_secret)

        self.ed_ali_appkey = QLineEdit()
        self.ed_ali_appkey.setPlaceholderText("Appkey")
        c_v2.addWidget(self.ed_ali_appkey)

        btn_test_ali = QPushButton("测试连接")
        btn_test_ali.setObjectName("testBtn")
        btn_test_ali.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test_ali.clicked.connect(self._test_aliyun_api)
        btn_test_ali.setMaximumWidth(100)
        c_v2.addWidget(btn_test_ali)

        v.addWidget(card_ali)
        v.addStretch()
        return page

    def _build_page_audio(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)

        title = QLabel("音频设置")
        title.setObjectName("sectionTitle")
        v.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        c_v = QVBoxLayout(card)
        c_v.setContentsMargins(20, 20, 20, 20)
        c_v.setSpacing(16)

        # Device
        row1 = QHBoxLayout()
        lbl1 = QLabel("输入设备")
        lbl1.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        row1.addWidget(lbl1)
        row1.addStretch()
        self.cmb_device = QComboBox()
        devs = list_loopback_devices()
        self.cmb_device.addItem("默认扬声器回采", "")
        for d in devs:
            self.cmb_device.addItem(d, d)
        row1.addWidget(self.cmb_device)
        c_v.addLayout(row1)

        # Chunk
        row2 = QHBoxLayout()
        lbl2 = QLabel("分块秒数")
        lbl2.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        row2.addWidget(lbl2)
        hint2 = QLabel("每次识别的音频片段长度")
        hint2.setObjectName("hintLabel")
        row2.addWidget(hint2)
        row2.addStretch()
        self.sp_chunk = QDoubleSpinBox()
        self.sp_chunk.setRange(1.0, 10.0)
        self.sp_chunk.setSingleStep(0.5)
        self.sp_chunk.setFixedWidth(100)
        row2.addWidget(self.sp_chunk)
        c_v.addLayout(row2)

        # Threshold
        row3 = QHBoxLayout()
        lbl3 = QLabel("静音阈值")
        lbl3.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        row3.addWidget(lbl3)
        hint3 = QLabel("低于此值视为静音")
        hint3.setObjectName("hintLabel")
        row3.addWidget(hint3)
        row3.addStretch()
        self.sp_thresh = QDoubleSpinBox()
        self.sp_thresh.setRange(0.0, 0.5)
        self.sp_thresh.setSingleStep(0.005)
        self.sp_thresh.setDecimals(3)
        self.sp_thresh.setFixedWidth(100)
        row3.addWidget(self.sp_thresh)
        c_v.addLayout(row3)

        v.addWidget(card)
        v.addStretch()
        return page

    def _build_page_model(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)

        title = QLabel("本地模型")
        title.setObjectName("sectionTitle")
        v.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        c_v = QVBoxLayout(card)
        c_v.setContentsMargins(20, 20, 20, 20)
        c_v.setSpacing(16)

        lbl = QLabel("SenseVoice 模型")
        lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff;")
        c_v.addWidget(lbl)

        hint = QLabel("首次使用时会自动下载（约 230MB），也可手动检查更新")
        hint.setObjectName("hintLabel")
        c_v.addWidget(hint)

        h = QHBoxLayout()
        h.setSpacing(12)
        btn_check = QPushButton("检查更新")
        btn_check.setObjectName("actionBtn")
        btn_check.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_check.clicked.connect(self._check_model_update)
        h.addWidget(btn_check)

        btn_update = QPushButton("更新模型")
        btn_update.setObjectName("actionBtn")
        btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_update.clicked.connect(self._update_model)
        h.addWidget(btn_update)
        h.addStretch()
        c_v.addLayout(h)

        v.addWidget(card)
        v.addStretch()
        return page

    def _populate(self) -> None:
        a, ad = self._cfg.asr, self._cfg.audio
        mode_map = {"local": 0, "baidu": 1, "aliyun": 2, "auto": 3}
        self.cmb_mode.setCurrentIndex(mode_map.get(a.mode, 0))
        self.ed_baidu_api.setText(a.baidu_api_key)
        self.ed_baidu_secret.setText(a.baidu_secret_key)
        self.ed_ali_id.setText(a.aliyun_access_key_id)
        self.ed_ali_secret.setText(a.aliyun_access_key_secret)
        self.ed_ali_appkey.setText(a.aliyun_appkey)
        lang_map = {"zh": 0, "en": 1, "auto": 2}
        self.cmb_lang.setCurrentIndex(lang_map.get(a.language, 0))
        idx = self.cmb_device.findData(ad.device_name)
        if idx >= 0:
            self.cmb_device.setCurrentIndex(idx)
        self.sp_chunk.setValue(ad.chunk_seconds)
        self.sp_thresh.setValue(ad.silence_threshold)

    def _on_save(self) -> None:
        c = cfg_mod.AppConfig()
        idx = self.cmb_mode.currentIndex()
        c.asr.mode = ["local", "baidu", "aliyun", "auto"][idx]
        c.asr.baidu_api_key = self.ed_baidu_api.text().strip()
        c.asr.baidu_secret_key = self.ed_baidu_secret.text().strip()
        c.asr.aliyun_access_key_id = self.ed_ali_id.text().strip()
        c.asr.aliyun_access_key_secret = self.ed_ali_secret.text().strip()
        c.asr.aliyun_appkey = self.ed_ali_appkey.text().strip()
        c.asr.local_model = "sensevoice"
        idx = self.cmb_lang.currentIndex()
        c.asr.language = ["zh", "en", "auto"][idx]
        c.subtitle = self._cfg.subtitle
        c.audio.device_name = self.cmb_device.currentData() or ""
        c.audio.sample_rate = 16000
        c.audio.channels = 1
        c.audio.chunk_seconds = self.sp_chunk.value()
        c.audio.silence_threshold = self.sp_thresh.value()
        try:
            cfg_mod.save(c)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        self._cfg = c
        self.accept()

    def _test_baidu_api(self) -> None:
        api_key = self.ed_baidu_api.text().strip()
        secret_key = self.ed_baidu_secret.text().strip()
        if not api_key or not secret_key:
            QMessageBox.warning(self, "测试失败", "请先填写百度 API Key 和 Secret Key")
            return
        from app.asr.baidu_engine import BaiduEngine
        try:
            engine = BaiduEngine(api_key, secret_key)
            engine._get_token()
            QMessageBox.information(self, "测试成功", "百度 API 连接正常！")
        except Exception as e:
            QMessageBox.critical(self, "测试失败", f"百度 API 连接失败：{str(e)}")

    def _test_aliyun_api(self) -> None:
        ali_id = self.ed_ali_id.text().strip()
        ali_secret = self.ed_ali_secret.text().strip()
        ali_appkey = self.ed_ali_appkey.text().strip()
        if not ali_id or not ali_secret or not ali_appkey:
            QMessageBox.warning(self, "测试失败", "请先填写阿里云 AccessKey ID、Secret 和 Appkey")
            return
        from app.asr.aliyun_engine import AliyunEngine
        try:
            engine = AliyunEngine(ali_id, ali_secret, ali_appkey)
            engine._get_token()
            QMessageBox.information(self, "测试成功", "阿里云 API 连接正常！")
        except Exception as e:
            QMessageBox.critical(self, "测试失败", f"阿里云 API 连接失败：{str(e)}")

    def _check_model_update(self) -> None:
        from app.asr.sensevoice_engine import check_model_update
        try:
            info = check_model_update()
            if info["model_path"] is None:
                QMessageBox.information(self, "模型检查", "未找到本地模型，首次运行时会自动下载")
                return
            local_mb = info["local_size"] / (1024 * 1024)
            remote_mb = info["remote_size"] / (1024 * 1024)
            if info["has_update"]:
                msg = f"发现新版本！\n\n本地模型：{local_mb:.1f}MB\n远程模型：{remote_mb:.1f}MB\n\n建议点击「更新模型」按钮获取最新版本。"
                QMessageBox.information(self, "模型更新", msg)
            else:
                msg = f"本地模型已是最新版本！\n\n模型路径：{info['model_path']}\n模型大小：{local_mb:.1f}MB"
                QMessageBox.information(self, "模型检查", msg)
        except Exception as e:
            QMessageBox.critical(self, "检查失败", f"检查模型更新失败：{str(e)}")

    def _update_model(self) -> None:
        reply = QMessageBox.question(
            self, "确认更新",
            "确定要更新本地模型吗？\n\n更新会重新下载整个模型文件（约 230MB），可能需要几分钟时间。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from app.asr.sensevoice_engine import update_model
        try:
            update_model()
            QMessageBox.information(self, "更新成功", "模型更新完成！\n\n下次启动时会使用新模型。")
        except Exception as e:
            QMessageBox.critical(self, "更新失败", f"更新模型失败：{str(e)}")

    def result_config(self) -> cfg_mod.AppConfig:
        return self._cfg
