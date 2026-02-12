#!/usr/bin/env python3
"""
需求文档解析器
支持格式：.txt, .md, .pdf, .docx

使用说明：
1. 直接运行解析文件：python parse_requirements.py <文件路径>
2. 作为模块导入：from parse_requirements import extract_requirements
"""

import re
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


def extract_requirements(file_path: str) -> Dict[str, Any]:
    """
    从需求文档中提取结构化信息

    Args:
        file_path: 需求文档路径

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
    return analyze_content(content)


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


def analyze_content(content: str) -> Dict[str, Any]:
    """
    分析需求文档内容，提取结构化信息
    """
    lines = content.split("\n")

    # 初始化结果
    result = {
        "metadata": {
            "total_lines": len(lines),
            "total_words": len(content.split()),
            "file_type": "需求文档",
        },
        "functional_requirements": [],
        "non_functional_requirements": [],
        "user_stories": [],
        "business_rules": [],
        "priorities": {"high": [], "medium": [], "low": []},
        "keywords": [],
    }

    # 常见模式匹配
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # 用户故事模式：As a... I want... So that...
        if re.match(r"(?i)as a\s+.+\s+i want\s+.+\s+so that\s+.+", line):
            result["user_stories"].append({"text": line, "line": i + 1})

        # 功能需求：包含"应"、"必须"、"需要"等关键词
        elif re.search(r"应|必须|需要|要求|功能|特性", line):
            # 提取优先级
            priority = "medium"
            if re.search(r"重要|关键|必须|紧急", line):
                priority = "high"
            elif re.search(r"可选|建议|期望", line):
                priority = "low"

            result["functional_requirements"].append(
                {"text": line, "line": i + 1, "priority": priority}
            )

            # 添加到优先级列表
            result["priorities"][priority].append(line)

        # 业务规则：包含"规则"、"政策"、"标准"
        elif re.search(r"规则|政策|标准|规范|约束|条件", line):
            result["business_rules"].append({"text": line, "line": i + 1})

        # 非功能需求：性能、安全、可用性等
        elif re.search(r"性能|安全|可用|可靠|兼容|易用", line):
            result["non_functional_requirements"].append({"text": line, "line": i + 1})

    # 提取关键词（简单实现）
    words = re.findall(r"\b[A-Za-z\u4e00-\u9fa5]{2,}\b", content)
    from collections import Counter

    word_counts = Counter(words)
    result["keywords"] = [word for word, count in word_counts.most_common(20)]

    return result


def print_summary(result: Dict[str, Any]):
    """打印解析摘要"""
    if "error" in result:
        print(f"错误: {result['error']}")
        return

    print("=" * 60)
    print("需求文档分析结果")
    print("=" * 60)

    meta = result["metadata"]
    print(f"文档统计: {meta['total_lines']} 行, {meta['total_words']} 词")
    print()

    print(f"功能需求: {len(result['functional_requirements'])} 条")
    for i, req in enumerate(result["functional_requirements"][:5], 1):
        print(f"  {i}. [{req['priority']}] {req['text'][:80]}...")

    print(f"\n用户故事: {len(result['user_stories'])} 条")
    for i, story in enumerate(result["user_stories"][:3], 1):
        print(f"  {i}. {story['text'][:100]}...")

    print(f"\n业务规则: {len(result['business_rules'])} 条")
    for i, rule in enumerate(result["business_rules"][:3], 1):
        print(f"  {i}. {rule['text'][:80]}...")

    print(f"\n非功能需求: {len(result['non_functional_requirements'])} 条")
    for i, nfr in enumerate(result["non_functional_requirements"][:3], 1):
        print(f"  {i}. {nfr['text'][:80]}...")

    print(f"\n高频关键词: {', '.join(result['keywords'][:10])}")
    print("=" * 60)


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python parse_requirements.py <文件路径>")
        print("示例: python parse_requirements.py requirements.docx")
        sys.exit(1)

    file_path = sys.argv[1]
    result = extract_requirements(file_path)

    # 输出 JSON 格式结果
    if len(sys.argv) > 2 and sys.argv[2] == "--json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_summary(result)


if __name__ == "__main__":
    main()
