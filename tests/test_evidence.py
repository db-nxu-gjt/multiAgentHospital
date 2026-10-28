"""
循证医学等级与证据管理测试
"""
import pytest

from src.core.evidence import (
    EvidenceLevel, RecommendationStrength,
    EvidenceItem, Recommendation
)


def test_evidence_level_description():
    assert "RCT" in EvidenceLevel.A.description
    assert "队列" in EvidenceLevel.B.description
    assert "病例" in EvidenceLevel.C.description
    assert "AI" in EvidenceLevel.D.description


def test_evidence_level_rank():
    assert EvidenceLevel.A.rank > EvidenceLevel.B.rank
    assert EvidenceLevel.B.rank > EvidenceLevel.C.rank
    assert EvidenceLevel.C.rank > EvidenceLevel.D.rank


def test_evidence_level_parse_valid():
    """parse 方法应正确处理合法值"""
    assert EvidenceLevel.parse("A") == EvidenceLevel.A
    assert EvidenceLevel.parse("a") == EvidenceLevel.A  # 大小写不敏感
    assert EvidenceLevel.parse("B") == EvidenceLevel.B
    assert EvidenceLevel.parse(EvidenceLevel.C) == EvidenceLevel.C


def test_evidence_level_parse_invalid():
    """parse 方法对非法值应回退到 D"""
    assert EvidenceLevel.parse(None) == EvidenceLevel.D
    assert EvidenceLevel.parse("") == EvidenceLevel.D
    assert EvidenceLevel.parse("XYZ非法") == EvidenceLevel.D
    assert EvidenceLevel.parse(123) == EvidenceLevel.D


def test_recommendation_strength_parse_valid():
    """parse 方法应正确处理合法值"""
    assert RecommendationStrength.parse("强推荐") == RecommendationStrength.STRONG
    assert RecommendationStrength.parse("弱推荐") == RecommendationStrength.WEAK
    assert RecommendationStrength.parse("有条件推荐") == RecommendationStrength.CONDITIONAL
    assert RecommendationStrength.parse(RecommendationStrength.STRONG) == RecommendationStrength.STRONG


def test_recommendation_strength_parse_invalid():
    """parse 方法对非法值应回退到 CONDITIONAL"""
    assert RecommendationStrength.parse(None) == RecommendationStrength.CONDITIONAL
    assert RecommendationStrength.parse("") == RecommendationStrength.CONDITIONAL
    assert RecommendationStrength.parse("XYZ非法") == RecommendationStrength.CONDITIONAL


def test_evidence_item_creation():
    item = EvidenceItem(
        source="2023 ESC心力衰竭指南",
        level=EvidenceLevel.A,
        summary="SGLT2抑制剂降低心衰住院风险",
        url="https://example.com",
        year=2023
    )
    assert item.source == "2023 ESC心力衰竭指南"
    assert item.level == EvidenceLevel.A
    assert item.year == 2023


def test_recommendation_to_dict():
    rec = Recommendation(
        content="建议行心电图检查",
        evidence_level=EvidenceLevel.B,
        strength=RecommendationStrength.STRONG,
        evidences=[EvidenceItem("临床指南", EvidenceLevel.B, "心电图是心衰评估基础")],
        confidence=0.85
    )
    d = rec.to_dict()
    assert d["content"] == "建议行心电图检查"
    assert d["evidence_level"] == "B"
    assert d["strength"] == "强推荐"
    assert d["confidence"] == 0.85
    assert len(d["evidences"]) == 1
    assert d["evidences"][0]["level"] == "B"


def test_recommendation_roundtrip():
    """序列化/反序列化往返测试"""
    original = Recommendation(
        content="使用 ACEI 治疗心力衰竭",
        evidence_level=EvidenceLevel.A,
        strength=RecommendationStrength.STRONG,
        evidences=[
            EvidenceItem("ESC指南", EvidenceLevel.A, "Class I 推荐"),
            EvidenceItem("中华医学会心血管病学分会", EvidenceLevel.A, "强推荐")
        ],
        confidence=0.92
    )
    d = original.to_dict()
    restored = Recommendation.from_dict(d)
    assert restored.content == original.content
    assert restored.evidence_level == original.evidence_level
    assert restored.strength == original.strength
    assert restored.confidence == original.confidence
    assert len(restored.evidences) == 2


def test_recommendation_from_dict_with_invalid_fields():
    """from_dict 应能容忍字段缺失/类型错误"""
    rec = Recommendation.from_dict({
        "content": "测试建议",
        # 缺失 evidence_level, strength, evidences
    })
    assert rec.content == "测试建议"
    assert rec.evidence_level == EvidenceLevel.D  # 默认
    assert rec.strength == RecommendationStrength.CONDITIONAL  # 默认
    assert rec.evidences == []
    assert rec.confidence == 0.0


def test_recommendation_from_dict_with_garbage_evidences():
    """evidences 字段为非列表或包含非 dict 时不应崩溃"""
    rec = Recommendation.from_dict({
        "content": "x",
        "evidence_level": "A",
        "strength": "强推荐",
        "evidences": "should_be_list"  # 类型错误
    })
    assert rec.evidences == []

    rec2 = Recommendation.from_dict({
        "content": "x",
        "evidence_level": "A",
        "strength": "强推荐",
        "evidences": [{"source": "s1"}, "not_a_dict", {"source": "s2"}]
    })
    # 只有 2 个 dict 项被解析
    assert len(rec2.evidences) == 2


def test_recommendation_confidence_rounding():
    """confidence 序列化应保留 3 位小数"""
    rec = Recommendation(
        content="x", evidence_level=EvidenceLevel.A,
        strength=RecommendationStrength.STRONG, evidences=[],
        confidence=0.123456789
    )
    assert rec.to_dict()["confidence"] == 0.123
