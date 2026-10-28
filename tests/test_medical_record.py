"""
病历整合引擎测试
"""
import pytest
from datetime import date

from src.core.medical_record import MedicalRecordIntegrator, NLPEngine
from src.core.patient import Patient, Gender, LabResult
from src.adapters.base import MockHospitalAdapter


@pytest.fixture
def integrator_with_data():
    integrator = MedicalRecordIntegrator()

    his_data = {
        "P001": {
            "name": "张三",
            "gender": "男",
            "age": 65,
            "department": "心内科",
            "attending_doctor": "李医生",
            "admission_date": "2026-07-28"
        }
    }
    emr_data = {
        "P001": {
            "chief_complaint": "胸痛2小时",
            "present_illness": "突发胸骨后压榨性疼痛，伴大汗。",
            "past_history": "高血压10年",
            "physical_exam": "BP 150/90mmHg"
        }
    }
    lis_data = {
        "P001": {
            "lab_results": [
                {
                    "item_name": "肌钙蛋白",
                    "value": "2.5",
                    "unit": "ng/mL",
                    "reference_range": "<0.04",
                    "abnormal": True,
                    "test_date": "2026-07-28"
                }
            ]
        }
    }
    pacs_data = {
        "P001": {
            "imaging_reports": [
                {
                    "modality": "X线",
                    "body_part": "胸部",
                    "findings": "心影增大",
                    "impression": "心影增大，肺淤血",
                    "report_date": "2026-07-28"
                }
            ]
        }
    }

    integrator.add_adapter(MockHospitalAdapter("HIS", sample_data=his_data))
    integrator.add_adapter(MockHospitalAdapter("EMR", sample_data=emr_data))
    integrator.add_adapter(MockHospitalAdapter("LIS", sample_data=lis_data))
    integrator.add_adapter(MockHospitalAdapter("PACS", sample_data=pacs_data))

    return integrator


def test_integrate_patient(integrator_with_data):
    patient = integrator_with_data.integrate("P001")
    assert patient.name == "张三"
    assert patient.age == 65
    assert patient.gender.value == "男"
    assert len(patient.lab_results) == 1
    assert patient.lab_results[0].abnormal
    assert len(patient.imaging_reports) == 1
    assert len(patient.timeline) >= 2


def test_gender_parsing():
    integrator = MedicalRecordIntegrator()
    assert integrator._parse_gender("男") == Gender.MALE
    assert integrator._parse_gender("女") == Gender.FEMALE
    assert integrator._parse_gender("unknown") == Gender.UNKNOWN


def test_date_parsing():
    integrator = MedicalRecordIntegrator()
    assert integrator._parse_date("2026-07-28") == date(2026, 7, 28)
    assert integrator._parse_date("2026/07/28") == date(2026, 7, 28)
    assert integrator._parse_date(None) is None


def test_nlp_extract_symptoms():
    text = "患者反复咳嗽、咳痰，伴呼吸困难1周。"
    symptoms = NLPEngine.extract_symptoms(text)
    assert "咳嗽" in symptoms
    assert "咳痰" in symptoms
    assert "呼吸困难" in symptoms


def test_nlp_extract_diseases():
    text = "患者有高血压、糖尿病病史多年。"
    diseases = NLPEngine.extract_diseases(text)
    assert "高血压" in diseases
    assert "糖尿病" in diseases


def test_news_score_calculation():
    integrator = MedicalRecordIntegrator()
    patient = Patient(
        patient_id="P002",
        name="李四",
        gender=Gender.MALE,
        age=70,
        lab_results=[
            LabResult("心率", "130", "次/分", "60-100", abnormal=True),
            LabResult("收缩压", "85", "mmHg", "90-140", abnormal=True),
            LabResult("血氧饱和度", "90", "%", "95-100", abnormal=True)
        ]
    )
    scores = integrator._calculate_risk_scores(patient)
    assert "NEWS" in scores
    assert scores["NEWS"] > 0
