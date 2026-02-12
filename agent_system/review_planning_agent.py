from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage


@dataclass
class MissingInfoQuestion:
    """表示缺失信息的问题"""
    question_id: str
    question_text: str
    related_todo_id: str
    required_for: str  # 描述为什么需要这个信息


class ReviewPlanningAgent:
    """
    Review Planning Agent 负责审查从 SKILL.md 提取的 TodoList，
    识别缺失的用户信息，并在 TodoList 开头添加询问任务。
    
    工作流程：
    1. 分析 TodoList 中的每个任务
    2. 识别执行任务所需但用户未提供的信息
    3. 生成具体的问题列表
    4. 在 TodoList 开头添加"询问用户"任务
    5. 返回更新后的 TodoList
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[Any],
    ) -> None:
        self.llm = llm
        self.tools = tools
    
    def review_plan(
        self,
        todos: List[Dict[str, Any]],
        user_query: str,
        skill_doc: str,
        uploaded_content: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        审查 TodoList，识别缺失信息，并添加询问任务。
        
        参数:
            todos: 从 SKILL.md 提取的原始 TodoList
            user_query: 用户的原始查询
            skill_doc: SKILL.md 的完整内容
            uploaded_content: 用户上传的文件内容（如果有）
            
        返回:
            更新后的 TodoList，包含询问任务（如果需要）
        """
        if not todos:
            return todos
        
        # 1. 识别缺失信息
        missing_info = self._identify_missing_info(
            todos=todos,
            user_query=user_query,
            skill_doc=skill_doc,
            uploaded_content=uploaded_content
        )
        
        # 如果没有缺失信息，直接返回原 TodoList
        if not missing_info:
            return todos
        
        # 2. 生成询问任务
        question_todos = self._create_question_todos(missing_info)
        
        # 3. 创建问题ID到询问任务ID的映射
        question_id_to_ask_todo_id = {}
        for q_todo in question_todos:
            todo_id = q_todo["id"]
            if todo_id.startswith("ask_"):
                original_qid = todo_id[4:]  # 去掉 "ask_" 前缀
                question_id_to_ask_todo_id[original_qid] = todo_id
        
        # 4. 更新原始任务的依赖关系
        updated_todos = []
        
        # 首先添加所有询问任务
        updated_todos.extend(question_todos)
        
        # 然后添加原始任务，更新其依赖关系
        for todo in todos:
            # 查找所有关联到这个任务的问题
            dependencies = []
            for info in missing_info:
                if info.related_todo_id == todo.get("id", ""):
                    ask_todo_id = question_id_to_ask_todo_id.get(info.question_id)
                    if ask_todo_id:
                        dependencies.append(ask_todo_id)
            
            # 如果找到依赖，更新任务的 depends_on 字段
            if dependencies:
                # 确保 depends_on 字段存在
                if "depends_on" not in todo:
                    todo["depends_on"] = []
                # 添加依赖（去重）
                existing_deps = set(todo["depends_on"])
                for dep in dependencies:
                    existing_deps.add(dep)
                todo["depends_on"] = list(existing_deps)
            
            updated_todos.append(todo)
        
        return updated_todos
    
    def _identify_missing_info(
        self,
        todos: List[Dict[str, Any]],
        user_query: str,
        skill_doc: str,
        uploaded_content: Optional[str] = None,
    ) -> List[MissingInfoQuestion]:
        """
        使用 LLM 识别缺失信息。
        
        策略：
        1. 分析 SKILL.md 中的"输入要求"部分
        2. 检查用户查询是否提及必要信息
        3. 检查上传文件是否包含所需数据
        4. 针对每个 Todo 任务，判断执行所需的上下文信息
        """
        # 构建提示词让 LLM 分析缺失信息
        system_prompt = (
            "你是一个计划审查专家，负责识别任务执行所需但用户未提供的必要信息。\n\n"
            "你的任务：\n"
            "1. 分析 SKILL.md 文档，了解该技能需要哪些输入信息\n"
            "2. 检查用户查询和上传的文件内容\n"
            "3. 针对 TodoList 中的每个任务，判断执行该任务需要哪些具体信息\n"
            "4. 识别哪些必要信息是用户尚未提供的\n"
            "5. 为每个缺失信息生成一个清晰、具体的问题\n\n"
            "输出要求：\n"
            "请输出 JSON 格式，包含一个 questions 数组，每个问题包含以下字段：\n"
            "- question_id: 唯一标识符（如 'q1', 'q2'）\n"
            "- question_text: 具体的问题文本\n"
            "- related_todo_id: 关联的 Todo 任务 ID\n"
            "- required_for: 描述为什么需要这个信息（例如：'用于生成测试用例的输入参数'）\n"
            "如果没有任何缺失信息，输出空数组。"
        )
        
        # 构建用户提示词
        user_prompt_parts = [f"## SKILL.md 内容\n```\n{skill_doc}\n```", f"## 用户查询\n{user_query}"]

        # 添加上传文件内容（如果有）
        if uploaded_content:
            user_prompt_parts.append(f"## 上传文件内容\n```\n{uploaded_content}\n```")
        else:
            user_prompt_parts.append("## 上传文件内容\n无上传文件")
        
        # 添加 TodoList
        todo_list_text = "## TodoList\n"
        for todo in todos:
            todo_list_text += f"- [{todo.get('id', '?')}] {todo.get('content', '')} (优先级: {todo.get('priority', 'N/A')})\n"
        user_prompt_parts.append(todo_list_text)
        
        user_prompt_parts.append("请分析上述信息，识别缺失的必要信息，并生成问题列表。")
        user_prompt = "\n\n".join(user_prompt_parts)
        
        # 定义返回的 JSON Schema
        missing_info_schema = {
            "type": "object",
            "description": "缺失信息问题列表",
            "properties": {
                "questions": {
                    "type": "array",
                    "description": "缺失信息问题列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question_id": {
                                "type": "string",
                                "description": "问题唯一标识符"
                            },
                            "question_text": {
                                "type": "string",
                                "description": "具体的问题文本"
                            },
                            "related_todo_id": {
                                "type": "string",
                                "description": "关联的 Todo 任务 ID"
                            },
                            "required_for": {
                                "type": "string",
                                "description": "描述为什么需要这个信息"
                            }
                        },
                        "required": ["question_id", "question_text", "related_todo_id", "required_for"]
                    }
                }
            },
            "required": ["questions"]
        }
        
        try:
            # 创建 agent 进行缺失信息分析
            reviewer_agent = create_agent(
                model=self.llm,
                system_prompt=system_prompt,
                response_format=missing_info_schema,
                tools=self.tools
            )
            
            result = reviewer_agent.invoke({
                "messages": [
                    {"role": "user", "content": user_prompt}
                ]
            })
            
            # 解析返回结果
            questions_data = []
            
            if isinstance(result, dict):
                # 尝试从 structured_response 提取
                structured_response = result.get("structured_response", {})
                if structured_response and isinstance(structured_response, dict):
                    questions_data = structured_response.get("questions", [])
                
                # 如果 structured_response 中没有，尝试从 output 字段提取
                if not questions_data:
                    output = result.get("output", "")
                    if output and isinstance(output, str):
                        questions_data = self._parse_json_from_text(output, "questions")
                
                # 如果 output 中没有，尝试从 messages 中提取
                if not questions_data:
                    messages = result.get("messages", [])
                    for msg in messages:
                        content = ""
                        if isinstance(msg, dict):
                            content = msg.get("content", "")
                        elif hasattr(msg, "content"):
                            content = str(msg.content)
                        
                        if content:
                            questions_data = self._parse_json_from_text(content, "questions")
                            if questions_data:
                                break
            
            # 转换为 MissingInfoQuestion 对象列表
            missing_info_list = []
            for q_data in questions_data:
                if isinstance(q_data, dict):
                    try:
                        missing_info_list.append(MissingInfoQuestion(
                            question_id=q_data.get("question_id", ""),
                            question_text=q_data.get("question_text", ""),
                            related_todo_id=q_data.get("related_todo_id", ""),
                            required_for=q_data.get("required_for", "")
                        ))
                    except Exception:
                        continue
            
            return missing_info_list
            
        except Exception as e:
            # 如果分析失败，返回空列表（不添加询问任务）
            print(f"[ReviewPlanningAgent] 缺失信息分析失败: {e}")
            return []
    
    def _create_question_todos(self, missing_info: List[MissingInfoQuestion]) -> List[Dict[str, Any]]:
        """根据缺失信息创建询问任务"""
        question_todos = []
        
        for i, info in enumerate(missing_info):
            # 为每个缺失信息创建一个询问任务
            todo_id = f"ask_{info.question_id}"
            
            # 构建任务描述
            task_description = (
                f"询问用户以下信息（需要用于任务 {info.related_todo_id}）：\n"
                f"问题：{info.question_text}\n"
                f"用途：{info.required_for}\n"
                f"要求：使用 question 工具向用户提问，并记录用户的回答。"
            )
            
            question_todo = {
                "id": todo_id,
                "content": task_description,
                "status": "pending",
                "priority": "must-have",  # 询问任务是必须的
                "depends_on": []  # 询问任务不依赖其他任务
            }
            
            question_todos.append(question_todo)
        
        return question_todos
    
    def _update_dependencies(
        self,
        todos: List[Dict[str, Any]],
        question_todos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        更新原始任务的依赖关系，使其依赖相关的询问任务。
        
        例如：如果任务 "t2" 需要信息 "q1"，则添加 "ask_q1" 到 t2 的 depends_on 中。
        """
        if not question_todos:
            return todos
        
        # 创建问题ID到任务ID的映射
        question_id_to_todo_id = {}
        for q_todo in question_todos:
            # q_todo["id"] 格式为 "ask_q1"，其中的 "q1" 是原始 question_id
            todo_id = q_todo["id"]
            # 提取原始 question_id（去掉 "ask_" 前缀）
            if todo_id.startswith("ask_"):
                original_qid = todo_id[4:]
                question_id_to_todo_id[original_qid] = todo_id
        
        # 更新原始任务的依赖
        updated_todos = []
        for todo in todos:
            # 跳过询问任务本身
            if todo.get("id", "").startswith("ask_"):
                updated_todos.append(todo)
                continue
            
            # 检查这个任务是否与任何问题关联
            todo_id = todo.get("id", "")
            # 查找所有关联到这个任务的问题
            related_question_todo_ids = []
            for original_qid, ask_todo_id in question_id_to_todo_id.items():
                # 注意：我们无法直接知道哪个问题关联到哪个任务
                # 这个信息应该在 MissingInfoQuestion 中，但我们需要在方法外部传递
                # 由于我们在这个方法中没有 missing_info 列表，我们暂时跳过依赖更新
                # 在实际执行中，LLM 生成的 question 已经包含了 related_todo_id
                # 我们可以考虑在 _create_question_todos 中直接更新原始任务的 depends_on
                pass
            
            # 暂时不自动添加依赖，保持简单实现
            # 询问任务已经在 TodoList 开头，会自然先执行
            updated_todos.append(todo)
        
        return updated_todos
    
    def _parse_json_from_text(self, text: str, array_key: str) -> List[Dict[str, Any]]:
        """从文本中解析 JSON 数组"""
        import re
        
        if not text:
            return []
        
        try:
            # 尝试直接解析整个文本为 JSON
            data = json.loads(text)
            if isinstance(data, dict) and array_key in data:
                array_data = data[array_key]
                if isinstance(array_data, list):
                    return array_data
            
            # 如果整个文本不是 JSON，尝试查找 JSON 代码块
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            matches = re.findall(json_pattern, text, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and array_key in data:
                        array_data = data[array_key]
                        if isinstance(array_data, list):
                            return array_data
                except:
                    continue
            
            # 尝试查找内嵌的 JSON 对象
            brace_start = text.find('{')
            brace_end = text.rfind('}')
            if brace_start >= 0 and brace_end > brace_start:
                json_str = text[brace_start:brace_end+1]
                try:
                    data = json.loads(json_str)
                    if isinstance(data, dict) and array_key in data:
                        array_data = data[array_key]
                        if isinstance(array_data, list):
                            return array_data
                except:
                    pass
        except Exception:
            pass
        
        return []