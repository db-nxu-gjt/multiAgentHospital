"""
医学知识图谱查看对话框
"""
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..core.knowledge_graph import MedicalKnowledgeGraph


class KnowledgeGraphDialog(QDialog):
    """知识图谱查看对话框"""

    def __init__(self, knowledge_graph: MedicalKnowledgeGraph, parent=None):
        super().__init__(parent)
        self.knowledge_graph = knowledge_graph
        self.setWindowTitle("医学知识图谱")
        self.setMinimumSize(900, 700)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("医学知识图谱浏览器")
        title_font = QFont("Microsoft YaHei", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 搜索
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("症状查询："))
        self.symptom_input = QLineEdit()
        self.symptom_input.setPlaceholderText("输入症状，多个用逗号分隔，如：咳嗽,呼吸困难")
        search_layout.addWidget(self.symptom_input)
        self.btn_search = QPushButton("查询可能疾病")
        self.btn_search.clicked.connect(self._search_diseases)
        search_layout.addWidget(self.btn_search)
        layout.addLayout(search_layout)

        # 疾病查询
        disease_layout = QHBoxLayout()
        disease_layout.addWidget(QLabel("疾病查询："))
        self.disease_input = QLineEdit()
        self.disease_input.setPlaceholderText("输入疾病名称，如：慢性阻塞性肺疾病")
        disease_layout.addWidget(self.disease_input)
        self.btn_disease = QPushButton("查询相关症状/检查")
        self.btn_disease.clicked.connect(self._search_disease_details)
        disease_layout.addWidget(self.btn_disease)
        layout.addLayout(disease_layout)

        # 结果表
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["项目", "类型", "置信度/权重", "说明"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.result_table)

        # 统计信息
        stats = (
            f"实体总数：{len(self.knowledge_graph.entities)} | "
            f"关系总数：{len(self.knowledge_graph.relations)}"
        )
        layout.addWidget(QLabel(stats))

        # 详情文本
        self.detail_edit = QTextEdit()
        self.detail_edit.setReadOnly(True)
        layout.addWidget(QLabel("详细信息"))
        layout.addWidget(self.detail_edit)

        # 关闭按钮
        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close)

    def _search_diseases(self):
        symptoms_text = self.symptom_input.text().strip()
        if not symptoms_text:
            QMessageBox.warning(self, "警告", "请输入症状")
            return

        symptoms = [s.strip() for s in symptoms_text.split(",") if s.strip()]
        results = self.knowledge_graph.find_diseases_by_symptoms(symptoms, top_k=10)

        self.result_table.setRowCount(len(results))
        for i, result in enumerate(results):
            self.result_table.setItem(i, 0, QTableWidgetItem(result["disease"]))
            self.result_table.setItem(i, 1, QTableWidgetItem("疾病"))
            self.result_table.setItem(i, 2, QTableWidgetItem(f"{result['confidence']:.1%}"))
            self.result_table.setItem(i, 3, QTableWidgetItem(
                f"匹配症状：{', '.join(result['matched_symptoms'])}"
            ))

        self.detail_edit.setText(
            f"根据症状 {'、'.join(symptoms)} 共找到 {len(results)} 种可能疾病"
        )

    def _search_disease_details(self):
        disease_name = self.disease_input.text().strip()
        if not disease_name:
            QMessageBox.warning(self, "警告", "请输入疾病名称")
            return

        symptoms = self.knowledge_graph.find_related_symptoms(disease_name)
        tests = self.knowledge_graph.find_recommended_tests(disease_name)

        # 清空表格，显示症状和检查
        rows = len(symptoms) + len(tests)
        self.result_table.setRowCount(rows)
        row = 0
        for symptom in symptoms:
            self.result_table.setItem(row, 0, QTableWidgetItem(symptom))
            self.result_table.setItem(row, 1, QTableWidgetItem("症状"))
            self.result_table.setItem(row, 2, QTableWidgetItem("-"))
            self.result_table.setItem(row, 3, QTableWidgetItem("该疾病的典型症状"))
            row += 1

        for test in tests:
            self.result_table.setItem(row, 0, QTableWidgetItem(test))
            self.result_table.setItem(row, 1, QTableWidgetItem("检查"))
            self.result_table.setItem(row, 2, QTableWidgetItem("-"))
            self.result_table.setItem(row, 3, QTableWidgetItem("推荐检查项目"))
            row += 1

        detail_text = f"疾病：{disease_name}\n\n"
        detail_text += f"典型症状：{', '.join(symptoms) if symptoms else '未找到'}\n\n"
        detail_text += f"推荐检查：{', '.join(tests) if tests else '未找到'}"
        self.detail_edit.setText(detail_text)
