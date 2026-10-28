"""
虚拟会诊视图

设计要点：
- 卡片式表单布局，专业蓝色主按钮
- 专家列表采用勾选+卡片样式
- 历史会诊列表采用专业表格样式
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QGroupBox, QGridLayout,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..core.consultation import ConsultationEngine
from ..core.patient import Patient, Priority


class ConsultationView(QWidget):
    """会诊视图组件"""

    consultation_requested = pyqtSignal(str, list)
    review_requested = pyqtSignal(str)  # 医生点击"会诊审核"时发出

    BORDER = "#e2e8f0"
    CARD_BG = "#ffffff"
    TEXT_MAIN = "#1e293b"
    TEXT_SECOND = "#64748b"
    PRIMARY = "#2563eb"
    PRIMARY_HOVER = "#1d4ed8"

    def __init__(self, engine: ConsultationEngine):
        super().__init__()
        self.engine = engine
        self.patient: Patient = None
        self.current_consultation_id: str = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel("虚拟会诊")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.TEXT_MAIN};")
        layout.addWidget(title)

        # 会诊申请表单
        form_group = self._card_group("会诊申请")
        form_layout = QGridLayout(form_group)
        form_layout.setSpacing(12)

        self.patient_id_edit = QLineEdit()
        self.patient_id_edit.setReadOnly(True)
        self.patient_name_edit = QLineEdit()
        self.patient_name_edit.setReadOnly(True)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["MDT多学科会诊", "常规会诊", "急诊会诊"])
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["急诊", "常规", "疑难"])
        self.question_edit = QTextEdit()
        self.question_edit.setPlaceholderText("请描述需要会诊解决的临床问题...")
        self.question_edit.setMaximumHeight(90)

        for edit in (self.patient_id_edit, self.patient_name_edit):
            edit.setStyleSheet(f"""
                QLineEdit {{ background: #f8fafc; border: 1px solid {self.BORDER};
                            border-radius: 8px; padding: 8px 10px; color: {self.TEXT_MAIN}; }}
            """)
        self.type_combo.setStyleSheet(self._combo_style())
        self.priority_combo.setStyleSheet(self._combo_style())
        self.question_edit.setStyleSheet(f"""
            QTextEdit {{ background: white; border: 1px solid {self.BORDER};
                        border-radius: 10px; padding: 10px; color: {self.TEXT_MAIN}; font-size: 13px; }}
            QTextEdit:focus {{ border: 2px solid {self.PRIMARY}; padding: 9px; }}
        """)

        form_layout.addWidget(self._form_label("患者ID:"), 0, 0)
        form_layout.addWidget(self.patient_id_edit, 0, 1)
        form_layout.addWidget(self._form_label("患者姓名:"), 0, 2)
        form_layout.addWidget(self.patient_name_edit, 0, 3)
        form_layout.addWidget(self._form_label("会诊类型:"), 1, 0)
        form_layout.addWidget(self.type_combo, 1, 1)
        form_layout.addWidget(self._form_label("优先级:"), 1, 2)
        form_layout.addWidget(self.priority_combo, 1, 3)
        form_layout.addWidget(self._form_label("临床问题:"), 2, 0, Qt.AlignmentFlag.AlignTop)
        form_layout.addWidget(self.question_edit, 2, 1, 1, 3)
        layout.addWidget(form_group)

        # 智能体选择
        agent_group = self._card_group("参与会诊专家")
        agent_layout = QVBoxLayout(agent_group)
        agent_layout.setSpacing(12)

        agent_header = QHBoxLayout()
        agent_header.addWidget(self._section_label("选择参与会诊的 AI 专家"))
        agent_header.addStretch()
        self.btn_auto_select = QPushButton("智能推荐")
        self.btn_auto_select.setStyleSheet(self._secondary_btn_style())
        self.btn_auto_select.clicked.connect(self._auto_select_agents)
        agent_header.addWidget(self.btn_auto_select)
        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.setStyleSheet(self._secondary_btn_style())
        self.btn_select_all.clicked.connect(self._select_all_agents)
        agent_header.addWidget(self.btn_select_all)
        agent_layout.addLayout(agent_header)

        self.agent_list = QListWidget()
        self.agent_list.setStyleSheet(f"""
            QListWidget {{ background: white; border: 1px solid {self.BORDER}; border-radius: 10px;
                           padding: 6px; outline: none; }}
            QListWidget::item {{ padding: 10px; border-bottom: 1px solid #f1f5f9; border-radius: 6px; }}
            QListWidget::item:hover {{ background: #f8fafc; }}
        """)
        self._load_agents()
        agent_layout.addWidget(self.agent_list)

        # 操作按钮
        button_layout = QHBoxLayout()
        self.btn_start = QPushButton("开始虚拟会诊")
        self.btn_start.setStyleSheet(self._primary_btn_style())
        self.btn_start.clicked.connect(self._start_consultation)
        button_layout.addWidget(self.btn_start)

        self.btn_review = QPushButton("会诊审核")
        self.btn_review.setStyleSheet(self._secondary_btn_style())
        self.btn_review.clicked.connect(self._open_review)
        self.btn_review.setEnabled(False)
        button_layout.addWidget(self.btn_review)
        button_layout.addStretch()
        agent_layout.addLayout(button_layout)

        layout.addWidget(agent_group)

        # 本次会话历史（与"我的工作空间"归档报告区分：此处为引擎内存中的会诊请求）
        history_group = self._card_group("本次会话历史")
        history_layout = QVBoxLayout(history_group)
        self.history_list = QListWidget()
        self.history_list.setStyleSheet(f"""
            QListWidget {{ background: white; border: 1px solid {self.BORDER}; border-radius: 10px;
                           padding: 6px; outline: none; }}
            QListWidget::item {{ padding: 9px 12px; border-bottom: 1px solid #f1f5f9; }}
            QListWidget::item:selected {{ background: #dbeafe; color: {self.TEXT_MAIN}; }}
        """)
        self.history_list.itemClicked.connect(self._on_history_selected)
        history_layout.addWidget(self.history_list)
        layout.addWidget(history_group)

        layout.addStretch()

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
        lbl.setStyleSheet(f"color: {self.TEXT_MAIN};")
        return lbl

    def _form_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {self.TEXT_SECOND}; font-size: 12px;")
        return lbl

    def _combo_style(self) -> str:
        return f"""
            QComboBox {{ background: white; border: 1px solid {self.BORDER}; border-radius: 8px;
                        padding: 8px 10px; color: {self.TEXT_MAIN}; }}
            QComboBox:focus {{ border: 2px solid {self.PRIMARY}; padding: 7px 9px; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
        """

    def _primary_btn_style(self) -> str:
        return f"""
            QPushButton {{ background: {self.PRIMARY}; color: white; border: none;
                          border-radius: 10px; padding: 12px 24px; font-size: 14px; font-weight: bold; }}
            QPushButton:hover {{ background: {self.PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background: #1e40af; }}
            QPushButton:disabled {{ background: #93c5fd; }}
        """

    def _secondary_btn_style(self) -> str:
        return f"""
            QPushButton {{ background: white; color: {self.TEXT_MAIN}; border: 1px solid {self.BORDER};
                          border-radius: 8px; padding: 8px 16px; font-size: 13px; }}
            QPushButton:hover {{ background: #f1f5f9; }}
        """

    def _load_agents(self):
        agents = self.engine.agent_registry.list_agents()
        for agent in agents:
            item = QListWidgetItem(f"{agent['name']}  ·  {agent['specialty']}")
            item.setData(Qt.ItemDataRole.UserRole, agent["agent_id"])
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setFont(QFont("Microsoft YaHei", 11))
            self.agent_list.addItem(item)

    def set_patient(self, patient: Patient):
        self.patient = patient
        self.patient_id_edit.setText(patient.patient_id)
        self.patient_name_edit.setText(patient.name)

    def start_new_consultation(self, patient: Patient):
        self.set_patient(patient)
        self.question_edit.clear()
        self.current_consultation_id = None
        self.btn_review.setEnabled(False)
        self._clear_agent_selection()

    def _clear_agent_selection(self):
        for i in range(self.agent_list.count()):
            self.agent_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _auto_select_agents(self):
        if not self.patient:
            QMessageBox.warning(self, "警告", "请先加载患者")
            return
        recommendations = self.engine.agent_registry.recommend_agents(self.patient)
        recommended_ids = {rec["agent_id"] for rec in recommendations}
        for i in range(self.agent_list.count()):
            item = self.agent_list.item(i)
            agent_id = item.data(Qt.ItemDataRole.UserRole)
            item.setCheckState(Qt.CheckState.Checked if agent_id in recommended_ids else Qt.CheckState.Unchecked)

    def _select_all_agents(self):
        for i in range(self.agent_list.count()):
            self.agent_list.item(i).setCheckState(Qt.CheckState.Checked)

    def _get_selected_agents(self) -> list:
        selected = []
        for i in range(self.agent_list.count()):
            item = self.agent_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected

    def _start_consultation(self):
        if not self.patient:
            QMessageBox.warning(self, "警告", "请先加载患者")
            return
        selected_agents = self._get_selected_agents()
        if not selected_agents:
            QMessageBox.warning(self, "警告", "请至少选择一位参与会诊的专家")
            return

        consultation_type = self.type_combo.currentText()
        priority_text = self.priority_combo.currentText()
        priority_map = {"急诊": Priority.EMERGENCY, "常规": Priority.ROUTINE, "疑难": Priority.MDT}
        priority = priority_map.get(priority_text, Priority.ROUTINE)

        self.current_consultation_id = self.engine.request_consultation(
            patient_id=self.patient.patient_id,
            clinical_question=self.question_edit.toPlainText(),
            consultation_type=consultation_type,
            priority=priority,
            requested_agents=selected_agents,
            attending_doctor=self.patient.attending_doctor,
            department=self.patient.department
        )

        self.consultation_requested.emit(self.current_consultation_id, selected_agents)
        self.btn_review.setEnabled(True)
        self._refresh_history()

    def _open_review(self):
        if self.current_consultation_id:
            self.review_requested.emit(self.current_consultation_id)

    def _refresh_history(self):
        self.history_list.clear()
        for req in self.engine.get_consultation_requests():
            item_text = f"{req['consultation_id']}  |  {req['patient_id']}  |  {req['status']}  |  {req['consultation_type']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, req["consultation_id"])
            self.history_list.addItem(item)

    def _on_history_selected(self, item: QListWidgetItem):
        self.current_consultation_id = item.data(Qt.ItemDataRole.UserRole)
        self.btn_review.setEnabled(True)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self._refresh_history()
        except Exception:
            pass
