"""
pytest 包装：从 test.xlsx 读取测试用例并执行

每个用例ID生成一个独立的 pytest 测试项，失败时显示详细消息。
test.xlsx 由 tests/build_test_xlsx.py 生成；若文件缺失则自动重新生成。
"""
import json
from pathlib import Path

import pytest

from tests.xlsx_runner import XlsxTestRunner, TestCase

XLSX = Path(__file__).parent / "test.xlsx"


def _ensure_xlsx():
    if not XLSX.exists():
        from tests.build_test_xlsx import build
        build()


def _load_cases() -> list:
    _ensure_xlsx()
    runner = XlsxTestRunner(str(XLSX))
    return runner.load_cases()


_CASES = _load_cases()


def _case_id(c: TestCase) -> str:
    return f"{c.case_id}-{c.name}"


@pytest.mark.parametrize("case", _CASES, ids=[_case_id(c) for c in _CASES])
def test_xlsx_case(case: TestCase):
    runner = XlsxTestRunner(str(XLSX))
    # 只运行当前用例
    runner.results = []
    result = runner._run_one(case)
    if not result.passed:
        pytest.fail(
            f"[{case.category}] {case.case_id} {case.name}\n"
            f"操作: {case.operation}\n"
            f"参数: {json.dumps(case.params, ensure_ascii=False)}\n"
            f"断言: {case.expected_type} 期望: {case.expected}\n"
            f"原因: {result.message}"
        )


def test_xlsx_summary():
    """汇总：所有用例必须全部通过"""
    runner = XlsxTestRunner(str(XLSX))
    runner.run(verbose=False)
    s = runner.summary()
    failed = [r for r in runner.results if not r.passed and "已跳过" not in r.message]
    assert s["failed"] == 0, (
        f"共失败 {len(failed)} 条:\n" +
        "\n".join(f"  - {r.case_id} {r.name}: {r.message}" for r in failed)
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
