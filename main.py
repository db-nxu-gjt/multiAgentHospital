"""
医院虚拟会诊系统 - 桌面应用入口

启动流程：
1. 启动 QApplication
2. 显示登录窗口
3. 登录成功 -> 创建主窗口（医生工作台）并显示
4. 主窗口退出登录 -> 关闭主窗口，重新显示登录窗口
5. 登录窗口关闭 -> 退出应用
"""
import sys
from pathlib import Path

# 将src目录添加到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import QApplication

from src.core.user import User
from src.core.session import AuditLogger
from src.ui.login_window import LoginWindow
from src.ui.main_window import MainWindow


class Application:
    """应用控制器：管理登录/主窗口的生命周期"""

    REMEMBER_KEY = "auth/remembered_username"

    def __init__(self, app: QApplication):
        self.app = app
        self.settings = QSettings("MultiAgentHospital", "VCS")
        self.login_window: LoginWindow = None
        self.main_window: MainWindow = None

    def start(self):
        self._show_login()
        return self.app.exec()

    def _show_login(self):
        # 关闭旧主窗口（如有）
        if self.main_window is not None:
            self.main_window.close()
            self.main_window = None

        self.login_window = LoginWindow()
        # 回填记忆的用户名
        remembered = self.settings.value(self.REMEMBER_KEY, "", type=str)
        self.login_window.set_remembered_username(remembered)
        self.login_window.login_success.connect(self._on_login_success)
        self.login_window.show()

    def _on_login_success(self, user: User):
        # 记忆用户名
        self.settings.setValue(self.REMEMBER_KEY,
                               self.login_window.get_remembered_username())

        # 关闭登录窗口
        self.login_window.hide()
        self.login_window.deleteLater()
        self.login_window = None

        # 创建并显示主窗口
        self.main_window = MainWindow(user)
        self.main_window.logout_requested.connect(self._on_logout)
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _on_logout(self):
        # 退出登录：返回登录界面
        self._show_login()


def main():
    # 启用高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("医院虚拟会诊系统")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("MultiAgentHospital")
    app.setStyle("Fusion")

    controller = Application(app)
    sys.exit(controller.start())


if __name__ == "__main__":
    main()
