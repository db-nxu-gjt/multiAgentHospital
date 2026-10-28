"""
会诊引擎测试
"""
import pytest
from datetime import date

from src.core.consultation import ConsultationEngine
from src.core.patient import Patient, Gender, LabResult, ImagingReport
from src.core.knowledge_graph import build_default_knowledge_graph


@pytest.fixture
def engine():
    kg = build_default_knowledge_graph()
    return ConsultationEngine(knowledge_graph=kg)


@pytest.fixture
def sample_patient():
    return Patient(
        patient_id="P004",
        name="赵六",
        gender=Gender.FEMALE,
        age=72,
        department="心内科",
        chief_complaint="突发胸痛2小时",
        present_illness="胸骨后压榨性疼痛，向左肩放射，伴大汗。",
        past_history="高血压20年，糖尿病10年",
        lab_results=[
            LabResult("肌钙蛋白", "2.8", "ng/mL", "<0.04", abnormal=True),
            LabResult("NT-proBNP", "1200", "pg/mL", "<300", abnormal=True),
            LabResult("血糖", "8.5", "mmol/L", "3.9-6.1", abnormal=True),
            LabResult("收缩压", "160", "mmHg", "90-140", abnormal=True)
        ],
        imaging_reports=[
            ImagingReport("X线", "胸部", "心影增大", "心影增大，肺淤血", report_date=date(2026, 7, 31))
        ],
        medications=[
            {"drug_name": "阿司匹林", "dosage": "100mg", "frequency": "每日1次", "status": "current"},
            {"drug_name": "二甲双胍", "dosage": "0.5g", "frequency": "每日3次", "status": "current"}
        ]
    )


def test_request_consultation(engine):
    cid = engine.request_consultation(
        patient_id="P004",
        clinical_question="胸痛原因待查",
        consultation_type="急诊会诊"
    )
    assert cid.startswith("VCS-")
    assert len(engine.get_consultation_requests()) == 1


def test_run_consultation(engine, sample_patient):
    cid = engine.request_consultation(
        patient_id=sample_patient.patient_id,
        clinical_question="胸痛伴呼吸困难原因待查",
        consultation_type="MDT"
    )

    report = engine.run_consultation(cid, patient=sample_patient)
    assert report is not None
    assert report.consultation_id == cid
    assert len(report.differential_diagnosis) > 0
    assert len(report.recommended_tests) > 0
    assert report.final_conclusion != ""
    assert report.status == "COMPLETED"


def test_report_markdown(engine, sample_patient):
    cid = engine.request_consultation(
        patient_id=sample_patient.patient_id,
        clinical_question="胸痛原因待查"
    )
    report = engine.run_consultation(cid, patient=sample_patient)
    md = report.to_markdown()
    assert "# 虚拟会诊报告" in md
    assert report.patient_name in md
    assert "鉴别诊断" in md


def test_approve_report(engine, sample_patient):
    cid = engine.request_consultation(
        patient_id=sample_patient.patient_id,
        clinical_question="胸痛原因待查"
    )
    engine.run_consultation(cid, patient=sample_patient)
    result = engine.approve_report(cid, "张主任", "signature123")
    assert result is True


def test_knowledge_graph_differential(engine, sample_patient):
    results = engine.get_knowledge_graph_differential(sample_patient)
    assert isinstance(results, list)
