#!/usr/bin/env python3
"""
执行测试命令并捕获输出。

支持：
- 执行测试命令
- 实时捕获标准输出和标准错误
- 检测测试失败
- 收集详细的错误信息
"""

import subprocess
import sys
import os
import time
from typing import Dict, List, Tuple, Optional


def run_command(command: str, cwd: Optional[str] = None, timeout: int = 300) -> Dict:
    """
    执行命令并返回结果

    Args:
        command: 要执行的命令
        cwd: 工作目录
        timeout: 超时时间（秒）

    Returns:
        包含执行结果的字典：
        {
            "success": bool,
            "returncode": int,
            "stdout": str,
            "stderr": str,
            "duration": float,
            "command": str
        }
    """
    if not cwd:
        cwd = os.getcwd()

    print(f"执行命令: {command}")
    print(f"工作目录: {cwd}")

    start_time = time.time()

    try:
        # 使用 subprocess 执行命令，捕获输出
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )

        stdout_lines = []
        stderr_lines = []

        # 实时读取输出
        while True:
            # 读取标准输出
            if process.stdout:
                stdout_line = process.stdout.readline()
                if stdout_line:
                    stdout_lines.append(stdout_line)
                    print(stdout_line.rstrip())

            # 读取标准错误
            if process.stderr:
                stderr_line = process.stderr.readline()
                if stderr_line:
                    stderr_lines.append(stderr_line)
                    print(f"STDERR: {stderr_line.rstrip()}", file=sys.stderr)

            # 检查进程是否结束
            returncode = process.poll()
            if returncode is not None:
                # 读取剩余输出
                remaining_stdout, remaining_stderr = process.communicate()
                if remaining_stdout:
                    stdout_lines.append(remaining_stdout)
                    print(remaining_stdout.rstrip())
                if remaining_stderr:
                    stderr_lines.append(remaining_stderr)
                    print(f"STDERR: {remaining_stderr.rstrip()}", file=sys.stderr)
                break

            # 检查超时
            if time.time() - start_time > timeout:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

                return {
                    "success": False,
                    "returncode": -1,
                    "stdout": "".join(stdout_lines),
                    "stderr": "".join(stderr_lines) + f"\n命令超时（{timeout} 秒）",
                    "duration": time.time() - start_time,
                    "command": command,
                    "timeout": True,
                }

        duration = time.time() - start_time

        result = {
            "success": returncode == 0,
            "returncode": returncode,
            "stdout": "".join(stdout_lines),
            "stderr": "".join(stderr_lines),
            "duration": duration,
            "command": command,
        }

        print(f"命令执行完成，返回值: {returncode}，耗时: {duration:.2f} 秒")

        return result

    except Exception as e:
        duration = time.time() - start_time
        print(f"执行命令时发生异常: {e}")

        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "duration": duration,
            "command": command,
            "exception": str(e),
        }


def detect_test_failures(result: Dict) -> List[Dict]:
    """
    从测试结果中检测失败

    Args:
        result: run_command 返回的结果字典

    Returns:
        失败信息列表，每个失败信息包含：
        {
            "type": "assertion_error" | "import_error" | "syntax_error" | "runtime_error" | "unknown",
            "message": str,
            "file": Optional[str],
            "line": Optional[int],
            "traceback": Optional[str]
        }
    """
    failures = []

    if result["success"]:
        return failures

    stderr = result["stderr"]
    stdout = result["stdout"]

    # 合并输出以便分析
    full_output = stdout + "\n" + stderr

    # 查找常见的错误模式

    # 1. 断言错误（pytest, unittest）
    assertion_patterns = [
        r"AssertionError: (.*)",
        r"assert (.*)",
        r"Expected: (.*)\n\s*Actual: (.*)",
    ]

    # 2. 导入错误
    import_patterns = [
        r"ModuleNotFoundError: No module named \'(.*)\'",
        r"ImportError: (.*)",
    ]

    # 3. 语法错误
    syntax_patterns = [
        r"SyntaxError: (.*)",
        r'File "(.*)", line (\d+)',
    ]

    # 4. 文件未找到错误
    file_not_found_patterns = [
        r"FileNotFoundError: (.*)",
        r"No such file or directory: (.*)",
    ]

    # 5. 索引错误
    index_patterns = [
        r"IndexError: (.*)",
        r"list index out of range",
    ]

    # 6. 类型错误
    type_patterns = [
        r"TypeError: (.*)",
    ]

    # 7. 属性错误
    attribute_patterns = [
        r"AttributeError: (.*)",
    ]

    # 解析错误信息
    lines = full_output.split("\n")
    current_traceback = []
    in_traceback = False

    for i, line in enumerate(lines):
        line = line.strip()

        # 检测 traceback 开始
        if line.startswith("Traceback (most recent call last):"):
            in_traceback = True
            current_traceback = [line]
            continue

        if in_traceback:
            current_traceback.append(line)

            # 检测 traceback 结束（通常是错误类型）
            if line.startswith(
                (
                    "AssertionError:",
                    "ImportError:",
                    "SyntaxError:",
                    "FileNotFoundError:",
                    "IndexError:",
                    "TypeError:",
                    "AttributeError:",
                    "RuntimeError:",
                    "ValueError:",
                )
            ):
                # traceback 结束
                traceback_text = "\n".join(current_traceback)

                # 确定错误类型
                error_type = "unknown"
                if "AssertionError" in line:
                    error_type = "assertion_error"
                elif "ImportError" in line or "ModuleNotFoundError" in line:
                    error_type = "import_error"
                elif "SyntaxError" in line:
                    error_type = "syntax_error"
                elif "FileNotFoundError" in line:
                    error_type = "file_not_found"
                elif "IndexError" in line:
                    error_type = "index_error"
                elif "TypeError" in line:
                    error_type = "type_error"
                elif "AttributeError" in line:
                    error_type = "attribute_error"
                elif "RuntimeError" in line:
                    error_type = "runtime_error"
                elif "ValueError" in line:
                    error_type = "value_error"

                # 提取文件名和行号
                file_path = None
                line_num = None

                for tb_line in current_traceback:
                    # 查找类似 "File \"path/to/file.py\", line 123" 的行
                    file_match = re.search(r'File "(.*)", line (\d+)', tb_line)
                    if file_match:
                        file_path = file_match.group(1)
                        line_num = int(file_match.group(2))
                        break

                failure = {
                    "type": error_type,
                    "message": line,
                    "file": file_path,
                    "line": line_num,
                    "traceback": traceback_text,
                    "raw_output": full_output,
                }

                failures.append(failure)
                in_traceback = False
                current_traceback = []

    # 如果没有找到结构化的 traceback，尝试从输出中提取错误信息
    if not failures and stderr:
        # 提取第一行错误信息
        error_lines = [line for line in stderr.split("\n") if line.strip()]
        if error_lines:
            failure = {
                "type": "unknown",
                "message": error_lines[0],
                "file": None,
                "line": None,
                "traceback": stderr,
                "raw_output": full_output,
            }
            failures.append(failure)

    return failures


def run_test_suite(test_commands: List[str], cwd: Optional[str] = None) -> Dict:
    """
    运行测试套件

    Args:
        test_commands: 测试命令列表
        cwd: 工作目录

    Returns:
        测试套件结果：
        {
            "overall_success": bool,
            "results": List[命令结果],
            "failures": List[失败信息],
            "total_duration": float
        }
    """
    if not test_commands:
        return {
            "overall_success": False,
            "results": [],
            "failures": [
                {
                    "type": "no_test_commands",
                    "message": "没有找到测试命令",
                    "file": None,
                    "line": None,
                    "traceback": "",
                }
            ],
            "total_duration": 0,
        }

    results = []
    all_failures = []
    total_duration = 0

    for i, cmd in enumerate(test_commands):
        print(f"\n{'=' * 60}")
        print(f"运行测试命令 {i + 1}/{len(test_commands)}: {cmd}")
        print(f"{'=' * 60}")

        result = run_command(cmd, cwd)
        results.append(result)
        total_duration += result["duration"]

        if not result["success"]:
            failures = detect_test_failures(result)
            all_failures.extend(failures)

    overall_success = (
        all(len(r.get("failures", [])) == 0 for r in results) and len(all_failures) == 0
    )

    return {
        "overall_success": overall_success,
        "results": results,
        "failures": all_failures,
        "total_duration": total_duration,
    }


# 导入正则表达式模块
import re


def main():
    """命令行入口点"""
    if len(sys.argv) < 2:
        print("用法: python run_tests.py <测试命令> [<测试命令2> ...]")
        print("示例: python run_tests.py 'pytest' 'npm test'")
        sys.exit(1)

    test_commands = sys.argv[1:]
    cwd = os.getcwd()

    print(f"工作目录: {cwd}")
    print(f"测试命令: {test_commands}")

    result = run_test_suite(test_commands, cwd)

    print(f"\n{'=' * 60}")
    print("测试套件结果摘要")
    print(f"{'=' * 60}")
    print(f"总体成功: {result['overall_success']}")
    print(f"总耗时: {result['total_duration']:.2f} 秒")
    print(f"失败数量: {len(result['failures'])}")

    if result["failures"]:
        print(f"\n失败详情:")
        for i, failure in enumerate(result["failures"]):
            print(f"\n失败 {i + 1}:")
            print(f"  类型: {failure['type']}")
            print(f"  消息: {failure['message']}")
            if failure["file"]:
                print(f"  文件: {failure['file']}")
            if failure["line"]:
                print(f"  行号: {failure['line']}")

    # 输出结果供其他脚本使用
    if result["failures"]:
        print(f"\n导出失败信息:")
        for i, failure in enumerate(result["failures"]):
            print(f"export FAILURE_{i}_TYPE='{failure['type']}'")
            print(f"export FAILURE_{i}_MESSAGE='{failure['message']}'")
            if failure["file"]:
                print(f"export FAILURE_{i}_FILE='{failure['file']}'")
            if failure["line"]:
                print(f"export FAILURE_{i}_LINE='{failure['line']}'")

    # 返回退出代码
    sys.exit(0 if result["overall_success"] else 1)


if __name__ == "__main__":
    main()
