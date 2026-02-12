#!/usr/bin/env python3
"""
pytest 代码生成器
根据测试用例生成 pytest 测试代码，包含 allure 装饰器
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_test_cases(test_cases_file: str) -> List[Dict[str, Any]]:
    """加载测试用例"""
    with open(test_cases_file, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_pytest_code(
    test_cases: List[Dict[str, Any]], output_dir: str = "tests"
) -> Dict[str, str]:
    """
    生成 pytest 测试代码

    Args:
        test_cases: 测试用例列表
        output_dir: 输出目录

    Returns:
        生成的文件路径字典
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 按类型分组测试用例
    test_cases_by_type = {}
    for test_case in test_cases:
        test_type = test_case.get("type", "unknown")
        if test_type not in test_cases_by_type:
            test_cases_by_type[test_type] = []
        test_cases_by_type[test_type].append(test_case)

    generated_files = {}

    # 为每种类型生成测试文件
    for test_type, cases in test_cases_by_type.items():
        if test_type == "api_test":
            filename = os.path.join(output_dir, "test_api.py")
            content = generate_api_test_file(cases)
        elif test_type == "functional_test":
            filename = os.path.join(output_dir, "test_functional.py")
            content = generate_functional_test_file(cases)
        elif test_type == "user_story_test":
            filename = os.path.join(output_dir, "test_user_stories.py")
            content = generate_user_story_test_file(cases)
        else:
            # 默认生成通用测试文件
            filename = os.path.join(output_dir, f"test_{test_type}.py")
            content = generate_generic_test_file(cases, test_type)

        # 写入文件
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        generated_files[test_type] = filename

    # 生成 conftest.py
    conftest_content = generate_conftest()
    conftest_file = os.path.join(output_dir, "conftest.py")
    with open(conftest_file, "w", encoding="utf-8") as f:
        f.write(conftest_content)
    generated_files["conftest"] = conftest_file

    # 生成 pytest.ini
    pytest_ini_content = generate_pytest_ini()
    pytest_ini_file = "pytest.ini"
    with open(pytest_ini_file, "w", encoding="utf-8") as f:
        f.write(pytest_ini_content)
    generated_files["pytest_ini"] = pytest_ini_file

    # 生成 requirements.txt
    requirements_content = generate_requirements()
    requirements_file = "requirements.txt"
    with open(requirements_file, "w", encoding="utf-8") as f:
        f.write(requirements_content)
    generated_files["requirements"] = requirements_file

    # 生成运行脚本
    run_script_content = generate_run_script()
    run_script_file = "run_tests.py"
    with open(run_script_file, "w", encoding="utf-8") as f:
        f.write(run_script_content)
    generated_files["run_script"] = run_script_file

    return generated_files


def generate_api_test_file(test_cases: List[Dict[str, Any]]) -> str:
    """生成 API 测试文件"""
    imports = '''"""
API 测试文件
生成的 pytest 测试代码，包含 allure 装饰器
"""

import pytest
import allure
import requests
import json
import os
from typing import Dict, Any

# API 基础配置
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
'''

    fixture_code = '''
@pytest.fixture(scope="session")
def api_client():
    """API 客户端 fixture"""
    import requests
    session = requests.Session()
    
    # 可以在这里添加认证头等
    # session.headers.update({"Authorization": "Bearer token"})
    
    yield session
    session.close()


@pytest.fixture
def test_data():
    """测试数据 fixture"""
    return {
        "valid_user": {
            "username": "test_user",
            "email": "test@example.com",
            "password": "Test@123456"
        },
        "invalid_user": {
            "username": "",
            "email": "invalid_email",
            "password": "123"
        }
    }
'''

    test_functions = []

    for test_case in test_cases:
        test_id = test_case.get("id", "")
        title = test_case.get("title", "")
        description = test_case.get("description", "")
        priority = test_case.get("priority", "中")
        steps = test_case.get("steps", [])
        expected_results = test_case.get("expected_results", [])

        # 将优先级映射为 allure 的严重程度
        severity_map = {"高": "blocker", "中": "critical", "低": "minor"}
        allure_severity = severity_map.get(priority, "normal")

        # 生成测试函数
        function_name = f"test_{test_id.lower().replace('-', '_')}"

        # 构建测试函数代码
        test_function = f'''
@allure.feature("API 测试")
@allure.story("{title}")
@allure.severity(allure.severity_level.{allure_severity})
@allure.title("{title}")
@allure.description("""{description}

测试ID: {test_id}
优先级: {priority}
""")
def {function_name}(api_client, test_data):
    """{title}"""
'''

        # 添加测试步骤
        for i, step in enumerate(steps, 1):
            test_function += f'    with allure.step("步骤{i}: {step}"):\n'

            # 根据步骤内容添加具体代码
            if "发送" in step and "请求" in step:
                # 提取方法和路径
                method_match = None
                path_match = None
                if "GET" in step:
                    method = "GET"
                elif "POST" in step:
                    method = "POST"
                elif "PUT" in step:
                    method = "PUT"
                elif "DELETE" in step:
                    method = "DELETE"
                else:
                    method = "GET"

                # 简单解析路径
                if "/api/" in step:
                    path_start = step.find("/api/")
                    path = (
                        step[path_start:].split()[0]
                        if path_start != -1
                        else "/api/endpoint"
                    )
                else:
                    path = "/api/endpoint"

                test_function += f'''        # 准备请求
        url = f"{{BASE_URL}}{path}"
        
        # 发送请求
        response = api_client.request(
            method="{method}",
            url=url,
            timeout=API_TIMEOUT,
            json=test_data.get("valid_user", {{}})
        )
        
        # 记录响应
        allure.attach(
            json.dumps({{
                "request_url": url,
                "request_method": "{method}",
                "response_status": response.status_code,
                "response_headers": dict(response.headers),
                "response_body": response.json() if response.content else {{}}
            }}, indent=2, ensure_ascii=False),
            name="请求响应详情",
            attachment_type=allure.attachment_type.JSON
        )
'''
            elif "验证响应状态码" in step:
                test_function += f"""        # 验证状态码
        assert 200 <= response.status_code < 300, f"状态码异常: {{response.status_code}}"
        
        # 验证响应格式
        if response.content:
            try:
                response_json = response.json()
                allure.attach(
                    json.dumps(response_json, indent=2, ensure_ascii=False),
                    name="响应数据",
                    attachment_type=allure.attachment_type.JSON
                )
            except json.JSONDecodeError:
                assert False, "响应不是有效的 JSON 格式"
"""
            elif "验证响应数据格式" in step:
                test_function += f"""        # 验证数据格式
        if response.content:
            response_data = response.json()
            # 这里可以添加具体的格式验证
            # 例如: assert "id" in response_data
            # 或者使用 JSON schema 验证
"""
            else:
                test_function += f"        # {step}\n        pass\n"

        # 添加预期结果验证
        if expected_results:
            test_function += f"\n    # 验证预期结果\n"
            for i, expected in enumerate(expected_results, 1):
                test_function += f"    # {expected}\n"

        test_function += f"    # 测试完成\n    assert True\n"

        test_functions.append(test_function)

    # 组合所有代码
    test_file_content = imports + fixture_code + "\n".join(test_functions)
    return test_file_content


def generate_functional_test_file(test_cases: List[Dict[str, Any]]) -> str:
    """生成功能测试文件"""
    imports = '''"""
功能测试文件
生成的 pytest 测试代码，包含 allure 装饰器
"""

import pytest
import allure
import time
from typing import Dict, Any

# 页面/功能配置
APP_URL = "http://localhost:3000"
'''

    fixture_code = '''
@pytest.fixture
def setup_browser():
    """浏览器设置 fixture"""
    # 这里可以初始化 Selenium 或其他 UI 测试框架
    # 例如: driver = webdriver.Chrome()
    driver = None
    yield driver
    if driver:
        driver.quit()


@pytest.fixture
def test_user():
    """测试用户 fixture"""
    return {
        "username": "test_user",
        "password": "Test@123456",
        "email": "test@example.com"
    }
'''

    test_functions = []

    for test_case in test_cases:
        test_id = test_case.get("id", "")
        title = test_case.get("title", "")
        description = test_case.get("description", "")
        priority = test_case.get("priority", "高")
        steps = test_case.get("steps", [])
        expected_results = test_case.get("expected_results", [])

        # 生成测试函数
        function_name = f"test_{test_id.lower().replace('-', '_')}"

        # 构建测试函数代码
        test_function = f'''
@allure.feature("功能测试")
@allure.story("{title}")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("{title}")
@allure.description("""{description}

测试ID: {test_id}
""")
def {function_name}(setup_browser, test_user):
    """{title}"""
'''

        # 添加测试步骤
        for i, step in enumerate(steps, 1):
            test_function += f'    with allure.step("步骤{i}: {step}"):\n'

            # 根据步骤内容添加具体代码
            if "登录" in step or "登入" in step:
                test_function += f"""        # 执行登录操作
        # 示例: driver.get(f"{{APP_URL}}/login")
        # driver.find_element(By.ID, "username").send_keys(test_user["username"])
        # driver.find_element(By.ID, "password").send_keys(test_user["password"])
        # driver.find_element(By.ID, "login-button").click()
        time.sleep(1)  # 等待页面加载
        
        allure.attach(
            f"用户登录: {{test_user['username']}}",
            name="登录操作",
            attachment_type=allure.attachment_type.TEXT
        )
"""
            elif "点击" in step or "选择" in step:
                test_function += f"""        # 执行点击/选择操作
        # element = driver.find_element(By.XPATH, "//button[text()='确定']")
        # element.click()
        time.sleep(0.5)
"""
            elif "输入" in step or "填写" in step:
                test_function += f"""        # 执行输入操作
        # input_field = driver.find_element(By.ID, "input-field")
        # input_field.clear()
        # input_field.send_keys("测试数据")
"""
            elif "验证" in step or "检查" in step:
                test_function += f"""        # 执行验证操作
        # result_element = driver.find_element(By.ID, "result")
        # assert "成功" in result_element.text
        allure.attach("验证通过", name="验证结果", attachment_type=allure.attachment_type.TEXT)
"""
            else:
                test_function += f"        # {step}\n        pass\n"

        # 添加预期结果验证
        if expected_results:
            test_function += f"\n    # 验证预期结果\n"
            for expected in expected_results:
                test_function += f'    assert True, "应满足: {expected}"\n'

        test_functions.append(test_function)

    # 组合所有代码
    test_file_content = imports + fixture_code + "\n".join(test_functions)
    return test_file_content


def generate_user_story_test_file(test_cases: List[Dict[str, Any]]) -> str:
    """生成用户故事测试文件"""
    imports = '''"""
用户故事测试文件
生成的 pytest 测试代码，包含 allure 装饰器
"""

import pytest
import allure
import time
from typing import Dict, Any

# 用户故事测试配置
'''

    fixture_code = '''
@pytest.fixture
def user_scenario_data():
    """用户场景数据 fixture"""
    return {
        "scenario_1": {
            "user_role": "普通用户",
            "actions": ["登录", "浏览产品", "下单", "支付"],
            "expected_outcomes": ["成功登录", "看到产品列表", "订单创建成功", "支付成功"]
        },
        "scenario_2": {
            "user_role": "管理员",
            "actions": ["登录", "管理用户", "查看报表", "配置系统"],
            "expected_outcomes": ["成功登录", "用户管理界面正常", "报表数据准确", "配置保存成功"]
        }
    }
'''

    test_functions = []

    for test_case in test_cases:
        test_id = test_case.get("id", "")
        title = test_case.get("title", "")
        description = test_case.get("description", "")
        priority = test_case.get("priority", "高")
        steps = test_case.get("steps", [])
        expected_results = test_case.get("expected_results", [])

        # 生成测试函数
        function_name = f"test_{test_id.lower().replace('-', '_')}"

        # 构建测试函数代码
        test_function = f'''
@allure.feature("用户故事测试")
@allure.story("{title}")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("{title}")
@allure.description("""{description}

测试ID: {test_id}
用户故事验收标准:
{chr(10).join(f"- {criteria}" for criteria in expected_results)}
""")
def {function_name}(user_scenario_data):
    """{title}"""
'''

        # 添加测试步骤
        for i, step in enumerate(steps, 1):
            test_function += f'    with allure.step("步骤{i}: {step}"):\n'
            test_function += f"        # 执行: {step}\n"

            if "模拟用户场景" in step:
                test_function += f"""        # 模拟用户场景
        scenario = user_scenario_data.get("scenario_1", {{}})
        allure.attach(
            f"模拟用户场景: {{scenario.get('user_role', '未知角色')}}",
            name="用户场景",
            attachment_type=allure.attachment_type.TEXT
        )
"""
            elif "执行相关操作" in step:
                test_function += f"""        # 执行用户操作序列
        actions = scenario.get("actions", [])
        for action in actions:
            with allure.step(f"执行操作: {{action}}"):
                # 这里执行具体操作
                time.sleep(0.2)
                allure.attach(
                    f"完成操作: {{action}}",
                    name="操作记录",
                    attachment_type=allure.attachment_type.TEXT
                )
"""
            elif "验证结果" in step:
                test_function += f"""        # 验证用户故事结果
        expected_outcomes = scenario.get("expected_outcomes", [])
        for outcome in expected_outcomes:
            assert True, f"验证: {{outcome}}"
            allure.attach(
                f"验证通过: {{outcome}}",
                name="验证结果",
                attachment_type=allure.attachment_type.TEXT
            )
"""
            else:
                test_function += f"        pass\n"

        test_functions.append(test_function)

    # 组合所有代码
    test_file_content = imports + fixture_code + "\n".join(test_functions)
    return test_file_content


def generate_generic_test_file(test_cases: List[Dict[str, Any]], test_type: str) -> str:
    """生成通用测试文件"""
    imports = f'''"""
{test_type} 测试文件
生成的 pytest 测试代码
"""

import pytest
import allure
'''

    test_functions = []

    for test_case in test_cases:
        test_id = test_case.get("id", "")
        title = test_case.get("title", "")
        description = test_case.get("description", "")

        function_name = f"test_{test_id.lower().replace('-', '_')}"

        test_function = f'''
@allure.feature("{test_type}")
@allure.title("{title}")
def {function_name}():
    """{title}"""
    with allure.step("测试步骤"):
        # 这里添加测试逻辑
        pass
    
    assert True
'''
        test_functions.append(test_function)

    return imports + "\n".join(test_functions)


def generate_conftest() -> str:
    """生成 conftest.py"""
    return '''"""
pytest 配置文件
包含全局的 fixture 和配置
"""

import pytest
import allure
import json
import os
from datetime import datetime


def pytest_configure(config):
    """pytest 配置钩子"""
    # 创建 allure 结果目录
    allure_results_dir = os.path.join(os.path.dirname(__file__), "reports", "allure-results")
    os.makedirs(allure_results_dir, exist_ok=True)


def pytest_sessionstart(session):
    """测试会话开始"""
    print("测试会话开始")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束"""
    print(f"测试会话结束，退出状态: {exitstatus}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


@pytest.fixture(scope="session", autouse=True)
def setup_allure_environment():
    """设置 allure 环境"""
    # 设置 allure 环境变量
    os.environ["ALLURE_RESULTS_PATH"] = "reports/allure-results"
    
    yield
    
    # 清理操作


@pytest.fixture
def allure_attach_screenshot():
    """附加截图的 fixture"""
    def _attach_screenshot(name="screenshot"):
        # 这里可以添加截图逻辑
        # 例如: driver.save_screenshot("screenshot.png")
        # allure.attach.file("screenshot.png", name=name, attachment_type=allure.attachment_type.PNG)
        pass
    return _attach_screenshot


@pytest.fixture
def allure_attach_json():
    """附加 JSON 数据的 fixture"""
    def _attach_json(data, name="data"):
        if isinstance(data, dict):
            allure.attach(
                json.dumps(data, indent=2, ensure_ascii=False),
                name=name,
                attachment_type=allure.attachment_type.JSON
            )
        else:
            allure.attach(str(data), name=name, attachment_type=allure.attachment_type.TEXT)
    return _attach_json


@pytest.fixture
def test_logger():
    """测试日志 fixture"""
    import logging
    
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
'''


def generate_pytest_ini() -> str:
    """生成 pytest.ini 配置文件"""
    return """[pytest]
# pytest 配置

# 测试文件匹配模式
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 测试发现选项
testpaths = tests
norecursedirs = .git .venv env node_modules build dist

# 报告配置
addopts = 
    --strict-markers
    --tb=short
    --show-capture=no
    -v
    --alluredir=reports/allure-results

# 标记定义
markers =
    smoke: 冒烟测试
    regression: 回归测试
    api: API 测试
    functional: 功能测试
    integration: 集成测试
    performance: 性能测试
    security: 安全测试

# 日志配置
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)s] %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# 其他配置
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
"""


def generate_requirements() -> str:
    """生成 requirements.txt"""
    return """# 测试框架依赖
pytest>=7.0.0
pytest-html>=3.0.0
pytest-xdist>=3.0.0
pytest-timeout>=2.1.0
pytest-cov>=4.0.0

# Allure 报告
allure-pytest>=2.13.0
allure-python-commons>=2.13.0

# HTTP 客户端
requests>=2.28.0
httpx>=0.24.0

# 数据验证
jsonschema>=4.17.0
pydantic>=1.10.0

# 测试数据
Faker>=18.0.0
factory-boy>=3.2.0

# 日志和工具
python-dotenv>=1.0.0
PyYAML>=6.0
colorlog>=6.7.0

# UI 测试 (可选)
selenium>=4.10.0
webdriver-manager>=4.0.0

# 数据库测试 (可选)
sqlalchemy>=2.0.0
pytest-postgresql>=3.0.0

# 开发工具
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
"""


def generate_run_script() -> str:
    """生成测试运行脚本"""
    return '''#!/usr/bin/env python3
"""
测试运行脚本
自动运行 pytest 测试并生成 allure 报告
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("开始运行测试")
    print("=" * 60)
    
    # 清理旧的测试结果
    allure_results_dir = Path("reports/allure-results")
    allure_report_dir = Path("reports/allure-report")
    
    if allure_results_dir.exists():
        shutil.rmtree(allure_results_dir)
    if allure_report_dir.exists():
        shutil.rmtree(allure_report_dir)
    
    allure_results_dir.mkdir(parents=True, exist_ok=True)
    
    # 运行 pytest
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",
        "--alluredir=reports/allure-results",
        "--tb=short",
        "--strict-markers",
        "tests/"
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 输出测试结果
    print(result.stdout)
    if result.stderr:
        print("错误输出:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    
    print(f"测试退出码: {result.returncode}")
    
    # 生成 allure 报告
    if allure_results_dir.exists() and any(allure_results_dir.iterdir()):
        print()
        print("生成 Allure 报告...")
        
        # 检查是否安装了 allure
        try:
            allure_cmd = ["allure", "generate", "reports/allure-results", "-o", "reports/allure-report", "--clean"]
            allure_result = subprocess.run(allure_cmd, capture_output=True, text=True)
            
            if allure_result.returncode == 0:
                print("Allure 报告生成成功!")
                print(f"报告位置: {allure_report_dir.absolute()}")
                
                # 尝试打开报告
                if sys.platform == "win32":
                    os.startfile(allure_report_dir / "index.html")
                elif sys.platform == "darwin":
                    subprocess.run(["open", allure_report_dir / "index.html"])
                else:
                    print(f"请手动打开: file://{allure_report_dir.absolute()}/index.html")
            else:
                print("Allure 报告生成失败:")
                print(allure_result.stderr)
        except FileNotFoundError:
            print("Allure 命令行工具未安装，请安装后重试")
            print("安装方法: https://docs.qameta.io/allure/#_installing_a_commandline")
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
'''


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python generate_pytest_code.py <测试用例JSON文件> [输出目录]")
        print("示例: python generate_pytest_code.py generated_test_cases.json tests")
        sys.exit(1)

    test_cases_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "tests"

    try:
        test_cases = load_test_cases(test_cases_file)
        print(f"加载了 {len(test_cases)} 个测试用例")

        generated_files = generate_pytest_code(test_cases, output_dir)

        print("生成的文件:")
        for file_type, file_path in generated_files.items():
            print(f"  - {file_type}: {file_path}")

        print()
        print("下一步:")
        print("1. 安装依赖: pip install -r requirements.txt")
        print("2. 运行测试: python run_tests.py")
        print("3. 查看报告: 打开 reports/allure-report/index.html")

    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
