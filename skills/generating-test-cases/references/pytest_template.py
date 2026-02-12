"""
pytest 测试文件模板
包含基本的测试结构和常用模式
"""

import pytest
import allure  # type: ignore
import logging
from typing import Dict, Any, List

# 测试配置
TEST_CONFIG = {
    "api_base_url": "http://localhost:8080",
    "ui_base_url": "http://localhost:3000",
    "timeout": 30,
    "retry_count": 3,
}

# 日志设置
logger = logging.getLogger(__name__)


class TestBase:
    """测试基类，包含通用功能"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """每个测试用例的前置和后置操作"""
        # 测试开始前
        logger.info("测试开始")
        yield
        # 测试结束后
        logger.info("测试结束")

    def assert_response(self, response, expected_status: int = 200):
        """验证响应"""
        assert response.status_code == expected_status, (
            f"预期状态码 {expected_status}，实际 {response.status_code}"
        )

        if response.content:
            try:
                return response.json()
            except Exception as e:
                logger.error(f"JSON 解析失败: {e}")
                return response.text
        return None

    def log_step(self, message: str):
        """记录测试步骤"""
        logger.info(f"步骤: {message}")
        allure.step(message)


class TestExample(TestBase):
    """示例测试类"""

    @allure.feature("示例功能")
    @allure.story("示例测试用例")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("示例测试 - 验证基本功能")
    @allure.description("""
    这是一个示例测试用例，展示如何编写 pytest 测试。
    
    测试场景:
    1. 验证系统基本功能
    2. 测试错误处理
    3. 验证边界条件
    """)
    def test_example_basic(self):
        """示例基本测试"""
        with allure.step("步骤1: 准备测试数据"):
            test_data = {"key": "value"}
            allure.attach_json(test_data, name="测试数据")

        with allure.step("步骤2: 执行操作"):
            # 这里执行实际的操作
            result = True

        with allure.step("步骤3: 验证结果"):
            assert result is True, "操作应返回 True"
            allure.attach("验证通过", name="验证结果")

    @allure.feature("示例功能")
    @allure.story("参数化测试")
    @allure.title("示例参数化测试")
    @pytest.mark.parametrize("input_value,expected", [(1, 2), (2, 4), (3, 6)])
    def test_example_parametrized(self, input_value, expected):
        """示例参数化测试"""
        with allure.step(f"测试输入: {input_value}"):
            result = input_value * 2
            assert result == expected, f"预期 {expected}，实际 {result}"

    @allure.feature("示例功能")
    @allure.story("异常测试")
    @allure.title("示例异常测试")
    def test_example_exception(self):
        """示例异常测试"""
        with allure.step("测试异常情况"):
            with pytest.raises(ValueError) as exc_info:
                raise ValueError("测试异常")

            assert "测试异常" in str(exc_info.value)
            allure.attach(f"捕获异常: {exc_info.value}", name="异常信息")


# 数据驱动测试示例
TEST_CASES = [
    {
        "name": "用例1",
        "data": {"username": "user1", "password": "pass1"},
        "expected": "success",
    },
    {
        "name": "用例2",
        "data": {"username": "user2", "password": "pass2"},
        "expected": "success",
    },
]


@pytest.mark.parametrize("test_case", TEST_CASES)
def test_data_driven(test_case: Dict[str, Any]):
    """数据驱动测试示例"""
    allure.dynamic.title(f"数据驱动测试 - {test_case['name']}")

    with allure.step(f"执行测试用例: {test_case['name']}"):
        # 使用测试数据执行操作
        data = test_case["data"]
        expected = test_case["expected"]

        # 这里执行实际的操作
        result = "success"  # 模拟结果

        assert result == expected, f"预期 {expected}，实际 {result}"


# 测试夹具示例
@pytest.fixture(scope="module")
def shared_resource():
    """模块级共享资源"""
    resource = {"initialized": True, "data": []}
    logger.info("初始化共享资源")
    yield resource
    logger.info("清理共享资源")


@pytest.fixture
def test_user():
    """测试用户夹具"""
    return {
        "id": 1,
        "username": "test_user",
        "email": "test@example.com",
        "role": "user",
    }


@pytest.fixture
def admin_user():
    """管理员用户夹具"""
    return {
        "id": 100,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
    }


def test_with_fixtures(test_user, admin_user, shared_resource):
    """使用多个夹具的测试"""
    allure.title("测试夹具使用")

    with allure.step("验证测试用户"):
        assert test_user["role"] == "user"
        allure.attach_json(test_user, name="测试用户")

    with allure.step("验证管理员用户"):
        assert admin_user["role"] == "admin"
        allure.attach_json(admin_user, name="管理员用户")

    with allure.step("验证共享资源"):
        assert shared_resource["initialized"] is True
        shared_resource["data"].append("test_data")
        assert "test_data" in shared_resource["data"]


# Allure 报告增强示例
def test_allure_enhanced():
    """Allure 增强报告示例"""
    allure.epic("大型功能")
    allure.feature("报告功能")
    allure.story("详细报告")
    allure.title("Allure 增强报告测试")

    # 添加链接
    allure.link("https://example.com", name="相关文档")
    allure.issue("BUG-123", "https://jira.example.com/browse/BUG-123")
    allure.testcase("TC-456", "https://testops.example.com/testcase/TC-456")

    # 添加附件
    allure.attach(
        "测试日志内容", name="日志", attachment_type=allure.attachment_type.TEXT
    )
    allure.attach(
        "<html><body><h1>测试HTML</h1></body></html>",
        name="HTML内容",
        attachment_type=allure.attachment_type.HTML,
    )

    # 添加环境信息
    allure.environment(browser="Chrome", version="120", platform="Windows")

    # 测试步骤
    with allure.step("复杂操作步骤"):
        with allure.step("子步骤1"):
            pass
        with allure.step("子步骤2"):
            pass

    assert True


if __name__ == "__main__":
    # 可以直接运行测试
    pytest.main([__file__, "-v"])
