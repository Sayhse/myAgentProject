#!/usr/bin/env python3
"""
解析 README.md 文件，提取安装和测试命令。

支持识别常见的命令模式：
- 安装命令：npm install, pip install, mvn install, etc.
- 测试命令：pytest, unittest, jest, mvn test, etc.
- Allure 报告命令：allure generate, allure serve
"""

import re
import os
import sys
from typing import List, Dict, Optional


def extract_commands(readme_path: str) -> Dict[str, List[str]]:
    """
    从 README.md 文件中提取命令

    Args:
        readme_path: README.md 文件路径

    Returns:
        包含命令分类的字典：
        {
            "install": ["npm install", "pip install -r requirements.txt"],
            "test": ["pytest", "pytest --alluredir=allure-results"],
            "allure": ["allure generate allure-results -o allure-report --clean"]
        }
    """
    if not os.path.exists(readme_path):
        print(f"错误：文件 {readme_path} 不存在")
        return {"install": [], "test": [], "allure": []}

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 初始化命令字典
    commands = {"install": [], "test": [], "allure": []}

    # 常见安装命令模式
    install_patterns = [
        r"```(?:bash|shell|sh)\s*\n(.*?)```",
        r"`(npm\s+install[^`]*)`",
        r"`(pip\s+install[^`]*)`",
        r"`(yarn\s+install[^`]*)`",
        r"`(mvn\s+install[^`]*)`",
        r"`(gradle\s+build[^`]*)`",
        r"`(docker\s+compose[^`]*)`",
        r"`(docker\s+build[^`]*)`",
    ]

    # 常见测试命令模式
    test_patterns = [
        r"`(pytest[^`]*)`",
        r"`(python\s+-m\s+pytest[^`]*)`",
        r"`(npm\s+test[^`]*)`",
        r"`(yarn\s+test[^`]*)`",
        r"`(mvn\s+test[^`]*)`",
        r"`(gradle\s+test[^`]*)`",
        r"`(jest[^`]*)`",
        r"`(unittest[^`]*)`",
        r"`(cargo\s+test[^`]*)`",
    ]

    # 常见 Allure 命令模式
    allure_patterns = [
        r"`(allure\s+generate[^`]*)`",
        r"`(allure\s+serve[^`]*)`",
        r"`(allure\s+report[^`]*)`",
        r"--alluredir[=\s]\S+",
    ]

    # 提取代码块中的命令
    code_blocks = re.findall(
        r"```(?:bash|shell|sh|python|javascript|js|typescript|ts)\s*\n(.*?)```",
        content,
        re.DOTALL,
    )
    for block in code_blocks:
        lines = block.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查安装命令
            if any(
                re.search(pattern, line, re.IGNORECASE)
                for pattern in [
                    r"^npm\s+install",
                    r"^pip\s+install",
                    r"^yarn\s+install",
                    r"^mvn\s+install",
                    r"^gradle\s+build",
                    r"^docker\s+compose",
                    r"^docker\s+build",
                    r"^bundle\s+install",
                    r"^composer\s+install",
                ]
            ):
                if line not in commands["install"]:
                    commands["install"].append(line)

            # 检查测试命令
            if any(
                re.search(pattern, line, re.IGNORECASE)
                for pattern in [
                    r"^pytest",
                    r"^npm\s+test",
                    r"^yarn\s+test",
                    r"^mvn\s+test",
                    r"^gradle\s+test",
                    r"^jest",
                    r"^unittest",
                    r"^cargo\s+test",
                    r"^go\s+test",
                ]
            ):
                if line not in commands["test"]:
                    commands["test"].append(line)

            # 检查 Allure 命令
            if "allure" in line.lower():
                if line not in commands["allure"]:
                    commands["allure"].append(line)

    # 提取行内代码命令
    inline_code = re.findall(r"`([^`]+)`", content)
    for code in inline_code:
        code = code.strip()

        # 安装命令
        if any(
            re.search(pattern, code, re.IGNORECASE)
            for pattern in [
                r"^npm\s+install",
                r"^pip\s+install",
                r"^yarn\s+install",
                r"^mvn\s+install",
            ]
        ):
            if code not in commands["install"]:
                commands["install"].append(code)

        # 测试命令
        if any(
            re.search(pattern, code, re.IGNORECASE)
            for pattern in [
                r"^pytest",
                r"^npm\s+test",
                r"^yarn\s+test",
                r"^mvn\s+test",
                r"^jest",
            ]
        ):
            if code not in commands["test"]:
                commands["test"].append(code)

        # Allure 命令
        if "allure" in code.lower():
            if code not in commands["allure"]:
                commands["allure"].append(code)

    # 如果没有找到明确的测试命令，尝试推断
    if not commands["test"]:
        # 查找包含 "test" 的代码块
        test_blocks = re.findall(
            r"```(?:bash|shell|sh)\s*\n(.*?test.*?)```",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        for block in test_blocks:
            lines = block.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line and "test" in line.lower() and line not in commands["test"]:
                    commands["test"].append(line)

    return commands


def main():
    """命令行入口点"""
    if len(sys.argv) != 2:
        print("用法: python parse_readme.py <README.md 路径>")
        sys.exit(1)

    readme_path = sys.argv[1]
    commands = extract_commands(readme_path)

    print("提取到的命令：")
    print(f"安装命令: {commands['install']}")
    print(f"测试命令: {commands['test']}")
    print(f"Allure 命令: {commands['allure']}")

    # 输出为环境变量格式，供其他脚本使用
    if commands["install"]:
        print(f"\n导出安装命令:")
        for i, cmd in enumerate(commands["install"]):
            print(f"export INSTALL_CMD_{i}='{cmd}'")

    if commands["test"]:
        print(f"\n导出测试命令:")
        for i, cmd in enumerate(commands["test"]):
            print(f"export TEST_CMD_{i}='{cmd}'")

    if commands["allure"]:
        print(f"\n导出 Allure 命令:")
        for i, cmd in enumerate(commands["allure"]):
            print(f"export ALLURE_CMD_{i}='{cmd}'")


if __name__ == "__main__":
    main()
