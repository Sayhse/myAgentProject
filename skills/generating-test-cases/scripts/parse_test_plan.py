#!/usr/bin/env python3
"""
测试计划解析器
解析测试计划模板，提取测试场景、API端点、测试需求等信息
支持格式：.txt, .md, .pdf, .docx
"""

import re
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


def extract_test_plan_info(file_path: str) -> Dict[str, Any]:
    """
    从测试计划文档中提取结构化信息

    Args:
        file_path: 测试计划文档路径

    Returns:
        包含提取信息的字典
    """
    path = Path(file_path)

    # 根据扩展名选择解析方法
    if not path.exists():
        return {"error": f"文件不存在: {file_path}"}

    # 读取文件内容
    content = ""
    suffix = path.suffix.lower()

    try:
        if suffix == ".txt":
            content = path.read_text(encoding="utf-8")
        elif suffix == ".md":
            content = path.read_text(encoding="utf-8")
        elif suffix == ".pdf":
            content = _extract_from_pdf(path)
        elif suffix == ".docx":
            content = _extract_from_docx(path)
        else:
            # 尝试作为文本文件读取
            try:
                content = path.read_text(encoding="utf-8")
            except:
                return {"error": f"不支持的文件格式: {suffix}"}
    except Exception as e:
        return {"error": f"读取文件失败: {str(e)}"}

    # 分析内容
    return analyze_test_plan(content)


def _extract_from_pdf(path: Path) -> str:
    """从 PDF 提取文本"""
    try:
        import PyPDF2  # type: ignore

        text = ""
        with open(path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except ImportError:
        return f"[PDF 文件需要 PyPDF2 库，请运行: pip install PyPDF2]\n文件路径: {path}"
    except Exception as e:
        return f"[PDF 解析错误: {str(e)}]"


def _extract_from_docx(path: Path) -> str:
    """从 DOCX 提取文本"""
    try:
        import docx

        doc = docx.Document(str(path))
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except ImportError:
        return f"[DOCX 文件需要 python-docx 库，请运行: pip install python-docx]\n文件路径: {path}"
    except Exception as e:
        return f"[DOCX 解析错误: {str(e)}]"


def analyze_test_plan(content: str) -> Dict[str, Any]:
    """
    分析测试计划内容，提取结构化信息
    """
    lines = content.split("\n")

    # 初始化结果
    result = {
        "metadata": {
            "total_lines": len(lines),
            "total_words": len(content.split()),
            "file_type": "测试计划",
        },
        "project_info": {
            "project_name": "",
            "api_name": "",
            "version": "",
            "test_manager": "",
        },
        "test_scopes": {"included": [], "excluded": [], "assumptions": []},
        "test_types": [],
        "api_endpoints": [],
        "functional_tests": [],
        "non_functional_tests": [],
        "user_stories": [],
        "test_schedule": [],
        "risks": [],
        "deliverables": [],
    }

    current_section = ""

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # 检测章节标题
        if line.startswith("# "):
            current_section = "project_overview"
        elif line.startswith("## "):
            section_title = line[3:].lower()
            if "项目概述" in line:
                current_section = "project_overview"
            elif "测试范围" in line:
                current_section = "test_scope"
            elif "测试策略" in line:
                current_section = "test_strategy"
            elif "API 测试计划" in line:
                current_section = "api_test_plan"
            elif "功能测试计划" in line:
                current_section = "functional_test_plan"
            elif "非功能测试计划" in line:
                current_section = "non_functional_test_plan"
            elif "测试进度" in line:
                current_section = "test_schedule"
            elif "风险评估" in line:
                current_section = "risk_assessment"
            elif "交付物" in line:
                current_section = "deliverables"
            else:
                current_section = ""

        # 提取项目信息
        if "项目名称" in line:
            match = re.search(r"项目名称\s*[:：]\s*(.+)", line)
            if match:
                result["project_info"]["project_name"] = match.group(1).strip()
        elif "API 名称" in line:
            match = re.search(r"API 名称\s*[:：]\s*(.+)", line)
            if match:
                result["project_info"]["api_name"] = match.group(1).strip()
        elif "版本" in line:
            match = re.search(r"版本\s*[:：]\s*(.+)", line)
            if match:
                result["project_info"]["version"] = match.group(1).strip()
        elif "测试负责人" in line:
            match = re.search(r"测试负责人\s*[:：]\s*(.+)", line)
            if match:
                result["project_info"]["test_manager"] = match.group(1).strip()

        # 提取测试范围
        if current_section == "test_scope":
            if line.startswith("- ") or line.startswith("* "):
                item = line[2:].strip()
                if "包含的功能" in content[i - 20 : i] or "包含" in content[i - 10 : i]:
                    result["test_scopes"]["included"].append(item)
                elif (
                    "排除的功能" in content[i - 20 : i] or "排除" in content[i - 10 : i]
                ):
                    result["test_scopes"]["excluded"].append(item)
                elif "假设" in content[i - 20 : i] or "约束" in content[i - 10 : i]:
                    result["test_scopes"]["assumptions"].append(item)

        # 提取测试类型
        if current_section == "test_strategy" and "|" in line:
            # 解析表格行
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if (
                len(parts) >= 2
                and "功能测试" not in parts[0]
                and "测试类型" not in parts[0]
            ):
                test_type = {
                    "type": parts[0],
                    "description": parts[1] if len(parts) > 1 else "",
                    "tools": parts[2] if len(parts) > 2 else "",
                    "owner": parts[3] if len(parts) > 3 else "",
                }
                result["test_types"].append(test_type)

        # 提取API端点
        if current_section == "api_test_plan" and "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3 and "端点" not in parts[0] and "[/api/" in parts[0]:
                endpoint = {
                    "path": parts[0],
                    "method": parts[1] if len(parts) > 1 else "",
                    "scenario": parts[2] if len(parts) > 2 else "",
                    "priority": parts[3] if len(parts) > 3 else "中",
                    "status": parts[4] if len(parts) > 4 else "待执行",
                    "owner": parts[5] if len(parts) > 5 else "",
                }
                result["api_endpoints"].append(endpoint)

        # 提取功能测试
        if current_section == "functional_test_plan":
            if line.startswith("#### 模块"):
                module_name = line.replace("####", "").strip()
                # 尝试提取后续的测试场景
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith("- **测试场景**:"):
                        scenario = next_line.replace("- **测试场景**:", "").strip()
                        test_item = {
                            "module": module_name,
                            "scenario": scenario,
                            "steps": [],
                            "expected_result": "",
                        }
                        # 提取步骤
                        for j in range(i + 2, min(i + 10, len(lines))):
                            step_line = lines[j].strip()
                            if step_line.startswith("1. "):
                                test_item["steps"].append(step_line[2:].strip())
                            elif step_line.startswith("- **预期结果**:"):
                                test_item["expected_result"] = step_line.replace(
                                    "- **预期结果**:", ""
                                ).strip()
                                break
                        result["functional_tests"].append(test_item)

        # 提取用户故事
        if "用户故事" in line and line.startswith("#### "):
            story_title = line.replace("####", "").strip()
            story_item = {
                "title": story_title,
                "acceptance_criteria": [],
                "test_cases": [],
            }
            # 提取验收标准
            for j in range(i + 1, min(i + 20, len(lines))):
                criteria_line = lines[j].strip()
                if criteria_line.startswith("- "):
                    story_item["acceptance_criteria"].append(criteria_line[2:].strip())
                elif criteria_line.startswith("#### "):
                    break
            result["user_stories"].append(story_item)

        # 提取风险
        if current_section == "risk_assessment" and "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 5 and "风险项" not in parts[0]:
                risk = {
                    "item": parts[0],
                    "impact": parts[1],
                    "probability": parts[2],
                    "mitigation": parts[3],
                    "owner": parts[4],
                }
                result["risks"].append(risk)

    return result


def generate_test_cases(plan_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    根据测试计划信息生成测试用例
    """
    test_cases = []

    # 为每个API端点生成测试用例
    for endpoint in plan_info.get("api_endpoints", []):
        test_case = {
            "id": f"API-{len(test_cases) + 1:03d}",
            "type": "api_test",
            "title": f"测试 {endpoint.get('method', '')} {endpoint.get('path', '')}",
            "description": endpoint.get("scenario", ""),
            "priority": endpoint.get("priority", "中"),
            "preconditions": [f"系统运行正常", f"测试环境已准备就绪"],
            "steps": [
                f"准备测试数据",
                f"发送 {endpoint.get('method', '')} 请求到 {endpoint.get('path', '')}",
                f"验证响应状态码",
                f"验证响应数据格式",
            ],
            "expected_results": [
                f"返回正确的状态码 (200/201/204)",
                f"响应数据符合预期格式",
                f"业务逻辑正确执行",
            ],
            "test_data": [
                {
                    "name": "valid_request",
                    "type": "json",
                    "description": "有效请求数据",
                },
                {
                    "name": "invalid_request",
                    "type": "json",
                    "description": "无效请求数据",
                },
            ],
        }
        test_cases.append(test_case)

    # 为每个功能测试生成测试用例
    for func_test in plan_info.get("functional_tests", []):
        test_case = {
            "id": f"FUNC-{len(test_cases) + 1:03d}",
            "type": "functional_test",
            "title": f"测试 {func_test.get('module', '')} - {func_test.get('scenario', '')}",
            "description": func_test.get("scenario", ""),
            "priority": "高",
            "preconditions": [f"用户已登录系统", f"相关功能模块可用"],
            "steps": func_test.get("steps", []),
            "expected_results": [func_test.get("expected_result", "功能正常执行")],
            "test_data": [
                {
                    "name": "test_user",
                    "type": "credentials",
                    "description": "测试用户账号",
                },
                {"name": "test_data", "type": "json", "description": "测试输入数据"},
            ],
        }
        test_cases.append(test_case)

    # 为用户故事生成测试用例
    for story in plan_info.get("user_stories", []):
        test_case = {
            "id": f"STORY-{len(test_cases) + 1:03d}",
            "type": "user_story_test",
            "title": f"验证用户故事: {story.get('title', '')}",
            "description": story.get("title", ""),
            "priority": "高",
            "preconditions": [f"系统正常运行", f"用户具备相应权限"],
            "steps": [f"模拟用户场景", f"执行相关操作", f"验证结果"],
            "expected_results": story.get("acceptance_criteria", []),
            "test_data": [
                {
                    "name": "user_scenario_data",
                    "type": "json",
                    "description": "用户场景数据",
                }
            ],
        }
        test_cases.append(test_case)

    return test_cases


def print_summary(result: Dict[str, Any]):
    """打印解析摘要"""
    if "error" in result:
        print(f"错误: {result['error']}")
        return

    print("=" * 60)
    print("测试计划分析结果")
    print("=" * 60)

    project = result["project_info"]
    print(f"项目名称: {project['project_name']}")
    print(f"API 名称: {project['api_name']}")
    print(f"版本: {project['version']}")
    print(f"测试负责人: {project['test_manager']}")
    print()

    print(f"测试范围:")
    print(f"  包含功能: {len(result['test_scopes']['included'])} 项")
    print(f"  排除功能: {len(result['test_scopes']['excluded'])} 项")
    print(f"  假设约束: {len(result['test_scopes']['assumptions'])} 项")

    print(f"\n测试类型: {len(result['test_types'])} 种")
    for test_type in result["test_types"][:3]:
        print(f"  - {test_type['type']}: {test_type['description'][:50]}...")

    print(f"\nAPI 端点: {len(result['api_endpoints'])} 个")
    for endpoint in result["api_endpoints"][:3]:
        print(f"  - {endpoint['method']} {endpoint['path']}")

    print(f"\n功能测试: {len(result['functional_tests'])} 项")
    for func_test in result["functional_tests"][:2]:
        print(f"  - {func_test['module']}: {func_test['scenario'][:50]}...")

    print(f"\n用户故事: {len(result['user_stories'])} 个")
    for story in result["user_stories"][:2]:
        print(f"  - {story['title'][:50]}...")

    # 生成测试用例
    test_cases = generate_test_cases(result)
    print(f"\n建议测试用例: {len(test_cases)} 个")
    print(f"  - API 测试: {sum(1 for tc in test_cases if tc['type'] == 'api_test')}")
    print(
        f"  - 功能测试: {sum(1 for tc in test_cases if tc['type'] == 'functional_test')}"
    )
    print(
        f"  - 用户故事测试: {sum(1 for tc in test_cases if tc['type'] == 'user_story_test')}"
    )

    print("=" * 60)


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python parse_test_plan.py <测试计划文件路径>")
        print("示例: python parse_test_plan.py test_plan.md")
        sys.exit(1)

    file_path = sys.argv[1]
    result = extract_test_plan_info(file_path)

    # 输出 JSON 格式结果
    if len(sys.argv) > 2 and sys.argv[2] == "--json":
        print(json.dumps(result, ensure_ascii=False, indent=2))

        # 生成测试用例
        test_cases = generate_test_cases(result)
        print("\n生成的测试用例:")
        print(json.dumps(test_cases, ensure_ascii=False, indent=2))
    else:
        print_summary(result)

        # 保存详细结果到文件
        output_file = "test_plan_analysis.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"详细结果已保存到: {output_file}")

        # 保存测试用例
        test_cases = generate_test_cases(result)
        test_cases_file = "generated_test_cases.json"
        with open(test_cases_file, "w", encoding="utf-8") as f:
            json.dump(test_cases, f, ensure_ascii=False, indent=2)
        print(f"测试用例已保存到: {test_cases_file}")


if __name__ == "__main__":
    main()
