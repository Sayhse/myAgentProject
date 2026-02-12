#!/usr/bin/env python3
"""
测试矩阵生成器
结合需求分析和 API 分析结果，生成测试覆盖矩阵
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_requirements(requirements_file: str) -> Dict[str, Any]:
    """加载需求分析结果"""
    with open(requirements_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_api_analysis(api_file: str) -> Dict[str, Any]:
    """加载 API 分析结果"""
    with open(api_file, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_test_matrix(
    requirements: Dict[str, Any], api_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    生成测试覆盖矩阵

    Args:
        requirements: 需求分析结果
        api_analysis: API 分析结果

    Returns:
        测试矩阵
    """
    # 创建测试矩阵
    matrix = {
        "project_overview": {
            "project_name": requirements.get("metadata", {}).get(
                "file_type", "未知项目"
            ),
            "api_title": api_analysis.get("metadata", {}).get("title", "未知API"),
            "total_requirements": len(requirements.get("functional_requirements", []))
            + len(requirements.get("non_functional_requirements", [])),
            "total_endpoints": len(api_analysis.get("endpoints", [])),
            "analysis_date": "2025-02-07",  # 可以使用实际日期
        },
        "test_coverage": {
            "functional_coverage": [],
            "api_coverage": [],
            "integration_coverage": [],
        },
        "test_scenarios": [],
        "risk_assessment": [],
        "resource_estimation": {},
    }

    # 功能需求覆盖
    func_reqs = requirements.get("functional_requirements", [])
    for req in func_reqs:
        coverage_item = {
            "requirement": req.get("text", "")[:100],
            "priority": req.get("priority", "medium"),
            "test_type": "functional",
            "test_scenarios": [
                f"验证: {req.get('text', '')[:50]}...",
                f"边界条件测试",
                f"错误处理测试",
            ],
            "estimated_effort": "1-2小时"
            if req.get("priority") == "high"
            else "2-4小时",
        }
        matrix["test_coverage"]["functional_coverage"].append(coverage_item)

    # 非功能需求覆盖
    nfr_reqs = requirements.get("non_functional_requirements", [])
    for nfr in nfr_reqs:
        coverage_item = {
            "requirement": nfr.get("text", "")[:100],
            "priority": "high",
            "test_type": "non_functional",
            "test_scenarios": [
                f"性能测试: {nfr.get('text', '')[:50]}...",
                f"压力测试",
                f"兼容性测试",
            ],
            "estimated_effort": "4-8小时",
        }
        matrix["test_coverage"]["functional_coverage"].append(coverage_item)

    # API 端点覆盖
    endpoints = api_analysis.get("endpoints", [])
    for endpoint in endpoints:
        coverage_item = {
            "endpoint": f"{endpoint.get('method', '')} {endpoint.get('path', '')}",
            "summary": endpoint.get("summary", "")[:50],
            "priority": "high" if endpoint.get("security") else "medium",
            "test_type": "api",
            "test_scenarios": [f"正常请求测试", f"参数验证测试", f"错误响应测试"],
            "estimated_effort": "1-2小时",
        }
        matrix["test_coverage"]["api_coverage"].append(coverage_item)

        # 添加到测试场景
        scenario = {
            "id": f"API-{len(matrix['test_scenarios']) + 1:03d}",
            "name": f"{endpoint.get('method', '')} {endpoint.get('path', '')}",
            "description": endpoint.get("summary", endpoint.get("description", "")),
            "type": "api_test",
            "steps": [
                f"准备测试数据",
                f"发送 {endpoint.get('method', '')} 请求到 {endpoint.get('path', '')}",
                f"验证响应状态码",
                f"验证响应数据格式",
            ],
            "expected_result": "返回正确的状态码和响应数据",
            "priority": "high" if endpoint.get("security") else "medium",
        }
        matrix["test_scenarios"].append(scenario)

    # 集成测试覆盖（基于用户故事）
    user_stories = requirements.get("user_stories", [])
    for story in user_stories:
        coverage_item = {
            "user_story": story.get("text", "")[:100],
            "priority": "high",
            "test_type": "integration",
            "test_scenarios": [
                f"端到端用户流程测试",
                f"{story.get('text', '')[:50]}...",
            ],
            "estimated_effort": "4-8小时",
        }
        matrix["test_coverage"]["integration_coverage"].append(coverage_item)

        # 添加到测试场景
        scenario = {
            "id": f"INT-{len(matrix['test_scenarios']) + 1:03d}",
            "name": f"用户故事: {story.get('text', '')[:50]}...",
            "description": story.get("text", ""),
            "type": "integration_test",
            "steps": [
                "模拟用户登录（如需要）",
                "执行相关操作序列",
                "验证最终结果符合预期",
            ],
            "expected_result": "用户故事的所有验收条件都得到满足",
            "priority": "high",
        }
        matrix["test_scenarios"].append(scenario)

    # 风险评估
    risks = [
        {
            "risk": "需求不明确",
            "impact": "高",
            "probability": "中",
            "mitigation": "及时与产品经理确认需求细节",
            "owner": "测试负责人",
        },
        {
            "risk": "API 变更频繁",
            "impact": "高",
            "probability": "中",
            "mitigation": "建立 API 变更通知机制",
            "owner": "开发团队",
        },
        {
            "risk": "测试环境不稳定",
            "impact": "中",
            "probability": "高",
            "mitigation": "准备备用测试环境",
            "owner": "运维团队",
        },
    ]
    matrix["risk_assessment"] = risks

    # 资源估算
    total_scenarios = len(matrix["test_scenarios"])
    matrix["resource_estimation"] = {
        "total_test_scenarios": total_scenarios,
        "estimated_hours": total_scenarios * 2,  # 平均每个场景2小时
        "team_size": "2-3人",
        "timeline_weeks": max(1, total_scenarios // 20),  # 每周完成20个场景
        "tools": ["Postman", "JUnit", "Selenium", "JMeter"],
        "deliverables": ["测试计划文档", "测试用例", "测试脚本", "测试报告"],
    }

    return matrix


def print_matrix_summary(matrix: Dict[str, Any]):
    """打印测试矩阵摘要"""
    overview = matrix["project_overview"]
    coverage = matrix["test_coverage"]
    resource = matrix["resource_estimation"]

    print("=" * 60)
    print("测试覆盖矩阵")
    print("=" * 60)

    print(f"项目: {overview['project_name']}")
    print(f"API: {overview['api_title']}")
    print(f"需求总数: {overview['total_requirements']}")
    print(f"API端点: {overview['total_endpoints']}")
    print()

    print("测试覆盖范围:")
    print(f"  功能测试: {len(coverage['functional_coverage'])} 项")
    print(f"  API测试: {len(coverage['api_coverage'])} 项")
    print(f"  集成测试: {len(coverage['integration_coverage'])} 项")
    print(f"  总测试场景: {len(matrix['test_scenarios'])} 个")
    print()

    print("资源估算:")
    print(f"  预计工时: {resource['estimated_hours']} 小时")
    print(f"  团队规模: {resource['team_size']}")
    print(f"  时间线: {resource['timeline_weeks']} 周")
    print(f"  测试工具: {', '.join(resource['tools'])}")
    print()

    print("高风险项:")
    for risk in matrix["risk_assessment"][:3]:
        if risk["impact"] == "高":
            print(f"  - {risk['risk']} (负责人: {risk['owner']})")

    print("=" * 60)


def export_to_markdown(matrix: Dict[str, Any], output_file: str):
    """导出为 Markdown 格式"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# 测试覆盖矩阵\n\n")

        # 项目概述
        f.write("## 项目概述\n\n")
        overview = matrix["project_overview"]
        f.write(f"- **项目名称**: {overview['project_name']}\n")
        f.write(f"- **API 名称**: {overview['api_title']}\n")
        f.write(f"- **分析日期**: {overview['analysis_date']}\n")
        f.write(f"- **需求总数**: {overview['total_requirements']}\n")
        f.write(f"- **API 端点**: {overview['total_endpoints']}\n\n")

        # 测试覆盖
        f.write("## 测试覆盖\n\n")
        coverage = matrix["test_coverage"]

        f.write("### 功能测试\n")
        for item in coverage["functional_coverage"][:5]:
            f.write(f"- **{item['requirement']}** (优先级: {item['priority']})\n")
            f.write(f"  - 测试类型: {item['test_type']}\n")
            f.write(f"  - 预估工时: {item['estimated_effort']}\n")
        f.write(f"\n*共 {len(coverage['functional_coverage'])} 项功能测试*\n\n")

        f.write("### API 测试\n")
        for item in coverage["api_coverage"][:5]:
            f.write(f"- **{item['endpoint']}** (优先级: {item['priority']})\n")
            f.write(f"  - 摘要: {item['summary']}\n")
            f.write(f"  - 预估工时: {item['estimated_effort']}\n")
        f.write(f"\n*共 {len(coverage['api_coverage'])} 项 API 测试*\n\n")

        # 测试场景
        f.write("## 测试场景示例\n\n")
        for scenario in matrix["test_scenarios"][:10]:
            f.write(f"### {scenario['id']}: {scenario['name']}\n")
            f.write(f"**类型**: {scenario['type']}  ")
            f.write(f"**优先级**: {scenario['priority']}\n\n")
            f.write(f"**描述**: {scenario['description']}\n\n")
            f.write("**步骤**:\n")
            for step in scenario["steps"]:
                f.write(f"1. {step}\n")
            f.write(f"\n**预期结果**: {scenario['expected_result']}\n\n")

        # 资源估算
        f.write("## 资源估算\n\n")
        resource = matrix["resource_estimation"]
        f.write(f"- **总测试场景**: {resource['total_test_scenarios']} 个\n")
        f.write(f"- **预计工时**: {resource['estimated_hours']} 小时\n")
        f.write(f"- **团队规模**: {resource['team_size']}\n")
        f.write(f"- **时间线**: {resource['timeline_weeks']} 周\n")
        f.write(f"- **测试工具**: {', '.join(resource['tools'])}\n\n")

        print(f"Markdown 报告已保存到: {output_file}")


def main():
    """命令行入口"""
    if len(sys.argv) < 3:
        print("用法: python generate_test_matrix.py <需求分析文件> <API分析文件>")
        print(
            "示例: python generate_test_matrix.py requirements_analysis.json swagger_analysis.json"
        )
        sys.exit(1)

    requirements_file = sys.argv[1]
    api_file = sys.argv[2]

    try:
        requirements = load_requirements(requirements_file)
        api_analysis = load_api_analysis(api_file)

        matrix = generate_test_matrix(requirements, api_analysis)

        if len(sys.argv) > 3 and sys.argv[3] == "--json":
            print(json.dumps(matrix, ensure_ascii=False, indent=2))
        else:
            print_matrix_summary(matrix)

            # 保存 JSON 文件
            json_file = "test_matrix.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(matrix, f, ensure_ascii=False, indent=2)
            print(f"完整测试矩阵已保存到: {json_file}")

            # 导出 Markdown 报告
            md_file = "test_matrix_report.md"
            export_to_markdown(matrix, md_file)

    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
