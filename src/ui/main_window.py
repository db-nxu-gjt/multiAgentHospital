"""
医院虚拟会诊系统 - 桌面主窗口（医生工作台）

角色空间分配：
- 管理员（ADMIN）：大屏 + 系统管理 + 系统集成 + 数据安全审计 + 质控统计报表
  （系统集成/数据安全审计/质控统计报表与"系统管理"同级，不直接参与诊疗）
- 医生（DOCTOR）：大屏 + 患者管理 + 虚拟会诊（融合会诊报告内容）+ 我的工作空间
- 审核员（REVIEWER）：大屏 + 审核工作台（融合报告详情与审核操作）+ 审核记录

界面设计：
- 使用自绘矢量图标替代 emoji，专业配色，卡片阴影，圆角，统一间距
- 顶部回退按钮 + 头像 + 用户信息 + 操作按钮
- 左侧导航：图标 + 文字，选中高亮
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QSplitter, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog,
    QProgressDialog, QApplication, QListWidget, QListWidgetItem,
    QStackedWidget, QFrame, QFormLayout, QLineEdit,
    QDialog, QDialogButtonBox, QComboBox
)

from ..core.consultation import ConsultationEngine
from ..core.medical_record import MedicalRecordIntegrator
from ..core.knowledge_graph import build_default_knowledge_graph
from ..core.patient import Patient
from ..core.user import User, Role, UserManager, get_user_manager
from ..core.session import UserSession, AuditLogger, GlobalConsultationIndex, ReviewQueue
from ..adapters.base import MockHospitalAdapter
from .patient_view import PatientView
from .consultation_view import ConsultationView
from .report_view import ReportView, ApproveReviewDialog, RejectReviewDialog
from .admin_view import AdminPanel
from .icons import (
    avatar_icon, dashboard_icon, patient_icon, stethoscope_icon,
    report_icon, folder_icon, gear_icon, user_icon, logout_icon,
    upload_icon, image_icon, back_icon, link_icon, shield_icon, chart_icon
)


class AppContext:
    """应用上下文 - 封装登录后共享的资源"""

    def __init__(self, user: User):
        self.user = user
        self.user_manager: UserManager = get_user_manager()
        self.audit_logger = AuditLogger()
        self.user_session = UserSession(user_id=user.user_id)
        self.global_index = GlobalConsultationIndex()
        self.review_queue = ReviewQueue()

    def refresh_user(self) -> User:
        u = self.user_manager.get_user(self.user.user_id)
        if u:
            self.user = u
        return self.user


class ConsultationWorker(QThread):
    """会诊执行工作线程"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, engine: ConsultationEngine, consultation_id: str,
                 patient: Patient = None, selected_agents: list = None):
        super().__init__()
        self.engine = engine
        self.consultation_id = consultation_id
        self.patient = patient
        self.selected_agents = selected_agents or []

    def run(self):
        try:
            self.progress.emit("正在整合病历数据...")
            self.progress.emit("多智能体正在分析...")
            report = self.engine.run_consultation(
                self.consultation_id,
                patient=self.patient,
                selected_agent_ids=self.selected_agents if self.selected_agents else None
            )
            self.finished.emit(report)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """主窗口 - 医生工作台"""

    logout_requested = pyqtSignal()

    # 专业配色
    PRIMARY = "#2563eb"
    PRIMARY_HOVER = "#1d4ed8"
    PRIMARY_LIGHT = "#dbeafe"
    NAV_BG = "#1e293b"
    NAV_HOVER = "#334155"
    NAV_SELECTED = "#2563eb"
    TEXT_MAIN = "#1e293b"
    TEXT_SECOND = "#64748b"
    BORDER = "#e2e8f0"
    BG = "#f8fafc"
    CARD_BG = "#ffffff"

    def __init__(self, user: User):
        super().__init__()
        self.ctx = AppContext(user)

        self.setWindowTitle("医院虚拟会诊系统 (VCS)")
        self.setMinimumSize(1440, 900)

        self.knowledge_graph = build_default_knowledge_graph()
        self.integrator = MedicalRecordIntegrator()
        self.engine = ConsultationEngine(
            integrator=self.integrator,
            knowledge_graph=self.knowledge_graph
        )

        self.current_patient: Optional[Patient] = None
        self.current_consultation_id: Optional[str] = None
        self._sample_patients: list = []
        self.worker: Optional[ConsultationWorker] = None
        self.progress_dialog: Optional[QProgressDialog] = None

        self._nav_items: List[Tuple[str, str, QWidget, QPixmap]] = []  # (key, text, page, icon)

        # 导航历史（用于"返回"按钮）
        self._nav_history: List[str] = []
        self._current_page_key: Optional[str] = None
        self._suppress_history = False

        self._init_ui()
        try:
            self._load_sample_data(silent=True)
        except Exception as e:
            self._set_status(f"初始化加载失败：{e}")
        self._refresh_workspace_lists()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(220)
        self.nav_list.setStyleSheet(f"""
            QListWidget {{
                background: {self.NAV_BG};
                border: none;
                outline: none;
                padding: 8px 0;
            }}
            QListWidget::item {{
                color: #cbd5e1;
                padding: 15px 18px;
                border: none;
                font-size: 16px;
                margin: 2px 10px;
                border-radius: 8px;
            }}
            QListWidget::item:selected {{
                background: {self.NAV_SELECTED};
                color: white;
            }}
            QListWidget::item:hover:!selected {{ background: {self.NAV_HOVER}; }}
        """)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        body_layout.addWidget(self.nav_list)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {self.BG};")
        body_layout.addWidget(self.stack, 1)

        # 子视图（先创建，供各页面嵌入使用）
        self.patient_view = PatientView()
        self.consultation_view = ConsultationView(self.engine)

        # 构建页面（医生/审核员按角色构建）
        role = self.ctx.user.role
        self.page_dashboard = self._build_dashboard_page()
        self.page_patient = self._build_patient_page()
        self.page_workspace = self._build_workspace_page()
        if role == Role.DOCTOR:
            # 医生"虚拟会诊"页仅保留会诊表单；报告内容移入"会诊审核"对话框
            self.page_consultation = self.consultation_view
        else:
            self.page_consultation = QWidget()
        if role == Role.REVIEWER:
            self.page_review_workbench = self._build_review_workbench_page()
            self.page_review_history = self._build_review_history_page()
        else:
            self.page_review_workbench = QWidget()
            self.page_review_history = QWidget()

        # AdminPanel 初始化独立保护 - 即使后台管理模块加载失败，主窗口仍可用
        try:
            self.admin_panel = AdminPanel(self.ctx)
        except Exception as e:
            # 降级：创建占位 widget 显示错误信息，便于排查
            import traceback
            err_detail = traceback.format_exc()
            fallback = QWidget()
            fb_layout = QVBoxLayout(fallback)
            fb_layout.setContentsMargins(40, 40, 40, 40)
            err_title = QLabel("后台管理模块加载失败")
            err_title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
            err_title.setStyleSheet("color: #dc2626;")
            fb_layout.addWidget(err_title)
            err_msg = QLabel(f"错误信息：\n{e}\n\n详细堆栈：\n{err_detail}\n\n"
                             f"请检查程序完整性或联系系统管理员重新打包。")
            err_msg.setWordWrap(True)
            err_msg.setStyleSheet("color: #1e293b; font-size: 13px; padding: 12px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px;")
            fb_layout.addWidget(err_msg)
            fb_layout.addStretch()
            self.admin_panel = fallback
        self.admin_panel.setVisible(False)  # 仅管理员可见
        self.page_admin = self.admin_panel

        # 管理员额外页面：系统集成 / 数据安全审计 / 质控统计报表（与系统管理同级）
        if role == Role.ADMIN and hasattr(self.admin_panel, "get_integration_page"):
            self.page_integration = self._build_admin_standalone_page(
                "系统集成", self.admin_panel.get_integration_page())
            self.page_security = self._build_admin_standalone_page(
                "数据安全审计", self.admin_panel.get_security_page())
            self.page_quality = self._build_admin_standalone_page(
                "质控统计报表", self.admin_panel.get_quality_page())
        else:
            self.page_integration = QWidget()
            self.page_security = QWidget()
            self.page_quality = QWidget()

        # 将页面加入 stack（导航按 widget 定位，与索引顺序无关）
        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_patient)
        self.stack.addWidget(self.page_consultation)
        self.stack.addWidget(self.page_workspace)
        self.stack.addWidget(self.page_review_workbench)
        self.stack.addWidget(self.page_review_history)
        self.stack.addWidget(self.page_admin)
        self.stack.addWidget(self.page_integration)
        self.stack.addWidget(self.page_security)
        self.stack.addWidget(self.page_quality)

        self._build_patient_page_content()

        self.consultation_view.consultation_requested.connect(self._on_consultation_requested)
        self.consultation_view.review_requested.connect(self._open_consultation_review)
        self.patient_view.image_upload_requested.connect(self._upload_medical_image)
        self.patient_view.image_delete_requested.connect(self._delete_medical_image)

        root.addWidget(body, 1)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(f"color: {self.TEXT_SECOND}; padding: 6px 18px; background: white; border-top: 1px solid {self.BORDER};")
        root.addWidget(self.status_label)

        self._build_nav_items()

    def _build_admin_standalone_page(self, title_text: str, content: QWidget) -> QWidget:
        """将后台管理的独立模块包装成带标题的顶层页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel(title_text)
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.TEXT_MAIN};")
        layout.addWidget(title)
        layout.addWidget(content, 1)
        return page

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet(f"""
            QFrame {{ background: {self.CARD_BG}; border-bottom: 1px solid {self.BORDER}; }}
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        # 左侧标题
        brand = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(avatar_icon(36, "VCS", self.PRIMARY))
        brand.addWidget(icon_label)
        brand.addSpacing(10)
        title = QLabel("医院虚拟会诊系统")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.TEXT_MAIN};")
        brand.addWidget(title)
        brand.addStretch()
        layout.addLayout(brand)

        layout.addStretch()

        # 回退按钮
        self.btn_back = QPushButton(" 返回")
        self.btn_back.setIcon(QIcon(back_icon(16, self.TEXT_SECOND)))
        self._style_header_btn(self.btn_back)
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.setEnabled(False)
        layout.addWidget(self.btn_back)

        # 用户信息区
        u = self.ctx.user
        avatar = QLabel()
        avatar.setPixmap(avatar_icon(36, u.display_name, self._role_color(u.role)))
        layout.addWidget(avatar)
        layout.addSpacing(8)

        self.user_info_label = QLabel(
            f"<b>{u.display_name}</b><br/>"
            f"<span style='color:{self.TEXT_SECOND};font-size:12px;'>{u.role.display_name} · {u.department or '—'}</span>"
        )
        self.user_info_label.setStyleSheet("color: #1e293b; font-size: 13px;")
        layout.addWidget(self.user_info_label)

        layout.addSpacing(12)

        self.btn_change_pwd = QPushButton(" 修改密码")
        self.btn_change_pwd.setIcon(QIcon(user_icon(16, self.TEXT_SECOND)))
        self._style_header_btn(self.btn_change_pwd)
        self.btn_change_pwd.clicked.connect(self._change_password)
        layout.addWidget(self.btn_change_pwd)

        self.btn_logout = QPushButton(" 退出登录")
        self.btn_logout.setIcon(QIcon(logout_icon(16, "#dc2626")))
        self._style_header_btn(self.btn_logout, "#dc2626")
        self.btn_logout.clicked.connect(self._on_logout)
        layout.addWidget(self.btn_logout)

        return header

    def _style_header_btn(self, btn: QPushButton, text_color: str = "#64748b"):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid {self.BORDER};
                color: {text_color}; border-radius: 8px; padding: 6px 12px; font-size: 13px;
            }}
            QPushButton:hover {{ background: #f1f5f9; border-color: #cbd5e1; }}
        """)

    @staticmethod
    def _role_color(role: Role) -> str:
        return {Role.ADMIN: "#2563eb", Role.DOCTOR: "#0d904f", Role.REVIEWER: "#e8710a"}.get(role, "#64748b")

    def _build_nav_items(self):
        self.nav_list.clear()
        self._nav_items = []

        role = self.ctx.user.role
        # 所有角色都有首页（工作台 → 大屏）
        self._add_nav("dashboard", "大屏", dashboard_icon(20, self.PRIMARY), self.page_dashboard)

        if role == Role.DOCTOR:
            self._add_nav("patient", "患者管理", patient_icon(20, "#0d904f"), self.page_patient)
            self._add_nav("consultation", "虚拟会诊", stethoscope_icon(20, "#e8710a"), self.page_consultation)
            self._add_nav("workspace", "我的工作空间", folder_icon(20, "#5f6368"), self.page_workspace)

        elif role == Role.REVIEWER:
            self._add_nav("review_workbench", "审核工作台", stethoscope_icon(20, "#e8710a"), self.page_review_workbench)
            self._add_nav("review_history", "审核记录", folder_icon(20, "#5f6368"), self.page_review_history)

        if role == Role.ADMIN:
            self._add_nav("admin", "系统管理", gear_icon(20, "#607d8b"), self.page_admin)
            self._add_nav("integration", "系统集成", link_icon(20, "#2563eb"), self.page_integration)
            self._add_nav("security", "数据安全审计", shield_icon(20, "#d93025"), self.page_security)
            self._add_nav("quality", "质控统计报表", chart_icon(20, "#9c27b0"), self.page_quality)

        for _, text, _, icon in self._nav_items:
            item = QListWidgetItem(QIcon(icon), f"  {text}")
            self.nav_list.addItem(item)
        self.nav_list.setCurrentRow(0)

    def _add_nav(self, key: str, text: str, icon, page: QWidget):
        self._nav_items.append((key, text, page, icon))

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(22)

        u = self.ctx.user
        if u.is_admin:
            welcome = QLabel("系统概览")
            sub_text = f"当前登录：{u.display_name}（{u.role.display_name}）· 负责系统信息与用户权限维护"
        elif u.is_reviewer:
            welcome = QLabel(f"欢迎，{u.display_name}")
            sub_text = f"角色：{u.role.display_name}   科室：{u.department or '—'}   职称：{u.title or '—'} · 负责会诊报告审核"
        else:
            welcome = QLabel(f"欢迎，{u.display_name}")
            sub_text = f"角色：{u.role.display_name}   科室：{u.department or '—'}   职称：{u.title or '—'}"

        welcome.setFont(QFont("Microsoft YaHei", 22, QFont.Weight.Bold))
        welcome.setStyleSheet(f"color: {self.TEXT_MAIN};")
        layout.addWidget(welcome)

        sub = QLabel(sub_text)
        sub.setStyleSheet(f"color: {self.TEXT_SECOND}; font-size: 13px;")
        layout.addWidget(sub)

        # 统计卡片
        cards = QHBoxLayout()
        cards.setSpacing(16)
        if u.is_admin:
            self.stat_total_users = self._stat_card("用户总数", "0", self.PRIMARY)
            self.stat_enabled_users = self._stat_card("启用用户", "0", "#0d904f")
            self.stat_total_reports = self._stat_card("全局会诊", "0", "#e8710a")
            cards.addWidget(self.stat_total_users)
            cards.addWidget(self.stat_enabled_users)
            cards.addWidget(self.stat_total_reports)
        elif u.is_reviewer:
            self.stat_pending_review = self._stat_card("待审核报告", "0", "#e8710a")
            self.stat_approved_review = self._stat_card("已审核报告", "0", "#0d904f")
            self.stat_rejected_review = self._stat_card("已驳回报告", "0", "#dc2626")
            cards.addWidget(self.stat_pending_review)
            cards.addWidget(self.stat_approved_review)
            cards.addWidget(self.stat_rejected_review)
        else:
            self.stat_my_reports = self._stat_card("我的会诊记录", "0", self.PRIMARY)
            self.stat_my_patients = self._stat_card("我的患者", "0", "#0d904f")
            self.stat_today = self._stat_card("今日登录", "—", "#e8710a")
            cards.addWidget(self.stat_my_reports)
            cards.addWidget(self.stat_my_patients)
            cards.addWidget(self.stat_today)
        layout.addLayout(cards)

        # 快捷操作
        quick = self._card_frame("快捷操作")
        quick_layout = QVBoxLayout(quick)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        if u.is_admin:
            b = QPushButton(" 进入系统管理")
            b.setIcon(QIcon(gear_icon(16, "#2563eb")))
            b.clicked.connect(lambda: self._goto_nav("admin"))
            btn_row.addWidget(b)
            b2 = QPushButton(" 刷新统计数据")
            b2.clicked.connect(self._refresh_dashboard_stats)
            btn_row.addWidget(b2)
        elif u.is_reviewer:
            b1 = QPushButton(" 查看待审核报告")
            b1.clicked.connect(lambda: self._goto_nav("review_workbench"))
            btn_row.addWidget(b1)
            b2 = QPushButton(" 查看审核记录")
            b2.clicked.connect(lambda: self._goto_nav("review_history"))
            btn_row.addWidget(b2)
            b3 = QPushButton(" 刷新统计数据")
            b3.clicked.connect(self._refresh_dashboard_stats)
            btn_row.addWidget(b3)
        else:
            b1 = QPushButton(" 发起新会诊")
            b1.clicked.connect(self._quick_new_consultation)
            btn_row.addWidget(b1)
            b2 = QPushButton(" 查看会诊报告")
            b2.clicked.connect(lambda: self._goto_nav("consultation"))
            btn_row.addWidget(b2)
            b3 = QPushButton(" 查看我的工作空间")
            b3.clicked.connect(lambda: self._goto_nav("workspace"))
            btn_row.addWidget(b3)
        for i in range(btn_row.count()):
            w = btn_row.itemAt(i).widget()
            if isinstance(w, QPushButton):
                w.setStyleSheet(self._primary_btn_style())
        btn_row.addStretch()
        quick_layout.addLayout(btn_row)
        layout.addWidget(quick)

        # 最近动态
        activity = self._card_frame("最近动态")
        activity_layout = QVBoxLayout(activity)
        self.activity_list = QListWidget()
        self.activity_list.setStyleSheet(self._list_style())
        self.activity_list.setMaximumHeight(220)
        activity_layout.addWidget(self.activity_list)
        layout.addWidget(activity)

        layout.addStretch()
        return page

    def _stat_card(self, title: str, value: str, color: str) -> QWidget:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {self.CARD_BG}; border: 1px solid {self.BORDER};
                border-radius: 12px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        card.setGraphicsEffect(self._shadow_effect())
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        t = QLabel(title)
        t.setStyleSheet(f"color: {self.TEXT_SECOND}; font-size: 12px;")
        v = QLabel(value)
        v.setObjectName("valueLabel")
        v.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
        lay.addWidget(t)
        lay.addWidget(v)
        card.value_label = v  # type: ignore[attr-defined]
        return card

    def _card_frame(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{ background: {self.CARD_BG}; border: 1px solid {self.BORDER}; border-radius: 12px; }}
            QLabel {{ background: transparent; border: none; }}
        """)
        frame.setGraphicsEffect(self._shadow_effect())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        if title:
            lbl = QLabel(title)
            lbl.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {self.TEXT_MAIN}; margin-bottom: 8px;")
            layout.addWidget(lbl)
        return frame

    def _shadow_effect(self):
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(0, 3)
        return shadow

    def _primary_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: {self.PRIMARY}; color: white; border: none;
                border-radius: 8px; padding: 10px 18px; font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {self.PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background: #1e40af; }}
        """

    def _build_patient_page(self) -> QWidget:
        page = QWidget()
        return page

    def _build_patient_page_content(self):
        page = self.page_patient
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("患者管理")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.TEXT_MAIN};")
        layout.addWidget(title)

        op = QHBoxLayout()
        op.setSpacing(10)
        b_load_sample = QPushButton(" 加载示例病例")
        b_load_sample.setIcon(QIcon(patient_icon(16, "#ffffff")))
        b_load_sample.setStyleSheet(self._primary_btn_style())
        b_load_sample.setMinimumHeight(36)
        b_load_sample.clicked.connect(lambda: self._load_sample_data(silent=False))
        op.addWidget(b_load_sample)
        b_load_file = QPushButton(" 从JSON加载患者")
        b_load_file.setStyleSheet(self._secondary_btn_style())
        b_load_file.setMinimumHeight(36)
        b_load_file.clicked.connect(self._load_patient_from_file)
        op.addWidget(b_load_file)
        b_save_current = QPushButton(" 保存到我的空间")
        b_save_current.setIcon(QIcon(folder_icon(16, self.TEXT_SECOND)))
        b_save_current.setStyleSheet(self._secondary_btn_style())
        b_save_current.setMinimumHeight(36)
        b_save_current.clicked.connect(self._save_current_patient_to_space)
        op.addWidget(b_save_current)
        op.addStretch()
        layout.addLayout(op)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = self._card_frame("")
        left.setGraphicsEffect(self._shadow_effect())
        left.setMinimumWidth(180)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_title = QLabel("示例患者列表")
        left_title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        left_title.setStyleSheet(f"color: {self.TEXT_MAIN}; margin-bottom: 6px;")
        left_layout.addWidget(left_title)
        self.patient_list = QListWidget()
        self.patient_list.setStyleSheet(self._list_style())
        self.patient_list.itemClicked.connect(self._on_sample_patient_selected)
        left_layout.addWidget(self.patient_list)
        splitter.addWidget(left)

        self.patient_view.setParent(None)
        splitter.addWidget(self.patient_view)

        right = self._card_frame("")
        right.setGraphicsEffect(self._shadow_effect())
        right.setMinimumWidth(180)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_title = QLabel("我的患者空间")
        right_title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        right_title.setStyleSheet(f"color: {self.TEXT_MAIN}; margin-bottom: 6px;")
        right_layout.addWidget(right_title)
        self.my_patients_list = QListWidget()
        self.my_patients_list.setStyleSheet(self._list_style())
        self.my_patients_list.itemClicked.connect(self._on_my_patient_selected)
        right_layout.addWidget(self.my_patients_list)
        btn_del_patient = QPushButton("删除选中患者")
        btn_del_patient.setStyleSheet(self._danger_btn_style())
        btn_del_patient.setMinimumHeight(32)
        btn_del_patient.clicked.connect(self._delete_my_patient)
        right_layout.addWidget(btn_del_patient)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)
        splitter.setChildrenCollapsible(False)  # 不允许子面板完全折叠
        layout.addWidget(splitter, 1)

    def _list_style(self) -> str:
        return f"""
            QListWidget {{
                background: white; border: 1px solid {self.BORDER}; border-radius: 8px;
                padding: 4px; outline: none;
            }}
            QListWidget::item {{ padding: 8px; border-radius: 6px; }}
            QListWidget::item:selected {{ background: {self.PRIMARY_LIGHT}; color: {self.TEXT_MAIN}; }}
            QListWidget::item:hover:!selected {{ background: #f1f5f9; }}
        """

    def _secondary_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: white; color: {self.TEXT_MAIN}; border: 1px solid {self.BORDER};
                border-radius: 8px; padding: 9px 16px; font-size: 13px;
            }}
            QPushButton:hover {{ background: #f1f5f9; border-color: #cbd5e1; }}
        """

    def _danger_btn_style(self) -> str:
        return """
            QPushButton { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;
                border-radius: 8px; padding: 8px 14px; font-size: 13px; }
            QPushButton:hover { background: #fee2e2; }
        """

    def _build_workspace_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("我的工作空间")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.TEXT_MAIN};")
        layout.addWidget(title)

        desc = QLabel("此处展示您个人空间持久化的所有会诊记录（与他人数据隔离）。\n查看或导出报告详情，请选中后点击「查看选中报告」。")
        desc.setStyleSheet(f"color: {self.TEXT_SECOND}; font-size: 13px;")
        layout.addWidget(desc)

        op = QHBoxLayout()
        b_refresh = QPushButton("刷新列表")
        b_refresh.setStyleSheet(self._secondary_btn_style())
        b_refresh.clicked.connect(self._refresh_workspace_lists)
        op.addWidget(b_refresh)
        b_open = QPushButton("查看选中报告")
        b_open.setStyleSheet(self._primary_btn_style())
        b_open.clicked.connect(self._open_workspace_report)
        op.addWidget(b_open)
        b_delete = QPushButton("删除选中报告")
        b_delete.setStyleSheet(self._danger_btn_style())
        b_delete.clicked.connect(self._delete_workspace_report)
        op.addWidget(b_delete)
        op.addStretch()
        layout.addLayout(op)

        self.workspace_reports_table = QTableWidget()
        self.workspace_reports_table.setColumnCount(7)
        self.workspace_reports_table.setHorizontalHeaderLabels(
            ["会诊编号", "患者ID", "患者姓名", "类型", "状态", "创建时间", "完成时间"]
        )
        self.workspace_reports_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.workspace_reports_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.workspace_reports_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.workspace_reports_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.workspace_reports_table.setStyleSheet(self._table_style())
        self.workspace_reports_table.setGraphicsEffect(self._shadow_effect())
        layout.addWidget(self.workspace_reports_table, 1)

        return page

    # ================================================================
    # 审核员页面：审核工作台
    # ================================================================
    def _build_review_workbench_page(self) -> QWidget:
        """审核工作台 - 上下布局：上方待审核列表，下方操作按钮；审核详情在对话框中展示"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("审核工作台")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.TEXT_MAIN};")
        layout.addWidget(title)

        desc = QLabel("此处为待审核会诊报告列表。选中某条报告后点击「审核」，将弹出审核对话框查看报告详情并进行审核通过或驳回。")
        desc.setStyleSheet(f"color: {self.TEXT_SECOND}; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 待审核报告列表（占满宽度）
        self.review_pending_table = QTableWidget()
        self.review_pending_table.setColumnCount(8)
        self.review_pending_table.setHorizontalHeaderLabels(
            ["会诊编号", "患者ID", "患者姓名", "类型", "申请医生", "科室", "优先级", "提交时间"]
        )
        self.review_pending_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.review_pending_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.review_pending_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.review_pending_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.review_pending_table.setStyleSheet(self._table_style())
        self.review_pending_table.setGraphicsEffect(self._shadow_effect())
        layout.addWidget(self.review_pending_table, 1)

        # 操作按钮栏（列表下方）
        op = QHBoxLayout()
        op.setSpacing(10)
        b_refresh = QPushButton("刷新列表")
        b_refresh.setStyleSheet(self._secondary_btn_style())
        b_refresh.clicked.connect(self._refresh_review_workbench)
        op.addWidget(b_refresh)
        b_review = QPushButton("审核")
        b_review.setStyleSheet(self._primary_btn_style())
        b_review.clicked.connect(self._open_review_workbench_dialog)
        op.addWidget(b_review)
        op.addStretch()
        layout.addLayout(op)

        return page

    # ================================================================
    # 审核员页面：审核记录
    # ================================================================
    def _build_review_history_page(self) -> QWidget:
        """审核记录 - 展示该审核员历史审核记录"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("审核记录")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.TEXT_MAIN};")
        layout.addWidget(title)

        desc = QLabel("此处展示您的历史审核记录（已通过 / 已驳回的会诊报告）。")
        desc.setStyleSheet(f"color: {self.TEXT_SECOND}; font-size: 13px;")
        layout.addWidget(desc)

        op = QHBoxLayout()
        op.setSpacing(10)
        b_refresh = QPushButton("刷新列表")
        b_refresh.setStyleSheet(self._secondary_btn_style())
        b_refresh.clicked.connect(self._refresh_review_history)
        op.addWidget(b_refresh)
        b_view = QPushButton("查看审核详情")
        b_view.setStyleSheet(self._primary_btn_style())
        b_view.clicked.connect(self._view_reviewed_report)
        op.addWidget(b_view)
        op.addStretch()
        layout.addLayout(op)

        self.review_history_table = QTableWidget()
        self.review_history_table.setColumnCount(8)
        self.review_history_table.setHorizontalHeaderLabels(
            ["会诊编号", "患者姓名", "类型", "申请医生", "审核结果", "审核人", "审核时间", "审核意见"]
        )
        self.review_history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.review_history_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.review_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.review_history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.review_history_table.setStyleSheet(self._table_style())
        self.review_history_table.setGraphicsEffect(self._shadow_effect())
        layout.addWidget(self.review_history_table, 1)

        return page

    def _refresh_review_workbench(self):
        """刷新审核工作台的待审核列表"""
        if not hasattr(self, "review_pending_table"):
            return
        try:
            pending = self.ctx.review_queue.list_pending(reviewer_id=self.ctx.user.user_id)
            table = self.review_pending_table
            table.setRowCount(len(pending))
            for i, r in enumerate(pending):
                table.setItem(i, 0, QTableWidgetItem(r.get("consultation_id", "")))
                table.setItem(i, 1, QTableWidgetItem(r.get("patient_id", "")))
                table.setItem(i, 2, QTableWidgetItem(r.get("patient_name", "")))
                table.setItem(i, 3, QTableWidgetItem(r.get("consultation_type", "")))
                table.setItem(i, 4, QTableWidgetItem(r.get("doctor_name", "")))
                table.setItem(i, 5, QTableWidgetItem(r.get("department", "")))
                table.setItem(i, 6, QTableWidgetItem(r.get("priority", "")))
                table.setItem(i, 7, QTableWidgetItem(str(r.get("submitted_at", ""))[:19]))
        except Exception:
            pass
        self._refresh_dashboard_stats()

    def _refresh_review_history(self):
        """刷新审核记录列表"""
        if not hasattr(self, "review_history_table"):
            return
        try:
            reviewed = self.ctx.review_queue.list_reviewed_by(self.ctx.user.user_id)
            table = self.review_history_table
            table.setRowCount(len(reviewed))
            for i, r in enumerate(reviewed):
                status_text = "已通过" if r.get("status") == "APPROVED" else "已驳回"
                table.setItem(i, 0, QTableWidgetItem(r.get("consultation_id", "")))
                table.setItem(i, 1, QTableWidgetItem(r.get("patient_name", "")))
                table.setItem(i, 2, QTableWidgetItem(r.get("consultation_type", "")))
                table.setItem(i, 3, QTableWidgetItem(r.get("doctor_name", "")))
                table.setItem(i, 4, QTableWidgetItem(status_text))
                table.setItem(i, 5, QTableWidgetItem(r.get("reviewer_name", "")))
                table.setItem(i, 6, QTableWidgetItem(str(r.get("reviewed_at", ""))[:19]))
                table.setItem(i, 7, QTableWidgetItem(r.get("review_comment", "")))
        except Exception:
            pass

    def _selected_pending_report(self) -> Optional[dict]:
        """获取审核工作台当前选中的待审核报告条目"""
        row = self.review_pending_table.currentRow()
        if row < 0:
            return None
        cid = self.review_pending_table.item(row, 0).text()
        return self.ctx.review_queue.get_entry(cid)

    def _open_review_workbench_dialog(self):
        """打开审核对话框：展示待审核报告详情，并在对话框内进行审核通过/驳回"""
        entry = self._selected_pending_report()
        if not entry:
            QMessageBox.warning(self, "警告", "请先选中一行待审核报告")
            return
        # 跨用户加载报告
        report = self.ctx.global_index.load_report(
            entry.get("doctor_id", ""), entry.get("consultation_id", "")
        )
        if report is None:
            QMessageBox.warning(self, "警告", "无法加载报告，可能报告文件已被删除")
            return
        dialog = ReviewWorkbenchDialog(entry, report, self._do_approve, self._do_reject, self)
        dialog.exec()
        self._refresh_review_workbench()
        self._refresh_review_history()
        self._refresh_dashboard_stats()

    def _do_approve(self, entry: dict, comment: str) -> bool:
        """审核通过（供审核对话框调用），返回是否成功"""
        consultation_id = entry.get("consultation_id", "")
        doctor_id = entry.get("doctor_id", "")

        ok = self.ctx.review_queue.approve(
            consultation_id,
            reviewer_id=self.ctx.user.user_id,
            reviewer_name=self.ctx.user.display_name,
            comment=comment
        )
        if not ok:
            QMessageBox.critical(self, "错误", "审核失败：该报告可能已被处理")
            return False

        self.ctx.global_index.update_report_status(
            doctor_id, consultation_id, "APPROVED",
            extra_fields={
                "reviewer": self.ctx.user.display_name,
                "reviewed_at": datetime.now().isoformat(),
                "review_comment": comment
            }
        )
        self.ctx.audit_logger.log(
            user_id=self.ctx.user.user_id, username=self.ctx.user.username,
            action="APPROVE_REPORT", target=consultation_id,
            detail=f"patient={entry.get('patient_name', '')}, doctor={entry.get('doctor_name', '')}"
        )
        self._set_status(f"会诊 {consultation_id} 已审核通过")
        return True

    def _do_reject(self, entry: dict, comment: str) -> bool:
        """驳回报告（供审核对话框调用），返回是否成功"""
        consultation_id = entry.get("consultation_id", "")
        doctor_id = entry.get("doctor_id", "")

        ok = self.ctx.review_queue.reject(
            consultation_id,
            reviewer_id=self.ctx.user.user_id,
            reviewer_name=self.ctx.user.display_name,
            comment=comment
        )
        if not ok:
            QMessageBox.critical(self, "错误", "驳回失败：该报告可能已被处理")
            return False

        self.ctx.global_index.update_report_status(
            doctor_id, consultation_id, "REJECTED",
            extra_fields={
                "reviewer": self.ctx.user.display_name,
                "reviewed_at": datetime.now().isoformat(),
                "review_comment": comment
            }
        )
        self.ctx.audit_logger.log(
            user_id=self.ctx.user.user_id, username=self.ctx.user.username,
            action="REJECT_REPORT", target=consultation_id,
            detail=f"patient={entry.get('patient_name', '')}, reason={comment}"
        )
        self._set_status(f"会诊 {consultation_id} 已驳回")
        return True

    def _view_reviewed_report(self):
        """查看已审核记录详情（审核结果 + 会诊报告内容）"""
        row = self.review_history_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选中一行审核记录")
            return
        cid = self.review_history_table.item(row, 0).text()
        entry = self.ctx.review_queue.get_entry(cid)
        if not entry:
            QMessageBox.warning(self, "警告", "无法找到该审核记录")
            return
        report = self.ctx.global_index.load_report(
            entry.get("doctor_id", ""), entry.get("consultation_id", "")
        )
        if report is None:
            QMessageBox.warning(self, "警告", "无法加载报告，可能报告文件已被删除")
            return
        dialog = ReviewDetailDialog(entry, report, self)
        dialog.exec()

    def _on_report_submitted(self, consultation_id: str):
        """医生提交审核：先选择审查员，再将报告加入审核队列

        :return: 提交成功返回更新后的报告对象，取消或失败返回 None
        """
        report = self.engine.get_report(consultation_id)
        if report is None:
            report = self.ctx.user_session.load_report(consultation_id)
        if report is None:
            return None

        # 选择审查员
        dialog = SubmitReviewDialog(self.ctx.user_manager, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        reviewer_id = dialog.selected_reviewer_id
        reviewer_name = dialog.selected_reviewer_name

        # 更新报告状态为"待审核报告"
        if self.engine.get_report(consultation_id) is not None:
            self.engine.submit_for_review(consultation_id)
        else:
            report.status = "PENDING_REVIEW"
        try:
            self.ctx.user_session.save_report(report)
        except Exception:
            pass

        # 提交到审核队列
        patient_name = report.patient_name
        patient_id = report.patient_id
        consultation_type = report.consultation_type

        # 从会诊请求中获取优先级
        priority = "常规"
        request = self.engine.consultation_requests.get(consultation_id)
        if request:
            priority = request.get("priority", "常规")

        ok = self.ctx.review_queue.submit(
            consultation_id=consultation_id,
            doctor_id=self.ctx.user.user_id,
            doctor_name=self.ctx.user.display_name,
            patient_id=patient_id,
            patient_name=patient_name,
            consultation_type=consultation_type,
            priority=priority,
            department=self.ctx.user.department,
            assigned_reviewer_id=reviewer_id,
            assigned_reviewer_name=reviewer_name
        )
        if ok:
            self.ctx.audit_logger.log(
                user_id=self.ctx.user.user_id, username=self.ctx.user.username,
                action="SUBMIT_FOR_REVIEW", target=consultation_id,
                detail=f"patient={patient_name}, reviewer={reviewer_name}"
            )
            self._set_status(f"报告 {consultation_id} 已提交审核（审查员：{reviewer_name}）")
            QMessageBox.information(self, "成功", f"报告已提交审核\n审查员：{reviewer_name}")
            self._refresh_workspace_lists()
            self._refresh_dashboard_stats()
            return report
        else:
            QMessageBox.warning(self, "提示", "该报告已在审核队列中，无需重复提交")
            self._refresh_workspace_lists()
            self._refresh_dashboard_stats()
            return None

    def _table_style(self) -> str:
        return f"""
            QTableWidget {{
                background: white; border: 1px solid {self.BORDER}; border-radius: 10px;
                gridline-color: {self.BORDER}; outline: none;
            }}
            QHeaderView::section {{
                background: #f1f5f9; color: {self.TEXT_MAIN}; font-weight: bold;
                padding: 10px; border: none; border-bottom: 1px solid {self.BORDER};
            }}
            QTableWidget::item {{ padding: 8px; border-bottom: 1px solid {self.BORDER}; }}
            QTableWidget::item:selected {{ background: {self.PRIMARY_LIGHT}; color: {self.TEXT_MAIN}; }}
        """

    def _on_nav_changed(self, row: int):
        if row < 0 or row >= len(self._nav_items):
            return
        key = self._nav_items[row][0]
        page = self._nav_items[row][2]  # (key, text, page, icon) 中的 page widget

        # 记录导航历史（用于"返回"按钮）
        if not self._suppress_history:
            if self._current_page_key and self._current_page_key != key:
                self._nav_history.append(self._current_page_key)
        self._current_page_key = key
        self._update_back_button()

        # 修复：使用 setCurrentWidget 而非 setCurrentIndex(row)
        # 原因：导航行号与 stack 页面索引不一一对应
        self.stack.setCurrentWidget(page)

        if key == "consultation":
            try:
                self.consultation_view._refresh_history()
            except Exception:
                pass
        if key == "workspace":
            self._refresh_workspace_lists()
        if key == "review_workbench":
            self._refresh_review_workbench()
        if key == "review_history":
            self._refresh_review_history()
        if key == "dashboard":
            self._refresh_dashboard_stats()
        if key == "admin" and hasattr(self, "admin_panel"):
            try:
                self.admin_panel._refresh_all()
            except Exception:
                pass
        if key == "integration" and hasattr(self.admin_panel, "refresh_integration"):
            self.admin_panel.refresh_integration()
        if key == "security" and hasattr(self.admin_panel, "refresh_security"):
            self.admin_panel.refresh_security()
        if key == "quality" and hasattr(self.admin_panel, "refresh_quality"):
            self.admin_panel.refresh_quality()

    def _goto_nav(self, key: str):
        self._navigate(key, record=True)

    def _navigate(self, key: str, record: bool = True):
        idx = None
        for i, (k, _, _, _) in enumerate(self._nav_items):
            if k == key:
                idx = i
                break
        if idx is None:
            return
        if record and self._current_page_key and self._current_page_key != key:
            self._nav_history.append(self._current_page_key)
        self._suppress_history = True
        try:
            self.nav_list.setCurrentRow(idx)
        finally:
            self._suppress_history = False
        self._current_page_key = key
        self._update_back_button()

    def _go_back(self):
        """回退到上一页面"""
        if not self._nav_history:
            return
        key = self._nav_history.pop()
        self._navigate(key, record=False)

    def _update_back_button(self):
        if hasattr(self, "btn_back"):
            self.btn_back.setEnabled(bool(self._nav_history))

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "退出登录", "确定要退出当前登录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.ctx.audit_logger.log(
                user_id=self.ctx.user.user_id, username=self.ctx.user.username,
                action="LOGOUT"
            )
            self.logout_requested.emit()

    def _change_password(self):
        dialog = ChangePasswordDialog(self.ctx.user_manager, self.ctx.user, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "成功", "密码修改成功，请妥善保管")
            self.ctx.audit_logger.log(
                user_id=self.ctx.user.user_id, username=self.ctx.user.username,
                action="CHANGE_PASSWORD"
            )

    def _load_sample_data(self, silent: bool = False):
        try:
            sample_path = Path(__file__).parent.parent.parent / "data" / "sample_cases.json"
            if not sample_path.exists():
                msg = f"示例病例文件不存在: {sample_path}"
                if not silent:
                    QMessageBox.warning(self, "警告", msg)
                else:
                    self._set_status(msg)
                return

            with open(sample_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not data.get("patients"):
                msg = "示例病例文件为空"
                if not silent:
                    QMessageBox.warning(self, "警告", msg)
                else:
                    self._set_status(msg)
                return

            self._sample_patients = data["patients"]
            self.patient_list.clear()
            for p in self._sample_patients:
                pid = p.get("patient_id", "")
                name = p.get("name", "")
                dept = p.get("department", "")
                item = QListWidgetItem(f"{pid} | {name} | {dept}")
                item.setData(Qt.ItemDataRole.UserRole, pid)
                self.patient_list.addItem(item)

            patient_data = data["patients"][0]
            self.current_patient = Patient.from_dict(patient_data)
            self._display_patient(self.current_patient)
            self._set_status(f"已加载示例患者: {self.current_patient.name}")
            self._setup_mock_adapters(data["patients"])
        except Exception as e:
            msg = f"加载示例数据失败: {str(e)}"
            if not silent:
                QMessageBox.critical(self, "错误", msg)
            else:
                self._set_status(msg)

    def _on_sample_patient_selected(self, item: QListWidgetItem):
        pid = item.data(Qt.ItemDataRole.UserRole)
        if not pid or not self._sample_patients:
            return
        try:
            patient = self.integrator.integrate(pid)
            if patient and patient.name:
                self.current_patient = patient
            else:
                for p in self._sample_patients:
                    if p.get("patient_id") == pid:
                        self.current_patient = Patient.from_dict(p)
                        break
            self._load_patient_images(self.current_patient.patient_id)
            self._display_patient(self.current_patient)
            self._set_status(f"已切换患者: {self.current_patient.name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"切换患者失败: {e}")

    def _display_patient(self, patient: Patient):
        self.patient_view.set_patient(patient)
        self.consultation_view.set_patient(patient)

    def _load_patient_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择患者JSON文件", "", "JSON文件 (*.json)"
        )
        if not file_path:
            return
        if not Path(file_path).exists():
            QMessageBox.warning(self, "警告", "所选文件不存在或已取消")
            return
        try:
            self.current_patient = self.engine.load_patient_from_json(file_path)
            # 加载该患者关联的医学影像元数据
            self._load_patient_images(self.current_patient.patient_id)
            self._display_patient(self.current_patient)
            self._set_status(f"已加载患者: {self.current_patient.name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载患者失败: {str(e)}")

    def _load_patient_images(self, patient_id: str):
        """从用户空间加载患者医学影像元数据到当前患者对象"""
        if not self.current_patient or self.current_patient.patient_id != patient_id:
            return
        images_meta = self.ctx.user_session.list_medical_images(patient_id=patient_id)
        from ..core.patient import MedicalImage
        self.current_patient.medical_images = [
            MedicalImage.from_dict(m) for m in images_meta
        ]

    def _upload_medical_image(self):
        if not self.current_patient:
            QMessageBox.warning(self, "警告", "请先加载患者")
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "上传医学影像图片", "",
            "医学影像 (*.dcm *.jpg *.jpeg *.png *.bmp);;所有文件 (*)"
        )
        if not file_path:
            return
        source = Path(file_path)
        if not source.exists():
            QMessageBox.warning(self, "警告", "所选文件不存在或已取消")
            return
        try:
            image = self.ctx.user_session.save_medical_image(
                patient_id=self.current_patient.patient_id,
                source_path=str(source),
                image_type="其他",
                body_part="",
                description=source.name
            )
            self.ctx.user_session.save_medical_image_meta(image)
            self.patient_view.add_medical_image(image)
            self.ctx.audit_logger.log(
                user_id=self.ctx.user.user_id, username=self.ctx.user.username,
                action="UPLOAD_MEDICAL_IMAGE", target=image.image_id,
                detail=f"患者 {self.current_patient.patient_id}"
            )
            self._set_status(f"已上传影像图片: {image.file_name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"上传失败: {e}")

    def _delete_medical_image(self, image_id: str):
        if not self.current_patient:
            return
        try:
            ok = self.ctx.user_session.delete_medical_image(image_id)
            if ok:
                self.patient_view.remove_medical_image(image_id)
                self.ctx.audit_logger.log(
                    user_id=self.ctx.user.user_id, username=self.ctx.user.username,
                    action="DELETE_MEDICAL_IMAGE", target=image_id,
                    detail=f"患者 {self.current_patient.patient_id}"
                )
                self._set_status(f"已删除影像图片: {image_id}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败: {e}")

    def _setup_mock_adapters(self, patients_data: list):
        his_data, emr_data, lis_data, pacs_data = {}, {}, {}, {}
        for patient_data in patients_data:
            pid = patient_data["patient_id"]
            his_data[pid] = {
                "name": patient_data["name"],
                "gender": patient_data["gender"],
                "age": patient_data["age"],
                "admission_id": patient_data.get("admission_id", ""),
                "department": patient_data.get("department", ""),
                "attending_doctor": patient_data.get("attending_doctor", ""),
                "admission_date": patient_data.get("admission_date", "")
            }
            emr_data[pid] = {
                "chief_complaint": patient_data.get("chief_complaint", ""),
                "present_illness": patient_data.get("present_illness", ""),
                "past_history": patient_data.get("past_history", ""),
                "personal_history": patient_data.get("personal_history", ""),
                "family_history": patient_data.get("family_history", ""),
                "physical_exam": patient_data.get("physical_exam", "")
            }
            lis_data[pid] = {"lab_results": patient_data.get("lab_results", [])}
            pacs_data[pid] = {"imaging_reports": patient_data.get("imaging_reports", [])}

        self.integrator.adapters = []
        self.integrator.add_adapter(MockHospitalAdapter("HIS", sample_data=his_data))
        self.integrator.add_adapter(MockHospitalAdapter("EMR", sample_data=emr_data))
        self.integrator.add_adapter(MockHospitalAdapter("LIS", sample_data=lis_data))
        self.integrator.add_adapter(MockHospitalAdapter("PACS", sample_data=pacs_data))

    def _save_current_patient_to_space(self):
        if not self.current_patient:
            QMessageBox.warning(self, "警告", "请先加载一名患者")
            return
        try:
            self.ctx.user_session.save_patient(self.current_patient)
            self.ctx.audit_logger.log(
                user_id=self.ctx.user.user_id, username=self.ctx.user.username,
                action="SAVE_PATIENT", target=self.current_patient.patient_id,
                detail=self.current_patient.name
            )
            self._refresh_my_patients_list()
            QMessageBox.information(self, "成功", "患者已保存到您的个人空间")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def _refresh_my_patients_list(self):
        self.my_patients_list.clear()
        for p in self.ctx.user_session.list_patients():
            item = QListWidgetItem(f"{p['patient_id']} | {p['name']} | {p['department']}")
            item.setData(Qt.ItemDataRole.UserRole, p["patient_id"])
            self.my_patients_list.addItem(item)

    def _on_my_patient_selected(self, item: QListWidgetItem):
        pid = item.data(Qt.ItemDataRole.UserRole)
        patient = self.ctx.user_session.load_patient(pid)
        if patient:
            self.current_patient = patient
            self._load_patient_images(pid)
            self._display_patient(patient)
            self._set_status(f"已加载个人空间患者: {patient.name}")

    def _delete_my_patient(self):
        item = self.my_patients_list.currentItem()
        if not item:
            QMessageBox.warning(self, "警告", "请先选中一名患者")
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "确认", f"确定删除患者 {pid}？")
        if reply == QMessageBox.StandardButton.Yes:
            self.ctx.user_session.delete_patient(pid)
            self.ctx.audit_logger.log(
                user_id=self.ctx.user.user_id, username=self.ctx.user.username,
                action="DELETE_PATIENT", target=pid
            )
            self._refresh_my_patients_list()

    def _quick_new_consultation(self):
        if not self.current_patient:
            QMessageBox.warning(self, "警告", "请先在患者管理中加载患者")
            return
        self._goto_nav("consultation")
        self.consultation_view.start_new_consultation(self.current_patient)

    def _on_consultation_requested(self, consultation_id: str, selected_agents: list):
        self.current_consultation_id = consultation_id

        self.progress_dialog = QProgressDialog("正在执行虚拟会诊...", "取消", 0, 0, self)
        self.progress_dialog.setWindowTitle("会诊中")
        self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()

        self.worker = ConsultationWorker(
            self.engine, consultation_id,
            patient=self.current_patient,
            selected_agents=selected_agents
        )
        self.worker.finished.connect(self._on_consultation_finished)
        self.worker.error.connect(self._on_consultation_error)
        self.worker.progress.connect(self._update_progress)
        self.worker.start()

        self.ctx.audit_logger.log(
            user_id=self.ctx.user.user_id, username=self.ctx.user.username,
            action="CREATE_CONSULTATION", target=consultation_id,
            detail=f"agents={selected_agents}"
        )

    def _update_progress(self, message: str):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
        self._set_status(message)

    def _on_consultation_finished(self, report):
        if self.progress_dialog:
            self.progress_dialog.close()

        try:
            self.ctx.user_session.save_report(report)
            self.ctx.audit_logger.log(
                user_id=self.ctx.user.user_id, username=self.ctx.user.username,
                action="COMPLETE_CONSULTATION", target=report.consultation_id,
                detail=f"patient={report.patient_name}"
            )
        except Exception as e:
            print(f"⚠ 报告持久化失败: {e}")

        # 报告内容已移入"会诊审核"对话框，此处仅刷新历史并停留当前页
        try:
            self.consultation_view._refresh_history()
        except Exception:
            pass
        self._goto_nav("consultation")
        self._set_status(f"会诊 {report.consultation_id} 已完成")
        QMessageBox.information(self, "完成", f"会诊报告已生成\n编号: {report.consultation_id}\n请点击「会诊审核」查看并提交审核")
        self._refresh_dashboard_stats()

    def _on_consultation_error(self, error_message: str):
        if self.progress_dialog:
            self.progress_dialog.close()
        QMessageBox.critical(self, "错误", f"会诊执行失败: {error_message}")

    def _open_consultation_review(self, consultation_id: str):
        """打开"会诊审核"对话框：展示会诊报告内容并支持提交审核"""
        report = self.engine.get_report(consultation_id)
        if report is None:
            report = self.ctx.user_session.load_report(consultation_id)
            if report:
                self.engine.consultations[consultation_id] = report
        if report is None:
            QMessageBox.warning(self, "警告", "未找到该会诊报告")
            return
        dialog = ConsultationReviewDialog(report, self._on_report_submitted, self)
        dialog.exec()

    def _refresh_workspace_lists(self):
        self._refresh_my_patients_list()
        reports = self.ctx.user_session.list_reports()
        table = self.workspace_reports_table
        table.setRowCount(len(reports))
        for i, r in enumerate(reports):
            table.setItem(i, 0, QTableWidgetItem(r.get("consultation_id", "")))
            table.setItem(i, 1, QTableWidgetItem(r.get("patient_id", "")))
            table.setItem(i, 2, QTableWidgetItem(r.get("patient_name", "")))
            table.setItem(i, 3, QTableWidgetItem(r.get("consultation_type", "")))
            table.setItem(i, 4, QTableWidgetItem(r.get("status", "")))
            table.setItem(i, 5, QTableWidgetItem(str(r.get("created_at", ""))))
            table.setItem(i, 6, QTableWidgetItem(str(r.get("completed_at", ""))))
        self._refresh_dashboard_stats()

    def _selected_workspace_report_id(self) -> Optional[str]:
        row = self.workspace_reports_table.currentRow()
        if row < 0:
            return None
        return self.workspace_reports_table.item(row, 0).text()

    def _open_workspace_report(self):
        cid = self._selected_workspace_report_id()
        if not cid:
            QMessageBox.warning(self, "警告", "请先选中一行报告")
            return
        self._open_consultation_review(cid)

    def _delete_workspace_report(self):
        cid = self._selected_workspace_report_id()
        if not cid:
            QMessageBox.warning(self, "警告", "请先选中一行报告")
            return
        reply = QMessageBox.question(self, "确认", f"确定删除会诊 {cid}？此操作不可恢复。")
        if reply == QMessageBox.StandardButton.Yes:
            self.ctx.user_session.delete_report(cid)
            self.ctx.audit_logger.log(
                user_id=self.ctx.user.user_id, username=self.ctx.user.username,
                action="DELETE_REPORT", target=cid
            )
            self._refresh_workspace_lists()

    def _refresh_dashboard_stats(self):
        try:
            u = self.ctx.user
            if u.is_admin:
                stats = self.ctx.user_manager.stats()
                self.stat_total_users.value_label.setText(str(stats["total"]))  # type: ignore[attr-defined]
                self.stat_enabled_users.value_label.setText(str(stats["enabled"]))  # type: ignore[attr-defined]
                self.stat_total_reports.value_label.setText(str(len(self.ctx.global_index.list_all_reports())))  # type: ignore[attr-defined]
                self._refresh_activity_list("ADMIN")
            elif u.is_reviewer:
                pending = self.ctx.review_queue.list_pending(reviewer_id=u.user_id)
                reviewed = self.ctx.review_queue.list_reviewed_by(u.user_id)
                approved = sum(1 for r in reviewed if r.get("status") == "APPROVED")
                rejected = sum(1 for r in reviewed if r.get("status") == "REJECTED")
                self.stat_pending_review.value_label.setText(str(len(pending)))  # type: ignore[attr-defined]
                self.stat_approved_review.value_label.setText(str(approved))  # type: ignore[attr-defined]
                self.stat_rejected_review.value_label.setText(str(rejected))  # type: ignore[attr-defined]
                self._refresh_activity_list("REVIEWER")
            else:
                reports = self.ctx.user_session.list_reports()
                patients = self.ctx.user_session.list_patients()
                self.stat_my_reports.value_label.setText(str(len(reports)))  # type: ignore[attr-defined]
                self.stat_my_patients.value_label.setText(str(len(patients)))  # type: ignore[attr-defined]
                self.stat_today.value_label.setText("✓" if u.last_login_at else "—")  # type: ignore[attr-defined]
                self._refresh_activity_list("DOCTOR")
        except Exception:
            pass

    def _refresh_activity_list(self, role_hint: str = ""):
        """刷新首页最近动态列表"""
        if not hasattr(self, "activity_list"):
            return
        self.activity_list.clear()
        try:
            if role_hint == "ADMIN":
                logs = self.ctx.audit_logger.get_logs(limit=8)
                for e in logs:
                    text = f"{e.get('timestamp', '')[:19]}  {e.get('username', '')} {e.get('action', '')}"
                    self.activity_list.addItem(text)
            elif role_hint == "REVIEWER":
                # 审核员首页展示待审核与最近审核记录（仅本人可见的待审/已审）
                pending = self.ctx.review_queue.list_pending(reviewer_id=self.ctx.user.user_id)[:4]
                for r in pending:
                    text = (f"{r.get('submitted_at', '')[:19]}  待审核  "
                            f"{r.get('patient_name', '')}  ({r.get('doctor_name', '')})")
                    self.activity_list.addItem(text)
                reviewed = self.ctx.review_queue.list_reviewed_by(self.ctx.user.user_id)[:4]
                for r in reviewed:
                    status = "已通过" if r.get("status") == "APPROVED" else "已驳回"
                    text = (f"{r.get('reviewed_at', '')[:19]}  {status}  "
                            f"{r.get('patient_name', '')}  ({r.get('reviewer_name', '')})")
                    self.activity_list.addItem(text)
            else:
                reports = self.ctx.user_session.list_reports()[:8]
                for r in reports:
                    text = f"{r.get('created_at', '')[:19]}  {r.get('patient_name', '')}  {r.get('consultation_type', '')}  {r.get('status', '')}"
                    self.activity_list.addItem(text)
        except Exception:
            pass

    def _set_status(self, text: str):
        self.status_label.setText(text)


class ChangePasswordDialog(QDialog):
    """修改密码对话框"""

    def __init__(self, user_manager: UserManager, user: User, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.user = user
        self.setWindowTitle("修改密码")
        self.setMinimumWidth(380)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        self.old_edit = QLineEdit()
        self.old_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_edit = QLineEdit()
        self.new_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addRow("原密码：", self.old_edit)
        layout.addRow("新密码：", self.new_edit)
        layout.addRow("确认新密码：", self.confirm_edit)

        tip = QLabel("提示：新密码不少于 6 位。")
        tip.setStyleSheet("color: #888; font-size: 11px;")
        layout.addRow(tip)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_accept(self):
        old = self.old_edit.text()
        new = self.new_edit.text()
        confirm = self.confirm_edit.text()
        if not old or not new:
            QMessageBox.warning(self, "警告", "请填写原密码与新密码")
            return
        if len(new) < 6:
            QMessageBox.warning(self, "警告", "新密码长度不能少于 6 位")
            return
        if new != confirm:
            QMessageBox.warning(self, "警告", "两次输入的新密码不一致")
            return
        ok = self.user_manager.change_password(self.user.user_id, old, new)
        if not ok:
            QMessageBox.critical(self, "错误", "原密码不正确")
            return
        self.accept()


class SubmitReviewDialog(QDialog):
    """医生提交审核时选择审查员的对话框"""

    def __init__(self, user_manager: UserManager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.selected_reviewer_id: str = ""
        self.selected_reviewer_name: str = ""
        self.setWindowTitle("选择审查员")
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        tip = QLabel("请选择本报告提交给哪位审查员审核：")
        tip.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: bold;")
        layout.addWidget(tip)

        form = QFormLayout()
        self.reviewer_combo = QComboBox()
        reviewers = [u for u in self.user_manager.list_users() if u.role == Role.REVIEWER]
        if not reviewers:
            # 兜底：无审查员时允许选择管理员审核
            reviewers = [u for u in self.user_manager.list_users() if u.role == Role.ADMIN]
        for r in reviewers:
            self.reviewer_combo.addItem(f"{r.display_name}（{r.department or '—'} · {r.title or '—'}）", r.user_id)
        self.reviewer_combo.setStyleSheet("""
            QComboBox { border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; }
        """)
        form.addRow("审查员：", self.reviewer_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("提交审核")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        idx = self.reviewer_combo.currentIndex()
        if idx < 0 or self.reviewer_combo.count() == 0:
            QMessageBox.warning(self, "警告", "当前没有可用的审查员，请联系管理员创建审查员账号")
            return
        self.selected_reviewer_id = self.reviewer_combo.currentData()
        self.selected_reviewer_name = self.reviewer_combo.currentText().split("（")[0]
        self.accept()


class ReviewDetailDialog(QDialog):
    """查看审核详情对话框：审核结果 + 会诊报告内容"""

    def __init__(self, entry: dict, report, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.report = report
        self.setWindowTitle("审核详情")
        self.resize(980, 760)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        status = "已通过" if self.entry.get("status") == "APPROVED" else "已驳回"
        status_color = "#0d904f" if self.entry.get("status") == "APPROVED" else "#dc2626"
        info = QLabel(
            f"<b>会诊编号：</b>{self.entry.get('consultation_id', '')}　"
            f"<b>患者：</b>{self.entry.get('patient_name', '')}　"
            f"<b>申请医生：</b>{self.entry.get('doctor_name', '')}<br>"
            f"<b>审核结果：</b><span style='color:{status_color};font-weight:bold;'>{status}</span>　"
            f"<b>审核人：</b>{self.entry.get('reviewer_name', '')}　"
            f"<b>审核时间：</b>{str(self.entry.get('reviewed_at', ''))[:19]}<br>"
            f"<b>审核意见：</b>{self.entry.get('review_comment', '') or '—'}"
        )
        info.setWordWrap(True)
        info.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; font-size: 13px;")
        layout.addWidget(info)

        # 嵌入只读的报告视图
        report_view = ReportView(show_title=True)
        report_view.set_submit_visible(False)
        report_view.set_report(self.report)
        layout.addWidget(report_view, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)


class ConsultationReviewDialog(QDialog):
    """会诊审核对话框：展示会诊报告内容，并支持提交审核（选择审查员）"""

    def __init__(self, report, submit_callback, parent=None):
        super().__init__(parent)
        self.report = report
        self.submit_callback = submit_callback
        self.setWindowTitle("会诊审核")
        self.resize(980, 760)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            f"<b>会诊编号：</b>{self.report.consultation_id}　"
            f"<b>患者：</b>{self.report.patient_name}（{self.report.patient_id}）　"
            f"<b>类型：</b>{self.report.consultation_type}　"
            f"<b>状态：</b>{self.report.status}"
        )
        info.setWordWrap(True)
        info.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; font-size: 13px;")
        layout.addWidget(info)

        # 报告内容：不显示"会诊报告"标题，标题由对话框"会诊审核"承担
        self.report_view = ReportView(show_title=False)
        self.report_view.set_report(self.report)
        self.report_view.report_submitted.connect(self._on_submit)
        layout.addWidget(self.report_view, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_submit(self, consultation_id: str):
        updated = self.submit_callback(consultation_id)
        if updated is not None:
            self.report = updated
            self.report_view.set_report(updated)


class ReviewWorkbenchDialog(QDialog):
    """审核对话框：展示待审核报告详情，并在对话框内进行审核通过/驳回"""

    def __init__(self, entry: dict, report, approve_cb, reject_cb, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.report = report
        self.approve_cb = approve_cb
        self.reject_cb = reject_cb
        self.setWindowTitle("审核报告")
        self.resize(980, 760)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            f"<b>会诊编号：</b>{self.entry.get('consultation_id', '')}　"
            f"<b>患者：</b>{self.entry.get('patient_name', '')}（{self.entry.get('patient_id', '')}）<br>"
            f"<b>申请医生：</b>{self.entry.get('doctor_name', '')}　"
            f"<b>科室：</b>{self.entry.get('department', '')}　"
            f"<b>类型：</b>{self.entry.get('consultation_type', '')}　"
            f"<b>优先级：</b>{self.entry.get('priority', '')}"
        )
        info.setWordWrap(True)
        info.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; font-size: 13px;")
        layout.addWidget(info)

        # 报告详情内容（不显示"会诊报告"标题，且隐藏"提交审核"按钮）
        self.report_view = ReportView(show_title=False)
        self.report_view.set_submit_visible(False)
        self.report_view.set_report(self.report)
        layout.addWidget(self.report_view, 1)

        # 审核操作 + 关闭
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_approve = QPushButton("审核通过")
        btn_approve.setStyleSheet("""
            QPushButton { background: #0d904f; color: white; border: none;
                          border-radius: 8px; padding: 10px 18px; font-size: 13px; font-weight: bold; }
            QPushButton:hover { background: #0b7a3f; }
        """)
        btn_approve.clicked.connect(self._on_approve)
        btn_row.addWidget(btn_approve)

        btn_reject = QPushButton("驳回")
        btn_reject.setStyleSheet("""
            QPushButton { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;
                          border-radius: 8px; padding: 10px 18px; font-size: 13px; }
            QPushButton:hover { background: #fee2e2; }
        """)
        btn_reject.clicked.connect(self._on_reject)
        btn_row.addWidget(btn_reject)

        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet("""
            QPushButton { background: white; color: #1e293b; border: 1px solid #e2e8f0;
                          border-radius: 8px; padding: 10px 18px; font-size: 13px; }
            QPushButton:hover { background: #f1f5f9; }
        """)
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _on_approve(self):
        dialog = ApproveReviewDialog(self, self.entry)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        comment = dialog.comment_edit.text().strip()
        if self.approve_cb(self.entry, comment):
            QMessageBox.information(self, "成功", f"报告 {self.entry.get('consultation_id', '')} 已审核通过")
            self.accept()

    def _on_reject(self):
        dialog = RejectReviewDialog(self, self.entry)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        comment = dialog.comment_edit.text().strip()
        if not comment:
            QMessageBox.warning(self, "警告", "驳回时请填写驳回原因")
            return
        if self.reject_cb(self.entry, comment):
            QMessageBox.information(self, "已驳回", f"报告 {self.entry.get('consultation_id', '')} 已驳回\n原因：{comment}")
            self.accept()
