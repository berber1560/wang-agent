from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from agent.llm_client import AliyunBailianLLM, LLMClient
from agent.runtime import AgentRuntime
from tools.calculator import CalculatorTool
from tools.registry import ToolRegistry
from tools.search import MockSearchTool, WebSearchTool
from tools.todo import TodoTool


DEFAULT_USER_ID = "local_user"
DEFAULT_SESSION_ID = "default"
DEFAULT_LLM_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "local_llm.json"


class RuleBasedLLM(LLMClient):
    """Small demo-only LLM replacement for the stage 8 CLI."""

    def complete(
        self,
        messages: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
    ) -> str:
        last_message = messages[-1]
        if last_message["role"] == "tool":
            return self._final_from_tool(last_message)

        user_text = str(last_message["content"]).strip()
        decision = self._decide_from_user_text(user_text)
        return json.dumps(decision, ensure_ascii=False)

    def _decide_from_user_text(self, user_text: str) -> dict[str, Any]:
        if self._looks_like_search(user_text):
            return {
                "action": "tool",
                "tool_name": "web_search",
                "arguments": {"query": self._extract_search_query(user_text)},
            }

        if self._looks_like_todo(user_text):
            return self._todo_decision(user_text)

        expression = self._extract_expression(user_text)
        if expression is not None:
            return {
                "action": "tool",
                "tool_name": "calculator",
                "arguments": {"expression": expression},
            }

        return {"action": "final", "answer": f"收到：{user_text}"}

    def _final_from_tool(self, message: dict[str, Any]) -> str:
        tool_name = message["tool_name"]
        content = message["content"]

        if not content["success"]:
            answer = f"工具 {tool_name} 执行失败：{content['error']}"
            return json.dumps({"action": "final", "answer": answer}, ensure_ascii=False)

        data = content["data"]
        if tool_name == "calculator":
            answer = f"计算结果是 {data['result']}。"
        elif tool_name in {"mock_search", "web_search"}:
            answer = self._format_search_answer(data)
        elif tool_name == "todo":
            answer = self._format_todo_answer(data)
        else:
            answer = f"工具 {tool_name} 已执行完成。"

        return json.dumps({"action": "final", "answer": answer}, ensure_ascii=False)

    def _looks_like_search(self, user_text: str) -> bool:
        return "搜索" in user_text or user_text.lower().startswith("search ")

    def _extract_search_query(self, user_text: str) -> str:
        query = user_text.replace("搜索", "", 1)
        query = re.sub(r"^search\b", "", query, flags=re.IGNORECASE)
        query = query.strip(" ：:")
        return query or user_text

    def _looks_like_todo(self, user_text: str) -> bool:
        lower_text = user_text.lower()
        return any(keyword in user_text for keyword in ("待办", "添加", "完成", "删除", "查看")) or any(
            keyword in lower_text for keyword in ("todo", "add", "complete", "delete", "list")
        )

    def _todo_decision(self, user_text: str) -> dict[str, Any]:
        lower_text = user_text.lower()
        if "查看" in user_text or "列表" in user_text or "list" in lower_text:
            return {"action": "tool", "tool_name": "todo", "arguments": {"operation": "list"}}

        if "完成" in user_text or "complete" in lower_text:
            return {
                "action": "tool",
                "tool_name": "todo",
                "arguments": {"operation": "complete", "id": self._extract_todo_id(user_text)},
            }

        if "删除" in user_text or "delete" in lower_text:
            return {
                "action": "tool",
                "tool_name": "todo",
                "arguments": {"operation": "delete", "id": self._extract_todo_id(user_text)},
            }

        title = self._extract_todo_title(user_text)
        return {
            "action": "tool",
            "tool_name": "todo",
            "arguments": {"operation": "create", "title": title},
        }

    def _extract_todo_id(self, user_text: str) -> int:
        match = re.search(r"\d+", user_text)
        if match is None:
            return 1

        return int(match.group(0))

    def _extract_todo_title(self, user_text: str) -> str:
        title = user_text
        title = re.sub(r"\b(todo|add|new|create)\b", " ", title, flags=re.IGNORECASE)
        for keyword in ("待办", "添加", "新增", "创建", "：", ":"):
            title = title.replace(keyword, " ")

        return " ".join(title.split()) or "未命名待办"

    def _extract_expression(self, user_text: str) -> str | None:
        candidates = re.findall(r"[-+*/().\d\s]+", user_text)
        valid_candidates = [
            candidate.strip()
            for candidate in candidates
            if any(char.isdigit() for char in candidate) and any(char in "+-*/" for char in candidate)
        ]
        if not valid_candidates:
            return None

        return max(valid_candidates, key=len)

    def _format_search_answer(self, data: dict[str, Any]) -> str:
        results = data["results"]
        if not results:
            return data["message"]

        titles = "；".join(result["title"] for result in results)
        source_label = "真实联网" if data.get("message", "").startswith("Real web search") else "mock"
        return f"找到 {len(results)} 条{source_label}搜索结果：{titles}。"

    def _format_todo_answer(self, data: dict[str, Any]) -> str:
        if "todos" in data:
            todos = data["todos"]
            if not todos:
                return "当前没有待办。"

            items = "；".join(
                f"{todo['id']}. {todo['title']} ({'完成' if todo['completed'] else '未完成'})"
                for todo in todos
            )
            return f"当前待办：{items}。"

        todo = data["todo"]
        status = "完成" if todo["completed"] else "未完成"
        return f"待办 {todo['id']}：{todo['title']}，状态：{status}。"


def load_local_api_key(config_path: Path = DEFAULT_LLM_CONFIG_PATH) -> str | None:
    if not config_path.exists():
        return None

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    api_key = config.get("api_key")
    if not isinstance(api_key, str) or not api_key.strip():
        return None

    return api_key.strip()


def build_llm_client(config_path: Path = DEFAULT_LLM_CONFIG_PATH) -> LLMClient:
    api_key = load_local_api_key(config_path)
    if api_key is None:
        print("未找到可用的 config/local_llm.json api_key，已回退到 RuleBasedLLM 演示模式。")
        return RuleBasedLLM()

    print("已加载 config/local_llm.json，默认使用阿里云百炼 qwen3.7-plus。")
    try:
        return AliyunBailianLLM(api_key=api_key)
    except RuntimeError as exc:
        print(f"阿里云百炼客户端初始化失败：{exc}")
        print("已回退到 RuleBasedLLM 演示模式。请确认已安装 requirements.txt 中的 openai 依赖。")
        return RuleBasedLLM()


def build_runtime(config_path: Path = DEFAULT_LLM_CONFIG_PATH) -> AgentRuntime:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(WebSearchTool())
    registry.register(MockSearchTool())
    registry.register(TodoTool())
    return AgentRuntime(llm_client=build_llm_client(config_path), tool_registry=registry)


def configure_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def format_agent_error(exc: Exception) -> str:
    message = str(exc)
    if "Aliyun Bailian API request failed" in message:
        return (
            "Agent error: 阿里云百炼请求失败。请检查网络、代理、API Key 和百炼服务地址；"
            f"原始错误：{message}"
        )
    if "invalid JSON" in message or "Invalid JSON" in message:
        return f"Agent error: LLM 返回内容不是有效 JSON，请重试或检查 system prompt；原始错误：{message}"
    if "exceeded max loop steps" in message:
        return f"Agent error: Agent 连续调用工具次数过多，已停止以避免死循环；原始错误：{message}"

    return f"Agent error: {message}"


def main() -> None:
    configure_stdio()
    runtime = build_runtime()
    print("Local Agent CLI started. Type 'exit' or 'quit' to leave.")

    while True:
        try:
            user_input = input("> ")
        except EOFError:
            print()
            break

        if user_input.strip().lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        try:
            answer = runtime.run(
                user_id=DEFAULT_USER_ID,
                session_id=DEFAULT_SESSION_ID,
                user_message=user_input,
            )
        except Exception as exc:
            answer = format_agent_error(exc)

        print(answer)


if __name__ == "__main__":
    main()
