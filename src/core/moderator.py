"""
会诊主持人智能体（Moderator Agent）
负责协调多个专科智能体的讨论、辩论与意见整合
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from .patient import Patient
from .agent import SpecialistAgent, AgentOpinion
from .evidence import EvidenceLevel, RecommendationStrength, EvidenceItem, Recommendation


@dataclass
class DiscussionRound:
    """讨论轮次"""
    round_number: int
    topic: str
    opinions: List[AgentOpinion] = field(default_factory=list)
    consensus_points: List[str] = field(default_factory=list)
    disagreement_points: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "round_number": self.round_number,
            "topic": self.topic,
            "opinions": [op.to_dict() for op in self.opinions],
            "consensus_points": self.consensus_points,
            "disagreement_points": self.disagreement_points
        }


@dataclass
class ConsultationReport:
    """会诊报告"""
    consultation_id: str
    patient_id: str
    patient_name: str
    consultation_type: str
    status: str
    created_at: str
    completed_at: Optional[str] = None

    participating_agents: List[Dict[str, str]] = field(default_factory=list)
    differential_diagnosis: List[Dict[str, Any]] = field(default_factory=list)
    recommended_tests: List[Recommendation] = field(default_factory=list)
    treatment_plan: List[Recommendation] = field(default_factory=list)
    medication_suggestions: List[Recommendation] = field(default_factory=list)
    risk_assessment: str = ""
    follow_up_plan: List[str] = field(default_factory=list)
    discussion_summary: List[DiscussionRound] = field(default_factory=list)
    disagreements: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    final_conclusion: str = ""

    def to_dict(self) -> dict:
        return {
            "consultation_id": self.consultation_id,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "consultation_type": self.consultation_type,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "participating_agents": self.participating_agents,
            "differential_diagnosis": self.differential_diagnosis,
            "recommended_tests": [r.to_dict() for r in self.recommended_tests],
            "treatment_plan": [r.to_dict() for r in self.treatment_plan],
            "medication_suggestions": [r.to_dict() for r in self.medication_suggestions],
            "risk_assessment": self.risk_assessment,
            "follow_up_plan": self.follow_up_plan,
            "discussion_summary": [d.to_dict() for d in self.discussion_summary],
            "disagreements": self.disagreements,
            "uncertainties": self.uncertainties,
            "final_conclusion": self.final_conclusion
        }

    def to_markdown(self) -> str:
        """转换为Markdown报告"""
        lines = [
            f"# 虚拟会诊报告",
            f"",
            f"**会诊编号**：{self.consultation_id}",
            f"**患者**：{self.patient_name}（{self.patient_id}）",
            f"**会诊类型**：{self.consultation_type}",
            f"**状态**：{self.status}",
            f"**生成时间**：{self.created_at}",
            f"",
            f"## 一、参与会诊专家",
            ""
        ]

        for agent in self.participating_agents:
            lines.append(f"- {agent['name']}（{agent['specialty']}）")

        lines.extend([
            "",
            "## 二、鉴别诊断",
            "",
            "| 排序 | 诊断 | 置信度 | 证据等级 | 依据 |",
            "|------|------|--------|----------|------|"
        ])

        for idx, diag in enumerate(self.differential_diagnosis, 1):
            lines.append(
                f"| {idx} | {diag.get('disease', '')} | "
                f"{diag.get('confidence', 0):.0%} | "
                f"{diag.get('evidence_level', 'D')} | "
                f"{diag.get('reasoning', '')[:60]}... |"
            )

        lines.extend([
            "",
            "## 三、推荐检查",
            ""
        ])
        for rec in self.recommended_tests:
            lines.append(f"- {rec.content}（证据等级：{rec.evidence_level.value}）")

        lines.extend([
            "",
            "## 四、治疗方案",
            ""
        ])
        for rec in self.treatment_plan:
            lines.append(f"- {rec.content}（证据等级：{rec.evidence_level.value}，{rec.strength.value}）")

        lines.extend([
            "",
            "## 五、用药建议",
            ""
        ])
        for rec in self.medication_suggestions:
            lines.append(f"- {rec.content}")

        lines.extend([
            "",
            f"## 六、风险评估",
            f"",
            self.risk_assessment,
            "",
            "## 七、随访计划",
            ""
        ])
        for item in self.follow_up_plan:
            lines.append(f"- {item}")

        if self.uncertainties:
            lines.extend([
                "",
                "## 八、不确定性声明",
                ""
            ])
            for item in self.uncertainties:
                lines.append(f"- {item}")

        lines.extend([
            "",
            f"## 九、最终结论",
            f"",
            self.final_conclusion,
            ""
        ])

        return "\n".join(lines)


class ModeratorAgent:
    """会诊主持人智能体"""

    def __init__(self, max_rounds: int = 3):
        self.max_rounds = max_rounds
        self.discussion_log: List[str] = []

    def conduct_consultation(self, patient: Patient, agents: List[SpecialistAgent],
                             consultation_id: str,
                             consultation_type: str = "MDT") -> ConsultationReport:
        """主持并完成一次虚拟会诊"""
        self.discussion_log = []
        self.discussion_log.append(f"[{datetime.now()}] 开始主持会诊 {consultation_id}")

        report = ConsultationReport(
            consultation_id=consultation_id,
            patient_id=patient.patient_id,
            patient_name=patient.name,
            consultation_type=consultation_type,
            status="IN_PROGRESS",
            created_at=datetime.now().isoformat(),
            participating_agents=[
                {"agent_id": a.agent_id, "name": a.name, "specialty": a.specialty}
                for a in agents
            ]
        )

        # Round 1: 各Agent独立发表初步意见
        round1 = DiscussionRound(round_number=1, topic="初步诊断意见")
        initial_opinions = []
        for agent in agents:
            try:
                opinion = agent.analyze(patient)
                round1.opinions.append(opinion)
                initial_opinions.append(opinion)
                self.discussion_log.append(f"✓ {agent.name} 完成分析")
            except Exception as e:
                self.discussion_log.append(f"✗ {agent.name} 分析失败: {str(e)}")

        # 识别共识点与分歧点
        round1.consensus_points, round1.disagreement_points = self._identify_consensus(initial_opinions)
        report.discussion_summary.append(round1)

        # Round 2: 针对分歧点辩论（简化实现）
        if round1.disagreement_points and self.max_rounds >= 2:
            round2 = DiscussionRound(
                round_number=2,
                topic="针对分歧点讨论",
                opinions=initial_opinions,
                consensus_points=round1.consensus_points,
                disagreement_points=round1.disagreement_points
            )
            report.discussion_summary.append(round2)
            self.discussion_log.append("完成分歧点讨论")

        # Round 3: 综合决策
        round3 = DiscussionRound(round_number=3, topic="综合决策与报告生成")
        round3.consensus_points = round1.consensus_points
        report.discussion_summary.append(round3)

        # 整合最终报告
        self._synthesize_report(report, initial_opinions, patient)

        report.status = "COMPLETED"
        report.completed_at = datetime.now().isoformat()
        self.discussion_log.append(f"[{datetime.now()}] 会诊 {consultation_id} 完成")

        return report

    def _identify_consensus(self, opinions: List[AgentOpinion]) -> tuple:
        """识别共识点与分歧点

        - 剔除占位诊断（如"无影像资料"、"暂无明确xxx疾病"）
        - 剔除零置信度项
        - 同一 Agent 内重复出现的疾病只计一次
        - 区分 Agent 维度：>=2 个不同专科支持才算"共识"
        """
        # 占位诊断关键字（不参与共识/分歧识别）
        PLACEHOLDER_KEYWORDS = ("无影像资料", "暂无明确", "未见明确异常", "影像未见")

        def is_placeholder(name: str) -> bool:
            return any(k in name for k in PLACEHOLDER_KEYWORDS)

        # disease -> set of agent_id who proposed it (with avg confidence)
        disease_agents: Dict[str, set] = {}
        disease_confs: Dict[str, List[float]] = {}

        for opinion in opinions:
            seen_in_agent = set()
            for diag in opinion.differential_diagnosis:
                disease = diag.get("disease", "")
                conf = diag.get("confidence", 0)
                if not disease or is_placeholder(disease) or conf <= 0:
                    continue
                if disease in seen_in_agent:
                    # 同一 Agent 内重复出现，不重复计数
                    continue
                seen_in_agent.add(disease)
                disease_agents.setdefault(disease, set()).add(opinion.agent_id)
                disease_confs.setdefault(disease, []).append(conf)

        consensus = []
        disagreement = []

        for disease, agents in disease_agents.items():
            avg_conf = sum(disease_confs[disease]) / len(disease_confs[disease])
            if len(agents) >= 2:
                consensus.append(
                    f"{len(agents)}个专科均考虑{disease}（平均置信度{avg_conf:.0%}）"
                )
            else:
                disagreement.append(f"仅单个专科考虑{disease}")

        if not consensus and not disagreement:
            disagreement.append("各专科初步诊断差异较大或缺少有效诊断，需进一步整合")

        return consensus, disagreement

    def _synthesize_report(self, report: ConsultationReport,
                           opinions: List[AgentOpinion],
                           patient: Patient) -> None:
        """整合各Agent意见生成最终报告"""

        # 1. 鉴别诊断排序（剔除占位诊断）
        PLACEHOLDER_KEYWORDS = ("无影像资料", "暂无明确", "未见明确异常", "影像未见")

        def is_placeholder(name: str) -> bool:
            return any(k in name for k in PLACEHOLDER_KEYWORDS)

        diagnosis_scores = {}
        for opinion in opinions:
            for diag in opinion.differential_diagnosis:
                disease = diag.get("disease", "")
                if not disease or is_placeholder(disease):
                    continue

                if disease not in diagnosis_scores:
                    diagnosis_scores[disease] = {
                        "disease": disease,
                        "confidence_sum": 0.0,
                        "count": 0,
                        "evidence_levels": [],
                        "reasonings": [],
                        "agent_ids": set(),
                    }

                diagnosis_scores[disease]["confidence_sum"] += float(diag.get("confidence", 0))
                diagnosis_scores[disease]["count"] += 1
                diagnosis_scores[disease]["evidence_levels"].append(diag.get("evidence_level", "D"))
                diagnosis_scores[disease]["reasonings"].append(diag.get("reasoning", ""))
                diagnosis_scores[disease]["agent_ids"].add(opinion.agent_id)

        # 计算加权置信度（按不同 Agent 数加权，而非按诊断条目数）
        sorted_diagnosis = []
        for disease, data in diagnosis_scores.items():
            avg_conf = data["confidence_sum"] / data["count"] if data["count"] > 0 else 0
            # 不同专科数（去重）支持时提升置信度
            n_specialties = len(data["agent_ids"])
            boost = min((n_specialties - 1) * 0.1, 0.2)
            final_conf = min(avg_conf + boost, 0.99)

            # 证据等级取最高
            level_ranks = {"A": 4, "B": 3, "C": 2, "D": 1}
            best_level = max(data["evidence_levels"], key=lambda x: level_ranks.get(x, 0))

            sorted_diagnosis.append({
                "disease": disease,
                "confidence": round(final_conf, 3),
                "evidence_level": best_level,
                "reasoning": "；".join(dict.fromkeys(data["reasonings"]))[:200],
                "supporting_specialties": n_specialties
            })

        sorted_diagnosis.sort(key=lambda x: x["confidence"], reverse=True)
        report.differential_diagnosis = sorted_diagnosis

        # 2. 推荐检查（去重合并，保持稳定排序）
        test_set = set()
        for opinion in opinions:
            for test in opinion.recommended_tests:
                if test and not test.startswith("根据临床需要"):
                    test_set.add(test)

        for test in sorted(test_set):
            report.recommended_tests.append(Recommendation(
                content=test,
                evidence_level=EvidenceLevel.B,
                strength=RecommendationStrength.STRONG,
                evidences=[EvidenceItem("临床诊疗常规", EvidenceLevel.B, "基于专科诊疗常规推荐")]
            ))

        # 3. 治疗方案
        treatment_set = set()
        for opinion in opinions:
            for treatment in opinion.treatment_plan:
                if treatment:
                    treatment_set.add(treatment)

        for treatment in sorted(treatment_set):
            report.treatment_plan.append(Recommendation(
                content=treatment,
                evidence_level=EvidenceLevel.B,
                strength=RecommendationStrength.CONDITIONAL,
                evidences=[EvidenceItem("专家共识", EvidenceLevel.B, "基于多学科专家意见")]
            ))

        # 4. 用药建议（主要来自药学Agent，剔除"无明显相互作用"等中性条目）
        NEUTRAL_MED_KEYWORDS = ("无明显相互作用", "当前用药无明显")
        for opinion in opinions:
            if opinion.specialty == "药学":
                for suggestion in opinion.treatment_plan:
                    if any(k in suggestion for k in NEUTRAL_MED_KEYWORDS):
                        continue
                    report.medication_suggestions.append(Recommendation(
                        content=suggestion,
                        evidence_level=EvidenceLevel.A,
                        strength=RecommendationStrength.STRONG,
                        evidences=[EvidenceItem("药品说明书/临床药学指南", EvidenceLevel.A, "基于药物安全性评估")]
                    ))

        # 5. 风险评估
        risk_parts = [op.risk_assessment for op in opinions if op.risk_assessment and op.risk_assessment != "无法评估"]
        report.risk_assessment = "；".join(risk_parts) if risk_parts else "需结合临床进一步评估"

        # 6. 随访计划
        report.follow_up_plan = [
            "24-48小时内复查关键异常指标",
            "根据治疗效果调整治疗方案",
            "必要时安排专科门诊随访",
            "建议1-2周后复诊评估"
        ]

        # 7. 不确定性
        if report.differential_diagnosis:
            top_conf = report.differential_diagnosis[0].get("confidence", 0)
            if top_conf < 0.7:
                report.uncertainties.append("当前诊断置信度不足，建议进一步完善检查")

        if len(report.differential_diagnosis) > 1:
            top_conf = report.differential_diagnosis[0].get("confidence", 0)
            second_conf = report.differential_diagnosis[1].get("confidence", 0)
            # 首选与次选置信度接近时提示不确定性
            if top_conf - second_conf < 0.15:
                report.uncertainties.append("首选与次选诊断置信度接近，需结合动态观察鉴别")

        # 8. 最终结论
        if report.differential_diagnosis:
            top = report.differential_diagnosis[0]
            report.final_conclusion = (
                f"综合多学科AI专家意见，当前最可能的诊断为：{top['disease']} "
                f"（置信度：{top['confidence']:.0%}，证据等级：{top['evidence_level']}，"
                f"{top['supporting_specialties']}个专科支持）。"
                f"建议按推荐方案进一步完善检查并启动治疗，由主诊医师审核确认。"
            )
        else:
            report.final_conclusion = "当前信息不足以形成明确诊断意见，建议补充资料后再次会诊。"

    def get_discussion_log(self) -> str:
        return "\n".join(self.discussion_log)
