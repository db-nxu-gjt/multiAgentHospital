"""
多智能体系统 - 专科AI专家智能体
"""
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .patient import Patient
from .evidence import EvidenceLevel, RecommendationStrength, EvidenceItem, Recommendation
from .knowledge_graph import MedicalKnowledgeGraph


@dataclass
class AgentOpinion:
    """单个智能体的会诊意见"""
    agent_id: str
    agent_name: str
    specialty: str
    differential_diagnosis: List[Dict[str, Any]] = field(default_factory=list)
    recommended_tests: List[str] = field(default_factory=list)
    treatment_plan: List[str] = field(default_factory=list)
    risk_assessment: str = ""
    key_points: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "specialty": self.specialty,
            "differential_diagnosis": self.differential_diagnosis,
            "recommended_tests": self.recommended_tests,
            "treatment_plan": self.treatment_plan,
            "risk_assessment": self.risk_assessment,
            "key_points": self.key_points,
            "confidence": round(self.confidence, 3)
        }


class SpecialistAgent(ABC):
    """专科智能体基类"""

    def __init__(self, agent_id: str, name: str, specialty: str,
                 knowledge_graph: MedicalKnowledgeGraph = None):
        self.agent_id = agent_id
        self.name = name
        self.specialty = specialty
        self.knowledge_graph = knowledge_graph

    @abstractmethod
    def analyze(self, patient: Patient) -> AgentOpinion:
        """分析患者数据并返回专科意见"""
        pass

    def _extract_symptoms_from_patient(self, patient: Patient) -> List[str]:
        """从患者病历中提取症状"""
        text = " ".join([
            patient.chief_complaint,
            patient.present_illness,
            patient.past_history,
            patient.physical_exam
        ])

        # 使用知识图谱中的症状实体匹配
        symptoms = []
        if self.knowledge_graph:
            for entity in self.knowledge_graph.get_entities_by_type("symptom"):
                if entity.match(text) and entity.name not in symptoms:
                    symptoms.append(entity.name)
        return symptoms

    def _get_lab_value(self, patient: Patient, item_name: str) -> Optional[str]:
        """获取指定检验项的值"""
        for lab in patient.lab_results:
            if item_name in lab.item_name or lab.item_name in item_name:
                return lab.value
        return None

    def _has_lab_abnormality(self, patient: Patient, item_name: str) -> bool:
        """检查指定检验项是否异常"""
        for lab in patient.lab_results:
            if item_name in lab.item_name or lab.item_name in item_name:
                return lab.abnormal
        return False

    def _get_imaging_findings(self, patient: Patient, modality: str = None) -> List[str]:
        """获取影像发现"""
        reports = patient.imaging_reports
        if modality:
            reports = [r for r in reports if r.modality == modality]
        return [r.impression for r in reports]

    def _create_recommendation(self, content: str, level: EvidenceLevel,
                               strength: RecommendationStrength,
                               source: str = "临床指南") -> Recommendation:
        """创建带证据的建议"""
        evidence = EvidenceItem(
            source=source,
            level=level,
            summary=f"基于{self.specialty}相关{source}"
        )
        return Recommendation(
            content=content,
            evidence_level=level,
            strength=strength,
            evidences=[evidence]
        )


class PulmonologyAgent(SpecialistAgent):
    """呼吸内科AI专家"""

    def __init__(self, knowledge_graph: MedicalKnowledgeGraph = None):
        super().__init__("pulmonology_v1", "呼吸内科AI专家", "呼吸内科", knowledge_graph)

    def analyze(self, patient: Patient) -> AgentOpinion:
        symptoms = self._extract_symptoms_from_patient(patient)
        text = f"{patient.chief_complaint} {patient.present_illness}"

        diagnosis = []

        # COPD诊断需要慢性咳嗽/咳痰等呼吸道症状
        has_cough = any(s in text for s in ["咳嗽", "咳痰"])
        has_dyspnea = any(s in text for s in ["呼吸困难", "气促", "气短", "喘憋"])

        if has_cough:
            # 有咳嗽/咳痰，COPD可能性较高
            diagnosis.append({
                "disease": "慢性阻塞性肺疾病急性加重",
                "confidence": 0.80 if has_dyspnea else 0.60,
                "evidence_level": "B",
                "reasoning": "患者存在慢性咳嗽/咳痰症状，结合吸烟/年龄因素需考虑COPD"
            })
            diagnosis.append({
                "disease": "社区获得性肺炎",
                "confidence": 0.65,
                "evidence_level": "B",
                "reasoning": "咳嗽咳痰伴呼吸困难需警惕肺部感染"
            })
        elif has_dyspnea:
            # 仅有呼吸困难/气促，无咳嗽咳痰，COPD可能性降低
            diagnosis.append({
                "disease": "慢性阻塞性肺疾病急性加重",
                "confidence": 0.40,
                "evidence_level": "C",
                "reasoning": "仅有呼吸困难/气促，缺乏慢性咳嗽咳痰，COPD可能性较低，需排除心源性呼吸困难"
            })

        if has_dyspnea and "胸痛" in text:
            diagnosis.append({
                "disease": "肺栓塞",
                "confidence": 0.35,
                "evidence_level": "C",
                "reasoning": "呼吸困难伴胸痛需排除肺栓塞"
            })

        # 影像异常提示
        imaging = self._get_imaging_findings(patient)
        if any("结节" in img or "占位" in img for img in imaging):
            diagnosis.append({
                "disease": "肺部占位性病变",
                "confidence": 0.55,
                "evidence_level": "B",
                "reasoning": "影像学发现肺部结节/占位需进一步鉴别"
            })

        return AgentOpinion(
            agent_id=self.agent_id,
            agent_name=self.name,
            specialty=self.specialty,
            differential_diagnosis=diagnosis or [{
                "disease": "暂无明确呼吸系统疾病",
                "confidence": 0.5,
                "evidence_level": "D",
                "reasoning": "当前信息不足以做出呼吸专科诊断"
            }],
            recommended_tests=["肺功能检查", "胸部CT", "血气分析", "痰培养"],
            treatment_plan=["支气管扩张剂雾化吸入", "氧疗", "必要时抗感染治疗"],
            risk_assessment="中低风险，需排除急性加重和感染",
            key_points=["关注呼吸道症状演变", "重视肺功能评估"],
            confidence=0.78
        )


class CardiologyAgent(SpecialistAgent):
    """心内科AI专家"""

    def __init__(self, knowledge_graph: MedicalKnowledgeGraph = None):
        super().__init__("cardiology_v1", "心内科AI专家", "心内科", knowledge_graph)

    def analyze(self, patient: Patient) -> AgentOpinion:
        text = f"{patient.chief_complaint} {patient.present_illness} {patient.past_history}"
        diagnosis = []

        # 检查关键指标
        bnp = self._get_lab_value(patient, "BNP") or self._get_lab_value(patient, "NT-proBNP")
        troponin = self._get_lab_value(patient, "肌钙蛋白")
        bp_high = self._has_lab_abnormality(patient, "收缩压")

        if "呼吸困难" in text or "水肿" in text or bnp:
            diagnosis.append({
                "disease": "心力衰竭",
                "confidence": 0.75 if bnp else 0.55,
                "evidence_level": "B",
                "reasoning": "呼吸困难/水肿提示心功能不全，BNP升高支持诊断"
            })

        # 识别更广泛的心血管症状，并按典型程度分层
        has_angina_keyword = "心绞痛" in text
        has_classic_angina = "胸骨后压榨性疼痛" in text or "压榨性胸痛" in text
        has_retrosternal_pain = "胸骨后疼痛" in text or "胸骨后" in text
        has_chest_pain = "胸痛" in text or "胸闷" in text or "心悸" in text

        if has_angina_keyword or has_classic_angina or has_retrosternal_pain or has_chest_pain or troponin:
            if troponin:
                chd_conf = 0.85
            elif has_angina_keyword or has_classic_angina:
                chd_conf = 0.82
            elif has_retrosternal_pain:
                chd_conf = 0.72
            else:
                chd_conf = 0.58

            diagnosis.append({
                "disease": "冠状动脉粥样硬化性心脏病",
                "confidence": chd_conf,
                "evidence_level": "B",
                "reasoning": "胸痛/心绞痛症状需警惕心肌缺血，肌钙蛋白异常提示急性冠脉综合征"
            })

        # 基于心血管危险因素评估
        risk_factors = 0
        risk_reasons = []
        if patient.age >= 55:
            risk_factors += 1
            risk_reasons.append("年龄≥55岁")
        if "高血压" in text or bp_high:
            risk_factors += 1
            risk_reasons.append("高血压")
        if "糖尿病" in text:
            risk_factors += 1
            risk_reasons.append("糖尿病")
        if "高脂血症" in text or self._has_lab_abnormality(patient, "总胆固醇"):
            risk_factors += 1
            risk_reasons.append("血脂异常")
        if "吸烟" in text:
            risk_factors += 1
            risk_reasons.append("吸烟")

        if risk_factors >= 2 and not any(d["disease"] == "冠状动脉粥样硬化性心脏病" for d in diagnosis):
            diagnosis.append({
                "disease": "冠状动脉粥样硬化性心脏病",
                "confidence": min(0.45 + risk_factors * 0.08, 0.75),
                "evidence_level": "B",
                "reasoning": f"存在多项心血管危险因素：{'，'.join(risk_reasons)}"
            })

        if bp_high or "高血压" in text:
            # 单纯血压升高，未合并急性心血管事件时，置信度适中
            has_acute_cardiac = any(d["disease"] == "冠状动脉粥样硬化性心脏病" for d in diagnosis)
            htn_conf = 0.75 if has_acute_cardiac else 0.70
            diagnosis.append({
                "disease": "高血压病",
                "confidence": htn_conf,
                "evidence_level": "A",
                "reasoning": "血压升高或既往高血压病史"
            })

        return AgentOpinion(
            agent_id=self.agent_id,
            agent_name=self.name,
            specialty=self.specialty,
            differential_diagnosis=diagnosis or [{
                "disease": "暂无明确心血管疾病",
                "confidence": 0.5,
                "evidence_level": "D",
                "reasoning": "缺乏典型心血管症状和异常指标"
            }],
            recommended_tests=["心电图", "超声心动图", "BNP/NT-proBNP", "心肌酶谱"],
            treatment_plan=["控制血压", "利尿减轻心脏负荷", "必要时冠脉评估"],
            risk_assessment="需排除急性心血管事件",
            key_points=["监测生命体征", "关注心电图动态变化"],
            confidence=0.80
        )


class NeurologyAgent(SpecialistAgent):
    """神经内科AI专家"""

    def __init__(self, knowledge_graph: MedicalKnowledgeGraph = None):
        super().__init__("neurology_v1", "神经内科AI专家", "神经内科", knowledge_graph)

    def analyze(self, patient: Patient) -> AgentOpinion:
        text = f"{patient.chief_complaint} {patient.present_illness}"
        diagnosis = []

        neuro_symptoms = ["头痛", "头晕", "眩晕", "意识障碍", "肢体无力", "言语不清"]
        has_neuro = any(s in text for s in neuro_symptoms)

        if has_neuro:
            diagnosis.append({
                "disease": "脑血管疾病",
                "confidence": 0.70,
                "evidence_level": "B",
                "reasoning": "神经系统症状需首先排除脑血管事件"
            })
            diagnosis.append({
                "disease": "眩晕综合征",
                "confidence": 0.40,
                "evidence_level": "C",
                "reasoning": "头晕/眩晕需鉴别中枢性与周围性"
            })

        return AgentOpinion(
            agent_id=self.agent_id,
            agent_name=self.name,
            specialty=self.specialty,
            differential_diagnosis=diagnosis or [{
                "disease": "暂无明确神经系统疾病",
                "confidence": 0.5,
                "evidence_level": "D",
                "reasoning": "无神经系统症状"
            }],
            recommended_tests=["头颅CT", "头颅MRI", "神经系统查体", "颈动脉超声"],
            treatment_plan=["明确病因后针对性治疗", "控制危险因素"],
            risk_assessment="若存在急性神经功能缺损需紧急处理",
            key_points=["FAST评估", "排除颅内出血"],
            confidence=0.72
        )


class EndocrinologyAgent(SpecialistAgent):
    """内分泌科AI专家"""

    def __init__(self, knowledge_graph: MedicalKnowledgeGraph = None):
        super().__init__("endocrinology_v1", "内分泌科AI专家", "内分泌科", knowledge_graph)

    def analyze(self, patient: Patient) -> AgentOpinion:
        text = f"{patient.chief_complaint} {patient.present_illness} {patient.past_history}"
        diagnosis = []

        glucose = self._get_lab_value(patient, "血糖") or self._get_lab_value(patient, "空腹血糖")
        hba1c = self._get_lab_value(patient, "糖化血红蛋白")

        if glucose or hba1c or "糖尿病" in text:
            diagnosis.append({
                "disease": "2型糖尿病",
                "confidence": 0.80 if hba1c else 0.60,
                "evidence_level": "A",
                "reasoning": "血糖升高或既往糖尿病病史"
            })

        if "多尿" in text or "多饮" in text:
            diagnosis.append({
                "disease": "糖尿病",
                "confidence": 0.65,
                "evidence_level": "B",
                "reasoning": "典型三多症状提示糖尿病可能"
            })

        return AgentOpinion(
            agent_id=self.agent_id,
            agent_name=self.name,
            specialty=self.specialty,
            differential_diagnosis=diagnosis or [{
                "disease": "暂无明确内分泌疾病",
                "confidence": 0.5,
                "evidence_level": "D",
                "reasoning": "无内分泌代谢异常提示"
            }],
            recommended_tests=["空腹血糖", "糖化血红蛋白", "肾功能", "血脂"],
            treatment_plan=["生活方式干预", "降糖药物治疗", "血糖监测"],
            risk_assessment="注意糖尿病急性并发症",
            key_points=["评估胰岛功能", "筛查并发症"],
            confidence=0.75
        )


class RadiologyAgent(SpecialistAgent):
    """影像科AI专家"""

    def __init__(self, knowledge_graph: MedicalKnowledgeGraph = None):
        super().__init__("radiology_v1", "影像科AI专家", "影像科", knowledge_graph)

    def analyze(self, patient: Patient) -> AgentOpinion:
        imaging = self._get_imaging_findings(patient)
        diagnosis = []

        if not imaging:
            return AgentOpinion(
                agent_id=self.agent_id,
                agent_name=self.name,
                specialty=self.specialty,
                differential_diagnosis=[{
                    "disease": "无影像资料",
                    "confidence": 0.0,
                    "evidence_level": "D",
                    "reasoning": "缺少影像检查报告"
                }],
                recommended_tests=["根据临床需要选择相应影像检查"],
                treatment_plan=["完善影像检查"],
                risk_assessment="无法评估",
                key_points=["影像检查不可或缺"],
                confidence=0.0
            )

        findings_text = " ".join(imaging)
        if "结节" in findings_text or "占位" in findings_text:
            diagnosis.append({
                "disease": "肺部/腹部占位性病变",
                "confidence": 0.60,
                "evidence_level": "B",
                "reasoning": "影像发现结节/占位，需结合临床进一步鉴别良恶性"
            })
        if "渗出" in findings_text or "实变" in findings_text:
            diagnosis.append({
                "disease": "肺部感染",
                "confidence": 0.70,
                "evidence_level": "B",
                "reasoning": "影像学见渗出/实变影"
            })
        if "胸腔积液" in findings_text:
            diagnosis.append({
                "disease": "胸腔积液",
                "confidence": 0.75,
                "evidence_level": "B",
                "reasoning": "影像学明确胸腔积液"
            })

        return AgentOpinion(
            agent_id=self.agent_id,
            agent_name=self.name,
            specialty=self.specialty,
            differential_diagnosis=diagnosis or [{
                "disease": "影像未见明确异常",
                "confidence": 0.5,
                "evidence_level": "C",
                "reasoning": "现有影像未见明显异常"
            }],
            recommended_tests=["必要时增强CT/MRI", "随访复查"],
            treatment_plan=["结合临床及其他检查综合判断"],
            risk_assessment="影像学仅提供形态学信息",
            key_points=["影像需结合临床", "注意对比前后影像"],
            confidence=0.82
        )


class PharmacyAgent(SpecialistAgent):
    """药学AI专家"""

    def __init__(self, knowledge_graph: MedicalKnowledgeGraph = None):
        super().__init__("pharmacy_v1", "药学AI专家", "药学", knowledge_graph)

    def analyze(self, patient: Patient) -> AgentOpinion:
        medications = patient.medications
        interactions = []

        # 处理 medications 可能是 dict 或 Medication 对象的情况
        def get_drug_name(m):
            if isinstance(m, dict):
                return m.get("drug_name", "")
            return getattr(m, "drug_name", "")

        # 简化版药物相互作用检查
        drug_names = [get_drug_name(m) for m in medications]
        if "阿司匹林" in drug_names and "华法林" in drug_names:
            interactions.append("阿司匹林与华法林合用增加出血风险")
        if "二甲双胍" in drug_names and any("造影剂" in d for d in drug_names):
            interactions.append("二甲双胍与造影剂合用需警惕乳酸酸中毒")

        return AgentOpinion(
            agent_id=self.agent_id,
            agent_name=self.name,
            specialty=self.specialty,
            differential_diagnosis=[],
            recommended_tests=["肝肾功能", "凝血功能（如使用抗凝药）"],
            treatment_plan=interactions or ["当前用药无明显相互作用"],
            risk_assessment="已完成用药安全性初审",
            key_points=["关注药物相互作用", "肝肾功能不全需调整剂量"],
            confidence=0.85
        )


class AgentRegistry:
    """智能体注册中心"""

    def __init__(self, knowledge_graph: MedicalKnowledgeGraph = None):
        self.knowledge_graph = knowledge_graph
        self._agents: Dict[str, SpecialistAgent] = {}
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        agents = [
            PulmonologyAgent(self.knowledge_graph),
            CardiologyAgent(self.knowledge_graph),
            NeurologyAgent(self.knowledge_graph),
            EndocrinologyAgent(self.knowledge_graph),
            RadiologyAgent(self.knowledge_graph),
            PharmacyAgent(self.knowledge_graph),
        ]
        for agent in agents:
            self._agents[agent.agent_id] = agent

    def get_agent(self, agent_id: str) -> Optional[SpecialistAgent]:
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, str]]:
        return [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "specialty": agent.specialty
            }
            for agent in self._agents.values()
        ]

    def recommend_agents(self, patient: Patient) -> List[Dict[str, Any]]:
        """根据患者病情推荐专科Agent"""
        text = f"{patient.chief_complaint} {patient.present_illness} {patient.past_history}"
        recommendations = []

        # 简单规则匹配
        if any(k in text for k in ["咳嗽", "咳痰", "呼吸困难", "胸痛", "气促"]):
            recommendations.append({
                "agent_id": "pulmonology_v1",
                "reason": "存在呼吸道症状"
            })

        if any(k in text for k in ["胸痛", "心悸", "水肿", "高血压", "心衰"]):
            recommendations.append({
                "agent_id": "cardiology_v1",
                "reason": "存在心血管症状或相关病史"
            })

        if any(k in text for k in ["头痛", "头晕", "意识障碍", "肢体无力"]):
            recommendations.append({
                "agent_id": "neurology_v1",
                "reason": "存在神经系统症状"
            })

        if any(k in text for k in ["多尿", "多饮", "糖尿病", "血糖"]) or patient.medications:
            recommendations.append({
                "agent_id": "endocrinology_v1",
                "reason": "存在糖尿病相关线索"
            })

        if patient.imaging_reports:
            recommendations.append({
                "agent_id": "radiology_v1",
                "reason": "已有影像检查需要影像科解读"
            })

        if patient.medications:
            recommendations.append({
                "agent_id": "pharmacy_v1",
                "reason": "需要用药安全审核"
            })

        # 去重
        seen = set()
        unique = []
        for rec in recommendations:
            if rec["agent_id"] not in seen:
                seen.add(rec["agent_id"])
                unique.append(rec)

        return unique
