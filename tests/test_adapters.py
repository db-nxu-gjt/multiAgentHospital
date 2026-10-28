"""
适配器测试 - HIS/EMR/LIS/PACS 及 Mock 适配器
"""
import pytest

from src.adapters.base import HospitalAdapter, MockHospitalAdapter
from src.adapters.his_adapter import HISAdapter, MockHISAdapter
from src.adapters.emr_adapter import EMRAdapter, MockEMRAdapter
from src.adapters.lis_adapter import LISAdapter, MockLISAdapter
from src.adapters.pacs_adapter import PACSAdapter, MockPACSAdapter


def test_mock_adapter_basic():
    """MockHospitalAdapter 基础功能"""
    data = {"P001": {"name": "张三", "age": 60}}
    adapter = MockHospitalAdapter("HIS", sample_data=data)
    assert adapter.system_name == "HIS"
    assert adapter.is_available()
    assert adapter.connect() is True
    assert adapter.fetch_patient_data("P001") == data["P001"]
    assert adapter.fetch_patient_data("NOT_EXIST") == {}


def test_mock_adapter_disconnect():
    adapter = MockHospitalAdapter("HIS", sample_data={})
    adapter.connect()
    assert adapter.connected is True
    adapter.disconnect()
    assert adapter.connected is False


def test_mock_adapter_default_empty_data():
    """未提供 sample_data 时应返回空 dict"""
    adapter = MockHospitalAdapter("HIS")
    assert adapter.fetch_patient_data("P001") == {}


def test_his_adapter_requires_endpoint():
    """HISAdapter 必须配置 endpoint 才可用"""
    adapter = HISAdapter()
    assert adapter.is_available() is False
    assert adapter.connect() is False


def test_his_adapter_with_endpoint():
    adapter = HISAdapter({"endpoint": "http://his.hospital.com/api"})
    assert adapter.is_available() is True
    assert adapter.connect() is True


def test_emr_adapter_requires_endpoint():
    adapter = EMRAdapter()
    assert adapter.is_available() is False


def test_emr_adapter_with_endpoint():
    adapter = EMRAdapter({"endpoint": "http://emr.hospital.com/api"})
    assert adapter.is_available() is True
    assert adapter.connect() is True


def test_lis_adapter_requires_endpoint():
    adapter = LISAdapter()
    assert adapter.is_available() is False


def test_lis_adapter_with_endpoint():
    adapter = LISAdapter({"endpoint": "http://lis.hospital.com/api"})
    assert adapter.is_available() is True


def test_pacs_adapter_requires_endpoint():
    adapter = PACSAdapter()
    assert adapter.is_available() is False


def test_pacs_adapter_with_endpoint():
    adapter = PACSAdapter({"endpoint": "http://pacs.hospital.com/api"})
    assert adapter.is_available() is True


def test_mock_specialty_adapters_naming():
    """MockHISAdapter 等专用 Mock 适配器应使用对应的 system_name"""
    assert MockHISAdapter().system_name == "HIS_Mock"
    assert MockEMRAdapter().system_name == "EMR_Mock"
    assert MockLISAdapter().system_name == "LIS_Mock"
    assert MockPACSAdapter().system_name == "PACS_Mock"


def test_his_adapter_returns_placeholder_for_unconnected():
    """HISAdapter 未连接时应自动尝试 connect，返回占位数据"""
    adapter = HISAdapter({"endpoint": "http://his.hospital.com/api"})
    data = adapter.fetch_patient_data("P001")
    assert data["patient_id"] == "P001"
    assert data["system"] == "HIS"


def test_lis_adapter_returns_empty_lab_results():
    """LISAdapter 应返回 lab_results 字段"""
    adapter = LISAdapter({"endpoint": "http://lis.hospital.com/api"})
    data = adapter.fetch_patient_data("P001")
    assert "lab_results" in data
    assert data["lab_results"] == []


def test_pacs_adapter_returns_empty_imaging_reports():
    """PACSAdapter 应返回 imaging_reports 字段"""
    adapter = PACSAdapter({"endpoint": "http://pacs.hospital.com/api"})
    data = adapter.fetch_patient_data("P001")
    assert "imaging_reports" in data
    assert data["imaging_reports"] == []


def test_hospital_adapter_is_abstract():
    """HospitalAdapter 是抽象基类，不能直接实例化"""
    with pytest.raises(TypeError):
        HospitalAdapter("HIS")


def test_mock_adapter_supports_arbitrary_system():
    """MockHospitalAdapter 应支持任意 system_name"""
    adapter = MockHospitalAdapter("CustomSystem", sample_data={"P1": {"x": 1}})
    assert adapter.system_name == "CustomSystem"
    assert adapter.fetch_patient_data("P1") == {"x": 1}
