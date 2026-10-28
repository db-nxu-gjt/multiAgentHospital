"""
医院信息系统适配器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class HospitalAdapter(ABC):
    """医院信息系统适配器基类"""

    def __init__(self, system_name: str, config: Dict[str, Any] = None):
        self.system_name = system_name
        self.config = config or {}
        self.connected = False

    @abstractmethod
    def connect(self) -> bool:
        """连接医院系统"""
        pass

    @abstractmethod
    def fetch_patient_data(self, patient_id: str) -> Dict[str, Any]:
        """获取患者数据"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查适配器是否可用"""
        pass

    def disconnect(self) -> None:
        """断开连接"""
        self.connected = False


class MockHospitalAdapter(HospitalAdapter):
    """模拟医院系统适配器，用于测试和演示"""

    def __init__(self, system_name: str, config: Dict[str, Any] = None, sample_data: Dict[str, Any] = None):
        super().__init__(system_name, config)
        self.sample_data = sample_data or {}

    def connect(self) -> bool:
        self.connected = True
        return True

    def fetch_patient_data(self, patient_id: str) -> Dict[str, Any]:
        return self.sample_data.get(patient_id, {})

    def is_available(self) -> bool:
        return True
