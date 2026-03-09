from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any

from .context import ConversationContext
from .mcp_tools import list_all_mcp_tools
from .review_planning_agent import ReviewPlanningAgent
from .skill_loader import SkillMetadata, load_all_skills


@dataclass
class RoutingDecision:
    """主 agent 对一次用户请求的路由决策结果。"""

    is_simple: bool
    reason: str
    selected_skills: List[str]


class MultiAgentSystem:
    """
    多 agent 系统入口：
    - 初始化时加载所有 SKILL.md 元信息
    - 注册 MCP 工具到主/子 agent
    - 根据用户意图路由到合适的子 agent，或直接由主 agent 回复
    """

    def __init__(
            self,
            llm: BaseChatModel,
            skills_root: str | Path = "skills",
            context: Optional[ConversationContext] = None,
    ) -> None:
        self.llm = llm
        self.skills: List[SkillMetadata] = load_all_skills(skills_root)
        self.tools = list_all_mcp_tools()
        # 会话上下文（短期记忆 / 工具状态等）
        self.context = context or ConversationContext()

    # ------------------- 公共调用入口 -------------------
    def handle_request(
            self,
            user_query: str,
            uploaded_file_path: Optional[str] = None,
    ) -> str:
        """
        对外暴露的统一入口。
        - user_query: 用户自然语言请求
        - uploaded_file_path: 用户“上传”的测试计划/需求文档路径（可选）
        """
        ctx = self.context
        ctx.add_user_message(user_query)

        routing = self._decide_routing(user_query)

        if routing.is_simple or not routing.selected_skills:
            # 简单任务，直接由主 agent 处理
            answer = self._answer_directly(user_query, uploaded_file_path, routing)
            ctx.add_assistant_message(answer, routing=routing.reason)
            return answer

        # 复杂任务：基于选中的技能创建“workflow 型”子 agent
        # 规则：
        # 1. 在 self.skills 中找到对应的 SkillMetadata，拿到 skill.path
        # 2. 读取该 skill 目录下的 SKILL.md 全文
        # 3. 将 SKILL.md 的内容作为子 agent 的 system prompt/workflow 描述
        for skill_name in routing.selected_skills:
            skill = self._find_skill_by_name(skill_name)
            if skill is None:
                continue
            answer = self._run_skill_workflow(
                skill=skill,
                user_query=user_query,
                uploaded_file_path=uploaded_file_path,
            )
            ctx.add_assistant_message(answer, skill=skill.name)
            return answer

        # 如果没有在 self.skills 中找到对应技能，则回退到通用子 agent（使用第一个技能名）
        primary_skill = (
            self._find_skill_by_name(routing.selected_skills[0])
            if routing.selected_skills
            else None
        )
        answer = self._generic_skill_agent_reply(
            user_query=user_query,
            skill=primary_skill,
            uploaded_file_path=uploaded_file_path,
            routing=routing,
        )
        ctx.add_assistant_message(answer, skill=primary_skill.name if primary_skill else None)
        return answer

    # ------------------- 路由决策 -------------------
    def _decide_routing(self, user_query: str) -> RoutingDecision:
        """
        使用 LLM 基于 SKILL 元信息做意图识别与路由决策。
        返回 JSON 字符串，然后解析为 RoutingDecision。
        """
        skills_brief = "\n".join(
            f"- {s.name}: {s.description}" for s in self.skills
        ) or "(当前没有可用技能)"

        judge_info_schema = {
            "type": "object",
            "description": "判断用户请求是简单任务还是需要专项技能的复杂任务的判断结果。",
            "properties": {
                "is_simple": {"type": "boolean",
                              "description": "如果可以直接回答（问答、概念解释、小修改），则为true；如果需要生成测试计划、测试用例、运行测试、自动修复代码等复杂流程，则为false。"},
                "reason": {"type": "string", "description": "用中文解释为什么是简单/复杂任务。"},
                "selected_skills": {"type": "array",
                                    "description": "如果可以直接回答（问答、概念解释、小修改），则为空数组；如果需要生成测试计划、测试用例、运行测试、自动修复代码等复杂流程，则从技能列表中选择一个或多个最相关的技能 name 放入 selected_skills。",
                                    "items": {"type": "string"}}
            },
            "required": ["is_simple", "reason", "selected_skills"]
        }

        system_prompt = (
            "你是一个路由调度器，负责判断用户请求是简单任务还是需要专项技能的复杂任务。\n"
            "你会看到一组可用技能列表（name + description），以及用户的自然语言请求。\n"
            "你可以使用以下 MCP 工具来帮助你完成任务：\n"
            f"{self.tools}\n"
            "请只输出 JSON"
        )

        user_prompt = (
            "可用技能列表：\n"
            f"{skills_brief}\n\n"
            f"用户请求：{user_query}\n\n"
            "请根据上述规则输出 JSON。"
        )

        agent = create_agent(model=self.llm, system_prompt=system_prompt, response_format=judge_info_schema,
                             tools=self.tools)

        # chain = ChatPromptTemplate.from_messages(
        #     [
        #         ("system", system_prompt),
        #         ("human", "{input}"),
        #     ]
        # ) | self.llm | StrOutputParser()

        result = agent.invoke({
            "messages": [
                {"role": "user", "content": user_prompt}]
        })

        # raw = chain.invoke({"input": user_prompt})

        try:
            data = result["structured_response"]
            is_simple = bool(data.get("is_simple", False))
            reason = str(data.get("reason", ""))
            skills = [str(s) for s in data.get("selected_skills", [])]
            return RoutingDecision(is_simple=is_simple, reason=reason, selected_skills=skills)
        except Exception:
            # 解析失败时保守退回简单任务
            return RoutingDecision(
                is_simple=True,
                reason="路由 JSON 解析失败，回退为简单任务处理。",
                selected_skills=[],
            )

    # ------------------- 主 agent 直接回答 -------------------
    def _answer_directly(
            self,
            user_query: str,
            uploaded_file_path: Optional[str],
            routing: RoutingDecision,
    ) -> str:
        """
        简单任务：不启用专项子 agent，由主 agent 直接回答。
        如果带有上传文件，也会作为额外上下文（例如让模型简单分析文档）。
        """
        system_msg = (
            "你是软件测试和自动化方面的助手，可以回答测试计划、测试用例、代码修改等问题。\n"
            "当前路由判断认为这是一个简单任务，请直接、高效地给出答案。"
        )

        messages: List[Any] = [SystemMessage(content=system_msg)]

        if uploaded_file_path:
            path = Path(uploaded_file_path)
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    messages.append(
                        HumanMessage(
                            content=f"以下是用户上传的文件内容（用于参考）：\n\n{content[:8000]}"
                        )
                    )
                except Exception as e:
                    messages.append(
                        HumanMessage(
                            content=f"尝试读取用户上传的文件失败: {e}。你可以忽略文件内容，仅根据问题作答。"
                        )
                    )

        messages.append(
            HumanMessage(
                content=(
                    f"路由决策信息（供你参考，不必复述）：{routing.reason}\n\n"
                    f"用户问题：{user_query}"
                )
            )
        )

        resp = self.llm.invoke(messages)
        return resp.content  # type: ignore[no-any-return]

    # ------------------- 专项：测试用例生成 -------------------
    def _handle_generating_test_cases(
            self,
            user_query: str,
            uploaded_file_path: str,
    ) -> str:
        """
        使用 generating-test-cases 技能，根据上传的测试计划/需求文档生成 pytest 测试用例。
        """
        skill = self._find_skill_by_name("generating-test-cases")
        system_msg = (
            "你是一个“测试用例生成器”子 agent，专门从测试计划或需求文档生成高质量 pytest 测试用例。\n"
            "请基于上传的文件内容，结合用户的补充说明，设计结构化的测试用例，并给出示例 pytest 代码片段。\n"
            "注意突出：测试目标、前置条件、步骤、预期结果，以及必要时的参数化和 Allure 标注。"
        )

        messages: List[Any] = [SystemMessage(content=system_msg)]

        path = Path(uploaded_file_path)
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                messages.append(
                    HumanMessage(
                        content=(
                            f"下面是用户上传的测试计划/需求文档内容（来自技能 {skill.name if skill else 'N/A'}）:\n\n"
                            f"{content[:16000]}"
                        )
                    )
                )
            except Exception as e:
                messages.append(
                    HumanMessage(
                        content=f"读取上传文件失败: {e}。请仅根据用户问题生成测试用例。"
                    )
                )

        messages.append(
            HumanMessage(
                content=(
                    "用户的额外说明/期望：\n"
                    f"{user_query}\n\n"
                    "请先输出一个简要的测试用例列表，然后给出关键测试用例的 pytest 代码示例。"
                )
            )
        )

        resp = self.llm.invoke(messages)
        return resp.content  # type: ignore[no-any-return]

    # ------------------- 专项：测试计划生成 -------------------
    def _handle_generating_test_plans(
            self,
            user_query: str,
            uploaded_file_path: str,
    ) -> str:
        """
        使用 generating-test-plans 技能，根据需求文档或 Swagger 生成测试计划。
        """
        skill = self._find_skill_by_name("generating-test-plans")
        system_msg = (
            "你是一个“测试计划生成器”子 agent，专门从需求文档和 API 定义生成结构化测试计划。\n"
            "请分析上传文件的内容，结合用户问题，输出包含：项目概述、测试范围、测试策略、API 测试计划、"
            "功能测试计划、风险与资源规划等章节的测试计划草案。"
        )

        messages: List[Any] = [SystemMessage(content=system_msg)]

        path = Path(uploaded_file_path)
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                messages.append(
                    HumanMessage(
                        content=(
                            f"以下是用户上传的需求/Swagger 文档内容（来自技能 {skill.name if skill else 'N/A'}）:\n\n"
                            f"{content[:16000]}"
                        )
                    )
                )
            except Exception as e:
                messages.append(
                    HumanMessage(
                        content=f"读取上传文件失败: {e}。请仅根据用户问题生成测试计划。"
                    )
                )

        messages.append(
            HumanMessage(
                content=(
                    "用户的额外说明/期望：\n"
                    f"{user_query}\n\n"
                    "请按照正式测试计划结构化输出内容，适合直接保存为 Markdown 文档。"
                )
            )
        )

        resp = self.llm.invoke(messages)
        return resp.content  # type: ignore[no-any-return]

    # ------------------- 通用子 agent -------------------
    def _generic_skill_agent_reply(
            self,
            user_query: str,
            skill: Optional[SkillMetadata],
            uploaded_file_path: Optional[str],
            routing: RoutingDecision,
    ) -> str:
        """
        对于没有专门处理逻辑的技能，使用该技能的 description 作为 system prompt，构建通用子 agent。
        """
        if skill is None:
            system_msg = (
                "你是一个通用的软件测试/自动化代理，请根据用户问题和可用工具给出最佳答案或操作方案。"
            )
        else:
            system_msg = (
                f"你现在扮演一个具有如下技能的专项子 agent：\n"
                f"技能名：{skill.name}\n"
                f"技能描述：{skill.description}\n\n"
                "请在该技能的职责范围内处理用户请求。"
            )

        messages: List[Any] = [SystemMessage(content=system_msg)]

        if uploaded_file_path:
            path = Path(uploaded_file_path)
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    messages.append(
                        HumanMessage(
                            content=f"用户上传文件内容如下（截断前 16000 字符）：\n\n{content[:16000]}"
                        )
                    )
                except Exception as e:
                    messages.append(
                        HumanMessage(
                            content=f"读取上传文件失败: {e}。你可以忽略文件，仅基于问题作答。"
                        )
                    )

        messages.append(
            HumanMessage(
                content=(
                    f"路由器给出的决策说明（仅供参考，不必复述）：{routing.reason}\n\n"
                    f"用户请求：{user_query}"
                )
            )
        )

        resp = self.llm.invoke(messages)
        return resp.content  # type: ignore[no-any-return]

    # ------------------- 从 SKILL.md 提取工作流程并生成 TodoList（使用 LLM 智能识别）-------------------
    def _extract_workflow_from_skill_md(self, skill_doc: str) -> List[Dict[str, Any]]:
        """
        使用 LLM 从 SKILL.md 文档中智能提取工作流程步骤，生成 TodoList。
        
        策略：
        1. 将 SKILL.md 文档交给 LLM 分析
        2. 让 LLM 识别工作流程、分析步骤、执行步骤等章节
        3. 提取关键步骤并生成结构化的 TodoList
        4. 返回 JSON 格式的任务列表
        """
        
        # 定义返回的 JSON Schema
        workflow_schema = {
            "type": "object",
            "description": "从 SKILL.md 提取的工作流程 TodoList",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "工作流程任务列表，按照执行顺序排列",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "任务唯一标识符，从1开始递增"
                            },
                            "content": {
                                "type": "string",
                                "description": "任务描述，应具体、可执行，遵循SMART原则"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["pending"],
                                "description": "任务初始状态，固定为pending"
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["must-have", "should-have", "could-have", "won't-have"],
                                "description": "任务优先级，使用MoSCoW法"
                            },
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "依赖的任务ID列表，如果没有依赖则为空数组"
                            }
                        },
                        "required": ["id", "content", "status", "priority"]
                    }
                }
            },
            "required": ["todos"]
        }
        
        system_prompt = (
            "你是一个工作流程分析专家，擅长从技能文档中提取工作流程步骤。\n"
            "你的任务是从给定的 SKILL.md 文档中识别并提取工作流程步骤，生成结构化的 TodoList。\n\n"
            "分析要求：\n"
            "1. 仔细阅读整个 SKILL.md 文档\n"
            "2. 识别文档中描述的工作流程、分析步骤、执行步骤等章节\n"
            "3. 提取关键的执行步骤，每个步骤应该是：\n"
            "   - 具体、可执行（遵循SMART原则）\n"
            "   - 有明确的执行顺序\n"
            "   - 可以独立完成或明确依赖关系\n"
            "4. 如果文档中有多个层级的步骤（主步骤和子步骤），优先提取主步骤\n"
            "5. 如果文档中没有明确的工作流程章节，根据文档内容推断合理的执行步骤\n"
            "6. 为每个步骤设置合适的优先级（must-have/should-have/could-have）\n"
            "7. 识别步骤之间的依赖关系\n\n"
            "你可以使用以下 MCP 工具来帮助你完成任务：\n"
            f"{self.tools}\n"
            "输出要求：\n"
            "请只输出 JSON 格式，包含 todos 数组，每个任务包含 id、content、status、priority、depends_on 字段。"
        )
        
        user_prompt = (
            "请分析以下 SKILL.md 文档，提取工作流程步骤并生成 TodoList：\n\n"
            "---------------- SKILL.md 开始 ----------------\n"
            f"{skill_doc}\n"  
            "---------------- SKILL.md 结束 ----------------\n\n"
            "请识别文档中描述的工作流程步骤，生成结构化的 TodoList。"
        )
        
        try:
            # 使用 LLM 提取工作流程
            from langchain.agents import create_agent
            
            extractor_agent = create_agent(
                model=self.llm,
                system_prompt=system_prompt,
                response_format=workflow_schema,
                tools=self.tools
            )
            
            result = extractor_agent.invoke({
                "messages": [
                    {"role": "user", "content": user_prompt}
                ]
            })
            
            # 解析返回结果
            todos_data = None
            
            if isinstance(result, dict):
                # 优先尝试从 structured_response 提取
                structured_response = result.get("structured_response", {})
                if structured_response and isinstance(structured_response, dict):
                    todos_data = structured_response.get("todos", [])
                    if todos_data and isinstance(todos_data, list):
                        return todos_data
                
                # 尝试从 output 字段提取
                output = result.get("output", "")
                if output and isinstance(output, str):
                    todos_data = self._parse_json_from_text(output)
                    if todos_data:
                        return todos_data
                
                # 尝试从 messages 中提取
                messages = result.get("messages", [])
                for msg in messages:
                    content = ""
                    if isinstance(msg, dict):
                        content = msg.get("content", "")
                    elif hasattr(msg, "content"):
                        content = str(msg.content)
                    
                    if content:
                        todos_data = self._parse_json_from_text(content)
                        if todos_data:
                            return todos_data
            elif isinstance(result, str):
                # 如果直接返回字符串，尝试解析
                todos_data = self._parse_json_from_text(result)
                if todos_data:
                    return todos_data
            
            # 如果所有解析都失败，使用 fallback
            return self._extract_workflow_fallback(skill_doc)
            
        except Exception as e:
            # 如果出错，使用 fallback 方法
            return self._extract_workflow_fallback(skill_doc)
    
    def _parse_json_from_text(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """
        从文本中解析 JSON 格式的 TodoList。
        支持多种格式：完整的 JSON 对象、JSON 代码块、内嵌 JSON 等。
        """
        import json
        import re
        
        if not text or "todos" not in text:
            return None
        
        # 尝试1：查找 JSON 代码块
        json_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        matches = re.findall(json_block_pattern, text, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                todos = data.get("todos", [])
                if todos and isinstance(todos, list):
                    return todos
            except:
                continue
        
        # 尝试2：查找最外层的大括号对
        brace_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(brace_pattern, text, re.DOTALL)
        for match in matches:
            if "todos" in match:
                try:
                    data = json.loads(match)
                    todos = data.get("todos", [])
                    if todos and isinstance(todos, list):
                        return todos
                except:
                    continue
        
        # 尝试3：直接查找第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                json_str = text[start:end+1]
                data = json.loads(json_str)
                todos = data.get("todos", [])
                if todos and isinstance(todos, list):
                    return todos
            except:
                pass
        
        return None
    
    def _extract_workflow_fallback(self, skill_doc: str) -> List[Dict[str, Any]]:
        """
        Fallback 方法：当 LLM 提取失败时使用简单的默认步骤。
        """
        return [
            {
                "id": "1",
                "content": "分析用户需求和输入材料，理解任务目标",
                "status": "pending",
                "priority": "must-have",
            },
            {
                "id": "2",
                "content": "按照 SKILL.md 中的工作流程执行任务",
                "status": "pending",
                "priority": "must-have",
                "depends_on": ["1"],
            },
            {
                "id": "3",
                "content": "生成最终输出并验证质量",
                "status": "pending",
                "priority": "must-have",
                "depends_on": ["2"],
            },
        ]

    # ------------------- 基于 SKILL.md 的 workflow 子 agent -------------------
    def _run_skill_workflow(
            self,
            skill: SkillMetadata,
            user_query: str,
            uploaded_file_path: Optional[str],
    ) -> str:
        """
        严格基于某个 skill 的 SKILL.md 描述来创建“workflow 型”子 agent，并接入 MCP 工具能力。

        实现思路：
        - 读取 skill.path 下的 SKILL.md 全文
        - 将其作为 system prompt，告诉子 agent：
          “你就是这个文档里描述的技能，请按其中的工作流程处理当前用户任务。”
        - 创建一个 tool-calling agent，注册所有 MCP 工具（read/write/edit/glob/grep/bash/todowrite/task/question/webfetch）
        - 将用户问题和（可选的）上传文件内容作为 human 输入
        - 子 agent 可以主动调用工具来执行 SKILL.md 中描述的流程步骤
        """
        skill_md_path = Path(skill.path) / "SKILL.md"
        try:
            skill_doc = skill_md_path.read_text(encoding="utf-8")
        except Exception as e:
            # 如果 SKILL.md 读取失败，回退使用 description
            fallback = (
                f"你是一个名为 {skill.name} 的专项 agent，技能描述如下：\n"
                f"{skill.description}\n\n"
                "请在你的技能范围内处理用户的请求。"
            )
            system_prompt = fallback + f"\n\n（额外信息：读取 SKILL.md 失败: {e}）"
            workflow_todos = []
        else:
            # 从 SKILL.md 中提取工作流程并生成 TodoList
            workflow_todos = self._extract_workflow_from_skill_md(skill_doc)
            
            # 使用 Review Planning Agent 审查 TodoList，识别缺失信息并添加询问任务
            if workflow_todos:
                # 读取上传文件内容（如果有）
                uploaded_content = None
                if uploaded_file_path:
                    path = Path(uploaded_file_path)
                    if path.is_file():
                        try:
                            uploaded_content = path.read_text(encoding="utf-8")
                        except Exception:
                            uploaded_content = None
                
                review_agent = ReviewPlanningAgent(llm=self.llm, tools=self.tools)
                workflow_todos = review_agent.review_plan(
                    todos=workflow_todos,
                    user_query=user_query,
                    skill_doc=skill_doc,
                    uploaded_content=uploaded_content
                )
            
            # 执行引擎设计和反思机制说明
            execution_guidelines = """
## 执行引擎设计（严格按照 TodoList 执行）

### 第一阶段：战术执行（按计划执行）

**执行引擎设计：**

1. **专注模式**：一次只处理一个Todo项，避免任务切换开销
   - 完成当前任务后再开始下一个
   - 不要跳过或并行执行多个任务（除非明确可以并行）
   - 保持对当前任务的专注

2. **上下文管理**：维护执行状态，记录中间结果和决策依据
   - 使用 `read`/`write`/`edit` 工具保存中间结果
   - 记录关键决策和发现的问题
   - 保持执行上下文的连贯性

3. **进度跟踪**：每完成一个任务，立即使用 `todowrite` 更新任务状态
   - 将已完成的任务标记为 `completed`
   - 将进行中的任务标记为 `in-progress`
   - 如果任务失败，标记为 `failed` 并记录原因
   - 保持用户和Agent的同步认知

**防偏离机制：**

1. **范围护栏**：每个步骤开始前检查是否偏离原始目标
   - 回顾任务目标和 SKILL.md 中的要求
   - 确认当前步骤与目标的相关性
   - 如果发现偏离，立即调整

2. **时间盒**：为每个任务设置最大时间限制，防止陷入细节
   - 如果某个任务耗时过长，考虑分解或调整策略
   - 避免在单个任务上花费过多时间
   - 保持整体进度的平衡

3. **完成标准**：明确定义每个任务的完成条件
   - 在开始任务前明确完成标准
   - 完成后验证是否达到标准
   - 只有达到标准才能标记为 `completed`

### 第二阶段：反思与调整

**动态调整机制：**

1. **检查点**：在关键节点（完成30%、50%、80%任务时）重新评估计划的有效性
   - 检查计划是否仍然有效
   - 识别是否需要调整剩余任务
   - 评估当前进度是否符合预期

2. **机会识别**：在执行过程中发现优化机会时调整计划
   - 如果发现更高效的方法，可以调整后续任务
   - 使用 `todowrite` 更新 TodoList
   - 但要保持与 SKILL.md 工作流程的一致性

3. **问题应对**：遇到阻碍时重新规划剩余任务
   - 如果任务失败，分析原因
   - 调整后续任务或创建替代方案
   - 记录问题和解决方案

**学习反馈：**

- 经验积累：记录成功和失败的模式
- 模式识别：识别重复出现的问题类型
- 策略优化：基于历史执行数据改进执行策略

### 第三阶段：Human-in-the-Loop机制（关键执行原则）

**当遇到以下情况时，必须使用 `question` 工具询问用户：**

1. **信息不完整**：执行当前任务需要某个具体信息，但用户未提供
   - 例如：需要具体的API端点URL、数据库连接参数、测试数据示例等
   - 不要自行假设或生成虚假信息
   - 使用 `question` 工具明确询问所需信息

2. **选择不确定**：有多个可行的执行方案，但不确定用户偏好
   - 例如：可以选择不同的测试框架、代码风格、文件格式等
   - 列出选项并询问用户偏好
   - 不要自行决定用户的偏好

3. **需求模糊**：用户需求描述不够具体，无法确定执行细节
   - 例如：用户说"优化代码"，但未说明优化目标（性能、可读性、内存等）
   - 询问具体的目标和约束条件
   - 确保理解用户的真实意图

4. **发现矛盾**：用户提供的信息与SKILL.md要求或常识矛盾
   - 例如：用户要求测试不存在的API端点
   - 指出矛盾并询问澄清
   - 不要继续执行矛盾的需求

**询问规则：**

1. **一次一问**：每个问题应该聚焦一个具体信息点
2. **提供上下文**：解释为什么需要这个信息，它与当前任务的关系
3. **明确格式**：如果需要特定格式的数据，说明要求
4. **保持礼貌**：使用专业、友好的语言询问

**执行流程：**

1. **识别缺失** → 2. **使用 `question` 工具询问** → 3. **等待用户回答** → 4. **整合信息继续执行**

**重要原则：**
- **禁止遐想**：绝对不要为缺失的信息生成假设性内容
- **严格验证**：如果用户提供的信息仍然不够，继续询问直到信息完整
- **记录对话**：使用 `write`/`edit` 工具记录用户提供的额外信息
- **保持透明**：让用户了解为什么需要这些信息，以及将如何使用

## 执行要求

1. **必须严格按照 TodoList 的顺序执行**，不要跳过或改变顺序
2. **每完成一个任务必须更新 TodoList 状态**，使用 `todowrite` 工具
3. **在关键节点进行反思**（完成30%、50%、80%任务时）
4. **保持与 SKILL.md 工作流程的一致性**，不要偏离原始流程
5. **遇到问题时先分析再调整**，不要盲目执行
"""
            
            # 构建 TodoList 的文本描述
            todo_list_text = "**从 SKILL.md 提取的工作流程 TodoList：**\n\n"
            for todo in workflow_todos:
                todo_list_text += f"- [{todo['id']}] {todo['content']} (状态: {todo['status']}, 优先级: {todo['priority']})\n"
            
            system_prompt = (
                f"你现在扮演技能 `{skill.name}` 对应的专项子 agent。\n"
                "下面是该技能的完整说明文档（包括你的角色定位、能力边界和完整工作流程）：\n"
                "---------------- SKILL.md 开始 ----------------\n"
                f"{skill_doc}\n"
                "---------------- SKILL.md 结束 ----------------\n\n"
                f"{todo_list_text}\n\n"
                f"{execution_guidelines}\n\n"
                "你可以使用以下 MCP 工具来帮助你完成任务：\n"
                f"{self.tools}\n"
                "**重要：你必须严格按照上述 TodoList 的顺序执行，每完成一个任务就更新状态。**\n\n"\
                "**关键 Human-in-the-Loop 原则：**\n"\
                "1. **遇到任何不确定、不完整或模糊的信息时，必须使用 `question` 工具询问用户**\n"\
                "2. **绝对不要为缺失的信息生成假设性内容或自行遐想**\n"\
                "3. **如果用户回答仍然不够清晰，继续询问直到信息完整**\n"\
                "4. **记录所有用户提供的额外信息，确保执行准确性**"
            )

        agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt,
        )

        user_input_parts = []

        # 附加用户上传的文件内容（如果有）
        if uploaded_file_path:
            path = Path(uploaded_file_path)
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    user_input_parts.append(
                        f"以下是用户提供的相关文档内容，请结合你的技能说明进行处理：\n\n{content[:16000]}"
                    )
                except Exception as e:
                    user_input_parts.append(
                        f"尝试读取用户上传的文件失败: {e}。如果该文件对任务很重要，请在回答中提示用户。"
                    )

        # 附上用户的自然语言请求，明确要求按照 TodoList 执行
        if workflow_todos:
            # 如果有提取到工作流程，要求 agent 先创建 TodoList，然后按顺序执行
            user_input_parts.append(
                f"当前需要你基于自己的技能说明文档来处理的用户请求是：\n{user_query}\n\n"
                "**执行要求：**\n"
                "1. 严格按照 TodoList 的顺序执行每个任务\n"
                "2. 每完成一个任务，立即使用 `todowrite` 更新任务状态为 `completed`\n"
                "3. 在关键节点（完成30%、50%、80%任务时）进行反思和调整\n"
                "4. 保持与 SKILL.md 工作流程的一致性，不要偏离原始流程\n"
                "5. **遇到任何不确定、不完整或模糊的信息时，必须使用 `question` 工具询问用户**\n"
                "6. **绝对不要为缺失的信息生成假设性内容或自行遐想**\n"
                "7. **如果用户回答仍然不够清晰，继续询问直到信息完整**"
            )
        else:
            user_input_parts.append(
                f"当前需要你基于自己的技能说明文档来处理的用户请求是：\n{user_query}"
            )

        user_input = "\n\n".join(user_input_parts)

        # 调用 tool-calling agent
        try:
            result = agent.invoke({
                "messages": [
                    {"role": "user", "content": user_input}
                ]
            })

            # 处理返回结果：提取完整的对话历史并记录到上下文
            has_output = False
            ctx = self.context

            if isinstance(result, dict):
                # 尝试提取最终输出
                output = result.get("output", "")
                if output:
                    has_output = True
                # 从 messages 中提取完整的对话历史
                messages = result.get("messages", [])

                if messages:
                    # 遍历所有消息，按类型记录到上下文
                    for msg in messages:
                        # 处理字典格式的消息
                        if isinstance(msg, dict):
                            msg_type = msg.get("type", "") or msg.get("__class__", "")
                            content = msg.get("content", "")

                            # HumanMessage - 用户消息
                            if "human" in str(msg_type).lower() or "HumanMessage" in str(msg_type):
                                if content:
                                    ctx.add_user_message(content, skill=skill.name)

                            # AIMessage - Assistant 回复
                            elif "assistant" in str(msg_type).lower() or "AIMessage" in str(msg_type):
                                if content:
                                    ctx.add_assistant_message(content, skill=skill.name)

                                # 注意：tool_calls 信息会在后续的 ToolMessage 中完整记录，
                                # 这里只记录 assistant 的文本回复，不重复记录工具调用

                            # ToolMessage - 工具执行结果
                            elif "tool" in str(msg_type).lower() or "ToolMessage" in str(msg_type):
                                tool_name = msg.get("name", "")
                                tool_content = msg.get("content", "")
                                tool_call_id = msg.get("tool_call_id", "")

                                if tool_name and tool_content:
                                    # 判断工具重要性（write/edit/bash 等操作类工具更重要）
                                    important = tool_name in ["write", "edit", "bash", "grep"]

                                    ctx.add_tool_result(
                                        name=tool_name,
                                        args={"tool_call_id": tool_call_id} if tool_call_id else {},
                                        result=tool_content,
                                        important=important,
                                    )

                                # 如果是 todowrite 工具，同步更新 context 的 todos
                                if tool_name == "todowrite" and tool_content:
                                    try:
                                        # 尝试从 tool_content 中解析 todo 列表
                                        # tool_content 格式通常是 JSON 字符串或包含 JSON 的文本
                                        import json
                                        # 尝试提取 JSON 部分
                                        if "{" in tool_content and "}" in tool_content:
                                            start = tool_content.find("{")
                                            end = tool_content.rfind("}") + 1
                                            json_str = tool_content[start:end]
                                            try:
                                                todos_data = json.loads(json_str)
                                                if isinstance(todos_data, dict):
                                                    ctx.update_todos_from_tool(list(todos_data.values()))
                                            except:
                                                pass
                                    except:
                                        pass

                        # 处理 langchain Message 对象
                        else:
                            # 检查是否是 langchain 的 Message 对象

                            # HumanMessage
                            if type(msg) == HumanMessage:
                                if hasattr(msg, "content"):
                                    ctx.add_user_message(str(msg.content), skill=skill.name)

                            # AIMessage
                            elif type(msg) == AIMessage:
                                if hasattr(msg, "content"):
                                    content = str(msg.content)
                                    ctx.add_assistant_message(content, skill=skill.name)

                                # 注意：tool_calls 信息会在后续的 ToolMessage 中完整记录

                            # ToolMessage
                            elif type(msg) == ToolMessage:
                                tool_name = getattr(msg, "name", "") or ""
                                tool_content = getattr(msg, "content", "") or ""

                                if tool_name and tool_content:
                                    important = tool_name in ["write", "edit", "bash", "grep"]
                                    ctx.add_tool_result(
                                        name=tool_name,
                                        args={},
                                        result=str(tool_content),
                                        important=important,
                                    )

                                    # 处理 todowrite 工具
                                    if tool_name == "todowrite":
                                        try:
                                            import json
                                            content_str = str(tool_content)
                                            if "{" in content_str and "}" in content_str:
                                                start = content_str.find("{")
                                                end = content_str.rfind("}") + 1
                                                json_str = content_str[start:end]
                                                todos_data = json.loads(json_str)
                                                if isinstance(todos_data, dict):
                                                    ctx.update_todos_from_tool(list(todos_data.values()))
                                        except:
                                            pass

                            # 提取最终输出（最后一条 AIMessage 的 content）
                            if type(msg) == AIMessage and hasattr(msg, "content"):
                                if not has_output:
                                    output = str(msg.content)

                # 如果没有从 messages 中提取到输出，尝试其他方式
                if not output:
                    output = result.get("output", "")
                    if not output:
                        # 尝试从最后一条消息中提取
                        if messages:
                            last_msg = messages[-1]
                            if isinstance(last_msg, dict):
                                output = last_msg.get("content", "")
                            elif hasattr(last_msg, "content"):
                                output = str(last_msg.content)

                if not output:
                    output = str(result)
            else:
                output = str(result)

            return output
        except Exception as e:
            # 如果 tool-calling agent 调用失败，回退到普通对话模式
            fallback_msg = (
                f"Tool-calling agent 执行失败: {e}。"
                "以下是基于技能说明的初步回复："
            )
            messages: List[Any] = [SystemMessage(content=system_prompt), HumanMessage(content=user_input)]
            resp = self.llm.invoke(messages)
            return f"{fallback_msg}\n\n{resp.content}"  # type: ignore[no-any-return]

    # ------------------- 工具方法 -------------------
    def _find_skill_by_name(self, name: str) -> Optional[SkillMetadata]:
        for s in self.skills:
            if s.name == name:
                return s
        return None
