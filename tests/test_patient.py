"""
患者数据模型测试
"""
import json
import pytest
from datetime import date

from src.core.patient import (
    Patient, Gender, LabResult, ImagingReport,
    Medication, TimelineEvent
)


@pytest.fixture
def sample_patient():
    return Patient(
        patient_id="P001",
        name="测试患者",
        gender=Gender.MALE,
        age=55,
        department="呼吸内科",
        chief_complaint="咳嗽、咳痰1周",
        present_illness="1周前受凉后出现咳嗽，咳白色黏痰。",
        lab_results=[
            LabResult("白细胞", "11.2", "×10^9/L", "4.0-10.0", abnormal=True,
                     test_date=date(2026, 7, 31)),
            LabResult("血红蛋白", "130", "g/L", "130-175", abnormal=False,
                     test_date=date(2026, 7, 31))
        ],
        imaging_reports=[
            ImagingReport("CT", "胸部", "双肺纹理增粗", "支气管炎可能",
                         report_date=date(2026, 7, 30))
        ]
    )


def test_patient_creation(sample_patient):
    assert sample_patient.patient_id == "P001"
    assert sample_patient.name == "测试患者"
    assert sample_patient.gender == Gender.MALE
    assert sample_patient.age == 55


def test_patient_summary(sample_patient):
    summary = sample_patient.get_summary()
    assert "测试患者" in summary
    assert "咳嗽、咳痰1周" in summary
    assert "异常检验指标：1项" in summary


def test_patient_serialization(sample_patient):
    json_str = sample_patient.to_json()
    restored = Patient.from_json(json_str)
    assert restored.patient_id == sample_patient.patient_id
    assert restored.name == sample_patient.name
    assert len(restored.lab_results) == len(sample_patient.lab_results)


def test_lab_result_abnormal_detection():
    normal = LabResult("血糖", "5.0", "mmol/L", "3.9-6.1", abnormal=False)
    abnormal = LabResult("血糖", "8.0", "mmol/L", "3.9-6.1", abnormal=True)
    assert not normal.abnormal
    assert abnormal.abnormal


def test_get_key_findings(sample_patient):
    findings = sample_patient.get_key_findings()
    assert len(findings) > 0
    assert any("主诉" in f for f in findings)
    assert any("异常检验" in f for f in findings)
