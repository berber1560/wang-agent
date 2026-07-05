from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import main
from agent.llm_client import AliyunBailianLLM, BAILIAN_MODEL, FakeLLM, LLMClient, parse_llm_response
from agent.runtime import AgentRuntime
from tools.calculator import CalculatorTool
from tools.registry import ToolRegistry
from tools.search import MockSearchTool, WebSearchTool
from tools.todo import TodoTool


def test_fake_llm_is_llm_client() -> None:
    fake_llm = FakeLLM([])

    assert isinstance(fake_llm, LLMClient)


def test_fake_llm_returns_responses_in_order() -> None:
    fake_llm = FakeLLM(
        [
            {"action": "tool", "tool_name": "calculator", "arguments": {"expression": "1 + 2"}},
            {"action": "final", "answer": "计算结果是 3。"},
        ]
    )

    first = fake_llm.complete(messages=[{"role": "user", "content": "1 + 2"}], tool_schemas=[])
    second = fake_llm.complete(messages=[], tool_schemas=[])

    assert json.loads(first) == {
        "action": "tool",
        "tool_name": "calculator",
        "arguments": {"expression": "1 + 2"},
    }
    assert json.loads(second) == {"action": "final", "answer": "计算结果是 3。"}
    assert len(fake_llm.calls) == 2
    assert fake_llm.calls[0]["messages"] == [{"role": "user", "content": "1 + 2"}]


def test_fake_llm_raises_when_responses_are_exhausted() -> None:
    fake_llm = FakeLLM([])

    with pytest.raises(RuntimeError, match="no more responses"):
        fake_llm.complete(messages=[], tool_schemas=[])


def test_parse_llm_response_accepts_tool_action() -> None:
    decision = parse_llm_response(
        """
        {
          "action": "tool",
          "tool_name": "calculator",
          "arguments": {
            "expression": "1 + 2"
          }
        }
        """
    )

    assert decision == {
        "action": "tool",
        "tool_name": "calculator",
        "arguments": {"expression": "1 + 2"},
    }


def test_parse_llm_response_accepts_final_action() -> None:
    decision = parse_llm_response('{"action": "final", "answer": "计算结果是 3。"}')

    assert decision == {"action": "final", "answer": "计算结果是 3。"}


def test_parse_llm_response_rejects_invalid_json() -> None:
    with pytest.raises(ValueError, match="Invalid JSON response"):
        parse_llm_response("{not json")


def test_parse_llm_response_rejects_missing_action() -> None:
    with pytest.raises(ValueError, match="action must be 'tool' or 'final'"):
        parse_llm_response('{"answer": "missing action"}')


def test_parse_llm_response_rejects_invalid_action() -> None:
    with pytest.raises(ValueError, match="action must be 'tool' or 'final'"):
        parse_llm_response('{"action": "unknown"}')


def test_parse_llm_response_rejects_tool_without_arguments() -> None:
    with pytest.raises(ValueError, match="arguments"):
        parse_llm_response('{"action": "tool", "tool_name": "calculator"}')


def test_parse_llm_response_rejects_final_without_answer() -> None:
    with pytest.raises(ValueError, match="answer"):
        parse_llm_response('{"action": "final"}')


def test_runtime_returns_single_step_final_answer() -> None:
    fake_llm = FakeLLM([{"action": "final", "answer": "你好，我在。"}])
    runtime = AgentRuntime(fake_llm, ToolRegistry())

    answer = runtime.run(user_id="user-1", session_id="session-1", user_message="你好")
    session = runtime.get_session("user-1", "session-1")

    assert answer == "你好，我在。"
    assert session.messages == [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，我在。"},
    ]
    assert session.tool_traces == []


def test_runtime_calls_calculator_tool_then_returns_final_answer() -> None:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    fake_llm = FakeLLM(
        [
            {"action": "tool", "tool_name": "calculator", "arguments": {"expression": "1 + 2"}},
            {"action": "final", "answer": "计算结果是 3。"},
        ]
    )
    runtime = AgentRuntime(fake_llm, registry)

    answer = runtime.run(user_id="user-1", session_id="session-1", user_message="计算 1 + 2")
    session = runtime.get_session("user-1", "session-1")

    assert answer == "计算结果是 3。"
    assert session.tool_traces == [
        {
            "tool_name": "calculator",
            "arguments": {"expression": "1 + 2"},
            "success": True,
            "data": {"result": 3},
            "error": None,
        }
    ]
    assert session.messages[-1] == {"role": "assistant", "content": "计算结果是 3。"}


def test_runtime_calls_search_tool_then_returns_final_answer() -> None:
    registry = ToolRegistry()
    registry.register(MockSearchTool())
    fake_llm = FakeLLM(
        [
            {"action": "tool", "tool_name": "mock_search", "arguments": {"query": "Python 是什么"}},
            {"action": "final", "answer": "Python 是一种编程语言。"},
        ]
    )
    runtime = AgentRuntime(fake_llm, registry)

    answer = runtime.run(user_id="user-1", session_id="session-1", user_message="搜索 Python 是什么")
    session = runtime.get_session("user-1", "session-1")

    assert answer == "Python 是一种编程语言。"
    assert session.tool_traces[0]["tool_name"] == "mock_search"
    assert session.tool_traces[0]["success"] is True
    assert session.tool_traces[0]["data"]["results"]


def test_runtime_calls_web_search_tool_then_returns_final_answer() -> None:
    registry = ToolRegistry()
    registry.register(WebSearchTool(html_fetcher=lambda url, timeout: "<a class='result__a' href='https://example.com'>Example</a>"))
    fake_llm = FakeLLM(
        [
            {"action": "tool", "tool_name": "web_search", "arguments": {"query": "Example"}},
            {"action": "final", "answer": "找到 Example。"},
        ]
    )
    runtime = AgentRuntime(fake_llm, registry)

    answer = runtime.run(user_id="user-1", session_id="session-1", user_message="搜索 Example")
    session = runtime.get_session("user-1", "session-1")

    assert answer == "找到 Example。"
    assert session.tool_traces[0]["tool_name"] == "web_search"
    assert session.tool_traces[0]["success"] is True
    assert session.tool_traces[0]["data"]["results"][0]["source"] == "duckduckgo"


def test_rule_based_llm_routes_search_to_web_search() -> None:
    llm = main.RuleBasedLLM()

    response = llm.complete(messages=[{"role": "user", "content": "search Python"}], tool_schemas=[])

    assert json.loads(response) == {
        "action": "tool",
        "tool_name": "web_search",
        "arguments": {"query": "Python"},
    }


def test_build_runtime_registers_web_search_tool(tmp_path) -> None:
    runtime = main.build_runtime(tmp_path / "missing_local_llm.json")

    tool_names = [tool.name for tool in runtime.tool_registry.list_tools()]

    assert "web_search" in tool_names
    assert "mock_search" in tool_names


def test_format_agent_error_explains_aliyun_request_failure() -> None:
    message = main.format_agent_error(RuntimeError("Aliyun Bailian API request failed: Connection error."))

    assert "阿里云百炼请求失败" in message
    assert "网络、代理、API Key" in message
    assert "Connection error" in message


def test_format_agent_error_explains_invalid_json() -> None:
    message = main.format_agent_error(RuntimeError("Aliyun Bailian API returned invalid JSON: bad"))

    assert "不是有效 JSON" in message
    assert "bad" in message


def test_format_agent_error_explains_max_steps() -> None:
    message = main.format_agent_error(RuntimeError("AgentRuntime exceeded max loop steps."))

    assert "连续调用工具次数过多" in message
    assert "避免死循环" in message


def test_runtime_calls_todo_create_then_returns_final_answer() -> None:
    registry = ToolRegistry()
    registry.register(TodoTool())
    fake_llm = FakeLLM(
        [
            {"action": "tool", "tool_name": "todo", "arguments": {"operation": "create", "title": "提交周报"}},
            {"action": "final", "answer": "已添加待办：提交周报。"},
        ]
    )
    runtime = AgentRuntime(fake_llm, registry)

    answer = runtime.run(user_id="user-1", session_id="session-1", user_message="添加待办：提交周报")
    session = runtime.get_session("user-1", "session-1")

    assert answer == "已添加待办：提交周报。"
    assert session.todos == [{"id": 1, "title": "提交周报", "completed": False}]
    assert session.tool_traces[0]["tool_name"] == "todo"
    assert session.tool_traces[0]["data"]["todo"] == {"id": 1, "title": "提交周报", "completed": False}


def test_runtime_raises_when_max_steps_are_exceeded() -> None:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    fake_llm = FakeLLM(
        [
            {"action": "tool", "tool_name": "calculator", "arguments": {"expression": "1 + 1"}},
            {"action": "tool", "tool_name": "calculator", "arguments": {"expression": "2 + 2"}},
        ]
    )
    runtime = AgentRuntime(fake_llm, registry, max_steps=2)

    with pytest.raises(RuntimeError, match="exceeded max loop steps"):
        runtime.run(user_id="user-1", session_id="session-1", user_message="一直计算")

    session = runtime.get_session("user-1", "session-1")
    assert len(session.tool_traces) == 2


def test_runtime_compresses_messages_when_max_messages_is_exceeded() -> None:
    fake_llm = FakeLLM(
        [
            {"action": "final", "answer": "first answer"},
            {"action": "final", "answer": "second answer"},
            {"action": "final", "answer": "third answer"},
        ]
    )
    runtime = AgentRuntime(fake_llm, ToolRegistry())
    session = runtime.get_session("user-1", "session-1")
    session.max_messages = 2

    runtime.run("user-1", "session-1", "first request")
    runtime.run("user-1", "session-1", "second request")
    runtime.run("user-1", "session-1", "third request")

    assert "用户请求：first request" in session.summary
    assert "用户请求：second request" in session.summary
    assert len(session.messages) == 2


def test_runtime_sends_summary_recent_messages_and_tool_schemas_to_llm() -> None:
    fake_llm = FakeLLM(
        [
            {"action": "final", "answer": "first answer"},
            {"action": "final", "answer": "second answer"},
            {"action": "final", "answer": "third answer"},
        ]
    )
    runtime = AgentRuntime(fake_llm, ToolRegistry())
    session = runtime.get_session("user-1", "session-1")
    session.max_messages = 2

    runtime.run("user-1", "session-1", "first request")
    runtime.run("user-1", "session-1", "second request")
    runtime.run("user-1", "session-1", "third request")

    last_call_messages = fake_llm.calls[-1]["messages"]
    assert last_call_messages[0]["role"] == "system"
    assert "Session summary" in last_call_messages[0]["content"]
    assert "first request" in last_call_messages[0]["content"]
    assert last_call_messages[-1] == {"role": "user", "content": "third request"}
    assert fake_llm.calls[-1]["tool_schemas"] == []


def test_runtime_session_summaries_are_isolated() -> None:
    fake_llm = FakeLLM(
        [
            {"action": "final", "answer": "A1"},
            {"action": "final", "answer": "A2"},
            {"action": "final", "answer": "B1"},
        ]
    )
    runtime = AgentRuntime(fake_llm, ToolRegistry())
    first_session = runtime.get_session("user-1", "session-a")
    second_session = runtime.get_session("user-1", "session-b")
    first_session.max_messages = 2
    second_session.max_messages = 2

    runtime.run("user-1", "session-a", "first session request")
    runtime.run("user-1", "session-a", "first session followup")
    runtime.run("user-1", "session-b", "second session request")

    assert "first session request" in first_session.summary
    assert "second session request" not in first_session.summary
    assert second_session.summary == ""


def test_runtime_keeps_recent_messages_after_compression() -> None:
    fake_llm = FakeLLM(
        [
            {"action": "final", "answer": "first answer"},
            {"action": "final", "answer": "second answer"},
            {"action": "final", "answer": "third answer"},
        ]
    )
    runtime = AgentRuntime(fake_llm, ToolRegistry())
    session = runtime.get_session("user-1", "session-1")
    session.max_messages = 2

    runtime.run("user-1", "session-1", "first request")
    runtime.run("user-1", "session-1", "second request")
    runtime.run("user-1", "session-1", "third request")

    assert session.messages == [
        {"role": "user", "content": "third request"},
        {"role": "assistant", "content": "third answer"},
    ]


class FakeCompletions:
    def __init__(self, chunks: list[object]) -> None:
        self.chunks = chunks
        self.kwargs = None

    def create(self, **kwargs: object) -> list[object]:
        self.kwargs = kwargs
        return self.chunks


def make_stream_chunk(content: str | None = None, reasoning_content: str | None = None) -> object:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(
                    content=content,
                    reasoning_content=reasoning_content,
                )
            )
        ]
    )


def test_aliyun_bailian_llm_builds_request_and_collects_streaming_content() -> None:
    completions = FakeCompletions(
        [
            make_stream_chunk(reasoning_content="ignored thinking"),
            make_stream_chunk('{"action":"final",'),
            make_stream_chunk('"answer":"你好"}'),
        ]
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    llm = AliyunBailianLLM(api_key="test-api-key", client=client)

    result = llm.complete(
        messages=[
            {"role": "system", "content": "Session summary:\n用户请求：旧问题"},
            {"role": "user", "content": "你好"},
            {
                "role": "tool",
                "tool_name": "calculator",
                "content": {"success": True, "data": {"result": 3}, "error": None},
            },
        ],
        tool_schemas=[{"name": "calculator", "parameters": {"type": "object"}}],
    )

    assert result == '{"action":"final","answer":"你好"}'
    assert completions.kwargs["model"] == BAILIAN_MODEL
    assert completions.kwargs["extra_body"] == {"enable_thinking": True}
    assert completions.kwargs["stream"] is True
    request_messages = completions.kwargs["messages"]
    assert request_messages[0]["role"] == "system"
    assert "只输出严格 JSON" in request_messages[0]["content"]
    assert "calculator" in request_messages[0]["content"]
    assert request_messages[1] == {"role": "system", "content": "Session summary:\n用户请求：旧问题"}
    assert request_messages[2] == {"role": "user", "content": "你好"}
    assert request_messages[3]["role"] == "user"
    assert "最近一次工具调用结果：calculator" in request_messages[3]["content"]


def test_aliyun_bailian_llm_rejects_invalid_json_response() -> None:
    completions = FakeCompletions([make_stream_chunk("not json")])
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    llm = AliyunBailianLLM(api_key="test-api-key", client=client)

    with pytest.raises(RuntimeError, match="invalid JSON"):
        llm.complete(messages=[{"role": "user", "content": "hello"}], tool_schemas=[])


def test_build_llm_client_falls_back_when_config_is_missing(tmp_path, capsys) -> None:
    missing_config = tmp_path / "local_llm.json"

    llm_client = main.build_llm_client(missing_config)

    assert isinstance(llm_client, main.RuleBasedLLM)
    assert "回退到 RuleBasedLLM" in capsys.readouterr().out


def test_build_llm_client_uses_aliyun_when_config_has_api_key(tmp_path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "local_llm.json"
    config_path.write_text('{"api_key": "test-api-key"}', encoding="utf-8")
    captured = {}

    class FakeAliyunBailianLLM:
        def __init__(self, api_key: str) -> None:
            captured["api_key"] = api_key

    monkeypatch.setattr(main, "AliyunBailianLLM", FakeAliyunBailianLLM)

    llm_client = main.build_llm_client(config_path)

    assert isinstance(llm_client, FakeAliyunBailianLLM)
    assert captured["api_key"] == "test-api-key"
    assert "qwen3.7-plus" in capsys.readouterr().out


def test_build_llm_client_falls_back_when_aliyun_client_cannot_initialize(tmp_path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "local_llm.json"
    config_path.write_text('{"api_key": "test-api-key"}', encoding="utf-8")

    class BrokenAliyunBailianLLM:
        def __init__(self, api_key: str) -> None:
            raise RuntimeError("The openai package is required.")

    monkeypatch.setattr(main, "AliyunBailianLLM", BrokenAliyunBailianLLM)

    llm_client = main.build_llm_client(config_path)

    assert isinstance(llm_client, main.RuleBasedLLM)
    output = capsys.readouterr().out
    assert "客户端初始化失败" in output
    assert "回退到 RuleBasedLLM" in output
