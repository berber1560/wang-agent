from __future__ import annotations

import copy
from typing import Any

from agent.llm_client import LLMClient, parse_llm_response
from agent.session import SessionState
from tools.registry import ToolRegistry, ToolResult


class AgentRuntime:
    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        max_steps: int = 5,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")

        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self._sessions: dict[tuple[str, str], SessionState] = {}

    def get_session(self, user_id: str, session_id: str) -> SessionState:
        key = (user_id, session_id)
        if key not in self._sessions:
            self._sessions[key] = SessionState(user_id=user_id, session_id=session_id)

        return self._sessions[key]

    def run(self, user_id: str, session_id: str, user_message: str) -> str:
        session = self.get_session(user_id, session_id)
        session.add_message({"role": "user", "content": user_message})

        for _ in range(self.max_steps):
            response = self.llm_client.complete(
                messages=self._build_llm_messages(session),
                tool_schemas=self.tool_registry.get_tool_schemas(),
            )
            decision = parse_llm_response(response)

            if decision["action"] == "final":
                answer = decision["answer"]
                session.add_message({"role": "assistant", "content": answer})
                return answer

            tool_result = self._run_tool_decision(session, decision)
            self._record_tool_result(session, decision, tool_result)

        raise RuntimeError("AgentRuntime exceeded max loop steps.")

    def _build_llm_messages(self, session: SessionState) -> list[dict[str, Any]]:
        messages = copy.deepcopy(session.messages)
        if not session.summary:
            return messages

        return [
            {
                "role": "system",
                "content": f"Session summary:\n{session.summary}",
            },
            *messages,
        ]

    def _run_tool_decision(self, session: SessionState, decision: dict[str, Any]) -> ToolResult:
        tool_name = decision["tool_name"]
        arguments = dict(decision["arguments"])
        tool_arguments = dict(arguments)
        tool_arguments["session"] = session

        try:
            tool = self.tool_registry.get(tool_name)
            result = tool.run(tool_arguments)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

        if not isinstance(result, ToolResult):
            return ToolResult(success=False, error=f"Tool '{tool_name}' did not return ToolResult.")

        return result

    def _record_tool_result(
        self,
        session: SessionState,
        decision: dict[str, Any],
        result: ToolResult,
    ) -> None:
        tool_name = decision["tool_name"]
        arguments = dict(decision["arguments"])
        result_payload = {
            "success": result.success,
            "data": result.data,
            "error": result.error,
        }

        session.tool_traces.append(
            {
                "tool_name": tool_name,
                "arguments": arguments,
                **result_payload,
            }
        )
        session.add_message(
            {
                "role": "tool",
                "tool_name": tool_name,
                "content": result_payload,
            }
        )
