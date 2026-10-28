import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.data_loader import load_heart_disease_patients
from src.core.consultation import ConsultationEngine
from src.core.knowledge_graph import build_default_knowledge_graph

patients = load_heart_disease_patients(
    'e:/gjt/workspace/doing/project/MultiAgentHospital/data/raw/heart_disease_cleveland.csv',
    limit=3
)
p = patients[1]
print('患者2:', p.name, '真实标签:', p.raw_data.get('ground_truth'))
print('主诉:', p.chief_complaint)
print('现病史:', p.present_illness[:100])

kg = build_default_knowledge_graph()
engine = ConsultationEngine(knowledge_graph=kg)
cid = engine.request_consultation(p.patient_id, '胸痛原因待查')
report = engine.run_consultation(cid, patient=p)
print('鉴别诊断:')
for d in report.differential_diagnosis:
    print(f"  {d['disease']}: {d['confidence']}")
