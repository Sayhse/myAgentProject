"""
pytest 配置文件模板
包含全局的 fixture 和配置
"""

import pytest
import allure  # type: ignore
import json
import os
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Optional
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 测试配置
TEST_CONFIG = {
    "api": {
        "base_url": os.getenv("API_BASE_URL", "http://localhost:8080"),
        "timeout": int(os.getenv("API_TIMEOUT", "30")),
        "retry_count": int(os.getenv("API_RETRY_COUNT", "3")),
    },
    "ui": {
        "base_url": os.getenv("UI_BASE_URL", "http://localhost:3000"),
        "browser": os.getenv("BROWSER", "chrome"),
        "headless": os.getenv("HEADLESS", "true").lower() == "true",
    },
    "database": {
        "url": os.getenv(
            "DATABASE_URL", "postgresql://user:pass@localhost:5432/test_db"
        ),
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
    },
}


def pytest_configure(config):
    """pytest 配置钩子 - 在测试开始前执行"""
    # 设置 allure 环境变量
    allure_results_dir = PROJECT_ROOT / "reports" / "allure-results"
    allure_results_dir.mkdir(parents=True, exist_ok=True)

    os.environ["ALLURE_RESULTS_PATH"] = str(allure_results_dir)

    # 添加自定义标记说明
    config.addinivalue_line("markers", "smoke: 冒烟测试 - 快速验证核心功能")
    config.addinivalue_line("markers", "regression: 回归测试 - 验证已有功能")
    config.addinivalue_line("markers", "api: API 测试")
    config.addinivalue_line("markers", "ui: UI 测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "performance: 性能测试")
    config.addinivalue_line("markers", "security: 安全测试")
    config.addinivalue_line("markers", "slow: 慢速测试 - 可能需要较长时间")

    print(f"测试配置完成")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Allure 结果目录: {allure_results_dir}")


def pytest_sessionstart(session):
    """测试会话开始钩子"""
    print("测试会话开始")

    # 清理旧的测试结果（可选）
    if os.getenv("CLEAN_RESULTS", "true").lower() == "true":
        allure_results = PROJECT_ROOT / "reports" / "allure-results"
        if allure_results.exists():
            # 只清理超过7天的文件
            seven_days_ago = datetime.now().timestamp() - 7 * 24 * 60 * 60
            for file in allure_results.glob("*"):
                if file.stat().st_mtime < seven_days_ago:
                    file.unlink()

    # 记录环境信息
    env_info = {
        "python_version": os.getenv("PYTHON_VERSION", "unknown"),
        "pytest_version": pytest.__version__,
        "allure_version": "2.24.0",  # 根据实际版本调整
        "test_config": TEST_CONFIG,
        "start_time": datetime.now().isoformat(),
    }

    env_file = PROJECT_ROOT / "reports" / "allure-results" / "environment.json"
    with open(env_file, "w", encoding="utf-8") as f:
        json.dump(env_info, f, ensure_ascii=False, indent=2)


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束钩子"""
    print(f"测试会话结束，退出状态: {exitstatus}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 生成会话摘要
    summary = {
        "exit_status": exitstatus,
        "end_time": datetime.now().isoformat(),
        "total_tests": session.testscollected
        if hasattr(session, "testscollected")
        else 0,
        "test_root": str(PROJECT_ROOT),
    }

    summary_file = PROJECT_ROOT / "reports" / "session_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """终端摘要钩子"""
    # 添加自定义摘要信息
    if terminalreporter.stats.get("passed"):
        terminalreporter.write_sep("=", "测试通过统计", green=True)
        terminalreporter.write_line(
            f"通过测试: {len(terminalreporter.stats['passed'])}"
        )

    if terminalreporter.stats.get("failed"):
        terminalreporter.write_sep("=", "测试失败统计", red=True)
        terminalreporter.write_line(
            f"失败测试: {len(terminalreporter.stats['failed'])}"
        )

    if terminalreporter.stats.get("skipped"):
        terminalreporter.write_sep("=", "测试跳过统计", yellow=True)
        terminalreporter.write_line(
            f"跳过测试: {len(terminalreporter.stats['skipped'])}"
        )


@pytest.fixture(scope="session", autouse=True)
def setup_allure_environment():
    """设置 allure 环境 - 会话级自动使用的 fixture"""
    # 设置 allure 环境变量
    os.environ["ALLURE_NO_OPENER"] = "true"  # 禁止自动打开报告

    # 创建必要的目录
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    allure_results_dir = reports_dir / "allure-results"
    allure_results_dir.mkdir(exist_ok=True)

    allure_report_dir = reports_dir / "allure-report"
    allure_report_dir.mkdir(exist_ok=True)

    screenshots_dir = reports_dir / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    logs_dir = reports_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    yield

    # 清理临时文件（如果需要）
    pass


@pytest.fixture(scope="session")
def logger():
    """测试日志 fixture"""
    import logging

    # 创建 logger
    logger = logging.getLogger("test_framework")
    logger.setLevel(logging.DEBUG)

    # 清除已有的 handler
    logger.handlers.clear()

    # 创建控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建文件 handler
    log_file = PROJECT_ROOT / "reports" / "logs" / "test_execution.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # 创建格式器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 添加 handler
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


@pytest.fixture
def test_data():
    """测试数据 fixture - 函数级"""
    return {
        "users": {
            "admin": {"username": "admin", "password": "Admin@123456", "role": "admin"},
            "regular_user": {
                "username": "test_user",
                "password": "Test@123456",
                "role": "user",
            },
        },
        "products": {
            "featured": {"id": 1, "name": "特色产品", "price": 199.99},
            "discounted": {
                "id": 2,
                "name": "折扣产品",
                "price": 99.99,
                "original_price": 149.99,
            },
        },
    }


@pytest.fixture(scope="class")
def api_client():
    """API 客户端 fixture - 类级"""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    # 创建会话
    session = requests.Session()

    # 配置重试策略
    retry_strategy = Retry(
        total=TEST_CONFIG["api"]["retry_count"],
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # 设置默认头部
    session.headers.update(
        {
            "User-Agent": "pytest-test-framework/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )

    # 设置超时
    session.request = lambda method, url, **kwargs: requests.Session.request(  # type: ignore
        session, method, url, timeout=TEST_CONFIG["api"]["timeout"], **kwargs
    )

    yield session

    # 清理
    session.close()


@pytest.fixture
def allure_attach_screenshot():
    """附加截图的 fixture"""

    def _attach_screenshot(driver=None, name="screenshot"):
        if driver:
            # 使用 selenium 截图
            screenshot_path = (
                PROJECT_ROOT
                / "reports"
                / "screenshots"
                / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            driver.save_screenshot(str(screenshot_path))
            allure.attach.file(
                str(screenshot_path),
                name=name,
                attachment_type=allure.attachment_type.PNG,
            )
        else:
            # 如果没有 driver，附加一个占位符
            allure.attach(
                "截图不可用（无 WebDriver）",
                name=name,
                attachment_type=allure.attachment_type.TEXT,
            )

    return _attach_screenshot


@pytest.fixture
def allure_attach_json():
    """附加 JSON 数据的 fixture"""

    def _attach_json(data, name="data"):
        if isinstance(data, (dict, list)):
            formatted_data = json.dumps(data, ensure_ascii=False, indent=2)
            allure.attach(
                formatted_data, name=name, attachment_type=allure.attachment_type.JSON
            )
        else:
            allure.attach(
                str(data), name=name, attachment_type=allure.attachment_type.TEXT
            )

    return _attach_json


@pytest.fixture
def allure_attach_text():
    """附加文本数据的 fixture"""

    def _attach_text(text, name="text"):
        allure.attach(str(text), name=name, attachment_type=allure.attachment_type.TEXT)

    return _attach_text


@pytest.fixture
def allure_attach_html():
    """附加 HTML 数据的 fixture"""

    def _attach_html(html, name="html"):
        allure.attach(html, name=name, attachment_type=allure.attachment_type.HTML)

    return _attach_html


@pytest.fixture(scope="function")
def temp_directory():
    """临时目录 fixture - 函数级"""
    temp_dir = tempfile.mkdtemp(prefix="pytest_temp_")
    yield Path(temp_dir)
    # 清理临时目录
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_requests(monkeypatch):
    """模拟 requests 的 fixture"""
    from unittest.mock import Mock

    def _mock_response(status_code=200, json_data=None, text=None, headers=None):
        mock_resp = Mock()
        mock_resp.status_code = status_code
        mock_resp.headers = headers or {}

        if json_data:
            mock_resp.json.return_value = json_data
            mock_resp.text = json.dumps(json_data)
        elif text:
            mock_resp.text = text
            mock_resp.json.side_effect = ValueError("No JSON data")
        else:
            mock_resp.text = ""
            mock_resp.json.side_effect = ValueError("No JSON data")

        return mock_resp

    class MockSession:
        def __init__(self):
            self.headers = {}
            self.request = Mock(return_value=_mock_response())
            self.get = Mock(return_value=_mock_response())
            self.post = Mock(return_value=_mock_response())
            self.put = Mock(return_value=_mock_response())
            self.delete = Mock(return_value=_mock_response())
            self.patch = Mock(return_value=_mock_response())

        def close(self):
            pass

    mock_session = MockSession()
    monkeypatch.setattr("requests.Session", lambda: mock_session)

    return mock_session


@pytest.fixture
def db_connection():
    """数据库连接 fixture（示例）"""
    # 这里应该创建实际的数据库连接
    # 例如: connection = psycopg2.connect(TEST_CONFIG["database"]["url"])
    connection = None

    yield connection

    if connection:
        connection.close()


# 钩子函数 - 测试失败时执行
@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """测试报告生成钩子"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        # 测试失败时执行额外操作
        if hasattr(item, "funcargs") and "driver" in item.funcargs:
            driver = item.funcargs["driver"]
            try:
                # 尝试截图
                screenshot_path = (
                    PROJECT_ROOT
                    / "reports"
                    / "screenshots"
                    / f"failure_{item.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                )
                driver.save_screenshot(str(screenshot_path))

                if screenshot_path.exists():
                    allure.attach.file(
                        str(screenshot_path),
                        name="failure_screenshot",
                        attachment_type=allure.attachment_type.PNG,
                    )
            except Exception as e:
                print(f"截图失败: {e}")

        # 记录失败信息
        failure_info = {
            "test_name": item.name,
            "failure_time": datetime.now().isoformat(),
            "failure_message": str(report.longrepr)
            if report.longrepr
            else "Unknown error",
            "node_id": item.nodeid,
        }

        failure_log = PROJECT_ROOT / "reports" / "logs" / "failures.jsonl"
        with open(failure_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(failure_info, ensure_ascii=False) + "\n")


# 自定义命令行选项
def pytest_addoption(parser):
    """添加自定义命令行选项"""
    parser.addoption(
        "--env", action="store", default="test", help="测试环境: test, staging, prod"
    )
    parser.addoption(
        "--browser",
        action="store",
        default="chrome",
        help="浏览器: chrome, firefox, safari, edge",
    )
    parser.addoption(
        "--headless", action="store_true", default=True, help="无头模式运行浏览器"
    )
    parser.addoption("--slow", action="store_true", default=False, help="运行慢速测试")


@pytest.fixture(scope="session")
def env(request):
    """环境配置 fixture"""
    return request.config.getoption("--env")


@pytest.fixture(scope="session")
def browser_type(request):
    """浏览器类型 fixture"""
    return request.config.getoption("--browser")


@pytest.fixture(scope="session")
def headless(request):
    """无头模式 fixture"""
    return request.config.getoption("--headless")


# 测试跳过条件
def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    skip_slow = pytest.mark.skip(reason="跳过慢速测试")
    skip_prod = pytest.mark.skip(reason="跳过生产环境测试")

    for item in items:
        # 跳过标记为 slow 的测试（除非指定了 --slow）
        if "slow" in item.keywords and not config.getoption("--slow"):
            item.add_marker(skip_slow)

        # 根据环境跳过测试
        env = config.getoption("--env")
        if "prod_only" in item.keywords and env != "prod":
            item.add_marker(skip_prod)
        elif "non_prod" in item.keywords and env == "prod":
            item.add_marker(skip_prod)
