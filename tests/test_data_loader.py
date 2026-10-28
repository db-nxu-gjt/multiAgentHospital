"""
数据加载器测试
"""
import pytest
from pathlib import Path

from src.utils.data_loader import (
    load_heart_disease_patients, load_diabetes_patients,
    save_patients_to_json, load_patients_from_json
)


@pytest.fixture
def project_root():
    return Path(__file__).parent.parent


def test_load_heart_disease(project_root):
    csv_path = project_root / "data" / "raw" / "heart_disease_cleveland.csv"
    if not csv_path.exists():
        pytest.skip("心脏病数据集未下载")

    patients = load_heart_disease_patients(str(csv_path), limit=10)
    assert len(patients) == 10
    assert patients[0].age > 0
    assert len(patients[0].lab_results) > 0
    assert "ground_truth" in patients[0].raw_data


def test_load_diabetes(project_root):
    csv_path = project_root / "data" / "raw" / "pima_diabetes.csv"
    if not csv_path.exists():
        pytest.skip("糖尿病数据集未下载")

    patients = load_diabetes_patients(str(csv_path), limit=10)
    assert len(patients) == 10
    assert patients[0].age > 0
    assert "ground_truth" in patients[0].raw_data


def test_patient_json_roundtrip(project_root, tmp_path):
    csv_path = project_root / "data" / "raw" / "heart_disease_cleveland.csv"
    if not csv_path.exists():
        pytest.skip("心脏病数据集未下载")

    patients = load_heart_disease_patients(str(csv_path), limit=3)
    output_path = tmp_path / "test_patients.json"

    save_patients_to_json(patients, str(output_path))
    loaded = load_patients_from_json(str(output_path))

    assert len(loaded) == 3
    assert loaded[0].patient_id == patients[0].patient_id
    assert loaded[0].name == patients[0].name
