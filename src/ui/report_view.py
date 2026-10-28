"""
会诊报告视图

设计要点：
- 卡片式报告信息头部
- 鉴别诊断表格专业样式
- 详细报告使用富文本 HTML，层次清晰
- 医生提交审核按钮（审核通过/驳回已移入审核工作台详情）
"""
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QGroupBox,
    QLineEdit, QFormLayout, QDialog, QDialogButtonBox,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..core.moderator import ConsultationReport
from ..core.consultation import ConsultationEngine


class ReportView(QWidget):
    """会诊报告视图组件

    可通过 show_title 控制是否显示顶部"会诊报告"标题，便于嵌入到其它页面。
    """

    report_submitted = pyqtSignal(str)  # 医生提交审核时发出

    BORDER = "#e2e8f0"
    CARD_BG = "#ffffff"
    TEXT_MAIN = "#1e293b"
    TEXT_SECOND = "#64748b"
    PRIMARY = "#2563eb"
    PRIMARY_HOVER = "#1d4ed8"
    SUCCESS = "#0d904f"
    WARNING = "#e8710a"

    def __init__(self, show_title: bool = True):
        super().__init__()
        self.report: ConsultationReport = None
        self._engine = None
        self._show_title = show_title
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self.title_label = QLabel("会诊报告")
        self.title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {self.TEXT_MAIN};")
        self.title_label.setVisible(self._show_title)
        layout.addWidget(self.title_label)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self.btn_save_json = QPushButton("保存为 JSON")
        self.btn_save_json.setStyleSheet(self._secondary_btn_style())
        self.btn_save_json.clicked.connect(self._save_json)
        toolbar.addWidget(self.btn_save_json)

        self.btn_save_md = QPushButton("保存为 Markdown")
        self.btn_save_md.setStyleSheet(self._secondary_btn_style())
        self.btn_save_md.clicked.connect(self._save_markdown)
        toolbar.addWidget(self.btn_save_md)

        self.btn_submit_review = QPushButton("提交审核")
        self.btn_submit_review.setStyleSheet(self._warning_btn_style())
        self.btn_submit_review.clicked.connect(self._submit_for_review)
        toolbar.addWidget(self.btn_submit_review)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 报告基本信息
        info_group = self._card_group("报告信息")
        info_layout = QVBoxLayout(info_group)
        self.info_label = QLabel("暂无报告")
        self.info_label.setStyleSheet(f"color: {self.TEXT_SECOND}; font-size: 13px;")
        info_layout.addWidget(self.info_label)
        layout.addWidget(info_group)

        # 鉴别诊断表
        diag_group = self._card_group("鉴别诊断")
        diag_layout = QVBoxLayout(diag_group)
        self.diagnosis_table = QTableWidget()
        self.diagnosis_table.setColumnCount(5)
        self.diagnosis_table.setHorizontalHeaderLabels(
            ["排序", "诊断", "置信度", "证据等级", "支持专科数"]
        )
        self.diagnosis_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.diagnosis_table.setStyleSheet(self._table_style())
        diag_layout.addWidget(self.diagnosis_table)
        layout.addWidget(diag_group)

        # 报告内容
        detail_group = self._card_group("详细报告")
        detail_layout = QVBoxLayout(detail_group)
        self.report_edit = QTextEdit()
        self.report_edit.setReadOnly(True)
        self.report_edit.setStyleSheet(f"""
            QTextEdit {{ background: white; border: 1px solid {self.BORDER}; border-radius: 10px;
                        padding: 12px; color: {self.TEXT_MAIN}; font-size: 13px; }}
        """)
        detail_layout.addWidget(self.report_edit)
        layout.addWidget(detail_group)

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

    def _table_style(self) -> str:
        return f"""
            QTableWidget {{ background: white; border: 1px solid {self.BORDER}; border-radius: 8px;
                            gridline-color: {self.BORDER}; outline: none; }}
            QHeaderView::section {{ background: #f1f5f9; color: {self.TEXT_MAIN}; font-weight: bold;
                                    padding: 9px; border: none; border-bottom: 1px solid {self.BORDER}; }}
            QTableWidget::item {{ padding: 8px; border-bottom: 1px solid {self.BORDER}; }}
            QTableWidget::item:selected {{ background: #dbeafe; color: {self.TEXT_MAIN}; }}
        """

    def _primary_btn_style(self) -> str:
        return f"""
            QPushButton {{ background: {self.PRIMARY}; color: white; border: none;
                          border-radius: 8px; padding: 9px 18px; font-size: 13px; font-weight: bold; }}
            QPushButton:hover {{ background: {self.PRIMARY_HOVER}; }}
        """

    def _secondary_btn_style(self) -> str:
        return f"""
            QPushButton {{ background: white; color: {self.TEXT_MAIN}; border: 1px solid {self.BORDER};
                          border-radius: 8px; padding: 9px 18px; font-size: 13px; }}
            QPushButton:hover {{ background: #f1f5f9; }}
        """

    def _success_btn_style(self) -> str:
        return f"""
            QPushButton {{ background: {self.SUCCESS}; color: white; border: none;
                          border-radius: 8px; padding: 9px 18px; font-size: 13px; font-weight: bold; }}
            QPushButton:hover {{ background: #0b7a3f; }}
        """

    def _warning_btn_style(self) -> str:
        return f"""
            QPushButton {{ background: {self.WARNING}; color: white; border: none;
                          border-radius: 8px; padding: 9px 18px; font-size: 13px; font-weight: bold; }}
            QPushButton:hover {{ background: #c5610a; }}
        """

    def set_engine(self, engine: ConsultationEngine):
        self._engine = engine

    def set_report(self, report: ConsultationReport):
        self.report = report
        if report is None:
            self.clear_report()
            return

        status_color = "#0d904f" if report.status == "APPROVED" else self.PRIMARY
        info_text = (
            f"会诊编号：<b>{report.consultation_id}</b>　|　"
            f"患者：<b>{report.patient_name}</b>（{report.patient_id}）　|　"
            f"类型：{report.consultation_type}　|　"
            f"状态：<span style='color:{status_color};font-weight:bold;'>{report.status}</span>　|　"
            f"生成时间：{report.created_at}"
        )
        self.info_label.setText(info_text)

        self.diagnosis_table.setRowCount(len(report.differential_diagnosis))
        for i, diag in enumerate(report.differential_diagnosis):
            self.diagnosis_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.diagnosis_table.setItem(i, 1, QTableWidgetItem(diag.get("disease", "")))
            conf = diag.get("confidence", 0)
            self.diagnosis_table.setItem(i, 2, QTableWidgetItem(f"{conf:.1%}"))
            self.diagnosis_table.setItem(i, 3, QTableWidgetItem(diag.get("evidence_level", "D")))
            self.diagnosis_table.setItem(i, 4, QTableWidgetItem(str(diag.get("supporting_specialties", 1))))

        self.report_edit.setHtml(self._report_to_html(report))

    def clear_report(self):
        """清空当前展示的报告内容"""
        self.report = None
        self.info_label.setText("暂无报告")
        self.diagnosis_table.setRowCount(0)
        self.report_edit.clear()

    def set_submit_visible(self, visible: bool):
        """控制"提交审核"按钮是否可见（用于只读场景）"""
        self.btn_submit_review.setVisible(visible)

    def _report_to_html(self, report: ConsultationReport) -> str:
        html = [f"""
            <style>
                body {{ font-family: 'Microsoft YaHei', sans-serif; color: {self.TEXT_MAIN}; line-height: 1.6; }}
                h2 {{ color: {self.PRIMARY}; border-bottom: 2px solid #dbeafe; padding-bottom: 6px; margin-top: 0; }}
                h3 {{ color: #334155; margin-top: 18px; margin-bottom: 8px; }}
                li {{ margin: 4px 0; }}
                strong {{ color: #1e293b; }}
            </style>
            <h2>会诊报告详情</h2>
        """]

        html.append("<h3>一、参与会诊专家</h3><ul>")
        for agent in report.participating_agents:
            html.append(f"<li><strong>{agent['name']}</strong>（{agent['specialty']}）</li>")
        html.append("</ul>")

        html.append("<h3>二、推荐检查</h3><ul>")
        for rec in report.recommended_tests:
            html.append(f"<li>{rec.content}（证据等级：{rec.evidence_level.value}）</li>")
        html.append("</ul>")

        html.append("<h3>三、治疗方案</h3><ul>")
        for rec in report.treatment_plan:
            html.append(f"<li>{rec.content}（{rec.strength.value}，证据等级：{rec.evidence_level.value}）</li>")
        html.append("</ul>")

        html.append("<h3>四、用药建议</h3><ul>")
        for rec in report.medication_suggestions:
            html.append(f"<li>{rec.content}</li>")
        html.append("</ul>")

        html.append(f"<h3>五、风险评估</h3><p>{report.risk_assessment}</p>")

        html.append("<h3>六、随访计划</h3><ul>")
        for item in report.follow_up_plan:
            html.append(f"<li>{item}</li>")
        html.append("</ul>")

        if report.uncertainties:
            html.append("<h3>七、不确定性声明</h3><ul>")
            for item in report.uncertainties:
                html.append(f"<li>{item}</li>")
            html.append("</ul>")

        html.append(f"<h3>八、最终结论</h3><p style='font-size:15px;'><strong>{report.final_conclusion}</strong></p>")

        return "\n".join(html)

    def _save_json(self):
        if not self.report:
            QMessageBox.warning(self, "警告", "没有可保存的报告")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存报告", f"{self.report.consultation_id}.json", "JSON文件 (*.json)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.report.to_dict(), f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "成功", "报告已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def _save_markdown(self):
        if not self.report:
            QMessageBox.warning(self, "警告", "没有可保存的报告")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存报告", f"{self.report.consultation_id}.md", "Markdown文件 (*.md)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.report.to_markdown())
                QMessageBox.information(self, "成功", "报告已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def _submit_for_review(self):
        """医生点击"提交审核"：触发主窗口选择审核员并提交到审核队列"""
        if not self.report:
            QMessageBox.warning(self, "警告", "没有可提交的报告")
            return
        status = self.report.status
        if status in ("APPROVED",):
            QMessageBox.information(self, "提示", "该报告已审核通过，无需再次提交")
            return
        if status == "PENDING_REVIEW":
            QMessageBox.information(self, "提示", "该报告已提交审核，请等待审核员处理")
            return

        self.report_submitted.emit(self.report.consultation_id)


class ApproveReviewDialog(QDialog):
    """审核工作台 - 审核通过对话框"""

    def __init__(self, parent, entry: dict):
        super().__init__(parent)
        self.entry = entry
        self.setWindowTitle("审核通过")
        self.setMinimumWidth(460)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            f"<b>会诊编号：</b>{self.entry.get('consultation_id', '')}<br>"
            f"<b>患者：</b>{self.entry.get('patient_name', '')}（{self.entry.get('patient_id', '')}）<br>"
            f"<b>申请医生：</b>{self.entry.get('doctor_name', '')}　"
            f"<b>科室：</b>{self.entry.get('department', '')}　"
            f"<b>类型：</b>{self.entry.get('consultation_type', '')}"
        )
        info.setStyleSheet("background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px; font-size: 13px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("可选：填写审核意见")
        self.comment_edit.setStyleSheet("""
            QLineEdit { border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; }
            QLineEdit:focus { border: 2px solid #2563eb; padding: 7px 9px; }
        """)
        form.addRow("审核意见：", self.comment_edit)
        layout.addLayout(form)

        tip = QLabel("审核通过后报告状态将变为 APPROVED 并归档，操作会被记录到审计日志。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(tip)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确认通过")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class RejectReviewDialog(QDialog):
    """审核工作台 - 驳回对话框"""

    def __init__(self, parent, entry: dict):
        super().__init__(parent)
        self.entry = entry
        self.setWindowTitle("驳回报告")
        self.setMinimumWidth(460)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            f"<b>会诊编号：</b>{self.entry.get('consultation_id', '')}<br>"
            f"<b>患者：</b>{self.entry.get('patient_name', '')}（{self.entry.get('patient_id', '')}）<br>"
            f"<b>申请医生：</b>{self.entry.get('doctor_name', '')}"
        )
        info.setStyleSheet("background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 12px; font-size: 13px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("必填：请填写驳回原因")
        self.comment_edit.setStyleSheet("""
            QLineEdit { border: 1px solid #fecaca; border-radius: 8px; padding: 8px 10px; }
            QLineEdit:focus { border: 2px solid #dc2626; padding: 7px 9px; }
        """)
        form.addRow("驳回原因：", self.comment_edit)
        layout.addLayout(form)

        tip = QLabel("驳回后报告将退回给申请医生，医生可修改后重新提交审核。操作会被记录到审计日志。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #dc2626; font-size: 11px;")
        layout.addWidget(tip)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确认驳回")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
