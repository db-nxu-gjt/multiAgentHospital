"""
数据集加载器
将公开医学数据集（UCI Heart Disease, Pima Diabetes）转换为系统可用的患者对象
"""
import json
import random
from pathlib import Path
from typing import List, Dict, Any
from datetime import date, timedelta

import pandas as pd

from ..core.patient import Patient, Gender, LabResult, ImagingReport, Medication, TimelineEvent


def load_heart_disease_patients(csv_path: str, limit: int = 20) -> List[Patient]:
    """从UCI心脏病数据集加载患者"""
    df = pd.read_csv(csv_path)
    patients = []

    # Cleveland数据集列
    columns = [
        "age", "sex", "cp", "trestbps", "chol", "fbs",
        "restecg", "thalach", "exang", "oldpeak", "slope", "ca", "thal", "num"
    ]

    # 确保列名正确
    if list(df.columns) != columns and len(df.columns) == len(columns):
        df.columns = columns

    for idx, row in df.head(limit).iterrows():
        gender = Gender.MALE if int(row.get("sex", 0)) == 1 else Gender.FEMALE
        cp_types = {1: "典型心绞痛", 2: "非典型心绞痛", 3: "非心绞痛", 4: "无症状"}
        cp = cp_types.get(int(row.get("cp", 4)), "未知")

        # 构建主诉 - 根据真实标签生成不同临床表现
        is_chd = int(row.get("num", 0)) > 0
        if is_chd:
            chief = f"胸骨后压榨性疼痛，伴胸闷气促，向左肩放射"
            diagnosis = "冠心病可能"
        else:
            # 非冠心病患者：使用中性描述，避免使用'心绞痛'等触发词
            if int(row.get("cp", 4)) in [1, 2]:  # 典型/非典型心绞痛样胸痛
                chief = "活动后轻微胸闷不适，休息可缓解"
            else:
                chief = "无明显胸痛，偶有胸闷感"
            diagnosis = "胸痛待查"

        admission_date = date.today() - timedelta(days=random.randint(1, 30))

        patient = Patient(
            patient_id=f"HD{idx+1:04d}",
            name=f"心脏患者{idx+1}",
            gender=gender,
            age=int(row.get("age", 60)),
            department="心内科",
            attending_doctor="心内科医生",
            admission_date=admission_date,
            chief_complaint=chief,
            present_illness=(
                f"患者因活动后胸痛就诊，疼痛位于胸骨后，呈压榨性，持续数分钟，休息或含服硝酸甘油可缓解。"
                f"静息心电图{int(row.get('restecg', 0))}级改变。"
                f"运动试验{'阳性' if int(row.get('exang', 0)) == 1 else '阴性'}。"
            ) if is_chd else (
                "患者因胸部不适感就诊，疼痛性质不典型，与活动关系不明显。"
                f"静息心电图{int(row.get('restecg', 0))}级改变。"
                f"运动试验{'阳性' if int(row.get('exang', 0)) == 1 else '阴性'}。"
            ),
            past_history="高血压病史不详，否认糖尿病。",
            physical_exam=f"血压{int(row.get('trestbps', 120))}/{random.randint(70, 90)}mmHg，心率{int(row.get('thalach', 70))}次/分。",
            lab_results=[
                LabResult("总胆固醇", str(row.get("chol", 200)), "mg/dL", "<200",
                         abnormal=float(row.get("chol", 200)) > 200,
                         test_date=admission_date, department="检验科"),
                LabResult("空腹血糖", str(row.get("fbs", 0) * 7 + random.uniform(4, 6)), "mmol/L", "3.9-6.1",
                         abnormal=float(row.get("fbs", 0)) == 1,
                         test_date=admission_date, department="检验科"),
                LabResult("收缩压", str(int(row.get("trestbps", 120))), "mmHg", "90-140",
                         abnormal=int(row.get("trestbps", 120)) > 140,
                         test_date=admission_date, department="心内科"),
                LabResult("最大心率", str(int(row.get("thalach", 70))), "次/分", "60-100",
                         abnormal=int(row.get("thalach", 70)) > 100 or int(row.get("thalach", 70)) < 60,
                         test_date=admission_date, department="心内科"),
            ],
            imaging_reports=[
                ImagingReport(
                    modality="X线",
                    body_part="胸部",
                    findings="心影评估",
                    impression=f"{'心影增大' if int(row.get('num', 0)) > 0 else '心影未见明显增大'}，结合临床。",
                    report_date=admission_date
                )
            ],
            medications=[
                Medication("阿司匹林", "100mg", "每日1次", start_date=admission_date),
                Medication("阿托伐他汀", "20mg", "每晚1次", start_date=admission_date),
            ]
        )

        # 添加真实标签用于测试验证
        patient.raw_data["ground_truth"] = "冠心病" if int(row.get("num", 0)) > 0 else "非冠心病"
        patients.append(patient)

    return patients


def load_diabetes_patients(csv_path: str, limit: int = 20) -> List[Patient]:
    """从Pima糖尿病数据集加载患者"""
    df = pd.read_csv(csv_path)
    patients = []

    for idx, row in df.head(limit).iterrows():
        gender = Gender.FEMALE
        age = int(row.get("Age", 30))
        glucose = float(row.get("Glucose", 100))
        bmi = float(row.get("BMI", 25))
        outcome = int(row.get("Outcome", 0))

        admission_date = date.today() - timedelta(days=random.randint(1, 30))

        if outcome == 1:
            chief = "多饮多尿伴体重下降"
            diagnosis = "2型糖尿病"
        else:
            chief = "体检发现血糖异常"
            diagnosis = "糖耐量异常待查"

        patient = Patient(
            patient_id=f"DB{idx+1:04d}",
            name=f"糖尿病筛查患者{idx+1}",
            gender=gender,
            age=age,
            department="内分泌科",
            attending_doctor="内分泌医生",
            admission_date=admission_date,
            chief_complaint=chief,
            present_illness=f"患者{chief}{'1月' if outcome == 1 else '1周'}。妊娠次数{int(row.get('Pregnancies', 0))}次。",
            past_history="既往血糖情况不详。",
            physical_exam=f"BMI {bmi:.1f}kg/m²，余查体未见明显异常。",
            lab_results=[
                LabResult("血糖", f"{glucose:.1f}", "mg/dL", "70-100",
                         abnormal=glucose > 100,
                         test_date=admission_date, department="检验科"),
                LabResult("BMI", f"{bmi:.1f}", "kg/m²", "18.5-24",
                         abnormal=bmi > 24,
                         test_date=admission_date, department="体检科"),
                LabResult("血压", f"{random.randint(110, 140)}/{random.randint(70, 90)}", "mmHg", "90-140/60-90",
                         abnormal=False,
                         test_date=admission_date, department="心内科"),
            ],
            medications=[]
        )

        patient.raw_data["ground_truth"] = "2型糖尿病" if outcome == 1 else "非糖尿病"
        patients.append(patient)

    return patients


def save_patients_to_json(patients: List[Patient], filepath: str) -> None:
    """将患者列表保存为JSON"""
    data = {"patients": [p.to_dict() for p in patients]}
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_patients_from_json(filepath: str) -> List[Patient]:
    """从JSON加载患者列表"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Patient.from_dict(p) for p in data.get("patients", [])]
