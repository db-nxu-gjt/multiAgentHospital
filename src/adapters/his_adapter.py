"""
HIS（医院信息系统）适配器
"""
from typing import Dict, Any
from .base import HospitalAdapter, MockHospitalAdapter


class HISAdapter(HospitalAdapter):
    """HIS系统适配器"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("HIS", config)

    def connect(self) -> bool:
        # 实际环境中通过HL7/FHIR/API连接HIS
        endpoint = self.config.get("endpoint", "")
        if endpoint:
            self.connected = True
        return self.connected

    def fetch_patient_data(self, patient_id: str) -> Dict[str, Any]:
        if not self.connected:
            self.connect()
        # 实际实现：调用HIS API
        return {
            "system": "HIS",
            "patient_id": patient_id,
            "orders": [],
            "billing": []
        }

    def is_available(self) -> bool:
        return self.config.get("endpoint") is not None


class MockHISAdapter(MockHospitalAdapter):
    """HIS模拟适配器"""

    def __init__(self, sample_data: Dict[str, Any] = None):
        super().__init__("HIS_Mock", sample_data=sample_data)
