"""
下载公开医学数据集用于系统测试
"""
import os
import urllib.request
import zipfile
import pandas as pd
from pathlib import Path


def download_uci_heart_disease(raw_dir: str) -> str:
    """下载UCI心脏病数据集"""
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.cleveland.data"
    filepath = Path(raw_dir) / "heart_disease_cleveland.csv"

    print(f"正在下载UCI心脏病数据集...")
    urllib.request.urlretrieve(url, filepath)

    # 添加列名
    columns = [
        "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
        "thalach", "exang", "oldpeak", "slope", "ca", "thal", "num"
    ]
    df = pd.read_csv(filepath, header=None, names=columns, na_values="?")
    df.to_csv(filepath, index=False)
    print(f"✓ 心脏病数据集已保存: {filepath}")
    return str(filepath)


def download_uci_diabetes(raw_dir: str) -> str:
    """下载UCI糖尿病数据集，如果网络失败则使用sklearn内置数据生成"""
    filepath = Path(raw_dir) / "pima_diabetes.csv"

    urls = [
        "https://raw.githubusercontent.com/jbrownlee/Datasets/master/pima-indians-diabetes.data.csv",
        "https://archive.ics.uci.edu/ml/machine-learning-databases/diabetes/diabetes-data.tar.Z"
    ]

    columns = [
        "Pregnancies", "Glucose", "BloodPressure", "SkinThickness",
        "Insulin", "BMI", "DiabetesPedigreeFunction", "Age", "Outcome"
    ]

    for url in urls:
        try:
            print(f"正在尝试下载糖尿病数据集: {url}...")
            urllib.request.urlretrieve(url, filepath)
            df = pd.read_csv(filepath, header=None, names=columns)
            df.to_csv(filepath, index=False)
            print(f"✓ 糖尿病数据集已保存: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"✗ 从 {url} 下载失败: {e}")
            continue

    # 如果下载失败，使用sklearn生成合成数据
    print("网络下载失败，使用sklearn生成糖尿病合成测试数据...")
    from sklearn.datasets import load_diabetes
    diabetes = load_diabetes()
    df = pd.DataFrame(diabetes.data, columns=diabetes.feature_names)
    df["Outcome"] = (diabetes.target > diabetes.target.mean()).astype(int)
    # 重命名列为与Pima一致的格式
    df = df.rename(columns={
        "age": "Age",
        "bmi": "BMI"
    })
    # 确保有所需列
    for col in columns:
        if col not in df.columns:
            df[col] = 0
    df = df[columns]
    df.to_csv(filepath, index=False)
    print(f"✓ 糖尿病合成数据集已保存: {filepath}")
    return str(filepath)


def download_medical_qa_sample(raw_dir: str) -> str:
    """下载医学QA样本数据"""
    # 使用HuggingFace datasets的medical_dialog或medical_qa需要额外安装
    # 这里创建一个简单的医学问答样本
    filepath = Path(raw_dir) / "medical_qa_sample.csv"
    data = {
        "question": [
            "慢性阻塞性肺疾病的典型症状是什么？",
            "心力衰竭患者常见的临床表现有哪些？",
            "2型糖尿病的诊断标准是什么？",
            "急性心肌梗死的典型胸痛特点是什么？",
            "高血压患者日常生活中应注意什么？"
        ],
        "answer": [
            "慢性咳嗽、咳痰、气短或呼吸困难、喘息和胸闷。",
            "呼吸困难、乏力、水肿（下肢水肿）、咳嗽、食欲减退。",
            "空腹血糖≥7.0mmol/L，或餐后2小时血糖≥11.1mmol/L，或HbA1c≥6.5%。",
            "胸骨后压榨性疼痛，可向左肩、左上肢放射，持续不缓解，伴大汗、恶心。",
            "低盐饮食、规律运动、控制体重、戒烟限酒、规律监测血压、按时服药。"
        ]
    }
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"✓ 医学QA样本已保存: {filepath}")
    return str(filepath)


def main():
    project_root = Path(__file__).parent.parent
    raw_dir = project_root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("开始下载医学测试数据集")
    print("=" * 50)

    try:
        download_uci_heart_disease(str(raw_dir))
    except Exception as e:
        print(f"✗ 心脏病数据集下载失败: {e}")

    try:
        download_uci_diabetes(str(raw_dir))
    except Exception as e:
        print(f"✗ 糖尿病数据集下载失败: {e}")

    try:
        download_medical_qa_sample(str(raw_dir))
    except Exception as e:
        print(f"✗ 医学QA样本生成失败: {e}")

    print("=" * 50)
    print("数据集下载完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
