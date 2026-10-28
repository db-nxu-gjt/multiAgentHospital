"""
LIS（检验信息系统）适配器
"""
from typing import Dict, Any
from .base import HospitalAdapter, MockHospitalAdapter


class LISAdapter(HospitalAdapter):
    """LIS系统适配器"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("LIS", config)

    def connect(self) -> bool:
        endpoint = self.config.get("endpoint", "")
        if endpoint:
            self.connected = True
        return self.connected

    def fetch_patient_data(self, patient_id: str) -> Dict[str, Any]:
        if not self.connected:
            self.connect()
        return {
            "system": "LIS",
            "patient_id": patient_id,
            "lab_results": []
        }

    def is_available(self) -> bool:
        return self.config.get("endpoint") is not None


class MockLISAdapter(MockHospitalAdapter):
    """LIS模拟适配器"""

    def __init__(self, sample_data: Dict[str, Any] = None):
        super().__init__("LIS_Mock", sample_data=sample_data)
