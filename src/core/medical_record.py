"""
病历整合引擎
负责从多个医院信息系统抽取、清洗、标准化患者数据，构建患者全景视图
"""
import json
import re
from datetime import date, datetime
from typing import List, Dict, Any, Optional
import jieba

from ..adapters.base import HospitalAdapter
from .patient import (
    Patient, Gender, LabResult, ImagingReport,
    Medication, TimelineEvent
)


class MedicalRecordIntegrator:
    """病历整合器"""

    def __init__(self, adapters: List[HospitalAdapter] = None):
        self.adapters = adapters or []
        self.integration_log: List[str] = []

    def add_adapter(self, adapter: HospitalAdapter) -> None:
        self.adapters.append(adapter)

    def integrate(self, patient_id: str) -> Patient:
        """整合患者病历数据"""
        self.integration_log = []
        self.integration_log.append(f"开始整合患者 {patient_id} 的病历数据")

        raw_data: Dict[str, Any] = {}
        for adapter in self.adapters:
            try:
                if adapter.is_available():
                    data = adapter.fetch_patient_data(patient_id)
                    if not isinstance(data, dict) or not data:
                        self.integration_log.append(f"⚠ {adapter.system_name} 返回空数据")
                        continue
                    # 同名适配器合并：已有字段不被空值覆盖，列表字段累加去重
                    existing = raw_data.get(adapter.system_name)
                    if existing is None:
                        raw_data[adapter.system_name] = data
                    else:
                        raw_data[adapter.system_name] = self._merge_dict(existing, data)
                    self.integration_log.append(f"✓ 从 {adapter.system_name} 获取数据成功")
                else:
                    self.integration_log.append(f"✗ {adapter.system_name} 不可用")
            except Exception as e:
                self.integration_log.append(f"✗ {adapter.system_name} 获取失败: {str(e)}")

        patient = self._build_patient(patient_id, raw_data)
        self.integration_log.append(f"✓ 患者全景视图构建完成: {patient.name}")
        return patient

    @staticmethod
    def _merge_dict(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        """合并两个 dict：标量字段非空保留，列表字段合并去重"""
        merged = dict(a)
        for k, v in b.items():
            if k not in merged or merged[k] in (None, "", 0):
                merged[k] = v
            elif isinstance(merged[k], list) and isinstance(v, list):
                # 列表合并去重（dict 不可哈希，按 json 序列化去重）
                seen = {json.dumps(x, ensure_ascii=False, sort_keys=True) for x in merged[k]}
                for item in v:
                    key = json.dumps(item, ensure_ascii=False, sort_keys=True)
                    if key not in seen:
                        merged[k].append(item)
                        seen.add(key)
            elif isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = MedicalRecordIntegrator._merge_dict(merged[k], v)
        return merged

    def _build_patient(self, patient_id: str, raw_data: Dict[str, Any]) -> Patient:
        """根据原始数据构建患者对象"""
        # 默认空患者
        patient = Patient(
            patient_id=patient_id,
            name="",
            gender=Gender.UNKNOWN,
            age=0
        )

        # 从HIS获取基本信息（合并多个HIS/HIS_Mock适配器的数据，后到不覆盖已有非空字段）
        his_data = self._merge_adapter_data(raw_data, ["HIS", "HIS_Mock"])
        if his_data:
            # 仅在当前字段为空时填充，避免覆盖
            if not patient.name and his_data.get("name"):
                patient.name = his_data.get("name")
            if patient.gender == Gender.UNKNOWN and his_data.get("gender"):
                patient.gender = self._parse_gender(his_data.get("gender"))
            if patient.age == 0 and his_data.get("age") is not None:
                patient.age = self._parse_int(his_data.get("age"))
            if not patient.phone and his_data.get("phone"):
                patient.phone = his_data.get("phone")
            if not patient.id_card and his_data.get("id_card"):
                patient.id_card = his_data.get("id_card")
            if not patient.admission_id and his_data.get("admission_id"):
                patient.admission_id = his_data.get("admission_id")
            if not patient.department and his_data.get("department"):
                patient.department = his_data.get("department")
            if not patient.attending_doctor and his_data.get("attending_doctor"):
                patient.attending_doctor = his_data.get("attending_doctor")
            if patient.admission_date is None and his_data.get("admission_date"):
                patient.admission_date = self._parse_date(his_data.get("admission_date"))

        # 从EMR获取病历文本（合并多个适配器）
        emr_data = self._merge_adapter_data(raw_data, ["EMR", "EMR_Mock"])
        if emr_data:
            # 病历文本采用"已有则保留，无则补充"策略
            if not patient.chief_complaint:
                patient.chief_complaint = emr_data.get("chief_complaint", "")
            if not patient.present_illness:
                patient.present_illness = emr_data.get("present_illness", "")
            if not patient.past_history:
                patient.past_history = emr_data.get("past_history", "")
            if not patient.personal_history:
                patient.personal_history = emr_data.get("personal_history", "")
            if not patient.family_history:
                patient.family_history = emr_data.get("family_history", "")
            if not patient.physical_exam:
                patient.physical_exam = emr_data.get("physical_exam", "")

        # 从LIS获取检验结果（合并多个适配器并按项目去重）
        lis_data = self._merge_adapter_data(raw_data, ["LIS", "LIS_Mock"])
        if lis_data:
            lab_results = self._parse_lab_results(lis_data.get("lab_results", []))
            # 与已有结果按"项目名+日期"去重合并
            existing_keys = {(r.item_name, r.test_date) for r in patient.lab_results}
            for r in lab_results:
                key = (r.item_name, r.test_date)
                if key not in existing_keys:
                    patient.lab_results.append(r)
                    existing_keys.add(key)

        # 从PACS获取影像报告（合并多个适配器）
        pacs_data = self._merge_adapter_data(raw_data, ["PACS", "PACS_Mock"])
        if pacs_data:
            imaging_reports = self._parse_imaging_reports(pacs_data.get("imaging_reports", []))
            existing_keys = {(r.modality, r.body_part, r.report_date) for r in patient.imaging_reports}
            for r in imaging_reports:
                key = (r.modality, r.body_part, r.report_date)
                if key not in existing_keys:
                    patient.imaging_reports.append(r)
                    existing_keys.add(key)

        # 用药记录可以从HIS或药房系统获取（合并去重）
        medications_data = []
        for adapter_keys in (["HIS", "HIS_Mock"], ["Pharmacy", "Pharmacy_Mock"]):
            data = self._merge_adapter_data(raw_data, adapter_keys)
            if data and isinstance(data.get("medications"), list):
                medications_data.extend(data["medications"])
        if medications_data:
            existing_drugs = {m.drug_name if hasattr(m, "drug_name") else m.get("drug_name", "")
                              for m in patient.medications}
            for m in medications_data:
                if isinstance(m, dict):
                    med = Medication.from_dict(m)
                elif isinstance(m, Medication):
                    med = m
                else:
                    continue
                if med.drug_name and med.drug_name not in existing_drugs:
                    patient.medications.append(med)
                    existing_drugs.add(med.drug_name)

        # 构建时间线
        patient.timeline = self._build_timeline(patient, raw_data)

        # 计算风险评分
        patient.risk_scores = self._calculate_risk_scores(patient)

        # 原始数据保留用于调试，但导出报告时应通过 to_public_dict 脱敏
        patient.raw_data = raw_data
        return patient

    @staticmethod
    def _merge_adapter_data(raw_data: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """合并多个适配器返回的数据：后者不覆盖前者已有字段"""
        merged: Dict[str, Any] = {}
        for key in keys:
            data = raw_data.get(key)
            if not isinstance(data, dict):
                continue
            for k, v in data.items():
                if k not in merged or merged[k] in (None, "", [], {}):
                    merged[k] = v
        return merged

    @staticmethod
    def _parse_gender(value: Any) -> Gender:
        """委托 Gender.parse 统一解析逻辑"""
        return Gender.parse(value)

    @staticmethod
    def _parse_int(value: Any) -> int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_date(value: Any) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return None

    def _parse_lab_results(self, lab_data: List[Any]) -> List[LabResult]:
        results = []
        for item in lab_data:
            if isinstance(item, LabResult):
                results.append(item)
            elif isinstance(item, dict):
                results.append(LabResult.from_dict(item))
        return results

    def _parse_imaging_reports(self, imaging_data: List[Any]) -> List[ImagingReport]:
        reports = []
        for item in imaging_data:
            if isinstance(item, ImagingReport):
                reports.append(item)
            elif isinstance(item, dict):
                reports.append(ImagingReport.from_dict(item))
        return reports

    def _build_timeline(self, patient: Patient, raw_data: Dict[str, Any]) -> List[TimelineEvent]:
        """构建患者时间线"""
        events = []

        if patient.admission_date:
            events.append(TimelineEvent(
                event_date=patient.admission_date,
                event_type="入院",
                description=f"患者因{patient.chief_complaint or '待查'}入住{patient.department}",
                source="HIS"
            ))

        for lab in patient.lab_results:
            if lab.test_date:
                events.append(TimelineEvent(
                    event_date=lab.test_date,
                    event_type="检验",
                    description=f"{lab.item_name}: {lab.value} {lab.unit}{'（异常）' if lab.abnormal else ''}",
                    source="LIS"
                ))

        for img in patient.imaging_reports:
            if img.report_date:
                events.append(TimelineEvent(
                    event_date=img.report_date,
                    event_type="影像",
                    description=f"{img.modality} {img.body_part}: {img.impression[:80]}",
                    source="PACS"
                ))

        # 按时间排序
        events.sort(key=lambda e: e.event_date)
        return events

    def _calculate_risk_scores(self, patient: Patient) -> Dict[str, float]:
        """计算风险评分（简化版）

        异常时记录到 integration_log，便于排查；不再静默吞掉
        """
        scores = {}

        # NEWS评分简化版：基于体温、心率、呼吸、血压、血氧、意识
        try:
            news = self._calculate_news_score(patient)
            scores["NEWS"] = news
        except Exception as e:
            self.integration_log.append(f"⚠ NEWS评分计算失败: {e}")

        # 基于异常指标数量的风险分
        abnormal_count = sum(1 for lab in patient.lab_results if lab.abnormal)
        scores["abnormal_lab_risk"] = min(abnormal_count * 0.5, 10.0)

        return scores

    def _calculate_news_score(self, patient: Patient) -> float:
        """简化版NEWS评分（基于生命体征）"""
        score = 0.0
        labs = {lab.item_name: lab for lab in patient.lab_results}

        def get_numeric_value(name: str) -> Optional[float]:
            """提取检验项的数值，支持"120/80"型血压格式（取收缩压）"""
            if name not in labs:
                return None
            try:
                val = str(labs[name].value).strip()
                # 处理范围值，如 "120/80"（仅取第一项作为收缩压/心率等）
                if "/" in val:
                    val = val.split("/")[0]
                # 处理 "<0.04" 等参考范围前缀
                val = val.lstrip("<>").strip()
                return float(val)
            except (ValueError, TypeError):
                return None

        # 心率（次/分）
        hr = get_numeric_value("心率")
        if hr is not None:
            if hr < 40 or hr > 130:
                score += 3
            elif 40 <= hr <= 50 or 111 <= hr <= 130:
                score += 1
            elif 91 <= hr <= 110:
                score += 2

        # 收缩压（mmHg）
        sbp = get_numeric_value("收缩压")
        if sbp is not None:
            if sbp < 90 or sbp > 220:
                score += 3
            elif 90 <= sbp <= 100:
                score += 2
            elif 101 <= sbp <= 110:
                score += 1

        # 血氧饱和度（%）
        spo2 = get_numeric_value("血氧饱和度")
        if spo2 is not None:
            if spo2 < 91:
                score += 3
            elif 91 <= spo2 <= 93:
                score += 2
            elif 94 <= spo2 <= 95:
                score += 1

        return score

    def get_integration_log(self) -> str:
        """获取整合日志"""
        return "\n".join(self.integration_log)


class NLPEngine:
    """简单的NLP引擎，用于病历文本处理"""

    # 医学症状词典（简化版）
    SYMPTOM_KEYWORDS = [
        "发热", "咳嗽", "咳痰", "胸痛", "呼吸困难", "心悸",
        "头晕", "头痛", "恶心", "呕吐", "腹痛", "腹泻",
        "乏力", "消瘦", "水肿", "晕厥", "意识障碍"
    ]

    # 疾病词典（简化版）
    DISEASE_KEYWORDS = [
        "高血压", "糖尿病", "冠心病", "心力衰竭", "肺炎",
        "慢性阻塞性肺疾病", "脑梗死", "脑出血", "肿瘤",
        "肝炎", "肾炎", "贫血"
    ]

    @classmethod
    def extract_symptoms(cls, text: str) -> List[str]:
        """从文本中提取症状关键词"""
        if not text:
            return []
        found = []
        for symptom in cls.SYMPTOM_KEYWORDS:
            if symptom in text:
                found.append(symptom)
        return found

    @classmethod
    def extract_diseases(cls, text: str) -> List[str]:
        """从文本中提取疾病关键词"""
        if not text:
            return []
        found = []
        for disease in cls.DISEASE_KEYWORDS:
            if disease in text:
                found.append(disease)
        return found

    @classmethod
    def segment_text(cls, text: str) -> List[str]:
        """中文分词"""
        if not text:
            return []
        return list(jieba.cut(text))

    @classmethod
    def extract_entities(cls, text: str) -> Dict[str, List[str]]:
        """综合实体抽取"""
        return {
            "symptoms": cls.extract_symptoms(text),
            "diseases": cls.extract_diseases(text),
            "tokens": cls.segment_text(text)[:50]
        }
