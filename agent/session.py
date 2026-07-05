from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    user_id: str
    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    todos: list[dict[str, Any]] = field(default_factory=list)
    tool_traces: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    max_messages: int = 20

    def add_message(self, message: dict[str, Any]) -> None:
        self.messages.append(message)
        self.compress_messages()

    def compress_messages(self) -> None:
        if self.max_messages < 1:
            raise ValueError("max_messages must be at least 1.")
        if len(self.messages) <= self.max_messages:
            return

        older_messages = self.messages[:-self.max_messages]
        self.messages = self.messages[-self.max_messages :]
        new_summary = self._summarize_messages(older_messages)
        if not new_summary:
            return

        if self.summary:
            self.summary = f"{self.summary}\n{new_summary}"
        else:
            self.summary = new_summary

    def _summarize_messages(self, messages: list[dict[str, Any]]) -> str:
        summary_lines = []
        for message in messages:
            role = message.get("role")
            if role == "user":
                summary_lines.append(f"用户请求：{message.get('content', '')}")
            elif role == "tool":
                summary_lines.append(self._summarize_tool_message(message))

        return "\n".join(line for line in summary_lines if line)

    def _summarize_tool_message(self, message: dict[str, Any]) -> str:
        tool_name = message.get("tool_name", "unknown")
        content = message.get("content", {})
        if not isinstance(content, dict):
            return f"工具结果：{tool_name} -> {content}"

        if content.get("success"):
            return f"工具结果：{tool_name} -> {content.get('data', {})}"

        return f"工具错误：{tool_name} -> {content.get('error')}"
