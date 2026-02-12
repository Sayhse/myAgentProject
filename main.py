from __future__ import annotations

import os

from langchain_core.language_models import BaseChatModel

"""
一个简单的交互式入口示例：

- 启动多 agent 系统（基于 skills 目录和 MCP 工具）
- 支持用户输入问题
- 支持通过“上传文件路径”的方式，让 agent 解析文件生成测试计划/测试用例

实际项目中，你可以将 MultiAgentSystem 集成到 Web 接口、桌面应用或 CI 流水线中。
"""

from dotenv import load_dotenv
from typing import Optional


from langchain.chat_models import init_chat_model

from agent_system import MultiAgentSystem, load_all_skills


def build_llm() -> BaseChatModel:
    """
    构建底层 LLM。
    默认使用 OpenAI 风格接口，你可以根据自己环境替换为其他实现（如自建 LLM 网关）。
    需要环境变量：
    - OPENAI_API_KEY
    - OPENAI_MODEL（可选，默认 gpt-4.1-mini 或你可用的模型）
    """
    llm = init_chat_model(model="deepseek-chat", model_provider="deepseek", max_tokens=8192)
    return llm


def interactive_cli(uploaded_file: Optional[str] = None) -> None:
    """
    一个简单的命令行循环，用于本地调试：
    - 可以在启动时指定 uploaded_file 路径，模拟“用户上传文件”
    """
    llm = build_llm()
    system = MultiAgentSystem(llm=llm, skills_root="skills")

    print("已加载的技能：")
    for s in load_all_skills("skills"):
        print(f"- {s.name}: {s.description}")
    print("\n输入你的问题（输入 exit 退出）：")

    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出。")
            break
        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            print("退出。")
            break

        answer = system.handle_request(user_query=q, uploaded_file_path=uploaded_file)
        print("\n=== Agent 回复 ===")
        print(answer)
        print("==================\n")


if __name__ == "__main__":
    load_dotenv()
    # 你可以通过环境变量 UPLOADED_FILE 指定一个本地文件路径，用于调试“上传文件生成测试用例/计划”
    uploaded = os.getenv("UPLOADED_FILE")
    interactive_cli(uploaded_file=uploaded)


