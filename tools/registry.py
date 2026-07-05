from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class BaseTool(ABC):
    name: str
    description: str
    parameters: dict[str, Any]

    @abstractmethod
    def run(self, arguments: dict[str, Any]) -> ToolResult:
        """Run the tool with parsed arguments."""


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._validate_tool(tool)

        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")

        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool '{name}' is not registered.") from exc

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    def _validate_tool(self, tool: BaseTool) -> None:
        if not isinstance(tool, BaseTool):
            raise TypeError("Registered tool must inherit from BaseTool.")
        if not isinstance(tool.name, str) or not tool.name:
            raise ValueError("Tool name must be a non-empty string.")
        if not isinstance(tool.description, str) or not tool.description:
            raise ValueError("Tool description must be a non-empty string.")
        if not isinstance(tool.parameters, dict):
            raise ValueError("Tool parameters must be a JSON Schema dictionary.")
