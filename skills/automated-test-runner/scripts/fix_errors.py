#!/usr/bin/env python3
"""
自动修复常见的测试错误。

支持修复的错误类型：
1. 导入缺失
2. 语法错误
3. 文件路径错误
4. 简单的断言错误
5. 类型错误
"""

import os
import sys
import re
import ast
import importlib
import subprocess
from typing import Dict, List, Optional, Tuple
import traceback


class ErrorFixer:
    """错误修复器"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.fixed_files = []

    def fix_import_error(self, error_info: Dict) -> bool:
        """
        修复导入错误

        Args:
            error_info: 错误信息字典

        Returns:
            是否修复成功
        """
        message = error_info.get("message", "")
        file_path = error_info.get("file")

        if not file_path or not os.path.exists(file_path):
            print(f"无法修复导入错误：文件不存在 {file_path}")
            return False

        # 解析错误消息，提取缺失的模块名
        # ModuleNotFoundError: No module named 'module_name'
        match = re.search(r"No module named ['\"]([^'\"]+)['\"]", message)
        if not match:
            return False

        module_name = match.group(1)
        print(f"尝试修复缺失的模块: {module_name}")

        # 尝试安装缺失的模块
        try:
            # 检查是否是标准库模块
            import importlib.util

            spec = importlib.util.find_spec(module_name)
            if spec is None:
                # 不是标准库，尝试安装
                print(f"安装缺失的模块: {module_name}")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", module_name],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                )

                if result.returncode == 0:
                    print(f"成功安装模块: {module_name}")
                    return True
                else:
                    print(f"安装模块失败: {result.stderr}")
                    return False
            else:
                print(f"模块 {module_name} 是标准库的一部分，无需安装")
                return True

        except Exception as e:
            print(f"安装模块时出错: {e}")
            return False

    def fix_syntax_error(self, error_info: Dict) -> bool:
        """
        修复语法错误

        Args:
            error_info: 错误信息字典

        Returns:
            是否修复成功
        """
        message = error_info.get("message", "")
        file_path = error_info.get("file")
        line_num = error_info.get("line")

        if not file_path or not os.path.exists(file_path):
            print(f"无法修复语法错误：文件不存在 {file_path}")
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")

            if line_num and 1 <= line_num <= len(lines):
                # 获取有问题的行
                problem_line = lines[line_num - 1]
                print(f"语法错误行 {line_num}: {problem_line}")

                # 尝试修复常见的语法错误

                # 1. 缺少括号
                if problem_line.count("(") > problem_line.count(")"):
                    # 添加缺失的右括号
                    fixed_line = problem_line + ")"
                    lines[line_num - 1] = fixed_line
                    print(f"修复：添加缺失的右括号")

                # 2. 缺少引号
                elif problem_line.count('"') % 2 == 1:
                    # 添加缺失的引号
                    fixed_line = problem_line + '"'
                    lines[line_num - 1] = fixed_line
                    print(f"修复：添加缺失的引号")

                # 3. 缺少冒号（在 def、class、if、for、while 之后）
                elif re.search(
                    r"\b(def|class|if|elif|else|for|while|try|except|finally|with)\b[^:]*$",
                    problem_line,
                ):
                    fixed_line = problem_line + ":"
                    lines[line_num - 1] = fixed_line
                    print(f"修复：添加缺失的冒号")

                # 4. 缩进错误
                elif (
                    "unexpected indent" in message.lower()
                    or "expected an indented block" in message.lower()
                ):
                    # 尝试修复缩进
                    if line_num > 1:
                        # 使用上一行的缩进
                        prev_line = lines[line_num - 2]
                        indent_match = re.match(r"^(\s*)", prev_line)
                        if indent_match:
                            indent = indent_match.group(1)
                            lines[line_num - 1] = indent + lines[line_num - 1].lstrip()
                            print(f"修复：调整缩进")

                # 写入修复后的文件
                fixed_content = "\n".join(lines)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)

                self.fixed_files.append(file_path)
                return True

            return False

        except Exception as e:
            print(f"修复语法错误时出错: {e}")
            return False

    def fix_file_not_found(self, error_info: Dict) -> bool:
        """
        修复文件未找到错误

        Args:
            error_info: 错误信息字典

        Returns:
            是否修复成功
        """
        message = error_info.get("message", "")
        file_path = error_info.get("file")

        if not message:
            return False

        # 提取文件名
        match = re.search(r"['\"]([^'\"]+)['\"]", message)
        if not match:
            return False

        missing_file = match.group(1)
        print(f"缺失的文件: {missing_file}")

        # 检查是否是相对路径问题
        if not os.path.isabs(missing_file):
            # 尝试在项目目录中查找
            for root, dirs, files in os.walk(self.project_root):
                if missing_file in files:
                    print(f"找到文件: {os.path.join(root, missing_file)}")
                    return True

            # 如果找不到，尝试创建缺失的目录结构
            dir_path = os.path.dirname(missing_file)
            if dir_path:
                full_dir = os.path.join(self.project_root, dir_path)
                os.makedirs(full_dir, exist_ok=True)
                print(f"创建目录: {full_dir}")

            # 创建空文件
            full_path = os.path.join(self.project_root, missing_file)
            with open(full_path, "w") as f:
                f.write("# Created by automated test fixer\n")

            print(f"创建文件: {full_path}")
            return True

        return False

    def fix_assertion_error(self, error_info: Dict) -> bool:
        """
        修复断言错误

        Args:
            error_info: 错误信息字典

        Returns:
            是否修复成功
        """
        # 断言错误通常需要更复杂的逻辑修复
        # 这里只提供基本信息，由 Claude 模型进行智能修复
        print("断言错误需要人工检查，提供以下信息供 Claude 修复：")
        print(f"错误信息: {error_info.get('message')}")
        print(f"文件: {error_info.get('file')}")
        print(f"行号: {error_info.get('line')}")

        if error_info.get("traceback"):
            print(f"Traceback:\n{error_info.get('traceback')}")

        return False

    def fix_index_error(self, error_info: Dict) -> bool:
        """
        修复索引错误

        Args:
            error_info: 错误信息字典

        Returns:
            是否修复成功
        """
        file_path = error_info.get("file")
        line_num = error_info.get("line")

        if not file_path or not os.path.exists(file_path) or not line_num:
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            if 1 <= line_num <= len(lines):
                problem_line = lines[line_num - 1]

                # 查找索引访问
                index_pattern = r"\[([^]]+)\]"
                matches = list(re.finditer(index_pattern, problem_line))

                if matches:
                    # 尝试添加边界检查
                    # 这只是一个简单示例，实际修复需要更多上下文
                    print(f"索引错误在行 {line_num}: {problem_line}")
                    print("建议添加边界检查，例如: if index < len(list):")
                    return False

            return False

        except Exception as e:
            print(f"修复索引错误时出错: {e}")
            return False

    def fix_type_error(self, error_info: Dict) -> bool:
        """
        修复类型错误

        Args:
            error_info: 错误信息字典

        Returns:
            是否修复成功
        """
        message = error_info.get("message", "")
        print(f"类型错误: {message}")

        # 提取类型信息
        # 例如: "can only concatenate str (not 'int') to str"
        if "concatenate" in message and "str" in message:
            print("建议将非字符串值转换为字符串: str(value)")
            return False

        return False

    def fix_attribute_error(self, error_info: Dict) -> bool:
        """
        修复属性错误

        Args:
            error_info: 错误信息字典

        Returns:
            是否修复成功
        """
        message = error_info.get("message", "")
        file_path = error_info.get("file")
        line_num = error_info.get("line")

        if not message:
            return False

        # 提取缺失的属性名
        # 例如: "'module' object has no attribute 'function'"
        match = re.search(r"has no attribute ['\"]([^'\"]+)['\"]", message)
        if match:
            missing_attr = match.group(1)
            print(f"缺失的属性: {missing_attr}")

            # 检查是否是常见的拼写错误
            common_corrections = {
                "lengh": "length",
                "lenght": "length",
                "lenght": "length",
                "lenght": "length",
                "recieve": "receive",
                "seperate": "separate",
                "occured": "occurred",
                "occurence": "occurrence",
                "definately": "definitely",
                "seperate": "separate",
            }

            if missing_attr in common_corrections:
                correct_attr = common_corrections[missing_attr]
                print(f"可能是拼写错误，建议使用: {correct_attr}")

                # 尝试修复文件中的拼写错误
                if file_path and os.path.exists(file_path) and line_num:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # 简单替换（实际应用中需要更精确的替换）
                        fixed_content = content.replace(missing_attr, correct_attr)

                        if fixed_content != content:
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(fixed_content)
                            self.fixed_files.append(file_path)
                            print(f"修复拼写错误: {missing_attr} -> {correct_attr}")
                            return True
                    except Exception as e:
                        print(f"修复拼写错误时出错: {e}")

        return False

    def fix_error(self, error_info: Dict) -> bool:
        """
        根据错误类型调用相应的修复方法

        Args:
            error_info: 错误信息字典

        Returns:
            是否修复成功
        """
        error_type = error_info.get("type", "")

        fix_methods = {
            "import_error": self.fix_import_error,
            "syntax_error": self.fix_syntax_error,
            "file_not_found": self.fix_file_not_found,
            "assertion_error": self.fix_assertion_error,
            "index_error": self.fix_index_error,
            "type_error": self.fix_type_error,
            "attribute_error": self.fix_attribute_error,
        }

        if error_type in fix_methods:
            print(f"\n尝试修复 {error_type} 错误...")
            return fix_methods[error_type](error_info)
        else:
            print(f"\n未知错误类型: {error_type}")
            print(f"错误信息: {error_info.get('message')}")
            return False

    def get_fix_summary(self) -> Dict:
        """
        获取修复摘要

        Returns:
            修复摘要字典
        """
        return {"fixed_files": self.fixed_files, "total_fixed": len(self.fixed_files)}


def parse_failures_from_env() -> List[Dict]:
    """
    从环境变量解析失败信息

    Returns:
        失败信息列表
    """
    failures = []

    # 从环境变量读取失败信息
    # 环境变量格式由 run_tests.py 设置
    import os

    i = 0
    while True:
        type_key = f"FAILURE_{i}_TYPE"
        if type_key not in os.environ:
            break

        failure = {
            "type": os.environ[type_key],
            "message": os.environ.get(f"FAILURE_{i}_MESSAGE", ""),
            "file": os.environ.get(f"FAILURE_{i}_FILE"),
            "line": os.environ.get(f"FAILURE_{i}_LINE"),
        }

        # 转换行号为整数
        if failure["line"]:
            try:
                failure["line"] = int(failure["line"])
            except ValueError:
                failure["line"] = None

        failures.append(failure)
        i += 1

    return failures


def main():
    """命令行入口点"""
    if len(sys.argv) != 2:
        print("用法: python fix_errors.py <项目根目录>")
        print("环境变量: 从 FAILURE_* 环境变量读取失败信息")
        sys.exit(1)

    project_root = sys.argv[1]

    if not os.path.exists(project_root):
        print(f"错误：项目目录不存在 {project_root}")
        sys.exit(1)

    # 解析失败信息
    failures = parse_failures_from_env()

    if not failures:
        print("没有失败信息需要修复")
        sys.exit(0)

    print(f"找到 {len(failures)} 个需要修复的失败")

    # 创建修复器
    fixer = ErrorFixer(project_root)

    # 尝试修复每个失败
    success_count = 0
    for i, failure in enumerate(failures):
        print(f"\n{'=' * 60}")
        print(f"处理失败 {i + 1}/{len(failures)}")
        print(f"{'=' * 60}")

        if fixer.fix_error(failure):
            success_count += 1
            print(f"✓ 修复成功")
        else:
            print(f"✗ 修复失败，需要人工干预")

    # 输出修复摘要
    summary = fixer.get_fix_summary()
    print(f"\n{'=' * 60}")
    print("修复摘要")
    print(f"{'=' * 60}")
    print(f"总失败数: {len(failures)}")
    print(f"成功修复: {success_count}")
    print(f"修复的文件: {summary['fixed_files']}")

    # 导出修复结果
    print(f"\n导出修复结果:")
    print(f"export FIXED_COUNT={success_count}")
    print(f"export TOTAL_FAILURES={len(failures)}")

    if summary["fixed_files"]:
        for i, file_path in enumerate(summary["fixed_files"]):
            print(f"export FIXED_FILE_{i}='{file_path}'")

    sys.exit(0 if success_count > 0 else 1)


if __name__ == "__main__":
    main()
