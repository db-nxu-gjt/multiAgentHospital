"""
登录窗口与认证流程

设计要点：
- 使用自绘矢量图标（替代 emoji），避免打包后字体差异导致截断或显示异常
- 居中卡片式登录界面，风格现代、专业、大方
- 登录成功后通过信号把已认证 User 传递给主应用
- 密码错误、账户禁用等场景给出明确提示
- 登录尝试次数限制（5 次失败后短暂锁定），防止暴力破解
"""
import time
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QCheckBox
)

from ..core.user import User, UserManager, get_user_manager
from ..core.session import AuditLogger
from .icons import hospital_icon


class LoginWindow(QWidget):
    """登录窗口"""

    login_success = pyqtSignal(object)
    login_failed = pyqtSignal(str)

    MAX_ATTEMPTS = 5
    LOCK_SECONDS = 30

    PRIMARY = "#2563eb"
    PRIMARY_HOVER = "#1d4ed8"
    PRIMARY_PRESS = "#1e40af"
    TEXT_MAIN = "#1e293b"
    TEXT_SECOND = "#64748b"
    BORDER = "#e2e8f0"
    BG = "#f1f5f9"
    CARD_BG = "#ffffff"
    ERROR = "#dc2626"

    def __init__(self, user_manager: UserManager = None,
                 audit_logger: AuditLogger = None):
        super().__init__()
        self.user_manager = user_manager or get_user_manager()
        self.audit_logger = audit_logger or AuditLogger()
        self._failed_count = 0
        self._lock_until = 0.0
        self._init_ui()
        self._refresh_lock_state()

    def _init_ui(self):
        self.setWindowTitle("医院虚拟会诊系统 - 登录")
        # 固定窗口大小，防止用户缩小导致内容被压缩
        self.setFixedSize(500, 800)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)

        self.setStyleSheet(f"""
            QWidget {{ background: {self.BG}; }}
            QLabel {{ color: {self.TEXT_MAIN}; }}
        """)

        # 主布局：标题区 + 登录卡片
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 50, 40, 50)
        main_layout.setSpacing(30)

        # ---- 标题区 ----
        icon_label = QLabel()
        icon_label.setPixmap(hospital_icon(64, self.PRIMARY, "#dbeafe"))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setMinimumHeight(80)
        main_layout.addWidget(icon_label)

        title = QLabel("医院虚拟会诊系统")
        title.setFont(QFont("Microsoft YaHei", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setMinimumHeight(40)
        main_layout.addWidget(title)

        subtitle = QLabel("VCS · AI 赋能多学科协作会诊平台")
        subtitle.setFont(QFont("Microsoft YaHei", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {self.TEXT_SECOND};")
        subtitle.setMinimumHeight(24)
        main_layout.addWidget(subtitle)

        # ---- 登录卡片 ----
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {self.CARD_BG};
                border: 1px solid {self.BORDER};
                border-radius: 16px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(18)

        # 卡片标题
        card_title = QLabel("用户登录")
        card_title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        card_title.setMinimumHeight(32)
        card_layout.addWidget(card_title)

        # 用户名输入
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("请输入用户名")
        self.username_edit.setMinimumHeight(48)
        self.username_edit.setFont(QFont("Microsoft YaHei", 14))
        self.username_edit.setStyleSheet(self._input_style())
        self.username_edit.returnPressed.connect(self._on_login)
        card_layout.addWidget(self.username_edit)

        # 密码输入
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setMinimumHeight(48)
        self.password_edit.setFont(QFont("Microsoft YaHei", 14))
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setStyleSheet(self._input_style())
        self.password_edit.returnPressed.connect(self._on_login)
        card_layout.addWidget(self.password_edit)

        # 记住用户名
        self.remember_check = QCheckBox("记住用户名")
        self.remember_check.setFont(QFont("Microsoft YaHei", 12))
        self.remember_check.setStyleSheet(f"color: {self.TEXT_SECOND};")
        self.remember_check.setMinimumHeight(32)
        card_layout.addWidget(self.remember_check)

        # 登录按钮
        self.btn_login = QPushButton("登 录")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setMinimumHeight(52)
        self.btn_login.setFont(QFont("Microsoft YaHei", 15, QFont.Weight.Bold))
        self.btn_login.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.PRIMARY};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{ background-color: {self.PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background-color: {self.PRIMARY_PRESS}; }}
            QPushButton:disabled {{ background-color: #93c5fd; }}
        """)
        self.btn_login.clicked.connect(self._on_login)
        card_layout.addWidget(self.btn_login)

        # 退出按钮
        self.btn_exit = QPushButton("退 出")
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.setMinimumHeight(46)
        self.btn_exit.setFont(QFont("Microsoft YaHei", 13))
        self.btn_exit.setStyleSheet(f"""
            QPushButton {{
                background-color: #f8fafc;
                color: {self.TEXT_SECOND};
                border: 1px solid {self.BORDER};
                border-radius: 10px;
            }}
            QPushButton:hover {{ background-color: #f1f5f9; border-color: #cbd5e1; }}
        """)
        self.btn_exit.clicked.connect(self.close)
        card_layout.addWidget(self.btn_exit)

        # 错误提示
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(f"color: {self.ERROR}; font-size: 13px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setMinimumHeight(24)
        card_layout.addWidget(self.error_label)

        main_layout.addWidget(card)

    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                border: 1px solid {self.BORDER};
                border-radius: 10px;
                padding: 10px 14px;
                background: #ffffff;
                color: {self.TEXT_MAIN};
            }}
            QLineEdit:focus {{
                border: 2px solid {self.PRIMARY};
                padding: 9px 13px;
            }}
        """

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def set_remembered_username(self, username: str):
        if username:
            self.username_edit.setText(username)
            self.remember_check.setChecked(True)
            self.password_edit.setFocus()
        else:
            self.username_edit.setFocus()

    def get_remembered_username(self) -> str:
        return self.username_edit.text().strip() if self.remember_check.isChecked() else ""

    def _refresh_lock_state(self):
        now = time.time()
        if now < self._lock_until:
            remaining = int(self._lock_until - now)
            self.btn_login.setEnabled(False)
            self.error_label.setText(f"登录失败次数过多，请 {remaining} 秒后重试")
            QTimer.singleShot(1000, self._refresh_lock_state)
        else:
            self.btn_login.setEnabled(True)
            if self._failed_count > 0 and self._failed_count < self.MAX_ATTEMPTS:
                self.error_label.setText(
                    f"用户名或密码错误（剩余尝试 {self.MAX_ATTEMPTS - self._failed_count} 次）"
                )

    def _on_login(self):
        self.error_label.setText("")
        now = time.time()
        if now < self._lock_until:
            self._refresh_lock_state()
            return

        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            self.error_label.setText("请输入用户名和密码")
            return

        user = self.user_manager.authenticate(username, password)
        if user is None:
            self._failed_count += 1
            self.audit_logger.log(
                user_id="", username=username, action="LOGIN_FAILED",
                detail=f"第 {self._failed_count} 次失败", ip="127.0.0.1"
            )
            if self._failed_count >= self.MAX_ATTEMPTS:
                self._lock_until = time.time() + self.LOCK_SECONDS
                self._failed_count = 0
                self.error_label.setText(f"失败次数过多，已锁定 {self.LOCK_SECONDS} 秒")
            self._refresh_lock_state()
            self.password_edit.clear()
            self.password_edit.setFocus()
            self.login_failed.emit("认证失败")
            return

        self._failed_count = 0
        self._lock_until = 0
        self.user_manager.update_last_login(user.user_id, ip="127.0.0.1")
        self.audit_logger.log(
            user_id=user.user_id, username=user.username,
            action="LOGIN_SUCCESS", ip="127.0.0.1"
        )

        self.login_success.emit(user)
