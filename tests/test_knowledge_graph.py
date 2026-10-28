"""
医学知识图谱测试
"""
import pytest
import tempfile
import json

from src.core.knowledge_graph import (
    MedicalKnowledgeGraph, MedicalEntity, MedicalRelation,
    build_default_knowledge_graph
)


@pytest.fixture
def kg():
    return build_default_knowledge_graph()


def test_default_kg_built(kg):
    """默认知识图谱应包含疾病、症状、检查、药物实体"""
    assert len(kg.entities) > 0
    diseases = kg.get_entities_by_type("disease")
    symptoms = kg.get_entities_by_type("symptom")
    tests = kg.get_entities_by_type("test")
    drugs = kg.get_entities_by_type("drug")
    assert len(diseases) >= 5
    assert len(symptoms) >= 8
    assert len(tests) >= 5
    assert len(drugs) >= 5
    assert len(kg.relations) > 0


def test_find_diseases_by_symptoms_copd(kg):
    """咳嗽+咳痰+呼吸困难应能匹配到 COPD/肺炎等"""
    results = kg.find_diseases_by_symptoms(["咳嗽", "咳痰", "呼吸困难"], top_k=5)
    assert len(results) > 0
    diseases = [r["disease"] for r in results]
    # 至少匹配到一个呼吸系统疾病
    assert any("肺" in d or "阻塞性" in d for d in diseases)


def test_find_diseases_by_symptoms_diabetes(kg):
    """多尿+多饮应能匹配到糖尿病"""
    results = kg.find_diseases_by_symptoms(["多尿"], top_k=5)
    assert len(results) > 0
    assert any("糖尿病" in r["disease"] for r in results)


def test_find_diseases_by_empty_symptoms(kg):
    """空症状列表应返回空结果，不报错"""
    results = kg.find_diseases_by_symptoms([], top_k=5)
    assert results == []


def test_find_diseases_by_unknown_symptom(kg):
    """未在图谱中的症状应返回空结果"""
    results = kg.find_diseases_by_symptoms(["XYZ不存在的症状"], top_k=5)
    assert results == []


def test_find_related_symptoms(kg):
    """查询 COPD 的典型症状"""
    symptoms = kg.find_related_symptoms("慢性阻塞性肺疾病")
    assert len(symptoms) > 0
    assert "咳嗽" in symptoms or "呼吸困难" in symptoms


def test_find_related_symptoms_alias(kg):
    """通过别名也能查到症状"""
    symptoms = kg.find_related_symptoms("COPD")
    assert len(symptoms) > 0


def test_find_related_symptoms_unknown(kg):
    """查询未知疾病应返回空列表"""
    symptoms = kg.find_related_symptoms("不存在的疾病XYZ")
    assert symptoms == []


def test_find_recommended_tests(kg):
    """查询疾病的推荐检查"""
    tests = kg.find_recommended_tests("心力衰竭")
    assert len(tests) > 0
    assert any("BNP" in t or "心电图" in t for t in tests)


def test_entity_match_alias():
    """实体别名匹配"""
    entity = MedicalEntity("d1", "心力衰竭", "disease", aliases=["心衰", "心功能不全"])
    assert entity.match("患者心衰")
    assert entity.match("心功能不全加重")
    assert entity.match("心力衰竭急性发作")
    assert not entity.match("高血压")


def test_entity_match_case_insensitive():
    """实体匹配应大小写不敏感"""
    entity = MedicalEntity("d1", "COPD", "disease", aliases=["慢阻肺"])
    assert entity.match("copd急性加重")
    assert entity.match("慢阻肺患者")


def test_kg_save_and_load(kg, tmp_path):
    """知识图谱序列化/反序列化"""
    filepath = tmp_path / "kg.json"
    kg.save_to_file(str(filepath))
    assert filepath.exists()

    kg2 = MedicalKnowledgeGraph()
    kg2.load_from_file(str(filepath))
    assert len(kg2.entities) == len(kg.entities)
    assert len(kg2.relations) == len(kg.relations)


def test_get_related_relations(kg):
    """获取实体的相关关系"""
    relations = kg.get_related("disease_copd", "HAS_SYMPTOM")
    assert len(relations) > 0
    # 过滤关系类型
    test_relations = kg.get_related("disease_copd", "TESTED_BY")
    assert all(r.relation_type == "TESTED_BY" for r in test_relations)


def test_get_related_no_filter(kg):
    """不过滤关系类型应返回全部"""
    all_relations = kg.get_related("disease_copd")
    symptom_relations = kg.get_related("disease_copd", "HAS_SYMPTOM")
    assert len(all_relations) >= len(symptom_relations)


def test_get_entity_not_found(kg):
    """查询不存在的实体应返回 None"""
    assert kg.get_entity("nonexistent_id") is None


def test_load_from_dict_with_extra_fields():
    """load_from_dict 应忽略未知字段"""
    kg = MedicalKnowledgeGraph()
    data = {
        "entities": [
            {"id": "e1", "name": "测试", "entity_type": "symptom",
             "aliases": [], "description": "测试实体", "properties": {}}
        ],
        "relations": [
            {"source": "e1", "target": "e2", "relation_type": "HAS_SYMPTOM",
             "weight": 1.0, "evidence": ""}
        ],
        "extra_field": "should_be_ignored"
    }
    kg.load_from_dict(data)
    assert kg.get_entity("e1") is not None
