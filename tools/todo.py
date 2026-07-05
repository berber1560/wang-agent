from __future__ import annotations

from typing import Any

from agent.session import SessionState
from tools.registry import BaseTool, ToolResult


class TodoTool(BaseTool):
    name = "todo"
    description = "Manage todos stored in the current session state."
    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["create", "list", "complete", "delete"],
                "description": "Todo operation to run.",
            },
            "title": {
                "type": "string",
                "description": "Todo title for create.",
            },
            "id": {
                "type": "integer",
                "description": "Todo id for complete or delete.",
            },
        },
        "required": ["operation"],
    }

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        session = arguments.get("session")
        if not isinstance(session, SessionState):
            return ToolResult(success=False, error="SessionState is required.")

        operation = arguments.get("operation")
        if operation == "create":
            return self._create(session, arguments)
        if operation == "list":
            return self._list(session)
        if operation == "complete":
            return self._complete(session, arguments)
        if operation == "delete":
            return self._delete(session, arguments)

        return ToolResult(success=False, error="Unsupported todo operation.")

    def _create(self, session: SessionState, arguments: dict[str, Any]) -> ToolResult:
        title = arguments.get("title")
        if not isinstance(title, str) or not title.strip():
            return ToolResult(success=False, error="Todo title must be a non-empty string.")

        todo = {
            "id": self._next_id(session),
            "title": title.strip(),
            "completed": False,
        }
        session.todos.append(todo)
        return ToolResult(success=True, data={"todo": dict(todo)})

    def _list(self, session: SessionState) -> ToolResult:
        return ToolResult(success=True, data={"todos": [dict(todo) for todo in session.todos]})

    def _complete(self, session: SessionState, arguments: dict[str, Any]) -> ToolResult:
        todo_id = self._parse_id(arguments.get("id"))
        if todo_id is None:
            return ToolResult(success=False, error="Todo id must be an integer.")

        todo = self._find(session, todo_id)
        if todo is None:
            return ToolResult(success=False, error=f"Todo '{todo_id}' was not found.")

        todo["completed"] = True
        return ToolResult(success=True, data={"todo": dict(todo)})

    def _delete(self, session: SessionState, arguments: dict[str, Any]) -> ToolResult:
        todo_id = self._parse_id(arguments.get("id"))
        if todo_id is None:
            return ToolResult(success=False, error="Todo id must be an integer.")

        for index, todo in enumerate(session.todos):
            if todo["id"] == todo_id:
                removed = session.todos.pop(index)
                return ToolResult(success=True, data={"todo": dict(removed)})

        return ToolResult(success=False, error=f"Todo '{todo_id}' was not found.")

    def _next_id(self, session: SessionState) -> int:
        if not session.todos:
            return 1

        return max(todo["id"] for todo in session.todos) + 1

    def _find(self, session: SessionState, todo_id: int) -> dict[str, Any] | None:
        for todo in session.todos:
            if todo["id"] == todo_id:
                return todo

        return None

    def _parse_id(self, value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)

        return None
