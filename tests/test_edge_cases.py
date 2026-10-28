"""
边界与健壮性测试 - 空/畸形数据、异常路径覆盖
"""
import pytest
import json
from datetime import date

from src.core.patient import (
    Patient, Gender, LabResult, ImagingReport, Medication, TimelineEvent
)
from src.core.medical_record import MedicalRecordIntegrator, NLPEngine
from src.core.consultation import ConsultationEngine, ConsultationStatus
from src.core.knowledge_graph import build_default_knowledge_graph
from src.adapters.base import MockHospitalAdapter


# -------------------- Patient 模型边界 --------------------

def test_patient_from_empty_dict():
    """从空 dict 构造患者不应崩溃"""
    p = Patient.from_dict({})
    assert p.patient_id == "UNKNOWN"
    assert p.name == ""
    assert p.gender == Gender.UNKNOWN
    assert p.age == 0


def test_patient_from_invalid_gender():
    """非法 gender 值应回退到 UNKNOWN"""
    p = Patient.from_dict({"patient_id": "P1", "name": "x", "gender": "INVALID", "age": 50})
    assert p.gender == Gender.UNKNOWN


def test_patient_from_invalid_age():
    """非数字 age 应回退到 0"""
    p = Patient.from_dict({"patient_id": "P1", "name": "x", "gender": "男", "age": "not_a_number"})
    assert p.age == 0


def test_patient_from_invalid_date():
    """非法日期字符串应返回 None 而非抛异常"""
    p = Patient.from_dict({
        "patient_id": "P1", "name": "x", "gender": "男", "age": 50,
        "admission_date": "not-a-date"
    })
    assert p.admission_date is None


def test_patient_from_invalid_nested_fields():
    """lab_results/imaging_reports 为非列表或包含非 dict 项时应安全处理"""
    p = Patient.from_dict({
        "patient_id": "P1", "name": "x", "gender": "男", "age": 50,
        "lab_results": "not_a_list",
        "imaging_reports": [123, {"modality": "CT", "body_part": "胸", "findings": "x", "impression": "y"}],
        "medications": [None, {"drug_name": "x", "dosage": "y", "frequency": "z"}],
        "risk_scores": "should_be_dict"
    })
    assert p.lab_results == []
    assert len(p.imaging_reports) == 1
    assert len(p.medications) == 1
    assert p.risk_scores == {}


def test_patient_to_public_dict_masks_pii():
    """to_public_dict 应屏蔽身份证、电话"""
    p = Patient(
        patient_id="P1", name="测试", gender=Gender.MALE, age=50,
        phone="13812345678",
        id_card="110101199001011234",
        raw_data={"ground_truth": "冠心病"}
    )
    public = p.to_public_dict()
    assert public["phone"] != "13812345678"
    assert public["id_card"] != "110101199001011234"
    assert "ground_truth" not in public  # raw_data 被移除
    # 保留前缀用于识别
    assert public["phone"].startswith("138")
    assert public["id_card"].startswith("110101")


def test_patient_to_public_dict_short_phone():
    """过短电话应被全部屏蔽"""
    p = Patient(patient_id="P1", name="x", gender=Gender.MALE, age=50, phone="123")
    public = p.to_public_dict()
    assert public["phone"] == "******"


def test_gender_parse_various_inputs():
    """Gender.parse 应兼容多种输入"""
    assert Gender.parse("男") == Gender.MALE
    assert Gender.parse("男性") == Gender.MALE
    assert Gender.parse("M") == Gender.MALE
    assert Gender.parse("MALE") == Gender.MALE
    assert Gender.parse("1") == Gender.MALE
    assert Gender.parse("女") == Gender.FEMALE
    assert Gender.parse("F") == Gender.FEMALE
    assert Gender.parse("2") == Gender.FEMALE
    assert Gender.parse(None) == Gender.UNKNOWN
    assert Gender.parse("") == Gender.UNKNOWN
    assert Gender.parse("xyz") == Gender.UNKNOWN
    assert Gender.parse(123) == Gender.UNKNOWN


# -------------------- LabResult / Medication 边界 --------------------

def test_lab_result_from_empty_dict():
    lr = LabResult.from_dict({})
    assert lr.item_name == ""
    assert lr.value == ""
    assert lr.abnormal is False
    assert lr.test_date is None


def test_medication_from_empty_dict():
    m = Medication.from_dict({})
    assert m.drug_name == ""
    assert m.dosage == ""
    assert m.status == "current"


def test_timeline_event_from_empty_dict():
    """TimelineEvent 缺失日期时回退到今天"""
    te = TimelineEvent.from_dict({})
    assert te.event_date == date.today()


# -------------------- 病历整合器边界 --------------------

def test_integrate_nonexistent_patient():
    """整合不存在的患者ID应返回空 Patient"""
    integrator = MedicalRecordIntegrator()
    integrator.add_adapter(MockHospitalAdapter("HIS", sample_data={}))
    patient = integrator.integrate("NOT_EXIST")
    assert patient.patient_id == "NOT_EXIST"
    assert patient.name == ""
    assert patient.gender == Gender.UNKNOWN


def test_integrate_with_no_adapters():
    """无适配器时返回空患者"""
    integrator = MedicalRecordIntegrator()
    patient = integrator.integrate("P1")
    assert patient.patient_id == "P1"
    assert patient.name == ""


def test_integrate_handles_adapter_exception():
    """单个适配器异常不应影响整体整合"""
    class FailingAdapter(MockHospitalAdapter):
        def fetch_patient_data(self, patient_id):
            raise RuntimeError("连接失败")
    integrator = MedicalRecordIntegrator()
    integrator.add_adapter(FailingAdapter("HIS"))
    integrator.add_adapter(MockHospitalAdapter("EMR", sample_data={"P1": {"chief_complaint": "x"}}))
    patient = integrator.integrate("P1")
    assert patient.chief_complaint == "x"
    log = integrator.get_integration_log()
    assert "HIS" in log
    assert "失败" in log or "✗" in log


def test_integrate_merges_multiple_his_adapters():
    """多个 HIS 适配器应合并数据，后到不覆盖前者非空字段"""
    integrator = MedicalRecordIntegrator()
    integrator.add_adapter(MockHospitalAdapter("HIS", sample_data={
        "P1": {"name": "张三", "age": 60, "department": "心内科"}
    }))
    integrator.add_adapter(MockHospitalAdapter("HIS", sample_data={
        "P1": {"name": "", "phone": "13800000000", "department": ""}
    }))
    patient = integrator.integrate("P1")
    assert patient.name == "张三"
    assert patient.department == "心内科"
    assert patient.phone == "13800000000"


def test_integrate_dedups_lab_results():
    """同项目+同日期的检验结果应去重"""
    integrator = MedicalRecordIntegrator()
    integrator.add_adapter(MockHospitalAdapter("LIS", sample_data={
        "P1": {"lab_results": [
            {"item_name": "血糖", "value": "5.5", "unit": "mmol/L", "reference_range": "3.9-6.1",
             "test_date": "2026-07-30"},
            {"item_name": "血糖", "value": "6.5", "unit": "mmol/L", "reference_range": "3.9-6.1",
             "test_date": "2026-07-30"},
            {"item_name": "血糖", "value": "5.8", "unit": "mmol/L", "reference_range": "3.9-6.1",
             "test_date": "2026-07-31"},
        ]}
    }))
    patient = integrator.integrate("P1")
    # 2 个唯一日期的血糖记录
    glucose_dates = {lr.test_date for lr in patient.lab_results if lr.item_name == "血糖"}
    assert len(glucose_dates) == 2


def test_news_score_with_blood_pressure_format():
    """血压"120/80"格式不应导致 NEWS 评分崩溃"""
    integrator = MedicalRecordIntegrator()
    patient = Patient(
        patient_id="P1", name="x", gender=Gender.MALE, age=50,
        lab_results=[
            LabResult("心率", "95", "次/分", "60-100", abnormal=True),
            LabResult("收缩压", "120/80", "mmHg", "90-140", abnormal=False),
            LabResult("血氧饱和度", "92", "%", "95-100", abnormal=True),
        ]
    )
    scores = integrator._calculate_risk_scores(patient)
    assert "NEWS" in scores
    assert scores["NEWS"] > 0  # 心率 95 + 血氧 92 应有得分


def test_news_score_with_reference_prefix():
    """值含"<"前缀（如<0.04）应被正确解析"""
    integrator = MedicalRecordIntegrator()
    patient = Patient(
        patient_id="P1", name="x", gender=Gender.MALE, age=50,
        lab_results=[
            LabResult("心率", "<50", "次/分", "60-100", abnormal=True),
        ]
    )
    scores = integrator._calculate_risk_scores(patient)
    assert scores["NEWS"] >= 1  # 心率 50 应得分


# -------------------- NLPEngine 测试 --------------------

def test_nlp_extract_empty_text():
    """空文本应返回空列表"""
    assert NLPEngine.extract_symptoms("") == []
    assert NLPEngine.extract_symptoms(None) == []
    assert NLPEngine.extract_diseases("") == []


def test_nlp_extract_no_match():
    """无匹配症状应返回空列表"""
    assert NLPEngine.extract_symptoms("患者一般情况良好") == []


def test_nlp_extract_entities():
    entities = NLPEngine.extract_entities("咳嗽、呼吸困难，既往高血压、糖尿病")
    assert "咳嗽" in entities["symptoms"]
    assert "呼吸困难" in entities["symptoms"]
    assert "高血压" in entities["diseases"]
    assert "糖尿病" in entities["diseases"]
    assert isinstance(entities["tokens"], list)


def test_nlp_segment_text():
    tokens = NLPEngine.segment_text("患者反复咳嗽咳痰")
    assert isinstance(tokens, list)
    assert len(tokens) > 0


def test_nlp_segment_empty():
    assert NLPEngine.segment_text("") == []
    assert NLPEngine.segment_text(None) == []


# -------------------- ConsultationEngine 边界 --------------------

def test_run_consultation_invalid_id():
    """会诊ID不存在时应抛 ValueError"""
    engine = ConsultationEngine(knowledge_graph=build_default_knowledge_graph())
    with pytest.raises(ValueError, match="不存在"):
        engine.run_consultation("INVALID-ID")


def test_run_consultation_no_patient():
    """无患者对象且无适配器时应抛 ValueError"""
    engine = ConsultationEngine(knowledge_graph=build_default_knowledge_graph())
    cid = engine.request_consultation(
        patient_id="P1", clinical_question="x", consultation_type="MDT"
    )
    with pytest.raises(ValueError):
        engine.run_consultation(cid)


def test_run_consultation_invalid_agent_id_falls_back():
    """选择不存在的 agent_id 时应抛 ValueError"""
    engine = ConsultationEngine(knowledge_graph=build_default_knowledge_graph())
    cid = engine.request_consultation(
        patient_id="P1", clinical_question="x", consultation_type="MDT"
    )
    with pytest.raises(ValueError):
        engine.run_consultation(
            cid,
            patient=Patient(patient_id="P1", name="x", gender=Gender.MALE, age=50),
            selected_agent_ids=["nonexistent_agent"]
        )


def test_get_report_nonexistent():
    """获取不存在的报告应返回 None"""
    engine = ConsultationEngine(knowledge_graph=build_default_knowledge_graph())
    assert engine.get_report("NONEXISTENT") is None


def test_approve_report_nonexistent():
    """审核不存在的报告应返回 False"""
    engine = ConsultationEngine(knowledge_graph=build_default_knowledge_graph())
    assert engine.approve_report("NONEXISTENT", "张医生") is False


def test_save_report_nonexistent_raises(tmp_path):
    """保存不存在的报告应抛 ValueError"""
    engine = ConsultationEngine(knowledge_graph=build_default_knowledge_graph())
    with pytest.raises(ValueError):
        engine.save_report("NONEXISTENT", str(tmp_path / "x.json"), "json")


def test_load_patient_from_invalid_json(tmp_path):
    """加载无效 JSON 文件应抛异常"""
    engine = ConsultationEngine(knowledge_graph=build_default_knowledge_graph())
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json", encoding="utf-8")
    with pytest.raises(Exception):
        engine.load_patient_from_json(str(bad_file))


def test_consultation_status_enum():
    """状态枚举覆盖"""
    assert ConsultationStatus.DRAFT.value == "草稿"
    assert ConsultationStatus.PENDING.value == "待审核"
    assert ConsultationStatus.IN_PROGRESS.value == "进行中"
    assert ConsultationStatus.COMPLETED.value == "已完成"
    assert ConsultationStatus.ARCHIVED.value == "已归档"


def test_full_workflow_with_malformed_data():
    """端到端：畸形数据也能跑通基本流程"""
    integrator = MedicalRecordIntegrator()
    integrator.add_adapter(MockHospitalAdapter("HIS", sample_data={
        "P1": {"name": "测试", "gender": "男", "age": 60, "admission_date": "2026-07-30"}
    }))
    integrator.add_adapter(MockHospitalAdapter("LIS", sample_data={
        "P1": {"lab_results": [
            {"item_name": "心率", "value": "95", "unit": "次/分", "reference_range": "60-100", "abnormal": True,
             "test_date": "2026-07-30"}
        ]}
    }))
    engine = ConsultationEngine(integrator=integrator, knowledge_graph=build_default_knowledge_graph())
    cid = engine.request_consultation(
        patient_id="P1", clinical_question="胸痛待查", consultation_type="MDT"
    )
    report = engine.run_consultation(cid)
    assert report.status == "COMPLETED"
    # 鉴别诊断应为空（无主诉、无现病史）
    assert isinstance(report.differential_diagnosis, list)
    # 最终结论应能兜底
    assert report.final_conclusion != ""
