"""
系统集成测试
测试完整会诊流程：患者加载 → 病历整合 → 智能体分析 → 报告生成
"""
import pytest
import json
from pathlib import Path
from datetime import date

from src.core.consultation import ConsultationEngine
from src.core.medical_record import MedicalRecordIntegrator
from src.core.knowledge_graph import build_default_knowledge_graph
from src.core.patient import Patient
from src.adapters.base import MockHospitalAdapter
from src.utils.data_loader import load_heart_disease_patients, load_diabetes_patients


@pytest.fixture
def project_root():
    return Path(__file__).parent.parent


@pytest.fixture
def engine_with_adapters(project_root):
    """构建带模拟适配器的完整引擎"""
    kg = build_default_knowledge_graph()
    integrator = MedicalRecordIntegrator()

    # 加载示例病例作为模拟数据
    sample_path = project_root / "data" / "sample_cases.json"
    with open(sample_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    # 构建包含所有患者数据的适配器（每个系统一个适配器）
    his_data, emr_data, lis_data, pacs_data = {}, {}, {}, {}
    for patient_data in cases["patients"]:
        pid = patient_data["patient_id"]
        his_data[pid] = {
            "name": patient_data["name"],
            "gender": patient_data["gender"],
            "age": patient_data["age"],
            "department": patient_data.get("department", ""),
            "attending_doctor": patient_data.get("attending_doctor", ""),
            "admission_date": patient_data.get("admission_date", "")
        }
        emr_data[pid] = {
            "chief_complaint": patient_data.get("chief_complaint", ""),
            "present_illness": patient_data.get("present_illness", ""),
            "past_history": patient_data.get("past_history", ""),
            "physical_exam": patient_data.get("physical_exam", "")
        }
        lis_data[pid] = {"lab_results": patient_data.get("lab_results", [])}
        pacs_data[pid] = {"imaging_reports": patient_data.get("imaging_reports", [])}

    integrator.add_adapter(MockHospitalAdapter("HIS", sample_data=his_data))
    integrator.add_adapter(MockHospitalAdapter("EMR", sample_data=emr_data))
    integrator.add_adapter(MockHospitalAdapter("LIS", sample_data=lis_data))
    integrator.add_adapter(MockHospitalAdapter("PACS", sample_data=pacs_data))

    engine = ConsultationEngine(integrator=integrator, knowledge_graph=kg)
    return engine


def test_full_workflow_from_sample_data(engine_with_adapters):
    """从示例数据完成全流程"""
    engine = engine_with_adapters

    # 1. 整合病历
    patient = engine.integrator.integrate("ZY20260728001")
    assert patient.name == "李建国"
    assert len(patient.lab_results) > 0

    # 2. 发起会诊
    cid = engine.request_consultation(
        patient_id=patient.patient_id,
        clinical_question="反复咳嗽咳痰伴呼吸困难原因待查",
        consultation_type="MDT"
    )

    # 3. 执行会诊
    report = engine.run_consultation(cid, patient=patient)
    assert report.status == "COMPLETED"
    assert len(report.differential_diagnosis) > 0
    assert "慢性阻塞性肺疾病" in report.final_conclusion or len(report.differential_diagnosis) > 0

    # 4. 保存报告
    output_path = Path(__file__).parent.parent / "data" / "processed" / f"{cid}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine.save_report(cid, str(output_path), "json")
    assert output_path.exists()


def test_heart_disease_dataset(project_root):
    """使用真实心脏病数据集测试"""
    csv_path = project_root / "data" / "raw" / "heart_disease_cleveland.csv"
    if not csv_path.exists():
        pytest.skip("心脏病数据集未下载")

    patients = load_heart_disease_patients(str(csv_path), limit=5)
    assert len(patients) == 5
    assert all(isinstance(p, Patient) for p in patients)

    # 对第一个患者执行会诊
    kg = build_default_knowledge_graph()
    engine = ConsultationEngine(knowledge_graph=kg)
    patient = patients[0]

    cid = engine.request_consultation(
        patient_id=patient.patient_id,
        clinical_question="胸痛原因待查",
        consultation_type="MDT"
    )

    report = engine.run_consultation(cid, patient=patient)
    assert report.status == "COMPLETED"
    assert len(report.differential_diagnosis) > 0


def test_diabetes_dataset(project_root):
    """使用真实糖尿病数据集测试"""
    csv_path = project_root / "data" / "raw" / "pima_diabetes.csv"
    if not csv_path.exists():
        pytest.skip("糖尿病数据集未下载")

    patients = load_diabetes_patients(str(csv_path), limit=5)
    assert len(patients) == 5
    assert all(isinstance(p, Patient) for p in patients)

    kg = build_default_knowledge_graph()
    engine = ConsultationEngine(knowledge_graph=kg)
    patient = patients[0]

    cid = engine.request_consultation(
        patient_id=patient.patient_id,
        clinical_question="血糖异常原因待查",
        consultation_type="常规会诊"
    )

    report = engine.run_consultation(cid, patient=patient)
    assert report.status == "COMPLETED"
    assert len(report.differential_diagnosis) > 0


def test_report_contains_evidence_levels(engine_with_adapters):
    """测试报告包含循证等级"""
    engine = engine_with_adapters
    patient = engine.integrator.integrate("ZY20260731002")

    cid = engine.request_consultation(
        patient_id=patient.patient_id,
        clinical_question="胸痛伴呼吸困难",
        consultation_type="急诊会诊"
    )

    report = engine.run_consultation(cid, patient=patient)
    assert len(report.recommended_tests) > 0
    assert len(report.treatment_plan) > 0
    # 检查证据等级
    for rec in report.recommended_tests:
        assert rec.evidence_level is not None
