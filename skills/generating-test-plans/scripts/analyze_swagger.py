#!/usr/bin/env python3
"""
Swagger/OpenAPI 分析器
解析 Swagger JSON 文件，提取 API 端点信息
"""

import json
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Any, Optional
import re


def load_swagger(source: str) -> Dict[str, Any]:
    """
    加载 Swagger 定义

    Args:
        source: 文件路径或 URL

    Returns:
        Swagger JSON 字典
    """
    # 判断是文件路径还是 URL
    if source.startswith(("http://", "https://")):
        return load_from_url(source)
    else:
        return load_from_file(source)


def load_from_url(url: str) -> Dict[str, Any]:
    """从 URL 加载 Swagger JSON"""
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode("utf-8")
            return json.loads(content)
    except Exception as e:
        raise Exception(f"无法从 URL 加载 Swagger: {str(e)}")


def load_from_file(file_path: str) -> Dict[str, Any]:
    """从文件加载 Swagger JSON"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_swagger(swagger_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析 Swagger 定义，提取 API 信息

    Args:
        swagger_data: Swagger JSON 数据

    Returns:
        包含分析结果的字典
    """
    result = {
        "metadata": {
            "title": swagger_data.get("info", {}).get("title", "未知"),
            "description": swagger_data.get("info", {}).get("description", ""),
            "version": swagger_data.get("info", {}).get("version", "1.0"),
            "openapi_version": swagger_data.get(
                "openapi", swagger_data.get("swagger", "未知")
            ),
            "host": swagger_data.get("host", ""),
            "base_path": swagger_data.get("basePath", ""),
            "schemes": swagger_data.get("schemes", ["http"]),
        },
        "endpoints": [],
        "security_schemes": [],
        "tags": [],
        "models": [],
    }

    # 提取端点信息
    paths = swagger_data.get("paths", {})
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() in [
                "get",
                "post",
                "put",
                "delete",
                "patch",
                "head",
                "options",
            ]:
                endpoint_info = {
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "operation_id": details.get("operationId", ""),
                    "tags": details.get("tags", []),
                    "parameters": [],
                    "responses": [],
                    "security": details.get("security", []),
                    "consumes": details.get("consumes", []),
                    "produces": details.get("produces", []),
                }

                # 提取参数
                for param in details.get("parameters", []):
                    param_info = {
                        "name": param.get("name", ""),
                        "in": param.get("in", ""),
                        "required": param.get("required", False),
                        "type": param.get(
                            "type", param.get("schema", {}).get("type", "")
                        ),
                        "description": param.get("description", ""),
                        "enum": param.get("enum", []),
                    }
                    endpoint_info["parameters"].append(param_info)

                # 提取响应
                for status_code, response in details.get("responses", {}).items():
                    response_info = {
                        "code": status_code,
                        "description": response.get("description", ""),
                        "content_type": list(response.get("content", {}).keys()),
                    }
                    endpoint_info["responses"].append(response_info)

                result["endpoints"].append(endpoint_info)

    # 提取安全方案
    security_schemes = swagger_data.get("components", {}).get("securitySchemes", {})
    for name, scheme in security_schemes.items():
        result["security_schemes"].append(
            {
                "name": name,
                "type": scheme.get("type", ""),
                "description": scheme.get("description", ""),
            }
        )

    # 提取标签
    result["tags"] = swagger_data.get("tags", [])

    # 提取模型/架构（简化版）
    schemas = swagger_data.get("components", {}).get("schemas", {})
    for name, schema in schemas.items():
        model_info = {
            "name": name,
            "type": schema.get("type", ""),
            "properties": list(schema.get("properties", {}).keys()),
            "required": schema.get("required", []),
        }
        result["models"].append(model_info)

    return result


def generate_test_scenarios(endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    为 API 端点生成测试场景

    Args:
        endpoints: 端点列表

    Returns:
        测试场景列表
    """
    test_scenarios = []

    for endpoint in endpoints:
        # 基础场景
        scenario = {
            "endpoint": endpoint["path"],
            "method": endpoint["method"],
            "scenarios": [],
        }

        # 正常流程测试
        normal_scenario = {
            "name": "正常流程",
            "description": f"{endpoint['method']} {endpoint['path']} - 有效请求",
            "test_type": "positive",
            "priority": "high",
        }
        scenario["scenarios"].append(normal_scenario)

        # 参数测试（如果有参数）
        for param in endpoint["parameters"]:
            if param["in"] in ["query", "path", "header"]:
                # 边界值测试
                boundary_scenario = {
                    "name": f"参数测试 - {param['name']}",
                    "description": f"测试参数 {param['name']} 的边界值和无效值",
                    "test_type": "boundary",
                    "priority": "medium",
                }
                scenario["scenarios"].append(boundary_scenario)

        # 错误场景测试
        error_scenario = {
            "name": "错误处理",
            "description": f"{endpoint['method']} {endpoint['path']} - 无效请求和错误响应",
            "test_type": "negative",
            "priority": "high",
        }
        scenario["scenarios"].append(error_scenario)

        # 安全测试（如果需要认证）
        if endpoint["security"]:
            security_scenario = {
                "name": "安全测试",
                "description": f"验证 {endpoint['method']} {endpoint['path']} 的认证和授权",
                "test_type": "security",
                "priority": "high",
            }
            scenario["scenarios"].append(security_scenario)

        test_scenarios.append(scenario)

    return test_scenarios


def print_summary(result: Dict[str, Any]):
    """打印分析摘要"""
    meta = result["metadata"]

    print("=" * 60)
    print("Swagger API 分析结果")
    print("=" * 60)
    print(f"API 名称: {meta['title']}")
    print(f"版本: {meta['version']}")
    print(f"OpenAPI 版本: {meta['openapi_version']}")
    print(f"端点数量: {len(result['endpoints'])}")
    print(f"安全方案: {len(result['security_schemes'])}")
    print(f"数据模型: {len(result['models'])}")
    print()

    # 按方法统计
    method_counts = {}
    for endpoint in result["endpoints"]:
        method = endpoint["method"]
        method_counts[method] = method_counts.get(method, 0) + 1

    print("端点统计:")
    for method, count in method_counts.items():
        print(f"  {method}: {count} 个端点")

    print()
    print("标签:")
    for tag in result["tags"][:10]:
        print(f"  - {tag.get('name', tag.get('description', '未知'))}")

    print()
    print("示例端点:")
    for i, endpoint in enumerate(result["endpoints"][:5], 1):
        print(f"  {i}. {endpoint['method']} {endpoint['path']}")
        if endpoint["summary"]:
            print(f"     摘要: {endpoint['summary'][:60]}...")

    # 生成测试场景
    test_scenarios = generate_test_scenarios(result["endpoints"])
    print()
    print(f"建议测试场景: {sum(len(s['scenarios']) for s in test_scenarios)} 个")

    print("=" * 60)


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python analyze_swagger.py <文件路径或URL>")
        print("示例: python analyze_swagger.py swagger.json")
        print("示例: python analyze_swagger.py https://api.example.com/swagger.json")
        sys.exit(1)

    source = sys.argv[1]

    try:
        swagger_data = load_swagger(source)
        result = analyze_swagger(swagger_data)

        if len(sys.argv) > 2 and sys.argv[2] == "--json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_summary(result)

            # 保存详细结果到文件
            output_file = "swagger_analysis.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"详细结果已保存到: {output_file}")

    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
