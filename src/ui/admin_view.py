"""
后端管理平台 - 管理员后台面板

依据《医院虚拟会诊系统后端管理平台完整功能》设计书实现，包含 10 大管理模块：
  1. 工作台概览（仪表盘 + 业务指标）
  2. 用户与权限管理（用户、角色模板）
  3. 会诊业务管理（全生命周期、调度规则、报告管理）
  4. AI 智能体管理（专科智能体生命周期、Moderator 配置）
  5. 知识库管理（医学知识图谱、病例库、循证库）
  6. 系统集成管理（数据源适配器、FHIR 映射、集成监控）
  7. 数据安全与审计（脱敏、审计日志、加密、合规）
  8. 质控统计报表（评分模板、质控台账、统计看板）
  9. 系统配置运维（全局参数、通知、监控告警、备份）
 10. 患者档案管理（全景档案、异常检索、随访）

所有敏感操作写入审计日志。
"""
import json
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QFont, QIcon, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFormLayout, QLineEdit, QComboBox, QDialog,
    QDialogButtonBox, QFileDialog, QGroupBox, QGraphicsDropShadowEffect,
    QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit, QSplitter,
    QScrollArea, QFrame, QSizePolicy
)

from ..core.user import User, Role, UserManager
from ..core.session import GlobalConsultationIndex
from ..core.admin_config import (
    get_admin_config, AdminConfigManager,
    AgentConfig, AdapterConfig, QualityControlItem,
    RoleTemplate, PluginConfig, DesensitizationRule
)


# ============================================================
# 通用样式与辅助组件
# ============================================================

class StyleMixin:
    """样式常量与按钮风格"""
    PRIMARY = "#2563eb"
    PRIMARY_HOVER = "#1d4ed8"
    SECONDARY = "#64748b"
    BORDER = "#e2e8f0"
    BG = "#f8fafc"
    CARD_BG = "#ffffff"
    DANGER = "#dc2626"
    SUCCESS = "#0d904f"
    WARN = "#e8710a"

    def _primary_btn(self) -> str:
        return f"""
            QPushButton {{ background: {self.PRIMARY}; color: white; border: none;
                          border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: bold; }}
            QPushButton:hover {{ background: {self.PRIMARY_HOVER}; }}
            QPushButton:disabled {{ background: #94a3b8; }}
        """

    def _secondary_btn(self) -> str:
        return f"""
            QPushButton {{ background: white; color: #1e293b; border: 1px solid {self.BORDER};
                          border-radius: 8px; padding: 8px 16px; font-size: 13px; }}
            QPushButton:hover {{ background: #f1f5f9; border-color: #cbd5e1; }}
            QPushButton:disabled {{ color: #94a3b8; background: #f8fafc; }}
        """

    def _danger_btn(self) -> str:
        return """
            QPushButton { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;
                          border-radius: 8px; padding: 8px 16px; font-size: 13px; }
            QPushButton:hover { background: #fee2e2; }
            QPushButton:disabled { color: #94a3b8; background: #f8fafc; }
        """

    def _table_style(self) -> str:
        return f"""
            QTableWidget {{ background: white; border: 1px solid {self.BORDER}; border-radius: 10px;
                            gridline-color: {self.BORDER}; outline: none; }}
            QHeaderView::section {{ background: #f1f5f9; color: #1e293b; font-weight: bold;
                                   padding: 10px; border: none; border-bottom: 1px solid {self.BORDER}; }}
            QTableWidget::item {{ padding: 8px; border-bottom: 1px solid {self.BORDER}; }}
            QTableWidget::item:selected {{ background: #dbeafe; color: #1e293b; }}
        """

    def _shadow(self) -> QGraphicsDropShadowEffect:
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(0, 3)
        return shadow

    def _group_style(self) -> str:
        return f"""
            QGroupBox {{ font-weight: bold; border: 1px solid {self.BORDER}; border-radius: 10px;
                         margin-top: 12px; padding-top: 12px; background: white; color: #1e293b; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}
        """

    def _input_style(self) -> str:
        return f"""
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                border: 1px solid {self.BORDER}; border-radius: 6px; padding: 6px 10px;
                background: white; color: #1e293b; font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus {{ border: 2px solid {self.PRIMARY}; padding: 5px 9px; }}
            QCheckBox {{ spacing: 6px; color: #1e293b; }}
        """

    def _stat_card(self, title: str, value: str, color: str = None) -> QFrame:
        color = color or self.PRIMARY
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background: white; border: 1px solid {self.BORDER}; border-radius: 10px; }}
            QLabel {{ background: transparent; border: none; }}
        """)
        card.setGraphicsEffect(self._shadow())
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        t = QLabel(title)
        t.setStyleSheet(f"color: {self.SECONDARY}; font-size: 12px;")
        v = QLabel(str(value))
        v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        lay.addWidget(t)
        lay.addWidget(v)
        card.value_label = v  # type: ignore[attr-defined]
        return card

    def _toolbar_button(self, text: str, style: str = None, icon=None) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(style or self._secondary_btn())
        btn.setMinimumHeight(34)
        if icon is not None:
            btn.setIcon(icon)
        return btn


# ============================================================
# 用户编辑对话框
# ============================================================

class UserEditDialog(QDialog):
    """新建/编辑用户对话框"""

    def __init__(self, user_manager: UserManager, parent=None, user: User = None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.user = user
        self.created_user: Optional[User] = None
        self.updated_user: Optional[User] = None
        self.setWindowTitle("新建用户" if user is None else "编辑用户")
        self.setMinimumWidth(460)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("登录名（唯一）")
        layout.addRow("用户名*：", self.username_edit)

        self.display_edit = QLineEdit()
        layout.addRow("姓名*：", self.display_edit)

        self.role_combo = QComboBox()
        self.role_combo.addItem("管理员", Role.ADMIN)
        self.role_combo.addItem("医生", Role.DOCTOR)
        self.role_combo.addItem("审核员", Role.REVIEWER)
        layout.addRow("角色*：", self.role_combo)

        self.dept_edit = QLineEdit()
        layout.addRow("科室：", self.dept_edit)

        self.title_edit = QLineEdit()
        layout.addRow("职称：", self.title_edit)

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_edit.setPlaceholderText("不少于 6 位")
        pwd_row_label = QLabel("密码*：")
        layout.addRow(pwd_row_label, self.pwd_edit)

        if self.user is not None:
            self.username_edit.setText(self.user.username)
            self.username_edit.setEnabled(False)
            self.display_edit.setText(self.user.display_name)
            for i in range(self.role_combo.count()):
                if self.role_combo.itemData(i) == self.user.role:
                    self.role_combo.setCurrentIndex(i)
                    break
            self.dept_edit.setText(self.user.department)
            self.title_edit.setText(self.user.title)
            self.pwd_edit.setEnabled(False)
            pwd_row_label.setText("密码：")
            self.pwd_edit.setPlaceholderText("编辑模式下不可修改（请用重置密码）")

        for i in range(layout.rowCount()):
            field = layout.itemAt(i, QFormLayout.ItemRole.FieldRole)
            if field and isinstance(field.widget(), (QLineEdit, QComboBox)):
                field.widget().setStyleSheet("""
                    QLineEdit, QComboBox { border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; }
                    QLineEdit:focus { border: 2px solid #2563eb; padding: 7px 9px; }
                """)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_accept(self):
        username = self.username_edit.text().strip()
        display = self.display_edit.text().strip()
        role = self.role_combo.currentData()
        dept = self.dept_edit.text().strip()
        title = self.title_edit.text().strip()

        if not username or not display:
            QMessageBox.warning(self, "警告", "用户名与姓名不能为空")
            return

        try:
            if self.user is None:
                pwd = self.pwd_edit.text()
                if not pwd or len(pwd) < 6:
                    QMessageBox.warning(self, "警告", "密码不少于 6 位")
                    return
                self.created_user = self.user_manager.create_user(
                    username=username, display_name=display, role=role,
                    department=dept, title=title, password=pwd
                )
            else:
                self.updated_user = self.user_manager.update_user(
                    self.user.user_id, display_name=display, role=role,
                    department=dept, title=title
                )
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "警告", str(e))


# ============================================================
# 通用：编辑对话框（用于 Agent / Adapter / Quality / Role 等配置项）
# ============================================================

class KeyValueEditDialog(QDialog):
    """通用键值编辑对话框"""

    def __init__(self, title: str, fields: list, parent=None, initial: dict = None):
        """
        :param fields: [(key, label, widget_type, options, required), ...]
            widget_type: 'text' / 'combo' / 'spin' / 'doublespin' / 'check' / 'textarea'
            options: for combo -> list of (label, value); for spin -> (min,max,step);
                     for doublespin -> (min,max,step,decimals); for check -> default bool
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.fields = fields
        self.widgets: dict = {}
        self.result_data: dict = {}
        self._build(initial or {})

    def _build(self, initial: dict):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        for key, label, wtype, opts, required in self.fields:
            val = initial.get(key, "")
            if wtype == "text":
                w = QLineEdit(str(val) if val != "" else "")
            elif wtype == "textarea":
                w = QTextEdit(str(val) if val != "" else "")
            elif wtype == "combo":
                w = QComboBox()
                for lbl, data in opts:
                    w.addItem(lbl, data)
                if val != "":
                    for i in range(w.count()):
                        if w.itemData(i) == val:
                            w.setCurrentIndex(i)
                            break
            elif wtype == "spin":
                w = QSpinBox()
                lo, hi, step = opts
                w.setRange(lo, hi)
                w.setSingleStep(step)
                w.setValue(int(val) if val != "" else lo)
            elif wtype == "doublespin":
                w = QDoubleSpinBox()
                lo, hi, step, dec = opts
                w.setRange(lo, hi)
                w.setSingleStep(step)
                w.setDecimals(dec)
                w.setValue(float(val) if val != "" else lo)
            elif wtype == "check":
                w = QCheckBox()
                w.setChecked(bool(val))
            else:
                w = QLineEdit(str(val))
            w.setStyleSheet("""
                QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                    border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; }
                QTextEdit { border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; }
            """)
            label_text = f"{label}{'*' if required else ''}："
            layout.addRow(label_text, w)
            self.widgets[key] = w

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_accept(self):
        for key, label, wtype, opts, required in self.fields:
            w = self.widgets[key]
            if wtype == "text":
                val = w.text().strip()
            elif wtype == "textarea":
                val = w.toPlainText().strip()
            elif wtype == "combo":
                val = w.currentData()
            elif wtype in ("spin", "doublespin"):
                val = w.value()
            elif wtype == "check":
                val = w.isChecked()
            else:
                val = w.text().strip()
            if required and (val == "" or val is None):
                QMessageBox.warning(self, "警告", f"{label} 不能为空")
                return
            self.result_data[key] = val
        self.accept()


# ============================================================
# 主面板
# ============================================================

def _diag_log(message: str) -> None:
    """诊断日志 - 写入 data/admin/init.log，便于排查打包环境下的初始化问题"""
    try:
        from ..core.admin_config import get_project_root
        log_dir = get_project_root() / "data" / "admin"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "init.log"
        import datetime
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        # 诊断日志失败不应影响主流程
        try:
            print(f"[AdminPanel diag] {message}")
        except Exception:
            pass


class AdminPanel(QWidget, StyleMixin):
    """管理员后台主面板 - 10 大管理模块"""

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        _diag_log("AdminPanel.__init__ 开始")
        try:
            self.admin_cfg: AdminConfigManager = get_admin_config()
            _diag_log(f"AdminConfigManager 获取成功 (version={self.admin_cfg.system.version})")
        except Exception as e:
            _diag_log(f"[严重] AdminConfigManager 获取失败: {e}")
            self.admin_cfg = None
        self._init_ui()
        _diag_log("_init_ui 完成，开始 _refresh_all")
        try:
            self._refresh_all()
            _diag_log("_refresh_all 完成")
        except Exception as e:
            _diag_log(f"[严重] _refresh_all 失败: {e}")
            import traceback
            _diag_log(traceback.format_exc())

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 标题区
        header = QHBoxLayout()
        title = QLabel("后端管理平台")
        title.setFont(QFont("Microsoft YaHei", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b;")
        header.addWidget(title)
        header.addStretch()
        sub = QLabel("系统信息维护 · 不参与临床诊疗与会诊报告审核")
        sub.setStyleSheet(f"color: {self.SECONDARY}; font-size: 13px;")
        header.addWidget(sub)
        layout.addLayout(header)

        # 选项卡 - 10 大管理模块（每个 tab 构造异常隔离，避免单个失败导致整体不可用）
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {self.BORDER}; border-radius: 10px; background: white; }}
            QTabBar::tab {{ background: #f1f5f9; color: {self.SECONDARY}; padding: 10px 16px;
                           border-top-left-radius: 8px; border-top-right-radius: 8px;
                           font-size: 13px; margin-right: 2px; }}
            QTabBar::tab:selected {{ background: {self.PRIMARY}; color: white; font-weight: bold; }}
            QTabBar::tab:hover:!selected {{ background: #e2e8f0; }}
        """)

        # tab 列表：(构建方法名, 标签文本)
        # 注：系统集成 / 数据安全审计 / 质控统计报表 已从系统管理中分离，
        # 作为与"系统管理"同级的主窗口导航页面（由 get_*_page() 独立构建）。
        tab_builders = [
            ("_build_dashboard_tab", "工作台概览"),
            ("_build_user_tab", "用户与权限"),
            ("_build_consultation_tab", "会诊业务管理"),
            ("_build_agent_tab", "AI 智能体"),
            ("_build_knowledge_tab", "知识库管理"),
            ("_build_config_tab", "系统配置运维"),
            ("_build_patient_archive_tab", "患者档案管理"),
        ]
        for builder_name, tab_label in tab_builders:
            try:
                builder = getattr(self, builder_name)
                widget = builder()
                self.tabs.addTab(widget, tab_label)
                _diag_log(f"tab 添加成功: {tab_label}")
            except Exception as e:
                _diag_log(f"[错误] tab '{tab_label}' 构造失败: {e}")
                import traceback
                _diag_log(traceback.format_exc())
                # 用错误占位 widget 替代，保证 tab 仍然可见
                err_widget = QWidget()
                err_layout = QVBoxLayout(err_widget)
                err_label = QLabel(f"该模块加载失败：{tab_label}\n\n错误信息：\n{e}\n\n请联系系统管理员或重新打包程序。")
                err_label.setWordWrap(True)
                err_label.setStyleSheet(f"color: {self.DANGER}; padding: 20px; font-size: 13px;")
                err_layout.addWidget(err_label)
                err_layout.addStretch()
                self.tabs.addTab(err_widget, tab_label)
        _diag_log(f"全部 tab 添加完成，共 {self.tabs.count()} 个")
        layout.addWidget(self.tabs, 1)

    # ============================================================
    # 公共方法
    # ============================================================
    def _audit(self, action: str, target: str = "", detail: str = ""):
        self.ctx.audit_logger.log(
            user_id=self.ctx.user.user_id, username=self.ctx.user.username,
            action=action, target=target, detail=detail
        )

    def _make_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        return scroll

    # ============================================================
    # 1. 工作台概览
    # ============================================================
    def _build_dashboard_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("系统概览")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        # 业务指标卡片
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.dash_card_users = self._stat_card("用户总数", "0", self.PRIMARY)
        self.dash_card_agents = self._stat_card("AI 智能体", "0", self.SUCCESS)
        self.dash_card_adapters = self._stat_card("数据源适配器", "0", self.WARN)
        self.dash_card_consultations = self._stat_card("全局会诊数", "0", "#9c27b0")
        for c in [self.dash_card_users, self.dash_card_agents, self.dash_card_adapters, self.dash_card_consultations]:
            cards.addWidget(c)
        layout.addLayout(cards)

        # 系统健康状态
        info_group = QGroupBox("系统信息")
        info_group.setStyleSheet(self._group_style())
        info_group.setGraphicsEffect(self._shadow())
        info_layout = QFormLayout(info_group)
        s = self.admin_cfg.system
        info_layout.addRow("应用名称：", QLabel(s.hospital_name + " 虚拟会诊系统"))
        info_layout.addRow("版本：", QLabel(s.version))
        info_layout.addRow("院区：", QLabel(s.campus_info))
        info_layout.addRow("最大并发会诊：", QLabel(f"{s.max_concurrent_consultations}"))
        info_layout.addRow("数据存储路径：", QLabel(s.pdf_storage_path))
        layout.addWidget(info_group)

        # 最近审计动态
        act_group = QGroupBox("最近操作动态")
        act_group.setStyleSheet(self._group_style())
        act_group.setGraphicsEffect(self._shadow())
        act_layout = QVBoxLayout(act_group)
        from PyQt6.QtWidgets import QListWidget
        self.dash_activity = QListWidget()
        self.dash_activity.setMaximumHeight(180)
        self.dash_activity.setStyleSheet(f"""
            QListWidget {{ background: white; border: 1px solid {self.BORDER}; border-radius: 8px;
                          padding: 4px; outline: none; }}
            QListWidget::item {{ padding: 6px; border-bottom: 1px solid {self.BORDER}; }}
        """)
        act_layout.addWidget(self.dash_activity)
        layout.addWidget(act_group)

        layout.addStretch()
        return page

    def _refresh_dashboard(self):
        try:
            us = self.ctx.user_manager.stats()
            self.dash_card_users.value_label.setText(str(us["total"]))  # type: ignore[attr-defined]
            cfg_stats = self.admin_cfg.stats()
            self.dash_card_agents.value_label.setText(str(cfg_stats["agent_enabled"]))  # type: ignore[attr-defined]
            self.dash_card_adapters.value_label.setText(str(cfg_stats["adapter_enabled"]))  # type: ignore[attr-defined]
            total_c = len(self.ctx.global_index.list_all_reports())
            self.dash_card_consultations.value_label.setText(str(total_c))  # type: ignore[attr-defined]
            self.dash_activity.clear()
            for e in self.ctx.audit_logger.get_logs(limit=10):
                txt = f"{str(e.get('timestamp',''))[:19]}  {e.get('username','')}  {e.get('action','')}"
                self.dash_activity.addItem(txt)
        except Exception:
            pass

    # ============================================================
    # 2. 用户与权限管理
    # ============================================================
    def _build_user_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # 上：用户列表
        upper = QWidget()
        upper_layout = QVBoxLayout(upper)
        upper_layout.setSpacing(10)
        op = QHBoxLayout()
        op.setSpacing(8)
        b_create = self._toolbar_button("+ 新建用户", self._primary_btn())
        b_create.clicked.connect(self._create_user)
        op.addWidget(b_create)
        b_edit = self._toolbar_button("编辑用户")
        b_edit.clicked.connect(self._edit_user)
        op.addWidget(b_edit)
        b_reset = self._toolbar_button("重置密码")
        b_reset.clicked.connect(self._reset_password)
        op.addWidget(b_reset)
        b_toggle = self._toolbar_button("启用 / 停用")
        b_toggle.clicked.connect(self._toggle_enabled)
        op.addWidget(b_toggle)
        b_delete = self._toolbar_button("删除用户", self._danger_btn())
        b_delete.clicked.connect(self._delete_user)
        op.addWidget(b_delete)
        b_refresh = self._toolbar_button("刷新")
        b_refresh.clicked.connect(self._refresh_users)
        op.addWidget(b_refresh)
        op.addStretch()
        upper_layout.addLayout(op)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(8)
        self.user_table.setHorizontalHeaderLabels(
            ["用户ID", "用户名", "姓名", "角色", "科室", "职称", "状态", "最后登录"]
        )
        self.user_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.user_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.user_table.setStyleSheet(self._table_style())
        upper_layout.addWidget(self.user_table)

        self.user_stats_label = QLabel("")
        self.user_stats_label.setStyleSheet(f"color: {self.SECONDARY}; font-size: 12px;")
        upper_layout.addWidget(self.user_stats_label)
        splitter.addWidget(upper)

        # 下：角色模板
        lower = QWidget()
        lower_layout = QVBoxLayout(lower)
        lower_layout.setSpacing(8)
        role_title = QLabel("角色权限模板（自定义角色）")
        role_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        lower_layout.addWidget(role_title)
        role_op = QHBoxLayout()
        b_add_role = self._toolbar_button("新增角色模板", self._primary_btn())
        b_add_role.clicked.connect(self._add_role_template)
        role_op.addWidget(b_add_role)
        b_del_role = self._toolbar_button("删除选中角色", self._danger_btn())
        b_del_role.clicked.connect(self._delete_role_template)
        role_op.addWidget(b_del_role)
        role_op.addStretch()
        lower_layout.addLayout(role_op)

        self.role_table = QTableWidget()
        self.role_table.setColumnCount(5)
        self.role_table.setHorizontalHeaderLabels(["角色ID", "角色名", "权限范围", "数据范围", "说明"])
        self.role_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.role_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.role_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.role_table.setStyleSheet(self._table_style())
        lower_layout.addWidget(self.role_table)
        splitter.addWidget(lower)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        return page

    def _refresh_users(self):
        users = self.ctx.user_manager.list_users()
        table = self.user_table
        table.setRowCount(len(users))
        for i, u in enumerate(users):
            table.setItem(i, 0, QTableWidgetItem(u.user_id))
            table.setItem(i, 1, QTableWidgetItem(u.username))
            table.setItem(i, 2, QTableWidgetItem(u.display_name))
            table.setItem(i, 3, QTableWidgetItem(u.role.display_name))
            table.setItem(i, 4, QTableWidgetItem(u.department))
            table.setItem(i, 5, QTableWidgetItem(u.title))
            status_item = QTableWidgetItem("启用" if u.enabled else "停用")
            status_item.setForeground(QColor(self.SUCCESS if u.enabled else self.DANGER))
            table.setItem(i, 6, QTableWidgetItem(status_item))
            last = ""
            if u.last_login_at:
                last = QDateTime.fromSecsSinceEpoch(int(u.last_login_at)).toString("yyyy-MM-dd hh:mm")
            table.setItem(i, 7, QTableWidgetItem(last))
        stats = self.ctx.user_manager.stats()
        self.user_stats_label.setText(
            f"共 {stats['total']} 个用户 | 管理员 {stats['admin']} | "
            f"医生 {stats['doctor']} | 审核员 {stats['reviewer']} | "
            f"启用 {stats['enabled']} / 停用 {stats['disabled']}"
        )
        # 角色模板
        rt = self.role_table
        rt.setRowCount(len(self.admin_cfg.role_templates))
        for i, r in enumerate(self.admin_cfg.role_templates):
            rt.setItem(i, 0, QTableWidgetItem(r.role_id))
            rt.setItem(i, 1, QTableWidgetItem(r.name))
            rt.setItem(i, 2, QTableWidgetItem(",".join(r.permissions)))
            rt.setItem(i, 3, QTableWidgetItem(r.data_scope))
            rt.setItem(i, 4, QTableWidgetItem(r.description))

    def _selected_user_id(self) -> Optional[str]:
        row = self.user_table.currentRow()
        if row < 0:
            return None
        return self.user_table.item(row, 0).text()

    def _create_user(self):
        dialog = UserEditDialog(self.ctx.user_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                u = dialog.created_user
                self._audit("CREATE_USER", target=u.user_id,
                            detail=f"{u.username}({u.role.display_name})")
                QMessageBox.information(self, "成功", f"用户 {u.username} 已创建")
                self._refresh_users()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def _edit_user(self):
        uid = self._selected_user_id()
        if not uid:
            QMessageBox.warning(self, "警告", "请先选中一名用户")
            return
        user = self.ctx.user_manager.get_user(uid)
        if not user:
            return
        dialog = UserEditDialog(self.ctx.user_manager, self, user=user)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.updated_user:
            self._audit("UPDATE_USER", target=uid,
                        detail=f"->{dialog.updated_user.display_name}")
            QMessageBox.information(self, "成功", "用户信息已更新")
            self._refresh_users()

    def _reset_password(self):
        uid = self._selected_user_id()
        if not uid:
            QMessageBox.warning(self, "警告", "请先选中一名用户")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("重置密码")
        layout = QFormLayout(dialog)
        pwd = QLineEdit(); pwd.setEchoMode(QLineEdit.EchoMode.Password)
        confirm = QLineEdit(); confirm.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("新密码：", pwd)
        layout.addRow("确认：", confirm)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if len(pwd.text()) < 6:
                QMessageBox.warning(self, "警告", "密码长度不能少于 6 位")
                return
            if pwd.text() != confirm.text():
                QMessageBox.warning(self, "警告", "两次输入不一致")
                return
            try:
                self.ctx.user_manager.reset_password(uid, pwd.text())
                self._audit("RESET_PASSWORD", target=uid)
                QMessageBox.information(self, "成功", "密码已重置")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def _toggle_enabled(self):
        uid = self._selected_user_id()
        if not uid:
            QMessageBox.warning(self, "警告", "请先选中一名用户")
            return
        user = self.ctx.user_manager.get_user(uid)
        if not user:
            return
        if user.user_id == self.ctx.user.user_id and user.enabled:
            QMessageBox.warning(self, "警告", "不能停用当前登录的管理员账户")
            return
        try:
            self.ctx.user_manager.update_user(uid, enabled=not user.enabled)
            self._audit("TOGGLE_USER", target=uid,
                        detail="启用" if not user.enabled else "停用")
            self._refresh_users()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _delete_user(self):
        uid = self._selected_user_id()
        if not uid:
            QMessageBox.warning(self, "警告", "请先选中一名用户")
            return
        if uid == self.ctx.user.user_id:
            QMessageBox.warning(self, "警告", "不能删除当前登录的账户")
            return
        reply = QMessageBox.question(
            self, "确认", "确定删除该用户？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.ctx.user_manager.delete_user(uid)
                self._audit("DELETE_USER", target=uid)
                self._refresh_users()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def _add_role_template(self):
        fields = [
            ("role_id", "角色ID", "text", None, True),
            ("name", "角色名", "text", None, True),
            ("description", "说明", "text", None, False),
            ("data_scope", "数据范围", "combo",
             [("本人", "self"), ("本科室", "department"), ("本园区", "campus"), ("全院", "hospital")], True),
            ("permissions", "权限范围", "text", None, False),
        ]
        dialog = KeyValueEditDialog("新增角色模板", fields, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                d = dialog.result_data
                self.admin_cfg.add_role_template(RoleTemplate(
                    role_id=d["role_id"], name=d["name"],
                    description=d.get("description", ""),
                    permissions=d.get("permissions", "").split(","),
                    data_scope=d["data_scope"]
                ))
                self._audit("CREATE_ROLE_TEMPLATE", target=d["role_id"])
                self._refresh_users()
            except ValueError as e:
                QMessageBox.warning(self, "警告", str(e))

    def _delete_role_template(self):
        row = self.role_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选中一个角色模板")
            return
        rid = self.role_table.item(row, 0).text()
        if rid.startswith("ROLE_") and rid in ("ROLE_ADMIN", "ROLE_DOCTOR", "ROLE_REVIEWER"):
            QMessageBox.warning(self, "警告", "系统内置角色不可删除")
            return
        self.admin_cfg.delete_role_template(rid)
        self._audit("DELETE_ROLE_TEMPLATE", target=rid)
        self._refresh_users()

    # ============================================================
    # 3. 会诊业务管理
    # ============================================================
    def _build_consultation_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # 上：全局会诊列表
        upper = QWidget()
        ul = QVBoxLayout(upper)
        ul.setSpacing(8)
        op = QHBoxLayout()
        b_refresh = self._toolbar_button("刷新", self._primary_btn())
        b_refresh.clicked.connect(self._refresh_consultations)
        op.addWidget(b_refresh)
        b_export = self._toolbar_button("批量导出")
        b_export.clicked.connect(self._export_consultations)
        op.addWidget(b_export)
        op.addStretch()
        self.consult_count_label = QLabel("")
        self.consult_count_label.setStyleSheet(f"color: {self.SECONDARY}; font-size: 12px;")
        op.addWidget(self.consult_count_label)
        ul.addLayout(op)

        self.consult_table = QTableWidget()
        self.consult_table.setColumnCount(7)
        self.consult_table.setHorizontalHeaderLabels(
            ["会诊编号", "用户ID", "患者ID", "患者姓名", "类型", "状态", "创建时间"]
        )
        self.consult_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.consult_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.consult_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.consult_table.setStyleSheet(self._table_style())
        ul.addWidget(self.consult_table)
        splitter.addWidget(upper)

        # 下：调度规则配置
        lower = QWidget()
        ll = QVBoxLayout(lower)
        rule_title = QLabel("会诊调度规则")
        rule_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        ll.addWidget(rule_title)

        form = QFormLayout()
        form.setSpacing(10)
        self.spin_emergency = QSpinBox()
        self.spin_emergency.setRange(1, 60)
        self.spin_emergency.setSuffix(" 分钟")
        form.addRow("急诊 AI 响应时效：", self.spin_emergency)
        self.spin_routine = QSpinBox()
        self.spin_routine.setRange(1, 168)
        self.spin_routine.setSuffix(" 小时")
        form.addRow("常规会诊时效：", self.spin_routine)
        self.spin_mdt = QSpinBox()
        self.spin_mdt.setRange(1, 240)
        self.spin_mdt.setSuffix(" 小时")
        form.addRow("MDT 会诊时效：", self.spin_mdt)
        self.combo_collab = QComboBox()
        self.combo_collab.addItem("全自动 (auto)", "auto")
        self.combo_collab.addItem("半自动 (semi-auto)", "semi-auto")
        self.combo_collab.addItem("人工主导 (manual)", "manual")
        form.addRow("人机协作模式：", self.combo_collab)
        for w in [self.spin_emergency, self.spin_routine, self.spin_mdt, self.combo_collab]:
            w.setStyleSheet(self._input_style())
        ll.addLayout(form)

        btn_row = QHBoxLayout()
        b_save_rule = self._toolbar_button("保存调度规则", self._primary_btn())
        b_save_rule.clicked.connect(self._save_schedule_rule)
        btn_row.addWidget(b_save_rule)
        btn_row.addStretch()
        ll.addLayout(btn_row)
        splitter.addWidget(lower)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        return page

    def _refresh_consultations(self):
        reports = self.ctx.global_index.list_all_reports()
        t = self.consult_table
        t.setRowCount(len(reports))
        for i, r in enumerate(reports):
            t.setItem(i, 0, QTableWidgetItem(r.get("consultation_id", "")))
            t.setItem(i, 1, QTableWidgetItem(r.get("user_id", "")))
            t.setItem(i, 2, QTableWidgetItem(r.get("patient_id", "")))
            t.setItem(i, 3, QTableWidgetItem(r.get("patient_name", "")))
            t.setItem(i, 4, QTableWidgetItem(r.get("consultation_type", "")))
            status_item = QTableWidgetItem(r.get("status", ""))
            status_item.setForeground(QColor(self.SUCCESS if r.get("status") == "APPROVED" else self.WARN))
            t.setItem(i, 5, status_item)
            t.setItem(i, 6, QTableWidgetItem(str(r.get("created_at", ""))[:19]))
        self.consult_count_label.setText(f"共 {len(reports)} 条会诊记录")
        rule = self.admin_cfg.schedule_rule
        self.spin_emergency.setValue(rule.emergency_response_minutes)
        self.spin_routine.setValue(rule.routine_response_hours)
        self.spin_mdt.setValue(rule.mdt_response_hours)
        idx = self.combo_collab.findData(rule.collaboration_mode)
        if idx >= 0:
            self.combo_collab.setCurrentIndex(idx)

    def _save_schedule_rule(self):
        rule = self.admin_cfg.schedule_rule
        rule.emergency_response_minutes = self.spin_emergency.value()
        rule.routine_response_hours = self.spin_routine.value()
        rule.mdt_response_hours = self.spin_mdt.value()
        rule.collaboration_mode = self.combo_collab.currentData()
        self.admin_cfg.save_all()
        self._audit("UPDATE_SCHEDULE_RULE", detail=f"模式={rule.collaboration_mode}")
        QMessageBox.information(self, "成功", "会诊调度规则已保存")

    def _export_consultations(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "批量导出会诊列表", "consultations.csv", "CSV 文件 (*.csv)"
        )
        if not file_path:
            return
        try:
            reports = self.ctx.global_index.list_all_reports()
            with open(file_path, "w", encoding="utf-8-sig") as f:
                f.write("会诊编号,用户ID,患者ID,患者姓名,类型,状态,创建时间\n")
                for r in reports:
                    row = [r.get("consultation_id", ""), r.get("user_id", ""),
                           r.get("patient_id", ""), r.get("patient_name", ""),
                           r.get("consultation_type", ""), r.get("status", ""),
                           str(r.get("created_at", ""))[:19]]
                    f.write(",".join(f'"{c}"' for c in row) + "\n")
            self._audit("EXPORT_CONSULTATIONS", detail=f"共 {len(reports)} 条")
            QMessageBox.information(self, "成功", f"已导出 {len(reports)} 条会诊记录")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

    # ============================================================
    # 4. AI 智能体管理
    # ============================================================
    def _build_agent_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        upper = QWidget()
        ul = QVBoxLayout(upper)
        ul.setSpacing(8)
        op = QHBoxLayout()
        b_add = self._toolbar_button("+ 新增智能体", self._primary_btn())
        b_add.clicked.connect(self._add_agent)
        op.addWidget(b_add)
        b_edit = self._toolbar_button("编辑配置")
        b_edit.clicked.connect(self._edit_agent)
        op.addWidget(b_edit)
        b_toggle = self._toolbar_button("启用 / 停用")
        b_toggle.clicked.connect(self._toggle_agent)
        op.addWidget(b_toggle)
        b_del = self._toolbar_button("删除", self._danger_btn())
        b_del.clicked.connect(self._delete_agent)
        op.addWidget(b_del)
        b_refresh = self._toolbar_button("刷新")
        b_refresh.clicked.connect(self._refresh_agents)
        op.addWidget(b_refresh)
        op.addStretch()
        ul.addLayout(op)

        self.agent_table = QTableWidget()
        self.agent_table.setColumnCount(7)
        self.agent_table.setHorizontalHeaderLabels(
            ["智能体ID", "名称", "专科", "状态", "LLM 底座", "温度", "知识库"]
        )
        self.agent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.agent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.agent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.agent_table.setStyleSheet(self._table_style())
        ul.addWidget(self.agent_table)
        splitter.addWidget(upper)

        lower = QWidget()
        ll = QVBoxLayout(lower)
        m_title = QLabel("Moderator 主持人配置")
        m_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        ll.addWidget(m_title)

        m_form = QFormLayout()
        m_form.setSpacing(10)
        self.spin_rounds = QSpinBox()
        self.spin_rounds.setRange(1, 10)
        m_form.addRow("讨论轮次上限：", self.spin_rounds)
        self.spin_consensus = QDoubleSpinBox()
        self.spin_consensus.setRange(0.5, 1.0); self.spin_consensus.setSingleStep(0.05); self.spin_consensus.setDecimals(2)
        m_form.addRow("共识阈值：", self.spin_consensus)
        self.check_debate = QCheckBox("启用分歧辩论")
        m_form.addRow("", self.check_debate)
        self.combo_weight = QComboBox()
        self.combo_weight.addItem("证据等级加权 (evidence)", "evidence")
        self.combo_weight.addItem("置信度加权 (confidence)", "confidence")
        self.combo_weight.addItem("混合加权 (hybrid)", "hybrid")
        m_form.addRow("权重打分策略：", self.combo_weight)
        for w in [self.spin_rounds, self.spin_consensus, self.combo_weight]:
            w.setStyleSheet(self._input_style())
        ll.addLayout(m_form)

        b_save_m = self._toolbar_button("保存 Moderator 配置", self._primary_btn())
        b_save_m.clicked.connect(self._save_moderator)
        ll.addWidget(b_save_m)
        splitter.addWidget(lower)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        return page

    def _refresh_agents(self):
        agents = self.admin_cfg.agents
        t = self.agent_table
        t.setRowCount(len(agents))
        for i, a in enumerate(agents):
            t.setItem(i, 0, QTableWidgetItem(a.agent_id))
            t.setItem(i, 1, QTableWidgetItem(a.name))
            t.setItem(i, 2, QTableWidgetItem(a.specialty))
            status = QTableWidgetItem("启用" if a.enabled else "停用")
            status.setForeground(QColor(self.SUCCESS if a.enabled else self.DANGER))
            t.setItem(i, 3, status)
            t.setItem(i, 4, QTableWidgetItem(a.llm_backend))
            t.setItem(i, 5, QTableWidgetItem(f"{a.temperature:.2f}"))
            t.setItem(i, 6, QTableWidgetItem(a.knowledge_base))
        m = self.admin_cfg.moderator
        self.spin_rounds.setValue(m.max_discussion_rounds)
        self.spin_consensus.setValue(m.consensus_threshold)
        self.check_debate.setChecked(m.enable_debate)
        idx = self.combo_weight.findData(m.weight_strategy)
        if idx >= 0:
            self.combo_weight.setCurrentIndex(idx)

    def _add_agent(self):
        fields = [
            ("agent_id", "智能体ID", "text", None, True),
            ("name", "名称", "text", None, True),
            ("specialty", "专科", "text", None, True),
            ("description", "说明", "textarea", None, False),
            ("llm_backend", "LLM 底座", "combo",
             [("规则引擎 (rule-based)", "rule-based"),
              ("DeepSeek", "DeepSeek"), ("通义千问 (Qwen)", "Qwen"), ("GPT", "GPT")], True),
            ("temperature", "温度", "doublespin", (0.0, 2.0, 0.1, 2), True),
            ("knowledge_base", "知识库", "text", None, False),
        ]
        dialog = KeyValueEditDialog("新增智能体", fields, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                d = dialog.result_data
                self.admin_cfg.add_agent(AgentConfig(
                    agent_id=d["agent_id"], name=d["name"], specialty=d["specialty"],
                    description=d.get("description", ""), llm_backend=d["llm_backend"],
                    temperature=float(d["temperature"]), knowledge_base=d.get("knowledge_base", "default")
                ))
                self._audit("CREATE_AGENT", target=d["agent_id"])
                self._refresh_agents()
            except ValueError as e:
                QMessageBox.warning(self, "警告", str(e))

    def _edit_agent(self):
        row = self.agent_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选中一个智能体")
            return
        agent = self.admin_cfg.agents[row]
        fields = [
            ("name", "名称", "text", None, True),
            ("specialty", "专科", "text", None, True),
            ("description", "说明", "textarea", None, False),
            ("llm_backend", "LLM 底座", "combo",
             [("规则引擎 (rule-based)", "rule-based"),
              ("DeepSeek", "DeepSeek"), ("通义千问 (Qwen)", "Qwen"), ("GPT", "GPT")], True),
            ("temperature", "温度", "doublespin", (0.0, 2.0, 0.1, 2), True),
            ("knowledge_base", "知识库", "text", None, False),
            ("system_prompt", "系统提示词", "textarea", None, False),
        ]
        dialog = KeyValueEditDialog("编辑智能体", fields, self, initial={
            "name": agent.name, "specialty": agent.specialty, "description": agent.description,
            "llm_backend": agent.llm_backend, "temperature": agent.temperature,
            "knowledge_base": agent.knowledge_base, "system_prompt": agent.system_prompt
        })
        if dialog.exec() == QDialog.DialogCode.Accepted:
            d = dialog.result_data
            self.admin_cfg.update_agent(agent.agent_id,
                name=d["name"], specialty=d["specialty"], description=d.get("description", ""),
                llm_backend=d["llm_backend"], temperature=float(d["temperature"]),
                knowledge_base=d.get("knowledge_base", "default"),
                system_prompt=d.get("system_prompt", ""))
            self._audit("UPDATE_AGENT", target=agent.agent_id)
            self._refresh_agents()

    def _toggle_agent(self):
        row = self.agent_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选中一个智能体")
            return
        agent = self.admin_cfg.agents[row]
        new_state = self.admin_cfg.toggle_agent(agent.agent_id)
        self._audit("TOGGLE_AGENT", target=agent.agent_id, detail="启用" if new_state else "停用")
        self._refresh_agents()

    def _delete_agent(self):
        row = self.agent_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选中一个智能体")
            return
        agent = self.admin_cfg.agents[row]
        reply = QMessageBox.question(self, "确认", f"确定下线并删除智能体 {agent.name}？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.admin_cfg.delete_agent(agent.agent_id)
            self._audit("DELETE_AGENT", target=agent.agent_id)
            self._refresh_agents()

    def _save_moderator(self):
        m = self.admin_cfg.moderator
        m.max_discussion_rounds = self.spin_rounds.value()
        m.consensus_threshold = self.spin_consensus.value()
        m.enable_debate = self.check_debate.isChecked()
        m.weight_strategy = self.combo_weight.currentData()
        self.admin_cfg.save_all()
        self._audit("UPDATE_MODERATOR_CONFIG",
                    detail=f"轮次={m.max_discussion_rounds},共识阈值={m.consensus_threshold}")
        QMessageBox.information(self, "成功", "Moderator 配置已保存")

    # ============================================================
    # 5. 知识库管理
    # ============================================================
    def _build_knowledge_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        # 知识图谱概览
        kg_group = QGroupBox("医学知识图谱")
        kg_group.setStyleSheet(self._group_style())
        kg_group.setGraphicsEffect(self._shadow())
        kg_layout = QFormLayout(kg_group)
        try:
            from ..core.knowledge_graph import build_default_knowledge_graph
            kg = build_default_knowledge_graph()
            stats = kg.stats() if hasattr(kg, "stats") else {}
            kg_layout.addRow("疾病实体数：", QLabel(str(stats.get("diseases", len(kg.get_entities_by_type("disease"))))))
            kg_layout.addRow("症状实体数：", QLabel(str(stats.get("symptoms", len(kg.get_entities_by_type("symptom"))))))
            kg_layout.addRow("检查实体数：", QLabel(str(stats.get("tests", len(kg.get_entities_by_type("test"))))))
            kg_layout.addRow("药品实体数：", QLabel(str(stats.get("drugs", len(kg.get_entities_by_type("drug"))))))
        except Exception as e:
            kg_layout.addRow("状态：", QLabel(f"加载失败: {e}"))
        layout.addWidget(kg_group)

        # 病例库
        case_group = QGroupBox("结构化会诊病例库")
        case_group.setStyleSheet(self._group_style())
        case_group.setGraphicsEffect(self._shadow())
        case_layout = QVBoxLayout(case_group)
        case_op = QHBoxLayout()
        b_refresh_case = self._toolbar_button("刷新病例库", self._primary_btn())
        b_refresh_case.clicked.connect(self._refresh_case_library)
        case_op.addWidget(b_refresh_case)
        b_export_case = self._toolbar_button("导出脱敏数据集")
        b_export_case.clicked.connect(self._export_case_library)
        case_op.addWidget(b_export_case)
        case_op.addStretch()
        case_layout.addLayout(case_op)

        self.case_table = QTableWidget()
        self.case_table.setColumnCount(6)
        self.case_table.setHorizontalHeaderLabels(
            ["会诊编号", "患者ID", "患者姓名", "类型", "状态", "完成时间"]
        )
        self.case_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.case_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.case_table.setStyleSheet(self._table_style())
        case_layout.addWidget(self.case_table)
        layout.addWidget(case_group)

        # 循证库说明
        ev_group = QGroupBox("循证医学证据库")
        ev_group.setStyleSheet(self._group_style())
        ev_group.setGraphicsEffect(self._shadow())
        ev_layout = QFormLayout(ev_group)
        ev_layout.addRow("证据等级：", QLabel("A（高质量 RCT Meta）/ B（队列/权威指南）/ C（病例系列/共识）/ D（AI 推理）"))
        ev_layout.addRow("推荐强度：", QLabel("强推荐 / 弱推荐 / 有条件推荐"))
        ev_layout.addRow("管理方式：", QLabel("通过 data/admin/config.json 维护证据等级规则；文献批量上传可在文件存储目录扩展"))
        layout.addWidget(ev_group)

        layout.addStretch()
        return page

    def _collect_case_library_reports(self) -> list:
        """汇总结构化会诊病历库数据：全局会诊报告 + 处理后的示例报告"""
        reports = self.ctx.global_index.list_all_reports()
        seen_ids = {r.get("consultation_id", "") for r in reports}

        # 兜底：并入 data/processed 目录下已处理的结构化报告，避免病例库为空
        processed_dir = Path(__file__).parent.parent.parent / "data" / "processed"
        if processed_dir.exists():
            for f in sorted(processed_dir.glob("*.json"), reverse=True):
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    cid = data.get("consultation_id", "")
                    if not cid or cid in seen_ids:
                        continue
                    reports.append({
                        "user_id": "processed",
                        "consultation_id": cid,
                        "patient_id": data.get("patient_id", ""),
                        "patient_name": data.get("patient_name", ""),
                        "consultation_type": data.get("consultation_type", ""),
                        "status": data.get("status", ""),
                        "created_at": data.get("created_at", ""),
                        "completed_at": data.get("completed_at", ""),
                    })
                    seen_ids.add(cid)
                except (json.JSONDecodeError, OSError):
                    continue
        return reports

    def _refresh_case_library(self):
        """刷新结构化会诊病历库表格"""
        reports = self._collect_case_library_reports()
        t = self.case_table
        t.setRowCount(len(reports))
        for i, r in enumerate(reports):
            t.setItem(i, 0, QTableWidgetItem(r.get("consultation_id", "")))
            t.setItem(i, 1, QTableWidgetItem(r.get("patient_id", "")))
            t.setItem(i, 2, QTableWidgetItem(r.get("patient_name", "")))
            t.setItem(i, 3, QTableWidgetItem(r.get("consultation_type", "")))
            t.setItem(i, 4, QTableWidgetItem(r.get("status", "")))
            t.setItem(i, 5, QTableWidgetItem(str(r.get("completed_at", "") or r.get("created_at", ""))[:19]))

    def _export_case_library(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出脱敏病例数据集", "case_library.csv", "CSV 文件 (*.csv)"
        )
        if not file_path:
            return
        try:
            reports = self._collect_case_library_reports()
            with open(file_path, "w", encoding="utf-8-sig") as f:
                f.write("会诊编号,患者ID(脱敏),患者姓名(脱敏),类型,状态,完成时间\n")
                for r in reports:
                    pid = r.get("patient_id", "")
                    pid_mask = pid[:2] + "***" + pid[-2:] if len(pid) > 4 else "****"
                    pname = r.get("patient_name", "")
                    pname_mask = pname[0] + "**" if len(pname) > 1 else "*"
                    row = [r.get("consultation_id", ""), pid_mask, pname_mask,
                           r.get("consultation_type", ""), r.get("status", ""),
                           str(r.get("completed_at", "") or r.get("created_at", ""))[:19]]
                    f.write(",".join(f'"{c}"' for c in row) + "\n")
            self._audit("EXPORT_CASE_LIBRARY", detail=f"共 {len(reports)} 条脱敏")
            QMessageBox.information(self, "成功", f"已导出 {len(reports)} 条脱敏病例")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

    # ============================================================
    # 6. 系统集成管理
    # ============================================================
    def _build_integration_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        op = QHBoxLayout()
        b_add = self._toolbar_button("+ 新增适配器", self._primary_btn())
        b_add.clicked.connect(self._add_adapter)
        op.addWidget(b_add)
        b_edit = self._toolbar_button("编辑")
        b_edit.clicked.connect(self._edit_adapter)
        op.addWidget(b_edit)
        b_test = self._toolbar_button("连通性测试")
        b_test.clicked.connect(self._test_adapter)
        op.addWidget(b_test)
        b_del = self._toolbar_button("删除", self._danger_btn())
        b_del.clicked.connect(self._delete_adapter)
        op.addWidget(b_del)
        b_refresh = self._toolbar_button("刷新")
        b_refresh.clicked.connect(self._refresh_adapters)
        op.addWidget(b_refresh)
        op.addStretch()
        layout.addLayout(op)

        self.adapter_table = QTableWidget()
        self.adapter_table.setColumnCount(8)
        self.adapter_table.setHorizontalHeaderLabels(
            ["类型", "名称", "Endpoint", "API 类型", "同步周期", "状态", "最近测试", "测试结果"]
        )
        self.adapter_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.adapter_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.adapter_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.adapter_table.setStyleSheet(self._table_style())
        layout.addWidget(self.adapter_table)

        # FHIR 映射说明
        fhir_group = QGroupBox("FHIR R4 标准化映射")
        fhir_group.setStyleSheet(self._group_style())
        fhir_group.setGraphicsEffect(self._shadow())
        fhir_layout = QFormLayout(fhir_group)
        fhir_layout.addRow("映射标准：", QLabel("FHIR R4 / ICD-11 / LOINC / SNOMED"))
        fhir_layout.addRow("映射方式：", QLabel("院内原始字段 → 标准临床术语（在适配器中维护映射表）"))
        fhir_layout.addRow("数据清洗：", QLabel("异常检验值过滤、文本脏数据清洗（按适配器配置生效）"))
        layout.addWidget(fhir_group)

        layout.addStretch()
        return page

    def _refresh_adapters(self):
        adapters = self.admin_cfg.adapters
        t = self.adapter_table
        t.setRowCount(len(adapters))
        for i, a in enumerate(adapters):
            t.setItem(i, 0, QTableWidgetItem(a.adapter_type))
            t.setItem(i, 1, QTableWidgetItem(a.name))
            t.setItem(i, 2, QTableWidgetItem(a.endpoint))
            t.setItem(i, 3, QTableWidgetItem(a.api_type))
            t.setItem(i, 4, QTableWidgetItem(f"{a.sync_period_minutes} 分钟"))
            status = QTableWidgetItem("启用" if a.enabled else "停用")
            status.setForeground(QColor(self.SUCCESS if a.enabled else self.DANGER))
            t.setItem(i, 5, status)
            t.setItem(i, 6, QTableWidgetItem(a.last_test_at or "—"))
            test_status = QTableWidgetItem(a.last_test_status)
            if a.last_test_status == "成功":
                test_status.setForeground(QColor(self.SUCCESS))
            elif a.last_test_status == "失败":
                test_status.setForeground(QColor(self.DANGER))
            t.setItem(i, 7, test_status)

    def _add_adapter(self):
        fields = [
            ("adapter_type", "类型", "combo",
             [("HIS", "HIS"), ("EMR", "EMR"), ("LIS", "LIS"), ("PACS", "PACS"),
              ("药房", "Pharmacy"), ("麻醉", "Anesthesia")], True),
            ("name", "名称", "text", None, True),
            ("endpoint", "Endpoint", "text", None, True),
            ("api_type", "API 类型", "combo",
             [("REST", "REST"), ("FHIR", "FHIR"), ("WebService", "WebService"),
              ("Database", "Database"), ("MQ", "MQ"), ("DICOMWeb", "DICOMWeb")], True),
            ("username", "账号", "text", None, False),
            ("sync_period_minutes", "同步周期(分钟)", "spin", (1, 1440, 1), True),
            ("sync_mode", "同步模式", "combo",
             [("增量", "incremental"), ("全量", "full")], True),
        ]
        dialog = KeyValueEditDialog("新增适配器", fields, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            d = dialog.result_data
            self.admin_cfg.add_adapter(AdapterConfig(
                adapter_type=d["adapter_type"], name=d["name"], endpoint=d["endpoint"],
                api_type=d["api_type"], username=d.get("username", ""),
                sync_period_minutes=d["sync_period_minutes"], sync_mode=d["sync_mode"]
            ))
            self._audit("CREATE_ADAPTER", target=d["name"])
            self._refresh_adapters()

    def _edit_adapter(self):
        row = self.adapter_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选中一个适配器")
            return
        a = self.admin_cfg.adapters[row]
        fields = [
            ("name", "名称", "text", None, True),
            ("endpoint", "Endpoint", "text", None, True),
            ("api_type", "API 类型", "combo",
             [("REST", "REST"), ("FHIR", "FHIR"), ("WebService", "WebService"),
              ("Database", "Database"), ("MQ", "MQ"), ("DICOMWeb", "DICOMWeb")], True),
            ("username", "账号", "text", None, False),
            ("sync_period_minutes", "同步周期(分钟)", "spin", (1, 1440, 1), True),
            ("sync_mode", "同步模式", "combo",
             [("增量", "incremental"), ("全量", "full")], True),
        ]
        dialog = KeyValueEditDialog("编辑适配器", fields, self, initial={
            "name": a.name, "endpoint": a.endpoint, "api_type": a.api_type,
            "username": a.username, "sync_period_minutes": a.sync_period_minutes,
            "sync_mode": a.sync_mode
        })
        if dialog.exec() == QDialog.DialogCode.Accepted:
            d = dialog.result_data
            self.admin_cfg.update_adapter(row,
                name=d["name"], endpoint=d["endpoint"], api_type=d["api_type"],
                username=d.get("username", ""), sync_period_minutes=d["sync_period_minutes"],
                sync_mode=d["sync_mode"])
            self._audit("UPDATE_ADAPTER", target=d["name"])
            self._refresh_adapters()

    def _test_adapter(self):
        row = self.adapter_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选中一个适配器")
            return
        status, ts = self.admin_cfg.test_adapter(row)
        a = self.admin_cfg.adapters[row]
        self._audit("TEST_ADAPTER", target=a.name, detail=f"{status} @ {ts}")
        self._refresh_adapters()
        QMessageBox.information(self, "测试结果",
                                 f"适配器：{a.name}\n测试状态：{status}\n测试时间：{ts}")

    def _delete_adapter(self):
        row = self.adapter_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选中一个适配器")
            return
        a = self.admin_cfg.adapters[row]
        reply = QMessageBox.question(self, "确认", f"确定删除适配器 {a.name}？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.admin_cfg.delete_adapter(row)
            self._audit("DELETE_ADAPTER", target=a.name)
            self._refresh_adapters()

    # ============================================================
    # 7. 数据安全与审计
    # ============================================================
    def _build_security_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # 上：审计日志
        upper = QWidget()
        ul = QVBoxLayout(upper)
        op = QHBoxLayout()
        op.addWidget(QLabel("动作过滤："))
        self.audit_action_combo = QComboBox()
        self.audit_action_combo.addItems(["全部", "LOGIN_SUCCESS", "LOGIN_FAILED",
                                          "LOGOUT", "CREATE_CONSULTATION", "COMPLETE_CONSULTATION",
                                          "APPROVE_REPORT", "CREATE_USER", "UPDATE_USER", "DELETE_USER",
                                          "RESET_PASSWORD", "CHANGE_PASSWORD",
                                          "UPLOAD_MEDICAL_IMAGE", "DELETE_MEDICAL_IMAGE",
                                          "CREATE_AGENT", "UPDATE_AGENT", "TEST_ADAPTER"])
        self.audit_action_combo.setStyleSheet(self._input_style())
        op.addWidget(self.audit_action_combo)
        op.addWidget(QLabel("用户过滤："))
        self.audit_user_combo = QComboBox()
        self.audit_user_combo.addItem("全部", "")
        for u in self.ctx.user_manager.list_users():
            self.audit_user_combo.addItem(f"{u.username} ({u.display_name})", u.user_id)
        self.audit_user_combo.setStyleSheet(self._input_style())
        op.addWidget(self.audit_user_combo)
        b_filter = self._toolbar_button("查询", self._primary_btn())
        b_filter.clicked.connect(self._refresh_audit)
        op.addWidget(b_filter)
        b_export = self._toolbar_button("导出日志")
        b_export.clicked.connect(self._export_audit)
        op.addWidget(b_export)
        op.addStretch()
        ul.addLayout(op)

        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(6)
        self.audit_table.setHorizontalHeaderLabels(["时间", "用户", "动作", "目标", "详情", "IP"])
        self.audit_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.audit_table.setStyleSheet(self._table_style())
        ul.addWidget(self.audit_table)
        splitter.addWidget(upper)

        # 下：安全配置
        lower = QWidget()
        ll = QVBoxLayout(lower)
        s_title = QLabel("加密与安全配置")
        s_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        ll.addWidget(s_title)

        sec_form = QFormLayout()
        sec_form.setSpacing(10)
        self.check_tls = QCheckBox("启用 TLS1.3 传输加密")
        sec_form.addRow("", self.check_tls)
        self.combo_storage_enc = QComboBox()
        self.combo_storage_enc.addItems(["AES-256", "国密 SM4"])
        sec_form.addRow("存储加密：", self.combo_storage_enc)
        self.check_sm2 = QCheckBox("已上传国密 SM2 电子签名证书")
        sec_form.addRow("", self.check_sm2)
        self.check_dlp = QCheckBox("禁止批量导出全量患者病历（DLP 防泄漏）")
        sec_form.addRow("", self.check_dlp)
        self.spin_bulk = QSpinBox()
        self.spin_bulk.setRange(10, 10000); self.spin_bulk.setSuffix(" 条")
        sec_form.addRow("批量导出阈值：", self.spin_bulk)
        self.combo_compliance = QComboBox()
        self.combo_compliance.addItems(["等保二级", "等保三级", "等保四级"])
        sec_form.addRow("合规等级：", self.combo_compliance)
        self.check_research_consent = QCheckBox("科研使用需患者知情同意")
        sec_form.addRow("", self.check_research_consent)
        for w in [self.check_tls, self.combo_storage_enc, self.check_sm2, self.check_dlp,
                  self.spin_bulk, self.combo_compliance, self.check_research_consent]:
            w.setStyleSheet(self._input_style())
        ll.addLayout(sec_form)

        # 脱敏规则
        mask_title = QLabel("数据脱敏规则（按场景配置）")
        mask_title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        ll.addWidget(mask_title)

        self.mask_table = QTableWidget()
        self.mask_table.setColumnCount(5)
        self.mask_table.setHorizontalHeaderLabels(
            ["场景", "屏蔽姓名", "屏蔽身份证", "屏蔽电话", "屏蔽住址"]
        )
        self.mask_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.mask_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.mask_table.setStyleSheet(self._table_style())
        ll.addWidget(self.mask_table)

        b_save_sec = self._toolbar_button("保存安全配置", self._primary_btn())
        b_save_sec.clicked.connect(self._save_security)
        ll.addWidget(b_save_sec)
        splitter.addWidget(lower)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        return page

    def _refresh_audit(self):
        action = self.audit_action_combo.currentText()
        action = None if action == "全部" else action
        uid = self.audit_user_combo.currentData()
        uid = None if not uid else uid
        logs = self.ctx.audit_logger.get_logs(limit=1000, action=action, user_id=uid)
        t = self.audit_table
        t.setRowCount(len(logs))
        for i, e in enumerate(logs):
            t.setItem(i, 0, QTableWidgetItem(str(e.get("timestamp", ""))[:19]))
            t.setItem(i, 1, QTableWidgetItem(str(e.get("username", ""))))
            t.setItem(i, 2, QTableWidgetItem(str(e.get("action", ""))))
            t.setItem(i, 3, QTableWidgetItem(str(e.get("target", ""))))
            t.setItem(i, 4, QTableWidgetItem(str(e.get("detail", ""))))
            t.setItem(i, 5, QTableWidgetItem(str(e.get("ip", ""))))

    def _export_audit(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出审计日志", "audit_export.txt", "文本文件 (*.txt)"
        )
        if file_path:
            try:
                logs = self.ctx.audit_logger.get_logs(limit=100000)
                with open(file_path, "w", encoding="utf-8") as f:
                    for e in logs:
                        f.write(
                            f"{e.get('timestamp','')} | {e.get('username','')} | "
                            f"{e.get('action','')} | {e.get('target','')} | "
                            f"{e.get('detail','')}\n"
                        )
                self._audit("EXPORT_AUDIT_LOG", detail=f"共 {len(logs)} 条")
                QMessageBox.information(self, "成功", "审计日志已导出")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def _save_security(self):
        sec = self.admin_cfg.security
        sec.tls_enabled = self.check_tls.isChecked()
        sec.storage_encryption = self.combo_storage_enc.currentText()
        sec.sm2_cert_uploaded = self.check_sm2.isChecked()
        sec.dlp_block_bulk_export = self.check_dlp.isChecked()
        sec.bulk_export_threshold = self.spin_bulk.value()
        sec.compliance_level = self.combo_compliance.currentText()
        sec.research_consent_required = self.check_research_consent.isChecked()
        self.admin_cfg.save_all()
        self._audit("UPDATE_SECURITY_CONFIG", detail=f"合规={sec.compliance_level}")
        QMessageBox.information(self, "成功", "安全配置已保存")

    # ============================================================
    # 8. 质控统计报表
    # ============================================================
    def _build_quality_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # 上：业务指标看板
        upper = QWidget()
        ul = QVBoxLayout(upper)
        ul.setSpacing(10)
        stat_title = QLabel("业务指标看板")
        stat_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        ul.addWidget(stat_title)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.qc_card_total = self._stat_card("会诊总量", "0", self.PRIMARY)
        self.qc_card_approved = self._stat_card("已审核", "0", self.SUCCESS)
        self.qc_card_pending = self._stat_card("待审核", "0", self.WARN)
        self.qc_card_users = self._stat_card("活跃用户", "0", "#9c27b0")
        for c in [self.qc_card_total, self.qc_card_approved, self.qc_card_pending, self.qc_card_users]:
            cards.addWidget(c)
        ul.addLayout(cards)

        # 业务分布表
        self.qc_dist_table = QTableWidget()
        self.qc_dist_table.setColumnCount(4)
        self.qc_dist_table.setHorizontalHeaderLabels(["会诊类型", "数量", "占比", "已审核"])
        self.qc_dist_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.qc_dist_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.qc_dist_table.setStyleSheet(self._table_style())
        ul.addWidget(self.qc_dist_table)
        splitter.addWidget(upper)

        # 下：质控评分模板
        lower = QWidget()
        ll = QVBoxLayout(lower)
        qc_title = QLabel("质控评分模板")
        qc_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        ll.addWidget(qc_title)

        op = QHBoxLayout()
        b_add_qc = self._toolbar_button("+ 新增评分项", self._primary_btn())
        b_add_qc.clicked.connect(self._add_quality_item)
        op.addWidget(b_add_qc)
        b_edit_qc = self._toolbar_button("编辑")
        b_edit_qc.clicked.connect(self._edit_quality_item)
        op.addWidget(b_edit_qc)
        b_del_qc = self._toolbar_button("删除", self._danger_btn())
        b_del_qc.clicked.connect(self._delete_quality_item)
        op.addWidget(b_del_qc)
        op.addStretch()
        ll.addLayout(op)

        self.qc_item_table = QTableWidget()
        self.qc_item_table.setColumnCount(5)
        self.qc_item_table.setHorizontalHeaderLabels(
            ["评分项ID", "名称", "说明", "最大分值", "权重"]
        )
        self.qc_item_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.qc_item_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.qc_item_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.qc_item_table.setStyleSheet(self._table_style())
        ll.addWidget(self.qc_item_table)
        splitter.addWidget(lower)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        return page

    def _refresh_quality(self):
        reports = self.ctx.global_index.list_all_reports()
        # 统计
        total = len(reports)
        approved = sum(1 for r in reports if r.get("status") == "APPROVED")
        pending = total - approved
        users_set = set(r.get("user_id", "") for r in reports)
        self.qc_card_total.value_label.setText(str(total))  # type: ignore[attr-defined]
        self.qc_card_approved.value_label.setText(str(approved))  # type: ignore[attr-defined]
        self.qc_card_pending.value_label.setText(str(pending))  # type: ignore[attr-defined]
        self.qc_card_users.value_label.setText(str(len(users_set)))  # type: ignore[attr-defined]

        # 按类型统计
        from collections import Counter
        type_counter = Counter(r.get("consultation_type", "未分类") for r in reports)
        type_approved = Counter(
            r.get("consultation_type", "未分类") for r in reports if r.get("status") == "APPROVED"
        )
        t = self.qc_dist_table
        t.setRowCount(len(type_counter))
        for i, (ctype, cnt) in enumerate(sorted(type_counter.items())):
            t.setItem(i, 0, QTableWidgetItem(ctype))
            t.setItem(i, 1, QTableWidgetItem(str(cnt)))
            pct = f"{cnt*100/total:.1f}%" if total else "0%"
            t.setItem(i, 2, QTableWidgetItem(pct))
            t.setItem(i, 3, QTableWidgetItem(str(type_approved.get(ctype, 0))))

        # 质控项
        items = self.admin_cfg.quality_items
        qt = self.qc_item_table
        qt.setRowCount(len(items))
        for i, q in enumerate(items):
            qt.setItem(i, 0, QTableWidgetItem(q.item_id))
            qt.setItem(i, 1, QTableWidgetItem(q.name))
            qt.setItem(i, 2, QTableWidgetItem(q.description))
            qt.setItem(i, 3, QTableWidgetItem(f"{q.max_score:.1f}"))
            qt.setItem(i, 4, QTableWidgetItem(f"{q.weight:.2f}"))

    def _add_quality_item(self):
        fields = [
            ("item_id", "评分项ID", "text", None, True),
            ("name", "名称", "text", None, True),
            ("description", "说明", "textarea", None, False),
            ("max_score", "最大分值", "doublespin", (1.0, 100.0, 1.0, 1), True),
            ("weight", "权重", "doublespin", (0.1, 5.0, 0.1, 2), True),
        ]
        dialog = KeyValueEditDialog("新增质控评分项", fields, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                d = dialog.result_data
                self.admin_cfg.add_quality_item(QualityControlItem(
                    item_id=d["item_id"], name=d["name"], description=d.get("description", ""),
                    max_score=float(d["max_score"]), weight=float(d["weight"])
                ))
                self._audit("CREATE_QUALITY_ITEM", target=d["item_id"])
                self._refresh_quality()
            except ValueError as e:
                QMessageBox.warning(self, "警告", str(e))

    def _edit_quality_item(self):
        row = self.qc_item_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选中一个评分项")
            return
        q = self.admin_cfg.quality_items[row]
        fields = [
            ("name", "名称", "text", None, True),
            ("description", "说明", "textarea", None, False),
            ("max_score", "最大分值", "doublespin", (1.0, 100.0, 1.0, 1), True),
            ("weight", "权重", "doublespin", (0.1, 5.0, 0.1, 2), True),
        ]
        dialog = KeyValueEditDialog("编辑质控评分项", fields, self, initial={
            "name": q.name, "description": q.description,
            "max_score": q.max_score, "weight": q.weight
        })
        if dialog.exec() == QDialog.DialogCode.Accepted:
            d = dialog.result_data
            self.admin_cfg.update_quality_item(q.item_id,
                name=d["name"], description=d.get("description", ""),
                max_score=float(d["max_score"]), weight=float(d["weight"]))
            self._audit("UPDATE_QUALITY_ITEM", target=q.item_id)
            self._refresh_quality()

    def _delete_quality_item(self):
        row = self.qc_item_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选中一个评分项")
            return
        qid = self.qc_item_table.item(row, 0).text()
        self.admin_cfg.delete_quality_item(qid)
        self._audit("DELETE_QUALITY_ITEM", target=qid)
        self._refresh_quality()

    # ============================================================
    # 9. 系统配置运维
    # ============================================================
    def _build_config_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        scroll_content = QWidget()
        sl = QVBoxLayout(scroll_content)
        sl.setSpacing(12)

        # 全局参数
        sys_group = QGroupBox("系统全局参数")
        sys_group.setStyleSheet(self._group_style())
        sys_group.setGraphicsEffect(self._shadow())
        sys_form = QFormLayout(sys_group)
        sys_form.setSpacing(10)
        self.edit_hospital = QLineEdit()
        sys_form.addRow("医院名称：", self.edit_hospital)
        self.edit_campus = QLineEdit()
        sys_form.addRow("院区信息：", self.edit_campus)
        self.spin_concurrency = QSpinBox()
        self.spin_concurrency.setRange(1, 1000)
        sys_form.addRow("最大并发会诊：", self.spin_concurrency)
        self.spin_record_limit = QSpinBox()
        self.spin_record_limit.setRange(10, 500)
        sys_form.addRow("病历加载上限：", self.spin_record_limit)
        self.spin_vector = QSpinBox()
        self.spin_vector.setRange(1, 100)
        sys_form.addRow("向量检索并发：", self.spin_vector)
        self.edit_storage = QLineEdit()
        sys_form.addRow("文件存储路径：", self.edit_storage)
        self.spin_file_size = QSpinBox()
        self.spin_file_size.setRange(1, 500); self.spin_file_size.setSuffix(" MB")
        sys_form.addRow("单文件大小限制：", self.spin_file_size)
        for w in [self.edit_hospital, self.edit_campus, self.spin_concurrency,
                  self.spin_record_limit, self.spin_vector, self.edit_storage, self.spin_file_size]:
            w.setStyleSheet(self._input_style())
        sl.addWidget(sys_group)

        # 消息通知
        notif_group = QGroupBox("消息通知配置")
        notif_group.setStyleSheet(self._group_style())
        notif_group.setGraphicsEffect(self._shadow())
        notif_layout = QVBoxLayout(notif_group)
        self.channel_checks: dict = {}
        ch_row = QHBoxLayout()
        for ch in ["站内信", "企业微信", "钉钉", "短信", "邮件"]:
            cb = QCheckBox(ch)
            cb.setStyleSheet(self._input_style())
            self.channel_checks[ch] = cb
            ch_row.addWidget(cb)
        ch_row.addStretch()
        notif_layout.addLayout(ch_row)
        notif_layout.addWidget(QLabel("通知模板（占位符：{consultation_id}）"))
        self.template_edits: dict = {}
        for key in ["consultation_submitted", "consultation_completed",
                    "consultation_timeout", "qc_rectification"]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{key}："))
            edit = QLineEdit()
            edit.setStyleSheet(self._input_style())
            self.template_edits[key] = edit
            row.addWidget(edit)
            notif_layout.addLayout(row)
        sl.addWidget(notif_group)

        # 备份与灾备
        backup_group = QGroupBox("备份与灾备")
        backup_group.setStyleSheet(self._group_style())
        backup_group.setGraphicsEffect(self._shadow())
        backup_form = QFormLayout(backup_group)
        self.check_auto_backup = QCheckBox("启用定时自动备份")
        backup_form.addRow("", self.check_auto_backup)
        self.spin_backup_period = QSpinBox()
        self.spin_backup_period.setRange(1, 168); self.spin_backup_period.setSuffix(" 小时")
        backup_form.addRow("备份周期：", self.spin_backup_period)
        self.spin_keep_count = QSpinBox()
        self.spin_keep_count.setRange(1, 90); self.spin_keep_count.setSuffix(" 份")
        backup_form.addRow("保留份数：", self.spin_keep_count)
        self.check_degraded = QCheckBox("AI 引擎故障时切换降级模式")
        backup_form.addRow("", self.check_degraded)
        for w in [self.check_auto_backup, self.spin_backup_period, self.spin_keep_count, self.check_degraded]:
            w.setStyleSheet(self._input_style())
        sl.addWidget(backup_group)

        # 监控告警说明
        mon_group = QGroupBox("监控与告警")
        mon_group.setStyleSheet(self._group_style())
        mon_group.setGraphicsEffect(self._shadow())
        mon_form = QFormLayout(mon_group)
        mon_form.addRow("服务监控：", QLabel("微服务 CPU / 内存 / 接口响应（Prometheus + Grafana）"))
        mon_form.addRow("链路追踪：", QLabel("Jaeger 全链路日志，定位 AI 推理慢节点"))
        mon_form.addRow("告警策略：", QLabel("服务宕机 / AI 超时 / 同步失败 / 异常访问分级告警"))
        sl.addWidget(mon_group)

        # 插件管理
        plug_group = QGroupBox("插件与版本管理")
        plug_group.setStyleSheet(self._group_style())
        plug_group.setGraphicsEffect(self._shadow())
        plug_layout = QVBoxLayout(plug_group)
        plug_op = QHBoxLayout()
        b_refresh_plug = self._toolbar_button("刷新", self._primary_btn())
        b_refresh_plug.clicked.connect(self._refresh_plugins)
        plug_op.addWidget(b_refresh_plug)
        b_toggle_plug = self._toolbar_button("启用 / 停用")
        b_toggle_plug.clicked.connect(self._toggle_plugin)
        plug_op.addWidget(b_toggle_plug)
        plug_op.addStretch()
        plug_layout.addLayout(plug_op)

        self.plugin_table = QTableWidget()
        self.plugin_table.setColumnCount(5)
        self.plugin_table.setHorizontalHeaderLabels(["插件ID", "名称", "类型", "版本", "状态"])
        self.plugin_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.plugin_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.plugin_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.plugin_table.setStyleSheet(self._table_style())
        plug_layout.addWidget(self.plugin_table)
        sl.addWidget(plug_group)

        # 保存按钮
        b_save_config = self._toolbar_button("保存全部配置", self._primary_btn())
        b_save_config.setMinimumHeight(40)
        b_save_config.clicked.connect(self._save_all_config)
        sl.addWidget(b_save_config)

        sl.addStretch()
        scroll = self._make_scroll(scroll_content)
        layout.addWidget(scroll)
        return page

    def _refresh_config(self):
        s = self.admin_cfg.system
        self.edit_hospital.setText(s.hospital_name)
        self.edit_campus.setText(s.campus_info)
        self.spin_concurrency.setValue(s.max_concurrent_consultations)
        self.spin_record_limit.setValue(s.record_load_limit)
        self.spin_vector.setValue(s.vector_search_concurrency)
        self.edit_storage.setText(s.pdf_storage_path)
        self.spin_file_size.setValue(s.single_file_size_limit_mb)

        n = self.admin_cfg.notification
        for ch, cb in self.channel_checks.items():
            cb.setChecked(n.channels.get(ch, False))
        for key, edit in self.template_edits.items():
            edit.setText(n.templates.get(key, ""))

        b = self.admin_cfg.backup
        self.check_auto_backup.setChecked(b.auto_backup_enabled)
        self.spin_backup_period.setValue(b.backup_period_hours)
        self.spin_keep_count.setValue(b.keep_backup_count)
        self.check_degraded.setChecked(b.degraded_mode_on_ai_failure)

        self._refresh_plugins()

    def _refresh_plugins(self):
        plugins = self.admin_cfg.plugins
        t = self.plugin_table
        t.setRowCount(len(plugins))
        for i, p in enumerate(plugins):
            t.setItem(i, 0, QTableWidgetItem(p.plugin_id))
            t.setItem(i, 1, QTableWidgetItem(p.name))
            t.setItem(i, 2, QTableWidgetItem(p.plugin_type))
            t.setItem(i, 3, QTableWidgetItem(p.version))
            status = QTableWidgetItem("启用" if p.enabled else "停用")
            status.setForeground(QColor(self.SUCCESS if p.enabled else self.DANGER))
            t.setItem(i, 4, status)

    def _toggle_plugin(self):
        row = self.plugin_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "请先选中一个插件")
            return
        pid = self.plugin_table.item(row, 0).text()
        new_state = self.admin_cfg.toggle_plugin(pid)
        self._audit("TOGGLE_PLUGIN", target=pid, detail="启用" if new_state else "停用")
        self._refresh_plugins()

    def _save_all_config(self):
        s = self.admin_cfg.system
        s.hospital_name = self.edit_hospital.text().strip() or s.hospital_name
        s.campus_info = self.edit_campus.text().strip()
        s.max_concurrent_consultations = self.spin_concurrency.value()
        s.record_load_limit = self.spin_record_limit.value()
        s.vector_search_concurrency = self.spin_vector.value()
        s.pdf_storage_path = self.edit_storage.text().strip() or s.pdf_storage_path
        s.single_file_size_limit_mb = self.spin_file_size.value()

        n = self.admin_cfg.notification
        for ch, cb in self.channel_checks.items():
            n.channels[ch] = cb.isChecked()
        for key, edit in self.template_edits.items():
            n.templates[key] = edit.text().strip()

        b = self.admin_cfg.backup
        b.auto_backup_enabled = self.check_auto_backup.isChecked()
        b.backup_period_hours = self.spin_backup_period.value()
        b.keep_backup_count = self.spin_keep_count.value()
        b.degraded_mode_on_ai_failure = self.check_degraded.isChecked()

        self.admin_cfg.save_all()
        self._audit("UPDATE_SYSTEM_CONFIG", detail="全局参数/通知/备份")
        QMessageBox.information(self, "成功", "系统配置已保存")

    # ============================================================
    # 10. 患者档案管理
    # ============================================================
    def _build_patient_archive_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        op = QHBoxLayout()
        op.addWidget(QLabel("患者姓名："))
        self.archive_search = QLineEdit()
        self.archive_search.setPlaceholderText("输入姓名或患者ID检索")
        self.archive_search.setStyleSheet(self._input_style())
        op.addWidget(self.archive_search)
        b_search = self._toolbar_button("检索", self._primary_btn())
        b_search.clicked.connect(self._refresh_patient_archive)
        op.addWidget(b_search)
        b_refresh = self._toolbar_button("刷新全部")
        b_refresh.clicked.connect(self._refresh_patient_archive)
        op.addWidget(b_refresh)
        op.addStretch()
        layout.addLayout(op)

        self.archive_table = QTableWidget()
        self.archive_table.setColumnCount(7)
        self.archive_table.setHorizontalHeaderLabels(
            ["患者ID", "姓名", "性别", "年龄", "科室", "主管医生", "关联会诊数"]
        )
        self.archive_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.archive_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.archive_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.archive_table.setStyleSheet(self._table_style())
        layout.addWidget(self.archive_table)

        # 异常指标检索说明
        alert_group = QGroupBox("异常指标全局检索")
        alert_group.setStyleSheet(self._group_style())
        alert_group.setGraphicsEffect(self._shadow())
        alert_layout = QFormLayout(alert_group)
        alert_layout.addRow("说明：", QLabel("批量筛选存在危急值、高危风险评分（NEWS/APACHE II）患者"))
        alert_layout.addRow("操作方式：", QLabel("选择患者后可查看完整 360 病历视图；高危患者可标记随访"))
        layout.addWidget(alert_group)

        layout.addStretch()
        return page

    def _refresh_patient_archive(self):
        """从所有用户的患者空间汇总患者档案（去重）"""
        keyword = self.archive_search.text().strip().lower()
        # 遍历所有用户空间（使用统一的 get_project_root 兼容打包环境）
        archive = {}
        try:
            from ..core.admin_config import get_project_root
            project_root = get_project_root()
            userdata_root = project_root / "data" / "userdata"
            if userdata_root.exists():
                for user_dir in userdata_root.iterdir():
                    if not user_dir.is_dir():
                        continue
                    patients_dir = user_dir / "patients"
                    if not patients_dir.exists():
                        continue
                    for f in patients_dir.glob("*.json"):
                        try:
                            import json
                            with open(f, "r", encoding="utf-8") as fh:
                                data = json.load(fh)
                            pid = data.get("patient_id", "")
                            if not pid or pid in archive:
                                continue
                            name = data.get("name", "")
                            if keyword and keyword not in name.lower() and keyword not in pid.lower():
                                continue
                            archive[pid] = {
                                "patient_id": pid,
                                "name": name,
                                "gender": data.get("gender", ""),
                                "age": data.get("age", 0),
                                "department": data.get("department", ""),
                                "attending_doctor": data.get("attending_doctor", ""),
                            }
                        except Exception:
                            continue
        except Exception:
            pass

        # 关联会诊数
        reports = self.ctx.global_index.list_all_reports()
        from collections import Counter
        consult_counter = Counter(r.get("patient_id", "") for r in reports)
        for pid in archive:
            archive[pid]["consult_count"] = consult_counter.get(pid, 0)

        rows = list(archive.values())
        t = self.archive_table
        t.setRowCount(len(rows))
        for i, p in enumerate(rows):
            t.setItem(i, 0, QTableWidgetItem(p["patient_id"]))
            t.setItem(i, 1, QTableWidgetItem(p["name"]))
            t.setItem(i, 2, QTableWidgetItem(str(p["gender"])))
            t.setItem(i, 3, QTableWidgetItem(str(p["age"])))
            t.setItem(i, 4, QTableWidgetItem(p["department"]))
            t.setItem(i, 5, QTableWidgetItem(p["attending_doctor"]))
            cnt_item = QTableWidgetItem(str(p.get("consult_count", 0)))
            cnt_item.setForeground(QColor(self.WARN if p.get("consult_count", 0) > 0 else self.SECONDARY))
            t.setItem(i, 6, cnt_item)

    # ============================================================
    # 独立模块（与系统管理同级，由主窗口作为顶层页面展示）
    # ============================================================
    def get_integration_page(self) -> QWidget:
        """构建并返回"系统集成"独立页面（懒加载）"""
        if not hasattr(self, "_integration_page"):
            self._integration_page = self._build_integration_tab()
            self.refresh_integration()
        return self._integration_page

    def get_security_page(self) -> QWidget:
        """构建并返回"数据安全审计"独立页面（懒加载）"""
        if not hasattr(self, "_security_page"):
            self._security_page = self._build_security_tab()
            self.refresh_security()
        return self._security_page

    def get_quality_page(self) -> QWidget:
        """构建并返回"质控统计报表"独立页面（懒加载）"""
        if not hasattr(self, "_quality_page"):
            self._quality_page = self._build_quality_tab()
            self.refresh_quality()
        return self._quality_page

    def refresh_integration(self):
        if hasattr(self, "_integration_page"):
            try:
                self._refresh_adapters()
            except Exception as e:
                _diag_log(f"[错误] _refresh_adapters 失败: {e}")

    def refresh_security(self):
        if hasattr(self, "_security_page"):
            try:
                self._refresh_audit()
            except Exception as e:
                _diag_log(f"[错误] _refresh_audit 失败: {e}")
            try:
                self._refresh_security_config_ui()
            except Exception as e:
                _diag_log(f"[错误] 安全配置刷新失败: {e}")

    def refresh_quality(self):
        if hasattr(self, "_quality_page"):
            try:
                self._refresh_quality()
            except Exception as e:
                _diag_log(f"[错误] _refresh_quality 失败: {e}")

    def _refresh_security_config_ui(self):
        """刷新数据安全审计页的脱敏规则与安全配置控件"""
        if self.admin_cfg is None:
            return
        mask_rows = self.admin_cfg.desensitization
        mt = getattr(self, "mask_table", None)
        if mt is not None:
            mt.setRowCount(len(mask_rows))
            for i, m in enumerate(mask_rows):
                mt.setItem(i, 0, QTableWidgetItem(m.scene))
                mt.setItem(i, 1, QTableWidgetItem("✓" if m.mask_patient_name else "—"))
                mt.setItem(i, 2, QTableWidgetItem("✓" if m.mask_id_card else "—"))
                mt.setItem(i, 3, QTableWidgetItem("✓" if m.mask_phone else "—"))
                mt.setItem(i, 4, QTableWidgetItem("✓" if m.mask_address else "—"))
        sec = self.admin_cfg.security
        if hasattr(self, "check_tls"):
            self.check_tls.setChecked(sec.tls_enabled)
            idx = self.combo_storage_enc.findText(sec.storage_encryption)
            if idx >= 0:
                self.combo_storage_enc.setCurrentIndex(idx)
            self.check_sm2.setChecked(sec.sm2_cert_uploaded)
            self.check_dlp.setChecked(sec.dlp_block_bulk_export)
            self.spin_bulk.setValue(sec.bulk_export_threshold)
            idx = self.combo_compliance.findText(sec.compliance_level)
            if idx >= 0:
                self.combo_compliance.setCurrentIndex(idx)
            self.check_research_consent.setChecked(sec.research_consent_required)

    # ============================================================
    # 总刷新
    # ============================================================
    def _refresh_all(self):
        """安全刷新系统管理内的所有模块（独立模块由主窗口各自刷新）"""
        refresh_methods = [
            "_refresh_dashboard",
            "_refresh_users",
            "_refresh_consultations",
            "_refresh_agents",
            "_refresh_case_library",
            "_refresh_config",
            "_refresh_patient_archive",
        ]
        for method_name in refresh_methods:
            method = getattr(self, method_name, None)
            if method is None:
                continue
            try:
                method()
                _diag_log(f"{method_name} 刷新成功")
            except Exception as e:
                _diag_log(f"[错误] {method_name} 刷新失败: {e}")
                import traceback
                _diag_log(traceback.format_exc())
