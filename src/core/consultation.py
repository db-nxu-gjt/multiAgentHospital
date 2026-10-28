"""
虚拟会诊引擎
整合病历、智能体、主持人，提供完整的会诊流程管理
"""
import uuid
import json
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional

from .patient import Patient, Priority
from .medical_record import MedicalRecordIntegrator
from .agent import SpecialistAgent, AgentRegistry
from .moderator import ModeratorAgent, ConsultationReport
from .knowledge_graph import MedicalKnowledgeGraph


class ConsultationStatus(Enum):
    DRAFT = "草稿"
    PENDING = "待审核"
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    PENDING_REVIEW = "待审核报告"
    ARCHIVED = "已归档"


class ConsultationEngine:
    """虚拟会诊引擎"""

    def __init__(self, integrator: MedicalRecordIntegrator = None,
                 knowledge_graph: MedicalKnowledgeGraph = None,
                 agent_registry: AgentRegistry = None):
        self.integrator = integrator or MedicalRecordIntegrator()
        self.knowledge_graph = knowledge_graph or MedicalKnowledgeGraph()
        self.agent_registry = agent_registry or AgentRegistry(self.knowledge_graph)
        self.moderator = ModeratorAgent(max_rounds=3)
        self.consultations: Dict[str, ConsultationReport] = {}
        self.consultation_requests: Dict[str, Dict[str, Any]] = {}

    def request_consultation(self, patient_id: str,
                            clinical_question: str,
                            consultation_type: str = "MDT",
                            priority: Priority = Priority.ROUTINE,
                            requested_agents: List[str] = None,
                            attending_doctor: str = "",
                            department: str = "") -> str:
        """发起会诊申请"""
        consultation_id = f"VCS-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        self.consultation_requests[consultation_id] = {
            "consultation_id": consultation_id,
            "patient_id": patient_id,
            "clinical_question": clinical_question,
            "consultation_type": consultation_type,
            "priority": priority.value,
            "requested_agents": requested_agents or [],
            "attending_doctor": attending_doctor,
            "department": department,
            "status": ConsultationStatus.PENDING.value,
            "created_at": datetime.now().isoformat()
        }

        return consultation_id

    def run_consultation(self, consultation_id: str,
                        patient: Patient = None,
                        auto_select_agents: bool = True,
                        selected_agent_ids: List[str] = None) -> ConsultationReport:
        """执行会诊"""
        request = self.consultation_requests.get(consultation_id)
        if not request:
            raise ValueError(f"会诊申请 {consultation_id} 不存在")

        # 如果未提供患者对象，则通过整合器获取
        if patient is None:
            patient = self.integrator.integrate(request["patient_id"])

        # 校验患者对象：必须能从适配器拿到基本数据（name 非空代表 HIS 数据已获取）
        if not patient or not patient.patient_id or not patient.name:
            raise ValueError(
                "无法获取有效患者对象（HIS 适配器未返回患者基本信息），无法启动会诊"
            )

        # 确定参与Agent：显式选择 > 申请时记录 > 自动推荐 > 全部Agent
        agent_ids = selected_agent_ids or request.get("requested_agents", [])
        if auto_select_agents and not agent_ids:
            recommendations = self.agent_registry.recommend_agents(patient)
            agent_ids = [rec["agent_id"] for rec in recommendations]

        # 自动推荐无结果时，使用所有已注册 Agent（MDT 场景默认全科会诊）
        if not agent_ids:
            agent_ids = [a["agent_id"] for a in self.agent_registry.list_agents()]

        if not agent_ids:
            raise ValueError("没有可用的智能体参与会诊（注册中心为空）")

        agents = []
        for agent_id in agent_ids:
            agent = self.agent_registry.get_agent(agent_id)
            if agent:
                agents.append(agent)

        if not agents:
            raise ValueError("选择的智能体均未在注册中心注册")

        # 更新状态
        request["status"] = ConsultationStatus.IN_PROGRESS.value

        # 主持人主持会诊
        report = self.moderator.conduct_consultation(
            patient=patient,
            agents=agents,
            consultation_id=consultation_id,
            consultation_type=request["consultation_type"]
        )

        self.consultations[consultation_id] = report
        request["status"] = ConsultationStatus.COMPLETED.value

        return report

    def get_report(self, consultation_id: str) -> Optional[ConsultationReport]:
        return self.consultations.get(consultation_id)

    def approve_report(self, consultation_id: str, reviewer: str,
                      signature: str = "") -> bool:
        """审核确认会诊报告"""
        report = self.consultations.get(consultation_id)
        if not report:
            return False

        report.status = "APPROVED"
        request = self.consultation_requests.get(consultation_id)
        if request:
            request["status"] = ConsultationStatus.ARCHIVED.value
            request["reviewer"] = reviewer
            request["reviewed_at"] = datetime.now().isoformat()
            request["signature"] = signature

        return True

    def submit_for_review(self, consultation_id: str) -> bool:
        """医生提交报告到待审核状态

        将已完成的会诊报告状态从 COMPLETED 改为 PENDING_REVIEW，
        表示医生已提交该报告等待审核员审核。
        """
        report = self.consultations.get(consultation_id)
        if not report:
            return False
        if report.status not in ("COMPLETED", "REJECTED"):
            return False
        report.status = "PENDING_REVIEW"
        request = self.consultation_requests.get(consultation_id)
        if request:
            request["status"] = ConsultationStatus.PENDING_REVIEW.value
        return True

    def reject_report(self, consultation_id: str, reviewer: str,
                      comment: str = "") -> bool:
        """驳回会诊报告"""
        report = self.consultations.get(consultation_id)
        if not report:
            return False
        report.status = "REJECTED"
        request = self.consultation_requests.get(consultation_id)
        if request:
            request["status"] = ConsultationStatus.DRAFT.value
            request["reviewer"] = reviewer
            request["reviewed_at"] = datetime.now().isoformat()
            request["review_comment"] = comment
        return True

    def get_consultation_requests(self) -> List[Dict[str, Any]]:
        return list(self.consultation_requests.values())

    def get_knowledge_graph_differential(self, patient: Patient) -> List[Dict[str, Any]]:
        """基于知识图谱进行鉴别诊断"""
        from .medical_record import NLPEngine
        symptoms = NLPEngine.extract_symptoms(
            f"{patient.chief_complaint} {patient.present_illness}"
        )
        return self.knowledge_graph.find_diseases_by_symptoms(symptoms, top_k=5)

    def save_report(self, consultation_id: str, filepath: str,
                   format: str = "json") -> None:
        """保存会诊报告"""
        report = self.consultations.get(consultation_id)
        if not report:
            raise ValueError(f"会诊报告 {consultation_id} 不存在")

        with open(filepath, "w", encoding="utf-8") as f:
            if format == "json":
                json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
            elif format == "markdown":
                f.write(report.to_markdown())

    def load_patient_from_json(self, filepath: str) -> Patient:
        """从JSON文件加载患者"""
        with open(filepath, "r", encoding="utf-8") as f:
            return Patient.from_json(f.read())
