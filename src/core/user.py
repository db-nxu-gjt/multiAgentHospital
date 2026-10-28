"""
用户系统 - 用户、角色、权限、用户管理

支持三类角色：
- ADMIN：管理员（系统维护、用户管理、全局审计）
- DOCTOR：医生（发起会诊、查看本人记录）
- REVIEWER：审核员（审核会诊报告）

密码使用 hashlib + salt 安全哈希存储，永不明文落盘。
用户数据持久化到 data/users/users.json。
"""
import hashlib
import os
import json
import secrets
import sys
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any


def get_project_root() -> Path:
    """获取项目根目录，兼容开发环境和 PyInstaller 打包环境"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，使用 sys._MEIPASS 获取资源目录
        return Path(sys._MEIPASS)
    else:
        # 开发环境：从当前文件位置推算项目根目录
        return Path(__file__).parent.parent.parent


class Role(Enum):
    """用户角色"""
    ADMIN = "admin"          # 管理员
    DOCTOR = "doctor"        # 医生
    REVIEWER = "reviewer"   # 审核员

    @property
    def display_name(self) -> str:
        return {"admin": "管理员", "doctor": "医生", "reviewer": "审核员"}[self.value]

    @classmethod
    def parse(cls, value: Any) -> "Role":
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.DOCTOR
        v = str(value).strip().lower()
        for m in cls:
            if m.value == v:
                return m
        # 中文别名
        cn_map = {"管理员": cls.ADMIN, "医生": cls.DOCTOR, "审核员": cls.REVIEWER}
        return cn_map.get(str(value), cls.DOCTOR)

    def can_review(self) -> bool:
        """该角色是否具备审核权限（权限定义集中在 Role）"""
        return self in (Role.ADMIN, Role.REVIEWER)


@dataclass
class User:
    """用户实体"""
    user_id: str
    username: str                # 登录名（唯一）
    display_name: str            # 显示名（姓名）
    role: Role
    department: str = ""         # 科室
    title: str = ""               # 职称
    password_hash: str = ""       # 密码哈希（salt:hash 格式）
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    last_login_at: Optional[float] = None
    last_login_ip: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["role"] = self.role.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            user_id=data.get("user_id", ""),
            username=data.get("username", ""),
            display_name=data.get("display_name", ""),
            role=Role.parse(data.get("role")),
            department=data.get("department", ""),
            title=data.get("title", ""),
            password_hash=data.get("password_hash", ""),
            enabled=bool(data.get("enabled", True)),
            created_at=float(data.get("created_at", time.time())),
            last_login_at=data.get("last_login_at"),
            last_login_ip=data.get("last_login_ip", ""),
        )

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_doctor(self) -> bool:
        return self.role == Role.DOCTOR

    @property
    def is_reviewer(self) -> bool:
        return self.role == Role.REVIEWER

    def can_review(self) -> bool:
        """是否具备审核权限：委托给角色权限定义"""
        return self.role.can_review()

    def to_public_dict(self) -> dict:
        """脱敏后的用户信息（不含密码哈希）"""
        d = self.to_dict()
        d.pop("password_hash", None)
        return d


class PasswordHasher:
    """密码哈希工具 - PBKDF2-HMAC-SHA256 + 随机 salt"""

    ITERATIONS = 100_000
    SALT_LEN = 16
    HASH_LEN = 32

    @classmethod
    def hash(cls, password: str) -> str:
        if not password:
            raise ValueError("密码不能为空")
        salt = secrets.token_hex(cls.SALT_LEN)
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"),
            salt.encode("utf-8"), cls.ITERATIONS, cls.HASH_LEN
        )
        return f"{salt}${dk.hex()}"

    @classmethod
    def verify(cls, password: str, stored: str) -> bool:
        if not stored or "$" not in stored:
            return False
        try:
            salt, expected_hex = stored.split("$", 1)
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"),
                salt.encode("utf-8"), cls.ITERATIONS, cls.HASH_LEN
            )
            # 常量时间比较，避免计时攻击
            return secrets.compare_digest(dk.hex(), expected_hex)
        except (ValueError, TypeError):
            return False


class UserManager:
    """用户管理器 - 持久化在 data/users/users.json"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # 默认在项目根目录下的 data/users/
            project_root = get_project_root()
            data_dir = project_root / "data" / "users"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.data_dir / "users.json"
        self._users: Dict[str, User] = {}
        self._username_index: Dict[str, str] = {}  # username -> user_id
        self._load()
        # 首次运行或文件为空时初始化默认管理员
        if not self._users:
            self._init_default_users()

    def _load(self) -> None:
        if not self.users_file.exists():
            return
        try:
            with open(self.users_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for u_data in data.get("users", []):
                user = User.from_dict(u_data)
                self._users[user.user_id] = user
                self._username_index[user.username] = user.user_id
        except (json.JSONDecodeError, OSError) as e:
            # 数据损坏时不抛异常，记录空用户列表
            print(f"⚠ 用户数据文件加载失败: {e}")

    def _save(self) -> None:
        data = {
            "users": [u.to_dict() for u in self._users.values()],
            "version": "1.1",
        }
        # 原子写入：先写临时文件再重命名
        tmp = self.users_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.users_file)

    def _init_default_users(self) -> None:
        """初始化默认管理员账户"""
        admin = User(
            user_id="U_ADMIN",
            username="admin",
            display_name="系统管理员",
            role=Role.ADMIN,
            department="信息科",
            title="管理员",
            password_hash=PasswordHasher.hash("admin123"),
        )
        doctor = User(
            user_id="U_DOCTOR",
            username="doctor",
            display_name="张医生",
            role=Role.DOCTOR,
            department="心内科",
            title="主治医师",
            password_hash=PasswordHasher.hash("doctor123"),
        )
        reviewer = User(
            user_id="U_REVIEWER",
            username="reviewer",
            display_name="李主任",
            role=Role.REVIEWER,
            department="医务科",
            title="主任医师",
            password_hash=PasswordHasher.hash("reviewer123"),
        )
        self._users[admin.user_id] = admin
        self._users[doctor.user_id] = doctor
        self._users[reviewer.user_id] = reviewer
        self._username_index[admin.username] = admin.user_id
        self._username_index[doctor.username] = doctor.user_id
        self._username_index[reviewer.username] = reviewer.user_id
        self._save()

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """认证登录，返回用户对象或 None"""
        user_id = self._username_index.get(username)
        if not user_id:
            return None
        user = self._users.get(user_id)
        if not user or not user.enabled:
            return None
        if not PasswordHasher.verify(password, user.password_hash):
            return None
        return user

    def update_last_login(self, user_id: str, ip: str = "") -> None:
        user = self._users.get(user_id)
        if user:
            user.last_login_at = time.time()
            user.last_login_ip = ip
            self._save()

    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        user_id = self._username_index.get(username)
        return self._users.get(user_id) if user_id else None

    def list_users(self, role: Role = None) -> List[User]:
        users = list(self._users.values())
        if role:
            users = [u for u in users if u.role == role]
        # 按角色、用户名排序
        users.sort(key=lambda u: (u.role.value, u.username))
        return users

    def create_user(self, username: str, display_name: str, role: Role,
                    department: str = "", title: str = "",
                    password: str = None) -> User:
        """新建用户"""
        if not username or not username.strip():
            raise ValueError("用户名不能为空")
        if username in self._username_index:
            raise ValueError(f"用户名 '{username}' 已存在")
        if not display_name:
            raise ValueError("显示名不能为空")
        if not password or len(password) < 6:
            raise ValueError("密码长度不能少于 6 位")

        # 生成 user_id（避免冲突）
        user_id = f"U_{username.upper()}_{secrets.token_hex(3).upper()}"
        while user_id in self._users:
            user_id = f"U_{username.upper()}_{secrets.token_hex(3).upper()}"

        user = User(
            user_id=user_id,
            username=username.strip(),
            display_name=display_name,
            role=role,
            department=department,
            title=title,
            password_hash=PasswordHasher.hash(password),
        )
        self._users[user_id] = user
        self._username_index[user.username] = user_id
        self._save()
        return user

    def update_user(self, user_id: str, **fields) -> User:
        """更新用户字段（除 password_hash 外）"""
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")

        if "username" in fields:
            new_username = fields["username"]
            if new_username and new_username != user.username:
                if new_username in self._username_index:
                    raise ValueError(f"用户名 '{new_username}' 已被占用")
                # 更新索引
                del self._username_index[user.username]
                user.username = new_username
                self._username_index[new_username] = user_id

        if "display_name" in fields:
            user.display_name = fields["display_name"]
        if "role" in fields:
            user.role = Role.parse(fields["role"])
        if "department" in fields:
            user.department = fields["department"]
        if "title" in fields:
            user.title = fields["title"]
        if "enabled" in fields:
            user.enabled = bool(fields["enabled"])

        self._save()
        return user

    def reset_password(self, user_id: str, new_password: str) -> None:
        """重置密码"""
        if not new_password or len(new_password) < 6:
            raise ValueError("密码长度不能少于 6 位")
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")
        user.password_hash = PasswordHasher.hash(new_password)
        self._save()

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """用户自助修改密码"""
        user = self._users.get(user_id)
        if not user:
            return False
        if not PasswordHasher.verify(old_password, user.password_hash):
            return False
        self.reset_password(user_id, new_password)
        return True

    def delete_user(self, user_id: str) -> bool:
        """删除用户（不能删除最后一个管理员）"""
        user = self._users.get(user_id)
        if not user:
            return False
        if user.role == Role.ADMIN:
            admin_count = sum(1 for u in self._users.values() if u.role == Role.ADMIN and u.enabled)
            if admin_count <= 1:
                raise ValueError("系统至少需要保留 1 个启用的管理员，无法删除")
        del self._users[user_id]
        if user.username in self._username_index:
            del self._username_index[user.username]
        self._save()
        return True

    def user_count(self) -> int:
        return len(self._users)

    def stats(self) -> dict:
        """用户统计"""
        users = list(self._users.values())
        return {
            "total": len(users),
            "admin": sum(1 for u in users if u.role == Role.ADMIN),
            "doctor": sum(1 for u in users if u.role == Role.DOCTOR),
            "reviewer": sum(1 for u in users if u.role == Role.REVIEWER),
            "enabled": sum(1 for u in users if u.enabled),
            "disabled": sum(1 for u in users if not u.enabled),
        }


# 全局单例（懒加载）
_user_manager: Optional[UserManager] = None


def get_user_manager() -> UserManager:
    """获取全局 UserManager 单例"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager
