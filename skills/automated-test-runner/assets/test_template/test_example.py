#!/usr/bin/env python3
"""
测试用例模板

这是一个使用 pytest 和 Allure 的测试模板。
包含常见的测试模式和最佳实践。
"""

import pytest
import allure
import logging
from typing import Any, Dict, List

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 测试固件
@pytest.fixture
def setup_data() -> Dict[str, Any]:
    """测试数据固件"""
    return {
        "username": "test_user",
        "password": "test_password",
        "email": "test@example.com",
    }


@pytest.fixture
def setup_environment() -> Dict[str, Any]:
    """测试环境固件"""
    with allure.step("设置测试环境"):
        env = {"base_url": "https://api.example.com", "timeout": 30, "retry_count": 3}
        logger.info(f"测试环境: {env}")
        return env


# 测试类
@allure.epic("用户管理")
@allure.feature("用户认证")
class TestUserAuthentication:
    """用户认证测试"""

    @allure.story("用户登录")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("""
    测试用户登录功能：
    1. 输入有效的用户名和密码
    2. 验证登录成功
    3. 检查返回的令牌
    """)
    def test_login_success(self, setup_data: Dict, setup_environment: Dict):
        """测试成功登录"""
        with allure.step("准备测试数据"):
            username = setup_data["username"]
            password = setup_data["password"]
            logger.info(f"测试用户: {username}")

        with allure.step("执行登录操作"):
            # 模拟登录逻辑
            result = self._login(username, password)

            # 添加附件
            allure.attach(
                f"登录请求: username={username}, password={password}",
                name="登录请求",
                attachment_type=allure.attachment_type.TEXT,
            )

            allure.attach(
                str(result),
                name="登录响应",
                attachment_type=allure.attachment_type.JSON,
            )

        with allure.step("验证登录结果"):
            assert result["success"] is True, "登录应该成功"
            assert "token" in result, "响应应该包含令牌"
            assert len(result["token"]) > 0, "令牌不应该为空"

            logger.info(f"登录成功，令牌: {result['token'][:10]}...")

    @allure.story("用户登录")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_failure(self, setup_data: Dict):
        """测试登录失败"""
        with allure.step("使用错误密码"):
            username = setup_data["username"]
            wrong_password = "wrong_password"

            result = self._login(username, wrong_password)

            allure.attach(
                f"使用错误密码尝试登录: {username}/{wrong_password}",
                name="登录尝试",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("验证失败响应"):
            assert result["success"] is False, "登录应该失败"
            assert "error" in result, "响应应该包含错误信息"
            assert result["error"] == "Invalid credentials", "错误信息不匹配"

    @allure.story("用户注册")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize(
        "user_data",
        [
            {"username": "user1", "email": "user1@example.com"},
            {"username": "user2", "email": "user2@example.com"},
            {"username": "user3", "email": "user3@example.com"},
        ],
    )
    def test_user_registration(self, user_data: Dict):
        """测试用户注册（参数化测试）"""
        with allure.step(f"注册用户 {user_data['username']}"):
            result = self._register_user(user_data)

            allure.attach(
                str(user_data),
                name="注册数据",
                attachment_type=allure.attachment_type.JSON,
            )

        with allure.step("验证注册结果"):
            assert result["success"] is True, "注册应该成功"
            assert result["user"]["username"] == user_data["username"]
            assert result["user"]["email"] == user_data["email"]

    # 辅助方法
    def _login(self, username: str, password: str) -> Dict[str, Any]:
        """模拟登录逻辑"""
        # 在实际项目中，这里会是真实的登录逻辑
        if password == "test_password":
            return {
                "success": True,
                "token": "fake_jwt_token_1234567890",
                "user": {"username": username, "role": "user"},
            }
        else:
            return {"success": False, "error": "Invalid credentials"}

    def _register_user(self, user_data: Dict) -> Dict[str, Any]:
        """模拟用户注册"""
        return {
            "success": True,
            "user": {"id": 123, **user_data, "created_at": "2025-02-09T10:30:00Z"},
        }


# 函数测试
@allure.feature("工具函数")
class TestUtilityFunctions:
    """工具函数测试"""

    @allure.story("字符串处理")
    @allure.severity(allure.severity_level.MINOR)
    def test_string_operations(self):
        """测试字符串操作"""
        test_string = "Hello, World!"

        with allure.step("测试字符串长度"):
            assert len(test_string) == 13

        with allure.step("测试字符串包含"):
            assert "Hello" in test_string
            assert "World" in test_string

        with allure.step("测试字符串分割"):
            parts = test_string.split(", ")
            assert len(parts) == 2
            assert parts[0] == "Hello"
            assert parts[1] == "World!"

    @allure.story("数学运算")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (1, 2, 3),
            (0, 0, 0),
            (-1, 1, 0),
            (100, 200, 300),
        ],
    )
    def test_addition(self, a: int, b: int, expected: int):
        """测试加法运算"""
        result = a + b
        assert result == expected, f"{a} + {b} 应该等于 {expected}"


# 异常测试
@allure.feature("异常处理")
class TestExceptionHandling:
    """异常处理测试"""

    @allure.story("输入验证")
    @allure.severity(allure.severity_level.NORMAL)
    def test_invalid_input(self):
        """测试无效输入处理"""
        with allure.step("测试空输入"):
            with pytest.raises(ValueError) as exc_info:
                self._process_input("")

            assert str(exc_info.value) == "输入不能为空"

        with allure.step("测试 None 输入"):
            with pytest.raises(ValueError) as exc_info:
                self._process_input(None)

            assert "输入不能为 None" in str(exc_info.value)

    def _process_input(self, input_data: Any) -> Any:
        """模拟输入处理"""
        if input_data is None:
            raise ValueError("输入不能为 None")
        if not input_data:
            raise ValueError("输入不能为空")
        return input_data.upper()


# 测试配置
def pytest_configure(config):
    """pytest 配置钩子"""
    # 添加自定义标记
    config.addinivalue_line("markers", "slow: 标记为慢速测试（运行时间较长）")
    config.addinivalue_line("markers", "integration: 标记为集成测试（需要外部服务）")


@pytest.fixture(autouse=True)
def log_test_execution(request):
    """自动记录测试执行日志"""
    test_name = request.node.name
    logger.info(f"开始测试: {test_name}")

    yield

    logger.info(f"结束测试: {test_name}")


if __name__ == "__main__":
    # 直接运行此文件时执行测试
    pytest.main([__file__, "-v", "--alluredir=allure-results"])
