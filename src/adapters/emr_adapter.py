"""
EMR（电子病历系统）适配器
"""
from typing import Dict, Any
from .base import HospitalAdapter, MockHospitalAdapter


class EMRAdapter(HospitalAdapter):
    """EMR系统适配器"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("EMR", config)

    def connect(self) -> bool:
        endpoint = self.config.get("endpoint", "")
        if endpoint:
            self.connected = True
        return self.connected

    def fetch_patient_data(self, patient_id: str) -> Dict[str, Any]:
        if not self.connected:
            self.connect()
        return {
            "system": "EMR",
            "patient_id": patient_id,
            "records": []
        }

    def is_available(self) -> bool:
        return self.config.get("endpoint") is not None


class MockEMRAdapter(MockHospitalAdapter):
    """EMR模拟适配器"""

    def __init__(self, sample_data: Dict[str, Any] = None):
        super().__init__("EMR_Mock", sample_data=sample_data)
