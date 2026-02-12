#!/usr/bin/env python3
"""
生成 Allure 测试报告。

功能：
- 查找 Allure 结果目录
- 生成 HTML 报告
- 验证报告生成成功
- 返回报告路径
"""

import os
import sys
import subprocess
import shutil
from typing import Optional, Tuple, Dict


class AllureReporter:
    """Allure 报告生成器"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.allure_results_dir = None
        self.allure_report_dir = None

    def find_allure_results(self) -> Optional[str]:
        """
        查找 Allure 结果目录

        Returns:
            Allure 结果目录路径，如果找不到则返回 None
        """
        common_dirs = [
            "allure-results",
            "allure_results",
            "target/allure-results",
            "build/allure-results",
            "test-results",
            "test_results",
            "reports/allure-results",
        ]

        for dir_name in common_dirs:
            dir_path = os.path.join(self.project_root, dir_name)
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                # 检查目录是否包含 Allure 结果文件
                if self._is_allure_results_dir(dir_path):
                    self.allure_results_dir = dir_path
                    return dir_path

        # 递归搜索
        for root, dirs, files in os.walk(self.project_root):
            for dir_name in dirs:
                if "allure" in dir_name.lower() and "result" in dir_name.lower():
                    dir_path = os.path.join(root, dir_name)
                    if self._is_allure_results_dir(dir_path):
                        self.allure_results_dir = dir_path
                        return dir_path

        return None

    def _is_allure_results_dir(self, dir_path: str) -> bool:
        """
        检查目录是否包含 Allure 结果文件

        Args:
            dir_path: 目录路径

        Returns:
            如果是 Allure 结果目录则返回 True
        """
        try:
            files = os.listdir(dir_path)
            # Allure 结果目录通常包含 .json、.txt 等文件
            allure_extensions = [".json", ".txt", ".xml"]
            for file in files:
                if any(file.endswith(ext) for ext in allure_extensions):
                    return True
        except:
            pass
        return False

    def generate_report(self, output_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        生成 Allure 报告

        Args:
            output_dir: 输出目录，如果为 None 则使用默认目录

        Returns:
            (成功与否, 报告目录路径)
        """
        if not self.allure_results_dir:
            found = self.find_allure_results()
            if not found:
                return False, "未找到 Allure 结果目录"

        # 设置输出目录
        if output_dir:
            self.allure_report_dir = output_dir
        else:
            self.allure_report_dir = os.path.join(self.project_root, "allure-report")

        # 清理旧报告（如果存在）
        if os.path.exists(self.allure_report_dir):
            try:
                shutil.rmtree(self.allure_report_dir)
                print(f"已清理旧报告目录: {self.allure_report_dir}")
            except Exception as e:
                print(f"清理旧报告目录时出错: {e}")

        # 生成报告
        print(f"生成 Allure 报告...")
        print(f"结果目录: {self.allure_results_dir}")
        print(f"报告目录: {self.allure_report_dir}")

        try:
            # 检查 allure 命令是否可用
            allure_cmd = self._get_allure_command()
            if not allure_cmd:
                return False, "未找到 Allure 命令行工具"

            # 执行 allure generate 命令
            cmd = [
                allure_cmd,
                "generate",
                self.allure_results_dir,
                "-o",
                self.allure_report_dir,
                "--clean",
            ]

            print(f"执行命令: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=self.project_root
            )

            if result.returncode == 0:
                # 验证报告是否生成成功
                if self._validate_report():
                    return True, self.allure_report_dir
                else:
                    return False, "报告生成失败：验证未通过"
            else:
                error_msg = f"Allure 命令执行失败: {result.stderr}"
                print(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"生成报告时出错: {e}"
            print(error_msg)
            return False, error_msg

    def _get_allure_command(self) -> Optional[str]:
        """
        获取 Allure 命令路径

        Returns:
            Allure 命令路径，如果找不到则返回 None
        """
        # 尝试多种方式查找 allure 命令
        possible_commands = ["allure", "allure.bat"]

        for cmd in possible_commands:
            try:
                # 检查命令是否可用
                result = subprocess.run(
                    [cmd, "--version"], capture_output=True, text=True
                )
                if result.returncode == 0:
                    return cmd
            except:
                continue

        # 检查常见安装路径
        common_paths = [
            os.path.join(
                os.environ.get("PROGRAMFILES", ""), "Allure", "bin", "allure.bat"
            ),
            os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Microsoft",
                "WindowsApps",
                "allure.exe",
            ),
            "/usr/local/bin/allure",
            "/usr/bin/allure",
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        return None

    def _validate_report(self) -> bool:
        """
        验证报告是否生成成功

        Returns:
            报告有效则返回 True
        """
        if not self.allure_report_dir or not os.path.exists(self.allure_report_dir):
            return False

        # 检查报告目录是否包含必要的文件
        required_files = ["index.html", "widgets", "data"]

        for file in required_files:
            file_path = os.path.join(self.allure_report_dir, file)
            if not os.path.exists(file_path):
                print(f"报告验证失败：缺少文件 {file}")
                return False

        # 检查 index.html 是否可读
        index_html = os.path.join(self.allure_report_dir, "index.html")
        try:
            with open(index_html, "r", encoding="utf-8") as f:
                content = f.read(1000)  # 只读取前1000个字符
                if "<!DOCTYPE html>" not in content and "<html" not in content:
                    print("报告验证失败：index.html 不是有效的 HTML 文件")
                    return False
        except:
            print("报告验证失败：无法读取 index.html")
            return False

        return True

    def get_report_url(self) -> Optional[str]:
        """
        获取报告 URL（用于本地服务器）

        Returns:
            报告 URL，如果无法获取则返回 None
        """
        if not self.allure_report_dir or not os.path.exists(self.allure_report_dir):
            return None

        # 转换为文件 URL
        abs_path = os.path.abspath(self.allure_report_dir)
        if os.name == "nt":  # Windows
            # Windows 文件 URL
            abs_path = abs_path.replace("\\", "/")
            if not abs_path.startswith("/"):
                abs_path = "/" + abs_path
            url = f"file://{abs_path}/index.html"
        else:  # Unix/Linux/Mac
            url = f"file://{abs_path}/index.html"

        return url

    def serve_report(self, port: int = 8080) -> Tuple[bool, str]:
        """
        启动 Allure 服务器预览报告

        Args:
            port: 服务器端口

        Returns:
            (成功与否, 服务器 URL)
        """
        if not self.allure_results_dir:
            found = self.find_allure_results()
            if not found:
                return False, "未找到 Allure 结果目录"

        try:
            allure_cmd = self._get_allure_command()
            if not allure_cmd:
                return False, "未找到 Allure 命令行工具"

            # 启动 allure serve
            cmd = [allure_cmd, "serve", self.allure_results_dir, "--port", str(port)]

            print(f"启动 Allure 服务器: {' '.join(cmd)}")

            # 注意：这个命令会阻塞，所以我们在后台运行
            import threading

            def run_server():
                subprocess.run(cmd, cwd=self.project_root)

            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()

            url = f"http://localhost:{port}"
            return True, url

        except Exception as e:
            error_msg = f"启动服务器时出错: {e}"
            print(error_msg)
            return False, error_msg


def main():
    """命令行入口点"""
    if len(sys.argv) != 2:
        print("用法: python generate_report.py <项目根目录>")
        print("可选环境变量:")
        print("  ALLURE_RESULTS_DIR: 指定 Allure 结果目录")
        print("  ALLURE_REPORT_DIR: 指定报告输出目录")
        sys.exit(1)

    project_root = sys.argv[1]

    if not os.path.exists(project_root):
        print(f"错误：项目目录不存在 {project_root}")
        sys.exit(1)

    # 创建报告生成器
    reporter = AllureReporter(project_root)

    # 检查是否指定了结果目录
    import os

    results_dir = os.environ.get("ALLURE_RESULTS_DIR")
    if results_dir and os.path.exists(results_dir):
        reporter.allure_results_dir = results_dir
        print(f"使用指定的结果目录: {results_dir}")

    # 检查是否指定了报告目录
    report_dir = os.environ.get("ALLURE_REPORT_DIR")

    # 生成报告
    success, result = reporter.generate_report(report_dir)

    if success:
        print(f"\n{'=' * 60}")
        print("Allure 报告生成成功！")
        print(f"{'=' * 60}")
        print(f"报告目录: {result}")

        # 获取报告 URL
        report_url = reporter.get_report_url()
        if report_url:
            print(f"报告 URL: {report_url}")

        # 导出报告路径
        print(f"\n导出报告路径:")
        print(f"export ALLURE_REPORT_DIR='{result}'")
        if report_url:
            print(f"export ALLURE_REPORT_URL='{report_url}'")

        # 可选：启动服务器预览
        print(f"\n是否启动服务器预览报告？(y/n)")
        try:
            response = input().strip().lower()
            if response == "y":
                serve_success, serve_url = reporter.serve_report()
                if serve_success:
                    print(f"服务器已启动: {serve_url}")
                    print(f"按 Ctrl+C 停止服务器")
                    # 等待用户中断
                    import time

                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        print("\n服务器已停止")
                else:
                    print(f"启动服务器失败: {serve_url}")
        except:
            pass  # 非交互式环境

        sys.exit(0)
    else:
        print(f"\n{'=' * 60}")
        print("Allure 报告生成失败！")
        print(f"{'=' * 60}")
        print(f"错误信息: {result}")

        # 尝试提供替代方案
        print(f"\n替代方案:")
        print("1. 检查是否已安装 Allure: https://docs.qameta.io/allure/")
        print(
            "2. 手动生成报告: allure generate allure-results -o allure-report --clean"
        )
        print("3. 直接查看原始结果文件")

        sys.exit(1)


if __name__ == "__main__":
    main()
