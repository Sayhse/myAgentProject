# @Time    : 2026/2/18 18:29
# @Author  : Yun
# @FileName: demo_1
# @Software: PyCharm
# @Desc    :

import asyncio
import time

from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent


async def main():
    client = MultiServerMCPClient(
        {
            # "amap-maps": {
            #     "command": "npx.cmd",
            #     "args": ["-y", "@amap/amap-maps-mcp-server"],
            #     "env": {
            #         "AMAP_MAPS_API_KEY": "508c82722b477f05c7b4d6d5682d40bc"
            #     },
            #     "transport": "stdio"
            # },
            # "calculate": {
            #     "transport": "sse",
            #     "url": "http://127.0.0.1:8000/sse",
            # },
            "playwright": {
                "command": "npx.cmd",
                "args": [
                    "@playwright/mcp@latest"
                ],
                "transport": "stdio"
            },
            # "computer-control-mcp": {
            #     "command": "uvx.cmd",
            #     "args": [
            #         "computer-control-mcp@latest"
            #     ],
            #     "transport": "stdio"
            # }
        }
    )

    tools = await client.get_tools()
    for tool in tools:
        print("tool_name:", tool.name)
        print("tool_description:", tool.description)
        print("tool_args:", tool.args)
    llm = init_chat_model(model="deepseek-chat", model_provider="deepseek")
    agent = create_agent(
        model=llm,
        tools=tools
    )
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "帮我搜索一下openclaw"}]}
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
