from __future__ import annotations

from agent.llm_client import FakeLLM
from agent.runtime import AgentRuntime
from tools.calculator import CalculatorTool
from tools.registry import ToolRegistry
from tools.search import MockSearchTool
from tools.todo import TodoTool


def build_runtime(fake_llm: FakeLLM) -> AgentRuntime:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(MockSearchTool())
    registry.register(TodoTool())
    return AgentRuntime(fake_llm, registry)


def test_e2e_direct_chat_returns_final_without_tools() -> None:
    runtime = build_runtime(FakeLLM([{"action": "final", "answer": "你好，我可以帮你处理本地任务。"}]))

    answer = runtime.run("user-1", "session-1", "你好")
    session = runtime.get_session("user-1", "session-1")

    assert answer == "你好，我可以帮你处理本地任务。"
    assert session.tool_traces == []
    assert session.messages[-1] == {"role": "assistant", "content": "你好，我可以帮你处理本地任务。"}


def test_e2e_calculates_requested_expression() -> None:
    runtime = build_runtime(
        FakeLLM(
            [
                {"action": "tool", "tool_name": "calculator", "arguments": {"expression": "128 * 36 + 450"}},
                {"action": "final", "answer": "计算结果是 5058。"},
            ]
        )
    )

    answer = runtime.run("user-1", "session-1", "帮我计算 128 * 36 + 450")
    session = runtime.get_session("user-1", "session-1")

    assert answer == "计算结果是 5058。"
    assert session.tool_traces == [
        {
            "tool_name": "calculator",
            "arguments": {"expression": "128 * 36 + 450"},
            "success": True,
            "data": {"result": 5058},
            "error": None,
        }
    ]


def test_e2e_searches_python_and_summarizes_result() -> None:
    runtime = build_runtime(
        FakeLLM(
            [
                {"action": "tool", "tool_name": "mock_search", "arguments": {"query": "Python 是什么"}},
                {"action": "final", "answer": "Python 是一种易读、通用的编程语言。"},
            ]
        )
    )

    answer = runtime.run("user-1", "session-1", "搜索 Python 是什么")
    session = runtime.get_session("user-1", "session-1")

    assert answer == "Python 是一种易读、通用的编程语言。"
    assert session.tool_traces[0]["tool_name"] == "mock_search"
    assert session.tool_traces[0]["arguments"] == {"query": "Python 是什么"}
    assert session.tool_traces[0]["success"] is True
    assert session.tool_traces[0]["data"]["results"]


def test_e2e_adds_todo() -> None:
    runtime = build_runtime(
        FakeLLM(
            [
                {
                    "action": "tool",
                    "tool_name": "todo",
                    "arguments": {"operation": "create", "title": "明天下午三点提交周报"},
                },
                {"action": "final", "answer": "已添加待办：明天下午三点提交周报。"},
            ]
        )
    )

    answer = runtime.run("user-1", "session-1", "添加待办 明天下午三点提交周报")
    session = runtime.get_session("user-1", "session-1")
    other_session = runtime.get_session("user-1", "session-2")

    assert answer == "已添加待办：明天下午三点提交周报。"
    assert session.todos == [{"id": 1, "title": "明天下午三点提交周报", "completed": False}]
    assert other_session.todos == []
    assert session.tool_traces[0]["tool_name"] == "todo"
    assert session.tool_traces[0]["data"]["todo"] == session.todos[0]


def test_e2e_lists_current_todos() -> None:
    runtime = build_runtime(
        FakeLLM(
            [
                {"action": "tool", "tool_name": "todo", "arguments": {"operation": "list"}},
                {"action": "final", "answer": "当前待办有：明天下午三点提交周报。"},
            ]
        )
    )
    session = runtime.get_session("user-1", "session-1")
    session.todos.append({"id": 1, "title": "明天下午三点提交周报", "completed": False})

    answer = runtime.run("user-1", "session-1", "查看当前待办")

    assert answer == "当前待办有：明天下午三点提交周报。"
    assert session.tool_traces[0]["tool_name"] == "todo"
    assert session.tool_traces[0]["arguments"] == {"operation": "list"}
    assert session.tool_traces[0]["data"]["todos"] == [
        {"id": 1, "title": "明天下午三点提交周报", "completed": False}
    ]


def test_e2e_completes_report_todo() -> None:
    runtime = build_runtime(
        FakeLLM(
            [
                {"action": "tool", "tool_name": "todo", "arguments": {"operation": "complete", "id": 1}},
                {"action": "final", "answer": "已将提交周报标记为完成。"},
            ]
        )
    )
    session = runtime.get_session("user-1", "session-1")
    session.todos.append({"id": 1, "title": "明天下午三点提交周报", "completed": False})

    answer = runtime.run("user-1", "session-1", "把提交周报标记完成")

    assert answer == "已将提交周报标记为完成。"
    assert session.todos == [{"id": 1, "title": "明天下午三点提交周报", "completed": True}]
    assert session.tool_traces[0]["tool_name"] == "todo"
    assert session.tool_traces[0]["data"]["todo"]["completed"] is True


def test_e2e_searches_iphone_price_then_calculates_three_units() -> None:
    runtime = build_runtime(
        FakeLLM(
            [
                {"action": "tool", "tool_name": "mock_search", "arguments": {"query": "苹果手机价格"}},
                {"action": "tool", "tool_name": "calculator", "arguments": {"expression": "5999 * 3"}},
                {"action": "final", "answer": "按 mock 单价 5999 计算，买 3 台共 17997。"},
            ]
        )
    )

    answer = runtime.run("user-1", "session-1", "搜索苹果手机模拟价格，并计算买 3 台多少钱")
    session = runtime.get_session("user-1", "session-1")

    assert answer == "按 mock 单价 5999 计算，买 3 台共 17997。"
    assert [trace["tool_name"] for trace in session.tool_traces] == ["mock_search", "calculator"]
    assert session.tool_traces[0]["arguments"] == {"query": "苹果手机价格"}
    assert session.tool_traces[1]["arguments"] == {"expression": "5999 * 3"}
    assert session.tool_traces[1]["data"] == {"result": 17997}


def test_e2e_searches_beijing_weather_then_adds_umbrella_todo() -> None:
    runtime = build_runtime(
        FakeLLM(
            [
                {"action": "tool", "tool_name": "mock_search", "arguments": {"query": "北京天气"}},
                {"action": "tool", "tool_name": "todo", "arguments": {"operation": "create", "title": "带伞"}},
                {"action": "final", "answer": "已根据天气搜索结果添加待办：带伞。"},
            ]
        )
    )

    answer = runtime.run("user-1", "session-1", "搜索北京天气，如果下雨就添加带伞待办")
    session = runtime.get_session("user-1", "session-1")

    assert answer == "已根据天气搜索结果添加待办：带伞。"
    assert [trace["tool_name"] for trace in session.tool_traces] == ["mock_search", "todo"]
    assert session.tool_traces[0]["arguments"] == {"query": "北京天气"}
    assert session.tool_traces[1]["arguments"] == {"operation": "create", "title": "带伞"}
    assert session.todos == [{"id": 1, "title": "带伞", "completed": False}]


def test_e2e_calculates_expenses_then_adds_reimbursement_todo() -> None:
    runtime = build_runtime(
        FakeLLM(
            [
                {"action": "tool", "tool_name": "calculator", "arguments": {"expression": "32 + 48 + 26"}},
                {"action": "tool", "tool_name": "todo", "arguments": {"operation": "create", "title": "报销今天开销"}},
                {"action": "final", "answer": "总额是 106，并已添加报销今天开销待办。"},
            ]
        )
    )

    answer = runtime.run("user-1", "session-1", "计算午饭32、打车48、咖啡26的总额，并记录报销今天开销待办")
    session = runtime.get_session("user-1", "session-1")

    assert answer == "总额是 106，并已添加报销今天开销待办。"
    assert [trace["tool_name"] for trace in session.tool_traces] == ["calculator", "todo"]
    assert session.tool_traces[0]["data"] == {"result": 106}
    assert session.tool_traces[1]["data"]["todo"] == {"id": 1, "title": "报销今天开销", "completed": False}
    assert session.todos == [{"id": 1, "title": "报销今天开销", "completed": False}]


def test_e2e_deletes_reimbursement_todo() -> None:
    runtime = build_runtime(
        FakeLLM(
            [
                {"action": "tool", "tool_name": "todo", "arguments": {"operation": "delete", "id": 1}},
                {"action": "final", "answer": "已删除刚才的报销待办。"},
            ]
        )
    )
    session = runtime.get_session("user-1", "session-1")
    session.todos.append({"id": 1, "title": "报销今天开销", "completed": False})
    other_session = runtime.get_session("user-2", "session-1")
    other_session.todos.append({"id": 1, "title": "其他会话待办", "completed": False})

    answer = runtime.run("user-1", "session-1", "删除刚才的报销待办")

    assert answer == "已删除刚才的报销待办。"
    assert session.todos == []
    assert other_session.todos == [{"id": 1, "title": "其他会话待办", "completed": False}]
    assert session.tool_traces[0]["tool_name"] == "todo"
    assert session.tool_traces[0]["arguments"] == {"operation": "delete", "id": 1}
    assert session.tool_traces[0]["data"]["todo"] == {"id": 1, "title": "报销今天开销", "completed": False}
