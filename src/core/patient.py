"""
患者数据模型与全景视图
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import re


class Gender(Enum):
    MALE = "男"
    FEMALE = "女"
    UNKNOWN = "未知"

    @classmethod
    def parse(cls, value: Any) -> "Gender":
        """安全解析性别值，对非法输入返回 UNKNOWN 而非抛异常"""
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.UNKNOWN
        value_str = str(value).strip()
        # 反查枚举值
        for member in cls:
            if member.value == value_str:
                return member
        # 兼容英文/数字编码
        upper = value_str.upper()
        if upper in ("M", "MALE", "MAN", "1", "男", "男性", "男孩"):
            return cls.MALE
        if upper in ("F", "FEMALE", "WOMAN", "2", "女", "女性", "女孩"):
            return cls.FEMALE
        return cls.UNKNOWN


class Priority(Enum):
    EMERGENCY = "急诊"
    ROUTINE = "常规"
    MDT = "疑难"


@dataclass
class LabResult:
    """检验结果"""
    item_name: str
    value: str
    unit: str
    reference_range: str
    abnormal: bool = False
    test_date: Optional[date] = None
    department: str = ""

    def to_dict(self) -> dict:
        return {
            "item_name": self.item_name,
            "value": self.value,
            "unit": self.unit,
            "reference_range": self.reference_range,
            "abnormal": self.abnormal,
            "test_date": self.test_date.isoformat() if self.test_date else None,
            "department": self.department
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LabResult":
        return cls(
            item_name=data.get("item_name", ""),
            value=data.get("value", ""),
            unit=data.get("unit", ""),
            reference_range=data.get("reference_range", ""),
            abnormal=bool(data.get("abnormal", False)),
            test_date=_parse_date_safe(data.get("test_date")),
            department=data.get("department", "")
        )


@dataclass
class ImagingReport:
    """影像报告"""
    modality: str  # CT/MRI/X光/超声
    body_part: str
    findings: str
    impression: str
    report_date: Optional[date] = None

    def to_dict(self) -> dict:
        return {
            "modality": self.modality,
            "body_part": self.body_part,
            "findings": self.findings,
            "impression": self.impression,
            "report_date": self.report_date.isoformat() if self.report_date else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImagingReport":
        return cls(
            modality=data.get("modality", ""),
            body_part=data.get("body_part", ""),
            findings=data.get("findings", ""),
            impression=data.get("impression", ""),
            report_date=_parse_date_safe(data.get("report_date"))
        )


@dataclass
class MedicalImage:
    """医学影像图片附件

    支持 DICOM/JPG/PNG/BMP 等常见医学影像格式。
    图片文件独立存储在用户空间，本对象仅保存元数据。
    """
    image_id: str
    patient_id: str
    file_name: str
    file_path: str          # 相对或绝对路径
    image_type: str = "CT"  # CT/MRI/X光/超声/病理/其他
    body_part: str = ""
    description: str = ""
    uploaded_at: Optional[date] = None
    file_size: int = 0

    def to_dict(self) -> dict:
        return {
            "image_id": self.image_id,
            "patient_id": self.patient_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "image_type": self.image_type,
            "body_part": self.body_part,
            "description": self.description,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "file_size": self.file_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MedicalImage":
        return cls(
            image_id=data.get("image_id", ""),
            patient_id=data.get("patient_id", ""),
            file_name=data.get("file_name", ""),
            file_path=data.get("file_path", ""),
            image_type=data.get("image_type", "CT"),
            body_part=data.get("body_part", ""),
            description=data.get("description", ""),
            uploaded_at=_parse_date_safe(data.get("uploaded_at")),
            file_size=int(data.get("file_size", 0) or 0),
        )


@dataclass
class Medication:
    """用药记录"""
    drug_name: str
    dosage: str
    frequency: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = "current"  # current/stopped

    def to_dict(self) -> dict:
        return {
            "drug_name": self.drug_name,
            "dosage": self.dosage,
            "frequency": self.frequency,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Medication":
        return cls(
            drug_name=data.get("drug_name", ""),
            dosage=data.get("dosage", ""),
            frequency=data.get("frequency", ""),
            start_date=_parse_date_safe(data.get("start_date")),
            end_date=_parse_date_safe(data.get("end_date")),
            status=data.get("status", "current")
        )


@dataclass
class TimelineEvent:
    """病程时间线事件"""
    event_date: date
    event_type: str  # 入院/检查/手术/用药/会诊
    description: str
    source: str = ""

    def to_dict(self) -> dict:
        return {
            "event_date": self.event_date.isoformat(),
            "event_type": self.event_type,
            "description": self.description,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimelineEvent":
        return cls(
            event_date=_parse_date_safe(data.get("event_date")) or date.today(),
            event_type=data.get("event_type", ""),
            description=data.get("description", ""),
            source=data.get("source", "")
        )


@dataclass
class Patient:
    """患者实体"""
    patient_id: str
    name: str
    gender: Gender
    age: int
    phone: str = ""
    id_card: str = ""
    admission_id: str = ""
    department: str = ""
    attending_doctor: str = ""
    admission_date: Optional[date] = None

    # 病历数据
    chief_complaint: str = ""
    present_illness: str = ""
    past_history: str = ""
    personal_history: str = ""
    family_history: str = ""
    physical_exam: str = ""

    lab_results: List[LabResult] = field(default_factory=list)
    imaging_reports: List[ImagingReport] = field(default_factory=list)
    medical_images: List[MedicalImage] = field(default_factory=list)
    medications: List[Medication] = field(default_factory=list)
    timeline: List[TimelineEvent] = field(default_factory=list)

    # 风险评分
    risk_scores: Dict[str, float] = field(default_factory=dict)

    # 扩展字段
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def gender_str(self) -> str:
        return self.gender.value

    def get_summary(self) -> str:
        """生成患者病情摘要"""
        lines = [
            f"患者{self.name}，{self.gender_str}，{self.age}岁，{self.department}住院。",
            f"主诉：{self.chief_complaint or '未记录'}。",
            f"现病史：{self.present_illness or '未记录'}。",
            f"既往史：{self.past_history or '无特殊'}。",
        ]

        if self.lab_results:
            abnormal = [r for r in self.lab_results if r.abnormal]
            lines.append(f"异常检验指标：{len(abnormal)}项。" if abnormal else "检验指标无明显异常。")

        if self.imaging_reports:
            lines.append(f"影像检查：{len(self.imaging_reports)}项。")

        if self.medications:
            lines.append(f"当前用药：{len(self.medications)}种。")

        return "\n".join(lines)

    def get_key_findings(self) -> List[str]:
        """提取关键发现"""
        findings = []
        if self.chief_complaint:
            findings.append(f"主诉：{self.chief_complaint}")
        if self.present_illness:
            findings.append(f"现病史：{self.present_illness[:200]}...")
        for lab in self.lab_results:
            if lab.abnormal:
                findings.append(f"异常检验：{lab.item_name} {lab.value} {lab.unit}")
        for img in self.imaging_reports:
            findings.append(f"影像：{img.modality} {img.body_part} - {img.impression[:100]}")
        return findings

    def to_dict(self) -> dict:
        return {
            "patient_id": self.patient_id,
            "name": self.name,
            "gender": self.gender.value,
            "age": self.age,
            "phone": self.phone,
            "id_card": self.id_card,
            "admission_id": self.admission_id,
            "department": self.department,
            "attending_doctor": self.attending_doctor,
            "admission_date": self.admission_date.isoformat() if self.admission_date else None,
            "chief_complaint": self.chief_complaint,
            "present_illness": self.present_illness,
            "past_history": self.past_history,
            "personal_history": self.personal_history,
            "family_history": self.family_history,
            "physical_exam": self.physical_exam,
            "lab_results": [r.to_dict() for r in self.lab_results],
            "imaging_reports": [r.to_dict() for r in self.imaging_reports],
            "medical_images": [img.to_dict() for img in self.medical_images],
            "medications": [m.to_dict() for m in self.medications],
            "timeline": [t.to_dict() for t in self.timeline],
            "risk_scores": self.risk_scores,
            "raw_data": self.raw_data
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Patient":
        # 防御性默认值：缺失 patient_id/name/age 时使用占位值，避免崩溃
        return cls(
            patient_id=data.get("patient_id", "UNKNOWN"),
            name=data.get("name", ""),
            gender=Gender.parse(data.get("gender", "未知")),
            age=_safe_int(data.get("age", 0)),
            phone=data.get("phone", ""),
            id_card=data.get("id_card", ""),
            admission_id=data.get("admission_id", ""),
            department=data.get("department", ""),
            attending_doctor=data.get("attending_doctor", ""),
            admission_date=_parse_date_safe(data.get("admission_date")),
            chief_complaint=data.get("chief_complaint", ""),
            present_illness=data.get("present_illness", ""),
            past_history=data.get("past_history", ""),
            personal_history=data.get("personal_history", ""),
            family_history=data.get("family_history", ""),
            physical_exam=data.get("physical_exam", ""),
            lab_results=[LabResult.from_dict(r) for r in data.get("lab_results", []) if isinstance(r, dict)],
            imaging_reports=[ImagingReport.from_dict(r) for r in data.get("imaging_reports", []) if isinstance(r, dict)],
            medical_images=[MedicalImage.from_dict(img) for img in data.get("medical_images", []) if isinstance(img, dict)],
            medications=[Medication.from_dict(m) for m in data.get("medications", []) if isinstance(m, dict)],
            timeline=[TimelineEvent.from_dict(t) for t in data.get("timeline", []) if isinstance(t, dict)],
            risk_scores=data.get("risk_scores", {}) if isinstance(data.get("risk_scores"), dict) else {},
            raw_data=data.get("raw_data", {}) if isinstance(data.get("raw_data"), dict) else {}
        )

    def to_public_dict(self) -> dict:
        """导出脱敏后的患者信息（用于报告共享/审计），屏蔽敏感字段"""
        data = self.to_dict()
        # 移除内部测试标签
        data.pop("raw_data", None)
        # 屏蔽身份证号、电话（保留部分用于识别）
        if data.get("id_card"):
            data["id_card"] = data["id_card"][:6] + "********" if len(data["id_card"]) >= 6 else "******"
        if data.get("phone"):
            data["phone"] = data["phone"][:3] + "****" + data["phone"][-2:] if len(data["phone"]) >= 5 else "******"
        return data

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "Patient":
        return cls.from_dict(json.loads(json_str))


def _safe_int(value: Any) -> int:
    """安全转 int，非法值返回 0"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _parse_date_safe(value: Any) -> Optional[date]:
    """安全解析日期，支持多种格式与 None/异常"""
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None
