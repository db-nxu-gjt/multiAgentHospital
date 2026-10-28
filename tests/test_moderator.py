"""
主持人智能体测试 - 共识识别、报告整合逻辑
"""
import pytest
from datetime import date

from src.core.patient import Patient, Gender, LabResult, ImagingReport
from src.core.agent import (
    PulmonologyAgent, CardiologyAgent, RadiologyAgent, PharmacyAgent,
    AgentOpinion
)
from src.core.moderator import ModeratorAgent


@pytest.fixture
def moderator():
    return ModeratorAgent(max_rounds=3)


@pytest.fixture
def copd_patient():
    return Patient(
        patient_id="M001",
        name="测试患者",
        gender=Gender.MALE,
        age=68,
        chief_complaint="咳嗽、咳痰伴呼吸困难2月",
        present_illness="2月来反复咳嗽咳痰，活动后气促",
        past_history="吸烟40年",
        lab_results=[
            LabResult("NT-proBNP", "500", "pg/mL", "<300", abnormal=True),
            LabResult("收缩压", "150", "mmHg", "90-140", abnormal=True)
        ],
        imaging_reports=[
            ImagingReport("CT", "胸部", "肺气肿", "肺气肿改变", report_date=date(2026, 7, 30))
        ]
    )


def test_conduct_consultation_basic(moderator, copd_patient):
    """基础会诊流程"""
    agents = [PulmonologyAgent(), CardiologyAgent()]
    report = moderator.conduct_consultation(
        patient=copd_patient,
        agents=agents,
        consultation_id="TEST-001",
        consultation_type="MDT"
    )
    assert report.consultation_id == "TEST-001"
    assert report.patient_id == "M001"
    assert report.status == "COMPLETED"
    assert len(report.differential_diagnosis) > 0
    assert report.final_conclusion != ""


def test_consensus_identifies_multi_specialty(moderator, copd_patient):
    """多专科支持的诊断应被识别为共识"""
    agents = [PulmonologyAgent(), CardiologyAgent(), RadiologyAgent()]
    report = moderator.conduct_consultation(
        patient=copd_patient, agents=agents,
        consultation_id="TEST-002", consultation_type="MDT"
    )
    # 至少有讨论记录
    assert len(report.discussion_summary) > 0
    # 鉴别诊断应去重并按置信度排序
    diseases = [d["disease"] for d in report.differential_diagnosis]
    assert len(diseases) == len(set(diseases))  # 无重复
    # 置信度应递减
    confs = [d["confidence"] for d in report.differential_diagnosis]
    assert confs == sorted(confs, reverse=True)


def test_consensus_filters_placeholder(moderator, copd_patient):
    """占位诊断（无影像资料、暂无明确）不应进入最终鉴别诊断"""
    agents = [RadiologyAgent(), CardiologyAgent()]
    # 不提供影像的患者
    patient_no_imaging = Patient(
        patient_id="M002", name="无影像", gender=Gender.MALE, age=50,
        chief_complaint="咳嗽", present_illness="咳嗽1周"
    )
    report = moderator.conduct_consultation(
        patient=patient_no_imaging, agents=agents,
        consultation_id="TEST-003", consultation_type="MDT"
    )
    for diag in report.differential_diagnosis:
        assert "无影像资料" not in diag["disease"]
        assert "暂无明确" not in diag["disease"]


def test_consensus_same_agent_dedup(moderator):
    """同一 Agent 内重复出现的疾病只算一次支持"""
    opinion = AgentOpinion(
        agent_id="dup_v1", agent_name="测试", specialty="测试科",
        differential_diagnosis=[
            {"disease": "测试疾病", "confidence": 0.8, "evidence_level": "B", "reasoning": "x"},
            {"disease": "测试疾病", "confidence": 0.7, "evidence_level": "B", "reasoning": "x"},
            {"disease": "测试疾病", "confidence": 0.6, "evidence_level": "B", "reasoning": "x"},
        ]
    )
    consensus, disagreement = moderator._identify_consensus([opinion])
    # 仅 1 个专科支持 -> 应进 disagreement
    assert any("测试疾病" in d for d in disagreement)
    assert all("测试疾病" not in c for c in consensus)


def test_consensus_multi_specialty(moderator):
    """不同 Agent 提出同一疾病应进共识"""
    opinion1 = AgentOpinion(
        agent_id="a1", agent_name="A", specialty="科A",
        differential_diagnosis=[
            {"disease": "肺炎", "confidence": 0.7, "evidence_level": "B", "reasoning": "x"}
        ]
    )
    opinion2 = AgentOpinion(
        agent_id="a2", agent_name="B", specialty="科B",
        differential_diagnosis=[
            {"disease": "肺炎", "confidence": 0.6, "evidence_level": "C", "reasoning": "y"}
        ]
    )
    consensus, _ = moderator._identify_consensus([opinion1, opinion2])
    assert any("肺炎" in c for c in consensus)


def test_consensus_zero_confidence_filtered(moderator):
    """零置信度项应被过滤"""
    opinion = AgentOpinion(
        agent_id="a1", agent_name="A", specialty="科A",
        differential_diagnosis=[
            {"disease": "测试", "confidence": 0, "evidence_level": "D", "reasoning": "x"}
        ]
    )
    consensus, disagreement = moderator._identify_consensus([opinion])
    assert all("测试" not in c for c in consensus)
    assert all("测试" not in d for d in disagreement)


def test_report_markdown_content(moderator, copd_patient):
    """Markdown 报告应包含核心字段"""
    agents = [PulmonologyAgent(), CardiologyAgent()]
    report = moderator.conduct_consultation(
        patient=copd_patient, agents=agents,
        consultation_id="TEST-MD", consultation_type="MDT"
    )
    md = report.to_markdown()
    assert "# 虚拟会诊报告" in md
    assert "TEST-MD" in md
    assert "鉴别诊断" in md
    assert "推荐检查" in md
    assert "治疗方案" in md
    assert "最终结论" in md


def test_report_dict_serializable(moderator, copd_patient):
    """报告 to_dict 应可被 JSON 序列化"""
    import json
    agents = [PulmonologyAgent(), CardiologyAgent()]
    report = moderator.conduct_consultation(
        patient=copd_patient, agents=agents,
        consultation_id="TEST-JSON", consultation_type="MDT"
    )
    d = report.to_dict()
    # 应可被 json 序列化
    json_str = json.dumps(d, ensure_ascii=False, default=str)
    assert "TEST-JSON" in json_str
    assert "differential_diagnosis" in json_str


def test_no_agents_raises(moderator, copd_patient):
    """无 Agent 应正常完成（空报告，不抛异常）"""
    report = moderator.conduct_consultation(
        patient=copd_patient, agents=[],
        consultation_id="TEST-EMPTY", consultation_type="MDT"
    )
    assert report.status == "COMPLETED"
    assert report.differential_diagnosis == []
    assert "信息不足" in report.final_conclusion or "不足以" in report.final_conclusion


def test_uncertainty_when_low_confidence(moderator, copd_patient):
    """首选置信度 < 0.7 时应记录不确定性"""
    agents = [PulmonologyAgent()]
    report = moderator.conduct_consultation(
        patient=copd_patient, agents=agents,
        consultation_id="TEST-UNCERT", consultation_type="MDT"
    )
    # 若首选置信度 <0.7 应有对应不确定性提示
    if report.differential_diagnosis:
        if report.differential_diagnosis[0]["confidence"] < 0.7:
            assert any("置信度不足" in u for u in report.uncertainties)


def test_pharmacy_recommendations_filtered(moderator):
    """药学 Agent 的中性条目（无相互作用）不应作为用药建议"""
    # 构造一个含多种用药的患者以触发药学 Agent
    from src.core.patient import Medication
    patient = Patient(
        patient_id="P0", name="x", gender=Gender.MALE, age=60,
        chief_complaint="高血压", present_illness="",
        medications=[
            Medication("氨氯地平", "5mg", "每日1次"),
        ]
    )
    agents = [PharmacyAgent()]
    report = moderator.conduct_consultation(
        patient=patient, agents=agents,
        consultation_id="TEST-PHARM", consultation_type="MDT"
    )
    for sug in report.medication_suggestions:
        assert "无明显相互作用" not in sug.content
        assert "当前用药无明显" not in sug.content
