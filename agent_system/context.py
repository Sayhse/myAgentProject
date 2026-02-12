from __future__ import annotations

"""
会话与上下文管理模块：

实现你描述的上下文管理机制，包括：
- 对话历史管理（短期记忆）
- 工具状态与结果记录
- todo / 任务进度
- 简单的“智能上下文窗口”与内容裁剪（按优先级与长度截断）
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import os
import platform


Role = Literal["user", "assistant", "tool"]


@dataclass
class ConversationTurn:
    role: Role
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallRecord:
    name: str
    args: Dict[str, Any]
    result_preview: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    important: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    """
    会话状态与记忆层级：
    - 短期记忆：conversation_history
    - 工具状态记忆：tool_calls
    - 会话状态：todo、用户偏好等
    """

    # 对话历史（短期记忆）
    conversation_history: List[ConversationTurn] = field(default_factory=list)

    # 工具调用记录（含 bash、grep、edit 等）
    tool_calls: List[ToolCallRecord] = field(default_factory=list)

    # todo 列表 / 任务进度（结构与 todowrite 工具保持一致）
    todos: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 用户偏好与会话级配置
    user_preferences: Dict[str, Any] = field(default_factory=dict)

    # 环境信息（状态保持机制）
    env: Dict[str, Any] = field(default_factory=dict)

    # 为错误诊断保留的关键上下文（结构化压缩）
    important_snippets: List[str] = field(default_factory=list)


class ConversationContext:
    """
    面向多 agent 系统的统一上下文管理器。

    特性：
    - 完整对话记录 & 工具结果整合
    - 简单的智能上下文裁剪（按长度与优先级）
    - 记录环境变量、平台信息、工作目录等
    - 支持导出给 LLM 的历史片段（messages 形式）
    """

    def __init__(
        self,
        max_chars: int = 80_000,
        keep_recent_turns: int = 20,
    ) -> None:
        """
        max_chars: 上下文输出的目标最大字符数（粗略代替 token），适配大模型上下文上限。
        keep_recent_turns: 至少保留的最近对话轮数。
        """
        self.state = SessionState()
        self.max_chars = max_chars
        self.keep_recent_turns = keep_recent_turns
        self._init_env()

    # ---------- 环境 & 会话状态 ----------
    def _init_env(self) -> None:
        self.state.env.update(
            {
                "cwd": str(Path.cwd()),
                "platform": platform.platform(),
                "os": os.name,
                "date": datetime.now().isoformat(),
            }
        )

    # ---------- 对话记录 ----------
    def add_user_message(self, content: str, **metadata: Any) -> None:
        self.state.conversation_history.append(
            ConversationTurn(role="user", content=content, metadata=metadata)
        )

    def add_assistant_message(self, content: str, **metadata: Any) -> None:
        self.state.conversation_history.append(
            ConversationTurn(role="assistant", content=content, metadata=metadata)
        )

    def add_tool_result(
        self,
        name: str,
        args: Dict[str, Any],
        result: str,
        important: bool = False,
        **metadata: Any,
    ) -> None:
        """
        记录一次工具调用的结果。
        为了控制上下文长度，只保存 result 的前若干字符。
        """
        preview = result[:4000]
        self.state.tool_calls.append(
            ToolCallRecord(
                name=name,
                args=args,
                result_preview=preview,
                important=important,
                metadata=metadata,
            )
        )
        if important:
            # 将关键错误信息/路径等放入 important_snippets，支持错误恢复与诊断
            snippet = metadata.get("snippet") or preview
            self.state.important_snippets.append(snippet)

    # ---------- todo / 任务状态 ----------
    def update_todos_from_tool(self, items: List[Dict[str, Any]]) -> None:
        """
        与 todowrite 工具的结构对齐：
        items: [{id, content, status, ...}]
        """
        for item in items:
            todo_id = str(item.get("id"))
            if not todo_id:
                continue
            current = self.state.todos.get(todo_id, {})
            current.update(item)
            self.state.todos[todo_id] = current

    # ---------- 用户偏好 ----------
    def set_user_preference(self, key: str, value: Any) -> None:
        self.state.user_preferences[key] = value

    def get_user_preference(self, key: str, default: Any = None) -> Any:
        return self.state.user_preferences.get(key, default)

    # ---------- 导出给 LLM 的历史 ----------
    def build_history_for_llm(self) -> List[Dict[str, str]]:
        """
        将内部的 conversation_history + 重要的工具输出，整理为适合传给 LLM 的 messages 片段。

        策略（贴合你的上下文管理描述）：
        - 优先保留最近 N 轮对话（keep_recent_turns）
        - 追加重要的工具输出摘要和错误片段（important_snippets）
        - 粗略控制整体字符数不超过 max_chars
        """
        turns = self.state.conversation_history[-self.keep_recent_turns :]

        messages: List[Dict[str, str]] = []
        buf_len = 0

        # 1. 最近的对话内容（高优先级）
        for t in turns:
            msg = {"role": t.role, "content": t.content}
            buf_len += len(t.content)
            messages.append(msg)

        # 2. 追加一些重要错误片段 / 工具结果（结构化压缩的一种简单形式）
        for snippet in self.state.important_snippets[-10:]:
            text = f"[important-context]\n{snippet}"
            if buf_len + len(text) > self.max_chars:
                break
            messages.append({"role": "tool", "content": text})
            buf_len += len(text)

        return messages

    # ---------- 调试/查看 ----------
    def summary(self) -> Dict[str, Any]:
        return {
            "turns": len(self.state.conversation_history),
            "tool_calls": len(self.state.tool_calls),
            "todos": list(self.state.todos.values()),
            "env": self.state.env,
        }


