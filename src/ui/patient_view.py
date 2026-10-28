"""
患者全景视图

设计要点：
- 分组卡片式布局，信息层次清晰
- 表格采用统一的专业样式
- 异常检验项以柔和红色背景标注（替代刺眼黄色）
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QGroupBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QListWidget,
    QListWidgetItem, QPushButton, QMessageBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPixmap, QIcon

from ..core.patient import Patient
from ..core.medical_record import NLPEngine
from .icons import image_icon, upload_icon


class PatientView(QWidget):
    """患者全景视图组件"""

    image_upload_requested = pyqtSignal()
    image_delete_requested = pyqtSignal(str)  # image_id
    image_preview_requested = pyqtSignal(str)  # image_id

    BORDER = "#e2e8f0"
    CARD_BG = "#ffffff"
    TEXT_MAIN = "#1e293b"
    TEXT_SECOND = "#64748b"
    PRIMARY = "#2563eb"
    PRIMARY_LIGHT = "#dbeafe"
    WARN_BG = "#fef2f2"

    def __init__(self):
        super().__init__()
        self.patient: Patient = None
        self._image_map: dict = {}  # image_id -> file_path
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 标题
        self.title_label = QLabel("患者全景视图")
        title_font = QFont("Microsoft YaHei", 16, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {self.TEXT_MAIN}; padding-bottom: 4px;")
        layout.addWidget(self.title_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #e2e8f0; }")

        # 左侧：基本信息与病历
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)

        basic_group = self._card_group("基本信息")
        basic_layout = QGridLayout(basic_group)
        basic_layout.setSpacing(10)
        self.basic_labels = {}
        basic_fields = [
            ("patient_id", "患者ID"),
            ("name", "姓名"),
            ("gender", "性别"),
            ("age", "年龄"),
            ("department", "科室"),
            ("attending_doctor", "主管医生"),
            ("admission_id", "住院号"),
        ]
        for i, (field, label) in enumerate(basic_fields):
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(f"color: {self.TEXT_SECOND}; font-size: 12px;")
            basic_layout.addWidget(lbl, i // 2, (i % 2) * 2)
            value_label = QLabel("-")
            value_label.setStyleSheet(f"color: {self.TEXT_MAIN}; font-size: 13px; font-weight: 500;")
            self.basic_labels[field] = value_label
            basic_layout.addWidget(value_label, i // 2, (i % 2) * 2 + 1)
        left_layout.addWidget(basic_group)

        left_layout.addWidget(self._section_label("主诉"))
        self.chief_complaint_edit = self._styled_text_edit()
        left_layout.addWidget(self.chief_complaint_edit)

        left_layout.addWidget(self._section_label("现病史"))
        self.present_illness_edit = self._styled_text_edit()
        left_layout.addWidget(self.present_illness_edit)

        left_layout.addWidget(self._section_label("既往史"))
        self.past_history_edit = self._styled_text_edit()
        left_layout.addWidget(self.past_history_edit)

        splitter.addWidget(left_widget)

        # 右侧：检查、用药、时间线
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        lab_group = self._card_group("检验结果")
        lab_layout = QVBoxLayout(lab_group)
        self.lab_table = QTableWidget()
        self.lab_table.setColumnCount(5)
        self.lab_table.setHorizontalHeaderLabels(["项目", "结果", "单位", "参考范围", "异常"])
        self.lab_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.lab_table.setStyleSheet(self._table_style())
        lab_layout.addWidget(self.lab_table)
        right_layout.addWidget(lab_group)

        right_layout.addWidget(self._section_label("影像报告"))
        self.imaging_edit = self._styled_text_edit()
        right_layout.addWidget(self.imaging_edit)

        # 医学影像图片（独立卡片：上传按钮 + 缩略图列表 + 预览）
        img_group = self._card_group("医学影像图片")
        img_layout = QVBoxLayout(img_group)
        img_layout.setSpacing(8)

        img_toolbar = QHBoxLayout()
        img_toolbar.setSpacing(8)
        self.btn_upload_image = QPushButton(" 上传影像")
        self.btn_upload_image.setIcon(QIcon(upload_icon(16, self.PRIMARY)))
        self.btn_upload_image.setStyleSheet(self._secondary_btn_style())
        self.btn_upload_image.setMinimumWidth(96)
        self.btn_upload_image.setMinimumHeight(32)
        self.btn_upload_image.clicked.connect(self.image_upload_requested.emit)
        img_toolbar.addWidget(self.btn_upload_image)
        self.btn_delete_image = QPushButton(" 删除选中")
        self.btn_delete_image.setStyleSheet(self._danger_btn_style())
        self.btn_delete_image.setMinimumWidth(88)
        self.btn_delete_image.setMinimumHeight(32)
        self.btn_delete_image.clicked.connect(self._on_delete_image)
        img_toolbar.addWidget(self.btn_delete_image)
        img_toolbar.addStretch()
        img_count_label = QLabel("影像列表")
        img_count_label.setStyleSheet(f"color: {self.TEXT_SECOND}; font-size: 12px;")
        img_toolbar.addWidget(img_count_label)
        img_layout.addLayout(img_toolbar)

        # 缩略图列表与预览：左右分栏，避免垂直挤压
        img_splitter = QSplitter(Qt.Orientation.Horizontal)
        img_splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        self.image_list = QListWidget()
        self.image_list.setStyleSheet(self._list_style())
        self.image_list.setIconSize(QSize(48, 48))
        self.image_list.setMinimumHeight(140)
        self.image_list.setMaximumHeight(220)
        self.image_list.itemClicked.connect(self._on_image_preview)
        self.image_list.itemDoubleClicked.connect(self._on_image_preview)
        img_splitter.addWidget(self.image_list)

        self.image_preview = QLabel("单击左侧列表项可预览\n\n支持 DICOM/JPG/PNG/BMP")
        self.image_preview.setMinimumHeight(140)
        self.image_preview.setMinimumWidth(180)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setStyleSheet(f"""
            QLabel {{ background: #f8fafc; border: 1px dashed {self.BORDER};
                     border-radius: 10px; color: {self.TEXT_SECOND};
                     font-size: 12px; padding: 12px; }}
        """)
        self.image_preview.setScaledContents(False)  # 改为手动按比例缩放，避免拉伸
        img_splitter.addWidget(self.image_preview)
        img_splitter.setSizes([260, 380])
        img_splitter.setStretchFactor(0, 2)
        img_splitter.setStretchFactor(1, 3)
        img_layout.addWidget(img_splitter)

        right_layout.addWidget(img_group)

        med_group = self._card_group("用药记录")
        med_layout = QVBoxLayout(med_group)
        self.medication_table = QTableWidget()
        self.medication_table.setColumnCount(4)
        self.medication_table.setHorizontalHeaderLabels(["药品", "剂量", "频次", "状态"])
        self.medication_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.medication_table.setStyleSheet(self._table_style())
        med_layout.addWidget(self.medication_table)
        right_layout.addWidget(med_group)

        right_layout.addWidget(self._section_label("NLP 实体提取"))
        self.nlp_edit = self._styled_text_edit()
        right_layout.addWidget(self.nlp_edit)

        splitter.addWidget(right_widget)
        splitter.setSizes([600, 800])

        layout.addWidget(splitter)

    def _card_group(self, title: str) -> QGroupBox:
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                background: {self.CARD_BG}; border: 1px solid {self.BORDER};
                border-radius: 12px; margin-top: 10px; padding-top: 8px;
                font-weight: bold; color: {self.TEXT_MAIN};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 22))
        shadow.setOffset(0, 2)
        group.setGraphicsEffect(shadow)
        return group

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {self.TEXT_MAIN}; margin-top: 4px;")
        return lbl

    def _styled_text_edit(self) -> QTextEdit:
        edit = QTextEdit()
        edit.setReadOnly(True)
        edit.setStyleSheet(f"""
            QTextEdit {{
                background: {self.CARD_BG}; border: 1px solid {self.BORDER};
                border-radius: 10px; padding: 10px; color: {self.TEXT_MAIN};
                font-size: 13px;
            }}
        """)
        return edit

    def _table_style(self) -> str:
        return f"""
            QTableWidget {{ background: {self.CARD_BG}; border: 1px solid {self.BORDER};
                            border-radius: 8px; gridline-color: {self.BORDER}; outline: none; }}
            QHeaderView::section {{ background: #f1f5f9; color: {self.TEXT_MAIN}; font-weight: bold;
                                    padding: 8px; border: none; border-bottom: 1px solid {self.BORDER}; }}
            QTableWidget::item {{ padding: 7px; border-bottom: 1px solid {self.BORDER}; }}
            QTableWidget::item:selected {{ background: #dbeafe; color: {self.TEXT_MAIN}; }}
        """

    def _list_style(self) -> str:
        return f"""
            QListWidget {{ background: white; border: 1px solid {self.BORDER}; border-radius: 8px;
                          padding: 4px; outline: none; }}
            QListWidget::item {{ padding: 8px; border-radius: 6px; }}
            QListWidget::item:selected {{ background: {self.PRIMARY_LIGHT}; color: {self.TEXT_MAIN}; }}
            QListWidget::item:hover:!selected {{ background: #f1f5f9; }}
        """

    def _secondary_btn_style(self) -> str:
        return f"""
            QPushButton {{ background: white; color: {self.TEXT_MAIN}; border: 1px solid {self.BORDER};
                          border-radius: 8px; padding: 8px 14px; font-size: 13px; }}
            QPushButton:hover {{ background: #f1f5f9; border-color: #cbd5e1; }}
        """

    def _danger_btn_style(self) -> str:
        return """
            QPushButton { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;
                          border-radius: 8px; padding: 8px 14px; font-size: 13px; }
            QPushButton:hover { background: #fee2e2; }
        """

    def set_patient(self, patient: Patient):
        self.patient = patient
        self.title_label.setText(f"患者全景视图 · {patient.name}")

        self.basic_labels["patient_id"].setText(patient.patient_id)
        self.basic_labels["name"].setText(patient.name)
        self.basic_labels["gender"].setText(patient.gender_str)
        self.basic_labels["age"].setText(str(patient.age))
        self.basic_labels["department"].setText(patient.department or "—")
        self.basic_labels["attending_doctor"].setText(patient.attending_doctor or "—")
        self.basic_labels["admission_id"].setText(patient.admission_id or "—")

        self.chief_complaint_edit.setText(patient.chief_complaint or "未记录")
        self.present_illness_edit.setText(patient.present_illness or "未记录")
        self.past_history_edit.setText(patient.past_history or "无特殊")

        self.lab_table.setRowCount(len(patient.lab_results))
        for i, lab in enumerate(patient.lab_results):
            self.lab_table.setItem(i, 0, QTableWidgetItem(lab.item_name))
            self.lab_table.setItem(i, 1, QTableWidgetItem(str(lab.value)))
            self.lab_table.setItem(i, 2, QTableWidgetItem(lab.unit))
            self.lab_table.setItem(i, 3, QTableWidgetItem(lab.reference_range))
            abnormal_item = QTableWidgetItem("是" if lab.abnormal else "否")
            if lab.abnormal:
                abnormal_item.setBackground(QColor(self.WARN_BG))
                abnormal_item.setForeground(QColor("#dc2626"))
            self.lab_table.setItem(i, 4, abnormal_item)

        imaging_text = []
        for img in patient.imaging_reports:
            imaging_text.append(
                f"【{img.modality} - {img.body_part}】\n"
                f"表现：{img.findings}\n"
                f"印象：{img.impression}\n"
            )
        self.imaging_edit.setText("\n".join(imaging_text) if imaging_text else "无影像报告")

        self.medication_table.setRowCount(len(patient.medications))
        for i, med in enumerate(patient.medications):
            self.medication_table.setItem(i, 0, QTableWidgetItem(med.drug_name))
            self.medication_table.setItem(i, 1, QTableWidgetItem(med.dosage))
            self.medication_table.setItem(i, 2, QTableWidgetItem(med.frequency))
            self.medication_table.setItem(i, 3, QTableWidgetItem(med.status))

        nlp_text = []
        all_text = f"{patient.chief_complaint} {patient.present_illness} {patient.past_history}"
        entities = NLPEngine.extract_entities(all_text)
        nlp_text.append(f"症状：{', '.join(entities['symptoms']) or '未提取'}")
        nlp_text.append(f"疾病：{', '.join(entities['diseases']) or '未提取'}")
        self.nlp_edit.setText("\n".join(nlp_text))

        # 刷新医学影像图片列表
        self.refresh_image_list()

    def refresh_image_list(self):
        """刷新影像图片列表（从 patient.medical_images 读取）"""
        self.image_list.clear()
        self._image_map.clear()
        self.image_preview.setText("选择图片可预览")
        self.image_preview.setPixmap(QPixmap())
        if not self.patient:
            return
        for img in self.patient.medical_images:
            self._image_map[img.image_id] = img.file_path
            desc = f"{img.image_type} · {img.body_part}" if img.body_part else img.image_type
            item = QListWidgetItem(image_icon(20, self.PRIMARY), f"{img.file_name}\n{desc}")
            item.setData(Qt.ItemDataRole.UserRole, img.image_id)
            item.setToolTip(img.description or img.file_name)
            self.image_list.addItem(item)

    def add_medical_image(self, image):
        """主窗口上传成功后调用，更新视图"""
        if self.patient and image:
            self.patient.medical_images.append(image)
            self.refresh_image_list()

    def _on_image_preview(self, item: QListWidgetItem):
        image_id = item.data(Qt.ItemDataRole.UserRole)
        self.image_preview_requested.emit(image_id)
        self._preview_image(image_id)

    def _preview_image(self, image_id: str):
        path = self._image_map.get(image_id)
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.image_preview.setText("无法加载该图片格式")
            self.image_preview.setPixmap(QPixmap())
            return
        # 按比例缩放至预览区域（保留边距 padding）
        avail_w = max(self.image_preview.width() - 24, 80)
        avail_h = max(self.image_preview.height() - 24, 80)
        scaled = pixmap.scaled(
            avail_w, avail_h,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_preview.setText("")
        self.image_preview.setPixmap(scaled)

    def _on_delete_image(self):
        item = self.image_list.currentItem()
        if not item:
            QMessageBox.warning(self, "警告", "请先选中一张图片")
            return
        image_id = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "确认删除", "确定删除该影像图片？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.image_delete_requested.emit(image_id)

    def remove_medical_image(self, image_id: str):
        """主窗口删除成功后调用，更新视图"""
        if self.patient:
            self.patient.medical_images = [img for img in self.patient.medical_images if img.image_id != image_id]
        self._image_map.pop(image_id, None)
        self.refresh_image_list()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 窗口大小变化时重新缩放当前预览图
        item = self.image_list.currentItem()
        if item:
            self._preview_image(item.data(Qt.ItemDataRole.UserRole))
