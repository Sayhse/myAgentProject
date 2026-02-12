from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from openai import BaseModel
from pydantic import Field

from langchain_core.tools import tool, BaseTool
from langchain_community.document_loaders import WebBaseLoader


def _ensure_str_path(path: str | Path) -> Path:
    return path if isinstance(path, Path) else Path(path)


@tool("read", return_direct=False, description="读取文件内容")
def read_file_tool(path: str) -> str:
    """读取指定文件的全部内容。参数: path=文件路径(相对或绝对)。"""
    p = _ensure_str_path(path)
    if not p.is_file():
        return f"[read] 文件不存在: {p}"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"[read] 读取失败: {e}"


@tool("write", return_direct=False, description="写入/创建文件")
def write_file_tool(path: str, content: str) -> str:
    """写入/创建文件，覆盖原内容。参数: path=文件路径, content=写入内容。"""
    p = _ensure_str_path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"[write] 已写入文件: {p}"
    except Exception as e:
        return f"[write] 写入失败: {e}"


@tool("edit", return_direct=False, description="精确编辑文件内容（替换字符串）")
def edit_file_tool(path: str, old: str, new: str, count: int = -1) -> str:
    """
    在文件中进行字符串替换。
    参数:
    - path: 文件路径
    - old: 需要被替换的原字符串
    - new: 新字符串
    - count: 替换次数，默认 -1 表示全部替换
    """
    p = _ensure_str_path(path)
    if not p.is_file():
        return f"[edit] 文件不存在: {p}"
    try:
        text = p.read_text(encoding="utf-8")
        new_text = text.replace(old, new, count if count >= 0 else text.count(old))
        p.write_text(new_text, encoding="utf-8")
        return f"[edit] 已替换 {path} 中的内容"
    except Exception as e:
        return f"[edit] 编辑失败: {e}"


@tool("glob", return_direct=False, description="文件模式匹配（*.py, **/*.js等）")
def glob_tool(pattern: str, root: str = ".") -> List[str]:
    """按模式匹配文件，例如: pattern='**/*.py', root='.'。返回匹配到的相对路径列表。"""
    base = _ensure_str_path(root)
    matches = [str(p.relative_to(base)) for p in base.rglob(pattern)]
    return matches


@tool("grep", return_direct=False, description="文件内容正则搜索")
def grep_tool(pattern: str, root: str = ".", ignore_case: bool = True) -> List[str]:
    """
    在目录下递归搜索包含正则 pattern 的文件行。
    返回格式: 'relative/path:行号:内容'
    """
    base = _ensure_str_path(root)
    flags = re.IGNORECASE if ignore_case else 0
    regex = re.compile(pattern, flags)
    results: List[str] = []

    for file in base.rglob("*"):
        if not file.is_file():
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                rel = str(file.relative_to(base))
                results.append(f"{rel}:{i}:{line}")
    return results


@tool("bash", return_direct=False, description="执行shell命令（git、npm、docker等）")
def bash_tool(command: str, cwd: Optional[str] = None, timeout: int = 600) -> str:
    """执行 shell 命令（Windows 下使用 PowerShell / *nix 使用 /bin/bash），返回 stdout/stderr。"""
    workdir = _ensure_str_path(cwd) if cwd else None
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(workdir) if workdir else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return f"[bash] exit={result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "[bash] 命令执行超时"
    except Exception as e:
        return f"[bash] 执行失败: {e}"


@dataclass
class TodoItem:
    id: str
    content: str
    status: str = "pending"


_TODO_STORE: dict[str, TodoItem] = {}

item_schema = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "content", "status"],
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "任务唯一标识符"
                    },
                    "content": {
                        "type": "string",
                        "description": "任务描述（应遵循SMART原则：具体、可衡量、可实现、相关、有时限）"
                    },
                    "status": {
                        "type": "string",
                        "description": "任务状态",
                        "enum": ["pending", "in-progress", "completed", "failed", "cancelled"],
                        "default": "pending"
                    },
                    "priority": {
                        "type": "string",
                        "description": "任务优先级",
                        "enum": ["must-have", "should-have", "could-have", "won't-have", "high", "medium", "low"],
                        "default": "low"
                    },
                    "depends_on": {
                        "type": "array",
                        "description": "依赖的任务ID列表",
                        "items": {
                          "type": "string"
                        },
                        "default": []
                    },
                    "completion_criteria": {
                        "type": "string",
                        "description": "完成标准（明确定义任务完成的判断条件）",
                        "default": ""
                    },
                    "estimated_tools": {
                        "type": "array",
                        "description": "预估需要的工具列表",
                        "items": {
                            "type": "string",
                            "enum": ["read", "write", "edit", "glob", "grep", "bash", "todowrite", "task", "skill", "question", "webfetch"]
                        },
                        "default": []
                    }
                }
            }
        }
    },
    "required": ["items"]
}


@tool("todowrite", return_direct=False, description="创建和管理结构化任务列表，支持思维链工作流程",
      args_schema=item_schema)
def todowrite_tool(items: List[dict]) -> str:
    """
    创建或更新结构化任务列表。

    参数: items=[{id, content, status, priority?, depends_on?, completion_criteria?}]

    必需字段：
    - id: 任务唯一标识符（字符串）
    - content: 任务描述（应遵循SMART原则：具体、可衡量、可实现、相关、有时限）
    - status: 任务状态，可选值：pending, in-progress, completed, failed, cancelled

    可选字段（可在content中描述，或作为独立字段）：
    - priority: 优先级（must-have/should-have/could-have/won't-have 或 high/medium/low）
    - depends_on: 依赖的任务ID列表（字符串数组）
    - completion_criteria: 完成标准（明确定义任务完成的判断条件）
    - estimated_tools: 预估需要的工具列表（如 ["read", "write", "bash"]）

    使用场景：
    1. 战略规划阶段：创建完整的TodoList，包含所有任务及其依赖关系
    2. 执行阶段：更新任务状态（pending -> in-progress -> completed）
    3. 反思阶段：调整任务列表，添加新任务或修改现有任务

    示例：
    [
        {
            "id": "1",
            "content": "分析需求文档，提取核心功能模块（必须完成）",
            "status": "pending",
            "priority": "must-have"
        },
        {
            "id": "2",
            "content": "创建测试计划文档结构（依赖任务1）",
            "status": "pending",
            "depends_on": ["1"],
            "priority": "must-have"
        }
    ]
    """
    for raw in items:
        # 提取所有字段，包括可选字段
        item_data = {
            "id": str(raw.get("id")),
            "content": str(raw.get("content")),
            "status": str(raw.get("status", "pending")),
        }
        # 保留其他可选字段到 metadata
        metadata = {}
        for key in ["priority", "depends_on", "completion_criteria", "estimated_tools"]:
            if key in raw:
                metadata[key] = raw[key]

        item = TodoItem(
            id=item_data["id"],
            content=item_data["content"],
            status=item_data["status"],
        )
        # 将元数据存储到 item 的 __dict__ 中（如果 TodoItem 支持）
        if metadata:
            item.__dict__.update(metadata)

        _TODO_STORE[item.id] = item

    # 返回当前所有任务，包括元数据
    result_dict = {}
    for k, v in _TODO_STORE.items():
        result_dict[k] = vars(v)

    return "[todowrite] 当前任务列表: " + json.dumps(
        result_dict, ensure_ascii=False, indent=2
    )


@tool("task", return_direct=False, description="启动专用代理进行复杂探索（代码库分析、多步骤任务）")
def task_tool(description: str) -> str:
    """
    启动专用代理进行复杂探索的占位符工具。
    目前仅记录任务描述，真实实现可在此基础上扩展。
    """
    return f"[task] 已记录复杂任务描述，稍后由专用代理处理: {description}"


# @tool("skill", return_direct=False)
# def skill_tool(name: str, action: str = "describe") -> str:
#     """
#     skill 工具占位符。
#     目前支持: action='describe' 时，返回该技能的用途说明（由上层注入）。
#     实际的技能路由由主 agent / 子 agent 控制。
#     """
#     return f"[skill] 请求技能: {name}, action={action}（实际执行由多agent系统负责）"


# 全局存储用户问答（用于测试和预配置答案）
_QUESTION_ANSWER_STORE: Dict[str, str] = {}
# 预配置答案文件路径（可选）
_QUESTION_ANSWER_FILE = Path("question_answers.json")

@tool("question", return_direct=False, description="交互式提问（收集需求、澄清指令）")
def question_tool(prompt: str, question_id: Optional[str] = None) -> str:
    """
    交互式提问工具，支持Human-in-the-Loop机制。
    
    参数:
    - prompt: 向用户提问的具体问题
    - question_id: 可选的问题标识符，用于从预配置答案中查找回答
    
    工作流程:
    1. 检查是否有预配置答案（通过question_id或prompt匹配）
    2. 如果有预配置答案，直接返回答案
    3. 如果没有预配置答案，返回结构化的问题信息供上层处理
    4. 记录问题到日志文件便于调试
    
    预配置答案支持:
    - 全局字典 _QUESTION_ANSWER_STORE
    - 外部文件 question_answers.json
    - 环境变量（未来扩展）
    
    返回格式:
    - 如果有答案: [question] 用户已回答: {答案内容}
    - 如果没有答案: [question] 需要用户回答: {问题内容} [ID: {question_id}]
    """
    import os
    from datetime import datetime
    
    # 生成问题ID（如果未提供）
    if question_id is None:
        # 基于prompt生成简单的哈希ID
        import hashlib
        question_id = hashlib.md5(prompt.encode()).hexdigest()[:8]
    
    # 尝试从全局存储获取答案
    if question_id in _QUESTION_ANSWER_STORE:
        answer = _QUESTION_ANSWER_STORE[question_id]
        return f"[question] 用户已回答（来自内存存储）: {answer}"
    
    # 尝试从预配置答案文件获取答案
    if _QUESTION_ANSWER_FILE.is_file():
        try:
            answers_data = json.loads(_QUESTION_ANSWER_FILE.read_text(encoding="utf-8"))
            if isinstance(answers_data, dict):
                # 尝试通过question_id查找
                if question_id in answers_data:
                    answer = answers_data[question_id]
                    return f"[question] 用户已回答（来自文件存储）: {answer}"
                # 尝试通过prompt关键词查找
                for key, value in answers_data.items():
                    if isinstance(key, str) and key in prompt:
                        return f"[question] 用户已回答（关键词匹配）: {value}"
        except Exception as e:
            # 文件读取失败，继续使用标准流程
            pass
    
    # 检查环境变量中是否有预配置答案（格式：QUESTION_ANSWER_{QUESTION_ID}）
    env_key = f"QUESTION_ANSWER_{question_id.upper()}"
    if env_key in os.environ:
        answer = os.environ[env_key]
        return f"[question] 用户已回答（来自环境变量）: {answer}"
    
    # 没有预配置答案，返回结构化问题信息
    # 记录问题到日志文件（便于调试和跟踪）
    log_dir = Path("question_logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"questions_{datetime.now().strftime('%Y%m%d')}.log"
    
    question_record = {
        "timestamp": datetime.now().isoformat(),
        "question_id": question_id,
        "prompt": prompt,
        "status": "pending"
    }
    
    try:
        # 追加记录到日志文件
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(question_record, ensure_ascii=False) + "\n")
    except Exception:
        # 日志写入失败不影响主要功能
        pass
    
    # 返回结构化的问题信息
    # 注意：在纯后端模式下，上层需要解析此输出并获取用户回答
    # 然后通过某种机制（如更新预配置答案）提供回答
    structured_output = {
        "type": "question",
        "question_id": question_id,
        "prompt": prompt,
        "timestamp": datetime.now().isoformat(),
        "instructions": "请提供此问题的答案，可通过以下方式：1. 更新question_answers.json文件 2. 设置环境变量 3. 通过其他交互机制"
    }
    
    return f"[question] 需要用户回答: {prompt}\n" + \
           f"[question] 问题ID: {question_id}\n" + \
           f"[question] 结构化信息: {json.dumps(structured_output, ensure_ascii=False)}"


def set_question_answer(question_id: str, answer: str) -> None:
    """
    设置预配置答案到内存存储。
    用于测试和开发阶段提供模拟用户回答。
    """
    global _QUESTION_ANSWER_STORE
    _QUESTION_ANSWER_STORE[question_id] = answer


def load_question_answers_from_file(file_path: Optional[str] = None) -> bool:
    """
    从JSON文件加载预配置答案。
    
    参数:
        file_path: JSON文件路径，默认为 question_answers.json
        
    返回:
        bool: 是否成功加载
    """
    global _QUESTION_ANSWER_STORE, _QUESTION_ANSWER_FILE
    
    if file_path:
        target_file = Path(file_path)
    else:
        target_file = _QUESTION_ANSWER_FILE
    
    if not target_file.is_file():
        return False
    
    try:
        answers_data = json.loads(target_file.read_text(encoding="utf-8"))
        if isinstance(answers_data, dict):
            _QUESTION_ANSWER_STORE.update(answers_data)
            return True
    except Exception as e:
        print(f"[question] 加载预配置答案失败: {e}")
    
    return False


def save_question_answers_to_file(file_path: Optional[str] = None) -> bool:
    """
    将当前内存中的预配置答案保存到JSON文件。
    
    参数:
        file_path: JSON文件路径，默认为 question_answers.json
        
    返回:
        bool: 是否成功保存
    """
    global _QUESTION_ANSWER_STORE, _QUESTION_ANSWER_FILE
    
    if file_path:
        target_file = Path(file_path)
    else:
        target_file = _QUESTION_ANSWER_FILE
    
    try:
        # 确保目录存在
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(json.dumps(_QUESTION_ANSWER_STORE, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[question] 保存预配置答案失败: {e}")
    
    return False


# 初始化时尝试加载预配置答案文件
try:
    load_question_answers_from_file()
except Exception:
    # 初始化失败不影响主要功能
    pass


class WebURLInput(BaseModel):
    """链接解析输入"""
    urls: list[str] = Field(description="用户问题中携带的所有url")


@tool("webfetch", return_direct=False, args_schema=WebURLInput,
      description="这是一个解析链接的工具助手，可以获取用户发送的链接并读取链接内所有内容，返回的为链接中内容")
def webfetch_tool(urls: list[str]) -> str:
    """获取链接中的内容"""
    loader = WebBaseLoader(urls)
    docs = loader.load()
    web_content = docs[0].page_content
    return web_content


def list_all_mcp_tools() -> List[BaseTool]:
    """返回需要注册到所有 agent 的 MCP 风格工具列表。"""
    return [
        read_file_tool,
        write_file_tool,
        edit_file_tool,
        glob_tool,
        grep_tool,
        bash_tool,
        todowrite_tool,
        task_tool,
        # skill_tool,
        question_tool,
        webfetch_tool,
    ]
