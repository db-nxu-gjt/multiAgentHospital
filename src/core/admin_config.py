"""
后端管理平台配置中心 - 持久化的系统级配置数据

依据《医院虚拟会诊系统后端管理平台完整功能》设计，覆盖：
1. 系统全局参数（医院信息、并发阈值、存储路径等）
2. AI 智能体配置（专科智能体生命周期、Moderator 阈值、LLM 底座）
3. 会诊调度规则（优先级时效、超时预警、人机协作模式）
4. 数据源适配器配置（HIS/EMR/LIS/PACS 接口参数）
5. 数据安全与脱敏规则（脱敏字段、加密开关、DLP 规则）
6. 质控评分模板（评分项配置、整改意见台账）
7. 消息通知配置（多渠道开关与模板）
8. 备份与灾备策略（周期、保留份数、降级策略）
9. 角色权限模板（自定义角色与权限矩阵）
10. 系统版本与插件管理

所有配置持久化到 data/admin/config.json，原子写入；提供单例 get_admin_config()。
"""
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional


def get_project_root() -> Path:
    """获取项目根目录，兼容开发环境和 PyInstaller 打包环境"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，使用 sys._MEIPASS 获取资源目录
        return Path(sys._MEIPASS)
    else:
        # 开发环境：从当前文件位置推算项目根目录
        return Path(__file__).parent.parent.parent


# ============================================================
# 数据模型
# ============================================================

@dataclass
class SystemGlobalConfig:
    """系统全局参数"""
    hospital_name: str = "示范医院"
    campus_info: str = "本部院区"
    system_logo: str = ""
    max_concurrent_consultations: int = 100
    record_load_limit: int = 50
    vector_search_concurrency: int = 8
    minio_endpoint: str = "http://localhost:9000"
    pdf_storage_path: str = "data/processed"
    single_file_size_limit_mb: int = 50
    version: str = "2.2.0"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SystemGlobalConfig":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class AgentConfig:
    """单个 AI 智能体配置"""
    agent_id: str
    name: str
    specialty: str
    enabled: bool = True
    description: str = ""
    llm_backend: str = "rule-based"  # rule-based / DeepSeek / Qwen / GPT
    temperature: float = 0.3
    system_prompt: str = ""
    knowledge_base: str = "default"
    weight: float = 1.0
    version: str = "v1"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AgentConfig":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__ if k in d})


@dataclass
class ModeratorConfig:
    """主持人 Moderator Agent 全局配置"""
    max_discussion_rounds: int = 3
    consensus_threshold: float = 0.80
    enable_debate: bool = True
    weight_strategy: str = "evidence"  # evidence / confidence / hybrid
    uncertainty_threshold: float = 0.15  # 首选与次选置信度差小于阈值时标注不确定性
    report_summary_mode: str = "weighted"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ModeratorConfig":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class ConsultationScheduleRule:
    """会诊调度规则"""
    emergency_response_minutes: int = 2  # 急诊 AI 响应时效
    routine_response_hours: int = 24    # 常规时效
    mdt_response_hours: int = 48       # MDT 时效
    timeout_alert_channels: List[str] = field(default_factory=lambda: ["站内信"])
    escalation_targets: List[str] = field(default_factory=list)
    collaboration_mode: str = "semi-auto"  # auto / semi-auto / manual
    department_mode_overrides: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ConsultationScheduleRule":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class AdapterConfig:
    """数据源适配器配置"""
    adapter_type: str  # HIS / EMR / LIS / PACS / Pharmacy / Anesthesia
    name: str
    endpoint: str = ""
    api_type: str = "REST"  # REST / FHIR / WebService / Database / MQ
    username: str = ""
    api_key: str = ""
    sync_period_minutes: int = 30
    sync_mode: str = "incremental"  # incremental / full
    enabled: bool = True
    last_test_status: str = "未测试"  # 成功 / 失败 / 未测试
    last_test_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        # 不在配置文件中明文保存 api_key（基础脱敏）
        if d.get("api_key"):
            d["api_key"] = "****"
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AdapterConfig":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__ if k in d})


@dataclass
class DesensitizationRule:
    """数据脱敏规则"""
    scene: str  # display / export / research
    mask_patient_name: bool = True
    mask_id_card: bool = True
    mask_phone: bool = True
    mask_address: bool = True
    custom_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DesensitizationRule":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class SecurityConfig:
    """加密与安全配置"""
    tls_enabled: bool = True
    tls_version: str = "TLS1.3"
    storage_encryption: str = "AES-256"  # AES-256 / SM4
    sm2_cert_uploaded: bool = False
    sm2_cert_expiry: str = ""
    dlp_block_bulk_export: bool = True
    bulk_export_threshold: int = 100
    compliance_level: str = "等保三级"
    research_consent_required: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SecurityConfig":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class QualityControlItem:
    """质控评分项"""
    item_id: str
    name: str
    description: str = ""
    max_score: float = 10.0
    weight: float = 1.0
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "QualityControlItem":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__ if k in d})


@dataclass
class NotificationConfig:
    """消息通知配置"""
    channels: Dict[str, bool] = field(
        default_factory=lambda: {
            "站内信": True, "企业微信": False, "钉钉": False, "短信": False, "邮件": False
        }
    )
    templates: Dict[str, str] = field(
        default_factory=lambda: {
            "consultation_submitted": "您提交的会诊 {consultation_id} 已受理",
            "consultation_completed": "会诊 {consultation_id} 已完成，请及时查看报告",
            "consultation_timeout": "会诊 {consultation_id} 已超时，请尽快处理",
            "qc_rectification": "会诊 {consultation_id} 质控发现问题，请整改",
        }
    )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "NotificationConfig":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class BackupConfig:
    """备份与灾备策略"""
    auto_backup_enabled: bool = True
    backup_period_hours: int = 24
    keep_backup_count: int = 7
    last_backup_at: str = ""
    degraded_mode_on_ai_failure: bool = True
    degraded_mode: str = "manual"  # manual / readonly

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BackupConfig":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class RoleTemplate:
    """角色模板"""
    role_id: str
    name: str
    description: str = ""
    permissions: List[str] = field(default_factory=list)  # 权限码列表
    data_scope: str = "self"  # self / department / campus / hospital

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RoleTemplate":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__ if k in d})


@dataclass
class PluginConfig:
    """插件配置"""
    plugin_id: str
    name: str
    plugin_type: str  # agent / adapter / model
    version: str = "1.0"
    enabled: bool = True
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PluginConfig":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__ if k in d})


# ============================================================
# 配置管理器
# ============================================================

class AdminConfigManager:
    """后端配置管理器 - 单例持久化在 data/admin/config.json"""

    DEFAULT_ROLE_TEMPLATES = [
        ("ROLE_ADMIN", "系统超级管理员", "全部权限", "*", "hospital"),
        ("ROLE_MEDICAL_ADMIN", "医务科管理员", "会诊工单/质控/统计报表/报告模板", "consultation,quality,report_template", "hospital"),
        ("ROLE_IT_ADMIN", "信息科运维管理员", "系统集成/数据库备份/监控告警/账号权限", "integration,backup,monitor,user", "hospital"),
        ("ROLE_AI_ADMIN", "AI 医学质控管理员", "智能体配置/知识图谱/循证库/病例库", "agent,knowledge,case_library", "hospital"),
        ("ROLE_DOCTOR", "主诊医师", "发起会诊/查看本人记录", "consultation_create,self_view", "self"),
        ("ROLE_REVIEWER", "医务审核员", "审核会诊报告", "report_review", "department"),
        ("ROLE_DEPT_ADMIN", "科室管理员", "本科室会诊管理", "dept_manage", "department"),
    ]

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            project_root = get_project_root()
            data_dir = project_root / "data" / "admin"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.data_dir / "config.json"
        # 各模块配置
        self.system: SystemGlobalConfig = SystemGlobalConfig()
        self.moderator: ModeratorConfig = ModeratorConfig()
        self.schedule_rule: ConsultationScheduleRule = ConsultationScheduleRule()
        self.security: SecurityConfig = SecurityConfig()
        self.notification: NotificationConfig = NotificationConfig()
        self.backup: BackupConfig = BackupConfig()
        self.agents: List[AgentConfig] = []
        self.adapters: List[AdapterConfig] = []
        self.desensitization: List[DesensitizationRule] = []
        self.quality_items: List[QualityControlItem] = []
        self.role_templates: List[RoleTemplate] = []
        self.plugins: List[PluginConfig] = []
        self._load()
        # 首次初始化默认值
        if not self.agents:
            self._init_default_agents()
        if not self.adapters:
            self._init_default_adapters()
        if not self.desensitization:
            self._init_default_desensitization()
        if not self.quality_items:
            self._init_default_quality_items()
        if not self.role_templates:
            self._init_default_role_templates()
        if not self.plugins:
            self._init_default_plugins()
        self._save()

    # ---------- 持久化 ----------
    def _load(self) -> None:
        if not self.config_file.exists():
            return
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.system = SystemGlobalConfig.from_dict(data.get("system", {}))
            self.moderator = ModeratorConfig.from_dict(data.get("moderator", {}))
            self.schedule_rule = ConsultationScheduleRule.from_dict(data.get("schedule_rule", {}))
            self.security = SecurityConfig.from_dict(data.get("security", {}))
            self.notification = NotificationConfig.from_dict(data.get("notification", {}))
            self.backup = BackupConfig.from_dict(data.get("backup", {}))
            self.agents = [AgentConfig.from_dict(a) for a in data.get("agents", [])]
            self.adapters = [AdapterConfig.from_dict(a) for a in data.get("adapters", [])]
            self.desensitization = [DesensitizationRule.from_dict(d) for d in data.get("desensitization", [])]
            self.quality_items = [QualityControlItem.from_dict(q) for q in data.get("quality_items", [])]
            self.role_templates = [RoleTemplate.from_dict(r) for r in data.get("role_templates", [])]
            self.plugins = [PluginConfig.from_dict(p) for p in data.get("plugins", [])]
        except (json.JSONDecodeError, OSError, TypeError) as e:
            print(f"⚠ 后端配置加载失败: {e}")

    def _save(self) -> None:
        data = {
            "system": self.system.to_dict(),
            "moderator": self.moderator.to_dict(),
            "schedule_rule": self.schedule_rule.to_dict(),
            "security": self.security.to_dict(),
            "notification": self.notification.to_dict(),
            "backup": self.backup.to_dict(),
            "agents": [a.to_dict() for a in self.agents],
            "adapters": [a.to_dict() for a in self.adapters],
            "desensitization": [d.to_dict() for d in self.desensitization],
            "quality_items": [q.to_dict() for q in self.quality_items],
            "role_templates": [r.to_dict() for r in self.role_templates],
            "plugins": [p.to_dict() for p in self.plugins],
            "version": "1.0",
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        tmp = self.config_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.config_file)

    # ---------- 默认数据初始化 ----------
    def _init_default_agents(self) -> None:
        defaults = [
            ("pulmonology_v1", "呼吸内科 AI 专家", "呼吸内科", "COPD、肺炎、肺栓塞、肺部占位"),
            ("cardiology_v1", "心内科 AI 专家", "心内科", "冠心病、心力衰竭、高血压、急性冠脉综合征"),
            ("neurology_v1", "神经内科 AI 专家", "神经内科", "脑血管疾病、眩晕综合征"),
            ("endocrinology_v1", "内分泌科 AI 专家", "内分泌科", "糖尿病、代谢综合征"),
            ("radiology_v1", "影像科 AI 专家", "影像科", "影像报告解读、占位鉴别"),
            ("pharmacy_v1", "药学 AI 专家", "药学", "用药安全审核、药物相互作用"),
        ]
        for aid, name, spec, desc in defaults:
            self.agents.append(AgentConfig(
                agent_id=aid, name=name, specialty=spec, description=desc
            ))

    def _init_default_adapters(self) -> None:
        defaults = [
            ("HIS", "HIS 主适配器", "http://his.hospital.com/api", "REST"),
            ("EMR", "EMR 病历适配器", "http://emr.hospital.com/api", "FHIR"),
            ("LIS", "LIS 检验适配器", "http://lis.hospital.com/api", "REST"),
            ("PACS", "PACS 影像适配器", "http://pacs.hospital.com/api", "DICOMWeb"),
        ]
        for atype, name, endpoint, api_type in defaults:
            self.adapters.append(AdapterConfig(
                adapter_type=atype, name=name, endpoint=endpoint, api_type=api_type
            ))

    def _init_default_desensitization(self) -> None:
        for scene, name_mask, id_mask, phone_mask, addr_mask in [
            ("display", True, True, True, False),   # 病历展示
            ("export", True, True, True, True),     # 导出
            ("research", True, True, True, True),   # 科研
        ]:
            self.desensitization.append(DesensitizationRule(
                scene=scene,
                mask_patient_name=name_mask,
                mask_id_card=id_mask,
                mask_phone=phone_mask,
                mask_address=addr_mask,
            ))

    def _init_default_quality_items(self) -> None:
        defaults = [
            ("QC-01", "病历完整性", "病历字段是否完整、必填项是否齐全", 15.0, 1.0),
            ("QC-02", "AI 循证依据", "诊断建议是否有循证等级与文献支持", 20.0, 1.2),
            ("QC-03", "诊断逻辑", "鉴别诊断逻辑是否合理、置信度合适", 20.0, 1.2),
            ("QC-04", "方案合理性", "治疗方案是否符合指南、用药安全", 20.0, 1.1),
            ("QC-05", "报告完整性", "报告字段是否完整、格式是否规范", 15.0, 1.0),
            ("QC-06", "随访计划", "是否给出明确随访建议", 10.0, 0.8),
        ]
        for qid, name, desc, max_s, w in defaults:
            self.quality_items.append(QualityControlItem(
                item_id=qid, name=name, description=desc, max_score=max_s, weight=w
            ))

    def _init_default_role_templates(self) -> None:
        for rid, name, desc, perms, scope in self.DEFAULT_ROLE_TEMPLATES:
            self.role_templates.append(RoleTemplate(
                role_id=rid, name=name, description=desc,
                permissions=perms.split(","), data_scope=scope
            ))

    def _init_default_plugins(self) -> None:
        defaults = [
            ("PLG_PULMONARY", "呼吸内科智能体插件", "agent", "v1", "呼吸系统疾病诊断能力"),
            ("PLG_CARDIOLOGY", "心内科智能体插件", "agent", "v1", "心血管疾病诊断能力"),
            ("PLG_HIS_ADAPTER", "HIS 适配器插件", "adapter", "v1", "医院信息系统集成"),
            ("PLG_DEEPSEEK", "DeepSeek LLM 底座", "model", "v1", "通用大语言模型底座"),
        ]
        for pid, name, ptype, ver, desc in defaults:
            self.plugins.append(PluginConfig(
                plugin_id=pid, name=name, plugin_type=ptype, version=ver, description=desc
            ))

    # ---------- CRUD 接口 ----------
    def save_all(self) -> None:
        self._save()

    # 智能体
    def add_agent(self, agent: AgentConfig) -> None:
        if any(a.agent_id == agent.agent_id for a in self.agents):
            raise ValueError(f"智能体 ID {agent.agent_id} 已存在")
        self.agents.append(agent)
        self._save()

    def update_agent(self, agent_id: str, **fields) -> AgentConfig:
        for a in self.agents:
            if a.agent_id == agent_id:
                for k, v in fields.items():
                    if hasattr(a, k):
                        setattr(a, k, v)
                self._save()
                return a
        raise ValueError(f"智能体 {agent_id} 不存在")

    def delete_agent(self, agent_id: str) -> bool:
        before = len(self.agents)
        self.agents = [a for a in self.agents if a.agent_id != agent_id]
        if len(self.agents) < before:
            self._save()
            return True
        return False

    def toggle_agent(self, agent_id: str) -> bool:
        for a in self.agents:
            if a.agent_id == agent_id:
                a.enabled = not a.enabled
                self._save()
                return a.enabled
        raise ValueError(f"智能体 {agent_id} 不存在")

    # 适配器
    def add_adapter(self, adapter: AdapterConfig) -> None:
        self.adapters.append(adapter)
        self._save()

    def update_adapter(self, idx: int, **fields) -> AdapterConfig:
        if idx < 0 or idx >= len(self.adapters):
            raise ValueError("适配器索引无效")
        a = self.adapters[idx]
        for k, v in fields.items():
            if hasattr(a, k):
                setattr(a, k, v)
        self._save()
        return a

    def delete_adapter(self, idx: int) -> bool:
        if 0 <= idx < len(self.adapters):
            self.adapters.pop(idx)
            self._save()
            return True
        return False

    def test_adapter(self, idx: int) -> tuple:
        """模拟适配器连通性测试"""
        if 0 <= idx < len(self.adapters):
            a = self.adapters[idx]
            # 简单模拟：检查 endpoint 是否非空
            ok = bool(a.endpoint) and a.endpoint.startswith("http")
            a.last_test_status = "成功" if ok else "失败"
            a.last_test_at = time.strftime("%Y-%m-%d %H:%M:%S")
            self._save()
            return (a.last_test_status, a.last_test_at)
        return ("失败", "适配器不存在")

    # 质控项
    def add_quality_item(self, item: QualityControlItem) -> None:
        if any(q.item_id == item.item_id for q in self.quality_items):
            raise ValueError(f"质控项 ID {item.item_id} 已存在")
        self.quality_items.append(item)
        self._save()

    def update_quality_item(self, item_id: str, **fields) -> QualityControlItem:
        for q in self.quality_items:
            if q.item_id == item_id:
                for k, v in fields.items():
                    if hasattr(q, k):
                        setattr(q, k, v)
                self._save()
                return q
        raise ValueError(f"质控项 {item_id} 不存在")

    def delete_quality_item(self, item_id: str) -> bool:
        before = len(self.quality_items)
        self.quality_items = [q for q in self.quality_items if q.item_id != item_id]
        if len(self.quality_items) < before:
            self._save()
            return True
        return False

    # 角色模板
    def add_role_template(self, role: RoleTemplate) -> None:
        if any(r.role_id == role.role_id for r in self.role_templates):
            raise ValueError(f"角色 ID {role.role_id} 已存在")
        self.role_templates.append(role)
        self._save()

    def delete_role_template(self, role_id: str) -> bool:
        before = len(self.role_templates)
        self.role_templates = [r for r in self.role_templates if r.role_id != role_id]
        if len(self.role_templates) < before:
            self._save()
            return True
        return False

    # 插件
    def toggle_plugin(self, plugin_id: str) -> bool:
        for p in self.plugins:
            if p.plugin_id == plugin_id:
                p.enabled = not p.enabled
                self._save()
                return p.enabled
        raise ValueError(f"插件 {plugin_id} 不存在")

    # 统计
    def stats(self) -> dict:
        return {
            "agent_total": len(self.agents),
            "agent_enabled": sum(1 for a in self.agents if a.enabled),
            "adapter_total": len(self.adapters),
            "adapter_enabled": sum(1 for a in self.adapters if a.enabled),
            "quality_items": len(self.quality_items),
            "role_templates": len(self.role_templates),
            "plugins": len(self.plugins),
            "plugins_enabled": sum(1 for p in self.plugins if p.enabled),
        }


# 全局单例
_admin_config: Optional[AdminConfigManager] = None


def get_admin_config() -> AdminConfigManager:
    global _admin_config
    if _admin_config is None:
        _admin_config = AdminConfigManager()
    return _admin_config
