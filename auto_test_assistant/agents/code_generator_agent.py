# @Time    : 2026/3/2 17:19
# @Author  : Yun
# @FileName: code_generator_agent
# @Software: PyCharm
# @Desc    :
from langchain_core.language_models import BaseChatModel

from auto_test_assistant.utils.tools import list_all_mcp_tools


class CodeGeneratorAgentSystem:
    def __init__(
            self,
            llm: BaseChatModel,
    ) -> None:
        self.llm = llm
        self.tools = list_all_mcp_tools()

    def code_generation(self, use_case: dict):
        return None

