from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any


BAILIAN_BASE_URL = "https://ws-sfjve45f4q20om2f.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
BAILIAN_MODEL = "qwen3.7-plus"


class LLMClient(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
    ) -> str:
        """Return a JSON decision string for the agent."""


class FakeLLM(LLMClient):
    def __init__(self, responses: list[str | dict[str, Any]]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        messages: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
    ) -> str:
        self.calls.append(
            {
                "messages": messages,
                "tool_schemas": tool_schemas,
            }
        )

        if not self._responses:
            raise RuntimeError("FakeLLM has no more responses.")

        response = self._responses.pop(0)
        if isinstance(response, str):
            return response

        return json.dumps(response, ensure_ascii=False)


class AliyunBailianLLM(LLMClient):
    def __init__(
        self,
        api_key: str,
        client: Any | None = None,
        base_url: str = BAILIAN_BASE_URL,
        model: str = BAILIAN_MODEL,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required for AliyunBailianLLM.")

        self.model = model
        self.base_url = base_url
        self.client = client if client is not None else self._create_client(api_key, base_url)

    def complete(
        self,
        messages: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
    ) -> str:
        request_messages = self._build_messages(messages, tool_schemas)

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=request_messages,
                extra_body={"enable_thinking": True},
                stream=True,
            )
            content = self._collect_stream_content(completion)
        except Exception as exc:
            raise RuntimeError(f"Aliyun Bailian API request failed: {exc}") from exc

        if not content.strip():
            raise RuntimeError("Aliyun Bailian API returned empty content.")

        try:
            parse_llm_response(content)
        except ValueError as exc:
            raise RuntimeError(f"Aliyun Bailian API returned invalid JSON: {exc}") from exc

        return content

    def _create_client(self, api_key: str, base_url: str) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is required to use AliyunBailianLLM.") from exc

        return OpenAI(api_key=api_key, base_url=base_url)

    def _build_messages(
        self,
        messages: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        system_prompt = self._build_system_prompt(tool_schemas)
        normalized_messages = [self._normalize_message(message) for message in messages]
        return [{"role": "system", "content": system_prompt}, *normalized_messages]

    def _build_system_prompt(self, tool_schemas: list[dict[str, Any]]) -> str:
        tool_schema_text = json.dumps(tool_schemas, ensure_ascii=False, indent=2)
        return (
            "你是一个本地 Agent 的决策模型。你必须只输出严格 JSON，不能输出 Markdown，"
            "不能输出额外解释。\n"
            "你只能输出两种 JSON：\n"
            '{"action":"tool","tool_name":"calculator","arguments":{"expression":"1 + 2"}}\n'
            '{"action":"final","answer":"计算结果是 3。"}\n'
            "如果需要调用工具，请根据工具 schema 选择 tool action。"
            "如果已经得到足够信息，请输出 final action。\n"
            f"可用工具 schema：\n{tool_schema_text}"
        )

    def _normalize_message(self, message: dict[str, Any]) -> dict[str, str]:
        role = message.get("role")
        content = message.get("content", "")

        if role == "system":
            return {"role": "system", "content": str(content)}
        if role == "assistant":
            return {"role": "assistant", "content": str(content)}
        if role == "tool":
            tool_name = message.get("tool_name", "unknown")
            return {
                "role": "user",
                "content": f"最近一次工具调用结果：{tool_name} -> {json.dumps(content, ensure_ascii=False)}",
            }

        return {"role": "user", "content": str(content)}

    def _collect_stream_content(self, completion: Any) -> str:
        parts: list[str] = []
        for chunk in completion:
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue

            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None)
            if content:
                parts.append(content)

        return "".join(parts)


def parse_llm_response(response: str) -> dict[str, Any]:
    try:
        decision = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON response: {exc.msg}") from exc

    if not isinstance(decision, dict):
        raise ValueError("LLM response must be a JSON object.")

    action = decision.get("action")
    if action == "tool":
        return _parse_tool_decision(decision)
    if action == "final":
        return _parse_final_decision(decision)

    raise ValueError("LLM response action must be 'tool' or 'final'.")


def _parse_tool_decision(decision: dict[str, Any]) -> dict[str, Any]:
    tool_name = decision.get("tool_name")
    arguments = decision.get("arguments")

    if not isinstance(tool_name, str) or not tool_name.strip():
        raise ValueError("Tool decision requires a non-empty tool_name.")
    if not isinstance(arguments, dict):
        raise ValueError("Tool decision requires arguments to be an object.")

    return {
        "action": "tool",
        "tool_name": tool_name,
        "arguments": arguments,
    }


def _parse_final_decision(decision: dict[str, Any]) -> dict[str, Any]:
    answer = decision.get("answer")

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Final decision requires a non-empty answer.")

    return {
        "action": "final",
        "answer": answer,
    }
