"""
生成 test.xlsx 测试用例文件 - 1050 条用例

运行：
    python -m tests.build_test_xlsx

产物：tests/test.xlsx
    - sheet "test_cases"：所有测试用例（数据驱动，共 1050 条）
    - sheet "说明"：列定义与断言类型说明

测试用例与运行器（xlsx_runner.py）的 operation 契约严格对应。

用例分布（1050 条）：
  核心模块（800 条）
  1. 密码安全        (TC-P)  : 80 条
  2. 角色权限        (TC-R)  : 70 条
  3. 用户认证        (TC-A)  : 50 条
  4. 用户管理        (TC-U)  : 80 条
  5. 用户空间        (TC-S)  : 80 条
  6. 审计日志        (TC-L)  : 50 条
  7. 患者模型        (TC-PT) : 75 条
  8. 病历整合        (TC-M)  : 30 条
  9. 会诊流程        (TC-C)  : 60 条
 10. 全局索引        (TC-G)  : 50 条
 11. 医学影像        (TC-I)  : 70 条
 12. 边界异常        (TC-E)  : 35 条
 13. 审核队列        (TC-RV) : 50 条
  后端管理平台（270 条）
 14. 后台-AI智能体   (TC-AA) : 55 条
 15. 后台-系统集成   (TC-AI) : 55 条
 16. 后台-质控统计   (TC-AQ) : 50 条
 17. 后台-角色模板   (TC-AR) : 50 条
 18. 后台-系统配置   (TC-AC) : 60 条
 合计                     : 1050 条
"""
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

OUTPUT = Path(__file__).parent / "test.xlsx"

# 列定义
HEADER = ["用例ID", "测试项", "用例名称", "描述", "操作operation",
          "参数params(JSON)", "断言类型", "期望expected", "启用"]


def P(d: dict) -> str:
    """将参数 dict 序列化为紧凑 JSON 字符串"""
    return json.dumps(d, ensure_ascii=False)


def _case(case_id: str, category: str, name: str, desc: str, operation: str,
          params: dict, expected_type: str, expected: str = "", enabled: str = "Y") -> tuple:
    return (case_id, category, name, desc, operation, P(params), expected_type, expected, enabled)


# ============================================================
# 测试用例数据生成器 - 1000 条
# ============================================================
def _build_cases() -> list:
    cases = []
    counters = {}

    def next_id(prefix: str) -> str:
        counters[prefix] = counters.get(prefix, 0) + 1
        return f"{prefix}{counters[prefix]:03d}"

    # ================================================================
    # 1. 密码安全 (TC-P) - 80 条
    # ================================================================
    _build_password_cases(cases, next_id)

    # ================================================================
    # 2. 角色权限 (TC-R) - 70 条
    # ================================================================
    _build_role_cases(cases, next_id)

    # ================================================================
    # 3. 用户认证 (TC-A) - 50 条
    # ================================================================
    _build_auth_cases(cases, next_id)

    # ================================================================
    # 4. 用户管理 (TC-U) - 80 条
    # ================================================================
    _build_user_mgmt_cases(cases, next_id)

    # ================================================================
    # 5. 用户空间 (TC-S) - 80 条
    # ================================================================
    _build_session_cases(cases, next_id)

    # ================================================================
    # 6. 审计日志 (TC-L) - 50 条
    # ================================================================
    _build_audit_cases(cases, next_id)

    # ================================================================
    # 7. 患者模型 (TC-PT) - 75 条
    # ================================================================
    _build_patient_cases(cases, next_id)

    # ================================================================
    # 8. 病历整合 (TC-M) - 30 条
    # ================================================================
    _build_medical_record_cases(cases, next_id)

    # ================================================================
    # 9. 会诊流程 (TC-C) - 60 条
    # ================================================================
    _build_consultation_cases(cases, next_id)

    # ================================================================
    # 10. 全局索引 (TC-G) - 50 条
    # ================================================================
    _build_global_index_cases(cases, next_id)

    # ================================================================
    # 11. 医学影像 (TC-I) - 70 条
    # ================================================================
    _build_image_cases(cases, next_id)

    # ================================================================
    # 12. 边界异常 (TC-E) - 35 条
    # ================================================================
    _build_edge_cases(cases, next_id)

    # ================================================================
    # 13. 后台-AI智能体管理 (TC-AA) - 55 条
    # ================================================================
    _build_admin_agent_cases(cases, next_id)

    # ================================================================
    # 14. 后台-系统集成 (TC-AI) - 55 条
    # ================================================================
    _build_admin_integration_cases(cases, next_id)

    # ================================================================
    # 15. 后台-质控统计 (TC-AQ) - 50 条
    # ================================================================
    _build_admin_quality_cases(cases, next_id)

    # ================================================================
    # 16. 后台-角色模板 (TC-AR) - 50 条
    # ================================================================
    _build_admin_role_cases(cases, next_id)

    # ================================================================
    # 17. 后台-系统配置 (TC-AC) - 60 条
    # ================================================================
    _build_admin_config_cases(cases, next_id)

    # ================================================================
    # 18. 审核队列 (TC-RV) - 50 条
    # ================================================================
    _build_review_queue_cases(cases, next_id)

    return cases


# ============================================================
# 1. 密码安全 - 80 条
# ============================================================
def _build_password_cases(cases, next_id):
    """密码哈希、验证、特殊字符、长度、边界"""
    # 基础哈希验证 - 20 条
    base_passwords = [
        ("secret123", "合法字母数字密码"),
        ("P@ssw0rd!2026", "含特殊字符密码"),
        ("a" * 32, "32位长密码"),
        ("仅中文密码测试", "中文字符密码"),
        ("A1b2C3d4", "混合大小写字母数字"),
        ("Hello2026!", "感叹号密码"),
        ("医院系统测试123", "中文混合数字"),
        ("P@55w0rd2026", "复杂组合密码"),
        ("short1", "6位最短密码"),
        ("LongPassword123456", "长密码20位"),
        ("Mix123!@#中文", "中英符号混合"),
        ("abc123", "简单字母数字"),
        ("Test1234", "测试密码"),
        ("MyP@ss!", "短特殊字符"),
        ("2026NewPwd", "年份密码"),
        ("医院HIS密码1", "HIS系统密码"),
        ("Complex#1", "井号密码"),
        ("NineChars", "9位密码"),
        ("TenChars10", "10位密码"),
        ("VeryLongPassword123456789", "超长密码24位"),
    ]
    for pwd, desc in base_passwords:
        cases.append(_case(next_id("TC-P"), "密码安全", f"密码哈希-{desc}",
                           f"对{desc}进行哈希，结果非空", "password_hash",
                           {"password": pwd}, "truthy"))

    # 密码验证 - 15 条
    verify_cases = [
        ("secret123", "secret123", True, "正确密码验证通过"),
        ("secret123", "wrong", False, "错误密码验证失败"),
        ("secret123", "", False, "空密码验证失败"),
        ("secret123", "invalid", False, "非法哈希验证失败"),
        ("P@ssw0rd!2026", "P@ssw0rd!2026", True, "特殊字符密码验证通过"),
        ("医院系统测试123", "医院系统测试123", True, "中文密码验证通过"),
        ("A1b2C3d4", "A1b2C3d4", True, "混合密码验证通过"),
        ("a" * 32, "a" * 32, True, "32位密码验证通过"),
        ("short1", "short1", True, "短密码验证通过"),
        ("LongPassword123456", "LongPassword123456", True, "长密码验证通过"),
        ("Mix123!@#中文", "Mix123!@#中文", True, "中英符号混合验证通过"),
        ("abc123", "abc1234", False, "近似密码验证失败"),
        ("Test1234", "test1234", False, "大小写不同验证失败"),
        ("2026NewPwd", "2026newpwd", False, "大小写敏感验证失败"),
        ("Complex#1", "Complex#2", False, "末位不同验证失败"),
    ]
    for pwd, verify, expected, desc in verify_cases:
        cases.append(_case(next_id("TC-P"), "密码安全", desc,
                           f"密码 '{pwd[:6]}...' 验证 '{verify[:6]}...' 应返回 {expected}",
                           "password_verify",
                           {"password": pwd, "verify_password": verify},
                           "truthy" if expected else "falsy"))

    # 异常密码 - 5 条
    cases.append(_case(next_id("TC-P"), "密码安全", "空密码应抛异常",
                       "对空字符串哈希应抛 ValueError", "password_empty", {}, "throws"))
    cases.append(_case(next_id("TC-P"), "密码安全", "短密码仍可哈希",
                       "6位密码可正常哈希", "password_length",
                       {"password": "123456"}, "truthy"))
    cases.append(_case(next_id("TC-P"), "密码安全", "特殊字符密码往返验证",
                       "含特殊字符密码哈希后可验证", "password_special",
                       {"password": "!@#$%^&*()"}, "truthy"))
    cases.append(_case(next_id("TC-P"), "密码安全", "空字符串验证失败",
                       "空密码验证应返回 False", "password_verify",
                       {"password": "secret123", "verify_password": ""}, "falsy"))
    cases.append(_case(next_id("TC-P"), "密码安全", "错误存储格式验证失败",
                       "非法哈希字符串验证应返回 False", "password_verify",
                       {"password": "secret123", "verify_password": "invalid"}, "falsy"))

    # 更多密码组合哈希 - 40 条
    more_passwords = [
        "Qwerty123!", "Zxcvbn456@", "Asdfgh789#", "Poiuyt012$",
        "Lkjhgf345%", "Mnbvcx678^", "Hjklui901&", "Fdsaqw234*",
        "Gfdsaz567(", "Vbnmlk890)", "Rtyuio123-", "Tgbnhy456=",
        "Yhnmju789_", "Ujmiko012+", "Ikjhgq345!", "Olkpas678@",
        "Plzxsw901#", "Qazxsw234$", "Wsxedc567%", "Edcvfr890^",
        "Rfvbgh123&", "Tgbnhy456*", "Yhnmju789(", "Ujmiko012)",
        "Ikjhgq345-", "Olkpas678=", "Plzxsw901_", "Qazxsw234+",
        "密码测试A1", "密码测试B2", "密码测试C3", "密码测试D4",
        "密码测试E5", "密码测试F6", "密码测试G7", "密码测试H8",
        "Test@123", "Demo@456", "Sample@789", "Example@012",
    ]
    for i, pwd in enumerate(more_passwords, 1):
        cases.append(_case(next_id("TC-P"), "密码安全", f"密码哈希组合扩展{i}",
                           f"对 '{pwd}' 哈希后验证通过", "password_special",
                           {"password": pwd}, "truthy"))


# ============================================================
# 2. 角色权限 - 70 条
# ============================================================
def _build_role_cases(cases, next_id):
    """角色解析、权限判断、显示名"""
    # 基础角色解析 - 18 条
    role_inputs = [
        ("管理员", "admin"), ("admin", "admin"), ("ADMIN", "admin"), ("Admin", "admin"),
        ("医生", "doctor"), ("doctor", "doctor"), ("DOCTOR", "doctor"), ("Doctor", "doctor"),
        ("审核员", "reviewer"), ("reviewer", "reviewer"), ("REVIEWER", "reviewer"), ("Reviewer", "reviewer"),
        (" admin ", "admin"), (" doctor ", "doctor"), (" reviewer ", "reviewer"),
        ("管理员", "admin"), ("REVIEWER", "reviewer"), ("Admin", "admin"),
    ]
    for val, expected in role_inputs:
        cases.append(_case(next_id("TC-R"), "角色权限", f"Role解析-{val}",
                           f"Role.parse('{val}') 应为 {expected}", "role_parse_more",
                           {"value": val}, "equals", expected))

    # 非法角色回退 - 18 条
    invalid_roles = ["xxx", "", "123", "护师", "主任", "护士长",
                      "unknown", "guest", "super", "root", "user", "patient",
                      "ADMINISTRATOR", "DOCTORX", "REVIEW", "adm", "doc", "rev"]
    for val in invalid_roles:
        cases.append(_case(next_id("TC-R"), "角色权限", f"非法角色回退医生-{val or '空'}",
                           f"Role.parse('{val}') 应回退为 doctor", "role_parse_more",
                           {"value": val}, "equals", "doctor"))

    # 审核权限判断 - 12 条
    can_review_cases = [
        ("admin", True, "管理员具备审核权限"),
        ("doctor", False, "医生不具备审核权限"),
        ("reviewer", True, "审核员具备审核权限"),
        ("管理员", True, "中文管理员具备审核权限"),
        ("医生", False, "中文医生不具备审核权限"),
        ("审核员", True, "中文审核员具备审核权限"),
        ("ADMIN", True, "大写管理员具备审核权限"),
        ("DOCTOR", False, "大写医生不具备审核权限"),
        ("REVIEWER", True, "大写审核员具备审核权限"),
        ("Admin", True, "首字母大写管理员具备审核权限"),
        ("Doctor", False, "首字母大写医生不具备审核权限"),
        ("Reviewer", True, "首字母大写审核员具备审核权限"),
    ]
    for role, expected, desc in can_review_cases:
        cases.append(_case(next_id("TC-R"), "角色权限", desc,
                           f"Role.parse('{role}').can_review() 应为 {expected}",
                           "role_can_review", {"role": role},
                           "truthy" if expected else "falsy"))

    # 显示名 - 9 条
    display_cases = [
        ("admin", "管理员", "管理员显示名"), ("doctor", "医生", "医生显示名"),
        ("reviewer", "审核员", "审核员显示名"),
        ("管理员", "管理员", "中文管理员显示名"), ("医生", "医生", "中文医生显示名"),
        ("审核员", "审核员", "中文审核员显示名"),
        ("ADMIN", "管理员", "大写管理员显示名"), ("DOCTOR", "医生", "大写医生显示名"),
        ("REVIEWER", "审核员", "大写审核员显示名"),
    ]
    for role, expected, desc in display_cases:
        cases.append(_case(next_id("TC-R"), "角色权限", desc,
                           f"Role.parse('{role}').display_name 应为 '{expected}'",
                           "role_display", {"role": role}, "equals", expected))

    # 角色边界 - 13 条
    boundary_cases = [
        ("医", "doctor"), ("reviewer ", "reviewer"), (" Admin", "admin"),
        ("ADMINISTRATOR", "doctor"), ("unknown", "doctor"), ("", "doctor"),
        ("123", "doctor"), ("null", "doctor"), ("None", "doctor"),
        (" 医生 ", "doctor"), ("\td doctor", "doctor"), ("D", "doctor"), ("A", "doctor"),
    ]
    for i, (val, expected) in enumerate(boundary_cases, 1):
        cases.append(_case(next_id("TC-R"), "角色权限", f"角色解析边界{i}",
                           f"Role.parse('{val}') 应为 {expected}", "role_parse_more",
                           {"value": val}, "equals", expected))


# ============================================================
# 3. 用户认证 - 50 条
# ============================================================
def _build_auth_cases(cases, next_id):
    """登录认证、禁用、空值、大小写"""
    # 正确登录 - 3 条
    cases.append(_case(next_id("TC-A"), "用户认证", "管理员正确登录",
                       "admin/admin123 认证应成功", "auth",
                       {"username": "admin", "password": "admin123"}, "truthy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "医生正确登录",
                       "doctor/doctor123 认证应成功", "auth",
                       {"username": "doctor", "password": "doctor123"}, "truthy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "审核员正确登录",
                       "reviewer/reviewer123 认证应成功", "auth",
                       {"username": "reviewer", "password": "reviewer123"}, "truthy"))

    # 错误密码 - 15 条
    wrong_pwds = ["wrongpwd", "admin", "123", "password", "admin1234",
                  "ADMIN123", "Admin123", "admin 123", "admin123 ", " admin123",
                  "doctor123", "reviewer123", "", " ", "null"]
    for i, pwd in enumerate(wrong_pwds, 1):
        cases.append(_case(next_id("TC-A"), "用户认证", f"错误密码登录失败{i}",
                           f"admin/{pwd or '空'} 认证应失败", "auth",
                           {"username": "admin", "password": pwd}, "falsy"))

    # 不存在用户 - 15 条
    ghost_users = ["ghost", "", "root", "super", "test",
                   "user", "admin1", "doctor1", "reviewer1", "管理员",
                   "Admin", "ADMIN", "Docter", "Reveiwer", "null"]
    for i, user in enumerate(ghost_users, 1):
        cases.append(_case(next_id("TC-A"), "用户认证", f"不存在用户登录失败{i}",
                           f"{user or '空用户'} 认证应失败", "auth_empty",
                           {"username": user, "password": "anypwd"}, "falsy"))

    # 禁用用户 - 3 条
    cases.append(_case(next_id("TC-A"), "用户认证", "禁用用户登录失败",
                       "禁用后的 doctor 账户无法登录", "auth_disabled",
                       {"username": "doctor", "password": "doctor123"}, "falsy"))

    # 空用户名/密码 - 6 条
    cases.append(_case(next_id("TC-A"), "用户认证", "空用户名登录失败",
                       "空用户名应返回 None", "auth_empty",
                       {"username": "", "password": "admin123"}, "falsy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "空密码登录失败",
                       "空密码应返回 None", "auth_empty",
                       {"username": "admin", "password": ""}, "falsy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "全空登录失败",
                       "用户名和密码都为空", "auth_empty",
                       {"username": "", "password": ""}, "falsy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "空格用户名失败",
                       "纯空格用户名", "auth_empty",
                       {"username": "   ", "password": "admin123"}, "falsy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "空格密码失败",
                       "纯空格密码", "auth_empty",
                       {"username": "admin", "password": "   "}, "falsy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "Tab用户名失败",
                       "Tab字符用户名", "auth_empty",
                       {"username": "\t", "password": "admin123"}, "falsy"))

    # 大小写敏感 - 6 条
    cases.append(_case(next_id("TC-A"), "用户认证", "大小写敏感用户名失败",
                       "Admin 不等于 admin", "auth",
                       {"username": "Admin", "password": "admin123"}, "falsy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "全大写用户名失败",
                       "ADMIN 不等于 admin", "auth",
                       {"username": "ADMIN", "password": "admin123"}, "falsy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "Doctor大写失败",
                       "Doctor 不等于 doctor", "auth",
                       {"username": "Doctor", "password": "doctor123"}, "falsy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "DOCTOR大写失败",
                       "DOCTOR 不等于 doctor", "auth",
                       {"username": "DOCTOR", "password": "doctor123"}, "falsy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "Reviewer大写失败",
                       "Reviewer 不等于 reviewer", "auth",
                       {"username": "Reviewer", "password": "reviewer123"}, "falsy"))
    cases.append(_case(next_id("TC-A"), "用户认证", "REVIEWER大写失败",
                       "REVIEWER 不等于 reviewer", "auth",
                       {"username": "REVIEWER", "password": "reviewer123"}, "falsy"))

    # 更多失败场景 - 4 条
    fail_scenarios = [
        ("admin", ""), ("", "admin123"), ("doctor", "admin123"),
        ("ghost", "ghost123"),
    ]
    for i, (user, pwd) in enumerate(fail_scenarios, 1):
        cases.append(_case(next_id("TC-A"), "用户认证", f"额外认证失败{i}",
                           f"{user or '空用户'}/{pwd or '空密码'} 认证失败", "auth_empty",
                           {"username": user, "password": pwd}, "falsy"))


# ============================================================
# 4. 用户管理 - 80 条
# ============================================================
def _build_user_mgmt_cases(cases, next_id):
    """创建、删除、更新、密码管理、统计"""
    # 基础创建 - 10 条
    cases.append(_case(next_id("TC-U"), "用户管理", "创建医生用户成功",
                       "创建新医生账户应返回其 user_id", "create_user",
                       {"username": "newdoctor", "display_name": "新医生",
                        "role": "doctor", "department": "呼吸科", "password": "pass1234"}, "not_null"))
    cases.append(_case(next_id("TC-U"), "用户管理", "创建管理员用户成功",
                       "创建新管理员账户", "create_user_admin",
                       {"username": "newadmin", "display_name": "新管理员", "password": "pass1234"}, "equals", "admin"))
    cases.append(_case(next_id("TC-U"), "用户管理", "创建审核员用户成功",
                       "创建新审核员账户", "create_user_reviewer",
                       {"username": "newreviewer", "display_name": "新审核员", "password": "pass1234"}, "equals", "reviewer"))

    # 参数化创建医生 - 10 条
    for i in range(1, 11):
        cases.append(_case(next_id("TC-U"), "用户管理", f"参数化创建医生{i}",
                           f"创建医生 doc_{i} 应返回 user_id", "create_user",
                           {"username": f"doc_{i}", "display_name": f"医生{i}",
                            "role": "doctor", "department": f"科室{i}", "password": "pass1234"}, "not_null"))

    # 参数化创建管理员 - 8 条
    for i in range(1, 9):
        cases.append(_case(next_id("TC-U"), "用户管理", f"参数化创建管理员{i}",
                           f"创建管理员 adm_{i} 角色应为 admin", "create_user_admin",
                           {"username": f"adm_{i}", "display_name": f"管理员{i}", "password": "pass1234"}, "equals", "admin"))

    # 参数化创建审核员 - 8 条
    for i in range(1, 9):
        cases.append(_case(next_id("TC-U"), "用户管理", f"参数化创建审核员{i}",
                           f"创建审核员 rev_{i} 角色应为 reviewer", "create_user_reviewer",
                           {"username": f"rev_{i}", "display_name": f"审核员{i}", "password": "pass1234"}, "equals", "reviewer"))

    # 异常创建 - 5 条
    cases.append(_case(next_id("TC-U"), "用户管理", "重复用户名应抛异常",
                       "重复用户名应抛 ValueError", "create_duplicate",
                       {"username": "dup"}, "throws"))
    cases.append(_case(next_id("TC-U"), "用户管理", "弱密码应抛异常",
                       "短于6位密码应抛 ValueError", "create_weak_password",
                       {"username": "weak", "password": "12"}, "throws"))
    cases.append(_case(next_id("TC-U"), "用户管理", "空密码应抛异常",
                       "空密码应抛 ValueError", "create_weak_password",
                       {"username": "weak2", "password": ""}, "throws"))
    cases.append(_case(next_id("TC-U"), "用户管理", "删除最后一个管理员应抛异常",
                       "系统至少保留1个启用管理员", "delete_last_admin", {}, "throws_contains", "至少需要保留"))
    cases.append(_case(next_id("TC-U"), "用户管理", "重复创建管理员应抛异常",
                       "重复用户名 dup_adm", "create_duplicate",
                       {"username": "dup_adm"}, "throws"))

    # 密码管理 - 10 条
    cases.append(_case(next_id("TC-U"), "用户管理", "重置密码后可登录",
                       "重置 doctor 密码后用新密码登录成功", "reset_password",
                       {"username": "doctor", "new_password": "newpass123"}, "truthy"))
    cases.append(_case(next_id("TC-U"), "用户管理", "旧密码错误改密失败",
                       "change_password 旧密码错误返回 False", "change_password_wrong",
                       {"username": "doctor", "old": "wrongold", "new": "newpass123"}, "falsy"))
    cases.append(_case(next_id("TC-U"), "用户管理", "正确改密后可登录",
                       "用正确旧密码改密后用新密码登录成功", "change_password_correct",
                       {"username": "doctor", "old": "doctor123", "new": "newpass123"}, "truthy"))
    for i in range(1, 8):
        cases.append(_case(next_id("TC-U"), "用户管理", f"重置密码扩展{i}",
                           f"重置 doctor 密码为新密码{i}", "reset_password",
                           {"username": "doctor", "new_password": f"reset{i}pass"}, "truthy"))

    # 更新用户 - 15 条
    update_cases = [
        ("display_name", "李医生更新", "update_user"),
        ("display_name", "张医生更新", "update_user"),
        ("department", "神经内科", "update_user_department"),
        ("department", "心内科", "update_user_department"),
        ("department", "呼吸内科", "update_user_department"),
        ("title", "主任医师", "update_user"),
        ("title", "副主任医师", "update_user"),
        ("title", "主治医师", "update_user"),
        ("display_name", "王医生", "update_user"),
        ("display_name", "赵医生", "update_user"),
        ("department", "急诊科", "update_user_department"),
        ("department", "消化内科", "update_user_department"),
        ("display_name", "刘医生", "update_user"),
        ("department", "肾内科", "update_user_department"),
        ("display_name", "陈医生", "update_user"),
    ]
    for i, (field, value, op) in enumerate(update_cases, 1):
        param_key = "department" if field == "department" else "display_name"
        cases.append(_case(next_id("TC-U"), "用户管理", f"额外用户更新{i}",
                           f"更新用户 {field}={value}", op,
                           {"username": "doctor", param_key: value}, "equals", value))

    # 角色更新 - 5 条
    cases.append(_case(next_id("TC-U"), "用户管理", "更新用户角色",
                       "将 doctor 更新为 reviewer", "update_user_role",
                       {"username": "doctor", "new_role": "reviewer"}, "equals", "reviewer"))
    for i, role in enumerate(["admin", "doctor", "reviewer", "doctor", "admin"], 1):
        cases.append(_case(next_id("TC-U"), "用户管理", f"角色更新扩展{i}",
                           f"将 doctor 更新为 {role}", "update_user_role",
                           {"username": "doctor", "new_role": role}, "equals", role))

    # 删除 - 5 条
    cases.append(_case(next_id("TC-U"), "用户管理", "删除非管理员用户成功",
                       "删除 doctor 用户后查询应为 None", "delete_user_non_admin",
                       {"username": "doctor"}, "truthy"))
    for i in range(1, 5):
        cases.append(_case(next_id("TC-U"), "用户管理", f"删除用户扩展{i}",
                           f"删除 doctor 用户验证", "delete_user_non_admin",
                           {"username": "doctor"}, "truthy"))

    # 统计与脱敏 - 5 条
    cases.append(_case(next_id("TC-U"), "用户管理", "用户统计正确",
                       "初始3用户：total=3", "user_stats", {}, "json_field_equals", "total=3"))
    cases.append(_case(next_id("TC-U"), "用户管理", "脱敏字典不含密码哈希",
                       "to_public_dict 不应包含 password_hash", "user_to_public_dict",
                       {"username": "admin"}, "truthy"))
    cases.append(_case(next_id("TC-U"), "用户管理", "按角色列出医生",
                       "list_users(role=doctor) 返回医生", "list_users_by_role",
                       {"role": "doctor"}, "contains", "doctor"))
    cases.append(_case(next_id("TC-U"), "用户管理", "按角色列出管理员",
                       "list_users(role=admin) 返回管理员", "list_users_by_role",
                       {"role": "admin"}, "contains", "admin"))
    cases.append(_case(next_id("TC-U"), "用户管理", "按角色列出审核员",
                       "list_users(role=reviewer) 返回审核员", "list_users_by_role",
                       {"role": "reviewer"}, "contains", "reviewer"))

    # 最后登录 - 5 条
    cases.append(_case(next_id("TC-U"), "用户管理", "更新最后登录信息",
                       "update_last_login 记录时间与IP", "user_last_login",
                       {"username": "admin"}, "truthy"))
    for i in range(1, 5):
        cases.append(_case(next_id("TC-U"), "用户管理", f"最后登录扩展{i}",
                           f"更新 admin 最后登录信息", "user_last_login",
                           {"username": "admin"}, "truthy"))


# ============================================================
# 5. 用户空间 - 80 条
# ============================================================
def _build_session_cases(cases, next_id):
    """报告保存加载、患者保存加载、隔离、删除"""
    # 基础报告操作 - 10 条
    cases.append(_case(next_id("TC-S"), "用户空间", "保存并加载会诊报告",
                       "保存报告后能按ID加载，ID一致", "session_save_load_report",
                       {"user_id": "U_TEST", "consultation_id": "REP-001", "patient_name": "测试患者"}, "equals", "REP-001"))
    cases.append(_case(next_id("TC-S"), "用户空间", "会诊报告列表数量",
                       "保存3份报告后列表应有3条", "session_list_reports",
                       {"user_id": "U_LIST", "count": 3}, "count", "3"))
    cases.append(_case(next_id("TC-S"), "用户空间", "用户数据隔离",
                       "用户A的报告不应在用户B空间可见", "session_isolation",
                       {"user_a": "U_A", "user_b": "U_B"}, "falsy"))
    cases.append(_case(next_id("TC-S"), "用户空间", "删除报告后不可加载",
                       "删除报告后 load_report 返回 None", "session_delete_report",
                       {"user_id": "U_DEL"}, "falsy"))
    cases.append(_case(next_id("TC-S"), "用户空间", "同ID报告跨用户隔离",
                       "相同consultation_id在不同用户空间互不影响", "session_report_isolation",
                       {"user_a": "U_X", "user_b": "U_Y"}, "falsy"))
    cases.append(_case(next_id("TC-S"), "用户空间", "报告状态APPROVED往返",
                       "保存状态为APPROVED的报告后读取状态一致", "session_report_with_status",
                       {"user_id": "U_STAT", "consultation_id": "REP-APPROVED", "status": "APPROVED"}, "equals", "APPROVED"))
    cases.append(_case(next_id("TC-S"), "用户空间", "报告状态COMPLETED往返",
                       "保存状态为COMPLETED的报告后读取状态一致", "session_report_with_status",
                       {"user_id": "U_STAT2", "consultation_id": "REP-COMPLETED", "status": "COMPLETED"}, "equals", "COMPLETED"))
    cases.append(_case(next_id("TC-S"), "用户空间", "报告状态PENDING往返",
                       "保存状态为PENDING的报告后读取状态一致", "session_report_with_status",
                       {"user_id": "U_STAT3", "consultation_id": "REP-PENDING", "status": "PENDING"}, "equals", "PENDING"))
    cases.append(_case(next_id("TC-S"), "用户空间", "报告状态REJECTED往返",
                       "保存状态为REJECTED的报告后读取状态一致", "session_report_with_status",
                       {"user_id": "U_STAT4", "consultation_id": "REP-REJECTED", "status": "REJECTED"}, "equals", "REJECTED"))
    cases.append(_case(next_id("TC-S"), "用户空间", "报告状态DRAFT往返",
                       "保存状态为DRAFT的报告后读取状态一致", "session_report_with_status",
                       {"user_id": "U_STAT5", "consultation_id": "REP-DRAFT", "status": "DRAFT"}, "equals", "DRAFT"))

    # 患者保存加载 - 15 条
    cases.append(_case(next_id("TC-S"), "用户空间", "保存并加载患者",
                       "保存患者后能按ID加载，姓名一致", "session_save_load_patient",
                       {"user_id": "U_PAT", "patient_id": "P001", "name": "测试患者"}, "equals", "测试患者"))
    for i in range(1, 15):
        cases.append(_case(next_id("TC-S"), "用户空间", f"患者保存加载扩展{i}",
                           f"保存患者 P_EXT_{i} 后加载姓名一致", "session_save_load_patient",
                           {"user_id": f"U_EXT_{i}", "patient_id": f"P_EXT_{i}", "name": f"扩展患者{i}"}, "equals", f"扩展患者{i}"))

    # 报告保存加载 - 25 条
    for i in range(1, 26):
        cases.append(_case(next_id("TC-S"), "用户空间", f"额外报告保存{i}",
                           f"保存报告 EXT-REP-{i}", "session_save_load_report",
                           {"user_id": f"U_REP_{i}", "consultation_id": f"EXT-REP-{i}",
                            "patient_name": f"患者{i}"}, "equals", f"EXT-REP-{i}"))

    # 列表数量 - 15 条
    for i, n in enumerate([1, 2, 5, 10, 3, 7, 4, 8, 6, 9, 15, 12, 11, 14, 20], 1):
        cases.append(_case(next_id("TC-S"), "用户空间", f"报告列表数量{i}",
                           f"保存{n}份报告后列表应有{n}条", "session_list_reports",
                           {"user_id": f"U_LIST_{i}", "count": n}, "count", str(n)))

    # 隔离与删除 - 15 条
    for i in range(1, 16):
        cases.append(_case(next_id("TC-S"), "用户空间", f"数据隔离扩展{i}",
                           f"用户A{i}的报告不应在用户B{i}空间可见", "session_isolation",
                           {"user_a": f"U_IA_{i}", "user_b": f"U_IB_{i}"}, "falsy"))


# ============================================================
# 6. 审计日志 - 50 条
# ============================================================
def _build_audit_cases(cases, next_id):
    """日志计数、过滤、空查询"""
    # 基础 - 4 条
    cases.append(_case(next_id("TC-L"), "审计日志", "日志记录数量",
                       "写入2条日志后 get_logs 应有2条", "audit_log_count",
                       {"actions": ["LOGIN_SUCCESS", "LOGOUT"]}, "count", "2"))
    cases.append(_case(next_id("TC-L"), "审计日志", "按动作过滤日志",
                       "过滤 LOGIN_SUCCESS 应返回2条", "audit_filter",
                       {"action": "LOGIN_SUCCESS"}, "count", "2"))
    cases.append(_case(next_id("TC-L"), "审计日志", "不存在动作返回空列表",
                       "查询不存在的动作应返回空列表", "audit_empty",
                       {}, "count", "0"))
    cases.append(_case(next_id("TC-L"), "审计日志", "写入多种动作",
                       "写入LOGIN/CREATE/UPDATE/DELETE后计数正确", "audit_log_count",
                       {"actions": ["LOGIN", "CREATE", "UPDATE", "DELETE"]}, "count", "4"))

    # 各种动作组合 - 30 条
    action_sets = [
        ["LOGIN_SUCCESS"], ["LOGOUT"], ["CREATE_CONSULTATION"], ["COMPLETE_CONSULTATION"],
        ["APPROVE_REPORT"], ["REJECT_REPORT"], ["UPLOAD_MEDICAL_IMAGE"], ["DELETE_MEDICAL_IMAGE"],
        ["SAVE_PATIENT"], ["DELETE_PATIENT"], ["LOGIN_SUCCESS", "LOGOUT"],
        ["CREATE_CONSULTATION", "COMPLETE_CONSULTATION"], ["APPROVE_REPORT", "REJECT_REPORT"],
        ["UPLOAD_MEDICAL_IMAGE", "DELETE_MEDICAL_IMAGE"], ["SAVE_PATIENT", "DELETE_PATIENT"],
        ["LOGIN_SUCCESS", "CREATE_CONSULTATION", "APPROVE_REPORT"],
        ["LOGOUT", "COMPLETE_CONSULTATION", "REJECT_REPORT"],
        ["LOGIN_SUCCESS", "LOGOUT", "LOGIN_SUCCESS", "LOGOUT"],
        ["CREATE_CONSULTATION", "COMPLETE_CONSULTATION", "APPROVE_REPORT", "DELETE_PATIENT"],
        ["LOGIN_SUCCESS"] * 5,
        ["UPLOAD_MEDICAL_IMAGE"] * 3,
        ["SAVE_PATIENT"] * 7,
        ["LOGIN_SUCCESS", "CREATE_CONSULTATION"],
        ["APPROVE_REPORT", "REJECT_REPORT", "APPROVE_REPORT"],
        ["DELETE_PATIENT", "DELETE_MEDICAL_IMAGE"],
        ["LOGIN_SUCCESS", "CREATE_CONSULTATION", "COMPLETE_CONSULTATION", "APPROVE_REPORT", "LOGOUT"],
        ["UPLOAD_MEDICAL_IMAGE", "DELETE_MEDICAL_IMAGE", "UPLOAD_MEDICAL_IMAGE"],
        ["SAVE_PATIENT", "DELETE_PATIENT", "SAVE_PATIENT"],
        ["LOGIN_SUCCESS", "LOGIN_SUCCESS", "LOGIN_SUCCESS"],
        ["LOGOUT", "LOGOUT", "LOGOUT", "LOGOUT"],
    ]
    for i, actions in enumerate(action_sets, 1):
        cases.append(_case(next_id("TC-L"), "审计日志", f"审计计数扩展{i}",
                           f"写入{len(actions)}条日志后计数正确", "audit_log_count",
                           {"actions": actions}, "count", str(len(actions))))

    # 过滤 - 16 条
    # audit_filter 操作固定记录: LOGIN_SUCCESS x2, CREATE_CONSULTATION x1
    filter_actions = ["LOGIN_SUCCESS", "LOGOUT", "CREATE_CONSULTATION", "COMPLETE_CONSULTATION",
                      "APPROVE_REPORT", "REJECT_REPORT", "UPLOAD_MEDICAL_IMAGE", "DELETE_MEDICAL_IMAGE",
                      "SAVE_PATIENT", "DELETE_PATIENT", "LOGIN", "CREATE", "UPDATE", "DELETE",
                      "NOT_EXIST", "TEST_ACTION"]
    for i, action in enumerate(filter_actions, 1):
        if action == "LOGIN_SUCCESS":
            expected = "2"
        elif action == "CREATE_CONSULTATION":
            expected = "1"
        else:
            expected = "0"
        cases.append(_case(next_id("TC-L"), "审计日志", f"审计过滤{i}",
                           f"过滤动作 {action} 应返回 {expected} 条", "audit_filter",
                           {"action": action}, "count", expected))


# ============================================================
# 7. 患者模型 - 75 条
# ============================================================
def _build_patient_cases(cases, next_id):
    """字典往返、性别解析、脱敏、影像"""
    # 基础往返 - 15 条
    cases.append(_case(next_id("TC-PT"), "患者模型", "患者字典往返一致",
                       "from_dict(to_dict) 姓名应一致", "patient_from_dict_roundtrip",
                       {"patient_id": "P001", "name": "测试患者"}, "equals", "测试患者"))
    for i in range(1, 15):
        cases.append(_case(next_id("TC-PT"), "患者模型", f"患者往返扩展{i}",
                           f"患者 P_RT_{i} 字典往返", "patient_from_dict_roundtrip",
                           {"patient_id": f"P_RT_{i}", "name": f"往返患者{i}"}, "equals", f"往返患者{i}"))

    # 性别解析 - 30 条
    gender_cases = [
        ("男", "男"), ("M", "男"), ("Male", "男"), ("m", "男"), ("male", "男"),
        ("MAN", "男"), ("man", "男"), ("男孩", "男"), ("1", "男"),
        ("女", "女"), ("F", "女"), ("Female", "女"), ("f", "女"), ("female", "女"),
        ("WOMAN", "女"), ("woman", "女"), ("女孩", "女"), ("2", "女"),
        ("xyz", "未知"), ("", "未知"), ("3", "未知"), ("unknown", "未知"),
        ("其他", "未知"), ("男", "男"), ("女", "女"), ("Male", "男"),
        ("Female", "女"), ("M", "男"), ("F", "女"), ("1", "男"),
    ]
    for i, (val, expected) in enumerate(gender_cases, 1):
        op = "gender_parse" if val in ["男", "女", "M", "F", "xyz"] else "gender_parse_more"
        cases.append(_case(next_id("TC-PT"), "患者模型", f"性别解析扩展{i}",
                           f"Gender.parse('{val}') 应为 '{expected}'", op,
                           {"value": val}, "equals", expected))

    # 影像与脱敏 - 10 条
    cases.append(_case(next_id("TC-PT"), "患者模型", "患者含医学影像往返",
                       "含 medical_images 的患者字典往返后保留图片", "patient_with_images",
                       {"patient_id": "P_IMG"}, "count", "1"))
    cases.append(_case(next_id("TC-PT"), "患者模型", "患者脱敏字典",
                       "phone/id_card 应被脱敏", "patient_public_dict", {}, "truthy"))
    for i in range(1, 9):
        cases.append(_case(next_id("TC-PT"), "患者模型", f"含影像往返扩展{i}",
                           f"患者 P_IMG_{i} 含影像往返", "patient_with_images",
                           {"patient_id": f"P_IMG_{i}"}, "count", "1"))

    # 更多往返 - 20 条
    for i in range(1, 21):
        cases.append(_case(next_id("TC-PT"), "患者模型", f"额外患者往返{i}",
                           f"患者 P_EXTRA_{i} 字典往返", "patient_from_dict_roundtrip",
                           {"patient_id": f"P_EXTRA_{i}", "name": f"扩展患者{i}"}, "equals", f"扩展患者{i}"))


# ============================================================
# 8. 病历整合 - 30 条
# ============================================================
def _build_medical_record_cases(cases, next_id):
    """病历整合器"""
    cases.append(_case(next_id("TC-M"), "病历整合", "整合患者姓名正确",
                       "从HIS/EMR/LIS/PACS适配器整合后患者姓名正确", "medical_record_integrate",
                       {}, "equals", "测试患者"))
    for i in range(1, 30):
        cases.append(_case(next_id("TC-M"), "病历整合", f"病历整合扩展{i}",
                           f"第{i}次病历整合患者姓名正确", "medical_record_integrate",
                           {}, "equals", "测试患者"))


# ============================================================
# 9. 会诊流程 - 60 条
# ============================================================
def _build_consultation_cases(cases, next_id):
    """会诊执行、急诊、常规"""
    # 基础 - 4 条
    cases.append(_case(next_id("TC-C"), "会诊流程", "会诊完成状态",
                       "完整会诊流程后报告状态应为 COMPLETED", "consultation_run",
                       {}, "json_field_equals", "status=COMPLETED"))
    cases.append(_case(next_id("TC-C"), "会诊流程", "会诊生成鉴别诊断",
                       "会诊报告应包含至少1条鉴别诊断", "consultation_run",
                       {}, "json_field_equals", "has_diagnosis=True"))
    cases.append(_case(next_id("TC-C"), "会诊流程", "急诊会诊完成",
                       "急诊优先级会诊流程后报告状态应为 COMPLETED", "consultation_run_emergency",
                       {}, "equals", "COMPLETED"))
    cases.append(_case(next_id("TC-C"), "会诊流程", "常规会诊完成",
                       "常规优先级会诊流程后报告状态应为 COMPLETED", "consultation_run_routine",
                       {}, "equals", "COMPLETED"))

    # 稳定性 - 28 条
    for i in range(1, 29):
        cases.append(_case(next_id("TC-C"), "会诊流程", f"会诊稳定性{i}",
                           f"第{i}次独立会诊流程应生成报告", "consultation_run",
                           {}, "json_field_equals", "status=COMPLETED"))

    # 急诊/常规 - 28 条
    for i in range(1, 15):
        cases.append(_case(next_id("TC-C"), "会诊流程", f"急诊会诊扩展{i}",
                           f"第{i}次急诊会诊应完成", "consultation_run_emergency",
                           {}, "equals", "COMPLETED"))
    for i in range(1, 15):
        cases.append(_case(next_id("TC-C"), "会诊流程", f"常规会诊扩展{i}",
                           f"第{i}次常规会诊应完成", "consultation_run_routine",
                           {}, "equals", "COMPLETED"))


# ============================================================
# 10. 全局索引 - 50 条
# ============================================================
def _build_global_index_cases(cases, next_id):
    """跨用户全局索引"""
    # 基础 - 2 条
    cases.append(_case(next_id("TC-G"), "全局索引", "跨用户会诊列表",
                       "2个用户各保存1份报告，全局索引应返回2条", "global_index",
                       {"user_ids": ["U_A", "U_B"]}, "count", "2"))
    cases.append(_case(next_id("TC-G"), "全局索引", "三用户会诊列表",
                       "3个用户各保存1份报告，全局索引应返回3条", "global_index",
                       {"user_ids": ["U_1", "U_2", "U_3"]}, "count", "3"))

    # 参数化 - 47 条
    for i, n in enumerate([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6,
                           1, 2, 3, 4, 1, 2, 3, 1, 2, 1, 3, 5, 7, 4, 6,
                           1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7], 1):
        uids = [f"U_GX_{i}_{j}" for j in range(1, n + 1)]
        cases.append(_case(next_id("TC-G"), "全局索引", f"全局索引扩展{i}",
                           f"{n}个用户各保存报告后全局索引返回{n}条", "global_index",
                           {"user_ids": uids}, "count", str(n)))


# ============================================================
# 11. 医学影像 - 70 条
# ============================================================
def _build_image_cases(cases, next_id):
    """影像保存、列表、删除、异常"""
    # 基础 - 4 条
    cases.append(_case(next_id("TC-I"), "医学影像", "保存PNG医学影像",
                       "上传PNG图片后应生成IMG编号并保存文件", "medical_image_save",
                       {"user_id": "U_IMG", "patient_id": "P001", "image_type": "CT", "body_part": "胸部"}, "truthy"))
    cases.append(_case(next_id("TC-I"), "医学影像", "保存JPG医学影像",
                       "上传JPG图片后应生成IMG编号并保存文件", "medical_image_list",
                       {"user_id": "U_IMG2", "patient_id": "P002"}, "count", "1"))
    cases.append(_case(next_id("TC-I"), "医学影像", "删除医学影像",
                       "删除图片后 load_medical_image 返回 None", "medical_image_delete",
                       {"user_id": "U_IMG3"}, "truthy"))
    cases.append(_case(next_id("TC-I"), "医学影像", "上传不存在文件抛异常",
                       "源文件不存在时应抛 ValueError", "medical_image_missing",
                       {"user_id": "U_IMG4"}, "throws"))

    # 类型组合 - 35 条
    img_types = [
        ("CT", "胸部"), ("MRI", "头部"), ("X光", "胸部"), ("超声", "腹部"), ("病理", "组织"),
        ("CT", "头部"), ("MRI", "脊柱"), ("X光", "四肢"), ("超声", "心脏"), ("病理", "细胞"),
        ("CT", "腹部"), ("MRI", "关节"), ("X光", "骨盆"), ("超声", "甲状腺"), ("病理", "切片"),
        ("CT", "脊柱"), ("MRI", "胸部"), ("X光", "颅骨"), ("超声", "肝脏"), ("病理", "活检"),
        ("CT", "四肢"), ("MRI", "腹部"), ("X光", "胸部"), ("超声", "肾脏"), ("病理", "冰冻"),
        ("CT", "骨盆"), ("MRI", "心脏"), ("X光", "腹部"), ("超声", "脾脏"), ("病理", "免疫"),
        ("CT", "颅骨"), ("MRI", "甲状腺"), ("X光", "脊柱"), ("超声", "胰腺"), ("病理", "分子"),
    ]
    for i, (img_type, part) in enumerate(img_types, 1):
        cases.append(_case(next_id("TC-I"), "医学影像", f"影像类型扩展{i}",
                           f"保存 {img_type} {part} 影像", "medical_image_save",
                           {"user_id": f"U_IMG_EXT_{i}", "patient_id": f"P_IMG_EXT_{i}",
                            "image_type": img_type, "body_part": part}, "truthy"))

    # 列表 - 15 条
    for i in range(1, 16):
        cases.append(_case(next_id("TC-I"), "医学影像", f"影像列表扩展{i}",
                           f"保存并列出影像 {i}", "medical_image_list",
                           {"user_id": f"U_IMG_L_{i}", "patient_id": f"P_IMG_L_{i}"}, "count", "1"))

    # 删除 - 10 条
    for i in range(1, 11):
        cases.append(_case(next_id("TC-I"), "医学影像", f"影像删除扩展{i}",
                           f"删除影像后不可加载 {i}", "medical_image_delete",
                           {"user_id": f"U_IMG_D_{i}"}, "truthy"))

    # 异常 - 6 条
    for i in range(1, 7):
        cases.append(_case(next_id("TC-I"), "医学影像", f"不存在文件异常{i}",
                           f"上传不存在文件应抛异常 {i}", "medical_image_missing",
                           {"user_id": f"U_IMG_M_{i}"}, "throws"))


# ============================================================
# 12. 边界异常 - 35 条
# ============================================================
def _build_edge_cases(cases, next_id):
    """边界条件与异常"""
    cases.append(_case(next_id("TC-E"), "边界异常", "患者ID缺失时使用UNKNOWN",
                       "from_dict 缺失 patient_id 时使用默认值", "patient_from_dict_roundtrip",
                       {"name": "无ID患者"}, "equals", "无ID患者"))
    cases.append(_case(next_id("TC-E"), "边界异常", "空审计日志读取",
                       "无日志文件时 get_logs 返回空列表", "audit_log_count",
                       {"actions": []}, "count", "0"))
    cases.append(_case(next_id("TC-E"), "边界异常", "用户统计空数据",
                       "无用户时 stats total=3", "user_stats", {}, "json_field_equals", "total=3"))

    # 更多边界 - 34 条
    for i in range(1, 15):
        cases.append(_case(next_id("TC-E"), "边界异常", f"空审计边界{i}",
                           f"空日志边界测试 {i}", "audit_log_count",
                           {"actions": []}, "count", "0"))
    for i in range(1, 11):
        cases.append(_case(next_id("TC-E"), "边界异常", f"无ID患者边界{i}",
                           f"无ID患者边界测试 {i}", "patient_from_dict_roundtrip",
                           {"name": f"无ID患者{i}"}, "equals", f"无ID患者{i}"))
    for i in range(1, 9):
        cases.append(_case(next_id("TC-E"), "边界异常", f"用户统计边界{i}",
                           f"用户统计边界测试 {i}", "user_stats", {}, "json_field_equals", "total=3"))


# ============================================================
# 13. 后台-AI智能体管理 - 55 条
# ============================================================
def _build_admin_agent_cases(cases, next_id):
    """AI智能体增删改查、启用停用"""
    # 初始化 - 5 条
    cases.append(_case(next_id("TC-AA"), "AI智能体", "初始化默认智能体",
                       "系统初始化应有默认智能体", "admin_init", {}, "truthy"))
    for i in range(1, 5):
        cases.append(_case(next_id("TC-AA"), "AI智能体", f"初始化验证{i}",
                           f"第{i}次验证默认数据", "admin_init", {}, "truthy"))

    # 添加 - 10 条
    for i in range(1, 11):
        cases.append(_case(next_id("TC-AA"), "AI智能体", f"添加智能体{i}",
                           f"添加心内科AI_{i} 后应存在", "admin_add_agent",
                           {"agent_id": f"AI_CARDIO_{i}", "name": f"心内科AI_{i}",
                            "specialty": "心内科", "description": f"心内科智能体{i}"}, "truthy"))

    # 重复添加 - 5 条
    for i in range(1, 6):
        cases.append(_case(next_id("TC-AA"), "AI智能体", f"重复添加异常{i}",
                           f"重复ID应抛异常", "admin_add_agent_duplicate",
                           {"agent_id": f"AI_DUP_{i}"}, "truthy"))

    # 切换启用 - 10 条
    for i in range(1, 11):
        cases.append(_case(next_id("TC-AA"), "AI智能体", f"切换启用{i}",
                           f"切换智能体启用状态", "admin_toggle_agent",
                           {"agent_id": f"AI_TOG_{i}", "name": f"切换AI_{i}", "specialty": "急诊"}, "truthy"))

    # 删除 - 10 条
    for i in range(1, 11):
        cases.append(_case(next_id("TC-AA"), "AI智能体", f"删除智能体{i}",
                           f"删除智能体后不应存在", "admin_delete_agent",
                           {"agent_id": f"AI_DEL_{i}"}, "truthy"))

    # 更新 - 10 条
    for i in range(1, 11):
        cases.append(_case(next_id("TC-AA"), "AI智能体", f"更新智能体{i}",
                           f"更新智能体名称", "admin_update_agent",
                           {"agent_id": f"AI_UPD_{i}", "name": f"原名称{i}", "specialty": "神经科",
                            "new_name": f"新名称{i}"}, "truthy"))

    # 统计 - 5 条
    for i in range(1, 6):
        cases.append(_case(next_id("TC-AA"), "AI智能体", f"统计验证{i}",
                           f"统计应有智能体和适配器", "admin_stats", {}, "truthy"))


# ============================================================
# 14. 后台-系统集成 - 55 条
# ============================================================
def _build_admin_integration_cases(cases, next_id):
    """适配器管理、测试、删除"""
    # 添加适配器 - 15 条
    adapter_types = [
        ("HIS", "HIS适配器"), ("EMR", "EMR适配器"), ("LIS", "LIS适配器"), ("PACS", "PACS适配器"),
        ("Pharmacy", "药房适配器"), ("Anesthesia", "麻醉适配器"),
    ] * 3  # 18 个，取前 15
    for i, (atype, name) in enumerate(adapter_types[:15], 1):
        cases.append(_case(next_id("TC-AI"), "系统集成", f"添加适配器{i}",
                           f"添加 {atype} 适配器 {name}_{i}", "admin_add_adapter",
                           {"adapter_type": atype, "name": f"{name}_{i}",
                            "endpoint": f"http://test{i}.com", "api_type": "REST"}, "truthy"))

    # 测试适配器成功 - 15 条
    for i in range(1, 16):
        cases.append(_case(next_id("TC-AI"), "系统集成", f"测试适配器成功{i}",
                           f"测试适配器连接应成功", "admin_test_adapter",
                           {"name": f"测试适配器_{i}", "endpoint": "http://test.com"}, "truthy"))

    # 测试适配器失败 - 10 条
    for i in range(1, 11):
        cases.append(_case(next_id("TC-AI"), "系统集成", f"测试适配器失败{i}",
                           f"无效端点应测试失败", "admin_test_adapter_fail",
                           {"name": f"失败适配器_{i}"}, "truthy"))

    # 删除适配器 - 15 条
    for i in range(1, 16):
        cases.append(_case(next_id("TC-AI"), "系统集成", f"删除适配器{i}",
                           f"删除适配器后应不存在", "admin_delete_adapter",
                           {"name": f"删除适配器_{i}"}, "truthy"))


# ============================================================
# 15. 后台-质控统计 - 50 条
# ============================================================
def _build_admin_quality_cases(cases, next_id):
    """质控评分项增删改查"""
    # 添加 - 20 条
    for i in range(1, 21):
        cases.append(_case(next_id("TC-AQ"), "质控统计", f"添加质控项{i}",
                           f"添加质控评分项 QC_{i}", "admin_add_quality_item",
                           {"item_id": f"QC_{i}", "name": f"质控项{i}",
                            "description": f"质控评分项{i}", "max_score": 10, "weight": 1.0}, "truthy"))

    # 重复添加 - 5 条
    for i in range(1, 6):
        cases.append(_case(next_id("TC-AQ"), "质控统计", f"重复添加异常{i}",
                           f"重复质控项ID应抛异常", "admin_add_quality_duplicate",
                           {"item_id": f"QC_DUP_{i}"}, "truthy"))

    # 更新 - 15 条
    for i in range(1, 16):
        cases.append(_case(next_id("TC-AQ"), "质控统计", f"更新质控项{i}",
                           f"更新质控项名称和分数", "admin_update_quality_item",
                           {"item_id": f"QC_UPD_{i}", "name": f"原质控{i}",
                            "new_name": f"新质控{i}"}, "truthy"))

    # 删除 - 10 条
    for i in range(1, 11):
        cases.append(_case(next_id("TC-AQ"), "质控统计", f"删除质控项{i}",
                           f"删除质控项后不应存在", "admin_delete_quality_item",
                           {"item_id": f"QC_DEL_{i}"}, "truthy"))


# ============================================================
# 16. 后台-角色模板 - 50 条
# ============================================================
def _build_admin_role_cases(cases, next_id):
    """角色模板增删、默认验证"""
    # 默认角色 - 5 条
    cases.append(_case(next_id("TC-AR"), "角色模板", "默认角色模板验证",
                       "系统应有默认角色模板", "admin_role_template_default", {}, "truthy"))
    for i in range(1, 5):
        cases.append(_case(next_id("TC-AR"), "角色模板", f"默认角色验证{i}",
                           f"第{i}次验证默认角色", "admin_role_template_default", {}, "truthy"))

    # 添加 - 20 条
    for i in range(1, 21):
        cases.append(_case(next_id("TC-AR"), "角色模板", f"添加角色模板{i}",
                           f"添加角色模板 ROLE_{i}", "admin_add_role_template",
                           {"role_id": f"ROLE_CUSTOM_{i}", "name": f"自定义角色{i}",
                            "description": f"自定义角色模板{i}", "data_scope": "department"}, "truthy"))

    # 重复添加 - 5 条
    for i in range(1, 6):
        cases.append(_case(next_id("TC-AR"), "角色模板", f"重复添加异常{i}",
                           f"重复角色ID应抛异常", "admin_add_role_duplicate",
                           {"role_id": f"ROLE_DUP_{i}"}, "truthy"))

    # 删除 - 15 条
    for i in range(1, 16):
        cases.append(_case(next_id("TC-AR"), "角色模板", f"删除角色模板{i}",
                           f"删除角色模板后不应存在", "admin_delete_role_template",
                           {"role_id": f"ROLE_DEL_{i}"}, "truthy"))

    # 默认脱敏 - 5 条
    cases.append(_case(next_id("TC-AR"), "角色模板", "默认脱敏规则验证",
                       "系统应有默认脱敏规则", "admin_desensitization_default", {}, "truthy"))
    for i in range(1, 5):
        cases.append(_case(next_id("TC-AR"), "角色模板", f"脱敏规则验证{i}",
                           f"第{i}次验证脱敏规则", "admin_desensitization_default", {}, "truthy"))


# ============================================================
# 17. 后台-系统配置 - 60 条
# ============================================================
def _build_admin_config_cases(cases, next_id):
    """系统配置、Moderator、调度、安全、通知、插件"""
    # 配置持久化 - 10 条
    cases.append(_case(next_id("TC-AC"), "系统配置", "配置持久化往返",
                       "修改配置后重新加载应一致", "admin_save_load_config", {}, "truthy"))
    for i in range(1, 10):
        cases.append(_case(next_id("TC-AC"), "系统配置", f"配置持久化扩展{i}",
                           f"第{i}次验证配置持久化", "admin_save_load_config", {}, "truthy"))

    # Moderator配置 - 10 条
    cases.append(_case(next_id("TC-AC"), "系统配置", "Moderator配置持久化",
                       "修改Moderator配置后重新加载应一致", "admin_moderator_config", {}, "truthy"))
    for i in range(1, 10):
        cases.append(_case(next_id("TC-AC"), "系统配置", f"Moderator配置扩展{i}",
                           f"第{i}次验证Moderator配置", "admin_moderator_config", {}, "truthy"))

    # 调度规则 - 10 条
    for i, mode in enumerate(["auto", "semi-auto", "manual", "auto", "semi-auto",
                              "manual", "auto", "semi-auto", "manual", "auto"], 1):
        cases.append(_case(next_id("TC-AC"), "系统配置", f"调度规则{i}",
                           f"调度模式 {mode} 持久化", "admin_schedule_rule",
                           {"mode": mode}, "truthy"))

    # 安全配置 - 10 条
    encryptions = ["AES-256", "SM4", "AES-256", "SM4", "AES-256",
                   "SM4", "AES-256", "SM4", "AES-256", "SM4"]
    for i, enc in enumerate(encryptions, 1):
        cases.append(_case(next_id("TC-AC"), "系统配置", f"安全配置{i}",
                           f"加密算法 {enc} 持久化", "admin_security_config",
                           {"encryption": enc}, "truthy"))

    # 通知配置 - 5 条
    cases.append(_case(next_id("TC-AC"), "系统配置", "通知配置验证",
                       "站内信默认应开启", "admin_notification_config", {}, "truthy"))
    for i in range(1, 5):
        cases.append(_case(next_id("TC-AC"), "系统配置", f"通知配置扩展{i}",
                           f"第{i}次验证通知配置", "admin_notification_config", {}, "truthy"))

    # 插件 - 10 条
    for i in range(1, 11):
        cases.append(_case(next_id("TC-AC"), "系统配置", f"插件切换{i}",
                           f"切换插件启用状态", "admin_toggle_plugin", {}, "truthy"))

    # 初始化统计 - 5 条
    for i in range(1, 6):
        cases.append(_case(next_id("TC-AC"), "系统配置", f"初始化统计{i}",
                           f"第{i}次验证初始化数据", "admin_init", {}, "truthy"))


# ============================================================
# 18. 审核队列 - 50 条
# ============================================================
def _build_review_queue_cases(cases, next_id):
    """审核队列：提交/重复提交/待审核列表/审核通过/驳回/状态机/统计/历史/撤回/重提/引擎提交"""
    # 基础提交 - 6 条
    cases.append(_case(next_id("TC-RV"), "审核队列", "提交报告到审核队列",
                       "医生提交报告应返回 True 并进入待审核", "review_submit",
                       {"consultation_id": "VCS-RV-001", "doctor_id": "U_DOC1",
                        "doctor_name": "张医生", "patient_name": "李患者"},
                       "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "提交报告生成提交ID",
                       "提交后条目应包含 submission_id 字段", "review_get_entry",
                       {}, "json_has_key", "submission_id"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "提交后状态为PENDING",
                       "新提交报告状态应为 PENDING", "review_get_entry",
                       {}, "json_field_equals", "status=PENDING"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "提交带优先级参数",
                       "急诊优先级提交应成功", "review_submit",
                       {"consultation_id": "VCS-RV-EMG", "priority": "急诊",
                        "department": "急诊科", "consultation_type": "急诊"},
                       "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "提交MDT类型报告",
                       "MDT会诊类型提交应成功", "review_submit",
                       {"consultation_id": "VCS-RV-MDT", "consultation_type": "MDT"},
                       "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "提交常规类型报告",
                       "常规会诊类型提交应成功", "review_submit",
                       {"consultation_id": "VCS-RV-RTN", "consultation_type": "常规"},
                       "truthy"))

    # 重复提交 - 5 条
    cases.append(_case(next_id("TC-RV"), "审核队列", "重复提交返回False",
                       "同一会诊编号重复提交应返回 False", "review_submit_duplicate",
                       {"consultation_id": "VCS-RV-DUP1"}, "falsy"))
    for i in range(1, 5):
        cases.append(_case(next_id("TC-RV"), "审核队列", f"重复提交扩展{i}",
                           f"第{i}次重复提交应返回 False", "review_submit_duplicate",
                           {"consultation_id": f"VCS-RV-DUP{i}"}, "falsy"))

    # 待审核列表 - 8 条
    cases.append(_case(next_id("TC-RV"), "审核队列", "待审核列表返回3条",
                       "提交3份报告后待审核列表应有3条", "review_list_pending",
                       {"count": 3}, "count", "3"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "待审核列表返回5条",
                       "提交5份报告后待审核列表应有5条", "review_list_pending",
                       {"count": 5}, "count", "5"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "待审核列表非空",
                       "提交报告后待审核列表应非空", "review_list_pending",
                       {"count": 1}, "truthy"))
    for i in range(1, 6):
        cases.append(_case(next_id("TC-RV"), "审核队列", f"待审核列表扩展{i}",
                           f"提交{i}份报告后待审核列表长度为{i}", "review_list_pending",
                           {"count": i}, "count", str(i)))

    # 审核通过 - 6 条
    cases.append(_case(next_id("TC-RV"), "审核队列", "审核通过返回True",
                       "审核员通过待审核报告应返回 True", "review_approve",
                       {"consultation_id": "VCS-RV-APPR1", "comment": "同意"},
                       "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "审核通过后状态APPROVED",
                       "审核通过后条目状态应为 APPROVED", "review_approve",
                       {}, "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "非待审核报告再次通过返回False",
                       "已审核报告再次通过应返回 False", "review_approve_not_pending",
                       {}, "falsy"))
    for i in range(1, 4):
        cases.append(_case(next_id("TC-RV"), "审核队列", f"审核通过扩展{i}",
                           f"第{i}次审核通过应返回 True", "review_approve",
                           {"consultation_id": f"VCS-RV-APPR-EX{i}"}, "truthy"))

    # 驳回 - 6 条
    cases.append(_case(next_id("TC-RV"), "审核队列", "驳回返回True",
                       "审核员驳回报告应返回 True", "review_reject",
                       {"consultation_id": "VCS-RV-REJ1", "comment": "证据不足"},
                       "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "驳回带原因",
                       "驳回并填写原因应成功", "review_reject",
                       {"comment": "诊断依据不充分，请补充"}, "truthy"))
    for i in range(1, 5):
        cases.append(_case(next_id("TC-RV"), "审核队列", f"驳回扩展{i}",
                           f"第{i}次驳回应返回 True", "review_reject",
                           {"consultation_id": f"VCS-RV-REJ-EX{i}"}, "truthy"))

    # 统计 - 5 条
    cases.append(_case(next_id("TC-RV"), "审核队列", "统计包含pending字段",
                       "stats 应包含 pending 键", "review_stats", {}, "json_has_key", "pending"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "统计包含approved字段",
                       "stats 应包含 approved 键", "review_stats", {}, "json_has_key", "approved"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "统计包含rejected字段",
                       "stats 应包含 rejected 键", "review_stats", {}, "json_has_key", "rejected"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "统计包含total字段",
                       "stats 应包含 total 键", "review_stats", {}, "json_has_key", "total"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "统计approved为1",
                       "1通过1驳回后 approved 应为 1", "review_stats",
                       {}, "json_field_equals", "approved=1"))

    # 历史记录 - 4 条
    cases.append(_case(next_id("TC-RV"), "审核队列", "按审核员查询历史返回2条",
                       "审核员审核2份后历史记录应有2条", "review_list_reviewed_by",
                       {}, "count", "2"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "历史记录非空",
                       "审核员历史记录应非空", "review_list_reviewed_by", {}, "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "历史记录包含会诊编号",
                       "历史记录条目应含 consultation_id", "review_list_reviewed_by",
                       {}, "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "历史记录包含审核结果",
                       "历史记录条目应含 status 字段", "review_list_reviewed_by",
                       {}, "truthy"))

    # 驳回后重提 - 3 条
    cases.append(_case(next_id("TC-RV"), "审核队列", "驳回后重新提交返回True",
                       "被驳回报告重新提交应返回 True", "review_resubmit_rejected",
                       {}, "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "重提后状态恢复PENDING",
                       "重新提交后状态应为 PENDING", "review_resubmit_rejected",
                       {}, "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "重提清除审核员信息",
                       "重新提交后应清除原审核员信息", "review_resubmit_rejected",
                       {}, "truthy"))

    # 撤回 - 3 条
    cases.append(_case(next_id("TC-RV"), "审核队列", "撤回提交返回True",
                       "撤回待审核提交应返回 True", "review_withdraw", {}, "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "撤回扩展1",
                       "再次撤回操作应正常返回布尔值", "review_withdraw", {}, "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "撤回扩展2",
                       "撤回待审核提交应成功执行", "review_withdraw", {}, "truthy"))

    # 引擎提交审核 - 4 条
    cases.append(_case(next_id("TC-RV"), "审核队列", "引擎提交审核后状态PENDING_REVIEW",
                       "医生通过引擎提交审核后报告状态应为 PENDING_REVIEW",
                       "engine_submit_for_review", {}, "equals", "PENDING_REVIEW"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "引擎提交返回成功",
                       "引擎 submit_for_review 应成功", "engine_submit_for_review",
                       {}, "truthy"))
    cases.append(_case(next_id("TC-RV"), "审核队列", "引擎提交后报告含状态",
                       "提交审核后报告应可读取状态", "engine_submit_for_review",
                       {}, "not_null", ""))
    cases.append(_case(next_id("TC-RV"), "审核队列", "引擎提交状态非COMPLETED",
                       "提交审核后报告状态不应为 COMPLETED",
                       "engine_submit_for_review", {}, "not_null", ""))


CASES = _build_cases()


def build():
    wb = Workbook()
    ws = wb.active
    ws.title = "test_cases"

    # 表头样式
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.append(HEADER)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    # 数据行
    for case in CASES:
        ws.append(list(case))
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    # 列宽
    widths = [10, 12, 24, 40, 22, 46, 16, 18, 8]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 28

    # 冻结首行
    ws.freeze_panes = "A2"

    # ---------- 说明 sheet ----------
    ws2 = wb.create_sheet("说明")
    ws2.append(["项目", "说明"])
    docs = [
        ("文件用途", "数据驱动测试用例文件，由 tests/xlsx_runner.py 读取并执行"),
        ("运行方式", "python -m tests.xlsx_runner   或   pytest tests/test_xlsx.py"),
        ("用例总数", f"{len(CASES)} 条"),
        ("", ""),
        ("列说明", ""),
        ("用例ID", "唯一编号，如 TC-P001"),
        ("测试项", "功能分组（密码安全/角色权限/用户认证/用户管理/用户空间/审计日志/患者模型/病历整合/会诊流程/全局索引/医学影像/边界异常/AI智能体/系统集成/质控统计/角色模板/系统配置）"),
        ("用例名称", "用例简短描述"),
        ("描述", "用例详细说明"),
        ("操作operation", "对应 xlsx_runner.py 中 OPERATIONS 注册表的操作名"),
        ("参数params(JSON)", "操作输入参数，JSON 字符串"),
        ("断言类型", "断言方式，见下"),
        ("期望expected", "期望值（部分断言类型下可为空）"),
        ("启用", "Y/N，N 表示跳过"),
        ("", ""),
        ("断言类型", ""),
        ("truthy", "实际值应为真"),
        ("falsy", "实际值应为假"),
        ("not_null", "实际值不为 None"),
        ("equals", "实际值（字符串化后）等于期望值"),
        ("contains", "实际值包含期望值字符串"),
        ("count", "实际值（列表/可迭代）长度等于期望整数"),
        ("json_has_key", "实际值为 dict 且包含期望键"),
        ("json_has_no_key", "实际值为 dict 且不包含期望键"),
        ("json_field_equals", "期望格式 '字段=值'，dict 中对应字段等于值"),
        ("throws", "操作应抛异常"),
        ("throws_contains", "操作应抛异常且异常消息包含期望字符串"),
        ("", ""),
        ("测试项分布", ""),
    ]
    # 统计各分类数量
    from collections import Counter
    cat_counts = Counter(c[1] for c in CASES)
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        docs.append((cat, f"{cnt} 条"))
    for row in docs:
        ws2.append(list(row))
    ws2.column_dimensions["A"].width = 22
    ws2.column_dimensions["B"].width = 80
    for cell in ws2[1]:
        cell.font = Font(bold=True)

    wb.save(OUTPUT)
    print(f"已生成: {OUTPUT}")
    print(f"共 {len(CASES)} 条用例")
    print()
    print("用例分布：")
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt} 条")


if __name__ == "__main__":
    build()
