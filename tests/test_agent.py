"""
智能体系统测试
"""
import pytest
from datetime import date

from src.core.patient import Patient, Gender, LabResult, ImagingReport
from src.core.agent import (
    AgentRegistry, PulmonologyAgent, CardiologyAgent,
    PharmacyAgent
)
from src.core.knowledge_graph import build_default_knowledge_graph


@pytest.fixture
def knowledge_graph():
    return build_default_knowledge_graph()


@pytest.fixture
def sample_patient():
    return Patient(
        patient_id="P003",
        name="王五",
        gender=Gender.MALE,
        age=68,
        chief_complaint="咳嗽、咳痰伴呼吸困难2月",
        present_illness="2月来反复咳嗽咳痰，活动后气促，吸烟40年。",
        past_history="高血压",
        lab_results=[
            LabResult("NT-proBNP", "500", "pg/mL", "<300", abnormal=True),
            LabResult("收缩压", "150", "mmHg", "90-140", abnormal=True)
        ],
        imaging_reports=[
            ImagingReport("CT", "胸部", "肺气肿改变", "肺气肿，右上肺结节", report_date=date(2026, 7, 30))
        ],
        medications=[
            {"drug_name": "氨氯地平", "dosage": "5mg", "frequency": "每日1次", "status": "current"}
        ]
    )


def test_agent_registry(knowledge_graph):
    registry = AgentRegistry(knowledge_graph)
    agents = registry.list_agents()
    assert len(agents) >= 6
    assert any(a["specialty"] == "呼吸内科" for a in agents)


def test_pulmonology_agent(knowledge_graph, sample_patient):
    agent = PulmonologyAgent(knowledge_graph)
    opinion = agent.analyze(sample_patient)
    assert opinion.agent_id == "pulmonology_v1"
    assert len(opinion.differential_diagnosis) > 0
    assert any("慢性阻塞性肺疾病" in d["disease"] for d in opinion.differential_diagnosis)


def test_cardiology_agent(knowledge_graph, sample_patient):
    agent = CardiologyAgent(knowledge_graph)
    opinion = agent.analyze(sample_patient)
    assert opinion.agent_id == "cardiology_v1"
    assert len(opinion.differential_diagnosis) > 0
    assert any("心力衰竭" in d["disease"] for d in opinion.differential_diagnosis)


def test_pharmacy_agent(knowledge_graph, sample_patient):
    agent = PharmacyAgent(knowledge_graph)
    opinion = agent.analyze(sample_patient)
    assert opinion.specialty == "药学"
    assert len(opinion.treatment_plan) >= 0


def test_agent_recommendation(knowledge_graph, sample_patient):
    registry = AgentRegistry(knowledge_graph)
    recommendations = registry.recommend_agents(sample_patient)
    recommended_ids = [r["agent_id"] for r in recommendations]
    assert "pulmonology_v1" in recommended_ids
    assert "cardiology_v1" in recommended_ids
    assert "radiology_v1" in recommended_ids
