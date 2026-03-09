# @Time    : 2026/3/4 15:52
# @Author  : Yun
# @FileName: code_generator_demo
# @Software: PyCharm
# @Desc    :
import time

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from auto_test_assistant.agents.code_generator_agent import CodeGeneratorAgentSystem


def build_llm() -> BaseChatModel:
    """
    构建底层 LLM。
    默认使用 OpenAI 风格接口，你可以根据自己环境替换为其他实现（如自建 LLM 网关）。
    需要环境变量：
    - OPENAI_API_KEY
    - OPENAI_MODEL
    """
    llm = init_chat_model(model="deepseek-chat", model_provider="deepseek", max_tokens=8192)
    return llm


time.sleep(1)
llm = build_llm()
system = CodeGeneratorAgentSystem(llm)
steps = [{'id': 1, 'value': '截图发送给视觉模型，获取账号输入框的坐标x,y；点击输入框，输入账号：18979775270；'},
         {'id': 2, 'value': '截图发送给视觉模型，获取密码输入框的坐标x,y；点击输入框，输入密码：18979775270；'},
         {'id': 3, 'value': "截图发送给视觉模型， 定位'登录按钮'的坐标x,y；"}, {'id': 4, 'value': '点击按钮；'},
         {'id': 5, 'value': '等待10秒；'},
         {'id': 6, 'value': "截图桌面发送截图给视觉模型，询问'是否出现桌面图标/任务栏'"}]
system.execute_use_case_step("截图发送给视觉模型，获取账号输入框的坐标x,y；点击输入框，输入账号：18979775270；", steps, "./scripts/use_case_demo.py")
