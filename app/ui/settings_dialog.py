"""Simplified settings dialog — 国内服务: 本地 + 百度 + 阿里云."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QComboBox,
                             QPushButton, QVBoxLayout, QHBoxLayout,
                             QDoubleSpinBox, QLabel, QWidget, QMessageBox,
                             QGroupBox)
from app.core import config as cfg_mod
from app.core.audio_capture import list_loopback_devices


class SettingsDialog(QDialog):
    def __init__(self, current: cfg_mod.AppConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置 - AI 实时字幕")
        self.resize(560, 580)
        self._cfg = current
        self._build_ui()
        self._populate()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Recognition Mode
        grp_mode = QGroupBox("识别设置")
        form_mode = QFormLayout(grp_mode)
        form_mode.setContentsMargins(8, 12, 8, 8)
        form_mode.setSpacing(10)

        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems([
            "本地 SenseVoice (离线无限量，推荐)",
            "百度在线 (永久免费)",
            "阿里云在线 (每日免费额度)",
            "自动模式 (百度优先，失败回退本地)",
        ])
        self.cmb_mode.setToolTip(
            "选择语音识别模式：\n"
            "- 本地：完全离线，无需网络，无限量使用\n"
            "- 百度：永久免费，需配置 API Key\n"
            "- 阿里云：每日有免费额度\n"
            "- 自动：优先使用百度，其次阿里云，失败自动切本地"
        )
        form_mode.addRow("识别模式:", self.cmb_mode)

        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["中文", "英文", "自动检测"])
        self.cmb_lang.setToolTip(
            "选择识别语言：\n"
            "- 中文：仅识别中文\n"
            "- 英文：仅识别英文\n"
            "- 自动检测：自动识别语言类型"
        )
        form_mode.addRow("识别语言:", self.cmb_lang)
        root.addWidget(grp_mode)

        # Baidu API
        grp_baidu = QGroupBox("百度 API")
        form_baidu = QFormLayout(grp_baidu)
        form_baidu.setContentsMargins(8, 12, 8, 8)
        form_baidu.setSpacing(10)

        hint_baidu = QLabel("永久免费，需在百度智能云创建语音技术应用")
        hint_baidu.setStyleSheet("color: #888; font-size: 11px;")
        form_baidu.addRow(hint_baidu)

        self.ed_baidu_api = QLineEdit()
        self.ed_baidu_api.setPlaceholderText("API Key")
        self.ed_baidu_api.setToolTip(
            "百度智能云 API Key\n"
            "获取方式：登录百度智能云控制台 → 语音技术 → 创建应用"
        )
        form_baidu.addRow("API Key:", self.ed_baidu_api)

        self.ed_baidu_secret = QLineEdit()
        self.ed_baidu_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_baidu_secret.setPlaceholderText("Secret Key")
        self.ed_baidu_secret.setToolTip(
            "百度智能云 Secret Key\n"
            "注意：创建应用时会显示一次，请妥善保存"
        )
        form_baidu.addRow("Secret Key:", self.ed_baidu_secret)

        btn_test_baidu = QPushButton("测试百度 API")
        btn_test_baidu.clicked.connect(self._test_baidu_api)
        form_baidu.addRow("", btn_test_baidu)
        root.addWidget(grp_baidu)

        # Aliyun API
        grp_ali = QGroupBox("阿里云 API")
        form_ali = QFormLayout(grp_ali)
        form_ali.setContentsMargins(8, 12, 8, 8)
        form_ali.setSpacing(10)

        hint_ali = QLabel("每日有免费额度，需开通智能语音交互服务")
        hint_ali.setStyleSheet("color: #888; font-size: 11px;")
        form_ali.addRow(hint_ali)

        self.ed_ali_id = QLineEdit()
        self.ed_ali_id.setPlaceholderText("AccessKey ID")
        self.ed_ali_id.setToolTip(
            "阿里云 AccessKey ID\n"
            "获取方式：控制台 → 头像 → AccessKey 管理"
        )
        form_ali.addRow("AccessKey ID:", self.ed_ali_id)

        self.ed_ali_secret = QLineEdit()
        self.ed_ali_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_ali_secret.setPlaceholderText("AccessKey Secret")
        self.ed_ali_secret.setToolTip(
            "阿里云 AccessKey Secret\n"
            "注意：创建时显示一次，请妥善保存"
        )
        form_ali.addRow("AccessKey Secret:", self.ed_ali_secret)

        self.ed_ali_appkey = QLineEdit()
        self.ed_ali_appkey.setPlaceholderText("Appkey")
        self.ed_ali_appkey.setToolTip(
            "智能语音交互 Appkey\n"
            "获取方式：智能语音交互 → 创建项目"
        )
        form_ali.addRow("Appkey:", self.ed_ali_appkey)

        btn_test_ali = QPushButton("测试阿里云 API")
        btn_test_ali.clicked.connect(self._test_aliyun_api)
        form_ali.addRow("", btn_test_ali)
        root.addWidget(grp_ali)

        # Audio Settings
        grp_audio = QGroupBox("音频设置")
        form_audio = QFormLayout(grp_audio)
        form_audio.setContentsMargins(8, 12, 8, 8)
        form_audio.setSpacing(10)

        self.cmb_device = QComboBox()
        devs = list_loopback_devices()
        self.cmb_device.addItem("默认扬声器回采", "")
        for d in devs:
            self.cmb_device.addItem(d, d)
        self.cmb_device.setToolTip(
            "选择音频输入设备\n"
            "- 默认扬声器回采：录制电脑播放的声音"
        )
        form_audio.addRow("输入设备:", self.cmb_device)

        self.sp_chunk = QDoubleSpinBox()
        self.sp_chunk.setRange(1.0, 10.0)
        self.sp_chunk.setSingleStep(0.5)
        self.sp_chunk.setToolTip(
            "每次识别的音频片段长度（秒）\n"
            "- 值越小：延迟越低\n"
            "- 值越大：识别更完整\n"
            "推荐：3.0 秒"
        )
        form_audio.addRow("分块秒数:", self.sp_chunk)

        self.sp_thresh = QDoubleSpinBox()
        self.sp_thresh.setRange(0.0, 0.5)
        self.sp_thresh.setSingleStep(0.005)
        self.sp_thresh.setDecimals(3)
        self.sp_thresh.setToolTip(
            "静音检测阈值\n"
            "- 值越小：更敏感\n"
            "- 值越大：更迟钝\n"
            "推荐：0.010"
        )
        form_audio.addRow("静音阈值(RMS):", self.sp_thresh)
        root.addWidget(grp_audio)

        # Model Update
        grp_model = QGroupBox("本地模型")
        form_model = QFormLayout(grp_model)
        form_model.setContentsMargins(8, 12, 8, 8)
        form_model.setSpacing(10)

        model_row = QHBoxLayout()
        btn_check_update = QPushButton("检查更新")
        btn_check_update.clicked.connect(self._check_model_update)
        btn_update_model = QPushButton("更新模型")
        btn_update_model.clicked.connect(self._update_model)
        model_row.addWidget(btn_check_update)
        model_row.addWidget(btn_update_model)
        model_row.addStretch()
        form_model.addRow("", model_row)
        root.addWidget(grp_model)

        # Footer buttons
        bar = QHBoxLayout()
        bar.addStretch()
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("保存")
        ok.setDefault(True)
        ok.clicked.connect(self._on_save)
        bar.addWidget(cancel)
        bar.addWidget(ok)
        root.addLayout(bar)

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
            QMessageBox.information(self, "测试成功", "百度 API Key 有效，连接正常！")
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
            QMessageBox.information(self, "测试成功", "阿里云 API Key 有效，连接正常！")
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
            self,
            "确认更新",
            "确定要更新本地模型吗？\n\n"
            "更新会重新下载整个模型文件（约 230MB），\n"
            "可能需要几分钟时间。",
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
