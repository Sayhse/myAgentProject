from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph.state import CompiledStateGraph

from .mcp_tools import (
    bash_tool,
    edit_file_tool,
    glob_tool,
    grep_tool,
    read_file_tool,
    task_tool,
    todowrite_tool,
    write_file_tool,
)


def _normalize_project_root(project_root: str | Path) -> str:
    """将项目根路径规范化为绝对路径字符串。"""
    p = Path(project_root).expanduser().resolve()
    return str(p)


def get_ci_tools():
    """
    CI agent 使用的工具集合：
    - bash: 运行测试脚本、安装依赖、生成报告
    - grep: 在代码和日志中搜索错误信息
    - read/write/edit: 查看和修改源码
    - glob: 定位相关文件
    - todowrite/task: 记录修复步骤和复杂任务
    """
    return [
        bash_tool,
        grep_tool,
        read_file_tool,
        write_file_tool,
        edit_file_tool,
        glob_tool,
        todowrite_tool,
        task_tool,
    ]


def build_ci_agent(llm: BaseChatModel) -> CompiledStateGraph:
    """
    基于 langchain 创建一个 Tool-calling Agent，用于 CI “执行-评估-修复”闭环。

    该 agent 的职责：
    1. 使用 automated-test-runner 目录中的脚本执行完整测试流程
    2. 当测试失败时，分析错误日志（借助 grep/read），定位问题代码
    3. 使用 edit 工具进行小步修复（如导入、参数错误、断言调整等）
    4. 重复运行测试直到：
       - 全部通过；或
       - 达到合理的尝试次数，再输出详细失败报告
    """
    system_prompt = (
        "你是一个 CI 执行与自我修复的专用代理，围绕 automated-test-runner 技能工作。\n"
        "你的目标：在给定项目根目录中，自动执行测试、分析失败原因、小步修改代码、反复重跑，"
        "尝试在有限次数内修复常见错误，并最终生成可读的测试报告总结。\n\n"
        "工作约束：\n"
        "1. 始终优先使用项目中已有的脚本：\n"
        "   - skills/automated-test-runner/scripts/parse_readme.py\n"
        "   - skills/automated-test-runner/scripts/run_tests.py\n"
        "   - skills/automated-test-runner/scripts/fix_errors.py\n"
        "   - skills/automated-test-runner/scripts/generate_report.py\n"
        "   在调用它们时，请使用 bash 工具，并确保 cwd 设置为项目根目录或合适的子目录。\n"
        "2. 当测试失败时：\n"
        "   - 使用 grep/read 工具分析错误日志和相关源码\n"
        "   - 只做小范围、可解释的修改（如修复导入路径、参数顺序、明显的断言错误）\n"
        "   - 每次修改后都要重新运行测试验证结果\n"
        "3. 使用 todowrite/task 工具记录关键修复步骤和后续建议，方便人类查看。\n"
        "4. 最终输出时，必须包含：\n"
        "   - 测试执行概览（命令、次数、耗时大致描述）\n"
        "   - 修复尝试摘要（修改了哪些文件、做了哪些变更）\n"
        "   - 最终测试结果（全部通过 / 仍然失败 & 失败概况）\n"
        "   - 如果生成了 Allure 报告，请给出报告目录路径。\n"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
        ]
    )

    tools = get_ci_tools()
    agent = create_agent(model=llm, tools=tools, system_prompt=system_prompt)
    # agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
    # executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent


@dataclass
class CiResult:
    """CI 执行的结果封装。"""

    project_root: str
    raw_output: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_root": self.project_root,
            "raw_output": self.raw_output,
        }


class CiAgentOrchestrator:
    """
    便于在 Python 代码中直接调用的 CI 封装：
    - 负责构建 AgentExecutor
    - 暴露 run_ci(project_root, extra_instructions) 入口
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self.llm = llm
        self._executor = build_ci_agent(llm)

    def run_ci(
        self,
        project_root: str | Path,
        extra_instructions: Optional[str] = None,
    ) -> CiResult:
        """
        在指定项目根目录下执行自动化测试 + 自我修复闭环。

        参数：
        - project_root: 项目根目录路径（应包含 README.md 和测试代码）
        - extra_instructions: 可选的额外控制指令，例如：
          “请只尝试最多两轮代码修改”，
          “优先修复登录模块相关的失败”等。
        """
        root = _normalize_project_root(project_root)

        user_task = (
            "请在下面的项目根目录中，执行完整的 CI 流程：\n"
            f"- 项目根目录: {root}\n\n"
            "核心步骤建议（可根据实际情况调整）：\n"
            "1. 使用 skills/automated-test-runner/scripts/parse_readme.py 解析 README.md，"
            "   获取安装依赖和测试命令。\n"
            "2. 使用 run_tests.py 或 README 中的测试命令运行测试。\n"
            "3. 如果有失败：\n"
            "   - 使用 grep/read 工具查看报错栈和相关源码\n"
            "   - 使用 edit 工具进行小范围修复\n"
            "   - 再次运行测试验证\n"
            "4. 使用 generate_report.py 或相关命令生成 Allure 报告（如果项目支持）。\n"
            "5. 总结整个过程并输出人类可读的报告。\n"
        )

        if extra_instructions:
            user_task += f"\n额外要求：{extra_instructions}\n"

        # 将项目根路径也通过上下文告知 agent，方便其设置 bash 的 cwd 等。
        result = self._executor.invoke(
            {
                # "input": user_task,
                # "chat_history": [],
                "messages": [{"role": "user",
                              "content": user_task}]
            }
        )

        # AgentExecutor 返回的 result 通常包含 'output' 字段
        raw_output = ""
        if isinstance(result, dict):
            raw_output = str(result.get("output", "")) or str(result)
        else:
            raw_output = str(result)

        return CiResult(project_root=root, raw_output=raw_output)


