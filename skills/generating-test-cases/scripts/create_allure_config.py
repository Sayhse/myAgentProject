#!/usr/bin/env python3
"""
Allure 配置生成器
创建 allure 报告框架的配置文件和目录结构
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any


def create_allure_structure(base_dir: str = ".") -> Dict[str, str]:
    """
    创建 allure 目录结构和配置文件

    Args:
        base_dir: 基础目录

    Returns:
        创建的文件路径字典
    """
    created_files = {}

    # 创建目录结构
    directories = [
        "reports/allure-results",
        "reports/allure-report",
        "reports/html",
        "reports/junit",
        "reports/screenshots",
        "reports/logs",
        "allure/plugins",
        "allure/categories",
        "allure/environment",
    ]

    for directory in directories:
        dir_path = os.path.join(base_dir, directory)
        os.makedirs(dir_path, exist_ok=True)
        print(f"创建目录: {dir_path}")

    # 生成 allure.yml 配置文件
    allure_config = generate_allure_config()
    allure_config_path = os.path.join(base_dir, "allure.yml")
    with open(allure_config_path, "w", encoding="utf-8") as f:
        yaml.dump(allure_config, f, allow_unicode=True, default_flow_style=False)
    created_files["allure_config"] = allure_config_path

    # 生成 categories.json 分类配置
    categories = generate_categories()
    categories_path = os.path.join(base_dir, "allure/categories/categories.json")
    with open(categories_path, "w", encoding="utf-8") as f:
        import json

        json.dump(categories, f, ensure_ascii=False, indent=2)
    created_files["categories"] = categories_path

    # 生成 environment.properties 环境配置
    environment = generate_environment()
    environment_path = os.path.join(
        base_dir, "allure/environment/environment.properties"
    )
    with open(environment_path, "w", encoding="utf-8") as f:
        f.write(environment)
    created_files["environment"] = environment_path

    # 生成 allure.properties 属性文件
    allure_properties = generate_allure_properties()
    allure_properties_path = os.path.join(base_dir, "allure.properties")
    with open(allure_properties_path, "w", encoding="utf-8") as f:
        f.write(allure_properties)
    created_files["allure_properties"] = allure_properties_path

    # 生成 generate_report.py 报告生成脚本
    report_script = generate_report_script()
    report_script_path = os.path.join(base_dir, "generate_report.py")
    with open(report_script_path, "w", encoding="utf-8") as f:
        f.write(report_script)
    created_files["report_script"] = report_script_path

    # 生成 README.md 说明文件
    readme = generate_readme()
    readme_path = os.path.join(base_dir, "reports/README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme)
    created_files["readme"] = readme_path

    return created_files


def generate_allure_config() -> Dict[str, Any]:
    """生成 allure.yml 配置文件"""
    return {
        "title": "测试报告",
        "report": {
            "language": "zh-CN",
            "plugins": [
                "behaviors",
                "packages",
                "screen-diff",
                "xctest",
                "jira",
                "xray",
                "testops",
            ],
            "categories": "allure/categories/categories.json",
            "environment": "allure/environment/environment.properties",
        },
        "export": {
            "path": "reports/allure-report",
            "clean": True,
            "report": {"name": "测试执行报告", "language": "zh-CN"},
        },
        "plugins": {
            "jira": {"url": "https://jira.example.com", "project": "PROJ"},
            "testops": {
                "url": "https://testops.example.com",
                "project": "test-project",
            },
        },
    }


def generate_categories() -> list:
    """生成测试分类配置"""
    return [
        {
            "name": "产品缺陷",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*AssertionError.*|.*Exception.*",
            "traceRegex": ".*",
        },
        {
            "name": "测试缺陷",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*TimeoutException.*|.*ElementNotVisibleException.*",
            "traceRegex": ".*",
        },
        {
            "name": "环境问题",
            "matchedStatuses": ["broken"],
            "messageRegex": ".*ConnectionError.*|.*TimeoutError.*",
            "traceRegex": ".*",
        },
        {
            "name": "跳过测试",
            "matchedStatuses": ["skipped"],
            "messageRegex": ".*跳过.*|.*skip.*",
            "traceRegex": ".*",
        },
        {
            "name": "已知问题",
            "matchedStatuses": ["failed", "broken"],
            "messageRegex": ".*已知问题.*|.*known issue.*",
            "traceRegex": ".*",
        },
    ]


def generate_environment() -> str:
    """生成环境配置文件"""
    return """# 测试环境配置
environment=测试环境
browser=Chrome 120
platform=Windows 11
python.version=3.12.0
pytest.version=7.4.0
allure.version=2.24.0
api.base_url=http://localhost:8080
ui.base_url=http://localhost:3000
database.url=jdbc:postgresql://localhost:5432/test_db
test.data.path=test_data/
report.path=reports/allure-report/
"""


def generate_allure_properties() -> str:
    """生成 allure.properties 文件"""
    return """# Allure 配置属性
allure.results.directory=reports/allure-results
allure.report.directory=reports/allure-report
allure.issues.tracker.pattern=https://jira.example.com/browse/%s
allure.tests.management.pattern=https://testops.example.com/testcase/%s
allure.link.issue.pattern=https://jira.example.com/browse/%s
allure.link.tms.pattern=https://testops.example.com/testcase/%s

# 报告配置
allure.report.name=测试执行报告
allure.report.language=zh-CN
allure.report.remove.results=true

# 插件配置
allure.plugins.enabled=true
allure.plugins.behaviors.enabled=true
allure.plugins.packages.enabled=true
allure.plugins.screen.diff.enabled=true

# 分类配置
allure.categories.config=allure/categories/categories.json

# 环境配置
allure.environment.config=allure/environment/environment.properties
"""


def generate_report_script() -> str:
    """生成报告生成脚本"""
    return '''#!/usr/bin/env python3
"""
Allure 报告生成脚本
生成并打开 allure 测试报告
"""

import os
import sys
import subprocess
import webbrowser
from pathlib import Path
import argparse


def check_allure_installed() -> bool:
    """检查 allure 是否安装"""
    try:
        subprocess.run(["allure", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_allure_report(results_dir: str = "reports/allure-results", 
                          report_dir: str = "reports/allure-report") -> bool:
    """生成 allure 报告"""
    if not Path(results_dir).exists():
        print(f"错误: 测试结果目录不存在: {results_dir}")
        return False
    
    if not any(Path(results_dir).iterdir()):
        print(f"警告: 测试结果目录为空: {results_dir}")
        return False
    
    print(f"从 {results_dir} 生成 Allure 报告...")
    
    cmd = [
        "allure", "generate",
        results_dir,
        "-o", report_dir,
        "--clean"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Allure 报告生成成功!")
        print(f"报告位置: {Path(report_dir).absolute()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"生成报告失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Allure 命令行工具未安装")
        print("请安装 Allure: https://docs.qameta.io/allure/#_installing_a_commandline")
        return False


def open_allure_report(report_dir: str = "reports/allure-report") -> bool:
    """打开 allure 报告"""
    index_html = Path(report_dir) / "index.html"
    
    if not index_html.exists():
        print(f"错误: 报告文件不存在: {index_html}")
        return False
    
    print(f"打开报告: {index_html}")
    
    try:
        # 尝试用默认浏览器打开
        webbrowser.open(f"file://{index_html.absolute()}")
        return True
    except Exception as e:
        print(f"打开报告失败: {e}")
        print(f"请手动打开: file://{index_html.absolute()}")
        return False


def serve_allure_report(results_dir: str = "reports/allure-results", 
                       port: int = 8080) -> None:
    """启动 allure 报告服务器"""
    if not check_allure_installed():
        return
    
    print(f"启动 Allure 报告服务器在 http://localhost:{port}")
    print("按 Ctrl+C 停止服务器")
    
    cmd = [
        "allure", "serve",
        results_dir,
        "--port", str(port)
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("服务器已停止")
    except Exception as e:
        print(f"启动服务器失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Allure 报告工具")
    parser.add_argument("action", choices=["generate", "open", "serve", "all"],
                       help="执行的操作: generate(生成报告), open(打开报告), serve(启动服务器), all(生成并打开)")
    parser.add_argument("--results", default="reports/allure-results",
                       help="测试结果目录 (默认: reports/allure-results)")
    parser.add_argument("--report", default="reports/allure-report",
                       help="报告输出目录 (默认: reports/allure-report)")
    parser.add_argument("--port", type=int, default=8080,
                       help="服务器端口 (默认: 8080)")
    
    args = parser.parse_args()
    
    if args.action in ["generate", "all"]:
        if not generate_allure_report(args.results, args.report):
            sys.exit(1)
    
    if args.action in ["open", "all"]:
        open_allure_report(args.report)
    
    if args.action == "serve":
        serve_allure_report(args.results, args.port)


if __name__ == "__main__":
    main()
'''


def generate_readme() -> str:
    """生成 README.md 说明文件"""
    return """# Allure 测试报告说明

## 目录结构

```
reports/
├── allure-results/     # Allure 原始测试结果
├── allure-report/      # 生成的 Allure HTML 报告
├── html/              # 其他 HTML 格式报告
├── junit/             # JUnit XML 格式报告
├── screenshots/       # 测试截图
└── logs/              # 测试日志
```

## 使用方法

### 1. 生成测试报告

运行 pytest 测试并生成 Allure 结果：

```bash
pytest --alluredir=reports/allure-results
```

或者使用提供的运行脚本：

```bash
python run_tests.py
```

### 2. 生成 HTML 报告

从测试结果生成 HTML 报告：

```bash
# 使用 generate_report.py 脚本
python generate_report.py generate

# 或直接使用 allure 命令
allure generate reports/allure-results -o reports/allure-report --clean
```

### 3. 查看报告

打开生成的报告：

```bash
# 使用脚本打开
python generate_report.py open

# 或手动打开
open reports/allure-report/index.html  # macOS
start reports/allure-report/index.html # Windows
xdg-open reports/allure-report/index.html # Linux
```

### 4. 启动报告服务器

启动实时报告服务器：

```bash
python generate_report.py serve
# 或
allure serve reports/allure-results
```

## 配置说明

### Allure 配置
- `allure.yml`: 主配置文件
- `allure.properties`: 属性配置文件
- `allure/categories/categories.json`: 测试分类配置
- `allure/environment/environment.properties`: 环境配置

### 自定义分类

在 `allure/categories/categories.json` 中定义测试分类规则，用于在报告中自动分类失败的测试。

### 环境变量

在 `allure/environment/environment.properties` 中配置测试环境信息，这些信息会显示在报告的环境部分。

## 依赖安装

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 Allure 命令行工具

#### macOS
```bash
brew install allure
```

#### Windows
使用 Scoop:
```bash
scoop install allure
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-add-repository ppa:qameta/allure
sudo apt-get update
sudo apt-get install allure

# 或使用 SDKMAN
sdk install allure
```

#### 手动安装
从 https://github.com/allure-framework/allure2/releases 下载并配置 PATH。

## 报告功能

Allure 报告提供以下功能：

1. **测试概览** - 总体测试结果统计
2. **测试分类** - 按功能、故事、严重程度等分类
3. **时间线** - 测试执行时间线
4. **行为** - 按功能和行为分组
5. **包** - 按包和模块分组
6. **环境** - 测试环境信息
7. **附件** - 测试截图、日志、数据等附件
8. **历史** - 测试执行历史记录

## 故障排除

### 问题: Allure 命令未找到
解决方案: 安装 Allure 命令行工具并确保在 PATH 中

### 问题: 报告生成失败
解决方案: 检查测试结果目录是否正确，确保有测试结果文件

### 问题: 报告无法显示截图
解决方案: 确保截图保存在正确目录，并在测试代码中正确附加

## 相关链接

- [Allure 官方文档](https://docs.qameta.io/allure/)
- [Allure-pytest 文档](https://allurereport.org/docs/pytest/)
- [示例项目](https://github.com/allure-examples)
"""


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="创建 Allure 配置")
    parser.add_argument("--dir", default=".", help="基础目录 (默认: 当前目录)")

    args = parser.parse_args()

    print("创建 Allure 配置和目录结构...")
    created_files = create_allure_structure(args.dir)

    print()
    print("创建的文件:")
    for file_type, file_path in created_files.items():
        print(f"  - {file_type}: {file_path}")

    print()
    print("Allure 配置创建完成!")
    print("下一步:")
    print("1. 安装 Allure 命令行工具")
    print("2. 运行测试生成结果")
    print("3. 使用 generate_report.py 生成报告")


if __name__ == "__main__":
    # 添加 argparse 导入
    import argparse

    main()
