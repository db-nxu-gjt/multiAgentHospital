"""
循证医学等级与证据管理模块
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Any


class EvidenceLevel(Enum):
    """循证等级定义"""
    A = "A"  # 高质量RCT Meta分析/系统评价
    B = "B"  # 队列研究/病例对照研究/指南
    C = "C"  # 病例系列/专家共识/病理生理推理
    D = "D"  # AI推理/类比，无直接文献支持

    @property
    def description(self) -> str:
        descriptions = {
            EvidenceLevel.A: "高质量RCT的Meta分析/系统评价",
            EvidenceLevel.B: "队列研究/病例对照研究/权威指南",
            EvidenceLevel.C: "病例系列/专家共识/病理生理学推理",
            EvidenceLevel.D: "仅基于AI推理/类比，无直接文献支持"
        }
        return descriptions[self]

    @property
    def rank(self) -> int:
        """等级数值，越高代表证据越强"""
        return {"A": 4, "B": 3, "C": 2, "D": 1}[self.value]

    @classmethod
    def parse(cls, value: Any) -> "EvidenceLevel":
        """安全解析证据等级，非法值返回 D"""
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.D
        v = str(value).strip().upper()
        for member in cls:
            if member.value == v:
                return member
        return cls.D


class RecommendationStrength(Enum):
    """推荐强度"""
    STRONG = "强推荐"
    WEAK = "弱推荐"
    CONDITIONAL = "有条件推荐"

    @classmethod
    def parse(cls, value: Any) -> "RecommendationStrength":
        """安全解析推荐强度，非法值返回 CONDITIONAL"""
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.CONDITIONAL
        v = str(value).strip()
        for member in cls:
            if member.value == v:
                return member
        return cls.CONDITIONAL


@dataclass
class EvidenceItem:
    """单个证据项"""
    source: str  # 来源：指南名称、文献标题、数据库等
    level: EvidenceLevel
    summary: str  # 证据摘要
    url: Optional[str] = None
    year: Optional[int] = None


@dataclass
class Recommendation:
    """诊疗建议"""
    content: str
    evidence_level: EvidenceLevel
    strength: RecommendationStrength
    evidences: List[EvidenceItem]
    confidence: float = 0.0  # 0-1置信度

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "evidence_level": self.evidence_level.value,
            "strength": self.strength.value,
            "confidence": round(self.confidence, 3),
            "evidences": [
                {
                    "source": e.source,
                    "level": e.level.value,
                    "summary": e.summary,
                    "url": e.url,
                    "year": e.year
                } for e in self.evidences
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Recommendation":
        return cls(
            content=data.get("content", ""),
            evidence_level=EvidenceLevel.parse(data.get("evidence_level")),
            strength=RecommendationStrength.parse(data.get("strength")),
            evidences=[
                EvidenceItem(
                    source=e.get("source", ""),
                    level=EvidenceLevel.parse(e.get("level")),
                    summary=e.get("summary", ""),
                    url=e.get("url"),
                    year=e.get("year")
                ) for e in data.get("evidences", []) if isinstance(e, dict)
            ],
            confidence=float(data.get("confidence", 0.0))
        )
