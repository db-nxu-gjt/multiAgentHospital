"""
PACS（影像归档通信系统）适配器
"""
from typing import Dict, Any
from .base import HospitalAdapter, MockHospitalAdapter


class PACSAdapter(HospitalAdapter):
    """PACS系统适配器"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("PACS", config)

    def connect(self) -> bool:
        endpoint = self.config.get("endpoint", "")
        if endpoint:
            self.connected = True
        return self.connected

    def fetch_patient_data(self, patient_id: str) -> Dict[str, Any]:
        if not self.connected:
            self.connect()
        return {
            "system": "PACS",
            "patient_id": patient_id,
            "imaging_reports": []
        }

    def is_available(self) -> bool:
        return self.config.get("endpoint") is not None


class MockPACSAdapter(MockHospitalAdapter):
    """PACS模拟适配器"""

    def __init__(self, sample_data: Dict[str, Any] = None):
        super().__init__("PACS_Mock", sample_data=sample_data)
