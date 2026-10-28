"""
医学知识图谱模块
提供疾病、症状、检查、药物之间的医学知识关联
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Set, Any, Optional
from collections import defaultdict


@dataclass
class MedicalEntity:
    """医学实体"""
    id: str
    name: str
    entity_type: str  # disease/symptom/test/drug/treatment
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    def match(self, text: str) -> bool:
        """判断实体名称是否匹配文本"""
        text_lower = text.lower()
        if self.name.lower() in text_lower:
            return True
        for alias in self.aliases:
            if alias.lower() in text_lower:
                return True
        return False


@dataclass
class MedicalRelation:
    """医学关系"""
    source: str
    target: str
    relation_type: str  # HAS_SYMPTOM/TESTED_BY/TREATED_BY/etc.
    weight: float = 1.0
    evidence: str = ""


class MedicalKnowledgeGraph:
    """医学知识图谱"""

    def __init__(self):
        self.entities: Dict[str, MedicalEntity] = {}
        self.relations: List[MedicalRelation] = []
        self._index_by_type: Dict[str, Set[str]] = defaultdict(set)
        self._adjacency: Dict[str, List[MedicalRelation]] = defaultdict(list)

    def add_entity(self, entity: MedicalEntity) -> None:
        self.entities[entity.id] = entity
        self._index_by_type[entity.entity_type].add(entity.id)

    def add_relation(self, relation: MedicalRelation) -> None:
        self.relations.append(relation)
        self._adjacency[relation.source].append(relation)

    def get_entity(self, entity_id: str) -> Optional[MedicalEntity]:
        return self.entities.get(entity_id)

    def get_entities_by_type(self, entity_type: str) -> List[MedicalEntity]:
        return [self.entities[eid] for eid in self._index_by_type.get(entity_type, [])]

    def get_related(self, entity_id: str, relation_type: str = None) -> List[MedicalRelation]:
        """获取实体的相关关系"""
        relations = self._adjacency.get(entity_id, [])
        if relation_type:
            relations = [r for r in relations if r.relation_type == relation_type]
        return relations

    def find_diseases_by_symptoms(self, symptoms: List[str], top_k: int = 10) -> List[Dict[str, Any]]:
        """根据症状查找可能的疾病"""
        symptom_ids = set()
        for symptom in symptoms:
            for entity in self.entities.values():
                if entity.entity_type == "symptom" and entity.match(symptom):
                    symptom_ids.add(entity.id)

        disease_scores: Dict[str, float] = defaultdict(float)
        disease_total: Dict[str, float] = defaultdict(float)

        # 统计每种疾病拥有的症状
        for relation in self.relations:
            if relation.relation_type == "HAS_SYMPTOM":
                disease_total[relation.source] += relation.weight
                if relation.target in symptom_ids:
                    disease_scores[relation.source] += relation.weight

        # 计算匹配比例
        results = []
        for disease_id, matched_score in disease_scores.items():
            total = disease_total.get(disease_id, 1)
            coverage = matched_score / total if total > 0 else 0
            disease = self.entities.get(disease_id)
            if disease:
                results.append({
                    "disease": disease.name,
                    "disease_id": disease_id,
                    "matched_symptoms": [self.entities[sid].name for sid in symptom_ids],
                    "score": round(matched_score, 2),
                    "coverage": round(coverage, 3),
                    "confidence": round(min(matched_score * 0.3 + coverage * 0.5, 0.95), 3)
                })

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[:top_k]

    def find_related_symptoms(self, disease_name: str) -> List[str]:
        """查找疾病的典型症状"""
        disease_id = None
        for entity in self.entities.values():
            if entity.entity_type == "disease" and entity.match(disease_name):
                disease_id = entity.id
                break

        if not disease_id:
            return []

        symptoms = []
        for relation in self.get_related(disease_id, "HAS_SYMPTOM"):
            entity = self.entities.get(relation.target)
            if entity:
                symptoms.append(entity.name)
        return symptoms

    def find_recommended_tests(self, disease_name: str) -> List[str]:
        """查找疾病推荐检查"""
        disease_id = None
        for entity in self.entities.values():
            if entity.entity_type == "disease" and entity.match(disease_name):
                disease_id = entity.id
                break

        if not disease_id:
            return []

        tests = []
        for relation in self.get_related(disease_id, "TESTED_BY"):
            entity = self.entities.get(relation.target)
            if entity:
                tests.append(entity.name)
        return tests

    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典加载图谱"""
        for entity_data in data.get("entities", []):
            self.add_entity(MedicalEntity(**entity_data))
        for relation_data in data.get("relations", []):
            self.add_relation(MedicalRelation(**relation_data))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [
                {
                    "id": e.id,
                    "name": e.name,
                    "entity_type": e.entity_type,
                    "aliases": e.aliases,
                    "description": e.description,
                    "properties": e.properties
                } for e in self.entities.values()
            ],
            "relations": [
                {
                    "source": r.source,
                    "target": r.target,
                    "relation_type": r.relation_type,
                    "weight": r.weight,
                    "evidence": r.evidence
                } for r in self.relations
            ]
        }

    def save_to_file(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def load_from_file(self, filepath: str) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            self.load_from_dict(json.load(f))


def build_default_knowledge_graph() -> MedicalKnowledgeGraph:
    """构建默认医学知识图谱"""
    kg = MedicalKnowledgeGraph()

    # 疾病实体
    diseases = [
        MedicalEntity("disease_copd", "慢性阻塞性肺疾病", "disease",
                      aliases=["COPD", "慢阻肺", "慢性支气管炎"],
                      description="一种常见的、可以预防和治疗的慢性气道疾病"),
        MedicalEntity("disease_hf", "心力衰竭", "disease",
                      aliases=["心衰", "心功能不全"],
                      description="心脏泵血功能受损导致的一系列临床综合征"),
        MedicalEntity("disease_pneumonia", "肺炎", "disease",
                      aliases=["肺部感染"],
                      description="肺实质的炎症性疾病"),
        MedicalEntity("disease_chd", "冠心病", "disease",
                      aliases=["冠状动脉粥样硬化性心脏病"],
                      description="冠状动脉狭窄或阻塞导致的心肌缺血"),
        MedicalEntity("disease_diabetes", "2型糖尿病", "disease",
                      aliases=["糖尿病", "T2DM"],
                      description="以胰岛素抵抗为主的慢性代谢性疾病"),
        MedicalEntity("disease_stroke", "脑梗死", "disease",
                      aliases=["缺血性脑卒中", "中风"],
                      description="脑部血液供应障碍导致脑组织缺血缺氧性坏死"),
        MedicalEntity("disease_htn", "高血压", "disease",
                      aliases=["原发性高血压"],
                      description="体循环动脉血压升高为主要特征的临床综合征"),
    ]

    # 症状实体
    symptoms = [
        MedicalEntity("symptom_dyspnea", "呼吸困难", "symptom",
                      aliases=["气促", "气短", "喘憋"]),
        MedicalEntity("symptom_cough", "咳嗽", "symptom", aliases=["咳"]),
        MedicalEntity("symptom_sputum", "咳痰", "symptom", aliases=["痰多"]),
        MedicalEntity("symptom_chest_pain", "胸痛", "symptom", aliases=["胸闷"]),
        MedicalEntity("symptom_fatigue", "乏力", "symptom", aliases=["无力", "倦怠"]),
        MedicalEntity("symptom_edema", "水肿", "symptom", aliases=["浮肿"]),
        MedicalEntity("symptom_fever", "发热", "symptom", aliases=["发烧"]),
        MedicalEntity("symptom_dizziness", "头晕", "symptom", aliases=["眩晕"]),
        MedicalEntity("symptom_polyuria", "多尿", "symptom", aliases=["尿频"]),
        MedicalEntity("symptom_blurred_vision", "视物模糊", "symptom", aliases=["视力下降"]),
        MedicalEntity("symptom_headache", "头痛", "symptom", aliases=["头疼"]),
        MedicalEntity("symptom_nausea", "恶心", "symptom", aliases=["呕吐"]),
    ]

    # 检查实体
    tests = [
        MedicalEntity("test_spirometry", "肺功能检查", "test", aliases=["肺功能", "肺通气功能"]),
        MedicalEntity("test_chest_ct", "胸部CT", "test", aliases=["肺CT", "胸部计算机断层扫描"]),
        MedicalEntity("test_chest_xray", "胸部X线", "test", aliases=["胸片", "胸部平片"]),
        MedicalEntity("test_bnp", "BNP/NT-proBNP", "test", aliases=["脑钠肽", "NT-proBNP"]),
        MedicalEntity("test_ecg", "心电图", "test", aliases=["ECG", "EKG"]),
        MedicalEntity("test_echo", "超声心动图", "test", aliases=["心脏超声"]),
        MedicalEntity("test_blood_glucose", "血糖", "test", aliases=["空腹血糖", "餐后血糖"]),
        MedicalEntity("test_hb1ac", "糖化血红蛋白", "test", aliases=["HbA1c"]),
        MedicalEntity("test_head_ct", "头颅CT", "test", aliases=["脑CT"]),
        MedicalEntity("test_mri", "头颅MRI", "test", aliases=["脑核磁"]),
        MedicalEntity("test_bp", "血压监测", "test", aliases=["24小时动态血压"]),
    ]

    # 药物实体
    drugs = [
        MedicalEntity("drug_salbutamol", "沙丁胺醇", "drug", aliases=["万托林"]),
        MedicalEntity("drug_ipratropium", "异丙托溴铵", "drug", aliases=["爱全乐"]),
        MedicalEntity("drug_furosemide", "呋塞米", "drug", aliases=["速尿"]),
        MedicalEntity("drug_acei", "ACEI/ARB", "drug", aliases=["依那普利", "缬沙坦"]),
        MedicalEntity("drug_metformin", "二甲双胍", "drug", aliases=["格华止"]),
        MedicalEntity("drug_aspirin", "阿司匹林", "drug", aliases=["拜阿司匹林"]),
        MedicalEntity("drug_statin", "他汀类药物", "drug", aliases=["阿托伐他汀", "瑞舒伐他汀"]),
    ]

    for entity in diseases + symptoms + tests + drugs:
        kg.add_entity(entity)

    # 疾病-症状关系
    disease_symptoms = {
        "disease_copd": ["symptom_dyspnea", "symptom_cough", "symptom_sputum", "symptom_chest_pain"],
        "disease_hf": ["symptom_dyspnea", "symptom_fatigue", "symptom_edema", "symptom_chest_pain"],
        "disease_pneumonia": ["symptom_fever", "symptom_cough", "symptom_sputum", "symptom_dyspnea"],
        "disease_chd": ["symptom_chest_pain", "symptom_dyspnea", "symptom_fatigue"],
        "disease_diabetes": ["symptom_polyuria", "symptom_fatigue", "symptom_blurred_vision"],
        "disease_stroke": ["symptom_headache", "symptom_dizziness", "symptom_nausea"],
        "disease_htn": ["symptom_headache", "symptom_dizziness", "symptom_chest_pain"],
    }

    # 疾病-检查关系
    disease_tests = {
        "disease_copd": ["test_spirometry", "test_chest_ct", "test_chest_xray"],
        "disease_hf": ["test_bnp", "test_ecg", "test_echo"],
        "disease_pneumonia": ["test_chest_xray", "test_chest_ct"],
        "disease_chd": ["test_ecg", "test_echo"],
        "disease_diabetes": ["test_blood_glucose", "test_hb1ac"],
        "disease_stroke": ["test_head_ct", "test_mri"],
        "disease_htn": ["test_bp", "test_ecg"],
    }

    # 疾病-药物关系
    disease_drugs = {
        "disease_copd": ["drug_salbutamol", "drug_ipratropium"],
        "disease_hf": ["drug_furosemide", "drug_acei"],
        "disease_diabetes": ["drug_metformin"],
        "disease_chd": ["drug_aspirin", "drug_statin"],
        "disease_htn": ["drug_acei"],
    }

    for disease_id, symptom_ids in disease_symptoms.items():
        for symptom_id in symptom_ids:
            kg.add_relation(MedicalRelation(disease_id, symptom_id, "HAS_SYMPTOM", weight=1.0))

    for disease_id, test_ids in disease_tests.items():
        for test_id in test_ids:
            kg.add_relation(MedicalRelation(disease_id, test_id, "TESTED_BY", weight=1.0))

    for disease_id, drug_ids in disease_drugs.items():
        for drug_id in drug_ids:
            kg.add_relation(MedicalRelation(disease_id, drug_id, "TREATED_BY", weight=1.0))

    return kg
