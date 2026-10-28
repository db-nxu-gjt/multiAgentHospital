"""
医院虚拟会诊系统 - 命令行演示
无需启动GUI即可体验完整会诊流程
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.consultation import ConsultationEngine
from src.core.medical_record import MedicalRecordIntegrator
from src.core.knowledge_graph import build_default_knowledge_graph
from src.core.patient import Patient
from src.adapters.base import MockHospitalAdapter
from src.utils.data_loader import load_heart_disease_patients, load_diabetes_patients


def print_section(title):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def demo_with_sample_patient():
    """使用内置示例患者演示"""
    print_section("演示1：内置示例病例全流程会诊")

    # 加载示例病例
    sample_path = project_root / "data" / "sample_cases.json"
    if not sample_path.exists():
        print("示例病例文件不存在")
        return

    import json
    with open(sample_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    patient_data = cases["patients"][0]
    pid = patient_data["patient_id"]

    # 设置适配器
    integrator = MedicalRecordIntegrator()
    integrator.add_adapter(MockHospitalAdapter("HIS", sample_data={pid: {
        "name": patient_data["name"],
        "gender": patient_data["gender"],
        "age": patient_data["age"],
        "department": patient_data.get("department", ""),
        "attending_doctor": patient_data.get("attending_doctor", ""),
    }}))
    integrator.add_adapter(MockHospitalAdapter("EMR", sample_data={pid: {
        "chief_complaint": patient_data.get("chief_complaint", ""),
        "present_illness": patient_data.get("present_illness", ""),
        "past_history": patient_data.get("past_history", ""),
    }}))
    integrator.add_adapter(MockHospitalAdapter("LIS", sample_data={pid: {
        "lab_results": patient_data.get("lab_results", [])
    }}))
    integrator.add_adapter(MockHospitalAdapter("PACS", sample_data={pid: {
        "imaging_reports": patient_data.get("imaging_reports", [])
    }}))

    # 整合病历
    patient = integrator.integrate(pid)
    print(f"\n患者：{patient.name}，{patient.gender_str}，{patient.age}岁")
    print(f"主诉：{patient.chief_complaint}")
    print(f"异常检验：{len([l for l in patient.lab_results if l.abnormal])}项")

    # 执行会诊
    kg = build_default_knowledge_graph()
    engine = ConsultationEngine(integrator=integrator, knowledge_graph=kg)
    cid = engine.request_consultation(
        patient_id=pid,
        clinical_question="反复咳嗽咳痰伴呼吸困难原因待查",
        consultation_type="MDT"
    )

    print(f"\n发起会诊：{cid}")
    report = engine.run_consultation(cid, patient=patient)

    print(f"\n会诊状态：{report.status}")
    print(f"\n鉴别诊断：")
    for i, diag in enumerate(report.differential_diagnosis[:5], 1):
        print(f"  {i}. {diag['disease']} "
              f"(置信度：{diag['confidence']:.1%}, "
              f"证据等级：{diag['evidence_level']})")

    print(f"\n最终结论：\n  {report.final_conclusion}")

    # 保存报告
    output_path = project_root / "data" / "processed" / f"{cid}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report.to_markdown())
    print(f"\n报告已保存：{output_path}")


def demo_with_real_dataset():
    """使用真实心脏病数据集演示"""
    print_section("演示2：真实UCI心脏病数据集会诊")

    csv_path = project_root / "data" / "raw" / "heart_disease_cleveland.csv"
    if not csv_path.exists():
        print("心脏病数据集不存在，请先运行 scripts/download_datasets.py")
        return

    patients = load_heart_disease_patients(str(csv_path), limit=3)
    print(f"\n加载了 {len(patients)} 例心脏病患者")

    kg = build_default_knowledge_graph()
    engine = ConsultationEngine(knowledge_graph=kg)

    for patient in patients[:3]:
        cid = engine.request_consultation(
            patient_id=patient.patient_id,
            clinical_question="胸痛原因待查",
            consultation_type="MDT"
        )
        report = engine.run_consultation(cid, patient=patient)

        print(f"\n患者：{patient.name}，{patient.age}岁")
        print(f"  真实标签：{patient.raw_data.get('ground_truth', '未知')}")
        print(f"  AI首选诊断：{report.differential_diagnosis[0]['disease']} "
              f"(置信度：{report.differential_diagnosis[0]['confidence']:.1%})")


def demo_knowledge_graph():
    """演示医学知识图谱"""
    print_section("演示3：医学知识图谱症状-疾病关联")

    kg = build_default_knowledge_graph()
    symptoms = ["咳嗽", "呼吸困难"]
    results = kg.find_diseases_by_symptoms(symptoms, top_k=5)

    print(f"\n症状：{', '.join(symptoms)}")
    print("\n可能的疾病：")
    for result in results:
        print(f"  - {result['disease']} "
              f"(置信度：{result['confidence']:.1%})")


def main():
    print("医院虚拟会诊系统 (VCS) - 命令行演示")
    print("=" * 60)

    demo_knowledge_graph()
    demo_with_sample_patient()
    demo_with_real_dataset()

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
